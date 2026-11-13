"""Frostbell Hollow numpy previews (NOT client captures): the kit's standard shots plus eye-level views of the set
pieces, rendered with the map's fog.  python scenes/frostbell_hollow/fh_render.py out/frostbell_hollow"""
from __future__ import annotations

import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..'))
from aosmap.kit import preview  # noqa: E402
from aosmap.kit.codec import decode  # noqa: E402

from fh_spec import SPEC  # noqa: E402

# camera (x, y, h) and look (x, y, h); h = 63 - z, so the valley floor (z 50) is h 13 and eye level is h ~15.5
SHOTS = preview.STANDARD_SHOTS + [
    ('eye_blue_spawn_through_gatehouse', dict(cam=(108, 252, 19), look=(200, 256, 17), fov=70, size=(1400, 800))),
    ('eye_gatehouse_soldiers', dict(cam=(178, 240, 21), look=(148, 216, 22), fov=66, size=(1400, 800))),
    ('eye_market_spruce', dict(cam=(206, 146, 21), look=(256, 192, 28), fov=72, size=(1400, 800))),
    ('eye_rink', dict(cam=(214, 296, 22), look=(256, 330, 12), fov=70, size=(1400, 800))),
    ('eye_tavern_front', dict(cam=(222, 180, 21), look=(250, 152, 18), fov=70, size=(1400, 800))),
    ('eye_station_train', dict(cam=(226, 110, 21), look=(262, 80, 18), fov=72, size=(1400, 800))),
    ('eye_covered_bridge', dict(cam=(214, 386, 22), look=(256, 432, 11), fov=70, size=(1400, 800))),
    ('eye_chapel', dict(cam=(112, 232, 21), look=(72, 256, 22), fov=70, size=(1400, 800))),
    ('eye_village_houses', dict(cam=(124, 240, 22), look=(80, 196, 22), fov=72, size=(1400, 800))),
    ('eye_mill_creek', dict(cam=(118, 432, 12), look=(150, 410, 10), fov=70, size=(1400, 800))),
    ('eye_tunnel_chamber', dict(cam=(98.5, 160.5, 5.6), look=(112, 173, 5), fov=80, size=(1200, 700))),
    ('eye_carousel', dict(cam=(228, 280, 21), look=(256, 292, 15), fov=70, size=(1400, 800))),
    ('eye_under_platform_strip', dict(cam=(214, 244, 20), look=(256, 262, 14), fov=72, size=(1400, 800))),
    ('eye_blue_spawn_back_west', dict(cam=(132, 256, 20), look=(60, 256, 22), fov=72, size=(1400, 800))),
]


def render(map_dir):
    out = os.path.join(map_dir, 'renders')
    os.makedirs(out, exist_ok=True)
    vx = sorted(glob.glob(os.path.join(map_dir, '*.vxl')))[0]
    solid, color, _ = decode(open(vx, 'rb').read())
    preview.topdown(solid, color).save(os.path.join(out, '01_top_down.png'))
    shots = list(SHOTS)
    b = json.load(open(os.path.join(map_dir, 'build.json')))
    for i, p in enumerate((b.get('pads_built') or [])[:4]):
        x0, x1, y0, y1 = p['pad']
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        shots.append((f'eye_pad_{i}_{p["kind"].replace(" ", "_")}',
                      dict(cam=(cx - 16, cy + 12, 22), look=(cx, cy, 16), fov=40, size=(1000, 700))))
    for name, kw in shots:
        fog = None if name.startswith('overview') or name == 'eye_tunnel_chamber' else SPEC['fog']
        preview.view(solid, color, fog=fog, fog_dist=(30, 128), bg=SPEC['fog'] if fog else (34, 30, 44),
                     **kw).save(os.path.join(out, name + '.png'))
    return out


if __name__ == '__main__':
    print('numpy previews in', render(sys.argv[1]))
