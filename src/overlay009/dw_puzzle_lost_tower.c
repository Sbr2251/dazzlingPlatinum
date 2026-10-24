// DW Lost Tower puzzle tables (rift-lt, Phase 2).
//
// Two engine-a tables, one per visit, plus the visit-2 engine-b actor
// table. Registry: dw_puzzle.c sPuzzleTables[] / sActorTables[] (one
// extern + one line each, parallel order: V1 -> NULL actor table,
// V2 -> gDwActorsLostTowerTable).
//
// Visit 1 (progress 92-93): NO groups, NO sigils, NO runes. The
// Phase 0 scripted ghost acts run unchanged (ov9 + scripts). The
// table exists so the engine counts falls (gDwPuzzleState.fallCount,
// for the Cyrus hint after two falls) and so lip falls respawn at
// the entry checkpoint through the engine instead of the coord
// events (the step hook returns handled and Field_ProcessStep skips
// coord events). The false seam is NOT a VOID tile here: the per-map
// hook owns it and calls DwPuzzle_NotifyFall before its fall script
// (the README's scripted-fall pattern).
//
// Visit 2 (progress 94-95): groups + sigils + rune + actor table.
// Group polarities follow engine-b section 6 (Hitmonlee SET group->0,
// Vespiquen SET group->1, Lapras SET group->1); the plain sigils SET
// their groups to 0 (dispel / clear). All group tiles carry explicit
// surfaces (GROUND = base terrain, WEST_WALL = the wall).
//
//   group 0 G_H2    (18,22) crystal: ON = BLOCKED (prop shown), pad
//                   SET 0 -> SOLID. Ghost group 6.
//   group 1 G_V2    (19,22),(20,22) shadow: ON = BLOCKED (props
//                   shown), pad SET 0 -> SOLID (light dispels it).
//                   Flipped polarity (design: the blocked state must
//                   be drawn; a group whose props show only when ON
//                   cannot draw its OFF state). Ghost group 7.
//   group 2 G_SPUR  (16,24),(17,24) mist: ON = BLOCKED (props
//                   shown), spur sigil SET 0 -> SOLID. Ghost group 8.
//   group 3 G_STONES (23,26,29,32,22) stones: OFF = VOID (sunk,
//                   nothing drawn over open mist; hopping onto one
//                   falls), pad SET 1 -> SOLID. Ghost group 4.
//   group 4 G_GATE  (38,22) aura: ON = BLOCKED (prop shown), gate
//                   sigil SET 0 -> SOLID. Ghost group 9.
//   group 5 G_CARRY no tiles: the Skarmory pad's no-op sigil target
//                   (engine-b requires every pad to resolve through
//                   PressSigil; the carry itself is script-driven).
//
// Sigil order matches the actor table's pad order (H, V, L, S) plus
// the two plain sigils (spur, gate). The rune lands on (11,4,19),
// ADJACENT to the V pad: the landing rule says a rune landing fires
// NOTHING, so landing on the pad tile itself would leave the pad
// unfired; from (11,4,19) the player walks onto (11,4,20) and the
// pad prompt fires normally.
//
// Checkpoints (all off the shadow lane): entry, vein room,
// (16,23), carry landing. A checkpoint never shares a tile with a
// pad, sigil or rune.
//
// Fall script: 2 (DWLostTower_Fall), for step falls onto VOID tiles
// (lips, sunk stones). fallVar 0: no frame fall (no group ever
// turns off under a standing player: pads only SET toward open, and
// the frame-fall init line is not needed).

#include "generated/map_headers.h"
#include "generated/vars_flags.h"

#include "location.h"
#include "overlay009/dw_puzzle.h"
#include "overlay009/dw_puzzle_actors.h"

/* ---- Visit 1: fall lips (explicit VOID, GROUND) ---- */

static const DwPuzzleTile sV1Tiles[] = {
    { 15, 1, 11, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 19, 1, 11, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 20, 1, 11, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 21, 1, 11, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 20, 1, 13, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 21, 1, 13, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 12, 1, 15, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 13, 1, 15, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 14, 1, 15, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 15, 1, 15, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
};

static const DwPuzzleCheckpoint sV1Checkpoints[] = {
    { 20, 1, 12, -1, DW_PUZZLE_SURFACE_GROUND, { 0, 0 } },
};

const DwPuzzleTable gDwPuzzleLostTowerV1Table = {
    MAP_HEADER_DW_LOST_TOWER,
    92, 93,                     // VAR_ARC2_PROGRESS: visit 1
    2, 0,                       // fallScriptId (DWLostTower_Fall), no frame fall
    0, 0, 0, 0, 1, 10,           // group/sigil/rune/current/checkpoint/tile counts
    0, 0,                       // testOnly, padding
    NULL, NULL, NULL, NULL, sV1Checkpoints, sV1Tiles,
};

/* ---- Visit 2: groups ---- */

static const DwPuzzleTile sV2CrystalTiles[] = {
    { 18, 1, 22, 0, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
};

static const DwPuzzleTile sV2ShadowTiles[] = {
    { 19, 1, 22, 0, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
    { 20, 1, 22, 0, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
};

static const DwPuzzleTile sV2SpurTiles[] = {
    { 16, 1, 24, 0, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
    { 17, 1, 24, 0, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
};

static const DwPuzzleTile sV2StoneTiles[] = {
    { 23, 1, 22, 0, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
    { 26, 1, 22, 0, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
    { 29, 1, 22, 0, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
    { 32, 1, 22, 0, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
};

static const DwPuzzleTile sV2GateTiles[] = {
    { 38, 1, 22, 0, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
};

static const DwPuzzleGroup sV2Groups[] = {
    /* tiles, count, ghostPropGroup, fadeOut, fadeInLead, on, off, initial, fallScriptId */
    { sV2CrystalTiles, 1, 6, 0, 0, DW_PUZZLE_TILE_BLOCKED, DW_PUZZLE_TILE_SOLID, 1, 0 },
    { sV2ShadowTiles, 2, 7, 0, 0, DW_PUZZLE_TILE_BLOCKED, DW_PUZZLE_TILE_SOLID, 1, 0 },
    { sV2SpurTiles, 2, 8, 0, 0, DW_PUZZLE_TILE_BLOCKED, DW_PUZZLE_TILE_SOLID, 1, 0 },
    { sV2StoneTiles, 4, 4, 0, 0, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_TILE_VOID, 0, 0 },
    { sV2GateTiles, 1, 9, 0, 0, DW_PUZZLE_TILE_BLOCKED, DW_PUZZLE_TILE_SOLID, 1, 0 },
    { NULL, 0, DW_PUZZLE_GHOST_GROUP_NONE, 0, 0, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_TILE_SOLID, 0, 0 },
};

/* ---- Visit 2: sigils (pads first, then plain sigils) ---- */

static const DwPuzzleSigil sV2Sigils[] = {
    /* x, y, z, kind, targetGroup, setValue, surface */
    { 16, 1, 22, DW_PUZZLE_SIGIL_SET, 0, 0, DW_PUZZLE_SURFACE_GROUND },      // H pad -> crystal off
    { 11, 4, 20, DW_PUZZLE_SIGIL_SET, 1, 0, DW_PUZZLE_SURFACE_WEST_WALL },  // V pad -> shadow off
    { 16, 1, 24, DW_PUZZLE_SIGIL_SET, 3, 1, DW_PUZZLE_SURFACE_GROUND },      // L pad -> stones up
    { 32, 1, 22, DW_PUZZLE_SIGIL_SET, 5, 1, DW_PUZZLE_SURFACE_GROUND },      // S pad -> no-op group
    { 20, 1, 22, DW_PUZZLE_SIGIL_SET, 2, 0, DW_PUZZLE_SURFACE_GROUND },      // spur sigil -> mist off
    { 37, 1, 23, DW_PUZZLE_SIGIL_SET, 4, 0, DW_PUZZLE_SURFACE_GROUND },      // gate sigil -> aura off
};

/* ---- Visit 2: rune (one-way, GROUND -> WEST_WALL) ---- */

static const DwPuzzleRune sV2Runes[] = {
    /* x, y, z, targetX, targetY, targetZ, surface, targetSurface, facing, pad, rot, steps, useCamera, camX, camY, camZ, camSteps */
    { 17, 1, 23, 11, 4, 19, DW_PUZZLE_SURFACE_GROUND, DW_PUZZLE_SURFACE_WEST_WALL,
      FACE_LEFT, 0, 90, 0, 0, 0, 0, 0, 0 },
};

/* ---- Visit 2: checkpoints + fall lips ---- */

static const DwPuzzleCheckpoint sV2Checkpoints[] = {
    { 20, 1, 12, -1, DW_PUZZLE_SURFACE_GROUND, { 0, 0 } },
    { 13, 1, 23, -1, DW_PUZZLE_SURFACE_GROUND, { 0, 0 } },
    { 16, 1, 23, -1, DW_PUZZLE_SURFACE_GROUND, { 0, 0 } },
    { 37, 1, 22, -1, DW_PUZZLE_SURFACE_GROUND, { 0, 0 } },
};

static const DwPuzzleTile sV2Tiles[] = {
    { 15, 1, 11, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 19, 1, 11, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 20, 1, 11, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 21, 1, 11, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 20, 1, 13, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 21, 1, 13, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 12, 1, 15, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 13, 1, 15, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 14, 1, 15, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
    { 15, 1, 15, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 2, 0 },
};

const DwPuzzleTable gDwPuzzleLostTowerV2Table = {
    MAP_HEADER_DW_LOST_TOWER,
    94, 95,                     // VAR_ARC2_PROGRESS: visit 2
    2, 0,                       // fallScriptId (DWLostTower_Fall), no frame fall
    6, 6, 1, 0, 4, 10,           // group/sigil/rune/current/checkpoint/tile counts
    0, 0,                       // testOnly, padding
    sV2Groups, sV2Sigils, sV2Runes, NULL, sV2Checkpoints, sV2Tiles,
};

/* ---- Visit 2: engine-b actor table ----
 * 4 pads (H, V, L, S - exactly DW_ACTORS_MAX_PADS), one shadow lane.
 * The shadow tile list is the DwActors_MakeShadowLane expansion of
 * endpoints (17,22)-(31,22) on GROUND, PINGPONG, beat 50 frames
 * (45-60). No stones, no echo. */

const DwActorTable gDwActorsLostTowerTable = {
    /* stones: none */
    { { { 0, 0, 0, 0, 0 }, { { { 0, 0, 0, 0, 0 }, { 0, 0, 0, 0, 0 } } }, 0, 0 } },
    0,
    { 0, 0, 0 },
    /* shadow: the DwActors_MakeShadowLane expansion of (17,22)-(31,22) */
    { { { 17, 1, 22, DW_ACTOR_SURFACE_GROUND, 0 }, { 18, 1, 22, DW_ACTOR_SURFACE_GROUND, 0 },
          { 19, 1, 22, DW_ACTOR_SURFACE_GROUND, 0 }, { 20, 1, 22, DW_ACTOR_SURFACE_GROUND, 0 },
          { 21, 1, 22, DW_ACTOR_SURFACE_GROUND, 0 }, { 22, 1, 22, DW_ACTOR_SURFACE_GROUND, 0 },
          { 23, 1, 22, DW_ACTOR_SURFACE_GROUND, 0 }, { 24, 1, 22, DW_ACTOR_SURFACE_GROUND, 0 },
          { 25, 1, 22, DW_ACTOR_SURFACE_GROUND, 0 }, { 26, 1, 22, DW_ACTOR_SURFACE_GROUND, 0 },
          { 27, 1, 22, DW_ACTOR_SURFACE_GROUND, 0 }, { 28, 1, 22, DW_ACTOR_SURFACE_GROUND, 0 },
          { 29, 1, 22, DW_ACTOR_SURFACE_GROUND, 0 }, { 30, 1, 22, DW_ACTOR_SURFACE_GROUND, 0 },
          { 31, 1, 22, DW_ACTOR_SURFACE_GROUND, 0 } }, 15, 50, 1 },
    /* echo: inactive (active, playerSurface, echoSurface, echoAxis, echoValue, mirrorAxis, mirrorMin, mirrorMax, sigilTiles, sigilCount) */
    { 0, 0, 0, 0, 0, 0, 0, 0, { { 0, 0, 0, 0, 0 } }, 0 },
    /* pads: H, V, L, S (pad indices 0-3, matched by the prompt script) */
    {
        { { 16, 1, 22, DW_ACTOR_SURFACE_GROUND, 0 }, DW_ACTOR_TOTEM_HITMONLEE, 0 },
        { { 11, 4, 20, DW_ACTOR_SURFACE_WEST_WALL, 0 }, DW_ACTOR_TOTEM_VESPIQUEN, 0 },
        { { 16, 1, 24, DW_ACTOR_SURFACE_GROUND, 0 }, DW_ACTOR_TOTEM_LAPRAS, 0 },
        { { 32, 1, 22, DW_ACTOR_SURFACE_GROUND, 0 }, DW_ACTOR_TOTEM_SKARMORY, 0 },
    },
    4,
    { 0, 0, 0 },
    /* protected: none */
    { { 0, 0, 0, 0, 0 } },
    0,
    { 0, 0, 0 },
};
