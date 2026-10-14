from pathlib import Path

import pytest

from app.calibration import Calibration, point_in_polygon
from app.occupancy import Occupancy, ZoneState
from app.planner import Planner, WarehouseMap, load_maps
from app.simulator import Simulator, VehicleStatus, run_trace

ROOT = Path(__file__).resolve().parent.parent
C, B, U = ZoneState.CLEAR, ZoneState.BLOCKED, ZoneState.UNKNOWN


@pytest.fixture
def wmap():
    return WarehouseMap.load(ROOT / "config" / "maps" / "warehouse.json")


def clear(wmap, **overrides):
    return {z: overrides.get(z, C) for z in wmap.zones}


# planner

def test_baseline_route_uses_aisle_a(wmap):
    assert Planner(wmap).route("S", "D").nodes == ("S", "W", "A1", "A2", "E", "P", "D")


def test_blocked_aisle_reroutes_and_costs_more(wmap):
    p = Planner(wmap)
    detour = p.route("S", "D", frozenset({"A"}))
    assert detour.nodes == ("S", "W", "B1", "B2", "E", "P", "D")
    assert detour.cost_s > p.route("S", "D").cost_s


def test_no_route_when_both_aisles_or_dock_blocked(wmap):
    p = Planner(wmap)
    assert p.route("S", "D", frozenset({"A", "B"})) is None
    assert p.route("S", "D", frozenset({"C"})) is None


def test_turn_cost_is_charged(wmap):
    p = Planner(wmap)
    assert p.route("S", "W").cost_s == pytest.approx(16 / wmap.speed)
    assert p.route("S", "A1").cost_s == pytest.approx(28 / wmap.speed + wmap.turn_cost_s)


def test_plan_versions_increase(wmap):
    p = Planner(wmap)
    r = p.route("S", "D")
    assert p.make_plan(r).version < p.make_plan(r).version


# occupancy

def make_occ():
    occ = Occupancy(["A", "B"], block_frames=3, clear_frames=5, clear_seconds=1.5, stale_seconds=3.0)
    occ.reset(C, 0.0, "test")
    return occ


def test_block_needs_three_consecutive_observations():
    occ = make_occ()
    assert occ.observe(0.2, {"A"}, True) == []
    assert occ.observe(0.4, {"A"}, True) == []
    assert occ.observe(0.6, set(), True) == []          # a miss resets the streak
    occ.observe(0.8, {"A"}, True)
    occ.observe(1.0, {"A"}, True)
    assert occ.states()["A"] == C
    t = occ.observe(1.2, {"A"}, True)
    assert [(x.zone_id, x.new) for x in t] == [("A", B)]
    assert occ.states()["B"] == C


def test_single_missed_detection_does_not_clear():
    occ = make_occ()
    for i in range(3):
        occ.observe(0.2 * i, {"A"}, True)
    occ.observe(1.0, set(), True)
    assert occ.states()["A"] == B


def test_clear_needs_sustained_clear_view():
    occ = make_occ()
    for i in range(3):
        occ.observe(0.2 * i, {"A"}, True)
    for t in (1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4):
        occ.observe(t, set(), True)
        assert occ.states()["A"] == B
    occ.observe(2.6, set(), True)
    assert occ.states()["A"] == C


def test_degraded_view_goes_unknown_and_never_clears():
    occ = make_occ()
    for i in range(3):
        occ.observe(0.2 * i, {"A"}, True)
    occ.observe(1.0, set(), False, "frame too dark")
    assert occ.states() == {"A": U, "B": U}
    for i in range(20):
        occ.observe(1.2 + 0.2 * i, set(), False, "frame too dark")
    assert occ.states()["A"] == U


def test_stale_frames_go_unknown():
    occ = make_occ()
    occ.observe(1.0, set(), True)
    assert occ.check_stale(3.9) == []
    assert {t.new for t in occ.check_stale(4.1)} == {U}


# calibration

def test_homography_maps_corners_and_held_out_point():
    c = Calibration(1, [(0.1, 0.2), (0.9, 0.15), (0.95, 0.9), (0.05, 0.85)], 100, 56)
    mapped = c.to_map(c.image_points)
    assert abs(mapped - [[0, 0], [100, 0], [100, 56], [0, 56]]).max() < 1e-6
    assert abs(c.to_image(c.to_map([(0.5, 0.5)])) - [[0.5, 0.5]]).max() < 1e-9
    assert c.check([{"image": c.to_image([(50, 28)])[0].tolist(), "map": [50, 28]}])[0] < 1e-6


def test_box_maps_to_the_right_zone(wmap):
    c = Calibration(1, [(0, 0), (1, 0), (1, 1), (0, 1)], 100, 56)
    in_a = [0.40, 0.12, 0.50, 0.24]     # map x 40..50, y 6.7..13.4
    assert c.zones_for_box(in_a, wmap.zones, 0.15) == ["A"]
    assert c.zones_for_box([0.02, 0.4, 0.08, 0.5], wmap.zones, 0.15) == []


def test_bad_calibration_rejected():
    with pytest.raises(ValueError):
        Calibration(1, [(0.1, 0.1), (0.9, 0.9), (0.9, 0.1), (0.1, 0.9)], 100, 56)   # self-crossing
    with pytest.raises(ValueError):
        Calibration(1, [(0.5, 0.5), (0.51, 0.5), (0.51, 0.51), (0.5, 0.51)], 100, 56)  # too small


def test_point_in_polygon():
    square = [[0, 0], [10, 0], [10, 10], [0, 10]]
    assert point_in_polygon(5, 5, square) and not point_in_polygon(15, 5, square)


# simulator

def run(sim, states, seconds, dt=0.05):
    for _ in range(int(seconds / dt)):
        sim.tick(dt, states)


def test_delivery_completes_on_baseline_route(wmap):
    sim = Simulator(wmap, Planner(wmap))
    sim.start_order("S", "D")
    run(sim, clear(wmap), 40)
    assert sim.status == VehicleStatus.DONE and sim.plan_changes == 1


def test_reroute_when_aisle_blocked(wmap):
    sim = Simulator(wmap, Planner(wmap))
    sim.start_order("S", "D")
    run(sim, clear(wmap), 1.0)
    first = sim.plan_version
    run(sim, clear(wmap, A=B), 0.1)
    assert sim.plan_version > first and "B1" in sim.plan.nodes
    run(sim, clear(wmap, A=B), 60)
    assert sim.status == VehicleStatus.DONE


def test_no_route_pauses_at_waiting_node_then_resumes(wmap):
    sim = Simulator(wmap, Planner(wmap))
    sim.start_order("S", "D")
    run(sim, clear(wmap), 1.0)
    run(sim, clear(wmap, A=B, B=B), 10)
    assert sim.status == VehicleStatus.PAUSED_NO_ROUTE
    assert sim.node == "W" and sim.next is None      # finished its edge, never entered a blocked aisle
    run(sim, clear(wmap, A=B), 60)
    assert sim.status == VehicleStatus.DONE


def test_unknown_zone_pauses_before_entry(wmap):
    sim = Simulator(wmap, Planner(wmap))
    sim.start_order("S", "D")
    run(sim, clear(wmap, A=U, B=U, C=U), 10)
    assert sim.status == VehicleStatus.PAUSED_UNKNOWN and sim.node == "W"   # held at the wait point, no zone entered


def test_obstruction_on_current_edge_pauses_in_place(wmap):
    sim = Simulator(wmap, Planner(wmap))
    sim.start_order("S", "D")
    states = clear(wmap)
    while not (sim.node == "A1" and sim.next == "A2" and sim.progress > 5):
        sim.tick(0.05, states)
    where = sim.position()
    run(sim, clear(wmap, A=B), 5)
    assert sim.status == VehicleStatus.PAUSED_CONFLICT and sim.position() == where
    run(sim, clear(wmap), 60)
    assert sim.status == VehicleStatus.DONE


def test_stale_plan_version_rejected(wmap):
    p = Planner(wmap)
    sim = Simulator(wmap, p)
    old, new = p.make_plan(p.route("S", "D")), p.make_plan(p.route("S", "D"))
    assert sim.set_plan(new) and not sim.set_plan(old)


def test_dynamic_beats_static_on_long_block_and_waiting_wins_on_short_block(wmap):
    long_block = [(1.0, "A", "BLOCKED"), (40.0, "A", "CLEAR")]
    dyn, sta = (run_trace(wmap, p, long_block, "S", "D") for p in ("dynamic", "static"))
    assert dyn["completed"] and sta["completed"] and dyn["makespan_s"] < sta["makespan_s"]
    short_block = [(1.0, "A", "BLOCKED"), (4.5, "A", "CLEAR")]
    dyn, sta = (run_trace(wmap, p, short_block, "S", "D") for p in ("dynamic", "static"))
    assert sta["makespan_s"] < dyn["makespan_s"]


def test_far_blockage_does_not_stop_the_vehicle_early(wmap):
    sim = Simulator(wmap, Planner(wmap))
    sim.start_order("S", "D")
    run(sim, clear(wmap, C=B), 30)
    assert sim.status == VehicleStatus.PAUSED_NO_ROUTE and sim.node == "E"   # holds at the wait point before the dock
    run(sim, clear(wmap), 30)
    assert sim.status == VehicleStatus.DONE


# every use-case map follows the same contract: A primary, B alternate, C shared final segment

@pytest.mark.parametrize("map_id", ["warehouse", "crossdock", "factory"])
def test_each_use_case_map_reroutes_pauses_and_completes(map_id):
    m = load_maps()[map_id]
    p = Planner(m)
    source, dest = m.data["order"]["source"], m.data["order"]["dest"]

    def zones_on(route):
        return {m.edge_zone(a, b) for a, b in zip(route.nodes, route.nodes[1:])} - {None}

    assert set(m.zones) == {"A", "B", "C"} and (m.data["width"], m.data["height"]) == (100, 56)
    assert zones_on(p.route(source, dest)) == {"A", "C"}
    detour = p.route(source, dest, frozenset({"A"}))
    assert zones_on(detour) == {"B", "C"} and detour.cost_s > p.route(source, dest).cost_s
    assert p.route(source, dest, frozenset({"A", "B"})) is None
    assert p.route(source, dest, frozenset({"C"})) is None
    for policy in ("static", "dynamic"):
        assert run_trace(m, policy, [(1.0, "A", "BLOCKED"), (15.0, "A", "CLEAR")], source, dest)["completed"]
    for s in m.data["structures"]:
        assert 0 <= s["x"] - s["w"] / 2 and s["x"] + s["w"] / 2 <= 100
        assert 0 <= s["y"] - s["d"] / 2 and s["y"] + s["d"] / 2 <= 56


def test_operator_hold_stops_movement_but_keeps_the_plan_current(wmap):
    sim = Simulator(wmap, Planner(wmap))
    sim.start_order("S", "D")
    run(sim, clear(wmap), 1.0)
    where, version = sim.position(), sim.plan_version
    sim.set_held(True)
    run(sim, clear(wmap, A=B), 3.0)
    assert sim.position() == where and sim.plan_version > version and "B1" in sim.plan.nodes
    assert sim.snapshot()["status"] == "PAUSED_OPERATOR"
    sim.set_held(False)
    run(sim, clear(wmap, A=B), 60)
    assert sim.status == VehicleStatus.DONE
