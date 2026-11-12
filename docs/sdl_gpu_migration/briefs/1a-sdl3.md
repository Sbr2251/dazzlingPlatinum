# 1a. SDL2 to SDL3 platform port (OpenGL renderer unchanged)

Model: Sonnet. Tree name: `sdl3`. Read `PLAN.md` and `briefs/COMMON.md` first.

## Resume state

Create the tree with the saved work applied:
`tools/sdl_gpu_migration/make_tree.sh sdl3 --libntr docs/sdl_gpu_migration/wip/sdl3-libntr.patch --game docs/sdl_gpu_migration/wip/sdl3-game.patch`

The patches contain a complete first pass: the simulator's 35 SDL-using files converted, `imgui_impl_sdl3` vendored
(`imgui_impl_opengl3` kept), meson on `dependency('sdl3')`, `src/port/sim_icon.cpp`, `src/port/savedata_upgrade.c`,
and the Mac build files. In the previous run this built, linked `libSDL3` and no `libSDL2`, and ran headless. The
integrator checked two lockstep checkpoints (frames 401 and 901 of a fresh boot, both 2D paths): pixels identical to
the SDL2 reference; only the BMP header differs. The first build after applying recompiles the whole game.

Your job is the remaining verification and whatever it turns up (list in "Verification" below).

## Task

Port the platform layer from the SDL2 API to the real SDL3 API (`#include <SDL3/SDL.h>`), keeping the OpenGL
renderer working unchanged. The SDL3 GPU API cannot be mixed with SDL2 headers, so nothing may include SDL2 any
more. After the change the game builds against SDL 3.4.20, still creates its OpenGL context through SDL3, and
behaves exactly as before.

Scope (confirm with grep for `SDL_`, `SDL2/`, `SDLK_`, `KMOD_`):
- `subprojects/libntr`: `libraries/sim/src/*` (window, GL context, events, keyboard, joystick, mouse, audio, threads,
  semaphores, mutexes, timers, message boxes, surfaces and BMP saving, config key names), `libraries/os/src/*` and
  `include/nitro/os/common/*.h`, `libraries/fs`, `libraries/sim7`, `include/simulator/*`.
- `subprojects/libntrwifi` (files under `libraries/soc` and `libraries/cps`).
- Game side: `src/port/*`, `include/port/*`.
- Dear ImGui platform backend: `imgui_impl_sdl2` replaced by `imgui_impl_sdl3` from the upstream ImGui commit that
  matches the vendored version (`IMGUI_VERSION_NUM 19297`). `ImGuiFileDialog` must keep working.
- Build system: SDL3 through `dependency('sdl3')` for the `linux` and `win64` targets. The `nx` and `prospero`
  targets are not supported by this project: keep their meson branches syntactically valid only.
- Mac build files in the outer repo (`tools/macos/build.sh`, `tools/macos/make_app.sh`, `README_macOS.md`,
  `.github/workflows/macos-test.yml`, `meson/native_macos_port.ini`): Homebrew `sdl3` instead of `sdl2-compat`.
  These cannot be built here; say so.

Points that are easy to get wrong:
- Most SDL functions that returned 0 on success now return `bool` (true on success). Audit every comparison of an
  SDL return value.
- Keycodes: user configs (`sim_config.ini`) store key codes; existing configs and the defaults must map to the same
  physical keys. Check the media play key used for pause.
- Audio: `SDL_OpenAudio` with a callback is gone. `sim_audio.cpp` has a lockstep mode in which the callback emits
  silence and the sequencer advances once per rendered frame on the game thread; that must be preserved exactly
  (docs/headless_protocol.md, "Lockstep guarantee").
- High-DPI: the code distinguishes window points from drawable pixels (PostFX viewport mapping, touch mapping).
- Headless (`SIM_HEADLESS=1`) uses a hidden window, SDL's `offscreen` video driver when there is no DISPLAY, and the
  dummy audio driver; SDL3 renamed the driver environment variables and hints.
- Screenshots: `SDL_SaveBMP` in SDL3 writes a different header. Anything that reads the game's BMPs (the scenario
  runner's reference comparison, the comparison tool) must decode pixels and accept both headers.

Coordination: workstream 1b moves the OpenGL calls (`gl*`) of the same files into backend files. Change only what
the SDL3 port needs: do not reformat, reorder or move code, and do not touch `gl*` calls.

## Verification (required)

1. `tools/sdl_gpu_migration/wt_run.sh sdl3 ninja -j3 -C build_linux` succeeds; `ldd build_linux/main` shows
   `libSDL3` and no `libSDL2`.
2. Lockstep A/B against the reference binary, comparing decoded pixels, for `SIM_G2_GPU=0` and `1`: at least 20
   checkpoints through boot, intro and title, plus the new-game path. Zero differing pixels.
3. Both scenarios pass (`core_title`, `core_new_game`), the title one twice.
4. Interactive path under `xvfb-run -a` with `SDL_AUDIO_DRIVER=dummy`, keys injected with `SIM_DEBUG_KEYS`, exit
   with `SIM_DEBUG_EXIT_FRAME`: runs without errors (this executes the real window, event and audio-device code).
5. Report the list of SDL return-value checks that had to change, and everything about macOS and Windows that could
   not be verified here.
