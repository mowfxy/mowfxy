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
        self.serif = set()
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
        if self.serif:
            f = TTFont(SERIF)
            opts = subset.Options()
            opts.flavor, opts.layout_features, opts.name_IDs, opts.hinting = "woff2", [], [], False
            sub = subset.Subsetter(opts)
            sub.populate(text="".join(self.serif))
            sub.subset(f)
            buf = io.BytesIO()
            f.flavor = "woff2"
            f.save(buf)
            b64 = base64.b64encode(buf.getvalue()).decode()
            css.append(f"@font-face{{font-family:S;src:url(data:font/woff2;base64,{b64}) format('woff2')}}")
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
            f'<rect width="4" height="1" fill="#000" opacity=".14"/></pattern>'
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


# ------------------------------------------------------------------ scenes
def ripples(cols, rows, n, aspect=2.1):
    """Calm water in ASCII: two slow ripples crossing."""
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


def scope(s, x, y, w, h, start):
    """A vector oscilloscope in XY mode: a 3:2 Lissajous trace with a bright beam running along it."""
    for i in range(11):
        gx = x + w * i / 10
        s.add(f'<line x1="{gx:.1f}" y1="{y}" x2="{gx:.1f}" y2="{y+h}" stroke="{C["grid"]}" '
              f'stroke-dasharray="{"0" if i in (0, 5, 10) else "2 4"}"/>')
    for j in range(9):
        gy = y + h * j / 8
        s.add(f'<line x1="{x}" y1="{gy:.1f}" x2="{x+w}" y2="{gy:.1f}" stroke="{C["grid"]}" '
              f'stroke-dasharray="{"0" if j in (0, 4, 8) else "2 4"}"/>')
    pts, n = [], 720
    for i in range(n + 1):
        t = 2 * math.pi * i / n
        pts.append((x + w / 2 + math.sin(3 * t + .6) * w * .42, y + h / 2 - math.sin(2 * t) * h * .4))
    d = "M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in pts)
    L = sum(math.dist(pts[i], pts[i + 1]) for i in range(n))
    g = glow(s)
    s.css.append(f"@keyframes beam{{from{{stroke-dashoffset:0}}to{{stroke-dashoffset:-{L:.0f}}}}}"
                 f".beam{{animation:beam 4s linear {start}s infinite}}")
    s.add(f'<path d="{d}" fill="none" stroke="{C["green"]}" stroke-width="1.2" opacity=".22"/>')
    s.add(f'<g{g}><path class="beam" d="{d}" fill="none" stroke="{C["green"]}" stroke-width="2.4" '
          f'stroke-linecap="round" stroke-dasharray="{L*.22:.0f} {L*.78:.0f}"/>'
          f'<path class="beam" d="{d}" fill="none" stroke="#e9fff2" stroke-width="2.4" stroke-linecap="round" '
          f'stroke-dasharray="1 {L-1:.0f}" style="animation-delay:{start}s;stroke-dashoffset:-{L*.22:.0f}"/></g>')


def kern_scene(s, x, y, w, size=96, word="Kern"):
    """Real letters on a baseline, drifting apart and kerning back together, with sidebearing guides."""
    s.serif.update(word)
    font = ImageFont.truetype(SERIF, size)
    widths = [font.getlength(ch) for ch in word]
    tight = [-size * .05, -size * .02, -size * .01]
    loose = size * .12
    xs, cx = [], 0
    for i, wd in enumerate(widths):
        xs.append(cx)
        cx += wd + (tight[i] if i < len(tight) else 0)
    x0 = x + (w - cx) / 2
    mid = (len(word) - 1) / 2
    base = y
    s.add(f'<line x1="{x}" y1="{base}" x2="{x+w}" y2="{base}" stroke="{C["faint"]}"/>'
          f'<line x1="{x}" y1="{base-size*.53:.1f}" x2="{x+w}" y2="{base-size*.53:.1f}" stroke="{C["faint"]}" stroke-dasharray="2 4"/>'
          f'<line x1="{x}" y1="{base-size*.73:.1f}" x2="{x+w}" y2="{base-size*.73:.1f}" stroke="{C["faint"]}" stroke-dasharray="2 4"/>')
    for i, ch in enumerate(word):
        dx = (i - mid) * loose
        k = s.uid("k")
        s.css.append(f"@keyframes {k}{{0%,18%,100%{{transform:translateX(0)}}50%,68%{{transform:translateX({dx:.1f}px)}}}}"
                     f".{k}{{animation:{k} 5s cubic-bezier(.65,0,.35,1) infinite}}")
        lx = x0 + xs[i]
        guide = (f'<line x1="{lx+widths[i]:.1f}" y1="{base-size*.82:.1f}" x2="{lx+widths[i]:.1f}" y2="{base+10}" '
                 f'stroke="{C["amber"]}" stroke-width="1" opacity=".55"/>') if i < len(word) - 1 else ""
        s.add(f'<g class="{k}"><text x="{lx:.1f}" y="{base}" font-size="{size}" fill="{C["text"]}" '
              f'style="font-family:S,Georgia,serif">{esc(ch)}</text>{guide}</g>')


# ------------------------------------------------------------------ hero
def hero():
    W, H = 1000, 340
    s = SVG(W, H, "A terminal window running mowfxy --hello: an oscilloscope tracing a Lissajous figure next to "
                  "Mohamed Mowafy, electronics engineering student in Cairo.")
    s.add(f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="14" fill="{C["bg"]}" stroke="{C["line"]}"/>')
    s.add(f'<path d="M14 .5H{W-14}a13.5 13.5 0 0 1 13.5 13.5V38H.5V14A13.5 13.5 0 0 1 14 .5Z" fill="{C["panel"]}"/>'
          f'<line x1="1" y1="38.5" x2="{W-1}" y2="38.5" stroke="{C["line"]}"/>')
    for i in range(3):
        s.add(f'<circle cx="{22 + i * 18}" cy="19.5" r="5.5" fill="#3a4540"/>')
    s.text(W / 2, 24, "mowfxy@cairo: ~", 12, C["dim"], anchor="middle")

    y0 = 74
    s.text(28, y0, "~ ❯", 15, C["green"], 700)
    cmd = "mowfxy --hello"
    s.text(68, y0, cmd, 15, C["text"])
    cw = 15 * CW
    s.css.append(f"@keyframes ty{{from{{transform:translateX(0)}}to{{transform:translateX({len(cmd) * cw:.1f}px)}}}}"
                 f".ty{{animation:ty 1.1s steps({len(cmd)}) .4s both}}"
                 f"@keyframes cur{{0%,49%{{opacity:1}}50%,100%{{opacity:0}}}}.cur{{animation:cur 1s steps(1) infinite}}"
                 f"@keyframes pin{{0%{{opacity:0;transform:translateY(6px)}}100%{{opacity:1;transform:none}}}}"
                 f".pin{{animation:pin .6s cubic-bezier(.2,.7,.2,1) 1.6s both}}")
    s.add(f'<rect class="ty" x="66" y="{y0-16}" width="{len(cmd)*cw+6:.1f}" height="22" fill="{C["bg"]}"/>')
    s.add(f'<g class="ty"><rect class="cur" x="68" y="{y0-14}" width="9" height="18" fill="{C["green"]}" opacity=".85"/></g>')

    s.add('<g class="pin">')
    scope(s, 40, 108, 380, 196, 1.6)
    ax = 480
    s.text(ax, 196, "Mohamed Mowafy", 40, C["text"], 700, extra='letter-spacing="-1.2"')
    s.text(ax, 228, "electronics engineering student · cairo", 14, C["green"])
    s.text(ax, 264, "mohamedmowafy.com ↗", 14, C["blue"])
    s.add("</g>")
    scanlines(s, 0, 0, W, H, 14)
    return s.render()


# ------------------------------------------------------------------ tiles
def tile(name, tag, desc, scene, accent, alt):
    W, H = 423, 250
    cw, chh = W - 10, H - 6
    s = SVG(W, H, alt)
    s.add('<g transform="translate(5 0)">')
    s.add(f'<rect x=".5" y=".5" width="{cw-1}" height="{chh-1}" rx="12" fill="{C["bg"]}" stroke="{C["line"]}"/>')
    scene(s)
    s.text(18, 30, f"~/{name.lower()}", 11, C["dim"])
    s.text(cw - 18, 30, tag, 11, accent, anchor="end")
    s.text(18, chh - 40, name, 20, C["text"], 700)
    s.text(cw - 18, chh - 40, "↗", 16, C["dim"], anchor="end")
    s.text(18, chh - 19, desc, 11.5, C["soft"])
    s.add("</g>")
    scanlines(s, 5, 0, cw, chh, 12)
    return s.render()


WORK = [
    dict(slug="clem", name="Clem", tag="desktop app", accent=C["blue"], desc="A calm, local-first workspace.",
         scene=lambda s: s.frames(ripples(64, 10, 40), 18, 62, 10, 11.5, 6, C["blue"])),
    dict(slug="kern", name="Kern", tag="agent skills", accent=C["amber"], desc="Design taste for coding agents.",
         scene=lambda s: kern_scene(s, 18, 160, 377)),
]
LINKS = {"clem": "https://github.com/mowfxy/clem", "kern": "https://github.com/mowfxy/kern"}


# ------------------------------------------------------------------ footer
def footer():
    W, H = 1000, 60
    s = SVG(W, H, "exit. Thanks for stopping by.")
    s.add(f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="12" fill="{C["bg"]}" stroke="{C["line"]}"/>')
    s.text(28, 35, "~ ❯", 14, C["green"], 700)
    s.text(66, 35, "exit", 14, C["text"])
    s.text(116, 35, "# thanks for stopping by", 14, C["dim"])
    s.css.append("@keyframes cur{0%,49%{opacity:1}50%,100%{opacity:0}}.cur{animation:cur 1s steps(1) infinite}")
    s.add(f'<rect class="cur" x="{116 + 25 * 14 * CW:.1f}" y="21" width="8.4" height="18" fill="{C["green"]}" opacity=".85"/>')
    scanlines(s, 0, 0, W, H, 12)
    return s.render()


def readme():
    tiles = "".join(f'<a href="{LINKS[w["slug"]]}"><img src="assets/tile-{w["slug"]}.svg" width="423" '
                    f'alt="{w["name"]}: {w["desc"]}"></a>' for w in WORK)
    return "\n".join([
        '<a href="https://mohamedmowafy.com"><img src="assets/hero.svg" width="100%" alt="Mohamed Mowafy, '
        'electronics engineering student in Cairo. mohamedmowafy.com"></a>',
        "",
        f'<p align="center">{tiles}</p>',
        "",
        '<img src="assets/footer.svg" width="100%" alt="exit. Thanks for stopping by.">',
        "",
        "<!-- Generated by scripts/build.py. Set in JetBrains Mono and DejaVu Serif. -->",
        "",
    ])


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))
    files = {"hero.svg": hero(), "footer.svg": footer()}
    for w in WORK:
        files[f"tile-{w['slug']}.svg"] = tile(w["name"], w["tag"], w["desc"], w["scene"], w["accent"],
                                               f"{w['name']}: {w['desc']}")
    for name, content in files.items():
        with open(os.path.join(OUT, name), "w") as f:
            f.write(content)
        print(f"{name:24} {len(content) / 1024:7.1f} KB")
    with open(os.path.join(HERE, "..", "README.md"), "w") as f:
        f.write(readme())
