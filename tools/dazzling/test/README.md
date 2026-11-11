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
  `set_flag`, `give_item`, `import_save`, `wait_until`, `screenshot`, `assert`.
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
- The runner sets `SIM_HEADLESS=1 SIM_CONTROL=stdio SIM_FIXED_RTC=
  2026-01-01T12:00:00 SIM_SEED=12345`, a private `SIM_SAVE_PATH` per
  scenario (parallel-safe), and `SIM_SCRIPT_COVERAGE=<workdir>/coverage.txt`.
- On failure it prints the step index and step, the assertion/wait failure,
  the last state (truncated), the last screenshot path, and the per-scenario
  workdir (game stderr log + coverage log are kept there).

State paths assume the protocol's state reply nests field position under
`player` (`player.map`, `player.x`, `player.z`, `player.dir`) plus `app`,
`frame`, `message_waiting`, `in_battle`, `vars`/`flags`/`party` on request.
`run.py` also normalizes flat `map`/`x`/`z`/`application` replies. Field
names may need one adjustment pass when debug-headless documents its exact
reply in `docs/headless_protocol.md`.

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
