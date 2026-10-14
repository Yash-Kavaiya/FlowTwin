"""Compare inference configurations on the same held-out frames. Run on the Jetson, inside the GPU window.

Usage:
  python3 scripts/bench.py --images data/heldout \\
      --weights /cache/flowtwin/yolo11n.pt /cache/flowtwin/yolo11n.engine [--variants]

Without --variants each weights file is measured once (FP32, CPU letterbox). With --variants a .pt file is
also measured with FP16 and with on-device preprocessing, and an engine with on-device preprocessing.
Every configuration shares image size, confidence, postprocessing and warmup (they all use UltralyticsDetector).
Times are CUDA-synchronized. "call" is the whole prediction call; "model" is model execution only.
"""
import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.gpu import gpu_info, gpu_stats  # noqa: E402
from app.perception import UltralyticsDetector  # noqa: E402


def configurations(weights: list[str], variants: bool, cuda: bool) -> list[dict]:
    out = []
    for w in weights:
        out.append({"weights": w, "half": False, "gpu_preprocess": False})
        if variants:
            if w.endswith(".pt") and cuda:
                out.append({"weights": w, "half": True, "gpu_preprocess": False})
            out.append({"weights": w, "half": False, "gpu_preprocess": True})
            if w.endswith(".pt") and cuda:
                out.append({"weights": w, "half": True, "gpu_preprocess": True})
    return out


def pct(values, q) -> float:
    return round(float(np.percentile(values, q)), 1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--images", required=True, help="folder of held-out .jpg/.png frames")
    parser.add_argument("--weights", nargs="+", required=True)
    parser.add_argument("--passes", type=int, default=5, help="timed passes over the image set")
    parser.add_argument("--variants", action="store_true", help="also measure FP16 and on-device preprocessing")
    args = parser.parse_args()

    import torch

    th = json.loads((ROOT / "config" / "thresholds.json").read_text())
    paths = sorted(p for p in Path(args.images).iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    images = [cv2.imread(str(p)) for p in paths]
    if not images:
        sys.exit("no images found")
    cuda = torch.cuda.is_available()

    rows, reference = [], None
    for cfg in configurations(args.weights, args.variants, cuda):
        if cuda:
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()
        detector = UltralyticsDetector(cfg["weights"], th["conf"], th["imgsz"], cfg["half"], cfg["gpu_preprocess"])
        for image in images[:10]:  # extra warmup on real frames
            detector.predict(image)
        call, model, pre, found = [], [], [], []
        started = time.perf_counter()
        for _ in range(args.passes):
            found = []
            for image in images:
                detections, ms = detector.predict(image)
                call.append(ms)
                model.append(detector.last_stages["model_ms"])
                pre.append(detector.last_stages["preprocess_ms"])
                found.append(Counter(d.cls for d in detections))
        wall = time.perf_counter() - started
        if reference is None:
            reference = found
        stats = gpu_stats()
        rows.append((
            detector.info["backend"], detector.info["model"], "device" if cfg["gpu_preprocess"] else "CPU",
            len(call), pct(call, 50), pct(call, 95), pct(model, 50), pct(pre, 50), round(len(call) / wall, 1),
            stats.get("process_peak_allocated_mb", "n/a"), stats.get("device_used_mb", "n/a"),
            f"{sum(a != b for a, b in zip(reference, found))}/{len(images)}",
        ))
        del detector

    info = gpu_info()
    print(f"Device: {info['device'] or 'CPU only (no CUDA)'}. PyTorch {info['torch']}, CUDA {info['cuda_runtime']}, "
          f"TensorRT {info['tensorrt']}. {len(images)} held-out frames, imgsz {th['imgsz']}, conf {th['conf']}, "
          f"{args.passes} passes.\n")
    header = ("backend", "model", "preprocess", "calls", "call p50 ms", "call p95 ms", "model p50 ms",
              "preprocess p50 ms", "sustained calls/s", "peak PyTorch GPU MB", "device GPU MB in use",
              "frames differing from first row")
    print("| " + " | ".join(header) + " |")
    print("|" + "---|" * len(header))
    for row in rows:
        print("| " + " | ".join(str(v) for v in row) + " |")
    print("\nPeak PyTorch GPU memory excludes TensorRT allocations; for an engine read the device column. "
          "The device column includes other processes on a shared GPU. "
          "'Frames differing' counts frames whose set of detected classes differs from the first row.")


if __name__ == "__main__":
    main()
