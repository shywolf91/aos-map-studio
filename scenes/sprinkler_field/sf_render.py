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
    # art-pass close-ups (ground z 52 = h 11; tunnel floor z 60 = h 3)
    'hose_closeup': dict(cam=(60, 150, 22), look=(96, 124, 16), fov=60, size=(1400, 800)),
    'nest_north_chamber_interior': dict(cam=(156, 170, 5.5), look=(178, 172, 4.5), fov=80, size=(1400, 800)),
    'nest_queen_chamber_interior': dict(cam=(245, 150, 5.5), look=(266, 152, 4.5), fov=80, size=(1400, 800)),
    'tussock_details': dict(cam=(150, 228, 22), look=(150, 200, 26), fov=60, size=(1400, 800)),
    'clover_dandelion_mushroom': dict(cam=(160, 252, 18), look=(190, 205, 20), fov=66, size=(1400, 800)),
    'spigot': dict(cam=(50, 178, 30), look=(16, 140, 22), fov=62, size=(1400, 800)),
    'hose_reel': dict(cam=(462, 176, 30), look=(494, 132, 20), fov=62, size=(1400, 800)),
    'flowerpot': dict(cam=(110, 470, 24), look=(60, 446, 14), fov=62, size=(1400, 800)),
    'glove': dict(cam=(420, 400, 34), look=(452, 450, 10), fov=66, size=(1400, 800)),
    'snail_shell': dict(cam=(378, 100, 30), look=(420, 60, 22), fov=62, size=(1400, 800)),
    'footprint_and_key': dict(cam=(256, 400, 40), look=(290, 460, 8), fov=66, size=(1400, 800)),
    'plant_label': dict(cam=(110, 80, 26), look=(76, 50, 22), fov=62, size=(1400, 800)),
    'corner_tag': dict(cam=(52, 470, 40), look=(52, 500, 9), fov=60, size=(1400, 800)),
    'sky_dragonfly': dict(cam=(60, 200, 28), look=(98, 152, 33), fov=50, size=(1400, 800)),
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
