"""Tests for aosmap.kit (fast ones; the legacy-reproduction test is tools/kit_acceptance.py)."""
import io
import os
import subprocess
import sys

import numpy as np
import pytest

from aosmap.kit import Canvas, babel_checks, build, codec, noise, sky, structures, symmetry, tag, veg

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


def flat(z=50, c=(100, 140, 80)):
    cv = Canvas('t')
    cv.fill_terrain(np.full((512, 512), z), c)
    return cv


def test_codec_roundtrip_and_pyspades_identical():
    cv = flat()
    cv.box(100, 120, 100, 120, 40, 49, (200, 50, 50))
    cv.carve(105, 115, 105, 115, 41, 48)
    data = cv.to_vxl()
    s, c, colored = codec.decode(data)
    assert (s == cv.solid).all()
    assert codec.encode(s, np.where(colored, c, 0)) == data
    from pyspades.vxl import VXLData
    assert bytes(VXLData(io.BytesIO(data)).generate()) == data


def test_noise_is_deterministic_across_processes():
    a = noise.fbm2((64, 64), 16, 3, 'x', 7)
    code = ('import sys; sys.path.insert(0, r"%s"); from aosmap.kit import noise; '
            'print(noise.fbm2((64, 64), 16, 3, "x", 7).sum().hex())' % ROOT)
    out = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, check=True).stdout.strip()
    assert out == a.sum().hex()


def test_mirror_canvas_is_symmetric_and_fills_axis_column():
    cv = flat()
    cv.box(40, 60, 30, 50, 30, 49, (10, 20, 30))
    symmetry.mirror_canvas(cv, 'x512')
    assert symmetry.mirror_mismatch(cv.solid, cv.mat, 'x512')['solid'] == 0
    assert (cv.solid[256] == cv.solid[255]).all()
    cv2 = flat()
    cv2.box(40, 60, 30, 50, 30, 49, (10, 20, 30))
    symmetry.mirror_canvas(cv2, 'x511')
    assert symmetry.mirror_mismatch(cv2.solid, None, 'x511')['solid'] == 0


def test_orphans_removed_and_expected_kept():
    cv = flat()
    cv.box(300, 302, 300, 302, 10, 12, (1, 1, 1))           # stray fragment
    cv.box(20, 40, 20, 30, 5, 8, (2, 2, 2))                 # intentional piece
    cv.expect('cloud', 20, 40, 20, 30, 5, 8)
    rep = symmetry.remove_orphans(cv)
    assert rep['removed_components'] == 1 and len(rep['kept_floating']) == 1
    assert not cv.solid[300:303, 300:303, 10:13].any() and cv.solid[20:41, 20:31, 5:9].all()


def test_vegetation_is_face_connected_with_three_details():
    cv = flat()
    rng = np.random.default_rng(3)
    pal = veg.palette_family([(60, 110, 50), (120, 140, 66)], n=6)
    infos = [veg.broadleaf(cv, rng, 100 + 30 * i, 100, 50, pal) for i in range(4)]
    infos += [veg.conifer(cv, rng, 100 + 30 * i, 160, 50, pal) for i in range(4)]
    assert all(len(set(i['details'])) == 3 for i in infos)
    assert symmetry.floating_components(cv.solid) == []


def test_building_interiors_are_reachable():
    cv = flat()
    structures.building(cv, 60, 75, 200, 215, 50, storeys=3, doors=('E',), name='house')
    R = babel_checks.run_all(cv.to_vxl(), build={'interiors': cv.interiors}, pyspades=False)
    assert R['interiors']['checked'] == 3 and R['interiors']['failures'] == []
    assert R['floating_components']['count'] == 0


def test_tag_in_corner_and_txt_rules(tmp_path):
    cv = flat()
    x0, x1, y0, y1, z = tag.paint_tag(cv, 'Kit Test', corner='SW')
    assert x0 < 20 and y1 > 490 and z == 50
    good = tmp_path / 'good.txt'
    good.write_text(build.map_txt('Kit Test', "Babel: it's a test", (170, 168, 190), {'babel': True}))
    assert build.check_txt(good)['ok']
    bad = tmp_path / 'bad.txt'
    bad.write_text("name = 'x'\nauthor = 'me'\nfog = (20, 20, 20)\nextensions = {}\n"
                   "def get_spawn_location(c):\n    return None\n")
    issues = ' '.join(build.check_txt(bad)['issues'])
    assert 'get_spawn_location' in issues and 'author' in issues and 'fog' in issues and 'babel' in issues


def test_sky_placement_rules():
    cv = flat()
    rec = sky.place(cv, 'moon', sky.moon, 400, 60, 16)
    assert rec['voxels'] > 50
    assert sky.rule_check([(o, 256, 20) for o in range(250, 260)])['ok'] is False      # over the platform
    with pytest.raises(RuntimeError):
        sky.place(cv, 'bird', sky.bird, 118, 256, 10, 0.0)                         # over a spawn square


def test_exposure_presets_agree_on_open_flat_map():
    cv = flat()
    e = babel_checks.spawn_exposure(cv.solid, (118, 256))
    assert e['hidden_pct'] == 0.0 and e['n_spots'] == 441 and e['n_viewers'] == 65


def test_mirror_excludes_accept_a_list_of_cosmetic_boxes():
    cv = flat()
    cv.box(40, 60, 30, 50, 30, 49, (10, 20, 30))
    symmetry.mirror_canvas(cv, 'x512')
    cv.box(250, 270, 80, 86, 44, 49, (9, 9, 9))          # train across the axis (after the mirror)
    cv.box(470, 490, 20, 26, 46, 49, (9, 9, 9))          # tag in a corner
    legacy = babel_checks.cosmetic_excludes({'cosmetic_asymmetric_bbox': [250, 270, 80, 86]})
    both = babel_checks.cosmetic_excludes({'cosmetic_asymmetric_bbox': [250, 270, 80, 86],
                                           'cosmetic_asymmetric_boxes': [[250, 270, 80, 86], [470, 490, 20, 26]]})
    assert legacy == [(250, 270, 80, 86)] and len(both) == 2
    assert symmetry.mirror_mismatch(cv.solid, None, 'x512', legacy)['solid'] > 0
    assert symmetry.mirror_mismatch(cv.solid, None, 'x512', both)['solid'] == 0


def test_glow_extension_keys_are_xyz_tuples(tmp_path):
    ext = build.glow_extensions({(5, 6, 7): (10, 20, 30)}, {'babel': True})
    assert ext['glow_enabled'] is True and ext['glow_stored_colors'] == {(5, 6, 7): (10, 20, 30)}
    f = tmp_path / 'g.txt'
    f.write_text(build.map_txt('G', 'Babel: glow', (170, 168, 190), ext))
    ns = {}
    exec(f.read_text(), ns)
    assert ns['extensions']['glow_stored_colors'] == {(5, 6, 7): (10, 20, 30)}


# ------------------------------------------------------------------------------------------- zones (zone profile)

@pytest.fixture(scope='module')
def walled_blue():
    """Flat z 50 map. Blue spawn walled in (6 high, 5 outside the square) with one 3-wide gate on the enemy side;
    red spawn open. Not mirrored on purpose (each team is measured separately)."""
    from aosmap.kit import zones
    cv = flat()
    x0, x1, y0, y1 = 98 - 5, 138 + 5, 236 - 5, 276 + 5
    for (a, b, c, d) in ((x0, x1, y0, y0), (x0, x1, y1, y1), (x0, x0, y0, y1), (x1, x1, y0, y1)):
        cv.box(a, b, c, d, 44, 49, (90, 90, 90))
    cv.carve(x1, x1, 255, 257, 44, 49)
    data = cv.to_vxl()
    solid, topc = zones.decode_solid_fast(data)
    return cv, data, solid, zones.zone_profile(solid)


def test_zones_fast_decoder_matches_strict_reader(walled_blue):
    cv, data, solid, _ = walled_blue
    s2, c2, _ = codec.decode(data)
    assert (solid == s2).all() and (solid == cv.solid | (np.arange(64) == 63)).all()


def test_zones_spawn_exits_and_enclosure(walled_blue):
    zp = walled_blue[3]
    b, r = zp['teams']['blue']['spawn'], zp['teams']['red']['spawn']
    assert b['exit_min_cut'] == 3 and b['sealable'] is True
    assert r['exit_min_cut'] > 100 and r['sealable'] is False
    assert b['floor_z'] == 50 and b['near_mode_share'] == 1.0 and b['roof_cols'] == 0 and b['water_cols'] == 0
    assert b['enclosure']['r0_8_enemy_cover3'] > 0 and r['enclosure']['r0_8_enemy_cover3'] == 0
    assert b['platform_viewers_mean'] < r['platform_viewers_mean']


def test_zones_front_centre_and_map_on_flat_ground(walled_blue):
    zp = walled_blue[3]
    f = zp['teams']['red']['front']
    assert f['build_gap_blocks'] == 50 - 2 and not f['platform_reachable_on_foot']
    assert f['object_share'] == 0 and f['flat_share'] == 1.0 and f['water_share'] == 0
    assert zp['centre']['strip']['min_gap_to_platform'] == 48
    assert zp['routes']['flank_exists'] and zp['routes']['map_crossing_width'] > 400
    assert zp['map']['land_share'] == 1.0
    from aosmap.kit import zones
    c = zones.classify(zp)
    assert c == {'class': 'ground', 'assist': False, 'stock_fit': True}


def test_zones_rays_and_symmetry():
    from aosmap.kit import zones
    cv = flat()
    cv.box(110, 110, 0, 511, 40, 49, (1, 1, 1))                     # wall 10 east of x 100
    op = zones._opaque(cv.solid, babel_checks.BABEL_DEFAULT)
    L = zones.free_rays(op, [(100.5, 100.5, 47.6)], dirs=4)
    assert 9 <= L[0, 0] <= 10 and 99.5 <= L[0, 2] <= 101              # east blocked; west runs to the map edge
    assert zones.symmetry_type(cv.solid)['type'] not in ('x512', 'x511')
    cv2 = flat()
    cv2.box(100, 140, 40, 60, 40, 49, (1, 1, 1))
    cv2.box(100, 140, 451, 471, 40, 49, (1, 1, 1))               # y' = 511 - y mirror only
    assert zones.symmetry_type(cv2.solid)['best'] == 'y511'
    vis = zones.los_any(op, [(100.5, 100.5, 47.6)], [(120.5, 100.5, 47.8), (90.5, 100.5, 47.8)])
    assert vis.tolist() == [0, 1]


def test_zones_roof_versus_deck_columns():
    from aosmap.kit import zones
    cv = flat()
    cv.box(10, 19, 10, 19, 44, 44, (5, 5, 5))           # roof 5 above dry ground: room under it
    cv.box(30, 39, 10, 19, 49, 49, (5, 5, 5))           # 1-voxel slab lying on the ground: no gap
    cv.carve(50, 59, 10, 19, 20, 62)                     # pit to the sea floor ...
    cv.box(50, 59, 10, 19, 20, 20, (5, 5, 5))           # ... bridged by a deck 42 above it
    F = zones.fields(cv.solid)
    assert F['roof'][10:20, 10:20].all() and not F['deck'][10:20, 10:20].any()
    assert not F['roof'][30:40, 10:20].any() and not F['deck'][30:40, 10:20].any()
    assert F['deck'][50:60, 10:20].all() and not F['roof'][50:60, 10:20].any()


# ------------------------------------------------------------------------------------- zone rules (adopted 2026-11-13)

def _zr(cv, **kw):
    from aosmap.kit import zones
    return zones.zone_rules(cv.solid, **kw)


def _mirrored(cv):
    symmetry.mirror_canvas(cv, 'x512')
    return cv


def _props(cv, z0=46, first_z0=None, xs=range(145, 195, 10)):
    for i, x in enumerate(xs):
        y = 240 + 12 * (i % 3)
        cv.box(x, x + 5, y, y + 5, first_z0 if (i == 0 and first_z0) else z0, 49, (120, 90, 60))
    return cv


def test_zone_rule_front_dressing_pass_and_fail():
    r = _zr(_mirrored(_props(flat())))['front_dressing']               # 5 low props, 6 x 6, 4 tall
    assert r['status'] == 'pass', r['why']
    assert r['values']['blue']['objects'] == 5 and r['values']['red']['objects'] == 5
    assert 0.05 <= r['avg']['object_share'] <= 0.30 and r['avg']['low_share'] == 1.0
    r = _zr(_mirrored(_props(flat(), first_z0=30)))['front_dressing']   # one prop 20 tall
    assert r['status'] == 'fail' and 'share of objects <= 10 tall 0.8 < 0.9 (short by 0.1)' in r['why']
    bare = _zr(_mirrored(flat()))['front_dressing']
    assert bare['status'] == 'fail' and 'blue objects 0 < 4 (short by 4)' in bare['why']


def test_zone_rule_front_gate_exemption_and_free_share():
    def gate_map(arch):
        cv = _props(flat(), xs=range(160, 200, 10))                    # 4 low props
        cv.box(148, 153, 230, 282, 34, 49, (90, 90, 90))               # gate wall, 16 tall, across the band
        cv.carve(148, 153, 256 - arch, 256 + arch, 46, 49)             # walk-through arch
        return _mirrored(cv)
    box = [[148, 153, 230, 282], [359, 364, 230, 282]]
    wide = gate_map(16)
    assert _zr(wide)['front_dressing']['status'] == 'fail'           # the gate counts: a 16-tall object
    r = _zr(wide, front_exempt_boxes=box)
    assert r['front_dressing']['status'] == 'pass', r['front_dressing']['why']
    ex = r['front_exempt']
    assert len(ex) == 2 and ex[0]['height_max'] >= 14 and 0.5 < ex[0]['open_share'] < 1
    narrow = _zr(gate_map(1), front_exempt_boxes=box)['front_dressing']   # 3-wide arch still blocks the front
    assert narrow['status'] == 'fail' and 'free share of the 8-col section' in narrow['why']


def test_zone_rule_spawn_cover_pass_and_fail():
    cv = flat()
    cv.box(139, 158, 236, 276, 47, 49, (80, 120, 60))                 # enemy-side cover, 3 tall, within 20
    cv.box(58, 77, 190, 322, 44, 49, (60, 90, 50))                    # rear backdrop 20-40 behind
    r = _zr(_mirrored(cv))['spawn_cover']
    assert r['status'] == 'pass', r['why']
    v = r['values']['blue']
    assert v['enemy_0_20'] >= 0.25 and v['rear_20_40'] >= 0.30 and v['enemy_0_8'] >= 0.8
    r = _zr(_mirrored(flat()))['spawn_cover']
    assert r['status'] == 'fail' and 'blue enemy-side cover within 20 0 < 0.25 (short by 0.25)' in r['why']
    assert 'rear backdrop 20-40 0 < 0.3' in r['why']


def test_zone_rule_under_platform_and_centre():
    cv = flat()
    for x in (214, 230, 246):                                         # low props in the strip (mirrored)
        cv.box(x, x + 5, 242, 269, 47, 49, (110, 100, 90))
    for x in range(160, 250, 20):                                     # room-sized pieces in the central zone
        for y in (150, 340):
            cv.box(x, x + 7, y, y + 7, 44, 49, (120, 110, 100))
    r = _zr(_mirrored(cv))
    up, ce = r['under_platform'], r['centre_footprint']
    assert up['status'] == 'pass', up['why']
    assert 0.15 <= up['values']['object_share'] <= 0.45 and up['values']['min_air_all'] == 45
    assert ce['status'] == 'pass' and ce['values']['footprint_p50'] >= 25
    cv.box(250, 255, 250, 255, 12, 49, (1, 1, 1))                     # a pillar: 10 air below the platform
    cv.box(205, 207, 250, 252, 44, 49, (1, 1, 1))                     # a prop on the blue anchor end
    r = _zr(cv)['under_platform']
    assert r['status'] == 'fail'
    assert 'min air between strip tops and the platform 10 < 25 (short by 15)' in r['why']
    assert 'blue anchor top-z range 6 > 1 (over by 5)' in r['why'] and 'blue anchor prop columns' in r['why']
    small = flat()
    for x in range(160, 250, 10):
        small.box(x, x + 2, 200, 202, 46, 49, (1, 1, 1))              # 3 x 3 props only
    ce = _zr(_mirrored(small))['centre_footprint']
    assert ce['status'] == 'fail' and 'median object footprint 9 cells < 25 (short by 16)' in ce['why']


def test_zone_rules_relief_not_objects_and_terrain_H():
    from aosmap.kit import zones
    cv = Canvas('t')
    H = np.full((512, 512), 50)
    for i in range(6):                                                # gentle ridge, 1-voxel steps, 12 wide
        H[150:200, 250 - 6 + i] = 50 - (i + 1) // 2
        H[150:200, 262 - i] = 50 - (i + 1) // 2
    H[150:200, 250:257] = 47                                          # 3 high, 19 wide, 1-voxel steps
    cv.fill_terrain(H, (100, 140, 80))
    obj, _, _, method = zones.object_field(cv.solid, zones.fields(cv.solid))
    assert method == 'estimated' and not obj[150:200, 240:266].any()
    cv.box(170, 175, 300, 305, 44, 49, (1, 1, 1))
    obj2, oh, _, m2 = zones.object_field(cv.solid, zones.fields(cv.solid), terrain_H=cv.H)
    assert m2 == 'terrain_H' and obj2[170:176, 300:306].all() and int(oh.max()) == 6 and obj2.sum() == 36


def test_zone_rules_not_applicable_skip_and_summary_rows():
    H = np.full((512, 512), 50)
    H[:, 236:277] = 63                                                # the whole y band is sea: fronts, strip, ends
    H[150:363, 130:383] = 63                                          # and the central zone
    cv = Canvas('w')
    cv.fill_terrain(H, (90, 120, 160))
    r = _zr(cv, skip={'spawn_cover': 'owner: custom spawns on this server'})
    assert r['front_dressing']['status'] == 'n.a.' and 'not land' in r['front_dressing']['why']
    assert r['under_platform']['status'] == 'n.a.' and r['centre_footprint']['status'] == 'n.a.'
    assert r['spawn_cover']['status'] == 'skipped' and 'custom spawns' in r['spawn_cover']['why']
    R = babel_checks.run_all(flat().to_vxl(), pyspades=False, zone_profile=False,
                             build={'front_exempt_boxes': [[150, 155, 230, 282]]})
    rows = [row for row in babel_checks.summary(R) if row.get('status')]
    assert len(rows) == 4 and R['zone_rules']['front_exempt_boxes'] == [[150, 155, 230, 282]]
    fr = [row for row in rows if row['rule'].startswith('zone: front')][0]
    assert fr['status'] == 'fail' and not fr['ok'] and 'objects 0 < 4' in babel_checks.format_row(fr)
