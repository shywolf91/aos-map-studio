"""Build, colour, tag, export Silverpine Hunt.

python sph_main.py OUTDIR            (v1.0)
python sph_main.py OUTDIR --sky      (v1.1: + the optional floating sky layer: moon, bats, crows)
python sph_main.py OUTDIR --graybox  (terrain only)
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

import numpy as np

from sph_build import FILE, NAME, VERSION, build
from sph_color import colorize, ground_stats
from sph_core import pack_rgb, write_vxl
import sph_props as P

FONT = {   # 5 x 7, rows top->bottom
    'S': ['.####', '#....', '#....', '.###.', '....#', '....#', '####.'],
    'I': ['#####', '..#..', '..#..', '..#..', '..#..', '..#..', '#####'],
    'L': ['#....', '#....', '#....', '#....', '#....', '#....', '#####'],
    'V': ['#...#', '#...#', '#...#', '#...#', '.#.#.', '.#.#.', '..#..'],
    'E': ['#####', '#....', '#....', '####.', '#....', '#....', '#####'],
    'R': ['####.', '#...#', '#...#', '####.', '#.#..', '#..#.', '#...#'],
    'P': ['####.', '#...#', '#...#', '####.', '#....', '#....', '#....'],
    'N': ['#...#', '##..#', '#.#.#', '#..##', '#...#', '#...#', '#...#'],
    'H': ['#...#', '#...#', '#...#', '#####', '#...#', '#...#', '#...#'],
    'U': ['#...#', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'],
    'T': ['#####', '..#..', '..#..', '..#..', '..#..', '..#..', '..#..'],
    ' ': ['.....'] * 7,
}

FOG = (170, 160, 190)
HEAVENS = (96, 102, 156, 255)
MAP_TXT = '''name = 'Silverpine Hunt'
version = '{VERSION}'
author = 'shywolf91 + AI'
description = ('Babel: a moonlit werewolf snow forest. Hunters lodges at both spawns, the werewolf den under '
               'the platform, a frozen waterfall to the north and a silver mine to the south.')
fog = {FOG}
extensions = {{
    'babel': True,
    'water_damage': 0,
    'heavens_color': {HEAVENS},
}}
'''


def paint_tag(m, color, text, x0, y0):
    """Flatten a rock shelf in the SW corner and paint the name on it (map name only)."""
    w = 6 * len(text) + 2
    rect = (x0 - 2, x0 + w, y0 - 2, y0 + 9)
    sub = m[rect[0]:rect[1] + 1, rect[2]:rect[3] + 1] > 0
    zt = int(np.min(np.argmax(sub, axis=2)))
    for x in range(rect[0], rect[1] + 1):
        for y in range(rect[2], rect[3] + 1):
            m[x, y, :zt] = 0
            m[x, y, zt:63] = np.where(m[x, y, zt:63] == 0, P.ROCK, m[x, y, zt:63])
            m[x, y, zt] = P.ROCK_DK
    x = x0
    cells = []
    for ch in text:
        for r, row in enumerate(FONT[ch]):
            for c, v in enumerate(row):
                if v == '#':
                    cells.append((x + c, y0 + r))
        x += 6
    return rect, zt, cells


def main(out, graybox=False, sky=False):
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    V, F = build(graybox=graybox, sky=sky)
    m = V.m
    rect = zt = cells = None
    if not graybox:
        rect, zt, cells = paint_tag(m, None, 'SILVERPINE HUNT', 10, 494)
    solid = m > 0
    solid[:, :, 63] = True
    m[:, :, 63] = np.where(m[:, :, 63] == 0, P.ROCK, m[:, :, 63])
    color, cinfo = colorize(m, getattr(V, 'cover', None))
    if cells:
        for (cx, cy) in cells:
            color[cx, cy, zt] = pack_rgb(np.array((176, 184, 204), float))
    stats = ground_stats(m, color)
    data = write_vxl(solid, color)
    path = os.path.join(out, FILE + '.vxl')
    with open(path, 'wb') as f:
        f.write(data)
    np.save(os.path.join(out, 'mat.npy'), m)
    with open(os.path.join(out, FILE + '.txt'), 'w', newline='\n') as f:
        f.write(MAP_TXT.format(VERSION=(VERSION + '-sky') if sky else VERSION, FOG=FOG, HEAVENS=HEAVENS))
    info = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data), 'build_s': round(time.time() - t0, 1),
            'tag_rect': rect, 'cosmetic_asymmetric_bbox': list(rect) if rect else None,
            'cleanup': F.get('cleanup'), 'counts': F.get('counts'), 'tree_types_total': F.get('tree_types'),
            'sky_objects': F.get('sky_objects'), 'ground_stats': stats, **cinfo}
    with open(os.path.join(out, 'build.json'), 'w') as f:
        json.dump(info, f, indent=1, default=int)
    print(json.dumps(info, default=int))
    return solid, color, m, F


if __name__ == '__main__':
    main(sys.argv[1], graybox='--graybox' in sys.argv, sky='--sky' in sys.argv)
