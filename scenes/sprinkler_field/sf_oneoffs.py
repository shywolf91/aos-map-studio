"""Sprinkler Field one-off landmarks (after the mirror; each recorded as a cosmetic asymmetric box).

build(cv, rep, S) -> {'boxes': [[x0, x1, y0, y1], ...], 'named': {...}, 'flatten_removed': ...}

  spigot       W end of the hose: brass tap on a hollow concrete valve box (room + doors), an outside stair to its
               roof, the riser, the hand wheel and the spout bending down onto the hose end
  hose_reel    E end of the hose: reel cart; the drum lies on an N-S axle between two wheels, enterable through a
               door in its east side (stair up to the inner plank floor), a crank on the south wheel
  flowerpot    SW: terracotta pot on its side, mouth east; soil fill inside (floor), spill ramp from the lawn
  glove        SE: gardening glove lying palm down; cuff (open north = the door), palm room, finger and thumb tunnels
  snail_shell  NE: empty snail shell, aperture door, columella with a spiral ramp up to a lookout deck in a broken crown
  footprint    S: a sneaker print pressed 2 deep in the soil (1-deep rim, tread ribs, puddles in the grooves)
  plant_label  NW: blank plastic plant label leaning at 45 degrees (a climbable ramp) with its stake in the soil
(the valve key on the south axis is self-symmetric and lives in sf_axis)

Every structure is real: rooms are recorded in cv.interiors (checked for reachability and a way out).
"""
from __future__ import annotations

import math

from aosmap.kit.structures import straight_stair

from sf_build import GC, box, put, top


def flatten(cv, x0, x1, y0, y1, g, stats):
    """Level a landmark site to floor z g (soil below, air above). Counts removed non-soil voxels (props)."""
    soil = {cv.material(m) for m in ('soil', 'lawn', 'bank', 'trail', 'puddle', 'front', 'spawn', 'anchor', 'hose',
                                     'hose_stripe')}         # the hose ends are cut on purpose (strip_hose)
    for x in range(max(0, x0), min(511, x1) + 1):
        for y in range(max(0, y0), min(511, y1) + 1):
            col = cv.mat[x, y, :g]
            sol = cv.solid[x, y, :g]
            stats['removed'] += int((sol & ~(sum((col == m) for m in soil).astype(bool))).sum())
            cv.carve(x, x, y, y, 0, g - 1)
            if not cv.solid[x, y, g]:
                box(cv, x, x, y, y, g, 63, 'soil')
            cv.rgb[x, y, g] = GC['lawn']
            cv.mat[x, y, g] = cv.material('lawn')


def strip_hose(cv, x0, x1, y0, y1):
    """Remove the main hose inside a box (its end is then joined to the landmark)."""
    ids = (cv.material('hose'), cv.material('hose_stripe'))
    n = 0
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            for z in range(0, 62):
                if cv.mat[x, y, z] in ids:
                    cv.clear(x, y, z)
                    n += 1
    return n


# =============================================================================================== spigot

def spigot(cv, rep, S, stats):
    sx, sy = S['oneoffs']['spigot']
    g = S['z']['lawn']
    O = S['oneoff_dims']['spigot']
    fx0, fx1, fy0, fy1 = O['footing']
    ft = O['footing_top']
    flatten(cv, fx0 - 2, fx1 + 10, fy0 - 2, fy1 + 2, g, stats)
    box(cv, fx0, fx1, fy0, fy1, ft, g, 'concrete')
    cv.carve(fx0 + 1, fx1 - 1, fy0 + 1, fy1 - 1, ft + 2, g - 1)            # valve room (floor = soil z g)
    cv.carve(fx1, fx1, fy0 + 3, fy0 + 5, g - 4, g - 1)                     # east door
    cv.carve(sx - 1, sx + 1, fy0, fy0, g - 4, g - 1)                       # north door (hose side)
    for wx in (fx0 + 4, fx0 + 10, fx0 + 16):                               # south windows
        cv.carve(wx, wx + 1, fy1, fy1, g - 4, g - 3)
    rise = g - ft
    sy0 = fy1 - 8
    straight_stair(cv, fx1 + rise, sy0, sy0 + 2, g, rise, -1, GC['stair'], 'stair')   # east stair to the roof
    tx, ty = sx, (fy0 + fy1) // 2
    tz = O['tap_top']
    for x in range(tx - 3, tx + 4):
        for y in range(ty - 3, ty + 4):
            if math.hypot(x - tx, y - ty) <= 3.2:
                box(cv, x, x, y, y, tz, ft - 1, 'tap')
    box(cv, tx - 6, tx + 6, ty - 1, ty + 1, tz - 2, tz - 1, 'tap')         # hand wheel (cross)
    box(cv, tx - 1, tx + 1, ty - 6, ty + 6, tz - 2, tz - 1, 'tap')
    box(cv, tx - 1, tx + 1, ty - 1, ty + 1, tz - 4, tz - 3, 'brass')
    sz = O['spout_z']
    hy = int(round(sy))
    box(cv, tx - 2, tx + 2, hy - 2, ty - 3, sz, sz + 3, 'tap')              # spout north over the hose end
    hose_top = S['hose']['cz'] - S['hose']['r_out']
    box(cv, tx - 2, tx + 2, hy - 2, hy + 2, sz, hose_top - 1, 'tap')        # elbow down onto the hose
    n = strip_hose(cv, 0, tx - 3, hy - 10, hy + 10)
    cv.interiors.append(['spigot valve room', fx0 + 6, fy0 + 6, g])
    cv.interiors.append(['spigot roof', fx1 - 3, sy0 + 1, ft])
    rep['spigot'] = {'hose_voxels_removed': n, 'roof_z': ft}
    return [0, fx1 + rise + 2, hy - 12, fy1 + 3]


# =============================================================================================== hose reel

def hose_reel(cv, rep, S, stats):
    rx, ry = S['oneoffs']['hose_reel']
    g = S['z']['lawn']
    O = S['oneoff_dims']['hose_reel']
    R, cz = O['drum_r'], O['drum_cz']
    wy = O['wheel_y']
    flatten(cv, rx - R - 8, 511, wy[0] - 4, wy[1] + 8, g, stats)
    n = strip_hose(cv, rx - R - 4, 511, ry - 12, ry + 12)
    dy0, dy1 = O['drum_y']
    for x in range(rx - R - 2, rx + R + 3):
        for z in range(cz - R - 2, cz + R + 3):
            dd = math.hypot(x - rx, z - cz)
            for y in range(dy0, dy1 + 1):
                if R - 1.0 < dd <= R + 0.4:
                    put(cv, x, y, z, 'reel' if (y + z) % 4 else 'hose_stripe')
            for y in (dy0 - 2, dy0 - 1, dy1 + 1, dy1 + 2):                  # flanges
                if dd <= R + 2.4:
                    put(cv, x, y, z, 'cart')
            for y in (wy[0], wy[0] + 1, wy[1] - 1, wy[1]):                  # wheels (rims touch the soil)
                if g - cz - 2.6 < dd <= g - cz + 0.4 or dd <= 2.4:
                    put(cv, x, y, z, 'wheel')
                elif abs(x - rx) <= 1 or abs(z - cz) <= 1:
                    if dd <= g - cz:
                        put(cv, x, y, z, 'wheel')
    box(cv, rx - 1, rx + 1, wy[0], wy[1], cz - 1, cz + 1, 'cart')         # axle
    fz = O['floor_z']
    half = int(math.sqrt(max(0.0, (R - 0.6) ** 2 - (fz - cz) ** 2)))
    box(cv, rx - half, rx + half, dy0, dy1, fz, fz, 'floor')
    box(cv, rx - half, rx + half, dy0, dy1, fz + 1, cz + R, 'cart')        # joists: no pocket under the floor
    # east door through the drum and a stair up from the soil
    dyc = (dy0 + dy1) // 2
    rise = g - fz
    cv.carve(rx + half - 1, rx + R + 2, dyc - 3, dyc + 3, fz - 4, fz - 1)
    box(cv, rx + half - 1, rx + R + 1, dyc - 3, dyc + 3, fz, fz, 'floor')
    straight_stair(cv, rx + R + 1 + rise, dyc - 3, dyc + 3, g, rise, -1, GC['stair'], 'stair')
    # crank on the south wheel
    box(cv, rx - 1, rx + 1, wy[1] + 1, wy[1] + 2, cz - 9, cz, 'cart')
    box(cv, rx - 1, rx + 1, wy[1] + 2, wy[1] + 6, cz - 10, cz - 9, 'cart')
    # the hose end climbs into the drum's west side
    hz = S['hose']['cz']
    box(cv, rx - R - 4, rx - R + 1, ry - 3, ry + 3, hz - 4, g - 1, 'hose')
    cv.interiors.append(['hose reel drum', rx, dyc, fz])
    rep['hose_reel'] = {'hose_voxels_removed': n, 'floor_z': fz}
    return [rx - R - 10, 511, wy[0] - 5, wy[1] + 9]


# =============================================================================================== flowerpot

def flowerpot(cv, rep, S, stats):
    px, py = S['oneoffs']['flowerpot']
    g = S['z']['lawn']
    O = S['oneoff_dims']['flowerpot']
    xb, xm = O['base_x'], O['mouth_x']
    rb, rm = O['r_base'], O['r_mouth']
    fz = O['floor_z']
    flatten(cv, xb - 3, xm + 10, py - rm - 4, py + rm + 4, g, stats)

    def rad(x):
        return rb + (rm - rb) * (x - xb) / (xm - xb)
    for x in range(xb, xm + 3):
        r = rad(min(x, xm))
        czx = g - r - 0.5
        lip = x >= xm - 1
        for y in range(int(py - r - 3), int(py + r + 4)):
            for z in range(int(czx - r - 3), g + 1):
                rho = math.hypot(y - py, z - czx)
                if x <= xb + 1:
                    if rho <= r and rho > 2.2:
                        put(cv, x, y, z, 'pot')
                elif rho <= r + (1.5 if lip else 0) and rho > r - 1.6:
                    put(cv, x, y, z, 'pot')
                elif rho <= r - 1.6 and z >= fz and x <= xm:
                    put(cv, x, y, z, 'potsoil')
    # soil spill ramp out of the mouth (1 down per column)
    for i in range(1, g - fz + 1):
        x = xm + 2 + i
        z = fz + i
        for y in range(py - 5, py + 6):
            box(cv, x, x, y, y, z, g, 'potsoil')
    box(cv, xm, xm + 2, py - 5, py + 5, fz, g, 'potsoil')
    cv.carve(xm, xm + 2, py - 5, py + 5, fz - 4, fz - 1)
    cv.interiors.append(['flowerpot', (xb + xm) // 2, py, fz])
    rep['flowerpot'] = {'floor_z': fz}
    return [xb - 4, xm + 12, py - rm - 5, py + rm + 5]


# =============================================================================================== glove

def glove(cv, rep, S, stats):
    gx, gy = S['oneoffs']['glove']
    g = S['z']['lawn']
    O = S['oneoff_dims']['glove']
    x0, x1, y0, y1 = O['site']
    flatten(cv, x0, x1, y0, y1, g, stats)

    def shell(a0, a1, b0, b1, roof, walls=True):
        box(cv, a0, a1, b0, b1, roof, g - 1, 'glove')
        cv.carve(a0 + 1, a1 - 1, b0 + 1, b1 - 1, roof + 2, g - 1)
    cx0, cx1, cy0, cy1 = O['cuff']
    box(cv, cx0, cx1, cy0, cy1, O['cuff_roof'], g - 1, 'glove_cuff')
    cv.carve(cx0 + 1, cx1 - 1, cy0, cy1, O['cuff_roof'] + 2, g - 1)       # open north end = the door
    px0, px1, py0, py1 = O['palm']
    shell(px0, px1, py0, py1, O['palm_roof'])
    cv.carve(px0 + 1, px1 - 1, py0, py0, O['palm_roof'] + 2, g - 1)        # palm opens into the cuff
    rooms = [['glove cuff', (cx0 + cx1) // 2, (cy0 + cy1) // 2, g], ['glove palm', (px0 + px1) // 2,
                                                                      (py0 + py1) // 2, g]]
    for i, (fx0, fx1, flen) in enumerate(O['fingers']):
        shell(fx0, fx1, py1, py1 + flen, O['finger_roof'])
        cv.carve(fx0 + 1, fx1 - 1, py1, py1, O['finger_roof'] + 2, g - 1)
        rooms.append([f'glove finger {i + 1}', (fx0 + fx1) // 2, py1 + flen // 2, g])
    tx0, tx1, ty0, ty1 = O['thumb']
    shell(tx0, tx1, ty0, ty1, O['finger_roof'])
    cv.carve(tx1, px0, ty0 + 1, ty1 - 1, O['finger_roof'] + 2, g - 1)
    rooms.append(['glove thumb', (tx0 + tx1) // 2, (ty0 + ty1) // 2, g])
    # stitched seams on the back of the hand (1-voxel ridges)
    for sx_ in range(px0 + 4, px1 - 3, 9):
        box(cv, sx_, sx_, py0 + 2, py1 - 2, O['palm_roof'] - 1, O['palm_roof'] - 1, 'glove_cuff')
    cv.interiors.extend(rooms)
    rep['glove'] = {'rooms': len(rooms)}
    return [x0, x1, y0, y1]


# =============================================================================================== snail shell

def snail(cv, rep, S, stats):
    sx, sy = S['oneoffs']['snail_shell']
    g = S['z']['lawn']
    O = S['oneoff_dims']['snail_shell']
    R, Rz, cz, th = O['r'], O['rz'], O['cz'], O['wall']
    flatten(cv, sx - R - 6, sx + R + 6, sy - R - 6, sy + R + 6, g, stats)
    fz = g - 1
    for x in range(sx - R - 1, sx + R + 2):
        for y in range(sy - R - 1, sy + R + 2):
            for z in range(cz - Rz - 1, g):
                e_out = ((x - sx) / R) ** 2 + ((y - sy) / R) ** 2 + ((z - cz) / Rz) ** 2
                e_in = ((x - sx) / (R - th)) ** 2 + ((y - sy) / (R - th)) ** 2 + ((z - cz) / (Rz - th)) ** 2
                if e_out <= 1 and e_in > 1:
                    a = math.atan2(y - sy, x - sx)
                    put(cv, x, y, z, 'shell_dk' if int((a / (2 * math.pi) * 3 + z / 6.0)) % 2 else 'shell')
                elif e_in <= 1 and z >= fz:
                    put(cv, x, y, z, 'floor')
    # aperture door (low, SW)
    ad = math.radians(O['door_deg'])
    for x in range(sx - R - 1, sx + R + 2):
        for y in range(sy - R - 1, sy + R + 2):
            a = math.atan2(y - sy, x - sx)
            if abs((a - ad + math.pi) % (2 * math.pi) - math.pi) < math.radians(14) and \
                    math.hypot(x - sx, y - sy) > R - th - 3:
                cv.carve(x, x, y, y, fz - 4, fz - 1)
    # columella + spiral ramp + lookout deck; the crown is broken open over the deck
    dz = O['deck_z']
    for x in range(sx - 4, sx + 5):
        for y in range(sy - 4, sy + 5):
            dd = math.hypot(x - sx, y - sy)
            if dd <= 2.2:
                box(cv, x, x, y, y, dz, fz - 1, 'shell_dk')
            elif dd <= O['deck_r']:
                put(cv, x, y, dz, 'shell_dk')
    shell_ids = (cv.material('shell'), cv.material('shell_dk'))
    for x in range(sx - R, sx + R + 1):
        for y in range(sy - R, sy + R + 1):
            rr = math.hypot(x - sx, y - sy)
            if rr <= O['hole_r']:
                for z in range(0, dz + 2 if rr > O['deck_r'] else dz):    # broken crown over the deck
                    if cv.mat[x, y, z] in shell_ids:
                        cv.clear(x, y, z)
    n = fz - 1 - dz
    a0 = O['ramp_start_deg']
    for j in range(n):
        z = fz - 1 - j
        th_c = (a0 + 30 * j) % 360
        for x in range(sx - 8, sx + 9):
            for y in range(sy - 8, sy + 9):
                dd = math.hypot(x - sx, y - sy)
                if 2.2 < dd <= O['ramp_r']:
                    a = math.degrees(math.atan2(y - sy, x - sx)) % 360
                    if -15 <= (a - th_c + 180) % 360 - 180 < 15:
                        put(cv, x, y, z, 'step')
    ox = sx + int(R - th - 4.5)
    cv.interiors.append(['snail shell floor', ox, sy, fz])
    cv.interiors.append(['snail lookout deck', sx + 3, sy, dz])
    rep['snail_shell'] = {'floor_z': fz, 'deck_z': dz, 'ramp_steps': n}
    return [sx - R - 7, sx + R + 7, sy - R - 7, sy + R + 7]


# =============================================================================================== footprint

def footprint(cv, rep, S, stats):
    fx, fy, rx, ry = S['oneoffs']['footprint']
    g = S['z']['lawn']
    O = S['oneoff_dims']['footprint']
    bare = {cv.material(m) for m in ('soil', 'lawn', 'trail', 'puddle')}
    cells = 0
    skipped = 0
    for x in range(fx - rx - 1, fx + rx + 2):
        for y in range(fy - ry - 1, fy + ry + 2):
            u = (x - fx) / rx
            if abs(u) > 1:
                continue
            # sole outline: wide toe (east) and round heel (west), two overlapping ellipses -> narrow waist
            toe = 0.85 * math.sqrt(max(0.0, 1 - ((u - 0.3) / 0.7) ** 2))
            heel = 0.6 * math.sqrt(max(0.0, 1 - ((u + 0.65) / 0.35) ** 2))
            w = ry * max(toe, heel)
            v = abs(y - fy)
            if v > w:
                continue
            t = top(cv, x, y)
            if t != cv.H[x, y] or cv.mat[x, y, t] not in bare:      # a prop stands here: leave it alone
                skipped += 1
                continue
            depth = 1 if v > w - 2 or abs(u) > 0.94 else (1 if ((x - fx) // O['tread']) % 2 == 0 else 2)
            cv.carve(x, x, y, y, 0, g + depth - 1)
            box(cv, x, x, y, y, g + depth, 63, 'soil')
            m = 'puddle' if depth == 2 else 'print'
            cv.rgb[x, y, g + depth] = GC[m]
            cv.mat[x, y, g + depth] = cv.material(m)
            cells += 1
    cv.interiors.append(['sneaker print heel', fx - rx + 10, fy, g + 1])
    rep['footprint'] = {'cells': cells, 'skipped_non_bare': skipped}
    return [fx - rx - 2, fx + rx + 2, fy - ry - 2, fy + ry + 2]


# =============================================================================================== plant label

def plant_label(cv, rep, S, stats):
    lx, ly = S['oneoffs']['plant_label']
    g = S['z']['lawn']
    O = S['oneoff_dims']['plant_label']
    hw = O['half_w']
    foot = ly + O['foot_dy']
    flatten(cv, lx - hw - 3, lx + hw + 3, foot - O['length'] - 2, foot + 4, g, stats)
    for i in range(O['length'] + 1):
        y = foot - i
        z = g - 1 - i
        w = hw if i > O['stake_len'] else max(2, int(hw * i / O['stake_len']))
        box(cv, lx - w, lx + w, y, y, z, z + 1, 'label')
    box(cv, lx - 2, lx + 2, foot, foot + 2, g - 1, g + 5, 'label')           # stake point in the soil
    cv.interiors.append(['plant label top', lx, foot - O['length'] + 2, g - 1 - O['length'] + 2])
    rep['plant_label'] = {'top_z': g - 1 - O['length']}
    return [lx - hw - 4, lx + hw + 4, foot - O['length'] - 3, foot + 5]


def build(cv, rep, S):
    """Each landmark is built inside its SPEC site (reserved in the west build, so no prop stands there); the site
    is its cosmetic box. A builder reaching outside its site is reported (it would break the mirror check)."""
    stats = {'removed': 0}
    named, spill = {}, {}
    for name, fn in (('spigot', spigot), ('hose_reel', hose_reel), ('flowerpot', flowerpot), ('glove', glove),
                     ('snail_shell', snail), ('footprint', footprint), ('plant_label', plant_label)):
        used = fn(cv, rep, S, stats)
        site = list(S['oneoff_sites'][name])
        if used[0] < site[0] or used[1] > site[1] or used[2] < site[2] or used[3] > site[3]:
            spill[name] = {'used': used, 'site': site}
        named[name] = site
    return {'boxes': list(named.values()), 'named': named, 'flatten_removed_prop_voxels': stats['removed'],
            'outside_site': spill}
