#!/bin/bash
# Build the Linux PC port in build_linux (the recipe of the Makefile's "linux" target, without the DS toolchain).
#   tools/sdl_gpu_migration/build_linux.sh [ninja args]
# The first build is about 14,000 steps (35 minutes on 4 cores). Run tools/sdl_gpu_migration/setup_env.sh first.
set -euo pipefail
cd "$(dirname "$0")/../.."
ROOT=$PWD
BUILD=${BUILD:-build_linux}
DEPS=${DEPS:-$(dirname "$ROOT")/deps}
MESON="python3 $ROOT/subprojects/meson-1.12.0/meson.py"
export PKG_CONFIG_PATH="$DEPS/prefix/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
export LD_LIBRARY_PATH="$DEPS/prefix/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
if [ ! -f "$BUILD/build.ninja" ]; then
  mkdir -p "$BUILD"
  printf "[constants]\nroot = '%s'\n" "$ROOT" > "$BUILD/root.ini"
  python3 tools/scripts/lsfgen.py platinum.us/main.lsf.in --prefix-dir main.nef.p/ --dest-lsf platinum.us/main.lsf --dest-c src/meson.build
  $MESON setup -Dbuild_target=linux -Dbuild_variant=dev \
    --native-file=meson/native.ini --native-file="$BUILD/root.ini" \
    --cross-file=meson/cross_pcport_linux.ini --cross-file="$BUILD/root.ini" -- "$BUILD"
fi
ninja -C "$BUILD" "$@"
