"""Generate the animated dark-knight SVGs used by README.md.

    python tools/build_assets.py

Cinematic stormy night: procedural noise clouds and fog (feTurbulence),
layered skylines fading into haze, film grain and a vignette, in a slate
blue-grey palette with pure black silhouettes. Text is converted to outlines
with Bebas Neue and Oswald (both OFL), so the SVGs render the same everywhere
without loading any web font. The fonts are downloaded into tools/.cache on
first run.

about.svg embeds tools/avatar.jpg (a square crop of the profile picture)
inside a circle.
"""
import base64
import os
import random
import urllib.request

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets")
CACHE = os.path.join(HERE, ".cache")
AVATAR = os.path.join(HERE, "avatar.jpg")
FONTS = {
    "BebasNeue.ttf": "https://github.com/google/fonts/raw/main/ofl/bebasneue/BebasNeue-Regular.ttf",
    "Oswald.ttf": "https://github.com/google/fonts/raw/main/ofl/oswald/Oswald%5Bwght%5D.ttf",
}

C = dict(
    sky0="#07090E",
    sky1="#10141C",
    sky2="#1B1E28",
    sky3="#2B2B36",
    haze="#2C2D38",
    panel="#0B0D13",
    near="#000000",
    steel="#7B8193",
    steel2="#4A4F5E",
    silver="#B9BDC9",
    white="#E4E7EF",
    glow="#CDD5F0",
    win="#AEB4C4",
    win2="#6A7083",
)
# skyline layers, far to near: colour, haze over it
LAYERS = [("#171922", .0), ("#0E1016", .0), ("#0A0B10", .0), ("#000000", .0)]


def n(v):
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def rgb(hex_):
    return [int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5)]


# --------------------------------------------------------------------------- font

class Font:
    def __init__(self, file, wght=None):
        path = os.path.join(CACHE, file)
        if not os.path.exists(path):
            os.makedirs(CACHE, exist_ok=True)
            urllib.request.urlretrieve(FONTS[file], path)
        font = TTFont(path)
        if wght is not None:
            font = instancer.instantiateVariableFont(font, {"wght": wght})
        self.gs = font.getGlyphSet()
        self.cmap = font.getBestCmap()
        self.upm = font["head"].unitsPerEm
        self.hmtx = font["hmtx"]

    def layout(self, text, size, ls=0.0):
        s = size / self.upm
        x, glyphs = 0.0, []
        for ch in text:
            name = self.cmap.get(ord(ch), self.cmap[ord(" ")])
            pen = SVGPathPen(self.gs, ntos=n)
            self.gs[name].draw(TransformPen(pen, (s, 0, 0, -s, 0, 0)))
            adv = self.hmtx[name][0] * s
            glyphs.append((pen.getCommands(), x, adv))
            x += adv + ls
        return glyphs, x - ls

    def width(self, text, size, ls=0.0):
        return self.layout(text, size, ls)[1]


BEBAS = OSWALD = None


def text(font, s, size, x, y, fill, anchor="middle", ls=0.0, extra=""):
    glyphs, w = font.layout(s, size, ls)
    x0 = {"middle": x - w / 2, "start": x, "end": x - w}[anchor]
    out = "".join(f'<path transform="translate({n(x0 + gx)},{n(y)})" d="{d}"/>' for d, gx, _ in glyphs if d)
    return f'<g fill="{fill}"{extra}>{out}</g>'


# ------------------------------------------------------------------- gradients

def radial(gid, stops, cx=".5", cy=".5", r=".5"):
    s = "".join(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>' for o, c, a in stops)
    return f'<radialGradient id="{gid}" cx="{cx}" cy="{cy}" r="{r}">{s}</radialGradient>'


def linear(gid, stops, x2="0", y2="1"):
    s = "".join(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>' for o, c, a in stops)
    return f'<linearGradient id="{gid}" x1="0" y1="0" x2="{x2}" y2="{y2}">{s}</linearGradient>'


def glow(gid, sd, strength=1):
    nodes = '<feMergeNode in="b"/>' * strength
    return (f'<filter id="{gid}" x="-30%" y="-60%" width="160%" height="220%">'
            f'<feGaussianBlur stdDeviation="{sd}" result="b"/>'
            f'<feMerge>{nodes}<feMergeNode in="SourceGraphic"/></feMerge></filter>')


def blur(gid, sd):
    return f'<filter id="{gid}" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="{sd}"/></filter>'


def noise(gid, freq, octaves, seed, color, gain, bias):
    """Fractal noise tinted `color`; alpha = noise*gain + bias, masked by the source shape."""
    r, g, b = rgb(color)
    return (f'<filter id="{gid}" x="0" y="0" width="100%" height="100%">'
            f'<feTurbulence type="fractalNoise" baseFrequency="{freq}" numOctaves="{octaves}" seed="{seed}"/>'
            f'<feColorMatrix values="0 0 0 0 {r:.3f} 0 0 0 0 {g:.3f} 0 0 0 0 {b:.3f} {gain} 0 0 0 {bias}"/>'
            f'<feComposite in2="SourceGraphic" operator="in"/></filter>')


GRAIN = ('<filter id="grain" x="0" y="0" width="100%" height="100%">'
         '<feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" stitchTiles="stitch"/>'
         '<feColorMatrix values=".33 .33 .33 0 0 .33 .33 .33 0 0 .33 .33 .33 0 0 0 0 0 0 .09"/></filter>')


# ---------------------------------------------------------------------- scenery

# right half of an original bat silhouette, ~200 x 60, centred on (0,0)
BAT_R = ("M0,-8 L5,-8 L9,-22 L13,-8 Q30,-10 46,-22 Q70,-34 100,-18 Q86,-8 84,6 "
         "Q72,-2 60,10 Q52,2 40,14 Q30,8 22,26 Q12,18 0,30Z")


def bat_shape(fill):
    return f'<g fill="{fill}"><path d="{BAT_R}"/><path transform="scale(-1,1)" d="{BAT_R}"/></g>'


def bat(x, y, s, fill):
    return f'<g transform="translate({n(x)},{n(y)}) scale({s})">{bat_shape(fill)}</g>'


def gliding_bats(count, seed, x_range, y_range, dx, dy, size=(.035, .07), dur=(16, 26)):
    """Distant bats drifting slowly across the sky, wings barely moving."""
    rnd = random.Random(seed)
    out = []
    for _ in range(count):
        d = rnd.uniform(*dur)
        out.append(f'<g transform="translate({n(rnd.uniform(*x_range))},{n(rnd.uniform(*y_range))})">'
                   f'<g class="fly" style="animation-duration:{d:.1f}s;animation-delay:{-rnd.uniform(0, d):.1f}s;'
                   f'--dx:{n(dx + rnd.uniform(-80, 80))}px;--dy:{n(dy + rnd.uniform(-40, 40))}px">'
                   f'<g transform="scale({rnd.uniform(*size):.3f})"><g class="flap" style="animation-duration:{rnd.uniform(.5, .8):.2f}s">'
                   f'{bat_shape("#05060A")}</g></g></g></g>')
    return "".join(out)


def rain(w, h, count, seed, opacity=.13):
    rnd = random.Random(seed)
    out = []
    for _ in range(count):
        d = rnd.uniform(.45, .8)
        ln = rnd.uniform(26, 48)
        out.append(f'<g transform="translate({n(rnd.uniform(0, w + 80))},{n(rnd.uniform(-60, 0))})">'
                   f'<path class="rain" style="animation-duration:{d:.2f}s;animation-delay:{-rnd.uniform(0, d):.2f}s;--h:{h + 60}px" '
                   f'd="M0,0 l-5,{n(ln)}" stroke="{C["silver"]}" stroke-width=".8" stroke-linecap="round" '
                   f'opacity="{rnd.uniform(opacity * .4, opacity):.2f}"/></g>')
    return "".join(out)


def skyline(w, base, seed, hmin, hmax, fill, win_rate=0.0, win_op=(.15, .45)):
    rnd = random.Random(seed)
    out, win = [], []
    x = -10
    while x < w + 10:
        bw = rnd.uniform(28, 90)
        bh = rnd.uniform(hmin, hmax)
        top = base - bh
        out.append(f'<rect x="{n(x)}" y="{n(top)}" width="{n(bw + 1)}" height="{n(bh + 2)}"/>')
        roll = rnd.random()
        if roll < .14:  # gothic spire
            out.append(f'<path d="M{n(x + bw * .25)},{n(top)} L{n(x + bw / 2)},{n(top - bh * .4)} L{n(x + bw * .75)},{n(top)}Z"/>')
        elif roll < .3:  # antenna
            out.append(f'<rect x="{n(x + bw / 2 - 1)}" y="{n(top - 30)}" width="2" height="30"/>')
            if win_rate:
                win.append(f'<circle class="beacon" style="animation-delay:{-rnd.uniform(0, 3):.1f}s" '
                           f'cx="{n(x + bw / 2)}" cy="{n(top - 31)}" r="1.6" fill="{C["white"]}"/>')
        elif roll < .45:  # stepped roof
            out.append(f'<rect x="{n(x + bw * .15)}" y="{n(top - 12)}" width="{n(bw * .7)}" height="14"/>')
            out.append(f'<rect x="{n(x + bw * .3)}" y="{n(top - 22)}" width="{n(bw * .4)}" height="12"/>')
        elif roll < .55:  # water tower
            out.append(f'<rect x="{n(x + bw * .55)}" y="{n(top - 18)}" width="12" height="14" rx="2"/>'
                       f'<path d="M{n(x + bw * .55 + 1)},{n(top - 4)} v6 M{n(x + bw * .55 + 11)},{n(top - 4)} v6" '
                       f'stroke="{fill}" stroke-width="1.5"/>')
        if win_rate:
            # windows cluster on a few floors instead of a uniform grid
            for wy in range(int(top + 10), int(base - 6), 9):
                if rnd.random() > .35:
                    continue
                for wx in range(int(x + 5), int(x + bw - 6), 7):
                    if rnd.random() < win_rate:
                        col = rnd.choice([C["win"], C["win2"], C["win2"]])
                        cls = (f' class="win" style="animation-delay:{-rnd.uniform(0, 11):.1f}s"'
                               if rnd.random() < .12 else "")
                        win.append(f'<rect{cls} x="{wx}" y="{wy}" width="3" height="4" fill="{col}" '
                                   f'opacity="{rnd.uniform(*win_op):.2f}"/>')
        x += bw + rnd.uniform(-6, 4)
    return f'<g fill="{fill}">{"".join(out)}</g>{"".join(win)}'


class Scene:
    """Collects <defs> for one SVG and builds the shared cinematic storm layers."""

    def __init__(self, uid, w, h):
        self.uid, self.w, self.h = uid, w, h
        self.defs = [GRAIN,
                     linear(f"sky{uid}", [(0, C["sky0"], 1), (.5, C["sky1"], 1), (.85, C["sky2"], 1), (1, C["sky3"], 1)], x2=".35"),
                     radial(f"vig{uid}", [(0, "#000", 0), (.55, "#000", 0), (1, "#000", .88)], cy=".42", r=".72"),
                     linear(f"band{uid}", [(0, "#fff", 0), (.5, "#fff", 1), (1, "#fff", 0)]),
                     linear(f"top{uid}", [(0, "#fff", 1), (.75, "#fff", .6), (1, "#fff", 0)]),
                     glow(f"glow{uid}", 4),
                     blur(f"soft{uid}", 6)]
        self.k = 0

    def _id(self, kind):
        self.k += 1
        return f"{kind}{self.uid}{self.k}"

    def clouds(self, seed, y0=-20, y1=None, color=None, freq="0.0035 0.010", gain=1.7, bias=-.55, dur=90):
        y1 = self.h * .75 if y1 is None else y1
        fid = self._id("cl")
        self.defs.append(noise(fid, freq, 5, seed, color or C["haze"], gain, bias))
        return (f'<g class="drift" style="animation-duration:{dur}s">'
                f'<rect x="-120" y="{n(y0)}" width="{self.w + 240}" height="{n(y1 - y0)}" '
                f'fill="url(#top{self.uid})" filter="url(#{fid})"/></g>')

    def fog(self, seed, y, height, opacity=.55, dur=60):
        fid = self._id("fg")
        self.defs.append(noise(fid, "0.006 0.03", 4, seed, C["haze"], 1.4, -.25))
        return (f'<g class="drift" style="animation-duration:{dur}s;animation-direction:alternate-reverse">'
                f'<rect x="-120" y="{n(y)}" width="{self.w + 240}" height="{n(height)}" opacity="{opacity}" '
                f'fill="url(#band{self.uid})" filter="url(#{fid})"/></g>')

    def sky(self):
        return f'<rect width="{self.w}" height="{self.h}" fill="url(#sky{self.uid})"/>'

    def lightning(self, delay=0):
        return (f'<rect class="flash" style="animation-delay:{delay}s" width="{self.w}" height="{self.h}" '
                f'fill="{C["glow"]}"/>')

    def finish(self):
        return (f'<rect width="{self.w}" height="{self.h}" fill="url(#vig{self.uid})"/>'
                f'<rect width="{self.w}" height="{self.h}" filter="url(#grain)"/>')


# ------------------------------------------------------------------------ styles

STYLE = """<style>
.fly{animation:fly linear infinite}
@keyframes fly{0%{transform:translate(0,0);opacity:0}10%,85%{opacity:1}100%{transform:translate(var(--dx),var(--dy));opacity:0}}
.flap{animation:flap .6s ease-in-out infinite alternate;transform-box:fill-box;transform-origin:center}
@keyframes flap{from{transform:scale(1,1)}to{transform:scale(.94,.7)}}
.rain{animation:rain .6s linear infinite}
@keyframes rain{to{transform:translate(-40px,var(--h))}}
.drift{animation:drift 90s ease-in-out infinite alternate}
@keyframes drift{from{transform:translateX(-90px)}to{transform:translateX(90px)}}
.win{animation:win 11s steps(1) infinite}
@keyframes win{0%,70%{opacity:.4}71%,100%{opacity:0}}
.beacon{animation:beacon 2.6s ease-in-out infinite}
@keyframes beacon{0%,100%{opacity:.05}50%{opacity:.7}}
.flash{animation:flash 13s infinite;opacity:0}
@keyframes flash{0%,88%,100%{opacity:0}88.6%{opacity:.13}89.2%{opacity:.02}90%{opacity:.09}91.5%{opacity:0}}
.sway{animation:sway 14s ease-in-out infinite;transform-box:view-box}
@keyframes sway{0%,100%{transform:rotate(-2deg)}50%{transform:rotate(2deg)}}
.breathe{animation:breathe 5s ease-in-out infinite}
@keyframes breathe{0%,100%{opacity:.55}50%{opacity:.9}}
.shine{animation:shine 7s ease-in-out infinite}
@keyframes shine{0%,60%{transform:translateX(-200px)}90%,100%{transform:translateX(1200px)}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
</style>"""


def svg(w, h, body, title, defs):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{title}"><title>{title}</title>{STYLE}<defs>{"".join(defs)}</defs>{body}</svg>')


def card(w, h, inner, uid, pad=6, r=14):
    box = f'x="{pad}" y="{pad}" width="{w - 2 * pad}" height="{h - 2 * pad}" rx="{r}"'
    return (f'<clipPath id="card{uid}"><rect {box}/></clipPath>'
            f'<rect {box} fill="{C["sky0"]}"/>'
            f'<g clip-path="url(#card{uid})">{inner}</g>'
            f'<rect {box} fill="none" stroke="{C["steel2"]}" stroke-opacity=".6" stroke-width="1.5"/>')


# ----------------------------------------------------------------------- assets

def header():
    W, H = 1000, 470
    sc = Scene("h", W, H)
    bx, by = 650, 470   # searchlight base
    sx, sy = 800, 98    # where the beam hits the clouds
    sc.defs += [linear("beam", [(0, C["glow"], 0), (.5, C["glow"], .1), (1, C["glow"], .3)]),
                radial("hit", [(0, C["glow"], .75), (.4, C["glow"], .3), (1, C["glow"], 0)]),
                blur("beamb", 8), blur("batb", 1.6)]
    signal = (
        f'<g class="sway" style="transform-origin:{bx}px {by}px">'
        f'<path d="M{bx - 6},{by} L{bx + 6},{by} L{sx + 80},{sy + 30} L{sx - 80},{sy - 30}Z" '
        f'fill="url(#beam)" filter="url(#beamb)"/>'
        f'<g class="breathe"><ellipse cx="{sx}" cy="{sy}" rx="170" ry="110" fill="url(#hit)"/>'
        f'<g opacity=".9" filter="url(#batb)">{bat(sx, sy + 4, .62, "#05060A")}</g></g></g>')
    sub_l, sub_r, size, ls = "FULL-STACK DEVELOPER", "THAILAND", 24, 6
    gap = 56
    wl, wr = OSWALD.width(sub_l, size, ls), OSWALD.width(sub_r, size, ls)
    x0 = W / 2 - (wl + gap + wr) / 2
    subtitle = (text(OSWALD, sub_l, size, x0, 266, C["steel"], anchor="start", ls=ls)
                + bat(x0 + wl + gap / 2, 257, .12, C["steel"])
                + text(OSWALD, sub_r, size, x0 + wl + gap, 266, C["steel"], anchor="start", ls=ls))
    inner = (
        sc.sky()
        + sc.clouds(3)
        + sc.clouds(8, y0=-40, y1=200, color="#3A3B47", freq="0.006 0.016", gain=1.5, bias=-.7, dur=70)
        + sc.lightning()
        + signal
        + skyline(W, H, 5, 150, 290, LAYERS[0][0])
        + sc.fog(11, 230, 160, .6)
        + skyline(W, H, 6, 100, 220, LAYERS[1][0], .25, (.08, .25))
        + gliding_bats(6, 3, (-40, 400), (90, 210), 700, -60)
        + text(BEBAS, "PAPHOP", 168, W / 2, 216, C["silver"], ls=12, extra=' filter="url(#glowh)" opacity=".92"')
        + f'<rect x="{W / 2 - 150}" y="234" width="300" height="1.5" fill="{C["steel2"]}"/>'
        + subtitle
        + sc.fog(17, 330, 120, .5, 50)
        + skyline(W, H + 4, 9, 70, 160, LAYERS[2][0], .3, (.12, .35))
        + skyline(W, H + 6, 11, 30, 90, LAYERS[3][0], .2, (.15, .4))
        + rain(W, H, 110, 8)
        + sc.finish()
    )
    return svg(W, H, card(W, H, inner, "h"), "PAPHOP - Full-Stack Developer from Thailand", sc.defs)


SECTIONS = [("about", "About Me"), ("stack", "Tech Stack"), ("facts", "Fun Facts")]


def section_title(slug, label):
    W, H = 1000, 130
    size, ls = 46, 8
    tw = BEBAS.width(label, size, ls)
    pw, ph, cut = tw + 130, 62, 14
    x0, y0 = (W - pw) / 2, 34
    x1, y1 = x0 + pw, y0 + ph
    plate = (f"M{n(x0 + cut)},{y0} H{n(x1 - cut)} L{n(x1)},{y0 + cut} V{y1 - cut} L{n(x1 - cut)},{y1} "
             f"H{n(x0 + cut)} L{n(x0)},{y1 - cut} V{y0 + cut}Z")
    defs = [GRAIN,
            noise("pn", "0.02 0.06", 3, 5, C["haze"], 1.2, -.35),
            linear("lineL", [(0, C["steel2"], 0), (1, C["steel"], .9)], x2="1", y2="0"),
            linear("lineR", [(0, C["steel"], .9), (1, C["steel2"], 0)], x2="1", y2="0"),
            linear("plateg", [(0, "#171A23", 1), (1, C["panel"], 1)]),
            linear("shineg", [(0, "#fff", 0), (.5, "#fff", .06), (1, "#fff", 0)], x2="1", y2="0"),
            glow("tg", 3),
            f'<clipPath id="pc"><path d="{plate}"/></clipPath>']
    cy = y0 + ph / 2
    body = (
        f'<rect x="80" y="{cy - .75}" width="{n(x0 - 150)}" height="1.5" fill="url(#lineL)"/>'
        + f'<rect x="{n(x1 + 70)}" y="{cy - .75}" width="{n(850 - x1)}" height="1.5" fill="url(#lineR)"/>'
        + bat(x0 - 36, cy, .16, C["steel"]) + bat(x1 + 36, cy, .16, C["steel"])
        + f'<path d="{plate}" fill="url(#plateg)"/>'
        + f'<g clip-path="url(#pc)"><rect x="{n(x0)}" y="{y0}" width="{n(pw)}" height="{ph}" fill="#fff" filter="url(#pn)" opacity=".5"/>'
          f'<rect class="shine" x="0" y="{y0}" width="140" height="{ph}" fill="url(#shineg)" transform="skewX(-20)"/>'
          f'<rect x="{n(x0)}" y="{y0}" width="{n(pw)}" height="{ph}" filter="url(#grain)"/></g>'
        + f'<path d="{plate}" fill="none" stroke="{C["steel2"]}" stroke-width="1.5"/>'
        + f'<path d="M{n(x0 + cut)},{y0} H{n(x1 - cut)}" stroke="{C["steel"]}" stroke-width="1.5" opacity=".7"/>'
        + text(BEBAS, label, size, W / 2, y0 + 47, C["silver"], ls=ls, extra=' filter="url(#tg)"')
    )
    return svg(W, H, body, label, defs)


def about_card():
    W, H = 500, 460
    sc = Scene("a", W, H)
    cx, cy, r = 250, 188, 158
    with open(AVATAR, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    # eye positions inside the 400px crop space of avatar.jpg, scaled to the circle
    s = 2 * r / 400
    eyes = [(cx - r + 185 * s, cy - r + 190 * s), (cx - r + 250 * s, cy - r + 220 * s)]
    sc.defs += [f'<clipPath id="circ"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath>',
                radial("inner", [(0, "#000", 0), (.7, "#000", 0), (1, "#000", .65)]),
                radial("halo", [(0, C["glow"], 0), (.78, C["glow"], 0), (.84, C["glow"], .16), (1, C["glow"], 0)]),
                radial("eye", [(0, C["white"], .55), (1, C["white"], 0)])]
    portrait = (
        f'<circle cx="{cx}" cy="{cy}" r="{r * 1.22}" fill="url(#halo)" class="breathe"/>'
        f'<g clip-path="url(#circ)">'
        f'<image href="data:image/jpeg;base64,{b64}" x="{cx - r}" y="{cy - r}" width="{2 * r}" height="{2 * r}" '
        f'preserveAspectRatio="xMidYMid slice"/>'
        + "".join(f'<ellipse class="breathe" cx="{n(ex)}" cy="{n(ey)}" rx="20" ry="12" fill="url(#eye)"/>' for ex, ey in eyes)
        + rain(W, H, 26, 21, .1)
        + f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#inner)"/></g>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{C["steel"]}" stroke-width="1.5" opacity=".75"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r + 8}" fill="none" stroke="{C["steel2"]}" stroke-width="1" '
        f'stroke-dasharray="2 7" opacity=".7"/>'
    )
    inner = (
        sc.sky()
        + sc.clouds(13, y1=300)
        + sc.lightning(-5)
        + skyline(W, H, 23, 60, 150, LAYERS[1][0])
        + sc.fog(29, 300, 110, .5)
        + skyline(W, H + 4, 27, 20, 80, LAYERS[3][0], .2, (.1, .3))
        + rain(W, H, 40, 4)
        + portrait
        + text(OSWALD, "POWERED BY", 17, W / 2, 396, C["steel"], ls=7)
        + text(BEBAS, "BLACK COFFEE & LATE NIGHTS", 36, W / 2, 434, C["silver"], ls=4, extra=' filter="url(#glowa)"')
        + sc.finish()
    )
    return svg(W, H, card(W, H, inner, "a"), "Profile portrait in a stormy night", sc.defs)


def divider():
    W, H = 1000, 40
    defs = [linear("dl", [(0, C["steel2"], 0), (.5, C["steel"], .9), (1, C["steel2"], 0)], x2="1", y2="0")]
    body = (
        f'<rect x="60" y="19.5" width="880" height="1" fill="url(#dl)"/>'
        + f'<path d="M{W / 2 - 30},20 l-6,-4 v8Z M{W / 2 + 30},20 l6,-4 v8Z" fill="{C["steel2"]}"/>'
        + bat(W / 2, 20, .14, C["steel"])
    )
    return svg(W, H, body, "Divider", defs)


def footer():
    W, H = 1000, 340
    sc = Scene("f", W, H)
    sub = "SEE YOU IN THE NEXT COMMIT"
    sw = OSWALD.width(sub, 20, 6)
    inner = (
        sc.sky()
        + sc.clouds(41, y1=240)
        + sc.lightning(-6)
        + skyline(W, H, 31, 110, 220, LAYERS[0][0])
        + sc.fog(37, 170, 140, .55)
        + gliding_bats(8, 12, (700, 1040), (50, 170), -900, -40)
        + text(BEBAS, "THANKS FOR VISITING", 78, W / 2, 132, C["silver"], ls=8, extra=' filter="url(#glowf)" opacity=".92"')
        + text(OSWALD, sub, 20, W / 2 - 14, 172, C["steel"], ls=6)
        + bat(W / 2 + sw / 2 + 10, 165, .1, C["steel"])
        + skyline(W, H + 4, 41, 60, 150, LAYERS[2][0], .3, (.1, .3))
        + sc.fog(43, 270, 90, .45, 45)
        + skyline(W, H + 6, 47, 20, 70, LAYERS[3][0], .2, (.15, .4))
        + rain(W, H, 80, 13)
        + sc.finish()
    )
    return svg(W, H, card(W, H, inner, "f"), "Thanks for visiting", sc.defs)


def main():
    global BEBAS, OSWALD
    BEBAS, OSWALD = Font("BebasNeue.ttf"), Font("Oswald.ttf", 500)
    os.makedirs(OUT, exist_ok=True)
    files = {"header.svg": header(), "about.svg": about_card(),
             "divider.svg": divider(), "footer.svg": footer()}
    for slug, label in SECTIONS:
        files[f"title-{slug}.svg"] = section_title(slug, label)
    for name, content in files.items():
        with open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        print(f"{name:26s} {len(content) / 1024:6.1f} KB")


if __name__ == "__main__":
    main()
