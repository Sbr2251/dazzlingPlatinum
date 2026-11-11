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

Implemented (step 2). `SIM_CONTROL=stdio` implies `SIM_HEADLESS=1`.

- The game does not advance until told to. Control sits at the end of each rendered
  frame (inside `SIM_Render`, before the swap): when no frame budget remains, the game
  blocks reading stdin. The first rendered frame happens at boot; after that, frames
  run only in response to `step`/`press`/`touch` (and a short run after `import_save`
  so the restart can happen).
- Each command is one line of JSON on stdin. Each reply is one line of JSON on stdout.
  In this mode fd 1 is redirected to stderr, so all game `printf` output goes to stderr
  and stdout carries only replies. EOF on stdin quits the game (exit 0).
- Frames count *rendered* frames (`SIM_Headless_FrameCount`, also the `frame` field in
  replies), not the DS vblank counter. One rendered frame is exactly one `SIM_Render`
  call, which performs exactly one VBlank IRQ dispatch and one vblank-counter increment
  (the only increment site in the PC build is in `SIM_Render`), so vblank processing
  stays in lockstep with rendered frames: inputs applied for a step are sampled by the
  game on the first of those frames, and `step N` advances exactly N rendered frames
  and N vblanks.
- `step`/`press`/`touch` reply *after* their frames have run, with the new frame count.
  All other commands reply immediately. Every reply is an object with at least
  `{"ok":true,"frame":N}` or `{"ok":false,"error":"...","frame":N}`.

| Command | Effect |
|---|---|
| `{"cmd":"step","frames":N}` | Run N frames with no keys held. `frames` defaults to 1. |
| `{"cmd":"press","keys":["A","UP"],"frames":N}` | Hold the named keys (`A B X Y L R START SELECT UP DOWN LEFT RIGHT`) for N frames while stepping. |
| `{"cmd":"touch","x":X,"y":Y,"frames":N}` | Touch the bottom screen at DS coordinates (256x192) for N frames while stepping. |
| `{"cmd":"screenshot","path":"..."}` | Write the last rendered frame to a BMP at `path`. |
| `{"cmd":"state", ...}` | Game state (below; step 3 for the full fields). |
| `{"cmd":"import_save","path":"..."}` | Import a raw `.sav`/`.dsv`, reply, then restart the process (stdin/stdout survive `execv`, so the same client keeps working; the reply carries `"restarting":true`). |
| `{"cmd":"quit"}` | Reply, then exit 0. |

Example client: `tools/dazzling/headless_client.py`.

State (basic, step 2): without the game-side handler (step 3) `state` replies
`{"ok":true,"frame":N,"app":"unknown"}`. Step 3 replaces this with the full state.

## Game-side commands and state

Step 3. To be filled in.

## Asserts, crashes, watchdog

Step 4. To be filled in.

## Sanitizer build

Step 5. To be filled in.
