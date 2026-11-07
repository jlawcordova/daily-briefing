#!/usr/bin/env python3
"""Turns the frame loops of SVGs from `pixpocket publish` into SMIL, so they
play where a page's or an asset host's rules drop an SVG's <style> (as the
Daily Brief's asset store does: its SVGs, shown in an <img>, stood still with
every frame drawn at once).

    python3 art/generators/smil.py <in.svg|folder> [out folder]

Each frame group keeps the loop its scene starts it in: an `opacity` of 0
and an <animate> that shows it for its slice of the loop. The <style> goes."""
import os, re, sys


def keyframes(css):
    out = {}
    for name, body in re.findall(r'@keyframes\s+([\w-]+)\s*\{((?:[^{}]*\{[^{}]*\})*)[^{}]*\}', css):
        out[name] = [(float(p) / 100, float(o)) for p, o in re.findall(r'([\d.]+)%\s*\{\s*opacity:\s*([\d.]+)\s*\}', body)]
    return out


def convert(svg):
    m = re.search(r'<style>(.*?)</style>', svg, re.S)
    if not m:
        return svg
    css = m.group(1)
    kfs = keyframes(css)
    flat = re.sub(r'@keyframes[^{]*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}', '', css)
    hidden, plays = set(), {}
    for sel, body in re.findall(r'([^{}]+)\{([^{}]*)\}', flat):
        for one in sel.split(','):
            if 'data-state' in one:
                continue                          # another state's loop: the scene starts each in its own
            cls = re.findall(r'\.([\w-]+)', one)
            if not cls:
                continue
            c = cls[-1]
            if 'opacity:0' in body.replace(' ', ''):
                hidden.add(c)
            a = re.search(r'animation:\s*([\w-]+)\s+(\d+)ms', body)
            if a:
                plays[c] = (a.group(1), int(a.group(2)))

    def animate(c):
        name, ms = plays[c]
        stops = kfs[name]
        if stops[0][0] > 0:
            stops = [(0.0, 0.0)] + stops
        values = ';'.join(f'{o:g}' for _, o in stops)
        times = ';'.join(f'{t:.5f}'.rstrip('0').rstrip('.') or '0' for t, _ in stops)
        return (f'<animate attributeName="opacity" calcMode="discrete" values="{values}" keyTimes="{times}" '
                f'dur="{ms}ms" repeatCount="indefinite"/>')

    def group(g):
        c = g.group(1)
        if c not in hidden and c not in plays:
            return g.group(0)
        return f'<g class="{c}" opacity="0">' + (animate(c) if c in plays else '')

    body = svg[:m.start()] + svg[m.end():]
    return re.sub(r'<g class="([\w-]+)">', group, body)

if __name__ == '__main__':
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else None
    files = [os.path.join(src, f) for f in sorted(os.listdir(src)) if f.endswith('.svg')] if os.path.isdir(src) else [src]
    for f in files:
        out = convert(open(f).read())
        path = os.path.join(dst, os.path.basename(f)) if dst else f
        if dst:
            os.makedirs(dst, exist_ok=True)
        open(path, 'w').write(out)
        print(path, len(out))
