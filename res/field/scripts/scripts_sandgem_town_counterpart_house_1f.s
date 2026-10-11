#include "macros/scrcmd.inc"
#include "res/text/bank/sandgem_town_counterpart_house_1f.h"


    ScriptEntry _000A
    ScriptEntry _003A
    ScriptEntryEnd

_000A:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GetNationalDexEnabled VAR_RESULT
    GoToIfEq VAR_RESULT, 1, _002F
    Message 0
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_002F:
    Message 1
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_003A:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GetNationalDexEnabled VAR_RESULT
    GoToIfEq VAR_RESULT, 1, _009A
    GoTo _005A

_005A:
    // Arc 1: this is Ruth's family home, so the kid always talks about a big sister.
    GoTo _007A
    End

_007A:
    BufferPlayerName 0
    Message 2
    GoTo _0092

_0086:
    BufferPlayerName 0
    Message 3
    GoTo _0092

_0092:
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_009A:
    GoToIfUnset FLAG_GAME_COMPLETED, _005A
    GoToIfSet FLAG_UNK_0x00F0, _00C4
    SetFlag FLAG_UNK_0x00F0
    EnableSwarms
    BufferPlayerName 0
    Message 4
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_00C4:
    BufferPlayerName 0
    GetSwarmMapAndSpecies VAR_MAP_LOCAL_1, VAR_MAP_LOCAL_0
    BufferMapName 1, VAR_MAP_LOCAL_1
    BufferSpeciesNameFromVar 2, VAR_MAP_LOCAL_0, 0, 1
    GoTo _00FA
    End

_00FA:
    Message 5
    GoTo _010F

_0103:
    BufferPlayerName 0
    Message 6
    GoTo _010F

_010F:
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
