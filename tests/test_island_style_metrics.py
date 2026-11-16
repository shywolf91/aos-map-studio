"""tools/island_style_metrics.py on a tiny synthetic island written with aosmap.vxl (no third-party map)."""
import os
import sys

from aosmap.vxl import VoxelMap, rgb, save, load

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools'))
from island_style_metrics import measure, classic_table  # noqa: E402

SEA, SAND, WALL, CLOUD = rgb(40, 140, 190), rgb(220, 200, 140), rgb(150, 110, 80), rgb(230, 230, 235)


def _island(tmp_path):
    m = VoxelMap()
    m.set(slice(None), slice(None), 63, SEA)                    # painted sea plane, z 62 air = water
    m.set(slice(60, 452), slice(200, 312), slice(60, 64), SAND)  # one island, 3 high (ground top z 60)
    # a hut on the island: 9x9 walls 4 high with a roof, open inside (roofed columns, one structure)
    m.set(slice(250, 259), slice(170 + 60, 179 + 60), slice(55, 60), WALL)
    m.set(slice(251, 258), slice(171 + 60, 178 + 60), slice(56, 60), None)
    m.set(slice(250, 259), slice(230, 239), 55, WALL)
    m.set(252, 230, slice(56, 59), None)                        # doorway
    # a floating cloud over the sea (sky decor)
    m.set(slice(20, 40), slice(20, 30), slice(10, 13), CLOUD)
    p = tmp_path / 'synthetic_island.vxl'
    save(m, str(p))
    m2, rep = load(str(p))
    assert rep.ok
    return measure(m2, 'synthetic', os.path.getsize(p))


def test_island_metrics(tmp_path):
    r = _island(tmp_path)
    land = 392 * 112
    assert r['land_cols'] == land
    assert r['water_pct'] == round(100 * (1 - land / 512 ** 2), 1)
    assert r['landmasses'] == 1 and r['main_share_pct'] == 100.0
    assert r['main_aspect_x_over_y'] == round(392 / 112, 2)
    assert r['terrain_slope'] == 0.0 and r['cliff_pct'] == 0.0
    assert r['floating_components'] == 1 and r['floating_voxels'] == 20 * 10 * 3
    assert r['struct_components'] == 1                          # the hut; the cloud is excluded
    assert r['roofed_pct'] > 0
    assert r['spawn_blue']['land_pct'] == 100.0 and r['spawn_red']['land_pct'] == 100.0
    assert r['plat_end_blue']['land_pct'] == 100.0 and r['solid_z_le2_over_platform'] == 0
    assert r['mirror_x_land'] < 1.0                              # the hut is not mirrored
    assert r['hue_families_90'] >= 1 and r['sea_colours'] == 1


def test_classic_table_flags_ranges(tmp_path):
    r = _island(tmp_path)
    rows = {k: ok for k, lo, hi, v, ok, sep, _ in classic_table(r)}
    assert rows['landmasses'] is True and rows['water_pct'] is True     # 83.3 % sea, one island
    r['landmasses'] = 20                                                # an archipelago is out of range
    rows = {k: ok for k, lo, hi, v, ok, sep, _ in classic_table(r)}
    assert rows['landmasses'] is False
