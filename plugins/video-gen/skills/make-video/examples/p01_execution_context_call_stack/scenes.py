"""p01 Execution context, call stack, strict mode: scenes in the kinetic design (DESIGN.md)."""
import kinetic as K
from kinetic import (CYAN, VIOLET, AMBER, GREEN, RED, WHITE, DIM, Scene, ramp, pulse, back, mono, pop, rows)
from skin import font, paint

KICKER = "QUICK JS & NODE  ·  JS CORE"
Title = K.hero("Execution Context", KICKER, [("run your code", CYAN, "runs"), ("execution", VIOLET, "execution"),
                                             ("context", GREEN, "context")])

CODE = ["var name = 'Ada'", "function hi() { return name }", "hi()"]


class Phases(Scene):
    def setup(self):
        self.env = self.at("environment")
        self.parts = [self.at("variables", beat=0), self.at("scope", beat=0), self.at("this", beat=0)]
        self.ts = [self.at("creation", beat=1), self.at("execution", beat=2)]
        self.scan, self.mem = self.at("scans"), self.at("memory")
        self.vals, self.names = self.at("values"), self.at("names")

    def slot(self, pen, y, name, val, col, a, hot):
        pen.text(120, y, name, mono(34), WHITE, a)
        pen.text_r(960, y, val, mono(34), col, a)
        if hot > 0:
            r = K.skia.RRect.MakeRectXY(K.skia.Rect(100, y - 12, 980, y + 54), 14, 14)
            pen.c.drawRRect(r, paint(col, 0.2 * hot * a))

    def draw(self, pen, t):
        a = K.lane(pen, (70, 345, 1010, 505), "execution context", "", CYAN, t, self.env)
        if a:
            for x, txt, col, t0 in zip((250, 540, 830), ("variables", "scope", "this"), (GREEN, VIOLET, AMBER), self.parts):
                pop(pen, t, t0, x, 450, txt, col, size=27)
        K.step_track(pen, t, [("Creation", "set up memory, run nothing", VIOLET), ("Execution", "run line by line", GREEN)],
                     self.ts, y=565, x0=300, x1=780)
        c = ramp(t, self.ts[0] - 0.2, 0.4)
        if c > 0:
            ex = t >= self.ts[1]
            k = int((t - self.ts[1]) / 1.3) if ex else int((t - self.scan) / 0.7) if t >= self.scan else -1
            hl = {min(k, 2): (GREEN if ex else VIOLET, 1.0)} if k >= 0 and (ex or k <= 2) else None
            K.code_card(pen, (70, 730, 1010, 985), CODE, t, name="app.js", hl=hl, alpha=c, size=32)
        m = K.lane(pen, (70, 1005, 1010, 1290), "memory", "", VIOLET, t, self.mem, code=False)
        if m:
            v = "'Ada'" if t >= self.vals else "undefined"
            self.slot(pen, 1085, "name", v, GREEN if t >= self.vals else AMBER,
                      m * ramp(t, self.mem + 0.3, 0.3), pulse(t, self.vals, 1.2))
            self.slot(pen, 1180, "hi", "function", CYAN, m * ramp(t, self.mem + 0.7, 0.3), 0)
        pop(pen, t, self.names, 540, 1345, "names exist before the code runs", GREEN, size=27)


class Kinds(Scene):
    def setup(self):
        self.glob = self.at("global")
        self.fn, self.call = self.at("function", beat=1), self.at("same")
        self.calls = [self.at("three", beat=1) + 0.25 * k for k in range(3)]
        self.own = self.at("own", beat=1)
        self.ev, self.rare = self.at("eval"), self.at("rarely")

    def draw(self, pen, t):
        rows(pen, t, [dict(name="global", text="one, created when the script starts", col=VIOLET, t0=self.glob)], 350)
        a = K.lane(pen, (70, 490, 1010, 1110), "function", "new for every call", CYAN, t, self.fn)
        if a:
            for k, (arg, t0) in enumerate(zip("ABC", self.calls)):
                p = ramp(t, t0, 0.4, back)
                if p <= 0:
                    continue
                y = 590 + k * 165 + 20 * (1 - min(1, p))
                K.panel(pen, (110, y, 970, y + 145), min(1, p), radius=20, edge=CYAN, glow=pulse(t, t0), glow_col=CYAN)
                pen.text(140, y + 22, f"greet('{arg}')", mono(34), WHITE, min(1, p))
                pen.text(140, y + 84, f"name = '{arg}'", mono(30), GREEN, min(1, p) * ramp(t, self.own, 0.4))
                pen.text_r(940, y + 22, f"context {k + 1}", mono(26), DIM, min(1, p))
        rows(pen, t, [dict(name="eval", text="its own context, rarely used", col=AMBER, t0=self.ev, bad=self.rare)], 1135)


FRAMES = [("global", VIOLET), ("main()", CYAN), ("fetchUser()", GREEN), ("parse()", AMBER)]
BASE, H0 = 1370, 138


class Stack(Scene):
    def setup(self):
        self.t0 = [self.at("global"), self.at("main"), self.at("fetch"), self.at("parse")]
        self.push, self.single, self.frozen = self.at("pushes"), self.at("single"), self.at("frozen")
        self.ret, self.cont = self.at("returns"), self.at("continues")
        self.keeps, self.over, self.err = self.at("keeps"), self.at("overflows"), self.at("range")

    def draw(self, pen, t):
        squeeze = ramp(t, self.keeps - 0.2, 0.4)
        h, gap = H0 - 40 * squeeze, 12 - 2 * squeeze
        items = [(n, c, t0, self.ret) for (n, c), t0 in zip(FRAMES, self.t0)]
        items[3:3] = []
        items += [("recurse()", RED, self.keeps + 0.3 * k, None) for k in range(5)]
        live = [it for it in items if t >= it[2] and (it[3] is None or it[0] != "parse()" or t < it[3] + 0.4)]
        for i, (name, col, t0, _) in enumerate(live):
            top = i == len(live) - 1
            gone = ramp(t, self.ret, 0.4) if name == "parse()" else 0
            p = ramp(t, t0, 0.35)
            al = p * (1 - gone) * (1.0 if top else 1 - 0.45 * ramp(t, self.single, 0.4))
            y = BASE - (i + 1) * (h + gap) - 60 * (1 - p) - 70 * gone
            K.panel(pen, (70, y, 1010, y + h), al, radius=20, edge=col, glow=pulse(t, t0, 0.8), glow_col=col)
            pen.text(110, y + h / 2 - 24, name, mono(38), col, al)
            if top and t >= self.single:
                K.pill(pen, 850, y + h / 2, "running", GREEN, alpha=al, f=mono(26), pad=20, hot=pulse(t, self.cont))
            elif t >= self.frozen and not top:
                pen.text_r(960, y + h / 2 - 16, "frozen", mono(28), DIM, al * ramp(t, self.frozen, 0.4))
        pop(pen, t, self.push, 540, 620, "push: a new context on top", CYAN, size=30, until=self.single)
        pop(pen, t, self.single, 540, 420, "one thread: only the top runs", GREEN, size=30, until=self.keeps)
        pop(pen, t, self.ret, 540, 520, "parse returns: pop", AMBER, size=30, until=self.keeps)
        b = ramp(t, self.err - 0.3, 0.3)
        if b > 0:
            K.panel(pen, (70, 340, 1010, 440), b, radius=20, edge=RED, glow=pulse(t, self.err, 1.2), glow_col=RED)
            pen.text_c(540, 374, "RangeError: Maximum call stack size exceeded", mono(27), RED, b)


class Strict(Scene):
    def setup(self):
        self.auto, self.cls = self.at("automatic"), self.at("classes")
        self.l = [self.at("assigning"), self.at("value", beat=2), self.at("writing")]
        self.r = [self.at("throws", beat=1), self.at("undefined", beat=2), self.at("throws", beat=3)]
        self.loud = self.at("loud")

    def draw(self, pen, t):
        pop(pen, t, self.auto, 540, 375, "automatic: ES modules and classes", GREEN, size=30)
        data = [("count = 1", "sloppy: creates a global", "strict: ReferenceError", RED),
                ("function f() { return this }", "sloppy: globalThis", "strict: undefined", AMBER),
                ("Object.freeze(o).x = 1", "sloppy: fails silently", "strict: TypeError", RED)]
        for k, (code, old, new, col) in enumerate(data):
            y = 440 + k * 280
            a = K.lane(pen, (70, y, 1010, y + 262), code, "", CYAN, t, self.l[k])
            if a:
                f = font(32, 500)
                pen.text(110, y + 96, old, f, DIM, a)
                K.strike(pen, 108, 112 + pen.textlength(old, f), y + 118, RED, ramp(t, self.r[k], 0.4), a)
                pen.text(110, y + 170, new, mono(34), col, a * ramp(t, self.r[k], 0.4))
                if t >= self.r[k]:
                    K.check(pen, 950, y + 188, 18, GREEN, ramp(t, self.r[k], 0.3))
        pop(pen, t, self.loud, 540, 1330 + 40, "silent bugs become loud errors", GREEN, size=30)


SCENES = [Title, Phases, Kinds, Stack, Strict]
