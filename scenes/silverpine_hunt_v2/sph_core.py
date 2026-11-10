"""Core helpers for Silverpine Hunt generator.

VXL encode/decode follows the aosmap toolchain (aosmap/vxl.py), which mirrors pyspades 1.4.2 save_vxl():
  * x, y 0..511, z 0..63 with z = 0 the top of the sky, z = 63 the bottom (water plane).
  * columns stored y-major / x-minor; spans (N, S, E, A) + colours B, G, R, A(shade 0x80).
  * surface voxel = solid and (z == 0 or an in-map face neighbour is air); out-of-map x/y and below 63 = solid.
Arrays are indexed [x, y, z].
"""
from __future__ import annotations

import struct
import zlib

import numpy as np

MX, MY, MZ = 512, 512, 64
SHADE = 0x80


# ----------------------------------------------------------------------------- colour packing

def pack_rgb(rgb: np.ndarray, shade: int = SHADE) -> np.ndarray:
    rgb = np.clip(np.rint(rgb), 0, 255).astype(np.uint32)
    return (np.uint32(shade) << 24) | (rgb[..., 0] << 16) | (rgb[..., 1] << 8) | rgb[..., 2]


def unpack_rgb(c: np.ndarray) -> np.ndarray:
    c = c.astype(np.uint32)
    return np.stack([(c >> 16) & 255, (c >> 8) & 255, c & 255], -1).astype(np.uint8)


# ----------------------------------------------------------------------------- VXL

def surface_mask(solid: np.ndarray) -> np.ndarray:
    air = ~solid
    ex = np.zeros_like(solid)
    ex[:, :, 0] = True
    ex[:, :, 1:] |= air[:, :, :-1]
    ex[:, :, :-1] |= air[:, :, 1:]
    ex[1:, :, :] |= air[:-1, :, :]
    ex[:-1, :, :] |= air[1:, :, :]
    ex[:, 1:, :] |= air[:, :-1, :]
    ex[:, :-1, :] |= air[:, 1:, :]
    return solid & ex


def write_vxl(solid: np.ndarray, color: np.ndarray) -> bytes:
    """Encode; byte-identical to pyspades 1.4.2 VXLData.generate() for the same solid/colour data."""
    solid = solid.copy()
    solid[:, :, 63] = True
    surf = surface_mask(solid)
    S_ = np.ascontiguousarray(solid.transpose(1, 0, 2))
    F_ = np.ascontiguousarray(surf.transpose(1, 0, 2))
    C_ = np.ascontiguousarray(color.astype(np.uint32).transpose(1, 0, 2))
    out = bytearray()
    pack = struct.Struct('<I').pack
    Z = MZ
    for y in range(MY):
        rs, rf, rc = S_[y].tolist(), F_[y].tolist(), C_[y].tolist()
        for x in range(MX):
            g, s, c = rs[x], rf[x], rc[x]
            k = 0
            while k < Z:
                air_start = k
                while k < Z and not g[k]:
                    k += 1
                top_start = k
                while k < Z and s[k]:
                    k += 1
                top_end = k
                while k < Z and g[k] and not s[k]:
                    k += 1
                bot_start = k
                zz = k
                while zz < Z and s[zz]:
                    zz += 1
                if zz != Z:
                    while k < Z and s[k]:
                        k += 1
                bot_end = k
                ntop, nbot = top_end - top_start, bot_end - bot_start
                out.append(0 if k == Z else ntop + nbot + 1)
                out.append(top_start)
                out.append(top_end - 1)
                out.append(air_start)
                for i in range(top_start, top_end):
                    out += pack(c[i])
                for i in range(bot_start, bot_end):
                    out += pack(c[i])
    return bytes(out)


def read_vxl(data: bytes):
    """Independent strict decoder -> (solid, color, colored). Raises on malformed data."""
    solid = np.zeros((MX, MY, MZ), bool)
    color = np.zeros((MX, MY, MZ), np.uint32)
    colored = np.zeros((MX, MY, MZ), bool)
    p = 0
    n = len(data)
    for y in range(MY):
        for x in range(MX):
            z = 0
            col = solid[x, y]
            while True:
                if p + 4 > n:
                    raise ValueError(f'truncated at column {x},{y}')
                N, S, E, A = data[p], data[p + 1], data[p + 2], data[p + 3]
                if E + 1 < S or E > 63:
                    raise ValueError(f'bad span at {x},{y}: S={S} E={E}')
                ntop = E - S + 1
                for i in range(ntop):
                    off = p + 4 + 4 * i
                    color[x, y, S + i] = int.from_bytes(data[off:off + 4], 'little')
                    colored[x, y, S + i] = True
                col[S:E + 1] = True
                if N == 0:
                    col[S:] = True
                    p += 4 + 4 * ntop
                    break
                nbot = N - 1 - ntop
                nxt = p + 4 * N
                Anext = data[nxt + 3]
                col[S:Anext] = True
                for i in range(nbot):
                    off = p + 4 + 4 * (ntop + i)
                    zz = Anext - nbot + i
                    color[x, y, zz] = int.from_bytes(data[off:off + 4], 'little')
                    colored[x, y, zz] = True
                p = nxt
    if p != n:
        raise ValueError(f'{n - p} trailing bytes')
    return solid, color, colored


# ----------------------------------------------------------------------------- noise (deterministic)

def _seed(tag: str, seed: int) -> int:
    return (zlib.crc32(tag.encode()) ^ (seed * 2654435761)) & 0xFFFFFFFF


def value_noise2(shape, cell, tag, seed):
    """Smooth 2D value noise in [0,1] over an (X, Y) grid, bicubic-ish (smoothstep) interpolation."""
    rng = np.random.default_rng(_seed(tag, seed))
    X, Y = shape
    gx, gy = X // cell + 3, Y // cell + 3
    g = rng.random((gx, gy))
    xs = np.arange(X) / cell
    ys = np.arange(Y) / cell
    x0 = np.floor(xs).astype(int); y0 = np.floor(ys).astype(int)
    fx = xs - x0; fy = ys - y0
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
    a = g[x0][:, y0]; b = g[x0 + 1][:, y0]; c = g[x0][:, y0 + 1]; d = g[x0 + 1][:, y0 + 1]
    FX = fx[:, None]; FY = fy[None, :]
    return (a * (1 - FX) + b * FX) * (1 - FY) + (c * (1 - FX) + d * FX) * FY


def fbm2(shape, cell, octaves, tag, seed, gain=0.5):
    tot = np.zeros(shape); amp = 1.0; s = 0.0
    for o in range(octaves):
        c = max(1, cell // (2 ** o))
        tot += amp * value_noise2(shape, c, f'{tag}/{o}', seed)
        s += amp; amp *= gain
    return tot / s


def fold_x(a: np.ndarray) -> np.ndarray:
    """Make an [x, y, ...] field mirror-symmetric about x = 256 (x' = 512 - x)."""
    a = a.copy()
    a[257:] = a[255:0:-1]
    return a


def hash3(x, y, z, salt=0):
    """Cheap deterministic integer hash -> [0,1)."""
    h = (np.asarray(x, np.int64) * 73856093) ^ (np.asarray(y, np.int64) * 19349663) ^ \
        (np.asarray(z, np.int64) * 83492791) ^ (salt * 2246822519)
    h = (h ^ (h >> 13)) * 1274126177
    h = h ^ (h >> 16)
    return (h & 0xFFFFFF) / float(0x1000000)
