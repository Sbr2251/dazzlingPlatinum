#include "overlay005/field_phenomena.h"

#include <nitro.h>
#include <string.h>

#include "constants/battle.h"
#include "constants/field/dynamic_map_features.h"
#include "constants/field/map.h"
#include "constants/fieldmap.h"
#include "constants/heap.h"
#include "constants/map_object.h"
#include "constants/wild_encounters.h"
#include "generated/badges.h"

#include "struct_decls/map_object.h"
#include "struct_defs/wild_encounters.h"

#include "field/field_system.h"
#include "overlay005/land_data.h"
#include "overlay006/phenomena_tables.h"
#include "overlay006/wild_encounters.h"
#include "port/sim_config_prj.h"

#include "bag.h"
#include "encounter.h"
#include "field_battle_data_transfer.h"
#include "location.h"
#include "map_header.h"
#include "map_header_data.h"
#include "map_matrix.h"
#include "map_object.h"
#include "map_tile_behavior.h"
#include "math_util.h"
#include "persisted_map_features_init.h"
#include "player_avatar.h"
#include "pokeradar.h"
#include "rtc.h"
#include "save_player.h"
#include "sound_playback.h"
#include "system_flags.h"
#include "terrain_collision_manager.h"
#include "trainer_info.h"

#define PHENOMENA_SCAN_MIN_DIST   2
#define PHENOMENA_SCAN_MAX_DIST   5
#define PHENOMENA_MAX_CANDIDATES  128
#define PHENOMENA_MAX_PLAYER_DIST 14
#define PHENOMENA_SFX_MAX_DIST    6
#define PHENOMENA_SFX_COOLDOWN    50

typedef struct {
    BOOL active;
    enum PhenomenonType type;
    int mapHeaderID;
    int tileX;
    int tileZ;
    int stepCounter;
    int animFrame;
    int sfxCooldown;
    fx32 worldX;
    fx32 worldY;
    fx32 worldZ;
} FieldPhenomenaState;

typedef struct {
    int x;
    int z;
    enum PhenomenonType type;
} PhenomenonCandidate;

static FieldPhenomenaState sPhenomena = { 0 };

static int AbsInt(int v)
{
    return v < 0 ? -v : v;
}

static BOOL IsForbiddenMap(FieldSystem *fieldSystem, int mapHeaderID)
{
    if (fieldSystem == NULL) {
        return TRUE;
    }

    if (mapHeaderID >= MAP_HEADER_GREAT_MARSH_1 && mapHeaderID <= MAP_HEADER_GREAT_MARSH_6) {
        return TRUE;
    }
    if (MapHeader_IsTrophyGarden(mapHeaderID)) {
        return TRUE;
    }
    if (mapHeaderID == MAP_HEADER_PAL_PARK || mapHeaderID == MAP_HEADER_PAL_PARK_LOBBY) {
        return TRUE;
    }
    if ((mapHeaderID >= MAP_HEADER_DISTORTION_WORLD_1F && mapHeaderID <= MAP_HEADER_DISTORTION_WORLD_TURNBACK_CAVE_ROOM)
        || mapHeaderID == MAP_HEADER_DISTORTION_WORLD_ARC1_SEAMS) {
        return TRUE;
    }
    if (PersistedMapFeatures_IsCurrentDynamicMap(fieldSystem, DYNAMIC_MAP_FEATURES_DISTORTION_WORLD) == TRUE) {
        return TRUE;
    }
    if (fieldSystem->saveData != NULL) {
        VarsFlags *varsFlags = SaveData_GetVarsFlags(fieldSystem->saveData);
        if (SystemFlag_CheckSafariGameActive(varsFlags) == TRUE || SystemFlag_CheckInPalPark(varsFlags) == TRUE) {
            return TRUE;
        }
    }
    return FALSE;
}

static BOOL IsPhenomenaAllowed(FieldSystem *fieldSystem)
{
    if (!SIM_Config_prj_PhenomenaEnabled()) {
        return FALSE;
    }
    if (fieldSystem == NULL || fieldSystem->saveData == NULL || fieldSystem->location == NULL || fieldSystem->playerAvatar == NULL) {
        return FALSE;
    }
    if (!TrainerInfo_HasBadge(SaveData_GetTrainerInfo(fieldSystem->saveData), BADGE_ID_COAL)) {
        return FALSE;
    }
    if (fieldSystem->chain != NULL && GetRadarChainActive(fieldSystem->chain) == TRUE) {
        return FALSE;
    }
    if (IsForbiddenMap(fieldSystem, fieldSystem->location->mapHeaderID)) {
        return FALSE;
    }
    return TRUE;
}

static BOOL IsCyclingRoadDeckTile(FieldSystem *fieldSystem, int mapHeaderID, int tileX, int tileZ)
{
    if (mapHeaderID != MAP_HEADER_ROUTE_206) {
        return FALSE;
    }
    u8 beh = TerrainCollisionManager_GetTileBehavior(fieldSystem, tileX, tileZ);
    if (TileBehavior_IsBikeBridgeNorthSouth(beh) || TileBehavior_IsBikeBridgeEastWest(beh) || TileBehavior_IsBridge(beh)) {
        return TRUE;
    }
    MapObject *playerObj = PlayerAvatar_GetMapObject(fieldSystem->playerAvatar);
    if (playerObj != NULL && MapObject_CheckStatusFlag(playerObj, MAP_OBJ_STATUS_ON_ELEVATED_BRIDGE)) {
        return TRUE;
    }
    return FALSE;
}

static BOOL HasMapObjectAtTile(FieldSystem *fieldSystem, int tileX, int tileZ)
{
    if (fieldSystem->mapObjMan == NULL) {
        return FALSE;
    }
    MapObject *obj = NULL;
    int idx = 0;
    while (MapObjectMan_FindObjectWithStatus(fieldSystem->mapObjMan, &obj, &idx, MAP_OBJ_STATUS_0) == TRUE) {
        if (MapObject_CheckStatusFlag(obj, MAP_OBJ_STATUS_AUTO_BORDER_CLONE)) {
            continue;
        }
        if (MapObject_GetX(obj) == tileX && MapObject_GetZ(obj) == tileZ) {
            return TRUE;
        }
    }
    return FALSE;
}

static BOOL IsTileSameMapHeader(FieldSystem *fieldSystem, int mapHeaderID, int tileX, int tileZ)
{
    if (fieldSystem->mapMatrix == NULL || fieldSystem->landDataMan == NULL) {
        return FALSE;
    }
    int offsetX = LandDataManager_GetOffsetTileX(fieldSystem->landDataMan);
    int offsetZ = LandDataManager_GetOffsetTileZ(fieldSystem->landDataMan);
    int mx = (tileX - offsetX) / MAP_TILES_COUNT_X;
    int mz = (tileZ - offsetZ) / MAP_TILES_COUNT_Z;
    if (tileX - offsetX < 0 || tileZ - offsetZ < 0) {
        return FALSE;
    }
    return (int)MapMatrix_GetMapHeaderIDAtCoords(fieldSystem->mapMatrix, mx, mz) == mapHeaderID;
}

static BOOL IsTileValidForPhenomenon(FieldSystem *fieldSystem, int mapHeaderID, int tileX, int tileZ, enum PhenomenonType type)
{
    if (!IsTileSameMapHeader(fieldSystem, mapHeaderID, tileX, tileZ)) {
        return FALSE;
    }
    if (HasMapObjectAtTile(fieldSystem, tileX, tileZ)) {
        return FALSE;
    }

    u8 beh = TerrainCollisionManager_GetTileBehavior(fieldSystem, tileX, tileZ);

    switch (type) {
    case PHENOMENON_GRASS:
        return TileBehavior_IsTallGrass(beh) || TileBehavior_IsVeryTallGrass(beh);

    case PHENOMENON_DUST:
        if (!MapHeader_IsCave(mapHeaderID)) {
            return FALSE;
        }
        if (TerrainCollisionManager_CheckCollision(fieldSystem, tileX, tileZ)) {
            return FALSE;
        }
        if (TileBehavior_IsNull(beh)
            || TileBehavior_IsSurfable(beh)
            || TileBehavior_IsShallowWater(beh)
            || TileBehavior_IsDoor(beh)
            || TileBehavior_IsWarpEntranceNorth(beh)
            || TileBehavior_IsWarpEntranceSouth(beh)
            || TileBehavior_IsWarpEntranceEast(beh)
            || TileBehavior_IsWarpEntranceWest(beh)
            || TileBehavior_IsWarpNorth(beh)
            || TileBehavior_IsWarpSouth(beh)
            || TileBehavior_IsWarpEast(beh)
            || TileBehavior_IsWarpWest(beh)
            || TileBehavior_IsWarpStairsEast(beh)
            || TileBehavior_IsWarpStairsWest(beh)) {
            return FALSE;
        }
        return TRUE;

    case PHENOMENON_WATER:
        return TileBehavior_IsSurfable(beh);

    case PHENOMENON_SHADOW:
        if (mapHeaderID != MAP_HEADER_ROUTE_206) {
            return FALSE;
        }
        if (TerrainCollisionManager_CheckCollision(fieldSystem, tileX, tileZ)) {
            return FALSE;
        }
        return IsCyclingRoadDeckTile(fieldSystem, mapHeaderID, tileX, tileZ);

    default:
        return FALSE;
    }
}

static void ActivatePhenomenon(FieldSystem *fieldSystem, enum PhenomenonType type, int mapHeaderID, int tileX, int tileZ)
{
    fx32 worldX = (FX32_ONE * 16 * tileX) + (FX32_ONE * 8);
    fx32 worldZ = (FX32_ONE * 16 * tileZ) + (FX32_ONE * 8);
    const VecFx32 *playerPos = PlayerAvatar_GetPos(fieldSystem->playerAvatar);
    fx32 refY = playerPos != NULL ? playerPos->y : 0;
    u8 heightSrc = 0;
    fx32 worldY = TerrainCollisionManager_GetHeight(fieldSystem, refY, worldX, worldZ, &heightSrc);

    sPhenomena.active = TRUE;
    sPhenomena.type = type;
    sPhenomena.mapHeaderID = mapHeaderID;
    sPhenomena.tileX = tileX;
    sPhenomena.tileZ = tileZ;
    sPhenomena.animFrame = 0;
    sPhenomena.sfxCooldown = 10;
    sPhenomena.worldX = worldX;
    sPhenomena.worldY = worldY;
    sPhenomena.worldZ = worldZ;
}

static BOOL TrySpawnRandomPhenomenon(FieldSystem *fieldSystem)
{
    int mapHeaderID = fieldSystem->location->mapHeaderID;
    int playerX = PlayerAvatar_GetXPos(fieldSystem->playerAvatar);
    int playerZ = PlayerAvatar_GetZPos(fieldSystem->playerAvatar);

    BOOL allowType[5] = { FALSE, FALSE, FALSE, FALSE, FALSE };
    BOOL anyAllowed = FALSE;
    for (int t = PHENOMENON_GRASS; t <= PHENOMENON_SHADOW; t++) {
        if (PhenomenaTables_MapHasPhenomenon(mapHeaderID, (enum PhenomenonType)t)) {
            allowType[t] = TRUE;
            anyAllowed = TRUE;
        }
    }
    if (!anyAllowed) {
        return FALSE;
    }

    PhenomenonCandidate candidates[PHENOMENA_MAX_CANDIDATES];
    int count = 0;

    for (int dz = -PHENOMENA_SCAN_MAX_DIST; dz <= PHENOMENA_SCAN_MAX_DIST; dz++) {
        for (int dx = -PHENOMENA_SCAN_MAX_DIST; dx <= PHENOMENA_SCAN_MAX_DIST; dx++) {
            int adx = AbsInt(dx);
            int adz = AbsInt(dz);
            int cheb = adx > adz ? adx : adz;
            if (cheb < PHENOMENA_SCAN_MIN_DIST || cheb > PHENOMENA_SCAN_MAX_DIST) {
                continue;
            }
            int tx = playerX + dx;
            int tz = playerZ + dz;
            for (int t = PHENOMENON_GRASS; t <= PHENOMENON_SHADOW; t++) {
                if (!allowType[t]) {
                    continue;
                }
                if (IsTileValidForPhenomenon(fieldSystem, mapHeaderID, tx, tz, (enum PhenomenonType)t)) {
                    if (count < PHENOMENA_MAX_CANDIDATES) {
                        candidates[count].x = tx;
                        candidates[count].z = tz;
                        candidates[count].type = (enum PhenomenonType)t;
                        count++;
                    }
                    break;
                }
            }
        }
    }

    if (count == 0) {
        return FALSE;
    }

    int pick = (int)(LCRNG_Next() % (u32)count);
    ActivatePhenomenon(fieldSystem, candidates[pick].type, mapHeaderID, candidates[pick].x, candidates[pick].z);
    return TRUE;
}

static void ComputeBaseLevelRange(FieldSystem *fieldSystem, enum PhenomenonType type, BOOL isFishing, int *outMinLv, int *outMaxLv)
{
    int minLv = 999;
    int maxLv = 0;
    WildEncounters *encData = MapHeaderData_GetWildEncounters(fieldSystem);

    if (encData != NULL) {
        if (type == PHENOMENON_WATER) {
            if (isFishing) {
                for (int i = 0; i < MAX_WATER_ENCOUNTERS; i++) {
                    if (encData->superRodEncounters.encounters[i].species != 0) {
                        int lo = encData->superRodEncounters.encounters[i].minLevel;
                        int hi = encData->superRodEncounters.encounters[i].maxLevel;
                        if (lo > 0 && lo < minLv) minLv = lo;
                        if (hi > maxLv) maxLv = hi;
                    }
                }
            } else {
                for (int i = 0; i < MAX_WATER_ENCOUNTERS; i++) {
                    if (encData->surfEncounters.encounters[i].species != 0) {
                        int lo = encData->surfEncounters.encounters[i].minLevel;
                        int hi = encData->surfEncounters.encounters[i].maxLevel;
                        if (lo > 0 && lo < minLv) minLv = lo;
                        if (hi > maxLv) maxLv = hi;
                    }
                }
            }
        } else {
            for (int i = 0; i < MAX_GRASS_ENCOUNTERS; i++) {
                if (encData->grassEncounters.encounters[i].species != 0) {
                    int lv = encData->grassEncounters.encounters[i].level;
                    if (lv > 0 && lv < minLv) minLv = lv;
                    if (lv > maxLv) maxLv = lv;
                }
            }
        }
    }

    if (minLv > maxLv || maxLv == 0) {
        minLv = 15;
        maxLv = 25;
    }

    *outMinLv = minLv;
    *outMaxLv = maxLv;
}

static BOOL IsNightTime(void)
{
    int tod = GetTimeOfDay();
    return (tod == TIMEOFDAY_NIGHT || tod == TIMEOFDAY_LATE_NIGHT);
}

static FieldBattleDTO *BuildPhenomenonBattleDTO(FieldSystem *fieldSystem, enum PhenomenonType type, BOOL isFishing)
{
    int baseMinLv = 15;
    int baseMaxLv = 25;
    ComputeBaseLevelRange(fieldSystem, type, isFishing, &baseMinLv, &baseMaxLv);

    int playerX = PlayerAvatar_GetXPos(fieldSystem->playerAvatar);
    int playerZ = PlayerAvatar_GetZPos(fieldSystem->playerAvatar);
    u16 species = 0;
    u8 level = (u8)baseMinLv;

    if (!PhenomenaTables_RollEncounter(fieldSystem->location->mapHeaderID, type, isFishing, IsNightTime(), playerX, playerZ, baseMinLv, baseMaxLv, &species, &level)) {
        return NULL;
    }
    if (species == 0) {
        return NULL;
    }

    FieldBattleDTO *dto = FieldBattleDTO_New(HEAP_ID_FIELD2, BATTLE_TYPE_WILD_MON);
    if (dto == NULL) {
        return NULL;
    }
    FieldBattleDTO_Init(dto, fieldSystem);
    if (type == PHENOMENON_WATER) {
        FieldBattleDTO_SetWaterTerrain(dto);
    }
    CreateWildMon_Scripted(fieldSystem, species, level, dto);
    return dto;
}

void FieldPhenomena_Clear(void)
{
    sPhenomena.active = FALSE;
    sPhenomena.type = PHENOMENON_NONE;
    sPhenomena.mapHeaderID = 0;
    sPhenomena.tileX = 0;
    sPhenomena.tileZ = 0;
    sPhenomena.sfxCooldown = 0;
    sPhenomena.animFrame = 0;
    sPhenomena.worldX = 0;
    sPhenomena.worldY = 0;
    sPhenomena.worldZ = 0;
}

void FieldPhenomena_OnFieldInit(FieldSystem *fieldSystem)
{
    (void)fieldSystem;
    memset(&sPhenomena, 0, sizeof(sPhenomena));
}

void FieldPhenomena_OnFieldExit(FieldSystem *fieldSystem)
{
    (void)fieldSystem;
    memset(&sPhenomena, 0, sizeof(sPhenomena));
}

void FieldPhenomena_OnZoneChange(FieldSystem *fieldSystem)
{
    (void)fieldSystem;
    FieldPhenomena_Clear();
}

void FieldPhenomena_OnBattleStart(FieldSystem *fieldSystem)
{
    (void)fieldSystem;
    memset(&sPhenomena, 0, sizeof(sPhenomena));
}

void FieldPhenomena_OnPlayerStep(FieldSystem *fieldSystem)
{
    if (!IsPhenomenaAllowed(fieldSystem)) {
        if (sPhenomena.active) {
            FieldPhenomena_Clear();
        }
        return;
    }

    int mapHeaderID = fieldSystem->location->mapHeaderID;
    int playerX = PlayerAvatar_GetXPos(fieldSystem->playerAvatar);
    int playerZ = PlayerAvatar_GetZPos(fieldSystem->playerAvatar);

    if (sPhenomena.active) {
        if (sPhenomena.mapHeaderID != mapHeaderID
            || AbsInt(playerX - sPhenomena.tileX) > PHENOMENA_MAX_PLAYER_DIST
            || AbsInt(playerZ - sPhenomena.tileZ) > PHENOMENA_MAX_PLAYER_DIST) {
            FieldPhenomena_Clear();
        }
        return;
    }

    sPhenomena.stepCounter++;

    BOOL onCyclingDeck = IsCyclingRoadDeckTile(fieldSystem, mapHeaderID, playerX, playerZ);
    if (onCyclingDeck) {
        if (sPhenomena.stepCounter >= 5) {
            sPhenomena.stepCounter = 0;
            if ((LCRNG_Next() % 100) < 15) {
                TrySpawnRandomPhenomenon(fieldSystem);
            }
        }
    } else {
        if (sPhenomena.stepCounter >= 20) {
            sPhenomena.stepCounter = 0;
            if ((LCRNG_Next() % 10) == 0) {
                TrySpawnRandomPhenomenon(fieldSystem);
            }
        }
    }
}

void FieldPhenomena_Update(FieldSystem *fieldSystem)
{
    if (!sPhenomena.active || fieldSystem == NULL || fieldSystem->playerAvatar == NULL || fieldSystem->location == NULL) {
        return;
    }
    if (!SIM_Config_prj_PhenomenaEnabled() || sPhenomena.mapHeaderID != fieldSystem->location->mapHeaderID) {
        FieldPhenomena_Clear();
        return;
    }

    sPhenomena.animFrame++;

    int playerX = PlayerAvatar_GetXPos(fieldSystem->playerAvatar);
    int playerZ = PlayerAvatar_GetZPos(fieldSystem->playerAvatar);
    int dx = AbsInt(playerX - sPhenomena.tileX);
    int dz = AbsInt(playerZ - sPhenomena.tileZ);
    int dist = dx > dz ? dx : dz;

    if (sPhenomena.sfxCooldown > 0) {
        sPhenomena.sfxCooldown--;
    } else if (dist <= PHENOMENA_SFX_MAX_DIST) {
        sPhenomena.sfxCooldown = PHENOMENA_SFX_COOLDOWN;
        switch (sPhenomena.type) {
        case PHENOMENON_GRASS:
            Sound_PlayEffect(SEQ_SE_DP_FW230_sseq);
            break;
        case PHENOMENON_DUST:
            Sound_PlayEffect(SEQ_SE_DP_UG_023_sseq);
            break;
        case PHENOMENON_WATER:
            Sound_PlayEffect(SEQ_SE_DP_FW104_sseq);
            break;
        case PHENOMENON_SHADOW:
            Sound_PlayEffect(SEQ_SE_PL_JUMP2_sseq);
            break;
        default:
            break;
        }
    }
}

static void DrawQuadXZ(fx16 x0, fx16 z0, fx16 x1, fx16 z1, fx16 y)
{
    G3_Vtx(x0, y, z0);
    G3_Vtx(x1, y, z0);
    G3_Vtx(x1, y, z1);
    G3_Vtx(x0, y, z1);
}

static void DrawVerticalBlade(fx16 cx, fx16 cz, fx16 halfW, fx16 baseY, fx16 topY, fx16 tiltX, fx16 tiltZ)
{
    G3_Vtx((fx16)(cx - halfW), baseY, cz);
    G3_Vtx((fx16)(cx + halfW), baseY, cz);
    G3_Vtx((fx16)(cx + halfW + tiltX), topY, (fx16)(cz + tiltZ));
    G3_Vtx((fx16)(cx - halfW + tiltX), topY, (fx16)(cz + tiltZ));
}

void FieldPhenomena_Draw(FieldSystem *fieldSystem)
{
    if (!sPhenomena.active || fieldSystem == NULL || fieldSystem->location == NULL) {
        return;
    }
    if (!SIM_Config_prj_PhenomenaEnabled() || sPhenomena.mapHeaderID != fieldSystem->location->mapHeaderID) {
        return;
    }

    u16 angle = (u16)((sPhenomena.animFrame * 1400) & 0xFFFF);
    fx32 sinVal = FX_SinIdx(angle);
    fx32 cosVal = FX_CosIdx(angle);
    u16 angle2 = (u16)(((sPhenomena.animFrame + 24) * 1400) & 0xFFFF);
    fx32 sinVal2 = FX_SinIdx(angle2);

    NNS_G3dGlbFlush();

    G3_MtxMode(GX_MTXMODE_POSITION_VECTOR);
    G3_PushMtx();
    G3_Translate(sPhenomena.worldX, sPhenomena.worldY, sPhenomena.worldZ);
    G3_Scale(FX32_ONE * 8, FX32_ONE * 8, FX32_ONE * 8);

    G3_TexImageParam(GX_TEXFMT_NONE, GX_TEXGEN_NONE, GX_TEXSIZE_S8, GX_TEXSIZE_T8, GX_TEXREPEAT_NONE, GX_TEXFLIP_NONE, GX_TEXPLTTCOLOR0_USE, 0);

    switch (sPhenomena.type) {
    case PHENOMENON_GRASS: {
        fx16 sway1 = (fx16)((sinVal * 900) >> FX32_SHIFT);
        fx16 sway2 = (fx16)((cosVal * 900) >> FX32_SHIFT);
        fx16 lift = (fx16)(FX32_ONE / 4 + ((AbsInt((int)sinVal) * 600) >> FX32_SHIFT));

        G3_PolygonAttr(GX_LIGHTMASK_NONE, GX_POLYGONMODE_MODULATE, GX_CULL_NONE, 0, 28, 0);
        G3_Begin(GX_BEGIN_QUADS);
        G3_Color(GX_RGB(8, 28, 6));
        DrawVerticalBlade(-FX16_CONST(0.45f), -FX16_CONST(0.30f), FX16_CONST(0.14f), FX16_CONST(0.05f), (fx16)(FX16_CONST(1.10f) + lift), sway1, FX16_CONST(0.10f));
        DrawVerticalBlade(FX16_CONST(0.40f), -FX16_CONST(0.25f), FX16_CONST(0.14f), FX16_CONST(0.05f), (fx16)(FX16_CONST(1.15f) + lift), sway2, -FX16_CONST(0.10f));
        G3_Color(GX_RGB(18, 31, 10));
        DrawVerticalBlade(0, FX16_CONST(0.35f), FX16_CONST(0.16f), FX16_CONST(0.05f), (fx16)(FX16_CONST(1.25f) + lift), (fx16)(-sway1), sway2);
        DrawVerticalBlade(-FX16_CONST(0.20f), FX16_CONST(0.05f), FX16_CONST(0.12f), FX16_CONST(0.05f), (fx16)(FX16_CONST(1.00f) + lift), sway2, sway1);
        G3_Color(GX_RGB(31, 31, 18));
        DrawQuadXZ((fx16)(-FX16_CONST(0.15f) + sway1), (fx16)(-FX16_CONST(0.15f) + sway2), (fx16)(FX16_CONST(0.15f) + sway1), (fx16)(FX16_CONST(0.15f) + sway2), (fx16)(FX16_CONST(1.35f) + lift));
        G3_End();
        break;
    }

    case PHENOMENON_DUST: {
        fx16 ox = (fx16)((sinVal * 900) >> FX32_SHIFT);
        fx16 oz = (fx16)((cosVal * 900) >> FX32_SHIFT);
        fx16 rise1 = (fx16)(FX16_CONST(0.20f) + ((AbsInt((int)sinVal) * 1400) >> FX32_SHIFT));
        fx16 rise2 = (fx16)(FX16_CONST(0.45f) + ((AbsInt((int)sinVal2) * 1600) >> FX32_SHIFT));
        fx16 r = FX16_CONST(0.45f);

        G3_PolygonAttr(GX_LIGHTMASK_NONE, GX_POLYGONMODE_MODULATE, GX_CULL_NONE, 0, 22, 0);
        G3_Begin(GX_BEGIN_QUADS);
        G3_Color(GX_RGB(22, 19, 15));
        DrawQuadXZ((fx16)(ox - r), (fx16)(oz - r), (fx16)(ox + r), (fx16)(oz + r), rise1);
        G3_Color(GX_RGB(26, 24, 20));
        DrawQuadXZ((fx16)(-ox - r), (fx16)(-oz - r), (fx16)(-ox + r), (fx16)(-oz + r), rise2);
        DrawVerticalBlade(ox, oz, FX16_CONST(0.32f), FX16_CONST(0.05f), rise2, (fx16)(-ox), (fx16)(-oz));
        G3_End();
        break;
    }

    case PHENOMENON_WATER: {
        fx16 phase1 = (fx16)((sPhenomena.animFrame % 30) * (FX32_ONE / 30));
        fx16 phase2 = (fx16)(((sPhenomena.animFrame + 15) % 30) * (FX32_ONE / 30));
        fx16 r1 = (fx16)(FX16_CONST(0.25f) + ((phase1 * 3) >> 2));
        fx16 r2 = (fx16)(FX16_CONST(0.25f) + ((phase2 * 3) >> 2));

        G3_PolygonAttr(GX_LIGHTMASK_NONE, GX_POLYGONMODE_MODULATE, GX_CULL_NONE, 0, 24, 0);
        G3_Begin(GX_BEGIN_QUADS);
        G3_Color(GX_RGB(16, 28, 31));
        DrawQuadXZ(-r1, -r1, r1, r1, FX16_CONST(0.12f));
        G3_Color(GX_RGB(28, 31, 31));
        DrawQuadXZ(-r2, -r2, r2, r2, FX16_CONST(0.18f));
        DrawVerticalBlade(0, 0, FX16_CONST(0.10f), FX16_CONST(0.15f), (fx16)(FX16_CONST(0.55f) + ((AbsInt((int)sinVal) * 800) >> FX32_SHIFT)), (fx16)((sinVal * 400) >> FX32_SHIFT), 0);
        G3_End();
        break;
    }

    case PHENOMENON_SHADOW: {
        fx16 swoopX = (fx16)((sinVal * 1100) >> FX32_SHIFT);
        fx16 swoopZ = (fx16)((cosVal * 600) >> FX32_SHIFT);
        fx16 wing = (fx16)(FX16_CONST(0.65f) + ((AbsInt((int)sinVal2) * 900) >> FX32_SHIFT));

        G3_PolygonAttr(GX_LIGHTMASK_NONE, GX_POLYGONMODE_MODULATE, GX_CULL_NONE, 0, 22, 0);
        G3_Begin(GX_BEGIN_QUADS);
        G3_Color(GX_RGB(4, 3, 7));
        DrawQuadXZ((fx16)(swoopX - FX16_CONST(0.45f)), (fx16)(swoopZ - FX16_CONST(0.45f)), (fx16)(swoopX + FX16_CONST(0.45f)), (fx16)(swoopZ + FX16_CONST(0.45f)), FX16_CONST(0.12f));
        DrawQuadXZ((fx16)(swoopX - wing), (fx16)(swoopZ - FX16_CONST(0.18f)), (fx16)(swoopX + wing), (fx16)(swoopZ + FX16_CONST(0.18f)), FX16_CONST(0.14f));
        G3_End();
        break;
    }

    default:
        break;
    }

    G3_PopMtx(1);
    G3_Color(GX_RGB(31, 31, 31));
}

int FieldPhenomena_CheckStepTrigger(FieldSystem *fieldSystem)
{
    if (!sPhenomena.active || fieldSystem == NULL || fieldSystem->location == NULL || fieldSystem->playerAvatar == NULL) {
        return 0;
    }
    if (!SIM_Config_prj_PhenomenaEnabled()) {
        return 0;
    }
    if (sPhenomena.mapHeaderID != fieldSystem->location->mapHeaderID) {
        return 0;
    }

    int playerX = PlayerAvatar_GetXPos(fieldSystem->playerAvatar);
    int playerZ = PlayerAvatar_GetZPos(fieldSystem->playerAvatar);
    if (playerX != sPhenomena.tileX || playerZ != sPhenomena.tileZ) {
        return 0;
    }

    enum PhenomenonType type = sPhenomena.type;
    int mapHeaderID = sPhenomena.mapHeaderID;
    FieldPhenomena_Clear();

    BOOL doBattle = TRUE;
    if (type == PHENOMENON_DUST) {
        doBattle = ((LCRNG_Next() % 100) < 40);
    } else if (type == PHENOMENON_SHADOW) {
        doBattle = ((LCRNG_Next() % 100) < 20);
    }

    if (doBattle) {
        FieldBattleDTO *dto = BuildPhenomenonBattleDTO(fieldSystem, type, FALSE);
        if (dto != NULL) {
            Encounter_NewVsWild(fieldSystem, dto);
            return 1;
        }
        return 0;
    }

    u16 itemID = PhenomenaTables_RollItem(type, mapHeaderID);
    if (itemID != 0 && fieldSystem->saveData != NULL) {
        Bag_TryAddItem(SaveData_GetBag(fieldSystem->saveData), itemID, 1, HEAP_ID_FIELD1);
        Sound_PlayEffect(SEQ_SE_DP_DECIDE_sseq);
    }
    return -1;
}

BOOL FieldPhenomena_TrySuperRodEncounter(FieldSystem *fieldSystem, enum EncounterFishingRodType rodType, FieldBattleDTO **battleParams)
{
    if (rodType != FISHING_TYPE_SUPER_ROD || battleParams == NULL) {
        return FALSE;
    }
    if (!sPhenomena.active || sPhenomena.type != PHENOMENON_WATER) {
        return FALSE;
    }
    if (!SIM_Config_prj_PhenomenaEnabled() || fieldSystem == NULL || fieldSystem->location == NULL || fieldSystem->playerAvatar == NULL) {
        return FALSE;
    }
    if (sPhenomena.mapHeaderID != fieldSystem->location->mapHeaderID) {
        return FALSE;
    }

    int targetX = PlayerAvatar_GetXPos(fieldSystem->playerAvatar);
    int targetZ = PlayerAvatar_GetZPos(fieldSystem->playerAvatar);
    int dir = PlayerAvatar_GetFacingDir(fieldSystem->playerAvatar);
    switch (dir) {
    case DIR_NORTH:
        targetZ -= 1;
        break;
    case DIR_SOUTH:
        targetZ += 1;
        break;
    case DIR_WEST:
        targetX -= 1;
        break;
    case DIR_EAST:
        targetX += 1;
        break;
    default:
        return FALSE;
    }

    if (targetX != sPhenomena.tileX || targetZ != sPhenomena.tileZ) {
        return FALSE;
    }

    FieldPhenomena_Clear();
    FieldBattleDTO *dto = BuildPhenomenonBattleDTO(fieldSystem, PHENOMENON_WATER, TRUE);
    if (dto == NULL) {
        return FALSE;
    }
    *battleParams = dto;
    return TRUE;
}

BOOL FieldPhenomena_DebugForceSpawn(FieldSystem *fieldSystem, enum PhenomenonType type, BOOL hasCoords, int tileX, int tileZ)
{
    if (fieldSystem == NULL || fieldSystem->location == NULL || fieldSystem->playerAvatar == NULL) {
        return FALSE;
    }
    if (type < PHENOMENON_GRASS || type > PHENOMENON_SHADOW) {
        return FALSE;
    }

    int mapHeaderID = fieldSystem->location->mapHeaderID;
    int tx = tileX;
    int tz = tileZ;

    if (!hasCoords) {
        int playerX = PlayerAvatar_GetXPos(fieldSystem->playerAvatar);
        int playerZ = PlayerAvatar_GetZPos(fieldSystem->playerAvatar);
        BOOL found = FALSE;
        for (int dist = 1; dist <= PHENOMENA_SCAN_MAX_DIST && !found; dist++) {
            for (int dz = -dist; dz <= dist && !found; dz++) {
                for (int dx = -dist; dx <= dist && !found; dx++) {
                    if (dx == 0 && dz == 0) {
                        continue;
                    }
                    int cx = playerX + dx;
                    int cz = playerZ + dz;
                    if (IsTileValidForPhenomenon(fieldSystem, mapHeaderID, cx, cz, type)) {
                        tx = cx;
                        tz = cz;
                        found = TRUE;
                    }
                }
            }
        }
        if (!found) {
            int dir = PlayerAvatar_GetFacingDir(fieldSystem->playerAvatar);
            tx = playerX + (dir == DIR_EAST ? 2 : (dir == DIR_WEST ? -2 : 0));
            tz = playerZ + (dir == DIR_SOUTH ? 2 : (dir == DIR_NORTH ? -2 : 0));
        }
    }

    ActivatePhenomenon(fieldSystem, type, mapHeaderID, tx, tz);
    return TRUE;
}

void FieldPhenomena_GetState(BOOL *outActive, enum PhenomenonType *outType, int *outMapHeaderID, int *outTileX, int *outTileZ, int *outStepCounter)
{
    if (outActive) {
        *outActive = sPhenomena.active;
    }
    if (outType) {
        *outType = sPhenomena.type;
    }
    if (outMapHeaderID) {
        *outMapHeaderID = sPhenomena.mapHeaderID;
    }
    if (outTileX) {
        *outTileX = sPhenomena.tileX;
    }
    if (outTileZ) {
        *outTileZ = sPhenomena.tileZ;
    }
    if (outStepCounter) {
        *outStepCounter = sPhenomena.stepCounter;
    }
}
