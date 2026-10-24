// Distortion World puzzle engine (engine-a).
//
// Data-driven core for the DW puzzle rifts (docs/distortion_world/PUZZLE_PLAN.md
// section 3; API and table guide in include/overlay009/dw_puzzle.h and
// tools/distortion_world/README.md). The ov9 glue calls DwPuzzle_HandleStep /
// DwPuzzle_HandleFrame / DwPuzzle_QueryTile and acts on the results; this
// file owns all runtime behaviour and never touches ov9 internals.
//
// State is RAM-only statics. That is deliberate: a fall warp reloads the
// same map, and the state must survive it. Persistent once-only flags are
// never touched, so the Lost Tower's keep working. A fresh entry (no fall
// pending at map load) resets the puzzle; a save/load also resets it, which
// is the safe fallback.

#include <nitro.h>
#include <string.h>

#include "generated/map_headers.h"
#include "generated/sdat.h"
#include "generated/vars_flags.h"

#include "field/field_system.h"
#include "overlay009/dw_puzzle.h"

#include "location.h"
#include "map_object.h"
#include "player_avatar.h"
#include "savedata_misc.h"
#include "sound_playback.h"
#include "vars_flags.h"

DwPuzzleDebug gDwPuzzleDebug;
BOOL gDwPuzzleTestMode = FALSE;

// The registry: one extern + one line per rift table (dw_puzzle_<map>.c).
extern const DwPuzzleTable gDwPuzzleTestTable;
extern const DwPuzzleTable gDwPuzzleTestEternaTable;
extern const DwPuzzleTable gDwPuzzleLostTowerV1Table; // dwp:rift-lt
extern const DwPuzzleTable gDwPuzzleLostTowerV2Table; // dwp:rift-lt
extern const DwActorTable gDwActorsLostTowerTable; // dwp:rift-lt (visit 2)
extern const DwPuzzleTable gDwPuzzleRavagedPathTable; // dwp:rift-rp
extern const DwPuzzleTable gDwPuzzleEternaForestTable;
extern const DwPuzzleTable gDwPuzzleRoute214Table; // dwp:rift-214
// dwp:rift-213
extern const DwPuzzleTable gDwPuzzleRoute213Table;
extern const DwActorTable gDwPuzzleRoute213ActorTable;

static const DwPuzzleTable *const sPuzzleTables[] = {
    &gDwPuzzleTestTable,
    &gDwPuzzleTestEternaTable,
    &gDwPuzzleLostTowerV1Table, // dwp:rift-lt
    &gDwPuzzleLostTowerV2Table, // dwp:rift-lt
    &gDwPuzzleRavagedPathTable,
    &gDwPuzzleEternaForestTable,
    &gDwPuzzleRoute214Table, // dwp:rift-214
    // dwp:rift-213
    &gDwPuzzleRoute213Table,
};

// Rift actor tables (engine-b), one per puzzle table, NULL until the
// rift workstream ships one in its dw_puzzle_<map>.c. The glue registers
// the map's actor table on map load (DwActors_RegisterTable).
static const DwActorTable *const sActorTables[] = {
    NULL, // Ravaged Path test table: no actor table yet
    NULL, // Eterna Forest test table: no actor table yet
    NULL, // dwp:rift-lt: Lost Tower visit 1: no actor table (Phase 0 acts)
    &gDwActorsLostTowerTable, // dwp:rift-lt: Lost Tower visit 2: pads + shadow
    NULL, // Ravaged Path production table: no actors // dwp:rift-rp
    NULL, // Eterna Forest production table: no actor table
    NULL, // DW Route 214: no actor table (currents + sigils only)
    // dwp:rift-213
    &gDwPuzzleRoute213ActorTable,
};



// ---- runtime state (main-binary RAM; see DwPuzzleState) ---------------
#define sTable (gDwPuzzleState.table)
#define sPrevTable (gDwPuzzleState.prevTable)
#define sTableMap (gDwPuzzleState.tableMap)
#define sFreshResetPending (gDwPuzzleState.freshResetPending)
#define sFallPending (gDwPuzzleState.fallPending)
#define sFallRestored (gDwPuzzleState.fallRestored)
#define sFallX (gDwPuzzleState.fallX)
#define sFallY (gDwPuzzleState.fallY)
#define sFallZ (gDwPuzzleState.fallZ)
#define sRespawnPending (gDwPuzzleState.respawnPending)
#define sRespawnRestored (gDwPuzzleState.respawnRestored)
#define sTrackingValid (gDwPuzzleState.trackingValid)
#define sLastX (gDwPuzzleState.lastX)
#define sLastY (gDwPuzzleState.lastY)
#define sLastZ (gDwPuzzleState.lastZ)
#define sLastSurface (gDwPuzzleState.lastSurface)
#define sLastTileState (gDwPuzzleState.lastTileState)
#define sFrameCount (gDwPuzzleState.frameCount)
#define sFallCount (gDwPuzzleState.fallCount)
#define sResetGeneration (gDwPuzzleState.resetGeneration)
#define sLastEvent (gDwPuzzleState.lastEvent)
#define sLastEventFrame (gDwPuzzleState.lastEventFrame)
#define sLastEventGroup (gDwPuzzleState.lastEventGroup)
#define sFlashFrames (gDwPuzzleState.flashFrames)
#define sGroupBase (gDwPuzzleState.groupBase)
#define sGroupTarget (gDwPuzzleState.groupTarget)
#define sGroupOn (gDwPuzzleState.groupOn)
#define sGroupDisplay (gDwPuzzleState.groupDisplay)
#define sGroupTimer (gDwPuzzleState.groupTimer)
#define sMomentaryHolders (gDwPuzzleState.momentaryHolders)
#define sSigilPressed (gDwPuzzleState.sigilPressed)
#define sCheckpointIndex (gDwPuzzleState.checkpointIndex)
#define sSnapGroupBase (gDwPuzzleState.snapGroupBase)
#define sSliding (gDwPuzzleState.sliding)
#define sSlideDir (gDwPuzzleState.slideDir)
#define sSlideFrames (gDwPuzzleState.slideFrames)
#define sSlideSteps (gDwPuzzleState.slideSteps)
/* Actor tiles stay in overlay 9 (see DwPuzzleState): engine-b re-syncs
 * them on every map load, and the harness pokes them by xMAP symbol. */
static DwPuzzleActorTile sActorTiles[DW_PUZZLE_MAX_ACTOR_BLOCKS];

#define sCachedTestMode (gDwPuzzleState.cachedTestMode)
#define sCachedProgress (gDwPuzzleState.cachedProgress)

// ---- helpers ---------------------------------------------------------------

static u16 PuzzleProgress(FieldSystem *fieldSystem)
{
    if (fieldSystem == NULL || fieldSystem->saveData == NULL) {
        return 0;
    }
    return *VarsFlags_GetVarAddress(SaveData_GetVarsFlags(fieldSystem->saveData), VAR_ARC2_PROGRESS);
}

static void PuzzleSetEvent(u32 event, u32 group)
{
    sLastEvent = event;
    sLastEventFrame = sFrameCount;
    sLastEventGroup = group;
}

static BOOL SurfaceMatches(u8 entrySurface, int surface)
{
    return entrySurface == DW_PUZZLE_SURFACE_ANY || entrySurface == (u8)surface;
}

static int GroupFadeOut(const DwPuzzleGroup *group)
{
    if (group->ghostPropGroup == DW_PUZZLE_GHOST_GROUP_NONE) {
        return 0;
    }
    return group->fadeOutFrames != 0 ? group->fadeOutFrames : DW_PUZZLE_FADE_OUT_FRAMES;
}

static int GroupFadeInLead(const DwPuzzleGroup *group)
{
    if (group->ghostPropGroup == DW_PUZZLE_GHOST_GROUP_NONE) {
        return 0;
    }
    return group->fadeInLeadFrames != 0 ? group->fadeInLeadFrames : DW_PUZZLE_FADE_IN_LEAD;
}

// Apply a new effective target to a group, starting its fade. If the solid
// state already equals the target (a re-flip mid-fade), just fix the
// display and stop the timer: the honeycomb rule is about what is drawn,
// and the tile is already in the state the target asks for.
static void GroupSetTarget(int i, u8 target)
{
    const DwPuzzleGroup *group = &sTable->groups[i];

    if (sGroupTarget[i] == target && sGroupTimer[i] == 0) {
        return;
    }

    sGroupTarget[i] = target;
    sGroupDisplay[i] = target;

    if (sGroupOn[i] == target) {
        sGroupTimer[i] = 0;
        return;
    }

    sGroupTimer[i] = target ? GroupFadeInLead(group) : GroupFadeOut(group);
    if (sGroupTimer[i] == 0) {
        sGroupOn[i] = target;
    }
}

// The effective target from base + momentary holders (any occupant).
static void GroupRefreshTarget(int i)
{
    u8 target = sGroupBase[i];

    if (sMomentaryHolders[i] != 0) {
        target = 1;
    }
    GroupSetTarget(i, target);
}

static void TakeSnapshot(void)
{
    for (int i = 0; i < sTable->groupCount; i++) {
        sSnapGroupBase[i] = sGroupBase[i];
    }
}

// Restore semantics (reset sigil, shadow catch, fall respawn): the
// snapshot's LOGICAL base state is restored; target / solid / display all
// snap to it (fade timers cleared, props snap, no fade). Momentary holds
// are NOT in the snapshot: holders are cleared for every occupant
// (occupants must re-press after a restore), so the restored target is
// the base, not the snapshot-time held value. Slide cleared; actors
// notified via resetGeneration (engine-b restores its own snapshot when
// the generation changes).
static void RestoreSnapshot(void)
{
    if (sTable == NULL) {
        return;
    }
    for (int i = 0; i < sTable->groupCount; i++) {
        sGroupBase[i] = sSnapGroupBase[i];
        sGroupTarget[i] = sSnapGroupBase[i];
        sGroupOn[i] = sSnapGroupBase[i];
        sGroupDisplay[i] = sSnapGroupBase[i];
        sGroupTimer[i] = 0;
        sMomentaryHolders[i] = 0;
    }
    memset(sSigilPressed, 0, sizeof(sSigilPressed));
    sSliding = FALSE;
    sResetGeneration++;
    gDwPuzzleDebug.resetGeneration = sResetGeneration;
}

static void ResetPuzzleToInitial(void)
{
    if (sTable == NULL) {
        return;
    }
    for (int i = 0; i < sTable->groupCount; i++) {
        sGroupBase[i] = sTable->groups[i].initialOn ? 1 : 0;
        sGroupTarget[i] = sGroupBase[i];
        sGroupOn[i] = sGroupBase[i];
        sGroupDisplay[i] = sGroupBase[i];
        sGroupTimer[i] = 0;
        sMomentaryHolders[i] = 0;
    }
    memset(sSigilPressed, 0, sizeof(sSigilPressed));
    sCheckpointIndex = 0;
    sSliding = FALSE;
    sFallPending = FALSE;
    sFallRestored = FALSE;
    sRespawnPending = FALSE;
    sRespawnRestored = FALSE;
    sResetGeneration++;
    gDwPuzzleDebug.resetGeneration = sResetGeneration;
    TakeSnapshot();
}

// Resolve the table for a map, honouring the progress gate and the test
// gate. Test tables win while test mode is on; production tables are the
// fallback. Returns NULL for a map with no puzzle.
static const DwPuzzleTable *FindTable(u32 mapHeader, u16 progress)
{
    const DwPuzzleTable *production = NULL;

    for (u32 i = 0; i < NELEMS(sPuzzleTables); i++) {
        const DwPuzzleTable *table = sPuzzleTables[i];

        if (table == NULL || table->mapHeader != mapHeader) {
            continue;
        }
        if (table->minProgress != 0 || table->maxProgress != 0) {
            if (progress < table->minProgress || progress > table->maxProgress) {
                continue;
            }
        }
        if (table->testOnly) {
            if (gDwPuzzleTestMode) {
                return table;
            }
            continue;
        }
        production = table;
    }
    return production;
}

// The actor table for a map: the one parallel to the ACTIVE puzzle
// table (progress + test gated), not the first table for the map.
// Lost Tower's visit gate lives here: for progress 92-93 FindTable
// returns the visit-1 puzzle table (whose parallel actor table is
// NULL, so actors stay inert); for progress 94 it returns the visit-2
// puzzle table and its actor table. Selecting by map alone would return
// the first match and could never distinguish the visits.
const DwActorTable *DwPuzzle_GetActorTable(FieldSystem *fieldSystem, u32 mapHeader)
{
    const DwPuzzleTable *table = FindTable(mapHeader, PuzzleProgress(fieldSystem));

    if (table == NULL) {
        return NULL;
    }
    for (u32 i = 0; i < NELEMS(sPuzzleTables); i++) {
        if (sPuzzleTables[i] == table) {
            return sActorTables[i];
        }
    }
    return NULL;
}

// Activate (or deactivate) for this map, applying a pending fresh reset.
// Returns TRUE when a table is active.
static BOOL EnsureActive(FieldSystem *fieldSystem, u32 mapHeader)
{
    u16 progress = PuzzleProgress(fieldSystem);
    BOOL testMode = gDwPuzzleTestMode != 0;

    if (sTableMap != mapHeader || sCachedTestMode != testMode || sCachedProgress != progress) {
        sTable = FindTable(mapHeader, progress);
        sTableMap = mapHeader;
        sCachedTestMode = testMode;
        sCachedProgress = progress;
        // Do NOT touch sTrackingValid / sLastX/Y/Z here: a fall warp
        // reloads the map, and the frame hook detects the warp by
        // comparing the post-warp position against the pre-warp tracked
        // position (the fall tile).
        if (sTable != NULL) {
            memset(&gDwPuzzleDebug, 0, sizeof(gDwPuzzleDebug));
            gDwPuzzleDebug.mapHeader = mapHeader;
            gDwPuzzleDebug.active = 1;
            gDwPuzzleDebug.resetGeneration = sResetGeneration;
            if (sFreshResetPending) {
                sFreshResetPending = FALSE;
                sFallCount = 0;
                ResetPuzzleToInitial();
            } else if (sTable != sPrevTable && !sFallPending && !sRespawnPending) {
                // A different puzzle table with no fall/catch in flight
                // (a direct warp to another puzzle map, or first
                // activation after load): the previous map's group state
                // must not leak into this table.
                ResetPuzzleToInitial();
            }
            sPrevTable = sTable;
        } else {
            gDwPuzzleDebug.active = 0;
        }
    } else if (sTable != NULL && sFreshResetPending) {
        sFreshResetPending = FALSE;
        sFallCount = 0;
        ResetPuzzleToInitial();
    }
    return sTable != NULL;
}

static void RefreshDebug(int x, int y, int z, int surface)
{
    gDwPuzzleDebug.playerX = (s16)x;
    gDwPuzzleDebug.playerY = (s16)y;
    gDwPuzzleDebug.playerZ = (s16)z;
    gDwPuzzleDebug.surface = (u8)surface;
    gDwPuzzleDebug.frameCount = sFrameCount;
    gDwPuzzleDebug.fallCount = sFallCount;
    gDwPuzzleDebug.lastEvent = sLastEvent;
    gDwPuzzleDebug.lastEventFrame = sLastEventFrame;
    gDwPuzzleDebug.lastEventGroup = sLastEventGroup;
    gDwPuzzleDebug.flashFrames = sFlashFrames;
    gDwPuzzleDebug.resetGeneration = sResetGeneration;
    gDwPuzzleDebug.slideActive = sSliding ? 1 : 0;
    gDwPuzzleDebug.slideDir = (s8)sSlideDir;
    gDwPuzzleDebug.slideSteps = sSlideSteps;
    gDwPuzzleDebug.checkpointIndex = sCheckpointIndex;
    gDwPuzzleDebug.groupBits = 0;
    gDwPuzzleDebug.groupDisplayBits = 0;
    gDwPuzzleDebug.sigilBits = 0;

    if (sTable == NULL) {
        gDwPuzzleDebug.checkpointX = 0;
        gDwPuzzleDebug.checkpointY = 0;
        gDwPuzzleDebug.checkpointZ = 0;
        gDwPuzzleDebug.currentTileState = DW_PUZZLE_TILE_DEFAULT;
        return;
    }

    for (int i = 0; i < sTable->groupCount; i++) {
        // groupBits is the LOGICAL state (target: base OR momentary
        // holds), not the walkability, which lags during fades.
        if (sGroupTarget[i]) {
            gDwPuzzleDebug.groupBits |= (1u << i);
        }
        if (sGroupDisplay[i]) {
            gDwPuzzleDebug.groupDisplayBits |= (1u << i);
        }
    }
    for (int i = 0; i < sTable->sigilCount; i++) {
        if (sSigilPressed[i]) {
            gDwPuzzleDebug.sigilBits |= (1u << i);
        }
    }
    if (sCheckpointIndex < (u32)sTable->checkpointCount) {
        gDwPuzzleDebug.checkpointX = sTable->checkpoints[sCheckpointIndex].x;
        gDwPuzzleDebug.checkpointY = sTable->checkpoints[sCheckpointIndex].y;
        gDwPuzzleDebug.checkpointZ = sTable->checkpoints[sCheckpointIndex].z;
    }
}

// Resolve a tile without side effects (used by QueryTile and by the
// step/frame hooks). Precedence: actor tiles (engine-b) > explicit
// table overrides > groups (later group wins). An actor tile is the
// most immediate physical reality (a stone sitting on a tile), so a
// RESTING stone's BLOCKED actor tile plugs a current tile even if that
// tile has an explicit SOLID override (rift-213), and a LANDED stone's
// SOLID actor tile shields a VOID tile (no fall from any path).
// fallScriptId is the step-fall script for the winning VOID entry, or 0
// for the table default (actor tiles carry no fallScriptId).
static DwPuzzleTileState ResolveTileEx(int x, int y, int z, int surface, u16 *fallScriptIdOut)
{
    DwPuzzleTileState state = DW_PUZZLE_TILE_DEFAULT;
    u16 fallScriptId = 0;

    if (sTable == NULL) {
        return state;
    }

    for (int i = 0; i < sTable->groupCount; i++) {
        const DwPuzzleGroup *group = &sTable->groups[i];

        for (int t = 0; t < group->tileCount; t++) {
            if (group->tiles[t].x == x && group->tiles[t].y == y && group->tiles[t].z == z
                && SurfaceMatches(group->tiles[t].surface, surface)) {
                state = sGroupOn[i] ? (DwPuzzleTileState)group->onState : (DwPuzzleTileState)group->offState;
                fallScriptId = group->fallScriptId;
                break;
            }
        }
    }

    for (int i = 0; i < sTable->tileCount; i++) {
        if (sTable->tiles[i].x == x && sTable->tiles[i].y == y && sTable->tiles[i].z == z
            && SurfaceMatches(sTable->tiles[i].surface, surface)) {
            state = (DwPuzzleTileState)sTable->tiles[i].state;
            fallScriptId = sTable->tiles[i].fallScriptId;
            break;
        }
    }

    for (int i = 0; i < DW_PUZZLE_MAX_ACTOR_BLOCKS; i++) {
        if (sActorTiles[i].present && sActorTiles[i].x == x && sActorTiles[i].y == y && sActorTiles[i].z == z
            && SurfaceMatches(sActorTiles[i].surface, surface)) {
            state = (DwPuzzleTileState)sActorTiles[i].state;
            fallScriptId = 0;
            break;
        }
    }

    if (fallScriptIdOut != NULL) {
        *fallScriptIdOut = fallScriptId;
    }
    return state;
}

static DwPuzzleTileState ResolveTile(int x, int y, int z, int surface)
{
    return ResolveTileEx(x, y, z, surface, NULL);
}

static const DwPuzzleSigil *FindSigil(int x, int y, int z, int surface)
{
    if (sTable == NULL) {
        return NULL;
    }
    for (int i = 0; i < sTable->sigilCount; i++) {
        if (sTable->sigils[i].x == x && sTable->sigils[i].y == y && sTable->sigils[i].z == z
            && SurfaceMatches(sTable->sigils[i].surface, surface)) {
            return &sTable->sigils[i];
        }
    }
    return NULL;
}

static int SigilIndex(const DwPuzzleSigil *sigil)
{
    return (int)(sigil - sTable->sigils);
}

static const DwPuzzleRune *FindRune(int x, int y, int z, int surface)
{
    if (sTable == NULL) {
        return NULL;
    }
    for (int i = 0; i < sTable->runeCount; i++) {
        if (sTable->runes[i].x == x && sTable->runes[i].y == y && sTable->runes[i].z == z
            && SurfaceMatches(sTable->runes[i].surface, surface)) {
            return &sTable->runes[i];
        }
    }
    return NULL;
}

static const DwPuzzleCurrent *FindCurrent(int x, int y, int z, int surface)
{
    if (sTable == NULL) {
        return NULL;
    }
    for (int i = 0; i < sTable->currentCount; i++) {
        if (sTable->currents[i].x == x && sTable->currents[i].y == y && sTable->currents[i].z == z
            && SurfaceMatches(sTable->currents[i].surface, surface)) {
            return &sTable->currents[i];
        }
    }
    return NULL;
}

static int FindCheckpoint(int x, int y, int z, int surface)
{
    if (sTable == NULL) {
        return -1;
    }
    for (int i = 0; i < sTable->checkpointCount; i++) {
        if (sTable->checkpoints[i].x == x && sTable->checkpoints[i].y == y && sTable->checkpoints[i].z == z
            && SurfaceMatches(sTable->checkpoints[i].surface, surface)) {
            return i;
        }
    }
    return -1;
}

// Release one occupant's momentary sigils it is no longer standing on.
// Standing on means the same tile AND the same surface: an in-place
// surface rune (same coordinates, new surface) lifts the occupant off
// the sigil, so the hold must release.
static void ReleaseMomentaryFor(int x, int y, int z, int surface, int occupant)
{
    u8 bit = (u8)(1u << occupant);

    if (sTable == NULL || occupant < 0 || occupant >= DW_PUZZLE_OCCUPANT_COUNT) {
        return;
    }
    for (int i = 0; i < sTable->sigilCount; i++) {
        const DwPuzzleSigil *sigil = &sTable->sigils[i];

        if (sigil->kind != DW_PUZZLE_SIGIL_MOMENTARY || (sSigilPressed[i] & bit) == 0) {
            continue;
        }
        if (sigil->x == x && sigil->y == y && sigil->z == z && SurfaceMatches(sigil->surface, surface)) {
            continue;
        }
        sSigilPressed[i] &= (u8)~bit;
        if (sigil->targetGroup < (u8)sTable->groupCount) {
            sMomentaryHolders[sigil->targetGroup] &= (u8)~bit;
            GroupRefreshTarget(sigil->targetGroup);
        }
    }
}

static void FireSigilAs(const DwPuzzleSigil *sigil, int occupant)
{
    int i = SigilIndex(sigil);
    u8 bit = (u8)(1u << occupant);

    switch (sigil->kind) {
    case DW_PUZZLE_SIGIL_TOGGLE:
        if (sigil->targetGroup < (u8)sTable->groupCount) {
            sGroupBase[sigil->targetGroup] = sGroupBase[sigil->targetGroup] ? 0 : 1;
            GroupRefreshTarget(sigil->targetGroup);
        }
        break;
    case DW_PUZZLE_SIGIL_SET:
        if (sigil->targetGroup < (u8)sTable->groupCount) {
            sGroupBase[sigil->targetGroup] = sigil->setValue ? 1 : 0;
            GroupRefreshTarget(sigil->targetGroup);
        }
        break;
    case DW_PUZZLE_SIGIL_MOMENTARY:
        if ((sSigilPressed[i] & bit) == 0) {
            sSigilPressed[i] |= bit;
            if (sigil->targetGroup < (u8)sTable->groupCount) {
                sMomentaryHolders[sigil->targetGroup] |= bit;
                GroupRefreshTarget(sigil->targetGroup);
            }
        }
        break;
    case DW_PUZZLE_SIGIL_RESET:
        RestoreSnapshot();
        break;
    }

    Sound_PlayEffect(SEQ_SE_PL_SYUWA);
    sFlashFrames = 8;
    PuzzleSetEvent(sigil->kind == DW_PUZZLE_SIGIL_RESET ? DW_PUZZLE_EVENT_RESET : DW_PUZZLE_EVENT_SIGIL,
        sigil->targetGroup);
}

// ---- public API --------------------------------------------------------

const DwPuzzleTable *DwPuzzle_GetTable(u32 mapHeader)
{
    // No progress gate here (no FieldSystem); see DwPuzzle_IsActive.
    for (u32 i = 0; i < NELEMS(sPuzzleTables); i++) {
        const DwPuzzleTable *table = sPuzzleTables[i];

        if (table != NULL && table->mapHeader == mapHeader) {
            if (table->testOnly) {
                if (gDwPuzzleTestMode) {
                    return table;
                }
                continue;
            }
            return table;
        }
    }
    return NULL;
}

void DwPuzzle_SetTestMode(BOOL enabled)
{
    gDwPuzzleTestMode = enabled;
    // Re-resolve on the next hook call.
    sTableMap = 0xFFFFFFFF;
    sTable = NULL;
}

BOOL DwPuzzle_IsTestMode(void)
{
    return gDwPuzzleTestMode;
}

BOOL DwPuzzle_IsActive(FieldSystem *fieldSystem, u32 mapHeader)
{
    return EnsureActive(fieldSystem, mapHeader);
}

DwPuzzleTileState DwPuzzle_QueryTile(FieldSystem *fieldSystem, int x, int y, int z, int surface)
{
    u32 mapHeader = 0;

    if (fieldSystem != NULL && fieldSystem->location != NULL) {
        mapHeader = (u32)fieldSystem->location->mapId;
    }
    if (!EnsureActive(fieldSystem, mapHeader)) {
        return DW_PUZZLE_TILE_DEFAULT;
    }
    return ResolveTile(x, y, z, surface);
}

BOOL DwPuzzle_HandleStep(FieldSystem *fieldSystem, int x, int y, int z, int surface, int facing, DwPuzzleStepResult *out)
{
    u32 mapHeader = 0;
    const DwPuzzleSigil *sigil;
    const DwPuzzleRune *rune;
    const DwPuzzleCurrent *current;
    int checkpoint;
    DwPuzzleTileState tileState;
    u16 fallScriptId = 0;

    (void)facing;
    if (out != NULL) {
        memset(out, 0, sizeof(*out));
    }
    if (fieldSystem != NULL && fieldSystem->location != NULL) {
        mapHeader = (u32)fieldSystem->location->mapId;
    }
    if (!EnsureActive(fieldSystem, mapHeader)) {
        return FALSE;
    }

    RefreshDebug(x, y, z, surface);

    // A fall is in progress: the fall script owns the player. Ignore steps
    // until the warp lands and the respawn clears sFallPending.
    if (sFallPending || sRespawnPending) {
        return FALSE;
    }

    ReleaseMomentaryFor(x, y, z, surface, DW_PUZZLE_OCCUPANT_PLAYER);

    // A slide that lands off-current ends here (sigils / runes /
    // checkpoints / falls on the landing tile still run below).
    if (sSliding && FindCurrent(x, y, z, surface) == NULL) {
        sSliding = FALSE;
        PuzzleSetEvent(DW_PUZZLE_EVENT_CURRENT_STOP, 0);
    }

    // Sigils fire before the fall check: a sigil on a VOID tile fires.
    sigil = FindSigil(x, y, z, surface);
    if (sigil != NULL) {
        FireSigilAs(sigil, DW_PUZZLE_OCCUPANT_PLAYER);
    }

    // Checkpoints snapshot after sigils, so a sigil on a checkpoint tile
    // is captured in the snapshot.
    checkpoint = FindCheckpoint(x, y, z, surface);
    if (checkpoint >= 0) {
        if ((u32)checkpoint != sCheckpointIndex) {
            sCheckpointIndex = (u32)checkpoint;
            Sound_PlayEffect(SEQ_SE_PL_SYUWA);
            PuzzleSetEvent(DW_PUZZLE_EVENT_CHECKPOINT, (u32)checkpoint);
        }
        TakeSnapshot();
        if (out != NULL) {
            out->checkpointReached = TRUE;
        }
    }

    // Runes: the slide ends, the glue runs the jump-point change.
    rune = FindRune(x, y, z, surface);
    if (rune != NULL) {
        if (sSliding) {
            sSliding = FALSE;
            PuzzleSetEvent(DW_PUZZLE_EVENT_CURRENT_STOP, 0);
        }
        Sound_PlayEffect(SEQ_SE_PL_SYUWA);
        PuzzleSetEvent(DW_PUZZLE_EVENT_RUNE, 0);
        if (out != NULL) {
            out->handled = TRUE;
            out->runeRequested = TRUE;
            out->rune.targetX = rune->targetX;
            out->rune.targetY = rune->targetY;
            out->rune.targetZ = rune->targetZ;
            out->rune.targetSurface = rune->targetSurface;
            out->rune.facing = rune->facing;
            out->rune.rot = rune->rot;
            out->rune.steps = rune->steps;
            out->rune.useCamera = rune->useCamera;
            out->rune.cameraX = rune->cameraX;
            out->rune.cameraY = rune->cameraY;
            out->rune.cameraZ = rune->cameraZ;
            out->rune.cameraSteps = rune->cameraSteps;
        }
        RefreshDebug(x, y, z, surface);
        return TRUE;
    }

    // Currents: start or continue a slide. The slide itself runs in the
    // frame hook; landing on a new current changes its direction.
    // rift-214: a tile can be both a group tile and a current. When the
    // group's tile state is BLOCKED it wins and no slide happens (a slide
    // stranded there stops); when it is open, the current applies. A VOID
    // current tile is a fall, not a slide: it falls through to the VOID
    // check below.
    current = FindCurrent(x, y, z, surface);
    if (current != NULL) {
        DwPuzzleTileState curState = ResolveTileEx(x, y, z, surface, &fallScriptId);
        if (curState == DW_PUZZLE_TILE_BLOCKED) {
            if (sSliding) {
                sSliding = FALSE;
                PuzzleSetEvent(DW_PUZZLE_EVENT_CURRENT_STOP, 0);
            }
            RefreshDebug(x, y, z, surface);
            return out != NULL && out->handled;
        }
        if (curState != DW_PUZZLE_TILE_VOID && !sSliding) {
            sSliding = TRUE;
            sSlideDir = current->dir;
            sSlideFrames = DW_PUZZLE_SLIDE_FRAMES_PER_TILE;
            sSlideSteps = 0;
            PuzzleSetEvent(DW_PUZZLE_EVENT_CURRENT_START, 0);
            Sound_PlayEffect(SEQ_SE_PL_SYUWA);
            if (out != NULL) {
                out->slideStarted = TRUE;
            }
        } else if (curState != DW_PUZZLE_TILE_VOID && sSlideDir != current->dir) {
            sSlideDir = current->dir;
        }
        if (curState == DW_PUZZLE_TILE_VOID) {
            // Fall through to the VOID check below: no slide, no return.
        } else {
            RefreshDebug(x, y, z, surface);
            gDwPuzzleDebug.slideTargetX = (s16)x;
            gDwPuzzleDebug.slideTargetY = (s16)y;
            gDwPuzzleDebug.slideTargetZ = (s16)z;
            return out != NULL && out->handled;
        }
    }

    // VOID: the step is a fall. The per-map glue starts the fall script.
    tileState = ResolveTileEx(x, y, z, surface, &fallScriptId);
    gDwPuzzleDebug.currentTileState = (u8)tileState;
    if (tileState == DW_PUZZLE_TILE_VOID) {
        sSliding = FALSE;
        sFallPending = TRUE;
        sFallRestored = FALSE;
        sFallX = x;
        sFallY = y;
        sFallZ = z;
        sFallCount++;
        PuzzleSetEvent(DW_PUZZLE_EVENT_FALL, 0);
        if (out != NULL) {
            out->handled = TRUE;
            out->fallRequested = TRUE;
            out->fallScriptId = fallScriptId != 0 ? fallScriptId : sTable->fallScriptId;
        }
        RefreshDebug(x, y, z, surface);
        return TRUE;
    }

    RefreshDebug(x, y, z, surface);
    return out != NULL && out->handled;
}

void DwPuzzle_HandleFrame(FieldSystem *fieldSystem, int x, int y, int z, int surface, int facing, DwPuzzleFrameResult *out)
{
    u32 mapHeader = 0;
    int dx = 0, dy = 0, dz = 0;
    DwPuzzleTileState tileState;

    if (out != NULL) {
        memset(out, 0, sizeof(*out));
    }
    sFrameCount++;
    if (fieldSystem != NULL && fieldSystem->location != NULL) {
        mapHeader = (u32)fieldSystem->location->mapId;
    }
    if (!EnsureActive(fieldSystem, mapHeader)) {
        sTrackingValid = FALSE;
        return;
    }

    if (sFlashFrames > 0) {
        sFlashFrames--;
    }

    // Group fades: the solid state catches up to the target when the
    // fade timer expires (honeycomb rule).
    for (int i = 0; i < sTable->groupCount; i++) {
        if (sGroupTimer[i] > 0) {
            sGroupTimer[i]--;
            if (sGroupTimer[i] == 0) {
                sGroupOn[i] = sGroupTarget[i];
            }
        }
    }

    RefreshDebug(x, y, z, surface);
    tileState = ResolveTile(x, y, z, surface);
    gDwPuzzleDebug.currentTileState = (u8)tileState;

    // Ghost-prop masks for the glue (only the engine's own groups).
    if (out != NULL) {
        for (int i = 0; i < sTable->groupCount; i++) {
            u8 ghost = sTable->groups[i].ghostPropGroup;

            if (ghost == DW_PUZZLE_GHOST_GROUP_NONE) {
                continue;
            }
            if (sGroupDisplay[i]) {
                out->ghostShowMask |= (1u << ghost);
            } else {
                out->ghostHideMask |= (1u << ghost);
            }
        }
    }

    ReleaseMomentaryFor(x, y, z, surface, DW_PUZZLE_OCCUPANT_PLAYER);

    // --- shadow catch: restore + respawn, no fall script --------------
    if (sRespawnPending) {
        if (!sRespawnRestored) {
            RestoreSnapshot();
            sRespawnRestored = TRUE;
            PuzzleSetEvent(DW_PUZZLE_EVENT_RESPAWN, sCheckpointIndex);
            RefreshDebug(x, y, z, surface);
        }
        if (sCheckpointIndex < (u32)sTable->checkpointCount) {
            const DwPuzzleCheckpoint *cp = &sTable->checkpoints[sCheckpointIndex];

            // Complete only on the checkpoint tile AND its surface AND
            // its facing: a warp that already lands at the checkpoint
            // coordinates on the right surface but the wrong facing
            // must still apply the checkpoint's facing (glue respawn).
            // A facing of -1 (or out of range, a table error) means keep.
            if (x == cp->x && y == cp->y && z == cp->z && SurfaceMatches(cp->surface, surface)
                && (cp->facing < 0 || cp->facing > 3 || facing == cp->facing)) {
                sRespawnPending = FALSE;
                sRespawnRestored = FALSE;
            } else if (out != NULL) {
                out->respawnRequested = TRUE;
                out->respawnX = cp->x;
                out->respawnY = cp->y;
                out->respawnZ = cp->z;
                out->respawnFacing = cp->facing;
                out->respawnSurface = cp->surface;
            }
        }
        sLastX = x;
        sLastY = y;
        sLastZ = z;
        sLastSurface = surface;
        sTrackingValid = TRUE;
        sLastTileState = (u8)tileState;
        RefreshDebug(x, y, z, surface);
        return;
    }

    // --- fall warp landed? -------------------------------------------
    // sFallPending is set by the step/frame hook before the fall script
    // runs. The fall script locks input, so the FIRST position change
    // after that is the script's warp -- even when it is only one tile
    // (HoneyFall warps the hive's (39,22) VOID fall to the adjacent
    // (40,22), a 1-tile move). Only then restore the snapshot and
    // respawn at the checkpoint. The warp is detected against the FALL
    // TILE, not the tracked position: a warp reloads overlay 9 and
    // zeroes the test-mode gate, deactivating the engine and
    // invalidating the tracking before the frame hook sees the warp;
    // the fall tile persists in main RAM across the reload.
    if (sFallPending) {
        BOOL warped = (x != sFallX || y != sFallY || z != sFallZ);
        if (warped && !sFallRestored) {
            RestoreSnapshot();
            sFallRestored = TRUE;
            PuzzleSetEvent(DW_PUZZLE_EVENT_RESPAWN, sCheckpointIndex);
            RefreshDebug(x, y, z, surface);
        }
        // Respawn stays requested until the player is actually at the
        // checkpoint: the glue may defer the teleport a frame (player
        // busy), so this must not depend on the warp discontinuity,
        // which is only true on the first post-warp frame.
        if (sFallRestored && sCheckpointIndex < (u32)sTable->checkpointCount) {
            const DwPuzzleCheckpoint *cp = &sTable->checkpoints[sCheckpointIndex];

            // Complete only on the checkpoint tile AND its surface AND
            // its facing (see the shadow-catch block above).
            if (x == cp->x && y == cp->y && z == cp->z && SurfaceMatches(cp->surface, surface)
                && (cp->facing < 0 || cp->facing > 3 || facing == cp->facing)) {
                sFallPending = FALSE;
                sFallRestored = FALSE;
            } else if (out != NULL) {
                out->respawnRequested = TRUE;
                out->respawnX = cp->x;
                out->respawnY = cp->y;
                out->respawnZ = cp->z;
                out->respawnFacing = cp->facing;
                out->respawnSurface = cp->surface;
            }
        }
        sLastX = x;
        sLastY = y;
        sLastZ = z;
        sLastSurface = surface;
        sTrackingValid = TRUE;
        sLastTileState = (u8)tileState;
        RefreshDebug(x, y, z, surface);
        return;
    }

    // --- ground went away under a standing player ----------------------
    // Only when the player did NOT step: the step hook owns steps onto
    // VOID. A changed tile state under a stationary player means a group
    // faded out beneath them (the honeycomb case). Stationary means the
    // same tile AND the same surface: a rune landing changes the surface
    // at unchanged coordinates, and a landing must fire nothing
    // (landing rule). Raise fallVar so the rift's init frame table
    // starts the fall script from the idle field.
    if (sTrackingValid && x == sLastX && y == sLastY && z == sLastZ && surface == sLastSurface
        && tileState == DW_PUZZLE_TILE_VOID && sLastTileState != DW_PUZZLE_TILE_VOID
        && fieldSystem != NULL && fieldSystem->saveData != NULL
        && sTable->fallVar != 0 && sTable->fallScriptId != 0) {
        VarsFlags *varsFlags = SaveData_GetVarsFlags(fieldSystem->saveData);

        *VarsFlags_GetVarAddress(varsFlags, sTable->fallVar) = 1;
        sFallPending = TRUE;
        sFallRestored = FALSE;
        sFallX = x;
        sFallY = y;
        sFallZ = z;
        sFallCount++;
        PuzzleSetEvent(DW_PUZZLE_EVENT_FALL, 0);
        if (out != NULL) {
            out->frameFallRequested = TRUE;
        }
        RefreshDebug(x, y, z, surface);
    }

    // --- slide -----------------------------------------------------------
    // rift-214: a group that turns a current tile BLOCKED under a sliding
    // player stops the slide here (the slide never leaves a BLOCKED tile).
    if (sSliding && !sFallPending && !sRespawnPending
        && ResolveTile(x, y, z, surface) == DW_PUZZLE_TILE_BLOCKED) {
        sSliding = FALSE;
        PuzzleSetEvent(DW_PUZZLE_EVENT_CURRENT_STOP, 0);
    }
    if (sSliding && !sFallPending && !sRespawnPending && out != NULL) {
        if (sSlideFrames > 0) {
            sSlideFrames--;
        }
        if (sSlideFrames <= 0) {
            DwPuzzle_DirDelta(surface, sSlideDir, &dx, &dy, &dz);

            sSlideFrames = DW_PUZZLE_SLIDE_FRAMES_PER_TILE;
            out->slideActive = TRUE;

            int nx = x + dx, ny = y + dy, nz = z + dz;
            DwPuzzleTileState nextState = ResolveTile(nx, ny, nz, surface);

            if (nextState == DW_PUZZLE_TILE_BLOCKED || sSlideSteps >= DW_PUZZLE_MAX_SLIDE_STEPS) {
                // Blocked, or the safety cap on a closed current cycle:
                // the slide stops where it is and input unlocks. The
                // step hook already ran on this tile; nothing else to do.
                sSliding = FALSE;
                PuzzleSetEvent(DW_PUZZLE_EVENT_CURRENT_STOP, 0);
                out->slideActive = FALSE;
            } else {
                sSlideSteps++;
                out->slideStep = TRUE;
                out->slideX = (s16)nx;
                out->slideY = (s16)ny;
                out->slideZ = (s16)nz;
                gDwPuzzleDebug.slideTargetX = (s16)nx;
                gDwPuzzleDebug.slideTargetY = (s16)ny;
                gDwPuzzleDebug.slideTargetZ = (s16)nz;
            }
        } else {
            out->slideActive = TRUE;
        }
    }

    sLastX = x;
    sLastY = y;
    sLastZ = z;
    sLastSurface = surface;
    sTrackingValid = TRUE;
    sLastTileState = (u8)tileState;
    RefreshDebug(x, y, z, surface);
}

// A fall the step hook never sees (a scripted fall: DW Eterna Forest's
// honeycomb, the Lost Tower false-seam drop). The caller owns starting
// the fall script; the engine records fall-pending in its own RAM at the
// moment of the call. That record must survive the fall script clearing
// its fallVar (HoneyFall clears VAR_MAP_LOCAL_2 first thing), which is
// why it lives here and not in any var. On the fall script's warp, the
// frame hook restores the last checkpoint snapshot and respawns, exactly
// as for a VOID-tile fall. No-op without an active table, and idempotent
// while a fall is already in flight (the honeycomb frame hook calls it
// every frame the player stands on the gone honeycomb).
void DwPuzzle_NotifyFall(FieldSystem *fieldSystem)
{
    u32 mapHeader = 0;

    if (fieldSystem != NULL && fieldSystem->location != NULL) {
        mapHeader = (u32)fieldSystem->location->mapId;
    }
    if (!EnsureActive(fieldSystem, mapHeader)) {
        return;
    }
    if (sFallPending || sRespawnPending) {
        return;
    }
    sFallPending = TRUE;
    sFallRestored = FALSE;
    if (fieldSystem != NULL && fieldSystem->playerAvatar != NULL) {
        MapObject *playerMapObj = Player_MapObject(fieldSystem->playerAvatar);

        sFallX = MapObject_GetX(playerMapObj);
        sFallY = MapObject_GetY(playerMapObj) / 2;
        sFallZ = MapObject_GetZ(playerMapObj);
    }
    sFallCount++;
    PuzzleSetEvent(DW_PUZZLE_EVENT_FALL, 0);
    // No RefreshDebug here: the next frame hook refreshes with the real
    // player position.
}

void DwPuzzle_OnMapEnter(FieldSystem *fieldSystem, u32 mapHeader)
{
    (void)fieldSystem;
    // A fall warp reloads the same map: keep the state, the fall flag
    // tells the frame hook a respawn is owed. A same-map warp (fold,
    // fall) is not a fresh entry: the puzzle state persists across it
    // (sTableMap still holds the map we came from; the state itself is
    // in main-binary RAM, so it survives the overlay reload). Only a
    // load of a DIFFERENT map with no fall pending is a fresh entry,
    // and only that resets the puzzle to its initial state.
    // The table itself resolves lazily in EnsureActive, so there is
    // nothing to do when the map has no table.
    if (!sFallPending && !sRespawnPending && sTableMap != mapHeader) {
        sFreshResetPending = TRUE;
    }
    sTableMap = 0xFFFFFFFF;
    sTable = NULL;
}

void DwPuzzle_OnMapExit(FieldSystem *fieldSystem, u32 mapHeader)
{
    (void)fieldSystem;
    (void)mapHeader;
    // A real departure: the next load of this map is a fresh entry, so
    // invalidate the table cache now; OnMapEnter will reset then.
    // Same-map warps never call this (the glue only calls it when the
    // destination differs from the freed map).
    sTableMap = 0xFFFFFFFF;
    sTable = NULL;
}

void DwPuzzle_CancelSlide(FieldSystem *fieldSystem)
{
    u32 mapHeader = 0;

    if (fieldSystem != NULL && fieldSystem->location != NULL) {
        mapHeader = (u32)fieldSystem->location->mapId;
    }
    if (!EnsureActive(fieldSystem, mapHeader)) {
        return;
    }
    if (sSliding) {
        sSliding = FALSE;
        PuzzleSetEvent(DW_PUZZLE_EVENT_CURRENT_STOP, 0);
    }
}

void DwPuzzle_SetActorTile(int index, int x, int y, int z, int surface, DwPuzzleTileState state, BOOL present)
{
    if (index < 0 || index >= DW_PUZZLE_MAX_ACTOR_BLOCKS) {
        return;
    }
    sActorTiles[index].x = (s16)x;
    sActorTiles[index].y = (s16)y;
    sActorTiles[index].z = (s16)z;
    sActorTiles[index].surface = (u8)surface;
    sActorTiles[index].state = (u8)state;
    sActorTiles[index].present = present ? 1 : 0;
}

void DwPuzzle_ClearActorTiles(void)
{
    memset(sActorTiles, 0, sizeof(sActorTiles));
}

BOOL DwPuzzle_PressSigil(FieldSystem *fieldSystem, int x, int y, int z, int surface, int occupant)
{
    const DwPuzzleSigil *sigil;
    u32 mapHeader = 0;

    if (occupant < 0 || occupant >= DW_PUZZLE_OCCUPANT_COUNT) {
        return FALSE;
    }
    if (fieldSystem != NULL && fieldSystem->location != NULL) {
        mapHeader = (u32)fieldSystem->location->mapId;
    }
    if (!EnsureActive(fieldSystem, mapHeader)) {
        return FALSE;
    }
    ReleaseMomentaryFor(x, y, z, surface, occupant);
    sigil = FindSigil(x, y, z, surface);
    if (sigil == NULL) {
        return FALSE;
    }
    FireSigilAs(sigil, occupant);
    return TRUE;
}

void DwPuzzle_ReleaseSigils(FieldSystem *fieldSystem, int occupant)
{
    u32 mapHeader = 0;
    u8 bit;

    if (occupant < 0 || occupant >= DW_PUZZLE_OCCUPANT_COUNT) {
        return;
    }
    if (fieldSystem != NULL && fieldSystem->location != NULL) {
        mapHeader = (u32)fieldSystem->location->mapId;
    }
    if (!EnsureActive(fieldSystem, mapHeader)) {
        return;
    }
    bit = (u8)(1u << occupant);
    for (int i = 0; i < sTable->sigilCount; i++) {
        if ((sSigilPressed[i] & bit) == 0) {
            continue;
        }
        sSigilPressed[i] &= (u8)~bit;
        if (sTable->sigils[i].kind == DW_PUZZLE_SIGIL_MOMENTARY
            && sTable->sigils[i].targetGroup < (u8)sTable->groupCount) {
            sMomentaryHolders[sTable->sigils[i].targetGroup] &= (u8)~bit;
            GroupRefreshTarget(sTable->sigils[i].targetGroup);
        }
    }
}

// dwp:rift-lt: commit a checkpoint by index, mirroring HandleStep's
// checkpoint block (sound + CHECKPOINT event + snapshot). Scripted
// landings never run Field_ProcessStep, so the landing's checkpoint
// would otherwise never commit (e.g. the Lost Tower Skarmory carry
// landing at CP3). The caller also calls DwActors_OnCheckpoint for
// the actor snapshot.
void DwPuzzle_CommitCheckpointByIndex(FieldSystem *fieldSystem, int checkpointIndex)
{
    u32 mapHeader = 0;

    if (fieldSystem != NULL && fieldSystem->location != NULL) {
        mapHeader = (u32)fieldSystem->location->mapId;
    }
    if (!EnsureActive(fieldSystem, mapHeader)) {
        return;
    }
    if (checkpointIndex < 0 || (u32)checkpointIndex >= (u32)sTable->checkpointCount) {
        return;
    }
    if ((u32)checkpointIndex != sCheckpointIndex) {
        sCheckpointIndex = (u32)checkpointIndex;
        Sound_PlayEffect(SEQ_SE_PL_SYUWA);
        PuzzleSetEvent(DW_PUZZLE_EVENT_CHECKPOINT, (u32)checkpointIndex);
    }
    TakeSnapshot();
}

void DwPuzzle_RequestCheckpointRespawn(FieldSystem *fieldSystem)
{
    u32 mapHeader = 0;

    if (fieldSystem != NULL && fieldSystem->location != NULL) {
        mapHeader = (u32)fieldSystem->location->mapId;
    }
    if (!EnsureActive(fieldSystem, mapHeader)) {
        return;
    }
    if (sFallPending) {
        return; // a fall respawn is already owed; it wins
    }
    sRespawnPending = TRUE;
    sRespawnRestored = FALSE;
    sSliding = FALSE;
    sFallCount++;
    PuzzleSetEvent(DW_PUZZLE_EVENT_CAUGHT, 0);
}

void DwPuzzle_DirDelta(int surface, int dir, int *dx, int *dy, int *dz)
{
    // Indexed by FACE_* (UP 0, DOWN 1, LEFT 2, RIGHT 3), the same tables
    // the stock DW movement code uses.
    static const s8 sDeltaGround[4][3] = {
        { 0, 0, -1 }, { 0, 0, 1 }, { -1, 0, 0 }, { 1, 0, 0 },
    };
    static const s8 sDeltaWestWall[4][3] = {
        { 0, 1, 0 }, { 0, -1, 0 }, { 0, 0, 1 }, { 0, 0, -1 },
    };
    static const s8 sDeltaEastWall[4][3] = {
        { 0, 1, 0 }, { 0, -1, 0 }, { 0, 0, -1 }, { 0, 0, 1 },
    };
    static const s8 sDeltaCeiling[4][3] = {
        { 0, 0, 1 }, { 0, 0, -1 }, { -1, 0, 0 }, { 1, 0, 0 },
    };
    const s8 (*table)[3] = sDeltaGround;

    switch (surface) {
    case DW_PUZZLE_SURFACE_WEST_WALL:
        table = sDeltaWestWall;
        break;
    case DW_PUZZLE_SURFACE_EAST_WALL:
        table = sDeltaEastWall;
        break;
    case DW_PUZZLE_SURFACE_CEILING:
        table = sDeltaCeiling;
        break;
    default:
        table = sDeltaGround; // GROUND and floating FLOOR both walk flat
        break;
    }

    if (dir < 0 || dir > 3) {
        dir = 0;
    }
    if (dx != NULL) {
        *dx = table[dir][0];
    }
    if (dy != NULL) {
        *dy = table[dir][1];
    }
    if (dz != NULL) {
        *dz = table[dir][2];
    }
}
