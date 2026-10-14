"""Simulated delivery vehicle. Simulation behavior only, not a robot controller."""
from __future__ import annotations

from enum import Enum

from .occupancy import ZoneState
from .planner import Plan, Planner, Route, WarehouseMap


class VehicleStatus(str, Enum):
    IDLE = "IDLE"
    MOVING = "MOVING"
    PAUSED_NO_ROUTE = "PAUSED_NO_ROUTE"
    PAUSED_UNKNOWN = "PAUSED_UNKNOWN"
    PAUSED_CONFLICT = "PAUSED_CONFLICT"
    WAITING_BLOCKED = "WAITING_BLOCKED"
    DONE = "DONE"


class Simulator:
    """policy="dynamic" replans around non-clear zones; "static" keeps its first route and waits."""

    def __init__(self, wmap: WarehouseMap, planner: Planner, policy: str = "dynamic", on_event=None):
        self.map = wmap
        self.planner = planner
        self.policy = policy
        self.on_event = on_event or (lambda kind, **fields: None)
        self.orders_started = 0
        self._reset()

    def _reset(self) -> None:
        self.status = VehicleStatus.IDLE
        self.held = False
        self.node = self.map.data["order"]["source"]
        self.prev_node: str | None = None
        self.next: str | None = None
        self.progress = 0.0
        self.goal: str | None = None
        self.plan: Plan | None = None
        self.plan_version = 0
        self.pause_zone: str | None = None
        self.reason = ""
        self.turn_delay = 0.0
        self.elapsed = self.waiting = self.distance = 0.0
        self.plan_changes = 0
        self._planned_for: frozenset | None = None
        self._hold: tuple | None = None  # (status, reason) to take at the end of a partial plan
        self._last_states: dict[str, ZoneState] = {}

    def start_order(self, source: str, dest: str) -> None:
        self._reset()
        self.orders_started += 1
        self.node, self.goal = source, dest
        self.status = VehicleStatus.MOVING
        self.on_event("order", decision_reason=f"order started {source} -> {dest}")

    def set_plan(self, plan: Plan) -> bool:
        """Only a plan newer than the last accepted one is taken."""
        if plan.version <= self.plan_version:
            return False
        self.plan, self.plan_version = plan, plan.version
        return True

    def set_held(self, held: bool) -> None:
        """Operator pause. The plan keeps being re-validated; the vehicle just does not move."""
        if held != self.held:
            self.held = held
            self.on_event("vehicle", decision_reason="operator paused the vehicle" if held else "operator resumed")

    def _status(self, status: VehicleStatus, zone: str | None = None, reason: str = "") -> None:
        if status != self.status or zone != self.pause_zone:
            self.status, self.pause_zone = status, zone
            if reason:
                self.reason = reason
            if status != VehicleStatus.MOVING:
                self.on_event("vehicle", zone_id=zone, decision_reason=f"{status.value}: {reason}")

    def _change_reason(self, states: dict[str, ZoneState]) -> str:
        changed = [f"{self.map.zones[z]['label']} {s.value}" for z, s in states.items()
                   if self._last_states.get(z, ZoneState.CLEAR) != s]
        return ", ".join(changed) or "initial plan"

    def _replan(self, states: dict[str, ZoneState], non_clear: frozenset) -> None:
        anchor = self.next or self.node
        prev = self.node if self.next else self.prev_node
        why = self._change_reason(states)
        self._planned_for, self._last_states = non_clear, dict(states)
        route = self.planner.route(anchor, self.goal, non_clear, prev)
        old_version = self.plan_version
        if route is None:
            blocked = frozenset(z for z, s in states.items() if s == ZoneState.BLOCKED)
            through_unknown = self.planner.route(anchor, self.goal, blocked, prev)
            if through_unknown:
                self._hold = (VehicleStatus.PAUSED_UNKNOWN, f"only route needs an unobserved zone ({why})")
            else:
                self._hold = (VehicleStatus.PAUSED_NO_ROUTE, f"no feasible route ({why})")
            best = through_unknown or self.planner.route(anchor, self.goal, frozenset(), prev)
            hold = self._hold_nodes(best.nodes, non_clear)
            if len(hold) < 2:
                self.plan = None
                self._status(self._hold[0], None, self._hold[1])
            elif not self.plan or anchor not in self.plan.nodes or self.plan.nodes[self.plan.nodes.index(anchor):] != hold:
                distance = sum(self.map.length(a, b) for a, b in zip(hold, hold[1:]))
                self.set_plan(self.planner.make_plan(Route(hold, distance / self.map.speed, distance)))
                self.reason = f"{self._hold[1]}; proceeding to wait point {self.map.nodes[hold[-1]]['label']}"
                self.on_event("plan", old_plan_version=old_version, new_plan_version=self.plan_version,
                              decision_reason=self.reason)
            return
        self._hold = None
        remaining = self.plan.nodes[self.plan.nodes.index(anchor):] if self.plan and anchor in self.plan.nodes else None
        if route.nodes != remaining:
            self.set_plan(self.planner.make_plan(route))
            self.plan_changes += 1
            self.reason = why
            self.on_event("plan", old_plan_version=old_version, new_plan_version=self.plan_version,
                          decision_reason=f"route {' > '.join(route.nodes)} because {why}")
        if self.status != VehicleStatus.MOVING:
            self._status(VehicleStatus.MOVING)

    def _hold_nodes(self, nodes: tuple[str, ...], non_clear: frozenset) -> tuple[str, ...]:
        """Prefix of nodes ending at the last waiting node before the first non-clear edge."""
        end = 0
        for i, (a, b) in enumerate(zip(nodes, nodes[1:])):
            if self.map.edge_zone(a, b) in non_clear:
                break
            if self.map.nodes[b]["kind"] == "wait":
                end = i + 1
        return nodes[:end + 1]

    def tick(self, dt: float, states: dict[str, ZoneState]) -> None:
        """Advance by dt seconds. dt=0 re-validates the plan without moving."""
        if self.status in (VehicleStatus.IDLE, VehicleStatus.DONE):
            return
        self.elapsed += dt
        non_clear = frozenset(z for z, s in states.items() if s != ZoneState.CLEAR)
        if self.next is not None:
            zone = self.map.edge_zone(self.node, self.next)
            if zone in non_clear:
                self._status(VehicleStatus.PAUSED_CONFLICT, zone,
                             f"{self.map.zones[zone]['label']} became {states[zone].value} on the current edge")
                self.waiting += dt
                return
        if self.policy == "dynamic" and non_clear != self._planned_for:
            self._replan(states, non_clear)
        elif self.policy != "dynamic" and self.plan is None:
            route = (self.planner.route(self.node, self.goal, non_clear)
                     or self.planner.route(self.node, self.goal))
            self.set_plan(self.planner.make_plan(route))
        if self.held:
            self.waiting += dt
        elif dt > 0:
            self._advance(dt, non_clear)

    def _advance(self, dt: float, non_clear: frozenset) -> None:
        budget = dt
        while budget > 1e-9:
            if self.next is None:
                if self.plan is None or self.node == self.plan.nodes[-1]:  # nothing further is traversable
                    if self._hold:
                        self._status(self._hold[0], None, self._hold[1])
                    self.waiting += budget
                    return
                nxt = self.plan.nodes[self.plan.nodes.index(self.node) + 1]
                zone = self.map.edge_zone(self.node, nxt)
                if zone in non_clear:
                    self._status(VehicleStatus.WAITING_BLOCKED, zone,
                                 f"waiting for {self.map.zones[zone]['label']} on the fixed route")
                    self.waiting += budget
                    return
                if self.prev_node is not None and self.map.is_turn(self.prev_node, self.node, nxt):
                    self.turn_delay = self.map.turn_cost_s
                self.next, self.progress = nxt, 0.0
            if self.plan is not None:
                self._status(VehicleStatus.MOVING)
            if self.turn_delay > 0:
                used = min(budget, self.turn_delay)
                self.turn_delay -= used
                budget -= used
                continue
            length = self.map.length(self.node, self.next)
            step = min(self.map.speed * budget, length - self.progress)
            self.progress += step
            self.distance += step
            budget -= step / self.map.speed
            if self.progress >= length - 1e-9:
                self.prev_node, self.node, self.next, self.progress = self.node, self.next, None, 0.0
                if self.node == self.goal:
                    self._status(VehicleStatus.DONE, None, "delivery completed")
                    return

    def position(self) -> tuple[float, float]:
        x, y = self.map.xy(self.node)
        if self.next is None:
            return x, y
        nx, ny = self.map.xy(self.next)
        f = self.progress / self.map.length(self.node, self.next)
        return x + (nx - x) * f, y + (ny - y) * f

    def _remaining_s(self, nodes: tuple[str, ...], cost_s: float) -> float:
        """Estimated seconds to the goal along nodes, which start at the vehicle's next anchor node."""
        on_edge = 0.0
        if self.next is not None:
            on_edge = (self.map.length(self.node, self.next) - self.progress) / self.map.speed + self.turn_delay
        return on_edge + cost_s

    def snapshot(self) -> dict:
        x, y = self.position()
        anchor = self.next or self.node
        prev = self.node if self.next else self.prev_node
        remaining = direct = None
        route_nodes: list[str] = []
        if self.goal and self.status != VehicleStatus.DONE:
            unconstrained = self.planner.route(anchor, self.goal, frozenset(), prev)
            direct = round(self._remaining_s(unconstrained.nodes, unconstrained.cost_s), 1)
            if self.plan and anchor in self.plan.nodes:
                route_nodes = list(self.plan.nodes[self.plan.nodes.index(anchor):])
                current = self.planner.route(anchor, self.goal, self._planned_for or frozenset(), prev)
                if current:
                    remaining = round(self._remaining_s(current.nodes, current.cost_s), 1)
        active = self.status not in (VehicleStatus.IDLE, VehicleStatus.DONE)
        return {
            "status": "PAUSED_OPERATOR" if self.held and active else self.status.value,
            "held": self.held, "x": round(x, 2), "y": round(y, 2),
            "node": self.node, "next": self.next, "goal": self.goal,
            "pause_zone": self.pause_zone, "reason": self.reason,
            "plan_version": self.plan_version, "route": route_nodes,
            "estimated_remaining_s": remaining, "estimated_direct_remaining_s": direct,
            "elapsed_s": round(self.elapsed, 1), "waiting_s": round(self.waiting, 1),
            "distance": round(self.distance, 1), "plan_changes": self.plan_changes,
        }


def run_trace(wmap: WarehouseMap, policy: str, schedule, source: str, dest: str,
              dt: float = 0.05, timeout: float = 300.0) -> dict:
    """Headless run. schedule is a list of (time_s, zone_id, state); zones start CLEAR."""
    sim = Simulator(wmap, Planner(wmap), policy)
    states = {z: ZoneState.CLEAR for z in wmap.zones}
    pending = sorted(schedule, key=lambda e: e[0])
    sim.start_order(source, dest)
    t = 0.0
    while t < timeout and sim.status != VehicleStatus.DONE:
        while pending and pending[0][0] <= t + 1e-9:
            _, zone_id, state = pending.pop(0)
            states[zone_id] = ZoneState(state)
        sim.tick(dt, states)
        t += dt
    return {
        "policy": policy, "completed": sim.status == VehicleStatus.DONE,
        "makespan_s": round(sim.elapsed, 2), "waiting_s": round(sim.waiting, 2),
        "distance": round(sim.distance, 2), "plan_changes": sim.plan_changes,
    }


def compare_policies(wmap: WarehouseMap, scenarios: list[dict]) -> dict:
    """Static vs dynamic on the same scenario set: same schedule, speed and start for both."""
    order = wmap.data["order"]
    rows, totals = [], {"static": 0.0, "dynamic": 0.0}
    for sc in scenarios:
        result = {p: run_trace(wmap, p, [tuple(e) for e in sc["schedule"]], order["source"], order["dest"])
                  for p in ("static", "dynamic")}
        s, d = result["static"]["makespan_s"], result["dynamic"]["makespan_s"]
        totals["static"] += s
        totals["dynamic"] += d
        faster = "tie" if abs(s - d) < 0.1 else ("dynamic" if d < s else "static")
        rows.append({"name": sc["name"], "static": result["static"], "dynamic": result["dynamic"], "faster": faster})
    return {"rows": rows, "total_makespan_s": {k: round(v, 1) for k, v in totals.items()},
            "units": "simulated seconds and map units"}
