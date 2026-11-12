# Shared brief for every agent on the renderer migration

Read `docs/sdl_gpu_migration/PLAN.md` first (goal, decisions, how the renderer works, status). This file holds the
rules that apply to every workstream. Paths below assume the repo is at `/home/user/dazzlingPlatinum`, which makes
the helper scripts use `/home/user/wt` for workstream copies and `/home/user/deps` for SDL3.

## Trees and git

- The integrator's tree is the repo itself. Treat it as read-only. Its `build_linux/main` is the OpenGL reference
  binary.
- The simulator is a separate git repo cloned at `subprojects/libntr` (ignored by the outer repo). Its local branch
  `dazzling` is upstream plus this project's patch. The outer repo stores that as
  `tools/macos/patches/libntr.patch`; the integrator regenerates it at the end. Do not edit or regenerate it.
- Your tree is `/home/user/wt/<name>` (created with `tools/sdl_gpu_migration/make_tree.sh <name> ...`). Edit files
  only under it. Commit there on branch `team/<name>` (one in the outer repo if you touch it, one inside
  `subprojects/libntr`), with `git -c user.name=agent -c user.email=agent@localhost commit`. Commit early and often:
  agents on this account have been cut off mid-task by usage limits, and uncommitted half-edits are hard to resume.
  Never push, never touch remotes.
- Build and run your tree only through the wrapper, which mounts your copy at the repo path:
  `tools/sdl_gpu_migration/wt_run.sh <name> ninja -j2 -C build_linux`
  `tools/sdl_gpu_migration/wt_run.sh <name> bash -c 'cd build_linux && SIM_CONTROL=stdio ... ./main'`
  Inside the wrapper your tree is `/home/user/dazzlingPlatinum`; outside it, it is `/home/user/wt/<name>`.

## Machine

- Ubuntu 24.04, 4 cores shared with the other agents: `ninja -j2`, one game instance at a time unless an A/B run
  needs two. A full game rebuild is about 14,000 steps (35+ minutes alone): avoid changing headers the whole game
  includes (`include/nitro/**`) unless your task requires it. Rebuilding the simulator library and relinking takes
  a minute or two.
- No GPU. OpenGL is Mesa llvmpipe through SDL's offscreen/EGL driver (no DISPLAY needed). Vulkan is Mesa lavapipe.
  Metal cannot be run here: design for it, verify on Vulkan, and say what is unverified.
- SDL 3.4.20 is at `/home/user/deps/prefix` (`include/SDL3/*.h`, pkg-config `sdl3`); its source, docs and examples
  at `/home/user/deps/SDL` (`docs/README-migration.md` lists the SDL2 to SDL3 renames). The headers are the
  authority on the API: read `SDL_gpu.h` instead of trusting memory.
- Installed: gcc, clang, meson (`python3 subprojects/meson-1.12.0/meson.py`), ninja, glslangValidator, spirv-cross,
  gdb, Xvfb, python3. Do not `apt-get install` without need; if you must, add the package to
  `tools/sdl_gpu_migration/setup_env.sh` in your tree and say so in your report.
- Ubuntu's gcc defaults to `_FORTIFY_SOURCE=3`. A "buffer overflow detected" abort usually means a `memcpy` across
  adjacent simulated hardware registers, which is intended on the DS.

## Running and comparing

- Read `docs/headless_protocol.md`. Use lockstep mode (`SIM_CONTROL=stdio`, JSON commands on stdin) with fixed
  `SIM_SEED` and `SIM_FIXED_RTC` and a fresh `SIM_SAVE_PATH` per run. Run from `build_linux` (the game reads its
  data relative to the working directory).
- A/B comparison: same command stream to both binaries or configurations, `screenshot` at the same frames, compare
  **decoded pixels**. Two rules learned the hard way (PLAN.md, "Verification method"): `SIM_DEBUG_SHOT_EVERY` is not
  deterministic and must not be used for A/B, and SDL2 and SDL3 builds write different BMP headers, so file hashes
  differ even when pixels match.
- `SIM_G2_GPU=0` selects the CPU 2D renderer, `1` (default) the GPU 2D renderer. Both must keep working.
- Scenario suite: `python3 tools/dazzling/test/run.py --game build_linux/main -j 1 --filter core_title` (75 s) and
  `--filter core_new_game` (5 minutes); pass `--work-root <scratch dir>`. Both pass on the reference.
- The reference binary may be run for comparison from the integrator's `build_linux`, always with your own
  `SIM_SAVE_PATH` and output directories. Put scratch output under `/home/user/wt/scratch/<name>/`.

## Rules for simulator code

- C++20 / C11; must build with gcc on Linux and clang on macOS arm64. No implicit declarations, no pointer stored in
  a `u32`.
- Straight ASCII apostrophes only, in every file.
- Comments say what the code does or why, in plain present tense. No history, no agent names.
- Mobile-minded: no geometry shaders, no reliance on GL-style global state, BGRA swapchains possible, shaders
  compiled offline (GLSL 450 to SPIR-V with glslangValidator, SPIR-V to MSL with spirv-cross). No HLSL or DXC.
- The game stays deterministic in lockstep mode: nothing the game can observe may depend on wall-clock time or on
  which renderer is active.

## Report (your final message goes to the integrator)

State plainly: what works and how you verified it (commands and results); what does not work or was not attempted;
every file added or changed; the commit hashes; and what the next wave must know. If you run out of budget, commit
what you have and write a `RESUME.md` at the top of your tree with the same content.
