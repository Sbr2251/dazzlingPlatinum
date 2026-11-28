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
  p_macos="tools/macos/patches/$name.patch"
  p_ios="tools/ios/patches/$name.patch"
  if git -C "$d" apply --check "$ROOT/$p_macos" 2>/dev/null; then
    git -C "$d" apply "$ROOT/$p_macos" && echo "patched $name ($p_macos)"
  elif git -C "$d" apply --reverse --check "$ROOT/$p_macos" 2>/dev/null; then
    : # exact current macOS patch already applied
  elif [ -f "$ROOT/$p_ios" ] && git -C "$d" apply --reverse --check "$ROOT/$p_ios" 2>/dev/null; then
    # iOS patch is stacked on top of the macOS patch (e.g. libntrwifi); verify macOS patch underneath
    git -C "$d" apply --reverse "$ROOT/$p_ios"
    rc=0
    git -C "$d" apply --reverse --check "$ROOT/$p_macos" 2>/dev/null || rc=$?
    git -C "$d" apply "$ROOT/$p_ios"
    if [ "$rc" -ne 0 ]; then
      echo "error: $d does not match $p_macos (stale patch or local edits under $p_ios)." >&2
      echo "Refresh $d to pinned rev $rev from tools/macos/patches/REVISIONS (back up local edits first):" >&2
      echo "  rm -rf $d" >&2
      echo "  # or: git -C $d fetch origin $rev && git -C $d checkout -f $rev && git -C $d clean -fd" >&2
      exit 1
    fi
  else
    echo "error: $d cannot apply $p_macos and does not already have this exact patch applied." >&2
    echo "Refresh $d to pinned rev $rev from tools/macos/patches/REVISIONS (back up local edits first):" >&2
    echo "  rm -rf $d" >&2
    echo "  # or: git -C $d fetch origin $rev && git -C $d checkout -f $rev && git -C $d clean -fd" >&2
    exit 1
  fi
  if [ -f "$ROOT/$p_ios" ]; then
    if git -C "$d" apply --check "$ROOT/$p_ios" 2>/dev/null; then
      git -C "$d" apply "$ROOT/$p_ios" && echo "patched $name ($p_ios)"
    elif git -C "$d" apply --reverse --check "$ROOT/$p_ios" 2>/dev/null; then
      : # exact current iOS patch already applied
    else
      echo "error: $d cannot apply $p_ios and does not already have this exact patch applied." >&2
      echo "Refresh $d to pinned rev $rev from tools/macos/patches/REVISIONS (back up local edits first):" >&2
      echo "  rm -rf $d" >&2
      echo "  # or: git -C $d fetch origin $rev && git -C $d checkout -f $rev && git -C $d clean -fd" >&2
      exit 1
    fi
  fi
done < tools/macos/patches/REVISIONS

mkdir -p "$BUILD"
printf "[constants]\nroot = '%s'\n" "$ROOT" > "$BUILD/root.ini"
SDK_PATH=$(xcrun --sdk "$SDK" --show-sdk-path)
sed -e "s|@IOS_SDK_PATH@|$SDK_PATH|g" -e "s|@IOS_DEPS_PREFIX@|$DEPS|g" -e "s|@IOS_MIN_VERSION@|$MIN|g" \
  "$TEMPLATE" > "$BUILD/cross_ios.ini"

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
