#!/usr/bin/env python3
"""Portrait (1080x1920) engine for YouTube Shorts — adapted from engine.py.

Same scene kinds and helpers, but:
  - 1080x1920 portrait canvas
  - Normal pace (no [slow pace] prefix), WPS 2.5, shorter holds
  - Layouts adapted for narrow/tall format
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30

# ---------------------------------------------------------------------------
# Timing — faster for shorts
# ---------------------------------------------------------------------------
WPS = 2.7             # observed voice speed on shorts: ~2.6-2.8 words/s
BEAT_TAIL_S = 0.3
MEASURED_TAIL_S = 0.25  # real (local TTS) clip lengths -> short, uniform pause
MIN_SCENE_S = 3.0
MAX_ENTRIES = 75
INTRO_F = 10
TRANS_S = 0.4
GRID_F = 3
TYPE_CPS_MIN = 45

# ---------------------------------------------------------------------------
# Theme (same as engine.py)
# ---------------------------------------------------------------------------
BG = (13, 17, 23)
PANEL = (22, 27, 34)
PANEL2 = (33, 38, 45)
BORDER = (48, 54, 61)
TEXT = (230, 237, 243)
DIM = (139, 148, 158)
ACCENT = (88, 166, 255)
GREEN = (63, 185, 80)
YELLOW = (210, 153, 34)
RED = (248, 81, 73)
PURPLE = (188, 140, 255)
ORANGE = (240, 136, 62)
TEAL = (57, 197, 187)
CONSOLE_BG = (8, 11, 15)

C_KW = (255, 123, 114)
C_STR = (165, 214, 255)
C_NUM = (121, 192, 255)
C_FN = (210, 168, 255)
C_CMT = (139, 148, 158)
C_BUILTIN = (255, 166, 87)

# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------
@lru_cache(maxsize=None)
def _font(kind: str, size: int):
    cands = {
        "sans": [("/System/Library/Fonts/HelveticaNeue.ttc", 0),
                 ("/System/Library/Fonts/Helvetica.ttc", 0)],
        "sans_bold": [("/System/Library/Fonts/HelveticaNeue.ttc", 1),
                      ("/System/Library/Fonts/Helvetica.ttc", 1)],
        "mono": [("/System/Library/Fonts/Menlo.ttc", 0)],
        "mono_bold": [("/System/Library/Fonts/Menlo.ttc", 1),
                      ("/System/Library/Fonts/Menlo.ttc", 0)],
    }[kind]
    for path, index in cands:
        try:
            return ImageFont.truetype(path, size, index=index)
        except Exception:
            continue
    return ImageFont.load_default(size)


def sans(size): return _font("sans", int(size))
def sans_bold(size): return _font("sans_bold", int(size))
def mono(size): return _font("mono", int(size))
def mono_bold(size): return _font("mono_bold", int(size))

# ---------------------------------------------------------------------------
# Math helpers
# ---------------------------------------------------------------------------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))

def ease(p):
    p = clamp(p)
    return 4 * p * p * p if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2

def lerp(a, b, t):
    return a + (b - a) * t

def mix(c1, c2, t):
    t = clamp(t)
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))

def fade(color, t):
    return mix(BG, color, t)

# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------
def wrap(draw, text, font, max_w):
    lines, cur = [], ""
    for word in text.split():
        t = (cur + " " + word).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_par(draw, text, font, x, y, max_w, fill=TEXT, lh=None):
    lh = lh or int(font.size * 1.35)
    for ln in wrap(draw, text, font, max_w):
        draw.text((x, y), ln, font=font, fill=fill)
        y += lh
    return y


def text_c(draw, cx, y, text, font, fill=TEXT):
    tw = draw.textlength(text, font=font)
    draw.text((cx - tw / 2, y), text, font=font, fill=fill)


def rrect(draw, box, fill=None, outline=None, width=2, radius=16):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def box_node(draw, x, y, w, h, label, sub=None, border=BORDER, fill=PANEL,
             label_color=TEXT, label_font=None, sub_color=DIM, sub_font=None, width=3):
    rrect(draw, (x, y, x + w, y + h), fill=fill, outline=border, width=width)
    lf = label_font or sans_bold(30)
    if sub:
        sf = sub_font or sans(24)
        text_c(draw, x + w / 2, y + h / 2 - lf.size * 0.95, label, lf, label_color)
        text_c(draw, x + w / 2, y + h / 2 + 8, sub, sf, sub_color)
    else:
        text_c(draw, x + w / 2, y + h / 2 - lf.size * 0.62, label, lf, label_color)


def arrow(draw, x1, y1, x2, y2, color=ACCENT, width=5, head=18):
    draw.line((x1, y1, x2, y2), fill=color, width=width)
    ang = math.atan2(y2 - y1, x2 - x1)
    for da in (2.6, -2.6):
        draw.line((x2, y2, x2 + head * math.cos(ang + da), y2 + head * math.sin(ang + da)),
                  fill=color, width=width)


def arrow_partial(draw, x1, y1, x2, y2, p, color=ACCENT, width=5):
    if p <= 0.02:
        return
    arrow(draw, x1, y1, lerp(x1, x2, p), lerp(y1, y2, p), color=color, width=width)


def banner(draw, text, y=1750, color=ACCENT, font=None, fill=PANEL):
    f = font or sans_bold(32)
    tw = draw.textlength(text, font=f)
    bw, bh = tw + 80, 66
    x = (W - bw) / 2
    rrect(draw, (x, y, x + bw, y + bh), fill=fill, outline=color, width=3)
    draw.text((x + 40, y + bh / 2 - f.size * 0.62), text, font=f, fill=TEXT)


def chip(draw, x, y, text, color=ACCENT, font=None, fill=None):
    f = font or sans_bold(22)
    tw = draw.textlength(text, font=f)
    h = f.size + 16
    rrect(draw, (x, y, x + tw + 28, y + h), fill=fill, outline=color, width=2, radius=h // 2)
    draw.text((x + 14, y + 6), text, font=f, fill=color)
    return tw + 28


FOOTER = ""


def base_frame(heading=None, tag=None):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    if heading:
        hf = sans_bold(44)
        lines = wrap(d, heading, hf, W - 140)
        y = 60
        for ln in lines:
            d.text((70, y), ln, font=hf, fill=TEXT)
            y += int(hf.size * 1.2)
        d.rectangle((70, y + 6, 140, y + 11), fill=ACCENT)
    if tag:
        f = sans_bold(22)
        chip(d, W - 70 - d.textlength(tag, font=f) - 28, 68, tag, PURPLE)
    d.text((70, H - 60), FOOTER, font=sans(22), fill=DIM)
    return img


# ---------------------------------------------------------------------------
# Code rendering (same tokenizer as engine.py)
# ---------------------------------------------------------------------------
JS_KEYWORDS = {
    "var", "let", "const", "function", "return", "if", "else", "for", "while", "do",
    "new", "class", "extends", "super", "this", "typeof", "instanceof", "in", "of",
    "async", "await", "yield", "try", "catch", "finally", "throw", "import", "export",
    "default", "from", "null", "undefined", "true", "false", "switch", "case", "break",
    "continue", "delete", "void", "static", "get", "set",
}
JS_BUILTINS = {
    "console", "Promise", "Object", "Array", "process", "setTimeout", "setImmediate",
    "setInterval", "globalThis", "Math", "JSON", "require", "module", "exports",
    "Symbol", "Map", "Set", "WeakMap", "Reflect", "Proxy", "Error", "Number", "String",
    "Boolean", "queueMicrotask", "Buffer", "window",
}
TOKEN_RE = re.compile(
    r"(//.*$|`[^`]*`|\"[^\"]*\"|'[^']*'|\b\d[\d_]*(?:\.\d+)?n?\b|[A-Za-z_$][\w$]*)")


def draw_code_line(draw, line, x, y, font):
    cx, pos = x, 0
    for m in TOKEN_RE.finditer(line):
        if m.start() > pos:
            seg = line[pos:m.start()]
            draw.text((cx, y), seg, font=font, fill=TEXT)
            cx += draw.textlength(seg, font=font)
        tok = m.group(0)
        if tok.startswith("//"):
            color = C_CMT
        elif tok[0] in "\"'`":
            color = C_STR
        elif tok[0].isdigit():
            color = C_NUM
        elif tok in JS_KEYWORDS:
            color = C_KW
        elif tok in JS_BUILTINS:
            color = C_BUILTIN
        elif line[m.end():m.end() + 1] == "(":
            color = C_FN
        else:
            color = TEXT
        draw.text((cx, y), tok, font=font, fill=color)
        cx += draw.textlength(tok, font=font)
        pos = m.end()
    if pos < len(line):
        draw.text((cx, y), line[pos:], font=font, fill=TEXT)


def code_metrics(lines, box_w, box_h, size=32):
    longest = max((len(l) for l in lines), default=1)
    size = min(size, (box_w - 70) / (0.61 * max(longest, 1)),
               (box_h - 80) / (1.45 * max(len(lines), 1)))
    size = max(18, int(size))
    return size, int(size * 1.45)


def code_panel(draw, box, lines, upto=None, partial=None, hl=None, size=32, title=None,
               fit_height=True, dim_others=False):
    x0, y0, x1, y1 = box
    size, lh = code_metrics(lines, x1 - x0, y1 - y0, size)
    if fit_height:
        y1 = min(y1, y0 + 74 + lh * len(lines))
    rrect(draw, (x0, y0, x1, y1), fill=PANEL, outline=BORDER, width=2)
    for i, c in enumerate((RED, YELLOW, GREEN)):
        draw.ellipse((x0 + 22 + 24 * i, y0 + 18, x0 + 36 + 24 * i, y0 + 34), fill=c)
    if title:
        draw.text((x0 + 100, y0 + 12), title, font=sans(22), fill=DIM)
    font = mono(size)
    hls = set() if hl is None else ({hl} if isinstance(hl, int) else set(hl))
    upto = len(lines) if upto is None else upto
    ty = y0 + 52
    for i, line in enumerate(lines):
        typing = partial is not None and i == upto
        if i >= upto and not typing:
            break
        if i in hls:
            rrect(draw, (x0 + 8, ty - 6, x1 - 8, ty + lh - 6), fill=PANEL2, radius=8)
            draw.rectangle((x0 + 8, ty - 6, x0 + 14, ty + lh - 6), fill=ACCENT)
        text = line[:partial] if typing else line
        if dim_others and hls and i not in hls:
            draw.text((x0 + 26, ty), text, font=font, fill=(80, 88, 98))
        else:
            draw_code_line(draw, text, x0 + 26, ty, font)
        if typing:
            cx = x0 + 26 + draw.textlength(text, font=font)
            draw.rectangle((cx + 2, ty, cx + 2 + size * 0.42, ty + size), fill=ACCENT)
        ty += lh
    return (x0, y0, x1, y1), size, lh


def console_panel(draw, box, lines, n=None, title="Console output", size=28, min_h=200):
    x0, y0, x1, y1 = box
    f = mono(size)
    need = 86
    for item in lines:
        text = item if isinstance(item, str) else item[0]
        need += len(wrap(draw, text, f, x1 - x0 - 80)) * int(size * 1.45) + 8
    y1 = min(y1, y0 + max(min_h, need))
    rrect(draw, (x0, y0, x1, y1), fill=CONSOLE_BG, outline=BORDER, width=2)
    draw.text((x0 + 22, y0 + 14), title, font=sans_bold(22), fill=DIM)
    draw.line((x0 + 2, y0 + 50, x1 - 2, y0 + 50), fill=BORDER, width=2)
    ty = y0 + 66
    for item in lines[: (len(lines) if n is None else n)]:
        text, color = item if isinstance(item, tuple) else (item, TEXT)
        draw.text((x0 + 22, ty), ">", font=f, fill=DIM)
        for ln in wrap(draw, text, f, x1 - x0 - 80):
            draw.text((x0 + 50, ty), ln, font=f, fill=color)
            ty += int(size * 1.45)
        ty += 8


def memory_panel(draw, box, title, rows, hl=None, title_color=ACCENT, size=28,
                 new_rows=(), p=1.0, name_w=None, appear=1.0, empty_text="(empty)"):
    x0, y0, x1, y1 = box
    a = ease(appear)
    off_y = (1 - a) * 30
    y0, y1 = y0 + off_y, y1 + off_y
    rrect(draw, (x0, y0, x1, y1), fill=mix(BG, PANEL, a), outline=fade(title_color, a), width=3)
    draw.text((x0 + 22, y0 + 16), title, font=sans_bold(26), fill=fade(title_color, a))
    f = mono(size)
    rh = int(size * 1.9)
    nw = name_w or int((x1 - x0) * 0.38)
    hls = set() if hl is None else ({hl} if isinstance(hl, int) else set(hl))
    order = sorted(new_rows)
    ty = y0 + 68
    if not rows and empty_text:
        draw.text((x0 + 26, ty), empty_text, font=sans(26), fill=fade(DIM, a))
    for i, (name, value, color) in enumerate(rows):
        t = clamp(p * len(order) - order.index(i)) if i in order else 1.0
        t = min(t, a)
        off = (1 - ease(t)) * 40
        if i in hls:
            rrect(draw, (x0 + 12, ty - 8, x1 - 12, ty + rh - 14), fill=PANEL2,
                  outline=YELLOW, width=2, radius=8)
        draw.text((x0 + 26 + off, ty), name, font=f, fill=fade(TEXT, t))
        draw.text((x0 + 26 + nw + off, ty), value, font=f, fill=fade(color, t))
        ty += rh
    return ty


def table(draw, x, y, col_ws, header, rows, n_show=None, hl=None, size=26,
          header_color=ACCENT, pad=14):
    hf, cf = sans_bold(size), sans(size)
    lh = int(size * 1.3)
    total_w = sum(col_ws)

    def row_h(cells, font):
        return max(len(wrap(draw, c if isinstance(c, str) else c[0], font, w - 2 * pad))
                   for c, w in zip(cells, col_ws)) * lh + 2 * pad

    hh = row_h(header, hf)
    rrect(draw, (x, y, x + total_w, y + hh), fill=PANEL2, radius=10)
    cx = x
    for c, w in zip(header, col_ws):
        draw_par(draw, c, hf, cx + pad, y + pad, w - 2 * pad, fill=header_color, lh=lh)
        cx += w
    y += hh + 6
    for i, cells in enumerate(rows[: (len(rows) if n_show is None else n_show)]):
        rh = row_h(cells, cf)
        fill = PANEL2 if i == hl else PANEL
        rrect(draw, (x, y, x + total_w, y + rh), fill=fill,
              outline=ACCENT if i == hl else None, width=2, radius=10)
        cx = x
        for c, w in zip(cells, col_ws):
            text, color = (c, TEXT) if isinstance(c, str) else c
            font = mono(size - 2) if text.startswith("`") else cf
            draw_par(draw, text.strip("`"), font, cx + pad, y + pad, w - 2 * pad, fill=color, lh=lh)
            cx += w
        y += rh + 6
    return y


# ---------------------------------------------------------------------------
# Speech timing — no pace prefix for shorts
# ---------------------------------------------------------------------------
TAG = ""


def clean(text):
    return text.strip()


def speech_seconds(text, wps=None):
    words = len(clean(text).split())
    return words / (wps or WPS)


def full_speech(spec):
    return " ".join(b.strip() for b in spec["beats"])


def plan_timeline(scenes, wps=None, measured=None):
    plan, cursor, mi = [], 0, 0
    for spec in scenes:
        beats_s = [speech_seconds(b, wps) for b in spec["beats"]]
        tail = BEAT_TAIL_S
        if measured is not None:
            beats_s = measured[mi:mi + len(beats_s)]
            mi += len(beats_s)
            tail = MEASURED_TAIL_S
        beat_f = [math.ceil((b + tail) * FPS / GRID_F) * GRID_F for b in beats_s]
        min_f = math.ceil(max(MIN_SCENE_S, spec.get("min_s", 0)) * FPS / GRID_F) * GRID_F
        if sum(beat_f) < min_f:
            beat_f[-1] += min_f - sum(beat_f)
        cues_f, acc = [], 0
        for b in beat_f:
            cues_f.append(acc)
            acc += b
        ends_f = [c + max(GRID_F, round(b * FPS)) for c, b in zip(cues_f, beats_s)]
        plan.append(dict(spec=spec, start_f=cursor, frames=acc, cues_f=cues_f,
                         ends_f=ends_f, speech_s=sum(beats_s), beats_s=beats_s))
        cursor += acc
    return plan


# ---------------------------------------------------------------------------
# Scene renderers
# ---------------------------------------------------------------------------
def beat_at(cues_f, f):
    k = 0
    for i, c in enumerate(cues_f):
        if f >= c:
            k = i
    return k


def per_beat(spec, key, default=None):
    v = spec.get(key)
    n = len(spec["beats"])
    if v is None:
        return [default] * n
    assert len(v) == n, f"{spec.get('heading')}: '{key}' needs {n} entries, got {len(v)}"
    return v


def default_show(spec, n_items):
    n = len(spec["beats"])
    if spec.get("show"):
        return per_beat(spec, "show")
    if n == n_items:
        return list(range(1, n_items + 1))
    if n == n_items + 1:
        return list(range(0, n_items + 1))
    raise ValueError(f"{spec.get('heading')}: give 'show' (items={n_items}, beats={n})")


def draw_banner_for(spec, d, k):
    b = per_beat(spec, "banners")[k]
    if b:
        text, color = (b, ACCENT) if isinstance(b, str) else b
        banner(d, text, y=spec.get("banner_y", 1750), color=color)


def render_title(spec, k):
    img = base_frame(None, spec.get("tag"))
    d = ImageDraw.Draw(img)
    if spec.get("kicker"):
        text_c(d, W / 2, 500, spec["kicker"], sans_bold(30), PURPLE)
    tf = sans_bold(spec.get("title_size", 64))
    y = 600
    for ln in wrap(d, spec["title"], tf, W - 140):
        text_c(d, W / 2, y, ln, tf, TEXT)
        y += int(tf.size * 1.2)
    text_c(d, W / 2, y + 30, spec.get("subtitle", ""), sans(36), ACCENT)
    chips = spec.get("chips", [])
    if chips:
        f = sans_bold(24)
        widths = [d.textlength(c, font=f) + 28 for c in chips]
        total = sum(widths) + 20 * (len(chips) - 1)
        x = (W - total) / 2
        for c, wdt in zip(chips, widths):
            chip(d, x, y + 120, c, ACCENT, font=f)
            x += wdt + 20
    if spec.get("foot"):
        text_c(d, W / 2, 1600, spec["foot"], sans(28), DIM)
    return img


def render_bullets(spec, k):
    img = base_frame(spec["heading"], spec.get("tag"))
    d = ImageDraw.Draw(img)
    items = spec["items"]
    n_shown = default_show(spec, len(items))[k]
    hl = per_beat(spec, "hl")[k]
    y = 180
    quote = spec.get("quote")
    if quote:
        qf = sans(36)
        qlines = wrap(d, quote, qf, W - 180)
        qh = 48 + len(qlines) * 48
        rrect(d, (70, y, W - 70, y + qh), fill=PANEL, outline=BORDER, width=2)
        d.rectangle((70, y + 12, 78, y + qh - 12), fill=ACCENT)
        qy = y + 24
        for ln in qlines:
            d.text((100, qy), ln, font=qf, fill=TEXT)
            qy += 48
        y += qh + 36
    size = spec.get("size", 38)
    bf = sans(size)
    for i, it in enumerate(items[:n_shown]):
        text, color = (it, TEXT) if isinstance(it, str) else it
        if hl is not None and i == hl:
            color = YELLOW
        dim = hl is not None and i != hl
        if spec.get("numbered"):
            nf = sans_bold(size)
            d.text((78, y), f"{i + 1}.", font=nf, fill=ACCENT)
            tx = 130
        else:
            d.ellipse((78, y + size * 0.35, 94, y + size * 0.35 + 16), fill=ACCENT)
            tx = 120
        y = draw_par(d, text, bf, tx, y, W - 70 - tx,
                     fill=mix(color, BG, 0.45) if dim else color, lh=int(size * 1.3)) + 26
    draw_banner_for(spec, d, k)
    return img


def render_table(spec, k):
    img = base_frame(spec["heading"], spec.get("tag"))
    d = ImageDraw.Draw(img)
    rows = spec["rows"]
    n_shown = default_show(spec, len(rows))[k]
    hl = per_beat(spec, "hl")[k]
    col_ws = spec.get("col_ws") or [(W - 140) // len(spec["header"])] * len(spec["header"])
    table(d, 70, spec.get("y", 180), col_ws, spec["header"], rows, n_show=n_shown, hl=hl,
          size=spec.get("size", 28))
    draw_banner_for(spec, d, k)
    return img


def render_diagram(spec, k, p):
    img = base_frame(spec["heading"], spec.get("tag"))
    d = ImageDraw.Draw(img)
    step = per_beat(spec, "steps", None)[k]
    step = k if step is None else step
    spec["draw"](d, step, p)
    draw_banner_for(spec, d, k)
    return img


def code_layout(spec):
    """Portrait: code on top, console below."""
    has_console = bool(spec.get("console"))
    top = spec.get("code_top", 180)
    if has_console:
        split = spec.get("split", 1000)
        return (70, top, W - 70, split), (70, split + 30, W - 70, 1700)
    return (70, top, W - 70, 1700), None


def render_code(spec, k, upto, partial, nout):
    img = base_frame(spec["heading"], spec.get("tag"))
    d = ImageDraw.Draw(img)
    lines = spec["_lines"]
    code_box, con_box = code_layout(spec)
    hl = per_beat(spec, "hl")[k]
    code_panel(d, code_box, lines, upto=upto, partial=partial, hl=hl,
               size=spec.get("size", 36), title=spec.get("file"),
               dim_others=spec.get("dim_others", False))
    if con_box:
        console_panel(d, con_box, spec["console"], n=nout,
                      title=spec.get("console_title", "Console output"),
                      size=spec.get("console_size", 28))
    draw_banner_for(spec, d, k)
    return img


# ---------------------------------------------------------------------------
# Per-frame state machine
# ---------------------------------------------------------------------------
def code_schedule(spec, pl):
    lines = spec["_lines"]
    n = len(spec["beats"])
    upto = per_beat(spec, "upto", None)
    if upto[0] is None:
        upto = [len(lines)] * n
    typing = spec.get("type", True)
    sched, prev = [], 0
    for k in range(n):
        start, end = prev, max(prev, upto[k])
        chars = [max(3, len(lines[i]) + 2) for i in range(start, end)]
        beat_f = pl["ends_f"][k] - pl["cues_f"][k]
        if not typing or not chars:
            tf = 0
        else:
            tf = min(sum(chars) / TYPE_CPS_MIN * FPS, max(6, 0.7 * beat_f))
        sched.append((start, end, max(0, int(tf)), chars))
        prev = end
    return sched


def frame_states(pl):
    spec = pl["spec"]
    kind = spec["kind"]
    cues = pl["cues_f"]
    if kind == "code":
        sched = code_schedule(spec, pl)
        outs = per_beat(spec, "out", None)
        if outs[0] is None:
            outs = [len(spec.get("console") or [])] * len(cues)
    trans_list = per_beat(spec, "trans", None)
    for f in range(pl["frames"]):
        k = beat_at(cues, f)
        local = f - cues[k]
        intro = round((f + 1) / INTRO_F, 3) if f < INTRO_F else 1.0
        if kind == "code":
            start, end, tf, chars = sched[k]
            if local >= tf or tf == 0:
                upto, partial = end, None
                done_at = tf
            else:
                typed = sum(chars) * (local + 1) / tf
                upto, partial = start, None
                for i, c in enumerate(chars):
                    if typed >= c:
                        typed -= c
                        upto = start + i + 1
                    else:
                        partial = int(len(spec["_lines"][start + i]) * typed / c)
                        break
                done_at = None
            prev_out = outs[k - 1] if k > 0 else 0
            nout = outs[k] if (done_at is not None and local >= done_at + 6) else prev_out
            if k == 0 and f < INTRO_F:
                nout = prev_out
            yield ("code", k, upto, partial, nout, intro)
        else:
            tr = trans_list[k] if trans_list[k] is not None else spec.get("trans_s", TRANS_S)
            tr_f = max(1, round(tr * FPS))
            p = 1.0 if k == 0 else round(clamp((local + 1) / tr_f), 3)
            yield (kind, k, p, intro)


BG_IMG = Image.new("RGB", (W, H), BG)


class SceneRenderer:
    def __init__(self, spec):
        self.spec = spec
        self.full = {}

    def step_img(self, k):
        if k not in self.full:
            kind = self.spec["kind"]
            if kind == "title":
                self.full[k] = render_title(self.spec, k)
            elif kind == "bullets":
                self.full[k] = render_bullets(self.spec, k)
            elif kind == "table":
                self.full[k] = render_table(self.spec, k)
            elif kind == "diagram":
                self.full[k] = render_diagram(self.spec, k, 1.0)
        return self.full[k]

    def draw(self, state):
        kind = state[0]
        intro = state[-1]
        if kind == "code":
            _, k, upto, partial, nout, _ = state
            img = render_code(self.spec, k, upto, partial, nout)
        else:
            _, k, p, _ = state
            if p >= 1.0:
                img = self.step_img(k)
            elif kind == "diagram" and self.spec.get("animate", True):
                img = render_diagram(self.spec, k, ease(p))
            else:
                img = Image.blend(self.step_img(k - 1), self.step_img(k), ease(p))
        if intro < 1.0:
            img = Image.blend(BG_IMG, img, intro)
        return img


# ---------------------------------------------------------------------------
# Validation + output
# ---------------------------------------------------------------------------
def prepare(scenes):
    for i, spec in enumerate(scenes):
        assert spec.get("beats"), f"scene {i + 1} has no beats"
        sp = full_speech(spec)
        assert len(sp) < 800, f"scene {i + 1} speech is {len(sp)} chars (limit 800)"
        for key in ("show", "upto", "out", "hl", "banners", "trans", "steps"):
            v = spec.get(key)
            assert v is None or len(v) == len(spec["beats"]), \
                f"scene {i + 1}: '{key}' has {len(v)} entries but there are {len(spec['beats'])} beats"
        for k, b in enumerate(spec["beats"]):
            n = len(b.split())
            if not 3 <= n <= 45:
                print(f"WARNING: scene {i + 1} beat {k + 1} has {n} words (keep beats 3-45 words)")
        if spec["kind"] in ("bullets", "table"):
            default_show(spec, len(spec["items" if spec["kind"] == "bullets" else "rows"]))
        if spec["kind"] == "code":
            spec["_lines"] = spec["code"].strip("\n").split("\n")
            up = spec.get("upto")
            assert not up or up == sorted(up), f"scene {i + 1}: 'upto' must never decrease"


def split_plan(plan, max_entries):
    blocks = []
    for p in plan:
        sp = p["spec"]
        if not blocks or sp.get("split_before", sp["kind"] in ("title", "bullets")):
            blocks.append([])
        blocks[-1].append(p)
    nb = lambda ps: sum(len(p["spec"]["beats"]) for p in ps)  # noqa: E731
    total = nb(plan)
    n = max(1, math.ceil(total / max_entries))
    while True:
        target = math.ceil(total / n)
        groups, cur, cnt = [], [], 0
        for blk in blocks:
            b = nb(blk)
            if cur and cnt + b > target and len(groups) < n - 1:
                groups.append(cur)
                cur, cnt = [], 0
            cur.extend(blk)
            cnt += b
        groups.append(cur)
        if n >= len(blocks):
            return groups
        if all(sum(len(p["spec"]["beats"]) for p in g) <= max_entries for g in groups):
            return groups
        n += 1


def write_json(plan, out_json, title, voice, duration):
    off = plan[0]["start_f"]
    scenes_json = [{"start": round((p["start_f"] - off + c) / FPS, 1), "speech": b.strip()}
                   for p in plan for c, b in zip(p["cues_f"], p["spec"]["beats"])]
    starts = [s["start"] for s in scenes_json]
    assert starts[0] == 0 and starts == sorted(starts)
    payload = {"title": title, "duration": duration, "voice": voice, "scenes": scenes_json}
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def print_table(plan):
    print("\nscene  start(s)  length(s)  speech(s)  silence(s)  beats  heading")
    print("-----  --------  ---------  ---------  ----------  -----  -------")
    for i, p in enumerate(plan):
        spec = p["spec"]
        heading = spec.get("heading") or spec.get("title", "")
        length = p["frames"] / FPS
        print(f"{i + 1:>5}  {p['start_f'] / FPS:>8.1f}  {length:>9.1f}  {p['speech_s']:>9.1f}"
              f"  {length - p['speech_s']:>10.1f}  {len(spec['beats']):>5}  {heading}")


def run(scenes, *, title, out_base: Path, footer=None, voice="Holt"):
    global FOOTER
    if footer:
        FOOTER = footer
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--scenes", default="")
    ap.add_argument("--wps", type=float, default=None)
    ap.add_argument("--durations", default=None)
    ap.add_argument("--max-entries", type=int, default=MAX_ENTRIES)
    args = ap.parse_args()

    prepare(scenes)
    dur_file = Path(args.durations) if args.durations else out_base.parent / "durations.json"
    measured = json.loads(dur_file.read_text()) if dur_file.exists() else None
    if measured is not None:
        print(f"Using measured voice lengths from {dur_file}")
        n_beats = sum(len(sc["beats"]) for sc in scenes)
        assert len(measured) == n_beats, f"durations needs one entry per beat ({n_beats})"
    plan = plan_timeline(scenes, wps=args.wps, measured=measured)
    total_f = sum(p["frames"] for p in plan)
    print_table(plan)
    print(f"\nPlanned total: {total_f / FPS:.1f}s ({total_f / FPS / 60:.1f} min), "
          f"{len(plan)} scenes")

    if args.scenes:
        selected = [plan[int(s) - 1] for s in args.scenes.split(",")]
        out_mp4 = out_base.with_name(out_base.name + "_preview.mp4")
        dur = render_mp4(selected, plan, out_mp4)
        print(f"\nPreview: {out_mp4} ({dur:.1f}s)")
        return

    groups = split_plan(plan, args.max_entries)
    for gi, group in enumerate(groups):
        if len(groups) == 1:
            base, gtitle = out_base, title
        else:
            base = out_base.with_name(f"{out_base.name}_{gi + 1}of{len(groups)}")
            gtitle = f"{title} ({gi + 1}/{len(groups)})"
        out_mp4, out_json = base.with_suffix(".mp4"), base.with_suffix(".json")
        n_entries = sum(len(p["spec"]["beats"]) for p in group)
        gdur = sum(p["frames"] for p in group) / FPS
        if args.dry_run:
            write_json(group, out_json, gtitle, voice, round(gdur, 1))
            print(f"(dry run) wrote {out_json} ({n_entries} entries, {gdur:.1f}s)")
            continue
        dur = render_mp4(group, plan, out_mp4)
        write_json(group, out_json, gtitle, voice, round(dur, 1))
        print(f"\nVideo {gi + 1}/{len(groups)}: {dur:.1f}s ({dur / 60:.1f} min), "
              f"{len(group)} scenes, {n_entries} Vids entries")
        print(f"Files: {out_mp4}\n       {out_json}")


def render_mp4(selected, plan, out_mp4):
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out_mp4)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    want = sum(p["frames"] for p in selected)
    written = 0
    for p in selected:
        r = SceneRenderer(p["spec"])
        last_state, last_bytes = None, None
        for state in frame_states(p):
            if state != last_state:
                last_bytes = r.draw(state).tobytes()
                last_state = state
            proc.stdin.write(last_bytes)
            written += 1
        si = plan.index(p) + 1
        print(f"  rendered scene {si}/{len(plan)} ({written}/{want} frames)", flush=True)
    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        sys.exit("ffmpeg failed")
    dur = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(out_mp4)],
        capture_output=True, text=True).stdout.strip())
    if abs(dur - want / FPS) > 0.1:
        print(f"WARNING: mp4 is {dur:.2f}s but timeline is {want / FPS:.2f}s")
    return dur
