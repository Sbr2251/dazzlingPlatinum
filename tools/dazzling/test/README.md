# Dazzling Platinum test suite (debug-suite)

Three pieces, all under `tools/dazzling/test/` unless noted. The game side of
the headless/lockstep protocol is owned by debug-headless (see BRIEF.md,
"Shared interface"); this suite develops against that protocol as specified.
Until it lands, `fake_game.py` implements the protocol for the runner's own
unit tests.

## One command each

```sh
# static checks (no game build, ~seconds)
python3 tools/dazzling/test/static_checks.py

# scenario suite (needs build_macos/main with SIM_HEADLESS/SIM_CONTROL)
python3 tools/dazzling/test/run.py -j 4

# sanitizer gate (ASan + UBSan across the whole suite): builds the `asan`
# variant in `build_asan` (configure it once; see the header of the script
# and docs/headless_protocol.md "Sanitizer build") and runs the scenario
# suite, the battle tests, and short soaks under it. Exits non-zero on any
# sanitizer report. UBSan suppressions for the NNS allocator's own
# 4-byte-aligned block headers live in `ubsan_suppressions.txt` (see its
# header); misalignment in game code still reports.
bash tools/dazzling/test/sanitize.sh

# random-input soak (overworld + menus) against any headless build:
#   LP_NUM_THREADS=2 python3 tools/dazzling/test/soak.py --game build_asan/main --frames 6000 --seed 7

# (re)record reference screenshots
python3 tools/dazzling/test/run.py --record --filter title
```

Runner unit tests (mock game, no build): `python3 tools/dazzling/test/test_runner.py`

## Scenario format: JSON

JSON was picked over YAML: stdlib-only (no PyYAML on CI runners), and the
runner, the fake game and the protocol all already speak JSON.

```json
{
  "name": "core_save_and_reload",
  "_note": "free-form comment, ignored",
  "requires_exists": ["~/Downloads/.../A1-02.sav"],
  "start": {
    "save": "~/Downloads/.../A1-02.sav",
    "warp": {"map": "MAP_HEADER_ROUTE_201", "x": 10, "z": 12, "dir": "DIR_NORTH"},
    "vars": {"VAR_X": 1},
    "flags": {"FLAG_X": true},
    "items": [{"item": "ITEM_POTION", "qty": 3}]
  },
  "steps": [
    {"press": "UP", "frames": 10},
    {"hold": ["A", "UP"], "frames": 30},
    {"step": 60},
    {"touch": [120, 90], "frames": 5},
    {"talk": "LOCALID_X"},
    {"wait_until": {"app": "field"}, "timeout_frames": 1200},
    {"screenshot": "shot", "reference": "../references/x.bmp", "tolerance": 0.01},
    {"assert": {"player.map": "MAP_HEADER_TWINLEAF_TOWN"}}
  ],
  "assertions": [{"player.map": "MAP_HEADER_TWINLEAF_TOWN"}]
}
```

- `start`: a save (`import_save`), or nothing (new game / title), plus
  optional `warp`/`vars`/`flags`/`items` applied after loading.
- Steps: `press`/`hold` (key or list, held `frames`), `step` (frames),
  `touch`, `talk` (localid or `{"object": N}`), `warp`, `set_var`,
  `set_flag`, `give_item`, `import_save`, `wait_until`, `screenshot`, `assert`,
  and `press_until` (press periodically while polling a state condition -
  use this to finish dialogue instead of fixed press counts, which race
  message timing). A scenario with `"known_issue": "..."` or
  `"pending_step3": "..."` is reported as a SKIP with that text.
- Assertions map dotted state paths (`player.map`, `party.0.level`) to
  expected values, or use `{"path": ..., "op": eq|ne|gt|ge|lt|le|contains|in,
  "value": ...}`. `wait_until` takes the same shape and steps 10 frames at a
  time until it holds or `timeout_frames` runs out.
- Screenshots compare against `reference` (BMP; PNG via `sips` on macOS)
  with `tolerance` = allowed fraction of differing pixels. `--record`
  writes references instead of comparing. `optional_reference: true` skips
  a missing reference (used until a reference is recorded on the real build).
- `requires_exists`: if a listed path is missing the scenario is a SKIP,
  not a failure. The 18 test saves and the Mega save live in
  `~/Downloads` (BRIEF.md), not the repo, so those scenarios are local-only
  and skip in CI.
- Frame counts are rendered frames (per debug-headless's docs/headless_protocol.md), not the DS vblank counter used by the old SIM_DEBUG_* numbers. The runner sets `SIM_HEADLESS=1 SIM_CONTROL=stdio SIM_FIXED_RTC=
  2026-01-01T12:00:00 SIM_SEED=12345`, a private `SIM_SAVE_PATH` per
  scenario (parallel-safe), and `SIM_SCRIPT_COVERAGE=<workdir>/coverage.txt`.
- On failure it prints the step index and step, the assertion/wait failure,
  the last state (truncated), the last screenshot path, and the per-scenario
  workdir (game stderr log + coverage log are kept there).

State paths (step 3, `docs/headless_protocol.md`): top-level `map` plus
`player.x/z/dir` are normalized to `player.map/x/z/dir`; `battle.waiting` /
`battle.battlers[]` and `party[]` are as the engine sends them; `run.py`
adds `in_battle`. Short presses (1-2 frames) don't register in menus:
use ~10-frame presses.

## Script coverage

`src/field_script_context.c` (hook behind `SIM_SCRIPT_COVERAGE=<file>`, off
otherwise; loaders in `src/script_manager.c` record the scr_seq archive id)
appends `"<archive id> <offset>"` per script start. Map a run's logs to
labels and get a reached-story-labels report:

```sh
python3 tools/dazzling/test/coverage.py /path/to/coverage.txt
```

## Static checks

`static_checks.py` checks, each failure line naming check, file and line:
`script_targets` (folds in `tools/dazzling/check_script_targets.py`),
`text_labels`, `event_scripts`, `json_data`, `curly`, `waitfanfare`.
The curly check is baselined (`curly_baseline.json`): vanilla pret banks
use U+2019 as the in-game apostrophe glyph, so pre-existing files are
grandfathered by count and any new file or increased count fails. Only
regenerate the baseline after reviewing the diff:
`python3 tools/dazzling/test/static_checks.py --write-curly-baseline`.

## Golden-image (visual) regression tests

Scenarios named `visual_*` in `scenarios/` are exact-pixel golden tests:
every screenshot uses `tolerance: 0.0`, `crop` (top screen `[0,0,512,384]`,
bottom screen `[0,384,512,384]`) so references in `references/visual/` are
one 512x384 BMP (~577 KB) instead of the full 512x768 frame. Recording a
crop stores the cropped image; comparison crops only the actual frame
(legacy full-size references are cropped on the fly as a fallback). Battle
scenarios start from `tools/battle/specs/visual_*.json` (plus the shared
`mega_infernape_vs_garchomp.json` / `totem_battle.json`) via the new
`start_battle` / `battle_decide` / `battle_event` step types, and screenshot
at a fixed rendered-frame offset after a decision, so the frame is a pure
function of save + seed + spec + decisions (`docs/headless_protocol.md`).

Coverage: Intimidate stat drop, Swords Dance stat raise, Growl enemy stat
drop, Thunder Wave status, super-effective Flamethrower hit, Mega Evolution
('reacting' text + cinematic flash), Totem aura flare-up + persistent
aura, double-battle target select (bottom-screen battler buttons), wild
battle opening, and overworld frames on 6 story-save maps (Lake
Verity, Twinleaf, Jubilife, Oreburgh City, Eterna Forest, Solaceon).

Battle screenshots are **event-anchored**, not fixed-frame (fps60 changed
presentation timing and moved every fixed offset): each waits for an engine
event via `wait_battle_event` (`stat_stage`, `status`, `damage`,
`move_chosen` with `mega:true`, `mega_evolution`, the Totem aura's first
`stat_stage` boost, `battle_start` for the wild opening) and then takes a
short fixed settle (30-400 rendered frames) into the animation. References
are per-platform: Linux `references/visual/`, macOS `references/visual_mac/`
(picked automatically on darwin); both sets verified 3x in a row.

```sh
python3 tools/dazzling/test/run.py --game build_linux/main -j 4 --filter visual   # check
python3 tools/dazzling/test/run.py --game build_linux/main -j 4 --record --filter visual  # re-record all
python3 tools/dazzling/test/run.py --game build_linux/main --update --filter visual_intimidate  # accept new reference(s) after reviewing a diff
python3 tools/dazzling/test/run.py --game build_linux/main --compare-renderers --filter visual_intimidate  # CPU vs GPU 2D
```

- On mismatch the failure prints `expected:` / `actual:` / `diff:` BMP
  paths inside the scenario workdir (diff = differing pixels in red over a
  darkened actual). Review those three, then accept deliberately with
  `--update --filter <name>` (never blanket-`--record` a red suite).
- `--compare-renderers` runs each selected scenario twice,
  `SIM_G2_GPU=0` and `=1`, against the same references: real game scenes
  covering text/affine BGs, OBJ + windows, blending/translucency and the
  3D battle stage (depth-equal/decal stat-effect quads, toon sprites).
  Caveat on this devserver: Mesa llvmpipe rejects `g2gpu_fragment.glsl`
  (`uint packed` - `packed` is reserved), so the GPU path fails to compile
  and falls back; a true GPU-vs-CPU pixel proof needs the g2gaps shader
  fix or the owner's Mac (Apple GL 4.1). The mode is ready for the scenes
  lane g2gaps names in its status file.
- Re-record responsibility when visuals change intentionally:
  **capture** (battle animation/particle changes) - battle `visual_*`;
  **g2gaps** (2D renderer features: mosaic, WIN1, affine windows, OBJ
  extended palettes) - all `visual_*`, via `--compare-renderers`;
  **hiresui** (UI/textbox/menu art) - double target-select, Mega and
  menu-adjacent frames; **fps60** (frame pacing/animation timing) - any
  frame-offset screenshot may land on a different animation phase.
- Timing notes: stat/status animation frames are fixed offsets measured
  on the current build (e.g. Intimidate at 660 rendered frames after
  `start_battle`). The Mega scenario ends on the cinematic frame and reads
  no state afterwards.

### Per-platform references (macOS)
3D rasterization differs by a few pixels between Apple's OpenGL and Mesa llvmpipe, so golden images are per platform:
Linux uses `references/<dir>/`, macOS uses `references/<dir>_mac/` (e.g. `references/visual_mac/`). Record the Mac set on a
Mac with `run.py --update --filter visual_`; Linux CI keeps using the base set.
