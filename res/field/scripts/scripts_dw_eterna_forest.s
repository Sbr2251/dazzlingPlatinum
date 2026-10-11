#include "macros/scrcmd.inc"
#include "res/text/bank/dw_eterna_forest.h"

// Arc 2 rift: MAP_HEADER_DW_ETERNA_FOREST (R0 stub; owner rift-a). docs/arc2/rift_contract.md is the contract:
//   entry   overworld script warps here: Warp MAP_HEADER_DW_ETERNA_FOREST, 0, 20, 12, DIR_WEST
//   exit    Warp MAP_HEADER_ETERNA_FOREST, 0, 84, 37, DIR_SOUTH
//   calm    totem calmed sets VAR_ARC2_PROGRESS = 26
// The stub has no puzzle: the coord event at (17,12) (three steps west of the entry) runs the exit.

    ScriptEntry DWEternaForest_OnTransition
    ScriptEntry DWEternaForest_Exit
    ScriptEntryEnd

DWEternaForest_OnTransition:
    InitPersistedMapFeaturesForDistortionWorld
    End

DWEternaForest_Exit:
    LockAll
    Message DWEternaForest_Text_StubExit
    WaitABXPadPress
    CloseMessage
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut
    WaitFadeScreen
    ScrCmd_320
    ReturnToField
    Warp MAP_HEADER_ETERNA_FOREST, 0, 84, 37, DIR_SOUTH
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End
