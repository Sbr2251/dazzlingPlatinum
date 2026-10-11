#include "macros/scrcmd.inc"
#include "res/text/bank/solaceon_town.h"


    ScriptEntry _004F
    ScriptEntry _0062
    ScriptEntry _0093
    ScriptEntry _00A6
    ScriptEntry _00B9
    ScriptEntry _00CC
    ScriptEntry _0123
    ScriptEntry _013A
    ScriptEntry _0151
    ScriptEntry _0034
    ScriptEntry _0032
    ScriptEntry _0168
    ScriptEntry SolaceonTown_Arc2WallPhotos
    ScriptEntry SolaceonTown_Arc2WallPonyta
    ScriptEntry SolaceonTown_Arc2WallElias
    ScriptEntry SolaceonTown_Arc2WallBanner
    ScriptEntry SolaceonTown_Arc2WallTeo
    ScriptEntry SolaceonTown_Arc2IndraCutaway
    ScriptEntryEnd

// Arc 2 (s-celestic), 2.16a: the memorial wall (P1: sign events on the fence west of the main road,
// x 556, z 652-656, read from the road facing west; the wall art is P2) and the Indra cutaway.
// The cutaway plays the first time the player comes down the road from Route 210 at state 44 (coord row at
// the town's north edge): 47 at the start, 49 at the end. Map-local hide flag: FLAG_UNK_0x0030 = Indra.
// The stock Barry run-in at the south exit (VAR_UNK_0x4073) is switched off from Arc 2 on.
#define LOCALID_ARC2_INDRA 21

_0032:
    End

_0034:
    SetFlag FLAG_UNK_0x0030
    CallIfGe VAR_ARC2_PROGRESS, 1, SolaceonTown_Arc2NoBarry
    CheckDaycareHasEgg VAR_MAP_LOCAL_0
    GoToIfNe VAR_MAP_LOCAL_0, FALSE, _0047
    End

_0047:
    SetObjectEventDir 3, DIR_EAST
    End

SolaceonTown_Arc2NoBarry:
    SetVar VAR_UNK_0x4073, 1
    Return

SolaceonTown_Arc2WallPhotos:
    GoToIfLt VAR_ARC2_PROGRESS, 44, SolaceonTown_Arc2WallEnd
    LockAll
    Message SolaceonTown_Text_Arc2WallPhotos
    GoTo SolaceonTown_Arc2WallClose
    End

SolaceonTown_Arc2WallPonyta:
    GoToIfLt VAR_ARC2_PROGRESS, 44, SolaceonTown_Arc2WallEnd
    LockAll
    Message SolaceonTown_Text_Arc2WallPonyta
    GoTo SolaceonTown_Arc2WallClose
    End

SolaceonTown_Arc2WallElias:
    GoToIfLt VAR_ARC2_PROGRESS, 44, SolaceonTown_Arc2WallEnd
    LockAll
    Message SolaceonTown_Text_Arc2WallElias
    GoTo SolaceonTown_Arc2WallClose
    End

SolaceonTown_Arc2WallBanner:
    GoToIfLt VAR_ARC2_PROGRESS, 44, SolaceonTown_Arc2WallEnd
    LockAll
    Message SolaceonTown_Text_Arc2WallBanner
    GoTo SolaceonTown_Arc2WallClose
    End

SolaceonTown_Arc2WallTeo:
    GoToIfLt VAR_ARC2_PROGRESS, 49, SolaceonTown_Arc2WallEnd
    LockAll
    Message SolaceonTown_Text_Arc2WallTeo
    GoTo SolaceonTown_Arc2WallClose
    End

SolaceonTown_Arc2WallClose:
    WaitABXPadPress
    CloseMessage
    ReleaseAll
SolaceonTown_Arc2WallEnd:
    End

// 2.16a: shown to the player only. The player is put at the wall and hidden; Indra pins up Teo's card.
SolaceonTown_Arc2IndraCutaway:
    LockAll
    SetVar VAR_ARC2_PROGRESS, 47
    FadeScreenOut
    WaitFadeScreen
    SetPosition LOCALID_PLAYER, 558, 0, 654, DIR_WEST
    ApplyMovement LOCALID_PLAYER, SolaceonTown_Arc2Movement_Hide
    WaitMovement
    ClearFlag FLAG_UNK_0x0030
    AddObject LOCALID_ARC2_INDRA
    LockObject LOCALID_ARC2_INDRA
    WaitTime 15, VAR_RESULT
    FadeScreenIn
    WaitFadeScreen
    WaitTime 20, VAR_RESULT
    ApplyMovement LOCALID_ARC2_INDRA, SolaceonTown_Arc2Movement_PinCard
    WaitMovement
    PlayFanfare SEQ_SE_DP_KON
    WaitTime 20, VAR_RESULT
    Message SolaceonTown_Text_Arc2IndraAnotherName
    Message SolaceonTown_Text_Arc2IndraSomebodyHasTo
    Message SolaceonTown_Text_Arc2IndraMorningDoor
    Message SolaceonTown_Text_Arc2IndraHandsShake
    Message SolaceonTown_Text_Arc2IndraKeepTheDoor
    CloseMessage
    ApplyMovement LOCALID_ARC2_INDRA, SolaceonTown_Arc2Movement_IndraLeave
    WaitMovement
    RemoveObject LOCALID_ARC2_INDRA
    WaitTime 20, VAR_RESULT
    FadeScreenOut
    WaitFadeScreen
    SetPosition LOCALID_PLAYER, 557, 0, 654, DIR_WEST
    ApplyMovement LOCALID_PLAYER, SolaceonTown_Arc2Movement_Show
    WaitMovement
    FadeScreenIn
    WaitFadeScreen
    SetVar VAR_ARC2_PROGRESS, 49
    Message SolaceonTown_Text_Arc2WallTeo
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
SolaceonTown_Arc2Movement_Hide:
    SetInvisible
    EndMovement

    .balign 4, 0
SolaceonTown_Arc2Movement_Show:
    SetVisible
    FaceWest
    EndMovement

    .balign 4, 0
SolaceonTown_Arc2Movement_PinCard:
    FaceWest
    Delay8
    WalkOnSpotSlowWest
    EndMovement

    .balign 4, 0
SolaceonTown_Arc2Movement_IndraLeave:
    Delay8 2
    WalkNormalSouth 2
    WalkNormalEast 3
    WalkNormalSouth 4
    EndMovement

_004F:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 3
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0062:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfBadgeAcquired BADGE_ID_RELIC, _0088
    Message 4
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0088:
    Message 5
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0093:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 6
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_00A6:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 7
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_00B9:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 8
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_00CC:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    CheckPoketchAppRegistered POKETCH_APPID_POKEMONHISTORY, VAR_RESULT
    GoToIfEq VAR_RESULT, 1, _0118
    GetLocalDexSeenCount VAR_RESULT
    GoToIfLt VAR_RESULT, 50, _010D
    Message 10
    SetVar VAR_0x8004, POKETCH_APPID_POKEMONHISTORY
    GivePoketchApp
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_010D:
    Message 9
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0118:
    Message 11
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0123:
    ShowMapSign 12
    End

_013A:
    ShowLandmarkSign 13
    End

_0151:
    ShowLandmarkSign 14
    End

_0168:
    LockAll
    ApplyMovement LOCALID_PLAYER, _0218
    WaitMovement
    SetRivalBGM
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    SetObjectEventPos 18, VAR_0x8004, 0x295
    ClearFlag FLAG_UNK_0x021E
    AddObject 18
    LockObject 18
    ApplyMovement LOCALID_PLAYER, _0228
    ApplyMovement 18, _01E8
    WaitMovement
    Message 0
    CloseMessage
    ApplyMovement 18, _01F0
    WaitMovement
    BufferRivalName 0
    BufferPlayerName 1
    Message 1
    ApplyMovement 18, _0208
    WaitMovement
    Message 2
    CloseMessage
    ApplyMovement 18, _0210
    WaitMovement
    RemoveObject 18
    FadeToDefaultMusic2
    SetVar VAR_UNK_0x4073, 1
    ReleaseAll
    End

    .balign 4, 0
_01E8:
    WalkFastSouth 7
    EndMovement

    .balign 4, 0
_01F0:
    WalkOnSpotFastWest
    Delay8
    WalkOnSpotFastEast
    Delay8
    WalkOnSpotFastSouth
    EndMovement

    .balign 4, 0
_0208:
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
_0210:
    WalkFastNorth 7
    EndMovement

    .balign 4, 0
_0218:
    Delay8
    EmoteExclamationMark
    Delay8 3
    EndMovement

    .balign 4, 0
_0228:
    FaceNorth
    EndMovement
