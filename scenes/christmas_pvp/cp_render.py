"""Christmas PVP v2 previews (numpy renders, not client captures).

    python scenes/christmas_pvp/cp_render.py OUTDIR [--before]

Writes OUTDIR/renders/: top-down, isometric overview, close-ups (spawn, centre trees, walls with lights, pond,
candy tower), eye-level views with fog, and with --before a before/after contact sheet against the original.
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..'))

from aosmap import render  # noqa: E402
from aosmap.kit import codec, preview  # noqa: E402
from aosmap.vxl import VoxelMap  # noqa: E402

from cp_spec import SPEC  # noqa: E402

LABEL = 'numpy preview - not a client capture'

ISO = {   # name: (crop x0, y0, x1, y1), view, scale
    'iso_overview': ((88, 128, 424, 384), 0, 2),
    'iso_spawn_blue_x5': ((96, 222, 172, 290), 0, 5),
    'iso_spawn_red_x5': ((340, 222, 416, 290), 2, 5),
    'iso_centre_trees_x4': ((196, 222, 316, 290), 0, 4),
    'iso_pond_and_tower_x4': ((200, 290, 312, 350), 0, 4),
    'iso_candy_tower_x5': ((112, 192, 156, 236), 0, 5),
}
VIEWS = {  # perspective (cam, look, fov), h = 63 - z
    'eye_blue_spawn_to_front': ((112, 256, 4.5), (230, 256, 8), 70),
    'eye_red_spawn_to_front': ((400, 256, 4.5), (282, 256, 8), 70),
    'eye_west_wall_lights': ((176, 250, 6), (92, 250, 26), 72),
    'eye_north_wall_lights': ((250, 230, 6), (250, 132, 28), 72),
    'eye_south_wall_lights': ((256, 300, 6), (256, 381, 28), 72),
    'eye_centre_trees': ((256, 205, 8), (256, 256, 22), 74),
    'platform_edge_to_blue_spawn': ((206, 256, 64), (118, 256, 2), 66),
    'overview_high': ((256, 470, 120), (256, 250, 0), 60),
}


def _vm(solid, color):
    vm = VoxelMap()
    vm.solid = solid
    vm.color = codec.as_packed(color)
    return vm


def _stamp(im, text=LABEL):
    d = ImageDraw.Draw(im)
    d.text((6, im.height - 14), text, fill=(255, 255, 255))
    return im


def render_all(out, fog=None, prefix=''):
    data = open(os.path.join(out, SPEC['file'] + '.vxl'), 'rb').read()
    solid, color, _ = codec.decode(data)
    rd = os.path.join(out, 'renders')
    os.makedirs(rd, exist_ok=True)
    fog = fog or SPEC['fog']
    preview.topdown(solid, color, scale=2, crop=(86, 126, 426, 386)).save(os.path.join(rd, prefix + 'top_down.png'))
    vm = _vm(solid, color)
    for name, (crop, view, s) in ISO.items():
        _stamp(render.isometric(vm, crop=crop, view=view, s=s)).save(os.path.join(rd, prefix + name + '.png'))
    for name, (cam, look, fov) in VIEWS.items():
        preview.view(solid, color, cam=cam, look=look, fov=fov, size=(1280, 720), fog=fog,
                     fog_dist=(70, 130), bg=fog).save(os.path.join(rd, prefix + name + '.png'))
    return rd


def before_after(out):
    src = open(SPEC['source'], 'rb').read()
    s0, c0, _ = codec.decode(src)
    data = open(os.path.join(out, SPEC['file'] + '.vxl'), 'rb').read()
    s1, c1, _ = codec.decode(data)
    rd = os.path.join(out, 'renders')
    pairs = []
    crop = (86, 126, 426, 386)
    pairs.append((preview.topdown(s0, c0, scale=2, crop=crop, label=False),
                  preview.topdown(s1, c1, scale=2, crop=crop, label=False)))
    for name in ('eye_blue_spawn_to_front', 'eye_centre_trees', 'eye_west_wall_lights'):
        cam, look, fov = VIEWS[name]
        pairs.append(tuple(preview.view(s, c, cam=cam, look=look, fov=fov, size=(680, 383), label=False,
                                        fog=f, fog_dist=(70, 130), bg=f or (200, 220, 240))
                           for s, c, f in ((s0, c0, None), (s1, c1, SPEC['fog']))))
    for crop2, view, sc in (ISO['iso_spawn_blue_x5'], ISO['iso_centre_trees_x4']):
        pairs.append(tuple(render.isometric(_vm(s, c), crop=crop2, view=view, s=max(2, sc - 2))
                           for s, c in ((s0, c0), (s1, c1))))
    W = max(a.width + b.width for a, b in pairs) + 30
    H = sum(max(a.height, b.height) for a, b in pairs) + 10 * len(pairs) + 40
    sheet = Image.new('RGB', (W, H), (24, 26, 30))
    d = ImageDraw.Draw(sheet)
    d.text((10, 8), 'BEFORE (original Christmas PVP, GTR-CODE)', fill=(255, 255, 255))
    d.text((W // 2 + 10, 8), 'AFTER (Christmas PVP v2, cozy evening)', fill=(255, 255, 255))
    y = 30
    for a, b in pairs:
        sheet.paste(a, (10, y))
        sheet.paste(b, (20 + a.width, y))
        y += max(a.height, b.height) + 10
    _stamp(sheet)
    sheet.save(os.path.join(rd, 'before_after_sheet.png'))
    return os.path.join(rd, 'before_after_sheet.png')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--before', action='store_true')
    a = ap.parse_args()
    print(render_all(a.out))
    if a.before:
        print(before_after(a.out))
