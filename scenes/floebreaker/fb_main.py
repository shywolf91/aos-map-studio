"""Build, colour, export Floebreaker (day + night).  python fb_main.py OUTDIR [--seed N] [--no-sky]"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np

import fb_build
import fb_sky
from fb_color import colorize
from fb_core import MAT
from fb_terrain import SPEC
from aosmap.vxl import write_vxl

FOG = {'day': (204, 184, 186), 'night': (172, 156, 206)}
HEAVENS = {'day': (158, 200, 238, 255), 'night': (46, 34, 104, 255)}
TXT = '''name = {name!r}
version = '1.0'
author = 'shywolf91 + AI'
description = {desc!r}
fog = {fog!r}
extensions = {{
    'babel': True,
    'boundary_damage': {bd!r},
    'heavens_color': {hv!r},
    'glow_enabled': True,
    'glow_stored_colors': {glow!r},
}}
'''


def build_variant(variant, decor_seed, out, sky=True):
    t0 = time.time()
    W = fb_build.build(decor_seed=decor_seed)
    if sky:
        fb_sky.build_sky(W, variant)
    vm, tag, glow = colorize(W, night=(variant == 'night'))
    data = write_vxl(vm, missing='error')
    fname = f"floebreaker_{variant}"
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, fname + '.vxl'), 'wb').write(data)
    gl = {(x, y, z): tuple(int(c) for c in (((vm.color[x, y, z] >> 16) & 255, (vm.color[x, y, z] >> 8) & 255,
                                                vm.color[x, y, z] & 255))) for (x, y, z) in glow}
    name = 'Floebreaker (Day)' if variant == 'day' else 'Floebreaker (Night)'
    desc = ('Babel: an arctic ice floe with a grounded icebreaker, research camps and a whale skeleton. Build your '
            'tower from the ice plain to the sky platform. Reimagined from Arctic Icebreaker (original author unknown).')
    open(os.path.join(out, fname + '.txt'), 'w', newline='\n').write(
        TXT.format(name=name, desc=desc, fog=FOG[variant], bd=SPEC['boundary_damage'], hv=HEAVENS[variant], glow=gl))
    np.save(os.path.join(out, fname + '_mat.npy'), W.m)
    info = {'variant': variant, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
            'decor_seed': decor_seed, 'layout_seed': W.seed, 'tag_rect': tag, 'glow_sources': len(glow),
            'floating_pieces': len(W.floating), 'build_s': round(time.time() - t0, 1), **W.stats}
    json.dump({**info, 'floating': W.floating}, open(os.path.join(out, fname + '_build.json'), 'w'), indent=1)
    print(json.dumps(info))
    return W


if __name__ == '__main__':
    out = sys.argv[1]
    seed = int(sys.argv[sys.argv.index('--seed') + 1]) if '--seed' in sys.argv else int.from_bytes(os.urandom(4), 'little')
    for v in ('day', 'night'):
        build_variant(v, seed, out, sky='--no-sky' not in sys.argv)
