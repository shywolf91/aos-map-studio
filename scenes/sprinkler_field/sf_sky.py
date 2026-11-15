"""Sprinkler Field floating sky decor (owner opted in 2026-11-15): 6 drifting dandelion seeds and 2 dragonflies.

Rules [USER] (aosmap.kit.sky.place enforces them): >= 60 voxels from the platform, never over a spawn square, >= 8 air
below, 2 voxels of clear air round each piece; every piece is recorded in cv.expect_floating (listed as expected
floating, excluded from the mirror check). Each piece is >= 13 voxels wide (birds narrower than ~13 vanish in fog).
Collapse caveat: a player block built against a piece and then broken drops that whole piece for the round.
"""
from __future__ import annotations

import math

from aosmap.kit import sky
from aosmap.kit.canvas import line_points

# dragonfly seen from above, head first (row 0 = front). 21 wide (wingspan), 20 long.
# E eye, H head, T thorax, A abdomen, a abdomen ring, W wing membrane, w wing edge, v vein, p pterostigma
DRAGONFLY = [
    '.........EHE.........',
    '.........EEE.........',
    '..........T..........',
    '.wwwwwwwwTTTwwwwwwww.',
    'wpWWWvWWWTTTWWWvWWWpw',
    '.wWWWvWWWTTTWWWvWWWw.',
    '..wwwwwwwTTTwwwwwww..',
    '.wwwwwwwwTTTwwwwwwww.',
    'wpWWWvWWWTTTWWWvWWWpw',
    '.wWWWWvWWTTTWWvWWWWw.',
    '...wwwwww.A.wwwwww...',
    '..........A..........',
    '..........a..........',
    '..........A..........',
    '..........A..........',
    '..........a..........',
    '..........A..........',
    '..........A..........',
    '..........a..........',
    '..........A..........',
]
assert all(len(r) == 21 for r in DRAGONFLY)
BODY = {'E', 'H', 'T', 'A', 'a'}


def dragonfly(target, x, y, z, heading, eye=(58, 108, 72)):
    """Wings 1 voxel thick at z, body 2 thick (z, z + 1). Smoky translucent-looking wings, metallic green thorax,
    teal-green banded abdomen, no saturated blue."""
    cols = {'#': (176, 182, 178), 'W': (176, 182, 178), 'w': (150, 158, 154), 'v': (138, 148, 144),
            'p': (92, 80, 60), 'E': eye, 'H': (70, 82, 60), 'T': (78, 110, 74), 'A': (66, 116, 100),
            'a': (44, 60, 54)}
    pts = sky.stamp(target, DRAGONFLY, x, y, z, heading, cols, tips_up=0)
    body = [''.join(ch if ch in BODY else '.' for ch in row) for row in DRAGONFLY]
    pts += sky.stamp(target, body, x, y, z + 1, heading, cols, tips_up=0)
    return pts


def dandelion_seed(target, x, y, z, heading, rays=12, L=7):
    """Pappus: 12 plumed rays cupped 2 upward round a hub (15 wide), a 4-voxel beak and a ribbed 2-wide achene."""
    pts = []

    def put(px, py, pz, c):
        target.set(px, py, pz, c, 'sky')
        pts.append((int(px), int(py), int(pz)))
    hub = (178, 172, 152)
    put(x, y, z, hub)
    for i in range(rays):
        a = heading + 2 * math.pi * i / rays
        ex, ey = x + L * math.cos(a), y + L * math.sin(a)
        line = line_points(x, y, z, ex, ey, z - 2)
        for k, (px, py, pz) in enumerate(line):
            r = math.hypot(px - x, py - y)
            put(px, py, pz, (206, 204, 196) if r >= L - 1.5 else (196, 196, 188))
        # plumes: side hairs near the tip, face-joined to the ray
        tx, ty, tz = line[-1]
        sx, sy = -math.sin(a), math.cos(a)
        for s in (-1, 1):
            put(int(round(tx + s * sx)), int(round(ty + s * sy)), tz, (204, 202, 194))
            # if the rounded side voxel only touches the tip diagonally, join it through the tip row
            if abs(int(round(tx + s * sx)) - tx) + abs(int(round(ty + s * sy)) - ty) == 2:
                put(int(round(tx + s * sx)), ty, tz, (204, 202, 194))
    for k in range(1, 5):                                   # beak
        put(x, y, z + k, (188, 182, 162))
    for k in range(5, 9):                                   # achene, 2 wide, ribbed
        put(x, y, z + k, (120, 100, 68) if k % 2 else (104, 86, 58))
        put(x + 1, y, z + k, (112, 94, 62) if k % 2 else (96, 80, 54))
    return pts


# (name, fn, x, y, z, args) - drift spots over open lawn, the hose and the puddles; place() searches nearby
PIECES = [
    ('dandelion seed 1', dandelion_seed, 64, 196, 30, (0.2,)),
    ('dandelion seed 2', dandelion_seed, 172, 52, 24, (1.1,)),
    ('dandelion seed 3', dandelion_seed, 318, 46, 32, (2.3,)),
    ('dandelion seed 4', dandelion_seed, 452, 214, 26, (0.7,)),
    ('dandelion seed 5', dandelion_seed, 398, 452, 30, (1.9,)),
    ('dandelion seed 6', dandelion_seed, 160, 470, 22, (2.8,)),
    ('dragonfly over the NW puddle', dragonfly, 96, 150, 30, (0.6, (58, 108, 72))),
    ('dragonfly over the SE puddle', dragonfly, 416, 362, 32, (3.6, (150, 118, 52))),
]

ALT = {   # fallback spots if a first choice has no clear room
    'dandelion seed 1': [(52, 214, 28), (40, 180, 30)],
    'dandelion seed 2': [(186, 40, 22), (150, 40, 26)],
    'dandelion seed 3': [(340, 60, 30), (300, 34, 30)],
    'dandelion seed 4': [(466, 230, 24), (470, 196, 28)],
    'dandelion seed 5': [(380, 470, 28), (420, 440, 28)],
    'dandelion seed 6': [(140, 484, 22), (182, 486, 22)],
    'dragonfly over the NW puddle': [(96, 150, 26), (110, 140, 28)],
    'dragonfly over the SE puddle': [(416, 362, 28), (400, 372, 30)],
}


def place_all(cv):
    out = []
    for (name, fn, x, y, z, args) in PIECES:
        rec = None
        for (px, py, pz) in [(x, y, z)] + ALT.get(name, []):
            try:
                rec = sky.place(cv, name, fn, px, py, pz, *args)
                break
            except RuntimeError:
                continue
        if rec is None:
            raise RuntimeError(f'sky piece {name}: no clear spot')
        r = sky.rule_check([(rec['x'][0], rec['y'][0], rec['z'][1]), (rec['x'][1], rec['y'][1], rec['z'][1])])
        rec['width'] = max(rec['x'][1] - rec['x'][0], rec['y'][1] - rec['y'][0]) + 1
        rec['platform_dist'] = r['platform_dist']
        out.append(rec)
    return out
