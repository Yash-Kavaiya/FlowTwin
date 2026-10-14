# Ten-minute live demo

Before the judges arrive: server running with the real model, mode LIVE, camera started, calibration outlines aligned, Reset pressed, props within reach, backup clip open in another tab.

| Time | Do | Say | They must see |
|---|---|---|---|
| 0:00 | Nothing on screen changes | "Move a real object into an aisle; FlowTwin sees the disruption, replans the delivery, and explains the consequence. The camera and the model are real. The vehicle is simulated, and the screen says so." | The paper map and the 3D twin side by side |
| 0:45 | Point at the header, open Engineering | "Inference runs on the Jetson Thor. These values come from the backend, not from the page." | Backend, model, GPU name, LIVE badge, observation age |
| 1:30 | Press Start delivery | "One order, storage to dispatch. The planner picks aisle A because it is shorter." | Blue route through aisle A, vehicle moving |
| 2:30 | Hand a judge the prop: "put it anywhere in aisle A" | "Three consistent observations are required before the map changes, so a single flicker cannot reroute a vehicle." | Detection box, aisle A turns red and reads BLOCKED (OBSERVED), route moves to aisle B |
| 4:00 | Point at the decision card and the top timeline row; click its evidence link | "Every decision keeps the frame that caused it. The time figure is an estimate in simulated seconds. Waiting is compared against an assumed clearance time that I type in; the system does not invent one." | Why line, plan version, Compare decisions, evidence frame labelled as recorded |
| 5:00 | Place a second prop in aisle B | "No route is feasible. It holds at a wait point rather than driving at an obstruction." | Both aisles red, vehicle amber, "Paused: no feasible route" |
| 6:00 | Remove one prop | "A missed detection is not proof of clearance. The aisle has to be seen clear for a sustained interval before the vehicle resumes." | Aisle stays red briefly, then CLEAR, vehicle resumes |
| 7:00 | Cover the lens with a hand | "When it cannot see, it says so and stops before entering anything it has not observed." | VIEW UNKNOWN badge, zones gray, vehicle paused |
| 8:00 | Uncover; scroll to the results | "Held-out trials with denominators, PyTorch against TensorRT on this device, and static against dynamic routing including a case where waiting wins." | `docs/results.md` figures |
| 9:00 | Stop | "Buyer: a warehouse operations manager. Limit: one camera, three prop classes, a planar map. Next step: a four-week advisory pilot on one aisle." | Pilot slide |

The script above uses the warehouse use case. If a judge asks "does this only work for warehouses?", click the Cross-dock or Factory tab: the floor, structures and buyer story change, the perception and decision logic do not. Swap the paper sheet only if there is time; otherwise show it in SYNTHETIC mode and say so.

## If something goes wrong

- Wrong or missing detection: say so, move the prop flat and fully inside the dashed aisle outline, continue. Do not touch thresholds.
- Page frozen: Reset. If that fails, restart the server (see `runbook.md`) while explaining the architecture slide.
- GPU or network gone: switch the input mode to REPLAY or play the backup clip, and say that it is a recording.

## Questions to expect

- **Is this a game?** Real perception drives the map. Execution is simulated and labelled.
- **Why a Jetson?** Perception runs locally on the accelerator, which is the route to on-site processing. This remote demo still needs the network.
- **Where is the AI?** In the learned visual detector. Route search is a deterministic algorithm, on purpose.
- **What is original?** The calibrated observation-to-map bridge, the temporal state rules, verified recovery and the evidence trail. The detector is a pretrained model.
- **What happens when it is unsure?** The zone becomes UNKNOWN and the vehicle pauses before entry.
- **What does the ROI prove?** Nothing yet. It is a hypothesis with stated inputs that a pilot would measure.
