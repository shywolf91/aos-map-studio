"""Frozen Icebreaker: painting helpers on top of aosmap.kit.Canvas.

* every material is a family of 1-4 close tones (fi_spec.PAL); `tone()` picks one per voxel from a crc-style hash
  so surfaces get texture without single-voxel speckle of foreign colours;
* `put` / `boxm` / `lamp` paint and tag the kit material grid (mirror + floating reports read it);
* `STRUCTS` is the craft_checks registry (build.json 'structures'), mirrored with the west half.
"""
from __future__ import annotations

import numpy as np

from aosmap.kit import noise
from aosmap.kit.symmetry import mirror_index
from fi_spec import PAL, GLOW

STRUCTS: list[dict] = []
INTERIORS_EXTRA: list = []


def _h(x, y, z, salt=0):
    return ((np.asarray(x, np.int64) * 73856093) ^ (np.asarray(y, np.int64) * 19349663)
            ^ (np.asarray(z, np.int64) * 83492791) ^ (salt * 2654435761)) & 0xFFFF


def tone(name, x, y, z, salt=0):
    t = PAL[name]
    return t[int(_h(x, y, z, salt)) % len(t)]


def P(name, mode='hash', salt=0):
    """Colour function for Canvas.box/fill_mask. mode: 'hash' (per voxel), 'course' (per z row: board courses),
    'block' (3x3x2 blocks: masonry / ice blocks), 'col' (per column)."""
    arr = np.array(PAL[name], float)
    n = len(arr)

    def f(xs, ys, zs):
        if mode == 'course':
            k = _h(np.zeros_like(xs), np.zeros_like(ys), zs, salt) % n
        elif mode == 'block':
            k = _h(xs // 3 + (zs // 2) * 7, ys // 3, zs // 2, salt) % n
        elif mode == 'col':
            k = _h(xs, ys, np.zeros_like(zs), salt) % n
        else:
            k = _h(xs, ys, zs, salt) % n
        return arr[k].astype(np.uint8)
    return f


def put(cv, x, y, z, name, mat='prop', salt=0):
    if 0 <= x < 512 and 0 <= y < 512 and 0 <= z <= 63:
        cv.set(int(x), int(y), int(z), tone(name, x, y, z, salt), mat)


def boxm(cv, x0, x1, y0, y1, z0, z1, name, mat='prop', mode='hash', salt=0):
    cv.box(min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1), min(z0, z1), max(z0, z1), P(name, mode, salt), mat)


def lamp(cv, x, y, z, kind='amber'):
    if 0 <= x < 512 and 0 <= y < 512 and 0 <= z < 62:
        cv.add_glow(int(x), int(y), int(z), GLOW[kind])
        cv.mat[int(x), int(y), int(z)] = cv.material('glow')


def top(cv, x, y):
    """Topmost solid z of a column (the voxel a player would stand on)."""
    return cv.column_top(int(x), int(y))


def ground(cv, x, y):
    return int(cv.H[int(x), int(y)])


def pad(cv, x0, x1, y0, y1, z=None, name='track', mat='ground'):
    """Level a site to z (default: median terrain height) and give it a packed-snow top. Returns z."""
    x0, x1, y0, y1 = max(0, x0), min(511, x1), max(0, y0), min(511, y1)
    if z is None:
        z = int(np.median(cv.H[x0:x1 + 1, y0:y1 + 1]))
    cv.carve(x0, x1, y0, y1, 0, z - 1)
    cv.box(x0, x1, y0, y1, z + 1, 63, P('snow'), 'ground')
    cv.box(x0, x1, y0, y1, z, z, P(name), mat)
    cv.H[x0:x1 + 1, y0:y1 + 1] = z
    return z


def reg(name, box, role):
    STRUCTS.append({'name': name, 'box': [int(v) for v in box], 'role': role})


def mirror_structs():
    """Add the east twin of every west-authored structure (call right after the canvas mirror)."""
    east = []
    for s in STRUCTS:
        x0, x1, y0, y1 = s['box']
        if x1 <= 255:
            east.append({'name': s['name'] + ' (E)', 'box': [mirror_index(x1), mirror_index(x0), y0, y1],
                         'role': s['role']})
            s['name'] += ' (W)'
    STRUCTS.extend(east)


def rng(tag, seed):
    return noise.rng(tag, seed)
