"""Planar image-to-map calibration, zone overlap and frame-quality checks.

Image points are normalized (0..1) so they do not depend on the capture size.
A 2D box is not a 3D footprint: keep props low and near the calibrated plane.
"""
from __future__ import annotations

import numpy as np


def compute_homography(src, dst) -> np.ndarray:
    """Direct linear transform from four (or more) src points to dst points."""
    rows = []
    for (x, y), (u, v) in zip(src, dst):
        rows.append([-x, -y, -1, 0, 0, 0, u * x, u * y, u])
        rows.append([0, 0, 0, -x, -y, -1, v * x, v * y, v])
    _, _, vt = np.linalg.svd(np.asarray(rows, dtype=float))
    h = vt[-1].reshape(3, 3)
    return h / h[2, 2]


def apply_h(h: np.ndarray, points) -> np.ndarray:
    pts = np.asarray(points, dtype=float).reshape(-1, 2)
    out = np.hstack([pts, np.ones((len(pts), 1))]) @ h.T
    return out[:, :2] / out[:, 2:3]


def _quad_area(points) -> float:
    p = np.asarray(points, dtype=float)
    x, y = p[:, 0], p[:, 1]
    return 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def _is_convex(points) -> bool:
    p = np.asarray(points, dtype=float)
    signs = []
    for i in range(4):
        a, b, c = p[i], p[(i + 1) % 4], p[(i + 2) % 4]
        signs.append(np.sign((b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])))
    return all(s > 0 for s in signs) or all(s < 0 for s in signs)


def point_in_polygon(x: float, y: float, polygon) -> bool:
    inside = False
    n = len(polygon)
    for i in range(n):
        (x1, y1), (x2, y2) = polygon[i], polygon[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


class Calibration:
    """Four image points, clicked in the order top-left, top-right, bottom-right, bottom-left of the map."""

    def __init__(self, version: int, image_points, map_width: float, map_height: float):
        if len(image_points) != 4:
            raise ValueError("exactly four image points are required")
        pts = [(float(x), float(y)) for x, y in image_points]
        if any(not (0 <= x <= 1 and 0 <= y <= 1) for x, y in pts):
            raise ValueError("image points must be normalized to 0..1")
        if not _is_convex(pts) or _quad_area(pts) < 0.02:
            raise ValueError("points must form a convex quadrilateral covering the map")
        self.version = version
        self.image_points = pts
        corners = [(0, 0), (map_width, 0), (map_width, map_height), (0, map_height)]
        self.h = compute_homography(pts, corners)
        self.h_inv = np.linalg.inv(self.h)

    def to_map(self, points) -> np.ndarray:
        return apply_h(self.h, points)

    def to_image(self, points) -> np.ndarray:
        return apply_h(self.h_inv, points)

    def zones_for_box(self, box_n, zones: dict, min_overlap: float) -> list[str]:
        """Zones covered by at least min_overlap of a 5x5 sample grid inside the normalized box."""
        x1, y1, x2, y2 = box_n
        xs, ys = np.linspace(x1, x2, 5), np.linspace(y1, y2, 5)
        samples = self.to_map([(x, y) for x in xs for y in ys])
        hits = []
        for zone_id, zone in zones.items():
            inside = sum(point_in_polygon(px, py, zone["polygon"]) for px, py in samples)
            if inside / len(samples) >= min_overlap:
                hits.append(zone_id)
        return hits

    def check(self, pairs) -> list[float]:
        """Map-unit error for held-out (image point, known map point) pairs."""
        mapped = self.to_map([p["image"] for p in pairs])
        return [float(np.hypot(*(m - np.asarray(p["map"], dtype=float)))) for m, p in zip(mapped, pairs)]


def frame_quality(image_bgr, min_brightness: float, min_sharpness: float) -> dict:
    """Detects a covered or badly defocused view. It cannot detect every occlusion."""
    import cv2

    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    brightness = float(gray.mean())
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    reason = ""
    if brightness < min_brightness:
        reason = "frame too dark (camera covered?)"
    elif sharpness < min_sharpness:
        reason = "frame has no detail (camera covered or defocused?)"
    return {"ok": not reason, "reason": reason, "brightness": round(brightness, 1), "sharpness": round(sharpness, 1)}
