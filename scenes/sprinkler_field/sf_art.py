"""Sprinkler Field art pass (separate from the graybox; it must not change gameplay geometry).

    art_west(cv, rep, S, rng)   BEFORE the mirror (OS seed `veg_seed`): every plant (each grass blade, clover, low
                                clover, dandelion, mushroom, daisy, sprout) draws EXACTLY three random details. Flush
                                details recolour the plant's own voxels (dew beads on tips, glowing gills); attached
                                details are tiny face-connected add-ons on blade / stalk sides or on top of a canopy,
                                always >= 6 above any floor below them and never in a spawn / front / anchor column
                                (ladybird beetle, snail, caterpillar, firefly, grass seed head, spider thread, clover
                                flower, side bud). Colour-only details (withered tip, chewed notch, aphids, moss collar,
                                pollen, wet streak, bald patch, slug bite ...) are painted after the mirror.
    finish(cv, rep, S, seed)    AFTER the mirror, the axis objects and the one-offs: sky decor (sf_sky), material ->
                                colour paint with noise (sf_paint), tunnel fungi / root ends / egg clusters, flush glow
                                (spigot drip, nozzle droplets, dewdrop props), baked light + AO, morning grade, corner
                                tag, brightness rules, glow bake (knowledge base 11.4).

Nothing here adds walk-blocking volume: the add-on list, the tag strip and the sky pieces are the only solid changes
(sf_checks.art_diff measures that against an in-process graybox build).
"""
from __future__ import annotations

import math

import numpy as np

from aosmap.kit import color, noise, tag

import sf_paint
import sf_sky
from sf_build import KEEP

CYAN, YELLOW, WARM, GREEN = (95, 255, 255), (255, 255, 95), (255, 175, 95), (95, 255, 95)
GLOW_PALETTE = {(255, 255, 255), (255, 95, 95), (255, 255, 95), (95, 255, 255), (255, 175, 95), (95, 255, 95)}

ADDON_MATS = ('beetle', 'snail_s', 'caterpillar', 'firefly', 'grass_seed', 'silk', 'spider', 'clover_flower', 'bud')
FLUSH_MATS = ('dew_bead', 'dew_glow', 'gill_glow')
NOGO = KEEP['spawn'] | KEEP['front'] | KEEP['anchor']
PLANT_MATS = ('blade', 'crown', 'stalk', 'clover', 'dandelion_stalk', 'seedhead', 'mushroom_cap', 'mushroom_stem',
              'daisy', 'daisy_eye', 'sprout') + ADDON_MATS + FLUSH_MATS

# detail pools (weights). GEO = attached add-ons (need room); the rest are flush / colour-only
BLADE_POOL = {'dew bead': 3.0, 'withered tip': 2.0, 'chewed notch': 2.0, 'aphids': 2.0, 'moss collar': 1.6,
              'pollen dusting': 1.0, 'wet streak': 1.6, 'ladybird beetle': 1.2, 'snail': 0.8, 'caterpillar': 1.0,
              'firefly': 1.1, 'seed head': 1.0, 'spider thread': 0.5}
CLOVER_POOL = {'dew beads': 3.0, 'ladybird beetle': 1.0, 'snail': 0.8, 'firefly': 1.3, 'withered leaflet': 1.5,
               'chewed holes': 1.5, 'aphids': 1.2, 'clover flower': 1.3, 'moss collar': 1.0, 'spider thread': 0.7,
               'caterpillar': 0.8}
DANDELION_POOL = {'dew on globe': 2.0, 'bald patch': 1.5, 'firefly': 1.6, 'snail': 1.0, 'caterpillar': 1.0,
                  'aphids': 1.2, 'moss collar': 1.0, 'side bud': 1.3, 'spider thread': 0.8}
MUSHROOM_POOL = {'dew drops': 2.0, 'glowing gills': 1.6, 'slug bite': 1.5, 'spore dust': 1.0, 'moss collar': 1.0,
                 'snail': 0.8, 'firefly': 1.0, 'cap cracks': 1.2}
LOW_POOL = {'dew bead': 2.0, 'withered edge': 1.5, 'chewed notch': 1.5, 'aphids': 1.5, 'moss collar': 1.0,
            'pollen dusting': 1.2}
GEO = {'ladybird beetle', 'snail', 'caterpillar', 'firefly', 'seed head', 'spider thread', 'clover flower',
       'side bud'}
FLUSH_GEO = {'dew bead', 'dew beads', 'dew on globe', 'dew drops', 'glowing gills'}   # recolour in art_west


def _pick(rng, pool, n=3):
    keys = list(pool)
    p = np.array([pool[k] for k in keys], float)
    idx = rng.choice(len(keys), size=n, replace=False, p=p / p.sum())
    return [keys[i] for i in idx]


# =============================================================================================== add-on placement

class Addons:
    """Places small attached pieces; every cell must be air, inside the west half (x <= 252), outside spawn / front /
    anchor columns, and have >= 6 air above the first solid below it unless that solid is plant matter or the piece
    itself (so no floor loses headroom or climb room)."""

    def __init__(self, cv):
        self.cv = cv
        self.plant_ids = {cv.material(m) for m in PLANT_MATS}
        self.voxels = []                       # (x, y, z, mat)
        self.glow = 0

    def ok(self, cells):
        cv = self.cv
        own = {(x, y, z) for (x, y, z, _, _) in cells}
        for (x, y, z, _, _) in cells:
            if not (4 <= x <= 252 and 4 <= y <= 507 and 3 <= z <= 60):
                return False
            if cv.solid[x, y, z] or cv.keep[x, y] & NOGO:
                return False
            col = cv.solid[x, y, z + 1:]
            below = np.nonzero(col)[0]
            zz = z + 1
            for k in below:                           # first solid below that is not part of this piece
                zz = z + 1 + int(k)
                if (x, y, zz) not in own:
                    break
            else:
                zz = 64
            if zz < 64 and zz - z < 6 and cv.mat[x, y, zz] not in self.plant_ids:
                return False
        return True

    def put(self, cells):
        cv = self.cv
        for (x, y, z, mat, c) in cells:
            if mat in ('firefly_glow',):
                cv.add_glow(x, y, z, c)
                cv.mat[x, y, z] = cv.material('firefly')
                self.glow += 1
            else:
                cv.set(x, y, z, c, mat)
            self.voxels.append((x, y, z, mat))


def _frame(hx, hy, hz, d):
    ox, oy = d
    px, py = -oy, ox
    return lambda o, s, dz: (hx + ox * o + px * s, hy + oy * o + py * s, hz + dz)


DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def _shape(kind, rng):
    """Local cells (o = out from the host face, s = sideways, dz = down (+) / up (-)) and colours."""
    if kind == 'ladybird beetle':
        shell = (206, 172, 50) if rng.random() < 0.5 else (200, 118, 42)
        spot, head = (40, 34, 30), (52, 46, 40)
        cells = [(1, s, dz, 'beetle', spot if (s != 0 and dz == 1) else shell) for s in (-1, 0, 1) for dz in (0, 1)]
        cells += [(2, 0, 0, 'beetle', spot), (2, 0, 1, 'beetle', shell), (1, 0, -1, 'beetle', head)]
        return cells
    if kind == 'snail':
        sh = [(196, 170, 122), (150, 108, 70), (120, 86, 56)]
        cells = []
        for o in (1, 2, 3):
            for s in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    if abs(s) == 1 and abs(dz) == 1 and o in (1, 3):
                        continue
                    band = sh[(abs(s) + abs(dz) + o) % 3] if (o, s, dz) != (2, 0, 0) else (104, 76, 52)
                    cells.append((o, s, dz, 'snail_s', band))
        body = (138, 128, 104)
        cells += [(1, 0, -2, 'snail_s', body), (1, 0, -3, 'snail_s', body), (1, 0, -4, 'snail_s', (126, 116, 94)),
                  (2, 0, -4, 'snail_s', (112, 104, 86)), (2, 0, -5, 'snail_s', (96, 90, 76)),
                  (1, 0, 2, 'snail_s', (128, 120, 98))]
        return cells
    if kind == 'caterpillar':
        g1, g2, band, dot = (118, 162, 66), (98, 142, 56), (198, 186, 86), (60, 66, 44)
        cells = []
        for dz in range(0, 6):
            for s in (0, 1):
                c = band if dz % 3 == 1 else (g1 if s == 0 else g2)
                if dz % 3 == 2 and s == 1:
                    c = dot
                cells.append((1, s, dz, 'caterpillar', c))
        cells += [(1, 0, -1, 'caterpillar', (150, 140, 70)), (1, 1, -1, 'caterpillar', (120, 112, 58))]
        return cells
    if kind == 'firefly':
        c = YELLOW if rng.random() < 0.6 else WARM
        return [(1, 0, 0, 'firefly_glow', c), (1, 0, -1, 'firefly', (112, 92, 58)), (2, 0, -1, 'firefly', (96, 80, 52)),
                (1, 0, -2, 'firefly', (58, 50, 42))]
    if kind == 'spider thread':
        L = int(rng.integers(3, 5))
        cells = [(o, 0, 0, 'silk', (164, 172, 164)) for o in range(1, L + 1)]
        cells += [(L, 0, 1, 'spider', (92, 76, 58)), (L, 0, 2, 'spider', (70, 58, 46))]
        return cells
    if kind == 'side bud':
        cells = [(1, 0, 0, 'bud', (100, 140, 66)), (2, 0, 0, 'bud', (100, 140, 66))]
        for o in (2, 3):
            for s in (0, 1):
                for dz in (-1, -2, -3):
                    c = (206, 176, 60) if dz == -3 else ((112, 150, 70) if s == 0 else (92, 128, 60))
                    cells.append((o, s, dz, 'bud', c))
        return cells
    raise KeyError(kind)


def _attach_side(ad, rng, hosts, kind, zlo, zhi, tries=40):
    """Attach `kind` to the side of one of `hosts` (voxels (x, y, z)) with z in [zlo, zhi]."""
    cand = [h for h in hosts if zlo <= h[2] <= zhi]
    if not cand:
        return False
    order = rng.permutation(len(cand))[:tries]
    cv = ad.cv
    for i in order:
        hx, hy, hz = cand[int(i)]
        if not cv.solid[hx, hy, hz]:
            continue
        for di in rng.permutation(4):
            fr = _frame(hx, hy, hz, DIRS[int(di)])
            cells = [fr(o, s, dz) + (m, c) for (o, s, dz, m, c) in _shape(kind, rng)]
            if ad.ok(cells):
                ad.put(cells)
                return True
    return False


def _seed_head(ad, rng, tip):
    tx, ty, tz = tip
    d = DIRS[int(rng.integers(0, 4))]
    cells = []
    for k in range(1, 7):
        cells.append((tx, ty, tz - k, 'grass_seed', (150 + 5 * k, 136 + 4 * k, 88 + 3 * k)))
        if k % 2 == 0:
            sgn = 1 if (k // 2) % 2 else -1
            cells.append((tx + d[0] * sgn, ty + d[1] * sgn, tz - k, 'grass_seed', (166, 134, 98)))
    if ad.ok(cells):
        ad.put(cells)
        return True
    return False


def _clover_flower(ad, f):
    cx, cy, zc = int(f['x']), int(f['y']), int(f['zc'])
    cells = []
    for x in range(cx - 1, cx + 3):
        for y in range(cy - 1, cy + 3):
            for z in (zc - 1, zc - 2, zc - 3):
                d = (x - cx - 0.5) ** 2 + (y - cy - 0.5) ** 2 + ((z - (zc - 2)) * 1.25) ** 2
                if d <= 3.3:
                    c = (172, 188, 142) if z == zc - 1 else ((204, 200, 188) if (x + y + z) % 3 else (190, 176, 168))
                    cells.append((x, y, z, 'clover_flower', c))
    if cells and ad.ok(cells):
        ad.put(cells)
        return True
    return False


def _flush(cv, pts, mat, colour=None, glow=None):
    """Recolour existing plant voxels in place (no geometry change)."""
    n = 0
    for (x, y, z) in pts:
        if not cv.solid[x, y, z]:
            continue
        if glow is not None:
            cv.add_glow(x, y, z, glow)
        else:
            cv.rgb[x, y, z] = colour
        cv.mat[x, y, z] = cv.material(mat)
        n += 1
    return n


def _top_surface(cv, xs, ys, zs):
    """Voxels of the given set with air directly above."""
    return [(x, y, z) for x, y, z in zip(xs, ys, zs) if z > 0 and not cv.solid[x, y, z - 1]]


# =============================================================================================== art_west

def art_west(cv, rep, S, rng):
    """Three details per plant on the west half (mirrored afterwards). Records rep['art_plants']."""
    ad = Addons(cv)
    plants = []
    blade_id = cv.material('blade')
    feats = rep.get('features', [])

    def apply(rec, pool, geo_fn):
        """Draw 3; geometry that finds no room is replaced by a flush detail from the pool (still exactly 3)."""
        want = _pick(rng, pool)
        done = []
        for d in want:
            if d in GEO:
                if geo_fn(d):
                    done.append(d)
                else:
                    rest = [k for k in pool if k not in GEO and k not in want and k not in done]
                    if rest:
                        r_ = rest[int(rng.integers(0, len(rest)))]
                        if r_ in FLUSH_GEO:
                            geo_fn(r_)
                        done.append(r_)
            else:
                if d in FLUSH_GEO:
                    geo_fn(d)
                done.append(d)
        rec['details'] = done
        if len(done) != 3:
            rec['details_short'] = True

    # ---------------------------------------------------------------- grass blades (one plant each)
    for bi, br in enumerate(rep.get('blade_records', [])):
        vox = [(x, y, z) for (x, y, z, f, a, b, w) in br['vox'] if cv.mat[x, y, z] == blade_id]
        rec = {'kind': 'blade', 'id': bi, 'tussock': br['tussock']}
        if not vox:
            rec['details'] = []
            plants.append(rec)
            continue
        g = br['base'][2]
        tip = min(vox, key=lambda p: p[2])

        def geo(d, vox=vox, g=g, tip=tip):
            if d == 'dew bead':
                if rng.random() < 0.34:
                    _flush(cv, [tip], 'dew_glow', glow=CYAN)
                else:
                    _flush(cv, [tip], 'dew_bead', colour=(186, 204, 206))
                    below = (tip[0], tip[1], tip[2] + 1)
                    if cv.mat[below] == blade_id:
                        _flush(cv, [below], 'dew_bead', colour=(166, 190, 186))
                return True
            if d == 'seed head':
                return _seed_head(ad, rng, tip)
            Hb = br['Hb']
            return _attach_side(ad, rng, vox, d, max(tip[2] + 3, g - int(0.85 * Hb)), g - 9)
        apply(rec, BLADE_POOL, geo)
        plants.append(rec)

    # ---------------------------------------------------------------- clovers, dandelions, mushrooms, low plants
    for f in feats:
        kind = f['kind']
        sub = f.get('sub')
        if kind not in ('clover', 'clover_low', 'dandelion', 'mushroom') and sub not in ('daisy', 'sprout'):
            continue
        if f['x'] >= 254:
            continue
        rec = {'kind': kind if kind != 'front' else sub, 'name': f['name']}
        cx, cy = int(f['x']), int(f['y'])
        g = int(f.get('g', cv.H[cx, cy]))
        if kind == 'clover':
            hgt = int(f['hgt'])
            stalk = [(x, y, z) for x in (cx, cx + 1) for y in (cy, cy + 1) for z in range(g - hgt, g)]
            R = f['R']
            box = cv.mat[cx - int(R) - 2:cx + int(R) + 3, cy - int(R) - 2:cy + int(R) + 3, :g - 1]
            xs, ys, zs = np.nonzero(box == cv.material('clover'))
            leaf = _top_surface(cv, xs + cx - int(R) - 2, ys + cy - int(R) - 2, zs)

            def geo(d, stalk=stalk, leaf=leaf, g=g, hgt=hgt, f=f):
                if d == 'dew beads':
                    if not leaf:
                        return True
                    sel = [leaf[int(i)] for i in rng.choice(len(leaf), size=min(4, len(leaf)), replace=False)]
                    _flush(cv, sel[:1], 'dew_glow', glow=CYAN)
                    _flush(cv, sel[1:], 'dew_bead', colour=(184, 202, 204))
                    return True
                if d == 'clover flower':
                    return _clover_flower(ad, f)
                if d == 'ladybird beetle':
                    return _attach_top(ad, rng, leaf, d)
                return _attach_side(ad, rng, stalk, d, g - hgt + 2, g - 6)
            apply(rec, CLOVER_POOL, geo)
        elif kind == 'dandelion':
            hgt = int(f['hgt'])
            x0 = cx - 1
            stalk = [(x0 + a, cy - 1 + b, z) for a in range(3) for b in range(3) if not (a == 1 and b == 1)
                     for z in range(g - hgt, g)]
            Rg = f['Rg']
            gx, gy, gz = f['x'], f['y'], f['gz']
            sub_ = cv.mat[int(gx - Rg - 1):int(gx + Rg + 2), int(gy - Rg - 1):int(gy + Rg + 2), :]
            xs, ys, zs = np.nonzero(sub_ == cv.material('seedhead'))
            globe = list(zip(xs + int(gx - Rg - 1), ys + int(gy - Rg - 1), zs))

            def geo(d, stalk=stalk, globe=globe, g=g, hgt=hgt, gz=gz):
                if d == 'dew on globe':
                    up = [p for p in globe if p[2] <= gz and not cv.solid[p[0], p[1], p[2] - 1]]
                    if not up:
                        return True
                    sel = [up[int(i)] for i in rng.choice(len(up), size=min(3, len(up)), replace=False)]
                    _flush(cv, sel[:1], 'dew_glow', glow=CYAN)
                    _flush(cv, sel[1:], 'dew_bead', colour=(190, 204, 204))
                    return True
                return _attach_side(ad, rng, stalk, d, g - hgt + 4, g - 7)
            apply(rec, DANDELION_POOL, geo)
        elif kind == 'mushroom':
            hgt = int(f['hgt'])
            R = int(f['R'])
            stem = [(x, y, z) for x in range(cx - 2, cx + 3) for y in range(cy - 2, cy + 3)
                    if math.hypot(x - cx, y - cy) <= 2.3 for z in range(g - hgt, g)]
            capm = cv.mat[cx - R - 1:cx + R + 2, cy - R - 1:cy + R + 2, :g]
            xs, ys, zs = np.nonzero(capm == cv.material('mushroom_cap'))
            xs, ys = xs + cx - R - 1, ys + cy - R - 1
            top = _top_surface(cv, xs, ys, zs)
            under = [(x, y, z) for x, y, z in zip(xs, ys, zs) if not cv.solid[x, y, z + 1] and
                     math.hypot(x - cx, y - cy) > 2.6]

            def geo(d, stem=stem, top=top, under=under, g=g, hgt=hgt):
                if d == 'dew drops':
                    if not top:
                        return True
                    sel = [top[int(i)] for i in rng.choice(len(top), size=min(3, len(top)), replace=False)]
                    _flush(cv, sel[:1], 'dew_glow', glow=CYAN)
                    _flush(cv, sel[1:], 'dew_bead', colour=(188, 200, 198))
                    return True
                if d == 'glowing gills':
                    if not under:
                        return True
                    sel = [under[int(i)] for i in rng.choice(len(under), size=min(3, len(under)), replace=False)]
                    _flush(cv, sel, 'gill_glow', glow=GREEN)
                    return True
                return _attach_side(ad, rng, stem, d, g - hgt + 1, g - 6)
            apply(rec, MUSHROOM_POOL, geo)
        else:                                            # clover_low, daisy, sprout: flush details only
            r_ = 5 if kind == 'clover_low' else 5
            box = cv.mat[cx - r_:cx + r_ + 2, cy - r_:cy + r_ + 2, :g]
            ids = [cv.material(m) for m in ('clover', 'daisy', 'daisy_eye', 'sprout')]
            xs, ys, zs = np.nonzero(np.isin(box, ids))
            top = _top_surface(cv, xs + cx - r_, ys + cy - r_, zs)

            def geo(d, top=top):
                if d == 'dew bead' and top:
                    sel = top[int(rng.integers(0, len(top)))]
                    _flush(cv, [sel], 'dew_glow', glow=CYAN)
                return True
            apply(rec, LOW_POOL, geo)
        plants.append(rec)

    rep['art_plants'] = plants
    by_kind, dets = {}, {}
    for p in plants:
        by_kind[p['kind']] = by_kind.get(p['kind'], 0) + 1
        for d in p['details']:
            dets[d] = dets.get(d, 0) + 1
    mats = {}
    for (_, _, _, m) in ad.voxels:
        mats[m] = mats.get(m, 0) + 1
    return {'veg_rule': 'every plant has exactly three random details (OS seed)',
            'plants_west': len(plants), 'by_kind': by_kind, 'details': dets,
            'all_exactly_three': all(len(p['details']) == 3 for p in plants if p['kind'] != 'blade' or p['details']),
            'blades_without_voxels': sum(1 for p in plants if p['kind'] == 'blade' and not p['details']),
            'addon_voxels_west': len(ad.voxels), 'addon_by_mat': mats, 'addon_glow_west': ad.glow,
            'glow_sources_west': len(cv.glow)}


def _attach_top(ad, rng, tops, kind, tries=30):
    """Beetle sitting on a leaf top (cells above the surface)."""
    if not tops:
        return False
    shell = (206, 172, 50) if rng.random() < 0.5 else (200, 118, 42)
    for i in rng.permutation(len(tops))[:tries]:
        x, y, z = tops[int(i)]
        d = DIRS[int(rng.integers(0, 4))]
        cells = [(x, y, z - 1, 'beetle', shell), (x + d[0], y + d[1], z - 1, 'beetle', (40, 34, 30)),
                 (x - d[0], y - d[1], z - 1, 'beetle', (52, 46, 40)), (x, y, z - 2, 'beetle', shell)]
        if ad.ok(cells) and all(ad.cv.solid[cx, cy, cz + 1] or (cx, cy) == (x, y) for (cx, cy, cz, _, _) in cells[:3]):
            ad.put(cells)
            return True
    return False


# =============================================================================================== finish

def _glow_flush(cv, x, y, z, c):
    """Turn an existing surface voxel into a glow source without touching solid / material (post-mirror)."""
    if not cv.solid[x, y, z]:
        return False
    cv.rgb[x, y, z] = c
    cv.nolight[x, y, z] = True
    cv.glow.append((int(x), int(y), int(z), tuple(c)))
    return True


def underground(cv, rep, S, seed):
    """Tunnel fungi (pale caps + one glow each), root ends on the ceilings, egg clusters in the queen chamber."""
    rng = noise.rng('underground', seed)
    T = cv.tops()
    fl = S['z']['tunnel_floor']
    zz = np.arange(64)[None, None, :]
    air_ug = (~cv.solid) & (zz > T[:, :, None] + 2) & (zz < 62)          # air below the ground surface
    n_fungi = n_roots = n_eggs = 0
    # walls: solid with a horizontal underground-air neighbour, z fl-3..fl-1
    W = np.zeros_like(cv.solid)
    for dx, dy in DIRS:
        sh = np.roll(np.roll(air_ug, dx, 0), dy, 1)
        W |= cv.solid & sh
    W[:, :, :fl - 3] = False
    W[:, :, fl:] = False
    xs, ys, zs = np.nonzero(W)
    order = rng.permutation(len(xs))
    taken = []
    for i in order:
        x, y, z = int(xs[i]), int(ys[i]), int(zs[i])
        if any(abs(x - a) + abs(y - b) < 15 for a, b in taken):
            continue
        taken.append((x, y))
        _glow_flush(cv, x, y, z, GREEN)
        n_fungi += 1
        for (a, b, c) in ((0, 0, -1), (0, 0, 1), (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, -2)):
            X, Y, Z = x + a, y + b, z + c
            if 0 <= X < 512 and 0 <= Y < 512 and W[X, Y, Z] and not cv.nolight[X, Y, Z]:
                cv.rgb[X, Y, Z] = (206, 198, 170) if (a + b + c) % 2 else (190, 180, 150)
    # ceilings: solid with underground air directly below
    C = cv.solid & np.roll(air_ug, -1, 2)
    C[:, :, 62:] = False
    C[:, :, :54] = False                          # tunnel / chamber ceilings only (not hose arches or canopies)
    xs, ys, zs = np.nonzero(C)
    for i in rng.permutation(len(xs))[:max(1, len(xs) // 45)]:
        x, y, z = int(xs[i]), int(ys[i]), int(zs[i])
        if cv.nolight[x, y, z]:
            continue
        cv.rgb[x, y, z] = (172, 140, 98)
        for (a, b) in ((1, 0), (0, 1)):
            if C[x + a, y + b, z] and rng.random() < 0.6:
                cv.rgb[x + a, y + b, z] = (150, 120, 86)
        n_roots += 1
    # eggs: pearly ovals on the queen chamber floor ring and the wall base
    qx, qy, rx, ry = S['nest']['queen']
    for k in range(5):
        a0 = rng.uniform(0, 2 * math.pi)
        ex, ey = qx + 0.78 * rx * math.cos(a0), qy + 0.78 * ry * math.sin(a0)
        for x in range(int(ex) - 4, int(ex) + 5):
            for y in range(int(ey) - 4, int(ey) + 5):
                if math.hypot((x - ex) / 3.6, (y - ey) / 2.8) > 1:
                    continue
                for z in (fl, fl - 1):
                    if cv.solid[x, y, z] and z - 1 >= 0 and not cv.solid[x, y, z - 1] and not cv.nolight[x, y, z]:
                        egg = (x + 2 * y) % 3
                        cv.rgb[x, y, z] = ((206, 200, 180), (192, 186, 166), (168, 158, 136))[egg]
                        n_eggs += 1
                        break
    return {'fungi_glow': n_fungi, 'root_ends': n_roots, 'egg_voxels': n_eggs}


def object_glow(cv, rep, S):
    """Spigot drip, sprinkler nozzle droplets, dewdrop props (flush glow on existing voxels)."""
    n = {'spigot_drip': 0, 'nozzle_droplets': 0, 'dewdrop_props': 0}
    sx, sy = S['oneoffs']['spigot']
    hy = int(round(sy))
    hose_top = S['hose']['cz'] - S['hose']['r_out']
    for (x, y, z) in ((sx, hy + 2, hose_top - 1), (sx + 1, hy + 2, hose_top - 2), (sx - 2, hy, hose_top - 1)):
        if _glow_flush(cv, x, y, z, CYAN):
            n['spigot_drip'] += 1
    T = S['sprinkler']['tbar']
    z = T['z'] + 1
    for x in (T['x'][0], T['x'][1], T['x'][0] + 8, T['x'][1] - 8):
        if _glow_flush(cv, x, (T['y'][0] + T['y'][1]) // 2, z, CYAN):
            n['nozzle_droplets'] += 1
    hx, hy2 = S['sprinkler']['hub']
    for (x, y) in ((hx - 5, hy2), (hx + 5, hy2)):
        zt = S['sprinkler']['head_z'] + 1
        if _glow_flush(cv, x, y, zt, CYAN):
            n['nozzle_droplets'] += 1
    for f in rep.get('features', []):
        if f.get('sub') == 'dewdrop':
            for xx in (int(f['x']), 512 - int(f['x'])):
                y = int(f['y'])
                t = cv.column_top(xx, y)
                if _glow_flush(cv, xx, y, t, CYAN):
                    n['dewdrop_props'] += 1
    return n


def bake_glow_fast(cv, surf, radius=6.5, strength=0.32):
    """Same model as aosmap.kit.color.bake_glow (knowledge base 11.4), vectorised per source (from yh_art)."""
    srcs, seen = [], set()
    for (x, y, z, c) in cv.glow:
        if (x, y, z) in seen or not cv.inside(x, y, z) or not cv.solid[x, y, z]:
            continue
        seen.add((x, y, z))
        srcs.append((x, y, z, c))
    R = int(math.ceil(radius))
    o = np.arange(-R, R + 1)
    DX, DY, DZ = np.meshgrid(o, o, o, indexing='ij')
    D = np.sqrt(DX ** 2 + DY ** 2 + DZ ** 2)
    Wt = np.where((D < radius) & (D > 0), (1 - D / radius) * strength, 0.0)
    acc = {}
    for (x, y, z, c) in srcs:
        xs, ys, zs = x + DX, y + DY, z + DZ
        ok = (Wt > 0) & (xs >= 0) & (xs < 512) & (ys >= 0) & (ys < 512) & (zs >= 0) & (zs < 64)
        xs, ys, zs, w = xs[ok], ys[ok], zs[ok], Wt[ok]
        s = surf[xs, ys, zs]
        for (a, b, cc, ww) in zip(xs[s], ys[s], zs[s], w[s]):
            k = (int(a), int(b), int(cc))
            v = acc.get(k)
            if v is None:
                acc[k] = [c[0] * ww, c[1] * ww, c[2] * ww]
            else:
                v[0] += c[0] * ww
                v[1] += c[1] * ww
                v[2] += c[2] * ww
    stored = {}
    for k, a in acc.items():
        if k in seen:
            continue
        orig = tuple(int(v) for v in cv.rgb[k])
        stored[k] = orig
        cv.rgb[k] = (min(255, int(orig[0] + a[0])), min(255, int(orig[1] + a[1])), min(255, int(orig[2] + a[2])))
    for (x, y, z, c) in srcs:
        cv.rgb[x, y, z] = c
        stored[(x, y, z)] = tuple(c)
    return stored, len(srcs)


def finish(cv, rep, S, seed):
    """Sky decor -> paint -> underground + object glow -> light + AO -> grade -> tag -> brightness -> glow bake."""
    out = {}
    out['sky'] = sf_sky.place_all(cv)
    out['paint'] = sf_paint.paint(cv, rep, S, seed)
    out['underground'] = underground(cv, rep, S, seed)
    out['object_glow'] = object_glow(cv, rep, S)
    surf = color.lighting(cv)
    grade = np.array((1.03, 1.01, 0.965), np.float32)
    m = cv.solid & ~cv.nolight
    cv.rgb[m] = np.clip(cv.rgb[m].astype(np.float32) * grade, 0, 255).astype(np.uint8)
    out['grade'] = grade.round(3).tolist()
    T = S['tag']
    trgb, tsh = (204, 188, 146), (86, 66, 50)
    rect = tag.paint_tag(cv, T['text'], corner=T['corner'], margin=8, scale=1, rgb=trgb, shadow=tsh)
    out['tag_rect'] = list(rect)
    out['tag_strip_retextured'] = sf_paint.retexture_tag_strip(cv, rect, (trgb, tsh), seed)
    out['brightness'] = color.enforce_brightness(cv, floor_min=41)
    stored, n_src = bake_glow_fast(cv, surf)
    srcs = {(x, y, z) for (x, y, z, _) in cv.glow}
    nudged = 0
    for key in list(stored):
        if key in srcs:
            continue
        cc = tuple(int(v) for v in cv.rgb[key])
        if cc in GLOW_PALETTE:
            cv.rgb[key] = (max(0, cc[0] - 1), cc[1], cc[2])
            nudged += 1
    out['glow_sources'] = n_src
    out['glow_lit_voxels'] = len(stored) - n_src
    out['palette_nudged'] = nudged
    out['colour_stats'] = color.colour_stats(cv.solid, cv.rgb)
    bx0, bx1, by0, by1, _ = rect
    out['boxes'] = [[bx0, bx1, by0, by1]] + [[o['x'][0] - 2, o['x'][1] + 2, o['y'][0] - 2, o['y'][1] + 2]
                                            for o in out['sky']]
    return stored, out
