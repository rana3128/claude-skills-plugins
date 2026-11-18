---
name: make-video
description: Generate animated, voiced portrait (1080x1920) YouTube Shorts from a study guide or topic - split a guide into parts, write narration, build kinetic word-synced scenes, voice them with Kokoro TTS and render MP4s. Use when the user asks to make, generate, render or re-render a short, video, part or episode, or to turn a document into a Shorts series.
---

# Make voiced kinetic Shorts

Everything renders with the bundled pipeline in `pipeline/` next to this file
(the "Base directory for this skill" shown when the skill loads).

## 0. Setup (once per project)
If the project has no `video_gen/` folder with `kinetic_build.py`, create it:
```bash
mkdir -p video_gen && cp <skill dir>/pipeline/* video_gen/
cd video_gen
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt            # drawing (Python 3.11+)
python3.12 -m venv .venv-tts && .venv-tts/bin/pip install -r requirements-tts.txt  # Kokoro voice
```
`ffmpeg` must be on PATH. `voice.py` runs the TTS worker in `.venv-tts` next to it.
Run every command from `video_gen/`.

## 1. Read the rules
- **`DESIGN.md`** - the kinetic visual style. Hard rules: boxes stack in one full-width column,
  never side by side; no accent bars on box edges; big text; each element appears on its spoken word;
  headings fit one line (about 30 characters); **no burned-in subtitles**.
- **`PARTS.md`** - the `part.md` format, narration rules, and how to split a guide.
Don't read `engine_short.py`, `templates.py` or `skin.py` unless debugging them.

## 2. New series: split first, get approval
1. Analyse the source guide and **propose a part list** (one concept per part, about 90-125 s each).
   **Stop for user approval.** Never cut content to hit a length; add examples and the "why" instead.
2. Write every `<series>/pNN_<slug>/part.md`, plus `<series>/README.md` with the analysis and a parts table.
3. Add the series folder to `SERIES` in `build_part.py` (kicker + footer). Optionally add a logo
   mark to `MARKS` in `kinetic.py`.
4. Lint narration: `.venv/bin/python build_part.py <part dir> --lint` and fix every problem.
   Narration: no recap, no welcome, jump straight to the topic; no symbols or code; spell out
   acronyms for the voice; beats at most 45 words.

## 3. Scenes
Each part gets a `scenes.py` defining `SCENES`. Two styles (see `examples/`):
- **Declarative stage blocks** (preferred, fast): `SCENES = K.part(word, tag, chips, [[blocks...], ...])`
  using `Track, Pipe, Rows, Code, Lanes, Bars, Ring, Fan, Chips, Big, Note`. A cue is a word prefix
  (searched after the block's previous cue), `(word, beat)` or a beat number. Example: `examples/p03_*`.
- **Hand-written `Scene` classes** for a metaphor the blocks can't show. Example: `examples/p01_*`.
List cue words in spoken order, or cues come back MISSING.

## 4. Check, then render
```bash
.venv/bin/python kinetic_build.py <part dir> --stills /tmp/pNN.png   # contact sheet + cue report
.venv/bin/python kinetic_build.py <part dir> --out <series>/output   # final <slug>_voiced.mp4
.venv/bin/python cue_scan.py <series>/p*_*                           # text-only sync check
```
Fix every `MISSING` cue and `overflow` before the final render. For a whole series, render the first
two parts and get the user's OK on the look, then run the rest 3 at a time in the background
(`xargs -P 3`).

## 5. Report
A table: MP4 link, topic, length, longest silence (target under 1 s). Mark the parts rendered in
the series README. Say plainly what was not checked (frames not viewed, audio not listened to).

## Never
- Put boxes side by side, edge accent bars, small text, or burned-in subtitles.
- Propose per-video voice calibration; sync is word-timed and generic.
- Edit `engine_short.py` directly; `build_part.py` patches it in memory.
