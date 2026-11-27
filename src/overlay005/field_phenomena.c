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

static void DrawDiscXZ(fx16 cx, fx16 cz, fx16 rx, fx16 rz, fx16 y, int segs)
{
    G3_Begin(GX_BEGIN_TRIANGLES);
    for (int i = 0; i < segs; i++) {
        u16 a0 = (u16)((i * 65536) / segs);
        u16 a1 = (u16)(((i + 1) * 65536) / segs);
        fx16 x0 = (fx16)(cx + ((FX_CosIdx(a0) * rx) >> FX32_SHIFT));
        fx16 z0 = (fx16)(cz + ((FX_SinIdx(a0) * rz) >> FX32_SHIFT));
        fx16 x1 = (fx16)(cx + ((FX_CosIdx(a1) * rx) >> FX32_SHIFT));
        fx16 z1 = (fx16)(cz + ((FX_SinIdx(a1) * rz) >> FX32_SHIFT));
        G3_Vtx(cx, y, cz);
        G3_Vtx(x0, y, z0);
        G3_Vtx(x1, y, z1);
    }
    G3_End();
}

static void DrawRingXZ(fx16 cx, fx16 cz, fx16 rInner, fx16 rOuter, fx16 y, int segs)
{
    G3_Begin(GX_BEGIN_QUADS);
    for (int i = 0; i < segs; i++) {
        u16 a0 = (u16)((i * 65536) / segs);
        u16 a1 = (u16)(((i + 1) * 65536) / segs);
        fx32 c0 = FX_CosIdx(a0);
        fx32 s0 = FX_SinIdx(a0);
        fx32 c1 = FX_CosIdx(a1);
        fx32 s1 = FX_SinIdx(a1);
        G3_Vtx((fx16)(cx + ((c0 * rInner) >> FX32_SHIFT)), y, (fx16)(cz + ((s0 * rInner) >> FX32_SHIFT)));
        G3_Vtx((fx16)(cx + ((c0 * rOuter) >> FX32_SHIFT)), y, (fx16)(cz + ((s0 * rOuter) >> FX32_SHIFT)));
        G3_Vtx((fx16)(cx + ((c1 * rOuter) >> FX32_SHIFT)), y, (fx16)(cz + ((s1 * rOuter) >> FX32_SHIFT)));
        G3_Vtx((fx16)(cx + ((c1 * rInner) >> FX32_SHIFT)), y, (fx16)(cz + ((s1 * rInner) >> FX32_SHIFT)));
    }
    G3_End();
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
    fx32 cosVal2 = FX_CosIdx(angle2);

    G3_MtxMode(GX_MTXMODE_PROJECTION);
    G3_LoadMtx44(NNS_G3dGlbGetProjectionMtx());

    G3_MtxMode(GX_MTXMODE_POSITION_VECTOR);
    G3_PushMtx();
    G3_LoadMtx43(NNS_G3dGlbGetCameraMtx());
    G3_Translate(sPhenomena.worldX, sPhenomena.worldY, sPhenomena.worldZ);
    G3_Scale(FX32_ONE * 8, FX32_ONE * 8, FX32_ONE * 8);

    G3_TexImageParam(GX_TEXFMT_NONE, GX_TEXGEN_NONE, GX_TEXSIZE_S8, GX_TEXSIZE_T8, GX_TEXREPEAT_NONE, GX_TEXFLIP_NONE, GX_TEXPLTTCOLOR0_USE, 0);
    G3_MaterialColorDiffAmb(GX_RGB(31, 31, 31), GX_RGB(31, 31, 31), FALSE);
    G3_MaterialColorSpecEmi(GX_RGB(0, 0, 0), GX_RGB(0, 0, 0), FALSE);

    switch (sPhenomena.type) {
    case PHENOMENON_GRASS: {
        // BW2-style vigorous rustling grass tuft + fluttering leaf particles
        fx16 sway1 = (fx16)((sinVal * 1500) >> FX32_SHIFT);
        fx16 sway2 = (fx16)((cosVal * 1500) >> FX32_SHIFT);
        fx16 lift = (fx16)(FX16_CONST(0.25f) + ((AbsInt((int)sinVal) * 1100) >> FX32_SHIFT));
        fx16 leafY1 = (fx16)(FX16_CONST(0.95f) + (((sPhenomena.animFrame % 24) * 120)));
        fx16 leafY2 = (fx16)(FX16_CONST(0.85f) + ((((sPhenomena.animFrame + 12) % 24) * 120)));

        // Subtle dark base shadow under shaking patch
        G3_PolygonAttr(GX_LIGHTMASK_NONE, GX_POLYGONMODE_MODULATE, GX_CULL_NONE, 0, 14, 0);
        G3_Color(GX_RGB(3, 10, 3));
        DrawDiscXZ(0, 0, FX16_CONST(0.95f), FX16_CONST(0.75f), FX16_CONST(0.06f), 10);

        // Rich multi-blade shaking grass cluster (back dark green + front bright lime blades)
        G3_PolygonAttr(GX_LIGHTMASK_NONE, GX_POLYGONMODE_MODULATE, GX_CULL_NONE, 0, 31, 0);
        G3_Begin(GX_BEGIN_QUADS);
        G3_Color(GX_RGB(4, 17, 4));
        DrawVerticalBlade(-FX16_CONST(0.65f), -FX16_CONST(0.35f), FX16_CONST(0.22f), FX16_CONST(0.08f), (fx16)(FX16_CONST(1.30f) + lift), (fx16)(-FX16_CONST(0.25f) + sway1), FX16_CONST(0.10f));
        DrawVerticalBlade(FX16_CONST(0.60f), -FX16_CONST(0.30f), FX16_CONST(0.22f), FX16_CONST(0.08f), (fx16)(FX16_CONST(1.35f) + lift), (fx16)(FX16_CONST(0.25f) + sway2), -FX16_CONST(0.10f));
        DrawVerticalBlade(0, -FX16_CONST(0.45f), FX16_CONST(0.24f), FX16_CONST(0.08f), (fx16)(FX16_CONST(1.50f) + lift), sway1, FX16_CONST(0.12f));

        G3_Color(GX_RGB(12, 27, 7));
        DrawVerticalBlade(-FX16_CONST(0.40f), FX16_CONST(0.15f), FX16_CONST(0.22f), FX16_CONST(0.08f), (fx16)(FX16_CONST(1.25f) + lift), (fx16)(-sway2), sway1);
        DrawVerticalBlade(FX16_CONST(0.40f), FX16_CONST(0.20f), FX16_CONST(0.22f), FX16_CONST(0.08f), (fx16)(FX16_CONST(1.25f) + lift), sway1, -sway2);

        G3_Color(GX_RGB(21, 31, 11));
        DrawVerticalBlade(0, FX16_CONST(0.35f), FX16_CONST(0.20f), FX16_CONST(0.10f), (fx16)(FX16_CONST(1.35f) + lift), (fx16)(-sway1), sway2);

        // Two leaping leaf flecks popping out of the rustling grass
        G3_Color(GX_RGB(25, 31, 12));
        DrawQuadXZ((fx16)(-FX16_CONST(0.55f) + sway1), (fx16)(-FX16_CONST(0.15f) + sway2), (fx16)(-FX16_CONST(0.22f) + sway1), (fx16)(FX16_CONST(0.15f) + sway2), leafY1);
        DrawQuadXZ((fx16)(FX16_CONST(0.22f) - sway2), (fx16)(-FX16_CONST(0.20f) - sway1), (fx16)(FX16_CONST(0.55f) - sway2), (fx16)(FX16_CONST(0.10f) - sway1), leafY2);
        G3_End();
        break;
    }

    case PHENOMENON_DUST: {
        // BW2-style swirling multi-puff cave dust cloud (layered soft circular puffs)
        fx16 ox = (fx16)((sinVal * 1500) >> FX32_SHIFT);
        fx16 oz = (fx16)((cosVal * 1300) >> FX32_SHIFT);
        fx16 ox2 = (fx16)((cosVal2 * 1400) >> FX32_SHIFT);
        fx16 oz2 = (fx16)((sinVal2 * 1200) >> FX32_SHIFT);
        fx16 rBase = (fx16)(FX16_CONST(0.70f) + ((AbsInt((int)sinVal) * 700) >> FX32_SHIFT));
        fx16 rTop = (fx16)(FX16_CONST(0.55f) + ((AbsInt((int)cosVal) * 600) >> FX32_SHIFT));
        fx16 rise1 = (fx16)(FX16_CONST(0.30f) + ((AbsInt((int)sinVal) * 1400) >> FX32_SHIFT));
        fx16 rise2 = (fx16)(FX16_CONST(0.65f) + ((AbsInt((int)sinVal2) * 1500) >> FX32_SHIFT));

        // Ground shadow ring
        G3_PolygonAttr(GX_LIGHTMASK_NONE, GX_POLYGONMODE_MODULATE, GX_CULL_NONE, 0, 16, 0);
        G3_Color(GX_RGB(10, 8, 6));
        DrawDiscXZ(0, 0, FX16_CONST(1.05f), FX16_CONST(0.90f), FX16_CONST(0.06f), 12);

        // Swirling billowing dust puffs
        G3_PolygonAttr(GX_LIGHTMASK_NONE, GX_POLYGONMODE_MODULATE, GX_CULL_NONE, 0, 25, 0);
        G3_Color(GX_RGB(21, 18, 14));
        DrawDiscXZ(ox, oz, rBase, rBase, rise1, 10);
        DrawDiscXZ((fx16)(-ox), (fx16)(-oz), (fx16)(rBase - FX16_CONST(0.10f)), (fx16)(rBase - FX16_CONST(0.10f)), (fx16)(rise1 + FX16_CONST(0.18f)), 10);

        G3_PolygonAttr(GX_LIGHTMASK_NONE, GX_POLYGONMODE_MODULATE, GX_CULL_NONE, 0, 27, 0);
        G3_Color(GX_RGB(27, 25, 21));
        DrawDiscXZ(ox2, oz2, rTop, rTop, rise2, 10);
        DrawDiscXZ((fx16)(-ox2 / 2), (fx16)(-oz2 / 2), (fx16)(rTop * 4 / 5), (fx16)(rTop * 4 / 5), (fx16)(rise2 + FX16_CONST(0.25f)), 10);
        break;
    }

    case PHENOMENON_WATER: {
        // BW2-style hollow concentric rippling water rings + dark center swirl + splash droplet
        int p1 = sPhenomena.animFrame % 36;
        int p2 = (sPhenomena.animFrame + 18) % 36;
        fx16 r1Outer = (fx16)(FX16_CONST(0.32f) + ((p1 * FX16_CONST(0.85f)) / 36));
        fx16 r1Inner = (fx16)(r1Outer > FX16_CONST(0.16f) ? r1Outer - FX16_CONST(0.16f) : 0);
        fx16 r2Outer = (fx16)(FX16_CONST(0.32f) + ((p2 * FX16_CONST(0.85f)) / 36));
        fx16 r2Inner = (fx16)(r2Outer > FX16_CONST(0.16f) ? r2Outer - FX16_CONST(0.16f) : 0);
        int a1 = 29 - (p1 * 18) / 36;
        int a2 = 29 - (p2 * 18) / 36;

        // Subtle dark water depression in the center
        G3_PolygonAttr(GX_LIGHTMASK_NONE, GX_POLYGONMODE_MODULATE, GX_CULL_NONE, 0, 18, 0);
        G3_Color(GX_RGB(4, 12, 22));
        DrawDiscXZ(0, 0, FX16_CONST(0.42f), FX16_CONST(0.36f), FX16_CONST(0.08f), 12);

        // Two expanding hollow white/cyan foam ripple rings
        G3_PolygonAttr(GX_LIGHTMASK_NONE, GX_POLYGONMODE_MODULATE, GX_CULL_NONE, 0, a1, 0);
        G3_Color(GX_RGB(28, 31, 31));
        DrawRingXZ(0, 0, r1Inner, r1Outer, FX16_CONST(0.14f), 14);

        G3_PolygonAttr(GX_LIGHTMASK_NONE, GX_POLYGONMODE_MODULATE, GX_CULL_NONE, 0, a2, 0);
        G3_Color(GX_RGB(19, 29, 31));
        DrawRingXZ(0, 0, r2Inner, r2Outer, FX16_CONST(0.16f), 14);

        // Tiny center splash jet
        G3_PolygonAttr(GX_LIGHTMASK_NONE, GX_POLYGONMODE_MODULATE, GX_CULL_NONE, 0, 28, 0);
        G3_Begin(GX_BEGIN_QUADS);
        G3_Color(GX_RGB(30, 31, 31));
        DrawVerticalBlade(0, 0, FX16_CONST(0.12f), FX16_CONST(0.14f), (fx16)(FX16_CONST(0.65f) + ((AbsInt((int)sinVal) * 900) >> FX32_SHIFT)), (fx16)((sinVal * 400) >> FX32_SHIFT), 0);
        G3_End();
        break;
    }

    case PHENOMENON_SHADOW: {
        // BW2-style smooth dark circular bird shadow pulsing/swooping across the Cycling Road deck
        fx16 swoopX = (fx16)((sinVal * 900) >> FX32_SHIFT);
        fx16 swoopZ = (fx16)((cosVal * 600) >> FX32_SHIFT);
        fx16 pulse = (fx16)(FX16_CONST(0.75f) + ((AbsInt((int)sinVal2) * 1100) >> FX32_SHIFT));

        // Soft outer penumbra + darker crisp core oval
        G3_PolygonAttr(GX_LIGHTMASK_NONE, GX_POLYGONMODE_MODULATE, GX_CULL_NONE, 0, 12, 0);
        G3_Color(GX_RGB(3, 3, 6));
        DrawDiscXZ(swoopX, swoopZ, (fx16)(pulse + FX16_CONST(0.24f)), (fx16)(pulse + FX16_CONST(0.12f)), FX16_CONST(0.10f), 14);

        G3_PolygonAttr(GX_LIGHTMASK_NONE, GX_POLYGONMODE_MODULATE, GX_CULL_NONE, 0, 22, 0);
        G3_Color(GX_RGB(2, 2, 5));
        DrawDiscXZ(swoopX, swoopZ, pulse, (fx16)(pulse * 4 / 5), FX16_CONST(0.12f), 14);
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
