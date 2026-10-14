"""GPU facts and live measurements. Every value is read from the device; nothing is assumed.

Works without a GPU (reports cuda_available: false) so the same code runs on a laptop.
"""
from __future__ import annotations

import shutil
import subprocess
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

# Jetson boards expose GPU load in sysfs as 0..1000; the path differs by board and release.
_SYSFS_LOAD = (
    "/sys/devices/platform/gpu.0/load",
    "/sys/devices/gpu.0/load",
    "/sys/devices/platform/bus@0/17000000.gpu/load",
    "/sys/devices/platform/17000000.gpu/load",
)
_UTIL_CACHE_S = 1.0
_util_cache: tuple[float, dict] | None = None


def _torch():
    try:
        import torch
        return torch
    except ImportError:
        return None


def _package(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def gpu_info() -> dict:
    """Static description of the accelerator and the installed NVIDIA stack."""
    torch = _torch()
    info = {
        "cuda_available": False, "device": None, "torch": None, "cuda_runtime": None, "cudnn": None,
        "total_memory_mb": None, "tensorrt": _package("tensorrt"), "ultralytics": _package("ultralytics"),
    }
    if torch is None:
        return info
    info["torch"] = torch.__version__
    info["cuda_available"] = bool(torch.cuda.is_available())
    if info["cuda_available"]:
        props = torch.cuda.get_device_properties(0)
        info.update(
            device=torch.cuda.get_device_name(0), cuda_runtime=torch.version.cuda,
            cudnn=torch.backends.cudnn.version(), total_memory_mb=round(props.total_memory / 2**20),
            capability=".".join(str(v) for v in torch.cuda.get_device_capability(0)),
        )
    return info


def _utilization() -> dict:
    """GPU load in percent with the source it came from, or None when the platform does not expose it."""
    global _util_cache
    now = time.monotonic()
    if _util_cache and now - _util_cache[0] < _UTIL_CACHE_S:
        return _util_cache[1]
    result = {"utilization_pct": None, "utilization_source": "not exposed by this platform"}
    for path in _SYSFS_LOAD:
        try:
            result = {"utilization_pct": round(int(Path(path).read_text().strip()) / 10, 1), "utilization_source": path}
            break
        except (OSError, ValueError):
            continue
    else:
        if shutil.which("nvidia-smi"):
            try:
                out = subprocess.run(
                    ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=2, check=True,
                ).stdout.strip().splitlines()[0]
                result = {"utilization_pct": float(out), "utilization_source": "nvidia-smi"}
            except (OSError, subprocess.SubprocessError, ValueError, IndexError):
                pass  # nvidia-smi prints [N/A] on some Jetson releases
    _util_cache = (now, result)
    return result


def gpu_stats() -> dict:
    """Live memory and load. Memory figures are for this process unless named otherwise."""
    torch = _torch()
    if torch is None or not torch.cuda.is_available():
        return {"cuda_available": False}
    free, total = torch.cuda.mem_get_info(0)
    mb = 2**20
    return {
        "cuda_available": True,
        "process_allocated_mb": round(torch.cuda.memory_allocated(0) / mb, 1),
        "process_reserved_mb": round(torch.cuda.memory_reserved(0) / mb, 1),
        "process_peak_allocated_mb": round(torch.cuda.max_memory_allocated(0) / mb, 1),
        "device_used_mb": round((total - free) / mb), "device_total_mb": round(total / mb),
        "memory_note": "process figures cover PyTorch allocations only; a TensorRT engine allocates outside them, "
                       "so use device_used_mb for TensorRT",
        **_utilization(),
    }
