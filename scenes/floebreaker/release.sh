#!/usr/bin/env bash
# Rebuild + validate Floebreaker v1.   bash scenes/floebreaker/release.sh [decor_seed]
# Needs: python 3.11+ with numpy/scipy/pillow (toolchain) and the repo venv python (piqueserver 1.4.2) as $VENV_PY.
set -e
R=maps/floebreaker_v1
VENV_PY=${VENV_PY:-"D:/Ace of Spades/Aos_Map/venv/Scripts/python.exe"}
python scenes/floebreaker/fb_main.py $R ${1:+--seed $1}
for v in day night; do python scenes/floebreaker/fb_float.py $R $v; python -I scenes/floebreaker/fb_check.py $R $v --exposure >/dev/null; done
"$VENV_PY" scenes/floebreaker/fb_pyspades.py $R >/dev/null
python scenes/floebreaker/fb_render.py $R $R/previews
python -I tools/art_metrics.py $R/art_metrics.json $R/floebreaker_day.vxl $R/floebreaker_night.vxl
