# Use cases and their 3D structures

FlowTwin ships three use cases. Each one is a map file in `config/maps/` with its own 3D structures, labels and story. The perception, temporal rules, planner and evidence trail are identical; only the floor changes. Switch between them with the Use case tabs in the app (this starts a new session).

All three share one contract, checked by the tests:

- the same 100 × 56 footprint, so one camera calibration serves all three paper sheets;
- zone **A** on the primary route, zone **B** on the alternate, zone **C** on the shared final segment;
- blocking A reroutes through B, blocking A and B or blocking C leaves no route, and the vehicle holds at a wait point.

| | Warehouse aisle dispatch | Cross-dock transfer | Factory line-side delivery |
|---|---|---|---|
| Map file | `warehouse.json` | `crossdock.json` | `factory.json` |
| Buyer | Warehouse operations manager | Cross-dock or parcel hub shift lead | Plant logistics or production supervisor |
| Disruption | Pallet or spill in a picking aisle | Dropped parcel cage in the direct lane | Parked cart in the main corridor |
| Zone A (primary) | Aisle A | Direct lane | Main corridor |
| Zone B (alternate) | Aisle B | Bypass lane | North corridor |
| Zone C (shared) | Dock lane | Gate approach | Cell approach |
| 3D structures | Three racking rows, pallet stacks, packing bench, dispatch door | Inbound and outbound trailers, sorter conveyor, staging cages, dock wall | Press cell, weld cell, paint booth, assembly line, kit shelves |
| Route | Storage → Dispatch | Inbound dock → Truck bay | Kitting store → Assembly station |
| Pilot metric | Delay minutes avoided per blocked-aisle event | Trailers leaving on time despite a lane obstruction | Line-side stock-outs avoided per shift |

The structures are for orientation only. They are drawn in the 3D view and printed pale on the paper sheet; the camera never reports on them.

## Fixed route vs replanning, per use case

Seven fixed scenarios, total makespan in simulated seconds (`python scripts/compare_sim.py`):

| Use case | Fixed route | Replanning |
|---|---|---|
| Warehouse aisle dispatch | 211.8 | 163.8 |
| Cross-dock transfer | 178.0 | 135.5 |
| Factory line-side delivery | 185.8 | 159.2 |

The same table, scenario by scenario, is in the app under "Fixed route vs replanning". These are simulation figures in map units, not site measurements.

## Paper sheets

`python scripts/make_print_map.py` writes `docs/tabletop_warehouse.svg`, `docs/tabletop_crossdock.svg` and `docs/tabletop_factory.svg`. Keep the four black corner squares in the same place when you swap sheets and the calibration carries over; if in doubt, recalibrate.

## Adding a fourth

Copy a map file, keep the footprint and the zone ids A, B, C, list its `structures` (kind, position, size, optional label), and add its id to the parametrized test in `tests/test_core.py`.

## Theme

The interface uses a Globant-style palette: lime `#BFD732` accent on black with white type. Lime marks the brand and the active route; red (blocked), gray (unknown) and amber (paused or pending) keep their operational meaning. Only colors are used. No Globant logo or licensed typeface is bundled, so add official assets yourself if the event permits it.
