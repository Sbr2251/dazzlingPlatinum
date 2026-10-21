#ifndef POKEPLATINUM_BATTLE_ABILITY_POPUP_H
#define POKEPLATINUM_BATTLE_ABILITY_POPUP_H

#include <nitro/types.h>

#include "battle/battle_message.h"
#include "battle/ov16_0223DF00.h"

// Gen 5 ability pop-up banner (BW2's BtlvScuAbilityWin, pokebw2 btlv_scu.c:2472-2650), drawn as OBJs because
// BG2 and BG3 are taken in this battle. When a battle message names the ability of the Pokemon it is about
// ("<Pokemon>'s <Ability> ..."), a banner with "<Pokemon>'s" over "<Ability>" slides in on that Pokemon's side,
// stays while the message prints and a little after, then slides out. The message itself is kept.
// See docs/battle_events.md.

// Called for every message the battle script prints (BattleDisplay_PrintMessage). printerID is the text printer
// that prints it, so the banner can stay up while the message is printing.
void AbilityPopup_OnBattleMessage(BattleSystem *battleSys, const BattleMessage *msg, u8 printerID);

// Frees both banners at once. Call before the battle's sprite system is torn down.
void AbilityPopup_Shutdown(void);

// TRUE while either side's banner is on screen or moving.
BOOL AbilityPopup_IsActive(void);

#endif // POKEPLATINUM_BATTLE_ABILITY_POPUP_H
