#include "macros/btlcmd.inc"
#include "generated/trainer_message_types.h"


_000:
    // Show trainer mega evolution dialog if the trainer has one. The controller sets MSG_TEMP to
    // TRMSG_MEGA_EVOLUTION only for an opposing trainer that has this message, since looking it up is slow.
    CompareVarToValue OPCODE_NEQ, BTLVAR_MSG_TEMP, TRMSG_MEGA_EVOLUTION, _key_stone
    PrintTrainerMessage BTLSCR_MSG_TEMP, TRMSG_MEGA_EVOLUTION
    Wait
    WaitButtonABTime 30

_key_stone:
    // {0}'s {1} is reacting to {2}'s Key Stone!
    // This message stays up during the animation, so only a short pause is needed before it starts.
    PrintMessage BattleStrings_Text_MegaEvolutionReacting, TAG_NICKNAME_ITEM_TRNAME, BTLSCR_MSG_TEMP, BTLSCR_MSG_BATTLER_TEMP, BTLSCR_MSG_TEMP
    Wait
    WaitButtonABTime 15

    // Handle substitute: remove it temporarily before animation
    CompareMonDataToValue OPCODE_FLAG_NOT, BTLSCR_MSG_TEMP, BATTLEMON_VOLATILE_STATUS, VOLATILE_CONDITION_SUBSTITUTE, _016
    PlayBattleAnimation BTLSCR_MSG_TEMP, BATTLE_ANIMATION_SUB_OUT
    Wait
    RestoreSprite BTLSCR_MSG_TEMP
    Wait
    PlayBattleAnimation BTLSCR_MSG_TEMP, BATTLE_ANIMATION_SUB_IN
    Wait

_016:
    // Affine Pulse charge: dim, whiten, compress, and conceal the base form
    PlaySound BTLSCR_MSG_TEMP, SEQ_SE_MEGA_CHARGE
    AffinePulse BTLSCR_MSG_TEMP, 0
    Wait
    // Swap forms only while the sprite is fully concealed
    ChangeForm BTLSCR_MSG_TEMP
    Wait
    // Affine Pulse reveal: flash, elastic overshoot, settle, and restore
    PlaySound BTLSCR_MSG_TEMP, SEQ_SE_MEGA_BURST
    AffinePulse BTLSCR_MSG_TEMP, 1
    Wait
    // Sparkle effect after the Mega sprite has settled
    PlayBattleAnimation BTLSCR_MSG_TEMP, BATTLE_ANIMATION_SHINY
    Wait
    // {0} Mega Evolved!
    PrintMessage pl_msg_00000368_01269, TAG_NICKNAME, BTLSCR_MSG_TEMP
    Wait
    WaitButtonABTime 30
    // Restore substitute if it was up
    CompareMonDataToValue OPCODE_FLAG_NOT, BTLSCR_MSG_TEMP, BATTLEMON_VOLATILE_STATUS, VOLATILE_CONDITION_SUBSTITUTE, _058
    PlayBattleAnimation BTLSCR_MSG_TEMP, BATTLE_ANIMATION_SUB_OUT
    Wait
    RefreshSprite BTLSCR_MSG_TEMP
    Wait
    PlayBattleAnimation BTLSCR_MSG_TEMP, BATTLE_ANIMATION_SUB_IN
    Wait

_058:
    End
