"""Generate the SVGs for the mowfxy profile README.

The banner is a short looping film in Clem's ink: an ivory pen line that wanders a little and boils on twos, one
colour spot per shot, poses that snap with a small overshoot. It is plain SVG + CSS, so GitHub plays it in an <img>.
The project cards are still pictures.

    pip install fonttools brotli
    python3 scripts/build.py      # CLEM=../clem KERN=../kern to point at the repos the pictures come from
"""
import base64, io, math, os
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
        for j in range(8):
            t = j / 8
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


def path_d(pts, close=False):
    return "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + ("Z" if close else "")


def draw(pts, boil, fill=None, w=LINE, smooth=False, closed=False, color=INK):
    s = SEED[0]
    SEED[0] += 1
    tr = hand(spline(pts, closed) if smooth else densify(pts, closed), s, boil)
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
        lead = len(r) - len(r.lstrip(" "))
        r = r.strip(" ")
        if r:
            sp.append(f'<tspan x="{x + lead * size * .6:.1f}" y="{y + i * lh:.1f}">{esc(r)}</tspan>')
    if not sp:
        return ""
    o = f' opacity="{opacity}"' if opacity < 1 else ""
    c = f' class="{cls}"' if cls else ""
    return f'<text{c} class="mono" font-size="{size}" fill="{fill}"{o} xml:space="preserve">{"".join(sp)}</text>'


class Flip:
    """Looping flip-books of ASCII frames, n frames over `period` seconds."""
    done = set()

    def __init__(self, film):
        self.f = film

    def __call__(self, frames, x, y, size, lh, period, fill, opacity=1):
        n = len(frames)
        key = f"fl{n}"
        if key not in Flip.done:
            Flip.done.add(key)
            self.f.css.append(f"@keyframes {key}{{0%{{visibility:visible}}{100 / n:.3f}%,100%{{visibility:hidden}}}}")
        out = ""
        for i, fr in enumerate(frames):
            d = -(n - i) % n * period / n
            vis = "" if i == 0 else "visibility:hidden;"
            out += (f'<g class="fl" style="{vis}animation:{key} {period}s step-end {-(period - i * period / n) % period:.3f}s '
                    f'infinite">{rows_text(fr, x, y, size, lh, fill, opacity)}</g>')
        return out


def smoke_frames(n=12, cols=18, rows=12):
    out = []
    for k in range(n):
        g = [[" "] * cols for _ in range(rows)]
        for p in range(26):
            ph = (hsh(p, 1) + k / n) % 1
            y = int((1 - ph) * (rows - 1))
            x = int(cols / 2 + math.sin(ph * 5 + p) * (1 + ph * 4) + (hsh(p, 2) - .5) * 3)
            if 0 <= x < cols:
                g[y][x] = "o" if ph < .15 else ("~" if ph < .45 else ("'" if ph < .7 else "."))
        out.append(["".join(r) for r in g])
    return out


def static_frames(cols, rows, n=4, dens=.13):
    return [["".join((CHARS[1 + int(hsh(i + k * 31, j) * 6)] if hsh(i * 3 + k, j * 7 + k) < dens else " ")
                     for i in range(cols)) for j in range(rows)] for k in range(n)]


def glow_frames(cols, rows, cx, cy, r0, r1, n=4, aspect=.52):
    out = []
    for k in range(n):
        fr = []
        for j in range(rows):
            line = ""
            for i in range(cols):
                d = math.hypot((i - cx) * aspect, j - cy)
                if d < r0 or d > r1:
                    line += " "
                    continue
                v = (1 - (d - r0) / (r1 - r0)) ** 1.4
                line += (" .:+*"[min(4, int(v * 5 + hsh(i + k, j) * .8))] if hsh(i * 7 + k * 13, j * 3) < v * .9 else " ")
            fr.append(line)
        out.append(fr)
    return out


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


# ------------------------------------------------------------------ the film
SNAP = "cubic-bezier(.34,1.5,.64,1)"


class Film:
    """Shots on one looping timeline. Every timed thing is a CSS animation over the whole loop."""

    def __init__(self, T):
        self.T, self.css, self.n = T, [], 0

    def anim(self, stops):
        """stops: [(seconds, 'css', optional easing for the segment that starts there)]"""
        self.n += 1
        k = f"k{self.n}"
        fr = "".join(f"{max(0, min(100, st[0] / self.T * 100)):.3f}%{{{st[1]}"
                     + (f";animation-timing-function:{st[2]}" if len(st) > 2 else "") + "}" for st in stops)
        self.css.append(f"@keyframes {k}{{{fr}}}.{k}{{animation:{k} {self.T}s linear infinite}}")
        return k

    def windows(self, wins):
        """Visible only inside the given (start, end) windows of the loop."""
        stops, t = [(0, "opacity:0")], 0
        for a, b in sorted(wins):
            stops += [(a, "opacity:0", "step-end"), (a + .001, "opacity:1"), (b, "opacity:1", "step-end"),
                      (b + .001, "opacity:0")]
        stops.append((self.T, "opacity:0"))
        if wins and min(a for a, _ in wins) <= 0:
            stops[0] = (0, "opacity:1")
        return self.anim(stops)

    def ink(self, fn, draw_on=None):
        """Three drawings of the same lines, flipped six times a second, so the line boils."""
        seed = SEED[0]
        out = ""
        for b in range(3):
            SEED[0] = seed
            out += f'<g class="b b{b}">{fn(b)}</g>'
        if draw_on:
            t0, t1 = draw_on
            k = self.anim([(0, "stroke-dashoffset:1"), (t0, "stroke-dashoffset:1", "cubic-bezier(.4,.1,.3,1)"),
                           (t1, "stroke-dashoffset:0"), (self.T, "stroke-dashoffset:0")])
            out = out.replace('pathLength="1"', f'pathLength="1" stroke-dasharray="1 1.02" class="{k}"')
        return out

    def pop(self, t):
        return self.anim([(0, "transform:scale(0)"), (t, "transform:scale(0)", SNAP), (t + .32, "transform:scale(1)"),
                          (self.T, "transform:scale(1)")])

    def fade(self, a, b, c=None, d=None):
        st = [(0, "opacity:0"), (a, "opacity:0"), (b, "opacity:1")]
        if c is not None:
            st += [(c, "opacity:1"), (d, "opacity:0")]
        return self.anim(st + [(self.T, f"opacity:{0 if c is not None else 1}")])


def spot(poly, b, a=-.7, gap=7, color=INK):
    return (draw(poly, b, fill=BLUE, closed=True, w=FINE, color=color)
            + "".join(draw([p, q], b, w=THIN, color=color) for p, q in stripes(poly, a, gap)))


def caption(s):
    return f'<text x="560" y="224" class="serif" font-size="42" fill="{INK}">{esc(s)}</text>'


def film():
    W, H, T = 1000, 420, 14.0
    f = Film(T)
    flip = Flip(f)
    shots, texts, mono = [], set(), set()
    CUTS = [0.0, 3.5, 7.0, 10.5]

    # ---------------- 1 · a soldering iron touches the joint; ASCII smoke rises
    t0, g = 0.0, []
    board = rounded(110, 262, 360, 64, 12)
    g.append(f.ink(lambda b: draw(board, b, w=FINE, closed=True)
                   + "".join(draw([(x, 284), (x + 1, 304)], b, w=THIN) for x in range(150, 431, 40))))
    body = rounded(232, 214, 104, 34, 17)
    g.append(f.ink(lambda b: draw(body, b, closed=True)
                   + draw([(232, 231), (180, 231), (180, 262)], b, w=FINE)
                   + draw([(336, 231), (392, 231), (392, 258)], b, w=FINE)
                   + "".join(draw([(x, 219), (x + 1, 243)], b, w=THIN) for x in (262, 282, 302))))
    joint = ellipse(392, 262, 15, 9)
    k = f.pop(t0 + 1.2)
    g.append(f'<g class="{k}" style="transform-origin:392px 262px">{f.ink(lambda b: spot(joint, b, gap=6))}</g>')
    iron = lambda b: (draw([(398, 250), (434, 202)], b, w=FINE)
                      + draw([(424, 214), (448, 180), (500, 112), (518, 124), (466, 192), (442, 226)], b, closed=True)
                      + draw([(509, 118), (556, 56)], b, w=FINE)
                      + draw([(462, 160), (478, 172)], b, w=THIN) + draw([(474, 144), (490, 156)], b, w=THIN))
    k = f.anim([(0, "transform:translate(130px,-100px) rotate(10deg)"),
                (t0 + .45, "transform:translate(130px,-100px) rotate(10deg)", SNAP),
                (t0 + .95, "transform:translate(0,0) rotate(0)"),
                (t0 + 2.5, "transform:translate(0,0) rotate(0)", SNAP),
                (t0 + 2.95, "transform:translate(80px,-70px) rotate(6deg)"),
                (T, "transform:translate(80px,-70px) rotate(6deg)")])
    g.append(f'<g class="{k}" style="transform-origin:398px 250px">{f.ink(iron)}</g>')
    sm = smoke_frames()
    mono.update("".join("".join(r) for r in fr) for fr in sm)
    k = f.fade(t0 + 1.25, t0 + 1.5, t0 + 3.0, t0 + 3.4)
    g.append(f'<g class="{k}">{flip(sm, 318, 66, 15, 15, 1.6, INK, .85)}</g>')
    sp = [["  .  *  ,", " ' \\ | / .", "*-- o --*", " , / | \\ '", "  .  *  ."]]
    mono.update("".join(sp[0]))
    k = f.fade(t0 + 1.0, t0 + 1.05, t0 + 1.3, t0 + 1.45)
    g.append(f'<g class="{k}">{rows_text(sp[0], 366, 240, 11, 9, SAND)}</g>')
    g.append(caption("I solder things."))
    texts.add("I solder things.")
    shots.append((t0, t0 + 3.5, g))

    # ---------------- 2 · the scope: static on the glass, a wave, the knob turns, a glowing faster wave
    t0, g = 3.5, []
    st = static_frames(33, 10)
    mono.update("".join("".join(r) for r in fr) for fr in st)
    g.append(flip(st, 150, 134, 13, 15.5, .5, INK, .38))
    screen = rounded(130, 104, 300, 196, 18)
    g.append(f.ink(lambda b: draw(screen, b, closed=True)
                   + draw([(150, 202), (410, 202)], b, w=THIN) + draw([(280, 122), (281, 282)], b, w=THIN)
                   + draw([(172, 300), (162, 324)], b, w=FINE) + draw([(388, 300), (398, 324)], b, w=FINE)))
    for i, (amp, per, a, e) in enumerate(((40, 2.0, t0 + .35, t0 + 1.35), (58, 4.0, t0 + 1.95, t0 + 2.55))):
        wave = [(152 + 256 * j / 72, 202 - amp * math.sin(TAU * per * j / 72)) for j in range(73)]
        k = f.fade(t0, t0 + .01, t0 + 1.9, t0 + 1.95) if i == 0 else f.fade(t0 + 1.95, t0 + 1.96)
        g.append(f'<g class="{k}">' + f.ink((lambda wv: lambda b: draw(wv, b, w=FINE, smooth=True))(wave),
                                            draw_on=(a, e)) + "</g>")
    # phosphor: ASCII glow hugging the fast wave
    gl = []
    for kk in range(4):
        fr = []
        for j in range(11):
            line = ""
            for i in range(33):
                x = 152 + i * 7.8
                y = 129 + j * 15.5
                wy = 202 - 58 * math.sin(TAU * 4 * (x - 152) / 256)
                d = abs(y - wy) / 15.5
                line += (".:+"[min(2, int((1.6 - d) * 1.6))] if d < 1.6 and hsh(i + kk * 7, j) < .75 - d * .3 else " ")
            fr.append(line)
        gl.append(fr)
    mono.update("".join("".join(r) for r in fr) for fr in gl)
    k = f.fade(t0 + 2.4, t0 + 2.7)
    g.append(f'<g class="{k}">{flip(gl, 152, 134, 13, 15.5, .5, BLUE, .55)}</g>')
    knob = ellipse(478, 150, 22)
    g.append(f.ink(lambda b: spot(knob, b, a=.7)))
    k = f.anim([(0, "transform:rotate(-70deg)"), (t0 + 1.6, "transform:rotate(-70deg)", SNAP),
                (t0 + 1.95, "transform:rotate(40deg)"), (T, "transform:rotate(40deg)")])
    g.append(f'<g class="{k}" style="transform-origin:478px 150px">'
             + f.ink(lambda b: draw([(478, 152), (478, 120)], b, w=LINE)) + "</g>")
    g.append(f.ink(lambda b: draw(ellipse(478, 228, 13), b, closed=True, w=FINE)
                   + draw([(478, 228), (487, 219)], b, w=THIN)))
    g.append(caption("I measure them."))
    texts.add("I measure them.")
    shots.append((t0, t0 + 3.5, g))

    # ---------------- 3 · a wire reaches the bulb; it lights and ASCII light spills out
    t0, g = 7.0, []
    hl = glow_frames(48, 22, 24, 9.6, 5.2, 11)
    mono.update("".join("".join(r) for r in fr) for fr in hl)
    k = f.fade(t0 + 1.3, t0 + 1.6)
    g.append(f'<g class="{k}">{flip(hl, 392 - 24 * 7.8, 172 - 9.6 * 15.5 + 4, 13, 15.5, .5, BLUE, .7)}</g>')
    g.append(f.ink(lambda b: draw(rounded(130, 214, 70, 112, 10), b, closed=True)
                   + draw(rounded(152, 200, 26, 14, 4), b, closed=True, w=FINE)
                   + draw([(157, 246), (173, 246)], b, w=THIN) + draw([(165, 238), (165, 254)], b, w=THIN)
                   + draw([(157, 298), (173, 298)], b, w=THIN)))
    wire = [(165, 200), (172, 150), (232, 132), (272, 196), (300, 292), (346, 304), (368, 290)]
    g.append(f.ink(lambda b: draw(wire, b, w=FINE, smooth=True), draw_on=(t0 + .3, t0 + 1.2)))
    glass = [(372, 252)] + arc(392, 172, 66, 66, math.pi * .62, math.pi * 2.38, 40) + [(412, 252)]
    k = f.fade(t0 + 1.25, t0 + 1.32)
    g.append(f'<g class="{k}">' + f.ink(lambda b: draw(glass, b, fill=BLUE, closed=True, w=0)
                                        + "".join(draw([p, q], b, w=THIN) for p, q in stripes(glass, -.6, 10)))
             + "</g>")
    g.append(f.ink(lambda b: draw(glass, b, closed=True)
                   + draw(rounded(368, 252, 48, 40, 8), b, closed=True, w=FINE)
                   + draw([(370, 266), (414, 264)], b, w=THIN) + draw([(370, 278), (414, 276)], b, w=THIN)
                   + draw([(381, 252), (381, 204), (388, 190), (396, 204), (404, 190), (404, 252)], b, w=THIN)))
    g.append(caption("Then they light up."))
    texts.add("Then they light up.")
    shots.append((t0, t0 + 3.5, g))

    # ---------------- 4 · the name decodes out of ASCII into ink, over Clem's ASCII range (also the still frame)
    t0, g = 10.5, []
    name, sub = "Mohamed Mowafy", "electronics engineering student · cairo"
    texts.update([name, sub])
    mt = [mountains(120, 9, top=0, k=kk) for kk in range(2)]
    sky = [["".join(("." if hsh(i * 13 + kk, j * 7) < .5 else "'") if hsh(i * 3, j * 11) < .02 else " "
                    for i in range(120)) for j in range(9)] for kk in range(2)]
    for fr in mt + sky:
        mono.update("".join(fr))
    g.append(flip(sky, 0, 22, 14, 17, 1.4, ASH))
    g.append(rows_text(mt[0], 0, 286, 14, 17, ASH))
    letters = "MOHAMEDWFY@#%&*+=~^/\\<>01"
    mono.update(name + letters)
    steps = 10
    for s_ in range(steps):
        prog = (s_ + 1) / steps
        txt = "".join(c if (c == " " or hsh(i, 3) < prog * 1.2 - .1) else letters[int(hsh(i, s_ + 9) * len(letters))]
                      for i, c in enumerate(name))
        a = t0 + .15 + s_ * .08
        k = f.windows([(a, a + .08)] if s_ < steps - 1 else [(a, t0 + 1.25)])
        g.append(f'<text class="mono {k}" style="opacity:0" x="{W/2}" y="200" font-size="58" fill="{INK}" '
                 f'text-anchor="middle" xml:space="preserve">{esc(txt)}</text>')
    k = f.anim([(0, "opacity:0"), (t0 + 1.0, "opacity:0"), (t0 + 1.3, "opacity:1"), (T, "opacity:1")])
    g.append(f'<g class="{k}"><rect x="200" y="128" width="600" height="100" fill="{BG}" opacity=".85" rx="20"/>'
             f'<text x="{W/2}" y="208" class="serif" font-size="78" fill="{INK}" text-anchor="middle">{name}</text></g>')
    under = [(310 + 380 * j / 12, 240 + math.sin(j * 1.1) * 2.4) for j in range(13)]
    g.append(f.ink(lambda b: draw(under, b, w=FINE, smooth=True, color=BLUE), draw_on=(t0 + 1.3, t0 + 1.9)))
    k = f.fade(t0 + 1.6, t0 + 2.0)
    g.append(f'<text class="sans {k}" x="{W/2}" y="292" font-size="20" fill="{SOFT}" text-anchor="middle" '
             f'letter-spacing=".4">{esc(sub)}</text>')
    shots.append((t0, T, g))

    # ---------------- cuts: an ASCII dissolve sweeps over every change of shot
    body = []
    for i, (a, b, g) in enumerate(shots):
        if i == len(shots) - 1:
            k = f.anim([(0, "opacity:0"), (a, "opacity:0", "step-end"), (a + .001, "opacity:1"),
                        (b - .001, "opacity:1", "step-end"), (b, "opacity:0")])
            body.append(f'<g class="{k}">{"".join(g)}</g>')
        else:
            k = f.anim([(0, "opacity:1" if a == 0 else "opacity:0"), (a, "opacity:0" if a else "opacity:1", "step-end"),
                        (a + .001, "opacity:1"), (b, "opacity:1", "step-end"), (b + .001, "opacity:0"),
                        (T, "opacity:0")])
            body.append(f'<g class="{k} still-off">{"".join(g)}</g>')
    dens = [.1, .3, .58, .88, .88, .58, .3, .1]
    dt = .07
    for n_, d in enumerate(dens):
        fr = []
        for j in range(25):
            line = ""
            for i in range(119):
                sweep = d + .35 * (i / 118 - .5) * (1 if n_ < 4 else -1)
                line += CHARS[1 + int(hsh(i + n_ * 3, j) * 15)] if hsh(i * 7 + n_, j * 13) < sweep else " "
            fr.append(line)
        mono.update("".join(fr))
        wins = []
        for c in CUTS:
            s0 = c - 4 * dt + n_ * dt
            if s0 < 0:
                wins.append((s0 + T, s0 + T + dt))
            else:
                wins.append((s0, s0 + dt))
        k = f.windows([(a, min(T, b)) for a, b in wins])
        body.append(f'<g class="{k} still-off" style="opacity:0"><rect width="{W}" height="{H}" rx="16" fill="{BG}" '
                    f'opacity="{min(1, d * 1.05):.2f}"/>{rows_text(fr, 4, 17, 14, 17, INK, .8)}</g>')

    css = (font_face("MS", "MowafySerif-Regular.woff2", "".join(texts))
           + font_face("MN", "MowafySans-Regular.woff2", "".join(texts))
           + font_face("JM", "JetBrainsMono.woff2", "".join(mono))
           + ".serif{font-family:MS,Georgia,serif;letter-spacing:-.5px}.sans{font-family:MN,system-ui,sans-serif}"
           + ".mono{font-family:JM,ui-monospace,monospace;white-space:pre}"
           + "@keyframes bo{0%{visibility:visible}33.33%,100%{visibility:hidden}}"
           + ".b{animation:bo .5s step-end infinite}.b1{animation-delay:-.3333s}.b2{animation-delay:-.1667s}"
           + "".join(f.css)
           + "@media (prefers-reduced-motion:reduce){*{animation:none!important}.b1,.b2,.still-off{display:none}}")
    alt = ("A short film in ink and ASCII: a soldering iron touches a joint as ASCII smoke rises, an oscilloscope "
           "draws a wave, a bulb lights up and spills ASCII light, then the name Mohamed Mowafy decodes out of "
           "characters over an ASCII mountain range: electronics engineering student in Cairo.")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="{esc(alt)}"><title>Mohamed Mowafy</title><style>{css}</style>'
            f'<rect width="{W}" height="{H}" rx="16" fill="{BG}"/>{"".join(body)}</svg>')


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
        '<a href="https://mohamedmowafy.com"><img src="assets/film.svg" width="100%" alt="A short film in ink and '
        'ASCII: a soldering iron, an oscilloscope, a bulb lighting up, then Mohamed Mowafy, electronics engineering '
        'student in Cairo."></a>',
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
