#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
ROM=${1:?usage: validate_totem_walk_reachability.sh ROM ENTRY_SAVE SLUG PATH_RUNS EXPECTED_MAP EXPECTED_X EXPECTED_Z OUT_DIR}
RAW=${2:?usage: validate_totem_walk_reachability.sh ROM ENTRY_SAVE SLUG PATH_RUNS EXPECTED_MAP EXPECTED_X EXPECTED_Z OUT_DIR}
SLUG=${3:?usage: validate_totem_walk_reachability.sh ROM ENTRY_SAVE SLUG PATH_RUNS EXPECTED_MAP EXPECTED_X EXPECTED_Z OUT_DIR}
PATH_RUNS=${4:?usage: validate_totem_walk_reachability.sh ROM ENTRY_SAVE SLUG PATH_RUNS EXPECTED_MAP EXPECTED_X EXPECTED_Z OUT_DIR}
EXPECTED_MAP=${5:?usage: validate_totem_walk_reachability.sh ROM ENTRY_SAVE SLUG PATH_RUNS EXPECTED_MAP EXPECTED_X EXPECTED_Z OUT_DIR}
EXPECTED_X=${6:?usage: validate_totem_walk_reachability.sh ROM ENTRY_SAVE SLUG PATH_RUNS EXPECTED_MAP EXPECTED_X EXPECTED_Z OUT_DIR}
EXPECTED_Z=${7:?usage: validate_totem_walk_reachability.sh ROM ENTRY_SAVE SLUG PATH_RUNS EXPECTED_MAP EXPECTED_X EXPECTED_Z OUT_DIR}
OUT=${8:?usage: validate_totem_walk_reachability.sh ROM ENTRY_SAVE SLUG PATH_RUNS EXPECTED_MAP EXPECTED_X EXPECTED_Z OUT_DIR}

ROM=$(readlink -f "$ROM")
RAW=$(readlink -f "$RAW")
OUT=$(mkdir -p "$OUT" && readlink -f "$OUT")
base="totem_walk_${SLUG}"
capture_rom="$OUT/$base.nds"
dsv="$HOME/.config/desmume/$base.dsv"
arrival_save="$OUT/arrival.sav"

[[ $(stat -c %s "$RAW") -eq 524288 ]] || { echo "raw save must be 524288 bytes" >&2; exit 1; }
expected_map_id=$(grep -n -x "$EXPECTED_MAP" "$ROOT/generated/map_headers.txt" | cut -d: -f1)
[[ -n "$expected_map_id" ]] || { echo "unknown map symbol: $EXPECTED_MAP" >&2; exit 1; }
expected_map_id=$((expected_map_id - 1))

mkdir -p "$(dirname "$dsv")"
rm -f "$OUT"/*.png "$OUT"/*.log "$OUT"/*.txt "$arrival_save" "$dsv" "$HOME/.config/desmume/$base.sav"
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
[[ -n "$win" ]] || { echo "$SLUG: DeSmuME window not found" >&2; exit 2; }
focus() { xdotool windowactivate --sync "$win" || xdotool windowfocus --sync "$win" || true; }
tap() { focus; xdotool keydown "$1"; sleep "${2:-0.12}"; xdotool keyup "$1"; }
shot() { import -window "$win" "$OUT/$1.png"; }

# Proven deterministic title flow: Start, Start, one A to Continue.
sleep 32
tap Return 0.30
sleep 3
tap Return 0.15
sleep 4
tap x 0.12
sleep 4
shot 00_entry_loaded

IFS=',' read -r -a runs <<<"$PATH_RUNS"
run_index=0
total_steps=0
for run in "${runs[@]}"; do
  key=${run%%:*}
  count=${run##*:}
  case "$key" in
    Up|Down|Left|Right) ;;
    *) echo "invalid path key: $key" >&2; exit 3 ;;
  esac
  [[ "$count" =~ ^[0-9]+$ ]] || { echo "invalid path count: $count" >&2; exit 3; }
  run_index=$((run_index + 1))
  for _ in $(seq 1 "$count"); do
    tap "$key" 0.18
    sleep 0.18
    total_steps=$((total_steps + 1))
  done
  sleep 0.5
  printf -v frame 'walk_%02d_after_%s_%s' "$run_index" "$key" "$count"
  shot "$frame"
done
sleep 1
shot 01_arrival_before_save

# Save natively so the resulting raw save records the player location reached by
# ordinary movement rather than by direct save editing or a proof-only warp.
tap s 0.20
sleep 2
shot 02_menu_open
for _ in $(seq 1 4); do tap Down 0.15; sleep 0.25; done
tap x 0.15
sleep 2
tap x 0.15
sleep 2
tap x 0.15
sleep 10
tap x 0.15
sleep 3
shot 03_after_native_save

kill "$pid" 2>/dev/null || true
wait "$pid" 2>/dev/null || true
pid=""
sync
[[ -f "$dsv" ]] || { echo "$SLUG: expected DSV not written" >&2; exit 4; }
head -c 524288 "$dsv" >"$arrival_save"
python3 "$ROOT/tools/verify_platinum_save.py" "$arrival_save" >"$OUT/save-verification.txt"
python3 "$ROOT/tools/inspect_save_player_state.py" "$arrival_save" >"$OUT/player-state.txt"

grep -q 'native_main_load_result=OK' "$OUT/save-verification.txt" || {
  echo "$SLUG: native arrival save validation failed" >&2
  exit 5
}
grep -q "map_id=$expected_map_id .* x=$EXPECTED_X z=$EXPECTED_Z " "$OUT/player-state.txt" || {
  echo "$SLUG: live walk did not reach expected map/coordinate" >&2
  cat "$OUT/player-state.txt" >&2
  exit 6
}

sha256sum "$RAW" "$arrival_save" "$ROM" "$OUT"/*.png >"$OUT/hashes.sha256"
printf 'species=%s\nproduction_rom=%s\nentry_save=%s\npath_runs=%s\ntotal_steps=%s\nexpected_map=%s\nexpected_map_id=%s\nexpected_x=%s\nexpected_z=%s\nwindow=%s\n' \
  "$SLUG" "$ROM" "$RAW" "$PATH_RUNS" "$total_steps" "$EXPECTED_MAP" "$expected_map_id" "$EXPECTED_X" "$EXPECTED_Z" "$win" >"$OUT/run-metadata.txt"
printf '%s: PASS — live walk reached (%s,%s) in %s tile inputs\n' "$SLUG" "$EXPECTED_X" "$EXPECTED_Z" "$total_steps"
