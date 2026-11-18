"""Tradeoff Christmas v2: deadly water kept, giant Christmas tree island in the centre, garland murals on the towers,
sky decor only over the outer water. Reuses the v1 prop helpers (tc_build.py).

python tc2_build.py SRC_tradeoff.vxl SRC_tradeoff.txt OUTDIR [--seed N]

Differences to v1 (owner feedback 2026-11-18): NO props on the outer floor (it is deadly water, water_damage 25 in the
original .txt); the original .txt hooks/extensions are kept (spawn rects on the tower tops, bases at x = 118 / 394, babel,
orange heavens + fog); one centre landmark: a giant tree on a seabed island with a ribbon staircase (partial assist).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..')))
from tc_build import (BAUBLES, CREAM, GLOW_PAL, PINE, SHADE, SNOW_D, SNOW_L, TEAM, WHITE, Cv, bake_glow,  # noqa: E402
                      cloud, gift, lerp, pine, pk, sleigh, snowflake)
from aosmap.art import fbm, value_noise                                           # noqa: E402
from aosmap.pixelfont import text_mask                                            # noqa: E402
from aosmap.validate import floating_components                                   # noqa: E402
from aosmap.vxl import read_vxl, surface_mask, write_vxl                          # noqa: E402

NAME = 'Tradeoff Christmas'
FLOOR = 62
TREE_C = (256, 256)
SPAWN_RECTS = [(108, 246, 128, 266), (384, 246, 404, 266)]       # from the original .txt (BLUE_RECT / GREEN_RECT)
PLATFORM = (206, 240, 305, 271)                                  # stock babel_script platform, z = 1
GARLAND_ROWS = (14, 30, 46)


# ===================================================================== web strands
def strand_info(S):
    """The original 'spider web': thin bars at z 9-12 reaching out from the towers (columns with top z = 9 that lie
    within 2.5 of open water). Returns (2D mask, list of tip columns)."""
    top = np.where(S.any(2), S.argmax(2), 64)
    water_d = ndimage.distance_transform_edt(top != 63)
    st = (top == 9) & (water_d <= 2.5)
    lab, n = ndimage.label(st, structure=np.ones((3, 3)))
    tower_d = ndimage.distance_transform_edt(top != 2)
    tips = []
    for i in range(1, n + 1):
        ix, iy = np.nonzero(lab == i)
        if len(ix) < 6:
            continue
        j = int(np.argmax(tower_d[ix, iy]))
        tips.append((int(ix[j]), int(iy[j])))
    return st, tips


# ===================================================================== recolour
def recolour(vm, seed=7):
    S, C = vm.solid, vm.color
    xs, ys, zs = np.nonzero(S)
    n = len(xs)
    cc = C[xs, ys, zs].astype(np.int64)
    r = ((cc >> 16) & 255).astype(np.int16); g = ((cc >> 8) & 255).astype(np.int16); b = (cc & 255).astype(np.int16)
    lum = 0.3 * r + 0.59 * g + 0.11 * b
    top2d = np.where(S.any(2), S.argmax(2), 64)
    slab = top2d < 60
    lab, _ = ndimage.label(ndimage.binary_dilation(slab, iterations=2))
    blue_lab = lab[256, 185]
    T2 = np.zeros((512, 512), np.int8)
    T2[lab == blue_lab] = 1
    T2[(lab != blue_lab) & (lab > 0)] = 2
    tower = T2[xs, ys]
    team = np.where(tower > 0, tower, np.where(b > r, 1, 2)).astype(np.int8)
    up_open = np.zeros_like(S)
    up_open[:, :, 1:] = ~S[:, :, :-1]
    up_open[:, :, 0] = True
    topf = up_open[xs, ys, zs]
    # wall direction for the murals: u runs along the wall
    pad = np.pad(S, ((1, 1), (1, 1), (0, 0)))
    ax = (~pad[0:-2, 1:-1, :][xs, ys, zs]) | (~pad[2:, 1:-1, :][xs, ys, zs])
    ay = (~pad[1:-1, 0:-2, :][xs, ys, zs]) | (~pad[1:-1, 2:, :][xs, ys, zs])
    u = np.where(ay & ~ax, xs, np.where(ax & ~ay, ys, (xs + ys) * 0.7071)).astype(np.float32)

    water = (zs == 63) | ((r > 190) & (g > 70) & (g < 170) & (b < 80))
    strand2d, _ = strand_info(S)
    fin = strand2d[xs, ys] & (zs >= 9) & (zs <= 12)
    trim = ~water & (((b > 170) & (r < 110) & (g < 110)) | ((r > 170) & (g < 110) & (b < 110)))
    dark = ~water & ~trim & (lum < 28)
    dteam = ~water & ~trim & ~dark & ((r + g + b) < 330)
    light = ~water & ~trim & ~dark & ~dteam

    nA = value_noise(xs, ys, zs, 2.6, seed)
    nB = value_noise(xs, ys, zs, 9.0, seed + 1)
    nC = value_noise(xs, ys, zs, 1.4, seed + 2)
    out = np.zeros((n, 3), np.float32)

    # --- deadly water: cold teal with ripple lines (must still read as water)
    big = fbm(xs, ys, None, 60.0, 3, seed + 3)
    t = np.clip(0.2 + 0.5 * big + 0.35 * nB, 0, 1)
    wcol = lerp((16, 98, 156), (44, 150, 198), t)
    ripple = np.sin((xs * 0.42 + ys * 0.17) + value_noise(xs, ys, None, 18.0, seed + 6) * 9.0)
    wcol = np.where((ripple > 0.93)[:, None], np.array([116, 200, 226], np.float32), wcol)
    out = np.where(water[:, None], wcol, out)

    for tm in (1, 2):
        P = TEAM[tm]
        m_t = team == tm
        # outer wall = trim: team colour, snow ledge, garland swags with baubles and bows
        side = trim & ~topf & m_t
        base = lerp(P['mid'], P['lite'], np.clip(0.25 + 0.6 * nB + (zs / 63.0) * 0.0, 0, 1)) + (nA[:, None] - 0.5) * 10
        ledge = ((zs % 8) >= 3) & ((zs % 8) <= 4)
        wall = np.where(ledge[:, None], lerp(SNOW_D, SNOW_L, 0.35 + 0.5 * nA), base)
        for zr in GARLAND_ROWS:
            pos = np.mod(u, 24.0)
            zc = zr + 6.0 * (1 - ((pos - 12.0) / 12.0) ** 2)
            gm = np.abs(zs - zc) <= 1.0
            gcol = lerp(PINE[0], (70, 150, 92), np.clip(nC + 0.2, 0, 1))
            wall = np.where(gm[:, None], gcol, wall)
            bulb = (np.mod(np.floor(u), 4) == 2) & (np.round(zs - zc) == 2)
            bi = np.mod(np.floor(u / 4).astype(int) + zr, len(BAUBLES))
            wall = np.where(bulb[:, None], np.array(BAUBLES, np.float32)[bi], wall)
            bow = ((pos >= 23) | (pos <= 1.0)) & (np.abs(zs - zr) <= 2)
            wall = np.where(bow[:, None], np.array([214, 40, 52], np.float32), wall)
            wall = np.where((bow & (np.abs(zs - zr) == 0) & (np.abs(np.minimum(pos, 24 - pos)) < 0.6))[:, None],
                            np.array([240, 206, 90], np.float32), wall)
        out = np.where(side[:, None], wall, out)
        ring = (((xs + ys) // 2) & 1).astype(bool)
        rc = np.where(ring[:, None], np.array(P['mid'], np.float32), np.array(WHITE, np.float32))
        out = np.where((trim & topf & m_t)[:, None], rc, out)
        # roofs: team-tinted snow with topographic contour lines (inspired by trademas)
        roof = (light | dteam) & topf & (zs <= 3) & m_t
        cont = fbm(xs, ys, None, 40.0, 3, seed + 8) * 13.0
        line = (cont - np.floor(cont)) < 0.12
        roofc = lerp(P['roof'], SNOW_L, 0.1 + 0.45 * nB) * (0.92 + 0.1 * nA)[:, None]
        roofc = np.where(line[:, None], roofc * 0.82, roofc)
        roofc = np.where((nC > 0.94)[:, None], np.array([214, 218, 218], np.float32), roofc)
        out = np.where(roof[:, None], roofc, out)
        flo = light & topf & (zs > 3) & m_t
        chk = ((((xs // 4) + (ys // 4)) & 1) == 0)
        floc = np.where(chk[:, None], np.array(P['floor'], np.float32), np.array(CREAM, np.float32)) + (nA[:, None] - 0.5) * 16
        out = np.where(flo[:, None], floc, out)
        wl = light & ~topf & m_t
        wlc = lerp(P['stone'][0], P['stone'][1], np.clip(0.2 + 0.6 * nB + 0.3 * nA, 0, 1)) + (nC[:, None] - 0.5) * 12
        out = np.where(wl[:, None], wlc, out)
        dt = dteam & ~roof & m_t
        dtc = lerp(PINE[0], PINE[1], np.clip(0.2 + 0.7 * nB, 0, 1)) + (nC[:, None] - 0.5) * 12
        out = np.where(dt[:, None], dtc, out)
        out = np.where((dark & m_t)[:, None], np.array(P['navy'], np.float32) * (0.9 + 0.2 * nA)[:, None], out)
    # fins -> candy canes (ornaments are added at their tips)
    candy = (((xs + ys + zs) // 2) & 1).astype(bool)
    out = np.where(fin[:, None], np.where(candy[:, None], np.array([214, 40, 52], np.float32), np.array([232, 232, 232], np.float32)), out)
    vm.color[xs, ys, zs] = ((SHADE << 24) | (np.clip(out[:, 0], 0, 255).astype(np.int64) << 16)
                           | (np.clip(out[:, 1], 0, 255).astype(np.int64) << 8)
                           | np.clip(out[:, 2], 0, 255).astype(np.int64)).astype(np.uint32)
    vm.colored[:] = S
    return T2, slab


# ===================================================================== centre landmark
def centre_tree(cv, rng, log, h=38, stair_h=22):
    cx, cy = TREE_C
    base = 59                                     # lowest air voxel above the island top (z = 60)
    R_isl = 19
    # seabed island: snow top z=60, step ring z=61 (dry), outer step z=62 (still wet)
    def snow(a, b, c):
        return lerp(SNOW_D, SNOW_L, 0.45 + 0.5 * rng.random())
    for x in range(cx - 25, cx + 26):
        for y in range(cy - 25, cy + 26):
            d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            if d <= R_isl:
                top = 60
            elif d <= R_isl + 2.5:
                top = 61
            elif d <= R_isl + 5:
                top = 62
            else:
                continue
            for z in range(top, 63):
                cv.put(x, y, z, snow(x, y, z) if z == top else (150, 160, 178))
    pine(cv, cx, cy, h, rng, base=base, details=['tinsel', 'ornaments', 'berries'], star=False)
    for t in range(0, 9):                          # wide trunk
        for dx in range(-1, 3):
            for dy in range(-1, 3):
                cv.put(cx + dx, cy + dy, base - t, (112 + int(rng.integers(-8, 8)), 78, 50))
    Rm = 0.33 * h

    def prof(t):                                   # outer foliage radius at height t (matches pine())
        return Rm * (1 - 0.88 * min(t / h, 0.999)) + 1.0

    # ribbon staircase around the tree: 3-wide, 2-thick treads rising 1 per ~4 voxels of arc
    th, stairs = 0.0, []
    for hh in range(0, stair_h + 1):
        rr = prof(hh + 2) + 3.0
        th += 4.0 / rr
        stairs.append((hh, rr, th))
    for hh, rr, th in stairs:
        for k in range(-5, 6):                     # tread length 4 along the arc
            a = th + k * 0.5 / rr
            for w in (-1.5, -0.5, 0.5, 1.5):
                px, py = int(round(cx + 0.5 + (rr + w) * np.cos(a))), int(round(cy + 0.5 + (rr + w) * np.sin(a)))
                z = base + 1 - hh
                for zz in range(z + 1, z - 4, -1):   # clear headroom
                    if zz < z:
                        cv.clear(px, py, zz)
                col = (214, 40, 52) if (hh // 2) % 2 == 0 else (236, 236, 236)
                if abs(w) > 1.2:
                    col = (240, 206, 90)
                cv.put(px, py, z, col)
                cv.put(px, py, z + 1, col)
    hh, rr, th = stairs[-1]                         # landing
    lx, ly = cx + 0.5 + rr * np.cos(th), cy + 0.5 + rr * np.sin(th)
    for dx in range(-3, 4):
        for dy in range(-3, 4):
            if dx * dx + dy * dy <= 10:
                for zz in range(base + 1 - hh - 4, base + 1 - hh):
                    cv.clear(int(lx) + dx, int(ly) + dy, zz)
                cv.put(int(lx) + dx, int(ly) + dy, base + 1 - hh, (240, 206, 90))
                cv.put(int(lx) + dx, int(ly) + dy, base + 2 - hh, (240, 206, 90))
    # surface-snapped lights and baubles
    def snap(ang, z, rmax):
        for r_ in np.arange(rmax, 0.4, -0.5):
            px_, py_ = int(round(cx + 0.5 + r_ * np.cos(ang))), int(round(cy + 0.5 + r_ * np.sin(ang)))
            if cv.S[px_, py_, z]:
                return px_, py_
        return None
    for k in range(46):
        t = 5 + (h - 8) * k / 46.0
        z = int(base - t)
        hit = snap(k * 0.62, z, Rm + 2)
        if hit:
            cv.lit(hit[0], hit[1], z, [2, 3, 4, 5][k % 4])
    for k in range(18):
        t = rng.uniform(6, h - 8)
        z = int(base - t)
        hit = snap(rng.uniform(0, 6.28), z, Rm + 2)
        if hit:
            cv.ball(hit[0], hit[1], z, 1.5, 1.5, 1.5, BAUBLES[k % len(BAUBLES)])
    top = base - h
    sc = (244, 208, 96)
    for dz in range(-4, 1):
        for dx in range(-2, 3):
            if abs(dx) + abs(dz) * 0.7 <= 2.6:
                cv.put(cx + dx, cy, top + dz - 2, sc); cv.put(cx, cy + dx, top + dz - 2, sc)
    cv.lit(cx, cy, top - 3, 2)
    for dx in (-1, 1):
        cv.lit(cx + dx, cy, top - 3, 2); cv.lit(cx, cy + dx, top - 3, 2)
    for k in range(7):                              # gift pile on the island
        a = k * 0.9 + 0.3
        gift(cv, int(cx + 16 * np.cos(a)) - 2, int(cy + 16 * np.sin(a)) - 2, int(rng.integers(4, 7)), int(rng.integers(4, 7)),
             int(rng.integers(3, 6)), rng, base=59)
    log['tree'] = dict(centre=TREE_C, height=h, star_z=int(top - 3), island_radius=R_isl, stair_top_stand_z=int(base + 1 - stair_h) - 1,
                       stair_steps=len(stairs))


def fin_baubles(cv, tips, log):
    for k, (x, y) in enumerate(tips):
        cv.ball(x, y, 16, 3.2, 3.2, 3.2, BAUBLES[k % len(BAUBLES)])
        for zz in range(9, 15):
            cv.put(x, y, zz, (240, 206, 90), over=False)
    log['strand_tip_baubles'] = tips


# ===================================================================== build
def build(src, seed):
    t0 = time.time()
    vm, rep = read_vxl(open(src, 'rb').read())
    T2, slab = recolour(vm)
    cv = Cv(vm)
    rng = np.random.default_rng(seed)
    log = {}
    _, tips = strand_info(vm.solid)
    centre_tree(cv, rng, log)
    fin_baubles(cv, tips, log)

    # roof-edge fairy lights (not in the spawn rects, not under/over the platform footprint)
    sf = surface_mask(vm.solid)
    edge = ndimage.binary_erosion(slab, iterations=1)
    pal = [2, 3, 4, 5, 3]
    nb = 0
    for x, y in np.argwhere(sf[:, :, 2] & slab):
        if edge[x, y] or (x * 7 + y * 3) % 6 or vm.solid[x, y, 1]:
            continue
        if any(r[0] - 3 <= x <= r[2] + 3 and r[1] - 3 <= y <= r[3] + 3 for r in SPAWN_RECTS):
            continue
        if PLATFORM[0] - 10 <= x <= PLATFORM[2] + 10 and PLATFORM[1] - 10 <= y <= PLATFORM[3] + 10:
            continue
        cv.lit(x, y, 1, pal[(x // 6 + y // 6) % 5]); nb += 1
    log['roof_bulbs'] = nb

    # sky decor over the outer water only
    floaters = []

    def mark(name, bbox):
        floaters.append({'name': name, 'bbox': [int(v) for v in bbox]})
    sx, sy, sz = 120, 62, 24
    sleigh(cv, sx, sy, rng, base=sz, scale=1, deer=4, flying=True)
    mark('flying sleigh + 4 reindeer', (sx - 2, sy - 12, 8, sx + 70, sy + 14, sz + 2))
    for (cx, cy, cz, R) in [(400, 70, 26, 13), (60, 120, 30, 11), (84, 430, 28, 14), (430, 400, 24, 12), (250, 450, 32, 12),
                            (270, 50, 34, 10), (462, 230, 30, 11), (44, 262, 26, 10)]:
        cloud(cv, cx, cy, cz, R, rng, deck_trees=3 if R > 10 else 2, baubles=2)
        mark('snow-cloud island', (cx - R, cy - R, cz - R, cx + R, cy + R, cz + R))
    for (cx, cy, cz, R, ax) in [(30, 60, 20, 8, 1), (470, 150, 22, 9, 1), (30, 330, 24, 8, 1), (480, 330, 18, 8, 1),
                                (160, 470, 22, 9, 0), (360, 40, 14, 8, 0), (140, 28, 14, 7, 0), (380, 465, 20, 8, 0),
                                (20, 190, 14, 7, 1), (490, 80, 16, 7, 1)]:
        snowflake(cv, cx, cy, cz, R, ax, (208, 224, 240))
        mark('snowflake', (cx - R - 2, cy - R - 2, cz - R, cx + R + 2, cy + R + 2, cz + R))
    log['floaters'] = floaters

    # corner tag (map name only) painted on the water floor, bottom-right
    tm = text_mask(['Tradeoff', 'Christmas'], spacing=1, line_gap=3)
    ox, oy = 438, 476
    for i, j in np.argwhere(ndimage.binary_dilation(tm, iterations=1) & ~tm):
        vm.color[ox + i, oy + j, 63] = pk((236, 236, 236))
    for i, j in np.argwhere(tm):
        vm.color[ox + i, oy + j, 63] = pk((190, 30, 46))
    log['tag'] = dict(x=ox, y=oy, w=int(tm.shape[0]), h=int(tm.shape[1]))

    # drop tiny accidental floating bits (not the listed sky pieces)
    removed = 0
    for c in floating_components(vm.solid):
        (x0, x1), (y0, y1), (z0, z1) = c['bbox']
        in_sky = any(f['bbox'][0] - 6 <= x0 and x1 <= f['bbox'][3] + 6 and f['bbox'][1] - 6 <= y0 and y1 <= f['bbox'][4] + 6
                     and f['bbox'][2] - 16 <= z0 and z1 <= f['bbox'][5] + 16 for f in floaters)
        if not in_sky and c['voxels'] <= 40:
            sub = vm.solid[x0:x1 + 1, y0:y1 + 1, z0:z1 + 1]
            lbl, nl = ndimage.label(sub)
            for i in range(1, nl + 1):
                if (lbl == i).sum() == c['voxels']:
                    sub[lbl == i] = False
                    vm.colored[x0:x1 + 1, y0:y1 + 1, z0:z1 + 1][lbl == i] = False
                    removed += c['voxels']; break
    cv.glow = {k: v for k, v in cv.glow.items() if vm.solid[k]}
    log['removed_floating_voxels'] = removed
    vm.colored[:] = vm.solid
    stored, nlit = bake_glow(vm, cv.glow)
    log.update(glow_sources=len(cv.glow), glow_lit_voxels=nlit, build_s=round(time.time() - t0, 1))
    return vm, stored, log


def make_txt(orig_txt, stored):
    """Original hooks/extensions kept verbatim (owner's server), renamed, glow keys added."""
    src = open(orig_txt, encoding='utf-8').read().replace('\r\n', '\n')
    head, tail = src.split('extensions', 1)
    rest = tail.split('}', 1)[1]                        # everything after the original extensions dict
    lines = ["# Tradeoff Christmas v2 - based on Tradeoff by ei8htx / aloha.pk; spawn rects, bases, water_damage, babel flag, fog",
             "# and heavens_color are the original map's own settings (not AI-authored).",
             f"name = {NAME!r}", "version = '2.0'", "author = 'shywolf91 + AI'",
             "description = 'Tradeoff Christmas: candy-garland towers, a giant tree island in the middle, deadly water kept. "
             "Original Tradeoff by ei8htx.'",
             "extensions = {", "\t'water_damage' : 25,", "\t'babel' : True,", "\t'heavens_color' : (250, 130, 40, 255),",
             "\t'glow_enabled' : True,", "\t'glow_stored_colors' : {"]
    lines += [f"\t\t{k!r}: {tuple(int(v) for v in stored[k])!r}," for k in sorted(stored)]
    lines += ["\t},", "}"]
    fog_and_code = rest[rest.index('fog'):] if 'fog' in rest else rest
    return '\n'.join(lines) + '\n\n' + fog_and_code


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('txt'); ap.add_argument('out'); ap.add_argument('--seed', type=int, default=None)
    a = ap.parse_args()
    seed = a.seed if a.seed is not None else int.from_bytes(os.urandom(4), 'little')
    os.makedirs(a.out, exist_ok=True)
    vm, stored, log = build(a.src, seed)
    data = write_vxl(vm)
    open(os.path.join(a.out, 'tradeoff_christmas.vxl'), 'wb').write(data)
    open(os.path.join(a.out, 'tradeoff_christmas.txt'), 'w', newline='\n').write(make_txt(a.txt, stored))
    info = dict(seed=seed, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), **log)
    json.dump(info, open(os.path.join(a.out, 'build.json'), 'w'), indent=1, default=int)
    print(json.dumps({k: v for k, v in info.items() if k != 'floaters'}, indent=1, default=int))


if __name__ == '__main__':
    main()
