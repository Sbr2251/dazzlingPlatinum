#!/usr/bin/env bash
set -euo pipefail

ROM=${1:?usage: validate_totem_victory_persistence.sh ROM STRONG_RAW_SAVE SPECIES APPROACH_KEY OUT_DIR}
RAW=${2:?usage: validate_totem_victory_persistence.sh ROM STRONG_RAW_SAVE SPECIES APPROACH_KEY OUT_DIR}
SPECIES=${3:?usage: validate_totem_victory_persistence.sh ROM STRONG_RAW_SAVE SPECIES APPROACH_KEY OUT_DIR}
APPROACH=${4:?usage: validate_totem_victory_persistence.sh ROM STRONG_RAW_SAVE SPECIES APPROACH_KEY OUT_DIR}
OUT=${5:?usage: validate_totem_victory_persistence.sh ROM STRONG_RAW_SAVE SPECIES APPROACH_KEY OUT_DIR}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
ROM=$(readlink -f "$ROM")
RAW=$(readlink -f "$RAW")
OUT=$(mkdir -p "$OUT" && readlink -f "$OUT")
SLUG=$(printf '%s' "$SPECIES" | tr '[:upper:]' '[:lower:]')
BASE="totem_${SLUG}_victory"
CAPTURE_ROM="$OUT/$BASE.nds"
CONFIG_DIR="$HOME/.config/desmume"
DSV="$CONFIG_DIR/$BASE.dsv"
POST_SAVE="$OUT/${SLUG}-after-victory.sav"
mkdir -p "$CONFIG_DIR"
rm -f "$OUT"/*.png "$OUT"/*.log "$OUT"/*.txt "$OUT"/*.sav "$DSV" "$CONFIG_DIR/$BASE.sav"
cp "$ROM" "$CAPTURE_ROM"
python3 "$ROOT/tools/assert_totem_save_outcome.py" "$RAW" "$SLUG" clear >"$OUT/input-flag-assertion.txt"
python3 "$ROOT/tools/make_desmume_dsv.py" "$RAW" "$DSV" >"$OUT/dsv-wrap.log"

openbox >"$OUT/openbox.log" 2>&1 &
WM_PID=$!
PID=""
cleanup() {
  if [[ -n "$PID" ]]; then
    kill "$PID" 2>/dev/null || true
    wait "$PID" 2>/dev/null || true
  fi
  kill "$WM_PID" 2>/dev/null || true
  wait "$WM_PID" 2>/dev/null || true
}
trap cleanup EXIT
sleep 1

launch() {
  local log=$1
  /usr/games/desmume-cli --disable-sound --nojoy=1 --save-type=6 --autodetect_method=0 "$CAPTURE_ROM" >"$OUT/$log" 2>&1 &
  PID=$!
  WIN=""
  for _ in $(seq 1 100); do
    WIN=$(xdotool search --onlyvisible --pid "$PID" --name DeSmuME | tail -1 || true)
    [[ -n "$WIN" ]] && break
    sleep 0.25
  done
  [[ -n "$WIN" ]] || { echo "DeSmuME window not found" >&2; exit 2; }
}

focus() { xdotool windowactivate --sync "$WIN" || xdotool windowfocus --sync "$WIN" || true; }
tap() { focus; xdotool keydown "$1"; sleep "${2:-0.12}"; xdotool keyup "$1"; }
shot() {
  local name=$1
  for _ in 1 2 3; do
    if import -window "$WIN" "$OUT/$name.png" 2>/dev/null; then return 0; fi
    sleep 0.5
  done
  echo "screenshot failed: $name" >&2
  return 3
}
boot_to_field() {
  sleep 32
  tap Return 0.30
  sleep 3
  tap Return 0.15
  sleep 4
  tap x 0.12
  sleep 4
}
face_totem() {
  case "$APPROACH" in
    Stay) ;;
    FaceUp) tap Down 0.18; sleep 0.35; tap Up 0.18 ;;
    FaceDown) tap Up 0.18; sleep 0.35; tap Down 0.18 ;;
    FaceLeft) tap Right 0.18; sleep 0.35; tap Left 0.18 ;;
    FaceRight) tap Left 0.18; sleep 0.35; tap Right 0.18 ;;
    *) tap "$APPROACH" 0.18 ;;
  esac
  sleep 1
}
stop_emulator() {
  kill "$PID" 2>/dev/null || true
  wait "$PID" 2>/dev/null || true
  PID=""
  sleep 1
}

launch first-run-desmume.log
boot_to_field
face_totem
shot 00_before_interaction
tap x 0.15
sleep 7
shot 01_battle_started

# The test lead is level 100 with 999 battle stats and four always-hit Aerial Ace
# moves. Repeated confirmations select Fight, the first move, and all result text.
for _ in $(seq 1 120); do
  tap x 0.08
  sleep 0.75
done
sleep 4
shot 02_after_victory_field

# Save through Platinum so the defeated and hide flags persist in flash data.
tap s 0.20
sleep 2
shot 03_menu_open
for _ in $(seq 1 4); do tap Down 0.12; sleep 0.25; done
tap x 0.15
sleep 2
tap x 0.15
sleep 2
tap x 0.15
sleep 12
tap x 0.15
sleep 3
shot 04_after_native_save
stop_emulator
sync

[[ -f "$DSV" ]] || { echo "expected DSV not written" >&2; exit 4; }
head -c 524288 "$DSV" >"$POST_SAVE"
python3 "$ROOT/tools/verify_platinum_save.py" "$POST_SAVE" >"$OUT/post-victory-save-verification.txt"
grep -q 'native_main_load_result=OK' "$OUT/post-victory-save-verification.txt"
python3 "$ROOT/tools/inspect_totem_save_flags.py" "$POST_SAVE" >"$OUT/post-victory-totem-flags.txt"
python3 "$ROOT/tools/assert_totem_save_outcome.py" "$POST_SAVE" "$SLUG" set >"$OUT/post-victory-flag-assertion.txt"

# Reload the exact native post-victory DSV and capture the persistent field state.
launch reload-desmume.log
boot_to_field
shot 05_reload_object_absent
stop_emulator

sha256sum "$RAW" "$ROM" "$POST_SAVE" "$OUT"/*.png >"$OUT/hashes.sha256"
printf 'result=PASS\nspecies=%s\nrom=%s\ninput_save=%s\npost_victory_save=%s\napproach_key=%s\n' \
  "$SPECIES" "$ROM" "$RAW" "$POST_SAVE" "$APPROACH" >"$OUT/run-metadata.txt"
