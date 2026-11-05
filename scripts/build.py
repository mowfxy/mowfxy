"""Generate the SVGs for the mowfxy profile README.

The banner is a short looping film in Clem's ink: an ivory pen line that wanders a little and boils on twos, one
colour spot per shot, poses that snap with a small overshoot. It is plain SVG + CSS, so GitHub plays it in an <img>.
The project cards are still pictures.

    pip install fonttools brotli pillow
    python3 scripts/build.py      # CLEM=../clem KERN=../kern to point at the repos the pictures come from
"""
import base64, io, math, os
from fontTools import subset
from fontTools.ttLib import TTFont
from PIL import Image

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


def spot(poly, b, a=-.7, gap=7):
    return draw(poly, b, fill=BLUE, closed=True, w=FINE) + "".join(draw([p, q], b, w=THIN) for p, q in stripes(poly, a, gap))


def caption(s):
    return f'<text x="560" y="224" class="serif" font-size="42" fill="{INK}">{esc(s)}</text>'


def film():
    W, H, T = 1000, 420, 14.0
    f = Film(T)
    shots, texts = [], set()

    # ---------------- 1 · a soldering iron touches the joint, a curl of smoke
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
    smoke = lambda b: (draw([(384, 240), (374, 214), (390, 190), (376, 164), (388, 138)], b, w=THIN, smooth=True)
                       + draw([(402, 236), (412, 210), (398, 188), (410, 164)], b, w=THIN, smooth=True))
    k = f.fade(t0 + 1.35, t0 + 1.4, t0 + 2.9, t0 + 3.2)
    g.append(f'<g class="{k}">{f.ink(smoke, draw_on=(t0 + 1.35, t0 + 2.4))}</g>')
    g.append(caption("I solder things."))
    texts.add("I solder things.")
    shots.append((t0, t0 + 3.5, g))

    # ---------------- 2 · the scope draws a wave; the knob turns and the wave speeds up
    t0, g = 3.5, []
    screen = rounded(130, 104, 300, 196, 18)
    g.append(f.ink(lambda b: draw(screen, b, closed=True)
                   + draw([(150, 202), (410, 202)], b, w=THIN) + draw([(280, 122), (281, 282)], b, w=THIN)
                   + draw([(172, 300), (162, 324)], b, w=FINE) + draw([(388, 300), (398, 324)], b, w=FINE)))
    for i, (amp, per, a, e) in enumerate(((40, 2.0, t0 + .35, t0 + 1.35), (58, 4.0, t0 + 1.95, t0 + 2.55))):
        wave = [(152 + 256 * j / 72, 202 - amp * math.sin(TAU * per * j / 72)) for j in range(73)]
        k = f.fade(t0, t0 + .01, t0 + 1.9, t0 + 1.95) if i == 0 else f.fade(t0 + 1.95, t0 + 1.96)
        g.append(f'<g class="{k}">' + f.ink((lambda wv: lambda b: draw(wv, b, w=FINE, smooth=True))(wave),
                                            draw_on=(a, e)) + "</g>")
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

    # ---------------- 3 · a wire reaches the bulb and it lights
    t0, g = 7.0, []
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
    for i in range(7):
        a = math.pi * (1.0 + i / 6)
        p = (392 + math.cos(a) * 86, 172 + math.sin(a) * 86)
        q = (392 + math.cos(a) * 110, 172 + math.sin(a) * 110)
        k = f.pop(t0 + 1.35 + i * .05)
        g.append(f'<g class="{k}" style="transform-origin:{p[0]:.0f}px {p[1]:.0f}px">'
                 + f.ink((lambda p, q: lambda b: draw([p, q], b, w=FINE))(p, q)) + "</g>")
    g.append(caption("Then they light up."))
    texts.add("Then they light up.")
    shots.append((t0, t0 + 3.5, g))

    # ---------------- 4 · the name: written on, then underlined by the pen (also the still frame)
    t0, g = 10.5, []
    name, sub = "Mohamed Mowafy", "electronics engineering student · cairo"
    texts.update([name, sub])
    g.append(f'<text x="{W/2}" y="208" class="serif" font-size="78" fill="{INK}" text-anchor="middle">{name}</text>')
    k = f.anim([(0, "transform:scaleX(1)"), (t0 + .25, "transform:scaleX(1)", "cubic-bezier(.5,0,.2,1)"),
                (t0 + 1.15, "transform:scaleX(0)"), (T, "transform:scaleX(0)")])
    g.append(f'<rect class="{k}" x="220" y="120" width="580" height="110" fill="{BG}" style="transform-origin:800px 0"/>')
    under = [(310 + 380 * j / 12, 240 + math.sin(j * 1.1) * 2.4) for j in range(13)]
    g.append(f.ink(lambda b: draw(under, b, w=FINE, smooth=True, color=BLUE), draw_on=(t0 + 1.05, t0 + 1.7)))
    k = f.fade(t0 + 1.4, t0 + 1.9)
    g.append(f'<text class="sans {k}" x="{W/2}" y="292" font-size="20" fill="{SOFT}" text-anchor="middle" '
             f'letter-spacing=".4">{esc(sub)}</text>')
    shots.append((t0, T, g))

    body = []
    for i, (a, b, g) in enumerate(shots):
        if i == len(shots) - 1:  # the title is what shows when motion is off
            k = f.anim([(0, "opacity:0"), (a, "opacity:0"), (a + .3, "opacity:1"), (b - .45, "opacity:1"),
                        (b - .05, "opacity:0"), (T, "opacity:0")])
            body.append(f'<g class="{k}">{"".join(g)}</g>')
        else:
            k = f.anim([(0, "opacity:0"), (a, "opacity:0"), (a + .35, "opacity:1"), (b - .35, "opacity:1"),
                        (b, "opacity:0"), (T, "opacity:0")])
            body.append(f'<g class="{k} still-off">{"".join(g)}</g>')

    css = (font_face("MS", "MowafySerif-Regular.woff2", "".join(texts))
           + font_face("MN", "MowafySans-Regular.woff2", "".join(texts))
           + ".serif{font-family:MS,Georgia,serif;letter-spacing:-.5px}.sans{font-family:MN,system-ui,sans-serif}"
           + "@keyframes bo{0%{visibility:visible}33.33%,100%{visibility:hidden}}"
           + ".b{animation:bo .5s step-end infinite}.b1{animation-delay:-.3333s}.b2{animation-delay:-.1667s}"
           + "".join(f.css)
           + "@media (prefers-reduced-motion:reduce){*{animation:none!important}.b1,.b2,.still-off{display:none}}")
    alt = ("A short ink film: a soldering iron touches a joint, an oscilloscope draws a wave, a bulb lights up, "
           "then the name Mohamed Mowafy, electronics engineering student in Cairo.")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="{esc(alt)}"><title>Mohamed Mowafy</title><style>{css}</style>'
            f'<rect width="{W}" height="{H}" rx="16" fill="{BG}"/>{"".join(body)}</svg>')


# ------------------------------------------------------------------ cards with a picture
def picture(path, box, out_w=800):
    im = Image.open(path).convert("RGB").crop(box)
    x0, y0, x1, y1 = box
    im = im.resize((out_w, round(out_w * (y1 - y0) / (x1 - x0))), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=82, method=6)
    return base64.b64encode(buf.getvalue()).decode()


def picture_fit(path, size=(786, 340), scale=1.0):
    """The whole picture, centred on its own background colour."""
    im = Image.open(path).convert("RGB")
    canvas = Image.new("RGB", size, im.getpixel((4, 4)))
    h = round(size[1] * scale)
    im = im.resize((round(im.width * h / im.height), h), Image.LANCZOS)
    canvas.paste(im, ((size[0] - im.width) // 2, (size[1] - im.height) // 2))
    buf = io.BytesIO()
    canvas.save(buf, "WEBP", quality=84, method=6)
    return base64.b64encode(buf.getvalue()).decode()


def card(name, desc, pic):
    W, H = 423, 268
    cw, ch = W - 10, H - 8
    pw, ph = cw - 20, 170
    css = (font_face("MS", "MowafySerif-Regular.woff2", name) + font_face("MN", "MowafySans-Regular.woff2", desc + "↗")
           + ".serif{font-family:MS,Georgia,serif}.sans{font-family:MN,system-ui,sans-serif}")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="{esc(name)}: {esc(desc)}"><title>{esc(name)}</title><style>{css}</style>'
            f'<defs><clipPath id="p"><rect x="15" y="10" width="{pw}" height="{ph}" rx="10"/></clipPath></defs>'
            f'<rect x="5.5" y=".5" width="{cw-1}" height="{ch-1}" rx="14" fill="{CARD}" stroke="{RULE}"/>'
            f'<image href="data:image/webp;base64,{pic}" x="15" y="10" width="{pw}" height="{ph}" '
            f'preserveAspectRatio="xMidYMid slice" clip-path="url(#p)"/>'
            f'<rect x="15.5" y="10.5" width="{pw-1}" height="{ph-1}" rx="10" fill="none" stroke="{RULE}"/>'
            f'<text class="serif" x="24" y="{ph+48}" font-size="26" fill="{INK}">{esc(name)}</text>'
            f'<text class="sans" x="{cw-6}" y="{ph+46}" font-size="18" fill="{MUTE}" text-anchor="end">↗</text>'
            f'<text class="sans" x="24" y="{ph+72}" font-size="14" fill="{SOFT}">{esc(desc)}</text></svg>')


CARDS = [
    dict(slug="clem", name="Clem", desc="A calm, local-first workspace.", url="https://github.com/mowfxy/clem",
         pic=lambda: picture(f"{CLEM}/docs/assets/screenshots/home.png", (300, 225, 1500, 742))),
    dict(slug="kern", name="Kern", desc="Design taste for coding agents.", url="https://github.com/mowfxy/kern",
         pic=lambda: picture_fit(f"{KERN}/.claude-plugin/icon.png", scale=1.15)),
]


def readme():
    cards = "".join(f'<a href="{c["url"]}"><img src="assets/card-{c["slug"]}.svg" width="423" '
                    f'alt="{c["name"]}: {c["desc"]}"></a>' for c in CARDS)
    return "\n".join([
        '<a href="https://mohamedmowafy.com"><img src="assets/film.svg" width="100%" alt="A short ink film: a '
        'soldering iron, an oscilloscope, a bulb lighting up, then Mohamed Mowafy, electronics engineering student '
        'in Cairo."></a>',
        "",
        f'<p align="center">{cards}</p>',
        "",
        '<p align="center"><a href="https://mohamedmowafy.com">mohamedmowafy.com</a></p>',
        "",
        "<!-- Generated by scripts/build.py. Set in Mowafy Serif and Mowafy Sans. -->",
        "",
    ])


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for x in os.listdir(OUT):
        os.remove(os.path.join(OUT, x))
    files = {"film.svg": film()}
    for c in CARDS:
        files[f"card-{c['slug']}.svg"] = card(c["name"], c["desc"], c["pic"]())
    for n, content in files.items():
        with open(os.path.join(OUT, n), "w") as fh:
            fh.write(content)
        print(f"{n:20} {len(content) / 1024:7.1f} KB")
    with open(os.path.join(HERE, "..", "README.md"), "w") as fh:
        fh.write(readme())
