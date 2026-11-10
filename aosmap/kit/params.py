"""Game constants the kit checks against. [SRC] piqueserver 1.4.2 scripts/babel_script.py (servers may change them,
so every check takes `params` and these are only the defaults)."""

MX, MY, MZ = 512, 512, 64

BABEL_DEFAULT = {
    'platform_x': (206, 305), 'platform_y': (240, 271), 'platform_z': 1,
    'bases': ((118, 256), (394, 256)), 'spawn_half': 20,
    # tower corridors where the *enemy* may not build (blue stands in x 301-384 -> refused, red in x 128-211)
    'tower_corridor_y': (240, 272),
    'team_names': ('blue', 'red'),
}

# movement model shared by every route check [DERIVED] (knowledge base §4)
FALL_SAFE_MAX = 9        # drops <= 9 counted safe
FALL_ANY_MAX = 19        # drops >= 20 are lethal
