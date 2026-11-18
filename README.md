# claude-skills-plugins

Personal [Claude Code](https://claude.com/claude-code) plugin marketplace.

## Install

```
/plugin marketplace add rana3128/claude-skills-plugins
/plugin install video-gen@claude-skills-plugins
```

## Plugins

| Plugin | Skill | What it does |
|---|---|---|
| [video-gen](plugins/video-gen) | `make-video` | Turns a study guide into a series of animated, voiced portrait (1080x1920) YouTube Shorts. Splits the guide into parts, writes narration, builds kinetic word-synced scenes, voices them with Kokoro TTS and renders MP4s. |

### video-gen

The skill bundles its rendering pipeline in [`skills/make-video/pipeline/`](plugins/video-gen/skills/make-video/pipeline):

- `kinetic.py`, `kinetic_build.py` - kinetic scene engine (Skia) and per-part builder
- `build_part.py`, `engine_short.py`, `skin.py`, `templates.py` - `part.md` parsing, lint, layout, render
- `voice.py`, `tts_worker.py` - Kokoro TTS with word timings
- `cue_scan.py` - text-only sync check
- `DESIGN.md`, `PARTS.md` - the visual design rules and the `part.md` format

Requirements: Python 3.11+ (`requirements.txt`), Python 3.12 for TTS (`requirements-tts.txt`), and `ffmpeg`.
On first use the skill copies the pipeline into a `video_gen/` folder in your project and sets up both venvs.

Examples in [`skills/make-video/examples/`](plugins/video-gen/skills/make-video/examples): one part with
hand-written scenes and one with declarative stage blocks.
