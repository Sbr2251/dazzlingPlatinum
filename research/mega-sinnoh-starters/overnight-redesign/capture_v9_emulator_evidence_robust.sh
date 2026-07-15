#!/usr/bin/env bash
set -euo pipefail
WORK=/home/ubuntu/dazzlingPlatinum/research/mega-sinnoh-starters/overnight-redesign/v9-emulator-evidence
ROMS="$WORK/firstframe-roms"
OUT="$WORK/final-native-captures-robust"
rm -rf "$OUT"
mkdir -p "$OUT"
variants=(
  mega_torterra_front mega_torterra_back
  mega_infernape_front mega_infernape_back
  mega_empoleon_front mega_empoleon_back
)
score_top_screen() {
  convert "$1" -crop 256x192+0+0 -colorspace Gray -threshold 5% -format '%[fx:mean]' info:
}
for name in "${variants[@]}"; do
  accepted=""
  for attempt in 1 2 3; do
    run="$OUT/${name}_attempt${attempt}"
    mkdir -p "$run"
    /usr/games/desmume-cli --disable-sound --nojoy=1 "$ROMS/$name.nds" >"$run/emulator.log" 2>&1 &
    pid=$!
    sleep 3
    win=$(xdotool search --onlyvisible --name 'DeSmuME' | head -1 || true)
    if [[ -z "$win" ]]; then
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
      continue
    fi
    for checkpoint in $(seq 0 18); do
      if ! kill -0 "$pid" 2>/dev/null; then break; fi
      import -window "$win" "$run/window_$(printf '%02d' "$checkpoint").png" || true
      if [[ "$checkpoint" -eq 2 ]]; then
        xdotool key --window "$win" Return || true
      else
        for _ in 1 2 3; do
          xdotool key --window "$win" x || true
          sleep 0.6
        done
        if [[ "$checkpoint" -ge 5 && $((checkpoint % 4)) -eq 1 ]]; then
          xdotool key --window "$win" Return || true
        fi
      fi
      sleep 1.2
    done
    kill "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
    # Choose the latest low-density but nonempty top-screen image. A native
    # sprite on black scores roughly 0.005-0.12; black is 0 and title is high.
    for image in $(find "$run" -name 'window_*.png' | sort -r); do
      checkpoint=$(basename "$image" .png | sed 's/window_//')
      [[ $((10#$checkpoint)) -lt 5 ]] && continue
      score=$(score_top_screen "$image")
      awk -v s="$score" 'BEGIN { exit !(s > 0.002 && s < 0.20) }' || continue
      accepted="$image"
      printf '%s attempt=%s checkpoint=%s score=%s\n' "$name" "$attempt" "$checkpoint" "$score" >> "$OUT/selection.log"
      break
    done
    [[ -n "$accepted" ]] && break
  done
  if [[ -z "$accepted" ]]; then
    printf '%s no-stable-sprite-frame\n' "$name" >> "$OUT/selection.log"
    exit 1
  fi
  cp "$accepted" "$OUT/$name.png"
  sha256sum "$OUT/$name.png" >> "$OUT/checksums.sha256"
done
