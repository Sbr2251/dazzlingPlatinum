#include "macros/scrcmd.inc"
#include "res/text/bank/mt_coronet_1f_tunnel_room.h"


    ScriptEntry _0006
    ScriptEntry MtCoronet1FTunnelRoom_OnTransition
    ScriptEntryEnd

_0006:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 0
    WaitABXPadPress
    CloseMessage
    ApplyMovement 16, _0024
    WaitMovement
    ReleaseAll
    End

    .balign 4, 0
_0024:
    FaceNorth
    EndMovement

// Arc 2: Team Galactic never existed here; keep the stock Galactic grunts in this room hidden (their flag is only set by
// stock Platinum story scripts that no longer run).
MtCoronet1FTunnelRoom_OnTransition:
    SetFlag FLAG_UNK_0x028F
    End
