#ifndef POKEPLATINUM_BATTLE_ANIM_EFFECT_BG_H
#define POKEPLATINUM_BATTLE_ANIM_EFFECT_BG_H

#include "constants/battle/battle_effect_bg.h"

#include "battle_anim/battle_anim_system.h"

#include "bg_window.h"

// Black 2/White 2's battle effect backgrounds for SwitchBg (bgID BATTLE_BG_BW2_FIRST and up) and their
// palette-cycle anims. docs/living_battle_stage/effect_bg.md has the design; the assets are built by
// tools/effect_bg/bw2_effect_bg.py into bw2_effect_bg.narc.

#define BATTLE_EFFECT_BG_NO_MEMBER 0xFFFF

typedef struct BattleEffectBgEntry {
    u16 ncgr; // 4bpp tiles, LZ
    u16 nclr; // our BG palette rows 8-15
    u16 nscr; // 512x256 screen, LZ
    u16 nscrReversed; // mirrored about the screen centre, for an enemy attacker (Platinum's NSCR2)
    u16 palAnim; // the anim's .bin member, started when the background loads, or BATTLE_EFFECT_BG_NO_MEMBER
    u16 rowMask; // BG palette rows the screen uses (row 9 always)
    u16 contestBg; // the pl_batt_bg bgID a contest shows instead
    u16 numTiles;
} BattleEffectBgEntry;

// Read by the emulator critic through the xMAP (tools/battle_stage/emu/critic.py, effect_bg.md)
typedef struct BattleEffectBgStats {
    u32 loads; // BW2 backgrounds loaded
    u32 cuts; // stage-to-background cuts made while the arena was visible
    u32 palAnimSteps; // palette anim rows applied
    u32 lastBgID; // the last BW2 bgID loaded
    u32 lastTiles; // its tile count (VRAM: 32 bytes each)
    u32 cutActive; // the stage is hidden by a cut right now
    u32 palAnimActive; // a palette anim task is running
} BattleEffectBgStats;

BOOL BattleEffectBg_IsBw2(int bgID);
int BattleEffectBg_ContestBg(int bgID);
void BattleEffectBg_Load(BattleAnimSystem *system, enum BgLayer layer, int bgID, BOOL reversed, BOOL blackBackdrop);
void BattleEffectBg_LoadOnVBlank(BattleAnimSystem *system, enum BgLayer layer, int bgID, BOOL reversed);
void BattleEffectBg_UploadOnVBlank(BgConfig *bgConfig, enum BgLayer layer, u8 colorMode, const void *chars, u32 charSize, void *charFile, const void *screen, u32 screenSize, void *screenFile, BOOL resetOffset);
void BattleEffectBg_CancelUpload(void);
BOOL BattleEffectBg_IsUploading(void);
u16 BattleEffectBg_PaletteMask(int bgID);
u16 BattleEffectBg_CurrentPaletteMask(void);
void BattleEffectBg_StartPalAnim(BattleAnimSystem *system, int anim, int loops);
void BattleEffectBg_StopPalAnim(void);
void BattleEffectBg_SetCut(BOOL cut);
BOOL BattleEffectBg_IsCut(void);
void BattleEffectBg_CountCut(void);
void BattleEffectBg_SetCutBack(BOOL cutBack);
BOOL BattleEffectBg_IsCutBack(void);
BOOL BattleEffectBg_IsCutBackDone(void);
void BattleEffectBg_Reset(void);

#endif // POKEPLATINUM_BATTLE_ANIM_EFFECT_BG_H
