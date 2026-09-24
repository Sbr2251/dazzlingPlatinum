#include "macros/btlcmd.inc"


_000:
    // The Totem's boosts are announced by the aura message alone
    UpdateVar OPCODE_SET, BTLVAR_SIDE_EFFECT_PARAM, MOVE_SUBSCRIPT_PTR_ATTACK_UP_1_STAGE
    ChangeStatStage _Defense, _Defense, _Defense

_Defense:
    UpdateVar OPCODE_SET, BTLVAR_SIDE_EFFECT_PARAM, MOVE_SUBSCRIPT_PTR_DEFENSE_UP_1_STAGE
    ChangeStatStage _Speed, _Speed, _Speed

_Speed:
    UpdateVar OPCODE_SET, BTLVAR_SIDE_EFFECT_PARAM, MOVE_SUBSCRIPT_PTR_SPEED_UP_1_STAGE
    ChangeStatStage _SpAttack, _SpAttack, _SpAttack

_SpAttack:
    UpdateVar OPCODE_SET, BTLVAR_SIDE_EFFECT_PARAM, MOVE_SUBSCRIPT_PTR_SP_ATTACK_UP_1_STAGE
    ChangeStatStage _SpDefense, _SpDefense, _SpDefense

_SpDefense:
    UpdateVar OPCODE_SET, BTLVAR_SIDE_EFFECT_PARAM, MOVE_SUBSCRIPT_PTR_SP_DEFENSE_UP_1_STAGE
    ChangeStatStage _Aura, _Aura, _Aura

_Aura:
    PlayBattleAnimation BTLSCR_ENEMY_SLOT_1, BATTLE_ANIMATION_TOTEM_AURA
    Wait
    // Totem {0}'s aura flared to life! Its stats rose!
    PrintGlobalMessage BattleStrings_Text_TotemAuraFlared, TAG_NICKNAME, BTLSCR_ENEMY_SLOT_1
    Wait
    WaitButtonABTime 30
    End
