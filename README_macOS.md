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
| Fast-forward: hold for up to 4x (`SIM_FAST_FORWARD_SPEED=<1.5–16>` changes it) | Space |
| Frame cap on/off (uncapped) | Tab |
| Settings and debug menu | ` (grave accent) |
| Export the save (.sav) | Cmd+E (or Export save… in the ` menu) |
| Import a save (.sav or DeSmuME .dsv), then restart | Cmd+I (or Import save… in the ` menu) |
| Quit | Cmd+Q |

While fast-forwarding, a badge in the top-right corner shows the speed (`MAX` when the frame cap is off).

**Saves.** The game keeps its save in `~/Library/Application Support/Pokemon Platinum/save.bin`, a raw image of the cartridge's
512 KB flash: the same format as a `.sav` from DeSmuME (File > Export/Import Backup Memory), melonDS or a cartridge dump, so an
exported save opens in those emulators and theirs open here. Import also reads DeSmuME/OpenEmu `.dsv` files (OpenEmu keeps them in
`~/Library/Application Support/OpenEmu/DeSmuME/Battery Saves`). Before an import the current save is copied to `save-backups/` in
that folder; the game restarts to load the imported one.

A game controller is supported by the port (not tested on macOS yet).

## What the macOS target changes

- `meson/native_macos_port.ini`, `meson/cross_pcport_macos.ini`: the port builds natively with clang, configured as the `linux`
  target plus `SDK_BUILD_MACOS` (the host machine says x86_64 only to satisfy meson's nasm check, as the NX build does).
- `tools/macos/trainer_ai_macho.sh`: Apple's assembler cannot fold the trainer AI script's label arithmetic; it is assembled as ELF
  with arm-none-eabi-as and its bytes wrapped in a Mach-O object.
- `lib/ppwlobby`: libc++ needs `const` map keys in allocators and allocator equality; pointer-to-`u32` casts go through `uintptr_t`;
  C++14 on macOS.
- `tools/nitroarc`, `tools/scripts/copy_pc_files.sh`: clang warning order; macOS `cp` has no `-u`.
- `tools/macos/gen_order.py` + `-order_file` link flag (meson.build): the simulator's hardware registers and memory
  (libntr `sim_vars.c`) are laid out in definition order, as GNU ld does. Apple's ld sorted them by name, which broke every
  32-bit store the SDK makes across two 16-bit registers: `G2_SetBlendAlpha` writes BLDCNT and BLDALPHA together, so the alpha
  blend coefficients were lost and blended graphics drew black (the ESRB/copyright text, the Game Freak logo, the intro's
  forest fade). The fog density table read and other multi-register accesses depend on it too.
- `tools/macos/patches/*.patch` (applied by `build.sh` to the subprojects, pinned in `REVISIONS`):
  - libntr: OpenGL 4.1 core (macOS's maximum): context version, `#version 410` shaders, no KHR_debug; the four palette RAM
    arrays in one struct (HW_PLTT spans BG+OBJ palettes and relied on GNU ld keeping them adjacent; with Apple's ld a palette clear
    wiped the heap table); `HW_DB_BG_VRAM_SIZE` / `HW_DB_OBJ_VRAM_END` sized to their arrays; X/Y/debug buttons set released after
    `HW_MAIN_MEM_SYSTEM` is cleared (they read as held, so the first X press did nothing); no empty placeholder archives.
    Renderer fixes (not macOS-specific): translucent 3D draw calls, deferred to the end of the frame, now apply their own
    cull mode and depth test (they inherited the frame's last state, usually cull-all, so particles such as the title glows,
    Chimchar's flames and Turtwig's leaves were never drawn) and leave the depth buffer alone like the DS; translucent 3D pixels
    blend with a 2nd-target layer below whatever BLDCNT's mode is (the DS's 3D special case); the backdrop colour uniform is set
    with `glUniform4fv`; frame pacing sleeps in ≤2 ms slices against a running deadline (macOS timer coalescing held a
    background window at ~26 fps) and Space fast-forwards at up to 4x instead of uncapped.
  - libntrwifi: no `SOCK_NONBLOCK` on macOS (`fcntl(O_NONBLOCK)`).
  - libntrdwc: no `wctype_t` typedef on macOS.
- Debug automation (any PC build, off unless set): `SIM_DEBUG_KEYS="<frame>:<keys>[/<hold>],…"` (keys `A B X Y L R START SELECT UP
  DOWN LEFT RIGHT`, `T<x>;<y>` touches the bottom screen), `SIM_DEBUG_SHOT_DIR` + `SIM_DEBUG_SHOT_EVERY` (BMP screenshots),
  `SIM_DEBUG_EXIT_FRAME` (also prints the fps since frame 100), `SIM_DEBUG_FAST=1` (no frame cap), `SIM_DEBUG_FF_HOLD=1` (as if
  Space were held), `SIM_DEBUG_DUMP_FRAME=<n>` (2D display/blend registers and BG palette).

## Tested (M-series Mac, macOS 27)

Boot, intro, title, new game (Rowan's touch-screen tutorial, naming), overworld (Twinleaf, houses, Route 201) with movement and
events, start menu, saving and Continue, the starter briefcase and the first rival battle (moves, animations, touch-screen menus).
Save import/export checked both ways with DeSmuME (an exported save loads in DeSmuME; a DeSmuME .dsv loads here).
Not yet tested: audio by ear, a controller, Wi-Fi features, long play sessions.
