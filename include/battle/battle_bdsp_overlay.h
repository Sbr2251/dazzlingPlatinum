#ifndef POKEPLATINUM_BATTLE_BDSP_OVERLAY_H
#define POKEPLATINUM_BATTLE_BDSP_OVERLAY_H

#include "battle/battle_system.h"
#include "battle_sub_menus/battle_bag.h"
#include "battle_sub_menus/battle_party.h"
#include "port/sim_hud_hd.h"

// BDSP HD In-Battle Bag & Party Overlays (owned by Lane 3: overlays).
// Runs directly over the live 3D battle scene (no BattleSystem_EnterSubMenu
// teardown or fade-to-black) when SIM_Battle3D_ModelsEnabled() is active.
void BattleBdspOverlay_Reset(void);
BOOL BattleBdspOverlay_ShouldUse(BattleSystem *battleSys);
void BattleBdspOverlay_StartBag(BattleBagContext *ctx);
void BattleBdspOverlay_StartParty(BattlePartyContext *ctx);
BOOL BattleBdspOverlay_IsActive(void);
void BattleBdspOverlay_Tick(BattleSystem *battleSys);
void BattleBdspOverlay_FillFrame(BattleSystem *battleSys, SIM_HudHD_Frame *frame);

#endif // POKEPLATINUM_BATTLE_BDSP_OVERLAY_H
