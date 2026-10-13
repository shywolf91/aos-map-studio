"""Material-based voxel scene: geometry (material ids) is authored separately from colouring.

Coordinates follow the VXL convention: x, y in 0..511, z in 0..63 with z = 0 at the TOP.
All box ranges are INCLUSIVE on both ends to match how map coordinates are written in metadata.
Helper `ground(z_top)` style is deliberately avoided: you always state z ranges explicitly, top
(smaller z) first, so "up" mistakes are visible in code review.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

import numpy as np

from .vxl import VoxelMap, rgb, surface_mask, MAP_X, MAP_Y, MAP_Z


@dataclass
class Material:
    name: str
    base: tuple                     # (r, g, b)
    jitter: int = 0                 # +- per-channel deterministic variation (keep small: no noise)
    top: tuple | None = None        # colour for voxels exposed to the sky directly above
    depth_ramp: float = 0.0         # darken per voxel below the column's local top (0 = off)
    shader: object = None           # optional callable(ctx) -> float (N, 3) RGB; see aosmap/art.py


@dataclass
class Scene:
    name: str
    seed: int = 0
    mat: np.ndarray = field(default_factory=lambda: np.zeros((MAP_X, MAP_Y, MAP_Z), np.uint8))
    materials: dict = field(default_factory=dict)       # id -> Material
    _ids: dict = field(default_factory=dict)            # name -> id
    markers: dict = field(default_factory=dict)         # free-form named points for metadata/tests
    bottom_rgb: np.ndarray | None = None                # optional 512x512x3 backdrop for the z=63 plane

    def paint_bottom(self, rgb_xy):
        """Paint the z = 63 water plane as a full 512x512 canvas (indexed [x, y, rgb]).
        Purely visual: players in water stand at the bottom, and water_damage applies at z >= 61.
        Technique observed in Cloud Smash (27,994 of 28,109 colours live on its bottom plane)."""
        a = np.asarray(rgb_xy, np.uint8)
        if a.shape != (MAP_X, MAP_Y, 3):
            raise ValueError('bottom image must be 512 x 512 x 3, indexed [x, y]')
        self.bottom_rgb = a

    def material(self, m: Material) -> int:
        if m.name in self._ids:
            return self._ids[m.name]
        mid = len(self._ids) + 1
        if mid > 255:
            raise ValueError('too many materials')
        self._ids[m.name] = mid
        self.materials[mid] = m
        return mid

    # ---- geometry primitives (inclusive ranges) -------------------------------------
    def box(self, x0, x1, y0, y1, z0, z1, mid):
        x0, x1 = sorted((x0, x1)); y0, y1 = sorted((y0, y1)); z0, z1 = sorted((z0, z1))
        self.mat[x0:x1 + 1, y0:y1 + 1, z0:z1 + 1] = mid

    def carve(self, x0, x1, y0, y1, z0, z1):
        self.box(x0, x1, y0, y1, z0, z1, 0)

    def hollow_box(self, x0, x1, y0, y1, z0, z1, mid):
        self.box(x0, x1, y0, y1, z0, z1, mid)
        self.carve(x0 + 1, x1 - 1, y0 + 1, y1 - 1, z0 + 1, z1 - 1)

    def point(self, x, y, z, mid):
        self.mat[x, y, z] = mid

    @property
    def solid(self):
        return self.mat > 0

    # ---- colouring --------------------------------------------------------------------
    def _hash_noise(self, shape_xyz, salt):
        """Deterministic per-voxel integer noise in [-1, 1], from seed + salt (no global RNG)."""
        h = hashlib.sha256(f'{self.seed}:{salt}'.encode()).digest()
        rng = np.random.default_rng(int.from_bytes(h[:8], 'little'))
        return rng.integers(-1, 2, size=shape_xyz, dtype=np.int16)

    def to_voxelmap(self) -> VoxelMap:
        solid = self.solid.copy()
        solid[:, :, 63] = True                              # bottom/water plane always solid
        surf = surface_mask(solid)
        sky_open = np.zeros_like(solid)                     # voxel whose z-1 is air (or z == 0)
        sky_open[:, :, 0] = solid[:, :, 0]
        sky_open[:, :, 1:] = solid[:, :, 1:] & ~solid[:, :, :-1]
        # depth below the nearest air above, per voxel (for ramps)
        depth = np.zeros(solid.shape, np.int16)
        run = np.zeros(solid.shape[:2], np.int16)
        for z in range(MAP_Z):
            run = np.where(solid[:, :, z], run + 1, 0)
            depth[:, :, z] = run - 1
        vm = VoxelMap(solid=solid)
        color = np.zeros(solid.shape, np.uint32)
        occ = None
        if any(m.shader is not None for m in self.materials.values()):
            from scipy import ndimage
            occ = ndimage.uniform_filter(solid.astype(np.float32), size=3, mode='constant', cval=1.0)
            air_below = np.zeros_like(solid)
            air_below[:, :, :-1] = solid[:, :, :-1] & ~solid[:, :, 1:]
        for mid, m in self.materials.items():
            sel = surf & (self.mat == mid)
            if not sel.any():
                continue
            if m.shader is not None:
                x, y, z = np.nonzero(sel)
                ctx = {'x': x, 'y': y, 'z': z, 'top': sky_open[x, y, z], 'under': air_below[x, y, z],
                       'depth': depth[x, y, z], 'occ': occ[x, y, z], 'seed': self.seed, 'name': m.name}
                c = np.clip(np.rint(m.shader(ctx)), 0, 255).astype(np.uint32)
                color[x, y, z] = (np.uint32(0x80) << 24) | (c[:, 0] << 16) | (c[:, 1] << 8) | c[:, 2]
                continue
            base = np.array(m.base, np.int16)
            r = np.full(sel.sum(), base[0]); g = np.full(sel.sum(), base[1]); b = np.full(sel.sum(), base[2])
            if m.top is not None:
                t = sky_open[sel]
                r = np.where(t, m.top[0], r); g = np.where(t, m.top[1], g); b = np.where(t, m.top[2], b)
            if m.depth_ramp:
                f = np.clip(1.0 - m.depth_ramp * depth[sel], 0.55, 1.0)
                r, g, b = (r * f).astype(np.int16), (g * f).astype(np.int16), (b * f).astype(np.int16)
            if m.jitter:
                n = self._hash_noise(sel.sum(), m.name) * m.jitter
                r, g, b = r + n, g + n, b + n               # value-only jitter keeps hue coherent
            r, g, b = (np.clip(c, 0, 255).astype(np.uint32) for c in (r, g, b))
            color[sel] = (np.uint32(0x80) << 24) | (r << 16) | (g << 8) | b
        # bottom plane colour where the scene left z = 63 unassigned
        water = surf[:, :, 63] & (self.mat[:, :, 63] == 0)
        if self.bottom_rgb is None:
            color[:, :, 63][water] = rgb(*WATER_RGB)
        else:
            b = self.bottom_rgb.astype(np.uint32)
            painted = (np.uint32(0x80) << 24) | (b[..., 0] << 16) | (b[..., 1] << 8) | b[..., 2]
            color[:, :, 63][water] = painted[water]
        vm.color = color
        vm.colored = surf.copy()
        return vm


WATER_RGB = (38, 92, 120)
