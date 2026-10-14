"""Rolling measurements. Only measured values are reported; nothing is hardcoded."""
from __future__ import annotations

from collections import deque

import numpy as np


class Metrics:
    def __init__(self, window: int = 300):
        self.window = window
        self.series: dict[str, deque] = {}
        self.frames = 0
        self.rejected = 0

    def record(self, **values_ms: float) -> None:
        for name, value in values_ms.items():
            self.series.setdefault(name, deque(maxlen=self.window)).append(float(value))

    def summary(self) -> dict:
        out = {}
        for name, values in self.series.items():
            arr = np.asarray(values)
            out[name] = {"n": len(arr), "p50_ms": round(float(np.percentile(arr, 50)), 1),
                         "p95_ms": round(float(np.percentile(arr, 95)), 1)}
        return out
