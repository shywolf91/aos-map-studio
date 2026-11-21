"""Frozen Icebreaker architecture and props (docs/craft_standard.md §2).

`house()` builds every hut / hall / lab: concrete base course, cladding in board courses of two close tones,
contrasting corner posts, a string course per upper floor, framed doors (2 x 3) and windows (2 x 2), a 45-degree
gable or hip roof with 1-voxel eaves, plank rows in two tones, a ridge cap and snow on the upper slope, closed
gables, a chimney or stovepipe, rooms on 1-3 floors joined by kit straight stairs, furniture, ceiling lamps (glow),
a door lantern and an optional porch. Composed buildings combine volumes. Props are small stories (woodpile, sled
rack, drums, crates, snowmobile, tents ...), each face-connected to the ground it stands on.
"""
from __future__ import annotations

from aosmap.kit import structures
from fi_world import P, boxm, put, lamp, pad, reg, top, tone, _h


# ------------------------------------------------------------------------------------------------ house
def house(cv, x0, y0, w, d, floors=1, storey=5, fam='ochre', ridge='long', roof='gable', doors=(('S', None),),
          chimney='E', porch=False, snow=0.55, name='house', role='small', zf=None, pitch=1, register=True,
          furnish=True, lantern=True, roofmat='roof', base='concrete'):
    """Footprint x0..x0+w-1, y0..y0+d-1; zf = floor z players stand on (default: pad to the median ground)."""
    x1, y1 = x0 + w - 1, y0 + d - 1
    if zf is None:
        zf = pad(cv, x0 - 2, x1 + 2, y0 - 2, y1 + 2)
    cv.no_prop(x0 - 5, x1 + 5, y0 - 5, y1 + 5)
    ze = zf - floors * storey                     # top wall row is ze + 1
    clad = 'clad_' + fam
    # walls + interior air
    boxm(cv, x0, x1, y0, y1, ze + 1, zf - 1, clad, 'building', 'course', salt=x0)
    cv.carve(x0 + 1, x1 - 1, y0 + 1, y1 - 1, ze + 1, zf - 1)
    boxm(cv, x0, x1, y0, y1, zf - 2, zf - 1, base, 'building', 'block')            # base course (2 rows)
    cv.carve(x0 + 1, x1 - 1, y0 + 1, y1 - 1, zf - 2, zf - 1)
    boxm(cv, x0 + 1, x1 - 1, y0 + 1, y1 - 1, zf, zf, 'floor', 'building', 'col')    # floor boards
    for (cx, cy) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):                         # corner posts
        boxm(cv, cx, cx, cy, cy, ze + 1, zf - 3, 'beam', 'building')
    for f in range(1, floors):                                                       # string course + slab
        zs = zf - f * storey
        boxm(cv, x0, x1, y0, y1, zs, zs, 'trim', 'building')
        boxm(cv, x0 + 1, x1 - 1, y0 + 1, y1 - 1, zs, zs, 'floor', 'building', 'col')
    boxm(cv, x0, x1, y0, y1, ze + 1, ze + 1, 'beam', 'building')                      # wall plate under the eaves
    cv.carve(x0 + 1, x1 - 1, y0 + 1, y1 - 1, ze + 1, ze + 1)
    # roof
    along_y = (ridge == 'long' and d >= w) or (ridge == 'short' and d < w)
    rx0, rx1, ry0, ry1 = x0 - 1, x1 + 1, y0 - 1, y1 + 1
    tmax = ((rx1 - rx0) // 2 if along_y else (ry1 - ry0) // 2)
    if roof == 'hip':
        tmax = min((rx1 - rx0) // 2, (ry1 - ry0) // 2)
    top_z = ze
    for x in range(rx0, rx1 + 1):
        for y in range(ry0, ry1 + 1):
            if roof == 'hip':
                t = min(x - rx0, rx1 - x, y - ry0, ry1 - y)
            else:
                t = min(x - rx0, rx1 - x) if along_y else min(y - ry0, ry1 - y)
            z = ze - t * pitch + 1
            top_z = min(top_z, z)
            nm = roofmat if t % 2 == 0 else roofmat
            for k in range(pitch + 1 if t > 0 else 1):                       # eave row 1 thick: door headroom
                put(cv, x, y, z + k, nm, 'roof', salt=t)
            if t >= tmax:
                put(cv, x, y, z, 'ridge', 'roof')
            elif snow and t >= tmax * (1 - snow) and _h(x // 3, y // 3, 0, 7) % 7 != 0:
                put(cv, x, y, z, 'snow_roof', 'roof')
    if roof == 'gable':                                                              # closed gable triangles
        for e in ((y0, y1) if along_y else (x0, x1)):
            lo, hi = (x0, x1) if along_y else (y0, y1)
            for u in range(lo, hi + 1):
                t = (min(u - lo, hi - u) + 1) * pitch
                for z in range(ze - t + 2, ze + 1):
                    if along_y:
                        put(cv, u, e, z, clad, 'building', salt=x0)
                    else:
                        put(cv, e, u, z, clad, 'building', salt=x0)
    # doors with trim frames + outside step
    dl = []
    for (s, pos) in doors:
        if s in ('S', 'N'):
            yy = y1 if s == 'S' else y0
            xc = pos if pos is not None else (x0 + x1) // 2
            cv.carve(xc, xc + 1, yy, yy, zf - 3, zf - 1)
            boxm(cv, xc - 1, xc - 1, yy, yy, zf - 4, zf - 1, 'trim', 'building')
            boxm(cv, xc + 2, xc + 2, yy, yy, zf - 4, zf - 1, 'trim', 'building')
            boxm(cv, xc, xc + 1, yy, yy, zf - 4, zf - 4, 'trim', 'building')
            dl.append((xc, yy, (0, 1 if s == 'S' else -1)))
        else:
            xx = x1 if s == 'E' else x0
            yc = pos if pos is not None else (y0 + y1) // 2
            cv.carve(xx, xx, yc, yc + 1, zf - 3, zf - 1)
            boxm(cv, xx, xx, yc - 1, yc - 1, zf - 4, zf - 1, 'trim', 'building')
            boxm(cv, xx, xx, yc + 2, yc + 2, zf - 4, zf - 1, 'trim', 'building')
            boxm(cv, xx, xx, yc, yc + 1, zf - 4, zf - 4, 'trim', 'building')
            dl.append((xx, yc, (1 if s == 'E' else -1, 0)))
    # windows: 2 x 2 openings every 5, framed, on every floor
    for f in range(floors):
        zb = zf - f * storey - 2
        for x in range(x0 + 2, x1 - 2, 5):
            for yy in (y0, y1):
                if f == 0 and any(abs(x - a) <= 3 and b == yy for a, b, _ in dl):
                    continue
                _window(cv, x, yy, zb, 'x')
        for y in range(y0 + 2, y1 - 2, 5):
            for xx in (x0, x1):
                if f == 0 and any(abs(y - b) <= 3 and a == xx for a, b, _ in dl):
                    continue
                _window(cv, xx, y, zb, 'y')
    # chimney / stovepipe outside a wall, 2 above the roof top
    if chimney:
        cx, cy = {'E': (x1 + 1, (y0 + y1) // 2), 'W': (x0 - 2, (y0 + y1) // 2),
                  'N': ((x0 + x1) // 2, y0 - 2), 'S': ((x0 + x1) // 2, y1 + 1)}[chimney]
        g = max(top(cv, cx, cy), top(cv, cx + 1, cy + 1))
        boxm(cv, cx, cx + 1, cy, cy + 1, top_z - 3, g, 'stone', 'building', 'block')
        boxm(cv, cx, cx + 1, cy, cy + 1, top_z - 4, top_z - 4, 'dsteel', 'building')
    # stairs (after every slab exists so the cut-outs open the slab above)
    inner_x = w - 2
    for f in range(1, floors):
        zlo = zf - (f - 1) * storey
        if inner_x >= storey + 4:
            sy = y0 + 1 if f % 2 else y1 - 2
            sx = x0 + 2 if f % 2 else x1 - 2
            structures.straight_stair(cv, sx, sy, sy + 1, zlo, storey, 1 if f % 2 else -1, tone('beam', 0, 0, 0),
                                      'building')
        else:
            sx = x0 + 1 if f % 2 else x1 - 2
            sy = y0 + 2 if f % 2 else y1 - 2
            structures.straight_stair(cv, sy, sx, sx + 1, zlo, storey, 1 if f % 2 else -1, tone('beam', 0, 0, 0),
                                      'building', along='y')
    # rooms: furniture, ceiling lamp, interiors record
    lx, ly = (x0 + x1) // 2, (y0 + y1) // 2
    for f in range(floors):
        zfl = zf - f * storey
        if furnish and w >= 7 and d >= 7:
            boxm(cv, x1 - 1, x1 - 1, y1 - 2, y1 - 1, zfl - 2, zfl - 1, 'furn', 'building')      # cupboard
            boxm(cv, x0 + 1, x0 + 2, y1 - 1, y1 - 1, zfl - 1, zfl - 1, 'plank', 'building')     # bunk
            if w >= 10:
                boxm(cv, lx - 1, lx, ly - 2, ly - 2, zfl - 2, zfl - 2, 'furn', 'building')     # table
                boxm(cv, lx - 1, lx - 1, ly - 2, ly - 2, zfl - 1, zfl - 1, 'furn', 'building')
        zz = zfl - 1
        while zz > 0 and not cv.solid[lx, ly, zz]:
            zz -= 1
        if zfl - zz >= 5:                                                        # ceiling lamp, 3+ headroom kept
            lamp(cv, lx, ly, zz + 1, 'warm')
        cv.interiors.append([f'{name} f{f}', lx, ly + 1, zfl])
    # porch on the first door: deck + posts + lean-to roof
    if porch and dl:
        _porch(cv, dl[0], zf)
    for (a, b, (ox, oy)) in dl:
        if lantern:
            lx2, ly2 = (a - 1, b + oy) if oy else (a + ox, b - 1)
            if not porch or (a, b) != dl[0][:2]:
                put(cv, lx2, ly2, zf - 4, 'beam', 'building')
                lamp(cv, lx2, ly2, zf - 5, 'amber')
        for k in range(1, 4):                                                    # door apron: packed snow
            for wv in (0, 1):
                xx, yy = a + ox * k + (wv if oy else 0), b + oy * k + (wv if ox else 0)
                if 0 <= xx < 512 and 0 <= yy < 512 and not cv.solid[xx, yy, zf - 1] and cv.solid[xx, yy, zf]:
                    put(cv, xx, yy, zf, 'track', 'ground')
    if register:
        reg(name, (x0 - 1, x1 + 1, y0 - 1, y1 + 1), role)
    return {'zf': zf, 'ze': ze, 'top_z': top_z, 'doors': dl, 'box': (x0, x1, y0, y1)}


def _window(cv, x, y, zb, along):
    if along == 'x':
        cv.carve(x, x + 1, y, y, zb - 1, zb)
        boxm(cv, x, x + 1, y, y, zb + 1, zb + 1, 'trim', 'building')
        boxm(cv, x, x + 1, y, y, zb - 2, zb - 2, 'trim', 'building')
        boxm(cv, x - 1, x - 1, y, y, zb - 1, zb, 'beam', 'building')
        boxm(cv, x + 2, x + 2, y, y, zb - 1, zb, 'beam', 'building')
    else:
        cv.carve(x, x, y, y + 1, zb - 1, zb)
        boxm(cv, x, x, y, y + 1, zb + 1, zb + 1, 'trim', 'building')
        boxm(cv, x, x, y, y + 1, zb - 2, zb - 2, 'trim', 'building')
        boxm(cv, x, x, y - 1, y - 1, zb - 1, zb, 'beam', 'building')
        boxm(cv, x, x, y + 2, y + 2, zb - 1, zb, 'beam', 'building')


def _porch(cv, door, zf):
    a, b, (ox, oy) = door
    if oy:
        ys = [b + oy * k for k in (1, 2, 3)]
        xa, xb = a - 3, a + 4
        for y in ys:
            boxm(cv, xa, xb, y, y, zf, zf, 'plank', 'building', 'col')
        yl = ys[-1]
        for x in (xa, xb):
            boxm(cv, x, x, yl, yl, zf - 4, zf - 1, 'beam', 'building')
        for i, y in enumerate(ys):
            boxm(cv, xa - 1, xb + 1, y, y, zf - 5 + i, zf - 5 + i, 'roof_wood', 'roof')
        lamp(cv, a, ys[0], zf - 4, 'amber')
    else:
        xs = [a + ox * k for k in (1, 2, 3)]
        ya, yb = b - 3, b + 4
        for x in xs:
            boxm(cv, x, x, ya, yb, zf, zf, 'plank', 'building', 'col')
        xl = xs[-1]
        for y in (ya, yb):
            boxm(cv, xl, xl, y, y, zf - 4, zf - 1, 'beam', 'building')
        for i, x in enumerate(xs):
            boxm(cv, x, x, ya - 1, yb + 1, zf - 5 + i, zf - 5 + i, 'roof_wood', 'roof')
        lamp(cv, xs[0], b, zf - 4, 'amber')


# ------------------------------------------------------------------------------------------------ props
def g_at(cv, x, y):
    """Floor z for a prop: the column top (props stand on whatever surface is there)."""
    return top(cv, x, y)


def woodpile(cv, x, y, n=6, axis='x'):
    g = g_at(cv, x, y)
    for i in range(n):
        xx, yy = (x + i, y) if axis == 'x' else (x, y + i)
        for z in range(g - 3, g):
            put(cv, xx, yy, z, 'log' if (i + z) % 2 else 'dwood')
        if axis == 'x':
            put(cv, xx, yy + 1, g - 1, 'log')
        else:
            put(cv, xx + 1, yy, g - 1, 'log')
    put(cv, x + (1 if axis == 'x' else 0), y + (0 if axis == 'x' else 1), g - 4, 'snow_roof')


def drum_stack(cv, x, y, kinds=('drum_y', 'drum_g', 'drum_s')):
    g = g_at(cv, x, y)
    for i, (dx, dy, h) in enumerate(((0, 0, 3), (2, 0, 3), (0, 2, 3), (2, 2, 2), (1, 1, 5))):
        k = kinds[i % len(kinds)]
        boxm(cv, x + dx, x + dx + 1, y + dy, y + dy, g - h, g - 1, k)
        put(cv, x + dx, y + dy, g - h, 'dsteel')


def crate_stack(cv, x, y, h=4):
    g = g_at(cv, x, y)
    boxm(cv, x, x + 2, y, y + 2, g - 3, g - 1, 'plank', mode='course')
    boxm(cv, x, x + 2, y, y + 2, g - 3, g - 3, 'beam')
    if h > 3:
        boxm(cv, x + 1, x + 2, y + 1, y + 2, g - h - 1, g - 4, 'plank', mode='course')
    boxm(cv, x + 3, x + 4, y, y + 1, g - 2, g - 1, 'plank')


def sled_rack(cv, x, y, axis='x'):
    g = g_at(cv, x, y)
    for i in range(0, 7, 2):
        xx, yy = (x + i, y) if axis == 'x' else (x, y + i)
        boxm(cv, xx, xx, yy, yy, g - 4, g - 1, 'dwood')
        put(cv, xx, yy, g - 4, 'canvas_o' if i % 4 == 0 else 'plank')
    for i in range(7):
        xx, yy = (x + i, y + 1) if axis == 'x' else (x + 1, y + i)
        put(cv, xx, yy, g - 3, 'beam')
        put(cv, xx, yy, g - 2, 'beam')
        put(cv, xx, yy, g - 1, 'beam')


def snowmobile(cv, x, y, axis='x', body='canvas_o'):
    """6 x 3 snowmobile on skis: track base, body, seat, windscreen, handlebar (3 tall)."""
    g = g_at(cv, x, y)
    L, W = (6, 3) if axis == 'x' else (3, 6)
    def at(i, j):
        return (x + i, y + j) if axis == 'x' else (x + j, y + i)
    for i in range(6):
        for j in range(3):
            xx, yy = at(i, j)
            if j == 1 or i in (0, 5):
                put(cv, xx, yy, g - 1, 'dsteel')
            else:
                put(cv, xx, yy, g - 1, 'black')
            if 1 <= i <= 5:
                put(cv, xx, yy, g - 2, body if i < 4 else 'black')
    for i in (2, 3):
        xx, yy = at(i, 1)
        put(cv, xx, yy, g - 3, 'black')
    xx, yy = at(1, 1)
    put(cv, xx, yy, g - 3, 'glass')
    xx, yy = at(0, 0); put(cv, xx, yy, g - 1, 'steel')
    xx, yy = at(0, 2); put(cv, xx, yy, g - 1, 'steel')


def cargo_sled(cv, x, y, axis='x'):
    g = g_at(cv, x, y)
    for i in range(9):
        for j in range(4):
            xx, yy = (x + i, y + j) if axis == 'x' else (x + j, y + i)
            if j in (0, 3):
                put(cv, xx, yy, g - 1, 'dwood')
            elif i % 2 == 0:
                put(cv, xx, yy, g - 1, 'plank')
            else:
                put(cv, xx, yy, g - 1, 'dwood')
    g2 = g - 1                                                                # load: crates + tarp, one block
    if axis == 'x':
        boxm(cv, x + 1, x + 4, y, y + 3, g2 - 3, g2 - 1, 'plank', mode='course')
        boxm(cv, x + 5, x + 7, y, y + 3, g2 - 2, g2 - 1, 'canvas_k')
        boxm(cv, x + 1, x + 2, y + 1, y + 2, g2 - 4, g2 - 4, 'canvas_o')
    else:
        boxm(cv, x, x + 3, y + 1, y + 4, g2 - 3, g2 - 1, 'plank', mode='course')
        boxm(cv, x, x + 3, y + 5, y + 7, g2 - 2, g2 - 1, 'canvas_k')
        boxm(cv, x + 1, x + 2, y + 1, y + 2, g2 - 4, g2 - 4, 'canvas_o')


def tent(cv, x, y, fam='canvas_o', size=7, name=None):
    """Pyramid (Scott) polar tent: square base, sloping canvas walls to a peak, guy-line valance in khaki,
    a door flap opening and a pole tip. Hollow; one room."""
    g = g_at(cv, x + size // 2, y + size // 2)
    h = size // 2 + 2
    for k in range(h):
        z = g - 1 - k
        r = size // 2 - k // 2 if k >= 2 else size // 2
        if r < 0:
            break
        cx, cy = x + size // 2, y + size // 2
        boxm(cv, cx - r, cx + r, cy - r, cy + r, z, z, fam if k else 'canvas_k', 'building', 'course')
        if r >= 1 and k < h - 2:
            cv.carve(cx - r + 1, cx + r - 1, cy - r + 1, cy + r - 1, z, z)
    cx, cy = x + size // 2, y + size // 2
    put(cv, cx, cy, g - 1 - h, 'beam', 'building')
    # door flap facing east and west
    cv.carve(x + size - 1, x + size - 1, cy, cy, g - 3, g - 1)
    cv.carve(x, x, cy, cy, g - 3, g - 1)
    lamp(cv, cx, cy, g - h + 1, 'warm') if size >= 7 else None
    # valance snow skirt
    for (a, b) in ((x - 1, y + 1), (x - 1, y + size - 2), (x + size, y + 1), (x + size, y + size - 2)):
        put(cv, a, b, g_at(cv, a, b) - 1, 'snow_roof')


def ice_block(cv, x, y, w, d, h, tilt=0, name='ice'):
    """A tilted slab of pack ice (a wedge, not a pillar): h at the low edge rising by `tilt` across x, blue glass
    sides with darker strata, a snow-dusted top face and a broken (notched) upper edge."""
    for i in range(w):
        for j in range(d):
            hh = h + (tilt * i // max(w - 1, 1) if tilt >= 0 else -tilt * (w - 1 - i) // max(w - 1, 1))
            if (i in (0, w - 1)) and (j in (0, d - 1)):
                hh -= 1                                                        # rounded corners
            if _h(x + i, y + j, 0, 11) % 5 == 0:
                hh -= 1                                                        # notched, broken top edge
            hh = max(hh, 1)
            gg = g_at(cv, x + i, y + j)
            for z in range(gg - hh, gg):
                nm = 'ice_cap' if z == gg - hh else ('ice_deep' if (z + x // 3) % 4 == 0 else 'ice')
                put(cv, x + i, y + j, z, nm, 'ice')


def rubble(cv, rng, cx, cy, n=8, spread=6, hmin=2, hmax=5, avoid=None):
    """Pressure-ridge rubble: n tilted ice blocks around (cx, cy)."""
    for _ in range(n):
        x = int(cx + rng.integers(-spread, spread + 1))
        y = int(cy + rng.integers(-spread, spread + 1))
        if avoid is not None and avoid(x, y):
            continue
        w, d = int(rng.integers(3, 7)), int(rng.integers(3, 5))
        ice_block(cv, x, y, w, d, int(rng.integers(hmin, hmax + 1)), int(rng.integers(-3, 4)))


def heap(cv, rng, cx, cy, n=6, hmin=3, hmax=6):
    """A contiguous heap of tilted floes: each block overlaps the previous one (reads as one pressure heap and
    counts as one object)."""
    x, y = cx, cy
    for _ in range(n):
        w, d = int(rng.integers(4, 7)), int(rng.integers(3, 6))
        ice_block(cv, x, y, w, d, int(rng.integers(hmin, hmax - 1)), int(rng.integers(-3, 4)))
        x += int(rng.integers(-2, 3))
        y += int(rng.integers(-2, 3))


def flagpole(cv, x, y, h=12, flag='team', mat='team'):
    g = g_at(cv, x, y)
    boxm(cv, x, x, y, y, g - h, g - 1, 'flag_pole', 'prop')
    for z in range(g - h, g - h + 3):
        for k in range(1, 5):
            cv.set(x + k, y, z, tone(flag, x + k, y, z), mat)
    put(cv, x, y, g - h - 1, 'steel')


def antenna(cv, x, y, h=16):
    g = g_at(cv, x, y)
    boxm(cv, x, x, y, y, g - h, g - 1, 'steel', 'prop')
    for z in (g - h + 3, g - h + 8):
        for k in (-2, -1, 1, 2):
            put(cv, x + k, y, z, 'steel')
    lamp(cv, x, y, g - h - 1, 'amber')


def lamp_post(cv, x, y, h=6, kind='amber'):
    g = g_at(cv, x, y)
    boxm(cv, x, x, y, y, g - h, g - 1, 'dsteel', 'prop')
    put(cv, x + 1, y, g - h, 'dsteel')
    lamp(cv, x + 1, y, g - h + 1, kind)


def snow_wall(cv, x0, y0, x1, y1, h=3, thick=2):
    """Cut-block snow windbreak, 2 thick, staggered joints, capped."""
    n = max(abs(x1 - x0), abs(y1 - y0))
    for i in range(n + 1):
        x = round(x0 + (x1 - x0) * i / max(n, 1))
        y = round(y0 + (y1 - y0) * i / max(n, 1))
        offs = [(k, 0) for k in range(thick)] if abs(y1 - y0) > abs(x1 - x0) else [(0, k) for k in range(thick)]
        for (ax, ay) in offs:
            g = g_at(cv, x + ax, y + ay)
            for z in range(g - h, g):
                joint = (i % 3 == 0 and (g - z) % 2 == 1) or ((i + 1) % 3 == 0 and (g - z) % 2 == 0)
                put(cv, x + ax, y + ay, z, 'snow_trough' if joint else 'snow', 'prop')
            put(cv, x + ax, y + ay, g - h - 1, 'snow_crest', 'prop')


def ski_rack(cv, x, y):
    g = g_at(cv, x, y)
    for i in range(5):
        boxm(cv, x + i, x + i, y, y, g - 4, g - 1, 'canvas_o' if i % 2 else 'yellow')
    boxm(cv, x - 1, x + 5, y + 1, y + 1, g - 3, g - 3, 'beam')
    put(cv, x - 1, y + 1, g - 2, 'beam'); put(cv, x - 1, y + 1, g - 1, 'beam')
    put(cv, x + 5, y + 1, g - 2, 'beam'); put(cv, x + 5, y + 1, g - 1, 'beam')


def generator(cv, x, y):
    g = g_at(cv, x, y)
    boxm(cv, x, x + 4, y, y + 2, g - 3, g - 1, 'container_g', mode='course')
    boxm(cv, x, x + 4, y, y + 2, g - 3, g - 3, 'dsteel')
    boxm(cv, x + 4, x + 4, y + 1, y + 1, g - 6, g - 4, 'dsteel')
    lamp(cv, x, y + 1, g - 4, 'amber')


def core_boxes(cv, x, y):
    """Ice-core shipping boxes: insulated white-grey crates in a stack of 2 rows."""
    g = g_at(cv, x, y)
    boxm(cv, x, x + 8, y, y + 4, g - 2, g - 1, 'container_s', mode='course')
    for i in (2, 5):                                                          # box seams
        boxm(cv, x + i, x + i, y, y + 4, g - 2, g - 1, 'dsteel')
    boxm(cv, x + 1, x + 4, y + 1, y + 3, g - 4, g - 3, 'canvas_k')


def seal(cv, x, y, axis='x'):
    """Ringed seal hauled out beside a breathing hole: 7 long, 2 tall, darker back, flippers."""
    g = g_at(cv, x, y)
    for i in range(7):
        w = 1 if i in (0, 6) else 2
        for j in range(w):
            xx, yy = (x + i, y + j) if axis == 'x' else (x + j, y + i)
            put(cv, xx, yy, g - 1, 'seal')
            if 1 <= i <= 4:
                put(cv, xx, yy, g - 2, 'seal', salt=3)
    hx, hy = (x - 3, y) if axis == 'x' else (x, y - 3)
    for dx in (0, 1):
        for dy in (0, 1):
            put(cv, hx + dx, hy + dy, g, 'lead', 'ground')


def walrus(cv, x, y, axis='x', rngv=0):
    g = g_at(cv, x, y)
    for i in range(9):
        w = 3 if 2 <= i <= 6 else 2
        for j in range(w):
            xx, yy = (x + i, y + j) if axis == 'x' else (x + j, y + i)
            for z in range(g - (3 if 2 <= i <= 6 else 2), g):
                put(cv, xx, yy, z, 'walrus', salt=rngv)
    tx, ty = (x - 1, y + 1) if axis == 'x' else (x + 1, y - 1)
    put(cv, tx, ty, g - 1, 'tusk')
    put(cv, tx, ty + (0 if axis == 'x' else 0), g - 1, 'tusk')


def polar_bear(cv, x, y, scale=1, facing=1):
    """Polar bear (body 12 x 5 x 6 at scale 1): legs, rounded body, head with dark nose and eyes."""
    g = g_at(cv, x + 6, y + 2)
    L = 12 * scale
    for i in range(L):
        t = i / max(L - 1, 1)
        hgt = int(round((4 + 2 * (1 - abs(t - 0.45) * 2)) * scale))
        wid = 5 * scale if 0.15 < t < 0.8 else 4 * scale
        for j in range(wid):
            for z in range(g - 2 * scale - hgt, g - 2 * scale):
                xx = x + (i if facing > 0 else L - 1 - i)
                put(cv, xx, y + j - (wid - 5 * scale) // 2, z, 'fur', 'prop', salt=1)
    for (i, j) in ((1, 0), (1, 4), (9, 0), (9, 4)):                      # legs
        for di in range(scale):
            for dj in range(scale):
                xx = x + (i * scale + di if facing > 0 else L - 1 - i * scale - di)
                boxm(cv, xx, xx, y + j * scale + dj, y + j * scale + dj, g - 2 * scale, g - 1, 'fur')
    hx = x + L if facing > 0 else x - 4 * scale
    hz = g - 2 * scale - 5 * scale
    boxm(cv, hx, hx + 4 * scale - 1, y + scale, y + 4 * scale - 1, hz, hz + 3 * scale - 1, 'fur')
    nose_x = hx + 4 * scale if facing > 0 else hx - 1
    boxm(cv, nose_x, nose_x, y + 2 * scale, y + 3 * scale - 1, hz + scale, hz + 2 * scale - 1, 'fur_dark')
    ex = hx + 3 * scale if facing > 0 else hx
    put(cv, ex, y + scale, hz, 'black'); put(cv, ex, y + 4 * scale - 1, hz, 'black')
    put(cv, hx + (scale if facing > 0 else 2 * scale), y + scale, hz - 1, 'fur')       # ears
    put(cv, hx + (scale if facing > 0 else 2 * scale), y + 4 * scale - 1, hz - 1, 'fur')


def cairn(cv, x, y, cross=True):
    """Expedition cairn of stacked stone with a weathered timber cross and a tin message box."""
    g = g_at(cv, x + 2, y + 2)
    for k, r in enumerate((3, 2, 2, 1, 1)):
        boxm(cv, x + 2 - r, x + 2 + r, y + 2 - r, y + 2 + r, g - 1 - k, g - 1 - k, 'stone', mode='block')
    if cross:
        boxm(cv, x + 2, x + 2, y + 2, y + 2, g - 12, g - 6, 'beam')
        boxm(cv, x + 2, x + 2, y + 0, y + 4, g - 10, g - 10, 'beam')
    put(cv, x + 3, y + 1, g - 6, 'rust')
