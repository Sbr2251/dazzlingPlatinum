#include "macros/scrcmd.inc"
#include "res/text/bank/dw_route_213.h"

// Arc 2 rift: MAP_HEADER_DW_ROUTE_213 (R0 stub; owner rift-b). docs/arc2/rift_contract.md is the contract:
//   entry   overworld script warps here: Warp MAP_HEADER_DW_ROUTE_213, 0, 20, 12, DIR_WEST
//   exit    Warp MAP_HEADER_ROUTE_213, 0, 715, 831, DIR_SOUTH
//   calm    totem calmed sets VAR_ARC2_PROGRESS = 84
// The stub has no puzzle: the coord event at (17,12) (three steps west of the entry) runs the exit.

    ScriptEntry DWRoute213_OnTransition
    ScriptEntry DWRoute213_Exit
    ScriptEntryEnd

DWRoute213_OnTransition:
    InitPersistedMapFeaturesForDistortionWorld
    End

DWRoute213_Exit:
    LockAll
    Message DWRoute213_Text_StubExit
    WaitABXPadPress
    CloseMessage
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut
    WaitFadeScreen
    ScrCmd_320
    ReturnToField
    Warp MAP_HEADER_ROUTE_213, 0, 715, 831, DIR_SOUTH
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End
