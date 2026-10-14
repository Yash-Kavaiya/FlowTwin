#!/usr/bin/env bash
# Start FlowTwin on the Jetson: one worker, no reload, port 8000.
# Usage: scripts/run_jetson.sh [weights]        default /cache/flowtwin/yolo11n.pt
# Optional, only after bench.py --variants shows a gain: FLOWTWIN_HALF=1 FLOWTWIN_GPU_PREPROCESS=1
set -euo pipefail

cd "$(dirname "$0")/.."
export FLOWTWIN_MODEL="${1:-${FLOWTWIN_MODEL:-/cache/flowtwin/yolo11n.pt}}"
export YOLO_AUTOINSTALL=False

if [ ! -f "$FLOWTWIN_MODEL" ]; then
  echo "Weights not found: $FLOWTWIN_MODEL" >&2
  echo "Cache them during the GPU window, or pass the path as the first argument." >&2
  exit 1
fi
if [ ! -f frontend/dist/index.html ]; then
  echo "frontend/dist is missing: copy it from the laptop build." >&2
  exit 1
fi

echo "Serving $FLOWTWIN_MODEL on port 8000 (Ctrl+C to stop)"
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
