#include "macros/scrcmd.inc"
#include "res/text/bank/route_216.h"


    ScriptEntry Route216_CantRideBike_Unused
    ScriptEntry Route216_ArrowSignpostMtCoronet
    ScriptEntry Route216_SignboardSnowboundLodge
    ScriptEntry Route216_TeoMemorial
    ScriptEntryEnd

Route216_CantRideBike_Unused:
    NPCMessage Route216_Text_CantRideBikeOnSnow
    End

Route216_ArrowSignpostMtCoronet:
    ShowArrowSign Route216_Text_SignMtCoronet
    End

Route216_SignboardSnowboundLodge:
    ShowLandmarkSign Route216_Text_SignSnowboundLodge
    End

Route216_TeoMemorial:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message Route216_Text_TeoMemorialStone
    WaitABPadPress
    Message Route216_Text_TeoMemorialInscription
    WaitABPadPress
    Message Route216_Text_TeoMemorialOfferings
    WaitABPadPress
    PlaySE SEQ_SE_DP_KIRAKIRA_sseq
    Message Route216_Text_TeoMemorialFootprints
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
