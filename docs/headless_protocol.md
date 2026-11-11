# Headless and lockstep protocol

Engine side: `debug-headless`. Runner side: `debug-suite`. This document describes exactly
what is implemented; it is updated in the same commits as the code.

Status: step 1 (headless + save path + fixed RTC/seed) implemented and verified on Linux
(devvm37887, Mesa llvmpipe). macOS verification is pending (lead runs it at integration);
all platform-specific code is guarded so the same paths build on macOS.

## Environment variables

| Variable | Effect |
|---|---|
| `SIM_HEADLESS=1` | No visible window (hidden window; on Linux with no `DISPLAY`, SDL's `offscreen` video driver via EGL surfaceless), SDL dummy audio driver, uncapped frame rate, vsync off. Rendering still happens, so screenshots work. |
| `SIM_SAVE_PATH=<file>` | The save file (`save.bin`) is read/written at this path instead of `./save.bin`. `save.bin.bak` is written next to it as `<file>.bak`, and import backups go in `save-backups/` next to it. Several instances can share one build directory with different save paths. |
| `SIM_FIXED_RTC=YYYY-MM-DDTHH:MM:SS` | The RTC starts at that instant and advances exactly 1/60 s per rendered frame (whole seconds = frame/60), never by wall clock. Applies with or without headless. |
| `SIM_SEED=<n>` | Seeds the game's RNGs (`MTRNG`/`LCRNG` in `InitRNG`) with `n` instead of the RTC/vblank-derived seed. Together with `SIM_FIXED_RTC` and identical inputs, runs are deterministic. |
| `SIM_CONTROL=stdio` | Lockstep protocol (step 2). Implies `SIM_HEADLESS=1`. |
| `SIM_WATCHDOG_SEC=<n>` | Watchdog timeout in seconds (step 4). On by default in headless mode. |

Existing `SIM_DEBUG_*` automation (keys, screenshots, exit frame, save import/export) keeps
working unchanged, including in headless mode.

## Determinism

With `SIM_HEADLESS=1 SIM_FIXED_RTC=... SIM_SEED=...`, the same save and the same inputs give
identical screenshots across runs. Verified on Linux: two runs importing the same test save
with the same `SIM_DEBUG_KEYS` script produced byte-identical BMP screenshots (md5 match).

Note on frame numbering: protocol and `SIM_HEADLESS_SHOT_AT` frames count rendered frames (`SIM_Headless_FrameCount`). The older `SIM_DEBUG_*` frame numbers use the DS vblank counter, which can run ahead of rendered frames at uncapped rates, so two runs shot at the same vblank number are not necessarily the same rendered frame.

Caveats:
- The simulator's random MAC address (`srand(time(NULL))` in `SIM_Config_LoadDefaults`) is
  not game-visible in single-player test scenarios.
- Rendering goes through the host GL driver; pixel equality is guaranteed for the same
  machine/driver, not across different GPUs/drivers.

## Lockstep protocol (`SIM_CONTROL=stdio`)

Step 2. To be filled in with the exact command/reply shapes as implemented.

## Game-side commands and state

Step 3. To be filled in.

## Asserts, crashes, watchdog

Step 4. To be filled in.

## Sanitizer build

Step 5. To be filled in.
