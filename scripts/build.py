"""Generate the SVGs for the mowfxy profile README.

The banner is a short looping film in Clem's ink: an ivory pen line that wanders a little and boils on twos, one
colour spot per shot, poses that snap with a small overshoot. It is plain SVG + CSS, so GitHub plays it in an <img>.
The project cards are still pictures.

    pip install fonttools brotli
    python3 scripts/build.py      # CLEM=../clem KERN=../kern to point at the repos the pictures come from
"""
import base64, io, math, os, re
from fontTools import subset
from fontTools.ttLib import TTFont


HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets")
CLEM = os.environ.get("CLEM", os.path.join(HERE, "../../clem"))
KERN = os.environ.get("KERN", os.path.join(HERE, "../../kern"))
FONTS = os.environ.get("MOWAFY_FONTS", os.path.join(CLEM, "public/fonts"))

BG, CARD, RULE = "#141413", "#1a1a18", "#2b2b28"
INK, SOFT, MUTE = "#f0efeb", "#b5b4ad", "#85847e"
BLUE = "#6a9bcc"
LINE, FINE, THIN = 3.6, 3.0, 2.2
TAU = math.pi * 2


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def font_face(family, file, text):
    f = TTFont(os.path.join(FONTS, file))
    o = subset.Options()
    o.flavor, o.layout_features, o.name_IDs, o.hinting = "woff2", ["kern", "liga"], [], False
    s = subset.Subsetter(o)
    s.populate(text=text + " ")
    s.subset(f)
    buf = io.BytesIO()
    f.flavor = "woff2"
    f.save(buf)
    return (f"@font-face{{font-family:{family};src:url(data:font/woff2;base64,"
            f"{base64.b64encode(buf.getvalue()).decode()}) format('woff2')}}")


# ------------------------------------------------------------------ the pen (after Clem's vectorFilm)
SEED = [0]


def spline(pts, closed):
    n = len(pts)
    if n < 3:
        return pts
    out = []
    for i in range(n if closed else n - 1):
        a = pts[(i - 1) % n if closed else max(0, i - 1)]
        b, c = pts[i], pts[(i + 1) % n]
        d = pts[(i + 2) % n if closed else min(n - 1, i + 2)]
        sub = 4 if COMPACT[0] else 8
        for j in range(sub):
            t = j / sub
            t2, t3 = t * t, t * t * t
            out.append(tuple(.5 * (2 * b[k] + (-a[k] + c[k]) * t + (2 * a[k] - 5 * b[k] + 4 * c[k] - d[k]) * t2
                                   + (-a[k] + 3 * b[k] - 3 * c[k] + d[k]) * t3) for k in (0, 1)))
    if not closed:
        out.append(pts[-1])
    return out


def densify(pts, closed, step=8):
    out, n = [], len(pts)
    for i in range(n if closed else n - 1):
        a, b = pts[i], pts[(i + 1) % n]
        k = max(1, round(math.dist(a, b) / step))
        out += [(a[0] + (b[0] - a[0]) * j / k, a[1] + (b[1] - a[1]) * j / k) for j in range(k)]
    if not closed:
        out.append(pts[-1])
    return out


def hand(pts, s, boil):
    """A slow, low wander of about a pixel, different for every line and for each of three drawings."""
    f, A = s * 2.39 + boil * 1.9, 1.2
    return [(x + A * (.7 * math.sin(y * .031 + f) + .3 * math.sin(y * .083 + x * .021 + f * 1.7)),
             y + A * (.7 * math.sin(x * .029 + f * 1.3) + .3 * math.sin(x * .077 - y * .019 + f * 2.1))) for x, y in pts]


COMPACT = [False]


def path_d(pts, close=False):
    if COMPACT[0]:
        return "M" + "L".join(f"{x:.0f} {y:.0f}" for x, y in pts) + ("Z" if close else "")
    return "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + ("Z" if close else "")


def draw(pts, boil, fill=None, w=LINE, smooth=False, closed=False, color=INK):
    s = SEED[0]
    SEED[0] += 1
    tr = hand(spline(pts, closed) if smooth else densify(pts, closed, 14 if COMPACT[0] else 8), s, boil)
    out = ""
    if fill and closed:
        out += f'<path d="{path_d([(x + .9, y + .7) for x, y in tr], True)}" fill="{fill}"/>'
    if w:
        line = tr
        if closed and len(tr) > 4:
            # one stroke that starts somewhere along the shape, drifts a touch and just meets its start again
            L = len(tr)
            st = int(((s * .618) % 1) * L)
            r = tr[st:] + tr[:st]
            a = s * 1.7
            dx, dy = math.cos(a) * 1.4, math.sin(a) * 1.4
            line = [(x + dx * i / L, y + dy * i / L) for i, (x, y) in enumerate(r + r[:3])]
        if COMPACT[0]:
            c = "" if color == INK else f' stroke="{color}"'
            out += f'<path class="L" d="{path_d(line)}" stroke-width="{w}"{c}/>'
        else:
            out += (f'<path d="{path_d(line)}" fill="none" stroke="{color}" stroke-width="{w}" '
                    f'stroke-linecap="round" stroke-linejoin="round" pathLength="1"/>')
    return out


def arc(cx, cy, rx, ry, a0, a1, steps=36):
    return [(cx + math.cos(a0 + (a1 - a0) * i / steps) * rx, cy + math.sin(a0 + (a1 - a0) * i / steps) * ry)
            for i in range(steps + 1)]


def ellipse(cx, cy, rx, ry=None):
    return arc(cx, cy, rx, ry or rx, 0, TAU, 40)[:-1]


def rounded(x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    return (arc(x + w - r, y + r, r, r, -math.pi / 2, 0, 6) + arc(x + w - r, y + h - r, r, r, 0, math.pi / 2, 6)
            + arc(x + r, y + h - r, r, r, math.pi / 2, math.pi, 6) + arc(x + r, y + r, r, r, math.pi, math.pi * 1.5, 6))


def inside(poly, p):
    x, y = p
    c, j = False, len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            c = not c
        j = i
    return c


def stripes(poly, a, gap):
    """Thin parallel lines laid over a colour spot, clipped to it."""
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    R = max(math.dist(p, (cx, cy)) for p in poly) + 4
    ux, uy = math.cos(a), math.sin(a)
    vx, vy = -uy, ux
    segs, o = [], -R + gap / 2
    while o <= R:
        run = []
        for i in range(121):
            t = -R + 2 * R * i / 120
            p = (cx + vx * o + ux * t, cy + vy * o + uy * t)
            if inside(poly, p):
                run.append(p)
            else:
                if len(run) > 2:
                    segs.append((run[1], run[-2]))
                run = []
        if len(run) > 2:
            segs.append((run[1], run[-2]))
        o += gap
    return segs


# ------------------------------------------------------------------ ASCII (after Clem's AsciiField)
CHARS = " .,:'`-~=+*^/\\_o"
ASH = "#5d5c57"   # ASCII in the dark film
PAPER_ASH = "#c4c1b6"


def hsh(a, b):
    v = math.sin(a * 127.1 + b * 311.7) * 43758.5453
    return v - math.floor(v)


def rows_text(rows, x, y, size, lh, fill, opacity=1, cls=""):
    """Rows of ASCII as one <text>, one <tspan> per row, spaces kept."""
    sp = []
    for i, r in enumerate(rows):
        for m in re.finditer(r"\S+(?: {1,9}\S+)*", r):
            sp.append(f'<tspan x="{x + m.start() * size * .6:.1f}" y="{y + i * lh:.1f}">{esc(m.group())}</tspan>')
    if not sp:
        return ""
    o = f' opacity="{opacity}"' if opacity < 1 else ""
    c = f' class="{cls}"' if cls else ""
    return f'<text{c} class="mono" font-size="{size}" fill="{fill}"{o} xml:space="preserve">{"".join(sp)}</text>'


RIDGE = [(0, .9), (.05, .86), (.09, .88), (.16, .78), (.2, .8), (.25, .72), (.3, .79), (.34, .77), (.4, .86),
         (.46, .83), (.52, .88), (.58, .79), (.62, .81), (.68, .7), (.73, .77), (.77, .75), (.83, .8), (.9, .76),
         (.95, .84), (1, .82)]


def ridge_y(x):
    for (x0, y0), (x1, y1) in zip(RIDGE, RIDGE[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0), (y1 - y0) / (x1 - x0)
    return RIDGE[-1][1], 0


def mountains(cols, rows, top=.0, k=0, stars=True):
    """Clem's ASCII range: a ridge line of ^ / \\ over a scatter of dots, and a few stars above."""
    out = []
    for j in range(rows):
        line = ""
        for i in range(cols):
            x = i / (cols - 1)
            ry, sl = ridge_y(x)
            yy = top + (1 - top) * j / (rows - 1)
            ry = top + (1 - top) * (ry - .55) / .45
            if abs(yy - ry) < .5 / rows:
                line += "^" if abs(sl) < .4 else ("/" if sl < 0 else "\\")
            elif yy > ry:
                line += ".:,'`-"[int(hsh(i, j) * 6)] if hsh(i * 5, j * 9) < .35 else " "
            elif stars and hsh(i * 11 + k * 3, j * 17) < .012:
                line += "*" if hsh(i, j + k) < .3 else "."
            else:
                line += " "
        out.append(line)
    return out


# ------------------------------------------------------------------ the film: ink against ASCII
# Drawn frame by frame at 12 fps, like Clem's films: every frame is a fresh drawing, so the ink boils and the
# characters flicker on their own. Each frame is shown for one twelfth of a second by a shared CSS step animation.
FPS, T = 12, 12.0
FW, FH = 1000, 420
CS, CW_, LH = 14, 8.4, 16.8          # ASCII cell: font size, advance, line height
COLS, ROWS = 119, 25
NAME = "Mohamed Mowafy"


def ease_out(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def snap(x):
    x = max(0.0, min(1.0, x))
    c = 1.7
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def partial(pts, k):
    """The first k (0–1) of a polyline, by length: the pen still drawing it."""
    if k >= 1:
        return pts
    if k <= 0 or len(pts) < 2:
        return []
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    left = sum(seg) * k
    out = [pts[0]]
    for i, s in enumerate(seg):
        if left >= s:
            out.append(pts[i + 1]); left -= s
        else:
            t = left / s if s else 0
            out.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t))
            break
    return out


class Grid:
    """One frame of ASCII: a character and a colour per cell."""

    def __init__(self):
        self.c = {}

    def put(self, x, y, ch, col="a"):
        i, j = int(round((x - 4) / CW_)), int(round((y - 4) / LH))
        if 0 <= i < COLS and 0 <= j < ROWS and ch != " ":
            self.c[(i, j)] = (ch, col)

    def clear(self, pred):
        for key in [k for k in self.c if pred(4 + k[0] * CW_, 4 + k[1] * LH)]:
            del self.c[key]

    def svg(self):
        fills = {"a": "#8f8e86", "i": INK, "b": BLUE, "s": SAND}
        out = []
        for col, fill in fills.items():
            rows = []
            for j in range(ROWS):
                rows.append("".join(self.c.get((i, j), (" ", ""))[0] if self.c.get((i, j), (" ", ""))[1] == col else " "
                                    for i in range(COLS)).rstrip())
            out.append(rows_text(rows, 4 - CW_ / 2 + 4.2 - 4.2, 4 + LH * .35, CS, LH, fill))
        return "".join(out)


def dirch(a):
    """A character that points along angle a."""
    a = a % math.pi
    return "-" if a < math.pi / 8 or a > 7 * math.pi / 8 else ("\\" if a < 3 * math.pi / 8 else ("|" if a < 5 * math.pi / 8 else "/"))


# ---------------- ASCII moves
def rain(g, t, dens=1.0, col="a", head="i"):
    for i in range(COLS):
        if hsh(i, 1) > dens:
            continue
        v = 10 + hsh(i, 2) * 16
        hy = (t * v + hsh(i, 3) * 60) % (ROWS + 14) - 4
        L = 5 + int(hsh(i, 4) * 8)
        for k in range(L):
            j = int(hy) - k
            if 0 <= j < ROWS:
                ch = CHARS[1 + int(hsh(i * 3 + j, int(t * 12) + k) * 15)]
                g.put(4 + i * CW_, 4 + j * LH, ch, head if k == 0 else col)


def burst(g, cx, cy, age, n=60, speed=520, col="i", seed=0):
    """Characters thrown out from a point, each pointing the way it flies."""
    for p in range(n):
        a = TAU * hsh(p, seed + 5)
        sp = speed * (.35 + .65 * hsh(p, seed + 6))
        r = sp * age * (1 - .35 * age)
        if age > .9 * hsh(p, seed + 7) + .4:
            continue
        g.put(cx + math.cos(a) * r, cy + math.sin(a) * r * .8, dirch(a) if hsh(p, seed + 8) < .6 else "*+o."[p % 4], col)


def ring(g, cx, cy, r, col="a", ch=None):
    n = max(8, int(r * .5))
    for p in range(n):
        a = TAU * p / n
        g.put(cx + math.cos(a) * r, cy + math.sin(a) * r * .9, ch or dirch(a + math.pi / 2), col)


def bolt(g, x0, y0, x1, y1, seed, col="i"):
    pts, n = [], 9
    for k in range(n + 1):
        u = k / n
        off = 0 if k in (0, n) else (hsh(seed, k) - .5) * 90
        pts.append((x0 + (x1 - x0) * u + off, y0 + (y1 - y0) * u))
    for a, b in zip(pts, pts[1:]):
        steps = int(math.dist(a, b) / 9) + 1
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        for s in range(steps):
            g.put(a[0] + (b[0] - a[0]) * s / steps, a[1] + (b[1] - a[1]) * s / steps, dirch(ang), col)
    return pts


def sphere(g, cx, cy, R, rot, col="b", dim="a"):
    for j in range(-int(R / LH) - 1, int(R / LH) + 2):
        for i in range(-int(R / CW_) - 1, int(R / CW_) + 2):
            x, y = i * CW_ / R, j * LH / R
            d = x * x + y * y
            if d > 1:
                continue
            z = math.sqrt(1 - d)
            lon = math.atan2(x, z) + rot
            lat = math.asin(-y)
            shade = max(0, -.5 * x - .4 * y + .75 * z)
            on = abs(math.sin(lon * 3)) < .25 or abs(math.sin(lat * 3)) < .2
            g.put(cx + i * CW_, cy + j * LH, " .:-=+*#%@"[min(9, int((.35 + .65 * shade) * 9))] if on
                  else " .:"[min(2, int(shade * 3))], col if on else dim)


def field(g, pred, t, col="a", dens=.55):
    for j in range(ROWS):
        for i in range(COLS):
            x, y = 4 + i * CW_, 4 + j * LH
            if pred(x, y) and hsh(i * 7 + int(t * 12), j * 3) < dens:
                g.put(x, y, CHARS[1 + int(hsh(i + int(t * 12), j) * 15)], col)


def scramble(s, prog, salt):
    pool = "MOHAMEDWFY@#%&*+=~^/\\<>01"
    return "".join(c if c == " " or hsh(i, 3) < prog * 1.15 - .08 else pool[int(hsh(i, salt) * len(pool))]
                   for i, c in enumerate(s))


# ---------------- ink moves
class Ink:
    def __init__(self, boil):
        self.b, self.out = boil, []

    def line(self, pts, w=LINE, k=1, smooth=False, color=INK):
        p = partial(spline(pts, False) if smooth else pts, k)
        if len(p) > 1:
            self.out.append(draw(p, self.b, w=w, color=color))
        else:
            SEED[0] += 1

    def shape(self, pts, w=LINE, fill=None, color=INK, hatch=None):
        self.out.append(draw(pts, self.b, w=w, closed=True, fill=fill, color=color))
        if hatch is not None:
            for p, q in stripes(pts, hatch, 7):
                self.out.append(draw([p, q], self.b, w=THIN, color=color))

    def svg(self):
        return "".join(self.out)


def nib(ink, x, y, a, s=1.0):
    pts = [(0, 0), (-16, -9), (-46, -9), (-46, 9), (-16, 9)]
    c, si = math.cos(a), math.sin(a)
    tr = [(x + (px * c - py * si) * s, y + (px * si + py * c) * s) for px, py in pts]
    ink.shape(tr, w=FINE, fill=BLUE)
    ink.line([(x, y), (x - 16 * c * s, y - 16 * si * s)], w=THIN)


def splat(ink, cx, cy, r, seed):
    pts = [(cx + math.cos(TAU * k / 14) * r * (.7 + .5 * hsh(seed, k)),
            cy + math.sin(TAU * k / 14) * r * (.7 + .5 * hsh(seed, k))) for k in range(14)]
    ink.out.append(draw(spline(pts, True), ink.b, w=FINE, closed=True, fill=BLUE))
    for p, q in stripes(pts, -.7, 7):
        ink.out.append(draw([p, q], ink.b, w=THIN))


# ---------------- the show: ink and ASCII take turns stealing the frame
INTRO = 7.6


def star(cx, cy, r, n=5, inner=.45, rot=-math.pi / 2):
    return [(cx + math.cos(rot + math.pi * k / n) * (r if k % 2 == 0 else r * inner),
             cy + math.sin(rot + math.pi * k / n) * (r if k % 2 == 0 else r * inner)) for k in range(2 * n)]


def heart(cx, cy, r):
    return [(cx + r * 16 * math.sin(a) ** 3 / 17, cy - r * (13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a)
                                                         - math.cos(4 * a)) / 17) for a in [TAU * k / 40 for k in range(40)]]


def ascii_shape(g, poly, col="i", fill=True, ch="#"):
    xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
    for j in range(int(min(ys) / LH) - 1, int(max(ys) / LH) + 2):
        for i in range(int(min(xs) / CW_) - 1, int(max(xs) / CW_) + 2):
            x, y = 4 + i * CW_, 4 + j * LH
            if inside(poly, (x, y)):
                g.put(x, y, ch if fill else ".", col)


def frame(t):
    """Everything on screen at time t: (ascii svg, ink svg, shake, flash)."""
    SEED[0] = 0
    g, ink = Grid(), Ink(int(t * FPS) // 2 % 3)
    shake, flash, extra = 0.0, False, ""
    cx, cy = FW / 2, FH / 2

    if t < .9:                        # 1 · a dot of ink; a bigger @ beside it; a ring of ink; a bigger ring of ASCII
        u = t
        r = 6 + 60 * snap((u - .05) / .25) + 70 * snap((u - .5) / .2)
        ink.shape(ellipse(cx - 40, cy, max(4, r * .5)), w=LINE, fill=BLUE if u > .5 else INK)
        if u > .2:
            ring(g, cx - 40, cy, r * .5 + 40 + 120 * ease_out((u - .6) / .3), "i", ch=None)
            g.put(cx + 120 - 200 * ease_out((u - .6) / .3), cy, "@", "b")
        if u > .62:
            ring(g, cx - 40, cy, r * .5 + 70 + 200 * ease_out((u - .62) / .28), "a")

    elif t < 1.8:                     # 2 · an ink bulb lights; an ASCII sun rises behind it, brighter and bigger
        u = t - .9
        R = 170 * snap((u - .3) / .3)
        if R > 5:
            for p in range(90):
                a = TAU * p / 90 + u * 2
                for q in range(3):
                    rr = R + 20 + q * 22 + 10 * math.sin(p * 1.7 + u * 20)
                    if hsh(p, q) < .7:
                        g.put(cx + 140 + math.cos(a) * rr, cy + math.sin(a) * rr * .85, dirch(a), "s" if q == 0 else "a")
            sphere(g, cx + 140, cy, R * .7, u * 3, col="s", dim="a")
        glass = [(cx - 172, cy + 40)] + arc(cx - 150, cy - 30, 62, 62, math.pi * .62, math.pi * 2.38, 40) + [(cx - 128, cy + 40)]
        lit = u > .2
        ink.shape(glass, w=LINE, fill=BLUE if lit else None, hatch=-.6 if lit else None)
        ink.shape(rounded(cx - 174, cy + 40, 48, 38, 8), w=FINE)
        if lit:
            for k in range(7):
                a = math.pi * (1 + k / 6)
                rr = 80 + 30 * snap((u - .2 - k * .03) / .2)
                ink.line([(cx - 150 + math.cos(a) * 78, cy - 30 + math.sin(a) * 78),
                          (cx - 150 + math.cos(a) * rr, cy - 30 + math.sin(a) * rr)], w=FINE)

    elif t < 2.8:                     # 3 · an ink wave crosses the frame; ASCII bars jump up through it
        u = t - 1.8
        k = ease_out(u / .4)
        pts = [(x, cy + 70 * math.sin(x * .022 - u * 12)) for x in range(20, int(20 + 960 * k), 12)]
        if len(pts) > 1:
            ink.line(pts, w=LINE + .5, smooth=True)
            ink.line([(x, y + 24) for x, y in pts], w=THIN, smooth=True, color=BLUE)
        if u > .3:
            for i in range(0, COLS, 2):
                h = (ROWS * .9) * (.15 + .85 * abs(math.sin(i * .37 + u * 9) * math.sin(i * .11 - u * 5)))
                h *= ease_out((u - .3) / .25)
                for j in range(int(h)):
                    g.put(4 + i * CW_, FH - 8 - j * LH, "|" if j < h - 1 else "^", "b" if j >= h - 2 else "a")
                    if j % 2 == 0:
                        g.put(4 + (i + 1) * CW_, FH - 8 - j * LH, ":", "a")

    elif t < 3.8:                     # 4 · an ASCII planet; the pen gives it rings and a moon and takes the eye back
        u = t - 2.8
        R = 120 * snap(u / .2)
        if R > 4:
            sphere(g, cx, cy, R, u * 5)
        for k in range(3):
            kk = ease_out((u - .25 - k * .08) / .22)
            if kk > 0:
                ink.line(arc(cx, cy, 190 + k * 30, 46 + k * 12, -.4, -.4 + TAU * kk, 52), w=FINE + (1 if k == 0 else 0),
                         color=BLUE if k == 1 else INK)
        if u > .5:
            a = (u - .5) * 7
            ink.shape(ellipse(cx + math.cos(a) * 250, cy + math.sin(a) * 64, 18), w=FINE, fill=BLUE, hatch=.7)
        rain(g, t, dens=.12)

    elif t < 4.9:                     # 5 · rapid turns: each thing drawn in ink, then answered in ASCII
        u = t - 3.8
        beat = int(u / .22)
        side = beat % 2
        shapes = [lambda x, y, r: star(x, y, r), lambda x, y, r: heart(x, y, r * .9),
                  lambda x, y, r: rounded(x - r, y - r * .7, r * 2, r * 1.4, r * .3),
                  lambda x, y, r: [(x - r, y - r * .6), (x + r * .2, y - r * .6), (x + r * .2, y - r),
                                   (x + r, y), (x + r * .2, y + r), (x + r * .2, y + r * .6), (x - r, y + r * .6)],
                  lambda x, y, r: ellipse(x, y, r, r * .6)]
        sh = shapes[beat % len(shapes)]
        uu = (u % .22) / .22
        r = 90 + 40 * snap(uu / .4)
        px = cx + (-200 if side == 0 else 200)
        poly = sh(px, cy, r)
        if side == 0:
            ink.shape(poly, w=LINE + 1, fill=BLUE if beat % 4 == 0 else None, hatch=-.7 if beat % 4 == 0 else None)
            prev = shapes[(beat - 1) % len(shapes)](cx + 200, cy, 80) if beat else None
            if prev:
                ascii_shape(g, prev, "a", ch="+")
        else:
            ascii_shape(g, poly, "i" if beat % 3 else "b")
            ink.shape(shapes[(beat - 1) % len(shapes)](cx - 200, cy, 80), w=THIN)
        shake = 3 if uu < .2 else 0

    elif t < 5.9:                     # 6 · both claim the screen: hatching from the left, characters from the right
        u = t - 4.9
        edge = cx + 230 * math.sin(u * 8) * (1 - u * .4)
        poly = [(10, 10), (edge, 10), (edge + 30 * math.sin(u * 30), FH / 2), (edge, FH - 10), (10, FH - 10)]
        for p, q in stripes(poly, -.8, 20):
            ink.line([p, q], w=THIN)
        ink.line([(edge, 10), (edge + 30 * math.sin(u * 30), FH / 2), (edge, FH - 10)], w=LINE + 1, color=BLUE)
        field(g, lambda x, y: x > edge + 18, t, dens=.38)

    elif t < 6.9:                     # 7 · both race to write the name
        u = t - 5.9
        extra += (f'<text class="mono" x="{cx}" y="{cy - 40}" font-size="46" fill="{"#8f8e86"}" text-anchor="middle" '
                  f'xml:space="preserve">{esc(scramble(NAME, u / .8, int(u * 24)))}</text>')
        w = 620 * ease_out(u / .8)
        extra += (f'<clipPath id="wc{int(t*FPS)}"><rect x="{cx - 310}" y="{cy}" width="{w:.0f}" height="110"/></clipPath>'
                  f'<text x="{cx}" y="{cy + 80}" class="serif" font-size="70" fill="{INK}" text-anchor="middle" '
                  f'clip-path="url(#wc{int(t*FPS)})">{NAME}</text>')
        nx = cx - 310 + w
        nib(ink, nx, cy + 70, -.6, 1.0)
        rain(g, t, dens=.15)

    else:                             # 8 · they merge: a glitch, and the name lands where the still will hold it
        u = t - 6.9
        flash = u < .09
        off = int((1 - ease_out(u / .6)) * 40)
        for s_ in range(6):
            y0 = cy - 60 + s_ * 18
            dx = (hsh(s_, int(u * 24)) - .5) * 2 * off
            extra += (f'<clipPath id="gl{int(t*FPS)}{s_}"><rect x="0" y="{y0}" width="{FW}" height="18"/></clipPath>'
                      f'<text x="{cx + dx:.1f}" y="{cy + 22}" class="serif" font-size="78" fill="{INK if s_ % 3 else BLUE}" '
                      f'text-anchor="middle" clip-path="url(#gl{int(t*FPS)}{s_})">{NAME}</text>')
        burst(g, cx, cy, u, n=60, speed=600, col="a", seed=77)
        shake = 5 * max(0, 1 - u * 3)
    sx = (hsh(int(t * FPS), 1) - .5) * 2 * shake
    sy = (hsh(int(t * FPS), 2) - .5) * 2 * shake
    return g.svg(), ink.svg() + extra, (sx, sy), flash


def name_ascii(seed=0):
    """The name rasterised in Mowafy Serif and set again in characters."""
    from PIL import Image as Im, ImageDraw, ImageFont
    f = TTFont(os.path.join(FONTS, "MowafySerif-Regular.woff2"))
    f.flavor = None
    buf = io.BytesIO(); f.save(buf); buf.seek(0)
    cols, rows, sx, sy = 150, 18, 3, 5
    size = 100
    while ImageFont.truetype(io.BytesIO(buf.getvalue()), size).getlength(NAME) > cols * sx * .97:
        size -= 1
    font = ImageFont.truetype(buf, size)
    im = Im.new("L", (cols * sx, rows * sy), 0)
    ImageDraw.Draw(im).text((cols * sx / 2, rows * sy * .52), NAME, font=font, fill=255, anchor="mm", stroke_width=1, stroke_fill=255)
    px = im.load()
    out = []
    for j in range(rows):
        line = ""
        for i in range(cols):
            v = sum(px[i * sx + a, j * sy + b] for a in range(sx) for b in range(sy)) / (255 * sx * sy)
            line += (" .:-=+*#%@"[min(9, int(v * 12))] if v > .05 else
                     ("." if hsh(i + seed * 31, j) < .03 else " "))
        out.append(line)
    return out, cols, rows


def film():
    n = int(INTRO * FPS)
    css, groups = [], []
    COMPACT[0] = True
    for i in range(n):
        t = i / FPS
        a, ink, (sx, sy), flash = frame(t)
        body = a + ink
        if flash:
            body = f'<rect width="{FW}" height="{FH}" fill="{INK}"/><g style="filter:invert(1)">{body}</g>'
        if sx or sy:
            body = f'<g transform="translate({sx:.1f} {sy:.1f})">{body}</g>'
        css.append(f".q{i}{{animation:fr {1 / FPS:.4f}s step-end {t:.4f}s 1}}")
        groups.append(f'<g class="fi q{i}">{body}</g>')
    css.append("@keyframes fr{0%{visibility:visible}100%{visibility:hidden}}")

    # ---------------- the still: the name holds for good, and every few seconds glitches into its ASCII self
    cx, cy = FW / 2, FH / 2
    SEED[0] = 500
    under = [(310 + 380 * j / 12, cy + 50 + math.sin(j * 1.1) * 2.4) for j in range(13)]
    boil = "".join(f'<g class="b b{b}">{draw(spline(under, False), b, w=FINE, color=BLUE)}</g>'
                   for b in range(3) if not SEED.__setitem__(0, 500))
    COMPACT[0] = False
    mt = mountains(COLS, 7, top=0, k=0)
    sky = rows_text(mt, 4, FH - 7 * LH + 8, CS, LH, "#5d5c57")
    art, acols, arows = name_ascii(0)
    art2, _, _ = name_ascii(1)
    acs = 7.6   # ASCII-art cell: a little larger than the ink name, so the switch reads
    ax = cx - acols * acs * .6 / 2
    ay = cy - arows * acs / 2 + acs * .2
    art_svg = (f'<g class="ga">{rows_text(art, ax, ay, acs, acs, INK)}</g>'
               f'<g class="ga2">{rows_text(art2, ax + 3, ay, acs, acs, BLUE, .45)}</g>')
    slices = "".join(
        f'<clipPath id="s{k}"><rect x="0" y="{cy - 62 + k * 16}" width="{FW}" height="16"/></clipPath>'
        f'<text class="serif gs gs{k}" x="{cx}" y="{cy + 22}" font-size="78" fill="{BLUE if k % 2 else INK}" '
        f'text-anchor="middle" clip-path="url(#s{k})">{NAME}</text>' for k in range(6))
    P, D = 6.0, INTRO + 2.4   # glitch every P seconds, the first one D seconds in
    css.append(
        f"@keyframes inh{{from{{opacity:0}}to{{opacity:1}}}}.hold{{animation:inh .01s linear {INTRO - .02:.2f}s both}}"
        # the ink name: gone while the ASCII art shows
        f"@keyframes nm{{0%,30%{{opacity:1}}31%,72%{{opacity:0}}73%,100%{{opacity:1}}}}"
        f".nm{{animation:nm {P * .25:.2f}s steps(1) {D}s infinite;animation-duration:{P}s}}"
        # the ASCII art: in for most of a second, flickering between two drawings
        f"@keyframes ga{{0%,31%{{opacity:0}}32%,71%{{opacity:1}}72%,100%{{opacity:0}}}}"
        f".ga,.ga2{{opacity:0;animation:ga {P}s steps(1) {D}s infinite}}"
        f"@keyframes gf{{0%,49%{{transform:translateX(0)}}50%,100%{{transform:translateX(-3px)}}}}"
        f".ga2 text{{animation:gf .17s steps(1) infinite}}"
        # torn slices on the way in and out
        + "".join(f"@keyframes gs{k}{{0%,27%{{opacity:0;transform:none}}28%{{opacity:1;transform:translateX({(hsh(k, 1) - .5) * 60:.0f}px)}}"
                  f"30%{{opacity:1;transform:translateX({(hsh(k, 2) - .5) * 90:.0f}px)}}32%,71%{{opacity:0}}"
                  f"72%{{opacity:1;transform:translateX({(hsh(k, 3) - .5) * 80:.0f}px)}}74%,100%{{opacity:0;transform:none}}}}"
                  f".gs{k}{{opacity:0;animation:gs{k} {P}s linear {D}s infinite}}" for k in range(6)))
    # scale the glitch keyframes: the whole cycle is P seconds, the glitch about 2.4 s of it
    hold = (f'<g class="hold">{sky}'
            f'<text class="serif nm" x="{cx}" y="{cy + 22}" font-size="78" fill="{INK}" text-anchor="middle">{NAME}</text>'
            f'{boil}{art_svg}{slices}</g>')
    mono_t = CHARS + "@#%&*+=~^/\\<>01|█▀▌" + NAME + "MOHAMEDWFY" + " .:-=+*#%@" + "".join(art) + "".join(art2) + "".join(mt)
    css_all = (font_face("MS", "MowafySerif-Regular.woff2", NAME)
               + font_face("JM", "JetBrainsMono.woff2", mono_t)
               + ".serif{font-family:MS,Georgia,serif;letter-spacing:-.5px}"
               + ".mono{font-family:JM,ui-monospace,monospace;white-space:pre}.fi{visibility:hidden}"
               + f".L{{fill:none;stroke:{INK};stroke-linecap:round;stroke-linejoin:round}}"
               + "@keyframes bo{0%{visibility:visible}33.33%,100%{visibility:hidden}}"
               + ".b{animation:bo .5s step-end infinite}.b1{animation-delay:-.3333s}.b2{animation-delay:-.1667s}"
               + "".join(css)
               + "@media (prefers-reduced-motion:reduce){*{animation:none!important}.fi,.b1,.b2,.ga,.ga2,.gs{display:none}}")
    alt = ("Ink drawings and ASCII characters take turns stealing the frame, then the name Mohamed Mowafy stays, "
           "now and then glitching into an ASCII version of itself.")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{FW}" height="{FH}" viewBox="0 0 {FW} {FH}" role="img" '
            f'aria-label="{esc(alt)}"><title>Mohamed Mowafy</title><style>{css_all}</style>'
            f'<defs><clipPath id="stage"><rect width="{FW}" height="{FH}" rx="16"/></clipPath></defs>'
            f'<g clip-path="url(#stage)"><rect width="{FW}" height="{FH}" fill="{BG}"/>{"".join(groups)}{hold}</g></svg>')


# ------------------------------------------------------------------ cards: a designed picture of each project
PAPER, NAVY, SAND, RED = "#f4f2ec", "#20253a", "#c8b48c", "#e0462f"


def clem_art(x, y, w, h):
    """Clem at night-into-morning: its mark and greeting over the ASCII range, a composer drawn in its ink."""
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{PAPER}"/>']
    mt = mountains(73, 9, top=0, k=1)
    out.append(rows_text(mt, x + 2, y + h - 9 * 9.6 + 6, 9, 9.6, PAPER_ASH))
    # sun, hatched, in the ink's hand
    SEED[0] = 900
    sun = ellipse(x + w - 62, y + 44, 15)
    out.append(draw(sun, 0, fill=SAND, closed=True, w=2, color=NAVY)
               + "".join(draw([p, q], 0, w=1.4, color=NAVY) for p, q in stripes(sun, -.7, 5)))
    # the mark: the C and its cursor
    cx, cy, s = x + 96, y + 62, .42
    out.append(f'<g transform="translate({cx - 50 * s:.1f} {cy - 50 * s:.1f}) scale({s})">'
               f'<path d="M72.29 29.93A30 30 0 1 0 72.29 70.07" fill="none" stroke="{NAVY}" stroke-width="13" '
               f'stroke-linecap="round"/><rect x="56" y="40" width="11" height="20" rx="2" fill="{NAVY}"/></g>')
    out.append(f'<text class="serif" x="{cx + 22}" y="{cy + 8}" font-size="23" fill="{NAVY}">Evening, thinker.</text>')
    # the composer, drawn
    SEED[0] = 950
    box = rounded(x + 72, y + 88, w - 144, 38, 12)
    out.append(draw(box, 0, closed=True, w=1.8, color=NAVY))
    out.append(f'<text class="sans" x="{x + 88}" y="{y + 112}" font-size="11" fill="#8a897f">'
               f'why does my op-amp oscillate?</text>')
    for i, op in enumerate((1, .45, .3)):
        out.append(f'<rect x="{x + w - 116 + i * 10:.1f}" y="{y + 100}" width="5" height="10" rx="1" '
                   f'fill="{NAVY}" opacity="{op}"/>')
    return "".join(out), "Evening, thinker.", "why does my op-amp oscillate?", "".join(mt)


def kern_art(x, y, w, h):
    """A kerning spec sheet: K and n set tight, their side-bearings in red and the pair's value."""
    size, upm = 128, 1000
    k_ = size / upm
    kern = -64
    kadv, kxmax, nxmin, nxmax = 818, 809, 16, 653
    total = (kadv + kern + nxmax) * k_
    bx = x + (w - total) / 2
    base = y + h * .74
    nx = bx + (kadv + kern) * k_
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#121214"/>']
    for yy, dash in ((base, ""), (base - 540 * k_, ' stroke-dasharray="3 4"'), (base - 720 * k_, ' stroke-dasharray="3 4"')):
        out.append(f'<line x1="{x}" y1="{yy:.1f}" x2="{x + w}" y2="{yy:.1f}" stroke="#34343a"{dash}/>')
    out.append(f'<text class="serifb" x="{bx:.1f}" y="{base:.1f}" font-size="{size}" fill="{INK}">K</text>')
    out.append(f'<text class="serifb" x="{nx:.1f}" y="{base:.1f}" font-size="{size}" fill="{INK}">n</text>')
    l1, l2 = bx + kadv * k_, nx  # where n would sit, and where kerning puts it
    for lx in (l1, l2):
        out.append(f'<line x1="{lx:.1f}" y1="{base - 760 * k_:.1f}" x2="{lx:.1f}" y2="{base + 14:.1f}" '
                   f'stroke="{RED}" stroke-width="1.2"/>')
    mid = (l1 + l2) / 2
    out.append(f'<path d="M{min(l1, l2):.1f} {base + 22:.1f}H{max(l1, l2):.1f}" stroke="{RED}" stroke-width="1.2"/>')
    out.append(f'<text class="mono" x="{mid:.1f}" y="{base + 40:.1f}" font-size="11" fill="{RED}" '
               f'text-anchor="middle">{kern}</text>')
    labels = [("K/n", x + 14, y + 22, "start"), ("x-height", x + w - 14, base - 540 * k_ - 5, "end"),
              ("cap", x + w - 14, base - 720 * k_ - 5, "end"), ("baseline", x + w - 14, base - 5, "end")]
    for t, lx, ly, an in labels:
        out.append(f'<text class="mono" x="{lx:.1f}" y="{ly:.1f}" font-size="9.5" fill="#6d6d74" '
                   f'text-anchor="{an}">{t}</text>')
    return "".join(out), "Kn", "".join(l[0] for l in labels) + str(kern)


def card(name, desc, art):
    W, H = 423, 268
    cw, ch = W - 10, H - 8
    pw, ph = cw - 20, 170
    body, serif_t, sans_t, mono_t = art(15, 10, pw, ph)
    css = (font_face("MS", "MowafySerif-Regular.woff2", name + serif_t)
           + font_face("MN", "MowafySans-Regular.woff2", desc + sans_t + "↗")
           + (font_face("MB", "MowafySerif-Bold.woff2", "Kn") if name == "Kern" else "")
           + font_face("JM", "JetBrainsMono.woff2", mono_t)
           + ".serif{font-family:MS,Georgia,serif}.serifb{font-family:MB,Georgia,serif;font-weight:700}"
           + ".sans{font-family:MN,system-ui,sans-serif}.mono{font-family:JM,ui-monospace,monospace;white-space:pre}")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="{esc(name)}: {esc(desc)}"><title>{esc(name)}</title><style>{css}</style>'
            f'<defs><clipPath id="p"><rect x="15" y="10" width="{pw}" height="{ph}" rx="10"/></clipPath></defs>'
            f'<rect x="5.5" y=".5" width="{cw-1}" height="{ch-1}" rx="14" fill="{CARD}" stroke="{RULE}"/>'
            f'<g clip-path="url(#p)">{body}</g>'
            f'<rect x="15.5" y="10.5" width="{pw-1}" height="{ph-1}" rx="10" fill="none" stroke="{RULE}"/>'
            f'<text class="serif" x="24" y="{ph+48}" font-size="26" fill="{INK}">{esc(name)}</text>'
            f'<text class="sans" x="{cw-6}" y="{ph+46}" font-size="18" fill="{MUTE}" text-anchor="end">↗</text>'
            f'<text class="sans" x="24" y="{ph+72}" font-size="14" fill="{SOFT}">{esc(desc)}</text></svg>')


def clem_art_wrap(x, y, w, h):
    body, serif_t, sans_t, mono_t = clem_art(x, y, w, h)
    return body, serif_t, sans_t, mono_t


def kern_art_wrap(x, y, w, h):
    body, serif_t, mono_t = kern_art(x, y, w, h)
    return body, "", "", mono_t


CARDS = [
    dict(slug="clem", name="Clem", desc="A calm, local-first workspace.", url="https://github.com/mowfxy/clem",
         art=clem_art_wrap),
    dict(slug="kern", name="Kern", desc="Design taste for coding agents.", url="https://github.com/mowfxy/kern",
         art=kern_art_wrap),
]


def readme():
    cards = "".join(f'<a href="{c["url"]}"><img src="assets/card-{c["slug"]}.svg" width="423" '
                    f'alt="{c["name"]}: {c["desc"]}"></a>' for c in CARDS)
    return "\n".join([
        '<a href="https://mohamedmowafy.com"><img src="assets/film.svg" width="100%" alt="Ink and ASCII take turns '
        'stealing the frame, then the name Mohamed Mowafy stays."></a>',
        "",
        f'<p align="center">{cards}</p>',
        "",
        '<p align="center"><a href="https://mohamedmowafy.com">mohamedmowafy.com</a></p>',
        "",
        "<!-- Generated by scripts/build.py. Set in Mowafy Serif, Mowafy Sans and JetBrains Mono. -->",
        "",
    ])


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for x in os.listdir(OUT):
        os.remove(os.path.join(OUT, x))
    files = {"film.svg": film()}
    for c in CARDS:
        files[f"card-{c['slug']}.svg"] = card(c["name"], c["desc"], c["art"])
    for n, content in files.items():
        with open(os.path.join(OUT, n), "w") as fh:
            fh.write(content)
        print(f"{n:20} {len(content) / 1024:7.1f} KB")
    with open(os.path.join(HERE, "..", "README.md"), "w") as fh:
        fh.write(readme())
