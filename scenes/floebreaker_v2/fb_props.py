"""Floebreaker props: research camps, huts, tents, weather towers, crevasses, seracs, arches, whale skeleton,
spawn-cover fins and base camps. Every enclosed structure has openings (door/windows) and is furnished."""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from fb_core import MAT, XX, YY, fbm


def pad(W, H, x0, x1, y0, y1, zf=None, apron=2):
    """Level a rectangular pad to floor surface zf (default: lowest ground in the footprint). Returns zf."""
    if zf is None:
        zf = int(H[x0:x1 + 1, y0:y1 + 1].max())
        zf = min(zf, 60)
    for x in range(x0 - apron, x1 + apron + 1):
        for y in range(y0 - apron, y1 + apron + 1):
            inside = x0 <= x <= x1 and y0 <= y <= y1
            h0 = int(H[x, y])
            if h0 >= 63:
                continue
            if inside or True:
                tgt = zf if inside else (zf if abs(h0 - zf) <= 1 else h0)
                if tgt > h0:                           # ground higher than pad -> dig down
                    W.m[x, y, h0:tgt] = 0
                elif tgt < h0:                         # ground lower -> fill up
                    W.m[x, y, tgt:h0] = MAT['pack']
                if tgt != h0:
                    W.m[x, y, tgt] = MAT['snow']
                    H[x, y] = tgt
    return zf


def hut(W, H, x0, y0, w, d, door='S', mat='dwood', roof='plank', zf=None):
    """Single-room hut: footprint w x d, interior 4 high, door 2x3, windows, bunk, table, stove, lamp."""
    x1, y1 = x0 + w - 1, y0 + d - 1
    zf = pad(W, H, x0 - 1, x1 + 1, y0 - 1, y1 + 1, zf)
    zc = zf - 5
    W.room(x0, x1, y0, y1, zf, zc, mat)
    # pitched roof: two tiers
    W.box(x0 - 1, x1 + 1, y0 - 1, y1 + 1, zc, zc, roof)
    W.box(x0 + 1, x1 - 1, y0 + 1, y1 - 1, zc - 1, zc - 1, roof)
    if w > 6 and d > 6:
        W.box(x0 + 2, x1 - 2, y0 + 2, y1 - 2, zc - 2, zc - 2, roof)
    # door
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    if door == 'S':
        W.carve(cx, cx + 1, y1, y1, zf - 3, zf - 1)
    elif door == 'N':
        W.carve(cx, cx + 1, y0, y0, zf - 3, zf - 1)
    elif door == 'E':
        W.carve(x1, x1, cy, cy + 1, zf - 3, zf - 1)
    else:
        W.carve(x0, x0, cy, cy + 1, zf - 3, zf - 1)
    # door ramp: bring the ground in front of the door up to the sill in 1-voxel steps
    dx, dy = {'S': (0, 1), 'N': (0, -1), 'E': (1, 0), 'W': (-1, 0)}[door]
    bx0, by0 = {'S': (cx, y1), 'N': (cx, y0), 'E': (x1, cy), 'W': (x0, cy)}[door]
    for k in range(1, 4):
        level = zf + (k - 1)
        for wdt in (0, 1):
            xx = bx0 + dx * k + (wdt if dx == 0 else 0); yy = by0 + dy * k + (wdt if dy == 0 else 0)
            h0 = int(H[xx, yy])
            if h0 > level and h0 < 62:
                W.m[xx, yy, level:h0] = MAT['pack']
                W.m[xx, yy, level] = MAT['snow']
                H[xx, yy] = level
    # windows (2 wide x 2 high) on the walls that are not the door wall
    if door not in ('N',):
        W.carve(x0 + 1, x0 + 2, y0, y0, zf - 3, zf - 2)
    if door not in ('S',):
        W.carve(x1 - 2, x1 - 1, y1, y1, zf - 3, zf - 2)
    W.carve(x0, x0, y0 + 1, y0 + 2, zf - 3, zf - 2) if door != 'W' else None
    W.carve(x1, x1, y1 - 2, y1 - 1, zf - 3, zf - 2) if door != 'E' else None
    # furniture (never on the door row): bunk in the NW corner, table + stove away from the door
    W.box(x0 + 1, x0 + 2, y0 + 1, y0 + 2, zf - 1, zf - 1, 'plank')
    if door in ('E', 'W'):
        W.box(x0 + 3, x0 + 4, y1 - 2, y1 - 1, zf - 2, zf - 2, 'dwood'); W.box(x0 + 3, x0 + 3, y1 - 2, y1 - 2, zf - 1, zf - 1, 'dwood')
        W.box(x0 + 5, x0 + 5, y0 + 1, y0 + 1, zf - 2, zf - 1, 'dsteel')
    else:
        W.box(x1 - 2, x1 - 1, cy - 1, cy, zf - 2, zf - 2, 'dwood'); W.box(x1 - 2, x1 - 2, cy - 1, cy - 1, zf - 1, zf - 1, 'dwood')
        W.box(x1 - 1, x1 - 1, y0 + 1 if door == 'S' else y1 - 1, y0 + 1 if door == 'S' else y1 - 1, zf - 2, zf - 1, 'dsteel')
    W.pt(cx, cy, zc + 1, 'lamp')
    W.interiors.append(('hut', cx, cy + 1, zf))
    return zf


def tent(W, H, x0, y0, length=8, half=3, door='S', mat='canvas_o', zf=None):
    """A-frame tent (ridge along y), open door end, bedroll and lamp inside."""
    x1, y1 = x0 + 2 * half, y0 + length - 1
    zf = pad(W, H, x0, x1, y0, y1, zf)
    cx = x0 + half
    for y in range(y0, y1 + 1):
        for h in range(0, half + 2):
            hw = half - h
            if hw < 0:
                break
            z = zf - 1 - h
            for x in (cx - hw, cx + hw):
                W.pt(x, y, z, mat)
            if hw == 0:
                W.pt(cx, y, z, mat)
    # far wall
    for h in range(0, half + 1):
        hw = half - h
        z = zf - 1 - h
        for x in range(cx - hw, cx + hw + 1):
            W.pt(x, y1 if door == 'S' else y0, z, mat)
    W.pt(cx, y0 + length // 2, zf - 1 - half - 1, 'lamp')            # lantern on the ridge (keeps the inside walkable)
    # ramp at the open end: ground outside steps 1 voxel at a time from the tent floor
    oy = -1 if door == 'S' else 1
    yo = y0 if door == 'S' else y1
    for k in range(1, 4):
        for x in range(cx - half, cx + half + 1):
            yy = yo + oy * k
            level = zf - (k - 1) if int(H[x, yy]) < zf else zf + (k - 1)
            h0 = int(H[x, yy])
            if abs(h0 - zf) <= k - 1:
                continue
            if h0 < level:
                W.m[x, yy, h0:level] = 0
            else:
                W.m[x, yy, level:h0] = MAT['pack']
            W.m[x, yy, level] = MAT['snow']
            H[x, yy] = level
    W.box(cx - 1, cx, y0 + 2, y0 + 3, zf, zf, 'canvas_b')              # bedroll mat flush with the floor
    return zf


def drum_group(W, H, x, y, n=3, seed=0):
    rng = np.random.default_rng(seed)
    for i in range(n):
        dx, dy = int(rng.integers(0, 4)), int(rng.integers(0, 4))
        g = int(H[x + dx, y + dy])
        mid = ['drum_r', 'drum_b', 'orange'][i % 3]
        W.box(x + dx, x + dx + 1, y + dy, y + dy + 1, g - 3, g - 1, mid)


def crates(W, H, x, y, seed=0):
    rng = np.random.default_rng(seed)
    g = int(H[x, y])
    W.box(x, x + 2, y, y + 2, g - 2, g - 1, 'plank')
    W.box(x + 1, x + 2, y + 1, y + 2, g - 3, g - 3, 'dwood')
    W.box(x + 3, x + 4, y, y + 1, g - 1, g - 1, 'plank')


def lamp_post(W, H, x, y, h=7, mat='lamp'):
    g = int(H[x, y])
    W.box(x, x, y, y, g - h, g - 1, 'dwood')
    W.pt(x, y, g - h - 1, mat)


def sled(W, H, x, y):
    g = int(H[x, y])
    W.box(x, x, y, y + 5, g - 1, g - 1, 'dwood'); W.box(x + 2, x + 2, y, y + 5, g - 1, g - 1, 'dwood')
    W.box(x, x + 2, y + 1, y + 1, g - 2, g - 2, 'plank'); W.box(x, x + 2, y + 4, y + 4, g - 2, g - 2, 'plank')


def weather_tower(W, H, x0, y0):
    """Two-storey tower 9x9: floors at zf / zf-6, roof deck z zf-12 with rail and antenna. Door S, stairs inside."""
    x1, y1 = x0 + 8, y0 + 8
    zf = pad(W, H, x0 - 1, x1 + 1, y0 - 1, y1 + 1)
    for i, z in enumerate((zf, zf - 6)):
        W.room(x0, x1, y0, y1, z, z - 6, 'dwood' if i else 'plank')
    W.carve(x0 + 3, x0 + 4, y1, y1, zf - 3, zf - 1)                   # door
    for z in (zf, zf - 6):
        W.carve(x0 + 1, x0 + 2, y0, y0, z - 3, z - 2); W.carve(x1 - 2, x1 - 1, y0, y0, z - 3, z - 2)
        W.carve(x0, x0, y0 + 3, y0 + 4, z - 3, z - 2); W.carve(x1, x1, y0 + 3, y0 + 4, z - 3, z - 2)
    W.stairs(x0 + 1, x0 + 3, y0 + 1, zf, zf - 6, '+y', 'plank')       # ground floor -> upper
    W.stairs(x0 + 5, x0 + 7, y0 + 7, zf - 6, zf - 12, '-y', 'plank')  # upper -> roof deck
    for x in range(x0, x1 + 1):                                       # roof rail
        for y in (y0, y1):
            if (x + y) % 2: W.pt(x, y, zf - 13, 'steel')
    for y in range(y0, y1 + 1):
        for x in (x0, x1):
            if (x + y) % 2: W.pt(x, y, zf - 13, 'steel')
    W.box(x0 + 4, x0 + 4, y0 + 4, y0 + 4, zf - 22, zf - 13, 'steel')   # antenna
    W.box(x0 + 2, x0 + 6, y0 + 4, y0 + 4, zf - 19, zf - 19, 'steel')
    W.box(x0 + 3, x0 + 5, y0 + 3, y0 + 5, zf - 24, zf - 23, 'orange')   # anemometer head
    W.pt(x0 + 4, y0 + 4, zf - 25, 'lamp')
    W.pt(x0 + 4, y0 + 2, zf - 5, 'lamp'); W.pt(x0 + 4, y0 + 6, zf - 11, 'lamp')
    W.interiors.append(('tower_ground', x0 + 6, y0 + 3, zf)); W.interiors.append(('tower_upper', x0 + 6, y0 + 3, zf - 6))
    return zf


def crevasse(W, H, pts, hw=5, depth=4):
    """V-notch crevasse along a polyline; slope < 1 so it can be walked out of. Walls get blue ice."""
    path = []
    for (ax, ay), (bx, by) in zip(pts[:-1], pts[1:]):
        n = int(np.hypot(bx - ax, by - ay))
        for t in np.linspace(0, 1, max(n, 1), endpoint=False):
            path.append((ax + (bx - ax) * t, ay + (by - ay) * t))
    path = np.array(path)
    x0, x1 = int(path[:, 0].min() - hw - 2), int(path[:, 0].max() + hw + 2)
    y0, y1 = int(path[:, 1].min() - hw - 2), int(path[:, 1].max() + hw + 2)
    xs, ys = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1), indexing='ij')
    dmin = np.full(xs.shape, 1e9)
    for px, py in path[::2]:
        dmin = np.minimum(dmin, np.hypot(xs - px, ys - py))
    for i in range(xs.shape[0]):
        for j in range(xs.shape[1]):
            x, y = xs[i, j], ys[i, j]
            if not (0 <= x < 512 and 0 <= y < 512):
                continue
            dd = dmin[i, j]
            g = int(H[x, y])
            if g >= 62:
                continue
            if dd < hw + 1.5:
                dep = int(round(depth * (1 - min(dd, hw) / hw)))
                if dd < hw and dep > 0:
                    W.m[x, y, g:g + dep] = 0
                    H[x, y] = g + dep
                    W.m[x, y, g + dep:g + dep + 3] = MAT['blueice']
                else:
                    W.m[x, y, g:g + 2] = MAT['blueice']
    # no pits: a column lower than all four neighbours by >= 2 is raised to one below the lowest neighbour
    for _ in range(4):
        for x in range(max(x0, 1), min(x1, 510) + 1):
            for y in range(max(y0, 1), min(y1, 510) + 1):
                g = int(H[x, y])
                if g >= 62:
                    continue
                nb = min(int(H[x - 1, y]), int(H[x + 1, y]), int(H[x, y - 1]), int(H[x, y + 1]))
                if g - nb >= 2:
                    W.m[x, y, nb + 1:g] = MAT['blueice']
                    H[x, y] = nb + 1


def serac_cluster(W, H, cx, cy, n=4, seed=0, hmax=11):
    """Cluster of tapering ice spires (cones with a shoulder), tallest in the middle of the cluster."""
    rng = np.random.default_rng(seed)
    for i in range(n):
        ang = rng.uniform(0, 2 * np.pi); rr = rng.uniform(0, 5)
        px, py = int(cx + rr * np.cos(ang)), int(cy + rr * np.sin(ang))
        w = int(rng.integers(2, 5)); h = int(rng.integers(5, hmax))
        for x in range(px - w, px + w + 1):
            for y in range(py - w, py + w + 1):
                dd = np.hypot(x - px, y - py) / (w + 0.5)
                if dd > 1:
                    continue
                gx = int(H[x, y])
                if gx >= 62:
                    continue
                top = gx - int(round(h * (1 - dd) ** 0.8 + 1))
                W.m[x, y, top:gx] = MAT['blueice']
                W.m[x, y, top] = MAT['snow'] if dd < 0.35 else MAT['blueice']


def ice_arch(W, H, cx, cy, span=9, height=10, thick=4, axis='x', hmat='blueice'):
    """Natural ice arch (walk-through gate): a dome with a half-elliptical opening; legs reach the ground."""
    R = span / 2 + 4.0
    Ht = height + 4
    for t in range(-int(R), int(R) + 1):
        outer = int(round(Ht * np.sqrt(max(0.0, 1 - (t / R) ** 2))))
        op = int(round(height * np.sqrt(max(0.0, 1 - (t / (span / 2)) ** 2)))) if abs(t) <= span / 2 else 0
        if outer <= 0:
            continue
        for u in range(thick):
            x, y = (cx + t, cy + u) if axis == 'x' else (cx + u, cy + t)
            g = int(H[x, y])
            top = g - outer
            W.m[x, y, top:g - op] = MAT[hmat]
            W.m[x, y, top] = MAT['snow'] if u in (1, 2) else MAT[hmat]
            if op:
                W.m[x, y, g - op:g] = 0
    return True


def whale(W, H, cx=255.5, y0=330, y1=432):
    """Whale skeleton on the southern ice plain: spine, ribs (walk through the gaps), skull gate."""
    n = y1 - y0
    ys = np.arange(y0, y1 + 1)
    # spine arc height (z) above ground along y: rises toward the chest
    prof = np.sin(np.pi * np.clip((ys - y0) / n, 0, 1)) ** 0.7
    pad(W, H, int(cx) - 14, int(cx) + 14, y0 - 2, y1 + 8, 59, apron=3)
    for i, y in enumerate(ys):
        zs = 59 - int(round(5 + 9 * prof[i]))
        for x in (int(cx), int(cx) + 1):
            W.m[x, y, zs:zs + 2] = MAT['bone']
        if i % 4 == 0:                                   # vertebra spurs
            W.m[int(cx):int(cx) + 2, y, zs - 2:zs] = MAT['bone']
    # ribs every 8 voxels through the chest section (face-connected paths from spine to ground)
    for j, y in enumerate(range(y0 + 22, y0 + 76, 8)):
        amp = 9 + 6 * np.sin(np.pi * (y - y0) / n)
        zt = 59 - int(round(5 + 9 * prof[y - y0]))
        for side in (-1, 1):
            pts = []
            for th in np.linspace(0, np.pi / 2, 160):
                pts.append((int(round(cx + side * (1 + (amp + 3) * np.sin(th)))), int(round(59 - (59 - zt) * np.cos(th)))))
            full = [pts[0]]
            for (px, pz) in pts[1:]:
                x, z = full[-1]
                while (x, z) != (px, pz):
                    if x != px:
                        x += 1 if px > x else -1
                        full.append((x, z))
                    if z != pz:
                        z += 1 if pz > z else -1
                        full.append((x, z))
            for (x, z) in full:
                for dy in (0, 1):
                    W.m[x, y + dy, z] = MAT['bone']
                    W.m[x, y + dy, min(z + 1, 62)] = MAT['bone']
    # skull gate at the south end: upper jaw dome + two jaw arcs, 11 wide walk-through
    for ydelta in range(0, 12):
        y = y1 - 11 + ydelta
        for xo in range(-13, 14):
            zt = 59 - int(round(14 * np.sqrt(max(0, 1 - (xo / 13.0) ** 2)) * (1 - 0.35 * ydelta / 11)))
            if abs(xo) > 5 or ydelta in (0, 1, 10, 11):
                if abs(xo) > 5:
                    W.m[int(cx + xo), y, zt:59] = MAT['bone']
                else:
                    W.m[int(cx + xo), y, zt:zt + 3] = MAT['bone']
    for y in range(y1 - 9, y1 + 8, 2):                   # teeth along the lower jaw
        for side in (-1, 1):
            W.m[int(cx + side * 9), y, 56:59] = MAT['bone']
    # tail flukes: low curved ridges
    for k in range(6):
        W.m[int(cx - 2 - k):int(cx + 3 + k), y0 - 1 - k, 56:59] = MAT['bone']
    W.marks['whale'] = {'x': (int(cx) - 14, int(cx) + 14), 'y': (y0 - 8, y1 + 8)}


def fins_for_spawn(W, H, side, rows):
    """Staggered ice fins that screen the spawn square from the platform eyes. `side` -1 = blue (west)."""
    for i, (cx, y0, y1, thick, zt, lean) in enumerate(rows):
        x = cx if side < 0 else 512 - cx
        fin_wall(W, H, x, y0, y1, thick, zt, lean, seed=100 + i + (7 if side > 0 else 0))


def fin_wall(W, H, cx, y0, y1, thick, zt, lean, seed=0, mirror=False):
    """Glacier fin: ragged crest, wandering thickness, buttresses on both flanks; every column grounded."""
    rng = np.random.default_rng(seed)
    n = y1 - y0 + 1
    ys = np.arange(y0, y1 + 1)
    t = (ys - y0) / max(n - 1, 1)
    prof = np.clip(np.sin(np.pi * t) ** 0.45, 0, 1)
    jag = ndi.gaussian_filter(rng.standard_normal(n), 1.0) * 4.2
    wob = np.round(ndi.gaussian_filter(rng.standard_normal(n), 4) * 2.2).astype(int)
    if mirror:
        wob = -wob
    butt = {int(b): int(rng.integers(0, 2)) for b in rng.integers(4, n - 4, size=max(n // 12, 3))}
    for i, y in enumerate(ys):
        off = int(round(lean * (t[i] - 0.5))) + int(wob[i])
        for u in range(-1 if i in butt else 0, thick + (1 if i in butt else 0)):
            x = cx + off + u
            g = int(H[x, y])
            top = int(round(g - (g - zt) * prof[i] * (0.7 if (u < 0 or u >= thick) else 1.0) + jag[i] * prof[i]))
            top = min(top, g - 3)
            W.m[x, y, top:g] = MAT['blueice']
            W.m[x, y, top] = MAT['snow'] if (u in (1, 2) and (i % 5)) else MAT['blueice']
