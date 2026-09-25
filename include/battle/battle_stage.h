#ifndef POKEPLATINUM_BATTLE_BATTLE_STAGE_H
#define POKEPLATINUM_BATTLE_BATTLE_STAGE_H

#include "struct_decls/battle_system.h"

// The 3D arena drawn behind the battle sprites. With BATTLE_STAGE_3D off, every function does nothing.
void BattleStage_Init(BattleSystem *battleSys);
void BattleStage_Free(void);

// Called from the battle draw task, before particles and sprites
void BattleStage_Draw(void);

// Live on/off switch (the debug A/B toggle); the stage starts enabled
void BattleStage_SetEnabled(BOOL enabled);
BOOL BattleStage_IsEnabled(void);

// Reasons the arena is temporarily hidden, falling back to the classic BG3 backdrop and
// OBJ platforms. At home pose the arena matches the classic backdrop, so the swap is
// nearly invisible. Several reasons can be active at once.
enum BattleStageSuppress {
    BATTLE_STAGE_SUPPRESS_BG_SWITCH = 1 << 0, // a move replaced/animates the BG3 backdrop
    BATTLE_STAGE_SUPPRESS_BG2_EFFECT = 1 << 1, // a move draws on BG2 (under the 3D layer)
    BATTLE_STAGE_SUPPRESS_BRIGHTNESS = 1 << 2, // a 2D brightness/blend effect that skips BG0
    BATTLE_STAGE_SUPPRESS_MENU = 1 << 3, // a screen that owns the 3D layer or VRAM
    BATTLE_STAGE_SUPPRESS_OTHER = 1 << 4,
};

void BattleStage_Suppress(u32 reasons, BOOL suppress);
// TRUE when the arena is enabled, loaded for this battle and not suppressed
BOOL BattleStage_IsVisible(void);

// Debug views (DEBUG_BATTLE_TOOLS): 0 = home pose, others orbit the camera to show the
// arena is 3D. Sprites do not follow the camera yet (chunks 3-4).
void BattleStage_SetDebugView(int view);
int BattleStage_GetDebugView(void);

#endif // POKEPLATINUM_BATTLE_BATTLE_STAGE_H
