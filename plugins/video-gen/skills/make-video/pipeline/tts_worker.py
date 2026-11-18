#!/usr/bin/env python3
"""Kokoro TTS worker. Runs inside .venv-tts (Python 3.12); called by voice.py.

stdin: {"items": [{"text": ..., "out": "/path.wav", "voice": "am_michael", "speed": 1.0}, ...]}
Writes 24 kHz 16-bit mono WAVs with leading/trailing silence trimmed, plus <name>.words.json:
[[word, start_s, end_s], ...] (word timings in the trimmed WAV, used to sync animations).
"""
import json
import sys
import warnings

warnings.filterwarnings("ignore")

import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402
from kokoro import KPipeline  # noqa: E402

SR = 24000
_pipes = {}


def pipe(voice):
    lang = voice[0]  # 'a' = American, 'b' = British
    if lang not in _pipes:
        _pipes[lang] = KPipeline(lang_code=lang, repo_id="hexgrad/Kokoro-82M")
    return _pipes[lang]


def trim(audio, thresh=0.01, pad=0.04):
    """-> (trimmed audio, samples cut from the start)."""
    idx = np.where(np.abs(audio) > thresh)[0]
    if not len(idx):
        return audio, 0
    p = int(pad * SR)
    start = max(0, idx[0] - p)
    return audio[start: idx[-1] + p], start


def main():
    job = json.load(sys.stdin)
    for i, it in enumerate(job["items"]):
        parts, words, offset = [], [], 0.0
        for r in pipe(it["voice"])(it["text"], voice=it["voice"], speed=it["speed"]):
            a = r.audio.numpy() if hasattr(r.audio, "numpy") else np.asarray(r.audio)
            for tk in r.tokens or []:
                if tk.start_ts is not None and tk.text.strip():
                    words.append([tk.text, offset + tk.start_ts, offset + (tk.end_ts or tk.start_ts)])
            parts.append(a)
            offset += len(a) / SR
        audio, cut = trim(np.concatenate(parts))
        sf.write(it["out"], audio, SR, subtype="PCM_16")
        words = [[w, round(max(0.0, s - cut / SR), 3), round(max(0.0, e - cut / SR), 3)]
                 for w, s, e in words]
        with open(it["out"][:-4] + ".words.json", "w") as fh:
            json.dump(words, fh)
        print(f"  tts {i + 1}/{len(job['items'])}: {len(audio) / SR:.2f}s", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
