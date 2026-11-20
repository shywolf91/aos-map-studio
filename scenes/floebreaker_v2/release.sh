#!/usr/bin/env bash
# Rebuild + validate Floebreaker v2.   bash scenes/floebreaker_v2/release.sh [decor_seed]
# Needs: python 3.11+ with numpy/scipy/pillow (toolchain) and the repo venv python (piqueserver 1.4.2) as $VENV_PY.
set -e
R=maps/floebreaker_v2
VENV_PY=${VENV_PY:-"D:/Ace of Spades/Aos_Map/venv/Scripts/python.exe"}
python scenes/floebreaker_v2/fb_main.py $R ${1:+--seed $1}
for v in day night; do python scenes/floebreaker_v2/fb_float.py $R $v; python -I scenes/floebreaker_v2/fb_check.py $R $v --exposure >/dev/null; done
"$VENV_PY" scenes/floebreaker_v2/fb_pyspades.py $R >/dev/null
"$VENV_PY" scenes/floebreaker_v2/fb_rules.py $R | grep -E "FAIL|=====|^ +[a-z]" || true
python scenes/floebreaker_v2/fb_render.py $R $R/previews
for v in day night; do python -m aosmap.kit.craft_checks $R/floebreaker_$v.vxl --mode babel --out $R/craft_$v.json | grep -E "FAIL|PASS [0-9]|spawns"; python tools/palette_audit.py $R/floebreaker_$v.vxl --fog $( [ $v = day ] && echo 202,180,200 || echo 172,156,206 ) | grep -E "value bands|dominant|verdict"; done
python -I tools/art_metrics.py $R/art_metrics.json $R/floebreaker_day.vxl $R/floebreaker_night.vxl
