"""Live server probe: load a map on a real piqueserver 1.4.2 in a throw-away config dir and record what the server
actually built (map name, extensions, fog, Babel platform cells, intel / base positions, 400 sampled spawns per team).

Merged from server_test/*/scripts/{hc,gf,sph}_probe.py, tools/ww_probe.py and aosmap.pipeline's runtime checks.

    python -m aosmap.kit.probe maps/<map>_v1 [--mode babel|ctf|push|arena] [--keep DIR] [--timeout 90]

Status ladder: a passing probe is "server-loaded". It is not client inspection.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

MODES = {'babel': 'piqueserver.game_modes.babel', 'ctf': 'ctf', 'tc': 'tc',
         'push': 'piqueserver.game_modes.push', 'arena': 'piqueserver.game_modes.arena'}

# owner's normal script list (knowledge base §13.4) minus scripts that need extra setup
SCRIPTS = ['piqueserver.scripts.rollback', 'piqueserver.scripts.protect', 'piqueserver.scripts.map_extensions',
           'piqueserver.scripts.votekick', 'piqueserver.scripts.trusted', 'piqueserver.scripts.ratio',
           'piqueserver.scripts.blockinfo', 'piqueserver.scripts.squad', 'piqueserver.scripts.afk']

PROBE_SCRIPT = r'''"""aosmap.kit probe script: record what the server built after the map loads, then stop."""
import json
from collections import Counter
from twisted.internet import reactor


def apply_script(protocol, connection, config):
    class KitProbeProtocol(protocol):
        def on_map_change(self, map):
            r = protocol.on_map_change(self, map)
            reactor.callLater(1.0, self._kit_probe)
            return r

        def _kit_probe(self):
            out = {}
            try:
                m, info = self.map, self.map_info
                out = {'map_name': info.name, 'author': getattr(info, 'author', None),
                       'babel': getattr(self, 'babel', None), 'cap_limit': getattr(info, 'cap_limit', None),
                       'extensions': {k: (v if isinstance(v, (int, float, str, bool, list, tuple)) else str(v))
                                      for k, v in info.extensions.items() if k != 'glow_stored_colors'},
                       'fog': list(self.fog_color) if hasattr(self, 'fog_color') else None}
                plat = 0
                for x in range(206, 306):
                    for y in range(240, 272):
                        if m.get_solid(x, y, 1):
                            plat += 1
                out['platform_cells_z1'] = plat
                out['get_z_bases'] = [m.get_z(118, 256), m.get_z(394, 256)]

                class Stub:
                    pass
                spawns = {}
                for team in (self.team_1, self.team_2):
                    c = Stub(); c.team = team; c.protocol = self
                    zs, xs, ys = Counter(), [], []
                    for i in range(400):
                        x, y, z = info.get_spawn_location(c)
                        zs[int(z)] += 1; xs.append(x); ys.append(y)
                    spawns[team.name] = {'z': dict(zs), 'x_range': [min(xs), max(xs)], 'y_range': [min(ys), max(ys)],
                                         'base': [team.base.x, team.base.y, team.base.z]}
                out['spawns_400'] = spawns
                out['intel'] = [[e.x, e.y, e.z] for e in (self.team_1.flag, self.team_2.flag)]
            except Exception as e:
                out['probe_error'] = repr(e)
            with open('probe.json', 'w') as f:
                json.dump(out, f, indent=1, default=str)
            reactor.stop()
    return KitProbeProtocol, connection
'''

CONFIG = '''name = "aosmap kit probe"
port = {port}
game_mode = "{mode}"
rotation = ["{rot}"]
scripts = {scripts}
[team1]
name = "Blue"
color = [0, 0, 255]
[team2]
name = "Red"
color = [255, 0, 0]
[ssh]
enabled = false
[status_server]
enabled = false
[ban_publish]
enabled = false
'''


def probe(map_dir, mode='babel', timeout=120, keep=None, port=32999, extra_scripts=()):
    vx = sorted(glob.glob(os.path.join(map_dir, '*.vxl')))
    if len(vx) != 1:
        raise SystemExit(f'expected one .vxl in {map_dir}')
    rot = os.path.splitext(os.path.basename(vx[0]))[0]
    tmp = keep or tempfile.mkdtemp(prefix='aoskit_probe_')
    os.makedirs(os.path.join(tmp, 'maps'), exist_ok=True)
    os.makedirs(os.path.join(tmp, 'scripts'), exist_ok=True)
    shutil.copy(vx[0], os.path.join(tmp, 'maps'))
    txt = vx[0][:-4] + '.txt'
    if os.path.exists(txt):
        shutil.copy(txt, os.path.join(tmp, 'maps'))
    with open(os.path.join(tmp, 'scripts', 'aoskit_probe.py'), 'w') as f:
        f.write(PROBE_SCRIPT)
    scripts = SCRIPTS + list(extra_scripts) + (['piqueserver.scripts.babel_script'] if mode == 'babel' else []) + \
        ['aoskit_probe']
    with open(os.path.join(tmp, 'config.toml'), 'w') as f:
        f.write(CONFIG.format(port=port, mode=MODES.get(mode, mode), rot=rot, scripts=json.dumps(scripts)))
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, '-m', 'piqueserver', '-d', tmp], cwd=tmp, capture_output=True,
                           text=True, timeout=timeout)
        log = (p.stdout or '') + (p.stderr or '')
    except subprocess.TimeoutExpired as e:
        log = (e.stdout or b'').decode(errors='replace') if isinstance(e.stdout, bytes) else (e.stdout or '')
        log += '\n[timeout]'
    res = {'map_dir': map_dir, 'mode': mode, 'seconds': round(time.time() - t0, 1), 'config_dir': tmp}
    pj = os.path.join(tmp, 'probe.json')
    if os.path.exists(pj):
        res['probe'] = json.load(open(pj))
    res['log_tail'] = log.strip().splitlines()[-15:]
    pr = res.get('probe', {})
    checks = {'loaded': bool(pr) and 'probe_error' not in pr}
    if mode == 'babel' and pr:
        checks['platform_3200_cells'] = pr.get('platform_cells_z1') == 3200
        checks['babel_extension'] = bool(pr.get('extensions', {}).get('babel'))
        checks['txt_loaded'] = pr.get('map_name') not in (None, rot)
    res['checks'] = checks
    res['ok'] = all(checks.values())
    if keep is None:
        shutil.rmtree(tmp, ignore_errors=True)
        res['config_dir'] = None
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description='Load a map on piqueserver 1.4.2 and probe it')
    ap.add_argument('mapdir')
    ap.add_argument('--mode', default='babel')
    ap.add_argument('--timeout', type=int, default=120)
    ap.add_argument('--keep', help='keep the config dir here')
    ap.add_argument('--port', type=int, default=32999)
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    r = probe(a.mapdir, a.mode, a.timeout, a.keep, a.port)
    if a.out:
        json.dump(r, open(a.out, 'w'), indent=1)
    print(json.dumps({k: v for k, v in r.items() if k != 'log_tail'}, indent=1, default=str))
    if not r['ok']:
        print('\n'.join(r['log_tail']))
    return r


if __name__ == '__main__':
    main()
