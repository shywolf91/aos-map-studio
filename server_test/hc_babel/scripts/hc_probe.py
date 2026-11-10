"""Live probe: after the map loads, record what the server actually built, then stop the reactor.
Copy maps/the_hollow_crown_v1/*.vxl/.txt into server_test/hc_babel/maps/, then
`piqueserver -d server_test/hc_babel` -> probe.json in the working directory. Drop "hc_probe" from the
script list to keep the server running normally."""
import json
from collections import Counter
from twisted.internet import reactor


def apply_script(protocol, connection, config):
    class ProbeProtocol(protocol):
        def on_map_change(self, map):
            r = protocol.on_map_change(self, map)
            reactor.callLater(1.0, self._wkh_probe)
            return r

        def _wkh_probe(self):
            m = self.map
            info = self.map_info
            out = {'map_name': info.name, 'babel': getattr(self, 'babel', None),
                   'cap_limit': info.cap_limit, 'extensions': {k: v for k, v in info.extensions.items()},
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
                zs = Counter()
                xs = []
                for i in range(400):
                    x, y, z = info.get_spawn_location(c)
                    zs[z] += 1
                    xs.append(x)
                spawns[team.name] = {'z': dict(zs), 'x_range': [min(xs), max(xs)],
                                     'base': [team.base.x, team.base.y, team.base.z]}
            out['spawns_400'] = spawns
            out['intel'] = [[e.x, e.y, e.z] for e in (self.team_1.flag, self.team_2.flag)]
            with open('probe.json', 'w') as f:
                json.dump(out, f, indent=1)
            reactor.stop()
    return ProbeProtocol, connection
