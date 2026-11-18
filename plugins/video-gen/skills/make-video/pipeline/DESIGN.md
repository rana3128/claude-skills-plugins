# Kinetic design rules for portrait Shorts

**Status: approved by the user on 2026-10-26** (after the p09 `useEffect` experiment). Every new portrait
Short should follow these rules. The implementation is [kinetic.py](kinetic.py) (skin, chrome, captions and reusable blocks),
[kinetic_build.py](kinetic_build.py) (the runner) and one `scenes.py` per part. The reference parts are
`Quick_react/p01`–`p10`; p09 (`useEffect`) was the approved prototype.

It replaces the older look of `skin.py` + `templates.py` (navy dot grid, text cards). The user's verdict on that
look was "just boxes and text, very bad looking".

---

## 1. The core idea

**Animate the concept, not a list of text.** Each scene shows the mechanism moving: a playhead
travelling through steps, code typing itself in, render ticks firing, a tooltip flickering. Narration
explains it, and **captions carry the words**, so the stage needs very little text.

If a scene would only be a box holding a sentence, redesign it. Ask: *what would this look like if it
were happening?*

## 2. Hard rules (the user rejected each of these)

1. **Never put boxes side by side in a row.** On a 1080 px wide screen they become narrow, tall boxes
   with cramped text. **Stack boxes as full-width rows in one column**, x 70 → 1010.
   - Allowed in a row: small **pills** (labels such as `fetch()` and `subscribe()`), the dots of a timeline, step
     nodes on a horizontal track, and values on a ruler.
   - Not allowed: two or three cards or panels next to each other, or a tall phone beside a timeline.
2. **No accent bar or stripe on the left edge of a box or line.** To highlight, use a soft, full-width,
   rounded band (17% alpha in the role colour), a glow, or a colour change.
3. **Text must be large and readable.**

   | Text | Minimum size |
   |---|---|
   | Scene heading | 62 px, weight 750 |
   | Primary labels | 34 px |
   | Secondary labels / descriptions | 28 px |
   | Small tags in pills | 25 px |

   Nothing on the stage goes below 24 px, and secondary text uses `DIM = (152, 162, 192)`, never darker.
4. **No walls of text on the stage.** Use at most one short line per element. Explanations go in narration and captions.
5. **The explanation must flow with the animation.** Every element appears on the spoken word that names
   it (from Kokoro's word timings). Nothing appears before it's mentioned, and nothing sits still for long.

## 3. Screen layout (1080 x 1920)

| Zone | y range | Contents |
|---|---|---|
| Story bar | 30–37 | One segment per scene, Instagram-style: done = white 92%, current = fills with progress, upcoming = white 16% |
| Top row | 70–120 | Spinning React-atom mark (r 20) at x 72, letter-spaced kicker `QUICK REACT` (mono 24, cyan), scene counter `02 / 05` right-aligned (mono 24, DIM) |
| Heading | 168–270 | Centred, one line. Hook/code words (`useX...`) in **cyan mono 56**, other words white sans 62/750. A cyan→violet gradient underline grows from the centre (240 px) |
| **Stage** | 330–1400 | The animated visual, full width x 70–1010 |
| Captions | ~1430–1660 | Empty: burned-in captions are off (§7) |
| Footer | 1836 | "Quick React Series", sans 24, DIM, centred |

The title scene (scene 1) has no heading. Its stage is a hero:
- a large glowing React atom, with orbiting electrons and a back-ease scale-in;
- the topic word typed letter by letter, mono 132, with a cyan→violet gradient and a blinking cursor;
- a small spaced kicker (`QUICK REACT · HOOKS`);
- 2–3 topic pills that pop in on their spoken words.

## 4. Look

- **Canvas:** `BG (6, 8, 15)`, near-black. Three huge soft radial glows drift slowly with `sin`/`cos` of time:
  - cyan at (250, 520), r 640, alpha .15;
  - violet at (900, 1250), r 700, alpha .15;
  - pink at (540, 1800), r 520, alpha .07.

  A radial vignette darkens the corners to 55% black. **No dot grid.**
- **Palette** (each colour has one role in a scene; keep it consistent):

  | Name | RGB | Typical role |
  |---|---|---|
  | CYAN | 97, 218, 251 | React, primary, the "now" highlight, function names in code |
  | VIOLET | 167, 139, 250 | DOM / second step, gradient partner |
  | PINK | 244, 114, 182 | effects, keywords in code |
  | GREEN | 52, 211, 153 | good / painted / success / checks / strings |
  | AMBER | 251, 191, 36 | change, warning, cleanup, numbers |
  | RED | 248, 113, 113 | bad / anti-pattern / flicker |
  | WHITE | 241, 245, 255 | main text |
  | DIM | 152, 162, 192 | secondary text |
  | PANEL / EDGE | 12, 16, 27 / 42, 50, 74 | panel fill / hairline border |

- **Type:**
  - sans is SF Pro (`skin.font(size, weight)`); headings and captions use weight 750.
  - code is SF Mono (`kinetic.mono(size)`, from `/System/Library/Fonts/SFNSMono.ttf`).
- **Panels:** radius 22–30, fill PANEL at 92%, a 1.5 px EDGE hairline (or the role colour when it's the
  focus), and a soft drop shadow (offset 18, blur 26). When a panel becomes the topic, give it a glow pulse in its role colour.
- **Pills:** fully rounded, 14% tint fill with a 1.8 px border in the role colour, white mono text inside.
  They are labels, never paragraphs.

## 5. Visual vocabulary (pick the metaphor that matches the concept)

| Concept shape | Visual | Reference |
|---|---|---|
| A sequence of phases | **Horizontal step track** at the top of the stage (nodes on a line, a glowing playhead that slides to each step on its word, gradient fill behind it), with **the current step's meaning in large mono text under it** | p09 scene 2 |
| What the user sees | **Wide browser window** (traffic-light dots, URL bar `localhost:3000/...`) showing a real mini UI: a profile card with avatar, name and button. The UI changes state with the narration: dashed wireframe → grey DOM nodes → painted colours with a white flash | p09 scene 2 |
| Code behaviour | **Code editor card** (traffic lights, filename tab, line numbers, syntax colours: keywords pink, function calls cyan, numbers amber, strings green, punctuation grey-blue). The code changes live: lines **type themselves in**, the dependency array swaps, the line being discussed gets a soft band | p09 scenes 3–4 |
| Lint / error / warning | Amber **squiggle** under the token, plus an ESLint-style **toast** panel (amber border, warning triangle, mono message) | p09 scene 3 |
| "When does X happen?" over time | **Firing lanes**: a ruler of renders (`#1..#6`) with changing values (changed values in amber), then one full-width lane per option. Each lane fires glowing dots with ripples, sweeping left to right | p09 scene 3 |
| Lifecycle / duration | **Lifecycle bar**: a pill at the start, a growing bar with tick marks, a ticking clock riding its tip, stopping (grey) at an event pill such as "cleanup: clear" | p09 scene 4 |
| A replaces B / handover | Two bars on one lane (timer A → cleanup pill → timer B) plus a green rule pill ("never two timers at once") | p09 scene 4 |
| A list of related items | **Stacked full-width rows**: name in role-coloured mono 34 on the left, the meaning in sans 32 on the right, a green check when the narration closes the idea | p09 scene 4 |
| A vs B behaviour | **Two full-width lanes stacked**. Each has a name, a tag pill, a mini step track with a playhead, and a mini screen acting out the difference (tooltip lands wrong then jumps = "flicker!" vs lands right = "no flicker"). **Replay** the animation when the narration comes back to the point | p09 scene 5 |
| Talking to the outside world | **Ripples** from the source, dashed lines to destination pills, and dots travelling along the lines | p09 scene 2 |

New metaphors are welcome, but they must follow §2. Ideas for later topics: a component tree for
reconciliation and keys, a store with flowing actions for Redux, a cache shelf for TanStack Query, a
network waterfall for races and Suspense, a bundle that splits into chunks.

## 6. Motion

- **Cue = spoken word.** `Scene.at(name, key, beat=k)` finds the first word starting with `key`, restricted to beat k
  when the word recurs. If the build log shows `MISSING`, fix the key.
- Entrance: ease-out cubic over 0.35–0.45 s (`ramp`). Pills and badges pop with back-ease (`ramp(..., back)`), with a
  20–30 px upward slide.
- Emphasis: a **glow pulse** that fades over 0.8–1.2 s (`pulse`) when an element is named, ripple rings on events,
  and a white flash on "paint"-type moments.
- Continuous life: background glows drift, the atom spins, the playhead glows, clocks tick, and dots travel along links.
  Something should always move a little.
- Playheads and sweeps: 0.3–0.55 s between steps; lane sweeps fire one dot every 0.32 s.
- Replays: when the narration repeats a contrast ("without a visible flicker"), re-run that animation from its start.
- Old elements stay visible but quieter: an inactive lane goes to 55%, an inactive step to 35–40%. Never remove
  context the viewer still needs.

## 7. Captions (karaoke): OFF by default

**Since 2026-10-26 the user wants no subtitles burned into the video** (`kinetic.SHOW_CAPTIONS = False`). The voice
carries the words and the `.srt` file is still written for platforms that show closed captions. The caption zone
(y 1430–1660) stays free, so nothing else moves. The notes below describe the code, in case captions are turned back on.


- They're built from Kokoro's word timings per beat (`kinetic.chunks`). Each chunk is at most about 30 characters, or ends at punctuation once it has 3+ words.
- Spelled-out acronyms are joined back for display (J S X → **JSX**, D O M → **DOM**, A P Is → **APIs**), and so are hook
  names (use effect → **useEffect**, use layout effect → **useLayoutEffect**, use state → **useState**). Add more entries to
  `CAMEL` when a new series needs them.
- Word states: already spoken = white; **current = cyan on a rounded cyan 22% highlight**; upcoming = white 34%.
  Text has a soft black shadow. Each chunk slides up 14 px and fades in over 0.18 s.

## 8. How to build one (current workflow)

Each part folder holds `part.md` (narration, PARTS.md rules) and `scenes.py` (the visuals).

1. Write `<series>/pNN_<slug>/scenes.py`:
   - `KICKER = "QUICK REACT  ·  HOOKS"`
   - `Title = K.hero(word, KICKER, [(chip, colour, spoken key), ...])`
   - one `Scene` subclass per remaining `##` scene, in order: `setup()` holds the cues (`self.at("word", beat=k)`),
     and `draw(pen, t)` draws the stage;
   - `SCENES = [Title, ...]`.

   Chrome, the story bar and captions are automatic. Copy the style of the existing `Quick_react/p0*/scenes.py`.
2. **Reusable blocks** in `kinetic.py`:

   | Block | What it draws |
   |---|---|
   | `hero` | title scene |
   | `rows` | stacked full-width rows with check or cross |
   | `step_track` | phase track with playhead and large description |
   | `code_card` + `typed_lines` | live code editor that types itself |
   | `lane` | full-width A/B panel with tag |
   | `node` + `link` | pill nodes and curved connectors with comets |
   | `browser` | window chrome |
   | `pop` | pill that pops on a cue |
   | `big_text`, `squiggle`, `check`, `cross`, `strike`, `spinner`, `glow_dot`, `ring`, `panel`, `pill` | smaller marks |

   Add a new block to `kinetic.py` when two parts need the same visual.
3. Check: `.venv/bin/python kinetic_build.py <part dir> --stills <scratchpad>/sheet.png` renders the state at the end of
   every beat and prints the cue table plus a count of missing cues. Look at it once against §2 and fix any overlaps.
4. Render: `ls -d <series>/p0[1-9]_* | xargs -P 3 -I{} .venv/bin/python kinetic_build.py {} --out <series>/output`.
   That gives one result line per part; `build.log` has the cue times.
5. The narration rules from PARTS.md still apply (spelled-out acronyms, 3–45-word beats, concepts never cut). Write
   the narration so it walks the visual in drawing order.

**Possible next step:** let simple scenes be declared in `part.md` (for example `Visual: rows | ...`) and
generated without a `scenes.py`. Until then, each part needs its own `scenes.py`, about 60–120 lines using the blocks.

**Declarative stage (added 2026-11-02, Quick JS & Node).** Instead of a custom `Scene`, a part can set
`SCENES = K.part(word, tag, chips, [[blocks for scene 2], [blocks for scene 3], ...])`. The blocks in `kinetic.py` are `Track`, `Pipe`
(rows joined by comets), `Rows`, `Code`, `Lanes`, `Bars` (racing timelines), `Ring` (a loop), `Fan` (one to many), `Chips`, `Big`
(a value that changes) and `Note`. A cue is a word prefix searched after the block's previous cue, `(word, beat)`, or a beat number.
A stack that is too tall logs a `MISSING overflow` cue. Examples: `Quick_JavaScript/p03`–`p44`. Each series sets its mark in `kinetic.MARKS`.

## 9. Checklist before rendering

- [ ] No boxes side by side; every box is a full-width row
- [ ] No edge accent bars; highlights are bands, glows or colour
- [ ] Every text item at or above its §2 size; secondary text DIM or brighter
- [ ] Stage stays in y 330–1400; nothing collides with captions (y 1430+)
- [ ] Every element has a spoken cue; no `MISSING` in the log
- [ ] Each scene shows the mechanism moving, not a sentence in a box
- [ ] Colours keep their roles (§4)
- [ ] Stills sheet looked at once; result line shows h264+aac and max-gap under 1 s
