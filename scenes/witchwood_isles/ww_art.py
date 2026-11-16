"""Witchwood Isles — art pass on top of the graybox gameplay geometry.

Everything is authored on the west half (x <= 256) and mirrored x' = 512 - x. Colours are painted per voxel
(overrides) for designed surfaces, and shaded by material + coherent noise elsewhere. Noise uses folded x so
the mirror stays exact.
"""
import numpy as np
from scipy import ndimage

import ww_gen
from ww_gen import SPEC
from ww_core import W, D, fbm, seed_of, surface_mask

SEED = ww_gen.SEED

MAT_NAMES = [
    'air', 'seabed', 'lagoon_bed', 'sand', 'grass', 'spawn_floor', 'earth', 'stone_floor', 'mound', 'stair',
    'boardwalk', 'piling', 'cover_wall', 'trunk', 'foliage_purple', 'foliage_green', 'cottage_wall', 'roof',
    'pumpkin', 'standing_stone', 'path',
    # art additions
    'plaster', 'timber', 'slate', 'brick', 'window_lit', 'window_dark', 'dry_stone', 'lantern', 'iron', 'brew',
    'ember', 'leaf_litter', 'moss', 'autumn', 'pine', 'rope', 'gravestone', 'jack_face', 'stem', 'soil', 'cobble',
    'wet_sand', 'rock', 'deadwood', 'hay', 'cloth',
]
A = {n: i for i, n in enumerate(MAT_NAMES)}
MATS = {i: (n, (0, 0, 0)) for i, n in enumerate(MAT_NAMES)}

# (dark, light) ramps for noise-shaded materials
RAMP = {
    'seabed': ((22, 44, 54), (30, 56, 66)), 'lagoon_bed': ((40, 110, 88), (52, 132, 98)),
    'sand': ((146, 128, 92), (174, 156, 110)), 'wet_sand': ((112, 100, 76), (128, 114, 86)),
    'grass': ((50, 84, 46), (82, 114, 56)), 'spawn_floor': ((112, 106, 100), (130, 124, 116)),
    'earth': ((84, 64, 46), (102, 80, 58)), 'stone_floor': ((100, 98, 108), (124, 120, 128)),
    'mound': ((112, 108, 124), (140, 134, 150)), 'stair': ((150, 142, 120), (176, 166, 138)),
    'boardwalk': ((104, 76, 50), (136, 100, 66)), 'piling': ((62, 46, 34), (86, 64, 46)),
    'cover_wall': ((90, 88, 100), (110, 106, 118)), 'trunk': ((48, 38, 32), (72, 56, 42)),
    'foliage_purple': ((70, 46, 104), (118, 82, 150)), 'foliage_green': ((40, 74, 48), (66, 104, 60)),
    'cottage_wall': ((150, 136, 110), (172, 158, 128)), 'roof': ((56, 48, 76), (80, 70, 100)),
    'pumpkin': ((206, 100, 22), (236, 132, 38)), 'standing_stone': ((78, 78, 92), (108, 106, 118)),
    'path': ((112, 90, 66), (134, 108, 78)), 'plaster': ((164, 148, 120), (188, 172, 140)),
    'timber': ((52, 36, 28), (72, 50, 36)), 'slate': ((54, 46, 74), (78, 68, 98)),
    'brick': ((104, 58, 48), (130, 76, 60)), 'window_lit': ((236, 150, 58), (255, 186, 88)),
    'window_dark': ((28, 26, 38), (40, 36, 52)), 'dry_stone': ((92, 90, 98), (126, 122, 126)),
    'lantern': ((255, 186, 84), (255, 214, 120)), 'iron': ((30, 28, 34), (52, 50, 58)),
    'brew': ((86, 200, 104), (136, 236, 132)), 'ember': ((214, 84, 28), (250, 150, 56)),
    'leaf_litter': ((134, 70, 32), (172, 102, 44)), 'moss': ((84, 102, 74), (104, 122, 86)),
    'autumn': ((150, 64, 28), (206, 118, 40)), 'pine': ((28, 54, 50), (42, 74, 62)),
    'rope': ((146, 124, 88), (168, 146, 104)), 'gravestone': ((112, 112, 122), (144, 142, 148)),
    'jack_face': ((255, 206, 88), (255, 232, 140)), 'stem': ((58, 82, 38), (78, 102, 46)),
    'soil': ((70, 52, 38), (88, 66, 46)), 'cobble': ((104, 100, 98), (128, 122, 116)),
    'rock': ((84, 82, 90), (116, 112, 116)), 'deadwood': ((70, 64, 62), (96, 88, 82)),
    'hay': ((170, 140, 72), (196, 166, 92)), 'cloth': ((92, 62, 52), (116, 80, 64)),
}
GLOW = {'window_lit', 'lantern', 'brew', 'ember', 'jack_face'}


class Art:
    def __init__(self):
        S = SPEC
        solid, mat, H, info = ww_gen.build(props=False)
        # remap graybox material ids (same names, same order for 0..20)
        self.solid = solid
        self.mat = mat.astype(np.uint8)
        self.H = H
        self.info = info
        self.col = np.zeros((W, W, D, 3), np.uint8)
        self.ovr = np.zeros((W, W, D), bool)
        self.rng = np.random.RandomState(SEED + 7)
        self.ztop = 63 - H
        self.keep = np.zeros((W, W), bool)      # no-prop mask (routes, objectives, build zones)
        self._keepouts()

    # ------------------------------------------------------------- primitives
    def put(self, x, y, z, m, c=None):
        if not (0 <= x <= 256 and 0 <= y < W and 0 <= z < 63):
            return
        self.solid[x, y, z] = True
        self.mat[x, y, z] = A[m]
        if c is not None:
            self.col[x, y, z] = c
            self.ovr[x, y, z] = True
        else:
            self.ovr[x, y, z] = False

    def box(self, x0, x1, y0, y1, z0, z1, m):
        x0, x1 = max(x0, 0), min(x1, 256)
        self.solid[x0:x1 + 1, y0:y1 + 1, z0:z1 + 1] = True
        self.mat[x0:x1 + 1, y0:y1 + 1, z0:z1 + 1] = A[m]
        self.ovr[x0:x1 + 1, y0:y1 + 1, z0:z1 + 1] = False

    def paint(self, x, y, z, c, m=None):
        if self.solid[x, y, z]:
            self.col[x, y, z] = c
            self.ovr[x, y, z] = True
            if m:
                self.mat[x, y, z] = A[m]

    def top(self, x, y):
        """current topmost solid z of a column"""
        return int(np.argmax(self.solid[x, y]))

    def ground(self, x, y):
        return int(self.ztop[x, y])

    def _keepouts(self):
        S = SPEC
        k = self.keep
        k[98 - 3:138 + 4, 236 - 3:276 + 4] = True                          # spawn box
        k[186:257, 228:285] = True                                         # central island (handled by hand)
        k[150:200, 225:262] = True                                         # crossings + landing
        k[160:200, 226:234] = True
        mo = S['mound']
        k[mo['x'][0] - 2:mo['x'][1] + 3, mo['north_stair_y'][0] - 2:mo['south_stair_y'][1] + 3] = True

    # ------------------------------------------------------------- terrain + sea colours
    def terrain_colours(self):
        S = SPEC
        land = self.info['land']
        H = self.H
        nb = fbm(seed_of('grassbig', SEED), (W, W), 40, 3)
        ns = fbm(seed_of('grasssmall', SEED), (W, W), 6, 2)
        for x in range(0, 257):
            col_land = land[x]
            for y in np.nonzero(col_land)[0]:
                z = self.ztop[x, y]
                m = self.mat[x, y, z]
                if m == A['grass']:
                    t = 0.55 * nb[x, y] + 0.45 * ns[x, y]
                    hb = min(1.0, H[x, y] / 22.0)
                    dark, light = np.array((44, 78, 44)), np.array((86, 116, 58))
                    c = dark + (light - dark) * np.clip(t * 0.8 + hb * 0.35, 0, 1)
                    if nb[x, y] > 0.62 and ns[x, y] > 0.45:          # dry olive patches
                        c = c * 0.7 + np.array((120, 112, 64)) * 0.3
                    self.col[x, y, z] = c.astype(np.uint8)
                    self.ovr[x, y, z] = True
                elif m == A['sand'] and H[x, y] <= 1:
                    self.mat[x, y, z] = A['wet_sand']

    def seabed(self):
        """Seabed (= water colour in the clients): deep sea → lighter shallows near land → a soft-edged
        glowing lagoon round the centre, in 7 discrete bands so it reads as voxels, not a hard ellipse."""
        land = self.info['land']
        dist = ndimage.distance_transform_edt(~land)
        xs = np.arange(W)[:, None]
        ys = np.arange(W)[None, :]
        lg = SPEC['lagoon']
        r = np.sqrt(((xs - lg['cx']) / lg['rx']) ** 2 + ((ys - lg['cy']) / lg['ry']) ** 2)
        n = fbm(seed_of('sea', SEED), (W, W), 20, 2)
        deep = np.array((22, 46, 58), float)
        shallow = np.array((34, 78, 82), float)
        glow = np.array((44, 118, 92), float)
        w = (fbm(seed_of('seawarp', SEED), (W, W), 28, 2) - 0.5) * 0.22
        t_sh = np.clip(1 - dist / 16.0, 0, 1) ** 1.5
        t_lg = np.clip((1.3 - (r + w)) / 0.9, 0, 1) ** 1.3 * 0.8
        t_lg = np.round(t_lg * 12) / 12          # fine steps, warped edges: no target rings
        t_sh = np.round(t_sh * 8) / 8
        c = deep[None, None] * (1 - t_sh[..., None]) + shallow[None, None] * t_sh[..., None]
        c = c * (1 - t_lg[..., None]) + glow[None, None] * t_lg[..., None]
        c *= (0.94 + 0.12 * n)[..., None]
        for x in range(0, 257):
            self.col[x, :, 63] = c[x].clip(0, 255).astype(np.uint8)
            self.ovr[x, :, 63] = True

    # ------------------------------------------------------------- props: buildings
    def witch_house(self, x0, x1, y0, y1, floor_z, wall_top, roof_steps, door='west', chimney_y=None, lit=0.6,
                    jetty=True):
        """Solid crooked half-timbered house (solid core so it also blocks sightlines)."""
        mid = (floor_z + wall_top) // 2
        # plinth + core
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                g = self.ground(x, y)
                for z in range(floor_z + 1, g + 1):
                    if not self.solid[x, y, z]:
                        self.put(x, y, z, 'dry_stone')
                for z in range(wall_top, floor_z + 1):
                    self.put(x, y, z, 'plaster')
        if jetty:
            for x in (x0 - 1, x1 + 1):
                for y in range(y0, y1 + 1):
                    for z in range(wall_top, mid + 1):
                        self.put(x, y, z, 'plaster')
        jx0 = x0 - 1 if jetty else x0
        jx1 = x1 + 1 if jetty else x1
        # facade paint: stone base, timber frame, plaster
        for z in range(wall_top, floor_z + 1):
            upper = z <= mid
            xa, xb = (jx0, jx1) if upper else (x0, x1)
            for x in range(xa, xb + 1):
                for y in range(y0, y1 + 1):
                    if not (x in (xa, xb) or y in (y0, y1)):
                        continue
                    if z >= floor_z - 1:
                        self.paint(x, y, z, None or self._stone(x, y, z), 'dry_stone')
                        continue
                    along = y if x in (xa, xb) else x
                    lo = y0 if x in (xa, xb) else xa
                    hi = y1 if x in (xa, xb) else xb
                    beam = z in (wall_top, mid, mid + 1) or (along - lo) % 5 == 0 or along == hi
                    if not beam and upper and ((along - lo) % 5 in (1, 4)) and ((z - wall_top) % 3 == 1):
                        beam = True       # diagonal brace hints
                    if beam:
                        self.paint(x, y, z, (58 + (z % 2) * 6, 40, 30), 'timber')
                    else:
                        self.paint(x, y, z, self._plaster(x, y, z), 'plaster')
        # windows: recessed 1, lit or dark, on both long faces, both storeys
        rng = self.rng
        for face_x, inner in ((jx0, 1), (jx1, -1)):
            for (zt, xa) in ((wall_top + 1, face_x), (mid + 2, face_x + (inner if jetty else 0))):
                for yy in range(y0 + 2, y1 - 1, 5):
                    if door == 'west' and face_x == jx0 and zt == mid + 2 and abs(yy - (y0 + y1) // 2) < 7:
                        continue
                    litc = (246, 168, 70) if rng.rand() < lit else (36, 32, 46)
                    for dy in (1, 2):
                        for dz in (0, 1):
                            if self.solid[xa, yy + dy, zt + dz]:
                                self.solid[xa, yy + dy, zt + dz] = False
                                self.ovr[xa, yy + dy, zt + dz] = False
                                self.paint(xa + inner, yy + dy, zt + dz, litc,
                                           'window_lit' if litc[0] > 100 else 'window_dark')
                    # sill
                    for dy in (0, 1, 2, 3):
                        if self.solid[xa, yy + dy, zt + 2]:
                            self.paint(xa, yy + dy, zt + 2, (50, 36, 28), 'timber')
        # door (recessed) on the chosen face
        if door == 'west':
            yc = (y0 + y1) // 2
            for dy in (0, 1):
                for z in range(floor_z - 3, floor_z):
                    self.solid[x0, yc + dy, z] = False
                    self.ovr[x0, yc + dy, z] = False
                    self.paint(x0 + 1, yc + dy, z, (64, 42, 30), 'timber')
            # wall lantern beside the door
            self.put(x0 - 1, yc - 2, floor_z - 4, 'lantern', (255, 196, 96))
        elif door == 'south':
            xc = (x0 + x1) // 2
            for dx in (0, 1):
                for z in range(floor_z - 3, floor_z):
                    self.solid[xc + dx, y1, z] = False
                    self.ovr[xc + dx, y1, z] = False
                    self.paint(xc + dx, y1 - 1, z, (64, 42, 30), 'timber')
            self.put(xc - 2, y1 + 1, floor_z - 4, 'lantern', (255, 196, 96))
        # steep gable roof along y with a sagging ridge
        rx0, rx1 = jx0 - 1, jx1 + 1
        ylen = y1 - y0
        top_layer = 0
        for j in range(roof_steps):
            inset = j // 2
            xa, xb = rx0 + inset, rx1 - inset
            if xa > xb:
                break
            z = wall_top - 1 - j
            for x in range(xa, xb + 1):
                for y in range(y0 - 1, y1 + 2):
                    if j >= roof_steps - 2 and abs(y - (y0 + y1) / 2) < ylen / 6:
                        continue      # sag
                    edge = x in (xa, xb)
                    c = self._slate(x, y, z, edge)
                    self.put(x, y, z, 'slate', c)
            top_layer = z
        # chimney
        if chimney_y is not None:
            cx = x1 - 1
            for z in range(top_layer - 3, wall_top):
                for dx in (0, 1):
                    for dy in (0, 1):
                        sh = 1 if z <= top_layer - 2 else 0
                        self.put(cx + dx + sh, chimney_y + dy, z, 'brick', self._brick(cx + dx, chimney_y + dy, z))
            # connect the crooked top step (face contact on the shifted column)
            self.put(cx + 1, chimney_y, top_layer - 1, 'brick')
            self.put(cx + 1, chimney_y + 1, top_layer - 1, 'brick')
            for dx in (0, 1):
                for dy in (0, 1):
                    self.put(cx + dx + 1, chimney_y + dy, top_layer - 4, 'iron', (40, 36, 40))

    def _stone(self, x, y, z):
        h = (x * 7 + y * 13 + (z // 2) * 5 + ((y + (z // 2) * 2) // 3) * 11) % 5
        b = 98 + h * 6
        return (b, b - 2, b + 4)

    def _plaster(self, x, y, z):
        h = ((x * 3 + y * 5 + z * 7) % 7)
        return (170 + h * 2, 154 + h * 2, 126 + h)

    def _slate(self, x, y, z, edge):
        row = (z % 2)
        h = ((y * 5 + x * 3) // 2) % 3
        base = np.array((60, 50, 80)) + row * 8 + h * 4
        if edge:
            base = base - 12
        return tuple(int(v) for v in base)

    def _brick(self, x, y, z):
        return (112 + ((x + y + z) % 3) * 8, 62, 50) if z % 2 else (98, 56, 46)

    # ------------------------------------------------------------- props: trees
    def witch_tree(self, cx, cy, top_z, trunk_w, limbs, clusters_r, cluster_h, lean=(1, 0), foliage='foliage_purple',
                   moss=0.025, lantern=False, max_x=None):
        g = max(self.ground(x, y) for x in range(cx - trunk_w // 2 - 1, cx + trunk_w // 2 + 2)
                for y in range(cy - trunk_w // 2 - 1, cy + trunk_w // 2 + 2))
        # roots sitting on the ground
        for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            L = 2 + self.rng.randint(0, 3)
            for i in range(trunk_w // 2 + 1, trunk_w // 2 + 1 + L):
                x, y = cx + dx * i, cy + dy * i
                for w in range(-(1 if i < trunk_w // 2 + L else 0), 1):
                    xx, yy = x + (w if dy else 0), y + (w if dx else 0)
                    gz = self.ground(xx, yy)
                    self.put(xx, yy, gz - 1, 'trunk')
        # trunk with lean and taper
        ox = oy = 0
        w = trunk_w
        height = g - top_z
        for k, z in enumerate(range(g, top_z - 1, -1)):
            if k > 0 and k % 6 == 0:
                ox += lean[0]
                oy += lean[1]
            if k > height * 0.6:
                w = max(2, trunk_w - 1)
            xa = cx + ox - w // 2
            ya = cy + oy - w // 2
            for x in range(xa, xa + w):
                for y in range(ya, ya + w):
                    self.put(x, y, z, 'trunk')
        tx, ty = cx + ox, cy + oy
        ends = [(tx, ty, top_z)]
        # limbs (2x2 staircase paths)
        for (dx, dy, length, rise) in limbs:
            x, y, z = tx, ty, top_z
            for i in range(length):
                if dx and (not dy or i % 2 == 0):
                    x += dx
                elif dy:
                    y += dy
                if i % rise == rise - 1:
                    z -= 1
                for ax in (0, 1):
                    for ay in (0, 1):
                        self.put(x + ax, y + ay, z, 'trunk')
                        self.put(x + ax, y + ay, z + 1, 'trunk')
            ends.append((x, y, z))
        # canopy clusters
        f_dark = np.array(RAMP[foliage][0], float)
        f_light = np.array(RAMP[foliage][1], float)
        cells = []
        for (ex, ey, ez) in ends:
            r = clusters_r + self.rng.randint(-1, 2)
            h = cluster_h
            czc = ez - 1
            for x in range(ex - r, ex + r + 2):
                if max_x is not None and x > max_x:
                    continue
                for y in range(ey - r, ey + r + 2):
                    for z in range(czc - h, czc + h + 1):
                        d = ((x - ex - 0.5) / r) ** 2 + ((y - ey - 0.5) / r) ** 2 + ((z - czc) / h) ** 2
                        if d <= 1.0 and 0 <= z < 62 and not self.solid[x, y, z]:
                            t = np.clip(0.5 + (czc - z) / (2.0 * h) + 0.25 * (((x * 7 + y * 3 + z) % 5) / 4 - 0.5), 0, 1)
                            c = f_dark + (f_light - f_dark) * t
                            self.put(x, y, z, foliage, tuple(int(v) for v in c))
                            cells.append((x, y, z))
        # hanging moss strands under the canopy
        for (x, y, z) in cells:
            if self.rng.rand() < moss and z + 1 < 60 and not self.solid[x, y, z + 1]:
                L = 2 + self.rng.randint(0, 3)
                for i in range(1, L + 1):
                    if self.solid[x, y, z + i] or z + i + 3 >= self.ground(x, y):
                        break
                    self.put(x, y, z + i, 'moss', (96 - i * 4, 112 - i * 4, 84 - i * 3))
        if lantern and len(ends) > 1:
            ex, ey, ez = ends[1]
            # chain hangs from the limb underside
            zc = ez + 2
            for i in range(3):
                if self.solid[ex, ey, zc + i]:
                    continue
                self.put(ex, ey, zc + i, 'iron', (40, 38, 44))
            self.put(ex, ey, zc + 3, 'lantern', (255, 200, 100))

    def pine(self, cx, cy, height):
        g = self.ground(cx, cy)
        for z in range(g, g - height, -1):
            self.put(cx, cy, z, 'trunk')
            self.put(cx + 1, cy, z, 'trunk')
            self.put(cx, cy + 1, z, 'trunk')
            self.put(cx + 1, cy + 1, z, 'trunk')
        zt = g - height
        tiers = 4
        for t in range(tiers):
            rr = 4 - t
            zb = g - 4 - t * 3
            for dz in range(3):
                r = rr - dz * 0.6
                for x in range(cx - 4, cx + 6):
                    for y in range(cy - 4, cy + 6):
                        if (x - cx - 0.5) ** 2 + (y - cy - 0.5) ** 2 <= r * r and not self.solid[x, y, zb - dz]:
                            shade = 0.85 + 0.15 * dz
                            c = np.array(RAMP['pine'][0]) * (1 - dz / 3) + np.array(RAMP['pine'][1]) * dz / 3
                            self.put(x, y, zb - dz, 'pine', tuple(int(v * shade) for v in c))
        for z in range(zt, zt - 3, -1):          # spire continues straight up from the trunk top
            self.put(cx, cy, z, 'pine')

    def dead_tree(self, cx, cy, height, branches=3):
        g = self.ground(cx, cy)
        for z in range(g, g - height, -1):
            for dx in (0, 1):
                for dy in (0, 1):
                    self.put(cx + dx, cy + dy, z, 'deadwood')
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        self.rng.shuffle(dirs)
        for b in range(branches):
            dx, dy = dirs[b % 4]
            z = g - height + 2 + b * 2
            x, y = cx + (1 if dx > 0 else 0), cy + (1 if dy > 0 else 0)
            for i in range(3 + self.rng.randint(0, 3)):
                x += dx
                y += dy
                self.put(x, y, z, 'deadwood')
                z -= 1
                self.put(x, y, z, 'deadwood')

    def autumn_tree(self, cx, cy, height):
        g = self.ground(cx, cy)
        for z in range(g, g - height, -1):
            for dx in (0, 1):
                for dy in (0, 1):
                    self.put(cx + dx, cy + dy, z, 'trunk')
        zc = g - height - 1
        r, h = 4, 3
        for x in range(cx - r, cx + r + 2):
            for y in range(cy - r, cy + r + 2):
                for z in range(zc - h, zc + h + 1):
                    d = ((x - cx - 0.5) / r) ** 2 + ((y - cy - 0.5) / r) ** 2 + ((z - zc) / h) ** 2
                    if d <= 1 and not self.solid[x, y, z]:
                        t = np.clip(0.5 + (zc - z) / (2.0 * h), 0, 1)
                        c = np.array((150, 62, 28)) + (np.array((214, 128, 42)) - np.array((150, 62, 28))) * t
                        if (x * 5 + y * 3 + z * 7) % 11 == 0:
                            c = np.array((196, 156, 52))
                        self.put(x, y, z, 'autumn', tuple(int(v) for v in c))
        # leaf litter ring
        for x in range(cx - 5, cx + 7):
            for y in range(cy - 5, cy + 7):
                if (x - cx - 0.5) ** 2 + (y - cy - 0.5) ** 2 <= 30 and self.rng.rand() < 0.5:
                    z = self.top(x, y)
                    if self.mat[x, y, z] == A['grass'] and z == self.ground(x, y):
                        self.paint(x, y, z, (150 + self.rng.randint(0, 30), 78, 34), 'leaf_litter')

    # ------------------------------------------------------------- props: small things
    def lantern_post(self, x, y, h=3):
        g = self.top(x, y)
        for z in range(g - 1, g - 1 - h, -1):
            self.put(x, y, z, 'iron', (38, 36, 42))
        self.put(x, y, g - 1 - h, 'lantern', (255, 198, 98))
        self.put(x, y, g - 2 - h, 'iron', (30, 28, 34))

    def jack(self, cx, cy, r=3, face=(0, 1)):
        g = self.ground(cx, cy)
        rz = r * 0.75
        zc = g - rz
        for x in range(cx - r, cx + r + 1):
            for y in range(cy - r, cy + r + 1):
                for z in range(int(zc - rz) - 1, g + 1):
                    d = ((x - cx) / r) ** 2 + ((y - cy) / r) ** 2 + ((z - zc) / rz) ** 2
                    if d <= 1.05 and not self.solid[x, y, z]:
                        ang = np.arctan2(y - cy, x - cx)
                        rib = int(((ang + np.pi) / (2 * np.pi)) * 10) % 2
                        c = (212, 104, 24) if rib else (232, 130, 36)
                        self.put(x, y, z, 'pumpkin', c)
        ztop = int(zc - rz)
        for z in range(ztop - 2, ztop + 1):
            if not self.solid[cx, cy, z]:
                self.put(cx, cy, z, 'stem', (66, 90, 40))
        # carved glowing face on the facing side (paint only)
        fx, fy = face
        pts = [(-1, -1), (1, -1), (0, 0), (-2, 1), (-1, 2), (0, 2), (1, 2), (2, 1)]   # eyes, nose, grin
        for (u, v) in pts:
            if fx == 0:
                x, y = cx + u, cy + fy * r
                while not self.solid[x, y, int(zc) + v] and abs(y - cy) > 0:
                    y -= fy
                self.paint(x, y, int(zc) + v, (255, 214, 96), 'jack_face')
            else:
                x, y = cx + fx * r, cy + u
                while not self.solid[x, y, int(zc) + v] and abs(x - cx) > 0:
                    x -= fx
                self.paint(x, y, int(zc) + v, (255, 214, 96), 'jack_face')

    def small_pumpkin(self, x, y):
        g = self.ground(x, y)
        if self.top(x, y) != g or self.top(x + 1, y) != g or self.top(x, y + 1) != g or self.top(x + 1, y + 1) != g:
            return False
        for dx in (0, 1):
            for dy in (0, 1):
                self.put(x + dx, y + dy, g - 1, 'pumpkin', (224, 120, 30) if (dx + dy) % 2 else (210, 104, 24))
        self.put(x, y, g - 2, 'stem', (70, 92, 42))
        return True

    def gravestone(self, x, y, kind=0):
        g = self.ground(x, y)
        if kind == 0:   # rounded slab 2 wide (y)
            for dy in (0, 1):
                for z in range(g - 1, g - 3, -1):
                    self.put(x, y + dy, z, 'gravestone')
            self.put(x, y, g - 3, 'gravestone')
            self.put(x, y + 1, g - 3, 'gravestone')
            self.paint(x, y, g - 3, (156, 154, 160))
        else:           # cross
            for z in range(g - 1, g - 5, -1):
                self.put(x, y, z, 'gravestone')
            self.put(x, y - 1, g - 3, 'gravestone')
            self.put(x, y + 1, g - 3, 'gravestone')

    def boulder(self, cx, cy, r):
        g = self.ground(cx, cy)
        for x in range(cx - r, cx + r + 1):
            for y in range(cy - r, cy + r + 1):
                gx = self.ground(x, y)
                zs = [z for z in range(g - r, gx + 1)
                      if ((x - cx) / r) ** 2 + ((y - cy) / r) ** 2 + ((z - g) / (r * 0.8)) ** 2 <= 1.0]
                if not zs:
                    continue
                for z in range(min(zs), gx + 1):          # fill down to the ground: never floating
                    if not self.solid[x, y, z]:
                        self.put(x, y, z, 'rock')

    # ------------------------------------------------------------- big pieces
    def spawn_green(self):
        """Witch's village green: cobbled square, painted rune ring, low dry-stone wall with gates, lanterns."""
        bx, by = 118, 256
        sp = SPEC['spawn_plateau']
        z = 63 - sp['H']
        for x in range(sp['x'][0], sp['x'][1] + 1):
            for y in range(sp['y'][0], sp['y'][1] + 1):
                if self.ztop[x, y] != z or self.top(x, y) != z:
                    continue
                d = np.hypot(x - bx, y - by)
                cell = ((x // 2) * 31 + (y // 2) * 17 + ((y // 2) % 2) * 7) % 5
                c = np.array((112, 104, 96)) + cell * 5
                edge = min(x - sp['x'][0], sp['x'][1] - x, y - sp['y'][0], sp['y'][1] - y)
                if edge < 4 and ((x * 7 + y * 11) % 5) < 2:
                    c = c * 0.7 + np.array((76, 100, 62)) * 0.3      # moss creeping in at the edges
                if (x % 2 == 0) and (y % 2 == 0):
                    c = c - 10            # mortar dots: low contrast, not stripes
                if 8.5 <= d <= 10.5:
                    c = np.array((84, 74, 104))      # rune ring
                    ang = (np.degrees(np.arctan2(y - by, x - bx)) + 360) % 45
                    if ang < 6:
                        c = np.array((214, 128, 52))   # rune marks
                elif d < 3.5:
                    c = np.array((92, 80, 112))
                self.paint(x, y, z, tuple(int(v) for v in c), 'cobble')
        # low wall (2 high) round the green, outside the stock spawn box, with gates
        wz = z - 1
        gates = {'n': range(110, 127), 's': range(110, 127), 'w': range(248, 265)}
        for x in range(93, 140):
            for y in (232, 280):
                if x in gates['n']:
                    continue
                self._drywall(x, y, wz)
        for y in range(232, 281):
            if y in gates['w']:
                continue
            self._drywall(93, y, wz)
        # lantern posts at the gates (on the wall line, outside the box)
        for (x, y) in ((109, 232), (127, 232), (109, 280), (127, 280), (93, 247), (93, 265)):
            self.lantern_post(x, y, 2)

    def _drywall(self, x, y, wz):
        g = self.ground(x, y)
        for z in range(g - 1, wz - 2, -1):
            self.put(x, y, z, 'dry_stone', self._stone(x, y, z))
        self.paint(x, y, wz - 1, (132, 128, 128), 'dry_stone')    # cap stone

    def screen_houses(self):
        """The two staggered spawn screens become crooked witch houses (same footprint role as walls A/B)."""
        # house A (north), house B (south): solid, roofs reach z ~26 so they also block high lines
        self.witch_house(141, 146, 224, 256, floor_z=48, wall_top=36, roof_steps=10, door='west', chimney_y=230)
        self.witch_house(151, 156, 256, 288, floor_z=48, wall_top=36, roof_steps=10, door='west', chimney_y=280)

    def boardwalks(self):
        S = SPEC
        land = self.info['land']
        for key in ('boardwalk', 'footbridge'):
            b = S[key]
            z = b['deck_z']
            y0, y1 = b['y']
            xs = []
            for x in range(b['x'][0], b['x'][1] + 1):
                over = [y for y in range(y0, y1 + 1) if not (land[x, y] and self.ztop[x, y] <= z)]
                if not over:
                    continue
                xs.append(x)
                for y in range(y0, y1 + 1):
                    if land[x, y] and self.ztop[x, y] <= z:
                        continue
                    shade = 112 + ((x * 7) % 3) * 9 + (10 if y in (y0, y1) else 0)
                    self.put(x, y, z, 'boardwalk', (shade, int(shade * 0.73), int(shade * 0.48)))
            x0, x1 = min(xs), max(xs)
            wide = key == 'boardwalk'
            # posts (down to seabed) + rail posts above deck + rope rail with an opening mid-span
            for x in range(x0, x1 + 1):
                for y in (y0, y1):
                    is_post = (x - x0) % 4 == 0 or x == x1
                    if is_post:
                        if not land[x, y]:
                            for zz in range(z + 1, 63):
                                self.put(x, y, zz, 'piling', (70, 52, 38))
                        for zz in range(z - 1, z - 4, -1):
                            self.put(x, y, zz, 'timber', (66, 46, 32))
                        if (x - x0) % 8 == 0 or x == x1:
                            self.put(x, y, z - 4, 'lantern', (255, 196, 96))
                    mid = (x0 + x1) // 2
                    gap = wide and abs(x - mid) <= 1
                    if not is_post and not gap:
                        self.put(x, y, z - 3, 'rope', (150, 128, 90))

    def pilings(self):
        pl = SPEC['pilings']
        h = pl['size'] // 2
        for (px, py) in pl['centres']:
            for x in range(px - h, px + h + 1):
                for y in range(py - h, py + h + 1):
                    for z in range(pl['top_z'], 63):
                        ring = (z - pl['top_z']) % 3 == 2
                        c = (60, 44, 32) if ring else (82 + ((x + y) % 2) * 6, 62, 44)
                        if z == pl['top_z']:
                            c = (92, 104, 70)          # mossy top
                        self.put(x, y, z, 'piling', c)

    def mound_art(self):
        S = SPEC
        mo = S['mound']
        x0, x1 = mo['x']
        y0, y1 = mo['y']
        tz = mo['top_z']
        floor_z = 63 - S['central']['H']
        ny0, ny1 = mo['north_stair_y']
        sy0, sy1 = mo['south_stair_y']
        # ashlar faces: courses 2 high, blocks 4 long, staggered; moss streaks from the top
        for x in range(x0, x1 + 1):
            for y in range(ny0, sy1 + 1):
                for z in range(self.top(x, y), floor_z + 1):
                    if not self.solid[x, y, z]:
                        continue
                    course = z // 2
                    along = y if x in (x0, x1) else x
                    joint = (along + (course % 2) * 2) % 4 == 0
                    seam = z % 2 == 0
                    b = 128 + ((along // 4 + course) * 7) % 3 * 6
                    c = np.array((b, b - 4, b + 10), float)
                    if joint or seam:
                        c *= 0.86
                    mossy = ((x * 13 + y * 7) % 9 == 0) and (z - self.top(x, y)) < 6
                    if mossy:
                        c = c * 0.6 + np.array((80, 104, 70)) * 0.4
                    self.paint(x, y, z, tuple(int(v) for v in c))
        # top: flagstones + painted crescent (decoration only)
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                cell = ((x // 3) * 5 + (y // 3) * 3) % 4
                c = (136 + cell * 5, 132 + cell * 5, 146 + cell * 4)
                if x % 3 == 0 or y % 3 == 0:
                    c = (124, 120, 132)
                self.paint(x, y, tz, c)
        # stairs: light treads, darker risers handled by side shading; rail caps
        for x in range(x0, x1 + 1):
            for y in list(range(ny0, ny1 + 1)) + list(range(sy0, sy1 + 1)):
                zt = self.top(x, y)
                if y in (ny0, sy1):
                    self.paint(x, y, zt, (100, 96, 108))
                else:
                    self.paint(x, y, zt, (178, 168, 140))
        # relief on the enemy-facing (east) face: a pale crescent moon painted into the ashlar
        cy_, cz_ = (y0 + y1) / 2, (tz + floor_z) / 2
        for y in range(y0, y1 + 1):
            for z in range(tz + 1, floor_z):
                r1 = np.hypot(y - cy_, (z - cz_) * 1.4)
                r2 = np.hypot(y - cy_ - 3, (z - cz_ + 1) * 1.4)
                if r1 <= 7 and r2 > 6:
                    self.paint(x1, y, z, (200, 196, 176))
        # lanterns at the stair feet on the apron
        for y in (ny0 - 1, sy1 + 1):
            self.lantern_post(x0 - 2, y, 3)

    def central_floor(self):
        """Flagstones with moss in the joints, standing-stone ellipse, trilithon gate, central cauldron."""
        S = SPEC
        central = self.info['central']
        fz = 63 - S['central']['H']
        nm = fbm(seed_of('moss', SEED), (W, W), 10, 2)
        for x in range(186, 257):
            for y in range(226, 287):
                if not central[x, y]:
                    continue
                z = self.top(x, y)
                if z != self.ztop[x, y]:
                    continue
                m = self.mat[x, y, z]
                if m not in (A['stone_floor'],):
                    continue
                joint = (x % 4 == 0) or ((y + (x // 4) % 2 * 2) % 4 == 0)
                cell = ((x // 4) * 7 + (y // 4) * 11) % 4
                c = np.array((106 + cell * 5, 104 + cell * 5, 114 + cell * 4), float)
                if joint:
                    c *= 0.88
                    if nm[x, y] > 0.55:
                        c = c * 0.5 + np.array((72, 98, 62)) * 0.5
                d = np.hypot((x - 256) / 1.0, (y - 256) / 1.0)
                if 9.5 <= d <= 11:
                    c = np.array((88, 80, 104))
                self.paint(x, y, z, tuple(int(v) for v in c))
        # standing stones on an ellipse round the centre (rx 30, ry 17), west half + axis
        for ang in (90, 125, 152, 208, 235, 270):
            a = np.radians(ang)
            sx = int(round(256 + 30 * np.cos(a))) - (1 if ang in (90, 270) else 0)   # axis stones straddle x 256
            sy = int(round(256 + 17 * np.sin(a)))
            hgt = 7 + (ang % 3)
            self._menhir(sx, sy, hgt, fz)
        # trilithon gate facing the mound (west)
        for sy in (250, 260):
            self._menhir(225, sy, 8, fz, w=2)
        for y in range(249, 263):
            for x in (225, 226):
                self.put(x, y, fz - 9, 'standing_stone', (98, 96, 110))
        # cauldron at the centre (x 256 is the axis; build x <= 256, the mirror completes it)
        self._cauldron(256, 256, fz)

    def _menhir(self, cx, cy, h, fz, w=3):
        for k in range(h):
            z = fz - 1 - k
            ww = w if k < h - 2 else max(1, w - 1)
            for x in range(cx, cx + ww):
                for y in range(cy, cy + 2):
                    if x > 256:
                        continue
                    shade = 92 + ((k * 5 + x + y) % 3) * 7
                    c = (shade, shade, shade + 12)
                    if k >= h - 2 and (x + y) % 2 == 0:
                        c = (88, 106, 76)    # moss cap
                    self.put(x, y, z, 'standing_stone', c)

    def _cauldron(self, cx, cy, fz):
        prof = [(fz - 1, 3, False), (fz - 2, 4, False), (fz - 3, 5, False), (fz - 4, 5, 'brew'),
                (fz - 5, 5, True), (fz - 6, 6, True)]
        for (z, r, hollow) in prof:
            for x in range(cx - r - 1, cx + 1):
                for y in range(cy - r - 1, cy + r + 2):
                    d = np.hypot(x - cx, y - cy)
                    if d > r + 0.3:
                        continue
                    if hollow is True and d < r - (1.7 if r == 6 else 0.7):
                        continue          # lip overlaps the wall below so it is face-connected
                    if hollow == 'brew' and d < r - 0.7:
                        c = (110, 226, 120) if (x + y) % 3 else (160, 246, 150)
                        self.put(x, y, z, 'brew', c)
                        continue
                    sh = 34 + int(10 * (1 - d / (r + 1)))
                    self.put(x, y, z, 'iron', (sh, sh - 2, sh + 6))
        # ring of fire logs with embers round the base
        for x in range(cx - 8, cx + 1):
            for y in range(cy - 8, cy + 9):
                d = np.hypot(x - cx, y - cy)
                if 6 <= d <= 7.4 and not self.solid[x, y, fz - 1]:
                    ember = (x * 3 + y * 5) % 4 == 0
                    self.put(x, y, fz - 1, 'ember' if ember else 'timber',
                             (236, 120, 40) if ember else (62, 44, 32))

    def cottage(self):
        co = SPEC['cottage']
        x0, x1 = co['x']
        y0, y1 = co['y']
        fz = int(np.min(self.ztop[x0:x1 + 1, y0:y1 + 1]))
        self.witch_house(x0, x1, y0, y1, floor_z=fz, wall_top=fz - 7, roof_steps=9, door='south',
                         chimney_y=y0 + 2, lit=0.8, jetty=False)
        # picket fence garden to the south with a pumpkin row
        for x in range(x0 - 2, x1 + 3):
            for y in (y1 + 9,):
                if 118 <= x <= 122:
                    continue          # garden gate on the path
                g = self.ground(x, y)
                if (x - x0) % 2 == 0:
                    self.put(x, y, g - 1, 'timber', (96, 72, 50))
                    self.put(x, y, g - 2, 'timber', (96, 72, 50))
                else:
                    self.put(x, y, g - 1, 'timber', (84, 62, 44))
        for x in range(x0 - 2, x1 + 3, 3):
            self.small_pumpkin(x, y1 + 6)
        # yard cauldron
        cx, cy = x0 - 4, y1 + 4
        g = self.ground(cx, cy)
        for (dz, r) in ((1, 1), (2, 2), (3, 2)):
            for x in range(cx - r, cx + r + 1):
                for y in range(cy - r, cy + r + 1):
                    if abs(x - cx) + abs(y - cy) <= r + 1:
                        inner = dz == 3 and abs(x - cx) <= 1 and abs(y - cy) <= 1 and (x, y) != (cx - r, cy)
                        self.put(x, y, g - dz, 'brew' if inner and abs(x - cx) + abs(y - cy) <= 1 else 'iron',
                                 (120, 230, 120) if inner and abs(x - cx) + abs(y - cy) <= 1 else (38, 36, 44))

    def pumpkin_patch(self):
        S = SPEC
        h = [hh for hh in S['hills'] if hh['name'] == 'pumpkin_hill'][0]
        cx, cy = h['cx'], h['cy']
        # tilled soil rows (low-contrast, 2-wide rows)
        for x in range(cx - 11, cx + 12):
            for y in range(cy - 11, cy + 12):
                if np.hypot(x - cx, y - cy) <= 11 and self.top(x, y) == self.ground(x, y) \
                        and self.mat[x, y, self.ground(x, y)] == A['grass']:
                    c = (82, 60, 42) if (y // 2) % 2 else (94, 70, 48)
                    self.paint(x, y, self.ground(x, y), c, 'soil')
        for (dx, dy, r) in ((-6, -4, 3), (5, 3, 3), (-2, 7, 2), (7, -6, 2)):
            self.jack(cx + dx, cy + dy, r, face=(0, -1))
        for (dx, dy) in ((0, -8), (-9, 2), (3, -2), (9, 8), (-6, 9), (2, 10), (-10, -6)):
            self.small_pumpkin(cx + dx, cy + dy)
        # scarecrow
        sx, sy = cx + 1, cy - 1
        g = self.ground(sx, sy)
        for z in range(g - 1, g - 9, -1):
            self.put(sx, sy, z, 'timber', (90, 66, 46))
        for y in range(sy - 3, sy + 4):
            self.put(sx, y, g - 6, 'timber', (90, 66, 46))
        for y in range(sy - 2, sy + 3):
            for z in (g - 5, g - 4, g - 3):
                if abs(y - sy) <= 1 or z == g - 5:
                    self.put(sx, y, z, 'cloth', (110, 74, 58))
        for dz in (9, 10):
            for dx in (0, 1):
                for dy in (0, 1):
                    self.put(sx + dx - 1, sy + dy, g - dz, 'pumpkin', (222, 116, 28))
        self.paint(sx - 1, sy + 1, g - 9, (255, 212, 96), 'jack_face')
        self.paint(sx - 1, sy, g - 9, (255, 212, 96), 'jack_face')
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1, 2):
                self.put(sx - 1 + dx, sy + dy, g - 11, 'iron', (30, 28, 34))
        self.put(sx - 1, sy, g - 12, 'iron', (30, 28, 34))
        self.put(sx - 1, sy, g - 13, 'iron', (30, 28, 34))

    def graveyard(self):
        pts = [(74, 200, 0), (78, 204, 1), (82, 199, 0), (86, 205, 0), (90, 200, 1), (76, 210, 0), (84, 212, 1),
               (92, 210, 0), (80, 216, 0), (88, 218, 1)]
        for (x, y, k) in pts:
            if self.top(x, y) == self.ground(x, y):
                self.gravestone(x, y, k)
        # iron fence corners
        for (x, y) in ((70, 195), (96, 195), (70, 222), (96, 222)):
            self.lantern_post(x, y, 3)

    def groves(self):
        rng = self.rng
        land = self.info['land']
        placed = []
        keep = self.keep.copy()
        # props already placed are keep-outs too
        occ = self.solid[:, :, :60].any(axis=2) & (np.argmax(self.solid, axis=2) < self.ztop)
        keep |= ndimage.binary_dilation(occ, iterations=4)
        for (gx, gy, gr, cnt) in SPEC['groves']:
            made = tries = 0
            while made < cnt and tries < 250:
                tries += 1
                a = rng.rand() * 2 * np.pi
                rr = gr * np.sqrt(rng.rand())
                tx, ty = int(gx + rr * np.cos(a)), int(gy + rr * np.sin(a))
                if not (10 <= tx <= 246 and 10 <= ty <= 500):
                    continue
                if keep[tx - 5:tx + 6, ty - 5:ty + 6].any():
                    continue
                if not land[tx - 4:tx + 5, ty - 4:ty + 5].all() or self.H[tx, ty] < 4:
                    continue
                if any((tx - px) ** 2 + (ty - py) ** 2 < 81 for px, py in placed):
                    continue
                kind = rng.rand()
                if kind < 0.40:
                    self.witch_tree(tx, ty, self.ground(tx, ty) - 10 - rng.randint(0, 4), 2,
                                    [(1, 1, 4, 2), (-1, 0, 4, 2)], 3, 2, lean=(rng.randint(-1, 2), rng.randint(-1, 2)),
                                    moss=0.03)
                elif kind < 0.65:
                    self.pine(tx, ty, 13 + rng.randint(0, 5))
                elif kind < 0.85:
                    self.autumn_tree(tx, ty, 7 + rng.randint(0, 3))
                else:
                    self.dead_tree(tx, ty, 9 + rng.randint(0, 4))
                placed.append((tx, ty))
                made += 1
        self.placed_trees = placed

    def big_trees(self):
        gt = SPEC['giant_tree']
        self.witch_tree(gt['x'], gt['y'], 16, 6, [(1, 0, 7, 2), (-1, 0, 6, 2), (0, 1, 7, 2), (0, -1, 6, 2)],
                        6, 3, lean=(0, 0), moss=0.03, lantern=True)
        for tr in SPEC['screen_trees']:
            self.witch_tree(tr['x'], tr['y'], 21, 4, [(0, 1, 6, 3), (0, -1, 6, 3), (-1, 0, 4, 2), (1, 0, 3, 2)],
                            7, 3, lean=(0, 0), moss=0.02, max_x=168)

    def toadstools(self):
        """Small fairy rings of toadstools (1-2 high, never on paths or in keep-out areas)."""
        rng = np.random.RandomState(SEED + 33)
        land = self.info['land']
        made = 0
        for _ in range(400):
            if made >= 14:
                break
            cx, cy = rng.randint(30, 175), rng.randint(110, 400)
            if self.keep[cx - 6:cx + 7, cy - 6:cy + 7].any() or not land[cx - 6:cx + 7, cy - 6:cy + 7].all():
                continue
            pts = [(int(round(cx + 4 * np.cos(t))), int(round(cy + 4 * np.sin(t)))) for t in np.linspace(0, 2 * np.pi, 9)[:-1]]
            if not all(self.top(x, y) == self.ground(x, y) and self.mat[x, y, self.ground(x, y)] == A['grass']
                       for x, y in pts):
                continue
            for i, (x, y) in enumerate(pts):
                g = self.ground(x, y)
                self.put(x, y, g - 1, 'cloth', (214, 206, 190))                 # stalk
                cap = (176, 44, 52) if i % 2 else (132, 70, 168)
                self.put(x, y, g - 2, 'cloth', cap)
            made += 1

    def islets(self):
        for it in SPEC['islets']:
            cx, cy = it['cx'], it['cy']
            self.dead_tree(cx - 5, cy - 1, 10, 3)
            self.lantern_post(cx - 7, cy + 3, 2)
            self.gravestone(cx - 2, cy + 3, 0)
            self.small_pumpkin(cx - 6, cy - 5)

    def shore_rocks(self):
        land = self.info['land']
        rng = np.random.RandomState(SEED + 21)
        coast = land & ~ndimage.binary_erosion(land)
        cand = np.argwhere(coast[:257])
        rng.shuffle(cand)
        n = 0
        for (x, y) in cand:
            if n >= 26:
                break
            if self.keep[max(x - 6, 0):x + 7, y - 6:y + 7].any():
                continue
            if self.info['central'][x, y] or self.info['islets'][x, y]:
                continue
            if self.solid[x - 3:x + 4, y - 3:y + 4, :60].any():
                continue
            self.boulder(int(x), int(y), 2 + rng.randint(0, 2))
            n += 1

    def paths(self):
        """Packed-dirt paths (paint only) from the green's gates to the crossings and the cottage."""
        segs = [(118, 231, 118, 200), (118, 200, 121, 168),            # north gate → cottage
                (118, 281, 118, 300), (118, 300, 140, 300), (140, 300, 152, 292), (152, 292, 166, 262),
                (166, 262, 168, 256),                                  # south gate → boardwalk
                (138, 222, 166, 224), (166, 224, 168, 230),            # north-east → footbridge
                (93, 256, 70, 256)]                                    # west gate → giant tree
        for (ax, ay, bx, by) in segs:
            n = max(abs(bx - ax), abs(by - ay)) + 1
            for i in range(n):
                x = int(round(ax + (bx - ax) * i / max(n - 1, 1)))
                y = int(round(ay + (by - ay) * i / max(n - 1, 1)))
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        xx, yy = x + dx, y + dy
                        z = self.ztop[xx, yy]
                        if self.top(xx, yy) == z and self.mat[xx, yy, z] in (A['grass'], A['sand'], A['leaf_litter']):
                            t = ((xx * 5 + yy * 3) % 4)
                            self.paint(xx, yy, z, (116 + t * 5, 92 + t * 4, 66 + t * 3), 'path')

    def name_tag(self):
        """Corner tag: map name only, painted on the sea floor (ground level) in the SW corner (z 63).
        That corner is open water with no props, so the ground-level tag reads cleanly from above."""
        from ww_font import text_mask
        l1 = text_mask('WITCHWOOD ISLES', scale=2)
        x0, y0 = 10, 486
        for (i, j) in np.argwhere(l1):
            self.paint(x0 + j, y0 + i, 63, (230, 214, 170))
        return (x0, y0, x0 + l1.shape[1], y0 + l1.shape[0])

    # ------------------------------------------------------------- finish
    def mirror(self):
        for a in (self.solid, self.mat, self.ovr):
            a[257:512] = a[255:0:-1]
        self.col[257:512] = self.col[255:0:-1]
        self.solid[:, :, 63] = True

    def shade(self):
        """Fill colours for every voxel without an override (material ramp + coherent noise, folded x)."""
        nA = fbm(seed_of('shadeA', SEED), (W, W), 8, 2)
        nB = fbm(seed_of('shadeB', SEED), (W, W), 3, 1)
        surf = surface_mask(self.solid)
        idx = np.argwhere(surf & ~self.ovr)
        x, y, z = idx[:, 0], idx[:, 1], idx[:, 2]
        fx = np.where(x > 256, 512 - x, x)
        n = 0.6 * nA[fx, (y + z * 11) % W] + 0.4 * nB[(fx + z * 5) % W, y]
        m = self.mat[x, y, z]
        dark = np.zeros((len(MAT_NAMES), 3), np.float32)
        light = np.zeros((len(MAT_NAMES), 3), np.float32)
        for name, (d, l) in RAMP.items():
            dark[A[name]] = d
            light[A[name]] = l
        c = dark[m] + (light[m] - dark[m]) * n[:, None]
        # earth: strata bands on exposed sides
        e = m == A['earth']
        band = ((z[e] + (nA[fx[e], y[e]] * 4).astype(int)) // 3) % 2
        c[e] *= np.where(band == 1, 0.9, 1.0)[:, None]
        self.col[x, y, z] = c.clip(0, 255).astype(np.uint8)
        # lighting on everything: sides darker, undersides darker still
        solid = self.solid
        above = np.zeros_like(solid)
        above[:, :, 1:] = solid[:, :, :-1]
        below = np.ones_like(solid)
        below[:, :, :-1] = solid[:, :, 1:]
        cols = self.col.astype(np.float32)
        side = surf & above
        under = surf & ~below & above
        cols[side] *= 0.82
        cols[under] *= 0.80
        glow_ids = [A[g] for g in GLOW]
        isglow = np.isin(self.mat, glow_ids) & surf
        cols[isglow] = self.col[isglow]            # glow surfaces keep full brightness
        self.col = cols.clip(0, 255).astype(np.uint8)
        return surf

    def build(self):
        self.terrain_colours()
        self.seabed()
        self.spawn_green()
        self.screen_houses()
        self.boardwalks()
        self.pilings()
        self.mound_art()
        self.central_floor()
        self.cottage()
        self.pumpkin_patch()
        self.graveyard()
        self.big_trees()
        self.groves()
        self.toadstools()
        self.islets()
        self.shore_rocks()
        self.paths()
        self.mirror()
        self.tag_box = self.name_tag()          # after the mirror: one corner only
        surf = self.shade()
        return self.solid, self.mat, self.col
