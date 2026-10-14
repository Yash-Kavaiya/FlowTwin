"""Check the assigned Jetson environment before installing or starting anything. Standard library only.

Usage: python3 scripts/jetson_preflight.py [--install] [--weights /cache/flowtwin/yolo11n.pt]

For each missing package it asks pip for a dry run and reads what would change. If the organizer-provided
stack (torch, torchvision, numpy, TensorRT, NVIDIA packages) would be touched, it stops and tells you to ask
the organizers. With --install it performs only the installs that passed that check, as --user installs.
It never uses sudo and never writes outside the user site.
"""
import argparse
import importlib.util
import re
import shutil
import socket
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = ("fastapi", "uvicorn", "ultralytics")
# nvidia-ml-py is only the pure-Python NVML bindings, not part of the CUDA runtime, so it is allowed.
PROTECTED = re.compile(r"^(torch|torchvision|torchaudio|numpy|tensorrt.*|nvidia-(?!ml-py$).*|pycuda)$", re.IGNORECASE)
REVIEW = re.compile(r"^opencv-.*$", re.IGNORECASE)  # a pip OpenCV wheel can shadow a system build


def installed(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def would_install(package: str) -> tuple[list[str], str]:
    """Names pip would install for package, from a dry run. Returns (names, raw error text)."""
    run = subprocess.run([sys.executable, "-m", "pip", "install", "--user", "--dry-run", package],
                         capture_output=True, text=True)
    if run.returncode != 0:
        return [], (run.stderr or run.stdout).strip()[-400:]
    names = []
    for line in run.stdout.splitlines():
        if line.startswith("Would install"):
            # "Would install fastapi-0.115.0 starlette-0.38.6": the version is the last dash-separated field
            names = [item.rsplit("-", 1)[0] for item in line.split()[2:]]
    return names, ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--install", action="store_true", help="perform the installs that passed the dry-run check")
    parser.add_argument("--weights", default="/cache/flowtwin/yolo11n.pt")
    args = parser.parse_args()
    problems, notes = [], []

    print("## Protected stack (recorded, never changed by this script)")
    for name in ("torch", "torchvision", "numpy", "tensorrt"):
        print(f"- {name}: {installed(name) or 'NOT INSTALLED'}")
    if importlib.util.find_spec("torch"):
        import torch
        print(f"- CUDA available: {torch.cuda.is_available()}"
              + (f" ({torch.cuda.get_device_name(0)})" if torch.cuda.is_available() else ""))
        if not torch.cuda.is_available():
            problems.append("CUDA is not available: contact the organizers, do not reinstall PyTorch")
    else:
        problems.append("PyTorch is not installed: contact the organizers")

    print("\n## Application packages")
    for package in REQUIRED:
        have = installed(package)
        if have:
            print(f"- {package}: {have}")
            continue
        names, error = would_install(package)
        if error:
            print(f"- {package}: MISSING, and the dry run failed: {error}")
            problems.append(f"could not dry-run {package}")
            continue
        touched = [n for n in names if PROTECTED.match(n)]
        review = [n for n in names if REVIEW.match(n)]
        print(f"- {package}: MISSING. A --user install would add: {', '.join(names) or 'nothing'}")
        if touched:
            problems.append(f"installing {package} would change the protected stack ({', '.join(touched)}): "
                            "STOP and ask the organizers for a compatible version")
            continue
        if review:
            notes.append(f"installing {package} adds {', '.join(review)}, which can shadow a system OpenCV build")
        if args.install:
            done = subprocess.run([sys.executable, "-m", "pip", "install", "--user", package])
            print(f"  installed {package}" if done.returncode == 0 else f"  install of {package} FAILED")
            if done.returncode != 0:
                problems.append(f"install of {package} failed")
        else:
            notes.append(f"safe to run: {sys.executable} -m pip install --user {package}   (or rerun with --install)")

    print("\n## Deployment")
    dist = ROOT / "frontend" / "dist" / "index.html"
    print(f"- built frontend: {'present' if dist.exists() else 'MISSING (copy frontend/dist from the laptop)'}")
    if not dist.exists():
        problems.append("frontend/dist is missing")
    weights = Path(args.weights)
    print(f"- weights {weights}: {'present' if weights.exists() else 'missing (cache them during the GPU window)'}")
    for path in ("/workspace", "/cache"):
        if Path(path).exists():
            free = shutil.disk_usage(path).free / 2**30
            print(f"- free space on {path}: {free:.1f} GB")
    with socket.socket() as probe:
        busy = probe.connect_ex(("127.0.0.1", 8000)) == 0
    print(f"- port 8000: {'IN USE (another server is running)' if busy else 'free'}")
    for tool in ("nvidia-smi", "trtexec"):
        print(f"- {tool}: {shutil.which(tool) or 'not on PATH'}")

    for note in notes:
        print(f"\nNote: {note}")
    if problems:
        print("\nNOT READY:")
        for p in problems:
            print(f"- {p}")
        return 1
    print("\nReady. Next: python3 scripts/gpu_check.py " + args.weights)
    return 0


if __name__ == "__main__":
    sys.exit(main())
