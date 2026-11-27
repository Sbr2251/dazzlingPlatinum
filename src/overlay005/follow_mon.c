#include "overlay005/follow_mon.h"

#include <nitro.h>
#include <nnsys.h>
#include <stdio.h>
#include <string.h>

#include "constants/field/dynamic_map_features.h"
#include "constants/field/map.h"
#include "constants/field/map_load.h"
#include "constants/fieldmap.h"
#include "constants/heap.h"
#include "constants/map_object.h"
#include "constants/player_avatar.h"
#include "constants/pokemon.h"
#include "constants/species.h"
#include "generated/movement_types.h"

#include "field/field_system.h"
#include "overlay005/area_light.h"
#include "overlay005/follow_mon_archive.h"
#include "overlay005/object_event_gfx_data.h"
#include "overlay005/ov5_021ECC20.h"
#include "overlay005/ov5_021ECE40.h"
#include "overlay005/resource_heap.h"
#include "port/sim_config_prj.h"

#include "billboard.h"
#include "billboard_gfx_sequence.h"
#include "heap.h"
#include "map_header.h"
#include "map_header_data.h"
#include "map_object.h"
#include "map_object_move.h"
#include "party.h"
#include "persisted_map_features_init.h"
#include "player_avatar.h"
#include "pokemon.h"
#include "savedata.h"
#include "sound_playback.h"
#include "system_flags.h"
#include "terrain_collision_manager.h"
#include "vars_flags.h"

typedef struct FollowMonArchive {
    BOOL probed;
    BOOL available;
    BOOL useStdio;
    FSFile fsFile;
    FILE *stdioFile;
    u32 fatbStart;
    u32 fimgStart;
    u16 numFiles;
} FollowMonArchive;

typedef struct FollowMonRenderData {
    Billboard *billboard;
    s8 lastDir;
    u8 reserved[3];
} FollowMonRenderData;

typedef struct FollowMonState {
    FollowMonArchive archive;
    BOOL fieldActive;
    BOOL active;
    BOOL hidden;
    BOOL waitingForStepToEmerge;
    BOOL retractOnNextInit;
    int partySlot;
    int species;
    int form;
    int gender;
    BOOL isShiny;
    BOOL isLarge;
    int tileX;
    int tileZ;
    int dir;
    int mood;
    u32 stepCounter;
    u8 shinyLeaves[MAX_PARTY_SIZE];

    // Smooth interpolation state
    BOOL moving;
    BOOL hopping;
    int moveFrame;
    int moveDuration;
    int moveSpeed;
    int targetX;
    int targetZ;
    int targetDir;
    VecFx32 startPos;
    VecFx32 endPos;

    // External talk hop vertical offset
    fx32 talkJumpY;

    // Live FieldMap / Billboard resources (allocated in HEAP_ID_FIELD1)
    MapObject *mapObj;
    Billboard *billboard;
    void *btxBuf;
    void *seqBuf;
    void *modelBuf;
    BillboardGfxSequence gfxSequence;
    BillboardAnim anims[5];
} FollowMonState;

static FollowMonState sFollowMon;

// ---------------------------------------------------------------------------
// Minimal NARC reader (supports FS_OpenFile and stdio fopen fallback)
// ---------------------------------------------------------------------------

static BOOL ArchiveReadExact(FollowMonArchive *arc, u32 offset, void *dst, u32 size)
{
    if (arc->useStdio) {
        if (arc->stdioFile == NULL) {
            return FALSE;
        }
        if (fseek(arc->stdioFile, (long)offset, SEEK_SET) != 0) {
            return FALSE;
        }
        return fread(dst, 1, size, arc->stdioFile) == size ? TRUE : FALSE;
    }

    if (!FS_SeekFile(&arc->fsFile, (s32)offset, FS_SEEK_SET)) {
        return FALSE;
    }
    return FS_ReadFile(&arc->fsFile, dst, (s32)size) == (s32)size ? TRUE : FALSE;
}

static BOOL ArchiveParseHeader(FollowMonArchive *arc)
{
    u8 hdr[16] = { 0 };
    u8 btaf[12] = { 0 };
    u8 btnf[8] = { 0 };
    u16 headerSize = 0;
    u32 btafSize = 0;
    u32 btnfSize = 0;
    u16 fileCount = 0;

    if (!ArchiveReadExact(arc, 0, hdr, sizeof(hdr))) {
        return FALSE;
    }
    if (memcmp(hdr, "NARC", 4) != 0) {
        return FALSE;
    }

    headerSize = (u16)(hdr[12] | ((u16)hdr[13] << 8));
    if (headerSize < 16) {
        return FALSE;
    }

    if (!ArchiveReadExact(arc, headerSize, btaf, sizeof(btaf))) {
        return FALSE;
    }
    if (memcmp(btaf, "BTAF", 4) != 0) {
        return FALSE;
    }

    btafSize = (u32)btaf[4] | ((u32)btaf[5] << 8) | ((u32)btaf[6] << 16) | ((u32)btaf[7] << 24);
    fileCount = (u16)(btaf[8] | ((u16)btaf[9] << 8));
    if (fileCount == 0 || btafSize < 12) {
        return FALSE;
    }

    u32 btnfStart = (u32)headerSize + btafSize;
    if (!ArchiveReadExact(arc, btnfStart, btnf, sizeof(btnf))) {
        return FALSE;
    }
    if (memcmp(btnf, "BTNF", 4) != 0) {
        return FALSE;
    }

    btnfSize = (u32)btnf[4] | ((u32)btnf[5] << 8) | ((u32)btnf[6] << 16) | ((u32)btnf[7] << 24);
    arc->fatbStart = headerSize;
    arc->fimgStart = btnfStart + btnfSize;
    arc->numFiles = fileCount;
    return TRUE;
}

static BOOL FollowMon_EnsureArchiveLoaded(void)
{
    FollowMonArchive *arc = &sFollowMon.archive;
    if (arc->probed) {
        return arc->available;
    }
    arc->probed = TRUE;
    arc->available = FALSE;
    arc->useStdio = FALSE;
    arc->stdioFile = NULL;

    static const char *const kPaths[] = {
        "follow_mon.narc",
        "gen5/follow_mon.narc",
        "data/follow_mon.narc",
    };

    for (int i = 0; i < (int)(sizeof(kPaths) / sizeof(kPaths[0])); i++) {
        FS_InitFile(&arc->fsFile);
        if (FS_OpenFile(&arc->fsFile, kPaths[i])) {
            arc->useStdio = FALSE;
            if (ArchiveParseHeader(arc)) {
                arc->available = TRUE;
                return TRUE;
            }
            FS_CloseFile(&arc->fsFile);
        }
    }

    for (int i = 0; i < (int)(sizeof(kPaths) / sizeof(kPaths[0])); i++) {
        FILE *fp = fopen(kPaths[i], "rb");
        if (fp != NULL) {
            arc->useStdio = TRUE;
            arc->stdioFile = fp;
            if (ArchiveParseHeader(arc)) {
                arc->available = TRUE;
                return TRUE;
            }
            fclose(fp);
            arc->stdioFile = NULL;
        }
    }

    arc->available = FALSE;
    return FALSE;
}

int FollowMon_GetArchiveMemberCount(void)
{
    if (!FollowMon_EnsureArchiveLoaded()) {
        return 0;
    }
    return (int)sFollowMon.archive.numFiles;
}

void *FollowMon_ReadArchiveMember(int memberIdx, u32 *outSize)
{
    if (outSize != NULL) {
        *outSize = 0;
    }
    if (!FollowMon_EnsureArchiveLoaded()) {
        return NULL;
    }
    FollowMonArchive *arc = &sFollowMon.archive;
    if (memberIdx < 0 || memberIdx >= (int)arc->numFiles) {
        return NULL;
    }

    u8 entry[8] = { 0 };
    u32 entryOff = arc->fatbStart + 12u + (u32)memberIdx * 8u;
    if (!ArchiveReadExact(arc, entryOff, entry, sizeof(entry))) {
        return NULL;
    }

    u32 fileStart = (u32)entry[0] | ((u32)entry[1] << 8) | ((u32)entry[2] << 16) | ((u32)entry[3] << 24);
    u32 fileEnd = (u32)entry[4] | ((u32)entry[5] << 8) | ((u32)entry[6] << 16) | ((u32)entry[7] << 24);
    if (fileEnd <= fileStart) {
        return NULL;
    }

    u32 size = fileEnd - fileStart;
    void *buf = Heap_AllocAtEnd(HEAP_ID_FIELD1, size);
    if (buf == NULL) {
        return NULL;
    }

    if (!ArchiveReadExact(arc, arc->fimgStart + 8u + fileStart, buf, size)) {
        Heap_Free(buf);
        return NULL;
    }

    if (outSize != NULL) {
        *outSize = size;
    }
    return buf;
}

// ---------------------------------------------------------------------------
// Disabled map & restriction checks
// ---------------------------------------------------------------------------

static BOOL FollowMon_IsDisabledMap(FieldSystem *fieldSystem, enum MapHeaderID mapId)
{
    if (fieldSystem == NULL) {
        return TRUE;
    }

    if (fieldSystem->mapLoadType == MAP_LOAD_TYPE_UNDERGROUND
        || fieldSystem->mapLoadType == MAP_LOAD_TYPE_UNION
        || fieldSystem->mapLoadType == MAP_LOAD_TYPE_COLOSSEUM) {
        return TRUE;
    }

    if (MapHeader_IsUnionRoom(mapId) || MapHeader_IsAmitySquare(mapId)) {
        return TRUE;
    }

    if (PersistedMapFeatures_IsCurrentDynamicMap(fieldSystem, DYNAMIC_MAP_FEATURES_DISTORTION_WORLD)) {
        return TRUE;
    }

    VarsFlags *varsFlags = SaveData_GetVarsFlags(fieldSystem->saveData);
    if (varsFlags != NULL) {
        if (SystemFlag_CheckSafariGameActive(varsFlags) || SystemFlag_CheckInPalPark(varsFlags)) {
            return TRUE;
        }
    }

    switch (mapId) {
    case MAP_HEADER_UNDERGROUND:
    case MAP_HEADER_UNION_ROOM:
    case MAP_HEADER_COMMUNICATION_CLUB_COLOSSEUM_2P:
    case MAP_HEADER_COMMUNICATION_CLUB_COLOSSEUM_4P:
    case MAP_HEADER_GLOBAL_TERMINAL_1F:
    case MAP_HEADER_GLOBAL_TERMINAL_2F:
    case MAP_HEADER_GLOBAL_TERMINAL_3F:
    case MAP_HEADER_AMITY_SQUARE:
    case MAP_HEADER_PASTORIA_CITY_DP_GREAT_MARSH:
    case MAP_HEADER_GREAT_MARSH_1:
    case MAP_HEADER_GREAT_MARSH_2:
    case MAP_HEADER_GREAT_MARSH_3:
    case MAP_HEADER_GREAT_MARSH_4:
    case MAP_HEADER_GREAT_MARSH_5:
    case MAP_HEADER_GREAT_MARSH_6:
    case MAP_HEADER_PAL_PARK:
    case MAP_HEADER_PAL_PARK_LOBBY:
    case MAP_HEADER_BATTLE_FRONTIER:
    case MAP_HEADER_BATTLE_TOWER:
    case MAP_HEADER_BATTLE_TOWER_ELEVATOR:
    case MAP_HEADER_BATTLE_TOWER_CORRIDOR:
    case MAP_HEADER_BATTLE_TOWER_CORRIDOR_MULTI:
    case MAP_HEADER_BATTLE_TOWER_BATTLE_ROOM:
    case MAP_HEADER_BATTLE_TOWER_MULTI_BATTLE_ROOM:
    case MAP_HEADER_BATTLE_TOWER_BATTLE_SALON:
    case MAP_HEADER_BATTLE_FACTORY:
    case MAP_HEADER_BATTLE_HALL:
    case MAP_HEADER_BATTLE_CASTLE:
    case MAP_HEADER_BATTLE_ARCADE:
    case MAP_HEADER_CONTEST_HALL_LOBBY:
    case MAP_HEADER_CONTEST_HALL_STAGE_ONGOING_CONTEST:
    case MAP_HEADER_CONTEST_HALL_STAGE_NO_CONTEST:
    case MAP_HEADER_DISTORTION_WORLD_1F:
    case MAP_HEADER_DISTORTION_WORLD_B1F:
    case MAP_HEADER_DISTORTION_WORLD_B2F:
    case MAP_HEADER_DISTORTION_WORLD_B3F:
    case MAP_HEADER_DISTORTION_WORLD_B4F:
    case MAP_HEADER_DISTORTION_WORLD_B5F:
    case MAP_HEADER_DISTORTION_WORLD_B6F:
    case MAP_HEADER_DISTORTION_WORLD_B7F:
    case MAP_HEADER_DISTORTION_WORLD_GIRATINA_ROOM:
    case MAP_HEADER_DISTORTION_WORLD_TURNBACK_CAVE_ROOM:
    case MAP_HEADER_DISTORTION_WORLD_ARC1_SEAMS:
    case MAP_HEADER_CANALAVE_CITY_GYM:
    case MAP_HEADER_POKEMON_LEAGUE_ELEVATOR_TO_AARON_ROOM:
    case MAP_HEADER_POKEMON_LEAGUE_ELEVATOR_TO_BERTHA_ROOM:
    case MAP_HEADER_POKEMON_LEAGUE_ELEVATOR_TO_FLINT_ROOM:
    case MAP_HEADER_POKEMON_LEAGUE_ELEVATOR_TO_LUCIAN_ROOM:
    case MAP_HEADER_POKEMON_LEAGUE_ELEVATOR_TO_CHAMPION_ROOM:
        return TRUE;
    default:
        break;
    }

    return FALSE;
}

static BOOL FollowMon_ShouldRetract(FieldSystem *fieldSystem, BOOL isLarge)
{
    if (fieldSystem == NULL || fieldSystem->playerAvatar == NULL || fieldSystem->location == NULL) {
        return TRUE;
    }

    enum MapHeaderID mapId = fieldSystem->location->mapHeaderID;
    if (FollowMon_IsDisabledMap(fieldSystem, mapId)) {
        return TRUE;
    }

    int avatarState = PlayerAvatar_GetPlayerState(fieldSystem->playerAvatar);
    if (avatarState == PLAYER_AVATAR_CYCLING
        || avatarState == PLAYER_AVATAR_SURFING
        || avatarState == PLAYER_AVATAR_HEAL
        || avatarState == PLAYER_AVATAR_DISTORTION_WORLD
        || avatarState == PLAYER_AVATAR_DISTORTION_WORLD_SURF) {
        return TRUE;
    }

    VarsFlags *varsFlags = SaveData_GetVarsFlags(fieldSystem->saveData);
    if (varsFlags != NULL && SystemFlag_CheckHasPartner(varsFlags)) {
        return TRUE;
    }

    if (isLarge && !MapHeader_IsOutdoors(mapId) && !MapHeader_IsCave(mapId)) {
        return TRUE;
    }

    return FALSE;
}

// ---------------------------------------------------------------------------
// Party lead resolution
// ---------------------------------------------------------------------------

typedef struct LeadMonInfo {
    BOOL found;
    int slot;
    int species;
    int form;
    int gender;
    BOOL isShiny;
    BOOL isLarge;
} LeadMonInfo;

static LeadMonInfo FollowMon_FindLeadMon(FieldSystem *fieldSystem)
{
    LeadMonInfo info;
    memset(&info, 0, sizeof(info));
    info.slot = -1;

    if (fieldSystem == NULL || fieldSystem->saveData == NULL) {
        return info;
    }

    Party *party = SaveData_GetParty(fieldSystem->saveData);
    if (party == NULL) {
        return info;
    }

    int count = Party_GetCurrentCount(party);
    for (int i = 0; i < count; i++) {
        Pokemon *mon = Party_GetPokemonBySlotIndex(party, i);
        if (mon == NULL) {
            continue;
        }
        u32 isEgg = Pokemon_GetValue(mon, MON_DATA_IS_EGG, NULL);
        u32 hp = Pokemon_GetValue(mon, MON_DATA_HP, NULL);
        u32 species = Pokemon_GetValue(mon, MON_DATA_SPECIES, NULL);
        if (isEgg != 0 || hp == 0 || species == SPECIES_NONE || species == SPECIES_EGG || species == SPECIES_BAD_EGG) {
            continue;
        }

        info.found = TRUE;
        info.slot = i;
        info.species = (int)species;
        info.form = (int)Pokemon_GetValue(mon, MON_DATA_FORM, NULL);
        info.gender = (int)Pokemon_GetGender(mon);
        info.isShiny = Pokemon_IsShiny(mon) ? TRUE : FALSE;
        info.isLarge = FollowMonArchive_IsLargeSpecies((u16)info.species, (u8)info.form);
        return info;
    }

    return info;
}

// ---------------------------------------------------------------------------
// Billboard creation / teardown & custom MapObject renderer
// ---------------------------------------------------------------------------

static int FindModelNarcIdx(enum BillboardModel modelId)
{
    const ObjectEventGfxFileEntry *entry = gObjectEventGfxModelsTable;
    while (entry->id != BILLBOARD_MODEL_SENTINEL_ID) {
        if (entry->id == (int)modelId) {
            return entry->narcIdx;
        }
        entry++;
    }
    return -1;
}

static void FollowMon_FreeBillboardBuffers(void)
{
    if (sFollowMon.btxBuf != NULL) {
        Heap_Free(sFollowMon.btxBuf);
        sFollowMon.btxBuf = NULL;
    }
    if (sFollowMon.seqBuf != NULL) {
        Heap_Free(sFollowMon.seqBuf);
        sFollowMon.seqBuf = NULL;
    }
    if (sFollowMon.modelBuf != NULL) {
        Heap_Free(sFollowMon.modelBuf);
        sFollowMon.modelBuf = NULL;
    }
    memset(&sFollowMon.gfxSequence, 0, sizeof(sFollowMon.gfxSequence));
}

static BOOL FollowMon_BuildGfxSequence(const NNSG3dResTex *tex, BOOL isShiny)
{
    int texCount = (tex != NULL) ? (int)tex->dict.numEntry : 0;
    int plttCount = (tex != NULL && tex->plttInfo.ofsDict != 0) ? (int)((const NNSG3dResDict *)((const u8 *)tex + tex->plttInfo.ofsDict))->numEntry : 0;
    if (texCount <= 0 || plttCount <= 0) {
        return FALSE;
    }

    u8 plttIdx = FollowMonArchive_PaletteIndex(isShiny);
    if ((int)plttIdx >= plttCount) {
        plttIdx = 0;
    }

    u32 seqSize = 0;
    void *loadedSeq = FollowMon_ReadArchiveMember(FOLLOW_MON_ARC_SEQUENCE, &seqSize);
    BOOL validLoaded = FALSE;
    u32 seqCount = 0;

    if (loadedSeq != NULL && seqSize >= 4) {
        seqCount = *((u32 *)loadedSeq);
        if (seqCount > 0 && seqCount <= 128 && seqSize >= (4u + seqCount * 4u)) {
            validLoaded = TRUE;
        }
    }

    if (validLoaded) {
        sFollowMon.seqBuf = loadedSeq;
        BillboardGfxSequence_SetData(sFollowMon.seqBuf, &sFollowMon.gfxSequence);

        u8 *texIdxArr = (u8 *)sFollowMon.gfxSequence.textureIdx;
        u8 *plttIdxArr = (u8 *)sFollowMon.gfxSequence.plttIdx;
        const u16 *startArr = sFollowMon.gfxSequence.startFrame;

        for (u32 i = 0; i < seqCount; i++) {
            if ((int)texIdxArr[i] >= texCount) {
                texIdxArr[i] = (u8)(texIdxArr[i] % (u32)texCount);
            }
            plttIdxArr[i] = plttIdx;
        }

        u16 maxFrame = startArr[seqCount - 1];
        int dirSpan = 16;
        if (maxFrame >= 48) {
            dirSpan = 16;
        } else if (maxFrame >= 24) {
            dirSpan = 8;
        } else if (maxFrame >= 12) {
            dirSpan = 4;
        } else {
            dirSpan = 2;
        }

        for (int d = 0; d < 4; d++) {
            sFollowMon.anims[d].startFrame = d * dirSpan;
            sFollowMon.anims[d].endFrame = (d + 1) * dirSpan - 1;
            sFollowMon.anims[d].animType = BILLBOARD_ANIM_TYPE_LOOP;
        }
        sFollowMon.anims[4].startFrame = 0;
        sFollowMon.anims[4].endFrame = 0;
        sFollowMon.anims[4].animType = BILLBOARD_ANIM_TYPE_TABLE_END;
        return TRUE;
    }

    if (loadedSeq != NULL) {
        Heap_Free(loadedSeq);
    }

    // Fallback synthesized 4-direction x 2-frame sequence (64 frames total)
    const u32 count = 8;
    u8 *synth = Heap_AllocAtEnd(HEAP_ID_FIELD1, 4u + count * 4u);
    if (synth == NULL) {
        return FALSE;
    }
    *((u32 *)synth) = count;
    u16 *starts = (u16 *)(synth + 4);
    u8 *texIds = synth + 4 + count * 2;
    u8 *plttIds = texIds + count;
    for (u32 i = 0; i < count; i++) {
        starts[i] = (u16)(i * 8u);
        texIds[i] = (u8)(i % (u32)texCount);
        plttIds[i] = plttIdx;
    }
    sFollowMon.seqBuf = synth;
    BillboardGfxSequence_SetData(sFollowMon.seqBuf, &sFollowMon.gfxSequence);

    for (int d = 0; d < 4; d++) {
        sFollowMon.anims[d].startFrame = d * 16;
        sFollowMon.anims[d].endFrame = (d + 1) * 16 - 1;
        sFollowMon.anims[d].animType = BILLBOARD_ANIM_TYPE_LOOP;
    }
    sFollowMon.anims[4].startFrame = 0;
    sFollowMon.anims[4].endFrame = 0;
    sFollowMon.anims[4].animType = BILLBOARD_ANIM_TYPE_TABLE_END;
    return TRUE;
}

Billboard *FollowMon_CreateBillboard(MapObject *mapObj, BillboardList *list, ResourceHeap *modelHeap)
{
    (void)modelHeap;

    if (mapObj == NULL || list == NULL) {
        return NULL;
    }

    // Clean any previously owned follower billboard/buffers first.
    if (sFollowMon.billboard != NULL) {
        Billboard_Delete(sFollowMon.billboard);
        sFollowMon.billboard = NULL;
    }
    FollowMon_FreeBillboardBuffers();

    if (!FollowMon_EnsureArchiveLoaded() || sFollowMon.species <= SPECIES_NONE) {
        return NULL;
    }

    int memberIdx = FollowMonArchive_SpriteMemberIndex(
        (u16)sFollowMon.species,
        (u8)sFollowMon.form,
        (u8)sFollowMon.gender,
        sFollowMon.isShiny);
    if (memberIdx < 0 || memberIdx >= (int)sFollowMon.archive.numFiles) {
        return NULL;
    }

    u32 btxSize = 0;
    void *btxBuf = FollowMon_ReadArchiveMember(memberIdx, &btxSize);
    if (btxBuf == NULL || btxSize < 32) {
        if (btxBuf != NULL) {
            Heap_Free(btxBuf);
        }
        return NULL;
    }

    NNSG3dResTex *tex = NNS_G3dGetTex(btxBuf);
    if (tex == NULL || tex->dict.numEntry == 0 || tex->plttInfo.ofsDict == 0 || ((const NNSG3dResDict *)((const u8 *)tex + tex->plttInfo.ofsDict))->numEntry == 0) {
        Heap_Free(btxBuf);
        return NULL;
    }

    sFollowMon.btxBuf = btxBuf;

    // Detect actual BTX0 frame dimensions (32x32 vs 64x64) so VRAM transfer size matches.
    BOOL use64 = sFollowMon.isLarge;
    const NNSG3dResDictTexData *texData0 = NNS_G3dGetTexDataByIdx(tex, 0);
    if (texData0 != NULL) {
        u32 sShift = (texData0->texImageParam & NNS_G3D_TEXIMAGE_PARAM_S_SIZE_MASK) >> NNS_G3D_TEXIMAGE_PARAM_S_SIZE_SHIFT;
        u32 tShift = (texData0->texImageParam & NNS_G3D_TEXIMAGE_PARAM_T_SIZE_MASK) >> NNS_G3D_TEXIMAGE_PARAM_T_SIZE_SHIFT;
        u32 w = 8u << sShift;
        u32 h = 8u << tShift;
        if (w >= 64u || h >= 64u) {
            use64 = TRUE;
        } else {
            use64 = FALSE;
        }
    }

    int modelNarcIdx = FindModelNarcIdx(use64 ? BILLBOARD_MODEL_GENERIC_64x64 : BILLBOARD_MODEL_GENERIC_32x32);
    if (modelNarcIdx < 0) {
        FollowMon_FreeBillboardBuffers();
        return NULL;
    }

    const MapObjectManager *mapObjMan = MapObject_MapObjectManager(mapObj);
    sFollowMon.modelBuf = ov5_021ECD68(mapObjMan, (u32)modelNarcIdx, 0);
    if (sFollowMon.modelBuf == NULL) {
        FollowMon_FreeBillboardBuffers();
        return NULL;
    }

    if (!FollowMon_BuildGfxSequence(tex, sFollowMon.isShiny)) {
        FollowMon_FreeBillboardBuffers();
        return NULL;
    }

    BillboardResources res;
    memset(&res, 0, sizeof(res));
    BillboardResources_SetWithoutKeys(&res, sFollowMon.modelBuf, tex, sFollowMon.anims, &sFollowMon.gfxSequence);

    BillboardTemplate tmpl;
    memset(&tmpl, 0, sizeof(tmpl));
    tmpl.list = list;
    tmpl.resources = &res;
    ov5_021ECDA0(mapObj, &tmpl.pos);
    tmpl.pos.z += FX32_ONE * 6;
    VEC_Set(&tmpl.scale, FX32_ONE, FX32_ONE, FX32_ONE);

    Billboard *bb = BillboardList_Append(&tmpl);
    if (bb == NULL) {
        FollowMon_FreeBillboardBuffers();
        return NULL;
    }

    int dir = MapObject_GetFacingDir(mapObj);
    if (dir < DIR_NORTH || dir > DIR_EAST) {
        dir = DIR_SOUTH;
    }

    Billboard_SetDrawFlag(bb, (sFollowMon.hidden || MapObject_IsHidden(mapObj)) ? 0 : 1);
    Billboard_SetAnimNum(bb, dir);
    Billboard_SetAnimFrameNum(bb, 0);
    NNS_G3dMdlSetMdlFogEnableFlagAll(Billboard_GetModel(bb), 1);
    AreaLight_UseGlobalModelAttributes(Billboard_GetModel(bb));
    Billboard_TryRequestVRAMTransfer(bb);

    sFollowMon.billboard = bb;
    return bb;
}

void FollowMon_DestroyBillboard(MapObject *mapObj, Billboard **billboard)
{
    (void)mapObj;

    Billboard *target = NULL;
    if (billboard != NULL && *billboard != NULL) {
        target = *billboard;
        *billboard = NULL;
    } else if (sFollowMon.billboard != NULL) {
        target = sFollowMon.billboard;
    }

    if (target != NULL) {
        Billboard_Delete(target);
    }

    if (target == sFollowMon.billboard) {
        sFollowMon.billboard = NULL;
    } else if (sFollowMon.billboard != NULL) {
        Billboard_Delete(sFollowMon.billboard);
        sFollowMon.billboard = NULL;
    }

    FollowMon_FreeBillboardBuffers();
}

static void FollowMon_RenderInit(MapObject *mapObj)
{
    FollowMonRenderData *data = sub_02062ACC(mapObj, sizeof(FollowMonRenderData));
    data->billboard = NULL;
    data->lastDir = -1;

    ov5_021ECF04(mapObj, &data->billboard);
    if (data->billboard != NULL) {
        sub_02062B68(mapObj);
    }
}

static void FollowMon_RenderDraw(MapObject *mapObj)
{
    FollowMonRenderData *data = sub_02062AF0(mapObj);
    Billboard *bb = data->billboard;
    if (bb == NULL) {
        return;
    }

    int dir = MapObject_GetFacingDir(mapObj);
    if (dir < DIR_NORTH || dir > DIR_EAST) {
        dir = DIR_SOUTH;
    }

    if (dir != (int)data->lastDir) {
        Billboard_SetAnimNum(bb, dir);
        Billboard_SetAnimFrameNum(bb, 0);
        data->lastDir = (s8)dir;
    }

    if (ov5_021ECD38(mapObj) == 0) {
        fx32 animStep = FX32_ONE / 4; // gentle HGSS idle animation
        if (sFollowMon.moving) {
            if (sFollowMon.moveSpeed >= PLAYER_ACTION_SPEED_FAST) {
                animStep = FX32_ONE * 2;
            } else {
                animStep = FX32_ONE;
            }
        }
        Billboard_AdvanceAnim(bb, animStep);
    }

    ov5_021EDEB4(mapObj, bb);
    Billboard_SetDrawFlag(bb, (sFollowMon.hidden || MapObject_IsHidden(mapObj)) ? 0 : 1);
}

static void FollowMon_RenderDelete(MapObject *mapObj)
{
    FollowMonRenderData *data = sub_02062AF0(mapObj);
    ov5_021ECFA4(mapObj, &data->billboard);
}

static void FollowMon_RenderPause(MapObject *mapObj)
{
    FollowMonRenderData *data = sub_02062AF0(mapObj);
    ov5_021ECFA4(mapObj, &data->billboard);
    MapObject_SetStatusFlagOn(mapObj, MAP_OBJ_STATUS_21);
}

static void FollowMon_RenderResume(MapObject *mapObj)
{
    FollowMonRenderData *data = sub_02062AF0(mapObj);
    if (data->billboard == NULL) {
        ov5_021ECF04(mapObj, &data->billboard);
    }
    if (data->billboard != NULL) {
        ov5_021EDEB4(mapObj, data->billboard);
        Billboard_SetDrawFlag(data->billboard, (sFollowMon.hidden || MapObject_IsHidden(mapObj)) ? 0 : 1);
        MapObject_SetStatusFlagOff(mapObj, MAP_OBJ_STATUS_21);
    }
}

void FollowMon_BindObjectRenderer(MapObject *mapObj)
{
    sub_02062B4C(mapObj, FollowMon_RenderInit);
    sub_02062B60(mapObj, FollowMon_RenderDraw);
    sub_02062B74(mapObj, FollowMon_RenderDelete);
    sub_02062B88(mapObj, FollowMon_RenderPause);
    sub_02062B9C(mapObj, FollowMon_RenderResume);
}

BOOL FollowMon_IsFollowerObject(const MapObject *mapObj)
{
    if (mapObj == NULL) {
        return FALSE;
    }
    if (MapObject_GetLocalID(mapObj) == LOCALID_FOLLOW_MON
        || MapObject_GetGraphicsID(mapObj) == OBJ_EVENT_GFX_FOLLOW_MON) {
        return TRUE;
    }
    return FALSE;
}

// ---------------------------------------------------------------------------
// Positioning & spawn / despawn helpers
// ---------------------------------------------------------------------------

static void FollowMon_SnapToTile(FieldSystem *fieldSystem, MapObject *obj, int x, int z, int dir)
{
    VecFx32 pos;
    VecFx32 zero = { 0, 0, 0 };

    VecFx32_SetPosFromMapCoords(x, z, &pos);
    pos.y = (fieldSystem != NULL && fieldSystem->playerAvatar != NULL)
        ? PlayerAvatar_GetPos(fieldSystem->playerAvatar)->y
        : 0;
    if (fieldSystem != NULL) {
        MapObject_RecalculatePositionHeight(fieldSystem, &pos);
    }

    int yGrid = (pos.y >> 3) / FX32_ONE;
    MapObject_SetX(obj, x);
    MapObject_SetZ(obj, z);
    MapObject_SetY(obj, yGrid);
    MapObject_SetXPrev(obj, x);
    MapObject_SetZPrev(obj, z);
    MapObject_SetYPrev(obj, yGrid);
    MapObject_SetPos(obj, &pos);
    MapObject_Face(obj, dir);
    MapObject_Turn(obj, dir);
    MapObject_RecalculateObjectHeight(obj);

    zero.y = sFollowMon.talkJumpY;
    MapObject_SetSpriteJumpOffset(obj, &zero);

    if (sFollowMon.billboard != NULL) {
        ov5_021EDEB4(obj, sFollowMon.billboard);
    }

    sFollowMon.tileX = x;
    sFollowMon.tileZ = z;
    sFollowMon.dir = dir;
    sFollowMon.moving = FALSE;
    sFollowMon.hopping = FALSE;
    sFollowMon.moveFrame = 0;
    sFollowMon.moveDuration = 0;
}

static BOOL FollowMon_PickSpawnTile(FieldSystem *fieldSystem, int *outX, int *outZ, int *outDir)
{
    if (fieldSystem == NULL || fieldSystem->playerAvatar == NULL) {
        return FALSE;
    }

    int px = PlayerAvatar_GetXPos(fieldSystem->playerAvatar);
    int pz = PlayerAvatar_GetZPos(fieldSystem->playerAvatar);
    int pdir = PlayerAvatar_GetFacingDir(fieldSystem->playerAvatar);
    if (pdir < DIR_NORTH || pdir > DIR_EAST) {
        pdir = DIR_SOUTH;
    }

    int behindDir = Direction_GetOpposite(pdir);
    int dirs[4] = {
        behindDir,
        (behindDir + 1) % 4,
        (behindDir + 2) % 4,
        (behindDir + 3) % 4,
    };

    for (int i = 0; i < 4; i++) {
        int candX = px + MapObject_GetDxFromDir(dirs[i]);
        int candZ = pz + MapObject_GetDzFromDir(dirs[i]);
        if (!TerrainCollisionManager_CheckCollision(fieldSystem, candX, candZ)
            && MapHeaderData_IsPosFreeOfObjectEvents(fieldSystem, (u16)candX, (u16)candZ)) {
            *outX = candX;
            *outZ = candZ;
            *outDir = pdir;
            return TRUE;
        }
    }

    // Fallback: stand on player's tile (retracted until player steps)
    *outX = px;
    *outZ = pz;
    *outDir = pdir;
    return FALSE;
}

static void FollowMon_SetHiddenState(BOOL hidden)
{
    sFollowMon.hidden = hidden;
    if (sFollowMon.mapObj != NULL) {
        MapObject_SetHidden(sFollowMon.mapObj, hidden);
    }
    if (sFollowMon.billboard != NULL) {
        Billboard_SetDrawFlag(sFollowMon.billboard, hidden ? 0 : 1);
    }
}

static void FollowMon_Despawn(FieldSystem *fieldSystem)
{
    FollowMon_TalkOnFieldExit();

    MapObject *obj = sFollowMon.mapObj;
    if (obj == NULL && fieldSystem != NULL && fieldSystem->mapObjMan != NULL) {
        obj = FollowMon_GetMapObject(fieldSystem);
    }

    if (obj != NULL) {
        MapObject_Delete(obj);
    } else if (sFollowMon.billboard != NULL) {
        FollowMon_DestroyBillboard(NULL, &sFollowMon.billboard);
    } else {
        FollowMon_FreeBillboardBuffers();
    }

    sFollowMon.mapObj = NULL;
    sFollowMon.billboard = NULL;
    sFollowMon.active = FALSE;
    sFollowMon.hidden = TRUE;
    sFollowMon.moving = FALSE;
    sFollowMon.hopping = FALSE;
    sFollowMon.waitingForStepToEmerge = FALSE;
}

static BOOL FollowMon_ReloadBillboardForCurrentMon(MapObject *obj)
{
    if (obj == NULL) {
        return FALSE;
    }
    FollowMonRenderData *data = sub_02062AF0(obj);
    if (data == NULL) {
        return FALSE;
    }

    ov5_021ECFA4(obj, &data->billboard);
    data->lastDir = -1;
    ov5_021ECF04(obj, &data->billboard);
    if (data->billboard != NULL) {
        FollowMon_RenderDraw(obj);
        return TRUE;
    }
    return FALSE;
}

static void FollowMon_TrySpawn(FieldSystem *fieldSystem)
{
    if (fieldSystem == NULL || fieldSystem->mapObjMan == NULL || fieldSystem->playerAvatar == NULL) {
        return;
    }
    if (!SIM_Config_prj_FollowerEnabled() || !FollowMon_EnsureArchiveLoaded()) {
        return;
    }

    LeadMonInfo lead = FollowMon_FindLeadMon(fieldSystem);
    if (!lead.found) {
        return;
    }

    // Verify archive actually has a sprite for this species
    int memberIdx = FollowMonArchive_SpriteMemberIndex(
        (u16)lead.species,
        (u8)lead.form,
        (u8)lead.gender,
        lead.isShiny);
    if (memberIdx < 0 || memberIdx >= (int)sFollowMon.archive.numFiles) {
        return;
    }

    sFollowMon.partySlot = lead.slot;
    sFollowMon.species = lead.species;
    sFollowMon.form = lead.form;
    sFollowMon.gender = lead.gender;
    sFollowMon.isShiny = lead.isShiny;
    sFollowMon.isLarge = lead.isLarge;

    BOOL restricted = FollowMon_ShouldRetract(fieldSystem, lead.isLarge);
    int spawnX = 0;
    int spawnZ = 0;
    int spawnDir = DIR_SOUTH;
    BOOL foundOpenTile = FollowMon_PickSpawnTile(fieldSystem, &spawnX, &spawnZ, &spawnDir);

    BOOL startHidden = restricted || sFollowMon.retractOnNextInit || !foundOpenTile;
    sFollowMon.retractOnNextInit = FALSE;
    sFollowMon.hidden = startHidden;
    sFollowMon.waitingForStepToEmerge = startHidden;

    ObjectEvent ev;
    memset(&ev, 0, sizeof(ev));
    ObjectEvent_SetLocalID(&ev, LOCALID_FOLLOW_MON);
    ObjectEvent_SetGraphicsID(&ev, OBJ_EVENT_GFX_FOLLOW_MON);
    ObjectEvent_SetMovementType(&ev, MOVEMENT_TYPE_NONE);
    ObjectEvent_SetTrainerType(&ev, 0);
    ObjectEvent_SetHiddenFlag(&ev, 0);
    ObjectEvent_SetScript(&ev, 0);
    ObjectEvent_SetInitialDir(&ev, spawnDir);
    ObjectEvent_SetDataAt(&ev, 0, 0);
    ObjectEvent_SetDataAt(&ev, 0, 1);
    ObjectEvent_SetDataAt(&ev, 0, 2);
    ObjectEvent_SetMovementRangeX(&ev, -1);
    ObjectEvent_SetMovementRangeZ(&ev, -1);
    ObjectEvent_SetX(&ev, spawnX);
    ObjectEvent_SetZ(&ev, spawnZ);
    ObjectEvent_SetY(&ev, 0);

    enum MapHeaderID mapId = (fieldSystem->location != NULL)
        ? fieldSystem->location->mapHeaderID
        : MAP_HEADER_TWINLEAF_TOWN;

    MapObject *obj = MapObjectMan_AddMapObjectFromHeader(fieldSystem->mapObjMan, &ev, mapId);
    if (obj == NULL) {
        sFollowMon.active = FALSE;
        return;
    }

    // Persistent across zone crossings, pass-through for player, non-script-interactable.
    MapObject_SetStatusFlagOn(obj, MAP_OBJ_STATUS_PERSISTENT | MAP_OBJ_STATUS_18 | MAP_OBJ_STATUS_19);
    MapObject_SetStatusFlagOff(obj, MAP_OBJ_STATUS_AUTO_BORDER_CLONE);
    MapObject_SetHidden(obj, startHidden);

    sFollowMon.mapObj = obj;
    sFollowMon.active = TRUE;

    FollowMon_SnapToTile(fieldSystem, obj, spawnX, spawnZ, spawnDir);
    FollowMon_SetHiddenState(startHidden);
}

// ---------------------------------------------------------------------------
// Public lifecycle & movement hooks
// ---------------------------------------------------------------------------

void FollowMon_OnFieldInit(FieldSystem *fieldSystem)
{
    sFollowMon.fieldActive = TRUE;
    sFollowMon.talkJumpY = 0;

    // Clean any stale pointer from a previous field session before spawning.
    sFollowMon.mapObj = NULL;
    sFollowMon.billboard = NULL;
    FollowMon_FreeBillboardBuffers();

    if (!FollowMon_EnsureArchiveLoaded()) {
        sFollowMon.active = FALSE;
        sFollowMon.hidden = TRUE;
        return;
    }

    FollowMon_TrySpawn(fieldSystem);
}

void FollowMon_OnFieldExit(FieldSystem *fieldSystem)
{
    FollowMon_Despawn(fieldSystem);
    sFollowMon.fieldActive = FALSE;
    sFollowMon.talkJumpY = 0;
}

void FollowMon_OnZoneChange(FieldSystem *fieldSystem)
{
    if (!sFollowMon.fieldActive || fieldSystem == NULL || fieldSystem->location == NULL) {
        return;
    }

    if (sFollowMon.active && sFollowMon.mapObj != NULL) {
        enum MapHeaderID newMap = fieldSystem->location->mapHeaderID;
        MapObject_SetMapHeaderID(sFollowMon.mapObj, newMap);
        MapObject_SetStatusFlagOn(sFollowMon.mapObj, MAP_OBJ_STATUS_PERSISTENT | MAP_OBJ_STATUS_18 | MAP_OBJ_STATUS_19);
        MapObject_SetStatusFlagOff(sFollowMon.mapObj, MAP_OBJ_STATUS_AUTO_BORDER_CLONE);

        if (FollowMon_ShouldRetract(fieldSystem, sFollowMon.isLarge)) {
            FollowMon_SetHiddenState(TRUE);
            sFollowMon.waitingForStepToEmerge = TRUE;
        }
    }
}

void FollowMon_OnPlayerWarp(FieldSystem *fieldSystem)
{
    (void)fieldSystem;
    sFollowMon.retractOnNextInit = TRUE;
    sFollowMon.waitingForStepToEmerge = TRUE;
    if (sFollowMon.active) {
        FollowMon_SetHiddenState(TRUE);
    }
}

void FollowMon_OnPlayerStep(FieldSystem *fieldSystem, int oldX, int oldZ, int newX, int newZ, int dir, int actionSpeed, BOOL isJump)
{
    if (!sFollowMon.fieldActive || !sFollowMon.active || sFollowMon.mapObj == NULL || fieldSystem == NULL) {
        return;
    }

    if (!SIM_Config_prj_FollowerEnabled()) {
        return;
    }

    if (FollowMon_ShouldRetract(fieldSystem, sFollowMon.isLarge)) {
        if (!sFollowMon.hidden) {
            FollowMon_SetHiddenState(TRUE);
        }
        sFollowMon.waitingForStepToEmerge = TRUE;
        return;
    }

    // Track steps and drift mood toward 0 every 100 steps.
    sFollowMon.stepCounter++;
    if ((sFollowMon.stepCounter % 100u) == 0u) {
        if (sFollowMon.mood > 0) {
            sFollowMon.mood--;
        } else if (sFollowMon.mood < 0) {
            sFollowMon.mood++;
        }
    }

    MapObject *obj = sFollowMon.mapObj;

    // Re-emerge from Poke Ball onto the tile the player just vacated.
    if (sFollowMon.hidden) {
        FollowMon_SnapToTile(fieldSystem, obj, oldX, oldZ, dir);
        sFollowMon.waitingForStepToEmerge = FALSE;
        FollowMon_SetHiddenState(FALSE);
        sFollowMon.moving = TRUE;
        sFollowMon.hopping = TRUE;
        sFollowMon.moveFrame = 0;
        sFollowMon.moveDuration = SIM_Config_prj_DoubleStep() ? 16 : 8;
        sFollowMon.moveSpeed = actionSpeed;
        sFollowMon.targetX = oldX;
        sFollowMon.targetZ = oldZ;
        sFollowMon.targetDir = dir;
        MapObject_GetPosPtr(obj, &sFollowMon.startPos);
        sFollowMon.endPos = sFollowMon.startPos;
        Sound_PlayEffect(SEQ_SE_DP_BOWA_sseq);
        return;
    }

    // Determine target tile: the player's just-vacated tile (oldX, oldZ).
    // When the player walks onto the follower's tile (newX == tileX && newZ == tileZ),
    // the follower smoothly swaps onto (oldX, oldZ) behind the player.
    int curX = sFollowMon.moving ? sFollowMon.targetX : sFollowMon.tileX;
    int curZ = sFollowMon.moving ? sFollowMon.targetZ : sFollowMon.tileZ;

    if (curX == oldX && curZ == oldZ) {
        MapObject_Face(obj, dir);
        sFollowMon.dir = dir;
        return;
    }

    // Snap any in-progress step to its destination before launching the next step.
    if (sFollowMon.moving) {
        FollowMon_SnapToTile(fieldSystem, obj, sFollowMon.targetX, sFollowMon.targetZ, sFollowMon.targetDir);
        curX = sFollowMon.tileX;
        curZ = sFollowMon.tileZ;
    }

    int dx = oldX - curX;
    int dz = oldZ - curZ;
    int manhattan = (dx < 0 ? -dx : dx) + (dz < 0 ? -dz : dz);

    // If follower somehow got separated (> 3 tiles), teleport smoothly to vacated tile.
    if (manhattan > 3) {
        FollowMon_SnapToTile(fieldSystem, obj, oldX, oldZ, dir);
        return;
    }

    int travelDir = GetDirectionBetweenPoints(curX, curZ, oldX, oldZ);
    if (travelDir < DIR_NORTH || travelDir > DIR_EAST) {
        travelDir = dir;
    }
    // If crossing directly onto the follower's tile, keep facing the player's new direction.
    BOOL isSwap = (newX == curX && newZ == curZ) ? TRUE : FALSE;
    int faceDir = isSwap ? dir : travelDir;

    int baseFrames = 8;
    if (isJump || manhattan >= 2) {
        baseFrames = 14;
    } else if (actionSpeed >= PLAYER_ACTION_SPEED_FAST) {
        baseFrames = 4;
    } else if (actionSpeed <= PLAYER_ACTION_SPEED_SLOW) {
        baseFrames = 12;
    }

    if (SIM_Config_prj_DoubleStep()) {
        baseFrames *= 2;
    }

    VecFx32 startPos;
    VecFx32 endPos;
    MapObject_GetPosPtr(obj, &startPos);
    VecFx32_SetPosFromMapCoords(oldX, oldZ, &endPos);
    endPos.y = startPos.y;
    MapObject_RecalculatePositionHeight(fieldSystem, &endPos);

    sFollowMon.moving = TRUE;
    sFollowMon.hopping = (isJump || manhattan >= 2) ? TRUE : FALSE;
    sFollowMon.moveFrame = 0;
    sFollowMon.moveDuration = baseFrames;
    sFollowMon.moveSpeed = actionSpeed;
    sFollowMon.targetX = oldX;
    sFollowMon.targetZ = oldZ;
    sFollowMon.targetDir = faceDir;
    sFollowMon.startPos = startPos;
    sFollowMon.endPos = endPos;

    // Update logical coordinates immediately so facing/talk checks see the target tile.
    MapObject_SetXPrev(obj, curX);
    MapObject_SetZPrev(obj, curZ);
    MapObject_SetX(obj, oldX);
    MapObject_SetZ(obj, oldZ);
    MapObject_Face(obj, faceDir);
    MapObject_Turn(obj, faceDir);
    sFollowMon.tileX = oldX;
    sFollowMon.tileZ = oldZ;
    sFollowMon.dir = faceDir;
}

void FollowMon_Update(FieldSystem *fieldSystem)
{
    if (!sFollowMon.fieldActive || fieldSystem == NULL || fieldSystem->playerAvatar == NULL) {
        return;
    }

    // Handle live config toggle OFF / ON.
    BOOL enabled = SIM_Config_prj_FollowerEnabled();
    if (!enabled) {
        if (sFollowMon.active) {
            FollowMon_Despawn(fieldSystem);
        }
        return;
    }

    if (!FollowMon_EnsureArchiveLoaded()) {
        return;
    }

    LeadMonInfo lead = FollowMon_FindLeadMon(fieldSystem);
    if (!lead.found) {
        if (sFollowMon.active) {
            FollowMon_Despawn(fieldSystem);
        }
        return;
    }

    if (!sFollowMon.active) {
        FollowMon_TrySpawn(fieldSystem);
        return;
    }

    // Verify MapObject is still alive in MapObjectManager.
    if (sFollowMon.mapObj == NULL || !FollowMon_IsFollowerObject(sFollowMon.mapObj)) {
        sFollowMon.mapObj = FollowMon_GetMapObject(fieldSystem);
        if (sFollowMon.mapObj == NULL) {
            sFollowMon.active = FALSE;
            FollowMon_TrySpawn(fieldSystem);
            return;
        }
    }

    // Live lead swap / form / shiny update.
    if (lead.species != sFollowMon.species
        || lead.form != sFollowMon.form
        || lead.gender != sFollowMon.gender
        || lead.isShiny != sFollowMon.isShiny
        || lead.slot != sFollowMon.partySlot) {
        int memberIdx = FollowMonArchive_SpriteMemberIndex(
            (u16)lead.species,
            (u8)lead.form,
            (u8)lead.gender,
            lead.isShiny);

        sFollowMon.partySlot = lead.slot;
        sFollowMon.species = lead.species;
        sFollowMon.form = lead.form;
        sFollowMon.gender = lead.gender;
        sFollowMon.isShiny = lead.isShiny;
        sFollowMon.isLarge = lead.isLarge;

        if (memberIdx < 0 || memberIdx >= (int)sFollowMon.archive.numFiles) {
            FollowMon_SetHiddenState(TRUE);
        } else {
            FollowMon_ReloadBillboardForCurrentMon(sFollowMon.mapObj);
        }
    }

    // Check retraction restrictions live (bike/surf/partner/disabled map/large indoors).
    BOOL restricted = FollowMon_ShouldRetract(fieldSystem, sFollowMon.isLarge);
    if (restricted) {
        if (!sFollowMon.hidden) {
            FollowMon_SetHiddenState(TRUE);
            sFollowMon.waitingForStepToEmerge = TRUE;
        }
    }

    // If the player teleported far away without FieldMap_Exit (e.g. script move), keep follower nearby.
    if (!sFollowMon.hidden && !sFollowMon.moving) {
        int px = PlayerAvatar_GetXPos(fieldSystem->playerAvatar);
        int pz = PlayerAvatar_GetZPos(fieldSystem->playerAvatar);
        int dx = px - sFollowMon.tileX;
        int dz = pz - sFollowMon.tileZ;
        int dist = (dx < 0 ? -dx : dx) + (dz < 0 ? -dz : dz);
        if (dist > 4) {
            int sx = 0;
            int sz = 0;
            int sdir = DIR_SOUTH;
            FollowMon_PickSpawnTile(fieldSystem, &sx, &sz, &sdir);
            FollowMon_SnapToTile(fieldSystem, sFollowMon.mapObj, sx, sz, sdir);
        }
    }

    // Advance smooth movement interpolation.
    if (sFollowMon.moving && sFollowMon.mapObj != NULL) {
        sFollowMon.moveFrame++;
        if (sFollowMon.moveFrame >= sFollowMon.moveDuration || sFollowMon.moveDuration <= 0) {
            FollowMon_SnapToTile(fieldSystem, sFollowMon.mapObj, sFollowMon.targetX, sFollowMon.targetZ, sFollowMon.targetDir);
        } else {
            int f = sFollowMon.moveFrame;
            int dur = sFollowMon.moveDuration;
            VecFx32 curPos;
            curPos.x = sFollowMon.startPos.x + (fx32)(((s64)(sFollowMon.endPos.x - sFollowMon.startPos.x) * f) / dur);
            curPos.y = sFollowMon.startPos.y + (fx32)(((s64)(sFollowMon.endPos.y - sFollowMon.startPos.y) * f) / dur);
            curPos.z = sFollowMon.startPos.z + (fx32)(((s64)(sFollowMon.endPos.z - sFollowMon.startPos.z) * f) / dur);
            MapObject_SetPos(sFollowMon.mapObj, &curPos);

            VecFx32 jumpOff = { 0, sFollowMon.talkJumpY, 0 };
            if (sFollowMon.hopping) {
                // Smooth parabolic arc peaking at 10 * FX32_ONE.
                s64 num = (s64)4 * f * (dur - f) * (10 * FX32_ONE);
                s64 den = (s64)dur * dur;
                jumpOff.y += (fx32)(num / den);
            }
            MapObject_SetSpriteJumpOffset(sFollowMon.mapObj, &jumpOff);
        }
    } else if (sFollowMon.mapObj != NULL) {
        VecFx32 jumpOff = { 0, sFollowMon.talkJumpY, 0 };
        MapObject_SetSpriteJumpOffset(sFollowMon.mapObj, &jumpOff);
    }

    FollowMon_TalkUpdate(fieldSystem);
}

// ---------------------------------------------------------------------------
// Mood, Shiny Leaf, & state query helpers
// ---------------------------------------------------------------------------

void FollowMon_AdjustMood(int delta)
{
    int next = sFollowMon.mood + delta;
    if (next < -128) {
        next = -128;
    } else if (next > 127) {
        next = 127;
    }
    sFollowMon.mood = next;
}

int FollowMon_GetMood(void)
{
    return sFollowMon.mood;
}

BOOL FollowMon_IsAvailable(void)
{
    return FollowMon_EnsureArchiveLoaded();
}

BOOL FollowMon_IsActive(void)
{
    return sFollowMon.active;
}

BOOL FollowMon_IsHidden(void)
{
    return sFollowMon.hidden;
}

int FollowMon_GetSpecies(void)
{
    return sFollowMon.active ? sFollowMon.species : SPECIES_NONE;
}

BOOL FollowMon_IsShiny(void)
{
    return sFollowMon.active ? sFollowMon.isShiny : FALSE;
}

BOOL FollowMon_IsLarge(void)
{
    return sFollowMon.active ? sFollowMon.isLarge : FALSE;
}

void FollowMon_GetPosition(int *outX, int *outZ, int *outDir)
{
    if (outX != NULL) {
        *outX = sFollowMon.tileX;
    }
    if (outZ != NULL) {
        *outZ = sFollowMon.tileZ;
    }
    if (outDir != NULL) {
        *outDir = sFollowMon.dir;
    }
}

MapObject *FollowMon_GetMapObject(FieldSystem *fieldSystem)
{
    if (sFollowMon.mapObj != NULL && FollowMon_IsFollowerObject(sFollowMon.mapObj)) {
        return sFollowMon.mapObj;
    }
    if (fieldSystem == NULL || fieldSystem->mapObjMan == NULL) {
        return NULL;
    }

    int idx = 0;
    MapObject *obj = NULL;
    while (MapObjectMan_FindObjectWithStatus(fieldSystem->mapObjMan, &obj, &idx, MAP_OBJ_STATUS_0) == TRUE) {
        if (FollowMon_IsFollowerObject(obj)) {
            return obj;
        }
    }
    return NULL;
}

void FollowMon_SetTalkBubbleOffset(fx32 jumpY)
{
    sFollowMon.talkJumpY = jumpY;
    if (sFollowMon.mapObj != NULL) {
        VecFx32 jumpOff = { 0, jumpY, 0 };
        MapObject_SetSpriteJumpOffset(sFollowMon.mapObj, &jumpOff);
    }
}

u8 FollowMon_GetShinyLeafCount(int slotIndex)
{
    if (slotIndex < 0 || slotIndex >= MAX_PARTY_SIZE) {
        return 0;
    }
    return sFollowMon.shinyLeaves[slotIndex];
}

void FollowMon_IncrementShinyLeafCount(int slotIndex)
{
    if (slotIndex < 0 || slotIndex >= MAX_PARTY_SIZE) {
        return;
    }
    if (sFollowMon.shinyLeaves[slotIndex] < 5) {
        sFollowMon.shinyLeaves[slotIndex]++;
    }
}

int FollowMon_GetActivePartySlot(void)
{
    return sFollowMon.active ? sFollowMon.partySlot : -1;
}

u32 FollowMon_GetStepCounter(void)
{
    return sFollowMon.stepCounter;
}
