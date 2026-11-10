"""Frostbell Hollow sky decor (owner opt-in, expected floating): a sleigh-and-reindeer silhouette over the station and
four snow-cloud puffs. Placed AFTER the mirror with aosmap.kit.sky.place, which enforces the rules (>= 60 from the
platform, never over a spawn square, >= 8 air below, 2 voxels of clearance); every piece is one face-connected
component and its box goes into cosmetic_asymmetric_boxes. Collapse caveat: a player block touching a piece, once
broken, drops that piece for the round."""
from __future__ import annotations

from aosmap.kit import sky

# top-down silhouette, heading +x (rows = across the flight line). '#' dark body, 'r' warm rim, 'a' antler,
# 'h' harness, 's' sleigh body, 'g' gold trim. Each reindeer is 14 long; the sleigh 17 long.
REINDEER = [
    '...a..a.......',
    '..aa.aa.......',
    '...aaa........',
    '...r##rrrrr...',
    '.r######rrr##.',
    'rr###########r',
    '.r######rrr##.',
    '...r##rrrrr...',
]
SLEIGH = [
    '..ggggggggggggg..',
    '.gsssssssssssssg.',
    'gsssssssssssssssg',
    'gsssssrrrrrsssssg',
    'gsssssssssssssssg',
    '.gsssssssssssssg.',
    '..ggggggggggggg..',
]


def _grid(rows, x0, y0):
    out = {}
    for i, row in enumerate(rows):
        for j, ch in enumerate(row):
            if ch != '.':
                out[(x0 + j, y0 + i)] = ch
    return out


def sleigh_team(target, x, y, z):
    """Sleigh at the back (west), two pairs of reindeer ahead (east), harness lines joining everything.
    Single voxel layer at z plus a second layer under the bodies for mass; returns the voxel list."""
    cells = {}
    cells.update(_grid(SLEIGH, x, y))                         # sleigh x .. x+16, y .. y+6
    rows_y = (y - 6, y + 5)                                   # reindeer rows (8 tall each)
    for k, rx in enumerate((x + 21, x + 38)):
        for ry in rows_y:
            cells.update(_grid(REINDEER, rx, ry))
    # harness: from the sleigh front to every reindeer, along y then x (face-connected lines)
    hx0 = x + 16
    for ry in rows_y:
        yy = ry + 5
        for xx in range(hx0, x + 52):
            cells.setdefault((xx, yy), 'h')
    for yy in range(rows_y[0] + 5, rows_y[1] + 6):
        cells.setdefault((hx0 + 1, yy), 'h')
    col = {'#': (52, 44, 50), 'r': (176, 120, 78), 'a': (96, 74, 60), 'h': (150, 120, 80), 's': (120, 40, 40),
           'g': (200, 160, 80)}
    pts = []
    for (cx, cy), ch in cells.items():
        target.set(cx, cy, z, col[ch], 'sky')
        pts.append((cx, cy, z))
        if ch in ('#', 's'):
            target.set(cx, cy, z + 1, (44, 38, 44), 'sky')
            pts.append((cx, cy, z + 1))
    return pts


def place_sky(cv):
    recs = [sky.place(cv, 'sleigh and reindeer', sleigh_team, 228, 54, 8)]
    for i, (x, y, z, L) in enumerate(((96, 150, 12, 26), (420, 156, 11, 24), (110, 382, 13, 22),
                                      (404, 376, 12, 28))):
        recs.append(sky.place(cv, f'snow cloud {i}', sky.cloud, x, y, z, L, seed=1000 + i,
                              top=(206, 208, 214), bottom=(168, 172, 190)))
    return recs
