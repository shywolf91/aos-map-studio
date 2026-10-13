"""Live Babel check: spectator + one bot per team on a running piqueserver 1.4.2 babel server.

Reports: fog colour, intel and base positions (StateData / CTFState), whether the script platform is
present in the map the client receives, and where each team's player actually spawns.
Usage: python tools/babel_live_check.py <port>
"""
import json
import sys
import time

import os  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.bot_protect_test import Bot          # noqa: E402
from aosmap.vxl import read_vxl                 # noqa: E402


class StateBot(Bot):
    state = None
    spawn = None

    def pump(self, seconds):
        import enet
        from pyspades.bytes import ByteReader
        from pyspades.packet import load_server_packet
        end = time.time() + seconds
        while time.time() < end:
            ev = self.host.service(20)
            if ev.type != enet.EVENT_TYPE_RECEIVE:
                continue
            data = bytes(ev.packet.data)
            if data[0] == 19:
                self.chunks.append(data[1:]); continue
            try:
                p = load_server_packet(ByteReader(data))
            except Exception:                                 # noqa: BLE001
                continue
            n = type(p).__name__
            if n == 'StateData':
                import zlib
                from pyspades import contained as loaders
                self.pid = p.player_id
                self.map_bytes = zlib.decompress(b''.join(self.chunks))
                st = p.state
                self.state = {'fog': p.fog_color, 'team1': p.team1_name, 'team2': p.team2_name,
                              'team1_flag': (st.team1_flag_x, st.team1_flag_y, st.team1_flag_z),
                              'team2_flag': (st.team2_flag_x, st.team2_flag_y, st.team2_flag_z),
                              'team1_base': (st.team1_base_x, st.team1_base_y, st.team1_base_z),
                              'team2_base': (st.team2_base_x, st.team2_base_y, st.team2_base_z),
                              'cap_limit': st.cap_limit}
                if self.team is not None:
                    j = loaders.ExistingPlayer()
                    j.player_id = self.pid; j.team = self.team; j.weapon = 0; j.tool = 2
                    j.kills = 0; j.color = 0x808080; j.name = self.name
                    self.send(j)
            elif n == 'CreatePlayer' and p.player_id == self.pid:
                self.spawn = (round(p.x, 2), round(p.y, 2), round(p.z, 2))


def main(port):
    spec = StateBot(port, None, 'spec')
    for _ in range(80):
        spec.pump(0.2)
        if spec.state:
            break
    m, rep = read_vxl(spec.map_bytes)
    plat = m.solid[206:306, 240:272, 1]
    out = {'state': spec.state, 'map_reader_ok': rep.ok,
           'platform_cells_present': int(plat.sum()), 'platform_cells_expected': 100 * 32}
    bots = [StateBot(port, 0, 'blue_bot'), StateBot(port, 1, 'red_bot')]
    for _ in range(60):
        for b in bots:
            b.pump(0.1)
        if all(b.spawn for b in bots):
            break
    out['spawn_blue'] = bots[0].spawn
    out['spawn_red'] = bots[1].spawn
    print(json.dumps(out, indent=1, default=str))


if __name__ == '__main__':
    main(int(sys.argv[1]))
