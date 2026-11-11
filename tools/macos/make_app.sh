#!/bin/bash
# macOS: wrap the built game in "Dazzling Platinum.app" (called by tools/scripts/copy_pc_files.sh after it has laid the game files out next to main).
# The app holds main, its SDL libraries (Frameworks) and the game files (Resources/game). At launch it runs from
# ~/Library/Application Support/Dazzling Platinum (macOS), where the game files are linked in and its own files go:
# save.bin, sim_config.ini, sim_config_prj.ini, imgui.ini.
# usage: make_app.sh <build dir> <filesys.csv>
set -e
BUILDDIR=$(cd "$1" && pwd)
CSV=$2
APP="$BUILDDIR/Dazzling Platinum.app"
ROOT=$(cd "$BUILDDIR/.." && pwd)

rm -rf "$APP.tmp"
mkdir -p "$APP.tmp/Contents/MacOS" "$APP.tmp/Contents/Frameworks" "$APP.tmp/Contents/Resources/game"
C="$APP.tmp/Contents"

# The game files, exactly as copy_pc_files.sh placed them (filesys.csv targets), and the files it adds
grep -v '^#' "$CSV" | grep -v '^Source File' | grep -v '^[[:space:]]*$' | cut -d, -f2 | while read -r dest; do
  dest=${dest%$'\r'}
  mkdir -p "$(dirname "$C/Resources/game$dest")"
  cp "$BUILDDIR$dest" "$C/Resources/game$dest"
done
for f in header.bin firmware.bin language.csv; do cp "$BUILDDIR/$f" "$C/Resources/game/$f"; done

# The executable and the SDL it links (sdl2-compat over SDL3 from Homebrew), relinked to the bundle's copies
cp "$BUILDDIR/main" "$C/MacOS/pokeplatinum"
sdl2=$(otool -L "$C/MacOS/pokeplatinum" | awk '/libSDL2/ { print $1 }')
if [ -n "$sdl2" ] && [ -f "$sdl2" ]; then
  cp "$sdl2" "$C/Frameworks/libSDL2-2.0.0.dylib"
  install_name_tool -change "$sdl2" "@executable_path/../Frameworks/libSDL2-2.0.0.dylib" "$C/MacOS/pokeplatinum"
  install_name_tool -id "@executable_path/../Frameworks/libSDL2-2.0.0.dylib" "$C/Frameworks/libSDL2-2.0.0.dylib"
  # sdl2-compat loads SDL3 at run time (dlopen), first as @loader_path/libSDL3.dylib: ship it beside it
  sdl3=$(ls /opt/homebrew/opt/sdl3/lib/libSDL3.0.dylib 2>/dev/null || true)
  [ -n "$sdl3" ] && cp -L "$sdl3" "$C/Frameworks/libSDL3.dylib"
fi
chmod u+w "$C/Frameworks/"*.dylib 2>/dev/null || true

# Launcher: run from the per-user data folder with the game files linked in
cat > "$C/MacOS/launch" <<'LAUNCH'
#!/bin/bash
here=$(cd "$(dirname "$0")" && pwd)
game="$here/../Resources/game"
data="$HOME/Library/Application Support/Dazzling Platinum"
mkdir -p "$data"
for f in "$game"/*; do
  n=$(basename "$f")
  # point every game entry at this app's copy (a rebuilt app replaces the old links); the game's own files are left alone
  ln -sfn "$f" "$data/$n"
done
cd "$data"
export DYLD_FALLBACK_LIBRARY_PATH="$here/../Frameworks:${DYLD_FALLBACK_LIBRARY_PATH}"
exec "$here/pokeplatinum" "$@" >> "$data/log.txt" 2>&1
LAUNCH
chmod +x "$C/MacOS/launch"

# Icon (the Linux AppImage's), Info.plist
icon_png="$ROOT/tools/linuxdeploy/app.png"
if [ -f "$icon_png" ]; then
  set_dir="$BUILDDIR/app.iconset"; rm -rf "$set_dir"; mkdir -p "$set_dir"
  for s in 16 32 128 256 512; do
    sips -z $s $s "$icon_png" --out "$set_dir/icon_${s}x${s}.png" >/dev/null 2>&1 || true
    d=$((s * 2)); sips -z $d $d "$icon_png" --out "$set_dir/icon_${s}x${s}@2x.png" >/dev/null 2>&1 || true
  done
  iconutil -c icns "$set_dir" -o "$C/Resources/app.icns" 2>/dev/null || true
  rm -rf "$set_dir"
fi
cat > "$C/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Dazzling Platinum</string>
  <key>CFBundleDisplayName</key><string>Pokémon Dazzling Platinum</string>
  <key>CFBundleIdentifier</key><string>local.dazzlingplatinum.macos</string>
  <key>CFBundleExecutable</key><string>launch</string>
  <key>CFBundleIconFile</key><string>app.icns</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>LSMinimumSystemVersion</key><string>13.0</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSAppSleepDisabled</key><true/>
  <key>LSApplicationCategoryType</key><string>public.app-category.games</string>
</dict>
</plist>
PLIST

# Ad-hoc signature, so Apple silicon runs the relinked binary and libraries
codesign --force --sign - "$C/Frameworks/"*.dylib >/dev/null 2>&1 || true
codesign --force --sign - "$C/MacOS/pokeplatinum" >/dev/null 2>&1 || true
codesign --force --sign - "$APP.tmp" >/dev/null 2>&1 || true

rm -rf "$APP"
mv "$APP.tmp" "$APP"
echo "app: $APP"
