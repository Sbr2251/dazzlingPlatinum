#!/bin/bash
# One-time devserver setup for the SDL GPU migration (integrator; needs sudo for dnf).
# Installs lavapipe (Vulkan on the CPU), the Vulkan loader and shader tools, and builds SDL 3.4.16 and spirv-cross
# from source into /data/repos/dp-wt/sdl3-deps/prefix. Safe to run again: finished steps are skipped.
# Run on devvm37887 2026-11-11 (SDL needs the X11 headers even for offscreen builds).
set -euo pipefail
DEPS=/data/repos/dp-wt/sdl3-deps
SDL_TAG=${SDL_TAG:-release-3.4.16}
mkdir -p "$DEPS"
sudo dnf install -y mesa-vulkan-drivers vulkan-loader vulkan-loader-devel vulkan-tools glslang spirv-tools cmake ninja-build \
  libX11-devel libXext-devel libXrandr-devel libXcursor-devel libXi-devel libXfixes-devel libXScrnSaver-devel libXtst-devel \
  libxkbcommon-devel alsa-lib-devel pulseaudio-libs-devel
if [ ! -f "$DEPS/prefix/lib64/libSDL3.so" ] && [ ! -f "$DEPS/prefix/lib/libSDL3.so" ]; then
  [ -d "$DEPS/SDL" ] || git clone -q --depth 1 -b "$SDL_TAG" https://github.com/libsdl-org/SDL.git "$DEPS/SDL"
  cmake -S "$DEPS/SDL" -B "$DEPS/SDL/build" -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_INSTALL_PREFIX="$DEPS/prefix" -DSDL_SHARED=ON -DSDL_STATIC=OFF -DSDL_TESTS=OFF -DSDL_EXAMPLES=OFF \
    -DSDL_VULKAN=ON -DSDL_OPENGL=ON -DSDL_X11=ON -DSDL_WAYLAND=OFF -DSDL_DUMMYVIDEO=ON -DSDL_OFFSCREEN=ON
  nice ninja -C "$DEPS/SDL/build" -j32 && ninja -C "$DEPS/SDL/build" install
fi
if [ ! -x "$DEPS/prefix/bin/spirv-cross" ]; then
  [ -d "$DEPS/SPIRV-Cross" ] || git clone -q --depth 1 https://github.com/KhronosGroup/SPIRV-Cross.git "$DEPS/SPIRV-Cross"
  cmake -S "$DEPS/SPIRV-Cross" -B "$DEPS/SPIRV-Cross/build" -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$DEPS/prefix" -DSPIRV_CROSS_ENABLE_TESTS=OFF
  nice ninja -C "$DEPS/SPIRV-Cross/build" -j32 && ninja -C "$DEPS/SPIRV-Cross/build" install
fi
PKG_CONFIG_PATH="$DEPS/prefix/lib64/pkgconfig:$DEPS/prefix/lib/pkgconfig" pkg-config --modversion sdl3
which glslangValidator && "$DEPS/prefix/bin/spirv-cross" --help >/dev/null 2>&1 && echo "spirv-cross ok"
VK_ICD_FILENAMES=$(ls /usr/share/vulkan/icd.d/lvp_icd*.json | head -1) vulkaninfo --summary | grep -i 'deviceName' || true
