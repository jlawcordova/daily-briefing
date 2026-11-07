"""What the Daily Brief's drawings share: the kit, round things built from
stacked 2:1 ellipses (dishes, domes, pucks), steam, and saving.

Every food is drawn around (0, 0), the middle of the table it stands on, the
pixel corner the dish stands on. Light comes from the upper left: a round thing is
lit down its left, shaded down its right, its top the lightest."""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(ART, 'kit'))
from kit import *  # noqa: E402,F401,F403
from kit import Pic, ellipse, line, sprite  # noqa: E402

DOC = os.path.join(ART, 'daily-brief.pixpocket')
BUILD = os.path.join(ART, 'build')  # generated, not in git
OUT = os.path.join(BUILD, 'objects')
SCENES_OUT = os.path.join(BUILD, 'scenes')
LIBRARY = 'Daily Brief'

# Materials, light to dark.
PORCELAIN = ('cream', 'path-1', 'path-2', 'path-3')
STEEL = ('stone-1', 'stone-2', 'stone-3', 'stone-4')
BAMBOO = ('gold-1', 'gold-2', 'gold-3', 'gold-4')
BUN = ('clay-1', 'clay-2', 'clay-3', 'clay-4')
CRUST = ('gold-1', 'clay-1', 'clay-2', 'clay-3')
BEEF = ('brick-1', 'brick-2', 'brick-3', 'brick-4')
CHOC = ('wood-2', 'wood-3', 'wood-4', 'soil-4')
LEAF = ('grass-1', 'grass-2', 'grass-3', 'grass-4')
TOMATO = ('roof-1', 'roof-2', 'roof-3', 'roof-4')
UBE = ('plum-1', 'plum-2', 'plum-3', 'plum-4')
CARDBOARD = ('wood-1', 'wood-2', 'wood-3', 'wood-4')


def cat(sub):
    return [LIBRARY, sub]


def even(n):
    n = int(round(n))
    return n - (n % 2)


def across(side, w):
    """A color function for ellipse: the side's shades from the lit left edge to the dark right."""
    n = len(side)
    return lambda x, y: side[max(0, min(n - 1, int((x + w / 2) / w * n)))]


def dish(p, cx, cy, w, h, side, foot=None, top_c=None):
    """A round dish or a pot, its rim an ellipse w wide on (cx, cy) and its
    body h pixels down to a foot `foot` wide (as wide as the rim: a puck).
    Returns the rim's pixels; with top_c the rim's top is filled."""
    foot = w if foot is None else foot
    for k in range(h, 0, -1):
        ww = even(w + (foot - w) * k / h)
        ellipse(p, cx, cy + k, max(2, ww), across(side, ww))
    if top_c:
        return ellipse(p, cx, cy, w, top_c)
    return ellipse(Pic(), cx, cy, w, None)


def front_edge(cx, cy, w):
    """The front edge of an ellipse w wide on (cx, cy): {x: its lowest y}."""
    out = {}
    for (x, y) in ellipse(Pic(), cx, cy, w, None):
        out[x] = max(out.get(x, y), y)
    return out


def band(p, cx, cy, w, n, color):
    """A band n pixels tall round the front of a round thing's side, its
    bottom on the front edge of the ellipse w wide on (cx, cy). `color` may
    be fn(x, t), t rows up from the bottom."""
    for x, y in front_edge(cx, cy, w).items():
        for t in range(n):
            p.put(x, y - t, color(x, t) if callable(color) else color)


def bowl(p, cx, cy, w, h, side, rim, inside, foot_frac=0.55):
    """A bowl: its body tapering to a foot, a rim band of `rim` and its
    inside `inside` (a color or a function) an ellipse 4 narrower."""
    dish(p, cx, cy, w, h, side, foot=even(w * foot_frac))
    ellipse(p, cx, cy, w, rim)
    return ellipse(p, cx, cy, w - 4, inside)


def plate(p, cx, cy, w, side=PORCELAIN):
    """A plate: a puck two pixels thick, its well a step darker inside a rim."""
    dish(p, cx, cy, w, 2, side[1:], top_c=side[0])
    ellipse(p, cx, cy, w - 8, side[1])
    ellipse(p, cx, cy + 1, w - 12, side[0])


def dome(p, cx, cy, w, h, ramp, lean=0.0, color=None):
    """A mound on (cx, cy): stacked ellipses rising h pixels, narrowing as a
    half ball, shaded in four bands lit from the upper left. With color,
    color(x, y, shade) picks the pixel (x, y from the centre) instead."""
    for k in range(0, h + 1):
        f = math.sqrt(max(0.0, 1 - (k / (h + 0.5)) ** 2))
        ww = even(w * f)
        if ww < 2:
            continue
        def c(x, y, k=k, ww=ww):
            nx = x / (w / 2)
            b = 0.75 * (k / h) - 0.7 * nx + 0.35 * (-y / (ww / 4 + 0.5)) * 0.5
            i = 0 if b > 0.62 else 1 if b > 0.05 else 2 if b > -0.45 else 3
            i = min(len(ramp) - 1, i)
            return color(x, y - k, i) if color else ramp[i]
        ellipse(p, cx + round(lean * k), cy - k, ww, c)


def steam(p, x, y, k, n=3, tall=16, spread=6, c='cream'):
    """Wisps rising from (x, y): n of them, `spread` apart, each a wavy line
    with gaps that climb as k (0 to 5) goes on."""
    for i in range(n):
        x0 = x + (i - (n - 1) / 2) * spread
        for d in range(tall):
            yy = y - d
            phase = (d + k * 3 + i * 5) % 18
            if phase >= 11:
                continue
            wob = round(1.5 * math.sin((d + i * 4) / 3.0))
            p.put(int(x0 + wob), yy, c)
            if d < tall - 5:
                p.put(int(x0 + wob) + 1, yy, c)


def stick(p, x0, y0, n, c, c2=None, dx=1):
    """A thin stick along a 2:1 line from (x0, y0), n pixels across, climbing
    to the right (dx = 1); with c2 it's two pixels thick, c2 underneath."""
    for i in range(n):
        x, y = x0 + i * dx, y0 - i // 2
        p.put(x, y, c)
        if c2:
            p.put(x, y + 1, c2)


def save(name, obj):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name + '.json'), 'w') as f:
        json.dump(obj, f)


def save_scene(name, obj):
    os.makedirs(SCENES_OUT, exist_ok=True)
    with open(os.path.join(SCENES_OUT, name + '.json'), 'w') as f:
        json.dump(obj, f)


def looped(frames, category, notes, ms, name='glow', extra=None, start=None):
    """A sprite whose frames loop in one state (plus any extra states)."""
    states = {name: {'frames': list(range(len(frames))), 'ms': ms}}
    states.update(extra or {})
    return sprite(frames, category, notes, states=states, start=start or name)


def halves(frames):
    """A drawing wider than a sprite, cut at x = 0 into its left and right
    halves (each a list of frames), placed together on the same anchor."""
    if isinstance(frames, Pic):
        frames = [frames]
    return ([Pic({q: c for q, c in f.items() if q[0] < 0}) for f in frames],
            [Pic({q: c for q, c in f.items() if q[0] >= 0}) for f in frames])
