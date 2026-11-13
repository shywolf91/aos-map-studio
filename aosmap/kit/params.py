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

# Adopted zone rules (owner, 2026-11-13; AGENTS.md §4, measured as in docs/babel_zone_study.md §9 "Zone rules").
# babel_checks.run_all(zone_rules=True | {overrides}) -> R['zone_rules'] + four summary() rows.
ZONE_RULES = {
    # object detection
    'baseline_window': 25,         # grey-opening window for the estimated ground (features narrower = objects)
    'object_min_h': 2,             # object column: >= 2 above the ground
    'relief_step': 2,              # estimated ground only: a component is an object if >= relief_steep_share of
    'relief_steep_share': 0.5,     # its boundary steps are >= relief_step tall (walls); gentle relief is dropped
    'min_object_cells': 4,         # components smaller than this are not counted as objects
    'applicable_land_min': 0.5,    # a zone with less land than this is "not applicable" (water, sky, void)
    # 1. dress the front (front band x 139-211 / 300-373, y 236-276)
    'front': {'objects': (4, 15), 'share': (0.05, 0.30), 'low_h': 10, 'low_share_min': 0.90,
              'section': 8, 'section_free_min': 0.50},
    # 2. spawn cover: enemy side within 20 of the square (one combined 0-20 share), rear backdrop 20-40
    'spawn_cover': {'cover_h': 3, 'enemy_r': 20, 'enemy_min': 0.25, 'rear_r': (20, 40), 'rear_min': 0.30},
    # 3. under the platform: strip x 212-300, y 240-271; anchor ends = the 6 columns under each platform end
    'under_platform': {'share': (0.15, 0.45), 'min_air': 25, 'anchor_flat_range': 1},
    # 4. centre: median object footprint in the central zone
    'centre': {'box': (150, 362, 130, 382), 'footprint_p50_min': 25},
}
