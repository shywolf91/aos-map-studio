"""Opt-in floating sky decor (owner asked): sleigh-and-reindeer silhouette, snow clouds, a faint aurora band.
Rules [USER]: >= 60 from the platform (we keep >= 120), never over a spawn square, >= 8 air below, 2 voxels clear
round each piece; each piece recorded in cv.expect_floating. Collapse caveat: a player block touching a piece, once
broken, drops that piece for the round."""
from __future__ import annotations

import math

import numpy as np

from aosmap.kit import sky

SLEIGH = [
    '..........................................',
    '.r.r.......r.r.......r.r..................',
    '.rrr.......rrr.......rrr..........SSSSSS..',
    'RRRRRR....RRRRRR....RRRRRR.......SSPPPPSS.',
    '.RRRR......RRRR......RRRR....-----SSSSSSSS',
    '.R..R......R..R......R..R........S......S.',
    '..........................................',
]


def sleigh(target, x, y, z, heading=0.0, scale=2):
    """Sleigh + three reindeer, drawn at 2x so it reads from the south chain (birds under ~13 wide vanish)."""
    cols = {'#': (60, 40, 36), 'R': (96, 66, 48), 'r': (128, 96, 70), 'S': (150, 40, 40), 'P': (196, 160, 70),
            '-': (120, 110, 90)}
    big = []
    for row in SLEIGH:
        r2 = ''.join(ch * scale for ch in row)
        big += [r2] * scale
    pts = sky.stamp(target, big, x, y, z, heading, cols, tips_up=0)
    pts += sky.stamp(target, big, x, y, z - 1, heading, cols, tips_up=0)
    return pts


def aurora(target, x0, x1, yc, z_top, height=6, amp=5.0, period=70.0, phase=0.0):
    """Wavy curtain 1 voxel thick: teal-green at the hem, violet at the top, faint (desaturated) colours; each x step
    keeps face contact (an extra voxel where y changes)."""
    pts = []
    prev = None
    for x in range(x0, x1 + 1):
        t = (x - x0) / max(1, x1 - x0)
        hh = max(2, int(round(height * math.sin(math.pi * t) ** 0.6)))
        y = int(round(yc + amp * math.sin(2 * math.pi * x / period + phase)))
        cols = [y] if prev is None or prev == y else [prev, y]
        for yy in cols:
            for k in range(hh):
                f = k / max(1, hh - 1)
                c = (int(96 + 60 * f), int(176 - 64 * f), int(150 + 50 * f))
                target.set(x, yy, z_top + hh - 1 - k, c, 'sky')
                pts.append((x, yy, z_top + hh - 1 - k))
        prev = y
    return pts


def aurora_at(target, x, y, z, length, height=6, amp=4.0, period=64.0, phase=0.0):
    return aurora(target, x, x + length, y, z, height, amp, period, phase)


def place_all(cv, rep, S, rng):
    out = []
    out.append(sky.place(cv, 'sleigh and reindeer', sleigh, 256, 474, 8, 0.0))
    for i, (x, y, z, L) in enumerate(((60, 150, 6, 24), (452, 362, 7, 26), (180, 26, 5, 22), (340, 488, 6, 22),
                                      (40, 330, 8, 18))):
        top = (206, 208, 214)
        bot = (168, 174, 190)
        out.append(sky.place(cv, f'snow cloud {i}', sky.cloud, x, y, z, L, seed=100 + i, top=top, bottom=bot))
    for i, (x0, x1, yc, zt, ph) in enumerate(((40, 190, 20, 5, 0.0), (200, 330, 14, 4, 1.7), (340, 470, 22, 5, 3.1))):
        out.append(sky.place(cv, f'aurora {i}', aurora_at, x0, yc, zt, x1 - x0, 6, 4.0, 64.0, ph))
    return [{k: o[k] for k in ('name', 'voxels', 'x', 'y', 'z')} for o in out]
