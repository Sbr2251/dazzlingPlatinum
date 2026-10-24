// DW puzzle actors (engine-b): rift stones, Giratina's shadow, the echo self, totem-echo pads.
// Design: docs/distortion_world/actors_design.md. The core below is platform-independent and
// runs over a DwActorPlatform; the ROM glue (platform callbacks,
// MapObject visuals) is in the second half of this file, under #ifndef DW_ACTORS_HOST_TEST.
//
// Surfaces are EXPLICIT (engine-a: (x, y, z) alone does not identify a tile). Every actor tile
// carries its surface; every entry point takes the player's surface; the core never derives a
// surface from coordinates.
//
// Engine-a API status: dw_puzzle.h is engine-a's (merged, engine-a wins on
// conflict) and dw_puzzle.c has landed, so this file links against the
// strong engine-a definitions (the weak TEMP SHIM block is deleted).

#ifdef DW_ACTORS_HOST_TEST
#include <string.h>
#include "overlay009/dw_puzzle_actors.h"
#else
#include <nitro.h>
#include <string.h>

#include "constants/species.h"
#include "generated/movement_types.h"
#include "generated/object_events_gfx.h"
#include "generated/vars_flags.h"
#include "overlay009/dw_puzzle.h"
#include "overlay009/dw_puzzle_actors.h"
#include "overlay009/ov9_02249960.h"

#include "constants/map_object.h"
#include "field/field_system.h"
#include "field_task.h"
#include "map_object.h"
#include "player_avatar.h"
#include "script_manager.h"
#include "sound_playback.h"
#include "vars_flags.h"
#endif

// ---------------------------------------------------------------------------
// Core state
// ---------------------------------------------------------------------------

typedef struct {
    DwActorTile tile;
    DwActorTile fallLanding;
    u8 state;
    u8 fallTimer;
} DwActorStoneRuntime;

typedef struct {
    DwActorStoneRuntime stones[DW_ACTORS_MAX_STONES];
    u8 shadowPhase;
    s8 shadowDir;
    u16 shadowFrameCounter;
    u8 padUsed;
} DwActorSnapshot;

typedef struct {
    const DwActorTable *tableSrc; // identity for the idempotent re-init path
    const DwActorTable *table; // &tableCopy (sanitised)
    DwActorTable tableCopy;
    DwActorPlatform platform;
    BOOL active;
    BOOL generationInit;
    u32 lastResetGeneration;
    DwActorStoneRuntime stones[DW_ACTORS_MAX_STONES];
    u8 shadowPhase;
    s8 shadowDir;
    u16 shadowFrameCounter;
    u16 shadowGrace;
    u8 shadowState;
    u16 shadowCaughtTimer;
    BOOL catchResetIssued;
    u16 catchWatchdog;
    DwActorTile echoTile;
    BOOL echoShown;
    BOOL echoBlocked;
    u16 echoSigilPresses;
    s8 pendingPad;
    u8 padUsed;
    BOOL padDenied;
    s8 pendingCutin;
    s8 carryPending;
    u16 caughtCount;
    u16 respawnRequests;
    DwActorSnapshot snapshot;
} DwActorState;

static DwActorState sActors;

static BOOL TileEq(DwActorTile a, DwActorTile b)
{
    return a.x == b.x && a.y == b.y && a.z == b.z && a.surface == b.surface;
}

static DwActorTile TileNone(u8 surface)
{
    DwActorTile t;

    t.x = DW_ACTOR_TILE_NONE;
    t.y = DW_ACTOR_TILE_NONE;
    t.z = DW_ACTOR_TILE_NONE;
    t.surface = surface;
    t.padding = 0;
    return t;
}

__attribute__((unused)) static BOOL TileIsNone(DwActorTile t)
{
    return t.x == DW_ACTOR_TILE_NONE && t.y == DW_ACTOR_TILE_NONE && t.z == DW_ACTOR_TILE_NONE;
}

static DwActorTile ShadowTile(void)
{
    if (!sActors.active || sActors.table->shadow.tileCount == 0) {
        return TileNone(DW_ACTOR_SURFACE_FLOOR);
    }
    return sActors.table->shadow.tiles[sActors.shadowPhase];
}

static void ResetStateFromTable(void)
{
    int i;

    for (i = 0; i < DW_ACTORS_MAX_STONES; i++) {
        sActors.stones[i].tile = sActors.table->stones[i].start;
        sActors.stones[i].fallLanding = TileNone(DW_ACTOR_SURFACE_FLOOR);
        sActors.stones[i].state = DW_ACTOR_STONE_RESTING;
        sActors.stones[i].fallTimer = 0;
    }
    sActors.shadowPhase = 0;
    sActors.shadowDir = 1;
    sActors.shadowFrameCounter = 0;
    sActors.shadowGrace = DW_SHADOW_SPAWN_GRACE_FRAMES;
    sActors.shadowState = sActors.table->shadow.tileCount > 0 ? DW_ACTOR_SHADOW_PATROL : DW_ACTOR_SHADOW_INACTIVE;
    sActors.shadowCaughtTimer = 0;
    sActors.catchResetIssued = FALSE;
    sActors.catchWatchdog = 0;
    sActors.echoTile = TileNone(DW_ACTOR_SURFACE_FLOOR);
    sActors.echoShown = FALSE;
    sActors.echoBlocked = FALSE;
    sActors.echoSigilPresses = 0;
    sActors.pendingPad = -1;
    sActors.padUsed = 0;
    sActors.padDenied = FALSE;
    sActors.pendingCutin = -1;
    sActors.carryPending = -1;
    sActors.caughtCount = 0;
    sActors.respawnRequests = 0;
    // Capture the reset generation as the baseline: a reset that fires after Init (a reset
    // sigil, a fall, a catch) must be seen by the first poll, never swallowed as "initial".
    if (sActors.platform.getResetGeneration != NULL) {
        sActors.lastResetGeneration = sActors.platform.getResetGeneration(sActors.platform.ctx);
        sActors.generationInit = TRUE;
    } else {
        sActors.generationInit = FALSE;
        sActors.lastResetGeneration = 0;
    }

    // The initial state is also the first checkpoint snapshot (checkpoint 0 = map entry).
    DwActors_OnCheckpoint();
}

// Clear-then-reapply: the only way actor tiles are ever written, so a stale override
// (e.g. a LANDED stone restored to a different LANDED tile) can never survive.
static void SyncActorTiles(void)
{
    int i;

    if (!sActors.active || sActors.platform.clearActorTiles == NULL) {
        return;
    }
    sActors.platform.clearActorTiles(sActors.platform.ctx);
    if (sActors.platform.setActorTile == NULL) {
        return;
    }
    for (i = 0; i < sActors.table->stoneCount; i++) {
        if (sActors.stones[i].state == DW_ACTOR_STONE_RESTING) {
            sActors.platform.setActorTile(sActors.platform.ctx, i, sActors.stones[i].tile.x,
                sActors.stones[i].tile.y, sActors.stones[i].tile.z, sActors.stones[i].tile.surface,
                DW_ACTOR_TILE_BLOCKED, TRUE);
        } else if (sActors.stones[i].state == DW_ACTOR_STONE_LANDED) {
            sActors.platform.setActorTile(sActors.platform.ctx, i, sActors.stones[i].tile.x,
                sActors.stones[i].tile.y, sActors.stones[i].tile.z, sActors.stones[i].tile.surface,
                DW_ACTOR_TILE_SOLID, TRUE);
        }
    }
}

static BOOL IsProtectedTile(DwActorTile t)
{
    int i;

    for (i = 0; i < sActors.table->padCount; i++) {
        if (TileEq(t, sActors.table->pads[i].tile)) {
            return TRUE;
        }
    }
    for (i = 0; i < sActors.table->echo.sigilCount; i++) {
        if (TileEq(t, sActors.table->echo.sigilTiles[i])) {
            return TRUE;
        }
    }
    for (i = 0; i < sActors.table->protectedCount; i++) {
        if (TileEq(t, sActors.table->protectedTiles[i])) {
            return TRUE;
        }
    }
    // Landing tiles are reserved: a stone may only land there, never be pushed there.
    for (i = 0; i < sActors.table->stoneCount; i++) {
        int e;

        for (e = 0; e < sActors.table->stones[i].edgeCount; e++) {
            if (TileEq(t, sActors.table->stones[i].edges[e].landing)) {
                return TRUE;
            }
        }
    }
    return FALSE;
}

// Any stone (RESTING or LANDED) physically at the tile. FALLING stones occupy no tile.
static int FindStoneAt(DwActorTile tile)
{
    int i;

    for (i = 0; i < sActors.table->stoneCount; i++) {
        if (sActors.stones[i].state != DW_ACTOR_STONE_FALLING && TileEq(tile, sActors.stones[i].tile)) {
            return i;
        }
    }
    return -1;
}

static int FindEdge(const DwActorStoneDef *stone, DwActorTile target, DwActorTile *landingOut)
{
    int i;

    for (i = 0; i < stone->edgeCount; i++) {
        if (TileEq(target, stone->edges[i].edge)) {
            if (landingOut != NULL) {
                *landingOut = stone->edges[i].landing;
            }
            return i;
        }
    }
    return -1;
}

static DwActorTileKind TileAt(DwActorTile tile)
{
    if (sActors.platform.tileAt == NULL) {
        return DW_ACTOR_TILE_WALKABLE;
    }
    return sActors.platform.tileAt(sActors.platform.ctx, tile.x, tile.y, tile.z, tile.surface);
}

static BOOL ScriptRunning(void)
{
    if (sActors.platform.isScriptRunning == NULL) {
        return FALSE;
    }
    return sActors.platform.isScriptRunning(sActors.platform.ctx) != 0;
}

static void StartCatch(void)
{
    sActors.shadowState = DW_ACTOR_SHADOW_CAUGHT;
    sActors.shadowCaughtTimer = DW_SHADOW_CAUGHT_FRAMES;
    sActors.catchResetIssued = FALSE;
    sActors.catchWatchdog = 0;
    sActors.caughtCount++;
    if (sActors.platform.setInputLocked != NULL) {
        sActors.platform.setInputLocked(sActors.platform.ctx, TRUE);
    }
    if (sActors.platform.playCatchEffect != NULL) {
        sActors.platform.playCatchEffect(sActors.platform.ctx);
    }
}

static void PollResetGeneration(void)
{
    u32 gen;

    if (sActors.platform.getResetGeneration == NULL) {
        return;
    }
    gen = sActors.platform.getResetGeneration(sActors.platform.ctx);
    if (!sActors.generationInit) {
        sActors.generationInit = TRUE;
        sActors.lastResetGeneration = gen;
        return;
    }
    if (gen != sActors.lastResetGeneration) {
        sActors.lastResetGeneration = gen;
        DwActors_OnFallReset();
    }
}

// ---------------------------------------------------------------------------
// Public core API
// ---------------------------------------------------------------------------

BOOL DwActors_MakeShadowLane(DwActorShadowDef *def, DwActorTile start, DwActorTile end, u16 beatFrames)
{
    int dx, dy, dz, steps, i, axis;

    if (def == NULL || beatFrames == 0 || start.surface != end.surface) {
        return FALSE;
    }
    dx = end.x - start.x;
    dy = end.y - start.y;
    dz = end.z - start.z;
    // Exactly one axis moves, and the line must lie on the shared surface:
    //  wall surfaces: y-move with start/end y in [2,9], or z-move at a y in [2,9];
    //  floor/ground/ceiling: x- or z-move (y constant).
    if (start.surface == DW_ACTOR_SURFACE_WEST_WALL || start.surface == DW_ACTOR_SURFACE_EAST_WALL) {
        if (dx == 0 && dz == 0 && dy != 0) {
            if (start.y < 2 || start.y > 9 || end.y < 2 || end.y > 9) {
                return FALSE;
            }
            axis = 1;
            steps = dy < 0 ? -dy : dy;
        } else if (dy == 0 && dx == 0 && dz != 0) {
            if (start.y < 2 || start.y > 9) {
                return FALSE;
            }
            axis = 2;
            steps = dz < 0 ? -dz : dz;
        } else {
            return FALSE;
        }
    } else {
        if (dy != 0) {
            return FALSE;
        }
        if (dx != 0 && dz == 0) {
            axis = 0;
            steps = dx < 0 ? -dx : dx;
        } else if (dz != 0 && dx == 0) {
            axis = 2;
            steps = dz < 0 ? -dz : dz;
        } else {
            return FALSE;
        }
    }
    if (steps >= DW_ACTORS_MAX_SHADOW_TILES) {
        return FALSE;
    }
    memset(def, 0, sizeof(*def));
    def->beatFrames = beatFrames;
    def->pingpong = 1;
    def->tileCount = (u8)(steps + 1);
    for (i = 0; i <= steps; i++) {
        DwActorTile t = start;

        if (axis == 0) {
            t.x = (s16)(start.x + (dx < 0 ? -i : i));
        } else if (axis == 1) {
            t.y = (s16)(start.y + (dy < 0 ? -i : i));
        } else {
            t.z = (s16)(start.z + (dz < 0 ? -i : i));
        }
        def->tiles[i] = t;
    }
    return TRUE;
}

void DwActors_Init(const DwActorTable *table, const DwActorPlatform *platform)
{
    int i;

    if (table == NULL) {
        DwActors_OnExit();
        return;
    }
    if (sActors.active && sActors.tableSrc == table) {
        // Idempotent re-init (battle reload): keep puzzle state AND the reset-generation
        // polling state (a generation bump that lands while we are away is still caught),
        // refresh only the platform.
        if (platform != NULL) {
            sActors.platform = *platform;
        }
        SyncActorTiles();
        return;
    }
    // Sanitise a copy: Init never trusts counts from an external table (a malformed count
    // would overrun the fixed arrays in every loop below). Clear the old table's actor
    // tiles first: the memset below drops the old platform.
    if (sActors.active && sActors.platform.clearActorTiles != NULL) {
        sActors.platform.clearActorTiles(sActors.platform.ctx);
    }
    memset(&sActors, 0, sizeof(sActors));
    sActors.tableCopy = *table;
    if (sActors.tableCopy.stoneCount > DW_ACTORS_MAX_STONES) {
        sActors.tableCopy.stoneCount = DW_ACTORS_MAX_STONES;
    }
    for (i = 0; i < DW_ACTORS_MAX_STONES; i++) {
        if (sActors.tableCopy.stones[i].edgeCount > DW_ACTORS_MAX_STONE_EDGES) {
            sActors.tableCopy.stones[i].edgeCount = DW_ACTORS_MAX_STONE_EDGES;
        }
    }
    if (sActors.tableCopy.shadow.tileCount > DW_ACTORS_MAX_SHADOW_TILES) {
        sActors.tableCopy.shadow.tileCount = DW_ACTORS_MAX_SHADOW_TILES;
    }
    if (sActors.tableCopy.shadow.beatFrames == 0) {
        sActors.tableCopy.shadow.beatFrames = 1;
    }
    if (sActors.tableCopy.echo.sigilCount > DW_ACTORS_MAX_ECHO_SIGILS) {
        sActors.tableCopy.echo.sigilCount = DW_ACTORS_MAX_ECHO_SIGILS;
    }
    if (sActors.tableCopy.padCount > DW_ACTORS_MAX_PADS) {
        sActors.tableCopy.padCount = DW_ACTORS_MAX_PADS;
    }
    if (sActors.tableCopy.protectedCount > DW_ACTORS_MAX_PROTECTED_TILES) {
        sActors.tableCopy.protectedCount = DW_ACTORS_MAX_PROTECTED_TILES;
    }
    sActors.tableSrc = table;
    sActors.table = &sActors.tableCopy;
    if (platform != NULL) {
        sActors.platform = *platform;
    }
    sActors.active = TRUE;
    ResetStateFromTable();
    SyncActorTiles();
}

void DwActors_OnExit(void)
{
    // Full teardown for an actual departure (map change / blackout): clear the actor tiles,
    // release the echo's momentary holds, release a catch input lock, drop all state.
    // Same-map reloads (fall warp) must NOT call this: they call VisualsExit only and keep
    // the snapshot, which the reset-generation poll restores.
    if (sActors.active) {
        if (sActors.platform.clearActorTiles != NULL) {
            sActors.platform.clearActorTiles(sActors.platform.ctx);
        }
        if (sActors.platform.releaseSigils != NULL) {
            sActors.platform.releaseSigils(sActors.platform.ctx, DW_ACTOR_OCCUPANT_ECHO);
        }
        if (sActors.platform.setInputLocked != NULL) {
            sActors.platform.setInputLocked(sActors.platform.ctx, FALSE);
        }
    }
    memset(&sActors, 0, sizeof(sActors));
    sActors.pendingPad = -1;
    sActors.pendingCutin = -1;
    sActors.carryPending = -1;
}

BOOL DwActors_IsActive(void)
{
    return sActors.active ? TRUE : FALSE;
}

BOOL DwActors_TryPush(DwActorTile prev, DwActorTile cur)
{
    int stone, dx, dy, dz, i;
    DwActorTile target, landing;
    DwActorTileKind kind;

    if (!sActors.active) {
        return TRUE;
    }
    if (prev.surface != cur.surface) {
        return TRUE; // a surface-changing step never pushes (jump/rune owns it)
    }
    stone = FindStoneAt(cur);
    if (stone < 0) {
        // No stone at the destination (a LANDED stone is terrain, a FALLING one occupies
        // nothing): the step is a normal walk.
        return TRUE;
    }
    if (sActors.stones[stone].state != DW_ACTOR_STONE_RESTING) {
        return TRUE;
    }
    dx = cur.x - prev.x;
    dy = cur.y - prev.y;
    dz = cur.z - prev.z;
    if ((dx < 0 ? -dx : dx) + (dy < 0 ? -dy : dy) + (dz < 0 ? -dz : dz) != 1) {
        return FALSE; // not a unit step: jumps and diagonals do not push
    }
    // The push must stay in the surface plane: walls move in (y, z), the rest in (x, z).
    if (cur.surface == DW_ACTOR_SURFACE_WEST_WALL || cur.surface == DW_ACTOR_SURFACE_EAST_WALL) {
        if (dx != 0) {
            return FALSE;
        }
    } else if (dy != 0) {
        return FALSE;
    }
    target.x = (s16)(cur.x + dx);
    target.y = (s16)(cur.y + dy);
    target.z = (s16)(cur.z + dz);
    target.surface = cur.surface;
    target.padding = 0;

    // A FALLING stone's edge tile is occupied by the fall: do not stack falls.
    for (i = 0; i < sActors.table->stoneCount; i++) {
        if (sActors.stones[i].state == DW_ACTOR_STONE_FALLING && TileEq(target, sActors.stones[i].tile)) {
            return FALSE;
        }
    }
    // Designated edge: the stone falls to the surface below. The edge target is still
    // subject to the occupancy rules (no stacking, no protected tiles, no landing clash).
    if (FindEdge(&sActors.table->stones[stone], target, &landing) >= 0) {
        if (FindStoneAt(target) >= 0 || IsProtectedTile(target)) {
            return FALSE;
        }
        for (i = 0; i < sActors.table->stoneCount; i++) {
            if (i == stone) {
                continue;
            }
            if (sActors.stones[i].state == DW_ACTOR_STONE_LANDED && TileEq(landing, sActors.stones[i].tile)) {
                return FALSE;
            }
            if (sActors.stones[i].state == DW_ACTOR_STONE_FALLING && TileEq(landing, sActors.stones[i].fallLanding)) {
                return FALSE;
            }
        }
        sActors.stones[stone].tile = target;
        sActors.stones[stone].state = DW_ACTOR_STONE_FALLING;
        sActors.stones[stone].fallTimer = DW_STONE_FALL_FRAMES;
        sActors.stones[stone].fallLanding = landing;
        SyncActorTiles();
        return TRUE;
    }
    // No stacking, no protected tiles (pads, echo sigils, listed tiles, landing tiles).
    if (FindStoneAt(target) >= 0 || IsProtectedTile(target)) {
        return FALSE;
    }
    kind = TileAt(target);
    if (kind == DW_ACTOR_TILE_BLOCKED || kind == DW_ACTOR_TILE_VOID) {
        return FALSE;
    }
    sActors.stones[stone].tile = target;
    SyncActorTiles();
    return TRUE;
}

static void EchoHide(BOOL blocked)
{
    if (sActors.echoShown && sActors.platform.releaseSigils != NULL) {
        // The echo is gone: release its momentary sigil holds (it re-presses on re-entry).
        sActors.platform.releaseSigils(sActors.platform.ctx, DW_ACTOR_OCCUPANT_ECHO);
    }
    sActors.echoShown = FALSE;
    sActors.echoBlocked = blocked ? TRUE : FALSE;
}

static void EchoUpdate(DwActorTile player, int playerSurface)
{
    const DwActorEchoDef *echo;
    DwActorTile desired, prevTile;
    BOOL prevShown;
    DwActorTileKind kind;
    int i;

    if (!sActors.active) {
        return;
    }
    echo = &sActors.table->echo;
    if (!echo->active) {
        EchoHide(FALSE);
        return;
    }
    if (playerSurface != echo->playerSurface) {
        // Player is not on the echo's paired surface: the echo hides.
        EchoHide(FALSE);
        return;
    }
    desired = player;
    desired.surface = echo->echoSurface;
    // The echo surface fixes one coordinate (the wall's x, the ceiling/floor's y).
    if (echo->echoAxis == DW_ACTOR_AXIS_X) {
        desired.x = echo->echoValue;
    } else if (echo->echoAxis == DW_ACTOR_AXIS_Y) {
        desired.y = echo->echoValue;
    } else {
        desired.z = echo->echoValue;
    }
    // Mirroring applies after the fixed coordinate (mirrorAxis must differ from echoAxis).
    if (echo->mirrorAxis == DW_ACTOR_MIRROR_X) {
        desired.x = (s16)(echo->mirrorMin + echo->mirrorMax - player.x);
    } else if (echo->mirrorAxis == DW_ACTOR_MIRROR_Y) {
        desired.y = (s16)(echo->mirrorMin + echo->mirrorMax - player.y);
    } else if (echo->mirrorAxis == DW_ACTOR_MIRROR_Z) {
        desired.z = (s16)(echo->mirrorMin + echo->mirrorMax - player.z);
    }
    if (sActors.echoShown && TileEq(desired, sActors.echoTile)) {
        return; // unchanged: no refire, no move
    }
    prevTile = sActors.echoTile;
    prevShown = sActors.echoShown;
    kind = TileAt(desired);
    if ((kind == DW_ACTOR_TILE_WALKABLE || kind == DW_ACTOR_TILE_SOLID) && !DwActors_IsStoneAt(desired)
        && !(desired.x == player.x && desired.y == player.y && desired.z == player.z && desired.surface == (u8)playerSurface)) {
        sActors.echoTile = desired;
        sActors.echoShown = TRUE;
        sActors.echoBlocked = FALSE;
        // The echo moved (hidden -> shown, or a move onto a new tile): release its momentary
        // holds first. PressSigil releases holds elsewhere when pressing a new sigil, but a
        // move onto a NON-sigil tile releases nothing - the old momentary group would stay
        // held forever. Releasing here covers both cases (re-pressing the destination sigil
        // re-establishes its hold right after).
        if (sActors.platform.releaseSigils != NULL) {
            sActors.platform.releaseSigils(sActors.platform.ctx, DW_ACTOR_OCCUPANT_ECHO);
        }
        // Fire an echo sigil only on entering its tile (hidden -> shown, or a move onto it),
        // and count only presses that actually fired (a missing sigil is a table error).
        for (i = 0; i < echo->sigilCount; i++) {
            if (TileEq(desired, echo->sigilTiles[i]) && (!prevShown || !TileEq(desired, prevTile))) {
                if (sActors.platform.pressSigil != NULL
                    && sActors.platform.pressSigil(sActors.platform.ctx, desired.x, desired.y,
                        desired.z, desired.surface, DW_ACTOR_OCCUPANT_ECHO)) {
                    sActors.echoSigilPresses++;
                }
                break;
            }
        }
    } else {
        // Blocked: the echo hides (not last-valid). The player is unaffected.
        EchoHide(TRUE);
    }
}

DwActorEvent DwActors_HandlePlayerStep(DwActorTile prev, DwActorTile cur)
{
    int i, stone;

    if (!sActors.active) {
        return DW_ACTOR_EVENT_NONE;
    }
    PollResetGeneration();
    if (sActors.shadowState == DW_ACTOR_SHADOW_CAUGHT) {
        return DW_ACTOR_EVENT_NONE; // frozen: steps are script-driven
    }
    // Safety net: the glue should have called TryPush pre-move. If the player still ended
    // up on a RESTING stone's tile, put them back.
    stone = FindStoneAt(cur);
    if (stone >= 0 && sActors.stones[stone].state == DW_ACTOR_STONE_RESTING) {
        if (!DwActors_TryPush(prev, cur)) {
            if (sActors.platform.setPlayerTile != NULL) {
                sActors.platform.setPlayerTile(sActors.platform.ctx, prev.x, prev.y, prev.z);
            }
            return DW_ACTOR_EVENT_STONE_PUSH_BLOCKED;
        }
    }
    EchoUpdate(cur, cur.surface);
    if (sActors.carryPending >= 0) {
        return DW_ACTOR_EVENT_NONE; // script owns the player during the carry
    }
    for (i = 0; i < sActors.table->padCount; i++) {
        if (TileEq(cur, sActors.table->pads[i].tile) && !(sActors.padUsed & (1 << i))) {
            sActors.pendingPad = (s8)i;
            return DW_ACTOR_EVENT_PAD_READY;
        }
    }
    if (sActors.shadowState == DW_ACTOR_SHADOW_PATROL && sActors.shadowGrace == 0 && !ScriptRunning()
        && TileEq(cur, ShadowTile())) {
        StartCatch();
    }
    return DW_ACTOR_EVENT_NONE;
}

void DwActors_HandleFrame(DwActorTile player)
{
    int i;

    if (!sActors.active) {
        return;
    }
    PollResetGeneration();

    // Falling stones keep falling (the world does not pause for a catch or a carry).
    for (i = 0; i < sActors.table->stoneCount; i++) {
        if (sActors.stones[i].state == DW_ACTOR_STONE_FALLING) {
            if (--sActors.stones[i].fallTimer == 0) {
                sActors.stones[i].tile = sActors.stones[i].fallLanding;
                sActors.stones[i].state = DW_ACTOR_STONE_LANDED;
                SyncActorTiles();
            }
        }
    }

    if (sActors.shadowState == DW_ACTOR_SHADOW_CAUGHT) {
        if (sActors.shadowCaughtTimer > 0) {
            sActors.shadowCaughtTimer--;
        }
        if (sActors.shadowCaughtTimer == 0 && !sActors.catchResetIssued) {
            // Latched: the respawn is requested once; the poll restores the snapshot when
            // engine-a bumps the reset generation. If that never comes (engine-a absent),
            // the watchdog below self-heals instead of freezing the player forever.
            sActors.catchResetIssued = TRUE;
            sActors.catchWatchdog = DW_SHADOW_CATCH_WATCHDOG_FRAMES;
            sActors.respawnRequests++;
            if (sActors.platform.requestCheckpointRespawn != NULL) {
                sActors.platform.requestCheckpointRespawn(sActors.platform.ctx);
            }
        } else if (sActors.catchResetIssued && sActors.catchWatchdog > 0) {
            if (--sActors.catchWatchdog == 0) {
                DwActors_OnFallReset();
            }
        }
        return;
    }
    if (sActors.shadowState != DW_ACTOR_SHADOW_PATROL) {
        return;
    }
    if (sActors.carryPending >= 0 || sActors.pendingPad >= 0) {
        return; // the patrol freezes during actor-owned script windows (carry, pad prompt)
    }
    if (sActors.shadowGrace > 0) {
        sActors.shadowGrace--;
        // The patrol advances during grace; only the catch is suppressed.
    }
    if (++sActors.shadowFrameCounter >= sActors.table->shadow.beatFrames) {
        sActors.shadowFrameCounter = 0;
        if (sActors.table->shadow.tileCount <= 1) {
            sActors.shadowPhase = 0;
            sActors.shadowDir = 1;
        } else if (sActors.table->shadow.pingpong) {
            int next = (int)sActors.shadowPhase + sActors.shadowDir;

            if (next >= sActors.table->shadow.tileCount) {
                sActors.shadowDir = -1;
                next = (int)sActors.shadowPhase - 1;
            } else if (next < 0) {
                sActors.shadowDir = 1;
                next = 1;
            }
            if (next < 0) {
                next = 0;
            }
            sActors.shadowPhase = (u8)next;
        } else {
            sActors.shadowPhase = (u8)((sActors.shadowPhase + 1) % sActors.table->shadow.tileCount);
        }
    }
    if (sActors.shadowGrace == 0 && !ScriptRunning() && TileEq(player, ShadowTile())) {
        StartCatch();
    }
}

void DwActors_ResetStones(void)
{
    int i;

    if (!sActors.active) {
        return;
    }
    for (i = 0; i < sActors.table->stoneCount; i++) {
        sActors.stones[i].tile = sActors.table->stones[i].start;
        sActors.stones[i].state = DW_ACTOR_STONE_RESTING;
        sActors.stones[i].fallTimer = 0;
        sActors.stones[i].fallLanding = TileNone(DW_ACTOR_SURFACE_FLOOR);
    }
    SyncActorTiles();
}

DwActorEvent DwActors_ResolvePad(int padIndex, BOOL accepted)
{
    const DwActorPadDef *pad;
    int pressed;

    if (!sActors.active || padIndex < 0 || padIndex >= sActors.table->padCount || padIndex != sActors.pendingPad) {
        return DW_ACTOR_EVENT_NONE; // stale answer for a pad the player already left
    }
    sActors.pendingPad = -1;
    if (!accepted) {
        return DW_ACTOR_EVENT_NONE;
    }
    pad = &sActors.table->pads[padIndex];
    if (sActors.platform.totemDefeated == NULL || !sActors.platform.totemDefeated(sActors.platform.ctx, pad->totem)) {
        sActors.padDenied = TRUE; // denied: explicitly NOT marked used
        return DW_ACTOR_EVENT_NONE;
    }
    // Fire the pad's engine-a sigil (the sigil entry carries target group + set value). If
    // no sigil exists at the pad tile the table is wrong: leave the pad unused (retryable)
    // and report nothing, so a broken table is visible instead of silently consumed.
    pressed = 0;
    if (sActors.platform.pressSigil != NULL) {
        pressed = sActors.platform.pressSigil(sActors.platform.ctx, pad->tile.x, pad->tile.y,
            pad->tile.z, pad->tile.surface, DW_ACTOR_OCCUPANT_PLAYER);
    }
    if (!pressed) {
        sActors.padDenied = TRUE;
        return DW_ACTOR_EVENT_NONE;
    }
    sActors.padUsed |= (u8)(1 << padIndex);
    sActors.padDenied = FALSE;
    sActors.pendingCutin = (s8)pad->totem;
    if (pad->totem == DW_ACTOR_TOTEM_SKARMORY) {
        // The rift script plays the carry (Lost Tower Act 4 machinery); actors never step
        // the player tile-by-tile over VOID.
        sActors.carryPending = (s8)padIndex;
        return DW_ACTOR_EVENT_CARRY_REQUESTED;
    }
    return DW_ACTOR_EVENT_CUTIN;
}

int DwActors_TakePendingCutin(void)
{
    int cutin = sActors.pendingCutin;

    sActors.pendingCutin = -1;
    return cutin;
}

void DwActors_ConfirmCarryDone(void)
{
    sActors.carryPending = -1;
}

void DwActors_OnCheckpoint(void)
{
    int i;

    if (!sActors.active) {
        return;
    }
    for (i = 0; i < DW_ACTORS_MAX_STONES; i++) {
        sActors.snapshot.stones[i] = sActors.stones[i];
    }
    sActors.snapshot.shadowPhase = sActors.shadowPhase;
    sActors.snapshot.shadowDir = sActors.shadowDir;
    sActors.snapshot.shadowFrameCounter = sActors.shadowFrameCounter;
    sActors.snapshot.padUsed = sActors.padUsed;
}

void DwActors_OnFallReset(void)
{
    int i;

    if (!sActors.active) {
        return;
    }
    for (i = 0; i < sActors.table->stoneCount; i++) {
        sActors.stones[i] = sActors.snapshot.stones[i];
    }
    sActors.shadowPhase = sActors.snapshot.shadowPhase;
    sActors.shadowDir = sActors.snapshot.shadowDir;
    sActors.shadowFrameCounter = sActors.snapshot.shadowFrameCounter;
    sActors.shadowGrace = DW_SHADOW_SPAWN_GRACE_FRAMES;
    sActors.shadowState = sActors.table->shadow.tileCount > 0 ? DW_ACTOR_SHADOW_PATROL : DW_ACTOR_SHADOW_INACTIVE;
    sActors.shadowCaughtTimer = 0;
    sActors.catchResetIssued = FALSE;
    sActors.catchWatchdog = 0;
    sActors.echoTile = TileNone(DW_ACTOR_SURFACE_FLOOR);
    sActors.echoShown = FALSE;
    sActors.echoBlocked = FALSE;
    if (sActors.platform.releaseSigils != NULL) {
        sActors.platform.releaseSigils(sActors.platform.ctx, DW_ACTOR_OCCUPANT_ECHO);
    }
    sActors.pendingPad = -1;
    sActors.padUsed = sActors.snapshot.padUsed;
    sActors.padDenied = FALSE;
    sActors.pendingCutin = -1;
    sActors.carryPending = -1;
    if (sActors.platform.setInputLocked != NULL) {
        sActors.platform.setInputLocked(sActors.platform.ctx, FALSE);
    }
    SyncActorTiles();
}

BOOL DwActors_IsStoneAt(DwActorTile tile)
{
    int i;

    if (!sActors.active) {
        return FALSE;
    }
    for (i = 0; i < sActors.table->stoneCount; i++) {
        if (sActors.stones[i].state == DW_ACTOR_STONE_RESTING && TileEq(tile, sActors.stones[i].tile)) {
            return TRUE;
        }
    }
    return FALSE;
}

void DwActors_FillDebug(DwActorDebug *out)
{
    int i;
    DwActorTile shadow, echo;

    if (out == NULL) {
        return;
    }
    memset(out, 0, sizeof(*out));
    if (!sActors.active) {
        out->pendingPad = -1;
        out->carryPending = -1;
        for (i = 0; i < DW_ACTORS_MAX_STONES; i++) {
            out->stoneTiles[i][0] = DW_ACTOR_TILE_NONE;
            out->stoneTiles[i][1] = DW_ACTOR_TILE_NONE;
            out->stoneTiles[i][2] = DW_ACTOR_TILE_NONE;
            out->stoneSurfaces[i] = DW_ACTOR_SURFACE_FLOOR;
        }
        out->shadowTile[0] = DW_ACTOR_TILE_NONE;
        out->shadowTile[1] = DW_ACTOR_TILE_NONE;
        out->shadowTile[2] = DW_ACTOR_TILE_NONE;
        out->shadowSurface = DW_ACTOR_SURFACE_FLOOR;
        out->echoTile[0] = DW_ACTOR_TILE_NONE;
        out->echoTile[1] = DW_ACTOR_TILE_NONE;
        out->echoTile[2] = DW_ACTOR_TILE_NONE;
        out->echoSurface = DW_ACTOR_SURFACE_FLOOR;
        return;
    }
    out->stoneCount = sActors.table->stoneCount;
    for (i = 0; i < DW_ACTORS_MAX_STONES; i++) {
        out->stoneStates[i] = sActors.stones[i].state;
        out->stoneTiles[i][0] = sActors.stones[i].tile.x;
        out->stoneTiles[i][1] = sActors.stones[i].tile.y;
        out->stoneTiles[i][2] = sActors.stones[i].tile.z;
        out->stoneSurfaces[i] = sActors.stones[i].tile.surface;
    }
    shadow = ShadowTile();
    out->shadowTile[0] = shadow.x;
    out->shadowTile[1] = shadow.y;
    out->shadowTile[2] = shadow.z;
    out->shadowSurface = shadow.surface;
    out->shadowPhase = sActors.shadowPhase;
    out->shadowState = sActors.shadowState;
    echo = sActors.echoShown ? sActors.echoTile : TileNone(sActors.table->echo.echoSurface);
    out->echoTile[0] = echo.x;
    out->echoTile[1] = echo.y;
    out->echoTile[2] = echo.z;
    out->echoSurface = echo.surface;
    out->echoBlocked = sActors.echoBlocked ? 1 : 0;
    out->echoSigilPresses = sActors.echoSigilPresses;
    out->pendingPad = sActors.pendingPad;
    out->padUsed = sActors.padUsed;
    out->padDenied = sActors.padDenied ? 1 : 0;
    out->caughtCount = sActors.caughtCount;
    out->carryPending = sActors.carryPending;
    out->respawnRequests = sActors.respawnRequests;
}

// ---------------------------------------------------------------------------
// Debug-only test table (host test + engine-a's test map if it wants actors)
// Surfaces: stones on the west wall, shadow/pads on base ground (GROUND), echo
// player-side west wall -> echo-side east wall, mirrored in z over [12, 20].
// ---------------------------------------------------------------------------

const DwActorTable gDwActorsTestTable = {
    {
        // Stone 0: west wall, pushed +z; edge (11,3,18) falls to the ground gap (12,1,18).
        { { 11, 3, 14, DW_ACTOR_SURFACE_WEST_WALL, 0 },
            { { { 11, 3, 18, DW_ACTOR_SURFACE_WEST_WALL, 0 }, { 12, 1, 18, DW_ACTOR_SURFACE_GROUND, 0 } } }, 1, 0 },
        // Stone 1: west wall, blocks stone 0's push at (11,3,16).
        { { 11, 3, 16, DW_ACTOR_SURFACE_WEST_WALL, 0 },
            { { { 0, 0, 0, 0, 0 }, { 0, 0, 0, 0, 0 } } }, 0, 0 },
    },
    2,
    { 0, 0, 0 },
    // Shadow: one slow lane on the ground (test uses a short beat; Arc 2 tables use 45-60).
    { { { 12, 1, 12, DW_ACTOR_SURFACE_GROUND, 0 }, { 12, 1, 13, DW_ACTOR_SURFACE_GROUND, 0 },
          { 12, 1, 14, DW_ACTOR_SURFACE_GROUND, 0 }, { 12, 1, 15, DW_ACTOR_SURFACE_GROUND, 0 },
          { 12, 1, 16, DW_ACTOR_SURFACE_GROUND, 0 } }, 5, 6, 1 },
    // Echo: player on the west wall -> echo on the east wall, mirrored in z over [12, 20].
    // Echo sigil at (49,3,18): player at (11,3,14) puts the echo on it.
    { 1, DW_ACTOR_SURFACE_WEST_WALL, DW_ACTOR_SURFACE_EAST_WALL, DW_ACTOR_AXIS_X, 49,
        DW_ACTOR_MIRROR_Z, 12, 20,
        { { 49, 3, 18, DW_ACTOR_SURFACE_EAST_WALL, 0 } }, 1 },
    // Pads on the ground: Hitmonlee / Vespiquen / Lapras / Skarmory.
    {
        { { 12, 1, 13, DW_ACTOR_SURFACE_GROUND, 0 }, DW_ACTOR_TOTEM_HITMONLEE, 0 },
        { { 12, 1, 14, DW_ACTOR_SURFACE_GROUND, 0 }, DW_ACTOR_TOTEM_VESPIQUEN, 0 },
        { { 12, 1, 15, DW_ACTOR_SURFACE_GROUND, 0 }, DW_ACTOR_TOTEM_LAPRAS, 0 },
        { { 12, 1, 16, DW_ACTOR_SURFACE_GROUND, 0 }, DW_ACTOR_TOTEM_SKARMORY, 0 },
    },
    4,
    { 0, 0, 0 },
    // Protected: the checkpoint tile (12,1,12) and a wall tile behind stone 0.
    { { 12, 1, 12, DW_ACTOR_SURFACE_GROUND, 0 }, { 11, 3, 13, DW_ACTOR_SURFACE_WEST_WALL, 0 } },
    2,
    { 0, 0, 0 },
};

#ifndef DW_ACTORS_HOST_TEST
// ---------------------------------------------------------------------------
// ROM glue: platform callbacks, visuals
// ---------------------------------------------------------------------------

static const u16 sTotemFlags[DW_ACTOR_TOTEM_COUNT] = {
    FLAG_TOTEM_HITMONLEE_DEFEATED,
    FLAG_TOTEM_VESPIQUEN_DEFEATED,
    FLAG_TOTEM_LAPRAS_DEFEATED,
    FLAG_TOTEM_SKARMORY_DEFEATED,
};

static DwActorTileKind RomTileAt(void *ctx, int x, int y, int z, int surface)
{
    FieldSystem *fieldSystem = (FieldSystem *)ctx;
    DwPuzzleTileState state = DwPuzzle_QueryTile(fieldSystem, x, y, z, surface);

    switch (state) {
    case DW_PUZZLE_TILE_SOLID:
        return DW_ACTOR_TILE_SOLID;
    case DW_PUZZLE_TILE_BLOCKED:
        return DW_ACTOR_TILE_BLOCKED;
    case DW_PUZZLE_TILE_VOID:
        return DW_ACTOR_TILE_VOID;
    default:
        break;
    }
    // DEFAULT: the stock grid on the queried surface decides. The queried surface is the
    // player's current surface (gDwPuzzleDebug.surface, refreshed by engine-a's hooks) in
    // every actors query that matters; a tile on any other surface reads INVALID here and
    // is BLOCKED (actors_design.md section 2: cross-surface actor tiles need explicit
    // engine-a state). GROUND has no platform grid and no reachable stock-terrain query
    // from actors, so a DEFAULT ground tile reads BLOCKED too (fail closed): rift tables
    // must give explicit states for ground actor tiles.
    if (surface != (int)gDwPuzzleDebug.surface) {
        return DW_ACTOR_TILE_BLOCKED;
    }
    if (surface == DW_PUZZLE_SURFACE_GROUND) {
        return DW_ACTOR_TILE_BLOCKED;
    }
    if (DistWorld_CheckCollisionOnCurrentFloatingPlatform(fieldSystem, x, y, z)) {
        return DW_ACTOR_TILE_BLOCKED;
    }
    return DW_ACTOR_TILE_WALKABLE;
}

static void RomSetActorTile(void *ctx, int index, int x, int y, int z, int surface, DwActorTileKind state, int present)
{
    DwPuzzleTileState engineState;

    (void)ctx;
    switch (state) {
    case DW_ACTOR_TILE_SOLID:
        engineState = DW_PUZZLE_TILE_SOLID;
        break;
    case DW_ACTOR_TILE_BLOCKED:
        engineState = DW_PUZZLE_TILE_BLOCKED;
        break;
    case DW_ACTOR_TILE_VOID:
        engineState = DW_PUZZLE_TILE_VOID;
        break;
    default:
        engineState = DW_PUZZLE_TILE_DEFAULT;
        break;
    }
    DwPuzzle_SetActorTile(index, x, y, z, surface, engineState, present ? TRUE : FALSE);
}

static void RomClearActorTiles(void *ctx)
{
    (void)ctx;
    DwPuzzle_ClearActorTiles();
}

static int RomPressSigil(void *ctx, int x, int y, int z, int surface, int occupant)
{
    return DwPuzzle_PressSigil((FieldSystem *)ctx, x, y, z, surface, occupant) ? TRUE : FALSE;
}

static void RomReleaseSigils(void *ctx, int occupant)
{
    DwPuzzle_ReleaseSigils((FieldSystem *)ctx, occupant);
}

static void RomRequestCheckpointRespawn(void *ctx)
{
    DwPuzzle_RequestCheckpointRespawn((FieldSystem *)ctx);
}

static void RomSetPlayerTile(void *ctx, int x, int y, int z)
{
    // Push-back safety net only (the glue should have called TryPush pre-move): move the
    // player object back with the stock MapObject API, keeping its facing. This does not
    // touch the DW platform state, which is why it is a last resort, not a path.
    FieldSystem *fieldSystem = (FieldSystem *)ctx;
    MapObject *playerObj = fieldSystem != NULL ? Player_MapObject(fieldSystem->playerAvatar) : NULL;

    if (playerObj != NULL) {
        MapObject_SetPosDirFromCoords(playerObj, x, 2 * y, z, (int)MapObject_GetFacingDir(playerObj));
        MapObject_UpdateCoords(playerObj);
    }
}

static void RomSetInputLocked(void *ctx, int locked)
{
    // The catch freeze: pause the player object's movement with the stock MapObject API.
    FieldSystem *fieldSystem = (FieldSystem *)ctx;
    MapObject *playerObj = fieldSystem != NULL ? Player_MapObject(fieldSystem->playerAvatar) : NULL;

    if (playerObj == NULL) {
        return;
    }
    if (locked) {
        MapObject_SetPauseMovementOn(playerObj);
    } else {
        MapObject_SetPauseMovementOff(playerObj);
    }
}

static int RomIsScriptRunning(void *ctx)
{
    // A script is running while the ScriptManager has active contexts (set to 1 when a
    // script starts, decremented as its contexts finish). The pad/carry/CAUGHT windows
    // freeze the patrol in-core as well; shadow lanes must still avoid script tiles
    // (actors_design.md section 4) as defence in depth.
    // Safety: FieldSystem_GetScriptMemberPtr asserts that the current field task's env
    // is a ScriptManager - it dereferences fieldSystem->task and its magic. During idle
    // frames task can be NULL, and other field tasks have different envs, so calling it
    // blindly would NULL-deref or trip the assert. Guard first: no task, or an env whose
    // first word is not the ScriptManager magic, means no script is running.
    FieldSystem *fieldSystem = (FieldSystem *)ctx;
    void *env;
    u8 *numActive;

    if (fieldSystem == NULL || fieldSystem->task == NULL) {
        return FALSE;
    }
    env = FieldTask_GetEnv(fieldSystem->task);
    if (env == NULL || *(u32 *)env != SCRIPT_MANAGER_MAGIC_NUMBER) {
        return FALSE;
    }
    numActive = (u8 *)FieldSystem_GetScriptMemberPtr(fieldSystem, SCRIPT_MANAGER_NUM_ACTIVE_CONTEXTS);
    return (numActive != NULL && *numActive > 0) ? TRUE : FALSE;
}

static int RomTotemDefeated(void *ctx, int totem)
{
    FieldSystem *fieldSystem = (FieldSystem *)ctx;

    if (totem < 0 || totem >= DW_ACTOR_TOTEM_COUNT) {
        return FALSE;
    }
    return VarsFlags_CheckFlag(SaveData_GetVarsFlags(fieldSystem->saveData), sTotemFlags[totem]) ? TRUE : FALSE;
}

static u32 RomGetResetGeneration(void *ctx)
{
    (void)ctx;
    return gDwPuzzleDebug.resetGeneration;
}

static void RomPlayCatchEffect(void *ctx)
{
    (void)ctx;
    Sound_PlayPokemonCry(SPECIES_GIRATINA, 0);
}

static DwActorPlatform RomPlatform(FieldSystem *fieldSystem)
{
    DwActorPlatform platform;

    memset(&platform, 0, sizeof(platform));
    platform.tileAt = RomTileAt;
    platform.setActorTile = RomSetActorTile;
    platform.clearActorTiles = RomClearActorTiles;
    platform.pressSigil = RomPressSigil;
    platform.releaseSigils = RomReleaseSigils;
    platform.requestCheckpointRespawn = RomRequestCheckpointRespawn;
    platform.setPlayerTile = RomSetPlayerTile;
    platform.setInputLocked = RomSetInputLocked;
    platform.isScriptRunning = RomIsScriptRunning;
    platform.totemDefeated = RomTotemDefeated;
    platform.getResetGeneration = RomGetResetGeneration;
    platform.playCatchEffect = RomPlayCatchEffect;
    platform.ctx = fieldSystem;
    return platform;
}

// The glue registers a table with this helper (engine-a's map-load hook calls it); it
// builds the ROM platform for the FieldSystem. Pass table == NULL for inert maps.
void DwActors_RegisterTable(FieldSystem *fieldSystem, const DwActorTable *table)
{
    DwActorPlatform platform = RomPlatform(fieldSystem);

    DwActors_Init(table, &platform);
}

void DwActors_SyncDebug(void)
{
    DwActorDebug dbg;
    int i;

    DwActors_FillDebug(&dbg);
    gDwPuzzleDebug.stoneCount = dbg.stoneCount;
    // dwp:engine-a (4): stone states (RESTING/FALLING/LANDED) for the harness.
    for (i = 0; i < DW_PUZZLE_MAX_STONES; i++) {
        gDwPuzzleDebug.stoneStates[i] = (u8)(i < DW_ACTORS_MAX_STONES ? dbg.stoneStates[i] : DW_ACTOR_STONE_RESTING);
    }
    for (i = 0; i < DW_PUZZLE_MAX_STONES; i++) {
        if (i < DW_ACTORS_MAX_STONES) {
            gDwPuzzleDebug.stones[i].x = dbg.stoneTiles[i][0];
            gDwPuzzleDebug.stones[i].y = dbg.stoneTiles[i][1];
            gDwPuzzleDebug.stones[i].z = dbg.stoneTiles[i][2];
            gDwPuzzleDebug.stones[i].present = (u8)(i < dbg.stoneCount ? 1 : 0);
            gDwPuzzleDebug.stones[i].surface = dbg.stoneSurfaces[i];
        } else {
            gDwPuzzleDebug.stones[i].present = 0;
        }
    }
    gDwPuzzleDebug.shadowPhase = dbg.shadowPhase;
    gDwPuzzleDebug.shadow.x = dbg.shadowTile[0];
    gDwPuzzleDebug.shadow.y = dbg.shadowTile[1];
    gDwPuzzleDebug.shadow.z = dbg.shadowTile[2];
    gDwPuzzleDebug.shadow.present = (u8)(dbg.shadowState != DW_ACTOR_SHADOW_INACTIVE ? 1 : 0);
    gDwPuzzleDebug.shadow.surface = dbg.shadowSurface;
    gDwPuzzleDebug.echo.x = dbg.echoTile[0];
    gDwPuzzleDebug.echo.y = dbg.echoTile[1];
    gDwPuzzleDebug.echo.z = dbg.echoTile[2];
    gDwPuzzleDebug.echo.present = (u8)(dbg.echoTile[0] != DW_ACTOR_TILE_NONE ? 1 : 0);
    gDwPuzzleDebug.echo.surface = dbg.echoSurface;
}

// --- Visuals: one MapObject per actor, all MAP_OBJ_STATUS_18 (non-colliding) ---------

// Display position for a tile: wall actors stand one tile in front of the face (x=12 west,
// x=48 east); floor/ground/ceiling actors stand on their tile.
static void DisplayPos(DwActorTile tile, int *outX, int *outY, int *outZ)
{
    if (tile.surface == DW_ACTOR_SURFACE_WEST_WALL) {
        *outX = 12;
        *outY = tile.y;
        *outZ = tile.z;
    } else if (tile.surface == DW_ACTOR_SURFACE_EAST_WALL) {
        *outX = 48;
        *outY = tile.y;
        *outZ = tile.z;
    } else {
        *outX = tile.x;
        *outY = tile.y;
        *outZ = tile.z;
    }
}

static MapObject *sStoneObjs[DW_ACTORS_MAX_STONES];
static MapObject *sShadowObj;
static MapObject *sEchoObj;

static MapObject *SpawnActorObject(FieldSystem *fieldSystem, int dispX, int dispZ, u16 graphicsID)
{
    MapObject *obj = MapObjectMan_AddMapObject(fieldSystem->mapObjMan, dispX, dispZ, DIR_SOUTH,
        graphicsID, MOVEMENT_TYPE_NONE, fieldSystem->location->mapId);

    if (obj == NULL) {
        return NULL;
    }
    MapObject_SetHeightCalculationDisabled(obj, TRUE);
    MapObject_SetStatusFlagOn(obj, MAP_OBJ_STATUS_18);
    return obj;
}

// Position an actor object at a tile (SetPosDirFromCoords takes y = 2 * tile y, mirroring
// the DW overlay spawn in ov9_0224EF64).
static void PlaceActorObject(MapObject *obj, DwActorTile tile)
{
    int dx, dy, dz;

    DisplayPos(tile, &dx, &dy, &dz);
    MapObject_SetPosDirFromCoords(obj, dx, 2 * dy, dz, DIR_SOUTH);
}

static void DeleteObj(MapObject **slot)
{
    if (*slot != NULL) {
        MapObject_Delete(*slot);
        *slot = NULL;
    }
}

void DwActors_VisualsInit(FieldSystem *fieldSystem)
{
    DwActors_VisualsUpdate(fieldSystem);
}

void DwActors_VisualsUpdate(FieldSystem *fieldSystem)
{
    int i;
    DwActorDebug dbg;

    if (fieldSystem == NULL) {
        return;
    }
    if (!sActors.active) {
        return;
    }
    DwActors_FillDebug(&dbg);
    for (i = 0; i < sActors.table->stoneCount; i++) {
        DwActorTile tile;

        tile.x = dbg.stoneTiles[i][0];
        tile.y = dbg.stoneTiles[i][1];
        tile.z = dbg.stoneTiles[i][2];
        tile.surface = dbg.stoneSurfaces[i];
        tile.padding = 0;
        if (sStoneObjs[i] == NULL) {
            int dx, dy, dz;

            DisplayPos(tile, &dx, &dy, &dz);
            sStoneObjs[i] = SpawnActorObject(fieldSystem, dx, dz, OBJ_EVENT_GFX_STRENGTH_BOULDER);
        }
        if (sStoneObjs[i] != NULL) {
            // FALLING stones are between surfaces: hidden, nothing drawn in the void.
            MapObject_SetHidden(sStoneObjs[i], dbg.stoneStates[i] == DW_ACTOR_STONE_FALLING ? TRUE : FALSE);
            if (dbg.stoneStates[i] != DW_ACTOR_STONE_FALLING) {
                PlaceActorObject(sStoneObjs[i], tile);
            }
        }
    }
    if (sActors.table->shadow.tileCount > 0) {
        DwActorTile tile;

        tile.x = dbg.shadowTile[0];
        tile.y = dbg.shadowTile[1];
        tile.z = dbg.shadowTile[2];
        tile.surface = dbg.shadowSurface;
        tile.padding = 0;
        if (sShadowObj == NULL && !TileIsNone(tile)) {
            int dx, dy, dz;

            DisplayPos(tile, &dx, &dy, &dz);
            sShadowObj = SpawnActorObject(fieldSystem, dx, dz, OBJ_EVENT_GFX_RIFT_ARC2);
        }
        if (sShadowObj != NULL && !TileIsNone(tile)) {
            PlaceActorObject(sShadowObj, tile);
        }
    }
    if (sActors.table->echo.active) {
        DwActorTile tile;

        tile.x = dbg.echoTile[0];
        tile.y = dbg.echoTile[1];
        tile.z = dbg.echoTile[2];
        tile.surface = dbg.echoSurface;
        tile.padding = 0;
        if (sEchoObj == NULL && !TileIsNone(tile)) {
            int dx, dy, dz;
            MapObject *playerObj = Player_MapObject(fieldSystem->playerAvatar);
            u32 gfx = playerObj != NULL ? MapObject_GetGraphicsID(playerObj) : OBJ_EVENT_GFX_CYRUS;

            DisplayPos(tile, &dx, &dy, &dz);
            sEchoObj = SpawnActorObject(fieldSystem, dx, dz, (u16)gfx);
        }
        if (sEchoObj != NULL) {
            MapObject_SetHidden(sEchoObj, TileIsNone(tile) ? TRUE : FALSE);
            if (!TileIsNone(tile)) {
                MapObject *playerObj = Player_MapObject(fieldSystem->playerAvatar);

                if (playerObj != NULL && MapObject_GetGraphicsID(sEchoObj) != MapObject_GetGraphicsID(playerObj)) {
                    sub_02061AB4(sEchoObj, MapObject_GetGraphicsID(playerObj));
                }
                PlaceActorObject(sEchoObj, tile);
            }
        }
    }
    DwActors_SyncDebug();
}

void DwActors_VisualsExit(FieldSystem *fieldSystem)
{
    int i;

    // Map unload: delete the objects and NULL the pointers (the MapObjectManager will free
    // them anyway; this stops VisualsUpdate from touching dangling pointers). Core state
    // is untouched: same-map reloads keep the snapshot, departures call DwActors_OnExit.
    (void)fieldSystem;
    for (i = 0; i < DW_ACTORS_MAX_STONES; i++) {
        DeleteObj(&sStoneObjs[i]);
    }
    DeleteObj(&sShadowObj);
    DeleteObj(&sEchoObj);
}

#endif // DW_ACTORS_HOST_TEST
