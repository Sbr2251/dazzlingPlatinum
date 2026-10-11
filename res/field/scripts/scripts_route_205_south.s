#include "macros/scrcmd.inc"
#include "res/text/bank/route_205_south.h"

// Arc 2 (s-floaroma): the stock Galactic bridge guards (locals 12, 13) and the twin asking for her papa
// (local 18) are hidden for good (FLAG_UNK_0x003F, map-local temp, set every load); their coord events are gone.
// While Ruth and Cyrus wait inside the Windworks (VAR_ARC2_PROGRESS 21), the bridge north (x216-218, z653)
// turns the player back.
// Arc 2 quests (R3, S11): the Plusle/Minun reunion. The Minun that fled the Windworks (FLAG_ARC2_FLOAROMA_A)
// waits by a crate that fell off an Eclipse truck at the Windworks turn-off (crate 221,658; Minun 220,658).
// The first step into the junction (x213-223, z658-663) buzzes the Resonator once per map load.
// Opening the crate frees the Plusle; both join the party as a pair (needs 2 free party slots, else a
// come-back line and the crate stays shut). Flag: FLAG_UNK_0x0920 = FLAG_ARC2_LEAD_A = pair reunited (lead's block).
// Map-local: FLAG_UNK_0x0030 hides the Minun and the crate, FLAG_UNK_0x0031 the Plusle (shown only in the scene);
// VAR_MAP_LOCAL_1 = 1 arms the buzz coord event.
#define FLAG_QUESTS_PAIR_REUNITED FLAG_ARC2_LEAD_A
#define LOCALID_QUESTS_MINUN  32
#define LOCALID_QUESTS_CRATE  33
#define LOCALID_QUESTS_PLUSLE 34


    ScriptEntry _002A
    ScriptEntry _00F8
    ScriptEntry _010B
    ScriptEntry _002C
    ScriptEntry _011E
    ScriptEntry _015D
    ScriptEntry _0070
    ScriptEntry _0280
    ScriptEntry _0297
    ScriptEntry _02AE
    ScriptEntry Route205South_Arc2WindworksGate
    ScriptEntry Route205South_QuestsMinun
    ScriptEntry Route205South_QuestsCrate
    ScriptEntry Route205South_QuestsBuzz
    ScriptEntryEnd

_002A:
    SetFlag FLAG_UNK_0x003F
    Call Route205South_QuestsOnTransition
    End

_002C:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    ApplyMovement 13, _0060
    WaitMovement
    Message 2
    CloseMessage
    ApplyMovement 12, _0068
    WaitMovement
    Call _00B6
    Message 4
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
_0060:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_0068:
    WalkOnSpotNormalSouth
    EndMovement

_0070:
    LockAll
    ApplyMovement 13, _00BC
    WaitMovement
    Message 2
    CloseMessage
    ApplyMovement 12, _00C4
    WaitMovement
    Message 3
    CloseMessage
    ApplyMovement 13, _00CC
    ApplyMovement LOCALID_PLAYER, _00EC
    WaitMovement
    ApplyMovement 12, _00E4
    WaitMovement
    Call _00B6
    ReleaseAll
    End

_00B6:
    SetFlag FLAG_UNK_0x007F
    Return

    .balign 4, 0
_00BC:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_00C4:
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_00CC:
    WalkFastEast
    WalkOnSpotFastSouth
    Delay8 2
    WalkNormalWest
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_00E4:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_00EC:
    WalkNormalSouth
    WalkOnSpotFastNorth
    EndMovement

_00F8:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 5
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_010B:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 6
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_011E:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfSet FLAG_UNK_0x0091, _0142
    Call _014D
    Message 0
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0142:
    Message 1
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_014D:
    SetFlag FLAG_UNK_0x01A1
    SetFlag FLAG_UNK_0x0091
    SetVar VAR_UNK_0x4089, 1
    Return

_015D:
    LockAll
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 0x293, _01A8
    GoToIfEq VAR_0x8005, 0x294, _01C2
    GoToIfEq VAR_0x8005, 0x295, _01DC
    GoToIfEq VAR_0x8005, 0x296, _01E2
    GoToIfEq VAR_0x8005, 0x297, _01FC
    End

_01A8:
    ApplyMovement 18, _0238
    WaitMovement
    ApplyMovement LOCALID_PLAYER, _0228
    WaitMovement
    GoTo _0216

_01C2:
    ApplyMovement 18, _024C
    WaitMovement
    ApplyMovement LOCALID_PLAYER, _0228
    WaitMovement
    GoTo _0216

_01DC:
    GoTo _0216

_01E2:
    ApplyMovement 18, _025C
    WaitMovement
    ApplyMovement LOCALID_PLAYER, _0230
    WaitMovement
    GoTo _0216

_01FC:
    ApplyMovement 18, _026C
    WaitMovement
    ApplyMovement LOCALID_PLAYER, _0230
    WaitMovement
    GoTo _0216

_0216:
    Call _014D
    Message 0
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
_0228:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_0230:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
_0238:
    WalkOnSpotNormalNorth
    EmoteExclamationMark
    Delay8
    WalkNormalNorth
    EndMovement

    .balign 4, 0
_024C:
    WalkOnSpotNormalNorth
    EmoteExclamationMark
    Delay8
    EndMovement

    .balign 4, 0
_025C:
    WalkOnSpotNormalSouth
    EmoteExclamationMark
    Delay8
    EndMovement

    .balign 4, 0
_026C:
    WalkOnSpotNormalSouth
    EmoteExclamationMark
    Delay8
    WalkNormalSouth
    EndMovement

_0280:
    ShowArrowSign 7
    End

_0297:
    ShowArrowSign 8
    End

_02AE:
    ShowScrollingSign 9
    End

    .balign 4, 0

Route205South_Arc2WindworksGate:
    LockAll
    Message Route205South_Text_Arc2WaitingAtWindworks
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_PLAYER, Route205South_Movement_Arc2StepBack
    WaitMovement
    ReleaseAll
    End

    .balign 4, 0
Route205South_Movement_Arc2StepBack:
    WalkNormalSouth
    EndMovement

Route205South_QuestsOnTransition:
    SetFlag FLAG_UNK_0x0030
    SetFlag FLAG_UNK_0x0031
    SetVar VAR_MAP_LOCAL_1, 0
    GoToIfUnset FLAG_ARC2_FLOAROMA_A, Route205South_QuestsReturn
    GoToIfSet FLAG_QUESTS_PAIR_REUNITED, Route205South_QuestsReturn
    ClearFlag FLAG_UNK_0x0030
    SetVar VAR_MAP_LOCAL_1, 1
Route205South_QuestsReturn:
    Return

Route205South_QuestsBuzz:
    LockAll
    SetVar VAR_MAP_LOCAL_1, 2
    CheckItem ITEM_RESONATOR, 1, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, Route205South_QuestsBuzzEnd
    PlayFanfare SEQ_SE_DP_BEEP
    Message Route205South_Text_QuestsBuzz
    WaitABXPadPress
    CloseMessage
Route205South_QuestsBuzzEnd:
    ReleaseAll
    End

Route205South_QuestsMinun:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    PlayCry SPECIES_MINUN
    Message Route205South_Text_QuestsMinunPaws
    WaitCry
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_QUESTS_MINUN, Route205South_Movement_QuestsFaceEast
    WaitMovement
    ReleaseAll
    End

Route205South_QuestsCrate:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message Route205South_Text_QuestsCrate
    WaitABXPadPress
    CheckItem ITEM_RESONATOR, 1, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, Route205South_QuestsCrateAsk
    PlayFanfare SEQ_SE_DP_BEEP
    Message Route205South_Text_QuestsCrateBuzz
    WaitABXPadPress
Route205South_QuestsCrateAsk:
    Message Route205South_Text_QuestsOpenCrate
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_NO, Route205South_QuestsCrateLeave
    GetPartyCount VAR_RESULT
    GoToIfGe VAR_RESULT, 5, Route205South_QuestsNoRoom
    CloseMessage
    PlayFanfare SEQ_SE_DP_KI_GASYAN
    WaitFanfare SEQ_SE_DP_KI_GASYAN
    RemoveObject LOCALID_QUESTS_CRATE
    ClearFlag FLAG_UNK_0x0031
    AddObject LOCALID_QUESTS_PLUSLE
    PlayCry SPECIES_PLUSLE
    Message Route205South_Text_QuestsPlusleTumbled
    WaitCry
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_QUESTS_MINUN, Route205South_Movement_QuestsHop
    ApplyMovement LOCALID_QUESTS_PLUSLE, Route205South_Movement_QuestsHopWest
    WaitMovement
    PlayCry SPECIES_MINUN
    Message Route205South_Text_QuestsPairCries
    WaitCry
    WaitABXPadPress
    Message Route205South_Text_QuestsWontLetGo
    WaitABXPadPress
    CloseMessage
    ApplyMovement LOCALID_QUESTS_MINUN, Route205South_Movement_QuestsFaceSouth
    ApplyMovement LOCALID_QUESTS_PLUSLE, Route205South_Movement_QuestsFaceSouth
    WaitMovement
    Message Route205South_Text_QuestsLookingAtYou
    WaitABXPadPress
    BufferPlayerName 0
    PlaySound SEQ_FANFA4
    Message Route205South_Text_QuestsReceivedPair
    WaitSound
    WaitABXPadPress
    CloseMessage
    GivePokemon SPECIES_PLUSLE, 18, ITEM_NONE, VAR_RESULT
    GivePokemon SPECIES_MINUN, 18, ITEM_NONE, VAR_RESULT
    SetFlag FLAG_QUESTS_PAIR_REUNITED
    SetVar VAR_MAP_LOCAL_1, 2
    RemoveObject LOCALID_QUESTS_PLUSLE
    RemoveObject LOCALID_QUESTS_MINUN
    SetFlag FLAG_UNK_0x0030
    SetFlag FLAG_UNK_0x0031
    ReleaseAll
    End

Route205South_QuestsNoRoom:
    Message Route205South_Text_QuestsNoRoom
    WaitABXPadPress
Route205South_QuestsCrateLeave:
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
Route205South_Movement_QuestsFaceEast:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
Route205South_Movement_QuestsFaceSouth:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
Route205South_Movement_QuestsHop:
    WalkOnSpotNormalEast
    JumpOnSpotFastEast
    JumpOnSpotFastEast
    EndMovement

    .balign 4, 0
Route205South_Movement_QuestsHopWest:
    WalkOnSpotNormalWest
    JumpOnSpotFastWest
    JumpOnSpotFastWest
    EndMovement
