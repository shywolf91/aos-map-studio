"""Frostbell Hollow graybox: gameplay geometry only (flat function colours per material, no art pass).

Order: terrain heights -> fill_terrain -> structures (west half + axis west halves) -> underground -> props and
stand-in pines -> [fh_main: orphan report -> mirror x512 -> stopped train (the one asymmetric piece)].
Every number comes from fh_spec.SPEC. Every room, floor, tunnel segment and chamber is recorded in cv.interiors.
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from aosmap.kit import Canvas, noise, structures  # noqa: E402
from aosmap.kit.structures import straight_stair  # noqa: E402

from fh_spec import SPEC  # noqa: E402

# flat graybox colours per material (luma >= 40, max channel <= 212)
C = {
    'snow': (188, 192, 200), 'cobble': (132, 128, 124), 'rock': (104, 102, 110), 'ice': (150, 194, 208),
    'water': (60, 90, 120), 'dirt': (112, 96, 80), 'ballast': (98, 94, 92), 'mine_floor': (120, 104, 84),
    'wall': (178, 162, 134), 'stone': (150, 146, 140), 'timber': (132, 98, 66), 'roof': (120, 70, 60),
    'floor': (122, 94, 68), 'stair': (154, 124, 92), 'rail': (86, 86, 94), 'prop': (178, 126, 66),
    'veg': (54, 98, 64), 'trunk': (98, 74, 54), 'furn': (102, 80, 58), 'metal': (112, 114, 124),
    'soldier': (168, 70, 64), 'figure': (170, 150, 120), 'hay': (196, 170, 96),
}
GROUND_KEYS = ['snow', 'cobble', 'rock', 'ice', 'water', 'ballast']   # region codes 0..5 for the top voxel


# =============================================================================================== terrain

def terrain(S=SPEC):
    """Height map H[x, y] (floor z) and top-surface region codes. West half is authoritative (mirrored later)."""
    seed = S['layout_seed']
    Z = S['z']
    X, Y = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    Xw = np.minimum(X, 512 - X)

    # valley floor 50 with +-1 gentle noise
    n = noise.fbm2((512, 512), 32, 3, 'valley', seed)
    H = np.where(n > 0.64, Z['valley'] - 1, np.where(n < 0.36, Z['valley'] + 1, Z['valley'])).astype(int)
    region = np.zeros((512, 512), np.int8)

    def box(xr, yr):
        m = np.zeros((512, 512), bool)
        m[xr[0]:xr[1] + 1, yr[0]:yr[1] + 1] = True
        return m

    # village 48-49 (gentle mounds), spawn square inside it
    vil = box(S['village']['x'], S['village']['y'])
    mound = noise.fbm2((512, 512), 12, 2, 'mounds', seed)
    H[vil] = np.where(mound[vil] > 0.6, Z['village_mound'], Z['village'])

    # railway strip z 49 (embankment), station platform included
    rw = S['railway']
    rail = box(rw['x'], rw['y_strip'])
    H[rail] = Z['rail']
    region[box(rw['x'], rw['embankment_y'])] = 5

    # flat cobbled market, front, anchors, under-platform, gatehouse floor (z 50)
    mk = box(S['market_cobble']['x'], S['market_cobble']['y'])
    H[mk] = Z['valley']
    region[mk] = 1
    for b in (S['front'], S['anchor'], S['under_platform']):
        H[box(b['x'], b['y'])] = Z['valley']
    region[box(S['front']['x'], S['front']['y'])] = 0
    gh = S['gatehouse']
    H[box((gh['x'][0] - 1, gh['x'][1]), (gh['statue_y'][0] - 2, 512 - gh['statue_y'][0] + 2))] = gh['floor_z']
    region[box(gh['x'], gh['y'])] = 1
    # nativity yard flat
    H[box((240, 255), (104, 126))] = Z['valley']

    # building pads (village 49) so floors are flat
    pads = [S['post_office']['box']] + [h['box'] for h in S['houses']]
    ch = S['chapel']
    pads += [(ch['tower'][0], ch['nave'][1], ch['nave'][2], ch['nave'][3])]
    for (x0, x1, y0, y1) in pads:
        H[box((x0 - 1, x1 + 1), (y0 - 1, y1 + 1))] = Z['village']

    # creek valley (south flank): water 63, ice shelves 62, banks 61 -> 50
    cr = S['creek']
    yc = cr['y_c'] + cr['wiggle'] * np.sin((256 - X) * math.pi / 120.0) ** 2
    ady = np.abs(Y - yc)
    bank = np.rint(Z['bank_low'] - (ady - cr['bank_from']) * (Z['bank_low'] - Z['valley']) / cr['bank_w'])
    cz = np.where(ady <= cr['water_half'], Z['water'],
                  np.where(ady <= cr['shelf_half'], Z['ice_shelf'],
                           np.where(ady <= cr['bank_from'], Z['bank_low'], bank))).astype(int)
    cm = ady <= cr['bank_from'] + cr['bank_w']
    H[cm] = np.maximum(H[cm], cz[cm])
    region[cm & (cz == Z['ice_shelf'])] = 3
    region[cm & (cz == Z['water'])] = 4

    # mill pad + front terrace (z 52) on the north bank
    ml = S['mill']
    mx0, mx1, my0, my1 = ml['box']
    H[box((mx0 - 2, mx1 + 2), (my0 - 4, my1))] = ml['floor']

    # bridge abutments (z 52) and the sledding hill that ends on the south abutment
    bd = S['bridge']
    H[box((bd['x'][0], 255), (398, bd['y'][0] - 1))] = bd['deck_z']
    H[box((bd['x'][0], 255), (bd['y'][1] + 1, 461))] = bd['deck_z']
    sh = S['sled_hill']
    shm = box(sh['x'], sh['y'])
    sz = np.rint(sh['z_bottom'] - (Y - sh['y'][0]) * (sh['z_bottom'] - sh['z_top']) / (sh['y'][1] - sh['y'][0]))
    H[shm] = np.minimum(H[shm], sz[shm].astype(int))

    # ridge spur across the railway (north flank), tunnel carved later
    sp = S['spur']
    cxs = (sp['x'][0] + sp['x'][1]) / 2.0
    dxs = np.abs(X + 0.5 - (cxs + 0.5))
    hx = np.where(dxs <= sp['core_half'], sp['top_z'],
                  sp['top_z'] + (dxs - sp['core_half']) * (Z['rail'] - sp['top_z']) / (13 - sp['core_half']))
    t = np.clip((Y - sp['tip_from']) / float(sp['y'][1] - sp['tip_from']), 0, 1)
    hs = hx + t * (Z['valley'] - hx)
    spm = (dxs <= 13) & (Y >= sp['y'][0]) & (Y <= sp['y'][1])
    H[spm] = np.minimum(H[spm], np.rint(hs[spm]).astype(int))

    # mountain ring (higher terrain wins): d = distance to the map edge on the west half
    d = np.minimum(np.minimum(Xw, Y), 511 - Y).astype(float)
    dn = d + (noise.fbm2((512, 512), 24, 3, 'ringwarp', seed) - 0.5) * 10
    rg = S['ring']
    pk = Z['ring_peak'][0] + (Z['ring_peak'][1] - Z['ring_peak'][0]) * noise.fbm2((512, 512), 16, 2, 'peaks', seed)
    face_top = 42
    ringH = np.where(dn <= rg['peak_band'], pk,
                     np.where(dn <= rg['rock_to'],
                              pk + (face_top - pk) * (dn - rg['peak_band']) / (rg['rock_to'] - rg['peak_band']),
                              face_top + (Z['ring_foot'] - face_top) * (dn - rg['rock_to']) / (rg['foot'] - rg['rock_to'])))
    ringH = np.rint(ringH).astype(int)
    rm = dn <= rg['foot']
    H[rm] = np.minimum(H[rm], ringH[rm])
    H = np.maximum(H, Z['min_solid_z'] + 1)
    region[(H <= 45) & (region != 1)] = 2
    region[H >= 62] = np.where(H[H >= 62] == 63, 4, 3)
    return H.astype(int), region


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


def ground_at(cv, x, y):
    return int(cv.H[x, y])


def stall(cv, x0, x1, y0, y1, name, front='S', g=50, counter=True):
    """Market stall: 4 corner posts, back wall, roof at g-6 (5 voxels of headroom), counter with an entrance gap."""
    rz = g - 6
    for (x, y) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        post(cv, x, y, rz + 1, g)
    cv.box(x0, x1, y0, y1, rz, rz, C['roof'], 'roof')
    by = y0 if front == 'S' else y1
    fy = y1 if front == 'S' else y0
    cv.box(x0, x1, by, by, rz + 1, g - 1, C['timber'], 'timber')            # back wall
    if counter:
        cx = (x0 + x1) // 2
        cv.box(x0 + 1, cx - 2, fy, fy, g - 1, g - 1, C['furn'], 'furniture')
        cv.box(cx + 2, x1 - 1, fy, fy, g - 1, g - 1, C['furn'], 'furniture')
    cv.interiors.append([name, (x0 + x1) // 2, (y0 + y1) // 2, g])


def crate_stack(cv, x, y, g=50):
    cv.box(x, x + 2, y, y + 2, g - 2, g - 1, C['prop'], 'prop')
    cv.box(x, x + 1, y, y + 1, g - 3, g - 3, C['prop'], 'prop')


def bench(cv, x, y, g=50, length=5, back=True):
    cv.box(x, x + length - 1, y, y, g - 1, g - 1, C['furn'], 'prop')
    if back:
        cv.box(x, x + length - 1, y + 1, y + 1, g - 2, g - 1, C['furn'], 'prop')


def lantern(cv, x, y, g=50, h=6):
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


def free_for_prop(cv, x0, x1, y0, y1):
    """No keep flag and nothing above the terrain in the box."""
    x0, y0 = max(0, x0), max(0, y0)
    if cv.keep[x0:x1 + 1, y0:y1 + 1].any():
        return False
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            if cv.solid[x, y, :cv.H[x, y]].any():
                return False
    return True


# =============================================================================================== village

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


def build_post_office(cv, S=SPEC):
    po = S['post_office']
    x0, x1, y0, y1 = po['box']
    g = S['z']['village']
    structures.building(cv, x0, x1, y0, y1, g, storeys=1, storey_h=6, doors=('S', 'N'), wall=C['wall'],
                        name='post office counter room', furnish=False)
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
    cv.box(mx0, mx1, my0, my1, g - 4, g - 1, C['soldier'], 'prop')


def build_houses(cv, S=SPEC):
    g = S['z']['village']
    for h in S['houses']:
        x0, x1, y0, y1 = h['box']
        structures.building(cv, x0, x1, y0, y1, g, storeys=2, storey_h=5, doors=h['doors'], wall=C['wall'],
                            roof=C['roof'], name=h['name'])


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
    cv.interiors += [['gatehouse north tower', x0 + 2, yA + 1, g], ['gatehouse south tower', x0 + 2, 512 - yA - 1, g],
                     ['gatehouse gallery', x0 + 2, 245, gf], ['gatehouse stair landing', x0 + 2, yA + 9, g - 5]]


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


def build_front(cv, S=SPEC):
    """Front (gatehouse -> anchor): low walk-through props only, two open huts at the band edges, two lanterns."""
    g = S['z']['valley']
    for i, h in enumerate(S['front_huts']):
        hut(cv, *h['box'], h['open'], f'front hut {i}', g)
    P = C['prop']
    cv.box(156, 159, 262, 263, g - 1, g - 1, P, 'prop')                 # sled
    cv.box(190, 193, 250, 251, g - 1, g - 1, P, 'prop')                 # sled
    cv.box(160, 163, 270, 271, g - 2, g - 1, C['trunk'], 'prop')        # firewood
    cv.box(176, 178, 246, 247, g - 2, g - 1, C['hay'], 'prop')          # hay bale
    cv.box(192, 194, 264, 265, g - 2, g - 1, C['hay'], 'prop')          # hay bale
    cv.box(170, 174, 256, 258, g - 2, g - 2, C['timber'], 'prop')       # hand cart bed
    for (wx, wy) in ((171, 256), (173, 256), (171, 258), (173, 258)):
        cv.set(wx, wy, g - 1, C['metal'], 'prop')                       # wheels
    cv.ellipsoid(182.5, 241.5, g - 1, 2, 2, 1.5, C['rock'], 'prop')     # rocks
    cv.ellipsoid(196.5, 270.5, g - 1, 1.5, 2, 1.5, C['rock'], 'prop')
    cv.ellipsoid(158.5, 244.5, g - 1, 2, 2, 2, C['veg'], 'veg')         # low bushes
    cv.ellipsoid(186.5, 258.5, g - 1, 2, 2, 2, C['veg'], 'veg')
    bench(cv, 158, 249, g)
    bench(cv, 180, 266, g)
    lantern(cv, 154, 236, g, 6)
    lantern(cv, 154, 276, g, 6)
    # under the platform: props <= 2 tall
    bench(cv, 220, 246, g)
    bench(cv, 220, 265, g)
    cv.box(236, 237, 252, 253, g - 1, g - 1, P, 'prop')


# =============================================================================================== market

def build_market(cv, S=SPEC):
    g = S['z']['valley']
    for i, b in enumerate(S['stalls_north']):
        stall(cv, *b, f'stall N{i}', front='S' if b[2] > 190 else 'N', g=g)
    for i, b in enumerate(S['stalls_south']):
        stall(cv, *b, f'stall S{i}', front='N' if b[2] < 320 else 'S', g=g)
    hn = S['hatch_stalls']['north']
    stall(cv, *hn, 'hatch stall N', front='S', g=g)
    hs = S['hatch_stalls']['south']
    stall(cv, *hs, 'hatch stall S', front='N', g=g)
    for (x, y) in ((214, 188), (178, 198), (228, 170), (178, 316), (216, 340), (228, 378), (186, 228)):
        crate_stack(cv, x, y, g)
    for (x, y) in ((168, 196), (204, 196), (168, 312), (204, 312), (186, 364), (222, 226), (222, 286)):
        bench(cv, x, y, g)
    for (x, y) in ((180, 140), (198, 170), (198, 200), (180, 222), (180, 290), (198, 318), (198, 344),
                   (180, 372), (236, 200), (236, 312)):
        lantern(cv, x, y, g, 6)
    # ice-sculpture garden around the rink
    for (x, y, w, h) in ((228, 312, 3, 4), (230, 324, 2, 5), (226, 336, 3, 3), (232, 346, 2, 4)):
        cv.box(x, x + w - 1, y, y + w - 1, g - h, g - 1, C['ice'], 'ice')


# =============================================================================================== axis set pieces

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
    bench(cv, x0 + 3, cy0 + 1, f, back=False)

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
    cv.interiors.append(['nativity stable', 252, ny1 - 2, g])

    # tavern: two floors + cellar (cellar is dug in build_underground)
    tv = S['tavern']
    x0, x1, y0, y1 = tv['box']
    structures.building(cv, x0, x1, y0, y1, tv['floor'], storeys=2, storey_h=5, doors=('N', 'S', 'W'),
                        wall=C['wall'], name='tavern', furnish=False)
    cv.box(x0 + 4, x0 + 12, y1 - 3, y1 - 3, g - 1, g - 1, C['furn'], 'furniture')          # bar counter
    cv.box(x0 + 2, x0 + 3, y0 + 9, y0 + 10, g - 1, g - 1, C['furn'], 'furniture')          # table
    cv.box(x0 + 12, x0 + 13, y0 + 5, y0 + 6, g - 6, g - 6, C['furn'], 'furniture')         # upstairs table

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
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        px, py = int(math.floor(cx + 4.2 * math.cos(a))), int(math.floor(cy + 0.5 + 4.2 * math.sin(a)))
        if px <= 255:
            cv.box(px, px, py, py + 1, g - 3, g - 2, C['figure'], 'prop')
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


def build_mill(cv, S=SPEC):
    ml = S['mill']
    x0, x1, y0, y1 = ml['box']
    f = ml['floor']
    structures.building(cv, x0, x1, y0, y1, f, storeys=2, storey_h=5, doors=('N', 'W', 'E'), wall=C['wall'],
                        name='water mill')
    wx, wz = ml['wheel_c']
    r = ml['wheel_r']
    wy0, wy1 = ml['wheel_y']
    for x in range(wx - r - 1, wx + r + 2):
        for z in range(wz - r - 1, wz + r + 2):
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
    # buffer stop at the west end
    if x_start is not None:
        cv.box(x_start, x_start + 1, rw['rails_y'][0], rw['rails_y'][1], rz - 1, rz, C['soldier'], 'prop')
    # tunnel through the ridge spur (5 x 5) - rails run through it
    sp = S['spur']
    a0, a1 = sp['tunnel_air']
    for x in range(sp['x'][0], sp['x'][1] + 1):
        for y in range(sp['tunnel_y'][0], sp['tunnel_y'][1] + 1):
            cv.carve(x, x, y, y, a0, a1)
            if not cv.solid[x, y, a1 + 1]:
                cv.set(x, y, a1 + 1, C['ballast'], 'ballast')
        for y in rw['rails_y']:
            cv.set(x, y, rz, C['rail'], 'rail')
    cv.interiors.append(['spur rail tunnel', (sp['x'][0] + sp['x'][1]) // 2, sum(sp['tunnel_y']) // 2 + 1,
                         rz + 1])
    # stone portals
    for x in (sp['x'][0] + 3, sp['x'][1] - 3):
        for y in range(sp['tunnel_y'][0] - 1, sp['tunnel_y'][1] + 2):
            if cv.solid[x, y, a0 - 1]:
                cv.set(x, y, a0 - 1, C['stone'], 'building')


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


# =============================================================================================== pines + masks

def set_masks(cv, S=SPEC):
    sp = S['spawn']
    (bx, by), h, m = sp['base'], sp['half'], sp['margin']
    cv.no_prop(bx - h - m, bx + h + m, by - h - m, by + h + m, 1)
    a = S['anchor']
    cv.no_prop(a['x'][0] - 2, a['x'][1] + 2, a['y'][0] - 2, a['y'][1] + 2, 2)
    f = S['front']
    cv.no_prop(f['x'][0], f['x'][1], f['y'][0], f['y'][1], 4)
    u = S['under_platform']
    cv.no_prop(u['x'][0], u['x'][1], u['y'][0], u['y'][1], 8)


def plant_pines(cv, S=SPEC):
    placed, skipped = [], []
    for (x, y, r, h) in S['pines']:
        Hs = cv.H[x - r - 2:x + r + 3, y - r - 2:y + r + 3]
        ok = free_for_prop(cv, x - r - 2, x + r + 2, y - r - 2, y + r + 2) and Hs.max() <= 61 and \
            Hs.max() - Hs.min() <= 5
        if ok:
            pine(cv, x, y, r, h)
            placed.append((x, y, r, h))
        else:
            skipped.append((x, y, r, h))
    return {'placed': placed, 'skipped': skipped}


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


# =============================================================================================== top level

def build_west(S=SPEC):
    """Everything except the mirror and the train. Returns (canvas, report)."""
    cv = Canvas(S['name'])
    H, region = terrain(S)
    paint_terrain(cv, H, region)
    set_masks(cv, S)
    build_chapel(cv, S)
    build_post_office(cv, S)
    build_houses(cv, S)
    build_gatehouse(cv, S)
    build_front(cv, S)
    build_market(cv, S)
    build_axis(cv, S)
    build_mill(cv, S)
    build_railway(cv, S)
    build_underground(cv, S)
    pines = plant_pines(cv, S)
    return cv, {'pines': pines}
