"""Classic Ace of Spades (0.75) VXL reader/writer.

Coordinate convention (verified: piqueserver 1.4.2 pyspades/vxl_c.h, aosprotocol map spec):
    x, y in 0..511 (columns), z in 0..63 with z = 0 the TOP of the sky and z = 63 the bottom.
    Arrays here are indexed [x, y, z] (z contiguous, so a column is solid[x, y, :]).

File layout: no header. Columns stored y-major / x-minor: (0,0), (1,0) ... (511,0), (0,1) ...
Each column is a list of spans; each span = 4-byte header (N, S, E, A) followed by colours:
    N  span length in 4-byte units incl. header; 0 marks the column's last span
    S  first z of the top coloured run
    E  last z of the top coloured run (INCLUSIVE)
    A  z where this span's air begins (ignored for the first span: air starts at 0)
Colours are 4 bytes B, G, R, A (little-endian 0xAARRGGBB). The 4th byte is a shade value:
pyspades update_shadows() writes 127 - occlusion; OpenSpades discards it (forces 100);
pyspades make_color() writes 0x80 for a=255.

Surface rule (matches pyspades save_vxl is_surface): a solid voxel is "surface" (must carry a
colour) if z == 0, or any of its 6 face neighbours inside the map is air. Neighbours outside
the map in x/y, and below z = 63, count as SOLID.

The writer reproduces pyspades 1.4.2 save_vxl() span emission exactly, so for identical
occupancy + colours it is byte-identical to VXLData.generate() (tested in tools/compare_refs.py).
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

import numpy as np

MAP_X, MAP_Y, MAP_Z = 512, 512, 64
DEFAULT_COLOR = 0xFF674028          # pyspades DEFAULT_COLOR (ARGB)
DEFAULT_SHADE = 0x80                # alpha byte pyspades make_color() emits for opaque colours


def rgb(r: int, g: int, b: int, shade: int = DEFAULT_SHADE) -> int:
    """Pack an RGB colour into the native 0xAARRGGBB integer used in the file and in pyspades."""
    return (shade << 24) | (r << 16) | (g << 8) | b


def unpack(color: int) -> tuple[int, int, int, int]:
    """Return (r, g, b, shade) from a native colour int."""
    return (color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF, (color >> 24) & 0xFF


@dataclass
class VoxelMap:
    solid: np.ndarray = field(default_factory=lambda: np.zeros((MAP_X, MAP_Y, MAP_Z), bool))
    color: np.ndarray = field(default_factory=lambda: np.zeros((MAP_X, MAP_Y, MAP_Z), np.uint32))
    colored: np.ndarray = field(default_factory=lambda: np.zeros((MAP_X, MAP_Y, MAP_Z), bool))

    def set(self, x, y, z, color: int | None):
        """Set a voxel (slices allowed). color=None removes it."""
        if color is None:
            self.solid[x, y, z] = False
            self.colored[x, y, z] = False
            self.color[x, y, z] = 0
        else:
            self.solid[x, y, z] = True
            self.colored[x, y, z] = True
            self.color[x, y, z] = color

    def surface(self) -> np.ndarray:
        return surface_mask(self.solid)


def surface_mask(solid: np.ndarray) -> np.ndarray:
    """Vectorised pyspades is_surface(): solid AND (z==0 OR an in-bounds face neighbour is air)."""
    air = ~solid
    exposed = np.zeros_like(solid)
    exposed[:, :, 0] = True                       # z == 0 always surface
    exposed[:, :, 1:] |= air[:, :, :-1]           # air above (z-1)
    exposed[:, :, :-1] |= air[:, :, 1:]           # air below (z+1)
    exposed[1:, :, :] |= air[:-1, :, :]           # x-1
    exposed[:-1, :, :] |= air[1:, :, :]           # x+1
    exposed[:, 1:, :] |= air[:, :-1, :]           # y-1
    exposed[:, :-1, :] |= air[:, 1:, :]           # y+1
    return solid & exposed


# --------------------------------------------------------------------------- reader

@dataclass
class ReadReport:
    bytes_total: int = 0
    bytes_consumed: int = 0
    spans: int = 0
    empty_top_runs: int = 0     # spans with E == S-1 (zero colours in top run) - informational
    void_columns: int = 0       # columns whose z = 63 is AIR (last span S=64, E=63); may still have solid above
    issues: list = field(default_factory=list)   # (kind, x, y, detail) - capped

    def flag(self, kind, x, y, detail=""):
        if len(self.issues) < 200:
            self.issues.append((kind, x, y, detail))

    @property
    def ok(self) -> bool:
        return not self.issues and self.bytes_consumed == self.bytes_total


def read_vxl(data: bytes) -> tuple[VoxelMap, ReadReport]:
    """Independent spec-based decoder. Never trusts the file: every span is bounds-checked."""
    m = VoxelMap()
    rep = ReadReport(bytes_total=len(data))
    solid = np.ones((MAP_Y, MAP_X, MAP_Z), bool)        # temporary [y, x, z] for write locality
    color = np.zeros((MAP_Y, MAP_X, MAP_Z), np.uint32)
    colored = np.zeros((MAP_Y, MAP_X, MAP_Z), bool)
    unpack_u32 = struct.Struct('<I').unpack_from
    n = len(data)
    p = 0
    for y in range(MAP_Y):
        for x in range(MAP_X):
            col_s, col_c, col_k = solid[y, x], color[y, x], colored[y, x]
            z = 0
            first = True
            while True:
                if p + 4 > n:
                    rep.flag('truncated', x, y, f'offset {p}')
                    rep.bytes_consumed = p
                    raise ValueError(f'VXL truncated at column ({x},{y}), offset {p}')
                N, S, E, A = data[p], data[p + 1], data[p + 2], data[p + 3]
                rep.spans += 1
                if N == 0 and S == 64 and E == 63:
                    rep.void_columns += 1       # z=63 is air in this column (spec-violating, but
                                                # pyspades loads/re-emits it; seen in 10yearsaloha)
                elif S > 63 or E > 63:
                    rep.flag('z_out_of_range', x, y, f'S={S} E={E}')
                if E == S - 1:
                    rep.empty_top_runs += 1     # legal: pyspades save_vxl emits these (see writer)
                elif E < S - 1:
                    rep.flag('negative_top_run', x, y, f'S={S} E={E}')
                if S < z:
                    rep.flag('top_start_before_cursor', x, y, f'S={S} cursor={z}')
                col_s[z:S] = False                              # air run
                K = E - S + 1
                cp = p + 4
                for i in range(max(K, 0)):
                    col_c[S + i] = unpack_u32(data, cp)[0]
                    col_k[S + i] = True
                    cp += 4
                if N == 0:
                    p += 4 * (max(K, 0) + 1)
                    break
                Z = (N - 1) - K
                if Z < 0:
                    rep.flag('negative_bottom_count', x, y, f'N={N} K={K}')
                p += 4 * N
                if p + 4 > n:
                    rep.flag('truncated', x, y, f'offset {p}')
                    raise ValueError(f'VXL truncated at column ({x},{y})')
                M = data[p + 3]                                 # next span's air start
                if M < E + 1 + max(Z, 0):
                    rep.flag('bottom_run_overlaps_top', x, y, f'M={M} E={E} Z={Z}')
                for i in range(max(Z, 0)):
                    zz = M - Z + i
                    col_c[zz] = unpack_u32(data, cp)[0]
                    col_k[zz] = True
                    cp += 4
                z = M
                first = False
    rep.bytes_consumed = p
    if p != n:
        rep.flag('trailing_bytes', -1, -1, f'{n - p} bytes after last column')
    m.solid = np.ascontiguousarray(solid.transpose(1, 0, 2))
    m.color = np.ascontiguousarray(color.transpose(1, 0, 2))
    m.colored = np.ascontiguousarray(colored.transpose(1, 0, 2))
    return m, rep


# --------------------------------------------------------------------------- writer

class MissingColorError(ValueError):
    pass


def write_vxl(m: VoxelMap, missing: str = 'error', force_bottom: bool = True) -> bytes:
    """Encode a VoxelMap. Mirrors pyspades 1.4.2 save_vxl() span emission.

    missing='error'   raise if a surface voxel has no colour (authoring default - catches bugs)
    missing='default' use pyspades DEFAULT_COLOR, exactly as VXLData.generate() does
    force_bottom=True makes z = 63 solid everywhere (spec: bottom layer must be solid; it is the
                      water plane). False reproduces pyspades exactly for spec-violating inputs.
    """
    solid = m.solid.copy()
    if force_bottom:
        solid[:, :, 63] = True
    surf = surface_mask(solid)
    need = surf & ~m.colored
    if missing == 'error' and need.any():
        xs, ys, zs = np.nonzero(need)
        raise MissingColorError(f'{need.sum()} surface voxels lack colour, e.g. {(xs[0], ys[0], zs[0])}')
    colors = np.where(m.colored, m.color, np.uint32(DEFAULT_COLOR)).astype(np.uint32)

    # [y, x, z] views so we iterate in file order with contiguous columns
    S_ = np.ascontiguousarray(solid.transpose(1, 0, 2))
    F_ = np.ascontiguousarray(surf.transpose(1, 0, 2))
    C_ = np.ascontiguousarray(colors.transpose(1, 0, 2))
    out = bytearray()
    pack = struct.Struct('<I').pack
    Z = MAP_Z
    for y in range(MAP_Y):
        rs, rf, rc = S_[y].tolist(), F_[y].tolist(), C_[y].tolist()
        for x in range(MAP_X):
            g, s, c = rs[x], rf[x], rc[x]
            k = 0
            while k < Z:
                air_start = k
                while k < Z and not g[k]:
                    k += 1
                top_start = k
                while k < Z and s[k]:
                    k += 1
                top_end = k                                   # exclusive
                while k < Z and g[k] and not s[k]:
                    k += 1
                bot_start = k
                zz = k
                while zz < Z and s[zz]:
                    zz += 1
                if zz != Z:                                   # real bottom colours
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


def load(path) -> tuple[VoxelMap, ReadReport]:
    with open(path, 'rb') as f:
        return read_vxl(f.read())


def save(m: VoxelMap, path, **kw) -> bytes:
    data = write_vxl(m, **kw)
    with open(path, 'wb') as f:
        f.write(data)
    return data
