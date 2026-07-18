#!/usr/bin/env bash
set -euo pipefail

ROM=${1:?usage: capture_totem_encounter_start.sh ROM RAW_SAVE SPECIES APPROACH_KEY OUT_DIR}
RAW=${2:?usage: capture_totem_encounter_start.sh ROM RAW_SAVE SPECIES APPROACH_KEY OUT_DIR}
SPECIES=${3:?usage: capture_totem_encounter_start.sh ROM RAW_SAVE SPECIES APPROACH_KEY OUT_DIR}
APPROACH=${4:?usage: capture_totem_encounter_start.sh ROM RAW_SAVE SPECIES APPROACH_KEY OUT_DIR}
OUT=${5:?usage: capture_totem_encounter_start.sh ROM RAW_SAVE SPECIES APPROACH_KEY OUT_DIR}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
ROM=$(readlink -f "$ROM")
RAW=$(readlink -f "$RAW")
OUT=$(mkdir -p "$OUT" && readlink -f "$OUT")
slug=$(printf '%s' "$SPECIES" | tr '[:upper:]' '[:lower:]')
base="totem_encounter_${slug}"
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
for _ in $(seq 1 100); do
  win=$(xdotool search --onlyvisible --pid "$pid" --name DeSmuME | tail -1 || true)
  [[ -n "$win" ]] && break
  sleep 0.25
done
[[ -n "$win" ]] || { echo "DeSmuME window not found" >&2; exit 2; }
focus() { xdotool windowactivate --sync "$win" || xdotool windowfocus --sync "$win" || true; }
tap() { focus; xdotool keydown "$1"; sleep "${2:-0.12}"; xdotool keyup "$1"; }
shot() { import -window "$win" "$OUT/$1.png"; }

# Deterministic title flow proven by debug_totem_boot_sequence.sh:
# Start skips to the title, Start opens the menu, and exactly one A selects Continue.
# Never spam A here: the next A press after field load would trigger an adjacent Totem.
sleep 32
tap Return 0.30
sleep 3
tap Return 0.15
sleep 4
tap x 0.12
sleep 4
shot 00_overworld_loaded

# Face the adjacent stationary Totem when requested, then press the DS A button (keyboard X).
# `Stay` preserves a save that already faces the object and avoids stepping into non-solid billboards.
case "$APPROACH" in
  Stay)
    ;;
  FaceUp)
    tap Down 0.18
    sleep 0.35
    tap Up 0.18
    ;;
  FaceDown)
    tap Up 0.18
    sleep 0.35
    tap Down 0.18
    ;;
  FaceLeft)
    tap Right 0.18
    sleep 0.35
    tap Left 0.18
    ;;
  FaceRight)
    tap Left 0.18
    sleep 0.35
    tap Right 0.18
    ;;
  *)
    tap "$APPROACH" 0.18
    ;;
esac
sleep 1
shot 01_facing_totem
tap x 0.15
sleep 0.50
shot 02_after_a_050ms
sleep 1.50
shot 03_battle_transition
sleep 5
shot 04_battle_started

sha256sum "$RAW" "$ROM" "$OUT"/*.png >"$OUT/hashes.sha256"
printf 'species=%s\nproduction_rom=%s\nsave=%s\napproach_key=%s\nwindow=%s\npid=%s\n' \
  "$SPECIES" "$ROM" "$RAW" "$APPROACH" "$win" "$pid" >"$OUT/run-metadata.txt"
