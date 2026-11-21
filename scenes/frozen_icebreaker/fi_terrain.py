"""Frozen Icebreaker terrain: the pack-ice island, coast, drifts, refrozen leads, polynyas, sled tracks.

Height field H[x, y] = standing-floor z (z 54 field, 63 sea). Gameplay zones (spawn squares, front, strip under the
platform, anchors, tower zones) are kept flat or gently mounded; relief lives in the skirts.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage as ndi

from aosmap.kit import noise
from aosmap.kit.canvas import line_points
from fi_spec import SPEC, PAL

ICE = SPEC['ice_z']
SEA = SPEC['sea_z']


def _fbm(cell, oct_, tag, gain=0.5):
    return noise.fbm2((512, 512), cell, oct_, tag, SPEC['layout_seed'], gain)


def island_mask():
    I = SPEC['island']
    X, Y = np.meshgrid(np.arange(512, dtype=float), np.arange(512, dtype=float), indexing='ij')
    wx = (_fbm(64, 4, 'warpx') - 0.5) * 2 * I['warp']
    wy = (_fbm(64, 4, 'warpy') - 0.5) * 2 * I['warp']
    dx = np.abs(X + wx - I['cx']) / I['rx']
    dy = np.abs(Y + wy - I['cy']) / I['ry']
    r = (dx ** 3.2 + dy ** 3.2) ** (1 / 3.2)
    land = r < 1.0
    # bays and headlands: a second, coarser bite pattern near the coast only
    bite = _fbm(40, 3, 'bite')
    land &= ~((r > 0.86) & (bite > 0.64))
    # polynyas: a few open-water holes in the skirts (west half authored, mirrored later)
    for (px, py, pr) in ((70, 352, 9), (150, 452, 7), (36, 214, 6), (168, 92, 8)):
        land &= ~((X - px) ** 2 / (pr * 1.3) ** 2 + (Y - py) ** 2 / pr ** 2 < 1)
    land = ndi.binary_opening(land, iterations=2)
    lab, n = ndi.label(land)
    if n > 1:                                           # keep the main sheet + big floes only
        sizes = ndi.sum(land, lab, range(1, n + 1))
        keep = np.zeros(n + 1, bool)
        keep[1:] = sizes >= 400
        land = keep[lab]
    return land


def keep_zones():
    """[x, y] masks of zones that must stay flat (exact) or gently mounded."""
    flat = np.zeros((512, 512), bool)
    gentle = np.zeros((512, 512), bool)
    bx, by = SPEC['spawn']['base']
    h = SPEC['spawn']['half']
    gentle[bx - h - 6:bx + h + 7, by - h - 6:by + h + 7] = True
    fx0, fx1 = SPEC['front']['x']
    flat[fx0:256, 230:283] = True                      # front band, tower zone, strip, anchor ends
    flat[176:256, 140:212] = True                      # ship site (hull sits on a level cradle)
    flat[180:256, 286:350] = True                      # drift station site
    return flat, gentle


def heightfield():
    land = island_mask()
    dist = ndi.distance_transform_edt(land)
    flat, gentle = keep_zones()
    band = SPEC['shore_band']
    sea_lab, _ = ndi.label(~land)
    outer = sea_lab == sea_lab[0, 0]
    near_outer = ndi.binary_dilation(outer, iterations=3)
    cliff = (_fbm(48, 3, 'cliff') > 0.58) & near_outer            # inland pools always get a walkable slope
    H = np.full((512, 512), SEA, np.int16)
    # coast: a 1-per-column ice slope where the coast is gentle, a 4-6 high ice cliff where `cliff` says
    slope = np.clip(band + 1 - dist, 0, band)            # dist 1 -> z 62: one step up out of the sea
    cl = np.where(dist < 2, 7, 0)
    H_land = ICE + np.where(cliff, cl, np.rint(slope)).astype(int)
    # drifts (sastrugi): elongated mounds 1-2 high in the skirts, 1 in the gentle zones, none in flat zones
    X, Y = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    dr = noise.value_noise2((512, 512), 18, 'drift', SPEC['layout_seed'])
    dr2 = noise.value_noise2((512, 512), 7, 'drift2', SPEC['layout_seed'])
    drift = np.clip((dr * 0.75 + dr2 * 0.25 - 0.52) * 6.0, 0, 2.2)
    rel = np.rint(drift).astype(int)
    rel = np.where(gentle, np.minimum(rel, 1), rel)
    rel = np.where(flat, 0, rel)
    rel = np.where(dist < band + 2, 0, rel)
    H_land = H_land - rel
    H = np.where(land, H_land, SEA).astype(np.int16)
    # refrozen leads: dark ice bands 1 below the field, following noise contours through the skirts
    ln = _fbm(90, 3, 'lead')
    lead = (np.abs(ln - 0.5) < 0.018) & land & (dist > band + 1) & ~flat & ~gentle
    # the ship's broken channel: a refrozen wake running west from the stern to the coast
    wake = (np.abs(Y - 176 - 3 * np.sin(X / 23.0)) <= 9) & (X < 182) & land & (dist > 2)
    lead |= wake
    H = np.where(lead & (H <= ICE + 1), ICE + 1, H).astype(np.int16)
    # spawn square: gentle +-1 mounds (owner: not 100 % flat, easy to spawn on, no holes)
    bx, by = SPEC['spawn']['base']
    h = SPEC['spawn']['half']
    mound = noise.value_noise2((512, 512), 11, 'spawnmound', SPEC['layout_seed'])
    sq = (slice(bx - h - 3, bx + h + 4), slice(by - h - 3, by + h + 4))
    H[sq] = np.where(mound[sq] > 0.62, ICE, ICE + 1)            # a shallow hollow: floor 55 with 54 mounds
    return H, land, dist, lead, wake


def tracks():
    """Sled tracks (packed snow, value structure + wayfinding): polylines in the west half."""
    return [
        [(118, 256), (150, 250), (196, 252)],                         # spawn -> tower zone
        [(118, 236), (124, 212), (150, 200), (184, 196)],             # spawn -> ship gangway (south side)
        [(118, 276), (130, 300), (170, 318), (190, 314)],             # spawn -> station
        [(80, 252), (96, 254), (100, 256)],                           # lodge -> spawn
        [(96, 132), (110, 168), (114, 214)],                          # tunnel mouth -> camp
        [(150, 200), (196, 150), (230, 112), (256, 96)],              # ship -> schooner (north flank)
        [(170, 318), (200, 372), (232, 410), (256, 418)],             # station -> plane (south flank)
        [(60, 300), (70, 370), (120, 420), (180, 440)],               # south flank loop
        [(60, 210), (64, 150), (110, 96), (190, 74)],                 # north flank loop
    ]


def track_mask(H, land):
    m = np.zeros((512, 512), bool)
    for pl in tracks():
        for (x0, y0), (x1, y1) in zip(pl, pl[1:]):
            for (x, y, _) in line_points(x0, y0, 0, x1, y1, 0):
                m[max(0, x - 1):x + 2, max(0, y - 1):y + 2] = True
    wob = noise.value_noise2((512, 512), 5, 'trackwob', SPEC['layout_seed']) > 0.35
    m = ndi.binary_dilation(m, iterations=1) & (wob | ndi.binary_erosion(m, iterations=1))
    return m & land & (H <= ICE)


def colour_fn(H, land, dist, lead, wake, trk):
    """Per-voxel terrain colour: top-surface classes + body strata (snow over blue ice, seabed below water)."""
    snow = np.array(PAL['snow'], float)
    crest = np.array(PAL['snow_crest'], float)
    trough = np.array(PAL['snow_trough'], float)
    track = np.array(PAL['track'], float)
    leadc = np.array(PAL['lead'], float)
    ice = np.array(PAL['ice'], float)
    deep = np.array(PAL['ice_deep'], float)
    sea = np.array(PAL['sea'], float)
    shal = np.array(PAL['shallow'], float)
    # classes: crest on the NW lip of raised drifts (short, broken), trough on their SE lee and in low spots
    Hf = H.astype(float)
    gx = np.zeros_like(Hf); gy = np.zeros_like(Hf)
    gx[1:-1] = Hf[2:] - Hf[:-2]
    gy[:, 1:-1] = Hf[:, 2:] - Hf[:, :-2]
    raised = land & (H < ICE)
    brk = noise.value_noise2((512, 512), 4, 'crestbreak', SPEC['layout_seed'])
    cls = np.zeros((512, 512), np.int8)                      # 0 field
    cls[raised & ((gx + gy) > 0) & (brk > 0.45)] = 1         # crest
    lee = land & ((gx + gy) < 0) & ~raised
    cls[lee] = 2                                             # trough
    tr = noise.value_noise2((512, 512), 23, 'troughfield', SPEC['layout_seed'])
    cls[land & (tr > 0.8) & (cls == 0)] = 2
    cls[trk] = 3
    cls[lead] = 4
    cls[land & (dist < SPEC['shore_band'] + 1) & (H > ICE)] = 5      # coastal slope / cliff: ice
    sea_d = ndi.distance_transform_edt(~land)
    cls[~land & (sea_d <= 9)] = 6
    cls[~land & (sea_d > 9)] = 7

    def f(xs, ys, zs):
        k = (((xs * 73856093) ^ (ys * 19349663) ^ (zs * 83492791)) & 0xFFFF)
        c = cls[xs, ys]
        d = zs - H[xs, ys]                                  # 0 = top voxel
        out = snow[k % len(snow)].copy()
        out[c == 1] = crest[k[c == 1] % len(crest)]
        out[c == 2] = trough[k[c == 2] % len(trough)]
        out[c == 3] = track[k[c == 3] % len(track)]
        out[c == 4] = leadc[k[c == 4] % len(leadc)]
        out[c == 5] = ice[k[c == 5] % len(ice)]
        m6 = c == 6
        out[m6] = shal[k[m6] % len(shal)]
        m7 = c == 7
        out[m7] = sea[k[m7] % len(sea)]
        # body: 2 voxels of snow, then layered blue ice (visible on cliffs, leads and tunnel walls)
        body = (d >= 2) & (c <= 5)
        layer = ((zs + (xs // 9) + (ys // 11)) % 5 == 0)
        out[body] = np.where(layer[body][:, None], deep[k[body] % len(deep)], ice[k[body] % len(ice)])
        side = (d == 1) & (c <= 5)
        out[side] = trough[k[side] % len(trough)]
        return np.clip(out, 0, 255).astype(np.uint8)
    return f


def build_terrain(cv):
    H, land, dist, lead, wake = heightfield()
    trk = track_mask(H, land)
    cv.fill_terrain(H, colour_fn(H, land, dist, lead, wake, trk), 'ground')
    return {'land': land, 'dist': dist, 'lead': lead, 'track': trk,
            'land_share': round(float(land.mean()), 3)}
