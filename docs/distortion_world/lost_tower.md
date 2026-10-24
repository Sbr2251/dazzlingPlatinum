# DW Lost Tower puzzle (rift #5, Spiritomb, Gym 5)

Difficulty **6/10** (PUZZLE_PLAN.md rev. 2026-10-23, eight-rift curve).
Two visits. Visit 1 is a ~3/10 warm-up (26 steps, Phase 0 unchanged).
Visit 2 is the full climb (solver optimal 53 moves). Lead ruling
2026-10-23: both counts are close enough to the targets (about 20, and
55-80), so the design does not chase the numbers; a first play with
shadow waits, one catch and a reset lands in the 55-80 band.

New mechanics: **Giratina's shadow** (one slow, readable patrol; caught =
back to checkpoint) and **totem-echo pads** (the four scripted ghost acts
become player choices). Combined with **sigils and runes, lightly**: two
plain sigils (a gate sigil, a spur sigil) and one one-way rune (a
recovery route to the V pad, 0 uses on the optimal route).
**No echo self** (moved to Arc 3 Aggron), no currents, no pushed stones
(the Lapras stones stay an engine-a group, as in Phase 0).

Everything is built on the existing geometry: the Arc 1 seams clone's west
wall, the floor, the vein room, the deeper ledge, the stepping stones, the
gap and Cyrus's island. No new surface is added. The west wall is the only
wall (B1F record, attr 29); there is no second wall, so the echo self was
never placeable here, and the one-way rune reuses the west wall as the
rune's upper landing instead.

## Engine: what runs on each visit (engine-b is authoritative)

`docs/distortion_world/actors_design.md` (engine-b) governs the handover:

- **Visit 1 (progress 92): no engine table is registered.** The existing
  scripted ghost acts (Phase 0, `scripts_dw_lost_tower.s` + the ov9 hooks)
  run unchanged. No engine-a table, no actor table.
- **Visit 2 (progress 94): one engine-a table** (`gDwPuzzleLostTowerTable`,
  minProgress 94, maxProgress 95) **plus one engine-b actor table**
  (4 pads + the shadow). The wall's scar/seam are already open in
  Visit 2 via the persistent Phase 0 acts, so the engine-a table
  carries no V1 groups.

Surfaces are explicit (engine-b §2): floor tiles are **GROUND** (base
map terrain, platform index -1), wall tiles are **WEST_WALL**. The
rift tables must carry the surface per tile; engine-a derives it from
coordinates (floor y=1, wall x=11), engine-b takes it explicitly.

Persistent flags: none needed in Phase 1. The block
`FLAG_DW_LT_A..P` (0x0A20-0x0A2F, `docs/arc2/registry.md`) is reserved
for this workstream and unused so far; if Phase 2 needs a persistent
pad-use flag, take the first free letter then. Engine-b reads only the
four existing `FLAG_TOTEM_*_DEFEATED` flags.

## Layout

Coordinates are DW world tiles. Floor is y=1; the west wall is x=11,
y=2..5, z=13..22. `W` = wall tile, `F` = floor tile.

### Floor (y=1). `.` walkable, `#` blocked, `J` jump tile (hop, not a standing tile), `V` VOID fall lip

```
z\x 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33-36 37 38 39 40 41
10  .                 .                                                              (22,10) spur
11  .           V           V V V                                                     fall lips
12  .           .  .  .  .  .  .  .  .           J           J                         entry (20,12)
13  .           .                 .  .                                                  fall lips (20,13)
14  .     J  .  .  .                                                                  ledge, wall-on (12,14)
15  .        .  .  .  .                                                              fall lips (12-15,15)
16  .                                                                                 (10,16-22) west strip
17  .                                                                                 (not a route)
18  .                                                                                 .
19  .                                                                                 .
20  .                                                                                 .
21  .                       X  .                                                     N arm: candle blocks (16,21)
22  .                       .  .  .  .  .  J  J  .  J  J  .  J  J  .  J  J  .  .     ledge, stones, gap
23  .        J  .  .  .  .  .  .                                                     vein room, wall-off (12,23)
24  .                       .  .                                                     spur (16-17,24)
```

Full walkable floor set (from `map_data_677/678`): entry island
(15-22,12), (15,13), (15,11) lip, (19-22,11) lips, (20-21,13) lips,
ledge (12-15,14), (12-15,15) lips, west strip (10,14-24), vein room
(12-17,23), spur (16-17,24), north arm (16-17,21), deeper ledge
(16-20,22), stones (23,26,29,32,22), island (37-41,21-23). Jump tiles:
(12,14) wall-on, (12,23) wall-off, (21-22,22), (24-25,22), (27-28,22),
(30-31,22) stone hops, (25,12), (28,12) unused upper hops.

Persistent object blockers (all modelled in the solver): Cyrus's object
blocks (39,22) (not a floor tile in the model); the Spiritomb blocks
(41,22); Litwick candles block (16,21), (37,21), (41,23), and (13,15),
(15,15) (two candles on VOID lips, so those lips are untraversable).
The candle at (12,19) sits on a non-floor tile. The shard objects sit
on non-floor tiles. Ghost totem / starter objects are script-only
(hidden) and do not block. The (10,16-24) west strip is walkable in
the permissions but unreachable by floor walking; it is not a route.

### West wall (x=11). Rows y=5..2, columns z=13..22. `.` walkable, `#` blocked

```
y5  ##########
y4  ..####....   V pad (11,4,20) on the top row (Visit 2); walk z19-22
y3  ..####....   lit seam (11,3,20-21) (Phase 0, Visit 1 act)
y2  ..........   scar (11,2,14) (Phase 0, Visit 1 act);
                 false seam (11,2,20-21) = fall
```

The wall grid is the stock B1F grid (`lost_tower.json`, attr 29): y4/y3
z15-18 are the wall trees, always blocked; y2 z20-21 are the false seam,
always VOID (step = fall). All other wall walkability changes in
Visit 2 are engine-a groups, never grid edits, so the drawn wall face
still matches the collision (fix2-lost rule).

## Groups, pads, sigils, runes, shadow (Visit 2)

Solver polarity: a group bit means "open" (SOLID). Engine polarities
follow engine-b §6 exactly (Hitmonlee SET group->0, Vespiquen SET
group->1, Lapras SET group->1); plain sigils SET 0.

| Group | Tiles | Engine initial | Fired by (engine SET) | Ghost group / prop |
|---|---|---|---|---|
| G_H2 | (18,22) crystal | ON (crystal present, BLOCKED) | H pad (16,22) SET 0 | 6, one kind-1 crystal prop at (18,1,22) |
| G_V2 | (19,22),(20,22) dark tiles | OFF (dark, BLOCKED) | V pad (11,4,20) SET 1 | 7, light props at (19,1,22),(20,1,22); tiles textured dark in the land data (see below) |
| G_SPUR | (16,24),(17,24) misted spur | ON (mist, BLOCKED) | spur sigil (20,22) SET 0 | 8, two kind-1 mist props at (16,1,24),(17,1,24) |
| G_STONES | (23,22),(26,22),(29,22),(32,22) stones | OFF (sunk, VOID) | L pad (16,24) SET 1 | 4, existing kind-0 props at (23,26,29,32,22) |
| G_GATE | (38,22) aura | ON (aura, BLOCKED) | gate sigil (37,23) SET 0 | 9, one kind-1 aura prop at (38,1,22) |
| G_CARRY | (none - no-op group) | OFF | S pad (32,22) SET 1 | none (engine-b requires every pad to resolve through PressSigil; Skarmory's sigil targets this empty group, and the carry itself is script-driven) |

Ghost-prop groups: existing are 0 (decor), 2 (scar rock, Phase 0),
3 (seam light, Phase 0), 4 (stones). New groups are 6, 7, 8, 9
(5 is unused; 1 is free). Groups 2 and 3 are NOT engine-a groups.
In Visit 1 (no actor table) the Phase 0 hook drives them as in
Phase 0. In Visit 2 the engine-b gating disables the legacy
group-update block entirely, so the completed state is initialised
in the table instead: group 2 hidden (scar shut), group 3 shown
(seam lit). Ghost default-visible mask (one mask for the map; the
Visit 1 hook overrides it every frame, Visit 2 leaves it): groups
0, 3, 6, 8, 9 shown = bits 0,3,6,8,9 = 1 + 8 + 64 + 256 + 512 =
841. Groups 2, 4, 7 start hidden. Fade: engine defaults (33 frames
out, 3 in) for every group with props.

G_STONES off = VOID, not BLOCKED. Hopping onto a sunk stone falls
(the tile is drawn as open mist), so no jump-point suppression glue
is needed: the hop is never suppressed, the landing is VOID. Stones
only ever turn on (SET), and the L pad is at (16,24), unreachable
from a stone tile, so stones can never turn off under the player.

### Totem-echo pads (Visit 2, engine-b §6)

Four pads, exactly `DW_ACTORS_MAX_PADS` = 4: H (16,22, Hitmonlee),
V (11,4,20, Vespiquen), L (16,24, Lapras), S (32,22, Skarmory).
A pad tile **is** an engine-a sigil tile (the sigil entry carries the
target group + set value), but the glue suppresses its auto-fire:
stepping on a pad sets `pendingPad` and returns `PAD_READY`; the
glue skips engine-a's step handling for that step and the rift script
shows the Yes/No prompt. On Yes, `DwActors_ResolvePad` fires the
sigil via `PressSigil` (after the totem gate); on No it resolves with
no effect and the pad is not marked used. One use per load per pad
(`padUsed` bits, restored to the checkpoint snapshot on reset). A pad
tile must not be a checkpoint/rune/current tile: none of the four
is (checkpoints are entry/vein/(16,23)/carry landing; R1 is (17,23)).

- Gating: `ResolvePad` checks `FLAG_TOTEM_*_DEFEATED` first. If the
  flag is clear: no effect, no used bit, `padDenied = TRUE` in debug,
  and the script shows the "the totem has not been calmed" line.
  Denied pads are steppable; the denial is visible, not a silent
  no-op. The solver models denial as the pad doing nothing.
- Cut-in: on a successful Yes, actors return `CUTIN`; the script
  plays the existing Resonator ghost cut-in (same wash as Phase 0).
- Skarmory: `ResolvePad` returns `CARRY_REQUESTED` and sets
  `carryPending`. The script plays the carry with the existing,
  proven Act 4 machinery (floating platform + jump task) and calls
  `DwActors_ConfirmCarryDone()` when it completes. The carry is
  never a tile-by-tile walk over VOID. While `carryPending` is set,
  the shadow does not catch. A fall/reset/exit clears it.

The solver assumes the player answers Yes at every pad (optimal
play). Answering No leaves the pad unused; the player can step on it
again and answer Yes.

### Plain sigils (Visit 2, engine-a, auto-fire, no prompt)

Gate sigil at (37,23) (SET G_GATE off), spur sigil at (20,22) (SET
G_SPUR off: the misted spur south of the vein room clears once the
lane is crossed, which forces the Lapras pad to be a timed backtrack
across the shadow lane rather than a detour on the way in).

### Rune (Visit 2, one, one-way)

R1 at floor (17,23) -> wall (11,4,20), the V pad's tile. Teleport
landing re-enters tile processing, so landing on (11,4,20) fires the
V pad (SET G_V2 on) at once. This is the rune's purpose: a recovery
route to the V pad for a player who took the vein-room route first.
It is not a shortcut (reaching the north arm costs more via the vein
room than via the wall), and it uses 0 times on the optimal route.
In Visit 1 the rune tile (17,23) is east of the shadow wall and
unreachable. The rune tile itself is off the shadow lane, so the rune
is taught with no shadow pressure. Surfaces: (17,23) is GROUND,
(11,4,20) is WEST_WALL.

### Giratina's shadow (Visit 2, engine-b §4)

One lane, authored by `DwActors_MakeShadowLane` from endpoints
(17,22)-(31,22) on GROUND, PINGPONG, **beat 45-60 frames per tile**
(~1.5-2 s per tile). 15 tiles, inside `DW_ACTORS_MAX_SHADOW_TILES`
= 16. Ledge + stones only: the island (carry landing, goal, S pad)
is off-lane, and the lane avoids script tiles (the S pad at (32,22)
is off-lane). The shadow is a MapObject with the wall-of-shadow
sprite (`OBJ_EVENT_GFX_RIFT_ARC2`), `MAP_OBJ_STATUS_18`.

- Advance: the frame hook ticks; every `beatFrames` frames the shadow
  steps one tile (pingpong reverses at the ends). The patrol advances
  during spawn grace and freezes during actor-owned script windows
  (pad prompt, carry, catch).
- Catch: overlap is checked after every shadow advance and after every
  player step (same x, y, z AND surface). On overlap, if grace is 0
  and no script is running: catch effect (Giratina cry, input locked,
  30 frames frozen), then one latched
  `DwPuzzle_RequestCheckpointRespawn`. Catches are suppressed while
  a script is running (pad prompt, carry, Find Cyrus, hint boxes) and
  in the first 30 frames after load (spawn grace). All checkpoints
  and the entry are off-lane, so grace never decides a catch.
- Checkpoint snapshot: pattern index + pingpong direction + beat
  frame counter. A fall or catch restores all of them (canonicalized:
  PATROL, grace = spawn grace, timers 0). So the patrol is
  deterministic from each checkpoint.
- Unload: deleted before any warp; never in the overlay list, so no
  wall-rotation object can hang the exit.

Solver timing: the solver is GEOMETRY-ONLY for the shadow. The
shadow phase is abstracted as a nondeterministic choice: stepping
onto a lane tile yields a safe branch (the player timed it - waiting
for a favourable phase is always available on safe tiles) and a
caught branch (respawn at the checkpoint with its snapshot). The
solver therefore proves (i) reachability assuming favourable timing
and (ii) that EVERY catch lands in a state from which the goal is
still reachable. It does NOT prove a specific frame schedule and
does not model engine-b's deterministic snapshot (pattern index +
direction + beat counter) or its pingpong (which reverses
immediately: pattern period 2*(15-1) = 28 steps, not a duplicated
endpoint period). The timing proof is deferred to the harness:
headless replay of the solver's route against the real beat (45-60
frames/tile) must confirm the crossings are timed as the design
says. Step counts (53) are movement steps; the beat does not change
them. A faster patrol is NOT monotonically harder (it can move away
before the player arrives while a slower one stays), so no
conservative-faster-shadow argument is made.

## Teaching (Visit 2 first meets both new mechanics)

The shadow is taught at its first crossing: CP2 at (16,23) sits
immediately before the lane, the lane is visible from the safe
tiles (16,22) and (17,21), and a catch on the first crossing
respawns at CP2 - two steps back, almost no cost. The pads are
taught safely: the first pad the player meets (V, on the wall) is
off-lane, and the H pad (16,22) is off-lane too; neither is taught
under shadow pressure. Each pad's effect is obvious: stepping on
the H pad breaks the crystal at (18,22), two tiles east on the same
row, visible from the pad; the V pad's lit tiles are seen when the
player reaches the lane (they walk past the lit tiles to cross it).

Pad prompts (Yes/No, script). The prompts are ordered by totem
(Hitmonlee, Vespiquen, Lapras, Skarmory), and the template makes
the Visit 1 -> Visit 2 link: the totem helped through scripted acts
in Visit 1 ("still hums/glows/echoes/beats in the Resonator"), and
now the player calls on it. The Hitmonlee line is the lead's:

```
Hitmonlee's strength still
hums in the Resonator.
Call on it?
```

```
Vespiquen's light still glows
in the Resonator.
Call on it?
```

```
Lapras's song still echoes
in the Resonator.
Call on it?
```

```
Skarmory's wings still beat
in the Resonator.
Call on it?
```

## Visit 1 (state 92, ~3/10): find the vein — Phase 0, unchanged

Entry (20,12) facing west. Goal: step on (13,23) (vein, sets
`FLAG_ARC2_RIFTB_E`), then step on (15,23) (shadow wall), which runs
`Warp MAP_HEADER_ROUTE_209_LOST_TOWER_2F, 0, 7, 8, DIR_EAST` (state
unchanged). All other exits are closed: the shadow-wall object blocks
(16,23). No engine table, no actor table; the scripted ghost acts
run as in Phase 0:

1. Walk the entry island to the ledge (12,14): 10 steps.
2. Jump onto the wall (11,2,13). Wall: (11,2,14) (1).
3. Step on the scar (11,2,14): Hitmonlee's ghost kicks the scar shut
   (act 1). Walk through (11,2,15-18) (4).
4. Step onto the fork (z=19): Vespiquen's ghost lights the true seam
   (act 2). Climb to (11,3,19) (1), cross the lit tiles to (11,3,22)
   (3), descend to (11,2,22) (1), hop off to (12,23) (1). The false
   seam (11,2,20-21) is never stepped on; stepping there falls to
   the entry.
5. Step on (13,23): the vein. Step on (15,23): the exit warp.

26 steps to the exit trigger (24 to the vein). Visit 1 has no engine
checkpoints: a fall always returns the player to the entry, and the
completed act flags persist (Phase 0 semantics). The solver's Visit 1
run models this walk (the act tiles as SET stand-ins with the same
passability effect, falls to the entry with act flags preserved); the
acts themselves are Phase 0 scripts, already proven by the existing
game.

## Visit 2 (state 94, 6/10): the full climb

Entry (20,12). The shadow wall parts (Phase 0 script). Goal: step on
(38,22), which starts the Find Cyrus script, the Spiritomb battle,
the calm (state 95), and the exit warp
`Warp MAP_HEADER_ROUTE_209, 0, 568, 681, DIR_SOUTH`.

Solver-optimal route (53 moves, 0 waits on this phase; see solver output):

1. Entry island -> ledge (12,14) (10), jump onto the wall (1), climb the
   wall's top row: (11,2,13)->(11,2,19) (6), climb to (11,3,19) (1),
   (11,3,19)->(11,3,20) (1), climb to (11,4,20) (1): step on the V pad,
   answer Yes, Vespiquen lights (19,22) and (20,22). Climbing to the
   top row when the goal is east is the visit's non-obvious move.
2. Walk down the wall: (11,4,20)->(11,3,20) (1), (11,3,20)->(11,3,22)
   (2), descend to (11,2,22) (1), hop off to (12,23) (1). Vein room
   (13,23) = CP1 (1).
3. Vein room -> deeper ledge: (14,23),(15,23),(16,23) (3), CP2 at
   (16,23), (16,22) (1): step on the H pad, answer Yes, Hitmonlee
   breaks the crystal at (18,22). (16,22) is just west of the shadow
   lane; the north arm (17,21) is the safe refuge one step away.
4. Cross the lane to (20,22): (17,22),(18,22),(19,22),(20,22) (4).
   Stepping on (20,22) fires the spur sigil: the misted spur (16,24),
   (17,24) clears.
5. Backtrack across the lane to the spur: (19,22),(18,22),(17,22),
   (16,22) (4), (16,23) (1), (16,24) (1): step on the L pad, answer
   Yes, Lapras lifts the stones. Back to the lane: (16,23),(16,22) (2),
   (17,22),(18,22),(19,22),(20,22) (4), timed against the shadow.
   This backtrack is the second shadow crossing.
6. Stones: hop (23,22),(26,22),(29,22),(32,22) (4 hops), timed against
   the shadow.
7. Step on the S pad at (32,22), answer Yes: Skarmory carries the
   player to the island (37,22) = CP3 (1 carry). The island is
   off-lane, so the carry is never caught.
8. Island: step on the gate sigil (37,23) (1) -> (38,23) (1) ->
   (38,22) (1): Find Cyrus, the battle, the calm, the exit.

Order and choice: V must be on before the dark tiles (19,22), H before
the crystal (18,22), the spur sigil before the L pad, the gate sigil
before (38,22). A player who walks the vein room first reaches the
north arm without V on, and uses the one-way rune at (17,23) to get up
to the V pad (a longer route, not a shortcut). Pads are SET and
one-use-per-load, so no pad can be toggled off by mistake; recovery
from a catch is the checkpoint respawn. The shadow is the only time
pressure, and it never blocks a safe tile.

## Checkpoints and reset

Checkpoints are all off the shadow lane, so no checkpoint is ever
stepped on in the same step as a catch, and no catch-before-checkpoint
ordering is needed (Codex round 2). Snapshots are actual state:
stepping on a checkpoint tile snapshots the groups as they are at
that moment (the solver carries the snapshot in its state; there are
no fixed per-checkpoint masks). Re-crossing a checkpoint
re-snapshots it. Engine-b's snapshot also stores the shadow's pattern
index + direction + beat counter and the pad used-bits.

| # | Tile | Reached after |
|---|---|---|
| CP0 | (20,12) entry | entry |
| CP1 | (13,23) vein room | wall |
| CP2 | (16,23) vein room east | wall + vein room |
| CP3 | (37,22) island | Skarmory carry |

A fall (false seam, floor lip, hopping onto a sunk stone) or a catch
restores the player to the last checkpoint with that checkpoint's
snapshot (engine-a restores + respawns, bumps the reset generation;
actors poll it and restore their snapshot), and the shadow restarts
with spawn grace. A checkpoint never shares a tile with a pad, rune,
or current. Puzzle state is RAM-only per the engine; the persistent
once-only flags (fix2-lost: `FLAG_ARC2_RESONATOR_B`,
`FLAG_ARC2_CELESTIC_B/C/D`) are never touched by the puzzle.

Re-entry after a blackout: the totem battle's blackout reloads the map
at the entry state (94). All puzzle groups reset to the initial state,
checkpoints reset to CP0, pad used-bits clear, and the player replays
from the entry. The once-only act flags do not gate the pads: the pads
test `FLAG_TOTEM_*_DEFEATED`, which survive a blackout. The Skarmory
gap must be crossed again.

## Cyrus's hint after two falls

After the second fall or catch in one visit (fall count >= 2, counted
by the engine), the respawn shows one hint box. Ruth's voice in the
Resonator (Cyrus is not in the rift in Visit 1, and is beyond the gap
in Visit 2). ASCII, short lines. Text ids are proposals for Phase 2.

Visit 1 (wall), `DWLostTower_Text_HintWall`:

```
Ruth's voice: Step on the pad,
then walk through what opens.
The low seam is a scar.
```

Visit 2 (deeper), `DWLostTower_Text_HintDeeper`:

```
Ruth's voice: The shadow walks
the stones. Step aside and
let it pass, then cross.
```

A second hint box, only if the player falls twice more (fall count
>= 4), names the loop:

```
Ruth's voice: The rune takes you
up to Vespiquen's pad. Light
the dark tiles, then come down.
```

## Story beats

The story beats stay exactly as in Phase 0, only the trigger changes
from scripted acts to pads (Visit 2):

- Vein (Visit 1): stepping on (13,23) sets `FLAG_ARC2_RIFTB_E`; the
  2.25 call, the exit warp `Warp MAP_HEADER_ROUTE_209_LOST_TOWER_2F,
  0, 7, 8, DIR_EAST`, and the state (92, unchanged) are unchanged.
- Shadow wall: parts at 94 (Phase 0 script, `FLAG_ARC2_RIFTB_D`).
- Cyrus: at (39,22) on the island, behind the gate sigil's tile
  (38,22). Phase 2 changes the Find Cyrus script: it becomes a new
  `ScriptEntry` that starts when the player steps onto (38,22) (step
  hook or coord event), with the initial `ApplyMovement PlayerToCyrus`
  (37,22)->(38,22) REMOVED (the player is already at (38,22)); the
  starter reveal (ShowEmpoleon/Torterra/Infernape), Cyrus's two lines
  (once per save, `FLAG_ARC2_CELESTIC_D`), and the battle are
  unchanged. The carry landing at (37,22) must NOT start Find Cyrus
  (in Phase 0 it did), because the gate is still closed there.
- Spiritomb: the totem battle at the island, calm sets state 95 and
  `FLAG_TOTEM_SPIRITOMB_DEFEATED`, exit warp `Warp
  MAP_HEADER_ROUTE_209, 0, 568, 681, DIR_SOUTH`. No exit warp, calm
  value, entry tile (20,12) facing west, or rift-contract value
  changes.
- Ghost acts: in Visit 1 they run as Phase 0 scripts. In Visit 2 the
  four acts become the pads' effects (the same ghost movements, cries
  and lines, fired by answering Yes on the pad instead of by the step
  hook). The once-per-save act flags keep their meaning (the act's
  line plays once per save); stepping on a pad after its line has
  played still sets the group, without the line. The fallback lines
  for a missing totem stay: the pad is refused (above), so the
  fallback never opens a group.

## Collision vs drawn

- Every group-off tile is drawn as its obstacle: crystal (G_H2,
  ghost group 6, shown when on), misted spur (G_SPUR, group 8,
  shown when on), aura (G_GATE, group 9, shown when on), sunk stones
  (G_STONES, group 4 props hidden, tiles VOID and drawn as open
  mist - hopping onto one falls, which is the correct VOID behaviour).
- G_V2's blocked state is the base drawing: (19,22) and (20,22) are
  textured dark in the land data (the dark tiles), so a blocked dark
  tile is never drawn as open floor; the light props (group 7) show
  when the group is on. Phase 0's seam light (group 3) is unchanged.
- No wall-rotated objects are loaded at the exit warp: the pads, the
  shadow and the gate are engine actors, not map objects. The existing
  ghost totem objects (0x8A-0x8D) are script-only and are hidden
  (`ScrCmd_312`) before any warp, as in Phase 0. The shadow MapObject
  is deleted on exit (engine-b `VisualsExit` / `OnExit`).

## Solver model

`tools/distortion_world/lost_tower_solver.py`: standalone BFS with
the same semantics as the engine-a header + engine-b actors design
(groups, SET sigils, pads as Yes-answered steps, runes, checkpoints
with actual snapshots, VOID falls, shadow phase abstracted,
catch suppressed on pad/carry steps, Visit 1 falls to the entry
with act flags preserved). Results (solver output saved in
`/tmp/dwp/rift-lt/`):
Visit 1: SOLVED, 26 moves (walk model; acts are Phase 0 scripts).
Visit 2: SOLVED, 53 moves. The solver is GEOMETRY-ONLY for shadow
timing (see Shadow): stepping onto a lane tile yields a safe branch
and a caught branch; there is no arriving phase and no phase
branching. Soft-lock proof (`--softlock`, full-graph reverse
reachability under the phase abstraction): Visit 1: 101 reachable
states, 0 dead. Visit 2: 400 reachable states, 0 dead.
Pad refusal (debug, `--refuse <totem>`): refusing Hitmonlee,
Vespiquen, Lapras or Skarmory makes Visit 2 UNSOLVABLE (the pad's
group stays off), which is the refusal working; with all pads working
the player is never stuck. The harness solver
(`tools/distortion_world/emu/solver.py`) replaces it when it lands;
the model must stay in sync with it.

## Open at implementation (Phase 2)

- Rift scripts: the four pad Yes/No prompts + denial line, the
  Skarmory carry script (`CARRY_REQUESTED` -> Act 4 machinery ->
  `ConfirmCarryDone`), the new Find Cyrus `ScriptEntry` from
  (38,22), hint boxes at fall count >= 2 (>= 4 for the second hint).
- `lost_tower.json`: ghost groups 6, 7, 8, 9 + default-visible mask
  841; dark texture for (19,22),(20,22) in the land data.
- Engine-a table (Visit 2 only, progress 94-95) + engine-b actor
  table (Visit 2 only, 4 pads + shadow lane (17,22)-(31,22), beat
  45-60) in `dw_puzzle_lost_tower.c`.
- Engine-a table: the pad tiles are sigil entries (target group +
  set value) with auto-fire suppressed on PAD_READY steps (glue).
