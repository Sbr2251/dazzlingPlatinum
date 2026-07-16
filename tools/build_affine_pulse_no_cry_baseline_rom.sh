#!/usr/bin/env bash
set -euo pipefail

ROOT=/home/ubuntu/dazzlingPlatinum
cd "$ROOT"

SOURCE=src/battle/battle_display.c
BACKUP=$(mktemp)
BASELINE_DIR=deliverables/affine-pulse-proof/audio-ab-baseline
BASELINE_ROM="$BASELINE_DIR/route206-guaranteed-no-reveal-cry.nds"
ACCEPTED_TEST_ROM=deliverables/live-mega-battle-proof/route206-guaranteed-encounter-test.nds
mkdir -p "$BASELINE_DIR"
cp "$SOURCE" "$BACKUP"
restored=0

restore_source() {
  if [[ "$restored" -eq 0 ]]; then
    cp "$BACKUP" "$SOURCE"
    restored=1
  fi
}
cleanup() {
  restore_source
  rm -f "$BACKUP"
}
trap cleanup EXIT

cry_line='            Sound_PlayPokemonCry(data->species, data->form);'
[[ $(grep -Fxc "$cry_line" "$SOURCE") -eq 1 ]] || {
  echo 'expected exactly one reveal-cry call before baseline build' >&2
  exit 1
}
grep -Fv "$cry_line" "$SOURCE" > "$SOURCE.tmp"
mv "$SOURCE.tmp" "$SOURCE"
[[ $(grep -Fc 'Sound_PlayPokemonCry(data->species, data->form);' "$SOURCE") -eq 0 ]]

ninja -C build > "$BASELINE_DIR/no-cry-production-build.log" 2>&1
python3 tools/build_guaranteed_route206_encounter_rom.py > "$BASELINE_DIR/no-cry-guaranteed-build.json"
cp "$ACCEPTED_TEST_ROM" "$BASELINE_ROM"
sha256sum "$BASELINE_ROM" > "$BASELINE_DIR/no-cry-rom.sha256"

restore_source
ninja -C build > "$BASELINE_DIR/restored-production-build.log" 2>&1
python3 tools/build_guaranteed_route206_encounter_rom.py > "$BASELINE_DIR/restored-cry-guaranteed-build.json"
[[ $(grep -Fxc "$cry_line" "$SOURCE") -eq 1 ]]
sha256sum build/pokeplatinum.us.nds "$ACCEPTED_TEST_ROM" > "$BASELINE_DIR/restored-roms.sha256"

echo "baseline_rom=$BASELINE_ROM"
echo "accepted_test_rom=$ACCEPTED_TEST_ROM"
echo 'source_restored=true'
