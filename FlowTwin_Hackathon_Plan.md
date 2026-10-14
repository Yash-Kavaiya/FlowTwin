# FlowTwin — Physical AI Hackathon Build Plan

**Product promise.** A camera-connected 3D warehouse that detects visible aisle obstructions, updates its operational map, compares feasible responses, and verifies recovery. The prototype uses real camera observations and Jetson inference, with a simulated delivery vehicle. It does not control industrial equipment or claim full warehouse autonomy.

**One-sentence pitch.** “Move a real object into an aisle; FlowTwin sees the disruption, replans the delivery, and explains the operational consequence.”

**1. Competition strategy**

| Judging criterion | Weight from supplied rules | Evidence to prepare |
|---|---:|---|
| Innovation and creativity | 25% | Judge-created physical disruption; observed, predicted, and simulated states separated; recovery verified by vision |
| Technical complexity | 20% | Camera calibration, GPU perception, temporal occupancy, graph planning, stale-input handling, event replay |
| Jetson Thor capabilities | 20% | Actual CUDA execution; TensorRT comparison if working; resource and latency measurements; optional NVIDIA video path |
| Real-world impact | 15% | Warehouse dispatch disruptions, no-route handling, repeatable workload comparison |
| Demo quality | 10% | Clear tabletop-to-twin correspondence, practiced live sequence, stable protected URL, labeled fallback |
| Business value | 10% | One buyer, explicit assumptions, pilot metrics, implementation costs, credible deployment path |

Original contribution: the calibrated observation-to-map bridge, state transitions, decision comparison, explanation evidence, and recovery behavior. Reuse pretrained model components without presenting a complete borrowed project as original.

**2. Exact MVP boundary**

- One fixed overhead camera, one tabletop warehouse, one simulated vehicle, one active order at a time.
- A small graph with storage, two alternate aisles, packing, dispatch, and marked waiting nodes. Use approximately 8–12 nodes; choose a layout whose alternate routes are visually obvious.
- Three zones with explicit observed status: CLEAR, BLOCKED, UNKNOWN.
- Start/reset delivery, mark observed obstruction, replan, pause when no route exists, and resume after verified clearance.
- Separate browser capture rate, inference rate, and 3D render rate.
- One historical event timeline with the observation that caused each decision.
- A comparison of fixed-route waiting versus dynamic routing on an identical simulated workload.

Exclude from the deadline: full supplier-to-customer optimization, demand forecasting, actual forklift control, multi-robot coordination, ERP integrations, arbitrary-object recognition, full 3D reconstruction, chat agents, and production safety certification.

**3. Physical demonstration setup**

Use a paper or cardboard warehouse map, four calibration markers/corners, a fixed webcam support, diffuse lighting, and several approved props. An existing laptop webcam is sufficient if positioned consistently; a phone camera adds transport work and is optional. Props should be low-profile where possible to reduce planar mapping error.

Test a small detector on real camera views before choosing props. Candidate supported everyday classes include a book, bottle, or cup, but overhead recognition must be measured. A generic pretrained detector may not have a cardboard-box or pallet class. A book can represent a pallet obstruction in the tabletop demo; label the representation clearly. If recognition is poor, change the prop, angle, or lighting first. Do not spend the remaining week collecting a warehouse-scale dataset.

Four known map points establish a planar homography. Fixed aisle polygons are configured manually. Validate mapping using held-out points on the mat, not only the four calibration points. A 2D bounding box is not a precise 3D footprint: keep obstacles near the calibrated plane, use conservative zone overlap, and document the approximation. Require recalibration after camera movement. A repeated alignment check or marker visibility check should detect likely camera displacement; absence of valid alignment changes observation status to UNKNOWN.

No personal, customer, or confidential data is required. Capture the tabletop and props. Retain only consented demo clips and selected evidence frames.

**4. NVIDIA stack and compatibility policy**

| Layer | Planned implementation | Gate / fallback |
|---|---|---|
| Hardware | Assigned Jetson Thor environment | Stay within assigned windows and quotas |
| Base stack | Organizer-installed JetPack/CUDA/cuDNN/NVIDIA PyTorch | Record versions; do not replace system packages |
| Initial perception | Small detector running in NVIDIA PyTorch on CUDA | Required working baseline |
| Optimized perception | Same detector through installed TensorRT, FP16 if supported | Compare accuracy and latency; preserve baseline |
| Browser camera transport | Compressed JPEG frames over same-origin HTTPS/WebSocket | CPU JPEG decode; GPU model inference |
| Encoded-video path | H.264 file or approved stream through NVIDIA GStreamer decoder | Only if installed and tested |
| Streaming analytics | DeepStream: decode, conversion, nvstreammux, nvinfer, optional tracker | Optional; requires compatible installed plugins and model parser |
| Planning | Small CPU graph planner | Deterministic, testable, no model dependency |
| Interface | React/TypeScript with Three.js | Browser renders 3D locally |
| API and state | FastAPI, bounded input queue, SQLite | One public port 8000 |

YOLO11n is a reasonable initial candidate if a compatible package/model is already usable; a working organizer-supplied detector is preferable to a migration. Verify weight access and dependency compatibility before committing. Record model/source/license metadata in the dependency inventory and flag commercialization licensing for later review.

NVIDIA's DeepStream compatibility matrix differs by release. Choose based on the installed environment, not the newest web example. Native installation instructions may require sudo/system writes, which the supplied guide prohibits. Ask organizers about an available supported image or plugin; do not attempt host flashing, system upgrades, or nested Docker as a workaround.

Thor-specific codec detail: NVIDIA documentation says nvv4l2decoder does not support JPEG/MJPEG decoding on Thor. Do not claim a browser JPEG pipeline uses that hardware decoder. For the NVIDIA codec demonstration, use an actual H.264 input. A prerecorded input is labeled REPLAY, although inference may still execute live on Jetson.

CUDA + TensorRT is already a meaningful NVIDIA inference stack. DeepStream is an optional integration milestone. Isaac Sim, Omniverse, Triton, Kafka, Kubernetes, and ROS2 are not required for this single-camera prototype; they add no automatic judging credit merely by being named.

**5. Two supported input paths**

Path A, priority live demo: browser getUserMedia capture -> compressed frames -> authenticated same-origin backend -> decode/resize -> CUDA or TensorRT inference -> spatial/temporal state -> planner -> state updates -> browser 3D scene.

Begin with 640-pixel-class input at roughly 5 frames per second; these are starting settings, not measured capability claims. Keep only the newest waiting frame. A queue that accumulates seconds of video is worse than a lower frame rate. Send frame identifiers and capture-session identifiers. Reject out-of-order frames and results from an old calibration/session.

Path B, optional accelerated video benchmark: locally uploaded H.264 clip -> NVIDIA GStreamer decode/conversion -> compatible inference integration -> the same normalized detection/event schema. Build this only after Path A works. DeepStream is an alternative implementation of this path, not an extra service that must coexist with duplicate models in memory.

The browser makes outbound connections to the protected app URL, which forwards to port 8000. No extra publicly exposed RTSP/UDP/WebRTC port is assumed. If WebSockets fail through the actual proxy, use same-origin HTTP frame POST plus short polling or supported server events. Test the fallback before demo day.

**6. Observation and decision logic**

Each detection becomes an observation containing frame ID, server timestamp, calibration version, class, confidence, bounding box, and candidate zone. Confidence is model confidence, not a guarantee that the space is safe.

For each aisle, maintain CLEAR, BLOCKED, or UNKNOWN plus last observation time and evidence ID. Candidate starting temporal rules: require three consistent obstructed observations to mark BLOCKED, and a longer clear interval to return to CLEAR. Tune using real clips and publish final thresholds. Missing detections alone must not automatically clear a previously blocked zone when the view is degraded.

UNKNOWN triggers include stale frames, camera disconnect, calibration failure, and supported view-quality failures. The MVP can detect missing calibration markers and severe frame-quality problems; it cannot reliably infer all occlusions. Present this limit explicitly. For an unknown route segment, pause the simulated vehicle before entry.

Keep vehicle footprint and clearance margin in the simulator's configured map units. Inflate obstacles conservatively or disable intersecting graph edges. Do not claim centimeter accuracy on a coarse tabletop zone map.

Use A* or Dijkstra on traversable edges. For MVP, cost is distance divided by configured speed plus explicit fixed turn costs. Blocked edges are excluded. Do not predict clearance times from nothing. The “wait” alternative uses a user-entered assumed clearance time, visibly labeled. If uncertain, offer an operator decision instead of an invented optimum.

Plan changes are versioned. The simulator accepts only the latest valid plan. Every update checks whether the remaining path is still traversable. If an obstruction appears on the current edge, pause the simulation and mark the conflict; do not animate the vehicle through it while explaining a safe route. Resume from a valid position after clearance or an explicitly valid alternative. This is simulation behavior, not a certified real-robot controller.

**7. Minimal API and event contracts**

| Endpoint / channel | Purpose |
|---|---|
| GET /healthz | Process health and mode, no secrets |
| GET /api/status | Model/backend/version, camera age, calibration status |
| POST /api/calibration | Validated map-to-image points and version |
| POST /api/frame | Bounded frame upload when using HTTP transport |
| WS /ws/frames | Optional bounded live frame transport |
| WS /ws/state | Versioned map, event, and plan updates |
| POST /api/orders | Create a simple source-to-destination order |
| POST /api/demo/reset | Reset simulation and explicitly invalidate old pending results |
| GET /api/events | Evidence-linked history |
| GET /api/metrics | Actual measurements and simulation assumptions |

Illustrative event fields: event_id, session_id, frame_id, server_time, input_mode, inference_backend, calibration_version, zone_id, old_state, new_state, evidence_id, old_plan_version, new_plan_version, decision_reason. Use explicit input_mode values LIVE, REPLAY, and SYNTHETIC. Never silently swap between them.

Suggested code modules: api, capture, perception, calibration, occupancy, planner, simulator, events, metrics, and a frontend. Keep model-specific inference behind one adapter so CUDA and TensorRT share postprocessing. Store map configuration, thresholds, and simulator assumptions as small versioned JSON files. Keep a private repository under /workspace and model caches under /cache in the assigned environment.

**8. 3D product design**

Use an isometric warehouse view with simple geometry, readable labels, low visual clutter, and a fixed default camera. Blue indicates the active route, amber indicates a pending decision, red indicates a blocked aisle, and gray indicates unknown observation. Pair color with text/icons. Avoid a decorative world map or multiple disconnected dashboards.

Main surface: warehouse in the center; compact synchronized camera/evidence view; right-side order and decision card; bottom event timeline. Clearly distinguish OBSERVED state, SIMULATED vehicle movement, and ESTIMATED time/cost. On loss of fresh observations, show a prominent stale/unknown badge rather than continuing an apparently live scene.

Controls: Start delivery, Pause, Reset, camera view, Compare decisions, Replay event. Keep technical metrics in a collapsible engineering panel for judges. Use local assets so the live demo does not depend on external font or model downloads. Smooth browser rendering may run at 30 FPS while vision updates at 5 FPS; report them separately.

**9. Development schedule and exit gates**

This schedule assumes the final jury slot is late in deployment week. If assigned earlier, use the October 6 core build and omit optional work. GPU tasks move into the organizer-assigned window; never assume the calendar below authorizes GPU access.

| Date, IST | Work | Required exit gate |
|---|---|---|
| Oct 3, remaining evening | Confirm scope, team ownership, hardware props, jury/GPU availability | One scene sketch, one graph, one demo story |
| Oct 4 | Build tabletop, capture evaluation clips, create 3D map and simulated planner; prepare assets/dependencies | A synthetic event blocks an edge and changes the route; synthetic mode labeled |
| Oct 5 | Inspect Jetson, verify CUDA, deploy API/frontend at app URL, integrate real camera frames and detector | A real prop changes one observed zone and causes one route update |
| Oct 6 | Add calibration checks, temporal state, no-route pause, verified recovery, event log | Complete live block/reroute/block-all/clear loop works repeatedly |
| Oct 7 | TensorRT build/compare if feasible, held-out evaluation, resource and latency metrics | Results table exists; baseline retained; no core functionality regression |
| Oct 8 | Optional H.264/DeepStream path only if already close; business case, slides, demo rehearsal | Feature freeze; recovery procedure and labeled recording ready |
| Oct 9 or assigned earlier slot | Smoke-check URL, camera/calibration, model cache, metrics; present | No dependency upgrades or new features |

Time budget for a five-person team: aim for roughly 100–130 total person-hours spread across the remaining preparation and deployment days. This is a planning estimate, not an event requirement. Example ownership: perception/NVIDIA runtime; calibration/planner; 3D frontend; integration/evaluation; product/demo/business. Each owner supports integration daily rather than handing over at the end.

For a solo builder: target approximately 35–45 focused hours, one input path, one detector, one vehicle, one layout. Drop DeepStream, VLMs, second cameras, and elaborate assets. Keep actual Jetson CUDA inference, physical interaction, reliable failure behavior, and a results table.

During each allocated GPU session, prepare inputs beforehand and record settings/results immediately. Suggested allocation of available GPU time: 15% baseline/smoke tests, 35% engine build/optimization, 30% evaluation, 20% final demo rehearsal and reserve. Engine compilation times are unknown; abandon optimization before it consumes the reserve. Do not leave background inference running outside authorized windows.

**10. Go/no-go decisions**

- End Oct 4: if props are not detected consistently, simplify props/view immediately. Do not expand the label set.
- End Oct 5: if live transport is unreliable, use the tested HTTP fallback. If live capture remains unavailable, disclose replay mode and focus on live inference plus interactive planning while seeking organizer help.
- End Oct 6: if TensorRT migration is still unstable, freeze the working CUDA path. A functioning NVIDIA GPU prototype is better evidence than a nonfunctional engine claim.
- End Oct 7: cut optional features, finish benchmark evidence, practice the exact jury sequence.
- Before demo: if GPU unavailable, notify organizers. Recorded evidence is a fallback presentation aid, not a claim that current inference is live.

**11. Evaluation plan**

Hold back trials recorded with different positions and lighting from threshold tuning. Prepare at least 40 short scenario trials: 8 clear aisle, 8 obstruction in aisle A, 8 obstruction in aisle B, 8 both routes blocked, and 8 removal/recovery. Also run explicit disconnect, stale-input, shifted-camera, late-result, and partial-obstruction tests. List tested obstruction classes and unsupported conditions.

Report event-level obstruction detection, misses, false alarms, false-clear transitions, time to block, time to verified clearance, no-route correctness, and stale-view behavior. Do not inflate counts by treating adjacent video frames as independent trials. Small-sample percentages must include denominators.

Engineering targets to test, not promised results: roughly 5 fresh analyzed frames/second, p95 model-only latency below 150 ms at selected input size, p95 valid-state-update-to-plan below 100 ms on the tiny graph, and physical-change-to-visible-response under 1.5 seconds on the demo network. Temporal confirmation contributes to response delay. If targets fail, reduce frame resolution/complexity or explain the measured tradeoff. A 3-second freshness timeout is an initial candidate for input loss; tune it to the measured transport.

Measure CUDA inference using proper synchronization or CUDA events; distinguish preprocessing, transfer, model execution, postprocessing, temporal confirmation, planning, and browser transport. Browser/server clocks are not assumed synchronized: measure browser send-to-ack with one browser clock and server processing with a monotonic server clock. A filmed physical-change-to-screen test can measure the overall experience. Record GPU contention context; no other team's private workload details are needed.

Compare PyTorch and TensorRT with identical weights, image size, preprocessing, postprocessing, confidence settings, warmup, and held-out inputs. Record output-quality differences, p50/p95 latency, sustained inference FPS, process memory, and errors. Measure first, optimize, then remeasure. Do not extrapolate a small-detector benchmark to Thor peak TFLOPS.

Simulator comparison: static baseline follows the initial route and waits when it becomes blocked; dynamic variant recomputes feasible routes. Both see the same observation trace, vehicle speed, initial conditions, order arrivals, and obstacle-clearance schedule. Both respect blocked edges. Compare completed orders, total travel, makespan, and waiting. Include a case where waiting wins so the comparison is credible. Use a fixed scenario set, not a favorable single run. Distances may be map units and times simulated seconds until physically calibrated.

**12. Business case**

Buyer hypothesis: warehouse operations or automation manager. Initial application: advisory visibility and dispatch planning for one aisle or zone. Existing camera placement, coverage, integration access, and latency requirements must be validated in a pilot. The prototype demonstrates a workflow, not readiness to replace a warehouse management or robot fleet system.

ROI model: monthly avoidable-delay value = disruption events/month × avoidable delay/event in hours × marginal operating cost/hour × fraction actually prevented. Subtract additional route cost, false-alert intervention, hardware amortization, maintenance, and integration. Do not count the same labor time as both wage savings and throughput revenue unless independently justified.

Illustration only: 100 events/month × 0.2 hours/event × $50/hour × 50% prevented = $500/month gross avoided-delay value. This is not a customer result and may not justify new hardware by itself. That is useful information: deployments need more event volume, more operational value, multi-zone utilization, or an existing edge device. Show a low/base/high sensitivity table instead of claiming universal ROI.

Four-week pilot proposal after the hackathon: week 1 baseline data and camera calibration; week 2 advisory shadow mode; week 3 measured operator recommendations; week 4 review false alerts, response times, operational value, and integration needs. Actual automatic equipment control is a separate future project requiring appropriate engineering and validation.

Commercial path: paid discovery/integration plus a per-site software/support offering. Do not present hypothetical prices as validated willingness to pay. Scalability: individual sites process observations at the edge; central systems receive event metadata and summaries. This is a future architecture, not functionality claimed in the hackathon MVP.

**13. Ten-minute live demo**

| Time | Action / evidence |
|---|---|
| 0:00–0:45 | Problem and one-sentence promise; explain real camera and simulated vehicle |
| 0:45–1:30 | Show physical map, matched 3D view, inference backend/device, current camera status |
| 1:30–2:30 | Start order and show baseline route |
| 2:30–4:00 | Judge or operator places obstruction; highlight detected zone and replacement route |
| 4:00–5:00 | Show why the route changed and its estimated consequence |
| 5:00–6:00 | Block both routes; vehicle pauses with no feasible route |
| 6:00–7:00 | Remove obstruction; verify clearance and resume |
| 7:00–8:00 | Disconnect or cover the validated observation area; show unknown/stale behavior |
| 8:00–9:00 | Results panel and evidence replay; distinguish live from replay |
| 9:00–10:00 | Business implication, one limitation, pilot proposal |

Avoid relying on internet chat APIs or model downloads during the demo. Pre-warm the selected model during the authorized session. Keep a 60–90 second labeled backup video and a local configuration snapshot. Reset should restore a known clean order/session without editing code.

**14. Seven-minute technical/business presentation**

Seven slides, approximately one minute each: (1) operational problem and buyer; (2) product loop and originality; (3) architecture and NVIDIA components actually used; (4) calibration/temporal/planning decisions; (5) measured performance and failure cases; (6) business assumptions and pilot economics; (7) limits, scaling path, lessons learned.

Prepare answers: Is this a game? Real perception drives the map; execution is explicitly simulated. Why Jetson? The prototype demonstrates local accelerated perception and a route to on-site processing; the remote demo still needs internet. Where is AI? In learned visual perception, while route search is a deterministic algorithm. What is original? The observation-to-operation integration and verified recovery. What happens when it is unsure? Affected state becomes unknown and the simulated route pauses. What does the ROI prove? Only a hypothesis until a customer pilot validates inputs.

**15. Preflight commands for the assigned environment**

These are suggested read-only checks for your team's environment; they have not been run on your remote Jetson here.

```bash
python3 -c "import torch; print('torch', torch.__version__); print('cuda', torch.version.cuda); print('available', torch.cuda.is_available())"
python3 -c "import tensorrt as trt; print('TensorRT', trt.__version__)"
python3 -m pip show torch torchvision numpy
nvidia-smi
gst-inspect-1.0 nvv4l2decoder
gst-inspect-1.0 nvvidconv
gst-inspect-1.0 nvinfer
gst-inspect-1.0 nvstreammux
command -v trtexec
df -h /workspace /cache
```

An unavailable TensorRT import or GStreamer plugin is a discovery result, not authorization to install system packages. Follow the guide: dry-run proposed user package installs and stop if they replace torch, torchvision, or numpy; ask organizers. Do not use sudo, apt, host Docker, clock/power tuning, or writes to /usr, /etc, or /opt.

Serve the built frontend and API from the same FastAPI app. Suggested demo launch, after the app exists:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Use a single worker initially to avoid loading duplicate models. Omit auto-reload for the jury session. Confirm the root page, API, camera permission, WebSocket/HTTP fallback, authentication refresh, and reset behavior on the real protected URL. Never embed team credentials in the frontend or slides.

Build TensorRT engines in the assigned compatible target environment unless compatibility has been explicitly established. Engine runtime/hardware compatibility is not assumed. Preserve original weights, export settings, and the working CUDA adapter. Avoid exporters that silently fetch/upgrade protected dependencies; precheck the conversion path.

**16. Definition of done**

- Real camera frames produce actual GPU model detections on assigned Jetson.
- A physical obstruction changes a mapped aisle, not just a UI toggle.
- Route changes respect observed occupancy; no-route and stale-input states are handled.
- Removal is verified before resuming.
- Live/replay/synthetic observations, simulated actions, and estimated economics are labeled.
- Judging URL works from the intended browser session on port 8000.
- Actual backend/model versions and metrics are available.
- Held-out evaluation and a fair simulation baseline are documented.
- Private code is saved; weights are cached; credentials absent from artifacts.
- Presentation fits 7 minutes; live demo fits 10 minutes; feedback allocation follows the organizer's slot.
- Backup clip and restart/reset procedure are ready.

**Reference notes**

Event rules, quotas, dates, and scoring above come from the participant's supplied guide. Current online documentation may describe versions newer than the provided image. The installed environment is authoritative.

- NVIDIA DeepStream installation and compatibility: https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_Installation.html
- NVIDIA DeepStream 8.0 pipeline overview: https://docs.nvidia.com/metropolis/deepstream/8.0/text/DS_Overview.html
- NVIDIA accelerated GStreamer and Thor codec notes: https://docs.nvidia.com/jetson/archives/r39.2.1/DeveloperGuide/SD/Multimedia/AcceleratedGstreamer.html
- NVIDIA TensorRT best practices: https://docs.nvidia.com/deeplearning/tensorrt/latest/performance/best-practices.html
- NVIDIA TensorRT engine compatibility: https://docs.nvidia.com/deeplearning/tensorrt/latest/inference-library/engine-compatibility.html
- Ultralytics YOLO11 TensorRT example: https://www.ultralytics.com/blog/optimizing-ultralytics-yolo-models-with-the-tensorrt-integration
- Three.js browser renderer documentation: https://threejs.org/docs/pages/WebGLRenderer.html

These sources establish component capabilities; they do not establish FlowTwin performance, compatibility with the assigned image, or business outcomes. Those must be measured during implementation.
