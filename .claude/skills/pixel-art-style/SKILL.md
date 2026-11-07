---
name: pixel-art-style
description: The house look of the Daily Brief's pixel art in art/ (isometric, drawn on Pixpocket's 2:1 grid by SLYNYRD's process), the limits Pixpocket puts on it, and the rules the owner's verdicts have set. Read before drawing or changing anything in art/daily-brief.pixpocket or art/generators/, so new art matches what's there.
---

# The Daily Brief's art style

The art in `art/` is Pixpocket art: isometric, nearest-neighbor, in one
palette. It follows the house style of J. Law's other pixel art (the
jlawcordova-vlog studio's Office library), distilled here as policy. The
owner's verdicts outrank anything below. When the owner reacts to how
something looks, turn the reaction into a rule in **Taste** before acting on
it, and change the rule when a later verdict overrides it.

Look at what's there before you draw:

```sh
cd art && pixpocket render scene:brief-coffee --scale 4 --out /tmp/coffee.png
```

## The grid

- 2:1 dimetric. A tile is 44×22 pixels and a level is 22 pixels high, so a
  one-tile block is SLYNYRD's 44×44 cube. Columns run toward the viewer's
  lower right, rows toward the lower left.
- Edges are 2:1 stair steps: two pixels across, one down. Long edges are 2:1
  lines or verticals, 1:1 lines sparingly, and no other slopes.
- Sizes and positions in whole units, even where you can: corners land on
  pixel corners and edges keep their rhythm.
- A flat circle fits a 2:1 diamond, `w` wide and `w/2` high, centred on a
  pixel corner with an even width (the kit's `ellipse`). A short round thing
  is a `puck`, at least 12 wide so it reads round.

## Limits Pixpocket enforces

- A sprite is at most 128×128 pixels in at most 16 colors. Anything wider is
  drawn whole and cut into halves on one anchor (`halves` in `draw.py`: the
  sky, the rays, the tables).
- The palette is the Pixpocket starter's: 64 world colors (thirteen 4-shade
  ramps, 1 = highlight … 4 = shadow, plus ink, cream and two skins) and an
  outfit tier for characters only. Add a color only with the owner's yes.
- Budget the 16 colors before drawing; over budget, merge the rarest shades
  (a ramp's 4 where its 3 will do, a neighbour's color).
- Frame times that give whole frames at 30 fps (100 or 200 ms), or
  `pixpocket check --fps 30` warns.

## The process: SLYNYRD's (Pixelblog 41), on the grid

1. **Draw on the grid, never in 3D.** Boxes, 2:1 lines and skewed circles,
   straight in pixels with `art/kit/kit.py`. No 3D models, ray casting or
   projection.
2. **Start from cubes and round forms, then sculpt.** Block a thing out in
   boxes, pucks and stacked ellipses, then paint the details that name it
   onto their faces.
3. **Light from the upper left.** A top is the lightest (ramp 1–2), the left
   face mid (2–3), the right face darkest (3–4). A round thing is lit down
   its left and shaded down its right.
4. **Solid faces, no outlines.** Shapes read by their shading. Each face is
   one color: no seams, black outlines or stray dots. Keep only the marks
   that name a thing (a table's plank seams, the pleats on a dumpling).
5. **Clean up.** No lone specks, no one-pixel nubs or notches, steps on a
   curve in order (1, 1, 2, 2, 3).
6. **Count jags with the 2:1 ruler.** `pixpocket check --ruler` counts them per
   frame and warns past 24; `pixpocket preview object:<name> --marks` shows
   where. **More cubic when it jags:** square off a part that steps raggedly.
7. **Rounder than boxy.** Round furniture's corners on the grid (a table top's
   `r=4`), but keep what's square square.

## Taste: the owner's rules so far

General (from the house style):
- Match what's there: borrow its proportions, shading and detail.
- Make what's meant to be fun bright: saturated ramps (teal, plum, gold,
  roof), not steel grey.
- Shape a thing as people know it.
- Glass you see through is clear; paint only what you look at.
- Give every object a working state where it has one, and keep idle loops
  small and calm.
- Check motion in a video as well as a still.

The Daily Brief's (from its reviews):
- **Food has no faces.** Foods are things to eat, not characters.
- **Serve each food the way it comes:** on a plate, in a bowl, in a takeout
  box, with its utensils where they fit (a cup on a saucer, dumplings in a
  bamboo steamer, pizza in its box).
- **The spot of the day is a "ta-da" shot:** the food under a sky of turning
  rays that glow near it, glints twinkling on it.
- **Only the light and what's hot move.** The rays turn; the table and the
  food stand still. Steam rises, coals glow, a candle flickers.
- **Food stands on a table suited to it, never a podium:** a samgyupsal grill
  table, a café's marble table, a fine-dining table in a white cloth, a cozy
  wooden table. A table's props sit at its sides, clear of every food
  (x beyond ±34), and its legs run out of the box at the bottom.
- **Everything mixes and matches.** The light, the table and the food are
  separate layers on one anchor and one box (176×110), so any food goes on
  any table under any color of rays. A new food, table or light must work
  with all the others.
- **The page plays SMIL, not CSS.** The artifact's asset store strips an
  SVG's `<style>` and `<animate>`, so the SVGs are converted
  (`art/generators/smil.py`) and given to the page as its own files.

## Look before you finish

```sh
python3 art/generators/build.py                       # builds, checks, rulers and publishes
cd art && pixpocket render scene:brief-<food> --scale 4 --out /tmp/look.png
pixpocket preview object:<name> --marks --scale 6 --out /tmp/marks.png
```

Check for stray pixels and jags, a silhouette that reads at 1×, faces shaded
the right way round, symmetric circles, and every frame inside the same box.
Then stack the layers in a browser (the page shows them as `<img>`s) and
watch them move before calling it done. Show the owner, and add their verdict
to **Taste**.
