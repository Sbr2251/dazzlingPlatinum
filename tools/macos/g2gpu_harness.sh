#!/bin/sh
# Comparison harness for the G2 GPU path (perf-g2gpu).
# Runs the same scenario with SIM_G2_GPU=0 (CPU reference) and =1 (GPU),
# screenshots both, and pixel-diffs them with g2gpu_compare.py.
#
# Usage: tools/macos/g2gpu_harness.sh <scenario-name>
# Scenarios are defined below as env bundles. Run from anywhere; the game
# runs in a scratch dir of symlinks to build_macos/* (see BRIEF).
# ASCII only.
set -e
NAME=${1:?usage: g2gpu_harness.sh <scenario>}
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
SAVES=$HOME/Downloads/dazzling_platinum_test_saves_v2/raw_sav
OUT=/tmp/perf-g2gpu/harness/$NAME
BIN=$ROOT/build_macos/main
[ -x "$BIN" ] || { echo "build first: tools/macos/build.sh"; exit 2; }

# Scenario table: SAVE (optional), KEYS, EXIT frame. Shots every 30 frames.
SAVE=; KEYS=; EXIT=900
case "$NAME" in
  title)   SAVE=; KEYS=; EXIT=600 ;;
  intro)   SAVE=; KEYS="400:A/2"; EXIT=900 ;;
  overworld) SAVE=$SAVES/A1-03_route201_to_sandgem.sav; KEYS="200:UP/30,300:RIGHT/30,400:DOWN/30"; EXIT=900 ;;
  overworld2) SAVE=$SAVES/A2-49_solaceon_memorial_wall.sav; KEYS="200:LEFT/30,300:UP/30"; EXIT=900 ;;
  startmenu) SAVE=$SAVES/A1-03_route201_to_sandgem.sav; KEYS="700:A/2,1500:START/2"; EXIT=2100 ;;
  bag)     SAVE=$SAVES/A1-03_route201_to_sandgem.sav; KEYS="700:A/2,1500:START/2,1800:DOWN/2,1860:DOWN/2,1920:A/2"; EXIT=2400 ;;
  party)   SAVE=$SAVES/A1-03_route201_to_sandgem.sav; KEYS="700:A/2,1500:START/2,1800:DOWN/2,1920:A/2"; EXIT=2400 ;;
  battle)  SAVE=$SAVES/A1-03_route201_to_sandgem.sav; KEYS="700:A/2,1100:UP/90,1500:A/2"; EXIT=2100 ;;
  *) echo "unknown scenario $NAME"; exit 2 ;;
esac

run_one() { # $1=gpu0/1 $2=outdir
  rm -rf "$2"; mkdir -p "$2/shots" "$2/run"
  for f in "$ROOT"/build_macos/*; do ln -sfn "$f" "$2/run/$(basename "$f")"; done
  # Functional runs use InternalResolutionScale=2 (team rule), same for both paths.
  rm -f "$2/run/sim_config.ini"
  sed 's/InternalResolutionScale=.*/InternalResolutionScale=2/' "$ROOT/build_macos/sim_config.ini" > "$2/run/sim_config.ini"
  IMP=
  [ -n "$SAVE" ] && IMP="20:$SAVE"
  # Functional/comparison run (no measurement lock needed; fps is measured
  # separately at the default resolution under the team lock).
  (cd "$2/run" && env SIM_G2_GPU=$1 SIM_DEBUG_FAST=1 SIM_DEBUG_EXIT_FRAME=$EXIT \
    SIM_DEBUG_SHOT_DIR="$2/shots" SIM_DEBUG_SHOT_EVERY=30 \
    ${IMP:+SIM_DEBUG_IMPORT_SAVE="$IMP"} ${KEYS:+SIM_DEBUG_KEYS="$KEYS"} \
    ./main > "$2/log.txt" 2>&1) || true
  grep -E "fps since|SIM_PROFILE|SIM_G2_GPU|ERROR" "$2/log.txt" || true
}
run_one ${CPUGPU:-0} "$OUT/cpu"
run_one 1 "$OUT/gpu"
python3 "$ROOT/tools/macos/g2gpu_compare.py" "$OUT/cpu/shots" "$OUT/gpu/shots"
