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
// arena is 3D. They are stage camera poses, so the sprites and particles follow.
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

// The stage camera (chunk 4, battle_stage_camera.c; docs/living_battle_stage/camera.md). At
// its home pose nothing changes; off home the arena, the stage sprites and the particles
// follow it. Nothing moves while the stage isn't visible.

// Bits of the cinematics seen this battle (the critic reads them)
enum BattleStageCinematic {
    BATTLE_STAGE_CINEMATIC_SWEEP = 1 << 0,
    BATTLE_STAGE_CINEMATIC_MEGA = 1 << 1,
    BATTLE_STAGE_CINEMATIC_TOTEM = 1 << 2,
    BATTLE_STAGE_CINEMATIC_CRIT = 1 << 3,
    BATTLE_STAGE_CINEMATIC_FAINT = 1 << 4,
    BATTLE_STAGE_CINEMATIC_SCRIPT = 1 << 5, // an anim script used a camera command
};

// Anim script commands 85-88. focus is a STAGE_CAMERA_FOCUS_* constant; attacker and
// defender are the script's battlers. Frames count drawn frames; 0 snaps.
void BattleStage_CameraMove(int focus, int attacker, int defender, int distancePct, int yawDeg, int pitchDeg, int frames);
void BattleStage_CameraOrbit(int yawDeltaDeg, int frames);
void BattleStage_CameraShake(int amplitudePx, int frames);
void BattleStage_CameraHome(int frames);
// Command 89 waits while this is TRUE: an ease or a shake is in progress
BOOL BattleStage_IsCameraMoving(void);
// The home guard: every anim script start snaps the camera home (outside contests)
void BattleStage_CameraScriptStart(void);
// Right after the script started: the cinematic bit its first camera command sets
void BattleStage_SetCameraScriptCinematic(u32 cinematic);
// The battle-start sweep, at each command menu request; it plays once per battle
void BattleStage_StartBattleSweep(void);
// The command menu waits until this is TRUE: the camera is home, or it has waited too long
// (then the camera snaps home). Call it once per frame while waiting.
BOOL BattleStage_IsCameraReadyForMenu(void);
// The hit blink started on a battler; critical is TRUE when the hit was a critical hit
void BattleStage_CritKick(int battler, BOOL critical);
// The fainting sequence of a battler started
void BattleStage_FaintKick(int battler);

#endif // POKEPLATINUM_BATTLE_BATTLE_STAGE_H
