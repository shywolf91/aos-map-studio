"""Elderveil previews: python scenes/elderveil/ev_render.py OUTDIR [shot ...]

Numpy previews (aosmap.kit.preview), stamped "numpy preview - not a client capture". Camera tuples are
(x, y, h) with h = 63 - z (height above the bottom). Fog in the map's lilac.
"""
from __future__ import annotations

import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from aosmap.kit import codec, preview  # noqa: E402

FOG = (176, 172, 190)
SHOTS = {
    'overview_sw': dict(cam=(-60, 600, 190), look=(256, 256, 10), fov=46, size=(1600, 1000)),
    'overview_ne': dict(cam=(580, -80, 190), look=(256, 256, 10), fov=46, size=(1600, 1000)),
    'blue_spawn_camp': dict(cam=(132, 300, 24), look=(90, 250, 14), fov=70),
    'blue_spawn_east_front': dict(cam=(124, 256, 16.5), look=(220, 256, 20), fov=72),
    'spire_from_below': dict(cam=(204, 238, 14.5), look=(190, 218, 42), fov=72),
    'spire_from_top': dict(cam=(190, 222, 53.4), look=(130, 250, 14), fov=72),
    'plaza_queen': dict(cam=(222, 230, 19), look=(256, 185, 13), fov=72),
    'library_interior': dict(cam=(243, 122, 15.4), look=(256, 112, 15), fov=80),
    'under_platform': dict(cam=(214, 257, 15.4), look=(256, 256, 13), fov=72),
    'heart_tree': dict(cam=(212, 302, 20), look=(256, 340, 28), fov=72),
    'aqueduct': dict(cam=(140, 122, 20), look=(100, 88, 21), fov=72),
    'heart_tree_under_root': dict(cam=(244, 336, 12.6), look=(256, 340, 26), fov=80),
    'queen_head': dict(cam=(244, 178, 21), look=(256, 187, 19), fov=64),
    'queen_oblique': dict(cam=(222, 174, 44), look=(256, 210, 12), fov=60),
    'elder_head': dict(cam=(240, 250, 17), look=(256, 255, 12), fov=62),
    'cliff_west': dict(cam=(78, 300, 16), look=(20, 296, 30), fov=74),
    'cliff_falls': dict(cam=(228, 446, 14), look=(243, 486, 30), fov=74),
    'grove_interior': dict(cam=(96, 128, 15.4), look=(80, 110, 18), fov=78),
    'mushrooms_waterfall': dict(cam=(196, 408, 18), look=(243, 470, 24), fov=72),
    'islet': dict(cam=(54, 176, 42), look=(78, 150, 45), fov=60),
    'sky_tag': dict(cam=(36, 50, 68), look=(36, 16, 56), fov=60),
}


def render(map_dir, names=None):
    vx = sorted(glob.glob(os.path.join(map_dir, '*.vxl')))[0]
    solid, color, _ = codec.decode(open(vx, 'rb').read())
    out = os.path.join(map_dir, 'renders')
    os.makedirs(out, exist_ok=True)
    preview.topdown(solid, color).save(os.path.join(out, '01_top_down.png'))
    for name, kw in SHOTS.items():
        if names and name not in names:
            continue
        kw = dict(kw)
        kw.setdefault('size', (1200, 700))
        fog = None if name.startswith('overview') else FOG               # overviews are far beyond the fog
        preview.view(solid, color, fog=fog, **kw).save(os.path.join(out, name + '.png'))
    return out


if __name__ == '__main__':
    print(render(sys.argv[1], sys.argv[2:] or None))
