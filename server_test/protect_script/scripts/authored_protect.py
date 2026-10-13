"""
authored_protect - piqueserver 1.4.2 script implementing the project's protection policy.

* Authored (original map) blocks cannot be destroyed by players.
* Player-built blocks are tracked with the team that built them; the OPPOSING team can always
  destroy them; the builder's own team can too unless team_can_destroy_own = false.
* Spade and grenade actions near authored blocks are not cancelled wholesale (the stock
  user_blocks_only behaviour); instead only the permitted player blocks are removed, sent to
  clients as individual DESTROY_BLOCK actions so client maps stay in sync.
* Blocks the server or scripts place with set_point (arena gates, babel platform) are authored.
* Collapse is unchanged: pyspades check_node still removes anything that loses its path to
  z >= 62 when a block is destroyed - keep authored geometry grounded (see project docs).

Install: copy to <config dir>/scripts/authored_protect.py and add "authored_protect" to
`scripts` in config.toml (after mode scripts such as babel_script). Options:

    [authored_protect]
    team_can_destroy_own = true

Per map, `extensions = {'authored_protect': False}` in the map .txt disables it (read by this
script only). Admins / god mode bypass it.

Verified against piqueserver 1.4.2 source: FeatureConnection.on_block_destroy/on_block_build/
on_line_build/on_block_removed, pyspades player.py block and grenade handlers.
"""
from piqueserver.config import config
from pyspades import contained as loaders
from pyspades.constants import DESTROY_BLOCK, SPADE_DESTROY, GRENADE_DESTROY

SECTION = config.section('authored_protect')
TEAM_CAN_DESTROY_OWN = SECTION.option('team_can_destroy_own', default=True, cast=bool)


def apply_script(protocol, connection, config_dict):

    class AuthoredProtectProtocol(protocol):
        player_blocks = None          # (x, y, z) -> team id of the builder
        authored_protect = True

        def on_map_change(self, map_):
            self.player_blocks = {}
            ext = self.map_info.extensions if self.map_info else {}
            self.authored_protect = bool(ext.get('authored_protect', True))
            return protocol.on_map_change(self, map_)

    class AuthoredProtectConnection(connection):

        def _record(self, points):
            pb = self.protocol.player_blocks
            if pb is None or self.team is None:
                return
            for p in points:
                pb[(int(p[0]), int(p[1]), int(p[2]))] = self.team.id

        def on_block_build(self, x, y, z):
            self._record(((x, y, z),))
            return connection.on_block_build(self, x, y, z)

        def on_line_build(self, points):
            self._record(points)
            return connection.on_line_build(self, points)

        def on_block_removed(self, x, y, z):
            if self.protocol.player_blocks is not None:
                self.protocol.player_blocks.pop((x, y, z), None)
            return connection.on_block_removed(self, x, y, z)

        # ---- policy
        def _allowed(self, xyz):
            """True if this player may remove the solid block at xyz."""
            owner = self.protocol.player_blocks.get(xyz)
            if owner is None:
                return False                                   # authored
            if owner == self.team.id and not TEAM_CAN_DESTROY_OWN.get():
                return False
            return True

        def _affected(self, x, y, z, mode):
            if mode == SPADE_DESTROY:
                cand = ((x, y, z), (x, y, z + 1), (x, y, z - 1))
            elif mode == GRENADE_DESTROY:
                cand = tuple((a, b, c) for a in range(x - 1, x + 2)
                             for b in range(y - 1, y + 2) for c in range(z - 1, z + 2))
            else:
                cand = ((x, y, z),)
            m = self.protocol.map
            return [p for p in cand if 0 <= p[2] < 62 and m.get_solid(*p)]

        def _remove_one(self, xyz):
            m = self.protocol.map
            count = m.destroy_point(*xyz)
            if count:
                self.total_blocks_removed += count
                self.on_block_removed(*xyz)
            action = loaders.BlockAction()
            action.x, action.y, action.z = xyz
            action.value = DESTROY_BLOCK
            action.player_id = self.player_id
            self.protocol.broadcast_contained(action, save=True)

        def on_block_destroy(self, x, y, z, mode):
            proto = self.protocol
            if self.god or self.admin or not proto.authored_protect or proto.player_blocks is None:
                return connection.on_block_destroy(self, x, y, z, mode)
            solid = self._affected(x, y, z, mode)
            allowed = [p for p in solid if self._allowed(p)]
            if len(allowed) == len(solid):
                return connection.on_block_destroy(self, x, y, z, mode)   # nothing protected inside
            if mode == DESTROY_BLOCK or not allowed:
                return False
            # partial: remove only permitted player blocks, each still subject to other scripts' rules
            for p in allowed:
                if connection.on_block_destroy(self, p[0], p[1], p[2], DESTROY_BLOCK) is False:
                    continue
                self._remove_one(p)
            proto.update_entities()
            return False                                    # cancel the area action itself

    return AuthoredProtectProtocol, AuthoredProtectConnection
