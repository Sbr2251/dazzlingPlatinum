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

### Lockstep guarantee (`SIM_CONTROL=stdio`)

In control mode, game state is a pure function of the save, `SIM_SEED`, `SIM_FIXED_RTC`,
and the command sequence: identical commands give byte-identical `state` replies and
screenshots regardless of the 2D renderer (`SIM_G2_GPU=0` or `1`), render speed, or
machine load (including a second headless game running alongside). Nothing that game
logic can observe advances at wall-clock rate in this mode:

- Sound: the SDL audio callback emits silence and advances nothing. The sequencer
  (`SND_SeqMain`/`SND_ExChannelMain`), envelopes, fades, cries, and channel sample
  progression advance in `SIM_Audio_LockstepFrame`, once per rendered frame at the
  interactive rate (44100 samples/s of simulated time, fractional accumulators), on
  the game thread. Before this, they advanced only in the SDL audio callback, so
  e.g. the title screen waited a render-speed-dependent number of frames for the
  Giratina cry and every later input landed at a different phase.
- `OS_GetTick` is derived from the rendered frame count
  (`frame * (OS_SYSTEM_CLOCK/64) / 60`), not `SDL_GetTicks64`.
- OS alarms fire from the frame hook when the deterministic tick reaches them;
  no `SDL_AddTimer` is created in control mode.
- `import_save` is synchronous on the game thread, so the `execv` restart always
  happens at the next rendered frame instead of after a wall-clock-dependent
  number of the 30 post-import frames.

Outside control mode none of this changes: the audio callback, tick, alarms, and
the threaded save import behave exactly as in interactive play.

Verified on macOS (2026-11-11): `core_wild_battle_start_flee` state checkpoints
(225 state/screenshot samples through the battle) and boot screenshots are
byte-identical between `SIM_G2_GPU=0` and `SIM_G2_GPU=1`; both wild scenarios
pass 3x per renderer and once with another headless game running alongside.

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
| `{"cmd":"touch","x":X,"y":Y,"frames":N}` | Touch the bottom screen at DS coordinates (256x192) for N frames while stepping. The panel is pulsed on long touches (2 frames down, 14 frames up), so the game - which only sees a touch on the 0->1 edge - gets a fresh press every 16 frames for the whole command; a single held touch would register only on its first frame, before a touch-only battle menu (party SHIFT card, Use-next-Pokemon buttons) has finished opening. Short taps (<=10 frames) produce exactly one press, so chained menus are not double-tapped. |
| `{"cmd":"reload_scripts"}` | Script hot-reload (debug): re-read the current map's scripts and text bank from disk (see "Script hot-reload" below). Errors when not in the field or while a script is running. |
| `{"cmd":"screenshot","path":"..."}` | Write the last rendered frame to a BMP at `path`. |
| `{"cmd":"state", ...}` | Game state (below; step 3 for the full fields). |
| `{"cmd":"import_save","path":"..."}` | Import a raw `.sav`/`.dsv`, reply, then restart the process (stdin/stdout survive `execv`, so the same client keeps working; the reply carries `"restarting":true`). |
| `{"cmd":"memory"}` | Heap peaks + VRAM usage (below). |
| `{"cmd":"quit"}` | Reply, then exit 0. |

Example client: `tools/dazzling/headless_client.py`.

State (basic, step 2): without the game-side handler (step 3) `state` replies
`{"ok":true,"frame":N,"app":"unknown"}`. Step 3 replaces this with the full state.

## Game-side commands and state

Implemented (step 3) in `src/port/headless_game.c`. All return
`{"ok":true}` or `{"ok":false,"error":"..."}`.

| Command | Effect |
|---|---|
| `{"cmd":"warp","map":"MAP_HEADER_X","x":X,"z":Z,"dir":"DIR_NORTH"}` | Fly-style map change to that tile (`dir` optional, default `DIR_SOUTH`). Needs the field. |
| `{"cmd":"set_var","name":"VAR_X","value":V}` | Set a story var (field var pointer in the field, save vars otherwise). |
| `{"cmd":"set_flag","name":"FLAG_X","value":true}` | Set/clear a flag (same storage choice as `set_var`). |
| `{"cmd":"give_item","item":"ITEM_X","qty":N}` | Add items to the bag (`qty` defaults to 1). |
| `{"cmd":"talk","localid":"LOCALID_X"}` or `{"cmd":"talk","object":N}` | Move the player to a free adjacent tile facing the object (matching its elevation), then start the object's script exactly as the A-button interaction does (`ScriptManager_Set`). Starting it directly, rather than pressing A, makes talk deterministic: a wandering NPC can step off the faced tile before a pressed A lands. Errors when no adjacent tile is free or a script is already running. The reply includes the object's and player's positions. |

Names (`MAP_HEADER_*`, `VAR_*`, `FLAG_*`, `ITEM_*`, `SPECIES_*`, `DIR_*`,
`LOCALID_*`) are resolved from the build's generated data
(`generated/*.txt` enum sources, `res/field/maps/*/events.json`,
`include/constants/map_object.h`) by `tools/dazzling/gen_headless_names.py`,
which runs at build time and emits `headless_names.{h,c}`. Nothing is
hand-maintained. `LOCALID_*` ids are scoped to the current map.

`state` replies (step 3, full form):

```json
{"ok":true,"frame":N,"overlay":<FS overlay id>,
 "app":"field"|"battle"|"other",
 "map":"MAP_HEADER_X","map_id":N,
 "player":{"x":X,"z":Z,"dir":"DIR_NORTH"},
 "script":{"id":N,"offset":N} | null,
 "message_waiting":true|false,
 "party":[{"species":"SPECIES_X","species_id":N,"level":N,"hp":N,"max_hp":N,"held_item":"ITEM_X"}],
 "battle":{"turn":N,"waiting":true|false,
           "battlers":[{"battler":N,"species":"SPECIES_X","species_id":N,"level":N,"hp":N,"max_hp":N,"held_item":"ITEM_X"}]},
 "vars":{"VAR_X":N},"flags":{"FLAG_X":true},"bag":{"ITEM_X":N}}
```

- `map`/`player`/`script` appear in the field; `battle` appears in battle
  (`waiting` = the action menu is waiting for input); `party` is always present
  once a save is loaded. `script.offset` is the byte offset of the running
  script's program counter in its script data, or -1.
- `vars`, `flags`, `bag` appear only when requested:
  `{"cmd":"state","vars":["VAR_X"],"flags":["FLAG_X"],"bag":["ITEM_X"]}`.
  Unknown names report -1/false rather than failing the whole reply.
- `memory` appears in `state` when requested (`{"cmd":"state","memory":true}`),
  same shape as the standalone `memory` command:
  ```json
  {"memory":{"heaps":[{"id":5,"name":"BATTLE","size":2949120,"used":123456,"peak":234567,"peak_size":2949120,"blocks":42}],
             "vram":{"tex_kind":"lnk","tex_total":524288,"tex_free":400000,
                     "pltt_kind":"lnk","pltt_total":98304,"pltt_free":90000}}}
  ```
  `size` is the port-scaled (4x DS) heap size; `peak` is peak-ever used
  bytes since boot; `used` counts direct NNS-allocator allocations too.
  Only heaps with a live size or a recorded peak are listed. VRAM
  totals/free are -1 when unknown (frame managers, or before any manager
  is initialised). VRAM is not enlarged: sizes are DS hardware limits.
- `overlay` is the numeric FS overlay id (the application templates have no
  string names in the binary); `app` is the semantic classification.
- `talk`'s A press and `warp`'s map change take effect over the following
  frames; step and re-read `state` to observe the result.

## Script hot-reload (debug)

Field scripts and their text are loaded on demand from their NARC files
(`fielddata/script/scr_seq.narc`, `msgdata/pl_msg.narc`) every time a new
script context starts - nothing is cached in RAM while no script is
running. Editing a script therefore needs no game restart:

1. Edit `res/field/maps/<map>/scripts.s` (and/or its text in `res/text/`).
2. Rebuild the script/text targets and the file-copy step that lays them
   out where the game reads them (`fielddata/script/scr_seq.narc`,
   `msgdata/pl_msg.narc` under the build root):
   `ninja -C build_linux pokeplatinum.us`
   (on the Mac build tree: the same target under `build_macos`; a plain
   incremental `ninja` does the same when only scripts/text changed).
3. Reload: press **Reload Scripts** in the backtick GUI's pokeplatinum
   window, or send `{"cmd":"reload_scripts"}` headless. The reply carries
   the map name/id, script archive id, text bank id and the re-read sizes:
   `{"ok":true,"map":"MAP_HEADER_...","map_id":N,"script_archive":N,"text_bank":N,"script_bytes":N,"text_bytes":N}`.
   The next script that starts (talk, bg event, trainer sight) uses the
   rebuilt files.

The reload is refused while a script is running (`"a script is running;
reload deferred until it finishes"`; the GUI shows the same as a deferred
message) - a running script context owns the old script buffer and message
loader, and swapping files under it would corrupt its program counter.
New script *labels* are resolved by their ordinal in the map's script file,
so appending entries keeps existing script ids valid; adding a new object
event for a new label still needs the map itself to reload (warp away and
back), because object events load with the map.

## Asserts, crashes, watchdog

Implemented (step 4).

- `GF_ASSERT` carries file, line and the stringified expression
  (`include/global/assert.h`). It is keyed off `PM_KEEP_ASSERTS`: defined in
  dev/asan builds, absent in release, where `GF_ASSERT` compiles to nothing
  (the `build_variant` option from perf-game controls this; currently the
  port build defines it unconditionally).
- On PC builds, a failure (`src/error_handling.c`) behaves as follows:
  - Headless/control: always fails loudly - `GF_ASSERT <file>:<line>: <expr>`,
    a state dump and a symbolized backtrace (`backtrace()`/
    `backtrace_symbols_fd`; `-rdynamic` on Linux) to stderr, then exit 134.
    The interactive `EnableAsserts` config does not gate this.
  - Interactive with asserts enabled in the config: the same info is appended
    to `log.txt`, shown in an SDL message box, and the process exits 134
    instead of hanging silently. With asserts disabled in the config, the
    old behaviour (return and continue) is kept.
  - The simulator's own `SDK_ASSERT` (`SIM_handleAssertionFailure`) routes
    through the same reporter in headless mode.
- Best-effort signal handlers for SIGSEGV/SIGBUS/SIGABRT are installed in
  headless/control mode: they print the signal, the frame count and a
  backtrace to stderr, then exit 134. (Not installed interactively, so macOS
  crash reports in `~/Library/Logs/DiagnosticReports` keep working there.)
- Watchdog: `SIM_WATCHDOG_SEC=<n>`; on by default in headless/control mode
  with n=30 (`SIM_WATCHDOG_SEC=0` disables). If no frame completes for n
  seconds it dumps state (via the `state` handler) plus a backtrace to
  stderr and exits 124. It never fires while lockstep control is blocked
  waiting for a command, so an idle client is not a freeze; if inputs are
  being sent (frames granted) and frames stop completing, it fires.

## Sanitizer build

Implemented (step 5): the `asan` build variant (`tools/macos/build.sh asan`, meson `-Dbuild_variant=asan`)
instruments the whole PC build (game, simulator and host tools) with ASan + UBSan.
It adds `-fsanitize=address,undefined -fno-omit-frame-pointer` to compile and
link. (On the Linux devserver the build also needed static sanitizer runtimes
and `-Wl,--allow-shlib-undefined`; those GNU-ld flags are not in meson.build,
because Apple ld rejects them.)

Build (Linux):
```sh
python3 subprojects/meson-1.12.0/meson.py setup -Dbuild_target=linux -Dbuild_variant=asan \
  -Ddefault_library=static --native-file=... --cross-file=meson/cross_pcport_linux.ini build_asan
ninja -C build_asan
ASAN_OPTIONS=detect_leaks=0 ./main   # plus SIM_* as usual
```
On this devserver the GCC 15 toolset lacks the 64-bit sanitizer runtime;
the build was linked against clang compiler-rt archives via `LIBRARY_PATH`
(scratch only, not part of the repo build). On macOS / perf-game's toolchain
the option works as-is.

Findings from running one test save (boot -> field -> warp -> talk) through
the ASan build are listed in the step-5 section of the status report; the
headline items are a simulator DMA register-block over-read at boot
(`mi_dma.c`, not fixed - needs the register layout work) and several build
tool over-reads (fixed).
