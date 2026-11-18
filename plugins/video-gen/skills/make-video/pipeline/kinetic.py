"""Experimental "kinetic" skin for portrait shorts (lab only; the main pipeline still uses skin.py).

Aurora canvas, story-style progress segments, React atom mark, karaoke captions from the
voice's word timings, and code-editor cards with syntax colours. Drawn with Skia.
"""

import functools
import math
import re

import skia

import skin as S
from skin import W, H, paint, font, cint

BG = (6, 8, 15)
CYAN = (97, 218, 251)
VIOLET = (167, 139, 250)
PINK = (244, 114, 182)
AMBER = (251, 191, 36)
GREEN = (52, 211, 153)
RED = (248, 113, 113)
WHITE = (241, 245, 255)
DIM = (152, 162, 192)
PANEL = (12, 16, 27)
EDGE = (42, 50, 74)

BLOBS = [(250, 520, 640, CYAN, 0.15, 0.0), (900, 1250, 700, VIOLET, 0.15, 2.0),
         (540, 1800, 520, PINK, 0.07, 4.0)]


# --- type ------------------------------------------------------------------
class Mono:
    def __init__(self, size):
        tf = skia.Typeface.MakeFromFile("/System/Library/Fonts/SFNSMono.ttf") or skia.Typeface("Menlo")
        self.sk = skia.Font(tf, size)
        self.sk.setEdging(skia.Font.Edging.kAntiAlias)
        self.sk.setSubpixel(True)
        self.size = size
        self.ascent = -self.sk.getMetrics().fAscent


@functools.lru_cache(None)
def mono(size):
    return Mono(int(size))


# --- time ------------------------------------------------------------------
def clamp(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def ease(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def back(x):
    x = clamp(x)
    c = 1.70158
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def ramp(t, t0, d=0.45, fn=ease):
    return 0.0 if t0 is None else fn((t - t0) / d)


def pulse(t, t0, d=0.9):
    """1 -> 0 glow right after t0."""
    if t0 is None or t < t0:
        return 0.0
    return max(0.0, 1 - (t - t0) / d)


# --- canvas + chrome --------------------------------------------------------
def new_canvas(t=0.0):
    s = skia.Surface.MakeRaster(skia.ImageInfo.Make(W, H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType))
    c = s.getCanvas()
    c.clear(S.c4(BG))
    for cx, cy, r, col, a, ph in BLOBS:
        x, y = cx + 70 * math.sin(t * 0.23 + ph), cy + 50 * math.cos(t * 0.19 + ph)
        c.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Shader=skia.GradientShader.MakeRadial(
            (x, y), r, [cint(col, a), cint(col, 0.0)])))
    c.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Shader=skia.GradientShader.MakeRadial(
        (W / 2, H / 2), 1250, [cint(BG, 0.0), cint((0, 0, 0), 0.55)])))
    return s


def spaced(pen, x, y, s, f, rgb, alpha=1.0, gap=4):
    for ch in s:
        pen.text(x, y, ch, f, rgb, alpha)
        x += pen.textlength(ch, f) + gap
    return x


def spaced_len(pen, s, f, gap=4):
    return sum(pen.textlength(ch, f) + gap for ch in s) - gap


def atom(c, cx, cy, r, t, alpha=1.0, glow=0.0, col=CYAN):
    if glow:
        c.drawCircle(cx, cy, r * 1.05, paint(col, 0.16 * glow * alpha, blur=r * 0.45))
    ring = paint(col, alpha, stroke=max(2.0, r * 0.06))
    for k in range(3):
        c.save()
        c.translate(cx, cy)
        c.rotate(k * 60 + t * 14)
        c.drawOval(skia.Rect(-r, -r * 0.37, r, r * 0.37), ring)
        a = t * 2.4 + k * 2.1
        c.drawCircle(r * math.cos(a), r * 0.37 * math.sin(a), r * 0.06 + 2, paint(WHITE, alpha))
        c.restore()
    c.drawCircle(cx, cy, r * 0.15, paint(col, alpha))


def js_mark(c, cx, cy, r, t, alpha=1.0, glow=0.0, col=AMBER):
    """Series mark for JS & Node: a yellow JS tile with a dot orbiting it."""
    if glow:
        c.drawCircle(cx, cy, r * 1.05, paint(col, 0.16 * glow * alpha, blur=r * 0.45))
    s = r * 0.78
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(cx - s, cy - s, cx + s, cy + s), s * 0.18, s * 0.18), paint(col, alpha))
    f = font(max(14, int(r * 0.82)), 800)
    w = f.sk.measureText("JS")
    c.drawString("JS", cx + s * 0.9 - w, cy + s * 0.86, f.sk, paint(BG, alpha))
    c.drawCircle(cx, cy, r * 1.25, paint(col, 0.35 * alpha, stroke=max(1.5, r * 0.025)))
    a = t * 1.6
    c.drawCircle(cx + r * 1.25 * math.cos(a), cy + r * 1.25 * math.sin(a), r * 0.05 + 2, paint(WHITE, alpha))


MARKS = {"Quick_JavaScript": js_mark}
MARK = atom                 # set per series by kinetic_build.py
FOOTER = "Quick React Series"
HEAD = font(62, 750)
KICK = mono(24)


def heading(pen, text, y, alpha=1.0):
    """Heading where hook-like words (useX) are set in cyan mono."""
    toks = text.split()
    code = mono(56)
    hook = [bool(re.match(r"use[A-Z]", w)) for w in toks]
    widths = [pen.textlength(w + " ", code if h else HEAD) for w, h in zip(toks, hook)]
    x = (W - sum(widths)) / 2
    for w, wd, h in zip(toks, widths, hook):
        if h:
            pen.text(x, y + 6, w, code, CYAN, alpha)
        else:
            pen.text(x, y, w, HEAD, WHITE, alpha)
        x += wd


def chrome(pen, idx, n, prog, head, kicker, t):
    x0, x1, gap = 40, W - 40, 10
    seg = (x1 - x0 - gap * (n - 1)) / n
    for i in range(n):
        x = x0 + i * (seg + gap)
        r = skia.RRect.MakeRectXY(skia.Rect(x, 30, x + seg, 37), 4, 4)
        pen.c.drawRRect(r, paint(WHITE, 0.16))
        f = 1.0 if i < idx else (prog or 0.0) if i == idx else 0.0
        if f > 0:
            pen.c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(x, 30, x + seg * f, 37), 4, 4), paint(WHITE, 0.92))
    MARK(pen.c, 72, 96, 20, t, 0.95)
    spaced(pen, 108, 84, kicker, KICK, CYAN, 0.9)
    num = f"{idx + 1:02d} / {n:02d}"
    pen.text_r(W - 44, 84, num, KICK, DIM)
    if head:
        a = ramp(t, 0.0, 0.5)
        heading(pen, head, 168 + 20 * (1 - a), a)
        wbar = 120 * ramp(t, 0.15, 0.6)
        pen.c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(W / 2 - wbar, 262, W / 2 + wbar, 268), 3, 3),
                        skia.Paint(AntiAlias=True, Shader=skia.GradientShader.MakeLinear(
                            [(W / 2 - 120, 0), (W / 2 + 120, 0)], [cint(CYAN), cint(VIOLET)])))
    pen.text_c(W / 2, H - 84, FOOTER, font(24, 500), DIM, 0.8)


# --- captions ---------------------------------------------------------------
CAMEL = {("use", "layout", "effect"): "useLayoutEffect", ("use", "effect"): "useEffect",
         ("use", "state"): "useState"}
CAP = font(56, 750)


def display_tokens(words, t0):
    """Kokoro word list -> caption tokens [text, start, end] with acronyms and hook names re-joined."""
    out = []
    for w, s, e in words:
        if not re.search(r"\w", w):
            if out:
                out[-1][0] += w
            continue
        prev = out[-1][0] if out else ""
        core = re.sub(r"\W", "", w)
        if len(core) == 1 and core.isupper() and re.fullmatch(r"[A-Z]+", prev) and core != "I":
            out[-1][0] += w
            out[-1][2] = t0 + e
            continue
        if re.fullmatch(r"[A-Z]s", w) and re.fullmatch(r"[A-Z]{2,}", prev):
            out[-1][0] += w
            continue
        out.append([w, t0 + s, t0 + e])
    i, res = 0, []
    while i < len(out):
        for key, name in CAMEL.items():
            seg = [re.sub(r"\W", "", x[0]).lower() for x in out[i:i + len(key)]]
            if tuple(seg) == key:
                tail = re.sub(r"\w", "", out[i + len(key) - 1][0])
                res.append([name + tail, out[i][1], out[i + len(key) - 1][2]])
                i += len(key)
                break
        else:
            res.append(out[i])
            i += 1
    return res


def chunks(starts, words, maxc=30):
    res = []
    for st, ws in zip(starts, words):
        cur, n = [], 0
        for tok in display_tokens(ws, st):
            cur.append(tok)
            n += len(tok[0]) + 1
            if n >= maxc or (re.search(r"[.,?;:]$", tok[0]) and len(cur) >= 3):
                res.append(cur)
                cur, n = [], 0
        if cur:
            res.append(cur)
    return res


def captions(pen, chs, t):
    act = None
    for ch in chs:
        if ch[0][1] <= t + 0.05:
            act = ch
    if act is None:
        return
    a = ramp(t, act[0][1] - 0.05, 0.18)
    lines, cur, w = [], [], 0
    sp = pen.textlength(" ", CAP)
    for tok in act:
        tw = pen.textlength(tok[0], CAP)
        if cur and w + sp + tw > 920:
            lines.append(cur)
            cur, w = [], 0
        cur.append((tok, tw))
        w += (sp if len(cur) > 1 else 0) + tw
    lines.append(cur)
    y = 1500 - 36 * (len(lines) - 1) + 14 * (1 - a)
    for ln in lines:
        total = sum(tw for _, tw in ln) + sp * (len(ln) - 1)
        x = (W - total) / 2
        for tok, tw in ln:
            txt, s, e = tok
            if s <= t < e + 0.12:
                r = skia.RRect.MakeRectXY(skia.Rect(x - 12, y - 4, x + tw + 12, y + 70), 16, 16)
                pen.c.drawRRect(r, paint(CYAN, 0.22 * a))
                col, al = CYAN, 1.0
            elif t >= s:
                col, al = WHITE, 1.0
            else:
                col, al = WHITE, 0.34
            pen.c.drawString(txt, x, y + CAP.ascent + 2, CAP.sk, paint((0, 0, 0), 0.55 * a * al, blur=6))
            pen.text(x, y, txt, CAP, col, a * al)
            x += tw + sp
        y += 76


# --- shapes -----------------------------------------------------------------
def panel(pen, box, alpha=1.0, edge=EDGE, radius=28, fill=PANEL, glow=0.0, glow_col=CYAN):
    if alpha <= 0.01:
        return
    r = skia.RRect.MakeRectXY(skia.Rect(*box), radius, radius)
    pen.c.drawRRect(r.makeOffset(0, 18), paint((0, 0, 0), 0.5 * alpha, blur=26))
    if glow > 0.02:
        pen.c.drawRRect(r, paint(glow_col, 0.4 * glow * alpha, stroke=12, blur=16))
    pen.c.drawRRect(r, paint(fill, 0.92 * alpha))
    pen.c.drawRRect(r, paint(edge, alpha, stroke=1.5))


def pill(pen, cx, cy, text, col, alpha=1.0, f=None, fill=0.14, hot=0.0, pad=24):
    f = f or mono(28)
    w = pen.textlength(text, f) + 2 * pad
    h = f.size * 1.75
    r = skia.RRect.MakeRectXY(skia.Rect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), h / 2, h / 2)
    if hot > 0.02:
        pen.c.drawRRect(r, paint(col, 0.45 * hot * alpha, stroke=10, blur=12))
    pen.c.drawRRect(r, paint(col, fill * alpha))
    pen.c.drawRRect(r, paint(col, 0.85 * alpha, stroke=1.8))
    pen.text_c(cx, cy - f.size * 0.62, text, f, WHITE, alpha)
    return w


def glow_dot(pen, x, y, r, col, alpha=1.0, glow=1.0):
    pen.c.drawCircle(x, y, r * 2.2, paint(col, 0.35 * glow * alpha, blur=r))
    pen.c.drawCircle(x, y, r, paint(col, alpha))


def ring(pen, x, y, r, col, alpha=1.0, width=3.0):
    pen.c.drawCircle(x, y, r, paint(col, alpha, stroke=width))


def check(pen, x, y, s, col, alpha=1.0):
    p = skia.Path()
    p.moveTo(x - s, y)
    p.lineTo(x - s * 0.3, y + s * 0.7)
    p.lineTo(x + s, y - s * 0.8)
    pen.c.drawPath(p, paint(col, alpha, stroke=s * 0.35))


def line(pen, a, b, col, alpha=1.0, width=3.0, dash=None):
    p = paint(col, alpha, stroke=width)
    if dash:
        p.setPathEffect(skia.DashPathEffect.Make(dash, 0))
    pen.c.drawLine(*a, *b, p)


# --- code card --------------------------------------------------------------
TOK = re.compile(r"(\s+|//.*|'[^']*'|\d+|=>|[A-Za-z_]\w*|.)")
KW = {"const", "return", "function", "let", "if", "import", "from", "export", "new", "var", "typeof"}


def colored(line):
    toks = TOK.findall(line)
    out = []
    for i, tk in enumerate(toks):
        nxt = next((x for x in toks[i + 1:] if not x.isspace()), "")
        if tk.startswith("//"):
            c = DIM
        elif tk in KW or tk == "=>":
            c = PINK
        elif tk.startswith("'"):
            c = GREEN
        elif tk.isdigit():
            c = AMBER
        elif re.fullmatch(r"[A-Za-z_]\w*", tk):
            c = CYAN if nxt == "(" else (226, 232, 246)
        else:
            c = (150, 162, 194)
        out.append((tk, c))
    return out


def code_card(pen, box, lines, t, name="Profile.jsx", hl=None, alpha=1.0, size=32, show=None, tint=None):
    """lines: list of str (or (str, alpha)). hl: {line: (rgb, strength)}. show: chars typed per line."""
    x0, y0, x1, y1 = box
    panel(pen, box, alpha)
    for k, col in enumerate([(255, 95, 87), (254, 188, 46), (40, 200, 64)]):
        pen.c.drawCircle(x0 + 34 + k * 26, y0 + 30, 7, paint(col, 0.9 * alpha))
    pen.text(x0 + 130, y0 + 17, name, mono(22), DIM, alpha)
    pen.c.drawLine(x0, y0 + 60, x1, y0 + 60, paint(EDGE, alpha, stroke=1))
    f = mono(size)
    lh = size * 1.6
    cw = pen.textlength("M", f)
    y = y0 + 82
    for i, ln in enumerate(lines):
        txt, la = (ln, 1.0) if isinstance(ln, str) else ln
        if hl and i in hl:
            col, st = hl[i]
            if st > 0.01:
                band = skia.RRect.MakeRectXY(skia.Rect(x0 + 14, y - 8, x1 - 14, y + lh - 10), 12, 12)
                pen.c.drawRRect(band, paint(col, 0.17 * st * alpha))
        pen.text(x0 + 26, y, f"{i + 1}", mono(size * 0.75), DIM, 0.6 * alpha * la)
        x = x0 + 78
        left = None if show is None else show.get(i)
        for tk, c in colored(txt):
            if left is not None:
                if left <= 0:
                    break
                tk = tk[:int(left)]
                left -= len(tk)
            pen.text(x, y, tk, f, c, alpha * la)
            x += cw * len(tk)
        y += lh
    return dict(x=x0 + 78, y=y0 + 82, cw=cw, lh=lh)


def squiggle(pen, x0, x1, y, col, alpha=1.0):
    p = skia.Path()
    p.moveTo(x0, y)
    k, x = 0, x0
    while x < x1:
        x += 7
        p.lineTo(x, y + (5 if k % 2 == 0 else 0))
        k += 1
    pen.c.drawPath(p, paint(col, alpha, stroke=2.4))


# ===========================================================================
# Reusable building blocks (DESIGN.md §5). Every block takes the scene clock t
# and the cue times it should react to; nothing here knows about a topic.
# ===========================================================================
BIGT = 10 ** 6
SHOW_CAPTIONS = False    # burned-in karaoke captions; off by the user's request (2026-10-26). The .srt is still written.


class Scene:
    """One `##` scene: cues from spoken words (self.at), stage drawing in draw(pen, t).
    Captions are added automatically from the same word timings."""

    def __init__(self, heading):
        self.heading, self.plan, self.cues = heading, True, {}
        self.starts, self.words, self.total, self.caps, self.flat = [0.0], [[]], 1.0, [], []

    def set_times(self, starts, words, total):
        self.starts, self.words, self.total = starts, words, total
        self.flat = [(re.sub(r"\W", "", w).lower(), st + s) for st, ws in zip(starts, words) for w, s, _ in ws]
        self.caps = chunks(starts, words)
        self.cues = {}
        self.setup()

    def at(self, key, beat=None, after=0.0, name=None):
        """Time of the first spoken word starting with `key` (in beat `beat`, after `after`)."""
        name = name or key
        lo = self.starts[beat] if beat is not None else 0.0
        hi = self.starts[beat + 1] if beat is not None and beat + 1 < len(self.starts) else BIGT
        t = next((ts for w, ts in self.flat if w.startswith(key) and lo - 0.01 <= ts < hi and ts >= after), None)
        if t is None:
            t = max(lo, after)
            name += " (MISSING)"
        self.cues[name] = t
        return t

    def beat(self, k):
        return self.starts[min(k, len(self.starts) - 1)]

    def setup(self):
        pass

    def timing_log(self):
        return [f"{v:6.2f}s  {k}" for k, v in sorted(self.cues.items(), key=lambda kv: kv[1])]

    def fit(self, pen):
        pass

    def draw(self, pen, t):
        pass

    def paint_at(self, pen, now=None, step=None):
        t = self.total if now is None else now
        self.draw(pen, t)
        if SHOW_CAPTIONS:
            captions(pen, self.caps, t)


def hero(word, kicker, chips):
    """Title scene: glowing atom, the topic typed in gradient mono, chips that pop on their words.
    chips: [(text, colour, spoken key)]."""

    class Title(Scene):
        def setup(self):
            self.ct = [self.at(k, beat=0) for _, _, k in chips]

        def draw(self, pen, t):
            a = ramp(t, 0.0, 0.8, back)
            MARK(pen.c, 540, 600, 200 * (0.6 + 0.4 * a), t, alpha=ramp(t, 0, 0.4), glow=1.0)
            f = mono(26)
            spaced(pen, 540 - spaced_len(pen, kicker, f) / 2, 880, kicker, f, DIM, ramp(t, 0.2, 0.5))
            size = 132
            while pen.textlength(word, mono(size)) > 900 and size > 60:
                size -= 4
            fw = mono(size)
            n = int(len(word) * clamp((t - 0.35) / 0.9))
            w = pen.textlength(word, fw)
            x = 540 - w / 2
            g = skia.Paint(AntiAlias=True, Shader=skia.GradientShader.MakeLinear(
                [(x, 0), (x + w, 0)], [cint(CYAN), cint(VIOLET)]))
            pen.c.drawString(word[:n], x, 1000 - size * 0.55 + fw.ascent, fw.sk, g)
            if int(t * 2) % 2 == 0 or n < len(word):
                cx = x + pen.textlength(word[:n], fw) + 6
                pen.c.drawRect(skia.Rect(cx, 1000 - size * 0.45, cx + 8, 1000 + size * 0.45), paint(CYAN, 0.9))
            widths = [pen.textlength(c, mono(28)) + 48 for c, _, _ in chips]
            gap = 26
            x = 540 - (sum(widths) + gap * (len(chips) - 1)) / 2
            for (txt, col, _), wd, t0 in zip(chips, widths, self.ct):
                p = ramp(t, t0, 0.5, back)
                if p > 0:
                    pill(pen, x + wd / 2, 1180 + 30 * (1 - min(1, p)), txt, col, alpha=min(1, p), hot=pulse(t, t0))
                x += wd + gap

    return Title


def pop(pen, t, t0, cx, cy, text, col, size=25, pad=18, until=None):
    """A pill that pops in on its cue (back-ease, glow pulse); optional fade-out at `until`."""
    p = ramp(t, t0, 0.45, back)
    if p <= 0:
        return 0.0
    a = min(1.0, p) * (1 - ramp(t, until, 0.3) if until is not None else 1.0)
    if a > 0.01:
        pill(pen, cx, cy + 22 * (1 - min(1, p)), text, col, alpha=a, f=mono(size), hot=pulse(t, t0), pad=pad)
    return a


def cross(pen, x, y, s, col, alpha=1.0):
    pen.c.drawLine(x - s, y - s, x + s, y + s, paint(col, alpha, stroke=s * 0.35))
    pen.c.drawLine(x - s, y + s, x + s, y - s, paint(col, alpha, stroke=s * 0.35))


def strike(pen, x0, x1, y, col, prog, alpha=1.0):
    if prog > 0:
        pen.c.drawLine(x0, y, x0 + (x1 - x0) * prog, y, paint(col, alpha, stroke=5))


def fit_font(pen, text, size, maxw, weight=None, minsize=24):
    while size > minsize:
        f = font(size, weight) if weight else mono(size)
        if pen.textlength(text, f) <= maxw:
            return f
        size -= 2
    return font(minsize, weight) if weight else mono(minsize)


def rows(pen, t, items, y0, h=118, gap=16, x0=70, x1=1010):
    """Stacked full-width rows (never side by side). item: dict(name, text, col, t0,
    check=time|None, bad=time|None, code=True, dim=time|None). Name on top, meaning below."""
    y = y0
    for it in items:
        t0 = it["t0"]
        p = ramp(t, t0, 0.45, back)
        if p > 0:
            a = min(1.0, p) * (1 - 0.45 * ramp(t, it.get("dim"), 0.4))
            yy = y + 20 * (1 - min(1, p))
            col = it["col"]
            panel(pen, (x0, yy, x1, yy + h), a, radius=22, edge=col, glow=pulse(t, t0, 1.0), glow_col=col)
            maxw = x1 - x0 - 130
            fn = fit_font(pen, it["name"], 34, maxw) if it.get("code", True) else fit_font(pen, it["name"], 36, maxw, 750)
            tight = h < 118           # short rows pull the two lines apart so they never collide
            top = 18 if not tight else 10 if it.get("text") else h / 2 - 22
            pen.text(x0 + 32, yy + top, it["name"], fn, col, a)
            if it.get("text"):
                ft = fit_font(pen, it["text"], 26 if h < 96 else 30, maxw, 500)
                pen.text(x0 + 32, yy + h - (52 if not tight else 36 if h < 96 else 42), it["text"], ft, WHITE, 0.88 * a)
            if it.get("check") is not None and t >= it["check"]:
                check(pen, x1 - 50, yy + h / 2, 16, GREEN, a * ramp(t, it["check"], 0.3))
            if it.get("bad") is not None and t >= it["bad"]:
                cross(pen, x1 - 50, yy + h / 2, 14, RED, a * ramp(t, it["bad"], 0.3))
        y += h + gap
    return y


def node(pen, cx, cy, label, col, alpha=1.0, hot=0.0, size=30, sub=None, fill=0.16):
    """A pill-shaped graph node; returns (x0, y0, x1, y1)."""
    if alpha <= 0.01:
        return (cx, cy, cx, cy)
    f = mono(size)
    w = pen.textlength(label, f) + 56
    hgt = size * 2.1
    pill(pen, cx, cy, label, col, alpha=alpha, f=f, fill=fill, hot=hot, pad=28)
    if sub:
        pen.text_c(cx, cy + hgt / 2 + 10, sub, mono(24), DIM, alpha)
    return (cx - w / 2, cy - hgt / 2, cx + w / 2, cy + hgt / 2)


def link(pen, p0, p1, col, prog, alpha=1.0, flow=None, t=0.0, label=None, dashed=False, vertical=True, width=3.0):
    """Curved connector p0 -> p1 drawn to `prog`; a comet travels along it when flow is a start time."""
    if prog <= 0.01 or alpha <= 0.01:
        return
    path = S.Pen.curve(p0, p1, vertical)
    packet = ((t - flow) * 0.7) % 1 if flow is not None and t >= flow and prog >= 1 else None
    if dashed:
        m = skia.PathMeasure(path, False)
        seg = skia.Path()
        m.getSegment(0, m.getLength() * prog, seg, True)
        p = paint(col, 0.7 * alpha, stroke=width)
        p.setPathEffect(skia.DashPathEffect.Make([12, 10], 0))
        pen.c.drawPath(seg, p)
    else:
        pen.connector(path, col, g=prog, alpha=alpha, packet=packet, width=width)
    if label and prog >= 1:
        mx, my = S.Pen.point_at(path, 0.5)
        pill(pen, mx, my, label, col, alpha=alpha, f=mono(23), fill=0.85, pad=14)


def lane(pen, box, name, tag, col, t, t0, code=True):
    """Full-width panel with a title (and a tag pill); returns its alpha (0 before t0)."""
    a = ramp(t, t0 - 0.2, 0.45)
    if a <= 0:
        return 0.0
    x0, y0, x1, y1 = box
    panel(pen, box, a, radius=28, edge=col, glow=0.5 * pulse(t, t0, 1.2), glow_col=col)
    pen.text(x0 + 32, y0 + 22, name, mono(36) if code else font(38, 750), col, a)
    if tag:
        f = mono(22)
        w = pen.textlength(tag, f) + 32
        pill(pen, x1 - 28 - w / 2, y0 + 48, tag, col, alpha=a, f=f, pad=16)
    return a


def browser(pen, box, alpha=1.0, url="localhost:3000"):
    """Browser window chrome; returns the content top y."""
    x0, y0, x1, y1 = box
    panel(pen, box, alpha, radius=24, fill=(10, 13, 22), edge=(70, 80, 110))
    for k, col in enumerate([(255, 95, 87), (254, 188, 46), (40, 200, 64)]):
        pen.c.drawCircle(x0 + 32 + k * 24, y0 + 28, 7, paint(col, 0.9 * alpha))
    pen.text(x0 + 120, y0 + 14, url, mono(23), DIM, alpha)
    pen.c.drawLine(x0, y0 + 56, x1, y0 + 56, paint(EDGE, alpha, stroke=1))
    return y0 + 56


def step_track(pen, t, steps, cues, y=420, x0=180, x1=900, desc=True, size=36):
    """Horizontal phase track: nodes light up and a playhead slides to each on its cue.
    steps: [(name, description, colour)]; the current description is shown large below."""
    n = len(steps)
    xs = [x0 + (x1 - x0) * k / (n - 1) for k in range(n)]
    hx = xs[0] - 60
    cur = -1
    for k, t0 in enumerate(cues):
        p = ramp(t, t0 - 0.1, 0.5)
        if p > 0:
            hx = hx + (xs[k] - hx) * p
        if t >= t0:
            cur = k
    line(pen, (xs[0] - 60, y), (xs[-1] + 60, y), WHITE, 0.12, 4)
    if hx > xs[0] - 60:
        pen.c.drawLine(xs[0] - 60, y, hx, y, skia.Paint(AntiAlias=True, StrokeWidth=4, Shader=skia.GradientShader.MakeLinear(
            [(xs[0], 0), (xs[-1], 0)], [cint(steps[0][2]), cint(steps[-1][2])])))
    for k, ((name, _, col), x) in enumerate(zip(steps, xs)):
        vis = ramp(t, 0.15 + 0.1 * k, 0.4)
        on = ramp(t, cues[k], 0.35)
        ring(pen, x, y, 24, col, vis * (0.35 + 0.65 * on), 3)
        pl = pulse(t, cues[k], 0.8)
        if on > 0:
            pen.c.drawCircle(x, y, 24 + 30 * (1 - pl), paint(col, 0.5 * pl, stroke=3))
            pen.c.drawCircle(x, y, 13 * on, paint(col, on))
        f = fit_font(pen, name, size, (x1 - x0) / (n - 1) - 10, 750) if not re.match(r"use[A-Z]", name) else mono(size - 4)
        pen.text_c(x, y + 42, name, f, col if on > 0.5 else WHITE, vis * (0.4 + 0.6 * on))
    glow_dot(pen, hx, y, 10, WHITE, ramp(t, cues[0] - 0.2, 0.3))
    if desc and cur >= 0:
        _, d, col = steps[cur]
        a = ramp(t, cues[cur], 0.35)
        pen.text_c(540, y + 112 + 10 * (1 - a), d, fit_font(pen, d, 34, 940), col, a)
    return cur


def typed(t, t0, n, cps=30):
    """Characters of an n-char string visible when typing starts at t0."""
    return 0 if t0 is None or t < t0 else min(n, int((t - t0) * cps))


def big_text(pen, cx, y, text, col, size, alpha=1.0, code=True, glow=0.0):
    f = mono(size) if code else font(size, 750)
    if glow > 0.02:
        w = pen.textlength(text, f)
        pen.c.drawRect(skia.Rect(cx - w / 2, y + size * 0.2, cx + w / 2, y + size * 0.9), paint(col, 0.25 * glow * alpha, blur=30))
    pen.text_c(cx, y, text, f, col, alpha)


def typed_lines(lines, t, t0, cps=40):
    """`show` dict for code_card that types the lines one after another from t0."""
    left = 0.0 if t < t0 else (t - t0) * cps
    out = {}
    for i, ln in enumerate(lines):
        out[i] = min(len(ln), left)
        left = max(0.0, left - len(ln))
    return out


def spinner(pen, cx, cy, r, t, col, alpha=1.0):
    """A rotating arc (infinite loop / busy)."""
    rect = skia.Rect(cx - r, cy - r, cx + r, cy + r)
    pen.c.drawArc(rect, (t * 360) % 360, 270, False, paint(col, alpha, stroke=r * 0.22))


# ===========================================================================
# Declarative stage: a scene is a stack of blocks, each animated on spoken cues.
# A cue is a word prefix (searched after the block's previous cue), (word, beat), or a
# beat number. Blocks stack in one column from y 345; too tall a stack logs "MISSING overflow".
# ===========================================================================
STAGE_TOP, STAGE_BOTTOM = 345, 1395


class Block:
    h = 100

    def resolve(self, sc):
        pass

    def start(self, sc):
        self.sc, self.last = sc, 0.0

    def cue(self, key):
        sc = self.sc
        if key is None:
            return None
        if isinstance(key, int):
            t = sc.beat(key)
        elif isinstance(key, tuple):
            t = sc.at(key[0], beat=key[1])
        else:
            t = sc.at(key, after=self.last + 0.01)
        self.last = t
        return t

    def aside(self, key):
        """A cue that does not move the search point (an element's end or its mark)."""
        keep = self.last
        t = self.cue(key)
        self.last = keep
        return t


class Track(Block):
    """steps: (name, description, colour, cue). A phase track with a playhead."""
    h = 190

    def __init__(self, *steps):
        self.steps = steps

    def resolve(self, sc):
        self.ts = [self.cue(s[3]) for s in self.steps]

    def draw(self, pen, t, y):
        step_track(pen, t, [s[:3] for s in self.steps], self.ts, y=y + 30)


class Pipe(Block):
    """items: (label, sub, colour, cue). Full-width rows joined by links that carry a comet."""

    def __init__(self, *items):
        self.items = items
        self.rh, self.gap = (106 if any(i[1] for i in items) else 86), 32
        self.h = len(items) * (self.rh + self.gap) - self.gap

    def resolve(self, sc):
        self.ts = [self.cue(i[3]) for i in self.items]

    def draw(self, pen, t, y):
        cur = max((k for k, t0 in enumerate(self.ts) if t >= t0), default=-1)
        for k, ((label, sub, col, _), t0) in enumerate(zip(self.items, self.ts)):
            p = ramp(t, t0, 0.4, back)
            if p <= 0:
                continue
            a = min(1.0, p) * (1.0 if k == cur else 0.68)
            yy = y + k * (self.rh + self.gap)
            panel(pen, (70, yy, 1010, yy + self.rh), a, radius=20, edge=col, glow=pulse(t, t0, 1.0), glow_col=col)
            if sub:
                pen.text(104, yy + 13, label, fit_font(pen, label, 34, 870), col, a)
                pen.text(104, yy + 62, sub, fit_font(pen, sub, 28, 870, 500), WHITE, 0.88 * a)
            else:
                pen.text(104, yy + 22, label, fit_font(pen, label, 34, 870), col, a)
            if k + 1 < len(self.ts) and t >= self.ts[k + 1] - 0.3:
                link(pen, (540, yy + self.rh), (540, yy + self.rh + self.gap), col,
                     ramp(t, self.ts[k + 1] - 0.3, 0.3), flow=self.ts[k + 1], t=t)


class Rows(Block):
    """items: (name, text, colour, cue[, mark[, mark cue]]), mark "ok" or "bad"."""

    def __init__(self, *items, row=112):
        self.items, self.row = items, row
        self.h = len(items) * (row + 14) - 14

    def resolve(self, sc):
        self.ts, self.ms = [], []
        for i in self.items:
            t0 = self.cue(i[3])
            self.ts.append(t0)
            self.ms.append(self.aside(i[5]) if len(i) > 5 else (t0 + 0.7 if len(i) > 4 else None))

    def draw(self, pen, t, y):
        out = []
        for i, t0, m in zip(self.items, self.ts, self.ms):
            mark = i[4] if len(i) > 4 else None
            out.append(dict(name=i[0], text=i[1], col=i[2], t0=t0, check=m if mark == "ok" else None,
                            bad=m if mark == "bad" else None))
        rows(pen, t, out, y, h=self.row, gap=14)


class Code(Block):
    """A code card. key types the lines in from that cue; hl: (line, colour, cue[, end cue])."""

    def __init__(self, lines, name="app.js", key=0, hl=(), size=32, type_it=True):
        self.lines, self.name, self.key, self.hls, self.size, self.type_it = lines, name, key, hl, size, type_it
        self.h = int(82 + len(lines) * size * 1.6 + 8)

    def resolve(self, sc):
        self.t0 = self.cue(self.key)
        self.hts = [(self.cue(h[2]), self.aside(h[3]) if len(h) > 3 else None) for h in self.hls]

    def draw(self, pen, t, y):
        a = ramp(t, self.t0 - 0.2, 0.35)
        if a <= 0:
            return
        hl = {}
        for (line_no, col, *_), (t0, end) in zip(self.hls, self.hts):
            st = ramp(t, t0, 0.3) * (1 - ramp(t, end, 0.3) if end is not None else 1)
            if st > 0.01:
                hl[line_no] = (col, st)
        show = typed_lines(self.lines, t, self.t0) if self.type_it else None
        code_card(pen, (70, y, 1010, y + self.h), self.lines, t, name=self.name, hl=hl, alpha=a, size=self.size, show=show)


class Lanes(Block):
    """items: (name, tag, colour, cue, [(text, colour, cue), ...]). Full-width stacked A/B lanes."""

    def __init__(self, *items):
        self.items = items
        self.hs = [92 + 56 * len(i[4]) for i in items]
        self.h = sum(self.hs) + 16 * (len(items) - 1)

    def resolve(self, sc):
        self.ts = []
        for i in self.items:
            self.ts.append((self.cue(i[3]), [self.cue(ln[2]) for ln in i[4]]))

    def draw(self, pen, t, y):
        for i, hh, (t0, lts) in zip(self.items, self.hs, self.ts):
            a = lane(pen, (70, y, 1010, y + hh), i[0], i[1], i[2], t, t0)
            if a:
                for k, ((txt, col, _), lt) in enumerate(zip(i[4], lts)):
                    b = a * ramp(t, lt, 0.35)
                    if b > 0:
                        pen.text(106, y + 84 + k * 56 + 8 * (1 - ramp(t, lt, 0.35)), txt, fit_font(pen, txt, 30, 868), col, b)
                x = 70 + 940 * ((t * 0.22) % 1)
                glow_dot(pen, x, y + hh, 6, i[2], 0.8 * a)
            y += hh + 16


class Bars(Block):
    """Racing timelines. items: (label, fraction of the width, colour, cue, end label)."""

    def __init__(self, *items, secs=2.5):
        self.items, self.secs = items, secs
        self.h = len(items) * 118 - 12

    def resolve(self, sc):
        self.ts = [self.cue(i[3]) for i in self.items]

    def draw(self, pen, t, y):
        for k, ((label, frac, col, _, end), t0) in enumerate(zip(self.items, self.ts)):
            a = ramp(t, t0 - 0.1, 0.3)
            if a <= 0:
                continue
            yy = y + k * 118
            pen.text(76, yy, label, fit_font(pen, label, 30, 560), WHITE, a)
            prog = clamp((t - t0) / (self.secs * max(frac, 0.15)))
            r = skia.RRect.MakeRectXY(skia.Rect(76, yy + 54, 1004, yy + 86), 16, 16)
            pen.c.drawRRect(r, paint(WHITE, 0.08 * a))
            xe = 76 + 928 * frac * prog
            pen.c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(76, yy + 54, max(100, xe), yy + 86), 16, 16), paint(col, 0.85 * a))
            if prog < 1:
                glow_dot(pen, xe, yy + 70, 9, WHITE, a)
            elif end:
                pen.text_r(1004, yy + 4, end, fit_font(pen, end, 28, 360), col, a * ramp(t, t0 + self.secs * max(frac, 0.15), 0.3))


class Ring(Block):
    """A loop: nodes on a circle, a dot moves to each on its cue, then keeps orbiting."""
    h = 640

    def __init__(self, *items, center=""):
        self.items, self.center = items, center

    def resolve(self, sc):
        self.ts = [self.cue(i[2]) for i in self.items]

    def draw(self, pen, t, y):
        cx, cy, r, n = 540, y + 320, 250, len(self.items)
        a0 = ramp(t, self.ts[0] - 0.3, 0.4)
        if a0 <= 0:
            return
        pen.c.drawCircle(cx, cy, r, paint(WHITE, 0.14 * a0, stroke=4))
        pos = 0.0
        for k, t0 in enumerate(self.ts):
            pos = max(pos, k * 1.0 * (1 if t >= t0 else 0))
            p = ramp(t, t0 - 0.1, 0.4)
            if 0 < p < 1 and k:
                pos = k - 1 + p
        if t >= self.ts[-1] + 0.8:
            pos += (t - self.ts[-1] - 0.8) * 0.9
        ang = -math.pi / 2 + 2 * math.pi * pos / n
        glow_dot(pen, cx + r * math.cos(ang), cy + r * math.sin(ang), 13, WHITE, a0)
        if self.center:
            big_text(pen, cx, cy - 26, self.center, CYAN, 34, a0)
        for k, ((name, col, _), t0) in enumerate(zip(self.items, self.ts)):
            p = ramp(t, t0, 0.4, back)
            if p > 0:
                th = -math.pi / 2 + 2 * math.pi * k / n
                x = cx + (r + 8) * math.cos(th)
                x = min(max(x, 90 + 13 * len(name)), 990 - 13 * len(name))
                node(pen, x, cy + (r + 8) * math.sin(th), name, col, min(1, p), hot=pulse(t, t0), size=28, fill=0.9)


class Fan(Block):
    """One source pill with links to a row of target pills; comets flow along the links."""
    h = 300

    def __init__(self, src, *targets):
        self.src, self.targets = src, targets

    def resolve(self, sc):
        self.t0 = self.cue(self.src[2])
        self.ts = [self.cue(i[2]) for i in self.targets]

    def draw(self, pen, t, y):
        a = ramp(t, self.t0, 0.4, back)
        if a <= 0:
            return
        n = len(self.targets)
        node(pen, 540, y + 50, self.src[0], self.src[1], min(1, a), hot=pulse(t, self.t0), size=32)
        for k, ((txt, col, _), t0) in enumerate(zip(self.targets, self.ts)):
            x = 70 + 940 * (k + 0.5) / n
            link(pen, (540, y + 86), (x, y + 216), col, ramp(t, t0 - 0.3, 0.35), flow=t0, t=t)
            p = ramp(t, t0, 0.4, back)
            if p > 0:
                size = 30 if n < 3 else 25
                while pen.textlength(txt, mono(size)) > 940 / n - 70 and size > 24:
                    size -= 1
                node(pen, x, y + 252, txt, col, min(1, p), hot=pulse(t, t0), size=size)


class Chips(Block):
    """Pills that pop in on their words, wrapped over as many lines as they need."""

    def __init__(self, *items, size=30):
        self.items, self.size = items, size
        self.lines, cur, w = [], [], 0
        for i in items:
            wd = len(i[0]) * size * 0.61 + 84
            if cur and w + wd > 940:
                self.lines.append(cur)
                cur, w = [], 0
            cur.append(i)
            w += wd
        self.lines.append(cur)
        self.h = len(self.lines) * int(size * 2.6)

    def resolve(self, sc):
        self.tm = {i[0]: self.cue(i[2]) for i in self.items}

    def draw(self, pen, t, y):
        f = mono(self.size)
        for k, ln in enumerate(self.lines):
            ws = [pen.textlength(i[0], f) + 48 for i in ln]
            x = 540 - (sum(ws) + 28 * (len(ln) - 1)) / 2
            for i, wd in zip(ln, ws):
                pop(pen, t, self.tm[i[0]], x + wd / 2, y + (k + 0.5) * self.size * 2.6, i[0], i[1], size=self.size, pad=24)
                x += wd + 28


class Big(Block):
    """A large value that changes on each cue: states (text, colour, cue)."""

    def __init__(self, *states, size=72):
        self.states, self.size = states, size
        self.h = int(size * 1.5)

    def resolve(self, sc):
        self.ts = [self.cue(s[2]) for s in self.states]

    def draw(self, pen, t, y):
        cur = max((k for k, t0 in enumerate(self.ts) if t >= t0), default=-1)
        if cur < 0:
            return
        txt, col, _ = self.states[cur]
        size = self.size
        while pen.textlength(txt, mono(size)) > 930 and size > 30:
            size -= 2
        big_text(pen, 540, y + 8, txt, col, size, ramp(t, self.ts[cur], 0.3), glow=pulse(t, self.ts[cur], 1.2))


class Note(Block):
    """A takeaway pill on its cue."""
    h = 58

    def __init__(self, text, col, key, until=None):
        self.text, self.col, self.key, self.until = text, col, key, until

    def resolve(self, sc):
        self.t0, self.end = self.cue(self.key), self.cue(self.until)

    def draw(self, pen, t, y):
        size = 30
        while pen.textlength(self.text, mono(size)) > 860 and size > 25:
            size -= 1
        pop(pen, t, self.t0, 540, y + 29, self.text, self.col, size=size, until=self.end)


def stage(*blocks):
    class Stage(Scene):
        def setup(self):
            for b in blocks:
                b.start(self)
                b.resolve(self)
            used = sum(b.h for b in blocks)
            room = STAGE_BOTTOM - STAGE_TOP - used
            if room < 18 * (len(blocks) - 1):
                self.cues[f"overflow by {18 * (len(blocks) - 1) - room} (MISSING)"] = 0.0
            self.gap = min(44, room / max(1, len(blocks) - 1)) if len(blocks) > 1 else 0
            self.y0 = STAGE_TOP + max(0, room - self.gap * (len(blocks) - 1)) * 0.4

        def draw(self, pen, t):
            y = self.y0
            for b in blocks:
                b.draw(pen, t, y)
                y += b.h + self.gap

    return Stage


def part(word, tag, chips, scenes):
    """SCENES for a part: the title hero, then one stage per list of blocks."""
    return [hero(word, f"QUICK JS & NODE  ·  {tag}", chips)] + [stage(*s) for s in scenes]
