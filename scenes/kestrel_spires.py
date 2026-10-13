"""KESTREL SPIRES - Babel map (stock piqueserver 1.4.2 babel + babel_script). GRAYBOX v1.

Spatial specification lives in SPEC (single source of truth for geometry, checks and docs).
The west half is authored and mirrored x' = 512 - x, matching the script's bases (118 <-> 394).
Coordinates: x, y 0..511; z 0..63 with z = 0 the sky (smaller z = higher).

Run: python scenes/kestrel_spires.py out/kestrel_spires
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aosmap.scene import Scene, Material          # noqa: E402
from aosmap import art                            # noqa: E402

SEED = 7317

SPEC = {
    'mode': 'babel (stock piqueserver 1.4.2: game_modes.babel + scripts.babel_script)',
    'script_constants': {'platform_x': (206, 305), 'platform_y': (240, 271), 'platform_z': 1,
                         'intel': (256, 256), 'bases': ((118, 256), (394, 256)), 'spawn_half': 20},
    'play_space': {'x': (20, 492), 'y': (172, 340)},
    'canyon_floor_z': 56,
    'river_x_west': (228, 255),            # mirrored -> 257..284 ; water under the platform
    'bank_x_west': (214, 227),             # stepped banks 56 -> 61 so players can climb out
    'mesa': {'center': (112, 256), 'radii': (54, 52), 'deck_z': 10,
             'back_terraces': [(1.0, 1.12, 15), (1.12, 1.24, 21)]},   # (r0, r1, top z) behind/beside
    'spawn_plaza': {'x': (98, 138), 'y': (236, 276), 'z': 10},
    'arch': {'x': (164, 171), 'y': (252, 260), 'deck_from_z': 10, 'deck_to_z': 13, 'thickness': 3},
    'spire': {'center': (178, 256), 'r': 6.5, 'top_z': 13},
    'fingers': [{'center': (168, 226), 'r': 4.5, 'top_z': 17, 'ramp_y': (224, 228)},
                {'center': (168, 286), 'r': 4.5, 'top_z': 17, 'ramp_y': (284, 288)}],
    'slot_stair': {'x_top': 132, 'x_bottom': 86, 'y': (214, 217), 'exit_y': (195, 217)},
    'outer_walls': {'y_north': (150, 171), 'y_south': (341, 362), 'top_z': 6},
    'fog': (196, 170, 140),
}

GRAY = {  # graybox colours by FUNCTION (not art)
    'canyon': (196, 178, 140), 'cliff': (150, 132, 112), 'deck': (205, 160, 110),
    'spawn': (110, 140, 190), 'route': (225, 205, 120), 'bridgehead': (200, 90, 70),
    'flank': (210, 140, 60), 'terrace': (170, 150, 120), 'wall': (120, 112, 104), 'bank': (180, 170, 140),
}


def build_graybox(mirror_output=True):
    s = Scene('kestrel_spires', seed=SEED)
    M = {k: s.material(Material(k, v)) for k, v in GRAY.items()}
    X, Y = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    zz = np.arange(64)
    west = X <= 255
    ps = SPEC['play_space']
    floor_z = SPEC['canyon_floor_z']

    # --- canyon floor (grounded slab 56..62) across the play space
    floor = west & (X >= ps['x'][0]) & (Y >= ps['y'][0]) & (Y <= ps['y'][1])
    s.mat[floor[:, :, None] & (zz >= floor_z)[None, None, :]] = M['canyon']
    # stepped banks down to the river, then open water under the platform
    b0, b1 = SPEC['bank_x_west']
    for x in range(b0, b1 + 1):
        top = floor_z + int(round((x - b0) * 5 / (b1 - b0)))       # 56 .. 61
        col = (np.arange(512) >= ps['y'][0]) & (np.arange(512) <= ps['y'][1])
        s.mat[x, col, :top] = 0
        s.mat[x, col, top:63] = M['bank']
    r0, r1 = SPEC['river_x_west']
    s.mat[r0:r1 + 1, :, :] = 0

    # --- outer canyon walls (scenery backdrop, sheer, not walkable from the floor)
    ow = SPEC['outer_walls']
    for (y0, y1) in (ow['y_north'], ow['y_south']):
        n = art.fbm(X, Y, None, scale=14, octaves=3, seed=SEED + y0)
        band = west & (X >= ps['x'][0]) & (Y >= y0) & (Y <= y1)
        top = np.rint(ow['top_z'] + 6 * n).astype(int)
        s.mat[band[:, :, None] & (zz[None, None, :] >= top[:, :, None])] = M['wall']

    # --- mesa: deck z 10 inside r < 1, back terraces outside on the west / north / south only
    mc, (ra, rb) = SPEC['mesa']['center'], SPEC['mesa']['radii']
    n = (art.fbm(X, Y, None, scale=20, octaves=3, seed=SEED + 1) - 0.5) * 0.18
    d = np.sqrt(((X - mc[0]) / ra) ** 2 + ((Y - mc[1]) / rb) ** 2) + n
    deck = d < 1.0
    s.mat[deck[:, :, None] & (zz >= SPEC['mesa']['deck_z'])[None, None, :]] = M['cliff']
    s.mat[deck, SPEC['mesa']['deck_z']] = M['deck']
    behind = X < mc[0] + 20                                           # terraces not on the inner face
    for (q0, q1, tz) in SPEC['mesa']['back_terraces']:
        band = (d >= q0) & (d < q1) & behind & west
        s.mat[band[:, :, None] & (zz >= tz)[None, None, :]] = M['cliff']
        s.mat[band, tz] = M['terrace']
    sp = SPEC['spawn_plaza']
    s.box(sp['x'][0], sp['x'][1], sp['y'][0], sp['y'][1], sp['z'], sp['z'], M['spawn'])

    # --- sentinel spire + natural arch from the inner rim (deck steps 10 -> 13)
    spc = SPEC['spire']
    spire = np.sqrt((X - spc['center'][0]) ** 2 + (Y - spc['center'][1]) ** 2) < spc['r']
    s.mat[spire[:, :, None] & (zz >= spc['top_z'])[None, None, :]] = M['cliff']
    s.mat[spire, spc['top_z']] = M['bridgehead']
    a = SPEC['arch']
    x_rim = int(np.max(np.nonzero(deck[:, 256])[0]))                  # inner deck edge at y 256
    for x in range(x_rim - 1, spc['center'][0]):
        zt = a['deck_from_z'] + min(3, max(0, (x - x_rim) // 2))
        s.box(x, x, a['y'][0], a['y'][1], zt, zt + a['thickness'] - 1, M['cliff'])
        s.box(x, x, a['y'][0], a['y'][1], zt, zt, M['route'])
        s.mat[x, a['y'][0]:a['y'][1] + 1, :zt] = 0                    # clear anything above the walkway
    SPEC['arch']['x'] = (x_rim - 1, spc['center'][0] - 1)

    # --- flank fingers: lower pillars reached by stepped buttress ramps hugging the cliff
    for f in SPEC['fingers']:
        fc = f['center']
        pil = np.sqrt((X - fc[0]) ** 2 + (Y - fc[1]) ** 2) < f['r']
        s.mat[pil[:, :, None] & (zz >= f['top_z'])[None, None, :]] = M['cliff']
        s.mat[pil, f['top_z']] = M['flank']
        y0, y1 = f['ramp_y']
        x_edge = int(np.max(np.nonzero(deck[:, (y0 + y1) // 2])[0]))
        x = x_edge - 1
        z = SPEC['mesa']['deck_z']
        while x < fc[0] - 2:
            s.box(x, x, y0, y1, z, 62, M['cliff'])
            s.box(x, x, y0, y1, z, z, M['route'])
            s.mat[x, y0:y1 + 1, :z] = 0
            x += 1
            if (x - x_edge) % 2 == 0 and z < f['top_z']:
                z += 1

    # --- slot stair: a 4-wide gully cut down through the mesa's north flank, 1-voxel steps
    st = SPEC['slot_stair']
    y0, y1 = st['y']
    for x in range(st['x_bottom'], st['x_top'] + 1):
        fz = SPEC['mesa']['deck_z'] + (st['x_top'] - x)                 # 10 at top .. 56 at bottom
        fz = min(fz, floor_z)
        s.mat[x, y0:y1 + 1, :fz] = 0
        s.mat[x, y0:y1 + 1, fz] = M['route']
    # exit tunnel: from the stair foot head north until the columns above the floor are open sky,
    # so the gully always breaks out onto the canyon floor (terraces may wrap the mesa base)
    xb = st['x_bottom']
    y = st['y'][0] - 1                       # start beside the stair foot; never overwrite its steps
    while y > ps['y'][0]:
        cols = s.mat[xb:xb + 4, y, :floor_z]
        s.mat[xb:xb + 4, y, floor_z - 4:floor_z] = 0
        s.mat[xb:xb + 4, y, floor_z] = M['route']
        if y < st['y'][0] - 2 and not cols.any():
            break
        y -= 1
    SPEC['slot_stair']['exit_y'] = (y, st['y'][1])
    s.markers['deck_mask'] = deck
    if mirror_output:
        mirror(s)
    return s


def mirror(s):
    s.mat[257:512] = s.mat[1:256][::-1]
    s.mat[256] = s.mat[255]                 # the axis column itself (otherwise left empty)


def metadata_txt(fog=None):
    from aosmap.meta import map_txt
    # CTF fallback hooks (ignored in babel mode: babel_script replaces them on map change)
    spawns = {0: [(x, y, 10) for x in (104, 112, 120, 128) for y in (242, 256, 270)],
              1: [(512 - x, y, 10) for x in (104, 112, 120, 128) for y in (242, 256, 270)]}
    ents = {0: (76, 256, 10), 1: (436, 256, 10), 2: (118, 256, 10), 3: (394, 256, 10)}
    return map_txt(
        name='Kestrel Spires', author='aosmap (graybox v1)', version='0.1',
        description='Babel: build from your mesa spire to the sky platform. Graybox - layout only.',
        header='Generated by scenes/kestrel_spires.py (seed %d). Babel mode replaces the hooks below;\n'
               'they exist only as a CTF fallback and are not balanced/tested for CTF.' % SEED,
        fog=fog or SPEC['fog'], extensions={'babel': True, 'water_damage': 0},
        spawns=spawns, entities=ents)


if __name__ == '__main__':
    from aosmap.vxl import write_vxl
    out = sys.argv[1] if len(sys.argv) > 1 else 'out/kestrel_spires'
    os.makedirs(out, exist_ok=True)
    s = build_graybox()
    vm = s.to_voxelmap()
    data = write_vxl(vm)
    open(os.path.join(out, 'kestrel_spires.vxl'), 'wb').write(data)
    open(os.path.join(out, 'kestrel_spires.txt'), 'w').write(metadata_txt())
    json.dump(SPEC, open(os.path.join(out, 'spec.json'), 'w'), indent=1, default=list)
    print('written', len(data), 'bytes; arch x', SPEC['arch']['x'])
