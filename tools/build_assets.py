"""Generate the animated kawaii-cat SVGs used by README.md.

    python tools/build_assets.py

Text is converted to outlines with the Fredoka font (OFL), so the SVGs render
the same everywhere without loading any web font. The font is downloaded into
tools/.cache on first run.
"""
import math
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
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/fredoka/Fredoka%5Bwdth,wght%5D.ttf"

C = dict(
    cream="#FFFCF7",
    border="#EADCF4",
    lav="#CDB7E3",
    lav2="#B393D6",
    lav3="#9A74C4",
    lav_soft="#EFE5F8",
    brown="#6B3F23",
    brown2="#8A5A3B",
    ink="#4A3730",
    pink="#F4A3B6",
    pink_soft="#FBD5DE",
    gold="#F5C46E",
    red="#EA5B53",
    grey="#B7AEA8",
    patch="#7C5B49",
    white="#FFFFFF",
)
CONFETTI = [C["lav2"], C["pink"], C["gold"], C["red"], C["lav"], C["brown2"]]


def n(v):
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


# --------------------------------------------------------------------------- font

class Font:
    _base = None

    def __init__(self, wght):
        path = os.path.join(CACHE, "Fredoka.ttf")
        if not os.path.exists(path):
            os.makedirs(CACHE, exist_ok=True)
            urllib.request.urlretrieve(FONT_URL, path)
        font = instancer.instantiateVariableFont(TTFont(path), {"wght": wght, "wdth": 100})
        self.gs = font.getGlyphSet()
        self.cmap = font.getBestCmap()
        self.upm = font["head"].unitsPerEm
        self.hmtx = font["hmtx"]

    def layout(self, text, size, ls=0.0):
        s = size / self.upm
        x, glyphs = 0.0, []
        for ch in text:
            name = self.cmap[ord(ch)]
            pen = SVGPathPen(self.gs, ntos=n)
            self.gs[name].draw(TransformPen(pen, (s, 0, 0, -s, 0, 0)))
            adv = self.hmtx[name][0] * s
            glyphs.append((pen.getCommands(), x, adv))
            x += adv + ls
        return glyphs, x - ls

    def width(self, text, size, ls=0.0):
        return self.layout(text, size, ls)[1]


BOLD = SEMI = None


def text(font, s, size, x, y, fill, anchor="middle", ls=0.0, cls=None, step=0.0, extra=""):
    glyphs, w = font.layout(s, size, ls)
    x0 = {"middle": x - w / 2, "start": x, "end": x - w}[anchor]
    out = []
    for i, (d, gx, _) in enumerate(glyphs):
        if not d:
            continue
        if cls:
            out.append(f'<g transform="translate({n(x0 + gx)},{n(y)})"><path class="{cls}" '
                       f'style="animation-delay:{i * step:.2f}s" d="{d}"/></g>')
        else:
            out.append(f'<path transform="translate({n(x0 + gx)},{n(y)})" d="{d}"/>')
    return f'<g fill="{fill}"{extra}>{"".join(out)}</g>'


# ------------------------------------------------------------------------ shapes

def blob_d(cx, cy, r, rnd, k=8, var=0.2):
    pts = []
    for i in range(k):
        a = 2 * math.pi * i / k
        rr = r * (1 + rnd.uniform(-var, var))
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d = f"M{n(pts[0][0])},{n(pts[0][1])}"
    for i in range(k):
        p0, p1, p2, p3 = (pts[(i + j) % k] for j in (-1, 0, 1, 2))
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f"C{n(c1[0])},{n(c1[1])} {n(c2[0])},{n(c2[1])} {n(p2[0])},{n(p2[1])}"
    return d + "Z"


def blob(cx, cy, r, seed, fill, dur=10, var=0.2, opacity=1.0):
    rnd = random.Random(seed)
    frames = [blob_d(cx, cy, r, rnd, var=var) for _ in range(3)]
    values = ";".join(frames + frames[:1])
    return (f'<path d="{frames[0]}" fill="{fill}" opacity="{opacity}">'
            f'<animate attributeName="d" dur="{dur}s" repeatCount="indefinite" values="{values}" '
            f'calcMode="spline" keyTimes="0;.33;.66;1" keySplines=".45 0 .55 1;.45 0 .55 1;.45 0 .55 1"/>'
            f'</path>')


def drip(x, y, s, fill):
    """A paint drop, like the ones falling off the lavender blobs."""
    return (f'<g transform="translate({n(x)},{n(y)}) scale({s})"><g class="drip">'
            f'<path d="M0,-18 C6,-8 12,0 12,8 C12,15 6,20 0,20 C-6,20 -12,15 -12,8 C-12,0 -6,-8 0,-18Z" '
            f'fill="{fill}"/></g></g>')


def sparkle(x, y, r, fill=None, delay=0.0, dur=2.4):
    fill = fill or C["gold"]
    return (f'<g transform="translate({n(x)},{n(y)})"><path class="tw" '
            f'style="animation-delay:{delay:.2f}s;animation-duration:{dur}s" '
            f'd="M0,{-r} Q0,0 {r},0 Q0,0 0,{r} Q0,0 {-r},0 Q0,0 0,{-r}Z" fill="{fill}"/></g>')


def heart_d(s):
    pts = [(0, .9), (-1.25, 0), (-1, -.95), (-.5, -.95), (-.18, -.95), (0, -.62), (0, -.45),
           (0, -.62), (.18, -.95), (.5, -.95), (1, -.95), (1.25, 0), (0, .9)]
    p = [(a * s, b * s) for a, b in pts]
    d = f"M{n(p[0][0])},{n(p[0][1])}"
    for i in range(1, len(p), 3):
        d += "C" + " ".join(f"{n(a)},{n(b)}" for a, b in p[i:i + 3])
    return d + "Z"


def heart(x, y, s, fill=None, stroke=None, sw=0, cls=None, style=""):
    fill = fill or C["pink"]
    st = f' stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"' if stroke else ""
    c = f' class="{cls}" style="{style}"' if cls else ""
    return f'<g transform="translate({n(x)},{n(y)})"><path{c} d="{heart_d(s)}" fill="{fill}"{st}/></g>'


def rising_heart(x, y, s, delay, dur=4.0, fill=None):
    return heart(x, y, s, fill=fill, cls="rise", style=f"animation-delay:{delay:.2f}s;animation-duration:{dur}s")


def star_d(r, inner=0.5, pts=5):
    d = ""
    for i in range(pts * 2):
        a = -math.pi / 2 + i * math.pi / pts
        rr = r if i % 2 == 0 else r * inner
        d += ("M" if i == 0 else "L") + f"{n(rr * math.cos(a))},{n(rr * math.sin(a))}"
    return d + "Z"


def star(x, y, r, face=False, delay=0.0, cls="wob"):
    face_svg = ""
    if face:
        k = r / 40
        face_svg = (f'<g stroke="{C["ink"]}" stroke-width="{n(3 * k)}" fill="none" stroke-linecap="round">'
                    f'<path d="M{n(-12 * k)},{n(0)} q{n(4 * k)},{n(-6 * k)} {n(8 * k)},0"/>'
                    f'<path d="M{n(4 * k)},0 q{n(4 * k)},{n(-6 * k)} {n(8 * k)},0"/>'
                    f'<path d="M{n(-4 * k)},{n(7 * k)} q{n(4 * k)},{n(5 * k)} {n(8 * k)},0"/></g>'
                    f'<ellipse cx="{n(-15 * k)}" cy="{n(7 * k)}" rx="{n(5 * k)}" ry="{n(3 * k)}" fill="{C["pink"]}"/>'
                    f'<ellipse cx="{n(15 * k)}" cy="{n(7 * k)}" rx="{n(5 * k)}" ry="{n(3 * k)}" fill="{C["pink"]}"/>')
    return (f'<g transform="translate({n(x)},{n(y)})"><g class="{cls}" style="animation-delay:{delay:.2f}s">'
            f'<path d="{star_d(r)}" fill="{C["gold"]}" stroke="{C["ink"]}" stroke-width="{n(max(2, r / 14))}" '
            f'stroke-linejoin="round"/>{face_svg}</g></g>')


def flower(x, y, s, fill=None, delay=0.0):
    fill = fill or C["lav"]
    petals = "".join(
        f'<circle cx="{n(math.cos(a) * s * .55)}" cy="{n(math.sin(a) * s * .55)}" r="{n(s * .42)}"/>'
        for a in (2 * math.pi * i / 5 - math.pi / 2 for i in range(5)))
    return (f'<g transform="translate({n(x)},{n(y)})"><g class="spin" style="animation-delay:{delay:.2f}s">'
            f'<g fill="{fill}">{petals}</g><circle r="{n(s * .3)}" fill="{C["gold"]}"/></g></g>')


def bow(x, y, s, fill=None, delay=0.0):
    fill = fill or C["lav2"]
    st = f'stroke="{C["ink"]}" stroke-width="{n(3 / s)}" stroke-linejoin="round"'
    return (f'<g transform="translate({n(x)},{n(y)}) scale({s})"><g class="wob" style="animation-delay:{delay:.2f}s">'
            f'<path d="M-6,6 L-24,44 L-12,40 L-6,50 L2,10Z M6,6 L24,44 L12,40 L6,50 L-2,10Z" fill="{fill}" {st}/>'
            f'<path d="M0,0 C-18,-32 -62,-34 -60,0 C-62,34 -18,32 0,0Z" fill="{fill}" {st}/>'
            f'<path d="M0,0 C18,-32 62,-34 60,0 C62,34 18,32 0,0Z" fill="{fill}" {st}/>'
            f'<path d="M-40,-10 Q-30,0 -40,10 M40,-10 Q30,0 40,10" fill="none" {st} opacity=".45"/>'
            f'<ellipse rx="12" ry="14" fill="{fill}" {st}/></g></g>')


def paw(x, y, s, fill, rot=0.0, cls="", style=""):
    c = f' class="{cls}" style="{style}"' if cls else ""
    return (f'<g transform="translate({n(x)},{n(y)}) rotate({rot}) scale({s})"><g{c} fill="{fill}">'
            f'<path d="M0,2 C9,2 15,9 14,15 C13,21 7,20 0,20 C-7,20 -13,21 -14,15 C-15,9 -9,2 0,2Z"/>'
            f'<ellipse cx="-12" cy="-6" rx="4.6" ry="6" transform="rotate(-20 -12 -6)"/>'
            f'<ellipse cx="-4.5" cy="-12" rx="4.6" ry="6.2"/>'
            f'<ellipse cx="4.5" cy="-12" rx="4.6" ry="6.2"/>'
            f'<ellipse cx="12" cy="-6" rx="4.6" ry="6" transform="rotate(20 12 -6)"/></g></g>')


def confetti(w, h, count, seed, top=-30):
    rnd = random.Random(seed)
    out = []
    for i in range(count):
        x = rnd.uniform(20, w - 20)
        col = rnd.choice(CONFETTI)
        dur = rnd.uniform(6, 11)
        delay = -rnd.uniform(0, dur)
        kind = rnd.random()
        if kind < 0.45:
            shape = f'<rect x="-4" y="-2" width="8" height="4" rx="1.5" fill="{col}"/>'
        elif kind < 0.75:
            shape = f'<circle r="{n(rnd.uniform(2.2, 3.6))}" fill="{col}"/>'
        else:
            shape = f'<path d="M-5,0 q2.5,-4 5,0 t5,0" fill="none" stroke="{col}" stroke-width="2.2" stroke-linecap="round"/>'
        out.append(f'<g transform="translate({n(x)},{top})"><g class="fall" '
                   f'style="animation-duration:{dur:.1f}s;animation-delay:{delay:.1f}s;--h:{h - top + 40}px">'
                   f'{shape}</g></g>')
    return "".join(out)


def squiggle(d, color, width=2.4, delay=0.0):
    return (f'<path class="draw" style="animation-delay:{delay:.1f}s" d="{d}" fill="none" stroke="{color}" '
            f'stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round" pathLength="100"/>')


# --------------------------------------------------------------------------- cat

HEAD = "M-70,8 C-72,-38 -38,-56 0,-56 C38,-56 72,-38 70,8 C68,42 38,54 0,54 C-38,54 -68,42 -70,8Z"
EAR = "M-64,-14 Q-66,-60 -54,-80 Q-49,-87 -43,-81 Q-28,-66 -10,-52Z"
EAR_IN = "M-55,-34 Q-55,-60 -50,-70 Q-39,-61 -28,-50Z"
BODY = "M-50,30 C-62,70 -64,120 -62,160 L62,160 C64,120 62,70 50,30Z"
SIT_BODY = "M-50,30 C-80,78 -80,128 -42,134 L42,134 C80,128 80,78 50,30Z"

HATS = {
    "red": (C["red"], C["white"], C["white"]),
    "lav": (C["lav2"], C["white"], C["gold"]),
    "gold": (C["gold"], C["red"], C["white"]),
    "pink": (C["pink"], C["white"], C["lav2"]),
}


def party_hat(kind, x, y, angle, delay):
    body, dots, pom = HATS[kind]
    st = f'stroke="{C["ink"]}" stroke-width="3" stroke-linejoin="round"'
    dot_svg = "".join(f'<circle cx="{a}" cy="{b}" r="{r}" fill="{dots}"/>'
                      for a, b, r in ((-9, -10, 3.4), (8, -20, 3.2), (-2, -34, 2.8), (10, -5, 2.6), (-8, -26, 2.2)))
    return (f'<g transform="translate({x},{y}) rotate({angle})"><g class="hat" style="animation-delay:{delay:.2f}s">'
            f'<path d="M-22,0 L-3,-58 Q0,-64 3,-58 L22,0 Q0,7 -22,0Z" fill="{body}" {st}/>{dot_svg}'
            f'<path d="M-22,0 Q0,7 22,0" fill="none" {st}/>'
            f'<circle cy="-62" r="7" fill="{pom}" {st}/></g></g>')


def eyes(kind, uid):
    ink = C["ink"]
    happy = lambda cx: f'<path d="M{cx - 10},6 Q{cx},-6 {cx + 10},6" fill="none" stroke="{ink}" stroke-width="4" stroke-linecap="round"/>'
    sleep = lambda cx: f'<path d="M{cx - 10},2 Q{cx},10 {cx + 10},2" fill="none" stroke="{ink}" stroke-width="4" stroke-linecap="round"/>'
    opn = lambda cx, d: (f'<g transform="translate({cx},2)"><g class="blink" style="animation-delay:{d}s">'
                         f'<ellipse rx="6.5" ry="8" fill="{ink}"/><circle cx="2.2" cy="-3" r="2.2" fill="#fff"/></g></g>')
    d = (uid * 0.7) % 3
    return {
        "happy": happy(-30) + happy(30),
        "sleep": sleep(-30) + sleep(30),
        "open": opn(-30, d) + opn(30, d),
        "wink": opn(-30, d) + happy(30),
    }[kind]


def cat(uid, x, y, s=1.0, eye="happy", patch=None, hat=None, hat_side=1, extra_front="",
        body=BODY, delay=0.0, ear_fill=None, bow_on=False, tail=False):
    """A chubby cartoon cat. Local coords: head centred on (0,0), about 150 wide."""
    ink, st = C["ink"], f'stroke="{C["ink"]}" stroke-width="3.5" stroke-linejoin="round"'
    clip = f"hc{uid}"
    ear_fill = ear_fill or C["white"]

    patch_svg = ""
    if patch == "grey":
        patch_svg = f'<ellipse cx="-44" cy="-30" rx="36" ry="30" fill="{C["grey"]}"/><ellipse cx="52" cy="40" rx="20" ry="14" fill="{C["grey"]}"/>'
    elif patch == "brown":
        patch_svg = f'<path d="M-80,-16 Q-30,-30 0,-14 Q30,-30 80,-16 L80,-80 L-80,-80Z" fill="{C["patch"]}"/>'
    elif patch == "spot":
        patch_svg = f'<ellipse cx="40" cy="-34" rx="28" ry="22" fill="{C["patch"]}"/><ellipse cx="-50" cy="30" rx="16" ry="12" fill="{C["grey"]}"/>'
    elif patch == "black":
        patch_svg = f'<path d="{HEAD}" fill="#4B4442"/>'

    head_fill = C["white"]
    tail_svg = ""
    if tail:
        tail_svg = (f'<g transform="translate(54,112)"><g class="tail">'
                    f'<path d="M0,0 C30,4 52,-20 44,-56 C40,-70 28,-70 30,-56 C36,-30 22,-12 -4,-12Z" '
                    f'fill="{C["white"]}" {st}/></g></g>')
    ears = (f'<path d="{EAR}" fill="{ear_fill}" {st}/><path d="{EAR_IN}" fill="{C["pink_soft"]}"/>'
            f'<g transform="scale(-1,1)"><path d="{EAR}" fill="{ear_fill}" {st}/><path d="{EAR_IN}" fill="{C["pink_soft"]}"/></g>')
    if patch == "black":
        ears = ears.replace(C["pink_soft"], "#8C6F79")
    face = (f'<ellipse cx="-46" cy="20" rx="11" ry="6.5" fill="{C["pink"]}" opacity=".8"/>'
            f'<ellipse cx="46" cy="20" rx="11" ry="6.5" fill="{C["pink"]}" opacity=".8"/>'
            + eyes(eye, uid) +
            f'<path d="M-5,12 L5,12 L0,17Z" fill="#F08AA3" stroke="#F08AA3" stroke-width="2.5" stroke-linejoin="round"/>'
            f'<path d="M0,17 Q-3,25 -10,22 M0,17 Q3,25 10,22" fill="none" stroke="{ink}" stroke-width="3" stroke-linecap="round"/>'
            f'<path d="M-60,12 L-82,7 M-60,21 L-82,24 M60,12 L82,7 M60,21 L82,24" stroke="{ink}" stroke-width="2.4" stroke-linecap="round"/>')
    if patch == "black":
        face = face.replace(f'stroke="{ink}"', 'stroke="#F3EDE8"').replace(f'fill="{ink}"', 'fill="#FFF6D6"')
    paws = (f'<g {st} fill="{C["white"]}"><ellipse cx="-28" cy="54" rx="17" ry="11"/><ellipse cx="28" cy="54" rx="17" ry="11"/></g>'
            f'<path d="M-32,49 v6 M-24,49 v6 M24,49 v6 M32,49 v6" stroke="{ink}" stroke-width="2.2" stroke-linecap="round"/>')
    hat_svg = party_hat(hat, 20 * hat_side, -52, 14 * hat_side, delay) if hat else ""
    bow_svg = bow(-44, -58, 0.32, delay=delay) if bow_on else ""
    return (f'<g transform="translate({n(x)},{n(y)}) scale({s})"><g class="bob" style="animation-delay:{delay:.2f}s">'
            f'<clipPath id="{clip}"><path d="{HEAD}"/></clipPath>'
            f'{tail_svg}<path d="{body}" fill="{C["white"]}" {st}/>{ears}'
            f'<path d="{HEAD}" fill="{head_fill}"/><g clip-path="url(#{clip})">{patch_svg}</g>'
            f'<path d="{HEAD}" fill="none" {st}/>{face}{extra_front or paws}{hat_svg}{bow_svg}</g></g>')


# ------------------------------------------------------------------------ styles

STYLE = """<style>
.bob{animation:bob 3.2s ease-in-out infinite;transform-box:fill-box;transform-origin:50% 100%}
@keyframes bob{0%,100%{transform:translateY(0) rotate(0)}50%{transform:translateY(-5px) rotate(-1.6deg)}}
.blink{animation:blink 4.5s infinite;transform-box:fill-box;transform-origin:center}
@keyframes blink{0%,90%,100%{transform:scaleY(1)}94%{transform:scaleY(.1)}}
.hat{animation:hat 2.6s ease-in-out infinite;transform-box:fill-box;transform-origin:50% 100%}
@keyframes hat{0%,100%{transform:rotate(-6deg)}50%{transform:rotate(6deg)}}
.fall{animation:fall linear infinite;transform-box:fill-box;transform-origin:center}
@keyframes fall{0%{transform:translateY(0) rotate(0);opacity:0}8%{opacity:1}85%{opacity:1}100%{transform:translateY(var(--h)) rotate(720deg);opacity:0}}
.tw{animation:tw 2.4s ease-in-out infinite;transform-box:fill-box;transform-origin:center}
@keyframes tw{0%,100%{transform:scale(.5) rotate(0);opacity:.5}50%{transform:scale(1.15) rotate(45deg);opacity:1}}
.rise{animation:rise 4s ease-out infinite;transform-box:fill-box;transform-origin:center;opacity:0}
@keyframes rise{0%{transform:translateY(0) scale(.4);opacity:0}20%{opacity:1}100%{transform:translate(8px,-110px) scale(1.1);opacity:0}}
.hop{animation:hop 2.8s ease-in-out infinite;transform-box:fill-box;transform-origin:50% 100%}
@keyframes hop{0%,50%,100%{transform:translateY(0) scale(1)}22%{transform:translateY(-14px) scale(1.04,.97)}36%{transform:translateY(2px) scale(1.03,.96)}}
.wob{animation:wob 3.6s ease-in-out infinite;transform-box:fill-box;transform-origin:center}
@keyframes wob{0%,100%{transform:rotate(-8deg) scale(1)}50%{transform:rotate(8deg) scale(1.06)}}
.spin{animation:spin 12s linear infinite;transform-box:fill-box;transform-origin:center}
@keyframes spin{to{transform:rotate(360deg)}}
.drip{animation:drip 5s ease-in infinite;transform-box:fill-box;transform-origin:50% 0}
@keyframes drip{0%{transform:translateY(-6px) scale(.2);opacity:0}25%{transform:translateY(0) scale(1);opacity:1}70%{opacity:1}100%{transform:translateY(60px) scale(.8);opacity:0}}
.draw{stroke-dasharray:100;animation:draw 6s ease-in-out infinite}
@keyframes draw{0%{stroke-dashoffset:100}40%,75%{stroke-dashoffset:0}100%{stroke-dashoffset:-100}}
.float{animation:float 4s ease-in-out infinite}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}
.ear{animation:ear 5s ease-in-out infinite;transform-box:fill-box;transform-origin:50% 100%}
@keyframes ear{0%,86%,100%{transform:rotate(0)}90%{transform:rotate(-14deg)}94%{transform:rotate(6deg)}}
.tail{animation:tail 2.2s ease-in-out infinite;transform-box:fill-box;transform-origin:0 100%}
@keyframes tail{0%,100%{transform:rotate(-6deg)}50%{transform:rotate(10deg)}}
.zz{animation:zz 3.6s ease-out infinite;opacity:0}
@keyframes zz{0%{transform:translate(0,0) scale(.6);opacity:0}25%{opacity:1}100%{transform:translate(26px,-60px) scale(1.2);opacity:0}}
.walk{animation:walk 4.8s ease-in-out infinite}
@keyframes walk{0%{opacity:0;transform:scale(.6)}8%,40%{opacity:1;transform:scale(1)}55%,100%{opacity:0;transform:scale(1)}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
</style>"""


def svg(w, h, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{title}"><title>{title}</title>{STYLE}{body}</svg>')


def card(w, h, inner, uid, pad=8, r=32):
    return (f'<clipPath id="card{uid}"><rect x="{pad}" y="{pad}" width="{w - 2 * pad}" height="{h - 2 * pad}" rx="{r}"/></clipPath>'
            f'<rect x="{pad}" y="{pad}" width="{w - 2 * pad}" height="{h - 2 * pad}" rx="{r}" fill="{C["cream"]}"/>'
            f'<g clip-path="url(#card{uid})">{inner}</g>'
            f'<rect x="{pad}" y="{pad}" width="{w - 2 * pad}" height="{h - 2 * pad}" rx="{r}" fill="none" '
            f'stroke="{C["border"]}" stroke-width="3"/>')


# ----------------------------------------------------------------------- assets

def header():
    W, H = 1000, 470
    doodles = (
        squiggle("M770,70 c10,-24 40,-20 36,4 c-3,20 -30,18 -26,0 c4,-16 26,-10 20,4", C["brown2"], 2.6)
        + squiggle("M836,48 q14,10 8,26 q-6,16 10,26", C["brown2"], 2.6, 1.2)
        + squiggle("M196,240 q18,-16 34,0 t34,0", C["lav3"], 2.6, 0.6)
        + heart(716, 118, 8, fill="none", stroke=C["brown2"], sw=2.2)
        + heart(300, 60, 7, fill="none", stroke=C["brown2"], sw=2.2)
        + f'<circle cx="880" cy="118" r="4" fill="none" stroke="{C["brown2"]}" stroke-width="2.2"/>'
        + f'<circle cx="140" cy="150" r="3.5" fill="none" stroke="{C["brown2"]}" stroke-width="2.2"/>'
    )
    sub_l, sub_r = "Full-Stack Developer", "Thailand"
    gap = 44
    wl, wr = SEMI.width(sub_l, 27), SEMI.width(sub_r, 27)
    x0 = W / 2 - (wl + gap + wr) / 2
    subtitle = (text(SEMI, sub_l, 27, x0, 222, C["brown2"], anchor="start")
                + heart(x0 + wl + gap / 2, 212, 9, fill=C["pink"])
                + text(SEMI, sub_r, 27, x0 + wl + gap, 222, C["brown2"], anchor="start"))
    cats = (cat(1, 250, 378, .9, "happy", "grey", "red", -1, delay=0)
            + cat(2, 415, 384, .86, "open", None, "pink", 1, delay=.5)
            + cat(3, 585, 382, .88, "happy", "brown", "red", 1, delay=1.0)
            + cat(4, 752, 378, .9, "wink", "spot", "lav", -1, delay=1.5))
    inner = (
        blob(40, 40, 150, 3, C["lav"], 11)
        + blob(980, 250, 150, 7, C["lav"], 13)
        + blob(870, 470, 80, 11, C["lav_soft"], 9)
        + drip(150, 170, 1.0, C["lav"]) + drip(866, 410, .8, C["lav"])
        + doodles
        + confetti(W, H, 30, 42)
        + flower(96, 250, 26, delay=0) + flower(914, 96, 20, C["pink_soft"], 2)
        + star(128, 350, 26, face=True, delay=.4) + star(930, 330, 18, delay=1.3)
        + sparkle(220, 140, 12) + sparkle(800, 170, 14, delay=.8) + sparkle(60, 330, 9, C["lav2"], 1.4)
        + sparkle(660, 60, 9, C["lav2"], .3) + sparkle(350, 250, 8, delay=1.1) + sparkle(690, 250, 8, C["pink"], .5)
        + text(BOLD, "PAPHOP", 128, W / 2 + 5, 172, C["lav"], ls=4)
        + text(BOLD, "PAPHOP", 128, W / 2, 166, C["brown"], ls=4, cls="hop", step=.13)
        + subtitle
        + rising_heart(330, 330, 7, 0) + rising_heart(500, 320, 6, 1.4, fill=C["lav2"]) + rising_heart(670, 330, 7, 2.6)
        + cats
    )
    return svg(W, H, card(W, H, inner, "h"), "PAPHOP - Full-Stack Developer from Thailand")


SECTIONS = [
    ("about", "About Me", "flower", "paw"),
    ("stack", "Tech Stack", "star", "flower"),
    ("facts", "Fun Facts", "star", "heart"),
]


def deco(kind, x, y, delay):
    return {
        "flower": flower(x, y, 20, delay=delay),
        "star": star(x, y, 20, face=True, delay=delay),
        "heart": f'<g class="float" style="animation-delay:{delay}s">{heart(x, y, 16, stroke=C["ink"], sw=2.6)}</g>',
        "bow": bow(x, y, .42, delay=delay),
        "paw": paw(x, y, 1.3, C["lav2"], rot=-15, cls="wob", style=f"animation-delay:{delay}s"),
    }[kind]


def section_title(slug, label, left, right, i):
    W, H = 1000, 130
    size = 40
    tw = BOLD.width(label, size, 1)
    pw, ph = tw + 110, 70
    x0, y0 = (W - pw) / 2, 42
    ink = f'stroke="{C["brown2"]}" stroke-width="3" stroke-linejoin="round"'
    ear = lambda cx, flip, cls: (
        f'<g transform="translate({n(cx)},{y0 + 10}) scale({flip},1)"><g class="{cls}">'
        f'<path d="M-20,8 Q-16,-26 -4,-34 Q2,-37 6,-31 Q16,-12 22,8Z" fill="{C["cream"]}" {ink}/>'
        f'<path d="M-10,2 Q-8,-18 -1,-24 Q8,-10 11,2Z" fill="{C["pink_soft"]}"/></g></g>')
    whisk = (f'<g stroke="{C["lav2"]}" stroke-width="2.6" stroke-linecap="round">'
             f'<path d="M{n(x0 - 6)},{y0 + 30} l-24,-6 M{n(x0 - 6)},{y0 + 42} l-24,4"/>'
             f'<path d="M{n(x0 + pw + 6)},{y0 + 30} l24,-6 M{n(x0 + pw + 6)},{y0 + 42} l24,4"/></g>')
    pill = (
        f'<g class="float">'
        + ear(x0 + 46, 1, "ear") + ear(x0 + pw - 46, -1, "")
        + f'<rect x="{n(x0)}" y="{y0 + 7}" width="{n(pw)}" height="{ph}" rx="35" fill="{C["lav"]}"/>'
        + f'<rect x="{n(x0)}" y="{y0}" width="{n(pw)}" height="{ph}" rx="35" fill="{C["cream"]}" {ink}/>'
        + f'<ellipse cx="{n(x0 + 30)}" cy="{y0 + 44}" rx="9" ry="5" fill="{C["pink"]}" opacity=".8"/>'
        + f'<ellipse cx="{n(x0 + pw - 30)}" cy="{y0 + 44}" rx="9" ry="5" fill="{C["pink"]}" opacity=".8"/>'
        + text(BOLD, label, size, W / 2, y0 + 49, C["brown"], ls=1, cls="hop", step=.08)
        + whisk + '</g>'
    )
    body = (
        deco(left, x0 - 80, y0 + 36, 0) + deco(right, x0 + pw + 80, y0 + 36, .7)
        + sparkle(x0 - 132, y0 + 8, 10, delay=.2) + sparkle(x0 + pw + 130, y0 + 60, 10, C["lav2"], .9)
        + sparkle(x0 - 120, y0 + 66, 7, C["pink"], 1.5) + sparkle(x0 + pw + 136, y0 + 6, 7, delay=1.2)
        + pill
    )
    return svg(W, H, body, label)


def about_card():
    W, H = 500, 460
    k = 1.3
    carton = (
        f'<g stroke="{C["ink"]}" stroke-width="3" stroke-linejoin="round">'
        f'<path d="M6,54 L-2,20" stroke="{C["pink"]}" stroke-width="5" stroke-linecap="round"/>'
        f'<path d="M-26,66 L-20,52 L20,52 L26,66Z" fill="{C["pink_soft"]}"/>'
        f'<rect x="-26" y="66" width="52" height="60" rx="6" fill="{C["white"]}"/>'
        f'<rect x="-26" y="66" width="52" height="16" fill="{C["pink"]}"/></g>'
        f'<path d="M0,104 C-9,96 -9,88 -3,86 C0,85 0,87 0,88 C0,87 0,85 3,86 C9,88 9,96 0,104Z" fill="{C["red"]}"/>'
        f'<path d="M-4,86 q4,-6 8,0" fill="none" stroke="#7FB27A" stroke-width="2.6" stroke-linecap="round"/>'
        f'<circle cx="-2" cy="94" r=".9" fill="#FFE9A8"/><circle cx="2" cy="98" r=".9" fill="#FFE9A8"/>'
        + text(BOLD, "MILK", 10, 0, 118, C["brown"], ls=.5)
        + f'<g stroke="{C["ink"]}" stroke-width="3.5" fill="{C["white"]}">'
        f'<ellipse cx="-30" cy="96" rx="13" ry="11"/><ellipse cx="30" cy="96" rx="13" ry="11"/></g>'
        f'<g stroke="{C["ink"]}" stroke-width="3" fill="{C["white"]}">'
        f'<ellipse cx="-30" cy="136" rx="20" ry="10"/><ellipse cx="30" cy="136" rx="20" ry="10"/></g>'
    )
    inner = (
        blob(470, 40, 110, 5, C["lav"], 10)
        + blob(20, 440, 90, 9, C["lav_soft"], 12)
        + drip(420, 150, .8, C["lav"])
        + confetti(W, H, 12, 7)
        + flower(60, 70, 22) + star(430, 300, 20, face=True, delay=.3)
        + sparkle(110, 150, 11) + sparkle(400, 200, 9, C["lav2"], .6) + sparkle(80, 300, 8, C["pink"], 1.2)
        + squiggle("M60,200 q16,-14 30,0 t30,0", C["lav3"], 2.4)
        + cat(9, 250, 184, k, "happy", "grey", None, extra_front=carton, body=SIT_BODY, bow_on=True, tail=True)
        + rising_heart(318, 250, 7, 0) + rising_heart(332, 240, 5, 1.6, fill=C["lav2"]) + rising_heart(180, 250, 6, 2.8)
        + text(BOLD, "Powered by", 22, W / 2, 404, C["brown2"])
        + text(BOLD, "Strawberry Milk", 30, W / 2, 438, C["brown"], cls="hop", step=.07)
    )
    return svg(W, H, card(W, H, inner, "a", r=30), "A cat sipping strawberry milk")


def divider():
    W, H = 1000, 60
    steps = 14
    out = []
    for i in range(steps):
        x = 90 + i * (820 / (steps - 1))
        y = 24 if i % 2 == 0 else 40
        col = C["lav2"] if i % 3 else C["pink"]
        out.append(paw(x, y, .8, col, rot=90, cls="walk",
                       style=f"animation-delay:{i * 4.8 / steps / 1.6 - 4.8:.2f}s;transform-box:fill-box;transform-origin:center"))
    return svg(W, H, "".join(out), "Paw prints")


def footer():
    W, H = 1000, 360
    zz = "".join(
        f'<g transform="translate(360,{205 - j * 4})"><g class="zz" style="animation-delay:{j * 1.2 - 3.6:.1f}s">'
        + text(BOLD, "z", 20 + j * 4, 0, 0, C["lav3"]) + '</g></g>' for j in range(3))
    cats = (cat(21, 180, 300, .72, "happy", "brown", "gold", -1, delay=.2)
            + cat(22, 335, 304, .7, "sleep", "grey", None, delay=.8)
            + cat(23, 500, 300, .74, "open", "black", "red", 1, delay=1.4)
            + cat(24, 665, 304, .7, "happy", None, "lav", -1, delay=.4, bow_on=True)
            + cat(25, 820, 300, .72, "wink", "spot", "pink", 1, delay=1.0))
    inner = (
        blob(0, 0, 120, 21, C["lav"], 12)
        + blob(1000, 330, 120, 23, C["lav"], 10)
        + confetti(W, H, 24, 99)
        + bow(900, 70, .75, delay=.2)
        + star(96, 150, 22, face=True, delay=.5)
        + flower(840, 170, 18, C["pink_soft"])
        + sparkle(200, 60, 12) + sparkle(760, 50, 10, C["lav2"], .7) + sparkle(130, 250, 8, C["pink"], 1.3)
        + sparkle(880, 250, 9, delay=1.8)
        + squiggle("M620,160 q14,-12 28,0 t28,0", C["lav3"], 2.4)
        + text(BOLD, "Thanks for visiting!", 60, W / 2 + 4, 110, C["lav"])
        + text(BOLD, "Thanks for visiting!", 60, W / 2, 105, C["brown"], cls="hop", step=.07)
        + text(SEMI, "see you in the next commit", 24, W / 2 - 12, 150, C["brown2"])
        + heart(W / 2 + SEMI.width("see you in the next commit", 24) / 2 + 6, 142, 8)
        + zz + cats
    )
    return svg(W, H, card(W, H, inner, "f"), "Thanks for visiting")


def main():
    global BOLD, SEMI
    BOLD, SEMI = Font(700), Font(600)
    os.makedirs(OUT, exist_ok=True)
    files = {"header.svg": header(), "about-cat.svg": about_card(),
             "divider.svg": divider(), "footer.svg": footer()}
    for i, (slug, label, left, right) in enumerate(SECTIONS):
        files[f"title-{slug}.svg"] = section_title(slug, label, left, right, i)
    for name, content in files.items():
        with open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        print(f"{name:26s} {len(content) / 1024:6.1f} KB")


if __name__ == "__main__":
    main()
