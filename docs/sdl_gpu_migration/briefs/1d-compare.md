# 1d'. Backend comparison in the scenario runner (replaces v1's render_compare tool)

Model: Muse (tbh-1005 or tbh-1015). Tree name: `compare`. Read `PLAN.md` and `briefs/COMMON.md` first.
Tree: `tools/sdl_gpu_migration/make_worktree.sh compare`. Python and scenario files only; no simulator changes.

## Why

v1 planned a separate A/B tool (`tools/dazzling/render_compare/`). Since then `tools/dazzling/test/run.py` gained
cropped golden references, expected/actual/diff images, `--update`, `--compare-renderers` (CPU vs GPU 2D) and
per-platform references, and lockstep runs became byte-identical across renderers. Extend the runner instead.

## Task

1. `--compare-backends`: run each selected scenario twice, `SIM_RENDERER=gl` and `SIM_RENDERER=gpu`, against the
   same references, reporting both results per scenario (mirror `--compare-renderers`). Combinable with
   `--compare-renderers` (four runs). Per-scenario, per-step override for the `gpu` run's tolerance
   (`"tolerance_gpu": 0.002`) so wave 3 can record agreed 3D thresholds. Until the `gpu` backend exists, the game
   falls back to `gl` and both runs must pass.
2. New golden scenarios (event-anchored, not fixed-frame: wait for state, battle events or message text, then a short
   settle; record Linux references on `build_linux` and Mac references on the owner's Mac):
   - display capture: Totem Mamoswine at `MAP_HEADER_ACUITY_LAKEFRONT` (`LOCALID_TOTEM_MAMOSWINE_4`, needs a 2+ mon
     party): 3 frames inside the motion-blur window;
   - `HiResText=true` dialogue box; `Upscale2DFilter=Sharp` overworld frame;
   - screen layouts (vertical, horizontal, large) and swapped screens, one frame each;
   - the Distortion World; the bag, party, Pokedex and town-map menus; the naming screen;
   - an internal-resolution change at runtime (debug config), one frame after the change.
3. Docs: `tools/dazzling/test/README.md`. Keep the full suite under ~15 minutes at `-j4` on the devserver.

## Verification

Each new scenario passes 3 times in a row on Linux and on the Mac; `--compare-backends` passes over the whole suite
(`gl` vs `gl` fallback); eyeball every new reference and list what each shows in the report.
