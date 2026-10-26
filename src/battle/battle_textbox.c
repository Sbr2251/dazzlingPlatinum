#include "battle/battle_textbox.h"

#include <nitro.h>

#include "constants/graphics.h"
#include "constants/heap.h"
#include "constants/narc.h"

#include "battle/ov16_0223DF00.h"

#include "bg_window.h"
#include "palette.h"

// BW2's rest blend (btlv_scu.c:2290, BtlvScuWinFade_Init): BG1 first, everything else
// second, EVA 31 / EVB 7 over a black fill. Over a near-black fill the 31 coefficient
// saturates the fill away and the 7 lets the scene show through at about 7/16, while
// the white text saturates back to white.
#define TEXTBOX_BLEND_FIRST  GX_BLEND_PLANEMASK_BG1
#define TEXTBOX_BLEND_SECOND (GX_BLEND_PLANEMASK_BG0 | GX_BLEND_PLANEMASK_BG2 | GX_BLEND_PLANEMASK_BG3 | GX_BLEND_PLANEMASK_OBJ | GX_BLEND_PLANEMASK_BD)
#define TEXTBOX_BLEND_EVA    31
#define TEXTBOX_BLEND_EVB    7

// The idle blend the battle's effects end in (Battle_SetDefaultBlend is blending off;
// BattleAnimSystem_SetDefaultAlphaBlending and the Totem aura use no first target at
// 8/8 over every plane). Only these are taken over: an effect that uses no first
// target at other coefficients (the party gauge arrow's fade) is still running.
#define TEXTBOX_IDLE_SECOND_ALL 0x3F
#define TEXTBOX_IDLE_EVA        8
#define TEXTBOX_IDLE_EVB        8

#define TEXTBOX_BLDCNT_MODE_MASK  0xC0
#define TEXTBOX_BLDCNT_MODE_ALPHA 0x40
#define TEXTBOX_BLDCNT_FIRST_MASK 0x3F
#define TEXTBOX_BLDCNT_SECOND_SHIFT 8
#define TEXTBOX_BLDCNT_SECOND_MASK  0x3F

// The battle message window's text palette (BG palette slot 11, 16 colours). The text
// renderer maps a glyph's pixels through palette indices: per {COLOR n} code, fg at
// 2n+1 and shadow at 2n+2, bg at 15 (text.c). Slot 11's vanilla palette is the font
// palette (screen_indicators.NCLR): fg 1 is dark grey, shadow 2 light grey, bg 15
// white. Here fg is white, shadow near-black, bg near-black, and the other colour
// pairs are the same hues brightened for a dark background with dark shadows, so the
// gender symbols ({COLOR 1}/{COLOR 2}) and the other coloured words stay readable.
static const u16 sBattleTextboxTextPalette[16] = {
    GX_RGB(19, 24, 13), // 0: unused (palette index 0 is transparent on the BG)
    GX_RGB(31, 31, 31), // 1: fg, default: white
    GX_RGB(3, 3, 4), // 2: shadow, default: near-black
    GX_RGB(31, 10, 8), // 3: fg, colour 1: bright red
    GX_RGB(10, 2, 2), // 4: shadow, colour 1: dark red
    GX_RGB(8, 18, 31), // 5: fg, colour 2: bright blue
    GX_RGB(1, 5, 12), // 6: shadow, colour 2: dark blue
    GX_RGB(10, 26, 10), // 7: fg, colour 3: green
    GX_RGB(2, 8, 2), // 8: shadow, colour 3: dark green
    GX_RGB(30, 26, 26), // 9: fg, colour 4: pale
    GX_RGB(8, 6, 6), // 10: shadow, colour 4: dark
    GX_RGB(31, 31, 31), // 11: fg, colour 5: white
    GX_RGB(8, 4, 6), // 12: shadow, colour 5: dark pink
    GX_RGB(27, 27, 27), // 13: fg, colour 6: light grey
    GX_RGB(4, 8, 12), // 14: shadow, colour 6: dark blue-grey
    GX_RGB(1, 1, 2), // 15: bg: the box's near-black fill
};

// BG palette slot of the battle message window's text (window 0's palette)
#define TEXTBOX_TEXT_PALETTE_SLOT 11

static BattleSystem *sTextboxBattleSys;
static BOOL sTextboxSuspended;

static void WriteRestBlend(void)
{
    G2_SetBlendAlpha(TEXTBOX_BLEND_FIRST, TEXTBOX_BLEND_SECOND, TEXTBOX_BLEND_EVA, TEXTBOX_BLEND_EVB);
}

void BattleTextbox_Init(BattleSystem *battleSys)
{
    sTextboxBattleSys = battleSys;
    sTextboxSuspended = FALSE;
}

void BattleTextbox_Update(void)
{
    Window *window;
    u16 bldcnt;
    u16 mode;
    u16 first;

    if (sTextboxBattleSys == NULL || sTextboxSuspended) {
        return;
    }

    // The window is removed while the Pokedex, the naming screen or battle
    // teardown owns BG1: the box is not up, so its blend is not written.
    window = BattleSystem_Window(sTextboxBattleSys, 0);

    if (window == NULL || window->bgConfig == NULL) {
        return;
    }

    bldcnt = reg_G2_BLDCNT;
    mode = bldcnt & TEXTBOX_BLDCNT_MODE_MASK;

    if (mode == 0) {
        // Blending off: the idle state every effect ends in.
        WriteRestBlend();
        return;
    }

    if (mode != TEXTBOX_BLDCNT_MODE_ALPHA) {
        // A brightness flash (the Mega pulse, a screen flash): leave it alone.
        return;
    }

    first = bldcnt & TEXTBOX_BLDCNT_FIRST_MASK;

    if (first == 0) {
        // No first target: only the known idle blend is taken over. The idle
        // 8/8 over every plane is what the anim system and the Totem aura
        // leave behind, and it already keeps BG0 as a second target, so the
        // 3D layer's per-pixel alpha works under it.
        if (((bldcnt >> TEXTBOX_BLDCNT_SECOND_SHIFT) & TEXTBOX_BLDCNT_SECOND_MASK) == TEXTBOX_IDLE_SECOND_ALL
            && (reg_G2_BLDALPHA & 0xFF) == TEXTBOX_IDLE_EVA
            && ((reg_G2_BLDALPHA >> 8) & 0xFF) == TEXTBOX_IDLE_EVB) {
            WriteRestBlend();
        }

        return;
    }

    if (first == TEXTBOX_BLEND_FIRST) {
        // The box's own blend, but the stage fade trims its second targets
        // when it finishes (battle_stage.c UpdateFadeBlend), and other
        // writers can drift its coefficients: put the whole rest blend back.
        WriteRestBlend();
    }

    // Any other first target (a move animation, a stat change, an effect BG
    // swap) owns the registers: leave it alone until it ends.
}

void BattleTextbox_Suspend(void)
{
    sTextboxSuspended = TRUE;
}

void BattleTextbox_Resume(void)
{
    sTextboxSuspended = FALSE;
}

void BattleTextbox_LoadTextPalette(PaletteData *paletteSys)
{
    PaletteData_LoadBuffer(paletteSys, sBattleTextboxTextPalette, PLTTBUF_MAIN_BG, TEXTBOX_TEXT_PALETTE_SLOT * 16, sizeof(sBattleTextboxTextPalette));
}

void BattleTextbox_LoadClassicTextPalette(PaletteData *paletteSys)
{
    PaletteData_LoadBufferFromFileStart(paletteSys, NARC_INDEX_GRAPHIC__PL_FONT, 7, HEAP_ID_BATTLE, PLTTBUF_MAIN_BG, PALETTE_SIZE_BYTES, TEXTBOX_TEXT_PALETTE_SLOT * 16);
}
