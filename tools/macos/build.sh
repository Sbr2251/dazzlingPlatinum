#!/bin/bash
# Build the macOS (Apple silicon) PC port from a fresh clone: fetch the subprojects, pin them to the revisions the macOS patches
# were made against, apply the patches, build enet, configure, compile, and wrap the result in "Dazzling Platinum.app".
#   tools/macos/build.sh [dev|release|asan]   # dev (default) → build_macos, release → build_macos_release, asan → build_macos_asan
# Needs: Xcode command line tools; Homebrew sdl3, nasm, ninja, arm-none-eabi-gcc, gcc@14, libpng, pkg-config, python3.
# The game's own files are built from this source tree (no ROM needed).
set -euo pipefail
cd "$(dirname "$0")/../.."
ROOT=$PWD
VARIANT=${1:-dev}
case "$VARIANT" in
  dev)     BUILD=${BUILD:-build_macos} ;;
  release) BUILD=${BUILD:-build_macos_release} ;;
  asan)    BUILD=${BUILD:-build_macos_asan} ;;
  *) echo "usage: $0 [dev|release|asan]" >&2; exit 2 ;;
esac
DEPS=${DEPS:-$ROOT/../pokeplatinum-macos-deps}
MESON="python3 $ROOT/subprojects/meson-1.12.0/meson.py"

[ -d subprojects/meson-1.12.0 ] || git clone -q --depth=1 -b 1.12.0 https://github.com/mesonbuild/meson subprojects/meson-1.12.0

# enet (Homebrew's formula may be unavailable): a static build from source
if [ ! -f "$DEPS/prefix/lib/libenet.a" ]; then
  mkdir -p "$DEPS/prefix/lib" "$DEPS/prefix/include"
  [ -d "$DEPS/enet" ] || git clone -q --depth 1 https://github.com/lsalzman/enet.git "$DEPS/enet"
  ( cd "$DEPS/enet" && for f in callbacks compress host list packet peer protocol unix; do
      cc -O2 -c -Iinclude -DHAS_SOCKLEN_T=1 -DHAS_FCNTL=1 -DHAS_POLL=1 -DHAS_GETADDRINFO=1 -DHAS_GETNAMEINFO=1 -DHAS_MSGHDR_FLAGS=1 $f.c -o "$DEPS/$f.o"; done )
  ar rcs "$DEPS/prefix/lib/libenet.a" "$DEPS"/*.o
  cp -R "$DEPS/enet/include/enet" "$DEPS/prefix/include/"
fi

# Subprojects at the patched revisions, patches applied once
$MESON subprojects download >/dev/null
while read -r name rev; do
  [ -n "$name" ] || continue
  d=subprojects/$name
  # Skip the checkout when HEAD already contains the pinned rev (e.g. a team/<agent>
  # branch whose baseline commit includes the patch): resetting it would detach the branch
  if [ "$(git -C "$d" rev-parse HEAD)" != "$rev" ] && ! git -C "$d" merge-base --is-ancestor "$rev" HEAD 2>/dev/null; then
    git -C "$d" fetch -q --depth 1 origin "$rev" && git -C "$d" checkout -q "$rev"
  fi
  p="tools/macos/patches/$name.patch"
  ios_p="tools/ios/patches/$name.patch"
  if git -C "$d" apply --check "$ROOT/$p" 2>/dev/null; then
    git -C "$d" apply "$ROOT/$p"
    echo "patched $name"
  elif git -C "$d" apply --reverse --check "$ROOT/$p" 2>/dev/null; then
    : # exact current patch already applied
  elif [ -f "$ROOT/$ios_p" ] && git -C "$d" apply --reverse --check "$ROOT/$ios_p" 2>/dev/null; then
    # iOS patch is stacked on top of the macOS patch (e.g. libntrwifi); verify macOS patch underneath
    git -C "$d" apply --reverse "$ROOT/$ios_p"
    rc=0
    git -C "$d" apply --reverse --check "$ROOT/$p" 2>/dev/null || rc=$?
    git -C "$d" apply "$ROOT/$ios_p"
    if [ "$rc" -ne 0 ]; then
      echo "error: $d does not match $p (stale patch or local edits under $ios_p)." >&2
      echo "Refresh $d to pinned rev $rev from tools/macos/patches/REVISIONS (back up local edits first):" >&2
      echo "  rm -rf $d" >&2
      echo "  # or: git -C $d fetch origin $rev && git -C $d checkout -f $rev && git -C $d clean -fd" >&2
      exit 1
    fi
  else
    echo "error: $d cannot apply $p and does not already have this exact patch applied." >&2
    echo "Refresh $d to pinned rev $rev from tools/macos/patches/REVISIONS (back up local edits first):" >&2
    echo "  rm -rf $d" >&2
    echo "  # or: git -C $d fetch origin $rev && git -C $d checkout -f $rev && git -C $d clean -fd" >&2
    exit 1
  fi
done < tools/macos/patches/REVISIONS

# The native file names the deps prefix; regenerate it for this checkout
sed -i '' "s|/[^']*/pokeplatinum-macos-deps/prefix|$DEPS/prefix|g" meson/native_macos_port.ini

export LIBRARY_PATH="/opt/homebrew/lib:$DEPS/prefix/lib" CPATH="/opt/homebrew/include:$DEPS/prefix/include"
# A build dir configured before the 'ios' build_target choice existed crashes meson's regenerate
# ("Unhandled python exception" at get_option('build_target')): recreate it once
if [ -f "$BUILD/build.ninja" ] && ! grep -q '"ios"' "$BUILD/meson-info/intro-buildoptions.json" 2>/dev/null; then
  echo "$BUILD predates the iOS build target; recreating it"
  rm -rf "$BUILD"
fi
if [ ! -f "$BUILD/build.ninja" ]; then
  mkdir -p "$BUILD"
  printf "[constants]\nroot = '%s'\n" "$ROOT" > "$BUILD/root.ini"
  $MESON setup -Dbuild_target=linux -Dbuild_variant="$VARIANT" \
    --native-file=meson/native_macos_port.ini --native-file="$BUILD/root.ini" \
    --cross-file=meson/cross_pcport_macos.ini --cross-file="$BUILD/root.ini" -- "$BUILD"
else
  # Keep an existing build dir on the requested variant
  $MESON configure "$BUILD" -Dbuild_variant="$VARIANT"
fi
ninja -j8 -C "$BUILD"
ls -d "$BUILD/Dazzling Platinum.app"
