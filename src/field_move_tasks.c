#include "field_move_tasks.h"

#include <nitro.h>
#include <string.h>

#include "constants/field/dynamic_map_features.h"
#include "constants/field/map_load.h"
#include "constants/overworld_weather.h"
#include "constants/species.h"
#include "generated/badges.h"
#include "generated/items.h"
#include "generated/journal_location_events.h"
#include "generated/moves.h"
#include "generated/object_events_gfx.h"

#include "struct_decls/struct_020216E0_decl.h"
#include "struct_decls/struct_02061AB4_decl.h"
#include "struct_defs/pokemon.h"
#include "struct_defs/struct_020708E0.h"
#include "struct_defs/struct_020711C8.h"

#include "applications/town_map/main.h"
#include "field/field_system.h"
#include "overlay005/ov5_021DFB54.h"
#include "overlay005/ov5_021EB1A0.h"
#include "overlay005/ov5_021ECA70.h"
#include "overlay005/ov5_021F101C.h"
#include "overlay006/ov6_02247100.h"

#include "bag.h"
#include "field_overworld_state.h"
#include "field_task.h"
#include "heap.h"
#include "inlines.h"
#include "journal.h"
#include "map_header.h"
#include "map_object.h"
#include "map_tile_behavior.h"
#include "party.h"
#include "persisted_map_features_init.h"
#include "player_avatar.h"
#include "save_player.h"
#include "script_manager.h"
#include "start_menu.h"
#include "system_flags.h"
#include "terrain_collision_manager.h"
#include "trainer_info.h"
#include "unk_0203C954.h"
#include "unk_0203D1B8.h"
#include "unk_0205F180.h"
#include "unk_02020AEC.h"
#include "unk_020711C8.h"
#include "vars_flags.h"
#include "vram_transfer.h"

#define FIELD_MOVE_FLAG(move) (1 << (move))

typedef struct {
    FieldMoveTaskContext task;
    FieldMoveErrContext error;
} FieldMoveTaskOrError;

typedef struct {
    u32 magicNumber;
    MapObject *mapObj;
    FieldMovePokemon fieldMoveMon;
} FieldMoveTaskData;

static void FieldMoves_CanUseSurfDistortionWorld(FieldSystem *fieldSystem, FieldMoveContext *param1);
static enum FieldMoveError FieldMoves_CheckResonatorObstacle(const FieldMoveContext *fieldMoveContext);

static enum FieldMoveError FieldMoves_CheckFly(const FieldMoveContext *fieldMoveContext);
static void FieldMoves_SetFlyTask(FieldMovePokemon *fieldMoveMon, const FieldMoveContext *fieldMoveContext);

static enum FieldMoveError FieldMoves_CheckTeleport(const FieldMoveContext *fieldMoveContext);
static void FieldMoves_SetTeleportTask(FieldMovePokemon *fieldMoveMon, const FieldMoveContext *fieldMoveContext);
static BOOL FieldMoves_TeleportTask(FieldTask *taskMan);

static void FieldMoves_SetSurfTask(FieldMovePokemon *fieldMoveMon, const FieldMoveContext *fieldMoveContext);
static BOOL FieldMoves_SurfTask(FieldTask *taskMan);

static void FieldMoves_SetWaterfallTask(FieldMovePokemon *fieldMoveMon, const FieldMoveContext *fieldMoveContext);
static BOOL FieldMoves_WaterfallTask(FieldTask *taskMan);

static void FieldMoves_SetRockClimbTask(FieldMovePokemon *fieldMoveMon, const FieldMoveContext *fieldMoveContext);
static BOOL FieldMoves_RockClimbTask(FieldTask *taskMan);

static enum FieldMoveError FieldMoves_CheckFlash(const FieldMoveContext *fieldMoveContext);
static void FieldMoves_SetFlashTask(FieldMovePokemon *fieldMoveMon, const FieldMoveContext *fieldMoveContext);
static BOOL FieldMoves_FlashTask(FieldTask *taskMan);

static void FieldMoves_SetDefogTask(FieldMovePokemon *fieldMoveMon, const FieldMoveContext *fieldMoveContext);
static BOOL FieldMoves_DefogTask(FieldTask *taskMan);

static void FieldMoves_SetRockSmashTask(FieldMovePokemon *fieldMoveMon, const FieldMoveContext *fieldMoveContext);
static BOOL FieldMoves_RockSmashTask(FieldTask *taskMan);

static void FieldMoves_SetStrengthTask(FieldMovePokemon *fieldMoveMon, const FieldMoveContext *fieldMoveContext);
static BOOL FieldMoves_StrengthTask(FieldTask *taskMan);

static enum FieldMoveError FieldMoves_CheckDig(const FieldMoveContext *fieldMoveContext);
static void FieldMoves_SetDigTask(FieldMovePokemon *fieldMoveMon, const FieldMoveContext *fieldMoveContext);
static BOOL FieldMoves_DigTask(FieldTask *taskMan);

static enum FieldMoveError FieldMoves_CheckSweetScent(const FieldMoveContext *fieldMoveContext);
static void FieldMoves_SetSweetScentTask(FieldMovePokemon *fieldMoveMon, const FieldMoveContext *fieldMoveContext);

static enum FieldMoveError FieldMoves_CheckChatter(const FieldMoveContext *fieldMoveContext);
static void FieldMoves_SetChatterTask(FieldMovePokemon *fieldMoveMon, const FieldMoveContext *fieldMoveContext);
static BOOL FieldMoves_ChatterTask(FieldTask *taskMan);

static void FieldMoves_SetCutTask(FieldMovePokemon *fieldMoveMon, const FieldMoveContext *fieldMoveContext);
static BOOL FieldMoves_CutTask(FieldTask *taskMan);

static const FieldMoveTaskOrError fieldMoveTaskOrError[] = {
    { FieldMoves_SetCutTask, FieldMoves_CheckResonatorObstacle },
    { FieldMoves_SetFlyTask, FieldMoves_CheckFly },
    { FieldMoves_SetSurfTask, FieldMoves_CheckResonatorObstacle },
    { FieldMoves_SetStrengthTask, FieldMoves_CheckResonatorObstacle },
    { FieldMoves_SetDefogTask, FieldMoves_CheckResonatorObstacle },
    { FieldMoves_SetRockSmashTask, FieldMoves_CheckResonatorObstacle },
    { FieldMoves_SetWaterfallTask, FieldMoves_CheckResonatorObstacle },
    { FieldMoves_SetRockClimbTask, FieldMoves_CheckResonatorObstacle },
    { FieldMoves_SetFlashTask, FieldMoves_CheckFlash },
    { FieldMoves_SetTeleportTask, FieldMoves_CheckTeleport },
    { FieldMoves_SetDigTask, FieldMoves_CheckDig },
    { FieldMoves_SetSweetScentTask, FieldMoves_CheckSweetScent },
    { FieldMoves_SetChatterTask, FieldMoves_CheckChatter },
};

static inline BOOL FieldMoves_IsMoveUsable(const FieldMoveContext *fieldMoveContext, enum FieldMoveList fieldMove)
{
    if ((fieldMoveContext->usableMoves & FIELD_MOVE_FLAG(fieldMove)) != 0) {
        return TRUE;
    }

    return FALSE;
}

static inline BOOL PlayerHasRequiredBadge(const FieldMoveContext *fieldMoveContext, enum Badge badge)
{
    return TrainerInfo_HasBadge(SaveData_GetTrainerInfo(fieldMoveContext->fieldSystem->saveData), badge);
}

static enum FieldMoveError FieldMoves_CheckProgression(const FieldMoveContext *fieldMoveContext, enum Badge badge, u16 totemDefeatedFlag)
{
    if (PlayerHasRequiredBadge(fieldMoveContext, badge) == FALSE) {
        return FIELD_MOVE_ERROR_BADGE;
    }

    if (VarsFlags_CheckFlag(SaveData_GetVarsFlags(fieldMoveContext->fieldSystem->saveData), totemDefeatedFlag) == FALSE) {
        return FIELD_MOVE_ERROR_TOTEM;
    }

    return FIELD_MOVE_ERROR_NONE;
}

// Arc 2 Resonator (S8 stages 1-2, D10/D11): every field power is the Resonator channelling a calmed totem. It needs
// ITEM_RESONATOR in the bag, the totem's FLAG_TOTEM_*_DEFEATED and the region's Gym badge (the Leader vouching).
// The totems and badges follow docs/story/bible.md.
typedef struct ResonatorPower {
    u16 move;
    u16 species;
    u16 totemDefeatedFlag;
    u8 fieldMove;
    u8 badge;
} ResonatorPower;

static const ResonatorPower sResonatorPowers[] = {
    { MOVE_ROCK_SMASH, SPECIES_HITMONLEE, FLAG_TOTEM_HITMONLEE_DEFEATED, FIELD_MOVE_ROCK_SMASH, BADGE_ID_COAL },
    { MOVE_CUT, SPECIES_VESPIQUEN, FLAG_TOTEM_VESPIQUEN_DEFEATED, FIELD_MOVE_CUT, BADGE_ID_FOREST },
    { MOVE_FLY, SPECIES_SKARMORY, FLAG_TOTEM_SKARMORY_DEFEATED, FIELD_MOVE_FLY, BADGE_ID_COBBLE },
    { MOVE_SURF, SPECIES_LAPRAS, FLAG_TOTEM_LAPRAS_DEFEATED, FIELD_MOVE_SURF, BADGE_ID_FEN },
    { MOVE_DEFOG, SPECIES_SPIRITOMB, FLAG_TOTEM_SPIRITOMB_DEFEATED, FIELD_MOVE_DEFOG, BADGE_ID_RELIC },
    { MOVE_STRENGTH, SPECIES_AGGRON, FLAG_TOTEM_AGGRON_DEFEATED, FIELD_MOVE_STRENGTH, BADGE_ID_MINE },
    { MOVE_ROCK_CLIMB, SPECIES_MAMOSWINE, FLAG_TOTEM_MAMOSWINE_DEFEATED, FIELD_MOVE_ROCK_CLIMB, BADGE_ID_ICICLE },
    { MOVE_WATERFALL, SPECIES_KINGDRA, FLAG_TOTEM_KINGDRA_DEFEATED, FIELD_MOVE_WATERFALL, BADGE_ID_BEACON },
};

// The ghost totem the Resonator shows in the cut-in. The cut-in and the ride tasks keep a pointer to it, so it can't
// live on the heap. Fixed personality and OT id (not shiny) so building it never touches the RNG.
static Pokemon sResonatorGhost;

static const ResonatorPower *FieldMoves_FindResonatorPowerByMove(u16 move)
{
    for (int i = 0; i < NELEMS(sResonatorPowers); i++) {
        if (sResonatorPowers[i].move == move) {
            return &sResonatorPowers[i];
        }
    }

    return NULL;
}

static const ResonatorPower *FieldMoves_FindResonatorPowerByFieldMove(u32 fieldMove)
{
    for (int i = 0; i < NELEMS(sResonatorPowers); i++) {
        if (sResonatorPowers[i].fieldMove == fieldMove) {
            return &sResonatorPowers[i];
        }
    }

    return NULL;
}

// The Resonator is a key item. Reading the pocket directly needs no heap, so this also works from the party menu,
// where the field heaps are gone.
static BOOL FieldMoves_HasResonator(FieldSystem *fieldSystem)
{
    Bag *bag = SaveData_GetBag(fieldSystem->saveData);
    return Pocket_GetItemQuantity(bag->keyItems, KEY_ITEM_POCKET_SIZE, ITEM_RESONATOR, HEAP_ID_SYSTEM) > 0;
}

BOOL FieldMoves_IsHMUnlocked(FieldSystem *fieldSystem, u16 move)
{
    const ResonatorPower *power = FieldMoves_FindResonatorPowerByMove(move);

    if (power == NULL) {
        return FALSE;
    }

    return FieldMoves_HasResonator(fieldSystem)
        && TrainerInfo_HasBadge(SaveData_GetTrainerInfo(fieldSystem->saveData), power->badge)
        && VarsFlags_CheckFlag(SaveData_GetVarsFlags(fieldSystem->saveData), power->totemDefeatedFlag);
}

// Field obstacles are Resonator-only (D11): the party menu no longer lists these moves.
BOOL FieldMoves_IsResonatorObstacleMove(u16 move)
{
    switch (move) {
    case MOVE_CUT:
    case MOVE_SURF:
    case MOVE_STRENGTH:
    case MOVE_DEFOG:
    case MOVE_ROCK_SMASH:
    case MOVE_WATERFALL:
    case MOVE_ROCK_CLIMB:
        return TRUE;
    }

    return FALSE;
}

Pokemon *FieldMoves_GetHMPerformer(FieldSystem *fieldSystem, int partySlot)
{
    const ResonatorPower *power = NULL;

    if (partySlot >= RESONATOR_SLOT_BASE) {
        power = FieldMoves_FindResonatorPowerByFieldMove(partySlot - RESONATOR_SLOT_BASE);
    }

    if (power == NULL) {
        return Party_GetPokemonBySlotIndex(SaveData_GetParty(fieldSystem->saveData), partySlot);
    }

    Pokemon_InitWith(&sResonatorGhost, power->species, 50, 15, TRUE, 0, OTID_SET, 0xFFFF);
    return &sResonatorGhost;
}

// Fly is Skarmory's power through the Resonator: whichever Pokemon's menu it was picked from, Skarmory's ghost flies.
Pokemon *FieldMoves_GetFlyPerformer(FieldSystem *fieldSystem, int partySlot)
{
    return FieldMoves_GetHMPerformer(fieldSystem, RESONATOR_SLOT(FIELD_MOVE_FLY));
}

BOOL FieldMoves_IsResonatorGhost(const Pokemon *mon)
{
    return mon == &sResonatorGhost;
}

// Ghost palette for the Resonator cut-in: each colour keeps its brightness but is washed into a pale violet, with
// the darkest shades lifted to indigo so the outline still reads. Colour 0 is transparent and stays as it is.
void FieldMoves_ApplyResonatorGhostPalette(const Pokemon *mon, u16 *palette, int numColors)
{
    if (FieldMoves_IsResonatorGhost(mon) == FALSE) {
        return;
    }

    for (int i = 1; i < numColors; i++) {
        u32 r = palette[i] & 0x1F;
        u32 g = (palette[i] >> 5) & 0x1F;
        u32 b = (palette[i] >> 10) & 0x1F;
        u32 luma = (r * 77 + g * 151 + b * 28) >> 8;

        r = 8 + (luma * 20) / 31;
        g = 6 + (luma * 20) / 31;
        b = 15 + (luma * 16) / 31;

        palette[i] = (palette[i] & 0x8000) | (r > 31 ? 31 : r) | ((g > 31 ? 31 : g) << 5) | ((b > 31 ? 31 : b) << 10);
    }
}

// Arc 2 Resonator echoes (S8 Echo stage, workstream echo; scripts in ravaged_path, valley_windworks_building and
// route_214). From the second calmed totem on, the Resonator replays a few seconds of what happened at a torture site.
// The replay is a plain scripted cutscene: its actors are ordinary object events with local IDs ECHO_LOCALID_FIRST to
// ECHO_LOCALID_LAST, and the script sets their opacity in VAR_MAP_LOCAL_5 (0 = off, 1-31). This hook, run after
// every map object draws (MapObjectTask_Draw), turns those actors into ghosts the way the Resonator cut-in shows a
// totem: the sprite's palette washed pale violet (FieldMoves_ApplyResonatorGhostPalette's wash, precomputed per
// sprite by tools/arc2_echo/echo_palettes.py) and the billboard drawn translucent with no shadow (the Lost Tower ghost
// acts' material-callback approach, src/overlay009/ov9_02249960.c). At opacity 0 the actors are hidden.
// The washed palettes sit in their own texture-palette VRAM block while an echo plays: allocated on the first ghost
// draw, freed on the first draw after the opacity is back to 0. Echo scripts set it to 0 and wait a frame before they
// release the player, so the block never outlives the field.
#define ECHO_LOCALID_FIRST 0xC0
#define ECHO_LOCALID_LAST  0xC7
#define ECHO_OPACITY_VAR   VAR_MAP_LOCAL_5
#define ECHO_OPACITY_MAX   31
#define ECHO_POLYGON_ID    0x31 // + the palette index: overlapping ghosts of different sprites still blend

typedef struct EchoGhostPalette {
    u16 graphicsID;
    u16 singleFrame; // drawn by the single-frame renderers (ov5_021ECA70.c): billboard via ov5_021ECB80
    u16 colors[16];
} EchoGhostPalette;

static const EchoGhostPalette sEchoGhostPalettes[] = {
    { OBJ_EVENT_GFX_ECLIPSE_GRUNT_M, FALSE,
        { 0x7C1F, 0x40E9, 0x452B, 0x4D6D, 0x59F1, 0x4D6D, 0x5E12, 0x72F9,
            0x518E, 0x6654, 0x72F9, 0x494C, 0x59F1, 0x7B3B, 0x6EB7, 0x59F1 } },
    { OBJ_EVENT_GFX_ECLIPSE_GRUNT_F, FALSE,
        { 0x7C1F, 0x40E9, 0x452B, 0x4D6D, 0x59F1, 0x4D6D, 0x5E12, 0x72F9,
            0x518E, 0x6654, 0x72F9, 0x494C, 0x59F1, 0x7B3B, 0x6EB7, 0x59F1 } },
    { OBJ_EVENT_GFX_ECLIPSE_CRATE, TRUE,
        { 0x7C1F, 0x40E9, 0x494C, 0x55AF, 0x5E12, 0x6A96, 0x494C, 0x5E12,
            0x494C, 0x5E12, 0x72D8, 0x3CC8, 0x6EB7, 0x3CC8, 0x3CC8, 0x3CC8 } },
    { OBJ_EVENT_GFX_SHARD_FRAME, TRUE,
        { 0x7C1F, 0x3CC8, 0x492B, 0x55AF, 0x6254, 0x72D8, 0x492B, 0x518E,
            0x492B, 0x59F1, 0x6A96, 0x771A, 0x4D6D, 0x3CC8, 0x3CC8, 0x3CC8 } },
    { OBJ_EVENT_GFX_RIFT_ARC2, TRUE,
        { 0x7C1F, 0x3CC8, 0x40E9, 0x450A, 0x4D6D, 0x59F1, 0x6A96, 0x7B3B,
            0x5E12, 0x51AF, 0x3CC8, 0x3CC8, 0x3CC8, 0x3CC8, 0x3CC8, 0x3CC8 } },
    { OBJ_EVENT_GFX_TOTEM_HITMONLEE, TRUE,
        { 0x0000, 0x771A, 0x3CC8, 0x5E12, 0x4D6D, 0x6654, 0x6A96, 0x55AF,
            0x6ED8, 0x55AF, 0x492B, 0x59F1, 0x5E12, 0x3CC8, 0x3CC8, 0x3CC8 } },
    { OBJ_EVENT_GFX_TOTEM_SKARMORY, TRUE,
        { 0x0000, 0x771A, 0x3CC8, 0x6654, 0x51AF, 0x4D6D, 0x6ED8, 0x6675,
            0x492B, 0x40E9, 0x55AF, 0x5E12, 0x3CC8, 0x3CC8, 0x3CC8, 0x3CC8 } },
    { OBJ_EVENT_GFX_PIKACHU, FALSE, // the Plusle and Minun stand-in
        { 0x316D, 0x3CC8, 0x492B, 0x6ED8, 0x518E, 0x6654, 0x59F1, 0x771A,
            0x59F1, 0x3CC8, 0x3CC8, 0x3CC8, 0x3CC8, 0x3CC8, 0x3CC8, 0x3CC8 } },
};

#define ECHO_PALETTE_COUNT NELEMS(sEchoGhostPalettes)

// A ghost's render object points (ptrUser) at its tag, the palette index. NNS_G3dRenderObjInit clears ptrUser and the callback
// when a billboard is reused, so a stale tag can't follow a billboard to another object.
static u8 sEchoGhostTags[ECHO_PALETTE_COUNT];
static NNSGfdPlttKey sEchoPlttKey;
static BOOL sEchoPlttHeld;
static const MapObjectManager *sEchoPlttOwner;
static u8 sEchoOpacity;

static void FieldMoves_EchoGhostMaterialCallback(NNSG3dRS *rs)
{
    NNSG3dRenderObj *renderObj = NNS_G3dRSGetRenderObj(rs);
    NNSG3dMatAnmResult *result;
    const u8 *tag = renderObj->ptrUser;
    int alpha = sEchoOpacity;

    if (tag < &sEchoGhostTags[0] || tag >= &sEchoGhostTags[ECHO_PALETTE_COUNT] || alpha == 0) {
        return;
    }

    result = NNS_G3dRSGetMatAnmResult(rs);

    if (sEchoPlttHeld) {
        result->prmTexPltt = (NNS_GfdGetPlttKeyAddr(sEchoPlttKey) + *tag * sizeof(sEchoGhostPalettes[0].colors)) >> 4;
    }

    result->prmPolygonAttr = (result->prmPolygonAttr & ~(REG_G3_POLYGON_ATTR_ALPHA_MASK | REG_G3_POLYGON_ATTR_ID_MASK))
        | (alpha << REG_G3_POLYGON_ATTR_ALPHA_SHIFT) | ((ECHO_POLYGON_ID + *tag) << REG_G3_POLYGON_ATTR_ID_SHIFT);
}

static void FieldMoves_EchoLoadPalettes(const MapObjectManager *mapObjMan)
{
    u32 addr;

    if (sEchoPlttHeld) {
        return;
    }

    sEchoPlttKey = NNS_GfdAllocPlttVram(sizeof(sEchoGhostPalettes[0].colors) * ECHO_PALETTE_COUNT, FALSE, 0);

    if (sEchoPlttKey == NNS_GFD_ALLOC_ERROR_PLTTKEY) {
        return; // no room: the ghosts stay translucent in their own colours (retried next frame)
    }

    sEchoPlttHeld = TRUE;
    sEchoPlttOwner = mapObjMan;
    addr = NNS_GfdGetPlttKeyAddr(sEchoPlttKey);

    for (int i = 0; i < ECHO_PALETTE_COUNT; i++) {
        VramTransfer_Request(NNS_GFD_DST_3D_TEX_PLTT, addr + i * sizeof(sEchoGhostPalettes[0].colors), (void *)sEchoGhostPalettes[i].colors, sizeof(sEchoGhostPalettes[0].colors));
    }
}

static void FieldMoves_EchoFreePalettes(const MapObjectManager *mapObjMan)
{
    if (sEchoPlttHeld == FALSE) {
        return;
    }

    // A different object manager means a new field with fresh VRAM managers: the old block is already gone.
    if (sEchoPlttOwner == mapObjMan) {
        NNS_GfdFreePlttVram(sEchoPlttKey);
    }

    sEchoPlttHeld = FALSE;
    sEchoPlttOwner = NULL;
}

void FieldMoves_EchoGhostDraw(MapObject *mapObj)
{
    const MapObjectManager *mapObjMan = MapObject_MapObjectManager(mapObj);
    FieldSystem *fieldSystem = MapObjectMan_FieldSystem(mapObjMan);
    u32 localID = MapObject_GetLocalID(mapObj);
    u16 opacity;
    UnkStruct_020216E0 *billboard;
    NNSG3dRenderObj *renderObj;
    u32 graphicsID;
    int palette;

    if (fieldSystem == NULL || fieldSystem->saveData == NULL) {
        return;
    }

    opacity = *VarsFlags_GetVarAddress(SaveData_GetVarsFlags(fieldSystem->saveData), ECHO_OPACITY_VAR);

    if (opacity > ECHO_OPACITY_MAX) {
        opacity = ECHO_OPACITY_MAX;
    }

    sEchoOpacity = opacity;

    if (opacity == 0) {
        FieldMoves_EchoFreePalettes(mapObjMan);
    }

    if (localID < ECHO_LOCALID_FIRST || localID > ECHO_LOCALID_LAST) {
        return;
    }

    if (MapObject_IsHidden(mapObj) != (opacity == 0)) {
        MapObject_SetHidden(mapObj, opacity == 0);
    }

    MapObject_SetStatusFlagOn(mapObj, MAP_OBJ_STATUS_HIDE_SHADOW);

    if (opacity == 0) {
        return;
    }

    graphicsID = MapObject_GetGraphicsID(mapObj);

    for (palette = 0; palette < ECHO_PALETTE_COUNT; palette++) {
        if (sEchoGhostPalettes[palette].graphicsID == graphicsID) {
            break;
        }
    }

    // Only the sprites listed above become ghosts (each renderer keeps its billboard in its own data, so an unlisted
    // sprite's billboard can't be found safely); any other actor is just shown and hidden with the opacity.
    if (palette == ECHO_PALETTE_COUNT) {
        return;
    }

    // The single-frame sprites (crates, frames, rifts, totems) keep their billboard in their own renderer data.
    if (sEchoGhostPalettes[palette].singleFrame) {
        billboard = ov5_021ECB80(mapObj);
    } else {
        billboard = ov5_021EB1A0(mapObj);
    }

    if (billboard == NULL) {
        return;
    }

    FieldMoves_EchoLoadPalettes(mapObjMan);

    sEchoGhostTags[palette] = palette;
    renderObj = sub_02021440(billboard);
    renderObj->ptrUser = &sEchoGhostTags[palette];
    NNS_G3dRenderObjSetCallBack(renderObj, FieldMoves_EchoGhostMaterialCallback, NULL, NNS_G3D_SBC_MAT, NNS_G3D_SBC_CALLBACK_TIMING_B);
}

// Pressing A in fog with nothing else to interact with offers the Resonator's Defog (FieldMoves_Fog).
u16 FieldMoves_GetFogInteractScript(FieldSystem *fieldSystem)
{
    if (FieldOverworldState_GetWeather(SaveData_GetFieldOverworldState(fieldSystem->saveData)) == OVERWORLD_WEATHER_FOG
        && SystemFlag_CheckDefogActive(SaveData_GetVarsFlags(fieldSystem->saveData)) == FALSE) {
        return 10005;
    }

    return 0xFFFF;
}

static inline BOOL PlayerTravellingWithPartner(const FieldMoveContext *fieldMoveContext)
{
    return SystemFlag_CheckHasPartner(SaveData_GetVarsFlags(fieldMoveContext->fieldSystem->saveData));
}

static inline BOOL PlayerInSafariZoneOrPalPark(const FieldMoveContext *fieldMoveContext)
{
    if ((SystemFlag_CheckSafariGameActive(SaveData_GetVarsFlags(fieldMoveContext->fieldSystem->saveData)) == TRUE)
        || (SystemFlag_CheckInPalPark(SaveData_GetVarsFlags(fieldMoveContext->fieldSystem->saveData)) == TRUE)) {
        return TRUE;
    }

    return FALSE;
}

static inline BOOL PlayerInPalPark(const FieldMoveContext *fieldMoveContext)
{
    if (SystemFlag_CheckInPalPark(SaveData_GetVarsFlags(fieldMoveContext->fieldSystem->saveData)) == TRUE) {
        return TRUE;
    }

    return FALSE;
}

static inline BOOL PlayerOutsideLinkRoom(const FieldMoveContext *fieldMoveContext)
{
    if ((fieldMoveContext->fieldSystem->mapLoadType == MAP_LOAD_TYPE_COLOSSEUM) || (fieldMoveContext->fieldSystem->mapLoadType == MAP_LOAD_TYPE_UNION)) {
        return FALSE;
    }

    return TRUE;
}

void *FieldMove_GetTaskOrError(u16 taskOrError, u16 fieldMove)
{
    if (taskOrError == FIELD_MOVE_TASK) {
        return fieldMoveTaskOrError[fieldMove].task;
    }

    return fieldMoveTaskOrError[fieldMove].error;
}

void FieldMoves_SetUsableMoves(FieldSystem *fieldSystem, FieldMoveContext *fieldMoveContext)
{
    MapObject *mapObj;
    int playerX, playerY;
    int nextTileBehavior;
    int currTileBehavior;

    fieldMoveContext->fieldSystem = fieldSystem;
    fieldMoveContext->mapId = fieldSystem->location->mapId;
    fieldMoveContext->usableMoves = 0;

    if (PlayerAvatar_DistortionGravityChanged(fieldSystem->playerAvatar) == TRUE) {
        FieldMoves_CanUseSurfDistortionWorld(fieldSystem, fieldMoveContext);
        return;
    }

    sub_0203C9D4(fieldSystem, &mapObj);
    fieldMoveContext->mapObj = mapObj;

    if (mapObj != NULL) {
        switch (MapObject_GetGraphicsID(mapObj)) {
        case OBJ_EVENT_GFX_STRENGTH_BOULDER:
            fieldMoveContext->usableMoves |= FIELD_MOVE_FLAG(FIELD_MOVE_STRENGTH);
            break;
        case OBJ_EVENT_GFX_ROCK_SMASH:
            fieldMoveContext->usableMoves |= FIELD_MOVE_FLAG(FIELD_MOVE_ROCK_SMASH);
            break;
        case OBJ_EVENT_GFX_CUT_TREE:
            fieldMoveContext->usableMoves |= FIELD_MOVE_FLAG(FIELD_MOVE_CUT);
            break;
        }
    }

    playerX = Player_GetXPos(fieldSystem->playerAvatar);
    playerY = Player_GetZPos(fieldSystem->playerAvatar);
    currTileBehavior = TerrainCollisionManager_GetTileBehavior(fieldSystem, playerX, playerY);

    PlayerAvatar_GetFacingTileCoords(fieldSystem->playerAvatar, &playerX, &playerY);
    nextTileBehavior = TerrainCollisionManager_GetTileBehavior(fieldSystem, playerX, playerY);

    if (PlayerAvatar_CanUseSurf(fieldSystem->playerAvatar, currTileBehavior, nextTileBehavior)) {
        fieldMoveContext->usableMoves |= FIELD_MOVE_FLAG(FIELD_MOVE_SURF);
    }

    if (PlayerAvatar_CanUseRockClimb(nextTileBehavior, PlayerAvatar_GetDir(fieldSystem->playerAvatar))) {
        fieldMoveContext->usableMoves |= FIELD_MOVE_FLAG(FIELD_MOVE_ROCK_CLIMB);
    }

    if (TileBehavior_IsWaterfall(nextTileBehavior)) {
        fieldMoveContext->usableMoves |= FIELD_MOVE_FLAG(FIELD_MOVE_WATERFALL);
    }

    switch (FieldOverworldState_GetWeather(SaveData_GetFieldOverworldState(fieldSystem->saveData))) {
    case OVERWORLD_WEATHER_FOG:
        fieldMoveContext->usableMoves |= FIELD_MOVE_FLAG(FIELD_MOVE_DEFOG);
        break;
    case OVERWORLD_WEATHER_DARK_FLASH:
        fieldMoveContext->usableMoves |= FIELD_MOVE_FLAG(FIELD_MOVE_FLASH);
        break;
    }
}

static void FieldMoves_CanUseSurfDistortionWorld(FieldSystem *fieldSystem, FieldMoveContext *fieldMoveContext)
{
    int distortionDir;
    u32 currTileBehavior, nextTileBehavior;

    distortionDir = PlayerAvatar_GetDistortionDir(fieldSystem->playerAvatar);
    nextTileBehavior = PlayerAvatar_GetDistortionTileBehaviour(fieldSystem->playerAvatar, distortionDir);
    currTileBehavior = PlayerAvatar_GetDistortionCurrTileBehaviour(fieldSystem->playerAvatar);

    if (PlayerAvatar_CanUseSurf(fieldSystem->playerAvatar, currTileBehavior, nextTileBehavior) == TRUE) {
        fieldMoveContext->usableMoves |= FIELD_MOVE_FLAG(FIELD_MOVE_SURF);
    }
}

// D11: field obstacles are cleared with the Resonator only. The party menu doesn't list these moves any more; if one
// is ever selected from it anyway, it's refused like a move with nothing to act on.
static enum FieldMoveError FieldMoves_CheckResonatorObstacle(const FieldMoveContext *fieldMoveContext)
{
    return FIELD_MOVE_ERROR_LOCATION;
}

static FieldMoveTaskData *FieldMoves_AllocateTaskData(const FieldMovePokemon *fieldMoveMon, const FieldMoveContext *fieldMoveContext)
{
    FieldMoveTaskData *taskData = Heap_Alloc(HEAP_ID_FIELD3, sizeof(FieldMoveTaskData));

    taskData->magicNumber = 0x19740205;
    taskData->mapObj = fieldMoveContext->mapObj;
    taskData->fieldMoveMon = *fieldMoveMon;

    return taskData;
}

static void FieldMoves_FreeTaskData(FieldMoveTaskData *taskData)
{
    GF_ASSERT(taskData->magicNumber == 0x19740205);
    Heap_Free(taskData);
}

static void FieldMoves_SetCutTask(FieldMovePokemon *fieldMoveMon, const FieldMoveContext *fieldMoveContext)
{
    StartMenu *menu = FieldTask_GetEnv(fieldMoveMon->fieldTask);
    FieldMoveTaskData *taskData = FieldMoves_AllocateTaskData(fieldMoveMon, fieldMoveContext);

    FieldSystem_StartFieldMap(fieldMoveContext->fieldSystem);

    menu->callback = FieldMoves_CutTask;
    menu->taskData = taskData;
    menu->state = START_MENU_STATE_10;
}

static BOOL FieldMoves_CutTask(FieldTask *taskMan)
{
    FieldMoveTaskData *taskData = FieldTask_GetEnv(taskMan);
    FieldSystem *fieldSystem = FieldTask_GetFieldSystem(taskMan);

    ScriptManager_Change(taskMan, 10008, taskData->mapObj);
    FieldSystem_SetScriptParameters(fieldSystem, taskData->fieldMoveMon.fieldMonId, 0, 0, 0);
    FieldMoves_FreeTaskData(taskData);

    return 0;
}

static enum FieldMoveError FieldMoves_CheckFly(const FieldMoveContext *fieldMoveContext)
{
    enum FieldMoveError progressionError;

    if (PlayerOutsideLinkRoom(fieldMoveContext) == FALSE) {
        return FIELD_MOVE_ERROR_LOCATION;
    }

    // Fly is Skarmory's power through the Resonator (S8), like the obstacle powers.
    if (FieldMoves_HasResonator(fieldMoveContext->fieldSystem) == FALSE) {
        return FIELD_MOVE_ERROR_LOCATION;
    }

    progressionError = FieldMoves_CheckProgression(fieldMoveContext, BADGE_ID_COBBLE, FLAG_TOTEM_SKARMORY_DEFEATED);
    if (progressionError != FIELD_MOVE_ERROR_NONE) {
        return progressionError;
    }

    if (MapHeader_IsFlyAllowed(fieldMoveContext->mapId) == FALSE) {
        return FIELD_MOVE_ERROR_LOCATION;
    }

    if (PlayerTravellingWithPartner(fieldMoveContext) == TRUE) {
        return FIELD_MOVE_ERROR_PARTNER;
    }

    if (PlayerInSafariZoneOrPalPark(fieldMoveContext) == TRUE) {
        return FIELD_MOVE_ERROR_LOCATION;
    }

    return FIELD_MOVE_ERROR_NONE;
}

static void FieldMoves_SetFlyTask(FieldMovePokemon *fieldMoveMon, const FieldMoveContext *fieldMoveContext)
{
    FieldSystem *fieldSystem = FieldTask_GetFieldSystem(fieldMoveMon->fieldTask);
    StartMenu *menu = FieldTask_GetEnv(fieldMoveMon->fieldTask);

    u32 *fieldMonID = Heap_Alloc(HEAP_ID_FIELD2, sizeof(u32));
    *fieldMonID = fieldMoveMon->fieldMonId;
    menu->unk_260 = fieldMonID;

    menu->taskData = Heap_Alloc(HEAP_ID_FIELD2, sizeof(TownMapContext));

    TownMapContext_Init(fieldSystem, menu->taskData, TOWN_MAP_MODE_FLY);
    FieldSystem_OpenTownMap(fieldSystem, menu->taskData);
    sub_0203B674(menu, sub_0203C434);
}

static void FieldMoves_SetSurfTask(FieldMovePokemon *fieldMoveMon, const FieldMoveContext *fieldMoveContext)
{
    StartMenu *menu = FieldTask_GetEnv(fieldMoveMon->fieldTask);
    FieldMoveTaskData *taskData = FieldMoves_AllocateTaskData(fieldMoveMon, fieldMoveContext);

    FieldSystem_StartFieldMap(fieldMoveContext->fieldSystem);

    menu->callback = FieldMoves_SurfTask;
    menu->taskData = taskData;
    menu->state = START_MENU_STATE_10;
}

static BOOL FieldMoves_SurfTask(FieldTask *taskMan)
{
    FieldMoveTaskData *taskData = FieldTask_GetEnv(taskMan);
    FieldSystem *fieldSystem = FieldTask_GetFieldSystem(taskMan);

    ScriptManager_Change(taskMan, 10012, NULL);
    FieldSystem_SetScriptParameters(fieldSystem, taskData->fieldMoveMon.fieldMonId, 0, 0, 0);
    FieldMoves_FreeTaskData(taskData);

    return 0;
}

static void FieldMoves_SetStrengthTask(FieldMovePokemon *fieldMoveMon, const FieldMoveContext *fieldMoveContext)
{
    StartMenu *menu = FieldTask_GetEnv(fieldMoveMon->fieldTask);
    FieldMoveTaskData *taskData = FieldMoves_AllocateTaskData(fieldMoveMon, fieldMoveContext);

    FieldSystem_StartFieldMap(fieldMoveContext->fieldSystem);

    menu->callback = FieldMoves_StrengthTask;
    menu->taskData = taskData;
    menu->state = START_MENU_STATE_10;
}

static BOOL FieldMoves_StrengthTask(FieldTask *param0)
{
    FieldMoveTaskData *taskData = FieldTask_GetEnv(param0);
    FieldSystem *fieldSystem = FieldTask_GetFieldSystem(param0);

    ScriptManager_Change(param0, 10010, taskData->mapObj);
    FieldSystem_SetScriptParameters(fieldSystem, taskData->fieldMoveMon.fieldMonId, 0, 0, 0);
    FieldMoves_FreeTaskData(taskData);

    return 0;
}

static void FieldMoves_SetDefogTask(FieldMovePokemon *fieldMoveMon, const FieldMoveContext *fieldMoveContext)
{
    StartMenu *menu = FieldTask_GetEnv(fieldMoveMon->fieldTask);
    FieldMoveTaskData *taskData = FieldMoves_AllocateTaskData(fieldMoveMon, fieldMoveContext);

    FieldSystem_StartFieldMap(fieldMoveContext->fieldSystem);

    menu->callback = FieldMoves_DefogTask;
    menu->taskData = taskData;
    menu->state = START_MENU_STATE_10;
}

static BOOL FieldMoves_DefogTask(FieldTask *taskMan)
{
    FieldMoveTaskData *taskData = FieldTask_GetEnv(taskMan);
    FieldSystem *fieldSystem = FieldTask_GetFieldSystem(taskMan);

    ScriptManager_Change(taskMan, 10014, NULL);
    FieldSystem_SetScriptParameters(fieldSystem, taskData->fieldMoveMon.fieldMonId, 0, 0, 0);
    FieldMoves_FreeTaskData(taskData);

    return 0;
}

static void FieldMoves_SetRockSmashTask(FieldMovePokemon *fieldMoveMon, const FieldMoveContext *fieldMoveContext)
{
    StartMenu *menu = FieldTask_GetEnv(fieldMoveMon->fieldTask);
    FieldMoveTaskData *taskData = FieldMoves_AllocateTaskData(fieldMoveMon, fieldMoveContext);

    FieldSystem_StartFieldMap(fieldMoveContext->fieldSystem);

    menu->callback = FieldMoves_RockSmashTask;
    menu->taskData = taskData;
    menu->state = START_MENU_STATE_10;
}

static BOOL FieldMoves_RockSmashTask(FieldTask *taskMan)
{
    FieldMoveTaskData *taskData = FieldTask_GetEnv(taskMan);
    FieldSystem *fieldSystem = FieldTask_GetFieldSystem(taskMan);

    ScriptManager_Change(taskMan, 10009, taskData->mapObj);
    FieldSystem_SetScriptParameters(fieldSystem, taskData->fieldMoveMon.fieldMonId, 0, 0, 0);
    FieldMoves_FreeTaskData(taskData);

    return 0;
}

static void FieldMoves_SetWaterfallTask(FieldMovePokemon *fieldMoveMon, const FieldMoveContext *fieldMoveContext)
{
    StartMenu *menu = FieldTask_GetEnv(fieldMoveMon->fieldTask);
    FieldMoveTaskData *taskData = FieldMoves_AllocateTaskData(fieldMoveMon, fieldMoveContext);

    FieldSystem_StartFieldMap(fieldMoveContext->fieldSystem);

    menu->callback = FieldMoves_WaterfallTask;
    menu->taskData = taskData;
    menu->state = START_MENU_STATE_10;
}

static BOOL FieldMoves_WaterfallTask(FieldTask *param0)
{
    FieldMoveTaskData *taskData = FieldTask_GetEnv(param0);
    FieldSystem *fieldSystem = FieldTask_GetFieldSystem(param0);

    ScriptManager_Change(param0, 10013, NULL);
    FieldSystem_SetScriptParameters(fieldSystem, taskData->fieldMoveMon.fieldMonId, 0, 0, 0);
    FieldMoves_FreeTaskData(taskData);

    return 0;
}

static void FieldMoves_SetRockClimbTask(FieldMovePokemon *fieldMoveMon, const FieldMoveContext *fieldMoveContext)
{
    StartMenu *menu = FieldTask_GetEnv(fieldMoveMon->fieldTask);
    FieldMoveTaskData *taskData = FieldMoves_AllocateTaskData(fieldMoveMon, fieldMoveContext);

    FieldSystem_StartFieldMap(fieldMoveContext->fieldSystem);

    menu->callback = FieldMoves_RockClimbTask;
    menu->taskData = taskData;
    menu->state = START_MENU_STATE_10;
}

static BOOL FieldMoves_RockClimbTask(FieldTask *taskMan)
{
    FieldMoveTaskData *taskData = FieldTask_GetEnv(taskMan);
    FieldSystem *fieldSystem = FieldTask_GetFieldSystem(taskMan);

    ScriptManager_Change(taskMan, 10011, NULL);
    FieldSystem_SetScriptParameters(fieldSystem, taskData->fieldMoveMon.fieldMonId, 0, 0, 0);
    FieldMoves_FreeTaskData(taskData);

    return 0;
}

static enum FieldMoveError FieldMoves_CheckFlash(const FieldMoveContext *fieldMoveContext)
{
    if (PlayerOutsideLinkRoom(fieldMoveContext) == FALSE) {
        return FIELD_MOVE_ERROR_LOCATION;
    }

    if (FieldMoves_IsMoveUsable(fieldMoveContext, FIELD_MOVE_FLASH)) {
        return FIELD_MOVE_ERROR_NONE;
    }

    return FIELD_MOVE_ERROR_LOCATION;
}

static void FieldMoves_SetFlashTask(FieldMovePokemon *fieldMoveMon, const FieldMoveContext *fieldMoveContext)
{
    StartMenu *menu = FieldTask_GetEnv(fieldMoveMon->fieldTask);
    FieldMoveTaskData *taskData = FieldMoves_AllocateTaskData(fieldMoveMon, fieldMoveContext);

    FieldSystem_StartFieldMap(fieldMoveContext->fieldSystem);

    menu->callback = FieldMoves_FlashTask;
    menu->taskData = taskData;
    menu->state = START_MENU_STATE_10;
}

static BOOL FieldMoves_FlashTask(FieldTask *taskMan)
{
    FieldMoveTaskData *taskData = FieldTask_GetEnv(taskMan);
    FieldSystem *fieldSystem = FieldTask_GetFieldSystem(taskMan);

    ScriptManager_Change(taskMan, 10015, NULL);
    FieldSystem_SetScriptParameters(fieldSystem, taskData->fieldMoveMon.fieldMonId, 0, 0, 0);
    FieldMoves_FreeTaskData(taskData);

    return 0;
}

static enum FieldMoveError FieldMoves_CheckTeleport(const FieldMoveContext *fieldMoveContext)
{
    if (PlayerOutsideLinkRoom(fieldMoveContext) == FALSE) {
        return FIELD_MOVE_ERROR_LOCATION;
    }

    if (MapHeader_IsTeleportAllowed(fieldMoveContext->mapId) == FALSE) {
        return FIELD_MOVE_ERROR_LOCATION;
    }

    if (PlayerTravellingWithPartner(fieldMoveContext) == TRUE) {
        return FIELD_MOVE_ERROR_PARTNER;
    }

    if (PlayerInSafariZoneOrPalPark(fieldMoveContext) == TRUE) {
        return FIELD_MOVE_ERROR_LOCATION;
    }

    return FIELD_MOVE_ERROR_NONE;
}

static void FieldMoves_SetTeleportTask(FieldMovePokemon *fieldMoveMon, const FieldMoveContext *fieldMoveContext)
{
    FieldSystem *fieldSystem = FieldTask_GetFieldSystem(fieldMoveMon->fieldTask);
    StartMenu *menu = FieldTask_GetEnv(fieldMoveMon->fieldTask);

    FieldSystem_StartFieldMap(fieldSystem);

    UnkStruct_020711C8 *v2 = sub_020711C8(HEAP_ID_FIELD2, fieldMoveMon->fieldMonId, fieldSystem->saveData);

    menu->callback = FieldMoves_TeleportTask;
    menu->taskData = v2;
    menu->state = START_MENU_STATE_10;
}

static BOOL FieldMoves_TeleportTask(FieldTask *param0)
{
    FieldSystem *fieldSystem = FieldTask_GetFieldSystem(param0);
    UnkStruct_020711C8 *v1 = FieldTask_GetEnv(param0);
    void *v2 = ov6_02247530(fieldSystem, v1->unk_00, HEAP_ID_FIELD1);

    Heap_Free(v1);
    FieldTask_InitJump(param0, ov6_02247554, v2);

    return 0;
}

static enum FieldMoveError FieldMoves_CheckDig(const FieldMoveContext *fieldMoveContext)
{
    if (PlayerOutsideLinkRoom(fieldMoveContext) == FALSE) {
        return FIELD_MOVE_ERROR_LOCATION;
    }

    if (!((MapHeader_IsCave(fieldMoveContext->mapId) == TRUE) && (MapHeader_IsEscapeRopeAllowed(fieldMoveContext->mapId) == TRUE))) {
        return FIELD_MOVE_ERROR_LOCATION;
    }

    if (PlayerTravellingWithPartner(fieldMoveContext) == TRUE) {
        return FIELD_MOVE_ERROR_PARTNER;
    }

    return FIELD_MOVE_ERROR_NONE;
}

static void FieldMoves_SetDigTask(FieldMovePokemon *fieldMoveMon, const FieldMoveContext *fieldMoveContext)
{
    FieldSystem *fieldSystem = FieldTask_GetFieldSystem(fieldMoveMon->fieldTask);
    StartMenu *v1 = FieldTask_GetEnv(fieldMoveMon->fieldTask);

    FieldSystem_StartFieldMap(fieldSystem);

    UnkStruct_020711C8 *v2 = sub_020711C8(HEAP_ID_FIELD2, fieldMoveMon->fieldMonId, fieldSystem->saveData);

    v1->callback = FieldMoves_DigTask;
    v1->taskData = v2;
    v1->state = START_MENU_STATE_10;
}

static BOOL FieldMoves_DigTask(FieldTask *param0)
{
    FieldSystem *fieldSystem = FieldTask_GetFieldSystem(param0);
    UnkStruct_020711C8 *v1 = FieldTask_GetEnv(param0);
    void *v2 = ov6_02247488(fieldSystem, v1->unk_00, HEAP_ID_FIELD2);

    void *journalEntryLocationEvent = JournalEntry_CreateEventUsedMove(LOCATION_EVENT_USED_DIG - LOCATION_EVENT_USED_CUT, fieldSystem->location->mapId, HEAP_ID_FIELD1);
    JournalEntry_SaveData(fieldSystem->journalEntry, journalEntryLocationEvent, JOURNAL_LOCATION);

    Heap_Free(v1);
    FieldTask_InitJump(param0, ov6_022474AC, v2);

    return FALSE;
}

static enum FieldMoveError FieldMoves_CheckSweetScent(const FieldMoveContext *fieldMoveContext)
{
    if (PlayerOutsideLinkRoom(fieldMoveContext) == FALSE) {
        return FIELD_MOVE_ERROR_LOCATION;
    }

    if (PlayerInPalPark(fieldMoveContext) == TRUE) {
        return FIELD_MOVE_ERROR_LOCATION;
    }

    return FIELD_MOVE_ERROR_NONE;
}

static void FieldMoves_SetSweetScentTask(FieldMovePokemon *fieldMoveMon, const FieldMoveContext *fieldMoveContext)
{
    FieldSystem *fieldSystem = FieldTask_GetFieldSystem(fieldMoveMon->fieldTask);
    StartMenu *startMenu = FieldTask_GetEnv(fieldMoveMon->fieldTask);
    UnkStruct_020711C8 *v2 = sub_020711C8(HEAP_ID_FIELD2, fieldMoveMon->fieldMonId, fieldSystem->saveData);
    int unused;
    void *v4;

    FieldSystem_StartFieldMap(fieldSystem);

    startMenu->callback = ov5_021F101C;
    startMenu->taskData = v2;
    startMenu->state = START_MENU_STATE_10;

    v4 = JournalEntry_CreateEventUsedMove(LOCATION_EVENT_LURED_POKEMON - LOCATION_EVENT_USED_CUT, fieldSystem->location->mapId, HEAP_ID_FIELD2);
    JournalEntry_SaveData(fieldSystem->journalEntry, v4, JOURNAL_LOCATION);
}

static enum FieldMoveError FieldMoves_CheckChatter(const FieldMoveContext *fieldMoveContext)
{
    if ((PlayerOutsideLinkRoom(fieldMoveContext) == FALSE) || (PersistedMapFeatures_IsCurrentDynamicMap(fieldMoveContext->fieldSystem, 9) == TRUE)) {
        return FIELD_MOVE_ERROR_LOCATION;
    }

    return FIELD_MOVE_ERROR_NONE;
}

static void FieldMoves_SetChatterTask(FieldMovePokemon *fieldMoveMon, const FieldMoveContext *fieldMoveContext)
{
    FieldSystem *fieldSystem = FieldTask_GetFieldSystem(fieldMoveMon->fieldTask);
    StartMenu *menu = FieldTask_GetEnv(fieldMoveMon->fieldTask);
    FieldMoveTaskData *taskData = FieldMoves_AllocateTaskData(fieldMoveMon, fieldMoveContext);

    FieldSystem_StartFieldMap(fieldSystem);

    menu->callback = FieldMoves_ChatterTask;
    menu->taskData = taskData;
    menu->state = START_MENU_STATE_10;
}

static BOOL FieldMoves_ChatterTask(FieldTask *taskMan)
{
    FieldMoveTaskData *taskData = FieldTask_GetEnv(taskMan);
    FieldSystem *fieldSystem = FieldTask_GetFieldSystem(taskMan);

    ScriptManager_Change(taskMan, 8900, NULL);
    FieldSystem_SetScriptParameters(fieldSystem, taskData->fieldMoveMon.fieldMonId, 0, 0, 0);
    FieldMoves_FreeTaskData(taskData);

    return 0;
}
