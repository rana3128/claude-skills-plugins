#!/usr/bin/env python3
"""Build a portrait Short in the kinetic design (DESIGN.md) from <part dir>/part.md + <part dir>/scenes.py.

usage: .venv/bin/python kinetic_build.py <part dir> [--stills PNG] [--out DIR]
  --stills PNG  contact sheet at the end of every beat + the cue table (no video; uses the voice cache)
  --out DIR     copy the finished <slug>_voiced.mp4 there

scenes.py defines SCENES: one Scene subclass per `##` scene of part.md, in order, and KICKER for the
title (e.g. "QUICK REACT  ·  HOOKS"). Narration, voice, timing and muxing are build_part.py's.
"""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import build_part as BP  # noqa: E402
import kinetic as K  # noqa: E402
import skin as S  # noqa: E402


def load_scenes(here):
    spec = importlib.util.spec_from_file_location(f"scenes_{here.name}", here / "scenes.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_builder(mod, kicker):
    def build_scenes(title, tag, scenes, _kicker, footer):
        if len(scenes) != len(mod.SCENES):
            return [], [f"part.md has {len(scenes)} scenes but scenes.py has {len(mod.SCENES)}"]
        specs = []
        for i, (sc, cls) in enumerate(zip(scenes, mod.SCENES)):
            specs.append(dict(kind="diagram", live=True, heading=sc["heading"] if i else "", tag=tag,
                              footer=footer, draw=cls(sc["heading"]), beats=sc["beats"], _idx=i,
                              _n=len(scenes), _kicker=kicker, title_card=i == 0))
        return specs, []
    return build_scenes


def frame(spec, now=None, step=None, progress=None):
    t = spec["draw"].total if now is None else now
    surf = K.new_canvas(t)
    pen = S.Pen(surf.getCanvas())
    K.chrome(pen, spec["_idx"], spec["_n"], 1.0 if progress is None else progress,
             spec["heading"], spec["_kicker"], t)
    spec["draw"].paint_at(pen, now=t)
    return S.to_pil(surf)


def stills(here, builder, png):
    from PIL import Image
    title, tag, scenes = BP.parse_part(here / "part.md")
    specs, probs = builder(title, tag, scenes, "", "")
    if probs:
        sys.exit("\n".join(probs))
    wavs = BP.voice.synth_many([b for sp in specs for b in sp["beats"]], here / "voice_cache")
    it = iter(wavs)
    tiles, missing = [], 0
    for sp in specs:
        ws = [next(it) for _ in sp["beats"]]
        words = [json.loads(w.with_suffix(".words.json").read_text()) for w in ws]
        durs = [BP.voice.measure(w) for w in ws]
        starts = [0.6 + sum(durs[:k]) + 0.25 * k for k in range(len(ws))]
        total = starts[-1] + durs[-1] + 0.4
        sp["draw"].set_times(starts, words, total)
        log = sp["draw"].timing_log()
        missing += sum("MISSING" in ln for ln in log)
        print(sp["heading"] or "title", *log, sep="\n  ")
        for k in range(len(ws)):
            tt = starts[k] + durs[k] - 0.05
            tiles.append(frame(sp, now=tt, progress=tt / total).resize((432, 768)))
    cols = 6
    img = Image.new("RGB", (cols * 436, -(-len(tiles) // cols) * 772), (50, 50, 50))
    for i, tl in enumerate(tiles):
        img.paste(tl, ((i % cols) * 436, (i // cols) * 772))
    img.save(png)
    print(f"{here.name}: stills saved ({missing} missing cue(s))")


def main():
    args = sys.argv[1:]
    here = Path(next(a for a in args if not a.startswith("--") and
                     a not in [args[i + 1] for i, x in enumerate(args[:-1]) if x in ("--stills", "--out")])).resolve()
    mod = load_scenes(here)
    kicker, K.FOOTER = BP.SERIES.get(here.parent.name, BP.DEFAULT_SERIES)
    K.MARK = K.MARKS.get(here.parent.name, K.atom)
    builder = make_builder(mod, kicker)
    if "--stills" in args:
        return stills(here, builder, Path(args[args.index("--stills") + 1]))
    BP.build_scenes, BP.frame, BP.lint_layout = builder, frame, (lambda specs: [])
    S.new_canvas = lambda: K.new_canvas(0.0)
    sys.argv = [sys.argv[0], str(here)] + [a for a in args if a != str(here) and Path(a).resolve() != here]
    BP.main()


if __name__ == "__main__":
    main()
