#include "macros/scrcmd.inc"
#include "res/text/bank/floaroma_town.h"
#include "res/field/maps/locals/floaroma_town.h"

    ScriptEntry FloaromaTown_OnTransition
    ScriptEntry FloaromaTown_Grunts
    ScriptEntry FloaromaTown_SchoolKidM
    ScriptEntry FloaromaTown_LassWest
    ScriptEntry FloaromaTown_PokemonBreederF
    ScriptEntry FloaromaTown_LassEast
    ScriptEntry FloaromaTown_Camper
    ScriptEntry FloaromaTown_MapSignpost
    ScriptEntry FloaromaTown_SignboardFlowerShop
    ScriptEntry FloaromaTown_SignboardFloaromaMeadow
    ScriptEntry FloaromaTown_Beauty
    ScriptEntry FloaromaTown_Arc2EveningScene
    ScriptEntryEnd

FloaromaTown_OnTransition:
    SetFlag FLAG_HIDE_FLOAROMA_TOWN_GRUNTS
    SetVar VAR_OBJ_GFX_ID_0, OBJ_EVENT_GFX_DP_PLAYER_F /* Ruth placeholder (D1) */
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
    GoToIfNe VAR_ARC2_PROGRESS, 19, FloaromaTown_Arc2TransitionEnd
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_18
    End

FloaromaTown_Grunts:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    ApplyMovement LOCALID_GRUNT_M_WEST, FloaromaTown_Movement_WalkOnSpotEast
    WaitMovement
    Message FloaromaTown_Text_ThisDoesntSeemCool
    CloseMessage
    ApplyMovement LOCALID_GRUNT_M_EAST, FloaromaTown_Movement_WalkOnSpotWest
    WaitMovement
    Message FloaromaTown_Text_DontComplain
    WaitButton
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
FloaromaTown_Movement_WalkOnSpotEast:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
FloaromaTown_Movement_WalkOnSpotWest:
    WalkOnSpotNormalWest
    EndMovement

FloaromaTown_SchoolKidM:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    // Arc 2: the stock Galactic meadow lines are gone; she always says her flower line.
    GoTo FloaromaTown_OddlyPleasantMood
    End

FloaromaTown_OddlyPleasantMood:
    Message FloaromaTown_Text_OddlyPleasantMood
    WaitButton
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
FloaromaTown_Movement_SchoolKidMFaceNorth:
    FaceNorth
    Delay8 3
    EndMovement

FloaromaTown_LassWest:
    NPCMessage FloaromaTown_Text_ISimplyLoveItHere
    End

FloaromaTown_PokemonBreederF:
    NPCMessage FloaromaTown_Text_WelcomeToFloaroma
    End

FloaromaTown_LassEast:
    NPCMessage FloaromaTown_Text_BerriesCanBeFoodForPokemon
    End

FloaromaTown_Camper:
    NPCMessage FloaromaTown_Text_DrawnHereByHoney
    End

FloaromaTown_MapSignpost:
    ShowMapSign FloaromaTown_Text_MapSign
    End

FloaromaTown_SignboardFlowerShop:
    ShowLandmarkSign FloaromaTown_Text_SignFlowerShop
    End

FloaromaTown_SignboardFloaromaMeadow:
    ShowLandmarkSign FloaromaTown_Text_SignFlowerMeadow
    End

FloaromaTown_Beauty:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    FindPartySlotWithFatefulEncounterSpecies VAR_RESULT, SPECIES_SHAYMIN
    GoToIfEq VAR_RESULT, 0xFF, FloaromaTown_DoYouKnowGracideaFlowers
    CheckPartyHasSpecies VAR_RESULT, SPECIES_SHAYMIN
    GoToIfEq VAR_RESULT, FALSE, FloaromaTown_DoYouKnowGracideaFlowers
    CheckItem ITEM_GRACIDEA, 1, VAR_RESULT
    GoToIfNe VAR_RESULT, FALSE, FloaromaTown_GracideaFlowersBeenAroundLongTime
    Message FloaromaTown_Text_HaveGracideaFlowers
    SetVar VAR_0x8004, ITEM_GRACIDEA
    SetVar VAR_0x8005, 1
    CallCommonScript CommonScript_AddItemQuantityNoLineFeed
    CloseMessage
    ReleaseAll
    End

FloaromaTown_DoYouKnowGracideaFlowers:
    Message FloaromaTown_Text_DoYouKnowGracideaFlowers
    GoTo FloaromaTown_BeautyEnd
    End

FloaromaTown_GracideaFlowersBeenAroundLongTime:
    Message FloaromaTown_Text_GracideaFlowersBeenAroundLongTime
    GoTo FloaromaTown_BeautyEnd
    End

FloaromaTown_BeautyEnd:
    WaitButton
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0

FloaromaTown_Arc2TransitionEnd:
    End

FloaromaTown_Arc2EveningScene:
    LockAll
    // walk the player to (173,668), beside Ruth (the tree row at z670 hides anyone standing on z669)
    ApplyMovement LOCALID_PLAYER, FloaromaTown_Movement_Arc2StepNorth
    WaitMovement
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
FloaromaTown_Arc2WalkEastLoop:
    GoToIfGe VAR_0x8004, 173, FloaromaTown_Arc2AtRuth
    ApplyMovement LOCALID_PLAYER, FloaromaTown_Movement_Arc2StepEast
    WaitMovement
    AddVar VAR_0x8004, 1
    GoTo FloaromaTown_Arc2WalkEastLoop

FloaromaTown_Arc2AtRuth:
    ApplyMovement LOCALID_PLAYER, FloaromaTown_Movement_Arc2FaceEast
    ApplyMovement LOCALID_ARC2_RUTH, FloaromaTown_Movement_Arc2FaceWest
    WaitMovement
    Message FloaromaTown_Text_Arc2RuthSomethingAtWindworks
    WaitButton
    CloseMessage
    // Garius walks over from the shop, a jar of honey under his arm
    ApplyMovement LOCALID_ARC2_GARIUS, FloaromaTown_Movement_Arc2GariusWalkOver
    WaitMovement
    ApplyMovement LOCALID_PLAYER, FloaromaTown_Movement_Arc2FaceEast
    ApplyMovement LOCALID_ARC2_RUTH, FloaromaTown_Movement_Arc2FaceEast
    ApplyMovement LOCALID_ARC2_CYRUS, FloaromaTown_Movement_Arc2FaceEast
    WaitMovement
    BufferRivalName 0
    Message FloaromaTown_Text_Arc2GariusThroughTheForest
    WaitButton
    CloseMessage
    // he leaves north toward Eterna Forest (out the east road, Route 205)
    ApplyMovement LOCALID_ARC2_GARIUS, FloaromaTown_Movement_Arc2GariusLeave
    WaitMovement
    RemoveObject LOCALID_ARC2_GARIUS
    ApplyMovement LOCALID_ARC2_CYRUS, FloaromaTown_Movement_Arc2FaceWest
    ApplyMovement LOCALID_ARC2_RUTH, FloaromaTown_Movement_Arc2FaceEast
    WaitMovement
    Message FloaromaTown_Text_Arc2CyrusScoutTheRoad
    WaitButton
    CloseMessage
    // Cyrus walks off east into the dark; Ruth watches him go
    ApplyMovement LOCALID_ARC2_CYRUS, FloaromaTown_Movement_Arc2CyrusLeave
    ApplyMovement LOCALID_ARC2_RUTH, FloaromaTown_Movement_Arc2FaceEast
    WaitMovement
    RemoveObject LOCALID_ARC2_CYRUS
    WaitTime 30, VAR_RESULT
    ApplyMovement LOCALID_ARC2_RUTH, FloaromaTown_Movement_Arc2FaceWest
    WaitMovement
    Message FloaromaTown_Text_Arc2RuthGetSomeSleep
    WaitButton
    CloseMessage
    // night passes: heal, then morning at the Windworks gate (valley_windworks_outside runs the 20 scene)
    FadeScreenOut
    WaitFadeScreen
    HealParty
    SetVar VAR_ARC2_PROGRESS, 20
    Warp MAP_HEADER_VALLEY_WINDWORKS_OUTSIDE, 245, 658, DIR_NORTH
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

    .balign 4, 0
FloaromaTown_Movement_Arc2StepNorth:
    WalkNormalNorth
    EndMovement

    .balign 4, 0
FloaromaTown_Movement_Arc2StepEast:
    WalkNormalEast
    EndMovement

    .balign 4, 0
FloaromaTown_Movement_Arc2FaceNorth:
    FaceNorth
    EndMovement

    .balign 4, 0
FloaromaTown_Movement_Arc2FaceSouth:
    FaceSouth
    EndMovement

    .balign 4, 0
FloaromaTown_Movement_Arc2FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
FloaromaTown_Movement_Arc2FaceWest:
    FaceWest
    EndMovement

    .balign 4, 0
FloaromaTown_Movement_Arc2GariusWalkOver:
    WalkNormalSouth 15
    WalkNormalWest 3
    FaceWest
    EndMovement

    .balign 4, 0
FloaromaTown_Movement_Arc2GariusLeave:
    WalkNormalEast 3
    WalkNormalNorth 6
    WalkNormalEast 9
    EndMovement

    .balign 4, 0
FloaromaTown_Movement_Arc2CyrusLeave:
    WalkNormalEast 9
    EndMovement
