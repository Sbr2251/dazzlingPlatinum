#!/bin/bash
# iOS: wrap the built game in "Dazzling Platinum.app" (flat iOS bundle: executable +
# Info.plist + Resources/game with the game files exactly as the macOS app lays them
# out). Simulator builds are ad-hoc signed; device builds are left unsigned (the
# owner signs the .ipa from make_ipa.sh with Sideloadly).
# usage: make_app.sh <build dir> [device|sim]
set -euo pipefail
BUILDDIR=$(cd "$1" && pwd)
KIND=${2:-device}
ROOT=$(cd "$BUILDDIR/.." && pwd)
APP="$BUILDDIR/Dazzling Platinum.app"
CSV="$ROOT/platinum.us/filesys.csv"

rm -rf "$APP.tmp"
mkdir -p "$APP.tmp/Resources/game"
A="$APP.tmp"

# The game files, exactly as copy_pc_files.sh placed them (filesys.csv targets)
grep -v '^#' "$CSV" | grep -v '^Source File' | grep -v '^[[:space:]]*$' | cut -d, -f2 | while read -r dest; do
  dest=${dest%$'\r'}
  mkdir -p "$(dirname "$A/Resources/game$dest")"
  cp "$BUILDDIR$dest" "$A/Resources/game$dest"
done
for f in header.bin firmware.bin language.csv; do cp "$BUILDDIR/$f" "$A/Resources/game/$f"; done
[ -d "$BUILDDIR/battle_specs" ] && cp -R "$BUILDDIR/battle_specs" "$A/Resources/game/battle_specs"
[ -d "$ROOT/tools/texpack/demo/TexturePack" ] && cp -R "$ROOT/tools/texpack/demo/TexturePack" "$A/Resources/game/TexturePack"

cp "$BUILDDIR/main" "$A/DazzlingPlatinum"
chmod +x "$A/DazzlingPlatinum"
cp "$ROOT/tools/ios/Info.plist" "$A/Info.plist"

# Launch screen (compiled) and app icon PNGs from the Mac/Linux app icon
if command -v ibtool >/dev/null; then
  ibtool --errors --warnings --notices --module DazzlingPlatinum --target-device iphone --target-device ipad \
    --minimum-deployment-target 17.0 --output-format human-readable-text \
    --compile "$A/LaunchScreen.storyboardc" "$ROOT/tools/ios/LaunchScreen.storyboard" >/dev/null
fi
icon_png="$ROOT/tools/linuxdeploy/app.png"
if [ -f "$icon_png" ]; then
  for s in 40 58 60 80 87 120 180 1024; do
    sips -z $s $s "$icon_png" --out "$A/AppIcon$s.png" >/dev/null 2>&1 || true
  done
fi

if [ "$KIND" = sim ]; then
  codesign --force --sign - --timestamp=none "$A/DazzlingPlatinum" >/dev/null 2>&1 || true
  codesign --force --sign - --timestamp=none "$APP.tmp" >/dev/null 2>&1 || true
fi

rm -rf "$APP"
mv "$APP.tmp" "$APP"
echo "app: $APP"
