"""Build, colour, tag, export and preview-info for The Hollow Crown.

python hc_main.py OUTDIR [--graybox]
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

import numpy as np

from hc_build import FILE, NAME, SPEC, VERSION, build
from hc_core import write_vxl

FOG = (168, 164, 178)
MAP_TXT = '''name = '{NAME}'
version = '{VERSION}'
author = 'shywolf91'
description = ('Babel: a cursed medieval kingdom. Build your tower from the courtyard of the ruined Blackthorn '
               'Citadel up to the sky platform; graveyard to the north, Hollowshade Village to the south.')
fog = {FOG}
extensions = {{
    'babel': True,
    'water_damage': 0,
}}
'''


def main(out, graybox=False):
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    V, F, stats = build(graybox=graybox)
    from hc_color import colorize, team_recolor, paint_tag
    color = colorize(V.m, F, graybox=graybox)
    color = team_recolor(V.m, color)
    tag = None if graybox else paint_tag(V.m, color, SPEC['tag']['text'], SPEC['tag']['x'], SPEC['tag']['y'])
    solid = V.m > 0
    solid[:, :, 63] = True
    data = write_vxl(solid, color)
    with open(os.path.join(out, FILE + '.vxl'), 'wb') as f:
        f.write(data)
    np.save(os.path.join(out, 'mat.npy'), V.m)
    np.save(os.path.join(out, 'terrain_H.npy'), F['H_terrain'])
    with open(os.path.join(out, FILE + '.txt'), 'w', newline='\n') as f:
        f.write(MAP_TXT.format(NAME=NAME, VERSION=VERSION, FOG=FOG))
    info = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data), 'build_s': round(time.time() - t0, 1),
            'tag_rect': tag, **stats}
    with open(os.path.join(out, 'build.json'), 'w') as f:
        json.dump(info, f, indent=1)
    print(json.dumps(info))


if __name__ == '__main__':
    main(sys.argv[1], graybox='--graybox' in sys.argv)
