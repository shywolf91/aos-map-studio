"""Print the short form of OUTDIR/validation.json: the kit summary table and the rework checks.

    python scenes/royal_parade_snow_night/rpsn_summary.py OUTDIR
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..'))
from aosmap.kit import babel_checks  # noqa: E402


def main(out):
    R = json.load(open(os.path.join(out, 'validation.json')))
    for row in R['summary']:
        print(babel_checks.format_row(row))
    w = R['rework']
    d = dict(w['diff'])
    d.pop('locations', None)
    print('diff', json.dumps(d))
    c = w['connectivity']
    print('connectivity ok', c['ok'], 'orig', c['original_floating'], 'now', c['now_floating'], 'new', c['new_floating'][:5])
    for t, e in w['exposure_before_after'].items():
        if t != 'model':
            print('exposure', t, 'before', e['before'], 'after', e['after'])
    for t, e in w['front_lanes'].items():
        print('front lanes', t, e)
    print('clear width', json.dumps(w['clear_width']))
    print('colour', json.dumps(w['colour']))
    print('colour original', json.dumps(w['colour_original']))
    print('txt', w['txt'])
    if 'glow_palette_collisions' in w:
        print('glow palette collisions', w['glow_palette_collisions'])


if __name__ == '__main__':
    main(sys.argv[1])
