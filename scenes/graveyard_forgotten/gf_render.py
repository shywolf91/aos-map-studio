"""Preview renders (numpy point-splat from the WKH renderer; NOT a game client).

python gf_render.py OUTDIR [shot names...]
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'wicker_kings_harvest'))
from wkh_render import topdown, view          # noqa: E402

from gf_core import read_vxl                   # noqa: E402

FOG = (164, 170, 162)
SHOTS = [   # cam / look are (x, y, height) with height = 63 - z
    ('02_overview_sw', dict(cam=(-70, 600, 175), look=(256, 250, 10), fov=48, size=(1600, 1000))),
    ('03_overview_ne', dict(cam=(600, -60, 175), look=(256, 260, 10), fov=48, size=(1600, 1000))),
    ('04_facade_from_parvis', dict(cam=(256, 70, 32), look=(256, 140, 30), fov=62, size=(1280, 720))),
    ('05_blue_spawn_to_cathedral', dict(cam=(112, 256, 22), look=(240, 256, 28), fov=62, size=(1280, 720))),
    ('06_court_to_transept', dict(cam=(170, 300, 30), look=(232, 252, 22), fov=62, size=(1280, 720))),
    ('07_nave_ribcage', dict(cam=(248, 228, 22), look=(256, 160, 40), fov=70, size=(1280, 720))),
    ('08_hand_reaching', dict(cam=(300, 130, 34), look=(256, 66, 42), fov=60, size=(1280, 720))),
    ('09_hand_clawing', dict(cam=(232, 380, 30), look=(256, 440, 22), fov=62, size=(1280, 720))),
    ('10_cemetery_nw', dict(cam=(40, 230, 40), look=(140, 140, 20), fov=62, size=(1280, 720))),
    ('11_crossing_bell', dict(cam=(256, 300, 30), look=(256, 252, 18), fov=60, size=(1280, 720))),
    ('12_apse_altar', dict(cam=(256, 288, 24), look=(256, 330, 22), fov=62, size=(1280, 720))),
    ('13_platform_view_to_blue', dict(cam=(208, 256, 64.4), look=(118, 256, 19), fov=70, size=(1280, 720))),
]


if __name__ == '__main__':
    out = sys.argv[1]
    only = set(sys.argv[2:])
    rd = os.path.join(out, 'renders')
    os.makedirs(rd, exist_ok=True)
    s, c, _ = read_vxl(open(os.path.join(out, 'graveyard_of_the_forgotten.vxl'), 'rb').read())
    if not only or '01_top_down' in only:
        topdown(s, c, scale=2).save(os.path.join(rd, '01_top_down.png'))
    for name, kw in SHOTS:
        if only and name not in only:
            continue
        fogkw = {} if name.startswith(('02', '03')) else dict(fog=FOG, fog_dist=(90, 260))
        view(s, c, **fogkw, **kw).save(os.path.join(rd, name + '.png'))
        print(name)
    print('renders in', rd)
