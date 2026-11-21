#!/bin/bash
# Build the iOS port (device or Simulator) from this tree, mirroring tools/macos/build.sh:
# iOS deps, subprojects at the pinned revisions (macOS patches, then iOS patches),
# host tools on the Mac, the game cross-compiled, packaged by tools/ios/make_app.sh.
#   tools/ios/build.sh [device|sim] [--dev] # release by default; --dev opts into a developer build
# Needs: Xcode, Homebrew ninja/pkg-config/arm-none-eabi-gcc, python3. Device output
# also gets an unsigned .ipa (tools/ios/make_ipa.sh) for Sideloadly.
set -euo pipefail
cd "$(dirname "$0")/../.."
ROOT=$PWD
KIND=device
BUILD_VARIANT=${BUILD_VARIANT:-release}
for arg in "$@"; do
  case "$arg" in
    device|sim) KIND=$arg ;;
    --dev) BUILD_VARIANT=dev ;;
    --release) BUILD_VARIANT=release ;;
    *) echo "usage: $0 [device|sim] [--dev|--release]" >&2; exit 2 ;;
  esac
done
case "$KIND" in
  device) BUILD=${BUILD:-build_ios};     SDK=iphoneos;        TEMPLATE=meson/cross_pcport_ios.ini ;;
  sim)    BUILD=${BUILD:-build_ios_sim}; SDK=iphonesimulator; TEMPLATE=meson/cross_pcport_ios_sim.ini ;;
esac
DEPS_ROOT=${IOS_DEPS_ROOT:-$HOME/Documents/pokeplatinum-ios-deps}
DEPS=$DEPS_ROOT/$SDK
MIN=${IOS_MIN_VERSION:-17.0}
# Target triple for tools/ios/trainer_ai_ios.sh (device vs simulator object format)
if [ "$KIND" = sim ]; then export SIM_IOS_TARGET="arm64-apple-ios$MIN-simulator"; else export SIM_IOS_TARGET="arm64-apple-ios$MIN"; fi
MESON="python3 $ROOT/subprojects/meson-1.12.0/meson.py"

[ -d subprojects/meson-1.12.0 ] || git clone -q --depth=1 -b 1.12.0 https://github.com/mesonbuild/meson subprojects/meson-1.12.0
[ -f "$DEPS/lib/libSDL3.a" ] || tools/ios/build_deps.sh "$SDK"

# Subprojects at the patched revisions; macOS patches first, then the iOS ones
$MESON subprojects download >/dev/null 2>&1 || true # ios-build hook: offline trees ship the subprojects in place
while read -r name rev; do
  [ -n "$name" ] || continue
  d=subprojects/$name
  [ -d "$d/.git" ] || continue # ios-build hook: shipped tree without git; patches were applied before shipping
  if [ "$(git -C "$d" rev-parse HEAD)" != "$rev" ] && ! git -C "$d" merge-base --is-ancestor "$rev" HEAD 2>/dev/null; then
    git -C "$d" fetch -q --depth 1 origin "$rev" && git -C "$d" checkout -q "$rev"
  fi
  for p in "tools/macos/patches/$name.patch" "tools/ios/patches/$name.patch"; do
    if [ -f "$p" ] && git -C "$d" apply --check "$ROOT/$p" 2>/dev/null; then
      git -C "$d" apply "$ROOT/$p" && echo "patched $name ($p)"
    fi
  done
done < tools/macos/patches/REVISIONS

mkdir -p "$BUILD"
printf "[constants]\nroot = '%s'\n" "$ROOT" > "$BUILD/root.ini"
SDK_PATH=$(xcrun --sdk "$SDK" --show-sdk-path)
sed -e "s|@IOS_SDK_PATH@|$SDK_PATH|g" -e "s|@IOS_DEPS_PREFIX@|$DEPS|g" -e "s|@IOS_MIN_VERSION@|$MIN|g" \
  "$TEMPLATE" > "$BUILD/cross_ios.ini"

python3 tools/scripts/lsfgen.py platinum.us/main.lsf.in --prefix-dir main.nef.p/ --dest-lsf platinum.us/main.lsf --dest-c src/meson.build
if [ ! -f "$BUILD/build.ninja" ]; then
  # meson does not inherit PKG_CONFIG_PATH for the build machine; bake it into a
  # generated native file (with meson/native_ios_host.ini as the base).
  NATIVE=$BUILD/native_ios_host.ini
  cat meson/native_ios_host.ini > "$NATIVE"
  if [ -n "${PKG_CONFIG_PATH:-}" ]; then
    sed -i '' "s|\[built-in options\]|[built-in options]\npkg_config_path = ['$PKG_CONFIG_PATH']|" "$NATIVE"
  fi
  $MESON setup -Dbuild_target=ios -Dbuild_variant="$BUILD_VARIANT" \
    --native-file="$NATIVE" --native-file="$BUILD/root.ini" \
    --cross-file="$BUILD/cross_ios.ini" --cross-file="$BUILD/root.ini" -- "$BUILD"
else
  $MESON configure "$BUILD" -Dbuild_variant="$BUILD_VARIANT"
fi
ninja -j8 -C "$BUILD"
tools/ios/make_app.sh "$BUILD" "$KIND"
[ "$KIND" = device ] && tools/ios/make_ipa.sh "$BUILD"
ls -d "$BUILD/Dazzling Platinum.app"
