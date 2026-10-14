import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.perception import Detection


class FakeDetector:
    info = {"model": "fake", "backend": "TEST", "device": "cpu", "gpu": None}

    def __init__(self):
        self.boxes = []

    def predict(self, image):
        return [Detection("book", 0.9, b) for b in self.boxes], 1.0


def jpeg(dark=False):
    rng = np.random.default_rng(0)
    img = np.zeros((480, 640, 3), np.uint8) if dark else rng.integers(0, 255, (480, 640, 3), dtype=np.uint8)
    return cv2.imencode(".jpg", img)[1].tobytes()


@pytest.fixture
def ctx(tmp_path):
    detector = FakeDetector()
    with TestClient(create_app(tmp_path, detector, run_ticker=False)) as client:
        yield client, detector


def send(client, frame_id, session, body=None, mode="LIVE"):
    return client.post("/api/frame", content=body or jpeg(),
                       headers={"x-session-id": session, "x-frame-id": str(frame_id), "x-input-mode": mode})


FULL = {"image_points": [[0, 0], [1, 0], [1, 1], [0, 1]]}
BOX_IN_A = (256, 58, 320, 115)   # 640x480 frame -> map x 40..50, y 6.7..13.4


def test_synthetic_block_reroutes(ctx):
    client, _ = ctx
    state = client.post("/api/orders").json()
    assert state["vehicle"]["route"][:3] == ["S", "W", "A1"]
    state = client.post("/api/sim/zone", json={"zone_id": "A", "state": "BLOCKED"}).json()
    assert "B1" in state["vehicle"]["route"] and state["mode"] == "SYNTHETIC"
    state = client.post("/api/sim/zone", json={"zone_id": "B", "state": "BLOCKED"}).json()
    vehicle = state["vehicle"]
    assert vehicle["route"] == ["S", "W"] and vehicle["estimated_remaining_s"] is None
    assert "no feasible route" in vehicle["reason"]


def test_frames_rejected_in_synthetic_mode_and_manual_control_rejected_in_live(ctx):
    client, _ = ctx
    session = client.get("/api/state").json()["session_id"]
    assert send(client, 1, session).status_code == 409
    client.post("/api/demo/reset", json={"mode": "LIVE"})
    assert client.post("/api/sim/zone", json={"zone_id": "A", "state": "BLOCKED"}).status_code == 409


def test_live_detection_blocks_zone_with_evidence(ctx):
    client, detector = ctx
    client.post("/api/calibration", json=FULL)
    session = client.post("/api/demo/reset", json={"mode": "LIVE"}).json()["session_id"]
    detector.boxes = [BOX_IN_A]
    for i in range(1, 4):
        r = send(client, i, session)
        assert r.status_code == 200
    body = r.json()
    zone = body["state"]["zones"]["A"]
    assert zone["state"] == "BLOCKED" and body["detections"][0]["zones"] == ["A"]
    assert client.get("/api/evidence/" + zone["evidence_id"]).status_code == 200
    assert client.get("/api/metrics").json()["frames_analyzed"] == 3


def test_uncalibrated_or_dark_frames_are_unknown(ctx):
    client, detector = ctx
    session = client.post("/api/demo/reset", json={"mode": "LIVE"}).json()["session_id"]
    r = send(client, 1, session).json()
    assert r["state"]["view"]["reason"] == "camera not calibrated"
    client.post("/api/calibration", json=FULL)
    r = send(client, 2, session, jpeg(dark=True)).json()
    assert not r["state"]["view"]["ok"] and r["state"]["zones"]["A"]["state"] == "UNKNOWN"


def test_old_session_out_of_order_and_oversized_frames_rejected(ctx):
    client, _ = ctx
    old = client.post("/api/demo/reset", json={"mode": "LIVE"}).json()["session_id"]
    assert send(client, 5, old).status_code == 200
    assert send(client, 5, old).status_code == 409
    assert send(client, 6, old, b"x" * 2_000_000).status_code == 413
    assert send(client, 7, old, b"not an image").status_code == 400
    client.post("/api/demo/reset", json={"mode": "LIVE"})
    assert send(client, 8, old).status_code == 409


def test_comparison_includes_a_case_where_waiting_wins(ctx):
    client, _ = ctx
    result = client.get("/api/comparison").json()
    assert {"dynamic", "static"} <= {r["faster"] for r in result["rows"]}
    assert all(r["static"]["completed"] and r["dynamic"]["completed"] for r in result["rows"])


def test_switching_use_case_changes_the_map_and_starts_a_new_session(ctx):
    client, _ = ctx
    assert [m["id"] for m in client.get("/api/maps").json()] == ["warehouse", "crossdock", "factory"]
    before = client.get("/api/state").json()
    state = client.post("/api/map", json={"id": "factory"}).json()
    assert state["map_id"] == "factory" and state["session_id"] != before["session_id"]
    assert client.get("/api/map").json()["name"] == "Factory line-side delivery"
    state = client.post("/api/orders").json()
    assert state["vehicle"]["route"] == ["K", "J1", "J2", "X", "L"]
    state = client.post("/api/sim/zone", json={"zone_id": "A", "state": "BLOCKED"}).json()
    assert "N1" in state["vehicle"]["route"]
    assert client.post("/api/map", json={"id": "nope"}).status_code == 422


def test_bad_calibration_is_422(ctx):
    client, _ = ctx
    bad = {"image_points": [[0, 0], [1, 1], [1, 0], [0, 1]]}
    assert client.post("/api/calibration", json=bad).status_code == 422


def test_operator_pause_holds_the_vehicle_and_resume_releases_it(ctx):
    client, _ = ctx
    client.post("/api/orders")
    state = client.post("/api/sim/pause", json={"paused": True}).json()
    assert state["vehicle"]["status"] == "PAUSED_OPERATOR" and state["vehicle"]["held"]
    state = client.post("/api/sim/pause", json={"paused": False}).json()
    assert state["vehicle"]["status"] == "MOVING" and not state["vehicle"]["held"]
    assert client.post("/api/demo/reset").json()["vehicle"]["held"] is False


def test_held_out_calibration_check_reports_map_error(ctx):
    client, _ = ctx
    assert client.post("/api/calibration/check", json={"image": [0.5, 0.5], "map": [50, 28]}).status_code == 409
    client.post("/api/calibration", json=FULL)
    exact = client.post("/api/calibration/check", json={"image": [0.5, 0.5], "map": [50, 28]}).json()
    off = client.post("/api/calibration/check", json={"image": [0.6, 0.5], "map": [50, 28]}).json()
    assert exact["error_map_units"] == 0 and off["error_map_units"] == 10
    assert client.post("/api/calibration/check", json={"image": [0.5, 0.5]}).status_code == 422


def test_malformed_bodies_are_422_not_500(ctx):
    client, _ = ctx
    for path in ("/api/map", "/api/sim/zone", "/api/calibration", "/api/demo/reset"):
        r = client.post(path, content=b"{not json", headers={"content-type": "application/json"})
        assert r.status_code == 422, path
    assert client.post("/api/map", json=[1, 2]).status_code == 422


def test_view_goes_stale_even_when_zones_are_already_unknown(ctx):
    import time

    client, _ = ctx
    client.post("/api/calibration", json=FULL)
    session = client.post("/api/demo/reset", json={"mode": "LIVE"}).json()["session_id"]
    world = client.app.state.world
    assert send(client, 1, session).json()["state"]["view"]["ok"]      # one good frame: zones still UNKNOWN
    assert world.occupancy.states()["A"].value == "UNKNOWN"
    world.step(time.monotonic() + 10, 0.1)                               # no frame for 10 s
    state = client.get("/api/state").json()
    assert state["view"] == {"ok": False, "reason": "no fresh camera frame"}


def test_supported_classes_can_be_overridden_from_the_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("FLOWTWIN_CLASSES", "cell phone, scissors")
    with TestClient(create_app(tmp_path, FakeDetector(), run_ticker=False)) as client:
        assert client.get("/api/status").json()["thresholds"]["supported_classes"] == ["cell phone", "scissors"]


def test_gpu_endpoint_reports_device_facts_and_stage_latency(ctx):
    client, detector = ctx
    detector.last_stages = {"preprocess_ms": 1.0, "model_ms": 5.0, "postprocess_ms": 0.5}
    client.post("/api/calibration", json=FULL)
    session = client.post("/api/demo/reset", json={"mode": "LIVE"}).json()["session_id"]
    timings = send(client, 1, session).json()["timings"]
    assert timings["model_ms"] == 5.0
    report = client.get("/api/gpu").json()
    assert report["latency"]["model_ms"]["p50_ms"] == 5.0 and report["frames_analyzed"] == 1
    assert isinstance(report["info"]["cuda_available"], bool) and report["detector"]["backend"] == "TEST"


def run_world(world, seconds):
    import time

    now = time.monotonic()
    for _ in range(int(seconds * 10)):
        world.step(now, 0.1)


def test_operations_run_a_mixed_fleet_orders_trucks_and_stock(ctx):
    client, _ = ctx
    world = client.app.state.world
    before = client.get("/api/inventory").json()
    assert before["source"] == "SIMULATED" and len(before["racks"]) == 5 and 0 < before["fill"] < 1
    idle = client.get("/api/state").json()
    assert idle["fleet"]["enabled"] is False and idle["fleet"]["vehicles"] == [] and idle["ops"]["orders"] == []

    state = client.post("/api/fleet", json={"enabled": True}).json()
    assert [(v["id"], v["kind"]) for v in state["fleet"]["vehicles"]] == [
        ("V2", "tugger"), ("V3", "forklift"), ("V4", "amr"), ("V5", "amr"), ("V6", "forklift")]
    run_world(world, 150)
    state = client.get("/api/state").json()
    ops, kpis = state["ops"], state["kpis"]
    assert kpis["deliveries"] >= 10 and kpis["avg_delivery_s"] > 10
    assert all(v["legs_done"] >= 2 for v in state["fleet"]["vehicles"])
    assert ops["counts"]["DISPATCHED"] >= 4 and ops["trucks_departed"] >= 1 and ops["inbound_deliveries"] >= 3
    assert 0 <= ops["truck_load"] < ops["truck_capacity"]
    assert ops["orders"][0]["status"] in ("QUEUED", "IN_TRANSIT", "PACKED", "DISPATCHED")
    assert {"id", "product", "sku", "slot", "units", "status", "vehicle"} == set(ops["orders"][0])
    assert ops["traffic"] and max(ops["traffic"].values()) == 1.0
    kinds = {e["kind"] for e in client.get("/api/events?limit=500").json()}
    assert "truck" in kinds

    history = client.get("/api/analytics").json()["history"]
    assert len(history) >= 60 and history[-1]["t"] > history[0]["t"]
    assert max(h["throughput_per_min"] for h in history) >= 2 and max(h["utilisation_pct"] for h in history) > 0
    assert set(history[-1]) == {"t", "throughput_per_min", "utilisation_pct", "paused", "queue",
                                "stock_fill_pct", "blocked_zones"}
    assert client.post("/api/fleet", json={"enabled": False}).json()["fleet"]["vehicles"] == []


def test_fleet_respects_blocked_zones_and_raises_alerts(ctx):
    client, _ = ctx
    world = client.app.state.world
    client.post("/api/fleet", json={"enabled": True})
    client.post("/api/sim/zone", json={"zone_id": "A", "state": "BLOCKED"})
    import time

    now, seen = time.monotonic(), set()
    for _ in range(600):
        world.step(now, 0.1)
        for v in world.ops.vehicles:
            sim = v["sim"]
            if sim.next:
                seen.add(world.map.edge_zone(sim.node, sim.next))
    assert "B" in seen and "A" not in seen
    state = client.get("/api/state").json()
    assert state["kpis"]["blocked_events"] == 1 and state["kpis"]["deliveries"] >= 1
    assert {"level": "critical", "text": "Aisle A is BLOCKED"} in state["ops"]["alerts"]
    assert all("A1-A2" != edge for edge in state["ops"]["traffic"])


def test_inbound_truck_replenishes_the_emptiest_slots(ctx):
    client, _ = ctx
    inventory = client.app.state.world.inventory
    for rack in inventory.racks:
        for slot in rack["slots"][:2]:
            slot["qty"] = 0
    before = inventory.snapshot()["units"]
    added = inventory.replenish(slots=4)
    assert added > 0 and inventory.snapshot()["units"] == before + added
    assert inventory.take()["units"] >= 1


