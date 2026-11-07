"""The drawing kit: SLYNYRD's isometric process, drawn straight onto Pixpocket's
2:1 grid in pixels, the way he draws by hand. Nothing is modelled in 3D
or projected: a shape is cubes on 2-step lines first (`box`), then details
painted onto its faces, then circles from the skewed square (`ellipse`,
`cylinder`). See the `art-generators` skill.

Coordinates are pixels, with the anchor at (0, 0): the pixel just below and
right of the anchor tile's top-face centre. A tile's top is the pixels whose
centres have 0 < u < 22 and 0 < v < 22 from its back corner (0, -11), where
u = Y + X/2 runs down the columns (to the lower right) and v = Y - X/2 down
the rows (to the lower left). One unit of u or v is one pixel across, so a
tile is 22 units each way, 44×22 pixels, and a level is 22 pixels high.
"""
import math

TILE_W, TILE_H, LEVEL_H = 44, 22, 22
T = TILE_H  # a tile in units, along a column or a row
CAPS = {'size': 128, 'colors': 16}


class Pic(dict):
    """A drawing: (x, y) -> palette color name. Later puts win, so draw back to front."""

    def put(self, x, y, c):
        if c is not None:
            self[(x, y)] = c

    def copy(self):
        return Pic(self)

    def moved(self, dx, dy):
        return Pic({(x + dx, y + dy): c for (x, y), c in self.items()})

    def mirrored(self, axis2):
        """Mirror about x = axis2 / 2 (axis2 = 2·axis, so a pixel-corner axis is even)."""
        return Pic({(axis2 - 1 - x, y): c for (x, y), c in self.items()})

    def over(self, other):
        """This drawing with `other` painted on top."""
        out = Pic(self)
        out.update(other)
        return out

    def recolor(self, table):
        return Pic({p: table.get(c, c) for p, c in self.items()})

    def erase(self, pts):
        for p in pts:
            self.pop(p, None)


def uv(x, y, bx, by):
    """A pixel's centre in units (u down the columns, v down the rows) from the corner (bx, by)."""
    X, Y = x + 0.5 - bx, y + 0.5 - by
    return Y + X / 2, Y - X / 2


def paint(c, *args):
    """A color, or a function of the face's coordinates."""
    return c(*args) if callable(c) else c


def rounded(u, v, a, b, r):
    """Whether (u, v) is inside an a×b rectangle whose corners are rounded to
    radius r (circles in the rectangle's own units). r may be four radii, one
    per corner: (u0 v0, u1 v0, u1 v1, u0 v1), the back corner first."""
    if not (0 < u < a and 0 < v < b):
        return False
    if isinstance(r, tuple):
        r = r[{(0, 0): 0, (1, 0): 1, (1, 1): 2, (0, 1): 3}[(int(u > a / 2), int(v > b / 2))]]
    if r <= 0:
        return True
    cu, cv = min(max(u, r), a - r), min(max(v, r), b - r)
    return (u - cu) ** 2 + (v - cv) ** 2 < r * r


def top(p, bx, by, a, b, color, r=0):
    """A flat parallelogram on the ground plane: a units down the columns, b
    down the rows, its back corner at the pixel corner (bx, by), its corners
    rounded to r units if r is given. Returns its pixels with their (u, v).
    `color` may be fn(u, v)."""
    out = {}
    for x in range(bx - b - 1, bx + a + 2):
        for y in range(by - 1, by + (a + b) // 2 + 2):
            u, v = uv(x, y, bx, by)
            if rounded(u, v, a, b, r):
                out[(x, y)] = (u, v)
                p.put(x, y, paint(color, u, v))
    return out


def box(p, bx, by, a, b, h, top_c, left_c, right_c, r=0):
    """SLYNYRD's D1 cube, as Pixpocket draws a block: a top of a×b units with
    its back corner at (bx, by), and sides h pixels high hanging flush under
    the top's columns. The left face (toward the lower left) is under
    x < bx + a - b, the right face from there on. Colors may be functions:
    top(u, v), left(s, t) and right(s, t), where s counts pixels across the
    face from its left edge and t rows down from its top edge. With r, the
    top's corners are rounded to r units (a cushion), its sides still hanging
    under it."""
    tp = top(p, bx, by, a, b, top_c, r)
    bottom = {}
    for (x, y) in tp:
        bottom[x] = max(bottom.get(x, y), y)
    split = bx + a - b
    xl = bx - b
    for x, yb in sorted(bottom.items()):
        for t in range(h):
            if x < split:
                p.put(x, yb + 1 + t, paint(left_c, x - xl, t))
            else:
                p.put(x, yb + 1 + t, paint(right_c, x - split, t))
    return tp


def ramp_box(p, bx, by, a, b, h, ramp, lit=(0, 1, 2)):
    """A box in one material: the ramp's shades for top, left and right."""
    return box(p, bx, by, a, b, h, ramp[lit[0]], ramp[lit[1]], ramp[lit[2]])


def tile_corner(col=0, row=0, level=0):
    """The back corner of tile [col, row, level]'s top, from the anchor tile's."""
    return (col - row) * T, (col + row) * (T // 2) - T // 2 - level * LEVEL_H


def stand(level_px):
    """The y of a box's back corner whose top stands `level_px` pixels above the tile's."""
    return -T // 2 - level_px


def line(p, x0, y0, x1, y1, c):
    """A straight line, pixel centres nearest it (for 2:1, 1:1 and 1:2 lines,
    which come out as clean stairs when the ends are on the grid)."""
    dx, dy = x1 - x0, y1 - y0
    n = max(abs(dx), abs(dy))
    if n == 0:
        p.put(x0, y0, c)
        return
    if abs(dx) >= abs(dy):
        step = 1 if dx > 0 else -1
        for i in range(abs(dx) + 1):
            x = x0 + i * step
            y = y0 + dy * i / abs(dx)
            p.put(x, math.floor(y + 0.5 - 1e-9 * (1 if dy > 0 else -1)), c)
    else:
        step = 1 if dy > 0 else -1
        for i in range(abs(dy) + 1):
            y = y0 + i * step
            x = x0 + dx * i / abs(dy)
            p.put(math.floor(x + 0.5), y, c)


def run21(p, x, y, n, dx, c, dy=1):
    """A 2-step line from (x, y): n pixels, two across (dx = ±1) for each one
    down (dy = 1) or up (dy = -1)."""
    for i in range(n):
        p.put(x + i * dx, y + (i // 2) * dy, c)


def ellipse(p, cx, cy, w, color, h=None):
    """A circle on the ground plane, in its skewed square: w pixels wide (even)
    and w/2 high, centred on the pixel corner (cx, cy). Returns its pixels.
    `color` may be fn(x, y) in pixels from the centre."""
    h = h or w // 2
    a, b = w / 2, h / 2
    out = []
    for y in range(cy - (h + 1) // 2 - 1, cy + (h + 1) // 2 + 1):
        Y = y + 0.5 - cy
        if abs(Y) >= b:
            continue
        half = a * math.sqrt(1 - (Y / b) ** 2)
        k = int(half + 0.5)  # whole pixels each side, symmetric
        for x in range(cx - k, cx + k):
            out.append((x, y))
            p.put(x, y, paint(color, x + 0.5 - cx, Y))
    return out


def cylinder(p, cx, cy, w, h, top_c, side):
    """An upright cylinder: its top an ellipse w wide centred on (cx, cy), its
    side h pixels down. `side` is a list of colors from the lit left edge to
    the dark right edge, spread across the width."""
    cols = {}
    for (x, y) in ellipse(Pic(), cx, cy, w, None):
        cols[x] = max(cols.get(x, y), y)
    n = len(side)
    for x, yb in cols.items():
        f = (x + 0.5 - (cx - w / 2)) / w
        c = side[min(n - 1, int(f * n))]
        for y in range(yb - (w // 4), yb + h + 1):
            p.put(x, y, c)
    ellipse(p, cx, cy, w, top_c)
    return cols


def puck(p, cx, cy, w, h, top_c, side):
    """A short upright cylinder (a seat, a disc): its top an ellipse w wide
    centred on (cx, cy), and h more of it stacked under, shaded across the
    width by `side` (lit left to dark right). Unlike `cylinder`, whose side
    columns poke up at the ends of a short one, its outline stays round."""
    n = len(side)
    for dy in range(h, 0, -1):
        ellipse(p, cx, cy + dy, w, lambda x, y: side[min(n - 1, int((x + w / 2) / w * n))])
    return ellipse(p, cx, cy, w, top_c)


def face_left(p, x0, y0, w, h, color):
    """A rectangle on a left-facing plane (running along the rows): its top-left
    pixel (x0, y0), w pixels across and h down; each column one pixel across
    drops half a pixel, two pixels for one row. `color` may be fn(s, t)."""
    for s in range(w):
        for t in range(h):
            p.put(x0 + s, y0 + t + s // 2, paint(color, s, t))


def face_right(p, x0, y0, w, h, color):
    """As face_left, on a right-facing plane (running along the columns): each
    column one pixel across climbs half a pixel. (x0, y0) is the top-left
    pixel, the face's highest corner on its right."""
    for s in range(w):
        for t in range(h):
            p.put(x0 + s, y0 + t - s // 2, paint(color, s, t))


def disc_side(p, cx, cy, d, color, face='left'):
    """A circle on a side plane (a wheel, a clock face): d pixels wide, in a
    square skewed 2:1 with vertical sides, centred on the pixel corner (cx, cy)."""
    r = d / 2
    sgn = -1 if face == 'left' else 1
    out = []
    for x in range(cx - d // 2, cx + d // 2):
        s = x + 0.5 - cx
        for y in range(cy - d, cy + d):
            t = y + 0.5 - cy - sgn * s / 2
            if s * s + t * t < r * r:
                out.append((x, y))
                p.put(x, y, paint(color, s, t))
    return out


# ------------------------------------------------------------------ clean-up

def specks(p):
    """Lone pixels whose four neighbours are all one other color: SLYNYRD's
    clean-up after the transform. Returns them; `despeck` paints them over."""
    out = []
    for (x, y), c in p.items():
        n = [p.get(q) for q in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))]
        if None not in n and len(set(n)) == 1 and n[0] != c:
            out.append(((x, y), n[0]))
    return out


def despeck(p, keep=()):
    for q, c in specks(p):
        if p[q] not in keep:
            p[q] = c
    return p


# ------------------------------------------------------------------ packing

KEYS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'


def bounds(frames):
    pts = [q for f in frames for q in f]
    xs, ys = [x for x, _ in pts], [y for _, y in pts]
    return min(xs), min(ys), max(xs), max(ys)


def pack(frames, keys=None):
    """Frames sharing one box: (anchor, keys, maps). Keys are given per color
    in first-use order unless `keys` (color -> key) is passed."""
    x0, y0, x1, y1 = bounds(frames)
    w, h = x1 - x0 + 1, y1 - y0 + 1
    if w > CAPS['size'] or h > CAPS['size']:
        raise SystemExit(f'{w}×{h} is over the {CAPS["size"]}×{CAPS["size"]} cap')
    table = dict(keys or {})
    maps = []
    for f in frames:
        rows = []
        for y in range(y0, y1 + 1):
            row = ''
            for x in range(x0, x1 + 1):
                c = f.get((x, y))
                if c is None:
                    row += '.'
                    continue
                if c not in table:
                    table[c] = next(k for k in KEYS if k not in table.values())
                row += table[c]
            rows.append(row)
        maps.append(rows)
    used = {c for f in frames for c in f.values()}
    if len(used) > CAPS['colors']:
        raise SystemExit(f'{len(used)} colors, over the {CAPS["colors"]} cap: {sorted(used)}')
    return [-x0, -y0], {k: c for c, k in table.items() if c in used}, maps


def sprite(frames, category, notes, footprint=None, states=None, start=None, loop='pose', prefix='p'):
    """A sprite object: one still map, or a frame loop with states."""
    if isinstance(frames, Pic):
        frames = [frames]
    anchor, keys, maps = pack(frames)
    o = {'notes': notes, 'category': category, 'kind': 'sprite', 'anchor': anchor}
    if footprint and list(footprint) != [1, 1]:
        o['footprint'] = list(footprint)
    o['keys'] = keys
    if len(maps) == 1 and not states:
        o['layers'] = [{'map': maps[0]}]
    else:
        o['layers'] = [{'loop': loop, 'prefix': prefix, 'frames': maps}]
    if states:
        o['start'] = start or next(iter(states))
        o['states'] = states
    return o


def extend(base, keys, category, notes):
    """A recolor: a sprite that extends `base` with new colors for some keys."""
    return {'notes': notes, 'category': category, 'kind': 'sprite', 'extends': base, 'keys': keys}


def surface_map(fn):
    """A block's surface: one tile, 44×22, fn(u, v) per pixel of the tile's
    top (u, v in units from its back corner). The top is Pixpocket's tile,
    4-pixel points and a pixel wider than the lattice along each edge, where
    neighbours overlap; there u or v runs a little past 0 or 22, so fn must
    loop (take u and v modulo the period) for the overlap to match its
    neighbour. Returns {keys, map}."""
    table, rows = {}, []
    for r in range(TILE_H):
        row = ''
        for col in range(TILE_W):
            x, y = col - TILE_W // 2, r - TILE_H // 2
            u, v = uv(x, y, 0, -T // 2)
            if not abs(x + 0.5) < TILE_W / 2 + 1 - 2 * abs(y + 0.5):
                row += '.'
                continue
            c = fn(u, v)
            if c not in table:
                table[c] = KEYS[len(table)]
            row += table[c]
        rows.append(row)
    return {'keys': {k: c for c, k in table.items()}, 'map': rows}


def sides_map(left, right):
    """A block's side textures: one tile's face by one level, 22×22 each,
    left(s, t) and right(s, t) per pixel. They repeat along a wider face and
    down a taller one, so they must loop."""
    table = {}
    out = {}
    for name, fn in (('left', left), ('right', right)):
        rows = []
        for t in range(LEVEL_H):
            row = ''
            for s in range(T):
                c = fn(s, t)
                if c not in table:
                    table[c] = KEYS[len(table)]
                row += table[c]
            rows.append(row)
        out[name] = rows
    return {'keys': {k: c for c, k in table.items()}, **out}


def block(category, notes, size, faces, surface=None, sides=None):
    o = {'notes': notes, 'category': category, 'kind': 'block', 'size': list(size), 'faces': faces}
    if surface:
        o['surface'] = surface
    if sides:
        o['sides'] = sides
    return o
