"""Modern frame skin for portrait shorts, drawn with Skia: anti-aliased curves, soft shadows, glow.

"Systems blueprint" look: ink canvas with a faint dot grid, role-tinted cards with hairline
borders, thin curved connectors with comet packets, pill labels, SF Pro type.
Pen exposes textlength() like PIL's ImageDraw, so engine_short.wrap() works with it.
"""

import functools

import numpy as np
import skia
from PIL import Image

W, H = 1080, 1920

INK = (15, 20, 34)
GRID = (34, 43, 66)
SURF = (24, 32, 51)
LINE = (52, 64, 94)
TEXT = (236, 239, 247)
MUTED = (141, 151, 176)

INDIGO = (139, 156, 255)
TEAL = (67, 209, 190)
MINT = (110, 220, 158)
CORAL = (255, 123, 139)
AMBER = (245, 185, 95)
VIOLET = (183, 148, 255)
ORANGE = (255, 159, 90)


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def c4(rgb, alpha=1.0):
    return skia.Color4f(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, max(0.0, min(1.0, alpha)))


def cint(rgb, alpha=1.0):
    """Integer ARGB colour, as the gradient shaders expect."""
    return skia.ColorSetARGB(int(255 * max(0.0, min(1.0, alpha))), *rgb)


def paint(rgb, alpha=1.0, stroke=0.0, blur=0.0):
    p = skia.Paint(AntiAlias=True, Color4f=c4(rgb, alpha))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        p.setStrokeCap(skia.Paint.kRound_Cap)
        p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p


class Font:
    """skia.Font plus the .size attribute the layout code reads."""

    def __init__(self, size, weight):
        tf = skia.Typeface(".AppleSystemUIFont", skia.FontStyle(weight, 5, skia.FontStyle.kUpright_Slant))
        self.sk = skia.Font(tf, size)
        self.sk.setEdging(skia.Font.Edging.kAntiAlias)
        self.sk.setSubpixel(True)
        self.size = size
        self.ascent = -self.sk.getMetrics().fAscent


@functools.lru_cache(None)
def font(size, weight=400):
    return Font(int(size), weight)


def sans(size):
    return font(size, 400)


def sans_bold(size):
    return font(size, 650)


@functools.lru_cache(None)
def background():
    s = skia.Surface.MakeRaster(skia.ImageInfo.Make(W, H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType))
    c = s.getCanvas()
    c.clear(c4(INK))
    glow = skia.Paint(Shader=skia.GradientShader.MakeRadial(
        (W * 0.5, H * 0.32), 1100, [cint((32, 42, 72), 0.55), cint(INK, 0.0)]))
    c.drawRect(skia.Rect(0, 0, W, H), glow)
    dot = paint(GRID, 0.9)
    for y in range(24, H, 40):
        for x in range(20, W, 40):
            c.drawCircle(x, y, 1.6, dot)
    return s.makeImageSnapshot()


class Pen:
    def __init__(self, canvas=None):
        self.c = canvas

    # --- measuring (PIL-compatible) -------------------------------------
    def textlength(self, text, font):
        return font.sk.measureText(text)

    # --- text -----------------------------------------------------------
    def text(self, x, y, s, f, rgb, alpha=1.0):
        """y is the top of the line box (as in PIL)."""
        if alpha > 0.01 and s:
            self.c.drawString(s, x, y + f.ascent, f.sk, paint(rgb, alpha))

    def text_c(self, cx, y, s, f, rgb, alpha=1.0):
        self.text(cx - self.textlength(s, f) / 2, y, s, f, rgb, alpha)

    def text_r(self, rx, y, s, f, rgb, alpha=1.0):
        self.text(rx - self.textlength(s, f), y, s, f, rgb, alpha)

    # --- shapes ---------------------------------------------------------
    def card(self, box, rgb, alpha=1.0, hot=0.0, radius=26, tint=0.10, shadow=True):
        """Role-tinted card: soft shadow, tinted fill, hairline border that lights up when hot."""
        if alpha <= 0.01:
            return
        r = skia.RRect.MakeRectXY(skia.Rect(*box), radius, radius)
        if shadow:
            sh = r.makeOffset(0, 14)
            self.c.drawRRect(sh, paint((0, 0, 0), 0.45 * alpha, blur=22))
        if hot > 0.02:
            self.c.drawRRect(r, paint(rgb, 0.35 * hot * alpha, stroke=10, blur=14))
        self.c.drawRRect(r, paint(mix(SURF, rgb, tint), alpha))
        self.c.drawRRect(r, paint(mix(LINE, rgb, 0.5 + 0.5 * hot), alpha, stroke=1.6 + 1.4 * hot))

    def bar(self, box, rgb, alpha=1.0):
        r = skia.RRect.MakeRectXY(skia.Rect(*box), (box[2] - box[0]) / 2, (box[2] - box[0]) / 2)
        self.c.drawRRect(r, paint(rgb, alpha))

    def pill(self, box, rgb, alpha=1.0):
        h = box[3] - box[1]
        r = skia.RRect.MakeRectXY(skia.Rect(*box), h / 2, h / 2)
        self.c.drawRRect(r, paint(mix(INK, rgb, 0.22), 0.96 * alpha))
        self.c.drawRRect(r, paint(mix(INK, rgb, 0.45), 0.9 * alpha, stroke=1.2))

    def dot(self, x, y, r, rgb, alpha=1.0):
        self.c.drawCircle(x, y, r, paint(rgb, alpha))

    # --- connectors -----------------------------------------------------
    @staticmethod
    def curve(p0, p3, vertical=True):
        path = skia.Path()
        path.moveTo(*p0)
        if vertical:
            dy = (p3[1] - p0[1]) * 0.5
            path.cubicTo(p0[0], p0[1] + dy, p3[0], p3[1] - dy, *p3)
        else:
            dx = (p3[0] - p0[0]) * 0.5
            path.cubicTo(p0[0] + dx, p0[1], p3[0] - dx, p3[1], *p3)
        return path

    def connector(self, path, rgb, g=1.0, alpha=1.0, hot=0.0, packet=None, width=3.0):
        """Draw the first g (0..1) of the path, an arrowhead at its tip, and a comet at `packet`."""
        if alpha <= 0.01 or g <= 0.01:
            return
        m = skia.PathMeasure(path, False)
        L = m.getLength()
        seg = skia.Path()
        m.getSegment(0, L * g, seg, True)
        if hot > 0.02:
            self.c.drawPath(seg, paint(rgb, 0.35 * hot * alpha, stroke=width + 8, blur=8))
        self.c.drawPath(seg, paint(rgb, (0.55 + 0.45 * hot) * alpha, stroke=width + hot))
        pos, tan = m.getPosTan(L * g)
        tx, ty = tan.x(), tan.y()
        size = 14 + 2 * hot
        head = skia.Path()
        head.moveTo(pos.x() - tx * size - ty * size * 0.6, pos.y() - ty * size + tx * size * 0.6)
        head.lineTo(pos.x(), pos.y())
        head.lineTo(pos.x() - tx * size + ty * size * 0.6, pos.y() - ty * size - tx * size * 0.6)
        self.c.drawPath(head, paint(rgb, (0.7 + 0.3 * hot) * alpha, stroke=width + hot))
        if packet is not None:
            for k in range(7):                       # comet: head + fading trail
                q = packet - k * 0.018
                if q < 0:
                    break
                p, _ = m.getPosTan(L * q)
                a = (1 - k / 7) ** 2
                self.c.drawCircle(p.x(), p.y(), 9 - k * 0.9, paint(rgb, 0.9 * a * alpha))
            p, _ = m.getPosTan(L * packet)
            self.c.drawCircle(p.x(), p.y(), 16, paint(rgb, 0.45 * alpha, blur=9))
            self.c.drawCircle(p.x(), p.y(), 5, paint(TEXT, alpha))

    @staticmethod
    def point_at(path, f):
        m = skia.PathMeasure(path, False)
        p, _ = m.getPosTan(m.getLength() * f)
        return p.x(), p.y()


# ---------------------------------------------------------------------------
# frames
# ---------------------------------------------------------------------------
def new_canvas():
    s = skia.Surface.MakeRaster(skia.ImageInfo.Make(W, H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType))
    s.getCanvas().drawImage(background(), 0, 0)
    return s


def to_pil(surface):
    return Image.fromarray(np.ascontiguousarray(surface.toarray()[:, :, :3]), "RGB")


HEAD = font(54, 700)
SMALL = font(26, 500)


def chrome(pen, heading, topic, footer, progress=None, accent=INDIGO):
    """Heading (left, up to 2 lines), progress line, footer with topic + series."""
    from engine_short import wrap
    y = 92
    for ln in wrap(pen, heading or "", HEAD, W - 140):
        pen.text(70, y, ln, HEAD, TEXT)
        y += 66
    if progress is not None:
        pen.c.drawRect(skia.Rect(0, 0, W, 6), paint(LINE, 0.6))
        grad = skia.Paint(Shader=skia.GradientShader.MakeLinear(
            [(0, 0), (W, 0)], [cint(INDIGO), cint(TEAL)]))
        pen.c.drawRect(skia.Rect(0, 0, W * progress, 6), grad)
    if topic:
        pen.dot(80, H - 74, 6, accent)
        pen.text(98, H - 90, topic, SMALL, MUTED)
    if footer:
        pen.text_r(W - 70, H - 90, footer, SMALL, mix(MUTED, INK, 0.3))


def heading_lines(heading):
    from engine_short import wrap
    return wrap(Pen(), heading, HEAD, W - 140)
