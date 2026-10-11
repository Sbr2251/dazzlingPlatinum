#include "macros/scrcmd.inc"
#include "generated/text_banks.h"
#include "res/text/bank/field_moves.h"
#include "res/text/bank/arc2_common.h"

// Arc 2 Resonator (S8 stages 1-2, D10/D11). Field obstacles answer to the Resonator only: each needs ITEM_RESONATOR
// in the bag, the area's calmed totem (FLAG_TOTEM_*_DEFEATED) and the region's Gym badge, checked in that order.
// When something is missing the obstacle's description is followed by a line saying what is missing
// (FieldMoves_ResonatorBlocked). When everything is there, "{Totem}'s energy surges through the Resonator!" and the
// totem's ghost (its front sprite in a faded palette, src/field_move_tasks.c) clears the obstacle.
//
// Flags: none. The resonator allocation (FLAG_UNK_0x0924-0x0925) is unused.
//
// Party-slot stand-ins that make the cut-in and the Use* commands show the totem's ghost:
// RESONATOR_SLOT(FIELD_MOVE_*) in include/field_move_tasks.h. Keep in sync.
#define RESONATOR_SLOT_CUT        0xF0
#define RESONATOR_SLOT_SURF       0xF2
#define RESONATOR_SLOT_STRENGTH   0xF3
#define RESONATOR_SLOT_DEFOG      0xF4
#define RESONATOR_SLOT_ROCK_SMASH 0xF5
#define RESONATOR_SLOT_WATERFALL  0xF6
#define RESONATOR_SLOT_ROCK_CLIMB 0xF7

// VAR_0x8006 for FieldMoves_ResonatorBlocked: a BADGE_ID_* when only the badge is missing, or one of these.
#define RESONATOR_MISSING_ITEM    100
#define RESONATOR_MISSING_TOTEM   101


    ScriptEntry FieldMoves_CutTree
    ScriptEntry FieldMoves_Rock
    ScriptEntry FieldMoves_Boulder
    ScriptEntry FieldMoves_RockyWall
    ScriptEntry FieldMoves_Water
    ScriptEntry FieldMoves_Fog
    ScriptEntry FieldMoves_Waterfall
    ScriptEntry FieldMoves_Dummy
    ScriptEntry FieldMoves_UseCutFromMenu
    ScriptEntry FieldMoves_UseRockSmashFromMenu
    ScriptEntry FieldMoves_UseStrengthFromMenu
    ScriptEntry FieldMoves_UseRockClimbFromMenu
    ScriptEntry FieldMoves_UseSurfFromMenu
    ScriptEntry FieldMoves_UseWaterfallFromMenu
    ScriptEntry FieldMoves_UseDefogFromMenu
    ScriptEntry FieldMoves_UseFlashFromMenu
    ScriptEntry FieldMoves_WaterTotemNotDefeated
    ScriptEntryEnd

FieldMoves_CutTree:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    BufferSpeciesNameFromVar 1, SPECIES_VESPIQUEN, 0, 0
    SetVar VAR_0x8006, RESONATOR_MISSING_ITEM
    CheckItem ITEM_RESONATOR, 1, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, _008E
    SetVar VAR_0x8006, RESONATOR_MISSING_TOTEM
    GoToIfUnset FLAG_TOTEM_VESPIQUEN_DEFEATED, _008E
    SetVar VAR_0x8006, BADGE_ID_FOREST
    CheckBadgeAcquired BADGE_ID_FOREST, VAR_RESULT
    GoToIfEq VAR_RESULT, 0, _008E
    Message FieldMoves_Text_WouldYouLikeToUseCut
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, _00AE
    CloseMessage
    GoTo _066D
    End

_008E:
    Message FieldMoves_Text_TreeLooksLikeCanBeCut
    GetCurrentMapID VAR_0x8004
    CallIfEq VAR_0x8004, 203, _014A
    GoTo FieldMoves_ResonatorBlocked
    End

_00AE:
    Call FieldMoves_ResonatorSurge
    SetVar VAR_0x8004, RESONATOR_SLOT_CUT
    ScrCmd_0C5 VAR_0x8004
    ScrCmd_29E 0, VAR_0x8005
    WaitTime 7, VAR_RESULT
    RemoveObject VAR_LAST_TALKED
    GetCurrentMapID VAR_0x8004
    CreateJournalEvent LOCATION_EVENT_USED_CUT, VAR_0x8004, 0, 0, 0
_00E8:
    WaitTime 1, VAR_RESULT
    GoToIfEq VAR_0x8005, 0, _00E8
    GoTo _066D
    End

FieldMoves_UseCutFromMenu:
    LockAll
    BufferPartyMonNickname 0, VAR_0x8000
    Message FieldMoves_Text_PokemonUsedCut
    CloseMessage
    ScrCmd_0C5 VAR_0x8000
    ScrCmd_29E 0, VAR_0x8005
    WaitTime 7, VAR_RESULT
    RemoveObject VAR_LAST_TALKED
    GetCurrentMapID VAR_0x8004
    CreateJournalEvent LOCATION_EVENT_USED_CUT, VAR_0x8004, 0, 0, 0
_0133:
    WaitTime 1, VAR_RESULT
    GoToIfEq VAR_0x8005, 0, _0133
    ReleaseAll
    End

_014A:
    GoToIfNe VAR_UNK_0x40CD, 0, _0221
    GoToIfNe VAR_UNK_0x40B1, 1, _0221
    Call _017F
    GoToIfEq VAR_RESULT, 0, _0221
    SetVar VAR_UNK_0x40CD, 1
    Return

_017F:
    SetVar VAR_RESULT, 0
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8004, 73, _01CE
    GoToIfEq VAR_0x8004, 74, _01DD
    GoToIfEq VAR_0x8004, 75, _01EC
    GoToIfEq VAR_0x8004, 76, _01FB
    GoToIfEq VAR_0x8004, 77, _020A
    Return

_01CE:
    GoToIfEq VAR_0x8005, 33, _0219
    Return

_01DD:
    GoToIfEq VAR_0x8005, 34, _0219
    Return

_01EC:
    GoToIfEq VAR_0x8005, 34, _0219
    Return

_01FB:
    GoToIfEq VAR_0x8005, 33, _0219
    Return

_020A:
    GoToIfEq VAR_0x8005, 34, _0219
    Return

_0219:
    SetVar VAR_RESULT, 1
    Return

_0221:
    Return

FieldMoves_Rock:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    BufferSpeciesNameFromVar 1, SPECIES_HITMONLEE, 0, 0
    SetVar VAR_0x8006, RESONATOR_MISSING_ITEM
    CheckItem ITEM_RESONATOR, 1, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, _0275
    SetVar VAR_0x8006, RESONATOR_MISSING_TOTEM
    GoToIfUnset FLAG_TOTEM_HITMONLEE_DEFEATED, _0275
    SetVar VAR_0x8006, BADGE_ID_COAL
    CheckBadgeAcquired BADGE_ID_COAL, VAR_RESULT
    GoToIfEq VAR_RESULT, 0, _0275
    Message FieldMoves_Text_WouldYouLikeToUseRockSmash
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, _0284
    CloseMessage
    GoTo _066D
    End

_0275:
    Message FieldMoves_Text_PokemonMayBeAbleToSmashRock
    GoTo FieldMoves_ResonatorBlocked
    End

_0284:
    Call FieldMoves_ResonatorSurge
    SetVar VAR_0x8004, RESONATOR_SLOT_ROCK_SMASH
    ScrCmd_0C5 VAR_0x8004
    ScrCmd_29E 1, VAR_0x8005
    WaitTime 10, VAR_RESULT
    RemoveObject VAR_LAST_TALKED
    GetCurrentMapID VAR_0x8004
    CreateJournalEvent LOCATION_EVENT_USED_ROCK_SMASH, VAR_0x8004, 0, 0, 0
_02B2:
    WaitTime 1, VAR_RESULT
    GoToIfEq VAR_0x8005, 0, _02B2
    GoTo _066D
    End

FieldMoves_UseRockSmashFromMenu:
    LockAll
    BufferPartyMonNickname 0, VAR_0x8000
    Message FieldMoves_Text_PokemonUsedRockSmash
    CloseMessage
    ScrCmd_0C5 VAR_0x8000
    ScrCmd_29E 1, VAR_0x8005
    WaitTime 10, VAR_RESULT
    RemoveObject VAR_LAST_TALKED
    GetCurrentMapID VAR_0x8004
    CreateJournalEvent LOCATION_EVENT_USED_ROCK_SMASH, VAR_0x8004, 0, 0, 0
_02FD:
    WaitTime 1, VAR_RESULT
    GoToIfEq VAR_0x8005, 0, _02FD
    ReleaseAll
    End

FieldMoves_Boulder:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Strength 2, VAR_RESULT
    GoToIfEq VAR_RESULT, 1, _03BD
    BufferSpeciesNameFromVar 1, SPECIES_AGGRON, 0, 0
    SetVar VAR_0x8006, RESONATOR_MISSING_ITEM
    CheckItem ITEM_RESONATOR, 1, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, _0372
    SetVar VAR_0x8006, RESONATOR_MISSING_TOTEM
    GoToIfUnset FLAG_TOTEM_AGGRON_DEFEATED, _0372
    SetVar VAR_0x8006, BADGE_ID_MINE
    CheckBadgeAcquired BADGE_ID_MINE, VAR_RESULT
    GoToIfEq VAR_RESULT, 0, _0372
    Message FieldMoves_Text_WouldYouLikeToUseStrength
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, _0381
    CloseMessage
    GoTo _066D
    End

_0372:
    Message FieldMoves_Text_BoulderMayBeAbleToPush
    GoTo FieldMoves_ResonatorBlocked
    End

_0381:
    Call FieldMoves_ResonatorSurge
    SetVar VAR_0x8004, RESONATOR_SLOT_STRENGTH
    ScrCmd_0C5 VAR_0x8004
    Strength 1
    Message FieldMoves_Text_ResonatorStrengthMadePossibleToMove
    WaitABXPadPress
    CloseMessage
    GetCurrentMapID VAR_0x8004
    CreateJournalEvent LOCATION_EVENT_USED_STRENGTH, VAR_0x8004, 0, 0, 0
    GoTo _066D
    End

_03BD:
    Message FieldMoves_Text_StrengthMadePossibleToMove
    WaitABXPadPress
    CloseMessage
    GoTo _066D
    End

FieldMoves_UseStrengthFromMenu:
    LockAll
    Strength 2, VAR_RESULT
    GoToIfEq VAR_RESULT, 1, _03BD
    Strength 1
    BufferPartyMonNickname 0, VAR_0x8000
    Message FieldMoves_Text_PokemonUsedStrength
    CloseMessage
    ScrCmd_0C5 VAR_0x8000
    Message FieldMoves_Text_PokemonStrengthMadePossibleToMove
    WaitABXPadPress
    CloseMessage
    GetCurrentMapID VAR_0x8004
    CreateJournalEvent LOCATION_EVENT_USED_STRENGTH, VAR_0x8004, 0, 0, 0
    GoTo _0675

FieldMoves_RockyWall:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    BufferSpeciesNameFromVar 1, SPECIES_MAMOSWINE, 0, 0
    SetVar VAR_0x8006, RESONATOR_MISSING_ITEM
    CheckItem ITEM_RESONATOR, 1, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, _0469
    SetVar VAR_0x8006, RESONATOR_MISSING_TOTEM
    GoToIfUnset FLAG_TOTEM_MAMOSWINE_DEFEATED, _0469
    SetVar VAR_0x8006, BADGE_ID_ICICLE
    CheckBadgeAcquired BADGE_ID_ICICLE, VAR_RESULT
    GoToIfEq VAR_RESULT, 0, _0469
    CheckHasPartner VAR_RESULT
    GoToIfEq VAR_RESULT, 1, _0478
    Message FieldMoves_Text_WouldYouLikeToUseRockClimb
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, _0487
    CloseMessage
    GoTo _0671
    End

_0469:
    Message FieldMoves_Text_RockyWallWillMoveScale
    GoTo FieldMoves_ResonatorBlocked
    End

_0478:
    Message FieldMoves_Text_NoRockClimbingWithPartner
    WaitABXPadPress
    CloseMessage
    GoTo _0671
    End

_0487:
    Call FieldMoves_ResonatorSurge
    SetVar VAR_0x8004, RESONATOR_SLOT_ROCK_CLIMB
    UseRockClimb VAR_0x8004
    GetCurrentMapID VAR_0x8004
    CreateJournalEvent LOCATION_EVENT_USED_ROCK_CLIMB, VAR_0x8004, 0, 0, 0
    GoTo _0671
    End

FieldMoves_UseRockClimbFromMenu:
    LockAll
    BufferPartyMonNickname 0, VAR_0x8000
    Message FieldMoves_Text_PokemonUsedRockClimb
    CloseMessage
    UseRockClimb VAR_0x8000
    GetCurrentMapID VAR_0x8004
    CreateJournalEvent LOCATION_EVENT_USED_ROCK_CLIMB, VAR_0x8004, 0, 0, 0
    ReleaseAll
    End

FieldMoves_Water:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    BufferSpeciesNameFromVar 1, SPECIES_LAPRAS, 0, 0
    SetVar VAR_0x8006, RESONATOR_MISSING_ITEM
    CheckItem ITEM_RESONATOR, 1, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, FieldMoves_WaterBlocked
    SetVar VAR_0x8006, RESONATOR_MISSING_TOTEM
    GoToIfUnset FLAG_TOTEM_LAPRAS_DEFEATED, FieldMoves_WaterBlocked
    SetVar VAR_0x8006, BADGE_ID_FEN
    CheckBadgeAcquired BADGE_ID_FEN, VAR_RESULT
    GoToIfEq VAR_RESULT, 0, FieldMoves_WaterBlocked
    CheckHasPartner VAR_RESULT
    GoToIfEq VAR_RESULT, 1, _0512
    Message FieldMoves_Text_WouldYouLikeToUseSurf
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, _051F
    CloseMessage
    GoTo _0671
    End

_0512:
    Message FieldMoves_Text_NoSurfingWithPartner
    WaitABXPadPress
    CloseMessage
    GoTo _0671

FieldMoves_WaterBlocked:
    Message FieldMoves_Text_WaterIsDeepBlue
    GoTo FieldMoves_ResonatorBlocked
    End

_051F:
    Call FieldMoves_ResonatorSurge
    SetVar VAR_0x8004, RESONATOR_SLOT_SURF
    UseSurf VAR_0x8004
    GetCurrentMapID VAR_0x8004
    CreateJournalEvent LOCATION_EVENT_USED_SURF, VAR_0x8004, 0, 0, 0
    GoTo _0671
    End

FieldMoves_UseSurfFromMenu:
    LockAll
    BufferPartyMonNickname 0, VAR_0x8000
    Message FieldMoves_Text_PokemonUsedSurf
    CloseMessage
    ReleaseObject LOCALID_PLAYER
    UseSurf VAR_0x8000
    LockObject LOCALID_PLAYER
    GetCurrentMapID VAR_0x8004
    CreateJournalEvent LOCATION_EVENT_USED_SURF, VAR_0x8004, 0, 0, 0
    ReleaseAll
    End

// A pressed in fog with nothing else in front (FieldMoves_GetFogInteractScript).
FieldMoves_Fog:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    BufferSpeciesNameFromVar 1, SPECIES_SPIRITOMB, 0, 0
    SetVar VAR_0x8006, RESONATOR_MISSING_ITEM
    CheckItem ITEM_RESONATOR, 1, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, _05B4
    SetVar VAR_0x8006, RESONATOR_MISSING_TOTEM
    GoToIfUnset FLAG_TOTEM_SPIRITOMB_DEFEATED, _05B4
    SetVar VAR_0x8006, BADGE_ID_RELIC
    CheckBadgeAcquired BADGE_ID_RELIC, VAR_RESULT
    GoToIfEq VAR_RESULT, 0, _05B4
    Message FieldMoves_Text_WouldYouLikeToUseDefog_Unused
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, _05C3
    CloseMessage
    GoTo _0671
    End

_05B4:
    Message FieldMoves_Text_DeepFogDrapesArea_Unused
    GoTo FieldMoves_ResonatorBlocked
    End

_05C3:
    Call FieldMoves_ResonatorSurge
    SetVar VAR_0x8004, RESONATOR_SLOT_DEFOG
    ScrCmd_0C5 VAR_0x8004
    Defog 1
    PlayFanfare SEQ_SE_DP_FBRADE
    ScrCmd_0C4
    GetCurrentMapID VAR_0x8004
    CreateJournalEvent LOCATION_EVENT_USED_DEFOG, VAR_0x8004, 0, 0, 0
    GetCurrentMapID VAR_0x8004
    CallIfEq VAR_0x8004, 0x169, _0606
    GoTo _0671
    End

_0606:
    SetFlag FLAG_UNK_0x007B
    Return

FieldMoves_UseDefogFromMenu:
    LockAll
    BufferPartyMonNickname 0, VAR_0x8000
    Message FieldMoves_Text_PokemonUsedDefog
    CloseMessage
    ScrCmd_0C5 VAR_0x8000
    Defog 1
    PlayFanfare SEQ_SE_DP_FBRADE
    ScrCmd_0C4
    GetCurrentMapID VAR_0x8004
    CreateJournalEvent LOCATION_EVENT_USED_DEFOG, VAR_0x8004, 0, 0, 0
    GetCurrentMapID VAR_0x8004
    CallIfEq VAR_0x8004, 0x169, _0606
    GoTo _0675

FieldMoves_UseFlashFromMenu:
    LockAll
    BufferPartyMonNickname 0, VAR_0x8000
    Message FieldMoves_Text_PokemonUsedFlash
    CloseMessage
    ScrCmd_0C5 VAR_0x8000
    Flash 1
    ScrCmd_0C3
    WaitTime 42, VAR_RESULT
    GoTo _0675

_066D:
    ReleaseAll
    End

_0671:
    ReleaseAll
    End

_0675:
    ReleaseAll
    End

FieldMoves_Waterfall:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    BufferSpeciesNameFromVar 1, SPECIES_KINGDRA, 0, 0
    SetVar VAR_0x8006, RESONATOR_MISSING_ITEM
    CheckItem ITEM_RESONATOR, 1, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, _06C3
    SetVar VAR_0x8006, RESONATOR_MISSING_TOTEM
    GoToIfUnset FLAG_TOTEM_KINGDRA_DEFEATED, _06C3
    SetVar VAR_0x8006, BADGE_ID_BEACON
    CheckBadgeAcquired BADGE_ID_BEACON, VAR_RESULT
    GoToIfEq VAR_RESULT, 0, _06C3
    Message FieldMoves_Text_WouldYouLikeToUseWaterfall
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, _06D2
    CloseMessage
    GoTo _0671
    End

_06C3:
    Message FieldMoves_Text_WallOfWater
    GoTo FieldMoves_ResonatorBlocked
    End

_06D2:
    Call FieldMoves_ResonatorSurge
    SetVar VAR_0x8004, RESONATOR_SLOT_WATERFALL
    UseWaterfall VAR_0x8004
    GetCurrentMapID VAR_0x8004
    CreateJournalEvent LOCATION_EVENT_USED_WATERFALL, VAR_0x8004, 0, 0, 0
    GoTo _0671
    End

FieldMoves_UseWaterfallFromMenu:
    LockAll
    BufferPartyMonNickname 0, VAR_0x8000
    Message FieldMoves_Text_PokemonUsedWaterfall
    CloseMessage
    ReleaseObject LOCALID_PLAYER
    UseWaterfall VAR_0x8000
    LockObject LOCALID_PLAYER
    GetCurrentMapID VAR_0x8004
    CreateJournalEvent LOCATION_EVENT_USED_WATERFALL, VAR_0x8004, 0, 0, 0
    ReleaseAll
    End

FieldMoves_Dummy:
    End

// Stock-era entry (water with the badge but not Lapras); field_control now always sends water to FieldMoves_Water.
FieldMoves_WaterTotemNotDefeated:
    GoTo FieldMoves_Water
    End

// The totem's name is in string 1 ({STRVAR_1 1, 1, 0}).
FieldMoves_ResonatorSurge:
    MessageFromBank TEXT_BANK_ARC2_COMMON, Arc2Common_Text_ResonatorSurge
    WaitABXPadPress
    CloseMessage
    Return

// The obstacle's description is on screen; VAR_0x8006 says what's missing, the totem's name is in string 1.
FieldMoves_ResonatorBlocked:
    WaitABXPadPress
    GoToIfEq VAR_0x8006, RESONATOR_MISSING_ITEM, FieldMoves_ResonatorBlocked_Item
    GoToIfEq VAR_0x8006, RESONATOR_MISSING_TOTEM, FieldMoves_ResonatorBlocked_Totem
    GoToIfEq VAR_0x8006, BADGE_ID_COAL, FieldMoves_ResonatorBlocked_Coal
    GoToIfEq VAR_0x8006, BADGE_ID_FOREST, FieldMoves_ResonatorBlocked_Forest
    GoToIfEq VAR_0x8006, BADGE_ID_COBBLE, FieldMoves_ResonatorBlocked_Cobble
    GoToIfEq VAR_0x8006, BADGE_ID_FEN, FieldMoves_ResonatorBlocked_Fen
    GoToIfEq VAR_0x8006, BADGE_ID_RELIC, FieldMoves_ResonatorBlocked_Relic
    GoToIfEq VAR_0x8006, BADGE_ID_MINE, FieldMoves_ResonatorBlocked_Mine
    GoToIfEq VAR_0x8006, BADGE_ID_ICICLE, FieldMoves_ResonatorBlocked_Icicle
    GoTo FieldMoves_ResonatorBlocked_Beacon
    End

FieldMoves_ResonatorBlocked_Item:
    MessageFromBank TEXT_BANK_ARC2_COMMON, Arc2Common_Text_ResonatorMissing
    GoTo FieldMoves_ResonatorBlocked_End
    End

FieldMoves_ResonatorBlocked_Totem:
    MessageFromBank TEXT_BANK_ARC2_COMMON, Arc2Common_Text_ResonatorNoTotem
    GoTo FieldMoves_ResonatorBlocked_End
    End

FieldMoves_ResonatorBlocked_Coal:
    MessageFromBank TEXT_BANK_ARC2_COMMON, Arc2Common_Text_ResonatorNeedsCoalBadge
    GoTo FieldMoves_ResonatorBlocked_End
    End

FieldMoves_ResonatorBlocked_Forest:
    MessageFromBank TEXT_BANK_ARC2_COMMON, Arc2Common_Text_ResonatorNeedsForestBadge
    GoTo FieldMoves_ResonatorBlocked_End
    End

FieldMoves_ResonatorBlocked_Cobble:
    MessageFromBank TEXT_BANK_ARC2_COMMON, Arc2Common_Text_ResonatorNeedsCobbleBadge
    GoTo FieldMoves_ResonatorBlocked_End
    End

FieldMoves_ResonatorBlocked_Fen:
    MessageFromBank TEXT_BANK_ARC2_COMMON, Arc2Common_Text_ResonatorNeedsFenBadge
    GoTo FieldMoves_ResonatorBlocked_End
    End

FieldMoves_ResonatorBlocked_Relic:
    MessageFromBank TEXT_BANK_ARC2_COMMON, Arc2Common_Text_ResonatorNeedsRelicBadge
    GoTo FieldMoves_ResonatorBlocked_End
    End

FieldMoves_ResonatorBlocked_Mine:
    MessageFromBank TEXT_BANK_ARC2_COMMON, Arc2Common_Text_ResonatorNeedsMineBadge
    GoTo FieldMoves_ResonatorBlocked_End
    End

FieldMoves_ResonatorBlocked_Icicle:
    MessageFromBank TEXT_BANK_ARC2_COMMON, Arc2Common_Text_ResonatorNeedsIcicleBadge
    GoTo FieldMoves_ResonatorBlocked_End
    End

FieldMoves_ResonatorBlocked_Beacon:
    MessageFromBank TEXT_BANK_ARC2_COMMON, Arc2Common_Text_ResonatorNeedsBeaconBadge
FieldMoves_ResonatorBlocked_End:
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
