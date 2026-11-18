# claude-skills-plugins

A personal [Claude Code](https://claude.com/claude-code) plugin marketplace. Install it once on a laptop and its
skills work in any project, with any Claude account. Plugins are set up per machine and are not tied to a login.

## Plugins

| Plugin | Skill | What it does |
|---|---|---|
| [video-gen](plugins/video-gen) | `make-video` | Turns a study guide or topic into animated, voiced portrait (1080x1920) YouTube Shorts, with kinetic word-synced scenes and the Kokoro voice. |

---

## 1. Prerequisites (new laptop)

| Need | Why | macOS install |
|---|---|---|
| Claude Code | runs the skill | `npm install -g @anthropic-ai/claude-code` |
| git access to this repo | to add the marketplace | SSH key or `gh auth login` (only needed if the repo is private) |
| `ffmpeg` | audio mux and silence check | `brew install ffmpeg` |
| Python 3.11+ | drawing and rendering (Skia) | `brew install python@3.13` |
| Python 3.12 | Kokoro voice | `brew install python@3.12` |

On Linux, install the same tools with your package manager. Kokoro downloads its voice model on first use,
so the first run needs internet.

## 2. Install

Pick **one** of the options below.

### Option A: from GitHub (recommended, no clone needed)

Inside any Claude Code session:

```
/plugin marketplace add rana3128/claude-skills-plugins
/plugin install video-gen@claude-skills-plugins
```

Restart Claude Code, or run `/reload-plugins`.

### Option B: from a local clone (if you're editing the skill)

```bash
git clone git@github.com:rana3128/claude-skills-plugins.git ~/claude-skills-plugins
```

Then, in Claude Code:

```
/plugin marketplace add ~/claude-skills-plugins
/plugin install video-gen@claude-skills-plugins
```

### Option C: copy the skill only (no plugin system)

```bash
# available in every project on this laptop
cp -r ~/claude-skills-plugins/plugins/video-gen/skills/make-video ~/.claude/skills/
# or only in one project
cp -r ~/claude-skills-plugins/plugins/video-gen/skills/make-video <project>/.claude/skills/
```

A copied skill does not update itself. Copy it again after you pull changes.

### Check it's installed

Start a new session and type `/`. You should see `make-video`, shown as `video-gen:make-video` when it is
installed as a plugin. You can also run `/plugin` to see installed plugins.

## 3. Use it

Open Claude Code in the project where you want the videos, then just ask:

```
Split notes/Python_Guide.docx into parts for short videos
```
```
Generate the first 2 videos
```
```
Looks good, generate all of them
```
```
Make a short about database indexing
```

Or call it directly: `/video-gen:make-video <what you want>`.

What happens:

1. **First run in a project:** Claude creates `video_gen/`, copies the pipeline into it, and builds two
   virtualenvs: `.venv` for drawing and `.venv-tts` for the voice.
2. **Split:** Claude analyses the guide and proposes a list of parts. **It waits for your approval.**
3. **Write:** it writes one `part.md` (narration) and one `scenes.py` (animation) per part, and lints them.
4. **Preview:** it renders the first parts so you can check the look, then renders the rest in the background.
5. **Output:** `video_gen/<Series>/output/<part>_voiced.mp4`, plus a report table with each video's
   length and longest pause.

You can also run the pipeline by hand from `video_gen/`:

```bash
.venv/bin/python build_part.py <Series>/p01_topic --lint                   # check narration
.venv/bin/python kinetic_build.py <Series>/p01_topic --stills /tmp/p01.png # preview frames + cue report
.venv/bin/python kinetic_build.py <Series>/p01_topic --out <Series>/output # final MP4
.venv/bin/python cue_scan.py <Series>/p*_*                                 # sync check
```

## 4. Update

| Installed with | To get new changes |
|---|---|
| Option A / B | `/plugin marketplace update claude-skills-plugins` (for B, run `git pull` first) |
| Option C | `git pull`, then copy the folder again |

A project that already has `video_gen/` keeps its own copy of the pipeline. To use pipeline fixes there,
copy `plugins/video-gen/skills/make-video/pipeline/*` over it.

## 5. Uninstall

```
/plugin uninstall video-gen@claude-skills-plugins
/plugin marketplace remove claude-skills-plugins
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `marketplace add` fails with an auth or permission error | The repo is private. Set up an SSH key or run `gh auth login` with an account that can see it. |
| Skill doesn't show up | Restart Claude Code and check `/plugin`. |
| `ffmpeg: command not found` | `brew install ffmpeg` |
| Kokoro install fails | Use Python **3.12** for `.venv-tts`. Newer versions may lack wheels. |
| `MISSING` cues in the stills report | Cue words must be listed in the order they are spoken. Ask Claude to fix the cues. |

---

## Repo layout

```
.claude-plugin/marketplace.json        # marketplace manifest (lists the plugins)
plugins/video-gen/
  .claude-plugin/plugin.json           # plugin manifest
  skills/make-video/
    SKILL.md                           # the instructions Claude follows
    pipeline/                          # copied into <project>/video_gen/ on first use
      kinetic.py, kinetic_build.py     # kinetic scene engine (Skia) + per-part builder
      build_part.py, engine_short.py,  # part.md parsing, lint, layout, render
      skin.py, templates.py
      voice.py, tts_worker.py          # Kokoro TTS with word timings
      cue_scan.py                      # text-only sync check
      DESIGN.md, PARTS.md              # visual rules + part.md format
      requirements*.txt
    examples/                          # one hand-written part, one declarative-block part
```

## Adding a new skill or plugin

1. Create `plugins/<name>/.claude-plugin/plugin.json` and `plugins/<name>/skills/<skill>/SKILL.md`.
2. Add an entry to `plugins` in `.claude-plugin/marketplace.json`.
3. Run `claude plugin validate .`, then commit and push.
