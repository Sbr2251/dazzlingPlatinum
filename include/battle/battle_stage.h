#ifndef POKEPLATINUM_BATTLE_BATTLE_STAGE_H
#define POKEPLATINUM_BATTLE_BATTLE_STAGE_H

#include "struct_decls/battle_system.h"

#include "palette.h"

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
    BATTLE_STAGE_SUPPRESS_WINDOW = 1 << 5, // a move window shapes the BG3 backdrop under the arena (compat.md, F3)
};

void BattleStage_Suppress(u32 reasons, BOOL suppress);
// TRUE when this battle's background and terrain pieces loaded into an arena; FALSE keeps
// the classic scene for the whole battle
BOOL BattleStage_HasArena(void);
// TRUE while the arena is drawn: enabled, loaded for this battle and not suppressed, or
// still fading out after a suppression started during a move animation (compat.md, F6).
// The stage sprites stay on the stage path for as long as this is TRUE.
BOOL BattleStage_IsVisible(void);
// TRUE while nothing but the battle uses the 3D texture VRAM: there is an arena and no menu
// has taken over, even when the arena is hidden (the debug toggle, a move's backdrop). The
// sprite streams keep playing then, and the sprites draw them flat (sprite_stream.md)
BOOL BattleStage_KeepsTextureVram(void);
// TRUE while the arena is drawn translucent, fading out or back in
BOOL BattleStage_IsFading(void);
// The anim system: a move animation (or its background restore) is running. Suppressions
// that start while it is TRUE fade the arena out over SCREEN_FRAMES(8); the others, the menu
// and the debug toggle hide it at once.
void BattleStage_SetInMoveAnim(BOOL inMoveAnim);

// Debug views (DEBUG_BATTLE_TOOLS): 0 = home pose, others orbit the camera to show the
// arena is 3D. They are stage camera poses, so the sprites and particles follow.
void BattleStage_SetDebugView(int view);
int BattleStage_GetDebugView(void);

// The 2D brightness blend skips BG0, so an effect that dims or flashes the scene with it
// passes the same value here (-16..16, as G2_SetBlendBrightness). While it is not 0 it
// replaces the atmosphere fog on the FOG meshes: black when negative, white when positive,
// at |brightness| * 8 / 128. 0 brings the atmosphere fog back. Init and Free reset it to 0.
void BattleStage_SetBrightness(int brightness);
// A curtain in 3D (moves.md, category C: Fake Out): flat bars in the 2D backdrop colour (BG
// palette colour 0, as displayed) over the arena and the shadows but under the mons,
// covering the screen columns left of `left` and from `right` on. It stays until
// BattleStage_ClearCurtain; the anim system's End and Delete clear it too.
void BattleStage_SetCurtain(int left, int right);
void BattleStage_ClearCurtain(void);

// A move's palette fade or grayscale of the backdrop (FadeBg FADE_BG_TYPE_BASE,
// SetBgGrayscale, Fake Out's curtain). The arena's textures take the faded BG palette, so
// they follow the backdrop on their own; this brings the rest of the arena along: the fog
// colour and the light of the LIT meshes are grayed, then faded towards color by
// alpha / 16 (0..16, as PaletteData_StartFade), so a full fade reads as the flat colour as
// in classic. The brightness above wins while it is not 0. The move anim system feeds it
// every script frame and clears it at script end; alpha 0 and no grayscale draw as before.
// Init and Free reset it.
void BattleStage_SetBackdropFade(u16 color, int alpha);
void BattleStage_SetBackdropGrayscale(BOOL grayscale);

// Lit, deformable sprites (chunk 3, battle_stage_sprites.c). While the arena shows, the
// battle's mons are drawn as lit 8x8 grids that breathe at rest, with a blob shadow.
// A move or anim script is running: the battle anim system sets it every script frame,
// and the idle breathing pauses while it is TRUE
void BattleStage_SetMoveAnimActive(BOOL active);
// The battler took damage (the hit blink task): its sprite does a short wobble
void BattleStage_NotifyHit(int battler);
// The battler's sprite was drawn from its Gen 5 stream in the last frame (on the mesh, or flat
// with the arena hidden). A static 2D copy of its 80x80 frame A can't match that sprite, so
// a copy that only sits over it (SpriteToOAM, the send-out copies) stays hidden.
BOOL BattleStage_IsSpriteStreamed(int battler);
// For a 2D copy that stands in for a streamed battler (a move's BG or OAM copy): writes the
// classic 80x80 window of the stream frame on screen over tiles, as 100 4bpp tiles in the
// order of CharacterSprite_LoadPokemonSprite, so the copy keeps the pose instead of snapping
// to frame A. FALSE, and tiles untouched, when the battler isn't streamed.
BOOL BattleStage_GetStreamFrameTiles(int battler, u8 *tiles);

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
// A move's BG3 shake over the normal backdrop, in BG scroll sign (the picture moves by -dx,
// -dy): the camera moves the arena, mons and particles with it. (0, 0) drops it. It does not
// count as off home (offHomeFrames); it sets BATTLE_STAGE_CAMERA_SHAKING.
void BattleStage_SetBackdropShake(int dx, int dy);
// Command 89 waits while this is TRUE: an ease or a shake is in progress
BOOL BattleStage_IsCameraMoving(void);
// The home guard: every anim script start snaps the camera home (outside contests)
void BattleStage_CameraScriptStart(void);
// Right after the script started: the cinematic bit its first camera command sets
void BattleStage_SetCameraScriptCinematic(u32 cinematic);
// Right after the script started: if it ends off home, the camera holds there (as the
// battle-start focus) until the next command menu request instead of easing home
void BattleStage_HoldCameraAfterScript(void);
// The battle-start sweep, at each command menu request; it plays once per battle unless the
// battle-start focus played. It also releases a focus still holding (no send-out: Safari; the
// Totem aura).
void BattleStage_StartBattleSweep(void);
// The battle-start focus: when the opponent's healthbar first slides in, the camera pushes in
// on the opponents and holds there until the player's side sends out
void BattleStage_StartIntroFocus(void);
// The player's side is sending out: the focus eases home (after its least hold). Before the
// focus started, it keeps the focus from starting (the player sent out first).
void BattleStage_EndIntroFocus(void);
// A send-out (a trainer's throw, an opponent turning into an OBJ) waits until this is TRUE:
// no focus holds or eases home. Call it once per frame while waiting; it snaps after a cap.
BOOL BattleStage_IsIntroFocusDone(void);
// The mean screen offset of a side's anchors from home while the camera is off home, for the
// 2D trainer OBJs. FALSE (and 0, 0) at home.
BOOL BattleStage_GetSideOffset(int side, int *dx, int *dy);
// The command menu waits until this is TRUE: the camera is home, or it has waited too long
// (then the camera snaps home). Call it once per frame while waiting.
BOOL BattleStage_IsCameraReadyForMenu(void);
// The idle drift (Gen 5's command menu camera): once the command menu is up, the camera holds
// home for a second, then loops slowly through a few gentle poses. It does nothing while
// NO_CINEMATICS or NO_IDLE_CAMERA is set, and a menu shown while it runs doesn't wait.
// EndIdleCamera, when every battler's command is in, eases it home; an anim script start or
// a hidden arena snaps it home without counting a guard snap.
void BattleStage_StartIdleCamera(void);
void BattleStage_EndIdleCamera(void);
// The hit blink started on a battler; critical is TRUE when the hit was a critical hit
void BattleStage_CritKick(int battler, BOOL critical);
// The fainting sequence of a battler started
void BattleStage_FaintKick(int battler);

// Move compatibility (chunk 5; docs/living_battle_stage/compat.md). The critic reads these
// from RAM at sBattleStage+96; they are zeroed per battle with the rest of sBattleStage.
typedef struct BattleStageCompatFields {
    u32 hardPops; // +96: the arena went from visible to hidden in one frame, with no fade
    u32 hiddenFrames; // +100: drawn frames the arena was loaded and enabled but hidden
    u32 fades; // +104: the arena faded out through its alpha instead of popping
    u32 arenaAlpha; // +108: the arena's current polygon alpha, 0..31 (31 = opaque)
    u32 liftedBg2Frames; // +112: drawn frames with BG2 lifted above the 3D layer (a mon copy, or Surf's and Muddy Water's water)
    u32 tintedCopies; // +116: mon copies (BG2 or OAM) given the arena's sprite tint this battle
} BattleStageCompatFields;

// The compat fields of this battle; never NULL
BattleStageCompatFields *BattleStage_CompatFields(void);

// The arena's sprite tint for 2D copies of a mon (compat.md, F2): the per-channel factor,
// in 1/256, that the lit mesh applies to a camera-facing texel at the current time of day.
// FALSE (leave the colours alone) when the stage isn't visible, the sprites are classic or
// every channel is 256, as at day.
BOOL BattleStage_GetSpriteTint(u16 *tintR, u16 *tintG, u16 *tintB);
// Multiplies colours start..start+count-1 of a palette buffer, unfaded and faded, by the
// sprite tint and counts a tinted copy; FALSE and nothing changed when there is no tint
BOOL BattleStage_TintCopyPalette(PaletteData *paletteData, enum PaletteBufferID bufferID, u16 start, u16 count);
// BG2 holds a mon copy (compat.md, F1) or a water picture (moves.md, D) lifted above the 3D
// layer; counted per drawn frame
void BattleStage_SetBg2Lifted(BOOL lifted);
// A dark hole in the arena ground under a battler, for Dig (moves.md, D). It opens and closes
// over a few drawn frames; nothing is drawn while it is shut. ClearGroundHoles shuts every
// hole at once, as at the end of a script.
void BattleStage_SetGroundHole(int battler, BOOL open);
void BattleStage_ClearGroundHoles(void);

#endif // POKEPLATINUM_BATTLE_BATTLE_STAGE_H
