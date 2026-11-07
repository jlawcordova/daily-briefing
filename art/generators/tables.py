"""The tables a spot of the day's food is served on, in place of a podium:
a samgyupsal grill table, a café's marble bistro table, a fine-dining table
in a white cloth and a cozy wooden table. Each is drawn around (0, 0), the
middle of its top where the food stands, and its legs run out of the
stage's box at the bottom. What's on a table besides the food sits at its
sides, clear of every food (they reach x = ±34), so the food's layer can go
over any table. A table is wider than a sprite, so it comes in halves."""
from draw import *
from kit import box, puck, top
from stage import BOX

FRAMES = 6    # a table's loop (the grill's smoke and coals, the candle), 200 ms a frame


def at(bx, by, u, v):
    """The pixel of the point (u, v) units on a top whose back corner is (bx, by)."""
    return bx + u - v, by + (u + v) // 2


def legs(p, bx, by, a, b, h, faces, size=6, inset=4):
    """Four square legs under a top a×b with its back corner at (bx, by) and
    sides h deep, from under the top down out of the box."""
    for u, v in ((inset, inset), (a - inset - size, inset), (inset, b - inset - size), (a - inset - size, b - inset - size)):
        x, y = at(bx, by, u, v)
        box(p, x, y + h, size, size, 60 - y, *faces)


# ------------------------------------------------------------------ the cozy wooden table
def wood(k=0):
    """A farmhouse table of warm planks, rounded at its corners, on four
    chunky legs, a red gingham placemat under the food."""
    p = Pic()
    a, b, h = 96, 64, 6
    bx, by = -16, -38                       # its middle at (0, 2)
    legs(p, bx, by, a, b, h, ('wood-2', 'wood-3', 'wood-4'))
    box(p, bx, by, a, b, h, lambda u, v: 'wood-2' if int(v) % 16 == 0 else 'wood-1', 'wood-2', 'wood-3', r=4)

    def check(u, v):
        n = int(u // 5) % 2 + int(v // 5) % 2
        return ('cream', 'roof-1', 'roof-2')[n]
    top(p, -6, -16, 42, 30, check, r=3)      # the placemat, its middle at (0, 2)
    return p


# ------------------------------------------------------------------ the samgyupsal grill table
def coal(k):
    def c(x, y):
        h = (int(x) * 7 + int(y * 2) * 13 + k * 5) % 11
        return 'roof-1' if h == 0 else 'clay-1' if h == 1 else 'brick-3'
    return c


def grill(k=0):
    """A Korean barbecue table: a square top of dark wood with a round
    charcoal grill set in its left side, strips of pork belly sizzling on the
    grate and smoke rising, and three dishes of banchan on its right
    (kimchi, spinach and bean sprouts)."""
    p = Pic()
    a = b = 80
    h = 5
    bx, by = 0, -38                         # its middle at (0, 2)
    legs(p, bx, by, a, b, h, ('wood-4', 'wood-4', 'soil-4'))
    box(p, bx, by, a, b, h, 'wood-3', 'wood-4', 'soil-4', r=4)
    gx, gy = -50, 2
    ellipse(p, gx, gy, 28, 'stone-2')                      # the grill's steel ring
    ellipse(p, gx, gy, 24, 'ink')                          # its well
    ellipse(p, gx, gy + 1, 20, coal(k))                    # the coals, glowing
    for (x, y) in ellipse(Pic(), gx, gy, 22, None):        # the grate, bars on 2:1 lines
        if (x + 2 * y) % 6 == 0:
            p.put(x, y, 'stone-1')
    for i in range(3):                                     # the pork belly, fat and meat in stripes
        sx, sy = gx + 2 - 6 * i, gy - 9 + 3 * i
        top(p, sx, sy, 14, 4, lambda u, v: 'cream' if v < 1.4 else 'brick-1' if v < 2.8 else 'clay-2')
    steam(p, gx, gy - 6, k, n=2, tall=22, spread=10, c='stone-1')
    for cx, cy, fill in ((44, -4, ('roof-1', 'roof-2')), (58, 2, ('grass-3', 'grass-3')), (44, 10, ('gold-1', 'cream'))):
        puck(p, cx, cy, 14, 2, 'cream', ['stone-1', 'stone-2'])
        ellipse(p, cx, cy, 10, lambda x, y, f=fill: f[(int(x * 2) + int(y * 3)) % 2])
    return p


# ------------------------------------------------------------------ the café's bistro table
def cafe(k=0):
    """A café's round bistro table: a white marble top with grey veins on one
    iron pedestal and a round foot, a bud vase with a flower to one side."""
    p = Pic()
    puck(p, 0, 50, 34, 2, 'stone-4', ['stone-4', 'ink'])  # the foot
    for y in range(6, 50):                                 # the pedestal
        for x in range(-3, 3):
            p.put(x, y, 'stone-4' if x < 0 else 'ink')
    puck(p, 0, 2, 100, 3, 'stone-1', ['stone-1', 'stone-2', 'stone-2', 'stone-3'])
    for x0, y0, n in ((-34, 6, 14), (8, -12, 12), (20, 14, 10)):   # veins in the marble, 2:1
        for i in range(n):
            p.put(x0 + i, y0 + i // 2, 'stone-2')
    vx, vy = -42, -2                                       # the bud vase
    puck(p, vx, vy, 8, 7, 'clay-2', ['clay-2', 'clay-3'])
    ellipse(p, vx, vy, 4, 'clay-3')
    for y in range(vy - 12, vy):
        p.put(vx, y, 'grass-3')
    p.put(vx + 1, vy - 7, 'grass-3')
    p.put(vx + 2, vy - 8, 'grass-3')
    for x, y in ((-1, -14), (0, -14), (-2, -13), (1, -13), (-1, -12), (0, -12), (-1, -15), (0, -15)):
        p.put(vx + x, vy + y, 'roof-1')
    p.put(vx - 1, vy - 13, 'gold-1')
    p.put(vx, vy - 13, 'gold-1')
    return p


# ------------------------------------------------------------------ the fine-dining table
def candle_flame(p, x, y, k):
    """A candle's flame over (x, y), the wick's top: it leans and stretches as k goes on."""
    tall = (4, 5, 4, 3, 4, 5)[k]
    lean = (0, 0, 1, 0, -1, 0)[k]
    for d in range(tall):
        xx = x + (lean if d >= tall - 2 else 0)
        p.put(xx - 1, y - d, 'clay-1' if d < 2 else 'gold-1')
        if d < tall - 1:
            p.put(xx, y - d, 'gold-1' if d < 2 else 'cream')


def fine(k=0):
    """A fine-dining table: round, under a white cloth that falls in folds to
    the floor, a tall candle in a silver holder at its left and a glass of red
    wine at its right. The candle's flame flickers."""
    p = Pic()
    side = ('cream', 'path-1', 'path-2', 'path-3')
    for d in range(56, 0, -1):                             # the cloth, flaring a little as it falls
        ww = even(116 + 8 * d / 56)

        def c(x, y, ww=ww):
            f = (x + ww / 2) / ww
            i = min(3, int(f * 4))
            if int(x + ww / 2) % 12 == 11 and 0 < f < 0.95:
                i = min(3, i + 1)                          # a fold
            return side[i]
        ellipse(p, 0, 2 + d, ww, c)
    ellipse(p, 0, 2, 116, 'cream')
    cx, cy = -44, -4                                       # the candle
    puck(p, cx, cy, 10, 2, 'stone-1', ['stone-1', 'stone-2', 'stone-3'])
    for y in range(cy - 16, cy):
        for x in range(cx - 2, cx + 2):
            p.put(x, y, 'cream' if x < cx else 'path-1')
    p.put(cx, cy - 17, 'path-3')                          # the wick
    candle_flame(p, cx, cy - 18, k)
    wx, wy = 44, -2                                        # the wine glass
    ellipse(p, wx, wy, 8, 'stone-1')
    for y in range(wy - 7, wy):
        p.put(wx - 1, y, 'stone-1')
    for i, w in enumerate((4, 6, 8, 8, 8, 8, 6)):          # its bowl, bottom up
        y = wy - 8 - i
        for x in range(wx - w // 2, wx + w // 2):
            wine = i < 3 or (i == 3 and abs(x - wx + 0.5) < 3)
            if wine:
                c = 'roof-1' if i == 3 else 'roof-2'
            else:
                c = 'glass-1' if x < wx else 'glass-2'
            p.put(x, y, c)
    p.put(wx - 3, wy - 13, 'cream')                        # a glint on the glass
    p.put(wx - 3, wy - 12, 'cream')
    return p


def crop(p):
    """What of a table the brief's box shows: its legs and cloth cut off at the bottom."""
    x0, y0, w, h = BOX
    return Pic({(x, y): c for (x, y), c in p.items() if x0 <= x < x0 + w and y0 <= y < y0 + h})


# name: (draw, moves, notes)
TABLES = {
    'grill': (grill, 'sizzle', 'A samgyupsal grill table: a square top of dark wood on four legs, a round charcoal grill '
              'set in its left side with strips of pork belly on the grate, and three dishes of banchan on its right.'),
    'cafe': (cafe, None, 'A café\'s round bistro table: a white marble top with grey veins on an iron pedestal and a '
             'round foot, a bud vase with a red flower at its left.'),
    'fine': (fine, 'flicker', 'A fine-dining table: round, in a white cloth that falls in folds to the floor, a tall '
             'candle in a silver holder at its left and a glass of red wine at its right.'),
    'wood': (wood, None, 'A cozy farmhouse table of warm wooden planks, rounded at the corners, on four chunky legs, '
             'a red gingham placemat in its middle.'),
}


def build_tables():
    for name, (fn, moves, what) in TABLES.items():
        frames = [crop(fn(k)) for k in range(FRAMES)] if moves else [crop(fn())]
        for side, half in zip(('left', 'right'), halves(frames)):
            notes = [f'The {side} half of {what[0].lower() + what[1:]}',
                     f'Place both halves by pixel (px) on one point, the middle of its top: the food stands there, '
                     f'placed after it. Its legs run out of the brief\'s box at the bottom.']
            if moves:
                word = {'sizzle': 'the smoke rises and the coals glow', 'flicker': 'the candle flickers'}[moves]
                notes.append(f'States: {moves} ({FRAMES} frames, 200 ms each, looping: {word}), idle (still).')
                o = looped(half, cat('Table'), notes, 200, name=moves, extra={'idle': {'frames': [0], 'ms': 1000}})
            else:
                o = sprite(half[0], cat('Table'), notes)
            save(f'table-{name}-{side}', o)
    return list(TABLES)
