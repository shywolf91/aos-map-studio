"""Preliminary walkability / route analysis from pyspades 1.4.2 movement rules (world_c.cpp).

Model (derived from source, NOT playtested - results are labelled preliminary):
  * A player STANDS on solid voxel (x, y, z) when the voxels above it are air:
      3 air voxels (z-1..z-3) -> standing;  exactly 2 -> crouch-only (slow, cost x3.3).
    Out-of-map above z = 0 counts as air. Water: a column whose z = 62 is air has its floor at the
    z = 63 water plane (players wade there); water nodes are excluded when water_damage > 0.
  * Moves to the 8 neighbouring columns:
      level / drop   : drop of d voxels needs the target column clear from the head height down
                       (it lands on the first solid below). d >= FALL_LETHAL is excluded,
                       d >= FALL_DAMAGE is flagged.
      step up 1      : boxclipmove auto-climb (walking, not sprinting / crouching)
      up 2           : 'jump' edge - jump apex ~1.6 + auto-climb. Needs in-client confirmation.
      diagonal moves : only on level ground, and both orthogonal columns must be clear (no corner
                       cutting through walls).
  * Building, digging and grenades are NOT modelled: a route here is a route with no player
    construction. That is exactly what shortcut checks need (Push bridges, Babel tower).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

from .validate import FALL_DAMAGE_FROM, FALL_LETHAL_FROM

UP_MAX = 2            # 1 = auto-step, 2 = jump+climb (preliminary)
STEP_COST = 0.5
JUMP_COST = 2.0
CROUCH_MULT = 3.3     # move_player: crouch speed factor 0.3


def air_above(solid: np.ndarray) -> np.ndarray:
    """A[x, y, z] = number of consecutive air voxels directly above z (z-1, z-2, ...), capped 64.
    Above the map top counts as air."""
    X, Y, Z = solid.shape
    A = np.zeros(solid.shape, np.int16)
    run = np.full((X, Y), 64, np.int16)                       # above z = 0 is open sky
    for z in range(Z):
        A[:, :, z] = run
        run = np.where(solid[:, :, z], 0, np.minimum(run + 1, 64))
    return A


@dataclass
class NavGraph:
    node_xyz: np.ndarray        # (N, 3) floor voxel of each node
    crouch: np.ndarray          # (N,) bool: crouch-only node
    water: np.ndarray           # (N,) bool
    index: np.ndarray           # [x, y, z] -> node id or -1
    edges: tuple                # (src, dst, cost, kind) arrays; kind 0 level 1 step 2 jump 3 drop 4 damaging drop
    matrix: object

    def node(self, x, y, z=None):
        """Node id standing on column x, y (topmost node if z is None, else that floor z)."""
        if z is not None:
            return int(self.index[x, y, z])
        ids = self.index[x, y][self.index[x, y] >= 0]
        return int(ids[0]) if ids.size else -1


def build(solid: np.ndarray, water_damage: bool = True, region=None) -> NavGraph:
    """region = (x0, y0, x1, y1) inclusive to limit work; default = bounding box of land."""
    s = solid.copy()
    s[:, :, 63] = True
    if region is None:
        land = s[:, :, :63].any(axis=2)
        xs, ys = np.nonzero(land)
        region = (max(xs.min() - 2, 0), max(ys.min() - 2, 0), min(xs.max() + 2, 511), min(ys.max() + 2, 511))
    x0, y0, x1, y1 = region
    sub = s[x0:x1 + 1, y0:y1 + 1]
    A = air_above(sub)
    is_water_col = ~sub[:, :, 62]
    node = sub & (A >= 2)
    water = np.zeros_like(node)
    water[:, :, 63] = is_water_col & node[:, :, 63]
    node[:, :, 63] &= is_water_col                       # z=63 only standable where it is open water
    if water_damage:
        node &= ~water
    idx = -np.ones(sub.shape, np.int32)
    xyz = np.argwhere(node)
    idx[tuple(xyz.T)] = np.arange(len(xyz), dtype=np.int32)
    X, Y, Z = sub.shape
    src_l, dst_l, cost_l, kind_l = [], [], [], []
    crouch_node = node & (A < 3)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            diag = dx != 0 and dy != 0
            sxs = slice(max(0, -dx), X - max(0, dx)); txs = slice(max(0, dx), X - max(0, -dx))
            sys_ = slice(max(0, -dy), Y - max(0, dy)); tys = slice(max(0, dy), Y - max(0, -dy))
            n_s, A_s = node[sxs, sys_], A[sxs, sys_]
            n_t_all, A_t_all = node[txs, tys], A[txs, tys]
            if diag:
                o1 = A[txs, sys_]          # column (x+dx, y)
                o2 = A[sxs, tys]           # column (x, y+dy)
            dz_range = [0] if diag else range(-UP_MAX, FALL_LETHAL_FROM)
            for dz in dz_range:
                # target floor z' = z + dz  (dz < 0 is UP)
                if dz >= 0:
                    zs = slice(0, Z - dz); zt = slice(dz, Z)
                else:
                    zs = slice(-dz, Z); zt = slice(0, Z + dz)
                ok = n_s[:, :, zs] & n_t_all[:, :, zt]
                if not ok.any():
                    continue
                As, At = A_s[:, :, zs], A_t_all[:, :, zt]
                if dz < 0:
                    ok &= (As >= 3 - dz) & (At >= 3)      # climb: room above source, stand on target
                elif dz > 0:
                    ok &= At >= dz + 3                    # target column clear from head height down
                if diag:
                    ok &= (o1[:, :, zs] >= 3) & (o2[:, :, zs] >= 3) & (As >= 3) & (At >= 3)
                if not ok.any():
                    continue
                pts = np.argwhere(ok)
                sx = pts[:, 0] + sxs.start; sy = pts[:, 1] + sys_.start; sz = pts[:, 2] + zs.start
                tx = sx + dx; ty = sy + dy; tz = sz + dz
                s_id = idx[sx, sy, sz]; t_id = idx[tx, ty, tz]
                base = 1.4142 if diag else 1.0
                mult = np.where(crouch_node[sx, sy, sz] | crouch_node[tx, ty, tz], CROUCH_MULT, 1.0)
                if dz == 0:
                    kind, extra = 0, 0.0
                elif dz == -1:
                    kind, extra = 1, STEP_COST
                elif dz < -1:
                    kind, extra = 2, JUMP_COST
                elif dz < FALL_DAMAGE_FROM:
                    kind, extra = 3, 0.2 * dz
                else:
                    kind, extra = 4, 5.0 + dz            # damaging drop: allowed but expensive
                src_l.append(s_id); dst_l.append(t_id)
                cost_l.append((base * mult + extra).astype(np.float32))
                kind_l.append(np.full(len(s_id), kind, np.int8))
    src = np.concatenate(src_l); dst = np.concatenate(dst_l)
    cost = np.concatenate(cost_l); kind = np.concatenate(kind_l)
    n = len(xyz)
    M = coo_matrix((cost, (src, dst)), shape=(n, n)).tocsr()
    full_idx = -np.ones(solid.shape, np.int32)
    full_idx[x0:x1 + 1, y0:y1 + 1] = idx
    xyz_full = xyz + np.array([x0, y0, 0])
    return NavGraph(xyz_full, crouch_node[tuple(xyz.T)], water[tuple(xyz.T)], full_idx,
                    (src, dst, cost, kind), M)


def distances(g: NavGraph, sources):
    """Shortest path cost from any of the source node ids (list) to every node."""
    sources = [s for s in sources if s >= 0]
    if not sources:
        return np.full(len(g.node_xyz), np.inf)
    return dijkstra(g.matrix, directed=True, indices=sources, min_only=True)


def path(g: NavGraph, source, target):
    d, pred = dijkstra(g.matrix, directed=True, indices=source, return_predecessors=True)
    if not np.isfinite(d[target]):
        return None, np.inf
    p = [target]
    while p[-1] != source:
        p.append(pred[p[-1]])
    return [tuple(int(v) for v in g.node_xyz[i]) for i in p[::-1]], float(d[target])


def reach_map(g: NavGraph, dist, shape=(512, 512)):
    """2D map: min path cost to any node in each column (inf = unreachable)."""
    out = np.full(shape, np.inf, np.float32)
    xy = g.node_xyz[:, :2]
    np.minimum.at(out, (xy[:, 0], xy[:, 1]), dist.astype(np.float32))
    return out


# ---------------------------------------------------------------- reports

def zone_nodes(g: NavGraph, cx, cy, half):
    xy = g.node_xyz
    sel = (np.abs(xy[:, 0] - cx) <= half) & (np.abs(xy[:, 1] - cy) <= half)
    # spawning uses the TOPMOST solid voxel of a column -> keep only each column's top node
    ids = np.nonzero(sel)[0]
    best = {}
    for i in ids:
        k = (int(xy[i, 0]), int(xy[i, 1]))
        if k not in best or xy[i, 2] < xy[best[k], 2]:
            best[k] = i
    return list(best.values())


def babel_route_check(solid: np.ndarray, params=None, water_damage=True):
    """Standard Babel must NOT let players reach the platform without building.
    Adds the script platform (z = 1) to a copy of the map, then routes from both spawn zones.
    Also reports the 'build gap': shortest straight-line distance (voxels) from any spot a team
    can walk to, to the platform's top surface - the size of the construction challenge."""
    from .validate import BABEL_DEFAULT
    p = params or BABEL_DEFAULT
    (x0, x1), (y0, y1) = p['platform_x'], p['platform_y']
    s = solid.copy()
    s[x0:x1 + 1, y0:y1 + 1, p['platform_z']] = True
    g = build(s, water_damage=water_damage)
    plat = (g.node_xyz[:, 0] >= x0) & (g.node_xyz[:, 0] <= x1) & (g.node_xyz[:, 1] >= y0) & \
           (g.node_xyz[:, 1] <= y1) & (g.node_xyz[:, 2] == p['platform_z'])
    out = {}
    for team, (bx, by) in zip(('team1', 'team2'), p['bases']):
        src = zone_nodes(g, bx, by, p['spawn_half'])
        d = distances(g, src)
        reach = np.isfinite(d)
        xyz = g.node_xyz[reach & ~plat].astype(float)
        ddx = np.maximum(0, np.maximum(x0 - xyz[:, 0], xyz[:, 0] - x1))
        ddy = np.maximum(0, np.maximum(y0 - xyz[:, 1], xyz[:, 1] - y1))
        ddz = np.maximum(0, xyz[:, 2] - (p['platform_z'] - 1))       # stand on platform = floor z 1
        gap = np.sqrt(ddx ** 2 + ddy ** 2 + ddz ** 2)
        k = int(np.argmin(gap)) if len(gap) else -1
        out[team] = {'spawn_columns': len(src), 'reachable_nodes': int(reach.sum()),
                     'platform_reachable_without_building': bool(reach[plat].any()),
                     'build_gap_voxels': round(float(gap[k]), 1) if k >= 0 else None,
                     'gap_from': tuple(int(v) for v in xyz[k]) if k >= 0 else None,
                     'gap_vertical': int(ddz[k]) if k >= 0 else None,
                     'gap_horizontal': round(float(np.hypot(ddx[k], ddy[k])), 1) if k >= 0 else None}
    return out


def ctf_route_parity(solid: np.ndarray, spawns: dict, targets: dict, water_damage=True):
    """spawns: team -> list of (x, y); targets: team -> (x, y) of what that team must reach
    (e.g. enemy intel). Returns walk cost (no building) per team and the ratio."""
    g = build(solid, water_damage=water_damage)
    res = {}
    for team, pts in spawns.items():
        src = [g.node(x, y) for x, y in pts]
        d = distances(g, src)
        tx, ty = targets[team]
        t = g.node(tx, ty)
        res[team] = round(float(d[t]), 1) if t >= 0 else None
    vals = [v for v in res.values() if v is not None and np.isfinite(v)]
    res['ratio'] = round(max(vals) / min(vals), 3) if len(vals) == 2 and min(vals) > 0 else None
    return res
