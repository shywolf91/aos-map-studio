"""Stairs, doors, windows and enterable buildings (owner rule 2026-10-20: every structure is real).

Merged from Bloomhop builds.straight_stair / spiral_stair / stair_hatch, hc_build.stair_run / interior,
Haunted Fairground generate.stair_flight / stair_stack / door / windows_on and aosmap/art.stairs.

Height convention: a *floor* z is the solid voxel a player stands on; the player needs air at z-1..z-3.
z grows downward, so "up one step" is z - 1. Every builder records the rooms it makes in cv.interiors so the
interiors check (babel_checks) can prove each one is reachable and has a way out.
"""
from __future__ import annotations

import math

from .color import shade

HEADROOM = 3          # air a player needs to stand
CLIMB_ROOM = 4        # air over the step you climb FROM (auto-step needs z - 4 clear; nav graph rule)


def straight_stair(cv, x0, y0, y1, floor_z, rise, dx=1, c=(150, 120, 90), mat='stair', cut_above=True,
                   along='x'):
    """Steps rising `rise` levels, one column per step, starting at column x0 and moving by dx.
    Width y0..y1. Step i (1-based) has its top at floor_z - i. along='y' swaps the axes (x0 is then a y and
    y0..y1 an x range). Cuts 4 voxels of climb room above every step and 3 above the landing, which also opens
    the slab above. The column before the first step also needs 4 clear: keep the first step off a wall."""
    def put(a, b, z, col):
        if along == 'x':
            cv.set(a, b, z, col, mat)
        else:
            cv.set(b, a, z, col, mat)

    def cut(a, b, z):
        if along == 'x':
            cv.clear(a, b, z)
        else:
            cv.clear(b, a, z)

    for i in range(1, rise + 1):
        a = x0 + (i - 1) * dx
        for b in range(y0, y1 + 1):
            for z in range(floor_z - i, floor_z):
                put(a, b, z, c if z == floor_z - i else shade(c, 0.85))
            if cut_above:
                for z in range(floor_z - i - CLIMB_ROOM, floor_z - i):
                    cut(a, b, z)
    if cut_above:
        a = x0 + rise * dx
        for b in range(y0, y1 + 1):
            for z in range(floor_z - rise - HEADROOM, floor_z - rise):
                cut(a, b, z)
    return (x0 + (rise - 1) * dx, floor_z - rise)


def switchback_stair(cv, x0, y0, floor_z, rise, flight=6, width=3, c=(150, 120, 90), mat='stair'):
    """Flights of `flight` steps along +x then -x, each `width` wide, stacked in y with a 1-voxel landing.
    Fits a stairwell of (flight + 2) x (2 * width + 1). Returns the top floor z."""
    z = floor_z
    left = rise
    k = 0
    while left > 0:
        n = min(flight, left)
        if k % 2 == 0:
            straight_stair(cv, x0 + 1, y0, y0 + width - 1, z, n, 1, c, mat)
            lx = x0 + n + 1
        else:
            straight_stair(cv, x0 + flight, y0 + width + 1, y0 + 2 * width, z, n, -1, c, mat)
            lx = x0 + flight - n
        z -= n
        left -= n
        # landing joining the two flights
        cv.box(lx - 1 if k % 2 == 0 else lx, lx if k % 2 == 0 else lx + 1, y0, y0 + 2 * width, z, z, c, mat)
        cv.carve(lx - 1 if k % 2 == 0 else lx, lx if k % 2 == 0 else lx + 1, y0, y0 + 2 * width, z - HEADROOM, z - 1)
        k += 1
    return z


def spiral_stair(cv, cx, cy, z_top_floor, z_bot_floor, r=4, c=(140, 140, 146), core=(110, 110, 118),
                 mat='stair'):
    """Spiral inside a round shaft from floor z_bot_floor up to z_top_floor, 1 rise per 45 degrees."""
    for z in range(z_top_floor - HEADROOM, z_bot_floor):        # carve the shaft
        for x in range(int(cx - r - 1), int(cx + r + 2)):
            for y in range(int(cy - r - 1), int(cy + r + 2)):
                if math.hypot(x + 0.5 - cx, y + 0.5 - cy) <= r + 0.5:
                    cv.clear(x, y, z)
    n = z_bot_floor - z_top_floor
    for i in range(1, n + 1):
        zt = z_bot_floor - i
        a0 = (i % 8) * math.pi / 4
        for x in range(int(cx - r - 1), int(cx + r + 2)):
            for y in range(int(cy - r - 1), int(cy + r + 2)):
                d = math.hypot(x - cx, y - cy)
                if 1.2 < d <= r + 0.3:
                    da = (math.atan2(y - cy, x - cx) % (2 * math.pi) - a0) % (2 * math.pi)
                    if da < math.pi / 4 + 0.08:
                        cv.set(x, y, zt, c, mat)
    for x in (int(cx) - 1, int(cx)):
        for y in (int(cy) - 1, int(cy)):
            for z in range(z_top_floor, z_bot_floor):
                cv.set(x, y, z, core, mat)
    return n


def door(cv, x0, x1, y0, y1, floor_z, height=4):
    """Open a doorway (air) through a wall: the box x0..x1, y0..y1 from floor_z - 1 up `height` voxels."""
    cv.carve(x0, x1, y0, y1, floor_z - height, floor_z - 1)


def window(cv, x0, x1, y0, y1, floor_z, sill=2, height=2):
    cv.carve(x0, x1, y0, y1, floor_z - sill - height + 1, floor_z - sill)


def building(cv, x0, x1, y0, y1, ground_z, storeys=2, storey_h=5, wall=(170, 160, 140), floor=(120, 92, 66),
             roof=(110, 70, 60), stair=(150, 120, 90), doors=('E',), door_w=3, windows=True, name='house',
             furnish=True, mat='building'):
    """Enterable box building: walls, a floor slab per storey, real door openings, windows on every storey,
    a straight stair up to every upper floor and a flat roof. ground_z = floor the player stands on inside.
    Records every storey in cv.interiors. Needs an inside length (x) of at least storey_h + 4."""
    n = storeys
    top = ground_z - n * storey_h
    cv.box(x0, x1, y0, y1, top, ground_z, wall, mat)                       # shell
    cv.box(x0, x1, y0, y1, top, top, roof, mat)                            # roof slab
    for k in range(n):
        fz = ground_z - k * storey_h
        cv.carve(x0 + 1, x1 - 1, y0 + 1, y1 - 1, fz - storey_h + 1, fz - 1)  # room air
        cv.box(x0 + 1, x1 - 1, y0 + 1, y1 - 1, fz, fz, floor, mat)         # floor
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        cv.interiors.append([f'{name} floor {k}', cx, cy, fz])
        if windows:
            for wx in range(x0 + 3, x1 - 2, 5):
                window(cv, wx, wx + 1, y0, y0, fz)
                window(cv, wx, wx + 1, y1, y1, fz)
            for wy in range(y0 + 3, y1 - 2, 5):
                window(cv, x0, x0, wy, wy + 1, fz)
                window(cv, x1, x1, wy, wy + 1, fz)
        if furnish and (x1 - x0) >= 8:
            cv.box(x1 - 3, x1 - 2, y1 - 3, y1 - 2, fz - 1, fz - 1, shade(floor, 0.8), 'furniture')   # table
    for k in range(n - 1):            # stairs AFTER every slab exists, so their cut-outs open the slab above
        fz = ground_z - k * storey_h
        sy0 = y0 + 1 if k % 2 == 0 else y1 - 2
        straight_stair(cv, x0 + 2, sy0, sy0 + 1, fz, storey_h, 1, stair)
    cy = (y0 + y1) // 2
    cx = (x0 + x1) // 2
    h = door_w // 2
    for d in doors:
        if d == 'E':
            door(cv, x1, x1, cy - h, cy - h + door_w - 1, ground_z)
        elif d == 'W':
            door(cv, x0, x0, cy - h, cy - h + door_w - 1, ground_z)
        elif d == 'N':
            door(cv, cx - h, cx - h + door_w - 1, y0, y0, ground_z)
        elif d == 'S':
            door(cv, cx - h, cx - h + door_w - 1, y1, y1, ground_z)
    return {'name': name, 'box': (x0, x1, y0, y1, top, ground_z), 'storeys': n}
