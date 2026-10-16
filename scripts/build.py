"""Generate the animated SVG assets for the mowfxy profile README.

All text is converted to outlines, so the SVGs render identically everywhere
(GitHub serves them as images, which can't load web fonts).

    python3 scripts/build.py
"""
from functools import lru_cache
import math, os, random

from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

OUT = os.path.join(os.path.dirname(__file__), "..", "assets")
INTER = "/usr/share/fonts/opentype/inter/"

# palette — soldermask, copper, silkscreen
BG, BG2, EDGE, GRID = "#0B1310", "#0F1A16", "#22322B", "#1A2822"
COPPER, COPPER_D, HOT = "#D0914F", "#5E422A", "#FFD9A3"
CREAM, DIM, FAINT = "#EDE7D9", "#98A49D", "#5D6B64"
TEAL, LED, RED = "#62E0C8", "#7DF5B0", "#E5684F"


# ---------------------------------------------------------------- text → path
class Font:
    def __init__(self, path):
        self.f = TTFont(path)
        self.gs = self.f.getGlyphSet()
        self.cmap = self.f.getBestCmap()
        self.upm = self.f["head"].unitsPerEm
        self.hmtx = self.f["hmtx"]
        self.kern_subtables = []
        if "GPOS" in self.f:
            g = self.f["GPOS"].table
            idx = set()
            for fr in g.FeatureList.FeatureRecord:
                if fr.FeatureTag == "kern":
                    idx.update(fr.Feature.LookupListIndex)
            for i in sorted(idx):
                lk = g.LookupList.Lookup[i]
                for st in lk.SubTable:
                    if lk.LookupType == 9:
                        st = st.ExtSubTable
                    if getattr(st, "LookupType", 2) == 2:
                        self.kern_subtables.append(st)

    def glyph(self, ch):
        return self.cmap.get(ord(ch), ".notdef")

    @lru_cache(maxsize=None)
    def kern(self, a, b):
        for st in self.kern_subtables:
            cov = st.Coverage.glyphs
            if a not in cov:
                continue
            if st.Format == 1:
                for pvr in st.PairSet[cov.index(a)].PairValueRecord:
                    if pvr.SecondGlyph == b:
                        return getattr(pvr.Value1, "XAdvance", 0) or 0
            else:
                c1 = st.ClassDef1.classDefs.get(a, 0)
                c2 = st.ClassDef2.classDefs.get(b, 0)
                v = st.Class1Record[c1].Class2Record[c2].Value1
                return (getattr(v, "XAdvance", 0) or 0) if v else 0
        return 0

    def advances(self, text, size, ls=0):
        s = size / self.upm
        gl = [self.glyph(c) for c in text]
        out = []
        for i, g in enumerate(gl):
            a = self.hmtx[g][0] * s + ls
            if i + 1 < len(gl):
                a += self.kern(g, gl[i + 1]) * s
            out.append(a)
        return gl, out

    def width(self, text, size, ls=0):
        if not text:
            return 0
        _, adv = self.advances(text, size, ls)
        return sum(adv) - ls

    def d(self, text, size, x, y, anchor="start", ls=0):
        w = self.width(text, size, ls)
        x -= {"start": 0, "middle": w / 2, "end": w}[anchor]
        gl, adv = self.advances(text, size, ls)
        pen = SVGPathPen(self.gs, ntos=lambda v: f"{v:.1f}".rstrip("0").rstrip("."))
        s = size / self.upm
        for g, a in zip(gl, adv):
            self.gs[g].draw(TransformPen(pen, (s, 0, 0, -s, x, y)))
            x += a
        return pen.getCommands()


DISPLAY = Font(INTER + "InterDisplay-SemiBold.otf")
BODY = Font(INTER + "Inter-Regular.otf")
MED = Font(INTER + "Inter-Medium.otf")
MONO = Font("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")


def text(font, s, size, x, y, fill, anchor="start", ls=0, extra=""):
    return f'<path d="{font.d(s, size, x, y, anchor, ls)}" fill="{fill}" {extra}/>'


def label(s, x, y, fill=COPPER, size=11, anchor="start", ls=2.2):
    return text(MONO, s.upper(), size, x, y, fill, anchor, ls)


# ---------------------------------------------------------------- shared bits
BASE_CSS = """
@keyframes pulse{from{stroke-dashoffset:14}to{stroke-dashoffset:-100}}
@keyframes led{0%,100%{opacity:1}50%{opacity:.25}}
@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}
.pulse{fill:none;stroke:%HOT%;stroke-width:2.4;stroke-linecap:round;stroke-dasharray:14 120;
       animation:pulse 3.2s cubic-bezier(.5,0,.5,1) infinite}
.led{animation:led 2.4s ease-in-out infinite}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
""".replace("%HOT%", HOT)


def svg(w, h, body, css="", title=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'role="img" aria-label="{title}"><title>{title}</title>'
        f"<style>{BASE_CSS}{css}</style>"
        f'<defs><pattern id="g" width="22" height="22" patternUnits="userSpaceOnUse">'
        f'<circle cx="11" cy="11" r="1" fill="{GRID}"/></pattern>'
        f'<filter id="glow" x="-20%" y="-20%" width="140%" height="140%">'
        f'<feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/>'
        f'<feMergeNode in="SourceGraphic"/></feMerge></filter></defs>'
        f"{body}</svg>"
    )


def board(w, h, rx=16):
    return (
        f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="{rx}" fill="{BG}" stroke="{EDGE}"/>'
        f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="{rx}" fill="url(#g)"/>'
    )


def hole(x, y, r=7):
    return (f'<circle cx="{x}" cy="{y}" r="{r}" fill="none" stroke="{COPPER_D}" stroke-width="3"/>'
            f'<circle cx="{x}" cy="{y}" r="{r-3.5}" fill="#050807"/>')


def via(x, y):
    return f'<circle cx="{x}" cy="{y}" r="4.5" fill="{BG}" stroke="{COPPER}" stroke-width="2"/>'


def led(x, y, color=LED, delay=0, r=4):
    return (f'<g class="led" style="animation-delay:{delay}s"><circle cx="{x}" cy="{y}" r="{r*2.4}" fill="{color}" opacity=".18"/>'
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/></g>')


def trace(d, delay=0, dur=3.2, width=2):
    return (f'<path d="{d}" fill="none" stroke="{COPPER_D}" stroke-width="{width}" stroke-linejoin="round"/>'
            f'<path d="{d}" pathLength="100" class="pulse" style="animation-delay:{delay}s;animation-duration:{dur}s"/>')


def write(name, content):
    with open(os.path.join(OUT, name), "w") as f:
        f.write(content)
    print(f"{name:24} {len(content)//1024:4} KB")


# ---------------------------------------------------------------- hero
def hero():
    W, H = 1200, 460
    b = [board(W, H, 20)]
    for x, y in [(30, 30), (W - 30, 30), (30, H - 30), (W - 30, H - 30)]:
        b.append(hole(x, y))

    # chip
    cx, cy, s = 935, 214, 172
    x0, y0 = cx - s / 2, cy - s / 2
    pins, n, pitch = [], 8, 17
    first = -(n - 1) / 2 * pitch
    traces = []
    rnd = random.Random(4)
    for i in range(n):
        o = first + i * pitch
        # top / bottom / left / right pin positions
        pins += [(cx + o, y0, "t"), (cx + o, y0 + s, "b"), (x0, cy + o, "l"), (x0 + s, cy + o, "r")]
    for (px, py, side) in pins:
        if side == "t":
            b.append(f'<rect x="{px-3.5}" y="{py-12}" width="7" height="12" fill="{COPPER}"/>')
        elif side == "b":
            b.append(f'<rect x="{px-3.5}" y="{py}" width="7" height="12" fill="{COPPER}"/>')
        elif side == "l":
            b.append(f'<rect x="{px-12}" y="{py-3.5}" width="12" height="7" fill="{COPPER}"/>')
        else:
            b.append(f'<rect x="{px}" y="{py-3.5}" width="12" height="7" fill="{COPPER}"/>')

    # routed traces (45° bends) from pins outwards
    def route_top(px, i):
        k = i - (n - 1) / 2
        y1 = y0 - 12 - 18 - abs(k) * 6
        dx = k * 22
        y2 = y1 - abs(dx)
        return f"M{px},{y0-12} V{y1} L{px+dx},{y2} V{14 if i%3 else 70}"

    def route_bottom(px, i):
        k = i - (n - 1) / 2
        y1 = y0 + s + 12 + 16 + (n - i) * 7
        if i < 4:  # a short bus heading left, ending in vias clear of the text
            yb = y0 + s + 26 + i * 9
            yd = H - 64 + i * 11
            end = 520 + i * 26
            ends.append((end, yd))
            return f"M{px},{y0+s+12} V{yb} L{px-(yd-yb)},{yd} H{end}"
        dx = k * 18
        return f"M{px},{y0+s+12} V{y1} L{px+dx},{y1+abs(dx)} V{H-14}"

    def route_right(py, i):
        k = i - (n - 1) / 2
        x1 = x0 + s + 12 + 20 + abs(k) * 5
        dy = k * 14
        return f"M{x0+s+12},{py} H{x1} L{x1+abs(dy)},{py+dy} H{W-14 if i%2 else W-70}"

    def route_left(py, i):
        k = i - (n - 1) / 2
        x1 = x0 - 12 - 18 - abs(k) * 5
        ex = x1 - 70 - abs(k) * 8
        ends.append((ex, py + (24 if k > 0 else -24)))
        return f"M{x0-12},{py} H{x1} L{x1-24},{py+(24 if k>0 else -24)} H{ex}"

    ends = []
    for i in range(n):
        o = first + i * pitch
        traces.append(route_top(cx + o, i))
        traces.append(route_bottom(cx + o, i))
        traces.append(route_right(cy + o, i))
        traces.append(route_left(cy + o, i))
    for i, d in enumerate(traces):
        delay = round(rnd.uniform(0, 4), 2)
        dur = round(rnd.uniform(2.6, 4.4), 2)
        b.append(trace(d, delay, dur))
    for x, y in ends:
        b.append(via(x, y))

    # chip body
    b.append(f'<rect x="{x0}" y="{y0}" width="{s}" height="{s}" rx="10" fill="#141816" stroke="#2A302D"/>')
    b.append(f'<rect x="{x0+8}" y="{y0+8}" width="{s-16}" height="{s-16}" rx="6" fill="none" stroke="#1E2421"/>')
    b.append(f'<circle cx="{x0+22}" cy="{y0+22}" r="5" fill="#0B0E0C"/>')
    b.append(text(DISPLAY, "MWFX", 38, cx, cy + 8, CREAM, "middle", ls=3))
    b.append(label("EE · 2026", cx, cy + 36, FAINT, 10, "middle", 2))
    b.append(led(x0 + s - 24, y0 + 24, LED, 0, 3.5))

    # silkscreen
    b.append(label("U1", x0 - 4, y0 - 44, FAINT, 10, "end"))
    b.append(label("MWFX-01  REV A", W - 44, H - 22, FAINT, 10, "end"))

    # text block — knock out the traces behind it
    tx = 74
    b.append(label("electronics engineering  ·  GUC  ·  cairo", tx, 128, COPPER, 12, ls=2.6))
    b.append(text(DISPLAY, "Mohamed", 86, tx - 4, 214, CREAM, ls=-1.5))
    b.append(text(DISPLAY, "Mowafy", 86, tx - 4, 300, CREAM, ls=-1.5))

    # typewriter roles
    phrases = [
        "building Mowr, a local-first AI workspace",
        "writing skills that give coding agents taste",
        "drawing physics and circuits with code",
    ]
    size, ry, px = 21, 352, tx + 26
    b.append(text(MONO, ">", size, tx, ry, COPPER))
    T = 13.5
    slot = T / len(phrases)
    cursor_events = []
    for i, p in enumerate(phrases):
        start = i * slot
        n_ = len(p)
        type_d = n_ * 0.045
        hold_end = start + slot - 1.0
        del_d = 0.45
        ev = [(0, 0)]
        for k in range(n_ + 1):
            ev.append((start + 0.35 + type_d * k / n_, BODY.width(p[:k], size)))
        for k in range(n_, -1, -3):
            ev.append((hold_end + del_d * (n_ - k) / n_, BODY.width(p[:k], size)))
        ev.append((hold_end + del_d + 0.01, 0))
        ev.sort()
        keys = ";".join(f"{t/T:.4f}" for t, _ in ev)
        vals = ";".join(f"{w+2:.1f}" for _, w in ev)
        if ev[-1][0] < T:
            keys += ";1"
            vals += ";0"
        b.append(f'<clipPath id="c{i}"><rect x="{px}" y="{ry-30}" height="44" width="0">'
                 f'<animate attributeName="width" dur="{T}s" repeatCount="indefinite" calcMode="discrete" '
                 f'keyTimes="{keys}" values="{vals}"/></rect></clipPath>')
        b.append(f'<g clip-path="url(#c{i})">{text(BODY, p, size, px, ry, DIM)}</g>')
        cursor_events += [(t, w) for t, w in ev if start <= t <= start + slot]
    cursor_events = sorted(set(cursor_events))
    if cursor_events[0][0] > 0:
        cursor_events.insert(0, (0, 0))
    ck = ";".join(f"{t/T:.4f}" for t, _ in cursor_events) + ";1"
    cv = ";".join(f"{px + w + 3:.1f}" for _, w in cursor_events) + f";{px+3}"
    b.append(f'<rect y="{ry-19}" width="10" height="23" fill="{COPPER}" style="animation:blink 1s steps(1) infinite">'
             f'<animate attributeName="x" dur="{T}s" repeatCount="indefinite" calcMode="discrete" keyTimes="{ck}" values="{cv}"/></rect>')

    # status row
    b.append(led(tx + 4, 404, LED, 0, 3.5))
    b.append(label("online", tx + 18, 408, DIM, 11))
    b.append(label("@mowfxy", tx + 104, 408, FAINT, 11))
    b.append(label("mohamedmowafy.com", tx + 214, 408, FAINT, 11))

    # draw traces under the text: reorder so text sits on top (already appended after)
    return svg(W, H, "".join(b), title="Mohamed Mowafy — electronics engineering student building Mowr and agent skills")


# ---------------------------------------------------------------- oscilloscope divider
def scope():
    W, H = 1200, 170
    b = [board(W, H, 14)]
    L, R, T, B = 110, W - 30, 22, H - 22
    # graticule
    for i in range(11):
        x = L + (R - L) * i / 10
        b.append(f'<line x1="{x:.1f}" y1="{T}" x2="{x:.1f}" y2="{B}" stroke="{GRID}" stroke-width="1"/>')
    for j in range(5):
        y = T + (B - T) * j / 4
        b.append(f'<line x1="{L}" y1="{y:.1f}" x2="{R}" y2="{y:.1f}" stroke="{GRID}" stroke-width="1"/>')
    mid = T + (B - T) * 0.42
    b.append(f'<line x1="{L}" y1="{mid}" x2="{R}" y2="{mid}" stroke="#24352E" stroke-dasharray="2 4"/>')

    # CH1: amplitude-modulated sine
    pts = []
    N = 700
    for i in range(N + 1):
        t = i / N
        x = L + (R - L) * t
        env = 0.55 + 0.45 * math.sin(math.pi * t * 2 - 0.6)
        y = mid - 34 * env * math.sin(2 * math.pi * 9 * t)
        pts.append(f"{x:.1f},{y:.1f}")
    d = "M" + " L".join(pts)
    anim = ('<animate attributeName="stroke-dashoffset" dur="5s" repeatCount="indefinite" '
            'values="100;0;0;0" keyTimes="0;.62;.86;1"/>'
            '<animate attributeName="opacity" dur="5s" repeatCount="indefinite" '
            'values="1;1;1;0" keyTimes="0;.62;.86;1"/>')
    b.append(f'<path d="{d}" pathLength="100" fill="none" stroke="{TEAL}" stroke-width="6" opacity=".22" '
             f'stroke-dasharray="100" filter="url(#glow)">{anim}</path>')
    b.append(f'<path d="{d}" pathLength="100" fill="none" stroke="{TEAL}" stroke-width="2" stroke-dasharray="100">{anim}</path>')
    b.append(f'<circle r="4" fill="#E9FFFA"><animateMotion dur="5s" repeatCount="indefinite" path="{d}" '
             f'keyPoints="0;1;1;1" keyTimes="0;.62;.86;1" calcMode="linear"/>'
             f'<animate attributeName="opacity" dur="5s" repeatCount="indefinite" values="1;1;0;0" keyTimes="0;.62;.63;1"/></circle>')

    # CH2: scrolling clock, copper
    period = 64
    y_hi, y_lo = B - 30, B - 10
    seg = []
    x = L - period
    while x < R + period:
        seg.append(f"M{x},{y_lo} H{x+period/2} V{y_hi} H{x+period} V{y_lo}")
        x += period
    b.append(f'<clipPath id="sc"><rect x="{L}" y="{T}" width="{R-L}" height="{B-T}"/></clipPath>')
    b.append(f'<g clip-path="url(#sc)"><path d="{" ".join(seg)}" fill="none" stroke="{COPPER}" stroke-width="1.6" '
             f'style="animation:clk 1.6s linear infinite"/></g>')

    b.append(label("ch1", 28, mid + 4, TEAL, 11))
    b.append(label("500mv", 28, mid + 20, FAINT, 9, ls=1.2))
    b.append(label("ch2", 28, B - 14, COPPER, 11))
    b.append(label("clk", 28, B + 2, FAINT, 9, ls=1.2))
    b.append(label("t 5ms/div   trig ↑", R - 4, T + 16, FAINT, 9, "end", 1.6))
    css = "@keyframes clk{from{transform:translateX(0)}to{transform:translateX(%dpx)}}" % period
    return svg(W, H, "".join(b), css, "Oscilloscope trace")


# ---------------------------------------------------------------- project cards
def wrap(s, font, size, maxw):
    lines, cur = [], ""
    for w in s.split():
        t = (cur + " " + w).strip()
        if font.width(t, size) > maxw and cur:
            lines.append(cur)
            cur = w
        else:
            cur = t
    lines.append(cur)
    return lines


def glyph_mowr(cx, cy):
    g = [f'<rect x="{cx-70}" y="{cy-58}" width="140" height="108" rx="12" fill="{BG2}" stroke="{EDGE}"/>',
         f'<circle cx="{cx-56}" cy="{cy-45}" r="3" fill="{FAINT}"/><circle cx="{cx-46}" cy="{cy-45}" r="3" fill="{FAINT}"/>']
    # message bubbles appear in sequence
    rows = [(cx - 56, cy - 28, 74, COPPER_D), (cx - 18, cy - 10, 74, "#24453C"), (cx - 56, cy + 8, 52, COPPER_D)]
    for i, (x, y, w, c) in enumerate(rows):
        g.append(f'<rect x="{x}" y="{y}" width="{w}" height="12" rx="6" fill="{c}" '
                 f'style="opacity:0;animation:msg 6s {i*0.9}s infinite"/>')
    for i in range(3):
        g.append(f'<circle cx="{cx-50+i*11}" cy="{cy+34}" r="3.6" fill="{TEAL}" '
                 f'style="animation:dot 1.2s {i*0.18}s ease-in-out infinite"/>')
    css = ("@keyframes msg{0%{opacity:0;transform:translateY(6px)}8%,80%{opacity:1;transform:none}92%,100%{opacity:0}}"
           "@keyframes dot{0%,100%{transform:translateY(0);opacity:.4}40%{transform:translateY(-5px);opacity:1}}")
    return "".join(g), css


def glyph_blend(cx, cy):
    cols = [COPPER, TEAL, CREAM]
    g = [f'<g style="transform-origin:{cx}px {cy}px;animation:spin 14s linear infinite">']
    for i, c in enumerate(cols):
        a = i * 2 * math.pi / 3
        x, y = cx + 22 * math.cos(a), cy + 22 * math.sin(a)
        g.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="38" fill="{c}" opacity=".55" '
                 f'style="mix-blend-mode:screen;transform-origin:{x:.1f}px {y:.1f}px;animation:breathe 4s {i*1.3}s ease-in-out infinite"/>')
    g.append("</g>")
    css = ("@keyframes spin{to{transform:rotate(360deg)}}"
           "@keyframes breathe{0%,100%{transform:scale(.82)}50%{transform:scale(1.06)}}")
    return "".join(g), css


def glyph_check(cx, cy):
    g = []
    for i in range(4):
        y = cy - 45 + i * 30
        g.append(f'<rect x="{cx-62}" y="{y-9}" width="18" height="18" rx="4" fill="none" stroke="{EDGE}" stroke-width="2"/>')
        g.append(f'<rect x="{cx-34}" y="{y-3}" width="{[86,64,92,70][i]}" height="6" rx="3" fill="{GRID}"/>')
        g.append(f'<path d="M{cx-58},{y} l4,5 l8,-10" pathLength="10" fill="none" stroke="{LED}" stroke-width="2.6" '
                 f'stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="10" '
                 f'style="animation:tick 6s {0.5+i*0.7}s infinite;stroke-dashoffset:10"/>')
    css = "@keyframes tick{0%{stroke-dashoffset:10}10%,85%{stroke-dashoffset:0}95%,100%{stroke-dashoffset:10}}"
    return "".join(g), css


def glyph_gauge(cx, cy):
    r = 58
    cy += 18

    def pt(a, rr=r):
        return cx + rr * math.cos(a), cy + rr * math.sin(a)
    a0, a1 = math.pi, 2 * math.pi
    sx, sy = pt(a0)
    ex, ey = pt(a1)
    arc = f"M{sx:.1f},{sy:.1f} A{r},{r} 0 0 1 {ex:.1f},{ey:.1f}"
    g = [f'<path d="{arc}" fill="none" stroke="{GRID}" stroke-width="10" stroke-linecap="round"/>',
         f'<path d="{arc}" pathLength="100" fill="none" stroke="url(#gg)" stroke-width="10" stroke-linecap="round" '
         f'stroke-dasharray="100" style="animation:fill 5s ease-in-out infinite"/>',
         f'<defs><linearGradient id="gg"><stop offset="0" stop-color="{RED}"/><stop offset=".5" stop-color="{COPPER}"/>'
         f'<stop offset="1" stop-color="{LED}"/></linearGradient></defs>']
    for i in range(11):
        a = a0 + (a1 - a0) * i / 10
        x1, y1 = pt(a, r - 16)
        x2, y2 = pt(a, r - 22)
        g.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{FAINT}" stroke-width="1.5"/>')
    g.append(f'<g style="transform-origin:{cx}px {cy}px;animation:needle 5s ease-in-out infinite">'
             f'<line x1="{cx}" y1="{cy}" x2="{cx-44}" y2="{cy}" stroke="{CREAM}" stroke-width="3" stroke-linecap="round"/></g>')
    g.append(f'<circle cx="{cx}" cy="{cy}" r="6" fill="{CREAM}"/>')
    css = ("@keyframes needle{0%{transform:rotate(8deg)}55%{transform:rotate(172deg)}62%{transform:rotate(164deg)}"
           "68%,88%{transform:rotate(168deg)}100%{transform:rotate(8deg)}}"
           "@keyframes fill{0%{stroke-dashoffset:96}55%,88%{stroke-dashoffset:3}100%{stroke-dashoffset:96}}")
    return "".join(g), css


def glyph_grid(cx, cy):
    rnd = random.Random(9)
    g, css = [], ["@keyframes gr{0%,12%{transform:translate(var(--x),var(--y)) rotate(var(--r))}"
                  "40%,82%{transform:none}100%{transform:translate(var(--x),var(--y)) rotate(var(--r))}}"]
    for i in range(9):
        r, c = divmod(i, 3)
        x, y = cx - 46 + c * 32, cy - 46 + r * 32
        dx, dy, rot = rnd.randint(-40, 40), rnd.randint(-30, 30), rnd.randint(-40, 40)
        col = [COPPER, TEAL, CREAM][i % 3]
        g.append(f'<rect x="{x}" y="{y}" width="26" height="26" rx="5" fill="{col}" opacity=".85" '
                 f'style="--x:{dx}px;--y:{dy}px;--r:{rot}deg;transform-box:fill-box;transform-origin:center;'
                 f'animation:gr 6s {i*0.06:.2f}s cubic-bezier(.6,0,.2,1) infinite"/>')
    return "".join(g), "".join(css)


def glyph_pendulum(cx, cy):
    top = cy - 64
    g = [f'<line x1="{cx-50}" y1="{top}" x2="{cx+50}" y2="{top}" stroke="{FAINT}" stroke-width="3"/>']
    for k in range(6):
        g.append(f'<line x1="{cx-46+k*18}" y1="{top}" x2="{cx-54+k*18}" y2="{top-8}" stroke="{FAINT}" stroke-width="1.5"/>')
    arc_r = 104
    a = math.radians(32)
    lx, ly = cx - arc_r * math.sin(a), top + arc_r * math.cos(a)
    rx_, ry_ = cx + arc_r * math.sin(a), top + arc_r * math.cos(a)
    g.append(f'<path d="M{lx:.1f},{ly:.1f} A{arc_r},{arc_r} 0 0 0 {rx_:.1f},{ry_:.1f}" fill="none" stroke="{FAINT}" '
             f'stroke-dasharray="3 5"/>')
    g.append(f'<g style="transform-origin:{cx}px {top}px;animation:swing 2.4s ease-in-out infinite alternate">'
             f'<line x1="{cx}" y1="{top}" x2="{cx}" y2="{top+arc_r}" stroke="{CREAM}" stroke-width="2"/>'
             f'<circle cx="{cx}" cy="{top+arc_r}" r="14" fill="{COPPER}"/>'
             f'<path d="M{cx},{top+arc_r+16} v22" stroke="{TEAL}" stroke-width="2.5" marker-end="url(#ar)"/></g>'
             f'<defs><marker id="ar" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">'
             f'<path d="M0,0 L8,4 L0,8z" fill="{TEAL}"/></marker></defs>')
    css = "@keyframes swing{from{transform:rotate(32deg)}to{transform:rotate(-32deg)}}"
    return "".join(g), css


CARDS = [
    ("mowr", "01 · desktop app", "Mowr", "A local-first AI workspace for Windows. Your chats and files stay on your machine.",
     ["windows", "ai", "preview"], "live", glyph_mowr),
    ("blend", "02 · agent skills", "Blend", "Eleven coordinated frontend skills that give coding agents real design taste.",
     ["codex", "design", "oss"], "oss", glyph_blend),
    ("anti-slop", "03 · agent skill", "anti-slop", "Makes agents finish the details: working forms, accessibility, mobile, metadata.",
     ["codex", "qa", "oss"], "oss", glyph_check),
    ("web-perf", "04 · agent skill", "Web Perf", "Measure first, fix the real bottleneck, keep Core Web Vitals from regressing.",
     ["codex", "performance", "oss"], "oss", glyph_gauge),
    ("repo-tidier", "05 · agent skill", "Repo Tidier", "Turns a messy repository into a clean project without changing how it behaves.",
     ["codex", "hygiene", "oss"], "oss", glyph_grid),
    ("kinetra", "06 · engineering", "Kinetra", "A TypeScript workbench that renders physics and circuit diagrams from JSON.",
     ["typescript", "physics", "circuits"], "proto", glyph_pendulum),
]


def card(slug, tag, title, desc, tags, status, glyph):
    W, H = 600, 250
    b = [board(W, H, 16)]
    b.append(label(tag, 30, 44, COPPER, 11))
    st_col = {"live": LED, "oss": TEAL, "proto": COPPER}[status]
    b.append(led(W - 136, 40, st_col, random.Random(slug).uniform(0, 2), 3.5))
    b.append(label({"live": "live", "oss": "open source", "proto": "prototype"}[status], W - 28, 44, DIM, 10, "end", 1.8))
    b.append(text(DISPLAY, title, 38, 28, 104, CREAM, ls=-.6))
    for i, line in enumerate(wrap(desc, BODY, 16, 340)):
        b.append(text(BODY, line, 16, 30, 140 + i * 24, DIM))
    x = 30
    for t in tags:
        w = MONO.width(t.upper(), 10, 1.6) + 20
        b.append(f'<rect x="{x}" y="196" width="{w:.1f}" height="24" rx="12" fill="none" stroke="{EDGE}"/>')
        b.append(label(t, x + 10, 212, FAINT, 10, ls=1.6))
        x += w + 8
    g, css = glyph(480, 138)
    b.append(g)
    # bottom copper trace with a pulse
    b.append(trace(f"M16,{H-8} H{W-16}", random.Random(slug + "t").uniform(0, 3), 4.2, 1.6))
    pad = 6  # breathing room between cards in the grid
    body = f'<g transform="translate({pad},{pad})">{"".join(b)}</g>'
    return svg(W + 2 * pad, H + 2 * pad, body, css, f"{title} — {desc}")


# ---------------------------------------------------------------- buttons
def button(slug, head, sub, color):
    W, H = 300, 64
    b = [board(W, H, 32)]
    b.append(led(30, 32, color, 0, 4))
    b.append(text(MED, head.upper(), 13, 50, 30, CREAM, ls=2.2))
    b.append(text(MONO, sub, 11, 50, 47, FAINT, ls=.4))
    b.append(text(MED, "→", 18, W - 28, 38, color, "end", extra='style="animation:nudge 1.8s ease-in-out infinite"'))
    b.append(f'<defs><linearGradient id="sh" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
             f'<stop offset=".5" stop-color="#fff" stop-opacity=".07"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>'
             f'</linearGradient><clipPath id="bc"><rect width="{W}" height="{H}" rx="32"/></clipPath></defs>'
             f'<g clip-path="url(#bc)"><rect x="-120" width="110" height="{H}" fill="url(#sh)" '
             f'style="animation:sheen 5s {random.Random(slug).uniform(0,2):.2f}s ease-in-out infinite"/></g>')
    css = ("@keyframes sheen{0%,60%{transform:translateX(0)}100%{transform:translateX(560px)}}"
           "@keyframes nudge{0%,100%{transform:translateX(0)}50%{transform:translateX(4px)}}")
    return svg(W, H, "".join(b), css, f"{head}: {sub}")


# ---------------------------------------------------------------- toolchain
def stack():
    W, H = 1200, 170
    b = [board(W, H, 14)]
    b.append(label("toolchain", 30, 40, COPPER, 11))
    items = ["typescript", "python", "node.js", "html / css", "svg", "codex"]
    n = len(items)
    cw, ch, gap = 150, 64, 30
    total = n * cw + (n - 1) * gap
    x0 = (W - total) / 2
    y = 74
    bus_y = y + ch + 28
    b.append(f'<path d="M{x0-20},{bus_y} H{x0+total+20}" stroke="{COPPER_D}" stroke-width="2"/>')
    b.append(f'<path d="M{x0-20},{bus_y} H{x0+total+20}" pathLength="100" class="pulse" style="animation-duration:3.6s"/>')
    for i, it in enumerate(items):
        x = x0 + i * (cw + gap)
        for k in range(7):
            px = x + 16 + k * (cw - 32) / 6
            b.append(f'<rect x="{px-3:.1f}" y="{y-9}" width="6" height="9" fill="{COPPER_D}"/>')
            b.append(f'<rect x="{px-3:.1f}" y="{y+ch}" width="6" height="9" fill="{COPPER_D}"/>')
        b.append(f'<path d="M{x+cw/2},{y+ch+9} V{bus_y}" stroke="{COPPER_D}" stroke-width="2"/>')
        b.append(f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="6" fill="#141816" stroke="#2A302D"/>')
        b.append(f'<circle cx="{x+12}" cy="{y+12}" r="3" fill="#0B0E0C"/>')
        b.append(text(MED, it.upper(), 12, x + cw / 2, y + ch / 2 + 5, CREAM, "middle", 1.8))
        b.append(f'<circle cx="{x+cw-14}" cy="{y+14}" r="3" fill="{LED}" style="opacity:.15;animation:chase 3s {i*0.5}s infinite"/>')
    css = "@keyframes chase{0%,100%{opacity:.15}8%,22%{opacity:1}}"
    return svg(W, H, "".join(b), css, "Toolchain: TypeScript, Python, Node.js, HTML/CSS, SVG, Codex")


# ---------------------------------------------------------------- 7-segment sign-off
SEG = {  # a b c d e f g
    "H": "0110111", "E": "1001111", "L": "0001110", "O": "1111110", "C": "1001110", "A": "1110111",
    "I": "0110000", "r": "0000101", "G": "1011110", "U": "0111110", "2": "1101101", "0": "1111110",
    "6": "1011111", "-": "0000001", " ": "0000000", "S": "1011011", "Y": "0111011", "b": "0011111",
}


def seven(ch, x, y, w=40, h=72, t=8, on=COPPER, off="#1C2621"):
    bits = SEG[ch]
    hw = h / 2
    segs = [
        (x + t, y, w - 2 * t, t, "h"), (x + w - t, y + t, t, hw - 1.5 * t, "v"),
        (x + w - t, y + hw + t / 2, t, hw - 1.5 * t, "v"), (x + t, y + h - t, w - 2 * t, t, "h"),
        (x, y + hw + t / 2, t, hw - 1.5 * t, "v"), (x, y + t, t, hw - 1.5 * t, "v"),
        (x + t, y + hw - t / 2, w - 2 * t, t, "h"),
    ]
    out = []
    for bit, (sx, sy, sw, sh, _) in zip(bits, segs):
        out.append(f'<rect x="{sx:.1f}" y="{sy:.1f}" width="{sw:.1f}" height="{sh:.1f}" rx="{t/2}" '
                   f'fill="{on if bit=="1" else off}"/>')
    return "".join(out)


def footer():
    W, H = 1200, 180
    b = [board(W, H, 14)]
    words = ["HELLO ", "CAIrO ", "2026  ", "SEE YA"]
    x0, y0, w, gap = 70, 54, 44, 18
    # unlit background digits
    for i in range(6):
        b.append(seven(" ", x0 + i * (w + gap), y0, w))
    T = 8
    for k, wd in enumerate(words):
        g = "".join(seven(c, x0 + i * (w + gap), y0, w, off="none") for i, c in enumerate(wd))
        b.append(f'<g filter="url(#glow)" style="opacity:0;animation:word {T}s {k*T/len(words)}s steps(1) infinite">{g}</g>')
    right = x0 + 6 * (w + gap) + 40
    b.append(f'<line x1="{right-20}" y1="44" x2="{right-20}" y2="136" stroke="{EDGE}"/>')
    b.append(text(DISPLAY, "Thanks for stopping by.", 34, right + 10, 92, CREAM, ls=-.4))
    b.append(label("© 2026 mohamed mowafy  ·  made with copper and code", right + 12, 124, FAINT, 10, ls=1.8))
    css = "@keyframes word{0%{opacity:1}25%,100%{opacity:0}}"
    return svg(W, H, "".join(b), css, "Thanks for stopping by")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    write("hero.svg", hero())
    write("scope.svg", scope())
    for c in CARDS:
        write(f"card-{c[0]}.svg", card(*c))
    write("btn-site.svg", button("site", "Website", "mohamedmowafy.com", LED))
    write("btn-mowr.svg", button("mowr", "Mowr", "mowrai.com", TEAL))
    write("btn-download.svg", button("dl", "Download", "Mowr for Windows · preview", COPPER))
    write("stack.svg", stack())
    write("footer.svg", footer())
