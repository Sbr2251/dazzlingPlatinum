#!/bin/bash
# Build the macOS (Apple silicon) PC port from a fresh clone: fetch the subprojects, pin them to the revisions the macOS patches
# were made against, apply the patches, build enet, configure, compile, and wrap the result in "Dazzling Platinum.app".
#   tools/macos/build.sh            # → build_macos/Dazzling Platinum.app
# Needs: Xcode command line tools; Homebrew sdl2-compat (brings SDL3), nasm, ninja, arm-none-eabi-gcc, gcc@14, libpng, pkg-config, python3.
# The game's own files are built from this source tree (no ROM needed).
set -euo pipefail
cd "$(dirname "$0")/../.."
ROOT=$PWD
BUILD=${BUILD:-build_macos}
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
  if [ "$(git -C "$d" rev-parse HEAD)" != "$rev" ]; then
    git -C "$d" fetch -q --depth 1 origin "$rev" && git -C "$d" checkout -q "$rev"
  fi
  if git -C "$d" apply --check "$ROOT/tools/macos/patches/$name.patch" 2>/dev/null; then
    git -C "$d" apply "$ROOT/tools/macos/patches/$name.patch"
    echo "patched $name"
  fi
done < tools/macos/patches/REVISIONS

# The native file names the deps prefix; regenerate it for this checkout
sed -i '' "s|/[^']*/pokeplatinum-macos-deps/prefix|$DEPS/prefix|g" meson/native_macos_port.ini

export LIBRARY_PATH="/opt/homebrew/lib:$DEPS/prefix/lib" CPATH="/opt/homebrew/include:$DEPS/prefix/include"
if [ ! -f "$BUILD/build.ninja" ]; then
  mkdir -p "$BUILD"
  printf "[constants]\nroot = '%s'\n" "$ROOT" > "$BUILD/root.ini"
  python3 tools/scripts/lsfgen.py platinum.us/main.lsf.in --prefix-dir main.nef.p/ --dest-lsf platinum.us/main.lsf --dest-c src/meson.build
  $MESON setup -Dbuild_target=linux \
    --native-file=meson/native_macos_port.ini --native-file="$BUILD/root.ini" \
    --cross-file=meson/cross_pcport_macos.ini --cross-file="$BUILD/root.ini" -- "$BUILD"
fi
ninja -C "$BUILD"
ls -d "$BUILD/Dazzling Platinum.app"
