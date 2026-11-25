# Installation & Build Guide (macOS & iOS)

Dazzling Platinum builds natively as a macOS (Apple Silicon) app and an iOS (arm64) app using SDL3 + Metal. No external ROM is required — all game assets are compiled directly from this repository.

## macOS (Apple Silicon)

### 1. Prerequisites

Install Xcode Command Line Tools and Homebrew packages:

```sh
xcode-select --install
brew install sdl3 nasm ninja arm-none-eabi-gcc gcc@14 libpng pkg-config python3
```

(`arm-none-eabi-gcc` is used only by the build-time bytecode assemblers for field scripts, battle scripts, move animations, and trainer AI.)

### 2. Build & Run

```sh
# Release build (optimized, recommended for playing)
tools/macos/build.sh release
open "build_macos_release/Dazzling Platinum.app"

# Developer build (asserts & debug tools enabled)
tools/macos/build.sh dev
open "build_macos/Dazzling Platinum.app"

# AddressSanitizer + UBSan build
tools/macos/build.sh asan
```

You can also use the `Makefile` shortcuts (`make macos`, `make macos-release`, `make macos-asan`).

### 3. Incremental Rebuilds

After editing source files, rebuild quickly with `ninja`:

```sh
DEPS=../pokeplatinum-macos-deps
LIBRARY_PATH="/opt/homebrew/lib:$DEPS/prefix/lib" \
CPATH="/opt/homebrew/include:$DEPS/prefix/include" \
ninja -j8 -C build_macos_release
```

### 4. Installing to `~/Applications`

```sh
rm -rf "$HOME/Applications/Dazzling Platinum.app"
ditto "build_macos_release/Dazzling Platinum.app" "$HOME/Applications/Dazzling Platinum.app"
open "$HOME/Applications/Dazzling Platinum.app"
```

---

## iOS (iPhone, Landscape, Metal)

### 1. Prerequisites

- Full Xcode installation (with iOS SDK + Simulator runtime)
- The macOS Homebrew prerequisites above (`ninja`, `pkg-config`, `arm-none-eabi-gcc`, `python3`, `cmake`)

### 2. Build

```sh
# iOS Simulator bundle (ad-hoc signed)
tools/ios/build.sh sim

# iPhone device bundle + unsigned .ipa for Sideloadly
tools/ios/build.sh device
```

The first iOS build automatically builds static dependencies (SDL3, zlib, libpng, enet) into `~/Documents/pokeplatinum-ios-deps/`. See [`docs/ios.md`](docs/ios.md) for Simulator launch (`tools/ios/sim_run.sh`) and Sideloadly sideloading instructions.

---

## Verification

```sh
# Static content checks (scripts, text labels, JSON data, apostrophes)
python3 tools/dazzling/test/static_checks.py

# Headless lockstep scenario & visual regression suite
python3 tools/dazzling/test/run.py -j 2
```
