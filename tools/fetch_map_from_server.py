"""Minimal AoS 0.75 network client: connect to a server, download the map, compare with a file.

Protocol facts used (piqueserver 1.4.2 source):
  * ENet host with range-coder compression (pyspades/protocol.py compress_with_range_coder)
  * connect data must equal GAME_VERSION = 3 (pyspades/player.py on_connect)
  * map arrives as MapStart (id 18, uint32 size estimate) then MapChunk (id 19) packets carrying a
    zlib stream of VXLData generator output (pyspades/mapgenerator.py)
This verifies what a client RECEIVES. It does not render, spawn or play.
Usage: python tools/fetch_map_from_server.py <port> <expected.vxl>
"""
import hashlib
import sys
import time
import zlib

import enet

GAME_VERSION = 3


def fetch(port, timeout=30.0):
    host = enet.Host(None, 1, 1, 0, 0)
    host.compress_with_range_coder()
    peer = host.connect(enet.Address(b'127.0.0.1', port), 1, GAME_VERSION)
    chunks, started, other_ids = [], False, []
    deadline = time.time() + timeout
    done = False
    while time.time() < deadline and not done:
        ev = host.service(100)
        if ev.type == enet.EVENT_TYPE_RECEIVE:
            data = bytes(ev.packet.data)
            pid = data[0]
            if pid == 18:
                started = True
            elif pid == 19:
                chunks.append(data[1:])
            else:
                other_ids.append(pid)
                if started and chunks:          # first non-map packet after chunks: transfer done
                    done = True
        elif ev.type == enet.EVENT_TYPE_DISCONNECT:
            break
    peer.disconnect()
    host.service(100)
    raw = zlib.decompress(b''.join(chunks)) if chunks else b''
    return raw, {'map_start_seen': started, 'chunks': len(chunks),
                 'compressed_bytes': sum(map(len, chunks)), 'first_other_packet_ids': other_ids[:8]}


if __name__ == '__main__':
    port, expected = int(sys.argv[1]), open(sys.argv[2], 'rb').read()
    raw, info = fetch(port)
    info['received_bytes'] = len(raw)
    info['received_sha256'] = hashlib.sha256(raw).hexdigest()
    info['file_sha256'] = hashlib.sha256(expected).hexdigest()
    info['byte_identical_to_file'] = raw == expected
    print(info)
