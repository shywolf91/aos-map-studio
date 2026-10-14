"""DROWNED CATHEDRAL - Halloween Babel map for stock piqueserver 1.4.2 (babel + babel_script).

A gothic cathedral has sunk into a fen. The town's old quays still stand on both sides: each team spawns in a
walled chapel precinct on its quay (z 40) and builds its tower from an open processional esplanade at the quay
edge. The fen lies 22 voxels below, with the drowned nave, transepts and apse; the cathedral's crossing tower
(the surviving bell tower) rises from the water under the centre of the script platform.

Babel geometry (piqueserver 1.4.2 scripts/babel_script.py, read 2026-10-14):
  platform x 206-305, y 240-271, z 1 (script-generated); bases (118, 256) / (394, 256), spawns +-20 on the topmost
  voxel; intel on the platform. Nobody may destroy blocks in x 224-288 (blue needs x > 288, red x < 224), so
  anything built inside the cathedral centre is permanent -> the bell tower has two mirrored stair cores.

Layout (west half authored, mirrored x' = 512 - x):
  spawn precinct  x 84-148, y 190-322, z 40; spawn square x 98-138, y 236-276 kept clear (paving only)
  cover screen    arcade + gatehouse x 140-144, y 226-286 between the spawn square and the platform
  tower zone      esplanade x 148-205, y 228-284, z 40: open paving, no props (towers start here)
  mole            stone pier x 151-205, y 212-300 (top z 40) carrying the esplanade; vertical masonry quays drop 22
                  to the fen on three sides; stairs cut into its north/south faces (x 160-179) down to causeways
  fen             elliptical basin (semi-axes 150 x 196 round the centre) of water (z 62 air), mud hummocks, cypress
                  groves, lilies and a drowned town of half-sunk houses; natural slopes up to the forested banks
  cathedral       cruciform, nave along y, centred on x = 256: facade towers y 136-151, nave y 152-243,
                  transepts x 214-297 / y 236-275, crossing tower x 244-268 / y 244-267 (top z 23, belfry z 30),
                  choir y 268-329, apse r 24 round (256, 330)

Run: python scenes/drowned_cathedral.py out/drowned_cathedral
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aosmap.scene import Scene, Material                                     # noqa: E402
from aosmap import art                                                       # noqa: E402
from aosmap.art import SurfaceShader, PatternShader, StrataShader, fbm, value_noise, ramp, hex_rgb  # noqa: E402
from scenes import drowned_cathedral_props as P                              # noqa: E402

SEED = 1414
FOG = (152, 174, 168)          # bright slate-green tint: user rule, fog channels >= 150 to look right in testing
BANK = 40                     # quay / precinct standing z
FLOOR = 59                    # cathedral floors and causeways
CX = 256                      # mirror centre (x' = 512 - x)

SPEC = {
    'mode': 'babel (stock piqueserver 1.4.2: game_modes.babel + scripts.babel_script)',
    'script_constants': {'platform_x': (206, 305), 'platform_y': (240, 271), 'platform_z': 1,
                         'intel': (256, 256), 'bases': ((118, 256), (394, 256)), 'spawn_half': 20,
                         'no_destroy_band_x': (224, 288)},
    'bank_z': BANK, 'floor_z': FLOOR,
    'spawn_square': {'x': (98, 138), 'y': (236, 276)},
    'precinct': {'x': (84, 148), 'y': (190, 322)},
    'tower_zone': {'x': (148, 205), 'y': (228, 284)},
    'esplanade': {'x': (146, 205), 'y': (212, 300)},
    'screen': {'x': (141, 143), 'y': (226, 286), 'top': 31, 'gatehouse': {'x': (140, 144), 'y': (248, 264), 'top': 24}},
    'basin': {'centre': (256, 256), 'semi_axes': (150, 196), 'slope_w': 30},
    'mole': {'x': (151, 205), 'y': (212, 300)},                  # high stone pier carrying the esplanade
    'precinct_block': {'x': (0, 150), 'y': (190, 322)},
    'stairs': {'north': {'x_top': 160, 'x_bottom': 179, 'y': (213, 216), 'balustrade_y': 212, 'landing_x': (180, 186)},
               'south': 'mirror in y (y -> 512 - y)'},
    'causeways': {
        'quay_foot': ([(208, 186), (208, 326)], 5),
        'north_door': ([(207, 188), (233, 188)], 5),
        'south_door': ([(207, 324), (233, 324)], 5),
        'transept': ([(208, 256), (215, 256)], 8),
        'north_stair': ([(183, 209), (196, 196), (207, 189)], 5),
        'south_stair': ([(183, 303), (196, 316), (207, 323)], 5),
        'north_axis': ([(253, 84), (253, 145)], 7),
        'south_axis': ([(253, 352), (253, 428)], 7),
        'west_n': ([(120, 150), (160, 168), (196, 186), (207, 188)], 4),
        'west_s': ([(120, 362), (160, 344), (196, 326), (207, 324)], 4),
    },
    'cathedral': {
        'aisle_wall_x': (234, 235), 'aisle_top': 47, 'arcade_x': (244, 245), 'arcade_top': 35,
        'nave_y': (152, 243), 'choir_y': (268, 329),
        'piers_north': [158, 170, 182, 194, 206, 218, 230], 'piers_south': [282, 294, 306, 318],
        'transept': {'x': (214, 233), 'y': (236, 275), 'top': 36, 'gable_mid': 28},
        'tower': {'x0': 244, 'y_walls': ((244, 246), (265, 267)), 'top': 23, 'belfry_floor': 32},
        'facade': {'towers_x': (230, 243), 'towers_y': (136, 151), 'wall_y': (146, 151), 'rose': (32, 7.0)},
        'apse': {'centre': (256, 330), 'r': (21.5, 24.0), 'top': 36},
        'doors_y': (188, 324),
    },
    'chapel': {'x': (104, 132), 'y': (202, 222)},
    'ossuary': {'x': (106, 130), 'y': (290, 306)},
    'graveyard': {'x': (52, 86), 'y': (232, 280)},
    'cottages': [(40, 150, 11, 8), (62, 100, 10, 8), (104, 62, 12, 9), (152, 40, 10, 7)],
    'gibbets': [(194, 214)],
    'drowned_houses_n': 9,
    # mode: 'ground' = painted into the ground's top voxels; 'raised' = letters one voxel above the ground (shadow
    # painted on the ground); 'sky' = painted on a 1-voxel plate at sky_z, tethered to the ground by a hidden stalk.
    # clear: flatten + clear the patch under the tag (False keeps the forest; use with 'sky')
    'signature': {'lines': ['Drowned Cathedral', 'Designed by shywolf91 and AI'], 'corner': 'bottom-right',
                  'margin': 6, 'z': BANK, 'mode': 'sky', 'clear': False, 'sky_z': 4},
    'fog': FOG,
}


def smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def _h(a, b, n):
    a = np.asarray(a).astype(np.int64); b = np.asarray(b).astype(np.int64)
    return ((a * 73856093) ^ (b * 19349663)) % n


# ============================================================================================== shaders
@dataclass
class StainedMasonry:
    """Coursed stone blocks (one colour per block, courses offset) with weathering: coherent value variation,
    moss on top faces, rain streaks on sides, and a green-brown flood stain that rises toward the water."""
    colours: list
    block: tuple = (3, 2)
    stain_z: tuple = (52, 62)
    stain: str = '#46503e'
    stain_mix: float = 0.6
    moss_top: str | None = '#717a55'
    moss_mix: float = 0.42
    side_dark: float = 0.76
    under_dark: float = 0.62
    occ_dark: float = 0.36
    streak: float = 0.12
    salt: int = 0

    def __call__(self, ctx):
        x, y, z = ctx['x'], ctx['y'], ctx['z']
        bw, bh = self.block
        course = z // bh
        u = (x + y + (course % 2) * (bw // 2)) // bw
        pal = np.stack([hex_rgb(c) for c in self.colours])
        c = pal[_h(u, course + 7 * self.salt, len(self.colours))]
        seed = ctx['seed'] + 13 * self.salt
        n = fbm(x, y, z, scale=11, octaves=2, seed=seed + 3)
        c = c * (0.9 + 0.2 * n)[:, None]
        top = ctx['top']
        if self.moss_top:
            mo = np.clip((fbm(x, y, None, scale=6, octaves=2, seed=seed + 5) - 0.32) / 0.36, 0, 1) * self.moss_mix
            c = np.where(top[:, None], c * (1 - mo[:, None]) + hex_rgb(self.moss_top) * mo[:, None], c)
        side = ~top
        st = value_noise(x, y, z / 9.0, scale=1.7, seed=seed + 9)
        c = np.where(side[:, None], c * self.side_dark * (1 - self.streak * np.clip((st - 0.5) * 3, 0, 1))[:, None], c)
        t = np.clip((z - self.stain_z[0]) / max(self.stain_z[1] - self.stain_z[0], 1), 0, 1) * self.stain_mix
        c = c * (1 - t[:, None]) + hex_rgb(self.stain) * t[:, None]
        c = np.where((ctx['under'] & ~top)[:, None], c * self.under_dark, c)
        occ = np.clip((ctx['occ'] - 0.5) / 0.5, 0, 1)
        return c * (1 - self.occ_dark * occ)[:, None]


def materials(s):
    A = lambda n, sh: s.material(Material(n, (128, 128, 128), shader=sh))     # noqa: E731
    F = lambda n, rgb: s.material(Material(n, rgb))                           # noqa: E731
    SS = SurfaceShader
    m = {}
    # --- ground
    m['grass'] = A('fen_grass', SS(top=['#39432e', '#424e33', '#4c5738', '#575e3e'], side=['#33291f', '#3b3125'],
                                   noise_scale=24, noise_w=0.85, height_w=0.15, occ_dark=0.3))
    m['soil'] = A('soil', SS(top=['#43382a'], side=['#3a3125', '#43382a', '#33291f'], noise_scale=5, height_w=0))
    m['rock'] = A('rock', StrataShader(['#4d4f4c', '#565854', '#454744', '#5e605b'], pattern=(2, 3, 1, 2),
                                       crust='#4f5639', crust_mix=0.55, salt=5))
    m['mud'] = A('mud', SS(top=['#3a3125', '#433829', '#30291f', '#3b3a26'], side=['#2e271d', '#382f23'],
                           noise_scale=5, noise_w=0.85, height_w=0, occ_dark=0.3))
    m['quay'] = A('quay_masonry', StainedMasonry(['#575c56', '#60655e', '#4f544e', '#686c65'], block=(4, 2),
                                                stain_z=(46, 62), stain='#3c4838', stain_mix=0.55, salt=1))
    m['coping'] = A('quay_coping', StainedMasonry(['#6c6f69', '#757871', '#64675f'], block=(2, 1), stain_z=(60, 62),
                                                 moss_mix=0.3, salt=2))
    m['causeway'] = A('causeway', PatternShader(['#5b5e59', '#646761', '#535651', '#6b6d67'],
                                                lambda x, y, z: _h((x + (y // 2) % 2) // 2, y // 2, 4), occ_dark=0.4))
    bx, by = SPEC['script_constants']['bases'][0]

    def ring(x, y, z):
        x = np.where(x > 255, 512 - x, x)
        r = np.maximum(np.abs(x - bx), np.abs(y - by))
        return np.where((r % 7 == 0) | (r <= 1), 3, _h(x // 2, y // 2, 3))
    m['paving'] = A('precinct_paving', PatternShader(['#67686b', '#717275', '#5e5f62', '#4c4b47'], ring, occ_dark=0.3))
    zx, zy = SPEC['tower_zone']['x'], SPEC['tower_zone']['y']

    def espl(x, y, z):
        xm = np.where(x > 255, 512 - x, x)
        base = _h((xm + (y // 2 % 2) * 2) // 4, y // 2, 4)
        inzone = (xm >= zx[0]) & (xm <= zx[1]) & (y >= zy[0]) & (y <= zy[1])
        band = inzone & ((xm <= zx[0] + 1) | (y <= zy[0] + 1) | (y >= zy[1] - 1))
        band |= inzone & ((y == zy[0] + 4) | (y == zy[1] - 4)) & (xm % 4 != 0)
        strip = inzone & (np.abs(y - 256) <= 2)
        diamond = inzone & ((np.abs(y - 256) + np.abs((xm - zx[0]) % 14 - 7)) == 6)
        moss = _h(xm // 3 + 11, y // 2 + 5, 11) == 0
        puddle = (fbm(xm, y, None, scale=5, octaves=2, seed=SEED + 77) > 0.74) & ~band & ~strip
        out = np.where(moss, 5, base)
        out = np.where(puddle, 7, out)
        out = np.where(strip, np.where((xm % 6) < 3, 6, 3), out)
        out = np.where(diamond, 4, out)
        return np.where(band, 4, out)
    m['esplanade'] = A('esplanade', PatternShader(['#626460', '#6b6d68', '#5a5c58', '#73746f', '#454845', '#4e5640',
                                                   '#807f78', '#3b4644'], espl, occ_dark=0.3))
    m['gravel'] = A('gravel', SS(top=['#5a5850', '#646157', '#4f4e47'], side=['#4a483f'], noise_scale=2.5, noise_w=0.9,
                                 height_w=0, occ_dark=0.3))
    # --- cathedral stone
    m['stone'] = A('cathedral_stone', StainedMasonry(['#7a7c80', '#84858a', '#707277', '#8b8c90'], block=(3, 2),
                                                    stain_z=(50, 62), stain='#4a5442', moss_top='#7a8360', salt=3))
    m['stone_dk'] = A('cathedral_stone_dark', StainedMasonry(['#66686d', '#6f7176', '#5e6065'], block=(3, 2),
                                                             stain_z=(48, 62), stain='#45503f', moss_top='#6f7856', salt=4))
    m['trim'] = A('tracery', StainedMasonry(['#9a9b9e', '#a3a4a7', '#919295'], block=(2, 1), stain_z=(54, 62),
                                           moss_mix=0.25, streak=0.06, salt=6))
    m['floor'] = A('nave_floor', PatternShader(['#6d6f73', '#45474c', '#6d6f73', '#4a4c51'],
                                               lambda x, y, z: ((x // 2 + y // 2) % 2) * 1 + 2 * _h(x // 6, y // 6, 2), occ_dark=0.35))
    m['rubble'] = A('rubble', SS(top=['#6c6e71', '#78797c', '#5d5f62', '#5f6648'], side=['#5d5f62', '#68696c'],
                                 noise_scale=2.5, noise_w=0.9, height_w=0, occ_dark=0.45))
    m['slate'] = A('slate', PatternShader(['#363b45', '#3f4450', '#31353e', '#454a57'],
                                          lambda x, y, z: _h(x // 2 + z, y + z, 4), side_dark=0.8, occ_dark=0.3))
    glass = [('violet', '#55366f', '#64417f'), ('amber', '#ad6526', '#c17932'), ('crimson', '#722531', '#86303d'),
             ('teal', '#28625f', '#33736f')]
    m['glass'] = []
    for nm, a_, b_ in glass:
        m['glass'].append(A('glass_' + nm, PatternShader([a_, b_, '#2b2a30'],
                                                         lambda x, y, z: np.where((z % 3 == 0) | ((x + y) % 4 == 0), 2, _h(x + y, z, 2)),
                                                         side_dark=0.92, occ_dark=0.0)))
    # --- wood / metal
    m['timber'] = A('timber', SS(top=['#4f3e2e', '#594632'], side=['#43352a', '#4f3e2e'], noise_scale=3, height_w=0))
    m['iron'] = A('iron', SS(top=['#2f2d32'], side=['#2a282d', '#36343a'], noise_scale=2, height_w=0, occ_dark=0.1))
    m['bronze'] = A('bell_bronze', SS(top=['#6f5b33', '#7c673a'], side=['#5a4a2a', '#6f5b33'], noise_scale=2, height_w=0,
                                      occ_dark=0.2))
    m['boat'] = F('boat_paint', (62, 78, 84))
    # --- vegetation
    m['bark'] = A('cypress_bark', SS(top=['#4f4033'], side=['#3a2f25', '#43362a', '#3e3227'], noise_scale=3, height_w=0))
    m['leaf'] = A('cypress_leaf', SS(top=['#3d4d30', '#465735', '#4f5f3a'], side=['#2c3824', '#33412a'], noise_scale=9,
                                     noise_w=0.8, height_w=0.2, occ_dark=0.4))
    m['moss'] = A('hanging_moss', SS(top=['#7a856c'], side=['#6a755f', '#77826a', '#838c73'], noise_scale=2, height_w=0,
                                     occ_dark=0.15))
    m['snag'] = A('dead_wood', SS(top=['#6b6355'], side=['#5a5248', '#645b4f'], noise_scale=3, height_w=0))
    m['ivy'] = A('ivy', SS(top=['#3e4d2f', '#475832'], side=['#34422a', '#3e4d2f', '#4a5a34'], noise_scale=2.5, noise_w=0.9,
                           height_w=0, occ_dark=0.3))
    m['house'] = A('house_stone', StainedMasonry(['#6a655b', '#736d62', '#615c53', '#7a7468'], block=(3, 2), stain_z=(52, 62),
                                                stain='#3f4a39', salt=8))
    m['house2'] = A('house_plaster', StainedMasonry(['#857f71', '#8c8677', '#7e786b'], block=(5, 3), stain_z=(50, 62),
                                                   stain='#465140', stain_mix=0.65, salt=9))
    m['shrub'] = A('shrub', SS(top=['#3d482f', '#465337'], side=['#333d29'], noise_scale=2, height_w=0, occ_dark=0.35))
    m['reed'] = A('reed', SS(top=['#6a693e'], side=['#5c5b36', '#6a693e', '#727045'], noise_scale=2, height_w=0, occ_dark=0.1))
    m['reed_head'] = F('reed_head', (74, 58, 40))
    m['lily'] = A('lily', SS(top=['#4a6832', '#55743a', '#4e6e36'], side=['#3f5a2b'], noise_scale=2, height_w=0, occ_dark=0))
    m['flower'] = F('lily_flower', (214, 198, 218))
    # --- halloween / accents
    m['glow'] = F('lantern_glow', (232, 163, 60))
    m['glow_dim'] = F('ember_eyes', (206, 86, 44))
    m['wax'] = F('candle_wax', (214, 206, 180))
    m['sig_text'] = F('signature_text', (224, 218, 198))
    m['sig_shadow'] = F('signature_shadow', (18, 20, 16))
    m['sig_plate'] = F('signature_plate', (52, 60, 50))
    m['sig_orange'] = F('signature_pumpkin', (214, 112, 30))
    m['sig_green'] = F('signature_stem', (86, 120, 44))
    m['sig_glow'] = F('signature_glow', (250, 214, 92))
    m['dial'] = F('clock_dial', (196, 188, 160))
    m['pumpkin'] = F('pumpkin', (196, 98, 28))
    m['pumpkin_dark'] = F('pumpkin_rib', (164, 79, 22))
    m['stem'] = F('pumpkin_stem', (61, 74, 34))
    m['bone'] = F('bone', (200, 192, 168))
    m['skull'] = F('skull', (222, 214, 192))
    m['gargoyle'] = A('gargoyle', SS(top=['#5c5f61'], side=['#4f5254', '#5a5d5f'], noise_scale=2, height_w=0, occ_dark=0.3))
    m['banner_blue'] = s.material(Material('banner_blue', (47, 79, 168), top=(57, 92, 186)))
    m['banner_red'] = s.material(Material('banner_red', (168, 47, 47), top=(186, 60, 57)))
    m['gold'] = F('banner_gold', (186, 148, 62))
    # hollowfen_props.headstone keys
    m['grave'] = [m['stone_dk'], m['stone']]
    m['marble'] = m['trim']; m['marble_dark'] = m['stone_dk']
    return m


# ============================================================================================== geometry helpers
def arch_open(u, z, u0, u1, spring, R_mult=1.6):
    """Pointed (two-centred) arch opening spanning cells u0..u1; vertical sides below `spring` (z-down),
    pointed head above it. u, z: int arrays. Returns bool array."""
    uc = (u0 + u1) / 2.0
    a = (u1 - u0 + 1) / 2.0
    R = R_mult * a
    inside_w = np.abs(u - uc) < a
    h = (spring - z).astype(float)
    c1 = (u - (uc + (R - a))) ** 2 + h ** 2 <= R ** 2 + 0.2
    c2 = (u - (uc - (R - a))) ** 2 + h ** 2 <= R ** 2 + 0.2
    return inside_w & np.where(h <= 0, True, c1 & c2)


def arch_height(u0, u1, R_mult=1.6):
    a = (u1 - u0 + 1) / 2.0
    R = R_mult * a
    return float(np.sqrt(R * R - (R - a) ** 2))


def carve_arch_x(s, x0, x1, u0, u1, z_bottom, spring, fill=0, R_mult=1.6):
    """Opening in a wall that runs along y (wall occupies x0..x1). u = y."""
    hp = arch_height(u0, u1, R_mult)
    zt = int(np.floor(spring - hp)) - 1
    U, Z = np.meshgrid(np.arange(u0, u1 + 1), np.arange(max(zt, 0), z_bottom + 1), indexing='ij')
    o = arch_open(U, Z, u0, u1, spring, R_mult)
    for x in range(x0, x1 + 1):
        if x > 255:
            continue
        s.mat[x, U[o], Z[o]] = fill


def carve_arch_y(s, y0, y1, u0, u1, z_bottom, spring, fill=0, R_mult=1.6):
    """Opening in a wall that runs along x (wall occupies y0..y1). u = x. Cells x > 255 are skipped (mirror)."""
    hp = arch_height(u0, u1, R_mult)
    zt = int(np.floor(spring - hp)) - 1
    U, Z = np.meshgrid(np.arange(u0, u1 + 1), np.arange(max(zt, 0), z_bottom + 1), indexing='ij')
    o = arch_open(U, Z, u0, u1, spring, R_mult) & (U <= 255)
    for y in range(y0, y1 + 1):
        s.mat[U[o], y, Z[o]] = fill


def ruin(s, mask2d, amp, seed, keep_below=None, scale=7.0, base=0.36, only_above=None):
    """Knock the tops off walls: per column, remove `damage` voxels from the current top, where damage follows
    smooth noise (whole bays collapse together) plus a 1-voxel jagged edge. keep_below: never carve z >= this."""
    xs, ys = np.nonzero(mask2d)
    if not len(xs):
        return
    n = fbm(xs, ys, None, scale=scale, octaves=3, seed=seed)
    jag = (value_noise(xs, ys, None, scale=1.3, seed=seed + 1) > 0.55).astype(int)
    dmg = (amp * np.clip((n - base) / 0.42, 0, 1)).astype(int) + jag
    col = s.mat[xs, ys, :] > 0
    top = np.where(col.any(axis=1), np.argmax(col, axis=1), 63)
    for x, y, t, d in zip(xs, ys, top, dmg):
        if only_above is not None and t > only_above:
            continue
        zc = t + d
        if keep_below is not None:
            zc = min(zc, keep_below)
        if zc > t:
            s.mat[x, y, t:zc] = 0


def poly_dist(points, X, Y, step=0.5):
    pts = []
    for (x0, y0), (x1, y1) in zip(points[:-1], points[1:]):
        n = max(2, int(np.hypot(x1 - x0, y1 - y0) / step))
        t = np.linspace(0, 1, n, endpoint=False)
        pts.append(np.stack([x0 + (x1 - x0) * t, y0 + (y1 - y0) * t], 1))
    pts.append(np.array([points[-1]], float))
    from scipy.spatial import cKDTree
    d, _ = cKDTree(np.concatenate(pts)).query(np.stack([X.ravel(), Y.ravel()], 1))
    return d.reshape(X.shape)


def top_z(s, x, y):
    col = s.mat[x, y] > 0
    return int(np.argmax(col)) if col.any() else 63


def plant(s, pf, x, y, fz, max_fill=8):
    """art.stamp, then extend every base (k = 0) voxel down to the ground so props on uneven terrain stay
    face-connected (roots / footings). fz = standing voxel under the prefab origin."""
    art.stamp(s, pf, x, y, fz, replace_air_only=True)
    ox, oy = pf.origin
    ii, jj = np.nonzero(pf.a[:, :, 0])
    for i, j in zip(ii, jj):
        X, Y = x - ox + i, y - oy + j
        if not (0 <= X < 512 and 0 <= Y < 512) or fz - 1 < 0:
            continue
        mid = pf.a[i, j, 0]
        if s.mat[X, Y, fz - 1] != mid:
            continue
        z = fz
        while z < 63 and z < fz + max_fill and s.mat[X, Y, z] == 0:
            s.mat[X, Y, z] = mid
            z += 1


# ============================================================================================== layout + terrain
class Layout:
    def __init__(self):
        X, Y = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
        self.X, self.Y = X, Y
        self.west = X <= 255
        self.dy = np.abs(Y - 256).astype(float)
        bs = SPEC['basin']
        (ex, ey), (ax_, ay_) = bs['centre'], bs['semi_axes']
        ell = ((X - ex) / ax_) ** 2 + ((Y - ey) / ay_) ** 2
        ell = ell + (fbm(X, Y, None, scale=26, octaves=3, seed=SEED + 2) - 0.5) * 0.16
        self.inside0 = ell < 1.0
        box = lambda b: (X >= b['x'][0]) & (X <= b['x'][1]) & (Y >= b['y'][0]) & (Y <= b['y'][1])  # noqa: E731
        self.box = box
        self.mole = box(SPEC['mole'])
        self.pblock = box(SPEC['precinct_block'])
        self.land = self.mole | self.pblock
        self.inside = self.inside0 & ~self.land & self.west | (self.inside0 & ~self.west)
        self.d_ell = ndimage.distance_transform_edt(self.inside0)
        self.slope_w = float(bs['slope_w'])
        # vertical masonry faces: land-structure columns next to the basin
        self.quay_edge = self.land & self.west & ndimage.binary_dilation(self.inside & self.west, iterations=2)
        self.quay_face = self.inside & self.west & ndimage.binary_dilation(self.land, iterations=1)   # fen side
        self.square = box(SPEC['spawn_square'])
        self.precinct = box(SPEC['precinct'])
        self.zone = box(SPEC['tower_zone'])
        self.esplanade = self.mole | box(SPEC['esplanade'])
        zx = SPEC['tower_zone']['x']; zy = SPEC['tower_zone']['y']
        self.zone_both = self.zone | ((512 - X >= zx[0]) & (512 - X <= zx[1]) & (Y >= zy[0]) & (Y <= zy[1]))
        self.causeway = np.zeros(X.shape, bool)
        for nm, (pts, w) in SPEC['causeways'].items():
            self.causeway |= poly_dist(pts, X, Y) <= w / 2.0
        self.causeway &= self.west & ~self.land
        cat = box({'x': (222, 255), 'y': (130, 330)}) | box({'x': (208, 255), 'y': (230, 281)})
        cat |= (np.hypot(X - 256, Y - 330) <= 30) & (Y >= 326)
        self.cathedral = cat & self.west
        self.cottage = np.zeros(X.shape, bool)
        for (cx, cy, w, d) in SPEC['cottages']:
            for yy in (cy, 512 - cy):
                self.cottage |= box({'x': (cx - w // 2 - 3, cx + w // 2 + 3), 'y': (yy - d // 2 - 3, yy + d // 2 + 3)})
        self.graveyard = box(SPEC['graveyard'])
        st = SPEC['stairs']['north']
        self.stairs = box({'x': (st['x_top'], st['landing_x'][1]), 'y': (st['balustrade_y'], st['y'][1])})
        self.stairs |= box({'x': (st['x_top'], st['landing_x'][1]), 'y': (512 - st['y'][1], 512 - st['balustrade_y'])})
        self.houses = []                                   # filled by build() (drowned town)


def terrain(L: Layout):
    """Standing height H[x, y] (z-down). 63 = open water (no voxel above the water plane)."""
    X, Y = L.X, L.Y
    hb = BANK + np.rint((fbm(X, Y, None, scale=58, octaves=3, seed=SEED + 1) - 0.5) * 7)
    flat = L.land | L.precinct | ndimage.binary_dilation(L.graveyard, iterations=2)
    fd = ndimage.distance_transform_edt(~flat)
    hb = BANK + (hb - BANK) * smooth(fd / 12.0)
    H = np.rint(hb).astype(float)
    sw = L.slope_w
    tt = L.d_ell / sw
    rough = (fbm(X, Y, None, scale=7, octaves=2, seed=SEED + 4) - 0.5) * 2.2 * (1 - np.abs(2 * np.clip(tt, 0, 1) - 1))
    hs = hb + (61 - hb) * smooth(tt) + rough
    slope = L.inside & (tt < 1)
    H = np.where(slope, np.clip(np.rint(hs), BANK - 3, 61), H)
    fen = L.inside & ~slope
    H = np.where(fen, 63, H)
    n = fbm(X, Y, None, scale=13, octaves=3, seed=SEED + 6)
    keep_open = (ndimage.binary_dilation(L.cathedral, iterations=3) | ndimage.binary_dilation(L.causeway, iterations=3)
                 | (np.abs(X - 208) <= 6) & (L.dy <= 74))
    H = np.where(fen & (tt < 1.12), 61, H)                                        # mud shore at the slope foot
    foot = fen & ndimage.binary_dilation(L.land, iterations=2) & (value_noise(X, Y, None, scale=4, seed=SEED + 9) > 0.55)
    H = np.where(foot & ~keep_open, 61, H)                                         # silt banks at the quay feet
    H = np.where(fen & ~keep_open & (n > 0.58), 61, H)
    H = np.where(fen & ~keep_open & (n > 0.66), 60, H)
    return np.clip(H, 1, 63).astype(int)


def ground(s, L, m, H):
    """Fill the west half from H down to z 62 with zone materials; quay faces get masonry."""
    X, Y = L.X, L.Y
    west = L.west
    top = np.full(H.shape, m['grass'], np.int32)
    top = np.where(L.inside & (H >= 58), m['mud'], top)
    top = np.where(L.precinct & ~L.mole, m['grass'], top)
    top = np.where(L.esplanade & L.mole, m['esplanade'], top)
    top = np.where(L.square, m['paving'], top)
    top = np.where(L.quay_edge, m['coping'], top)
    # steep natural slope -> rock
    gx = np.maximum(np.abs(np.diff(H, axis=0, append=H[-1:])), np.abs(np.diff(H, axis=0, prepend=H[:1])))
    gy = np.maximum(np.abs(np.diff(H, axis=1, append=H[:, -1:])), np.abs(np.diff(H, axis=1, prepend=H[:, :1])))
    steep = (np.maximum(gx, gy) >= 3) & (H < 63)
    top = np.where(steep & ~L.quay_edge & ~L.esplanade, m['rock'], top)
    face = np.where(L.quay_edge, m['quay'], np.where(steep, m['rock'], m['soil']))
    for z in range(0, 63):
        sel = west & (z >= H) & (H < 63)
        if not sel.any():
            continue
        mz = np.where(z == H, top, np.where(z < H + 3, face, np.where(L.quay_edge, m['quay'], m['rock'])))
        s.mat[:, :, z][sel] = mz[sel]


def quay_stairs(s, m, L):
    """Straight stairs cut into the mole's north and south faces (1-voxel risers, 4 wide), a balustrade on the
    fen side, landing at the causeway level."""
    st = SPEC['stairs']['north']
    (ly0, ly1) = st['y']
    by = st['balustrade_y']
    for flip in (False, True):
        Y = (lambda y: 512 - y) if flip else (lambda y: y)
        for k in range(0, st['x_bottom'] - st['x_top'] + 1):
            x = st['x_top'] + k
            hz = BANK + k
            for y in range(by, ly1 + 1):
                yy = Y(y)
                s.mat[x, yy, :63] = 0
                s.mat[x, yy, hz:63] = m['quay']
                s.mat[x, yy, hz] = m['coping']
            s.mat[x, Y(by), hz - 1] = m['coping']                       # balustrade
            if k % 5 == 0:
                s.mat[x, Y(by), hz - 2] = m['coping']
        lx0, lx1 = st['landing_x']
        for x in range(lx0, lx1 + 1):
            for y in range(by, ly1 + 1):
                yy = Y(y)
                s.mat[x, yy, :63] = 0
                s.mat[x, yy, FLOOR:63] = m['quay']
                s.mat[x, yy, FLOOR] = m['causeway']
        for x in range(st['x_top'], lx1 + 2):                           # masonry face on the mole side of the cut
            col = s.mat[x, Y(ly1 + 1)]
            col[BANK + 1:63] = np.where(col[BANK + 1:63] > 0, m['quay'], 0)
        for y in range(by, ly1 + 1):
            col = s.mat[lx1 + 1, Y(y)]
            col[BANK + 1:63] = np.where(col[BANK + 1:63] > 0, m['quay'], 0)


def quay_details(s, m, L, H, rng):
    """Pilasters, a moulded cornice, drain spouts and ivy curtains on the fen side of every quay face, plus a
    parapet with lanterns along the mole edges outside the tower zone."""
    X, Y = L.X, L.Y
    face = L.quay_face & ~L.causeway & ~L.stairs & ~ndimage.binary_dilation(L.stairs, iterations=1)
    u = np.where(np.abs(np.diff(L.land.astype(int), axis=1, prepend=0)) + np.abs(np.diff(L.land.astype(int), axis=1, append=0)) > 0, X, Y)
    ivy = fbm(X, Y, None, scale=5, octaves=2, seed=SEED + 33)
    for x, y in np.argwhere(face):
        g = int(H[x, y]) if H[x, y] < 63 else 63
        if (u[x, y] % 14) in (0, 1):                                    # pilaster
            s.mat[x, y, BANK + 1:g] = np.where(s.mat[x, y, BANK + 1:g] == 0, m['quay'], s.mat[x, y, BANK + 1:g])
            s.mat[x, y, BANK + 1] = m['coping']
        else:
            s.mat[x, y, BANK + 2] = m['coping']                          # cornice band
            if (u[x, y] % 14) == 7 and rng.random() < 0.5:
                s.mat[x, y, 50] = m['iron']                              # mooring ring / drain spout
            if ivy[x, y] > 0.56:
                L_ = int(4 + (ivy[x, y] - 0.56) * 60)
                for z in range(BANK + 3, min(BANK + 3 + L_, g)):
                    if s.mat[x, y, z] == 0:
                        s.mat[x, y, z] = m['ivy']
    # parapet + lanterns on the mole edges (outside the tower zone y-range)
    mo = SPEC['mole']; zy = SPEC['tower_zone']['y']
    for y in (mo['y'][0], mo['y'][1]):
        for x in range(mo['x'][0], mo['x'][1] + 1):
            if L.stairs[x, y] or s.mat[x, y, BANK] == 0:
                continue
            s.mat[x, y, BANK - 1] = m['coping']
            if x % 8 == 0:
                s.mat[x, y, BANK - 2] = m['coping']
    lp = P.lantern_post(m, h=4)
    for x in range(156, 206, 16):
        for y in (mo['y'][0] + 2, mo['y'][1] - 2):
            if not L.stairs[x, y] and not L.zone[x, y]:
                plant(s, lp, x, y, BANK)


def drowned_house(s, m, x0, y0, w, d, seed, H):
    """Two-storey town house standing in the fen: flooded ground floor (door at the water line), timber upper
    floor partly fallen, gable ends, half a slate roof, a chimney, a few windows lit by something inside."""
    rng = np.random.default_rng(seed)
    x1, y1 = x0 + w - 1, y0 + d - 1
    wh = int(rng.integers(12, 16))
    zt = 62 - wh
    mat = m['house'] if rng.random() < 0.6 else m['house2']
    s.box(x0, x1, y0, y1, 62, zt, mat)
    s.carve(x0 + 1, x1 - 1, y0 + 1, y1 - 1, 61, zt)
    s.mat[x0 + 1:x1, y0 + 1:y1, 62] = 0                                   # flooded inside
    s.box(x0, x1, y0, y1, 55, 55, m['timber'])                            # storey band / beams
    s.box(x0 + 1, x1 - 1, y0 + 1, y1 - 1, 55, 55, m['timber'])            # upper floor (holes below)
    for (xx, yy) in np.argwhere(rng.random((w - 2, d - 2)) < 0.35):
        s.mat[x0 + 1 + xx, y0 + 1 + yy, 55] = 0
    ridge_x = rng.random() < 0.5
    if ridge_x:                                                           # gable ends on x0 / x1
        ym = (y0 + y1) / 2.0
        for x in (x0, x1):
            for y in range(y0, y1 + 1):
                g = zt - int(np.floor(d / 2.0 - abs(y - ym)))
                s.mat[x, y, g:zt] = mat
        for k in range(d // 2 + 1):
            z = zt - k
            for yy in (y0 - 1 + k, y1 + 1 - k):
                if rng.random() < 0.75:
                    s.mat[x0 - 1:x0 + w // 2 + 2, yy, z] = m['slate']
                    s.mat[x0 - 1:x0 + w // 2 + 2, yy, z + 1] = np.where(s.mat[x0 - 1:x0 + w // 2 + 2, yy, z + 1] == 0, m['slate'],
                                                                       s.mat[x0 - 1:x0 + w // 2 + 2, yy, z + 1])
    else:
        xm = (x0 + x1) / 2.0
        for y in (y0, y1):
            for x in range(x0, x1 + 1):
                g = zt - int(np.floor(w / 2.0 - abs(x - xm)))
                s.mat[x, y, g:zt] = mat
        for k in range(w // 2 + 1):
            z = zt - k
            for xx in (x0 - 1 + k, x1 + 1 - k):
                if rng.random() < 0.75:
                    s.mat[xx, y0 - 1:y0 + d // 2 + 2, z] = m['slate']
                    s.mat[xx, y0 - 1:y0 + d // 2 + 2, z + 1] = np.where(s.mat[xx, y0 - 1:y0 + d // 2 + 2, z + 1] == 0, m['slate'],
                                                                       s.mat[xx, y0 - 1:y0 + d // 2 + 2, z + 1])
    # doors at the water line, windows (some lit)
    s.carve(x0 + w // 2, x0 + w // 2 + 1, y0, y0, 61, 58)
    s.carve(x0, x0, y0 + d // 2, y0 + d // 2 + 1, 61, 58)
    for xw in range(x0 + 2, x1 - 1, 3):
        for yw in (y0, y1):
            s.mat[xw, yw, 52:54] = m['glow'] if rng.random() < 0.18 else 0
    for yw in range(y0 + 2, y1 - 1, 3):
        for xw in (x0, x1):
            s.mat[xw, yw, 52:54] = m['glow'] if rng.random() < 0.18 else 0
    s.box(x1 - 1, x1, y1 - 1, y1, 62, zt - 5, m['rock'])                    # chimney
    Xg, Yg = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    walls = (Xg >= x0) & (Xg <= x1) & (Yg >= y0) & (Yg <= y1) & ((Xg == x0) | (Xg == x1) | (Yg == y0) | (Yg == y1))
    walls &= ~((Xg >= x1 - 1) & (Yg >= y1 - 1))
    ruin(s, walls, amp=6, seed=seed, scale=4.0, base=0.42, only_above=56)


def causeways(s, m, L, H):
    """Raised stone causeways at z 59 across the fen; a few edge stones slumped to z 60."""
    X, Y = L.X, L.Y
    cw = L.causeway & (H >= 58)
    slump = cw & ~ndimage.binary_erosion(L.causeway | ~L.west, iterations=1) & (value_noise(X, Y, None, scale=2, seed=SEED + 8) > 0.62)
    for x, y in np.argwhere(cw):
        z0 = FLOOR + (1 if slump[x, y] else 0)
        s.mat[x, y, :63] = 0
        s.mat[x, y, z0:63] = m['quay']
        s.mat[x, y, z0] = m['causeway']


# ============================================================================================== cathedral
def crossing_tower(s, m):
    """The crossing tower (bell tower) with twin stair cores, belfry, bell, clock faces. West half authored
    (centred on x 256); the scene mirror makes the east half. Also used unchanged by v2."""
    C = SPEC['cathedral']
    tw = C['tower']
    # ---------------------------------------------------------------- crossing tower (the bell tower)
    x0 = tw['x0']
    (ny_a, ny_b), (sy_a, sy_b) = tw['y_walls']
    top = tw['top']
    s.box(x0, x0 + 2, ny_a, sy_b, 62, top, m['stone_dk'])                       # west wall
    s.box(x0, 255, ny_a, ny_b, 62, top, m['stone_dk'])                          # north wall
    s.box(x0, 255, sy_a, sy_b, 62, top, m['stone_dk'])                          # south wall
    s.box(x0 + 3, 255, ny_b + 1, sy_a - 1, FLOOR, FLOOR, m['floor'])
    # ground arches (to transept, nave, choir)
    carve_arch_x(s, x0, x0 + 2, 250, 261, FLOOR - 1, 51)
    carve_arch_y(s, ny_a, ny_b, 250, 262, FLOOR - 1, 51)
    carve_arch_y(s, sy_a, sy_b, 250, 262, FLOOR - 1, 51)
    # ringing-chamber slits and paired belfry lancets on every face
    for (u0, u1) in ((249, 252), (259, 262)):
        carve_arch_x(s, x0, x0 + 2, u0, u1, 31, 30)
        carve_arch_y(s, ny_a, ny_b, u0, u1, 31, 30)
        carve_arch_y(s, sy_a, sy_b, u0, u1, 31, 30)
    for (u0, u1) in ((253, 254),):
        carve_arch_y(s, ny_a, ny_b, u0, u1 + 5, 40, 38)
        carve_arch_y(s, sy_a, sy_b, u0, u1 + 5, 40, 38)
    # blind arcading above the roof line (1-voxel recess in the outer skin)
    for (u0, u1) in ((247, 250), (253, 258), (261, 264)):
        U, Z = np.meshgrid(np.arange(u0, u1 + 1), np.arange(44, 53), indexing='ij')
        o = arch_open(U, Z, u0, u1, 49)
        s.mat[x0, U[o], Z[o]] = 0
        o2 = o & (U <= 255)
        s.mat[U[o2], ny_a, Z[o2]] = 0
        s.mat[U[o2], sy_b, Z[o2]] = 0
    # clock face on the west (and, mirrored, east) face, stopped at midnight - seen from each esplanade
    yc_, zc_ = 255.5, 38
    Yc, Zc = np.meshgrid(np.arange(250, 262), np.arange(32, 45), indexing='ij')
    rc = np.hypot(Yc - yc_, Zc - zc_)
    s.mat[x0 - 1, Yc[rc <= 5.0], Zc[rc <= 5.0]] = m['trim']
    s.mat[x0 - 1, Yc[rc <= 3.9], Zc[rc <= 3.9]] = m['dial']
    angc = np.arctan2(Zc - zc_, Yc - yc_)
    marks = (rc > 3.0) & (rc <= 3.9) & (np.abs(((angc + np.pi / 12) % (np.pi / 6)) - np.pi / 12) * rc < 0.45)
    s.mat[x0 - 1, Yc[marks], Zc[marks]] = m['iron']
    s.mat[x0 - 1, 255:257, 35:39] = m['iron']                              # both hands at XII
    s.mat[x0 - 1, 255:257, 38] = m['iron']
    # angle buttresses on the outer corners, corbelled out above the roofs, stepping back as they rise
    for (ya, yb, ydir) in ((ny_a, ny_a + 2, -1), (sy_b - 2, sy_b, 1)):
        for (z_hi, z_lo, d) in ((44, 37, 3), (36, 31, 2), (30, 26, 1)):
            s.box(x0 - d, x0 - 1, ya, yb, z_lo, z_hi, m['stone_dk'])
            s.mat[x0 - d, ya:yb + 1, z_hi] = m['trim']
            yo = ya - d if ydir < 0 else yb + 1
            yo1 = ya - 1 if ydir < 0 else yb + d
            s.box(x0, x0 + 2, min(yo, yo1), max(yo, yo1), z_lo, z_hi, m['stone_dk'])
            s.mat[x0:x0 + 3, (min(yo, yo1) if ydir < 0 else max(yo, yo1)), z_hi] = m['trim']
        for k, dz in enumerate((45, 46, 47)):                                # corbels under the first stage
            s.mat[x0 - 3 + k, ya:yb + 1, dz] = m['trim']
            yo = ya - 3 + k if ydir < 0 else yb + 3 - k
            s.mat[x0:x0 + 3, yo, dz] = m['trim']
    # corbel table + cornice under the parapet
    for y in range(ny_a, sy_b + 1):
        s.mat[x0 - 1, y, top] = m['trim']
        if y % 2 == 0:
            s.mat[x0 - 1, y, top + 1] = m['trim']
    for x in range(x0, 256):
        for yy, yo in ((ny_a, ny_a - 1), (sy_b, sy_b + 1)):
            s.mat[x, yo, top] = m['trim']
            if x % 2 == 0:
                s.mat[x, yo, top + 1] = m['trim']
    # string courses
    for zc in (44, 31):
        s.mat[x0 - 1, ny_a:sy_b + 1, zc] = m['trim']
        s.mat[x0 - 1:256, ny_a - 1, zc] = m['trim']
        s.mat[x0 - 1:256, sy_b + 1, zc] = m['trim']
    # crenellated top + corner pinnacles
    for y in range(ny_a, sy_b + 1):
        if (y // 2) % 2 == 0:
            s.mat[x0, y, top - 1] = m['trim']
    for x in range(x0, 256):
        if (x // 2) % 2 == 0:
            s.mat[x, ny_a, top - 1] = m['trim']; s.mat[x, sy_b, top - 1] = m['trim']
    for (ya, yb) in ((ny_a, ny_b), (sy_a, sy_b)):
        s.box(x0, x0 + 2, ya, yb, top - 1, top - 3, m['stone'])
        s.mat[x0 + 1, ya + 1, top - 5:top - 3] = m['trim']
    # ---- twin stair core (west half; the mirror makes the east core). stand(z) = standing voxel.
    def step(xa, xb, ya, yb, stand, mat=m['trim']):
        s.mat[xa:xb + 1, ya:yb + 1, stand:FLOOR] = m['stone_dk']
        s.mat[xa:xb + 1, ya:yb + 1, stand] = mat
    for x in range(247, 256):                                   # flight A: east along the north wall, 58 -> 50
        step(x, x, 247, 249, 58 - (x - 247))
    for y in range(250, 262):                                   # central flight: south along x 254-258, 49 -> 38
        step(254, 255, y, y, 49 - (y - 250))
    step(253, 255, 262, 264, 38)                                # south landing
    for x in (252, 251, 250):                                   # flight B: west along the south wall, 37 -> 35
        step(x, x, 262, 264, 37 - (252 - x))
    step(247, 249, 262, 264, 34)                                # SW landing
    bf = tw['belfry_floor']
    for y, z in ((261, 33), (260, 32)):                         # flight C: north to the belfry floor (z 32)
        step(247, 249, y, y, z)
    # belfry floor with the stairwell open over flights B/C and the SW landing (headroom + step-up clearance)
    s.box(247, 255, 247, 264, bf, bf, m['floor'])
    s.carve(247, 249, 261, 264, bf, bf)
    s.carve(250, 252, 262, 264, bf, bf)
    s.box(247, 249, 260, 260, bf, bf, m['trim'])
    # timber bell frame + bronze bell hung from the beam (centred on x 256)
    s.box(247, 255, 255, 256, 24, 24, m['timber'])
    for (zz, xa, ya, yb) in ((25, 255, 255, 256), (26, 254, 254, 257), (27, 253, 253, 258), (28, 252, 252, 259)):
        s.box(xa, 255, ya, yb, zz, zz, m['bronze'])
    s.mat[255, 255:257, 29] = m['iron']                          # clapper
    s.box(250, 250, 247, 264, 24, 24, m['timber'])               # cross beam, wall to wall



def tower_gargoyles(s, m):
    tw = SPEC['cathedral']['tower']
    x0, top = tw['x0'], tw['top']
    g = P.gargoyle(m)
    gw = P.Prefab(np.rot90(g.a, 2, axes=(0, 1)).copy(), origin=(g.a.shape[0] - 1, 1))
    for y in (252, 259):
        art.stamp(s, gw, x0, y, top, replace_air_only=True)


def cathedral(s, m, rng, with_tower=True):
    C = SPEC['cathedral']
    ax0, ax1 = C['aisle_wall_x']
    rx0, rx1 = C['arcade_x']
    ny0, ny1 = C['nave_y']
    cy0, cy1 = C['choir_y']
    T = C['transept']
    tw = C['tower']
    glass = m['glass']

    # ---------------------------------------------------------------- floors (dry) - checker stone, solid to z 62
    def floor_box(x0, x1, y0, y1, z=FLOOR):
        x1 = min(x1, 255)
        s.mat[x0:x1 + 1, y0:y1 + 1, :63] = 0
        s.mat[x0:x1 + 1, y0:y1 + 1, z + 1:63] = m['stone_dk']
        s.mat[x0:x1 + 1, y0:y1 + 1, z] = m['floor']
    floor_box(250, 255, C['facade']['wall_y'][0], ny1)     # processional walkway (nave flooded either side)
    if C.get('cross_walk', True):
        floor_box(236, 249, 186, 190)                      # cross walk from the north aisle door
    floor_box(T['x'][0], 243, T['y'][0] + 2, T['y'][1] - 2)  # transept
    floor_box(247, 255, 247, 264)                          # crossing
    floor_box(236, 255, cy0, cy1)                          # choir (dry)
    X, Y = np.meshgrid(np.arange(224, 256), np.arange(326, 360), indexing='ij')
    ap = np.hypot(X - 256, Y - 330) < C['apse']['r'][0]
    s.mat[X[ap], Y[ap], :63] = 0
    s.mat[X[ap], Y[ap], FLOOR + 1:63] = m['stone_dk']
    s.mat[X[ap], Y[ap], FLOOR] = m['floor']

    # ---------------------------------------------------------------- aisle walls + nave arcade (north arm, choir)
    for (y0, y1) in ((ny0, T['y'][0] - 1), (T['y'][1] + 1, cy1)):
        s.box(ax0, ax1, y0, y1, 62, C['aisle_top'], m['stone'])
    for (y0, y1) in ((ny0, 243), (268, cy1)):
        s.box(rx0, rx1, y0, y1, 62, C['arcade_top'], m['stone'])
    piers = C['piers_north'] + C['piers_south']
    # arcade arches between piers (floor-level openings) and clerestory windows above
    for seq, ylim in ((C['piers_north'] + [244], (ny0, 243)), ([268] + C['piers_south'] + [330], (268, cy1))):
        seq = [ylim[0] - 2] + seq if seq[0] > ylim[0] + 4 else seq
        for a, b in zip(seq[:-1], seq[1:]):
            u0, u1 = a + 2, b - 1
            if u1 - u0 < 4:
                continue
            zb = 61 if ylim[0] == ny0 else FLOOR - 1
            carve_arch_x(s, rx0, rx1, u0, u1, zb, 52)
            mid = (u0 + u1) // 2
            carve_arch_x(s, rx0, rx1, mid - 1, mid + 2, 42, 39)          # clerestory window
            if rng.random() < 0.45:                                       # some keep their glass
                carve_arch_x(s, rx0, rx0, mid - 1, mid + 2, 42, 39, fill=glass[int(rng.integers(0, 4))])
            # aisle-wall lancet (with glass in the outer plane, sometimes shattered)
            carve_arch_x(s, ax0, ax1, mid - 1, mid + 2, 57, 54)
            if rng.random() < 0.8:
                g = glass[int(rng.integers(0, 4))]
                carve_arch_x(s, ax0, ax0, mid - 1, mid + 2, 57, 54, fill=g)
                if rng.random() < 0.4:                                    # broken: top half gone
                    carve_arch_x(s, ax0, ax0, mid - 1, mid + 2, 53, 54, fill=0)
    if C.get('cross_walk', True):
        s.mat[rx0:rx1 + 1, 186:191, FLOOR] = m['floor']                 # cross walk runs through the arcade
        s.mat[rx0:rx1 + 1, 186:191, FLOOR + 1:63] = m['stone_dk']
    # side doors (north + south aisle) with a lintel moulding
    for dyc in C['doors_y']:
        carve_arch_x(s, ax0, ax1, dyc - 2, dyc + 2, FLOOR - 1, 55)
        s.mat[ax0 - 1, dyc - 3:dyc + 4, 51] = m['trim']
        s.mat[ax0 - 1, dyc - 3, 51:FLOOR] = m['trim']; s.mat[ax0 - 1, dyc + 3, 51:FLOOR] = m['trim']
        s.mat[ax0 - 1, dyc - 3:dyc + 4, FLOOR + 1:63] = m['stone_dk']
    # string course under the clerestory windows, on the outside of the arcade wall
    for (y0, y1) in ((ny0, 243), (268, cy1)):
        sel = s.mat[rx0, y0:y1 + 1, 43] > 0
        s.mat[rx0 - 1, y0:y1 + 1, 43][sel] = m['trim']

    # ---------------------------------------------------------------- flying buttresses
    for p in piers:
        s.box(226, 230, p - 1, p + 2, 62, 42, m['stone_dk'])
        s.box(226, 230, p - 1, p + 2, 42, 42, m['trim'])
        s.box(227, 229, p, p + 1, 41, 38, m['stone'])
        s.box(228, 228, p, p + 1, 37, 36, m['trim'])
        for x in range(231, 244):
            zt = int(round(41 + (x - 231) * (37 - 41) / 12.0))
            zb = int(round(zt + 1 + 3 * (1 - np.sin(np.pi * (x - 231) / 12.0))))
            s.box(x, x, p, p + 1, zt, zb, m['stone'])
            if x % 3 == 0:
                s.mat[x, p:p + 2, zt - 1] = m['trim']                    # crocketed coping
        # pier in the nave arcade continues to the floor (2x2), full height
        s.box(rx0, rx1, p, p + 1, 62, C['arcade_top'], m['stone_dk'])

    # ---------------------------------------------------------------- aisle roof remnants (lean-to, stepped 2-thick)
    bays = [(a + 2, b - 1) for a, b in zip(piers[:-1], piers[1:]) if b - a == 12]
    for (u0, u1) in bays:
        if rng.random() < 0.35:
            for x in range(ax0, rx0):
                zr = 45 - (x - ax0) // 2
                ys = slice(u0, u1 + 1)
                cut = int(rng.integers(0, 4)) if x > ax0 + 4 else 0
                s.mat[x, u0 + cut:u1 + 1, zr] = m['slate']
                s.mat[x, u0 + cut:u1 + 1, zr + 1] = np.where(s.mat[x, ys, zr + 1][cut:] == 0, m['slate'], s.mat[x, ys, zr + 1][cut:])

    # ---------------------------------------------------------------- vault ribs over the nave (a few survive)
    for yr in C.get('ribs_y', (188, 212, 294)):
        for x in range(rx1 + 1, 256):
            dx = 256 - x                                                   # 1..10
            zr = int(round(33 - np.sqrt(max(0.0, 121 - dx * dx)) * 0.55))
            s.box(x, x, yr, yr + 1, zr, zr + 1 if x > rx1 + 1 else C['arcade_top'], m['trim'])

    # ---------------------------------------------------------------- transept
    tx0, tx1 = T['x']; ty0, ty1 = T['y']
    s.box(tx0, tx0 + 1, ty0, ty1, 62, T['top'] - 2, m['stone'])                  # end wall
    for y in range(ty0, ty1 + 1):                                                # gable
        g = T['gable_mid'] + int(round(abs(y - 255.5) * 0.5))
        if g < T['top'] - 1:
            s.mat[tx0:tx0 + 2, y, g:T['top'] - 1] = m['stone']
            s.mat[tx0:tx0 + 2, y, g] = m['trim']
    for (y0, y1) in ((ty0, ty0 + 1), (ty1 - 1, ty1)):
        s.box(tx0, ax1, y0, y1, 62, T['top'], m['stone'])
        for xc in T.get('windows', (218, 225)):
            U, Z = np.meshgrid(np.arange(xc, xc + 4), np.arange(48, 58), indexing='ij')
            o = arch_open(U, Z, xc, xc + 3, 54)
            for yy in range(y0, y1 + 1):
                s.mat[U[o], yy, Z[o]] = 0
            gsel = U[o], Z[o]
            s.mat[gsel[0], y0 if y0 == ty0 else y1, gsel[1]] = glass[(xc // 7) % 4]
    # transept door + great window with mullions and glass
    carve_arch_x(s, tx0, tx0 + 1, 252, 259, FLOOR - 1, 55)
    carve_arch_x(s, tx0, tx0 + 1, 248, 263, 46, 44)
    U, Z = np.meshgrid(np.arange(248, 264), np.arange(30, 47), indexing='ij')
    o = arch_open(U, Z, 248, 263, 44)
    gl = np.where((Z // 3 + U // 4) % 2 == 0, glass[0], glass[1]).astype(np.uint8)
    gl = np.where(((U - 248) % 16 // 4 == 1) & (Z < 38), glass[2], gl)
    s.mat[tx0, U[o], Z[o]] = gl[o]
    for um in (251, 255, 256, 260):                                              # mullions
        sel = o & (U == um)
        s.mat[tx0 + 1, U[sel], Z[sel]] = m['trim']
    sel = o & (Z == 40)
    s.mat[tx0 + 1, U[sel], Z[sel]] = m['trim']                                   # transom
    # corner buttresses
    for (y0, y1) in ((ty0, ty0 + 3), (ty1 - 3, ty1)):
        s.box(tx0 - 3, tx0 - 1, y0, y1, 62, 38, m['stone_dk'])
        s.box(tx0 - 2, tx0 - 1, y0, y1, 37, 35, m['stone_dk'])
        s.box(tx0 - 1, tx0 - 1, y0 + 1, y1 - 1, 34, 33, m['trim'])

    if with_tower:
        crossing_tower(s, m)

    # ---------------------------------------------------------------- west facade: twin towers, gable, portal, rose
    F_ = C['facade']
    fx0, fx1 = F_['towers_x']; fy0, fy1 = F_['towers_y']
    s.box(fx0, fx1, fy0, fy1, 62, 26, m['stone'])
    s.carve(fx0 + 3, fx1 - 3, fy0 + 3, fy1 - 3, 61, 27)                         # hollow core (flooded)
    fb = [(fx0 - 3, fx0 - 1, fy0, fy0 + 3), (fx0, fx0 + 3, fy0 - 3, fy0 - 1),
          (fx1 - 3, fx1, fy0 - 3, fy0 - 1), (fx0 - 3, fx0 - 1, fy1 - 3, fy1)]
    if not F_.get('front_buttresses', True):
        fb = [b for b in fb if b[3] >= fy0]
    for (bx0, bx1, by0, by1) in fb:
        s.box(bx0, bx1, by0, by1, 62, 38, m['stone_dk'])
        s.box(bx0, bx1, by0, by1, 37, 37, m['trim'])
    for (u0, u1) in ((233, 236), (237, 240)):                                     # north face windows
        carve_arch_y(s, fy0, fy0 + 2, u0, u1, 52, 49)
        carve_arch_y(s, fy0, fy0 + 2, u0, u1, 38, 35)
        carve_arch_y(s, fy0, fy0 + 2, u0 + 1, u1 - 1, 31, 30)
    for (u0, u1) in ((139, 142), (145, 148)):                                     # west face windows
        carve_arch_x(s, fx0, fx0 + 2, u0, u1, 52, 49)
        carve_arch_x(s, fx0, fx0 + 2, u0, u1, 38, 35)
    for zc in (44, 33):
        s.mat[fx0 - 1, fy0:fy1 + 1, zc] = m['trim']
        if F_.get('front_buttresses', True):
            s.mat[fx0:fx1 + 1, fy0 - 1, zc] = m['trim']
    wy0, wy1 = F_['wall_y']
    for x in range(fx1 + 1, 256):
        g = F_.get('gable_base', 21) + int(round((255 - x) * 0.75))
        s.mat[x, wy0:wy1 + 1, g:63] = m['stone']
        s.mat[x, wy0:wy1 + 1, g] = m['trim']
    # portal with stepped archivolts (wider at the outer face), threshold at FLOOR
    for (y, u0, u1) in ((wy0, 248, 264), (wy0 + 1, 249, 263), (wy0 + 2, 250, 262), (wy0 + 3, 251, 261),
                        (wy0 + 4, 251, 261), (wy0 + 5, 251, 261)):
        carve_arch_y(s, y, y, u0, u1, FLOOR - 1, 54)
    s.mat[248:256, wy0:wy1 + 1, FLOOR] = m['floor']
    # rose window: tracery plane y = wy0 + 2, glass plane wy0 + 3, open elsewhere through the wall
    zc, rr = F_['rose']
    Xr, Zr = np.meshgrid(np.arange(246, 256), np.arange(int(zc - rr - 1), int(zc + rr + 2)), indexing='ij')
    r = np.hypot(Xr - 256, Zr - zc)
    disk = r <= rr
    ang = np.arctan2(Zr - zc, Xr - 256)
    for y in range(wy0, wy1 + 1):
        s.mat[Xr[disk], y, Zr[disk]] = 0
    sector = (np.floor((ang + np.pi) / (np.pi / 4)).astype(int)) % 2
    gcol = np.where(r < 3.2, m['glass'][1], np.where(sector == 0, m['glass'][0], m['glass'][2]))
    s.mat[Xr[disk], wy0 + 3, Zr[disk]] = gcol[disk]
    spoke = np.min(np.abs(((ang + np.pi / 8) % (np.pi / 4)) - np.pi / 8)[..., None] * r[..., None], axis=-1) < 0.6
    trac = disk & ((r >= rr - 1.0) | (r <= 1.5) | ((r >= 3.6) & (r <= 4.5)) | (spoke & (r > 1.5)))
    s.mat[Xr[trac], wy0 + 2, Zr[trac]] = m['trim']
    # ring moulding around the rose on the outer face
    ringm = (r > rr) & (r <= rr + 1.0)
    s.mat[Xr[ringm], wy0 - 1, Zr[ringm]] = m['trim']

    # ---------------------------------------------------------------- apse (choir end), lancets, breach, buttresses
    A_ = C['apse']
    (acx, acy) = A_['centre']
    Xa, Ya = np.meshgrid(np.arange(224, 256), np.arange(acy, acy + 30), indexing='ij')
    ra = np.hypot(Xa - acx, Ya - acy)
    ring_ = (ra >= A_['r'][0]) & (ra <= A_['r'][1])
    for x, y in zip(Xa[ring_], Ya[ring_]):
        s.mat[x, y, A_['top']:63] = m['stone']
    th = np.arctan2(acx - Xa, Ya - acy)                                       # 0 on the axis (south), + to the west
    for phi in (0.42, 0.84, 1.26):
        win = ring_ & (np.abs(th - phi) * ra < 2.1)
        for x, y in zip(Xa[win], Ya[win]):
            u = int(round((th[x - 224, y - acy] - phi) * ra[x - 224, y - acy]))
            for z in range(40, 57):
                if arch_open(np.array([u]), np.array([z]), -2, 1, 47)[0]:
                    s.mat[x, y, z] = 0
                    if ra[x - 224, y - acy] >= A_['r'][1] - 0.8 and rng.random() < 0.85:
                        s.mat[x, y, z] = glass[int((phi * 10)) % 4]
        bdir = phi + 0.21                                                      # buttress between lancets
        for rad in np.arange(A_['r'][1], A_['r'][1] + 5.0, 0.5):
            for off in (-1, 0, 1):
                bx_ = int(round(acx - np.sin(bdir) * rad + np.cos(bdir) * off * 0.9))
                by_ = int(round(acy + np.cos(bdir) * rad + np.sin(bdir) * off * 0.9))
                if bx_ <= 255:
                    zt = int(40 + (rad - A_['r'][1]) * 1.4)
                    s.mat[bx_, by_, zt:63] = m['stone_dk']
    # breach on the axis
    for x in range(249, 256):
        for y in range(acy + 20, acy + 26):
            zcut = 44 + int(round(4 * value_noise(np.array([x]), np.array([y]), None, scale=2.0, seed=SEED + 41)[0]))
            if 256 - x <= 4:
                s.mat[x, y, :FLOOR] = 0
                s.mat[x, y, FLOOR:63] = m['stone_dk']
                s.mat[x, y, FLOOR] = m['floor']
            else:
                s.mat[x, y, :zcut] = 0

    # ---------------------------------------------------------------- choir furnishings: dais, altar, stalls
    s.box(248, 255, 316, 327, 58, 58, m['trim'])
    s.box(252, 255, 319, 323, 56, 57, m['stone'])
    s.box(251, 255, 319, 323, 55, 55, m['trim'])
    art.stamp(s, P.candles(SEED + 5, m, n=5), 253, 321, 55, replace_air_only=True)
    art.stamp(s, P.skull_pile(SEED + 6, m, r=1), 249, 318, 58, replace_air_only=True)
    for y in range(272, 312, 4):                                     # choir stalls (some smashed)
        if rng.random() < 0.75:
            s.box(238, 241, y, y + 1, 58, 58, m['timber'])
            s.box(238, 238, y, y + 1, 57, 56, m['timber'])

    # ---------------------------------------------------------------- ruin pass (tops knocked off, bays collapsed)
    X2, Y2 = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    walls_nave = (((X2 >= ax0) & (X2 <= ax1)) | ((X2 >= rx0) & (X2 <= rx1))) & (
        ((Y2 >= ny0) & (Y2 <= 235)) | ((Y2 >= 276) & (Y2 <= cy1)))
    ribs = np.zeros_like(walls_nave)
    for yr in C.get('ribs_y', (188, 212, 294)):
        ribs |= (Y2 >= yr - 2) & (Y2 <= yr + 3)
    ruin(s, walls_nave & (X2 <= 245) & ~ribs, amp=10, seed=SEED + 50, only_above=50)
    trans_walls = (X2 >= tx0) & (X2 <= ax1) & (((Y2 >= ty0) & (Y2 <= ty0 + 1)) | ((Y2 >= ty1 - 1) & (Y2 <= ty1)))
    trans_walls |= (X2 >= tx0) & (X2 <= tx0 + 1) & (Y2 >= ty0) & (Y2 <= ty1) & ((Y2 < 246) | (Y2 > 265))
    ruin(s, trans_walls, amp=8, seed=SEED + 51, only_above=50)
    ftw = (X2 >= fx0 - 3) & (X2 <= fx1) & (Y2 >= fy0 - 3) & (Y2 <= fy1)
    ruin(s, ftw, amp=7, seed=SEED + 52, base=0.3, only_above=50)
    apw = (np.hypot(X2 - acx, Y2 - acy) >= A_['r'][0]) & (np.hypot(X2 - acx, Y2 - acy) <= A_['r'][1] + 6) & (Y2 >= acy) & (X2 <= 255)
    ruin(s, apw, amp=9, seed=SEED + 53, only_above=50)

    # rubble at wall feet and on dry floors (from the collapsed vault)
    for (x, y) in C.get('rubble', ((239, 200), (242, 222), (240, 290), (238, 308), (248, 170), (226, 252), (229, 262), (241, 330))):
        art.stamp(s, P.boulder(int(rng.integers(1 << 30)), m, r=float(rng.uniform(1.6, 2.8))), x, y,
                  top_z(s, x, y), replace_air_only=True)

    # gargoyles on the bell tower top and on the facade towers (facing outward, -x)
    g = P.gargoyle(m)
    if with_tower:
        tower_gargoyles(s, m)
    gn = P.Prefab(np.rot90(g.a, 3, axes=(0, 1)).copy(), origin=(1, g.a.shape[0] - 1))
    for (x, y) in (((fx0 + 1, fy0), (fx1 - 2, fy0)) if F_.get('gargoyles', True) else ()):
        art.stamp(s, gn, x, y, top_z(s, x, y), replace_air_only=True)


# ============================================================================================== spawn precinct
def precinct(s, m, L, rng):
    sc = SPEC['screen']
    (sx0, sx1), (sy0, sy1) = sc['x'], sc['y']
    zt = sc['top']
    s.box(sx0, sx1, sy0, sy1, BANK - 1, zt, m['stone'])
    s.box(sx0 - 1, sx1 + 1, sy0, sy1, BANK - 1, BANK - 1, m['stone_dk'])                 # plinth
    for yc in (229, 237, 245, 267, 275, 283):
        carve_arch_x(s, sx0, sx1, yc - 2, yc + 1, BANK - 1, 36)
    for y in range(sy0, sy1 + 1):                                                          # coping + merlons
        if s.mat[sx0, y, zt]:
            s.mat[sx0:sx1 + 1, y, zt] = m['trim']
            if (y // 2) % 2 == 0:
                s.mat[sx1, y, zt - 1] = m['trim']
    gh = sc['gatehouse']
    s.box(gh['x'][0], gh['x'][1], gh['y'][0], gh['y'][1], BANK - 1, gh['top'], m['stone_dk'])
    carve_arch_x(s, gh['x'][0], gh['x'][1], 252, 260, BANK - 1, 35)
    for (ya, yb) in ((gh['y'][0], gh['y'][0] + 2), (gh['y'][1] - 2, gh['y'][1])):
        s.box(gh['x'][0], gh['x'][1], ya, yb, gh['top'] - 1, gh['top'] - 3, m['stone'])     # turret caps
        s.mat[gh['x'][0] + 2, (ya + yb) // 2, gh['top'] - 5:gh['top'] - 3] = m['trim']
    for y in range(gh['y'][0], gh['y'][1] + 1):
        if (y // 2) % 2 == 0:
            s.mat[gh['x'][0], y, gh['top'] - 1] = m['trim']; s.mat[gh['x'][1], y, gh['top'] - 1] = m['trim']
    s.mat[gh['x'][0] - 1, 251:262, 34] = m['trim']                                       # hood moulding
    # team banners on the gatehouse (spawn side, x 139) - blue here, recoloured red on the mirror
    for yb in (249, 263):
        s.mat[gh['x'][0] - 1, yb, 26] = m['iron']
        s.box(gh['x'][0] - 1, gh['x'][0] - 1, yb - 1, yb + 1, 27, 33, m['banner_blue'])
        s.mat[gh['x'][0] - 1, yb, 34] = m['banner_blue']
        s.mat[gh['x'][0] - 1, yb - 1:yb + 2, 27] = m['gold']
    # lanterns at the square corners + along the gate axis
    lp = P.lantern_post(m, h=4)
    for (x, y) in ((95, 233), (95, 279), (137, 231), (137, 281), (146, 246), (146, 266)):
        art.stamp(s, lp, x, y, top_z(s, x, y), replace_air_only=True)

    # --- chapel of the drowned (north of the square)
    c = SPEC['chapel']
    (cx0, cx1), (cy0, cy1) = c['x'], c['y']
    wt = 30
    s.box(cx0, cx1, cy0, cy1, BANK - 1, wt, m['stone'])
    s.carve(cx0 + 2, cx1 - 2, cy0 + 2, cy1 - 2, BANK - 1, wt)
    s.box(cx0 + 2, cx1 - 2, cy0 + 2, cy1 - 2, BANK, BANK, m['floor'])
    ymid = (cy0 + cy1) / 2.0
    for x in (cx0, cx0 + 1, cx1 - 1, cx1):                                                 # gable ends
        for y in range(cy0, cy1 + 1):
            g = wt - int(np.floor(10 - abs(y - ymid)))
            s.mat[x, y, g:wt] = m['stone']
    for k in range(11):                                                                    # slate roof, east part only
        z = wt - k
        for (ya, yb) in ((cy0 - 1 + k, cy0 + k), (cy1 - k, cy1 + 1 - k)):
            if ya <= yb and ya <= cy1 + 1:
                s.mat[cx0 + 14:cx1 + 2, ya:yb + 1, z] = m['slate']
    for x in range(cx0 + 2, cx0 + 14, 4):                                                  # bare rafters (west)
        for k in range(10):
            s.mat[x, cy0 + k, wt - k:wt - k + 2] = m['timber']; s.mat[x, cy1 - k, wt - k:wt - k + 2] = m['timber']
    carve_arch_x  # noqa
    U, Z = np.meshgrid(np.arange(116, 121), np.arange(30, 40), indexing='ij')
    o = arch_open(U, Z, 116, 120, 35)
    s.mat[U[o], cy1, Z[o]] = 0; s.mat[U[o], cy1 - 1, Z[o]] = 0                             # south door
    for xc in (108, 124, 128):
        for yy in (cy0, cy1):
            U, Z = np.meshgrid(np.arange(xc, xc + 3), np.arange(30, 38), indexing='ij')
            o = arch_open(U, Z, xc, xc + 2, 34)
            s.mat[U[o], yy, Z[o]] = m['glass'][1]
            s.mat[U[o], yy + (1 if yy == cy0 else -1), Z[o]] = 0
    s.box(cx1 - 1, cx1 + 1, int(ymid) - 1, int(ymid) + 1, 20, 18, m['stone'])             # bellcote
    s.carve(cx1 - 1, cx1 + 1, int(ymid), int(ymid), 19, 19)
    s.mat[cx1, int(ymid), 19] = m['bronze']
    s.mat[cx1, int(ymid), 17] = m['trim']
    art.stamp(s, P.candles(SEED + 21, m, n=6), cx0 + 4, int(ymid), BANK, replace_air_only=True)
    for x in range(cx0 + 8, cx1 - 3, 4):
        for (ya, yb) in ((cy0 + 3, cy0 + 7), (cy1 - 7, cy1 - 3)):
            if rng.random() < 0.7:
                s.box(x, x, ya, yb, BANK - 1, BANK - 1, m['timber'])
    # --- ossuary (south of the square): open arcade facing the square, skull shelves inside
    o_ = SPEC['ossuary']
    (ox0, ox1), (oy0, oy1) = o_['x'], o_['y']
    s.box(ox0, ox1, oy0, oy1, BANK - 1, 32, m['stone_dk'])
    s.carve(ox0 + 2, ox1 - 2, oy0 + 2, oy1 - 2, BANK - 1, 32)
    s.box(ox0 + 2, ox1 - 2, oy0 + 2, oy1 - 2, BANK, BANK, m['floor'])
    ymo = (oy0 + oy1) / 2.0
    for k in range(9):
        z = 32 - k
        for (ya, yb) in ((oy0 - 1 + k, oy0 + k), (oy1 - k, oy1 + 1 - k)):
            if ya <= yb:
                s.mat[ox0 - 1:ox1 + 2, ya:yb + 1, z] = m['slate']
    for x in (ox0, ox0 + 1, ox1 - 1, ox1):
        for y in range(oy0, oy1 + 1):
            g = 32 - int(np.floor(8.5 - abs(y - ymo)))
            s.mat[x, y, max(g, 24):32] = m['stone_dk']
    for xc in (109, 116, 123):
        U, Z = np.meshgrid(np.arange(xc, xc + 5), np.arange(31, 40), indexing='ij')
        o = arch_open(U, Z, xc, xc + 4, 36)
        s.mat[U[o], oy0, Z[o]] = 0; s.mat[U[o], oy0 + 1, Z[o]] = 0
    for x in range(ox0 + 2, ox1 - 1):                                                       # bone shelves
        s.mat[x, oy1 - 2, BANK - 1] = m['bone'] if x % 3 else m['skull']
        s.mat[x, oy1 - 2, BANK - 2] = m['skull'] if x % 2 else m['bone']
        s.mat[x, oy1 - 2, BANK - 4] = m['timber']
        s.mat[x, oy1 - 2, BANK - 5] = m['skull'] if x % 3 else 0
    art.stamp(s, P.skull_pile(SEED + 22, m, r=2), 118, oy0 + 7, BANK, replace_air_only=True)
    # --- graveyard of the drowned behind the spawn (west)
    from scenes import hollowfen_props as HP
    gyd = SPEC['graveyard']
    (gx0, gx1), (gy0, gy1) = gyd['x'], gyd['y']
    for x in range(gx0, gx1 + 1):
        for y in (gy0, gy1):
            s.mat[x, y, BANK - 1] = m['stone_dk']
            if x % 4 == 0:
                s.mat[x, y, BANK - 2] = m['trim']
    for y in range(gy0, gy1 + 1):
        if not (250 <= y <= 262):
            s.mat[gx0, y, BANK - 1] = m['stone_dk']
            if y % 4 == 0:
                s.mat[gx0, y, BANK - 2] = m['trim']
    kinds = ['slab', 'slab', 'cross', 'cross', 'obelisk', 'celtic', 'tomb']
    for gx in range(gx0 + 4, gx1 - 3, 6):
        for gy in range(gy0 + 4, gy1 - 3, 5):
            if 250 <= gy <= 262 or rng.random() < 0.15:
                continue
            kind = kinds[int(rng.integers(0, len(kinds)))]
            plant(s, HP.headstone(int(rng.integers(1 << 30)), m, kind), gx + int(rng.integers(-1, 2)), gy, BANK)
    s.box(gx0 + 1, gx1, 252, 260, BANK, BANK, m['gravel'])
    plant(s, P.snag(SEED + 30, m, height=11), 62, 240, BANK)
    plant(s, P.snag(SEED + 31, m, height=9), 78, 274, BANK)
    # path from the graveyard gate through the square and the gatehouse to the esplanade
    path = (L.X >= gx1 + 1) & (L.X <= 97) & (np.abs(L.Y - 256) <= 3)
    s.mat[:, :, BANK][path & (s.mat[:, :, BANK] > 0)] = m['gravel']
    # gravel paths: square -> chapel door, ossuary arcade, gatehouse
    for (xa, xb, ya, yb) in ((115, 121, 223, 235), (114, 122, 277, 289), (139, 147, 252, 260)):
        sel = np.zeros(s.mat.shape[:2], bool); sel[xa:xb + 1, ya:yb + 1] = True
        sel &= (s.mat[:, :, BANK] > 0) & (s.mat[:, :, BANK - 1] == 0)
        s.mat[:, :, BANK][sel] = m['gravel']
    # parapet along the precinct block's quay edges (north + south), outside the spawn square
    pb = SPEC['precinct_block']
    for y in (pb['y'][0], pb['y'][1]):
        for x in range(60, pb['x'][1] + 1):
            if L.quay_edge[x, y] and s.mat[x, y, BANK] and not s.mat[x, y, BANK - 1] and not L.stairs[x, y]:
                s.mat[x, y, BANK - 1] = m['coping']
                if x % 6 == 0:
                    s.mat[x, y, BANK - 2] = m['coping']
    # landmarks: the hanging tree, a calvary, a well, benches
    plant(s, P.hanging_tree(SEED + 40, m, height=15, spread=8), 94, 214, BANK)
    plant(s, P.calvary(m), 92, 298, BANK)
    plant(s, P.well(m), 140, 210, BANK)
    for (bx_, by_) in ((104, 230), (128, 230), (104, 283), (128, 283)):
        s.box(bx_, bx_ + 3, by_, by_, BANK - 1, BANK - 1, m['timber'])
    # pumpkin patch west of the chapel (vines + pumpkins), overgrown herb beds south-west of the ossuary
    for (px0, px1, py0, py1) in ((88, 101, 196, 212), (86, 100, 306, 318)):
        for x in range(px0, px1 + 1):
            for y in range(py0, py1 + 1):
                if s.mat[x, y, BANK - 1] == 0 and s.mat[x, y, BANK]:
                    s.mat[x, y, BANK] = m['soil'] if (y % 3) else m['grass']
        for x in range(px0 + 1, px1, 3):
            for y in range(py0 + 1, py1, 3):
                if rng.random() < 0.7 and s.mat[x, y, BANK - 1] == 0:
                    if px0 == 88:
                        plant(s, P.pumpkin(int(rng.integers(1 << 30)), m, size=int(rng.choice([1, 1, 2, 2, 3])),
                                           lit=rng.random() < 0.3, face=(0, 1)), x, y, BANK)
                    else:
                        plant(s, P.bush(int(rng.integers(1 << 30)), m, r=1.3), x, y, BANK)
    for (tx, ty) in ((88, 228), (100, 292), (146, 198), (146, 314)):
        plant(s, P.snag(int(rng.integers(1 << 30)), m, height=int(rng.integers(8, 12))), tx, ty, BANK)
    # buttresses + ivy on the chapel and ossuary
    for x in range(cx0 + 3, cx1 - 1, 6):
        if 114 <= x <= 122:
            continue
        for (yw, yo) in ((cy0, cy0 - 1), (cy1, cy1 + 1)):
            s.mat[x:x + 2, yo, 33:BANK] = m['stone_dk']
            s.mat[x:x + 2, yo, 32] = m['trim']
    for x in range(ox0 + 3, ox1 - 1, 7):
        s.mat[x:x + 2, oy1 + 1, 34:BANK] = m['stone_dk']
        s.mat[x:x + 2, oy1 + 1, 33] = m['trim']
    for (xa, xb, yy) in ((cx0, cx0 + 9, cy0 - 1), (ox1 - 8, ox1, oy1 + 1)):
        for x in range(xa, xb + 1):
            L_ = int(2 + 6 * value_noise(np.array([x]), np.array([yy]), None, scale=2.0, seed=SEED + 44)[0])
            for z in range(BANK - L_, BANK):
                if s.mat[x, yy, z] == 0 and (s.mat[x, yy + 1, z] or s.mat[x, yy - 1, z]):
                    s.mat[x, yy, z] = m['ivy']
    # jack-o'-lanterns along the precinct edge and the chapel/ossuary doors (none inside the spawn square)
    for (x, y, f) in ((114, 226, (0, 1)), (122, 226, (0, 1)), (112, 287, (0, -1)), (124, 287, (0, -1)),
                      (92, 244, (1, 0)), (92, 268, (1, 0)), (139, 246, (-1, 0)), (139, 266, (-1, 0))):
        art.stamp(s, P.pumpkin(int(rng.integers(1 << 30)), m, size=int(rng.integers(2, 4)), face=f), x, y,
                  top_z(s, x, y), replace_air_only=True)


def cottage_ruin(s, m, cx, cy, w, d, seed):
    rng = np.random.default_rng(seed)
    x0, y0 = cx - w // 2, cy - d // 2
    x1, y1 = x0 + w - 1, y0 + d - 1
    fz = int(np.median([top_z(s, x, y) for x in (x0, x1) for y in (y0, y1)]))
    for x in range(x0 - 1, x1 + 2):                                     # level pad
        for y in range(y0 - 1, y1 + 2):
            s.mat[x, y, :fz] = 0
            s.mat[x, y, fz:63] = np.where(s.mat[x, y, fz:63] == 0, m['soil'], s.mat[x, y, fz:63])
            s.mat[x, y, fz] = m['gravel']
    wh = int(rng.integers(5, 7))
    s.box(x0, x1, y0, y1, fz - 1, fz - wh, m['quay'])
    s.carve(x0 + 1, x1 - 1, y0 + 1, y1 - 1, fz - 1, fz - wh)
    ym = (y0 + y1) / 2.0
    for x in (x0, x1):                                                   # gable ends (one survives)
        if x == x1 and rng.random() < 0.5:
            continue
        for y in range(y0, y1 + 1):
            g = fz - wh - int(np.floor(d / 2.0 - abs(y - ym))) - 1
            s.mat[x, y, g:fz - wh] = m['quay']
    s.carve(x0 + w // 2, x0 + w // 2 + 1, y0, y0, fz - 1, fz - 3)       # door
    for xw in range(x0 + 2, x1 - 1, 3):
        s.carve(xw, xw, y1, y1, fz - 3, fz - 4)
    s.box(x1 - 2, x1 - 1, y1 - 2, y1 - 1, fz - 1, fz - wh - 5, m['rock'])  # chimney stack
    X, Y = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    inb = (X >= x0) & (X <= x1) & (Y >= y0) & (Y <= y1)
    wall = inb & ((X == x0) | (X == x1) | (Y == y0) | (Y == y1))
    keep_chim = (X >= x1 - 2) & (Y >= y1 - 2)
    ruin(s, wall & ~keep_chim, amp=4, seed=seed, scale=4.0, base=0.3, only_above=fz - 1)
    for k in range(int(rng.integers(1, 3))):                             # fallen rafter
        yy = int(rng.integers(y0 + 1, y1))
        s.box(x0 + 1, x1 - 1, yy, yy, fz - 1, fz - 1, m['timber'])


def drowned_town(s, m, L, H, rng, per_half=None):
    per_half = per_half or SPEC['drowned_houses_n']
    X, Y = L.X, L.Y
    ok = (L.west & L.inside & (H >= 60) & ~ndimage.binary_dilation(L.cathedral, iterations=6)
          & ~ndimage.binary_dilation(L.causeway, iterations=3) & ~ndimage.binary_dilation(L.land, iterations=4)
          & (L.d_ell > 10) & (X < 224))
    taken = np.zeros(X.shape, bool)
    houses = []
    for (ya, yb) in ((60, 205), (307, 452)):
        n = 0
        for _ in range(600):
            if n >= per_half:
                break
            w, d = int(rng.integers(8, 13)), int(rng.integers(7, 11))
            x0 = int(rng.integers(108, 224 - w)); y0 = int(rng.integers(ya, yb - d))
            fp = (slice(x0 - 1, x0 + w + 1), slice(y0 - 1, y0 + d + 1))
            if not ok[fp].all() or taken[x0 - 7:x0 + w + 7, y0 - 7:y0 + d + 7].any():
                continue
            drowned_house(s, m, x0, y0, w, d, int(rng.integers(1 << 30)), H)
            taken[x0:x0 + w, y0:y0 + d] = True
            houses.append((x0, y0, w, d))
            n += 1
    L.houses = houses
    return taken


def fen_and_banks_dressing(s, m, L, H, rng, extra_block=None):
    """Vegetation, lilies, reeds, wisps, gibbet, boat. Nothing in the spawn square, precinct, esplanade/tower
    zone, stairs, causeways or the cathedral footprint."""
    X, Y = L.X, L.Y
    west = L.west
    block = (L.precinct | L.esplanade | ndimage.binary_dilation(L.stairs, iterations=2)
             | ndimage.binary_dilation(L.causeway, iterations=2) | ndimage.binary_dilation(L.cathedral, iterations=2)
             | L.cottage | ndimage.binary_dilation(L.graveyard, iterations=3) | ndimage.binary_dilation(L.quay_edge, iterations=4)
             | (X < 2) | (Y < 2) | (Y > 509) | ~west)
    if extra_block is not None:
        block |= ndimage.binary_dilation(extra_block, iterations=3)
    sc = SPEC['script_constants']
    ddx = np.maximum(0, np.maximum(sc['platform_x'][0] - X, X - sc['platform_x'][1]))
    ddy = np.maximum(0, np.maximum(sc['platform_y'][0] - Y, Y - sc['platform_y'][1]))
    near_plat = np.hypot(ddx, ddy)
    dens = np.where(L.inside & (H >= 60), 0.55, 0.0)                                 # hummocks and shores
    dens = np.where(~L.inside, 0.35 + 0.4 * smooth((60 - X) / 40.0) + 0.3 * smooth((L.dy - 120) / 60.0), dens)
    dens = np.where(L.inside & (H < 60), 0.25, dens)                                 # natural slopes
    counts = {'cypress': 0, 'snag': 0, 'lilies': 0, 'reeds': 0, 'wisps': 0, 'bushes': 0}
    step = 9

    def try_tree(x, y, rng):
        if not (2 <= x <= 253 and 2 <= y <= 509):
            return
        if block[x - 2:x + 3, y - 2:y + 3].any() or rng.random() > dens[x, y]:
            return
        fz = int(H[x, y])
        if (s.mat[x, y, :fz] > 0).any() or (fz >= 63 and not L.inside[x, y]):
            return
        water = fz >= 63
        if water and rng.random() < 0.65:
            return                                                                     # fewer trees in open water
        hmax = 22 if not L.inside[x, y] else 20
        if near_plat[x, y] < 34:
            hmax = min(hmax, max(8, fz - 30))                                          # keep tops below z 30 near the platform
        if rng.random() < 0.78:
            hgt = int(rng.integers(12, hmax + 1)) if hmax > 12 else hmax
            pf = P.cypress(int(rng.integers(1 << 30)), m, height=hgt, crown_r=float(rng.uniform(3.8, 6.0)),
                           pads=int(rng.integers(2, 5)))
            counts['cypress'] += 1
        else:
            pf = P.snag(int(rng.integers(1 << 30)), m, height=int(rng.integers(7, min(hmax, 13) + 1)))
            counts['snag'] += 1
        plant(s, pf, x, y, fz)

    for gx in range(4, 256, step):
        for gy in range(4, 508, step):
            x = gx + int(rng.integers(-3, 4)); y = gy + int(rng.integers(-3, 4))
            try_tree(x, y, rng)
    # the grid above stops at y 502 while it starts at y 1, and the last rows sit under earlier crowns - infill
    # the south edge (only where there is a gap) until it matches the north edge's cover
    rng_s = np.random.default_rng(SEED + 404)
    for _ in range(3):
        for gx in range(3, 254, 5):
            for gy in (493, 499, 505):
                x = gx + int(rng_s.integers(-2, 3)); y = gy + int(rng_s.integers(-2, 3))
                if not (2 <= x <= 253 and 2 <= y <= 507) or block[x, y]:
                    continue
                fz = int(H[x, y])
                if (s.mat[x - 3:x + 4, y - 3:y + 4, max(fz - 22, 0):fz - 1] > 0).any():
                    continue                                                           # something already there
                try_tree(x, y, rng_s)
    # bushes on banks (low, frequent near the forest edge)
    for _ in range(900):
        x = int(rng.integers(4, 252)); y = int(rng.integers(4, 508))
        if block[x, y] or L.inside[x, y] or rng.random() > dens[x, y]:
            continue
        if (s.mat[x, y, :int(H[x, y])] > 0).any():
            continue
        plant(s, P.bush(int(rng.integers(1 << 30)), m, r=float(rng.uniform(1.3, 2.2))), x, y, int(H[x, y]))
        counts['bushes'] += 1
    # lilies on open water, reeds on hummock edges / shores, wisp lanterns on a few hummocks
    water = west & (H >= 63) & ~ndimage.binary_dilation(L.cathedral | L.causeway, iterations=1)
    for _ in range(1600):
        x = int(rng.integers(108, 254)); y = int(rng.integers(62, 450))
        if extra_block is not None and extra_block[x, y]:
            continue
        if water[x, y] and s.mat[x, y, 62] == 0 and rng.random() < 0.6:
            art.stamp(s, P.lily_patch(int(rng.integers(1 << 30)), m, r=float(rng.uniform(1.8, 3.6))), x, y, 63,
                      replace_air_only=True)
            counts['lilies'] += 1
    hum = west & L.inside & (H >= 60) & (H <= 61)
    edge = hum & ~ndimage.binary_erosion(hum, iterations=1)
    for (x, y) in np.argwhere(edge)[::5]:
        if block[x, y] or rng.random() < 0.5:
            continue
        plant(s, P.reeds(int(rng.integers(1 << 30)), m, n=int(rng.integers(4, 9))), int(x), int(y), int(H[x, y]))
        counts['reeds'] += 1
    lp = P.lantern_post(m, h=3)
    for (x, y) in np.argwhere(hum & ~block)[::97][:10]:
        art.stamp(s, lp, int(x), int(y), top_z(s, int(x), int(y)), replace_air_only=True)
        counts['wisps'] += 1
    # lychgates where the axis causeways leave the shore, boulders on the natural slopes
    for (yg, yd) in SPEC.get('lychgates', ((84, 1), (428, -1))):
        gz = int(H[250, yg])
        s.box(248, 249, yg - 1, yg + 1, gz - 1, gz - 9, m['stone_dk'])
        s.box(248, 255, yg - 1, yg + 1, gz - 10, gz - 10, m['trim'])
        for k in range(4):
            s.box(247 + k, 255, yg - 2, yg + 2, gz - 11 - k, gz - 11 - k, m['slate'])
        s.mat[255, yg, gz - 16] = m['trim']
        art.stamp(s, P.lantern_post(m, h=4), 246, yg + 3 * yd, gz, replace_air_only=True)
    rocky = west & L.inside & (H < 59) & (H > BANK - 2) & ~block
    for (x, y) in np.argwhere(rocky)[::211]:
        pf = P.boulder(int(rng.integers(1 << 30)), {'rubble': m['rock']}, r=float(rng.uniform(1.8, 3.4)))
        plant(s, pf, int(x), int(y), int(H[x, y]))
    # gibbet near the north quay corner (and its y-mirror), beached boat in the north fen
    for (gx, gy) in SPEC['gibbets']:
        g = P.gibbet(SEED + gy, m)
        ni, nj = g.a.shape[:2]
        north = P.Prefab(np.rot90(g.a, 3, axes=(0, 1)).copy(), origin=(g.origin[1], ni - 1 - g.origin[0]))
        south = P.Prefab(np.rot90(g.a, 1, axes=(0, 1)).copy(), origin=(nj - 1 - g.origin[1], g.origin[0]))
        plant(s, north, gx, gy, BANK)
        plant(s, south, gx, 512 - gy, BANK)
    bx, by = 196, 150
    art.stamp(s, P.rowboat(m, 9), bx, by, top_z(s, bx, by), replace_air_only=True)
    return counts


# ============================================================================================== build
EMBLEM = ['.....gg....',
          '....gg.....',
          '..ooooooo..',
          '.ooooooooo.',
          'ooyyoooyyoo',
          'ooyyoooyyoo',
          'ooooooooooo',
          'oyoyoyoyoyo',
          'ooyyyyyyyoo',
          '.ooooooooo.',
          '..ooooooo..']


def signature(s, m, L):
    """Map name / author tag painted on the ground in the bottom-right corner, the way community maps sign
    themselves (tradeoff, A Bridge Too Far, planeassault_halloween): light lettering with a dark drop shadow, read in
    the client's map view and in top-down previews. Only the tag's own patch is flattened and cleared (it lies in
    the forest outside the play space, so the one-sided change does not affect balance)."""
    from aosmap.pixelfont import text_mask, text_width
    sg = SPEC['signature']
    lines = sg['lines']
    masks = [text_mask([ln]) for ln in lines]
    tw = max(mk.shape[0] for mk in masks)
    ew = len(EMBLEM[0])
    bw, bh = tw + 4 + ew, max(len(lines) * 7 + (len(lines) - 1) * 3, len(EMBLEM))
    x1 = 511 - sg['margin']; y1 = 511 - sg['margin']
    x0 = x1 - bw + 1; y0 = y1 - bh + 1
    z = sg['z']
    px0, px1, py0, py1 = x0 - 5, min(x1 + 4, 510), y0 - 5, min(y1 + 4, 510)
    clear = sg.get('clear', True)
    for (qa, qb) in (((px0, px1),) if clear else ()):                     # flatten + clear the tag patch only
        s.mat[qa:qb + 1, py0:py1 + 1, :z] = 0
        sub = s.mat[qa:qb + 1, py0:py1 + 1, z:63]
        sub[sub == 0] = m['soil']
        s.mat[qa:qb + 1, py0:py1 + 1, z] = m['grass']
    text = np.zeros((bw, bh), bool)
    for li, mk in enumerate(masks):                                       # right-aligned against the emblem
        ox = tw - mk.shape[0]
        oy = li * 10 + (bh - (len(lines) * 7 + (len(lines) - 1) * 3)) // 2
        text[ox:ox + mk.shape[0], oy:oy + mk.shape[1]] |= mk
    paint = np.zeros((bw, bh), np.int32)
    paint[text] = m['sig_text']
    cmap = {'o': m['sig_orange'], 'g': m['sig_green'], 'y': m['sig_glow']}
    ex0 = tw + 4; ey0 = (bh - len(EMBLEM)) // 2
    for r, row in enumerate(EMBLEM):
        for c, ch in enumerate(row):
            if ch in cmap:
                paint[ex0 + c, ey0 + r] = cmap[ch]
    shadow = np.zeros((bw + 1, bh + 1), bool)
    shadow[1:, 1:] = paint > 0
    mode = sg.get('mode', 'ground')
    zp = z
    if mode == 'sky':                                                     # plate + tether stalk to the ground
        zp = sg['sky_z']
        s.mat[x0 - 3:x1 + 4, y0 - 3:y1 + 4, zp:zp + 2] = m['sig_plate']    # 2 thick: plain underside
        sx, sy = x1 + 3, y1 + 3                                           # tether stalk down to the first solid voxel
        zg = zp + 2
        while zg < 63 and s.mat[sx, sy, zg] == 0:
            s.mat[sx, sy, zg] = m['sig_plate']
            zg += 1
    for i in range(bw + 1):
        for j in range(bh + 1):
            x, y = x0 + i, y0 + j
            if i < bw and j < bh and paint[i, j]:
                if mode == 'raised':
                    s.mat[x, y, z - 1] = paint[i, j]
                else:
                    s.mat[x, y, zp] = paint[i, j]
            elif shadow[i, j]:
                s.mat[x, y, zp] = m['sig_shadow']


def mirror(s):
    s.mat[257:512] = s.mat[1:256][::-1]
    s.mat[256] = s.mat[255]


def prune_floating(s):
    """Remove components not face-connected to z >= 62 (ruin carving can orphan a lintel). Returns removed list."""
    solid = s.mat > 0
    solid[:, :, 63] = True
    lab, n = ndimage.label(solid, structure=P.FACE6)
    grounded = np.unique(lab[:, :, 62:][solid[:, :, 62:]])
    bad = ~np.isin(lab, grounded) & solid
    removed = int(bad.sum())
    comps = len(np.setdiff1d(np.unique(lab[bad]), [0]))
    s.mat[bad] = 0
    return {'components': comps, 'voxels': removed}


def build(stage='art'):
    L = Layout()
    s = Scene('drowned_cathedral', seed=SEED)
    m = materials(s)
    rng = np.random.default_rng(SEED + 100)
    H = terrain(L)
    ground(s, L, m, H)
    quay_stairs(s, m, L)
    causeways(s, m, L, H)
    cathedral(s, m, rng)
    counts = {}
    if stage == 'art':
        precinct(s, m, L, rng)
        for (cx, cy, w, d) in SPEC['cottages']:
            for yy in (cy, 512 - cy):
                cottage_ruin(s, m, cx, yy, w, d, SEED + cx * 7 + yy)
        quay_details(s, m, L, H, rng)
        town = drowned_town(s, m, L, H, rng)
        counts = fen_and_banks_dressing(s, m, L, H, rng, extra_block=town)
        counts['drowned_houses_west'] = len(L.houses)
    else:
        sc = SPEC['screen']
        s.box(sc['x'][0], sc['x'][1], sc['y'][0], sc['y'][1], BANK - 1, sc['top'], m['stone'])
    mirror(s)
    sub = s.mat[257:, :, :]
    sub[sub == m['banner_blue']] = m['banner_red']
    signature(s, m, L)
    s.markers['pruned'] = prune_floating(s)
    # painted fen bottom: murky teal with algae drifts
    X, Y = L.X, L.Y
    base = ramp(['#1e2e2b', '#2a403b', '#34503f'], fbm(X, Y, None, scale=26, octaves=3, seed=SEED + 70))
    alg = fbm(X, Y, None, scale=9, octaves=2, seed=SEED + 71)
    base = np.where((alg > 0.62)[..., None], base * 0.6 + hex_rgb('#4a6236') * 0.4, base)
    s.paint_bottom(np.clip(base, 0, 255).astype(np.uint8))
    s.markers['counts'] = counts
    s.markers['H'] = H
    return s, L


def metadata_txt(author='shywolf91 and AI'):
    """Map metadata only - no spawn or entity hooks. Spawns come from the game mode itself (stock babel_script: bases
    256 -+ 138 on y 256, random +-20 on the topmost voxel); the map is built around that square. Per the user's rule,
    spawn coordinates are not authored here - add them by hand after review if a server needs them."""
    from aosmap.meta import map_txt
    return map_txt(
        name='Drowned Cathedral', author=author, version='1.0',
        description='A gothic cathedral sunk in a fen at dusk. Babel: build from your quay, or race up the drowned '
                    'bell tower beneath the platform.',
        header='Generated by scenes/drowned_cathedral.py (seed %d). No spawn hooks: spawns use the game mode defaults.'
               % SEED,
        fog=FOG, extensions={'babel': True, 'water_damage': 0})


if __name__ == '__main__':
    from aosmap.vxl import write_vxl
    out = sys.argv[1] if len(sys.argv) > 1 else 'out/drowned_cathedral'
    stage = sys.argv[2] if len(sys.argv) > 2 else 'art'
    os.makedirs(out, exist_ok=True)
    s, L = build(stage)
    data = write_vxl(s.to_voxelmap())
    open(os.path.join(out, 'drowned_cathedral.vxl'), 'wb').write(data)
    open(os.path.join(out, 'drowned_cathedral.txt'), 'w').write(metadata_txt())
    json.dump({k: v for k, v in SPEC.items()}, open(os.path.join(out, 'spec.json'), 'w'), indent=1, default=list)
    print('written', len(data), 'bytes', s.markers['counts'], 'pruned', s.markers['pruned'])
