"""DROWNED CATHEDRAL v2 - rotated layout + safe descents (2026-10-14).

Playtest feedback on v1: "too tall... I'd play it rotated 90 degrees... players might find it difficult to get down".
The user clarified: spawn players need safe ways down to the tower zone and to ground level (the rest of the map).
A literal 90-degree turn of v1 breaks stock Babel (spawns land in the fen / on the ruins), so v2 is a redesign:

  * the cathedral now runs BETWEEN the teams: west front + nave + crossing tower + mirrored east nave + east front,
    x 206-305 - exactly the platform's length, so the platform lies along the nave like a lid; twin fronts face each
    team's tower zone; transepts point north and south into the fen;
  * the fen is wider than tall (ellipse semi-axes 175 x 130), with two lobes (north / south) holding the drowned town;
  * spawn precinct + mole + tower zone stay at z 40 (same 39-block build as v1, spawn and zone on one level);
  * safe ways down (no fall over 9 voxels): wide stone ghats - stepped banks with 1-voxel risers - on both faces of
    each mole (2 per face) and of each spawn precinct, natural slopes on the outer rim, and a gallery entrance in each
    cathedral front at zone level with stairs down into the nave;
  * the bell tower, belfry and twin stair cores are v1's, unchanged.

Built on the v1 generator (scenes/drowned_cathedral.py): v1's SPEC is adjusted in place at import, v1's cathedral is
built in a scratch scene, mirrored, transposed (nave along x) and its west half pasted; the crossing tower is built
directly in final coordinates.

Run: python scenes/drowned_cathedral_v2.py out/drowned_cathedral_v2
"""
import copy
import json
import os
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import scenes.drowned_cathedral as D                                          # noqa: E402
from scenes import drowned_cathedral_props as P                              # noqa: E402
from aosmap.scene import Scene                                               # noqa: E402
from aosmap.art import fbm, value_noise, ramp, hex_rgb                                     # noqa: E402

SEED = D.SEED
BANK, FLOOR = D.BANK, D.FLOOR
NAME = 'drowned_cathedral_v2'

V2 = {
    'basin': {'centre': (256, 256), 'semi_axes': (195, 150), 'slope_w': 30},
    # ghats: stepped banks descending from the land edge (edge_y, the north face; mirrored to the south face)
    'ghats': [{'x': (152, 171), 'edge_y': 212}, {'x': (182, 201), 'edge_y': 212}, {'x': (118, 141), 'edge_y': 190}],
    'parvis': {'x': (206, 213), 'y': (244, 268)},
    # gallery: symmetric about y 256 like everything built from the mirrored v1 cathedral; side parapets on y 246/266
    'gallery': {'x': (220, 224), 'y': (246, 266), 'portal_y': (252, 260), 'portal_z': (35, 39),
                'stair_lanes_y': ((247, 249), (263, 265)), 'stair_x': (225, 243)},
    'causeways': {
        'n_ghats': ([(162, 191), (192, 191), (214, 198), (234, 198)], 5),
        'n_axis': ([(253, 112), (253, 186)], 7),
        'n_precinct': ([(129, 170), (150, 178), (162, 191)], 4),
        's_ghats': ([(162, 321), (192, 321), (214, 314), (234, 314)], 5),
        's_axis': ([(253, 400), (253, 326)], 7),
        's_precinct': ([(129, 342), (150, 334), (162, 321)], 4),
    },
    'cathedral': {'transept': {'x': (190, 233), 'y': (236, 275), 'top': 36, 'gable_mid': 28,
                               'windows': (196, 210, 224)},
                  'nave_y': (220, 243), 'piers_north': [232], 'cross_walk': False, 'ribs_y': (231,), 'doors_y': (),
                  'rubble': ((239, 228), (226, 252), (229, 262)),
                  'facade': {'towers_x': (230, 243), 'towers_y': (206, 219), 'wall_y': (214, 219), 'rose': (29, 4.5),
                             'gable_base': 23, 'front_buttresses': False, 'gargoyles': False}},
    'gibbets': [(177, 214)],
    'lychgates': (),
}

ORIG_SPEC = copy.deepcopy(D.SPEC)


def configure():
    """Adjust the shared v1 SPEC in place for v2 (v1 functions read it)."""
    S = D.SPEC
    S['basin'] = V2['basin']
    S['causeways'] = V2['causeways']
    S['gibbets'] = V2['gibbets']
    S['lychgates'] = V2['lychgates']
    C = S['cathedral']
    for k, v in V2['cathedral'].items():
        if k == 'facade':
            C['facade'] = dict(ORIG_SPEC['cathedral']['facade'], **v)
        else:
            C[k] = v
    S['ghats'] = V2['ghats']
    S['mode'] = 'babel (stock piqueserver 1.4.2) - v2 rotated layout'


configure()


class Layout2(D.Layout):
    def __init__(self):
        super().__init__()
        X, Y = self.X, self.Y
        st = np.zeros(X.shape, bool)
        for g in V2['ghats']:
            (gx0, gx1), ey = g['x'], g['edge_y']
            st |= (X >= gx0 - 1) & (X <= gx1 + 1) & (Y >= ey - 21) & (Y <= ey)
            st |= (X >= gx0 - 1) & (X <= gx1 + 1) & (Y >= 512 - ey) & (Y <= 512 - ey + 21)
        self.stairs = st
        box = self.box
        self.cathedral = (box({'x': (204, 255), 'y': (204, 308)}) | box({'x': (230, 255), 'y': (184, 328)})) & self.west
        pv = V2['parvis']
        self.parvis = box(pv)


def ghats(s, m, L, H):
    """Stepped stone banks: 1-voxel risers from the land edge (z 40) down to z 59, then a 2-row landing; low cheek
    walls with posts. Updates H for the stepped cells."""
    for g in V2['ghats']:
        (gx0, gx1), ey = g['x'], g['edge_y']
        for flip in (False, True):
            Yf = (lambda y: 512 - y) if flip else (lambda y: y)
            for k in range(1, 22):
                y = Yf(ey - k)
                hz = min(BANK + k, FLOOR)
                for x in range(gx0 - 1, gx1 + 2):
                    s.mat[x, y, :63] = 0
                    s.mat[x, y, hz:63] = m['quay']
                    s.mat[x, y, hz] = m['coping'] if (k % 6) else m['esplanade']
                    H[x, y] = hz
                for x in (gx0 - 1, gx1 + 1):                              # cheek walls, 2 high: no auto-step over
                    s.mat[x, y, hz - 2:hz] = m['coping']
                    if k % 4 == 1:
                        s.mat[x, y, hz - 3] = m['coping']
            for j in range(1, 9):                                        # grade the bank beyond the landing
                y = Yf(ey - 21 - j)                                      # (2-voxel terraces, no cliff beside it)
                zmin = FLOOR - 2 * j
                for x in range(gx0 - 1, gx1 + 2):
                    if (s.mat[x, y, :zmin] > 0).any():
                        s.mat[x, y, :zmin] = 0
                        if s.mat[x, y, zmin]:
                            s.mat[x, y, zmin] = m['mud']
                            H[x, y] = max(H[x, y], zmin)


def paste_cathedral(s, m, rng):
    """Build v1's cathedral (adjusted SPEC, no tower) in a scratch scene, mirror it (nave along y, symmetric about
    x 256), transpose so the nave runs along x, and paste its west half (x <= 255) into the final scene."""
    tmp = Scene('tmp_cathedral', seed=SEED)
    mt = D.materials(tmp)
    assert mt['stone'] == m['stone'] and mt['glass'] == m['glass']
    D.cathedral(tmp, mt, rng, with_tower=False)
    D.mirror(tmp)
    T = tmp.mat.transpose(1, 0, 2)
    west = np.zeros(T.shape[:2], bool); west[:256] = True
    sel = (T > 0) & west[:, :, None]
    s.mat[sel] = T[sel]


def parvis_and_gallery(s, m):
    """Terrace between the twin front towers at zone level, a portal through the front into a gallery inside the
    nave, and two stair flights from the gallery (z 40) down to the nave floor (z 59)."""
    pv = V2['parvis']
    (px0, px1), (py0, py1) = pv['x'], pv['y']
    for x in range(px0, px1 + 1):
        for y in range(py0, py1 + 1):
            s.mat[x, y, :BANK] = 0
            s.mat[x, y, BANK + 1:63] = m['quay']
            s.mat[x, y, BANK] = m['esplanade']
    G = V2['gallery']
    (gx0, gx1), (gy0, gy1) = G['x'], G['y']
    (ty0, ty1), (tz0, tz1) = G['portal_y'], G['portal_z']
    s.mat[214:220, ty0:ty1 + 1, tz0:tz1 + 1] = 0                                 # portal through the front wall
    s.mat[214:220, ty0:ty1 + 1, BANK] = m['floor']
    s.mat[213, ty0 - 1:ty1 + 2, tz0 - 1] = m['trim']                              # lintel moulding
    s.mat[213, ty0 - 1, tz0:tz1 + 1] = m['trim']; s.mat[213, ty1 + 1, tz0:tz1 + 1] = m['trim']
    s.mat[gx0:gx1 + 1, gy0:gy1 + 1, :BANK] = 0
    s.mat[gx0:gx1 + 1, gy0:gy1 + 1, BANK] = m['floor']                            # gallery slab
    for yb in (gy0, gy1):                                                          # side parapets, 2 high
        s.mat[gx0:gx1 + 1, yb, BANK - 2:BANK] = m['trim']
    s.mat[gx1, gy0:gy1 + 1, BANK - 2:BANK] = m['trim']                             # gallery parapet, 2 high...
    for (ly0, ly1) in G['stair_lanes_y']:
        s.mat[gx1, ly0:ly1 + 1, BANK - 2:BANK] = 0                                # ...open over each flight
    sx0, sx1 = G['stair_x']
    for x in range(sx0, sx1 + 1):
        stand = BANK + (x - gx1)
        for (ly0, ly1) in G['stair_lanes_y']:
            s.mat[x, ly0:ly1 + 1, :stand] = 0
            s.mat[x, ly0:ly1 + 1, stand:63] = m['stone_dk']
            s.mat[x, ly0:ly1 + 1, stand] = m['trim']
            for yb in (ly0 - 1, ly1 + 1):                                       # stringer walls + 2-high rails
                s.mat[x, yb, stand - 2:63] = m['stone_dk']
                s.mat[x, yb, stand - 2] = m['trim']
    # candles on the gallery parapet and lanterns at the stair heads
    for y in range(gy0 + 1, gy1, 3):
        if s.mat[gx1, y, BANK - 2] and not s.mat[gx1, y, BANK - 3]:
            s.mat[gx1, y, BANK - 3] = m['wax']; s.mat[gx1, y, BANK - 4] = m['glow']


def transept_interior(s, m, rng):
    """The long v2 transepts would be bare checker floors: give each arm an arcade (2x2 piers every 11, pointed
    arches, ruined tops), slumped and silted floor slabs in the side aisle, tomb chests between the piers and two
    surviving vault ribs carried on their piers. West half only (x <= 255; the centre column is copied by mirror)."""
    T = D.SPEC['cathedral']['transept']
    tx0 = T['x'][0]
    wx0 = T['y'][0] + 2                                   # first floor column inside the west wall (v2 x)
    px = wx0 + 6                                          # pier line (2 thick): x 244-245
    piers = list(range(tx0 + 8, 232, 11))
    ribs = [y for y in piers if y <= 222][::2]
    for flip in (False, True):
        Yf = (lambda y: 512 - y) if flip else (lambda y: y)
        # slumped floor in the side aisle (1-2 down, silt in the deepest), walkway x 250-255 kept level
        for x in range(wx0, px):
            for yy in range(tx0 + 3, 234):
                y = Yf(yy)
                n = float(fbm(np.array([x]), np.array([yy]), None, scale=6, octaves=2, seed=SEED + 600)[0])
                d = 2 if n > 0.68 else (1 if n > 0.58 else 0)
                if d:
                    s.mat[x, y, FLOOR:FLOOR + d] = 0
                    s.mat[x, y, FLOOR + d] = m['mud'] if d == 2 else m['floor']
        # arcade wall band + piers, then arches
        y0, y1 = piers[0], piers[-1] + 1
        Ys = sorted((Yf(y0), Yf(y1)))
        s.box(px, px + 1, Ys[0], Ys[1], 45, 36, m['stone'])
        for yy in piers:
            ya = sorted((Yf(yy), Yf(yy + 1)))
            top = 36
            if yy in ribs:
                top = 27
            s.box(px, px + 1, ya[0], ya[1], 62, top, m['stone_dk'])
            s.mat[px - 1, ya[0]:ya[1] + 1, 46] = m['trim']                 # capital
            s.mat[px + 2, ya[0]:ya[1] + 1, 46] = m['trim']
        for a, b in zip(piers[:-1], piers[1:]):
            ua, ub = sorted((Yf(a + 2), Yf(b - 1)))
            D.carve_arch_x(s, px, px + 1, ua, ub, FLOOR - 1, 50)
        band = np.zeros((512, 512), bool)
        band[px:px + 2, Ys[0]:Ys[1] + 1] = True
        for yy in ribs:
            for y in (Yf(yy), Yf(yy + 1)):
                band[px:px + 2, y] = False
        D.ruin(s, band, amp=7, seed=SEED + 601, only_above=50)
        # surviving vault ribs: wall top -> pier -> crown, some broken short of the crown
        for yy in ribs:
            xb = int(rng.integers(249, 256))
            for x in range(wx0, 256):
                if x > xb:
                    break
                dx = 256 - x
                zr = int(round(36 - np.sqrt(max(0.0, 18 ** 2 - dx * dx)) * 0.5))
                for y in (Yf(yy), Yf(yy + 1)):
                    s.mat[x, y, zr:zr + 2] = m['trim']
                    if x == wx0:
                        s.mat[x, y, zr:FLOOR] = m['stone_dk']               # springer down the wall
        # tomb chests between the piers (side aisle)
        for a, b in zip(piers[:-1], piers[1:]):
            if rng.random() < 0.7:
                yc = (a + b) // 2
                ya, yb = sorted((Yf(yc - 2), Yf(yc + 2)))
                x0 = wx0 + 1
                fz = max(D.top_z(s, x, y) for x in range(x0, x0 + 3) for y in range(ya, yb + 1))
                s.box(x0, x0 + 2, ya, yb, fz - 1, fz - 2, m['stone'])
                s.box(x0, x0 + 2, ya, yb, fz - 3, fz - 3, m['trim'])
                for x in range(x0, x0 + 3):                                 # fill under (slumped slabs)
                    for y in range(ya, yb + 1):
                        z = fz
                        while z < FLOOR + 3 and s.mat[x, y, z] == 0:
                            s.mat[x, y, z] = m['stone_dk']; z += 1
                if rng.random() < 0.6:
                    s.mat[x0 + 1, ya + 1:yb, fz - 4] = m['stone']            # effigy
                    s.mat[x0 + 1, ya + 1 if not flip else yb - 1, fz - 5] = m['stone']


def escape_steps(s, m, max_rounds=4):
    """Flooded pockets (aisles, pools between causeways) that a player can step down into but not climb out of
    (water z 63 under a z 59 floor = 4 up). Using the nav graph (no damaging drops), find every such one-way pocket
    in the west half and set a 2-stone stair at its edge: stone at z 61 then z 60 up to the z 59 floor (2-1-1 rises).
    Repeats until no pocket of 3+ nodes is left."""
    from aosmap import nav
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import dijkstra
    sc = D.SPEC['script_constants']
    placed = []
    for _ in range(max_rounds):
        solid = s.mat > 0
        g = nav.build(solid, water_damage=False)
        src, dst, cost, kind = g.edges
        n = len(g.node_xyz)
        k = kind != 4
        M = coo_matrix((cost[k], (src[k], dst[k])), shape=(n, n)).tocsr()
        srcs = nav.zone_nodes(g, *sc['bases'][0], sc['spawn_half'])
        f = dijkstra(M, indices=srcs, min_only=True)
        b = dijkstra(M.T.tocsr(), indices=srcs, min_only=True)
        xyz = g.node_xyz
        trap = np.isfinite(f) & ~np.isfinite(b) & (xyz[:, 0] <= 254) & (xyz[:, 2] >= 61)
        esc = np.isfinite(b) & (xyz[:, 2] >= 58) & (xyz[:, 2] <= 60)
        tm = np.zeros((512, 512), bool); tm[xyz[trap, 0], xyz[trap, 1]] = True
        em = np.zeros((512, 512), bool); em[xyz[esc, 0], xyz[esc, 1]] = True
        lab, nl = ndimage.label(tm)
        if not nl:
            break
        sizes = ndimage.sum(tm, lab, range(1, nl + 1))
        done = 0
        for ci in range(1, nl + 1):
            if sizes[ci - 1] < 3:
                continue
            cells = np.argwhere(lab == ci)
            best = None
            for (x, y) in cells:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    x2, y2 = x - dx, y - dy                    # second stone, further into the pocket
                    if not (em[x + dx, y + dy] and 0 < x2 <= 254 and lab[x2, y2] == ci):
                        continue
                    if (s.mat[x, y, 50:61] > 0).any() or (s.mat[x2, y2, 50:62] > 0).any():
                        continue                               # keep headroom over both stones
                    key = (abs(int(y) - 256), int(x), int(y))   # deterministic pick: nearest the axis, then x
                    if best is None or key < best[0]:
                        best = (key, (int(x), int(y)), (int(x2), int(y2)))
            if best is None:
                continue
            (_, (x, y), (x2, y2)) = best
            s.mat[x, y, 60:63] = m['quay']; s.mat[x, y, 60] = m['causeway']
            s.mat[x2, y2, 61:63] = m['quay']; s.mat[x2, y2, 61] = m['causeway']
            placed.append([x, y, x2, y2])
            done += 1
        if not done:
            break
    return placed


def ghat_dressing(s, m, rng):
    """Lanterns at ghat tops/feet, candles and jack-o'-lanterns left on the steps."""
    lp = P.lantern_post(m, h=4)
    for g in V2['ghats']:
        (gx0, gx1), ey = g['x'], g['edge_y']
        for flip in (False, True):
            Yf = (lambda y: 512 - y) if flip else (lambda y: y)
            for x in (gx0 - 1, gx1 + 1):
                y = Yf(ey - 1)
                z = D.top_z(s, x, y)
                s.mat[x, y, z - 4:z] = m['iron']; s.mat[x, y, z - 5] = m['glow']; s.mat[x, y, z - 6] = m['iron']
            for k in range(3, 19, 5):
                y = Yf(ey - k); hz = BANK + k
                for x in (gx0 + 1, gx1 - 1):
                    if rng.random() < 0.6 and s.mat[x, y, hz - 1] == 0:
                        if rng.random() < 0.5:
                            s.mat[x, y, hz - 1] = m['wax']; s.mat[x, y, hz - 2] = m['glow']
                        else:
                            D.plant(s, P.pumpkin(int(rng.integers(1 << 30)), m, size=1), x, y, hz)


def build():
    L = Layout2()
    s = Scene(NAME, seed=SEED)
    m = D.materials(s)
    rng = np.random.default_rng(SEED + 100)
    H = D.terrain(L)
    D.ground(s, L, m, H)
    ghats(s, m, L, H)
    D.causeways(s, m, L, H)
    paste_cathedral(s, m, rng)
    D.crossing_tower(s, m)
    D.tower_gargoyles(s, m)
    transept_interior(s, m, rng)
    parvis_and_gallery(s, m)
    D.precinct(s, m, L, rng)
    for (cx, cy, w, d) in D.SPEC['cottages']:
        for yy in (cy, 512 - cy):
            D.cottage_ruin(s, m, cx, yy, w, d, SEED + cx * 7 + yy)
    D.quay_details(s, m, L, H, rng)
    town = D.drowned_town(s, m, L, H, rng)
    counts = D.fen_and_banks_dressing(s, m, L, H, rng, extra_block=town | L.cathedral | L.parvis)
    counts['drowned_houses_west'] = len(L.houses)
    ghat_dressing(s, m, rng)
    s.markers['escape_steps'] = escape_steps(s, m)
    D.mirror(s)
    sub = s.mat[257:, :, :]
    sub[sub == m['banner_blue']] = m['banner_red']
    D.signature(s, m, L)
    s.markers['pruned'] = D.prune_floating(s)
    X, Y = L.X, L.Y
    base = ramp(['#1e2e2b', '#2a403b', '#34503f'], fbm(X, Y, None, scale=26, octaves=3, seed=SEED + 70))
    alg = fbm(X, Y, None, scale=9, octaves=2, seed=SEED + 71)
    base = np.where((alg > 0.62)[..., None], base * 0.6 + hex_rgb('#4a6236') * 0.4, base)
    s.paint_bottom(np.clip(base, 0, 255).astype(np.uint8))
    s.markers['counts'] = counts
    s.markers['H'] = H
    return s, L


def metadata_txt():
    from aosmap.meta import map_txt
    return map_txt(
        name='Drowned Cathedral', author='shywolf91 and AI', version='2.0',
        description='A gothic cathedral sunk in a fen at dusk, its nave running between the two quays. Babel: build '
                    'from your quay, or race up the drowned bell tower beneath the platform.',
        header='Generated by scenes/drowned_cathedral_v2.py (seed %d). No spawn hooks: spawns use the game mode defaults.'
               % SEED,
        fog=D.FOG, extensions={'babel': True, 'water_damage': 0})


if __name__ == '__main__':
    from aosmap.vxl import write_vxl
    out = sys.argv[1] if len(sys.argv) > 1 else 'out/' + NAME
    os.makedirs(out, exist_ok=True)
    s, L = build()
    data = write_vxl(s.to_voxelmap())
    open(os.path.join(out, NAME + '.vxl'), 'wb').write(data)
    open(os.path.join(out, NAME + '.txt'), 'w').write(metadata_txt())
    json.dump({'v1_spec_after_v2_changes': D.SPEC, 'v2': V2}, open(os.path.join(out, 'spec.json'), 'w'), indent=1,
              default=list)
    print('written', len(data), 'bytes', s.markers['counts'], 'pruned', s.markers['pruned'],
          'escape steps', len(s.markers['escape_steps']))
