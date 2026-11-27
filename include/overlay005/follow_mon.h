#ifndef POKEPLATINUM_FOLLOW_MON_H
#define POKEPLATINUM_FOLLOW_MON_H

#include <nitro/fx/fx.h>
#include <nitro/types.h>

#include "field/field_system_decl.h"
#include "struct_decls/map_object.h"

#ifdef __cplusplus
extern "C" {
#endif

// Dedicated virtual graphics ID and local ID for the following Pokemon object.
// Note: LOCALID_FOLLOWER (0xF2) in constants/scrcmd.h is used for partner
// trainers (Cheryl/Riley/etc.), so the following Pokemon uses 0xFE.
#define OBJ_EVENT_GFX_FOLLOW_MON 0x7F00
#define LOCALID_FOLLOW_MON       0xFE

typedef struct Billboard Billboard;
typedef struct BillboardList BillboardList;
typedef struct ResourceHeap ResourceHeap;

// Emote bubble kinds for follower talk interactions.
typedef enum FollowMonEmoteKind {
    FOLLOW_MON_EMOTE_NONE = 0,
    FOLLOW_MON_EMOTE_EXCLAMATION,
    FOLLOW_MON_EMOTE_QUESTION,
    FOLLOW_MON_EMOTE_HEART,
    FOLLOW_MON_EMOTE_MUSIC,
    FOLLOW_MON_EMOTE_HAPPY,
    FOLLOW_MON_EMOTE_SWEAT,
    FOLLOW_MON_EMOTE_ANGRY,
    FOLLOW_MON_EMOTE_POISON,
    FOLLOW_MON_EMOTE_SLEEPY,
    FOLLOW_MON_EMOTE_SURPRISE,
    FOLLOW_MON_EMOTE_COUNT
} FollowMonEmoteKind;

// FieldMap lifecycle hooks (src/overlay005/fieldmap.c)
void FollowMon_OnFieldInit(FieldSystem *fieldSystem);
void FollowMon_OnFieldExit(FieldSystem *fieldSystem);
void FollowMon_Update(FieldSystem *fieldSystem);
void FollowMon_OnZoneChange(FieldSystem *fieldSystem);

// Player movement / warp hooks (src/player_move.c)
void FollowMon_OnPlayerStep(FieldSystem *fieldSystem, int oldX, int oldZ, int newX, int newZ, int dir, int actionSpeed, BOOL isJump);
void FollowMon_OnPlayerWarp(FieldSystem *fieldSystem);

// Talk trigger hook (src/overlay005/field_control.c)
BOOL FollowMon_TryTalk(FieldSystem *fieldSystem);

// Mood & fishing hooks (src/overlay005/fishing.c & general)
void FollowMon_AdjustMood(int delta);
int FollowMon_GetMood(void);
int FollowMon_GetFishingBonus(FieldSystem *fieldSystem);

// MapObject & Billboard pipeline hooks (src/map_object.c, src/overlay005/ov5_021ECE40.c)
BOOL FollowMon_IsFollowerObject(const MapObject *mapObj);
void FollowMon_BindObjectRenderer(MapObject *mapObj);
Billboard *FollowMon_CreateBillboard(MapObject *mapObj, BillboardList *list, ResourceHeap *modelHeap);
void FollowMon_DestroyBillboard(MapObject *mapObj, Billboard **billboard);

// State queries & headless test helpers (src/port/headless_game.c)
BOOL FollowMon_IsAvailable(void);
BOOL FollowMon_IsActive(void);
BOOL FollowMon_IsHidden(void);
int FollowMon_GetSpecies(void);
BOOL FollowMon_IsShiny(void);
BOOL FollowMon_IsLarge(void);
void FollowMon_GetPosition(int *outX, int *outZ, int *outDir);
BOOL FollowMon_HeadlessTalk(FieldSystem *fieldSystem, int *outEmote, int *outMood, char *outMsg, int msgCap);

// Shared helpers used by follow_mon_talk.c
MapObject *FollowMon_GetMapObject(FieldSystem *fieldSystem);
void FollowMon_SetTalkBubbleOffset(fx32 jumpY);
u8 FollowMon_GetShinyLeafCount(int slotIndex);
void FollowMon_IncrementShinyLeafCount(int slotIndex);
int FollowMon_GetActivePartySlot(void);
u32 FollowMon_GetStepCounter(void);
void *FollowMon_ReadArchiveMember(int memberIdx, u32 *outSize);
int FollowMon_GetArchiveMemberCount(void);
void FollowMon_TalkOnFieldExit(void);
void FollowMon_TalkUpdate(FieldSystem *fieldSystem);

#ifdef __cplusplus
}
#endif

#endif // POKEPLATINUM_FOLLOW_MON_H
