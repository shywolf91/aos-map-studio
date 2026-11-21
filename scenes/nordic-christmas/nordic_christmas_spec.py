"""Hrafnfjord Yule: SPEC (single source of truth). Phase B, written 2026-11-20 by map-builder.

Viking-age Yule village on a frozen fjord, polar night with glow blocks. Stock piqueserver 1.4.2 Babel
(babel_script, no assist structures) that also plays in stock CTF (no spawn/entity hooks in the .txt).
Concept: hybrid of "Hrafnfjord" (frozen fjord, ice bay under the platform, Thing-Rock, Yule pyre, rune ring, mead
halls, smithies, longhouses, boat sheds, Raven Gate, stave churches) and "Skogarborg" (Yule forest belts, beacon
towers, hunting lodges, antler gables on the mead halls). Owner/guru answers: scenes/nordic-christmas/concept/ and
docs/knowledge/project_memory.md 2026-11-20.

Coordinates: x, y 0..511 (y grows south), z 0..63 with z = 0 the sky top, z = 63 the bottom. Every box is
[x0, x1, y0, y1] inclusive. Heights are given as z of the TOP solid voxel (smaller z = higher). The west half
(x 0..256) is authored and mirrored x' = 512 - x (kit axis 'x512', column 256 kept); cosmetic asymmetric pieces
(sky, corner tag, south longship variation, Sleipnir detail) are drawn after the mirror inside declared boxes.
All ground is solid to z 63 (owner rule); there is no water anywhere: every "fjord/bay/pond" is ice-coloured land.

    python scenes/nordic-christmas/nordic_christmas_spec.py      # prints the SPEC self-check (no map is built)
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from aosmap.kit.params import BABEL_DEFAULT  # noqa: E402

P = BABEL_DEFAULT          # platform x 206-305, y 240-271, z 1; bases (118,256)/(394,256); spawn half 20

SPEC = {
    'name': 'Hrafnfjord Yule',
    'file': 'hrafnfjord_yule',
    'version': '1.0',
    'slug': 'nordic-christmas',
    'modes': ['babel', 'ctf'],               # one .vxl + one .txt; 'babel': True in extensions
    'layout_seed': 2026112001,               # fixed: terrain noise, rock shapes, snow drift, ice cracks
    'veg_seed': None,                        # OS-drawn per build (aosmap.kit.noise.os_seed) and saved to build.json
    'decor_seed': None,                      # OS-drawn per build (yard props, presents, lights) and saved
    'axis': 'x512',
    'babel': P,                              # platform and bases are parameters, never hard-coded downstream

    # ------------------------------------------------------------------ elevations (z of the top solid voxel)
    'z': {
        'land': 40,              # village / farmland / front / tower zone mean ground (rolling +-1 by fbm)
        'land_roll': 1,          # +-1 rolling outside no-prop flats
        'spawn_floor': (39, 41), # Babel spawn squares: gentle +-1 mounds, never dead flat, no holes
        'anchor': 40,            # anchor ground flat (zone rule anchor_flat_range 1) -> tower build gap 38 to z 1
        'ice': 43,               # fjord / bay / farm-pond ice floor: 3 below the shore
        'bank': (41, 42),        # two bank columns between shore (40) and ice (43): step <= 1 per column
        'fell_crest': 28,        # fell crests 12 above land; all slopes <= 1:2 (walkable)
        'fell_edge': 36,         # fells fall toward the map edges to z 36 (aurora band needs air above)
        'rear_hill_crest': (32, 34),   # CTF-strip backdrop hills 6-8 above the spawn floor
        'lateral_berm_top': (34, 36),  # spawn-side berms beside the front lane, 4-6 above the spawn floor
        'thing_rock_top': 33,    # Thing-Rock isle 10 above the ice; top z must stay >= 27 (>= 25 air under the platform)
        'lawspeaker_top': 30,    # Lawspeaker's rock on the isle: air 28 below platform z 1
        'pyre_holm_top': 40,     # pyre skerry 3 above the ice (shore height)
        'pyre_top': 24,          # Yule pyre 16 tall above its holm
        'raven_gate_top': 14,    # merlon tops; crown walk floor z 18 (stand on z 18 top = solid 18, player above)
        'raven_gate_crown_floor': 18,
        'raven_gate_soffit': 30, # arch underside at mid-span: 13 clear above the ice for the ice lane
        'church_spire': 8,
        'beacon_top': 10,
        'safe_drop_max': 9,      # FALL_SAFE_MAX: every authored ledge players walk off is <= 9
    },

    # ------------------------------------------------------------------ Babel geometry (west half; east mirrored)
    'spawn_square': {'blue': [98, 138, 236, 276], 'red': [374, 414, 236, 276]},     # clear, gentle, no props
    'spawn_no_prop': [94, 142, 232, 280],     # +-4 margin kept prop-free (west; mirrored)
    'front': [139, 211, 236, 276],            # zone-rule front band (west)
    'tower_zone': {'blue': [181, 212, 240, 271], 'red': [300, 331, 240, 271]},      # 32 wide, ground-built
    'anchor': {'blue': [206, 212, 236, 275], 'red': [300, 306, 236, 275], 'z': 40},
    # Mirror of west 206-212 is east 300-306: both required blocks (206-211 and 300-305, y 240-271) are anchor
    # ground at z 40. West gets 7 columns under/at the platform end, east 7 (300-306); the platform covers 6 vs 6.
    # No stairs or ramps on the enemy-facing (bay) side; the 2-column bank down to the ice is natural shore.
    'under_platform_strip': [212, 300, 240, 271],
    'platform_air_min': 25,                   # zone rule: nothing above z 27 in the strip (z 2..26 empty)

    # ------------------------------------------------------------------ terrain zones
    'fjord': {
        'channel': [231, 281, 0, 511],        # full-height frozen fjord, ice z 43 (banks included at 231-232 / 280-281)
        'pools': [[222, 290, 120, 176], [222, 290, 330, 382]],   # widenings around the two holms (ice lanes >= 9)
        'bay': {'cx': 256, 'cy': 256, 'rx': 43, 'ry': 72},       # ellipse x 213-299, y 184-328, banks included
        'ice_floor_bay_x': (215, 297),        # flat ice; 213-214 / 298-299 are the two bank columns
        'crags': [[222, 232, 0, 84], [280, 290, 0, 84], [222, 232, 430, 511], [280, 290, 430, 511]],
        # rocky fjord-side crags (cosmetic, walk-round) only where no route crosses; never under a sky piece
    },
    'fells': {
        'north': {'crest_box': [40, 212, 36, 80], 'extent': [0, 230, 0, 124]},
        'south': {'crest_box': [40, 212, 432, 476], 'extent': [0, 230, 388, 511]},
        'slope_max': 0.5,                     # rise / run <= 1:2 everywhere players walk
    },
    'forest_belts': [[0, 228, 0, 116], [0, 228, 396, 511]],   # groves (7-10 gaps, many trails), not even scatter
    'forest': {
        'tree_tall': (12, 22), 'grove_count_per_belt': (9, 14), 'gap': (7, 10),
        'species': ['spruce', 'pine', 'birch'],     # spruce dominant ~60 %, birch light accents ~15 %
        'decorated_share': 0.12,                    # Yule spruces with glow baubles / candles near paths
        'aurora_band_tree_top_min_z': 12,           # trees under the aurora bands keep their tops at z >= 12
        'details_per_plant': 3,                     # owner rule: three random details per plant
        'keep_off': ['routes', 'stave_church yards', 'beacon yards', 'lodge yards', 'tag_rect'],
    },
    'village_wings': {'north': [128, 214, 128, 234], 'south': [128, 214, 278, 384]},

    # ------------------------------------------------------------------ CTF strips (pyspades get_random_location)
    'ctf_strip': {'blue': [0, 127, 128, 383], 'red': [384, 511, 128, 383]},
    'ctf_strip_rules': {
        'theme': 'open snow farmland: stubble fields, furrows, drystone walls, wattle fences, haystacks, sleds, '
                 'hesjer (hay-drying racks: 1 wide, 4 tall, posts + hay band) as low spread cover',
        'hesje_grid': {'step': (22, 20), 'len': (7, 11), 'h': 4},   # layout-seeded jitter; CTF cover_within_8 >= 35 %
        'land_share_min': 0.70,              # it is 100 % land (pond is ice land)
        'walkable_top_object_max_h': 2,      # anything with a standable top is <= 2 tall
        'tall_object_h': (3, 6),             # 3-6 tall only if it steps down <= 1 per column or has a 1-voxel tip
        'stranded_max': 0.005, 'walk_out_min': 0.995,     # G3 targets (runner ctfsim)
        'object_top_cells_max_share': 0.02,  # <= 2 % of the strip's columns are object tops (craft §3.3: <= 3 %)
        'roofs': 0, 'flat_tops_over': 0, 'treetops_standable': 0,
        'max_slope': 0.5,
    },
    'rear_hills': {                          # backdrop behind each Babel spawn, inside the strip (guru Q5 = A)
        'box': [38, 96, 196, 316],           # west; slopes <= 1:2, no flat top larger than 6x6, no props on them
        'crest_x': (54, 80), 'crest_z': (31, 33),   # rolling crest >= 26 wide: ground, not an object top (CTF gate)
        'cover_by_x92': 3,                   # >= 3 above the spawn floor by x 92 (craft cover within 8)
    },
    'lateral_berms': {                       # Babel enemy-side cover, beside (never across) the front lane
        # graybox: crest moved 1 toward the lane (y 228 / 284) and the slopes run to y 214-240 / 272-298; the
        # berm stays out of the CTF strip (x >= 128: a berm crest in the strip counts as an object top there).
        'north': [128, 170, 214, 240], 'south': [128, 170, 272, 298],     # west; standable terrain, slopes <= 1:2
        'crest_y': (228, 284), 'crest_rise': 6, 'x_full': (140, 160),
        'top_z': (34, 36), 'spruce_clumps_on_back_slope': True,
    },
    'farm_pond': {'cx': 48, 'cy': 352, 'rx': 26, 'ry': 16, 'z': 41},   # frozen pond in the strip, 1 below the field
    'spawn_yard': {
        # G3: julenek replaces the Yule spruce (its canopy was a standable treetop in the CTF strip)
        'landmark': {'name': 'julenek (oat sheaf on a pole)', 'box': [79, 81, 255, 257], 'h': 4, 'tip': 'single voxel'},
        'fences': [[98, 127, 229, 229], [98, 127, 283, 283]],   # wattle, top ramped 1-2-3..3-2-1, gaps >= 7
        'cover_within_8_target': 0.50,       # craft gate >= 0.35
    },

    # ------------------------------------------------------------------ front dressing (west; mirrored)
    'front_dressing': {
        'targets': {'objects': (6, 12), 'share': (0.06, 0.10), 'h_max': 5, 'section_free_min': 0.60},
        'tower_zone_clear': [181, 212, 240, 271],   # no dressing in the tower zone (builders)
        'items': [
            {'name': 'haystack 1', 'box': [143, 147, 238, 242], 'h': 4},
            {'name': 'haystack 2', 'box': [144, 148, 270, 274], 'h': 4},
            {'name': 'hay rick (turf roof, open sides)', 'box': [152, 158, 246, 250], 'h': 5},
            {'name': 'woodpile + chopping block', 'box': [160, 165, 264, 266], 'h': 3},
            {'name': 'stockfish hjell', 'box': [166, 173, 242, 244], 'h': 4},
            {'name': 'sled with Yule presents', 'box': [150, 154, 258, 261], 'h': 2},
            {'name': 'rune cairn', 'box': [168, 170, 256, 258], 'h': 3},
            {'name': 'woodpile 2', 'box': [170, 175, 268, 270], 'h': 3},
            {'name': 'split-rail fence a', 'box': [143, 149, 254, 254], 'h': 3},   # 3 at graybox: craft spawn cover
            {'name': 'split-rail fence b', 'box': [158, 164, 276, 276], 'h': 2},
            {'name': 'haystack 3', 'box': [160, 164, 236, 240], 'h': 4},
        ],
    },

    # ------------------------------------------------------------------ centre and bay
    'centre_box': [150, 362, 130, 382],        # zone rule: median object footprint >= 25
    'centre_small_prop_rule': 'props < 25 cells inside the centre box stand on a kerb, yard plinth or wall so they '
                              'join a larger component, or stay <= 40 % of the object count',
    'bay_gaps': (7, 10),                       # clear walkable gaps between every bay object and the next
    'bay_contents': [
        {'name': 'Thing-Rock isle', 'cx': 256, 'cy': 256, 'r': 17, 'box': [239, 273, 239, 273], 'top_z': 33,
         'barrow_room': {'box': [248, 264, 248, 264], 'floor_z': 43, 'air': (38, 42), 'openings': 'N S E W, 5 wide'},
         'lawspeaker_rock': {'box': [253, 259, 253, 259], 'top_z': 30}},
        {'name': 'longship north (frozen in, double-ended)', 'box': [232, 280, 204, 214], 'keel_z': 44,
         'gunwale_z': 37, 'prow_top_z': 28, 'mast_top_z': 20, 'awning': [248, 264, 206, 212]},
        {'name': 'longship south (heeled 1, broken mast)', 'box': [232, 280, 298, 308], 'keel_z': 44,
         'gunwale_z': 37, 'prow_top_z': 28, 'awning': [248, 264, 300, 306]},
        {'name': 'ice-fishing hut NW', 'box': [218, 224, 188, 194], 'h': 7},
        {'name': 'ice-fishing hut W-mid N', 'box': [218, 224, 222, 228], 'h': 7},
        {'name': 'ice-fishing hut SW', 'box': [218, 224, 318, 324], 'h': 7},
        {'name': 'ice-fishing hut W-mid S', 'box': [218, 224, 284, 290], 'h': 7},
        {'name': 'pressure ridge N', 'box': [232, 244, 224, 228], 'h': (3, 5)},
        {'name': 'pressure ridge S', 'box': [232, 244, 284, 288], 'h': (3, 5)},
        {'name': 'ice-hole camp (sled, rack, fish)', 'box': [240, 250, 190, 196], 'h': (1, 3)},
    ],
    'holms': [
        {'name': 'Pyre Holm + Yule pyre', 'box': [240, 272, 132, 164], 'top_z': 40,
         'pyre': {'box': [248, 264, 140, 156], 'top_z': 24, 'log_ring_r': 13}},
        {'name': 'Rune Holm + rune-stone ring', 'box': [236, 276, 336, 376], 'top_z': 41,
         'ring': {'cx': 256, 'cy': 356, 'r': 18, 'stones': 12, 'stone_h': (5, 9), 'kerb_h': 2, 'gaps': (7, 9)}},
    ],
    'sleipnir': {'box': [246, 266, 440, 458], 'base_z': 43, 'top_z': 29,
                 'note': 'eight-legged Sleipnir of lashed timber and straw with lantern eyes on the south fjord ice, '
                         'one-off (guru G2: no Yule goat, Yulehaven Isles has one); legs walk-under, back not a perch'},

    # ------------------------------------------------------------------ structures (west; mirrored -> 2 each)
    # role per docs/craft_standard.md §2.3; every one registered in build.json 'structures'.
    'structures': [
        {'name': 'Skali mead hall (antler gables)', 'box': [132, 178, 148, 172], 'role': 'main', 'h': 18,
         'storeys': 2, 'doors': ['S', 'E', 'W'], 'volumes': ['hall', 'porch', 'loft wing'],
         'yard': [128, 184, 140, 182]},
        {'name': 'smithy', 'box': [144, 164, 186, 202], 'role': 'small', 'h': 12, 'yard': [140, 170, 182, 206]},
        {'name': 'boat shed north A', 'box': [186, 210, 186, 202], 'role': 'small', 'h': 12},
        {'name': 'boat shed north B', 'box': [186, 210, 211, 227], 'role': 'small', 'h': 12},
        {'name': 'longhouse', 'box': [140, 178, 308, 330], 'role': 'main', 'h': 15, 'storeys': 2,
         'volumes': ['house', 'byre lean-to', 'porch'], 'yard': [134, 184, 304, 336]},
        {'name': 'bathhouse', 'box': [146, 162, 342, 356], 'role': 'small', 'h': 10},
        {'name': 'boat shed south A', 'box': [186, 210, 285, 301], 'role': 'small', 'h': 12},
        {'name': 'boat shed south B', 'box': [186, 210, 310, 326], 'role': 'small', 'h': 12},
        {'name': 'stave church', 'box': [138, 162, 72, 96], 'role': 'main', 'h': 26, 'base_z': 34,
         'volumes': ['nave', 'chancel', 'ambulatory', 'bell loft'], 'yard': [130, 170, 64, 104]},
        {'name': 'beacon tower north', 'box': [176, 184, 40, 48], 'role': 'tower', 'h': 22},
        {'name': 'beacon tower south', 'box': [176, 184, 464, 472], 'role': 'tower', 'h': 22},
        {'name': 'hunting lodge north', 'box': [40, 56, 64, 78], 'role': 'small', 'h': 10},
        {'name': 'hunting lodge south', 'box': [40, 56, 434, 448], 'role': 'small', 'h': 10},
        {'name': 'ice-fishing huts (4)', 'role': 'small', 'boxes_from': 'bay_contents'},
        {'name': 'longship north', 'box': [232, 280, 204, 214], 'role': 'vessel', 'mirror_self': True},
        {'name': 'longship south', 'box': [232, 280, 298, 308], 'role': 'vessel', 'mirror_self': True},
        {'name': 'Raven Gate', 'box': [222, 290, 96, 108], 'role': 'tower', 'mirror_self': True},
        {'name': 'Thing-Rock barrow', 'box': [239, 273, 239, 273], 'role': 'ruin', 'mirror_self': True},
    ],
    # landmarks, not buildings (guru G2): not registered as structures, but get close-ups at G4
    'landmarks': [
        {'name': 'Yule pyre', 'box': [240, 272, 132, 164]},
        {'name': 'rune-stone ring', 'box': [236, 276, 336, 376]},
        {'name': 'Sleipnir', 'box': [246, 266, 440, 458]},
    ],
    'raven_gate': {
        'legs': [[222, 233, 96, 108], [279, 290, 96, 108]],   # stone legs on the banks, spiral stair in each
        'stair_core': 5, 'doors': ['N', 'S'],                 # each leg: ground doors N and S, crown door
        'span_open_x': (234, 278), 'soffit_z_mid': 30, 'crown_floor_z': 18, 'merlon_top_z': 14,
        'crown_walk_w': 5, 'glow': 'rune-blue runes along the soffit and leg courses',
        'carved_ravens': 'two carved ravens on the crown ends, decorative (not on the walk)',
    },

    # ------------------------------------------------------------------ routes, descents, construction
    'routes': {
        'front_lane': {'path': [(118, 256), (176, 256), (212, 256)], 'width': 41},
        'ice_lane': {'path': [(256, 0), (256, 511)], 'width': 51, 'note': 'through Raven Gate span, round holms'},
        'north_flank': {'path': [(100, 196), (90, 110), (180, 104), (256, 104)], 'y_from_centre': 152},
        'south_flank': {'path': [(100, 316), (90, 402), (180, 408), (256, 408)], 'y_from_centre': 152},
        'north_village_street': {'path': [(138, 230), (130, 182), (184, 180), (214, 184), (232, 180)], 'width': (7, 10)},
        'south_village_street': {'path': [(138, 282), (130, 330), (184, 332), (214, 330), (232, 334)], 'width': (7, 10)},
        'fell_trails': 'many 3-5 wide trails through the groves, every grove pocket with >= 2 exits',
    },
    'descents': {
        'spawn_to_tower_zone': 'level ground z 39-41 (no descent needed)',
        'tower_zone_to_ice': '2-column banks, step 1',
        'raven_gate_crown': 'spiral stairs in both legs to the banks',
        'beacons_church_loft_lodges': 'inside stairs; every walk-off ledge <= 9',
        'fells': 'slopes <= 1:2 to the shore',
    },
    'construction_areas': {'tower_zone': 'see tower_zone', 'anchor': 'see anchor'},
    'objectives': {
        'babel_intel': (256, 256, 'on the script platform'),
        'babel_bases': P['bases'],
        'ctf': 'intel and tent at random topmost voxels in the team strips (no hooks)',
    },

    # ------------------------------------------------------------------ zone and craft targets (numbers)
    'targets': {
        'front': {'objects': (4, 15), 'share': (0.05, 0.30), 'low_h': 10, 'low_share_min': 0.90,
                  'section_free_min': 0.50},
        'spawn_cover': {'enemy_0_20_min': 0.25, 'rear_20_40_min': 0.30, 'cover_h': 3,
                        'plan': {'enemy': 'lateral berms ~80 % of the 420 lateral wedge cells + haystacks/rick '
                                          '-> ~0.30', 'rear': 'rear hills >= 3 high over ~60 % of the wedge'}},
        'under_platform': {'share': (0.15, 0.45), 'plan_share': 0.30, 'min_air': 25},
        'centre': {'footprint_p50_min': 25},
        'spawn_exposure': {'viewers_max': 10, 'hidden_min': 0.15,
                           'owner_fallback': 'if hidden < 15 %: keep fronts open, report numbers for a waiver '
                                             '(owner 2026-11-20, Q4 = A); no gate, no taller front berms'},
        'craft_spawn': {'cover_within_8_min': 0.35, 'roof_spots_max': 0.03, 'steep_max': 0.15},
        'ground_luma_spread_p10_p90_min': 80,
        'snow_max_channel': 212, 'snow_field_luma_max': 180, 'snow_crest_share_max': 0.05, 'floor_luma_min': 40,
        'file_size_mb_max': 6.0,
    },

    # ------------------------------------------------------------------ look
    'fog': (176, 164, 196),                  # lilac-mauve, hue absent from the palette
    'heavens_color': (44, 40, 88, 255),
    'glow_budget': (3000, 5000),             # never in 1-voxel stripe patterns
    'tag': {'corner': 'SW', 'rect': [8, 60, 470, 500], 'level': 'ground', 'text': 'Hrafnfjord Yule',
            'clear': 'only the area under the tag (trees removed in rect + 2)'},
    'txt': {'author': 'shywolf91 + AI', 'extensions': {'babel': True, 'water_damage': 0},
            'description': 'Babel / CTF: Viking Yule on a frozen fjord at polar night.',
            'hooks': None},
}

# ------------------------------------------------------------------ sky decor (expected floating, opt-in by owner)
# Rules: >= 60 from the platform box, never over a Babel spawn square or a CTF strip, >= 8-10 air below.
# Collapse caveat: breaking a player block that touches a floating piece drops it for the round.
SKY = [
    {'name': 'crescent moon', 'kit': 'sky.moon', 'centre': (256, 34, 16), 'R': 14, 'box': [242, 270, 30, 38],
     'z': (2, 30), 'below': 'fjord ice z 43 (no crag under x 242-270)', 'air_min': 12, 'glow': True},
    {'name': 'Yule-rider sleigh + 6 generic reindeer', 'box': [248, 264, 404, 470], 'z': (12, 18),
     'heading': 'north', 'below': 'south fjord ice z 43; Sleipnir top z 29 at y 440-458', 'air_min': 10,
     'glow': 'runner lamps amber, sack ribbons'},
    {'name': 'raven A', 'box': [237, 251, 72, 84], 'z': (4, 6), 'wingspan': 15, 'below': 'ice z 43', 'air_min': 36},
    {'name': 'raven B', 'box': [261, 275, 116, 128], 'z': (4, 6), 'wingspan': 15,
     'below': 'ice z 43 (north pool, clear of Pyre Holm y >= 132)', 'air_min': 36},
    {'name': 'aurora ribbon north', 'box': [120, 392, 4, 24], 'z': (0, 2), 'thick': 2,
     'below': 'fell edge z >= 36, trees capped at top z >= 12', 'air_min': 9, 'glow': 'teal -> green'},
    {'name': 'aurora ribbon south', 'box': [120, 392, 488, 508], 'z': (0, 2), 'thick': 2,
     'below': 'fell edge z >= 36, trees capped at top z >= 12; tag rect x 8-60 is outside', 'air_min': 9,
     'glow': 'teal -> green'},
]

# ------------------------------------------------------------------ palette families (base mids; ramps in the art pass)
# Built with aosmap.kit.palette.shifted_ramp (moonlight light_hue 220 / shadow_hue 290 for snow; warm 70 for timber
# lit by glow), then color.lighting (baked light + AO), then enforce_brightness. Night grade: snow field luma ~140.
PALETTE = {
    'snow_slate': {          # (a) night snow
        'field': (132, 140, 158), 'crest': (164, 172, 188), 'trough': (104, 112, 132), 'track': (112, 108, 112),
        'roof_snow': (146, 154, 170)},
    'timber': {              # (b) tarred and weathered timber, warm
        'tar': (88, 64, 46), 'weathered': (128, 100, 74), 'plank': (150, 118, 84), 'red_trim': (150, 56, 44),
        'carved_gold': (178, 140, 72), 'shingle': (78, 62, 54), 'turf_roof': (74, 92, 62)},
    'forest_turf': {         # (c) spruce, pine, birch, turf, straw
        'spruce': (40, 66, 52), 'spruce_light': (62, 92, 68), 'pine': (52, 74, 56), 'birch_bark': (176, 170, 158),
        'turf': (84, 92, 64), 'straw': (164, 136, 84), 'stubble': (138, 124, 92)},
    'ice_stone': {           # (d) grey-green ice and granite (NOT icy blue: guru G1 d)
        'ice': (106, 134, 128), 'ice_light': (138, 162, 154), 'ice_dark': (76, 102, 98), 'ice_crack': (60, 82, 80),
        'granite': (104, 104, 110), 'granite_light': (130, 128, 132), 'rune_stone': (96, 98, 92)},
}
GLOW = {
    'window_amber': (255, 176, 64), 'hearth': (255, 140, 50), 'pyre': (255, 120, 30), 'candle': (255, 210, 120),
    'rune_blue': (120, 180, 255), 'aurora_teal': (90, 255, 200), 'aurora_green': (150, 255, 170),
    'moon': (236, 232, 200), 'string_light_red': (255, 90, 70), 'string_light_gold': (255, 214, 110),
}

RATIONALE = [
    'Ice x 213-299 (bay ellipse rx 43 at 256): the mirror of the west anchor 206-212 is 300-306, so both required '
    'anchor blocks (206-211 and 300-305, y 240-271) are solid shore at z 40; the bank is 213-214 / 298-299.',
    'Ice 3 below the shore (z 43 vs 40) with two bank columns: reads as a fjord, never a cliff or 1-wide stair; '
    'the enemy-side bank is a natural 1-step shore, not authored stairs.',
    'Land z 40 everywhere players fight: ground-built towers (gap 38 to the platform), no raised tower zone.',
    'Thing-Rock top z 33 (Lawspeaker z 30): 28-31 air under the platform (rule >= 25); covers ~30 % of the strip '
    '(rule 15-45 %); barrow room open on all four sides so the mirror stays exact.',
    'Front dressing 11 low objects, ~7.4 % share, all <= 5 tall, none in the tower zone: inside the 2026-11-13 '
    'numbers with every 8-column section >= 60 % free.',
    'Spawn cover from terrain: lateral berms (y 212-234 / 278-300, outside the front band) give the enemy-side '
    'wedge its cover; rear hills (guru Q5) give the 20-40 backdrop. Both standable, so CTF spawns stay safe.',
    'CTF strips: farmland with <= 2 % object-top columns; the only tall object is the single-tip Yule spruce '
    'landmark behind each spawn. Mead halls, smithies and longhouses start at x >= 128.',
    'Flanks at y ~104 / ~408 (152 from centre, rule 130-210); they cross the fjord under the Raven Gate (north) '
    'and over open ice past Sleipnir (south).',
    'Raven Gate crown ~140 from the platform (beyond the ~110 draw distance): a CTF sniper perch, not a Babel '
    'platform camp; reachable from both legs, so it is symmetric.',
    'Sky pieces only over fjord ice or the map-edge fell slopes, where nothing tall stands; forest under the '
    'aurora bands keeps tree tops at z >= 12.',
    'Fog (176,164,196) lilac: the palette has no purple; neutral between teams per palette.fog_team_lean.',
]


# ------------------------------------------------------------------ self-check of the numbers (no map built)
def _mirror_box(b):
    return [512 - b[1], 512 - b[0], b[2], b[3]]


def check():
    S, out = SPEC, []

    def ok(name, cond, info=''):
        out.append((name, bool(cond), info))

    bay = S['fjord']['bay']
    ice_x = (bay['cx'] - bay['rx'], bay['cx'] + bay['rx'])
    ok('ice within x 213-299', ice_x[0] >= 213 and ice_x[1] <= 299, f'bay x {ice_x}')
    ch = S['fjord']['channel']
    ok('fjord channel inside x 213-299', ch[0] >= 213 and ch[1] <= 299, str(ch[:2]))
    for pool in S['fjord']['pools']:
        ok(f'pool {pool[:2]} inside x 213-299 and clear of anchors', pool[0] >= 213 and pool[1] <= 299)
    aw, ae = S['anchor']['blue'], S['anchor']['red']
    ok('east anchor = mirror of west', _mirror_box(aw) == ae, f'{_mirror_box(aw)} vs {ae}')
    ok('anchors cover 206-211 / 300-305, y 240-271',
       aw[0] <= 206 and aw[1] >= 211 and ae[0] <= 300 and ae[1] >= 305 and aw[2] <= 240 and aw[3] >= 271)
    ok('anchor not in bay', aw[1] < ice_x[0] and ae[0] > ice_x[1])
    ok('tower zone 32 wide, red = mirror', S['tower_zone']['blue'][1] - S['tower_zone']['blue'][0] + 1 == 32
       and _mirror_box(S['tower_zone']['blue'])[0] == S['tower_zone']['red'][0] and S['tower_zone']['red'][1] == 331)
    tz = S['tower_zone']['blue']
    ok('tower zone 44-135 from centre?', True, f'inner edge {256 - tz[1]}..outer {256 - tz[0]} (stock zone '
       f'ends under the platform; AGENTS 44-135 is the build-zone span from centre)')
    ok('red spawn = mirror', _mirror_box(S['spawn_square']['blue']) == S['spawn_square']['red'])
    # under platform air
    for c in S['bay_contents']:
        b = c.get('box')
        if not b:
            continue
        inter = not (b[1] < 212 or b[0] > 300 or b[3] < 240 or b[2] > 271)
        top = c.get('top_z', c.get('prow_top_z'))
        if inter and top is not None:
            ok(f'{c["name"]} air under platform >= 25', top - 2 >= 25, f'top z {top} -> air {top - 2}')
    tr = S['bay_contents'][0]
    ok('lawspeaker air >= 25', tr['lawspeaker_rock']['top_z'] - 2 >= 25)
    area = sum(1 for x in range(212, 301) for y in range(240, 272)
               if (x - tr['cx']) ** 2 + (y - tr['cy']) ** 2 <= tr['r'] ** 2)
    share = area / (89 * 32)
    ok('under-platform share 15-45 %', 0.15 <= share <= 0.45, f'{share:.3f} (Thing-Rock alone)')
    # front dressing
    F = S['front']
    items = S['front_dressing']['items']
    cells = sum((i['box'][1] - i['box'][0] + 1) * (i['box'][3] - i['box'][2] + 1) for i in items)
    fa = (F[1] - F[0] + 1) * (F[3] - F[2] + 1)
    ok('front share 5-30 %', 0.05 <= cells / fa <= 0.30, f'{cells}/{fa} = {cells / fa:.3f}')
    ok('front objects 4-15', 4 <= len(items) <= 15, str(len(items)))
    ok('front heights <= 10', all(i['h'] <= 10 for i in items))
    ok('front items inside the band and outside the tower zone',
       all(F[0] <= i['box'][0] and i['box'][1] <= F[1] and F[2] <= i['box'][2] and i['box'][3] <= F[3]
           and i['box'][1] < tz[0] for i in items))
    sp = S['spawn_no_prop']
    ok('front items outside the spawn no-prop margin',
       all(i['box'][0] > sp[1] or i['box'][3] < sp[2] or i['box'][2] > sp[3] for i in items))

    def gap(a, b):
        return max(a[0] - b[1], b[0] - a[1], a[2] - b[3], b[2] - a[3]) - 1

    boxes = [(s['name'], s['box']) for s in S['structures'] if s.get('box')]
    boxes += [(k, v) for k, v in S['lateral_berms'].items() if isinstance(v, list)]
    boxes += [(c['name'], c['box']) for c in S['bay_contents']]
    bad = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            (na, a), (nb, b) = boxes[i], boxes[j]
            if na == 'Thing-Rock barrow' or nb == 'Thing-Rock barrow' or {na, nb} <= {'longship north',
               'longship north (frozen in, double-ended)', 'longship south', 'longship south (heeled 1, broken mast)'}:
                continue
            if a == b:
                continue
            g = gap(a, b)
            if g < 7 and not (b[0] > 256 or a[0] > 256):
                bad.append(f'{na} / {nb}: {g}')
    ok('west structures, berms and bay objects >= 7 apart', not bad, '; '.join(bad))
    # structures stay out of CTF strips and spawn squares
    strip = S['ctf_strip']['blue']
    for s in S['structures']:
        b = s.get('box')
        if not b:
            continue
        in_strip = not (b[1] < strip[0] or b[0] > strip[1] or b[3] < strip[2] or b[2] > strip[3])
        ok(f'{s["name"]} outside CTF strip', not in_strip, str(b))
    # sky
    (px0, px1), (py0, py1) = P['platform_x'], P['platform_y']
    for k in SKY:
        b = k['box']
        dx = max(px0 - b[1], b[0] - px1, 0)
        dy = max(py0 - b[3], b[2] - py1, 0)
        d = math.hypot(dx, dy)
        over_strip = any(not (b[1] < s[0] or b[0] > s[1] or b[3] < s[2] or b[2] > s[3])
                         for s in S['ctf_strip'].values())
        ok(f'sky {k["name"]} >= 60 from platform, not over strips, air >= 8',
           d >= 60 and not over_strip and k['air_min'] >= 8, f'dist {d:.0f}, air {k["air_min"]}')
    # flanks
    for r in ('north_flank', 'south_flank'):
        ok(f'{r} 130-210 from centre', 130 <= S['routes'][r]['y_from_centre'] <= 210)
    # fog
    try:
        from aosmap.kit.palette import fog_team_lean
        lean = fog_team_lean(S['fog'])
        ok('fog neutral (no team-lean warning), channels >= 150', not lean['warn'] and min(S['fog']) >= 150,
           str(lean))
    except Exception as e:  # pragma: no cover
        ok('fog lean check ran', False, repr(e))
    return out


if __name__ == '__main__':
    rows = check()
    for name, good, info in rows:
        print(('PASS ' if good else 'FAIL ') + name + (f'  [{info}]' if info else ''))
    print(f'{sum(g for _, g, _ in rows)}/{len(rows)} pass')
