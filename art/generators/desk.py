"""The claude.dev section's work desk: one laptop busy with code and the desk
things round it, gently alive, as isometric pieces on the 2:1 grid, in layers
on one anchor and one short box that the page stacks over the forest band.

The plan on the grid (the pixel-art-style skill's one rule):

- The box is 176x56, as wide as the spot's stage and short, so it takes little
  of the section's height; (0, 0) is its middle. No table and no backdrop: the
  layers are transparent over the forest band, the things standing on an
  unseen desk plane.
- The laptop, open: its base a rounded box 30x18 units and 3 pixels deep (a
  lit grey top with rows of keys and a trackpad, mid left face, dark right
  face), its screen a panel 30x2 units and 20 pixels tall on the base's back
  edge, the display on its left face (toward the viewer's lower left), where
  lines of code type in, a cursor blinking, then clear and start again. A
  sticky note on the screen's top corner flutters.
- A coffee mug at the far left: a clay cylinder with a handle, steam rising.
  A phone lies flat in front of it, a rounded box 8x14 units and 2 pixels
  deep: now and then it buzzes, its screen lighting with a notification.
- A desk lamp to the laptop's right: a teal puck of a base, a pole, an arm
  leaning over the laptop and a rounded head whose bulb glows, breathing,
  short rays of light falling from it.
- A potted plant: a brick-red cylinder pot, its leaves 2:1 ellipses in four
  greens layered up, the top ones swaying a pixel.
- A stack of three notebooks (teal, red, plum rounded boxes, a gold pen on
  top) with a rubber duck (no face: a gold rounded body and head, an orange
  beak) bobbing on them.
- Sparkles twinkle (the spot's glint).
- The ship moment, a layer the page shows for 1.5 s on a tap: the screen goes
  green with a check mark, the lamp flashes bright, the phone lights green,
  sticky notes fly up like confetti and a rocket launches from behind the
  laptop up out of the box.
- Light from the upper left: tops lightest, left faces mid, right faces
  darkest. Screens and the bulb glow in their own colors. No outlines, no
  faces, no logos.

Layers, bottom to top: back (the mug and the phone), laptop, code (its screen
and the sticky note), props (the lamp, the plant, the notebooks and the
duck), sparkles; and ship over them on a tap."""
from draw import *  # noqa: F401,F403
from draw import Pic, cat, halves, save_scene, sprite, steam
from kit import box, cylinder, ellipse, line, puck
import draw

BOX = (-88, -30, 176, 56)
X0, Y0, W, H = BOX
CAT = cat('Desk')


def rbox(p, cx, cy, a, b, h, faces, r=2):
    """A rounded box whose footprint's middle is the pixel corner (cx, cy), standing h pixels tall."""
    return box(p, cx - (a - b) // 2, cy - h - (a + b) // 4, a, b, h, *faces, r=r)


def face_map(bx, by, a, b, h):
    """{(s, t): (x, y)} for the left face of a box: s pixels across from its left edge, t rows down."""
    p = Pic()
    box(p, bx, by, a, b, h, 't', lambda s, t: ('L', s, t), 'r')
    return {(c[1], c[2]): q for q, c in p.items() if isinstance(c, tuple)}


def in_box(p):
    return Pic({q: c for q, c in p.items() if X0 <= q[0] < X0 + W and Y0 <= q[1] < Y0 + H})


# ------------------------------------------------------------------ the laptop
LA, LB, LH = 30, 18, 3               # the base: units along the columns and rows, pixels deep
LBX, LBY = -34, -6                   # the base top's back corner
SA, SB, SH = 30, 2, 20               # the screen panel standing on its back edge
SCREEN = face_map(LBX, LBY - SH, SA, SB, SH)


def keys(u, v):
    """The base's top: rows of keys, a trackpad near the front edge, lit grey round them."""
    if 3 <= u < LA - 3 and 4 <= v < 11:
        return 'stone-2' if int(u) % 3 != 0 and int(v) % 2 == 0 else 'stone-1'
    if LA / 2 - 5 <= u < LA / 2 + 5 and 12 <= v < 16:
        return 'stone-2'
    return 'stone-1'


def bezel(s, t, w, h, bg, rim):
    return rim if s < 2 or s >= w - 2 or t < 2 or t >= h - 2 else bg


def laptop():
    p = Pic()
    box(p, LBX, LBY, LA, LB, LH, keys, 'stone-2', 'stone-3', r=3)
    box(p, LBX, LBY - SH, SA, SB, SH, 'stone-2', lambda s, t: bezel(s, t, SA, SH, 'ink', 'stone-4'), 'stone-3')
    return p


CODE = [(0, 10, 'gold-1'), (2, 14, 'grass-1'), (4, 9, 'cream'), (4, 12, 'clay-1'), (0, 6, 'teal-1')]
GAP = 3                              # rows from one line of code to the next
TYPE = 3                             # characters (pixels) typed a frame
HOLDS = 8                            # frames the full screen holds before it clears
NOTE = [(s, t) for s in range(23, 29) for t in range(1, 7)]   # the sticky note on the screen's top corner


def sticky(p, k):
    """The sticky note: gold, its lower corner curling up and back as it flutters."""
    curl = (k // 3) % 4 == 1
    for (s, t) in NOTE:
        if curl and s >= 27 and t >= 5:
            continue
        c = 'gold-2' if t == 1 else 'gold-1'
        if curl and (s, t) in ((26, 6), (27, 4), (28, 4)):
            c = 'gold-3'
        p.put(*SCREEN[(s, t)], c)
    for s in (24, 25, 26):
        p.put(*SCREEN[(s, 3)], 'roof-2')                     # a scribble on it


def code_frames():
    """The laptop's screen: lines of code typing in, a cursor at the end, then a pause and a clear."""
    total = sum(n for _, n, _ in CODE)
    typing = -(-total // TYPE)
    frames = []
    for k in range(typing + HOLDS):
        p = Pic()
        budget = min(total, k * TYPE)
        cursor = None
        for j, (ind, n, c) in enumerate(CODE):
            shown = max(0, min(n, budget))
            budget -= n
            t = 3 + GAP * j
            for s in range(4 + ind, 4 + ind + shown):
                p.put(*SCREEN[(s, t)], c)
            if cursor is None and shown < n:
                cursor = (4 + ind + shown, t)
        if cursor is None:
            cursor = (4, 3 + GAP * len(CODE))
        if k % 4 < 2 and cursor in SCREEN and cursor[1] < SH - 2:
            p.put(*SCREEN[cursor], 'cream')
        sticky(p, k)
        frames.append(p)
    return frames


# ------------------------------------------------------------------ the mug and the phone
MUG = (-74, 8)
PHONE = (-58, 19)                    # the middle of the phone's footprint
PA, PB = 8, 14


def mug(k):
    """The mug with steam rising."""
    p = Pic()
    mx, my = MUG
    cylinder(p, mx, my, 12, 8, 'clay-1', ['clay-1', 'clay-2', 'clay-3'])
    ellipse(p, mx, my, 8, 'wood-3')                          # the coffee
    for y in range(my + 2, my + 7):                          # the handle on its right
        p.put(mx + 7, y, 'clay-3')
        p.put(mx + 8, y, 'clay-3')
    for x in (mx + 6, mx + 7):
        p.put(x, my + 2, 'clay-3')
        p.put(x, my + 6, 'clay-3')
    p.erase([(mx + 7, y) for y in range(my + 3, my + 6)])
    steam(p, mx, my - 3, k % 6, n=2, tall=12, spread=5, c='stone-1')
    return p


PHONE_FRAMES = 16                    # 200 ms each: a buzz, the screen lit a while, then dark with a blinking light


def phone_top(lit, green=False):
    def top(u, v):
        if u < 1.5 or u > PA - 1.5 or v < 1.5 or v > PB - 1.5:
            return 'stone-4'
        if green:
            return 'grass-1' if 5 <= v < 8 else 'grass-2'
        if lit:
            return 'cream' if 3 <= v < 5 else 'glass-2'
        return 'ink'
    return top


def phone(k, green=False):
    p = Pic()
    lit = green or 0 <= k < 7
    dx = (1 if k % 2 else -1) if k < 3 and not green else 0     # it buzzes
    cx, cy = PHONE
    rbox(p, cx + dx, cy, PA, PB, 2, (phone_top(lit, green), 'stone-3', 'stone-4'), r=2)
    if not lit and k % 4 == 0:
        p.put(cx + dx + 2, cy - 7, 'teal-1')                 # the notification light
    return p


# ------------------------------------------------------------------ the lamp, the plant, the notebooks, the duck
LAMP = (12, 16)                      # the middle of the lamp's base
POLE = 22
HEAD = (2, -3)                     # the middle of the lamp head's footprint
HA, HH = 8, 5
LAMP_TEAL = ('teal-1', 'teal-2', 'teal-3')
GLOW = ['gold-1', 'gold-1', 'cream', 'cream', 'cream', 'gold-1', 'gold-1', 'gold-2']   # the bulb breathing


def head_face():
    return face_map(HEAD[0] - 0, HEAD[1] - HH - HA // 2, HA, HA, HH)


def lamp(k, flash=False):
    p = Pic()
    cx, cy = LAMP
    puck(p, cx, cy, 14, 2, 'teal-1', ['teal-2', 'teal-3'])
    rbox(p, cx, cy - 2, 2, 2, POLE, LAMP_TEAL, r=0)
    top = cy - 2 - POLE                                      # the arm leans from the pole's top over the laptop
    hx, hy = HEAD
    line(p, cx, top, hx + 3, hy - HH - 3, 'teal-2')         # the arm, two pixels thick
    line(p, cx, top + 1, hx + 3, hy - HH - 2, 'teal-3')
    rbox(p, hx, hy, HA, HA, HH, LAMP_TEAL, r=3)
    glow = 'cream' if flash else GLOW[k % len(GLOW)]
    face = head_face()
    for (s, t), q in face.items():                           # the bulb: the head's lit underside, glowing
        if 1 <= s < HA - 1 and t >= HH - 2:
            p.put(*q, glow)
    ellipse(p, hx - 2, hy - 1, 6, glow)                     # the bulb, at the shade's mouth
    if flash or GLOW[k % len(GLOW)] == 'cream':
        bx, by = face[(HA // 2, HH - 1)]
        for i in range(1, 4 if not flash else 6):            # rays falling onto the keys
            for ox in (-4, 0, 4):
                p.put(bx + ox - i // 2, by + 1 + i, 'gold-1')
    return p


PLANT = (34, 14)
LEAVES = [(-5, -3, 10, 'grass-3', 0), (5, -4, 10, 'grass-4', 0), (-3, -8, 10, 'grass-2', 1),
          (4, -9, 8, 'grass-3', 1), (-1, -13, 8, 'grass-1', 2), (-6, -12, 6, 'grass-2', 2), (3, -16, 6, 'grass-1', 3)]
SWAY = [0, 0, 1, 1, 1, 0, 0, -1, -1, -1]                 # pixels the top leaves lean, 200 ms a step


def plant(k):
    p = Pic()
    cx, cy = PLANT
    cylinder(p, cx, cy, 14, 7, 'brick-1', ['brick-1', 'brick-2', 'brick-3'])
    ellipse(p, cx, cy, 10, 'soil-3')
    for dx, dy, w, c, tier in LEAVES:
        sway = SWAY[k] * (1 if tier >= 2 else 0)
        ellipse(p, cx + dx + sway, cy + dy, w, c)
    return p


BOOKS = (62, 18)
BOOK_STACK = [(0, 0, 18, 12, 3, ('teal-1', 'teal-2', 'teal-3')), (1, -3, 16, 11, 3, ('roof-1', 'roof-2', 'roof-3')),
              (-1, -6, 17, 12, 3, ('plum-1', 'plum-2', 'plum-3'))]


def books():
    """Three notebooks stacked a little askew, cream page edges down their sides, a gold pen on top."""
    p = Pic()
    bx, by = BOOKS
    for dx, dy, a, b, h, (t, left, right) in BOOK_STACK:
        rbox(p, bx + dx, by + dy, a, b, h, (t, lambda s, tt, l=left: 'cream' if tt == 1 and s > 2 else l, right), r=2)
    for i in range(10):                                      # the pen, along a 2:1 line on the top
        x, y = bx + 2 + i, by - 14 + i // 2
        p.put(x, y, 'gold-1')
        p.put(x, y + 1, 'gold-3')
    p.put(bx + 12, by - 9, 'ink'); p.put(bx + 13, by - 9, 'ink')
    return p


DUCK_BOB = [0, 0, 0, -1, -1, 0, 0, 0, 0, 0]


def duck(k):
    """A rubber duck, no face: a gold rounded body, a rounded head at its front left, an orange beak."""
    p = Pic()
    bx, by = BOOKS
    d = DUCK_BOB[k]
    gold = ('gold-1', 'gold-2', 'gold-3')
    rbox(p, bx + 1, by - 9 + d, 10, 8, 5, gold, r=3)              # the body, its tail to the back
    rbox(p, bx - 3, by - 12 + d, 6, 6, 5, gold, r=2)              # the head, at the front left
    rbox(p, bx - 7, by - 13 + d, 4, 3, 2, ('clay-1', 'clay-2', 'clay-3'), r=1)   # the beak, toward the viewer
    return p


PROPS_FRAMES = 10                    # the lamp, the plant and the duck each loop in 2 s


# ------------------------------------------------------------------ the ship moment
SHIP = 15
NOTES = [(-30, -4, 'gold-1', -1), (-10, -8, 'roof-1', 1), (6, -2, 'teal-1', 2), (-22, 0, 'plum-1', -2),
         (20, -6, 'gold-1', 1), (-40, -2, 'grass-1', -1), (0, 2, 'cream', 0), (-16, -6, 'roof-1', 2)]


def check(face, w, h, bg):
    """A face's display gone green, a cream check mark in its middle."""
    p = Pic()
    for (s, t), q in face.items():
        if 2 <= s < w - 2 and 2 <= t < h - 2:
            p.put(*q, bg)
    cx, cy = w // 2 - 5, h // 2 - 1
    for i in range(4):                                       # the short stroke, down
        for d in (0, 1):
            q = face.get((cx + i, cy + i + d))
            if q:
                p.put(*q, 'cream')
    for i in range(1, 9):                                    # the long stroke, up
        for d in (0, 1):
            q = face.get((cx + 3 + i, cy + 3 - i + d))
            if q:
                p.put(*q, 'cream')
    return p


def rocket(p, cx, cy, k):
    """A rocket: a rounded prism 6 units and 12 pixels tall, a red nose, red fins, a flickering flame."""
    box(p, cx - 6, cy - 12 - 6, 6, 6, 12, 'cream', 'stone-1', 'stone-2', r=2)
    box(p, cx - 4, cy - 15 - 4, 4, 4, 3, 'roof-1', 'roof-2', 'roof-3', r=1)
    for q in ((cx - 4, cy - 10), (cx - 3, cy - 10), (cx - 4, cy - 9), (cx - 3, cy - 9)):
        p.put(*q, 'glass-2')                                 # its window
    for dy in range(4):
        p.put(cx - 8, cy - 4 + dy, 'roof-2'); p.put(cx + 5, cy - 4 + dy, 'roof-3')
    for i, c in enumerate(('gold-1', 'clay-1', 'clay-2') if k % 2 else ('cream', 'gold-1', 'clay-1', 'clay-2')):
        for x in range(cx - 2 + i // 2, cx + 2 - i // 2):
            p.put(x, cy + 1 + i, c)


def ship_frames():
    out = []
    screen = check(SCREEN, SA, SH, 'grass-2')
    for k in range(SHIP):
        lit = Pic({q: c for q, c in lamp(0, flash=True).items() if c in ('cream', 'gold-1')})
        green = Pic({q: c for q, c in phone(0, green=True).items() if c.startswith('grass')})
        p = screen.over(lit if k % 4 < 2 else Pic()).over(green)
        for x, y, c, vx in NOTES:                            # sticky notes flying up and tumbling down
            nx, ny = x + vx * k, y - 5 * k + k * k // 3
            for q in ((nx, ny), (nx + 1, ny), (nx, ny + 1), (nx + 1, ny + 1)) if k % 2 else \
                    ((nx, ny), (nx + 1, ny), (nx + 2, ny), (nx + 1, ny + 1)):
                p.put(*q, c)
        y = 2 - k * k // 2 - 3 * k                           # the rocket climbs faster and faster
        if y > Y0 - 30:
            rocket(p, -12, y, k)
        for i in range(min(k, 5)):                           # puffs where it lifted off
            p.put(-16 - 3 * i, 4 + i % 2, 'stone-1'); p.put(-8 + 3 * i, 4 + (i + 1) % 2, 'stone-1')
        out.append(in_box(p))
    return out


# ------------------------------------------------------------------ building
def save(name, o):
    draw.save(name, o)


def one_state(frames, notes, name, ms, seq=None):
    seq = seq if seq is not None else list(range(len(frames)))
    return sprite(frames, CAT, notes, states={name: {'frames': seq, 'ms': ms}}, start=name)


def scene(notes, items, output):
    return {'notes': notes, 'output': output, 'viewBox': list(BOX), 'items': items}


def item(name, at=(0, 0), state=None, order=0):
    i = {'object': name, 'depth': 'back', 'order': order, 'at': {'px': list(at)}}
    if state:
        i['state'] = state
    return i


SPARKLES = [(-38, -24, 0), (-56, -6, 1), (26, -24, 2), (50, -12, 1), (80, 2, 0)]


def build_desk():
    save('dev-laptop', sprite(laptop(), CAT, [
        'The laptop, open: a rounded base 30x18 units (lit grey keys and a trackpad on top) with its screen panel '
        'standing on the back edge, the display (dark, in a grey bezel) on its left face. No logo.',
        'Place it by pixel (px) at the strip\'s anchor; its screen is dev-code, over it.']))
    code = code_frames()
    save('dev-code', one_state(code, [
        'What the laptop\'s screen shows: lines of code in gold, green, cream, orange and teal typing in, a cream '
        'cursor blinking at the end, then a pause and a clear; a gold sticky note on its top corner fluttering.',
        'Place it by pixel (px) at the strip\'s anchor, over dev-laptop.',
        f'States: type ({len(code)} frames of 100 ms, looping).'], 'type', 100))
    save('dev-mug', one_state([mug(k) for k in range(6)], [
        'A clay coffee mug (a cylinder with a handle on its right, coffee inside) with steam rising.',
        'Place it by pixel (px) at the strip\'s anchor.',
        'States: run (6 frames of 200 ms, looping).'], 'run', 200))
    save('dev-phone', one_state([phone(k) for k in range(PHONE_FRAMES)], [
        'A phone lying flat: a dark rounded box 8x14 units, 2 pixels deep. It buzzes and its screen lights with a '
        'notification, then it goes dark, a teal light blinking.',
        'Place it by pixel (px) at the strip\'s anchor.',
        f'States: run ({PHONE_FRAMES} frames of 200 ms, looping).'], 'run', 200))
    save('dev-lamp', one_state([lamp(k) for k in range(PROPS_FRAMES)], [
        'A teal desk lamp: a puck of a base, a pole, an arm leaning over the laptop and a rounded head whose bulb '
        'glows, breathing gold to cream, rays of light falling from it at its brightest.',
        'Place it by pixel (px) at the strip\'s anchor.',
        f'States: run ({PROPS_FRAMES} frames of 200 ms, looping).'], 'run', 200))
    save('dev-plant', one_state([plant(k) for k in range(PROPS_FRAMES)], [
        'A potted plant: a brick-red pot, its leaves 2:1 ellipses in four greens layered up, the top ones swaying.',
        'Place it by pixel (px) at the strip\'s anchor.',
        f'States: run ({PROPS_FRAMES} frames of 200 ms, looping).'], 'run', 200))
    save('dev-books', sprite(books(), CAT, [
        'Three notebooks stacked a little askew (teal, red, plum rounded boxes, cream page edges), a gold pen on top.',
        'Place it by pixel (px) at the strip\'s anchor.']))
    save('dev-duck', one_state([duck(k) for k in range(PROPS_FRAMES)], [
        'A rubber duck, no face: a gold rounded body, a rounded head at its front left, an orange beak; it bobs on the '
        'notebooks.',
        'Place it by pixel (px) at the strip\'s anchor, over dev-books.',
        f'States: run ({PROPS_FRAMES} frames of 200 ms, looping).'], 'run', 200))
    ship = ship_frames()
    left, right = halves(ship)
    for side, fs in (('left', left), ('right', right)):
        save(f'dev-ship-{side}', one_state(fs, [
            f'The ship moment ({side} half): the screen gone green with a cream check mark, the lamp flashing, the '
            'phone lit green, sticky notes flying up, a rocket launching from behind the laptop up out of the strip.',
            'The page shows it for 1.5 s on a tap, over everything.',
            f'States: ship ({SHIP} frames of 100 ms, looping; the page takes it away after one).'], 'ship', 100))

    layer = lambda name, notes, items: save_scene(name, scene(notes, items, name + '.svg'))
    layer('dev-back', ['The desk\'s back layer: the mug and the phone.'],
          [item('dev-mug', state='run'), item('dev-phone', state='run', order=1)])
    layer('dev-laptop', ['The laptop.'], [item('dev-laptop')])
    layer('dev-code', ['The laptop\'s screen, typing, and its sticky note.'], [item('dev-code', state='type')])
    layer('dev-props', ['The lamp, the plant, the notebooks and the duck.'],
          [item('dev-lamp', state='run'), item('dev-plant', state='run', order=1), item('dev-books', order=2),
           item('dev-duck', state='run', order=3)])
    layer('dev-sparkles', ['Sparkles round the desk.'],
          [item('brief-glint', (x, y), f'twinkle-{ph}', i) for i, (x, y, ph) in
           sorted(enumerate(SPARKLES), key=lambda e: (e[1][1], e[1][0]))])
    layer('dev-ship', ['The ship moment, shown on a tap.'],
          [item('dev-ship-left', state='ship'), item('dev-ship-right', state='ship', order=1)])
    return ['dev-back', 'dev-laptop', 'dev-code', 'dev-props', 'dev-sparkles']
