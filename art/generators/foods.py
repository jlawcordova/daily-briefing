"""The spot of the day's foods: things to eat, no faces, each served the
way it comes (a cup on a saucer, dumplings in a steamer, noodles in a bowl
with chopsticks, pizza in its box). Each is drawn around (0, 0), the middle
of the table's top, and the hot ones steam."""
import math
from draw import *

STEAM = 6     # steam frames, 200 ms each


def coffee(k=0):
    """A cup of coffee on its saucer, a heart in the crema, steam rising."""
    p = Pic()
    plate(p, 0, 0, 40)
    ellipse(p, 0, 0, 22, 'path-2')                       # the cup's ring on the saucer
    # the handle, on the shaded right
    for x, y in ((11, -12), (12, -12), (13, -12), (14, -11), (15, -10), (15, -9), (15, -8), (14, -7), (13, -6),
                 (12, -6)):
        p.put(x, y, 'path-2')
        p.put(x, y + 1, 'path-3')
    dish(p, 0, -14, 24, 12, ('cream', 'cream', 'path-1', 'path-2'), foot=18)
    ellipse(p, 0, -14, 24, 'cream')
    ellipse(p, 0, -14, 20, 'wood-3')                     # the coffee
    ellipse(p, 0, -14, 16, 'clay-2')                     # the crema
    for x, y in ((-3, -15), (-2, -15), (1, -15), (2, -15), (-4, -14), (-1, -14), (0, -14), (3, -14), (-3, -13),
                 (-2, -13), (-1, -13), (0, -13), (1, -13), (2, -13), (-1, -12), (0, -12)):
        p.put(x, y, 'cream')                             # a heart poured into it
    steam(p, 0, -20, k, n=3, tall=16, spread=6)
    return p


def dumplings(k=0):
    """Three pleated dumplings in a bamboo steamer, steam rising."""
    p = Pic()
    dish(p, 0, -8, 54, 8, ('gold-1', 'gold-2', 'gold-2', 'gold-3'))
    for y in (-3, 0):                                    # the steamer's woven bands
        band(p, 0, y, 54, 1, lambda x, t: 'gold-3' if x < 14 else 'gold-4')
    ellipse(p, 0, -8, 54, 'gold-1')                      # the rim
    ellipse(p, 0, -8, 50, 'gold-3')                      # inside, its slats
    ellipse(p, 0, -9, 46, 'gold-3')
    for cx, cy in ((-8, -14), (8, -14), (0, -7)):
        ellipse(p, cx + 1, cy + 1, 18, 'gold-4')         # its shadow on the slats
        dome(p, cx, cy, 18, 9, ('cream', 'cream', 'path-1', 'path-2'))
        for i in (-3, -1, 1, 3):                         # the pleats along its crest
            p.put(cx + i, cy - 8 + (abs(i) > 2), 'path-2')
        p.put(cx - 1, cy - 9, 'path-1')
        p.put(cx, cy - 9, 'path-1')
    band(p, 0, -8, 54, 2, 'gold-1')                      # the rim in front, over the paper's edge
    steam(p, 0, -20, k, n=3, tall=18, spread=10)
    return p


def noodle_soup(k=0):
    """A red bowl of noodle soup: golden broth, noodles, half an egg, two
    slices of pork, scallions and nori, chopsticks across the rim."""
    p = Pic()
    def broth(x, y):
        # noodles as wavy strands across the broth
        s = math.sin((x + 2 * y) / 2.2)
        return 'gold-1' if s > 0.35 else 'clay-1'
    bowl(p, 0, -14, 56, 14, TOMATO, 'cream', broth)
    # pork slices, back right
    for cx, cy in ((8, -19), (14, -16)):
        ellipse(p, cx, cy, 12, 'brick-1')
        ellipse(p, cx - 1, cy, 8, 'clay-1')
    # half an egg, front left
    ellipse(p, -10, -11, 14, 'cream')
    ellipse(p, -10, -11, 8, 'clay-2')
    ellipse(p, -11, -12, 4, 'gold-1')
    # nori standing at the back, left
    for x in range(-16, -8):
        for y in range(-26, -17):
            p.put(x, y + (x + 16) // 2, 'grass-4')
    for x in range(-16, -8):
        p.put(x, -26 + (x + 16) // 2, 'grass-3')
    # scallions
    for x, y in ((2, -12), (4, -10), (-1, -17), (1, -19), (-4, -18), (6, -13), (12, -11)):
        p.put(x, y, 'grass-2')
        p.put(x + 1, y, 'grass-3')
    # chopsticks across the rim, front right to back
    stick(p, -6, -6, 38, 'wood-1', 'wood-3')
    stick(p, -2, -4, 36, 'wood-1', 'wood-3')
    steam(p, 0, -24, k, n=3, tall=16, spread=10)
    return p


def pasta(k=0):
    """Spaghetti on a plate, twirled into a mound, tomato sauce and basil on
    top, a fork beside it."""
    p = Pic()
    plate(p, 0, 0, 58)

    def strands(x, y, i):
        a = math.atan2(y * 2, x)
        r = math.hypot(x, y * 2)
        s = math.sin(r / 1.6 + a * 2)
        return ('gold-1', 'gold-1', 'clay-1', 'clay-2')[i] if s > -0.2 else ('clay-1', 'clay-1', 'clay-2', 'clay-3')[i]
    dome(p, 0, -2, 38, 12, CRUST, color=strands)
    dome(p, -1, -12, 24, 3, ('roof-1', 'roof-2', 'roof-2', 'roof-3'))      # the sauce
    for x, y in ((-3, -18), (-2, -18), (-4, -17), (-3, -17), (-2, -17), (-1, -17), (-3, -16), (-2, -16)):
        p.put(x, y, 'grass-2')                                              # a basil leaf
    p.put(-1, -18, 'grass-3')
    p.put(0, -17, 'grass-3')
    for x, y in ((3, -15), (5, -13), (-6, -13), (1, -12)):
        p.put(x, y, 'cream')                                                # parmesan
    # the fork, lying on the plate's right, along a 2:1 line
    stick(p, 14, 6, 14, 'stone-1', 'stone-3')
    for i in range(3):
        stick(p, 28 + i, 0 + i // 2 - i, 1, 'stone-1')
    for x, y in ((27, -1), (28, -2), (29, -2), (30, -3)):
        p.put(x, y, 'stone-1')
        p.put(x, y + 1, 'stone-2')
    return p


def ice_cream(k=0):
    """Three scoops in a paper cup (ube, vanilla and mango), a cherry on top
    and a wafer stuck in."""
    p = Pic()
    ellipse(p, 0, 0, 32, 'path-3')                       # where it stands
    dish(p, 0, -11, 32, 11, ('plum-1', 'plum-2', 'plum-2', 'plum-3'), foot=24)
    ellipse(p, 0, -11, 32, 'cream')                      # the cup's rolled rim
    ellipse(p, 0, -11, 28, 'plum-3')
    dome(p, -7, -13, 20, 10, ('clay-1', 'clay-1', 'clay-2', 'clay-3'))     # mango, back left
    dome(p, 7, -13, 20, 10, UBE)                                           # ube, back right
    dome(p, 0, -9, 20, 9, ('cream', 'cream', 'path-1', 'path-2'))          # vanilla, in front
    dome(p, 1, -19, 16, 8, UBE)                                            # and ube on top
    # the wafer, stuck in at the back
    for x in range(10, 14):
        for y in range(-36, -22):
            p.put(x, y + (x - 10) // 2, 'gold-1' if x < 12 else 'gold-2')
    # the cherry
    dome(p, 0, -27, 8, 4, ('roof-1', 'roof-2', 'roof-3', 'roof-3'))
    for x, y in ((1, -32), (2, -33), (2, -34), (3, -35)):
        p.put(x, y, 'wood-3')
    return p


def skewers(k=0):
    """Two barbecue skewers on a plate: glazed pork, pepper and onion on
    bamboo sticks, smoke curling up off the char."""
    p = Pic()
    plate(p, 0, 0, 58)
    for x0, y0 in ((-22, 0), (-18, 8)):
        stick(p, x0, y0, 44, 'gold-1', 'gold-3')
        pieces = (BEEF, LEAF, BEEF, ('cream', 'path-1', 'path-2', 'path-3'), BEEF)
        for i, ramp in enumerate(pieces):
            cx = x0 + 8 + i * 7
            cy = y0 - (cx - x0) // 2
            if ramp is BEEF:
                box(p, cx - 1, cy - 7, 6, 6, 6, 'brick-1', 'brick-2', 'brick-3', r=1)
                p.put(cx - 2, cy - 2, 'soil-4')
                p.put(cx - 1, cy - 2, 'soil-4')
                p.put(cx + 2, cy - 1, 'soil-4')
                p.put(cx - 1, cy - 6, 'clay-1')
            else:
                box(p, cx - 1, cy - 6, 6, 4, 5, ramp[0], ramp[1], ramp[2], r=1)
    steam(p, -2, -16, k, n=2, tall=10, spread=16)
    return p


def bread(k=0):
    """A loaf with slashes across its crust and two pan de sal on a wooden
    board, crumbs about."""
    p = Pic()
    a, b, h = 38, 26, 4
    box(p, -(a - b) // 2, -(a + b) // 4 + 2 - h, a, b, h, 'wood-1', 'wood-2', 'wood-3', r=4)
    # the loaf: a long bevelled box, rounded hard
    la, lb, lh = 26, 12, 9
    lx, ly = -4 - (la - lb) // 2, -2 - (la + lb) // 4 - h - lh

    def crust(u, v):
        if 4 < u < la - 3 and abs((u % 7) - (v * 0.45) - 1.5) < 0.8 and 2 < v < lb - 2:
            return 'gold-1'
        return 'clay-1' if v < lb - 3 else 'clay-2'
    box(p, lx, ly, la, lb, lh, crust, 'clay-2', 'clay-3', r=5)
    # two pan de sal in front, right
    dome(p, 10, 2, 12, 5, BUN)
    dome(p, 2, 6, 12, 5, BUN)
    for x, y in ((9, -4), (11, -3), (1, 0), (3, 1)):
        p.put(x, y, 'path-1')
    for x, y in ((-12, 6), (16, 0), (-14, 2)):
        p.put(x, y, 'clay-2')
    return p


def cake(k=0):
    """A round cake on a plate, cream piped round its top, strawberries on
    it and one candle whose flame flickers."""
    p = Pic()
    plate(p, 0, 0, 58)
    dish(p, 0, -16, 44, 16, ('cream', 'path-1', 'path-1', 'path-2'), top_c='cream')
    # a ring of strawberry through the middle of its side
    band(p, 0, -6, 44, 3, lambda x, t: 'roof-1' if x < 10 else 'roof-2')
    # piped cream round the top's edge
    for i in range(10):
        a = math.pi * 2 * i / 10
        cx, cy = round(18 * math.cos(a)), round(-16 + 9 * math.sin(a))
        dome(p, cx, cy, 6, 3, ('cream', 'cream', 'path-1', 'path-2'))
    # strawberries on top
    for cx, cy in ((-6, -18), (6, -18), (0, -14)):
        dome(p, cx, cy, 6, 4, TOMATO)
        p.put(cx - 1, cy - 5, 'grass-2')
        p.put(cx, cy - 5, 'grass-3')
    # the candle, and its flame
    for y in range(-30, -20):
        p.put(-1, y, 'glass-1')
        p.put(0, y, 'glass-2')
    flame = ((0, -1), (-1, 0), (0, 0), (-1, 1), (0, 1), (-1, 2), (0, 2))
    lift = (0, 1, 0, -1, 0, 1)[k % 6]
    for x, y in flame:
        p.put(x - (k % 2) * (y < 1), -33 + y + lift, 'gold-1' if y < 1 else 'clay-1')
    p.put(-1, -36 + lift, 'clay-1')
    return p


def rice_bowl(k=0):
    """A rice bowl with its toppings: a fried egg, slices of beef, bok choy,
    scallions and sesame; chopsticks across the rim, steam."""
    p = Pic()

    def rice(x, y):
        return 'path-1' if (int(x * 3) + int(y * 5)) % 7 == 0 else 'cream'
    bowl(p, 0, -14, 54, 14, ('teal-2', 'teal-3', 'teal-3', 'teal-4'), 'cream', rice)
    band(p, 0, -5, 46, 2, lambda x, t: 'cream' if x < 10 else 'path-1')   # a cream band round the bowl
    dome(p, 0, -15, 44, 4, ('cream', 'cream', 'path-1', 'path-1'))
    # beef slices, back right
    for cx, cy in ((10, -20), (14, -16), (6, -17)):
        ellipse(p, cx, cy, 10, 'brick-2')
        ellipse(p, cx - 1, cy, 6, 'brick-1')
    # bok choy, back left
    for cx, cy in ((-12, -20), (-8, -22)):
        ellipse(p, cx, cy, 10, 'grass-2')
        ellipse(p, cx + 1, cy + 1, 4, 'grass-1')
    # the fried egg, in front
    ellipse(p, -4, -12, 18, 'cream')
    ellipse(p, -2, -12, 18, 'cream')
    dome(p, -3, -12, 8, 3, ('gold-1', 'clay-1', 'clay-1', 'clay-2'))
    for x, y in ((6, -11), (8, -13), (10, -10), (-14, -14), (0, -21), (-3, -19)):
        p.put(x, y, 'grass-2')
    for x, y in ((4, -14), (12, -13), (-8, -16), (2, -19)):
        p.put(x, y, 'path-3')
    stick(p, -6, -6, 38, 'wood-1', 'wood-3')
    stick(p, -2, -4, 36, 'wood-1', 'wood-3')
    steam(p, 0, -26, k, n=3, tall=14, spread=10)
    return p


def burger(k=0):
    """A cheeseburger on a plate: a sesame bun, lettuce, tomato, cheese
    melting over the patty."""
    p = Pic()
    plate(p, 0, 0, 54)
    dish(p, 0, -6, 38, 5, ('clay-2', 'clay-2', 'clay-3'), top_c='clay-1')                         # the bottom bun
    dish(p, 0, -11, 40, 5, ('wood-3', 'wood-3', 'wood-4', 'wood-4'), top_c='wood-3')   # the patty
    ellipse(p, 0, -12, 42, 'gold-1')                                       # the cheese
    for cx in (-14, 4, 15):                                                # its corners melting down
        for y in range(-11, -6):
            for x in range(cx - (-6 - y) // 2 - 1, cx + (-6 - y) // 2 + 1):
                p.put(x, y, 'gold-1' if x < cx else 'gold-2')
    band(p, 0, -12, 44, 3, lambda x, t: None if t == 0 and (x // 3) % 2 else 'grass-2' if x < 8 else 'grass-3')   # the lettuce frill
    dish(p, 0, -15, 38, 2, ('roof-1', 'roof-1', 'roof-2', 'roof-3'), top_c='roof-2')   # tomato
    dome(p, 0, -16, 40, 14, ('clay-1', 'clay-1', 'clay-2', 'clay-3'))                                           # the top bun
    for x, y in ((-8, -26), (-2, -28), (5, -26), (-12, -22), (10, -23), (2, -23), (-5, -21), (14, -19)):
        p.put(x, y, 'cream')
        p.put(x + 1, y, 'path-1')
    return p


def pizza(k=0):
    """A pizza in its takeout box, the lid up behind: pepperoni and basil on
    the cheese, cut in slices, steam rising."""
    p = Pic()
    a = 30
    bx, by = 0, -(a + a) // 4 - 4
    # the lid, standing up along the box's back right edge (along the columns)
    for s in range(a + 1):
        x = bx + s
        ytop = by + s // 2
        for t in range(24):
            p.put(x, ytop - 24 + t, 'path-1' if t > 1 else 'wood-1')
        p.put(x, ytop - 25, 'wood-2')
    box(p, bx, by, a, a, 4, 'path-2', 'wood-1', 'wood-2')
    top(p, bx, by, a, a, 'path-3')
    top(p, bx, by + 1, a - 2, a - 2, 'path-2')            # the box's floor, inside its walls
    # the pizza, a circle on the box's floor
    dish(p, 0, -3, 38, 2, ('clay-1', 'clay-2', 'clay-3'), top_c='clay-1')
    ellipse(p, 0, -3, 32, 'gold-1')
    for x in range(-15, 16):                              # slices: cuts across it
        p.put(x, -3, 'gold-2') if abs(x) > 1 else None
    line(p, -8, -10, 8, 4, 'gold-2')
    line(p, 8, -10, -8, 4, 'gold-2')
    for cx, cy in ((-8, -6), (6, -7), (-2, -1), (9, -1), (-9, 1), (2, 4), (0, -9)):
        ellipse(p, cx, cy, 6, 'roof-2')
        p.put(cx - 2, cy - 1, 'roof-1')
    for x, y in ((-4, -6), (4, -3), (-6, 3)):
        p.put(x, y, 'grass-2')
        p.put(x + 1, y, 'grass-3')
    steam(p, 0, -14, k, n=2, tall=14, spread=12)
    return p


FOODS = [
    ('coffee', coffee, True, 'A cup of coffee on its saucer, a heart poured in the crema, steam rising.'),
    ('dumplings', dumplings, True, 'Three pleated dumplings in a bamboo steamer, steam rising.'),
    ('noodle-soup', noodle_soup, True, 'A red bowl of noodle soup: golden broth, noodles, half an egg, pork, scallions and nori, chopsticks across the rim.'),
    ('pasta', pasta, False, 'Spaghetti twirled into a mound on a plate, tomato sauce, basil and parmesan on top, a fork beside it.'),
    ('ice-cream', ice_cream, False, 'Three scoops in a paper cup, ube, mango and vanilla, a cherry on top and a wafer stuck in.'),
    ('skewers', skewers, True, 'Two barbecue skewers on a plate, glazed pork, pepper and onion on bamboo sticks, smoke curling off the char.'),
    ('bread', bread, False, 'A scored loaf and two pan de sal on a wooden board, crumbs about.'),
    ('cake', cake, True, 'A round strawberry cream cake on a plate, cream piped round its top, one candle flickering.'),
    ('rice-bowl', rice_bowl, True, 'A teal rice bowl with its toppings: a fried egg, beef, bok choy, scallions and sesame, chopsticks across the rim, steam.'),
    ('burger', burger, False, 'A cheeseburger on a plate: a sesame bun, lettuce, tomato and cheese melting over the patty.'),
    ('pizza', pizza, True, 'A pepperoni pizza cut in slices in its takeout box, the lid up behind, steam rising.'),
]


def build_foods():
    for name, fn, hot, what in FOODS:
        notes = [what, 'Its anchor is the middle of what it stands on: place it by pixel (px) on the table\'s anchor, after the table.']
        if hot:
            word = 'flicker' if name == 'cake' else 'steam'
            notes.append(f'States: {word} ({STEAM} frames, 200 ms each, looping), idle (still).')
            frames = [fn(k) for k in range(STEAM)]
            o = sprite(frames, cat('Food'), notes,
                       states={word: {'frames': list(range(STEAM)), 'ms': 200}, 'idle': {'frames': [0], 'ms': 1000}},
                       start=word)
        else:
            o = sprite(fn(), cat('Food'), notes)
        save('food-' + name, o)
    return [n for n, *_ in FOODS]
