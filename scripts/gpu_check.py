"""First thing to run on the Jetson: prove real GPU inference before anything else is built on it.

Usage: python3 scripts/gpu_check.py [weights] [image]
Defaults: /cache/flowtwin/yolo11n.pt and the sample image shipped with Ultralytics.

Read-only apart from caching the weights if they are missing. Exits non-zero when CUDA is unavailable
(pass --allow-cpu to run the same checks on a laptop).
"""
import os
import sys
from pathlib import Path

os.environ["YOLO_AUTOINSTALL"] = "False"  # never let Ultralytics touch the protected stack

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.gpu import gpu_info, gpu_stats  # noqa: E402


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    allow_cpu = "--allow-cpu" in sys.argv
    weights = args[0] if args else "/cache/flowtwin/yolo11n.pt"

    info = gpu_info()
    print("## Environment")
    for key, value in info.items():
        print(f"- {key}: {value}")
    if not info["cuda_available"] and not allow_cpu:
        print("\nCUDA is not available. Contact the organizers; do not reinstall PyTorch.")
        return 1

    import cv2
    import numpy as np
    import torch
    from ultralytics.utils import ASSETS

    from app.perception import UltralyticsDetector

    image_path = args[1] if len(args) > 1 else str(ASSETS / "bus.jpg")
    image = cv2.imread(image_path)
    if image is None:
        print(f"\nCannot read image {image_path}")
        return 1

    print(f"\n## Inference on {image_path}")
    results = {}
    for name, options in (("baseline", {}), ("on-device preprocessing", {"gpu_preprocess": True}),
                          ("FP16", {"half": True})):
        if name == "FP16" and (not info["cuda_available"] or weights.endswith(".engine")):
            continue
        detector = UltralyticsDetector(weights, 0.35, 640, **options)  # warms up three times
        times = []
        for _ in range(20):
            detections, ms = detector.predict(image)
            times.append(ms)
        device = next(detector.model.model.parameters()).device if weights.endswith(".pt") else detector.info["device"]
        results[name] = sorted(d.cls for d in detections)
        print(f"- {name}: backend {detector.info['backend']}, model on {device}, "
              f"call p50 {np.percentile(times, 50):.1f} ms, p95 {np.percentile(times, 95):.1f} ms, "
              f"model stage {detector.last_stages['model_ms']:.1f} ms on the last call, "
              f"{len(detections)} detections: {', '.join(results[name]) or 'none'}")
        del detector
        if info["cuda_available"]:
            torch.cuda.empty_cache()

    print("\n## GPU after inference")
    for key, value in gpu_stats().items():
        print(f"- {key}: {value}")

    baseline = results["baseline"]
    mismatched = [name for name, found in results.items() if found != baseline]
    if not baseline:
        print("\nNo detections on the test image: check the weights and the image before going further.")
        return 1
    if mismatched:
        print(f"\nNote: {', '.join(mismatched)} detected a different set of classes than the baseline. "
              "Compare on your own frames with scripts/bench.py before enabling it.")
    print("\nGPU inference verified." if info["cuda_available"] else "\nChecks passed on CPU (no GPU claim).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
