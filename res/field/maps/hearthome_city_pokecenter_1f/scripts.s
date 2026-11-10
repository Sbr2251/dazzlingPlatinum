#include "macros/scrcmd.inc"
#include "res/text/bank/hearthome_city_pokecenter_1f.h"
#include "res/field/maps/locals/hearthome_city_pokecenter_1f.h"


    ScriptEntry HearthomeCityPokecenter1F_Nurse
    ScriptEntry HearthomeCityPokecenter1F_Youngster
    ScriptEntry HearthomeCityPokecenter1F_Socialite
    ScriptEntry HearthomeCityPokecenter1F_Guitarist
    ScriptEntry HearthomeCenter_VeinCall
    ScriptEntryEnd

HearthomeCityPokecenter1F_Nurse:
    SetVar VAR_0x8007, LOCALID_HEARTHOME_NURSE
    CallCommonScript CommonScript_PokecenterNurse
    End

HearthomeCityPokecenter1F_Youngster:
    NPCMessage HearthomeCityPokecenter1F_Text_HaveYouCheckedGlobalTerminal
    End

HearthomeCityPokecenter1F_Socialite:
    NPCMessage HearthomeCityPokecenter1F_Text_DoYouHaveAPoffinCase
    End

HearthomeCityPokecenter1F_Guitarist:
    NPCMessage HearthomeCityPokecenter1F_Text_FantinaLikesContestsToo
    End

    .balign 4, 0

HearthomeCenter_VeinCall:
    GoToIfUnset FLAG_ARC2_RIFTB_E, HearthomeCenter_VeinCallEnd
    LockAll
    BufferPlayerName 0
    BufferRivalName 1
    Message HearthomeCenter_Text_CalledProfessor
    WaitButton
    Message HearthomeCenter_Text_RowanAnySign
    WaitButton
    Message HearthomeCenter_Text_ToldVein
    WaitButton
    Message HearthomeCenter_Text_RowanWholeVein
    WaitButton
    Message HearthomeCenter_Text_RowanGariusHere
    WaitButton
    Message HearthomeCenter_Text_GariusShards
    WaitButton
    Message HearthomeCenter_Text_RowanFirstThing
    WaitButton
    CloseMessage
    SetVar VAR_ARC2_PROGRESS, 93
    FadeScreenOut
    WaitFadeScreen
    HealParty
    PlayFanfare SEQ_ASA_sseq
    WaitFanfare
    WaitFadeScreen
    Message HearthomeCenter_Text_NextMorning
    WaitButton
    CloseMessage
    ReleaseAll
HearthomeCenter_VeinCallEnd:
    End

