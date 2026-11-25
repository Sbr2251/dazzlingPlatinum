# Pokémon Dazzling Platinum (macOS & iOS)

Native macOS (Apple Silicon) and iOS SDL3 + Metal port of Pokémon Dazzling Platinum, built directly from source.

## Quick Start

### macOS (Apple Silicon)

```sh
brew install sdl3 nasm ninja arm-none-eabi-gcc gcc@14 libpng pkg-config
tools/macos/build.sh release
open "build_macos_release/Dazzling Platinum.app"
```

See [`INSTALL.md`](INSTALL.md) and [`README_macOS.md`](README_macOS.md) for prerequisites, controls, saves, and headless test automation.

### iOS (iPhone, Landscape, Metal)

```sh
tools/ios/build.sh sim      # iOS Simulator
tools/ios/build.sh device   # Device .app + unsigned .ipa for Sideloadly
```

See [`docs/ios.md`](docs/ios.md) for full iOS build and sideload instructions.

### Static Checks & Headless Scenario Suite

```sh
python3 tools/dazzling/test/static_checks.py
python3 tools/dazzling/test/run.py -j 2
```

See [`CLAUDE.md`](CLAUDE.md) for repository layout and content authoring conventions, and [`CONTRIBUTING.md`](CONTRIBUTING.md) for development guidelines.
