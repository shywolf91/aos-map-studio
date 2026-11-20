"""Floebreaker v2 architecture (docs/craft_standard.md §2).

One parametric builder, `building()`, makes every house-like structure:
  * a stone base course (2 rows) under board-clad walls laid in horizontal courses of two close tones;
  * contrasting corner posts and a string course between floors, framed doors and windows (real openings);
  * a gable roof at 45 degrees (2 voxels thick so the slope is face-connected) or a hip roof, with 1-voxel eaves,
    plank rows in two tones, a darker ridge cap and snow lying on the upper slope;
  * gable ends closed to the ridge, a stone chimney, rooms on 1-2 floors with stairs, furniture and a ceiling lamp;
  * optional porch (posts, deck, lean-to roof) and a lantern by the door.
Composed structures (`station`, `lodge`, `observation_tower`, `boathouse`) combine several volumes. Every structure is
registered in W.structures for aosmap.kit.craft_checks and its rooms in W.interiors.
"""
from __future__ import annotations

import numpy as np

from fb_core import MAT
from fb_props import pad


def _set(W, x, y, z, name):
    if 0 <= x < 512 and 0 <= y < 512 and 0 <= z < 63:
        W.m[x, y, z] = MAT[name]


def _hash(x, y, z, salt=0):
    return ((x * 73856093) ^ (y * 19349663) ^ (z * 83492791) ^ (salt * 2654435761)) & 0xFFFF


def building(W, H, x0, y0, w, d, floors=1, storey=5, family='red', ridge='long', roof='gable', door=('S', None),
             windows=True, chimney='E', porch=False, snow=0.55, name='building', role='small', zf=None,
             register=True, furnish=True, lamp_out=True, pitch=1):
    """Footprint x0..x0+w-1, y0..y0+d-1. Floors are `storey` voxels apart (4 air + slab). Returns geometry dict."""
    x1, y1 = x0 + w - 1, y0 + d - 1
    W.keep[max(x0 - 6, 0):x1 + 7, max(y0 - 6, 0):y1 + 7] = True
    if zf is None:
        zf = pad(W, H, x0 - 2, x1 + 2, y0 - 2, y1 + 2)
    wall_h = floors * storey
    ze = zf - wall_h                                   # eave level: top of the walls (the last wall row is ze + 1)
    ca, cb = f'clad_{family}_a', f'clad_{family}_b'
    # ---- walls with base course, courses, corner posts and string courses
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            edge = x in (x0, x1) or y in (y0, y1)
            corner = x in (x0, x1) and y in (y0, y1)
            for z in range(ze + 1, zf):
                if not edge:
                    W.m[x, y, z] = 0
                    continue
                k = zf - z                              # 1 = lowest wall row
                if k <= 2:
                    nm = 'stone' if _hash(x, y, z) % 3 else 'stone_b'
                elif corner:
                    nm = 'beam'
                elif floors > 1 and any(k == f * storey for f in range(1, floors)):
                    nm = 'trim'                         # string course at each upper floor
                else:
                    nm = ca if (k // 1) % 2 else cb     # 1-voxel board courses of two close tones
                W.m[x, y, z] = MAT[nm]
            W.m[x, y, zf] = MAT['floorp'] if not edge else MAT['stone']
    # ---- upper floor slabs
    for f in range(1, floors):
        zs = zf - f * storey
        W.box(x0 + 1, x1 - 1, y0 + 1, y1 - 1, zs, zs, 'floorp')
    # ---- roof
    along_y = (ridge == 'long' and d >= w) or (ridge == 'short' and d < w)
    span = w if along_y else d                        # roof slopes across this dimension
    half = (span + 1) / 2.0
    rx0, rx1, ry0, ry1 = x0 - 1, x1 + 1, y0 - 1, y1 + 1   # 1-voxel eaves all round
    top_z = None
    for x in range(rx0, rx1 + 1):
        for y in range(ry0, ry1 + 1):
            if roof == 'hip':
                t = min(x - rx0, rx1 - x, y - ry0, ry1 - y)
            else:
                t = (min(x - rx0, rx1 - x) if along_y else min(y - ry0, ry1 - y))
            rise = int(t) * pitch                      # pitch 1 = 45 degrees, 2 = steep spire / alpine roof
            z = ze - rise + 1
            top_z = z if top_z is None else min(top_z, z)
            row = int(t)
            nm = 'roof_a' if row % 2 == 0 else 'roof_b'
            for k in range(pitch + 1):                 # thick enough that the slope is face-connected
                _set(W, x, y, z + k, nm)
    # ridge cap and snow on the upper slope (smooth mask, never single-voxel speckle)
    for x in range(rx0, rx1 + 1):
        for y in range(ry0, ry1 + 1):
            col = W.m[x, y, :]
            zz = int(np.argmax(col > 0)) if (col > 0).any() else None
            if zz is None:
                continue
            if roof == 'hip':
                t = min(x - rx0, rx1 - x, y - ry0, ry1 - y)
                tmax = min((rx1 - rx0) // 2, (ry1 - ry0) // 2)
            else:
                t = (min(x - rx0, rx1 - x) if along_y else min(y - ry0, ry1 - y))
                tmax = int((span + 1) // 2)
            if t >= tmax:
                W.m[x, y, zz] = MAT['ridge']
            elif snow and t >= tmax * (1 - snow) and (_hash(x // 3, y // 3, 0, 7) % 7) != 0:
                W.m[x, y, zz] = MAT['snow_roof']
    # gable ends: close the triangle under the roof (gable roofs only)
    if roof == 'gable':
        ends = ((y0, y1) if along_y else (x0, x1))
        for e in ends:
            for u in range(x0 if along_y else y0, (x1 if along_y else y1) + 1):
                t = (min(u - (x0 if along_y else y0), (x1 if along_y else y1) - u) + 1) * pitch
                for z in range(ze - t + 2, ze + 1):
                    if along_y:
                        _set(W, u, e, z, 'clad_' + family + ('_a' if z % 2 else '_b'))
                    else:
                        _set(W, e, u, z, 'clad_' + family + ('_a' if z % 2 else '_b'))
        # attic air under the roof stays open (it is part of the top room)
    # ---- door(s) with frame and step
    side, pos = door
    doors = []
    for s in (side,) if isinstance(side, str) else side:
        if s in ('S', 'N'):
            yy = y1 if s == 'S' else y0
            xc = pos if pos is not None else (x0 + x1) // 2
            for x in (xc, xc + 1):
                for z in range(zf - 3, zf):
                    W.m[x, yy, z] = 0
            for z in range(zf - 4, zf):
                _set(W, xc - 1, yy, z, 'trim'); _set(W, xc + 2, yy, z, 'trim')
            _set(W, xc, yy, zf - 4, 'trim'); _set(W, xc + 1, yy, zf - 4, 'trim')
            out = (0, 1) if s == 'S' else (0, -1)
            doors.append((xc, yy, out))
        else:
            xx = x1 if s == 'E' else x0
            yc = pos if pos is not None else (y0 + y1) // 2
            for y in (yc, yc + 1):
                for z in range(zf - 3, zf):
                    W.m[xx, y, z] = 0
            for z in range(zf - 4, zf):
                _set(W, xx, yc - 1, z, 'trim'); _set(W, xx, yc + 2, z, 'trim')
            _set(W, xx, yc, zf - 4, 'trim'); _set(W, xx, yc + 1, zf - 4, 'trim')
            out = (1, 0) if s == 'E' else (-1, 0)
            doors.append((xx, yc, out))
    # ---- windows: 2 wide x 2 high, every 5 along each wall, framed (sill + lintel + jambs), on every floor
    if windows:
        for f in range(floors):
            zb = zf - f * storey - 2                  # lower window row
            for x in range(x0 + 2, x1 - 2, 5):
                for yy in (y0, y1):
                    if any(abs(x - dx) <= 3 and dy == yy for dx, dy, _ in doors) and f == 0:
                        continue
                    _window(W, x, yy, zb, 'x')
            for y in range(y0 + 2, y1 - 2, 5):
                for xx in (x0, x1):
                    if any(abs(y - dy) <= 3 and dx == xx for dx, dy, _ in doors) and f == 0:
                        continue
                    _window(W, xx, y, zb, 'y')
    # ---- chimney (stone, outside the gable or side wall), rising 2 above the ridge
    if chimney:
        if chimney == 'E':
            cx, cy = x1 + 1, (y0 + y1) // 2
        elif chimney == 'W':
            cx, cy = x0 - 2, (y0 + y1) // 2
        elif chimney == 'N':
            cx, cy = (x0 + x1) // 2, y0 - 2
        else:
            cx, cy = (x0 + x1) // 2, y1 + 1
        g = int(max(H[cx, cy], H[cx + 1, cy], H[cx, cy + 1], H[cx + 1, cy + 1]))
        for x in (cx, cx + 1):
            for y in (cy, cy + 1):
                for z in range(top_z - 3, g + 1):
                    _set(W, x, y, z, 'stone' if (z + x) % 3 else 'stone_b')
        _set(W, cx, cy, top_z - 4, 'dsteel'); _set(W, cx + 1, cy + 1, top_z - 4, 'dsteel')
        _set(W, cx + 1, cy, top_z - 4, 'dsteel'); _set(W, cx, cy + 1, top_z - 4, 'dsteel')
    # ---- stairs between floors (straight run along the long inside wall), rooms, furniture, lamps
    for f in range(1, floors):
        zlo, zhi = zf - (f - 1) * storey, zf - f * storey
        odd = f % 2 == 1                               # alternate sides so stacked flights never share a stairwell
        if d >= w:
            if odd:
                W.stairs(x1 - 3, x1 - 1, y0 + 2, zlo, zhi, '+y', 'beam')
            else:
                W.stairs(x0 + 1, x0 + 3, y1 - 2, zlo, zhi, '-y', 'beam')
        else:
            if odd:
                W.stairs(y0 + 1, y0 + 3, x0 + 2, zlo, zhi, '+x', 'beam')
            else:
                W.stairs(y1 - 3, y1 - 1, x1 - 2, zlo, zhi, '-x', 'beam')
    if furnish:
        for f in range(floors):
            zfl = zf - f * storey
            zc = zfl - storey if f < floors - 1 else ze
            big = w >= 12 and d >= 12
            if floors == 1 or big:
                W.box(x0 + 1, x0 + 2, y0 + 1, y0 + 2, zfl - 1, zfl - 1, 'plank')           # bunk / bench
                W.box(x1 - 1, x1 - 1, y1 - 2, y1 - 1, zfl - 2, zfl - 1, 'dwood')           # cupboard (away from stairs)
            if (floors == 1 or big) and w > 6 and d > 6:
                W.box(x0 + 3, x0 + 4, y0 + 3, y0 + 3, zfl - 2, zfl - 2, 'dwood')           # table top
                W.box(x0 + 3, x0 + 3, y0 + 3, y0 + 3, zfl - 1, zfl - 1, 'dwood')       # its leg
            lx, ly = (x0 + x1) // 2, (y0 + y1) // 2
            if W.m[lx, ly, zc] != 0 or f == floors - 1:
                hang = zc + 1 if W.m[lx, ly, zc] != 0 else zc
                W.pt(lx, ly, hang, 'lamp')
            W.interiors.append((name + f'_f{f}', lx, ly + 1 if ly + 1 <= y1 - 1 else ly, zfl))
    # ---- porch: deck + posts + lean-to roof in front of the first door
    if porch and doors:
        dx0, dy0, (ox, oy) = doors[0]
        if oy:
            yy0 = dy0 + oy
            ys = range(yy0, yy0 + 3 * oy, oy)
            px0, px1 = dx0 - 3, dx0 + 4
            for y in ys:
                for x in range(px0, px1 + 1):
                    g = int(H[x, y])
                    _set(W, x, y, zf, 'plank')
                    for z in range(zf + 1, g):
                        _set(W, x, y, z, 'beam')
            yl = yy0 + 2 * oy
            for x in (px0, px1):
                for z in range(zf - 4, zf):
                    _set(W, x, yl, z, 'beam')
            for i, y in enumerate(ys):
                for x in range(px0 - 1, px1 + 2):
                    _set(W, x, y, zf - 5 + i, 'roof_b')
        else:
            xx0 = dx0 + ox
            xs = range(xx0, xx0 + 3 * ox, ox)
            py0, py1 = dy0 - 3, dy0 + 4
            for x in xs:
                for y in range(py0, py1 + 1):
                    g = int(H[x, y])
                    _set(W, x, y, zf, 'plank')
                    for z in range(zf + 1, g):
                        _set(W, x, y, z, 'beam')
            xl = xx0 + 2 * ox
            for y in (py0, py1):
                for z in range(zf - 4, zf):
                    _set(W, xl, y, z, 'beam')
            for i, x in enumerate(xs):
                for y in range(py0 - 1, py1 + 2):
                    _set(W, x, y, zf - 5 + i, 'roof_b')
    # ---- lantern by the door and a door ramp down to the ground
    for (dx0, dy0, (ox, oy)) in doors:
        if lamp_out:
            lx, ly = (dx0 - 1, dy0 + oy) if oy else (dx0 + ox, dy0 - 1)
            _set(W, lx, ly, zf - 4, 'beam')
            W.pt(lx, ly, zf - 5, 'lamp')
        for k in range(1, 4):
            for wv in (0, 1):
                xx = dx0 + ox * k + (wv if oy else 0)
                yy = dy0 + oy * k + (wv if ox else 0)
                if 0 <= xx < 512 and 0 <= yy < 512:
                    level = zf + (k - 1)
                    h0 = int(H[xx, yy])
                    if level < h0 < 62:
                        W.m[xx, yy, level:h0] = MAT['pack']
                        W.m[xx, yy, level] = MAT['track']
                        H[xx, yy] = level
    if register:
        W.structures.append({'name': name, 'box': [x0 - 1, x1 + 1, y0 - 1, y1 + 1], 'role': role})
    return {'zf': zf, 'ze': ze, 'top_z': top_z, 'doors': doors, 'box': (x0, x1, y0, y1)}


def _window(W, x, y, zb, along):
    """2 wide x 2 high opening with a trim frame. `along` is the wall direction ('x' or 'y')."""
    if along == 'x':
        for xx in (x, x + 1):
            for z in (zb, zb - 1):
                W.m[xx, y, z] = 0
        for z in (zb + 1, zb - 2):
            _set(W, x, y, z, 'trim'); _set(W, x + 1, y, z, 'trim')
        for z in (zb, zb - 1):
            _set(W, x - 1, y, z, 'beam'); _set(W, x + 2, y, z, 'beam')
    else:
        for yy in (y, y + 1):
            for z in (zb, zb - 1):
                W.m[x, yy, z] = 0
        for z in (zb + 1, zb - 2):
            _set(W, x, y, z, 'trim'); _set(W, x, y + 1, z, 'trim')
        for z in (zb, zb - 1):
            _set(W, x, y - 1, z, 'beam'); _set(W, x, y + 2, z, 'beam')


# ------------------------------------------------------------------ yard props (each a small story)
def woodpile(W, H, x, y, n=6, axis='x'):
    g = int(H[x, y])
    for i in range(n):
        xx, yy = (x + i, y) if axis == 'x' else (x, y + i)
        for z in range(g - 3, g):
            _set(W, xx, yy, z, 'dwood' if (i + z) % 2 else 'plank')
    _set(W, x, y, g - 4, 'snow_roof')


def sled_rack(W, H, x, y):
    """Sleds stood on end against a rail: 3-4 tall cover with gaps."""
    g = int(H[x, y])
    for i in range(0, 7, 2):
        for z in range(g - 4, g):
            _set(W, x + i, y, z, 'dwood')
        _set(W, x + i, y, g - 4, 'orange' if i % 4 == 0 else 'dwood')
    for i in range(7):
        _set(W, x + i, y + 1, g - 3, 'beam')


def drum_stack(W, H, x, y):
    g = int(H[x, y])
    for dx, dy, h, c in ((0, 0, 3, 'drum_r'), (2, 0, 3, 'drum_b'), (0, 2, 3, 'drum_r'), (1, 1, 6, 'drum_r')):
        for z in range(g - h, g):
            _set(W, x + dx, y + dy, z, c)
            _set(W, x + dx + 1, y + dy, z, c)


def crate_stack(W, H, x, y, h=4):
    g = int(H[x, y])
    W.box(x, x + 2, y, y + 2, g - 3, g - 1, 'plank')
    W.box(x, x + 2, y, y + 2, g - 3, g - 3, 'beam')
    if h > 3:
        W.box(x + 1, x + 2, y + 1, y + 2, g - h - 1, g - 4, 'plank')
    W.box(x + 3, x + 4, y, y + 1, g - 2, g - 1, 'plank')


def snow_wall(W, H, x0, y0, x1, y1, h=3):
    """Cut-block snow wall (expedition windbreak), 2 thick, with a capping row."""
    n = max(abs(x1 - x0), abs(y1 - y0))
    for i in range(n + 1):
        x = round(x0 + (x1 - x0) * i / max(n, 1)); y = round(y0 + (y1 - y0) * i / max(n, 1))
        W.keep[x - 1:x + 3, y - 1:y + 3] = True
        for (ax, ay) in ((0, 0), (1, 0) if y1 != y0 else (0, 1)):
            g = int(H[x + ax, y + ay])
            for z in range(g - h, g):
                joint = (i % 3 == 0 and (g - z) % 2 == 1) or ((i + 1) % 3 == 0 and (g - z) % 2 == 0)
                _set(W, x + ax, y + ay, z, 'track' if joint else 'pack')
            _set(W, x + ax, y + ay, g - h - 1, 'snow')


def flagpole(W, H, x, y, h=12, colour='flag_r'):
    g = int(H[x, y])
    for z in range(g - h, g):
        _set(W, x, y, z, 'steel')
    for z in range(g - h, g - h + 3):
        for k in range(1, 5):
            _set(W, x + k, y, z, colour)


def antenna(W, H, x, y, h=16):
    g = int(H[x, y])
    for z in range(g - h, g):
        _set(W, x, y, z, 'steel')
    for z in (g - h + 3, g - h + 8):
        for k in range(-3, 4):
            _set(W, x + k, y, z, 'steel')
    W.pt(x, y, g - h - 1, 'lamp')


# ------------------------------------------------------------------ composed structures
def station(W, H, x0, y0, family='red', name='station', flip=False):
    """Polar research station: two-storey main hall (22 x 12) + perpendicular lab wing (11 x 12) + covered porch,
    stone chimney, radio antenna and a yard of fuel drums, crates, sled rack and woodpile."""
    zf = pad(W, H, x0 - 3, x0 + 36, y0 - 3, y0 + 26)
    a = building(W, H, x0, y0, 22, 12, floors=2, storey=5, family=family, ridge='long', door=('S', x0 + 6),
                 chimney='W', porch=True, name=name + '_hall', role='main', zf=zf, register=False)
    b = building(W, H, x0 + 22, y0 - 4, 11, 16, floors=1, storey=6, family='grey', ridge='long', door=(('S', 'E'), None),
                 chimney=None, name=name + '_lab', role='main', zf=zf, register=False)
    for z in range(zf - 3, zf):                                    # inside door between hall and wing
        W.m[x0 + 21, y0 + 5:y0 + 7, z] = 0
        W.m[x0 + 22, y0 + 5:y0 + 7, z] = 0
    antenna(W, H, x0 + 27, y0 - 7, 18)
    drum_stack(W, H, x0 + 15, y0 + 15)
    crate_stack(W, H, x0 + 24, y0 + 15, 5)
    sled_rack(W, H, x0 - 1, y0 + 16)
    woodpile(W, H, x0 - 4, y0 + 2, 6, 'y')
    flagpole(W, H, x0 + 11, y0 + 18, 13)
    W.structures.append({'name': name, 'box': [x0 - 1, x0 + 33, y0 - 5, y0 + 12], 'role': 'main'})
    return zf


def lodge(W, H, x0, y0, name='lodge'):
    """Expedition lodge behind a spawn: long timber hall (24 x 12, two floors) with a gabled front wing (9 x 9)
    facing the spawn, porch, chimney, woodpile, sled rack, crates and lanterns."""
    zf = pad(W, H, x0 - 3, x0 + 23, y0 - 4, y0 + 28)
    building(W, H, x0, y0, 12, 24, floors=2, storey=5, family='wood', ridge='long', door=('E', y0 + 6),
             chimney='W', porch=True, name=name + '_hall', zf=zf, register=False, snow=0.7)
    building(W, H, x0 + 12, y0 + 14, 9, 9, floors=1, storey=6, family='red', ridge='short', door=('E', None),
             chimney=None, name=name + '_wing', zf=zf, register=False)
    for z in range(zf - 3, zf):
        W.m[x0 + 11:x0 + 13, y0 + 17:y0 + 19, z] = 0
    woodpile(W, H, x0 + 2, y0 - 3, 7, 'x')
    flagpole(W, H, x0 + 14, y0 + 2, 12, 'flag_b')
    W.structures.append({'name': name, 'box': [x0 - 1, x0 + 22, y0 - 1, y0 + 24], 'role': 'main'})
    return zf


def cabin(W, H, x0, y0, family='red', door='S', name='cabin', porch=False):
    """Small gabled cabin 9 x 7: stone base, board courses, trimmed door and windows, stovepipe, snow on the roof."""
    building(W, H, x0, y0, 11, 9, floors=1, storey=6, family=family, ridge='long', door=(door, None),
             chimney='E' if door in ('S', 'N') else 'N', porch=True, name=name, role='small')
    woodpile(W, H, x0 - 3, y0 + 1, 5, 'y')
    drum_stack(W, H, x0 + 12, y0 + (8 if door == 'S' else -2))


def observation_tower(W, H, x0, y0, name='tower'):
    """Observation tower: 9 x 9 stone base storey, a timber upper storey with framed windows, a railed gallery,
    a hip roof with snow and an anemometer mast; stairs inside to the gallery."""
    zf = pad(W, H, x0 - 3, x0 + 11, y0 - 3, y0 + 11)
    g = building(W, H, x0, y0, 9, 9, floors=3, storey=6, family='grey', roof='hip', door=('S', None),
                 chimney=None, name=name, role='tower', zf=zf, register=False, snow=0.35, pitch=2)
    # stone lower storey: re-skin the lower 6 wall rows in stone courses
    for x in range(x0, x0 + 9):
        for y in range(y0, y0 + 9):
            if x in (x0, x0 + 8) or y in (y0, y0 + 8):
                for z in range(zf - 12, zf):
                    if W.m[x, y, z] != 0 and W.m[x, y, z] != MAT['trim'] and W.m[x, y, z] != MAT['beam']:
                        W.m[x, y, z] = MAT['stone'] if (x + y + z) % 3 else MAT['stone_b']
    # gallery: a railed walkway ring one voxel outside the upper floor
    zg = zf - 12
    for x in range(x0 - 1, x0 + 10):
        for y in range(y0 - 1, y0 + 10):
            if x in (x0 - 1, x0 + 9) or y in (y0 - 1, y0 + 9):
                _set(W, x, y, zg, 'plank')
                if (x + y) % 2 == 0:
                    _set(W, x, y, zg - 1, 'beam')
    for z in range(zg - 3, zg):                                  # door out onto the gallery (upper floor, south)
        W.m[x0 + 4:x0 + 6, y0 + 8, z] = 0
    top = g['top_z']
    for z in range(top - 6, top):
        _set(W, x0 + 4, y0 + 4, z, 'steel')
    for k in (-2, -1, 1, 2):
        _set(W, x0 + 4 + k, y0 + 4, top - 5, 'steel')
    W.pt(x0 + 4, y0 + 4, top - 7, 'lamp')
    W.structures.append({'name': name, 'box': [x0 - 2, x0 + 10, y0 - 2, y0 + 10], 'role': 'tower'})
    return zf
