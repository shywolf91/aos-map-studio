"""Load the original Christmas PVP into a kit Canvas and classify its voxels (colour + position).

The original is a Minecraft export: every block is one flat colour. We keep every voxel and classify it so the art
pass can regrade each family with its own ramp:
  wall    snow-coloured voxels of the 1-voxel perimeter wall core (x 91 / 421, y 132 / 381, +1 relief)
  snow    light low-chroma voxels (snow blocks, snow layers, white trims)
  ice     light saturated blues (packed-ice drifts, icicles)
  water   dark saturated blues at pond level (z >= 58): frozen in the art pass
  glass   teal / cyan glass panes (gate-house windows): warm lit windows in the art pass
  other   everything else (paths, timber, candy, foliage, props): general evening grade
"""
from __future__ import annotations

import hashlib

import numpy as np
from scipy import ndimage as ndi

from aosmap.kit import Canvas, codec, palette

CLASSES = ('wall', 'snow', 'ice', 'water', 'glass', 'other')


def load(path):
    data = open(path, 'rb').read()
    solid, color, _ = codec.decode(data)
    return data, solid, codec.unpack_rgb(color), hashlib.sha256(data).hexdigest()


def colour_classes(rgb_list):
    """rgb_list (N,3) unique colours -> class names (array of str) by OKLCH."""
    lch = palette.rgb_to_oklch(np.asarray(rgb_list, float))
    L, C, h = lch[:, 0], lch[:, 1], lch[:, 2]
    out = np.full(len(rgb_list), 'other', dtype=object)
    blue = (h > 215) & (h < 266) & (C > 0.06)
    out[blue & (L >= 0.66)] = 'ice'
    out[blue & (L < 0.66)] = 'water'
    teal = (h > 170) & (h <= 215) & (C > 0.04) & (L > 0.45)
    out[teal] = 'glass'
    out[(L > 0.70) & (C < 0.065)] = 'snow'
    return out


def classify(solid, rgb, spec):
    """-> uint8 class index per voxel (index into CLASSES; 255 = air)."""
    cls = np.full(solid.shape, 255, np.uint8)
    pk = codec.pack_rgb(rgb[solid])
    u, inv = np.unique(pk, return_inverse=True)
    names = colour_classes(codec.unpack_rgb(u))
    idx = np.array([CLASSES.index(n) for n in names], np.uint8)
    cls[solid] = idx[inv]
    # water only at pond level; elsewhere (screens, ornaments) those blues are ordinary props
    z = np.arange(64)[None, None, :]
    cls[(cls == CLASSES.index('water')) & (z < 58)] = CLASSES.index('other')
    # wall: snow voxels on the perimeter core or its first relief layer
    (px0, px1), (py0, py1) = spec['perimeter']['x'], spec['perimeter']['y']
    xs = np.arange(512)[:, None, None]
    ys = np.arange(512)[None, :, None]
    ring = (((xs >= px0) & (xs <= px0 + 1)) | ((xs <= px1) & (xs >= px1 - 1)) |
            ((ys >= py0) & (ys <= py0 + 1)) | ((ys <= py1) & (ys >= py1 - 1)))
    inside = (xs >= px0) & (xs <= px1) & (ys >= py0) & (ys <= py1)
    cls[(cls == CLASSES.index('snow')) & ring & inside & (z < 57)] = CLASSES.index('wall')
    return cls


def ground_estimate(solid, window=25):
    """Ground top z per column without narrow objects (grey opening of the height field)."""
    top = np.argmax(solid, axis=2)
    h = 63 - top
    g = ndi.grey_opening(h, size=(window, window))
    return (63 - g).astype(np.int16)


def to_canvas(solid, rgb, cls, name):
    cv = Canvas(name)
    cv.solid[:] = solid
    cv.rgb[:] = rgb
    for c in CLASSES:
        cv.material('orig_' + c)
    m = np.zeros(solid.shape, np.uint16)
    for i, c in enumerate(CLASSES):
        m[cls == i] = cv.materials['orig_' + c]
    cv.mat[:] = m
    cv.H[:] = ground_estimate(solid)
    return cv
