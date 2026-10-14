"""Checks for the GPU code that can run without a GPU. Needs ultralytics and local weights; skipped otherwise."""
from pathlib import Path

import numpy as np
import pytest

from app.gpu import gpu_info, gpu_stats

WEIGHTS = Path(__file__).resolve().parent.parent / "data" / "models" / "yolo11n.pt"


def test_gpu_report_is_honest_without_a_gpu():
    info, stats = gpu_info(), gpu_stats()
    assert isinstance(info["cuda_available"], bool)
    if not info["cuda_available"]:
        assert info["device"] is None and stats == {"cuda_available": False}
    else:
        assert stats["device_total_mb"] > 0 and "utilization_source" in stats


def test_letterbox_on_device_shape_range_and_mapping():
    torch = pytest.importorskip("torch")
    from app.perception import PAD_VALUE, letterbox_on_device

    image = np.zeros((360, 640, 3), dtype=np.uint8)
    image[..., 0] = 255                                   # pure blue in BGR
    tensor, scale, left, top = letterbox_on_device(image, 640, torch.device("cpu"), torch)
    assert tuple(tensor.shape) == (1, 3, 640, 640) and (scale, left, top) == (1.0, 0, 140)
    assert float(tensor.min()) >= 0 and float(tensor.max()) <= 1
    assert tensor[0, :, 0, 0].tolist() == pytest.approx([PAD_VALUE / 255] * 3)   # padding rows
    assert tensor[0, :, 320, 320].tolist() == pytest.approx([0, 0, 1])           # RGB order: blue is last


@pytest.mark.skipif(not WEIGHTS.exists(), reason="local weights not downloaded")
def test_device_preprocessing_matches_the_standard_path():
    pytest.importorskip("ultralytics")
    import cv2
    from ultralytics.utils import ASSETS

    from app.perception import UltralyticsDetector

    image = cv2.imread(str(ASSETS / "bus.jpg"))
    standard = UltralyticsDetector(str(WEIGHTS), 0.35, 640)
    on_device = UltralyticsDetector(str(WEIGHTS), 0.35, 640, gpu_preprocess=True)
    a, _ = standard.predict(image)
    b, _ = on_device.predict(image)
    assert sorted(d.cls for d in a) == sorted(d.cls for d in b)
    bus_a = next(d for d in a if d.cls == "bus")
    bus_b = next(d for d in b if d.cls == "bus")
    assert np.abs(np.array(bus_a.box) - np.array(bus_b.box)).max() < 12      # pixels, on an 810x1080 image
    assert abs(bus_a.conf - bus_b.conf) < 0.05
    assert set(on_device.last_stages) == {"preprocess_ms", "model_ms", "postprocess_ms"}
    assert on_device.info["preprocess"] == "on device" and on_device.info["half"] is False
