// DW Route 214 puzzle table (rift-214, Phase 2).
//
// Design: docs/distortion_world/route_214.md. The puzzle lives on the
// ceiling (y = 10, x 44-49, z 27-47): five chambers split by four
// stone-block walls. Each wall is crossed only by sliding through its
// current gap; between walls the player walks freely.
//
// Groups:
//   0 permanent walls: 22 tiles, ghost group 1, never toggled.
//     onState BLOCKED / offState SOLID is backwards-looking: the group
//     is initialOn 1 and its tiles are BLOCKED while on, so "on" here
//     means "the stone blocks are present". The engine only reads
//     onState/offState, so the table states the physical meaning.
//   1 group A: the W2 forward gap (48,33), ghost group 2, initialOn 1
//     (BLOCKED). Sigil A toggles it; when off the tile is a 'v' current.
//   2 group B: the C3 wall gap (44,39), ghost group 3, initialOn 1
//     (BLOCKED). Sigil B toggles it; when off the tile is a 'v' current.
//
// Group tile + current (engine-a confirmed): when the group's tile state
// is BLOCKED it wins and no slide happens; when open, the current
// applies. The A/B gap tiles are therefore both group tiles and
// currents in this table.
//
// Currents: 15 (7 wall gaps + 8 slide-path tiles). The D-pad direction
// on the ceiling is FACE_UP = +z (toward Skarmory), FACE_DOWN = -z.
//
// Checkpoints: 6, checkpoint 0 = the map entry (20,1,12) on GROUND.
// The ceiling-entry checkpoint is (49,10,28), not the jump landing
// (49,10,27): under the landing rule a jump landing fires nothing, so
// the checkpoint must sit on a WALKED tile (the first tile south of
// the landing). The wall-landing checkpoints (W1-W4) sit on slide
// landings, which DO fire (a slide is a movement), so they are fine.
//
// Fall script: DWRoute214_Fall, script entry 6 (see
// res/field/scripts/scripts_dw_route_214.s). It clears VAR_MAP_LOCAL_3
// (the frame-fall var), plays the fall, warps to the map entry, and
// shows Cyrus's hint on the second fall. The table has no VOID tiles
// and this map has no fall lips: every floor tile is drawn ground,
// every ceiling tile is slab or a drawn stone block, and the
// walls/ceiling are bounded by blocked tiles, so no step or
// frame-detected fall can fire in normal play -- the script is wired
// (fallScriptId + fallVar + init frame table) but unreachable. The
// fall/restore path itself is engine code, proven by engine-a's test
// tables; this table contributes only the checkpoint list. If ground
// ever does go away under a standing player (a future group change),
// the engine raises VAR_MAP_LOCAL_3, the init frame table starts this
// script, and the engine restores the last checkpoint snapshot and
// respawns at the checkpoint after the fall warp.
//
// Progress gate: 62/62 (the whole visit runs at progress 62; the calm
// at 63 ends the visit, so the table need not be active at 63).

#include "generated/map_headers.h"
#include "generated/vars_flags.h"

#include "location.h"
#include "overlay009/dw_puzzle.h"

// Group 0: permanent wall blocks (22 tiles, ceiling). x, y, z, state,
// surface, fallScriptId, padding. Group-tile state field is unused.
static const DwPuzzleTile sWallTiles[] = {
    { 44, 10, 29, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 45, 10, 29, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 47, 10, 29, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 48, 10, 29, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 49, 10, 29, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 45, 10, 33, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 46, 10, 33, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 47, 10, 33, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 49, 10, 33, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 45, 10, 37, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 46, 10, 37, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 47, 10, 37, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 48, 10, 37, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 45, 10, 39, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 46, 10, 39, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 47, 10, 39, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 48, 10, 39, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 49, 10, 39, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 45, 10, 41, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 46, 10, 41, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 48, 10, 41, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 49, 10, 41, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
};

// Group 1: the W2 forward gap (48,33). Group 2: the C3 wall gap (44,39).
static const DwPuzzleTile sGroupATiles[] = {
    { 48, 10, 33, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
};

static const DwPuzzleTile sGroupBTiles[] = {
    { 44, 10, 39, 0, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
};

static const DwPuzzleGroup sGroups[] = {
    // tiles, count, ghost group, fadeOut, fadeInLead, on, off, initial, fallScriptId
    { sWallTiles, 22, 1, 0, 0, DW_PUZZLE_TILE_BLOCKED, DW_PUZZLE_TILE_SOLID, 1, 0 },
    { sGroupATiles, 1, 2, 0, 0, DW_PUZZLE_TILE_BLOCKED, DW_PUZZLE_TILE_SOLID, 1, 0 },
    { sGroupBTiles, 1, 3, 0, 0, DW_PUZZLE_TILE_BLOCKED, DW_PUZZLE_TILE_SOLID, 1, 0 },
};

static const DwPuzzleSigil sSigils[] = {
    // x, y, z, kind, targetGroup, setValue, surface
    { 45, 10, 31, DW_PUZZLE_SIGIL_TOGGLE, 1, 0, DW_PUZZLE_SURFACE_CEILING }, // sigil A
    { 45, 10, 35, DW_PUZZLE_SIGIL_TOGGLE, 2, 0, DW_PUZZLE_SURFACE_CEILING }, // sigil B
};

static const DwPuzzleCurrent sCurrents[] = {
    // x, y, z, dir, surface, arrowGhostGroup, padding
    // W1 forward gap + slide path
    { 46, 10, 29, FACE_UP, DW_PUZZLE_SURFACE_CEILING, 4, 0 },
    { 46, 10, 30, FACE_UP, DW_PUZZLE_SURFACE_CEILING, 4, 0 },
    { 46, 10, 31, FACE_UP, DW_PUZZLE_SURFACE_CEILING, 4, 0 },
    // W2 forward gap (group A tile) + slide path
    { 48, 10, 33, FACE_UP, DW_PUZZLE_SURFACE_CEILING, DW_PUZZLE_GHOST_GROUP_NONE, 0 },
    { 48, 10, 34, FACE_UP, DW_PUZZLE_SURFACE_CEILING, 4, 0 },
    { 48, 10, 35, FACE_UP, DW_PUZZLE_SURFACE_CEILING, 4, 0 },
    // W2 return gap
    { 44, 10, 33, FACE_DOWN, DW_PUZZLE_SURFACE_CEILING, 4, 0 },
    // W3 forward gap + slide path
    { 44, 10, 37, FACE_UP, DW_PUZZLE_SURFACE_CEILING, 4, 0 },
    { 44, 10, 38, FACE_UP, DW_PUZZLE_SURFACE_CEILING, 4, 0 },
    // W3 return gap
    { 49, 10, 37, FACE_DOWN, DW_PUZZLE_SURFACE_CEILING, 4, 0 },
    // C3 wall gap (group B tile)
    { 44, 10, 39, FACE_UP, DW_PUZZLE_SURFACE_CEILING, DW_PUZZLE_GHOST_GROUP_NONE, 0 },
    // W4 forward gap + slide path
    { 47, 10, 41, FACE_UP, DW_PUZZLE_SURFACE_CEILING, 4, 0 },
    { 47, 10, 42, FACE_UP, DW_PUZZLE_SURFACE_CEILING, 4, 0 },
    { 47, 10, 43, FACE_UP, DW_PUZZLE_SURFACE_CEILING, 4, 0 },
    // W4 return gap
    { 44, 10, 41, FACE_DOWN, DW_PUZZLE_SURFACE_CEILING, 4, 0 },
};

static const DwPuzzleCheckpoint sCheckpoints[] = {
    // x, y, z, facing, surface, padding
    { 20, 1, 12, -1, DW_PUZZLE_SURFACE_GROUND, { 0, 0 } },   // map entry
    { 49, 10, 28, -1, DW_PUZZLE_SURFACE_CEILING, { 0, 0 } },  // ceiling entry (walked)
    { 46, 10, 32, -1, DW_PUZZLE_SURFACE_CEILING, { 0, 0 } },  // W1 landing (slide)
    { 48, 10, 36, -1, DW_PUZZLE_SURFACE_CEILING, { 0, 0 } },  // W2 landing (slide)
    { 44, 10, 40, -1, DW_PUZZLE_SURFACE_CEILING, { 0, 0 } },  // W3 landing (slide)
    { 47, 10, 44, -1, DW_PUZZLE_SURFACE_CEILING, { 0, 0 } },  // W4 landing (slide)
};

const DwPuzzleTable gDwPuzzleRoute214Table = {
    MAP_HEADER_DW_ROUTE_214,
    62, 62,                     // VAR_ARC2_PROGRESS gate
    6, VAR_MAP_LOCAL_3,         // fall script (DWRoute214_Fall), fallVar
    3, 2, 0, 15, 6, 0,          // group/sigil/rune/current/checkpoint/tile counts
    0, 0,                       // testOnly, padding
    sGroups, sSigils, NULL, sCurrents, sCheckpoints, NULL,
};

// Debug-only test table for MAP_HEADER_DW_ROUTE_214 (testOnly = 1,
// returned only while test mode is on). Identical to the production
// table except for six explicit VOID tiles -- one per checkpoint,
// off the optimal path -- that let the harness prove the fall path:
// a fall from each checkpoint restores that checkpoint's snapshot,
// and the second fall shows Cyrus's hint. The production table has
// no VOID tiles because this map has no fall lips (see the fall
// script comment above); the VOID tiles here are debug triggers, not
// designed hazards, and the production maze is unchanged (the optimal
// route never steps on them):
//   CP0 map entry .... (19,1,12)  on the entry walkway, west of (20,12)
//   CP1 ceiling entry  (44,10,27) C0 corner, off the C0 walk
//   CP2 W1 landing .... (44,10,30) C1 north-west, off the C1 walk
//   CP3 W2 landing .... (49,10,34) C2 east edge, off the C2 walk
//   CP4 W3 landing .... (49,10,40) C3 east end, off the C3 walk
//   CP5 W4 landing .... (44,10,42) C4 west, off the C4 walk
// All six use the same fall script (entry 6) as the production table.
static const DwPuzzleTile sTestTiles[] = {
    { 19, 1, 12, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 6, 0 },
    { 44, 10, 27, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_CEILING, 6, 0 },
    { 44, 10, 30, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_CEILING, 6, 0 },
    { 49, 10, 34, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_CEILING, 6, 0 },
    { 49, 10, 40, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_CEILING, 6, 0 },
    { 44, 10, 42, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_CEILING, 6, 0 },
};

const DwPuzzleTable gDwPuzzleRoute214TestTable = {
    MAP_HEADER_DW_ROUTE_214,
    62, 62,                     // VAR_ARC2_PROGRESS gate
    6, VAR_MAP_LOCAL_3,         // fall script (DWRoute214_Fall), fallVar
    3, 2, 0, 15, 6, 6,          // group/sigil/rune/current/checkpoint/tile counts
    1, 0,                       // testOnly, padding
    sGroups, sSigils, NULL, sCurrents, sCheckpoints, sTestTiles,
};
