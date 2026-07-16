#!/usr/bin/env bash
set -euo pipefail

ROOT=/home/ubuntu/dazzlingPlatinum
RAW=${1:?usage: capture_mega_button_energy_border.sh SAVE ROM OUTDIR LABEL}
ROM=${2:?usage: capture_mega_button_energy_border.sh SAVE ROM OUTDIR LABEL}
OUT=${3:?usage: capture_mega_button_energy_border.sh SAVE ROM OUTDIR LABEL}
LABEL=${4:?usage: capture_mega_button_energy_border.sh SAVE ROM OUTDIR LABEL}
RAW=$(realpath "$RAW")
ROM=$(realpath "$ROM")
OUT=$(realpath -m "$OUT")
BASE=$(basename "$ROM" .nds)_${LABEL}_energy_border
DSV=/home/ubuntu/.config/desmume/${BASE}.dsv
REFERENCE="$ROOT/deliverables/mega-staraptor-proof/live-test/emulator-run-extended-2/07_move_select_before_mega.png"

mkdir -p "$OUT/frames"
rm -f "$OUT"/*.png "$OUT"/*.gif "$OUT"/*.mp4 "$OUT"/*.txt "$OUT"/*.log "$OUT/frames"/*.png "$DSV"
python3 "$ROOT/tools/make_desmume_dsv.py" "$RAW" "$DSV" > "$OUT/dsv-build.log"
cp "$ROM" "$OUT/$BASE.nds"
CAPTURE_ROM="$OUT/$BASE.nds"
convert "$REFERENCE" -crop 256x192+0+192 +repage "$OUT/reference-move-grid.png"

openbox > "$OUT/openbox.log" 2>&1 & wm_pid=$!
sleep 0.5
/usr/games/desmume-cli --disable-sound --nojoy=1 --save-type=6 --autodetect_method=0 "$CAPTURE_ROM" > "$OUT/desmume.log" 2>&1 & pid=$!
cleanup() {
  kill "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
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
frame() { import -window "$win" "$OUT/frames/$1.png"; }
move_grid_visible() {
  local source=$1 crop="$OUT/.sync-current.png" metric normalized
  convert "$source" -crop 256x192+0+192 +repage "$crop"
  metric=$(compare -metric RMSE "$OUT/reference-move-grid.png" "$crop" null: 2>&1 || true)
  normalized=$(printf '%s' "$metric" | sed -n 's/.*(\([^)]*\)).*/\1/p')
  [[ -n "$normalized" ]] || return 1
  awk -v value="$normalized" 'BEGIN { exit !(value < 0.08) }'
}

# Load the supplied Route 206 save and enter the proven grass encounter.
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

for key in Left Left Left Down Down Down Right Right Right; do
  hold "$key" 1.1
  sleep 0.35
done
for key in Up Down Up Left Right Up Down Left Right; do
  hold "$key" 1.1
  sleep 0.35
done
sleep 5

move_ready=0
for i in $(seq -w 1 18); do
  shot "sync_${i}"
  if move_grid_visible "$OUT/sync_${i}.png"; then
    cp "$OUT/sync_${i}.png" "$OUT/01_move_select_inactive.png"
    printf 'move-grid synchronized at probe %s\n' "$i" > "$OUT/synchronization.txt"
    move_ready=1
    break
  fi
  tap x 0.10
  sleep 1.5
done
[[ "$move_ready" -eq 1 ]] || { echo 'Move grid synchronization failed' >&2; exit 2; }

# Move1 -> Move3 -> MEGA down the native left-column cursor path.
tap Down 0.12
sleep 0.25
tap Down 0.12
sleep 0.40
shot 02_mega_cursor_inactive

# Arm MEGA. Capture long enough to include a complete 84-frame loop and the
# start of the following lap, even with normal screenshot overhead.
tap x 0.12
sleep 0.08
for i in $(seq -w 0 23); do
  frame "armed_${i}"
  sleep 0.055
done
shot 03_armed_after_loop

# Disarm on the same cursor target; the border must return to its base palette.
tap x 0.12
sleep 0.30
shot 04_disarmed_cleanup

# Rearm to prove deterministic restart from the first path segment.
tap x 0.12
sleep 0.08
for i in $(seq -w 0 7); do
  frame "rearmed_${i}"
  sleep 0.055
done
shot 05_rearmed_repeatability

sha256sum "$RAW" "$ROM" "$DSV" "$OUT"/*.png "$OUT"/frames/*.png > "$OUT/hashes.sha256"
printf 'label=%s\nsave=%s\nsource_rom=%s\ncapture_rom=%s\nwindow=%s\npid=%s\n' "$LABEL" "$RAW" "$ROM" "$CAPTURE_ROM" "$win" "$pid" > "$OUT/run-metadata.txt"
