#!/usr/bin/env python3
"""Regenerates the Daily Brief library, the art of J. Law's Daily Brief page,
into art/daily-brief.pixpocket, then publishes the SVGs the page shows.

    python3 art/generators/build.py                (PIXPOCKET=<program> to pick another)
    python3 art/generators/build.py --no-publish

For the spot of the day: a sky of turning rays in six colors (`brief-light-<color>`), the tables a
food is served on (`brief-table-<table>`) and the foods with their glints
(`brief-food-<food>`). The page stacks the three, so any food goes on any
table under any light. `brief-<food>` scenes put each food on its usual table, to look at.

For the weather strip in the title band (`weather.py`): eleven kinds of day, by day and by night, each
a stack of `wx-<layer>` scenes on one 176×64 box (stars, sun or moon, rain, lightning, clouds, fog).

For the Birthdays section (`party.py`): a party on the 2:1 grid in `bday-<layer>` scenes on one 176×100
box (table, bunting, cake and gifts, balloons, sparkles, confetti), and `bday-icon-<name>` for the cards.

The SVGs: `pixpocket publish --dir art/build/svg`, then `smil.py` turns their
CSS frame loops into SMIL in art/build/smil, the files the page is given (an
artifact's asset store strips an SVG's <style>)."""
import glob, json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from draw import BUILD, OUT, SCENES_OUT, DOC, LIBRARY, save_scene  # noqa: E402
from canon import serialize  # noqa: E402
from program import run  # noqa: E402
import stage, foods, tables, smil, weather, party  # noqa: E402

# Where the glints twinkle on each food, in pixels from the table's anchor.
GLINTS = {
    'coffee': [(-9, -18), (8, -30), (16, -6)],
    'dumplings': [(-14, -22), (12, -24), (20, -8)],
    'noodle-soup': [(-18, -20), (14, -26), (22, -10)],
    'pasta': [(-12, -14), (8, -22), (20, -4)],
    'ice-cream': [(-10, -26), (6, -40), (14, -18)],
    'skewers': [(-14, -10), (10, -20), (22, -2)],
    'bread': [(-14, -14), (6, -22), (18, -2)],
    'cake': [(-16, -20), (10, -26), (20, -6)],
    'rice-bowl': [(-18, -20), (14, -26), (22, -10)],
    'burger': [(-12, -26), (10, -30), (20, -12)],
    'pizza': [(-16, -24), (14, -30), (20, -6)],
}

# The table each food is usually served on (the page may pick another).
TABLE = {
    'coffee': 'cafe', 'ice-cream': 'cafe', 'bread': 'cafe', 'cake': 'fine', 'pasta': 'fine',
    'skewers': 'grill', 'rice-bowl': 'grill', 'dumplings': 'wood', 'noodle-soup': 'wood',
    'burger': 'wood', 'pizza': 'wood',
}
AT = {'px': [0, 0]}


def light_items(light):
    return ([{'object': f'brief-sky-{light}-{s}', 'depth': 'back', 'order': 0, 'at': AT} for s in ('left', 'right')] +
            [{'object': f'brief-rays-{light}-{s}', 'depth': 'back', 'order': 1, 'at': AT} for s in ('left', 'right')])


def table_items(t):
    return [{'object': f'table-{t}-{s}', 'order': 0, 'at': AT} for s in ('left', 'right')]


def food_items(f):
    return ([{'object': 'food-' + f, 'order': 1, 'at': AT}] +
            [{'object': 'brief-glint', 'depth': 'front', 'state': f'twinkle-{i}', 'at': {'px': [x, y]}}
             for i, (x, y) in enumerate(GLINTS[f])])


def scene(notes, items, output=None):
    s = {'notes': notes}
    if output:
        s['output'] = output
    s['viewBox'] = list(stage.BOX)
    s['items'] = items
    return s


def scenes(food_names, table_names):
    for light in stage.LIGHTS:
        save_scene('brief-light-' + light, scene(
            [f'The spot of the day\'s {light} light, the page\'s bottom layer: the sky and its rays, turning, cream '
             'near the food.'], light_items(light), f'brief-light-{light}.svg'))
    for t in table_names:
        save_scene('brief-table-' + t, scene(
            [f'The {t} table alone, the page\'s middle layer, clear around it so the light shows.'],
            table_items(t), f'brief-table-{t}.svg'))
    lights = list(stage.LIGHTS)
    for i, f in enumerate(food_names):
        save_scene('brief-food-' + f, scene(
            [f'food-{f} and the glints that twinkle on it, alone: the page\'s top layer, over any table.'],
            food_items(f), f'brief-food-{f}.svg'))
        save_scene('brief-' + f, scene(
            [f'The spot of the day as the page shows it: food-{f} on the {TABLE[f]} table under '
             f'{lights[i % len(lights)]} rays. The table and the food stand still; the rays turn and glints twinkle.'],
            light_items(lights[i % len(lights)]) + table_items(TABLE[f]) + food_items(f)))


def install():
    made = {os.path.basename(f)[:-5]: json.load(open(f)) for f in sorted(glob.glob(os.path.join(OUT, '*.json')))}
    for f in glob.glob(os.path.join(DOC, 'objects', '*.json')):
        n = os.path.basename(f)[:-5]
        if n not in made and json.load(open(f)).get('category', [''])[0] == LIBRARY:
            os.remove(f)
    for n, o in made.items():
        with open(os.path.join(DOC, 'objects', n + '.json'), 'w') as f:
            f.write(serialize(o))
    new = {os.path.basename(s): s for s in glob.glob(os.path.join(SCENES_OUT, '*.json'))}
    for f in glob.glob(os.path.join(DOC, 'scenes', 'brief-*.json')) + glob.glob(os.path.join(DOC, 'scenes', 'wx-*.json')) + \
            glob.glob(os.path.join(DOC, 'scenes', 'bday-*.json')):
        if os.path.basename(f) not in new:
            os.remove(f)
    for n, f in sorted(new.items()):
        with open(os.path.join(DOC, 'scenes', n), 'w') as out:
            out.write(serialize(json.load(open(f))))
    return made, new


def build():
    shutil.rmtree(BUILD, ignore_errors=True)
    stage.build_stage()
    table_names = tables.build_tables()
    food_names = foods.build_foods()
    scenes(food_names, table_names)
    weather.build_weather()
    party.build_party()
    return install()


def publish():
    svg, out = os.path.join(BUILD, 'svg'), os.path.join(BUILD, 'smil')
    r = run(DOC, 'publish', '--dir', svg)
    if r.returncode:
        sys.exit(r.stderr or r.stdout)
    for f in sorted(glob.glob(os.path.join(svg, '*.svg'))):
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, os.path.basename(f)), 'w') as w:
            w.write(smil.convert(open(f).read()))
    return out


if __name__ == '__main__':
    made, new = build()
    print(f'install: {len(made)} objects, {len(new)} scenes')
    check = run(DOC, 'check', '--fps', '30')
    lines = check.stdout.strip().splitlines()
    print('check:', (lines or [check.stderr.strip()])[-1], *(['\n  ' + '\n  '.join(lines[:-1])] if len(lines) > 1 else []))
    if check.returncode:
        sys.exit(check.returncode)
    ruler = run(DOC, 'check', '--ruler', '--category', LIBRARY)
    print('ruler:', '\n       '.join(ruler.stdout.strip().splitlines()[:16]))
    if '--no-publish' not in sys.argv:
        print('published:', publish())
