"""Warehouse graph and deterministic route search (A* on the CPU)."""
from __future__ import annotations

import heapq
import itertools
import json
import math
from dataclasses import dataclass
from pathlib import Path


MAPS_DIR = Path(__file__).resolve().parent.parent / "config" / "maps"
DEFAULT_MAP = "warehouse"


def load_maps() -> dict[str, "WarehouseMap"]:
    """Every use-case map, keyed by id. All share the same footprint and the zone ids A, B, C."""
    maps = {p.stem: WarehouseMap.load(p) for p in sorted(MAPS_DIR.glob("*.json"))}
    return {DEFAULT_MAP: maps.pop(DEFAULT_MAP), **maps}


@dataclass(frozen=True)
class Route:
    nodes: tuple[str, ...]
    cost_s: float
    distance: float


@dataclass(frozen=True)
class Plan:
    version: int
    nodes: tuple[str, ...]
    cost_s: float
    distance: float


class WarehouseMap:
    def __init__(self, data: dict):
        self.data = data
        self.speed = float(data["speed"])
        self.turn_cost_s = float(data["turn_cost_s"])
        self.nodes = {n["id"]: n for n in data["nodes"]}
        self.zones = {z["id"]: z for z in data["zones"]}
        self._adjacent: dict[str, list[str]] = {n: [] for n in self.nodes}
        self._edge_zone: dict[frozenset, str | None] = {}
        for edge in data["edges"]:
            a, b = edge["a"], edge["b"]
            self._adjacent[a].append(b)
            self._adjacent[b].append(a)
            self._edge_zone[frozenset((a, b))] = edge.get("zone")

    @classmethod
    def load(cls, path: Path) -> "WarehouseMap":
        return cls(json.loads(Path(path).read_text()))

    def xy(self, node: str) -> tuple[float, float]:
        n = self.nodes[node]
        return float(n["x"]), float(n["y"])

    def neighbors(self, node: str) -> list[str]:
        return self._adjacent[node]

    def edge_zone(self, a: str, b: str) -> str | None:
        return self._edge_zone[frozenset((a, b))]

    def length(self, a: str, b: str) -> float:
        (ax, ay), (bx, by) = self.xy(a), self.xy(b)
        return math.hypot(bx - ax, by - ay)

    def is_turn(self, prev: str, node: str, nxt: str) -> bool:
        (px, py), (nx, ny), (tx, ty) = self.xy(prev), self.xy(node), self.xy(nxt)
        v1, v2 = (nx - px, ny - py), (tx - nx, ty - ny)
        cross = v1[0] * v2[1] - v1[1] * v2[0]
        dot = v1[0] * v2[0] + v1[1] * v2[1]
        return abs(cross) > 1e-6 or dot < 0


class Planner:
    def __init__(self, wmap: WarehouseMap):
        self.map = wmap
        self._version = 0

    def route(self, start: str, goal: str, excluded=frozenset(), prev: str | None = None) -> Route | None:
        """Cheapest route by travel time plus fixed turn costs; edges in excluded zones are removed."""
        m = self.map
        counter = itertools.count()
        first = (start, prev)
        best = {first: 0.0}
        parent: dict[tuple, tuple] = {}
        heap = [(m.length(start, goal) / m.speed, next(counter), 0.0, first)]
        while heap:
            _, _, g, state = heapq.heappop(heap)
            if g > best.get(state, math.inf):
                continue
            node, came_from = state
            if node == goal:
                nodes = [node]
                while state in parent:
                    state = parent[state]
                    nodes.append(state[0])
                nodes.reverse()
                distance = sum(m.length(a, b) for a, b in zip(nodes, nodes[1:]))
                return Route(tuple(nodes), g, distance)
            for nxt in m.neighbors(node):
                if m.edge_zone(node, nxt) in excluded:
                    continue
                cost = g + m.length(node, nxt) / m.speed
                if came_from is not None and m.is_turn(came_from, node, nxt):
                    cost += m.turn_cost_s
                new_state = (nxt, node)
                if cost < best.get(new_state, math.inf):
                    best[new_state] = cost
                    parent[new_state] = state
                    heapq.heappush(heap, (cost + m.length(nxt, goal) / m.speed, next(counter), cost, new_state))
        return None

    def make_plan(self, route: Route) -> Plan:
        self._version += 1
        return Plan(self._version, route.nodes, route.cost_s, route.distance)
