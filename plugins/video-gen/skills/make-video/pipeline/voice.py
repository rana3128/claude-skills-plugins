#!/usr/bin/env python3
"""Local voiceover for any video: Kokoro TTS -> per-beat WAVs -> audio track -> voiced MP4 + SRT.

Speech runs in .venv-tts (tts_worker.py, Python 3.12); this file is stdlib-only.
  .venv/bin/python voice.py --sample     # voice samples to pick from
"""

import array
import hashlib
import json
import re
import subprocess
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TTS_PY = ROOT / ".venv-tts" / "bin" / "python"
WORKER = ROOT / "tts_worker.py"
SR = 24000

VOICE = "af_heart"
SPEED = 1.0

# Narration spells acronyms for the old Vids voice; fix only what Kokoro says badly.
PRON = {"J SON": "Jason", "JSON": "Jason", "HyDE": "Hyde",
        "thenable": "then able", "iterables": "itterables", "iterable": "itterable",
        "libuv": "lib U V", "epoll": "E poll", "kqueue": "K queue"}


def speakable(text):
    for a, b in PRON.items():
        text = re.sub(rf"\b{re.escape(a)}\b", b, text)
    return text


def _run_worker(items):
    if not items:
        return
    r = subprocess.run([str(TTS_PY), str(WORKER)], input=json.dumps({"items": items}),
                       text=True, stderr=sys.stderr)
    if r.returncode:
        sys.exit("TTS worker failed")


def synth_many(texts, cache_dir, voice=VOICE, speed=SPEED):
    """One WAV per text, cached by content hash. Returns the WAV paths."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    paths, todo = [], []
    for t in texts:
        s = speakable(t)
        h = hashlib.sha1(f"{voice}|{speed}|{s}".encode()).hexdigest()[:16]
        p = cache_dir / f"{h}.wav"
        paths.append(p)
        if not p.exists() or not p.with_suffix(".words.json").exists():
            todo.append({"text": s, "out": str(p), "voice": voice, "speed": speed})
    if todo:
        print(f"Synthesising {len(todo)} of {len(texts)} beats with {voice} @ {speed}x")
    _run_worker(todo)
    return paths


def measure(wav_path):
    with wave.open(str(wav_path)) as w:
        return w.getnframes() / w.getframerate()


def build_track(json_path, wavs, out_wav):
    """Place each beat's WAV at its JSON start time; silence elsewhere."""
    data = json.loads(Path(json_path).read_text())
    total = int(round(data["duration"] * SR))
    buf = array.array("h", bytes(2 * total))
    for scene, wav_path in zip(data["scenes"], wavs):
        with wave.open(str(wav_path)) as w:
            clip = array.array("h", w.readframes(w.getnframes()))
        start = int(round(scene["start"] * SR))
        n = max(0, min(len(clip), total - start))
        buf[start:start + n] = clip[:n]
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(buf.tobytes())


def mux(silent_mp4, wav, out_mp4):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent_mp4), "-i", str(wav),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", str(out_mp4)], check=True)


def caption_text(speech):
    speech = speech.replace("[slow pace]", "").strip()
    s = re.sub(r"\b(?:[A-Z] )+[A-Z]\b", lambda m: m.group(0).replace(" ", ""), speech)
    return s.replace("J SON", "JSON")


def _ts(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_srt(json_path, wavs, out_srt):
    data = json.loads(Path(json_path).read_text())
    lines = []
    for i, (sc, wav_path) in enumerate(zip(data["scenes"], wavs), 1):
        end = min(sc["start"] + measure(wav_path), data["duration"])
        lines += [str(i), f"{_ts(sc['start'])} --> {_ts(end)}", caption_text(sc["speech"]), ""]
    Path(out_srt).write_text("\n".join(lines), encoding="utf-8")


def sample(out_dir):
    beats = ["You describe each tool to the model. A name, a description, and a J SON schema of its "
             "parameters. For example, get order status, which takes an order I D.",
             "Your code validates the arguments, and checks this user is allowed to see that order. "
             "Always enforce permissions on the server, not in the prompt, using an A P I and an L L M."]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    items = []
    for v in ["am_michael", "am_adam", "am_fenrir", "bm_george", "af_heart", "af_bella"]:
        for sp in (1.0, 1.1):
            items.append({"text": " ".join(beats), "out": str(out_dir / f"{v}_{sp}.wav"), "voice": v, "speed": sp})
    _run_worker(items)
    print(f"Samples in {out_dir}")


if __name__ == "__main__":
    if "--sample" in sys.argv:
        sample(sys.argv[sys.argv.index("--sample") + 1] if len(sys.argv) > 2 else ROOT / "voice_samples")
