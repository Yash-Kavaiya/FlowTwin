# FlowTwin runbook

## Laptop (no GPU, mock detector)

```bash
pip install -r requirements.txt
python -m pytest -q
python -m uvicorn app.main:app --port 8000      # open http://localhost:8000, use SYNTHETIC mode
```

Rebuild the frontend after UI changes: `cd frontend && npm install && npm run build`. `frontend/dist` is committed so the Jetson needs no Node.

## Jetson: first deployment (Oct 5)

1. Upload `deploy/flowtwin-deploy.tar.gz` to the Jetson (drag it into the VS Code file explorer) and unpack it:
   ```bash
   mkdir -p /workspace/FlowTwin /cache/flowtwin && tar -xzf flowtwin-deploy.tar.gz -C /workspace/FlowTwin
   cd /workspace/FlowTwin
   ```
   Rebuild the bundle on the laptop after any change (the command is at the end of this file).
2. Check the environment. This installs nothing; it dry-runs each missing package and stops if the organizer stack (`torch`, `torchvision`, `numpy`, TensorRT, CUDA packages) would change.
   ```bash
   python3 scripts/jetson_preflight.py
   ```
   If it says an install is safe, rerun it with `--install`. If it says STOP, ask the organizers for a compatible version.
3. During the GPU window, prove real GPU inference before anything else, then start the server:
   ```bash
   python3 scripts/gpu_check.py /cache/flowtwin/yolo11n.pt
   bash scripts/run_jetson.sh /cache/flowtwin/yolo11n.pt
   ```
   `gpu_check.py` downloads the weights to that path if they are missing, runs the model in three configurations (baseline, on-device preprocessing, FP16) with CUDA-synchronized timings, and must end with "GPU inference verified". Paste its output into `docs/results.md`. The server runs one worker with no reload; the model loads once and is warmed up before the port opens.
4. Open the organizer URL. The header must show `PyTorch CUDA`, the model file and the real GPU name. If it shows `MOCK`, `FLOWTWIN_MODEL` was not set.
5. Switch input mode to LIVE, start the camera, press Calibrate and click the paper map's corner squares in order 1, 2, 3, 4. The zone outlines drawn on the camera view must sit on the printed aisles; if they do not, calibrate again.
6. Press Verify and click the centre of each wait point when prompted. This is the held-out check: it reports how far each click lands from where the map says that point is, in map units (the map is 100 wide). A few units is fine for zone-level decisions; a large error means recalibrate.

## GPU options

All off by default, so plain PyTorch on CUDA stays the baseline. Turn one on only after `bench.py --variants` shows it is faster on your frames and detects the same things.

| Variable | Effect |
|---|---|
| `FLOWTWIN_MODEL=/path/model.pt` or `.engine` | Weights to serve. An `.engine` file runs through TensorRT. |
| `FLOWTWIN_HALF=1` | FP16 for the PyTorch model on CUDA. Ignored on CPU and for engines. |
| `FLOWTWIN_GPU_PREPROCESS=1` | Resize, pad and normalize on the GPU instead of the CPU. |

The Accelerator panel in the app and `GET /api/gpu` show the device, stack versions, GPU memory, GPU load (with the source it was read from) and p50/p95 per stage. If the platform does not expose GPU load, the panel says so rather than showing a number.

## Choosing props

The detector only treats the classes in `config/thresholds.json` (`supported_classes`: book, bottle, cup) as obstructions; anything else is drawn on the camera view as "unsupported" and ignored. To try another object without editing the file, start the server with `FLOWTWIN_CLASSES="cell phone,scissors"` (COCO class names, comma separated). Once you know what works from overhead, write the final list into the config so the published thresholds match the demo.

## Tabletop

Print the sheet for your use case, `docs/tabletop_<use case>.svg` (regenerate all three with `python scripts/make_print_map.py`; see `use_cases.md`). Fix the camera overhead so all four corner squares are visible. Recalibrate whenever the camera or paper moves.

## Evidence (Oct 7, inside the GPU window)

```bash
python3 scripts/export_trt.py /cache/flowtwin/yolo11n.pt
python3 scripts/bench.py --images data/heldout --variants --weights /cache/flowtwin/yolo11n.pt /cache/flowtwin/yolo11n.engine
FLOWTWIN_MODEL=/cache/flowtwin/yolo11n.pt python3 scripts/eval_trials.py data/trials/manifest.json
python3 scripts/compare_sim.py --markdown
```

Paste each script's output into `docs/results.md` unchanged. `bench.py` and `gpu_check.py` have been run on a CPU-only laptop, so their logic works but their CUDA branches (FP16, GPU memory, GPU load) have never executed. `export_trt.py` has not been run at all.

## Restart during the demo

1. Press Reset in the UI (new session, clean order, same mode). This fixes almost everything.
2. If the page is stuck: Ctrl+C the server, start it again with the command above, reload the page. Calibration is restored from `data/calibration.json`; confirm the zone outlines still line up.
3. If the GPU is unavailable: tell the judges, switch to REPLAY with a recorded clip (the badge says REPLAY), or play the backup video. Never present either as live.

## Preflight on demo day

- Header shows the real backend and GPU name, mode LIVE, observation fresh.
- Zone outlines line up on the camera view.
- One full loop: block A, reroute; block B, pause; clear, resume; cover the camera, UNKNOWN.
- Engineering panel shows measured p50/p95.
- Backup clip opens offline.

## Rebuilding the upload bundle (laptop, Git Bash)

```bash
cd frontend && npm run build && cd ..
tar --exclude='__pycache__' --exclude='.pytest_cache' -czf deploy/flowtwin-deploy.tar.gz     app config scripts tests docs frontend/dist requirements.txt README.md FlowTwin_Hackathon_Plan.md
```
