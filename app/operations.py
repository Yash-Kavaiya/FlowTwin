"""Simulated floor operations: a mixed fleet, an order and picking flow, trucks, and the analytics over them.

Everything here is simulation layered on the observed zone states. Vehicles share the planner and obey blocked
and unknown zones, but there is no collision avoidance between vehicles: this shows traffic, not fleet control.
"""
from __future__ import annotations

from collections import deque

from .occupancy import ZoneState
from .simulator import Simulator, VehicleStatus

FLEET = (("V2", "tugger"), ("V3", "forklift"), ("V4", "amr"), ("V5", "amr"), ("V6", "forklift"))
STAGGER_S = 3.0            # delay between successive vehicles starting
DWELL_S = 3.0              # loading or unloading time between two legs
ORDER_INTERVAL_S = 6.0     # a new order arrives this often while the queue has room
MAX_QUEUE = 8
PACK_S = 4.0               # time at the packing station before an order is dispatched
TRUCK_CAPACITY = 4         # dispatched orders per outbound truck
INBOUND_INTERVAL_S = 45.0  # an inbound truck replenishes stock this often
SAMPLE_S = 2.0
HISTORY = 150              # samples kept: five minutes
ORDERS_KEPT = 40


class Operations:
    def __init__(self, wmap, planner, inventory, on_delivery, log):
        self.map, self.inventory = wmap, inventory
        self.on_delivery, self.log = on_delivery, log
        self.enabled = False
        self.t = 0.0
        source, dest = wmap.data["order"]["source"], wmap.data["order"]["dest"]
        self.vehicles = []
        for index, (vid, kind) in enumerate(FLEET):
            outbound_first = index % 2 == 0
            legs = [(source, dest), (dest, source)] if outbound_first else [(dest, source), (source, dest)]
            sim = Simulator(wmap, planner)
            sim.node = legs[0][0]
            self.vehicles.append({"id": vid, "kind": kind, "sim": sim, "legs": legs, "leg": 0,
                                  "wait": index * STAGGER_S, "order": None, "counted": 0})
        self.source, self.dest = source, dest
        self.orders: list[dict] = []
        self._order_seq = 0
        self._next_order = 0.0
        self._next_inbound = INBOUND_INTERVAL_S
        self._next_sample = 0.0
        self.truck_load = 0
        self.trucks_departed = 0
        self.inbound_deliveries = 0
        self.completed: deque[float] = deque()
        self.history: deque[dict] = deque(maxlen=HISTORY)
        self.traffic: dict[str, float] = {}

    # ------------------------------------------------------------------ orders
    def _new_order(self) -> None:
        taken = self.inventory.take()
        if taken is None:
            return
        self._order_seq += 1
        self.orders.append({"id": f"O-{self._order_seq:03d}", **taken, "status": "QUEUED", "vehicle": None,
                            "created_s": round(self.t, 1), "done_s": None, "packed_at": None})
        del self.orders[:-ORDERS_KEPT]

    def _advance_orders(self) -> None:
        for order in self.orders:
            if order["status"] == "PACKED" and self.t - order["packed_at"] >= PACK_S:
                order["status"] = "DISPATCHED"
                self.truck_load += 1
                if self.truck_load >= TRUCK_CAPACITY:
                    self.truck_load = 0
                    self.trucks_departed += 1
                    self.log("truck", decision_reason=f"outbound truck {self.trucks_departed} departed with "
                                                      f"{TRUCK_CAPACITY} orders (SIMULATED)")

    # ------------------------------------------------------------------ step
    def step(self, dt: float, states: dict[str, ZoneState], extra_vehicles=()) -> None:
        """Advance the simulation. extra_vehicles are other simulators to include in traffic and utilisation."""
        if not self.enabled:
            return
        self.t += dt
        if self.t >= self._next_order:
            self._next_order = self.t + ORDER_INTERVAL_S
            if sum(o["status"] == "QUEUED" for o in self.orders) < MAX_QUEUE:
                self._new_order()
        if self.t >= self._next_inbound:
            self._next_inbound = self.t + INBOUND_INTERVAL_S
            units = self.inventory.replenish()
            if units:
                self.inbound_deliveries += 1
                self.log("truck", decision_reason=f"inbound truck {self.inbound_deliveries} replenished "
                                                  f"{units} units (SIMULATED)")

        for v in self.vehicles:
            sim = v["sim"]
            if sim.status in (VehicleStatus.IDLE, VehicleStatus.DONE):
                if sim.status == VehicleStatus.DONE and v["counted"] != sim.orders_started:
                    v["counted"] = sim.orders_started
                    self.on_delivery(v["id"], sim)
                    if v["order"]:
                        v["order"].update(status="PACKED", packed_at=self.t, done_s=round(self.t, 1))
                        self.completed.append(self.t)
                        v["order"] = None
                v["wait"] -= dt
                if v["wait"] <= 0:
                    leg = v["legs"][v["leg"] % 2]
                    if leg[0] == self.source:  # an outbound leg carries the oldest queued order, if there is one
                        queued = next((o for o in self.orders if o["status"] == "QUEUED"), None)
                        if queued:
                            queued.update(status="IN_TRANSIT", vehicle=v["id"])
                            v["order"] = queued
                    sim.start_order(*leg)
                    v["leg"] += 1
                    v["wait"] = DWELL_S
            sim.tick(dt, states)

        for sim in [v["sim"] for v in self.vehicles] + list(extra_vehicles):
            if sim.next is not None and sim.status == VehicleStatus.MOVING:
                key = "-".join(sorted((sim.node, sim.next)))
                self.traffic[key] = self.traffic.get(key, 0.0) + dt
        self._advance_orders()
        while self.completed and self.t - self.completed[0] > 60.0:
            self.completed.popleft()
        if self.t >= self._next_sample:
            self._next_sample = self.t + SAMPLE_S
            self.history.append(self._sample(states, extra_vehicles))

    # ------------------------------------------------------------------ views
    def _counts(self) -> dict:
        counts = {s: 0 for s in ("QUEUED", "IN_TRANSIT", "PACKED", "DISPATCHED")}
        for order in self.orders:
            counts[order["status"]] += 1
        return counts

    def _sample(self, states, extra_vehicles) -> dict:
        sims = [v["sim"] for v in self.vehicles] + [s for s in extra_vehicles if s.status != VehicleStatus.IDLE]
        moving = sum(s.status == VehicleStatus.MOVING and s.next is not None for s in sims)
        paused = sum(s.status.value.startswith("PAUSED") for s in sims)
        return {"t": round(self.t, 1), "throughput_per_min": len(self.completed),
                "utilisation_pct": round(100 * moving / len(sims)) if sims else 0, "paused": paused,
                "queue": self._counts()["QUEUED"], "stock_fill_pct": round(100 * self.inventory.snapshot()["fill"], 1),
                "blocked_zones": sum(s == ZoneState.BLOCKED for s in states.values())}

    def alerts(self, states: dict[str, ZoneState]) -> list[dict]:
        out = []
        for zone_id, state in states.items():
            if state != ZoneState.CLEAR:
                out.append({"level": "critical" if state == ZoneState.BLOCKED else "warning",
                            "text": f"{self.map.zones[zone_id]['label']} is {state.value}"})
        if self.enabled:
            held = [v["id"] for v in self.vehicles if v["sim"].status.value.startswith("PAUSED")]
            if held:
                out.append({"level": "warning", "text": f"{len(held)} vehicle(s) holding: {', '.join(held)}"})
            queued = self._counts()["QUEUED"]
            if queued >= MAX_QUEUE - 2:
                out.append({"level": "warning", "text": f"order queue is long: {queued} waiting"})
        low = sum(r["low_slots"] for r in self.inventory.snapshot()["racks"])
        if low:
            out.append({"level": "info", "text": f"{low} rack slot(s) low on stock (SIMULATED)"})
        return out

    def snapshot(self, states: dict[str, ZoneState]) -> dict:
        vehicles = []
        if self.enabled:
            for v in self.vehicles:
                snap = v["sim"].snapshot()
                vehicles.append({"id": v["id"], "kind": v["kind"],
                                 **{k: snap[k] for k in ("status", "x", "y", "route", "goal")},
                                 "order": v["order"]["id"] if v["order"] else None,
                                 "legs_done": max(0, v["sim"].orders_started - 1) + (snap["status"] == "DONE")})
        peak = max(self.traffic.values(), default=0.0)
        return {
            "fleet": {"enabled": self.enabled, "vehicles": vehicles, "note": "no collision avoidance between vehicles"},
            "ops": {
                "source": "SIMULATED", "counts": self._counts(), "truck_load": self.truck_load,
                "truck_capacity": TRUCK_CAPACITY, "trucks_departed": self.trucks_departed,
                "inbound_deliveries": self.inbound_deliveries,
                "orders": [{k: o[k] for k in ("id", "product", "sku", "slot", "units", "status", "vehicle")}
                           for o in self.orders[-12:]][::-1],
                "alerts": self.alerts(states),
                "traffic": {k: round(v / peak, 3) for k, v in self.traffic.items()} if peak else {},
            },
        }

    def analytics(self) -> dict:
        return {"source": "SIMULATED", "sample_s": SAMPLE_S, "history": list(self.history)}
