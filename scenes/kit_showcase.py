"""Art-kit showcase (NOT a gameplay map): exercises terrain, shaders and prefabs.

Run: python scenes/kit_showcase.py out/kit_showcase
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aosmap.scene import Scene, Material                       # noqa: E402
from aosmap import art                                         # noqa: E402

SEED = 4242


def build():
    s = Scene('aosmap_kit_showcase', seed=SEED)
    S = art.SurfaceShader
    grass = s.material(Material('grass', (110, 140, 70), shader=S(
        top=['#4b6636', '#6a8743', '#93a157'], side=['#5a4a35', '#6e5a40'], z_range=(60, 30),
        height_w=0.45, noise_w=0.55, noise_scale=20)))
    soil = s.material(Material('soil', (110, 90, 60), shader=S(
        top=['#6e5a40', '#80694a'], side=['#5a4a35', '#6e5a40', '#7b6648'], noise_scale=6, height_w=0.2)))
    rock = s.material(Material('rock', (130, 120, 108), shader=S(
        top=['#7d766c', '#9a9284', '#b3aa98'], side=['#5f594f', '#7d766c', '#8f8779'],
        z_range=(62, 20), noise_scale=5, noise_w=0.6, occ_dark=0.45)))
    deep = s.material(Material('deep', (90, 80, 70), shader=S(top=['#5f594f'], side=['#4c463e', '#5f594f'],
                                                               noise_scale=8)))
    trunk = s.material(Material('trunk', (90, 64, 48), shader=S(top=['#6e4e3a'], side=['#4f3829', '#6a4b37'],
                                                                 noise_scale=3, height_w=0)))
    leaf = s.material(Material('leaf', (80, 110, 50), shader=S(
        top=['#4f7a34', '#6c9440', '#8fae52'], side=['#33512a', '#46672f', '#5c7f38'], z_range=(55, 30),
        noise_scale=6, noise_w=0.6, height_w=0.3, occ_dark=0.45)))
    plaster = s.material(Material('plaster', (210, 200, 175), shader=S(
        top=['#d8ccb0'], side=['#c9bc9f', '#ddd2b7'], noise_scale=7, height_w=0, occ_dark=0.3)))
    roof = s.material(Material('roof', (130, 60, 45), shader=S(
        top=['#7c3a2c', '#934733', '#a85a3c'], side=['#5e2b21', '#753629'], noise_scale=5, height_w=0.2,
        steps=4)))
    timber = s.material(Material('timber', (75, 58, 45), shader=S(top=['#56402f'], side=['#3f2f23', '#4b382a'],
                                                                   noise_scale=4, height_w=0)))
    glass = s.material(Material('glass', (80, 110, 125), shader=S(top=['#4d6a78'], side=['#3c5763', '#4d6a78'],
                                                                   noise_scale=2, height_w=0, occ_dark=0)))

    # island mask: soft ellipse around the centre, with noisy shore
    xs, ys = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    d = np.sqrt(((xs - 256) / 120.0) ** 2 + ((ys - 256) / 90.0) ** 2)
    shore = art.fbm(xs, ys, None, scale=40, octaves=3, seed=SEED + 3) * 0.35
    mask = np.clip((1.0 - d + shore) * 2.2, 0, 1)
    H = art.heightfield(SEED, base_z=54, amp=24, scale=110, octaves=5, terrace=3, mask=mask, shore_z=61.5)
    land = mask > 0.08
    H = np.where(land, H, 63)                                     # sea elsewhere
    sand = s.material(Material('sand', (200, 185, 140), shader=S(
        top=['#b9a77c', '#cdbd92'], side=['#9c8b63', '#b09f75'], noise_scale=9, height_w=0.3, z_range=(62, 58))))
    art.apply_heightfield(s, np.minimum(H, 62), grass, soil, deep, sub_depth=3, cliff_mid=rock, cliff_slope=3,
                          region=(100, 140, 412, 372))
    beach = land & (H >= 60)
    for z in range(58, 63):                                     # sand on the lowest shore band
        sel = beach & (H == z)
        s.mat[sel, z] = sand
    s.mat[:, :, :][~land[:, :, None].repeat(64, 2)] = 0          # clear sea columns fully
    # beach rim: lowest band becomes soil-coloured sand-ish rock edge
    rng = np.random.default_rng(SEED)
    top = H
    # trees on gentle grass, avoid steep and very high ground
    placed = 0
    cand = np.argwhere(land & (top < 59) & (top > 38))
    grove = art.fbm(cand[:, 0], cand[:, 1], None, scale=45, octaves=2, seed=SEED + 21)
    cand = cand[grove > np.quantile(grove, 0.55)]               # trees cluster into groves
    rng.shuffle(cand)
    used = np.zeros((512, 512), bool)
    for x, y in cand:
        if placed >= 34:
            break
        if used[max(x - 5, 0):x + 6, max(y - 5, 0):y + 6].any():
            continue
        win = top[x - 2:x + 3, y - 2:y + 3]
        if win.max() - win.min() > 1:
            continue
        pf = art.tree(SEED + placed, trunk, leaf, height=int(rng.integers(8, 13)), crown_r=rng.uniform(4.5, 6.0),
                      crown_h=5, lean=rng.uniform(-1, 1))
        art.stamp(s, pf, int(x), int(y), int(top[x, y]))
        used[x - 3:x + 4, y - 3:y + 4] = True
        placed += 1
    # boulders scattered near cliffs
    cliff_cols = np.argwhere((s.mat == rock).any(axis=2))
    rng.shuffle(cliff_cols)
    for i, (x, y) in enumerate(cliff_cols[:10]):
        art.stamp(s, art.boulder(SEED + 100 + i, rock, r=rng.uniform(2.0, 3.2)), int(x), int(y), int(top[x, y]))
    # two houses on the flattest high terrace areas: flatten pads first (grounded foundations)
    houses = 0
    for x, y in np.argwhere(land & (top <= 52)):
        if houses >= 2:
            break
        if used[x - 8:x + 9, y - 7:y + 8].any():
            continue
        pad = top[x - 6:x + 7, y - 5:y + 6]
        if pad.size == 0 or pad.max() - pad.min() > 3:
            continue
        z = int(pad.max())                                      # lowest point of the pad -> fill up to it
        s.mat[x - 6:x + 7, y - 5:y + 6, z:63] = np.where(s.mat[x - 6:x + 7, y - 5:y + 6, z:63] == 0, soil,
                                                          s.mat[x - 6:x + 7, y - 5:y + 6, z:63])
        s.mat[x - 6:x + 7, y - 5:y + 6, :z] = 0
        s.mat[x - 6:x + 7, y - 5:y + 6, z] = grass
        art.stamp(s, art.house(SEED + houses, plaster, roof, timber, w=9, d=7, wall_h=5, window_mid=glass),
                  int(x), int(y), z)
        used[x - 9:x + 10, y - 8:y + 9] = True
        houses += 1
    s.markers = {'crop': (100, 140, 412, 372), 'trees': placed, 'houses': houses}
    return s


if __name__ == '__main__':
    import json
    from aosmap.vxl import write_vxl, read_vxl
    from aosmap.validate import floating_components
    from aosmap.render import isometric, top_down
    out = sys.argv[1] if len(sys.argv) > 1 else 'out/kit_showcase'
    os.makedirs(out, exist_ok=True)
    sc = build()
    vm = sc.to_voxelmap()
    data = write_vxl(vm)
    path = os.path.join(out, 'aosmap_kit_showcase.vxl')
    open(path, 'wb').write(data)
    back, rep = read_vxl(data)
    fl = floating_components(vm.solid)
    print(json.dumps({'bytes': len(data), 'reader_ok': rep.ok, 'floating': fl[:5], 'n_floating': len(fl),
                      'markers': {k: v for k, v in sc.markers.items() if k != 'crop'}}, default=str))
    c = sc.markers['crop']
    isometric(back, crop=c, view=0, s=3).save(os.path.join(out, 'iso0.png'))
    isometric(back, crop=c, view=2, s=3).save(os.path.join(out, 'iso2.png'))
    top_down(back, crop=c, scale=2).save(os.path.join(out, 'top.png'))
