#include "macros/scrcmd.inc"
#include "res/text/bank/route_205_south.h"
#include "res/field/maps/locals/route_205_south.h"

// Arc 2 (s-floaroma): the stock Galactic bridge guards (locals 12, 13) and the twin asking for her papa
// (local 18) are hidden for good (FLAG_MAP_LOCAL_0x3E, map-local temp, set every load); their coord events are gone.
// While Ruth and Cyrus wait inside the Windworks (VAR_ARC2_PROGRESS 21), the bridge north (x216-218, z653)
// turns the player back.
// Arc 2 quests (R3, S11): the Plusle/Minun reunion. The Minun that fled the Windworks (FLAG_ARC2_FLOAROMA_A)
// waits by a crate that fell off an Eclipse truck at the Windworks turn-off (crate 221,658; Minun 220,658).
// The first step into the junction (x213-223, z658-663) buzzes the Resonator once per map load.
// Opening the crate frees the Plusle; both join the party as a pair (needs 2 free party slots, else a
// come-back line and the crate stays shut). Flag: FLAG_ARC2_LEAD_A = FLAG_ARC2_LEAD_A = pair reunited (lead's block).
// Map-local: FLAG_MAP_LOCAL_HIDE_OBSTACLE_16 hides the Minun and the crate, FLAG_MAP_LOCAL_HIDE_OBSTACLE_17 the Plusle (shown only in the scene);
// VAR_MAP_LOCAL_0x01 = 1 arms the buzz coord event.
#define FLAG_QUESTS_PAIR_REUNITED FLAG_ARC2_LEAD_A
#define LOCALID_QUESTS_MINUN  32
#define LOCALID_QUESTS_CRATE  33
#define LOCALID_QUESTS_PLUSLE 34


    ScriptEntry Route205South_OnTransition
    ScriptEntry Route205South_BugCatcher
    ScriptEntry Route205South_Youngster
    ScriptEntry Route205South_Grunts
    ScriptEntry Route205South_LittleGirl
    ScriptEntry Route205South_CoordEvent_LittleGirl
    ScriptEntry Route205South_CoordEvent_Grunts
    ScriptEntry Route205South_ArrowSignpostFloaromaTown
    ScriptEntry Route205South_ArrowSignpostEternaForest
    ScriptEntry Route205South_TrainerTipsSignpost
    ScriptEntry Route205South_Arc2WindworksGate
    ScriptEntry Route205South_QuestsMinun
    ScriptEntry Route205South_QuestsCrate
    ScriptEntry Route205South_QuestsBuzz
    ScriptEntryEnd

Route205South_OnTransition:
    SetFlag FLAG_MAP_LOCAL_0x3E
    Call Route205South_QuestsOnTransition
    End

Route205South_Grunts:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    ApplyMovement LOCALID_GRUNT_M_WEST, Route205South_Movement_GruntMWestWalkOnSpotSouth
    WaitMovement
    Message Route205South_Text_TeamGalacticConductingResearch
    CloseMessage
    ApplyMovement LOCALID_GRUNT_M_EAST, Route205South_Movement_GruntMEastWalkOnSpotSouth
    WaitMovement
    Call _00B6
    Message Route205South_Text_ResearchInvolvesCatchingPokemon2
    WaitButton
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
Route205South_Movement_GruntMWestWalkOnSpotSouth:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
Route205South_Movement_GruntMEastWalkOnSpotSouth:
    WalkOnSpotNormalSouth
    EndMovement

Route205South_CoordEvent_Grunts:
    LockAll
    ApplyMovement LOCALID_GRUNT_M_WEST, Route205South_Movement_GruntMWestWalkOnSpotEast
    WaitMovement
    Message Route205South_Text_TeamGalacticConductingResearch
    CloseMessage
    ApplyMovement LOCALID_GRUNT_M_EAST, Route205South_Movement_GruntMEastWalkOnSpotWest
    WaitMovement
    Message Route205South_Text_ResearchInvolvesCatchingPokemon1
    CloseMessage
    ApplyMovement LOCALID_GRUNT_M_WEST, Route205South_Movement_GruntMWestPushBackPlayer
    ApplyMovement LOCALID_PLAYER, Route205South_Movement_PlayerGetPushedBack
    WaitMovement
    ApplyMovement LOCALID_GRUNT_M_EAST, Route205South_Movement_GruntMEastTurnBackSouth
    WaitMovement
    Call _00B6
    ReleaseAll
    End

_00B6:
    SetFlag FLAG_DUMMY_0x007F
    Return

    .balign 4, 0
Route205South_Movement_GruntMWestWalkOnSpotEast:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
Route205South_Movement_GruntMEastWalkOnSpotWest:
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
Route205South_Movement_GruntMWestPushBackPlayer:
    WalkFastEast
    WalkOnSpotFastSouth
    Delay8 2
    WalkNormalWest
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
Route205South_Movement_GruntMEastTurnBackSouth:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
Route205South_Movement_PlayerGetPushedBack:
    WalkNormalSouth
    WalkOnSpotFastNorth
    EndMovement

Route205South_BugCatcher:
    NPCMessage Route205South_Text_ManyPoisonTypePokemon
    End

Route205South_Youngster:
    NPCMessage Route205South_Text_SlatherHoneyOnATree
    End

Route205South_LittleGirl:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfSet FLAG_TALKED_TO_ROUTE_205_SOUTH_LITTLE_GIRL, Route205South_IWantToSeeMyPapa
    Call Route205South_HideFloaromaTownGrunts
    Message Route205South_Text_HelpIWantToSeeMyPapa
    WaitButton
    CloseMessage
    ReleaseAll
    End

Route205South_IWantToSeeMyPapa:
    Message Route205South_Text_IWantToSeeMyPapa
    WaitButton
    CloseMessage
    ReleaseAll
    End

Route205South_HideFloaromaTownGrunts:
    SetFlag FLAG_HIDE_FLOAROMA_TOWN_GRUNTS
    SetFlag FLAG_TALKED_TO_ROUTE_205_SOUTH_LITTLE_GIRL
    SetVar VAR_VALLEY_WINDWORKS_STATE, 1
    Return

Route205South_CoordEvent_LittleGirl:
    LockAll
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 659, Route205South_LittleGirlNoticePlayerZ659
    GoToIfEq VAR_0x8005, 660, Route205South_LittleGirlNoticePlayerZ660
    GoToIfEq VAR_0x8005, 661, Route205South_DummyZ661 @ unreachable position
    GoToIfEq VAR_0x8005, 662, Route205South_LittleGirlNoticePlayerZ662
    GoToIfEq VAR_0x8005, 663, Route205South_LittleGirlNoticePlayerZ663
    End

Route205South_LittleGirlNoticePlayerZ659:
    ApplyMovement LOCALID_LITTLE_GIRL, Route205South_Movement_TwinNoticePlayerZ659
    WaitMovement
    ApplyMovement LOCALID_PLAYER, Route205South_Movement_PlayerWalkOnSpotSouth
    WaitMovement
    GoTo Route205South_HelpIWantToSeeMyPapa

Route205South_LittleGirlNoticePlayerZ660:
    ApplyMovement LOCALID_LITTLE_GIRL, Route205South_Movement_TwinNoticePlayerZ660
    WaitMovement
    ApplyMovement LOCALID_PLAYER, Route205South_Movement_PlayerWalkOnSpotSouth
    WaitMovement
    GoTo Route205South_HelpIWantToSeeMyPapa

Route205South_DummyZ661:
    GoTo Route205South_HelpIWantToSeeMyPapa

Route205South_LittleGirlNoticePlayerZ662:
    ApplyMovement LOCALID_LITTLE_GIRL, Route205South_Movement_TwinNoticePlayerZ662
    WaitMovement
    ApplyMovement LOCALID_PLAYER, Route205South_Movement_PlayerWalkOnSpotNorth
    WaitMovement
    GoTo Route205South_HelpIWantToSeeMyPapa

Route205South_LittleGirlNoticePlayerZ663:
    ApplyMovement LOCALID_LITTLE_GIRL, Route205South_Movement_TwinNoticePlayerZ663
    WaitMovement
    ApplyMovement LOCALID_PLAYER, Route205South_Movement_PlayerWalkOnSpotNorth
    WaitMovement
    GoTo Route205South_HelpIWantToSeeMyPapa

Route205South_HelpIWantToSeeMyPapa:
    Call Route205South_HideFloaromaTownGrunts
    Message Route205South_Text_HelpIWantToSeeMyPapa
    WaitButton
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
Route205South_Movement_PlayerWalkOnSpotSouth:
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
Route205South_Movement_PlayerWalkOnSpotNorth:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
Route205South_Movement_TwinNoticePlayerZ659:
    WalkOnSpotNormalNorth
    EmoteExclamationMark
    Delay8
    WalkNormalNorth
    EndMovement

    .balign 4, 0
Route205South_Movement_TwinNoticePlayerZ660:
    WalkOnSpotNormalNorth
    EmoteExclamationMark
    Delay8
    EndMovement

    .balign 4, 0
Route205South_Movement_TwinNoticePlayerZ662:
    WalkOnSpotNormalSouth
    EmoteExclamationMark
    Delay8
    EndMovement

    .balign 4, 0
Route205South_Movement_TwinNoticePlayerZ663:
    WalkOnSpotNormalSouth
    EmoteExclamationMark
    Delay8
    WalkNormalSouth
    EndMovement

Route205South_ArrowSignpostFloaromaTown:
    ShowArrowSign Route205South_Text_SignFloaromaTown
    End

Route205South_ArrowSignpostEternaForest:
    ShowArrowSign Route205South_Text_SignEternaForest
    End

Route205South_TrainerTipsSignpost:
    ShowScrollingSign Route205South_Text_TrainerTipsItemsAutomaticallySorted
    End

    .balign 4, 0

Route205South_Arc2WindworksGate:
    LockAll
    Message Route205South_Text_Arc2WaitingAtWindworks
    WaitABPadPress
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
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    SetVar VAR_MAP_LOCAL_0x01, 0
    GoToIfUnset FLAG_ARC2_FLOAROMA_A, Route205South_QuestsReturn
    GoToIfSet FLAG_QUESTS_PAIR_REUNITED, Route205South_QuestsReturn
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    SetVar VAR_MAP_LOCAL_0x01, 1
Route205South_QuestsReturn:
    Return

Route205South_QuestsBuzz:
    LockAll
    SetVar VAR_MAP_LOCAL_0x01, 2
    CheckItem ITEM_RESONATOR, 1, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, Route205South_QuestsBuzzEnd
    PlaySE SEQ_SE_DP_BEEP_sseq
    Message Route205South_Text_QuestsBuzz
    WaitABPadPress
    CloseMessage
Route205South_QuestsBuzzEnd:
    ReleaseAll
    End

Route205South_QuestsMinun:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    PlayCry SPECIES_MINUN
    Message Route205South_Text_QuestsMinunPaws
    WaitCry
    WaitABPadPress
    CloseMessage
    ApplyMovement LOCALID_QUESTS_MINUN, Route205South_Movement_QuestsFaceEast
    WaitMovement
    ReleaseAll
    End

Route205South_QuestsCrate:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message Route205South_Text_QuestsCrate
    WaitABPadPress
    CheckItem ITEM_RESONATOR, 1, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, Route205South_QuestsCrateAsk
    PlaySE SEQ_SE_DP_BEEP_sseq
    Message Route205South_Text_QuestsCrateBuzz
    WaitABPadPress
Route205South_QuestsCrateAsk:
    Message Route205South_Text_QuestsOpenCrate
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_NO, Route205South_QuestsCrateLeave
    GetPartyCount VAR_RESULT
    GoToIfGe VAR_RESULT, 5, Route205South_QuestsNoRoom
    CloseMessage
    PlaySE SEQ_SE_DP_KI_GASYAN_sseq
    WaitSE SEQ_SE_DP_KI_GASYAN_sseq
    RemoveObject LOCALID_QUESTS_CRATE
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    AddObject LOCALID_QUESTS_PLUSLE
    PlayCry SPECIES_PLUSLE
    Message Route205South_Text_QuestsPlusleTumbled
    WaitCry
    WaitABPadPress
    CloseMessage
    ApplyMovement LOCALID_QUESTS_MINUN, Route205South_Movement_QuestsHop
    ApplyMovement LOCALID_QUESTS_PLUSLE, Route205South_Movement_QuestsHopWest
    WaitMovement
    PlayCry SPECIES_MINUN
    Message Route205South_Text_QuestsPairCries
    WaitCry
    WaitABPadPress
    Message Route205South_Text_QuestsWontLetGo
    WaitABPadPress
    CloseMessage
    ApplyMovement LOCALID_QUESTS_MINUN, Route205South_Movement_QuestsFaceSouth
    ApplyMovement LOCALID_QUESTS_PLUSLE, Route205South_Movement_QuestsFaceSouth
    WaitMovement
    Message Route205South_Text_QuestsLookingAtYou
    WaitABPadPress
    BufferPlayerName 0
    PlayFanfare SEQ_FANFA4_sseq
    Message Route205South_Text_QuestsReceivedPair
    WaitFanfare
    WaitABPadPress
    CloseMessage
    GivePokemon SPECIES_PLUSLE, 18, ITEM_NONE, VAR_RESULT
    GivePokemon SPECIES_MINUN, 18, ITEM_NONE, VAR_RESULT
    SetFlag FLAG_QUESTS_PAIR_REUNITED
    SetVar VAR_MAP_LOCAL_0x01, 2
    RemoveObject LOCALID_QUESTS_PLUSLE
    RemoveObject LOCALID_QUESTS_MINUN
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    ReleaseAll
    End

Route205South_QuestsNoRoom:
    Message Route205South_Text_QuestsNoRoom
    WaitABPadPress
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
