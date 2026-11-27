#!/bin/bash
# iOS: wrap the built game in "Dazzling Platinum.app" (flat iOS bundle: executable +
# Info.plist + game/ with the game files exactly as the macOS app lays them
# out under Resources/game; flat here because iOS bundles reject a Resources dir). Simulator builds are ad-hoc signed; device builds are left unsigned (the
# owner signs the .ipa from make_ipa.sh with Sideloadly).
# usage: make_app.sh <build dir> [device|sim]
set -euo pipefail
BUILDDIR=$(cd "$1" && pwd)
KIND=${2:-device}
ROOT=$(cd "$BUILDDIR/.." && pwd)
APP="$BUILDDIR/Dazzling Platinum.app"
CSV="$ROOT/platinum.us/filesys.csv"

rm -rf "$APP.tmp"
mkdir -p "$APP.tmp/game"
A="$APP.tmp"

# The game files, exactly as copy_pc_files.sh placed them (filesys.csv targets)
grep -v '^#' "$CSV" | grep -v '^Source File' | grep -v '^[[:space:]]*$' | cut -d, -f2 | while read -r dest; do
  dest=${dest%$'\r'}
  mkdir -p "$(dirname "$A/game$dest")"
  cp "$BUILDDIR$dest" "$A/game$dest"
done
for f in header.bin firmware.bin language.csv; do cp "$BUILDDIR/$f" "$A/game/$f"; done
[ -d "$BUILDDIR/battle_specs" ] && cp -R "$BUILDDIR/battle_specs" "$A/game/battle_specs"
[ -d "$ROOT/tools/texpack/demo/TexturePack" ] && cp -R "$ROOT/tools/texpack/demo/TexturePack" "$A/game/TexturePack"
[ -d "$ROOT/res/battle3d" ] && cp -R "$ROOT/res/battle3d" "$A/game/battle3d"
[ -d "$ROOT/res/hudhd" ] && cp -R "$ROOT/res/hudhd" "$A/game/hudhd"
# Following Pokemon archive (optional; built from user HGSS ROM + Gen 5 icons)
if [ -f "$ROOT/tools/follow_mon/build_follow_mon.py" ]; then
  python3 "$ROOT/tools/follow_mon/build_follow_mon.py" --optional --if-stale --out "$BUILDDIR/follow_mon.narc"
fi
if [ -f "$BUILDDIR/follow_mon.narc" ]; then
  cp "$BUILDDIR/follow_mon.narc" "$A/game/follow_mon.narc"
fi

cp "$BUILDDIR/main" "$A/DazzlingPlatinum"
chmod +x "$A/DazzlingPlatinum"
cp "$ROOT/tools/ios/Info.plist" "$A/Info.plist"

# Launch screen (compiled) and the app icon asset catalog from the app icon
if command -v ibtool >/dev/null; then
  ibtool --errors --warnings --notices --module DazzlingPlatinum --target-device iphone --target-device ipad \
    --minimum-deployment-target 17.0 --output-format human-readable-text \
    --compile "$A/LaunchScreen.storyboardc" "$ROOT/tools/ios/LaunchScreen.storyboard" >/dev/null
fi
icon_png="$ROOT/tools/macos/app.png"
if [ -f "$icon_png" ] && command -v actool >/dev/null; then
  xc="$BUILDDIR/Assets.xcassets"; rm -rf "$xc"; cp -R "$ROOT/tools/ios/Assets.xcassets" "$xc"
  sips -z 1024 1024 "$icon_png" --out "$xc/AppIcon.appiconset/icon1024.png" >/dev/null 2>&1 || true
  plat=iphonesimulator; [ "$KIND" = device ] && plat=iphoneos
  actool "$xc" --compile "$A" --platform $plat --minimum-deployment-target 17.0 \
    --app-icon AppIcon --output-partial-info-plist "$BUILDDIR/asset-info.plist" >/dev/null 2>&1 || true
  rm -rf "$xc"
fi

if [ "$KIND" = sim ]; then
  codesign --force --sign - --timestamp=none "$A/DazzlingPlatinum" >/dev/null 2>&1 || true
  codesign --force --sign - --timestamp=none "$APP.tmp" >/dev/null 2>&1 || true
fi

rm -rf "$APP"
mv "$APP.tmp" "$APP"
echo "app: $APP"
