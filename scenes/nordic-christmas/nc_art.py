"""Hrafnfjord Yule: art pass (phase D). Runs on the finished graybox canvas; gameplay geometry is not changed.

Order: cosmetic ornaments (additive, recorded with boxes) -> recolour by function role + structure identity
(kit palette ramps, hue-shifted, snow capped) -> vegetation recolour -> glow sources -> sky decor (expected floating)
-> corner tag -> kit lighting (baked light + AO) -> kit bake_glow -> kit enforce_brightness.

Every voxel ADDED or REMOVED here is cosmetic and listed in build.json 'art_additions' with its box; the runner
diffs solid/air against the graybox. Colours never need a box.
"""
from __future__ import annotations

import math

import numpy as np

from aosmap.kit import color, noise, palette as PAL, sky, tag
from aosmap.kit.codec import surface_mask
from aosmap.kit.canvas import line_points
from nc_world import FC
from nordic_christmas_spec import SPEC, GLOW

S = SPEC
H3 = noise.hash3


# ================================================================== palettes (night grade, moonlit)
def R(mid, n=5, step=0.05, light=70, shadow=290, tint=0.0, cap=None, hs=10):
    return PAL.shifted_ramp(mid, n=n, light_step=step, hue_shift=hs, light_hue=light, shadow_hue=shadow,
                            end_tint=tint, cap=cap)


SNOW = R((138, 146, 164), 7, 0.045, 220, 290, 0.02, 212)          # field band, darkest first
SNOW_ROOF = R((146, 154, 170), 5, 0.04, 220, 290, 0.02, 212)
ICE = R((104, 132, 126), 7, 0.045, 190, 250, 0.0, 212)             # grey-green, not icy blue
ICE_PALE = R((138, 160, 152), 3, 0.03, 190, 250, 0.0, 212)
GRANITE = R((106, 104, 110), 5, 0.05, 70, 280)
STONE_WARM = R((114, 106, 96), 5, 0.05, 70, 280)
HEATHER = R((92, 74, 88), 3, 0.05, 70, 280)
TURF = R((74, 90, 60), 5, 0.05, 90, 280)
STRAW = R((156, 128, 80), 5, 0.05, 80, 280)
TAR = R((80, 60, 46), 5, 0.045, 60, 280)                            # tarred timber
WEATHERED = R((126, 112, 96), 5, 0.045, 60, 280)                    # silver-grey weathered planks
LOG = R((112, 84, 60), 5, 0.05, 60, 280)                            # round logs (lodges)
RED_TIMBER = R((118, 64, 48), 5, 0.045, 60, 280)                    # oxblood boards (bathhouse, huts)
OCHRE = R((150, 108, 56), 5, 0.045, 70, 280)
PLANK = R((124, 94, 64), 5, 0.04, 60, 280)
SHINGLE_TAR = R((62, 52, 48), 5, 0.04, 60, 280)                    # mead hall: dark tarred shingles
SHINGLE_CHURCH = R((98, 76, 60), 5, 0.05, 30, 280)                 # church: weathered tar-brown shingles
SLATE = R((72, 78, 88), 5, 0.04, 220, 290)                          # smithy
PLANKROOF = R((116, 110, 100), 5, 0.04, 70, 280)                   # naust: silvered plank roof
BARKROOF = R((104, 78, 58), 5, 0.04, 60, 280)                       # bathhouse / lodge: birch-bark + wood shingles
TARPAPER = R((64, 62, 66), 5, 0.04, 220, 290)                       # ice huts
HULL = R((74, 56, 44), 5, 0.04, 60, 280)
GOLD = R((176, 136, 70), 3, 0.05, 80, 280)
BONE = R((182, 170, 146), 3, 0.05, 80, 280)
IRON = R((58, 58, 64), 3, 0.04, 220, 290)
SPRUCE = R((40, 66, 54), 5, 0.045, 120, 280)
PINE = R((52, 74, 56), 5, 0.045, 100, 280)
BIRCH_TWIG = R((104, 90, 92), 3, 0.05, 70, 290)
BIRCH_BARK = R((168, 164, 154), 3, 0.05, 80, 280)

TYPES = ['other', 'mead', 'smithy', 'shed', 'longhouse', 'byre', 'bath', 'church', 'beacon', 'lodge', 'hut', 'ship',
         'gate', 'rock']
# per type: walls, trim/posts, roof, roof snow share, base course (stone rows above the floor)
STYLE = {
    'mead': dict(wall=TAR, trim=GOLD, roof=SHINGLE_TAR, snow=0.45, base=0, courses='log'),
    'smithy': dict(wall=GRANITE, trim=TAR, roof=SLATE, snow=0.35, base=0, courses='stone'),
    'shed': dict(wall=STONE_WARM, trim=TAR, roof=PLANKROOF, snow=0.5, base=0, courses='stone', gable=TAR),
    'longhouse': dict(wall=WEATHERED, trim=TAR, roof=TURF, snow=0.6, base=2, courses='plank'),
    'byre': dict(wall=WEATHERED, trim=TAR, roof=TURF, snow=0.6, base=2, courses='plank'),
    'bath': dict(wall=RED_TIMBER, trim=TAR, roof=BARKROOF, snow=0.5, base=2, courses='plank'),
    'church': dict(wall=RED_TIMBER, trim=GOLD, roof=SHINGLE_CHURCH, snow=0.3, base=1, courses='stave'),
    'beacon': dict(wall=TAR, trim=WEATHERED, roof=SHINGLE_TAR, snow=0.3, base=2, courses='lattice'),
    'lodge': dict(wall=LOG, trim=TAR, roof=BARKROOF, snow=0.75, base=1, courses='log'),
    'hut': dict(wall=OCHRE, trim=TAR, roof=TARPAPER, snow=0.55, base=0, courses='plank'),
    'gate': dict(wall=GRANITE, trim=GRANITE, roof=SLATE, snow=0.4, base=0, courses='stone'),
    'other': dict(wall=WEATHERED, trim=TAR, roof=PLANKROOF, snow=0.5, base=0, courses='plank'),
    'rock': dict(wall=GRANITE, trim=GRANITE, roof=GRANITE, snow=0.5, base=0, courses='stone'),
    'ship': dict(wall=HULL, trim=TAR, roof=PLANK, snow=0.3, base=0, courses='plank'),
}


def type_of(name):
    n = name.lower()
    for key, t in (('mead hall', 'mead'), ('smithy', 'smithy'), ('boat shed', 'shed'), ('byre', 'byre'),
                   ('longhouse', 'longhouse'), ('bathhouse', 'bath'), ('stave church', 'church'),
                   ('beacon', 'beacon'), ('hunting lodge', 'lodge'), ('ice-fishing hut', 'hut'),
                   ('longship', 'ship'), ('raven gate', 'gate'), ('thing-rock', 'rock')):
        if key in n:
            return t
    return 'other'


def pick(ramp, t):
    """ramp list (darkest first), t array in [0, 1] -> (n, 3) uint8."""
    a = np.array(ramp, float)
    i = np.clip(np.rint(np.asarray(t) * (len(ramp) - 1)), 0, len(ramp) - 1).astype(int)
    return a[i]


# ================================================================== cosmetic additions (recorded)
class Adds:
    def __init__(self, cv):
        self.cv = cv
        self.rec = {}

    def _note(self, name, x, y, z, removed=False):
        r = self.rec.setdefault(name, {'name': name, 'box': [x, x, y, y, z, z], 'added': 0, 'removed': 0})
        b = r['box']
        b[0], b[1], b[2], b[3], b[4], b[5] = min(b[0], x), max(b[1], x), min(b[2], y), max(b[3], y), min(b[4], z), max(b[5], z)
        r['removed' if removed else 'added'] += 1

    def put(self, name, x, y, z, c, mat='ornament', mirror=True, glow=False):
        cv = self.cv
        xs = {int(x), 512 - int(x)} if mirror and 0 < x < 512 and x != 256 else {int(x)}
        for xx in xs:
            if not cv.inside(xx, y, z) or cv.solid[xx, y, z]:
                continue
            if glow:
                cv.set(xx, y, z, c, mat)
                cv.add_glow(xx, y, z, c)
            else:
                cv.set(xx, y, z, c, mat)
            self._note(name, xx, y, z)

    def line(self, name, p0, p1, c, mat='ornament', mirror=True):
        for (x, y, z) in line_points(*p0, *p1):
            self.put(name, x, y, z, c, mat, mirror)

    def remove(self, name, x, y, z):
        if self.cv.inside(x, y, z) and self.cv.solid[x, y, z]:
            self.cv.clear(x, y, z)
            self._note(name, x, y, z, removed=True)

    def report(self):
        return list(self.rec.values())


def top_at(cv, x, y):
    col = cv.solid[x, y]
    return int(np.argmax(col)) if col.any() else 64


def finials(A, cv, structs):
    """Crossed gable boards (vindskier) rising above every ridge end; dragon heads on the church."""
    axis = {'mead': 'x', 'smithy': 'x', 'shed': 'x', 'longhouse': 'x', 'bath': 'y', 'lodge': 'x'}
    wood = tuple(int(v) for v in TAR[3])
    for s in structs:
        t = type_of(s['name'])
        if t not in axis or s['box'][0] > 255:
            continue
        x0, x1, y0, y1 = s['box']
        if axis[t] == 'x':
            yr = y0 + (y1 - y0) // 2
            ends = [] if t == 'mead' else [(x0, yr), (x1, yr)]           # the mead hall keeps its antler gables
            if t == 'longhouse':
                ends = [(x1, yr)]                                        # west gable abuts the byre
            for (xe, _) in ends:
                zt = top_at(cv, xe, yr)
                if zt >= 63:
                    continue
                A.line('gable finials', (xe, yr - 1, zt + 1), (xe, yr + 2, zt - 2), wood)
                A.line('gable finials', (xe, yr + 1, zt + 1), (xe, yr - 2, zt - 2), wood)
        else:
            xr = x0 + (x1 - x0) // 2
            for ye in (y0, y1):
                zt = top_at(cv, xr, ye)
                if zt >= 63:
                    continue
                A.line('gable finials', (xr - 1, ye, zt + 1), (xr + 2, ye, zt - 2), wood)
                A.line('gable finials', (xr + 1, ye, zt + 1), (xr - 2, ye, zt - 2), wood)
    # church: dragon heads at both nave gable ends and on the tower spire foot
    for s in structs:
        if type_of(s['name']) != 'church' or s['box'][0] > 255:
            continue
        for xe, d in ((145, -1), (159, 1)):
            yr = 84
            zt = top_at(cv, xe, yr)
            if zt >= 63:
                continue
            for k in range(1, 5):
                A.put('church dragon heads', xe + d * k, yr, zt, tuple(int(v) for v in TAR[1]))     # neck, attached
            for k in range(2, 4):
                A.put('church dragon heads', xe + d * k, yr, zt - 1, tuple(int(v) for v in TAR[1]))
            A.put('church dragon heads', xe + d * 3, yr, zt - 2, tuple(int(v) for v in TAR[1]))
            A.put('church dragon heads', xe + d * 4, yr, zt - 2, tuple(int(v) for v in TAR[1]))
            A.put('church dragon heads', xe + d * 3, yr, zt - 3, (255, 150, 60), glow=True)     # ember eye


def lodge_antlers(A, cv, structs):
    bone = tuple(int(v) for v in BONE[2])
    for s in structs:
        if type_of(s['name']) != 'lodge' or s['box'][0] > 255:
            continue
        x0, x1, y0, y1 = s['box']
        south_door = y0 < 256
        yw = y1 - 1 if south_door else y0 + 1            # wall line (reg box has ov 1)
        yo = yw + (1 if south_door else -1)
        zf = int(np.median(cv.H[x0 + 2:x1 - 1, y0 + 2:y1 - 1]))
        zs = zf - 5                                        # skull on the door lintel, tines above
        A.put('lodge antler racks', 48, yo, zs, bone)
        for sgn in (-1, 1):
            A.line('lodge antler racks', (48, yo, zs), (48 + 3 * sgn, yo, zs - 2), bone)
            A.put('lodge antler racks', 48 + 2 * sgn, yo, zs - 2, bone)


def raven_heads(A, cv):
    """Carved raven heads at mid-span on both faces of the crown, and on each leg's turret cap."""
    dark = (58, 56, 64)
    for (yf, d) in ((98, -1), (106, 1)):
        for x in (255, 256, 257):
            for z in (19, 20, 21):
                A.put('Raven Gate raven heads', x, yf + d, z, dark, mirror=False)
        for x in (255, 256, 257):
            A.put('Raven Gate raven heads', x, yf + 2 * d, 20, dark, mirror=False)
        A.put('Raven Gate raven heads', 256, yf + 3 * d, 20, (90, 84, 70), mirror=False)       # beak
        A.put('Raven Gate raven heads', 256, yf + 3 * d, 21, (90, 84, 70), mirror=False)
        A.put('Raven Gate raven heads', 256, yf + 4 * d, 21, (90, 84, 70), mirror=False)
        for x in (255, 257):
            A.put('Raven Gate raven heads', x, yf + 2 * d, 19, GLOW['rune_blue'], mirror=False, glow=True)
    # leg caps: a perched raven on each pyramid tip (west leg authored, mirrored)
    lx0 = S['raven_gate']['legs'][0][0]
    ly1 = S['raven_gate']['legs'][0][3]
    cx, cy = lx0 + 2, ly1 - 2
    zt = top_at(cv, cx, cy)
    for (dx, dy, dz) in ((0, 0, 1), (0, -1, 1), (0, 1, 1), (0, 0, 2), (0, -1, 2), (0, -2, 2), (-1, 0, 2), (1, 0, 2)):
        A.put('Raven Gate raven heads', cx + dx, cy + dy, zt - dz, dark)
    A.put('Raven Gate raven heads', cx, cy - 3, zt - 2, (90, 84, 70))


def longship_details(A, cv, ships):
    """Shield rows on the gunwale, a furled frosted sail on the north ship, ice heaved at bow and stern."""
    cols = [(178, 140, 60), (120, 44, 38), (70, 74, 86), (160, 150, 128)]
    hullm = cv.materials.get('hull')
    for (cy, mast) in ships:
        for x in range(236, 249, 2):
            for side in (-1, 1):
                # outermost hull voxel at gunwale - 1
                zz = None
                for z in range(36, 41):
                    if cv.mat[x, cy, 41] == hullm:
                        zz = 38
                        break
                y = cy
                while 0 < abs(y - cy) < 8 or y == cy:
                    ny = y + side
                    if cv.mat[x, ny, 38] == hullm or cv.mat[x, ny, 39] == hullm:
                        y = ny
                        continue
                    break
                c = cols[((x // 2) + (side > 0)) % 4]
                for (dx, dz) in ((0, 0), (1, 0), (0, 1), (1, 1)):
                    A.put('longship shields', x + dx, y + side, 38 + dz + (1 if (side > 0 and cy > 256) else 0), c)
        if mast:
            sail = (172, 164, 150)
            for y in range(cy - 5, cy + 6):
                for xx in (255, 256):
                    A.put('longship furled sail', xx, y, mast + 3, sail, mirror=(xx == 255))
                    if abs(y - cy) < 4:
                        A.put('longship furled sail', xx, y, mast + 4, (188, 186, 184), mirror=(xx == 255))
        # ice heave: slabs at bow and stern on the ice (not at the boarding gaps)
        for x in range(226, 232):
            for y in range(cy - 3, cy + 4):
                h = H3(x, y, cy, 11)
                if h < 0.55 and not cv.solid[x, y, 42] and cv.solid[x, y, 43]:
                    A.put('ice heave at the hulls', x, y, 42, tuple(int(v) for v in ICE_PALE[1]), 'icerubble')
                    if h < 0.18:
                        A.put('ice heave at the hulls', x, y, 41, tuple(int(v) for v in ICE_PALE[2]), 'icerubble')


def stern_curls(A, cv, ships):
    """Cosmetic asymmetry after the mirror: the east end of each ship becomes a curled stern (the west end keeps the
    dragon prow). Removes the east head voxels and draws a spiral."""
    wood = tuple(int(v) for v in HULL[2])
    for (cy, _) in ships:
        prow = 28
        for x in range(279, 285):
            for y in range(cy - 1, cy + 2):
                for z in range(prow - 2, prow + 2):
                    if not (x in (279, 280) and y == cy):
                        A.remove('longship curled sterns', x, y, z)
        pts = [(279, prow - 1), (279, prow - 2), (280, prow - 3), (281, prow - 4), (282, prow - 4), (283, prow - 3),
               (283, prow - 2), (282, prow - 1), (281, prow - 1), (281, prow - 2)]
        prev = (280, cy, prow)
        for (x, z) in pts:
            A.line('longship curled sterns', prev, (x, cy, z), wood, mirror=False)
            prev = (x, cy, z)


POSTS = []


def lantern_posts(A, cv):
    """Lantern posts along the village streets and yards (1 x 1, 4 tall, glowing lamp on top)."""
    cand = [(182, 177), (186, 183), (212, 182), (226, 179), (136, 181), (129, 208), (172, 204),
            (182, 335), (186, 329), (212, 331), (226, 334), (136, 334), (129, 304), (172, 306),
            (150, 102), (164, 66), (60, 82), (60, 430)]
    post = tuple(int(v) for v in IRON[1])
    n = 0
    for (x, y) in cand:
        g = int(cv.H[x, y])
        if top_at(cv, x, y) != g:
            continue
        if any(top_at(cv, x + dx, y + dy) < int(cv.H[x + dx, y + dy]) for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
            continue
        for z in range(g - 3, g):
            A.put('lantern posts', x, y, z, post)
        A.put('lantern posts', x, y, g - 4, GLOW['window_amber'], glow=True)
        n += 1
        POSTS.append((x, y, g))
    return n


def furnish(A, cv, rooms, rng):
    """Beds, barrels, chests, looms and weapon racks along the walls of every room (1-3 tall, against a solid wall,
    never within 2 of a door, a stair or a recorded interior point)."""
    stair = cv.materials.get('stair')
    pts = [(p[1], p[2], p[3]) for p in cv.interiors]
    wood = tuple(int(v) for v in PLANK[1])
    dark = tuple(int(v) for v in TAR[2])
    wool = [(150, 60, 50), (70, 82, 104), (156, 140, 104)]
    n = 0
    for (x0, x1, y0, y1, zf) in rooms:
        if x0 > 255:
            continue
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                if (x + 2 * y) % 3:
                    continue
                if not cv.solid[x, y, zf] or cv.solid[x, y, zf - 1] or cv.solid[x, y, zf - 2] or cv.solid[x, y, zf - 3]:
                    continue
                walls = [(dx, dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)) if cv.solid[x + dx, y + dy, zf - 1]
                         and cv.solid[x + dx, y + dy, zf - 3]]
                if len(walls) != 1:
                    continue
                dx, dy = walls[0]
                ok = all(cv.solid[x + dx + k * dy, y + dy + k * dx, zf - 1] and cv.solid[x + dx + k * dy, y + dy + k * dx, zf - 3]
                         for k in (-2, -1, 1, 2))
                if not ok:
                    continue
                sub = cv.mat[x - 2:x + 3, y - 2:y + 3, zf - 6:zf + 1]
                if stair is not None and (sub == stair).any():
                    continue
                if any(abs(px - x) <= 2 and abs(py - y) <= 2 and abs(pz - zf) <= 1 for (px, py, pz) in pts):
                    continue
                k = int(rng.integers(5))
                if k == 0:                                           # barrel
                    A.put('interior furniture', x, y, zf - 1, wood)
                    A.put('interior furniture', x, y, zf - 2, dark)
                elif k == 1:                                         # chest
                    A.put('interior furniture', x, y, zf - 1, dark)
                elif k == 2:                                         # bed / fur bench
                    A.put('interior furniture', x, y, zf - 1, wool[int(rng.integers(3))])
                elif k == 3:                                         # loom against the wall
                    for z in (zf - 1, zf - 2, zf - 3):
                        A.put('interior furniture', x, y, z, wood if z != zf - 2 else wool[int(rng.integers(3))])
                else:                                                # weapon rack / shield on the wall
                    A.put('interior furniture', x, y, zf - 2, wool[int(rng.integers(3))])
                n += 1
    return n


# ================================================================== recolour
def role_grid(cv, idx):
    rgb = cv.rgb[idx].astype(np.int64)
    packed = (rgb[:, 0] << 16) | (rgb[:, 1] << 8) | rgb[:, 2]
    keys = {((c[0] << 16) | (c[1] << 8) | c[2]): i for i, c in enumerate(FC.values())}
    names = list(FC.keys())
    karr = np.array(sorted(keys))
    vals = np.array([keys[k] for k in karr])
    pos = np.clip(np.searchsorted(karr, packed), 0, len(karr) - 1)
    role = np.where(karr[pos] == packed, vals[pos], -1)
    return role, names


def owner_map(structs):
    own = np.zeros((512, 512), np.int16)
    zf = np.zeros(len(structs) + 1, np.int16)
    for i, s in enumerate(structs, start=1):
        x0, x1, y0, y1 = s['box']
        own[x0:x1 + 1, y0:y1 + 1] = TYPES.index(type_of(s['name']))
    return own


def recolour(cv, structs, report):
    surf = surface_mask(cv.solid)
    idx = np.nonzero(surf)
    xs, ys, zs = idx
    role, names = role_grid(cv, idx)
    rn = {n: i for i, n in enumerate(names)}
    mat = cv.mat[idx]
    M = cv.materials
    out = cv.rgb[idx].astype(float)
    above_air = ~cv.solid[xs, ys, np.maximum(zs - 1, 0)] | (zs == 0)
    n1 = H3(xs, ys, zs, 1)
    n2 = H3(xs // 3, ys // 3, zs // 2, 2)
    fbm = noise.fbm2((512, 512), 32, 3, 'artsnow', S['layout_seed'])
    fbm2 = noise.fbm2((512, 512), 10, 2, 'artpatch', S['layout_seed'])
    lane = noise.fbm2((512, 512), 24, 2, 'icelane', S['layout_seed'])
    own = owner_map(structs)
    T = own[xs, ys]
    own_i = np.zeros((512, 512), np.int32)
    for i, s_ in enumerate(structs, start=1):
        x0, x1, y0, y1 = s_['box']
        own_i[x0:x1 + 1, y0:y1 + 1] = i
    OI = own_i[xs, ys]
    roofm = np.isin(mat, [M['roof']]) | (np.isin(role, [rn['roof'], rn['ridge']]) & (mat == M['building']))
    zmin = np.full(len(structs) + 1, 99)
    zmax = np.full(len(structs) + 1, -1)
    np.minimum.at(zmin, OI[roofm], zs[roofm])
    np.maximum.at(zmax, OI[roofm], zs[roofm])
    frac = np.clip((zmax[OI] - zs) / np.maximum(zmax[OI] - zmin[OI], 1), 0, 1)
    along_y = np.zeros(len(structs) + 1, bool)
    a0 = np.zeros(len(structs) + 1, int)
    a1 = np.zeros(len(structs) + 1, int)
    for i, s_ in enumerate(structs, start=1):
        x0, x1, y0, y1 = s_['box']
        ay = type_of(s_['name']) in ('bath', 'hut') or (x1 - x0) < (y1 - y0) and type_of(s_['name']) not in ('mead', 'longhouse', 'smithy', 'shed', 'lodge', 'church')
        along_y[i] = ay
        a0[i], a1[i] = (y0, y1) if ay else (x0, x1)
    acoord = np.where(along_y[OI], ys, xs)
    aend = np.minimum(acoord - a0[OI], a1[OI] - acoord)
    drip = H3(acoord // 2, OI, 0, 61) < 0.18
    rf = noise.fbm2((512, 512), 4, 2, 'roofturf', S['layout_seed'])
    rs_ = noise.fbm2((512, 512), 5, 2, 'roofsnow', S['layout_seed'])
    rs_ = (rs_ - rs_.min()) / max(rs_.max() - rs_.min(), 1e-6)
    Hm = cv.H.astype(int)
    slope = np.maximum.reduce([np.abs(np.diff(Hm, axis=0, append=Hm[-1:])), np.abs(np.diff(Hm, axis=1, append=Hm[:, -1:]))])

    def rset(m, rgb):
        out[m] = rgb

    def is_role(*nm):
        return np.isin(role, [rn[n] for n in nm])

    # ---------------------------------------------------------------- terrain
    ground = (mat == M['ground']) & is_role('ground', 'field', 'fell', 'hill', 'berm', 'track', 'holm', 'bank')
    zone_field = is_role('field')
    zone_fell = is_role('fell')
    zone_track = is_role('track')
    zone_bank = is_role('bank', 'holm')
    fv = fbm[xs, ys]
    pv = fbm2[xs, ys]
    sl = slope[xs, ys]
    fz = (fv - fbm.mean()) / max(fbm.std(), 1e-6)                 # standardised drift field
    t_snow = np.clip(0.54 + 0.34 * fz + (n1 - 0.5) * 0.12, 0.03, 0.98)
    rset(ground, pick(SNOW, t_snow[ground]))
    side = ground & ~above_air
    rset(side, pick(SNOW, np.clip(t_snow[side] - 0.35, 0, 1)))
    # farmland: stubble rows showing through, furrows along x every 5 rows (low contrast)
    m = ground & zone_field & above_air & (pv > 0.6) & (ys % 3 != 1)
    rset(m, 0.45 * pick(STRAW, np.clip(0.3 + 0.3 * n1[m], 0, 1)) + 0.55 * pick(SNOW, np.full(m.sum(), 0.35)))
    m = ground & zone_field & above_air & (ys % 5 == 0) & (pv <= 0.58)
    rset(m, pick(SNOW, np.full(m.sum(), 0.33)))
    # fells: patchy snow, heather and turf in the gaps, granite on the steps
    m = ground & zone_fell & above_air & (pv < 0.45)
    rset(m, 0.9 * np.where((n2[m] < 0.5)[:, None], pick(HEATHER, 0.3 + 0.4 * n1[m]), pick(TURF, 0.2 + 0.4 * n1[m]))
         + 0.1 * pick(SNOW, np.full(m.sum(), 0.2)))
    cb = m & (pv < 0.3) & (n2 < 0.35)
    rset(cb, np.array([[50, 66, 50]]) * (0.95 + 0.1 * n1[cb])[:, None])                 # crowberry
    m = ground & (zone_fell | is_role('hill', 'berm')) & ((sl[:] >= 1) & (n2 < 0.35) | ~above_air)
    rset(m, pick(GRANITE, 0.2 + 0.6 * n1[m]))
    # trampled yards and paths: packed snow and earth
    m = ground & zone_track
    rset(m, np.where((pv[m] > 0.62)[:, None], pick(STONE_WARM, 0.3 + 0.3 * n1[m]),
                     pick(SNOW, np.clip(0.2 + 0.2 * n1[m], 0, 1))))
    # drifts on the banks: the brightest snow band (crest), broken
    m = ground & zone_bank & above_air
    rset(m, pick(SNOW, np.clip(0.3 + 0.12 * (n2[m] - 0.5), 0, 1)))                    # wind-scoured lips
    # wind drifts in the lee (north side) of buildings: lighter snow 1-3 north of a wall
    lee = np.zeros((512, 512), bool)
    for d in (1, 2, 3):
        lee[:, :-d] |= own[:, d:] > 0
    m = ground & above_air & lee[xs, ys] & (own[xs, ys] == 0) & (n1 < 0.8)
    rset(m, pick(SNOW, np.full(m.sum(), 0.88)))
    # village streets + front sled ruts: a trodden band
    paths = np.zeros((512, 512), bool)
    for key in ('north_village_street', 'south_village_street', 'front_lane'):
        P = S['routes'][key]['path']
        for (a, b) in zip(P, P[1:]):
            for (px, py, _) in line_points(a[0], a[1], 0, b[0], b[1], 0):
                w = 1 if key == 'front_lane' else 2
                for qx in (px, 512 - px):
                    if key == 'front_lane':
                        for off in (-3, 3):
                            paths[max(qx - w, 0):qx + w, py + off:py + off + 1] = True
                    else:
                        paths[max(qx - w, 0):qx + w + 1, max(py - w, 0):py + w + 1] = True
    m = ground & above_air & paths[xs, ys]
    rset(m, 0.6 * pick(STONE_WARM, np.clip(0.15 + 0.25 * n1[m], 0, 1)) + 0.4 * pick(SNOW, np.full(m.sum(), 0.12)))

    # ---------------------------------------------------------------- ice
    ice = (mat == M['ice']) | (mat == M.get('icerubble', -1))
    lv = lane[xs, ys]
    lz = (lv - lane.mean()) / max(lane.std(), 1e-6)
    t_ice = np.clip(0.5 + 0.3 * lz + (n1 - 0.5) * 0.1, 0, 1)
    rset(ice, pick(ICE, t_ice[ice]))
    # pressure cracks: 2-wide pale lines, low contrast, along a warped diagonal field
    warp = (xs * 0.7 + ys * 0.35 + 18 * fv)
    crack = ice & (np.abs((warp % 23) - 11.5) < 1.0) & (n2 < 0.8)
    rset(crack, pick(ICE_PALE, np.full(crack.sum(), 0.35)))
    dust = ice & above_air & (pv > 0.7)
    rset(dust, pick(SNOW, np.clip(0.45 + 0.3 * n1[dust], 0, 1)))
    rub = (mat == M.get('icerubble', -1))
    rset(rub, np.where(above_air[rub][:, None], pick(SNOW, 0.7 + 0.2 * n1[rub]), pick(ICE_PALE, 0.5 * n1[rub])))

    # ---------------------------------------------------------------- buildings
    bmat = np.isin(mat, [M[k] for k in ('building', 'roof', 'stair', 'furniture') if k in M])
    for tname, st in STYLE.items():
        tid = TYPES.index(tname)
        inb = bmat & (T == tid)
        if not inb.any():
            continue
        zf_t = zs[inb & is_role('floor')]
        zf0 = int(np.median(zf_t)) if len(zf_t) else 40
        wall = inb & is_role('wall', 'stone')
        c = st['courses']
        if c == 'log':
            t = 0.45 + 0.12 * ((zs % 2) * 2 - 1) + 0.15 * (n1 - 0.5)
        elif c == 'stone':
            blk = H3((xs + (zs // 2) % 2 * 2) // 3, (ys + (zs // 2) % 2 * 2) // 3, zs // 2, 5)
            t = 0.2 + 0.6 * blk
        elif c == 'stave':
            t = 0.45 + 0.12 * (((xs + ys) % 2) * 2 - 1) + 0.12 * (n1 - 0.5)
        elif c == 'lattice':
            beam = ((xs + zs) % 4 == 0) | ((ys + zs) % 4 == 0) | ((xs - zs) % 4 == 0) | ((ys - zs) % 4 == 0)
            t = np.where(beam, 0.15, 0.7) + 0.1 * (n1 - 0.5)
        else:
            t = 0.5 + 0.1 * (((xs // 1 + ys // 1) % 2) * 2 - 1) * 0.6 + 0.2 * (n1 - 0.5)
        rset(wall, pick(st['wall'], np.clip(t[wall], 0, 1)))
        if st.get('gable'):                                   # naust: timber gable triangles above the eaves
            g = wall & (zs < zf0 - 5)
            rset(g, pick(st['gable'], np.clip(0.4 + 0.2 * (n1[g] - 0.5), 0, 1)))
        if st['base']:
            b = wall & (zs >= zf0 - st['base']) & (zs < zf0)
            rset(b, pick(GRANITE, 0.25 + 0.5 * n2[b]))
        trim = inb & is_role('post', 'door_trim')
        rset(trim, pick(st['trim'], np.clip(0.5 + 0.3 * (n1[trim] - 0.5), 0, 1)))
        roof = inb & is_role('roof', 'ridge')
        if st['roof'] is TURF:
            t = 0.2 + 0.6 * rf[xs, ys] + 0.08 * (n1 - 0.5)
        elif tname == 'church':                                # shingle rows: alternate per course, offset joints
            t = 0.5 + 0.22 * ((zs % 2) * 2 - 1) - 0.1 * (((xs + ys + zs // 2) % 3) == 0) + 0.04 * (n1 - 0.5)
        else:
            t = 0.45 + 0.18 * ((zs % 2) * 2 - 1) + 0.12 * (n1 - 0.5)
        rset(roof, pick(st['roof'], np.clip(t[roof], 0, 1)))
        ridge = inb & is_role('ridge')
        rset(ridge, pick(st['roof'], np.full(ridge.sum(), 0.0)))
        # continuous snow on the upper slopes, thinning toward the eaves; shingle shows in 2-wide drip lines and
        # under the gable finials (no isolated patches)
        thr = 1.0 - st['snow'] + 0.08 * (rs_[xs, ys] - 0.5) + 0.3 * drip + 0.4 * (aend <= 1)
        snowy = roof & above_air & (frac >= thr)
        rset(snowy, pick(SNOW_ROOF, np.clip(0.35 + 0.45 * frac[snowy] + 0.08 * (n1[snowy] - 0.5), 0, 1)))
        fl = inb & is_role('floor')
        rset(fl, pick(PLANK, np.clip(0.45 + 0.15 * (((xs + ys * 0) % 2) * 2 - 1) + 0.1 * (n1[...] - 0.5), 0, 1)[fl]))
        stv = inb & is_role('stair')
        rset(stv, pick(PLANK, np.clip(0.7 + 0.2 * (n1[stv] - 0.5), 0, 1)))
        fu = inb & is_role('furniture')
        rset(fu, pick(TAR, np.clip(0.6 + 0.3 * (n1[fu] - 0.5), 0, 1)))
        hs = inb & is_role('stone') & (mat == M['furniture'])
        rset(hs, pick(GRANITE, 0.3 + 0.4 * n1[hs]))
    gid = TYPES.index('gate')
    gs = bmat & (T == gid) & is_role('stone')
    course = ((zs // 2) % 2 == 0)
    blk = H3((xs + course * 2) // 4, ys // 4, zs // 2, 7)
    rset(gs, pick(GRANITE, np.clip(0.3 + 0.35 * blk[gs] + 0.12 * course[gs], 0, 1)))
    frieze = gs & np.isin(ys, (98, 106)) & (zs >= 21) & (zs <= 25) & (xs >= 234) & (xs <= 278)
    rset(frieze, pick(SLATE, 0.15 + 0.2 * n1[frieze]))
    vous = gs & ~cv.solid[xs, ys, np.minimum(zs + 1, 63)] & (xs >= 234) & (xs <= 278)
    rset(vous, pick(GRANITE, np.where(((xs[vous] // 2) % 2) == 0, 0.85, 0.55)))
    quoin = gs & ((xs == 222) | (xs == 233) | (xs == 279) | (xs == 290)) & ((zs // 2) % 2 == 0)
    rset(quoin, pick(GRANITE, np.full(quoin.sum(), 0.9)))
    gsn = gs & above_air & (n2 < 0.5)
    rset(gsn, pick(SNOW_ROOF, 0.4 + 0.3 * n1[gsn]))
    # ---------------------------------------------------------------- hulls, rock, landmarks, props
    hull = mat == M.get('hull', -1)
    if hull.any():
        h_t = 0.4 + 0.18 * (((zs + (xs // 7)) % 2) * 2 - 1) + 0.1 * (n1 - 0.5)
        rset(hull & is_role('hull'), pick(HULL, np.clip(h_t[hull & is_role('hull')], 0, 1)))
        dk = hull & is_role('deck')
        rset(dk, pick(PLANK, np.clip((0.4 + 0.1 * (((xs // 2) % 2) * 2 - 1) + 0.1 * n1)[dk], 0, 1)))
        cvs = hull & is_role('canvas')
        stripe = ((ys // 2) % 2 == 0)
        rset(cvs, np.where(stripe[cvs][:, None], np.array([[142, 54, 46]]), np.array([[168, 156, 130]])) *
             (0.92 + 0.1 * n1[cvs])[:, None])
        rset(hull & is_role('mast'), pick(TAR, 0.6 + 0.2 * n1[hull & is_role('mast')]))
        rset(hull & is_role('furniture'), pick(PLANK, 0.3 + 0.2 * n1[hull & is_role('furniture')]))
        gun = hull & is_role('hull') & above_air
        rset(gun, pick(OCHRE, 0.3 + 0.2 * n1[gun]) * 0.8)
    rock = (mat == M.get('rock', -1)) & ~is_role('rune')
    rset(rock, pick(TURF, np.where(rf[xs[rock], ys[rock]] < 0.5, 0.25, 0.45)))         # turf barrow, 2 tones
    rs = rock & above_air & (rf[xs, ys] > 0.35)
    rset(rs, pick(SNOW, np.where(rf[xs[rs], ys[rs]] > 0.55, 0.7, 0.55)))
    rtid = TYPES.index('rock')
    portal = bmat & (T == rtid)
    rset(portal, pick(GRANITE, np.where(((zs[portal] // 2) % 2) == 0, 0.35, 0.6)))
    stone = np.isin(mat, [M.get(k, -1) for k in ('stone', 'kerb', 'altar')])
    blk = H3((xs + (zs // 2) % 2 * 2) // 3, (ys + (zs // 2) % 2 * 2) // 3, zs // 2, 6)
    rset(stone, pick(GRANITE, 0.15 + 0.7 * blk[stone]))
    ss = stone & above_air & (n2 < 0.5)
    rset(ss, pick(SNOW, 0.5 + 0.3 * n1[ss]))
    # rune role (lawspeaker rock, rune stones, offering stones): dark stone + painted serpent bands
    rune = is_role('rune')
    rset(rune, pick(GRANITE, 0.15 + 0.3 * n1[rune]))
    law = rune & (mat == M.get('rock', -1))
    rset(law, pick(GRANITE, np.where(((zs[law] + xs[law]) % 3) == 0, 0.45, 0.65)))
    serp = law & ~above_air & (np.abs(zs - (31 + np.rint(np.sin((xs * 0.9 + ys * 0.6) / 1.6)))) < 0.5)
    rset(serp, np.where(((xs[serp] + ys[serp]) % 4 < 2)[:, None], np.array([[150, 50, 40]]), np.array([[180, 132, 60]])))
    band = rune & ~above_air & ((zs + (xs + ys) // 2) % 5 == 0)
    rset(band, np.where((n2[band] < 0.5)[:, None], np.array([[134, 50, 40]]), np.array([[164, 116, 56]])))
    pyre = mat == M.get('pyre', -1)
    rset(pyre & is_role('log'), pick(LOG, 0.3 + 0.4 * n1[pyre & is_role('log')]))
    char = pyre & is_role('log') & (n2 < 0.25)
    rset(char, pick(TAR, 0.05 + 0.1 * n1[char]))
    sle = mat == M.get('sleipnir', -1)
    rset(sle & is_role('straw'), pick(STRAW, 0.35 + 0.4 * n1[sle & is_role('straw')]))
    rset(sle & is_role('log'), pick(TAR, 0.4 + 0.3 * n1[sle & is_role('log')]))
    hay = is_role('hay')
    rset(hay, pick(STRAW, np.clip(0.3 + 0.4 * n1[hay], 0, 1)))
    hsn = hay & above_air & (n2 < 0.45)
    rset(hsn, pick(SNOW, 0.6 + 0.2 * n1[hsn]))
    prop = (mat == M.get('prop', -1))
    pc = H3(xs // 2, ys // 2, 0, 12)
    choices = np.array([TAR[2], PLANK[2], (124, 52, 42), (78, 86, 98), STRAW[2], LOG[3]], float)
    pr = prop & is_role('prop', 'log', 'post', 'roof', 'stone', 'rune')
    rset(prop & is_role('straw'), pick(STRAW, 0.5 + 0.3 * n1[prop & is_role('straw')]))
    rset(pr, choices[(pc[pr] * len(choices)).astype(int) % len(choices)] * (0.9 + 0.15 * n1[pr])[:, None])
    rset(prop & is_role('post'), pick(TAR, 0.35 + 0.3 * n1[prop & is_role('post')]))
    psn = prop & above_air & (n2 < 0.4) & ~is_role('post')
    rset(psn, pick(SNOW, 0.55 + 0.25 * n1[psn]))
    ant = is_role('antler')
    rset(ant, pick(BONE, 0.3 + 0.5 * n1[ant]))

    # ---------------------------------------------------------------- vegetation
    leaf = mat == M.get('leaf', -1)
    lr = cv.rgb[idx].astype(int)
    birch = leaf & (lr[:, 1] - lr[:, 2] > 30) & (lr[:, 0] > 100)
    conif = leaf & ~birch
    rset(conif, np.where((n2[conif] < 0.6)[:, None], pick(SPRUCE, np.clip(0.2 + 0.6 * n1[conif] + 0.1 * (fv[conif] - 0.5), 0, 1)),
                         pick(PINE, np.clip(0.2 + 0.6 * n1[conif], 0, 1))))
    rset(birch, pick(BIRCH_TWIG, np.clip(0.2 + 0.6 * n1[birch], 0, 1)))
    load = leaf & above_air & (H3(xs // 2, ys // 2, zs, 21) < 0.62)
    rset(load, pick(SNOW, np.clip(0.55 + 0.35 * n1[load], 0, 1)))
    bark = mat == M.get('bark', -1)
    rset(bark, pick(TAR, np.clip(0.4 + 0.4 * n1[bark], 0, 1)))
    for k, rgbv in (('moss', (88, 100, 74)), ('vine', (50, 70, 56)), ('nest', (96, 76, 58)), ('fruit', (156, 38, 40)),
                    ('blossom', (176, 182, 196)), ('mushroom', (150, 92, 70)), ('ribbon', (150, 40, 44)),
                    ('deadwood', (104, 94, 86)), ('iron', (60, 56, 52))):
        mm = mat == M.get(k, -1)
        rset(mm, np.array([rgbv]) * (0.92 + 0.12 * n1[mm])[:, None])

    cv.rgb[idx] = np.clip(np.rint(out), 0, 255).astype(np.uint8)
    report['recoloured_surface_voxels'] = int(len(xs))
    return role, names, idx


# ================================================================== glow (on existing voxels: no geometry)
def glow_pass(cv, role, names, idx, structs):
    rn = {n: i for i, n in enumerate(names)}
    xs, ys, zs = idx
    mat = cv.mat[idx]
    M = cv.materials
    counts = {}

    def g(name, m, col):
        for (x, y, z) in zip(xs[m], ys[m], zs[m]):
            cv.add_glow(int(x), int(y), int(z), col)
        counts[name] = counts.get(name, 0) + int(m.sum())

    own = owner_map(structs)
    T = own[xs, ys]
    S_ = cv.solid
    # window sills: wall voxel under a through-wall hole with wall/roof above it (doors excluded: floor below)
    wallish = np.isin(role, [rn['wall'], rn['stone'], rn['post']]) & (T > 0)
    up = np.maximum(zs - 1, 0)
    hole = ~S_[xs, ys, up]
    lint = S_[xs, ys, np.maximum(zs - 3, 0)] | S_[xs, ys, np.maximum(zs - 4, 0)]
    thru_x = ~S_[np.clip(xs - 1, 0, 511), ys, up] & ~S_[np.clip(xs + 1, 0, 511), ys, up]
    thru_y = ~S_[xs, np.clip(ys - 1, 0, 511), up] & ~S_[xs, np.clip(ys + 1, 0, 511), up]
    side_y = S_[xs, np.clip(ys - 1, 0, 511), up] | S_[xs, np.clip(ys + 1, 0, 511), up]
    side_x = S_[np.clip(xs - 1, 0, 511), ys, up] | S_[np.clip(xs + 1, 0, 511), ys, up]
    sill = wallish & hole & lint & ((thru_x & side_y) | (thru_y & side_x)) 
    gate = T == TYPES.index('gate')
    church = T == TYPES.index('church')
    g('window sills (amber)', sill & ~gate & ~church, GLOW['window_amber'])
    g('church window candles', sill & church, GLOW['candle'])
    # hearths and the forge: every other top voxel of stone furniture
    hearth = (mat == M['furniture']) & (role == rn['stone']) & ~S_[xs, ys, up] & ((xs + ys) % 2 == 0)
    g('hearths and forges', hearth, GLOW['hearth'])
    fire = role == rn['fire']
    g('pyre core, forge and beacon baskets', fire, GLOW['pyre'])
    # pyre embers on log ends
    emb = (mat == M.get('pyre', -1)) & (role == rn['log']) & (H3(xs, ys, zs, 41) < 0.07)
    g('pyre embers', emb, (255, 120, 40))
    # Raven Gate runes: glyph clusters on the arch faces (y 98 / 106) at z 22-24, every 6 columns; soffit lights
    gx = (T == TYPES.index('gate')) & np.isin(ys, (98, 106)) & (zs >= 22) & (zs <= 24) & ((xs % 10) < 2) & \
        (H3(xs, zs, ys, 43) < 0.75) & (xs >= 234) & (xs <= 278)
    g('Raven Gate runes', gx, GLOW['rune_blue'])
    soff = (T == TYPES.index('gate')) & ~S_[xs, ys, np.minimum(zs + 1, 63)] & (xs >= 234) & (xs <= 278) & \
        ((xs % 8) == 0) & (ys == 102)
    g('Raven Gate soffit runes', soff, GLOW['rune_blue'])
    leg = (T == TYPES.index('gate')) & ((xs <= 233) | (xs >= 279)) & (zs % 8 == 0) & ((ys % 6) == 1) & \
        (H3(xs, ys, zs, 44) < 0.5)

    # Lawspeaker's rock carved runes + a few on the rune stones
    rune = role == rn['rune']
    lr = rune & (mat == M['rock']) & ((zs + xs + ys) % 3 == 0) & (H3(xs, ys, zs, 45) < 0.12)
    g("Lawspeaker's rock runes", lr, GLOW['rune_blue'])
    rr = rune & (mat == M.get('stone', -1)) & (H3(xs, ys, zs, 46) < 0.08)
    g('rune stones', rr, GLOW['rune_blue'])
    # church candles: top of the altar table + benches ends; wreath berries above every lintel middle
    alt = (mat == M['furniture']) & (T == TYPES.index('church')) & ~S_[xs, ys, up] & (role == rn['furniture'])
    g('church candles', alt & (H3(xs, ys, zs, 47) < 0.5), GLOW['candle'])
    lin = (role == rn['door_trim'])
    lm = lin & S_[np.clip(xs - 1, 0, 511), ys, zs] & S_[np.clip(xs + 1, 0, 511), ys, zs] & \
        ~S_[xs, ys, np.minimum(zs + 1, 63)]
    lm |= lin & S_[xs, np.clip(ys - 1, 0, 511), zs] & S_[xs, np.clip(ys + 1, 0, 511), zs] & \
        ~S_[xs, ys, np.minimum(zs + 1, 63)]
    # the wall voxel just above a lintel middle -> wreath berry (red glow), its neighbours green
    n = 0
    gate_t = TYPES.index('gate')
    for (x, y, z, tt) in zip(xs[lm], ys[lm], zs[lm], T[lm]):
        if tt == gate_t:
            continue
        if cv.solid[x, y, z - 1]:
            cv.rgb[x, y, z - 1] = (168, 40, 40)
            for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if cv.solid[x + dx, y + dy, z - 1]:
                    cv.rgb[x + dx, y + dy, z - 1] = (44, 88, 58)
            if cv.solid[x, y, z - 2]:
                cv.rgb[x, y, z - 2] = (44, 88, 58)
            n += 1
    counts['door wreath berries'] = n
    dt = np.zeros(S_.shape, bool)
    dt[xs[lin], ys[lin], zs[lin]] = True
    X1, Y1 = np.clip(xs + 1, 0, 511), np.clip(ys + 1, 0, 511)
    X0, Y0 = np.clip(xs - 1, 0, 511), np.clip(ys - 1, 0, 511)
    Zb = np.minimum(zs + 1, 63)
    corner = lin & dt[xs, ys, Zb] & (dt[X0, ys, zs] | dt[X1, ys, zs] | dt[xs, Y0, zs] | dt[xs, Y1, zs]) & (T != gate_t)
    g('door wreath candles', corner, GLOW['candle'])
    # Yule string lights under the eaves: overhang ring of each house (reg box minus the wall box), every 2nd voxel,
    # red / gold / amber in turn (dots, not stripes; hidden from above by the roof)
    k = 0
    lights = [GLOW['string_light_red'], GLOW['string_light_gold'], GLOW['window_amber']]
    for s_ in structs:
        t = type_of(s_['name'])
        if t not in ('mead', 'smithy', 'shed', 'longhouse', 'bath', 'church', 'lodge', 'hut', 'byre'):
            continue
        x0, x1, y0, y1 = s_['box']
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                if x0 < x < x1 and y0 < y < y1:
                    continue
                if (x + y) % 2:
                    continue
                col = cv.solid[x, y]
                if not col.any():
                    continue
                z = int(np.argmax(col))
                if cv.materials.get('roof') != cv.mat[x, y, z]:
                    continue
                zz = z
                while zz < 62 and cv.solid[x, y, zz + 1]:
                    zz += 1
                if zz < 62 and not cv.solid[x, y, zz + 1] and not cv.solid[x, y, zz + 2]:
                    cv.add_glow(x, y, zz, lights[k % 3])
                    k += 1
    counts['eave string lights'] = k
    gun = (mat == M.get('hull', -1)) & (role == rn['hull']) & ~S_[xs, ys, up] & ((xs % 4) == 0) & (zs <= 38)
    g('longship gunwale lanterns', gun, GLOW['window_amber'])
    # candles on tables and benches in every house, tea lights on the rune-ring kerb, braziers on the gate merlons
    furn = (mat == M['furniture']) & (role == rn['furniture']) & ~S_[xs, ys, up] & (T > 0) &         (T != TYPES.index('church')) & (H3(xs, ys, zs, 49) < 0.4)
    g('table and bench candles', furn, GLOW['candle'])
    kerb = (mat == M.get('kerb', -1)) & ~S_[xs, ys, up] & (H3(xs, ys, zs, 50) < 0.3)
    g('rune ring tea lights', kerb, GLOW['candle'])
    mer = (T == TYPES.index('gate')) & ~S_[xs, ys, up] & np.isin(ys, (98, 106)) & (zs <= 15) & (xs % 6 == 0)
    g('Raven Gate merlon braziers', mer, GLOW['hearth'])
    # beacon iron baskets: voxels next to fire -> iron
    # Sleipnir lantern eyes
    for (x, y, z) in ():
        if cv.solid[x, y, z]:
            cv.add_glow(x, y, z, GLOW['window_amber'])
            counts['Sleipnir lantern eyes'] = counts.get('Sleipnir lantern eyes', 0) + 1
    # ornaments on forest trees near the lodges, church and beacons (decorated Yule trees)
    leafm = (mat == M.get('leaf', -1)) & ~S_[xs, ys, up]
    near = np.zeros((512, 512), bool)
    for s in structs:
        t = type_of(s['name'])
        if t in ('lodge', 'church', 'beacon', 'mead', 'longhouse'):
            x0, x1, y0, y1 = s['box']
            near[max(0, x0 - 16):x1 + 17, max(0, y0 - 16):y1 + 17] = True
    orn = leafm & near[xs, ys] & (H3(xs, ys, zs, 48) < 0.10)
    cols = [GLOW['string_light_red'], GLOW['string_light_gold']]
    k = 0
    for (x, y, z) in zip(xs[orn], ys[orn], zs[orn]):
        cv.add_glow(int(x), int(y), int(z), cols[k % 2])
        k += 1
    counts['tree ornaments'] = k
    return counts


# ================================================================== sky decor
RAVEN = ['.......#.......',
         '......###......',
         '###.#######.###',
         '.#############.',
         '..##..###..##..',
         '......#.#......']


def _raven(target, x, y, z, heading):
    return sky.stamp(target, RAVEN, x, y, z, heading, {'#': (52, 50, 60)})


def _sleigh_team(target, x, y, z):
    """Yule-rider sleigh pulled by 6 generic reindeer (3 pairs), heading north (-y). One connected piece."""
    pts = []

    def s(px, py, pz, c):
        target.set(px, py, pz, c, 'sky')
        pts.append((px, py, pz))
    fur, ant, rein = (120, 92, 70), (176, 160, 130), (120, 40, 36)
    for k in range(3):
        y0 = y + k * 6
        for dx in (-2, 2):
            for j in range(4):
                s(x + dx, y0 + j, z, fur)                       # body
            s(x + dx, y0, z - 1, fur)                           # neck
            s(x + dx, y0 - 1, z - 1, fur)                       # head
            s(x + dx, y0, z - 2, ant)                           # antlers
            s(x + dx - 1, y0, z - 2, ant)
            s(x + dx + 1, y0, z - 2, ant)
            s(x + dx - 1, y0, z - 3, ant)
            s(x + dx + 1, y0, z - 3, ant)
            for j in (0, 3):
                s(x + dx, y0 + j, z + 1, fur)                   # legs (in stride)
        for dx in range(-2, 3):                                 # yoke
            s(x + dx, y0 + 2, z, rein)
        for j in range(6):                                      # reins along the centre line
            s(x, y0 + 2 + j, z, rein)
    ys0 = y + 3 * 6 + 2
    for dx in range(-2, 3):                                     # sleigh body
        for j in range(7):
            s(x + dx, ys0 + j, z, (128, 40, 36))
            if abs(dx) == 2 or j == 6:
                s(x + dx, ys0 + j, z - 1, (128, 40, 36))
                if j == 6:
                    s(x + dx, ys0 + j, z - 2, (128, 40, 36))
        for j in range(-1, 8):
            if abs(dx) == 2:
                s(x + dx, ys0 + j, z + 1, (176, 136, 70))       # gilded runners
    s(x - 2, ys0 - 2, z, (176, 136, 70))
    s(x + 2, ys0 - 2, z, (176, 136, 70))
    for dx in (-1, 0, 1):                                       # gift sack
        for j in (3, 4, 5):
            s(x + dx, ys0 + j, z - 1, (110, 84, 60))
    s(x, ys0 + 4, z - 2, (110, 84, 60))
    return pts


def _aurora(target, x, y, z, length, phase, cols):
    pts = []
    prev = None
    for i in range(length):
        px = x + i
        py = int(round(y + 3 * math.sin(i / 9.0 + phase)))
        c = cols[(i // 6) % len(cols)]
        cand = [(px, py)]
        if prev and prev[1] != py:
            cand = [(px, prev[1]), (px, py)]
        for (qx, qy) in cand:
            for dz in (0, 1):
                target.set(qx, qy, z + dz, c, 'sky')
                pts.append((qx, qy, z + dz))
        prev = (px, py)
    return pts


def sky_decor(cv):
    recs = []
    # crescent moon over the north fjord (kept <= 212 so it is not "too white")
    recs.append(sky.place(cv, 'crescent moon', sky.moon, 256, 34, 16, R=14.0, r=12.0, offset=6.0,
                          body=(206, 200, 176), rim=(212, 208, 186), dark=(176, 170, 150)))
    recs.append(sky.place(cv, 'raven A', _raven, 244, 78, 5, 0.6))
    recs.append(sky.place(cv, 'raven B', _raven, 268, 122, 5, -2.4))
    recs.append(sky.place(cv, 'Yule-rider sleigh with 6 reindeer', _sleigh_team, 256, 404, 14))
    cols = [(90, 230, 190), (120, 240, 170), (100, 214, 210)]
    for (x0, y0, ph) in ((124, 6, 0.0), (176, 8, 1.3), (232, 5, 2.1), (300, 7, 0.7), (352, 6, 2.8),
                         (124, 504, 1.0), (180, 502, 2.2), (240, 505, 0.4), (296, 503, 1.7), (350, 504, 2.9)):
        for (dx, dy) in ((0, 0), (0, 2 if y0 < 256 else -2), (8, 0), (-8, 0), (0, 4 if y0 < 256 else -4), (16, 0)):
            try:
                recs.append(sky.place(cv, 'aurora ribbon', _aurora, x0 + dx, y0 + dy, 0, 46, ph, cols))
                break
            except RuntimeError:
                continue
    # aurora + moon rim glow (sources keep their colour; the rest of the sky is plain colour)
    n = 0
    for r in recs:
        if r['name'] == 'aurora ribbon':
            for x in range(r['x'][0], r['x'][1] + 1):
                for y in range(r['y'][0], r['y'][1] + 1):
                    for z in range(r['z'][0], r['z'][1] + 1):
                        if cv.solid[x, y, z] and cv.mat[x, y, z] == cv.materials['sky']:
                            cv.add_glow(x, y, z, tuple(int(v) for v in cv.rgb[x, y, z]))
                            n += 1
    for r in recs:
        if r['name'] == 'crescent moon':
            for x in range(r['x'][0], r['x'][1] + 1):
                for y in range(r['y'][0], r['y'][1] + 1):
                    for z in range(r['z'][0], r['z'][1] + 1):
                        if cv.solid[x, y, z] and cv.mat[x, y, z] == cv.materials['sky'] and (x + z) % 3 == 0:
                            cv.add_glow(x, y, z, (212, 206, 170))
                            n += 1
    for r in recs:
        if r['name'] == 'Yule-rider sleigh with 6 reindeer':
            cv.add_glow(r['x'][0] + 2, r['y'][0] + 18 + 2 - 2, r['z'][1], GLOW['window_amber']) \
                if cv.solid[r['x'][0] + 2, r['y'][0] + 18, r['z'][1]] else None
    return recs, n


# ================================================================== main entry
# ================================================================== G4 round 2: hero pieces and yards
def _soffit(x):
    u = (256 - x) / 23.0
    return int(round(41 - 11 * math.sqrt(max(0.0, 1 - u * u))))


def gate_arch(A, cv):
    """Raven Gate: voussoir ring proud of both faces, keystone (on the face and raised on the parapet), battered
    legs, and a large carved raven (>= 9 tall, half-open wings, beak to the north / the fjord) on each leg cap."""
    v_light, v_mid = tuple(int(c) for c in GRANITE[4]), tuple(int(c) for c in GRANITE[2])
    for x in range(234, 257):
        so = _soffit(x)
        for yf in (97, 107):
            for k in range(3):
                c = v_light if ((x // 2) % 2 == 0) else v_mid
                A.put('Raven Gate voussoirs and keystone', x, yf, so - k, c, mirror=(x != 256))
    for x in (254, 255, 256):
        for (yf, yo) in ((97, 96), (107, 108)):
            for z in range(25, 32):
                A.put('Raven Gate voussoirs and keystone', x, yf, z, v_light, mirror=(x != 256))
            for z in range(26, 31):
                A.put('Raven Gate voussoirs and keystone', x, yo, z, v_mid, mirror=(x != 256))
        for y in (98, 106):
            for z in range(12, 17):
                A.put('Raven Gate voussoirs and keystone', x, y, z, v_light, mirror=(x != 256))
    # battered legs (west leg authored, mirrored): wedges on the outer face and on the N / S faces beside the doors
    lx0, lx1, ly0, ly1 = S['raven_gate']['legs'][0]
    for (x, ztop) in ((lx0 - 1, 30), (lx0 - 2, 35), (lx0 - 3, 38)):
        for y in range(ly0, ly1 + 1):
            g = top_at(cv, x, y)
            for z in range(ztop, g):
                A.put('Raven Gate battered legs', x, y, z, v_mid)
    for (dy, ztop) in ((1, 31), (2, 36)):
        for y in (ly0 - dy, ly1 + dy):
            for x in list(range(lx0 - dy + 1, lx0 + 4)) + list(range(lx0 + 7, lx1 + 1)):
                g = top_at(cv, x, y)
                for z in range(ztop, g):
                    A.put('Raven Gate battered legs', x, y, z, v_mid)
    # large carved ravens on the leg caps
    cx, cy = lx0 + 2, ly1 - 2
    b = top_at(cv, cx, cy) - 1
    blk = (52, 50, 60)
    beak = (96, 88, 72)

    def r(x, y, z, c=blk):
        A.put('Raven Gate carved ravens', x, y, z, c)
    for z in range(b - 4, b + 1):                          # body
        for x in range(cx - 1, cx + 2):
            for y in range(cy - 1, cy + 2):
                r(x, y, z)
    for z in range(b - 6, b - 3):                          # chest / neck
        for x in range(cx - 1, cx + 2):
            for y in (cy - 2, cy - 1):
                r(x, y, z)
    for z in range(b - 8, b - 5):                          # head
        for x in range(cx - 1, cx + 2):
            for y in (cy - 3, cy - 2):
                r(x, y, z)
    r(cx, cy - 4, b - 7, beak)
    r(cx, cy - 5, b - 7, beak)
    r(cx, cy - 4, b - 6, beak)
    for (x, y, z) in ((cx, cy + 2, b), (cx, cy + 3, b), (cx, cy + 3, b + 1)):
        r(x, y, z)                                           # tail
    for side in (-1, 1):                                   # half-open wings, raised and swept back
        for i in range(1, 6):
            x = cx + side * (1 + i)
            for z in range(b - 4 - (i + 1) // 2, b - 1 - i // 3):
                for y in ((cy, cy + 1) if i < 4 else (cy + 1,)):
                    r(x, y, z)
    A.put('Raven Gate carved ravens', cx - 1, cy - 4, b - 7, GLOW['rune_blue'], glow=True)
    A.put('Raven Gate carved ravens', cx + 1, cy - 4, b - 7, GLOW['rune_blue'], glow=True)


def gate_runes(cv):
    """Rune-glow bands down the leg faces (dark slate band, glyph glows every 2 rows). Colour only."""
    lx0, lx1, ly0, ly1 = S['raven_gate']['legs'][0]
    band_c = tuple(int(c) for c in SLATE[0])
    n = 0
    spots = [(x, y) for x in (lx1 - 3, lx1 - 2) for y in (ly0, ly1)] + [(lx0, y) for y in (ly0 + 5, ly0 + 6)]
    for (x, y) in spots:
        for xx in (x, 512 - x):
            for z in range(19, 31):
                if cv.solid[xx, y, z]:
                    cv.rgb[xx, y, z] = band_c
                    if z % 2 == 0 and (z // 2 + x) % 2 == 0:
                        cv.add_glow(xx, y, z, GLOW['rune_blue'])
                        n += 1
    return n


def sleipnir_rebuild(A, cv):
    """Sleipnir as an eight-legged straw-and-timber horse facing north, inside its box (x 246-266, y 440-458)."""
    sm = cv.materials.get('sleipnir')
    for x in range(244, 269):
        for y in range(432, 464):
            for z in range(20, 43):
                if cv.mat[x, y, z] == sm:
                    A.remove('Sleipnir rebuilt', x, y, z)
    straw = [tuple(int(c) for c in STRAW[k]) for k in range(5)]
    timber, lash = tuple(int(c) for c in TAR[2]), tuple(int(c) for c in STRAW[3])
    red, ochre = (140, 46, 40), (176, 128, 58)

    def p(x, y, z, c):
        A.put('Sleipnir rebuilt', x, y, z, c, mirror=(x != 256))
    for x in range(252, 257):                              # barrel body, belly lifted
        for y in range(443, 458):
            for z in range(29, 35):
                d = ((x - 256) / 4.2) ** 2 + ((y - 450) / 7.2) ** 2 + ((z - 32) / 2.6) ** 2
                if d <= 1.0:
                    c = straw[2 + int(H3(x, y, z, 70) * 2)]
                    if z <= 30 and 447 <= y <= 452:          # saddle blanket with knotwork trim
                        trim = y in (447, 452) or abs(x - 256) == 3 or ((x + y) % 3 == 0 and y in (448, 451))
                        c = ochre if trim else red
                    p(x, y, z, c)
    for (y, zt, zb) in ((444, 27, 31), (443, 26, 31), (442, 25, 29), (441, 24, 28)):   # short thick arched neck
        for x in (254, 255, 256):
            for z in range(zt, zb + 1):
                p(x, y, z, straw[3])
        p(256, y, zt - 1, straw[1])                        # straw mane
        p(255, y, zt - 1, straw[1])
    for x in (255, 256):                                   # heavy head with a deep jaw, muzzle down
        for y in range(436, 441):
            for z in range(23, 27):
                p(x, y, z, straw[3] if z < 26 else straw[4])
        for y in range(437, 441):
            p(x, y, 27, straw[4])                          # jaw
        p(x, 435, 25, timber)
        p(x, 435, 26, timber)
    p(255, 440, 22, straw[1])                              # ears
    A.put('Sleipnir rebuilt', 254, 437, 24, GLOW['window_amber'], glow=True)   # lantern eyes (mirrored to 258)
    for y in (445, 448, 452, 455):                         # four pairs of legs, spread chest to hip
        for z in range(34, 43):
            p(254, y, z, lash if z % 3 == 0 else timber)
        p(254, y, 33, timber)
    for (y, z) in ((458, 32), (459, 32), (459, 33), (460, 33), (460, 34), (460, 35), (460, 36)):   # straw tail
        A.put('Sleipnir rebuilt', 256, y, z, straw[2], mirror=False)


def church_tiers(A, cv):
    """Stave church: two stacked, diminishing pent roofs round the west tower (above the svalgang) and dragon
    heads at the upper tier's corners -> the classic stepped silhouette. Additive, outside the walls."""
    tx0, tx1, ty0, ty1 = 138, 146, 80, 88
    zf = int(np.median(cv.H[147:158, 78:91]))
    zl = zf - 10
    sh = tuple(int(c) for c in SHINGLE_CHURCH[2])
    for (zt, dmax) in ((zf - 8, 2), (zl, 1)):
        for d in range(1, dmax + 1):
            ring = [(tx0 - d, y) for y in range(ty0 - d, ty1 + d + 1)]
            ring += [(x, y) for x in range(tx0 - d + 1, tx1) for y in (ty0 - d, ty1 + d)]
            for (x, y) in ring:
                for k in (0, 1):
                    A.put('stave church pent roofs', x, y, zt + d - 1 + k, sh)
    head = tuple(int(c) for c in TAR[1])
    for (x, y, dx, dy) in ((tx0 - 1, ty0 - 1, -1, -1), (tx0 - 1, ty1 + 1, -1, 1)):
        z = zl - 1
        A.put('stave church pent roofs', x, y, z, head)
        A.put('stave church pent roofs', x + dx, y, z, head)
        A.put('stave church pent roofs', x + dx, y + dy, z, head)
        A.put('stave church pent roofs', x + dx, y + dy, z - 1, head)
        A.put('stave church pent roofs', x + 2 * dx, y + dy, z - 1, head)
        A.put('stave church pent roofs', x + 2 * dx, y + dy, z - 2, (255, 150, 60), glow=True)


def church_clerestory(A, cv):
    """Clerestory tier over the nave: short walls above the nave ridge with their own steep gable roof (pitch 1,
    ridge along x), blind arcading posts and dragon heads on its gables. Additive above the nave roof."""
    x0, x1, y0, y1, ze = 149, 155, 82, 86, 8
    wall, post, roof = FC['wall'], FC['post'], FC['roof']
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            if not (x in (x0, x1) or y in (y0, y1)):
                continue
            for z in range(ze, top_at(cv, x, y)):
                arc = (y in (y0, y1) and (x - x0) % 2 == 1 and z == ze + 1) or (x in (x0, x1) and y == 84 and z == ze + 1)
                A.put('stave church clerestory', x, y, z, post if arc else wall, 'building')
    rx0, rx1, ry0, ry1 = x0 - 1, x1 + 1, y0 - 1, y1 + 1
    for x in range(rx0, rx1 + 1):
        for y in range(ry0, ry1 + 1):
            t = min(y - ry0, ry1 - y)
            z = ze - t
            for k in ((0, 1) if t > 0 else (0,)):
                A.put('stave church clerestory', x, y, z + k, roof, 'roof')
            if x in (x0, x1):
                for zz in range(z + 2, ze):
                    A.put('stave church clerestory', x, y, zz, wall, 'building')
    head = tuple(int(c) for c in TAR[1])
    for (xe, d) in ((rx0, -1), (rx1, 1)):
        zt = ze - 3
        A.put('stave church clerestory', xe + d, 84, zt, head)
        A.put('stave church clerestory', xe + 2 * d, 84, zt, head)
        A.put('stave church clerestory', xe + 2 * d, 84, zt - 1, head)
        A.put('stave church clerestory', xe + 3 * d, 84, zt - 1, head)
        A.put('stave church clerestory', xe + 3 * d, 84, zt - 2, (255, 150, 60), glow=True)


def lawspeaker(A, cv):
    for x in (255, 256):
        for y in (255, 256, 257):
            for z in (28, 29):
                A.put('Lawspeaker rock raised', x, y, z, tuple(int(c) for c in GRANITE[3]), mirror=(x != 256))


def _forbidden(cv):
    f = np.zeros((512, 512), bool)
    tz, an = S['tower_zone']['blue'], S['anchor']['blue']
    for (x0, x1, y0, y1) in (S['spawn_no_prop'], S['front'], S['ctf_strip']['blue'],
                             [tz[0], an[1] + 2, an[2] - 4, an[3] + 4]):
        f[x0:x1 + 1, y0:y1 + 1] = True
        f[512 - x1:512 - x0 + 1, y0:y1 + 1] = True
    for key in ('north_village_street', 'south_village_street'):
        P = S['routes'][key]['path']
        for (a, b) in zip(P, P[1:]):
            for (px, py, _) in line_points(a[0], a[1], 0, b[0], b[1], 0):
                for qx in (px, 512 - px):
                    f[max(qx - 3, 0):qx + 4, max(py - 3, 0):py + 4] = True
    return f


def yards(A, cv, rng):
    """Silverpine-bar yards at the mead hall, longhouse and church: framing trees, woodpiles, sledges, drying racks.
    Placed only on free, flat ground off routes, doorways, spawns, the front and the tower zones."""
    from aosmap.kit import veg
    forb = _forbidden(cv)
    doors = [(155, 174), (180, 160), (130, 160), (159, 306), (180, 319), (152, 93), (136, 86), (134, 328)]

    why = []

    def free(x0, x1, y0, y1, slope=1):
        if x0 < 1 or y0 < 1 or x1 > 255 or y1 > 510 or forb[x0:x1 + 1, y0:y1 + 1].any():
            why.append((x0, y0, 'forbidden'))
            return False
        if any(abs((x0 + x1) / 2 - a) < 6 and abs((y0 + y1) / 2 - b) < 6 for a, b in doors):
            why.append((x0, y0, 'door'))
            return False
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                if top_at(cv, x, y) != int(cv.H[x, y]) or cv.mat[x, y, int(cv.H[x, y])] != cv.materials['ground']:
                    why.append((x0, y0, 'occupied', x, y))
                    return False
        sub = cv.H[x0:x1 + 1, y0:y1 + 1]
        if int(sub.max()) - int(sub.min()) > slope:
            why.append((x0, y0, 'slope'))
            return False
        return True
    n = {'trees': 0, 'props': 0}
    spruce = [(40, 66, 52), (50, 80, 58), (62, 92, 68)]
    def search(x, y, rx, ry, slope):
        for r in range(0, 7):
            for dx in range(-r, r + 1):
                for dy in (-r, r) if abs(dx) != r else range(-r, r + 1):
                    if free(x + dx - rx, x + dx + rx, y + dy - ry, y + dy + ry, slope):
                        return x + dx, y + dy
        return None
    for (x, y, h) in ((137, 141, 14), (148, 140, 16), (171, 142, 13), (134, 347, 14), (172, 346, 12),
                      (130, 68, 15), (171, 70, 13), (170, 101, 14), (131, 101, 12)):
        f = search(x, y, 2, 2, 2)
        if not f:
            continue
        x, y = f
        sl = (slice(x - 9, x + 10), slice(y - 9, y + 10))
        before = cv.solid[sl].copy()
        veg.conifer(cv, rng, x, y, int(cv.H[x, y]), spruce, h=h, clear=4)
        diff = cv.solid[sl] & ~before
        for (i, j, k) in zip(*np.nonzero(diff)):
            X, Y, Z = x - 9 + int(i), y - 9 + int(j), int(k)
            A._note('yard framing trees', X, Y, Z)
            mx = 512 - X
            if 0 <= mx < 512 and not cv.solid[mx, Y, Z]:
                cv.set(mx, Y, Z, tuple(int(v) for v in cv.rgb[X, Y, Z]), int(cv.mat[X, Y, Z]))
                A._note('yard framing trees', mx, Y, Z)
        n['trees'] += 1
    wood, bark = tuple(int(c) for c in LOG[2]), tuple(int(c) for c in LOG[1])
    items = [('woodpile', 152, 157, 142, 143, 2), ('sledge', 162, 165, 141, 142, 1), ('rack', 140, 146, 143, 143, 3),
             ('woodpile', 165, 166, 84, 89, 2), ('sledge', 133, 136, 92, 93, 1), ('rack', 131, 131, 75, 81, 3),
             ('sledge', 183, 184, 309, 312, 1), ('cart', 183, 185, 326, 329, 1), ('woodpile', 168, 173, 338, 339, 2),
             ('rack', 130, 130, 140, 146, 3), ('sledge', 172, 175, 107, 108, 1)]
    for (kind, x0, x1, y0, y1, h) in items:
        cxy = search((x0 + x1) // 2, (y0 + y1) // 2, (x1 - x0 + 1) // 2, (y1 - y0 + 1) // 2, 1)
        if not cxy:
            continue
        dxy = (cxy[0] - (x0 + x1) // 2, cxy[1] - (y0 + y1) // 2)
        x0, x1, y0, y1 = x0 + dxy[0], x1 + dxy[0], y0 + dxy[1], y1 + dxy[1]
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                g = int(cv.H[x, y])
                if kind == 'rack':
                    post = (x in (x0, x1) and y in (y0, y1)) or (x == x0 and (y - y0) % 3 == 0) or \
                        (y == y0 and (x - x0) % 3 == 0)
                    for z in (range(g - h, g) if post else [g - h]):
                        A.put('yard props', x, y, z, bark)
                    if (x + y) % 2 == 0:
                        A.put('yard props', x, y, g - h + 1, (150, 128, 96))      # stockfish
                else:
                    for z in range(g - h, g):
                        A.put('yard props', x, y, z, wood if (x + y + z) % 2 else bark)
                    if kind in ('sledge', 'cart') and (x in (x0, x1)):
                        A.put('yard props', x, y, g - 1, (124, 52, 42))
        n['props'] += 1
    n['rejected_tries'] = len(why)
    return n


def braziers(A, cv, structs):
    n = 0
    for s_ in structs:
        if type_of(s_['name']) != 'shed' or s_['box'][0] > 255:
            continue
        x0, x1, y0, y1 = s_['box']
        yc = (y0 + y1) // 2
        for y in (yc - 4, yc + 4):
            x = x0 - 3
            g = int(cv.H[x, y])
            if top_at(cv, x, y) != g:
                continue
            A.put('boat-shed braziers', x, y, g - 1, tuple(int(c) for c in IRON[1]))
            A.put('boat-shed braziers', x, y, g - 2, tuple(int(c) for c in IRON[2]))
            A.put('boat-shed braziers', x, y, g - 3, GLOW['pyre'], glow=True)
            n += 1
    return n


def lantern_strings(A, cv, posts):
    """Spaced-bulb strings between neighbouring lantern posts (rope dark, bulb every 3rd, colours alternate)."""
    rope = (54, 48, 46)
    cols = [GLOW['string_light_red'], GLOW['string_light_gold'], GLOW['window_amber']]
    used, n = set(), 0
    for i, (x, y, g) in enumerate(posts):
        best = None
        for j, (x2, y2, g2) in enumerate(posts):
            if j == i or (j, i) in used or (i, j) in used:
                continue
            d = math.hypot(x2 - x, y2 - y)
            if 5 <= d <= 18 and (best is None or d < best[0]):
                best = (d, j)
        if not best:
            continue
        j = best[1]
        used.add((i, j))
        x2, y2, g2 = posts[j]
        mz = min(g, g2) - 4
        pts = line_points(x, y, mz, x2, y2, mz)[1:-1]
        if any(top_at(cv, px, py) < pz + 4 for (px, py, pz) in pts):
            continue
        for k, (px, py, pz) in enumerate(pts):
            if k % 3 == 1:
                A.put('lantern strings', px, py, pz, cols[n % 3], glow=True)
                n += 1
            else:
                A.put('lantern strings', px, py, pz, rope)
    return n


def art_pass(cv, structs, art_seed):
    rng = np.random.default_rng(art_seed)
    rep = {}
    A = Adds(cv)
    ships = [(209, 20), (303, None)]
    # ---- cosmetic geometry (symmetric pieces drawn at x and 512 - x)
    finials(A, cv, structs)
    lodge_antlers(A, cv, structs)
    raven_heads(A, cv)
    longship_details(A, cv, ships)
    POSTS.clear()
    rep['lantern_posts_west'] = lantern_posts(A, cv)
    rep['lantern_strings_bulbs_west'] = lantern_strings(A, cv, POSTS)
    rep['braziers_west'] = braziers(A, cv, structs)
    gate_arch(A, cv)
    sleipnir_rebuild(A, cv)
    church_tiers(A, cv)
    church_clerestory(A, cv)
    lawspeaker(A, cv)
    rep['yards'] = yards(A, cv, rng)
    rooms = []
    for s in structs:
        t = type_of(s['name'])
        if t in ('mead', 'smithy', 'shed', 'longhouse', 'byre', 'bath', 'lodge', 'hut'):
            x0, x1, y0, y1 = s['box']
            zf = int(np.median(cv.H[x0 + 2:x1 - 1, y0 + 2:y1 - 1]))
            rooms.append((x0 + 2, x1 - 2, y0 + 2, y1 - 2, zf))
    rooms += [(134, 144, 150, 170, 35), (161, 176, 310, 328, 35)]        # mead hall gallery, longhouse loft
    zc = int(np.median(cv.H[147:158, 78:91]))
    rooms += [(147, 157, 78, 90, zc)]                                    # stave church nave
    rep['furniture_west'] = furnish(A, cv, rooms, rng)
    # ---- cosmetic asymmetry after the mirror
    stern_curls(A, cv, ships)
    # ---- colour
    role, names, idx = recolour(cv, structs, rep)
    rep['glow'] = glow_pass(cv, role, names, idx, structs)
    rep['glow']['Raven Gate leg rune bands'] = gate_runes(cv)
    sky_recs, n_aur = sky_decor(cv)
    rep['glow']['aurora'] = n_aur
    tx0, tx1, ty0, ty1 = tag.tag_rect(SPEC['name'], 'SW')
    bx = (max(0, tx0 - 2), tx1 + 2, max(0, ty0 - 2), min(511, ty1 + 2))
    before = cv.solid[bx[0]:bx[1] + 1, bx[2]:bx[3] + 1].copy()
    rect = tag.paint_tag(cv, SPEC['name'], corner='SW', rgb=(206, 192, 150), shadow=(64, 56, 50))
    after = cv.solid[bx[0]:bx[1] + 1, bx[2]:bx[3] + 1]
    for (i, j, k) in zip(*np.nonzero(before & ~after)):
        A._note('corner tag levelling (kit paint_tag: canopy and props cleared, strip levelled)', bx[0] + int(i),
                bx[2] + int(j), int(k), removed=True)
    for (i, j, k) in zip(*np.nonzero(after & ~before)):
        A._note('corner tag levelling (kit paint_tag: canopy and props cleared, strip levelled)', bx[0] + int(i),
                bx[2] + int(j), int(k))
    surf = color.lighting(cv, sun=(0.07, 0.04, -0.06, -0.03), side_f=0.84, ao_size=5, cover_f=0.84)
    stored, n_src = color.bake_glow(cv, surf, radius=4.5, strength=0.16)
    rep['brightness'] = color.enforce_brightness(cv)
    rep['glow_sources'] = n_src
    rep['glow_stored'] = len(stored)
    return {'report': rep, 'additions': A.report(), 'stored': stored, 'sky': sky_recs, 'tag_rect': list(rect)}


def clean_glow(cv, stored):
    """Drop glow_stored_colors keys that point at air (pieces removed by the final orphan cleanup)."""
    return {k: v for k, v in stored.items() if cv.inside(*k) and cv.solid[k]}
