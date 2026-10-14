"""Detector adapter. PyTorch and TensorRT share this class, so postprocessing is identical.

GPU options (environment variables, all off by default so the plain CUDA path stays the baseline):
  FLOWTWIN_MODEL=/path/model.pt|.engine   weights; unset means the mock detector
  FLOWTWIN_HALF=1                         FP16 for the PyTorch model on CUDA (ignored on CPU)
  FLOWTWIN_GPU_PREPROCESS=1               resize, pad and normalize on the device instead of the CPU
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass

PAD_VALUE = 114.0  # the gray Ultralytics pads letterboxed images with


@dataclass
class Detection:
    cls: str
    conf: float
    box: tuple[float, float, float, float]  # x1, y1, x2, y2 in pixels of the analyzed frame


class MockDetector:
    """No model. Used for laptop development; it never reports an object."""

    info = {"model": "none", "backend": "MOCK (no model loaded)", "device": "cpu", "gpu": None}
    last_stages: dict[str, float] = {}

    def predict(self, image_bgr) -> tuple[list[Detection], float]:
        return [], 0.0


def letterbox_on_device(image_bgr, size: int, device, torch):
    """HxWx3 uint8 BGR array -> 1x3xSxS float RGB tensor in 0..1 on the device, plus the mapping back.

    The frame is uploaded once as uint8 and everything else (channel swap, resize, pad, scale) runs on the device.
    Returns (tensor, scale, pad_left, pad_top); original x = (x - pad_left) / scale.
    """
    height, width = image_bgr.shape[:2]
    scale = min(size / height, size / width)
    new_h, new_w = round(height * scale), round(width * scale)
    frame = torch.from_numpy(image_bgr).to(device, non_blocking=True)
    frame = frame.permute(2, 0, 1).flip(0).unsqueeze(0).float()  # HWC BGR -> 1x3xHxW RGB
    if (new_h, new_w) != (height, width):
        frame = torch.nn.functional.interpolate(frame, size=(new_h, new_w), mode="bilinear",
                                                align_corners=False, antialias=scale < 1)
    pad_h, pad_w = size - new_h, size - new_w
    top, left = pad_h // 2, pad_w // 2
    frame = torch.nn.functional.pad(frame, (left, pad_w - left, top, pad_h - top), value=PAD_VALUE)
    return frame.div_(255.0), scale, left, top


class UltralyticsDetector:
    def __init__(self, weights: str, conf: float, imgsz: int, half: bool = False, gpu_preprocess: bool = False):
        os.environ.setdefault("YOLO_AUTOINSTALL", "False")
        import numpy as np
        import torch
        from ultralytics import YOLO

        self._torch = torch
        self.conf, self.imgsz = conf, imgsz
        self.cuda = torch.cuda.is_available()
        self.device = 0 if self.cuda else "cpu"
        self.torch_device = torch.device("cuda:0" if self.cuda else "cpu")
        engine = weights.endswith(".engine")
        self.half = half and self.cuda and not engine  # an engine carries its own precision
        self.gpu_preprocess = gpu_preprocess
        if self.cuda:
            torch.backends.cudnn.benchmark = True  # fixed input size, so let cuDNN pick the fastest kernels
        self.model = YOLO(weights, task="detect")
        # FP16 is only passed when requested; recent Ultralytics releases name it quantize, older ones half.
        from ultralytics.cfg import DEFAULT_CFG_DICT
        self._precision = {}
        if self.half:
            self._precision = {"quantize": 16} if "quantize" in DEFAULT_CFG_DICT else {"half": True}
        if engine:
            backend = "TensorRT"
        elif self.cuda:
            backend = "PyTorch CUDA FP16" if self.half else "PyTorch CUDA"
        else:
            backend = "PyTorch CPU"
        self.info = {
            "model": os.path.basename(weights), "backend": backend,
            "device": "cuda:0" if self.cuda else "cpu",
            "gpu": torch.cuda.get_device_name(0) if self.cuda else None,
            "torch": torch.__version__, "imgsz": imgsz, "conf": conf, "half": self.half,
            "preprocess": "on device" if gpu_preprocess else "CPU (Ultralytics letterbox)",
        }
        self.last_stages: dict[str, float] = {}
        for _ in range(3):  # warm up before serving: first calls include kernel selection and lazy allocation
            self.predict(np.zeros((imgsz, imgsz, 3), dtype=np.uint8))

    def _sync(self) -> None:
        if self.cuda:
            self._torch.cuda.synchronize()

    def predict(self, image_bgr) -> tuple[list[Detection], float]:
        """Returns detections and the whole prediction-call time in ms (pre/postprocessing included).

        Per-stage times are left in last_stages. All timing brackets are CUDA-synchronized.
        """
        self._sync()
        started = time.perf_counter()
        own_pre_ms, scale, left, top = 0.0, 1.0, 0, 0
        source = image_bgr
        if self.gpu_preprocess:
            source, scale, left, top = letterbox_on_device(image_bgr, self.imgsz, self.torch_device, self._torch)
            self._sync()
            own_pre_ms = (time.perf_counter() - started) * 1000
        result = self.model.predict(source=source, device=self.device, imgsz=self.imgsz, conf=self.conf,
                                    rect=False, verbose=False, **self._precision)[0]
        self._sync()
        elapsed_ms = (time.perf_counter() - started) * 1000
        speed = result.speed or {}
        self.last_stages = {
            "preprocess_ms": own_pre_ms + float(speed.get("preprocess") or 0.0),
            "model_ms": float(speed.get("inference") or 0.0),
            "postprocess_ms": float(speed.get("postprocess") or 0.0),
        }
        names = result.names
        detections = []
        for b in result.boxes:
            x1, y1, x2, y2 = (float(v) for v in b.xyxy[0].tolist())
            if self.gpu_preprocess:  # boxes come back in letterboxed coordinates
                x1, x2 = (x1 - left) / scale, (x2 - left) / scale
                y1, y2 = (y1 - top) / scale, (y2 - top) / scale
            detections.append(Detection(names[int(b.cls.item())], float(b.conf.item()), (x1, y1, x2, y2)))
        return detections, elapsed_ms


def _flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def make_detector(conf: float, imgsz: int):
    """FLOWTWIN_MODEL selects the weights (.pt or .engine). Unset means the mock detector."""
    weights = os.environ.get("FLOWTWIN_MODEL")
    if not weights:
        return MockDetector()
    return UltralyticsDetector(weights, conf, imgsz, half=_flag("FLOWTWIN_HALF"),
                               gpu_preprocess=_flag("FLOWTWIN_GPU_PREPROCESS"))
