# Seven-minute presentation (one slide per minute)

Numbers marked FILL come from `docs/results.md` after the Oct 7 measurements. Do not present a figure that is not in that file.

## 1. Problem and buyer
- An obstruction in one aisle stalls a delivery; the dispatcher learns about it late and by radio.
- Buyer: warehouse operations or automation manager.
- First use: advisory visibility and dispatch planning for one aisle or zone.
- The same loop is shown on three floors: warehouse aisle dispatch, cross-dock transfer, factory line-side delivery (`use_cases.md`).

## 2. Product loop and what is original
- See (camera) → map (calibrated zones) → decide (replan, pause, or wait) → verify (clearance seen before resuming).
- Original work: observation-to-map bridge, temporal confirmation, UNKNOWN handling, verified recovery, evidence-linked decisions.
- Reused: a pretrained object detector.

## 3. Architecture and NVIDIA components actually used
- Browser camera → JPEG frames over HTTPS → Jetson Thor → detector on CUDA → occupancy → planner → 3D twin in the browser.
- Used: Jetson Thor, NVIDIA PyTorch on CUDA, TensorRT FP16 (FILL: only if the engine built and passed the comparison).
- Not used and not claimed: DeepStream, hardware video decode, Isaac, Omniverse.

## 4. Decisions that make it trustworthy
- Four-point planar calibration; zone outlines drawn back on the camera view to check it.
- Block after 3 consistent observations; clear only after a sustained clear view; a missed detection never clears.
- Stale, dark or uncalibrated view → UNKNOWN → vehicle pauses before entry.
- Plans are versioned; a result from an old session or calibration is discarded.

## 5. Measured performance and failures
- Held-out trials: FILL correct/total per category, false blocks, false clears.
- PyTorch vs TensorRT on the device: FILL p50, p95, calls per second, detection differences.
- Physical change to visible response: FILL seconds (filmed), of which temporal confirmation is by design.
- Static vs dynamic routing over 7 fixed scenarios (simulated seconds), warehouse: total makespan 211.8 static, 163.8 dynamic. Dynamic is faster in 3, slower in 1 (a 3-second block, where waiting wins), tied in 3. Cross-dock: 178.0 vs 135.5. Factory: 185.8 vs 159.2.
- Known failures: FILL (props or angles that were missed).

## 6. Business assumptions and pilot economics
Monthly avoidable-delay value = events per month × avoidable hours per event × marginal cost per hour × fraction prevented.

| Case | Events/month | Hours/event | Cost/hour | Prevented | Gross value/month |
|---|---|---|---|---|---|
| Low | 40 | 0.1 | $35 | 30% | $42 |
| Base | 100 | 0.2 | $50 | 50% | $500 |
| High | 400 | 0.4 | $80 | 60% | $7,680 |

Every input is an assumption for illustration, not a customer figure. Subtract detour cost, false-alert handling, hardware, maintenance and integration. The low and base cases do not pay for new hardware on their own; the case needs many events, several zones per device, or an edge device already on site.

Four-week pilot: week 1 baseline and calibration; week 2 advisory shadow mode; week 3 measured operator recommendations; week 4 review false alerts, response times, value and integration needs.

## 7. Limits, scaling path, lessons
- Limits: one fixed camera, three prop classes, planar map, simulated vehicle, no equipment control.
- Scaling: each site processes video at the edge; only event metadata leaves the site. This is a direction, not something built.
- Lessons: FILL after the build (one about perception, one about the Jetson environment).
