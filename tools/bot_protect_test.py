"""Live protection test: bots join a running piqueserver 1.4.2 as real players and build/destroy.

Scenario (map: diagnostic scene; both teams spawn on open ground near x 200, y 260, floor z 58):
  T1  blue builds block P1 on the ground                         -> expect BUILD broadcast
  T2  blue shoots AUTHORED ground                                -> expect nothing (protected)
  T3  red shoots blue's block P1                                 -> expect destroy
  T4  blue builds P2, blue shoots its own P2                     -> expect destroy (team_can_destroy_own)
  T5  blue builds P3 on the ground; red SPADES P3 (spade also hits the authored ground below)
  T6  blue builds P4, P5; red throws a 0-fuse grenade at them (authored ground inside the blast)
Then a spectator downloads the server's CURRENT map and we check the voxels themselves.
Usage: python tools/bot_protect_test.py <port> <label>
"""
import json
import sys
import time
import zlib

import enet
from pyspades import contained as loaders
from pyspades.bytes import ByteReader, ByteWriter
from pyspades.packet import load_server_packet
from pyspades.constants import (BUILD_BLOCK, DESTROY_BLOCK, SPADE_DESTROY, SPADE_TOOL, BLOCK_TOOL,
                                WEAPON_TOOL, GRENADE_TOOL)

import os  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aosmap.vxl import read_vxl  # noqa: E402


class Bot:
    def __init__(self, port, team=None, name='bot'):
        self.host = enet.Host(None, 1, 1, 0, 0)
        self.host.compress_with_range_coder()
        self.peer = self.host.connect(enet.Address(b'127.0.0.1', port), 1, 3)
        self.team, self.name = team, name
        self.pid = None
        self.chunks, self.map_bytes, self.block_actions, self.chat = [], None, [], []
        self.spawned = False

    def send(self, pkt):
        w = ByteWriter(); pkt.write(w)
        self.peer.send(0, enet.Packet(bytes(w), enet.PACKET_FLAG_RELIABLE))

    def pump(self, seconds):
        end = time.time() + seconds
        while time.time() < end:
            ev = self.host.service(20)
            if ev.type != enet.EVENT_TYPE_RECEIVE:
                continue
            data = bytes(ev.packet.data)
            pid = data[0]
            if pid == 19:
                self.chunks.append(data[1:]); continue
            try:
                p = load_server_packet(ByteReader(data))
            except Exception:                                      # noqa: BLE001
                continue
            name = type(p).__name__
            if name == 'StateData':
                self.pid = p.player_id
                self.map_bytes = zlib.decompress(b''.join(self.chunks)) if self.chunks else None
                if self.team is not None:
                    j = loaders.ExistingPlayer()
                    j.player_id = self.pid; j.team = self.team; j.weapon = 0; j.tool = BLOCK_TOOL
                    j.kills = 0; j.color = 0xB43C3C if self.team else 0x3C3CB4; j.name = self.name
                    self.send(j)
            elif name == 'CreatePlayer' and p.player_id == self.pid:
                self.spawned = True
            elif name == 'BlockAction':
                self.block_actions.append((p.player_id, p.value, p.x, p.y, p.z))
            elif name == 'ChatMessage':
                self.chat.append(p.value)

    def tool(self, t):
        s = loaders.SetTool(); s.player_id = self.pid; s.value = t; self.send(s)

    def fire(self, on):
        w = loaders.WeaponInput(); w.player_id = self.pid; w.primary = bool(on); w.secondary = False
        self.send(w)

    def shoot_block(self, x, y, z):
        """Real clients hold the trigger; pyspades only accepts weapon DESTROY_BLOCK while shooting."""
        self.fire(True); self.pump(0.15)
        self.act(DESTROY_BLOCK, x, y, z); self.pump(0.15)
        self.fire(False)

    def act(self, value, x, y, z):
        b = loaders.BlockAction(); b.player_id = self.pid; b.value = value; b.x, b.y, b.z = x, y, z
        self.send(b)

    def grenade(self, pos, fuse=0.0):
        g = loaders.GrenadePacket(); g.player_id = self.pid; g.value = fuse
        g.position = pos; g.velocity = (0.0, 0.0, 0.0); self.send(g)


def step(bots, secs=1.2):
    for _ in range(int(secs / 0.1)):
        for b in bots:
            b.pump(0.05)


def main(port, label):
    blue, red = Bot(port, 0, 'blue_bot'), Bot(port, 1, 'red_bot')
    step([blue, red], 6)
    assert blue.spawned and red.spawned, f'bots did not spawn (blue={blue.spawned}, red={red.spawned})'
    log = {}

    def since(n0):
        return [a for a in blue.block_actions[n0:]]

    def run(name, fn, wait=1.5):
        n0 = len(blue.block_actions)
        fn(); step([blue, red], wait)
        log[name] = since(n0)

    P1, P2, P3, P4, P5 = (201, 260, 57), (201, 262, 57), (199, 261, 57), (205, 259, 57), (205, 260, 57)
    G = (202, 260, 58)
    blue.tool(BLOCK_TOOL); red.tool(WEAPON_TOOL); step([blue, red], 0.6)
    run('T1_blue_builds_P1', lambda: blue.act(BUILD_BLOCK, *P1))
    blue.tool(WEAPON_TOOL); step([blue, red], 0.6)
    run('T2_blue_shoots_authored_ground', lambda: blue.shoot_block(*G))
    run('T3_red_shoots_blue_P1', lambda: red.shoot_block(*P1))
    blue.tool(BLOCK_TOOL); step([blue, red], 0.6)
    run('T4a_blue_builds_P2', lambda: blue.act(BUILD_BLOCK, *P2))
    blue.tool(WEAPON_TOOL); step([blue, red], 0.6)
    run('T4b_blue_shoots_own_P2', lambda: blue.shoot_block(*P2))
    blue.tool(BLOCK_TOOL); step([blue, red], 0.6)
    run('T5a_blue_builds_P3', lambda: blue.act(BUILD_BLOCK, *P3))
    red.tool(SPADE_TOOL); step([blue, red], 0.6)
    run('T5b_red_spades_P3', lambda: red.act(SPADE_DESTROY, *P3))
    run('T6a_blue_builds_P4_P5', lambda: (blue.act(BUILD_BLOCK, *P4), step([blue], 0.7),
                                          blue.act(BUILD_BLOCK, *P5)), wait=2.0)
    red.tool(GRENADE_TOOL); step([blue, red], 0.6)
    run('T6b_red_grenade_at_P4_P5', lambda: red.grenade((205.5, 259.9, 57.4), 0.0), wait=2.5)
    # spectator downloads the server's current map
    spec = Bot(port, None, 'spec')
    for _ in range(60):
        spec.pump(0.2)
        if spec.map_bytes:
            break
    m, rep = read_vxl(spec.map_bytes)
    state = {k: bool(m.solid[v]) for k, v in
             {'P1': P1, 'P2': P2, 'P3': P3, 'P4': P4, 'P5': P5, 'ground_G': G,
              'ground_under_P3': (199, 261, 58), 'ground_under_P4': (205, 259, 58)}.items()}
    out = {'label': label, 'actions': {k: v for k, v in log.items()}, 'final_server_map': state,
           'chat': blue.chat[-6:] + red.chat[-6:]}
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main(int(sys.argv[1]), sys.argv[2])
