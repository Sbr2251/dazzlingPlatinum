#ifndef POKEPLATINUM_DW_PUZZLE_ACTORS_H
#define POKEPLATINUM_DW_PUZZLE_ACTORS_H

// DW puzzle actors (engine-b): rift stones, Giratina's shadow, the echo self, totem-echo pads.
// Design: docs/distortion_world/actors_design.md. Build order: stones, shadow and pads first;
// echo self last (Arc 3 Aggron rift, no Arc 2 user).
//
// The actor core is platform-independent: it runs over a DwActorPlatform supplied by the caller
// (the ROM glue in dw_puzzle_actors.c, or a fake platform in the host test). The core never
// touches game state directly, so the same code is what the host test proves.
//
// Surfaces are EXPLICIT, never derived: (x, y, z) alone does not identify a tile (engine-a:
// a wall and a ceiling can share one). Every actor tile carries its surface, and every entry
// point takes the player's surface. Actor surface values equal DwPuzzleSurface
// (FLOOR 0, WEST_WALL 1, EAST_WALL 2, CEILING 3, GROUND 4, ANY 0xFF).
//
// In ROM builds, include "overlay009/dw_puzzle.h" BEFORE this header (for DwPuzzleTileState
// and gDwPuzzleDebug) and nitro.h before that. In host-test builds (DW_ACTORS_HOST_TEST) this
// header defines the base types from stdint and the engine-a calls are never used.

#ifdef DW_ACTORS_HOST_TEST
#include <stddef.h>
#include <stdint.h>
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef int8_t s8;
typedef int16_t s16;
typedef int32_t s32;
typedef int BOOL;
#define TRUE 1
#define FALSE 0
#define NULL ((void *)0)
#endif

#ifdef __cplusplus
extern "C" {
#endif

#define DW_ACTORS_MAX_STONES 4
#define DW_ACTORS_MAX_STONE_EDGES 4
#define DW_ACTORS_MAX_SHADOW_TILES 16
#define DW_ACTORS_MAX_ECHO_SIGILS 8
#define DW_ACTORS_MAX_PADS 4
#define DW_ACTORS_MAX_PROTECTED_TILES 8

#define DW_STONE_FALL_FRAMES 12
#define DW_SHADOW_CAUGHT_FRAMES 30
#define DW_SHADOW_SPAWN_GRACE_FRAMES 30
#define DW_SHADOW_CATCH_WATCHDOG_FRAMES 60

#define DW_ACTOR_SURFACE_FLOOR 0
#define DW_ACTOR_SURFACE_WEST_WALL 1
#define DW_ACTOR_SURFACE_EAST_WALL 2
#define DW_ACTOR_SURFACE_CEILING 3
#define DW_ACTOR_SURFACE_GROUND 4
#define DW_ACTOR_SURFACE_ANY 0xFF

#define DW_ACTOR_OCCUPANT_PLAYER 0
#define DW_ACTOR_OCCUPANT_ECHO 1

#define DW_ACTOR_TILE_NONE (-1) // no tile (hidden / inactive actor)

// Core tile kinds (platform interface). ROM glue maps to/from DwPuzzleTileState;
// DEFAULT resolves via the stock grid on the queried surface (see RomTileAt).
typedef enum {
    DW_ACTOR_TILE_VOID = 0,
    DW_ACTOR_TILE_WALKABLE,
    DW_ACTOR_TILE_BLOCKED,
    DW_ACTOR_TILE_SOLID,
    DW_ACTOR_TILE_DEFAULT // no engine override: stock grid decides
} DwActorTileKind;

typedef enum {
    DW_ACTOR_EVENT_NONE = 0,
    DW_ACTOR_EVENT_PAD_READY, // player stepped onto a pad; glue MUST skip engine-a's step
        // handling for this step, rift script shows Yes/No, then ResolvePad
    DW_ACTOR_EVENT_STONE_PUSH_BLOCKED, // player was put back after stepping into an unpushable stone
    DW_ACTOR_EVENT_CUTIN, // ResolvePad: Yes + calmed; script plays the Resonator ghost cut-in
    DW_ACTOR_EVENT_CARRY_REQUESTED // ResolvePad: Yes + calmed + Skarmory; script plays the carry
} DwActorEvent;

typedef enum {
    DW_ACTOR_STONE_RESTING = 0,
    DW_ACTOR_STONE_FALLING,
    DW_ACTOR_STONE_LANDED
} DwActorStoneState;

typedef enum {
    DW_ACTOR_SHADOW_INACTIVE = 0,
    DW_ACTOR_SHADOW_PATROL,
    DW_ACTOR_SHADOW_CAUGHT
} DwActorShadowState;

typedef enum {
    DW_ACTOR_TOTEM_HITMONLEE = 0,
    DW_ACTOR_TOTEM_VESPIQUEN,
    DW_ACTOR_TOTEM_LAPRAS,
    DW_ACTOR_TOTEM_SKARMORY,
    DW_ACTOR_TOTEM_COUNT
} DwActorTotem;

// One DW world tile, with its surface. Two tiles are equal only if coords AND surface match.
typedef struct {
    s16 x;
    s16 y;
    s16 z;
    u8 surface; // DW_ACTOR_SURFACE_*
    u8 padding;
} DwActorTile;

// A fall edge: the tile a stone is pushed INTO to start falling (on the stone's surface),
// plus the landing tile on the surface below.
typedef struct {
    DwActorTile edge;
    DwActorTile landing;
} DwActorStoneEdge;

typedef struct {
    DwActorTile start;
    DwActorStoneEdge edges[DW_ACTORS_MAX_STONE_EDGES];
    u8 edgeCount;
    u8 padding;
} DwActorStoneDef;

typedef struct {
    DwActorTile tiles[DW_ACTORS_MAX_SHADOW_TILES]; // all on one surface (lane) or explicit
    u8 tileCount;
    u16 beatFrames; // frames per patrol step; Lost Tower (Arc 2): 45-60 (one slow, readable patrol)
    u8 pingpong; // 0 = loop back to the start, 1 = reverse at the ends
} DwActorShadowDef;

typedef enum {
    DW_ACTOR_MIRROR_NONE = 0, // identity on the paired surface (floor <-> ceiling, same x,z)
    DW_ACTOR_MIRROR_X, // mirror the X coordinate in [mirrorMin, mirrorMax]
    DW_ACTOR_MIRROR_Y, // mirror the Y coordinate
    DW_ACTOR_MIRROR_Z // mirror the Z coordinate
} DwActorMirrorAxis;

typedef enum {
    DW_ACTOR_AXIS_X = 0,
    DW_ACTOR_AXIS_Y,
    DW_ACTOR_AXIS_Z
} DwActorAxis;

typedef struct {
    u8 active;
    u8 playerSurface; // DW_ACTOR_SURFACE_*: the surface the player must be on for the echo to show
    u8 echoSurface; // DW_ACTOR_SURFACE_*: the echo's surface
    u8 echoAxis; // DW_ACTOR_AXIS_*: the coordinate the echo surface fixes (X for walls, Y for floor/ceiling)
    s16 echoValue; // that coordinate's value (e.g. 49 for the east wall, 10 for the ceiling)
    // Mirroring applied to the player's tile (on top of the surface swap).
    DwActorMirrorAxis mirrorAxis;
    s16 mirrorMin;
    s16 mirrorMax;
    // Sigil tiles the echo can press (engine-a sigils, fired via PressSigil as occupant ECHO).
    DwActorTile sigilTiles[DW_ACTORS_MAX_ECHO_SIGILS];
    u8 sigilCount;
} DwActorEchoDef;

// A pad: an engine-a sigil tile (the sigil entry in DwPuzzleTable.sigils carries the target
// group + set value; the glue suppresses its auto-fire and ResolvePad fires it via PressSigil
// after the Yes/No + totem gate). The pad tile must not be a checkpoint/rune/current tile.
typedef struct {
    DwActorTile tile;
    u8 totem; // DwActorTotem; gates on FLAG_TOTEM_*_DEFEATED
    u8 padding;
} DwActorPadDef;

// A rift's actor table. Rift workstreams own their tables (dw_puzzle_<map>.c).
// protectedTiles: tiles a stone may never occupy (reset sigil, player sigils, checkpoint tiles
// the table author lists). Pads, echo-sigil tiles and landing tiles are protected automatically.
typedef struct DwActorTable {
    DwActorStoneDef stones[DW_ACTORS_MAX_STONES];
    u8 stoneCount;
    u8 padding[3];
    DwActorShadowDef shadow;
    DwActorEchoDef echo;
    DwActorPadDef pads[DW_ACTORS_MAX_PADS];
    u8 padCount;
    u8 padding2[3];
    DwActorTile protectedTiles[DW_ACTORS_MAX_PROTECTED_TILES];
    u8 protectedCount;
    u8 padding3[3];
} DwActorTable;

// The engine-a / platform surface the actor core runs on. All callbacks take ctx.
typedef struct {
    DwActorTileKind (*tileAt)(void *ctx, int x, int y, int z, int surface);
    // Actor tiles (engine-a DwPuzzle_SetActorTile): index-keyed, state-bearing.
    void (*setActorTile)(void *ctx, int index, int x, int y, int z, int surface, DwActorTileKind state, int present);
    void (*clearActorTiles)(void *ctx);
    int (*pressSigil)(void *ctx, int x, int y, int z, int surface, int occupant); // engine-a PressSigil
    void (*releaseSigils)(void *ctx, int occupant); // engine-a ReleaseSigils
    void (*requestCheckpointRespawn)(void *ctx); // engine-a RequestCheckpointRespawn
    void (*setPlayerTile)(void *ctx, int x, int y, int z); // push-back safety net
    void (*setInputLocked)(void *ctx, int locked); // shadow catch freeze
    int (*isScriptRunning)(void *ctx);
    int (*totemDefeated)(void *ctx, int totem); // DwActorTotem -> 0/1
    u32 (*getResetGeneration)(void *ctx); // gDwPuzzleDebug.resetGeneration
    void (*playCatchEffect)(void *ctx); // Giratina cry
    void *ctx;
} DwActorPlatform;

// Actor slice for the host test (the ROM syncs the engine-a subset into gDwPuzzleDebug).
typedef struct {
    u8 stoneCount;
    u8 stoneStates[DW_ACTORS_MAX_STONES];
    s16 stoneTiles[DW_ACTORS_MAX_STONES][3];
    u8 stoneSurfaces[DW_ACTORS_MAX_STONES];
    s16 shadowTile[3];
    u8 shadowSurface;
    u16 shadowPhase;
    u8 shadowState;
    s16 echoTile[3];
    u8 echoSurface;
    u8 echoBlocked;
    u16 echoSigilPresses;
    s8 pendingPad;
    u8 padUsed;
    u8 padDenied;
    u16 caughtCount;
    s8 carryPending; // pad index awaiting the script's Skarmory carry, or -1
    u16 respawnRequests; // RequestCheckpointRespawn calls issued (catches)
} DwActorDebug;

// Expand a straight lane into a shadow pattern: start..end inclusive, one tile a step, PINGPONG.
// The authoring path for the Lost Tower's one slow, readable patrol: two endpoints + a beat,
// no hand-written tile list. Start/end must share one surface; the line must lie on it
// (wall surfaces: y- or z-move with start/end y in [2,9]; floor/ground/ceiling: x- or z-move).
// Returns FALSE otherwise.
BOOL DwActors_MakeShadowLane(DwActorShadowDef *def, DwActorTile start, DwActorTile end, u16 beatFrames);

// Core lifecycle. Init registers a table (NULL = inert); it is idempotent for the same table
// (a battle reload re-calls it without losing puzzle state). OnExit clears all state.
// Init sanitises a copy of the table (counts clamped, beat >= 1) and captures the reset
// generation as the baseline, so a reset that fires after Init is never missed.
void DwActors_Init(const DwActorTable *table, const DwActorPlatform *platform);
void DwActors_OnExit(void);
BOOL DwActors_IsActive(void);

// Preferred stone entry: the glue's collision path calls this BEFORE allowing a step onto a
// stone tile, for voluntary walking only (never for slides). Returns FALSE if the step must
// stay blocked (stone cannot be pushed). Non-stone steps always return TRUE. A step that
// changes surface never pushes.
BOOL DwActors_TryPush(DwActorTile prev, DwActorTile cur);
// Post-step entry: the glue's step hook calls this after the player steps (prev -> cur).
// Returns an event for the hook (PAD_READY when the player stepped onto a pad: the glue
// must then skip engine-a's step handling for this step).
DwActorEvent DwActors_HandlePlayerStep(DwActorTile prev, DwActorTile cur);
// Per-frame entry: the glue's frame hook calls this with the player's current tile + surface.
void DwActors_HandleFrame(DwActorTile player);

void DwActors_ResetStones(void); // explicit to-start reset (NOT the default reset path)
DwActorEvent DwActors_ResolvePad(int padIndex, BOOL accepted); // rift script's Yes/No answer
int DwActors_TakePendingCutin(void); // totem id for the Resonator ghost cut-in, or -1; clears it
void DwActors_ConfirmCarryDone(void); // rift script: the Skarmory carry completed
void DwActors_OnCheckpoint(void); // snapshot stones/shadow/pads for the checkpoint
void DwActors_OnFallReset(void); // restore the checkpoint snapshot
// TRUE iff a RESTING stone occupies the tile (blocks walking via TryPush, plugs currents).
// LANDED stones are terrain (walkable, no block); FALLING stones occupy nothing.
BOOL DwActors_IsStoneAt(DwActorTile tile);
void DwActors_FillDebug(DwActorDebug *out);

// Debug-only test table (stones + shadow lane + echo + pads) for the host test and for
// engine-a's test map if it wants actor coverage. Defined in dw_puzzle_actors.c.
extern const DwActorTable gDwActorsTestTable;

// ROM visuals + debug sync (MapObjects, dw_puzzle_actors.c only; absent in the host test).
// Engine-a's glue calls these: VisualsInit on map load (idempotent, respawns from core
// state), VisualsUpdate per frame, VisualsExit on map unload (NULLs pointers; does NOT
// clear core state - same-map reloads keep it), SyncDebug every frame.
#ifndef DW_ACTORS_HOST_TEST
#include "field/field_system_decl.h"
// Glue helper: register a rift's table with the ROM platform built for this FieldSystem.
void DwActors_RegisterTable(FieldSystem *fieldSystem, const DwActorTable *table);
void DwActors_VisualsInit(FieldSystem *fieldSystem);
void DwActors_VisualsUpdate(FieldSystem *fieldSystem);
void DwActors_VisualsExit(FieldSystem *fieldSystem);
void DwActors_SyncDebug(void);
#endif

#ifdef __cplusplus
}
#endif

#endif // POKEPLATINUM_DW_PUZZLE_ACTORS_H
