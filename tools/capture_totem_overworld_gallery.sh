#!/usr/bin/env bash
set -euo pipefail

ROOT=/home/ubuntu/dazzlingPlatinum
RAW=${1:-$ROOT/deliverables/totem-overworld-sprites/gallery-build/totem-overworld-gallery.sav}
ROM=${2:-$ROOT/deliverables/totem-overworld-sprites/gallery-build/totem-overworld-gallery.nds}
OUT=${3:-$ROOT/deliverables/totem-overworld-sprites/emulator-gallery-iteration-1}
RAW=$(realpath "$RAW")
ROM=$(realpath "$ROM")
OUT=$(realpath -m "$OUT")
BASE=totem_overworld_gallery_capture
DSV=/home/ubuntu/.config/desmume/${BASE}.dsv
CAPTURE_ROM=$OUT/${BASE}.nds

mkdir -p "$OUT/frames"
rm -f "$OUT"/*.png "$OUT"/*.txt "$OUT"/*.log "$OUT/frames"/*.png "$DSV" "$CAPTURE_ROM"
python3 "$ROOT/tools/make_desmume_dsv.py" "$RAW" "$DSV" > "$OUT/dsv-build.log"
cp "$ROM" "$CAPTURE_ROM"

openbox > "$OUT/openbox.log" 2>&1 &
wm_pid=$!
/usr/games/desmume-cli --disable-sound --nojoy=1 --save-type=6 --autodetect_method=0 "$CAPTURE_ROM" > "$OUT/desmume.log" 2>&1 &
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
  win=$(xdotool search --onlyvisible --pid "$pid" --name DeSmuME | head -1 || true)
  [[ -n "$win" ]] && break
  sleep 0.25
done
[[ -n "$win" ]] || { echo 'DeSmuME window not found' >&2; exit 1; }

focus() { xdotool windowactivate --sync "$win" || xdotool windowfocus --sync "$win" || true; }
tap() { focus; xdotool keydown "$1"; sleep "${2:-0.10}"; xdotool keyup "$1"; }
shot() { import -window "$win" "$OUT/$1.png"; }
frame() { import -window "$win" "$OUT/frames/$1.png"; }

# Wait through boot, load the generated save, and dismiss any stale save prompts.
sleep 32
tap Return 0.40
sleep 2
tap Return 0.08
sleep 1
for _ in $(seq 1 12); do
  tap x 0.08
  sleep 1
done
sleep 2
tap Return 0.15
sleep 4
shot 00_gallery_loaded

# Capture several idle-animation phases without moving the player or camera.
for i in $(seq -w 0 31); do
  frame "gallery_${i}"
  sleep 0.08
done
shot 01_gallery_after_idle_cycle

# Move one tile only if needed to exercise camera redraw, then return to the
# canonical generated-save position. The gallery remains fully in view.
tap Left 0.18
sleep 0.8
shot 02_gallery_camera_redraw
tap Right 0.18
sleep 0.8
shot 03_gallery_returned

sha256sum "$RAW" "$ROM" "$DSV" "$OUT"/*.png "$OUT"/frames/*.png > "$OUT/hashes.sha256"
printf 'save=%s\nsource_rom=%s\ncapture_rom=%s\nwindow=%s\npid=%s\n' \
  "$RAW" "$ROM" "$CAPTURE_ROM" "$win" "$pid" > "$OUT/run-metadata.txt"
