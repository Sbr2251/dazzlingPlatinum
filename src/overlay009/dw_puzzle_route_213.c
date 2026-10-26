// DW puzzle table for MAP_HEADER_DW_ROUTE_213, the Drowned Lake (rift #4).
//
// Design: docs/distortion_world/route_213.md (difficulty 5, 46 steps).
// Three ceiling stones drop through ceiling gaps to bridge ground VOID
// gaps as LANDED stepping stones; one ground stone plugs the stage-2
// current by being pushed onto the last current tile of its column.
// Two reset sigils restore the checkpoint snapshot; checkpoints sit on
// walked tiles only (landing rule: no checkpoint on a rune/jump
// landing tile).
//
// Surfaces: CEILING (y = 10) + GROUND (y = 1, base map terrain). The
// lakebed is base terrain, so GROUND, never FLOOR.
// Tile budget: 32/32 (8 ceiling + 20 ground shelves + 4 VOID).
// Stones: 4/4 (engine-b max). Protected tiles: 7/8 (engine-b max).

#include "generated/map_headers.h"
#include "generated/vars_flags.h"

#include "location.h"
#include "overlay009/dw_puzzle.h"
#include "overlay009/dw_puzzle_actors.h"

// Fall script: entry 10 in res/field/scripts/scripts_dw_route_213.s
// (DWRoute213_Fall); frame-fall var VAR_MAP_LOCAL_3, cleared there.
#define ROUTE_213_FALL_SCRIPT 10

// ------------------------------------------------------------------
// Explicit tile overrides (DwPuzzleTable.tiles): 32 total.
// ------------------------------------------------------------------

// Explicit tile overrides (DwPuzzleTable.tiles): 32 total, ceiling first,
// then ground. Per-section comments give the meaning of each tile.
static const DwPuzzleTile sRoute213Tiles[] = {
    { 44, 10, 34, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 49, 10, 40, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 47, 10, 42, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 45, 10, 33, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 48, 10, 39, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 48, 10, 43, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 45, 10, 29, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 48, 10, 37, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_SURFACE_CEILING, 0, 0 },
    { 46, 1, 33, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
    { 45, 1, 33, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
    { 44, 1, 33, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
    { 43, 1, 34, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
    { 49, 1, 34, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
    { 49, 1, 35, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
    { 49, 1, 36, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
    { 48, 1, 36, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
    { 48, 1, 37, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
    { 48, 1, 38, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
    { 48, 1, 39, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
    { 49, 1, 38, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
    { 49, 1, 39, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
    { 49, 1, 41, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
    { 43, 1, 43, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
    { 44, 1, 43, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
    { 45, 1, 43, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
    { 46, 1, 43, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
    { 47, 1, 43, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
    { 48, 1, 42, DW_PUZZLE_TILE_SOLID, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
    { 44, 1, 34, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
    { 49, 1, 40, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
    { 47, 1, 42, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
    { 48, 1, 40, DW_PUZZLE_TILE_VOID, DW_PUZZLE_SURFACE_GROUND, 0, 0 },
};

// ------------------------------------------------------------------
// Sigils: 2 RESET (targetGroup ignored). Both sit before their stage's
// stone, reachable from the pre-stage path only: returning to one
// passes a checkpoint, which snapshots the pushed stones first, so a
// reset can never undo a completed push.
// ------------------------------------------------------------------
static const DwPuzzleSigil sRoute213Sigils[] = {
    { 45, 10, 29, DW_PUZZLE_SIGIL_RESET, 0, 0, DW_PUZZLE_SURFACE_CEILING },
    { 48, 10, 37, DW_PUZZLE_SIGIL_RESET, 0, 0, DW_PUZZLE_SURFACE_CEILING },
};

// ------------------------------------------------------------------
// Runes: 6 (3 pairs). Ceiling -> ground: rot +180 (out of the ceiling,
// mirroring the stock ceiling -> wall +90), camera reset to the ground
// view (the Ravaged test table's wall -> ground rune pattern). Ground ->
// ceiling: rot -180 (into the ceiling), stock ceiling camera templates
// (useCamera 0). Facing -1 = keep facing; steps 0 = 16.
// ------------------------------------------------------------------
static const DwPuzzleRune sRoute213Runes[] = {
    { 45, 10, 33, 46, 1, 33, DW_PUZZLE_SURFACE_CEILING, DW_PUZZLE_SURFACE_GROUND,
      -1, 0, 180, 0, 1, 0, 0, 0, 0 },
    { 48, 10, 39, 49, 1, 34, DW_PUZZLE_SURFACE_CEILING, DW_PUZZLE_SURFACE_GROUND,
      -1, 0, 180, 0, 1, 0, 0, 0, 0 },
    { 48, 10, 43, 43, 1, 43, DW_PUZZLE_SURFACE_CEILING, DW_PUZZLE_SURFACE_GROUND,
      -1, 0, 180, 0, 1, 0, 0, 0, 0 },
    { 43, 1, 34, 44, 10, 35, DW_PUZZLE_SURFACE_GROUND, DW_PUZZLE_SURFACE_CEILING,
      -1, 0, -180, 0, 0, 0, 0, 0, 0 },
    { 49, 1, 41, 49, 10, 41, DW_PUZZLE_SURFACE_GROUND, DW_PUZZLE_SURFACE_CEILING,
      -1, 0, -180, 0, 0, 0, 0, 0, 0 },
    { 48, 1, 42, 47, 10, 43, DW_PUZZLE_SURFACE_GROUND, DW_PUZZLE_SURFACE_CEILING,
      -1, 0, -180, 0, 0, 0, 0, 0, 0 },
};

// ------------------------------------------------------------------
// Currents: 4. Stage 2: the column (48, 37) -> (48, 38) -> (48, 39),
// all sliding south; the plug stone is pushed down the column onto
// (48, 39), so the slide stops at (48, 38). Stage 3: (47, 43) slides
// north onto the landed stone at (47, 42). No arrow ghost props: no
// arrow prop kind exists in the DW prop set; the corridor geometry
// (the column points south to the hazard; the ride tile points north
// to the landed stone) plus the Cyrus hint show the drift.
// ------------------------------------------------------------------
static const DwPuzzleCurrent sRoute213Currents[] = {
    { 48, 1, 37, FACE_DOWN, DW_PUZZLE_SURFACE_GROUND, DW_PUZZLE_GHOST_GROUP_NONE, 0 },
    { 48, 1, 38, FACE_DOWN, DW_PUZZLE_SURFACE_GROUND, DW_PUZZLE_GHOST_GROUP_NONE, 0 },
    { 48, 1, 39, FACE_DOWN, DW_PUZZLE_SURFACE_GROUND, DW_PUZZLE_GHOST_GROUP_NONE, 0 },
    { 47, 1, 43, FACE_UP, DW_PUZZLE_SURFACE_GROUND, DW_PUZZLE_GHOST_GROUP_NONE, 0 },
};

// ------------------------------------------------------------------
// Checkpoints: 5. CP0 is the map entry (fresh-entry reset snapshots
// it without anyone stepping on it). CP1 is the first walked ceiling
// tile past the jump landing (49, 10, 27) -- the landing itself never
// fires a checkpoint (landing rule). No checkpoint is a rune landing.
// ------------------------------------------------------------------
static const DwPuzzleCheckpoint sRoute213Checkpoints[] = {
    { 20, 1, 12, -1, DW_PUZZLE_SURFACE_GROUND, { 0, 0 } },
    { 49, 10, 28, -1, DW_PUZZLE_SURFACE_CEILING, { 0, 0 } },
    { 44, 10, 30, -1, DW_PUZZLE_SURFACE_CEILING, { 0, 0 } },
    { 48, 10, 36, -1, DW_PUZZLE_SURFACE_CEILING, { 0, 0 } },
    { 49, 10, 42, -1, DW_PUZZLE_SURFACE_CEILING, { 0, 0 } },
};

const DwPuzzleTable gDwPuzzleRoute213Table = {
    MAP_HEADER_DW_ROUTE_213,
    83, 83,                                     // VAR_ARC2_PROGRESS gate: entry state only
    ROUTE_213_FALL_SCRIPT, VAR_MAP_LOCAL_3,     // frame-fall script, fallVar
    0, 2, 6, 4, 5, 32,                         // group/sigil/rune/current/checkpoint/tile counts
    0, 0,                                      // testOnly, padding
    NULL, sRoute213Sigils, sRoute213Runes, sRoute213Currents, sRoute213Checkpoints, sRoute213Tiles,
};

// ------------------------------------------------------------------
// Actor table (engine-b): 4 stones, no shadow, no echo, no pads.
// Protected tiles: the 5 checkpoints + the 2 reset sigils (7/8).
// Engine-b does NOT auto-protect engine-a checkpoints / reset sigils.
// ------------------------------------------------------------------
const DwActorTable gDwPuzzleRoute213ActorTable = {
    .stones = {
        { // S1: ceiling stone, drops through gap 1 to bridge (44, 1, 34).
            .start = { 44, 10, 31, DW_ACTOR_SURFACE_CEILING, 0 },
            .edges = {
                { { 44, 10, 34, DW_ACTOR_SURFACE_CEILING, 0 },
                  { 44, 1, 34, DW_ACTOR_SURFACE_GROUND, 0 } },
            },
            .edgeCount = 1,
            .padding = 0,
        },
        { // S2: ceiling stone, drops through gap 2 to bridge (49, 1, 40).
            .start = { 49, 10, 37, DW_ACTOR_SURFACE_CEILING, 0 },
            .edges = {
                { { 49, 10, 40, DW_ACTOR_SURFACE_CEILING, 0 },
                  { 49, 1, 40, DW_ACTOR_SURFACE_GROUND, 0 } },
            },
            .edgeCount = 1,
            .padding = 0,
        },
        { // S3: ceiling stone, drops through gap 3 to bridge (47, 1, 42).
            .start = { 48, 10, 42, DW_ACTOR_SURFACE_CEILING, 0 },
            .edges = {
                { { 47, 10, 42, DW_ACTOR_SURFACE_CEILING, 0 },
                  { 47, 1, 42, DW_ACTOR_SURFACE_GROUND, 0 } },
            },
            .edgeCount = 1,
            .padding = 0,
        },
        { // S4: plug stone, resting on the stage-2 current column. No edges.
            .start = { 48, 1, 37, DW_ACTOR_SURFACE_GROUND, 0 },
            .edgeCount = 0,
            .padding = 0,
        },
    },
    .stoneCount = 4,
    .padding = { 0, 0, 0 },
    .shadow = { .tileCount = 0, .beatFrames = 0, .pingpong = 0 },
    .echo = { .active = 0 },
    .pads = { { .tile = { 0, 0, 0, 0, 0 }, .totem = 0, .padding = 0 } },
    .padCount = 0,
    .padding2 = { 0, 0, 0 },
    .protectedTiles = {
        { 20, 1, 12, DW_ACTOR_SURFACE_GROUND, 0 },   // CP0
        { 49, 10, 28, DW_ACTOR_SURFACE_CEILING, 0 }, // CP1
        { 44, 10, 30, DW_ACTOR_SURFACE_CEILING, 0 }, // CP2
        { 48, 10, 36, DW_ACTOR_SURFACE_CEILING, 0 }, // CP3
        { 49, 10, 42, DW_ACTOR_SURFACE_CEILING, 0 }, // CP4
        { 45, 10, 29, DW_ACTOR_SURFACE_CEILING, 0 }, // reset 1
        { 48, 10, 37, DW_ACTOR_SURFACE_CEILING, 0 }, // reset 2
    },
    .protectedCount = 7,
    .padding3 = { 0, 0, 0 },
};
