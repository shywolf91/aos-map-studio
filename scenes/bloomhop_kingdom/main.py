"""Bloomhop Kingdom — build + export.  python main.py OUTDIR [veg_seed]"""
import sys, os, json, math, time, hashlib
import numpy as np
from scipy import ndimage
from geo import World, shade, mix, clamp8
from spec import SPEC
import terrain, builds as B, veg, vxlcore

FONT = {
    'B': ["1110", "1001", "1001", "1110", "1001", "1001", "1110"],
    'L': ["1000", "1000", "1000", "1000", "1000", "1000", "1111"],
    'O': ["0110", "1001", "1001", "1001", "1001", "1001", "0110"],
    'M': ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    'H': ["1001", "1001", "1001", "1111", "1001", "1001", "1001"],
    'P': ["1110", "1001", "1001", "1110", "1000", "1000", "1000"],
    'K': ["1001", "1010", "1100", "1100", "1010", "1001", "1001"],
    'I': ["111", "010", "010", "010", "010", "010", "111"],
    'N': ["1001", "1101", "1101", "1011", "1011", "1001", "1001"],
    'G': ["0110", "1001", "1000", "1011", "1001", "1001", "0111"],
    'D': ["1110", "1001", "1001", "1001", "1001", "1001", "1110"],
    ' ': ["00", "00", "00", "00", "00", "00", "00"],
}


def paint_path(W, pts, width, rng):
    cob = np.array([214, 190, 140]); cob2 = np.array([192, 166, 120]); edge = np.array([170, 146, 104])
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(n):
            t = i / max(n - 1, 1)
            cx, cy = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            r = width / 2
            for x in range(int(cx - r - 1), int(cx + r + 2)):
                for y in range(int(cy - r - 1), int(cy + r + 2)):
                    if not (0 <= x < 256 and 0 <= y < 512):
                        continue
                    d = math.hypot(x - cx, y - cy)
                    if d <= r:
                        z = int(W.H[x, y])
                        if z >= 61:
                            continue
                        c = cob if ((x // 2 + y // 2) % 3) else cob2
                        if d > r - 0.9:
                            c = edge
                        W.C[x, y, z] = c
                        W.C[x, y, z + 1] = (150, 112, 72)
                        W.keep[x, y] |= 2


PATHS = [
    ([(138, 256), (150, 256), (170, 256)], 7),
    ([(126, 236), (146, 214), (176, 206), (204, 206), (222, 194), (226, 180), (238, 196), (255, 200)], 5),
    ([(126, 276), (146, 298), (178, 308), (206, 312), (224, 322), (238, 316), (255, 312)], 5),
    ([(104, 214), (98, 186), (92, 150), (96, 120), (100, 96)], 5),
    ([(104, 298), (98, 326), (100, 360), (126, 390)], 5),
    ([(30, 94), (100, 96), (170, 90), (232, 92), (246, 86)], 5),
    ([(30, 390), (126, 392), (200, 392), (255, 392)], 5),
    ([(92, 150), (150, 150), (196, 142), (214, 150), (226, 162)], 4),
    ([(100, 360), (150, 362), (200, 370), (232, 362), (240, 352)], 4),
    ([(226, 180), (226, 170)], 4),
]


def sky_decor(W, rng):
    """Opt-in floating pieces over the flanks (>= 67 from the platform, nothing over spawn squares)."""
    pieces = []

    def cloud(cx, cy, cz, L):
        top = (234, 236, 242); bot = (198, 206, 226)
        n = int(rng.integers(4, 6))
        for k in range(n):
            ox = (k - (n - 1) / 2) * L / n + rng.uniform(-1, 1)
            oy = rng.uniform(-2, 2)
            r = L / n * rng.uniform(0.8, 1.15)
            rz = r * 0.62

            def cf(xs, ys, zs, d):
                t = np.clip((zs - (cz - rz)) / (2 * rz), 0, 1)[:, None]
                out = np.array(top, float) * (1 - t) + np.array(bot, float) * t
                return np.clip(out, 0, 255).astype(np.uint8)
            W.ellipsoid(cx + ox, cy + oy, cz - (0 if abs(ox) > L / 4 else 1), r, r * 0.8, rz, cf)
        W.box(int(cx - L / 2 - 4), int(cx + L / 2 + 4), int(cy - 10), int(cy + 10), cz + 2, cz + 6, air=True)
        pieces.append((int(cx - L / 2 - 6), int(cx + L / 2 + 6), int(cy - 10), int(cy + 10), cz - 8, cz + 2))

    def step_blocks(x0, y0, z0, n, dx, dz):
        for i in range(n):
            x = x0 + i * dx; z = z0 + (i % 2) * dz
            c = B.GOLD if i % 2 == 0 else B.BRICK
            B.toy_block(W, x, y0, z, sx=5, sy=5, sz=4, col=c, emblem=i % 3)
            pieces.append((x - 1, x + 6, y0 - 1, y0 + 6, z - 1, z + 5))

    # north flank (west half authored then mirrored by hand)
    for (cx, cy, cz, L) in ((70, 76, 10, 26), (164, 104, 12, 22)):
        for xx in (cx, 511 - cx):
            cloud(xx, cy, cz, L)
    step_blocks(104, 64, 17, 5, 8, -2)
    step_blocks(511 - 104 - 4 * 8 - 4, 64, 17, 5, 8, -2)
    # south flank, beyond the ridge
    for (cx, cy, cz, L) in ((96, 452, 12, 24), (200, 446, 10, 20)):
        for xx in (cx, 511 - cx):
            cloud(xx, cy, cz, L)
    W.expect_floating.extend(pieces)
    return len(pieces)


def corner_tag(W, text='BLOOMHOP KINGDOM'):
    x = 8; y0 = 490
    width = sum(len(FONT[ch][0]) + 1 for ch in text) + 4
    zs = W.H[4:x + width, y0 - 3:y0 + 11]
    z = int(np.median(zs))
    # level only the strip under the tag
    W.box(4, x + width - 1, y0 - 3, y0 + 10, z, 63, (124, 170, 74))
    W.box(4, x + width - 1, y0 - 3, y0 + 10, 0, z - 1, air=True)
    for xx in range(4, x + width):
        for yy in range(y0 - 3, y0 + 11):
            W.C[xx, yy, z] = (116, 172, 74) if (xx + yy) % 2 else (108, 164, 70)
            W.C[xx, yy, z + 1] = (126, 84, 52)
            W.H[xx, yy] = z
    cx = x
    for ch in text:
        g = FONT[ch]
        for r, row in enumerate(g):
            for c, bit in enumerate(row):
                if bit == '1':
                    W.set(cx + c, y0 + r, z - 1, (250, 220, 120))
                    W.C[cx + c, y0 + r, z] = (200, 150, 60)
        cx += len(g[0]) + 1
    return (4, x + width, y0 - 3, y0 + 10, z)


def remove_orphans(W):
    lab, n = ndimage.label(W.S)  # 6-connectivity
    grounded = np.unique(lab[:, :, 62:][W.S[:, :, 62:]])
    sizes = ndimage.sum_labels(np.ones_like(lab, dtype=np.int32), lab, index=np.arange(n + 1))
    keep_lab = np.zeros(n + 1, bool); keep_lab[grounded] = True; keep_lab[0] = False
    objs = ndimage.find_objects(lab)
    removed = 0; removed_vox = 0; kept_float = []
    for i, sl in enumerate(objs, start=1):
        if keep_lab[i] or sl is None:
            continue
        x0, x1 = sl[0].start, sl[0].stop - 1; y0, y1 = sl[1].start, sl[1].stop - 1; z0, z1 = sl[2].start, sl[2].stop - 1
        expected = any(a <= x0 and x1 <= b and c <= y0 and y1 <= d and e <= z0 and z1 <= f for (a, b, c, d, e, f) in W.expect_floating)
        if expected and sizes[i] > 20:
            kept_float.append(dict(bbox=[int(x0), int(x1), int(y0), int(y1), int(z0), int(z1)], voxels=int(sizes[i])))
            continue
        W.S[sl][lab[sl] == i] = False
        removed += 1; removed_vox += int(sizes[i])
    return removed, removed_vox, kept_float


def lighting(W):
    S = W.S
    P = np.pad(S, 1, constant_values=True)
    P[:, :, 0] = False  # above z=0 is air
    air = ~P
    a_xm = air[:-2, 1:-1, 1:-1]; a_xp = air[2:, 1:-1, 1:-1]
    a_ym = air[1:-1, :-2, 1:-1]; a_yp = air[1:-1, 2:, 1:-1]
    a_zm = air[1:-1, 1:-1, :-2]; a_zp = air[1:-1, 1:-1, 2:]
    surf = S & (a_xm | a_xp | a_ym | a_yp | a_zm | a_zp)
    occ = ndimage.uniform_filter(S.astype(np.float32), size=5, mode='constant', cval=1.0)
    f = np.where(a_zm, 1.0, 0.84).astype(np.float32)
    side = ~a_zm
    f += side * (0.06 * a_xm + 0.03 * a_ym - 0.05 * a_xp - 0.02 * a_yp)
    f *= np.clip(1.16 - 0.42 * occ, 0.72, 1.06)
    covered = np.cumsum(S, axis=2) - S  # solids strictly above
    f *= np.where(covered > 0, 0.86, 1.0)
    m = surf & ~W.nolight
    c = W.C[m].astype(np.float32) * f[m][:, None]
    W.C[m] = np.clip(c, 0, 255).astype(np.uint8)
    return surf


def bake_glow(W, surf):
    stored = {}
    add = {}
    srcs = []
    seen = set()
    for (x, y, z, c) in W.glow:
        if (x, y, z) in seen or not (0 <= x < 512 and 0 <= y < 512 and 0 <= z < 64):
            continue
        if not W.S[x, y, z]:
            continue
        seen.add((x, y, z)); srcs.append((x, y, z, c))
    R = 6
    for (x, y, z, c) in srcs:
        for dx in range(-R, R + 1):
            for dy in range(-R, R + 1):
                for dz in range(-R, R + 1):
                    d = math.sqrt(dx * dx + dy * dy + dz * dz)
                    if d >= 6.5 or d == 0:
                        continue
                    X, Y, Z = x + dx, y + dy, z + dz
                    if not (0 <= X < 512 and 0 <= Y < 512 and 0 <= Z < 64) or not surf[X, Y, Z]:
                        continue
                    k = (X, Y, Z)
                    a = add.setdefault(k, np.zeros(3))
                    a += np.array(c) * 0.32 * (1 - d / 6.5)
    srcset = {(x, y, z) for (x, y, z, c) in srcs}
    for k, a in add.items():
        if k in srcset:
            continue
        X, Y, Z = k
        orig = tuple(int(v) for v in W.C[X, Y, Z])
        stored[k] = orig
        W.C[X, Y, Z] = np.clip(np.array(orig) + a, 0, 255).astype(np.uint8)
    for (x, y, z, c) in srcs:
        W.C[x, y, z] = c
        stored[(x, y, z)] = tuple(c)
    return stored, len(srcs)


def main(out, veg_seed=None):
    t0 = time.time()
    os.makedirs(out, exist_ok=True)
    if veg_seed is None:
        veg_seed = int.from_bytes(os.urandom(4), 'little')
    rng_layout = np.random.default_rng(SPEC['layout_seed'])
    W = World()
    W.H = terrain.build_height()
    bed = terrain.ground_colours(W)
    terrain.paint_bed(W, bed)
    for pts, w in PATHS:
        paint_path(W, pts, w, rng_layout)
    # ---- set pieces (west half) ----
    B.bloomhop_keep(W)
    B.castle_cellar(W)
    B.anchor_dressing(W)
    B.toy_hill(W)
    B.mushroom_cottage(W, 178, 192, (222, 104, 74), door_dir=(0, 1), seed=3)
    B.mushroom_cottage(W, 182, 322, (98, 168, 160), door_dir=(0, -1), seed=4)
    B.stepblock_lookout(W, 202, 136)
    B.mushroom_gate(W)
    B.toy_wall_ruin(W, 214, 206, 1)
    B.toy_wall_ruin(W, 214, 300, 3)
    B.brick_arch(W, 162, 209, along='x', span=9, height=8)
    B.brick_arch(W, 196, 311, along='x', span=9, height=8)
    B.brick_arch(W, 98, 340, along='y', span=9, height=8)
    B.windmill(W)
    B.glowroot_tunnel(W)
    B.grotto_and_fort(W)
    B.ridge_stairs(W)
    B.hollow_log(W, 150, 112, 20, 'x')
    B.hollow_log(W, 54, 150, 16, 'y')
    B.hollow_log(W, 214, 384, 16, 'x')
    B.pond_crossings(W)
    for (x, y) in ((140, 233), (140, 279), (176, 234), (176, 278)):
        B.lantern_post(W, x, y, int(W.H[x, y]), 5)
    # ---- mirror x' = 511 - x ----
    W.S[256:] = W.S[255::-1]
    W.C[256:] = W.C[255::-1]
    W.H[256:] = W.H[255::-1]
    W.keep[256:] = W.keep[255::-1]
    W.glow = [g for g in W.glow if g[0] <= 255] + [(511 - x, y, z, c) for (x, y, z, c) in W.glow if x <= 255]
    blue = (52, 98, 214); red = (214, 60, 54)
    for (x, y, z) in W.banner:
        W.C[x, y, z] = blue
        W.C[511 - x, y, z] = red
    # ---- vegetation (non-deterministic) ----
    vrng = np.random.default_rng(veg_seed)
    counts = veg.plant_all(W, vrng, SPEC)
    # ---- sky decor + corner tag ----
    n_sky = sky_decor(W, np.random.default_rng(SPEC['layout_seed'] + 99))
    tag = corner_tag(W)
    # platform volume must stay clear
    x0, x1, y0, y1 = SPEC['platform']
    W.S[x0 - 1:x1 + 2, y0 - 1:y1 + 2, 0:3] = False
    removed, removed_vox, kept_float = remove_orphans(W)
    # glow source voxels excluded from shading
    for (x, y, z, c) in W.glow:
        if 0 <= x < 512 and 0 <= y < 512 and 0 <= z < 64:
            W.nolight[x, y, z] = True
    W.S[:, :, 63] = True  # bottom layer solid (water where z62 is air)
    surf = lighting(W)
    stored, nsrc = bake_glow(W, surf)
    data = vxlcore.encode(W.S, W.C)
    name = 'bloomhop_kingdom'
    with open(os.path.join(out, name + '.vxl'), 'wb') as fh:
        fh.write(data)
    sha = hashlib.sha256(data).hexdigest()
    # .txt
    glow_txt = '{' + ', '.join(f'({x}, {y}, {z}): ({c[0]}, {c[1]}, {c[2]})' for (x, y, z), c in sorted(stored.items())) + '}'
    txt = f"""name = 'Bloomhop Kingdom'
version = '1.0'
author = 'shywolf91 + AI'
description = 'Platformer-world Babel: build from the meadow terraces below the castle keeps up to the sky platform.'
fog = {SPEC['fog']}
extensions = {{
    'babel': True,
    'water_damage': {SPEC['water_damage']},
    'heavens_color': {SPEC['heavens']},
    'glow_enabled': True,
    'glow_stored_colors': {glow_txt},
}}
# No get_spawn_location / get_entity_location hooks (owner rule): babel_script defaults place bases and spawns.
"""
    with open(os.path.join(out, name + '.txt'), 'w') as fh:
        fh.write(txt)
    np.save(os.path.join(out, '_H.npy'), W.H)
    build = dict(map=SPEC['name'], layout_seed=SPEC['layout_seed'], veg_seed=veg_seed, sha256=sha, bytes=len(data),
                 vegetation=counts, sky_pieces=n_sky, kept_floating=kept_float, orphans_removed=removed,
                 orphan_voxels_removed=removed_vox, glow_sources=nsrc, glow_stored=len(stored), corner_tag=tag,
                 seconds=round(time.time() - t0, 1))
    with open(os.path.join(out, 'build.json'), 'w') as fh:
        json.dump(build, fh, indent=1)
    print(json.dumps({k: v for k, v in build.items() if k != 'kept_floating'}, indent=1))
    print('kept floating pieces:', len(kept_float))


if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else None)
