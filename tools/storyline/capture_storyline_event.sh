#!/usr/bin/env bash
set -euo pipefail

ROM=${1:?usage: capture_storyline_event.sh ROM RAW_SAVE SCENARIO OUT_DIR}
RAW=${2:?usage: capture_storyline_event.sh ROM RAW_SAVE SCENARIO OUT_DIR}
SCENARIO=${3:?usage: capture_storyline_event.sh ROM RAW_SAVE SCENARIO OUT_DIR}
OUT=${4:?usage: capture_storyline_event.sh ROM RAW_SAVE SCENARIO OUT_DIR}
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
ROM=$(readlink -f "$ROM")
RAW=$(readlink -f "$RAW")
OUT=$(mkdir -p "$OUT" && readlink -f "$OUT")
base="storyline_${SCENARIO}"
capture_rom="$OUT/$base.nds"
dsv="$HOME/.config/desmume/$base.dsv"

[[ $(stat -c %s "$RAW") -eq 524288 ]] || { echo "raw save must be 524288 bytes" >&2; exit 1; }
mkdir -p "$(dirname "$dsv")"
rm -f "$OUT"/*.png "$OUT"/*.log "$OUT"/*.txt "$dsv" "$HOME/.config/desmume/$base.sav"
cp "$ROM" "$capture_rom"
python3 "$ROOT/tools/make_desmume_dsv.py" "$RAW" "$dsv" >"$OUT/dsv-wrap.log"

openbox >"$OUT/openbox.log" 2>&1 &
wm_pid=$!
/usr/games/desmume-cli --disable-sound --nojoy=1 --save-type=6 --autodetect_method=0 "$capture_rom" >"$OUT/desmume.log" 2>&1 &
pid=$!
cleanup() {
  kill "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
  kill "$wm_pid" 2>/dev/null || true
  wait "$wm_pid" 2>/dev/null || true
}
trap cleanup EXIT

win=""
for _ in $(seq 1 120); do
  win=$(xdotool search --onlyvisible --pid "$pid" --name DeSmuME | tail -1 || true)
  [[ -n "$win" ]] && break
  sleep 0.25
done
[[ -n "$win" ]] || { echo "DeSmuME window not found" >&2; exit 2; }
focus() { xdotool windowactivate --sync "$win" || xdotool windowfocus --sync "$win" || true; }
tap() { focus; xdotool keydown "$1"; sleep "${2:-0.12}"; xdotool keyup "$1"; }
shot() { import -window "$win" "$OUT/$1.png"; }

# Reuse the exact Continue and Journal sequence proven by the successful
# Everspring traversal harness. Advancing all journal pages avoids a rendered
# but input-locked field state on inherited advanced saves.
sleep 32
tap Return 0.30
sleep 2
tap Return 0.15
sleep 1
for _ in $(seq 1 12); do
  tap x 0.12
  sleep 0.58
done
sleep 2
tap Return 0.15
sleep 6
shot 00_overworld_loaded

# Most fixtures begin one tile south of their trigger. The Spear Pillar
# blocked-gate fixture approaches from the walkable north side instead.
trigger_key=Up
[[ "$SCENARIO" == "act3_blocked" ]] && trigger_key=Down
tap "$trigger_key" 0.18
sleep 2
shot 01_event_triggered

case "$SCENARIO" in
  act1_cyrus) steps=14 ;;
  act1_rival) steps=18 ;;
  act2_everspring) steps=18 ;;
  act3_blocked) steps=4 ;;
  act3_climax) steps=24 ;;
  *) echo "unknown scenario: $SCENARIO" >&2; exit 3 ;;
esac

for i in $(seq 1 "$steps"); do
  tap x 0.12
  sleep 1.15
  printf -v label '%02d_after_a_%02d' "$((i + 1))" "$i"
  shot "$label"
done

sha256sum "$RAW" "$ROM" "$OUT"/*.png >"$OUT/hashes.sha256"
printf 'scenario=%s\nproduction_rom=%s\nsave=%s\nwindow=%s\npid=%s\nsteps=%s\n' \
  "$SCENARIO" "$ROM" "$RAW" "$win" "$pid" "$steps" >"$OUT/run-metadata.txt"
