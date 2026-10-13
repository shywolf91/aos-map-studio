"""Three original Babel concept GRAYBOXES (layout only, flat colours - not art).

Stock piqueserver 1.4.2 babel + babel_script constraints used:
  platform x 206-305, y 240-271, z 1 (script-generated); single intel at (256, 256) on it;
  bases / spawn squares +-20 around (118, 256) and (394, 256); spawns use the topmost voxel.
Each map is authored on the west half and mirrored x' = 512 - x (bases mirror exactly).

Run: python scenes/babel_concepts.py out/babel_concepts
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aosmap.scene import Scene, Material          # noqa: E402
from aosmap import art                            # noqa: E402

GB = {   # graybox palette: flat, distinct, readable - deliberately not art
    'ground': (120, 140, 95), 'cliff': (150, 140, 125), 'deck': (170, 150, 110), 'stone': (185, 180, 170),
    'accent': (190, 120, 80), 'sand': (200, 185, 140), 'spawn': (90, 120, 170),
}


def _mats(s):
    return {k: s.material(Material(k, v)) for k, v in GB.items()}


def mirror(s):
    s.mat[257:512] = s.mat[1:256][::-1]


def _xy():
    return np.meshgrid(np.arange(512), np.arange(512), indexing='ij')


def concept_a(seed=101):
    """KESTREL SPIRES - sky-high mesa babel. Each base is a broad sandstone mesa (top z 10) with
    terraced shelves; a walkable rock arch leads out to a sentinel spire (top z 13) 30 voxels
    from the platform edge. A deep canyon river under the platform offers a dangerous low
    flank to reach and cut enemy towers. Build challenge: ~30 horizontal + ~12 vertical."""
    s = Scene('babel_concept_a_kestrel_spires', seed=seed); M = _mats(s)
    X, Y = _xy()
    # canyon floor (sand banks) with a river through the middle (x 236-256 west half -> water)
    floor = (X < 256) & (np.abs(Y - 256) < 150)
    s.mat[floor[:, :, None].repeat(64, 2) & (np.arange(64) >= 54)] = M['sand']
    river = (X >= 232) & (X <= 256)
    s.mat[river, :] = 0                                  # open water lane (z62 air -> water)
    # mesa: rounded rectangle, cliffs, top z 10, a mid shelf at z 24 on the inner side
    d = np.sqrt(((X - 112) / 46.0) ** 2 + ((Y - 256) / 62.0) ** 2)
    n = art.fbm(X, Y, None, scale=18, octaves=3, seed=seed) * 0.25
    mesa = d + n < 1.0
    shelf = (d + n < 1.28) & ~mesa & (X > 100)
    for z in range(10, 63):
        s.mat[mesa, z] = M['cliff']
    for z in range(24, 63):
        s.mat[shelf, z] = M['cliff']
    s.mat[mesa, 10] = M['deck']; s.mat[shelf, 24] = M['ground']
    # sentinel spire + walkable natural arch from the mesa rim (deck z 13 -> spire)
    sp = np.sqrt((X - 176) ** 2 + (Y - 256) ** 2) < 6
    for z in range(13, 63):
        s.mat[sp, z] = M['stone']
    s.mat[sp, 13] = M['accent']
    for x in range(150, 172):                            # 3-wide arch deck, rising 1 per 7 voxels
        zt = 10 + (x - 150) // 7
        s.box(x, x, 252, 260, zt, zt + 2, M['stone'])
    s.box(150, 171, 252, 260, 12, 12, M['deck'])         # walking surface marker (graybox)
    # switchback trail from mesa top down the inner cliff to the shelf (descent route)
    for i in range(14):
        s.box(146 + (i % 2) * 0, 146, 230 - i * 2, 231 - i * 2, 10 + i, 62, M['deck'])
    mirror(s)
    return s, {'style': 'sky babel', 'theme': 'warm sandstone mesas, juniper, turquoise canyon river'}


def concept_b(seed=202):
    """BELLWATER - drowned stone city (ground babel). Each base is a canal quarter at z 54 around a
    tall bell tower (top deck z 20) that gives an early vantage but no route up. A lagoon fills
    the centre; a broken aqueduct (deck z 34) strides out toward the platform and stops 22
    voxels short, so towers start mid-height on its last pier - fights happen on the aqueduct."""
    s = Scene('babel_concept_b_bellwater', seed=seed); M = _mats(s)
    X, Y = _xy()
    quarter = (X < 200) & (np.abs(Y - 256) < 110)
    for z in range(54, 63):
        s.mat[quarter, z] = M['stone']
    s.mat[quarter, 54] = M['ground']
    canals = quarter & ((np.abs(Y - 226) < 3) | (np.abs(Y - 286) < 3) | (np.abs(X - 160) < 3))
    s.mat[canals, :] = 0
    # house blocks (graybox) lining the canals
    rng = np.random.default_rng(seed)
    for bx in range(60, 196, 14):
        for by in (196, 240, 262, 306):
            if abs(bx - 118) < 24 and abs(by - 256) < 24:
                continue                                  # keep the spawn square open
            if bx + 9 >= 120 and abs(by - 262) <= 8:
                continue                                  # keep the stair / aqueduct lane open
            h = int(rng.integers(5, 10))
            s.box(bx, bx + 9, by - 4, by + 4, 54 - h, 53, M['deck'])
            s.box(bx, bx + 9, by - 4, by + 4, 54 - h - 2, 54 - h - 1, M['accent'])
    # bell tower beside the spawn (solid, no ladder): vantage from z 20 deck via stairs
    s.box(124, 133, 284, 293, 20, 53, M['stone'])
    s.box(122, 135, 282, 295, 19, 19, M['accent'])
    # aqueduct: piers every 12 voxels from x 150 to 184, deck z 34 (reached by a stair at x 140)
    for px in range(150, 190, 12):
        s.box(px, px + 3, 252, 260, 35, 62, M['stone'])
    s.box(146, 185, 252, 260, 33, 34, M['stone'])
    for i in range(20):                                   # stair from quarter (z 54) to deck (z 34)
        s.box(126 + i, 126 + i, 262, 266, 53 - i, 53, M['deck'])
    s.box(146, 149, 256, 266, 33, 53, M['deck'])          # landing joining the stair top to the deck
    # lagoon: centre water (nothing at x 200-256)
    mirror(s)
    return s, {'style': 'ground babel (mid-height start)', 'theme': 'limestone canal city, verdigris roofs, teal lagoon'}


def concept_c(seed=303):
    """CAIRNFELL - highland babel. Each base is a hillfort on a ridge (top z 40) above a stream
    valley (z 56). In the valley centre stands a ring of grounded standing stones (tops z 30)
    directly under the platform: whoever controls the ring builds the shortest tower (29 up).
    Longer but safer towers can rise from the hillforts' inner walls."""
    s = Scene('babel_concept_c_cairnfell', seed=seed); M = _mats(s)
    X, Y = _xy()
    d = np.sqrt(((X - 256) / 210.0) ** 2 + ((Y - 256) / 150.0) ** 2)
    mask = np.clip((1 - d) * 3, 0, 1)
    ridge = np.exp(-((X - 118) / 55.0) ** 2) * np.exp(-((Y - 256) / 80.0) ** 2)
    H = 61.5 - (61.5 - 56) * np.clip(mask * 2, 0, 1) - 18 * ridge * mask \
        - 3 * (art.fbm(X, Y, None, scale=40, octaves=3, seed=seed) - 0.5) * mask
    H = np.clip(np.rint(H), 30, 62).astype(int)
    stream = np.abs(Y - 256 - 18 * np.sin(X / 23.0)) < 3
    land = mask > 0.02
    H = np.where(stream & (X > 180), 62, H)
    art.apply_heightfield(s, np.where(land, H, 63).clip(1, 62), M['ground'], M['cliff'], M['cliff'],
                          cliff_mid=M['cliff'], cliff_slope=3, region=(0, 0, 255, 511))
    s.mat[~land[:, :, None].repeat(64, 2)] = 0
    s.mat[(stream & (X > 180))[:, :, None].repeat(64, 2)] = 0
    # hillfort: ring wall on the ridge top, gate facing the valley
    fort = (np.abs(np.sqrt((X - 118) ** 2 + (Y - 256) ** 2) - 26) < 1.5) & (X < 256)
    for x, y in np.argwhere(fort):
        if x > 140 and abs(y - 256) < 4:
            continue
        top = int(np.argmax(s.mat[x, y] > 0))
        s.box(x, x, y, y, top - 5, top - 1, M['stone'])
    # standing-stone ring under the platform (west half of the ring; mirrored)
    for k in range(7):
        a = np.pi / 2 + k * np.pi / 6
        cx, cy = int(256 + 30 * np.cos(a)), int(256 + 20 * np.sin(a))
        if cx > 255:
            continue
        top = int(np.argmax(s.mat[cx, cy] > 0)) if (s.mat[cx, cy] > 0).any() else 62
        s.box(cx - 1, cx + 1, cy - 1, cy + 1, 30, 62, M['stone'])
        s.box(cx - 1, cx + 1, cy - 1, cy + 1, 30, 30, M['accent'])
    mirror(s)
    return s, {'style': 'ground babel (valley ring)', 'theme': 'moss highland, granite cairns, slate hillforts'}


if __name__ == '__main__':
    from aosmap.vxl import write_vxl, read_vxl
    from aosmap.validate import floating_components, check_babel
    from aosmap import nav
    from aosmap.render import isometric, top_down
    out = sys.argv[1] if len(sys.argv) > 1 else 'out/babel_concepts'
    os.makedirs(out, exist_ok=True)
    summary = {}
    for fn in (concept_a, concept_b, concept_c):
        sc, info = fn()
        vm = sc.to_voxelmap()
        data = write_vxl(vm)
        open(os.path.join(out, sc.name + '.vxl'), 'wb').write(data)
        back, rep = read_vxl(data)
        fl = floating_components(vm.solid)
        bab = check_babel(vm)
        route = nav.babel_route_check(vm.solid)
        summary[sc.name] = {'info': info, 'reader_ok': rep.ok, 'floating': len(fl),
                            'babel_findings': [f'{f.level}: {f.detail}' for f in bab.findings],
                            'route': route}
        # renders with a simulated platform so the layout reads correctly
        show = back
        show.solid[206:306, 240:272, 1] = True
        show.color[206:306, 240:272, 1] = 0x8000FFFF
        show.colored[206:306, 240:272, 1] = True
        top_down(show, crop=(20, 120, 491, 391), scale=2).save(os.path.join(out, sc.name + '_top.png'))
        isometric(show, crop=(20, 120, 491, 391), view=3, s=2).save(os.path.join(out, sc.name + '_iso.png'))
    json.dump(summary, open(os.path.join(out, 'summary.json'), 'w'), indent=1, default=str)
    for k, v in summary.items():
        print('==', k, v['info']['style'], '| floating', v['floating'], '| reader', v['reader_ok'])
        for f in v['babel_findings']:
            print('   ', f)
        for t, r in v['route'].items():
            print('   ', t, {kk: r[kk] for kk in ('platform_reachable_without_building', 'build_gap_voxels',
                                                 'gap_vertical', 'gap_horizontal', 'gap_from')})
