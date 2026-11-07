"""The claude.dev section's desk: a developer's corner, busy and alive, as
isometric pieces on the 2:1 grid, in layers on one anchor and one short box
that the page stacks over the section's forest band.

The plan on the grid (the pixel-art-style skill's one rule):

- The box is 176x56, as wide as the spot's stage and short, so it takes little
  of the section's height; (0, 0) is its middle. No table and no backdrop: the
  layers are transparent over the forest band.
- One laptop, open, standing on nothing: its base a rounded box 30x18 units
  and 3 pixels deep (lit grey top with rows of keys and a trackpad, mid left
  face, dark right face), its screen a panel 30x2 units and 20 pixels tall
  standing on the base's back edge, the display on its left face (toward the
  viewer's lower left), where lines of code type in, line after line, a
  cursor blinking, then clear and start again.
- A terminal window floating to its right: a thin panel 30x3 units and 22
  pixels tall, a title bar with three dots, a navy display where a command
  types, a progress bar fills and a done line comes up.
- Three code blocks floating between them: rounded cubes 8 units and 8 pixels
  tall (teal, plum, gold), a glyph on each left face ({, }, >_), bobbing at
  three phases.
- A coffee mug at the far left: a clay cylinder with a handle, steam rising.
- A server tower at the far right: a dark rounded box 10 units and 30 pixels
  tall, drive slots racked down its left face, each with a light blinking its
  own way, vents down its right face.
- Sparkles twinkle round the screen and the blocks (the spot's glint).
- The ship moment, a layer the page shows for 1.5 s on a tap: both screens go
  green with a check mark and a rocket (a rounded prism, a red nose, a flame)
  launches from behind the laptop up out of the box.
- Light from the upper left: tops lightest, left faces mid, right faces
  darkest. Screens glow, so their faces are the display's own colors. No
  outlines, no faces, no logos.

Layers, bottom to top: back (mug, server tower), laptop, code (the laptop's
screen), terminal, term (the terminal's screen), blocks, sparkles; and ship
over them on a tap."""
from draw import *  # noqa: F401,F403
from draw import Pic, cat, despeck, halves, save_scene, sprite, steam
from kit import box, cylinder, puck, line
import draw

BOX = (-88, -30, 176, 56)
X0, Y0, W, H = BOX
CAT = cat('Desk')

# ------------------------------------------------------------------ the laptop
LA, LB, LH = 30, 18, 3               # the base: units along the columns and rows, pixels deep
LBX, LBY = -34, -6                   # the base top's back corner
SA, SB, SH = 30, 2, 20               # the screen panel standing on its back edge
TA_, TB_, TH_ = 30, 3, 22            # the terminal panel
TBX, TBY = 30, -26                   # its top's back corner


def face_map(bx, by, a, b, h):
    """{(s, t): (x, y)} for the left face of a box: s pixels across from its left edge, t rows down."""
    p = Pic()
    box(p, bx, by, a, b, h, 't', lambda s, t: ('L', s, t), 'r')
    return {(c[1], c[2]): q for q, c in p.items() if isinstance(c, tuple)}


SCREEN = face_map(LBX, LBY - SH, SA, SB, SH)
TERM = face_map(TBX, TBY, TA_, TB_, TH_)


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
        frames.append(p)
    return frames


# ------------------------------------------------------------------ the terminal
def term_panel(s, t):
    if t < 4:
        if 1 <= t <= 2 and s in (3, 4, 7, 8, 11, 12):
            return {3: 'roof-1', 4: 'roof-1', 7: 'gold-1', 8: 'gold-1', 11: 'grass-1', 12: 'grass-1'}[s]
        return 'stone-1'
    return 'stone-2' if s < 1 or s >= TA_ - 1 or t >= TH_ - 1 else 'glass-4'


def terminal():
    p = Pic()
    box(p, TBX, TBY, TA_, TB_, TH_, 'stone-1', term_panel, 'stone-3')
    return p


TERM_FRAMES = 26


def term_frames():
    """The terminal's display: a prompt and a command typing, a progress bar filling, a done line."""
    out = []
    for k in range(TERM_FRAMES):
        p = Pic()
        for s in (3, 4):
            p.put(*TERM[(s, 7)], 'grass-1')                  # the prompt
        for s in range(6, 6 + min(16, 3 * k)):
            p.put(*TERM[(s, 7)], 'cream')                    # the command
        if k >= 6:
            for s in range(3, TA_ - 4):
                p.put(*TERM[(s, 11)], 'stone-4')             # the progress bar's track
                p.put(*TERM[(s, 12)], 'stone-4')
            for s in range(3, 3 + min(TA_ - 7, 2 * (k - 6))):
                p.put(*TERM[(s, 11)], 'grass-1')
                p.put(*TERM[(s, 12)], 'grass-2')
        if k >= 18:
            for s in (3, 4, 5):
                p.put(*TERM[(s, 16 - (s == 4))], 'grass-1')  # a little check
            for s in range(8, 18):
                p.put(*TERM[(s, 16)], 'gold-1')              # done
        if k >= 18 and k % 4 < 2:
            p.put(*TERM[(20, 16)], 'cream')
        out.append(p)
    return out


# ------------------------------------------------------------------ the code blocks
GLYPHS = {
    'open': ['..##', '.#..', '##..', '.#..', '..##'],
    'close': ['##..', '..#.', '..##', '..#.', '##..'],
    'prompt': ['#...', '.#..', '..#.', '.#..', '#.##'],
}
BLOCKS = [('open', ('teal-1', 'teal-2', 'teal-3'), (2, -10), 0), ('close', ('plum-1', 'plum-2', 'plum-3'), (16, -16), 1),
          ('prompt', ('gold-1', 'gold-2', 'gold-3'), (10, 2), 2)]


def block(glyph, faces):
    """A rounded cube 8 units, 8 pixels tall, its footprint's middle at (0, 0), a cream glyph on its left face."""
    top_c, left_c, right_c = faces
    g = GLYPHS[glyph]

    def left(s, t):
        gs, gt = s - 2, t - 1
        if 0 <= gt < len(g) and 0 <= gs < len(g[0]) and g[gt][gs] == '#':
            return 'cream'
        return left_c
    p = Pic()
    box(p, 0, -8 - 4, 8, 8, 8, top_c, left, right_c, r=2)
    return p


BOB = [0, 0, -1, -1, -2, -2, -2, -1, -1, 0, 0, 0]      # pixels up, 200 ms a step


# ------------------------------------------------------------------ the mug and the server
MUG = (-72, 12)


def mug(k):
    """The mug with steam rising."""
    p = Pic()
    mx, my = MUG
    cylinder(p, mx, my, 12, 8, 'clay-1', ['clay-1', 'clay-2', 'clay-3'])
    from kit import ellipse
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


SERVER = (70, 19)                    # the middle of the server tower's footprint
SV_A, SV_H = 10, 30


def server(k):
    """A server tower: a rounded box 10 units and 30 pixels tall, dark grey, its left face racked with
    drive slots, a light on each blinking its own way; vents down its right face."""
    p = Pic()
    lights = ('grass-1', 'gold-1', 'grass-1', 'teal-1', 'roof-1', 'grass-1')

    def left(s, t):
        row, r = divmod(t - 3, 4)
        if 0 <= row < len(lights) and r in (0, 1) and 2 <= s < SV_A - 1:
            if s >= SV_A - 3:                           # the light
                on = (k * (row + 2) + row * 3) % 5 < 3
                return lights[row] if on else 'ink'
            return 'ink'                                # the drive slot
        return 'stone-3'

    def right(s, t):
        return 'ink' if 3 <= t < SV_H - 3 and t % 3 == 0 and 2 <= s < SV_A - 2 else 'stone-4'
    cx, cy = SERVER
    box(p, cx - 0, cy - SV_H - SV_A // 2, SV_A, SV_A, SV_H, 'stone-2', left, right, r=2)
    return p


SERVER_FRAMES = 10                   # the lights blink through 10 frames of 200 ms


# ------------------------------------------------------------------ the ship moment
SHIP = 15


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
    lap = check(SCREEN, SA, SH, 'grass-2')
    trm = Pic({q: c for q, c in check(TERM, TA_, TH_, 'grass-2').items()})
    for k in range(SHIP):
        p = lap.over(trm)
        y = 2 - k * k // 2 * 1 - 3 * k                       # it climbs faster and faster
        if y > Y0 - 30:
            rocket(p, -12, y, k)
        for i in range(min(k, 5)):                           # puffs where it lifted off
            p.put(-16 - 3 * i, 4 + i % 2, 'stone-1'); p.put(-8 + 3 * i, 4 + (i + 1) % 2, 'stone-1')
        out.append(Pic({q: c for q, c in p.items() if X0 <= q[0] < X0 + W and Y0 <= q[1] < Y0 + H}))
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


SPARKLES = [(-38, -24, 0), (-6, -14, 1), (26, -22, 2), (-56, -2, 1), (46, 8, 0)]


def build_desk():
    save('dev-laptop', sprite(laptop(), CAT, [
        'The laptop, open: a rounded base 30x18 units (lit grey keys and a trackpad on top) with its screen panel '
        'standing on the back edge, the display (dark, in a grey bezel) on its left face. No logo.',
        'Place it by pixel (px) at the strip\'s anchor; its screen\'s code is `dev-code`, over it.']))
    code = code_frames()
    save('dev-code', one_state(code, [
        'What the laptop\'s screen shows: lines of code in gold, green, cream, orange and teal typing in, a cream '
        'cursor blinking at the end, then a pause and a clear.',
        'Place it by pixel (px) at the strip\'s anchor, over dev-laptop.',
        f'States: type ({len(code)} frames of 100 ms, looping).'], 'type', 100))
    save('dev-terminal', sprite(terminal(), CAT, [
        'A terminal window floating on the grid: a thin panel 30x3 units, 22 pixels tall, a light title bar with '
        'three dots (red, gold, green), a navy display.',
        'Place it by pixel (px) at the strip\'s anchor.']))
    term = term_frames()
    save('dev-term', one_state(term, [
        'The terminal\'s display: a green prompt and a cream command typing, a progress bar filling green, a '
        'check and a gold done line, a cursor blinking.',
        'Place it by pixel (px) at the strip\'s anchor, over dev-terminal.',
        f'States: run ({len(term)} frames of 100 ms, looping).'], 'run', 100))
    for glyph, faces, at, ph in BLOCKS:
        base = block(glyph, faces)
        frames = [base.moved(0, d) for d in sorted(set(BOB), reverse=True)]
        index = {d: i for i, d in enumerate(sorted(set(BOB), reverse=True))}
        seq = [index[d] for d in BOB]
        seq = seq[ph * 4:] + seq[:ph * 4]
        save(f'dev-block-{glyph}', one_state(frames, [
            f'A code block: a {faces[0].split("-")[0]} rounded cube 8 units and 8 pixels tall, a cream glyph '
            f'({glyph}) on its left face, bobbing.',
            'Place it by pixel (px) at the middle of its footprint.',
            'States: bob (12 frames of 200 ms, looping).'], 'bob', 200, seq))
    save('dev-mug', one_state([mug(k) for k in range(6)], [
        'A clay coffee mug (a cylinder with a handle on its right, coffee inside) with steam rising.',
        'Place it by pixel (px) at the strip\'s anchor, under the laptop.',
        'States: run (6 frames of 200 ms, looping).'], 'run', 200))
    save('dev-server', one_state([server(k) for k in range(SERVER_FRAMES)], [
        'A server tower: a dark grey rounded box 10 units and 30 pixels tall, drive slots racked down its left '
        'face with a light on each blinking its own way (green, gold, teal, red), vents down its right face.',
        'Place it by pixel (px) at the strip\'s anchor.',
        f'States: run ({SERVER_FRAMES} frames of 200 ms, looping).'], 'run', 200))
    ship = ship_frames()
    save('dev-ship', one_state(ship, [
        'The ship moment: both screens gone green with a cream check mark, and a rocket (a cream rounded prism, '
        'a red nose and fins, a flickering flame) launching from behind the laptop up out of the strip.',
        'The page shows it for 1.5 s on a tap, over everything.',
        f'States: ship ({SHIP} frames of 100 ms, looping; the page takes it away after one).'], 'ship', 100))

    layer = lambda name, notes, items: save_scene(name, scene(notes, items, name + '.svg'))
    layer('dev-back', ['The desk\'s back layer: the mug and the server tower.'],
          [item('dev-mug', state='run'), item('dev-server', state='run', order=1)])
    layer('dev-laptop', ['The laptop.'], [item('dev-laptop')])
    layer('dev-code', ['The laptop\'s screen, typing.'], [item('dev-code', state='type')])
    layer('dev-terminal', ['The terminal window.'], [item('dev-terminal')])
    layer('dev-term', ['The terminal\'s screen, running.'], [item('dev-term', state='run')])
    layer('dev-blocks', ['The three code blocks, bobbing.'],
          [item(f'dev-block-{g}', at, 'bob', i) for i, (g, _, at, _) in
           sorted(enumerate(BLOCKS), key=lambda e: (e[1][2][1], e[1][2][0]))])
    layer('dev-sparkles', ['Sparkles round the screen and the blocks.'],
          [item('brief-glint', (x, y), f'twinkle-{ph}', i) for i, (x, y, ph) in
           sorted(enumerate(SPARKLES), key=lambda e: (e[1][1], e[1][0]))])
    layer('dev-ship', ['The ship moment, shown on a tap.'], [item('dev-ship', state='ship')])
    return ['dev-back', 'dev-laptop', 'dev-code', 'dev-terminal', 'dev-term', 'dev-blocks', 'dev-sparkles']
