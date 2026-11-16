"""Validation for Bloomhop Kingdom. python check.py OUTDIR"""
import sys, os, json, math, hashlib
from collections import deque
import numpy as np
from scipy import ndimage
sys.path.insert(0, os.path.dirname(__file__))
import vxlcore
from spec import SPEC


def stand_mask(S):
    st = np.zeros_like(S)
    st[:, :, 3:] = S[:, :, 3:] & ~S[:, :, 2:-1] & ~S[:, :, 1:-2] & ~S[:, :, 0:-3]
    return st


def bfs(S, st, cols, starts, max_drop=9, wade=True):
    """Returns dict node->cost (step counts). Moves: 8-neigh, up 1, down <= max_drop."""
    dist = {}
    dq = deque()
    for s in starts:
        dist[s] = 0; dq.append(s)
    while dq:
        x, y, z = dq.popleft()
        c = dist[(x, y, z)]
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                X, Y = x + dx, y + dy
                if not (0 <= X < 512 and 0 <= Y < 512):
                    continue
                for Z in cols[X][Y]:
                    if Z < z - 1 or Z > z + max_drop:
                        continue
                    if not wade and Z == 63:
                        continue
                    lo = min(z, Z) - 3
                    if S[X, Y, max(lo, 0):Z].any():
                        continue
                    if Z == z - 1 and S[x, y, max(z - 4, 0)]:
                        continue
                    k = (X, Y, Z)
                    if k not in dist:
                        dist[k] = c + 1; dq.append(k)
    return dist


def exposure(S, top, sq, plat):
    x0, x1, y0, y1 = plat
    eyes = []
    for x in range(x0, x1 + 1, 3):
        eyes += [(x + .5, y0 + .5, -1.0), (x + .5, y1 + .5, -1.0)]
    for y in range(y0, y1 + 1, 3):
        eyes += [(x0 + .5, y + .5, -1.0), (x1 + .5, y + .5, -1.0)]
    eyes = np.array(eyes)
    sx0, sx1, sy0, sy1 = sq
    heads = []
    for x in range(sx0, sx1 + 1, 2):
        for y in range(sy0, sy1 + 1, 2):
            heads.append((x + .5, y + .5, top[x, y] - 2.4))
    heads = np.array(heads)
    viewers = np.zeros(len(heads), int)
    for e in eyes:
        d = heads - e[None, :]
        L = np.linalg.norm(d, axis=1)
        n = int(L.max() / 0.5) + 1
        ts = np.linspace(0, 1, n)[None, :]
        P = e[None, None, :] + d[:, None, :] * ts[..., None]
        px = np.floor(P[..., 0]).astype(int); py = np.floor(P[..., 1]).astype(int); pz = np.floor(P[..., 2]).astype(int)
        ok = (pz >= 0) & (pz < 64)
        # ignore samples within 1.5 voxels of the head
        near = (1 - ts) * L[:, None] < 1.5
        plat_hit = (pz == 1) & (px >= x0) & (px <= x1) & (py >= y0) & (py <= y1) & (ts * L[:, None] > 1.0)
        hit = np.zeros(px.shape, bool)
        hit[ok] = S[np.clip(px[ok], 0, 511), np.clip(py[ok], 0, 511), pz[ok]]
        hit &= ~near
        blocked = (hit | plat_hit).any(axis=1)
        viewers += ~blocked
    exposed = (viewers > 0).mean()
    return dict(exposed_pct=round(100 * exposed, 1), mean_viewers=round(float(viewers.mean()), 2),
                hidden_pct=round(100 * (1 - exposed), 1), eyes=len(eyes), spots=len(heads))


def main(d):
    rep = {}
    data = open(os.path.join(d, 'bloomhop_kingdom.vxl'), 'rb').read()
    S, C = vxlcore.decode(data)
    re = vxlcore.encode(S, C)
    rep['bytes'] = len(data); rep['sha256'] = hashlib.sha256(data).hexdigest()
    rep['reencode_identical'] = re == data
    rep['z63_solid_everywhere'] = bool(S[:, :, 63].all())
    lab, n = ndimage.label(S)
    grounded = set(np.unique(lab[:, :, 62:][S[:, :, 62:]]).tolist())
    objs = ndimage.find_objects(lab)
    fl = []
    for i, sl in enumerate(objs, start=1):
        if i in grounded or sl is None:
            continue
        fl.append(dict(bbox=[sl[0].start, sl[0].stop - 1, sl[1].start, sl[1].stop - 1, sl[2].start, sl[2].stop - 1],
                       voxels=int((lab[sl] == i).sum())))
    rep['floating_components'] = len(fl)
    rep['floating_min_dist_to_platform'] = None
    x0, x1, y0, y1 = SPEC['platform']
    if fl:
        dmin = 1e9
        for f in fl:
            bx0, bx1, by0, by1 = f['bbox'][:4]
            dx = max(x0 - bx1, bx0 - x1, 0); dy = max(y0 - by1, by0 - y1, 0)
            dmin = min(dmin, math.hypot(dx, dy))
        rep['floating_min_dist_to_platform'] = round(dmin, 1)
    rep['platform_volume_clear'] = not S[x0 - 1:x1 + 2, y0 - 1:y1 + 2, 0:4].any()
    top = np.argmax(S, axis=2)
    rep['ground_under_platform_ends'] = {'west_z': int(np.median(top[206:213, 240:272])), 'east_z': int(np.median(top[299:306, 240:272])),
                                         'land': bool(S[206:213, 240:272, 62].all() and S[299:306, 240:272, 62].all())}
    sq = []
    for (bx, by) in SPEC['bases']:
        sl = (slice(bx - 20, bx + 21), slice(by - 20, by + 21))
        t = top[sl]
        water = (~S[sl][:, :, 62]).sum()
        sq.append(dict(base=(bx, by), base_top=int(top[bx, by]), zmin=int(t.min()), zmax=int(t.max()),
                       flat_share=round(float((t == np.bincount(t.ravel()).argmax()).mean()), 2), water_columns=int(water)))
    rep['spawn_squares'] = sq
    tl = top[98:139, 236:277]; tr = top[373:414, 236:277][::-1]
    rep['spawn_mirror_equal'] = round(float((tl == tr).mean()), 3)
    mir = (S[:256] == S[256:][::-1]).mean()
    rep['solid_mirror_equal'] = round(float(mir), 4)
    # routes
    st = stand_mask(S)
    cols = [[np.nonzero(st[x, y])[0].tolist() for y in range(512)] for x in range(512)]
    res = {}
    for team, (bx, by) in enumerate(SPEC['bases']):
        sx = [(x, y, top[x, y]) for x in range(bx - 20, bx + 21, 4) for y in range(by - 20, by + 21, 4) if st[x, y, top[x, y]]]
        safe = bfs(S, st, cols, sx, max_drop=9)
        anyd = bfs(S, st, cols, sx, max_drop=19)
        tz = (range(168, 212), range(240, 273)) if team == 0 else (range(300, 344), range(240, 273))
        tz_nodes = [k for k in safe if k[0] in tz[0] and k[1] in tz[1] and k[2] >= 50]
        ex, ey = SPEC['bases'][1 - team]
        enemy = [k for k in anyd if abs(k[0] - ex) <= 20 and abs(k[1] - ey) <= 20]
        under = [k for k in anyd if 236 <= k[0] <= 275 and 228 <= k[1] <= 284]
        plat_near = [k for k in anyd if x0 - 3 <= k[0] <= x1 + 3 and y0 - 3 <= k[1] <= y1 + 3]
        gap = min(k[2] for k in plat_near) - 1 if plat_near else None
        best = min(plat_near, key=lambda k: k[2]) if plat_near else None
        res['team%d' % (team + 1)] = dict(reachable_nodes=len(anyd), safe_nodes=len(safe),
                                         tower_zone_safe=bool(tz_nodes), tower_zone_min_cost=min((safe[k] for k in tz_nodes), default=None),
                                         enemy_spawn_reachable=bool(enemy), enemy_spawn_min_cost=min((anyd[k] for k in enemy), default=None),
                                         centre_reachable=bool(under),
                                         platform_reachable_without_building=bool(plat_near and gap <= 2),
                                         build_gap=gap, build_gap_from=best)
        if team == 0:
            total = int(st[:, :, :63].sum())
            res['stand_nodes_total_dry'] = total
            # trapped dry nodes: in main play area, not reachable (excluding roofs/caps ~ nodes above z 40 in builds)
            reach = np.zeros_like(st)
            for k in anyd:
                reach[k] = True
            # reachability back to own spawn is approximated by forward reachability from spawn with drops<=9 reversed: skip
            unr = st & ~reach
            unr[:, :, 63] = False
            res['unreachable_stand_nodes'] = int(unr.sum())
            # where: ground-level unreachable (top surface) count
            gl = np.zeros((512, 512), bool)
            for x in range(512):
                pass
    rep['routes'] = res
    # anchor fronts: height step at the enemy-facing side of each anchor
    wf = [int(top[213, y]) - int(top[212, y]) for y in range(240, 273)]
    rep['anchor_front_step_min'] = min(wf)
    rep['spawn_exposure'] = {'team1': exposure(S, top, (98, 138, 236, 276), SPEC['platform']),
                             'team2': exposure(S, top, (373, 413, 236, 276), SPEC['platform'])}
    with open(os.path.join(d, 'validation.json'), 'w') as fh:
        json.dump(rep, fh, indent=1, default=str)
    print(json.dumps(rep, indent=1, default=str))


if __name__ == '__main__':
    main(sys.argv[1])
