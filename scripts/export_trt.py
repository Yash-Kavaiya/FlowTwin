"""Build a TensorRT FP16 engine from the working .pt weights. Run on the Jetson, inside the GPU window.

Usage: python3 scripts/export_trt.py /cache/flowtwin/yolo11n.pt
The .pt file is kept. Engines are specific to this device and TensorRT version.
"""
import os
import sys

os.environ["YOLO_AUTOINSTALL"] = "False"  # never let the exporter touch the protected stack

import tensorrt  # noqa: E402  fail early if TensorRT is not importable
from ultralytics import YOLO  # noqa: E402
from ultralytics.cfg import DEFAULT_CFG_DICT  # noqa: E402


def main() -> None:
    weights = sys.argv[1] if len(sys.argv) > 1 else "/cache/flowtwin/yolo11n.pt"
    print("TensorRT", tensorrt.__version__, "exporting", weights)
    # Recent Ultralytics releases use quantize; older ones use half.
    precision = {"quantize": 16} if "quantize" in DEFAULT_CFG_DICT else {"half": True}
    engine = YOLO(weights).export(format="engine", device=0, imgsz=640, batch=1, dynamic=False,
                                  workspace=1, simplify=False, **precision)
    print("engine written to", engine)
    print(f"serve it with: FLOWTWIN_MODEL={engine} uvicorn app.main:app --host 0.0.0.0 --port 8000")


if __name__ == "__main__":
    main()
