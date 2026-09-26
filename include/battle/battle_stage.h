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
    // A 2D brightness/blend effect that skips BG0 and can't use BattleStage_SetBrightness.
    // Nothing uses it now: the Mega pulse dims the arena with BattleStage_SetBrightness
    BATTLE_STAGE_SUPPRESS_BRIGHTNESS = 1 << 2,
    BATTLE_STAGE_SUPPRESS_MENU = 1 << 3, // a screen that owns the 3D layer or VRAM
    BATTLE_STAGE_SUPPRESS_OTHER = 1 << 4,
};

void BattleStage_Suppress(u32 reasons, BOOL suppress);
// TRUE when this battle's background and terrain pieces loaded into an arena; FALSE keeps
// the classic scene for the whole battle
BOOL BattleStage_HasArena(void);
// TRUE when the arena is enabled, loaded for this battle and not suppressed
BOOL BattleStage_IsVisible(void);

// Debug views (DEBUG_BATTLE_TOOLS): 0 = home pose, others orbit the camera to show the
// arena is 3D. Sprites do not follow the camera yet (chunks 3-4).
void BattleStage_SetDebugView(int view);
int BattleStage_GetDebugView(void);

// The 2D brightness blend skips BG0, so an effect that dims or flashes the scene with it
// passes the same value here (-16..16, as G2_SetBlendBrightness). While it is not 0 it
// replaces the atmosphere fog on the FOG meshes: black when negative, white when positive,
// at |brightness| * 8 / 128. 0 brings the atmosphere fog back. Init and Free reset it to 0.
void BattleStage_SetBrightness(int brightness);

// Lit, deformable sprites (chunk 3, battle_stage_sprites.c). While the arena shows, the
// battle's mons are drawn as lit 8x8 grids that breathe at rest, with a blob shadow.
// A move or anim script is running: the battle anim system sets it every script frame,
// and the idle breathing pauses while it is TRUE
void BattleStage_SetMoveAnimActive(BOOL active);
// The battler took damage (the hit blink task): its sprite does a short wobble
void BattleStage_NotifyHit(int battler);

#endif // POKEPLATINUM_BATTLE_BATTLE_STAGE_H
