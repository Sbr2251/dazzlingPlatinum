#include "macros/btlcmd.inc"
#include "generated/trainer_message_types.h"


_000:
    // Show trainer mega evolution dialog if the trainer has one
    PrintTrainerMessage BTLSCR_MSG_TEMP, TRMSG_MEGA_EVOLUTION
    Wait
    WaitButtonABTime 30
    // {0}'s {1} is reacting to {2}'s Key Stone!
    PrintMessage BattleStrings_Text_MegaEvolutionReacting, TAG_NICKNAME_ITEM_TRNAME, BTLSCR_MSG_TEMP, BTLSCR_MSG_BATTLER_TEMP, BTLSCR_MSG_TEMP
    Wait
    WaitButtonABTime 30

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
    // Rainbow energy converges into a cocoon; runs alongside the pulse, whose Wait covers both
    PlayBattleAnimation BTLSCR_MSG_TEMP, BATTLE_ANIMATION_MEGA_EVOLUTION_CHARGE
    PlaySound BTLSCR_MSG_TEMP, 1980
    AffinePulse BTLSCR_MSG_TEMP, 0
    Wait
    // Swap forms only while the sprite is fully concealed
    ChangeForm BTLSCR_MSG_TEMP
    Wait
    // Affine Pulse reveal: flash, elastic overshoot, settle, and restore
    // The cocoon shatters and the Mega symbol appears; runs alongside the pulse
    PlayBattleAnimation BTLSCR_MSG_TEMP, BATTLE_ANIMATION_MEGA_EVOLUTION
    PlaySound BTLSCR_MSG_TEMP, 1984
    AffinePulse BTLSCR_MSG_TEMP, 1
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
