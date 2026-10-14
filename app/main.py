"""FlowTwin API and frontend host. Run with a single worker: uvicorn app.main:app --host 0.0.0.0 --port 8000"""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .calibration import Calibration, frame_quality
from .events import EventLog
from .gpu import gpu_info, gpu_stats
from .inventory import Inventory
from .metrics import Metrics
from .occupancy import Occupancy, ZoneState
from .operations import Operations
from .perception import make_detector
from .planner import DEFAULT_MAP, Planner, load_maps
from .simulator import Simulator, VehicleStatus, compare_policies

ROOT = Path(__file__).resolve().parent.parent
MODES = ("SYNTHETIC", "LIVE", "REPLAY")
TICK_S = 0.1
MAX_EVIDENCE_FILES = 300


class World:
    """All mutable state. Only touched from the event loop, so no locking is needed around it."""

    def __init__(self, data_dir: Path, detector=None):
        self.data_dir = data_dir
        self.evidence_dir = data_dir / "evidence"
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.maps = load_maps()
        self.map = self.maps[DEFAULT_MAP]
        self.th = json.loads((ROOT / "config" / "thresholds.json").read_text())
        # Try other props without editing the config: FLOWTWIN_CLASSES="cell phone,scissors"
        override = [c.strip() for c in os.environ.get("FLOWTWIN_CLASSES", "").split(",") if c.strip()]
        if override:
            self.th["supported_classes"] = override
        self.detector = detector or make_detector(self.th["conf"], self.th["imgsz"])
        self.events = EventLog(data_dir / "events.jsonl")
        self.metrics = Metrics()
        self.inference_lock = asyncio.Lock()
        self.planner = Planner(self.map)
        self.occupancy = Occupancy(self.map.zones, self.th["block_frames"], self.th["clear_frames"],
                                   self.th["clear_seconds"], self.th["stale_seconds"])
        self.calibration: Calibration | None = None
        self._load_calibration()
        self.inventory = Inventory(self.map)
        self.fleet_enabled = False
        self.mode = "SYNTHETIC"
        self.new_session("SYNTHETIC", "startup")

    def log(self, kind: str, **fields) -> dict:
        return self.events.add(kind, session_id=self.session_id, input_mode=self.mode,
                               inference_backend=self.detector.info["backend"],
                               calibration_version=self.calibration.version if self.calibration else None,
                               **fields)

    def new_session(self, mode: str, why: str) -> None:
        """Fresh session: results still in flight for the old one are discarded when they return."""
        self.session_id = uuid.uuid4().hex[:8]
        self.mode = mode
        self.last_frame_id = -1
        self.last_detections: list[dict] = []
        self.view = {"ok": mode == "SYNTHETIC", "reason": "" if mode == "SYNTHETIC" else "no observation yet"}
        initial = ZoneState.CLEAR if mode == "SYNTHETIC" else ZoneState.UNKNOWN
        self.occupancy.reset(initial, time.monotonic(),
                             "synthetic default" if mode == "SYNTHETIC" else "no observation yet")
        self.sim = Simulator(self.map, self.planner, "dynamic", self.log)
        self.kpis = {"deliveries": 0, "delivery_s": 0.0, "waiting_s": 0.0, "reroutes": 0,
                     "blocked_events": 0, "unknown_events": 0}
        self._counted: dict[str, int] = {}
        self.ops = Operations(self.map, self.planner, self.inventory, self._record_delivery, self.log)
        self.ops.enabled = self.fleet_enabled
        self.log("session", decision_reason=f"{why}: new session in {mode} mode")

    def _record_delivery(self, key: str, sim: Simulator) -> None:
        """Count one completed leg in the session KPIs."""
        self.kpis["deliveries"] += 1
        self.kpis["delivery_s"] += sim.elapsed
        self.kpis["waiting_s"] += sim.waiting
        self.kpis["reroutes"] += max(0, sim.plan_changes - 1)

    def _count_delivery(self, key: str, sim: Simulator) -> None:
        """The operator's own delivery (V1): counted once, and it picks stock directly."""
        if sim.status == VehicleStatus.DONE and self._counted.get(key) != sim.orders_started:
            self._counted[key] = sim.orders_started
            self._record_delivery(key, sim)
            picked = self.inventory.pick()
            if picked:
                self.log("inventory", decision_reason=f"{key}: {picked} (SIMULATED stock)")

    def set_map(self, map_id: str) -> None:
        """Switch use case. The footprint is shared, so the camera calibration stays valid."""
        self.map = self.maps[map_id]
        self.planner = Planner(self.map)
        self.occupancy = Occupancy(self.map.zones, self.th["block_frames"], self.th["clear_frames"],
                                   self.th["clear_seconds"], self.th["stale_seconds"])
        self.inventory = Inventory(self.map)
        self.new_session(self.mode, f"use case changed to {self.map.data['name']}")

    def _load_calibration(self) -> None:
        path = self.data_dir / "calibration.json"
        if path.exists():
            saved = json.loads(path.read_text())
            self.calibration = Calibration(saved["version"], saved["image_points"],
                                           self.map.data["width"], self.map.data["height"])

    def set_calibration(self, image_points) -> Calibration:
        version = (self.calibration.version if self.calibration else 0) + 1
        self.calibration = Calibration(version, image_points, self.map.data["width"], self.map.data["height"])
        (self.data_dir / "calibration.json").write_text(
            json.dumps({"version": version, "image_points": self.calibration.image_points}))
        if self.mode != "SYNTHETIC":
            self.log_transitions(self.occupancy.invalidate(time.monotonic(), "recalibrated"))
        self.log("calibration", decision_reason=f"calibration v{version} set")
        return self.calibration

    def log_transitions(self, transitions, frame_id=None, evidence_id=None) -> None:
        for t in transitions:
            if t.new == ZoneState.BLOCKED:
                self.kpis["blocked_events"] += 1
            elif t.new == ZoneState.UNKNOWN:
                self.kpis["unknown_events"] += 1
            self.occupancy.zones[t.zone_id].evidence_id = evidence_id
            self.log("zone", zone_id=t.zone_id, old_state=t.old.value, new_state=t.new.value,
                     frame_id=frame_id, evidence_id=evidence_id, decision_reason=t.reason)

    def step(self, now: float, dt: float) -> None:
        if self.mode != "SYNTHETIC":
            # Staleness is about the view, not only about zone changes: zones may already be UNKNOWN.
            if self.occupancy.is_stale(now):
                self.view = {"ok": False, "reason": "no fresh camera frame"}
                self.log_transitions(self.occupancy.check_stale(now))
        states = self.occupancy.states()
        self.sim.tick(dt, states)
        self._count_delivery("V1", self.sim)
        self.ops.step(dt, states, extra_vehicles=(self.sim,))

    def kpi_snapshot(self) -> dict:
        k = self.kpis
        n = k["deliveries"]
        return {"source": "SIMULATED vehicles, " + ("manual zones" if self.mode == "SYNTHETIC" else "observed zones"),
                "deliveries": n, "avg_delivery_s": round(k["delivery_s"] / n, 1) if n else None,
                "avg_waiting_s": round(k["waiting_s"] / n, 1) if n else None, "reroutes": k["reroutes"],
                "blocked_events": k["blocked_events"], "unknown_events": k["unknown_events"],
                "inventory_fill": self.inventory.snapshot()["fill"]}

    def snapshot(self) -> dict:
        now = time.monotonic()
        occ = self.occupancy
        zones = {
            zone_id: {
                "state": s.state.value, "reason": s.reason, "state_age_s": round(now - s.since, 1),
                "observation_age_s": None if s.last_observed is None else round(now - s.last_observed, 1),
                "evidence_id": s.evidence_id,
            } for zone_id, s in occ.zones.items()
        }
        calibration = None
        if self.calibration:
            c = self.calibration
            calibration = {
                "version": c.version, "image_points": c.image_points,
                "zones_image": {z: c.to_image(zone["polygon"]).round(4).tolist()
                                for z, zone in self.map.zones.items()},
            }
        return {
            "session_id": self.session_id, "mode": self.mode, "server_time": time.time(),
            "map_id": self.map.data["id"],
            "zones": zones, "vehicle": self.sim.snapshot(), "view": self.view,
            "camera": {"age_s": None if occ.last_frame_time is None else round(now - occ.last_frame_time, 2),
                       "last_frame_id": self.last_frame_id, "detections": self.last_detections},
            "calibration": calibration, "detector": self.detector.info,
            "kpis": self.kpi_snapshot(), **self.ops.snapshot(self.occupancy.states()),
            "events": self.events.recent(40),
        }


async def _ticker(world: World) -> None:
    last = time.monotonic()
    while True:
        await asyncio.sleep(TICK_S)
        now = time.monotonic()
        world.step(now, min(now - last, 0.5))
        last = now


async def _read_bounded(request: Request, limit: int) -> bytes:
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > limit:
        raise HTTPException(413, "frame too large")
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise HTTPException(413, "frame too large")
        chunks.append(chunk)
    return b"".join(chunks)


async def _json(request: Request) -> dict:
    """Request body as a JSON object; an empty body is an empty object."""
    if not await request.body():
        return {}
    try:
        body = await request.json()
    except ValueError:
        raise HTTPException(422, "body is not valid JSON") from None
    if not isinstance(body, dict):
        raise HTTPException(422, "body must be a JSON object")
    return body


def create_app(data_dir: Path | None = None, detector=None, run_ticker: bool = True) -> FastAPI:
    data_dir = Path(data_dir or os.environ.get("FLOWTWIN_DATA", ROOT / "data"))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.world = World(data_dir, detector)  # the model is loaded once, here
        task = asyncio.create_task(_ticker(app.state.world)) if run_ticker else None
        yield
        if task:
            task.cancel()

    app = FastAPI(title="FlowTwin", lifespan=lifespan)

    def world() -> World:
        return app.state.world

    @app.get("/healthz")
    def healthz():
        return {"ok": True, "mode": world().mode}

    @app.get("/api/status")
    def status():
        w = world()
        age = w.snapshot()["camera"]["age_s"]
        return {"detector": w.detector.info, "mode": w.mode, "session_id": w.session_id,
                "calibration_version": w.calibration.version if w.calibration else None,
                "camera_age_s": age, "thresholds": w.th, "map_id": w.map.data["id"], "map_version": w.map.data["version"]}

    @app.get("/api/gpu")
    def gpu():
        """Accelerator facts, live memory and load, and per-stage latency, all read from the device."""
        w = world()
        measured = w.metrics.summary()
        stages = {k: measured[k] for k in ("preprocess_ms", "model_ms", "postprocess_ms", "inference_ms") if k in measured}
        return {"info": gpu_info(), "stats": gpu_stats(), "detector": w.detector.info, "latency": stages,
                "frames_analyzed": w.metrics.frames}

    @app.get("/api/map")
    def get_map():
        return world().map.data

    @app.get("/api/maps")
    def get_maps():
        return [{"id": m.data["id"], "name": m.data["name"], "use_case": m.data["use_case"]}
                for m in world().maps.values()]

    @app.post("/api/map")
    async def choose_map(request: Request):
        w = world()
        map_id = (await _json(request)).get("id")
        if map_id not in w.maps:
            raise HTTPException(422, f"unknown map; choose one of {list(w.maps)}")
        w.set_map(map_id)
        return w.snapshot()

    @app.get("/api/state")
    def state():
        return world().snapshot()

    @app.get("/api/events")
    def events(limit: int = 200):
        return world().events.recent(max(1, min(limit, 2000)))

    @app.get("/api/metrics")
    def metrics():
        w = world()
        return {
            "measured": w.metrics.summary(), "frames_analyzed": w.metrics.frames,
            "frames_rejected": w.metrics.rejected,
            "notes": {"inference_ms": "prediction call including pre/postprocessing, not model-only",
                      "model_ms": "model execution only, CUDA-synchronized, as profiled by the detector",
                      "clock": "server monotonic clock"},
            "simulation_assumptions": {"vehicle_speed_units_s": w.map.speed, "turn_cost_s": w.map.turn_cost_s,
                                       "tick_s": TICK_S, "units": "map units, not physically calibrated"},
        }

    @app.get("/api/comparison")
    def comparison():
        scenarios = json.loads((ROOT / "config" / "scenarios.json").read_text())["scenarios"]
        return compare_policies(world().map, scenarios)

    @app.get("/api/evidence/{evidence_id}")
    def evidence(evidence_id: str):
        if not re.fullmatch(r"[0-9a-f]{12}", evidence_id):
            raise HTTPException(400, "bad evidence id")
        path = world().evidence_dir / f"{evidence_id}.jpg"
        if not path.exists():
            raise HTTPException(404, "no such evidence")
        return FileResponse(path, media_type="image/jpeg")

    @app.post("/api/calibration")
    async def calibrate(request: Request):
        body = await _json(request)
        try:
            c = world().set_calibration(body["image_points"])
            errors = c.check(body.get("check_points", []))
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from None
        return {"version": c.version, "check_errors_map_units": [round(e, 2) for e in errors]}

    @app.post("/api/calibration/check")
    async def check_calibration(request: Request):
        """Held-out check: where does a clicked image point land, against where it should be on the map?"""
        w = world()
        if w.calibration is None:
            raise HTTPException(409, "camera not calibrated")
        body = await _json(request)
        try:
            error = w.calibration.check([{"image": body["image"], "map": body["map"]}])[0]
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from None
        return {"calibration_version": w.calibration.version, "error_map_units": round(error, 2),
                "map_width_units": w.map.data["width"]}

    @app.post("/api/orders")
    async def create_order(request: Request):
        w = world()
        body = await _json(request)
        source = body.get("source", w.map.data["order"]["source"])
        dest = body.get("dest", w.map.data["order"]["dest"])
        if source not in w.map.nodes or dest not in w.map.nodes or source == dest:
            raise HTTPException(422, "unknown or identical source/destination")
        w.sim.start_order(source, dest)
        w.sim.tick(0.0, w.occupancy.states())
        return w.snapshot()

    @app.post("/api/demo/reset")
    async def reset(request: Request):
        w = world()
        body = await _json(request)
        mode = body.get("mode", w.mode)
        if mode not in MODES:
            raise HTTPException(422, f"mode must be one of {MODES}")
        w.new_session(mode, "reset")
        return w.snapshot()

    @app.post("/api/sim/zone")
    async def sim_zone(request: Request):
        w = world()
        if w.mode != "SYNTHETIC":
            raise HTTPException(409, "manual zone control is only available in SYNTHETIC mode")
        body = await _json(request)
        try:
            zone_id, new_state = body["zone_id"], ZoneState(body["state"])
        except (KeyError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from None
        if zone_id not in w.map.zones:
            raise HTTPException(422, "unknown zone")
        w.log_transitions(w.occupancy.force(zone_id, new_state, time.monotonic(), "synthetic operator input"))
        w.sim.tick(0.0, w.occupancy.states())
        return w.snapshot()

    @app.post("/api/sim/pause")
    async def sim_pause(request: Request):
        w = world()
        w.sim.set_held(bool((await _json(request)).get("paused", True)))
        return w.snapshot()

    @app.get("/api/inventory")
    def inventory():
        return world().inventory.snapshot()

    @app.post("/api/fleet")
    async def fleet(request: Request):
        w = world()
        enabled = bool((await _json(request)).get("enabled", True))
        if enabled != w.fleet_enabled:
            w.fleet_enabled = enabled
            w.ops = Operations(w.map, w.planner, w.inventory, w._record_delivery, w.log)
            w.ops.enabled = enabled
            w.log("fleet", decision_reason=(f"operations started: {len(w.ops.vehicles)} extra simulated vehicles, "
                                            "orders and trucks" if enabled else "operations stopped"))
        return w.snapshot()

    @app.get("/api/analytics")
    def analytics():
        return world().ops.analytics()

    @app.post("/api/frame")
    async def frame(request: Request):
        import cv2

        w = world()
        th = w.th

        def reject(code: int, why: str):
            w.metrics.rejected += 1
            raise HTTPException(code, why)

        if w.mode == "SYNTHETIC":
            reject(409, "switch to LIVE or REPLAY mode before sending frames")
        session_id = request.headers.get("x-session-id")
        if session_id != w.session_id:
            reject(409, "frame belongs to an old session")
        if request.headers.get("x-input-mode", w.mode) != w.mode:
            reject(409, "input mode does not match the session")
        try:
            frame_id = int(request.headers["x-frame-id"])
        except (KeyError, ValueError):
            reject(400, "x-frame-id header must be an integer")
        if frame_id <= w.last_frame_id:
            reject(409, "out-of-order frame")
        body = await _read_bounded(request, th["max_frame_bytes"])
        if w.inference_lock.locked():
            reject(429, "inference busy; send the next frame after the previous response")

        calibration = w.calibration
        async with w.inference_lock:
            started = time.perf_counter()
            image = cv2.imdecode(np.frombuffer(body, dtype=np.uint8), cv2.IMREAD_COLOR)
            if image is None:
                reject(400, "body is not a decodable image")
            height, width = image.shape[:2]
            if max(height, width) > th["max_frame_side"]:
                reject(413, "frame dimensions too large")
            decoded = time.perf_counter()
            quality = frame_quality(image, th["min_brightness"], th["min_sharpness"])
            detections, inference_ms = [], 0.0
            if quality["ok"]:
                detections, inference_ms = await run_in_threadpool(w.detector.predict, image)
            analyzed = time.perf_counter()

        if session_id != w.session_id or calibration is not w.calibration:
            reject(409, "result discarded: session or calibration changed during inference")
        w.last_frame_id = frame_id

        obstructed: set[str] = set()
        out = []
        for d in detections:
            box_n = [d.box[0] / width, d.box[1] / height, d.box[2] / width, d.box[3] / height]
            supported = d.cls in th["supported_classes"]
            zones = calibration.zones_for_box(box_n, w.map.zones, th["min_zone_overlap"]) \
                if supported and calibration else []
            obstructed.update(zones)
            out.append({"class": d.cls, "confidence": round(d.conf, 3), "box_n": [round(v, 4) for v in box_n],
                        "supported": supported, "zones": zones})
        if not quality["ok"]:
            view = {"ok": False, "reason": quality["reason"]}
        elif calibration is None:
            view = {"ok": False, "reason": "camera not calibrated"}
        else:
            view = {"ok": True, "reason": ""}
        w.view, w.last_detections = view, out

        transitions = w.occupancy.observe(time.monotonic(), obstructed, view["ok"], view["reason"])
        evidence_id = None
        if transitions:
            evidence_id = uuid.uuid4().hex[:12]
            (w.evidence_dir / f"{evidence_id}.jpg").write_bytes(body)
            saved = sorted(w.evidence_dir.glob("*.jpg"), key=lambda p: p.stat().st_mtime)
            for old in saved[:-MAX_EVIDENCE_FILES]:
                old.unlink(missing_ok=True)
            w.log_transitions(transitions, frame_id, evidence_id)
        w.sim.tick(0.0, w.occupancy.states())
        finished = time.perf_counter()

        timings = {"decode_ms": (decoded - started) * 1000, "inference_ms": inference_ms,
                   "state_plan_ms": (finished - analyzed) * 1000, "server_total_ms": (finished - started) * 1000}
        if quality["ok"]:  # stage breakdown of the prediction call, when the detector reports one
            timings.update(getattr(w.detector, "last_stages", {}))
        w.metrics.frames += 1
        w.metrics.record(**timings)
        return {"frame_id": frame_id, "detections": out, "quality": quality,
                "timings": {k: round(v, 1) for k, v in timings.items()}, "state": w.snapshot()}

    dist = ROOT / "frontend" / "dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return app


app = create_app()
