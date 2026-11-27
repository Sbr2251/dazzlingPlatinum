#ifndef POKEPLATINUM_BATTLE_BATTLE_HUD_H
#define POKEPLATINUM_BATTLE_BATTLE_HUD_H

#include <nitro/types.h>

#include "struct_decls/battle_system.h"

#include "battle/battle_subscreen.h"

// Battle HUD (lane battlehud, phase 2): mirrors the battle command menu,
// move select (with PP and the Mega toggle state), doubles target select
// and the yes/no prompts onto the TOP (main) screen as a bottom-anchored
// panel above the battle message box, in the style of later games.
//
// The bottom-screen menus keep working exactly as before (D-pad + A/B and
// sub-screen touch are untouched); the HUD is a second, top-screen view of
// the same BattleSubscreen state, refreshed from BattleSystem_MenuInput.
// In the wide layout the HUD also tells the simulator the bottom panel is
// not needed (SIM_Layout_SetBattleTouchNeeded(0)) while it is active.
//
// Switch: BattleHud in sim_config_prj.ini [General], ON by default in the
// app, OFF under SIM_HEADLESS unless SIM_FX_BATTLEHUD=1 (goldens stay
// byte-identical). No-op under Renderer=gl is NOT required game-side (the
// HUD is game 2D), but the wide panel suppression only takes effect on
// the GPU wide composite.

#ifdef __cplusplus
extern "C" {
#endif

BOOL BattleHud_IsEnabled(void);
BOOL BattleHud_IsWidePixelMode(void);
BOOL BattleHud_IsHdMode(void);
// TRUE when the BDSP 3D battle + corner HUD is active (wide layout, battle
// HUD on, 3D arena on). D-pad cursor code uses this to match the vertical
// corner-HUD stacks instead of the DS 2D button grid.
BOOL BattleHud_IsBdspCornerHud(void);
BOOL BattleHud_IsWindowVisible(void);

// Wide pixel mode (342x192, 43x24 tiles): extend the authentic Platinum
// message box frame cleanly across the bottom of the 16:9 screen.
void BattleHud_DrawWideMessageFrame(BattleSystem *battleSys);

// Call every frame a battle menu is up (from BattleSystem_MenuInput).
// Returns a touch-array button index when a main-screen click confirms
// a button, else -1.
int BattleHud_Update(BattleSubscreen *btlSubscreen);
// Call when the subscreen returns to the idle menu (config 0) / battle end.
void BattleHud_Hide(BattleSubscreen *btlSubscreen);
// Call when a menu input is confirmed: panel hides, healthboxes return.
void BattleHud_HideOnConfirm(BattleSubscreen *btlSubscreen);

// Main-screen click hit test (DS coords): returns the touch-array
// button index for a click at (x, y), or -1. Clicks are routed by the
// simulator only while the HUD has opted in (SIM_Layout main touch).
int BattleHud_TopTouchButton(BattleSubscreen *btlSubscreen, int x, int y);

// HD battle HUD (BDSP parity): submit SIM_HudHD_Frame every battle frame
// (active = 0 when hidden or reset).
void BattleHud_SyncFrame(BattleSystem *battleSys);
void BattleHud_Reset(void);

#ifdef __cplusplus
}
#endif

#endif // POKEPLATINUM_BATTLE_BATTLE_HUD_H
