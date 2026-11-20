"""Original set pieces for Bloomhop Kingdom (west half authored; centre-line pieces mirror automatically)."""
import math
import numpy as np
from geo import shade, mix, clamp8

# ---------------- palette ----------------
CREAM = (234, 218, 184); CREAM_DK = (208, 190, 154); MORTAR = (182, 164, 134)
BASE_STONE = (170, 158, 150); BASE_STONE_DK = (138, 128, 122)
ROOF = (212, 96, 70); ROOF_DK = (172, 72, 54); ROOF_LT = (232, 128, 92)
WOOD = (142, 94, 58); WOOD_DK = (106, 68, 42); WOOD_LT = (176, 126, 80)
BRICK = (196, 106, 64); BRICK_DK = (156, 78, 46); BRICK_MORT = (220, 184, 144)
STONE = (160, 154, 150); STONE_DK = (124, 118, 116)
CAVE = (112, 96, 88); CAVE_DK = (86, 72, 66)
GOLD = (236, 186, 72); GOLD_DK = (200, 148, 52)
TOY = [(222, 92, 78), (238, 188, 76), (112, 190, 148), (236, 222, 190), (170, 136, 198)]
BANNER_PLACEHOLDER = (61, 111, 221)  # recoloured per team after mirroring
GLOW_AMBER = (255, 175, 95); GLOW_YEL = (255, 255, 95); GLOW_CYAN = (95, 255, 255); GLOW_GREEN = (95, 255, 95)
GLOW_PINK = (255, 95, 95)


def h32(*a):
    v = 2166136261
    for i in a:
        v = ((v ^ (int(i) & 0xffffffff)) * 16777619) & 0xffffffff
    return v


def brick_col(u, z, base=BRICK, dark=BRICK_DK, mort=BRICK_MORT, blen=4, rows=2):
    """Running-bond brick colour for wall coordinate u (along wall) and z."""
    if z % (rows + 1) == 0:
        return mort
    row = z // (rows + 1)
    if (u + (row % 2) * (blen // 2)) % (blen + 1) == 0:
        return mort
    bi = (u + (row % 2) * (blen // 2)) // (blen + 1)
    t = (h32(bi, row) % 100) / 100.0
    return clamp8(mix(base, dark, t * 0.6))


def stone_col(u, z, base=CREAM, dark=CREAM_DK, mort=MORTAR):
    """Large ashlar blocks (3 tall, 6 long)."""
    if z % 4 == 0:
        return mort
    row = z // 4
    if (u + (row % 2) * 3) % 7 == 0:
        return mort
    bi = (u + (row % 2) * 3) // 7
    t = (h32(bi, row, 7) % 100) / 100.0
    return clamp8(mix(base, dark, t * 0.5))


# ---------------- generic helpers ----------------
def cyl(W, cx, cy, r, z0, z1, col, inner=None):
    """Vertical cylinder from z0 (top) to z1 (bottom) inclusive. col(x,y,z) or tuple."""
    for x in range(int(cx - r - 1), int(cx + r + 2)):
        for y in range(int(cy - r - 1), int(cy + r + 2)):
            d = math.hypot(x - cx, y - cy)
            if d <= r and (inner is None or d > inner):
                for z in range(z0, z1 + 1):
                    W.set(x, y, z, col(x, y, z) if callable(col) else col)


def carve_cyl(W, cx, cy, r, z0, z1):
    for x in range(int(cx - r - 1), int(cx + r + 2)):
        for y in range(int(cy - r - 1), int(cy + r + 2)):
            if math.hypot(x - cx, y - cy) <= r:
                for z in range(z0, z1 + 1):
                    W.clear(x, y, z)


def cone(W, cx, cy, r, zbase, ztip, col):
    hgt = zbase - ztip
    for z in range(ztip, zbase + 1):
        rr = r * (z - ztip + 0.6) / (hgt + 0.6)
        for x in range(int(cx - r - 1), int(cx + r + 2)):
            for y in range(int(cy - r - 1), int(cy + r + 2)):
                if math.hypot(x - cx, y - cy) <= rr:
                    band = (z - ztip) % 3 == 0
                    W.set(x, y, z, col[1] if band else col[0])


def spiral_stair(W, cx, cy, z_top_floor, z_bot_floor, r=4, col=STONE, core=STONE_DK):
    """Spiral stair inside a shaft; floors are the standing-voxel z (top surfaces). Steps rise 1 per 45 deg."""
    carve_cyl(W, cx, cy, r + 0.5, z_top_floor - 3, z_bot_floor - 1)
    n = z_bot_floor - z_top_floor
    for i in range(1, n + 1):
        zt = z_bot_floor - i
        a0 = (i % 8) * math.pi / 4
        for x in range(int(cx - r - 1), int(cx + r + 2)):
            for y in range(int(cy - r - 1), int(cy + r + 2)):
                d = math.hypot(x + 0.5 - cx - 0.5, y + 0.5 - cy - 0.5)
                if 1.2 < d <= r + 0.3:
                    a = math.atan2(y - cy, x - cx) % (2 * math.pi)
                    da = (a - a0) % (2 * math.pi)
                    if da < math.pi / 4 + 0.08:
                        W.set(x, y, zt, col)
    # central core
    for x in (int(cx) - 1, int(cx)):
        for y in (int(cy) - 1, int(cy)):
            for z in range(z_top_floor, z_bot_floor):
                W.set(x, y, z, core)


def stair_hatch(W, cx, cy, r, z_slab, n):
    """Open a slab above the last 3 steps of a spiral_stair with n steps."""
    for i in range(max(1, n - 4), n):
        a0 = (i % 8) * math.pi / 4
        for x in range(int(cx - r - 1), int(cx + r + 2)):
            for y in range(int(cy - r - 1), int(cy + r + 2)):
                d = math.hypot(x - cx, y - cy)
                if d <= r + 0.6:
                    a = math.atan2(y - cy, x - cx) % (2 * math.pi)
                    if (a - a0) % (2 * math.pi) < math.pi / 4 + 0.2 or (a0 - a) % (2 * math.pi) < 0.2:
                        W.clear(x, y, z_slab)


def straight_stair(W, x0, y0, y1, floor_z, rise, dx, col=WOOD, cut_above=True):
    """Stair rising `rise` levels starting at column x0 going along x by dx (+1/-1); width y0..y1.
    Step i top at floor_z - i. Cuts air 3 above every step (opens slabs)."""
    for i in range(1, rise + 1):
        x = x0 + (i - 1) * dx
        for y in range(y0, y1 + 1):
            for z in range(floor_z - i, floor_z):
                W.set(x, y, z, col if z == floor_z - i else shade(col, 0.85))
            if cut_above:
                for z in range(floor_z - i - 3, floor_z - i):
                    W.clear(x, y, z)
    # landing headroom after the top step
    if cut_above:
        x = x0 + rise * dx
        for y in range(y0, y1 + 1):
            for z in range(floor_z - rise - 3, floor_z - rise):
                W.clear(x, y, z)


def mark_keep(W, x0, x1, y0, y1, flag=1):
    W.keep[max(0, x0):x1 + 1, max(0, y0):y1 + 1] |= flag


def lantern_post(W, x, y, ztop_ground, height=5, glow=GLOW_AMBER):
    for z in range(ztop_ground - height, ztop_ground):
        W.set(x, y, z, WOOD_DK)
    zc = ztop_ground - height - 1
    for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
        W.set(x + dx, y + dy, zc + 1, GOLD_DK)
    W.set(x, y, zc, glow)
    W.glow.append((x, y, zc, glow))
    W.set(x, y, zc - 1, GOLD_DK)
    W.set(x, y, zc - 2, GOLD)


def ground_z(W, x, y):
    return int(W.H[x, y])


# ---------------- spawn keep ----------------
def bloomhop_keep(W):
    """Spawn keep west of the spawn square. Floors: ground z46, 2nd slab z39, 3rd z33, roof z27."""
    x0, x1, y0, y1 = 42, 72, 238, 274
    g = 46
    slabs = [39, 33, 27]
    # foundation fill so the keep sits on level ground
    W.box(x0 - 3, x1 + 3, y0 - 3, y1 + 3, g, 63, BASE_STONE)
    W.box(x0 - 3, x1 + 3, y0 - 3, y1 + 3, 0, g - 1, air=True)
    # walls (2 thick)
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            edge = min(x - x0, x1 - x, y - y0, y1 - y)
            if edge < 2:
                u = x + y
                for z in range(25, g):
                    if z >= 42:
                        c = stone_col(u, z, BASE_STONE, BASE_STONE_DK, (120, 112, 106))
                    else:
                        c = stone_col(u, z)
                    W.set(x, y, z, c)
    # slabs
    for s in slabs:
        W.box(x0 + 2, x1 - 2, y0 + 2, y1 - 2, s, s, WOOD if s != 27 else STONE)
        # ceiling beams look: darker underside row every 4
        for x in range(x0 + 2, x1 - 1, 4):
            W.box(x, x, y0 + 2, y1 - 2, s, s, WOOD_DK if s != 27 else STONE_DK)
    # string course between floors
    for s in slabs:
        for x in range(x0 - 1, x1 + 2):
            for y in (y0 - 1, y1 + 1):
                W.set(x, y, s, CREAM_DK)
        for y in range(y0 - 1, y1 + 2):
            for x in (x0 - 1, x1 + 1):
                W.set(x, y, s, CREAM_DK)
    # battlements on the roof walk (z 25-26 parapet with merlons)
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            edge = min(x - x0, x1 - x, y - y0, y1 - y)
            if edge == 0:
                W.set(x, y, 26, CREAM)
                if (x + y) % 4 < 2:
                    W.set(x, y, 25, CREAM)
                    W.set(x, y, 24, CREAM_DK)
                else:
                    W.clear(x, y, 25)
            elif edge == 1:
                W.clear(x, y, 25); W.clear(x, y, 26)
    # doors: east (main, 13 wide, arched), north, south
    def arch_open(axis, fixed, a0, a1, zbot, ztop, thick):
        span = a1 - a0
        for a in range(a0, a1 + 1):
            t = (a - a0) / max(span, 1) * 2 - 1
            top = ztop + int(round((1 - math.sqrt(max(0, 1 - t * t))) * 2.5))
            for z in range(top, zbot + 1):
                for k in range(thick):
                    if axis == 'x':
                        W.clear(fixed + k, a, z)
                    else:
                        W.clear(a, fixed + k, z)
    arch_open('x', x1 - 1, 250, 262, 45, 39, 2)
    arch_open('y', y0, 53, 61, 45, 40, 2)
    arch_open('y', y1 - 1, 53, 61, 45, 40, 2)
    # door trim (gold keystones)
    for z in (38, 39):
        W.set(x1 + 1, 256, z, GOLD)
    # windows: 2 wide 3 tall every 6, each floor
    for (zb, zt) in ((43, 41), (37, 35), (31, 29)):
        for x in range(x0 + 4, x1 - 3, 6):
            for y in (y0, y0 + 1, y1 - 1, y1):
                for z in range(zt, zb + 1):
                    if not (zb == 43 and 52 <= x <= 62):
                        W.clear(x, y, z); W.clear(x + 1, y, z)
        for y in range(y0 + 4, y1 - 3, 6):
            for x in (x0, x0 + 1, x1 - 1, x1):
                if x >= x1 - 1 and 248 <= y <= 264 and zb == 43:
                    continue
                for z in range(zt, zb + 1):
                    W.clear(x, y, z); W.clear(x, y + 1, z)
    # window sills (lighter)
    # stairs: ground->2 along south wall going west->east; 2->3 along north wall east->west; 3->roof south wall
    straight_stair(W, x0 + 4, y1 - 5, y1 - 2, 46, 7, +1, WOOD)
    straight_stair(W, x1 - 4, y0 + 2, y0 + 5, 39, 6, -1, WOOD)
    straight_stair(W, x0 + 4, y1 - 5, y1 - 2, 33, 6, +1, WOOD)
    # railings around stair holes would block; leave open.
    # interior furniture: long table + benches (ground), hearth on west wall
    W.box(50, 64, 254, 257, 44, 44, WOOD_LT)
    for x in (50, 64):
        for y in (254, 257):
            W.set(x, y, 45, WOOD_DK)
    W.box(50, 64, 252, 252, 45, 45, WOOD_DK); W.box(50, 64, 259, 259, 45, 45, WOOD_DK)
    W.box(x0 + 2, x0 + 3, 252, 260, 40, 45, STONE_DK)
    W.box(x0 + 2, x0 + 2, 254, 258, 43, 45, air=True)
    W.set(x0 + 2, 256, 45, GLOW_AMBER); W.glow.append((x0 + 2, 256, 45, GLOW_AMBER))
    # 2nd floor bunks
    for y in range(244, 268, 6):
        W.box(x0 + 3, x0 + 7, y, y + 2, 38, 38, WOOD)
        W.box(x0 + 3, x0 + 7, y, y + 2, 37, 37, (196, 92, 84))
    # 3rd floor map table
    W.box(54, 60, 252, 260, 31, 32, WOOD)
    W.box(55, 59, 253, 259, 31, 31, (214, 196, 150))
    # corner turrets
    for (cx, cy) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        tc = lambda x, y, z, cx=cx, cy=cy: stone_col(int(math.degrees(math.atan2(y - cy, x - cx)) / 9), z)
        cyl(W, cx, cy, 5, 28, 45, tc)
        cyl(W, cx, cy, 5, 20, 27, tc, inner=3.4)
        W.box(cx - 3, cx + 3, cy - 3, cy + 3, 27, 27, STONE)  # turret floor at roof level
        # openings from the roof walk into turrets
        for z in (24, 25, 26):
            for k in range(-1, 2):
                if cx == x0:
                    W.clear(cx + 4, cy + k, z); W.clear(cx + 5, cy + k, z)
                else:
                    W.clear(cx - 4, cy + k, z); W.clear(cx - 5, cy + k, z)
        # arrow slits
        for z in (22, 23):
            for (ox, oy) in ((5, 0), (-5, 0), (0, 5), (0, -5)):
                W.clear(cx + ox, cy + oy, z)
        cone(W, cx, cy, 6.5, 19, 9, (ROOF, ROOF_DK))
        W.set(cx, cy, 8, GOLD); W.set(cx, cy, 7, GOLD)
    # central roof cupola (open pavilion with a pointed roof) on the roof walk
    for (px, py) in ((53, 250), (61, 250), (53, 262), (61, 262)):
        W.box(px, px + 1, py, py + 1, 22, 26, WOOD_DK)
    W.box(51, 64, 248, 264, 21, 21, ROOF_DK)
    for i in range(6):
        W.box(51 + i, 64 - i, 248 + i, 264 - i, 20 - i, 20 - i, ROOF if i % 2 == 0 else ROOF_LT)
    # team banner above the east door (placeholder colour, recoloured per team)
    banner = []
    for y in range(252, 261):
        for z in range(28, 37):
            emblem = (abs(y - 256) + abs(z - 32) <= 2) and not (y == 256 and z == 32)
            c = (236, 232, 220) if emblem else BANNER_PLACEHOLDER
            W.set(x1 + 1, y, z, c)
            if not emblem:
                banner.append((x1 + 1, y, z))
    for y in range(252, 261):
        W.set(x1 + 1, y, 27, GOLD_DK)
    W.banner = banner
    # lanterns either side of the main door
    for y in (247, 265):
        W.set(x1 + 1, y, 41, GOLD_DK)
        W.set(x1 + 2, y, 41, GLOW_AMBER); W.glow.append((x1 + 2, y, 41, GLOW_AMBER))
        W.set(x1 + 2, y, 40, GOLD_DK)
    mark_keep(W, x0 - 8, x1 + 8, y0 - 8, y1 + 8)
    # courtyard: low flower-bed walls and a fountain between keep and spawn square
    fx, fy = 85, 256
    cyl(W, fx, fy, 6, 44, 45, STONE, inner=4.6)
    cyl(W, fx, fy, 4.6, 45, 45, (120, 200, 196))
    cyl(W, fx, fy, 1.4, 39, 45, CREAM)
    cyl(W, fx, fy, 3, 38, 38, CREAM, inner=1.5)
    W.set(fx, fy, 37, (150, 216, 210))
    for (bx0, by0) in ((80, 226), (80, 278)):
        W.box(bx0, bx0 + 12, by0, by0 + 6, 45, 45, BRICK)
        W.box(bx0 + 1, bx0 + 11, by0 + 1, by0 + 5, 45, 45, (96, 70, 44))
        for i in range(bx0 + 1, bx0 + 12, 2):
            for j in range(by0 + 1, by0 + 6, 2):
                W.set(i, j, 44, [(236, 116, 108), (244, 206, 96), (236, 236, 214), (200, 140, 220)][(i + j) % 4])
    mark_keep(W, 76, 96, 222, 290)


def castle_cellar(W):
    """Cellar under the keep and a secret passage that exits on the plateau's north slope."""
    # cellar room floor z 53 (air 49-52)
    W.box(46, 66, 244, 268, 49, 52, air=True)
    for x in range(45, 68):
        for y in range(243, 270):
            if x in (45, 67) or y in (243, 269):
                for z in range(49, 53):
                    W.set(x, y, z, stone_col(x + y, z, BASE_STONE, BASE_STONE_DK, (110, 102, 98)))
    W.box(46, 66, 244, 268, 53, 53, STONE_DK)
    # stair down from the ground floor (z46) to cellar (z53) along x 58-64, y 245-247 descending east
    for i in range(1, 8):
        x = 57 + i
        for y in range(245, 248):
            for z in range(46, 46 + i):
                W.clear(x, y, z)
            W.set(x, y, 46 + i, STONE)
            for z in range(46 + i + 1, 54):
                W.set(x, y, z, STONE_DK)
    W.box(65, 66, 245, 247, 49, 52, air=True)
    # barrels and crates
    for (bx, by) in ((48, 250), (48, 254), (48, 262), (52, 266)):
        cyl(W, bx, by, 1.5, 50, 52, WOOD)
        W.set(bx, by, 50, WOOD_DK)
    W.box(60, 62, 262, 264, 51, 52, WOOD_LT)
    W.set(56, 256, 52, GLOW_AMBER); W.glow.append((56, 256, 52, GLOW_AMBER))
    # secret passage north, 4 wide, floor z 53
    for y in range(186, 245):
        wig = int(round(2 * math.sin(y / 9.0)))
        for x in range(53 + wig, 57 + wig):
            for z in range(49, 53):
                W.clear(x, y, z)
            W.set(x, y, 53, CAVE)
        for x in (52 + wig, 57 + wig):
            for z in range(49, 54):
                if W.S[x, y, z]:
                    W.set(x, y, z, CAVE_DK if (y + z) % 3 else CAVE)
        if y % 14 == 0:
            W.set(52 + wig, y, 50, GLOW_GREEN); W.glow.append((52 + wig, y, 50, GLOW_GREEN))
    # make sure the exit opens to air (clear above the passage where the slope is low)
    for y in range(180, 192):
        for x in range(50, 61):
            if W.H[x, y] >= 52:
                for z in range(40, 53):
                    if z < W.H[x, y] or z <= 52:
                        pass
    mark_keep(W, 48, 62, 180, 200)


# ---------------- tower anchor + front ----------------
def anchor_dressing(W):
    """Brick face on the anchor's sheer east wall (x 212 face) and brick block trims on front terraces."""
    for y in range(200, 312):
        if W.H[212, y] < W.H[213, y]:
            for z in range(W.H[212, y], W.H[213, y]):
                W.set(212, y, z, brick_col(y, z))
    # grass lip on the anchor top edge


# ---------------- centre: toy-block hill ----------------
def toy_block(W, x0, y0, ztop, sx=8, sy=8, sz=6, col=None, emblem=0, seed=0):
    c = col
    lt = shade(c, 1.12); dk = shade(c, 0.86)
    for x in range(x0, x0 + sx):
        for y in range(y0, y0 + sy):
            for z in range(ztop, ztop + sz):
                ex = x in (x0, x0 + sx - 1); ey = y in (y0, y0 + sy - 1); ez = z in (ztop, ztop + sz - 1)
                edge = (ex + ey + ez) >= 2
                cc = lt if edge else c
                # emblem on side faces: small diamond/ring/cross
                fu = None
                if ex and not ey and not ez:
                    fu = (y - y0 - (sy - 1) / 2, z - ztop - (sz - 1) / 2)
                elif ey and not ex and not ez:
                    fu = (x - x0 - (sx - 1) / 2, z - ztop - (sz - 1) / 2)
                if fu is not None:
                    a, b = abs(fu[0]), abs(fu[1])
                    if emblem == 0 and a + b <= 1.6:
                        cc = dk
                    elif emblem == 1 and 1.0 <= math.hypot(a, b) <= 2.0:
                        cc = dk
                    elif emblem == 2 and (a < 0.6 or b < 0.6) and a + b < 2.6:
                        cc = dk
                W.set(x, y, z, cc)


def toy_hill(W):
    """Stack of chunky toy blocks straddling the centre line under the platform. Tunnels N-S and E-W."""
    cz = 57
    rng = np.random.default_rng(55)
    # tier 1: 5x5 grid of 8x8x6 blocks, x 236..275, y 236..275, top z 51 (blocks z 51-56); leave tunnels
    xs = [236, 244, 252, 260, 268]
    ys = [236, 244, 252, 260, 268]
    for i, bx in enumerate(xs):
        for j, by in enumerate(ys):
            if i == 2 or j == 2:
                continue  # tunnels through the middle row/column
            if (i in (0, 4)) and (j in (0, 4)):
                continue  # rounded corners
            col = TOY[(i * 3 + j * 2) % len(TOY)]
            toy_block(W, bx, by, 51, col=col, emblem=(i + j) % 3)
    # tunnel ceilings: lintel blocks spanning the tunnels at z 51-52 (tunnel air z 53-56, 4 high)
    for bx in xs:
        if bx == 252:
            continue
        toy_block(W, bx, 252, 51, sz=2, col=TOY[3], emblem=0)
    for by in ys:
        if by == 252:
            continue
        toy_block(W, 252, by, 51, sz=2, col=TOY[3], emblem=0)
    toy_block(W, 252, 252, 51, sz=2, col=TOY[1], emblem=1)
    # tier 2: 3x3 (top z 45), centre block hollow chamber
    for i, bx in enumerate([244, 252, 260]):
        for j, by in enumerate([244, 252, 260]):
            col = TOY[(i + j * 2 + 1) % len(TOY)]
            toy_block(W, bx, by, 45, col=col, emblem=(i * 2 + j) % 3)
    # tier 3 accent: one tall block pair (top z 41) on the west half, mirrored
    toy_block(W, 248, 248, 41, sx=8, sy=6, sz=4, col=TOY[0], emblem=1)
    # stairs up the north and south faces (1-voxel risers), x 244-249 (mirrored to 262-267)
    for side in (-1, 1):
        # ground (z57) -> tier-1 top (z51): in front of the blocks
        for i in range(1, 7):
            y = (229 + i) if side < 0 else (282 - i)
            z = cz - i
            for x in range(244, 250):
                for zz in range(z, cz):
                    W.set(x, y, zz, shade(TOY[3], 0.95 if zz == z else 0.82))
                for zz in range(z - 3, z):
                    W.clear(x, y, zz)
        # tier-1 top (z51) -> tier-2 top (z45): on top of tier-1
        for i in range(1, 7):
            y = (237 + i) if side < 0 else (274 - i)
            z = 51 - i
            for x in range(244, 250):
                for zz in range(z, 51):
                    W.set(x, y, zz, shade(TOY[1], 0.95 if zz == z else 0.82))
                for zz in range(z - 3, z):
                    W.clear(x, y, zz)
    # chamber inside the tier-2 centre block, reached by corridors from the tier-1 roof (N and S)
    W.box(253, 258, 253, 258, 46, 50, air=True)
    W.set(255, 255, 50, GLOW_YEL); W.glow.append((255, 255, 50, GLOW_YEL))
    W.box(254, 257, 244, 253, 47, 50, air=True)
    W.box(254, 257, 258, 267, 47, 50, air=True)
    # tunnel lanterns
    for (x, y) in ((239, 255), (255, 239), (255, 272)):
        W.set(x, y, 53, GLOW_AMBER); W.glow.append((x, y, 53, GLOW_AMBER))
    mark_keep(W, 230, 281, 230, 281)


# ---------------- mushroom cottages ----------------
SPOT = (246, 238, 218)


def mushroom_cottage(W, cx, cy, cap_col, door_dir=(0, 1), seed=0):
    rng = np.random.default_rng(seed)
    g = int(np.median(W.H[cx - 8:cx + 9, cy - 8:cy + 9]))
    # level pad
    W.box(cx - 9, cx + 9, cy - 9, cy + 9, g, 63, (118, 92, 66))
    W.box(cx - 9, cx + 9, cy - 9, cy + 9, 0, g - 1, air=True)
    W.H[cx - 9:cx + 10, cy - 9:cy + 10] = g
    for x in range(cx - 9, cx + 10):
        for y in range(cy - 9, cy + 10):
            W.set(x, y, g, (112, 182, 70))
    body_top = g - 13
    stem = (238, 226, 198); stem_dk = (214, 198, 166)
    cyl(W, cx, cy, 7, body_top, g - 1, lambda x, y, z: stem if (z % 5) else stem_dk, inner=5.5)
    # loft slab at g-7
    lz = g - 7
    cyl(W, cx, cy, 5.6, lz, lz, WOOD)
    # stair ground->loft (straight, along x), y cy+1..cy+2
    straight_stair(W, cx - 3, cy + 1, cy + 2, g, 7, +1, WOOD_LT)
    # door
    ddx, ddy = door_dir
    for z in range(g - 4, g):
        for k in (-1, 0, 1):
            for r in (6, 7):
                if ddy:
                    W.clear(cx + k, cy + ddy * r, z)
                else:
                    W.clear(cx + ddx * r, cy + k, z)
    # door frame + round windows
    for k in (-2, 2):
        for z in range(g - 4, g):
            if ddy:
                W.set(cx + k, cy + ddy * 7, z, WOOD_DK)
            else:
                W.set(cx + ddx * 7, cy + k, z, WOOD_DK)
    for ang in range(0, 360, 60):
        a = math.radians(ang)
        wx, wy = cx + 6.5 * math.cos(a), cy + 6.5 * math.sin(a)
        for zc in (g - 3, lz - 3):
            for dz in (0, 1):
                for o in (0,):
                    W.clear(int(round(wx)), int(round(wy)), zc - dz)
    # cap: hollow dome
    capz = body_top
    def capc(x, y, z, d):
        out = []
        for xi, yi, zi in zip(x, y, z):
            s = (h32(xi // 3, yi // 3, zi // 3, seed) % 11 == 0)
            c = SPOT if s else cap_col
            t = (zi - (capz - 9)) / 9.0
            out.append(mix(c, shade(c, 0.86), max(0, t) * 0.6))
        return np.clip(np.array(out), 0, 255).astype(np.uint8)
    W.ellipsoid(cx, cy, capz + 1, 12, 12, 10, capc, hollow=0.62)
    # cut the lower half of the dome (keep only z <= capz+1) and leave a gill rim
    W.box(cx - 13, cx + 13, cy - 13, cy + 13, capz + 2, capz + 12, air=True)
    cyl(W, cx, cy, 12, capz + 1, capz + 1, (200, 170, 140), inner=7.2)
    # restore body under cap
    cyl(W, cx, cy, 7, capz + 2, g - 1, lambda x, y, z: stem if (z % 5) else stem_dk, inner=5.5)
    for z in range(capz + 2, g):
        pass
    # re-open door/windows (body restored)
    for z in range(g - 4, g):
        for k in (-1, 0, 1):
            for r in (5, 6, 7):
                if ddy:
                    W.clear(cx + k, cy + ddy * r, z)
                else:
                    W.clear(cx + ddx * r, cy + k, z)
    for ang in range(0, 360, 60):
        a = math.radians(ang)
        for r in (6, 7):
            wx, wy = int(round(cx + r * math.cos(a))), int(round(cy + r * math.sin(a)))
            for zc in (g - 3, lz - 3):
                W.clear(wx, wy, zc); W.clear(wx, wy, zc - 1)
    # re-cut stair headroom and loft slab
    cyl(W, cx, cy, 5.6, lz, lz, WOOD)
    straight_stair(W, cx - 3, cy + 1, cy + 2, g, 7, +1, WOOD_LT)
    # loft interior air under cap
    carve_cyl(W, cx, cy, 5.4, capz + 2, lz - 1)
    # dormer window in the cap facing the door side
    for z in range(capz - 4, capz):
        for k in (-1, 0, 1):
            for r in range(8, 13):
                if ddy:
                    W.clear(cx + k, cy + ddy * r, z)
                else:
                    W.clear(cx + ddx * r, cy + k, z)
    # chimney
    W.box(cx + 4, cx + 5, cy - 5, cy - 4, capz - 9, capz - 2, BRICK)
    # porch lantern
    if ddy:
        lantern_post(W, cx + 4, cy + ddy * 10, g, 4)
    else:
        lantern_post(W, cx + ddx * 10, cy + 4, g, 4)
    # loft furniture
    W.box(cx - 3, cx - 1, cy - 4, cy - 2, lz - 1, lz - 1, (196, 92, 84))
    mark_keep(W, cx - 14, cx + 14, cy - 14, cy + 14)


# ---------------- giant mushrooms (decor/cover) ----------------
CAPS = [((226, 120, 70), SPOT), ((92, 170, 166), SPOT), ((168, 96, 150), (236, 196, 220)),
        ((232, 176, 74), (250, 232, 196)), ((206, 84, 92), SPOT), ((126, 160, 92), (230, 236, 190))]


def giant_mushroom(W, cx, cy, height, cap_r, rng, cap_top_min=0, glow=False):
    g = int(W.H[cx, cy])
    top = max(g - height, cap_top_min + int(cap_r * 0.55) + 1)
    height = g - top
    if height < 5:
        return False
    capc, spotc = CAPS[rng.integers(len(CAPS))]
    capc = clamp8(np.array(capc) * rng.uniform(0.9, 1.08))
    stem = clamp8(np.array((236, 224, 196)) * rng.uniform(0.94, 1.02))
    sr = max(1.5, cap_r * rng.uniform(0.22, 0.3))
    lean = rng.uniform(-0.12, 0.12, 2)
    for z in range(top, g):
        t = (g - z)
        ox, oy = lean * t
        r = sr * (1.25 if z > g - 3 else 1.0)
        cyl(W, cx + ox, cy + oy, r, z, z, stem if (z % 4) else shade(stem, 0.94))
    tx, ty = cx + lean[0] * height, cy + lean[1] * height
    seed = int(rng.integers(1 << 30))
    rz = cap_r * rng.uniform(0.45, 0.62)
    details = set(rng.choice(['spots', 'skirt', 'babies', 'gillrim', 'band', 'warts', 'glowdots'], 3, replace=False))
    if not glow:
        details.discard('glowdots')
        if len(details) < 3:
            details.add('spots')
    def cc(x, y, z, d):
        out = np.empty((len(x), 3))
        for i, (xi, yi, zi) in enumerate(zip(x, y, z)):
            c = capc
            if 'spots' in details and h32(xi // 3, yi // 3, zi // 2, seed) % 9 == 0:
                c = spotc
            if 'band' in details and abs(zi - (top - rz * 0.35)) < 0.6:
                c = shade(capc, 1.15)
            t = np.clip((zi - (top - rz)) / max(rz, 1), 0, 1)
            out[i] = mix(c, shade(c, 0.84), t * 0.7)
        return np.clip(out, 0, 255).astype(np.uint8)
    W.ellipsoid(tx, ty, top, cap_r, cap_r, rz, cc)
    # flatten underside: remove below cap base except stem
    for x in range(int(tx - cap_r - 1), int(tx + cap_r + 2)):
        for y in range(int(ty - cap_r - 1), int(ty + cap_r + 2)):
            if True:
                for z in range(top + 1, min(int(top + rz) + 2, g - 1)):
                    W.clear(x, y, z)
    for z in range(top + 1, g):
        t = (g - z)
        ox, oy = lean * t
        r = sr * (1.25 if z > g - 3 else 1.0)
        cyl(W, cx + ox, cy + oy, r, z, z, stem if (z % 4) else shade(stem, 0.94))
    if 'gillrim' in details:
        cyl(W, tx, ty, cap_r - 0.5, top, top, (214, 186, 150), inner=sr + 0.8)
    if 'skirt' in details:
        zs = top + max(2, height // 3)
        cyl(W, tx + lean[0] * -(zs - top), ty, sr + 1.6, zs, zs, shade(stem, 1.04), inner=sr - 0.5)
    if 'babies' in details:
        for k in range(rng.integers(2, 4)):
            a = rng.uniform(0, 6.28); r = sr + rng.uniform(2, 4)
            bx, by = int(round(cx + r * math.cos(a))), int(round(cy + r * math.sin(a)))
            if 0 <= bx < 512 and 0 <= by < 512:
                bg = int(W.H[bx, by]); bh = int(rng.integers(2, 4))
                for z in range(bg - bh, bg):
                    W.set(bx, by, z, stem)
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        W.set(bx + dx, by + dy, bg - bh - 1, capc if (dx or dy) else spotc)
    if 'warts' in details:
        for k in range(5):
            a = rng.uniform(0, 6.28); r = rng.uniform(0, cap_r * 0.7)
            wx, wy = int(round(tx + r * math.cos(a))), int(round(ty + r * math.sin(a)))
            ztop = W.column_top(wx, wy, 0) if 0 <= wx < 512 and 0 <= wy < 512 else 64
            if ztop < 64:
                W.set(wx, wy, ztop - 1, spotc)
    if 'glowdots' in details:
        for k in range(3):
            a = rng.uniform(0, 6.28); r = rng.uniform(0, cap_r * 0.6)
            wx, wy = int(round(tx + r * math.cos(a))), int(round(ty + r * math.sin(a)))
            ztop = W.column_top(wx, wy, 0)
            if ztop < 64:
                W.set(wx, wy, ztop, GLOW_PINK); W.glow.append((wx, wy, ztop, GLOW_PINK))
    return True


# ---------------- stepblock lookout ----------------
def stepblock_lookout(W, cx, cy):
    """Hollow tower of stacked chunky brick blocks with an inner spiral stair to a railed deck."""
    g = int(np.median(W.H[cx - 6:cx + 7, cy - 6:cy + 7]))
    W.box(cx - 7, cx + 7, cy - 7, cy + 7, g, 63, STONE_DK)
    W.box(cx - 7, cx + 7, cy - 7, cy + 7, 0, g - 1, air=True)
    W.H[cx - 7:cx + 8, cy - 7:cy + 8] = g
    deck = g - 20
    for x in range(cx - 6, cx + 7):
        for y in range(cy - 6, cy + 7):
            edge = max(abs(x - cx), abs(y - cy))
            if edge >= 5:
                for z in range(deck + 1, g):
                    # block banding: each 4-high course a slightly different brick shade, corners gold
                    corner = abs(x - cx) >= 5 and abs(y - cy) >= 5
                    c = GOLD if corner and (z // 4) % 2 == 0 else brick_col(x + y, z)
                    W.set(x, y, z, c)
    spiral_stair(W, cx, cy, deck, g, r=4, col=WOOD_LT, core=WOOD_DK)
    # doorways on all four sides at ground
    for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        for z in range(g - 4, g):
            for k in (-1, 0, 1):
                for r in (5, 6):
                    W.clear(cx + dx * r + dy * k, cy + dy * r + dx * k, z)
    # windows every 5 up
    for z0 in range(g - 9, deck + 2, -5):
        for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for z in (z0, z0 - 1):
                for r in (5, 6):
                    W.clear(cx + dx * r, cy + dy * r, z)
    # deck with overhang and railing
    W.box(cx - 7, cx + 7, cy - 7, cy + 7, deck, deck, WOOD)
    stair_hatch(W, cx, cy, 4, deck, g - deck)
    for x in (cx - 1, cx):
        for y in (cy - 1, cy):
            W.set(x, y, deck, WOOD_DK)
    for x in range(cx - 7, cx + 8):
        for y in range(cy - 7, cy + 8):
            if max(abs(x - cx), abs(y - cy)) == 7 and (x + y) % 2 == 0:
                W.set(x, y, deck - 1, WOOD_DK)
    W.box(cx - 1, cx, cy - 1, cy, deck - 3, deck - 1, WOOD_DK)
    W.set(cx, cy, deck - 4, GLOW_YEL); W.glow.append((cx, cy, deck - 4, GLOW_YEL))
    mark_keep(W, cx - 10, cx + 10, cy - 10, cy + 10)


# ---------------- brick arch gate ----------------
def brick_arch(W, cx, cy, along='x', span=9, height=8):
    """Arch over a path. along = direction of travel through the arch. Opening 'span' wide, 'height' tall."""
    g = int(W.H[cx, cy])
    half = span // 2 + 2
    ztop = g - height - 4
    for k in range(-half, half + 1):
        for t in (-1, 0, 1):
            x = cx + (t if along == 'x' else k)
            y = cy + (k if along == 'x' else t)
            gz = int(W.H[x, y])
            if abs(k) <= span // 2:
                a = k / (span / 2 + 0.5)
                zopen = g - height + (3 - int(round(3 * math.sqrt(max(0.0, 1 - a * a)))))
                for z in range(ztop, zopen):
                    W.set(x, y, z, brick_col(k + 20, z))
            else:
                for z in range(ztop, gz):
                    W.set(x, y, z, brick_col(k + 20, z))
    for k in (-half, half):
        x = cx + (0 if along == 'x' else k); y = cy + (k if along == 'x' else 0)
        W.set(x, y, ztop - 1, GOLD)
    if along == 'x':
        mark_keep(W, cx - 3, cx + 3, cy - half - 1, cy + half + 1)
    else:
        mark_keep(W, cx - half - 1, cx + half + 1, cy - 3, cy + 3)


# ---------------- windmill on the north knoll (centre line) ----------------
def windmill(W, cx=255.5, cy=84):
    g = 47
    top = 22
    cyl(W, cx, cy, 7.5, top, g - 1, lambda x, y, z: stone_col(int(math.degrees(math.atan2(y - cy, x - cx)) / 8), z), inner=5.6)
    spiral_stair(W, cx, cy, top + 5, g, r=4.5, col=WOOD_LT, core=WOOD_DK)
    cyl(W, cx, cy, 5.8, top + 5, top + 5, WOOD)
    stair_hatch(W, cx, cy, 4.5, top + 5, g - (top + 5))
    # doors N and S
    for z in range(g - 4, g):
        for k in (-1, 0, 1):
            for r in (6, 7, 8):
                W.clear(int(cx + k), int(cy - r), z); W.clear(int(cx + k), int(round(cy + r)), z)
    # windows
    for zc in (36, 30):
        for a in range(0, 360, 90):
            ra = math.radians(a + 45)
            for r in (6, 7):
                W.clear(int(round(cx + r * math.cos(ra))), int(round(cy + r * math.sin(ra))), zc)
                W.clear(int(round(cx + r * math.cos(ra))), int(round(cy + r * math.sin(ra))), zc - 1)
    # cap roof
    cone(W, cx, cy, 9, top - 1, top - 9, (ROOF, ROOF_DK))
    W.set(int(cx), int(cy), top - 10, GOLD)
    # sails on the south face: hub + X arms in x-z plane at y = cy + 9..10
    hy = int(cy + 9)
    hz = top + 6
    W.box(int(cx) - 1, int(cx) + 1, int(cy + 7), hy, hz - 1, hz + 1, WOOD_DK)
    for sx, sz in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        for t in range(2, 16):
            x = int(round(cx + sx * t * 0.72)); z = int(round(hz + sz * t * 0.72))
            for w in range(0, 3):
                xx = x + (0 if sx > 0 else 0)
                zz = z - sz * w if t > 4 else z
                c = (240, 232, 214) if (t > 4 and w > 0 and t % 3) else WOOD
                if 0 <= zz < 63:
                    W.set(xx, hy, zz, c)
    mark_keep(W, int(cx) - 12, int(cx) + 12, int(cy) - 12, int(cy) + 14)


# ---------------- south: tunnel, grotto, fort ruin ----------------
def glowroot_tunnel(W):
    floor = 58
    for x in range(118, 256):
        wig = int(round(1.5 * math.sin(x / 11.0)))
        for y in range(413 + wig, 418 + wig):
            for z in range(54, 58):
                W.clear(x, y, z)
            W.set(x, y, floor, (122, 104, 86) if (x + y) % 5 else (138, 118, 96))
        for y in (412 + wig, 418 + wig):
            for z in range(53, 59):
                if W.S[x, y, z]:
                    W.set(x, y, z, CAVE if (x // 3 + z) % 4 else CAVE_DK)
        for z in (53,):
            for y in range(413 + wig, 418 + wig):
                W.set(x, y, z, CAVE_DK)
        # hanging roots
        if x % 7 == 3:
            W.set(x, 415 + wig, 54, (150, 110, 70))
        if x % 23 == 5:
            W.set(x, 412 + wig, 55, GLOW_CYAN); W.glow.append((x, 412 + wig, 55, GLOW_CYAN))
    # portals north to the meadow at x 132 and 196: trench 57/58 with 4 air, open to the sky at the mouth
    for px in (132, 196):
        for y in range(398, 414):
            for x in range(px - 2, px + 3):
                gz = int(W.H[x, y])
                if y <= 400:
                    fl = gz
                elif y == 401:
                    fl = max(min(gz, 57), 57) if gz <= 57 else gz
                else:
                    fl = floor
                top_clear = min(fl - 4, gz) if y <= 402 else fl - 4
                for z in range(min(top_clear, fl - 4) if y > 402 else min(gz, fl - 4), fl):
                    W.clear(x, y, z)
                for z in range(fl, 63):
                    W.set(x, y, z, (122, 104, 86) if z == fl else CAVE_DK)
        # stone portal frame at y 402
        for x in range(px - 4, px + 5):
            for z in range(51, 59):
                if abs(x - px) >= 3 or z <= 53:
                    W.set(x, 402, z, stone_col(x, z, STONE, STONE_DK, (104, 98, 96)))
        mark_keep(W, px - 6, px + 6, 390, 420)


def grotto_and_fort(W):
    # grotto cavern centred (255.5, 418), floor 58
    cx, cy = 255.5, 418
    for x in range(232, 256):
        for y in range(400, 438):
            d = ((x - cx) / 22) ** 2 + ((y - cy) / 16) ** 2
            if d < 1:
                ztop = int(58 - 10 * math.sqrt(1 - d))
                for z in range(ztop, 58):
                    W.clear(x, y, z)
                W.set(x, y, 58, (120, 104, 88))
                if d > 0.75:
                    W.set(x, y, ztop - 1, CAVE_DK)
    # painted underground pool (decor colours) + crystals
    for x in range(240, 256):
        for y in range(422, 432):
            if ((x - 248) / 9) ** 2 + ((y - 427) / 5) ** 2 < 1:
                W.set(x, y, 58, (64, 150, 168))
    rng = np.random.default_rng(77)
    for k in range(9):
        a = rng.uniform(0, math.pi);
        x = int(cx - 20 * abs(math.cos(a)) ); y = int(cy + 14 * math.sin(a) * (1 if k % 2 else -1))
        if x > 255:
            continue
        c = GLOW_CYAN if k % 3 else GLOW_GREEN
        for h in range(rng.integers(2, 5)):
            W.set(x, y, 57 - h, (150, 220, 230) if h else c)
        W.set(x, y, 57, c); W.glow.append((x, y, 57, c))
    # secret vault south, narrow 3-wide passage
    for y in range(433, 446):
        for x in range(254, 258):
            for z in range(55, 58):
                W.clear(x, y, z)
            W.set(x, y, 58, CAVE)
    W.box(248, 263, 444, 452, 53, 57, air=True)
    W.box(248, 263, 444, 452, 58, 58, (150, 132, 100))
    # treasure chest
    W.box(252, 259, 448, 451, 56, 57, WOOD); W.box(252, 259, 448, 451, 55, 55, GOLD_DK)
    W.box(255, 256, 447, 447, 56, 56, GOLD)
    W.set(250, 446, 55, GLOW_YEL); W.glow.append((250, 446, 55, GLOW_YEL))
    # fort ruin on the ridge top
    g = int(np.median(W.H[240:256, 410:432]))
    x0, x1, y0, y1 = 240, 271, 408, 434
    W.box(x0 - 2, x1 + 2, y0 - 2, y1 + 2, g, 52, STONE_DK)
    W.box(x0 - 2, x1 + 2, y0 - 2, y1 + 2, 0, g - 1, air=True)
    W.H[x0 - 2:x1 + 3, y0 - 2:y1 + 3] = g
    rngf = np.random.default_rng(91)
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            edge = min(x - x0, x1 - x, y - y0, y1 - y)
            if edge < 2:
                # broken top line: ruined height varies smoothly
                ht = 12 + int(5 * math.sin(x / 4.0 + y / 5.0)) - (6 if (x < 248 and y > 428) else 0)
                for z in range(g - ht, g):
                    W.set(x, y, z, stone_col(x + y, z, (196, 182, 162), (166, 152, 134), (140, 128, 116)))
                if ht > 10 and edge == 0 and (x + y) % 3 == 0:
                    W.set(x, y, g - ht - 1, (196, 182, 162))
    # gate openings N and S (and broken W wall gap)
    W.box(250, 261, y0, y0 + 1, g - 6, g - 1, air=True)
    W.box(250, 261, y1 - 1, y1, g - 6, g - 1, air=True)
    W.box(x0, x0 + 1, 416, 424, g - 5, g - 1, air=True)
    # windows
    for x in range(x0 + 4, x1 - 2, 6):
        W.box(x, x + 1, y0, y0 + 1, g - 9, g - 8, air=True)
        W.box(x, x + 1, y1 - 1, y1, g - 9, g - 8, air=True)
    # rubble
    for k in range(10):
        rx = int(rngf.integers(x0 + 2, 255)); ry = int(rngf.integers(y0 + 2, y1 - 1))
        W.set(rx, ry, g - 1, (176, 164, 146))
    # spiral shaft from the fort courtyard down to the grotto floor
    spiral_stair(W, 255.5, 421, g, 58, r=4, col=STONE, core=STONE_DK)
    cyl(W, 255.5, 421, 5.5, g - 1, g - 1, (150, 140, 124), inner=4.6)
    # lantern on the fort wall
    W.set(x0 + 2, y0 + 2, g - 1, GLOW_AMBER); W.glow.append((x0 + 2, y0 + 2, g - 1, GLOW_AMBER))
    mark_keep(W, x0 - 4, 256, y0 - 4, y1 + 4)


def ridge_stairs(W):
    """Open-cut stairs from the south meadow up the ridge's north face (x 160-163 and 222-225)."""
    for px in (162, 224):
        z = int(W.H[px, 396])
        y = 397
        while y < 432:
            z -= 1
            if y > 402 and z <= int(W.H[px, y]):
                break
            for x in range(px - 2, px + 2):
                gz = int(W.H[x, y])
                for zz in range(z, 63):
                    if not W.S[x, y, zz]:
                        W.set(x, y, zz, STONE)
                W.set(x, y, z, (190, 176, 150))
                for zz in range(min(gz, z - 3), z):
                    W.clear(x, y, zz)
                W.H[x, y] = z
            y += 1
        mark_keep(W, px - 4, px + 4, 392, y + 2)


# ---------------- hollow logs ----------------
def hollow_log(W, cx, cy, length, along='x', rng=None):
    g = int(W.H[cx, cy])
    r = 3.6
    bark = (118, 82, 52); bark_dk = (92, 62, 40); ring = (196, 160, 110)
    for t in range(-length // 2, length // 2 + 1):
        for a in range(-5, 6):
            for b in range(-5, 6):
                d = math.hypot(a, b)
                if d <= r + 0.3:
                    x = cx + (t if along == 'x' else a)
                    y = cy + (a if along == 'x' else t)
                    z = g - 1 - int(round(r)) + b
                    end = abs(t) == length // 2
                    if d >= r - 1.0:
                        c = ring if end else (bark if (t + b) % 4 else bark_dk)
                        W.set(x, y, z, c)
                    elif not end:
                        W.clear(x, y, z)
    # moss on top
    for t in range(-length // 2, length // 2 + 1, 2):
        x = cx + (t if along == 'x' else 0); y = cy + (0 if along == 'x' else t)
        zt = W.column_top(x, y, 0)
        W.set(x, y, zt, (110, 170, 74))
    if along == 'x':
        mark_keep(W, cx - length // 2 - 2, cx + length // 2 + 2, cy - 5, cy + 5)
    else:
        mark_keep(W, cx - 5, cx + 5, cy - length // 2 - 2, cy + length // 2 + 2)


# ---------------- pond crossings ----------------
def pond_crossings(W):
    # north pond: arched wooden footbridge along x at y 166..169 from x 226 to the centre line
    y0, y1 = 166, 169
    for x in range(224, 256):
        t = (x - 224) / 31.5
        z = 57 - int(round(3 * math.sin(t * math.pi / 2)))
        for y in range(y0, y1 + 1):
            W.set(x, y, z, WOOD_LT if x % 3 else WOOD)
            W.set(x, y, z + 1, WOOD_DK)
        for y in (y0 - 1, y1 + 1):
            W.set(x, y, z - 1, WOOD_DK if x % 4 == 0 else WOOD)
            if x % 4 == 0:
                for zz in range(z, 63):
                    W.set(x, y, zz, WOOD_DK)  # support posts down to the bed
    # south pond: stepping stones (3x3, top z 61) on a gentle arc
    for k, x in enumerate(range(229, 256, 5)):
        y = 344 + int(round(3 * math.sin(k)))
        for dx in range(3):
            for dy in range(3):
                for z in range(61, 64):
                    W.set(x + dx, y + dy, z, STONE if z == 61 else STONE_DK)
    # lily pads (painted on the bed would be invisible: use z 62 pads next to stones)
    rng = np.random.default_rng(31)
    for k in range(14):
        x = int(rng.integers(232, 256)); y = int(rng.integers(152, 186)) if k % 2 else int(rng.integers(330, 360))
        if W.H[x, y] == 63:
            W.set(x, y, 62, (84, 168, 82)); W.set(x + 1, y, 62, (84, 168, 82))
            if k % 3 == 0:
                W.set(x, y, 61, (244, 170, 196))


# ---------------- bloom lanterns (tall glowing flowers) ----------------
def bloom_lantern(W, x, y, rng):
    g = int(W.H[x, y])
    h = int(rng.integers(5, 9))
    stalk = (88, 150, 66)
    for z in range(g - h, g):
        W.set(x, y, z, stalk)
    # leaves
    for z in (g - 2, g - 4):
        d = rng.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
        W.set(x + d[0], y + d[1], z, (110, 176, 74))
    zc = g - h - 2
    petal = [(244, 150, 176), (250, 206, 120), (200, 160, 236), (250, 236, 200)][rng.integers(4)]
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                if abs(dx) + abs(dy) + abs(dz) == 1:
                    W.set(x + dx, y + dy, zc + dz, petal)
    gl = GLOW_YEL if rng.random() < 0.6 else GLOW_AMBER
    W.set(x, y, zc, gl); W.glow.append((x, y, zc, gl))
    W.set(x, y, zc + 1, stalk)


def mushroom_gate(W):
    """Two giant mushrooms flanking the spawn front lane; their caps meet high overhead (open passage beneath,
    ~15 voxels of clearance) and hide much of the spawn from the platform."""
    g = 46
    stem = (238, 228, 202); stem_dk = (214, 200, 170)
    caps = [((154, 229), (157, 241), (226, 112, 74)), ((154, 283), (157, 271), (232, 176, 76))]
    for (sx, sy), (cx, cy), capc in caps:
        gz = int(W.H[sx, sy])
        top = 23
        # stem leaning toward the lane centre
        for z in range(top + 4, gz):
            t = (gz - z) / (gz - top - 4)
            px = sx + (cx - sx) * t * 0.9; py = sy + (cy - sy) * t * 0.9
            r = 3.2 + (1.2 if z > gz - 3 else 0) + 0.6 * (1 - t)
            cyl(W, px, py, r, z, z, stem if z % 4 else stem_dk)
        # ring skirt
        zs = top + 9
        t = (gz - zs) / (gz - top - 4)
        cyl(W, sx + (cx - sx) * t * 0.9, sy + (cy - sy) * t * 0.9, 5.2, zs, zs, (246, 236, 214), inner=3.4)
        seed = h32(sx, sy)

        def cc(x, y, z, d, capc=capc, seed=seed):
            out = np.empty((len(x), 3))
            for i, (xi, yi, zi) in enumerate(zip(x, y, z)):
                c = SPOT if h32(xi // 4, yi // 4, zi // 3, seed) % 7 == 0 else capc
                tt = np.clip((zi - (top - 1)) / 8.0, 0, 1)
                out[i] = mix(c, shade(c, 0.82), tt * 0.7)
            return np.clip(out, 0, 255).astype(np.uint8)
        W.ellipsoid(cx, cy, top + 4, 14, 14, 6, cc)
        # flatten underside below z top+5, keep stem
        for x in range(cx - 17, cx + 18):
            for y in range(cy - 16, cy + 17):
                for z in range(top + 6, top + 12):
                    W.clear(x, y, z)
        cyl(W, cx, cy, 13.5, top + 5, top + 5, (216, 188, 152), inner=4.0)  # gills
        # redraw stem through the cap underside
        for z in range(top + 5, gz):
            t = (gz - z) / (gz - top - 4)
            px = sx + (cx - sx) * t * 0.9; py = sy + (cy - sy) * t * 0.9
            r = 3.2 + (1.2 if z > gz - 3 else 0) + 0.6 * (1 - t)
            cyl(W, px, py, r, z, z, stem if z % 4 else stem_dk)
        # hanging glow lantern under each cap
        W.set(cx, cy + (6 if cy < 256 else -6), top + 6, GOLD_DK)
        W.set(cx, cy + (6 if cy < 256 else -6), top + 7, GLOW_AMBER)
        W.glow.append((cx, cy + (6 if cy < 256 else -6), top + 7, GLOW_AMBER))
    mark_keep(W, 140, 174, 212, 300)


def toy_wall_ruin(W, x0, y0, seed):
    """Small tumbled wall of toy blocks with window gaps: low cover in the centre band."""
    rng = np.random.default_rng(seed)
    g = int(np.median(W.H[x0:x0 + 24, y0:y0 + 6]))
    W.box(x0 - 1, x0 + 24, y0 - 1, y0 + 6, g, 63, (118, 92, 66))
    W.box(x0 - 1, x0 + 24, y0 - 1, y0 + 6, 0, g - 1, air=True)
    for x in range(x0 - 1, x0 + 25):
        for y in range(y0 - 1, y0 + 7):
            W.set(x, y, g, (112, 180, 70))
    for i in range(4):
        if i == 2:
            continue  # gap to walk through
        toy_block(W, x0 + i * 6, y0, g - 5, sx=6, sy=5, sz=5, col=TOY[(i + seed) % 5], emblem=i % 3)
    for i in (0, 3):
        toy_block(W, x0 + i * 6, y0, g - 10, sx=6, sy=5, sz=5, col=TOY[(i + seed + 2) % 5], emblem=(i + 1) % 3)
    # a tumbled block lying beside the wall
    toy_block(W, x0 + 9, y0 + 7, g - 4, sx=5, sy=5, sz=4, col=TOY[(seed + 4) % 5], emblem=2)
    mark_keep(W, x0 - 3, x0 + 27, y0 - 3, y0 + 14)
