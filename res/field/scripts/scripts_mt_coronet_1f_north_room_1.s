#include "macros/scrcmd.inc"
#include "res/text/bank/mt_coronet_1f_north_room_1.h"


// Arc 2 (s-celestic), 2.14: Route 211's Coronet tunnel. The group crosses this room (the Route 211 West to
// Route 211 East passage), so the scene plays here rather than in mt_coronet_1f_tunnel_room.
// Map-local hide flags: FLAG_UNK_0x0030 = Ruth/Cyrus/Garius (shown at VAR_ARC2_PROGRESS 39 only),
// FLAG_UNK_0x0031 = the violet flash under the grate (scene only).
// Gate (R0 finding, rift_contract.md): the West-East passage needs Rock Smash (rock at 10,36) and Strength
// (boulder at 18,39). Strength is Arc 3, so that boulder (stock STRENGTH_BOULDER_9) is deleted from the events
// JSON; the objects after it moved down one local ID (the stock grunts 16/17 are now 15/16). The rock stays as
// the Resonator Rock Smash beat (Coal Badge + Hitmonlee totem).
#define LOCALID_ARC2_RUTH   18
#define LOCALID_ARC2_CYRUS  19
#define LOCALID_ARC2_GARIUS 20
#define LOCALID_ARC2_FLASH  22

    ScriptEntry _000A
    ScriptEntry _001D
    ScriptEntry MtCoronet1FNorthRoom1_Arc2Scene
    ScriptEntry MtCoronet1FNorthRoom1_Arc2Grate
    ScriptEntry MtCoronet1FNorthRoom1_OnTransition
    ScriptEntryEnd

MtCoronet1FNorthRoom1_OnTransition:
    // Stock Galactic grunts by the B1F stairs (14,10)/(14,11): their stock hide flag is set at Lake Verity,
    // which Arc 1 no longer does, so they stay hidden here.
    SetFlag FLAG_UNK_0x029A
    SetFlag FLAG_UNK_0x0031
    GoToIfEq VAR_ARC2_PROGRESS, 39, MtCoronet1FNorthRoom1_OnTransitionEnd
    SetFlag FLAG_UNK_0x0030
MtCoronet1FNorthRoom1_OnTransitionEnd:
    End

MtCoronet1FNorthRoom1_Arc2Grate:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message MtCoronet1FNorthRoom1_Text_Arc2Grate
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

// 2.14: runs from the frame table as soon as the player comes in from Route 211 West at state 39.
MtCoronet1FNorthRoom1_Arc2Scene:
    LockAll
    ApplyMovement LOCALID_PLAYER, MtCoronet1FNorthRoom1_Arc2Movement_FaceEast
    ApplyMovement LOCALID_ARC2_RUTH, MtCoronet1FNorthRoom1_Arc2Movement_FaceWest
    WaitMovement
    Message MtCoronet1FNorthRoom1_Text_Arc2RuthHot
    ApplyMovement LOCALID_ARC2_GARIUS, MtCoronet1FNorthRoom1_Arc2Movement_FaceNorth
    WaitMovement
    BufferRivalName 0
    Message MtCoronet1FNorthRoom1_Text_Arc2GariusBroken
    CloseMessage
    ApplyMovement LOCALID_ARC2_CYRUS, MtCoronet1FNorthRoom1_Arc2Movement_FaceEast
    WaitMovement
    WaitTime 60, VAR_RESULT
    ApplyMovement LOCALID_ARC2_RUTH, MtCoronet1FNorthRoom1_Arc2Movement_FaceEast
    WaitMovement
    Message MtCoronet1FNorthRoom1_Text_Arc2RuthCyrus
    ApplyMovement LOCALID_ARC2_CYRUS, MtCoronet1FNorthRoom1_Arc2Movement_FaceWest
    WaitMovement
    Message MtCoronet1FNorthRoom1_Text_Arc2CyrusNothing
    CloseMessage
    ApplyMovement LOCALID_ARC2_RUTH, MtCoronet1FNorthRoom1_Arc2Movement_WalkAway
    ApplyMovement LOCALID_ARC2_CYRUS, MtCoronet1FNorthRoom1_Arc2Movement_WalkAway
    WaitMovement
    // Only the player sees it: something violet-black, deep under the grate, for a moment.
    ApplyMovement LOCALID_PLAYER, MtCoronet1FNorthRoom1_Arc2Movement_FaceSouth
    WaitMovement
    WaitTime 20, VAR_RESULT
    ClearFlag FLAG_UNK_0x0031
    AddObject LOCALID_ARC2_FLASH
    WaitTime 4, VAR_RESULT
    RemoveObject LOCALID_ARC2_FLASH
    WaitTime 30, VAR_RESULT
    SetVar VAR_ARC2_PROGRESS, 40
    FadeScreenOut
    WaitFadeScreen
    RemoveObject LOCALID_ARC2_RUTH
    RemoveObject LOCALID_ARC2_CYRUS
    RemoveObject LOCALID_ARC2_GARIUS
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

    .balign 4, 0
MtCoronet1FNorthRoom1_Arc2Movement_FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
MtCoronet1FNorthRoom1_Arc2Movement_FaceWest:
    FaceWest
    EndMovement

    .balign 4, 0
MtCoronet1FNorthRoom1_Arc2Movement_FaceNorth:
    FaceNorth
    EndMovement

    .balign 4, 0
MtCoronet1FNorthRoom1_Arc2Movement_FaceSouth:
    FaceSouth
    EndMovement

    .balign 4, 0
MtCoronet1FNorthRoom1_Arc2Movement_WalkAway:
    WalkNormalNorth
    EndMovement

_000A:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 0
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_001D:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    ApplyMovement 15, _0058
    WaitMovement
    Message 1
    ApplyMovement 16, _0060
    WaitMovement
    Message 2
    CloseMessage
    ApplyMovement 15, _0068
    ApplyMovement 16, _0068
    WaitMovement
    ReleaseAll
    End

    .balign 4, 0
_0058:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_0060:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
_0068:
    WalkOnSpotNormalWest
    EndMovement
