"""Numpy preview renders for Cursed Skull Reef (labelled 'numpy preview - not a client capture').

python scenes/cursed_skull_reef/csr_render.py MAPDIR [shot ...]
Camera coordinates use h = 63 - z (height above the bottom).
"""
from __future__ import annotations

import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..'))
from aosmap.kit.codec import decode  # noqa: E402
from aosmap.kit.preview import topdown, view  # noqa: E402

FOG = (156, 184, 170)
SHOTS = {
    'overview_sw': dict(cam=(-40, 620, 170), look=(256, 256, 0), fov=50, size=(1600, 1000)),
    'overview_ne': dict(cam=(560, -100, 170), look=(256, 256, 0), fov=50, size=(1600, 1000)),
    'blue_spawn_from_platform_edge': dict(cam=(206, 256, 64), look=(118, 256, 18), fov=66, size=(1400, 800)),
    'blue_front_eye_level': dict(cam=(122, 256, 18), look=(256, 256, 18), fov=70, size=(1400, 800)),
    'neck_under_platform': dict(cam=(200, 300, 20), look=(256, 250, 2), fov=66, size=(1400, 800)),
    'assist_wreck_west': dict(cam=(190, 262, 40), look=(221, 222, 30), fov=64, size=(1400, 800)),
    'galleon': dict(cam=(212, 250, 34), look=(256, 190, 10), fov=64, size=(1400, 800)),
    'cannon_fort': dict(cam=(256, 196, 40), look=(256, 140, 14), fov=64, size=(1400, 800)),
    'skull_crag': dict(cam=(256, 262, 40), look=(256, 340, 24), fov=66, size=(1400, 800)),
    'skull_cave_mouth': dict(cam=(256, 290, 12), look=(256, 330, 8), fov=70, size=(1400, 800)),
    'blue_town_north': dict(cam=(150, 160, 34), look=(110, 210, 16), fov=64, size=(1400, 800)),
    'blue_harbour': dict(cam=(10, 300, 26), look=(60, 256, 12), fov=64, size=(1400, 800)),
    'ruined_tavern': dict(cam=(70, 120, 26), look=(40, 156, 12), fov=62, size=(1400, 800)),
    'lighthouse_stump': dict(cam=(440, 120, 30), look=(472, 156, 22), fov=62, size=(1400, 800)),
    'rum_dock': dict(cam=(100, 440, 22), look=(130, 404, 6), fov=62, size=(1400, 800)),
    'gallows': dict(cam=(420, 440, 22), look=(388, 400, 10), fov=62, size=(1400, 800)),
    'north_chain_brigs': dict(cam=(256, 140, 40), look=(200, 80, 6), fov=70, size=(1400, 800)),
    'heeled_brig': dict(cam=(230, 110, 22), look=(256, 60, 6), fov=64, size=(1400, 800)),
    'ghost_galleon': dict(cam=(170, 110, 30), look=(150, 30, 38), fov=60, size=(1400, 800)),
    'tag': dict(cam=(60, 440, 50), look=(60, 498, 0), fov=60, size=(1400, 800)),
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
