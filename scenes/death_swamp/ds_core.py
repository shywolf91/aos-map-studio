"""Shared helpers for Death Swamp (push).

Conventions (aosmap / pyspades 1.4.2): arrays [x, y, z]; x, y 0..511; z 0..63 with z = 0 the sky top and
z = 63 the water plane. The map is authored on the WEST half (x <= 255) and mirrored with x' = 511 - x, so
the mirror axis sits between columns 255 and 256 (centre 255.5) and both lanes are exact copies.
Noise is deterministic (zlib.crc32 seeds, numpy Generator), never Python hash().
"""
from __future__ import annotations

import zlib

import numpy as np

MX, MY, MZ = 512, 512, 64
SEED = 6613
WATER_Z = 62          # a column with z = 62 air is open (deadly) water


def _seed(tag: str, seed: int = SEED) -> int:
    return (zlib.crc32(tag.encode()) ^ (seed * 2654435761)) & 0xFFFFFFFF


def rng(tag: str, seed: int = SEED) -> np.random.Generator:
    return np.random.default_rng(_seed(tag, seed))


def value_noise2(shape, cell, tag, seed=SEED):
    """Smooth 2D value noise in [0, 1] over an (X, Y) grid (smoothstep interpolation)."""
    g = rng(tag, seed).random((shape[0] // cell + 3, shape[1] // cell + 3))
    xs = np.arange(shape[0]) / cell
    ys = np.arange(shape[1]) / cell
    x0 = np.floor(xs).astype(int); y0 = np.floor(ys).astype(int)
    fx = xs - x0; fy = ys - y0
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
    a = g[x0][:, y0]; b = g[x0 + 1][:, y0]; c = g[x0][:, y0 + 1]; d = g[x0 + 1][:, y0 + 1]
    FX = fx[:, None]; FY = fy[None, :]
    return (a * (1 - FX) + b * FX) * (1 - FY) + (c * (1 - FX) + d * FX) * FY


def fbm2(shape, cell, octaves, tag, seed=SEED, gain=0.5):
    tot = np.zeros(shape); amp = 1.0; s = 0.0
    for o in range(octaves):
        tot += amp * value_noise2(shape, max(1, cell // (2 ** o)), f'{tag}/{o}', seed)
        s += amp; amp *= gain
    return tot / s


def hash3(x, y, z, salt=0):
    """Deterministic integer hash -> [0, 1)."""
    with np.errstate(over='ignore'):
        h = (np.asarray(x).astype(np.uint64) * np.uint64(73856093)) ^ \
            (np.asarray(y).astype(np.uint64) * np.uint64(19349663)) ^ \
            (np.asarray(z).astype(np.uint64) * np.uint64(83492791)) ^ (np.uint64(salt) * np.uint64(2246822519))
        h = (h ^ (h >> np.uint64(13))) * np.uint64(1274126177)
        h = h ^ (h >> np.uint64(16))
    return (h & np.uint64(0xFFFFFF)).astype(np.float64) / float(0x1000000)


def mirror_x(a: np.ndarray) -> np.ndarray:
    """Copy the west half onto the east half: a[511 - x] = a[x] for x <= 255."""
    a = a.copy()
    a[256:] = a[255::-1]
    return a


def fold_x(x):
    """Map any x onto the authored west half (so mirrored noise matches)."""
    x = np.asarray(x)
    return np.where(x > 255, 511 - x, x)


def pack_rgb(rgb, shade=0x80):
    rgb = np.clip(np.rint(rgb), 0, 255).astype(np.uint32)
    return (np.uint32(shade) << 24) | (rgb[..., 0] << 16) | (rgb[..., 1] << 8) | rgb[..., 2]


def line_voxels(p0, p1):
    """Face-connected voxel path between two points (moves one axis per step)."""
    p = np.array(np.rint(p0), int)
    q = np.array(np.rint(p1), int)
    out = [tuple(p)]
    d = q - p
    n = int(np.abs(d).sum())
    if n == 0:
        return out
    acc = np.zeros(3)
    step = np.sign(d)
    frac = np.abs(d) / n
    for _ in range(n):
        acc += frac
        k = int(np.argmax(acc))
        acc[k] -= 1
        p[k] += step[k]
        out.append(tuple(p))
    return out
