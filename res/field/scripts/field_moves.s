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
// Flags: none. The resonator allocation (FLAG_ARC2_RESONATOR_A-0x0925) is unused.
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

// Each obstacle sets VAR_0x8007 to its totem's surge line and, as the checks run, VAR_0x8006 to the line saying what's
// missing (both in TEXT_BANK_ARC2_COMMON). Totem names are written out in mixed case, as in the screenplay.


    ScriptEntry FieldMoves_CutTree
    ScriptEntry FieldMoves_Rock
    ScriptEntry FieldMoves_Boulder
    ScriptEntry FieldMoves_RockyWall
    ScriptEntry FieldMoves_Water
    ScriptEntry FieldMoves_Fog
    ScriptEntry FieldMoves_Waterfall
    ScriptEntry FieldMoves_Dummy8
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
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    SetVar VAR_0x8007, Arc2Common_Text_ResonatorSurgeVespiquen
    SetVar VAR_0x8006, Arc2Common_Text_ResonatorMissing
    CheckItem ITEM_RESONATOR, 1, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, FieldMoves_CantUseCut
    SetVar VAR_0x8006, Arc2Common_Text_ResonatorNoTotem
    GoToIfUnset FLAG_TOTEM_VESPIQUEN_DEFEATED, FieldMoves_CantUseCut
    SetVar VAR_0x8006, Arc2Common_Text_ResonatorNeedsForestBadge
    CheckBadgeAcquired BADGE_ID_FOREST, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, FieldMoves_CantUseCut
    Message FieldMoves_Text_WouldYouLikeToUseCut
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, FieldMoves_UseCutFromField
    CloseMessage
    GoTo FieldMoves_End
    End

FieldMoves_CantUseCut:
    Message FieldMoves_Text_TreeLooksLikeCanBeCut
    GetCurrentMapID VAR_0x8004
    CallIfEq VAR_0x8004, MAP_HEADER_ETERNA_FOREST, FieldMoves_TryEnableCherylCutscene
    GoTo FieldMoves_ResonatorBlocked
    End

FieldMoves_UseCutFromField:
    Call FieldMoves_ResonatorSurge
    SetVar VAR_0x8004, RESONATOR_SLOT_CUT
    PlayHMCutIn VAR_0x8004
    StartDestroyObstacleAnimation 0, VAR_0x8005
    WaitTime 7, VAR_RESULT
    RemoveObject VAR_LAST_TALKED
    GetCurrentMapID VAR_0x8004
    CreateJournalEvent LOCATION_EVENT_USED_CUT, VAR_0x8004
FieldMoves_WaitForCutAnimFromField:
    WaitTime 1, VAR_RESULT
    GoToIfEq VAR_0x8005, 0, FieldMoves_WaitForCutAnimFromField
    GoTo FieldMoves_End
    End

FieldMoves_UseCutFromMenu:
    LockAll
    BufferPartyMonNickname 0, VAR_0x8000
    Message FieldMoves_Text_PokemonUsedCut
    CloseMessage
    PlayHMCutIn VAR_0x8000
    StartDestroyObstacleAnimation 0, VAR_0x8005
    WaitTime 7, VAR_RESULT
    RemoveObject VAR_LAST_TALKED
    GetCurrentMapID VAR_0x8004
    CreateJournalEvent LOCATION_EVENT_USED_CUT, VAR_0x8004
FieldMoves_WaitForCutAnimFromMenu:
    WaitTime 1, VAR_RESULT
    GoToIfEq VAR_0x8005, 0, FieldMoves_WaitForCutAnimFromMenu
    ReleaseAll
    End

FieldMoves_TryEnableCherylCutscene:
    GoToIfNe VAR_ETERNA_FOREST_CHERYL_OLD_CHATEAU_CUTSCENE_STATE, 0, FieldMoves_DontEnableCherylCutscene
    GoToIfNe VAR_ETERNA_FOREST_FOLLOWER_CHERYL_STATE, 1, FieldMoves_DontEnableCherylCutscene
    Call FieldMoves_CheckPositionForCherylCutscene
    GoToIfEq VAR_RESULT, FALSE, FieldMoves_DontEnableCherylCutscene
    SetVar VAR_ETERNA_FOREST_CHERYL_OLD_CHATEAU_CUTSCENE_STATE, 1
    Return

FieldMoves_CheckPositionForCherylCutscene:
    SetVar VAR_RESULT, FALSE
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8004, 73, FieldMoves_CheckPositionX73
    GoToIfEq VAR_0x8004, 74, FieldMoves_CheckPositionX74
    GoToIfEq VAR_0x8004, 75, FieldMoves_CheckPositionX75
    GoToIfEq VAR_0x8004, 76, FieldMoves_CheckPositionX76
    GoToIfEq VAR_0x8004, 77, FieldMoves_CheckPositionX77
    Return

FieldMoves_CheckPositionX73:
    GoToIfEq VAR_0x8005, 33, FieldMoves_CorrectPositionForCherylCutscene
    Return

FieldMoves_CheckPositionX74:
    GoToIfEq VAR_0x8005, 34, FieldMoves_CorrectPositionForCherylCutscene
    Return

FieldMoves_CheckPositionX75:
    GoToIfEq VAR_0x8005, 34, FieldMoves_CorrectPositionForCherylCutscene
    Return

FieldMoves_CheckPositionX76:
    GoToIfEq VAR_0x8005, 33, FieldMoves_CorrectPositionForCherylCutscene
    Return

FieldMoves_CheckPositionX77:
    GoToIfEq VAR_0x8005, 34, FieldMoves_CorrectPositionForCherylCutscene
    Return

FieldMoves_CorrectPositionForCherylCutscene:
    SetVar VAR_RESULT, TRUE
    Return

FieldMoves_DontEnableCherylCutscene:
    Return

FieldMoves_Rock:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    SetVar VAR_0x8007, Arc2Common_Text_ResonatorSurgeHitmonlee
    SetVar VAR_0x8006, Arc2Common_Text_ResonatorMissing
    CheckItem ITEM_RESONATOR, 1, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, FieldMoves_CantUseRockSmash
    SetVar VAR_0x8006, Arc2Common_Text_ResonatorNoTotem
    GoToIfUnset FLAG_TOTEM_HITMONLEE_DEFEATED, FieldMoves_CantUseRockSmash
    SetVar VAR_0x8006, Arc2Common_Text_ResonatorNeedsCoalBadge
    CheckBadgeAcquired BADGE_ID_COAL, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, FieldMoves_CantUseRockSmash
    Message FieldMoves_Text_WouldYouLikeToUseRockSmash
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, FieldMoves_UseRockSmashFromField
    CloseMessage
    GoTo FieldMoves_End
    End

FieldMoves_CantUseRockSmash:
    Message FieldMoves_Text_PokemonMayBeAbleToSmashRock
    GoTo FieldMoves_ResonatorBlocked
    End

FieldMoves_UseRockSmashFromField:
    Call FieldMoves_ResonatorSurge
    SetVar VAR_0x8004, RESONATOR_SLOT_ROCK_SMASH
    PlayHMCutIn VAR_0x8004
    StartDestroyObstacleAnimation 1, VAR_0x8005
    WaitTime 10, VAR_RESULT
    RemoveObject VAR_LAST_TALKED
    GetCurrentMapID VAR_0x8004
    CreateJournalEvent LOCATION_EVENT_USED_ROCK_SMASH, VAR_0x8004
FieldMoves_WaitForRockSmashAnimFromField:
    WaitTime 1, VAR_RESULT
    GoToIfEq VAR_0x8005, 0, FieldMoves_WaitForRockSmashAnimFromField
    // (2.8: Route 204 North's coord event on the smashed rock tile advances 17 -> 18; nothing to do here.)
    GoTo FieldMoves_End
    End

// 2.8 hand-off to s-route204: smashing Ruth's boulder on Route 204 North while VAR_ARC2_PROGRESS is 17 (Resonator
// just given) sets 18, so the scene can go on to Ruth's "It works!".
FieldMoves_Arc2FirstResonance:
    CallIfEq VAR_ARC2_PROGRESS, 17, FieldMoves_Arc2RockSmashed
    Return

FieldMoves_Arc2RockSmashed:
    SetVar VAR_ARC2_PROGRESS, 18
    Return

FieldMoves_UseRockSmashFromMenu:
    LockAll
    BufferPartyMonNickname 0, VAR_0x8000
    Message FieldMoves_Text_PokemonUsedRockSmash
    CloseMessage
    PlayHMCutIn VAR_0x8000
    StartDestroyObstacleAnimation 1, VAR_0x8005
    WaitTime 10, VAR_RESULT
    RemoveObject VAR_LAST_TALKED
    GetCurrentMapID VAR_0x8004
    CreateJournalEvent LOCATION_EVENT_USED_ROCK_SMASH, VAR_0x8004
FieldMoves_WaitForRockSmashAnimFromMenu:
    WaitTime 1, VAR_RESULT
    GoToIfEq VAR_0x8005, 0, FieldMoves_WaitForRockSmashAnimFromMenu
    ReleaseAll
    End

FieldMoves_Boulder:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    DoStrengthFunc FIELD_MOVE_FUNC_CHECK_ACTIVE, VAR_RESULT
    GoToIfEq VAR_RESULT, TRUE, FieldMoves_StrenghtAlreadyActive
    SetVar VAR_0x8007, Arc2Common_Text_ResonatorSurgeAggron
    SetVar VAR_0x8006, Arc2Common_Text_ResonatorMissing
    CheckItem ITEM_RESONATOR, 1, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, FieldMoves_CantUseStrength
    SetVar VAR_0x8006, Arc2Common_Text_ResonatorNoTotem
    GoToIfUnset FLAG_TOTEM_AGGRON_DEFEATED, FieldMoves_CantUseStrength
    SetVar VAR_0x8006, Arc2Common_Text_ResonatorNeedsMineBadge
    CheckBadgeAcquired BADGE_ID_MINE, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, FieldMoves_CantUseStrength
    Message FieldMoves_Text_WouldYouLikeToUseStrength
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, FieldMoves_UseStrengthFromField
    CloseMessage
    GoTo FieldMoves_End
    End

FieldMoves_CantUseStrength:
    Message FieldMoves_Text_BoulderMayBeAbleToPush
    GoTo FieldMoves_ResonatorBlocked
    End

FieldMoves_UseStrengthFromField:
    Call FieldMoves_ResonatorSurge
    SetVar VAR_0x8004, RESONATOR_SLOT_STRENGTH
    PlayHMCutIn VAR_0x8004
    DoStrengthFunc FIELD_MOVE_FUNC_SET_ACTIVE
    Message FieldMoves_Text_ResonatorStrengthMadePossibleToMove
    WaitABPadPress
    CloseMessage
    GetCurrentMapID VAR_0x8004
    CreateJournalEvent LOCATION_EVENT_USED_STRENGTH, VAR_0x8004
    GoTo FieldMoves_End
    End

FieldMoves_StrenghtAlreadyActive:
    Message FieldMoves_Text_StrengthMadePossibleToMove
    WaitButton
    CloseMessage
    GoTo FieldMoves_End
    End

FieldMoves_UseStrengthFromMenu:
    LockAll
    DoStrengthFunc FIELD_MOVE_FUNC_CHECK_ACTIVE, VAR_RESULT
    GoToIfEq VAR_RESULT, TRUE, FieldMoves_StrenghtAlreadyActive
    DoStrengthFunc FIELD_MOVE_FUNC_SET_ACTIVE
    BufferPartyMonNickname 0, VAR_0x8000
    Message FieldMoves_Text_PokemonUsedStrength
    CloseMessage
    PlayHMCutIn VAR_0x8000
    Message FieldMoves_Text_PokemonStrengthMadePossibleToMove
    WaitButton
    CloseMessage
    GetCurrentMapID VAR_0x8004
    CreateJournalEvent LOCATION_EVENT_USED_STRENGTH, VAR_0x8004
    GoTo FieldMoves_End3

FieldMoves_RockyWall:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    SetVar VAR_0x8007, Arc2Common_Text_ResonatorSurgeMamoswine
    SetVar VAR_0x8006, Arc2Common_Text_ResonatorMissing
    CheckItem ITEM_RESONATOR, 1, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, FieldMoves_CantUseRockClimb
    SetVar VAR_0x8006, Arc2Common_Text_ResonatorNoTotem
    GoToIfUnset FLAG_TOTEM_MAMOSWINE_DEFEATED, FieldMoves_CantUseRockClimb
    SetVar VAR_0x8006, Arc2Common_Text_ResonatorNeedsIcicleBadge
    CheckBadgeAcquired BADGE_ID_ICICLE, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, FieldMoves_CantUseRockClimb
    CheckHasPartner VAR_RESULT
    GoToIfEq VAR_RESULT, TRUE, FieldMoves_NoRockClimbingWithPartner
    Message FieldMoves_Text_WouldYouLikeToUseRockClimb
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, FieldMoves_UseRockClimbFromField
    CloseMessage
    GoTo FieldMoves_End2
    End

FieldMoves_CantUseRockClimb:
    Message FieldMoves_Text_RockyWallWillMoveScale
    GoTo FieldMoves_ResonatorBlocked
    End

FieldMoves_NoRockClimbingWithPartner:
    Message FieldMoves_Text_NoRockClimbingWithPartner
    WaitButton
    CloseMessage
    GoTo FieldMoves_End2
    End

FieldMoves_UseRockClimbFromField:
    Call FieldMoves_ResonatorSurge
    SetVar VAR_0x8004, RESONATOR_SLOT_ROCK_CLIMB
    UseRockClimb VAR_0x8004
    GetCurrentMapID VAR_0x8004
    CreateJournalEvent LOCATION_EVENT_USED_ROCK_CLIMB, VAR_0x8004
    GoTo FieldMoves_End2
    End

FieldMoves_UseRockClimbFromMenu:
    LockAll
    BufferPartyMonNickname 0, VAR_0x8000
    Message FieldMoves_Text_PokemonUsedRockClimb
    CloseMessage
    UseRockClimb VAR_0x8000
    GetCurrentMapID VAR_0x8004
    CreateJournalEvent LOCATION_EVENT_USED_ROCK_CLIMB, VAR_0x8004
    ReleaseAll
    End

FieldMoves_Water:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    SetVar VAR_0x8007, Arc2Common_Text_ResonatorSurgeLapras
    SetVar VAR_0x8006, Arc2Common_Text_ResonatorMissing
    CheckItem ITEM_RESONATOR, 1, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, FieldMoves_WaterBlocked
    SetVar VAR_0x8006, Arc2Common_Text_ResonatorNoTotem
    GoToIfUnset FLAG_TOTEM_LAPRAS_DEFEATED, FieldMoves_WaterBlocked
    SetVar VAR_0x8006, Arc2Common_Text_ResonatorNeedsFenBadge
    CheckBadgeAcquired BADGE_ID_FEN, VAR_RESULT
    GoToIfEq VAR_RESULT, 0, FieldMoves_WaterBlocked
    CheckHasPartner VAR_RESULT
    GoToIfEq VAR_RESULT, TRUE, FieldMoves_CantUseSurf
    Message FieldMoves_Text_WouldYouLikeToUseSurf
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, FieldMoves_UseSurfFromField
    CloseMessage
    GoTo FieldMoves_End2
    End

FieldMoves_CantUseSurf:
    Message FieldMoves_Text_NoSurfingWithPartner
    WaitButton
    CloseMessage
    GoTo FieldMoves_End2

FieldMoves_WaterBlocked:
    Message FieldMoves_Text_WaterIsDeepBlue
    GoTo FieldMoves_ResonatorBlocked
    End

FieldMoves_UseSurfFromField:
    Call FieldMoves_ResonatorSurge
    SetVar VAR_0x8004, RESONATOR_SLOT_SURF
    UseSurf VAR_0x8004
    GetCurrentMapID VAR_0x8004
    CreateJournalEvent LOCATION_EVENT_USED_SURF, VAR_0x8004
    GoTo FieldMoves_End2
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
    CreateJournalEvent LOCATION_EVENT_USED_SURF, VAR_0x8004
    ReleaseAll
    End

// A pressed in fog with nothing else in front (FieldMoves_GetFogInteractScript).
FieldMoves_Fog:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    SetVar VAR_0x8007, Arc2Common_Text_ResonatorSurgeSpiritomb
    SetVar VAR_0x8006, Arc2Common_Text_ResonatorMissing
    CheckItem ITEM_RESONATOR, 1, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, FieldMoves_CantUseDefog_Unused
    SetVar VAR_0x8006, Arc2Common_Text_ResonatorNoTotem
    GoToIfUnset FLAG_TOTEM_SPIRITOMB_DEFEATED, FieldMoves_CantUseDefog_Unused
    SetVar VAR_0x8006, Arc2Common_Text_ResonatorNeedsRelicBadge
    CheckBadgeAcquired BADGE_ID_RELIC, VAR_RESULT
    GoToIfEq VAR_RESULT, 0, FieldMoves_CantUseDefog_Unused
    Message FieldMoves_Text_WouldYouLikeToUseDefog_Unused
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, FieldMoves_UseDefogFromField_Unused
    CloseMessage
    GoTo FieldMoves_End2
    End

FieldMoves_CantUseDefog_Unused:
    Message FieldMoves_Text_DeepFogDrapesArea_Unused
    GoTo FieldMoves_ResonatorBlocked
    End

FieldMoves_UseDefogFromField_Unused:
    Call FieldMoves_ResonatorSurge
    SetVar VAR_0x8004, RESONATOR_SLOT_DEFOG
    PlayHMCutIn VAR_0x8004
    DoDefogFunc FIELD_MOVE_FUNC_SET_ACTIVE
    PlaySE SEQ_SE_DP_FBRADE_sseq
    ScrCmd_0C4
    GetCurrentMapID VAR_0x8004
    CreateJournalEvent LOCATION_EVENT_USED_DEFOG, VAR_0x8004
    GetCurrentMapID VAR_0x8004
    CallIfEq VAR_0x8004, MAP_HEADER_ROUTE_209_LOST_TOWER_5F, FieldMoves_SetFlagUsedDefog_Unused
    GoTo FieldMoves_End2
    End

FieldMoves_SetFlagUsedDefog_Unused:
    SetFlag FLAG_USED_DEFOG_IN_ROUTE_209_LOST_TOWER_5F
    Return

FieldMoves_UseDefogFromMenu:
    LockAll
    BufferPartyMonNickname 0, VAR_0x8000
    Message FieldMoves_Text_PokemonUsedDefog
    CloseMessage
    PlayHMCutIn VAR_0x8000
    DoDefogFunc FIELD_MOVE_FUNC_SET_ACTIVE
    PlaySE SEQ_SE_DP_FBRADE_sseq
    ScrCmd_0C4
    GetCurrentMapID VAR_0x8004
    CreateJournalEvent LOCATION_EVENT_USED_DEFOG, VAR_0x8004
    GetCurrentMapID VAR_0x8004
    CallIfEq VAR_0x8004, MAP_HEADER_ROUTE_209_LOST_TOWER_5F, FieldMoves_SetFlagUsedDefog_Unused
    GoTo FieldMoves_End3

FieldMoves_UseFlashFromMenu:
    LockAll
    BufferPartyMonNickname 0, VAR_0x8000
    Message FieldMoves_Text_PokemonUsedFlash
    CloseMessage
    PlayHMCutIn VAR_0x8000
    DoFlashFunc FIELD_MOVE_FUNC_SET_ACTIVE
    ScrCmd_0C3
    WaitTime 42, VAR_RESULT
    GoTo FieldMoves_End3

FieldMoves_End:
    ReleaseAll
    End

FieldMoves_End2:
    ReleaseAll
    End

FieldMoves_End3:
    ReleaseAll
    End

FieldMoves_Waterfall:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    SetVar VAR_0x8007, Arc2Common_Text_ResonatorSurgeKingdra
    SetVar VAR_0x8006, Arc2Common_Text_ResonatorMissing
    CheckItem ITEM_RESONATOR, 1, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, FieldMoves_CantUseWaterfall
    SetVar VAR_0x8006, Arc2Common_Text_ResonatorNoTotem
    GoToIfUnset FLAG_TOTEM_KINGDRA_DEFEATED, FieldMoves_CantUseWaterfall
    SetVar VAR_0x8006, Arc2Common_Text_ResonatorNeedsBeaconBadge
    CheckBadgeAcquired BADGE_ID_BEACON, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, FieldMoves_CantUseWaterfall
    Message FieldMoves_Text_WouldYouLikeToUseWaterfall
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_YES, FieldMoves_UseWaterfallFromField
    CloseMessage
    GoTo FieldMoves_End2
    End

FieldMoves_CantUseWaterfall:
    Message FieldMoves_Text_WallOfWater
    GoTo FieldMoves_ResonatorBlocked
    End

FieldMoves_UseWaterfallFromField:
    Call FieldMoves_ResonatorSurge
    SetVar VAR_0x8004, RESONATOR_SLOT_WATERFALL
    UseWaterfall VAR_0x8004
    GetCurrentMapID VAR_0x8004
    CreateJournalEvent LOCATION_EVENT_USED_WATERFALL, VAR_0x8004
    GoTo FieldMoves_End2
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
    CreateJournalEvent LOCATION_EVENT_USED_WATERFALL, VAR_0x8004
    ReleaseAll
    End

FieldMoves_Dummy8:
    End

// Stock-era entry (water with the badge but not Lapras); field_control now always sends water to FieldMoves_Water.
FieldMoves_WaterTotemNotDefeated:
    GoTo FieldMoves_Water
    End

// VAR_0x8007: the totem's surge line.
FieldMoves_ResonatorSurge:
    MessageFromBank TEXT_BANK_ARC2_COMMON, VAR_0x8007
    WaitABPadPress
    CloseMessage
    Return

// The obstacle's description is on screen; VAR_0x8006 is the line saying what's missing.
FieldMoves_ResonatorBlocked:
    WaitABPadPress
    MessageFromBank TEXT_BANK_ARC2_COMMON, VAR_0x8006
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

    .balign 4, 0
