"""Frostbell Hollow graybox v2: gameplay geometry only (flat function colours per material, no art pass).

Order: terrain heights (relief, flats, creek, spur, ring) -> fill_terrain -> structures (west half + axis west
halves) -> underground -> props, groves, outcrops, feature pads -> [fh_main: orphan report -> mirror x512 ->
stopped train (the one asymmetric piece)]. Every number comes from fh_spec.SPEC; every random choice comes from
aosmap.kit.noise (crc32 seeds, layout seed fixed). Every room, floor, tunnel segment and chamber is recorded in
cv.interiors, at least 3 voxels inside the room where the room allows it.
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from aosmap.kit import Canvas, noise, structures  # noqa: E402
from aosmap.kit.structures import straight_stair  # noqa: E402

from fh_spec import SPEC  # noqa: E402

# flat graybox colours per material (luma >= 40, max channel <= 212)
C = {
    'snow': (188, 192, 200), 'cobble': (132, 128, 124), 'rock': (104, 102, 110), 'ice': (150, 194, 208),
    'water': (60, 90, 120), 'dirt': (112, 96, 80), 'ballast': (98, 94, 92), 'mine_floor': (120, 104, 84),
    'gravel': (146, 136, 120),
    'wall': (178, 162, 134), 'stone': (150, 146, 140), 'timber': (132, 98, 66), 'roof': (120, 70, 60),
    'floor': (122, 94, 68), 'stair': (154, 124, 92), 'rail': (86, 86, 94), 'prop': (178, 126, 66),
    'veg': (54, 98, 64), 'trunk': (98, 74, 54), 'furn': (102, 80, 58), 'metal': (112, 114, 124),
    'soldier': (168, 70, 64), 'figure': (170, 150, 120), 'hay': (196, 170, 96), 'pad': (204, 206, 210),
}
GROUND_KEYS = ['snow', 'cobble', 'rock', 'ice', 'water', 'ballast', 'gravel']   # region codes 0..6 (top voxel)
X, Y = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
XW = np.minimum(X, 512 - X)


def _box(xr, yr):
    m = np.zeros((512, 512), bool)
    m[max(0, xr[0]):xr[1] + 1, max(0, yr[0]):yr[1] + 1] = True
    return m


def _row(tag, seed, cell, octaves=2):
    """1D smooth noise in [0, 1] over 512 samples (a row of a 2D fbm)."""
    return noise.fbm2((512, 8), cell, octaves, tag, seed)[:, 0]


# =============================================================================================== masks

def plaza_mask(S=SPEC):
    p = S['plaza']
    val = np.full((512, 512), 9.0)
    for (cx, cy, rx, ry) in p['ellipses']:
        val = np.minimum(val, np.sqrt(((XW - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2))
    n = noise.fbm2((512, 512), 14, 2, 'plaza_edge', S['layout_seed'])
    m = val + p['edge_noise'] * (n - 0.5) * 2 < 1.0
    for (x0, x1, y0, y1) in p['rects']:
        m |= _box((x0, x1), (y0, y1)) | _box((512 - x1, 512 - x0), (y0, y1))
    return m


def lanes_mask(S=SPEC):
    n = noise.fbm2((512, 512), 8, 2, 'lane_edge', S['layout_seed'])
    m = np.zeros((512, 512), bool)
    for pts, w in S['lanes']:
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            dx, dy = bx - ax, by - ay
            L2 = float(dx * dx + dy * dy)
            t = np.clip(((XW - ax) * dx + (Y - ay) * dy) / L2, 0, 1)
            d = np.hypot(XW - (ax + t * dx), Y - (ay + t * dy))
            m |= d <= w / 2.0 + (n - 0.5) * 1.6
    return m


def tunnel_mask(S=SPEC, grow=2):
    m = np.zeros((512, 512), bool)
    boxes = [b for _, b in S['tunnels']] + [b for _, b in S['chambers']] + [S['house_cellar'],
                                                                           S['tavern']['cellar']]
    for (x0, x1, y0, y1) in boxes:
        m |= _box((x0 - grow, x1 + grow), (y0 - grow, y1 + grow))
    return m                    # west half only: the east half is the mirror


def creek_line(S=SPEC):
    """Creek centre y_c(x) and water half width wh(x) (symmetric about x = 256, flat derivative on the axis)."""
    cr = S['creek']
    xs = np.arange(512)
    u = 256 - np.minimum(xs, 512 - xs)
    yc = cr['y_c'] + cr['amp'] * np.sin(math.pi * u / cr['period']) * (1 - np.exp(-(u / cr['axis_flat']) ** 2))
    w0, a1, a2 = cr['wh']
    wh = np.clip(w0 + a1 * np.sin(u / 13.0) + a2 * np.sin(u / 7.0 + 1.0), *cr['wh_clamp'])
    xw = np.minimum(xs, 512 - xs)
    for (ix, L, _W) in cr['islands']:
        wh = wh + 2.5 * np.exp(-((xw - ix) / (L + 3.0)) ** 2)
    return yc, wh


# =============================================================================================== terrain

def terrain(S=SPEC):
    """Height map H[x, y] (floor z), top-surface region codes and derived geometry (mill box, protected mask)."""
    seed = S['layout_seed']
    Z = S['z']
    geo = {}
    # ---------------------------------------------------------------- relief (knolls, drifts, hollows)
    rl = S['relief']
    r1 = noise.fbm2((512, 512), rl['cells'][0], 3, 'relief', seed)
    r2 = noise.fbm2((512, 512), rl['cells'][1], 2, 'relief2', seed)
    rel = (r1 - 0.5) * rl['amp'][0] + (r2 - 0.5) * rl['amp'][1]

    # ---------------------------------------------------------------- flat gameplay zones
    plaza = plaza_mask(S)
    lanes = lanes_mask(S)
    vil = _box(*[S['village'][k] for k in ('x', 'y')])
    rw = S['railway']
    emb = _box(rw['x'], rw['embankment_y'])
    sh = rw['shoulder']
    shoulder = _box(rw['x'], (rw['embankment_y'][0] - sh, rw['embankment_y'][1] + sh)) & ~emb
    ax0, ax1, ay0, ay1 = rw['station_apron']
    apron = _box((ax0, ax1), (ay0, ay1))
    f = S['front']
    front = _box(f['x'], f['y'])
    gh = S['gatehouse']
    gate = _box((gh['x'][0] - 2, gh['x'][1] + 1), (gh['statue_y'][0] - 3, 512 - gh['statue_y'][0] + 3))
    tx0, tx1, ty0, ty1 = S['tag']['strip']
    tagstrip = _box((512 - tx1, 512 - tx0), (ty0, ty1))                        # west mirror of the NE tag strip
    flats = plaza | lanes | vil | emb | shoulder | apron | front | gate | tagstrip
    # relief fades in over 8 voxels away from the flats (no cliffs at their edges)
    dist = ndi.distance_transform_edt(~flats)
    rel_eff = np.clip(rel, *rl['clip']) * np.clip(dist / 8.0, 0, 1)
    H = (Z['valley'] - np.rint(rel_eff)).astype(int)
    region = np.zeros((512, 512), np.int8)

    mound = noise.fbm2((512, 512), 12, 2, 'mounds', seed)
    H[vil] = np.where(mound[vil] > 0.6, Z['village_mound'], Z['village'])
    H[emb | apron] = Z['rail']
    sn = noise.fbm2((512, 512), 6, 2, 'shoulder', seed)
    H[shoulder] = np.where(sn[shoulder] > 0.5, Z['rail'], Z['valley'])
    region[emb] = 5
    H[plaza | lanes] = Z['valley']
    region[plaza | lanes] = 1
    # front: gentle +-1 drifts away from its edges, flat at the gatehouse and the anchors
    fin = _box((f['x'][0] + 4, f['x'][1] - 4), (f['y'][0] + 2, f['y'][1] - 2))
    fc = rl['front_clip']
    H[front] = Z['valley']
    H[fin] = Z['valley'] - np.rint(np.clip(rel[fin] * 0.6, -fc, fc)).astype(int)
    region[front] = 0
    for hb in S['front_huts']:                       # huts stand on flat ground
        x0, x1, y0, y1 = hb['box']
        H[_box((x0 - 1, x1 + 1), (y0 - 1, y1 + 1))] = Z['valley']
    H[gate] = gh['floor_z']
    H[tagstrip] = Z['valley']
    region[_box(gh['x'], gh['y'])] = 1
    for b in (S['anchor'], S['under_platform']):
        H[_box(b['x'], b['y'])] = Z['valley']
    # building pads (village 49) so floors are flat
    ch = S['chapel']
    pads = [S['post_office']['box'], S['post_office']['wing'],
            (ch['tower'][0], ch['nave'][1], ch['nave'][2], ch['nave'][3])]
    for h in S['houses']:
        pads += [p[0] for p in h['parts']]
    for (x0, x1, y0, y1) in pads:
        H[_box((x0 - 1, x1 + 1), (y0 - 1, y1 + 1))] = Z['village']

    # ---------------------------------------------------------------- creek: meander, irregular shelves, islands
    cr = S['creek']
    yc, wh = creek_line(S)
    YC, WH = yc[X], wh[X]
    ady = np.abs(Y - YC)
    shn = noise.fbm2((512, 512), 6, 2, 'shelf', seed)
    shelf = WH + cr['shelf'] + (shn - 0.5) * 2 * cr['shelf_noise']
    shelf = np.maximum(shelf, WH + 0.6)
    bank = np.rint(Z['bank_low'] - (ady - shelf - 1) * (Z['bank_low'] - Z['valley']) / cr['bank_w'])
    cz = np.where(ady <= WH, Z['water'], np.where(ady <= shelf, Z['ice_shelf'],
                                                   np.where(ady <= shelf + 1, Z['bank_low'], bank))).astype(int)
    cm = ady <= shelf + 1 + cr['bank_w'] + 8
    H[cm] = np.maximum(H[cm], cz[cm])
    for (ix, L, W) in cr['islands']:
        isl = (((XW - ix) / L) ** 2 + ((Y - YC) / W) ** 2 <= 1.0)
        H[isl] = Z['ice_shelf']
        region[isl] = 6
    valley = cm & (cz > Z['valley'])
    geo['creek_yc'] = yc
    geo['creek_wh'] = wh

    # ---------------------------------------------------------------- water mill on the north bank
    ml = S['mill']
    mx0, mx1 = ml['x']
    mxc = (mx0 + mx1) // 2
    y1 = int(round(yc[mxc] - ml['gap_to_water']))
    y0 = y1 - ml['depth']
    floor = int(H[mxc, y0 - 3])
    H[_box((mx0 - 2, mx1 + 2), (y0 - 4, y1))] = floor
    geo['mill'] = {'box': (mx0, mx1, y0, y1), 'floor': floor, 'wheel_c': (mxc, floor + 4),
                   'wheel_y': (y1 + 1, y1 + 3)}

    # ---------------------------------------------------------------- bridge abutments + sledding hill
    bd = S['bridge']
    H[_box((bd['x'][0], 255), (398, bd['y'][0] - 1))] = bd['deck_z']
    H[_box((bd['x'][0], 255), (bd['y'][1] + 1, 461))] = bd['deck_z']
    sl = S['sled_hill']
    shm = _box(sl['x'], sl['y'])
    sz = np.rint(sl['z_bottom'] - (Y - sl['y'][0]) * (sl['z_bottom'] - sl['z_top']) / (sl['y'][1] - sl['y'][0]))
    H[shm] = np.minimum(H[shm], sz[shm].astype(int))

    # ---------------------------------------------------------------- tapered ridge spur (north range -> track)
    sp = S['spur']
    ys = np.arange(512)
    xc = sp['xc'] + sp['wiggle'] * np.sin(ys / 15.0)
    hw = sp['hw'] + sp['hw_amp'] * (_row('spur_w', seed, 24) - 0.5) * 2
    c0, c1 = sp['crest']
    crest = c0 + (c1 - c0) * np.clip((ys - sp['y'][0]) / float(sp['y'][1] - sp['y'][0]), 0, 1) + \
        3 * (_row('spur_c', seed, 16) - 0.5)
    tt = np.clip((ys - sp['tip_from']) / float(sp['y'][1] - sp['tip_from']), 0, 1)
    crest = crest + tt * (Z['rail'] - crest)
    hw = hw * (1 - 0.45 * tt)
    t = np.abs(XW + 0.5 - xc[Y] - 0.5) / hw[Y]
    hs = crest[Y] + (Z['rail'] - crest[Y]) * (1 - np.clip(1 - t, 0, 1) ** 1.3)
    spm = (t < 1) & (Y >= sp['y'][0]) & (Y <= sp['y'][1])
    H[spm] = np.minimum(H[spm], np.rint(hs[spm]).astype(int))

    # ---------------------------------------------------------------- mountain ring (noisy depth 28-60)
    rg = S['ring']
    d = np.minimum(np.minimum(XW, Y), 511 - Y).astype(float)
    wn = noise.fbm2((512, 512), rg['w_cell'], 2, 'ringw', seed)
    W = rg['w'][0] + (rg['w'][1] - rg['w'][0]) * np.clip((wn - 0.3) / 0.4, 0, 1)
    u = d / W
    pk = Z['ring_peak'][0] + (Z['ring_peak'][1] - Z['ring_peak'][0]) * noise.fbm2((512, 512), 16, 2, 'peaks', seed)
    ft = rg['face_top']
    face = pk + (ft - pk) * (u - rg['peak_u']) / (rg['face_u'] - rg['peak_u'])
    rug = (noise.fbm2((512, 512), 6, 2, 'rugged', seed) - 0.5) * 2 * rg['rugged']
    face = face + rug * np.clip((u - rg['peak_u']) * 4, 0, 1)
    ter = noise.fbm2((512, 512), 20, 2, 'terrace', seed) > 0.52
    step = rg['terrace_step']
    face = np.where(ter, np.floor(face / step) * step + 2, face)
    foot = ft + (Z['ring_foot'] - ft) * (u - rg['face_u']) / (1 - rg['face_u'])
    ringH = np.where(u <= rg['peak_u'], pk, np.where(u <= rg['face_u'], face, foot))
    # the ring may close over the creek's and the railway's ends (valley head, buffer stop) but not elsewhere
    # inside the village box only the building pads, the adit and x >= 60 are protected, so foothills reach in
    padm = np.zeros((512, 512), bool)
    for (x0, x1, y0, y1) in pads + [(48, 66, 202, 216)]:
        padm |= _box((x0 - 2, x1 + 2), (y0 - 2, y1 + 2))
    fl2 = (flats & ~vil) | (vil & (XW >= 60)) | padm
    protect = (fl2 & (XW >= 52)) | padm | (valley & (XW >= 60)) | _box(S['anchor']['x'], S['anchor']['y'])
    P = ndi.distance_transform_edt(~protect)
    ringH = np.maximum(ringH, Z['ring_foot'] - rg['approach_slope'] * P)
    ringH = np.rint(ringH).astype(int)
    rm = u <= 1.0
    H[rm] = np.minimum(H[rm], ringH[rm])

    # ---------------------------------------------------------------- safety: tunnel roofs, ceiling, pits
    tm = tunnel_mask(S)
    H[tm] = np.minimum(H[tm], rl['over_tunnels_max_z'])
    H = np.maximum(H, Z['min_solid_z'] + 1)
    for _ in range(30):                  # a column > 1 below all 4 neighbours is raised to the lowest one + 1
        nb = np.stack([np.roll(H, 1, 0), np.roll(H, -1, 0), np.roll(H, 1, 1), np.roll(H, -1, 1)]).max(0)
        pit = (H > nb + 1) & (H < 63)
        if not pit.any():
            break
        H[pit] = nb[pit] + 1
    region[(H <= 45) & (region != 1)] = 2
    region[(H >= 62) & (region != 6)] = np.where(H[(H >= 62) & (region != 6)] == 63, 4, 3)
    geo['plaza'], geo['lanes'], geo['protect'] = plaza, lanes, protect
    return H.astype(int), region, geo


def paint_terrain(cv, H, region):
    def colour(xs, ys, zs):
        top = zs == H[xs, ys]
        out = np.empty((len(xs), 3), np.uint8)
        out[:] = C['dirt']
        out[(zs > H[xs, ys] + 3) | (H[xs, ys] <= 45)] = C['rock']
        for k, key in enumerate(GROUND_KEYS):
            out[top & (region[xs, ys] == k)] = C[key]
        return out
    cv.fill_terrain(H, colour, 'ground')
    xs, ys = np.nonzero(np.ones((512, 512), bool))
    zs = H[xs, ys]
    mats = np.array([cv.material(k if k != 'snow' else 'ground') for k in GROUND_KEYS], np.uint16)
    cv.mat[xs, ys, zs] = mats[region[xs, ys]]


# =============================================================================================== helpers

def post(cv, x, y, z_top, z_floor, c=C['timber'], mat='timber'):
    cv.box(x, x, y, y, z_top, z_floor - 1, c, mat)


def gbox(cv, x0, x1, y0, y1, h, c, mat='prop'):
    """Box standing on the terrain column by column: h voxels tall from each column's surface (z H-h..H-1)."""
    for x in range(max(0, x0), min(511, x1) + 1):
        for y in range(max(0, y0), min(511, y1) + 1):
            g = int(cv.H[x, y])
            cv.box(x, x, y, y, g - h, g - 1, c, mat)


def gable(cv, x0, x1, y0, y1, roof_z, ridge='x', c=C['roof']):
    """Stepped gable on a flat roof slab at roof_z: layers shrink across the ridge direction."""
    k = 1
    while True:
        if ridge == 'x':
            a, b = y0 + k, y1 - k
            if a > b:
                break
            cv.box(x0, x1, a, b, roof_z - k, roof_z - k, c, 'roof')
        else:
            a, b = x0 + k, x1 - k
            if a > b:
                break
            cv.box(a, b, y0, y1, roof_z - k, roof_z - k, c, 'roof')
        k += 1


def free_for_prop(cv, x0, x1, y0, y1, keep_mask=0xFF):
    """No keep flag and nothing above the terrain in the box."""
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(511, x1), min(511, y1)
    if (cv.keep[x0:x1 + 1, y0:y1 + 1] & keep_mask).any():
        return False
    sub = cv.solid[x0:x1 + 1, y0:y1 + 1]
    hh = cv.H[x0:x1 + 1, y0:y1 + 1]
    zz = np.arange(64)[None, None, :]
    return not (sub & (zz < hh[:, :, None])).any()


def crate_stack(cv, x, y):
    gbox(cv, x, x + 2, y, y + 2, 2, C['prop'])
    gbox(cv, x, x + 1, y, y + 1, 3, C['prop'])


def bench(cv, x, y, along='x', length=5, back=True):
    if along == 'x':
        gbox(cv, x, x + length - 1, y, y, 1, C['furn'])
        if back:
            gbox(cv, x, x + length - 1, y + 1, y + 1, 2, C['furn'])
    else:
        gbox(cv, x, x, y, y + length - 1, 1, C['furn'])
        if back:
            gbox(cv, x + 1, x + 1, y, y + length - 1, 2, C['furn'])


def lantern(cv, x, y, h=6):
    g = int(cv.H[x, y])
    post(cv, x, y, g - h + 1, g, C['metal'], 'prop')
    cv.set(x, y, g - h, (210, 190, 120), 'prop')


def pine(cv, x, y, r, h, skirt=True):
    """Stand-in pine: a cone standing on the ground (material veg), footprint filled down to the terrain."""
    g = int(cv.H[x, y])
    zb = g - 1
    cv.cone(x + 0.5, y + 0.5, r, zb, zb - h + 1, C['veg'], 'veg')
    if skirt:
        for xx in range(x - r - 1, x + r + 2):
            for yy in range(y - r - 1, y + r + 2):
                if 0 <= xx < 512 and 0 <= yy < 512 and cv.solid[xx, yy, zb] and cv.H[xx, yy] > zb + 1:
                    cv.box(xx, xx, yy, yy, zb + 1, int(cv.H[xx, yy]) - 1, C['veg'], 'veg')


def outcrop(cv, x, y, rx, ry, rz):
    g = int(cv.H[x, y])
    cv.ellipsoid(x + 0.5, y + 0.5, g, rx, ry, rz, C['rock'], 'rock')


def feature_pad(cv, x, y, w, d, kind, pads):
    """Low (1 voxel) snow pad reserved for an art-pass one-off (snowman, ice sculpture, sled, ...)."""
    gbox(cv, x, x + w - 1, y, y + d - 1, 1, C['pad'], 'pad')
    pads.append({'kind': kind, 'box': [x, x + w - 1, y, y + d - 1]})


# =============================================================================================== village

def build_post_office(cv, S=SPEC):
    po = S['post_office']
    x0, x1, y0, y1 = po['box']
    g = S['z']['village']
    structures.building(cv, x0, x1, y0, y1, g, storeys=1, storey_h=6, doors=('S',), wall=C['wall'],
                        name='post office counter room', furnish=False)
    gable(cv, x0, x1, y0, y1, g - 6, 'x')
    # rear wing (T plan): parcel store, reached through the counter room
    wx0, wx1, wy0, wy1 = po['wing']
    structures.building(cv, wx0, wx1, wy0, wy1, g, storeys=1, storey_h=6, doors=('N',), wall=C['wall'],
                        name='post office parcel wing', furnish=False)
    gable(cv, wx0, wx1, wy0, wy1, g - 6, 'y')
    structures.door(cv, wx0 + 4, wx0 + 6, y0, y0, g)
    px = po['partition_x']
    cy = (y0 + y1) // 2
    cv.box(px, px, y0 + 1, y1 - 1, g - 5, g - 1, C['wall'], 'building')
    structures.door(cv, px, px, cy - 1, cy + 1, g)
    cv.interiors.append(['post office sorting room', (x0 + px) // 2, cy, g])
    # counter with a gap, sorting shelves, mail sacks
    cv.box(px + 1, px + 5, y1 - 8, y1 - 8, g - 1, g - 1, C['furn'], 'furniture')
    cv.box(px + 9, x1 - 1, y1 - 8, y1 - 8, g - 1, g - 1, C['furn'], 'furniture')
    cv.box(x0 + 1, x0 + 2, y0 + 2, y0 + 9, g - 3, g - 1, C['furn'], 'furniture')
    cv.box(x0 + 4, x0 + 5, y1 - 4, y1 - 3, g - 1, g - 1, C['prop'], 'prop')
    mx0, mx1, my0, my1 = po['mailbox']
    gbox(cv, mx0, mx1, my0, my1, 4, C['soldier'])
    gbox(cv, mx1 + 1, mx1 + 3, my0, my1 + 1, 1, (220, 214, 196), 'letters')           # overflowing letters
    gbox(cv, mx1 + 1, mx1 + 1, my0, my0, 2, (220, 214, 196), 'letters')


def build_village(cv, S=SPEC):
    g = S['z']['village']
    for h in S['houses']:
        for i, (box, n, sh, doors, ridge) in enumerate(h['parts']):
            x0, x1, y0, y1 = box
            nm = h['name'] if i == 0 else f"{h['name']} wing"
            structures.building(cv, x0, x1, y0, y1, g, storeys=n, storey_h=sh, doors=doors,
                                door_w=h.get('door_w', 3), wall=C['wall'], roof=C['roof'], name=nm,
                                furnish=(x1 - x0) >= 8)
            gable(cv, x0, x1, y0, y1, g - n * sh, ridge)
            for k in range(1, n):                                                       # beds upstairs
                fz = g - k * sh
                if (x1 - x0) >= 12:
                    cv.box(x1 - 4, x1 - 2, y0 + 2, y0 + 3, fz - 1, fz - 1, (150, 110, 96), 'furniture')
        if 'link' in h:
            lx0, lx1, ly0, ly1 = h['link']
            cv.carve(lx0, lx1, ly0, ly1, g - 4, g - 1)
    for (x0, x1, y0, y1) in S['fences']:
        gbox(cv, x0, x1, y0, y1, 2, C['timber'], 'fence')
    wx0, wx1, wy0, wy1 = S['well']
    gbox(cv, wx0, wx1, wy0, wy1, 2, C['stone'], 'prop')
    cx, cy = (wx0 + wx1) // 2, (wy0 + wy1) // 2
    cv.carve(cx, cx, cy, cy, int(cv.H[cx, cy]) - 2, int(cv.H[cx, cy]) - 1)
    cv.set(cx, cy, int(cv.H[cx, cy]), C['water'], 'water')
    for (x0, x1, y0, y1) in S['woodpiles']:
        gbox(cv, x0, x1, y0, y1, 2, C['trunk'])


def build_chapel_roof(cv, S=SPEC):
    ch = S['chapel']
    nx0, nx1, ny0, ny1 = ch['nave']
    gable(cv, nx0 + 1, nx1, ny0, ny1, ch['nave_roof_z'], 'x')


def build_front(cv, S=SPEC):
    """Front (gatehouse -> anchor): low walk-through props only, two open huts at the band edges, two lanterns.
    Props are scattered (SPEC['front_props']), never in rows."""
    g = S['z']['valley']
    for i, h in enumerate(S['front_huts']):
        hut(cv, *h['box'], h['open'], f'front hut {i}', g)
    if S.get('zones'):
        _front_v12(cv, S)
        return
    for (x, y, kind) in S['front_props']:
        if kind == 'sled':
            gbox(cv, x, x + 3, y, y + 1, 1, C['prop'])
        elif kind == 'firewood':
            gbox(cv, x, x + 3, y, y + 1, 2, C['trunk'])
        elif kind == 'hay':
            gbox(cv, x, x + 2, y, y + 1, 2, C['hay'])
        elif kind == 'cart':
            gbox(cv, x, x + 4, y, y + 2, 2, C['timber'])
        elif kind == 'rock':
            outcrop(cv, x, y, 2, 1.6, 1.5)
        elif kind == 'bush':
            cv.ellipsoid(x + 0.5, y + 0.5, int(cv.H[x, y]) - 1, 2, 2, 2, C['veg'], 'veg')
        elif kind == 'bench':
            bench(cv, x, y, 'x' if (x + y) % 2 else 'y')
        elif kind == 'lantern':
            lantern(cv, x, y, 6)
    # under the platform: props <= 2 tall
    bench(cv, 220, 246)
    bench(cv, 229, 263, 'y')
    gbox(cv, 238, 239, 252, 253, 1, C['prop'])


def _front_v12(cv, S):
    """v1.2 front: the same scattered layout with fewer, larger low pieces (<= 5 tall; the zone rule wants 5-30 %
    object share with 4-15 objects). The old under-platform benches are replaced by the v1.2 market pieces."""
    for (x, y, kind) in S['front_props_v12']:
        if kind == 'sled':                                    # sled loaded with sacks: 5 x 3, 2 tall
            gbox(cv, x, x + 4, y, y + 2, 2, C['prop'])
        elif kind == 'firewood':
            gbox(cv, x, x + 4, y, y + 2, 2, C['trunk'])
        elif kind == 'hay':
            gbox(cv, x, x + 4, y, y + 2, 2, C['hay'])
            gbox(cv, x + 1, x + 3, y + 1, y + 1, 3, C['hay'])
        elif kind == 'cart':
            gbox(cv, x, x + 5, y, y + 3, 2, C['timber'])
            gbox(cv, x + 1, x + 2, y + 1, y + 2, 3, C['prop'])
        elif kind == 'rock':
            outcrop(cv, x, y, 3, 2.5, 2)
        elif kind == 'bush':                                  # clipped holly drum: steep sides, not a step-up
            g0 = int(cv.H[x, y])
            cv.cylinder(x + 0.5, y + 0.5, 2.8, g0 - 3, g0 - 1, C['veg'], 'veg')
        elif kind == 'bench':                                 # bench + planter group
            bench(cv, x, y, 'x')
            gbox(cv, x + 5, x + 7, y - 1, y + 1, 2, C['stone'], 'prop')
        elif kind == 'lantern':
            lantern(cv, x, y, 6)


# =============================================================================================== market

def stall(cv, x0, x1, y0, y1, name, front='S', kind='plain', g=50):
    """Market stall: 4 corner posts, back wall, roof at g-6 (5 voxels of headroom), counter with an entrance gap.
    kind 'awning': roof runs 2 further over the front; 'L': a side wing with its own roof and posts.
    Returns the footprint box (incl. awning / wing) for the gap report."""
    rz = g - 6
    for (x, y) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        post(cv, x, y, rz + 1, g)
    cv.box(x0, x1, y0, y1, rz, rz, C['roof'], 'roof')
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    if front in ('S', 'N'):
        by, fy = (y0, y1) if front == 'S' else (y1, y0)
        cv.box(x0, x1, by, by, rz + 1, g - 1, C['timber'], 'timber')
        cv.box(x0 + 1, cx - 2, fy, fy, g - 1, g - 1, C['furn'], 'furniture')
        cv.box(cx + 2, x1 - 1, fy, fy, g - 1, g - 1, C['furn'], 'furniture')
    else:
        bx, fx = (x0, x1) if front == 'E' else (x1, x0)
        cv.box(bx, bx, y0, y1, rz + 1, g - 1, C['timber'], 'timber')
        cv.box(fx, fx, y0 + 1, cy - 2, g - 1, g - 1, C['furn'], 'furniture')
        cv.box(fx, fx, cy + 2, y1 - 1, g - 1, g - 1, C['furn'], 'furniture')
    fb = [x0, x1, y0, y1]
    if kind == 'awning':
        if front == 'S':
            cv.box(x0, x1, y1 + 1, y1 + 2, rz, rz, C['roof'], 'roof')
            fb[3] += 2
        elif front == 'N':
            cv.box(x0, x1, y0 - 2, y0 - 1, rz, rz, C['roof'], 'roof')
            fb[2] -= 2
        elif front == 'E':
            cv.box(x1 + 1, x1 + 2, y0, y1, rz, rz, C['roof'], 'roof')
            fb[1] += 2
        else:
            cv.box(x0 - 2, x0 - 1, y0, y1, rz, rz, C['roof'], 'roof')
            fb[0] -= 2
    elif kind == 'L':
        if front == 'S':
            w = (x0, x0 + 3, y1 + 1, y1 + 5)
        elif front == 'N':
            w = (x0, x0 + 3, y0 - 5, y0 - 1)
        elif front == 'E':
            w = (x1 + 1, x1 + 5, y0, y0 + 3)
        else:
            w = (x0 - 5, x0 - 1, y0, y0 + 3)
        a0, a1, b0, b1 = w
        cv.box(a0, a1, b0, b1, rz, rz, C['roof'], 'roof')
        for (x, y) in ((a0, b0), (a1, b0), (a0, b1), (a1, b1)):
            if not cv.solid[x, y, g - 1]:
                post(cv, x, y, rz + 1, g)
        cv.box(a0 + 1, a1 - 1, b0 + 1, b1 - 1, g - 1, g - 1, C['prop'], 'prop')      # side table
        fb = [min(fb[0], a0), max(fb[1], a1), min(fb[2], b0), max(fb[3], b1)]
    cv.interiors.append([name, cx, cy, g])
    return fb


def build_market(cv, S=SPEC):
    g = S['z']['valley']
    boxes = []
    for i, (x0, x1, y0, y1, front, kind) in enumerate(S['stalls']):
        boxes.append(['stall %d' % i] + stall(cv, x0, x1, y0, y1, f'stall {i}', front, kind, g))
    hn = S['hatch_stalls']['north']
    boxes.append(['hatch stall N'] + stall(cv, *hn, 'hatch stall N', front='S', g=g))
    hs = S['hatch_stalls']['south']
    boxes.append(['hatch stall S'] + stall(cv, *hs, 'hatch stall S', front='N', g=g))
    for (x, y, w, h) in S['sculptures']:
        gbox(cv, x, x + w - 1, y, y + w - 1, h, C['ice'], 'ice')
    return boxes


def build_mill(cv, geo, S=SPEC):
    ml = geo['mill']
    x0, x1, y0, y1 = ml['box']
    f = ml['floor']
    structures.building(cv, x0, x1, y0, y1, f, storeys=2, storey_h=5, doors=('N', 'W', 'E'), wall=C['wall'],
                        name='water mill')
    gable(cv, x0, x1, y0, y1, f - 10, 'x')
    wx, wz = ml['wheel_c']
    r = S['mill']['wheel_r']
    wy0, wy1 = ml['wheel_y']
    for x in range(wx - r - 1, wx + r + 2):
        for z in range(wz - r - 1, min(63, wz + r + 2)):
            d = math.hypot(x + 0.5 - (wx + 0.5), z - wz)
            ring = r - 1.3 <= d <= r + 0.2
            spoke = d <= r and (abs(x - wx) < 1 or abs(z - wz) < 1)
            if ring or spoke:
                for y in range(wy0, wy1 + 1):
                    if not cv.solid[x, y, z]:
                        cv.set(x, y, z, C['timber'], 'prop')
    cv.box(wx, wx, y1, wy1, wz, wz, C['metal'], 'prop')                                 # axle into the wall


def build_railway(cv, S=SPEC):
    rw = S['railway']
    rz = rw['rail_z']
    x_start = None
    for x in range(rw['x'][0], 256):
        if all(cv.H[x, y] == rz + 1 for y in rw['rails_y']):
            if x_start is None:
                x_start = x
            for y in rw['rails_y']:
                cv.set(x, y, rz, C['rail'], 'rail')
    if x_start is not None:                                                             # buffer stop
        cv.box(x_start, x_start + 1, rw['rails_y'][0], rw['rails_y'][1], rz - 1, rz, C['soldier'], 'prop')
    # tunnel through the ridge spur (5 x 5) - rails run through it
    sp = S['spur']
    a0, a1 = sp['tunnel_air']
    covered = []
    for x in range(sp['tunnel_x'][0], sp['tunnel_x'][1] + 1):
        for y in range(sp['tunnel_y'][0], sp['tunnel_y'][1] + 1):
            cv.carve(x, x, y, y, a0, a1)
            if not cv.solid[x, y, a1 + 1]:
                cv.set(x, y, a1 + 1, C['ballast'], 'ballast')
        for y in rw['rails_y']:
            cv.set(x, y, rz, C['rail'], 'rail')
        if cv.solid[x, sp['tunnel_y'][0] + 2, :a0].any():
            covered.append(x)
    cx = covered[len(covered) // 2] if covered else sum(sp['tunnel_x']) // 2
    cv.interiors.append(['spur rail tunnel', cx, sum(sp['tunnel_y']) // 2, rz + 1])
    for x in (covered[0], covered[-1]) if covered else ():                               # stone portals
        for y in range(sp['tunnel_y'][0] - 1, sp['tunnel_y'][1] + 2):
            if cv.solid[x, y, a0 - 1]:
                cv.set(x, y, a0 - 1, C['stone'], 'building')
    return {'covered_x': [covered[0], covered[-1]] if covered else None}


def build_chapel(cv, S=SPEC):
    ch = S['chapel']
    g = S['z']['village']
    nx0, nx1, ny0, ny1 = ch['nave']
    structures.building(cv, nx0, nx1, ny0, ny1, g, storeys=1, storey_h=g - ch['nave_roof_z'], doors=('E',),
                        wall=C['stone'], floor=C['floor'], roof=C['roof'], name='chapel nave', furnish=False)
    # pews (aisle in the middle), altar
    cy = (ny0 + ny1) // 2
    for px in range(nx0 + 5, nx1 - 3, 3):
        cv.box(px, px, ny0 + 2, cy - 2, g - 1, g - 1, C['furn'], 'furniture')
        cv.box(px, px, cy + 2, ny1 - 2, g - 1, g - 1, C['furn'], 'furniture')
    cv.box(nx0 + 2, nx0 + 3, cy - 2, cy + 2, g - 2, g - 1, C['stone'], 'furniture')
    # bell tower: 4 storeys with stairs to every floor, belfry arches, bell hanging from the roof
    tx0, tx1, ty0, ty1 = ch['tower']
    n, sh = ch['tower_storeys'], ch['tower_storey_h']
    structures.building(cv, tx0, tx1, ty0, ty1, g, storeys=n, storey_h=sh, doors=('E',), wall=C['stone'],
                        floor=C['floor'], roof=C['roof'], stair=C['stair'], name='bell tower', furnish=False)
    top_floor = g - (n - 1) * sh
    roof = g - n * sh
    tcy = (ty0 + ty1) // 2
    cv.carve(tx0, tx0, tcy - 3, tcy + 3, roof + 2, top_floor - 1)
    cv.carve(tx1, tx1, tcy - 3, tcy + 3, roof + 2, top_floor - 1)
    cv.carve(tx0 + 3, tx1 - 3, ty0, ty0, roof + 2, top_floor - 1)
    cv.carve(tx0 + 3, tx1 - 3, ty1, ty1, roof + 2, top_floor - 1)
    cv.box(tx0 + 4, tx0 + 6, tcy - 1, tcy + 1, roof + 1, roof + 2, C['metal'], 'prop')      # bell
    # a door from the nave back out (west side of the tower is the mountain side)
    structures.door(cv, tx0, tx0, tcy - 1, tcy + 1, g)


def build_gatehouse(cv, S=SPEC):
    """Toy-soldier gatehouse: open passages z 41-49 between three piers, gallery room z 30-39 over them, roof z 28-29,
    end towers with a two-flight stair from floor 50 to the gallery floor 40. Built as the north half (y <= 256)
    and reflected in y about 256 (y' = 512 - y)."""
    gh = S['gatehouse']
    x0, x1 = gh['x']
    yA = gh['y'][0]
    ty1 = gh['tower_y'][1]
    g = gh['floor_z']
    gf = gh['gallery_floor']
    r0, r1 = gh['roof']
    ga0, ga1 = gh['gallery_air']
    pa0, pa1 = gh['passage_air']
    W, T = C['stone'], C['soldier']
    cv.carve(x0, x1, yA, 256, r0, g - 1)
    cv.box(x0, x1, yA, 256, r0, r1, C['roof'], 'roof')                       # roof slab
    cv.box(x0, x1, yA, 256, gf, gf, C['floor'], 'building')                  # gallery floor
    cv.box(x0, x0, yA, 256, ga0, ga1, W, 'building')                          # gallery walls
    cv.box(x1, x1, yA, 256, ga0, ga1, W, 'building')
    cv.box(x0, x1, yA, yA, ga0, ga1, W, 'building')
    # end tower shell (y yA..ty1) below the gallery floor
    cv.box(x0, x1, yA, ty1, pa0, pa1, T, 'building')
    cv.carve(x0 + 1, x1 - 1, yA + 1, ty1 - 1, pa0, pa1)
    for d_x in (x0, x1):                                                       # doors west and east
        structures.door(cv, d_x, d_x, yA + 1, yA + 2, g)
    # piers inside the band
    for (p0, p1) in gh['piers']:
        if p0 <= 256:
            cv.box(x0, x1, p0, min(p1, 256), pa0, pa1, T, 'building')
    # stairs: flight A along +y at x0+1..x0+2 (50 -> 45), landing pillar, flight B along -y at x0+3..x0+4 (45 -> 40)
    straight_stair(cv, yA + 3, x0 + 1, x0 + 2, g, 5, 1, C['stair'], along='y')
    cv.box(x0 + 1, x1 - 1, yA + 8, ty1 - 1, g - 5, g - 1, C['stair'], 'stair')
    straight_stair(cv, yA + 7, x0 + 3, x0 + 4, g - 5, 5, -1, C['stair'], along='y')
    # arrow slits (not aligned east/west)
    for y in (236, 248):
        cv.carve(x0, x0, y, y, 33, 35)
    for y in (243,):
        cv.carve(x1, x1, y, y, 33, 35)
    # toy-soldier statue at the outer end
    s0, s1 = gh['statue_y']
    cv.box(x0 + 1, x1 - 1, s0, s1, g - 3, g - 1, C['stone'], 'prop')
    cv.box(x0 + 1, x1 - 1, s0, s1, 36, g - 4, T, 'prop')
    cv.box(x0 + 2, x1 - 2, s0 + 1, s1 - 1, 33, 35, C['figure'], 'prop')
    cv.box(x0 + 2, x1 - 2, s0 + 1, s1 - 1, 29, 32, (60, 56, 70), 'prop')
    # reflect the north half to the south (y' = 512 - y)
    ys = np.arange(s0 - 1, 256)
    for a in (cv.solid, cv.rgb, cv.mat):
        a[x0:x1 + 1, 512 - ys] = a[x0:x1 + 1, ys]
    cv.interiors += [['gatehouse north tower', x0 + 3, yA + 6, g], ['gatehouse south tower', x0 + 3, 512 - yA - 6, g],
                     ['gatehouse gallery', x0 + 2, 245, gf], ['gatehouse stair landing', x0 + 2, yA + 9, g - 5]]


# ---------------------------------------------------------------- gatehouse variants (exposure experiment)

def _statues(cv, S):
    gh = S['gatehouse']
    x0, x1 = gh['x']
    g = gh['floor_z']
    s0, s1 = gh['statue_y']
    T = C['soldier']
    for (a, b) in ((s0, s1), (512 - s1, 512 - s0)):
        cv.box(x0 + 1, x1 - 1, a, b, g - 3, g - 1, C['stone'], 'prop')
        cv.box(x0 + 1, x1 - 1, a, b, 36, g - 4, T, 'prop')
        cv.box(x0 + 2, x1 - 2, a + 1, b - 1, 33, 35, C['figure'], 'prop')
        cv.box(x0 + 2, x1 - 2, a + 1, b - 1, 29, 32, (60, 56, 70), 'prop')


def _stair_tower(cv, ta, tb, south, name, closed_inner=False):
    """Gate tower x 143-151 (extends 3 west of the gate, still outside the spawn margin x <= 142), rows ta..tb
    given in north orientation (south=True mirrors them to 512 - y). Two flights along x: floor 50 -> landing 45
    -> tower room floor 40; room z 30-39, roof z 28-29; west door. Returns the room rows."""
    def Y(a, b):
        return (a, b) if not south else (512 - b, 512 - a)
    X0, X1, g = 143, 151, 50
    W, T = C['stone'], C['soldier']
    ya, yb = Y(ta, tb)
    cv.carve(X0, X1, ya, yb, 28, g - 1)
    cv.box(X0, X1, ya, yb, 41, g - 1, T, 'building')                  # shell below the room
    cv.carve(X0 + 1, X1 - 1, *Y(ta + 1, tb - 1), 41, g - 1)
    cv.box(X0, X1, ya, yb, 40, 40, C['floor'], 'building')             # room floor
    cv.box(X0, X1, ya, yb, 30, 39, W, 'building')                      # room walls
    cv.carve(X0 + 1, X1 - 1, *Y(ta + 1, tb - (0 if not closed_inner else 1)), 30, 39)
    cv.box(X0, X1, ya, yb, 28, 29, C['roof'], 'roof')
    structures.door(cv, X0, X0, *Y(ta + 1, ta + 2), g)
    a1, a2 = Y(ta + 1, ta + 2)
    straight_stair(cv, X0 + 2, a1, a2, g, 5, 1, C['stair'])
    cv.box(X1 - 1, X1 - 1, *Y(ta + 1, tb - 1), g - 5, g - 1, C['stair'], 'stair')
    b1, b2 = Y(tb - 2, tb - 1)
    straight_stair(cv, X1 - 2, b1, b2, g - 5, 5, -1, C['stair'])
    for yy in range(ya + 2, yb - 1, 4):                                 # arrow slits on the west face
        cv.carve(X0, X0, yy, yy, 33, 35)
    my = (ya + yb) // 2
    cv.interiors += [[f'{name} tower floor', X0 + 1, Y(ta + 1, ta + 2)[0], g],
                     [f'{name} tower landing', X1 - 1, my, g - 5], [f'{name} tower room', X0 + 3, my, 40]]


def build_gate_variant(cv, S, v):
    """Shortened / lowered gatehouses for the exposure experiment. Passages z 41-49, piers <= 5, >= 60 % of the
    front band open, toy-soldier statues kept; a gallery only where stairs reach it."""
    gh = S['gatehouse']
    x0, x1 = gh['x']
    g = gh['floor_z']
    W, T = C['stone'], C['soldier']
    if v in ('low', 'none'):
        build_gatehouse(cv, S)
        cv.interiors = [i for i in cv.interiors if not i[0].startswith('gatehouse')]
        if v == 'none':
            cv.carve(x0, x1, gh['y'][0], gh['y'][1], 0, g - 1)
            return
        # low: keep the towers and the gallery floor (z 40); the band above is a crenellated parapet z 36-39
        cv.carve(x0, x1, gh['y'][0], gh['y'][1], 0, 35)
        for y in range(gh['y'][0], gh['y'][1] + 1, 3):
            cv.carve(x0, x0, y, y, 36, 37)
            cv.carve(x1, x1, y, y, 36, 37)
        cv.interiors += [['gatehouse north tower', x0 + 3, gh['y'][0] + 6, g],
                         ['gatehouse south tower', x0 + 3, 512 - gh['y'][0] - 6, g],
                         ['gatehouse parapet walk', x0 + 2, 245, gh['gallery_floor']]]
        return
    if v != 'arch':
        _statues(cv, S)
    if v == 'band':
        for south in (False, True):
            _stair_tower(cv, 228, 235, south, 'gate S' if south else 'gate N')
        # gallery x 146-151 between the towers (rows 236-276), open into both tower rooms
        cv.carve(x0, x1, 236, 276, 28, g - 1)
        cv.box(x0, x1, 236, 276, 28, 29, C['roof'], 'roof')
        cv.box(x0, x1, 236, 276, 40, 40, C['floor'], 'building')
        cv.box(x0, x0, 236, 276, 30, 39, W, 'building')
        cv.box(x1, x1, 236, 276, 30, 39, W, 'building')
        cv.carve(x0 + 1, x1 - 1, 235, 277, 30, 39)
        for (p0, p1) in ((245, 247), (254, 258), (265, 267)):
            cv.box(x0, x1, p0, p1, 41, g - 1, T, 'building')
        cv.interiors.append(['gate gallery', x0 + 2, 250, 40])
    elif v == 'arch':
        # v1.1: single central gate y 240-272, solid masonry lintel z 28-40 (a gate, not a building: no room, no
        # interior record), crenellated top, four piers -> three passages, free-standing toy soldiers beside it
        ar = gh['arch']
        a0, a1 = ar['y']
        cv.carve(x0, x1, a0, a1, 28, g - 1)
        cv.box(x0, x1, a0, a1, 28, 40, W, 'building')
        cv.box(x0, x1, a0, a1, 28, 28, C['roof'], 'roof')
        m0, m1 = ar['merlon_z']
        for y in range(a0, a1 + 1):
            if ((abs(y - 256) + 1) // 2) % 2 == 0 or y in (a0, a1):
                for xx in (x0, x1):
                    cv.box(xx, xx, y, y, m0, m1, W, 'building')
        cv.box(x0 + 1, x1 - 1, 254, 258, m0 - 2, m1, W, 'building')        # raised centre block for the wreath
        for (p0, p1) in ar['piers']:
            cv.box(x0, x1, p0, p1, 41, g - 1, T, 'building')
        _arch_statues(cv, S)
        _arch_edge_dressing(cv, S)
    elif v in ('twin', 'twin_bridge'):
        for south in (False, True):          # 10 long, 5 rows inside the front band (pier <= 5)
            _stair_tower(cv, 227, 236, south, 'twin S' if south else 'twin N', closed_inner=(v == 'twin'))
        if v == 'twin_bridge':
            # light bridge between the tower rooms: deck z 40, crenellated parapets z 36-39, open sky above
            cv.box(x0, x1, 237, 275, 40, 40, C['floor'], 'building')
            cv.box(x0, x0, 237, 275, 36, 39, W, 'building')
            cv.box(x1, x1, 237, 275, 36, 39, W, 'building')
            for y in range(237, 276, 3):
                cv.carve(x0, x0, y, y, 36, 37)
                cv.carve(x1, x1, y, y, 36, 37)
            for (p0, p1) in ((254, 258),):
                cv.box(x0, x1, p0, p1, 41, g - 1, T, 'building')
            cv.interiors.append(['twin bridge deck', x0 + 2, 250, 40])
    else:
        raise ValueError(v)


def _arch_statues(cv, S):
    """Two free-standing toy soldiers beside the arch (rows 228-231 and the y-mirror, outside the front band and the
    passages): plinth, legs, coat, epaulettes, shako with plume, and a drum held in front (no weapon)."""
    gh = S['gatehouse']
    g = gh['floor_z']
    s0, s1 = gh['arch']['statue_y']
    for south in (False, True):
        def Y(a, b):
            return (a, b) if not south else (512 - b, 512 - a)
        cv.box(146, 151, *Y(s0 - 1, s1), g - 2, g - 1, C['stone'], 'statue')            # plinth (2 high)
        cv.box(148, 149, *Y(s0, s0 + 1), g - 7, g - 3, (52, 50, 58), 'statue')           # legs
        cv.box(148, 149, *Y(s1 - 1, s1), g - 7, g - 3, (52, 50, 58), 'statue')
        cv.box(147, 150, *Y(s0, s1), g - 14, g - 8, C['soldier'], 'statue')             # coat
        cv.box(147, 150, *Y(s0 - 1, s0 - 1), g - 14, g - 10, C['soldier'], 'statue')    # sleeves
        cv.box(147, 150, *Y(s1 + 1, s1 + 1), g - 14, g - 10, C['soldier'], 'statue')
        cv.box(148, 149, *Y(s0 + 1, s1 - 1), g - 17, g - 15, C['figure'], 'statue')     # head
        cv.box(148, 149, *Y(s0, s1), g - 22, g - 18, (48, 46, 54), 'statue')            # shako
        cv.box(149, 149, *Y(s0 + 1, s0 + 1), g - 24, g - 23, (200, 196, 190), 'statue')  # plume
        cv.box(151, 151, *Y(s0 + 1, s1 - 1), g - 10, g - 8, (196, 160, 80), 'statue')   # drum in front
    return 2


def _arch_edge_dressing(cv, S):
    """Village-edge detail on the ground the old end towers used (outside the front band where possible): low
    holly-hedge stubs, a sled, a lantern post and a snowman pad north of each statue (y-mirrored)."""
    g = S['gatehouse']['floor_z']
    for south in (False, True):
        def Y(a, b):
            return (a, b) if not south else (512 - b, 512 - a)
        gbox(cv, 143, 144, *Y(219, 223), 2, (54, 98, 64), 'hedge')                      # hedge stub, 2 tall
        gbox(cv, 143, 143, *Y(233, 237), 2, (54, 98, 64), 'hedge')                      # x 143: west of the gate
        a, b = Y(224, 225)
        gbox(cv, 150, 151, a, b, 1, C['prop'], 'prop')                                  # sled
        lantern(cv, 145, Y(226, 226)[0], 6)


def build_zone_pieces(cv, S):
    """v1.2 (2026-11-13 zone rules), all layout-fixed:
    - under the platform: a low open bandstand on the axis, two hearth courts (U-shaped seat walls round a brazier),
      a trestle-table set, a fir tub and hay-bale edges; all <= 5 tall except the bandstand roof (7); x <= 217 clear;
    - spawn cover on the enemy side: buttresses in front of the arch piers (5 tall, part of the gate), hedge walls
      and log stacks beside the gate ends, two small firs north/south of the market lanes;
    - rear backdrop: six firs behind the village square (positions pinned; look still from the veg seed).
    Returns the pinned stand-in pines [(x, y, r, h)]."""
    V = S['v12']
    g = S['z']['valley']
    # ---------------------------------------------------------------- under the platform
    gz = V['gazebo']
    cx, cy = gz['c']
    rz = gz['roof_z']
    cv.cylinder(cx, cy + 0.5, gz['r'] - 1, g - 1, g - 1, C['timber'], 'gazebo')        # floor, 1 high
    cv.cylinder(cx, cy + 0.5, gz['r'], rz, rz, C['roof'], 'gazebo')                    # roof (7 above the ground)
    cv.cylinder(cx, cy + 0.5, gz['r'], rz + 1, rz + 1, C['roof'], 'gazebo', hollow=gz['r'] - 1)   # valance
    for k in range(8):
        a = (k + 0.5) * math.pi / 4
        px = int(math.floor(cx + (gz['r'] - 1.2) * math.cos(a)))
        py = int(math.floor(cy + 0.5 + (gz['r'] - 1.2) * math.sin(a)))
        if px <= 255:
            post(cv, px, py, rz + 1, g - 1, C['metal'], 'gazebo')
    for (x0, x1, y0, y1) in V['hearths']:
        open_e = True
        cv.box(x0, x0, y0, y1, g - 2, g - 1, C['stone'], 'hearth')                     # back wall (west)
        cv.box(x0, x1, y0, y0, g - 2, g - 1, C['stone'], 'hearth')                     # side walls
        cv.box(x0, x1, y1, y1, g - 2, g - 1, C['stone'], 'hearth')
        my = (y0 + y1) // 2
        cv.box(x0 + 1, x0 + 3, my, my, g - 2, g - 1, C['stone'], 'hearth')            # hearth stone to the brazier
        cv.box(x0 + 4, x0 + 5, my - 1 if (y1 - y0) % 2 else my, my, g - 2, g - 1, C['metal'], 'brazier')
    tx0, tx1, ty0, ty1 = V['trestle']
    cv.box(tx0, tx1, ty0, ty0 + 1, g - 2, g - 1, C['furn'], 'trestle')
    cv.box(tx0, tx1, ty1 - 1, ty1, g - 2, g - 1, C['furn'], 'trestle')
    cv.box(tx0, tx0 + 1, ty0 + 2, ty1 - 2, g - 2, g - 1, C['furn'], 'trestle')            # serving counter
    px0, px1, py0, py1 = V['planter']
    cv.box(px0, px1, py0, py1, g - 2, g - 1, C['stone'], 'planter')
    cv.cone((px0 + px1 + 1) / 2, (py0 + py1 + 1) / 2, 2.2, g - 3, g - 5, C['veg'], 'planter_fir')
    for (x0, x1, y0, y1) in V['hay']:
        cv.box(x0, x1, y0, y1, g - 2, g - 1, C['hay'], 'hay')
    # ---------------------------------------------------------------- enemy-side spawn cover
    gh = S['gatehouse']
    bx0, bx1 = V['buttress_x']
    for (p0, p1) in gh['arch']['piers']:
        cv.box(bx0, bx1, p0, p1, g - 5, g - 1, C['soldier'], 'buttress')
    for south in (False, True):
        def Y(a, b):
            return (a, b) if not south else (512 - b, 512 - a)
        for (x0, x1, y0, y1) in V['cover_hedges']:
            gbox(cv, x0, x1, *Y(y0, y1), 4, (54, 98, 64), 'hedge')
        for (x0, x1, y0, y1) in V['cover_logs']:
            gbox(cv, x0, x1, *Y(y0, y1), 3, C['trunk'], 'prop')
    pinned = []
    for (x, y, r, h) in V['cover_firs'] + V['backdrop_firs']:
        for yy in ((y,) if (x, y, r, h) in V['backdrop_firs'] else (y, 512 - y)):
            pine(cv, x, yy, r, h)
            pinned.append((x, yy, r, h))
    return pinned


def build_flank_cover(cv, S):
    """'+ flank cover' experiment: tall rock spires right beside the gate ends and rock crags NE/SE of the spawn
    square - all outside the front band (y 232-280 for x 152-199) and outside the spawn square + margin."""
    full_len = S['gatehouse'].get('variant', 'full') in ('full', 'low')   # full-length towers occupy y 220-292
    xs0, xs1 = (136, 142) if full_len else (144, 150)
    for (a, b) in ((218, 225), (287, 294)):
        cv.box(xs0, xs1, a, b, 14, 49, C['rock'], 'rock')
    for (a, b) in ((216, 226), (286, 296)):
        cv.box(124, 132, a, b, 16, 48, C['rock'], 'rock')


def hut(cv, x0, x1, y0, y1, open_side, name, g=50):
    """Open one-room hut on the front: 5 tall (roof z g-5), walls on three sides with side doors."""
    rz = g - 5
    cv.box(x0, x1, y0, y1, rz, g - 1, C['timber'], 'building')
    cv.carve(x0 + 1, x1 - 1, y0 + 1, y1 - 1, rz + 1, g - 1)
    if open_side == 'S':
        cv.carve(x0 + 1, x1 - 1, y1, y1, rz + 1, g - 1)
    else:
        cv.carve(x0 + 1, x1 - 1, y0, y0, rz + 1, g - 1)
    cy = (y0 + y1) // 2
    for xx in (x0, x1):
        cv.carve(xx, xx, cy, cy + 1, rz + 1, g - 1)
    cv.box(x0 + 1, x0 + 2, y0 + 1 if open_side == 'S' else y1 - 1, y0 + 1 if open_side == 'S' else y1 - 1,
           g - 1, g - 1, C['furn'], 'furniture')
    cv.interiors.append([name, (x0 + x1) // 2, cy, g])


def build_axis(cv, S=SPEC):
    g = S['z']['valley']
    # station + canopy over the platform
    st = S['station']
    x0, x1, y0, y1 = st['box']
    f = st['floor']
    structures.building(cv, x0, x1, y0, y1, f, storeys=1, storey_h=6, doors=('S', 'N', 'W'), wall=C['wall'],
                        name='station', furnish=True)
    cy0, cy1 = st['canopy_y']
    cv.box(x0, 255, cy0, cy1, f - 6, f - 6, C['roof'], 'roof')
    for px in (x0 + 2, x0 + 8):
        post(cv, px, cy1, f - 5, f, C['metal'], 'timber')
    bench(cv, x0 + 3, cy0 + 1, 'x', back=False)

    # nativity stable (open to the south), figures, manger, star
    nx0, nx1, ny0, ny1 = S['nativity']['box']
    cv.box(nx0, 255, ny0, ny0, g - 6, g - 1, C['timber'], 'building')
    cv.box(nx0, nx0, ny0, ny1, g - 6, g - 1, C['timber'], 'building')
    cv.box(nx0, 255, ny0 - 1, ny1 + 1, g - 7, g - 7, C['roof'], 'roof')
    cv.box(nx0 + 4, nx0 + 4, ny0 + 3, ny0 + 3, g - 3, g - 1, C['figure'], 'prop')
    cv.box(nx0 + 2, nx0 + 2, ny0 + 6, ny0 + 6, g - 3, g - 1, C['figure'], 'prop')
    cv.box(253, 255, ny0 + 4, ny0 + 5, g - 1, g - 1, C['hay'], 'prop')
    cv.box(nx0 + 1, nx0 + 3, ny0 + 1, ny0 + 2, g - 2, g - 1, C['figure'], 'prop')
    cv.box(254, 255, (ny0 + ny1) // 2, (ny0 + ny1) // 2, g - 9, g - 8, (210, 200, 140), 'prop')
    cv.interiors.append(['nativity stable', 252, ny0 + 4, g])

    # tavern: two floors + cellar (cellar is dug in build_underground)
    tv = S['tavern']
    x0, x1, y0, y1 = tv['box']
    structures.building(cv, x0, x1, y0, y1, tv['floor'], storeys=2, storey_h=5, doors=('N', 'S', 'W'),
                        wall=C['wall'], name='tavern', furnish=False)
    cv.box(x0 + 4, x0 + 12, y1 - 3, y1 - 3, g - 1, g - 1, C['furn'], 'furniture')          # bar counter
    cv.box(x0 + 2, x0 + 3, y0 + 9, y0 + 10, g - 1, g - 1, C['furn'], 'furniture')          # table
    cv.box(x0 + 12, x0 + 13, y0 + 5, y0 + 6, g - 6, g - 6, C['furn'], 'furniture')         # upstairs table
    for (bx, by) in ((x0 + 2, y1 - 6), (x0 + 3, y1 - 8)):                                  # barrels by the wall
        cv.box(bx, bx, by, by, g - 2, g - 1, C['trunk'], 'furniture')
    for sx in (x0 + 5, x0 + 8, x0 + 11):                                                    # bar stools
        cv.box(sx, sx, y1 - 5, y1 - 5, g - 1, g - 1, C['furn'], 'furniture')
    cv.box(x0 + 4, x0 + 6, y0 + 9, y0 + 10, g - 6, g - 6, C['furn'], 'furniture')          # upstairs bed

    # giant spruce stand-in (trunk + cone, material veg)
    sp = S['spruce']
    cx, cy = sp['c']
    cv.cylinder(cx, cy + 0.5, sp['trunk_r'], sp['tip_z'], g - 1, C['trunk'], 'veg')
    cv.cone(cx, cy + 0.5, sp['r'] - 0.5, sp['cone_base_z'], sp['tip_z'], C['veg'], 'veg')

    # carousel: platform, pole, canopy, posts, horses (<= 8 tall)
    ca = S['carousel']
    cx, cy = ca['c']
    r = ca['r']
    cv.cylinder(cx, cy + 0.5, r, g - 1, g - 1, C['timber'], 'prop')
    cv.cylinder(cx, cy + 0.5, 1.5, ca['canopy_z'] + 1, g - 2, C['metal'], 'prop')
    cv.cylinder(cx, cy + 0.5, r, ca['canopy_z'], ca['canopy_z'], C['roof'], 'roof')
    for k in range(8):
        a = (k + 0.5) * math.pi / 4
        px, py = int(math.floor(cx + 6.6 * math.cos(a))), int(math.floor(cy + 0.5 + 6.6 * math.sin(a)))
        if px <= 255:
            post(cv, px, py, ca['canopy_z'] + 1, g - 1, C['metal'], 'prop')
    for k in range(4):                 # carousel animals: legs, body, head and a pole up to the canopy
        a = k * math.pi / 2 + math.pi / 4
        px, py = int(math.floor(cx + 4.2 * math.cos(a))), int(math.floor(cy + 0.5 + 4.2 * math.sin(a)))
        if px <= 255:
            py0 = py - 1
            cv.box(px, px, py0, py0, g - 3, g - 2, C['figure'], 'animal')               # hind leg
            cv.box(px, px, py0 + 2, py0 + 2, g - 3, g - 2, C['figure'], 'animal')       # fore leg
            cv.box(px, px, py0, py0 + 2, g - 4, g - 4, C['figure'], 'animal')           # body
            cv.box(px, px, py0 + 2, py0 + 3, g - 6, g - 5, C['figure'], 'animal')       # neck + head
            cv.box(px, px, py0 + 1, py0 + 1, ca['canopy_z'] + 1, g - 5, C['metal'], 'prop')   # pole
    cv.interiors.append(['carousel', cx - 5, cy, g - 1])

    # ice rink: ice at floor level, low kerb with gaps
    rx0, rx1, ry0, ry1 = S['rink']['box']
    cv.box(rx0, 255, ry0, ry1, g, g, C['ice'], 'ice')
    for x in range(rx0, 256):
        for y in (ry0, ry1):
            if (x // 4) % 2 == 0:
                cv.set(x, y, g - 1, C['stone'], 'prop')
    for y in range(ry0, ry1 + 1):
        if (y // 4) % 2 == 0:
            cv.set(rx0, y, g - 1, C['stone'], 'prop')

    # sleigh workshop: open floor plan, wide doors, sleigh, workbench
    wk = S['workshop']
    x0, x1, y0, y1 = wk['box']
    structures.building(cv, x0, x1, y0, y1, g, storeys=1, storey_h=wk['storey_h'], doors=(), wall=C['wall'],
                        name='sleigh workshop', furnish=False)
    cv.carve(252, 255, y0, y0, g - 6, g - 1)
    cv.carve(252, 255, y1, y1, g - 6, g - 1)
    cv.carve(x0, x0, (y0 + y1) // 2 - 3, (y0 + y1) // 2 + 3, g - 6, g - 1)
    sy = (y0 + y1) // 2
    cv.box(246, 251, sy - 2, sy - 2, g - 1, g - 1, C['metal'], 'prop')                 # runners
    cv.box(246, 251, sy + 2, sy + 2, g - 1, g - 1, C['metal'], 'prop')
    cv.box(246, 251, sy - 2, sy + 2, g - 3, g - 2, C['soldier'], 'prop')               # sleigh body
    cv.box(246, 246, sy - 2, sy + 2, g - 5, g - 4, C['soldier'], 'prop')               # backrest
    cv.box(x0 + 2, x0 + 5, y1 - 3, y1 - 2, g - 2, g - 1, C['furn'], 'furniture')       # workbench
    cv.box(x0 + 2, x0 + 3, y0 + 2, y0 + 3, g - 2, g - 1, C['prop'], 'prop')            # parts crate

    # covered bridge over the creek valley (deck z 52) between the earth abutments
    bd = S['bridge']
    bx0 = bd['x'][0]
    by0, by1 = bd['y']
    dz = bd['deck_z']
    cv.box(bx0, 255, by0, by1, dz, dz, C['timber'], 'building')
    cv.box(bx0, bx0, by0, by1, bd['roof_z'] + 1, dz - 1, C['timber'], 'building')
    cv.box(bx0 - 1, 255, by0 - 1, by1 + 1, bd['roof_z'], bd['roof_z'], C['roof'], 'roof')
    for y in range(by0 + 4, by1 - 2, 6):
        cv.carve(bx0, bx0, y, y + 1, dz - 4, dz - 3)
    cv.interiors.append(['covered bridge', bx0 + 4, (by0 + by1) // 2, dz])

    # sledding hill: sleds on the run
    for (x, y) in ((246, 470), (250, 484), (247, 494)):
        z = int(cv.H[x, y])
        cv.box(x, x + 1, y, y + 2, z - 1, z - 1, C['prop'], 'prop')


# =============================================================================================== underground

def tunnel_floor_paint(cv, x0, x1, y0, y1, fz):
    cv.box(x0, x1, y0, y1, fz, fz, C['mine_floor'], 'mine')


def build_underground(cv, S=SPEC):
    fz = S['z']['underground_floor']
    ta0, ta1 = S['z']['tunnel_air']
    ca0, ca1 = S['z']['chamber_air']
    for name, (x0, x1, y0, y1) in S['tunnels']:
        cv.carve(x0, x1, y0, y1, ta0, ta1)
        tunnel_floor_paint(cv, x0, x1, y0, y1, fz)
        L = max(x1 - x0, y1 - y0)
        k = max(1, L // 60)
        for i in range(k + 1):                               # record points along every segment
            t = (i + 0.5) / (k + 1)
            px, py = int(round(x0 + (x1 - x0) * t)), int(round(y0 + (y1 - y0) * t))
            cv.interiors.append([f'tunnel {name} {i}', px, py, fz])
    for name, (x0, x1, y0, y1) in S['chambers']:
        cv.carve(x0, x1, y0, y1, ca0, ca1)
        tunnel_floor_paint(cv, x0, x1, y0, y1, fz)
        cv.box(x0 + 2, x0 + 4, y0 + 2, y0 + 3, fz - 2, fz - 1, C['metal'], 'prop')        # mine cart
        cv.box(x1 - 3, x1 - 2, y1 - 3, y1 - 2, fz - 3, fz - 1, C['ice'], 'prop')          # crystal cluster
        cv.box(x1 - 6, x1 - 5, y0 + 2, y0 + 2, fz - 2, fz - 1, C['prop'], 'prop')         # crate
        cv.interiors.append([name, (x0 + x1) // 2, (y0 + y1) // 2, fz])
    # house cellar + stair up into the cellar house (floor 49)
    x0, x1, y0, y1 = S['house_cellar']
    cv.carve(x0, x1, y0, y1, ca0, ca1)
    tunnel_floor_paint(cv, x0, x1, y0, y1, fz)
    g = S['z']['village']
    straight_stair(cv, x0 + 2, y0 + 2, y0 + 3, fz, fz - g, 1, C['stair'])
    cv.interiors.append(['house cellar', x0 + 4, y1 - 3, fz])
    # mine adit: stair rising +x from the trunk tunnel to the village surface, timber portal
    ad = S['adit']
    ay0, ay1 = ad['y']
    top = straight_stair(cv, ad['x0'], ay0, ay1, fz, fz - g, 1, C['stair'])
    px = top[0] - 1
    post(cv, px, ay0 - 1, g - 5, g)
    post(cv, px, ay1 + 1, g - 5, g)
    cv.box(px, px, ay0 - 1, ay1 + 1, g - 5, g - 5, C['timber'], 'timber')
    cv.interiors.append(['mine adit', ad['x0'] + 2, ay0 + 1, fz - 2])
    # market hatches: stairs from the laterals up into the hatch stalls (floor 50)
    gv = S['z']['valley']
    hn = S['hatch_n']
    straight_stair(cv, hn['y0'], hn['x'][0], hn['x'][1], fz, fz - gv, 1, C['stair'], along='y')
    hs = S['hatch_s']
    straight_stair(cv, hs['y0'], hs['x'][0], hs['x'][1], fz, fz - gv, -1, C['stair'], along='y')
    cv.interiors += [['hatch stair N', hn['x'][0] + 1, hn['y0'] + 2, fz - 3],
                     ['hatch stair S', hs['x'][0] + 1, hs['y0'] - 2, fz - 3]]
    # tavern cellar + stair up to the tavern ground floor
    cx0, cx1, cy0, cy1 = S['tavern']['cellar']
    cv.carve(cx0, cx1, cy0, cy1, ca0, ca1)
    tunnel_floor_paint(cv, cx0, cx1, cy0, cy1, fz)
    straight_stair(cv, cy1 - 3, 248, 250, fz, fz - gv, -1, C['stair'], along='y')
    cv.box(cx0 + 1, cx0 + 2, cy0 + 1, cy0 + 4, fz - 2, fz - 1, C['trunk'], 'prop')       # casks
    cv.interiors.append(['tavern cellar', cx0 + 4, cy0 + 8, fz])


# =============================================================================================== masks + scatter

KEEP_SPAWN, KEEP_ANCHOR, KEEP_FRONT, KEEP_UNDER, KEEP_LANE, KEEP_ENTRY, KEEP_MISC = 1, 2, 4, 8, 16, 32, 64


def set_masks(cv, geo, S=SPEC):
    sp = S['spawn']
    (bx, by), h, m = sp['base'], sp['half'], sp['margin']
    cv.no_prop(bx - h - m, bx + h + m, by - h - m, by + h + m, KEEP_SPAWN)
    a = S['anchor']
    cv.no_prop(a['x'][0] - 2, a['x'][1] + 2, a['y'][0] - 2, a['y'][1] + 2, KEEP_ANCHOR)
    f = S['front']
    cv.no_prop(f['x'][0], f['x'][1], f['y'][0], f['y'][1], KEEP_FRONT)
    u = S['under_platform']
    cv.no_prop(u['x'][0], u['x'][1], u['y'][0], u['y'][1], KEEP_UNDER)
    cv.keep[geo['lanes']] |= KEEP_LANE
    hn, hs = S['hatch_stalls']['north'], S['hatch_stalls']['south']
    for (x0, x1, y0, y1) in ((50, 64, 204, 214), (hn[0] - 1, hn[1] + 1, hn[2] - 3, hn[3] + 1),
                             (hs[0] - 1, hs[1] + 1, hs[2] - 1, hs[3] + 3)):
        cv.no_prop(x0, x1, y0, y1, KEEP_ENTRY)
    gh = S['gatehouse']
    rw = S['railway']
    ml = geo['mill']['box']
    for (x0, x1, y0, y1) in ((gh['x'][0] - 3, gh['x'][1] + 3, gh['statue_y'][0] - 4, 512 - gh['statue_y'][0] + 4),
                             (244, 255, 396, 463), (242, 255, 462, 500), (rw['x'][0], 255, 75, 93),
                             rw['station_apron'], (242, 255, 104, 124), (ml[0] - 2, ml[1] + 2, ml[2] - 6, ml[3] + 4),
                             (512 - S['tag']['strip'][1], 512 - S['tag']['strip'][0],
                              S['tag']['strip'][2], S['tag']['strip'][3])):
        cv.no_prop(x0, x1, y0, y1, KEEP_MISC)


PAD_KINDS = ['snowman', 'ice sculpture', 'sled stack', 'snow fort', 'lantern ring', 'snowman family']


def _try_pine(cv, rng, x, y, margin=3):
    r = int(rng.integers(2, 5))
    h = int(rng.integers(9, 17))
    if not (r + margin + 1 <= x <= 250 - r - margin and r + margin <= y <= 511 - r - margin):
        return None
    Hs = cv.H[x - r - 2:x + r + 3, y - r - 2:y + r + 3]
    if Hs.max() > 61 or Hs.max() - Hs.min() > 5:
        return None
    if not free_for_prop(cv, x - r - margin, x + r + margin, y - r - margin, y + r + margin):
        return None
    pine(cv, x, y, r, h)
    return (x, y, r, h)


def _try_outcrop(cv, rng, x, y):
    rx, ry, rz = float(rng.uniform(2, 5)), float(rng.uniform(2, 4.5)), float(rng.uniform(1.5, 3.5))
    R = int(math.ceil(max(rx, ry)))
    if not (R + 4 <= x <= 250 - R and R + 4 <= y <= 507 - R):
        return None
    Hs = cv.H[x - R:x + R + 1, y - R:y + R + 1]
    if Hs.max() > 60 or Hs.max() - Hs.min() > 4:
        return None
    if not free_for_prop(cv, x - R - 3, x + R + 3, y - R - 3, y + R + 3):
        return None
    outcrop(cv, x, y, rx, ry, rz)
    return (x, y, round(rx, 1), round(ry, 1), round(rz, 1))


_NO_PAD_BOX = None                                   # v1.2: (x0, x1, y0, y1) where no pad may go (set per build)


def _in_no_pad(x0, x1, y0, y1):
    if _NO_PAD_BOX is None:
        return False
    a, b, c, d = _NO_PAD_BOX
    return not (x1 < a or x0 > b or y1 < c or y0 > d)


def _try_pad(cv, rng, x, y, pads, kinds=PAD_KINDS):
    w, d = (5, 5) if rng.random() < 0.5 else ((7, 5) if rng.random() < 0.5 else (5, 7))
    if x + w > 250 or _in_no_pad(x, x + w - 1, y, y + d - 1):
        return None
    Hs = cv.H[x:x + w, y:y + d]
    if Hs.max() > 60 or Hs.max() != Hs.min():
        return None
    if not free_for_prop(cv, x - 3, x + w + 2, y - 3, y + d + 2):
        return None
    feature_pad(cv, x, y, w, d, kinds[int(rng.integers(len(kinds)))], pads)
    return True


def _try_small(cv, rng, x, y, kind):
    if x > 248:
        return None
    if kind == 'crates':
        if free_for_prop(cv, x - 3, x + 5, y - 3, y + 5):
            crate_stack(cv, x, y)
            return True
    elif kind == 'bench':
        along = 'x' if rng.random() < 0.5 else 'y'
        bw, bd = (5, 2) if along == 'x' else (2, 5)
        if free_for_prop(cv, x - 3, x + bw + 2, y - 3, y + bd + 2):
            bench(cv, x, y, along)
            return True
    elif kind == 'lantern':
        if free_for_prop(cv, x - 3, x + 3, y - 3, y + 3):
            lantern(cv, x, y, 6)
            return True
    elif kind == 'barrels':
        if free_for_prop(cv, x - 3, x + 5, y - 3, y + 4):
            gbox(cv, x, x + 1, y, y + 1, 3, C['trunk'])
            gbox(cv, x + 2, x + 3, y, y + 1, 2, C['trunk'])
            return True
    elif kind == 'woodpile':
        if free_for_prop(cv, x - 3, x + 6, y - 3, y + 4):
            gbox(cv, x, x + 3, y, y + 1, 2, C['trunk'])
            return True
    return None


def scatter(cv, geo, S=SPEC, veg_seed=None):
    """Clutter on jittered grids (nothing lines up in rows; every piece keeps >= 3 voxels from anything standing).
    Fixed by the LAYOUT seed: rock outcrops and feature pads on the fields, plaza props and pads, village props.
    Placed by the per-build VEG seed (owner rule: vegetation placement is non-deterministic, seed saved): every pine
    stand-in - field groves (centres, member count, member positions), lone pines, village pines and ring pines.
    The fixed pass runs first, so trees only fill the space the fixed pieces leave."""
    sc = S['scatter']
    seed = S['layout_seed']
    rng = noise.rng('scatter', seed)
    vseed = seed if veg_seed is None else int(veg_seed)
    vrng = noise.rng('veg_scatter', vseed)
    pads, pines, rocks, small = [], [], [], 0
    vil = _box(*[S['village'][k] for k in ('x', 'y')])
    plaza = geo['plaza'] & ~geo['lanes']

    def grid(spacing, jitter, tag, sd=seed):
        r = noise.rng(tag, sd)
        for gx in range(6, 252, spacing):
            for gy in range(6, 506, spacing):
                yield (gx + int(r.integers(-jitter, jitter + 1)), gy + int(r.integers(-jitter, jitter + 1)))

    # fields (outside plaza, lanes and villages)
    for (x, y) in grid(sc['field_spacing'], sc['field_jitter'], 'grid_field'):
        if not (0 <= x <= 250 and 0 <= y <= 511) or plaza[x, y] or geo['lanes'][x, y] or vil[x, y]:
            continue
        if not (44 <= cv.H[x, y] <= 60):
            continue
        t = rng.random()
        if t < 0.5:
            pass                                        # grove slot: trees come from the veg pass below
        elif t < 0.75:
            o = _try_outcrop(cv, rng, x, y)
            if o:
                rocks.append(o)
        elif t < 0.9:
            _try_pad(cv, rng, x, y, pads)
        else:
            o = _try_outcrop(cv, rng, x + 8, y + 3)
            if o:
                rocks.append(o)
    # plaza clutter
    kinds = ['crates', 'bench', 'lantern', 'barrels', 'pad', 'crates', 'bench']
    for (x, y) in grid(sc['plaza_spacing'], sc['plaza_jitter'], 'grid_plaza'):
        if not (0 <= x <= 248 and 0 <= y <= 511) or not plaza[x, y]:
            continue
        k = kinds[int(rng.integers(len(kinds)))]
        if k == 'pad':
            _try_pad(cv, rng, x, y, pads, ['ice sculpture', 'snowman', 'present pile', 'lantern ring'])
        elif _try_small(cv, rng, x, y, k):
            small += 1
    # village clutter (spawn margin is kept clear by its keep flag)
    vk = ['woodpile', 'crates', 'pine', 'rock', 'pad', 'barrels']
    for (x, y) in grid(sc['village_spacing'], sc['village_jitter'], 'grid_village'):
        if not (0 <= x <= 248 and 0 <= y <= 511) or not vil[x, y]:
            continue
        k = vk[int(rng.integers(len(vk)))]
        if k == 'pine':
            pass                                        # village pines come from the veg pass below
        elif k == 'rock':
            o = _try_outcrop(cv, rng, x, y)
            if o:
                rocks.append(o)
        elif k == 'pad':
            _try_pad(cv, rng, x, y, pads, ['snowman', 'snowman family', 'sled stack'])
        elif _try_small(cv, rng, x, y, k):
            small += 1
    # ---------------------------------------------------------------- veg pass (per-build OS seed)
    R = sc['grove_radius']
    for (x, y) in grid(sc['field_spacing'], sc['field_jitter'] + 3, 'grid_field_veg', vseed):
        if not (0 <= x <= 250 and 0 <= y <= 511) or plaza[x, y] or geo['lanes'][x, y] or vil[x, y]:
            continue
        if not (44 <= cv.H[x, y] <= 60):
            continue
        t = vrng.random()
        if t < 0.55:                                    # a grove: centre jittered, 3-6 members
            n = int(vrng.integers(*sc['grove_n'])) + 1
            got = 0
            for _ in range(n * 4):
                p = _try_pine(cv, vrng, x + int(vrng.integers(-R, R + 1)), y + int(vrng.integers(-R, R + 1)))
                if p:
                    pines.append(p)
                    got += 1
                    if got >= n:
                        break
        elif t < 0.68:                                  # a lone tree in a clearing
            p = _try_pine(cv, vrng, x, y)
            if p:
                pines.append(p)
    for (x, y) in grid(sc['village_spacing'], sc['village_jitter'], 'grid_village_veg', vseed):
        if not (0 <= x <= 248 and 0 <= y <= 511) or not vil[x, y] or vrng.random() > 0.2:
            continue
        p = _try_pine(cv, vrng, x, y)
        if p:
            pines.append(p)
    # dark pines on the mountain ring: stand-ins on foothills, terraces and gentle faces (art paints them)
    ring_n = 0
    for (x, y) in grid(13, 5, 'grid_ring', vseed):
        if not (3 <= x <= 248 and 3 <= y <= 508) or not (16 <= cv.H[x, y] <= 46) or vil[x, y]:
            continue
        loc = cv.H[x - 1:x + 2, y - 1:y + 2]
        if loc.max() - loc.min() > 3 or vrng.random() < 0.25:
            continue
        r = int(vrng.integers(2, 4))
        h = min(int(vrng.integers(9, 15)), int(cv.H[x, y]) - 8)         # tip stays at z >= 8
        if h >= 6 and free_for_prop(cv, x - r - 2, x + r + 2, y - r - 2, y + r + 2):
            pine(cv, x, y, r, h)
            pines.append((x, y, r, h))
            ring_n += 1
    return {'pines': len(pines), 'ring_pines': ring_n, 'outcrops': len(rocks), 'small_props': small, 'feature_pads': pads,
            'pine_list': pines, 'veg_seed': vseed}


def clear_pine_traps(cv, pines, S=SPEC, rounds=3):
    """Seeded pines can close a pocket against a terrace step or a wall. Run the kit's trap model (same rules as
    babel_checks: safe graph from both spawns, walk back to the anchor set, terrain band +-3) on a mirrored copy and
    delete every pine stand-in within reach of a trap cell; repeat until none is left. Returns pines removed."""
    from aosmap.kit.babel_checks import Nav
    from aosmap.kit.params import BABEL_DEFAULT as P
    vid = cv.material('veg')
    removed = 0
    for _ in range(rounds):
        solid = cv.solid.copy()
        solid[257:] = cv.solid[255:0:-1]
        solid[256] = cv.solid[255]
        Hm = cv.H.astype(int).copy()
        Hm[257:] = cv.H[255:0:-1]
        Hm[256] = cv.H[255]
        nav = Nav(solid)
        h = P['spawn_half']
        src = np.concatenate([nav.nodes_in(b[0] - h, b[0] + h, b[1] - h, b[1] + h, 0, 62) for b in P['bases']])
        fwd = np.isfinite(nav.dist_from(src))
        (x0, x1), (y0, y1) = P['platform_x'], P['platform_y']
        anc = nav.nodes_in(min(b[0] for b in P['bases']) - h, max(b[0] for b in P['bases']) + h, y0 - 40, y1 + 40,
                           0, 62)[::5]
        back = np.isfinite(nav.dist_from(anc, reverse=True))
        p = nav.xyz
        landish = np.abs(p[:, 2] - Hm[p[:, 0], p[:, 1]]) <= 3
        tp = p[landish & fwd & ~back]
        if not len(tp):
            break
        tx = np.minimum(tp[:, 0], 512 - tp[:, 0])
        ty = tp[:, 1]
        drop = [q for q in pines if np.any((np.abs(tx - q[0]) <= q[2] + 4) & (np.abs(ty - q[1]) <= q[2] + 4))]
        if not drop:
            break
        for (x, y, r, hh) in drop:
            sl = (slice(x - r - 2, x + r + 3), slice(y - r - 2, y + r + 3))
            m = cv.mat[sl] == vid
            cv.solid[sl][m] = False
            cv.mat[sl][m] = 0
            pines.remove((x, y, r, hh))
            removed += 1
    return removed


def fill_nooks(cv, rounds=10):
    """Terrain-top columns more than 1 below all 4 neighbouring tops (a nook left between a terrace step and a pine
    stand-in) are raised with rock to the lowest neighbour + 1, so nobody can drop in and get stuck."""
    n = 0
    for _ in range(rounds):
        top = np.argmax(cv.solid, axis=2)
        nb = np.stack([np.roll(top, 1, 0), np.roll(top, -1, 0), np.roll(top, 1, 1), np.roll(top, -1, 1)]).max(0)
        pit = (top > nb + 1) & (top == cv.H) & (cv.H < 62)
        pit[:2] = pit[-2:] = False
        pit[:, :2] = pit[:, -2:] = False
        if not pit.any():
            break
        for x, y in zip(*np.nonzero(pit)):
            z = int(nb[x, y]) + 1
            cv.box(x, x, y, y, z, int(cv.H[x, y]) - 1, C['rock'], 'rock')
            cv.H[x, y] = z
            n += 1
    return n


def break_flats(cv, S=SPEC, target=22, rounds=40):
    """Deterministic pass: while a featureless flat square larger than `target` exists (same metric as fh_checks),
    put a small feature (pad, lantern, crates, bench) near its centre. Lanes may receive a pad or lantern at their
    edge; spawn margins, anchors, under-platform, front, entrances and misc keep zones never do."""
    import fh_checks
    rng = noise.rng('break_flats', S['layout_seed'])
    placed = []
    mask = 0xFF & ~KEEP_LANE
    kinds = ['pad', 'lantern', 'crates', 'bench', 'barrels']
    pads = []
    for _ in range(rounds):
        # measure the map as it will be after the mirror (patches across the axis count at full width), then
        # place features on the west part of each patch
        okw = fh_checks.featureless_ok_mask(cv.solid, cv.H, S)
        ok = okw.copy()
        ok[257:] = okw[255:0:-1]
        ok[256] = okw[255]
        Hm = cv.H.copy()
        Hm[257:] = cv.H[255:0:-1]
        Hm[256] = cv.H[255]
        best, where, tops = fh_checks.largest_flat_squares(Hm, ok, min_report=target + 1, n_report=12)
        if best <= target:
            break
        done = 0
        for v, x, y in tops:
            cx, cy = x - v // 2, y - v // 2
            xa, xb = x - v + 2, min(x, 248)
            cand = sorted(((px, py) for px in range(xa, xb, 2) for py in range(y - v + 2, y, 2)),
                          key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2)
            for _try, (px, py) in enumerate(cand):
                k = kinds[(_try + int(rng.integers(len(kinds)))) % len(kinds)]
                if px > 247 or px < 4 or py < 4 or py > 506:
                    continue
                box = {'pad': (px - 3, px + 7, py - 3, py + 7), 'lantern': (px - 3, px + 3, py - 3, py + 3),
                       'crates': (px - 3, px + 5, py - 3, py + 5), 'bench': (px - 3, px + 7, py - 3, py + 4),
                       'barrels': (px - 3, px + 6, py - 3, py + 4)}[k]
                if not free_for_prop(cv, *box, keep_mask=mask):
                    continue
                if k == 'pad' and _in_no_pad(px, px + 4, py, py + 4):
                    continue
                if k == 'pad':
                    Hs = cv.H[px:px + 5, py:py + 5]
                    if Hs.max() != Hs.min() or Hs.max() > 60:
                        continue
                    feature_pad(cv, px, py, 5, 5, ['snowman', 'ice sculpture', 'present pile'][int(rng.integers(3))],
                                pads)
                elif k == 'lantern':
                    lantern(cv, px, py, 6)
                elif k == 'crates':
                    crate_stack(cv, px, py)
                elif k == 'bench':
                    bench(cv, px, py, 'x')
                else:
                    gbox(cv, px, px + 1, py, py + 1, 3, C['trunk'])
                    gbox(cv, px + 2, px + 3, py, py + 1, 2, C['trunk'])
                placed.append((k, px, py))
                done += 1
                break
        if not done:
            break
    return {'placed': placed, 'feature_pads': pads, 'largest_side_after': int(best)}


# =============================================================================================== top level

def build_west(S=SPEC, veg_seed=None):
    """Everything except the mirror and the train. veg_seed places the pine stand-ins. Returns (canvas, report)."""
    global _NO_PAD_BOX
    _NO_PAD_BOX = S['v12_no_pad_box'] if S.get('zones') else None
    cv = Canvas(S['name'])
    H, region, geo = terrain(S)
    paint_terrain(cv, H, region)
    set_masks(cv, geo, S)
    build_chapel(cv, S)
    build_chapel_roof(cv, S)
    build_post_office(cv, S)
    build_village(cv, S)
    if S['gatehouse'].get('variant', 'full') == 'full':
        build_gatehouse(cv, S)                          # the released gatehouse, unchanged
    else:
        build_gate_variant(cv, S, S['gatehouse']['variant'])
    if S['gatehouse'].get('flank_cover'):
        build_flank_cover(cv, S)
    pinned = build_zone_pieces(cv, S) if S.get('zones') else []
    build_front(cv, S)
    market_boxes = build_market(cv, S)
    build_axis(cv, S)
    build_mill(cv, geo, S)
    rail = build_railway(cv, S)
    build_underground(cv, S)
    sc = scatter(cv, geo, S, veg_seed)
    if S['gatehouse'].get('variant') == 'arch':      # snowman pad on the old north-tower ground (mirrored south)
        feature_pad(cv, 146, 214, 5, 5, 'snowman', sc['feature_pads'])
    sc['nooks_filled'] = fill_nooks(cv)                 # after the seeded scatter: 0 traps for any seed
    sc['trap_pines_removed'] = clear_pine_traps(cv, sc['pine_list'], S)
    sc['pine_list'] += pinned                          # layout-pinned cover firs (never removed by the trap pass)
    sc['pinned_firs'] = len(pinned)
    bf = break_flats(cv, S)
    sc['feature_pads'] = sc['feature_pads'] + bf['feature_pads']
    sc['break_flats'] = {'placed': len(bf['placed']), 'largest_side_after_west': bf['largest_side_after']}
    return cv, {'scatter': sc, 'market_boxes': market_boxes, 'mill': geo['mill'], 'rail_tunnel': rail}


# =============================================================================================== train (after mirror)

def build_train(cv, S=SPEC):
    """Stopped train on the axis: 3 open carriages + locomotive at the east end. Asymmetric: added after the mirror."""
    tr = S['train']
    x0, x1, y0, y1 = tr['box']
    cz = tr['chassis_z']
    rz = S['railway']['rail_z']
    for y in (y0, y1):                                   # make sure the rails run under the whole train
        for x in range(x0, x1 + 1):
            cv.set(x, y, rz, C['rail'], 'rail')
    cars = [(x0, x0 + 12), (x0 + 14, x0 + 26), (x0 + 28, x0 + 40)]
    for i, (a, b) in enumerate(cars):
        cv.box(a, b, y0, y1, cz, cz, C['timber'], 'train')                       # chassis / floor
        cv.box(a, b, y0, y0, cz - 2, cz - 1, C['soldier'], 'train')              # sides
        cv.box(a, b, y1, y1, cz - 2, cz - 1, C['soldier'], 'train')
        cv.box(a, a, y0, y1, cz - 2, cz - 1, C['soldier'], 'train')
        cv.box(b, b, y0, y1, cz - 2, cz - 1, C['soldier'], 'train')
        m = (a + b) // 2
        cv.carve(m - 1, m, y0, y0, cz - 2, cz - 1)                                 # side doors
        cv.carve(m - 1, m, y1, y1, cz - 2, cz - 1)
        cv.box(m - 1, m, y0 - 1, y0 - 1, cz + 1, cz + 1, C['timber'], 'train')     # boarding steps
        cv.box(m - 1, m, y1 + 1, y1 + 1, cz + 1, cz + 1, C['timber'], 'train')
        cv.box(a + 2, a + 4, y0 + 1, y0 + 2, cz - 2, cz - 1, C['prop'], 'prop')     # presents cargo
        cv.box(a + 9, a + 11, y1 - 1, y1 - 1, cz - 1, cz - 1, C['furn'], 'furniture')  # bench
        cv.interiors.append([f'train carriage {i}', m + 3, (y0 + y1) // 2, cz])
    a, b = x0 + 42, x1
    cv.box(a, b, y0, y1, cz, cz, C['metal'], 'train')
    cv.box(a + 1, b - 7, y0 + 1, y1 - 1, cz - 4, cz - 1, (70, 70, 80), 'train')    # boiler
    cv.box(a + 3, a + 4, (y0 + y1) // 2, (y0 + y1) // 2, cz - 7, cz - 5, (70, 70, 80), 'train')   # chimney
    c0 = b - 5
    cv.box(c0, b, y0, y1, cz - 6, cz - 1, C['soldier'], 'train')                  # cab
    cv.carve(c0 + 1, b - 1, y0 + 1, y1 - 1, cz - 5, cz - 1)
    cv.carve(c0 + 2, c0 + 3, y0, y0, cz - 4, cz - 1)
    cv.carve(c0 + 2, c0 + 3, y1, y1, cz - 4, cz - 1)
    cv.box(c0 + 2, c0 + 3, y0 - 1, y0 - 1, cz + 1, cz + 1, C['timber'], 'train')
    cv.box(c0 + 2, c0 + 3, y1 + 1, y1 + 1, cz + 1, cz + 1, C['timber'], 'train')
    cv.interiors.append(['locomotive cab', c0 + 3, (y0 + y1) // 2, cz])
    return [x0, x1, y0 - 1, y1 + 1]
