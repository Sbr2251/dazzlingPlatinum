# macOS (Apple silicon) build

Private fork of [cybervisi0n/pokeplatinum](https://github.com/cybervisi0n/pokeplatinum) (`pc_port`) with a macOS target.
AI-assisted; not for upstream (that project does not accept AI-written pull requests). Do not publish builds: they contain the game's assets.

## Build

```sh
brew install sdl2-compat nasm ninja arm-none-eabi-gcc gcc@14 libpng pkg-config
tools/macos/build.sh
open "build_macos/Pokemon Platinum.app"
```

The game files are built from this source tree (no ROM needed). The app keeps its own files in
`~/Library/Application Support/Pokemon Platinum`: `save.bin` (your save; compatible with emulators and DS hardware),
`sim_config.ini` (window, scale, keys), `log.txt`.

The DS ROM still builds from the same tree with `make release` as before.

## Controls (defaults, `sim_config.ini`)

| DS | Key |
|---|---|
| D-pad | Arrow keys |
| A / B | Z / X |
| X / Y | C / V |
| L / R | Q / E |
| Start / Select | Return / Right Shift |
| Touch screen | Mouse on the bottom screen |
| Fast-forward (hold / toggle) | Space / Tab |
| Settings and debug menu | ` (grave accent) |

A game controller is supported by the port (not tested on macOS yet).

## What the macOS target changes

- `meson/native_macos_port.ini`, `meson/cross_pcport_macos.ini`: the port builds natively with clang, configured as the `linux`
  target plus `SDK_BUILD_MACOS` (the host machine says x86_64 only to satisfy meson's nasm check, as the NX build does).
- `tools/macos/trainer_ai_macho.sh`: Apple's assembler cannot fold the trainer AI script's label arithmetic; it is assembled as ELF
  with arm-none-eabi-as and its bytes wrapped in a Mach-O object.
- `lib/ppwlobby`: libc++ needs `const` map keys in allocators and allocator equality; pointer-to-`u32` casts go through `uintptr_t`;
  C++14 on macOS.
- `tools/nitroarc`, `tools/scripts/copy_pc_files.sh`: clang warning order; macOS `cp` has no `-u`.
- `tools/macos/patches/*.patch` (applied by `build.sh` to the subprojects, pinned in `REVISIONS`):
  - libntr: OpenGL 4.1 core (macOS's maximum): context version, `#version 410` shaders, no KHR_debug; the four palette RAM
    arrays in one struct (HW_PLTT spans BG+OBJ palettes and relied on GNU ld keeping them adjacent; with Apple's ld a palette clear
    wiped the heap table); `HW_DB_BG_VRAM_SIZE` / `HW_DB_OBJ_VRAM_END` sized to their arrays; X/Y/debug buttons set released after
    `HW_MAIN_MEM_SYSTEM` is cleared (they read as held, so the first X press did nothing); no empty placeholder archives.
  - libntrwifi: no `SOCK_NONBLOCK` on macOS (`fcntl(O_NONBLOCK)`).
  - libntrdwc: no `wctype_t` typedef on macOS.
- Debug automation (any PC build, off unless set): `SIM_DEBUG_KEYS="<frame>:<keys>[/<hold>],…"` (keys `A B X Y L R START SELECT UP
  DOWN LEFT RIGHT`, `T<x>;<y>` touches the bottom screen), `SIM_DEBUG_SHOT_DIR` + `SIM_DEBUG_SHOT_EVERY` (BMP screenshots),
  `SIM_DEBUG_EXIT_FRAME`, `SIM_DEBUG_FAST=1` (no frame cap).

## Tested (M-series Mac, macOS 27)

Boot, intro, title, new game (Rowan's touch-screen tutorial, naming), overworld (Twinleaf, houses, Route 201) with movement and
events, start menu, saving and Continue, the starter briefcase and the first rival battle (moves, animations, touch-screen menus).
Not yet tested: audio by ear, a controller, Wi-Fi features, long play sessions.
