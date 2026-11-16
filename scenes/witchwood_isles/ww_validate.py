"""Babel checks for Witchwood Isles (stock piqueserver 1.4.2 babel_script parameters).

Route graph is preliminary: 4-neighbour moves, step-up 1 (headroom checked), drops of any height
(recorded), standing needs 3 air voxels. It is not a collision simulation.
"""
import numpy as np
from scipy import sparse
from scipy.sparse import csgraph

from ww_core import W, D, floating_components, top_z

PLAT_X = (206, 305)
PLAT_Y = (240, 271)
PLAT_Z = 1
BASES = {'blue': (118, 256), 'red': (394, 256)}
SPAWN_HALF = 20
PROTECTED = {'blue': (128, 211, 240, 272), 'red': (301, 384, 240, 272)}  # enemy can't build standing here
SAFE_DROP = 9      # fall damage starts ~10 (derived)


def with_platform(solid):
    s = solid.copy()
    s[PLAT_X[0]:PLAT_X[1] + 1, PLAT_Y[0]:PLAT_Y[1] + 1, PLAT_Z] = True
    return s


# ---------------------------------------------------------------- route graph
class Nav:
    def __init__(self, solid):
        self.solid = solid
        air = ~solid
        pad = np.ones((W, W, D + 4), dtype=bool)     # z index shifted by +4; above map is air
        pad[:, :, 4:] = air
        self.air_p = pad
        stand = solid.copy()
        for k in (1, 2, 3):
            stand &= pad[:, :, 4 - k:4 - k + D]
        self.stand = stand
        nodes = np.argwhere(stand)
        self.nodes = nodes
        idx = np.full((W, W, D), -1, dtype=np.int32)
        idx[nodes[:, 0], nodes[:, 1], nodes[:, 2]] = np.arange(len(nodes), dtype=np.int32)
        self.idx = idx
        # next solid at or below z (for drops)
        nxt = np.full((W, W, D + 1), D, dtype=np.int16)
        for z in range(D - 1, -1, -1):
            nxt[:, :, z] = np.where(solid[:, :, z], z, nxt[:, :, z + 1])
        self.nxt = nxt
        self._edges()

    def air(self, x, y, z):
        return self.air_p[x, y, z + 4]

    def _edges(self):
        n = self.nodes
        x, y, z = n[:, 0], n[:, 1], n[:, 2]
        src, dst, up, drop = [], [], [], []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            ok = (nx >= 0) & (nx < W) & (ny >= 0) & (ny < W)
            i = np.nonzero(ok)[0]
            xi, yi, zi, nxi, nyi = x[i], y[i], z[i], nx[i], ny[i]
            same = self.stand[nxi, nyi, zi]
            zu = np.maximum(zi - 1, 0)
            up1 = (~same) & (zi >= 1) & self.stand[nxi, nyi, zu] & self.air(xi, yi, zi - 4)
            body = self.air(nxi, nyi, zi - 1) & self.air(nxi, nyi, zi - 2) & self.air(nxi, nyi, zi - 3) & \
                self.air(nxi, nyi, zi)
            fall = (~same) & (~up1) & body
            zt = self.nxt[nxi, nyi, np.minimum(zi, D - 1)]
            fall &= zt < D
            ztc = np.minimum(zt, D - 1)
            fall &= self.stand[nxi, nyi, ztc]
            for mask, ztarget, u, dr in ((same, zi, 0, None), (up1, zi - 1, 1, None), (fall, ztc, 0, 'f')):
                j = np.nonzero(mask)[0]
                src.append(i[j])
                dst.append(self.idx[nxi[j], nyi[j], ztarget[j]])
                up.append(np.full(len(j), u, np.int8))
                drop.append((ztarget[j] - zi[j]).astype(np.int16) if dr else np.zeros(len(j), np.int16))
        self.src = np.concatenate(src)
        self.dst = np.concatenate(dst)
        self.up = np.concatenate(up)
        self.drop = np.concatenate(drop)
        assert (self.dst >= 0).all()

    def graph(self, max_drop=99, dry=False):
        m = self.drop <= max_drop
        if dry:
            wet = self.nodes[:, 2] == 63
            m &= ~wet[self.src] & ~wet[self.dst]
        N = len(self.nodes)
        return sparse.csr_matrix((np.ones(m.sum()), (self.src[m], self.dst[m])), shape=(N, N))

    def ids(self, mask_fn):
        n = self.nodes
        return np.nonzero(mask_fn(n[:, 0], n[:, 1], n[:, 2]))[0]


def spawn_ids(nav, team, solid):
    bx, by = BASES[team]
    tz = top_z(solid)
    out = []
    for x in range(bx - SPAWN_HALF, bx + SPAWN_HALF + 1):
        for y in range(by - SPAWN_HALF, by + SPAWN_HALF + 1):
            i = nav.idx[x, y, tz[x, y]]
            if i >= 0:
                out.append(i)
    return np.array(out)


def dists(G, sources):
    d = csgraph.dijkstra(G, directed=True, indices=sources, min_only=True)
    return d


# ---------------------------------------------------------------- sightlines
def los_counts(solid_los, eyes, targets, max_range=None, step=0.33):
    """For each target, number of eyes with a clear straight line. Out-of-map / z<0 = air."""
    counts = np.zeros(len(targets), dtype=np.int32)
    T = np.asarray(targets, dtype=np.float64)
    for e in eyes:
        E = np.asarray(e, dtype=np.float64)
        vec = T - E
        L = np.linalg.norm(vec, axis=1)
        ok = np.ones(len(T), bool) if max_range is None else (L <= max_range)
        if not ok.any():
            continue
        S = int(np.ceil(L[ok].max() / step)) + 1
        ts = np.linspace(0, 1, S)[None, :, None]
        P = E[None, None, :] + vec[ok][:, None, :] * ts            # (n, S, 3)
        # ignore samples within 0.6 voxels of either end
        Lk = L[ok][:, None]
        dist_from_start = ts[:, :, 0] * Lk
        valid = (dist_from_start > 0.6) & (dist_from_start < Lk - 0.6)
        pi = np.floor(P).astype(np.int64)
        inmap = (pi[..., 0] >= 0) & (pi[..., 0] < W) & (pi[..., 1] >= 0) & (pi[..., 1] < W) & \
            (pi[..., 2] >= 0) & (pi[..., 2] < D)
        px = np.clip(pi[..., 0], 0, W - 1)
        py = np.clip(pi[..., 1], 0, W - 1)
        pz = np.clip(pi[..., 2], 0, D - 1)
        blocked = (solid_los[px, py, pz] & inmap & valid).any(axis=1)
        counts[np.nonzero(ok)[0][~blocked]] += 1
    return counts


def spawn_targets(solid, team, step=2):
    bx, by = BASES[team]
    tz = top_z(solid)
    pts = []
    for x in range(bx - SPAWN_HALF, bx + SPAWN_HALF + 1, step):
        for y in range(by - SPAWN_HALF, by + SPAWN_HALF + 1, step):
            pts.append((x + 0.5, y + 0.5, tz[x, y] - 2.2))
    return pts


def platform_eyes(step=2):
    eyes = []
    x0, x1 = PLAT_X
    y0, y1 = PLAT_Y
    for x in range(x0, x1 + 1, step):
        eyes.append((x + 0.5, y0 + 0.5, PLAT_Z - 2.4))
        eyes.append((x + 0.5, y1 + 0.5, PLAT_Z - 2.4))
    for y in range(y0 + step, y1, step):
        eyes.append((x0 + 0.5, y + 0.5, PLAT_Z - 2.4))
        eyes.append((x1 + 0.5, y + 0.5, PLAT_Z - 2.4))
    return eyes


# ---------------------------------------------------------------- main report
def run(solid, mat, spec, mats):
    R = {}
    M = {v[0]: k for k, v in mats.items()}
    tz = top_z(solid)

    # 1. floating
    flo, ncomp = floating_components(solid)
    R['floating_components'] = {'count': len(flo), 'components_total': ncomp, 'list': flo[:20]}

    # 2. mirror (x' = 512 - x)
    a = solid[1:256]
    b = solid[511:256:-1]
    ma = mat[1:256]
    mb = mat[511:256:-1]
    R['mirror'] = {'solid_mismatch': int((a != b).sum()), 'material_mismatch': int((ma != mb).sum())}

    # 3. platform clearance (build-blocked zone z <= 2 over the platform, and the z 1 ring)
    clear = solid[PLAT_X[0] - 1:PLAT_X[1] + 2, PLAT_Y[0] - 1:PLAT_Y[1] + 2, 0:3].sum()
    R['platform_clearance'] = {'authored_voxels_z0_2_over_platform_ring': int(clear)}

    # 4. anchor ground under each end of the platform
    mo = spec['mound']
    anchor = {}
    for team, xr in (('blue', (PLAT_X[0], mo['x'][1])), ('red', (512 - mo['x'][1], PLAT_X[1]))):
        cols = [(x, y) for x in range(xr[0], xr[1] + 1) for y in range(PLAT_Y[0], PLAT_Y[1] + 1)]
        tops = {int(tz[x, y]) for x, y in cols}
        solid_to_bottom = all(solid[x, y, tz[x, y]:].all() for x, y in cols)
        anchor[team] = {'x': list(xr), 'y': list(PLAT_Y), 'columns': len(cols), 'top_z': sorted(tops),
                        'solid_to_bottom': bool(solid_to_bottom),
                        'inside_own_build_ban_corridor': bool(PROTECTED[team][0] <= xr[0] and
                                                               xr[1] <= PROTECTED[team][1])}
    R['anchor_ground_under_platform'] = anchor

    # 5. spawn squares
    sp = {}
    for team, (bx, by) in BASES.items():
        box = (slice(bx - SPAWN_HALF, bx + SPAWN_HALF + 1), slice(by - SPAWN_HALF, by + SPAWN_HALF + 1))
        t = tz[box]
        land = solid[box][:, :, 62].all()
        # clearance: 3 air above every floor, and floor is topmost (get_z)
        clear3 = all((~solid[bx - SPAWN_HALF + i, by - SPAWN_HALF + j, max(0, t[i, j] - 3):t[i, j]]).all()
                     for i in range(t.shape[0]) for j in range(t.shape[1]))
        sp[team] = {'floor_z': sorted({int(v) for v in np.unique(t)}), 'all_land': bool(land),
                    'clearance_3': bool(clear3), 'base_get_z': int(tz[bx, by])}
    R['spawn_squares'] = sp

    # 6. pilings
    pl = spec['pilings']
    pil = []
    for (px, py) in pl['centres']:
        for team, cx in (('blue', px), ('red', 512 - px)):
            h = pl['size'] // 2
            blk = solid[cx - h:cx + h + 1, py - h:py + h + 1, pl['top_z']:63]
            pr = PROTECTED[team]
            above = solid[cx - h:cx + h + 1, py - h:py + h + 1, :pl['top_z']]
            pil.append({'team': team, 'centre': [cx, py], 'top_z': int(pl['top_z'] + 0 if blk.all() else -1),
                        'open_sky_above': bool(not above.any()), 'full_3x3_to_seabed': bool(blk.all()),
                        'in_own_corridor': bool(pr[0] <= cx - h and cx + h <= pr[1] and pr[2] <= py - h and py + h <= pr[3])})
    R['pilings'] = pil

    # 7. routes
    nav = Nav(solid)
    G_any = nav.graph()
    G_safe = nav.graph(max_drop=SAFE_DROP)
    G_safe_dry = nav.graph(max_drop=SAFE_DROP, dry=True)
    routes = {}
    reach_all = None
    for team in ('blue', 'red'):
        s = spawn_ids(nav, team, solid)
        if team == 'blue':
            mx = (mo['x'][0], mo['x'][1])
        else:
            mx = (512 - mo['x'][1], 512 - mo['x'][0])
        mound_top = nav.ids(lambda X, Y, Z: (X >= mx[0]) & (X <= mx[1]) & (Y >= mo['y'][0]) & (Y <= mo['y'][1]) &
                            (Z == mo['top_z']))
        floor_mid = nav.ids(lambda X, Y, Z: (X >= 212) & (X <= 300) & (Y >= 236) & (Y <= 276) &
                            (Z == 63 - spec['central']['H']))
        d_any = dists(G_any, s)
        d_safe_dry = dists(G_safe_dry, s)
        back_safe_dry = dists(G_safe_dry.T.tocsr(), s)     # distance from node to spawn
        reach = np.isfinite(d_any)
        reach_all = reach if reach_all is None else (reach_all | reach)
        # enemy walking from their spawn to THIS team's mound top (no building)
        enemy = 'red' if team == 'blue' else 'blue'
        se = spawn_ids(nav, enemy, solid)
        de = dists(G_any, se)
        stair_feet = nav.ids(lambda X, Y, Z: (X == (mo['x'][0] if team == 'blue' else 512 - mo['x'][0])) &
                             ((Y >= mo['north_stair_y'][0]) & (Y <= mo['north_stair_y'][1]) |
                              (Y >= mo['south_stair_y'][0]) & (Y <= mo['south_stair_y'][1])) &
                             (Z == 63 - spec['central']['H'] - 1))
        # footbridge alone (main boardwalk deck removed from the graph) still joins island and centre
        bw = spec['boardwalk']
        n_ = nav.nodes
        bw_rows = (n_[:, 1] >= bw['y'][0]) & (n_[:, 1] <= bw['y'][1]) & (n_[:, 2] == bw['deck_z']) & \
            (((n_[:, 0] >= 160) & (n_[:, 0] <= 200)) | ((n_[:, 0] >= 312) & (n_[:, 0] <= 352)))
        keep_e = ~bw_rows[nav.src] & ~bw_rows[nav.dst] & (nav.drop <= SAFE_DROP)
        wet_n = n_[:, 2] == 63
        keep_e &= ~wet_n[nav.src] & ~wet_n[nav.dst]
        Gfb = sparse.csr_matrix((np.ones(keep_e.sum()), (nav.src[keep_e], nav.dst[keep_e])), shape=(len(n_), len(n_)))
        d_fb = dists(Gfb, s)
        routes_fb = float(np.min(d_fb[floor_mid]))
        routes[team] = {
            'footbridge_only_spawn_to_central_floor_dry': routes_fb,
            'enemy_spawn_to_this_mound_top_steps': float(np.min(de[mound_top])),
            'stair_foot_cells': int(len(stair_feet)),
            'stair_feet_x': sorted({int(nav.nodes[i][0]) for i in stair_feet}),
            'spawn_nodes': int(len(s)),
            'spawn_to_mound_top_safe_dry_steps': float(np.min(d_safe_dry[mound_top])),
            'mound_top_to_spawn_safe_dry_steps_max': float(np.max(back_safe_dry[mound_top])),
            'mound_top_nodes': int(len(mound_top)),
            'mound_top_all_return_safe_dry': bool(np.isfinite(back_safe_dry[mound_top]).all()),
            'spawn_to_central_floor_safe_dry_steps': float(np.min(d_safe_dry[floor_mid])),
            'central_floor_all_return_safe_dry': bool(np.isfinite(back_safe_dry[floor_mid]).all()),
            'reachable_nodes_on_foot': int(reach.sum()),
        }
        # traps: reachable on foot (any drop) but cannot get back to spawn even with any drop
        back_any = dists(G_any.T.tocsr(), s)
        trap = reach & ~np.isfinite(back_any)
        tn = nav.nodes[trap]
        routes[team]['trap_nodes'] = int(trap.sum())
        routes[team]['trap_samples'] = tn[:10].tolist()
        # reachable dry land with only safe drops vs. everything walkable on land
        land_nodes = (nav.nodes[:, 2] < 63)
        routes[team]['land_nodes_reachable_safe_dry'] = int((np.isfinite(d_safe_dry) & land_nodes).sum())
    R['routes'] = routes

    # 8. build gap and highest reachable point near the platform (reachable on foot from either spawn)
    n = nav.nodes
    px = np.clip(n[:, 0], PLAT_X[0], PLAT_X[1])
    py = np.clip(n[:, 1], PLAT_Y[0], PLAT_Y[1])
    gap = np.sqrt((n[:, 0] - px) ** 2 + (n[:, 1] - py) ** 2 + (n[:, 2] - PLAT_Z) ** 2)
    gaps = {}
    for team in ('blue', 'red'):
        side = (n[:, 0] <= 255) if team == 'blue' else (n[:, 0] >= 257)
        g = np.where(reach_all & side, gap, np.inf)
        i = int(np.argmin(g))
        gaps[team] = {'min_gap': round(float(g[i]), 1), 'at': n[i].tolist(),
                      'material': mats[int(mat[tuple(n[i])])][0]}
    # pilings gap (towers start on the pilings, not reachable on foot)
    for team in ('blue', 'red'):
        tops = [(p['centre'][0], p['centre'][1], p['top_z']) for p in pil if p['team'] == team]
        gg = []
        for (cx, cy, cz) in tops:
            ddx = max(PLAT_X[0] - cx, 0, cx - PLAT_X[1])
            ddy = max(PLAT_Y[0] - cy, 0, cy - PLAT_Y[1])
            gg.append(np.sqrt(ddx ** 2 + ddy ** 2 + (cz - PLAT_Z) ** 2))
        gaps[team]['pilings_gap_range'] = [round(float(min(gg)), 1), round(float(max(gg)), 1)]
    near = (n[:, 0] >= 160) & (n[:, 0] <= 352) & (n[:, 1] >= 200) & (n[:, 1] <= 312) & reach_all
    zmin = int(n[near, 2].min())
    R['build_gap'] = gaps
    R['highest_reachable_near_platform'] = {'z': zmin, 'height_above_seabed': 63 - zmin,
                                            'distance_to_platform_top': zmin - PLAT_Z}
    # unreachable walkable surfaces on land (tops of props etc.), by material
    unreach = (~reach_all) & (n[:, 2] < 63)
    um = mat[n[unreach, 0], n[unreach, 1], n[unreach, 2]]
    R['unreachable_standable_surfaces_by_material'] = {mats[int(k)][0]: int(v) for k, v in
                                                       zip(*np.unique(um, return_counts=True))}

    # 9. spawn exposure from the platform perimeter (+ platform stamped as solid)
    sl = with_platform(solid)
    eyes = platform_eyes()
    expo = {}
    for team in ('blue', 'red'):
        T = spawn_targets(solid, team)
        c = los_counts(sl, eyes, T)
        expo[team] = {'spots': len(T), 'eyes': len(eyes), 'exposed_pct': round(100 * float((c > 0).mean()), 1),
                      'hidden_pct': round(100 * float((c == 0).mean()), 1),
                      'viewers_per_spot_mean': round(float(c.mean()), 1), 'viewers_max': int(c.max())}
    R['spawn_exposure_from_platform'] = expo

    # 10. ground sightlines into blue spawn from enemy-reachable spots (within 128, fog range)
    T = spawn_targets(solid, 'blue')
    groups = {
        'red_mound_top': [(x + 0.5, y + 0.5, mo['top_z'] - 2.4) for x in range(301, 317, 3) for y in range(240, 272, 3)],
        'blue_mound_top_invaded': [(x + 0.5, y + 0.5, mo['top_z'] - 2.4) for x in range(196, 212, 3) for y in range(240, 272, 3)],
        'central_floor': [(x + 0.5, y + 0.5, 63 - spec['central']['H'] - 2.4) for x in range(214, 300, 6) for y in range(232, 282, 6)],
        'blue_boardwalk': [(x + 0.5, y + 0.5, 61 - 2.4) for x in range(170, 186, 3) for y in range(252, 260, 3)],
    }
    gs = {}
    for k, E in groups.items():
        c = los_counts(sl, E, T, max_range=128)
        gs[k] = {'eyes': len(E), 'spots_seen_pct': round(100 * float((c > 0).mean()), 1),
                 'viewers_per_spot_mean': round(float(c.mean()), 2)}
    R['ground_sightlines_into_blue_spawn'] = gs
    return R
