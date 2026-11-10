#include "macros/scrcmd.inc"
#include "res/text/bank/valley_windworks_building.h"
#include "res/field/maps/locals/valley_windworks_building.h"

// Arc 2 (s-floaroma), scene 2.9: the cold site and leak L1. Reads VAR_ARC2_PROGRESS 21, sets 22.
// Stock Mars, Charon, the grunts and the twin are hidden for good (FLAG_MAP_LOCAL_0x3E, map-local temp, set every
// load); the Mars coord event and the fleeing-grunt frame script are gone. The scientist (local 2) is the
// "Windworks Worker" by the turbines.
// Locals added: 8 Ruth, 9 Cyrus (shown at 21, FLAG_MAP_LOCAL_HIDE_OBSTACLE_16 map-local temp), 10 Minun (PIKACHU sprite as a
// stand-in; shown from 21 until it flees: FLAG_MAP_LOCAL_HIDE_OBSTACLE_17 map-local temp, FLAG_ARC2_FLOAROMA_A = FLAG_ARC2_FLOAROMA_A
// once it fled), 11 the cage (ECLIPSE_CRATE placeholder).
// Ledger L1 writes VAR_ARC2_SUSPECT: Cyrus +0, Garius +4, Ruth +8, Bad luck (or B) +12, answered +512.
#define LOCALID_WORKER     2
#define LOCALID_ARC2_RUTH  8
#define LOCALID_ARC2_CYRUS 9
#define LOCALID_ARC2_MINUN 10
#define FLAG_ARC2_FLOAROMA_MINUN_FLED FLAG_ARC2_FLOAROMA_A

// Arc 2, workstream echo (R3): the Resonator echo at the cold site (S8 Echo stage). From the second calmed totem on
// (FLAG_TOTEM_VESPIQUEN_DEFEATED) and with the Resonator, examining the bolt holes replays the site once, as ghosts
// (src/field_move_tasks.c, FieldMoves_EchoGhostDraw): the Plusle strapped into a frame over the bolts, its sparks
// drawn off; the hurried packing; the Plusle carried out of the loading door while the Minun calls from the cage.
// No one comments; it's what the player sees. Nothing else changes, so it never blocks progress.
//   Flag: FLAG_ARC2_ECHO_WINDWORKS = FLAG_ARC1_SPARE_B (P2 pool), set when the echo has played.
//   Map-local: FLAG_MAP_LOCAL_0x17 hides the ghost actors (set every load, cleared only while the echo plays: AddObject
//   checks it); VAR_MAP_LOCAL_0x05 is their opacity (0 = off).
//   Ghost actors (object events with fixed local IDs 0xC0-0xC4, script-only): the frame and the Plusle on the bolt
//   holes (13,8), a grunt beside them (14,8, or 12,8 when the player stands at 14,8), then in the corridor the grunt
//   (15,15) and the Plusle (16,15) heading for the loading door (12,16), and the Minun at the cage (17,15, in front of it); a free
//   camera drops to the corridor for that part (the text box would hide it) and comes back up at the end.
#define FLAG_ARC2_ECHO_WINDWORKS FLAG_ARC1_SPARE_B
#define LOCALID_ECHO_FRAME  0xC0
#define LOCALID_ECHO_PLUSLE 0xC1
#define LOCALID_ECHO_GRUNT  0xC2
#define LOCALID_ECHO_MINUN  0xC3
#define ECHO_OPACITY        18


    ScriptEntry ValleyWindworksBuilding_OnTransition
    ScriptEntry ValleyWindworksBuilding_OnFrame_FirstEntry
    ScriptEntry ValleyWindworksBuilding_GruntM
    ScriptEntry ValleyWindworksBuilding_CoordEvent_Mars
    ScriptEntry ValleyWindworksBuilding_ScientistPapa
    ScriptEntry ValleyWindworksBuilding_Twin
    ScriptEntry ValleyWindworksBuilding_PCWest
    ScriptEntry ValleyWindworksBuilding_PCEast
    ScriptEntry ValleyWindworksBuilding_Arc2Ruth
    ScriptEntry ValleyWindworksBuilding_Arc2Cyrus
    ScriptEntry ValleyWindworksBuilding_Arc2Minun
    ScriptEntry ValleyWindworksBuilding_Arc2Cage
    ScriptEntry ValleyWindworksBuilding_Arc2BoltHoles
    ScriptEntry ValleyWindworksBuilding_Arc2Generator
    ScriptEntry ValleyWindworksBuilding_Arc2DragMarks
    ScriptEntryEnd

ValleyWindworksBuilding_OnTransition:
    SetFlag FLAG_FIRST_ARRIVAL_VALLEY_WINDWORKS
    SetFlag FLAG_MAP_LOCAL_0x17
    SetVar VAR_OBJ_GFX_ID_0, OBJ_EVENT_GFX_DP_PLAYER_F /* Ruth placeholder (D1) */
    SetFlag FLAG_MAP_LOCAL_0x3E
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
    CallIfEq VAR_ARC2_PROGRESS, 21, ValleyWindworksBuilding_Arc2ShowRuthCyrus
    GoToIfLt VAR_ARC2_PROGRESS, 21, ValleyWindworksBuilding_Arc2TransitionEnd
    GoToIfSet FLAG_ARC2_FLOAROMA_MINUN_FLED, ValleyWindworksBuilding_Arc2TransitionEnd
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
ValleyWindworksBuilding_Arc2TransitionEnd:
    End

ValleyWindworksBuilding_Arc2ShowRuthCyrus:
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    Return

ValleyWindworksBuilding_SetGirlAndPapaPositions:
    SetObjectEventPos LOCALID_LITTLE_GIRL, 21, 5
    SetObjectEventDir LOCALID_LITTLE_GIRL, DIR_WEST
    SetObjectEventMovementType LOCALID_LITTLE_GIRL, MOVEMENT_TYPE_LOOK_WEST
    SetObjectEventPos LOCALID_SCIENTIST_PAPA, 18, 4
    SetObjectEventDir LOCALID_SCIENTIST_PAPA, DIR_SOUTH
    SetObjectEventMovementType LOCALID_SCIENTIST_PAPA, MOVEMENT_TYPE_LOOK_SOUTH
    End

ValleyWindworksBuilding_OnFrame_FirstEntry:
    LockAll
    ApplyMovement LOCALID_GALACTIC_GRUNT_1, ValleyWindworksBuilding_Movement_GalacticGrunt1NoticePlayer
    WaitMovement
    Message ValleyWindworksBuilding_Text_GotToAlertCommander
    CloseMessage
    ApplyMovement LOCALID_GALACTIC_GRUNT_1, ValleyWindworksBuilding_Movement_GalacticGrunt1Leave
    ApplyMovement LOCALID_PLAYER, ValleyWindworksBuilding_Movement_PlayerWatchGalacticGrunt1Leave
    WaitMovement
    RemoveObject LOCALID_GALACTIC_GRUNT_1
    SetVar VAR_VALLEY_WINDWORKS_TEAM_GALACTIC_STATE, 1
    ReleaseAll
    End

    .balign 4, 0
ValleyWindworksBuilding_Movement_GalacticGrunt1NoticePlayer:
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_GalacticGrunt1Leave:
    WalkFastWest 9
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_PlayerWatchGalacticGrunt1Leave:
    Delay8
    WalkOnSpotNormalWest
    EndMovement

ValleyWindworksBuilding_GruntM:
    NPCMessage ValleyWindworksBuilding_Text_CommanderWillSmooshYou
    End

ValleyWindworksBuilding_CoordEvent_Mars:
    LockAll
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 6, ValleyWindworksBuilding_MarsNoticeAndWalkToPlayer
    GoToIfEq VAR_0x8005, 7, ValleyWindworksBuilding_MarsNoticePlayer
    End

ValleyWindworksBuilding_MarsNoticeAndWalkToPlayer:
    ApplyMovement LOCALID_MARS, ValleyWindworksBuilding_Movement_MarsNoticeAndWalkToPlayer
    WaitMovement
    GoTo ValleyWindworksBuilding_Mars
    End

ValleyWindworksBuilding_MarsNoticePlayer:
    ApplyMovement LOCALID_MARS, ValleyWindworksBuilding_Movement_MarsNoticePlayer
    WaitMovement
    GoTo ValleyWindworksBuilding_Mars
    End

ValleyWindworksBuilding_Mars:
    Message ValleyWindworksBuilding_Text_LetsHaveABattle
    CloseMessage
    StartTrainerBattle TRAINER_COMMANDER_MARS_VALLEY_WINDWORKS
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, ValleyWindworksBuilding_BlackOut
    Message ValleyWindworksBuilding_Text_IMessedThatOneUp
    CloseMessage
    ApplyMovement LOCALID_CHARON, ValleyWindworksBuilding_Movement_CharonWalkOnSpotSouth
    WaitMovement
    WaitTime 15, VAR_RESULT
    Message ValleyWindworksBuilding_Text_LoseToAChild
    ApplyMovement LOCALID_MARS, ValleyWindworksBuilding_Movement_MarsWalkOnSpotNorth
    WaitMovement
    Message ValleyWindworksBuilding_Text_WillYouShutIt
    ApplyMovement LOCALID_MARS, ValleyWindworksBuilding_Movement_MarsWalkOnSpotWest
    WaitMovement
    Message ValleyWindworksBuilding_Text_LeaveForTheTimeBeing
    CloseMessage
    FadeScreenOut
    WaitFadeScreen
    RemoveObject LOCALID_MARS
    RemoveObject LOCALID_CHARON
    RemoveObject LOCALID_GRUNT_M
    RemoveObject LOCALID_GALACTIC_GRUNT_2
    RemoveObject LOCALID_GALACTIC_GRUNT_3
    SetFlag FLAG_HIDE_ROUTE_205_SOUTH_GRUNTS
    ClearFlag FLAG_HIDE_ROUTE_205_SOUTH_YOUNGSTER
    SetVar VAR_VALLEY_WINDWORKS_STATE, 2
    SetFlag FLAG_DAILY_WON_AGAINST_VALLEY_WINDWORKS_OUTSIDE_DRIFLOON
    FadeScreenIn
    WaitFadeScreen
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 6, ValleyWindworksBuilding_ScientistPapaWalkToPlayerZ6
    GoToIfEq VAR_0x8005, 7, ValleyWindworksBuilding_ScientistPapaWalkToPlayerZ7
    End

ValleyWindworksBuilding_ScientistPapaWalkToPlayerZ6:
    ApplyMovement LOCALID_SCIENTIST_PAPA, ValleyWindworksBuilding_Movement_ScientistPapaWalkToPlayerZ6
    WaitMovement
    GoTo ValleyWindworksBuilding_FinallySeeMyDaughterAgain
    End

ValleyWindworksBuilding_ScientistPapaWalkToPlayerZ7:
    ApplyMovement LOCALID_SCIENTIST_PAPA, ValleyWindworksBuilding_Movement_ScientistPapaWalkToPlayerZ7
    WaitMovement
    GoTo ValleyWindworksBuilding_FinallySeeMyDaughterAgain
    End

ValleyWindworksBuilding_FinallySeeMyDaughterAgain:
    Message ValleyWindworksBuilding_Text_FinallySeeMyDaughterAgain
    CloseMessage
    SetFlag FLAG_HIDE_ROUTE_205_SOUTH_LITTLE_GIRL
    ClearFlag FLAG_HIDE_VALLEY_WINDWORKS_BUILDING_LITTLE_GIRL
    SetObjectEventMovementType LOCALID_LITTLE_GIRL, MOVEMENT_TYPE_LOOK_WEST
    AddObject LOCALID_LITTLE_GIRL
    LockObject LOCALID_LITTLE_GIRL
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 6, ValleyWindworksBuilding_LittleGirlWalkToScientistPapaZ6
    GoToIfEq VAR_0x8005, 7, ValleyWindworksBuilding_LittleGirlWalkToScientistPapaZ7
    End

ValleyWindworksBuilding_LittleGirlWalkToScientistPapaZ6:
    ApplyMovement LOCALID_LITTLE_GIRL, ValleyWindworksBuilding_Movement_LittleGirlWalkToScientistPapaZ6
    ApplyMovement LOCALID_SCIENTIST_PAPA, ValleyWindworksBuilding_Movement_ScientistPapaWalkOnSpotSouth
    WaitMovement
    GoTo ValleyWindworksBuilding_YuckPapaYoureStinky
    End

ValleyWindworksBuilding_LittleGirlWalkToScientistPapaZ7:
    ApplyMovement LOCALID_LITTLE_GIRL, ValleyWindworksBuilding_Movement_LittleGirlWalkToScientistPapaZ7
    ApplyMovement LOCALID_SCIENTIST_PAPA, ValleyWindworksBuilding_Movement_ScientistPapaWalkOnSpotNorth
    WaitMovement
    GoTo ValleyWindworksBuilding_YuckPapaYoureStinky
    End

ValleyWindworksBuilding_YuckPapaYoureStinky:
    Message ValleyWindworksBuilding_Text_YuckPapaYoureStinky
    CloseMessage
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 6, ValleyWindworksBuilding_ScientistPapaTurnInSpotFaceSouth
    GoToIfEq VAR_0x8005, 7, ValleyWindworksBuilding_ScientistPapaTurnInSpotFaceNorth
    End

ValleyWindworksBuilding_ScientistPapaTurnInSpotFaceSouth:
    ApplyMovement LOCALID_SCIENTIST_PAPA, ValleyWindworksBuilding_Movement_ScientistPapaTurnInSpotFaceSouth
    WaitMovement
    GoTo ValleyWindworksBuilding_BalloonPokemonWillVisitAgain
    End

ValleyWindworksBuilding_ScientistPapaTurnInSpotFaceNorth:
    ApplyMovement LOCALID_SCIENTIST_PAPA, ValleyWindworksBuilding_Movement_ScientistPapaTurnInSpotFaceNorth
    WaitMovement
    GoTo ValleyWindworksBuilding_BalloonPokemonWillVisitAgain
    End

ValleyWindworksBuilding_BalloonPokemonWillVisitAgain:
    Message ValleyWindworksBuilding_Text_SorryWorkingNonstop
    Message ValleyWindworksBuilding_Text_BalloonPokemonWillVisitAgain
    WaitButton
    CloseMessage
    SetVar VAR_VALLEY_WINDWORKS_LOOKER_STATE, 1
    ClearFlag FLAG_HIDE_VALLEY_WINDWORKS_OUTSIDE_LOOKER
    SetVar VAR_VALLEY_WINDWORKS_TEAM_GALACTIC_STATE, 2
    SetFlag FLAG_ALT_MUSIC_VALLEY_WINDWORKS_BUILDING
    ReleaseAll
    End

ValleyWindworksBuilding_BlackOut:
    BlackOutFromBattle
    ReleaseAll
    End

    .balign 4, 0
ValleyWindworksBuilding_Movement_LittleGirlWalkToScientistPapaZ6:
    WalkFastEast 4
    WalkFastNorth
    WalkFastEast 6
    WalkOnSpotFastNorth
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_LittleGirlWalkToScientistPapaZ7:
    WalkFastEast 4
    WalkFastNorth 2
    WalkFastEast 6
    WalkOnSpotFastSouth
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_ScientistPapaWalkToPlayerZ6:
    WalkNormalSouth 3
    WalkNormalWest
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_ScientistPapaWalkToPlayerZ7:
    WalkNormalSouth 4
    WalkNormalWest
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_ScientistPapaWalkOnSpotSouth:
    Delay8 6
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_ScientistPapaWalkOnSpotNorth:
    Delay8 6
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_ScientistPapaTurnInSpotFaceSouth:
    FaceEast
    Delay8 2
    FaceWest
    Delay8 2
    FaceSouth
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_ScientistPapaTurnInSpotFaceNorth:
    FaceEast
    Delay8 2
    FaceWest
    Delay8 2
    FaceNorth
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_MarsNoticeAndWalkToPlayer:
    EmoteExclamationMark
    WalkNormalNorth
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_MarsNoticePlayer:
    EmoteExclamationMark
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_MarsWalkOnSpotNorth:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_MarsWalkOnSpotWest:
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_CharonWalkOnSpotSouth:
    WalkOnSpotNormalSouth
    EndMovement

ValleyWindworksBuilding_ScientistPapa:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfEq VAR_ARC2_PROGRESS, 21, ValleyWindworksBuilding_Arc2Worker
    GoTo ValleyWindworksBuilding_ValleyWindworksUsesTurbines
    Message 11
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

ValleyWindworksBuilding_ValleyWindworksUsesTurbines:
    Message ValleyWindworksBuilding_Text_ValleyWindworksUsesTurbines
    WaitButton
    CloseMessage
    ReleaseAll
    End

ValleyWindworksBuilding_Twin:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfGe VAR_VALLEY_WINDWORKS_TEAM_GALACTIC_STATE, 3, ValleyWindworksBuilding_BlowBalloonPokemonAway
    Message ValleyWindworksBuilding_Text_BalloonPokemonWillVisitAgain
    WaitButton
    CloseMessage
    ReleaseAll
    End

ValleyWindworksBuilding_BlowBalloonPokemonAway:
    Message ValleyWindworksBuilding_Text_BlowBalloonPokemonAway
    WaitButton
    CloseMessage
    ReleaseAll
    End

ValleyWindworksBuilding_PCWest:
    GoTo ValleyWindworksBuilding_PC
    End

ValleyWindworksBuilding_PCEast:
    GoTo ValleyWindworksBuilding_PC
    End

ValleyWindworksBuilding_PC:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    // Arc 2: the stock Galactic orders (14) are gone; the screen just shows numbers.
    GoTo ValleyWindworksBuilding_PCScreenFilledWithNumbers
    Message 14
    GoTo ValleyWindworksBuilding_PCEnd
    End

ValleyWindworksBuilding_PCScreenFilledWithNumbers:
    Message ValleyWindworksBuilding_Text_PCScreenFilledWithNumbers
    GoTo ValleyWindworksBuilding_PCEnd
    End

ValleyWindworksBuilding_PCEnd:
    WaitButton
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0

ValleyWindworksBuilding_Arc2Worker:
    Message ValleyWindworksBuilding_Text_Arc2WorkerDarkCoats
    WaitABPadPress
    CloseMessage
    Message ValleyWindworksBuilding_Text_Arc2RuthACall
    WaitABPadPress
    CloseMessage
    // Ruth looks at Cyrus
    ApplyMovement LOCALID_ARC2_RUTH, ValleyWindworksBuilding_Movement_Arc2FaceEast
    ApplyMovement LOCALID_ARC2_CYRUS, ValleyWindworksBuilding_Movement_Arc2FaceWest
    WaitMovement
    WaitTime 15, VAR_RESULT
    Message ValleyWindworksBuilding_Text_Arc2CyrusSawLights
    WaitABPadPress
    CloseMessage
    Message ValleyWindworksBuilding_Text_Arc2RuthCouldHaveWokenUs
    WaitABPadPress
    CloseMessage
    // ledger L1
    ApplyMovement LOCALID_ARC2_RUTH, ValleyWindworksBuilding_Movement_Arc2FaceNorth
    ApplyMovement LOCALID_PLAYER, ValleyWindworksBuilding_Movement_Arc2FaceWest
    WaitMovement
    Message ValleyWindworksBuilding_Text_Arc2RuthWhoToldThem
    InitLocalTextMenu 31, 9, 0, VAR_RESULT
    SetMenuXOriginToRight
    AddMenuEntryImm ValleyWindworksBuilding_Text_Arc2LedgerCyrus, 0
    AddMenuEntryImm ValleyWindworksBuilding_Text_Arc2LedgerGarius, 1
    AddMenuEntryImm ValleyWindworksBuilding_Text_Arc2LedgerRuth, 2
    AddMenuEntryImm ValleyWindworksBuilding_Text_Arc2LedgerBadLuck, 3
    ShowMenu
    SetVar VAR_0x8008, VAR_RESULT
    AddVar VAR_ARC2_SUSPECT, 512
    GoToIfEq VAR_0x8008, 0, ValleyWindworksBuilding_Arc2PickCyrus
    GoToIfEq VAR_0x8008, 1, ValleyWindworksBuilding_Arc2PickGarius
    GoToIfEq VAR_0x8008, 2, ValleyWindworksBuilding_Arc2PickRuth
    GoTo ValleyWindworksBuilding_Arc2PickBadLuck
    End

ValleyWindworksBuilding_Arc2PickCyrus:
    Message ValleyWindworksBuilding_Text_Arc2ReactCyrus
    GoTo ValleyWindworksBuilding_Arc2LedgerDone
    End

ValleyWindworksBuilding_Arc2PickGarius:
    AddVar VAR_ARC2_SUSPECT, 4
    BufferRivalName 0
    Message ValleyWindworksBuilding_Text_Arc2ReactGarius
    GoTo ValleyWindworksBuilding_Arc2LedgerDone
    End

ValleyWindworksBuilding_Arc2PickRuth:
    AddVar VAR_ARC2_SUSPECT, 8
    Message ValleyWindworksBuilding_Text_Arc2ReactRuth
    GoTo ValleyWindworksBuilding_Arc2LedgerDone
    End

ValleyWindworksBuilding_Arc2PickBadLuck:
    AddVar VAR_ARC2_SUSPECT, 12
    Message ValleyWindworksBuilding_Text_Arc2ReactBadLuck
    GoTo ValleyWindworksBuilding_Arc2LedgerDone
    End

ValleyWindworksBuilding_Arc2LedgerDone:
    WaitABPadPress
    CloseMessage
    Message ValleyWindworksBuilding_Text_Arc2RuthEternaForestNext
    WaitABPadPress
    CloseMessage
    SetVar VAR_ARC2_PROGRESS, 22
    // stock bookkeeping: the Windworks trouble is over (Floaroma NPCs move on to their later lines)
    SetVar VAR_VALLEY_WINDWORKS_TEAM_GALACTIC_STATE, 3
    // Ruth and Cyrus head out toward Eterna Forest
    FadeScreenOut
    WaitFadeScreen
    RemoveObject LOCALID_ARC2_RUTH
    RemoveObject LOCALID_ARC2_CYRUS
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

ValleyWindworksBuilding_Arc2Ruth:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message ValleyWindworksBuilding_Text_Arc2RuthLookAround
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

ValleyWindworksBuilding_Arc2Cyrus:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    Message ValleyWindworksBuilding_Text_Arc2CyrusEllipsis
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

// The Minun (local 10, at 16,14) beside its cage (local 11, at 17,14). It bolts for the loading door (12,16).
ValleyWindworksBuilding_Arc2Minun:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    GoToIfSet FLAG_ARC2_FLOAROMA_MINUN_FLED, ValleyWindworksBuilding_Arc2CageEmpty
    Message ValleyWindworksBuilding_Text_Arc2Cage
    WaitABPadPress
    CloseMessage
    PlayCry SPECIES_MINUN
    ApplyMovement LOCALID_ARC2_MINUN, ValleyWindworksBuilding_Movement_Arc2MinunStartle
    WaitMovement
    Message ValleyWindworksBuilding_Text_Arc2MinunCry
    WaitCry
    WaitABPadPress
    CloseMessage
    GetPlayerDir VAR_RESULT
    GoToIfEq VAR_RESULT, DIR_EAST, ValleyWindworksBuilding_Arc2MinunRunSouth
    ApplyMovement LOCALID_ARC2_MINUN, ValleyWindworksBuilding_Movement_Arc2MinunRunWest
    WaitMovement
    GoTo ValleyWindworksBuilding_Arc2MinunGone
    End

ValleyWindworksBuilding_Arc2MinunRunSouth:
    ApplyMovement LOCALID_ARC2_MINUN, ValleyWindworksBuilding_Movement_Arc2MinunRunSouth
    WaitMovement
ValleyWindworksBuilding_Arc2MinunGone:
    RemoveObject LOCALID_ARC2_MINUN
    SetFlag FLAG_ARC2_FLOAROMA_MINUN_FLED
    Message ValleyWindworksBuilding_Text_Arc2MinunRanOut
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

ValleyWindworksBuilding_Arc2Cage:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    GoToIfUnset FLAG_ARC2_FLOAROMA_MINUN_FLED, ValleyWindworksBuilding_Arc2CageWithMinun
ValleyWindworksBuilding_Arc2CageEmpty:
    Message ValleyWindworksBuilding_Text_Arc2CageEmpty
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

ValleyWindworksBuilding_Arc2CageWithMinun:
    GoToIfLt VAR_ARC2_PROGRESS, 21, ValleyWindworksBuilding_Arc2CageEmpty
    GoTo ValleyWindworksBuilding_Arc2Minun
    End

ValleyWindworksBuilding_Arc2BoltHoles:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message ValleyWindworksBuilding_Text_Arc2BoltHoles
    WaitABPadPress
    CloseMessage
    Call ValleyWindworksBuilding_Echo
    ReleaseAll
    End

ValleyWindworksBuilding_Arc2Generator:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message ValleyWindworksBuilding_Text_Arc2Generator
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

ValleyWindworksBuilding_Arc2DragMarks:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message ValleyWindworksBuilding_Text_Arc2DragMarks
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
ValleyWindworksBuilding_Movement_Arc2FaceEast:
    FaceEast
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_Arc2FaceWest:
    FaceWest
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_Arc2FaceNorth:
    FaceNorth
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_Arc2MinunStartle:
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_Arc2MinunRunWest:
    WalkFastWest 4
    WalkFastSouth 2
    SetInvisible
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_Arc2MinunRunSouth:
    WalkFastSouth
    WalkFastWest 4
    WalkFastSouth
    SetInvisible
    EndMovement

// ------------------------------------------------------------------------------------------------ echo (S8)
// Called from the bolt holes (13,8) after their line; the player is beside them (any side).
ValleyWindworksBuilding_Echo:
    GoToIfUnset FLAG_TOTEM_VESPIQUEN_DEFEATED, ValleyWindworksBuilding_EchoReturn
    GoToIfSet FLAG_ARC2_ECHO_WINDWORKS, ValleyWindworksBuilding_EchoReturn
    CheckItem ITEM_RESONATOR, 1, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, ValleyWindworksBuilding_EchoReturn
    Message ValleyWindworksBuilding_Text_EchoHum
    WaitABPadPress
    CloseMessage
    // The grunt stands on the side away from the player
    SetObjectEventPos LOCALID_ECHO_GRUNT, 14, 8
    SetObjectEventDir LOCALID_ECHO_GRUNT, DIR_WEST
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8004, 14, ValleyWindworksBuilding_EchoGruntWest
    // The echo starts: a white flash, then the frame, the Plusle and the grunt fade in
    PlaySE SEQ_SE_PL_SYUWA_sseq
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    SetVar VAR_MAP_LOCAL_0x05, 1
    ClearFlag FLAG_MAP_LOCAL_0x17
    AddObject LOCALID_ECHO_FRAME
    AddObject LOCALID_ECHO_PLUSLE
    AddObject LOCALID_ECHO_GRUNT
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    WaitSE SEQ_SE_PL_SYUWA_sseq
    Call ValleyWindworksBuilding_EchoFadeIn
    WaitTime 15, VAR_RESULT
    Call ValleyWindworksBuilding_EchoSpark
    Message ValleyWindworksBuilding_Text_EchoFrame
    WaitABPadPress
    CloseMessage
    Call ValleyWindworksBuilding_EchoSpark
    Message ValleyWindworksBuilding_Text_EchoSparks
    WaitABPadPress
    CloseMessage
    // The grunt hurries
    ApplyMovement LOCALID_ECHO_GRUNT, ValleyWindworksBuilding_Movement_EchoHurry
    WaitMovement
    Message ValleyWindworksBuilding_Text_EchoPacking
    WaitABPadPress
    CloseMessage
    // The echo skips: the frame is gone; the grunt and the Plusle are in the corridor, the Minun in the cage
    PlaySE SEQ_SE_PL_SYUWA_sseq
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    RemoveObject LOCALID_ECHO_FRAME
    RemoveObject LOCALID_ECHO_PLUSLE
    RemoveObject LOCALID_ECHO_GRUNT
    // The camera drops to the corridor (z 13), above the text box
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    SetVar VAR_0x8006, VAR_0x8005
    AddFreeCamera VAR_0x8004, VAR_0x8005
    Call ValleyWindworksBuilding_EchoCameraDown
    WaitTime 2, VAR_RESULT
    ClearFlag FLAG_MAP_LOCAL_0x17 // RemoveObject set it again
    SetObjectEventPos LOCALID_ECHO_GRUNT, 15, 15
    SetObjectEventDir LOCALID_ECHO_GRUNT, DIR_WEST
    SetObjectEventPos LOCALID_ECHO_PLUSLE, 16, 15
    SetObjectEventDir LOCALID_ECHO_PLUSLE, DIR_WEST
    AddObject LOCALID_ECHO_GRUNT
    AddObject LOCALID_ECHO_PLUSLE
    AddObject LOCALID_ECHO_MINUN
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    WaitSE SEQ_SE_PL_SYUWA_sseq
    Message ValleyWindworksBuilding_Text_EchoCarried
    WaitABPadPress
    CloseMessage
    ApplyMovement LOCALID_ECHO_GRUNT, ValleyWindworksBuilding_Movement_EchoGruntOut
    ApplyMovement LOCALID_ECHO_PLUSLE, ValleyWindworksBuilding_Movement_EchoPlusleOut
    WaitMovement
    PlayCry SPECIES_MINUN
    ApplyMovement LOCALID_ECHO_MINUN, ValleyWindworksBuilding_Movement_EchoMinunCalls
    WaitMovement
    WaitCry
    Message ValleyWindworksBuilding_Text_EchoMinun
    WaitABPadPress
    CloseMessage
    // It fades; the ghosts go, the camera comes back up to the player, and the opacity is back to 0 before the
    // player moves again
    Call ValleyWindworksBuilding_EchoFadeOut
    RemoveObject LOCALID_ECHO_GRUNT
    RemoveObject LOCALID_ECHO_PLUSLE
    RemoveObject LOCALID_ECHO_MINUN
    Call ValleyWindworksBuilding_EchoCameraUp
    RestoreCamera
    SetFlag FLAG_MAP_LOCAL_0x17
    SetVar VAR_MAP_LOCAL_0x05, 0
    WaitTime 2, VAR_RESULT
    SetFlag FLAG_ARC2_ECHO_WINDWORKS
    Message ValleyWindworksBuilding_Text_EchoFade
    WaitABPadPress
    CloseMessage
ValleyWindworksBuilding_EchoReturn:
    Return

// The free camera steps south until it is at z 13 (VAR_0x8005 tracks it), then back north to the player's row
// (VAR_0x8006).
ValleyWindworksBuilding_EchoCameraDown:
    GoToIfGe VAR_0x8005, 13, ValleyWindworksBuilding_EchoReturn
    ApplyFreeCameraMovement ValleyWindworksBuilding_Movement_EchoCameraSouth
    WaitMovement
    AddVar VAR_0x8005, 1
    GoTo ValleyWindworksBuilding_EchoCameraDown
    End

ValleyWindworksBuilding_EchoCameraUp:
    GoToIfLe VAR_0x8005, VAR_0x8006, ValleyWindworksBuilding_EchoReturn
    ApplyFreeCameraMovement ValleyWindworksBuilding_Movement_EchoCameraNorth
    WaitMovement
    SubVar VAR_0x8005, 1
    GoTo ValleyWindworksBuilding_EchoCameraUp
    End

ValleyWindworksBuilding_EchoGruntWest:
    SetObjectEventPos LOCALID_ECHO_GRUNT, 12, 8
    SetObjectEventDir LOCALID_ECHO_GRUNT, DIR_EAST
    Return

// The Plusle sparks: its cry, a white flicker, a jolt
ValleyWindworksBuilding_EchoSpark:
    PlayCry SPECIES_PLUSLE
    ApplyMovement LOCALID_ECHO_PLUSLE, ValleyWindworksBuilding_Movement_EchoJolt
    FadeScreenOut FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    FadeScreenIn FADE_SCREEN_SPEED_FAST, COLOR_WHITE
    WaitFadeScreen
    ShakeCamera 4, 1
    WaitMovement
    WaitCry
    Return

ValleyWindworksBuilding_EchoFadeIn:
    AddVar VAR_MAP_LOCAL_0x05, 1
    WaitTime 1, VAR_RESULT
    GoToIfLt VAR_MAP_LOCAL_0x05, ECHO_OPACITY, ValleyWindworksBuilding_EchoFadeIn
    Return

ValleyWindworksBuilding_EchoFadeOut:
    SubVar VAR_MAP_LOCAL_0x05, 1
    WaitTime 1, VAR_RESULT
    GoToIfGt VAR_MAP_LOCAL_0x05, 1, ValleyWindworksBuilding_EchoFadeOut
    Return

    .balign 4, 0
ValleyWindworksBuilding_Movement_EchoCameraSouth:
    WalkFastSouth
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_EchoCameraNorth:
    WalkNormalNorth
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_EchoJolt:
    JumpOnSpotFastSouth
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_EchoHurry:
    WalkOnSpotFastSouth
    WalkOnSpotFastNorth
    WalkOnSpotFastSouth
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_EchoGruntOut:
    WalkFastWest 3
    WalkFastSouth
    SetInvisible
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_EchoPlusleOut:
    Delay4
    WalkFastWest 4
    WalkFastSouth
    SetInvisible
    EndMovement

    .balign 4, 0
ValleyWindworksBuilding_Movement_EchoMinunCalls:
    JumpOnSpotFastSouth
    Delay8
    JumpOnSpotFastSouth
    EndMovement
