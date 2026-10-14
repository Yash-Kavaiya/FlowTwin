"""Re-voice the video with Deepgram Aura, keeping every frame's timing. Standard library plus ffmpeg.

Usage (from videos/flowtwin-demo):
    python scripts/deepgram_voice.py [--voice aura-2-thalia-en] [--dry]

Needs DEEPGRAM_API_KEY in the environment or in a .env file next to this project (git-ignored).

What it does, per narration line in SCRIPT.md:
  1. Synthesizes the line with Deepgram text-to-speech.
  2. Tempo-fits it to the frame's existing time slot (pitch preserved), so the built frames stay in sync.
     A line that would need more than a 25% speed change is left at natural length and reported.
  3. Transcribes the fitted audio with Deepgram speech-to-text to get word timings for captions.
Then it rewrites audio_meta.json. The first run saves the slot lengths to voice_slots.json and backs up the
previous voice files, so re-running with another voice always fits the same slots.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAIL_S = 0.15                    # silence left at the end of each slot
MIN_RATIO, MAX_RATIO = 0.8, 1.25  # allowed tempo change


def api_key() -> str:
    key = os.environ.get("DEEPGRAM_API_KEY", "").strip()
    env_file = ROOT / ".env"
    if not key and env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("DEEPGRAM_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        sys.exit("DEEPGRAM_API_KEY is not set. Put DEEPGRAM_API_KEY=... in videos/flowtwin-demo/.env or the environment.")
    return key


def script_lines() -> dict[int, str]:
    """Spoken text per line number: the indented block under each '## Line N' heading."""
    lines, current = {}, None
    for raw in (ROOT / "SCRIPT.md").read_text(encoding="utf-8").splitlines():
        heading = re.match(r"## Line (\d+)", raw)
        if heading:
            current = int(heading.group(1))
        elif current and raw.startswith("    ") and raw.strip():
            lines[current] = (lines.get(current, "") + " " + raw.strip()).strip()
    return lines


def slots() -> dict[int, float]:
    path = ROOT / "voice_slots.json"
    if path.exists():
        return {int(k): v for k, v in json.loads(path.read_text()).items()}
    meta = json.loads((ROOT / "audio_meta.json").read_text())
    found = {int(v["frame"]): float(v["duration_s"]) for v in meta["voices"]}
    path.write_text(json.dumps(found, indent=2))
    return found


def call(url: str, key: str, body: bytes, content_type: str) -> bytes:
    request = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Authorization": f"Token {key}", "Content-Type": content_type})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        sys.exit(f"Deepgram returned HTTP {error.code}: {error.read().decode('utf-8', 'replace')[:400]}")


def wav_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--voice", default="aura-2-thalia-en", help="Deepgram Aura model id")
    parser.add_argument("--dry", action="store_true", help="show the lines and slots without calling Deepgram")
    args = parser.parse_args()

    lines, slot = script_lines(), slots()
    if sorted(lines) != sorted(slot):
        sys.exit(f"SCRIPT.md lines {sorted(lines)} do not match the voice slots {sorted(slot)}")
    if args.dry:
        for n in sorted(lines):
            print(f"{n:02d}  slot {slot[n]:6.3f}s  {len(lines[n].split()):2d} words  {lines[n][:70]}")
        print(f"total {sum(slot.values()):.3f}s, voice {args.voice}")
        return

    key = api_key()
    voice_dir = ROOT / "assets" / "voice"
    backup = ROOT / "assets" / "voice-previous"
    if not backup.exists():
        shutil.copytree(voice_dir, backup)

    voices, notes = [], []
    with tempfile.TemporaryDirectory() as tmp:
        for n in sorted(lines):
            raw = Path(tmp) / f"{n:02d}-raw.wav"
            raw.write_bytes(call(
                f"https://api.deepgram.com/v1/speak?model={args.voice}&encoding=linear16&sample_rate=48000&container=wav",
                key, json.dumps({"text": lines[n]}).encode("utf-8"), "application/json"))
            # A streamed WAV header can carry a placeholder length, so re-wrap it before measuring.
            clean = Path(tmp) / f"{n:02d}-clean.wav"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-ar", "44100", "-ac", "1", str(clean)],
                           check=True)
            natural = wav_seconds(clean)
            target = slot[n] - TAIL_S
            ratio = natural / target
            final = voice_dir / f"{n:02d}.wav"
            if MIN_RATIO <= ratio <= MAX_RATIO:
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(clean), "-filter:a", f"atempo={ratio:.5f}",
                                "-ar", "44100", "-ac", "1", str(final)], check=True)
            else:
                shutil.copy(clean, final)
                notes.append(f"line {n:02d}: natural {natural:.2f}s vs slot {slot[n]:.2f}s needs x{ratio:.2f}; left unfitted")
            fitted = wav_seconds(final)

            heard = json.loads(call("https://api.deepgram.com/v1/listen?model=nova-3&punctuate=true",
                                    key, final.read_bytes(), "audio/wav"))
            spoken = heard["results"]["channels"][0]["alternatives"][0].get("words", [])
            words = [{"id": i, "text": w.get("punctuated_word") or w["word"],
                      "start": round(w["start"], 3), "end": round(w["end"], 3)} for i, w in enumerate(spoken)]
            voices.append({"frame": n, "path": f"assets/voice/{n:02d}.wav", "duration_s": slot[n], "words": words})
            print(f"{n:02d}  natural {natural:5.2f}s  tempo x{ratio:4.2f}  fitted {fitted:5.2f}s / slot {slot[n]:5.2f}s  "
                  f"{len(words)} words timed")

    meta_path = ROOT / "audio_meta.json"
    meta = json.loads(meta_path.read_text())
    meta["voices"] = voices
    meta_path.write_text(json.dumps(meta, indent=2))
    script = ROOT / "SCRIPT.md"
    script.write_text(re.sub(r"\*\*Voice:\*\*.*", f"**Voice:** {args.voice} (Deepgram Aura)", script.read_text(encoding="utf-8"),
                             count=1), encoding="utf-8")
    for note in notes:
        print("NOTE", note)
    print(f"audio_meta.json updated: {len(voices)} lines, voice {args.voice}")


if __name__ == "__main__":
    main()
