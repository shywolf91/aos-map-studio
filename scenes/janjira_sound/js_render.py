"""Numpy previews for Janjira Sound (stamped 'numpy preview - not a client capture').

python scenes/janjira_sound/js_render.py maps/janjira_sound_v1
h = 63 - z (height above the bottom) in camera coordinates.
"""
from __future__ import annotations

import glob
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..'))
from aosmap.kit.codec import decode  # noqa: E402
from aosmap.kit.preview import _label, topdown, view  # noqa: E402

FOG = (190, 184, 178)
SHOTS = {
    '03_iso_whole_map': dict(cam=(-40, 600, 230), look=(256, 256, 0), fov=44, size=(1600, 1000)),
    '04_iso_whole_map_ne': dict(cam=(560, -90, 230), look=(256, 256, 0), fov=44, size=(1600, 1000)),
    '05_iso_blue_fort': dict(cam=(190, 350, 60), look=(110, 256, 6), fov=58, size=(1400, 850)),
    '06_iso_blue_fort_rear': dict(cam=(20, 160, 50), look=(100, 256, 8), fov=58, size=(1400, 850)),
    '07_iso_centre': dict(cam=(256, 350, 52), look=(256, 256, 4), fov=60, size=(1400, 850)),
    '08_blue_spawn_from_platform_edge': dict(cam=(206, 256, 64), look=(118, 256, 4), fov=66, size=(1400, 800)),
    '09_blue_front_eye_level': dict(cam=(120, 256, 7), look=(256, 256, 10), fov=70, size=(1400, 800)),
    '10_nw_island_tower': dict(cam=(190, 140, 40), look=(205, 205, 8), fov=60, size=(1400, 800)),
    '11_dhow': dict(cam=(225, 380, 25), look=(255, 335, 8), fov=60, size=(1400, 800)),
}


def height_png(solid):
    top = np.argmax(solid, axis=2)
    h = (63 - top).astype(float)
    g = np.clip(h / 40.0, 0, 1)
    rgb = np.stack([30 + 225 * g, 40 + 200 * g, 90 + 120 * g], -1)
    rgb[top >= 63] = (20, 40, 70)
    im = Image.fromarray(rgb.astype(np.uint8).transpose(1, 0, 2)).resize((1024, 1024), Image.NEAREST)
    return _label(im)


def main(mapdir):
    vx = sorted(glob.glob(os.path.join(mapdir, '*.vxl')))[0]
    solid, color, _ = decode(open(vx, 'rb').read())
    out = os.path.join(mapdir, 'renders')
    os.makedirs(out, exist_ok=True)
    topdown(solid, color, scale=2).save(os.path.join(out, '01_top.png'))
    height_png(solid).save(os.path.join(out, '02_height.png'))
    for k, kw in SHOTS.items():
        view(solid, color, fog=FOG if not k.startswith('03') and not k.startswith('04') else None,
             fog_dist=(110, 260), **kw).save(os.path.join(out, k + '.png'))
    return out


if __name__ == '__main__':
    print(main(sys.argv[1]))
