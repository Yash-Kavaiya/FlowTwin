**You need to run the vision model inside your assigned Jetson environment, then send its detections to FlowTwin.** The 3D website can stay largely the same.

Start with **PyTorch + CUDA**. Add **TensorRT** after the complete loop works. DeepStream is optional.

**1. Use this deployment arrangement**

| Component | Where it runs |
|---|---|
| Webcam capture | Your laptop’s browser |
| AI inference | Your assigned Jetson Thor |
| Aisle status and route planning | Your application |
| 3D rendering | Your laptop’s browser |
| Frontend and API hosting | Jetson application on port 8000 |

For the integrated demo, serve a copy of FlowTwin from your **organizer-provided application URL** alongside the backend. This keeps camera uploads and API requests on the same authenticated origin.

The current hosted concept remains a separate browser simulation until this integration exists.

**2. First, verify your Jetson access**

Open your assigned **VS Code terminal** and run:

```bash
python3 - <<'PY'
import torch
from importlib.metadata import version, PackageNotFoundError

print("CUDA available:", torch.cuda.is_available())
print("PyTorch:", torch.__version__)
print("CUDA runtime:", torch.version.cuda)

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))

for package in [
    "torchvision", "numpy", "ultralytics",
    "tensorrt", "fastapi", "uvicorn"
]:
    try:
        print(package, version(package))
    except PackageNotFoundError:
        print(package, "NOT INSTALLED")
PY
```

**Expected:** `CUDA available: True`.

If it is false, contact the organizers. Follow their guide rather than reinstalling PyTorch.

This confirms GPU availability; the next step confirms actual inference.

**3. Check dependencies before installing anything**

If Ultralytics is missing, inspect the proposed installation:

```bash
python3 -m pip install --user --dry-run ultralytics
```

**If the proposed changes include `torch`, `torchvision`, or `numpy`, stop and ask the organizers.** That is explicitly required by your participant guide.

Only proceed with the reviewed installation if it preserves their protected stack:

```bash
python3 -m pip install --user ultralytics
```

Use an organizer-recommended compatible version when available. Apply the same review process to any backend dependencies.

**4. Prove GPU inference on one image**

Before connecting the camera, upload one tabletop photo as:

```text
/workspace/test-frame.jpg
```

Choose an object the pretrained detector recognizes reliably, such as a book or bottle. Do not assume a generic detector recognizes cardboard pallets.

Run the following **during your GPU window**:

```bash
mkdir -p /cache/flowtwin
cd /cache/flowtwin

YOLO_AUTOINSTALL=False python3 - <<'PY'
import time
import torch
from ultralytics import YOLO

assert torch.cuda.is_available(), "CUDA is unavailable"

# Downloads the weights here if they are not already cached.
model = YOLO("yolo11n.pt")

settings = dict(
    source="/workspace/test-frame.jpg",
    device=0,
    imgsz=640,
    rect=False,
    conf=0.35,
    verbose=False,
)

# Warm up before measuring.
model.predict(**settings)
torch.cuda.synchronize()

started = time.perf_counter()
result = model.predict(**settings)[0]
torch.cuda.synchronize()
elapsed_ms = (time.perf_counter() - started) * 1000

print("GPU:", torch.cuda.get_device_name(0))
print("Model device:", next(model.model.parameters()).device)
print("Prediction call, ms:", round(elapsed_ms, 1))

for box in result.boxes:
    class_id = int(box.cls.item())
    print({
        "object": model.names[class_id],
        "confidence": round(float(box.conf.item()), 3),
        "box": box.xyxy[0].tolist(),
    })
PY
```

Ultralytics supports selecting the GPU using `device=0` and processing images or arrays. [docs.ultralytics.com](https://docs.ultralytics.com/modes/predict?utm_source=chatgpt.com)

**Your first milestone:** the output shows `cuda:0` and sensible detections from your own image.

The printed timing covers the prediction call, including associated processing. Do not label it “model-only latency.”

Pre-download the weights before your reserved session whenever possible.

**5. Put the working model behind an API**

Create a small FastAPI backend with these routes:

| Route | Purpose |
|---|---|
| `GET /api/status` | Actual GPU, model, backend, and readiness |
| `POST /api/frame` | Receive a camera image and return detections |
| `GET /api/state` | Return aisle states and the latest observation time |
| `/` | Serve the FlowTwin frontend |

Implementation requirements:

- Load the model **once at startup**.
- Allow **one inference operation at a time** initially.
- Accept only bounded image sizes.
- Return a frame identifier with every result.
- Include detections and measured server processing time.
- Keep camera freshness separate from model confidence.

FastAPI supports uploaded files through `UploadFile`; multipart uploads require `python-multipart`. Review its installation before adding it. [FastAPI](https://fastapi.tiangolo.com/tutorial/request-files/?utm_source=chatgpt.com)

Launch the application using:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Use a single worker initially so multiple workers do not load duplicate models.

**6. Connect your laptop camera**

The frontend should:

1. Request webcam access with `getUserMedia()`.
2. Capture a resized frame.
3. Send it to `/api/frame`.
4. Wait for that response before sending the next frame.
5. Update the detection overlay and aisle state.

Start with **three to five frames per second**. Increase only after measuring.

Do not use `cv2.VideoCapture(0)` on the remote Jetson expecting it to access your laptop camera. The browser must transmit the images.

**7. Replace FlowTwin’s simulated obstruction input**

The current concept has buttons that change whether aisle A or B is blocked.

Add a separate **camera observation mode**:

| Current behavior | Integrated behavior |
|---|---|
| Button creates an obstruction | Model detects a supported object |
| Button selects aisle A/B | Calibrated image zones identify the affected aisle |
| Immediate state change | Several consistent observations confirm the change |
| Button clears an aisle | Valid observations confirm clearance |

Keep manual scenario controls available in a clearly labeled simulation mode. Disable them from silently overriding camera-derived states.

For your first physical setup:

- Fix the camera position.
- Draw two aisle polygons on the camera image.
- Associate each polygon with the corresponding 3D aisle.
- Treat a supported detection overlapping a polygon as a candidate obstruction.
- Confirm it over multiple observations.
- Mark the view **UNKNOWN** when frames become stale.

**Do not interpret one missed detection as proof that an aisle is clear.**

**8. Add TensorRT after CUDA works**

TensorRT changes the inference backend. Your camera transport, map, planner, and 3D scene can remain unchanged.

Before export:

- Verify that the installed TensorRT imports successfully.
- Confirm export dependencies with the organizers.
- Keep automatic dependency installation disabled.
- Build during your assigned GPU window.
- Retain the working `.pt` model.

A version-aware export example:

```python
import os
os.environ["YOLO_AUTOINSTALL"] = "False"

from ultralytics import YOLO
from ultralytics.cfg import DEFAULT_CFG_DICT

model = YOLO("/cache/flowtwin/yolo11n.pt")

# Recent releases use quantize; older releases use half.
precision = (
    {"quantize": 16}
    if "quantize" in DEFAULT_CFG_DICT
    else {"half": True}
)

engine_path = model.export(
    format="engine",
    device=0,
    imgsz=640,
    batch=1,
    dynamic=False,
    workspace=1,
    simplify=False,
    **precision,
)

print(engine_path)
```

This requires compatible installed export dependencies. `workspace=1` limits the TensorRT builder workspace setting; it does **not** cap total process memory.

Ultralytics documents TensorRT export and FP16 configuration. Engines are hardware/runtime-specific, so build for the assigned deployment environment. [Ultralytics](https://docs.ultralytics.com/integrations/tensorrt?utm_source=chatgpt.com)

Then load the exported engine:

```python
model = YOLO("/cache/flowtwin/yolo11n.engine", task="detect")
```

Repeat the same image tests and compare detection quality and latency. If conversion fails, keep the working CUDA version while resolving compatibility.

**9. What to show the judges**

Display actual values returned by the backend:

- GPU name.
- Model name.
- **PyTorch CUDA** or **TensorRT** backend.
- Fresh camera frame and detection overlay.
- Median/p95 processing latency.
- Observation age.
- Reason for the latest route change.

Avoid hardcoded “GPU active” badges or invented performance figures.

**Your implementation order should be:**

1. **One image produces real CUDA detections.**
2. **Browser camera frames reach that model.**
3. **Detections change FlowTwin’s aisle states.**
4. **A physical obstruction causes rerouting or a pause.**
5. **TensorRT improves the measured pipeline, if compatible.**

**Start by running the environment-check command and share its output—without passwords or tokens.** That will determine the exact installation and export steps your assigned Jetson supports.