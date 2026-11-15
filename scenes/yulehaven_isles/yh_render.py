"""Numpy preview renders for Yulehaven Isles (labelled 'numpy preview - not a client capture').

python scenes/yulehaven_isles/yh_render.py MAPDIR [shot ...]
h = 63 - z (height above the bottom) in camera coordinates.
"""
from __future__ import annotations

import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..'))
from aosmap.kit.codec import decode  # noqa: E402
from aosmap.kit.preview import topdown, view  # noqa: E402

FOG = (172, 174, 192)
SHOTS = {
    'overview_sw': dict(cam=(-40, 620, 160), look=(256, 256, 0), fov=50, size=(1600, 1000)),
    'overview_ne': dict(cam=(560, -100, 160), look=(256, 256, 0), fov=50, size=(1600, 1000)),
    'blue_spawn_from_platform_edge': dict(cam=(206, 256, 64), look=(118, 256, 18), fov=66, size=(1400, 800)),
    'blue_front_eye_level': dict(cam=(122, 256, 18), look=(256, 256, 18), fov=70, size=(1400, 800)),
    'islet_ship': dict(cam=(200, 330, 40), look=(256, 260, 10), fov=60, size=(1400, 800)),
    'ship_closeup': dict(cam=(232, 300, 18), look=(256, 262, 8), fov=62, size=(1400, 800)),
    'blue_village_north': dict(cam=(150, 160, 34), look=(110, 214, 16), fov=64, size=(1400, 800)),
    'blue_village_south': dict(cam=(160, 360, 30), look=(110, 300, 14), fov=64, size=(1400, 800)),
    'inner_north_shore': dict(cam=(230, 150, 24), look=(186, 180, 6), fov=64, size=(1400, 800)),
    'inner_south_shore': dict(cam=(230, 372, 24), look=(178, 330, 6), fov=64, size=(1400, 800)),
    'lighthouse': dict(cam=(130, 40, 40), look=(90, 70, 22), fov=62, size=(1400, 800)),
    'goat': dict(cam=(380, 40, 26), look=(422, 72, 18), fov=62, size=(1400, 800)),
    'chapel': dict(cam=(382, 470, 30), look=(422, 439, 18), fov=62, size=(1400, 800)),
    'ice_camp': dict(cam=(140, 470, 24), look=(104, 439, 4), fov=62, size=(1400, 800)),
    'north_chain': dict(cam=(256, 150, 46), look=(200, 85, 6), fov=66, size=(1400, 800)),
    'iceberg_tag': dict(cam=(130, 420, 70), look=(54, 494, 50), fov=62, size=(1400, 800)),
    'bonfire': dict(cam=(256, 360, 26), look=(256, 318, 8), fov=62, size=(1400, 800)),
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
