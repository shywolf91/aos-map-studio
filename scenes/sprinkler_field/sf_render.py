"""Numpy preview renders for Sprinkler Field (labelled 'numpy preview - not a client capture').

python scenes/sprinkler_field/sf_render.py MAPDIR [shot ...]
Camera coordinates: (x, y, h) with h = 63 - z (height above the bottom).
"""
from __future__ import annotations

import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..'))
from aosmap.kit.codec import decode  # noqa: E402
from aosmap.kit.preview import topdown, view  # noqa: E402

from sf_spec import SPEC  # noqa: E402

FOG = SPEC['fog']
SHOTS = {
    'overview_sw': dict(cam=(-60, 620, 170), look=(256, 256, 10), fov=48, size=(1600, 1000)),
    'overview_ne': dict(cam=(580, -100, 170), look=(256, 256, 10), fov=48, size=(1600, 1000)),
    # ground level at the blue spawn, eye ~2.4 above the floor (z 50 -> h 13), looking at the sprinkler head
    'blue_spawn_ground_to_sprinkler': dict(cam=(120, 258, 16), look=(256, 210, 40), fov=72, size=(1400, 800)),
    'blue_spawn_from_platform_edge': dict(cam=(206, 256, 64), look=(118, 256, 14), fov=66, size=(1400, 800)),
    'sprinkler_closeup': dict(cam=(196, 150, 60), look=(256, 212, 40), fov=62, size=(1400, 800)),
    'trowel': dict(cam=(196, 372, 36), look=(256, 300, 26), fov=62, size=(1400, 800)),
    'hose_arch_and_split': dict(cam=(150, 175, 26), look=(170, 120, 14), fov=70, size=(1400, 800)),
    'nest_entrance_A': dict(cam=(84, 186, 22), look=(104, 168, 8), fov=62, size=(1400, 800)),
    'south_oneoffs': dict(cam=(256, 600, 110), look=(256, 440, 8), fov=60, size=(1600, 900)),
    'north_oneoffs': dict(cam=(256, -80, 110), look=(256, 80, 8), fov=60, size=(1600, 900)),
}


def main(mapdir, names=None):
    vx = sorted(glob.glob(os.path.join(mapdir, '*.vxl')))[0]
    solid, color, _ = decode(open(vx, 'rb').read())
    out = os.path.join(mapdir, 'renders')
    os.makedirs(out, exist_ok=True)
    if not names or 'top' in names:
        topdown(solid, color).save(os.path.join(out, '01_top_down.png'))
    for k, kw in SHOTS.items():
        if names and k not in names:
            continue
        fog = None if k.startswith('overview') else FOG
        view(solid, color, fog=fog, fog_dist=(70, 220), **kw).save(os.path.join(out, k + '.png'))
    return out


if __name__ == '__main__':
    print(main(sys.argv[1], sys.argv[2:]))
