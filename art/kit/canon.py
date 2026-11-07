"""Pixpocket's canonical JSON text (a port of crates/engine/src/format.rs)."""
import json, re

SPRITE = ["notes", "category", "kind", "extends", "anchor", "footprint", "keys", "rows", "layers", "start", "states"]
FIGURE = ["notes", "category", "kind", "extends", "footprint", "handle", "parts", "holds", "poses", "start", "states"]
PART = ["id", "box", "at", "with", "order", "faces", "drawing", "drawings", "sockets", "looks"]
FIGURE_STATE = ["poses", "ms", "loop", "then", "heading", "move"]
HOLD = ["object", "look", "turn"]
BLOCK = ["notes", "category", "kind", "size", "faces", "surface", "sides"]
LAYER = ["keys", "class", "loop", "prefix", "frames", "map", "ambient", "actions"]
SIDES = ["keys", "left", "right"]
SCENE = ["notes", "output", "image", "viewBox", "margin", "origin", "layers", "items", "motion", "entrance"]
SCENE_LAYER = ["id", "name", "parent"]
ITEM = ["object", "id", "class", "layer", "depth", "state", "at", "heading", "holds", "order", "ambient", "actions"]
GROUP = ["group", "depth", "items"]
AT = ["tile", "px", "level", "on", "units"]
MOTION = ["duration", "tracks"]
TRACK = ["item", "walk", "keys"]
WALK = ["start", "corners", "closed", "state", "stride", "then"]
KEY = ["t", "move", "show", "pose", "state", "heading", "hold"]
STATE = ["frames", "ms", "loop", "then", "move"]
MOVE_KEY = ["t", "move"]
LOOP = ["duration", "offset", "keys"]
IMAGE = ["file", "scale"]
ACTIONS = ["\0actions"]

def is_index(k):
    return k == '0' or (re.fullmatch(r'[1-9][0-9]{0,9}', k) is not None and int(k) < 4294967295)

def jkeys(m):
    idx = sorted((int(k), k) for k in m if is_index(k))
    return [k for _, k in idx] + [k for k in m if not is_index(k)]

def table_keys(m, table):
    return [k for k in table if k in m] + [k for k in jkeys(m) if k not in table]

def scalar(v):
    if v is True: return 'true'
    if v is False: return 'false'
    if v is None: return 'null'
    if isinstance(v, float) and v.is_integer(): return str(int(v))
    if isinstance(v, (int, float)): return json.dumps(v)
    return json.dumps(v, ensure_ascii=False)

def pad(d): return '  ' * d

def inline(v, table=None):
    if isinstance(v, list):
        return '[' + ', '.join(inline(e, table) for e in v) + ']'
    if isinstance(v, dict):
        if not v: return '{}'
        names = table_keys(v, table) if table and table != ACTIONS else jkeys(v)
        parts = []
        for k in names:
            val = v[k]
            if table == AT and k == 'level' and val == 0: continue
            inner = None
            if table == ITEM and k == 'at': inner = AT
            elif table == ITEM and k == 'ambient': inner = LOOP
            elif table == ITEM and k == 'actions': inner = ACTIONS
            elif table == ACTIONS: inner = LOOP
            elif table == LOOP and k == 'keys': inner = KEY
            elif table == STATE and k == 'move': inner = MOVE_KEY
            parts.append(json.dumps(k) + ': ' + inline(val, inner))
        return '{ ' + ', '.join(parts) + ' }'
    return scalar(v)

# shapes: ('pretty',), ('inline',), ('irec', table), ('rec', table, bykey), ('list', each)
P = ('pretty',)
def write(v, shape, d):
    kind = shape[0]
    if kind == 'inline': return inline(v)
    if kind == 'irec': return inline(v, shape[1])
    if kind == 'rec' and isinstance(v, dict): return record(v, shape[1], shape[2], d)
    if kind == 'list' and isinstance(v, list):
        if not v: return '[]'
        return '[\n' + ',\n'.join(pad(d + 1) + write(e, shape[1](e), d + 1) for e in v) + '\n' + pad(d) + ']'
    if isinstance(v, list) and v and all(isinstance(e, (int, float)) and not isinstance(e, bool) for e in v):
        return inline(v)
    if isinstance(v, list) and v:
        return '[\n' + ',\n'.join(pad(d + 1) + write(e, P, d + 1) for e in v) + '\n' + pad(d) + ']'
    if isinstance(v, dict): return record(v, [], lambda k: P, d)
    if isinstance(v, list): return '[]'
    return scalar(v)

def record(m, table, bykey, d):
    if not m: return '{}'
    return '{\n' + ',\n'.join(pad(d + 1) + json.dumps(k, ensure_ascii=False) + ': ' + write(m[k], bykey(k), d + 1) for k in table_keys(m, table)) + '\n' + pad(d) + '}'

def loop_key(k): return ('list', lambda e: ('irec', KEY)) if k == 'keys' else P
def layer_key(k):
    if k == 'ambient': return ('rec', LOOP, loop_key)
    if k == 'actions': return ('rec', [], lambda k2: ('rec', LOOP, loop_key))
    return P
def object_key(k):
    if k == 'layers': return ('list', lambda e: ('rec', LAYER, layer_key))
    if k == 'surface': return ('rec', LAYER, layer_key)
    if k == 'sides': return ('rec', SIDES, lambda k: P)
    if k == 'states': return ('rec', [], lambda k: ('irec', STATE))
    return P
def item_shape(v): return ('rec', GROUP, group_key) if isinstance(v, dict) and 'group' in v else ('irec', ITEM)
def group_key(k):
    if k == 'group': return ('inline',)
    if k == 'items': return ('list', item_shape)
    return P
def track_key(k):
    if k == 'keys': return ('list', lambda e: ('irec', KEY))
    if k == 'walk': return ('irec', WALK)
    return P
def motion_key(k): return ('list', lambda e: ('rec', TRACK, track_key)) if k == 'tracks' else P
def scene_key(k):
    if k == 'layers': return ('list', lambda e: ('irec', SCENE_LAYER))
    if k == 'items': return ('list', item_shape)
    if k == 'motion': return ('rec', MOTION, motion_key)
    if k == 'image': return ('irec', IMAGE)
    if k == 'entrance': return ('rec', [], lambda k: P)
    return P

def figure_key(k):
    """A figure's keys: one line per part, pose, hold and state."""
    if k == 'parts': return ('list', lambda e: ('irec', PART))
    if k == 'poses': return ('rec', [], lambda k: ('inline',))
    if k == 'holds': return ('rec', [], lambda k: ('irec', HOLD))
    if k == 'states': return ('rec', [], lambda k: ('irec', FIGURE_STATE))
    return P
def figure_changes_key(k):
    """A figure that extends another gives its parts as changes by id."""
    return ('rec', [], lambda k: ('irec', PART)) if k == 'parts' else figure_key(k)

def serialize(doc):
    if doc.get('kind') == 'sprite' and any(k in doc for k in ('parts', 'handle', 'holds', 'poses')):
        return write(doc, ('rec', FIGURE, figure_changes_key if isinstance(doc.get('parts'), dict) else figure_key), 0) + '\n'
    if 'kind' in doc and doc['kind'] in ('sprite', 'block'):
        return write(doc, ('rec', BLOCK if doc['kind'] == 'block' else SPRITE, object_key), 0) + '\n'
    if 'items' in doc:
        return write(doc, ('rec', SCENE, scene_key), 0) + '\n'
    return write(doc, P, 0) + '\n'

if __name__ == '__main__':
    import sys, glob
    bad = 0
    for f in sys.argv[1:]:
        t = open(f).read()
        if serialize(json.loads(t)) != t: bad += 1; print('differs', f)
    print('checked', len(sys.argv) - 1, 'bad', bad)
