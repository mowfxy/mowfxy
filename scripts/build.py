"""Generate the animated SVGs for the mowfxy profile README.

Everything is drawn as a terminal: monospaced text and ASCII frames, animated
with plain CSS so GitHub plays it inside an <img>. JetBrains Mono (OFL) is
subset per file and embedded as WOFF2, so it renders the same everywhere.

    pip install fonttools brotli pillow
    python3 scripts/build.py            # MONO_DIR=/path/to/jetbrains-mono to override
"""
import base64, io, math, os
from fontTools import subset
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets")
MONO = os.environ.get("MONO_DIR", "/usr/share/fonts/truetype/jetbrains-mono")
SERIF = os.environ.get("KERN_FONT", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf")

C = dict(bg="#0b0e0c", panel="#0e1210", line="#232b26", faint="#2c3630", grid="#17201b",
         text="#e8ede9", soft="#b7c0ba", dim="#748079",
         green="#7dffb0", amber="#ffc46b", blue="#8fd0ff", pink="#ff9fcf", red="#ff7a6b")
CW = 0.6  # JetBrains Mono advance, in em


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class SVG:
    """One SVG file: collects elements, the glyphs it uses and its CSS."""

    def __init__(self, w, h, title):
        self.w, self.h, self.title = w, h, title
        self.body, self.css, self.chars = [], [], {400: set(), 700: set()}
        self.n = 0

    def add(self, s):
        self.body.append(s)

    def uid(self, p="a"):
        self.n += 1
        return f"{p}{self.n}"

    def text(self, x, y, s, size=12, fill=C["text"], weight=400, anchor="start", extra=""):
        self.chars[weight].update(s)
        a = f' text-anchor="{anchor}"' if anchor != "start" else ""
        w = ' font-weight="700"' if weight == 700 else ""
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}"{w}{a} {extra}>{esc(s)}</text>')

    def spans(self, x, y, rows, size, lh, palette, default):
        """Rows of ASCII. Each row is a string, or (string, colour-key string)."""
        cw = size * CW
        out = []
        for i, row in enumerate(rows):
            s, keys = (row if isinstance(row, tuple) else (row, None))
            j = 0
            while j < len(s):
                k = keys[j] if keys else None
                e = j
                while e < len(s) and (keys[e] if keys else None) == k:
                    e += 1
                run = s[j:e]
                lead = len(run) - len(run.lstrip(" "))
                body = run.strip(" ")
                if body:
                    self.chars[400].update(body)
                    fill = f' fill="{palette[k]}"' if k and k in palette else ""
                    out.append(f'<tspan x="{x + (j + lead) * cw:.1f}" y="{y + i * lh:.1f}"{fill}>{esc(body)}</tspan>')
                j = e
        return f'<text font-size="{size}" fill="{default}">{"".join(out)}</text>'

    def frames(self, frames, x, y, size, lh, dur, fill, palette=None, start=0.0, wrap=""):
        """A looping flip-book: one group per frame, each shown for dur/len(frames)."""
        key = self.uid("f")
        n = len(frames)
        p = 100 / n
        self.css.append(f"@keyframes {key}{{0%,{p - .001:.3f}%{{opacity:1}}{p:.3f}%,100%{{opacity:0}}}}"
                        f".{key}{{opacity:0;animation:{key} {dur}s linear infinite}}")
        gs = []
        for k, fr in enumerate(frames):
            st = f"animation-delay:{start + k * dur / n:.3f}s" + (";opacity:1" if k == 0 else "")
            gs.append(f'<g class="{key}" style="{st}">{self.spans(x, y, fr, size, lh, palette or {}, fill)}</g>')
        self.add(f"<g{wrap}>{''.join(gs)}</g>")

    def font_css(self):
        css = []
        for weight, chars in self.chars.items():
            chars = chars | {" "}
            if len(chars) <= 1:
                continue
            name = "Regular" if weight == 400 else "Bold"
            f = TTFont(f"{MONO}/JetBrainsMono-{name}.ttf")
            opts = subset.Options()
            opts.flavor, opts.layout_features, opts.name_IDs = "woff2", [], []
            opts.hinting = False
            s = subset.Subsetter(opts)
            s.populate(text="".join(chars))
            s.subset(f)
            buf = io.BytesIO()
            f.flavor = "woff2"
            f.save(buf)
            b64 = base64.b64encode(buf.getvalue()).decode()
            css.append(f"@font-face{{font-family:M;font-weight:{weight};src:url(data:font/woff2;base64,{b64}) format('woff2')}}")
        return "".join(css)

    def render(self):
        css = (self.font_css() + "text{font-family:M,ui-monospace,monospace;white-space:pre}"
               + "".join(self.css) + "@media (prefers-reduced-motion:reduce){*{animation:none!important}}")
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" '
                f'role="img" aria-label="{esc(self.title)}"><title>{esc(self.title)}</title><style>{css}</style>'
                + "".join(self.body) + "</svg>")


def scanlines(svg, x, y, w, h, r):
    pid, cid = svg.uid("p"), svg.uid("c")
    svg.add(f'<defs><pattern id="{pid}" width="4" height="3" patternUnits="userSpaceOnUse">'
            f'<rect width="4" height="1" fill="#000" opacity=".22"/></pattern>'
            f'<clipPath id="{cid}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}"/></clipPath></defs>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#{pid})" clip-path="url(#{cid})" pointer-events="none"/>')


def glow(svg):
    fid = svg.uid("g")
    svg.add(f'<defs><filter id="{fid}" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="2.2" result="b"/>'
            f'<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>')
    return f' filter="url(#{fid})"'


def ramp(v, chars=" .,:;=+*#%@"):
    v = max(0.0, min(1.0, v))
    return chars[min(len(chars) - 1, int(v * (len(chars) - 1) + .5))]


def ease(t):
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ ASCII scenes
def lissajous(cols, rows, n):
    """An oscilloscope in XY mode: a 3:2 Lissajous figure drifting in phase, with phosphor trails."""
    out = []
    for k in range(n):
        acc = [[0.0] * cols for _ in range(rows)]
        for trail, w in ((0, 1.0), (1, .45), (2, .22), (3, .1)):
            ph = 2 * math.pi * (k - trail * .55) / n
            for i in range(1400):
                t = 2 * math.pi * i / 1400
                x = math.sin(3 * t + ph)
                y = math.sin(2 * t)
                cx = int((x * .47 + .5) * (cols - 1) + .5)
                cy = int((-y * .44 + .5) * (rows - 1) + .5)
                acc[cy][cx] = max(acc[cy][cx], w)
        out.append(["".join(ramp(v, " .:-+*#") if v else " " for v in r) for r in acc])
    return out


def sparkline(width, n):
    bars = " ▁▂▃▄▅▆▇█"
    out = []
    for k in range(n):
        ph = 2 * math.pi * k / n
        s = "".join(bars[1 + int(3.5 + 3.5 * (.65 * math.sin(i * .55 - ph) + .35 * math.sin(i * 1.3 - 2 * ph)))]
                    for i in range(width))
        out.append([s])
    return out


def ripples(cols, rows, n, aspect=2.1):
    out = []
    srcs = [(.3, .55, 0.0), (.74, .4, 1.7)]
    for k in range(n):
        ph = 2 * math.pi * k / n
        fr = []
        for j in range(rows):
            line = ""
            for i in range(cols):
                v = 0
                for sx, sy, off in srcs:
                    d = math.hypot((i - sx * cols) / aspect, j - sy * rows)
                    v += math.sin(d * 1.05 - ph * 2 + off) * math.exp(-d / 9)
                line += ramp((v + .9) / 2.2, "  .·-~=≈")
            fr.append(line)
        out.append(fr)
    return out


def kern_word(cols, rows, n, word="Kern"):
    """The word rasterised into ASCII, its letters drifting apart and kerning back together."""
    sx, sy = 4, 8
    W, H = cols * sx, rows * sy
    font = ImageFont.truetype(SERIF, int(H * .92))
    widths = [font.getlength(ch) for ch in word]
    tight = [-W * .012, -W * .006, -W * .004]  # optical kerning, a hair negative
    out = []
    for k in range(n):
        t = ease(.5 - .5 * math.cos(2 * math.pi * k / n))
        gap = [g * (1 - t) + W * .07 * t for g in tight]
        total = sum(widths) + sum(gap)
        x = (W - total) / 2
        im = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(im)
        for i, ch in enumerate(word):
            d.text((x, H * .45), ch, font=font, fill=255, anchor="lm")
            x += widths[i] + (gap[i] if i < len(gap) else 0)
        px = im.load()
        fr = []
        for j in range(rows):
            line = ""
            for i in range(cols):
                v = sum(px[i * sx + a, j * sy + b] for a in range(sx) for b in range(sy)) / (255 * sx * sy)
                line += ramp(v, " .:-=+*#%@") if v > .04 else " "
            fr.append(line)
        out.append(fr)
    return out


def checklist(n_items=("forms that submit", "keyboard + a11y", "mobile layout", "meta + og tags")):
    seq = [0, 1, 2, 3, 4, 4, 4, 4]
    out = []
    for done in seq:
        fr = []
        for i, label in enumerate(n_items):
            box = "[x]" if i < done else "[ ]"
            s = f"{box} {label}"
            keys = ("g" if i < done else "d") * 3 + " " + ("t" if i < done else "d") * len(label)
            fr.append((s, keys))
        out.append(fr)
    return out


def vitals(n=24):
    rows = [("LCP", 4.2, 1.1, "s"), ("INP", 380, 90, "ms"), ("CLS", .31, .02, "")]
    full = 14
    out = []
    for k in range(n):
        t = ease(min(1, k / (n * .6)))
        fr = []
        for name, a, b, unit in rows:
            v = a + (b - a) * t
            ln = max(1, round(full * (v / a)))
            val = f"{v:.2f}" if unit == "" else (f"{v:.1f}{unit}" if unit == "s" else f"{v:.0f}{unit}")
            bar = "█" * ln + "░" * (full - ln)
            col = "r" if t < .4 else ("a" if t < .85 else "g")
            s = f"{name} {bar} {val}"
            keys = "d" * 4 + col * ln + "f" * (full - ln) + " " + "t" * len(val)
            fr.append((s, keys))
        out.append(fr)
    return out


def pendulum(cols, rows, n, aspect=1.75):
    out = []
    px = cols // 2
    L = rows - 2.2
    for k in range(n):
        th = .62 * math.cos(2 * math.pi * k / n)
        g = [[" "] * cols for _ in range(rows)]
        keys = [[" "] * cols for _ in range(rows)]
        for i in range(px - 7, px + 8):
            g[0][i], keys[0][i] = "▔", "d"
        steps = 40
        for s in range(1, steps):
            r = L * s / steps
            x = px + r * math.sin(th) * aspect
            y = .6 + r * math.cos(th)
            ci, cj = int(round(x)), int(round(y))
            if 0 <= cj < rows and 0 <= ci < cols and g[cj][ci] == " ":
                g[cj][ci] = "·"
                keys[cj][ci] = "d"
        bx = int(round(px + (L + .5) * math.sin(th) * aspect))
        by = int(round(.6 + (L + .5) * math.cos(th)))
        by = min(rows - 1, by)
        g[by][bx], keys[by][bx] = "●", "p"
        # faint arc of the swing
        for a in range(-12, 13):
            aa = .62 * a / 12
            ax = int(round(px + (L + .5) * math.sin(aa) * aspect))
            ay = min(rows - 1, int(round(.6 + (L + .5) * math.cos(aa))))
            if g[ay][ax] == " ":
                g[ay][ax], keys[ay][ax] = "·", "f"
        out.append([("".join(r), "".join(c)) for r, c in zip(g, keys)])
    return out


def globe(cols, rows, n, aspect=1.8):
    out = []
    R = rows / 2 - .3
    cx, cy = cols / 2 - .5, rows / 2 - .5
    lx, ly, lz = -.5, -.45, .74
    for k in range(n):
        rot = 2 * math.pi * k / n
        fr, ks = [], []
        for j in range(rows):
            line, kl = "", ""
            for i in range(cols):
                x = (i - cx) / aspect / R
                y = (j - cy) / R
                d = x * x + y * y
                if d > 1:
                    line += " "; kl += " "
                    continue
                z = math.sqrt(1 - d)
                lat = math.asin(-y)
                lon = math.atan2(x, z) + rot
                shade = max(0, x * lx + y * ly + z * lz)
                on_grid = (abs(math.sin(lon * 3)) < .28) or (abs(math.sin(lat * 3)) < .2)
                if on_grid:
                    line += ramp(.45 + .55 * shade, " .:-=+*#")
                    kl += "b"
                else:
                    line += ramp(.2 + .45 * shade, " .:-=")
                    kl += "f"
            fr.append((line, kl))
        out.append(fr)
    return out


# ------------------------------------------------------------------ hero
def hero():
    W, H = 1000, 452
    s = SVG(W, H, "A terminal window. The command mowfxy --hello opens a panel: an oscilloscope drawing a drifting "
                  "Lissajous figure in ASCII, next to Mohamed Mowafy, electronics engineering student in Cairo, "
                  "having fun between the soldering iron and the terminal.")
    s.add(f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="14" fill="{C["bg"]}" stroke="{C["line"]}"/>')
    # title bar
    s.add(f'<path d="M14 .5H{W-14}a13.5 13.5 0 0 1 13.5 13.5V38H.5V14A13.5 13.5 0 0 1 14 .5Z" fill="{C["panel"]}"/>'
          f'<line x1="1" y1="38.5" x2="{W-1}" y2="38.5" stroke="{C["line"]}"/>')
    for i, col in enumerate(("#3a4540", "#3a4540", "#3a4540")):
        s.add(f'<circle cx="{22 + i * 18}" cy="19.5" r="5.5" fill="{col}"/>')
    s.text(W / 2, 24, "mowfxy@cairo: ~", 12, C["dim"], anchor="middle")

    # prompt + typed command
    y0 = 72
    s.text(26, y0, "~ ❯", 15, C["green"], 700)
    cmd = "mowfxy --hello"
    s.text(66, y0, cmd, 15, C["text"])
    cw = 15 * CW
    s.css.append(f"@keyframes ty{{from{{transform:translateX(0)}}to{{transform:translateX({len(cmd) * cw:.1f}px)}}}}"
                 f".ty{{animation:ty 1.1s steps({len(cmd)}) .4s both}}"
                 f"@keyframes cur{{0%,49%{{opacity:1}}50%,100%{{opacity:0}}}}.cur{{animation:cur 1s steps(1) infinite}}"
                 f"@keyframes cmv{{from{{transform:translateX(0)}}to{{transform:translateX({len(cmd) * cw:.1f}px)}}}}"
                 f".cmv{{animation:cmv 1.1s steps({len(cmd)}) .4s both}}"
                 f"@keyframes pin{{0%{{opacity:0}}30%{{opacity:.6}}40%{{opacity:.15}}100%{{opacity:1}}}}"
                 f".pin{{animation:pin .7s ease-out 1.65s both}}")
    s.add(f'<rect class="ty" x="64" y="{y0-16}" width="{len(cmd)*cw+6:.1f}" height="22" fill="{C["bg"]}"/>')
    s.add(f'<g class="cmv"><rect class="cur" x="66" y="{y0-14}" width="9" height="18" fill="{C["green"]}" opacity=".85"/></g>')

    # panel
    px, py, pw, ph = 24, 96, W - 48, 314
    s.add('<g class="pin">')
    s.add(f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="10" fill="none" stroke="{C["faint"]}"/>')
    s.add(f'<rect x="{px+18}" y="{py-8}" width="{len(" hello, world ")*7.2+4:.0f}" height="16" fill="{C["bg"]}"/>')
    s.text(px + 20, py + 4, " hello, world ", 12, C["green"])

    # oscilloscope
    cols, rows, fs, lh = 50, 21, 12, 12.6
    ox, oy = px + 26, py + 34
    gw, gh = cols * fs * CW, rows * lh
    for i in range(11):
        x = ox + gw * i / 10
        s.add(f'<line x1="{x:.1f}" y1="{oy-12}" x2="{x:.1f}" y2="{oy-12+gh:.1f}" stroke="{C["grid"]}" '
              f'stroke-dasharray="{"0" if i in (0, 5, 10) else "2 4"}"/>')
    for j in range(9):
        y = oy - 12 + gh * j / 8
        s.add(f'<line x1="{ox}" y1="{y:.1f}" x2="{ox+gw:.1f}" y2="{y:.1f}" stroke="{C["grid"]}" '
              f'stroke-dasharray="{"0" if j in (0, 4, 8) else "2 4"}"/>')
    s.frames(lissajous(cols, rows, 48), ox, oy, fs, lh, 4.8, C["green"], start=1.65, wrap=glow(s))
    s.text(ox, oy - 12 + gh + 20, "CH1 X  3 kHz", 11, C["dim"])
    s.text(ox + gw, oy - 12 + gh + 20, "CH2 Y  2 kHz   XY", 11, C["dim"], anchor="end")

    # about
    ax = px + 448
    s.text(ax, py + 62, "Mohamed Mowafy", 34, C["text"], 700, extra='letter-spacing="-1"')
    s.text(ax, py + 90, "electronics engineering student · cairo", 13, C["green"])
    s.text(ax, py + 128, "Just having fun somewhere between the", 14, C["soft"])
    s.text(ax, py + 149, "soldering iron and the terminal.", 14, C["soft"])
    kv = [("builds", "desktop apps, agent skills, diagram tools"),
          ("now", "Clem — a calm workspace for Windows"),
          ("site", "mohamedmowafy.com")]
    for i, (k, v) in enumerate(kv):
        y = py + 192 + i * 24
        s.text(ax, y, k, 13, C["dim"])
        s.text(ax + 72, y, v, 13, C["text"] if k != "site" else C["blue"])
    s.text(ax, py + 280, "signal", 13, C["dim"])
    s.frames(sparkline(30, 24), ax + 72, py + 280, 13, 14, 2.4, C["amber"], start=1.65)
    s.add("</g>")

    # status bar
    sy = H - 30
    s.add(f'<path d="M.5 {sy}H{W-.5}V{H-14}a13.5 13.5 0 0 1-13.5 13.5H14A13.5 13.5 0 0 1 .5 {H-14}Z" fill="{C["panel"]}"/>'
          f'<line x1="1" y1="{sy}" x2="{W-1}" y2="{sy}" stroke="{C["line"]}"/>')
    s.add(f'<circle cx="24" cy="{sy+15}" r="4" fill="{C["green"]}"/>')
    s.css.append("@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}.pulse{animation:pulse 2s ease-in-out infinite}")
    s.add(f'<circle class="pulse" cx="24" cy="{sy+15}" r="8" fill="none" stroke="{C["green"]}" opacity=".5"/>')
    s.text(38, sy + 19, "tinkering", 11, C["soft"])
    s.text(120, sy + 19, "1:scope*  2:clem  3:kern  4:kinetra", 11, C["dim"])
    s.text(W - 22, sy + 19, "utf-8  ·  zsh  ·  ♥", 11, C["dim"], anchor="end")
    scanlines(s, 0, 0, W, H, 14)
    return s.render()


# ------------------------------------------------------------------ tiles
def wrap_words(t, n):
    lines, cur = [], ""
    for w in t.split():
        if cur and len(cur) + 1 + len(w) > n:
            lines.append(cur); cur = w
        else:
            cur = f"{cur} {w}".strip()
    return lines + [cur]


def tile(big, name, tag, desc, scene, accent, alt):
    W, H = (423, 250) if big else (211, 156)
    cw, chh = W - 10, H - 6
    s = SVG(W, H, alt)
    s.add(f'<g transform="translate(5 0)">')
    s.add(f'<rect x=".5" y=".5" width="{cw-1}" height="{chh-1}" rx="12" fill="{C["bg"]}" stroke="{C["line"]}"/>')
    scene(s)
    if big:
        s.text(18, 30, f"~/{name.lower()}", 11, C["dim"])
        s.text(cw - 18, 30, tag, 11, accent, anchor="end")
        s.add(f'<line x1="18" y1="{chh-74}" x2="{cw-18}" y2="{chh-74}" stroke="{C["line"]}" stroke-dasharray="2 3"/>')
        s.text(18, chh - 46, name, 19, C["text"], 700)
        s.text(cw - 18, chh - 46, "↗", 16, C["dim"], anchor="end")
        for i, ln in enumerate(wrap_words(desc, 58)[:2]):
            s.text(18, chh - 26 + i * 15, ln, 11, C["soft"])
    else:
        s.text(14, 24, tag, 9.5, accent)
        s.text(cw - 14, 24, "↗", 12, C["dim"], anchor="end")
        s.text(14, chh - 30, name, 14, C["text"], 700)
        for i, ln in enumerate(wrap_words(desc, 31)[:2]):
            s.text(14, chh - 15 + i * 11, ln, 9, C["soft"])
    s.add("</g>")
    scanlines(s, 5, 0, cw, chh, 12)
    return s.render()


WORK = [
    dict(slug="clem", big=True, name="Clem", tag="desktop app", accent=C["blue"],
         desc="A calm, local-first workspace for Windows, powered by the AI plan you already have.",
         scene=lambda s: s.frames(ripples(64, 9, 40), 18, 58, 10, 11.5, 6, C["blue"])),
    dict(slug="kern", big=True, name="Kern", tag="agent skills", accent=C["amber"],
         desc="A design practice for coding agents: taste, method and craft for every interface.",
         scene=lambda s: s.frames(kern_word(64, 10, 36), 18, 54, 10, 10.5, 5, C["amber"])),
    dict(slug="anti-slop", big=False, name="anti-slop", tag="agent skill", accent=C["green"],
         desc="Makes agents finish the details.",
         scene=lambda s: s.frames(checklist(), 14, 50, 9.5, 14, 6.4, C["dim"],
                                  {"g": C["green"], "t": C["text"], "d": C["dim"]})),
    dict(slug="web-perf", big=False, name="Web Perf", tag="agent skill", accent=C["amber"],
         desc="Measure first, fix the real bottleneck.",
         scene=lambda s: s.frames(vitals(), 14, 56, 9.5, 16, 5, C["dim"],
                                  {"r": C["red"], "a": C["amber"], "g": C["green"], "t": C["text"],
                                   "d": C["dim"], "f": C["faint"]})),
    dict(slug="kinetra", big=False, name="Kinetra", tag="engineering", accent=C["pink"],
         desc="Physics + circuit diagrams from JSON.",
         scene=lambda s: s.frames(pendulum(33, 7, 32), 14, 42, 9, 10, 2.6, C["dim"],
                                  {"p": C["pink"], "d": C["soft"], "f": C["faint"]})),
    dict(slug="site", big=False, name="mohamedmowafy.com", tag="website", accent=C["blue"],
         desc="Where the rest of it lives.",
         scene=lambda s: s.frames(globe(36, 9, 36), 14, 40, 8.5, 8.8, 7.2, C["dim"],
                                  {"b": C["blue"], "f": C["faint"]})),
]
LINKS = {"clem": "https://github.com/mowfxy/clem", "kern": "https://github.com/mowfxy/kern",
         "anti-slop": "https://github.com/mowfxy/anti-slop", "web-perf": "https://github.com/mowfxy/web-perf",
         "kinetra": "https://github.com/mowfxy/kinetra", "site": "https://mohamedmowafy.com"}


# ------------------------------------------------------------------ footer
def footer():
    W, H = 1000, 64
    s = SVG(W, H, "~ exit. Thanks for stopping by, probably tinkering with something right now.")
    s.add(f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="12" fill="{C["bg"]}" stroke="{C["line"]}"/>')
    s.text(26, 37, "~ ❯", 14, C["green"], 700)
    s.text(64, 37, "exit", 14, C["text"])
    s.text(120, 37, "# thanks for stopping by — probably tinkering with something right now", 14, C["dim"])
    s.css.append("@keyframes cur{0%,49%{opacity:1}50%,100%{opacity:0}}.cur{animation:cur 1s steps(1) infinite}")
    s.add(f'<rect class="cur" x="{120 + 72 * 14 * CW + 6:.1f}" y="23" width="8.4" height="18" fill="{C["green"]}" opacity=".85"/>')
    scanlines(s, 0, 0, W, H, 12)
    return s.render()


def readme():
    def tile_tag(w):
        width = 423 if w["big"] else 211
        return (f'<a href="{LINKS[w["slug"]]}"><img src="assets/tile-{w["slug"]}.svg" width="{width}" '
                f'alt="{w["name"]}: {w["desc"]}"></a>')
    return "\n".join([
        '<img src="assets/hero.svg" width="100%" alt="A terminal window. The command mowfxy --hello opens a panel with an '
        'ASCII oscilloscope drawing a Lissajous figure, next to: Mohamed Mowafy, electronics engineering student in Cairo, '
        'having fun between the soldering iron and the terminal.">',
        "",
        '<p align="center"><a href="https://mohamedmowafy.com">mohamedmowafy.com</a> &nbsp;·&nbsp; '
        '<a href="https://github.com/mowfxy?tab=repositories">all repositories</a></p>',
        "",
        '<p align="center">' + "".join(tile_tag(w) for w in WORK) + "</p>",
        "",
        '<img src="assets/footer.svg" width="100%" alt="exit. Thanks for stopping by, probably tinkering with something right now.">',
        "",
        "<!-- Generated by scripts/build.py. Set in JetBrains Mono (OFL). -->",
        "",
    ])


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))
    files = {"hero.svg": hero(), "footer.svg": footer()}
    for w in WORK:
        files[f"tile-{w['slug']}.svg"] = tile(w["big"], w["name"], w["tag"], w["desc"], w["scene"], w["accent"],
                                               f"{w['name']}: {w['desc']}")
    for name, content in files.items():
        with open(os.path.join(OUT, name), "w") as f:
            f.write(content)
        print(f"{name:24} {len(content) / 1024:7.1f} KB")
    with open(os.path.join(HERE, "..", "README.md"), "w") as f:
        f.write(readme())
