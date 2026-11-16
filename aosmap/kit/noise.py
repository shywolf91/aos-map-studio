"""Deterministic noise. Seeds go through zlib.crc32, never Python's hash() (randomised per process).
Merged from the identical blocks in gf/hc/wkh/sph_core.py and Bloomhop's noise.py."""
from __future__ import annotations

import os
import zlib

import numpy as np


def seed_of(tag: str, seed: int) -> int:
    return (zlib.crc32(tag.encode()) ^ (int(seed) * 2654435761)) & 0xFFFFFFFF


def rng(tag: str, seed: int) -> np.random.Generator:
    return np.random.default_rng(seed_of(tag, seed))


def os_seed() -> int:
    """Fresh seed for the non-deterministic parts (vegetation, decoration): save it in build.json."""
    return int.from_bytes(os.urandom(4), 'little')


def value_noise2(shape, cell, tag, seed):
    """Smooth 2D value noise in [0,1] over an (X, Y) grid (smoothstep interpolation)."""
    r = rng(tag, seed)
    X, Y = shape
    gx, gy = X // cell + 3, Y // cell + 3
    g = r.random((gx, gy))
    xs = np.arange(X) / cell
    ys = np.arange(Y) / cell
    x0 = np.floor(xs).astype(int)
    y0 = np.floor(ys).astype(int)
    fx = xs - x0
    fy = ys - y0
    fx = fx * fx * (3 - 2 * fx)
    fy = fy * fy * (3 - 2 * fy)
    a = g[x0][:, y0]
    b = g[x0 + 1][:, y0]
    c = g[x0][:, y0 + 1]
    d = g[x0 + 1][:, y0 + 1]
    FX = fx[:, None]
    FY = fy[None, :]
    return (a * (1 - FX) + b * FX) * (1 - FY) + (c * (1 - FX) + d * FX) * FY


def fbm2(shape, cell, octaves, tag, seed, gain=0.5):
    tot = np.zeros(shape)
    amp = 1.0
    s = 0.0
    for o in range(octaves):
        c = max(1, cell // (2 ** o))
        tot += amp * value_noise2(shape, c, f'{tag}/{o}', seed)
        s += amp
        amp *= gain
    return tot / s


def hash3(x, y, z, salt=0):
    """Cheap deterministic integer hash -> [0, 1)."""
    h = (np.asarray(x, np.int64) * 73856093) ^ (np.asarray(y, np.int64) * 19349663) ^ \
        (np.asarray(z, np.int64) * 83492791) ^ (salt * 2246822519)
    h = (h ^ (h >> 13)) * 1274126177
    h = h ^ (h >> 16)
    return (h & 0xFFFFFF) / float(0x1000000)
