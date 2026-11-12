# 1d. A/B frame-comparison tool and tours

Model: Sonnet. Tree name: none (Python only). Read `PLAN.md` and `briefs/COMMON.md` first.

## Resume state

`tools/dazzling/render_compare/` in this repo holds two helper modules from the previous run: `rc_game.py` (starts
two headless lockstep games and feeds both the same command stream) and `rc_image.py` (BMP reading and diffing).
Neither was finished, run by the integrator, or reviewed. The main program, the tours and the README do not exist.
Work in a copy (`/home/user/wt/compare/tools/dazzling/render_compare/`); the integrator copies the result back.
Run the integrator's reference binary read-only (working directory `build_linux`), always with your own
`SIM_SAVE_PATH` and output directories under `/home/user/wt/scratch/compare/`.

## Task

Both renderers will live in one binary, chosen by `SIM_RENDERER=gl|gpu` (not implemented yet). The existing switch
`SIM_G2_GPU=0|1` (CPU or GPU 2D renderer) works today and is how you exercise the tool for real. Build a tool that
runs one deterministic input script through two configurations and reports exactly where and how the pictures
differ, across as much of the game's rendering as can be reached without the owner's save files.

Read first: `docs/headless_protocol.md`, `tools/dazzling/headless_client.py`, `tools/dazzling/test/run.py` and its
README, the two scenarios that run without saves (`core_title_screen_animation.json`,
`core_new_game_distortion_world_prologue.json`), `tools/macos/g2gpu_compare*.py` (an earlier, narrower tool),
`tools/battle/sim.py`, `battle_specs/`, `docs/battle_engine.md`, `src/port/headless_game.c`,
`src/port/debug_field.c`.

Deliverables (Python 3, stdlib only):
1. `render_compare.py`: configuration A and B (binary, working directory, extra environment) run through the same
   tour in lockstep with screenshots at the same frames. Assert the `state` replies are identical at every
   checkpoint and report a state divergence as a louder failure than a pixel difference. Per checkpoint: identical,
   or max channel delta, count and percentage of differing pixels, bounding box, split per DS screen, and a visual
   diff image (A, B, amplified difference). `--max-delta` and `--max-pixels-pct` thresholds, default exact. Non-zero
   exit on failure, `report.json`, and a summary sorted worst first. `-j 2` runs A and B concurrently.
   The BMP reader must decode pixels and accept both header variants (SDL2 writes pixel data at offset 122, SDL3 at
   138): an SDL2 build compared with an SDL3 build must report identical when the pixels are.
2. Tours (`tours/*.json`, reusing the scenario step vocabulary where possible), each a few minutes at most on this
   machine. Wanted coverage: boot logos, the intro movie and the title screen; new game (Rowan, naming screen,
   prologue); field maps of different kinds reached by `warp` (town, route with grass and water, cave, snow route,
   interior, a map with fog or weather, the Distortion World), with a few steps walked; start menu, bag, party,
   Pokedex, town map, options; battles through `start_battle` specs (wild, trainer, moves with 3D particles,
   stat-change effects, Mega Evolution with its PostFX, weather); fades, mosaic, windows; the save screen. Where a
   warp or battle needs setup from a fresh game, find the minimal setup and write it down; where something cannot
   be reached without a real save, say so.
3. Validation: every tour with `--a SIM_G2_GPU=0 --b SIM_G2_GPU=1` on the reference binary, reported honestly (on
   this machine the two 2D paths match at the two boot checkpoints the integrator checked; anything else is a
   finding). One tour with A equal to B, twice, to prove the harness and the tours are reproducible.
4. `README.md`: usage, tour format, how to add a tour, what each covers, what is unreachable, run times.

Constraints: at most two game instances at once, `nice`d. Do not modify game or simulator source; list protocol
gaps in your report instead.

## Verification (required)

The runs in deliverable 3, with numbers: tours, run times, checkpoint counts, A/B result per tour.

Report additionally: protocol gaps that limited coverage, and the exact command line for `SIM_RENDERER=gl` against
`SIM_RENDERER=gpu`.
