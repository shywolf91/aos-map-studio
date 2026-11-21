"""Hrafnfjord Yule: shared helpers - function colours (graybox), voxel helpers, structure registry.

Graybox colours are FUNCTION colours (what a voxel is for), not art. The art pass (its own module) recolours by
material name; gameplay geometry is never changed there.
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..', '..')]

from aosmap.kit.symmetry import mirror_index  # noqa: E402

# function colour per material name (graybox)
FC = {
    'ground': (150, 158, 150), 'field': (168, 160, 122), 'fell': (122, 140, 120), 'track': (140, 136, 150),
    'ice': (108, 148, 140), 'bank': (128, 138, 128), 'holm': (120, 120, 112), 'rock': (112, 112, 118),
    'wall': (178, 148, 108), 'stone': (132, 132, 136), 'roof': (150, 72, 60), 'ridge': (110, 50, 44),
    'floor': (122, 96, 70), 'stair': (222, 200, 60), 'furniture': (100, 80, 62), 'post': (96, 72, 54),
    'door_trim': (230, 230, 230), 'prop': (200, 120, 60), 'hay': (206, 180, 96), 'hull': (92, 70, 56),
    'deck': (150, 120, 86), 'canvas': (190, 186, 160), 'mast': (110, 86, 66), 'rune': (96, 104, 140),
    'log': (130, 96, 64), 'fire': (240, 140, 60), 'straw': (200, 176, 110), 'antler': (210, 200, 170),
    'berm': (138, 150, 132), 'hill': (150, 152, 128),
}

STRUCTS: list[dict] = []
LANDMARKS: list[dict] = []


def put(cv, x, y, z, name, mat=None):
    cv.set(x, y, z, FC[name], mat or name)


def boxm(cv, x0, x1, y0, y1, z0, z1, name, mat=None):
    """Inclusive box; z0/z1 in any order."""
    cv.box(min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1), min(z0, z1), max(z0, z1), FC[name], mat or name)


def top(cv, x, y):
    col = cv.solid[x, y]
    return int(np.argmax(col)) if col.any() else 64


def ground_med(cv, x0, x1, y0, y1):
    return int(np.median(cv.H[x0:x1 + 1, y0:y1 + 1]))


def pad(cv, x0, x1, y0, y1, z, name='track', clear_up=24):
    """Flatten a footprint: solid from z down to 63, air above z (up to clear_up) -> floor z."""
    cv.box(x0, x1, y0, y1, max(0, z - clear_up), z - 1, air=True)
    boxm(cv, x0, x1, y0, y1, z, 63, name, 'ground')
    cv.H[x0:x1 + 1, y0:y1 + 1] = z


def reg(name, box, role):
    STRUCTS.append({'name': name, 'box': [int(v) for v in box], 'role': role})


def landmark(name, box):
    LANDMARKS.append({'name': name, 'box': [int(v) for v in box]})


def mirror_registry(lst):
    """East twin of every west-only entry; centre entries (crossing x 256) are kept once."""
    east = []
    for s in lst:
        x0, x1, y0, y1 = s['box']
        if x1 <= 255:
            e = dict(s)
            e['name'] = s['name'] + ' (E)'
            e['box'] = [mirror_index(x1), mirror_index(x0), y0, y1]
            s['name'] += ' (W)'
            east.append(e)
        elif x0 <= 255 < x1:
            s['box'] = [x0, mirror_index(x0), y0, y1]      # authored west half of a centred piece -> full box
    lst.extend(east)
