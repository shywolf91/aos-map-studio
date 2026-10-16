"""Build, colour, tag, export and preview The Wicker King's Harvest.

python wkh_main.py OUTDIR            (art build)
python wkh_main.py OUTDIR --graybox  (terrain only, function colours)
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

import numpy as np

from wkh_build import FILE, NAME, VERSION, build
from wkh_color import colorize, team_recolor
from wkh_core import pack_rgb, write_vxl
import wkh_props as P

FONT = {   # 5 x 7, rows top->bottom
    'T': ['#####', '..#..', '..#..', '..#..', '..#..', '..#..', '..#..'],
    'H': ['#...#', '#...#', '#...#', '#####', '#...#', '#...#', '#...#'],
    'E': ['#####', '#....', '#....', '####.', '#....', '#....', '#####'],
    'W': ['#...#', '#...#', '#...#', '#.#.#', '#.#.#', '##.##', '#...#'],
    'I': ['#####', '..#..', '..#..', '..#..', '..#..', '..#..', '#####'],
    'C': ['.####', '#....', '#....', '#....', '#....', '#....', '.####'],
    'K': ['#...#', '#..#.', '#.#..', '##...', '#.#..', '#..#.', '#...#'],
    'R': ['####.', '#...#', '#...#', '####.', '#.#..', '#..#.', '#...#'],
    'S': ['.####', '#....', '#....', '.###.', '....#', '....#', '####.'],
    'A': ['.###.', '#...#', '#...#', '#####', '#...#', '#...#', '#...#'],
    'V': ['#...#', '#...#', '#...#', '#...#', '.#.#.', '.#.#.', '..#..'],
    'N': ['#...#', '##..#', '#.#.#', '#..##', '#...#', '#...#', '#...#'],
    'G': ['.####', '#....', '#....', '#.###', '#...#', '#...#', '.###.'],
    "'": ['..#..', '..#..', '.#...', '.....', '.....', '.....', '.....'],
    ' ': ['.....'] * 7,
}


def paint_tag(color, m, text, x0, y0, scale=2, rgb=(214, 190, 150)):
    """Paint the map name onto the sea floor (z = 63) in the SW corner. Returns the tag rectangle."""
    x = x0
    cells = []
    for ch in text:
        g = FONT[ch]
        for r, row in enumerate(g):
            for c, v in enumerate(row):
                if v == '#':
                    for dx in range(scale):
                        for dy in range(scale):
                            cells.append((x + c * scale + dx, y0 + r * scale + dy))
        x += 6 * scale if ch != "'" else 4 * scale
    x1 = x
    for (cx, cy) in cells:
        assert m[cx, cy, 62] == 0, 'tag must sit on open sea floor'
        color[cx, cy, 63] = pack_rgb(np.array(rgb, float))
    return (x0, x1, y0, y0 + 7 * scale)


FOG = (176, 160, 186)
MAP_TXT = '''name = "{NAME}"
version = '{VERSION}'
author = 'aosmap'
description = ('Tower of Babel on a carved jack-o-lantern island. Build from the ritual clearing up to the '
               'sky platform; the Wicker King watches from the north.')
fog = {FOG}
extensions = {{
    'babel': True,
    'water_damage': 0,
}}
'''

GRAY = {P.SKIN: (200, 110, 50), P.ROCK: (80, 80, 84), P.SHORE_ROCK: (100, 100, 104), P.PIT_ROCK: (50, 50, 56),
        P.SOIL: (150, 140, 110), P.DIRT: (120, 110, 90), P.ASH: (60, 60, 66), P.SEA: (30, 50, 80),
        P.STAIR: (240, 220, 60), P.PATH: (190, 170, 130), P.CLEARING: (170, 150, 120)}


def main(out, graybox=False, sky=False):
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    V, F, piers = build(graybox=graybox, sky=sky)
    m = V.m
    if graybox:
        m[257:] = m[255:0:-1]
        color = np.zeros(m.shape, np.uint32)
        for k in np.unique(m):
            if k == 0:
                continue
            color[m == k] = pack_rgb(np.array(GRAY.get(int(k), (200, 60, 200)), float))
    else:
        color = colorize(m, F)
        color = team_recolor(m, color)
    tag = None
    if not graybox:
        tag = paint_tag(color, m, "THE WICKER KING'S HARVEST", 10, 494, scale=1)
    solid = m > 0
    solid[:, :, 63] = True
    data = write_vxl(solid, color)
    path = os.path.join(out, FILE + '.vxl')
    with open(path, 'wb') as f:
        f.write(data)
    np.save(os.path.join(out, 'mat.npy'), m)
    with open(os.path.join(out, FILE + '.txt'), 'w', newline='\n') as f:
        # v1.1 = v1 + the optional floating sky layer (crows, bats, moon)
        f.write(MAP_TXT.format(NAME=NAME, VERSION='1.1' if sky else VERSION, FOG=FOG))
    info = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data), 'build_s': round(time.time() - t0, 1),
            'tag_rect': tag, 'cleanup': F.get('cleanup'), 'cosmetic_asymmetric_bbox': F.get('cosmetic_bbox'),
            'scatter_props': F.get('scatter_count'), 'sky_objects': F.get('sky_objects'),
            'piers': [{k: (round(v, 2) if isinstance(v, float) else v) for k, v in p.items() if k != 'u'}
                      for p in piers]}
    with open(os.path.join(out, 'build.json'), 'w') as f:
        json.dump(info, f, indent=1)
    print(json.dumps(info))
    return solid, color, m, F


if __name__ == '__main__':
    main(sys.argv[1], graybox='--graybox' in sys.argv, sky='--sky' in sys.argv)
