"""Zone profile of a Babel map: spawn, tower zone / front, centre (report-only metrics).

Pure functions on the solid array [x, y, z] (z = 0 sky top, z = 63 bottom) plus `params` (BABEL_DEFAULT). Every
number is deterministic (fixed sampling grids, fixed rng seed 0). Used by `babel_checks.run_all` ('zone_profile'
section) and by the corpus study `tools/babel_zone_study.py`. Definitions are repeated in docs/babel_zone_study.md.

Conventions
-----------
* top[x, y]   = topmost solid z of the column (64 if the column has no solid at all).
* height      = 63 - top (blocks above the bottom). "Higher" always means a smaller z.
* water       = top >= 62 (nothing above the sea / indestructible floor).
* ground baseline = grey opening of the height field with a 25 x 25 window: it removes every raised feature
  narrower than 25 voxels. object height = height - baseline; an "object column" has object height >= 2 and is not
  water. Large buildings (> 25 wide) and broad hills count as ground; narrow ridges count as objects.
  UNRELIABLE on sky/bridge maps (the baseline under decks is the sea) - say so when quoting it.
* walkable cell = kit `standable` (solid voxel with 3 air voxels above, z >= 3). Routes use the kit `Nav`
  ('hc' rules: 4 neighbours, 1-voxel step, safe drops <= 9). Graph model, not a collision simulation.
* eye = floor z - 2.4 (as the calibrated exposure model's platform eyes), head = floor z - 2.2.
* Line of sight marches in 0.5 steps through solid voxels plus the script platform (opaque at z = platform_z).
  Point-to-point LOS is cut at FOG_RANGE = 128 voxels (horizontal distance) unless stated otherwise; the kit's
  platform-viewer exposure ignores fog (kept as calibrated).

Zones (stock constants, team 0 = blue at x < 256; red is the mirror and every metric is measured for both teams)
* spawn square: base +- spawn_half (blue x 98-138, y 236-276). spawn floor = median top z of the square.
* front / tower zone: y = base_y +- spawn_half, x from the square edge to the platform end column inclusive
  (blue x 139-211, red x 300-373). anchor patch: the 6 columns under the platform end plus 6 in front
  (blue x 200-211, red x 300-311), y 240-271.
* centre strip: under the platform between the anchor ends (x 212-300, y 240-271).
* central zone: x 150-362, y 130-382.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage as ndi
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import maximum_flow

from .params import BABEL_DEFAULT, FALL_SAFE_MAX, MX, MY, MZ

FOG_RANGE = 128.0
EYE = 2.4
HEAD = 2.2
BASELINE_WINDOW = 25
CENTRE_BOX = (150, 362, 130, 382)
N_DIRS = 16


# =============================================================================================== decoding

def decode_solid_fast(data: bytes):
    """Span headers only -> (solid bool [x, y, z], top colour uint32 [x, y]). Much faster than the strict reader
    (colours below the top are skipped). Raises ValueError on truncated or out-of-range data."""
    solid = np.ones((MY, MX, MZ), bool)
    topc = np.zeros((MY, MX), np.uint32)
    n = len(data)
    mv = memoryview(data)
    p = 0
    for y in range(MY):
        sy = solid[y]
        for x in range(MX):
            z = 0
            got = False
            while True:
                if p + 4 > n:
                    raise ValueError(f'truncated at column ({x},{y})')
                N, S, E = mv[p], mv[p + 1], mv[p + 2]
                if S > 64 or E > 63:
                    raise ValueError(f'z out of range at ({x},{y})')
                if S > z:
                    sy[x, z:S] = False
                if not got and E >= S and p + 8 <= n:
                    topc[y, x] = int.from_bytes(mv[p + 4:p + 8], 'little')
                    got = True
                if N == 0:
                    p += 4 * (max(E - S + 1, 0) + 1)
                    break
                p += 4 * N
                if p + 4 > n:
                    raise ValueError(f'truncated at column ({x},{y})')
                z = mv[p + 3]
    if p != n:
        raise ValueError(f'{n - p} trailing bytes')
    return np.ascontiguousarray(solid.transpose(1, 0, 2)), np.ascontiguousarray(topc.T)


# =============================================================================================== basic fields

def tops(solid):
    any_ = solid.any(axis=2)
    return np.where(any_, np.argmax(solid, axis=2), 64).astype(np.int16)


def fields(solid, window=BASELINE_WINDOW):
    """Per-column fields shared by every metric (dict of 2-D arrays)."""
    top = tops(solid)
    water = top >= 62
    h = (63 - top).astype(np.int16)
    h = np.where(water, 0, h)
    base = ndi.grey_opening(h, size=(window, window), mode='nearest')
    obj_h = (h - base).astype(np.int16)
    obj = (obj_h >= 2) & ~water
    # air below the topmost voxel: 'roof' = an air gap >= 3 tall (room for a player) closed by a dry solid floor
    # <= 20 below the top (roof / canopy / overhang with a space under it: spawning there means spawning on a
    # roof). 'deck' = any other air below the top (thin pocket, or a deck/bridge over water or a lethal drop).
    Z = np.arange(MZ)[None, None, :]
    below = Z > top[..., None].astype(int)
    air_b = ~solid & below
    has_air = air_b.any(axis=2) & (top < 62)
    za = np.argmax(air_b, axis=2)
    sol_after = solid & (Z > za[..., None])
    zb = np.where(sol_after.any(axis=2), np.argmax(sol_after, axis=2), 64)
    roof = has_air & (zb - za >= 3) & (zb < 62) & (zb - top <= 20)
    deck = has_air & ~roof
    return {'top': top, 'water': water, 'h': h, 'base': base, 'obj_h': obj_h, 'obj': obj, 'roof': roof,
            'deck': deck}


def _pct(a, q):
    a = np.asarray(a, float)
    return round(float(np.percentile(a, q)), 2) if a.size else None


def _r(v, n=2):
    return None if v is None else round(float(v), n)


def _stats(a):
    a = np.asarray(a, float)
    if not a.size:
        return {'n': 0}
    return {'n': int(a.size), 'mean': _r(a.mean()), 'p10': _pct(a, 10), 'p50': _pct(a, 50), 'p90': _pct(a, 90),
            'max': _r(a.max())}


# =============================================================================================== line of sight

def _opaque(solid, params):
    (x0, x1), (y0, y1), pz = params['platform_x'], params['platform_y'], params['platform_z']
    op = solid.copy()
    op[x0:x1 + 1, y0:y1 + 1, pz] = True
    return op


def los_pairs(opaque, A, B, step=0.5, max_range=FOG_RANGE, chunk=200000):
    """Visibility for each pair (A[i], B[i]) of float xyz points. Pairs farther apart than max_range (horizontal)
    are not visible. The end voxel (the target's own column cell) is not tested."""
    A = np.asarray(A, float)
    B = np.asarray(B, float)
    out = np.zeros(len(A), bool)
    for s in range(0, len(A), chunk):
        a, b = A[s:s + chunk], B[s:s + chunk]
        d = b - a
        L = np.linalg.norm(d, axis=1)
        horiz = np.hypot(d[:, 0], d[:, 1])
        vis = np.ones(len(a), bool)
        if max_range is not None:
            vis &= horiz <= max_range
        Lm = L[vis].max() if vis.any() else 0
        n = int(np.ceil(Lm / step)) + 1
        for k in range(1, n):
            t = k * step / np.maximum(L, 1e-9)
            act = vis & (t < 0.995)
            if not act.any():
                break
            idx = np.nonzero(act)[0]
            p = a[idx] + d[idx] * t[idx, None]
            xi, yi, zi = (np.floor(p[:, i]).astype(int) for i in range(3))
            ins = (zi >= 0) & (zi < MZ) & (xi >= 0) & (xi < MX) & (yi >= 0) & (yi < MY)
            hit = np.zeros(len(idx), bool)
            hit[ins] = opaque[xi[ins], yi[ins], zi[ins]]
            vis[idx[hit]] = False
        out[s:s + chunk] = vis
    return out


def los_any(opaque, eyes, targets, max_range=FOG_RANGE):
    """-> per target: number of eyes that see it."""
    eyes = np.asarray(eyes, float)
    targets = np.asarray(targets, float)
    if not len(eyes) or not len(targets):
        return np.zeros(len(targets), int)
    A = np.repeat(eyes, len(targets), 0)
    B = np.tile(targets, (len(eyes), 1))
    return los_pairs(opaque, A, B, max_range=max_range).reshape(len(eyes), len(targets)).sum(0)


def free_rays(opaque, origins, dirs=N_DIRS, step=0.5, max_len=FOG_RANGE):
    """Horizontal free line-of-sight length from each origin (x, y, eye z) in `dirs` evenly spaced directions.
    -> array [n_origins, dirs]. A ray stops at the first opaque voxel at the eye z or at the map edge."""
    o = np.asarray(origins, float)
    ang = np.arange(dirs) * 2 * math.pi / dirs
    dv = np.stack([np.cos(ang), np.sin(ang)], 1)
    L = np.full((len(o), dirs), max_len)
    alive = np.ones((len(o), dirs), bool)
    zi = np.floor(o[:, 2]).astype(int)
    for k in range(1, int(max_len / step) + 1):
        if not alive.any():
            break
        r = k * step
        px = np.floor(o[:, 0, None] + dv[None, :, 0] * r).astype(int)
        py = np.floor(o[:, 1, None] + dv[None, :, 1] * r).astype(int)
        out = (px < 0) | (px >= MX) | (py < 0) | (py >= MY)
        zz = np.broadcast_to(zi[:, None], px.shape)
        okz = (zz >= 0) & (zz < MZ)
        hit = np.zeros(px.shape, bool)
        m = ~out & okz & alive
        hit[m] = opaque[px[m], py[m], zz[m]]
        stop = alive & (hit | out)
        L[stop] = r - step
        alive &= ~stop
    return L


# =============================================================================================== helpers

def team_geometry(params=BABEL_DEFAULT):
    """Per team: base, enemy direction s (+1 blue, -1 red), square, front x-range, anchor x-range, own end x-range."""
    (x0, x1), (y0, y1) = params['platform_x'], params['platform_y']
    half = params['spawn_half']
    out = []
    for k, (bx, by) in enumerate(params['bases']):
        s = 1 if k == 0 else -1
        sq = (bx - half, bx + half, by - half, by + half)
        if s > 0:
            front = (bx + half + 1, x0 + 5)
            anchor = (x0 - 6, x0 + 5)
            end = (x0, x0 + 5)
        else:
            front = (x1 - 5, bx - half - 1)
            anchor = (x1 - 5, x1 + 6)
            end = (x1 - 5, x1)
        out.append({'name': params['team_names'][k], 'base': (bx, by), 's': s, 'square': sq, 'front': front,
                    'anchor': anchor, 'end': end, 'band': (by - half, by + half)})
    return out


def _box(a, x0, x1, y0, y1):
    return a[max(x0, 0):min(x1, MX - 1) + 1, max(y0, 0):min(y1, MY - 1) + 1]


def _ring_loop(sq, r):
    """Cells at Chebyshev distance exactly r outside the square, in loop order (clockwise), clipped to the map."""
    x0, x1, y0, y1 = sq[0] - r, sq[1] + r, sq[2] - r, sq[3] + r
    pts = [(x, y0) for x in range(x0, x1 + 1)] + [(x1, y) for y in range(y0 + 1, y1 + 1)] + \
          [(x, y1) for x in range(x1 - 1, x0 - 1, -1)] + [(x0, y) for y in range(y1 - 1, y0, -1)]
    return [(x, y) for x, y in pts if 0 <= x < MX and 0 <= y < MY]


def _segments(flags):
    """Lengths of circular runs of True."""
    f = list(flags)
    if not f:
        return []
    if all(f):
        return [len(f)]
    k = f.index(False)
    f = f[k:] + f[:k]
    runs, c = [], 0
    for v in f:
        if v:
            c += 1
        elif c:
            runs.append(c)
            c = 0
    if c:
        runs.append(c)
    return runs


def _runs_1d(flags):
    runs, c = [], 0
    for v in flags:
        if v:
            c += 1
        elif c:
            runs.append(c)
            c = 0
    if c:
        runs.append(c)
    return runs


def _sample(idx, n, seed=0):
    idx = np.asarray(idx)
    if len(idx) <= n:
        return idx
    return np.sort(np.random.default_rng(seed).choice(idx, n, replace=False))


def _grid_eyes(top, xr, yr, sx, sy, eye=EYE):
    pts = []
    for x in range(xr[0], xr[1] + 1, sx):
        for y in range(yr[0], yr[1] + 1, sy):
            pts.append((x + .5, y + .5, float(top[x, y]) - eye))
    return np.array(pts, float)


def _flow_width(nav, nodes, src_mask, sink_mask):
    """Max number of vertex-disjoint directed paths src -> sink inside `nodes` (= min vertex cut, in cells)."""
    nodes = np.asarray(nodes)
    if not len(nodes) or not src_mask.any() or not sink_mask.any():
        return 0
    n = len(nodes)
    sub = nav.G[nodes][:, nodes].tocoo()
    S, T = 2 * n, 2 * n + 1
    big = n + 5
    rows = np.concatenate([np.arange(n), sub.row + n, np.full(src_mask.sum(), S), np.nonzero(sink_mask)[0] + n])
    cols = np.concatenate([np.arange(n) + n, sub.col, np.nonzero(src_mask)[0], np.full(sink_mask.sum(), T)])
    cap = np.concatenate([np.ones(n), np.full(len(sub.row), big), np.ones(src_mask.sum()), np.ones(sink_mask.sum())])
    M = coo_matrix((cap.astype(np.int32), (rows, cols)), shape=(2 * n + 2, 2 * n + 2)).tocsr()
    M.sum_duplicates()
    return int(maximum_flow(M, S, T, method='dinic').flow_value)


# =============================================================================================== spawn

def spawn_metrics(solid, F, nav, team, params, opaque, d_spawn=None):
    t_ = team
    top = F['top']
    pz = params['platform_z']
    x0s, x1s, y0s, y1s = t_['square']
    bx, by = t_['base']
    s = t_['s']
    t = _box(top, x0s, x1s, y0s, y1s).astype(int)
    floor = int(np.median(t))
    vals, cnt = np.unique(t, return_counts=True)
    mode = int(vals[np.argmax(cnt)])
    rough = np.concatenate([np.abs(np.diff(t, axis=0)).ravel(), np.abs(np.diff(t, axis=1)).ravel()])
    sq = {'floor_z': floor, 'top_z_mean': _r(t.mean()), 'top_z_min': int(t.min()), 'top_z_max': int(t.max()),
          'top_z_std': _r(t.std()), 'near_mode_share': _r((np.abs(t - mode) <= 1).mean(), 3),
          'roof_cols': int(_box(F['roof'], x0s, x1s, y0s, y1s).sum()),
          'deck_cols': int(_box(F['deck'], x0s, x1s, y0s, y1s).sum()),
          'water_cols': int(_box(F['water'], x0s, x1s, y0s, y1s).sum()),
          'roughness': _r(rough.mean(), 3)}
    fx = t_['front']
    ft = _box(top, fx[0], fx[1], *t_['band']).astype(int)
    (cx0, cx1), (py0, py1) = params['platform_x'], params['platform_y']
    ct = top[cx0 + 6:cx1 - 4, py0:py1 + 1].astype(int)
    land = top[~F['water']]
    med_land = float(np.median(land)) if land.size else 63.0
    horiz = abs(bx - (cx0 if s > 0 else cx1))
    sq['height_above_front'] = _r(ft.mean() - t.mean())
    sq['height_above_centre_ground'] = _r(np.median(ct) - t.mean())
    sq['height_above_map_median_land'] = _r(med_land - t.mean())
    sq['platform_drop'] = _r(t.mean() - pz)
    sq['platform_angle_deg'] = _r(math.degrees(math.atan2(t.mean() - pz, horiz)), 1)

    # enclosure: what stands above the spawn floor in rings around the square, by side
    X, Y = np.meshgrid(np.arange(MX), np.arange(MY), indexing='ij')
    dx = np.maximum(np.maximum(x0s - X, X - x1s), 0)
    dy = np.maximum(np.maximum(y0s - Y, Y - y1s), 0)
    d = np.maximum(dx, dy)
    sx = s * (X - bx)
    lat = np.abs(Y - by)
    enemy = (sx > t_['square'][1] - bx) & ((sx - (x1s - bx)) >= (lat - (y1s - by)))
    rear = (-sx > t_['square'][1] - bx) & ((-sx - (x1s - bx)) >= (lat - (y1s - by)))
    above = np.clip(floor - top.astype(int), 0, None)                       # blocks the column rises above floor
    vol = solid[:, :, :max(floor, 0)].sum(axis=2) if floor > 0 else np.zeros_like(top)
    enc = {}
    for rname, (ra, rb) in (('r0_8', (0, 8)), ('r8_20', (8, 20)), ('r20_40', (20, 40))):
        ring = (d > ra) & (d <= rb)
        for side, m in (('enemy', enemy), ('rear', rear), ('lateral', ~enemy & ~rear)):
            c = ring & m
            if c.any():
                enc[f'{rname}_{side}_vol'] = _r(vol[c].mean())
                enc[f'{rname}_{side}_cover3'] = _r((above[c] >= 3).mean(), 3)
    sq['enclosure'] = enc

    # exits: ring cells at distance r reached from the square without leaving the (square + r) box
    ex = {}
    if nav is not None:
        src = nav.nodes_in(x0s, x1s, y0s, y1s, 0, 62)
        for r in (1, 8, 20):
            allowed = nav.nodes_in(x0s - r, x1s + r, y0s - r, y1s + r, 0, 62)
            dd = nav.dist_from(src, allowed=allowed)
            reach = np.zeros((MX, MY), bool)
            q = nav.xyz[np.isfinite(dd)]
            reach[q[:, 0], q[:, 1]] = True
            loop = _ring_loop(t_['square'], r)
            flags = [reach[x, y] for x, y in loop]
            seg = _segments(flags)
            ex[f'r{r}'] = {'open_share': _r(np.mean(flags), 3), 'exits': len(seg),
                           'narrowest': int(min(seg)) if seg else 0, 'total_width': int(sum(seg))}
        sq['exits'] = ex
        # min vertex cut between the square and the ring 40 outside it (cells a team must fill to seal the spawn)
        box = nav.nodes_in(x0s - 40, x1s + 40, y0s - 40, y1s + 40, 0, 62)
        q = nav.xyz[box]
        dq = np.maximum(np.maximum(np.maximum(x0s - q[:, 0], q[:, 0] - x1s), np.maximum(y0s - q[:, 1],
                                                                                       q[:, 1] - y1s)), 0)
        sq['exit_min_cut'] = _flow_width(nav, box, dq == 0, dq >= 39)
        sq['sealable'] = bool(sq['exit_min_cut'] <= 10)

    # exposure from the platform edge (kit calibrated model, fog ignored)
    from .babel_checks import spawn_exposure
    e = spawn_exposure(solid, (bx, by), params, 'calibrated')
    sq['platform_viewers_mean'] = e['viewers_per_spot_mean']
    sq['platform_viewers_max'] = e['viewers_max']
    sq['platform_hidden_pct'] = e['hidden_pct']

    # exposure from ground (fog range 128): own tower zone x 168-211 / 300-343 (where attackers stand) and the
    # centre ground under the platform
    heads = np.array([(x + .5, y + .5, float(top[x, y]) - HEAD) for x in range(x0s, x1s + 1, 2)
                      for y in range(y0s, y1s + 1, 2)])
    tz = (cx0 - 38, cx0 + 5) if s > 0 else (cx1 - 5, cx1 + 38)                 # kit babel_checks tower zone
    e_front = _grid_eyes(top, tz, (py0, py1), 4, 8)
    e_centre = _grid_eyes(top, (cx0 + 6, cx1 - 5), (py0, py1), 8, 8)
    vf = los_any(opaque, e_front, heads)
    vc = los_any(opaque, e_centre, heads)
    sq['seen_from_tower_zone_ground_share'] = _r((vf > 0).mean(), 3)
    sq['seen_from_tower_zone_ground_viewers_mean'] = _r(vf.mean())
    sq['seen_from_centre_ground_share'] = _r((vc > 0).mean(), 3)

    # distance: walking steps spawn -> own platform end ground
    if nav is not None:
        if d_spawn is None:
            d_spawn = nav.dist_from(nav.nodes_in(x0s, x1s, y0s, y1s, 0, 62))
        endn = nav.nodes_in(t_['end'][0], t_['end'][1], py0, py1, 0, 62)
        v = d_spawn[endn] if len(endn) else np.array([np.inf])
        sq['steps_to_own_end'] = float(v.min()) if np.isfinite(v).any() else None      # from the nearest spot
        # from every spawn spot (topmost cell, every 2): median steps and median detour vs the straight x distance
        back = nav.dist_from(endn, reverse=True) if len(endn) else np.full(nav.G.shape[0], np.inf)
        st_, det = [], []
        for x in range(x0s, x1s + 1, 2):
            for y in range(y0s, y1s + 1, 2):
                i = nav.idx[x, y, int(top[x, y])] if top[x, y] < 63 else -1
                if i >= 0 and np.isfinite(back[i]):
                    st_.append(back[i])
                    det.append(back[i] / max(abs(x - (t_['end'][0] if s > 0 else t_['end'][1])), 1))
        sq['steps_to_own_end_median'] = _r(np.median(st_), 1) if st_ else None
        sq['detour_to_own_end_median'] = _r(np.median(det), 2) if det else None
        sq['spots_reaching_own_end_share'] = _r(len(st_) / 441, 3)
    sq['straight_to_own_end'] = horiz
    at = _box(top, t_['end'][0], t_['end'][1], py0, py1).astype(int)
    sq['anchor_minus_spawn_height'] = _r(t.mean() - at.mean())          # > 0: anchor ground is higher
    return sq


# =============================================================================================== front / tower zone

def front_metrics(solid, F, nav, team, params, opaque, d_spawn, floor, enemy_team):
    t_ = team
    top, obj, obj_h, water = F['top'], F['obj'], F['obj_h'], F['water']
    pz = params['platform_z']
    (x0, x1), (y0, y1) = params['platform_x'], params['platform_y']
    fx0, fx1 = t_['front']
    b0, b1 = t_['band']
    s = t_['s']
    bt = top[fx0:fx1 + 1, b0:b1 + 1].astype(int)
    H = (63 - bt).astype(float)
    prof = H.mean(axis=1)                       # along x (west -> east)
    xs = np.arange(fx0, fx1 + 1)
    toward = (xs - fx0) if s > 0 else (fx1 - xs)
    slope = float(np.polyfit(toward, prof, 1)[0]) * 10 if len(xs) > 2 else 0.0
    st = _box(top, *t_['square']).astype(int)
    ct = top[x0 + 6:x1 - 4, y0:y1 + 1].astype(int)
    wb = water[fx0:fx1 + 1, b0:b1 + 1]
    low = (bt > floor + 19)                      # >= 20 below the spawn floor (lethal drop) or water far below
    ground = ~wb & ~low
    R = {'profile_h_every4': [round(float(v), 1) for v in prof[::4]] if s > 0 else
         [round(float(v), 1) for v in prof[::-1][::4]],
         'h_mean': _r(H.mean()), 'slope_per10_toward_platform': _r(slope),
         'raised_vs_spawn': _r((63 - bt).mean() - (63 - st).mean()),
         'raised_vs_centre': _r((63 - bt).mean() - (63 - np.median(ct))),
         'flat_share': _r((np.abs(bt - np.median(bt)) <= 1).mean(), 3),
         'water_share': _r(wb.mean(), 3), 'lowland_share': _r(low.mean(), 3)}
    # land width through the corridor at each x
    gmap = (top < 62) & (top <= floor + 19)
    widths = []
    for x in range(fx0, fx1 + 1):
        col = gmap[x]
        ys = np.nonzero(col[b0:b1 + 1])[0]
        if not len(ys):
            widths.append(0)
            continue
        yc = b0 + ys[np.argmin(np.abs(ys + b0 - t_['base'][1]))]
        a = yc
        while a > 0 and col[a - 1]:
            a -= 1
        b = yc
        while b < MY - 1 and col[b + 1]:
            b += 1
        widths.append(b - a + 1)
    R['land_width_min'] = int(min(widths))
    R['land_width_p50'] = _r(np.median(widths), 1)
    # objects
    ob = obj[fx0:fx1 + 1, b0:b1 + 1]
    R['object_share'] = _r(ob.mean(), 3)
    oh = obj_h[fx0:fx1 + 1, b0:b1 + 1][ob]
    R['object_h'] = _stats(oh)
    win = obj[max(fx0 - 10, 0):fx1 + 11, max(b0 - 10, 0):b1 + 11]
    lab, n = ndi.label(win, structure=np.ones((3, 3)))
    inner = lab[(fx0 - max(fx0 - 10, 0)):(fx0 - max(fx0 - 10, 0)) + (fx1 - fx0 + 1),
                (b0 - max(b0 - 10, 0)):(b0 - max(b0 - 10, 0)) + (b1 - b0 + 1)]
    ids = np.unique(inner[inner > 0])
    sizes = ndi.sum(np.ones_like(lab), lab, ids) if len(ids) else np.array([])
    R['objects'] = int((sizes >= 4).sum()) if len(ids) else 0
    R['object_footprint'] = _stats(sizes[sizes >= 4]) if len(ids) else {'n': 0}
    free = ~ob & ground
    sec = [free[i:i + 8].mean() for i in range(0, free.shape[0], 8)]
    R['free_share'] = _r(free.mean(), 3)
    R['free_share_min_section8'] = _r(min(sec), 3)
    freemap = ~obj & (top < 62) & (top <= floor + 19)
    edt = ndi.distance_transform_edt(freemap)
    R['largest_empty_diam'] = _r(min(2 * edt[fx0:fx1 + 1, b0:b1 + 1].max(), 64), 1)
    # build gap
    an = top[t_['end'][0]:t_['end'][1] + 1, y0:y1 + 1].astype(int)
    R['anchor_top_mean'] = _r(an.mean())
    R['anchor_blocks_to_platform'] = _r(an.mean() - (pz + 1))
    R['anchor_water_cols'] = int((an >= 62).sum())
    if nav is not None:
        near = nav.nodes_in(x0 - 12 if s > 0 else x1 - 5, x0 + 5 if s > 0 else x1 + 12, y0 - 12, y1 + 12, 0, 62)
        rch = near[np.isfinite(d_spawn[near])] if len(near) else near
        zmin = int(nav.xyz[rch, 2].min()) if len(rch) else None
        R['highest_walkable_near_end_z'] = zmin
        R['build_gap_blocks'] = (zmin - (pz + 1)) if zmin is not None else None
        R['platform_reachable_on_foot'] = bool(zmin is not None and zmin <= pz + 2)
    # sightlines along the front: free horizontal LOS from sampled walkable front cells
    if nav is not None:
        cand = nav.nodes_in(fx0, fx1, b0, b1, 0, 61)
        cand = cand[np.isfinite(d_spawn[cand])] if len(cand) else cand
        smp = _sample(cand, 300)
        if len(smp):
            o = nav.xyz[smp].astype(float)
            o = np.column_stack([o[:, 0] + .5, o[:, 1] + .5, o[:, 2] - EYE])
            L = free_rays(opaque, o)
            ix = 0 if s > 0 else N_DIRS // 2                                 # toward the platform
            R['los_toward_platform_mean'] = _r(L[:, ix].mean(), 1)
            R['los_along_x_mean'] = _r(L[:, [0, N_DIRS // 2]].mean(), 1)
            R['los_16dir_mean'] = _r(L.mean(), 1)
            # share of front cells visible from the enemy tower zone ground (enemy anchor + 36 in front of it)
            ea = enemy_team['end']
            exr = (ea[0], ea[0] + 36) if s > 0 else (ea[1] - 36, ea[1])
            exr = (max(exr[0], 0), min(exr[1], MX - 1))
            eyes = _grid_eyes(top, exr, (y0, y1), 6, 8)
            heads = np.column_stack([o[:, 0], o[:, 1], o[:, 2] + EYE - HEAD])
            v = los_any(opaque, eyes, heads)
            R['seen_from_enemy_tower_zone_share'] = _r((v > 0).mean(), 3)
    return R


# =============================================================================================== centre

def centre_metrics(solid, F, nav, params, opaque, d_spawns, teams):
    top, obj, obj_h, water = F['top'], F['obj'], F['obj_h'], F['water']
    pz = params['platform_z']
    (x0, x1), (y0, y1) = params['platform_x'], params['platform_y']
    R = {}
    # under-platform strip
    st = top[x0 + 6:x1 - 4, y0:y1 + 1].astype(int)
    so = obj[x0 + 6:x1 - 4, y0:y1 + 1]
    under = top[x0:x1 + 1, y0:y1 + 1].astype(int)
    R['strip'] = {'ground_z_median': _r(np.median(st), 1), 'water_share': _r((st >= 62).mean(), 3),
                  'object_share': _r(so.mean(), 3), 'object_h': _stats(obj_h[x0 + 6:x1 - 4, y0:y1 + 1][so]),
                  'highest_z_under_platform': int(under.min()),
                  'min_gap_to_platform': int(under.min() - (pz + 1)),
                  'cols_within_8_of_platform': int((under <= pz + 8).sum())}
    # central zone
    cx0, cx1, cy0, cy1 = CENTRE_BOX
    zt = top[cx0:cx1 + 1, cy0:cy1 + 1]
    zw = water[cx0:cx1 + 1, cy0:cy1 + 1]
    zo = obj[cx0:cx1 + 1, cy0:cy1 + 1]
    zl = ~zw
    area = zt.size
    Z = {'land_share': _r(zl.mean(), 3), 'object_share': _r(zo.mean(), 3),
         'built_volume_per_col': _r(np.where(zo, obj_h[cx0:cx1 + 1, cy0:cy1 + 1], 0).sum() / area, 3)}
    lab, n = ndi.label(obj, structure=np.ones((3, 3)))
    ids = np.unique(lab[cx0:cx1 + 1, cy0:cy1 + 1])
    ids = ids[ids > 0]
    sizes = ndi.sum(np.ones_like(lab), lab, ids) if len(ids) else np.array([])
    big = sizes[sizes >= 4] if len(ids) else np.array([])
    Z['objects'] = int(len(big))
    Z['objects_per_10k'] = _r(len(big) / area * 10000, 2)
    Z['object_footprint'] = _stats(big)
    hts = ndi.maximum(obj_h, lab, ids) if len(ids) else np.array([])
    Z['object_height'] = _stats(np.asarray(hts)[sizes >= 4]) if len(ids) else {'n': 0}
    freemap = ~obj & ~water
    edt = ndi.distance_transform_edt(freemap)
    ze = edt[cx0:cx1 + 1, cy0:cy1 + 1]
    zf = freemap[cx0:cx1 + 1, cy0:cy1 + 1]
    Z['free_share'] = _r(zf.mean(), 3)
    ridge = zf & (ze >= ndi.maximum_filter(ze, size=3)) & (ze >= 1)
    gaps = 2 * ze[ridge]
    Z['gap_width'] = {'p10': _pct(gaps, 10), 'p50': _pct(gaps, 50), 'p90': _pct(gaps, 90)}
    Z['largest_empty_diam'] = _r(min(2 * ze.max(), 128), 1)
    if nav is not None:
        reach = np.zeros(nav.G.shape[0], bool)
        for d in d_spawns:
            reach |= np.isfinite(d)
        zn = nav.nodes_in(cx0, cx1, cy0, cy1, 0, 62)
        zr = zn[reach[zn]]
        p = nav.xyz[zr]
        if len(p):
            # indoor: a solid voxel above the 3-voxel headroom in the same column
            cs = np.cumsum(solid, axis=2, dtype=np.int16)
            roofed = (p[:, 2] >= 4) & (cs[p[:, 0], p[:, 1], np.maximum(p[:, 2] - 4, 0)] > 0)
            Z['indoor_share'] = _r(roofed.mean(), 3)
            cols, cnt = np.unique(p[:, 0] * 512 + p[:, 1], return_counts=True)
            Z['multilevel_share'] = _r((cnt >= 2).mean(), 3)
            Z['walkable_col_share'] = _r(len(cols) / area, 3)
            hh = 63 - p[:, 2]
            Z['walk_height'] = {'p5': _pct(hh, 5), 'p50': _pct(hh, 50), 'p95': _pct(hh, 95)}
            # sightlines
            smp = _sample(zr, 400)
            o = nav.xyz[smp].astype(float)
            o = np.column_stack([o[:, 0] + .5, o[:, 1] + .5, o[:, 2] - EYE])
            L = free_rays(opaque, o)
            Z['los_mean'] = _r(L.mean(), 1)
            Z['los_p90'] = _r(np.percentile(L, 90), 1)
            heads = np.column_stack([o[:, 0], o[:, 1], o[:, 2] + EYE - HEAD])
            for t_ in teams:
                eyes = _grid_eyes(top, t_['end'], (y0, y1), 2, 4)
                v = los_any(opaque, eyes, heads)
                Z[f'seen_from_{t_["name"]}_end_share'] = _r((v > 0).mean(), 3)
            # high ground overlooking the platform ends: walkable cells within 40 of an end, >= 6 above its ground
            hg = []
            for t_ in teams:
                ex0, ex1 = t_['end']
                ag = float(np.median(top[ex0:ex1 + 1, y0:y1 + 1]))
                nn = nav.nodes_in(ex0 - 40, ex1 + 40, y0 - 40, y1 + 40, 0, 62)
                nn = nn[reach[nn]]
                q = nav.xyz[nn]
                hi = q[q[:, 2] <= ag - 6]
                hg.append(len(np.unique(hi[:, 0] * 512 + hi[:, 1])) if len(hi) else 0)
            Z['high_ground_cols_near_ends'] = hg
            # crossing width (max vertex-disjoint W->E paths inside the zone)
            src = p[:, 0] <= cx0 + 3
            snk = p[:, 0] >= cx1 - 3
            Z['crossing_width'] = _flow_width(nav, zr, src, snk)
            # lanes at x = 256
            on = np.zeros(MY, bool)
            q = nav.xyz[zn[reach[zn]]]
            q = q[(q[:, 0] == 256) | (q[:, 0] == 255)]
            on[q[:, 1]] = True
            runs = _runs_1d(on[cy0:cy1 + 1])
            Z['lanes_at_axis'] = int(sum(1 for r in runs if r >= 3))
            Z['lane_widths_at_axis'] = sorted(runs, reverse=True)[:8]
    R['zone'] = Z
    return R


def route_metrics(nav, params, d_spawns, teams):
    """Spawn -> enemy spawn steps, whole-map crossing width and centre-avoiding flank route (kit flank band)."""
    R = {}
    if nav is None:
        return R
    half = params['spawn_half']
    b, r = teams
    redsq = nav.nodes_in(*r['square'], 0, 62)
    d = d_spawns[0]
    v = d[redsq] if len(redsq) else np.array([np.inf])
    direct = float(v.min()) if np.isfinite(v).any() else None
    R['spawn_to_enemy_spawn_steps'] = direct
    p = nav.xyz
    best = None
    for side, sgn in (('north', -1), ('south', 1)):
        dy = (p[:, 1] - 256) * sgn
        band = (p[:, 0] >= 176) & (p[:, 0] <= 336)
        allowed = np.nonzero(~band | ((dy >= 130) & (dy <= 210)))[0]
        df = nav.dist_from(nav.nodes_in(*b['square'], 0, 62), allowed=allowed)
        w = df[redsq] if len(redsq) else np.array([np.inf])
        val = float(w.min()) if np.isfinite(w).any() else None
        R[f'flank_{side}_steps'] = val
        if val is not None:
            best = val if best is None else min(best, val)
    R['flank_exists'] = best is not None
    R['flank_ratio'] = _r(best / direct, 2) if (best is not None and direct) else None
    reach = np.isfinite(d_spawns[0]) | np.isfinite(d_spawns[1])
    bx, rx = b['base'][0], r['base'][0]
    nodes = nav.nodes_in(bx + half + 1, rx - half - 1, 0, MY - 1, 0, 62)
    nodes = nodes[reach[nodes]]
    q = nav.xyz[nodes]
    R['map_crossing_width'] = _flow_width(nav, nodes, q[:, 0] <= bx + half + 3, q[:, 0] >= rx - half - 3)
    return R


# =============================================================================================== whole map

SYM_TRANSFORMS = {
    'x512': lambda a: a[(512 - np.arange(512)) % 512],
    'x511': lambda a: a[::-1],
    'y512': lambda a: a[:, (512 - np.arange(512)) % 512],
    'y511': lambda a: a[:, ::-1],
    'point511': lambda a: a[::-1, ::-1],
    'point512': lambda a: a[(512 - np.arange(512)) % 512][:, (512 - np.arange(512)) % 512],
}


def symmetry_type(solid, exact=0.02, approx=0.10):
    """Mismatch share (xor / union of solid voxels above z 62) for each mirror/point transform; best type.
    'x' types are the Babel team axis; 'y' only = the map is mirrored across the wrong axis (rotated);
    'point' = 180 degree rotational symmetry (teams swap sides and north/south)."""
    s = solid[:, :, :62]
    res = {}
    for k, f in SYM_TRANSFORMS.items():
        m = f(s)
        res[k] = round(float((s ^ m).sum() / max((s | m).sum(), 1)), 4)
    best = min(res, key=res.get)
    v = res[best]
    kind = best if v <= exact else (best + '~' if v <= approx else 'none')
    return {'type': kind, 'best': best, 'best_mismatch': v, 'mismatch': res}


def map_context(solid, F):
    top, water = F['top'], F['water']
    land = ~water
    hh = (63 - top[land]).astype(float)
    return {'land_share': _r(land.mean(), 3),
            'land_height': {'p10': _pct(hh, 10), 'p50': _pct(hh, 50), 'p90': _pct(hh, 90)} if hh.size else None,
            'void_cols': int((top >= 64).sum()), 'symmetry': symmetry_type(solid)}


# =============================================================================================== driver

def _avg(a, b):
    """Mirrored average of two per-team dicts (numbers averaged, bools OR-ed, lists/strings from team 0)."""
    if isinstance(a, dict) and isinstance(b, dict):
        return {k: _avg(a[k], b.get(k)) for k in a}
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) or bool(b)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return round((a + b) / 2, 3)
    if a is None or b is None:
        return a if b is None else b
    return a


def zone_profile(solid, params=BABEL_DEFAULT, nav=None, F=None, crossing=True):
    """All zone metrics -> JSON-able dict {'teams': {blue: {...}, red: {...}}, 'avg': {...}, 'centre', 'routes',
    'map'}. nav: a kit babel_checks.Nav built with rules='hc' and FALL_SAFE_MAX (built here if None)."""
    if nav is None:
        from .babel_checks import Nav
        nav = Nav(solid, FALL_SAFE_MAX, 'hc')
    if F is None:
        F = fields(solid)
    opaque = _opaque(solid, params)
    teams = team_geometry(params)
    d_spawns = [nav.dist_from(nav.nodes_in(*t['square'], 0, 62)) for t in teams]
    per = {}
    for k, t in enumerate(teams):
        sp = spawn_metrics(solid, F, nav, t, params, opaque, d_spawns[k])
        fr = front_metrics(solid, F, nav, t, params, opaque, d_spawns[k], sp['floor_z'], teams[1 - k])
        per[t['name']] = {'spawn': sp, 'front': fr}
    from .babel_checks import anchor_checks
    anc = anchor_checks(solid, nav, params)
    for t in teams:
        per[t['name']]['front']['anchor_enemy_face'] = anc[t['name']]
    names = [t['name'] for t in teams]
    out = {'teams': per, 'avg': _avg(per[names[0]], per[names[1]]),
           'centre': centre_metrics(solid, F, nav, params, opaque, d_spawns, teams) if crossing else None,
           'routes': route_metrics(nav, params, d_spawns, teams) if crossing else None,
           'map': map_context(solid, F)}
    return out


def classify(zp):
    """Map class from metrics (rule stated in docs/babel_zone_study.md):
    sky_bridge  - front lowland share (>= 20 below the spawn floor) >= 0.5 on average
    island      - otherwise, map land share < 0.5
    ground      - otherwise
    assist flag - build gap from the highest walkable cell near a platform end <= 4 blocks for either team
    stock_fit   - both stock spawn squares have < 50 % water and < 50 % roof columns (roof = a room-height air gap
                  under the topmost voxel with a dry floor <= 20 below; decks over drops/water do not count)."""
    a = zp['avg']
    if (a['front'].get('lowland_share') or 0) >= 0.5:
        cls = 'sky_bridge'
    elif zp['map']['land_share'] < 0.5:
        cls = 'island'
    else:
        cls = 'ground'
    gaps = [zp['teams'][t]['front'].get('build_gap_blocks') for t in zp['teams']]
    assist = any(g is not None and g <= 4 for g in gaps)
    fit = all(zp['teams'][t]['spawn']['water_cols'] < 0.5 * 41 * 41 and
              zp['teams'][t]['spawn']['roof_cols'] < 0.5 * 41 * 41 for t in zp['teams'])
    return {'class': cls, 'assist': assist, 'stock_fit': fit}
