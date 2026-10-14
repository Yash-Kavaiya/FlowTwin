"""Simulated rack inventory. Generated from a fixed seed per map; it is demo data, not a WMS feed."""
from __future__ import annotations

import random

PRODUCTS = ("Carton tape", "Shrink wrap", "Label rolls", "Corner boards", "Poly bags", "Stretch film",
            "Bubble mailers", "Pallet covers", "Void fill", "Strapping", "Edge protectors", "Packing slips")


class Inventory:
    def __init__(self, wmap):
        self._rng = random.Random(f"flowtwin-{wmap.data['id']}")
        self.racks: list[dict] = []
        for index, s in enumerate(wmap.data["structures"]):
            if s["kind"] != "rack":
                continue
            rack_id = f"R{len(self.racks) + 1}"
            bays, levels = max(1, round(s["w"] / 9)), max(2, round(s["h"] / 2.4))
            target = self._rng.uniform(0.25, 0.95)  # each rack gets its own typical fill, so the heatmap varies
            slots = []
            for bay in range(bays):
                for level in range(levels):
                    capacity = self._rng.choice((24, 36, 48))
                    qty = max(0, min(capacity, round(capacity * self._rng.gauss(target, 0.18))))
                    slots.append({"slot": f"{rack_id}-B{bay + 1}-L{level + 1}",
                                  "sku": f"SKU-{self._rng.randrange(1000, 9999)}",
                                  "product": self._rng.choice(PRODUCTS), "qty": qty, "capacity": capacity})
            self.racks.append({"id": rack_id, "structure_index": index, "label": s.get("label") or f"Rack {rack_id}",
                               "slots": slots})

    def take(self) -> dict | None:
        """Take a few units from a random stocked slot. Returns what was taken, or None when nothing is stocked."""
        stocked = [slot for rack in self.racks for slot in rack["slots"] if slot["qty"] > 0]
        if not stocked:
            return None
        slot = self._rng.choice(stocked)
        units = min(slot["qty"], self._rng.randint(1, 6))
        slot["qty"] -= units
        return {"slot": slot["slot"], "sku": slot["sku"], "product": slot["product"], "units": units}

    def pick(self) -> str | None:
        """take(), described in words for the event timeline."""
        taken = self.take()
        if taken is None:
            return None
        return f"picked {taken['units']} x {taken['product']} ({taken['sku']}) from {taken['slot']}"

    def replenish(self, slots: int = 4) -> int:
        """Top up the emptiest slots to 90% of capacity, as an inbound delivery would. Returns units added."""
        everything = [slot for rack in self.racks for slot in rack["slots"]]
        everything.sort(key=lambda s: s["qty"] / s["capacity"])
        added = 0
        for slot in everything[:slots]:
            target = round(slot["capacity"] * 0.9)
            if target > slot["qty"]:
                added += target - slot["qty"]
                slot["qty"] = target
        return added

    def snapshot(self) -> dict:
        racks = []
        for rack in self.racks:
            units = sum(s["qty"] for s in rack["slots"])
            capacity = sum(s["capacity"] for s in rack["slots"])
            racks.append({**rack, "units": units, "capacity": capacity,
                          "fill": round(units / capacity, 3) if capacity else 0.0,
                          "low_slots": sum(s["qty"] <= s["capacity"] * 0.15 for s in rack["slots"])})
        total_units = sum(r["units"] for r in racks)
        total_capacity = sum(r["capacity"] for r in racks)
        return {"source": "SIMULATED", "racks": racks, "units": total_units, "capacity": total_capacity,
                "fill": round(total_units / total_capacity, 3) if total_capacity else 0.0}
