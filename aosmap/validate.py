"""Map validators. Each rule cites the piqueserver 1.4.2 / client source it mirrors.

These are STATIC checks on voxel data. They do not replace server loading or playtesting.
"""
from __future__ import annotations

import colorsys
from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage

from .vxl import VoxelMap, surface_mask

FACE6 = ndimage.generate_binary_structure(3, 1)   # 6-face connectivity, no edges/corners

# Movement figures derived from pyspades/world_c.cpp (see tools/movement_sim.py). Not playtested.
PLAYER_STAND_CLEARANCE = 3     # standing box spans ~2.7 voxels
PLAYER_CROUCH_CLEARANCE = 2    # crouched box spans ~1.8 voxels
AUTOCLIMB_STEP = 1             # boxclipmove auto-steps 1 voxel (not while sprinting/crouching)
JUMP_APEX = 1.6                # move_player jump v.z = -0.36 -> ~1.6 voxel apex
FALL_DAMAGE_FROM = 10          # first drop height (voxels) that deals damage (approx.)
FALL_LETHAL_FROM = 20          # drop height that deals >= 100 damage (approx.)


@dataclass
class Finding:
    level: str          # 'error' | 'warn' | 'info'
    rule: str
    detail: str
    where: tuple | None = None


@dataclass
class Report:
    findings: list = field(default_factory=list)

    def add(self, level, rule, detail, where=None):
        self.findings.append(Finding(level, rule, detail, where))

    @property
    def errors(self):
        return [f for f in self.findings if f.level == 'error']

    def text(self):
        return '\n'.join(f'[{f.level.upper():5s}] {f.rule}: {f.detail}' + (f' @ {f.where}' if f.where else '')
                         for f in self.findings)


# ---------------------------------------------------------------- structure

def floating_components(solid: np.ndarray):
    """Components not face-connected to any solid voxel at z >= 62.

    Mirrors pyspades vxl_c.cpp check_node(): 6-neighbour flood fill, returns grounded as soon
    as a node with z >= 62 is reached. OpenSpades GameMapWrapper and BetterSpades map.c use the
    same rule. Note: none of them sweep floating geometry at map load; collapse is evaluated only
    around a destroyed voxel (pyspades VXLData.destroy_point).
    """
    lab, n = ndimage.label(solid, structure=FACE6)
    grounded = set(np.unique(lab[:, :, 62:][solid[:, :, 62:]]).tolist())
    objs = ndimage.find_objects(lab)
    sizes = np.bincount(lab.ravel(), minlength=n + 1)
    out = []
    for i in range(1, n + 1):
        if i in grounded:
            continue
        sl = objs[i - 1]
        out.append({'id': i, 'voxels': int(sizes[i]),
                    'bbox': tuple((s.start, s.stop - 1) for s in sl)})
    return out


# ---------------------------------------------------------------- palette rules

def _hls_bytes(rgb):
    """Exactly piqueserver/game_modes/push.py byte_rgb_to_hls()."""
    hls = colorsys.rgb_to_hls(*tuple(c / 255.0 for c in rgb))
    return tuple(int(round(c * 255)) for c in hls)


def push_team_colour_collisions(vm: VoxelMap, team_colors=((0, 0, 255), (0, 255, 0))):
    """Authored colours that Push would classify as a team's player block.

    push.py on_block_destroy: a block counts as team-built if its byte-HLS hue AND saturation
    equal the team colour's (compare_hs). Such authored voxels lose protect_map_blocks protection.
    Default team colours come from piqueserver/config/config.toml ([team1]/[team2] color).
    """
    surf = surface_mask(vm.solid)
    cols = np.unique(vm.color[surf & vm.colored] & 0xFFFFFF)
    team_hs = [(_hls_bytes(t)[0], _hls_bytes(t)[2]) for t in team_colors]
    hits = []
    for c in cols.tolist():
        rgb_ = ((c >> 16) & 255, (c >> 8) & 255, c & 255)
        h, l, s = _hls_bytes(rgb_)
        for ti, ths in enumerate(team_hs):
            if (h, s) == ths:
                hits.append((rgb_, ti))
    return hits


# ---------------------------------------------------------------- arena gates

def arena_gate_selection(vm: VoxelMap, start):
    """Reproduce piqueserver/game_modes/arena.py Gate.record_gate() selection.

    Flood fill over 6 face neighbours accepting voxels whose (r, g, b) from VXLData.get_point()
    equals the start voxel's. get_point() reports (0, 0, 0) for voxels with no stored colour, which
    in a pyspades-loaded map means every HIDDEN voxel - so thick gates are not selected fully.
    Returns (blocks, support_blocks). Python recursion: large gates may hit the recursion limit
    in the real script; we use an explicit stack and report the size instead.
    """
    surf = surface_mask(vm.solid)

    def rgb_at(x, y, z):
        if not vm.solid[x, y, z]:
            return None
        c = int(vm.color[x, y, z]) if (surf[x, y, z] and vm.colored[x, y, z]) else 0
        return ((c >> 16) & 255, (c >> 8) & 255, c & 255)

    target = rgb_at(*start)
    if target is None:
        raise ValueError(f'gate coordinate {start} is not solid (arena raises ArenaException)')
    blocks, support, seen, stack = [], [], set(), [tuple(start)]
    while stack:
        x, y, z = stack.pop()
        if (x, y, z) in seen:
            continue
        seen.add((x, y, z))
        blocks.append((x, y, z))
        touches_other = False
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            nx, ny, nz = x + dx, y + dy, z + dz
            if not (0 <= nx < 512 and 0 <= ny < 512 and 0 <= nz < 64):
                continue
            c = rgb_at(nx, ny, nz)
            if c is None:
                continue
            if c != target:
                touches_other = True
            elif (nx, ny, nz) not in seen:
                stack.append((nx, ny, nz))
        if touches_other:
            support.append((x, y, z))
    return blocks, support


# ---------------------------------------------------------------- spawns / entities

def spawn_check(vm: VoxelMap, x, y, z=None):
    """Check a spawn column. If z is None we emulate the hooks that use VXLData.get_z(x, y):
    the first solid voxel from the TOP (so a roof would win over the floor under it).
    pyspades player.spawn() then places the player at z - 2.4 (eye), feet ~0.15 above the voxel.
    """
    col = vm.solid[x, y]
    if z is None:
        zs = np.flatnonzero(col)
        z = int(zs[0]) if zs.size else 0
    ok_floor = bool(col[z])
    clear = all(not col[z - k] for k in range(1, PLAYER_STAND_CLEARANCE + 1) if z - k >= 0)
    water = z >= 62
    return {'x': x, 'y': y, 'z': z, 'floor_solid': ok_floor, 'headroom_ok': clear, 'in_water': water}


# ---------------------------------------------------------------- full pass

def validate(vm: VoxelMap, *, expect_floating=None, gates=(), spawns=(), team_colors=None) -> Report:
    rep = Report()
    if not vm.solid[:, :, 63].all():
        rep.add('error', 'bottom_layer', 'z = 63 must be solid everywhere (spec)')
    surf = surface_mask(vm.solid)
    missing = surf & ~vm.colored
    if missing.any():
        rep.add('error', 'surface_colour', f'{int(missing.sum())} surface voxels without colour',
                tuple(int(v[0]) for v in np.nonzero(missing)))
    fl = floating_components(vm.solid)
    for f in fl:
        tag = f.get('bbox')
        named = next((k for k, bb in expected_items(expect_floating) if bb == tag), None)
        if named:
            rep.add('info', 'floating_requested', f'{named}: {f["voxels"]} voxels (requested floating feature)', tag)
        else:
            rep.add('error', 'floating', f'{f["voxels"]} voxels not face-connected to z>=62 '
                    '(floating pieces are opt-in: list them in expect_floating if the brief asks for them)', tag)
    if any(expected_items(expect_floating)):
        rep.add('warn', 'floating_collapse_risk', 'requested floating pieces are not protected from collapse: '
                'pyspades check_node removes them if a player builds against one and that block is destroyed, '
                'even under user_blocks_only / protect_map_blocks. Keep them out of build reach or accept it.')
    for name, bb in expected_items(expect_floating):
        if not any(f['bbox'] == bb for f in fl):
            rep.add('error', 'floating_expected_missing', f'{name} was expected to be floating', bb)
    for g in gates:
        blocks, support = arena_gate_selection(vm, g['seed'])
        lvl = 'info' if len(blocks) == g['expect_blocks'] else 'error'
        rep.add(lvl, 'arena_gate', f"{g['name']}: selected {len(blocks)} blocks "
                f"(expected {g['expect_blocks']}), {len(support)} support", g['seed'])
        if len(blocks) > 900:
            rep.add('warn', 'arena_gate_recursion', f"{g['name']} has {len(blocks)} blocks; arena.py "
                    'record_gate is recursive and may hit Python\'s recursion limit (~1000)')
    for s in spawns:
        r = spawn_check(vm, *s['xyz'][:2], s['xyz'][2] if len(s['xyz']) > 2 else None)
        bad = not (r['floor_solid'] and r['headroom_ok']) or r['in_water']
        rep.add('error' if bad else 'info', 'spawn', f"{s['name']}: {r}")
    if team_colors is not None:
        for rgb_, ti in push_team_colour_collisions(vm, team_colors):
            rep.add('warn', 'push_team_colour', f'authored colour {rgb_} has team{ti + 1} hue+saturation; '
                    'push.py would treat it as a player block')
    return rep


def expected_items(expect):
    if not expect:
        return []
    return list(expect.items()) if isinstance(expect, dict) else [(str(i), b) for i, b in enumerate(expect)]


# ---------------------------------------------------------------- entity settling

def settle_entity_z(vm: VoxelMap, x, y, z=1):
    """Exactly pyspades/server.py update_entities(): an entity drops until it rests on the first
    solid voxel in its column (or climbs out if buried). Runs at map load and after every block
    change, so an entity always ends on the TOPMOST surface reachable from its start z downward."""
    s = vm.solid[x, y]
    if z - 1 >= 0 and s[z - 1]:
        z -= 1
        while z - 1 >= 0 and s[z - 1]:
            z -= 1
    else:
        while z < 64 and not s[z]:
            z += 1
    return z


# ---------------------------------------------------------------- push

PUSH_REQUIRED = ('push_blue_spawn', 'push_green_spawn', 'push_blue_cp', 'push_green_cp')


def push_extensions(blue_spawn, blue_cp, green_spawn, green_cp, spawn_range=5, water_damage=100,
                    blue_build_area=None, green_build_area=None, cp_protect_range=None):
    """The user's Push template. 'push': True is the documented convention (push.py docstring);
    piqueserver 1.4.2 push.py itself does not read it - the mode comes from config game_mode."""
    ext = {'push': True, 'push_spawn_range': spawn_range,
           'push_blue_spawn': tuple(blue_spawn), 'push_blue_cp': tuple(blue_cp),
           'push_green_spawn': tuple(green_spawn), 'push_green_cp': tuple(green_cp),
           'water_damage': water_damage}
    if blue_build_area:
        ext['push_blue_build_area'] = tuple(blue_build_area)
    if green_build_area:
        ext['push_green_build_area'] = tuple(green_build_area)
    if cp_protect_range is not None:
        ext['push_cp_protect_range'] = cp_protect_range
    return ext


def check_push(vm: VoxelMap, ext: dict, rep: Report | None = None,
               team_colors=((0, 0, 255), (0, 255, 0))) -> Report:
    """Static checks for piqueserver 1.4.2 game_modes/push.py metadata against the voxels."""
    rep = rep or Report()
    for k in PUSH_REQUIRED:
        if k not in ext:
            rep.add('error', 'push_meta', f'missing {k} (push.py raises "Missing push map metadata")')
    if any(k not in ext for k in PUSH_REQUIRED):
        return rep
    rng = ext.get('push_spawn_range', 5)
    for team in ('blue', 'green'):
        sx, sy, sz = ext[f'push_{team}_spawn'][:3]
        # the OTHER team's intel is placed at this spawn x, y with z=1 (push.py get_entity_location)
        # and settles onto the topmost solid voxel (update_entities)
        iz = settle_entity_z(vm, sx, sy, 1)
        rep.add('info', 'push_intel_settle', f'{team} spawn column: intel will rest at z={iz}', (sx, sy, iz))
        if iz != sz:
            rep.add('error', 'push_intel_not_on_floor', f'{team}: intended floor z={sz} but the intel settles '
                    f'at z={iz} (something above the spawn point, or wrong z in metadata)', (sx, sy))
        # spawn square: every point should be land with standing room (spawn uses get_z = topmost)
        bad = []
        for dx in range(-rng, rng + 1):
            for dy in range(-rng, rng + 1):
                x, y = sx + dx, sy + dy
                z = int(np.argmax(vm.solid[x, y]))
                headroom = z < 3 or not vm.solid[x, y, max(0, z - 3):z].any()
                if z >= 62 or not headroom or abs(z - sz) > 2:
                    bad.append((x, y, z))
        if bad:
            rep.add('error', 'push_spawn_area', f'{team}: {len(bad)} of {(2*rng+1)**2} spawn points land in '
                    f'water, without 3-voxel headroom, or >2 voxels off the intended floor z={sz} '
                    f'(spawn uses the topmost solid voxel), e.g. {bad[0]}', (sx, sy))
        cx, cy, cz0 = ext[f'push_{team}_cp'][:3]
        cz = settle_entity_z(vm, cx, cy, cz0)
        rep.add('info', 'push_cp_settle', f'{team} CP (tent) will rest at z={cz}', (cx, cy, cz))
        if cz >= 62:
            rep.add('error', 'push_cp_water', f'{team} CP column has no land', (cx, cy))
        elif cz != cz0:
            rep.add('warn', 'push_cp_moved', f'{team} CP given z={cz0} but settles at z={cz}', (cx, cy))
    for rgb_, ti in push_team_colour_collisions(vm, team_colors):
        rep.add('error', 'push_team_colour', f'authored colour {rgb_} counts as team{ti + 1} player block '
                '(loses protect_map_blocks protection)')
    return rep


# ---------------------------------------------------------------- babel

BABEL_DEFAULT = {   # piqueserver 1.4.2 scripts/babel_script.py module constants (servers may modify)
    'platform_x': (206, 305), 'platform_y': (240, 271), 'platform_z': 1,
    'bases': ((118, 256), (394, 256)), 'spawn_half': 20,
}


def check_babel(vm: VoxelMap, rep: Report | None = None, params=BABEL_DEFAULT) -> Report:
    rep = rep or Report()
    (x0, x1), (y0, y1) = params['platform_x'], params['platform_y']
    inner = int(vm.solid[x0:x1 + 1, y0:y1 + 1, 0:3].sum())
    margin = int(vm.solid[x0 - 1:x1 + 2, y0 - 1:y1 + 2, 0:3].sum()) - inner
    if inner:
        rep.add('error', 'babel_platform_volume', f'{inner} authored voxels inside the script platform '
                'cells (z 0..2) - the script writes its platform there and blocks building')
    if margin:
        rep.add('warn', 'babel_platform_margin', f'{margin} authored voxels in the 1-voxel margin around the '
                'platform (z 0..2): a foothold touching the platform; check it is intentional')
    h = params['spawn_half']
    tops = []
    for (bx, by) in params['bases']:
        t = np.argmax(vm.solid[bx - h:bx + h + 1, by - h:by + h + 1], axis=2)
        water = int((t >= 62).sum())      # topmost solid is the water plane -> spawn in water
        tops.append(t)
        rep.add('info', 'babel_spawn_zone', f'base {bx},{by}: spawn heights median z={int(np.median(t))}, '
                f'min z={int(t.min())}, water columns={int(water)}', (bx, by))
        if water:
            rep.add('warn', 'babel_spawn_water', f'{int(water)} spawn columns near base {bx},{by} are water')
    a, b = tops
    rep.add('info', 'babel_spawn_symmetry', f'spawn-zone heights equal under x-mirror: '
            f'{(a == b[::-1, :]).mean():.2f}, under 180 rotation: {(a == b[::-1, ::-1]).mean():.2f}')
    return rep
