#!/usr/bin/env python3
"""Build a voiced portrait short straight from <dir>/part.md (no render.py needed).

usage: .venv/bin/python build_part.py <part dir> [--lint] [--dry-run] [--out DIR]
  --lint     check narration and layout only, print problems, render nothing
  --dry-run  voice + timing table, no video
  --out DIR  copy the finished <slug>_voiced.mp4 there
  --sheet PNG  save a contact sheet of every scene's final state (for a visual check)

part.md: '# Title', optional 'Tag: SHORT TAG', then scenes:
  ## Heading
  Visual: <kind> | item | item ...     kinds: title (chips) and templates.KINDS
  - beat ...
The full engine log goes to <dir>/build.log; the console gets one result line.
"""

import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import engine_short as E  # noqa: E402
import skin as S  # noqa: E402
import templates as T  # noqa: E402
import voice  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

SERIES = {"Quick_system_design_short": ("QUICK SYSTEM DESIGN", "Quick System Design Series"),
          "Quick_react": ("QUICK REACT", "Quick React Series"),
          "Quick_JavaScript": ("QUICK JS & NODE", "Quick JS & Node Series")}
DEFAULT_SERIES = ("QUICK REVISION", "Quick Revision Series")


def parse_part(path):
    title, tag, scenes, cur = "", "", [], None
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.startswith("# ") and not title:
            title = ln[2:].strip()
        elif ln.startswith("Tag:") and cur is None:
            tag = ln[4:].strip()
        elif ln.startswith("## "):
            cur = dict(heading=ln[3:].strip(), visual="", beats=[])
            scenes.append(cur)
        elif cur is not None and ln.startswith("Visual:"):
            cur["visual"] = ln[7:].strip()
        elif cur is not None and ln.startswith("- "):
            cur["beats"].append(ln[2:].strip())
    return title, tag or title.upper()[:18], scenes


def lint_text(scenes):
    probs = []
    for i, sc in enumerate(scenes, 1):
        if not sc["beats"]:
            probs.append(f"scene {i}: no beats")
        if sum(len(b) + 1 for b in sc["beats"]) >= 800:
            probs.append(f"scene {i}: narration is 800+ characters")
        for b in sc["beats"]:
            n = len(b.split())
            if not 3 <= n <= 45:
                probs.append(f"scene {i}: beat has {n} words (3-45): {b[:40]}...")
            caps = re.findall(r"\b[A-Z]{2,}\b|[&%=<>/]", b)
            if [c for c in caps if c not in voice.PRON]:
                probs.append(f"scene {i}: spell out for the voice: {caps}")
    return probs


def build_scenes(title, tag, scenes, kicker, footer):
    out, probs = [], []
    for i, sc in enumerate(scenes):
        kind, _, rest = sc["visual"].partition("|")
        kind, items = kind.strip(), [s for s in (x.strip() for x in rest.split("|")) if s]
        if i == 0:
            chips = [c.strip() for c in rest.split(",") if c.strip()] if kind == "title" else []
            draw = T.Title(title, sc["heading"], chips, kicker)
            out.append(dict(kind="diagram", live=True, heading="", title_card=True, tag=tag,
                            footer=footer, draw=draw, beats=sc["beats"]))
            continue
        if kind not in T.KINDS or not items:
            probs.append(f"scene {i + 1}: Visual must be '<kind> | item | ...' "
                         f"with kind in {sorted(T.KINDS)}")
            continue
        draw = T.KINDS[kind](items, f"scene {i + 1} {kind}").bind(len(sc["beats"]))
        out.append(dict(kind="diagram", live=True, heading=sc["heading"], tag=tag, footer=footer,
                        draw=draw, beats=sc["beats"]))
    return out, probs


def frame(spec, now=None, step=None, progress=None):
    """One finished frame (PIL RGB) in the skin.py style: chrome + the scene's layout."""
    surf = S.new_canvas()
    pen = S.Pen(surf.getCanvas())
    S.chrome(pen, spec["heading"], spec["tag"].capitalize(), spec["footer"],
             None if spec.get("title_card") else progress)
    spec["draw"].paint_at(pen, now=now, step=step)
    return S.to_pil(surf)


def lint_layout(specs):
    """Fit every layout (no drawing); collect template warnings + long headings."""
    T.WARN.clear()
    probs = []
    for i, sp in enumerate(specs, 1):
        if sp["draw"].plan is None:
            sp["draw"].fit(S.Pen())
        if sp["heading"] and len(S.heading_lines(sp["heading"])) > 2:
            probs.append(f"scene {i}: heading wraps to 3+ lines; shorten it")
    return probs + T.WARN


def live_rendering():
    """Draw every scene frame by frame on the narration's own clock (word-synced reveals,
    highlight, flowing packets). Patched in memory only, like voiced.py: engine_short.py is unchanged."""
    orig_states, Base = E.frame_states, E.SceneRenderer

    def frame_states(pl):
        spec = pl["spec"]
        if not spec.get("live"):
            yield from orig_states(pl)
            return
        starts = [c / E.FPS for c in pl["cues_f"]]
        spec["draw"].set_times(starts, spec["_words"], pl["frames"] / E.FPS)
        print(f"  cues for '{spec['heading']}':", *spec["draw"].timing_log(), sep="\n    ")
        for f in range(pl["frames"]):
            yield ("live", f, pl["frames"], round((f + 1) / E.INTRO_F, 3) if f < E.INTRO_F else 1.0)

    class Renderer(Base):
        def draw(self, state):
            if state[0] != "live":
                return super().draw(state)
            _, f, n, intro = state
            img = frame(self.spec, now=f / E.FPS, progress=(f + 1) / n)
            return Image.blend(S.to_pil(S.new_canvas()), img, intro) if intro < 1 else img

    E.frame_states, E.SceneRenderer = frame_states, Renderer


def check_mp4(mp4):
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name:format=duration",
                            "-of", "json", str(mp4)], capture_output=True, text=True).stdout
    info = json.loads(probe)
    codecs = "+".join(s["codec_name"] for s in info["streams"])
    dur = float(info["format"]["duration"])
    sil = subprocess.run(["ffmpeg", "-i", str(mp4), "-af", "silencedetect=n=-40dB:d=0.2", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    gaps = [float(x) for x in re.findall(r"silence_duration: ([\d.]+)", sil)]
    return f"{dur:.1f}s {codecs} max-gap {max(gaps, default=0):.2f}s"


def main():
    args = sys.argv[1:]
    lint_only, dry = "--lint" in args, "--dry-run" in args
    out_dir = Path(args[args.index("--out") + 1]) if "--out" in args else None
    sheet = Path(args[args.index("--sheet") + 1]) if "--sheet" in args else None
    here = Path(next(a for a in args if not a.startswith("--")
                     and a not in (str(out_dir), str(sheet)))).resolve()
    slug = here.name
    kicker, footer = SERIES.get(here.parent.name, DEFAULT_SERIES)

    title, tag, scenes = parse_part(here / "part.md")
    specs, probs = build_scenes(title, tag, scenes, kicker, footer)
    probs = lint_text(scenes) + probs + (lint_layout(specs) if not probs else [])
    if sheet:
        tiles = [frame(sp, step=10 ** 6, progress=1.0).resize((360, 640)) for sp in specs]
        img = Image.new("RGB", (5 * 364, -(-len(tiles) // 5) * 644), (60, 60, 60))
        for i, t in enumerate(tiles):
            img.paste(t, ((i % 5) * 364, (i // 5) * 644))
        img.save(sheet)
    if probs or lint_only or sheet:
        print(f"{slug}: {len(probs)} problem(s)", *probs, sep="\n  ")
        sys.exit(1 if probs else 0)

    beats = [b for sc in specs for b in sc["beats"]]
    log = here / "build.log"
    err = os.dup(2)
    with open(log, "w") as fh, contextlib.redirect_stdout(fh):
        os.dup2(fh.fileno(), 2)  # TTS worker + ffmpeg noise goes to the log too
        wavs = voice.synth_many(beats, here / "voice_cache")
        dur_file = here / "voice_cache" / "durations.json"
        dur_file.write_text(json.dumps([round(voice.measure(w), 3) for w in wavs]))
        it = iter(wavs)
        for sp in specs:                               # word timings per beat, for live scenes
            sp["_words"] = [json.loads(next(it).with_suffix(".words.json").read_text())
                            for _ in sp["beats"]]
        live_rendering()
        sys.argv = [sys.argv[0], "--durations", str(dur_file), "--max-entries", "100000"] \
            + (["--dry-run"] if dry else [])
        E.run(specs, title=f"{kicker.title()} - {title}", out_base=here / slug, footer=footer)
        if not dry:
            track = here / "voice_cache" / "track.wav"
            voice.build_track(here / f"{slug}.json", wavs, track)
            voice.mux(here / f"{slug}.mp4", track, here / f"{slug}_voiced.mp4")
            voice.write_srt(here / f"{slug}.json", wavs, here / f"{slug}.srt")
    sys.stdout.flush()
    os.dup2(err, 2)
    if dry:
        total = sum(json.loads(dur_file.read_text())) + 0.25 * len(beats)
        print(f"{slug}: dry run ok, about {total:.0f}s (log: {log})")
        return
    mp4 = here / f"{slug}_voiced.mp4"
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(mp4, out_dir / mp4.name)
    print(f"{slug}: ok {check_mp4(mp4)} lint:0")


if __name__ == "__main__":
    main()
