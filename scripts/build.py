"""Generate the SVG assets for the mowfxy profile README.

Text is set in Mowafy Serif and Mowafy Sans and converted to outlines, so the
SVGs look the same everywhere (GitHub shows them as images, which can't load
fonts). Each asset is written in a light and a dark version.

    MOWAFY_SERIF=../serif/fonts MOWAFY_SANS=../sans/fonts/ttf python3 scripts/build.py
"""
from functools import lru_cache
import math, os

from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets")
SERIF_DIR = os.environ.get("MOWAFY_SERIF", os.path.join(HERE, "../../serif/fonts"))
SANS_DIR = os.environ.get("MOWAFY_SANS", os.path.join(HERE, "../../sans/fonts/ttf"))

THEMES = {
    "light": dict(ink="#111111", soft="#4A4A4A", mute="#8A8A8A", rule="#E2E2E2", accent="#6B6B6B",
                  dot="#111111", field=.45),
    "dark": dict(ink="#FFFFFF", soft="#B4B4B4", mute="#7C7C7C", rule="#2A2A2A", accent="#9C9C9C",
                 dot="#FFFFFF", field=.55),
}
W = 1000


# ---------------------------------------------------------------- text → outlines
GLYPHS = {}  # glyph outlines used by the SVG being built


class Font:
    def __init__(self, path):
        self.tag = os.path.splitext(os.path.basename(path))[0].replace("MowafySerif-", "s").replace("MowafySans-", "n")
        self.f = TTFont(path)
        self.gs = self.f.getGlyphSet()
        self.cmap = self.f.getBestCmap()
        self.upm = self.f["head"].unitsPerEm
        self.hmtx = self.f["hmtx"]
        self.kern_tables = []
        if "GPOS" in self.f:
            g = self.f["GPOS"].table
            idx = {i for fr in g.FeatureList.FeatureRecord if fr.FeatureTag == "kern"
                   for i in fr.Feature.LookupListIndex}
            for i in sorted(idx):
                lk = g.LookupList.Lookup[i]
                for st in lk.SubTable:
                    st = st.ExtSubTable if lk.LookupType == 9 else st
                    if getattr(st, "LookupType", 2) == 2:
                        self.kern_tables.append(st)

    @lru_cache(maxsize=None)
    def kern(self, a, b):
        for st in self.kern_tables:
            cov = st.Coverage.glyphs
            if a not in cov:
                continue
            if st.Format == 1:
                for r in st.PairSet[cov.index(a)].PairValueRecord:
                    if r.SecondGlyph == b:
                        return getattr(r.Value1, "XAdvance", 0) or 0
            else:
                v = st.Class1Record[st.ClassDef1.classDefs.get(a, 0)] \
                      .Class2Record[st.ClassDef2.classDefs.get(b, 0)].Value1
                return (getattr(v, "XAdvance", 0) or 0) if v else 0
        return 0

    def layout(self, s, size, ls):
        k = size / self.upm
        gl = [self.cmap.get(ord(c), ".notdef") for c in s]
        adv = []
        for i, g in enumerate(gl):
            a = self.hmtx[g][0] * k + ls
            if i + 1 < len(gl):
                a += self.kern(g, gl[i + 1]) * k
            adv.append(a)
        return gl, adv

    def width(self, s, size, ls=0):
        return sum(self.layout(s, size, ls)[1]) - ls if s else 0

    @lru_cache(maxsize=None)
    def outline(self, g):
        """Glyph outline in font units, rounded to whole units."""
        pen = SVGPathPen(self.gs, ntos=lambda v: str(round(v)))
        self.gs[g].draw(pen)
        return pen.getCommands()

    def uses(self, s, size, x, y, anchor="start", ls=0):
        """<use> elements placing each glyph; the outlines go once into GLYPHS."""
        x -= {"start": 0, "middle": self.width(s, size, ls) / 2, "end": self.width(s, size, ls)}[anchor]
        k = size / self.upm
        out = []
        for g, a in zip(*self.layout(s, size, ls)):
            d = self.outline(g)
            if d:
                gid = f"{self.tag}-{g}".replace(".", "_")
                GLYPHS[gid] = d
                out.append(f'<use href="#{gid}" transform="translate({x:.1f} {y:.1f}) scale({k:.5f} {-k:.5f})"/>')
            x += a
        return "".join(out)


SERIF_LIGHT = Font(f"{SERIF_DIR}/MowafySerif-Light.otf")
SERIF = Font(f"{SERIF_DIR}/MowafySerif-Regular.otf")
SANS = Font(f"{SANS_DIR}/MowafySans-Regular.ttf")
SANS_MED = Font(f"{SANS_DIR}/MowafySans-Medium.ttf")


def t(font, s, size, x, y, fill, anchor="start", ls=0, extra=""):
    return f'<g fill="{fill}" {extra}>{font.uses(s, size, x, y, anchor, ls)}</g>'


def caps(s, size, x, y, fill, anchor="start"):
    return t(SANS_MED, s.upper(), size, x, y, fill, anchor, size * 0.16)


def wrap(s, font, size, maxw):
    lines, cur = [], ""
    for w in s.split():
        nxt = f"{cur} {w}".strip()
        if cur and font.width(nxt, size) > maxw:
            lines.append(cur)
            cur = w
        else:
            cur = nxt
    return lines + [cur]


def svg(h, body, title, css=""):
    motion = "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
    return wrap_svg(W, h, body, title, css + motion)


def wrap_svg(w, h, body, title, css=""):
    defs = "".join(f'<path id="{k}" d="{v}"/>' for k, v in GLYPHS.items())
    GLYPHS.clear()
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-label="{title}"><title>{title}</title><style>{css}</style>'
            f'<defs>{defs}</defs>{body}</svg>')


def arrow(x, y, c, s=16):
    """A thin north-east arrow ending at (x, y)."""
    return (f'<path d="M{x-s},{y+s} L{x},{y} M{x-s*0.62},{y} H{x} V{y+s*0.62}" fill="none" stroke="{c}" '
            f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>')


# ---------------------------------------------------------------- hero (animated ornament)
def rosette(cx, cy, R, r, d, turns, steps=2400):
    pts = []
    for i in range(steps + 1):
        a = 2 * math.pi * turns * i / steps
        x = (R - r) * math.cos(a) + d * math.cos((R - r) / r * a)
        y = (R - r) * math.sin(a) - d * math.sin((R - r) / r * a)
        pts.append(f"{cx+x:.1f},{cy+y:.1f}")
    return "M" + " L".join(pts) + "Z"


CODE = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghkmnpqrstuvwxyz0123456789{}<>/=+#"


def dots(c, h, key, cx, cy, reach, step=20, rmax=3.3, wave=9.0):
    """A halftone field of fine dots and code characters.

    Dots grow toward (cx, cy) and dissolve with distance. A soft diagonal wave
    brightens and dims the field continuously, and some points slowly crossfade
    between a dot and a character, as if the field were decoding."""
    cells = []
    for j in range(int(h / step) + 1):
        for i in range(int(W / step) + 1):
            x = i * step + (step / 2 if j % 2 else 0)
            y = j * step + step / 2
            dist = math.hypot((x - cx) / 1.25, y - cy) / reach
            if dist >= 1:
                continue
            f = (1 - dist) ** 1.6
            f *= min(1, max(0, min(x, W - x, y, h - y) / 60))  # fade at the image edges
            if f < 0.04:
                continue
            rnd = ((i * 7919 + j * 104729) % 9973) / 9973  # stable pseudo-random per cell
            r = rmax * (0.35 + 0.65 * f)
            dot = f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}"/>'
            if f > 0.22 and rnd < 0.3:
                ch = CODE[int(rnd * 1000) % len(CODE)]
                glyph = SANS_MED.uses(ch, step * 0.6, x, y + step * 0.21, "middle")
                d = -(((i * 37 + j * 61) % 101) / 101) * 3 * wave  # independent timing per point
                el = (f'<g opacity="{f:.2f}"><g class="{key}d" style="animation-delay:{d:.2f}s">{dot}</g>'
                      f'<g class="{key}c" style="animation-delay:{d:.2f}s">{glyph}</g></g>')
            else:
                el = dot.replace("/>", f' opacity="{f:.2f}"/>')
            cells.append((i + j, el))

    # one group per diagonal, each a little behind the last: a continuous wave
    bands = {}
    for b, el in cells:
        bands.setdefault(b, []).append(el)
    span = 46  # diagonals per wavelength
    groups = "".join(f'<g class="{key}w" style="animation-delay:{-wave * (b % span) / span:.2f}s">{"".join(v)}</g>'
                     for b, v in sorted(bands.items()))
    css = (f"@keyframes {key}w{{0%,100%{{opacity:.3}}50%{{opacity:1}}}}"
           f".{key}w{{animation:{key}w {wave}s cubic-bezier(.45,0,.55,1) infinite}}"
           f"@keyframes {key}d{{0%,30%,100%{{opacity:1}}45%,85%{{opacity:0}}}}"
           f"@keyframes {key}c{{0%,30%,100%{{opacity:0}}45%,85%{{opacity:1}}}}"
           f".{key}d{{animation:{key}d {wave*3}s cubic-bezier(.45,0,.55,1) infinite}}"
           f".{key}c{{opacity:0;animation:{key}c {wave*3}s cubic-bezier(.45,0,.55,1) infinite}}")
    return f'<g opacity="{c["field"]}" fill="{c["dot"]}">{groups}</g>', css


def hero(c):
    H = 560
    bg, css = dots(c, H, "h", 870, 260, 470)
    b = [bg]
    b.append(caps("Mohamed Mowafy  ·  Cairo", 17, 0, 52, c["mute"]))
    b.append(t(SERIF_LIGHT, "Mohamed", 136, -5, 200, c["ink"], ls=-2.5))
    b.append(t(SERIF_LIGHT, "Mowafy", 136, -5, 328, c["accent"], ls=-2.5))
    intro = ("Electronics engineering student at the German University in Cairo. "
             "I build Mowr, a local-first AI workspace, and open-source skills "
             "that give coding agents better taste.")
    for i, line in enumerate(wrap(intro, SANS, 26, 620)):
        b.append(t(SANS, line, 26, 0, 404 + i * 40, c["soft"]))
    return svg(H, "".join(b), "Mohamed Mowafy — electronics engineering student building Mowr and agent skills", css)


# ---------------------------------------------------------------- links (static)
def link(label, sub, c):
    w, h = 250, 84
    b = [f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="{(h-2)/2}" fill="none" stroke="{c["rule"]}" stroke-width="1.5"/>',
         t(SANS_MED, label, 24, 30, 40, c["ink"]),
         t(SANS, sub, 16, 30, 63, c["mute"]),
         arrow(w - 30, 34, c["accent"])]
    return wrap_svg(w, h, "".join(b), f"{label}: {sub}")


# ---------------------------------------------------------------- selected work (static)
def section(c):
    H = 130
    b = [t(SERIF, "Selected work", 50, 0, 84, c["ink"], ls=-.5),
         caps("2025 — 2026", 15, W, 82, c["mute"], "end"),
         f'<line x1="0" y1="{H-1}" x2="{W}" y2="{H-1}" stroke="{c["ink"]}" stroke-width="1.5"/>']
    return svg(H, "".join(b), "Selected work")


WORK = [
    ("mowr", "01", "Mowr", "A local-first AI workspace for Windows. Chats and files stay on your machine.", "Desktop app"),
    ("blend", "02", "Blend", "Eleven coordinated frontend skills that give coding agents real design taste.", "Agent skills"),
    ("anti-slop", "03", "anti-slop", "Makes agents finish the details: working forms, accessibility, mobile, metadata.", "Agent skill"),
    ("web-perf", "04", "Web Perf", "Measure first, fix the real bottleneck, keep Core Web Vitals from slipping.", "Agent skill"),
    ("repo-tidier", "05", "Repo Tidier", "Turns a messy repository into a clean project without changing how it behaves.", "Agent skill"),
    ("kinetra", "06", "Kinetra", "A TypeScript workbench that renders physics and circuit diagrams from JSON.", "Engineering"),
]


def row(num, title, desc, kind, c):
    H = 170
    b = [t(SERIF, num, 22, 0, 66, c["mute"]),
         t(SERIF, title, 54, 70, 72, c["ink"], ls=-.6),
         caps(kind, 15, W - 44, 64, c["mute"], "end"),
         arrow(W - 2, 50, c["accent"], 18)]
    for i, line in enumerate(wrap(desc, SANS, 25, 760)):
        b.append(t(SANS, line, 25, 72, 116 + i * 36, c["soft"]))
    b.append(f'<line x1="0" y1="{H-1}" x2="{W}" y2="{H-1}" stroke="{c["rule"]}" stroke-width="1.5"/>')
    return svg(H, "".join(b), f"{title}: {desc}")


# ---------------------------------------------------------------- sign-off (animated dot)
def footer(c):
    H = 220
    bg, css = dots(c, H, "f", 900, 110, 380, rmax=2.6)
    b = [bg, t(SERIF_LIGHT, "Thanks for stopping by.", 54, 0, 104, c["ink"], ls=-.8)]
    b.append(f'<circle cx="7" cy="160" r="5" fill="{c["accent"]}"/>')
    b.append(t(SANS, "Currently building Mowr", 22, 26, 168, c["soft"]))
    b.append(t(SANS, "mohamedmowafy.com", 22, W, 168, c["mute"], "end"))
    return svg(H, "".join(b), "Thanks for stopping by. Currently building Mowr.", css)


def write(name, content):
    with open(os.path.join(OUT, name), "w") as f:
        f.write(content)


def pic(name, alt, width=None, height=None):
    size = f' width="{width}"' if width else f' height="{height}"'
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="assets/{name}-dark.svg">'
            f'<img src="assets/{name}-light.svg" alt="{alt}"{size}></picture>')


def write_readme():
    links = {
        "mowr": "https://github.com/mowfxy/mowr-releases", "blend": "https://github.com/mowfxy/blend",
        "anti-slop": "https://github.com/mowfxy/anti-slop", "web-perf": "https://github.com/mowfxy/web-perf",
        "repo-tidier": "https://github.com/mowfxy/cl-repo", "kinetra": "https://github.com/mowfxy/kinetra",
    }
    parts = [
        pic("hero", "Mohamed Mowafy — electronics engineering student at GUC, building Mowr and open-source agent skills", "100%"),
        "",
        "<p>",
        f'  <a href="https://mohamedmowafy.com">{pic("link-site", "Website: mohamedmowafy.com", height=40)}</a>',
        f'  <a href="https://mowrai.com">{pic("link-mowr", "Mowr: mowrai.com", height=40)}</a>',
        f'  <a href="https://github.com/mowfxy/mowr-releases/releases">{pic("link-download", "Download Mowr for Windows", height=40)}</a>',
        "</p>",
        "",
        "<br>",
        "",
        pic("section", "Selected work", "100%"),
        "",
    ]
    for slug, num, title, desc, kind in WORK:
        parts.append(f'<a href="{links[slug]}">{pic("work-" + slug, f"{title}: {desc}", "100%")}</a>')
    parts += ["", "<br>", "", pic("footer", "Thanks for stopping by. Currently building Mowr.", "100%"), "",
              "<!-- Generated by scripts/build.py. Set in Mowafy Serif and Mowafy Sans. -->", ""]
    with open(os.path.join(HERE, "..", "README.md"), "w") as f:
        f.write("\n".join(parts))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))
    for theme, c in THEMES.items():
        write(f"hero-{theme}.svg", hero(c))
        write(f"section-{theme}.svg", section(c))
        write(f"footer-{theme}.svg", footer(c))
        for slug, num, title, desc, kind in WORK:
            write(f"work-{slug}-{theme}.svg", row(num, title, desc, kind, c))
        write(f"link-site-{theme}.svg", link("Website", "mohamedmowafy.com", c))
        write(f"link-mowr-{theme}.svg", link("Mowr", "mowrai.com", c))
        write(f"link-download-{theme}.svg", link("Download", "Windows app", c))
    print(f"{len(os.listdir(OUT))} files written")
    write_readme()
