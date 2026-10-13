"""Art kit: deterministic noise, colour ramps, surface shaders, terrain and parametric props.

Calibration targets measured from the user's reference maps (tools/art_metrics.py, 2026-10-12):
  * 2-4 hue families per map (references: 2-5)
  * spatial coherence of top colours >= 1.5 (references 1.4-2.5; per-voxel jitter = 1.0)
  * side faces 10-20 L* darker than tops (most references -5 to -34)
  * either fine gradients (steps ~1-2 L*) or deliberate flat patches with bold steps (~3-11 L*)
All generators are generic and original; nothing is sampled from reference maps.

Coordinates: x, y 0..511, z 0..63 with z = 0 the sky. A prefab's local k axis points UP
(k = 0 is its lowest layer); Scene.stamp converts.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# ------------------------------------------------------------------ deterministic noise

def _hash(ix, iy, iz, seed):
    h = (ix.astype(np.uint32) * np.uint32(0x8DA6B343) ^ iy.astype(np.uint32) * np.uint32(0xD8163841)
         ^ iz.astype(np.uint32) * np.uint32(0xCB1AB31F) ^ np.uint32(seed * 0x9E3779B1 & 0xFFFFFFFF))
    h ^= h >> np.uint32(13); h *= np.uint32(0x5BD1E995); h ^= h >> np.uint32(15)
    return (h & np.uint32(0xFFFFFF)).astype(np.float32) / float(0xFFFFFF)          # [0, 1)


def value_noise(x, y, z=None, scale=8.0, seed=0):
    """Smooth lattice value noise in [0, 1] at arbitrary (float) points. Trilinear + smoothstep."""
    x = np.asarray(x, np.float32) / scale; y = np.asarray(y, np.float32) / scale
    z = np.zeros_like(x) if z is None else np.asarray(z, np.float32) / scale
    xi, yi, zi = np.floor(x), np.floor(y), np.floor(z)
    fx, fy, fz = x - xi, y - yi, z - zi
    fx, fy, fz = (f * f * (3 - 2 * f) for f in (fx, fy, fz))
    xi, yi, zi = xi.astype(np.int64), yi.astype(np.int64), zi.astype(np.int64)
    acc = 0.0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (fx if dx else 1 - fx) * (fy if dy else 1 - fy) * (fz if dz else 1 - fz)
                acc = acc + w * _hash(xi + dx, yi + dy, zi + dz, seed)
    return acc


def fbm(x, y, z=None, scale=32.0, octaves=4, seed=0, gain=0.5):
    """Fractal sum of value noise, normalised to ~[0, 1]."""
    tot, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        tot = tot + amp * value_noise(x, y, z, scale / (2 ** o), seed + 101 * o)
        norm += amp; amp *= gain
    return tot / norm


# ------------------------------------------------------------------ colour

def hex_rgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32)


def ramp(stops, t, steps=None):
    """stops: list of '#rrggbb' (evenly spaced) ; t in [0, 1] array. Interpolates in linear light.
    steps: quantise t to N levels for a deliberate flat, hand-painted look."""
    t = np.clip(np.asarray(t, np.float32), 0, 1)
    if steps:
        t = np.floor(t * steps) / max(steps - 1, 1)
        t = np.clip(t, 0, 1)
    cols = np.stack([hex_rgb(s) for s in stops]) / 255.0
    lin = np.where(cols <= 0.04045, cols / 12.92, ((cols + 0.055) / 1.055) ** 2.4)
    pos = t * (len(stops) - 1)
    i0 = np.clip(np.floor(pos).astype(int), 0, len(stops) - 1)
    i1 = np.clip(i0 + 1, 0, len(stops) - 1)
    f = (pos - i0)[..., None]
    c = lin[i0] * (1 - f) + lin[i1] * f
    c = np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.power(np.maximum(c, 0), 1 / 2.4) - 0.055)
    return c * 255.0


@dataclass
class SurfaceShader:
    """Callable colouring rule for a Scene Material (Material(shader=...)).

    t = height term + coherent noise term, mapped through the top ramp (top faces) or the side ramp.
    """
    top: list                        # ramp stops for faces open to the sky
    side: list | None = None         # ramp stops for side faces (default: top ramp darkened)
    side_dark: float = 0.80          # multiplier when side ramp is None
    under_dark: float = 0.62         # undersides / overhang ceilings
    z_range: tuple = (63, 0)         # z mapped to t = 0 .. 1 (default: bottom -> sky)
    height_w: float = 0.5            # weight of the height term in t
    noise_scale: float = 12.0        # voxels; coherent variation (NOT per-voxel jitter)
    noise_w: float = 0.5
    noise_3d: bool = True
    occ_dark: float = 0.35           # crevice darkening strength (baked AO)
    steps: int | None = None         # quantise for flat painted style
    seed_salt: int = 0

    def __call__(self, ctx):
        x, y, z = ctx['x'], ctx['y'], ctx['z']
        z0, z1 = self.z_range
        th = np.clip((z0 - z) / max(z0 - z1, 1), 0, 1)
        n = fbm(x, y, z if self.noise_3d else None, scale=self.noise_scale, octaves=3,
                seed=ctx['seed'] * 31 + self.seed_salt + hash(ctx['name']) % 997)
        t = self.height_w * th + self.noise_w * n
        t = t / max(self.height_w + self.noise_w, 1e-6)
        top = ramp(self.top, t, self.steps)
        if self.side is not None:
            sidec = ramp(self.side, t, self.steps)
        else:
            sidec = top * self.side_dark
        c = np.where(ctx['top'][:, None], top, sidec)
        c = np.where(ctx['under'][:, None] & ~ctx['top'][:, None], c * self.under_dark, c)
        occ = np.clip((ctx['occ'] - 0.5) / 0.5, 0, 1)       # 0 on convex edges, 1 deep in crevices
        c = c * (1 - self.occ_dark * occ)[:, None]
        return c


# ------------------------------------------------------------------ terrain

def heightfield(seed, base_z=50, amp=10, scale=96, octaves=5, terrace=None, mask=None,
                region=(0, 0, 511, 511), shore_z=None, terrace_cover=0.55):
    """Return int array H[x, y] = top-surface z (z-down, so smaller = higher).
    mask:   optional float [0, 1] (512, 512) - 0 at the shore, 1 inland. Scales the relief and,
            with shore_z, ramps the ground from shore_z (near water) up to base_z inland.
    terrace: voxels per step -> stepped contours, applied only in noise-chosen patches
            (terrace_cover = fraction of land) so slopes alternate between terraces and natural
            voxel staircases instead of a uniform contour-map look."""
    xs, ys = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    n = fbm(xs, ys, None, scale=scale, octaves=octaves, seed=seed)
    n = (n - n.min()) / max(n.max() - n.min(), 1e-6)
    m = np.ones_like(n) if mask is None else mask
    h = n * amp * m
    if terrace:
        wobble = (fbm(xs, ys, None, scale=10, octaves=2, seed=seed + 7) - 0.5) * terrace * 0.8
        ht = np.floor((h + wobble) / terrace) * terrace
        patch = fbm(xs, ys, None, scale=70, octaves=2, seed=seed + 11)
        thr = np.quantile(patch, 1 - terrace_cover)
        w = np.clip((patch - thr) / 0.04 + 0.5, 0, 1)
        h = h * (1 - w) + ht * w
    z = base_z - h
    if shore_z is not None:
        sm = m * m * (3 - 2 * m)                                   # smoothstep
        z = z + (shore_z - base_z) * (1 - sm)
    return np.clip(np.rint(z), 1, 62).astype(np.int16)


def apply_heightfield(scene, H, top_mid, sub_mid, deep_mid, sub_depth=3, cliff_mid=None, cliff_slope=3,
                      region=None):
    """Fill columns from H down to z = 62 (always grounded). Steep columns get cliff_mid on top."""
    x0, y0, x1, y1 = region or (0, 0, 511, 511)
    Hs = H[x0:x1 + 1, y0:y1 + 1].astype(int)
    zz = np.arange(64)[None, None, :]
    filled = zz >= Hs[..., None]
    filled[..., 63] = False                                     # leave z=63 to the water plane logic
    mids = np.where(zz < Hs[..., None] + sub_depth, sub_mid, deep_mid).astype(np.uint8)
    mids = np.where(zz == Hs[..., None], top_mid, mids)
    if cliff_mid is not None:
        gx = np.abs(np.diff(Hs, axis=0, append=Hs[-1:, :])); gy = np.abs(np.diff(Hs, axis=1, append=Hs[:, -1:]))
        gx2 = np.abs(np.diff(Hs, axis=0, prepend=Hs[:1, :])); gy2 = np.abs(np.diff(Hs, axis=1, prepend=Hs[:, :1]))
        steep = np.maximum.reduce([gx, gy, gx2, gy2]) >= cliff_slope
        cliff = steep[..., None] & (zz < Hs[..., None] + 6) & (zz >= Hs[..., None])
        mids = np.where(cliff, cliff_mid, mids)
    sub = scene.mat[x0:x1 + 1, y0:y1 + 1, :]
    sub[filled] = mids[filled]
    scene.mat[x0:x1 + 1, y0:y1 + 1, :] = sub


# ------------------------------------------------------------------ prefabs (local k axis = UP)

class Prefab:
    """Small voxel object. a[i, j, k] = material id (0 = empty), k = 0 is the lowest layer.
    origin = (ox, oy): the cell placed over the stamp point."""

    def __init__(self, a, origin=None, name=''):
        self.a = a
        self.origin = origin if origin is not None else (a.shape[0] // 2, a.shape[1] // 2)
        self.name = name


def stamp(scene, pf: Prefab, x, y, floor_z, replace_air_only=False):
    """Place prefab so that its k = 0 layer sits directly ON the voxel floor_z (i.e. at z = floor_z-1)."""
    a = pf.a
    ox, oy = pf.origin
    for k in range(a.shape[2]):
        z = floor_z - 1 - k
        if z < 0:
            break
        layer = a[:, :, k]
        ii, jj = np.nonzero(layer)
        X = x - ox + ii; Y = y - oy + jj
        ok = (X >= 0) & (X < 512) & (Y >= 0) & (Y < 512)
        X, Y, mids = X[ok], Y[ok], layer[ii[ok], jj[ok]]
        if replace_air_only:
            free = scene.mat[X, Y, z] == 0
            X, Y, mids = X[free], Y[free], mids[free]
        scene.mat[X, Y, z] = mids


def tree(seed, trunk_mid, leaf_mid, height=9, crown_r=4.5, crown_h=6, lean=0.0):
    """Original broadleaf tree: tapered trunk, 2-3 branches, lumpy crown from overlapping noise
    blobs. Everything is face-connected (crown touches branch/trunk tips)."""
    rng = np.random.default_rng(seed)
    R = int(np.ceil(crown_r)) + 3
    H = height + crown_h + 2
    a = np.zeros((2 * R + 1, 2 * R + 1, H), np.uint8)
    c = R
    tx, ty = float(c), float(c)
    prev = None
    for k in range(height):
        w = 1 if k > height * 0.45 else 2
        ix, iy = int(round(tx)), int(round(ty))
        a[ix:ix + w, iy:iy + w, k] = trunk_mid
        if prev is not None and prev != (ix, iy):
            a[prev[0], prev[1], k] = trunk_mid          # keep a face contact when the trunk shifts
        prev = (ix, iy)
        tx += lean * 0.15
    tips = [(int(round(tx)), int(round(ty)), height - 1)]
    for b in range(rng.integers(2, 4)):
        ang = rng.uniform(0, 2 * np.pi); L = rng.integers(2, 4); k0 = int(height * rng.uniform(0.55, 0.85))
        bx, by = int(round(tx)), int(round(ty))
        for s in range(1, L + 1):
            nx, ny, nk = bx + int(round(np.cos(ang) * s)), by + int(round(np.sin(ang) * s)), k0 + s // 2
            px, py, pk = bx + int(round(np.cos(ang) * (s - 1))), by + int(round(np.sin(ang) * (s - 1))), k0 + (s - 1) // 2
            a[nx, py, pk] = trunk_mid                            # L-step keeps face connectivity
            a[nx, ny, nk] = trunk_mid
            a[nx, ny, pk] = trunk_mid
        tips.append((nx, ny, nk))
    ii, jj, kk = np.meshgrid(np.arange(a.shape[0]), np.arange(a.shape[1]), np.arange(H), indexing='ij')
    crown = np.zeros(a.shape, bool)
    for (bx, by, bk) in tips:
        r = crown_r * rng.uniform(0.65, 0.9)
        d = np.sqrt((ii - bx) ** 2 + (jj - by) ** 2 + ((kk - bk - crown_h * 0.35) * 1.35) ** 2)
        n = value_noise(ii, jj, kk, scale=2.5, seed=seed + bx * 7 + by) - 0.5
        crown |= d + n * 2.2 < r
    for (bx, by, bk) in tips:                                   # anchor: leaves always wrap each tip
        d0 = np.sqrt((ii - bx) ** 2 + (jj - by) ** 2 + ((kk - bk - 1) * 1.2) ** 2)
        crown |= d0 <= 1.9
    leaf = crown & (a == 0)
    a[leaf] = leaf_mid
    # keep only parts face-connected to the trunk base (no floating leaf clumps)
    from scipy import ndimage
    lab, _ = ndimage.label(a > 0, structure=ndimage.generate_binary_structure(3, 1))
    base = lab[:, :, 0][lab[:, :, 0] > 0]
    keep = np.isin(lab, np.unique(base))
    a[~keep] = 0
    k_used = np.nonzero(a.any(axis=(0, 1)))[0]
    return Prefab(a[:, :, :k_used.max() + 1], origin=(c, c), name='tree')


def boulder(seed, mid, r=3.0, squash=0.7):
    R = int(np.ceil(r)) + 2
    ii, jj, kk = np.meshgrid(np.arange(2 * R + 1), np.arange(2 * R + 1), np.arange(2 * R + 1), indexing='ij')
    d = np.sqrt((ii - R) ** 2 + (jj - R) ** 2 + ((kk - 1) / squash) ** 2)
    n = value_noise(ii, jj, kk, scale=2.2, seed=seed) - 0.5
    a = np.where(d + n * 2.0 < r, mid, 0).astype(np.uint8)
    a[R - 1:R + 2, R - 1:R + 2, 0] = mid                       # flat seat on the ground
    k_used = np.nonzero(a.any(axis=(0, 1)))[0]
    return Prefab(a[:, :, :k_used.max() + 1], origin=(R, R), name='boulder')


def house(seed, wall_mid, roof_mid, trim_mid, w=9, d=7, wall_h=5, door=True, window_mid=None):
    """Gabled house: plinth trim, walls with window holes (or window_mid panes), door gap,
    roof with 1-voxel eave overhang along the gable sides. Interior hollow."""
    rng = np.random.default_rng(seed)
    rh = (d + 2) // 2 + 1
    a = np.zeros((w + 2, d + 2, wall_h + rh + 1), np.uint8)
    W0, D0 = 1, 1
    a[W0:W0 + w, D0:D0 + d, 0] = trim_mid                       # plinth / floor
    for k in range(1, wall_h + 1):
        a[W0:W0 + w, D0:D0 + d, k] = wall_mid
        a[W0 + 1:W0 + w - 1, D0 + 1:D0 + d - 1, k] = 0
    a[W0, D0, 1:wall_h + 1] = trim_mid; a[W0 + w - 1, D0, 1:wall_h + 1] = trim_mid   # corner posts
    a[W0, D0 + d - 1, 1:wall_h + 1] = trim_mid; a[W0 + w - 1, D0 + d - 1, 1:wall_h + 1] = trim_mid
    a[W0:W0 + w, D0:D0 + d, wall_h] = np.where(a[W0:W0 + w, D0:D0 + d, wall_h] > 0, trim_mid, 0)  # top band
    for wx in range(W0 + 2, W0 + w - 2, 3):                     # windows on long sides
        for side in (D0, D0 + d - 1):
            a[wx, side, 2:4] = window_mid if window_mid else 0
    if door:
        dx = W0 + w // 2
        a[dx, D0, 1:4] = 0
    for k in range(rh):                                         # gable roof along x, eaves overhang
        y_lo, y_hi = k, d + 1 - k
        if y_lo > y_hi:
            break
        kk = wall_h + 1 + k
        a[0:w + 2, y_lo, kk] = roof_mid; a[0:w + 2, y_hi, kk] = roof_mid
        if k < rh - 1:
            a[W0, y_lo + 1:y_hi, kk] = wall_mid; a[W0 + w - 1, y_lo + 1:y_hi, kk] = wall_mid  # gable ends
        else:
            a[0:w + 2, y_lo:y_hi + 1, kk] = roof_mid               # ridge
    # eave ends must be supported: hang a trim beam under the overhang ends onto the corner posts
    a[0, D0:D0 + d, wall_h] = trim_mid; a[w + 1, D0:D0 + d, wall_h] = trim_mid
    k_used = np.nonzero(a.any(axis=(0, 1)))[0]
    return Prefab(a[:, :, :k_used.max() + 1], origin=((w + 2) // 2, (d + 2) // 2), name='house')


def stairs(mid, rise, width=3, run=1, direction='+x'):
    """Straight stair of 1-voxel risers (auto-climbable). Solid underneath (grounded, no gaps)."""
    L = rise * run
    a = np.zeros((L, width, rise), np.uint8)
    for s in range(rise):
        a[s * run:(s + 1) * run, :, :s + 1] = mid
    if direction == '-x':
        a = a[::-1]
    elif direction in ('+y', '-y'):
        a = a.transpose(1, 0, 2)
        if direction == '-y':
            a = a[:, ::-1]
    return Prefab(a, origin=(0, 0), name='stairs')


@dataclass
class StrataShader:
    """Banded sedimentary rock. Bands follow z (warped by smooth noise and a slight tilt) so cliffs
    read as horizontal strata; tops get a dusty crust, sides carry vertical desert-varnish streaks,
    undersides and crevices darken. Spatially coherent by construction (no per-voxel noise)."""
    palette: list                    # band colours, top -> bottom order is irrelevant (cycled)
    pattern: tuple = (3, 2, 4, 1, 3, 2, 5, 2)   # band thicknesses in voxels, cycled
    warp: float = 2.2                # voxels of wavy band offset
    warp_scale: float = 34.0
    tilt: tuple = (0.012, 0.006)     # dz per voxel in x, y (gentle dip)
    crust: str | None = '#d8bf98'    # top-face dust colour (None = keep band colour)
    crust_mix: float = 0.55
    side_dark: float = 0.86
    under_dark: float = 0.6
    streak: float = 0.16             # strength of vertical varnish streaks on side faces
    occ_dark: float = 0.4
    salt: int = 0

    def __call__(self, ctx):
        x, y, z = ctx['x'].astype(np.float32), ctx['y'].astype(np.float32), ctx['z'].astype(np.float32)
        w = (fbm(x, y, None, scale=self.warp_scale, octaves=3, seed=ctx['seed'] + 17 + self.salt) - 0.5) * 2
        zz = z + w * self.warp + x * self.tilt[0] + y * self.tilt[1]
        cyc = np.cumsum(self.pattern)
        period = cyc[-1]
        k = np.mod(np.floor(zz).astype(int), period)
        band = np.searchsorted(cyc, k, side='right')                # index into pattern
        idx = (band + (np.floor(zz).astype(int) // period) * len(self.pattern)) % len(self.palette)
        pal = np.stack([hex_rgb(c) for c in self.palette])
        c = pal[idx]
        top = ctx['top'][:, None]
        if self.crust:
            c = np.where(top, c * (1 - self.crust_mix) + hex_rgb(self.crust) * self.crust_mix, c)
        side = ~ctx['top'] & ~ctx['under']
        st = value_noise(x, y, z / 7.0, scale=2.3, seed=ctx['seed'] + 99 + self.salt)
        c = np.where(side[:, None], c * self.side_dark * (1 - self.streak * np.clip((st - 0.45) * 2.5, 0, 1))[:, None], c)
        c = np.where((ctx['under'] & ~ctx['top'])[:, None], c * self.under_dark, c)
        occ = np.clip((ctx['occ'] - 0.5) / 0.5, 0, 1)
        return c * (1 - self.occ_dark * occ)[:, None]


@dataclass
class PatternShader:
    """Flat painted pattern from a function f(x, y, z) -> index into colours (for paving, inlays)."""
    colours: list
    fn: object
    side_dark: float = 0.82
    occ_dark: float = 0.3

    def __call__(self, ctx):
        idx = self.fn(ctx['x'], ctx['y'], ctx['z']) % len(self.colours)
        pal = np.stack([hex_rgb(c) for c in self.colours])
        c = pal[idx]
        c = np.where(ctx['top'][:, None], c, c * self.side_dark)
        occ = np.clip((ctx['occ'] - 0.5) / 0.5, 0, 1)
        return c * (1 - self.occ_dark * occ)[:, None]
