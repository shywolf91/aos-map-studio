"""VXL codec on plain numpy arrays.

encode() is the writer that was copied into gf/hc/wkh/sph_core.py; it is byte-identical to pyspades 1.4.2
VXLData.generate() for the same solid/colour data [RUN]. It replaces Bloomhop's Linux-only libvxlenc.so and
Haunted Fairground's vxlio.py (whose output was valid but not pyspades-canonical).
decode() wraps the strict reader in aosmap.vxl.

Colours: either packed uint32 0xAARRGGBB arrays [x, y, z] or uint8 rgb arrays [x, y, z, 3] (packed with shade 0x80).
"""
from __future__ import annotations

import io
import struct

import numpy as np

from .params import MX, MY, MZ

SHADE = 0x80


def pack_rgb(rgb, shade: int = SHADE) -> np.ndarray:
    rgb = np.clip(np.rint(np.asarray(rgb, float)), 0, 255).astype(np.uint32)
    return (np.uint32(shade) << 24) | (rgb[..., 0] << 16) | (rgb[..., 1] << 8) | rgb[..., 2]


def unpack_rgb(c) -> np.ndarray:
    c = np.asarray(c).astype(np.uint32)
    return np.stack([(c >> 16) & 255, (c >> 8) & 255, c & 255], -1).astype(np.uint8)


def as_packed(color) -> np.ndarray:
    color = np.asarray(color)
    if color.ndim == 4:
        return pack_rgb(color)
    return color.astype(np.uint32)


def surface_mask(solid: np.ndarray) -> np.ndarray:
    """Solid voxels with an air face neighbour (in-map only) or at z = 0. Out-of-map x/y and below 63 count as solid."""
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


def encode(solid: np.ndarray, color) -> bytes:
    """solid bool [x,y,z]; color packed uint32 [x,y,z] or rgb uint8 [x,y,z,3]. z = 63 is forced solid."""
    solid = solid.copy()
    solid[:, :, 63] = True
    color = as_packed(color)
    surf = surface_mask(solid)
    S_ = np.ascontiguousarray(solid.transpose(1, 0, 2))
    F_ = np.ascontiguousarray(surf.transpose(1, 0, 2))
    C_ = np.ascontiguousarray(color.transpose(1, 0, 2))
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


def decode(data: bytes):
    """Strict decode -> (solid bool, color uint32, colored bool), all [x, y, z]. Raises on malformed data."""
    from ..vxl import read_vxl
    m, rep = read_vxl(data)
    if rep.issues or rep.bytes_consumed != rep.bytes_total:
        raise ValueError(f'VXL decode issues: {rep.issues[:3]} consumed {rep.bytes_consumed}/{rep.bytes_total}')
    return m.solid, m.color, m.colored


def pyspades_crosscheck(data: bytes, solid=None, color=None, samples: int = 20000, seed: int = 1) -> dict:
    """Load with pyspades 1.4.2 VXLData: generate() identical? plus sampled solid / surface-colour mismatches."""
    from pyspades.vxl import VXLData
    if solid is None:
        solid, color, _ = decode(data)
    vm = VXLData(fp=io.BytesIO(data))
    g = bytes(vm.generate())
    surf = surface_mask(solid)
    rng = np.random.default_rng(seed)
    pts = rng.integers(0, [MX, MY, MZ], size=(samples, 3))
    sm = cm = 0
    for x, y, z in pts:
        s = vm.get_solid(int(x), int(y), int(z))
        if bool(s) != bool(solid[x, y, z]):
            sm += 1
        if s and surf[x, y, z]:
            c = vm.get_color(int(x), int(y), int(z))
            cc = int(color[x, y, z])
            if tuple(c[:3]) != ((cc >> 16) & 255, (cc >> 8) & 255, cc & 255):
                cm += 1
    return {'generate_identical': g == data, 'solid_mismatch_20k': sm, 'colour_mismatch_20k': cm}
