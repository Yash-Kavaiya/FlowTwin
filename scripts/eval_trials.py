"""Event-level evaluation of recorded trial clips through the real pipeline (detector, calibration, occupancy).

Usage: python3 scripts/eval_trials.py data/trials/manifest.json [map_id]
Manifest: {"trials": [{"file": "a_01.mp4", "category": "block A",
                       "expect_final": {"A": "BLOCKED", "B": "CLEAR", "C": "CLEAR"},
                       "must_visit": {"A": "BLOCKED"},          (optional, for recovery trials)
                       "event_time_s": 2.0}]}                   (optional, when the object was placed or removed)
Each clip is one trial. Adjacent frames are never counted as separate trials.
Uses data/calibration.json, so record the clips with the camera in its calibrated position.
Set FLOWTWIN_MODEL to the weights; without it the mock detector runs and nothing is ever detected.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.calibration import Calibration, frame_quality  # noqa: E402
from app.occupancy import Occupancy  # noqa: E402
from app.perception import make_detector  # noqa: E402
from app.planner import DEFAULT_MAP, load_maps  # noqa: E402

ANALYZE_FPS = 5.0


def run_clip(path: Path, detector, calibration, wmap, th) -> dict:
    occ = Occupancy(wmap.zones, th["block_frames"], th["clear_frames"], th["clear_seconds"], th["stale_seconds"])
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise SystemExit(f"cannot open {path}")
    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, round(fps / ANALYZE_FPS))
    transitions, index = [], 0
    while True:
        ok, image = capture.read()
        if not ok:
            break
        if index % step == 0:
            t = index / fps
            height, width = image.shape[:2]
            quality = frame_quality(image, th["min_brightness"], th["min_sharpness"])
            obstructed = set()
            if quality["ok"]:
                for d in detector.predict(image)[0]:
                    if d.cls in th["supported_classes"]:
                        box_n = [d.box[0] / width, d.box[1] / height, d.box[2] / width, d.box[3] / height]
                        obstructed.update(calibration.zones_for_box(box_n, wmap.zones, th["min_zone_overlap"]))
            for tr in occ.observe(t, obstructed, quality["ok"], quality["reason"]):
                transitions.append({"t": round(t, 2), "zone": tr.zone_id, "old": tr.old.value, "new": tr.new.value})
        index += 1
    capture.release()
    return {"final": {z: s.value for z, s in occ.states().items()}, "transitions": transitions}


def main() -> None:
    manifest_path = Path(sys.argv[1])
    manifest = json.loads(manifest_path.read_text())
    wmap = load_maps()[sys.argv[2] if len(sys.argv) > 2 else DEFAULT_MAP]
    th = json.loads((ROOT / "config" / "thresholds.json").read_text())
    saved = json.loads((ROOT / "data" / "calibration.json").read_text())
    calibration = Calibration(saved["version"], saved["image_points"], wmap.data["width"], wmap.data["height"])
    detector = make_detector(th["conf"], th["imgsz"])

    summary = defaultdict(lambda: {"n": 0, "correct": 0, "false_block": 0, "false_clear": 0, "delays": []})
    details = []
    for trial in manifest["trials"]:
        result = run_clip(manifest_path.parent / trial["file"], detector, calibration, wmap, th)
        expect = trial["expect_final"]
        visited = {(t["zone"], t["new"]) for t in result["transitions"]}
        correct = all(result["final"].get(z) == s for z, s in expect.items()) and \
            all((z, s) in visited for z, s in trial.get("must_visit", {}).items())
        row = summary[trial["category"]]
        row["n"] += 1
        row["correct"] += correct
        # A zone that ended BLOCKED but should not have, and the reverse (the dangerous direction).
        row["false_block"] += any(result["final"][z] == "BLOCKED" and s != "BLOCKED" for z, s in expect.items())
        row["false_clear"] += any(result["final"][z] == "CLEAR" and s == "BLOCKED" for z, s in expect.items())
        if "event_time_s" in trial:
            after = [t["t"] for t in result["transitions"]
                     if t["t"] >= trial["event_time_s"] and expect.get(t["zone"]) == t["new"]]
            if after:
                row["delays"].append(after[0] - trial["event_time_s"])
        details.append({**trial, **result, "correct": correct})

    print(f"Detector: {detector.info['backend']} {detector.info['model']}. Thresholds v{th['version']}: "
          f"block after {th['block_frames']} frames, clear after {th['clear_seconds']} s. "
          f"Supported classes: {', '.join(th['supported_classes'])}.\n")
    print("| category | correct trials | false blocks | false clears | median time to expected state (s) |")
    print("|---|---|---|---|---|")
    for category, row in summary.items():
        delays = sorted(row["delays"])
        median = f"{delays[len(delays) // 2]:.1f} (n={len(delays)})" if delays else "not measured"
        print(f"| {category} | {row['correct']}/{row['n']} | {row['false_block']}/{row['n']} | "
              f"{row['false_clear']}/{row['n']} | {median} |")
    out = manifest_path.with_name("results.json")
    out.write_text(json.dumps(details, indent=2))
    print(f"\nPer-trial transitions written to {out}")


if __name__ == "__main__":
    main()
