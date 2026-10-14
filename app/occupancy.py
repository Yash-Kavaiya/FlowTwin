"""Per-zone observed status with temporal confirmation and staleness."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ZoneState(str, Enum):
    CLEAR = "CLEAR"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass
class ZoneStatus:
    state: ZoneState
    since: float
    reason: str
    last_observed: float | None = None
    evidence_id: str | None = None
    obstructed_streak: int = 0
    clear_streak: int = 0
    clear_since: float | None = None


@dataclass(frozen=True)
class Transition:
    zone_id: str
    old: ZoneState
    new: ZoneState
    reason: str


class Occupancy:
    def __init__(self, zone_ids, block_frames: int, clear_frames: int, clear_seconds: float, stale_seconds: float):
        self.zone_ids = list(zone_ids)
        self.block_frames = block_frames
        self.clear_frames = clear_frames
        self.clear_seconds = clear_seconds
        self.stale_seconds = stale_seconds
        self.zones: dict[str, ZoneStatus] = {}
        self.last_frame_time: float | None = None
        self.reset(ZoneState.UNKNOWN, 0.0, "no observation yet")

    def reset(self, initial: ZoneState, now: float, reason: str) -> None:
        self.last_frame_time = None
        self.zones = {z: ZoneStatus(initial, now, reason) for z in self.zone_ids}

    def states(self) -> dict[str, ZoneState]:
        return {z: s.state for z, s in self.zones.items()}

    def _set(self, zone_id: str, new: ZoneState, now: float, reason: str) -> Transition | None:
        status = self.zones[zone_id]
        if status.state == new:
            return None
        old = status.state
        status.state, status.since, status.reason = new, now, reason
        return Transition(zone_id, old, new, reason)

    def invalidate(self, now: float, reason: str) -> list[Transition]:
        """Every zone becomes UNKNOWN and all confirmation progress is dropped."""
        out = []
        for zone_id, status in self.zones.items():
            status.obstructed_streak = status.clear_streak = 0
            status.clear_since = None
            t = self._set(zone_id, ZoneState.UNKNOWN, now, reason)
            if t:
                out.append(t)
        return out

    def observe(self, now: float, obstructed: set[str], view_ok: bool, reason: str = "") -> list[Transition]:
        """Apply one analyzed frame. A degraded view never clears or confirms anything."""
        self.last_frame_time = now
        if not view_ok:
            return self.invalidate(now, reason or "view not valid")
        out = []
        for zone_id, status in self.zones.items():
            status.last_observed = now
            t = None
            if zone_id in obstructed:
                status.obstructed_streak += 1
                status.clear_streak = 0
                status.clear_since = None
                if status.obstructed_streak >= self.block_frames:
                    t = self._set(zone_id, ZoneState.BLOCKED, now,
                                  f"{status.obstructed_streak} consecutive obstructed observations")
            else:
                status.obstructed_streak = 0
                status.clear_streak += 1
                if status.clear_since is None:
                    status.clear_since = now
                held = now - status.clear_since
                if status.clear_streak >= self.clear_frames and held >= self.clear_seconds:
                    t = self._set(zone_id, ZoneState.CLEAR, now,
                                  f"clear for {held:.1f}s over {status.clear_streak} observations")
            if t:
                out.append(t)
        return out

    def is_stale(self, now: float) -> bool:
        return self.last_frame_time is None or now - self.last_frame_time > self.stale_seconds

    def check_stale(self, now: float) -> list[Transition]:
        return self.invalidate(now, "no fresh camera frame") if self.is_stale(now) else []

    def force(self, zone_id: str, state: ZoneState, now: float, reason: str) -> list[Transition]:
        t = self._set(zone_id, state, now, reason)
        return [t] if t else []
