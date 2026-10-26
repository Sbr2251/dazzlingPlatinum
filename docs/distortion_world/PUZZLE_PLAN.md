# Distortion World puzzles: difficulty curve and new mechanics (branch `dwpuzzles`)

Owner ask (2026-10-23): "All of the Distortion World puzzles are basically the same right now. Make the puzzles
harder as we get further into the game before the totem Pokémon is fought. Include new engine mechanics." Muse
Preview (tbh-1015) agents implement, Codex reviews and iterates with them, and the new puzzles are tested headlessly.

## 1. Where we are

Every rift is the same idea: walk a seam on a wall or ceiling and avoid one hazard. The hazard is either scripted or
on a timer, so there are no real decisions.

| Rift (story point) | Floor | Puzzle today | Decisions |
|---|---|---|---|
| Arc 1 seams (prologue) | B1F clone | wall-walk tutorial, one fork | 1 |
| Ravaged Path, Hitmonlee (after Gym 1) | B1F clone | west-wall seam, 2 scars that crumble one step after use, a fork | 1-2 |
| Eterna Forest, Vespiquen (Gym 1-2) | B4F record | ceiling walk, honeycomb on a 213-frame timer | timing only |
| Route 214, Skarmory (after Gym 3) | B4F clone | 2 hops, a wall climb, a 6-wide ceiling strip, the boost choice (story) | 0 |
| Route 213, Lapras (Gym 4) | B4F clone | serpentine ceiling path under the hanging lake | 0 |
| Lost Tower, Spiritomb (Gym 5) | B1F clone | wall seam, a false seam that drops you, 4 scripted ghost acts | 0 (all scripted) |

Engine pieces we have: wall/ceiling surfaces and jump points (tw_arc), per-surface wall grids (tw_arc_attr), ghost-prop
groups that fade in and out, step and frame hooks per map (`src/overlay009/ov9_02249960.c`), fall coord events with a
fall/respawn path, and DW objects. Not yet possible: changing walkability at runtime, forced movement, objects that
move on a surface, and puzzle state that survives a fall.

## 2. The curve (revised 2026-10-23: eight totem rifts, not five)

Arc 3 still has three totem rifts after the Lost Tower: Aggron, Mamoswine and Kingdra, at Gyms 6-8. The curve runs over
all eight, so Arc 2 stops at 6/10 and Arc 3 climbs to 10. Each rift adds **one** new mechanic, taught safely at the
start of the map, then mixes it with **at most one or two** earlier mechanics before the totem. The totem fight stays
behind the puzzle.

| # | Rift (story point) | New mechanic | Combined with | Difficulty (1-10) | Optimal solution | Fail cost |
|---|---|---|---|---|---|---|
| 0 | Arc 1 seams (prologue) | (tutorial, unchanged) | - | 1 | ~15 steps | none |
| 1 | Ravaged Path, Hitmonlee (after Gym 1) | **Rift sigils**: stepping on a sigil toggles a group of stone bridges (ghost props + live walkability) | crumbling scars (one-use tiles) | 2 | 15-25 steps, one ordering idea | fall → wall resets |
| 2 | Eterna Forest, Vespiquen (Gym 1-2) | **Gravity runes**: a rune tile flips you between surfaces in place (wall ↔ ceiling, ceiling ↔ floor) | honeycomb timing; one sigil at most | 3 | 25-40 | fall → last rune checkpoint |
| 3 | Route 214, Skarmory (after Gym 3) | **Rift currents**: drift tiles slide you until blocked, ice-style; arrows show the drift | sigils (a toggled block changes where a slide stops) | 4 | 35-50, a small slide maze | fall → reset the strip |
| 4 | Route 213, Lapras (Gym 4) | **Rift stones**: push a stone along a surface; pushed off an edge it falls to the surface below as a stepping stone; it can plug a current | currents (runes only if needed for the two surfaces) | 5 | 45-65, two surfaces | a reset sigil returns the stones; no soft-lock |
| 5 | Lost Tower, Spiritomb (Gym 5, two visits) | **Giratina's shadow** (one slow, readable patrol; caught = checkpoint) and **totem-echo pads** (call a calmed totem's power; the 4 ghost acts become player choices) | sigils and runes, lightly | 6 (visit 1 is a ~3 warm-up) | visit 1 ~20, visit 2 55-80 | caught → checkpoint |
| 6 | Arc 3: Aggron (Gym 6) | **Echo self**: a mirrored ghost of you on a paired surface that presses its own sigils | stones or currents | 7 | 80-100 | checkpoint |
| 7 | Arc 3: Mamoswine (Gym 7) | (Arc 3 design: e.g. a faster shadow pattern with currents, or icy currents that don't stop on sigils) | shadow, currents, runes | 8-9 | 100-120 | checkpoint |
| 8 | Arc 3: Kingdra (Gym 8) | finale: every mechanic in play | all | 10 | 120+ multi-stage | checkpoint |

Scope of this build: rifts 1-5, plus engine support for all mechanics including the echo self, so the Arc 3 rifts can
use them when Arc 3 is built. Rifts 6-8 are design targets only for now.

Totem echoes. In the Lost Tower the scripted ghost acts become **player-used**: on echo pads you call a calmed totem's
power (Hitmonlee breaks a crystal, Vespiquen lights hidden tiles, Lapras lifts sunk stones, Skarmory carries you over a
gap). The story beats stay; which pad and in what order is the puzzle. Keep it readable, as a recap of Arc 2, not a
trap.

Difficulty bar per rift: hit the step range above, and include at least one non-obvious move from rift 3 on (a
wrong-looking step that is right). No dead ends without a visible reset. Cyrus (or Ruth's voice in the Resonator) gives
a hint after two falls. Lower rifts must stay easy: if the solver's optimal length or branching is above the row's
range, simplify.

## 3. Engine work (new code in `src/overlay009/`, data-driven)

Put the code in a new file, `src/overlay009/dw_puzzle.c` + `include/overlay009/dw_puzzle.h`, called from the existing
step/frame/fall hooks. Keep `ov9_02249960.c` edits to hook calls only. Each map's puzzle data goes in
`src/overlay009/dw_puzzle_<map>.c` (tables only).

| Module | What it does | Notes |
|---|---|---|
| Tile state | Per-map runtime overrides keyed by surface (attr id) and tile: SOLID / VOID (step = fall) / BLOCKED. Consulted by the walk check and the step hook. | Must also cover the floor plane (permissions) for floor puzzles |
| Groups | A group = tiles + ghost-prop group, on or off. Fades props in step with walkability (the honeycomb rule: holds exactly while drawn) | |
| Sigils | Tile triggers: toggle, set, momentary (held while stood on), reset. Sound and flash | |
| Runes | A tile that changes surface in place with the existing surface-change camera and rotation | Reuse the jump-point surface change |
| Currents | Forced movement in a direction until blocked or off-current; arrows as ghost props or decals | Input locked during the slide |
| Stones | DW object pushed along a surface grid. Falls to the surface below at an edge and becomes a SOLID tile there; can sit on a current tile to block it | Objects on walls hang the game if still loaded at the exit warp (README). Unload on exit |
| Shadow | Patrol actor on a beat (pattern table); overlap = caught → checkpoint | Art: Giratina's existing shadow sprite |
| Echo | Mirror actor that replays the player's moves mirrored on a paired surface; its own sigil presses | |
| Checkpoints and reset | Per-map checkpoint tiles. A fall or catch restores the player and puzzle state to the last checkpoint. Puzzle state survives the fall (today a fall reloads the map) | Lost Tower once-only flags must keep working (fix2-lost) |
| Debug export | A `gDwPuzzleDebug` struct in the xMAP: map, surface, player tile, group bits, stone positions, shadow phase, checkpoint, fall count | For the harness; no cost in release |

Limits: polygons and ghost-prop counts per map stay inside the stock DW budgets (B4F has the most props). Every
walkable tile must be drawn and every VOID tile must look open (the fix2-lost rule). Hard-coded tables must agree
with `tools/distortion_world/*.json`; the builder or a checker enforces it.

## 4. Workstreams (all on `dwpuzzles`, each in its own worktree `/data/repos/dp-wt/dw-<ws>`, branch `dw/<ws>`)

| ws | Owns | Depends on |
|---|---|---|
| `engine-a` | dw_puzzle.c/.h: tile state, groups, sigils, runes, currents, checkpoints and reset, debug export; hook calls in ov9 | - |
| `engine-b` | Stones, shadow, echo, and totem-echo pads (actors) in dw_puzzle_actors.c, built on engine-a's API (start from its header) | engine-a's header |
| `harness` | `tools/distortion_world/emu/`: a DW headless kit (enter any rift at its state, move on any surface with the right key mapping, read `gDwPuzzleDebug`, replay a solution string, fall/catch/reset checks, frame strips) and an offline solver framework (BFS over a puzzle model, solvability + soft-lock proof) | engine-a's debug struct |
| `rift-rp` | Ravaged Path puzzle (#1) | engine-a |
| `rift-ef` | Eterna Forest puzzle (#2) | engine-a |
| `rift-214` | Route 214 puzzle (#3) | engine-a |
| `rift-213` | Route 213 puzzle (#4) | engine-a, engine-b (stones) |
| `rift-lt` | Lost Tower puzzle (#5): shadow + totem-echo pads | engine-a, engine-b |
| `qa` | Final chained playthrough of all 6 rifts from the owner's saves, difficulty review | all |

The rift workstreams design first (layout on the existing geometry, a solver model, solvability and no soft-locks,
the hint text), then implement once the engine lands. Design docs go in `docs/distortion_world/<rift>.md`.

## 5. Process: Muse implements, Codex reviews

- Implementers are Muse Preview agents (`tbh-1015`).
- At each milestone (design, first playable, final), the implementer spawns a **Codex reviewer** on the devserver
  (`harness: codex`, `model: gpt-5.6-sol`, `node_id: devvm37887.nha0.facebook.com`). The reviewer reads the diff and
  the design, builds, runs the headless tests and the solver, and sends back findings. The implementer fixes them and
  asks again, until the reviewer replies APPROVED (at most 4 rounds; anything still open goes in the report).
- Headless proof for every rift:
  - the solver finds a solution and no reachable soft-lock;
  - the emulator replays the solver's solution from the rift entry to the totem;
  - each mechanic gets a fall/catch/reset test;
  - the exit warp and calm values from `docs/arc2/rift_contract.md` are unchanged.
- Regression: the other rifts still complete. Arc 1 seams and the Mawile fight are unchanged. The fix2-lost collision
  audit still passes. `make release` builds.

## 6. Rules

- Build with `make release` only. Don't commit `build/` or ROMs.
- Push with `git -c credential.helper= -c credential.helper='!gh auth git-credential' push` (the default helper has
  no credentials). Only the lead pushes `dwpuzzles`.
- Story text: ASCII, 197 px boxes. Hint lines are short and in character.
- Free flags/vars: take them from `docs/arc2/registry.md` and record what you take there (one block per workstream,
  named `FLAG_DW_<WS>_*`).
- Keep the rift contract: entry (20,12) facing west, exits and calm values as in the table.
- Disk is shared and has filled up before. Keep at most 2 ROM copies per workstream, delete frame dumps once their
  sheets exist, and delete `build/` when done.
