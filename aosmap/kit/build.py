"""Export: .vxl + .txt + build.json (+ mat.npy / terrain_H.npy for the checks), .txt rules, determinism helpers.

Merged from every *_main.py (export, sha256, build.json with seeds, counts, tag_rect, sky_objects, interiors),
aosmap/meta.py (map_txt, check_map_txt) and ww_gen / ds_main map_txt variants.

Owner rules applied: author = 'shywolf91 + AI'; no get_spawn_location / get_entity_location hooks; fog bright
(~150+ per channel); extensions carry 'babel': True for Babel maps.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

import numpy as np

from .. import meta

AUTHOR = 'shywolf91 + AI'
TXT_KEYS = {'name', 'version', 'author', 'description', 'extensions', 'time_limit', 'cap_limit', 'fog'}


def map_txt(name, description, fog, extensions, version='1.0', header=None, author=AUTHOR):
    """.txt text with only keys piqueserver 1.4.2 reads; repr() quoting makes apostrophes safe."""
    return meta.map_txt(name=name, author=author, description=description, version=version,
                        extensions=extensions, fog=fog, header=header)


def check_txt(path, mode='babel'):
    """Load the .txt the way piqueserver does and check the owner rules. Returns {'ok': bool, 'issues': [...]}."""
    issues = []
    try:
        mod = meta.check_map_txt(path)
    except Exception as e:                      # a .txt that fails to parse is only logged by the server
        return {'ok': False, 'issues': [f'does not load: {e!r}']}
    names = {k for k in vars(mod) if not k.startswith('_')}
    for hook in ('get_spawn_location', 'get_entity_location'):
        if hook in names:
            issues.append(f'{hook} present (owner rule: no AI-authored spawn hooks)')
    extra = names - TXT_KEYS - {'get_spawn_location', 'get_entity_location', 'is_indestructable',
                                'on_block_destroy', 'random', 'math'}
    if extra:
        issues.append(f'keys piqueserver does not read: {sorted(extra)}')
    if getattr(mod, 'author', None) != AUTHOR:
        issues.append(f"author is {getattr(mod, 'author', None)!r}, rule is {AUTHOR!r}")
    fog = getattr(mod, 'fog', None)
    if fog is None:
        issues.append('no fog set')
    elif min(fog) < 120 or sum(fog) / 3 < 150:
        issues.append(f'fog {fog} darker than the ~150+ rule')
    ext = getattr(mod, 'extensions', {}) or {}
    if mode == 'babel' and not ext.get('babel'):
        issues.append("extensions lacks 'babel': True")
    if 'water_damage' in ext:
        issues.append('note: water_damage needs piqueserver.scripts.map_extensions in the server script list')
    return {'ok': not [i for i in issues if not i.startswith('note')], 'issues': issues}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def export(cv, out_dir, file_name, txt, build_info=None, save_arrays=True):
    """Write <file_name>.vxl, .txt and build.json into out_dir. txt: kwargs for map_txt().
    build_info: seeds, counts, cleanup reports, tag_rect, cosmetic_asymmetric_bbox or a list
    cosmetic_asymmetric_boxes ... (merged into build.json).
    Returns the build.json dict."""
    os.makedirs(out_dir, exist_ok=True)
    data = cv.to_vxl()
    with open(os.path.join(out_dir, file_name + '.vxl'), 'wb') as f:
        f.write(data)
    with open(os.path.join(out_dir, file_name + '.txt'), 'w', encoding='utf-8') as f:
        f.write(map_txt(**txt))
    info = {'map': txt['name'], 'file': file_name, 'sha256': sha256(data), 'bytes': len(data)}
    info.update(build_info or {})
    if cv.expect_floating:
        info['sky_objects'] = cv.expect_floating
    if cv.interiors:
        info['interiors'] = cv.interiors
    with open(os.path.join(out_dir, 'build.json'), 'w') as f:
        json.dump(info, f, indent=1, default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o))
    if save_arrays:                              # git-ignored (*.npy): needed by babel_checks for material reports
        np.save(os.path.join(out_dir, 'mat.npy'), cv.mat)
        np.save(os.path.join(out_dir, 'terrain_H.npy'), cv.H)
    return info


def glow_extensions(stored, extensions=None):
    """Add the owner's glow-block keys to an extensions dict (knowledge base §11.4)."""
    ext = dict(extensions or {})
    ext['glow_enabled'] = True
    # keys are (x, y, z) tuples, as in hallweebalohabeta and every earlier map (knowledge base §11.4)
    ext['glow_stored_colors'] = {(int(x), int(y), int(z)): tuple(int(v) for v in c)
                                 for (x, y, z), c in stored.items()}
    return ext


def determinism_check(cmd, out_flag_dir_a, out_flag_dir_b, file_name, cwd=None):
    """Run the same build command twice in fresh processes (cmd + [outdir]) and compare the .vxl SHA-256."""
    shas = []
    for d in (out_flag_dir_a, out_flag_dir_b):
        subprocess.run(list(cmd) + [d], cwd=cwd, check=True, capture_output=True)
        shas.append(sha256(open(os.path.join(d, file_name + '.vxl'), 'rb').read()))
    return {'identical': shas[0] == shas[1], 'sha256': shas}


def python_exe():
    return sys.executable
