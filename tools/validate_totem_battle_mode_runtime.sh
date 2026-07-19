#!/usr/bin/env bash
set -euo pipefail

ROM=${1:?usage: validate_totem_battle_mode_runtime.sh ROM VESPIQUEN_RAW_SAVE OUT_DIR [APPROACH_KEY]}
RAW=${2:?usage: validate_totem_battle_mode_runtime.sh ROM VESPIQUEN_RAW_SAVE OUT_DIR [APPROACH_KEY]}
OUT=${3:?usage: validate_totem_battle_mode_runtime.sh ROM VESPIQUEN_RAW_SAVE OUT_DIR [APPROACH_KEY]}
APPROACH=${4:-Right}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
ROM=$(readlink -f "$ROM")
RAW=$(readlink -f "$RAW")
OUT=$(mkdir -p "$OUT" && readlink -f "$OUT")
BASE=totem_battle_mode_runtime
CAPTURE_ROM="$OUT/$BASE.nds"
DSV="$HOME/.config/desmume/$BASE.dsv"
PID=""
WM_PID=""

case "$OUT/" in
  "$ROOT/"*)
    echo "output directory must be outside the repository: $OUT" >&2
    exit 2
    ;;
esac

[[ -f "$ROM" ]] || { echo "ROM not found: $ROM" >&2; exit 2; }
[[ -f "$RAW" ]] || { echo "save not found: $RAW" >&2; exit 2; }
[[ $(stat -c %s "$RAW") -eq 524288 ]] || {
  echo "raw save must be exactly 524288 bytes: $RAW" >&2
  exit 2
}
for command in openbox /usr/games/desmume-cli xdotool import montage identify sha256sum; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "required command not found: $command" >&2
    exit 2
  }
done

mkdir -p "$(dirname "$DSV")"
rm -f "$OUT"/*.png "$OUT"/*.log "$OUT"/*.txt "$OUT"/*.sha256 \
  "$CAPTURE_ROM" "$DSV" "$HOME/.config/desmume/$BASE.sav"
cp "$ROM" "$CAPTURE_ROM"
python3 "$ROOT/tools/make_desmume_dsv.py" "$RAW" "$DSV" >"$OUT/dsv-wrap.log"

cleanup() {
  if [[ -n "$PID" ]]; then
    kill "$PID" 2>/dev/null || true
    wait "$PID" 2>/dev/null || true
  fi
  if [[ -n "$WM_PID" ]]; then
    kill "$WM_PID" 2>/dev/null || true
    wait "$WM_PID" 2>/dev/null || true
  fi
  rm -f "$CAPTURE_ROM"
}
trap cleanup EXIT

openbox >"$OUT/openbox.log" 2>&1 &
WM_PID=$!
/usr/games/desmume-cli --disable-sound --nojoy=1 --save-type=6 --autodetect_method=0 \
  "$CAPTURE_ROM" >"$OUT/desmume.log" 2>&1 &
PID=$!

WIN=""
for _ in $(seq 1 100); do
  WIN=$(xdotool search --onlyvisible --pid "$PID" --name DeSmuME | tail -1 || true)
  [[ -n "$WIN" ]] && break
  sleep 0.25
done
[[ -n "$WIN" ]] || { echo "DeSmuME window not found" >&2; exit 3; }

focus() {
  kill -0 "$PID" 2>/dev/null || {
    echo "DeSmuME exited unexpectedly" >&2
    return 1
  }
  xdotool windowactivate --sync "$WIN" 2>/dev/null \
    || xdotool windowfocus --sync "$WIN" 2>/dev/null \
    || true
}
tap() {
  focus
  xdotool keydown "$1"
  sleep "${2:-0.12}"
  xdotool keyup "$1"
}
shot() {
  local name=$1
  local attempt
  for attempt in 1 2 3; do
    if import -window "$WIN" "$OUT/$name.png" 2>/dev/null; then
      identify "$OUT/$name.png" >/dev/null
      return 0
    fi
    sleep 0.5
  done
  echo "failed to capture frame: $name" >&2
  return 1
}

# Deterministic title flow: Continue, dismiss the optional journal, and return to
# the field. The controlled Vespiquen save is adjacent to the encounter object.
sleep 32
tap Return 0.30
sleep 3
tap Return 0.15
sleep 4
tap x 0.12
sleep 4
tap z 0.12
sleep 1
shot 00_overworld_loaded

case "$APPROACH" in
  Stay) ;;
  FaceUp) tap Down 0.18; sleep 0.35; tap Up 0.18 ;;
  FaceDown) tap Up 0.18; sleep 0.35; tap Down 0.18 ;;
  FaceLeft) tap Right 0.18; sleep 0.35; tap Left 0.18 ;;
  FaceRight) tap Left 0.18; sleep 0.35; tap Right 0.18 ;;
  *) tap "$APPROACH" 0.18 ;;
esac
sleep 1
shot 01_facing_vespiquen

tap x 0.15
sleep 7
shot 02_totem_intro

# Advance the wild-appearance prompt and five +1 stat prompts. Vespiquen's
# Pressure message remains visible after these six confirmations.
for _ in 1 2 3 4 5 6; do
  tap x 0.15
  sleep 2
done
shot 03_pressure_message

# Turn 1: clear Pressure, choose Splash, confirm the highlighted player target,
# and wait for Combee (party slot 1) to be summoned at end of turn.
tap x 0.15
sleep 3
tap x 0.15
sleep 3
shot 04_turn1_move_menu
tap x 0.15
sleep 3
shot 05_turn1_target
tap x 0.15
sleep 3
tap x 0.15
sleep 3
shot 06_turn1_started
for frame in $(seq -w 1 15); do
  sleep 2
  shot "07_turn1_progress_$frame"
done
shot 08_after_first_summon

# Turn 2: choose Aerial Ace, move the default target from Vespiquen to Combee,
# KO it, and wait for Beautifly (party slot 2) to replace the vacant ally slot.
tap x 0.15
sleep 3
shot 10_turn2_move_menu
tap Right 0.18
sleep 2
shot 11_turn2_aerial_ace
tap x 0.15
sleep 3
shot 12_turn2_default_target
tap Left 0.18
sleep 2
shot 13_turn2_combee_target
tap x 0.15
sleep 3
shot 14_turn2_started
for frame in $(seq -w 1 18); do
  sleep 2
  shot "15_turn2_progress_$frame"
done
shot 16_after_second_summon

# Turn 3: KO Beautifly. The cap is now exhausted, so the battle must return to
# command selection with Vespiquen alone and no third wild-appearance sequence.
tap x 0.15
sleep 3
shot 20_turn3_move_menu
tap Right 0.18
sleep 2
shot 21_turn3_aerial_ace
tap x 0.15
sleep 3
shot 22_turn3_default_target
tap Left 0.18
sleep 2
shot 23_turn3_beautifly_target
tap x 0.15
sleep 3
shot 24_turn3_started
for frame in $(seq -w 1 20); do
  sleep 2
  shot "25_turn3_progress_$frame"
done
shot 26_after_summon_cap

# Turn 4: with no ally remaining, KO the Totem and capture the return to field.
tap x 0.15
sleep 3
shot 30_turn4_move_menu
tap Right 0.18
sleep 2
shot 31_turn4_aerial_ace
tap x 0.15
sleep 3
shot 32_turn4_default_target
tap Right 0.18
sleep 2
shot 33_turn4_totem_target
tap x 0.15
sleep 3
shot 34_turn4_started
for frame in $(seq -w 1 18); do
  sleep 2
  shot "35_turn4_progress_$frame"
done
shot 36_after_totem_victory

kill "$PID" 2>/dev/null || true
wait "$PID" 2>/dev/null || true
PID=""
kill "$WM_PID" 2>/dev/null || true
wait "$WM_PID" 2>/dev/null || true
WM_PID=""
rm -f "$CAPTURE_ROM"

montage "$OUT"/02_totem_intro.png "$OUT"/03_pressure_message.png \
  "$OUT"/04_turn1_move_menu.png "$OUT"/05_turn1_target.png \
  "$OUT"/06_turn1_started.png "$OUT"/07_turn1_progress_*.png \
  -thumbnail 256x384 -tile 3x -geometry +8+18 -background '#20242b' \
  -fill white -pointsize 12 -set label '%t' "$OUT/first-summon-contact-sheet.png"
montage "$OUT"/10_turn2_move_menu.png "$OUT"/11_turn2_aerial_ace.png \
  "$OUT"/12_turn2_default_target.png "$OUT"/13_turn2_combee_target.png \
  "$OUT"/14_turn2_started.png "$OUT"/15_turn2_progress_*.png \
  -thumbnail 256x384 -tile 3x -geometry +8+18 -background '#20242b' \
  -fill white -pointsize 12 -set label '%t' "$OUT/second-summon-contact-sheet.png"
montage "$OUT"/20_turn3_move_menu.png "$OUT"/21_turn3_aerial_ace.png \
  "$OUT"/22_turn3_default_target.png "$OUT"/23_turn3_beautifly_target.png \
  "$OUT"/24_turn3_started.png "$OUT"/25_turn3_progress_*.png \
  -thumbnail 256x384 -tile 3x -geometry +8+18 -background '#20242b' \
  -fill white -pointsize 12 -set label '%t' "$OUT/summon-cap-contact-sheet.png"
montage "$OUT"/30_turn4_move_menu.png "$OUT"/31_turn4_aerial_ace.png \
  "$OUT"/32_turn4_default_target.png "$OUT"/33_turn4_totem_target.png \
  "$OUT"/34_turn4_started.png "$OUT"/35_turn4_progress_*.png \
  "$OUT"/36_after_totem_victory.png \
  -thumbnail 256x384 -tile 3x -geometry +8+18 -background '#20242b' \
  -fill white -pointsize 12 -set label '%t' "$OUT/totem-victory-contact-sheet.png"

sha256sum "$RAW" "$ROM" "$OUT"/*.png >"$OUT/hashes.sha256"
cat >"$OUT/run-metadata.txt" <<EOF
scenario=vespiquen_two_summon_cap_and_totem_victory
production_rom=$ROM
controlled_save=$RAW
approach_key=$APPROACH
opening_boost_prompts=5
expected_first_ally=COMBEE
expected_second_ally=BEAUTIFLY
expected_summon_cap=2
expected_terminal_condition=TOTEM_KO_WIN
status=CAPTURE_COMPLETE_REQUIRES_VISUAL_REVIEW
EOF

printf 'Runtime evidence captured in %s\n' "$OUT"
printf 'Review: first-summon-contact-sheet.png, second-summon-contact-sheet.png, summon-cap-contact-sheet.png, totem-victory-contact-sheet.png\n'
