"""tools/recreate_analysis.py on one of our own maps (--fast), plus the never-execute-the-.txt guarantee."""
import hashlib
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import recreate_analysis as ra  # noqa: E402

VXL = os.path.join(ROOT, 'maps', 'yulehaven_isles_v1', 'yulehaven_isles.vxl')


def _evil_txt(tmp, marker):
    """A metadata .txt whose top-level code (and spawn hook) would create `marker` if it were ever executed."""
    p = tmp / 'evil.txt'
    p.write_text(
        'import os\n'
        f'open({str(marker)!r}, "w").write("executed")\n'
        "name = 'Evil Map'\n"
        "author = 'someone else'\n"
        "version = '0.9'\n"
        "fog = (120, 120, 120)\n"
        "extensions = {'babel': True, 'water_damage': 0, 'boom': os.getcwd()}\n"
        'def get_spawn_location(connection):\n'
        f'    open({str(marker)!r}, "w").write("hook")\n'
        '    return (0, 0, 0)\n', encoding='utf-8')
    return p


@pytest.fixture(scope='module')
def runs(tmp_path_factory):
    if not os.path.exists(VXL):
        pytest.skip('yulehaven_isles_v1 not in the checkout')
    tmp = tmp_path_factory.mktemp('recreate')
    marker = tmp / 'EXECUTED'
    txt = _evil_txt(tmp, marker)
    a = ra.analyse(VXL, str(txt), fast=True)
    b = ra.analyse(VXL, str(txt), fast=True)
    return a, b, marker, tmp


def test_main_keys_and_identity(runs):
    a, _, _, _ = runs
    for k in ('identity', 'txt', 'dna', 'babel', 'exposure', 'zones', 'art', 'island', 'ledger', 'orientation',
              'problems', 'babel_checks'):
        assert k in a, k
        assert not (isinstance(a[k], dict) and 'error' in a[k]), (k, a[k])
    I = a['identity']
    assert I['sha256'] == hashlib.sha256(open(VXL, 'rb').read()).hexdigest()
    assert I['bytes'] == os.path.getsize(VXL)
    assert I['reader_ok'] and I['z63_solid_every_column'] and I['reencode']['reencode_identical']
    assert I['canonical_encoding'] is None            # pyspades skipped with --fast


def test_numbers_are_sane(runs):
    a, _, _, _ = runs
    B = a['babel']
    assert B['platform_volume_clear'] and B['platform_volume_z0_2_voxels'] == 0
    assert B['anchors_equal']
    assert not B['platform_reachable_on_foot']
    for t in ('blue', 'red'):
        assert B['build_gap'][t]['blocks_to_platform_level'] == 42          # validation.json: 42 / 42
        assert B['spawn_squares'][t]['water_cols'] == 0 and B['spawn_squares'][t]['over_air_cols'] == 0
        e = a['exposure']['teams'][t]
        assert 0 < e['viewers_per_spot_mean'] <= 65 and 0 <= e['hidden_pct'] <= 100
    D = a['dna']
    assert D['spawn_to_spawn_steps'] == {'blue': 280.0, 'red': 280.0}
    assert D['floating']['count'] == 12                                     # the 12 declared sky pieces
    assert 50 < D['water']['engine_water_cols_pct'] < 80
    assert D['mirror_topz_match_pct']['x512'] > 90
    assert set(a['zones']['status']) == {'front_dressing', 'spawn_cover', 'under_platform', 'centre_footprint'}
    assert a['art']['pure_team_hue_top_pct'] == {'red': 0.0, 'blue': 0.0}
    assert a['ledger']['objects'] and a['ledger']['objects'][0]['footprint_cells'] >= 4


def test_txt_is_parsed_not_executed(runs):
    a, _, marker, _ = runs
    assert not marker.exists(), 'the .txt was executed'
    T = a['txt']
    assert T['supplied'] and T['name'] == 'Evil Map' and T['version'] == '0.9'
    assert T['spawn_hooks'] == ['get_spawn_location']
    assert T['fog'] == [120, 120, 120]
    keys = {p['key'] for p in a['problems']}
    assert {'spawn_hooks', 'fog_dark'} <= keys


def test_deterministic(runs):
    a, b, _, _ = runs
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_report_renders(runs):
    a, _, _, tmp = runs
    out = tmp / 'report'
    ra.write_report(dict(a), str(out), render=False)
    md = (out / 'analysis.md').read_text(encoding='utf-8')
    for h in ('## 1. Identity', '## 2. Map DNA', '## 3. Babel fitness', '## 4. Spawn exposure', '## 5. Zone targets',
              '## 6. Art stats', '## 7. Island style', '## 8. Problems found', '## 9. Element ledger',
              '## 10. Orientation'):
        assert h in md, h
    assert 'never executed' in md
    assert json.load(open(out / 'analysis.json'))['identity']['sha256'] == a['identity']['sha256']


def test_refuses_to_write_beside_input(runs):
    a, _, _, _ = runs
    with pytest.raises(SystemExit):
        ra.write_report(dict(a), os.path.dirname(VXL), render=False)


def test_unsupported_mode():
    with pytest.raises(SystemExit):
        ra.main([VXL, '--mode', 'ctf', '--no-render'])
