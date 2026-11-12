#!/bin/bash
# Prepare an Ubuntu 24.04 container for the SDL GPU migration work (docs/sdl_gpu_migration/PLAN.md):
# toolchain, software OpenGL/Vulkan drivers, shader compilers, SDL3 from source, the subprojects at their pinned
# revisions with the project patches applied, and a local git baseline inside subprojects/libntr.
#   tools/sdl_gpu_migration/setup_env.sh
# Safe to run again: every step skips what is already done. Needs root (apt) and network access to
# archive.ubuntu.com and github.com. Afterwards run tools/sdl_gpu_migration/build_linux.sh.
set -euo pipefail
cd "$(dirname "$0")/../.."
ROOT=$PWD
DEPS=${DEPS:-$(dirname "$ROOT")/deps}
SDL_TAG=${SDL_TAG:-release-3.4.20}
MESON="python3 $ROOT/subprojects/meson-1.12.0/meson.py"

# 1. Packages. libsdl2-dev is for the OpenGL reference build, which still uses SDL2 until the SDL3 port is merged.
export DEBIAN_FRONTEND=noninteractive
apt-get update -y >/dev/null
apt-get install -y --no-install-recommends \
  build-essential clang cmake ninja-build nasm pkg-config python3 git ccache gdb xvfb flex bison \
  gcc-arm-none-eabi binutils-arm-none-eabi libpng-dev libenet-dev libglew-dev libsdl2-dev \
  mesa-vulkan-drivers libvulkan-dev vulkan-tools glslang-tools spirv-cross \
  libgl1-mesa-dri libgl-dev libegl-dev libgles-dev libdrm-dev libgbm-dev \
  libx11-dev libxext-dev libxrandr-dev libxcursor-dev libxi-dev libxfixes-dev libxss-dev libxtst-dev \
  libxinerama-dev libxkbcommon-dev libwayland-dev libasound2-dev libpulse-dev libudev-dev libdbus-1-dev >/dev/null
echo "packages installed"

# 2. SDL3 (Ubuntu 24.04 has no SDL3 package). Installed to $DEPS/prefix; pkg-config name sdl3.
if [ ! -f "$DEPS/prefix/lib/libSDL3.so" ]; then
  mkdir -p "$DEPS"
  [ -d "$DEPS/SDL" ] || git clone -q --depth 1 -b "$SDL_TAG" https://github.com/libsdl-org/SDL.git "$DEPS/SDL"
  cmake -S "$DEPS/SDL" -B "$DEPS/SDL/build" -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_INSTALL_PREFIX="$DEPS/prefix" -DSDL_SHARED=ON -DSDL_STATIC=OFF -DSDL_TESTS=OFF -DSDL_EXAMPLES=OFF \
    -DSDL_VULKAN=ON -DSDL_OPENGL=ON -DSDL_X11=ON -DSDL_WAYLAND=OFF -DSDL_DUMMYVIDEO=ON -DSDL_OFFSCREEN=ON >/dev/null
  ninja -C "$DEPS/SDL/build" >/dev/null
  ninja -C "$DEPS/SDL/build" install >/dev/null
fi
echo "SDL3: $(PKG_CONFIG_PATH=$DEPS/prefix/lib/pkgconfig pkg-config --modversion sdl3) in $DEPS/prefix"

# 3. Meson and the subprojects.
[ -d subprojects/meson-1.12.0 ] || git clone -q --depth=1 -b 1.12.0 https://github.com/mesonbuild/meson subprojects/meson-1.12.0
# wrapdb.mesonbuild.com is not reachable from the cloud containers; the same patch archive is a GitHub release asset.
mkdir -p subprojects/packagecache
if [ ! -f subprojects/packagecache/yyjson_0.12.0-1_patch.zip ]; then
  curl -sSL -o subprojects/packagecache/yyjson_0.12.0-1_patch.zip \
    https://github.com/mesonbuild/wrapdb/releases/download/yyjson_0.12.0-1/yyjson_0.12.0-1_patch.zip
fi
$MESON subprojects download >/dev/null

# 4. Pin the simulator subprojects and apply the project patches (the same steps as tools/macos/build.sh).
while read -r name rev; do
  [ -n "$name" ] || continue
  d=subprojects/$name
  if [ "$(git -C "$d" rev-parse HEAD)" != "$rev" ] && ! git -C "$d" merge-base --is-ancestor "$rev" HEAD 2>/dev/null; then
    git -C "$d" fetch -q --depth 1 origin "$rev" && git -C "$d" checkout -q "$rev"
  fi
  if git -C "$d" apply --check "$ROOT/tools/macos/patches/$name.patch" 2>/dev/null; then
    git -C "$d" apply "$ROOT/tools/macos/patches/$name.patch"
    echo "patched $name"
  fi
done < tools/macos/patches/REVISIONS

# 5. A local baseline commit in libntr (branch "dazzling" = upstream + tools/macos/patches/libntr.patch), so
# workstreams can branch, commit and diff inside the simulator. The outer repo ignores subprojects/libntr.
if ! git -C subprojects/libntr rev-parse -q --verify dazzling >/dev/null; then
  git -C subprojects/libntr checkout -q -b dazzling
  git -C subprojects/libntr add -A
  git -C subprojects/libntr -c user.name=dazzling -c user.email=dazzling@localhost commit -q \
    -m "Dazzling patch baseline (tools/macos/patches/libntr.patch on the pinned revision)"
fi
echo "libntr baseline: $(git -C subprojects/libntr log --oneline -1 dazzling)"
echo "Vulkan driver: $(vulkaninfo --summary 2>/dev/null | grep -m1 deviceName | sed 's/.*= //')"
echo "setup done; next: tools/sdl_gpu_migration/build_linux.sh"
