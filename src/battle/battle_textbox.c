#include "battle/battle_textbox.h"

#include <nitro.h>

#include "constants/graphics.h"

#include "battle/ov16_0223DF00.h"

#include "bg_window.h"
#include "palette.h"
#include "render_window.h"

// BW2's rest blend (btlv_scu.c:2290, BtlvScuWinFade_Init) is BG1 first, everything
// else second, EVA 31 / EVB 7 over a black fill. With the hardware's divide-by-16
// blend that lets the scene through at 7/16 (about 44%); over the battle's dark
// grass and platform that still read as almost solid black, and Platinum's thick
// white frame boxed it in. This box uses EVA 22 / EVB 10 (about 60% scene) over a
// dark blue-grey fill, with no frame: the scene is visibly there while the box
// still reads as a panel. The white text saturates back to white at either
// setting, and its dark shadow stays dark.
#define TEXTBOX_BLEND_FIRST  GX_BLEND_PLANEMASK_BG1
#define TEXTBOX_BLEND_SECOND (GX_BLEND_PLANEMASK_BG0 | GX_BLEND_PLANEMASK_BG2 | GX_BLEND_PLANEMASK_BG3 | GX_BLEND_PLANEMASK_OBJ | GX_BLEND_PLANEMASK_BD)
#define TEXTBOX_BLEND_EVA    22
#define TEXTBOX_BLEND_EVB    10

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
    GX_RGB(2, 2, 5), // 15: bg: the box's dark blue-grey fill
};

// The battle message box's scroll cursor and wait dial (BG palette slot 10, the
// slot the frame palette used to own). The cursor arrow is palette index 1
// (white), its shadow index 2, the dial's shading index 3, and the cursor's
// background tiles are solid index 15. The frame is no longer drawn, so this
// slot is the cursor's alone.
static const u16 sBattleTextboxCursorPalette[16] = {
    GX_RGB(0, 0, 0), // 0: unused (palette index 0 is transparent on the BG)
    GX_RGB(31, 31, 31), // 1: cursor arrow / wait dial: white
    GX_RGB(3, 3, 4), // 2: cursor arrow shadow: near-black
    GX_RGB(20, 20, 22), // 3: wait dial shading: grey
    GX_RGB(2, 2, 5), // 4..14: dark fill
    GX_RGB(2, 2, 5),
    GX_RGB(2, 2, 5),
    GX_RGB(2, 2, 5),
    GX_RGB(2, 2, 5),
    GX_RGB(2, 2, 5),
    GX_RGB(2, 2, 5),
    GX_RGB(2, 2, 5),
    GX_RGB(2, 2, 5),
    GX_RGB(2, 2, 5),
    GX_RGB(2, 2, 5),
    GX_RGB(2, 2, 5), // 15: cursor background tiles: dark fill
};

// The classic text palette (BG palette slot 11): the font palette
// (screen_indicators.NCLR, the palette the vanilla battle loads into slot 11).
// Kept as an array, not a NARC load, so the stat window's palette can be
// re-applied every frame while it is up without a file read per frame.
static const u16 sBattleTextboxClassicTextPalette[16] = {
    GX_RGB(19, 24, 13), // 0: unused (palette index 0 is transparent on the BG)
    GX_RGB(10, 10, 11), // 1: fg, default: dark grey
    GX_RGB(20, 20, 21), // 2: shadow, default: light grey
    GX_RGB(29, 4, 2), // 3: fg, colour 1: red
    GX_RGB(31, 21, 23), // 4: shadow, colour 1: pink
    GX_RGB(0, 14, 31), // 5: fg, colour 2: blue
    GX_RGB(15, 23, 29), // 6: shadow, colour 2: light blue
    GX_RGB(0, 0, 0), // 7: fg, colour 3: black
    GX_RGB(0, 0, 0), // 8: shadow, colour 3: black
    GX_RGB(0, 0, 0), // 9: fg, colour 4: black
    GX_RGB(0, 0, 0), // 10: shadow, colour 4: black
    GX_RGB(31, 31, 31), // 11: fg, colour 5: white
    GX_RGB(31, 23, 24), // 12: shadow, colour 5: pink
    GX_RGB(27, 27, 27), // 13: fg, colour 6: light grey
    GX_RGB(18, 26, 31), // 14: shadow, colour 6: light blue
    GX_RGB(31, 31, 31), // 15: bg: white
};

// BG palette slot of the battle message window's text (window 0's palette)
#define TEXTBOX_TEXT_PALETTE_SLOT 11
// BG palette slot of the scroll cursor / wait dial (was the frame's slot)
#define TEXTBOX_CURSOR_PALETTE_SLOT 10

static BattleSystem *sTextboxBattleSys;
static BOOL sTextboxSuspended;
static BOOL sTextboxStatWindowUp;

static void WriteRestBlend(void)
{
    G2_SetBlendAlpha(TEXTBOX_BLEND_FIRST, TEXTBOX_BLEND_SECOND, TEXTBOX_BLEND_EVA, TEXTBOX_BLEND_EVB);
}

void BattleTextbox_Init(BattleSystem *battleSys)
{
    sTextboxBattleSys = battleSys;
    sTextboxSuspended = FALSE;
    sTextboxStatWindowUp = FALSE;
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

    // The level-up stat window shares the message window's text palette slot:
    // keep its classic palette in place while it is up.
    if (sTextboxStatWindowUp) {
        BattleTextbox_LoadClassicTextPalette(BattleSystem_PaletteSys(sTextboxBattleSys));
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

void BattleTextbox_LoadCursorPalette(PaletteData *paletteSys)
{
    PaletteData_LoadBuffer(paletteSys, sBattleTextboxCursorPalette, PLTTBUF_MAIN_BG, TEXTBOX_CURSOR_PALETTE_SLOT * 16, sizeof(sBattleTextboxCursorPalette));
}

void BattleTextbox_LoadTextPalette(PaletteData *paletteSys)
{
    PaletteData_LoadBuffer(paletteSys, sBattleTextboxTextPalette, PLTTBUF_MAIN_BG, TEXTBOX_TEXT_PALETTE_SLOT * 16, sizeof(sBattleTextboxTextPalette));
}

void BattleTextbox_LoadClassicTextPalette(PaletteData *paletteSys)
{
    PaletteData_LoadBuffer(paletteSys, sBattleTextboxClassicTextPalette, PLTTBUF_MAIN_BG, TEXTBOX_TEXT_PALETTE_SLOT * 16, sizeof(sBattleTextboxClassicTextPalette));
}

void BattleTextbox_StatWindowOpened(void)
{
    sTextboxStatWindowUp = TRUE;
}

void BattleTextbox_StatWindowClosed(void)
{
    sTextboxStatWindowUp = FALSE;
}

void BattleTextbox_DrawMessageWindow(Window *window)
{
    // The scroll cursor is drawn at the window's right edge, on the frame's
    // tilemap ring: it keeps whatever palette is already there, so give that
    // 2x2 rect the cursor palette first. The frame itself is not drawn.
    Bg_FillTilemapRect(window->bgConfig,
        Window_GetBgLayer(window),
        0,
        Window_GetXPos(window) + Window_GetWidth(window) + 1,
        Window_GetYPos(window) + 2,
        2,
        2,
        TEXTBOX_CURSOR_PALETTE_SLOT);
    // The cursor's background tiles (the frame's tiles 10/11 on BG1) become
    // solid dark-fill tiles, so the cursor sits on the box's own background
    // instead of on two light frame tiles.
    {
        u8 darkTiles[TILE_SIZE_4BPP * 2];
        u32 i;

        for (i = 0; i < sizeof(darkTiles); i++) {
            darkTiles[i] = 0xFF;
        }

        Bg_LoadTiles(window->bgConfig, Window_GetBgLayer(window), darkTiles, sizeof(darkTiles), 1 + 10);
    }
    Window_DrawMessageBoxWithoutFrame(window, 1);
}
