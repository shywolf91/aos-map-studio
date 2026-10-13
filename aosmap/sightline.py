"""Babel spawn exposure: how much of each team's spawn zone a player standing on the platform can see.

Motivation: the aloha.pk "Babel map rotation guide" (v1.8, 2023) names spawn camping from the platform as the main
reason Babel maps fail ("spawn camp hell", "empties the server"); maps survive when trees/walls/buildings/terrain
cover the spawn from the platform, and spawns that are too close to or too far below the platform are steep-angle
camping targets.

Model (geometry only, no player models / fog): viewers are eyes on the platform's walkable top
(z = platform_z - 2.4) sampled along its perimeter; targets are player heads in the spawn zone
(floor = topmost solid voxel per stock babel_script get_spawn_location; head = floor - 2.2).
A target is exposed if any viewer has an unobstructed straight line to it (ray marched at 0.25 voxel; the map plus
the script platform are opaque; z < 0 is open sky). Fog distance is ignored, so this is an upper bound on exposure.
"""
from __future__ import annotations

import numpy as np

PLATFORM = {'x': (206, 305), 'y': (240, 271), 'z': 1}
BASES = ((118, 256), (394, 256))


def spawn_points(solid, base, half=20, step=2):
    pts = []
    for x in range(base[0] - half, base[0] + half + 1, step):
        for y in range(base[1] - half, base[1] + half + 1, step):
            col = solid[x, y]
            z = int(np.argmax(col)) if col.any() else 63
            pts.append((x + 0.5, y + 0.5, z - 2.2, z))
    return np.array(pts, float)


def platform_viewers(platform=PLATFORM, step=4, side=None):
    (x0, x1), (y0, y1), z = platform['x'], platform['y'], platform['z']
    v = []
    for x in range(x0, x1 + 1, step):
        v += [(x + 0.5, y0 + 0.5), (x + 0.5, y1 + 0.5)]
    for y in range(y0, y1 + 1, step):
        v += [(x0 + 0.5, y + 0.5), (x1 + 0.5, y + 0.5)]
    v = np.unique(np.array(v), axis=0)
    if side == 'west':
        v = v[v[:, 0] < 256]
    elif side == 'east':
        v = v[v[:, 0] > 256]
    return np.column_stack([v, np.full(len(v), z - 2.4)])


def _visible(opaque, a, b, step=0.25):
    """a: (N,3) eyes, b: (N,3) targets -> bool (N,) line of sight."""
    d = b - a
    L = np.linalg.norm(d, axis=1)
    n = int(np.ceil(L.max() / step)) + 1
    vis = np.ones(len(a), bool)
    for k in range(1, n - 1):
        t = np.minimum(k * step / np.maximum(L, 1e-6), 1.0)
        p = a + d * t[:, None]
        active = (t < 0.995) & vis
        if not active.any():
            break
        xi = np.floor(p[:, 0]).astype(int); yi = np.floor(p[:, 1]).astype(int); zi = np.floor(p[:, 2]).astype(int)
        inside = (xi >= 0) & (xi < 512) & (yi >= 0) & (yi < 512) & (zi >= 0) & (zi < 64)
        hit = np.zeros(len(a), bool)
        hit[inside] = opaque[xi[inside], yi[inside], zi[inside]]
        vis &= ~(hit & active)
    return vis


def spawn_exposure(solid, base, platform=PLATFORM, viewer_step=4, spawn_step=2, chunk=40000):
    opaque = solid.copy()
    (x0, x1), (y0, y1), pz = platform['x'], platform['y'], platform['z']
    opaque[x0:x1 + 1, y0:y1 + 1, pz] = True
    T = spawn_points(solid, base, step=spawn_step)
    V = platform_viewers(platform, viewer_step)
    # a target column's own air above the floor is the player's space: make sure it is not treated as cover
    ia, ib = np.meshgrid(np.arange(len(V)), np.arange(len(T)), indexing='ij')
    ia, ib = ia.ravel(), ib.ravel()
    vis = np.zeros(len(ia), bool)
    for s in range(0, len(ia), chunk):
        sl = slice(s, s + chunk)
        vis[sl] = _visible(opaque, V[ia[sl]], T[ib[sl], :3])
    vis = vis.reshape(len(V), len(T))
    seen = vis.any(axis=0)
    floors = T[:, 3]
    horiz = np.array([np.hypot(max(0, x0 - tx, tx - x1 - 1), max(0, y0 - ty, ty - y1 - 1)) for tx, ty in T[:, :2]])
    angle = np.degrees(np.arctan2(floors - pz, np.maximum(horiz, 0.1)))
    return {'spawn_points': int(len(T)), 'exposed_pct': round(100.0 * seen.mean(), 1),
            'mean_viewers_per_point': round(float(vis.sum(axis=0).mean()), 1),
            'median_depression_angle_deg': round(float(np.median(angle)), 1),
            'median_floor_z': int(np.median(floors)), 'median_horizontal_dist': round(float(np.median(horiz)), 1)}


def babel_spawn_report(solid, platform=PLATFORM):
    return {('team1' if i == 0 else 'team2'): spawn_exposure(solid, b, platform) for i, b in enumerate(BASES)}
