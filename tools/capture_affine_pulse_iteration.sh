#!/usr/bin/env bash
set -euo pipefail

ROOT=/home/ubuntu/dazzlingPlatinum
RAW=${1:?usage: capture_affine_pulse_iteration.sh SAVE ROM OUTDIR [MOVE_GRID_REFERENCE]}
ROM=${2:?usage: capture_affine_pulse_iteration.sh SAVE ROM OUTDIR [MOVE_GRID_REFERENCE]}
OUT=${3:?usage: capture_affine_pulse_iteration.sh SAVE ROM OUTDIR [MOVE_GRID_REFERENCE]}
RAW=$(realpath "$RAW")
ROM=$(realpath "$ROM")
OUT=$(realpath -m "$OUT")
BASE=$(basename "$ROM" .nds)_affine_pulse
DSV=/home/ubuntu/.config/desmume/${BASE}.dsv
REFERENCE=${4:-"$ROOT/deliverables/mega-staraptor-proof/live-test/emulator-run-extended-2/07_move_select_before_mega.png"}
REFERENCE=$(realpath "$REFERENCE")

mkdir -p "$OUT"
rm -rf "$OUT"/*
rm -f "$DSV"
python3 "$ROOT/tools/make_desmume_dsv.py" "$RAW" "$DSV" > "$OUT/dsv-build.log"
cp "$ROM" "$OUT/$BASE.nds"
convert "$REFERENCE" -crop 256x192+0+192 +repage "$OUT/reference-move-grid.png"

openbox >"$OUT/openbox.log" 2>&1 & wm_pid=$!
sleep 0.5
sound_args=(--disable-sound)
audio_pid=""
if [[ "${AFFINE_CAPTURE_AUDIO:-0}" == "1" ]]; then
  sound_args=()
  parec --device="${AFFINE_AUDIO_SOURCE:-affine_null.monitor}" --file-format=wav "$OUT/emulator-audio.wav" >"$OUT/parec.log" 2>&1 & audio_pid=$!
fi
/usr/games/desmume-cli "${sound_args[@]}" --nojoy=1 --save-type=6 --autodetect_method=0 "$OUT/$BASE.nds" >"$OUT/desmume.log" 2>&1 & pid=$!
cleanup() {
  kill "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
  if [[ -n "$audio_pid" ]]; then
    kill "$audio_pid" 2>/dev/null || true
    wait "$audio_pid" 2>/dev/null || true
  fi
  kill "$wm_pid" 2>/dev/null || true
  wait "$wm_pid" 2>/dev/null || true
}
trap cleanup EXIT

win=""
for _ in $(seq 1 80); do
  win=$(xdotool search --onlyvisible --pid "$pid" --name DeSmuME | head -1 || true)
  [[ -n "$win" ]] && break
  sleep 0.25
done
[[ -n "$win" ]] || { echo 'DeSmuME window not found' >&2; exit 1; }

focus() { xdotool windowactivate --sync "$win" || xdotool windowfocus --sync "$win" || true; }
tap() { focus; xdotool keydown "$1"; sleep "${2:-0.10}"; xdotool keyup "$1"; }
hold() { focus; xdotool keydown "$1"; sleep "${2:-1.1}"; xdotool keyup "$1"; }
shot() { import -window "$win" "$OUT/$1.png"; }

move_grid_visible() {
  local source=$1 crop="$OUT/.sync-current.png" metric normalized
  convert "$source" -crop 256x192+0+192 +repage "$crop"
  metric=$(compare -metric RMSE "$OUT/reference-move-grid.png" "$crop" null: 2>&1 || true)
  normalized=$(printf '%s' "$metric" | sed -n 's/.*(\([^)]*\)).*/\1/p')
  [[ -n "$normalized" ]] || return 1
  awk -v value="$normalized" 'BEGIN { exit !(value < 0.08) }'
}

# Load the validated Route 206 save through the two-stage title flow.
sleep 32
tap Return 0.40
sleep 2
tap Return 0.05
sleep 1
for _ in $(seq 1 12); do tap x 0.08; sleep 1; done
sleep 2
tap Return 0.15
sleep 4
shot 00_overworld_loaded

# Enter a genuine wild battle by sweeping the proven eligible grass region.
for key in Left Left Left Down Down Down Right Right Right; do
  hold "$key" 1.1
  sleep 0.35
done
for key in Up Down Up Left Right Up Down Left Right; do
  hold "$key" 1.1
  sleep 0.35
done
shot 01_battle_entry_probe
sleep 5

# Advance one message at a time until the actual move grid is visible. The visual
# gate prevents an extra A press from prematurely submitting Close Combat.
move_ready=0
for i in $(seq -w 1 18); do
  shot "02_sync_${i}"
  if move_grid_visible "$OUT/02_sync_${i}.png"; then
    cp "$OUT/02_sync_${i}.png" "$OUT/03_move_grid_confirmed.png"
    printf 'move-grid synchronized at probe %s\n' "$i" > "$OUT/synchronization.txt"
    move_ready=1
    break
  fi
  tap x 0.10
  sleep 1.5
done
[[ "$move_ready" -eq 1 ]] || { echo 'Move grid synchronization failed' >&2; exit 2; }

# Navigate through the game's native move cursor to MEGA, toggle it, return to
# Move 1, and submit. No touchscreen or synthetic battle-state shortcuts are used.
tap Down 0.10
sleep 0.35
tap Down 0.10
sleep 0.60
shot 04_mega_button_selected
tap x 0.10
sleep 0.60
shot 05_mega_button_active
tap Up 0.10
sleep 0.35
tap Up 0.10
sleep 0.55
shot 06_move_one_reselected
tap x 0.10

# Dense capture across announcement, charge, silhouette compression, concealed
# form swap, flash, Mega overshoot, settle, cry, and restored battle state.
for i in $(seq -w 0 79); do
  sleep 0.10
  shot "07_transform_${i}"
done

# Preserve later messages and post-turn state, including Contrary proof.
for i in $(seq -w 1 12); do
  tap x 0.10
  sleep 1.25
  shot "08_message_advance_${i}"
done

sha256sum "$RAW" "$ROM" "$DSV" "$OUT"/*.png > "$OUT/hashes.sha256"
printf 'save=%s\nrom=%s\nwindow=%s\n' "$RAW" "$ROM" "$win" > "$OUT/run-metadata.txt"
