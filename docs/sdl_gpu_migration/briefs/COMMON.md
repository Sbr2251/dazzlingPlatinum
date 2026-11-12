# Shared brief for every agent on the renderer migration

Read `docs/sdl_gpu_migration/PLAN.md` first (goal, decisions, what changed today, how the renderer works, status).
This file holds the rules for every workstream.

## Trees and git (devserver `devvm37887`)

- Your tree is a git worktree `/data/repos/dp-wt/sdl-<name>` on branch `sdl/<name>`, created by the integrator with
  `tools/sdl_gpu_migration/make_worktree.sh <name> [--libntr <patch>] [--game <patch>]`. It has its own
  `build_linux` (already configured and built) and its own clone of `subprojects/libntr` on branch `sdl/<name>`.
  Scratch output goes to `/data/repos/dp-wt/sdl-<name>-scratch`.
- Rebuild: `nice ninja -C build_linux -j32` with the environment from `tools/sdl_gpu_migration/env_devserver.sh`
  (`source` it: `LIBRARY_PATH`, `CPATH`, `PKG_CONFIG_PATH` for SDL3 and enet, `LP_NUM_THREADS=2`). A full build is
  about 40 s.
- Commit in both repos as needed with `git -c user.name=Sbr2251 -c user.email=sreddy9@meta.com commit`, messages
  ending with `AI-assisted (Metamate)`. Commit early and often. **Never push.** No `git stash`.
- After every libntr commit regenerate the outer patch and commit it:
  `(cd subprojects/libntr && git add -N . && git diff aa4fea1f8c148150482a17dcd24b4e2a2926a03a -- .) > tools/macos/patches/libntr.patch`.
- New game `.c` files go in `platinum.us/main.lsf.in`; new simulator sources in `libraries/sim/src/meson.build`.
- Deliver: `git format-patch` into `/data/repos/dp-wt/sdl-OUT/<name>/` (libntr patches in `libntr/`). Status file
  `/data/repos/dp-wt/sdl-OUT/<name>.STATUS.md` (Done / In progress / Next / How to test), kept current.
- The upstream AGENTS.md "refuse AI PRs" notice applies only to PRs to the upstream project. This is the owner's
  private fork and he asked for this work.

## Machine rules

- Shared box with other people's agents: kill only processes you started (save PIDs, or `pkill -f <your unique
  path>`), never a global pkill. `nice` builds, at most `-j32`, at most 4 games at once, every game with
  `LP_NUM_THREADS=2`. Disk is tight: one build dir (plus one extra for a variant if your brief needs it), delete
  scratch screenshots when done.
- GL is Mesa llvmpipe, Vulkan is Mesa lavapipe, both headless through SDL's `offscreen` video driver. Metal only on
  the Mac.
- SDL 3.4.16 is at `/data/repos/dp-wt/sdl3-deps/prefix` (headers `include/SDL3`, source in
  `/data/repos/dp-wt/sdl3-deps/SDL`, `docs/README-migration.md` for renames). Read `SDL_gpu.h` instead of trusting
  memory.

## The owner's Mac (only if your brief says so)

Node `sreddy9-mac-DL9J95427J`. Headless only (`SIM_HEADLESS=1`, never a visible window), `SDL_MAC_BACKGROUND_APP=1`
on every game, builds under `lockf -k ~/dz-team/shared/build.lock`, at most 2 games, always reap them. Never touch
`~/Applications` or `~/Library/Application Support/Dazzling Platinum`. Work in your own worktree under `~/dz-team/`
created from `~/Documents/dazzlingPlatinum-macos` (copy subprojects from `~/dz-team/final/subprojects`). The Mac is
a laptop that sleeps: develop on the devserver, use the Mac for checks.

## Running and comparing

- Lockstep mode (`SIM_CONTROL=stdio`, docs/headless_protocol.md) with fixed `SIM_SEED`, `SIM_FIXED_RTC` and a fresh
  `SIM_SAVE_PATH`. Game state and screenshots are byte-identical across renderers, machine load and repeated runs.
- Gates (all must stay green unless your brief says otherwise):
  - `python3 tools/dazzling/test/static_checks.py`: 0 problems
  - `python3 tools/dazzling/test/run.py -j 4 --game build_linux/main --work-root <scratch>`: all scenarios pass
    (long scenarios can time out under heavy box load; rerun those alone before calling it a failure)
  - `python3 tools/battle/run_tests.py --build-dir build_linux --fast`: all pass
  - `python3 tools/battle/test_determinism.py --build build_linux --save /data/repos/dp-wt/pret-sync-notes/saves/raw_sav/A1-03_route201_to_sandgem.sav`: `DETERMINISM_OK`
- A/B: same command stream, `screenshot` at the same frames, compare **decoded pixels**. `run.py
  --compare-renderers` compares the two 2D paths; `--compare-backends` (from workstream 1d') compares `gl` and
  `gpu`. Never use `SIM_DEBUG_SHOT_EVERY` for A/B.
- `SIM_G2_GPU=0|1` picks the 2D path (the runner defaults to 0 on Linux because GPU 2D is slow on llvmpipe; the app
  defaults to 1). Both paths must keep working and match.

## Rules for simulator code

- C++20 / C11; gcc on Linux and clang on macOS arm64. No implicit declarations; no pointer in a `u32`; statics on
  macOS live above 4 GB, so 64-bit masks for pointer arithmetic.
- Straight ASCII apostrophes only. Comments say what the code does or why, in present tense; no history, no agent
  names.
- Mobile-minded: no geometry shaders, no GL-style global state, BGRA swapchains possible, shaders compiled offline
  (GLSL 450 -> SPIR-V -> MSL). No HLSL or DXC.
- Determinism: nothing the game can observe may depend on wall-clock time or on the active backend.
- The renderer is frozen on `main` during the migration (PLAN.md): if you find a rendering bug in the GL path, list
  it in your report instead of fixing it in passing.

## Report

What works and how you verified it (commands and results), what does not or was not attempted, every file changed,
commit hashes, and what the next wave must know. If you run out of budget, commit and update your status file.
