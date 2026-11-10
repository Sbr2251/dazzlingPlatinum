#include "macros/scrcmd.inc"
#include "res/text/bank/acuity_lakefront.h"
#include "res/field/maps/locals/acuity_lakefront.h"
#include "constants/totem_battle.h"


    ScriptEntry AcuityLakefront_OnTransition
    ScriptEntry AcuityLakefront_OnLoad
    ScriptEntry AcuityLakefront_ArrowSignpostLakeAcuity
    ScriptEntry AcuityLakefront_CoordEvent_Rival
    ScriptEntry TotemMamoswine_Encounter
    ScriptEntryEnd

AcuityLakefront_OnLoad:
    GoToIfUnset FLAG_TEAM_GALACTIC_LEFT_LAKE_VERITY, AcuityLakefront_RemoveWarpsLakeAcuityNormal
    GoToIfSet FLAG_TEAM_GALACTIC_LEFT_LAKE_VERITY, AcuityLakefront_RemoveWarpsLakeAcuityLowWater
    End

AcuityLakefront_RemoveWarpsLakeAcuityNormal:
    SetWarpEventPos WARP_LAKE_ACUITY_1, 305, 229
    SetWarpEventPos WARP_LAKE_ACUITY_2, 306, 229
    End

AcuityLakefront_RemoveWarpsLakeAcuityLowWater:
    SetWarpEventPos WARP_LAKE_ACUITY_LOW_WATER_1, 305, 229
    SetWarpEventPos WARP_LAKE_ACUITY_LOW_WATER_2, 306, 229
    End

AcuityLakefront_OnTransition:
    CheckBadgeAcquired BADGE_ID_ICICLE, VAR_MAP_LOCAL_0x00
    CallIfEq VAR_MAP_LOCAL_0x00, TRUE, AcuityLakefront_SetVeilstoneGymMaylene
    GoToIfUnset FLAG_TEAM_GALACTIC_LEFT_LAKE_VERITY, AcuityLakefront_RemoveWarpsLakeAcuityNormal
    GoToIfSet FLAG_TEAM_GALACTIC_LEFT_LAKE_VERITY, AcuityLakefront_RemoveWarpsLakeAcuityLowWater
    End

AcuityLakefront_SetVeilstoneGymMaylene:
    SetFlag FLAG_HIDE_SNOWPOINT_CITY_POKECENTER_1F_MAYLENE
    ClearFlag FLAG_HIDE_VEILSTONE_CITY_GYM_MAYLENE
    Return

AcuityLakefront_ArrowSignpostLakeAcuity:
    ShowArrowSign AcuityLakefront_Text_SignLakeAcuityAhead
    End

AcuityLakefront_CoordEvent_Rival:
    LockAll
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    AddFreeCamera VAR_0x8004, VAR_0x8005
    ApplyFreeCameraMovement AcuityLakefront_Movement_CameraMoveNorth
    WaitMovement
    WaitTime 15, VAR_RESULT
    BufferRivalName 0
    BufferPlayerName 1
    Message AcuityLakefront_Text_CantClimbWithoutBadge
    CloseMessage
    ApplyMovement LOCALID_RIVAL, AcuityLakefront_Movement_RivalLeave
    WaitMovement
    RemoveObject LOCALID_RIVAL
    ApplyFreeCameraMovement AcuityLakefront_Movement_CameraMoveSouth
    WaitMovement
    RestoreCamera
    SetVar VAR_ACUITY_LAKEFRONT_STATE, 1
    ReleaseAll
    End

    .balign 4, 0
AcuityLakefront_Movement_CameraMoveNorth:
    WalkNormalNorth 6
    EndMovement

    .balign 4, 0
AcuityLakefront_Movement_CameraMoveSouth:
    WalkNormalSouth 6
    EndMovement

    .balign 4, 0
AcuityLakefront_Movement_RivalLeave:
    WalkNormalNorth 3
    WalkNormalWest
    WalkNormalNorth 4
    EndMovement

TotemMamoswine_Encounter:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    WaitSE SE_CONFIRM_sseq_3
    PlayBattleMusic BATTLE_WILD_POKEMON_sseq
    PlayCry SPECIES_MAMOSWINE
    WaitCry
    SetFlag FLAG_MAP_LOCAL_REMOVE_OBJECT
    StartTotemBattle TOTEM_ENCOUNTER_MAMOSWINE
    ClearFlag FLAG_MAP_LOCAL_REMOVE_OBJECT
    CheckWonBattle VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, TotemMamoswine_Encounter_LostBattle
    SetFlag FLAG_TOTEM_MAMOSWINE_DEFEATED
    SetFlag FLAG_HIDE_TOTEM_MAMOSWINE
    RemoveObject VAR_LAST_TALKED
    ReleaseAll
    End

TotemMamoswine_Encounter_LostBattle:
    BlackOutFromBattle
    ReleaseAll
    End

    .balign 4, 0
