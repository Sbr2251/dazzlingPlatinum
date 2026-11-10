#include "macros/scrcmd.inc"
#include "res/text/bank/route_209_lost_tower_5f.h"


    ScriptEntry Route209LostTower5F_OldWoman1
    ScriptEntry Route209LostTower5F_OldWoman2
    ScriptEntry LostTower5F_OnTransition
    ScriptEntry LostTower5F_GraveSign
    ScriptEntryEnd

// Dazzling Platinum Arc 2 (s-hearthome, 2.24): Saros at Mira's grave. The cutaway runs from Lost Tower 1F's
// script (LostTower1F_SarosCutaway), which sets FLAG_ARC2_HEARTHOME_E while it stages 5F. Map-local here:
// FLAG_MAP_LOCAL_HIDE_OBSTACLE_16 hides Saros (shown only during the cutaway), FLAG_MAP_LOCAL_HIDE_OBSTACLE_17 hides the two old women then.
LostTower5F_OnTransition:
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    GoToIfUnset FLAG_ARC2_HEARTHOME_E, LostTower5F_OnTransitionEnd
    ClearFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_16
    SetFlag FLAG_MAP_LOCAL_HIDE_OBSTACLE_17
LostTower5F_OnTransitionEnd:
    End

LostTower5F_GraveSign:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message LostTower5F_Text_GraveSign
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

Route209LostTower5F_OldWoman1:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfUnset FLAG_USED_DEFOG_IN_ROUTE_209_LOST_TOWER_5F, Route209LostTower5F_ThisFogObscuresEverything
    GoToIfSet FLAG_RECEIVED_ROUTE_209_LOST_TOWER_5F_SPELL_TAG, Route209LostTower5F_FantinaIsARegularVisitor
    Message Route209LostTower5F_Text_DontBeShyTakeIt
    SetVar VAR_0x8004, ITEM_SPELL_TAG
    SetVar VAR_0x8005, 1
    GoToIfCannotFitItem VAR_0x8004, VAR_0x8005, VAR_RESULT, Route209LostTower5F_BagIsFull
    CallCommonScript CommonScript_AddItemQuantity
    SetFlag FLAG_RECEIVED_ROUTE_209_LOST_TOWER_5F_SPELL_TAG
    GoTo Route209LostTower5F_FantinaIsARegularVisitor
    End

Route209LostTower5F_FantinaIsARegularVisitor:
    Message Route209LostTower5F_Text_FantinaIsARegularVisitor
    WaitButton
    CloseMessage
    ReleaseAll
    End

Route209LostTower5F_ThisFogObscuresEverything:
    Message Route209LostTower5F_Text_ThisFogObscuresEverything
    WaitButton
    CloseMessage
    ReleaseAll
    End

Route209LostTower5F_OldWoman2:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    FacePlayer
    GoToIfUnset FLAG_USED_DEFOG_IN_ROUTE_209_LOST_TOWER_5F, Route209LostTower5F_ThisFogObscuresEverything2
    GoToIfSet FLAG_RECEIVED_ROUTE_209_LOST_TOWER_5F_CLEANSE_TAG, Route209LostTower5F_PokemonFindSolaceHere
    Message Route209LostTower5F_Text_TakeThis
    SetVar VAR_0x8004, ITEM_CLEANSE_TAG
    SetVar VAR_0x8005, 1
    GoToIfCannotFitItem VAR_0x8004, VAR_0x8005, VAR_RESULT, Route209LostTower5F_BagIsFull
    CallCommonScript CommonScript_AddItemQuantity
    SetFlag FLAG_RECEIVED_ROUTE_209_LOST_TOWER_5F_CLEANSE_TAG
    GoTo Route209LostTower5F_PokemonFindSolaceHere
    End

Route209LostTower5F_PokemonFindSolaceHere:
    Message Route209LostTower5F_Text_PokemonFindSolaceHere
    WaitButton
    CloseMessage
    ReleaseAll
    End

Route209LostTower5F_BagIsFull:
    CallCommonScript CommonScript_BagIsFull
    CloseMessage
    ReleaseAll
    End

Route209LostTower5F_ThisFogObscuresEverything2:
    Message Route209LostTower5F_Text_ThisFogObscuresEverything2
    WaitButton
    CloseMessage
    ReleaseAll
    End
