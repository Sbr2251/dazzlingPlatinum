#include "overlay005/follow_mon.h"

#include <nitro.h>
#include <nnsys.h>
#include <stdio.h>
#include <string.h>

#include "constants/accessories.h"
#include "constants/battle/condition.h"
#include "constants/charcode.h"
#include "constants/heap.h"
#include "constants/items.h"
#include "constants/map_object.h"
#include "constants/overworld_weather.h"
#include "constants/pokemon.h"
#include "constants/rtc.h"
#include "constants/species.h"
#include "generated/bg_event_types.h"
#include "generated/pokemon_types.h"
#include "generated/time_of_day.h"

#include "field/field_system.h"
#include "overlay005/area_light.h"
#include "overlay005/follow_mon_archive.h"
#include "overlay005/ov5_021ECC20.h"
#include "overlay005/ov5_021ECE40.h"
#include "port/sim_config_prj.h"

#include "bg_window.h"
#include "billboard.h"
#include "billboard_gfx_sequence.h"
#include "field_message.h"
#include "field_overworld_state.h"
#include "field_task.h"
#include "heap.h"
#include "map_header.h"
#include "map_header_data.h"
#include "map_object.h"
#include "map_object_move.h"
#include "math_util.h"
#include "party.h"
#include "vram_transfer.h"
#include "player_avatar.h"
#include "player_move.h"
#include "pokemon.h"
#include "render_window.h"
#include "rtc.h"
#include "save_player.h"
#include "savedata.h"
#include "script_manager.h"
#include "sound_playback.h"
#include "string_gf.h"
#include "system.h"
#include "unk_020298BC.h"

typedef enum FollowMonTalkState {
    TALK_STATE_INIT = 0,
    TALK_STATE_HOP,
    TALK_STATE_WAIT_MSG,
} FollowMonTalkState;

typedef struct FollowMonTalkOutcome {
    FollowMonEmoteKind emote;
    int moodDelta;
    char message[160];
} FollowMonTalkOutcome;

typedef struct FollowMonEmoteState {
    Billboard *billboard;
    void *modelBuf;
    void *texBuf;
    void *seqBuf;
    BillboardGfxSequence gfxSequence;
    BillboardAnim anims[2];
    int timer;
} FollowMonEmoteState;

typedef struct FollowMonTalkTaskCtx {
    FollowMonTalkState state;
    int hopFrame;
    int hopDuration;
    u8 printerID;
    BOOL windowOpen;
    Window window;
    String *msgStr;
    FollowMonTalkOutcome outcome;
} FollowMonTalkTaskCtx;

static FollowMonEmoteState sEmote;
static u32 sLastGiftStep = 0;
static BOOL sGiftedOnce = FALSE;

// ---------------------------------------------------------------------------
// ASCII <-> Platinum String conversion helpers (straight ASCII only)
// ---------------------------------------------------------------------------

static char DecodePlatinumChar(charcode_t c)
{
    if (c >= CHAR_0 && c <= CHAR_9) {
        return (char)('0' + (c - CHAR_0));
    }
    if (c >= CHAR_A && c <= CHAR_Z) {
        return (char)('A' + (c - CHAR_A));
    }
    if (c >= CHAR_a && c <= CHAR_z) {
        return (char)('a' + (c - CHAR_a));
    }
    if (c == CHAR_SPACE || c == CHAR_WIDE_SPACE) {
        return ' ';
    }
    if (c == CHAR_MINUS) {
        return '-';
    }
    if (c == CHAR_PERIOD) {
        return '.';
    }
    if (c == CHAR_SINGLE_QUOTE_OPEN || c == CHAR_SINGLE_QUOTE_CLOSE) {
        return '\'';
    }
    if (c == CHAR_EXCLAMATION) {
        return '!';
    }
    if (c == CHAR_QUESTION) {
        return '?';
    }
    return '\0';
}

static charcode_t EncodeAsciiChar(char ch)
{
    if (ch >= '0' && ch <= '9') {
        return (charcode_t)(CHAR_0 + (ch - '0'));
    }
    if (ch >= 'A' && ch <= 'Z') {
        return (charcode_t)(CHAR_A + (ch - 'A'));
    }
    if (ch >= 'a' && ch <= 'z') {
        return (charcode_t)(CHAR_a + (ch - 'a'));
    }
    switch (ch) {
    case ' ':
        return CHAR_SPACE;
    case '\n':
        return CHAR_CR;
    case '!':
        return CHAR_EXCLAMATION;
    case '?':
        return CHAR_QUESTION;
    case '.':
        return CHAR_PERIOD;
    case ',':
        return CHAR_COMMA;
    case '\'':
        return CHAR_SINGLE_QUOTE_CLOSE;
    case '-':
        return CHAR_MINUS;
    case ':':
        return CHAR_COLON;
    case '/':
        return CHAR_SLASH;
    case '(':
        return CHAR_PAREN_OPEN;
    case ')':
        return CHAR_PAREN_CLOSE;
    default:
        return CHAR_SPACE;
    }
}

static void CopyAsciiToPlatinumString(String *dst, const char *src)
{
    if (dst == NULL || src == NULL) {
        return;
    }
    String_Clear(dst);
    int col = 0;
    int line = 0;
    for (int i = 0; src[i] != '\0'; i++) {
        if ((u32)dst->size + 1u >= (u32)dst->maxSize) {
            break;
        }
        if (src[i] == '\n') {
            String_AppendChar(dst, (line == 0) ? CHAR_CR : CHAR_CONTROL_SCROLL);
            col = 0;
            line++;
            continue;
        }
        if (src[i] == ' ') {
            int nextLen = 0;
            for (int j = i + 1; src[j] != '\0' && src[j] != ' ' && src[j] != '\n'; j++) {
                nextLen++;
            }
            if (col > 0 && col + 1 + nextLen > 32) {
                String_AppendChar(dst, (line == 0) ? CHAR_CR : CHAR_CONTROL_SCROLL);
                col = 0;
                line++;
                continue;
            }
        }
        String_AppendChar(dst, EncodeAsciiChar(src[i]));
        col++;
    }
}

static void ReadPokemonDisplayName(Pokemon *mon, char *outName, int cap)
{
    if (outName == NULL || cap <= 0) {
        return;
    }
    snprintf(outName, (size_t)cap, "Your Pokemon");
    if (mon == NULL) {
        return;
    }

    String *nickStr = String_Init(32, HEAP_ID_FIELD1);
    if (nickStr == NULL) {
        return;
    }

    Pokemon_GetValue(mon, MON_DATA_NICKNAME_STRING, nickStr);
    const charcode_t *data = String_GetData(nickStr);
    u32 len = String_Length(nickStr);
    int outLen = 0;
    for (u32 i = 0; i < len && outLen < cap - 1; i++) {
        if (data[i] == CHAR_EOS) {
            break;
        }
        char ch = DecodePlatinumChar(data[i]);
        if (ch != '\0') {
            outName[outLen++] = ch;
        }
    }
    if (outLen > 0) {
        outName[outLen] = '\0';
    }
    String_Free(nickStr);
}

// ---------------------------------------------------------------------------
// Overhead emote bubble billboard (from follow_mon.narc members 571..601)
// ---------------------------------------------------------------------------

static void FollowMon_DestroyEmote(void)
{
    if (sEmote.billboard != NULL || sEmote.texBuf != NULL) {
        VramTransfer_Process();
    }
    if (sEmote.billboard != NULL) {
        Billboard_Delete(sEmote.billboard);
        sEmote.billboard = NULL;
    }
    if (sEmote.modelBuf != NULL) {
        Heap_Free(sEmote.modelBuf);
        sEmote.modelBuf = NULL;
    }
    if (sEmote.texBuf != NULL) {
        Heap_Free(sEmote.texBuf);
        sEmote.texBuf = NULL;
    }
    if (sEmote.seqBuf != NULL) {
        Heap_Free(sEmote.seqBuf);
        sEmote.seqBuf = NULL;
    }
    memset(&sEmote.gfxSequence, 0, sizeof(sEmote.gfxSequence));
    sEmote.timer = 0;
}

static int EmoteKindToArchiveOffset(FollowMonEmoteKind emote)
{
    // Exact HGSS emote BTX0 order in follow_mon.narc (members 574..587):
    // 0: fuki_heart, 1..5: fuki_kao1..5, 6: fuki_onpu (music), 7: fuki_hatena (?),
    // 8: fuki_bikkuri (!), 9: fuki_ase (sweat), 10: fuki_komari (troubled),
    // 11: fuki_doku (poison), 12: fuki_chinmoku (...), 13: fuki_pikon (spark/excited)
    switch (emote) {
    case FOLLOW_MON_EMOTE_HEART:
        return 0;
    case FOLLOW_MON_EMOTE_HAPPY:
        return 1;
    case FOLLOW_MON_EMOTE_ANGRY:
        return 4;
    case FOLLOW_MON_EMOTE_MUSIC:
        return 6;
    case FOLLOW_MON_EMOTE_QUESTION:
        return 7;
    case FOLLOW_MON_EMOTE_EXCLAMATION:
        return 8;
    case FOLLOW_MON_EMOTE_SWEAT:
        return 9;
    case FOLLOW_MON_EMOTE_POISON:
        return 11;
    case FOLLOW_MON_EMOTE_SLEEPY:
        return 12;
    case FOLLOW_MON_EMOTE_SURPRISE:
        return 13;
    default:
        return 1;
    }
}

static void FollowMon_PositionEmoteAboveFollower(FieldSystem *fieldSystem)
{
    if (sEmote.billboard == NULL || fieldSystem == NULL) {
        return;
    }
    MapObject *followerObj = FollowMon_GetMapObject(fieldSystem);
    if (followerObj == NULL) {
        return;
    }

    VecFx32 pos;
    ov5_021ECDA0(followerObj, &pos);
    pos.y += (FollowMon_IsLarge() ? 40 : 30) * FX32_ONE;
    pos.z -= 2 * FX32_ONE;
    Billboard_SetPos(sEmote.billboard, &pos);
}

static void FollowMon_SpawnEmote(FieldSystem *fieldSystem, FollowMonEmoteKind emote)
{
    FollowMon_DestroyEmote();

    if (fieldSystem == NULL || fieldSystem->mapObjMan == NULL || emote == FOLLOW_MON_EMOTE_NONE) {
        return;
    }

    int memberCount = FollowMon_GetArchiveMemberCount();
    int offset = EmoteKindToArchiveOffset(emote);
    if (offset < 0 || offset >= FOLLOW_MON_ARC_EMOTE_KINDS) {
        offset = 0;
    }

    int modelIdx = FOLLOW_MON_ARC_EMOTE_MODEL;
    int texIdx = FOLLOW_MON_ARC_EMOTE_TEXTURES + offset;
    int seqIdx = FOLLOW_MON_ARC_EMOTE_SEQUENCES + offset;
    if (modelIdx >= memberCount || texIdx >= memberCount || seqIdx >= memberCount) {
        return;
    }

    u32 modelSize = 0;
    u32 texSize = 0;
    u32 seqSize = 0;
    void *modelBuf = FollowMon_ReadArchiveMember(modelIdx, &modelSize);
    void *texBuf = FollowMon_ReadArchiveMember(texIdx, &texSize);
    void *seqBuf = FollowMon_ReadArchiveMember(seqIdx, &seqSize);

    if (modelBuf == NULL || texBuf == NULL || seqBuf == NULL || modelSize < 16 || texSize < 32 || seqSize < 8) {
        if (modelBuf != NULL) {
            Heap_Free(modelBuf);
        }
        if (texBuf != NULL) {
            Heap_Free(texBuf);
        }
        if (seqBuf != NULL) {
            Heap_Free(seqBuf);
        }
        return;
    }

    NNSG3dResMdlSet *mdlSet = NNS_G3dGetMdlSet(modelBuf);
    NNSG3dResTex *tex = NNS_G3dGetTex(texBuf);
    u32 seqCount = *((u32 *)seqBuf);
    if (mdlSet == NULL || tex == NULL || tex->dict.numEntry == 0 || tex->plttInfo.ofsDict == 0 || ((const NNSG3dResDict *)((const u8 *)tex + tex->plttInfo.ofsDict))->numEntry == 0
        || seqCount == 0 || seqCount > 128 || seqSize < (4u + seqCount * 4u)) {
        Heap_Free(modelBuf);
        Heap_Free(texBuf);
        Heap_Free(seqBuf);
        return;
    }

    sEmote.modelBuf = modelBuf;
    sEmote.texBuf = texBuf;
    sEmote.seqBuf = seqBuf;
    BillboardGfxSequence_SetData(sEmote.seqBuf, &sEmote.gfxSequence);

    // Clamp sequence indices to avoid any OOB texture or palette lookup.
    u8 *texArr = (u8 *)sEmote.gfxSequence.textureIdx;
    u8 *plttArr = (u8 *)sEmote.gfxSequence.plttIdx;
    int texEntries = (int)tex->dict.numEntry;
    int plttEntries = (int)((const NNSG3dResDict *)((const u8 *)tex + tex->plttInfo.ofsDict))->numEntry;
    for (u32 i = 0; i < seqCount; i++) {
        if ((int)texArr[i] >= texEntries) {
            texArr[i] = (u8)(texArr[i] % (u32)texEntries);
        }
        if ((int)plttArr[i] >= plttEntries) {
            plttArr[i] = 0;
        }
    }

    u16 lastStart = sEmote.gfxSequence.startFrame[seqCount - 1];
    sEmote.anims[0].startFrame = 0;
    sEmote.anims[0].endFrame = (int)lastStart + 4;
    sEmote.anims[0].animType = BILLBOARD_ANIM_TYPE_LOOP;
    sEmote.anims[1].startFrame = 0;
    sEmote.anims[1].endFrame = 0;
    sEmote.anims[1].animType = BILLBOARD_ANIM_TYPE_TABLE_END;

    UnkStruct_ov5_021ED0A4 *gfxMan = sub_0206285C(fieldSystem->mapObjMan);
    BillboardList *list = ov5_021EDC8C(gfxMan);
    if (list == NULL) {
        FollowMon_DestroyEmote();
        return;
    }

    BillboardResources res;
    memset(&res, 0, sizeof(res));
    BillboardResources_SetWithoutKeys(&res, sEmote.modelBuf, tex, sEmote.anims, &sEmote.gfxSequence);

    BillboardTemplate tmpl;
    memset(&tmpl, 0, sizeof(tmpl));
    tmpl.list = list;
    tmpl.resources = &res;
    VEC_Set(&tmpl.pos, 0, 0, 0);
    VEC_Set(&tmpl.scale, FX32_ONE, FX32_ONE, FX32_ONE);

    Billboard *bb = BillboardList_Append(&tmpl);
    if (bb == NULL) {
        FollowMon_DestroyEmote();
        return;
    }

    sEmote.billboard = bb;
    sEmote.timer = SIM_Config_prj_DoubleStep() ? 140 : 70;
    Billboard_SetDrawFlag(bb, 1);
    Billboard_SetAnimNum(bb, 0);
    Billboard_SetAnimFrameNum(bb, 0);
    NNS_G3dMdlSetMdlFogEnableFlagAll(Billboard_GetModel(bb), 0);
    AreaLight_UseGlobalModelAttributes(Billboard_GetModel(bb));
    FollowMon_PositionEmoteAboveFollower(fieldSystem);
    Billboard_TryRequestVRAMTransfer(bb);
}

void FollowMon_TalkOnFieldExit(void)
{
    FollowMon_DestroyEmote();
}

void FollowMon_TalkUpdate(FieldSystem *fieldSystem)
{
    if (sEmote.billboard == NULL) {
        return;
    }

    FollowMon_PositionEmoteAboveFollower(fieldSystem);
    Billboard_AdvanceAnim(sEmote.billboard, FX32_ONE);

    if (sEmote.timer > 0) {
        sEmote.timer--;
        if (sEmote.timer == 0) {
            FollowMon_DestroyEmote();
        }
    }
}

// ---------------------------------------------------------------------------
// Contextual dialogue, mood, hidden item sniffing & gift / Shiny Leaf logic
// ---------------------------------------------------------------------------

static BOOL HasNearbyHiddenItem(FieldSystem *fieldSystem, int centerX, int centerZ)
{
    if (fieldSystem == NULL) {
        return FALSE;
    }
    const BgEvent *events = MapHeaderData_GetBgEvents(fieldSystem);
    int numEvents = MapHeaderData_GetNumBgEvents(fieldSystem);
    if (events == NULL || numEvents <= 0) {
        return FALSE;
    }

    for (int i = 0; i < numEvents; i++) {
        if (events[i].type != BG_EVENT_TYPE_HIDDEN_ITEM) {
            continue;
        }
        u16 flag = Script_GetHiddenItemFlag((u16)events[i].script);
        if (FieldSystem_CheckFlag(fieldSystem, flag) == TRUE) {
            continue;
        }
        int dx = events[i].x - centerX;
        int dz = events[i].z - centerZ;
        if (dx < 0) {
            dx = -dx;
        }
        if (dz < 0) {
            dz = -dz;
        }
        if (dx + dz <= 4) {
            return TRUE;
        }
    }
    return FALSE;
}

typedef struct AccessoryGiftEntry {
    u32 accessoryId;
    const char *name;
} AccessoryGiftEntry;

static const AccessoryGiftEntry sGiftAccessories[] = {
    { ACCESSORY_RED_FLOWER, "Red Flower" },
    { ACCESSORY_WHITE_FLUFF, "White Fluff" },
    { ACCESSORY_ROUND_PEBBLE, "Round Pebble" },
    { ACCESSORY_SMALL_LEAF, "Small Leaf" },
    { ACCESSORY_PRETTY_DEWDROP, "Pretty Dewdrop" },
    { ACCESSORY_SEASHELL, "Seashell" },
    { ACCESSORY_SHINY_POWDER, "Shiny Powder" },
    { ACCESSORY_HUMMING_NOTE, "Humming Note" },
    { ACCESSORY_BLUE_FEATHER, "Blue Feather" },
    { ACCESSORY_PINK_SCALE, "Pink Scale" },
};

static BOOL TryAwardFollowerGift(FieldSystem *fieldSystem, int slotIndex, const char *monName, FollowMonTalkOutcome *out)
{
    if (fieldSystem == NULL || fieldSystem->saveData == NULL) {
        return FALSE;
    }

    u32 steps = FollowMon_GetStepCounter();
    if (sGiftedOnce && steps >= sLastGiftStep && (steps - sLastGiftStep) < 50u) {
        return FALSE;
    }

    enum MapHeaderID mapId = (fieldSystem->location != NULL)
        ? fieldSystem->location->mapHeaderID
        : MAP_HEADER_TWINLEAF_TOWN;

    // 1. Shiny Leaf opportunity outdoors (up to 5 tracked per party slot).
    u8 leaves = FollowMon_GetShinyLeafCount(slotIndex);
    if (MapHeader_IsOutdoors(mapId) && leaves < 5 && ((LCRNG_Next() % 3u) == 0u)) {
        FollowMon_IncrementShinyLeafCount(slotIndex);
        u8 newLeaves = FollowMon_GetShinyLeafCount(slotIndex);
        sLastGiftStep = steps;
        sGiftedOnce = TRUE;
        out->emote = FOLLOW_MON_EMOTE_HEART;
        out->moodDelta = 6;
        if (newLeaves >= 5) {
            snprintf(
                out->message,
                sizeof(out->message),
                "%s found a Shiny Leaf! Its 5 Shiny Leaves sparkle like a golden crown!",
                monName);
        } else {
            snprintf(
                out->message,
                sizeof(out->message),
                "%s found a Shiny Leaf! (%u/5 Shiny Leaves collected!)",
                monName,
                (unsigned)newLeaves);
        }
        return TRUE;
    }

    // 2. Fashion Case accessory gift.
    ImageClips *clips = SaveData_GetImageClips(fieldSystem->saveData);
    FashionCase *fashionCase = (clips != NULL) ? ImageClips_GetFashionCase(clips) : NULL;
    if (fashionCase != NULL) {
        int count = (int)(sizeof(sGiftAccessories) / sizeof(sGiftAccessories[0]));
        int start = (int)(LCRNG_Next() % (u32)count);
        for (int i = 0; i < count; i++) {
            const AccessoryGiftEntry *entry = &sGiftAccessories[(start + i) % count];
            if (FashionCase_CanFitAccessoryCount(fashionCase, entry->accessoryId, 1)) {
                FashionCase_AddAccessory(fashionCase, entry->accessoryId, 1);
                sLastGiftStep = steps;
                sGiftedOnce = TRUE;
                out->emote = FOLLOW_MON_EMOTE_MUSIC;
                out->moodDelta = 5;
                snprintf(
                    out->message,
                    sizeof(out->message),
                    "%s picked up a %s and happily gave it to you for your Fashion Case!",
                    monName,
                    entry->name);
                return TRUE;
            }
        }
    }

    return FALSE;
}

static void FollowMon_EvaluateTalk(FieldSystem *fieldSystem, FollowMonTalkOutcome *out)
{
    memset(out, 0, sizeof(*out));
    out->emote = FOLLOW_MON_EMOTE_HAPPY;
    out->moodDelta = 2;

    int slot = FollowMon_GetActivePartySlot();
    Pokemon *mon = NULL;
    if (fieldSystem != NULL && fieldSystem->saveData != NULL && slot >= 0) {
        Party *party = SaveData_GetParty(fieldSystem->saveData);
        if (party != NULL && slot < Party_GetCurrentCount(party)) {
            mon = Party_GetPokemonBySlotIndex(party, slot);
        }
    }

    char name[32];
    ReadPokemonDisplayName(mon, name, (int)sizeof(name));

    u32 hp = (mon != NULL) ? Pokemon_GetValue(mon, MON_DATA_HP, NULL) : 10;
    u32 maxHp = (mon != NULL) ? Pokemon_GetValue(mon, MON_DATA_MAX_HP, NULL) : 10;
    u32 status = (mon != NULL) ? Pokemon_GetValue(mon, MON_DATA_STATUS, NULL) : 0;
    u32 heldItem = (mon != NULL) ? Pokemon_GetValue(mon, MON_DATA_HELD_ITEM, NULL) : ITEM_NONE;
    u32 friendship = (mon != NULL) ? Pokemon_GetValue(mon, MON_DATA_FRIENDSHIP, NULL) : 70;
    u32 type1 = (mon != NULL) ? Pokemon_GetValue(mon, MON_DATA_TYPE_1, NULL) : TYPE_NORMAL;
    u32 type2 = (mon != NULL) ? Pokemon_GetValue(mon, MON_DATA_TYPE_2, NULL) : TYPE_NORMAL;
    int mood = FollowMon_GetMood();

    u16 weather = OVERWORLD_WEATHER_CLEAR;
    if (fieldSystem != NULL && fieldSystem->saveData != NULL) {
        FieldOverworldState *ovState = SaveData_GetFieldOverworldState(fieldSystem->saveData);
        if (ovState != NULL) {
            weather = FieldOverworldState_GetWeather(ovState);
        }
    }
    enum TimeOfDay tod = GetTimeOfDay();

    int fx = 0;
    int fz = 0;
    int fdir = DIR_SOUTH;
    FollowMon_GetPosition(&fx, &fz, &fdir);
    (void)fdir;

    // 1. Status conditions take top priority.
    if (status & MON_CONDITION_ANY_POISON) {
        out->emote = FOLLOW_MON_EMOTE_POISON;
        out->moodDelta = -1;
        snprintf(out->message, sizeof(out->message), "%s is shivering from poison...", name);
        return;
    }
    if (status & (MON_CONDITION_BURN | MON_CONDITION_PARALYSIS | MON_CONDITION_FREEZE)) {
        out->emote = FOLLOW_MON_EMOTE_SWEAT;
        out->moodDelta = -1;
        snprintf(out->message, sizeof(out->message), "%s looks uncomfortable and could use some care!", name);
        return;
    }
    if (status & MON_CONDITION_SLEEP) {
        out->emote = FOLLOW_MON_EMOTE_SLEEPY;
        out->moodDelta = 0;
        snprintf(out->message, sizeof(out->message), "%s is drowsy and nodding off on its feet.", name);
        return;
    }

    // 2. Low HP check.
    if (maxHp > 0 && (hp * 4u) <= maxHp) {
        out->emote = FOLLOW_MON_EMOTE_SWEAT;
        out->moodDelta = 0;
        snprintf(out->message, sizeof(out->message), "%s looks tired and worn out. Maybe visit a Pokemon Center?", name);
        return;
    }

    // 3. Gift / Shiny Leaf when friendship >= 150 and mood >= 20.
    if (friendship >= 150u && mood >= 20 && slot >= 0) {
        if (TryAwardFollowerGift(fieldSystem, slot, name, out)) {
            return;
        }
    }

    // 4. Nearby hidden item hint.
    if (HasNearbyHiddenItem(fieldSystem, fx, fz)) {
        out->emote = FOLLOW_MON_EMOTE_EXCLAMATION;
        out->moodDelta = 3;
        snprintf(out->message, sizeof(out->message), "%s is sniffing the ground excitedly! Something seems hidden nearby!", name);
        return;
    }

    // 5. Weather + Type reactions.
    BOOL isRain = (weather == OVERWORLD_WEATHER_RAINING
        || weather == OVERWORLD_WEATHER_HEAVY_RAIN
        || weather == OVERWORLD_WEATHER_THUNDERSTORM);
    BOOL isSnow = (weather == OVERWORLD_WEATHER_SNOWING
        || weather == OVERWORLD_WEATHER_HEAVY_SNOW
        || weather == OVERWORLD_WEATHER_BLIZZARD
        || weather == OVERWORLD_WEATHER_HAILING);

    if (isRain) {
        if (type1 == TYPE_WATER || type2 == TYPE_WATER || type1 == TYPE_ELECTRIC || type2 == TYPE_ELECTRIC) {
            out->emote = FOLLOW_MON_EMOTE_MUSIC;
            out->moodDelta = 4;
            snprintf(out->message, sizeof(out->message), "%s is splashing around joyfully in the rain!", name);
            return;
        }
        if (type1 == TYPE_FIRE || type2 == TYPE_FIRE) {
            out->emote = FOLLOW_MON_EMOTE_SWEAT;
            out->moodDelta = -2;
            snprintf(out->message, sizeof(out->message), "%s is trying to stay dry out of the rain...", name);
            return;
        }
    }
    if (isSnow && (type1 == TYPE_ICE || type2 == TYPE_ICE)) {
        out->emote = FOLLOW_MON_EMOTE_HAPPY;
        out->moodDelta = 4;
        snprintf(out->message, sizeof(out->message), "%s is beaming with energy in the falling snow!", name);
        return;
    }
    if (weather == OVERWORLD_WEATHER_SANDSTORM
        && (type1 == TYPE_ROCK || type2 == TYPE_ROCK || type1 == TYPE_GROUND || type2 == TYPE_GROUND || type1 == TYPE_STEEL || type2 == TYPE_STEEL)) {
        out->emote = FOLLOW_MON_EMOTE_HAPPY;
        out->moodDelta = 3;
        snprintf(out->message, sizeof(out->message), "%s stands proud and energized in the swirling sandstorm!", name);
        return;
    }
    if (weather == OVERWORLD_WEATHER_FOG || weather == OVERWORLD_WEATHER_DEEP_FOG) {
        out->emote = FOLLOW_MON_EMOTE_QUESTION;
        out->moodDelta = 1;
        snprintf(out->message, sizeof(out->message), "%s is peering carefully through the mist.", name);
        return;
    }

    // 6. Negative mood.
    if (mood <= -30) {
        out->emote = FOLLOW_MON_EMOTE_ANGRY;
        out->moodDelta = 4;
        snprintf(out->message, sizeof(out->message), "%s looks a little grumpy, but perks up when you check on it.", name);
        return;
    }

    // 7. Time of day reactions.
    if ((tod == TIMEOFDAY_NIGHT || tod == TIMEOFDAY_LATE_NIGHT)
        && (type1 == TYPE_GHOST || type2 == TYPE_GHOST || type1 == TYPE_DARK || type2 == TYPE_DARK)) {
        out->emote = FOLLOW_MON_EMOTE_MUSIC;
        out->moodDelta = 3;
        snprintf(out->message, sizeof(out->message), "%s is full of lively spirit under the night sky!", name);
        return;
    }
    if (tod == TIMEOFDAY_LATE_NIGHT) {
        out->emote = FOLLOW_MON_EMOTE_SLEEPY;
        out->moodDelta = 2;
        snprintf(out->message, sizeof(out->message), "%s let out a big yawn... It looks a bit sleepy.", name);
        return;
    }

    // 8. Held item mention (when holding an item and roll hits).
    if (heldItem != ITEM_NONE && ((LCRNG_Next() % 4u) == 0u)) {
        out->emote = FOLLOW_MON_EMOTE_HAPPY;
        out->moodDelta = 2;
        snprintf(out->message, sizeof(out->message), "%s is proudly holding onto its item!", name);
        return;
    }

    // 9. High friendship / great mood reactions.
    if (friendship >= 200u || mood >= 40) {
        out->emote = FOLLOW_MON_EMOTE_HEART;
        out->moodDelta = 3;
        snprintf(out->message, sizeof(out->message), "%s nuzzled up close to you! It looks completely overjoyed!", name);
        return;
    }

    if (tod == TIMEOFDAY_MORNING) {
        out->emote = FOLLOW_MON_EMOTE_HAPPY;
        out->moodDelta = 2;
        snprintf(out->message, sizeof(out->message), "%s is enjoying the fresh morning breeze!", name);
        return;
    }

    // 10. Varied cheerful default reactions.
    switch ((FollowMon_GetStepCounter() + LCRNG_Next()) % 4u) {
    case 0:
        out->emote = FOLLOW_MON_EMOTE_HAPPY;
        snprintf(out->message, sizeof(out->message), "%s is happily trotting along right behind you!", name);
        break;
    case 1:
        out->emote = FOLLOW_MON_EMOTE_MUSIC;
        snprintf(out->message, sizeof(out->message), "%s is humming a cheerful little tune!", name);
        break;
    case 2:
        out->emote = FOLLOW_MON_EMOTE_HEART;
        snprintf(out->message, sizeof(out->message), "%s looked up at you with bright, trusting eyes!", name);
        break;
    default:
        out->emote = FOLLOW_MON_EMOTE_SURPRISE;
        snprintf(out->message, sizeof(out->message), "%s bounced with excitement! It seems eager to explore!", name);
        break;
    }
}

// ---------------------------------------------------------------------------
// Interactive FieldTask for Press-A talk
// ---------------------------------------------------------------------------

static BOOL FollowMon_TalkFieldTask(FieldTask *task)
{
    FieldSystem *fieldSystem = FieldTask_GetFieldSystem(task);
    FollowMonTalkTaskCtx *ctx = FieldTask_GetEnv(task);
    if (fieldSystem == NULL || ctx == NULL) {
        return TRUE;
    }

    switch (ctx->state) {
    case TALK_STATE_INIT: {
        MapObjectMan_PauseAllMovement(fieldSystem->mapObjMan);
        FollowMon_SyncBillboardPose(fieldSystem);
        FollowMon_EvaluateTalk(fieldSystem, &ctx->outcome);
        FollowMon_AdjustMood(ctx->outcome.moodDelta);

        int species = FollowMon_GetSpecies();
        if (species > SPECIES_NONE) {
            Sound_PlayPokemonCry((u16)species, 0);
        }

        FollowMon_SpawnEmote(fieldSystem, ctx->outcome.emote);
        ctx->hopFrame = 0;
        ctx->hopDuration = SIM_Config_prj_DoubleStep() ? 24 : 12;
        ctx->state = TALK_STATE_HOP;
        break;
    }

    case TALK_STATE_HOP: {
        ctx->hopFrame++;
        int f = ctx->hopFrame;
        int dur = ctx->hopDuration;
        if (f < dur && dur > 0) {
            s64 num = (s64)4 * f * (dur - f) * (8 * FX32_ONE);
            s64 den = (s64)dur * dur;
            FollowMon_SetTalkBubbleOffset((fx32)(num / den));
            FollowMon_SyncBillboardPose(fieldSystem);
            return FALSE;
        }

        FollowMon_SetTalkBubbleOffset(0);
        FollowMon_SyncBillboardPose(fieldSystem);
        ctx->msgStr = String_Init(256, HEAP_ID_FIELD1);
        if (ctx->msgStr != NULL) {
            CopyAsciiToPlatinumString(ctx->msgStr, ctx->outcome.message);
            FieldMessage_AddWindow(fieldSystem->bgConfig, &ctx->window, BG_LAYER_MAIN_3);
            FieldMessage_DrawWindow(&ctx->window, SaveData_GetOptions(fieldSystem->saveData));
            ctx->windowOpen = TRUE;
            ctx->printerID = FieldMessage_Print(&ctx->window, ctx->msgStr, SaveData_GetOptions(fieldSystem->saveData), TRUE);
            ctx->state = TALK_STATE_WAIT_MSG;
            return FALSE;
        }

        FollowMon_DestroyEmote();
        MapObjectMan_UnpauseAllMovement(fieldSystem->mapObjMan);
        Heap_Free(ctx);
        return TRUE;
    }

    case TALK_STATE_WAIT_MSG: {
        if (FieldMessage_FinishedPrinting(ctx->printerID) == TRUE && JOY_NEW(PAD_BUTTON_A | PAD_BUTTON_B)) {
            if (ctx->windowOpen) {
                Window_EraseMessageBox(&ctx->window, FALSE);
                Window_Remove(&ctx->window);
                ctx->windowOpen = FALSE;
            }
            if (ctx->msgStr != NULL) {
                String_Free(ctx->msgStr);
                ctx->msgStr = NULL;
            }
            FollowMon_DestroyEmote();
            FollowMon_SetTalkBubbleOffset(0);
            MapObjectMan_UnpauseAllMovement(fieldSystem->mapObjMan);
            Heap_Free(ctx);
            return TRUE;
        }
        break;
    }
    }

    return FALSE;
}

BOOL FollowMon_TryTalk(FieldSystem *fieldSystem)
{
    if (fieldSystem == NULL || fieldSystem->playerAvatar == NULL || fieldSystem->mapObjMan == NULL) {
        return FALSE;
    }
    if (!FollowMon_IsActive() || FollowMon_IsHidden()) {
        return FALSE;
    }
    if (FieldSystem_IsRunningTask(fieldSystem)) {
        return FALSE;
    }

    MapObject *followerObj = FollowMon_GetMapObject(fieldSystem);
    if (followerObj == NULL || MapObject_IsHidden(followerObj)) {
        return FALSE;
    }

    int px = PlayerAvatar_GetXPos(fieldSystem->playerAvatar);
    int pz = PlayerAvatar_GetZPos(fieldSystem->playerAvatar);
    int pdir = PlayerAvatar_GetFacingDir(fieldSystem->playerAvatar);
    int facingX = px + MapObject_GetDxFromDir(pdir);
    int facingZ = pz + MapObject_GetDzFromDir(pdir);

    int fx = MapObject_GetX(followerObj);
    int fz = MapObject_GetZ(followerObj);
    if (facingX != fx || facingZ != fz) {
        return FALSE;
    }

    MapObject *playerObj = PlayerAvatar_GetMapObject(fieldSystem->playerAvatar);
    if (playerObj != NULL) {
        int dy = MapObject_GetY(playerObj) - MapObject_GetY(followerObj);
        if (dy < 0) {
            dy = -dy;
        }
        if (dy > 2) {
            return FALSE;
        }
    }

    if (PlayerAvatar_CheckForceStopMovement(fieldSystem->playerAvatar) == TRUE) {
        PlayerAvatar_ForceStopMovement(fieldSystem->playerAvatar, pdir);
    }

    int oppDir = Direction_GetOpposite(pdir);
    MapObject_Face(followerObj, oppDir);
    MapObject_Turn(followerObj, oppDir);

    FollowMonTalkTaskCtx *ctx = Heap_AllocAtEnd(HEAP_ID_FIELD1, sizeof(FollowMonTalkTaskCtx));
    if (ctx == NULL) {
        return FALSE;
    }
    memset(ctx, 0, sizeof(FollowMonTalkTaskCtx));
    ctx->state = TALK_STATE_INIT;

    FieldSystem_CreateTask(fieldSystem, FollowMon_TalkFieldTask, ctx);
    return TRUE;
}

// ---------------------------------------------------------------------------
// Headless talk helper & fishing friendliness bonus
// ---------------------------------------------------------------------------

BOOL FollowMon_HeadlessTalk(FieldSystem *fieldSystem, int *outEmote, int *outMood, char *outMsg, int msgCap)
{
    if (fieldSystem == NULL || !FollowMon_IsActive() || FollowMon_IsHidden()) {
        return FALSE;
    }

    MapObject *followerObj = FollowMon_GetMapObject(fieldSystem);
    if (followerObj != NULL && fieldSystem->playerAvatar != NULL) {
        int px = PlayerAvatar_GetXPos(fieldSystem->playerAvatar);
        int pz = PlayerAvatar_GetZPos(fieldSystem->playerAvatar);
        int fx = MapObject_GetX(followerObj);
        int fz = MapObject_GetZ(followerObj);
        int faceDir = GetDirectionBetweenPoints(fx, fz, px, pz);
        if (faceDir >= DIR_NORTH && faceDir <= DIR_EAST) {
            MapObject_Face(followerObj, faceDir);
            MapObject_Turn(followerObj, faceDir);
        }
    }

    FollowMonTalkOutcome outcome;
    FollowMon_EvaluateTalk(fieldSystem, &outcome);
    FollowMon_AdjustMood(outcome.moodDelta);

    int species = FollowMon_GetSpecies();
    if (species > SPECIES_NONE) {
        Sound_PlayPokemonCry((u16)species, 0);
    }
    FollowMon_SpawnEmote(fieldSystem, outcome.emote);

    if (outEmote != NULL) {
        *outEmote = (int)outcome.emote;
    }
    if (outMood != NULL) {
        *outMood = FollowMon_GetMood();
    }
    if (outMsg != NULL && msgCap > 0) {
        snprintf(outMsg, (size_t)msgCap, "%s", outcome.message);
    }
    return TRUE;
}

int FollowMon_GetFishingBonus(FieldSystem *fieldSystem)
{
    if (fieldSystem == NULL || fieldSystem->saveData == NULL) {
        return 0;
    }
    if (!FollowMon_IsActive() || FollowMon_IsHidden()) {
        return 0;
    }

    int slot = FollowMon_GetActivePartySlot();
    if (slot < 0) {
        return 0;
    }

    Party *party = SaveData_GetParty(fieldSystem->saveData);
    if (party == NULL || slot >= Party_GetCurrentCount(party)) {
        return 0;
    }

    Pokemon *mon = Party_GetPokemonBySlotIndex(party, slot);
    if (mon == NULL) {
        return 0;
    }

    u32 friendship = Pokemon_GetValue(mon, MON_DATA_FRIENDSHIP, NULL);
    int mood = FollowMon_GetMood();

    int bonus = 5; // +5% baseline bite re-roll bonus when follower is active
    if (friendship >= 150u) {
        bonus += 5;
    }
    if (friendship >= 200u && mood >= 20) {
        bonus += 5;
    }
    return bonus;
}
