"""Build, colour, tag and export Graveyard of the Forgotten.

python gf_main.py OUTDIR            (art build)
python gf_main.py OUTDIR --graybox  (terrain + function colours only)
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

import numpy as np

from gf_build import FILE, NAME, VERSION, build
from gf_color import colorize, paint_tag, team_recolor
from gf_core import pack_rgb, write_vxl
from gf_terrain import SEED, SPEC

FOG = (164, 170, 162)
MAP_TXT = '''name = "{NAME}"
version = '{VERSION}'
author = 'shywolf91'
description = ('Tower of Babel over a cursed graveyard. Build up from the courtyards beside the Bone '
               'Cathedral to the sky platform while two skeletal hands claw at the heavens.')
fog = {FOG}
extensions = {{
    'babel': True,
    'water_damage': 0,
}}
'''


def main(out, graybox=False):
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    V, F = build(graybox=graybox)
    m = V.m
    if graybox:
        color = np.zeros(m.shape, np.uint32)
        rng = np.random.default_rng(1)
        for k in np.unique(m):
            if k:
                color[m == k] = pack_rgb(rng.integers(60, 230, 3).astype(float))
        tag = None
    else:
        color = colorize(m)
        color = team_recolor(m, color)
        tx0, tx1, ty0, ty1 = SPEC['tag_rect']
        tag = paint_tag(color, m, NAME.upper(), tx0 + 8, ty0 + 4, F['tag_z'])
    solid = m > 0
    solid[:, :, 63] = True
    data = write_vxl(solid, color)
    with open(os.path.join(out, FILE + '.vxl'), 'wb') as f:
        f.write(data)
    np.save(os.path.join(out, 'mat.npy'), m)
    with open(os.path.join(out, FILE + '.txt'), 'w', newline='\n') as f:
        f.write(MAP_TXT.format(NAME=NAME, VERSION=VERSION, FOG=FOG))
    info = {'name': NAME, 'version': VERSION, 'seed': SEED, 'sha256': hashlib.sha256(data).hexdigest(),
            'bytes': len(data), 'build_s': round(time.time() - t0, 1), 'tag_rect': tag,
            'cleanup': F.get('cleanup'), 'cosmetic_bboxes': F.get('cosmetic_bboxes'),
            'graves_west_plots': F.get('graves_west'), 'trees_west': F.get('trees_west'), 'fog': FOG}
    with open(os.path.join(out, 'build.json'), 'w') as f:
        json.dump(info, f, indent=1)
    print(json.dumps(info))


if __name__ == '__main__':
    main(sys.argv[1], graybox='--graybox' in sys.argv)
