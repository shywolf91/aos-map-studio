"""Floebreaker core: material ids, world container, noise and construction primitives.

Coordinates follow the VXL convention (x, y 0..511; z 0 = sky top, 63 = bottom/seabed). All ranges inclusive.
Terrain noise is sampled through fold(): the field is x-symmetric (x <-> 512-x) by construction, the same
mirror the Babel bases use (118 <-> 394).
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

# ------------------------------------------------------------------ materials
NAMES = ['air',
         'snow', 'ice', 'blueice', 'rock', 'pack',                       # terrain
         'hull_red', 'hull_black', 'hull_grey', 'deck', 'white', 'steel', 'dsteel',
         'orange', 'yellow', 'glass', 'plank', 'dwood', 'canvas_o', 'canvas_g', 'canvas_b',
         'drum_r', 'drum_b', 'bone', 'cont_r', 'cont_g', 'cont_b', 'cont_y', 'rubber',
         'berg_a', 'berg_b', 'berg_c', 'crystal',                         # iceberg facets + glow crystal
         'lamp', 'lamp_c', 'lamp_g',                                      # glow sources (warm / cyan / green)
         'aur_a', 'aur_b', 'aur_c', 'cloud', 'cloud_s', 'bird', 'star', 'moon',   # sky decor
         'tag']
MAT = {n: i for i, n in enumerate(NAMES)}
GLOW = {'lamp': (255, 175, 95), 'lamp_c': (95, 255, 255), 'lamp_g': (95, 255, 95)}


def sym(a):
    """Make a 512-wide (axis 0) array symmetric under x <-> 512-x using the left half."""
    a = a.copy()
    a[257:] = a[255:0:-1]
    return a


class World:
    def __init__(self, seed=7311, decor_seed=1):
        self.m = np.zeros((512, 512, 64), np.uint8)
        self.seed = seed
        self.drng = np.random.default_rng(decor_seed)     # non-deterministic decor (seed saved in build.json)
        self.lrng = np.random.default_rng(seed)           # fixed layout
        self.glow = []                                    # (x, y, z) glow source voxels (colour from material)
        self.floating = []                                # expected-floating bboxes (sky decor)
        self.marks = {}
        self.stats = {}

    # ---- primitives
    def box(self, x0, x1, y0, y1, z0, z1, mid):
        x0, x1 = sorted((int(x0), int(x1))); y0, y1 = sorted((int(y0), int(y1))); z0, z1 = sorted((int(z0), int(z1)))
        x0, y0, z0 = max(x0, 0), max(y0, 0), max(z0, 0)
        self.m[x0:x1 + 1, y0:y1 + 1, z0:z1 + 1] = MAT[mid] if isinstance(mid, str) else mid

    def carve(self, x0, x1, y0, y1, z0, z1):
        self.box(x0, x1, y0, y1, z0, z1, 0)

    def pt(self, x, y, z, mid):
        if 0 <= x < 512 and 0 <= y < 512 and 0 <= z < 64:
            self.m[x, y, z] = MAT[mid] if isinstance(mid, str) else mid
            if mid in GLOW:
                self.glow.append((int(x), int(y), int(z)))

    def room(self, x0, x1, y0, y1, zf, zc, wall):
        """Hollow room: solid shell, floor surface at zf (solid), ceiling slab at zc (solid), air between.
        zf > zc numerically (z grows downward)."""
        self.box(x0, x1, y0, y1, zc, zf, wall)
        self.carve(x0 + 1, x1 - 1, y0 + 1, y1 - 1, zc + 1, zf - 1)

    def stairs(self, a0, a1, s0, zlo, zhi, direction, mat):
        """Stair run from a lower floor (surface zlo) up to an upper floor (surface zhi < zlo), one voxel
        of rise per voxel of run. a0..a1 is the span across the run (x range for '+y'/'-y', y range for
        '+x'/'-x'); s0 is the first tread's coordinate along the run. Treads are solid down to zlo; the
        slab at zhi above the run is cut open (stairwell) so heads clear."""
        rise = zlo - zhi
        sg = 1 if direction[0] == '+' else -1
        alongy = direction[1] == 'y'
        for k in range(1, rise + 1):
            pos = s0 + sg * (k - 1)
            z = zlo - k
            if alongy:
                self.box(a0, a1, pos, pos, z, zlo, 'steel' if mat is None else mat)
                if z - 1 >= zhi:
                    self.carve(a0, a1, pos, pos, zhi, z - 1)
            else:
                self.box(pos, pos, a0, a1, z, zlo, 'steel' if mat is None else mat)
                if z - 1 >= zhi:
                    self.carve(pos, pos, a0, a1, zhi, z - 1)


# ------------------------------------------------------------------ noise
def noise(seed, sigma, shape=(512, 512), fold=True):
    """Gaussian-filtered white noise normalised to ~[-1, 1]; x-symmetric when fold=True."""
    rng = np.random.default_rng(seed)
    a = ndi.gaussian_filter(rng.standard_normal(shape), sigma, mode='wrap')
    a = (a - a.mean()) / (a.std() + 1e-9) / 2.2
    a = np.clip(a, -1, 1)
    return sym(a) if fold else a


def fbm(seed, sigmas=(48, 24, 12, 6), gains=(1, .6, .35, .2), fold=True):
    out = 0
    for i, (s, g) in enumerate(zip(sigmas, gains)):
        out = out + g * noise(seed + 101 * i, s, fold=fold)
    return out / sum(gains)


def smooth(t, a, b):
    t = np.clip((t - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


XX, YY = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
