"""Numpy previews for Northgale Freighter (stamped 'numpy preview - not a client capture').

python scenes/northgale_freighter/nf_render.py maps/northgale_freighter_v1
h = 63 - z (height above the bottom) in camera coordinates. Deck floor z 40 = h 23; eye level on deck ~ h 25.
"""
from __future__ import annotations

import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..'))
from aosmap.kit.codec import decode  # noqa: E402
from aosmap.kit.preview import topdown, view  # noqa: E402

FOG = (170, 164, 190)
SHOTS = {
    '02_iso_whole_map_sw': dict(cam=(-60, 620, 250), look=(256, 256, 10), fov=44, size=(1600, 1000)),
    '03_iso_whole_map_ne': dict(cam=(580, -100, 250), look=(256, 256, 10), fov=44, size=(1600, 1000)),
    '04_bow_forecastle': dict(cam=(110, 150, 70), look=(40, 256, 26), fov=58, size=(1400, 850)),
    '05_bridge_and_funnel': dict(cam=(390, 160, 60), look=(465, 256, 34), fov=60, size=(1400, 850)),
    '06_deck_centre': dict(cam=(256, 150, 60), look=(256, 256, 24), fov=62, size=(1400, 850)),
    '07_blue_spawn_from_platform_edge': dict(cam=(206, 256, 64), look=(118, 256, 24), fov=66, size=(1400, 800)),
    '08_blue_front_eye_level': dict(cam=(124, 256, 26), look=(256, 256, 30), fov=70, size=(1400, 800)),
    '09_tween_deck': dict(cam=(178, 222, 17), look=(240, 230, 16), fov=74, size=(1400, 800)),
    '10_lower_hold_locomotive': dict(cam=(182, 226, 9), look=(240, 250, 6), fov=74, size=(1400, 800)),
    '11_gangway_and_side_port': dict(cam=(200, 150, 20), look=(200, 204, 14), fov=66, size=(1400, 800)),
    '12_north_islets': dict(cam=(256, 190, 24), look=(200, 110, 6), fov=66, size=(1400, 800)),
    '13_lighthouse': dict(cam=(292, 160, 34), look=(256, 118, 24), fov=58, size=(1400, 850)),
    '14_lighthouse_inside': dict(cam=(256, 121, 13), look=(256, 115, 24), fov=80, size=(1200, 800)),
}


def main(mapdir):
    vx = sorted(glob.glob(os.path.join(mapdir, '*.vxl')))[0]
    solid, color, _ = decode(open(vx, 'rb').read())
    out = os.path.join(mapdir, 'renders')
    os.makedirs(out, exist_ok=True)
    topdown(solid, color, scale=2).save(os.path.join(out, '01_top.png'))
    for k, kw in SHOTS.items():
        view(solid, color, fog=FOG if k[:2] not in ('02', '03') else None, fog_dist=(110, 260),
             **kw).save(os.path.join(out, k + '.png'))
    return out


if __name__ == '__main__':
    print(main(sys.argv[1]))
