"""The weather strip in the Daily Brief's title band: eleven kinds of day, each
by day and by night, as small isometric scenes on the 2:1 grid, stacked from
shared layers on one anchor and one box.

The plan on the grid (the pixel-art-style skill's one rule):

- The box is 176×64, as wide as the spot's stage; (0, 0) is a little below its middle. It is only sky:
  there is no ground (the owner's call), so what falls falls out of the bottom of the strip.
- No backdrop: the strip is transparent and has no frame, so the weather sits in the page's title band
  (cream by day, dark brown at night) as part of the header. Its colors are picked to read on that band.
- The sun and the moon are rounded cubes (`box`, r = 4): a lit top, a mid left face and a dark right
  face. The sun's rays lie on the grid's lines (straight up, down and across, and the four 2:1 lines)
  and pulse long and short in turn.
- A cloud is a cumulus: rounded boxes heaped in tiers, side by side underneath and narrowing to a crown,
  each lit on top, pale blue down its left, lavender down its right, with no slab under it. It drifts
  along a column, two pixels across for one down, and back.
- Rain falls straight down out of the bottom of the strip. Lightning flashes from under its cloud down
  out of the strip, twice, then rests.
- Fog is long, thin rounded slabs (`box`, three pixels deep) hanging in the air, sliding along a row and
  back. At night stars twinkle.

Layers, bottom to top: stars (at night), sun or moon, rain, bolt, clouds, fog.
Nothing has a face. Only what moves in weather moves."""
from draw import *  # noqa: F401,F403
from draw import Pic, cat, despeck, halves, save_scene, sprite
from kit import box
import draw

# The box: the title band's strip, as wide as the spot's stage, all sky.
BOX = (-88, -44, 176, 64)
X0, Y0, W, H = BOX
SUN = (-54, -24)                     # the sun's (and the moon's) middle, a pixel corner
CAT = cat('Weather')


# ------------------------------------------------------------------ the kinds
KINDS = ['sun', 'fair', 'partly', 'cloudy', 'fog', 'drizzle', 'showers', 'rain', 'heavy-rain',
         'thundershowers', 'storm']

# kind -> (sky tone: how many stars show at night, body?, wet layer, bolt layer, cloud layout, fog?)
PLAN = {
    'sun': ('clear', True, None, None, None, False),
    'fair': ('clear', True, None, None, 'fair', False),
    'partly': ('clear', True, None, None, 'partly', False),
    'cloudy': ('grey', False, None, None, 'cloudy', False),
    'fog': ('mist', True, None, None, None, True),
    'drizzle': ('grey', False, 'drizzle', None, 'rain', False),
    'showers': ('clear', True, 'shower', None, 'shower', False),
    'rain': ('grey', False, 'rain', None, 'rain', False),
    'heavy-rain': ('dark', False, 'heavy', None, 'storm', False),
    'thundershowers': ('clear', True, 'shower', 'bolt-shower', 'thunder', False),
    'storm': ('dark', False, 'heavy', 'bolt', 'storm', False),
}

# Stars at night (fewer where clouds or fog hide them).
STARS = [(-80, -34), (-30, -38), (-8, -30), (14, -40), (34, -20), (52, -36), (76, -26), (-76, -10), (70, 4),
         (-26, 6), (84, -40), (-50, 12)]
STARS_BY_TONE = {'clear': 12, 'grey': 4, 'dark': 0, 'mist': 3}

# Cloud tones, for cumulus lit from the upper left: (top, left face, right face) for its rounded boxes.
# The shadows lean blue and lavender, as a cumulus's do.
TONES = {
    'white': ('cream', 'glass-1', 'plum-1'),
    'grey': ('stone-1', 'glass-1', 'plum-2'),
    'dark': ('stone-2', 'glass-3', 'plum-3'),
    'dusk': ('stone-1', 'glass-2', 'plum-2'),    # white, at night
    'slate': ('stone-2', 'glass-3', 'plum-3'),   # grey, at night
    'storm': ('stone-3', 'stone-4', 'plum-4'),      # dark, at night
}
NIGHT_TONE = {'white': 'dusk', 'grey': 'slate', 'dark': 'storm'}

# Cumulus shapes on the 2:1 grid: rounded boxes heaped in tiers, widest low and narrowing to a crown,
# with no slab under them. A box is (gx, gy, a, b, h, z): the middle of its footprint (gx, gy) on the
# cloud's underside (the plane through its anchor), its size in units and pixels, and z, the pixels it
# stands above that plane (on the boxes under it).
SHAPES = {
    'tower': {'boxes': [
        (-18, 1, 10, 8, 4, 0), (-8, 4, 12, 10, 5, 0), (5, 4, 12, 10, 6, 0), (17, 1, 10, 8, 5, 0),
        (-10, -4, 12, 10, 5, 0), (6, -5, 12, 10, 6, 0), (-1, 0, 12, 10, 6, 0),
        (-13, 2, 10, 8, 5, 5), (-3, 5, 10, 8, 6, 5), (9, 3, 10, 8, 5, 6), (-6, -2, 12, 10, 6, 6),
        (6, -2, 12, 10, 7, 6), (16, 0, 8, 6, 4, 5),
        (-8, 1, 10, 8, 5, 11), (2, 3, 10, 8, 6, 11), (4, -2, 12, 10, 6, 13), (11, 0, 8, 6, 4, 11),
        (-2, 0, 10, 8, 5, 17), (6, -1, 8, 6, 5, 19),
        (1, -1, 8, 6, 4, 23)]},
    'heap': {'boxes': [
        (-12, 1, 10, 8, 4, 0), (-3, 3, 10, 8, 5, 0), (8, 2, 10, 8, 5, 0), (14, 0, 8, 6, 4, 0),
        (-5, -3, 10, 8, 5, 0), (5, -3, 10, 8, 5, 0),
        (-8, 1, 8, 6, 4, 4), (1, 2, 10, 8, 5, 5), (9, 0, 8, 6, 4, 5), (2, -2, 10, 8, 5, 5),
        (-2, 0, 8, 6, 5, 9), (5, -1, 8, 6, 4, 10),
        (1, -1, 8, 6, 4, 14)]},
    'puff': {'boxes': [
        (-6, 1, 8, 6, 4, 0), (2, 2, 8, 6, 4, 0), (6, -1, 8, 6, 4, 0), (-1, -2, 8, 6, 4, 0),
        (-2, 0, 8, 6, 4, 4), (4, 0, 6, 6, 3, 4),
        (1, -1, 6, 4, 3, 8)]},
    'bank': {'boxes': [
        (-24, 1, 8, 6, 4, 0), (-15, 3, 10, 8, 5, 0), (-4, 3, 10, 8, 4, 0), (7, 3, 10, 8, 5, 0),
        (18, 2, 10, 8, 5, 0), (26, 0, 6, 6, 3, 0), (-12, -4, 10, 8, 4, 0), (2, -4, 10, 8, 5, 0),
        (14, -3, 10, 8, 4, 0),
        (-18, 1, 8, 6, 4, 4), (-8, 1, 10, 8, 5, 4), (3, 1, 10, 8, 5, 5), (13, 1, 8, 6, 4, 5),
        (-2, -2, 10, 8, 5, 5),
        (-6, 0, 8, 6, 4, 9), (5, -1, 8, 6, 5, 10)]},
}
# Cloud layouts: (shape, tone, x, y of the middle of its underside, drift phase).
LAYOUT = {
    'fair': [('puff', 'white', 34, -26, 0)],
    'partly': [('heap', 'white', -22, -16, 1), ('puff', 'white', 48, -28, 2)],
    'cloudy': [('tower', 'white', -48, -12, 0), ('heap', 'grey', 40, -22, 2), ('bank', 'grey', 2, -2, 1),
               ('heap', 'white', 60, 2, 2), ('puff', 'grey', -72, 6, 1)],
    'rain': [('bank', 'grey', -48, -20, 0), ('bank', 'grey', 44, -22, 1), ('heap', 'grey', 0, -10, 2)],
    'shower': [('puff', 'white', -12, -28, 2), ('tower', 'grey', 42, -14, 0)],
    'thunder': [('puff', 'white', -12, -28, 2), ('tower', 'dark', 42, -14, 0)],
    'storm': [('bank', 'dark', -48, -18, 0), ('bank', 'dark', 44, -20, 1), ('tower', 'dark', 0, -10, 2)],
}

DRIFT = 3                       # steps a cloud drifts along its column and back (2 across, 1 down each)
HOLD = 4                        # 200 ms frames on each step


def drift_states():
    seq = [i for i in list(range(DRIFT + 1)) + list(range(DRIFT - 1, 0, -1)) for _ in range(HOLD)]
    return {f'drift-{k}': {'frames': seq[k * len(seq) // 3:] + seq[:k * len(seq) // 3], 'ms': 200} for k in range(3)}


def cloud(shape, tone):
    """A cumulus: rounded boxes heaped in tiers, the bottom tier side by side on one plane (the cloud's
    flat underside), each lit on top, pale down its left and in shade down its right, drawn back to front
    and bottom to top. No slab under it."""
    t, left, right = TONES[tone]
    p = Pic()
    for gx, gy, ba, bb, bh, z in sorted(SHAPES[shape]['boxes'], key=lambda q: (q[5], q[1], q[0])):
        tx, ty = gx, gy - z - bh
        box(p, tx - (ba - bb) // 2, ty - (ba + bb) // 4, ba, bb, bh, t, left, right, r=max(2, min(ba, bb) // 2 - 1))
    return despeck(despeck(p))


# ------------------------------------------------------------------ the sun and the moon
def disc(cx, cy, r):
    return [(x, y) for x in range(cx - r - 1, cx + r + 1) for y in range(cy - r - 1, cy + r + 1)
            if (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 < r * r]


def cube(p, a, h, faces, r=4, b=None, at=(0, 0)):
    """A rounded box a×b units and h pixels tall, its middle at `at`: a lit top, a mid left face and a
    dark right face, its corners rounded to r units."""
    b = a if b is None else b
    bx = at[0] - (a - b) // 2
    by = at[1] - (a + b) // 4 - h // 2
    return box(p, bx, by, a, b, h, *faces, r=r)


R_SUN = 8
RAYS = [(3, 2), (4, 3), (3, 4), (2, 3)]          # (straight ray, 2:1 ray) lengths in pixels a frame, pulsing in turn
TURN = len(RAYS)


def sun(k):
    """The sun: a rounded cube, gold on top, orange down its left, deeper down its right, its rays on the
    grid's lines pulsing: straight up, down and across, and along the four 2:1 lines."""
    body = Pic()
    cube(body, 2 * R_SUN, 2 * R_SUN - 4, ('gold-1', 'clay-1', 'clay-2'))
    for q in ((-3, -9), (-2, -9), (-4, -8), (-3, -8), (-2, -8), (-1, -8), (-3, -7), (-2, -7)):
        if q in body:
            body[q] = 'cream'                         # a glint on the lit top
    xs = [x for x, _ in body]
    ys = [y for _, y in body]
    left, right, up, down = min(xs), max(xs), min(ys), max(ys)
    p = Pic()
    straight, slant = RAYS[k]
    for d in range(straight):
        for a in (-1, 0):
            p.put(a, up - 3 - d, 'gold-1'); p.put(a, down + 3 + d, 'gold-1')
            p.put(left - 3 - d, a + (up + down) // 2, 'gold-1'); p.put(right + 3 + d, a + (up + down) // 2, 'gold-1')
    for i in range(2 * slant):                      # 2:1 rays off the cube's four slanted edges
        x0, y0 = 13 + i, 10 + i // 2
        for sx in (1, -1):
            for sy in (1, -1):
                x = x0 if sx > 0 else -1 - x0
                y = (y0 if sy > 0 else -1 - y0) + (up + down) // 2
                p.put(x, y, 'gold-1')
    return despeck(p.over(body))


def moon():
    """The moon: a pale rounded cube, cream on top, pale down its left, in shade down its right."""
    p = Pic()
    cube(p, 14, 12, ('cream', 'path-1', 'path-3'), r=4)
    return despeck(p)


def star(r):
    p = Pic()
    if r < 0:
        return p
    p.put(0, 0, 'cream')
    if r >= 1:
        for x, y in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            p.put(x, y, 'cream' if r == 1 else 'glass-1')
    return p


TWINKLE = (0, 1, 2, 1, 0, 0, 0, 0, 0, 0)            # a dot, out to a star and back, then a rest


# ------------------------------------------------------------------ rain, lightning, fog
# name: (x range, top of the fall, drops, drop length, pixels a frame, frames in the loop, ms)
WET = {
    'drizzle': ((-82, 82), -14, 44, 2, 2, 18, 100),
    'shower': ((26, 60), -14, 12, 3, 4, 9, 100),
    'rain': ((-82, 82), -12, 48, 3, 4, 9, 100),
    'heavy': ((-84, 84), -10, 72, 4, 5, 6, 100),
}
RAIN = {('day', 'drizzle'): 'glass-4', ('day', 'shower'): 'glass-4', ('day', 'rain'): 'glass-4',
        ('day', 'heavy'): 'glass-3', ('night', 'drizzle'): 'glass-2', ('night', 'shower'): 'glass-2',
        ('night', 'rain'): 'glass-2', ('night', 'heavy'): 'glass-1'}
def drops(name):
    """Each drop's column and phase, spread over the rain's width."""
    (xa, xb), _, n, _, _, frames, _ = WET[name]
    out, seed = [], 7
    for i in range(n):
        seed = (seed * 1103515245 + 12345) % 2 ** 31
        out.append((xa + seed % (xb - xa), (i * 5) % frames))
    return out


def wet(name, time):
    """Rain falling straight down from under the clouds and out of the bottom of the strip."""
    _, ytop, _, ln, v, frames, _ = WET[name]
    c = RAIN[(time, name)]
    out = []
    for k in range(frames):
        p = Pic()
        for (x, ph) in drops(name):
            y = ytop + ((k + ph) % frames) * v
            for d in range(ln):
                if y + d < Y0 + H:
                    p.put(x, y + d, c)
        out.append(p)
    return out


def bolt_path(x, y0, y1):
    """A lightning bolt from (x, y0) down past y1, out of the strip: 1:1 strokes that zig and zag, two pixels wide."""
    pts, y, dx, i = [], y0, 1, 0
    legs = [4, 3, 5, 3, 4, 4, 3, 5, 4, 3]
    while y < y1:
        for _ in range(legs[i % len(legs)]):
            if y >= y1:
                break
            pts.append((x, y)); pts.append((x + 1, y))
            x += dx; y += 1
        dx = -dx
        i += 1
    return pts


FLASH = 30                      # the loop: 30 frames of 100 ms, the bolt in frames 0 and 2
BOLTS = {'bolt': (6, -14, 20), 'bolt-shower': (38, -16, 20)}


BOLT = {'day': ('gold-2', 'clay-2'), 'night': ('cream', 'gold-1')}   # (core, edge): on the cream band, on the dark one


def bolt(x, y0, y1, time):
    core, edge = BOLT[time]
    path = bolt_path(x, y0, y1)
    frames = []
    for k in range(FLASH):
        p = Pic()
        if k in (0, 2):
            for (a, b) in path:
                p.put(a, b, core)
            for (a, b) in path[1::2]:
                p.put(a + 1, b, edge)
        frames.append(p)
    return frames


FOG_SLIDE = 3                   # steps a fog slab slides along its row and back (2 across, 1 down each)
# Fog slabs: (x, y of the top's middle, a, b units).
FOG = [(-40, -18, 56, 8), (32, -16, 52, 8), (-10, -8, 64, 8), (56, 0, 40, 8), (-54, 0, 40, 8)]


def slab(a, b, lit, side):
    p = Pic()
    box(p, -(a - b) // 2, -(a + b) // 4, a, b, 3, lit, side, side, r=4)
    return p


def slide_states():
    seq = [i for i in list(range(FOG_SLIDE + 1)) + list(range(FOG_SLIDE - 1, 0, -1)) for _ in range(HOLD + 1)]
    return {f'slide-{k}': {'frames': seq[k * len(seq) // 3:] + seq[:k * len(seq) // 3], 'ms': 200} for k in range(3)}


# ------------------------------------------------------------------ building
def obj(name):
    """An object's name: the scenes (the page's layers) are wx-…, the objects in them weather-…."""
    return 'weather-' + name[3:] if name.startswith('wx-') else name


def save(name, o):
    draw.save(obj(name), o)


def in_box(p):
    return Pic({q: c for q, c in p.items() if X0 <= q[0] < X0 + W and Y0 <= q[1] < Y0 + H})


def save_halves(name, frames, notes, states=None, start=None):
    for side, fs in zip(('left', 'right'), halves([in_box(f) for f in frames])):
        save(f'{name}-{side}', sprite(fs, CAT, [notes[0].replace('{side}', side)] + notes[1:],
                                      states=states, start=start))


def cloud_name(shape, tone, time):
    return f'wx-cloud-{shape}-{tone if time == "day" else NIGHT_TONE[tone]}'


def build_objects():
    save('wx-sun', sprite([sun(k) for k in range(TURN)], CAT, [
        'The sun: a rounded cube on the 2:1 grid, gold on top, orange down its left face, deeper orange down its '
        'right, a cream glint on its top; its gold rays on the grid\'s lines (straight up, down and across, and the '
        'four 2:1 lines) pulse long and short in turn. No face.',
        f'Place it by pixel (px) at {list(SUN)} on the strip\'s anchor.',
        f'States: shine ({TURN} frames of 200 ms, looping).'],
        states={'shine': {'frames': list(range(TURN)), 'ms': 200}}, start='shine'))
    save('wx-moon', sprite(moon(), CAT, [
        'The moon: a pale rounded cube on the 2:1 grid, cream on top, pale down its left face, in shade down its '
        'right. No face; it stands still.',
        f'Place it by pixel (px) at {list(SUN)} on the strip\'s anchor, where the sun is by day.']))
    n = len(TWINKLE)
    for i in range(5):
        save(f'wx-star-{i}', sprite([star(TWINKLE[(j + i * 2) % n]) for j in range(n)], CAT, [
            'A star at night: a cream dot that twinkles out to a small cross and back, then rests.',
            f'Phase {i} of five, two frames apart, so stars side by side twinkle in turn.',
            'States: twinkle (10 frames of 200 ms, looping).'],
            states={'twinkle': {'frames': list(range(n)), 'ms': 200}}, start='twinkle'))
    made = set()
    for layout in LAYOUT.values():
        for shape, tone, *_ in layout:
            for time in ('day', 'night'):
                name = cloud_name(shape, tone, time)
                if name in made:
                    continue
                made.add(name)
                t = tone if time == 'day' else NIGHT_TONE[tone]
                base = cloud(shape, t)
                save(name, sprite([base.moved(2 * d, d) for d in range(DRIFT + 1)], CAT, [
                    f'A {t} cumulus ({shape}) on the 2:1 grid: rounded boxes heaped in tiers, side by side on one plane '
                    'underneath and narrowing to a crown, each lit on top, pale down its left, in shade down its '
                    'right. No slab under it, no face.',
                    'Place it by pixel (px) at the middle of its underside.',
                    f'States: drift-0, drift-1, drift-2 (it drifts {DRIFT} steps along its column, two pixels '
                    'across for one down, and back, 800 ms a step, at three phases).'],
                    states=drift_states(), start='drift-0'))
    for name in WET:
        ms = WET[name][6]
        wide = WET[name][0][1] - WET[name][0][0] > 120
        for time in ('day', 'night'):
            frames = wet(name, time)
            notes = [f'{name.capitalize()} by {time}: drops falling straight down from under the clouds and out of the '
                     'bottom of the strip' +
                     (': the {side} half.' if wide else '.'),
                     'Place it by pixel (px) at the strip\'s anchor, under the clouds.',
                     f'States: fall ({len(frames)} frames of {ms} ms, looping).']
            states = {'fall': {'frames': list(range(len(frames))), 'ms': ms}}
            if wide:
                save_halves(f'wx-{name}-{time}', frames, notes, states, 'fall')
            else:
                save(f'wx-{name}-{time}', sprite(frames, CAT, notes, states=states, start='fall'))
    for (name, (x, y0, y1)), time in ((b, t) for b in BOLTS.items() for t in ('day', 'night')):
        core, edge = BOLT[time]
        save(f'wx-{name}-{time}', sprite(bolt(x, y0, y1, time), CAT, [
            f'A lightning bolt by {time} from under the cloud down out of the strip, {core} with a {edge} edge: it '
            'flashes twice, then the sky is still for nearly three seconds.',
            'Place it by pixel (px) at the strip\'s anchor, under the clouds.',
            f'States: flash ({FLASH} frames of 100 ms, looping).'],
            states={'flash': {'frames': list(range(FLASH)), 'ms': 100}}, start='flash'))
    for time, (lit, side) in (('day', ('stone-1', 'stone-2')), ('night', ('stone-3', 'stone-4'))):
        for a, b in sorted({(f[2], f[3]) for f in FOG}):
            s = slab(a, b, lit, side)
            save(f'wx-fog-{a}x{b}-{time}', sprite([s.moved(-2 * d, d) for d in range(FOG_SLIDE + 1)], CAT, [
                f'A fog bank {a}×{b} units by {time}: a long, thin rounded box hanging in the air, its top lit.',
                'Place it by pixel (px) at the middle of its top.',
                f'States: slide-0, slide-1, slide-2 (it slides {FOG_SLIDE} steps along its row, two pixels across for '
                'one down, and back, 1 s a step, at three phases).'], states=slide_states(), start='slide-0'))


def item(name, at=(0, 0), state=None, order=0):
    i = {'object': obj(name), 'depth': 'back', 'order': order, 'at': {'px': list(at)}}
    if state:
        i['state'] = state
    return i


def halves_items(name, state=None):
    return [item(f'{name}-{s}', state=state) for s in ('left', 'right')]


def layer_items(layer, time):
    kind = layer[0]
    if kind == 'stars':
        return [item(f'wx-star-{i % 5}', at, 'twinkle', i)
                for i, at in sorted(enumerate(STARS[:STARS_BY_TONE[layer[1]]]), key=lambda e: (e[1][1], e[1][0]))]
    if kind == 'body':
        return [item('wx-sun', SUN, 'shine') if time == 'day' else item('wx-moon', SUN)]
    if kind == 'wet':
        name = layer[1]
        if WET[name][0][1] - WET[name][0][0] > 120:
            return halves_items(f'wx-{name}-{time}', 'fall')
        return [item(f'wx-{name}-{time}', state='fall')]
    if kind == 'bolt':
        return [item(f'wx-{layer[1]}-{time}', state='flash')]
    if kind == 'clouds':
        return [item(cloud_name(shape, tone, time), (x, y), f'drift-{ph}', i)
                for i, (shape, tone, x, y, ph) in enumerate(sorted(LAYOUT[layer[1]], key=lambda c: (c[3], c[2])))]
    if kind == 'fog':
        return [item(f'wx-fog-{a}x{b}-{time}', (x, y), f'slide-{i % 3}', i)
                for i, (x, y, a, b) in enumerate(sorted(FOG, key=lambda f: (f[1], f[0])))]
    raise ValueError(layer)


def layers(kind, time):
    """The layers of a kind's strip, bottom to top."""
    sky, body, wet_, bolt_, clouds, fog = PLAN[kind]
    out = []
    if time == 'night' and STARS_BY_TONE[sky]:
        out.append(('stars', sky))
    if body:
        out.append(('body',))
    if wet_:
        out.append(('wet', wet_))
    if bolt_:
        out.append(('bolt', bolt_))
    if clouds:
        out.append(('clouds', clouds))
    if fog:
        out.append(('fog',))
    return out


def layer_name(layer, time):
    k = layer[0]
    if k == 'stars':
        return f'wx-stars-{layer[1]}'
    if k == 'body':
        return 'wx-sun' if time == 'day' else 'wx-moon'
    if k == 'wet':
        return f'wx-{layer[1]}-{time}'
    if k == 'bolt':
        return f'wx-{layer[1]}-{time}'
    if k == 'clouds':
        return f'wx-clouds-{layer[1]}-{time}'
    return f'wx-fog-{time}'


def scene(notes, items, output=None):
    s = {'notes': notes}
    if output:
        s['output'] = output
    s['viewBox'] = list(BOX)
    s['items'] = items
    return s


def build_scenes():
    """One scene per layer, the page's files (`wx-<layer>.svg`). Returns {kind: {time: [layer names, bottom to top]}}."""
    made, stacks = set(), {}
    for kind in KINDS:
        stacks[kind] = {}
        for time in ('day', 'night'):
            names = []
            for layer in layers(kind, time):
                name = layer_name(layer, time)
                names.append(name)
                if name not in made:
                    made.add(name)
                    save_scene(name, scene([f'A layer of the weather strip by {time}: {" ".join(layer)}. The page '
                                            'stacks the layers a kind needs, bottom to top, on one anchor.'],
                                           layer_items(layer, time), name + '.svg'))
            stacks[kind][time] = names
    return stacks


def build_weather():
    build_objects()
    return build_scenes()
