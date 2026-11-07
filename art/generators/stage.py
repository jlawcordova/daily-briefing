"""The light every spot of the day is shown in: a sky of rays behind the
table that turns, cream near the food in a glow that breathes, and the
glints that twinkle on the food. The table and the food stand still; only
the light moves (and what's hot: steam, a grill's coals, a candle)."""
import math
from draw import *

# The stage's box: what a brief scene shows, the middle of the table's top at (0, 0).
BOX = (-88, -58, 176, 110)
CENTRE = (0, -16)            # where the light comes from: the food's middle
RAYS = 12                    # rays round the circle, a ray and a gap each 15°
TURN = 6                     # frames to turn one ray on to the next


# ------------------------------------------------------------------ the light
# The lights: name -> (the sky between the rays, the rays), each from one ramp.
LIGHTS = {
    'blue': ('glass-2', 'glass-1'),
    'teal': ('teal-2', 'teal-1'),
    'plum': ('plum-2', 'plum-1'),
    'gold': ('gold-2', 'gold-1'),
    'sunset': ('clay-2', 'clay-1'),
    'green': ('grass-2', 'grass-1'),
}


def rays(k, half, pale='glass-1'):
    """The sky of rays over the stage's box, turned k / TURN of a ray on,
    one half of the box (0 left, 1 right: a sprite is at most 128 wide).
    The rays are the light's pale shade, and near the food they glow: cream
    rays on that shade out to a radius that breathes as they turn. The
    deeper shade between the rays further out is the light's sky."""
    p = Pic()
    x0, y0, w, h = BOX
    xs = range(x0, 0) if half == 0 else range(0, x0 + w)
    step = 2 * math.pi / RAYS
    turn = step * k / TURN
    glow = GLOW[k]
    for x in xs:
        for y in range(y0, y0 + h):
            dx, dy = x + 0.5 - CENTRE[0], y + 0.5 - CENTRE[1]
            ray = (math.atan2(dy, dx) - turn) % step < step / 2
            near = math.hypot(dx, dy) < glow
            if ray:
                p.put(x, y, 'cream' if near else pale)
            elif near:
                p.put(x, y, pale)
    return p


GLOW = (38, 40, 42, 44, 42, 40)


def sky(half, color='glass-2'):
    """The sky behind the rays: the box's half in one color."""
    p = Pic()
    x0, y0, w, h = BOX
    xs = range(x0, 0) if half == 0 else range(0, x0 + w)
    for x in xs:
        for y in range(y0, y0 + h):
            p.put(x, y, color)
    return p


# ------------------------------------------------------------------ glints
def star(r):
    """A four-point glint with arms r long, its core 2×2 on a pixel corner."""
    p = Pic()
    if r < 0:
        return p
    for a in (-1, 0):
        for b in (-1, 0):
            p.put(a, b, 'cream')
        for d in range(1, r + 1):
            c = 'gold-1' if d == r else 'cream'
            for x, y in ((-1 - d, a), (d, a), (a, -1 - d), (a, d)):
                p.put(x, y, c)
    return p


GLINT = (0, 2, 4, 2, 0, -1, -1, -1, -1, -1)       # a dot, out to a star and back, then a rest


def build_stage():
    for light, (deep, pale) in LIGHTS.items():
        for half, side in ((0, 'left'), (1, 'right')):
            save(f'brief-sky-{light}-{side}', sprite(sky(half, deep), cat('Light'), [
                f'The {side} half of the stage\'s {light} sky, one color ({deep}), behind its rays '
                f'(`brief-rays-{light}-{side}`).',
                'Place it by pixel (px) at the table\'s anchor, at depth Back, before the rays.']))
            save(f'brief-rays-{light}-{side}', looped([rays(k, half, pale) for k in range(TURN)], cat('Light'), [
                f'The {side} half of the {light} rays behind the table: twelve rays of {pale} from the food\'s middle '
                'out past the box, turning steadily round, cream near the food in a glow that breathes.',
                'Place it by pixel (px) at the table\'s anchor, at depth Back, over its sky.',
                f'States: turn (a twelfth of a turn in {TURN} frames, 100 ms each, looping, so the rays turn on and on).'],
                100, name='turn'))
    frames = [star(r) for r in GLINT]
    n = len(frames)
    states = {f'twinkle-{i}': {'frames': [(j + i * 3) % n for j in range(n)], 'ms': 100} for i in range(3)}
    save('brief-glint', sprite(frames, cat('Light'), [
        'A glint of shine on the food: a four-point star in cream and gold that grows from a dot and goes, then rests.',
        'Place it by pixel (px) over the food at depth Front. Its three states are the one twinkle at three phases, so '
        'glints side by side twinkle in turn.',
        'States: twinkle-0, twinkle-1, twinkle-2 (1000 ms, looping).'], states=states, start='twinkle-0'))
