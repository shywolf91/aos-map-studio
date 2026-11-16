"""Bloomhop Kingdom heightfield + ground materials. Author west half (x <= 255), mirror x' = 511 - x."""
import numpy as np
from noise import fbm, value_noise
from spec import SPEC

LAYOUT_SEED = SPEC['layout_seed']


def superellipse(xs, ys, cx, cy, rx, ry, p=4):
    return (np.abs(xs - cx) / rx) ** p + (np.abs(ys - cy) / ry) ** p


def build_height():
    sx = 256
    xs, ys = np.meshgrid(np.arange(sx, dtype=float), np.arange(512, dtype=float), indexing='ij')
    dy = np.abs(ys - 255.5)
    n1 = fbm((sx, 512), 48, LAYOUT_SEED)
    n2 = fbm((sx, 512), 14, LAYOUT_SEED + 7)
    h = 56.4 + 1.1 * n1 + 0.5 * n2  # rolling valley z ~55-58

    # --- ring hills (terraced, 2-voxel steps) ---
    e = np.minimum(np.minimum(xs, ys), 511 - ys)
    nr = fbm((sx, 512), 30, LAYOUT_SEED + 3)
    ring = np.clip((36 + 8 * nr - e) / 36, 0, 1)
    hr = 56 - (ring ** 1.25) * (34 + 4 * nr)
    hr = np.floor(hr / 2) * 2
    h = np.minimum(h, np.where(ring > 0, hr, 99))

    # --- north flank dome hills (outside the lane y 70-110) ---
    rng = np.random.default_rng(LAYOUT_SEED + 11)
    domes = [(70, 52, 16, 14), (112, 42, 20, 17), (160, 54, 14, 11), (200, 40, 18, 15), (236, 50, 12, 9),
             (92, 124, 13, 9), (146, 126, 11, 7), (196, 128, 12, 8),
             # south side domes, beyond the ridge
             (110, 470, 16, 13), (170, 474, 18, 15), (226, 468, 13, 10)]
    SPEC['domes'] = domes
    for cx, cy, r, ht in domes:
        d = np.hypot(xs - cx, ys - cy) / r
        dome = 56.5 - ht * np.sqrt(np.clip(1 - d * d, 0, 1))
        dome = np.floor(dome)
        h = np.where(d < 1, np.minimum(h, dome), h)

    # --- windmill knoll on the centre line (256, 84) ---
    d = np.hypot(xs - 255.5, ys - 84)
    knoll = np.where(d < 10, 47, 47 + (d - 10) * 0.55)
    h = np.minimum(h, np.floor(knoll))

    # --- Bramble Ridge (south flank), y 400-440, top ~z 38 ---
    nri = fbm((sx, 512), 20, LAYOUT_SEED + 5)
    ry = np.abs(ys - 421)
    ridge_on = (xs >= 84)
    xfade = np.clip((xs - 84) / 26, 0, 1)
    ridge_top = 39 + 1.5 * nri + (1 - xfade) * 14
    side = np.clip(ry - 13, 0, None)
    hrid = ridge_top + side * 2.2  # steep sides
    hrid = np.where(side > 0, np.floor(hrid / 2) * 2, np.floor(hrid))
    h = np.where(ridge_on, np.minimum(h, hrid), h)

    # --- spawn plateau (castle hill) x 30-152, y 200-312 at z 46 ---
    sp = SPEC['spawn_z']
    ne = fbm((sx, 512), 16, LAYOUT_SEED + 13)
    dxo = np.clip(xs - 152 - 3 * ne * (dy > 40), 0, None)
    dyo = np.clip(dy - 56 - 6 * ne, 0, None)
    plat = sp + np.sqrt((dxo * 0.5) ** 2 + (dyo * 0.75) ** 2)
    hump = value_noise((sx, 512), 9, LAYOUT_SEED + 9)
    plat_core = (dxo == 0) & (dyo == 0)
    plat = np.where(plat_core & (hump > 0.55), sp - 1, plat)
    plat = np.floor(plat)
    h = np.minimum(h, plat)

    # --- tower terrace / anchor x 152-212, y 226-286 at z 54; sheer east face at x 213 ---
    tz = SPEC['tower_z']
    dyt = np.clip(dy - 30, 0, None)
    terr = tz + dyt * 0.5
    terr = np.where((xs >= 150) & (xs <= 212), np.floor(terr), 99)
    h = np.minimum(h, terr)
    # centre floor in front of the anchor wall: fixed z 57 so the wall is a clean 3-voxel face
    cz = SPEC['centre_z']
    under = (xs >= 213) & (dy < 46)
    h = np.where(under, np.maximum(np.minimum(h, cz), cz), h)
    h = np.where(under, cz, h)

    # --- low meadow mounds in the centre zone (1-voxel terraces) ---
    for (cx, cy, r, ht) in ((140, 178, 11, 3), (204, 172, 8, 3), (148, 340, 11, 3), (212, 352, 8, 2),
                            (118, 138, 13, 4), (122, 374, 13, 4), (60, 180, 10, 3), (64, 330, 10, 3)):
        d = np.hypot(xs - cx, ys - cy) / r
        mound = 56.6 - ht * np.clip(1 - d * d, 0, 1) ** 0.7
        h = np.where(d < 1, np.minimum(h, np.floor(mound)), h)

    # --- ponds (water at z 63) with 1-voxel bank steps ---
    for (cx, cy, rx, ryy) in SPEC['ponds']:
        se = superellipse(xs, ys, cx, cy, rx, ryy, 3)
        r = np.sqrt(se) if False else se ** (1 / 3)
        dist = (r - 1) * min(rx, ryy)  # approx voxels outside the edge
        bank = np.where(dist <= 0, 63, 62 - np.floor(dist / 1.4))
        h = np.where(dist < 8, np.maximum(h, bank), h)

    h = np.clip(np.round(h), 8, 63).astype(np.int16)
    full = np.zeros((512, 512), np.int16)
    full[:256] = h
    full[256:] = h[::-1]
    return full


def ground_colours(W):
    """Fill terrain columns z H..63 with layered materials (grass/dirt/stone/sand)."""
    H = W.H
    full_g = fbm((512, 512), 40, LAYOUT_SEED + 21)
    full_g2 = fbm((512, 512), 11, LAYOUT_SEED + 22)
    g = 0.5 + 0.5 * full_g
    g = (g + g[::-1]) / 2  # mirror-coherent
    # vectorised colouring
    Z = np.arange(64)[None, None, :]
    depth = Z - H[:, :, None]
    xs = np.arange(512)[:, None, None]; ys = np.arange(512)[None, :, None]
    solid = depth >= 0
    # dirt base with structured banding (classic platformer soil)
    soil = np.array([152, 100, 60], float)
    soil_dk = np.array([126, 80, 48], float)
    soil_lt = np.array([178, 126, 78], float)
    band = ((Z // 3) % 2 == 0)
    dots = (((xs + 2 * Z) % 6 == 0) & ((ys + Z) % 5 == 0)) | (((ys + 2 * Z + 3) % 6 == 0) & ((xs + Z + 2) % 5 == 0))
    col = np.where(band[..., None], soil_dk, soil)
    col = np.broadcast_to(col, (512, 512, 64, 3)).astype(np.float32)
    col[np.broadcast_to(dots, (512, 512, 64))] = soil_lt
    # deep rock
    rock = np.array([124, 112, 108], float)
    deep = depth >= 12
    col[deep] = rock
    # grass top + lip
    grass_a = np.array([96, 170, 62], float)
    grass_b = np.array([132, 196, 70], float)
    gg = np.clip(g + 0.12 * full_g2, 0, 1)
    gcol = grass_a[None, None, :] * (1 - gg[..., None]) + grass_b[None, None, :] * gg[..., None]
    # height tint: higher ground a little sunnier/yellower, low meadows lusher
    th = np.clip((56 - H) / 34.0, -0.3, 1)[..., None].astype(np.float32)
    sunny = np.array([168, 204, 92], float); lush = np.array([70, 142, 62], float)
    gcol = np.where(th > 0, gcol * (1 - th * 0.45) + sunny * th * 0.45, gcol * (1 + th) - lush * th)
    # lush meadow patches (slow field)
    lp = fbm((512, 512), 26, LAYOUT_SEED + 23); lp = (lp + lp[::-1]) / 2
    lpw = np.clip((lp - 0.15) * 3, 0, 1)[..., None] * 0.5
    gcol = gcol * (1 - lpw) + lush * lpw
    # mowed stripes on the castle-hill plateau (4-wide bands, low contrast)
    xs2 = np.arange(512)[:, None]; ys2 = np.arange(512)[None, :]
    stripe = (((xs2 + ys2) // 5) % 2 == 0) & (H <= 46)
    gcol[stripe] = gcol[stripe] * 0.93
    top = depth == 0
    lip = depth == 1
    col[top] = np.broadcast_to(gcol[:, :, None, :], (512, 512, 64, 3))[top]
    col[lip] = (np.broadcast_to(gcol[:, :, None, :], (512, 512, 64, 3))[lip] * 0.93)
    # sand near water (H >= 60)
    sandy = (H >= 60)[:, :, None] & (depth <= 2)
    sand = np.array([224, 202, 146], float)
    col[sandy] = sand
    # pond beds (H == 63): painted water bed
    bed = (H == 63)
    W.C[:] = np.clip(col, 0, 255).astype(np.uint8)
    W.S[:] = solid
    return bed


def paint_bed(W, bed):
    """Painted pond beds: shallow sand-teal near banks to deep teal in the middle."""
    from scipy import ndimage
    dist = ndimage.distance_transform_edt(bed)
    t = np.clip(dist / 14, 0, 1)
    shallow = np.array([110, 196, 186]); deep = np.array([34, 112, 140])
    c = shallow[None, None, :] * (1 - t[..., None]) + deep[None, None, :] * t[..., None]
    rip = (np.sin(np.arange(512)[None, :] / 3.0 + np.arange(512)[:, None] / 7.0) > 0.93) & (t > 0.2)
    c[rip] = c[rip] * 1.12
    W.C[:, :, 63][bed] = np.clip(c[bed], 0, 255).astype(np.uint8)
