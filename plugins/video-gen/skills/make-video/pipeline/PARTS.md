# Part-based voiced shorts: `part.md` → finished MP4

> **Visual design moved to [DESIGN.md](DESIGN.md)** (approved 2026-10-26). The part.md format, narration rules,
> splitting workflow and voice pipeline below still apply. The `Visual:` layouts and the look of `templates.py`/`skin.py`
> are the old style, superseded by DESIGN.md for new Shorts.

The default way to make portrait YouTube Shorts (1080x1920, 90–150 s). You write **one file per
short**, `part.md`, containing the facts, the narration and one layout line per scene. You don't
write a `render.py` or any drawing code. `build_part.py` voices it, animates it in sync with the
voice, and writes `<slug>_voiced.mp4` + `.srt`.

First used for `Quick_system_design_short/` (37 parts); see the `part.md` files there for examples.
`p29_psp_overview` is the most complex.

## How it works

| File | Role |
|---|---|
| `build_part.py` | Parses part.md, lints, voices, renders, muxes, checks. Patches `engine_short.py` in memory only, so never edit the engine |
| `templates.py` | The layouts (graph, flow, cards, stack, grid, compare, calc, title), word-synced timing, label placement, layout lint |
| `skin.py` | The look: Skia drawing (anti-aliased, shadows, glow), "systems blueprint" style |
| `tts_worker.py` / `voice.py` | Kokoro `af_heart`, speed 1.0; one WAV + `*.words.json` (word timings) per beat, cached by text |
| `cue_scan.py` | Text-only sync check over `build.log` |

**Sync model.** Each beat is one TTS clip, followed by a 0.25 s pause. Kokoro returns the time of every
word, and each diagram element appears **on the word that names it**. The element being explained
glows, older ones dim to 75%, connectors draw along curves with a moving comet, and every scene has a
thin progress line.

**Look.** Navy canvas `#0F1422` with a dot grid. Role-tinted rounded cards with soft shadows. SF Pro
type. Colours carry meaning: `[blue]` indigo for services, `[green]` mint for success, `[red]` coral
for failure, `[orange]`, `[yellow]`, `[purple]`, `[teal]`, `[dim]`.

## part.md format

```
# Payment service provider: framing, numbers, state machine      <- title card text
Source: Quick guide A1 (Frame it, Architecture, ...)
Tag: PAYMENTS                                                    <- topic shown in the footer
Key facts:
- every fact/number from the source used on screen (not narrated, for reference)

## Design a payment service provider like Stripe                 <- scene 1: the question
Visual: title | Idempotency, Ledger, PCI                         <- chips
- How would you design a payment service provider, like Stripe or Razorpay?

## Architecture                                                  <- scene heading (max 2 lines)
Visual: graph | Merchant [blue] | API gateway (auth, rate limits) [teal] | ~ Merchant -> API gateway: request {request}
- A merchant's request enters through the A P I gateway, which ...
- ...
```

Rules:
- **Scene 1** is `Visual: title | chip, chip, chip` with one beat: the topic question. Then 4–6 scenes.
- **Total length** is 240–330 words, which at about 3 words per second is 90–150 s.
- **Beats** are 3–45 words each, and a scene's narration stays under 800 characters.
- **No** welcome, recap or question numbers.
- **Spell out acronyms for the voice**, e.g. "A P I", "P 99", "S Q L", "four twenty nine". The lint
  flags capitalised acronyms. Mispronounced words go in `voice.PRON`.
- **Write the narration to walk the diagram in the order it draws**, naming each element as it
  appears. That's what makes the explanation flow with the animation.

## Visual line grammar

`Visual: <kind> | item | item | ...`

| kind | item syntax | use for |
|---|---|---|
| `graph` | node row: `Label (sub) [color] & Label2 & ...` (nodes in one row split by `&`); edge: `~ From -> To: label [color]` | architectures, flows with branches, sagas, state machines, fan-out |
| `flow` | `Label (sub) [color]` | a straight vertical chain (pipeline, steps) |
| `cards` / `stack` | `Heading [color]: bullet; bullet; bullet` or plain `text` | grouped points, ladders of fixes |
| `grid` | same as cards, 2 columns | 4–6 short parallel items |
| `compare` | same as cards, one column per item | A vs B (2–3 items) |
| `calc` | `line` / `= result` | estimations; `=` lines are highlighted results |

Modifiers, allowed in any item:
- `[color]`: the role colour (see the list above).
- `{words}`: the spoken word that triggers the element. Without it, the item's first keyword is used, and the
  matching tolerates word forms ("saving" matches save) and spelled letters ("C D N" matches CDN).
- `@k`: not before beat k (0-based). Use it when the keyword is also said earlier.

Graph specifics:
- Edges carry the story. A source node appears with its first edge, or earlier if it is named earlier in the same
  beat. A target node appears as the arrow arrives. Nodes without edges are matched by their own keyword.
- Refer to nodes by their **label only**, without the `(sub)` part. Matching is exact first, then by prefix.
- **Never put `:` or `->` inside a node name.** The edge parser splits on them, and the lint now errors on it.
- Repeated edges between the same two nodes are drawn side by side (forward + compensation).
- Up to 6 rows. A row with 3 nodes needs short labels. A row whose labels don't fit shrinks its own font only.

Ordering gotchas, the main cause of late reveals:
- Items reveal **in the order you list them**, each searching for its word after the previous one's time.
  **List items, bullets and edges in the order the narration says them.**
- Number words and fillers (one, two, hundred, first, only, can, ...) are never cue words, because they recur.
- A `{cue}` at the end of a card belongs to its last bullet if the word is in that bullet; otherwise it names the card.

## Commands (run from `video_gen/`)

```bash
.venv/bin/python build_part.py <dir> --lint                 # narration + layout lint, prints problems only
.venv/bin/python build_part.py <dir> --sheet /tmp/s.png     # one image: every scene's final state
.venv/bin/python build_part.py <dir> --out <series>/output  # voice + render + mux + copy; prints one line:
#   p29_psp_overview: ok 140.3s h264+aac max-gap 0.68s lint:0
ls -d <series>/p0[1-9]_* | xargs -P 3 -I{} .venv/bin/python build_part.py {} --out <series>/output   # batch
.venv/bin/python cue_scan.py <series>/p*_*                  # sync check from build.log (text only)
```

`<dir>/build.log` holds the full engine log and, for every scene, when each element appears, e.g.
`14.87s  Order service -> Outbox table: same transaction`. Read that to check sync, not frames.

## Splitting a guide into a new series (do this before writing any part)

1. **Analyse.** Extract the text (`textutil -convert txt -stdout X.docx`) and make a table of every section:
   what it covers, and whether it's used. Skip sections that repeat another series or a cheat sheet.
2. **Propose the split and wait for the user's approval.** Group related questions so each part fully explains
   its concepts in 90–150 s. Merge small questions, and give big ones a part of their own.
3. **Write all parts** after approval, then the series README (analysis + index), then lint all of them. Render only what was asked for.
4. **Never cut content to hit a length.** Clarity comes first: each concept gets its what, its why and a small
   example. If a part is short, add an example or the interview angle at the end of a scene (this keeps the reveal order).

Gotchas found on Quick React:
- A graph node label that ends in `(...)`, like `dispatch(action)`, parses as label + sub. Edges must use `dispatch`.
- `compare` takes 2–3 items, so use `grid` for 4. Long code tokens (`React.ChangeEvent<HTMLInputElement>`) need `cards`, not `grid`.
- Two nodes in the same row with a labelled edge between them overlap, so drop that edge's label.
- Never use `{}`, `|` or `[word]` inside item text, because they are cue, separator and colour syntax. Use `:` only after a card heading.

## Workflow for a new short (token-lean)

1. Write `part.md`: facts, narration and Visual lines in one pass.
2. Run `--lint` and fix everything it prints.
3. Use `--sheet` only for a new kind of diagram, or when the lint reports overlaps.
4. Build with `--out`. Then run `cue_scan.py`: a "late" flag on anything other than the scene's last spoken
   word means an ordering or cue problem. Fix the order, or add `{word}` / `@k`, and rebuild.
5. Report one line per short: link, length, and longest silence (max-gap).

## Setup (once per machine)

- Kokoro: see README.md ("Voiced output"), which uses `.venv-tts` (Python 3.12).
- Skia, in the main `.venv`: `.venv/bin/pip install skia-python` (version 144.1 was used).
- SF Pro comes with macOS.

## Not yet available

Layouts for a `ring` (consistent hashing) and a `timeline` (TTL jitter, canary %, backoff) don't exist yet.
Approximate these with `compare` or `calc` for now. The 16:9 long-form series (`engine.py`, JS chapters) still use `render.py` + `legacy/voiced.py`;
porting the layouts to 16:9 is a possible next step.
