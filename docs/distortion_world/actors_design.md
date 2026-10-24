# DW puzzle actors: design (engine-b)

Owner: workstream `engine-b`. Actors: rift stones, Giratina's shadow, the echo self, totem-echo pads.
Implementation: `src/overlay009/dw_puzzle_actors.c` + `include/overlay009/dw_puzzle_actors.h`,
called from the existing step/frame/collision hooks (hook calls only; the ov9 glue belongs to
engine-a, except the one frame-hook call and the Lost Tower gating already on this branch).
Depends on engine-a's core API (`include/overlay009/dw_puzzle.h` - the LANDING version, synced
from engine-a's worktree; engine-a's own commit must replace it at merge. `dw_puzzle.c` is still
landing; actors carry weak fallbacks for its symbols, deleted when it lands).

Build order (lead, 2026-10-23; PUZZLE_PLAN section 2 revised, commit a850046d78): stones, shadow
and totem-echo pads first (rift-213 and rift-lt need them); **echo self last** - it has no Arc 2
user, it is for Arc 3's Aggron rift (rift 6). The echo is fully specified and implemented here
(engine support for all mechanics is in scope), but no Arc 2 table uses it.

Flags: the lead assigned the shared block `FLAG_DW_ENGINE_A..P` (0x0A30-0x0A3F) on dwpuzzles
(registry 463c9dd469): engine-a takes A..H, engine-b takes I..P (0x0A38-0x0A3F). Engine-b
currently uses **no** persistent flags (pad state is RAM + checkpoint snapshot; actors read
only the four existing `FLAG_TOTEM_*_DEFEATED` flags). The I..P block is reserved; rename a
`FLAG_UNK_0x0A..` line in generated/vars_flags.txt only if a use appears.

Codex reviews: round 1 (11 findings, all addressed), round 2 (8 findings: the landing-API
divergence + 7 implementation issues, all addressed in this revision - see section 10).
Section 9 is acceptance criteria, not completed proof.

## 1. What the DW code already gives us (findings from `ov9_02249960.c`)

- **DW overlay objects** (`UnkStruct_ov9_0224EF30` tables, e.g. `sArc2DwRoute213Objects`,
  `sArc2DwLostTowerObjects`): `{condition, value, useRotation, rotationDeg, ObjectEvent}`.
  Spawned on map load by `ov9_0224F048` into a **19-slot** list (`DistWorldSystem.unk_1C64`),
  via `MapObjectMan_AddMapObjectFromHeader`. `useRotation = 1` registers the object with the
  wall-rotation animator (`ov9_0224A390`); the Lost Tower candle comment states the hazard:
  wall objects stand at x=12 in front of the wall face, never use the wall-rotation animation,
  and a wall-animated object still loaded when the exit warp animation runs hangs the game.
  Route 213's Lapras on the ceiling is the one precedent for rotation: `useRotation = 1, 180`.
- **MapObject collision** (`sub_02063F00` in `src/map_object_move.c`): an object blocks
  movement if it shares the destination's x/z **and** its y is within 2 of the mover's y - **unless**
  it has `MAP_OBJ_STATUS_18`. Actor objects are therefore created with `MAP_OBJ_STATUS_18` set:
  resting stones must not intercept the push, landed stones must be steppable, the shadow must
  overlap the player to catch them, and the echo must never obstruct movement.
- **MapObjectManager capacity is 64** (`field_map_change.c`), DW maps have **0** events-file
  objects, and the biggest DW overlay list (Lost Tower) has 20 entries, most conditional or
  script-only. Six dynamic actor objects fit with headroom.
- **Ghost props**: templates come from `tw_arc.narc`, fixed positions, per-group visibility
  (max 24 groups, `GHOST_PROP_GROUP_MAX_COUNT`), driven by `Hide/ShowGhostPropGroup` (static in
  ov9). They cannot be repositioned at runtime, so moving actors are **not** ghost props.
  Actors consume **zero** ghost-prop templates/groups. Props stay owned by engine-a groups /
  rift tables for static scenery (bridges, hidden tiles, sunk stones).
- **Giratina's shadow fly-by** (`ov9_0224E884`, prop kind 20, `Unk_ov9_02252414` table) is a
  one-shot scripted animation over a *fixed* table: it cannot patrol, cannot be retargeted, and
  its table cannot gain entries without editing ov9. The patrol shadow therefore does **not**
  reuse that prop. It is a MapObject with the wall-of-shadow sprite (`OBJ_EVENT_GFX_RIFT_ARC2`,
  already used for the Lost Tower wall of shadow), stepping tile-by-tile on a beat.
- **Lost Tower ghost acts** (set-tower): scripted, once-per-save, driven by map-local vars and
  the totem flags; the Resonator ghost wash palettes live in `sLostTowerGhostPalettes` (precomputed
  from `FieldMoves_ApplyResonatorGhostPalette`). Totem-echo pads reuse that wash for the cut-in
  (section 6): the pad's ghost cut-in is the same wash, not a new palette.
- **Step hook** (`ov9_0224A71C`): per-step, DW world coords (x,y,z), runs **after** movement,
  exposes only the current tile. **Frame hook** (`Arc2Dw_HandleFrame` via `ov9_02249EDC`): per
  field frame. The step hook alone cannot implement pushes (section 3): actors need the pre-move
  hook in section 7.

## 2. Coordinates and surfaces

**Surfaces are explicit, never derived** (engine-a: `(x, y, z)` alone does NOT identify a tile -
a wall and a ceiling can share one; the B4F wall->ceiling transfers sit on the same tile).
Every actor tile carries its surface (`DW_ACTOR_SURFACE_*` = `DwPuzzleSurface`: FLOOR 0,
WEST_WALL 1, EAST_WALL 2, CEILING 3, GROUND 4, ANY 0xFF), and every entry point takes the
player's surface. The core never derives a surface from coordinates.

FLOOR and GROUND are different surfaces: FLOOR (0) is a *floating* floor platform, walked via
its tw_arc_attr grid; GROUND (4) is base map terrain (ov9 kind INVALID, platform index -1,
avatar distortion ACTIVE), walked via terrain collision. A stone landing on base ground
carries surface GROUND; a stone on a floating platform carries FLOOR. Table authors must get
this right: the landing tile's surface is part of the table, and a wrong surface resolves
against the wrong grid.

Tile queries go through engine-a's `DwPuzzle_QueryTile(fs, x, y, z, surface)` (see section 7
for the DEFAULT rule): `SOLID` = walkable, `BLOCKED` = impassable, `VOID` = step = fall,
`DEFAULT` = resolved by the stock grid on the queried surface, and **treated as BLOCKED for
tiles on any surface other than the player's current one** (the ROM glue compares against
`gDwPuzzleDebug.surface`). Consequence for rift authors: every tile an actor can occupy on a
surface other than the player's must have an explicit engine-a state (group tile or explicit
override); DEFAULT tiles are only resolved on the player's current surface. For GROUND,
there is no platform grid and no reachable stock-terrain query from actors, so a DEFAULT
ground tile reads BLOCKED (fail closed): rift tables must give explicit states for ground
actor tiles.

## 3. Rift stones

State per stone: `tile` (with surface), `state` (RESTING, FALLING with a frame timer + landing
tile with surface, LANDED), `fallLanding`. Max `DW_ACTORS_MAX_STONES = 4` per map. A stone's
surface changes when it falls (wall -> the landing surface).

Actor tiles (engine-a `DwPuzzle_SetActorTile`, index-keyed, state-bearing) are the ONLY way
stones affect walkability - there is no separate override layer, and no base-kind tracking:
- RESTING: actor tile `(tile, surface, BLOCKED, present)`. The walk check sees BLOCKED
  (resolved by `TryPush`); a slide stops before it.
- LANDED: actor tile `(tile, surface, SOLID, present)`. The tile is walkable terrain.
- FALLING: no actor tile (present FALSE). The stone occupies no tile.
`SyncActorTiles` is clear-then-reapply: it clears all actor tiles and re-registers the
present stones, so a stale override can never survive a restore (e.g. LANDED-B -> snapshot
LANDED-A leaves nothing behind). Actor tiles win over groups AND explicit table overrides
(engine-a precedence: actor tiles beat explicit overrides). That is what makes both stone
mechanics work: a LANDED stone's SOLID actor tile beats a VOID explicit override on its
landing tile, and a RESTING stone's BLOCKED actor tile beats a SOLID explicit override on
a current tile it plugs.

- **Push (pre-move).** The glue's collision path calls `DwActors_TryPush(prevTile, curTile)`
  **before** allowing a step onto a stone tile, for **voluntary walking only** - never for
  slides (a slide stops at a stone; it does not push it). `TryPush` on a non-stone tile returns
  TRUE. On a stone tile it computes the unit tile delta; a non-unit delta (jump, diagonal)
  does not push; a step that changes surface never pushes (jump/rune owns it); the push must
  stay in the surface plane (walls move in (y, z), the rest in (x, z)). The push succeeds and
  the stone moves one tile along the delta, unless the target is: another stone (RESTING or
  LANDED), a protected tile (pad, echo sigil, table-listed protected tile, or any landing
  tile - landing tiles are reserved: a stone may only *land* there, never be *pushed* there),
  `BLOCKED`, or `VOID` that is not a designated edge. If the push fails, the step stays
  blocked and the player does not enter the stone tile.
  `TryPush` is the only push entry: the post-step hook never pushes (it cannot - the step
  already happened). As a safety net, if the post-step hook ever finds the player on a RESTING
  stone's tile (glue missed the pre-move call), it pushes the player back to `prevTile` via
  the platform (stock MapObject API) and reports `DW_ACTOR_EVENT_STONE_PUSH_BLOCKED`.
- **Fall.** If the push target is a designated edge tile in the stone's `edges[]` (each edge
  tile carries its landing tile + surface), the stone enters FALLING for
  `DW_STONE_FALL_FRAMES = 12`, then lands: its tile becomes the landing tile (with the
  landing surface), state LANDED, actor tile SOLID. The edge target is still subject to the
  occupancy rules: no stacking on the edge tile, no protected edge tile, and no landing clash
  (another stone LANDED at the landing tile, or FALLING toward it, blocks the fall). The
  stone's MapObject is hidden during FALLING (it is between surfaces; nothing is drawn in the
  void - collision-vs-drawn rule) and repositioned at the landing tile on landing.
- **Occupancy (three predicates, not one).** RESTING, LANDED and FALLING stones behave differently:
  - RESTING: occupies its tile. `DwActors_IsStoneAt` is TRUE. Actor tile BLOCKED. Pushable.
  - LANDED: is terrain, not an obstacle. `DwActors_IsStoneAt` is FALSE, actor tile SOLID, so
    the player (and the echo) can stand on it. It is **not** pushable: stepping onto it is a
    normal walk onto SOLID terrain.
  - FALLING: occupies **no** tile (between surfaces). `DwActors_IsStoneAt` is FALSE, no actor
    tile, MapObject hidden.
  - Currents: a RESTING stone on a current tile plugs the current via its BLOCKED actor tile.
    A LANDED stone never sits on a current tile (table rule: landing tiles are never current tiles).
- **Landing tiles (reserved).** Each landing tile (+ surface) belongs to at most one stone; it
  must not be in any group, and must not be a sigil, pad, checkpoint, current, or rune tile.
  It MAY carry an explicit VOID override - this is the preferred way to make a gap landing a
  fall before the stone lands, with no map-data base-kind change: VOID before landing (no
  actor tile yet), SOLID once the stone lands (the LANDED actor tile beats the VOID
  override), VOID again when the actor tile is cleared (e.g. a reset restores a snapshot
  without that LANDED stone). An explicit override on a landing tile, if present, must be
  VOID only - a SOLID/BLOCKED override would make the gap walkable/blocked before landing
  and would come back when the actor tile clears. Without an explicit override, the tile's
  base kind decides: VOID (a gap the stone plugs) or WALKABLE (stock floor, no fall before
  landing). A stone can never land outside the map: falls only happen at designated edges
  with designated landings. Clearing a LANDED stone removes its actor tile (present FALSE),
  which restores whatever the tile resolves to without it (explicit VOID override if present,
  else base kind) - no base-kind bookkeeping.
- **Reset.** The reset path is engine-a's: a fall, a catch, or a RESET sigil bumps
  `gDwPuzzleDebug.resetGeneration`, and actors restore their **checkpoint snapshot** (section 7).
  Groups and stones therefore restore together to one consistent, previously-occupied state (the
  player reached that checkpoint with those stones, so the reset sigil is reachable from it).
  This is a deliberate deviation from the original brief ("reset sigil returns stones to start"):
  mixed restore (groups to checkpoint, stones to start) is a state no solver can model and no
  player has occupied. `DwActors_ResetStones()` still exists for tables that explicitly want a
  to-start reset: stones to `startTile`, actor tiles re-registered - but it is not the default
  reset path and it does not touch the checkpoint snapshot.
- **Mid-fall snapshots.** A checkpoint can be reached while a stone is FALLING (the player walks
  on while the stone drops). The snapshot therefore stores the full stone state: tile, surface,
  state, fall timer, landing tile. On restore a FALLING stone resumes its timer (it completes
  the fall after the restore); a LANDED stone re-registers its SOLID actor tile.
- **No soft-lock (by construction + table validation).** Push-block rules make these invariants
  hold for every table: (a) a stone can never occupy a checkpoint tile, a pad, a sigil, a
  landing tile, or the reset-sigil tile, so the reset path is never stone-blocked; (b) a stone
  can only fall at a designated edge with a designated landing, and never into a landing clash;
  (c) the checkpoint snapshot is a previously-occupied state. The rift table must still pass
  the offline solver check (harness workstream) that from every reachable stone configuration
  either the goal is reachable or the reset sigil is reachable - the actors code enforces (a)
  and (b); (c) is a table property.
- **Table sanitising.** `DwActors_Init` copies the table and clamps every count to its maximum
  (stones, edges, shadow tiles, echo sigils, pads, protected) and `beatFrames` to >= 1, so a
  malformed external table can never overrun the fixed arrays. It does NOT inspect engine-a
  table overrides (it has no access to them), so nothing in code rejects an override on a
  landing tile - the VOID-only rule above is enforced by the table validator (section 10).

Visual: one MapObject per stone, `OBJ_EVENT_GFX_STRENGTH_BOULDER`, movement NONE, no script,
height calculation disabled, `MAP_OBJ_STATUS_18` (non-colliding), `useRotation = 0`. On a wall it
stands one tile in front of the face (x=12 / x=48, y = tile y). On the ceiling it stands at the
ceiling tile (y=10); the boulder sprite is near-symmetric, so no rotation animation is registered
(rotation is the hang hazard; a static unrotated sprite is the safe choice). A LANDED stone keeps
its MapObject *and* the tile is SOLID: the sprite is the drawn proof of the SOLID tile
(collision-vs-drawn rule).

## 4. Giratina's shadow

Pattern table per map: `{ tiles[] (tile + surface, in patrol order), beatFrames, pingpong }`.
Max `DW_ACTORS_MAX_SHADOW_TILES = 16`, beat `>= 4` frames.

**Authoring (lead: the Lost Tower shadow is "one slow, readable patrol").** The common case is
a straight lane, so tables do not write tile lists by hand: a lane is authored as
`DwActors_MakeShadowLane(&def, startTile, endTile, beatFrames)` - two endpoints on one surface
plus a beat - and the actors code expands it to the tile list (inclusive, one tile a step,
PINGPONG). The lane must lie on the shared surface (wall surfaces: y- or z-move with
start/end y in [2,9]; floor/ground/ceiling: x- or z-move) and must not cross a seam corner.
A full explicit tile list is still available for Arc 3 (Mamoswine's faster pattern), but it is
the exception. Slow means slow: the Lost Tower lane uses **beat 45-60 frames** (~1.5-2 s per
tile), exactly **one** lane, and the lane tiles are all on one surface (no surface changes
mid-patrol). A faster beat (< 30 frames) is rejected by the table validator for Arc 2 tables -
it is an Arc 3 opt-in, not a silent default. The beat is the whole difficulty knob.
Table rule: shadow lane tiles must avoid script/cutscene tiles (entry, checkpoint, totem,
talk spots) as defence in depth - the core also suppresses catches while a script is
running (ScriptManager active-context count) and freezes the patrol during actor-owned
script windows (pad prompt, carry, catch).

- **Advance.** The frame hook ticks a frame counter; every `beatFrames` frames the shadow steps to
  the next pattern tile (pingpong reverses at the ends; loop wraps). Movement is stepwise, one
  tile per beat - the beat is the readable timing the player plays against. The patrol advances
  during spawn grace (grace suppresses catching, not movement) and freezes during actor-owned
  script windows (pad prompt pending, Skarmory carry pending, catch freeze).
- **Catch.** Overlap is checked after every shadow advance **and** after every player step:
  shadow tile == player tile (same x, y, z AND surface). On overlap, if grace is 0 and no
  script is running: state CAUGHT, `caughtCount++`, the catch effect (Giratina cry, input
  locked), 30 frames frozen, then the catch requests engine-a's checkpoint respawn
  (`DwPuzzle_RequestCheckpointRespawn`) exactly once (latched). Engine-a restores the puzzle
  and respawns the player, bumps the reset generation, and the actors' poll restores the
  checkpoint snapshot (input unlocked there). If engine-a never restores (e.g. its
  implementation is absent), a 60-frame watchdog self-heals: `OnFallReset` runs anyway, so
  the player is never frozen forever. The shadow never catches during a pending Skarmory
  carry, during a script, or in the first 30 frames after load (spawn grace). If grace
  expires while the player is standing on the shadow's tile, the catch fires on the next
  check - the player had 30 frames to move.
- **Checkpoint snapshot (deterministic replay).** The snapshot stores the pattern index **plus**
  the pingpong direction and the beat frame counter - a tile index alone does not determine
  the next step. A fall or catch restores all of them (canonicalized: state PATROL, grace =
  spawn grace, caught timer 0, request latch cleared), so the patrol is deterministic from
  each checkpoint (no RNG, no wall-clock dependence - the harness can replay it).
- **Unload.** `DwActors_OnExit` deletes the shadow MapObject before any warp; the shadow is never
  in the DW overlay object list, so there is no wall-rotation object to hang the exit.

Visual: one MapObject, `OBJ_EVENT_GFX_RIFT_ARC2`, movement NONE, no script,
`MAP_OBJ_STATUS_18`. Deliberately **not** the Giratina sprite: the shadow is a shadow, and the
RIFT_ARC2 blob is the existing shadow sprite already used on the Lost Tower wall of shadow.

## 5. Echo self (LAST - Arc 3 Aggron rift, rift 6; no Arc 2 user)

Paired-surface table per map: `{ playerSurface, echoSurface, echoAxis, echoValue, mirrorAxis,
mirrorMin, mirrorMax, echo sigil tiles[] }`.

- **Desired vs actual.** The echo's *desired* tile is a pure function of the player's tile:
  start from the player tile, set the echo surface and its fixed coordinate
  (`echoAxis`/`echoValue`: the wall's x, the ceiling/floor's y), and mirror the mirror axis in
  `[mirrorMin, mirrorMax]` (`IDENTITY` = no mirroring, for floor <-> ceiling at the same x,z).
  The echo's *actual* tile is: desired, if desired is enterable (engine-a tile query: not VOID,
  not BLOCKED, no RESTING stone, not the player's tile) - otherwise the echo is **hidden**
  (not left at its last tile). A hidden echo is readable: the player sees the echo cannot go
  there. When desired becomes enterable again, the echo reappears *at desired* - it may
  teleport across tiles; it is a ghost, and teleporting is more truthful than walking a stale
  path. On first activation with an unenterable desired tile, the echo starts hidden (there is
  no "previous tile").
- **Move.** On each player step the echo recomputes. It is only shown while the player's
  surface equals the table's `playerSurface`; otherwise it hides (it does not follow across
  surfaces - that would need a second mapping). A tile the echo cannot enter blocks the echo
  but not the player.
- **Echo sigils.** The table lists echo sigil tiles (tile + surface). They are engine-a
  sigils: when the echo *enters* one, actors call `DwPuzzle_PressSigil(tile, surface,
  OCCUPANT_ECHO)` - the same press/release the player step hook does, with per-occupant
  momentary tracking. Fire only when the echo's actual tile **changes** onto a sigil tile
  (track the previous tile): standing on one while the player steps elsewhere does not refire,
  and a hidden-to-appearing transition onto a sigil tile does fire. When the echo hides, its
  momentary holds are released (`DwPuzzle_ReleaseSigils(ECHO)`); on departure (`OnExit`) they
  are released too; on a checkpoint restore engine-a clears momentary holders, so the echo
  re-presses after the restore. On every visible echo move the core releases the echo's
  momentary holds first (`ReleaseSigils(ECHO)`) and then optionally presses the destination:
  `PressSigil` releases holds elsewhere when pressing a new sigil, but a move onto a
  NON-sigil tile releases nothing, so without this the old momentary group would stay held
  forever. Echo sigil presses are counted in debug (`echoSigilPresses`), and only presses
  that actually fired count (a missing sigil is a table error). The echo never triggers pads,
  currents, runes, or falls. Note: if the player steps on an echo-sigil tile, engine-a fires
  it as PLAYER (same group effect) - echo sigils are shared sigils, pressed by either
  occupant.
- **Checkpoint.** The echo has no persistent position: it is recomputed every player step, so
  the snapshot stores nothing for it. The echo's tile is never restored from a snapshot - the
  next player step recomputes it, so it can never disagree with the player.
- **Mirror/echo-axis rule:** `mirrorAxis` must differ from `echoAxis` (mirroring applies after
  the fixed coordinate; mirroring the fixed axis would silently overwrite it).

Visual: one MapObject, graphics copied from the player's MapObject at spawn
(`MapObject_GetGraphicsID`), movement NONE, no script, height calculation disabled,
`MAP_OBJ_STATUS_18`. A solid copy is deliberate: the player must read the echo's tile at a
glance; translucency would hide it. If the graphics copy ever fails, the echo is still fully
logical (its tile is in debug).

## 6. Totem-echo pads and the Lost Tower visits

A pad is a tile carrying a `DwActorPadDef` entry: `{ tile (with surface), totem (HITMONLEE /
VESPIQUEN / LAPRAS / SKARMORY) }`. The pad tile **is** an engine-a sigil tile: the sigil entry
in `DwPuzzleTable.sigils` carries the target group + set value (TOGGLE/SET; the Skarmory pad's
sigil targets a no-op group with no tiles, since the carry is script-driven). Pads are
player-only, one use per load per pad (`padUsed` bits in debug); a fall/catch/reset restores
the used bits to the checkpoint snapshot, so a pad spent before a fall is usable again after
the reset (consistent with puzzle state restoring to the checkpoint). A **denied** pad (totem
not yet calmed, or no sigil at the pad tile - a table error) is explicitly **not** marked used.

- **Prompt.** When the player steps onto a pad tile, actors set `pendingPad` (debug + state)
  and return event `DW_ACTOR_EVENT_PAD_READY` to the step hook. The glue **must** skip
  engine-a's step handling for that step (otherwise `DwPuzzle_HandleStep` would fire the pad's
  sigil immediately, bypassing the Yes/No prompt and the totem gate). The rift script shows
  the Yes/No prompt (standard script Yes/No) and, on Yes, calls `DwActors_ResolvePad(padIndex,
  TRUE)`; on No it calls `DwActors_ResolvePad(padIndex, FALSE)`. The prompt text and the
  script live in the rift workstream's scripts; actors own only the *resolution*. This keeps
  the menu in the script engine, where Yes/No already works, instead of building a second
  menu path in C. A pad tile must not also be a checkpoint/rune/current tile (the suppression
  skips engine-a's whole step handling for a PAD_READY step).
- **Resolution (return value).** `DwActors_ResolvePad` returns a `DwActorEvent`: `NONE` (No, or
  denied, or stale pad index, or no sigil at the pad tile), `CUTIN` (Yes + calmed: the script
  should play the Resonator ghost cut-in; the totem id is read with
  `DwActors_TakePendingCutin()`, which clears it), or `CARRY_REQUESTED` (Yes + calmed +
  Skarmory). A call for a pad index other than `pendingPad` is ignored (stale script answer)
  and leaves `pendingPad` set.
- **Gating.** Resolution checks the totem flag first: `FLAG_TOTEM_HITMONLEE_DEFEATED` /
  `FLAG_TOTEM_VESPIQUEN_DEFEATED` / `FLAG_TOTEM_LAPRAS_DEFEATED` / `FLAG_TOTEM_SKARMORY_DEFEATED`.
  If the flag is clear: no effect, no used bit, `padDenied = TRUE` in debug (the script shows
  the "the totem has not been calmed" line). Pads for uncalmed totems are still *steppable* - the
  denial is visible, not a silent no-op.
- **Effects** (all via `DwPuzzle_PressSigil` as occupant PLAYER; actors never touch collision):
  - Hitmonlee: the pad's sigil is SET group -> 0 - a BLOCKED group (a crystal) turns off.
  - Vespiquen: the pad's sigil is SET group -> 1 - hidden tiles are shown (group on).
  - Lapras: the pad's sigil is SET group -> 1 with the group being a SOLID group - sunk stones
    are lifted (their tiles become SOLID + drawn). The sigil entry carries the direction, so
    the same code serves all three; the totem only selects the table entry.
  - Skarmory: **the carry is the rift script's job.** `ResolvePad` returns `CARRY_REQUESTED`
    and sets `carryPending = padIndex`. The script plays the carry with the existing, proven
    Lost Tower Act 4 machinery (floating platform + jump task) - actors never step the player
    tile-by-tile over VOID, so there is no carry transaction that can strand the player in a
    fall/current/rune state. The script calls `DwActors_ConfirmCarryDone()` when the carry
    completes (clears `carryPending`); a fall/reset/exit clears it too. While `carryPending`
    is set, the shadow does not catch (the script owns the player's input during the carry)
    and the pad is already marked used. One reset destination: a reset during a pending carry
    restores the checkpoint snapshot (player to checkpoint via engine-a; `carryPending` cleared).
- **Resonator ghost cut-in.** On a successful Yes resolution, actors set the pending cut-in
  (totem id) and return `CUTIN`; the rift script plays the existing Resonator cut-in (the same
  wash as section 1, `FieldMoves_ApplyResonatorGhostPalette`). No new palette code is added;
  where the script cannot play it, the effect still applies (cut-in is cosmetic).
- **Lost Tower visits.** Visit 1 (progress 92) is a ~3 warm-up: **no actor table is registered**,
  and the existing scripted ghost acts (ov9 + `scripts_dw_lost_tower.s`) run unchanged. Visit 2
  (progress 94) registers the actor table: the shadow patrol + the four totem-echo pads (the
  four ghost acts become player choices, a readable recap of Arc 2, not a trap). The handover
  is automatic and backward-compatible: `DwActors_IsActive()` gates the old behaviour in ov9 -
  when no actor table is registered (today, and on visit 1), the old frame/step handlers run
  exactly as before (group ownership + Hitmonlee/Vespiquen/Lapras/Skarmory act triggers); the
  moment a table registers (visit 2), the old group ownership and act triggers step aside and
  the pads own the groups. The false seam still always drops the player (terrain, not an act).
  Persistent once-per-save act flags stay owned by the scripts/ov9 as today - actors read only
  the four `FLAG_TOTEM_*_DEFEATED` flags and keep pad state per-load (snapshot-restored). If the
  player blacks out on visit 2, the map reloads with the puzzle at its initial state (engine-a's
  RAM-only rule) and the pads are usable again; the Skarmory gap must be crossed again. The
  Lapras group's initial state on a fresh visit-2 entry is the rift table's `initialOn`, not a
  persistent flag - reconstructing "stones already up" across blackouts is rift-lt's table
  choice, not actors'. Skarmory's carry still runs on every visit that needs it (the gap is the
  only way across), via the script.

## 7. Engine-a contract (landing API; no requested additions)

All actor needs are covered by the landing API plus existing stock MapObject APIs (player
reposition / movement pause). There are **no** requested engine-a additions.

Published API used (actors `#include "overlay009/dw_puzzle.h"`):

| Use | Call |
|---|---|
| Stone occupancy / current plugging / landed SOLID | `DwPuzzle_SetActorTile(index, x, y, z, surface, state, present)`, `DwPuzzle_ClearActorTiles()` |
| Tile queries | `DwPuzzle_QueryTile(fs, x, y, z, surface)` (see DEFAULT rule below) |
| Pad + echo-sigil effects | `DwPuzzle_PressSigil(fs, x, y, z, surface, occupant)` (PLAYER / ECHO) |
| Echo momentary release | `DwPuzzle_ReleaseSigils(fs, occupant)` |
| Shadow catch | `DwPuzzle_RequestCheckpointRespawn(fs)` (engine-a restores + respawns, bumps `resetGeneration`) |
| Reset detection | actors poll `gDwPuzzleDebug.resetGeneration` (platform callback) and restore the checkpoint snapshot when it changes |
| Debug export | actors sync their slice into `gDwPuzzleDebug` (`stones[]`, `stoneCount`, `shadowPhase`, `shadow` ActorPos, `echo` ActorPos - engine-a zeroes these; engine-b writes them) |
| Directions | actors work with tile deltas; `DwPuzzle_DirDelta` is for the solver/harness, not the core |

DEFAULT rule (platform `tileAt`): `SOLID` -> SOLID, `BLOCKED` -> BLOCKED, `VOID` -> VOID,
`DEFAULT` -> if the queried surface is the player's current surface
(`gDwPuzzleDebug.surface`, refreshed by engine-a's hooks) and is not GROUND:
`DistWorld_CheckCollisionOnCurrentFloatingPlatform` (colliding -> BLOCKED, else WALKABLE);
otherwise -> BLOCKED (fail closed: GROUND has no platform grid and no reachable
stock-terrain query, and cross-surface tiles need explicit engine-a state per section 2).

**Weak fallbacks.** Until `dw_puzzle.c` lands, `dw_puzzle_actors.c` carries
`__attribute__((weak))` fallbacks for the engine-a symbols it uses (`gDwPuzzleDebug`,
`DwPuzzle_QueryTile`, `DwPuzzle_SetActorTile`, `DwPuzzle_ClearActorTiles`,
`DwPuzzle_PressSigil`, `DwPuzzle_ReleaseSigils`, `DwPuzzle_RequestCheckpointRespawn`), so
the ROM still links. Delete the weak block when engine-a's implementation lands - the strong
definitions win.

**Glue contract (ov9 glue, engine-a owns the edits except the two already on this branch: the
frame-hook call and the Lost Tower gating):**

- **Collision (voluntary walking only):** before the walk check blocks a step onto an actor-blocked
  tile, the glue calls `DwActors_TryPush(prevTile, destTile)`; if TRUE, the glue re-queries the
  tile (the stone moved) and allows the step; if FALSE, the step stays blocked. Slides never call
  `TryPush` (a slide stops at a stone). `ov9_0224A71C` is post-step and never pushes.
- **Step:** after the player steps, the glue calls
  `DwActors_HandlePlayerStep(prevTile, curTile)`; on `PAD_READY` the glue **must skip**
  `DwPuzzle_HandleStep` for this step (otherwise the pad's sigil would auto-fire) and start
  the pad script; on `STONE_PUSH_BLOCKED` the player was already put back.
  On `DwPuzzleStepResult.checkpointReached` (engine-a), the glue also calls
  `DwActors_OnCheckpoint()` (snapshot actors).
- **Frame:** the glue calls `DwActors_HandleFrame(playerTile)` (generation poll, shadow advance,
  stone fall timers, catch timing) and `DwActors_SyncDebug()` every frame. **Wired already**
  (the one ov9 hook call on this branch, in `Arc2Dw_HandleFrame`; inert without a table).
- **Visuals:** `DwActors_VisualsInit(fieldSystem)` on map load (idempotent; respawns from core
  state after a battle reload), `DwActors_VisualsUpdate(fieldSystem)` per frame,
  `DwActors_VisualsExit(fieldSystem)` on map unload (deletes objects + NULLs pointers; does NOT
  clear core state), `DwActors_OnExit()` on departure (full teardown). Engine-a's map-load hook
  calls `DwActors_RegisterTable(fieldSystem, table)` (NULL = inert); it must NOT call
  `DwActors_OnExit` / `DwActors_RegisterTable(NULL)` on a same-map reload (fall warp), which
  would destroy the snapshot the generation poll is about to restore.
- **Table registration:** engine-a's map-load hook calls `DwActors_RegisterTable` with the
  rift's actor table (NULL = inert) - or, for the Lost Tower, only when progress is 94
  (section 6); the old acts gate on `DwActors_IsActive()`.

**Platform interface.** The core runs over a `DwActorPlatform` (callbacks + ctx): tileAt,
setActorTile, clearActorTiles, pressSigil, releaseSigils, requestCheckpointRespawn,
setPlayerTile (push-back safety net, stock MapObject API), setInputLocked (catch freeze, stock
MapObject movement-pause API), isScriptRunning (ROM: `ScriptManager` active-context count via
`FieldSystem_GetScriptMemberPtr(SCRIPT_MANAGER_NUM_ACTIVE_CONTEXTS)` - > 0 means a script is
executing. Guarded first: the accessor asserts that the current field task's env is a
ScriptManager, and during idle frames `fieldSystem->task` can be NULL or another task's, so
the glue returns FALSE unless the task exists and its env's first word is the ScriptManager
magic), totemDefeated, getResetGeneration, playCatchEffect. The ROM glue implements it
over `FieldSystem *`; the host test implements it over a fake grid. The core never touches
game state directly, so the host test proves the same code.

**Debug.** `DwActorDebug` (actors header) is the full actor slice for the host test: stone
tiles/surfaces/states, shadow tile/surface/phase/state, echo tile/surface/blocked/sigil
presses, pendingPad, padUsed, padDenied, caughtCount, carryPending, respawnRequests. The ROM
sync writes the engine-a subset into `gDwPuzzleDebug` (stones 0..3 + stoneCount + shadowPhase +
shadow ActorPos + echo ActorPos; -1 coords when hidden/inactive). Engine-a's `fallCount` is
authoritative; actors do not keep their own copy.

## 8. Budgets, exit, fall/reset - the invariant list

- MapObjects: stones <= 4 + shadow 1 + echo 1 = **<= 6** dynamic objects per map, all with
  `MAP_OBJ_STATUS_18`. Ghost props: **0**. Polygons: 6 billboards. All inside the stock DW
  budgets (B4F has the most props; actors add none).
- **Two exit paths, not one.** `DwActors_VisualsExit` (map unload: delete objects, NULL
  pointers, keep core state) runs on every map unload - including same-map fall-warp reloads,
  where the snapshot must survive (the generation poll restores it after the warp).
  `DwActors_OnExit` (departure: full teardown - clear actor tiles, release echo holds, release
  the catch input lock, drop all state) runs only when actually leaving the map / blackout.
  Calling `OnExit` on a fall warp would destroy the snapshot the poll is about to restore;
  calling only `VisualsExit` on departure would leak the actor tiles. The glue must call the
  right one. Both are idempotent.
- `DwActors_OnFallReset`: restores the checkpoint snapshot (full stone state, shadow phase/dir/
  beat-counter/grace, echo reset, pad bits, carry cleared, input unlocked). Called by the
  generation poll, and by the catch watchdog if engine-a never respawns.
  `DwActors_ResetStones` (explicit to-start reset): stones to *start* positions, not the
  checkpoint; not the default reset path.
- A stone, shadow, or echo MapObject is never created for a map with no table; a table with zero
  stones / no shadow / no echo creates no objects for that actor. Tables are data: rift
  workstreams own their tables (`dw_puzzle_<map>.c` per PUZZLE_PLAN section 3), engine-b owns
  the actor code.
- Flag use: actors read the four `FLAG_TOTEM_*_DEFEATED` flags (existing). Engine-b's own
  block `FLAG_DW_ENGINE_I..P` is reserved, currently unused. Pad used-bits live in volatile
  state + checkpoint snapshot, not in save flags, so pads reset exactly like the rest of the
  puzzle (a fall restores the checkpoint's pad bits). No new vars.

## 9. Headless proof (acceptance criteria - to be demonstrated, not yet done)

- The actor core is platform-independent (section 7). The host test
  (`tools/distortion_world/dw_actors_test.c`, compiled with the same `dw_puzzle_actors.c`)
  supplies a fake platform (a grid + group bits + a fake player + a fake reset generation +
  a fake sigil map) and drives a **debug-only test table**: 2 stones (one with a designated
  edge + landing, one push-blocked case), 1 shadow lane (slow beat, pingpong), 1 echo pair +
  echo sigil, 4 pads (one per totem), plus a checkpoint. It asserts: push, push-blocked
  (wall / another stone / protected tile / landing tile / surface change), fall-to-landing +
  SOLID actor tile, falling occupies nothing, landed stone walkable + not pushable + SOLID
  actor tile, reset-generation restore (checkpoint snapshot, incl. mid-fall; generation
  captured at Init), shadow patrol loop + pingpong + direction/beat-counter snapshot, catch +
  checkpoint respawn request (latched, once) + watchdog self-heal, grace behaviour, patrol
  freeze during pad prompt + carry, echo mirror + echo-hidden-on-blocked (not last-valid) +
  echo sigil PressSigil-as-ECHO + fire-on-change + release-on-hide + echo does not block
  player, pad gating (denied when uncalmed, stays unused; missing sigil stays unused; each
  effect when calmed via PressSigil), Skarmory `CARRY_REQUESTED` + confirm + reset clears
  pending carry, checkpoint snapshot/restore, Init clamping of malformed tables, shadow-lane
  validation, exit unloads everything (actor tiles cleared, echo holds released, input
  unlocked). It dumps a frame-by-frame log and the harness renders frame strips from it
  (see `/tmp/dwp/engine-b/`).
- ROM: `make release` builds (weak fallbacks until engine-a's `dw_puzzle.c` lands; delete them at
  merge); boot smoke test shows the DW maps load with actors inert (no table registered) and the
  exit warp path unchanged. ROM-side actor activation awaits engine-a's implementation + a rift
  table; the host test is the actor proof until then.
- Solver: the harness workstream's BFS runs over the same table format (stone positions +
  player tile + shadow phase + pad bits); the actors code's push-block invariants (section 3)
  are the solver's transition rules, so the solver and the code cannot drift apart on stone moves.

## 10. Open

- Engine-a's `dw_puzzle.c` (implementation) + the ov9 glue calls (engine-a owns them): all wired on this branch (frame hook, collision TryPush, step incl. PAD_READY suppression, OnCheckpoint, visuals, RegisterTable, teardown).
- The header on this branch is engine-a's landing version, synced from engine-a's worktree;
  engine-a's own commit must replace it at merge, and the weak-fallback block in
  `dw_puzzle_actors.c` must be deleted then. (Done: merged, header replaced, shim deleted.)
- Rift tables: rift-213 (stones) and rift-lt (visit-2 shadow + pads) - rift workstreams.
- Table validator: beat < 30 rejected for Arc 2, landing-tile reservation, an explicit
  override on a landing tile must be VOID (any other override rejected), landing tiles in
  no group, seam-corner actor tiles rejected, cross-surface actor tiles need explicit
  state, pad tiles need a sigil in the engine-a table, `mirrorAxis` != `echoAxis`, shadow
  lanes off script tiles - harness workstream or a checker.
- The echo self is implemented but untested in-game (no Arc 2 user; Arc 3 Aggron rift).
