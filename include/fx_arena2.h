#ifndef POKEPLATINUM_FX_ARENA2_H
#define POKEPLATINUM_FX_ARENA2_H

#include <nitro.h>

#include "constants/battle.h"
#include "field/field_system_decl.h"
#include "struct_decls/battle_system.h"

// Lane arena2: battles in the actual place. At a wild/trainer encounter,
// the field (after the arena swoop has dived toward the player) is
// captured from a low, battle-like camera with the map objects hidden,
// with the DS display capture into VRAM C, quantized to the 256-colour
// 3-3-2 palette the battle stage's backdrop textures use, and kept in
// a static buffer across the field teardown. BattleStage then swaps the
// captured image into the backdrop piece in place of the prebuilt
// backdrop NARC art, and the battle's BG3 backdrop is rewritten with the
// same image, so the arena, its home pose and the BG3 fallback a 2D move
// effect swaps to all show the same real image, with no visual pop.
//
// Presentation only: nothing here changes battle mechanics, RNG-visible
// state or save data. The feature is off under SIM_HEADLESS unless
// SIM_FX_REALPLACE=1, so existing golden screenshots stay byte-identical.
// Eligible backgrounds are the outdoor ones (plain, water, city, forest,
// mountain, snow); interiors, caves, Elite Four rooms, the Distortion
// World and Frontier facilities fall back to the classic backdrop, as
// does the wide layout: the simulator's display capture only covers
// the left ~55% of the capture target in wide mode.

#define FX_ARENA2_WIDTH 256
#define FX_ARENA2_HEIGHT 192
// Backdrop texture A holds rows 0..127, texture B rows 127..158
// (tools/battle_stage/arena.py: TEX_A_ROWS, TEX_B_FIRST_ROW, TEX_B_ROWS).
#define FX_ARENA2_TEX_A_ROWS 128
#define FX_ARENA2_TEX_B_FIRST_ROW 127
#define FX_ARENA2_TEX_B_ROWS 32
#define FX_ARENA2_TEX_A_BYTES (FX_ARENA2_WIDTH * FX_ARENA2_TEX_A_ROWS)
#define FX_ARENA2_TEX_B_BYTES (FX_ARENA2_WIDTH * FX_ARENA2_TEX_B_ROWS)
// BG3 backdrop: 32x20 tiles of 8x8 8bpp pixels (the bottom 32 rows of
// the 256x192 frame are under the text box).
#define FX_ARENA2_BG3_TILES_W 32
#define FX_ARENA2_BG3_TILES_H 20
#define FX_ARENA2_BG3_TILE_BYTES 64
#define FX_ARENA2_BG3_TILES_BYTES (FX_ARENA2_BG3_TILES_W * FX_ARENA2_BG3_TILES_H * FX_ARENA2_BG3_TILE_BYTES)

// Feature gate: sim_config_prj.ini [General] RealPlaceArena (on by
// default in the app).
BOOL FxArena2_RealPlaceEnabled(void);

// TRUE when this field can supply a capture: the feature is on, the
// field is loaded, and its battle background is an eligible outdoor one.
BOOL FxArena2_ShouldCapture(const FieldSystem *fieldSystem);
// The battle background the field would use (surfing counts as water),
// for eligibility and for matching the capture to the battle.
enum BattleBackground FxArena2_FieldBackground(const FieldSystem *fieldSystem);
BOOL FxArena2_BackgroundEligible(enum BattleBackground background);

// Hide every map object (player, NPCs, follower, and their shadows and
// emotes) for the capture frame. RestoreMapObjects brings back exactly
// the ones this hid; objects already hidden stay hidden.
void FxArena2_HideMapObjects(const FieldSystem *fieldSystem);
void FxArena2_RestoreMapObjects(const FieldSystem *fieldSystem);

// The low, battle-like capture camera: behind the player, looking the
// way the player faces, pitched a few degrees down with a ~38 degree
// field of view and a near clip that keeps the foreground ground in
// range, so the horizon sits in the frame and the terrain ahead reads
// as a battle backdrop. SaveCamera snapshots the field camera;
// RestoreCamera puts it back exactly.
void FxArena2_SaveCamera(const FieldSystem *fieldSystem);
void FxArena2_SetCaptureCamera(const FieldSystem *fieldSystem);
void FxArena2_RestoreCamera(const FieldSystem *fieldSystem);

// Arm the DS display capture for the next rendered frame. Clears any
// previous capture first, so a failed capture never shows stale art.
void FxArena2_StartCapture(const FieldSystem *fieldSystem);
// Copy VRAM C (the capture target) into the static buffer and quantize
// it. Call after at least one rendered frame has passed since
// StartCapture. A capture that reads back as all one colour (the capture
// did not run) is dropped, and the battle falls back to the classic
// backdrop.
void FxArena2_FinishCapture(void);
// TRUE when a capture is waiting for the next battle to consume it.
BOOL FxArena2_HasCapture(void);
// The background the waiting capture was taken on.
enum BattleBackground FxArena2_CaptureBackground(void);
// Palette entry (GXRgb) for a quantized index: the 3-3-2 palette,
// softened (desaturated and darkened) so the backdrop sits behind the
// battlers instead of competing with them. The same for every capture,
// so the stage only needs the indices.
u16 FxArena2_PaletteEntry(int index);
// Quantized index at (x, y) of the waiting capture.
u8 FxArena2_CaptureIndex(int x, int y);
// Drop the waiting capture (battle over, or a battle that did not use it).
void FxArena2_ClearCapture(void);

// Rewrite the battle's BG3 backdrop (tiles, palette, the one tilemap
// entry that shares a char) with the waiting capture, for every BG3
// load site in the battle: battle init, and the anim system's
// RestoreBg. No-op when there is no capture for this battle. The BG
// palette's winframe/font slots (160..191) are preserved, and the
// capture's quantization never produces those indices, so the text box
// frame and the font keep their colours.
void FxArena2_ApplyToBattleBg(BattleSystem *battleSys);

#endif // POKEPLATINUM_FX_ARENA2_H
