#include "battle/battle_textbox.h"

#include <nitro.h>
#include <string.h>

#include "battle/battle_stage.h"
#include "battle/ov16_0223DF00.h"

#include "gx_layers.h"
#include "pokemon_sprite.h"
#include "system.h"
#include "text.h"

// BW2's fade is 6 frames at 60 Hz (btlv_scu.c:2298-2324). The battle logic here steps at
// 30 Hz, so each update moves the fade by the vblanks since the last one.
#define TEXTBOX_FADE_FRAMES 6
#define TEXTBOX_MAX_STEP    4 // vblanks one update may advance (after a pause)

// A finished message stays fully shown this long before a hide may start, unless A or B is
// held (BW2 waits 80 frames after a message before the next step, skippable the same way:
// btlv_scu.c:1885-1893). Platinum plays the move right after "X used Y!", so without the
// hold the box would go the moment the last letter printed.
#define TEXTBOX_READ_HOLD 30
// The longest an animation waits for the box (logic frames), then it plays with the box up
#define TEXTBOX_READY_WAIT_MAX 90

// BW2's planes (btlv_scu.c:2290): the box over everything else
#define TEXTBOX_BLEND_FIRST  GX_BLEND_PLANEMASK_BG1
#define TEXTBOX_BLEND_SECOND (GX_BLEND_PLANEMASK_BG0 | GX_BLEND_PLANEMASK_BG2 | GX_BLEND_PLANEMASK_BG3 | GX_BLEND_PLANEMASK_OBJ | GX_BLEND_PLANEMASK_BD)
#define BLDCNT_FIRST_MASK    0x3F
#define BLDCNT_MODE_MASK     0xC0
#define BLDCNT_MODE_ALPHA    0x40

enum TextboxState {
    TEXTBOX_STATE_SHOWN = 0,
    TEXTBOX_STATE_HIDING,
    TEXTBOX_STATE_HIDDEN,
    TEXTBOX_STATE_SHOWING,
};

typedef struct Textbox {
    BattleSystem *battleSys;
    u32 lastVBlank;
    u32 prior; // BLDCNT | BLDALPHA << 16 before the fade took them
    u32 written; // what the fade wrote last, to tell when someone else took them
    u16 readVBlanks; // since the last message finished printing
    u16 holdVBlanks; // since the pending hide was asked for
    u8 printer;
    u8 printing;
    u8 owned; // the fade holds the blend registers
    u8 hidBg1; // BG1 is off because of the box (only then does a show turn it on)
} Textbox;

static Textbox sTextbox;
BattleTextboxStats sBattleTextbox;

static BOOL Bg1On(void)
{
    return (GXLayers_EngineAGetLayers() & GX_PLANEMASK_BG1) != 0;
}

static u32 ReadBlend(void)
{
    return reg_G2_BLDCNT | ((u32)reg_G2_BLDALPHA << 16);
}

// Takes the blend registers for a fade when nobody else blends a layer; FALSE: do it at once
static BOOL TakeBlend(void)
{
    u32 blend;

    if (sTextbox.owned) {
        return TRUE;
    }

    blend = ReadBlend();

    if ((blend & BLDCNT_FIRST_MASK) != 0) {
        return FALSE;
    }

    sTextbox.prior = blend;
    sTextbox.written = 0;
    sTextbox.owned = TRUE;
    return TRUE;
}

// The box at level / TEXTBOX_FADE_FRAMES: a plain crossfade over what is under it. FALSE when
// someone else wrote the registers since (the fade then ends at once)
static BOOL WriteBlend(int level)
{
    int ev1;

    if (!sTextbox.owned) {
        return FALSE;
    }

    if (sTextbox.written != 0 && ReadBlend() != sTextbox.written) {
        sTextbox.owned = FALSE;
        sBattleTextbox.snaps++;
        return FALSE;
    }

    ev1 = 16 * level / TEXTBOX_FADE_FRAMES;
    G2_SetBlendAlpha(TEXTBOX_BLEND_FIRST, TEXTBOX_BLEND_SECOND, ev1, 16 - ev1);
    sTextbox.written = ReadBlend();
    return TRUE;
}

static void ReleaseBlend(void)
{
    if (sTextbox.owned && ReadBlend() == sTextbox.written) {
        reg_G2_BLDCNT = (u16)sTextbox.prior;
        reg_G2_BLDALPHA = (u16)(sTextbox.prior >> 16);
    }

    sTextbox.owned = FALSE;
}

// A Platinum back sprite whose art runs into its frame's bottom row and that the stage draws
// as it is (no Gen 5 stream: the form species, Spinda): the box keeps hiding its cut edge.
// The streams stand on their feet.
static BOOL CutBackShows(void)
{
    PokemonSpriteManager *monSpriteMan = BattleSystem_GetPokemonSpriteManager(sTextbox.battleSys);
    int max = BattleSystem_MaxBattlers(sTextbox.battleSys);
    int i;

    for (i = 0; i < max && i < MAX_MON_SPRITES; i++) {
        PokemonSprite *sprite = &monSpriteMan->sprites[i];

        if ((BattleSystem_BattlerSlot(sTextbox.battleSys, i) & 1) == 0
            && sprite->active
            && !sprite->transforms.hide
            && !BattleStage_IsSpriteStreamed(i)
            && PokemonSprite_IsCut(sprite)) {
            return TRUE;
        }
    }

    return FALSE;
}

static void StartShowing(void)
{
    sBattleTextbox.shows++;

    if (!TakeBlend()) {
        sBattleTextbox.snaps++;
        sBattleTextbox.level = TEXTBOX_FADE_FRAMES;
    } else {
        WriteBlend(sBattleTextbox.level);
    }

    // The blend first, so the box doesn't flash in whole for a frame
    if (sTextbox.hidBg1) {
        GXLayers_EngineAToggleLayers(GX_PLANEMASK_BG1, TRUE);
        sTextbox.hidBg1 = FALSE;
    }

    if (sBattleTextbox.level >= TEXTBOX_FADE_FRAMES) {
        ReleaseBlend();
        sBattleTextbox.state = TEXTBOX_STATE_SHOWN;
    } else {
        sBattleTextbox.state = TEXTBOX_STATE_SHOWING;
    }
}

static void FinishHiding(void)
{
    // BG1 off before the blend goes back, so the box doesn't come back whole for a frame
    if (Bg1On()) {
        GXLayers_EngineAToggleLayers(GX_PLANEMASK_BG1, FALSE);
        sTextbox.hidBg1 = TRUE;
    }

    ReleaseBlend();
    sBattleTextbox.level = 0;
    sBattleTextbox.state = TEXTBOX_STATE_HIDDEN;
}

void BattleTextbox_Init(BattleSystem *battleSys)
{
    memset(&sTextbox, 0, sizeof(sTextbox));
    memset(&sBattleTextbox, 0, sizeof(sBattleTextbox));

    sTextbox.battleSys = battleSys;
    sTextbox.lastVBlank = OS_GetVBlankCount();
    sTextbox.readVBlanks = TEXTBOX_READ_HOLD;
    sBattleTextbox.state = TEXTBOX_STATE_SHOWN;
    sBattleTextbox.level = TEXTBOX_FADE_FRAMES;

    // BW2 starts with the box hidden (btlv_scu.c:646); it is empty until the first message
    if (BattleStage_IsVisible() && Bg1On()) {
        GXLayers_EngineAToggleLayers(GX_PLANEMASK_BG1, FALSE);
        sTextbox.hidBg1 = TRUE;
        sBattleTextbox.level = 0;
        sBattleTextbox.state = TEXTBOX_STATE_HIDDEN;
    }
}

void BattleTextbox_Update(void)
{
    u32 now = OS_GetVBlankCount();
    u32 vblanks = now - sTextbox.lastVBlank;
    int level;

    sTextbox.lastVBlank = now;

    if (sTextbox.battleSys == NULL || sBattleTextbox.suspended) {
        return;
    }

    if (vblanks > TEXTBOX_MAX_STEP) {
        vblanks = TEXTBOX_MAX_STEP;
    }

    if (sTextbox.printing && !Text_IsPrinterActive(sTextbox.printer)) {
        sTextbox.printing = FALSE;
        sTextbox.readVBlanks = 0;
    } else if (!sTextbox.printing && sTextbox.readVBlanks < 0xFFFF - TEXTBOX_MAX_STEP) {
        sTextbox.readVBlanks += vblanks;
    }

    switch (sBattleTextbox.state) {
    case TEXTBOX_STATE_SHOWN:
        if (!sBattleTextbox.hidePending) {
            break;
        }

        // Only over the stage, and not over a cut back sprite
        if (!BattleStage_IsVisible() || CutBackShows()) {
            sBattleTextbox.hidePending = FALSE;
            sBattleTextbox.keptUp++;
            break;
        }

        // Never while the text prints, nor until it has been up for the hold
        if (sTextbox.printing || (sTextbox.readVBlanks < TEXTBOX_READ_HOLD && !JOY_HELD(PAD_BUTTON_A | PAD_BUTTON_B))) {
            sTextbox.holdVBlanks += vblanks;
            break;
        }

        if (sTextbox.holdVBlanks > sBattleTextbox.readHoldVBlanks) {
            sBattleTextbox.readHoldVBlanks = sTextbox.holdVBlanks;
        }

        sBattleTextbox.hidePending = FALSE;
        sBattleTextbox.hides++;

        if (!TakeBlend()) {
            sBattleTextbox.snaps++;
            FinishHiding();
            break;
        }

        sBattleTextbox.state = TEXTBOX_STATE_HIDING;
        WriteBlend(sBattleTextbox.level);
        break;
    case TEXTBOX_STATE_HIDING:
        level = sBattleTextbox.level - (int)vblanks;
        sBattleTextbox.level = level < 0 ? 0 : level;

        if (sBattleTextbox.level == 0 || !WriteBlend(sBattleTextbox.level)) {
            FinishHiding();
        }
        break;
    case TEXTBOX_STATE_HIDDEN:
        sBattleTextbox.hidePending = FALSE;
        sBattleTextbox.hiddenVBlanks += vblanks;
        break;
    case TEXTBOX_STATE_SHOWING:
        level = sBattleTextbox.level + (int)vblanks;
        sBattleTextbox.level = level > TEXTBOX_FADE_FRAMES ? TEXTBOX_FADE_FRAMES : level;

        if (sBattleTextbox.level >= TEXTBOX_FADE_FRAMES || !WriteBlend(sBattleTextbox.level)) {
            sBattleTextbox.level = TEXTBOX_FADE_FRAMES;
            ReleaseBlend();
            sBattleTextbox.state = TEXTBOX_STATE_SHOWN;
        }
        break;
    }
}

void BattleTextbox_NotePrint(u8 printerID)
{
    if (sTextbox.battleSys == NULL || sBattleTextbox.suspended) {
        return;
    }

    // An instant print returns MAX_TEXT_PRINTERS (or 0xFF): it is already done
    sTextbox.printer = printerID;
    sTextbox.printing = printerID < MAX_TEXT_PRINTERS && Text_IsPrinterActive(printerID);
    sTextbox.readVBlanks = 0;
    sTextbox.holdVBlanks = 0;
    sBattleTextbox.hidePending = FALSE;

    if (sBattleTextbox.state == TEXTBOX_STATE_HIDDEN || sBattleTextbox.state == TEXTBOX_STATE_HIDING) {
        sBattleTextbox.printsWhileHidden++;
        StartShowing();
    }
}

void BattleTextbox_RequestHide(void)
{
    if (sTextbox.battleSys == NULL || sBattleTextbox.suspended) {
        return;
    }

    if (sBattleTextbox.state != TEXTBOX_STATE_HIDDEN && sBattleTextbox.state != TEXTBOX_STATE_HIDING) {
        if (!sBattleTextbox.hidePending) {
            sTextbox.holdVBlanks = 0;
        }

        sBattleTextbox.hidePending = TRUE;
    }
}

BOOL BattleTextbox_IsReadyForAnim(int waitFrames)
{
    if (sTextbox.battleSys == NULL || sBattleTextbox.suspended || sBattleTextbox.state == TEXTBOX_STATE_HIDDEN) {
        return TRUE;
    }

    if (sBattleTextbox.state == TEXTBOX_STATE_SHOWN && !sBattleTextbox.hidePending) {
        return TRUE;
    }

    // The text is still being read: the animation plays with the box up
    if (waitFrames >= TEXTBOX_READY_WAIT_MAX && sBattleTextbox.state == TEXTBOX_STATE_SHOWN) {
        sBattleTextbox.hidePending = FALSE;
        sBattleTextbox.keptUp++;
        return TRUE;
    }

    return FALSE;
}

BOOL BattleTextbox_IsClear(void)
{
    return sTextbox.battleSys != NULL
        && !sBattleTextbox.suspended
        && (sBattleTextbox.state == TEXTBOX_STATE_HIDDEN || sBattleTextbox.state == TEXTBOX_STATE_HIDING);
}

BOOL BattleTextbox_IsHidden(void)
{
    return sTextbox.battleSys != NULL && !sBattleTextbox.suspended && sBattleTextbox.state == TEXTBOX_STATE_HIDDEN;
}

void BattleTextbox_Suspend(void)
{
    if (sTextbox.battleSys == NULL) {
        return;
    }

    sTextbox.owned = FALSE;
    sTextbox.hidBg1 = FALSE;
    sBattleTextbox.hidePending = FALSE;
    sBattleTextbox.suspended = TRUE;
}

void BattleTextbox_Resume(void)
{
    if (sTextbox.battleSys == NULL) {
        return;
    }

    // Shown, so BG1 must be on if the box turned it off
    if (sTextbox.hidBg1 && !Bg1On()) {
        GXLayers_EngineAToggleLayers(GX_PLANEMASK_BG1, TRUE);
    }

    ReleaseBlend();
    sTextbox.hidBg1 = FALSE;
    sTextbox.lastVBlank = OS_GetVBlankCount();
    sTextbox.readVBlanks = TEXTBOX_READ_HOLD;
    sBattleTextbox.suspended = FALSE;
    sBattleTextbox.state = TEXTBOX_STATE_SHOWN;
    sBattleTextbox.level = TEXTBOX_FADE_FRAMES;
}
