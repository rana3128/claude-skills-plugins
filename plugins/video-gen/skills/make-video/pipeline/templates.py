"""Animated diagram layouts for portrait shorts (1080x1920), synced to the narration, drawn with skin.py.

Live mode (build_part.py): every element - node, connector, label, bullet, line - appears on the word
that names it (Kokoro word timings). The element being explained glows; older ones dim; connectors
draw along smooth curves with a comet packet that keeps flowing while they are discussed.
Static mode (lint, contact sheets): paint everything up to beat `step`.

Item syntax:  "Label (sub text) [green]"          flow / graph node
              "Heading: line one; line two [red]" cards, stack, compare, grid
              "plain line" / "= result"           calc
              "~ From -> To: label [red]"         graph edge
Optional in any item: "@k" = not before beat k, "{words}" = the spoken words that trigger it
(default: the item's own first keyword, e.g. "Orders table" appears when "order(s)" is said).
"""

import re

from engine_short import ease, wrap
from skin import (AMBER, CORAL, INDIGO, MINT, MUTED, ORANGE, TEAL, TEXT, VIOLET, W, Pen,
                  font, mix, sans, sans_bold)

COLORS = dict(blue=INDIGO, green=MINT, yellow=AMBER, red=CORAL, purple=VIOLET, orange=ORANGE,
              teal=TEAL, dim=MUTED)
CYCLE = [INDIGO, TEAL, VIOLET, ORANGE, MINT, AMBER]
X0, X1, TOP, BOTTOM = 70, 1010, 270, 1740
SIZES = range(50, 23, -2)
WARN = []
_OVER = []          # words too wide at the size being tried

APPEAR_S = 0.5      # fade + slide-in
EDGE_S = 0.9        # connector growth
LOOP_S = 1.6        # comet loop while a connector is highlighted
STOP = set("the a an and or of to in on for with from by is are be it its this that then than as "
           "at into your you we our not no all each per via any "
           # number words and fillers recur too often to mark one moment
           "one two three four five six seven eight nine ten hundred thousand million "
           "first only just can will must get use more less".split())


# ---------------------------------------------------------------------------
# items, keywords, timing
# ---------------------------------------------------------------------------
def take_cue(s):
    m = re.search(r"\{([^}]*)\}", s)
    return ((s[:m.start()] + s[m.end():]).strip(), m.group(1)) if m else (s, None)


def parse(raw, i, cues=True):
    s, at, cue = raw.strip(), None, None
    if cues:
        s, cue = take_cue(s)
    m = re.search(r"(?:^|\s)@(\d+)\b", s)
    if m:
        at, s = int(m.group(1)), (s[:m.start()] + s[m.end():]).strip()
    color = CYCLE[i % len(CYCLE)]
    m = re.search(r"\s*\[(\w+)\]", s)
    if m and m.group(1) in COLORS:
        color, s = COLORS[m.group(1)], (s[:m.start()] + s[m.end():]).strip()
    return dict(at=at, fixed=at is not None, cue=cue, text=s, color=color, t0=None)


def keywords(text):
    return [w for w in re.findall(r"[a-z0-9]+", text.lower())
            if len(w) >= 3 and w not in STOP and not w.isdigit()]


def spoken(words):
    """[[word, s, e]] -> [(normalised word, s)]; spelled letters merged and marked: A P I -> #api."""
    out = []
    for w, s, _ in words:
        n = re.sub(r"[^a-z0-9]", "", w.lower())
        if not n:
            continue
        letter = len(n) == 1 and n.isalpha() and w.isupper()
        if letter and out and out[-1][2]:
            out[-1] = (out[-1][0] + n, out[-1][1], True)
        else:
            out.append((n, s, letter))
    return [("#" + n if letter and len(n) > 1 else n, s) for n, s, letter in out]


def stem(w):
    for suf in ("ing", "ed", "es", "s", "e"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[:-len(suf)]
    return w


def same_word(kw, w):
    if w.startswith("#"):                          # spelled letters: "A C D N" -> "#acdn" holds "cdn"
        return len(kw) >= 2 and kw in w[1:]
    if kw == w or stem(kw) == stem(w):
        return True
    if min(len(kw), len(w)) < 4:
        return False
    k = 0
    while k < min(len(kw), len(w)) and kw[k] == w[k]:
        k += 1
    return k >= max(4, min(len(kw), len(w)) - 2)


def find_word(kws, words, lo):
    """Time of the first spoken word at/after lo that matches a keyword (first keyword wins)."""
    for kw in kws:
        for w, t in words:
            if t >= lo - 0.05 and same_word(kw, w):
                return t
    return None


def fill_gaps(elems, starts, end):
    """Unmatched elements are spread evenly between their matched neighbours."""
    i = 0
    while i < len(elems):
        if elems[i]["t0"] is not None:
            i += 1
            continue
        j = i
        while j < len(elems) and elems[j]["t0"] is None:
            j += 1
        a = elems[i - 1]["t0"] if i else starts[elems[i]["at"] or 0]
        if elems[i]["fixed"]:
            a = max(a, starts[elems[i]["at"]])
        b = elems[j]["t0"] if j < len(elems) else min(end - 1.0, a + 1.2 * (j - i + 1))
        b = max(a, b)
        lead = 0 if (i == 0 or elems[i]["fixed"]) else 1
        for k in range(i, j):
            elems[k]["t0"] = a + (b - a) * (k - i + lead) / (j - i + lead)
        i = j


def schedule(items, n_beats):
    n = len(items)
    for i, it in enumerate(items):
        if it["at"] is None:
            it["at"] = min(n_beats - 1, i * n_beats // n)
        it["at"] = min(it["at"], n_beats - 1)


def lines_fit(d, text, f, max_w, where):
    ls = wrap(d, text, f, max_w)
    for ln in ls:
        if d.textlength(ln, font=f) > max_w + 1:
            _OVER.append(f"{where}: word too wide for its box: {ln!r}")
    return ls


def split_sub(text):
    m = re.match(r"(.*?)\s*\((.*)\)$", text)
    return (m.group(1), m.group(2)) if m else (text, "")


# ---------------------------------------------------------------------------
# base class
# ---------------------------------------------------------------------------
class Layout:
    """Subclasses define self.elems (narration order), measure(pen, s) and paint(pen)."""
    GAP = 32

    def __init__(self, raw, name):
        self.items = [parse(r, i) for i, r in enumerate(raw)]
        self.elems = self.items
        self.name = name
        self.plan = None
        self.now = None
        self.step = 0

    def bind(self, n_beats):
        schedule(self.items, n_beats)
        return self

    # --- timing ---------------------------------------------------------
    def keys_for(self, e):
        return keywords(e["cue"] or e["text"])

    def set_times(self, starts, beat_words, end):
        """starts: beat start (s, scene-local); beat_words: per beat [[w, s, e]]."""
        words = [(w, starts[k] + t) for k, ws in enumerate(beat_words) for w, t in spoken(ws)]
        t_prev = 0.0
        for e in self.elems:
            lo = max(t_prev, starts[e["at"]]) if e["fixed"] else t_prev
            e["t0"] = find_word(self.keys_for(e), words, lo)
            if e["t0"] is not None:
                t_prev = e["t0"]
        fill_gaps(self.elems, starts, end)
        self.after_times(words, starts)
        everything = self.all_elems()
        ts = sorted({round(e["t0"], 2) for e in everything})
        for e in everything:                       # when the next element arrives, this one cools
            later = [t for t in ts if t > e["t0"] + 0.6]
            e["t_cold"] = later[0] if later else 1e9

    def all_elems(self):
        return self.elems

    def after_times(self, words, starts):
        pass

    def timing_log(self):
        return [f"{e['t0']:6.2f}s  {e['text'][:50]}" for e in sorted(self.all_elems(), key=lambda e: e["t0"])]

    # --- per-element state ----------------------------------------------
    def vis(self, e):
        if self.now is None:
            return 1.0 if e["at"] <= self.step else 0.0
        return ease(min(1.0, max(0.0, (self.now - e["t0"]) / APPEAR_S)))

    def hot(self, e):
        if self.now is None or self.now < e["t0"]:
            return 0.0
        return 1.0 - min(1.0, max(0.0, (self.now - e["t_cold"]) / 0.5))

    def alpha(self, e, h=None):
        """Opacity: fade-in times focus (older elements settle at 75%)."""
        if self.now is None:
            return self.vis(e)
        h = self.hot(e) if h is None else h
        return self.vis(e) * (0.75 + 0.25 * h)

    def slide(self, e):
        return int((1 - self.vis(e)) * 22)

    # --- fitting + entry points -----------------------------------------
    def fit(self, pen):
        for s in SIZES:
            _OVER.clear()
            self.plan = self.measure(pen, s)
            if self.plan["h"] <= BOTTOM - TOP and not _OVER:
                break
        else:
            WARN.extend(_OVER)
            if self.plan["h"] > BOTTOM - TOP:
                WARN.append(f"{self.name}: content is {self.plan['h']}px tall, "
                            f"only {BOTTOM - TOP}px fit even at size {SIZES[-1]}")
        n_gaps = self.plan.get("n_gaps", len(self.items) - 1)
        slack = max(0, BOTTOM - TOP - self.plan["h"])
        self.gap = self.GAP + min(110, slack // (n_gaps + 2)) if n_gaps else self.GAP
        self.plan["h"] += (self.gap - self.GAP) * n_gaps
        self.y0 = TOP + max(0, (BOTTOM - TOP - self.plan["h"]) * 2 // 5)
        self.placed(pen)

    def placed(self, pen):
        pass

    def paint_at(self, pen, now=None, step=None):
        """now = scene time in seconds (live), or step = beat index (static)."""
        if self.plan is None:
            self.fit(pen)
        self.now, self.step = now, (step if step is not None else 10 ** 6)
        self.paint(pen)


# ---------------------------------------------------------------------------
# title card
# ---------------------------------------------------------------------------
class Title(Layout):
    def __init__(self, title, question, chips, kicker):
        self.name, self.plan, self.now, self.step = "title", None, None, 0
        self.title, self.question, self.kicker = title, question, kicker
        self.items = [dict(at=0, fixed=True, cue=None, text=title, color=INDIGO, t0=0.0)]
        self.items += [dict(at=0, fixed=True, cue=None, text=c, color=CYCLE[i % 6], t0=0.6 + 0.25 * i)
                       for i, c in enumerate(chips)]
        self.elems = self.items

    def bind(self, n_beats):
        return self

    def set_times(self, starts, beat_words, end):
        for e in self.items:
            e["t_cold"] = 1e9

    def measure(self, pen, s):
        return dict(h=0)

    def paint(self, pen):
        tf, qf, kf, cf = font(86, 700), font(40, 400), font(30, 500), font(28, 500)
        t = self.vis(self.items[0])
        y = 640 - self.slide(self.items[0])
        pen.bar((70, y + 6, 77, y + 40), INDIGO, t)
        pen.text(96, y + 4, self.kicker, kf, MUTED, t)
        y += 90
        for ln in wrap(pen, self.title, tf, W - 140):
            pen.text(70, y, ln, tf, TEXT, t)
            y += 100
        y += 20
        for ln in wrap(pen, self.question, qf, W - 160):
            pen.text(70, y, ln, qf, mix(MUTED, TEXT, 0.35), t)
            y += 54
        x, y = 70, y + 50
        for e in self.items[1:]:
            a = self.vis(e)
            tw = pen.textlength(e["text"], cf)
            pen.pill((x, y, x + tw + 44, y + 56), e["color"], a)
            pen.text(x + 22, y + 12, e["text"], cf, e["color"], a)
            x += tw + 62


# ---------------------------------------------------------------------------
# flow: vertical chain of nodes
# ---------------------------------------------------------------------------
class Flow(Layout):
    GAP = 56

    def keys_for(self, e):
        return keywords(e["cue"] or split_sub(e["text"])[0]) or keywords(e["text"])

    def measure(self, pen, s):
        w = X1 - X0 - 80
        boxes = []
        for it in self.items:
            label, sub = split_sub(it["text"])
            lf, sf = sans_bold(s), sans(max(22, s - 8))
            ll = lines_fit(pen, label, lf, w - 60, self.name)
            sl = lines_fit(pen, sub, sf, w - 60, self.name) if sub else []
            h = 44 + len(ll) * int(lf.size * 1.22) + len(sl) * int(sf.size * 1.3) + (8 if sl else 0)
            boxes.append((ll, sl, lf, sf, h))
        return dict(boxes=boxes, w=w, h=sum(b[4] for b in boxes) + self.GAP * (len(boxes) - 1))

    def paint(self, pen):
        w, x, y = self.plan["w"], (W - self.plan["w"]) // 2, self.y0
        for i, (e, (ll, sl, lf, sf, h)) in enumerate(zip(self.items, self.plan["boxes"])):
            if self.vis(e) > 0:
                a, hot = self.alpha(e), self.hot(e)
                if i:
                    g = 1.0 if self.now is None else min(1.0, (self.now - e["t0"]) / EDGE_S)
                    path = Pen.curve((W / 2, y - self.gap + 8), (W / 2, y - 10))
                    pen.connector(path, e["color"], max(g, 0.02), a, hot,
                                  packet=g if (self.now is not None and g < 1) else None)
                yy0 = y + self.slide(e)
                pen.card((x, yy0, x + w, yy0 + h), e["color"], a, hot)
                yy = yy0 + 22
                for ln in ll:
                    pen.text_c(W / 2, yy, ln, lf, TEXT, a)
                    yy += int(lf.size * 1.22)
                yy += 8 if sl else 0
                for ln in sl:
                    pen.text_c(W / 2, yy, ln, sf, MUTED, a)
                    yy += int(sf.size * 1.3)
            y += h + self.gap


# ---------------------------------------------------------------------------
# cards / stack / grid / compare: each card heading and each bullet is its own element
# ---------------------------------------------------------------------------
def head_body(text):
    head, sep, body = text.partition(":")
    if not sep:
        return "", [p.strip() for p in text.split(";") if p.strip()]
    return head.strip(), [p.strip() for p in body.split(";") if p.strip()]


class Cards(Layout):
    """Full-width stacked cards ('Heading: a; b' or plain rows); Grid lays them out in columns."""
    GAP = 32
    COLS = 1

    def __init__(self, raw, name, cols=None):
        super().__init__(raw, name)
        self.items = [parse(r, i, cues=False) for i, r in enumerate(raw)]   # cues per line below
        self.cols = cols or self.COLS
        self.elems = []
        for it in self.items:
            head, body = head_body(it["text"])
            it["head"], it["cue"] = take_cue(head)
            it["bullets"] = [dict(at=None, fixed=False, cue=c, text=b, color=it["color"], t0=None)
                             for b, c in map(take_cue, body)]
            last = it["bullets"][-1] if it["bullets"] else None
            if head and last and last["cue"] and not it["cue"] and not any(
                    same_word(k, w) for k in keywords(last["cue"]) for w in keywords(last["text"])):
                it["cue"], last["cue"] = last["cue"], None   # a trailing cue that names the card
            if it["head"]:
                self.elems.append(it)
            self.elems += it["bullets"]

    def bind(self, n_beats):
        schedule(self.items, n_beats)
        for it in self.items:
            for b in it["bullets"]:
                b["at"], b["fixed"] = it["at"], it["fixed"]
        return self

    def after_times(self, words, starts):
        for it in self.items:                      # a card without heading appears with its 1st line
            if not it["head"]:
                it["t0"] = it["bullets"][0]["t0"]

    def all_elems(self):
        return self.elems + [it for it in self.items if not it["head"]]

    def keys_for(self, e):
        if e.get("head"):
            return keywords(e["cue"] or e["head"]) or keywords(e["text"])
        return keywords(e["cue"] or e["text"])

    def block(self, pen, it, s, w):
        hf, bf = sans_bold(s + 2), sans(s)
        hl = lines_fit(pen, it["head"], hf, w - 76, self.name) if it["head"] else []
        bl = [lines_fit(pen, b["text"], bf, w - 110, self.name) for b in it["bullets"]]
        h = 52 + len(hl) * int(hf.size * 1.22) + (16 if hl and bl else 0) \
            + sum(len(b) * int(bf.size * 1.32) + 14 for b in bl)
        return dict(hl=hl, bl=bl, hf=hf, bf=bf, h=h)

    def measure(self, pen, s):
        w = (X1 - X0 - self.GAP * (self.cols - 1)) // self.cols
        cards = [self.block(pen, it, s, w) for it in self.items]
        rows = [cards[i:i + self.cols] for i in range(0, len(cards), self.cols)]
        rh = [max(c["h"] for c in r) for r in rows]
        return dict(cards=cards, w=w, rh=rh, h=sum(rh) + self.GAP * (len(rh) - 1), n_gaps=len(rh) - 1)

    def paint(self, pen):
        w = self.plan["w"]
        for i, (it, c) in enumerate(zip(self.items, self.plan["cards"])):
            r, colm = divmod(i, self.cols)
            x = X0 + colm * (w + self.GAP)
            y = self.y0 + sum(self.plan["rh"][:r]) + self.gap * r
            h = self.plan["rh"][r] if self.cols > 1 else c["h"]
            if self.vis(it) <= 0:
                continue
            y += self.slide(it)
            ch = max([self.hot(it)] + [self.hot(b) for b in it["bullets"]]) if self.now is not None else 0.0
            a = self.alpha(it, ch)
            pen.card((x, y, x + w, y + h), it["color"], a, ch, radius=28, tint=0.07)
            pen.bar((x + 22, y + 28, x + 28, y + h - 28), it["color"], a)
            yy = y + 26
            for ln in c["hl"]:
                pen.text(x + 50, yy, ln, c["hf"], it["color"], a)
                yy += int(c["hf"].size * 1.22)
            yy += 16 if c["hl"] and c["bl"] else 0
            for b, ls in zip(it["bullets"], c["bl"]):
                if self.vis(b) > 0:
                    ba = self.alpha(b)
                    if len(c["bl"]) > 1 or c["hl"]:
                        pen.dot(x + 58, yy + c["bf"].size * 0.62, 5, it["color"], ba)
                        tx = x + 80
                    else:
                        tx = x + 50
                    ly = yy
                    for ln in ls:
                        pen.text(tx, ly, ln, c["bf"], TEXT, ba)
                        ly += int(c["bf"].size * 1.32)
                yy += len(ls) * int(c["bf"].size * 1.32) + 14


class Grid(Cards):
    GAP = 28
    COLS = 2


# ---------------------------------------------------------------------------
# calc: lines that appear one by one; '= ...' lines are highlighted results
# ---------------------------------------------------------------------------
class Calc(Layout):
    GAP = 34

    def measure(self, pen, s):
        rows = []
        for it in self.items:
            res = it["text"].startswith("=")
            f = font(s + 6, 650) if res else sans(s + 2)
            ls = lines_fit(pen, it["text"].lstrip("= ").strip(), f, X1 - X0 - 120, self.name)
            rows.append((res, f, ls, len(ls) * int(f.size * 1.28) + (48 if res else 0)))
        return dict(rows=rows, h=sum(r[3] for r in rows) + self.GAP * (len(rows) - 1))

    def paint(self, pen):
        y = self.y0
        for e, (res, f, ls, h) in zip(self.items, self.plan["rows"]):
            if self.vis(e) > 0:
                a, hot = self.alpha(e), self.hot(e)
                yy0 = y + self.slide(e)
                if res:
                    pen.card((X0, yy0, X1, yy0 + h), MINT, a, hot, radius=24, tint=0.12)
                yy = yy0 + (24 if res else 0)
                for ln in ls:
                    if res:
                        pen.text_c(W / 2, yy, ln, f, MINT, a)
                    else:
                        pen.text(X0 + 10, yy, ln, f, TEXT, a)
                    yy += int(f.size * 1.28)
            y += h + self.gap


# ---------------------------------------------------------------------------
# graph: nodes in rows, curved connectors between any two nodes
# ---------------------------------------------------------------------------
class Graph(Layout):
    """Row item: "App (sub) [color] & Orders table"  (nodes split by '&').
    Edge item: "~ App -> Orders table: 1 save [green]".  Nodes are referenced by label (exact,
    then prefix). Edges carry the story: each edge appears on its label's word; its source node
    appears with it (or earlier, if named in the same beat) and its target as the connector arrives."""
    PAD = 22

    def __init__(self, raw, name):
        self.name, self.plan, self.now, self.step = name, None, None, 0
        rows, edges = [], []
        for i, r in enumerate(raw):
            m = re.match(r"\s*(@\d+)\s+(~.*)", r)          # "@2 ~ A -> B" is an edge too
            if m:
                r = f"{m.group(2)} {m.group(1)}"
            (edges if r.lstrip().startswith("~") else rows).append((i, r.lstrip("~ ").strip()))
        self.rows = [[parse(n, i + j) for j, n in enumerate(r.split("&"))] for i, r in rows]
        self.edges = [parse(e, 0) for _, e in edges]   # edges default to indigo
        self.nodes = [n for row in self.rows for n in row]
        self.items = self.nodes + self.edges
        for n in self.nodes:
            n["label"], n["sub"] = split_sub(n["text"])
        for e in self.edges:
            ends, _, e["label"] = e["text"].partition(":")
            a, _, b = ends.partition("->")
            e["a"], e["b"], e["label"] = self.find(a), self.find(b), e["label"].strip()
        self.row_of = {id(n): r for r, row in enumerate(self.rows) for n in row}
        self.elems = self.edges + [n for n in self.nodes if not self.touching(n)]

    def find(self, ref):
        ref = ref.strip().lower()
        if not ref:
            raise ValueError(f"{self.name}: an edge has an empty end (no ':' or '->' inside node names)")
        for test in (str.__eq__, str.startswith):      # exact name first, then prefix
            for n in self.nodes:
                if test(n["label"].lower(), ref):
                    return n
        raise ValueError(f"{self.name}: edge end {ref!r} matches no node")

    def touching(self, n):
        return [e for e in self.edges if n in (e["a"], e["b"])]

    def keys_for(self, e):
        if "a" in e:
            return keywords(e["cue"] or e["label"]) or keywords(e["b"]["label"])
        return keywords(e["cue"] or e["label"])

    def all_elems(self):
        return self.items

    def bind(self, n_beats):
        schedule(self.edges, n_beats)
        for n in self.nodes:
            if n["at"] is None:
                n["at"] = min([e["at"] for e in self.touching(n)], default=0)
        pairs = {}
        for e in self.edges:
            key = frozenset((id(e["a"]), id(e["b"])))
            e["k"] = pairs.get(key, 0)
            pairs[key] = e["k"] + 1
        for e in self.edges:
            e["n_par"] = pairs[frozenset((id(e["a"]), id(e["b"])))]
        spans = [sorted((self.row_of[id(e["a"])], self.row_of[id(e["b"])])) for e in self.edges]
        self.weight = [1 + sum(a <= g < b for a, b in spans) for g in range(len(self.rows) - 1)]
        return self

    def after_times(self, words, starts):
        for n in self.nodes:
            ts = [e["t0"] for e in self.touching(n) if e["a"] is n] \
                + [e["t0"] + EDGE_S * 0.7 for e in self.touching(n) if e["b"] is n]
            if ts:
                # named earlier in the same beat as its first connector -> appear on that word
                first = min(ts)
                beat = max(k for k, s in enumerate(starts) if s <= first + 1e-6)
                own = find_word(self.keys_for(n), words, starts[beat])
                n["t0"] = own if own is not None and own < first else first

    def measure(self, pen, s):
        boxes, row_h = {}, []
        for row in self.rows:
            n = len(row)
            inner = any(e["a"] in row and e["b"] in row for e in self.edges)
            w = min(600, (X1 - X0 - (230 if inner else 36) * (n - 1)) // n)
            for rs in range(s, 21, -2):          # a crowded row shrinks alone, not the whole graph
                mark = len(_OVER)
                lf, sf = sans_bold(rs), sans(max(20, rs - 8))
                fits = [(lines_fit(pen, nd["label"], lf, w - 2 * self.PAD, self.name),
                         lines_fit(pen, nd["sub"], sf, w - 2 * self.PAD, self.name) if nd["sub"] else [])
                        for nd in row]
                if len(_OVER) == mark or rs <= 22:
                    break
                del _OVER[mark:]
            hs = []
            for node, (ll, sl) in zip(row, fits):
                h = 2 * self.PAD + 8 + len(ll) * int(lf.size * 1.2) + len(sl) * int(sf.size * 1.28) \
                    + (6 if sl else 0)
                boxes[id(node)] = dict(ll=ll, sl=sl, w=w, lf=lf, sf=sf)
                hs.append(h)
            row_h.append(max(hs))
        self.ef = font(max(22, s - 10), 600)
        # room for connectors + labels: more connectors crossing a gap -> taller gap; scales with font
        self.min_gaps = [int((64 + 30 * (w - 1)) * s / 36) for w in self.weight]
        h = sum(row_h) + sum(self.min_gaps)
        return dict(boxes=boxes, row_h=row_h, h=h, h0=h, n_gaps=len(row_h) - 1)

    def placed(self, pen):
        """Node boxes: spare height goes to the gaps, more to gaps crossed by more connectors."""
        n_gaps = len(self.rows) - 1
        slack = max(0, BOTTOM - TOP - self.plan["h0"]) * 0.8
        gaps = [g + min(520, slack * w / sum(self.weight)) for g, w in zip(self.min_gaps, self.weight)]
        y = TOP + max(0, (BOTTOM - TOP - sum(self.plan["row_h"]) - sum(gaps)) * 2 // 5)
        for r, (row, rh) in enumerate(zip(self.rows, self.plan["row_h"])):
            n = len(row)
            w = self.plan["boxes"][id(row[0])]["w"]
            step_x = (X1 - X0 - w) // (n - 1) if n > 1 else 0
            x = X0 if n > 1 else (W - w) // 2
            for i, node in enumerate(row):
                self.plan["boxes"][id(node)]["box"] = (x + i * step_x, y, x + i * step_x + w, y + rh)
            y += rh + (gaps[r] if r < n_gaps else 0)
        for e in self.edges:
            e["path"] = self.edge_path(e)
        self.place_labels(pen)
        self.lint()

    def edge_path(self, e):
        """Smooth curve: bottom -> top between rows, side -> side within a row."""
        ba, bb = self.plan["boxes"][id(e["a"])]["box"], self.plan["boxes"][id(e["b"])]["box"]
        cax, cbx = (ba[0] + ba[2]) / 2, (bb[0] + bb[2]) / 2
        ra, rb = self.row_of[id(e["a"])], self.row_of[id(e["b"])]
        off = (e["k"] - (e["n_par"] - 1) / 2) * 26
        if id(e["a"]) > id(e["b"]):               # both directions of a pair keep their sides
            off = -off
        if ra == rb:
            sgn = 1 if cbx > cax else -1
            cay, cby = (ba[1] + ba[3]) / 2, (bb[1] + bb[3]) / 2
            p0 = (ba[2] + 8 if sgn > 0 else ba[0] - 8, cay + off)
            p3 = (bb[0] - 10 if sgn > 0 else bb[2] + 10, cby + off)
            return Pen.curve(p0, p3, vertical=False)
        down = rb > ra
        wa, wb = ba[2] - ba[0], bb[2] - bb[0]
        sa = max(-wa * 0.32, min(wa * 0.32, (cbx - cax) * 0.3))
        sb = max(-wb * 0.32, min(wb * 0.32, (cax - cbx) * 0.3))
        p0 = (cax + sa + off, (ba[3] + 8) if down else (ba[1] - 8))
        p3 = (cbx + sb + off, (bb[1] - 12) if down else (bb[3] + 12))
        return Pen.curve(p0, p3)

    def place_labels(self, pen):
        """Slide each label along (or beside) its connector to the first spot clear of everything."""
        taken = [self.plan["boxes"][id(n)]["box"] for n in self.nodes]
        hit = lambda a, b: a[0] < b[2] + 6 and b[0] < a[2] + 6 and a[1] < b[3] + 6 and b[1] < a[3] + 6
        for e in self.edges:
            if not e["label"]:
                continue
            tw = pen.textlength(e["label"], self.ef)
            hh = self.ef.size + 22
            side, first, bx = tw / 2 + 30, None, None
            for f, dx in [(f, dx) for dx in (0, side, -side, side + 120, -side - 120)
                          for f in (0.5, 0.35, 0.65, 0.25, 0.75, 0.15, 0.85)]:
                mx, my = Pen.point_at(e["path"], f)
                mx += dx
                bx = (mx - tw / 2 - 20, my - hh / 2, mx + tw / 2 + 20, my + hh / 2)
                if bx[0] < X0 or bx[2] > X1:
                    continue
                first = first or bx
                if not any(hit(bx, o) for o in taken):
                    break
            else:
                bx = first or bx
            e["lbox"] = bx
            taken.append(bx)

    def lint(self):
        rects = [("node " + n["label"], self.plan["boxes"][id(n)]["box"]) for n in self.nodes]
        rects += [("label " + e["label"], e["lbox"]) for e in self.edges if e["label"]]
        for i, (na, a) in enumerate(rects):
            if a[0] < X0 - 2 or a[2] > X1 + 2:
                WARN.append(f"{self.name}: {na} is outside the safe area")
            for nb, b in rects[i + 1:]:
                if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                    WARN.append(f"{self.name}: {na} overlaps {nb}")

    def paint(self, pen):
        live = self.now is not None
        for e in self.edges:                      # connectors under the nodes
            if self.vis(e) <= 0:
                continue
            g = min(1.0, (self.now - e["t0"]) / EDGE_S) if live else 1.0
            h = self.hot(e)
            q = None
            if live and g < 1:
                q = g
            elif live and h > 0.5:
                q = ((self.now - e["t0"] - EDGE_S) % LOOP_S) / LOOP_S
            pen.connector(e["path"], e["color"], max(g, 0.02), self.alpha(e) if live else 1.0, h, packet=q)
        for n in self.nodes:
            if self.vis(n) <= 0:
                continue
            b = self.plan["boxes"][id(n)]
            dy = self.slide(n)
            box = (b["box"][0], b["box"][1] + dy, b["box"][2], b["box"][3] + dy)
            hn = max([self.hot(n)] + [self.hot(e) for e in self.touching(n)]) if live else 0.0
            a = self.alpha(n, hn)
            pen.card(box, n["color"], a, hn)
            lf, sf = b["lf"], b["sf"]
            th = len(b["ll"]) * int(lf.size * 1.2) + len(b["sl"]) * int(sf.size * 1.28) + (6 if b["sl"] else 0)
            yy = (box[1] + box[3] - th) / 2
            for ln in b["ll"]:
                pen.text_c((box[0] + box[2]) / 2, yy, ln, lf, TEXT, a)
                yy += int(lf.size * 1.2)
            yy += 6 if b["sl"] else 0
            for ln in b["sl"]:
                pen.text_c((box[0] + box[2]) / 2, yy, ln, sf, MUTED, a)
                yy += int(sf.size * 1.28)
        for e in self.edges:                      # labels on top, once the connector is half drawn
            if not e["label"] or self.vis(e) <= 0:
                continue
            g = min(1.0, max(0.0, (self.now - e["t0"]) / EDGE_S)) if live else 1.0
            if g > 0.45:
                a = min(1.0, (g - 0.45) / 0.4) * (self.alpha(e) if live else 1.0)
                bx = e["lbox"]
                pen.pill(bx, e["color"], a)
                pen.text(bx[0] + 20, bx[1] + 11, e["label"], self.ef, mix(e["color"], TEXT, 0.25), a)


KINDS = {
    "graph": Graph,
    "flow": Flow,
    "cards": Cards,
    "stack": Cards,
    "grid": Grid,
    "compare": lambda raw, name: Grid(raw, name, cols=len(raw)),
    "calc": Calc,
}
