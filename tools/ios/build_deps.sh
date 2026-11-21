#!/bin/bash
# Build the iOS static deps (SDL3, zlib, libpng, enet) for one SDK into
# ~/Documents/pokeplatinum-ios-deps/<sdk> (override with IOS_DEPS_ROOT).
#   tools/ios/build_deps.sh [iphoneos|iphonesimulator] [...]
# SDL3 matches the Mac build's version: Homebrew's sdl3 when present, else 3.4.16.
set -euo pipefail
# Meta devservers reach GitHub only through fwdproxy; a laptop goes direct
if [ -z "${https_proxy:-}" ] && host fwdproxy >/dev/null 2>&1; then export https_proxy=http://fwdproxy:8080 http_proxy=http://fwdproxy:8080; fi
DEPS_ROOT=${IOS_DEPS_ROOT:-$HOME/Documents/pokeplatinum-ios-deps}
SRC=$DEPS_ROOT/src
MIN=${IOS_MIN_VERSION:-17.0}
mkdir -p "$SRC"

SDL_VER=${SDL_VER:-$(brew list --versions sdl3 2>/dev/null | awk '{print $2}' || true)}
SDL_VER=${SDL_VER:-3.4.16}
[ -d "$SRC/SDL" ] || git clone -q --depth 1 -b "release-$SDL_VER" https://github.com/libsdl-org/SDL.git "$SRC/SDL"
[ -d "$SRC/zlib" ] || git clone -q --depth 1 -b v1.3.1 https://github.com/madler/zlib.git "$SRC/zlib"
[ -d "$SRC/libpng" ] || git clone -q --depth 1 -b libpng16 https://github.com/glennrp/libpng.git "$SRC/libpng"
[ -d "$SRC/enet" ] || git clone -q --depth 1 https://github.com/lsalzman/enet.git "$SRC/enet"

build_sdk() {
  sdk=$1; prefix=$DEPS_ROOT/$sdk
  mkdir -p "$prefix/lib" "$prefix/include"
  target=arm64-apple-ios$MIN; [ "$sdk" = iphonesimulator ] && target=arm64-apple-ios$MIN-simulator
  sysroot=$(xcrun --sdk "$sdk" --show-sdk-path)
  cm=(-DCMAKE_SYSTEM_NAME=iOS -DCMAKE_OSX_SYSROOT="$sdk" -DCMAKE_OSX_ARCHITECTURES=arm64
      -DCMAKE_OSX_DEPLOYMENT_TARGET=$MIN -DCMAKE_INSTALL_PREFIX="$prefix"
      -DCMAKE_BUILD_TYPE=Release -G Ninja)

  if [ ! -f "$prefix/lib/libz.a" ]; then
    cmake -S "$SRC/zlib" -B "$SRC/build-zlib-$sdk" "${cm[@]}" -DBUILD_SHARED_LIBS=OFF >/dev/null
    cmake --build "$SRC/build-zlib-$sdk" -j8 >/dev/null && cmake --install "$SRC/build-zlib-$sdk" >/dev/null
  fi
  if [ ! -f "$prefix/lib/libpng.a" ]; then
    cmake -S "$SRC/libpng" -B "$SRC/build-png-$sdk" "${cm[@]}" -DPNG_SHARED=OFF -DPNG_STATIC=ON \
      -DPNG_TESTS=OFF -DZLIB_ROOT="$prefix" -DZLIB_LIBRARY="$prefix/lib/libz.a" -DZLIB_INCLUDE_DIR="$prefix/include" >/dev/null
    cmake --build "$SRC/build-png-$sdk" -j8 >/dev/null && cmake --install "$SRC/build-png-$sdk" >/dev/null
    ln -sf libpng16.a "$prefix/lib/libpng.a" 2>/dev/null || cp "$prefix/lib/libpng16.a" "$prefix/lib/libpng.a"
  fi
  if [ ! -f "$prefix/lib/libSDL3.a" ]; then
    cmake -S "$SRC/SDL" -B "$SRC/build-sdl-$sdk" "${cm[@]}" -DSDL_SHARED=OFF -DSDL_STATIC=ON \
      -DSDL_TEST_LIBRARY=OFF -DSDL_TESTS=OFF -DSDL_EXAMPLES=OFF -DSDL_INSTALL_TESTS=OFF >/dev/null
    cmake --build "$SRC/build-sdl-$sdk" -j8 >/dev/null && cmake --install "$SRC/build-sdl-$sdk" >/dev/null
  fi
  if [ ! -f "$prefix/lib/libenet.a" ]; then
    objs=""
    for f in callbacks compress host list packet peer protocol unix; do
      clang -target $target -isysroot "$sysroot" -O2 -c -I"$SRC/enet/include" \
        -DHAS_SOCKLEN_T=1 -DHAS_FCNTL=1 -DHAS_POLL=1 -DHAS_GETADDRINFO=1 -DHAS_GETNAMEINFO=1 -DHAS_MSGHDR_FLAGS=1 \
        "$SRC/enet/$f.c" -o "$SRC/enet-$sdk-$f.o"
      objs="$objs $SRC/enet-$sdk-$f.o"
    done
    ar rcs "$prefix/lib/libenet.a" $objs
    cp -R "$SRC/enet/include/enet" "$prefix/include/"
  fi
  echo "deps ready: $prefix (SDL $SDL_VER)"
}

for sdk in "${@:-iphoneos iphonesimulator}"; do build_sdk "$sdk"; done
