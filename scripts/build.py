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


# ---------------- the fight, beat by beat
def frame(t):
    """Everything on screen at time t: (ascii svg, ink svg, shake, flash)."""
    SEED[0] = 0
    g, ink = Grid(), Ink(int(t * FPS) // 2 % 3)
    shake, flash, extra = 0.0, False, ""
    cx, cy = FW / 2, FH / 2

    if t < 1.0:                       # 1 · ASCII rain; an ink slash cuts it in two
        rain(g, t, dens=.55)
        k = ease_out((t - .35) / .2)
        a, b = (60, 20), (940, 400)
        if k > 0:
            ink.line([a, b], w=LINE + 1.5, k=k)
            off = (t - .55) * 260 if t > .55 else 0
            g.clear(lambda x, y: abs((y - a[1]) * (b[0] - a[0]) - (x - a[0]) * (b[1] - a[1])) / 960 < 14 + off)
            if t > .55:
                burst(g, 500, 210, t - .55, n=40, speed=600, seed=3)
                shake = 8 * (1 - (t - .55) / .45)

    elif t < 2.0:                     # 2 · an ink shield; an ASCII swarm breaks on it
        u = t - 1.0
        R = 92
        ink.shape(ellipse(cx, cy, R, R * .92), w=LINE + 1, fill=BLUE if u > .45 else None,
                  hatch=-.7 if u > .45 else None) if u > .12 else ink.line(arc(cx, cy, R, R * .92, 0, TAU * ease_out(u / .12), 40))
        for p in range(140):
            a = TAU * hsh(p, 11)
            r0 = 520 + 200 * hsh(p, 12)
            v = 900 + 300 * hsh(p, 13)
            r = r0 - v * u
            if r < R + 6:
                r = R + 6 + (R + 6 - r) * .6
            g.put(cx + math.cos(a) * r, cy + math.sin(a) * r * .9, dirch(a) if r > R + 20 else "*", "i" if p % 3 else "b")
        if u > .45:
            ring(g, cx, cy, R + 14 + (u - .45) * 420, "b")
            shake = 6 * max(0, 1 - (u - .45) * 3)

    elif t < 3.0:                     # 3 · ASCII lightning; the shield shatters
        u = t - 2.0
        R = 92
        if u < .3:
            ink.shape(ellipse(cx, cy, R, R * .92), w=LINE + 1, fill=BLUE, hatch=-.7)
            for s in range(3):
                if u > s * .08:
                    bolt(g, 200 + s * 300, 0, cx + (s - 1) * 40, cy - R * .8, 31 + s + int(u * 24), "i")
            flash = 0.12 < u < .2
        else:
            v = u - .3
            for p in range(16):                       # shards fly out and spin
                a0, a1 = TAU * p / 16, TAU * (p + 1) / 16
                m = (a0 + a1) / 2
                d = 600 * v * (.6 + .6 * hsh(p, 21))
                rot = (hsh(p, 22) - .5) * 8 * v
                pts = [(cx + math.cos(m) * d + math.cos(a + rot) * R, cy + math.sin(m) * d + math.sin(a + rot) * R * .92)
                       for a in (a0, (a0 + a1) / 2, a1)]
                ink.line(pts, w=LINE)
            burst(g, cx, cy, v, n=90, speed=700, col="b", seed=9)
            rain(g, t, dens=min(.4, .2 + v))
            shake = 10 * max(0, 1 - v * 2.5)

    elif t < 4.2:                     # 4 · ink waves against ASCII waves; they meet in the middle
        u = t - 3.0
        front = min(cx, 80 + 900 * u)
        for w_ in range(3):
            y0 = 120 + w_ * 90
            pts = [(x, y0 + 26 * math.sin(x * .035 - u * 18 + w_)) for x in range(20, int(front), 12)]
            if len(pts) > 1:
                ink.line(pts, w=FINE, smooth=True, color=BLUE if w_ == 1 else INK)
            for x in range(int(FW - 20), int(max(cx, FW - 80 - 900 * u)), -9):
                y = y0 + 26 * math.sin(x * .035 + u * 18 + w_ + 1)
                g.put(x, y, "~", "a" if w_ != 1 else "b")
                g.put(x, y + 17, ".", "a")
        if u > .5:
            v = u - .5
            burst(g, cx, cy, v, n=110, speed=760, col="i", seed=17)
            burst(g, cx, cy, v * .8, n=60, speed=500, col="b", seed=23)
            for s in range(5):
                if v > s * .07:
                    splat(ink, cx + math.cos(s * 2.4) * (120 + 260 * min(1, v * 2)),
                          cy + math.sin(s * 2.4) * (80 + 120 * min(1, v * 2)), 16 + 6 * hsh(s, 1), s)
            flash = v < .09
            shake = 12 * max(0, 1 - v * 2)

    elif t < 5.4:                     # 5 · an ASCII world spins up; the pen cages it, it breaks out
        u = t - 4.2
        R = 135 * snap(u / .25)
        if R > 4:
            sphere(g, cx, cy, R, u * 6)
        for k in range(3):
            kk = ease_out((u - .25 - k * .1) / .2)
            if kk > 0 and u < .85:
                ink.line(arc(cx, cy, 150 + k * 22, 44 + k * 10, -.3 + k, -.3 + k + TAU * kk, 48), w=FINE)
        if u > .5:
            bars = ease_out((u - .5) / .15)
            for b_ in range(7):
                x = cx - 135 + b_ * 45
                if u < .85:
                    ink.line([(x, 40), (x, 40 + 340 * bars)], w=FINE)
        if u >= .85:
            v = u - .85
            for b_ in range(7):
                x = cx - 135 + b_ * 45
                a = (b_ - 3) * .5 * v * 6
                ink.line([(x + v * (b_ - 3) * 300, 40 - v * 200 * abs(b_ - 3)),
                          (x + v * (b_ - 3) * 300 + math.sin(a) * 340, 40 - v * 200 * abs(b_ - 3) + math.cos(a) * 340)], w=FINE)
            burst(g, cx, cy, v * 1.6, n=80, speed=600, col="b", seed=41)
            shake = 9 * max(0, 1 - v * 3)

    elif t < 6.6:                     # 6 · chase: the pen nib zips around, an ASCII snake on its tail
        u = t - 5.4
        path = lambda s: (cx + 380 * math.sin(s * 2.1), cy + 140 * math.sin(s * 4.2 + .5))
        s = u * 4.5
        trail = [path(s - k * .02) for k in range(40)]
        ink.line(trail[::-1], w=FINE, smooth=True)
        x, y = path(s)
        x2, y2 = path(s + .01)
        nib(ink, x, y, math.atan2(y2 - y, x2 - x), 1.2)
        for k in range(46):
            px, py = path(s - .55 - k * .018)
            g.put(px, py, "@" if k == 0 else "o=*+:~-."[min(7, k // 6)], "i" if k < 4 else ("b" if k < 16 else "a"))
        rain(g, t, dens=.18)

    elif t < 7.6:                     # 7 · tug of war: ink hatching against an ASCII field
        u = t - 6.6
        edge = cx + 260 * math.sin(u * 9) * (1 - u * .3)
        poly = [(10, 10), (edge, 10), (edge + 30 * math.sin(u * 30), FH / 2), (edge, FH - 10), (10, FH - 10)]
        for p, q in stripes(poly, -.8, 22):
            ink.line([p, q], w=THIN)
        ink.line([(edge, 10), (edge + 30 * math.sin(u * 30), FH / 2), (edge, FH - 10)], w=LINE + 1)
        field(g, lambda x, y: x > edge + 18, t, dens=.38)
        for j in range(ROWS):
            g.put(edge + 26, 4 + j * LH, "|" if j % 2 else ":", "b")
        shake = 4 * abs(math.cos(u * 9))

    elif t < 8.6:                     # 8 · fireworks: ink stars against ASCII stars
        u = t - 7.6
        for n_ in range(6):
            t0 = n_ * .14
            if u < t0:
                continue
            v = u - t0
            px = 140 + (n_ * 167) % 720
            py = 90 + (n_ * 97) % 230
            if n_ % 2 == 0:
                rr = 70 * ease_out(v / .3)
                for k in range(10):
                    a = TAU * k / 10 + n_
                    ink.line([(px + math.cos(a) * rr * .35, py + math.sin(a) * rr * .35),
                              (px + math.cos(a) * rr, py + math.sin(a) * rr)], w=FINE,
                             color=BLUE if k % 3 == 0 else INK)
                if v < .12:
                    ink.shape(ellipse(px, py, 8), w=FINE, fill=BLUE)
            else:
                burst(g, px, py, v * .8, n=40, speed=260, col="b" if n_ % 3 else "s", seed=50 + n_)
        rain(g, t, dens=.12)

    elif t < 9.6:                     # 9 · everything is pulled to the middle: ASCII becomes the name
        u = t - 8.6
        k = ease_out(u / .7)
        for p in range(180):
            a = TAU * hsh(p, 61) + u * 3
            r = (520 * hsh(p, 62) + 60) * (1 - k)
            if r > 30:
                g.put(cx + math.cos(a) * r, cy + math.sin(a) * r * .8, CHARS[1 + p % 15], "a" if p % 4 else "b")
        if u < .45:                                # ink strokes rush inward with the characters
            for q in range(12):
                a = TAU * q / 12 + .2
                r1 = 480 * (1 - ease_out(u / .45)) + 60
                ink.line([(cx + math.cos(a) * (r1 + 120), cy + math.sin(a) * (r1 + 120) * .8),
                          (cx + math.cos(a) * r1, cy + math.sin(a) * r1 * .8)], w=FINE, color=BLUE if q % 4 == 0 else INK)
        if u > .35:
            txt = scramble(NAME, (u - .35) / .55, int(u * 24))
            extra += (f'<text class="mono" x="{cx}" y="{cy + 18}" font-size="60" fill="{INK}" text-anchor="middle" '
                      f'xml:space="preserve">{esc(txt)}</text>')
        shake = 3 if u > .6 else 0

    else:                             # 10 · ink takes the name; the ASCII scatters and settles into a skyline
        u = t - 9.6
        if u < .12:
            flash = True
        for m_ in mountains(COLS, 7, top=0, k=int(u * 3) % 2)[:7]:
            pass
        mt = mountains(COLS, 7, top=0, k=int(u * 3) % 2)
        rise = ease_out((u - .4) / .6)
        for j, row in enumerate(mt):
            for i, ch in enumerate(row):
                if ch != " " and hsh(i, j) < rise:
                    g.put(4 + i * CW_, FH - (7 - j) * LH * rise, ch, "a")
        if u < 1.0:
            for p in range(len(NAME)):
                if NAME[p] == " ":
                    continue
                x0 = cx + (p - len(NAME) / 2 + .5) * 36
                a = TAU * hsh(p, 71)
                d = 700 * ease_out(u / .9)
                g.put(x0 + math.cos(a) * d, cy + math.sin(a) * d * .6, NAME[p], "a")
            burst(g, cx, cy, u, n=70, speed=650, col="a", seed=77)
        sc = snap(u / .25)
        extra += (f'<text x="{cx}" y="{cy + 22}" class="serif" font-size="{78 * max(.01, sc):.1f}" fill="{INK}" '
                  f'text-anchor="middle">{NAME}</text>')
        under = [(310 + 380 * j / 12, cy + 50 + math.sin(j * 1.1) * 2.4) for j in range(13)]
        ink.line(under, w=FINE, smooth=True, k=ease_out((u - .25) / .3), color=BLUE)
        for s_ in range(4):                       # a few last ink flecks
            if .2 < u < .7:
                splat(ink, cx + (s_ - 1.5) * 220, cy - 120 + 230 * (s_ % 2), 9 * (1 - (u - .2) * 1.6) + 1, s_ + 90)
        shake = 6 * max(0, 1 - u * 4)

    sx = (hsh(int(t * FPS), 1) - .5) * 2 * shake
    sy = (hsh(int(t * FPS), 2) - .5) * 2 * shake
    return g.svg(), ink.svg() + extra, (sx, sy), flash


def film():
    n = int(T * FPS)
    hold_from = int(10.6 * FPS)          # from here the name just boils: reuse a short cycle of drawings
    css_frames, groups, cache = [], [], {}
    for i in range(n):
        t = i / FPS
        key = i if i < hold_from else hold_from + (i - hold_from) % 6
        cache.setdefault(key, []).append(i)
    COMPACT[0] = True
    for key, idxs in cache.items():
        t = key / FPS
        a, ink, (sx, sy), flash = frame(t)
        body = a + ink
        if flash:
            body = f'<rect width="{FW}" height="{FH}" fill="{INK}"/><g style="filter:invert(1)">{body}</g>'
        if sx or sy:
            body = f'<g transform="translate({sx:.1f} {sy:.1f})">{body}</g>'
        cls = f"q{key}"
        stops = []
        for i in idxs:
            stops.append(f"{i / n * 100:.3f}%{{visibility:visible}}{(i + 1) / n * 100:.3f}%{{visibility:hidden}}")
        css_frames.append(f"@keyframes {cls}{{0%{{visibility:hidden}}{''.join(stops)}100%{{visibility:hidden}}}}"
                          f".{cls}{{animation:{cls} {T}s step-end infinite}}")
        still = ' style="visibility:visible"' if key == hold_from else ""
        groups.append(f'<g class="{cls} fr"{still}>{body}</g>')
    COMPACT[0] = False
    mono = CHARS + "@#%&*+=~^/\\<>01|" + NAME + "MOHAMEDWFY" + "".join(sorted(set(".:,'`-^")))
    css = (font_face("MS", "MowafySerif-Regular.woff2", NAME)
           + font_face("JM", "JetBrainsMono.woff2", mono + " .:-=+*#%@")
           + ".serif{font-family:MS,Georgia,serif;letter-spacing:-.5px}"
           + ".mono{font-family:JM,ui-monospace,monospace;white-space:pre}.fr{visibility:hidden}"
           + f".L{{fill:none;stroke:{INK};stroke-linecap:round;stroke-linejoin:round}}"
           + "".join(css_frames)
           + "@media (prefers-reduced-motion:reduce){*{animation:none!important}}")
    alt = ("A fast animated fight between ink drawings and ASCII characters: a pen slashes through falling "
           "characters, a shield breaks under ASCII lightning, waves collide, a pen nib is chased by a character "
           "snake, and it ends with the name Mohamed Mowafy.")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{FW}" height="{FH}" viewBox="0 0 {FW} {FH}" role="img" '
            f'aria-label="{esc(alt)}"><title>Mohamed Mowafy</title><style>{css}</style>'
            f'<defs><clipPath id="stage"><rect width="{FW}" height="{FH}" rx="16"/></clipPath></defs>'
            f'<g clip-path="url(#stage)"><rect width="{FW}" height="{FH}" fill="{BG}"/>{"".join(groups)}</g></svg>')


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
        '<a href="https://mohamedmowafy.com"><img src="assets/film.svg" width="100%" alt="A fast fight between ink '
        'drawings and ASCII characters that ends with the name Mohamed Mowafy."></a>',
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
