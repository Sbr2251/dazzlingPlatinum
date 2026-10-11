#include "macros/scrcmd.inc"
#include "res/text/bank/dw_ravaged_path.h"

// Arc 2 rift: MAP_HEADER_DW_RAVAGED_PATH (R0 stub; owner rift-a). docs/arc2/rift_contract.md is the contract:
//   entry   overworld script warps here: Warp MAP_HEADER_DW_RAVAGED_PATH, 0, 20, 12, DIR_WEST
//   exit    Warp MAP_HEADER_RAVAGED_PATH, 0, 19, 46, DIR_SOUTH
//   calm    totem calmed sets VAR_ARC2_PROGRESS = 15
// The stub has no puzzle: the coord event at (17,12) (three steps west of the entry) runs the exit.

    ScriptEntry DWRavagedPath_OnTransition
    ScriptEntry DWRavagedPath_Exit
    ScriptEntryEnd

DWRavagedPath_OnTransition:
    InitPersistedMapFeaturesForDistortionWorld
    End

DWRavagedPath_Exit:
    LockAll
    Message DWRavagedPath_Text_StubExit
    WaitABXPadPress
    CloseMessage
    PlayFanfare SEQ_SE_PL_SYUWA
    FadeScreenOut
    WaitFadeScreen
    ScrCmd_320
    ReturnToField
    Warp MAP_HEADER_RAVAGED_PATH, 0, 19, 46, DIR_SOUTH
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End
