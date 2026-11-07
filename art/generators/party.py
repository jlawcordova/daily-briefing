"""The Birthdays section's party, and the small icons on its cards: festive,
bright and busy, as isometric pieces on the 2:1 grid, in layers on one anchor
and one box that the page stacks over its gold band.

The plan on the grid (the pixel-art-style skill's one rule):

- The box is 176x100, as wide as the spot's stage; (0, 0) is its middle. No
  backdrop: the layers are transparent over the section's gold band.
- The table is a rounded box 72x36 units and 9 pixels deep, its top's middle
  at TABLE: teal, lit on top, with cream polka dots, on four square legs that
  run out of the box at the bottom. Pennants hang along its two front faces,
  their colors chasing round it (the bunting layer).
- On it, by (u, v) on its top: a two-tier cake in the middle (rounded boxes
  22 and 14 units: a strawberry tier and an ube tier, each with cream on top
  and a cream band round its sides, sprinkles on top, on a cream plate) with
  four striped candles whose flames flicker; three gifts as rounded cubes
  (plum with a gold ribbon, grass with a red ribbon, clay with a cream
  ribbon), each ribbon crossing its top and running down its faces, a bow on
  top, the gifts hopping in turn.
- Over it, four balloons of rounded prisms (a tapered bottom, a body 10x10
  units, a small cap; red, plum, grass, blue), bobbing on cream strings: two tied to the back gifts,
  two loose at the sides.
- Sparkles twinkle round the cake and balloons; confetti, tiny bits in seven
  colors, tumbles down over everything (flipping between 2x1 and 1x2 as it
  falls and sways).
- Light from the upper left: tops lightest, left faces mid, right faces
  darkest. No outlines and no faces: the cake is food.

Layers, bottom to top: table, bunting, party (gifts and cake in depth order),
balloons, sparkles, confetti.

The card icons are 24x24, shown at 2x: a little cake with one flickering
candle, a gift that hops and a balloon that bobs."""
import math
from draw import *  # noqa: F401,F403
from draw import Pic, cat, despeck, halves, save_scene, sprite
from kit import box, ellipse, puck
import draw

BOX = (-88, -54, 176, 100)
X0, Y0, W, H = BOX
ICON = (-12, -18, 24, 24)
CAT = cat('Party')

# The table: its top a x b units, its back corner at (BX, BY), h pixels deep.
TA, TB, TH = 72, 36, 9
BX, BY = -(TA - TB) // 2, 8 - (TA + TB) // 4


def at(u, v):
    """The pixel of the point (u, v) units on the table's top."""
    return BX + u - v, BY + (u + v) // 2


def rbox(p, cx, cy, a, b, h, faces, r=3):
    """A rounded box whose footprint's middle is the pixel corner (cx, cy), standing h pixels tall."""
    bx = cx - (a - b) // 2
    by = cy - h - (a + b) // 4
    return box(p, bx, by, a, b, h, *faces, r=r)


def in_box(p, bx=BOX):
    x0, y0, w, h = bx
    return Pic({q: c for q, c in p.items() if x0 <= q[0] < x0 + w and y0 <= q[1] < y0 + h})


def save(name, o):
    draw.save(name, o)


def one_state(frames, notes, name, ms, seq=None):
    seq = seq if seq is not None else list(range(len(frames)))
    return sprite(frames, CAT, notes, states={name: {'frames': seq, 'ms': ms}}, start=name)


# ------------------------------------------------------------------ the table and its bunting
def table():
    p = Pic()
    for u, v in ((3, 3), (TA - 9, 3), (3, TB - 9), (TA - 9, TB - 9)):     # legs, out of the box at the bottom
        x, y = at(u, v)
        box(p, x, y + TH, 6, 6, Y0 + H - y, 'teal-3', 'teal-3', 'teal-4')

    def dots(u, v):
        return 'cream' if int(u) % 10 in (4, 5) and int(v) % 10 == 5 else 'teal-1'
    box(p, BX, BY, TA, TB, TH, dots, 'teal-2', 'teal-3', r=6)
    return in_box(p)


PENNANTS = ('roof-1', 'gold-1', 'plum-1', 'grass-1', 'cream', 'clay-1')


def bunting(k):
    """The pennants on the table's front faces, k steps round in their chase of colors."""
    p = Pic()
    shadow = Pic()
    box(shadow, BX, BY, TA, TB, TH, 't', lambda s, t: ('l', s, t), lambda s, t: ('r', s, t), r=6)
    n = len(PENNANTS)
    for (x, y), c in shadow.items():
        if not isinstance(c, tuple):
            continue
        face, s, t = c
        q = s % 10                                  # a pennant every 10 pixels, 8 wide and 4 deep
        width = TA if face == 'l' else TB
        if s < 10 or s >= width - 8:                # none round the rounded corners
            continue
        if 1 <= q <= 8 and t <= 3 and abs(q - 4.5) <= 4 - t:
            i = s // 10 + (0 if face == 'l' else 20)
            p.put(x, y, PENNANTS[(i + k) % n])
    return p


# ------------------------------------------------------------------ the cake
CAKE = at(36, 18)


def drip(side, cream='cream'):
    """A tier's side: a band of cream along its top, the side's color under it."""
    return lambda s, t: cream if t < 2 else side


CANDLES = [(-4, -1, 'teal-1'), (3, -2, 'roof-1'), (-1, 2, 'gold-1'), (5, 2, 'plum-1')]


def flame(p, x, y, k):
    """A flame two pixels wide on a candle whose top is the row y, its tip flickering through 3 frames."""
    for dx in (0, 1):
        p.put(x + dx, y - 1, 'clay-1')
        p.put(x + dx, y - 2, 'gold-1')
    tip = [(x, y - 3), (x + 1, y - 3), (x + 1, y - 4)][k % 3]
    p.put(*tip, 'cream')
    if k % 3 == 2:
        p.put(x + 1, y - 3, 'gold-1')


def cake(k):
    p = Pic()
    cx, cy = CAKE
    puck(p, cx, cy + 1, 50, 1, 'cream', ['path-1', 'path-2'])     # the plate
    rbox(p, cx, cy, 22, 22, 10, ('cream', drip('roof-1'), drip('roof-2', 'path-1')), r=5)
    rbox(p, cx, cy - 10, 14, 14, 8, ('cream', drip('plum-1'), drip('plum-2', 'path-1')), r=4)
    ty = cy - 18                                                  # the upper tier's top, at its middle
    for i, (dx, dy) in enumerate(((-6, 0), (6, 0), (0, -3), (0, 3), (-3, 2), (3, -2))):
        p.put(cx + dx, ty + dy, PENNANTS[i % 4] if PENNANTS[i % 4] != 'cream' else 'teal-1')
    for i, (dx, dy, c) in enumerate(CANDLES):
        x, y = cx + dx, ty + dy
        for t in range(5):
            p.put(x, y - t, c if t % 2 == 0 else 'cream')
            p.put(x + 1, y - t, c if t % 2 == 0 else 'cream')
        flame(p, x, y - 5, k + i)
    return p


# ------------------------------------------------------------------ the gifts
def ribboned(a, b, h, box_c, ribbon_c):
    """The faces of a gift a x b x h: box_c and ribbon_c are (top, left, right) each."""
    def topf(u, v):
        return ribbon_c[0] if abs(u - a / 2) < 1.5 or abs(v - b / 2) < 1.5 else box_c[0]

    def left(s, t):
        return ribbon_c[1] if abs(s + 0.5 - a / 2) < 1.5 else box_c[1]

    def right(s, t):
        return ribbon_c[2] if abs(s + 0.5 - b / 2) < 1.5 else box_c[2]
    return topf, left, right


def gift(a, h, box_c, ribbon_c):
    """A gift on (0, 0): a rounded cube with its ribbon, a bow on top."""
    p = Pic()
    rbox(p, 0, 0, a, a, h, ribboned(a, a, h, box_c, ribbon_c), r=2)
    ty = -h
    ellipse(p, -3, ty - 1, 6, ribbon_c[0])
    ellipse(p, 3, ty - 1, 6, ribbon_c[0])
    ellipse(p, 0, ty, 2, ribbon_c[2])
    return despeck(p)


GIFTS = {
    'plum': ((14, 24), 14, 12, ('plum-1', 'plum-2', 'plum-3'), ('gold-1', 'gold-2', 'gold-3'), 0),
    'grass': ((58, 10), 12, 10, ('grass-1', 'grass-2', 'grass-3'), ('roof-1', 'roof-2', 'roof-3'), 5),
    'clay': ((62, 26), 10, 8, ('clay-1', 'clay-2', 'clay-3'), ('cream', 'path-1', 'path-2'), 10),
}
HOP = [0, -1, -2, -2, -1]                      # a gift's hop, 100 ms a frame, then it rests


def gift_frames(name):
    _, a, h, bc, rc, _ = GIFTS[name]
    base = gift(a, h, bc, rc)
    return [base.moved(0, d) for d in sorted(set(HOP), reverse=True)]


def gift_seq(phase):
    offsets = sorted(set(HOP), reverse=True)            # frame i is offset offsets[i]
    seq = [offsets.index(d) for d in HOP] + [0] * 10
    return seq[-phase:] + seq[:-phase] if phase else seq


# ------------------------------------------------------------------ balloons
BALLOONS = [
    # (name, faces, x of its middle, y of its footprint's middle, where its string ends, phase)
    ('red', ('roof-1', 'roof-2', 'roof-3'), -30, -34, (-30, -12), 0),
    ('plum', ('plum-1', 'plum-2', 'plum-3'), -62, -30, (-62, -8), 2),
    ('green', ('grass-1', 'grass-2', 'grass-3'), 32, -36, (32, -2), 4),
    ('blue', ('glass-1', 'glass-2', 'glass-3'), 62, -28, (62, -6), 1),
]
BOB = [0, 0, -1, -1, -2, -2, -1, -1]              # 200 ms a frame


def balloon(faces, d, end_dy):
    """A balloon d pixels up from its rest, its string from its knot down to end_dy below its footprint."""
    p = Pic()
    rbox(p, 0, d, 6, 6, 3, faces, r=2)             # the tapered bottom
    rbox(p, 0, d - 3, 10, 10, 9, faces, r=4)       # the body, widest
    rbox(p, 0, d - 12, 6, 6, 2, (faces[0], faces[0], faces[1]), r=2)   # the cap, in the light
    ky = d + 3                                     # the knot, under the bottom's front corner
    p.put(-1, ky, faces[2]); p.put(0, ky, faces[2]); p.put(-1, ky + 1, faces[2]); p.put(0, ky + 1, faces[2])
    for y in range(ky + 2, end_dy + 1):
        p.put(-1 if (y // 4) % 2 else 0, y, 'cream')
    return p


# ------------------------------------------------------------------ sparkles and confetti
def star(r):
    p = Pic()
    if r < 0:
        return p
    for a in (-1, 0):
        for b in (-1, 0):
            p.put(a, b, 'cream')
    for d in range(1, r + 1):
        c = 'glass-1' if d == r else 'cream'
        for a in (-1, 0):
            for x, y in ((-1 - d, a), (d, a), (a, -1 - d), (a, d)):
                p.put(x, y, c)
    return p


TWINKLE = (0, 1, 2, 1, 0, -1, -1, -1)
SPARKLES = [(-16, -40), (16, -46), (-46, -20), (48, -14), (0, -50), (-74, -48), (78, -46), (-8, 26)]

CONFETTI = ('roof-1', 'teal-1', 'plum-1', 'grass-1', 'cream', 'glass-1', 'clay-1')
FALL, FRAMES = 4, 25                            # pixels a frame, frames in the loop (200 ms each): 5 s


def confetti():
    bits, seed = [], 11
    for i in range(64):
        seed = (seed * 1103515245 + 12345) % 2 ** 31
        x = X0 + 2 + seed % (W - 4)
        seed = (seed * 1103515245 + 12345) % 2 ** 31
        bits.append((x, seed % H, CONFETTI[i % len(CONFETTI)], i % 4))
    frames = []
    for k in range(FRAMES):
        p = Pic()
        for x, y0, c, ph in bits:
            y = Y0 + (y0 + FALL * k) % H
            xx = x + round(1.5 * math.sin((k + ph * 3) / 2))
            if (k + ph) % 4 < 2:
                p.put(xx, y, c); p.put(xx + 1, y, c)
            else:
                p.put(xx, y, c); p.put(xx, y + 1, c)
        frames.append(in_box(p))
    return frames


# ------------------------------------------------------------------ icons
def icon_cake(k):
    p = Pic()
    ellipse(p, 0, 1, 22, 'cream')
    rbox(p, 0, 0, 10, 10, 6, ('cream', drip('roof-1'), drip('roof-2', 'path-1')), r=3)
    for t in range(4):
        p.put(-1, -5 - t, 'teal-1' if t % 2 == 0 else 'cream')
        p.put(0, -5 - t, 'teal-1' if t % 2 == 0 else 'cream')
    flame(p, -1, -9, k)
    return p


def icon_gift():
    return gift(8, 7, ('plum-1', 'plum-2', 'plum-3'), ('gold-1', 'gold-2', 'gold-3'))


def icon_balloon(d):
    """A small balloon for a card: a rounded prism 8x8 units and 9 pixels tall, on a cream string."""
    faces = ('roof-1', 'roof-2', 'roof-3')
    p = Pic()
    rbox(p, 0, d - 1, 4, 4, 2, faces, r=1)
    rbox(p, 0, d - 3, 8, 8, 7, faces, r=3)
    rbox(p, 0, d - 10, 4, 4, 1, (faces[0], faces[0], faces[1]), r=1)
    ky = d + 1
    for q in ((-1, ky), (0, ky)):
        p.put(*q, faces[2])
    for y in range(ky + 1, 6):
        p.put(-1 if (y // 3) % 2 else 0, y, 'cream')
    return p


# ------------------------------------------------------------------ building
def scene(notes, items, output, view=BOX):
    return {'notes': notes, 'output': output, 'viewBox': list(view), 'items': items}


def item(name, at=(0, 0), state=None, order=0):
    i = {'object': name, 'depth': 'back', 'order': order, 'at': {'px': list(at)}}
    if state:
        i['state'] = state
    return i


def halves_items(name, state=None):
    return [item(f'{name}-{s}', state=state) for s in ('left', 'right')]


def save_halves(name, frames, notes, state=None, ms=None):
    for side, fs in zip(('left', 'right'), halves(frames)):
        n = [notes[0].replace('{side}', side)] + notes[1:]
        if state:
            save(f'{name}-{side}', one_state(fs, n, state, ms))
        else:
            save(f'{name}-{side}', sprite(fs, CAT, n))


def build_party():
    """The party's objects and its layer scenes (bday-*.svg) and the icons' (bday-icon-*.svg)."""
    save_halves('party-table', [table()], [
        'The {side} half of the party table: a teal rounded box 72x36 units, 9 pixels deep, cream polka dots '
        'on its lit top, on four square legs that run out of the box at the bottom.',
        'Place it by pixel (px) at the party\'s anchor.'])
    n = len(PENNANTS)
    save_halves('party-bunting', [bunting(k) for k in range(n)], [
        'The {side} half of the pennants along the party table\'s two front faces, their six colors chasing '
        'round it a pennant a frame.',
        'Place it by pixel (px) at the party\'s anchor, over the table.',
        f'States: chase ({n} frames of 200 ms, looping).'], 'chase', 200)
    save('party-cake', one_state([cake(k) for k in range(3)], [
        'The birthday cake in the middle of the party table: a strawberry tier and an ube tier, rounded boxes '
        'lit on top, cream on top and in a band round their sides, sprinkles, on a cream plate; four striped '
        'candles whose flames flicker. No face: food has none.',
        'Place it by pixel (px) at the party\'s anchor.',
        'States: flicker (3 frames of 100 ms, looping).'], 'flicker', 100))
    for name, ((u, v), a, h, bc, rc, phase) in GIFTS.items():
        save(f'party-gift-{name}', one_state(gift_frames(name), [
            f'A {name} gift on the party table: a rounded cube {a} units, its ribbon ({rc[0]}) crossing its top '
            'and running down its faces, a bow on top. It hops now and then.',
            'Place it by pixel (px) at the middle of its footprint on the table.',
            f'States: hop ({len(HOP) + 10} frames of 100 ms, looping: a hop, then a rest).'], 'hop', 100,
            gift_seq(phase)))
    for name, faces, x, y, end, phase in BALLOONS:
        offs = sorted(set(BOB), reverse=True)
        frames = [balloon(faces, d, end[1] - y) for d in offs]
        seq = [offs.index(d) for d in BOB]
        seq = seq[phase:] + seq[:phase]
        save(f'party-balloon-{name}', one_state(frames, [
            f'A {name} balloon of rounded prisms (a tapered bottom, a body 10x10 units, a small cap), lit on top, '
            'bobbing on a cream string.',
            'Place it by pixel (px) at the middle of its footprint.',
            f'States: bob ({len(BOB)} frames of 200 ms, looping).'], 'bob', 200, seq))
    m = len(TWINKLE)
    for i in range(4):
        save(f'party-sparkle-{i}', one_state([star(TWINKLE[(j + i * 2) % m]) for j in range(m)], [
            'A sparkle at the party: a cream point that twinkles out to a star and back, then rests.',
            f'Phase {i} of four, two frames apart.', 'States: twinkle (8 frames of 100 ms, looping).'],
            'twinkle', 100))
    save_halves('party-confetti', confetti(), [
        'The {side} half of the confetti tumbling down over the party: bits in seven colors, swaying, flipping '
        'between 2x1 and 1x2 as they fall.',
        'Place it by pixel (px) at the party\'s anchor, over everything.',
        f'States: fall ({FRAMES} frames of 200 ms, looping).'], 'fall', 200)
    save('party-icon-cake', one_state([icon_cake(k) for k in range(3)], [
        'A card icon: a little strawberry cake, cream on top, with one striped candle whose flame flickers.',
        'States: flicker (3 frames of 100 ms, looping).'], 'flicker', 100))
    g = icon_gift()
    save('party-icon-gift', one_state([g, g.moved(0, -1), g.moved(0, -2)], [
        'A card icon: a plum gift with a gold ribbon and bow that hops.',
        'States: hop (100 ms frames, looping: a hop, then a rest).'], 'hop', 100,
        [0, 1, 2, 2, 1] + [0] * 7))
    offs = sorted(set(BOB), reverse=True)
    save('party-icon-balloon', one_state([icon_balloon(d) for d in offs], [
        'A card icon: a red balloon on a cream string, bobbing.',
        f'States: bob ({len(BOB)} frames of 200 ms, looping).'], 'bob', 200, [offs.index(d) for d in BOB]))

    # The layers.
    layer = lambda name, notes, items: save_scene(name, scene(notes, items, name + '.svg'))
    layer('bday-table', ['The party\'s table, the bottom layer, transparent over the section\'s gold band.'],
          halves_items('party-table'))
    layer('bday-bunting', ['The pennants chasing round the table\'s front faces.'], halves_items('party-bunting', 'chase'))
    things = [(at(*GIFTS['plum'][0]), 'party-gift-plum', 'hop'), (CAKE, 'party-cake', 'flicker'),
              (at(*GIFTS['grass'][0]), 'party-gift-grass', 'hop'), (at(*GIFTS['clay'][0]), 'party-gift-clay', 'hop')]
    items = []
    for i, (pos, name, state) in enumerate(sorted(things, key=lambda t: (t[0][1], t[0][0]))):
        items.append(item(name, (0, 0) if name == 'party-cake' else pos, state, i))
    layer('bday-party', ['The cake and the gifts on the table, in depth order.'], items)
    layer('bday-balloons', ['The balloons bobbing over the table.'],
          [item(f'party-balloon-{n}', (x, y), 'bob', i)
           for i, (n, _, x, y, _, _) in enumerate(sorted(BALLOONS, key=lambda b: (b[3], b[2])))])
    layer('bday-sparkles', ['Sparkles twinkling round the cake and the balloons.'],
          [item(f'party-sparkle-{i % 4}', at, 'twinkle', i)
           for i, at in sorted(enumerate(SPARKLES), key=lambda e: (e[1][1], e[1][0]))])
    layer('bday-confetti', ['Confetti tumbling down over everything, the top layer.'],
          halves_items('party-confetti', 'fall'))
    for n, st in (('cake', 'flicker'), ('gift', 'hop'), ('balloon', 'bob')):
        save_scene(f'bday-icon-{n}', scene([f'The {n} icon on a birthday card.'], [item(f'party-icon-{n}', state=st)],
                                           f'bday-icon-{n}.svg', ICON))
    return ['bday-table', 'bday-bunting', 'bday-party', 'bday-balloons', 'bday-sparkles', 'bday-confetti']
