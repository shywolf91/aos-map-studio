"""Sprinkler Field centre-axis objects, built AFTER the mirror and self-symmetric about x = 256 ('x512').

build(cv, rep, S) -> {'boxes': [...cosmetic asymmetric boxes...], 'landings': {...}, ...}

  sprinkler   tripod lawn sprinkler north of the platform (assist structure 1): 7x7 foot pads, three stepped legs
              (5 wide, 1-voxel steps, rivet rails) up to the collar deck (z 24, r 11), the nozzle body (r 5) whose top
              is the head deck (z 9), a spiral of nozzle fittings round the body (z 23 -> 10, 30 deg per step), the
              spray arm stepping 9 -> 6 south to the T-bar landing (z 6) beside the platform's north edge, and the
              impact-hammer counter arm on the north side (cosmetic, high enough to leave headroom over the spiral).
  feeder      garden hose from the Y-coupling on the main hose to the north foot pad; sinks into a rut (walk over)
  trowel      half-buried garden trowel south of the platform (assist structure 2): soil heap, scoop blade (walk up the
              centre rib), stepped handle, end-cap landing (z 11)
  queen       queen chamber of the ant nest under the feeder (links the two halves' tunnels)
  cap         bottle cap bunker under the platform (under-platform prop on the axis)
  valve key   T-shaped sprinkler valve key lying on the ground at the south edge (a walk-on bridge)

Symmetric pieces are drawn in full and then re-mirrored west -> east (column 256 untouched), so rounding never
breaks the symmetry. The spiral is chiral: it is drawn last and listed as a cosmetic asymmetric box (equal access is
kept because both teams reach it on the shared collar deck, the first step sits on the axis).
"""
from __future__ import annotations

import math

import numpy as np

from sf_build import GC, KEEP, box, bottle_cap, chamber, col_down, put, top


def resym(cv, x0=150, x1=255):
    """Copy columns x0..x1 onto their mirrors 512 - x (column 256 is left as drawn)."""
    for a in (cv.solid, cv.rgb, cv.mat):
        a[512 - x1:512 - x0 + 1] = a[x0:x1 + 1][::-1]


def leg(cv, foot, end, z0, z1, w, thick):
    """Stepped leg from the foot (top z0) to the collar edge (top z1); 1-voxel steps (slope must be <= 1)."""
    fx, fy = foot
    ex, ey = end
    L = math.hypot(ex - fx, ey - fy)
    ux, uy = (ex - fx) / L, (ey - fy) / L
    for x in range(int(min(fx, ex)) - 4, int(max(fx, ex)) + 5):
        for y in range(int(min(fy, ey)) - 4, int(max(fy, ey)) + 5):
            t = (x - fx) * ux + (y - fy) * uy
            n = -(x - fx) * uy + (y - fy) * ux
            if -1 <= t <= L + 1.5 and abs(n) <= w / 2:
                zt = int(round(z0 + (z1 - z0) * min(max(t / L, 0.0), 1.0)))
                box(cv, x, x, y, y, zt, zt + thick - 1, 'leg')
                if abs(n) > 1.5 and int(t) % 3 == 0 and 2 < t < L - 1:
                    put(cv, x, y, zt - 1, 'rivet')
    return L


def sprinkler(cv, rep, S):
    P = S['sprinkler']
    hx, hy = P['hub']
    cz = P['collar_z']
    pz = P['pad_z']
    feet = dict(P['feet'])
    feet['E'] = (512 - feet['W'][0], feet['W'][1])
    legs = {}
    for name, (fx, fy) in feet.items():
        p = P['pad']
        for x in range(fx - p, fx + p + 1):
            for y in range(fy - p, fy + p + 1):
                t = top(cv, x, y)
                if t < pz:
                    cv.carve(x, x, y, y, 0, pz - 1)
                box(cv, x, x, y, y, pz, max(pz, top(cv, x, y) - 1, 53), 'pad')
        d = math.hypot(hx - fx, hy - fy)
        ex, ey = hx - (hx - fx) / d * P['collar_r'], hy - (hy - fy) / d * P['collar_r']
        L = leg(cv, (fx, fy), (ex, ey), pz, cz, P['leg_w'], P['leg_thick'])
        legs[name] = {'foot': [fx, fy], 'collar_edge': [round(ex, 1), round(ey, 1)], 'length': round(L, 1),
                      'rise': pz - cz, 'slope': round((pz - cz) / L, 3)}
    # collar deck (2 thick) and the nozzle body; the body's top is the head deck
    R = P['collar_r']
    for x in range(hx - R - 1, hx + R + 2):
        for y in range(hy - R - 1, hy + R + 2):
            dd = math.hypot(x - hx, y - hy)
            if dd <= R + 0.3:
                box(cv, x, x, y, y, cz, cz + 1, 'collar')
            if dd <= P['riser_r'] + 0.3:
                box(cv, x, x, y, y, P['head_z'] + 2, cz + 1, 'riser')
                box(cv, x, x, y, y, P['head_z'], P['head_z'] + 1, 'brass')
    # spray arm: south from the head deck, stepping head_z -> arm z, 3 wide, 2 thick
    A = P['arm']
    y0, y1 = hy + P['riser_r'], A['y'][1]
    hw = A['w'] // 2
    n_steps = P['head_z'] - A['z']
    seg = (y1 - y0 + 1) / (n_steps + 1)
    for y in range(y0, y1 + 1):
        z = P['head_z'] - min(n_steps, int((y - y0) / seg))
        box(cv, hx - hw, hx + hw, y, y, z, z + 1, 'arm')
    T = P['tbar']
    box(cv, T['x'][0], T['x'][1], T['y'][0], T['y'][1], T['z'], T['z'] + 1, 'tbar')
    # counter arm (impact hammer) on the north side, high above the spiral (>= 4 air over every fitting)
    ca = P['counter_arm']
    zc = ca['z']
    box(cv, hx - 1, hx + 1, hy - 1, hy + 1, zc, P['head_z'] - 1, 'arm')
    box(cv, hx - 1, hx + 1, ca['y'][0], hy, zc, zc + 1, 'arm')
    box(cv, hx - 2, hx + 2, ca['y'][0], ca['y'][0] + 3, zc - 1, zc + 2, 'brass')
    box(cv, hx - 2, hx + 2, ca['y'][0] + 8, ca['y'][0] + 10, zc - 1, zc - 1, 'spring')
    cv.no_prop(hx - R - 3, hx + R + 3, hy - R - 3, A['y'][1] + 2, KEEP['axis'])
    rep['sprinkler'] = {'legs': legs, 'collar_z': cz, 'head_z': P['head_z'], 'arm_z': A['z'],
                        'tbar': [T['x'], T['y'], T['z']]}


def helix(cv, rep, S):
    """Spiral of nozzle fittings round the body: step j at z head_z + 1 + j, centred at end_deg - j * deg_per_step
    (j = 0 is the last step below the head deck, the highest j sits on the collar deck's north side, on the axis)."""
    P = S['sprinkler']
    Hx = P['helix']
    hx, hy = P['hub']
    r0, r1 = Hx['r']
    n = P['collar_z'] - P['head_z'] - 1               # steps z collar_z - 1 ... head_z + 1
    half = Hx['deg_per_step'] / 2
    steps = []
    for j in range(n):
        z = P['head_z'] + 1 + j
        th = (Hx['end_deg'] - Hx['deg_per_step'] * j) % 360
        cells = 0
        for x in range(hx - int(r1) - 1, hx + int(r1) + 2):
            for y in range(hy - int(r1) - 1, hy + int(r1) + 2):
                dd = math.hypot(x - hx, y - hy)
                if not (r0 < dd <= r1):
                    continue
                a = math.degrees(math.atan2(y - hy, x - hx)) % 360
                da = (a - th + 180) % 360 - 180
                if -half <= da < half:
                    put(cv, x, y, z, 'step')
                    cells += 1
        steps.append({'j': j, 'z': z, 'deg': th, 'cells': cells})
    rep['helix'] = {'steps': len(steps), 'first': steps[-1], 'last': steps[0]}
    return [hx - int(r1) - 2, hx + int(r1) + 2, hy - int(r1) - 2, hy + int(r1) + 2]


def feeder(cv, rep, S):
    F = S['hose']['feeder']
    r = F['r_out'] + 0.4
    y0 = S['hose']['coupling'][1]
    y1 = F['path'][-1][1] - S['sprinkler']['pad'] - 1
    g = S['z']['lawn']
    top_h = 2 * F['r_out']
    ra, rb = F['rut']
    for y in range(y0, y1 + 1):
        dist = max(ra - y, y - rb, 0)
        sink = max(0, top_h - dist)                     # 1 per column down into the rut, flush at the bottom
        czy = g - F['r_out'] + sink
        for x in range(256 - F['r_out'] - 1, 256 + F['r_out'] + 2):
            dx = x - 256
            for z in range(czy - F['r_out'] - 1, min(63, czy + F['r_out'] + 1) + 1):
                if dx * dx + (z - czy) ** 2 <= r * r and not (cv.mat[x, y, z] in (cv.material('coupling'),)):
                    put(cv, x, y, z, 'hose_stripe' if (dx == 0 and z == czy - F['r_out']) else 'hose')
    cv.no_prop(256 - 8, 256 + 8, y0, y1, KEEP['axis'])
    rep['feeder'] = {'y': [y0, y1], 'rut': [ra, rb], 'top_rest_z': g - top_h}


def queen(cv, rep, S):
    qx, qy, rx, ry = S['nest']['queen']
    fl = S['z']['tunnel_floor']
    chamber(cv, qx, qy, rx, ry, fl, S['z']['tunnel_air'][0], S['nest']['chamber_air_top'] - 1)
    cv.interiors.append(['ant nest queen chamber', qx, qy, fl])
    rep['queen'] = [qx, qy, fl]


def trowel(cv, rep, S):
    Tw = S['trowel']
    g = S['z']['lawn']
    hx, hy, hrx, hry, hpz = Tw['heap']
    hmax = g - hpz
    for x in range(hx - hrx - 1, hx + hrx + 2):
        for y in range(hy - hry - 1, hy + hry + 2):
            e = 1 - math.hypot((x - hx) / hrx, (y - hy) / hry)
            if e > 0:
                h = int(round(min(hmax, 0.9 * e * min(hrx, hry))))
                if h > 0:
                    t = top(cv, x, y)
                    box(cv, x, x, y, y, g - h, max(g - h, t - 1), 'heap')
    B = Tw['blade']
    bx0, bx1 = B['x']
    by0, by1 = B['y']
    cxb = (bx0 + bx1) // 2
    hw_full = (bx1 - bx0) / 2
    for y in range(by0, by1 + 1):
        zc = B['shoulder_z'] + (y - by0) * (B['tip_z'] - B['shoulder_z']) / (by1 - by0)
        hw = hw_full * min(1.0, (by1 - y) / 18.0) ** 0.7
        for x in range(bx0, bx1 + 1):
            dx = abs(x - cxb)
            if dx > hw + 0.3:
                continue
            dish = -2.0 * (dx / max(hw, 1.0)) ** 2
            zs = int(round(zc + dish))
            mat = 'blade_steel'
            if dx <= 1:
                zs = int(round(zc)) - 1
                mat = 'rib'
            cv.carve(x, x, y, y, 0, zs - 1)
            box(cv, x, x, y, y, zs, zs + 1, mat)
    Hd = Tw['handle']
    (_, ya, za), (_, yb, zb) = Hd['from'], Hd['to']
    r = Hd['r']
    fy0, fy1 = Tw['ferrule_y']
    for y in range(yb, ya + 1):
        zh = zb + (y - yb) * (za - zb) // (ya - yb)
        for x in range(256 - r - 1, 256 + r + 2):
            dx = abs(x - 256)
            if fy0 <= y <= fy1 and dx <= r + 1:                 # ferrule ring: top flush (walkable), sides proud
                box(cv, x, x, y, y, zh if dx <= r - 1 else zh + 1, zh + r + 1, 'ferrule')
            elif dx <= r - 1:
                box(cv, x, x, y, y, zh, zh + r + 1, 'handle')
            elif dx == r:
                box(cv, x, x, y, y, zh + 1, zh + r, 'handle')
    C = Tw['cap']
    cx, cy = C['c']
    for x in range(cx - C['r'] - 1, cx + C['r'] + 2):
        for y in range(cy - C['r'] - 1, cy + C['r'] + 2):
            if math.hypot(x - cx, y - cy) <= C['r'] + 0.3:
                box(cv, x, x, y, y, C['z'], C['z'] + 2, 'ferrule')
    cv.no_prop(hx - hrx - 2, hx + hrx + 2, cy - C['r'] - 2, hy + hry + 2, KEEP['axis'])
    rep['trowel'] = {'cap': [cx, cy, C['z']], 'blade_y': [by0, by1], 'handle_y': [yb, ya]}


def valve_key(cv, rep, S):
    K = S['valve_key']
    sx = K['shaft_x']
    (s_y0, s_y1), s_top = K['socket_y'], K['socket_top']
    box(cv, 256 - K['socket_half'], 256 + K['socket_half'], s_y0, s_y1, s_top, 56, 'key')
    h_y0, h_y1 = K['handle_y']
    h_top = K['handle_top']
    hx0, hx1 = K['handle_x']
    box(cv, hx0, hx1, h_y0, h_y1, h_top, 53, 'key')
    for kx0, kx1 in ((hx0 - 4, hx0 - 1), (512 - hx0 + 1, 512 - hx0 + 4)):
        box(cv, kx0, kx1, h_y0 - 1, h_y1 + 1, K['knob_top'], 53, 'key')
    ya, yb = s_y1 + 1, h_y0
    for y in range(ya, yb + 1):
        zt = int(round(s_top + (h_top - 1 - s_top) * (y - ya) / (yb - ya)))
        box(cv, 256 - sx, 256 + sx, y, y, zt, zt + 2, 'key')
        if zt + 3 >= 50:                                 # low end of the shaft rests on the soil: no gap under it
            for x in range(256 - sx, 256 + sx + 1):
                col_down(cv, x, y, zt + 3, 'key')
    rep['valve_key'] = {'shaft_y': [ya, yb], 'handle_top': h_top}


def build(cv, rep, S):
    sprinkler(cv, rep, S)
    feeder(cv, rep, S)
    queen(cv, rep, S)
    trowel(cv, rep, S)
    for i, (kind, x, y, R) in enumerate(S['under_platform']):
        if kind == 'cap' and x == 256:
            bottle_cap(cv, rep, f'under-platform cap {i}', x, y, R, open_axis='x')
    valve_key(cv, rep, S)
    resym(cv)
    hb = helix(cv, rep, S)
    P = S['sprinkler']
    T = P['tbar']
    C = S['trowel']['cap']
    landings = {'sprinkler_tbar': [T['x'][0], T['x'][1], T['y'][0] - 2, T['y'][1], T['z'] - 1, T['z'] + 1],
                'trowel_cap': [C['c'][0] - C['r'], C['c'][0] + C['r'], C['c'][1] - C['r'], C['c'][1] + C['r'],
                               C['z'] - 1, C['z'] + 1]}
    rep['landings'] = landings
    return {'boxes': [hb], 'boxes_named': {'sprinkler spiral (chiral)': hb}, 'landings': landings}
