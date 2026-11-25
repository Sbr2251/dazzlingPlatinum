# Solaceon Ruins: raid maps (scene 3.4a)

Workstream **raid-maps**, branch `sol/raid-maps` (from `solaceon` at 4577242c2). Contract: `PLAN.md` sections 1-2;
scene text: `screenplay.md` part 4. This file is the hand-off to **raid-scripts** (events, scripts, text) and the
lead (build).

The raid reuses the stock Ruins headers (no new map headers). The vault is Room 7. The generators are in three
dead ends. Everything that switches is an **object event**. The terrain changes are permanent dressing on two chunks
that only one header each uses.

Tools: `tools/solaceon_ruins/` (system `python3`, stdlib only; Blender 5 for previews). Each tool has a dry run,
`--preview DIR` and (if it writes anything) `--write`, and refuses `--write` if a check fails. Stock inputs are read
from git at `BASE_REV = 50482f890`.

| tool | what |
|---|---|
| `ruins.py` | shared constants: room table (header -> matrix -> chunk), paths (one constant per output dir, for the macOS port) |
| `survey.py` | stock survey: headers, chunk sharing, warp graph, tile maps; `--preview DIR --render` dumps and renders every room |
| `placements.py` | **the object-event table**, its gameplay checks, `--json` (paste-ready snippets), `--map` (ASCII) |
| `textures.py` | 11 new textures appended to set 055 |
| `build_dressing.py` | the in-place chunk edits of `map_data_390` (Room 1) and `map_data_405` (Room 7), checks, previews |
| `billboards.py` | preview billboards for the objects; `--concept` draws the concept sheets of the new sprites |
| `blender_cpu.py` | runs `tools/lake_verity/blender_preview.py` on Cycles/CPU (EEVEE renders blank in this session: no Metal shader cache) |
| `concept/*.png` | concept sheets (idle2 64x32) for the sprites this design needs. Not registered. |

```
python3 tools/solaceon_ruins/survey.py --preview "/tmp/Solaceon Update/raid/stock" --render
python3 tools/solaceon_ruins/placements.py            # gameplay checks (all pass)
python3 tools/solaceon_ruins/placements.py --json     # object_events snippets (also below)
python3 tools/solaceon_ruins/textures.py --write      # set 055
python3 tools/solaceon_ruins/build_dressing.py --write
python3 tools/solaceon_ruins/build_dressing.py --preview "/tmp/Solaceon Update/raid"
```

## 1. Survey (stock, at 50482f890)

### Headers, chunks, sharing

All Ruins headers use **area data 56** = props list 52 (build models 469, 470, 479, 480, 516, 76, 589), **texture
set 055**, area light 1. Area 56 is **shared with all of Turnback Cave and the Celestic Town cave**, so set 055 is
append-only. Every room is a 1x1 matrix: chunk (0,0). Event x/z equal chunk-local tiles. `CAMERA_TYPE_CAVE`
(pitch 63.26 deg, distance 574.6), weather 29, music `SEQ_D_02`. Room 5's southeast dead end alone uses
`CAMERA_TYPE_DEFAULT`.

| room | header (`MAP_HEADER_SOLACEON_RUINS_`) | matrix | chunk | chunk shared with | walkable | polys | model B | scripts / text |
|---|---|---|---|---|---|---|---|---|
| MT | `MANIAC_TUNNEL_ROOM` | 25 | 389 | - | 70 | 168 | 8620 | own |
| R1 | `ROOM_1` | 26 | **390** | - | 30 | 293 | 13356 | own (init: first-arrival flag) |
| R1-NW | `ROOM_1_NORTHWEST_DEAD_END` | 35 | 399 | R3-NW, R3-SW, R6-NW | 11 | 75 | 4680 | `scripts_empty`, `TEXT_BANK_JUBILIFE_CITY` |
| R1-SE | `ROOM_1_SOUTHEAST_DEAD_END` | 31 | 395 | R2-SE, R4-SE, R5-SE | 11 | 75 | 4584 | empty |
| R2 | `ROOM_2` | 39 | 403 | - | 30 | 232 | 10724 | own (empty init) |
| R2-NE | `ROOM_2_NORTHEAST_DEAD_END` | 40 | 404 | R6-SE | 11 | 80 | 5148 | empty |
| R2-SE | `ROOM_2_SOUTHEAST_DEAD_END` | 31 | 395 | R1-SE, R4-SE, R5-SE | 11 | 75 | 4584 | empty |
| R3 | `ROOM_3` | 34 | 398 | R6 | 30 | 266 | 12028 | empty |
| R3-NW | `ROOM_3_NORTHWEST_DEAD_END` | 35 | 399 | R1-NW, R3-SW, R6-NW | 11 | 75 | 4680 | empty |
| R3-SW | `ROOM_3_SOUTHWEST_DEAD_END` | 35 | 399 | R1-NW, R3-NW, R6-NW | 11 | 75 | 4680 | empty |
| R4 | `ROOM_4` | 36 | 400 | - | 30 | 209 | 9868 | empty |
| R4-SE | `ROOM_4_SOUTHEAST_DEAD_END` | 31 | 395 | R1-SE, R2-SE, R5-SE | 11 | 75 | 4584 | empty |
| R5 | `ROOM_5` | 30 | 394 | - | 50 | 189 | 9268 | empty |
| R5-SW | `ROOM_5_SOUTHWEST_DEAD_END` | 42 | 406 | - | 14 | 93 | 5604 | empty |
| R5-SE | `ROOM_5_SOUTHEAST_DEADEND` | 31 | 395 | R1-SE, R2-SE, R4-SE | 11 | 75 | 4584 | empty |
| R6 | `ROOM_6` | 34 | 398 | R3 | 30 | 266 | 12028 | empty |
| R6-NW | `ROOM_6_NORTHWEST_DEAD_END` | 35 | 399 | R1-NW, R3-NW, R3-SW | 11 | 75 | 4680 | empty |
| R6-SE | `ROOM_6_SOUTHEAST_DEAD_END` | 40 | 404 | R2-NE | 11 | 80 | 5148 | empty |
| R7 | `ROOM_7` | 41 | **405** | - | 70 | 104 | 5524 | own (empty init) |

Only chunks **390** (Room 1) and **405** (Room 7) are safe to dress, plus 389, 394, 400, 403 and 406, which are
also used by one header each but need nothing. Chunks 395, 398, 399 and 404 serve 2-4 rooms each. No matrix outside
the Ruins references chunks 389-406. `build_dressing.py` re-checks this against every matrix and header.

Room shapes:
- The main rooms are 3-wide corridors (x 4-6, z 2-11). Room 5 is 5 wide (x 2-6) and Room 7 is 7x10 (x 2-8, z 2-11).
- Each main room has stair alcoves at its corners, and those alcoves are the warps. Warp tiles 0x5e / 0x5f are
  stepped off east or west; 0x6f is the south exit.
- The dead ends are 4x3 rooms with a rock (`dun_imped`) in the middle row.
- Floors are at world y 16, and the walls are two bevelled tiers up to h 2. Every stock material is unlit with
  baked shades (205 / 156 / 98).
- Each main room's north wall carries the Unown inscription prop (build model 479 `d20_o03`). Its sign events are
  at (4..6,1), read facing north.

### Warp graph

```
                SOLACEON TOWN  (595,655)                    (597,652)
                      |                                        |
        R1-NW <-(4,3)-+ R1 (5,11) exit                MT (5,11) exit --(8,3)--> MANIAC TUNNEL
        R1-SE <-(6,10)+ R1                            (separate entrance; not part of the raid)
                        R1 (6,3)  --> R2 (4,3)           [rope here before progress 20]
  [A]   R2-NE <-(6,3)-- R2 --(6,10)-> R2-SE
                        R2 (4,10) --> R3 (6,10)
        R3-NW <-(4,3)-- R3 --(4,10)-> R3-SW
                        R3 (6,3)  --> R4 (4,10)
                        R4 --(6,10)-> R4-SE   [B]
                        R4 (4,3)  --> R5 (6,3)
        R5-SW <-(2,10)- R5 --(6,10)-> R5-SE
                        R5 (2,3)  --> R6 (6,3)
  [C]   R6-NW <-(4,3)-- R6 --(6,10)-> R6-SE
                        R6 (4,10) --> R7 (8,3)            THE VAULT
```

The main line is linear: R1 -> R2 -> R3 -> R4 -> R5 -> R6 -> R7. Each dead end has exactly one warp back.

### Stock content that stays

- **Unown:** every Ruins header has an Unown table except Room 1, which has no encounters. The Room 1/7/MT
  inscriptions are `MessageUnown` bg events. The bg events at the rocks in R1-NW (8036), R3-SW (8037) and R5-SE
  (8038) are untouched.
- **R2:** a Hiker at (4,6). His lines are about HM05, which ties to Room 7's ball.
- **R3:** Ruin Maniac Karl, a stock trainer at (5,6) (`LOOK_AROUND`, sight 1). He stays through the raid as "the
  maniac who wouldn't leave". The sight checks include him.
- **R7:** item balls at (4,9) Mind Plate (7095), (6,9) Odd Incense (7096), (4,7) Nugget (7097) and (6,7) **HM05**
  (7098, `scripts_unk_0404.s`). All four stay reachable in every state, which is checked.
- **MT:** the Maniac Tunnel room is untouched. It is a separate town entrance.

Stock renders: `/tmp/Solaceon Update/raid/stock/<room>_top.png`, `<room>_game.png`, and `stock_game_sheet.png`
(all 19 rooms, in the table order).

## 2. Route design

### The run

1. **R1** (excavation). The first entry at 20 plays the Cyrus scene and sets 30. Grunt **SOL_01** guards the stair
   to R2.
2. **R2.** Crates. The stair at (6,3) leads to **R2-NE: generator A**, guarded by **SOL_02**.
3. **R3.** Grunt **SOL_03** watches the corridor (Karl is still here).
4. **R4.** Crates. The stair at (6,10) leads to **R4-SE: generator B**, guarded by **SOL_04**.
5. **R5.** Grunt **SOL_05** guards the stair to R6.
6. **R6.** Crates. The stair at (4,3) leads to **R6-NW: generator C**, guarded by **SOL_06**. The next room is R7.
7. **R7.** The vestibule with Cyrus at the barrier. The barrier drops at 33. Then the vault, **Indra**, Looker
   and the switch.

**Generators: A = R2-NE, B = R4-SE, C = R6-NW**, as story suggested. That puts one in each stretch of the route, so
the player has to go deep (C is beside the vault door), and the order is free.
- The dead ends share chunks with other dead ends, but the generators are object events, so that doesn't matter.
- R5-SW (a unique chunk, 5x3) was the alternative for C. It was rejected so that the last line is cut right beside
  the barrier.

No field powers are needed. Every tile on the route is plain floor reached by walking and stairs, with no rock,
water, ledge or dark-room gating. The Resonator powers (bible section on the Resonator) don't come into it.

### Trainers, Cyrus, Indra, Looker (exact tiles)

`dir` is the facing. `sight` is the eye-contact range (`data[0]`).

| who | room | tile | dir | sight | sees | why it can't be dodged (checked) |
|---|---|---|---|---|---|---|
| `TRAINER_ECLIPSE_GRUNT_SOL_01` (M, RAID_DIGGER) | R1 | (6,2) | S | 3 | (6,3) (6,4) (6,5) | (6,3) is the stair to R2 |
| `TRAINER_ECLIPSE_GRUNT_SOL_02` (F, GEN_A_GUARD) | R2-NE | (5,2) | S | 2 | (5,3) (5,4) | the only way to the generator's talk tile (7,3) is through (5,4) or (5,3) |
| `TRAINER_ECLIPSE_GRUNT_SOL_03` (M, RAID_TECH) | R3 | (4,8) | E | 2 | (5,8) (6,8) | row 8 must be crossed |
| `TRAINER_ECLIPSE_GRUNT_SOL_04` (F, GEN_B_GUARD) | R4-SE | (3,2) | S | 2 | (3,3) (3,4) | talk tile (5,3) only via (3,3)/(3,4) |
| `TRAINER_ECLIPSE_GRUNT_SOL_05` (M, RAID_VAULT_WATCH) | R5 | (2,4) | N | 1 | (2,3) | (2,3) is the stair to R6 |
| `TRAINER_ECLIPSE_GRUNT_SOL_06` (F, GEN_C_GUARD) | R6-NW | (4,2) | S | 2 | (4,3) (4,4) | talk tile (2,3) only via (4,3)/(4,4) |
| `TRAINER_INDRA_SANCTUARY` (scripted battle) | R7 | (5,10) | S | - | - | at the main rack, back to the barrier. Escapes (4,10) -> (3,10) -> (2,10), faces west, hides |
| Cyrus, part 3 | R1 | (4,7) | W | - | - | "a hand on the stone". Only at progress 20, then walks north and hides |
| Cyrus, part 5 | R7 | (5,4) | S | - | - | the vestibule, facing the barrier. Walks in behind the player at 40 |
| Looker, part 6 | R7 | (8,4) | W | - | - | beside the entry stair. Shown at 45-49 and runs in from there |

SOL_07/08 are the town's dig pair (town-scripts), not in the Ruins. No trainer stands on a warp tile, and every
sight line is clear of objects in every state (`placements.py`).

### The generators

Each generator room has the same layout (mirrored for C): the generator in the north-row corner, its rack beside it,
the guard further along the north row facing south, and crates in the corners by the arrival stair.

```
 R2-NE                 R4-SE                 R6-NW
    4 5 6 7               2 3 4 5               2 3 4 5
 2  K T F G            2  K T F G            2  G F T K
 3  W . # .            3  W . # .            3  . # . W
 4  K . . .            4  K . . .            4  . . . K
 G generator  F rack  T guard (faces S)  K crate  # stock rock  W arrival stair
```

- **Talk tile** is the tile south of the generator, facing north: A (7,3), B (5,3), C (2,3). The generator and its
  rack both carry the generator's script, so talking to the rack works too.
- **On / off look** uses twin objects on the same tile:
  - the "on" generator and the lit rack are hidden by `FLAG_SOL_RAID_A/B/C`;
  - the "off" generator and the dark rack are hidden by the room-local `FLAG_UNK_0x0030`. The room's OnTransition
    script sets that flag unless the generator is off and progress is at most 49.
  - The Yes branch of the switch script does `SetFlag FLAG_SOL_RAID_x`, `RemoveObject` (on, lit),
    `ClearFlag FLAG_UNK_0x0030` and `AddObject` (off, dark).

### Room 7: the vault

```
      2 3 4 5 6 7 8           legend
  2   . . s s s . .           s  inscription reading tiles (stock bg events at z 1)
  3   . . . . . . W  <- entry W  entry stair (8,3), from R6
  4   K . . Y . . L           Y  Cyrus (5,4) facing S        L  Looker (8,4), 45-49 only
  5   X X X X X X X           X  the barrier, 7 objects, row z 5 (FLAG_SOL_RAID_D)
  6   F . . . . . F           F  racks (SHARD_FRAME lit / _DARK twin)
  7   F . b . b . F           b  stock item balls (b at (6,7) is HM05)
  8   K . . . . . V           V  violet crystal (lit / dark twin)
  9   K . b . b . K           K  Eclipse crates
 10   R . . I . . .           I  Indra (5,10) facing S; R rubble (2,10) from 45 (tunnel mouth in the west wall)
 11   K . F P F . K           P  the shard-machine plinth (terrain, blocked); the switch is a bg event on it
```

- **The barrier** is 7 object events across row z 5. While it is up, the vestibule (z 2-4) is sealed: the
  inscriptions and the entry stay usable, and the vault is visible through the light. This is checked.
  - Talking to it (or walking into it) runs `TODO_Barrier` ("A wall of violet light...").
  - At 33 `FLAG_SOL_RAID_D` hides all 7. Story allows doing it at once: `RemoveObject` x7 if the player is in R7.
- **Crossing into the vault:** coord events on (2..8,6) set 40 the first time (progress 33 + D).
- **The main rack:** the plinth (5,11) is terrain. The racks at (4,11) and (6,11) flank it.
  - **The switch** is a bg event on the plinth tile (5,11), `BG_EVENT_DIR_SOUTH`, read from (5,10). That is Indra's
    tile until she leaves, so the switch is only reachable from 45.
- **The stockpile** is the racks at (4,11), (6,11), (2,6), (2,7), (8,6) and (8,7), plus the crystal at (8,8). Each
  has a lit object (hidden by `FLAG_SOL_RAID_E`) and a dark twin (hidden by the local `FLAG_UNK_0x0031` until E).
- **The escape:** Indra walks (4,10) -> (3,10) -> (2,10), faces west and is hidden. Set `FLAG_SOL_RAID_G` when she
  is hidden.
  - The tunnel mouth is terrain in the west wall at z 9.5-11.1, so it is visible from the moment the player can see
    the vault: "a fresh tunnel, dark".
  - The cave-in is an object, `OBJ_EVENT_GFX_ROCK_SMASH`, at (2,10). It is hidden by the local `FLAG_UNK_0x0032`
    while progress is below 45. After her exit, show it with screen shake and flash.
  - Its tunnel comes out at the Maniac Tunnel (story; no map change here).
- **Looker** is shown at 45-49 at (8,4) (local `FLAG_UNK_0x0030`). The part 6 script walks him in.

### Outside the raid

| progress | Ruins state |
|---|---|
| < 20 (all of Arc 2 and Arc 3 before the briefing) | **Room 1 and its two dead ends are open; the rest is roped off.** A rope object (`DIG_ROPE`) stands on the stair to R2 (6,3) with the sign text from screenplay Appendix B 7 ("DIG SITE. STAFF ONLY. / The rope has a little bell on it."). Room 1 shows the excavation (scaffold towers, work lights, cables: terrain), which matches band A's "Visitors welcome in the first room". The Maniac Tunnel room, the Room 1 inscription and the Unown of R1-NW / R1-SE work as stock. |
| 20-49 | the raid: all objects per the table below |
| >= 50 | **The Ruins are open and empty.** Raid-scripts sets `FLAG_SOL_RAID_F` together with 50. That hides every grunt, crate, generator, rack and Cyrus. The dark twins are hidden by the OnTransition rules. What stays is the terrain: Room 1's excavation (band E: IP-closed in town; band F: real archaeologists, "mind the rubble") and Room 7 "scorched and empty" (the steel plinth, cables, the violet-scarred floor, the tunnel mouth and the cave-in rubble). Unown, items and the Maniac Tunnel are stock. |

**Why the rope.** It is the only way the Room 7 terrain (plinth, cables, cracks, tunnel) makes sense before the raid,
because nobody can see it. It also means the raid is the first time the player goes deep.

The cost: before 20, Unown are limited to R1-NW and R1-SE. The Room 7 items and the Hiker wait until after the raid.
In band B-D (54-99) the town fence closes the whole Ruins anyway (PLAN), so the rope only matters during the first
visit (44-53).

**Dependency:** the rope is an event. Until raid-scripts adds it, Room 7's dressing is visible to anyone who walks
there.

### Flags and visibility

`hidden_flag` semantics: the object is hidden while the flag is set.

| flag | meaning | set by | hides |
|---|---|---|---|
| `FLAG_SOL_RAID_A/B/C` | generator A/B/C off (story) | the generator scripts | that generator's "on" object and lit rack |
| `FLAG_SOL_RAID_D` | barrier dropped (story) | the 3rd generator (33) | the 7 barrier objects |
| `FLAG_SOL_RAID_E` | racks drained (story) | the switch (part 6) | the lit vault racks and crystal |
| `FLAG_SOL_RAID_F` | **NEW (proposed): raid over** | raid-scripts, with progress 50 before the warp | every grunt, crate, generator body (on look), loose crystal and frame in R2-R7, and Cyrus in R7 |
| `FLAG_SOL_RAID_G` | **NEW (proposed): Indra gone** | when she enters the tunnel (45) | Indra |
| `FLAG_UNK_0x0030/31/32` | map-local (cleared on every map load) | each room's OnTransition script (the Arc 2 depot precedent, `scripts_veilstone_city_galactic_warehouse.s`) | the "inverse" cases below |

Rooms beyond the rope are unreachable before 20, so persistent flags that are still clear then never show anything
to the player there.

OnTransition rules (raid-scripts writes these; `placements.LOCAL_RULES` is the reference):

```
Room 1 (append to the existing _000A, after SetFlag FLAG_FIRST_ARRIVAL_SOLACEON_RUINS):
    SetFlag FLAG_UNK_0x0030                       // Room 1 raid crew (SOL_01, 2 crates)
    SetFlag FLAG_UNK_0x0032                       // Cyrus, part 3
    GoToIfLt VAR_SOLACEON_PROGRESS, 20, R1_End    // rope (0x0031) stays clear = visible
    SetFlag FLAG_UNK_0x0031                       // rope gone from 20
    GoToIfGe VAR_SOLACEON_PROGRESS, 50, R1_End
    ClearFlag FLAG_UNK_0x0030
    GoToIfNe VAR_SOLACEON_PROGRESS, 20, R1_End
    ClearFlag FLAG_UNK_0x0032
R1_End: End

R2-NE / R4-SE / R6-NW (new init scripts; X = A / B / C):
    SetFlag FLAG_UNK_0x0030                       // off generator + dark rack
    GoToIfGe VAR_SOLACEON_PROGRESS, 50, Gen_End
    GoToIfUnset FLAG_SOL_RAID_X, Gen_End
    ClearFlag FLAG_UNK_0x0030
Gen_End: End

Room 7 (the stock init archive is empty: add an OnTransition entry):
    SetFlag FLAG_UNK_0x0030                       // Looker
    SetFlag FLAG_UNK_0x0031                       // dark racks / crystal
    SetFlag FLAG_UNK_0x0032                       // rubble
    GoToIfLt VAR_SOLACEON_PROGRESS, 45, R7_End
    ClearFlag FLAG_UNK_0x0032
    GoToIfGe VAR_SOLACEON_PROGRESS, 50, R7_End
    ClearFlag FLAG_UNK_0x0030
    GoToIfUnset FLAG_SOL_RAID_E, R7_End
    ClearFlag FLAG_UNK_0x0031
R7_End: End
```

`placements.py` simulates the 9 story states (0, 20, 30, 31, 33, 40, 45, 45+E, 50) and checks every one:
- no two visible objects share a tile;
- the twins are complementary;
- trainer sight lines are clear;
- every warp is reachable, except the roped stair before 20;
- the barrier seals the vestibule;
- the balls, the switch tile and Indra's escape path are reachable or free.

**Header changes raid-scripts needs** (existing headers only, no new ones):
- R2-NE, R4-SE and R6-NW use `scripts_empty`, no init script and `TEXT_BANK_JUBILIFE_CITY`. They need their own
  scripts, init scripts and text banks for the generators and their OnTransition.
- R3, R4, R5 and R6 only carry eye-contact trainers and crates. They need no scripts if the crates use script 0
  (stock precedent for objects that are not talked to, e.g. `ACUITY_LAKEFRONT_RIVAL_2`) or a shared crate line.

### New field sprites needed (specified, not registered)

The sheet rules are those of `docs/arc1/part2/sprites.md` (idle2 = 64x32, two 32x32 frames, 16 colours, index 0
transparent, feet on row 29). Concept sheets for each are in `tools/solaceon_ruins/concept/`, drawn in that format.
The placeholders below work today.

| constant | layout | look | placeholder until art |
|---|---|---|---|
| `OBJ_EVENT_GFX_SHARD_GENERATOR` | idle2 (frames: hum A/B, the core pulses) | waist-high gunmetal cabinet on black skids (about 18 px wide, 24 px tall). Round violet-lit shard window at the front, an amber status lamp, a vented top with a black-sun ring stencil, a thick black cable and a violet power cable out of the base | `OBJ_EVENT_GFX_ECLIPSE_CRATE` |
| `OBJ_EVENT_GFX_SHARD_GENERATOR_OFF` | idle2 (both frames equal) | the same cabinet with the window dark grey, the lamp off and the violet cable greyed | `OBJ_EVENT_GFX_ECLIPSE_CRATE` |
| `OBJ_EVENT_GFX_SHARD_BARRIER` | idle2 (2-frame shimmer) | a curtain of violet light the full 32 px wide, **only rows 12-30 tall (about 1 tile)**, so it never hides the player or Cyrus standing behind it. Bright edge lines, dithered see-through holes, a moving band. Adjacent tiles' curtains overlap into one wall | `OBJ_EVENT_GFX_RIFT_ARC2` |
| `OBJ_EVENT_GFX_SHARD_FRAME_DARK` | idle2 | `SHARD_FRAME` with its violet ramp swapped to greys (a palette swap: the drained rack) | `OBJ_EVENT_GFX_SHARD_FRAME` |
| `OBJ_EVENT_GFX_VIOLET_CRYSTAL_DARK` | idle2 | `VIOLET_CRYSTAL` palette-swapped to greys ("just stones") | `OBJ_EVENT_GFX_VIOLET_CRYSTAL` |
| `OBJ_EVENT_GFX_DIG_ROPE` | idle2 (the bell swings) | two short wooden posts with a sagging rope, red and white flags and a little brass bell | `OBJ_EVENT_GFX_SIGNBOARD` |

Stock sprites used as they are: `CYRUS`, `LOOKER` (his normal look in the vault), `ROCK_SMASH` (the cave-in rubble;
its script is its own, so it cannot be smashed). The Arc 2 sprites used: `ECLIPSE_GRUNT_M/F`, `INDRA`,
`ECLIPSE_CRATE`, `SHARD_FRAME`, `VIOLET_CRYSTAL`.

### Dressing table (object events)

| room | tile(s) | gfx | hidden_flag | role |
|---|---|---|---|---|
| R1 | (6,3) | DIG_ROPE | 0x0031 local | the rope, < 20 |
| R1 | (4,9), (6,7) | ECLIPSE_CRATE | 0x0030 local | raid supplies (20-49) |
| R2 | (6,6), (6,7) | ECLIPSE_CRATE | RAID_F | |
| R2 | (4,8) | SHARD_FRAME | RAID_F | a frame waiting to be wired |
| R2-NE | (7,2) / (6,2) | GENERATOR(+_OFF) / SHARD_FRAME(+_DARK) | RAID_A / 0x0030 | generator A + rack |
| R2-NE | (4,2), (4,4) | ECLIPSE_CRATE | RAID_F | |
| R3 | (6,5) | ECLIPSE_CRATE | RAID_F | |
| R3 | (4,4) | VIOLET_CRYSTAL | RAID_F | shards waiting to be racked |
| R4 | (6,5), (6,6) | ECLIPSE_CRATE | RAID_F | |
| R4 | (6,7) | SHARD_FRAME | RAID_F | |
| R4-SE | (5,2) / (4,2) | GENERATOR(+_OFF) / SHARD_FRAME(+_DARK) | RAID_B / 0x0030 | generator B + rack |
| R4-SE | (2,2), (2,4) | ECLIPSE_CRATE | RAID_F | |
| R5 | (3,7), (5,7) | SHARD_FRAME | RAID_F | |
| R5 | (3,5), (4,9) | ECLIPSE_CRATE | RAID_F | |
| R6 | (6,6), (6,7) | ECLIPSE_CRATE | RAID_F | |
| R6 | (6,8) | VIOLET_CRYSTAL | RAID_F | |
| R6-NW | (2,2) / (3,2) | GENERATOR(+_OFF) / SHARD_FRAME(+_DARK) | RAID_C / 0x0030 | generator C + rack |
| R6-NW | (5,2), (5,4) | ECLIPSE_CRATE | RAID_F | |
| R7 | (2..8,5) | SHARD_BARRIER x7 | RAID_D | the barrier |
| R7 | (4,11) (6,11) (2,6) (2,7) (8,6) (8,7) | SHARD_FRAME + _DARK twins | RAID_E / 0x0031 | the stockpile |
| R7 | (8,8) | VIOLET_CRYSTAL + _DARK twin | RAID_E / 0x0031 | |
| R7 | (2,4) (2,8) (2,9) (2,11) (8,9) (8,11) | ECLIPSE_CRATE | RAID_F | |
| R7 | (2,10) | ROCK_SMASH | 0x0032 local | the cave-in, >= 45 |

Object counts per room: R1 5, R2 3 (+ the stock Hiker), dead ends 7 each, R3 3 (+ Karl), R4 3, R5 5, R6 3, and R7
31 (+ 4 balls). At most 11 distinct sprites in R7, well under the field's 64 objects.

## 3. Terrain dressing (written to the tree)

Built by `build_dressing.py` from the stock chunks at 50482f890 with `tools/world_art/chunkedit.py`:
- every stock shape and material is byte-identical (no stock shape is even re-encoded: nothing is cut);
- the dressing is appended as new materials `rr_*`, unlit with baked shades like the stock Ruins materials;
- BDHC and props are byte-identical.

**Room 1, `map_data_390`: the excavation.** It makes sense in every state (band A "visitors welcome... mind the
crates"; band F archaeologists).
- Two **scaffold towers** in the entrance corners (4,11) and (6,11). They are galvanised frames with cross braces,
  boards at h 1 and h 2, and **work lights** on top. The lenses are tipped so the cave camera sees them.
- Plain wooden **crates** in the tower feet.
- A warm a5i3 **light pool** on the floor in front (x 4-7, z 7.6-11).
- A **cable run** from the towers up the east side to the stair down to Room 2 (6,3), plus a cross cable between the
  towers.

**Room 7, `map_data_405`: the vault.**
- The **shard-machine plinth** at (5,11): a steel skirt plus a body 0.62 tiles high, with a socket and black-sun ring
  on top.
- **Cables** from the entry stair (8,3) down the east side to the plinth, and from the plinth to the west racks.
- **Violet-lit cracks** spreading from the plinth: three 2x2 decals, dark fissures with a dim violet core. After the
  raid they read as scorch and residue.
- A **fresh tunnel mouth** in the west wall at z 9.5-11.1: a decal over the full two-tier wall profile, pushed 0.03
  tiles out.
- **Loose rubble** at its foot (floor decals, not blocking).

Intended permission changes (the only ones; checked):

| chunk | tile | stock | new | why |
|---|---|---|---|---|
| 390 | (4,11) | 0x0008 | 0x8000 | scaffold tower |
| 390 | (6,11) | 0x0008 | 0x8000 | scaffold tower |
| 405 | (5,11) | 0x0008 | 0x8000 | the plinth |

Budgets (all checks pass):

| chunk | polygons | model bytes (limit 0xF000 = 61440) | materials | on screen, CAMERA_TYPE_CAVE, worst walkable tile (limit 1800) |
|---|---|---|---|---|
| 390 Room 1 | 293 -> 342 | 13356 -> 16796 | 13 -> 20 | 273 -> 310 |
| 405 Room 7 | 104 -> 131 | 5524 -> 7756 | 8 -> 14 | 94 -> 117 |

**Set 055** grows from 26 to 37 textures and 27 to 38 palettes. VRAM goes from 14080 to **17616 B**, against
76416 B for set 048, the largest stock set. Turnback Cave and the Celestic cave load the same set. The stock textures
and palettes keep their names, order and data (`texset_append` asserts it). New textures are all pltt16 at 16
texels/tile, except `rd_glow`, which is a5i3 like the stock exit light. Their palettes are sampled from the stock
sandstone, grey-green and floor ramps plus a dim Eclipse violet.

| texture | size | use |
|---|---|---|
| `rd_cable` | 32x8 | floor cables (2 tiles per repeat, 0.5 wide) |
| `rd_crack` | 32x32 | violet floor cracks (2x2 decal) |
| `rd_steel` | 16x16 | plinth / lamp steel |
| `rd_plate` | 16x16 | plinth top: socket and black-sun ring |
| `rd_scaff` | 16x32 | scaffold faces (transparent between the tubes) |
| `rd_plank` | 16x16 | scaffold boards |
| `rd_lamp` | 16x16 | work-lamp lens |
| `rd_crate` | 16x16 | plain crates |
| `rd_tunnel` | 32x32 | the tunnel mouth (transparent outside the rim) |
| `rd_rubble` | 16x16 | loose stones (decal) |
| `rd_glow` | 32x32 a5i3 | warm light pool |

**What is terrain and what is an object.** Anything that must appear, disappear or change is an object (the barrier,
generators, racks, crystals, crates, rubble and rope). The terrain is only what can stay forever: the excavation in
Room 1 and the empty vault fittings in Room 7, which is only reachable from 20 because of the rope.

### Renders

In `/tmp/Solaceon Update/raid/` (Cycles previews; sprites are stand-in billboards; `raid_game_sheet.png` is the
overview):

- `raid_game_sheet.png`: the in-game camera, in this order: R1 pre, R1 raid, R1 after, R2, R2-NE, R3, R4, R4-SE, R5,
  R6, R6-NW, R7 raid, R7 vault, R7 after, R1-NW (stock).
- `raid_r1_top_sheet.png`, `raid_r7_top_sheet.png`: top views per state, with objects as tile icons.
- `<room>_<state>_game.png` / `_top.png` for each room.
- `textures/raid_textures.png`: the texture contact sheet.
- `stock/`: the stock dump and renders.

Preview caveats:
- Billboards are pulled 4 tiles toward the camera so Blender doesn't cut them into the bevelled walls.
- Cyrus is a recoloured grunt, and Looker is the Arc 2 newspaper sheet.
- The concept sheets stand in for the new sprites.

## 4. Event snippets (ready to paste; raid-scripts owns the events files)

Append to `object_events`. `script` values `TODO_*` are raid-scripts' script ids; trainers use the stock form.
`python3 tools/solaceon_ruins/placements.py --json` prints the same in the repo's indented style. Object local ids
follow the array position, after the stock objects (R2: Hiker first; R3: Karl first; R7: the 4 balls first).

#### `events_solaceon_ruins_room_1.json`

```json
{"id": "SOL_RUINS_R1_ROPE", "graphics_id": "OBJ_EVENT_GFX_DIG_ROPE", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_UNK_0x0031", "script": "TODO_RopeSign", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 6, "z": 3, "y": 0},
{"id": "SOL_RUINS_R1_GRUNT_01", "graphics_id": "OBJ_EVENT_GFX_ECLIPSE_GRUNT_M", "movement_type": "MOVEMENT_TYPE_LOOK_SOUTH", "trainer_type": "TRAINER_TYPE_NORMAL", "hidden_flag": "FLAG_UNK_0x0030", "script": "TRAINER_ECLIPSE_GRUNT_SOL_01", "initial_dir": 1, "data": [3], "movement_range_x": 0, "movement_range_z": 0, "x": 6, "z": 2, "y": 0},
{"id": "SOL_RUINS_R1_CYRUS", "graphics_id": "OBJ_EVENT_GFX_CYRUS", "movement_type": "MOVEMENT_TYPE_LOOK_WEST", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_UNK_0x0032", "script": "TODO_CyrusRoom1", "initial_dir": 2, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 4, "z": 7, "y": 0},
{"id": "SOL_RUINS_R1_CRATE_0", "graphics_id": "OBJ_EVENT_GFX_ECLIPSE_CRATE", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_UNK_0x0030", "script": "TODO_Crate", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 4, "z": 9, "y": 0},
{"id": "SOL_RUINS_R1_CRATE_1", "graphics_id": "OBJ_EVENT_GFX_ECLIPSE_CRATE", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_UNK_0x0030", "script": "TODO_Crate", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 6, "z": 7, "y": 0}
```

Coord event (first entry at 20, Cyrus scene): (5,10), one tile in from the exit (5,11), plus whatever trigger shape
raid-scripts prefers.

#### `events_solaceon_ruins_room_2.json`

```json
{"id": "SOL_RUINS_R2_CRATE_0", "graphics_id": "OBJ_EVENT_GFX_ECLIPSE_CRATE", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TODO_Crate", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 6, "z": 6, "y": 0},
{"id": "SOL_RUINS_R2_CRATE_1", "graphics_id": "OBJ_EVENT_GFX_ECLIPSE_CRATE", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TODO_Crate", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 6, "z": 7, "y": 0},
{"id": "SOL_RUINS_R2_FRAME_0", "graphics_id": "OBJ_EVENT_GFX_SHARD_FRAME", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TODO_Frame", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 4, "z": 8, "y": 0}
```

#### `events_solaceon_ruins_room_2_northeast_dead_end.json`

```json
{"id": "SOL_RUINS_GEN_A_ON", "graphics_id": "OBJ_EVENT_GFX_SHARD_GENERATOR", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_A", "script": "TODO_GeneratorA", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 7, "z": 2, "y": 0},
{"id": "SOL_RUINS_GEN_A_OFF", "graphics_id": "OBJ_EVENT_GFX_SHARD_GENERATOR_OFF", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_UNK_0x0030", "script": "TODO_GeneratorA", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 7, "z": 2, "y": 0},
{"id": "SOL_RUINS_GEN_A_RACK_ON", "graphics_id": "OBJ_EVENT_GFX_SHARD_FRAME", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_A", "script": "TODO_GeneratorA", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 6, "z": 2, "y": 0},
{"id": "SOL_RUINS_GEN_A_RACK_OFF", "graphics_id": "OBJ_EVENT_GFX_SHARD_FRAME_DARK", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_UNK_0x0030", "script": "TODO_GeneratorA", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 6, "z": 2, "y": 0},
{"id": "SOL_RUINS_GEN_A_GUARD", "graphics_id": "OBJ_EVENT_GFX_ECLIPSE_GRUNT_F", "movement_type": "MOVEMENT_TYPE_LOOK_SOUTH", "trainer_type": "TRAINER_TYPE_NORMAL", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TRAINER_ECLIPSE_GRUNT_SOL_02", "initial_dir": 1, "data": [2], "movement_range_x": 0, "movement_range_z": 0, "x": 5, "z": 2, "y": 0},
{"id": "SOL_RUINS_GEN_A_CRATE_0", "graphics_id": "OBJ_EVENT_GFX_ECLIPSE_CRATE", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TODO_Crate", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 4, "z": 2, "y": 0},
{"id": "SOL_RUINS_GEN_A_CRATE_1", "graphics_id": "OBJ_EVENT_GFX_ECLIPSE_CRATE", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TODO_Crate", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 4, "z": 4, "y": 0}
```

#### `events_solaceon_ruins_room_3.json`

```json
{"id": "SOL_RUINS_R3_GRUNT_03", "graphics_id": "OBJ_EVENT_GFX_ECLIPSE_GRUNT_M", "movement_type": "MOVEMENT_TYPE_LOOK_EAST", "trainer_type": "TRAINER_TYPE_NORMAL", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TRAINER_ECLIPSE_GRUNT_SOL_03", "initial_dir": 3, "data": [2], "movement_range_x": 0, "movement_range_z": 0, "x": 4, "z": 8, "y": 0},
{"id": "SOL_RUINS_R3_CRATE_0", "graphics_id": "OBJ_EVENT_GFX_ECLIPSE_CRATE", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TODO_Crate", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 6, "z": 5, "y": 0},
{"id": "SOL_RUINS_R3_CRYSTAL_0", "graphics_id": "OBJ_EVENT_GFX_VIOLET_CRYSTAL", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TODO_Crystal", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 4, "z": 4, "y": 0}
```

#### `events_solaceon_ruins_room_4.json`

```json
{"id": "SOL_RUINS_R4_CRATE_0", "graphics_id": "OBJ_EVENT_GFX_ECLIPSE_CRATE", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TODO_Crate", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 6, "z": 5, "y": 0},
{"id": "SOL_RUINS_R4_CRATE_1", "graphics_id": "OBJ_EVENT_GFX_ECLIPSE_CRATE", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TODO_Crate", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 6, "z": 6, "y": 0},
{"id": "SOL_RUINS_R4_FRAME_0", "graphics_id": "OBJ_EVENT_GFX_SHARD_FRAME", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TODO_Frame", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 6, "z": 7, "y": 0}
```

#### `events_solaceon_ruins_room_4_southeast_dead_end.json`

```json
{"id": "SOL_RUINS_GEN_B_ON", "graphics_id": "OBJ_EVENT_GFX_SHARD_GENERATOR", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_B", "script": "TODO_GeneratorB", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 5, "z": 2, "y": 0},
{"id": "SOL_RUINS_GEN_B_OFF", "graphics_id": "OBJ_EVENT_GFX_SHARD_GENERATOR_OFF", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_UNK_0x0030", "script": "TODO_GeneratorB", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 5, "z": 2, "y": 0},
{"id": "SOL_RUINS_GEN_B_RACK_ON", "graphics_id": "OBJ_EVENT_GFX_SHARD_FRAME", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_B", "script": "TODO_GeneratorB", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 4, "z": 2, "y": 0},
{"id": "SOL_RUINS_GEN_B_RACK_OFF", "graphics_id": "OBJ_EVENT_GFX_SHARD_FRAME_DARK", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_UNK_0x0030", "script": "TODO_GeneratorB", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 4, "z": 2, "y": 0},
{"id": "SOL_RUINS_GEN_B_GUARD", "graphics_id": "OBJ_EVENT_GFX_ECLIPSE_GRUNT_F", "movement_type": "MOVEMENT_TYPE_LOOK_SOUTH", "trainer_type": "TRAINER_TYPE_NORMAL", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TRAINER_ECLIPSE_GRUNT_SOL_04", "initial_dir": 1, "data": [2], "movement_range_x": 0, "movement_range_z": 0, "x": 3, "z": 2, "y": 0},
{"id": "SOL_RUINS_GEN_B_CRATE_0", "graphics_id": "OBJ_EVENT_GFX_ECLIPSE_CRATE", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TODO_Crate", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 2, "z": 2, "y": 0},
{"id": "SOL_RUINS_GEN_B_CRATE_1", "graphics_id": "OBJ_EVENT_GFX_ECLIPSE_CRATE", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TODO_Crate", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 2, "z": 4, "y": 0}
```

#### `events_solaceon_ruins_room_5.json`

```json
{"id": "SOL_RUINS_R5_GRUNT_05", "graphics_id": "OBJ_EVENT_GFX_ECLIPSE_GRUNT_M", "movement_type": "MOVEMENT_TYPE_LOOK_NORTH", "trainer_type": "TRAINER_TYPE_NORMAL", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TRAINER_ECLIPSE_GRUNT_SOL_05", "initial_dir": 0, "data": [1], "movement_range_x": 0, "movement_range_z": 0, "x": 2, "z": 4, "y": 0},
{"id": "SOL_RUINS_R5_FRAME_0", "graphics_id": "OBJ_EVENT_GFX_SHARD_FRAME", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TODO_Frame", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 3, "z": 7, "y": 0},
{"id": "SOL_RUINS_R5_FRAME_1", "graphics_id": "OBJ_EVENT_GFX_SHARD_FRAME", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TODO_Frame", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 5, "z": 7, "y": 0},
{"id": "SOL_RUINS_R5_CRATE_0", "graphics_id": "OBJ_EVENT_GFX_ECLIPSE_CRATE", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TODO_Crate", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 4, "z": 9, "y": 0},
{"id": "SOL_RUINS_R5_CRATE_1", "graphics_id": "OBJ_EVENT_GFX_ECLIPSE_CRATE", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TODO_Crate", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 3, "z": 5, "y": 0}
```

#### `events_solaceon_ruins_room_6.json`

```json
{"id": "SOL_RUINS_R6_CRATE_0", "graphics_id": "OBJ_EVENT_GFX_ECLIPSE_CRATE", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TODO_Crate", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 6, "z": 6, "y": 0},
{"id": "SOL_RUINS_R6_CRATE_1", "graphics_id": "OBJ_EVENT_GFX_ECLIPSE_CRATE", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TODO_Crate", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 6, "z": 7, "y": 0},
{"id": "SOL_RUINS_R6_CRYSTAL_0", "graphics_id": "OBJ_EVENT_GFX_VIOLET_CRYSTAL", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TODO_Crystal", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 6, "z": 8, "y": 0}
```

#### `events_solaceon_ruins_room_6_northwest_dead_end.json`

```json
{"id": "SOL_RUINS_GEN_C_ON", "graphics_id": "OBJ_EVENT_GFX_SHARD_GENERATOR", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_C", "script": "TODO_GeneratorC", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 2, "z": 2, "y": 0},
{"id": "SOL_RUINS_GEN_C_OFF", "graphics_id": "OBJ_EVENT_GFX_SHARD_GENERATOR_OFF", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_UNK_0x0030", "script": "TODO_GeneratorC", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 2, "z": 2, "y": 0},
{"id": "SOL_RUINS_GEN_C_RACK_ON", "graphics_id": "OBJ_EVENT_GFX_SHARD_FRAME", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_C", "script": "TODO_GeneratorC", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 3, "z": 2, "y": 0},
{"id": "SOL_RUINS_GEN_C_RACK_OFF", "graphics_id": "OBJ_EVENT_GFX_SHARD_FRAME_DARK", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_UNK_0x0030", "script": "TODO_GeneratorC", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 3, "z": 2, "y": 0},
{"id": "SOL_RUINS_GEN_C_GUARD", "graphics_id": "OBJ_EVENT_GFX_ECLIPSE_GRUNT_F", "movement_type": "MOVEMENT_TYPE_LOOK_SOUTH", "trainer_type": "TRAINER_TYPE_NORMAL", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TRAINER_ECLIPSE_GRUNT_SOL_06", "initial_dir": 1, "data": [2], "movement_range_x": 0, "movement_range_z": 0, "x": 4, "z": 2, "y": 0},
{"id": "SOL_RUINS_GEN_C_CRATE_0", "graphics_id": "OBJ_EVENT_GFX_ECLIPSE_CRATE", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TODO_Crate", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 5, "z": 2, "y": 0},
{"id": "SOL_RUINS_GEN_C_CRATE_1", "graphics_id": "OBJ_EVENT_GFX_ECLIPSE_CRATE", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TODO_Crate", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 5, "z": 4, "y": 0}
```

#### `events_solaceon_ruins_room_7.json`

```json
{"id": "SOL_RUINS_R7_BARRIER_0", "graphics_id": "OBJ_EVENT_GFX_SHARD_BARRIER", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_D", "script": "TODO_Barrier", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 2, "z": 5, "y": 0},
{"id": "SOL_RUINS_R7_BARRIER_1", "graphics_id": "OBJ_EVENT_GFX_SHARD_BARRIER", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_D", "script": "TODO_Barrier", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 3, "z": 5, "y": 0},
{"id": "SOL_RUINS_R7_BARRIER_2", "graphics_id": "OBJ_EVENT_GFX_SHARD_BARRIER", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_D", "script": "TODO_Barrier", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 4, "z": 5, "y": 0},
{"id": "SOL_RUINS_R7_BARRIER_3", "graphics_id": "OBJ_EVENT_GFX_SHARD_BARRIER", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_D", "script": "TODO_Barrier", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 5, "z": 5, "y": 0},
{"id": "SOL_RUINS_R7_BARRIER_4", "graphics_id": "OBJ_EVENT_GFX_SHARD_BARRIER", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_D", "script": "TODO_Barrier", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 6, "z": 5, "y": 0},
{"id": "SOL_RUINS_R7_BARRIER_5", "graphics_id": "OBJ_EVENT_GFX_SHARD_BARRIER", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_D", "script": "TODO_Barrier", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 7, "z": 5, "y": 0},
{"id": "SOL_RUINS_R7_BARRIER_6", "graphics_id": "OBJ_EVENT_GFX_SHARD_BARRIER", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_D", "script": "TODO_Barrier", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 8, "z": 5, "y": 0},
{"id": "SOL_RUINS_R7_CYRUS", "graphics_id": "OBJ_EVENT_GFX_CYRUS", "movement_type": "MOVEMENT_TYPE_LOOK_SOUTH", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TODO_CyrusBarrier", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 5, "z": 4, "y": 0},
{"id": "SOL_RUINS_R7_LOOKER", "graphics_id": "OBJ_EVENT_GFX_LOOKER", "movement_type": "MOVEMENT_TYPE_LOOK_WEST", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_UNK_0x0030", "script": "TODO_LookerVault", "initial_dir": 2, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 8, "z": 4, "y": 0},
{"id": "SOL_RUINS_R7_INDRA", "graphics_id": "OBJ_EVENT_GFX_INDRA", "movement_type": "MOVEMENT_TYPE_LOOK_SOUTH", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_G", "script": "TODO_IndraVault", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 5, "z": 10, "y": 0},
{"id": "SOL_RUINS_R7_RUBBLE", "graphics_id": "OBJ_EVENT_GFX_ROCK_SMASH", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_UNK_0x0032", "script": "TODO_Rubble", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 2, "z": 10, "y": 0},
{"id": "SOL_RUINS_R7_RACK_0_LIT", "graphics_id": "OBJ_EVENT_GFX_SHARD_FRAME", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_E", "script": "TODO_Rack", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 4, "z": 11, "y": 0},
{"id": "SOL_RUINS_R7_RACK_1_LIT", "graphics_id": "OBJ_EVENT_GFX_SHARD_FRAME", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_E", "script": "TODO_Rack", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 6, "z": 11, "y": 0},
{"id": "SOL_RUINS_R7_RACK_2_LIT", "graphics_id": "OBJ_EVENT_GFX_SHARD_FRAME", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_E", "script": "TODO_Rack", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 2, "z": 6, "y": 0},
{"id": "SOL_RUINS_R7_RACK_3_LIT", "graphics_id": "OBJ_EVENT_GFX_SHARD_FRAME", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_E", "script": "TODO_Rack", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 2, "z": 7, "y": 0},
{"id": "SOL_RUINS_R7_RACK_4_LIT", "graphics_id": "OBJ_EVENT_GFX_SHARD_FRAME", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_E", "script": "TODO_Rack", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 8, "z": 6, "y": 0},
{"id": "SOL_RUINS_R7_RACK_5_LIT", "graphics_id": "OBJ_EVENT_GFX_SHARD_FRAME", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_E", "script": "TODO_Rack", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 8, "z": 7, "y": 0},
{"id": "SOL_RUINS_R7_RACK_0_DARK", "graphics_id": "OBJ_EVENT_GFX_SHARD_FRAME_DARK", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_UNK_0x0031", "script": "TODO_Rack", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 4, "z": 11, "y": 0},
{"id": "SOL_RUINS_R7_RACK_1_DARK", "graphics_id": "OBJ_EVENT_GFX_SHARD_FRAME_DARK", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_UNK_0x0031", "script": "TODO_Rack", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 6, "z": 11, "y": 0},
{"id": "SOL_RUINS_R7_RACK_2_DARK", "graphics_id": "OBJ_EVENT_GFX_SHARD_FRAME_DARK", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_UNK_0x0031", "script": "TODO_Rack", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 2, "z": 6, "y": 0},
{"id": "SOL_RUINS_R7_RACK_3_DARK", "graphics_id": "OBJ_EVENT_GFX_SHARD_FRAME_DARK", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_UNK_0x0031", "script": "TODO_Rack", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 2, "z": 7, "y": 0},
{"id": "SOL_RUINS_R7_RACK_4_DARK", "graphics_id": "OBJ_EVENT_GFX_SHARD_FRAME_DARK", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_UNK_0x0031", "script": "TODO_Rack", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 8, "z": 6, "y": 0},
{"id": "SOL_RUINS_R7_RACK_5_DARK", "graphics_id": "OBJ_EVENT_GFX_SHARD_FRAME_DARK", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_UNK_0x0031", "script": "TODO_Rack", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 8, "z": 7, "y": 0},
{"id": "SOL_RUINS_R7_CRYSTAL_LIT", "graphics_id": "OBJ_EVENT_GFX_VIOLET_CRYSTAL", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_E", "script": "TODO_Rack", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 8, "z": 8, "y": 0},
{"id": "SOL_RUINS_R7_CRYSTAL_DARK", "graphics_id": "OBJ_EVENT_GFX_VIOLET_CRYSTAL_DARK", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_UNK_0x0031", "script": "TODO_Rack", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 8, "z": 8, "y": 0},
{"id": "SOL_RUINS_R7_CRATE_0", "graphics_id": "OBJ_EVENT_GFX_ECLIPSE_CRATE", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TODO_Crate", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 2, "z": 4, "y": 0},
{"id": "SOL_RUINS_R7_CRATE_1", "graphics_id": "OBJ_EVENT_GFX_ECLIPSE_CRATE", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TODO_Crate", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 2, "z": 8, "y": 0},
{"id": "SOL_RUINS_R7_CRATE_2", "graphics_id": "OBJ_EVENT_GFX_ECLIPSE_CRATE", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TODO_Crate", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 2, "z": 9, "y": 0},
{"id": "SOL_RUINS_R7_CRATE_3", "graphics_id": "OBJ_EVENT_GFX_ECLIPSE_CRATE", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TODO_Crate", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 2, "z": 11, "y": 0},
{"id": "SOL_RUINS_R7_CRATE_4", "graphics_id": "OBJ_EVENT_GFX_ECLIPSE_CRATE", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TODO_Crate", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 8, "z": 9, "y": 0},
{"id": "SOL_RUINS_R7_CRATE_5", "graphics_id": "OBJ_EVENT_GFX_ECLIPSE_CRATE", "movement_type": "MOVEMENT_TYPE_NONE", "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "FLAG_SOL_RAID_F", "script": "TODO_Crate", "initial_dir": 1, "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": 8, "z": 11, "y": 0}
```

`bg_events` (append): the main rack's switch on the plinth, read from (5,10) facing south.

```json
{"script": "TODO_MainRackSwitch", "type": 0, "x": 5, "z": 11, "y": 0, "player_facing_dir": "BG_EVENT_DIR_SOUTH"}
```

`coord_events`: (2..8, 6), the first step past the barrier line (progress 33 and `FLAG_SOL_RAID_D`) sets 40. raid-scripts chooses the var/value fields of its trigger format.

## 5. Open issues and notes for the others

1. **Two new flags proposed** in the raid range: `FLAG_SOL_RAID_F` (raid over, set with progress 50) and
   `FLAG_SOL_RAID_G` (Indra gone, set at 45). They are within raid-scripts' A..P block, so they need no registry
   change. Raid-scripts may rename them, but the snippets use these names.
2. **Header fields** for R2-NE, R4-SE and R6-NW: their own scripts, init scripts and text banks (section 2). These
   are field changes to existing headers. R7 and R1 already have init archives.
3. **The rope is load-bearing.** Until it is in Room 1's events, Room 7's terrain (plinth, cables, cracks, tunnel)
   can be seen before the raid. Story's rope text is in screenplay Appendix B 7. Before 20, Unown are limited to the
   Room 1 dead ends. That affects the stock Unown-count Maniac Tunnel growth only until the raid.
4. **Room 7's HM05 ball** (6,7), script 7098 in `scripts_unk_0404.s`. The bible removes HMs, and story suggests
   TM30 Shadow Ball. That is a one-line change in the shared item script file (raid-scripts or the lead). The R2
   Hiker's lines are about HM05 too (`scripts_solaceon_ruins_room_2.s`) and need the same decision.
5. **Optional (raid-scripts):** hide the R2 Hiker during 20-49. That needs an OnTransition in R2 and a local flag
   instead of his `hidden_flag` "0". Ruin Maniac Karl in R3 can stay; all checks include him.
6. **New sprites** (section 2) need art and registration (an `object_events_gfx.txt` append and the ov5 tables, as
   in `tools/integrate_arc2_field_sprites.py`). Until then the placeholders work but the on/off and lit/dark twins
   look identical. The barrier art must stay short (rows 12-30) or it will hide whoever stands behind it.
7. **Not verified in game** (the devserver build is unreachable):
   - how the a5i3 light pool blends on the unlit floor;
   - the decal offsets (0.015-0.04 tiles) against z-fighting at the cave camera's depth;
   - whether DS billboards clip into the north-wall bevel the way the Blender preview does. Stock NPCs stand in
     north rows everywhere, so probably not.
   Polygon counts are far under budget, so there is room to thicken anything that reads too thin.
8. **macOS port** (`solaceon-mac`): the chunk and texture bytes are identical. Only `ruins.MAP_DATA_DIR`,
   `TEXSET_DIR` and `EVENTS_DIR` move (`res/field/mapmodels/...`, `res/field/maps/<map>/events.json`). The
   snippets keep the schema and use flag names only; the `FLAG_SOL_RAID_*` slots differ there. The map-local
   `FLAG_UNK_0x0030..32` are the engine's first-64 local flags on both branches.
9. **Wild encounters** keep running in the raid rooms (stock Unown tables). Turning them off for the raid would need
   a header or encounter change. Not done.

## 6. Implemented (raid-scripts, macOS tree, branch `sol-mac/raid`)

Everything below is on the `solaceon-mac` layout (`res/field/maps/<map>/`). The object table is still
`placements.py`; `tools/solaceon_ruins/raid_events.py --write` writes it into the events files, translated to this
tree (ids `SOL_RUINS_X` -> `LOCALID_X`, `FLAG_UNK_0x0030/31/32` -> `FLAG_MAP_LOCAL_HIDE_OBSTACLE_16/17/18`, trainers
as `"trainer": {"id", "sight_range"}`, `DIR_*` facings). Open issues 1-6 of section 5 are done as proposed.

| piece | where | notes |
|---|---|---|
| trainers | `res/trainers/data/indra_sanctuary.json`, `eclipse_grunt_sol_01..08.json` | from `docs/story/trainers.md` (Power -> `iv_scale`), messages from screenplay Part 5 (pre/defeat/post; Indra also `TRMSG_LAST_BATTLER`). Generated by `tools/solaceon_ruins/trainers.py`, which checks every species, move, ability and item name and the text widths. SOL_07/08 are ready for town-scripts. |
| field sprites | `res/graphics/field_sprites/objects/{shard_generator,shard_generator_off,shard_barrier,shard_frame_dark,violet_crystal_dark,dig_rope}.png`, `field_sprites.order` + `meson.build` (members 0x1EC-0x1F1, texture names `sol_*`: nitrobtx allows 14 characters), `generated/object_events_gfx.txt`, the five tables in `src/overlay005/object_event_gfx_data.c` | painted by `tools/solaceon_ruins/sprites.py` (32x64 two-frame sheets, 16 colours). The generator, barrier (rows 12-30 only, no shadow, period 16 px so neighbours join) and rope are drawn; the dark rack and dark crystal are palette swaps of the stock Arc 2 sheets (violet ramp -> stone greys, frame B = frame A). |
| text | `res/text/solaceon_ruins_room_1.json`, `_room_7.json` (appended), `_room_2.json` (Hiker rewritten in place), new banks `solaceon_ruins_room_{2_northeast,4_southeast,6_northwest}_dead_end.json` (`generated/text_banks.txt` appended) | screenplay text verbatim, written by `tools/solaceon_ruins/raid_text.py` (screenplay notation in, width/ASCII/2-lines checks; `tools/solaceon_ruins/textwidth.py` is the 197 px measure). New text only where the screenplay has none: the lit/dark rack, the rubble, Looker's reminder, the Hiker. |
| Room 1 | `solaceon_ruins_room_1/{scripts,init,events}` | OnTransition per section 2 (`_16` crew, `_17` rope, `_18` Cyrus). The entry scene runs from the init frame table at 20 (`InitScriptGoToIfEqual VAR_SOLACEON_PROGRESS, 20`), not a coord event: it walks the player up beside Cyrus wherever the warp lands them, plays part 3 and sets 30. Cyrus walks off past the stair and is removed. The rope (`DIG_ROPE` on the stair (6,3)) reads Appendix B 7. |
| generators | `solaceon_ruins_room_{2_northeast,4_southeast,6_northwest}_dead_end/{header.json,scripts.s,init.s,events.json}`, `res/field/scripts.order` appended | headers now name their own text banks; scripts/init found by mapgen from the folder. Talk (generator or rack) -> YES/NO -> `FLAG_SOL_RAID_x`, the on/off twins swap at once, then progress is recounted as 30 + the number of A/B/C set (any order, robust to test states), 33 also sets `FLAG_SOL_RAID_D`, then the Poketch and Ruth's 31/32/33 line. "Already off" text when talked to again. |
| Room 2 | `solaceon_ruins_room_2/*` | the Hiker is hidden at 20-49 (`_16`, OnTransition). HMs don't exist in this hack, so he now wants the way down to the TM: shown TM30 he asks for directions (Yes: the same Green Shard; No: "It's not like the way down will wear out! Cheapskate!"). Stock flags kept. |
| Room 7 | `solaceon_ruins_room_7/{scripts,init,events}.json` | OnTransition per section 2, plus: Cyrus moves aside to (6,4) from 33 (`SetObjectEventPos`), the vault trigger (coord row z 6, `VAR_MAP_LOCAL_0x01`) is armed at 33 and 40, and the barrier warning (coord row z 4, `VAR_MAP_LOCAL_0x02`, once per visit) at 30-32. The vault scene squares the player up at (5,8), Cyrus walks in behind (5,7), Indra's lines, the battle (loss: `BlackOutFromBattle`, progress stays 40, the scene replays), 45, Indra walks to (2,10) and is removed (`FLAG_SOL_RAID_G`), shake + white flash + the rubble, Looker runs in to (6,8), part 6 to "The switch is yours." The switch (bg event on (5,11), read from (5,10)): YES/NO; Yes flashes, sets `FLAG_SOL_RAID_E`, swaps the 7 lit objects for the dark twins, Ruth, the ledger pages, then 50 + `FLAG_SOL_RAID_F` and a warp to `MAP_HEADER_SOLACEON_TOWN` (571,657), in front of the Sanctuary door (`SOL_RAID_TOWN_X/Z` at the top of the script: town-scripts can move it). After E or at 50 the switch only describes the dial. |
| Room 7 HM05 ball | `res/field/scripts/visible_items.s`, `generated/vars_flags.txt` | now `ITEM_TM30` (`VisibleItems_SolaceonRuinsRoom7_TM30`, flag renamed `FLAG_OBTAINED_SOLACEON_RUINS_ROOM_7_TM30`, same slot). |
| Rooms 3-6 | events only | grunts and dressing; crates, frames and crystals have no script anywhere (nothing happens when talked to). |
| headless `objects` | `src/port/headless_game.c`, `docs/headless_protocol.md` | a read-only command listing the map objects that exist (hidden ones are absent), used for the visibility asserts. |
| test save | `tools/dazzling/save_tool.py edit --level LV --max-ivs --max-pp` | sets exp to the level's minimum (growth rate), recomputes the party stats (Gen 4 formula, base stats from the species JSON), full HP/PP, 3 PP Ups. |

Not done here (other owners): part 7 in town and the Dusk Stone (town-scripts reads 50 when the town loads after
the warp); Looker's briefing and the dig pair at 20 (town-scripts sets 20). Wild Unown encounters still run during
the raid (section 5, 9).

## 7. Testing

`python3 tools/solaceon_ruins/raid_test.py build_macos "/tmp/Solaceon Update/raid_mac"` (about 1 minute). It builds a
level 100 copy of `tools/battle_stage/emu/saves/eterna_forest_grass.sav` (and a level 5 one for the loss), boots each
scenario in a fresh `SIM_CONTROL=stdio` game, presses through Continue and sets the state with `set_var`/`set_flag`/
`warp`. Battles go through the `battle_decide` queue. Every beat asserts map, tile, `VAR_SOLACEON_PROGRESS`,
`FLAG_SOL_RAID_A-G` and which objects exist, and takes a screenshot (`<scenario>_<beat>.png`).

| scenario | covers |
|---|---|
| `pre_raid` | progress 0: Room 1 entered from the town door, only the rope from the raid set, the rope blocks (6,3), the sign text |
| `run_abc` | 20 -> 50 on foot from the town: the Room 1 scene (30), SOL_01 and his post-battle line, Room 2 (Hiker hidden), generator A (31), Room 3 (SOL_03, Karl), Room 4, generator B (32), Room 5 (SOL_05), Room 6, Room 7 with the barrier up (warning on approach, the player and Cyrus standing behind it, Cyrus "Not yet", the barrier text), generator C (33 + D), Room 7 at 33 (barrier gone, Cyrus aside, "It's down"), the vault scene and Indra (40, 45, G, rubble, Looker at (6,8), Cyrus at (5,7)), the switch (No, then Yes: E, dark racks), the warp to town at 50 with F |
| `run_cab` | the generators in the order C (answering No first), A, B by warping into each dead end; Room 7 at 33 |
| `post_raid` | progress 50: Room 1 empty, generator B room empty, Room 2 Hiker back (TM30 -> asks the way -> Green Shard +1), Room 7 scorched and empty (rubble and the four stock balls only), the switch describes the dial |
| `indra_loss` | level 5 party: whiteout, progress stays 40, back in Room 7 the scene replays from "You turned off all three." |

Results (2026-11-25, `build_macos` at the head of `sol-mac/raid`): all five pass. What the screenshots show: the
new sprites draw at the right tiles (generator window violet / dark grey, lit and grey racks, the barrier as one
translucent band across row 5, the rope with its flags and bell on the stair); a player or Cyrus standing behind
the barrier stays visible from the waist up (the curtain covers the legs only); no text box overflows (every line
was also measured at build time). Notes from the run: a stair warp needs one step onto the stair tile and one more in
the stair's direction; whiting out goes to the save's last Pokemon Center (Oreburgh for this save).
