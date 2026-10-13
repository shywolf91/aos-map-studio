#!/usr/bin/env bash
# Screenshot a map in the REAL BetterSpades client (headless, Linux), joined to a running server as a spectator.
#
# Setup used 2026-10-13 (Ubuntu 24.04 container):
#   apt install libglfw3-dev libglew-dev libenet-dev libdeflate-dev xvfb xdotool imagemagick
#   git clone https://github.com/xtreme8000/BetterSpades   (master a695aaa)
#   git apply tools/betterspades_camfile.patch             (spectator camera read from $AOSMAP_CAMFILE)
#   cmake -B build -DCMAKE_BUILD_TYPE=Release -DENABLE_SOUND=OFF && make -C build
#   aos.party/bsresources.zip (gun models/icons) was unreachable: semi/smg/shotgun .kv6/.png were replaced by
#   copies of spade.kv6 / block.png. They only affect held-weapon visuals; map rendering is the client's own.
#
# Usage: tools/betterspades_capture.sh <client_dir> <port> <outdir> <views.txt>
#   views.txt lines: name x y z tx ty tz   (AoS map coords, z down; eye z = floor z - 2.4)
# The server needs nothing special; spectators can see the whole map.
set -euo pipefail
CLIENT_DIR=$1; PORT=$2; OUT=$3; VIEWS=$4
mkdir -p "$OUT"
CAM=$(mktemp); head -n1 "$VIEWS" | cut -d' ' -f2- > "$CAM"
export DISPLAY=${DISPLAY_NUM:-:77}
pgrep -f "Xvfb $DISPLAY" >/dev/null || { Xvfb "$DISPLAY" -screen 0 1100x640x24 >/dev/null 2>&1 & sleep 2; }
( cd "$CLIENT_DIR" && LIBGL_ALWAYS_SOFTWARE=1 AOSMAP_CAMFILE=$CAM ./client -aos://16777343:$PORT >"$OUT/client.log" 2>&1 & )
sleep 15
W=$(xdotool search --name BetterSpades | head -1)
xdotool windowfocus "$W"; xdotool key --window "$W" 3; sleep 3     # 3 = spectate
xdotool key --window "$W" F6; sleep 2                              # hide HUD
while read -r name x y z tx ty tz; do
  [ -z "$name" ] && continue
  echo "$x $y $z $tx $ty $tz" > "$CAM"; sleep 5
  import -window "$W" "$OUT/$name.png"
done < "$VIEWS"
kill "$(xdotool getwindowpid "$W")" 2>/dev/null || true
echo "shots in $OUT"
