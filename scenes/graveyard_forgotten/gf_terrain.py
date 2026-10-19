"""SPEC (single source of truth for layout numbers) and the terrain height field.

Coordinates: x, y 0..511, z 0..63 with z = 0 the sky top. Ground height H[x, y] = z of the top voxel.
The west half (x <= 256) is authored and mirrored x' = 512 - x; all noise is sampled on folded x.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from gf_core import fbm2, fold_x

SEED = 1313
G = 44                      # basin floor: spawn yards, fronts, courtyards, cathedral floor

SPEC = {
    'G': G,
    # stock babel_script 1.4.2
    'platform': {'x': (206, 305), 'y': (240, 271), 'z': 1},
    'bases': ((118, 256), (394, 256)),
    'spawn_half': 20,
    'spawn_sq': (98, 138, 236, 276),
    # spawn churchyard (west team; east is the mirror)
    'yard_ring': (94, 142, 232, 280),            # iron railing on a stone footing, outside the spawn square
    'yard_gates': {'E': (243, 269), 'W': (250, 262), 'N': (111, 125), 'S': (111, 125)},
    'gate_tombs': ((149, 226, (0, 1)), (149, 286, (0, -1))),   # flank the front, doors face the front path
    'chapel': (64, 256),                          # spawn backdrop ossuary chapel, faces east
    'bone_gate': True,                            # vertebra arch over the front (spawn cover); False = plain pillars
    # tower zone (open courtyard, no props)
    'court': (156, 211, 222, 290),
    # cathedral (axis x = 256, nave north of the crossing, choir south)
    'parvis': (212, 256, 100, 122),
    'facade_tower': (217, 235, 122, 141),        # west tower; east mirrored
    'facade_wall_y': (136, 141),
    'nave_wall_x': (236, 239),                   # west nave wall; interior starts at 240
    'nave_y': (142, 237),
    'rib_y': (146, 220),                         # rib cage keeps >= 20 clear of the platform edge (y 240)
    'spine_z': 10,
    'crossing': (238, 274, 238, 274),            # bell-tower stump, centred on (256, 256)
    'transept': (219, 237, 244, 268),
    'choir_y': (275, 330),
    'apse': ((256, 330), 18),
    'buttress_x': (226, 229),
    # hands (placed after mirroring; cosmetic asymmetry on the axis)
    'hand_up': (256, 62),                        # reaching to the sky, on the north burial mound
    'hand_claw': (256, 438),                     # clawing out of the south crater
    'mound': ((256, 64), 28, 5),
    'crater': ((256, 438), 30, 3),
    'rim_width': 64,
    'tag_rect': (6, 176, 492, 506),
}

CORE_RECTS = [   # folded-x rectangles kept at exactly G (flat)
    (66, 162, 204, 308),         # spawn churchyard + chapel
    (140, 256, 208, 304),        # front + courtyard + transept lane
    (206, 256, 94, 378),         # cathedral precinct
]


def folded_xy():
    xs, ys = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    fx = np.minimum(xs, 512 - xs)
    return xs, ys, fx


def core_mask():
    xs, ys, fx = folded_xy()
    m = np.zeros((512, 512), bool)
    for (a, b, c, d) in CORE_RECTS:
        m |= (fx >= a) & (fx <= b) & (ys >= c) & (ys <= d)
    return m


def terrain():
    """Return float field H (z of top voxel) before pads, plus helper fields."""
    xs, ys, fx = folded_xy()
    n1 = fold_x(fbm2((512, 512), 56, 3, 'hills', SEED))
    n2 = fold_x(fbm2((512, 512), 34, 3, 'rim', SEED))
    n3 = fold_x(fbm2((512, 512), 12, 2, 'lumps', SEED))
    hills = G - 3.0 - 10.5 * (n1 - 0.3) - 1.4 * (n3 - 0.5)
    # rising rim of dead forest toward the map edges
    d = np.minimum(np.minimum(fx, ys), 511 - ys).astype(float)
    r = np.clip((SPEC['rim_width'] - d) / SPEC['rim_width'], 0, 1) ** 1.5
    hills = hills - 19 * r * (0.7 + 0.6 * n2)
    # north burial mound (reaching hand) and south crater (clawing hand)
    (mx, my), mr, mh = SPEC['mound']
    dm = np.hypot(xs - mx, ys - my) / mr
    hills = hills - mh * np.clip(1 - dm ** 2, 0, 1) ** 1.2
    (cx, cy), cr, ch = SPEC['crater']
    dc = np.hypot(xs - cx, ys - cy) / cr
    ring = np.exp(-((dc - 0.85) / 0.22) ** 2) * ch
    bowl = np.clip(1 - (dc / 0.65) ** 2, 0, 1) * 4.5
    hills = hills - ring + bowl
    core = core_mask()
    dist = ndi.distance_transform_edt(~core)
    w = np.clip(dist / 26.0, 0, 1)
    w = w * w * (3 - 2 * w)
    H = G + w * (hills - G)
    H = np.clip(np.rint(H), 14, 50).astype(int)
    H[core] = G
    return H, {'core': core, 'rim': r, 'dist_core': dist, 'n1': n1}


def pad(H, x0, x1, y0, y1, z=None, margin=2, feather=8):
    """Flatten a building pad (plus `margin`) to z (default: rounded mean of the pad) and feather the
    surrounding `feather` ring linearly back to the original terrain, so pads never leave cliffs."""
    x0m, x1m, y0m, y1m = max(x0 - margin, 0), min(x1 + margin, 511), max(y0 - margin, 0), min(y1 + margin, 511)
    if z is None:
        z = int(round(H[x0:x1 + 1, y0:y1 + 1].mean()))
    a0, a1 = max(x0m - feather, 0), min(x1m + feather, 511)
    b0, b1 = max(y0m - feather, 0), min(y1m + feather, 511)
    xs, ys = np.meshgrid(np.arange(a0, a1 + 1), np.arange(b0, b1 + 1), indexing='ij')
    dx = np.maximum(np.maximum(x0m - xs, xs - x1m), 0)
    dy = np.maximum(np.maximum(y0m - ys, ys - y1m), 0)
    d = np.maximum(dx, dy).astype(float)
    t = np.clip(d / (feather + 1), 0, 1)
    sub = H[a0:a1 + 1, b0:b1 + 1]
    H[a0:a1 + 1, b0:b1 + 1] = np.rint(z * (1 - t) + sub * t).astype(int)
    return z
