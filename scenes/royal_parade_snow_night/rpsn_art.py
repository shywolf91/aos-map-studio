"""Royal Parade Snow Night art pass: COLOUR ONLY (the solid array is asserted unchanged).

art(cv, rep, spec, seed, P) -> (glow stored colours, report)

1. original palette (48 top colours) -> moonlit night materials: snow ramps (aosmap.kit.palette.shifted_ramp,
   moonlight hue 250 / violet shadows 290, broad field max channel ~170) driven by height, coherent noise and
   material; brick and slate-stone ramps keyed to the original value; OKLab night grade for everything else
2. street: tyre-track lanes and trodden slush on the boulevard, fresh pavement snow, kerb drifts, lamp pools
3. sea: deep navy with ripple bands; painted quay ice with cracks and a snow rim (paint only, the water stays water);
   the "Royal Parade / By Bradley" credit recoloured gold / frost, "SNOW NIGHT" added above it (map name tag)
4. festive vehicles (liveries, gift wrap, sleighs, reindeer), trees, snowmen, lamps, icicles
5. lights: lit windows (share from spec), string lights along the facades (colour + 1-voxel bulbs on the wall
   surface, every 3rd bulb a glow source), tree bulbs, stars, lamp lanterns, reindeer noses
6. aosmap.kit.color.lighting (baked light + AO) -> enforce_brightness -> bake_glow -> glow-palette nudge
"""
from __future__ import annotations

import hashlib
import math

import numpy as np
from scipy import ndimage as ndi

from aosmap.kit import color, noise, palette
from aosmap.kit.codec import surface_mask
from aosmap.pixelfont import text_mask

import rpsn_source

AMBER, YELLOW, WHITE, CYAN, GREEN, RED = ((255, 175, 95), (255, 255, 95), (255, 255, 255), (95, 255, 255),
                                          (95, 255, 95), (255, 95, 95))
GLOW_PALETTE = {AMBER, YELLOW, WHITE, CYAN, GREEN, RED}
FAM = {'snow': 1, 'black': 2, 'brick': 3, 'stone': 4, 'glass': 5, 'leaf': 6, 'yellow_light': 7, 'other': 8}
BULB_SRC = [AMBER, YELLOW, AMBER, AMBER, YELLOW, AMBER]               # glow-source bulbs (red reads pink, cyan/green wash snow)
BULB_DIM = [(236, 150, 84), (226, 214, 96), (96, 200, 104), (92, 196, 206), (206, 84, 92), (232, 160, 90)]


def _lerp(a, b, t):
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    t = np.asarray(t, float)
    if t.ndim:
        t = t[..., None]
    return a + (b - a) * t


def _ramp_lookup(ramp, t):
    """ramp: list of RGB (dark -> light); t in [0, 1] (array) -> (n, 3) float, smooth interpolation."""
    stops = [(i / (len(ramp) - 1), c) for i, c in enumerate(ramp)]
    return color.ramp(stops, np.clip(t, 0, 1))


def night_grade(rgb, L_mult=0.74, C_mult=0.78, tint=(-0.006, -0.030), tint_amt=0.55, warm_keep=0.9):
    """OKLab night grade for the original's non-snow colours: dimmer, less chroma, nudged toward moonlight blue;
    saturated warm colours keep more chroma (paint, lights)."""
    lab = palette.rgb_to_oklab(np.asarray(rgb, float))
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    C = np.hypot(a, b)
    warm = (a > 0.03) & (C > 0.08)
    cm = np.where(warm, warm_keep, C_mult)
    a2 = a * cm + tint[0] * tint_amt
    b2 = b * cm + tint[1] * tint_amt
    out = palette.oklab_to_rgb(np.stack([L * L_mult, a2, b2], -1))
    return np.clip(out, 0, 255)


def art(cv, rep, spec, seed, P):
    t_sha = hashlib.sha256(np.packbits(cv.solid).tobytes()).hexdigest()
    pal = spec['palette']
    S = cv.solid
    rng = np.random.default_rng(seed ^ 0x5EED)
    lseed = spec['layout_seed']
    zs = spec['street_z']
    names = {v: k for k, v in cv.materials.items()}
    mat = cv.mat
    surf = surface_mask(S)
    orig = cv.rgb.copy()
    fam = np.zeros(S.shape, np.uint8)                            # colour-family codes (FAM) of surface voxels
    xs, ys, zz = np.nonzero(surf)
    fs = rpsn_source.colour_family(orig[xs, ys, zz])
    for k_, v_ in FAM.items():
        fam[xs[fs == k_], ys[fs == k_], zz[fs == k_]] = v_
    mid = lambda n: cv.materials.get(n, -1)                       # noqa: E731
    rep_art = {}

    # ---------------------------------------------------------------- coherent fields
    F1 = noise.fbm2((512, 512), 9, 3, 'snow_a', lseed)              # 0..1
    F2 = noise.fbm2((512, 512), 23, 3, 'snow_b', lseed)
    F3 = noise.fbm2((512, 512), 5, 2, 'snow_c', lseed)
    Fw = noise.fbm2((512, 512), 14, 3, 'water', lseed)
    top = np.argmax(S, axis=2)
    land = S[:, :, 50:63].any(axis=2)                                 # sea columns: only z 63 (jets fly over water)
    X, Y = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')

    snow_ramp = palette.shifted_ramp(pal['snow_mid'], n=7, light_step=0.045, hue_shift=6.0,
                                     light_hue=pal['snow_light_hue'], shadow_hue=pal['snow_shadow_hue'],
                                     chroma_ends=0.8, cap=176, end_tint=0.012)
    slush_ramp = palette.shifted_ramp(pal['slush'], n=5, light_step=0.04, hue_shift=6, light_hue=240,
                                      shadow_hue=262, cap=150)
    brick_ramp = palette.shifted_ramp(pal['brick'], n=5, light_step=0.055, hue_shift=8, light_hue=70, cap=200)
    stone_ramp = palette.shifted_ramp(pal['stone'], n=5, light_step=0.06, hue_shift=8, light_hue=230,
                                      shadow_hue=280, cap=200)
    green_ramp = palette.shifted_ramp(pal['evergreen'], n=5, light_step=0.05, hue_shift=10, light_hue=110,
                                      shadow_hue=250, cap=200)
    rep_art['ramps'] = {'snow': snow_ramp, 'slush': slush_ramp, 'brick': brick_ramp, 'stone': stone_ramp,
                        'evergreen': green_ramp}

    # ---------------------------------------------------------------- 1. generic night grade of every surface voxel
    m = surf.copy()
    g = night_grade(orig[m])
    cv.rgb[m] = np.clip(np.rint(g), 0, 255).astype(np.uint8)

    # snow everywhere (family 'snow' on any material, plus the street layer): moonlit ramp by height + noise
    snowm = surf & (fam == FAM['snow'])
    sx, sy, sz = np.nonzero(snowm)
    h = (zs - sz) / 40.0                                              # 0 street .. 1 at z 16
    t = 0.34 + 0.46 * np.clip(h, 0, 1) + 0.24 * (F1[sx, sy] - 0.5) + 0.12 * (F2[sx, sy] - 0.5)
    cv.rgb[sx, sy, sz] = np.rint(_ramp_lookup(snow_ramp, t)).astype(np.uint8)

    # building materials by family, keyed to the original value (keeps the authors' shading and courses)
    bmat = [mid('building'), mid('guard')]
    for fname, ramp, lo, hi in (('brick', brick_ramp, 20, 80), ('stone', stone_ramp, 40, 130)):
        mm = surf & np.isin(mat, bmat) & (fam == FAM[fname])
        bx, by, bz = np.nonzero(mm)
        L0 = color.luma(orig[bx, by, bz].astype(float))
        tt = (L0 - lo) / (hi - lo) * 0.75 + 0.12 + 0.10 * (F3[bx, by] - 0.5) + 0.04 * ((bz // 2) % 2)
        cv.rgb[bx, by, bz] = np.rint(_ramp_lookup(ramp, tt)).astype(np.uint8)
    blk = surf & (fam == FAM['black'])
    cv.rgb[blk] = pal['interior']
    # evergreen foliage of the original trees, planters and hedges
    leafm = surf & (fam == FAM['leaf']) & np.isin(mat, [mid('tree'), mid('planter'), mid('building'), mid('prop')])
    lx, ly, lz = np.nonzero(leafm)
    cv.rgb[lx, ly, lz] = np.rint(_ramp_lookup(green_ramp, 0.25 + 0.5 * F3[lx, ly] + 0.2 * (zs - lz) / 10)).astype(np.uint8)
    # quay walls / ground below the street: dark slate with value courses
    gm = surf & (mat == mid('ground'))
    gx, gy, gz = np.nonzero(gm)
    cv.rgb[gx, gy, gz] = np.rint(_ramp_lookup(stone_ramp, 0.18 + 0.12 * ((gz % 3) == 0) + 0.15 * F3[gx, gy])).astype(np.uint8)

    # ---------------------------------------------------------------- 2. street surface
    st = surf & (mat == mid('street')) & (np.arange(64)[None, None, :] == zs)
    st &= ~np.roll(S, 1, axis=2)                                     # exposed top (air at z 55)
    stx, sty = np.nonzero(st[:, :, zs])
    by0, by1 = spec['boulevard_y']
    yv = sty.astype(float)
    # boulevard: two carriageways either side of the median, each with two wheel tracks (2-3 wide, soft edges)
    trk = np.zeros(len(stx))
    for c in (243.0, 248.5, 263.5, 269.0):
        d = np.abs(yv - c)
        trk = np.maximum(trk, np.clip(1.35 - d / 1.25, 0, 1))
    wobble = 0.6 * (F2[stx, sty] - 0.5)
    in_blvd = (sty >= by0) & (sty <= by1)
    tfresh = 0.50 + 0.22 * (F1[stx, sty] - 0.5) + 0.10 * (F3[stx, sty] - 0.5)
    snow_c = _ramp_lookup(snow_ramp, tfresh)
    slush_c = _ramp_lookup(slush_ramp, 0.55 - 0.30 * trk + 0.35 * (F3[stx, sty] - 0.5))
    k = np.where(in_blvd, np.clip(0.42 + 0.55 * trk + wobble * 0.3, 0, 0.96), 0.0)
    # trampled paths on the pavements (broad noise bands near building feet and plazas)
    tramp = np.clip((F2[stx, sty] - 0.56) * 3.0, 0, 0.55) * (~in_blvd)
    k = np.maximum(k, tramp)
    cv.rgb[stx, sty, zs] = np.rint(_lerp(snow_c, slush_c, k)).astype(np.uint8)
    rep_art['street_cols'] = int(len(stx))

    # ---------------------------------------------------------------- 3. sea, quay ice, credit
    sea = (~land)
    dl = ndi.distance_transform_edt(sea)                             # distance from the quay
    wx, wy = np.nonzero(sea)
    wd = np.clip(dl[wx, wy] / 60.0, 0, 1)
    ripple = 0.5 + 0.5 * np.sin((wy * 0.55 + 7 * Fw[wx, wy]))
    wc = _lerp(pal['water_near'], pal['water_deep'], wd) * (0.94 + 0.10 * ripple[:, None]) \
        + 10 * (Fw[wx, wy, None] - 0.5)
    cv.rgb[wx, wy, 63] = np.clip(np.rint(wc), 0, 255).astype(np.uint8)
    Q = spec['quay_ice']
    Fi = noise.fbm2((512, 512), Q['cell'], 3, 'ice', lseed)
    edge = Q['band'][0] + (Q['band'][1] - Q['band'][0]) * (0.55 + 0.6 * (Fi - 0.5))
    ice = sea & (dl <= edge)
    ix_, iy_ = np.nonzero(ice)
    crack = np.abs(noise.fbm2((512, 512), 6, 2, 'crack', lseed)[ix_, iy_] - 0.5) < 0.035
    rim = dl[ix_, iy_] <= 1.5
    ic = _lerp(pal['ice'], snow_ramp[3], np.clip(0.15 + 0.5 * (Fi[ix_, iy_] - 0.3), 0, 0.6))
    ic[rim] = _lerp(ic[rim], snow_ramp[4], 0.6)
    ic[crack] = pal['ice_crack']
    cv.rgb[ix_, iy_, 63] = np.clip(np.rint(ic), 0, 255).astype(np.uint8)
    rep_art['quay_ice_cols'] = int(ice.sum())
    # the original painted credit: title gold, by-line frost (edge pixels blended by their distance from water)
    o63 = orig[:, :, 63].astype(float)
    wdist = np.clip(np.linalg.norm(o63 - np.array((153, 217, 234)), axis=-1) / 120.0, 0, 1)
    for mname, col in (('credit_title', pal['credit_title']), ('credit_by', pal['credit_by'])):
        mm = mat[:, :, 63] == mid(mname)
        cx_, cy_ = np.nonzero(mm)
        base = cv.rgb[cx_, cy_, 63].astype(float)
        shade_ = 0.86 + 0.14 * (cy_ - cy_.min()) / max(1, cy_.max() - cy_.min())
        cv.rgb[cx_, cy_, 63] = np.rint(_lerp(base, np.array(col) * shade_[:, None], wdist[cx_, cy_])).astype(np.uint8)
    # map-name tag on the water above the credit: "SNOW NIGHT" (scale 3), frost with a gold drop shadow
    tm = text_mask(['SNOW NIGHT'])
    tm = np.kron(tm, np.ones((3, 3), bool))
    tx1 = 493
    tx0 = tx1 - tm.shape[0] + 1
    ty0 = 428
    tag_rect = [tx0 - 2, tx1 + 2, ty0 - 2, ty0 + tm.shape[1] + 2, 63]
    for (i, j) in zip(*np.nonzero(tm)):
        x, y = tx0 + i, ty0 + j
        if sea[x, y]:
            cv.rgb[x, y, 63] = pal['credit_by']
            if not tm[min(i + 1, tm.shape[0] - 1), min(j + 1, tm.shape[1] - 1)] and sea[x + 1, y + 1]:
                cv.rgb[x + 1, y + 1, 63] = pal['credit_title']
    rep_art['tag_rect'] = tag_rect

    # ---------------------------------------------------------------- 4. props and festive vehicles
    def paint(name, c):
        mm = (mat == mid(name)) & S
        cv.rgb[mm] = c
        return mm

    # vehicle liveries (colour only; snow caps stay snow, darks stay dark)
    liveries = [((150, 34, 40), (198, 160, 72)), ((34, 92, 60), (198, 160, 72)), ((40, 54, 118), (206, 180, 110)),
                ((176, 168, 182), (150, 34, 40)), ((120, 30, 52), (206, 196, 170)), ((190, 140, 56), (34, 92, 60))]
    vnames = sorted(n for n in cv.materials if n.startswith('vehicle:'))
    for i, vn in enumerate(vnames):
        body, trim = liveries[i % len(liveries)]
        if vn.endswith('gift_truck_w') or vn.endswith('gift_truck_e'):
            body, trim = (150, 34, 40), (198, 160, 72)
        if 'tree_float' in vn:
            body, trim = (34, 92, 60), (198, 160, 72)
        mm = surf & (mat == mid(vn))
        vx, vy, vz = np.nonzero(mm)
        f = fam[vx, vy, vz]
        L0 = color.luma(orig[vx, vy, vz].astype(float))
        sat = (orig[vx, vy, vz].max(1).astype(int) - orig[vx, vy, vz].min(1).astype(int))
        bodym = (f != FAM['snow']) & ((sat > 60) | (L0 > 120)) & (f != FAM['black'])
        zmin = vz.min() if len(vz) else 0
        band = (vz - zmin) % 4 == 2
        c = np.where(band[:, None], np.array(trim, float), np.array(body, float))
        c = c * (0.82 + 0.18 * np.clip(L0 / 200, 0, 1))[:, None]
        cur = cv.rgb[vx, vy, vz].astype(float)
        cv.rgb[vx, vy, vz] = np.where(bodym[:, None], c, cur).astype(np.uint8)
    # gift wrap: three boxes per truck in contrasting papers with a ribbon cross
    wraps = [((150, 34, 40), (206, 176, 96)), ((36, 96, 64), (196, 40, 48)), ((44, 60, 132), (206, 184, 120))]
    for gi in range(3):
        mm = (mat == mid(f'gift{gi}')) & S
        gx_, gy_, gz_ = np.nonzero(mm)
        if not len(gx_):
            continue
        paper, ribbon = wraps[gi]
        cxr = (gx_.min() + gx_.max()) / 2
        cyr = (gy_.min() + gy_.max()) / 2
        rib = (np.abs(gx_ - cxr) < 1.0) | (np.abs(gy_ - cyr) < 1.0)
        pat = ((gx_ + gy_ + gz_) % 4 == 0)
        c = np.where(rib[:, None], np.array(ribbon, float),
                     np.where(pat[:, None], np.array(paper, float) * 1.12, np.array(paper, float)))
        cv.rgb[gx_, gy_, gz_] = np.clip(c, 0, 255).astype(np.uint8)
    paint('gift_bow', (214, 180, 92))
    # sleighs (cover sleighs and the santa sleighs), reindeer, harness, sack
    for pre in ('parkedsleigh', 'santa_sleigh'):
        paint(pre + '_body', (164, 38, 44))
        paint(pre + '_back', (150, 32, 40))
        paint(pre + '_runner', (200, 162, 76))
    for pre in ('parkedsleigh', 'santa_sleigh'):         # gold rim on the top edge of the body and backrest
        mm = np.isin(mat, [mid(pre + '_body'), mid(pre + '_back')]) & S
        rim = mm & ~np.roll(S, 1, axis=2)
        cv.rgb[rim] = (204, 168, 84)
    paint('sack', (124, 96, 66))
    paint('harness', (120, 36, 40))
    rd = paint('reindeer', (112, 80, 56))
    rx_, ry_, rz_ = np.nonzero(rd)
    if len(rx_):
        cv.rgb[rx_, ry_, rz_] = np.where(((rz_ % 2) == 0)[:, None], np.array((112, 80, 56)), np.array((126, 92, 64)))
    paint('reindeer_antler', (170, 144, 106))
    # drifts, kerb drifts, snowcaps, snowmen bodies: snow ramp with their own height/noise
    for nm, base_t in (('coverdrift', 0.55), ('kerbdrift', 0.56), ('snowcap', 0.62), ('snowman', 0.66)):
        mm = (mat == mid(nm)) & surf
        dx_, dy_, dz_ = np.nonzero(mm)
        if len(dx_):
            tt = base_t + 0.06 * (zs - dz_) / 6 + 0.12 * (F1[dx_, dy_] - 0.5)
            cv.rgb[dx_, dy_, dz_] = np.rint(_ramp_lookup(snow_ramp, tt)).astype(np.uint8)
    paint('snowman_nose', (220, 112, 40))
    paint('snowman_coal', (44, 42, 52))
    paint('snowman_hat', (40, 38, 50))
    paint('snowman_arm', (96, 66, 46))
    scarf_cols = [(176, 36, 44), (36, 110, 70), (44, 70, 150), (190, 150, 60)]
    mm = (mat == mid('snowman_scarf')) & S
    sxx, syy, szz = np.nonzero(mm)
    for i, (a, b, c) in enumerate(zip(sxx, syy, szz)):
        cv.rgb[a, b, c] = scarf_cols[(int(a) * 7 + int(b) * 3) % 4]
    # icicles: pale ice, lighter at the tip
    mm = (mat == mid('icicle')) & S
    ix2, iy2, iz2 = np.nonzero(mm)
    tipish = ~S[ix2, iy2, np.minimum(iz2 + 1, 63)]
    cv.rgb[ix2, iy2, iz2] = np.where(tipish[:, None], np.array((150, 164, 192)), np.array((128, 142, 176)))
    # lamps: iron posts and caps (lights are added as glow below)
    paint('lamp_post', pal['iron'])
    paint('lamp_cap', (62, 58, 72))
    paint('lamp_collar', (176, 146, 80))
    # Christmas trees: evergreen ramp bottom -> top, snow on tier tops, tub, trunk, garland, baubles
    tree_details = {}
    for tname in ('greattree', 'floattree'):
        mm = (mat == mid(tname)) & S
        tx_, ty_, tz_ = np.nonzero(mm)
        if not len(tx_):
            continue
        lab, n = ndi.label(mm)
        for li in range(1, n + 1):
            sel = lab[tx_, ty_, tz_] == li
            ax, ay, az = tx_[sel], ty_[sel], tz_[sel]
            if len(ax) < 30:
                continue
            zt, zb = az.min(), az.max()
            f = (zb - az) / max(1, zb - zt)
            cxm, cym = ax.mean(), ay.mean()
            c = _ramp_lookup(green_ramp, 0.12 + 0.55 * f + 0.10 * rng.random(len(ax)))
            details = tuple(sorted(rng.choice(['tinsel', 'baubles', 'snow_heavy', 'ribbon', 'pinecones'], 3,
                                              replace=False).tolist()))
            ang = np.arctan2(ay - cym, ax - cxm)
            if 'tinsel' in details:                         # gold garland spiralling down
                sp = np.abs(((ang / (2 * math.pi) * 9 + (az - zt) * 0.9) % 6) - 3) < 0.45
                c[sp] = (206, 172, 90)
            if 'ribbon' in details:                         # red ribbon spiral the other way
                sp = np.abs(((-ang / (2 * math.pi) * 9 + (az - zt) * 0.9) % 7) - 3.5) < 0.4
                c[sp] = (170, 36, 46)
            if 'baubles' in details:
                pick = rng.random(len(ax)) < 0.05
                c[pick] = np.array([(150, 40, 50), (200, 168, 80), (60, 80, 160), (180, 180, 196)])[
                    rng.integers(0, 4, pick.sum())]
            if 'pinecones' in details:
                pick = rng.random(len(ax)) < 0.03
                c[pick] = (104, 74, 50)
            exposed = ~S[ax, ay, np.maximum(az - 1, 0)]
            snow_share = 0.75 if 'snow_heavy' in details else 0.45
            snowy = exposed & (rng.random(len(ax)) < snow_share)
            c[snowy] = _ramp_lookup(snow_ramp, 0.62 + 0.1 * rng.random(snowy.sum()))
            cv.rgb[ax, ay, az] = np.clip(np.rint(c), 0, 255).astype(np.uint8)
            tree_details[f'{tname}@{int(cxm)},{int(cym)}'] = details
    paint('greattree_trunk', (88, 62, 46))
    paint('floattree_trunk', (88, 62, 46))
    tub = paint('greattree_tub', (150, 34, 40))
    tbx, tby, tbz = np.nonzero(tub)
    if len(tbx):
        top_ring = ~np.roll(S, 1, axis=2)[tbx, tby, tbz]
        cv.rgb[tbx[top_ring], tby[top_ring], tbz[top_ring]] = (200, 164, 80)
    rep_art['tree_details'] = tree_details

    # ---------------------------------------------------------------- 5. lights (glow sources)
    glow = []

    def add(x, y, z, c):
        cv.add_glow(int(x), int(y), int(z), c)
        glow.append((int(x), int(y), int(z)))

    # stars and lantern lights
    for nm, c in (('greattree_star', YELLOW), ('floattree_star', YELLOW), ('lamp_light', AMBER),
                  ('reindeer_nose', RED)):
        for (x, y, z) in np.argwhere((mat == mid(nm)) & S):
            add(x, y, z, c)
    if spec.get('variant') == 'recolor':                 # original street posts: lantern on the open-topped cap
        for (x, y, z) in rep['lamps']['lights']:
            add(x, y, z, AMBER)
    # tree bulbs on the canopy surface
    nb = {'tree_bulbs_src': 0, 'tree_bulbs_dim': 0}
    for tname in ('greattree', 'floattree'):
        pts = np.argwhere((mat == mid(tname)) & surf)
        pick = pts[rng.random(len(pts)) < 0.07]
        for i, (x, y, z) in enumerate(pick):
            if i % 3 == 0:
                add(x, y, z, BULB_SRC[i % len(BULB_SRC)])
                nb['tree_bulbs_src'] += 1
            else:
                cv.rgb[x, y, z] = BULB_DIM[i % len(BULB_DIM)]
                nb['tree_bulbs_dim'] += 1
    # lit windows. The windows of this map are real openings into dark rooms (the original paints interiors black),
    # plus a few recessed panes. Lit units: the interior surface seen straight through the opening becomes a warm
    # source (the room is lit); recessed panes become the source themselves. Unlit: dim curtain / dark glass.
    win = _window_panes(cv, S, mat, fam, mid('building'))
    opn = _window_openings(S, mat, mid('building'), spec['street_z'])
    wl, wn = ndi.label(win | opn['cells'], structure=ndi.generate_binary_structure(3, 2))
    lit_units = rng.random(wn + 1) < spec['glow']['window_lit_share']
    n_src = 0
    seen_units = set()
    wx_, wy_, wz_ = np.nonzero(win)
    for (x, y, z) in zip(wx_, wy_, wz_):
        i = wl[x, y, z]
        if lit_units[i]:
            add(x, y, z, AMBER if (i % 5) else YELLOW)
            n_src += 1
        else:
            cv.rgb[x, y, z] = pal['window_dim'] if (i % 3 == 0) else pal['window_dark']
    for (x, y, z, ix, iy, iz) in opn['looks']:
        i = wl[x, y, z]
        if lit_units[i]:
            if i not in seen_units:                      # one lamp per window unit, on the room surface behind it
                add(ix, iy, iz, AMBER if (i % 5) else YELLOW)
                n_src += 1
                seen_units.add(i)
            elif (ix, iy, iz) not in set(glow[-1:]):
                c = cv.rgb[ix, iy, iz].astype(float)
                cv.rgb[ix, iy, iz] = np.clip(c * 0.4 + np.array((236, 160, 92)) * 0.6, 0, 255)
        else:
            c = cv.rgb[ix, iy, iz].astype(float)
            cv.rgb[ix, iy, iz] = np.clip(c * 0.7 + np.array(pal['window_dark']) * 0.3, 0, 255)
    # lit units with no room surface in reach (deep halls, see-through rooms): a candle on the window sill
    candles = 0
    ox, oy, oz = np.nonzero(opn['cells'])
    for (x, y, z) in zip(ox, oy, oz):
        i = wl[x, y, z]
        if not lit_units[i] or i in seen_units:
            continue
        if z + 1 < 63 and S[x, y, z + 1] and not opn['cells'][x, y, z + 1] and surf[x, y, z + 1]:
            add(x, y, z + 1, AMBER)
            seen_units.add(i)
            candles += 1
            n_src += 1
    # the original's yellow light blocks (tower lantern, shop signs): every 8th is an amber source, the rest paint
    yl = np.argwhere(surf & (fam == FAM['yellow_light']))
    for j, (x, y, z) in enumerate(yl):
        if j % 8 == 0:
            add(x, y, z, AMBER)
        else:
            cv.rgb[x, y, z] = (214, 176, 96)
    rep_art['windows'] = {'units': int(wn), 'recessed_panes': int(win.sum()), 'openings': int(opn['cells'].sum()),
                          'opening_looks': len(opn['looks']), 'sources': n_src, 'sill_candles': candles,
                          'orig_yellow_lights': int(len(yl)), 'orig_yellow_sources': int((len(yl) + 7) // 8)}
    # string lights along the facades: wire + bulbs painted on the wall surface (no geometry, no spans)
    rep_art['string_lights'] = _string_lights(cv, S, mat, mid('building'), win, rng, add, spec)
    rep_art['bunting'] = _bunting(cv, S, mat, mid('building'), win | opn['cells'], spec)
    # lamp posts: a green garland wound up the post with two small dim bulbs (colour only)
    garl = 0
    for (x, y, z) in np.argwhere((mat == mid('lamp_post')) & S):
        if (z + x + y) % 3 == 0:
            cv.rgb[x, y, z] = (46, 92, 60)
            garl += 1
        elif (z + x + y) % 3 == 1 and z % 2 == 0:
            cv.rgb[x, y, z] = BULB_DIM[(z + x) % len(BULB_DIM)]
            garl += 1
    rep_art['lamp_garlands_voxels'] = garl
    rep_art['bulbs'] = nb
    # lamp pools: warm light painted on the snow under each street lamp (lantern z 48, street z 56: the 6.5 glow
    # radius does not reach the ground)
    pr = spec['lamps']['pool_r']
    for (x, y, z) in rep['lamps']['lights']:
        R = int(math.ceil(pr))
        for dx in range(-R, R + 1):
            for dy in range(-R, R + 1):
                d = math.hypot(dx, dy)
                X_, Y_ = x + dx, y + dy
                if d > pr or not (0 <= X_ < 512 and 0 <= Y_ < 512):
                    continue
                zt_ = int(np.argmax(S[X_, Y_]))
                if zt_ < z or not surf[X_, Y_, zt_]:
                    continue
                w = 0.56 * (1 - d / pr) ** 1.5
                c = cv.rgb[X_, Y_, zt_].astype(float)
                cv.rgb[X_, Y_, zt_] = np.clip(c * (1 - w * 0.25) + np.array((255, 176, 104)) * w * 0.85, 0, 255)

    # ---------------------------------------------------------------- 6. baked light, brightness, glow bake
    surf2 = color.lighting(cv)
    bright = color.enforce_brightness(cv, floor_min=41)
    stored, n_glow = color.bake_glow(cv, surf2, radius=spec['glow']['radius'], strength=spec['glow']['strength'])
    srcs = set(glow)
    nudged = 0
    for k_ in list(stored):
        if k_ in srcs:
            continue
        cc = tuple(int(v) for v in cv.rgb[k_])
        if cc in GLOW_PALETTE:
            cv.rgb[k_] = (max(0, cc[0] - 1), cc[1], cc[2])
            nudged += 1
    # any other non-source voxel on a palette colour (e.g. capped whites) is nudged too
    for pc in GLOW_PALETTE:
        mm = (cv.rgb == np.array(pc, np.uint8)).all(-1) & S & ~cv.nolight
        if mm.any():
            cv.rgb[mm] = (max(0, pc[0] - 1), pc[1], pc[2])
            nudged += int(mm.sum())
    after = hashlib.sha256(np.packbits(cv.solid).tobytes()).hexdigest()
    assert after == t_sha, 'art pass changed geometry'
    rep_art.update({'brightness': bright, 'glow_sources': n_glow, 'glow_stored': len(stored),
                    'palette_nudged': nudged, 'geometry_unchanged_sha': after})
    return stored, rep_art


def _window_panes(cv, S, mat, fam, bmat):
    """Recessed pane voxels: a building voxel (glass/black/dark family) whose outward neighbour is air and that air
    cell has solid jambs on both sides along the wall and solid within 2 above (a lintel)."""
    pane = np.zeros(S.shape, bool)
    cand = (mat == bmat) & S & np.isin(fam, [FAM['glass'], FAM['black'], FAM['other']])
    air = ~S
    for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        o_air = np.roll(air, (-dx, -dy), axis=(0, 1))
        tx, ty = (0, 1) if dx else (1, 0)
        j1 = np.roll(S, (-dx - tx, -dy - ty), axis=(0, 1))
        j2 = np.roll(S, (-dx + tx, -dy + ty), axis=(0, 1))
        o_s = np.roll(S, (-dx, -dy), axis=(0, 1))
        lintel = np.roll(o_s, 1, axis=2) | np.roll(o_s, 2, axis=2)
        pane |= cand & o_air & j1 & j2 & lintel
    pane[:, :, 56:] = False
    return pane


def _window_openings(S, mat, bmat, zs, depth=10):
    """Window openings: an air cell in a building wall plane with solid jambs on both sides (building material),
    solid within 2 above (lintel) and within 2 below (sill), air outside and air behind (the room). 'looks' are the
    first interior surface voxel straight through each opening cell (where the room's light shows)."""
    air = ~S
    B = (mat == bmat) & S
    cells = np.zeros(S.shape, bool)
    looks = []
    for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        tx, ty = (0, 1) if dx else (1, 0)
        out_air = np.roll(air, (-dx, -dy), axis=(0, 1))
        back_air = np.roll(air, (dx, dy), axis=(0, 1))
        j1 = np.roll(B, (-tx, -ty), axis=(0, 1)) | np.roll(B, (-2 * tx, -2 * ty), axis=(0, 1))
        j2 = np.roll(B, (tx, ty), axis=(0, 1)) | np.roll(B, (2 * tx, 2 * ty), axis=(0, 1))
        lin = np.roll(B, 1, axis=2) | np.roll(B, 2, axis=2)
        sill = np.roll(B, -1, axis=2) | np.roll(B, -2, axis=2)
        c = air & out_air & j1 & j2 & lin & sill
        c[:, :, zs - 1:] = False
        c[:, :, :2] = False
        cells |= c
        for (x, y, z) in np.argwhere(c):
            for k in range(1, depth + 1):
                X, Y = x - dx * k, y - dy * k
                if not (0 <= X < 512 and 0 <= Y < 512):
                    break
                if S[X, Y, z]:
                    looks.append((int(x), int(y), int(z), int(X), int(Y), int(z)))
                    break
    return {'cells': cells, 'looks': looks}


def _bunting(cv, S, mat, bmat, openings, spec):
    """Pennant bunting painted on the boulevard-facing facades (normals +-y), one row per facade between the first
    and second floor: inverted triangles (3 wide, 2 tall) every 5 voxels in red / green / gold / blue. Colour only,
    never on an opening; nothing spans the street."""
    zs = spec['street_z']
    by0, by1 = spec['boulevard_y']
    cols = [(150, 36, 44), (36, 104, 66), (198, 160, 72), (60, 76, 150)]
    B = (mat == bmat) & S
    n = 0
    for dy in (1, -1):
        o_air = np.roll(~S, -dy, axis=1)
        face = B & o_air
        face[:, :, zs - 6:] = False
        # facades that look onto the boulevard: the outward side is the boulevard band
        ys = np.arange(512)
        look = (ys + dy * 4 >= by0 - 12) & (ys + dy * 4 <= by1 + 12)
        face &= look[None, :, None]
        has = face.any(axis=2)
        ztop = np.where(has, np.argmax(face, axis=2), 99)
        for (x, y) in np.argwhere(has & (ztop <= zs - 14)):
            zb = int(ztop[x, y]) + 7                      # bunting line below the top floor
            k = x % 5                                     # 0 1 2 = one pennant, 3 4 = gap
            if k >= 3:
                continue
            c = cols[(x // 5) % 4]
            cells = [zb, zb + 1] if k == 1 else [zb]
            for z in cells:
                if z < zs - 2 and face[x, y, z] and not openings[x, y, z]:
                    cv.rgb[x, y, z] = c
                    n += 1
    return {'voxels': n}


def _string_lights(cv, S, mat, bmat, win, rng, add, spec):
    """Facade string lights: for every facade column (building surface with air outside), find the top of the wall
    and hang a drooping wire 2-4 below it; bulbs every 3 voxels along the wire, every 3rd bulb a glow source."""
    zs = spec['street_z']
    B = (mat == bmat) & S
    n_wire = n_bulb = n_src = 0
    seg = spec['glow']['bulb_spacing']
    for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        o_air = np.roll(~S, (-dx, -dy), axis=(0, 1))
        face = B & o_air
        face[:, :, zs - 4:] = False
        # top of the facade per column: the smallest z with a face voxel whose outward column is open below it
        has = face.any(axis=2)
        ztop = np.where(has, np.argmax(face, axis=2), 99)
        # walk along the facade direction (tangent) in runs
        tx, ty = (0, 1) if dx else (1, 0)
        cols = np.argwhere(has & (ztop <= zs - 10))
        if not len(cols):
            continue
        # sort along the tangent so the droop is continuous
        key = cols[:, 1] * 512 + cols[:, 0] if ty else cols[:, 0] * 512 + cols[:, 1]
        cols = cols[np.argsort(key)]
        for (x, y) in cols:
            u = int(y if ty else x)
            sag = int(round(1.6 * abs(math.sin(math.pi * (u % 10) / 10))))
            z = int(ztop[x, y]) + 2 + sag
            if not (0 <= z < zs - 3) or not face[x, y, z] or win[x, y, z]:
                continue
            if ((u + (x * 3 if ty else y * 3)) % seg) == 0:
                i = (u // seg) % len(BULB_SRC)
                if (u // seg) % 5 == 0:
                    add(x, y, z, BULB_SRC[i])
                    n_src += 1
                else:
                    cv.rgb[x, y, z] = BULB_DIM[i]
                n_bulb += 1
            else:
                cv.rgb[x, y, z] = (44, 66, 52)
                n_wire += 1
    return {'wire_voxels': n_wire, 'bulbs': n_bulb, 'bulb_sources': n_src}
