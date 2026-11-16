"""Canvas: the world a generator paints into.

Merges Bloomhop's geo.World (solid + rgb arrays, box/ellipsoid with colour functions, glow + expected-floating
lists), the material grids of gf/hc/wkh/sph (mat.npy, used for mirror and floating reports) and the shared
poly_mask / line helpers of gf/hc/wkh_build and ds_core.

Conventions: arrays [x, y, z]; z = 0 is the sky top, z = 63 the bottom; boxes are inclusive.
A colour argument `c` is an (r, g, b) tuple or a function (xs, ys, zs) -> (n, 3) array.
"""
from __future__ import annotations

import math

import numpy as np

from .params import MX, MY, MZ


def _poly_mask_np(poly, shape=(MX, MY)):
    """Even-odd point-in-polygon on the cell centres of an [x, y] grid (pure numpy)."""
    xs, ys = np.meshgrid(np.arange(shape[0]) + 0.5, np.arange(shape[1]) + 0.5, indexing='ij')
    inside = np.zeros(shape, bool)
    p = list(poly)
    for (x0, y0), (x1, y1) in zip(p, p[1:] + p[:1]):
        if y0 == y1:
            continue
        cond = (ys >= min(y0, y1)) & (ys < max(y0, y1))
        xint = x0 + (ys - y0) * (x1 - x0) / (y1 - y0)
        inside ^= cond & (xs < xint)
    return inside


def poly_mask(poly, shape=(MX, MY)):
    """Boolean [x, y] mask of a polygon given as [(x, y), ...]."""
    return _poly_mask_np(poly, shape)


def disc_mask(cx, cy, r, shape=(MX, MY)):
    xs, ys = np.meshgrid(np.arange(shape[0]), np.arange(shape[1]), indexing='ij')
    return (xs - cx) ** 2 + (ys - cy) ** 2 <= r * r


def line_points(x0, y0, z0, x1, y1, z1):
    """Voxels on a 3D line, face-connected (every step changes one axis), so lines never float on diagonals."""
    pts = [(int(round(x0)), int(round(y0)), int(round(z0)))]
    n = int(max(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))) * 2 + 1
    for i in range(1, n + 1):
        t = i / n
        q = (int(round(x0 + (x1 - x0) * t)), int(round(y0 + (y1 - y0) * t)), int(round(z0 + (z1 - z0) * t)))
        last = pts[-1]
        while last != q:                      # walk one axis at a time -> face contact
            for a in range(3):
                if last[a] != q[a]:
                    step = list(last)
                    step[a] += 1 if q[a] > last[a] else -1
                    last = tuple(step)
                    pts.append(last)
                    break
    return pts


class Canvas:
    def __init__(self, name: str = 'map'):
        self.name = name
        self.solid = np.zeros((MX, MY, MZ), bool)
        self.rgb = np.zeros((MX, MY, MZ, 3), np.uint8)
        self.mat = np.zeros((MX, MY, MZ), np.uint16)     # 0 = untagged
        self.H = np.full((MX, MY), 63, np.int16)          # terrain top z per column
        self.keep = np.zeros((MX, MY), np.uint8)          # no-prop flags (spawn squares, anchors, walkways ...)
        self.nolight = np.zeros((MX, MY, MZ), bool)       # skip in the lighting pass (glow sources)
        self.glow = []                                     # (x, y, z, rgb) glow sources
        self.expect_floating = []                          # intentional floating pieces: dicts name/x/y/z ranges
        self.interiors = []                                # [name, x, y, floor_z] for the interiors check
        self.materials = {'air': 0}

    # ------------------------------------------------------------------ materials
    def material(self, name: str) -> int:
        if name not in self.materials:
            self.materials[name] = len(self.materials)
        return self.materials[name]

    def _m(self, mat):
        if mat is None:
            return 0
        return self.material(mat) if isinstance(mat, str) else int(mat)

    # ------------------------------------------------------------------ voxels
    def inside(self, x, y, z):
        return 0 <= x < MX and 0 <= y < MY and 0 <= z < MZ

    def set(self, x, y, z, c, mat=None):
        if self.inside(x, y, z):
            self.solid[x, y, z] = True
            self.rgb[x, y, z] = c
            self.mat[x, y, z] = self._m(mat)

    def clear(self, x, y, z):
        if self.inside(x, y, z):
            self.solid[x, y, z] = False
            self.mat[x, y, z] = 0

    def get(self, x, y, z):
        return bool(self.solid[x, y, z]) if self.inside(x, y, z) else z >= MZ

    def _clip(self, x0, x1, y0, y1, z0, z1):
        x0, x1 = max(0, min(x0, x1)), min(MX - 1, max(x0, x1))
        y0, y1 = max(0, min(y0, y1)), min(MY - 1, max(y0, y1))
        z0, z1 = max(0, min(z0, z1)), min(MZ - 1, max(z0, z1))
        if x0 > x1 or y0 > y1 or z0 > z1:
            return None
        return (slice(x0, x1 + 1), slice(y0, y1 + 1), slice(z0, z1 + 1))

    def fill_mask(self, m, c, mat=None, origin=(0, 0, 0)):
        """Fill a boolean mask (full-size, or a sub-block placed at origin)."""
        if m.shape != self.solid.shape:
            x0, y0, z0 = origin
            sl = self._clip(x0, x0 + m.shape[0] - 1, y0, y0 + m.shape[1] - 1, z0, z0 + m.shape[2] - 1)
            if sl is None:
                return
            m = m[:sl[0].stop - sl[0].start, :sl[1].stop - sl[1].start, :sl[2].stop - sl[2].start]
            sub_s, sub_c, sub_m = self.solid[sl], self.rgb[sl], self.mat[sl]
            sub_s[m] = True
            if callable(c):
                xs, ys, zs = np.nonzero(m)
                sub_c[m] = c(xs + sl[0].start, ys + sl[1].start, zs + sl[2].start)
            else:
                sub_c[m] = c
            sub_m[m] = self._m(mat)
            return
        self.solid[m] = True
        if callable(c):
            xs, ys, zs = np.nonzero(m)
            self.rgb[m] = c(xs, ys, zs)
        else:
            self.rgb[m] = c
        self.mat[m] = self._m(mat)

    def box(self, x0, x1, y0, y1, z0, z1, c=None, mat=None, air=False):
        sl = self._clip(x0, x1, y0, y1, z0, z1)
        if sl is None:
            return
        if air:
            self.solid[sl] = False
            self.mat[sl] = 0
            return
        self.solid[sl] = True
        if callable(c):
            xs, ys, zs = np.meshgrid(np.arange(sl[0].start, sl[0].stop), np.arange(sl[1].start, sl[1].stop),
                                     np.arange(sl[2].start, sl[2].stop), indexing='ij')
            self.rgb[sl] = c(xs.ravel(), ys.ravel(), zs.ravel()).reshape(xs.shape + (3,))
        elif c is not None:
            self.rgb[sl] = c
        self.mat[sl] = self._m(mat)

    def carve(self, x0, x1, y0, y1, z0, z1):
        self.box(x0, x1, y0, y1, z0, z1, air=True)

    def hollow_box(self, x0, x1, y0, y1, z0, z1, c, mat=None, wall=1, floor=True, roof=True):
        """Walls of thickness `wall`; z0 is the top (roof) and z1 the floor slab (z grows downward)."""
        self.box(x0, x1, y0, y1, z0, z1, c, mat)
        self.carve(x0 + wall, x1 - wall, y0 + wall, y1 - wall,
                   z0 + (wall if roof else 0), z1 - (wall if floor else 0))

    def cylinder(self, cx, cy, r, z0, z1, c, mat=None, hollow=0.0):
        sl = self._clip(int(cx - r - 1), int(cx + r + 1), int(cy - r - 1), int(cy + r + 1), z0, z1)
        if sl is None:
            return
        xs, ys = np.meshgrid(np.arange(sl[0].start, sl[0].stop), np.arange(sl[1].start, sl[1].stop), indexing='ij')
        d = np.hypot(xs + 0.5 - cx, ys + 0.5 - cy)
        m2 = (d <= r) & (d >= hollow) if hollow else d <= r
        m = np.repeat(m2[:, :, None], sl[2].stop - sl[2].start, axis=2)
        self.fill_mask(m, c, mat, origin=(sl[0].start, sl[1].start, sl[2].start))

    def cone(self, cx, cy, r_base, z_base, z_tip, c, mat=None):
        """Cone from radius r_base at z_base up to a point at z_tip (z_tip < z_base)."""
        h = max(1, z_base - z_tip)
        for z in range(z_tip, z_base + 1):
            r = r_base * (z - z_tip) / h + 0.5
            self.cylinder(cx, cy, r, z, z, c, mat)

    def ellipsoid(self, cx, cy, cz, rx, ry, rz, c, mat=None, hollow=0.0):
        sl = self._clip(int(math.floor(cx - rx)), int(math.ceil(cx + rx)), int(math.floor(cy - ry)),
                        int(math.ceil(cy + ry)), int(math.floor(cz - rz)), int(math.ceil(cz + rz)))
        if sl is None:
            return None
        xs, ys, zs = np.meshgrid(np.arange(sl[0].start, sl[0].stop), np.arange(sl[1].start, sl[1].stop),
                                 np.arange(sl[2].start, sl[2].stop), indexing='ij')
        d = ((xs - cx) / max(rx, .5)) ** 2 + ((ys - cy) / max(ry, .5)) ** 2 + ((zs - cz) / max(rz, .5)) ** 2
        m = d <= 1.0
        if hollow > 0:
            m &= d >= hollow
        self.fill_mask(m, c, mat, origin=(sl[0].start, sl[1].start, sl[2].start))
        return m

    def line(self, p0, p1, c, mat=None, width=1):
        for (x, y, z) in line_points(*p0, *p1):
            for dx in range(width):
                for dy in range(width):
                    self.set(x + dx, y + dy, z, c, mat)

    # ------------------------------------------------------------------ terrain
    def column_top(self, x, y, zmin=0):
        col = self.solid[x, y, zmin:]
        i = int(np.argmax(col))
        return zmin + i if col[i] else MZ

    def tops(self):
        return np.argmax(self.solid, axis=2)

    def fill_terrain(self, H, c, mat='ground'):
        """Solid from H[x, y] down to z = 63 (owner rule: ground is solid all the way down)."""
        H = np.clip(np.asarray(H, int), 0, 63)
        self.H = H.astype(np.int16)
        zz = np.arange(MZ)[None, None, :]
        m = zz >= H[:, :, None]
        self.fill_mask(m, c, mat)

    def no_prop(self, x0, x1, y0, y1, flag=1):
        self.keep[max(0, x0):x1 + 1, max(0, y0):y1 + 1] |= flag

    def add_glow(self, x, y, z, c):
        self.set(x, y, z, c)
        self.glow.append((int(x), int(y), int(z), tuple(int(v) for v in c)))
        self.nolight[x, y, z] = True

    def expect(self, name, x0, x1, y0, y1, z0, z1):
        self.expect_floating.append({'name': name, 'x': [x0, x1], 'y': [y0, y1], 'z': [z0, z1]})

    # ------------------------------------------------------------------ export
    def packed(self):
        from .codec import pack_rgb
        return pack_rgb(self.rgb)

    def to_vxl(self) -> bytes:
        from .codec import encode
        return encode(self.solid, self.rgb)
