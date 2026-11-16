"""Core voxel helpers for Witchwood Isles: volume, VXL writer/reader, noise, connectivity.

Coordinates: arrays are indexed [x, y, z]; z = 0 is the top of the sky, z = 63 the bottom.
VXL layout follows pyspades 1.4.2 vxl_c.cpp (columns y-outer / x-inner, spans N S E A,
colours stored B G R A for surface voxels only, A = 0x80).
"""
import struct
import zlib

import numpy as np
from scipy import ndimage

W = 512
D = 64


def new_volume():
    solid = np.zeros((W, W, D), dtype=bool)
    mat = np.zeros((W, W, D), dtype=np.uint8)
    solid[:, :, 63] = True
    return solid, mat


def surface_mask(solid):
    """Solid voxels that get a stored colour: z == 0 or any in-map face neighbour is air.
    Out-of-map x/y and below z 63 count as solid (pyspades is_surface)."""
    air = ~solid
    s = np.zeros_like(solid)
    s[:, :, 0] = True
    s[:, :, 1:] |= air[:, :, :-1]          # air above
    s[:, :, :-1] |= air[:, :, 1:]          # air below
    s[1:, :, :] |= air[:-1, :, :]
    s[:-1, :, :] |= air[1:, :, :]
    s[:, 1:, :] |= air[:, :-1, :]
    s[:, :-1, :] |= air[:, 1:, :]
    return s & solid


def write_vxl(path, solid, colors):
    """colors: uint8 [W,W,D,3] RGB. Only surface voxels' colours are written."""
    surf = surface_mask(solid)
    out = bytearray()
    for y in range(W):
        for x in range(W):
            sol = solid[x, y]
            sur = surf[x, y]
            col = colors[x, y]
            k = 0
            while k < D:
                air_start = k
                while k < D and not sol[k]:
                    k += 1
                top_start = k
                while k < D and sur[k]:
                    k += 1
                top_end = k
                while k < D and sol[k] and not sur[k]:
                    k += 1
                bottom_start = k
                z = k
                while z < D and sur[z]:
                    z += 1
                if z != D:
                    while k < D and sur[k]:
                        k += 1
                bottom_end = k
                ntop = top_end - top_start
                nbot = bottom_end - bottom_start
                n = 0 if k == D else ntop + nbot + 1
                out += bytes((n, top_start, top_end - 1, air_start))
                for zz in range(top_start, top_end):
                    r, g, b = col[zz]
                    out += bytes((b, g, r, 0x80))
                for zz in range(bottom_start, bottom_end):
                    r, g, b = col[zz]
                    out += bytes((b, g, r, 0x80))
    with open(path, 'wb') as f:
        f.write(bytes(out))
    return bytes(out)


def read_vxl(data):
    """Strict span reader (independent of the writer's logic)."""
    solid = np.ones((W, W, D), dtype=bool)
    stored = np.zeros((W, W, D), dtype=bool)
    colors = np.zeros((W, W, D, 3), dtype=np.uint8)
    p = 0
    L = len(data)
    for y in range(W):
        for x in range(W):
            first = True
            while True:
                if p + 4 > L:
                    raise ValueError('truncated at column %d,%d' % (x, y))
                n, s, e, a = data[p], data[p + 1], data[p + 2], data[p + 3]
                air_from = 0 if first else a
                first = False
                if s < air_from or e < s - 1 or e > 63:
                    raise ValueError('bad span at %d,%d: %r' % (x, y, (n, s, e, a)))
                solid[x, y, air_from:s] = False
                ntop = e - s + 1
                for i in range(ntop):
                    off = p + 4 + 4 * i
                    colors[x, y, s + i] = (data[off + 2], data[off + 1], data[off])
                    stored[x, y, s + i] = True
                if n == 0:
                    p += 4 + 4 * ntop
                    break
                nbot = n - 1 - ntop
                if nbot < 0:
                    raise ValueError('negative bottom run at %d,%d' % (x, y))
                nxt = p + 4 * n
                next_a = data[nxt + 3]
                for i in range(nbot):
                    off = p + 4 + 4 * (ntop + i)
                    zz = next_a - nbot + i
                    colors[x, y, zz] = (data[off + 2], data[off + 1], data[off])
                    stored[x, y, zz] = True
                p = nxt
    if p != L:
        raise ValueError('trailing bytes: %d' % (L - p))
    return solid, colors, stored


# ---------------------------------------------------------------- noise

def value_noise(seed, shape, cell):
    """Deterministic smooth value noise in [0,1] over a 2-D grid (bilinear, smoothstep)."""
    rng = np.random.RandomState(seed & 0x7fffffff)
    gx = shape[0] // cell + 2
    gy = shape[1] // cell + 2
    g = rng.rand(gx, gy)
    xs = np.arange(shape[0]) / cell
    ys = np.arange(shape[1]) / cell
    xi = xs.astype(int)
    yi = ys.astype(int)
    xf = xs - xi
    yf = ys - yi
    xf = xf * xf * (3 - 2 * xf)
    yf = yf * yf * (3 - 2 * yf)
    a = g[xi][:, yi]
    b = g[xi + 1][:, yi]
    c = g[xi][:, yi + 1]
    d = g[xi + 1][:, yi + 1]
    xf = xf[:, None]
    yf = yf[None, :]
    return (a * (1 - xf) + b * xf) * (1 - yf) + (c * (1 - xf) + d * xf) * yf


def fbm(seed, shape, cell, octaves=3):
    tot = np.zeros(shape)
    amp = 1.0
    norm = 0.0
    for o in range(octaves):
        tot += amp * value_noise(seed + 101 * o, shape, max(2, cell >> o))
        norm += amp
        amp *= 0.5
    return tot / norm


def seed_of(name, base):
    return (zlib.crc32(name.encode()) ^ base) & 0x7fffffff


# ---------------------------------------------------------------- connectivity

def floating_components(solid):
    """Components (6-connectivity) with no voxel at z >= 62. Returns list of (size, bbox)."""
    struct6 = ndimage.generate_binary_structure(3, 1)
    lab, n = ndimage.label(solid, structure=struct6)
    grounded = set(np.unique(lab[:, :, 62:])) - {0}
    out = []
    if n == len(grounded):
        return out, n
    objs = ndimage.find_objects(lab)
    sizes = ndimage.sum_labels(solid, lab, index=np.arange(1, n + 1))
    for i in range(1, n + 1):
        if i in grounded:
            continue
        sl = objs[i - 1]
        out.append({'size': int(sizes[i - 1]),
                    'x': [sl[0].start, sl[0].stop - 1],
                    'y': [sl[1].start, sl[1].stop - 1],
                    'z': [sl[2].start, sl[2].stop - 1]})
    return out, n


def top_z(solid):
    """Topmost solid z per column (pyspades get_z)."""
    return np.argmax(solid, axis=2)
