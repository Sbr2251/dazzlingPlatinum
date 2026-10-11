#include "macros/scrcmd.inc"
#include "res/text/bank/hearthome_city_pokecenter_1f.h"


    ScriptEntry _0012
    ScriptEntry _001E
    ScriptEntry _0031
    ScriptEntry _0044
    ScriptEntry HearthomeCenter_VeinCall
    ScriptEntryEnd

// Dazzling Platinum Arc 2, s-hearthome (2.25): the vein call. Progress 92 with the vein seen (rift-b sets
// FLAG_ARC2_RIFTB_E in DW_LOST_TOWER): crossing the row inside the door, the player calls Rowan from the counter
// phone (message boxes only). Only Rowan and Garius hear it: the leak that clears Cyrus. Sets 93.
HearthomeCenter_VeinCall:
    GoToIfUnset FLAG_ARC2_RIFTB_E, HearthomeCenter_VeinCallEnd
    LockAll
    BufferPlayerName 0
    BufferRivalName 1
    Message HearthomeCenter_Text_CalledProfessor
    WaitABXPadPress
    Message HearthomeCenter_Text_RowanAnySign
    WaitABXPadPress
    Message HearthomeCenter_Text_ToldVein
    WaitABXPadPress
    Message HearthomeCenter_Text_RowanWholeVein
    WaitABXPadPress
    Message HearthomeCenter_Text_RowanGariusHere
    WaitABXPadPress
    Message HearthomeCenter_Text_GariusShards
    WaitABXPadPress
    Message HearthomeCenter_Text_RowanFirstThing
    WaitABXPadPress
    CloseMessage
    SetVar VAR_ARC2_PROGRESS, 93
    FadeScreenOut
    WaitFadeScreen
    HealParty
    PlaySound SEQ_ASA
    WaitSound
    FadeScreenIn
    WaitFadeScreen
    Message HearthomeCenter_Text_NextMorning
    WaitABXPadPress
    CloseMessage
    ReleaseAll
HearthomeCenter_VeinCallEnd:
    End

_0012:
    CallPokecenterNurse 0
    End

_001E:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 0
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0031:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 1
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0044:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 3
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
