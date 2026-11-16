"""Logs what the server sees for the loaded map after babel_script set it up, then stops the reactor."""
import random
from twisted.internet import reactor


def apply_script(protocol, connection, config):
    class ProbeProtocol(protocol):
        def on_map_change(self, map):
            r = protocol.on_map_change(self, map)
            m = self.map
            plat = sum(1 for x in range(206, 306) for y in range(240, 272) if m.get_solid(x, y, 1))
            info = self.map_info
            print('PROBE map name:', info.name, '| author:', getattr(info, 'author', None))
            print('PROBE extensions:', info.extensions, '| fog:', self.fog_color)
            print('PROBE babel enabled:', getattr(self, 'babel', None), '| cap_limit:', info.cap_limit)
            print('PROBE platform solid cells at z1 (x206-305,y240-271):', plat)
            print('PROBE get_z at bases:', m.get_z(118, 256), m.get_z(394, 256))
            print('PROBE get_z under platform ends (209,256)/(303,256):', m.get_z(209, 256), m.get_z(303, 256))
            print('PROBE get_z under platform ends below z2 (209,256)/(303,256):', m.get_z(209, 256, 3), m.get_z(303, 256, 3))
            reactor.callLater(1, self.ww_later)
            reactor.callLater(3, reactor.stop)
            return r

        def ww_later(self):
            info = self.map_info
            class FakeTeam:
                pass
            class FakeConn:
                pass
            for team in (self.blue_team, self.green_team):
                c = FakeConn(); c.team = team; c.protocol = self
                random.seed(1)
                zs = set()
                for _ in range(400):
                    x, y, z = info.get_spawn_location(c)
                    zs.add(z)
                print('PROBE', team.name, 'base', (team.base.x, team.base.y, team.base.z), '400 spawn z values:', sorted(zs))
            print('PROBE intel', (self.blue_team.flag.x, self.blue_team.flag.y, self.blue_team.flag.z) if self.blue_team.flag else None,
                  (self.green_team.flag.x, self.green_team.flag.y, self.green_team.flag.z) if self.green_team.flag else None)

    return ProbeProtocol, connection
