#include "macros/scrcmd.inc"
#include "res/text/bank/dw_lost_tower.h"

// Arc 2 rift: MAP_HEADER_DW_LOST_TOWER (R0 stub; owner rift-b). docs/arc2/rift_contract.md is the contract:
//   entry   overworld script warps here: Warp MAP_HEADER_DW_LOST_TOWER, 0, 20, 12, DIR_WEST
//   exit    Warp MAP_HEADER_ROUTE_209_LOST_TOWER_2F, 0, 5, 8, DIR_WEST
//   calm    totem calmed sets VAR_ARC2_PROGRESS = 95
// The stub has no puzzle: the coord event at (17,12) (three steps west of the entry) runs the exit.

    ScriptEntry DWLostTower_OnTransition
    ScriptEntry DWLostTower_Exit
    ScriptEntryEnd

DWLostTower_OnTransition:
    InitPersistedMapFeaturesForDistortionWorld
    End

DWLostTower_Exit:
    LockAll
    Message DWLostTower_Text_StubExit
    WaitABXPadPress
    CloseMessage
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut
    WaitFadeScreen
    ScrCmd_320
    ReturnToField
    Warp MAP_HEADER_ROUTE_209_LOST_TOWER_2F, 0, 5, 8, DIR_WEST
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End
