# FlowTwin results

Every figure here is pasted from a script. Sections marked PENDING have not been measured yet; do not present them.

## 1. Backend comparison on the Jetson (PENDING)

Run `scripts/bench.py` inside the GPU window and paste its output here.

## 2. Held-out physical trials (PENDING)

Run `scripts/eval_trials.py` on the recorded clips and paste its table here, with the list of unsupported conditions.

## 3. Physical change to visible response (PENDING)

Filmed measurement, in seconds, with the number of repetitions.

## 4. Fixed route vs replanning (simulated)

Output of `python scripts/compare_sim.py --markdown`. Same obstruction schedule, speed and start for both policies. Units are simulated seconds and map units, not site measurements.

## Warehouse aisle dispatch (warehouse)
| scenario | static s | dynamic s | static wait s | dynamic wait s | static dist | dynamic dist | faster |
|---|---|---|---|---|---|---|---|
| no disruption | 18.25 | 18.25 | 0.0 | 0.0 | 126.0 | 126.0 | tie |
| primary route blocked 30 s | 45.25 | 21.25 | 27.0 | 0.0 | 126.0 | 150.0 | dynamic |
| primary route blocked 10 s | 25.25 | 21.25 | 7.0 | 0.0 | 126.0 | 150.0 | dynamic |
| primary route blocked 3 s | 18.25 | 21.25 | 0.0 | 0.0 | 126.0 | 150.0 | static |
| block appears while inside primary zone | 32.25 | 32.25 | 14.0 | 14.0 | 126.0 | 126.0 | tie |
| both routes blocked, alternate clears first | 54.25 | 31.25 | 36.0 | 10.0 | 126.0 | 150.0 | dynamic |
| shared segment blocked 8 s (no alternative) | 18.25 | 18.25 | 0.0 | 0.0 | 126.0 | 126.0 | tie |

Total makespan over 7 scenarios: static 211.8 s, dynamic 163.8 s (simulated)

## Cross-dock transfer (crossdock)
| scenario | static s | dynamic s | static wait s | dynamic wait s | static dist | dynamic dist | faster |
|---|---|---|---|---|---|---|---|
| no disruption | 12.0 | 12.0 | 0.0 | 0.0 | 92.0 | 92.0 | tie |
| primary route blocked 30 s | 41.0 | 18.5 | 29.0 | 0.0 | 92.0 | 128.0 | dynamic |
| primary route blocked 10 s | 21.0 | 18.5 | 9.0 | 0.0 | 92.0 | 128.0 | dynamic |
| primary route blocked 3 s | 14.0 | 18.0 | 2.0 | 0.0 | 92.0 | 128.0 | static |
| block appears while inside primary zone | 26.0 | 26.0 | 14.0 | 14.0 | 92.0 | 92.0 | tie |
| both routes blocked, alternate clears first | 50.0 | 28.5 | 38.0 | 10.0 | 92.0 | 128.0 | dynamic |
| shared segment blocked 8 s (no alternative) | 14.0 | 14.0 | 2.0 | 2.0 | 92.0 | 92.0 | tie |

Total makespan over 7 scenarios: static 178.0 s, dynamic 135.5 s (simulated)

## Factory line-side delivery (factory)
| scenario | static s | dynamic s | static wait s | dynamic wait s | static dist | dynamic dist | faster |
|---|---|---|---|---|---|---|---|
| no disruption | 13.25 | 13.25 | 0.0 | 0.0 | 102.0 | 102.0 | tie |
| primary route blocked 30 s | 42.25 | 23.75 | 29.0 | 0.0 | 102.0 | 170.0 | dynamic |
| primary route blocked 10 s | 22.25 | 23.75 | 9.0 | 0.0 | 102.0 | 170.0 | static |
| primary route blocked 3 s | 15.25 | 23.25 | 2.0 | 0.0 | 102.0 | 170.0 | static |
| block appears while inside primary zone | 27.25 | 27.25 | 14.0 | 14.0 | 102.0 | 102.0 | tie |
| both routes blocked, alternate clears first | 51.25 | 33.75 | 38.0 | 10.0 | 102.0 | 170.0 | dynamic |
| shared segment blocked 8 s (no alternative) | 14.25 | 14.25 | 1.0 | 1.0 | 102.0 | 102.0 | tie |

Total makespan over 7 scenarios: static 185.8 s, dynamic 159.2 s (simulated)

