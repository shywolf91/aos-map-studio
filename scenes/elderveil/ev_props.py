"""Elderveil one-offs (art pass, west half + axis halves before the mirror). Mostly recolours of the graybox pieces;
the few added voxels sit where nobody can stand (>= 5 above the ground, or on tops 2+ above the floor).

queen statue (crown, face, robe folds, belt, broken arm), elder head under the platform, moonwell rune ring and
focal light, library (book spines, fallen books, a star-chart floor upstairs, reading desk lamp), hunters' camps
(bedrolls, trophy skulls with antlers, weapon racks, alchemy flasks, notice papers, embers, forge, hall window
lights, cart sacks, gateway lanterns), ruin sites (obelisk inlay, chapel altar, lookout timber, nest cave crystals),
rune circle lights.
"""
from __future__ import annotations

import math

import numpy as np

from aosmap.kit import noise
from aosmap.kit.color import clamp8, mix, shade

WARM, CYAN, GREEN, WHITE = (255, 175, 95), (95, 255, 255), (95, 255, 95), (255, 255, 255)
GOLD = (198, 164, 76)
MARBLE = (206, 200, 188)


def _vox(cv, box, *mats):
    x0, x1, y0, y1 = box
    ids = [cv.materials[m] for m in mats if m in cv.materials]
    sub = cv.mat[x0:x1 + 1, y0:y1 + 1]
    m = np.isin(sub, ids) & cv.solid[x0:x1 + 1, y0:y1 + 1]
    xs, ys, zs = np.nonzero(m)
    return xs + x0, ys + y0, zs


def queen_art(cv, S):
    q = S['queen']
    xs, ys, zs = _vox(cv, (240, 255, 184, 236), 'statue')
    c = np.array([MARBLE] * len(xs), float)
    t0, t1 = q['torso_y']
    torso = (ys >= t0) & (ys <= t1)
    fold = torso & (xs % 3 == 0)
    c[fold] *= 0.9                                                       # robe folds (soft)
    belt = torso & (ys == t0 + 9)
    c[belt] = GOLD
    hips = ys >= q['hips_y'][0]
    c[hips] *= np.where((xs[hips] + zs[hips]) % 4 == 0, 0.9, 1.0)[:, None]
    hx, hy = q['head_c']
    head = ys < t0
    topf = ~cv.solid[xs, ys, np.maximum(zs - 1, 0)]
    crown = head & (ys <= hy - 3) & topf & ((xs + ys) % 2 == 0)
    c[crown] = GOLD
    hair = head & (ys <= hy - 2) & ~crown
    c[hair] *= 0.88
    eyes = head & topf & (ys == hy + 1) & (xs == 253)
    c[eyes] = (70, 72, 82)
    lips = head & topf & (ys == hy + 4) & (xs == 255)
    c[lips] = (176, 150, 140)
    arms = torso & (ys <= t0 + 6) & topf
    c[arms] = np.array(MARBLE) * 0.95
    moss = (noise.hash3(xs, ys, zs, 33) < 0.18) & (zs >= 47)
    c[moss] = (96, 126, 66)
    cv.rgb[xs, ys, zs] = np.clip(c, 0, 212).astype(np.uint8)
    # the broken-off forearm stump: a darker fracture face
    cv.rgb[q['x'][0] + 1, t0 + 6, q['torso_z'][0] - 1] = (150, 146, 138)
    return int(len(xs))


def head_art(cv, S):
    hd = S['under']['head']
    cx, cy = hd['c']
    xs, ys, zs = _vox(cv, (cx - 9, 255, cy - 9, cy + 9), 'statue')
    c = np.array([(196, 190, 178)] * len(xs), float)
    topf = ~cv.solid[xs, ys, np.maximum(zs - 1, 0)]
    beard = (ys > cy + 2) & ((xs + zs) % 3 == 0)
    c[beard] *= 0.86
    brows = topf & (np.abs(ys - (cy - 3.5)) <= 0.6) & (xs >= 250)
    c[brows] = (150, 144, 132)
    eyes = topf & (ys == cy - 2) & (xs == 251)
    c[eyes] = (66, 68, 76)
    moss = topf & (noise.hash3(xs, ys, zs, 35) < 0.3)
    c[moss] = (94, 124, 64)
    cv.rgb[xs, ys, zs] = np.clip(c, 0, 212).astype(np.uint8)
    return int(len(xs))


def moonwell_art(cv, S, glow):
    mw = S['plaza']['moonwell']
    cx, cy = mw['c']
    fx, fy = cx + 0.5, cy + 0.5
    n = 0
    for x in range(int(fx - mw['r']) - 1, 256):
        for y in range(int(fy - mw['r']) - 1, int(fy + mw['r']) + 2):
            d = math.hypot(x + 0.5 - fx, y + 0.5 - fy)
            if mw['r'] - 1.6 < d <= mw['r']:
                g = int(cv.H[x, y])
                z = g - mw['rim_h']
                if cv.solid[x, y, z] and not cv.solid[x, y, z - 1]:
                    a = int(math.degrees(math.atan2(y + 0.5 - fy, x + 0.5 - fx)) % 360)
                    if a % 30 < 7:
                        cv.rgb[x, y, z] = CYAN
                        glow.append((x, y, z, CYAN))
                        n += 1
                    else:
                        cv.rgb[x, y, z] = (170, 176, 182)
    # pillar: spiral rune band and the white focal light on top
    g = int(cv.H[255, cy])
    zt = g - 2 - mw['pillar_h']
    for z in range(zt, g - 2):
        for x in (254, 255):
            for y in (cy - 1, cy, cy + 1):
                if cv.solid[x, y, z]:
                    cv.rgb[x, y, z] = (150, 168, 176) if (z + y) % 3 else (120, 196, 200)
    for x in (254, 255):
        for y in (cy, cy + 1):
            if cv.solid[x, y, zt]:
                cv.rgb[x, y, zt] = WHITE
                glow.append((x, y, zt, WHITE))
                break
        else:
            continue
        break
    return n


def library_art(cv, S, glow):
    lb = S['library']
    x0, x1, y0, y1 = lb['box']
    g, sh = 50, lb['storey_h']
    up = g - sh
    BOOK = [(120, 60, 52), (60, 84, 112), (76, 104, 64), (150, 120, 70), (96, 70, 104), (140, 128, 104)]
    xs, ys, zs = _vox(cv, (lb['wing'][0], 255, y0, y1), 'furniture')
    k = (noise.hash3(xs, ys, zs, 51) * len(BOOK)).astype(int) % len(BOOK)
    cv.rgb[xs, ys, zs] = np.array(BOOK)[k]
    # fallen books on the ground floor (recolour of floor voxels round the fallen shelves)
    fid = cv.materials['building']
    n = 0
    for x in range(x0 + 3, 256):
        for y in range(y0 + 2, y1 - 1):
            if cv.mat[x, y, g] == fid and noise.hash3(x, y, 0, 52) < 0.07:
                cv.rgb[x, y, g] = BOOK[int(noise.hash3(x, y, 1, 52) * len(BOOK)) % len(BOOK)]
                n += 1
    # star-chart floor upstairs: deep blue with gold stars and two faint constellation lines
    for x in range(x0 + 6, 256):
        for y in range(y0 + 6, y1 - 7):
            if cv.solid[x, y, up] and cv.mat[x, y, up] == fid and not cv.solid[x, y, up - 1]:
                h = noise.hash3(x, y, 2, 53)
                c = (44, 54, 88) if h > 0.05 else (206, 180, 96)
                cv.rgb[x, y, up] = c
    # reading desk lamp in the alcove (warm)
    lx, ly = x0 + 9, y1 - 3
    if cv.solid[lx, ly, up - 1]:
        cv.rgb[lx, ly, up - 1] = WARM
        glow.append((lx, ly, up - 1, WARM))
    return n


def camp_art(cv, S, glow):
    g = 49
    # bedrolls in the tents (the furniture voxel inside each tent)
    WOOL = [(150, 110, 80), (110, 120, 96), (132, 92, 70), (96, 106, 126)]
    for i, (x0, x1, y0, y1, o) in enumerate(S['tents']):
        xs, ys, zs = _vox(cv, (x0, x1, y0, y1), 'furniture')
        cv.rgb[xs, ys, zs] = WOOL[i % len(WOOL)]
    # trophy racks: bone skulls hang from the bar, antlers rise above it (>= 5 above the ground: unreachable)
    for (x0, x1, y0, y1) in S['racks']:
        gg = int(cv.H[x0, y0])
        xs, ys, zs = _vox(cv, (x0, x1, y0, y1), 'prop')
        for (x, y, z) in zip(xs, ys, zs):
            if z == gg - 3:
                cv.rgb[x, y, z] = (210, 202, 184)
                for (dz, dd) in ((5, 0), (6, -1), (6, 1)):
                    ax, ay = (x + dd, y) if y0 == y1 else (x, y + dd)
                    if not cv.solid[ax, ay, gg - dz] and (dd == 0 or cv.solid[x, y, gg - 5]):
                        cv.set(ax, ay, gg - dz, (178, 160, 126), 'prop')
                        if dd and not cv.solid[x, y, gg - 6]:
                            cv.set(x, y, gg - 6, (178, 160, 126), 'prop')
    E = S['camp_extras']
    # alchemy table: flasks painted on the top (the top is reachable: no added voxels)
    ax0, ax1, ay0 = E['alchemy']
    FL = [(80, 150, 150), (190, 150, 70), (120, 90, 150), (110, 160, 90)]
    for i, x in enumerate(range(ax0, ax1 + 1)):                      # flasks and phials painted on the top
        for y in (ay0, ay0 + 1):
            if cv.solid[x, y, g - 2] and (i + y) % 2 == 0:
                cv.rgb[x, y, g - 2] = FL[(i + y) % len(FL)]
    # notice board papers
    bx, by = E['notice']
    for x in range(bx, bx + 4):
        for z in range(g - 5, g - 2):
            if cv.solid[x, by, z] and noise.hash3(x, by, z, 61) < 0.5:
                cv.rgb[x, by, z] = (204, 194, 170)
    # forge embers + anvil iron
    lx0, lx1, ly0, ly1 = E['lean_to']
    cv.rgb[lx0 + 2, ly0 + 3, g - 2] = WARM
    glow.append((lx0 + 2, ly0 + 3, g - 2, WARM))
    cv.rgb[lx0 + 6, ly0 + 3, g - 1] = (78, 80, 88)
    cv.rgb[lx0 + 7, ly0 + 3, g - 1] = (90, 92, 100)
    # campfires: charred log glowing, sooty stones
    for (x, y) in S['campfires']:
        z = int(cv.H[x, y]) - 1
        cv.rgb[x, y, z] = WARM
        glow.append((x, y, z, WARM))
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                zz = int(cv.H[x + dx, y + dy]) - 1
                if cv.solid[x + dx, y + dy, zz] and (dx or dy):
                    cv.rgb[x + dx, y + dy, zz] = (92, 88, 84)
    # hall: warm light on the sill below every second ground-floor window
    hl = S['hall']
    mx0, mx1, my0, my1 = hl['main']
    k = 0
    for x in range(mx0, mx1 + 1):
        for y in range(my0, my1 + 1):
            if (x in (mx0, mx1) or y in (my0, my1)) and not cv.solid[x, y, g - 2] and cv.solid[x, y, g - 1]:
                k += 1
                if k % 2:
                    cv.rgb[x, y, g - 1] = WARM
                    glow.append((x, y, g - 1, WARM))
    # gate-tower gateway lanterns (on the wall beside the arch, courtyard side)
    gx0, gx1, gy0, gy1 = S['gate_tower']['box']
    for y in (gy0 + 5, gy0 + 9):
        if cv.solid[gx0, y, 50 - 4]:
            cv.rgb[gx0, y, 50 - 4] = WARM
            glow.append((gx0, y, 50 - 4, WARM))
    # cart sacks, well water
    cx0, cx1, cy0, cy1 = S['cart']
    for x in range(cx0, cx1 + 1):
        for y in range(cy0, cy1 + 1):
            z = int(np.argmax(cv.solid[x, y]))
            if (x + y) % 2:
                cv.rgb[x, y, z] = (176, 156, 112)
    return k


def sites_art(cv, S, glow):
    T = S['sites']
    ob = T['obelisk']
    (ax, ay), (bx, by) = ob['shaft']
    for i in range(0, 20, 3):
        t = i / 19.0
        x, y = int(ax + (bx - ax) * t), int(ay + (by - ay) * t)
        z = int(np.argmax(cv.solid[x, y]))
        cv.rgb[x, y, z] = (198, 164, 76)
    ch = T['chapel']
    axp = int(ch['apse'][0])
    cy = (ch['nave'][2] + ch['nave'][3]) // 2
    for y in (cy - 1, cy, cy + 1):
        z = int(np.argmax(cv.solid[axp, y]))
        cv.rgb[axp, y, z] = (198, 164, 76)
    lk = T['lookout']
    dx0, dx1, dy0, dy1 = lk['deck']
    sid = cv.materials['stair']
    for x in range(dx0 - lk['h'] - 1, dx0 + 1):
        for y in range(dy0, dy1 + 1):
            for z in range(30, 51):
                if cv.mat[x, y, z] == sid:
                    cv.rgb[x, y, z] = (118, 88, 60) if x % 2 else (106, 78, 54)
    # nest cave: twigs and bones on the nest ring, three cyan crystals on the chamber walls
    nid = cv.materials.get('nest')
    xs, ys, zs = np.nonzero(cv.mat[:256] == nid)
    for (x, y, z) in zip(xs, ys, zs):
        cv.rgb[x, y, z] = (110, 86, 60) if (x + y) % 3 else (206, 198, 180)
    cid = cv.materials.get('cave')
    xs, ys, zs = np.nonzero(cv.mat[:256] == cid)
    if len(xs):
        cx, cy = int(xs.min()) + 3, int(np.median(ys))
        k = 0
        for (dx, dy, dz) in ((-1, -5, 3), (0, 5, 2), (-4, 2, 4)):
            x, y = cx + dx, cy + dy
            z = int(zs.min()) - dz
            if cv.solid[x, y, z]:
                cv.rgb[x, y, z] = CYAN
                glow.append((x, y, z, CYAN))
                k += 1
    return True


def rune_circle_art(cv, S, glow):
    rc = S['rune_circle']
    rid = cv.materials['rune']
    xs, ys, zs = _vox(cv, (230, 255, rc['c'][1] - 12, rc['c'][1] + 12), 'rune')
    lit = set()
    for (x, y, z) in zip(xs, ys, zs):
        key = (x // 2, y // 3)
        g = int(cv.H[x, y])
        if key not in lit and z == g - 3 and not cv.solid[x - 1, y, z]:
            cv.rgb[x, y, z] = CYAN
            glow.append((x, y, z, CYAN))
            lit.add(key)
    return len(lit)


def props_art(cv, S, rng, glow):
    if S.get('v11'):
        import ev_v11
        return {'queen': ev_v11.queen_art(cv, S, glow), 'head': ev_v11.head_art(cv, S, glow),
                'moonwell_runes': moonwell_art(cv, S, glow), 'library_books': library_art(cv, S, glow),
                'hall_window_lights': camp_art(cv, S, glow), 'sites': sites_art(cv, S, glow),
                'rune_stones_lit': rune_circle_art(cv, S, glow)}
    return {'queen': queen_art(cv, S), 'head': head_art(cv, S), 'moonwell_runes': moonwell_art(cv, S, glow),
            'library_books': library_art(cv, S, glow), 'hall_window_lights': camp_art(cv, S, glow),
            'sites': sites_art(cv, S, glow), 'rune_stones_lit': rune_circle_art(cv, S, glow)}
