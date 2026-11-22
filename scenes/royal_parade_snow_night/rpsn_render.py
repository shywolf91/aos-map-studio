"""Renders for Royal Parade Snow Night (numpy previews, NOT client captures).

    python scenes/royal_parade_snow_night/rpsn_render.py OUTDIR [--crops name,...]

Writes OUTDIR/renders/: top-down (new and original), close-ups (aosmap.render.isometric, s = 5) of the spawn
roundabout ends, the great trees, the boulevard with festive vehicles, facades with lights, the quay ice and the
credit, and a before/after contact sheet of the same crops.
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
from aosmap.kit import codec, preview  # noqa: E402
from aosmap.render import isometric  # noqa: E402
from aosmap.vxl import VoxelMap  # noqa: E402

from rpsn_spec import SPEC  # noqa: E402

# name: (x0, y0, x1, y1, s, view)
CROPS = {
    'roundabout_west': (8, 222, 70, 292, 5, 0),
    'spawn_blue': (92, 222, 176, 290, 5, 0),
    'spawn_red': (336, 222, 420, 290, 5, 2),
    'great_tree_blue': (128, 238, 160, 276, 7, 0),
    'boulevard_floats_west': (120, 228, 236, 284, 4, 0),
    'boulevard_centre': (180, 228, 330, 284, 4, 0),
    'santa_sleigh_west': (52, 236, 84, 258, 8, 0),
    'facades_north': (160, 180, 260, 240, 4, 0),
    'facades_south': (40, 270, 160, 330, 4, 2),
    'quay_ice_north': (60, 140, 200, 200, 4, 0),
    'credit_tag': (240, 420, 500, 510, 2, 0),
}


def _vm(solid, rgb):
    return VoxelMap(solid, codec.pack_rgb(rgb), solid.copy())


def label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, min(im.width, 9 * len(text) + 8), 14), fill=(20, 20, 26))
    d.text((4, 2), text, fill=(230, 230, 230))
    return im


def render(out, crops=None):
    rd = os.path.join(out, 'renders')
    os.makedirs(rd, exist_ok=True)
    data = open(os.path.join(out, SPEC['file'] + '.vxl'), 'rb').read()
    S, C, _ = codec.decode(data)
    rgb = codec.unpack_rgb(C).astype(np.uint8)
    oS, oC, _ = codec.decode(open(SPEC['source']['vxl'], 'rb').read())
    orgb = codec.unpack_rgb(oC).astype(np.uint8)
    paths = {}
    for nm, (s_, c_) in (('topdown', (S, rgb)), ('topdown_original', (oS, orgb))):
        im = preview.topdown(s_, c_, scale=2)
        p = os.path.join(rd, nm + '.png')
        im.save(p)
        paths[nm] = p
    strip = preview.topdown(S, rgb, scale=3, crop=(0, 150, 511, 356))
    strip.save(os.path.join(rd, 'topdown_strip.png'))
    vm, ovm = _vm(S, rgb), _vm(oS, orgb)
    pairs = []
    for nm, (x0, y0, x1, y1, s, view) in CROPS.items():
        if crops and nm not in crops:
            continue
        a = isometric(vm, crop=(x0, y0, x1, y1), s=s, view=view, bg=(30, 30, 40))
        label(a, f'{nm} - numpy preview, not a client capture')
        a.save(os.path.join(rd, f'close_{nm}.png'))
        paths[nm] = os.path.join(rd, f'close_{nm}.png')
        b = isometric(ovm, crop=(x0, y0, x1, y1), s=max(2, s // 2), view=view, bg=(30, 30, 40))
        a2 = a.resize((max(1, a.width // 2), max(1, a.height // 2)), Image.LANCZOS)
        pairs.append((nm, b, a2))
    if pairs:
        W = max(b.width + a.width for _, b, a in pairs) + 24
        H = sum(max(b.height, a.height) + 22 for _, b, a in pairs) + 8
        sheet = Image.new('RGB', (W, H), (24, 24, 30))
        d = ImageDraw.Draw(sheet)
        yy = 6
        for nm, b, a in pairs:
            d.text((8, yy), f'{nm}: original (left) / v2 (right) - numpy preview', fill=(230, 230, 230))
            yy += 14
            sheet.paste(b, (8, yy))
            sheet.paste(a, (16 + b.width, yy))
            yy += max(b.height, a.height) + 8
        sheet.save(os.path.join(rd, 'before_after.png'))
        paths['before_after'] = os.path.join(rd, 'before_after.png')
    # whole-map iso (two halves)
    for nm, cr in (('iso_west', (0, 150, 260, 356)), ('iso_east', (252, 150, 511, 356))):
        im = isometric(vm, crop=cr, s=2, view=0, bg=(30, 30, 40))
        label(im, f'{nm} - numpy preview')
        im.save(os.path.join(rd, nm + '.png'))
    return paths


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--crops')
    ap.add_argument('--variant', default='v2', choices=('v2', 'recolor'))
    a = ap.parse_args()
    if a.variant == 'recolor':
        from rpsn_main import RECOLOR
        SPEC.update(RECOLOR)
    print(render(a.out, a.crops.split(',') if a.crops else None))
