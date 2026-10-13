"""HOLLOWFEN - art pass v1 on the shared layout (scenes/hollowfen.py). Same gameplay geometry as the graybox
(terrain, lanes, plots, church massing + stair, cemetery walls, bogs, boardwalks), with detailed original assets.

Run: python scenes/hollowfen_art.py out/hollowfen
"""
import json
import os
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aosmap.scene import Scene, Material                                     # noqa: E402
from aosmap import art                                                       # noqa: E402
from aosmap.art import SurfaceShader, PatternShader, StrataShader           # noqa: E402
from scenes.hollowfen import (SPEC, G, SEED, Layout, ground, bogs, cemetery_wall, church, mirror,  # noqa: E402
                              metadata_txt)
from scenes import hollowfen_props as P                                      # noqa: E402


def _h(a, b, n):
    return ((a.astype(np.int64) * 73856093) ^ (b.astype(np.int64) * 19349663)) % n


def masonry(colours, block=(3, 2)):
    """Stone blocks: each block (block[0] along the wall, block[1] tall) gets one colour; courses offset."""
    bw, bh = block

    def fn(x, y, z):
        course = z // bh
        u = (x + y + (course % 2) * (bw // 2)) // bw
        return _h(u, course, len(colours))
    return PatternShader(colours, fn, side_dark=0.84, occ_dark=0.35)


def materials(s):
    A = lambda n, sh: s.material(Material(n, (128, 128, 128), shader=sh))     # noqa: E731
    SS = SurfaceShader
    m = {}
    m['grass'] = A('grass', SS(top=['#4b5733', '#56623a', '#626a3f', '#6f6b42'], side=['#4a3828', '#56412e'],
                                noise_scale=18, noise_w=0.85, height_w=0.15, occ_dark=0.3))
    m['forest'] = A('forest_floor', SS(top=['#4a3a26', '#5b4229', '#6b4b2b', '#4c4f31', '#3f4429'],
                                       side=['#463526', '#523e2b'], noise_scale=9, noise_w=0.9, height_w=0.1,
                                       occ_dark=0.35))
    m['soil'] = A('soil', SS(top=['#55412d'], side=['#4a3828', '#56412e', '#3f3023'], noise_scale=5, height_w=0))
    m['rock'] = A('rock', StrataShader(['#4d4852', '#57525b', '#45414a', '#5e5862'], pattern=(2, 3, 1, 2),
                                      crust='#5a5048', salt=11))
    m['cobble'] = A('cobble', PatternShader(['#67646d', '#726e78', '#5b5862', '#7c7782'],
                                            lambda x, y, z: _h((x + (y // 2) % 2) // 2, y // 2, 4), occ_dark=0.4))
    m['dirt'] = A('dirt_road', SS(top=['#4f3e2d', '#5d4935', '#6a543c', '#4a3a2b'], side=['#45362a'],
                                  noise_scale=4, noise_w=0.9, height_w=0, occ_dark=0.3))
    bx, by = SPEC['script_constants']['bases'][0]

    def flag(x, y, z):
        x = np.where(x > 255, 512 - x, x)
        r = np.maximum(np.abs(x - bx), np.abs(y - by))
        ring = (r % 8 == 0) | (r <= 1)
        return np.where(ring, 3, _h(x // 3, y // 3, 3))
    m['square'] = A('square_flags', PatternShader(['#706c78', '#7b7682', '#65616d', '#5a3d32'], flag, occ_dark=0.3))
    m['farm'] = A('farm_field', PatternShader(['#3e2f22', '#4a3826', '#3d4a26'],
                                              lambda x, y, z: np.where(y % 3 == 0, 2, _h(x // 4, y, 2))))
    m['cem'] = A('cemetery_grass', SS(top=['#39432d', '#434d33', '#4d5538', '#3d3f2b'], side=['#3e3124'],
                                      noise_scale=7, noise_w=0.9, height_w=0, occ_dark=0.3))
    m['cemwall'] = A('cemetery_wall', masonry(['#58545e', '#625d68', '#4f4b55', '#6a6570'], (3, 1)))
    m['bank'] = A('bog_mud', SS(top=['#3a3024', '#45392a', '#2f2a20'], side=['#2f271e', '#3a3024'],
                                noise_scale=5, noise_w=0.8, height_w=0, occ_dark=0.3))
    m['boardwalk'] = A('boardwalk', PatternShader(['#5a4632', '#4d3c2b', '#634d36'],
                                                  lambda x, y, z: _h(x, y // 4, 3), occ_dark=0.3))
    # church
    m['church'] = A('church_stone', masonry(['#6e6a78', '#77727f', '#625e6c', '#817c88']))
    m['church_trim'] = A('church_trim', masonry(['#8a8592', '#938e9a'], (2, 1)))
    m['stair'] = A('oak_stair', SS(top=['#5c4632', '#66503a'], side=['#4a3828'], noise_scale=3, height_w=0))
    m['belfry'] = A('belfry_planks', PatternShader(['#5a4632', '#4d3c2b'], lambda x, y, z: _h(x, y // 3, 2)))
    m['slate'] = A('slate', PatternShader(['#3a3644', '#433e4e', '#35313e', '#4a4456'],
                                          lambda x, y, z: _h(x // 2 + z, y + z, 4), side_dark=0.8, occ_dark=0.3))
    m['slate_ridge'] = A('slate_ridge', SS(top=['#2a2731'], side=['#26232c'], noise_scale=3, height_w=0))
    m['glass'] = [A('glass_violet', SS(top=['#6a2a7c'], side=['#6a2a7c', '#7c3490'], noise_scale=2, height_w=0, occ_dark=0)),
                  A('glass_amber', SS(top=['#c7741e'], side=['#c7741e', '#d98a2e'], noise_scale=2, height_w=0, occ_dark=0)),
                  A('glass_teal', SS(top=['#2a6f7a'], side=['#2a6f7a', '#348592'], noise_scale=2, height_w=0, occ_dark=0)),
                  A('glass_crimson', SS(top=['#8c2430'], side=['#8c2430', '#a02c3a'], noise_scale=2, height_w=0, occ_dark=0))]
    m['clock'] = A('clock_face', SS(top=['#d8cfb4'], side=['#d8cfb4', '#cfc5a8'], noise_scale=2, height_w=0, occ_dark=0))
    m['bronze'] = A('bell_bronze', SS(top=['#8a6a2e'], side=['#7a5c26', '#8f6e30'], noise_scale=2, height_w=0))
    # houses
    m['plasters'] = [A('plaster_' + n, SS(top=c, side=c, noise_scale=6, noise_w=0.6, height_w=0, occ_dark=0.35))
                     for n, c in (('bone', ['#b3a890', '#a99e88']), ('ochre', ['#a8915f', '#9c8656']),
                                  ('ash', ['#97948d', '#8b8882']), ('rose', ['#a0857b', '#957a70']),
                                  ('moss', ['#8f9278', '#83866d']))]
    m['roofs'] = [m['slate'],
                  A('roof_moss', PatternShader(['#3f4634', '#474f3a', '#383e2e'], lambda x, y, z: _h(x // 2 + z, y, 3))),
                  A('roof_thatch', PatternShader(['#6a5a3a', '#76653f', '#5e5035'], lambda x, y, z: _h(x, y + z, 3))),
                  A('roof_rust', PatternShader(['#5a3a32', '#653f36', '#4f332c'], lambda x, y, z: _h(x // 2 + z, y, 3)))]
    m['ridge'] = m['slate_ridge']
    m['timber'] = A('timber', SS(top=['#3a2a20'], side=['#2f221a', '#3a2a20'], noise_scale=3, height_w=0, occ_dark=0.2))
    m['stone'] = A('house_stone', masonry(['#5d5962', '#67626c', '#55515a'], (2, 1)))
    m['chimney_top'] = A('chimney_top', SS(top=['#2a2628'], side=['#3a3436'], noise_scale=2, height_w=0))
    m['win_lit'] = A('window_lit', SS(top=['#f0b04a'], side=['#f0b04a', '#ffc964'], noise_scale=2, height_w=0, occ_dark=0))
    m['win_dark'] = A('window_dark', SS(top=['#23202b'], side=['#23202b', '#2c2836'], noise_scale=2, height_w=0, occ_dark=0))
    # nature
    m['trunk'] = A('trunk', SS(top=['#4a3a2c'], side=['#3d3026', '#4a3a2c'], noise_scale=3, height_w=0, occ_dark=0.3))
    m['trunk_dark'] = A('trunk_dark', SS(top=['#3a2e26'], side=['#2f2620', '#3a2e26'], noise_scale=3, height_w=0))
    m['deadwood'] = A('deadwood', SS(top=['#4a4448'], side=['#3a3438', '#453f43'], noise_scale=3, height_w=0, occ_dark=0.2))
    m['leaves'] = [A('leaf_' + n, SS(top=c[:2], side=c[2:], noise_scale=4, noise_w=0.7, height_w=0.3,
                                     z_range=(57, 40), occ_dark=0.45))
                   for n, c in (('orange', ['#b8581f', '#d0752a', '#8f421a', '#a44d1e']),
                                ('red', ['#8e2e22', '#a83a26', '#6e241c', '#80291f']),
                                ('gold', ['#9c7424', '#b08630', '#76561c', '#86641f']),
                                ('rust', ['#7a4a26', '#8f5a2e', '#5e3a1f', '#6e4424']))]
    m['pine'] = A('pine', SS(top=['#25352b', '#2e4133'], side=['#1f2c24', '#283a2e'], noise_scale=3, noise_w=0.6,
                             height_w=0.3, z_range=(57, 38), occ_dark=0.45))
    m['bush'] = A('bush', SS(top=['#3d4a2a', '#4a4f2c', '#5a4a2a'], side=['#33402a'], noise_scale=3, height_w=0))
    m['reed'] = A('reed', SS(top=['#6a6a3a', '#7a7444'], side=['#5a5a32'], noise_scale=2, height_w=0))
    # halloween
    m['pumpkin'] = A('pumpkin', SS(top=['#d9741c'], side=['#c9661a', '#d9741c'], noise_scale=2, height_w=0, occ_dark=0.25))
    m['pumpkin_dark'] = A('pumpkin_rib', SS(top=['#b8561a'], side=['#a84e17'], noise_scale=2, height_w=0))
    m['stem'] = A('pumpkin_stem', SS(top=['#4a5a2a'], side=['#3f4d24'], noise_scale=2, height_w=0))
    m['glow'] = A('candle_glow', SS(top=['#ffd04d'], side=['#ffd04d', '#ffe27a'], noise_scale=2, height_w=0, occ_dark=0))
    m['iron'] = A('iron', SS(top=['#26232b'], side=['#1f1c24', '#2a2730'], noise_scale=2, height_w=0, occ_dark=0.1))
    m['rag'] = A('rag', SS(top=['#5a4a5e'], side=['#4f4053', '#5a4a5e'], noise_scale=2, height_w=0))
    m['hat'] = A('hat_black', SS(top=['#1f1a24'], side=['#1b1720', '#241e2a'], noise_scale=2, height_w=0, occ_dark=0))
    m['straw'] = A('straw', SS(top=['#c9a24a'], side=['#b38f3f', '#c9a24a'], noise_scale=2, height_w=0))
    m['grave'] = [A('grave_' + n, SS(top=c, side=c, noise_scale=3, noise_w=0.6, height_w=0, occ_dark=0.2))
                  for n, c in (('light', ['#a29fa6', '#96939b']), ('mid', ['#8a8792', '#7f7c86']),
                               ('moss', ['#7d8270', '#727765']), ('dark', ['#6a6670', '#5f5b66']))]
    m['marble'] = A('marble', SS(top=['#bdb8bd', '#b2adb3'], side=['#aaa5ac', '#b4afb5'], noise_scale=5, height_w=0, occ_dark=0.3))
    m['marble_dark'] = A('marble_dark', SS(top=['#8f8a92'], side=['#86818a'], noise_scale=3, height_w=0))
    m['mound'] = A('grave_mound', SS(top=['#3a2e22', '#43352a'], side=['#33291f'], noise_scale=3, height_w=0))
    m['gravel'] = A('gravel_path', SS(top=['#6e6a66', '#7a7570', '#635f5b'], side=['#55514d'], noise_scale=3,
                                      noise_w=0.9, height_w=0))
    m['barn'] = A('barn_planks', PatternShader(['#5e2620', '#6a2b24', '#55221d'], lambda x, y, z: _h(x + y, z // 3, 3)))
    m['barn_trim'] = A('barn_trim', SS(top=['#b9ad95'], side=['#a99e88'], noise_scale=3, height_w=0))
    m['hay'] = A('hay', SS(top=['#b8963f', '#c9a64a'], side=['#a3852f', '#b8963f'], noise_scale=3, height_w=0))
    m['brew'] = A('witch_brew', SS(top=['#7cd23a'], side=['#6abf2e'], noise_scale=2, height_w=0, occ_dark=0))
    # witches
    m['robe'] = A('witch_robe', SS(top=['#2a1f33'], side=['#241a2c', '#30243a'], noise_scale=2, height_w=0, occ_dark=0.1))
    m['skin'] = A('witch_skin', SS(top=['#7ab04a'], side=['#6c9e40', '#7ab04a'], noise_scale=2, height_w=0, occ_dark=0))
    m['hair'] = A('witch_hair', SS(top=['#4a2a5a'], side=['#40244e'], noise_scale=2, height_w=0))
    m['band'] = A('hat_band', SS(top=['#8a3aa0'], side=['#7a3290'], noise_scale=2, height_w=0))
    m['broom'] = A('broomstick', SS(top=['#6b4a2b'], side=['#5c3f25'], noise_scale=2, height_w=0))
    m['bristle'] = A('bristles', SS(top=['#c9a24a'], side=['#b38f3f', '#c9a24a'], noise_scale=2, height_w=0))
    m['cat'] = A('cat_black', SS(top=['#141217'], side=['#141217', '#1c1a20'], noise_scale=2, height_w=0, occ_dark=0))
    m['cat_eye'] = A('cat_eye', SS(top=['#e8e04a'], side=['#e8e04a'], noise_scale=2, height_w=0, occ_dark=0))
    return m


def place_house(s, m, p, floor_z=G):
    """Detailed house on a plot dict (x, y, front, storeys, seed) + doorstep jack-o'-lantern."""
    (x0, x1), (y0, y1) = p['x'], p['y']
    w, d = x1 - x0 + 1, y1 - y0 + 1
    r = np.random.default_rng(p['seed'])
    ridge = 'y' if (w <= 10 and r.random() < 0.45) else 'x'
    pf = P.house(p['seed'], w, d, p['storeys'], m, m['plasters'][int(r.integers(0, len(m['plasters'])))],
                 m['roofs'][int(r.integers(0, len(m['roofs'])))], ridge=ridge,
                 jetty=(p['storeys'] >= 2 and ridge == 'x' and r.random() < 0.5))
    a = pf.a; ox, oy = pf.origin
    if p['front'] == 's':                                     # door must face the lane (south)
        a = a[:, ::-1, :]; oy = a.shape[1] - 1 - oy
        art.stamp(s, P.Prefab(a, origin=(ox, oy)), x0, y1, floor_z, replace_air_only=True)
    else:
        art.stamp(s, P.Prefab(a, origin=(ox, oy)), x0, y0, floor_z, replace_air_only=True)
    # doorstep jack-o'-lantern beside the door
    if r.random() < 0.7:
        dc = (x0 + x1) // 2 + (3 if r.random() < 0.5 else -2)
        sz = int(r.integers(1, 3))
        pk = P.pumpkin(p['seed'] + 1, m, size=sz, lantern=True, face='-j')
        if p['front'] == 's':
            pk = P.Prefab(pk.a[:, ::-1, :], origin=(pk.origin[0], pk.a.shape[1] - 1 - pk.origin[1]))
            art.stamp(s, pk, dc, y1 + sz, floor_z, replace_air_only=True)
        else:
            art.stamp(s, pk, dc, y0 - sz, floor_z, replace_air_only=True)



def church_full(s, m):
    """Church massing (scenes.hollowfen.church, SPEC coordinates) + all art detail."""
    church(s, m['church'], m['stair'], m['belfry'], m['slate'])
    c = SPEC['church']
    (nx0, nx1), (ny0, ny1) = c['nave_x'], c['nave_y']
    (tx0, tx1), (ty0, ty1) = c['tower_x'], c['tower_y']
    top = c['nave_wall_top_z']; bz = c['belfry_floor_z']
    yc = (ny0 + ny1) // 2
    # buttresses on the long walls (stepped), lancet windows between them
    for bxp in range(nx0 + 3, nx1 - 1, 6):
        if nx0 + 5 <= bxp <= nx0 + 8:
            continue                                                  # side doors
        for (yy, sg) in ((ny0 - 1, -1), (ny1 + 1, 1)):
            s.mat[bxp, yy, top + 2:G] = np.where(s.mat[bxp, yy, top + 2:G] == 0, m['church'], s.mat[bxp, yy, top + 2:G])
            s.mat[bxp, yy + sg, G - 5:G] = np.where(s.mat[bxp, yy + sg, G - 5:G] == 0, m['church'], s.mat[bxp, yy + sg, G - 5:G])
    gi = 0
    for wx in range(nx0 + 4, nx1 - 2, 6):
        for yy in (ny0, ny1):
            if s.mat[wx, yy, G - 6] == 0:
                continue
            for k, z in enumerate(range(G - 10, G - 3)):
                s.mat[wx:wx + 2, yy, z] = m['glass'][(gi + k // 2) % 4]
            s.mat[wx:wx + 2, yy, G - 11] = m['church_trim']; s.mat[wx, yy, G - 12] = m['church_trim']
            gi += 1
    # west facade: pointed door arch + rose window in the gable
    for dzz, half in ((G - 6, 1), (G - 7, 0)):
        s.mat[nx0, yc - half - 1:yc + half + 2, dzz] = m['church_trim']
    rz = top - 5
    for dy in range(-3, 4):
        for dzr in range(-3, 4):
            rr = np.hypot(dy, dzr)
            if rr <= 3.2 and s.mat[nx0, yc + dy, rz + dzr] > 0:
                s.mat[nx0, yc + dy, rz + dzr] = m['church_trim'] if rr > 2.3 else m['glass'][(abs(dy) + abs(dzr)) % 4]
    # tower: glass slits (solid, so the stair keeps its wall support), clock faces east + west, bell, gargoyles, cross
    for zs in (G - 14, G - 20):
        for (xx, yy) in (((tx0 + tx1) // 2, ty0), ((tx0 + tx1) // 2, ty1)):
            s.mat[xx, yy, zs - 2:zs + 1] = m['glass'][1]
    for xx in (tx0, tx1):
        cy, czc = (ty0 + ty1) // 2, bz + 5
        for dy in range(-3, 4):
            for dzc in range(-3, 4):
                rr = np.hypot(dy, dzc)
                if rr <= 3.3:
                    s.mat[xx, cy + dy, czc + dzc] = m['iron'] if rr > 2.6 else m['clock']
        s.mat[xx, cy, czc - 2:czc + 1] = m['iron']; s.mat[xx, cy:cy + 3, czc] = m['iron']   # hands (ten past...)
    bcx, bcy = (tx0 + tx1) // 2, (ty0 + ty1) // 2
    s.mat[bcx, bcy, bz - 8 + 1] = m['iron']                                          # yoke
    for k, rad in enumerate((1, 2, 2)):                                             # bell: bottom z 28, deck z 32
        z = bz - 8 + 2 + k
        s.mat[bcx - rad:bcx + rad + 1, bcy - rad:bcy + rad + 1, z] = m['bronze']
    for (xx, yy) in ((tx0 - 1, ty0 - 1), (tx1 + 1, ty0 - 1), (tx0 - 1, ty1 + 1), (tx1 + 1, ty1 + 1)):
        ax = xx + (1 if xx < tx0 else -1); ay = yy + (1 if yy < ty0 else -1)
        s.mat[ax, yy, bz - 8] = m['church_trim']; s.mat[xx, yy, bz - 8] = m['iron']; s.mat[xx, yy, bz - 9] = m['iron']
    tipz = int(np.argmax(s.mat[bcx, bcy] > 0))                                       # top of the finial
    s.mat[bcx, bcy, tipz - 2:tipz] = m['iron']
    s.mat[bcx, bcy - 1:bcy + 2, tipz - 1] = m['iron']                                # iron cross
    # nave roof ridge cap
    k_ridge = None
    for z in range(0, top):
        if s.mat[nx0 + 2, yc, z] == m['slate']:
            k_ridge = z; break
    if k_ridge is not None:
        row = s.mat[nx0 - 1:nx1 + 1, yc, k_ridge]
        s.mat[nx0 - 1:nx1 + 1, yc, k_ridge] = np.where(row == m['slate'], m['slate_ridge'], row)


def plant_forest(s, m, rng, notree, bog_d, X, Y, x_max=255):
    """Forest on the west half: autumn broadleaf, pines (edges / high ground), dead trees (bogs), bushes."""
    topz = np.argmax(s.mat > 0, axis=2)
    dens = art.fbm(X, Y, None, scale=60, octaves=3, seed=SEED + 200)
    leaf_pick = [0, 1, 3, 0, 1, 3, 2, 0]                                   # orange, red, rust heavy; gold rare
    lib_broad = [art.tree(SEED + 300 + i, m['trunk'], m['leaves'][leaf_pick[i % 8]], height=int(5 + i % 4),
                          crown_r=3.0 + (i % 3) * 0.6, crown_h=4 + i % 2, lean=((i % 5) - 2) * 0.3) for i in range(24)]
    lib_pine = [P.pine(SEED + 400 + i, m, height=10 + i % 6, r0=3.0 + (i % 3) * 0.5) for i in range(12)]
    lib_dead = [P.dead_tree(SEED + 500 + i, m['deadwood'], height=7 + i % 5, spread=3 + i % 2) for i in range(10)]
    lib_bush = [P.bush(SEED + 600 + i, m['bush'], r=1.4 + (i % 3) * 0.4) for i in range(6)]
    tree_used = np.zeros(X.shape, bool)
    nt = {'broad': 0, 'pine': 0, 'dead': 0, 'bush': 0}
    for gx in range(2, 256, 5):
        for gy in range(2, 510, 5):
            x = gx + int(rng.integers(0, 4)); y = gy + int(rng.integers(0, 4))
            if x > 254 or y > 509 or notree[x, y] or tree_used[x, y]:
                continue
            dv = dens[x, y]
            edge = min(x, y, 511 - y)
            p_place = 0.35 + 0.6 * dv + (0.3 if edge < 40 else 0)
            if rng.random() > p_place:
                continue
            fz = int(topz[x, y])
            if fz >= 62 or s.mat[x, y, fz] not in (m['forest'], m['grass']):
                continue
            near_bog = bog_d[x, y] < 1.5
            r_ = rng.random()
            if near_bog and r_ < 0.6:
                pf, kind = lib_dead[int(rng.integers(0, len(lib_dead)))], 'dead'
            elif edge < 50 or fz < 52:
                pf, kind = (lib_pine[int(rng.integers(0, len(lib_pine)))], 'pine') if r_ < 0.7 else \
                           (lib_broad[int(rng.integers(0, len(lib_broad)))], 'broad')
            elif r_ < 0.10:
                pf, kind = lib_bush[int(rng.integers(0, len(lib_bush)))], 'bush'
            elif r_ < 0.22:
                pf, kind = lib_dead[int(rng.integers(0, len(lib_dead)))], 'dead'
            elif r_ < 0.47:
                pf, kind = lib_pine[int(rng.integers(0, len(lib_pine)))], 'pine'
            else:
                pf, kind = lib_broad[int(rng.integers(0, len(lib_broad)))], 'broad'
            fp = pf.a.any(axis=2)
            ox, oy = pf.origin
            xs0, ys0 = x - ox, y - oy
            if xs0 < 0 or ys0 < 0 or xs0 + fp.shape[0] > 256 or ys0 + fp.shape[1] > 511:
                continue
            if (notree[xs0:xs0 + fp.shape[0], ys0:ys0 + fp.shape[1]] & fp).any():
                continue
            art.stamp(s, pf, x, y, fz, replace_air_only=True)
            rr = 2 if kind == 'bush' else 3
            tree_used[x - rr:x + rr + 1, y - rr:y + rr + 1] = True
            nt[kind] += 1
    return nt


def build():
    L = Layout()
    s = Scene('hollowfen', seed=SEED)
    m = materials(s)
    M = {'grass': m['grass'], 'forest': m['forest'], 'soil': m['soil'], 'rock': m['rock'], 'cobble': m['cobble'],
         'dirt': m['dirt'], 'square': m['square'], 'farm': m['farm'], 'cem': m['cem'], 'cemwall': m['cemwall'],
         'bank': m['bank'], 'boardwalk': m['boardwalk']}
    X, Y = L.X, L.Y
    west = X <= 255
    rng = np.random.default_rng(SEED + 100)
    H = ground(s, L, M)
    water = bogs(s, L, M)
    cemetery_wall(s, L, M)
    cm = SPEC['cemetery']; cz = cm['z']
    counts = {}

    # ------------------------------------------------------------------ houses on the shared plots
    for p in L.plots:
        place_house(s, m, p)
    counts['houses'] = len(L.plots)

    # ------------------------------------------------------------------ church (shared massing + detail)
    church_full(s, m)

    # ------------------------------------------------------------------ mausoleum (centre, mirrored halves)
    mx, my = cm['mausoleum_x'], cm['mausoleum_y']
    s.box(mx[0], 255, my[0], my[1], cz - 7, cz - 1, m['marble'])
    s.carve(mx[0] + 1, 255, my[0] + 1, my[1] - 1, cz - 6, cz - 1)
    s.box(mx[0] - 1, 255, my[0] - 1, my[1] + 1, cz - 8, cz - 8, m['marble_dark'])   # cornice
    for k in range(4):                                                              # stepped pyramid roof
        s.box(mx[0] + k, 255, my[0] + k, my[1] - k, cz - 9 - k, cz - 9 - k, m['marble_dark'] if k % 2 else m['marble'])
    s.box(254, 255, 255, 257, cz - 17, cz - 13, m['marble_dark'])                   # obelisk finial (mirrored -> 2x... )
    s.mat[255, 256, cz - 19:cz - 17] = m['marble_dark']
    s.box(mx[0] - 3, mx[0] - 1, 251, 261, cz - 1, cz - 1, m['marble'])               # portico floor (1 step)
    for py in (251, 254, 258, 261):                                                 # columns
        s.mat[mx[0] - 3, py, cz - 7:cz - 1] = m['marble']
    s.box(mx[0] - 3, mx[0] - 1, 250, 262, cz - 8, cz - 8, m['marble_dark'])          # portico roof
    for k in range(3):                                                              # pediment
        s.box(mx[0] - 3, mx[0] - 3, 251 + 2 * k, 261 - 2 * k, cz - 9 - k, cz - 9 - k, m['marble'])
    s.carve(mx[0], mx[0], 254, 258, cz - 5, cz - 1)                                  # doorway
    s.mat[mx[0], 254:259, cz - 6] = m['iron']                                        # iron lintel
    for (ux, uy) in ((mx[0] - 1, my[0] - 1), (mx[0] - 1, my[1] + 1)):                # urns
        s.mat[ux, uy, cz - 9] = m['marble_dark']; s.mat[ux, uy, cz - 10] = m['glow']

    # ------------------------------------------------------------------ cemetery paths, graves, lanterns, dead trees
    paths = west & L.cem & ((np.abs(Y - 256) <= 2) | (X >= 252) | (np.abs(Y - 233) <= 1) | (np.abs(Y - 279) <= 1))
    paths &= ~((X >= mx[0] - 3) & (Y >= my[0] - 1) & (Y <= my[1] + 1))
    s.mat[paths & (s.mat[:, :, cz] == m['cem']), cz] = m['gravel']
    used = np.zeros(X.shape, bool)
    used |= ndimage.binary_dilation(paths, iterations=1)
    used |= (X >= mx[0] - 5) & (Y >= my[0] - 3) & (Y <= my[1] + 3) & west
    used |= ~ndimage.binary_erosion(L.cem | (X > 255), iterations=2)
    for (tx, ty) in ((218, 206), (236, 214), (220, 304), (238, 296), (228, 244), (226, 270)):   # dead trees
        pf = P.dead_tree(int(rng.integers(1 << 30)), m['deadwood'], height=int(rng.integers(8, 12)), spread=4)
        art.stamp(s, pf, tx, ty, cz, replace_air_only=True)
        used[tx - 4:tx + 5, ty - 4:ty + 5] = True
    kinds = ['slab', 'slab', 'slab', 'cross', 'cross', 'obelisk', 'tomb', 'celtic']
    n_g = 0
    for gx in range(cm['x'][0] + 4, 250, 7):
        for gy in range(cm['y'][0] + 4, cm['y'][1] - 3, 5):
            jx, jy = gx + int(rng.integers(-1, 2)), gy
            if used[jx - 1:jx + 6, jy - 2:jy + 3].any() or rng.random() < 0.12:
                continue
            kind = kinds[int(rng.integers(0, len(kinds)))]
            pf = P.headstone(int(rng.integers(1 << 30)), m, kind)
            art.stamp(s, pf, jx, jy, cz, replace_air_only=True)
            if kind != 'tomb':
                s.mat[jx + 1:jx + 5, jy - 1:jy + 2, cz - 1] = np.where(
                    s.mat[jx + 1:jx + 5, jy - 1:jy + 2, cz - 1] == 0, m['mound'], s.mat[jx + 1:jx + 5, jy - 1:jy + 2, cz - 1])
            n_g += 1
    counts['graves'] = n_g
    # churchyard graves (around the church, outside lanes)
    cy_mask = L.churchyard & ~ndimage.binary_dilation(L.roads | L.nave | L.tower, iterations=2)
    for gx in range(148, 206, 6):
        for gy in range(239, 274, 5):
            if cy_mask[gx - 1:gx + 5, gy - 2:gy + 3].all() and rng.random() < 0.75:
                pf = P.headstone(int(rng.integers(1 << 30)), m, ['slab', 'cross', 'slab', 'obelisk'][int(rng.integers(0, 4))])
                art.stamp(s, pf, gx, gy, G, replace_air_only=True)
                n_g += 1
    counts['graves_total'] = n_g
    # lanterns: cemetery paths and gates, village lanes
    lamp = P.lamp_post(m)
    lamp_pts = [(cm['x'][0] + 2, 229), (cm['x'][0] + 2, 283), (236, 251), (236, 261)]
    for x in range(76, 206, 16):
        lamp_pts += [(x, 229), (x, 283)]
    nl = 0
    for (lx, ly) in lamp_pts:
        tz = int(np.argmax(s.mat[lx, ly] > 0))
        if tz >= G - 1 and s.mat[lx, ly, tz - 6:tz].max() == 0:
            art.stamp(s, lamp, lx, ly, tz, replace_air_only=True); nl += 1
    counts['lamps'] = nl

    # ------------------------------------------------------------------ farm: barn, farmhouse, pumpkin field, scarecrows
    s.box(30, 50, 262, 273, G - 7, G - 1, m['barn'])
    s.carve(31, 49, 263, 272, G - 6, G - 1)
    for k in range(7):                                                              # gambrel-ish roof along x
        y_lo, y_hi = 261 + (k if k < 3 else 3 + (k - 3) * 2), 274 - (k if k < 3 else 3 + (k - 3) * 2)
        if y_lo > y_hi:
            break
        z = G - 8 - k
        s.box(29, 51, y_lo, y_lo + 1, z, z, m['roofs'][3]); s.box(29, 51, y_hi - 1, y_hi, z, z, m['roofs'][3])
        if y_lo + 2 <= y_hi - 2:
            s.box(30, 30, y_lo + 2, y_hi - 2, z, z, m['barn']); s.box(50, 50, y_lo + 2, y_hi - 2, z, z, m['barn'])
    s.carve(37, 43, 262, 262, G - 5, G - 1)                                         # big door (north)
    s.box(36, 44, 262, 262, G - 6, G - 6, m['barn_trim'])                           # white door frame
    s.mat[36, 262, G - 6:G] = m['barn_trim']; s.mat[44, 262, G - 6:G] = m['barn_trim']
    for zt in range(G - 7, G - 1, 2):                                               # trim bands on the gables
        s.mat[30, 263:273, zt] = np.where(s.mat[30, 263:273, zt] > 0, m['barn_trim'], 0)
    fh = P.house(SEED + 7, 15, 12, 2, m, m['plasters'][0], m['roofs'][0], ridge='x')
    art.stamp(s, P.Prefab(fh.a[:, ::-1, :], origin=(fh.origin[0], fh.a.shape[1] - 1 - fh.origin[1])), 32, 250, G,
              replace_air_only=True)
    n_p = 0
    fx, fy = SPEC['farm']['intel']
    for px in range(54, 86, 3):
        for py in list(range(240, 252, 3)) + list(range(261, 273, 3)):
            if abs(px - fx) <= 2 and abs(py - fy) <= 2:
                continue
            if rng.random() < 0.55:
                sz = int(rng.choice([1, 1, 2, 2, 3]))
                art.stamp(s, P.pumpkin(int(rng.integers(1 << 30)), m, size=sz, lantern=(sz >= 2 and rng.random() < 0.3)),
                          px, py, G, replace_air_only=True)
                n_p += 1
    for (sx_, sy_) in ((62, 244), (78, 268), (70, 250)):
        art.stamp(s, P.scarecrow(0, m), sx_, sy_, G, replace_air_only=True)
    for (hx, hy) in ((52, 265), (52, 270), (53, 268)):
        s.box(hx, hx + 1, hy, hy + 1, G - 2, G - 1, m['hay'])
    counts['field_pumpkins'] = n_p

    # ------------------------------------------------------------------ well on the green between square and church
    wx0, wy0 = 140, 240                                    # well: north corner of the green, off the door axis
    s.box(wx0, wx0 + 4, wy0, wy0 + 4, G - 2, G - 1, m['stone']); s.carve(wx0 + 1, wx0 + 3, wy0 + 1, wy0 + 3, G - 2, G - 1)
    for (wx_, wy_) in ((wx0, wy0), (wx0 + 4, wy0), (wx0, wy0 + 4), (wx0 + 4, wy0 + 4)):
        s.mat[wx_, wy_, G - 6:G - 2] = m['timber']
    s.box(wx0 - 1, wx0 + 5, wy0 - 1, wy0 + 5, G - 7, G - 7, m['roofs'][1])
    s.mat[wx0 + 1:wx0 + 4, wy0 + 2, G - 6] = m['timber']

    # ------------------------------------------------------------------ witch's hut in the north-west forest
    hx0, hy0 = 40, 120
    hz = int(np.median(H[hx0 - 6:hx0 + 7, hy0 - 6:hy0 + 7]))
    for x in range(hx0 - 8, hx0 + 9):                                                # level the clearing
        for y in range(hy0 - 8, hy0 + 9):
            if (x - hx0) ** 2 + (y - hy0) ** 2 <= 64:
                s.mat[x, y, :hz] = 0
                s.mat[x, y, hz:63] = np.where(s.mat[x, y, hz:63] == 0, m['soil'], s.mat[x, y, hz:63])
                s.mat[x, y, hz] = m['forest']
    hut = P.house(SEED + 13, 9, 7, 1, m, m['plasters'][4], m['roofs'][2], ridge='y', lit=1.0)
    art.stamp(s, hut, hx0 - 4, hy0 + 3, hz, replace_air_only=True)
    art.stamp(s, P.cauldron(m), hx0, hy0 + 7, hz, replace_air_only=True)
    s.markers['witch_hut'] = (hx0, hy0, hz)

    # ------------------------------------------------------------------ forest
    topz = np.argmax(s.mat > 0, axis=2)
    notree = (ndimage.binary_dilation(L.roads, iterations=2) | ndimage.binary_dilation(L.plot_mask, iterations=3)
              | L.village | L.cem | L.farm | ndimage.binary_dilation(L.bog & (L.bog_d < 0.9), iterations=1)
              | ((X - 40) ** 2 + (Y - 120) ** 2 <= 100) | (X > 255) | (X < 1))
    counts['trees'] = plant_forest(s, m, rng, notree, L.bog_d, X, Y)
    # reeds and dead snags along the bog shores
    shore = west & (L.bog_d > 0.75) & (L.bog_d < 1.0)
    for x, y in np.argwhere(shore)[::3]:
        if rng.random() < 0.35:
            tz = int(np.argmax(s.mat[x, y] > 0))
            if tz < 63 and s.mat[x, y, tz] == m['bank'] and s.mat[x, y, tz - 3:tz].max() == 0 and not L.roads[x, y]:
                h = int(rng.integers(2, 4))
                s.mat[x, y, tz - h:tz] = m['reed']
    # forest pumpkins (stray jack-o'-lanterns along the roads)
    for (poly, w, surf) in SPEC['lanes'].values():
        if surf != 'dirt':
            continue
        for (x0, y0), (x1, y1) in zip(poly[:-1], poly[1:]):
            for t in np.linspace(0, 1, 4)[1:-1]:
                px, py = int(x0 + (x1 - x0) * t) + 4, int(y0 + (y1 - y0) * t)
                if px <= 254 and not L.flat[px, py] and not L.bog[px, py] and rng.random() < 0.6:
                    tz = int(np.argmax(s.mat[px, py] > 0))
                    if tz >= 62 or s.mat[px, py, tz - 4:tz].max() > 0:
                        continue
                    art.stamp(s, P.pumpkin(int(rng.integers(1 << 30)), m, 2, lantern=True, face='+j'), px, py, tz,
                              replace_air_only=True)

    mirror(s)

    # ------------------------------------------------------------------ witches (requested floating scenery)
    for n, (wx, wy, wz) in enumerate(SPEC['witches']):
        pf = P.witch(SEED + 900 + n, m)
        a = np.rot90(pf.a, n % 4, axes=(0, 1))
        art.stamp(s, P.Prefab(a, origin=(a.shape[0] // 2, a.shape[1] // 2)), wx, wy, wz, replace_air_only=True)
    counts['witches'] = len(SPEC['witches'])

    # ------------------------------------------------------------------ painted bottom: murky bog water + lily pads
    bot = np.zeros((512, 512, 3), float)
    bot[:] = (34, 46, 38)
    nb = art.fbm(X, Y, None, scale=10, octaves=2, seed=SEED + 70)[..., None]
    bot = bot * (0.8 + 0.4 * nb)
    lily = (art.value_noise(X, Y, None, scale=3.0, seed=SEED + 71) > 0.78)
    bot[lily] = (58, 92, 44)
    s.paint_bottom(np.clip(bot, 0, 255).astype(np.uint8))
    s.markers['counts'] = counts
    s.markers['H'] = H
    return s, L


if __name__ == '__main__':
    from aosmap.vxl import write_vxl
    out = sys.argv[1] if len(sys.argv) > 1 else 'out/hollowfen'
    os.makedirs(out, exist_ok=True)
    s, L = build()
    data = write_vxl(s.to_voxelmap())
    open(os.path.join(out, 'hollowfen.vxl'), 'wb').write(data)
    open(os.path.join(out, 'hollowfen.txt'), 'w').write(metadata_txt(author='aosmap (art v1)'))
    spec = dict(SPEC); spec['plots'] = L.plots
    json.dump(spec, open(os.path.join(out, 'spec.json'), 'w'), indent=1, default=list)
    print('written', len(data), 'bytes', s.markers['counts'])
