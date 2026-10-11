#include "macros/btlcmd.inc"


_000:
    // In a Totem battle the Totem (always BATTLER_ENEMY_1) is not 'the wild {0}'
    CompareVarToValue OPCODE_FLAG_NOT, BTLVAR_BATTLE_SYS_STATUS, BATTLE_STATUS_TOTEM, _Default
    CompareVarToValue OPCODE_NEQ, BTLVAR_MSG_BATTLER_TEMP, BATTLER_ENEMY_1, _Default
    // Totem {0} is exerting its {1}!
    PrintGlobalMessage BattleStrings_Text_TotemExertingAbility, TAG_NICKNAME_ABILITY, BTLSCR_MSG_TEMP, BTLSCR_MSG_BATTLER_TEMP
    GoTo _End

_Default:
    // {0} is exerting its {1}!
    PrintMessage pl_msg_00000368_01238, TAG_NICKNAME_ABILITY, BTLSCR_MSG_TEMP, BTLSCR_MSG_BATTLER_TEMP

_End:
    Wait 
    WaitButtonABTime 30
    End 
