// Battle HUD (lane battlehud): battle menus as buttons on the TOP screen.
// See include/battle/battle_hud.h.
//
// Rendering: one Window on BG_LAYER_MAIN_1 above the message box. The
// panel and buttons are solid tiles (the same trick as the message box's
// scroll-cursor tile in battle_textbox.c: a generated solid 4bpp tile in
// a free BG1 char slot) through the battle text palette (slot 11: dark
// fill index 15, light-grey button index 13, red selection index 3, plus
// red/blue/green label colours). Labels are printed with
// Text_AddPrinterWithParamsAndColor over the button fills, with the type
// colour for move buttons. While the HUD is up, the player's healthboxes
// slide up (HealthBox_OffsetPositionXY) so the button strip never
// overlaps them; they slide back when the menu closes.
//
// Layout is anchored to the main-screen tile grid (32x24), not to pixel
// assumptions about the battlers: strip at tiles y=11..17, message box
// at y=19. In the wide layout the HUD stays inside the centred 4:3 2D
// rect (the main engine cannot draw outside 256x192; the wide margin is
// 3D-only in the composite) and the bottom panel is suppressed.

#include "battle/battle_hud.h"

#include <nitro.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef SDK_PORT
#include <simulator/sim_headless.h>
#endif

#include "constants/charcode.h"
#include "constants/graphics.h"
#include "generated/pokemon_types.h"

#include "battle/battle_context.h"
#include "battle/battle_system.h"
#include "battle/healthbox.h"
#include "port/sim_battle3d.h"
#include "port/sim_config_prj.h"
#include "port/sim_wide.h"

#include "bg_window.h"
#include "message.h"
#include "message_util.h"
#include "move_table.h"
#include "palette.h"
#include "pokemon.h"
#include "render_window.h"
#include "string_gf.h"
#include "string_template.h"
#include "system.h"
#include "text.h"

#include "res/text/bank/battle_strings.h"

// Menu config indices (sBattleMenuConfigs in battle_subscreen.c).
#define HUD_MENU_IDLE 0
#define HUD_MENU_MOVE 11
#define HUD_MENU_TARGET 12
// 13..17 are the yes/no family; 1..10 the action-menu family.

#define HUD_TILE_X 0
#define HUD_TILE_Y 11
#define HUD_TILE_W 32
#define HUD_TILE_H 7
#define HUD_SOLID_TILE 860 // free BG1 char slot (message win 31-138, cursor 139)
#define HUD_PALETTE 11 // battle text palette slot
#define HUD_HEALTHBOX_LIFT 84

// Native 16:9 wide pixel-art Battle HUD (342x192, 43x24 tiles).
// All menus dock inside the bottom 6-tile bar (y=18..23, 48px tall) using
// BG1 char base 500 (max 43x6 = 258 tiles -> 500..757, well below 1024) and
// dedicated Platinum-harmonized palette slot 15.
#define WIDE_HUD_WIDTH_PX 342
#define WIDE_HUD_BAR_Y 18
#define WIDE_HUD_BAR_H 6
#define WIDE_HUD_BAR_Y_PX (WIDE_HUD_BAR_Y * 8)
#define WIDE_HUD_BAR_H_PX (WIDE_HUD_BAR_H * 8)
#define WIDE_HUD_CHAR_BASE 500
#define WIDE_HUD_PALETTE 15

#define WIDE_HUD_ACTION_X 20
#define WIDE_HUD_ACTION_W 23
#define WIDE_HUD_FULL_X 0
#define WIDE_HUD_FULL_W 43
#define WIDE_HUD_YESNO_X 32
#define WIDE_HUD_YESNO_W 11

// Option A BDSP corner-docked authentic Platinum pixel-art HUD coordinates (342x192).
// All windows use BG1 char base 500 (max 21x14 = 294 tiles -> 500..793 < 1024)
// and palette slot 15, leaving 100% of the 3D clearing unobstructed.
#define BDSP_HUD_ACTION_X 31
#define BDSP_HUD_ACTION_Y 11
#define BDSP_HUD_ACTION_W 12
#define BDSP_HUD_ACTION_H 13

#define BDSP_HUD_MOVE_X 22
#define BDSP_HUD_MOVE_Y 10
#define BDSP_HUD_MOVE_W 21
#define BDSP_HUD_MOVE_H 14

#define BDSP_HUD_TARGET_X 18
#define BDSP_HUD_TARGET_Y 17
#define BDSP_HUD_TARGET_W 25
#define BDSP_HUD_TARGET_H 7

#define BDSP_HUD_YESNO_X 32
#define BDSP_HUD_YESNO_Y 12
#define BDSP_HUD_YESNO_W 11
#define BDSP_HUD_YESNO_H 6

// Palette slot 15 indices (4bpp).
#define WHUD_COL_TRANSPARENT 0
#define WHUD_COL_BORDER 1 // dark olive-charcoal border & normal text fg
#define WHUD_COL_TEXT_SHADOW 2 // Platinum light warm-grey text shadow
#define WHUD_COL_MINT_TRIM 3 // mint-sage outer frame trim (matches PL_WINFRAME)
#define WHUD_COL_PANEL_BG 4 // deep olive-sage recessed panel backing
#define WHUD_COL_BTN_FACE 5 // warm DS off-white beveled button face
#define WHUD_COL_BTN_SHADOW 6 // soft warm-grey button bottom/right bevel
#define WHUD_COL_WHITE 7 // pure white bevel highlight & selected text fg
#define WHUD_COL_CRIMSON 8 // FIGHT crimson (Fire/Fighting)
#define WHUD_COL_DARK_SHADOW 9 // deep shadow under white selected text
#define WHUD_COL_CERULEAN 10 // BAG cerulean (Water/Flying/Ice)
#define WHUD_COL_EMERALD 11 // POKeMON emerald (Grass/Bug)
#define WHUD_COL_SLATE 12 // RUN / CANCEL slate (Normal/Steel/Dark)
#define WHUD_COL_MEGA_GOLD 13 // MEGA gold (Electric / active highlight trim)
#define WHUD_COL_VIOLET 14 // Psychic/Poison/Ghost/Dragon/Fairy accent
#define WHUD_COL_AMBER 15 // Ground/Rock / warm selected fill accent

static const u16 sWideHudPalette[16] = {
    GX_RGB(0, 0, 0),    //  0: transparent
    GX_RGB(5, 6, 5),    //  1: dark olive-charcoal border & ink
    GX_RGB(20, 21, 20), //  2: light warm-grey text shadow
    GX_RGB(19, 24, 17), //  3: mint-sage trim matching PL_WINFRAME
    GX_RGB(11, 14, 11), //  4: dark olive-sage panel backing
    GX_RGB(30, 30, 29), //  5: warm DS off-white button face
    GX_RGB(23, 23, 22), //  6: button bottom/right bevel shadow
    GX_RGB(31, 31, 31), //  7: pure white highlight & selected text
    GX_RGB(25, 6, 6),   //  8: FIGHT crimson
    GX_RGB(8, 4, 5),    //  9: deep shadow under white selected text
    GX_RGB(5, 14, 25),  // 10: BAG cerulean
    GX_RGB(5, 18, 9),   // 11: POKeMON emerald
    GX_RGB(10, 12, 15), // 12: RUN / CANCEL slate
    GX_RGB(29, 22, 5),  // 13: MEGA gold
    GX_RGB(16, 8, 22),  // 14: royal violet
    GX_RGB(22, 12, 3),  // 15: warm amber-ochre
};

typedef struct BattleHudState {
    Window window;
    BOOL windowAdded;
    BOOL tilesLoaded;
    BOOL healthboxesLifted;
    BOOL wideModeWindow;
    BOOL bdspModeWindow;
    u8 winX;
    u8 winY;
    u8 winW;
    u8 winH;
    int lastMenu;
    int lastCursorX;
    int lastCursorY;
    int lastMega;
    int lastMoveSlot;
    u16 lastMovePP[4];
} BattleHudState;

static BattleHudState sHud;

BOOL BattleHud_IsEnabled(void)
{
    static int sHeadless = -1;
    const char *env = getenv("SIM_FX_BATTLEHUD");

    if (env != NULL && env[0] != '\0') {
        return env[0] != '0' ? TRUE : FALSE;
    }
    if (sHeadless < 0) {
        const char *headless = getenv("SIM_HEADLESS");
        sHeadless = (headless != NULL && headless[0] != '\0' && headless[0] != '0') ? 1 : 0;
    }
    if (sHeadless) {
        return FALSE;
    }
    return SIM_Config_prj_GetConfig()->battleHud;
}

BOOL BattleHud_IsWidePixelMode(void)
{
#ifdef SDK_PORT
    if (!SIM_Wide_IsWideLayout() || !BattleHud_IsEnabled()) {
        return FALSE;
    }
    if (SIM_Battle3D_IsEnabled()) {
        return TRUE;
    }
    if (!SIM_Headless_Enabled()) {
        return TRUE;
    }
    {
        const char *wideHud = getenv("SIM_FX_WIDE_BATTLEHUD");
        const char *interactive = getenv("SIM_HEADLESS_INTERACTIVE_FX");
        if ((wideHud != NULL && wideHud[0] == '1') || (interactive != NULL && interactive[0] == '1')) {
            return TRUE;
        }
    }
    return FALSE;
#else
    return FALSE;
#endif
}

void BattleHud_DrawWideMessageFrame(BattleSystem *battleSys)
{
    BgConfig *bgConfig;
    Window *msgWin;

    if (battleSys == NULL) {
        return;
    }
    bgConfig = BattleSystem_GetBgConfig(battleSys);
    if (bgConfig == NULL) {
        return;
    }

    // Authentic Platinum PL_WINFRAME (tiles 1..18, slot 10) spanning 43x6 tiles
    // across x=0..42, y=18..23 around windows[0] (x=2..28, y=19..22).
    // Top border (y = 18):
    Bg_FillTilemapRect(bgConfig, BG_LAYER_MAIN_1, 1, 0, 18, 1, 1, 10);
    Bg_FillTilemapRect(bgConfig, BG_LAYER_MAIN_1, 2, 1, 18, 1, 1, 10);
    Bg_FillTilemapRect(bgConfig, BG_LAYER_MAIN_1, 3, 2, 18, 38, 1, 10);
    Bg_FillTilemapRect(bgConfig, BG_LAYER_MAIN_1, 4, 40, 18, 1, 1, 10);
    Bg_FillTilemapRect(bgConfig, BG_LAYER_MAIN_1, 5, 41, 18, 1, 1, 10);
    Bg_FillTilemapRect(bgConfig, BG_LAYER_MAIN_1, 6, 42, 18, 1, 1, 10);

    // Middle rows (y = 19..22): left border 0..1, windows[0] 2..28,
    // solid interior tile 9 at 29..39, right border 40..42.
    Bg_FillTilemapRect(bgConfig, BG_LAYER_MAIN_1, 7, 0, 19, 1, 4, 10);
    Bg_FillTilemapRect(bgConfig, BG_LAYER_MAIN_1, 8, 1, 19, 1, 4, 10);
    Bg_FillTilemapRect(bgConfig, BG_LAYER_MAIN_1, 9, 29, 19, 11, 4, 10);
    Bg_FillTilemapRect(bgConfig, BG_LAYER_MAIN_1, 10, 40, 19, 1, 4, 10);
    Bg_FillTilemapRect(bgConfig, BG_LAYER_MAIN_1, 11, 41, 19, 1, 4, 10);
    Bg_FillTilemapRect(bgConfig, BG_LAYER_MAIN_1, 12, 42, 19, 1, 4, 10);

    // Bottom border (y = 23):
    Bg_FillTilemapRect(bgConfig, BG_LAYER_MAIN_1, 13, 0, 23, 1, 1, 10);
    Bg_FillTilemapRect(bgConfig, BG_LAYER_MAIN_1, 14, 1, 23, 1, 1, 10);
    Bg_FillTilemapRect(bgConfig, BG_LAYER_MAIN_1, 15, 2, 23, 38, 1, 10);
    Bg_FillTilemapRect(bgConfig, BG_LAYER_MAIN_1, 16, 40, 23, 1, 1, 10);
    Bg_FillTilemapRect(bgConfig, BG_LAYER_MAIN_1, 17, 41, 23, 1, 1, 10);
    Bg_FillTilemapRect(bgConfig, BG_LAYER_MAIN_1, 18, 42, 23, 1, 1, 10);

    msgWin = BattleSystem_GetWindow(battleSys, 0);
    if (msgWin != NULL && msgWin->bgConfig != NULL) {
        Window_PutToTilemap(msgWin);
    }

    Bg_ScheduleTilemapTransfer(bgConfig, BG_LAYER_MAIN_1);
}

// Button/panel fills are window-bitmap colours (palette slot 11 indices:
// 15 panel, 13 button, 3 selected), drawn with Window_FillRectWithColor
// before the labels are printed over them.
static void HudFillRect(BattleSubscreen *btlSubscreen, int color, int x, int y, int w, int h)
{
    (void)btlSubscreen;
    Window_FillRectWithColor(&sHud.window, (u8)color, (u16)(x * 8), (u16)(y * 8), (u16)(w * 8), (u16)(h * 8));
}

// Button in tile coords (window-local). selected swaps fill + label colour.
static void HudButton(BattleSubscreen *btlSubscreen, String *label, TextColor normalColor,
    int tx, int ty, int tw, BOOL selected, String *rightLabel)
{
    HudFillRect(btlSubscreen, selected ? 3 : 13, tx, ty, tw, 2);
    {
        TextColor color = selected ? TEXT_COLOR(1, 2, 3) : normalColor;
        Text_AddPrinterWithParamsAndColor(&sHud.window, FONT_SYSTEM, label,
            tx * 8 + 6, ty * 8 + 4, 0, color, NULL);
    }
    if (rightLabel != NULL) {
        TextColor color = selected ? TEXT_COLOR(1, 2, 3) : TEXT_COLOR(9, 1, 13);
        int width = Font_CalcStringWidth(FONT_SYSTEM, rightLabel, 0);
        Text_AddPrinterWithParamsAndColor(&sHud.window, FONT_SYSTEM, rightLabel,
            (tx + tw) * 8 - 6 - width, ty * 8 + 4, 0, color, NULL);
    }
}

static void HudLiftHealthboxes(BattleSubscreen *btlSubscreen, BOOL lift)
{
    BattleSystem *battleSys = btlSubscreen->battleSys;
    int i, maxBattlers;

    if (BattleHud_IsWidePixelMode()) {
        return; // wide pixel mode keeps player healthboxes docked lower-right
    }
    if (!lift && !sHud.healthboxesLifted) {
        return;
    }
    maxBattlers = BattleSystem_GetMaxBattlers(battleSys);
    for (i = 0; i < maxBattlers; i++) {
        HealthBox *healthbox;
        if (i % 2 != 0) {
            continue; // enemy side (left) stays put; player side is even
        }
        healthbox = BattleSystem_GetHealthBox(battleSys, i);
        if (healthbox != NULL) {
            if (lift) {
                // The active battler's bob task re-seats its box at the
                // template position every frame; stop it while lifted
                // (the game re-activates it at the next command phase).
                Healthbox_StopBobAnimation(healthbox);
            }
            HealthBox_OffsetPositionXY(healthbox, 0, lift ? -HUD_HEALTHBOX_LIFT : 0);
        }
    }
    sHud.healthboxesLifted = lift;
}

static void HudHideInternal(BattleSubscreen *btlSubscreen)
{
    if (sHud.windowAdded && btlSubscreen != NULL) {
        BgConfig *bgConfig = BattleSystem_GetBgConfig(btlSubscreen->battleSys);
        if (sHud.bdspModeWindow) {
            Window_FillRectWithColor(&sHud.window, 0, 0, 0, (u16)(sHud.winW * 8), (u16)(sHud.winH * 8));
            Window_ScheduleCopyToVRAM(&sHud.window);
            Bg_FillTilemapRect(bgConfig, BG_LAYER_MAIN_1,
                0, sHud.winX, sHud.winY, sHud.winW, sHud.winH, WIDE_HUD_PALETTE);
            if (sHud.lastMenu >= 13 && sHud.lastMenu <= 17) {
                Bg_FillTilemapRect(bgConfig, BG_LAYER_MAIN_1,
                    0, 0, 18, WIDE_HUD_FULL_W, 6, WIDE_HUD_PALETTE);
            }
            Bg_ScheduleTilemapTransfer(bgConfig, BG_LAYER_MAIN_1);
            Window_Remove(&sHud.window);
            sHud.windowAdded = FALSE;
            sHud.wideModeWindow = FALSE;
            sHud.bdspModeWindow = FALSE;
        } else if (sHud.wideModeWindow) {
            Window_FillRectWithColor(&sHud.window, 0, 0, 0, (u16)(sHud.winW * 8), (u16)(sHud.winH * 8));
            Window_Remove(&sHud.window);
            sHud.windowAdded = FALSE;
            sHud.wideModeWindow = FALSE;
            BattleHud_DrawWideMessageFrame(btlSubscreen->battleSys);
        } else {
            // Clear the strip so no panel tiles linger over the scene: wipe
            // the window bitmap to transparent and upload both the char
            // tiles and the tilemap (a tilemap-buffer write alone never
            // reaches VRAM).
            Window_FillRectWithColor(&sHud.window, 0, 0, 0, HUD_TILE_W * 8, HUD_TILE_H * 8);
            Window_ScheduleCopyToVRAM(&sHud.window);
            Bg_FillTilemapRect(bgConfig, BG_LAYER_MAIN_1,
                0, HUD_TILE_X, HUD_TILE_Y, HUD_TILE_W, HUD_TILE_H, HUD_PALETTE);
            Bg_ScheduleTilemapTransfer(bgConfig, BG_LAYER_MAIN_1);
            Window_Remove(&sHud.window);
            sHud.windowAdded = FALSE;
        }
    }
    if (btlSubscreen != NULL) {
        HudLiftHealthboxes(btlSubscreen, FALSE);
    }
    sHud.lastMenu = -2;
}

void BattleHud_Hide(BattleSubscreen *btlSubscreen)
{
    HudHideInternal(btlSubscreen);
    SIM_Wide_SetMainTouchEnabled(0);
    if (BattleHud_IsEnabled()) {
        SIM_Wide_SetBattleTouchNeeded(1);
    }
}

// Confirm in BattleSystem_MenuInput: the panel goes away and the
// healthboxes return, but the wide touch state is left alone (the next
// menu, if any, keeps the bottom panel suppressed; the final hide via
// menu config 0 / subscreen free restores it).
void BattleHud_HideOnConfirm(BattleSubscreen *btlSubscreen)
{
    HudHideInternal(btlSubscreen);
    SIM_Wide_SetMainTouchEnabled(0);
}

static void HudEnsureWindow(BattleSubscreen *btlSubscreen)
{
    if (sHud.windowAdded) {
        return;
    }
    Window_Add(BattleSystem_GetBgConfig(btlSubscreen->battleSys), &sHud.window,
        BG_LAYER_MAIN_1, HUD_TILE_X, HUD_TILE_Y, HUD_TILE_W, HUD_TILE_H, HUD_PALETTE, 600);
    sHud.windowAdded = TRUE;
    sHud.lastMenu = -2;
}

// Move type -> label colour index pair in the text palette (fg index).
static TextColor HudMoveColor(u16 moveID, BOOL selected)
{
    int type;
    int fg;

    if (selected) {
        return TEXT_COLOR(1, 2, 3);
    }
    type = MoveTable_LoadParam(moveID, MOVEATTRIBUTE_TYPE);
    switch (type) {
    case 9: // FIRE
    case 11: // WATER -> blue below, fire red
        fg = 3;
        break;
    default:
        fg = 9;
        break;
    }
    if (type == 11 || type == 2) { // WATER, FLYING-ish blue
        fg = 5;
    } else if (type == 12 || type == 4) { // GRASS, POISON green
        fg = 7;
    }
    return TEXT_COLOR(fg, 1, 13);
}

static void HudDrawAction(BattleSubscreen *btlSubscreen)
{
    MessageLoader *msgLoader = BattleSystem_GetMessageLoader(btlSubscreen->battleSys);
    u32 battleType = BattleSystem_GetBattleType(btlSubscreen->battleSys);
    String *fight, *bag, *party, *run;
    int cx = btlSubscreen->cursor.x, cy = btlSubscreen->cursor.y;

    if (battleType & BATTLE_TYPE_SAFARI) {
        fight = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_Ball);
        bag = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_Bait);
        party = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_Mud);
    } else if (battleType & BATTLE_TYPE_PAL_PARK) {
        fight = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_BallPalPark);
        bag = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_Bait);
        party = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_Mud);
    } else {
        fight = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_Fight);
        bag = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_Bag);
        party = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_Pokemon);
    }
    run = MessageLoader_GetNewString(msgLoader,
        btlSubscreen->activeMenuData.actionData.isWaitingForPartner
            ? BattleStrings_Text_Cancel : BattleStrings_Text_Run);

    HudButton(btlSubscreen, fight, TEXT_COLOR(3, 1, 13), 0, 0, 15, cx == 0 && cy == 0, NULL);
    HudButton(btlSubscreen, party, TEXT_COLOR(7, 1, 13), 16, 0, 15, cx == 1 && cy == 0, NULL);
    HudButton(btlSubscreen, bag, TEXT_COLOR(5, 1, 13), 0, 3, 15, cx == 0 && cy == 1, NULL);
    HudButton(btlSubscreen, run, TEXT_COLOR(9, 1, 13), 16, 3, 15, cx == 1 && cy == 1, NULL);

    String_Free(fight);
    String_Free(bag);
    String_Free(party);
    String_Free(run);
}

static void HudDrawMoves(BattleSubscreen *btlSubscreen)
{
    MoveSelectData *moveData = &btlSubscreen->activeMenuData.moveData;
    MessageLoader *msgLoader = BattleSystem_GetMessageLoader(btlSubscreen->battleSys);
    StringTemplate *template = BattleSystem_GetStringTemplate(btlSubscreen->battleSys);
    int cx = btlSubscreen->cursor.x, cy = btlSubscreen->cursor.y;
    int i;

    for (i = 0; i < 4; i++) {
        int tx = (i & 1) ? 16 : 0;
        int ty = (i & 2) ? 2 : 0;
        BOOL selected = (cx == (i & 1) && cy == (i >> 1));
        if (moveData->moveIDs[i] == 0) {
            continue;
        }
        {
            String *name = MessageUtil_MoveName(moveData->moveIDs[i], HEAP_ID_BATTLE);
            String *fmt = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_CurPPOutOfMaxPP);
            String *pp = String_Init(16, HEAP_ID_BATTLE);
            StringTemplate_SetNumber(template, 0, moveData->currPP[i], 2, 1, 0);
            StringTemplate_SetNumber(template, 1, moveData->maxPP[i], 2, 1, 0);
            StringTemplate_Format(template, pp, fmt);
            HudButton(btlSubscreen, name, HudMoveColor(moveData->moveIDs[i], selected),
                tx, ty, 15, selected, pp);
            String_Free(name);
            String_Free(fmt);
            String_Free(pp);
        }
        sHud.lastMovePP[i] = moveData->currPP[i];
    }

    if (moveData->megaEvolutionAvailable) {
        BattleContext *ctx = BattleSystem_GetBattleContext(btlSubscreen->battleSys);
        int battler = BattleSystem_GetBattlerOfType(btlSubscreen->battleSys, btlSubscreen->battlerType);
        int on = ctx->megaEvolutionTriggered[battler] ? 1 : 0;
        String *mega = MessageLoader_GetNewString(msgLoader, 1272); // "MEGA"
        // Mega strip: full-width button under the moves; red fill when armed.
        HudFillRect(btlSubscreen, on ? 3 : 13, 0, 5, 32, 2);
        Text_AddPrinterWithParamsAndColor(&sHud.window, FONT_SYSTEM, mega, 14, 5 * 8 + 4, 0,
            on ? TEXT_COLOR(1, 2, 3) : TEXT_COLOR(3, 1, 13), NULL);
        {
            String *label = MessageLoader_GetNewString(msgLoader,
                on ? BattleStrings_Text_Yes : BattleStrings_Text_No);
            Text_AddPrinterWithParamsAndColor(&sHud.window, FONT_SYSTEM, label, 64, 5 * 8 + 4, 0,
                on ? TEXT_COLOR(1, 2, 3) : TEXT_COLOR(2, 1, 13), NULL);
            String_Free(label);
        }
        String_Free(mega);
        sHud.lastMega = on;
    }
}

static void HudDrawTarget(BattleSubscreen *btlSubscreen)
{
    TargetSelectData *data = &btlSubscreen->activeMenuData.targetSelectData;
    MessageLoader *msgLoader = BattleSystem_GetMessageLoader(btlSubscreen->battleSys);
    StringTemplate *template = BattleSystem_GetStringTemplate(btlSubscreen->battleSys);
    String *message = String_Init(32, HEAP_ID_BATTLE);
    u8 battlersByType[6];
    int i;

    BattleSystem_SetBattlersByType(btlSubscreen->battleSys, battlersByType);

    for (i = 0; i < 4; i++) {
        int battlerIndex = battlersByType[2 + i];
        int tx = (i & 1) ? 16 : 0;
        int ty = (i & 2) ? 3 : 0;
        BOOL selected = (btlSubscreen->cursor.x == (i & 1) && btlSubscreen->cursor.y == (i >> 1));
        if (!data->targetMonData[battlerIndex].isPresent) {
            continue;
        }
        {
            String *formatMsg = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_HealthBoxPokemonName);
            Pokemon *partyMon = BattleSystem_GetPartyPokemon(btlSubscreen->battleSys, battlerIndex, data->targetMonData[battlerIndex].partySlot);
            StringTemplate_SetNickname(template, 0, Pokemon_GetBoxPokemon(partyMon));
            StringTemplate_Format(template, message, formatMsg);
            HudButton(btlSubscreen, message, TEXT_COLOR(9, 1, 13), tx, ty, 15, selected, NULL);
            String_Free(formatMsg);
        }
    }
    String_Free(message);
}

static void HudDrawYesNo(BattleSubscreen *btlSubscreen)
{
    MessageLoader *msgLoader = BattleSystem_GetMessageLoader(btlSubscreen->battleSys);
    String *yes = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_Yes);
    String *no = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_No);
    int cy = btlSubscreen->cursor.y;

    HudButton(btlSubscreen, yes, TEXT_COLOR(7, 1, 13), 0, 0, 15, cy == 0, NULL);
    HudButton(btlSubscreen, no, TEXT_COLOR(3, 1, 13), 0, 3, 15, cy == 1, NULL);

    String_Free(yes);
    String_Free(no);
}

// --- Native 16:9 Wide Pixel-Art Battle HUD (342x192, bottom bar y=18..23) ---

static String *WideHudAsciiString(const char *ascii)
{
    charcode_t buf[32];
    int i = 0;

    while (ascii[i] != '\0' && i < 31) {
        char c = ascii[i];
        if (c >= 'A' && c <= 'Z') {
            buf[i] = (charcode_t)(CHAR_A + (c - 'A'));
        } else if (c >= 'a' && c <= 'z') {
            buf[i] = (charcode_t)(CHAR_a + (c - 'a'));
        } else if (c >= '0' && c <= '9') {
            buf[i] = (charcode_t)(CHAR_0 + (c - '0'));
        } else if (c == '-') {
            buf[i] = CHAR_MINUS;
        } else if (c == '/') {
            buf[i] = CHAR_SLASH;
        } else if (c == ':') {
            buf[i] = CHAR_COLON;
        } else if (c == '+') {
            buf[i] = CHAR_PLUS;
        } else if (c == '*') {
            buf[i] = CHAR_STAR;
        } else {
            buf[i] = CHAR_SPACE;
        }
        i++;
    }
    buf[i] = CHAR_EOS;
    {
        String *str = String_Init(32, HEAP_ID_BATTLE);
        String_CopyChars(str, buf);
        return str;
    }
}

static u8 WideHudMoveTypeStripeColor(int type)
{
    switch (type) {
    case TYPE_FIRE:
    case TYPE_FIGHTING:
        return WHUD_COL_CRIMSON;
    case TYPE_WATER:
    case TYPE_FLYING:
    case TYPE_ICE:
        return WHUD_COL_CERULEAN;
    case TYPE_GRASS:
    case TYPE_BUG:
        return WHUD_COL_EMERALD;
    case TYPE_ELECTRIC:
        return WHUD_COL_MEGA_GOLD;
    case TYPE_GROUND:
    case TYPE_ROCK:
        return WHUD_COL_AMBER;
    case TYPE_POISON:
    case TYPE_GHOST:
    case TYPE_PSYCHIC:
    case TYPE_DRAGON:
    case TYPE_FAIRY:
        return WHUD_COL_VIOLET;
    case TYPE_NORMAL:
    case TYPE_STEEL:
    case TYPE_MYSTERY:
    case TYPE_DARK:
    default:
        return WHUD_COL_SLATE;
    }
}

static u8 WideHudMoveTypeFillColor(int type)
{
    // Electric uses warm amber for the selected fill so pure white text pops
    // while keeping gold for the stripe and highlight trim.
    if (type == TYPE_ELECTRIC) {
        return WHUD_COL_AMBER;
    }
    return WideHudMoveTypeStripeColor(type);
}

static void WideHudFillPx(int x, int y, int w, int h, u8 color)
{
    if (w <= 0 || h <= 0) {
        return;
    }
    Window_FillRectWithColor(&sHud.window, color, (u16)x, (u16)y, (u16)w, (u16)h);
}

static void WideHudDrawPanelFrameEx(int visW, int visH)
{
    // Clear full tile-aligned window width (including 2px right of 342px edge)
    // to border color, then draw authentic Platinum olive-charcoal + mint-sage
    // frame matching PL_WINFRAME's 4px bezel around the button interior.
    WideHudFillPx(0, 0, sHud.winW * 8, visH, WHUD_COL_BORDER);
    WideHudFillPx(1, 1, visW - 2, visH - 2, WHUD_COL_MINT_TRIM);
    WideHudFillPx(3, 3, visW - 6, visH - 6, WHUD_COL_BORDER);
    WideHudFillPx(4, 4, visW - 8, visH - 8, WHUD_COL_PANEL_BG);
}

static void WideHudDrawPanelFrame(int visW)
{
    WideHudDrawPanelFrameEx(visW, WIDE_HUD_BAR_H_PX);
}

static void WideHudDrawVerticalDivider(int x)
{
    // Crisp 4px vertical mint-sage divider between left/right zones.
    WideHudFillPx(x, 3, 4, WIDE_HUD_BAR_H_PX - 6, WHUD_COL_BORDER);
    WideHudFillPx(x + 1, 3, 2, WIDE_HUD_BAR_H_PX - 6, WHUD_COL_MINT_TRIM);
}

static void WideHudDrawRecessedPlaque(int x, int y, int w, int h, u8 stripeCol)
{
    WideHudFillPx(x, y, w, h, WHUD_COL_BORDER);
    WideHudFillPx(x + 1, y + 1, w - 2, h - 2, WHUD_COL_PANEL_BG);
    // Subtle bottom/right mint inset rim.
    WideHudFillPx(x + 1, y + h - 2, w - 2, 1, WHUD_COL_MINT_TRIM);
    WideHudFillPx(x + w - 2, y + 1, 1, h - 2, WHUD_COL_MINT_TRIM);
    if (stripeCol != 0) {
        WideHudFillPx(x + 1, y + 1, 2, h - 2, stripeCol);
    }
}

static void WideHudDrawButton(int x, int y, int w, int h, u8 stripeCol, u8 selectedFillCol,
    BOOL selected, BOOL drawStripe, const String *label, BOOL centerLabel, const String *rightLabel)
{
    int contentLeft;
    int textY = y + (h - 12) / 2;

    if (selected) {
        // Selected DS pixel-art button: dark outer border, crisp white inner
        // highlight rim, rich saturated fill, gold cursor bar, pure white text.
        WideHudFillPx(x, y, w, h, WHUD_COL_BORDER);
        WideHudFillPx(x + 1, y + 1, w - 2, h - 2, WHUD_COL_WHITE);
        WideHudFillPx(x + 2, y + 2, w - 4, h - 4, selectedFillCol);
        if (drawStripe) {
            u8 barCol = (selectedFillCol == WHUD_COL_AMBER || selectedFillCol == WHUD_COL_MEGA_GOLD)
                ? WHUD_COL_WHITE : WHUD_COL_MEGA_GOLD;
            WideHudFillPx(x + 2, y + 2, 3, h - 4, barCol);
            contentLeft = 7;
        } else {
            contentLeft = 4;
        }
    } else {
        // Normal DS beveled button: dark border, off-white face, top/left white
        // highlight, bottom/right soft warm-grey shadow, optional 3px accent stripe.
        WideHudFillPx(x, y, w, h, WHUD_COL_BORDER);
        WideHudFillPx(x + 1, y + 1, w - 2, h - 2, WHUD_COL_BTN_FACE);
        WideHudFillPx(x + 1, y + 1, w - 2, 1, WHUD_COL_WHITE);
        WideHudFillPx(x + 1, y + 1, 1, h - 2, WHUD_COL_WHITE);
        WideHudFillPx(x + 1, y + h - 2, w - 2, 1, WHUD_COL_BTN_SHADOW);
        WideHudFillPx(x + w - 2, y + 1, 1, h - 2, WHUD_COL_BTN_SHADOW);
        if (drawStripe) {
            WideHudFillPx(x + 1, y + 1, 3, h - 2, stripeCol);
            contentLeft = 7;
        } else {
            contentLeft = 4;
        }
    }

    if (label != NULL) {
        TextColor col = selected
            ? TEXT_COLOR(WHUD_COL_WHITE, WHUD_COL_DARK_SHADOW, 0)
            : TEXT_COLOR(WHUD_COL_BORDER, WHUD_COL_TEXT_SHADOW, 0);
        int labelX = x + contentLeft;
        if (centerLabel && rightLabel == NULL) {
            int textW = Font_CalcStringWidth(FONT_SYSTEM, label, 0);
            int availW = w - contentLeft - 3;
            int centered = x + contentLeft + (availW - textW) / 2;
            if (centered > labelX) {
                labelX = centered;
            }
        }
        Text_AddPrinterWithParamsAndColor(&sHud.window, FONT_SYSTEM, label,
            (u32)labelX, (u32)textY, TEXT_SPEED_NO_TRANSFER, col, NULL);
    }

    if (rightLabel != NULL) {
        TextColor col = selected
            ? TEXT_COLOR(WHUD_COL_WHITE, WHUD_COL_DARK_SHADOW, 0)
            : TEXT_COLOR(WHUD_COL_SLATE, WHUD_COL_TEXT_SHADOW, 0);
        int rightW = Font_CalcStringWidth(FONT_SYSTEM, rightLabel, 0);
        int rightX = x + w - 4 - rightW;
        if (rightX < x + contentLeft) {
            rightX = x + contentLeft;
        }
        Text_AddPrinterWithParamsAndColor(&sHud.window, FONT_SYSTEM, rightLabel,
            (u32)rightX, (u32)textY, TEXT_SPEED_NO_TRANSFER, col, NULL);
    }
}

static void WideHudEnsureWindow(BattleSubscreen *btlSubscreen, int menu)
{
    u8 tx, ty, tw, th;
    BgConfig *bgConfig = BattleSystem_GetBgConfig(btlSubscreen->battleSys);
    PaletteData *paletteData = BattleSystem_GetPaletteData(btlSubscreen->battleSys);

    ty = WIDE_HUD_BAR_Y;
    th = WIDE_HUD_BAR_H;
    if (menu == HUD_MENU_MOVE || menu == HUD_MENU_TARGET) {
        tx = WIDE_HUD_FULL_X;
        tw = WIDE_HUD_FULL_W;
    } else if (menu >= 13 && menu <= 17) {
        tx = WIDE_HUD_YESNO_X;
        tw = WIDE_HUD_YESNO_W;
    } else {
        tx = WIDE_HUD_ACTION_X;
        tw = WIDE_HUD_ACTION_W;
    }

    if (sHud.windowAdded && (!sHud.wideModeWindow || sHud.bdspModeWindow || sHud.winX != tx || sHud.winY != ty
            || sHud.winW != tw || sHud.winH != th)) {
        Window_FillRectWithColor(&sHud.window, 0, 0, 0, (u16)(sHud.winW * 8), (u16)(sHud.winH * 8));
        Window_Remove(&sHud.window);
        sHud.windowAdded = FALSE;
        sHud.wideModeWindow = FALSE;
        sHud.bdspModeWindow = FALSE;
        BattleHud_DrawWideMessageFrame(btlSubscreen->battleSys);
    }

    if (!sHud.windowAdded) {
        Window_Add(bgConfig, &sHud.window, BG_LAYER_MAIN_1,
            tx, ty, tw, th, WIDE_HUD_PALETTE, WIDE_HUD_CHAR_BASE);
        sHud.windowAdded = TRUE;
        sHud.wideModeWindow = TRUE;
        sHud.winX = tx;
        sHud.winY = ty;
        sHud.winW = tw;
        sHud.winH = th;
        sHud.lastMenu = -2;
    }

    if (paletteData != NULL) {
        PaletteData_LoadBuffer(paletteData, sWideHudPalette, PLTTBUF_MAIN_BG,
            WIDE_HUD_PALETTE * 16, sizeof(sWideHudPalette));
    }
}

static void WideHudKeepTilemapIntact(BattleSubscreen *btlSubscreen)
{
    BgConfig *bgConfig;
    u16 *tilemap;
    u32 x, y, idx;
    u16 expected;

    if (!sHud.windowAdded || !sHud.wideModeWindow) {
        return;
    }
    bgConfig = BattleSystem_GetBgConfig(btlSubscreen->battleSys);
    if (bgConfig == NULL) {
        return;
    }
    tilemap = Bg_GetTilemapBuffer(bgConfig, BG_LAYER_MAIN_1);
    if (tilemap == NULL) {
        return;
    }

    // windows[0] overlaps x=20..28, y=19..22. If message text reprinted and
    // put windows[0] back into the tilemap over our right-docked menu, restore
    // our menu window's tilemap entries cleanly.
    x = sHud.winX;
    y = sHud.winY + 1;
    idx = ((y & 0x20) * 32) + ((x & 0x20) * 32) + ((y & 0x1F) * 32) + (x & 0x1F);
    expected = (u16)((sHud.window.baseTile + sHud.winW) | (WIDE_HUD_PALETTE << 12));
    if (tilemap[idx] != expected) {
        Window_PutToTilemap(&sHud.window);
        Bg_ScheduleTilemapTransfer(bgConfig, BG_LAYER_MAIN_1);
    }
}

static void WideHudDrawAction(BattleSubscreen *btlSubscreen)
{
    MessageLoader *msgLoader = BattleSystem_GetMessageLoader(btlSubscreen->battleSys);
    u32 battleType = BattleSystem_GetBattleType(btlSubscreen->battleSys);
    int menu = btlSubscreen->activeMenuConfigIndex;
    int cx = btlSubscreen->cursor.x;
    int cy = btlSubscreen->cursor.y;
    int visW = WIDE_HUD_WIDTH_PX - WIDE_HUD_ACTION_X * 8; // 182px

    WideHudDrawPanelFrame(visW);

    if (menu == 5 || menu == 6) {
        // First battle: FIGHT only (sFirstBattleMenuTouchRects, button 0).
        String *fight = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_Fight);
        WideHudDrawButton(4, 4, 174, 40, WHUD_COL_CRIMSON, WHUD_COL_CRIMSON,
            TRUE, TRUE, fight, TRUE, NULL);
        String_Free(fight);
        return;
    }

    if (menu == 9 || menu == 10) {
        // Pal Park: BALL (cy==0, button 0) and RUN (cy==1, button 1).
        String *ball = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_BallPalPark);
        String *run = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_Run);
        WideHudDrawButton(4, 4, 174, 19, WHUD_COL_CRIMSON, WHUD_COL_CRIMSON,
            cy == 0, TRUE, ball, TRUE, NULL);
        WideHudDrawButton(4, 25, 174, 19, WHUD_COL_SLATE, WHUD_COL_SLATE,
            cy == 1, TRUE, run, TRUE, NULL);
        String_Free(ball);
        String_Free(run);
        return;
    }

    {
        String *fight, *bag, *party, *run;
        if (battleType & BATTLE_TYPE_SAFARI) {
            fight = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_Ball);
            bag = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_Bait);
            party = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_Mud);
        } else {
            fight = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_Fight);
            bag = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_Bag);
            party = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_Pokemon);
        }
        run = MessageLoader_GetNewString(msgLoader,
            btlSubscreen->activeMenuData.actionData.isWaitingForPartner
                ? BattleStrings_Text_Cancel : BattleStrings_Text_Run);

        // Authentic Platinum 2x3 silhouette matching sBattleMenuButtonLayout[2][3]:
        // Top full-width FIGHT (cy==0, button 0);
        // Bottom trio: BAG (cx==0, btn 1), RUN/CANCEL (cx==1, btn 3), POKeMON (cx==2, btn 2).
        WideHudDrawButton(4, 4, 174, 19, WHUD_COL_CRIMSON, WHUD_COL_CRIMSON,
            cy == 0, TRUE, fight, TRUE, NULL);
        WideHudDrawButton(4, 25, 52, 19, WHUD_COL_CERULEAN, WHUD_COL_CERULEAN,
            cy == 1 && cx == 0, TRUE, bag, TRUE, NULL);
        WideHudDrawButton(58, 25, 56, 19, WHUD_COL_SLATE, WHUD_COL_SLATE,
            cy == 1 && cx == 1, TRUE, run, TRUE, NULL);
        WideHudDrawButton(116, 25, 62, 19, WHUD_COL_EMERALD, WHUD_COL_EMERALD,
            cy == 1 && cx == 2, TRUE, party, TRUE, NULL);

        String_Free(fight);
        String_Free(bag);
        String_Free(party);
        String_Free(run);
    }
}

static void WideHudDrawMoves(BattleSubscreen *btlSubscreen)
{
    MoveSelectData *moveData = &btlSubscreen->activeMenuData.moveData;
    MessageLoader *msgLoader = BattleSystem_GetMessageLoader(btlSubscreen->battleSys);
    StringTemplate *template = BattleSystem_GetStringTemplate(btlSubscreen->battleSys);
    int cx = btlSubscreen->cursor.x;
    int cy = btlSubscreen->cursor.y;
    int i;

    WideHudDrawPanelFrame(WIDE_HUD_WIDTH_PX);
    WideHudDrawVerticalDivider(258);

    // Track last focused move slot so the info plaque stays meaningful even
    // while cursor rests on CANCEL.
    if (cy >= 0 && cy < 2 && cx >= 0 && cx < 2) {
        int focusIdx = cy * 2 + cx;
        if (moveData->moveIDs[focusIdx] != 0) {
            sHud.lastMoveSlot = focusIdx;
        }
    }
    if (sHud.lastMoveSlot < 0 || sHud.lastMoveSlot >= 4 || moveData->moveIDs[sHud.lastMoveSlot] == 0) {
        sHud.lastMoveSlot = 0;
        for (i = 0; i < 4; i++) {
            if (moveData->moveIDs[i] != 0) {
                sHud.lastMoveSlot = i;
                break;
            }
        }
    }

    // Left 2x2 move grid: 125x19px beveled buttons with 3px type-color stripe,
    // FONT_SYSTEM move name + right-aligned PP.
    // Col 0: x=4..128 (w=125), gap 3px, Col 1: x=132..256 (w=125).
    for (i = 0; i < 4; i++) {
        int col = i & 1;
        int row = i >> 1;
        int bx = col ? 132 : 4;
        int by = row ? 25 : 4;
        BOOL selected = (cx == col && cy == row);

        sHud.lastMovePP[i] = moveData->currPP[i];

        if (moveData->moveIDs[i] == 0) {
            WideHudDrawRecessedPlaque(bx, by, 125, 19, 0);
            continue;
        }
        {
            int moveType = (int)MoveTable_LoadParam(moveData->moveIDs[i], MOVEATTRIBUTE_TYPE);
            u8 stripeCol = WideHudMoveTypeStripeColor(moveType);
            u8 fillCol = WideHudMoveTypeFillColor(moveType);
            String *name = MessageUtil_MoveName(moveData->moveIDs[i], HEAP_ID_BATTLE);
            String *fmt = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_CurPPOutOfMaxPP);
            String *pp = String_Init(16, HEAP_ID_BATTLE);

            StringTemplate_SetNumber(template, 0, moveData->currPP[i], 2, 1, 0);
            StringTemplate_SetNumber(template, 1, moveData->maxPP[i], 2, 1, 0);
            StringTemplate_Format(template, pp, fmt);

            WideHudDrawButton(bx, by, 125, 19, stripeCol, fillCol,
                selected, TRUE, name, FALSE, pp);

            String_Free(name);
            String_Free(fmt);
            String_Free(pp);
        }
    }

    // Right column (x=264..337, 74px wide):
    // Top (y=4, h=19): MEGA toggle button when megaEvolutionAvailable,
    // else official Type name (TEXT_BANK_POKEMON_TYPE_NAMES) + base power.
    if (moveData->megaEvolutionAvailable) {
        BattleContext *ctx = BattleSystem_GetBattleContext(btlSubscreen->battleSys);
        int battler = BattleSystem_GetBattlerOfType(btlSubscreen->battleSys, btlSubscreen->battlerType);
        int on = ctx->megaEvolutionTriggered[battler] ? 1 : 0;
        BOOL megaSel = (cy == 2 && cx == 0);
        String *mega = MessageLoader_GetNewString(msgLoader, 1272); // "MEGA"
        String *stateStr = on ? WideHudAsciiString("ON") : NULL;

        if (on) {
            // Armed Mega Evolution: glowing gold/amber fill with crisp border.
            WideHudFillPx(264, 4, 74, 19, WHUD_COL_BORDER);
            WideHudFillPx(265, 5, 72, 17, megaSel ? WHUD_COL_WHITE : WHUD_COL_MEGA_GOLD);
            WideHudFillPx(266, 6, 70, 15, WHUD_COL_AMBER);
            WideHudFillPx(266, 6, 3, 15, WHUD_COL_MEGA_GOLD);
            Text_AddPrinterWithParamsAndColor(&sHud.window, FONT_SYSTEM, mega,
                272, 7, TEXT_SPEED_NO_TRANSFER,
                TEXT_COLOR(WHUD_COL_WHITE, WHUD_COL_BORDER, 0), NULL);
            if (stateStr != NULL) {
                int sw = Font_CalcStringWidth(FONT_SYSTEM, stateStr, 0);
                Text_AddPrinterWithParamsAndColor(&sHud.window, FONT_SYSTEM, stateStr,
                    (u32)(264 + 74 - 4 - sw), 7, TEXT_SPEED_NO_TRANSFER,
                    TEXT_COLOR(WHUD_COL_MEGA_GOLD, WHUD_COL_BORDER, 0), NULL);
            }
        } else {
            WideHudDrawButton(264, 4, 74, 19, WHUD_COL_MEGA_GOLD, WHUD_COL_VIOLET,
                megaSel, TRUE, mega, TRUE, NULL);
        }

        if (stateStr != NULL) {
            String_Free(stateStr);
        }
        String_Free(mega);
        sHud.lastMega = on;
    } else {
        u16 selMoveId = moveData->moveIDs[sHud.lastMoveSlot];
        int moveType = selMoveId ? (int)MoveTable_LoadParam(selMoveId, MOVEATTRIBUTE_TYPE) : TYPE_NORMAL;
        int movePower = selMoveId ? (int)MoveTable_LoadParam(selMoveId, MOVEATTRIBUTE_POWER) : 0;
        u8 stripeCol = WideHudMoveTypeStripeColor(moveType);
        MessageLoader *typeLoader = MessageLoader_Init(MSG_LOADER_LOAD_ON_DEMAND,
            NARC_INDEX_MSGDATA__PL_MSG, TEXT_BANK_POKEMON_TYPE_NAMES, HEAP_ID_BATTLE);
        String *typeName = MessageLoader_GetNewString(typeLoader, (u32)moveType);
        char pwrBuf[8];
        String *pwrStr;
        int pwrW;

        MessageLoader_Free(typeLoader);
        if (movePower > 0) {
            snprintf(pwrBuf, sizeof(pwrBuf), "%d", movePower);
        } else {
            snprintf(pwrBuf, sizeof(pwrBuf), "--");
        }
        pwrStr = WideHudAsciiString(pwrBuf);
        pwrW = Font_CalcStringWidth(FONT_SYSTEM, pwrStr, 0);

        WideHudDrawRecessedPlaque(264, 4, 74, 19, stripeCol);
        Text_AddPrinterWithParamsAndColor(&sHud.window, FONT_SYSTEM, typeName,
            268, 7, TEXT_SPEED_NO_TRANSFER,
            TEXT_COLOR(WHUD_COL_WHITE, WHUD_COL_BORDER, 0), NULL);
        Text_AddPrinterWithParamsAndColor(&sHud.window, FONT_SYSTEM, pwrStr,
            (u32)(264 + 74 - 3 - pwrW), 7, TEXT_SPEED_NO_TRANSFER,
            TEXT_COLOR(WHUD_COL_MEGA_GOLD, WHUD_COL_BORDER, 0), NULL);

        String_Free(typeName);
        String_Free(pwrStr);
        sHud.lastMega = -1;
    }

    // Bottom right (x=264, y=25, w=74, h=19): CANCEL / BACK button (button 0).
    {
        BOOL cancelSel = (cy == 2 && (cx == 1 || !moveData->megaEvolutionAvailable));
        String *cancel = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_Cancel2);
        WideHudDrawButton(264, 25, 74, 19, WHUD_COL_SLATE, WHUD_COL_SLATE,
            cancelSel, TRUE, cancel, TRUE, NULL);
        String_Free(cancel);
    }
}

static BOOL WideHudTargetMultiSelected(int targetingLayout, int row, int col)
{
    // Multi-target layouts from BattleSystem_Cursor_Battler:
    // 1=opponents, 2=all adj (slot1), 3=field, 5=user side, 7=all adj (slot2).
    switch (targetingLayout) {
    case 1:
        return row == 0;
    case 2:
        return row == 0 || (row == 1 && col == 1);
    case 7:
        return row == 0 || (row == 1 && col == 0);
    case 3:
        return TRUE;
    case 5:
        return row == 1;
    default:
        return FALSE;
    }
}

static void WideHudDrawTarget(BattleSubscreen *btlSubscreen)
{
    TargetSelectData *data = &btlSubscreen->activeMenuData.targetSelectData;
    MessageLoader *msgLoader = BattleSystem_GetMessageLoader(btlSubscreen->battleSys);
    StringTemplate *template = BattleSystem_GetStringTemplate(btlSubscreen->battleSys);
    int cx = btlSubscreen->cursor.x;
    int cy = btlSubscreen->cursor.y;
    int layout = btlSubscreen->targetingLayout;
    BOOL isMultiTarget = (layout == 1 || layout == 2 || layout == 3 || layout == 5 || layout == 7);
    BOOL cancelSel = isMultiTarget ? (cy > 0) : (cy == 2);
    String *targetHdr = WideHudAsciiString("TARGET");
    String *cancel = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_Cancel3);
    String *message = String_Init(32, HEAP_ID_BATTLE);
    u8 battlersByType[6];
    // Spatial 2x2 grid matching sSelectTargetMenuButtonLayout[3][2] & 3D battlefield:
    // Row 0 (Enemies): Left = battlersByType[5] (btn 3), Right = battlersByType[3] (btn 1)
    // Row 1 (Allies):  Left = battlersByType[2] (btn 0), Right = battlersByType[4] (btn 2)
    static const u8 sGridTypeIdx[2][2] = {
        { 5, 3 },
        { 2, 4 }
    };
    int row, col;

    BattleSystem_SetBattlersByType(btlSubscreen->battleSys, battlersByType);

    WideHudDrawPanelFrame(WIDE_HUD_WIDTH_PX);
    WideHudDrawVerticalDivider(83);

    // Left column (x=4..81, 78px wide): "TARGET" plaque + CANCEL button (btn 4).
    WideHudDrawRecessedPlaque(4, 4, 78, 19, WHUD_COL_MINT_TRIM);
    {
        int hw = Font_CalcStringWidth(FONT_SYSTEM, targetHdr, 0);
        int hx = 4 + (78 - hw) / 2;
        Text_AddPrinterWithParamsAndColor(&sHud.window, FONT_SYSTEM, targetHdr,
            (u32)hx, 7, TEXT_SPEED_NO_TRANSFER,
            TEXT_COLOR(WHUD_COL_WHITE, WHUD_COL_BORDER, 0), NULL);
    }
    WideHudDrawButton(4, 25, 78, 19, WHUD_COL_SLATE, WHUD_COL_SLATE,
        cancelSel, TRUE, cancel, TRUE, NULL);

    // Right 2x2 spatial grid (x=88..337: two 124px cols + 2px gap).
    for (row = 0; row < 2; row++) {
        for (col = 0; col < 2; col++) {
            int battlerIndex = battlersByType[sGridTypeIdx[row][col]];
            int bx = col ? 214 : 88;
            int by = row ? 25 : 4;
            BOOL isEnemy = (row == 0);
            u8 accent = isEnemy ? WHUD_COL_CRIMSON : WHUD_COL_EMERALD;
            BOOL selected;

            if (isMultiTarget) {
                selected = (!cancelSel) && WideHudTargetMultiSelected(layout, row, col);
            } else {
                selected = (!cancelSel) && (cy == row && cx == col);
            }

            if (!data->targetMonData[battlerIndex].isPresent) {
                WideHudDrawRecessedPlaque(bx, by, 124, 19, 0);
                continue;
            }
            {
                String *formatMsg = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_HealthBoxPokemonName);
                Pokemon *partyMon = BattleSystem_GetPartyPokemon(btlSubscreen->battleSys,
                    battlerIndex, data->targetMonData[battlerIndex].partySlot);
                StringTemplate_SetNickname(template, 0, Pokemon_GetBoxPokemon(partyMon));
                StringTemplate_Format(template, message, formatMsg);
                WideHudDrawButton(bx, by, 124, 19, accent, accent,
                    selected, TRUE, message, FALSE, NULL);
                String_Free(formatMsg);
            }
        }
    }

    String_Free(targetHdr);
    String_Free(cancel);
    String_Free(message);
}

static void WideHudDrawYesNo(BattleSubscreen *btlSubscreen)
{
    MessageLoader *msgLoader = BattleSystem_GetMessageLoader(btlSubscreen->battleSys);
    String *yes = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_Yes);
    String *no = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_No);
    int cy = btlSubscreen->cursor.y;
    int visW = WIDE_HUD_WIDTH_PX - WIDE_HUD_YESNO_X * 8; // 86px

    WideHudDrawPanelFrame(visW);
    WideHudDrawButton(4, 4, 78, 19, WHUD_COL_EMERALD, WHUD_COL_EMERALD,
        cy == 0, TRUE, yes, TRUE, NULL);
    WideHudDrawButton(4, 25, 78, 19, WHUD_COL_CRIMSON, WHUD_COL_CRIMSON,
        cy == 1, TRUE, no, TRUE, NULL);

    String_Free(yes);
    String_Free(no);
}

static int WideHudTouchButtonIndex(BattleSubscreen *btlSubscreen, int x, int y)
{
    int menu = btlSubscreen->activeMenuConfigIndex;
    int ly;

    // Wide pixel-art HUD bar lives at y=144..191 (tiles 18..23), x=0..341.
    if (y < WIDE_HUD_BAR_Y_PX || y >= WIDE_HUD_BAR_Y_PX + WIDE_HUD_BAR_H_PX) {
        return -1;
    }
    if (x < 0 || x >= WIDE_HUD_WIDTH_PX) {
        return -1;
    }
    ly = y - WIDE_HUD_BAR_Y_PX; // 0..47; top row 4..22, bottom row 25..43

    if (menu >= 13 && menu <= 17) {
        if (x < WIDE_HUD_YESNO_X * 8) {
            return -1;
        }
        return ly < 24 ? 0 : 1; // YES=0, NO=1
    }

    if (menu == HUD_MENU_MOVE) {
        if (x >= 260) {
            if (ly < 24) {
                return btlSubscreen->activeMenuData.moveData.megaEvolutionAvailable ? 5 : -1;
            }
            return 0; // CANCEL / BACK
        }
        {
            int col = x < 130 ? 0 : 1;
            int row = ly < 24 ? 0 : 1;
            int moveIdx = row * 2 + col;
            if (btlSubscreen->activeMenuData.moveData.moveIDs[moveIdx] == 0) {
                return -1;
            }
            return 1 + moveIdx; // moves 1..4 at touch indices 1..4
        }
    }

    if (menu == HUD_MENU_TARGET) {
        if (x < 84) {
            return ly >= 24 ? 4 : -1; // CANCEL=4; top is TARGET header
        }
        {
            static const u8 layout[2][2] = { { 3, 1 }, { 0, 2 } };
            int col = x < 213 ? 0 : 1;
            int row = ly < 24 ? 0 : 1;
            return layout[row][col];
        }
    }

    if (menu >= 1 && menu <= 10) {
        int lx;
        if (x < WIDE_HUD_ACTION_X * 8) {
            return -1;
        }
        lx = x - WIDE_HUD_ACTION_X * 8; // 0..181
        if (menu == 5 || menu == 6) {
            return 0; // First battle: FIGHT only
        }
        if (menu == 9 || menu == 10) {
            return ly < 24 ? 0 : 1; // Pal Park: BALL=0, RUN=1
        }
        if (ly < 24) {
            return 0; // FIGHT / BALL
        }
        if (lx < 57) {
            return 1; // BAG / BAIT
        }
        if (lx < 115) {
            return 3; // RUN / CANCEL
        }
        return 2; // POKeMON / MUD
    }

    return -1;
}

// --- Option A: Authentic Platinum Pixel-Art BDSP Corner-Docked Battle HUD ---

static BOOL BdspHudHasWildQuickBall(BattleSubscreen *btlSubscreen, int menu)
{
    u32 battleType;

    if (menu < 1 || menu > 10 || menu == 5 || menu == 6 || menu == 9 || menu == 10) {
        return FALSE;
    }
    battleType = BattleSystem_GetBattleType(btlSubscreen->battleSys);
    if (battleType & (BATTLE_TYPE_TRAINER | BATTLE_TYPE_SAFARI | BATTLE_TYPE_PAL_PARK)) {
        return FALSE;
    }
    return TRUE;
}

static void BdspHudClearBg1Lower(BattleSystem *battleSys)
{
    BgConfig *bgConfig = BattleSystem_GetBgConfig(battleSys);

    if (bgConfig == NULL) {
        return;
    }
    // Keep BG_LAYER_MAIN_1 transparent outside the right-docked BDSP menu
    // so 100% of the 3D clearing and bottom-left player healthbox show cleanly.
    Bg_FillTilemapRect(bgConfig, BG_LAYER_MAIN_1, 0, 0, 10, WIDE_HUD_FULL_W, 14, WIDE_HUD_PALETTE);
}

static void BdspHudEnsureWindow(BattleSubscreen *btlSubscreen, int menu)
{
    u8 tx, ty, tw, th;
    BgConfig *bgConfig = BattleSystem_GetBgConfig(btlSubscreen->battleSys);
    PaletteData *paletteData = BattleSystem_GetPaletteData(btlSubscreen->battleSys);

    if (menu == HUD_MENU_MOVE) {
        tx = BDSP_HUD_MOVE_X;
        ty = BDSP_HUD_MOVE_Y;
        tw = BDSP_HUD_MOVE_W;
        th = BDSP_HUD_MOVE_H;
    } else if (menu == HUD_MENU_TARGET) {
        tx = BDSP_HUD_TARGET_X;
        ty = BDSP_HUD_TARGET_Y;
        tw = BDSP_HUD_TARGET_W;
        th = BDSP_HUD_TARGET_H;
    } else if (menu >= 13 && menu <= 17) {
        tx = BDSP_HUD_YESNO_X;
        ty = BDSP_HUD_YESNO_Y;
        tw = BDSP_HUD_YESNO_W;
        th = BDSP_HUD_YESNO_H;
    } else {
        tx = BDSP_HUD_ACTION_X;
        ty = BDSP_HUD_ACTION_Y;
        tw = BDSP_HUD_ACTION_W;
        th = BDSP_HUD_ACTION_H;
    }

    if (sHud.windowAdded && (!sHud.bdspModeWindow || sHud.winX != tx || sHud.winY != ty
            || sHud.winW != tw || sHud.winH != th)) {
        Window_FillRectWithColor(&sHud.window, 0, 0, 0, (u16)(sHud.winW * 8), (u16)(sHud.winH * 8));
        Window_ScheduleCopyToVRAM(&sHud.window);
        Bg_FillTilemapRect(bgConfig, BG_LAYER_MAIN_1, 0, sHud.winX, sHud.winY, sHud.winW, sHud.winH, WIDE_HUD_PALETTE);
        Window_Remove(&sHud.window);
        sHud.windowAdded = FALSE;
        sHud.wideModeWindow = FALSE;
        sHud.bdspModeWindow = FALSE;
    }

    if (menu >= 13 && menu <= 17) {
        // Yes/No prompts display a question in windows[0] below the Yes/No box.
        Window *msgWin = BattleSystem_GetWindow(btlSubscreen->battleSys, 0);
        if (msgWin != NULL && msgWin->bgConfig != NULL) {
            Window_DrawMessageBox(msgWin, 1, 10);
            Window_PutToTilemap(msgWin);
            Bg_ScheduleTilemapTransfer(bgConfig, BG_LAYER_MAIN_1);
        }
    } else {
        BdspHudClearBg1Lower(btlSubscreen->battleSys);
    }

    if (!sHud.windowAdded) {
        Window_Add(bgConfig, &sHud.window, BG_LAYER_MAIN_1,
            tx, ty, tw, th, WIDE_HUD_PALETTE, WIDE_HUD_CHAR_BASE);
        sHud.windowAdded = TRUE;
        sHud.wideModeWindow = TRUE;
        sHud.bdspModeWindow = TRUE;
        sHud.winX = tx;
        sHud.winY = ty;
        sHud.winW = tw;
        sHud.winH = th;
        sHud.lastMenu = -2;
    }

    Window_PutToTilemap(&sHud.window);

    if (paletteData != NULL) {
        PaletteData_LoadBuffer(paletteData, sWideHudPalette, PLTTBUF_MAIN_BG,
            WIDE_HUD_PALETTE * 16, sizeof(sWideHudPalette));
    }
}

static void BdspHudKeepTilemapIntact(BattleSubscreen *btlSubscreen, int menu)
{
    BgConfig *bgConfig;
    u16 *tilemap;
    u32 x, y, idx;
    u16 expected;
    BOOL needsRestore = FALSE;

    if (!sHud.windowAdded || !sHud.bdspModeWindow) {
        return;
    }
    bgConfig = BattleSystem_GetBgConfig(btlSubscreen->battleSys);
    if (bgConfig == NULL) {
        return;
    }
    tilemap = Bg_GetTilemapBuffer(bgConfig, BG_LAYER_MAIN_1);
    if (tilemap == NULL) {
        return;
    }

    x = sHud.winX;
    y = sHud.winY + 1;
    idx = ((y & 0x20) * 32) + ((x & 0x20) * 32) + ((y & 0x1F) * 32) + (x & 0x1F);
    expected = (u16)((sHud.window.baseTile + sHud.winW) | (WIDE_HUD_PALETTE << 12));
    if (tilemap[idx] != expected) {
        needsRestore = TRUE;
    }

    // For Action, Move, and Target, ensure no message box tiles slipped back in.
    if (menu >= 1 && menu <= 12 && tilemap[19 * 32 + 2] != 0) {
        BdspHudClearBg1Lower(btlSubscreen->battleSys);
        needsRestore = TRUE;
    }

    if (needsRestore) {
        Window_PutToTilemap(&sHud.window);
        Bg_ScheduleTilemapTransfer(bgConfig, BG_LAYER_MAIN_1);
    }
}

static void BdspHudDrawQuickBallPill(int x, int y, int w, int h)
{
    String *xBadge = WideHudAsciiString("X");
    String *ballLabel = WideHudAsciiString("BALL");
    int bx = x + 6;
    int by = y + 3;

    // Compact slate/cerulean authentic Platinum beveled pill.
    WideHudFillPx(x, y, w, h, WHUD_COL_BORDER);
    WideHudFillPx(x + 1, y + 1, w - 2, h - 2, WHUD_COL_SLATE);
    WideHudFillPx(x + 1, y + 1, w - 2, 1, WHUD_COL_CERULEAN);
    WideHudFillPx(x + 1, y + 1, 1, h - 2, WHUD_COL_CERULEAN);
    WideHudFillPx(x + 1, y + h - 2, w - 2, 1, WHUD_COL_PANEL_BG);
    WideHudFillPx(x + w - 2, y + 1, 1, h - 2, WHUD_COL_PANEL_BG);
    WideHudFillPx(x + 1, y + 1, 3, h - 2, WHUD_COL_CERULEAN);

    // Miniature 9x9 pixel-art Poke Ball icon.
    WideHudFillPx(bx + 2, by, 5, 1, WHUD_COL_BORDER);
    WideHudFillPx(bx + 1, by + 1, 7, 1, WHUD_COL_BORDER);
    WideHudFillPx(bx, by + 2, 9, 5, WHUD_COL_BORDER);
    WideHudFillPx(bx + 1, by + 7, 7, 1, WHUD_COL_BORDER);
    WideHudFillPx(bx + 2, by + 8, 5, 1, WHUD_COL_BORDER);
    // Red upper dome + specular dot.
    WideHudFillPx(bx + 2, by + 1, 5, 1, WHUD_COL_CRIMSON);
    WideHudFillPx(bx + 1, by + 2, 7, 2, WHUD_COL_CRIMSON);
    WideHudFillPx(bx + 2, by + 2, 1, 1, WHUD_COL_WHITE);
    // White lower dome.
    WideHudFillPx(bx + 1, by + 5, 7, 2, WHUD_COL_WHITE);
    WideHudFillPx(bx + 2, by + 7, 5, 1, WHUD_COL_WHITE);
    // Center band and white button.
    WideHudFillPx(bx + 1, by + 4, 7, 1, WHUD_COL_BORDER);
    WideHudFillPx(bx + 3, by + 3, 3, 3, WHUD_COL_BORDER);
    WideHudFillPx(bx + 4, by + 4, 1, 1, WHUD_COL_WHITE);

    // Gold "X" shortcut glyph + white "BALL" label.
    Text_AddPrinterWithParamsAndColor(&sHud.window, FONT_SYSTEM, xBadge,
        (u32)(x + 20), (u32)(y + 2), TEXT_SPEED_NO_TRANSFER,
        TEXT_COLOR(WHUD_COL_MEGA_GOLD, WHUD_COL_BORDER, 0), NULL);
    Text_AddPrinterWithParamsAndColor(&sHud.window, FONT_SYSTEM, ballLabel,
        (u32)(x + 36), (u32)(y + 2), TEXT_SPEED_NO_TRANSFER,
        TEXT_COLOR(WHUD_COL_WHITE, WHUD_COL_DARK_SHADOW, 0), NULL);

    String_Free(xBadge);
    String_Free(ballLabel);
}

static void BdspHudDrawAction(BattleSubscreen *btlSubscreen)
{
    MessageLoader *msgLoader = BattleSystem_GetMessageLoader(btlSubscreen->battleSys);
    u32 battleType = BattleSystem_GetBattleType(btlSubscreen->battleSys);
    int menu = btlSubscreen->activeMenuConfigIndex;
    int cx = btlSubscreen->cursor.x;
    int cy = btlSubscreen->cursor.y;

    // Transparent backing so the 3D clearing shows right between the buttons.
    WideHudFillPx(0, 0, sHud.winW * 8, sHud.winH * 8, WHUD_COL_TRANSPARENT);

    if (menu == 5 || menu == 6) {
        // First battle: FIGHT only (touch button 0).
        String *fight = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_Fight);
        WideHudDrawButton(4, 76, 86, 26, WHUD_COL_CRIMSON, WHUD_COL_CRIMSON,
            TRUE, TRUE, fight, TRUE, NULL);
        String_Free(fight);
        return;
    }

    if (menu == 9 || menu == 10) {
        // Pal Park: BALL (cy==0, button 0) and RUN (cy==1, button 1).
        String *ball = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_BallPalPark);
        String *run = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_Run);
        WideHudDrawButton(4, 62, 86, 19, WHUD_COL_CRIMSON, WHUD_COL_CRIMSON,
            cy == 0, TRUE, ball, TRUE, NULL);
        WideHudDrawButton(4, 83, 86, 19, WHUD_COL_CERULEAN, WHUD_COL_CERULEAN,
            cy == 1, TRUE, run, TRUE, NULL);
        String_Free(ball);
        String_Free(run);
        return;
    }

    if (BdspHudHasWildQuickBall(btlSubscreen, menu)) {
        BdspHudDrawQuickBallPill(4, 2, 86, 16);
    }

    {
        String *fight, *bag, *party, *run;

        if (battleType & BATTLE_TYPE_SAFARI) {
            fight = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_Ball);
            bag = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_Bait);
            party = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_Mud);
        } else {
            fight = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_Fight);
            bag = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_Bag);
            party = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_Pokemon);
        }
        run = MessageLoader_GetNewString(msgLoader,
            btlSubscreen->activeMenuData.actionData.isWaitingForPartner
                ? BattleStrings_Text_Cancel : BattleStrings_Text_Run);

        // BDSP vertical 4-button stack: FIGHT, POKeMON, BAG, RUN/CANCEL.
        WideHudDrawButton(4, 20, 86, 19, WHUD_COL_CRIMSON, WHUD_COL_CRIMSON,
            cy == 0, TRUE, fight, TRUE, NULL);
        WideHudDrawButton(4, 41, 86, 19, WHUD_COL_EMERALD, WHUD_COL_EMERALD,
            cy == 1 && cx == 2, TRUE, party, TRUE, NULL);
        WideHudDrawButton(4, 62, 86, 19, WHUD_COL_MEGA_GOLD, WHUD_COL_AMBER,
            cy == 1 && cx == 0, TRUE, bag, TRUE, NULL);
        WideHudDrawButton(4, 83, 86, 19, WHUD_COL_CERULEAN, WHUD_COL_CERULEAN,
            cy == 1 && cx == 1, TRUE, run, TRUE, NULL);

        String_Free(fight);
        String_Free(bag);
        String_Free(party);
        String_Free(run);
    }
}

static void BdspHudDrawMoves(BattleSubscreen *btlSubscreen)
{
    MoveSelectData *moveData = &btlSubscreen->activeMenuData.moveData;
    MessageLoader *msgLoader = BattleSystem_GetMessageLoader(btlSubscreen->battleSys);
    StringTemplate *template = BattleSystem_GetStringTemplate(btlSubscreen->battleSys);
    int cx = btlSubscreen->cursor.x;
    int cy = btlSubscreen->cursor.y;
    int visW = WIDE_HUD_WIDTH_PX - BDSP_HUD_MOVE_X * 8; // 166px
    int visH = BDSP_HUD_MOVE_H * 8; // 112px
    int i;

    WideHudDrawPanelFrameEx(visW, visH);

    if (cy >= 0 && cy < 2 && cx >= 0 && cx < 2) {
        int focusIdx = cy * 2 + cx;
        if (moveData->moveIDs[focusIdx] != 0) {
            sHud.lastMoveSlot = focusIdx;
        }
    }
    if (sHud.lastMoveSlot < 0 || sHud.lastMoveSlot >= 4 || moveData->moveIDs[sHud.lastMoveSlot] == 0) {
        sHud.lastMoveSlot = 0;
        for (i = 0; i < 4; i++) {
            if (moveData->moveIDs[i] != 0) {
                sHud.lastMoveSlot = i;
                break;
            }
        }
    }

    // Stacked 4 move buttons: 158x19px each, 2px gaps (y = 4, 25, 46, 67).
    for (i = 0; i < 4; i++) {
        int col = i & 1;
        int row = i >> 1;
        int by = 4 + i * 21;
        BOOL selected = (cx == col && cy == row);

        sHud.lastMovePP[i] = moveData->currPP[i];

        if (moveData->moveIDs[i] == 0) {
            WideHudDrawRecessedPlaque(4, by, 158, 19, 0);
            continue;
        }
        {
            int moveType = (int)MoveTable_LoadParam(moveData->moveIDs[i], MOVEATTRIBUTE_TYPE);
            u8 stripeCol = WideHudMoveTypeStripeColor(moveType);
            u8 fillCol = WideHudMoveTypeFillColor(moveType);
            String *name = MessageUtil_MoveName(moveData->moveIDs[i], HEAP_ID_BATTLE);
            String *fmt = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_CurPPOutOfMaxPP);
            String *pp = String_Init(16, HEAP_ID_BATTLE);

            StringTemplate_SetNumber(template, 0, moveData->currPP[i], 2, 1, 0);
            StringTemplate_SetNumber(template, 1, moveData->maxPP[i], 2, 1, 0);
            StringTemplate_Format(template, pp, fmt);

            WideHudDrawButton(4, by, 158, 19, stripeCol, fillCol,
                selected, TRUE, name, FALSE, pp);

            String_Free(name);
            String_Free(fmt);
            String_Free(pp);
        }
    }

    // Bottom row (y = 88, h = 19): left = MEGA toggle or Type + Power plaque (w = 96),
    // right = CANCEL (x = 102, w = 60).
    if (moveData->megaEvolutionAvailable) {
        BattleContext *ctx = BattleSystem_GetBattleContext(btlSubscreen->battleSys);
        int battler = BattleSystem_GetBattlerOfType(btlSubscreen->battleSys, btlSubscreen->battlerType);
        int on = ctx->megaEvolutionTriggered[battler] ? 1 : 0;
        BOOL megaSel = (cy == 2 && cx == 0);
        String *mega = MessageLoader_GetNewString(msgLoader, 1272); // "MEGA"
        String *stateStr = on ? WideHudAsciiString("ON") : NULL;

        if (on) {
            WideHudFillPx(4, 88, 96, 19, WHUD_COL_BORDER);
            WideHudFillPx(5, 89, 94, 17, megaSel ? WHUD_COL_WHITE : WHUD_COL_MEGA_GOLD);
            WideHudFillPx(6, 90, 92, 15, WHUD_COL_AMBER);
            WideHudFillPx(6, 90, 3, 15, WHUD_COL_MEGA_GOLD);
            Text_AddPrinterWithParamsAndColor(&sHud.window, FONT_SYSTEM, mega,
                12, 91, TEXT_SPEED_NO_TRANSFER,
                TEXT_COLOR(WHUD_COL_WHITE, WHUD_COL_BORDER, 0), NULL);
            if (stateStr != NULL) {
                int sw = Font_CalcStringWidth(FONT_SYSTEM, stateStr, 0);
                Text_AddPrinterWithParamsAndColor(&sHud.window, FONT_SYSTEM, stateStr,
                    (u32)(4 + 96 - 5 - sw), 91, TEXT_SPEED_NO_TRANSFER,
                    TEXT_COLOR(WHUD_COL_MEGA_GOLD, WHUD_COL_BORDER, 0), NULL);
            }
        } else {
            WideHudDrawButton(4, 88, 96, 19, WHUD_COL_MEGA_GOLD, WHUD_COL_VIOLET,
                megaSel, TRUE, mega, TRUE, NULL);
        }

        if (stateStr != NULL) {
            String_Free(stateStr);
        }
        String_Free(mega);
        sHud.lastMega = on;
    } else {
        u16 selMoveId = moveData->moveIDs[sHud.lastMoveSlot];
        int moveType = selMoveId ? (int)MoveTable_LoadParam(selMoveId, MOVEATTRIBUTE_TYPE) : TYPE_NORMAL;
        int movePower = selMoveId ? (int)MoveTable_LoadParam(selMoveId, MOVEATTRIBUTE_POWER) : 0;
        u8 stripeCol = WideHudMoveTypeStripeColor(moveType);
        MessageLoader *typeLoader = MessageLoader_Init(MSG_LOADER_LOAD_ON_DEMAND,
            NARC_INDEX_MSGDATA__PL_MSG, TEXT_BANK_POKEMON_TYPE_NAMES, HEAP_ID_BATTLE);
        String *typeName = MessageLoader_GetNewString(typeLoader, (u32)moveType);
        char pwrBuf[8];
        String *pwrStr;
        int pwrW;

        MessageLoader_Free(typeLoader);
        if (movePower > 0) {
            snprintf(pwrBuf, sizeof(pwrBuf), "%d", movePower);
        } else {
            snprintf(pwrBuf, sizeof(pwrBuf), "--");
        }
        pwrStr = WideHudAsciiString(pwrBuf);
        pwrW = Font_CalcStringWidth(FONT_SYSTEM, pwrStr, 0);

        WideHudDrawRecessedPlaque(4, 88, 96, 19, stripeCol);
        Text_AddPrinterWithParamsAndColor(&sHud.window, FONT_SYSTEM, typeName,
            9, 91, TEXT_SPEED_NO_TRANSFER,
            TEXT_COLOR(WHUD_COL_WHITE, WHUD_COL_BORDER, 0), NULL);
        Text_AddPrinterWithParamsAndColor(&sHud.window, FONT_SYSTEM, pwrStr,
            (u32)(4 + 96 - 4 - pwrW), 91, TEXT_SPEED_NO_TRANSFER,
            TEXT_COLOR(WHUD_COL_MEGA_GOLD, WHUD_COL_BORDER, 0), NULL);

        String_Free(typeName);
        String_Free(pwrStr);
        sHud.lastMega = -1;
    }

    {
        BOOL cancelSel = (cy == 2 && (cx == 1 || !moveData->megaEvolutionAvailable));
        String *cancel = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_Cancel2);
        WideHudDrawButton(102, 88, 60, 19, WHUD_COL_SLATE, WHUD_COL_SLATE,
            cancelSel, TRUE, cancel, TRUE, NULL);
        String_Free(cancel);
    }
}

static void BdspHudDrawTarget(BattleSubscreen *btlSubscreen)
{
    TargetSelectData *data = &btlSubscreen->activeMenuData.targetSelectData;
    MessageLoader *msgLoader = BattleSystem_GetMessageLoader(btlSubscreen->battleSys);
    StringTemplate *template = BattleSystem_GetStringTemplate(btlSubscreen->battleSys);
    int cx = btlSubscreen->cursor.x;
    int cy = btlSubscreen->cursor.y;
    int layout = btlSubscreen->targetingLayout;
    BOOL isMultiTarget = (layout == 1 || layout == 2 || layout == 3 || layout == 5 || layout == 7);
    BOOL cancelSel = isMultiTarget ? (cy > 0) : (cy == 2);
    String *cancel = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_Cancel3);
    String *message = String_Init(32, HEAP_ID_BATTLE);
    u8 battlersByType[6];
    static const u8 sGridTypeIdx[2][2] = {
        { 5, 3 },
        { 2, 4 }
    };
    int visW = WIDE_HUD_WIDTH_PX - BDSP_HUD_TARGET_X * 8; // 198px
    int visH = BDSP_HUD_TARGET_H * 8; // 56px
    int row, col;

    BattleSystem_SetBattlersByType(btlSubscreen->battleSys, battlersByType);

    // Compact 3px authentic Platinum border framing 3 rows of 16px buttons.
    WideHudFillPx(0, 0, sHud.winW * 8, visH, WHUD_COL_BORDER);
    WideHudFillPx(1, 1, visW - 2, visH - 2, WHUD_COL_MINT_TRIM);
    WideHudFillPx(2, 2, visW - 4, visH - 4, WHUD_COL_BORDER);
    WideHudFillPx(3, 3, visW - 6, visH - 6, WHUD_COL_PANEL_BG);

    // Spatial 2x2 grid: Row 0 (Enemies, y=3..18), Row 1 (Allies, y=20..35).
    for (row = 0; row < 2; row++) {
        for (col = 0; col < 2; col++) {
            int battlerIndex = battlersByType[sGridTypeIdx[row][col]];
            int bx = col ? 100 : 4;
            int by = row ? 20 : 3;
            u8 accent = (row == 0) ? WHUD_COL_CRIMSON : WHUD_COL_EMERALD;
            BOOL selected;

            if (isMultiTarget) {
                selected = (!cancelSel) && WideHudTargetMultiSelected(layout, row, col);
            } else {
                selected = (!cancelSel) && (cy == row && cx == col);
            }

            if (!data->targetMonData[battlerIndex].isPresent) {
                WideHudDrawRecessedPlaque(bx, by, 94, 16, 0);
                continue;
            }
            {
                String *formatMsg = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_HealthBoxPokemonName);
                Pokemon *partyMon = BattleSystem_GetPartyPokemon(btlSubscreen->battleSys,
                    battlerIndex, data->targetMonData[battlerIndex].partySlot);
                StringTemplate_SetNickname(template, 0, Pokemon_GetBoxPokemon(partyMon));
                StringTemplate_Format(template, message, formatMsg);
                WideHudDrawButton(bx, by, 94, 16, accent, accent,
                    selected, TRUE, message, FALSE, NULL);
                String_Free(formatMsg);
            }
        }
    }

    // Bottom CANCEL bar (y=37..52, button 4).
    WideHudDrawButton(4, 37, 190, 16, WHUD_COL_SLATE, WHUD_COL_SLATE,
        cancelSel, TRUE, cancel, TRUE, NULL);

    String_Free(cancel);
    String_Free(message);
}

static int BdspHudTouchButtonIndex(BattleSubscreen *btlSubscreen, int x, int y)
{
    int menu = btlSubscreen->activeMenuConfigIndex;

    if (x < 0 || x >= WIDE_HUD_WIDTH_PX || y < 0 || y >= HW_LCD_HEIGHT) {
        return -1;
    }

    if (menu >= 13 && menu <= 17) {
        int wx = BDSP_HUD_YESNO_X * 8;
        int wy = BDSP_HUD_YESNO_Y * 8;
        if (x < wx || y < wy || y >= wy + BDSP_HUD_YESNO_H * 8) {
            return -1;
        }
        return (y - wy) < 24 ? 0 : 1; // YES=0, NO=1
    }

    if (menu == HUD_MENU_MOVE) {
        int wx = BDSP_HUD_MOVE_X * 8; // 176
        int wy = BDSP_HUD_MOVE_Y * 8; // 80
        int lx, ly;
        if (x < wx || y < wy) {
            return -1;
        }
        lx = x - wx; // 0..165
        ly = y - wy; // 0..111
        if (ly >= 87 && ly < 109) {
            if (lx >= 101) {
                return 0; // CANCEL
            }
            if (lx >= 4) {
                return btlSubscreen->activeMenuData.moveData.megaEvolutionAvailable ? 5 : -1;
            }
            return -1;
        }
        if (lx >= 4 && lx < 162 && ly >= 4 && ly < 87) {
            int moveIdx = (ly - 4) / 21;
            if (moveIdx >= 0 && moveIdx < 4 && btlSubscreen->activeMenuData.moveData.moveIDs[moveIdx] != 0) {
                return 1 + moveIdx; // moves 1..4 at touch indices 1..4
            }
        }
        return -1;
    }

    if (menu == HUD_MENU_TARGET) {
        int wx = BDSP_HUD_TARGET_X * 8; // 144
        int wy = BDSP_HUD_TARGET_Y * 8; // 136
        int lx, ly;
        if (x < wx || y < wy) {
            return -1;
        }
        lx = x - wx; // 0..197
        ly = y - wy; // 0..55
        if (ly >= 37) {
            return 4; // CANCEL
        }
        if (ly >= 3 && lx >= 4 && lx < 194) {
            static const u8 layout[2][2] = { { 3, 1 }, { 0, 2 } };
            int row = ly < 20 ? 0 : 1;
            int col = lx < 99 ? 0 : 1;
            return layout[row][col];
        }
        return -1;
    }

    if (menu >= 1 && menu <= 10) {
        int wx = BDSP_HUD_ACTION_X * 8; // 248
        int wy = BDSP_HUD_ACTION_Y * 8; // 88
        int lx, ly;
        if (x < wx || y < wy) {
            return -1;
        }
        lx = x - wx; // 0..93
        ly = y - wy; // 0..103
        if (lx < 3 || lx >= 91) {
            return -1;
        }
        if (menu == 5 || menu == 6) {
            return (ly >= 74 && ly < 103) ? 0 : -1; // First battle: FIGHT only
        }
        if (menu == 9 || menu == 10) {
            if (ly >= 61 && ly < 82) {
                return 0; // Pal Park: BALL
            }
            if (ly >= 82 && ly < 103) {
                return 1; // Pal Park: RUN
            }
            return -1;
        }
        if (BdspHudHasWildQuickBall(btlSubscreen, menu) && ly >= 1 && ly < 19) {
            return 1; // [X] BALL quick-bag pill
        }
        if (ly >= 20 && ly < 40) {
            return 0; // FIGHT / BALL
        }
        if (ly >= 40 && ly < 61) {
            return 2; // POKeMON / MUD
        }
        if (ly >= 61 && ly < 82) {
            return 1; // BAG / BAIT
        }
        if (ly >= 82 && ly < 103) {
            return 3; // RUN / CANCEL
        }
        return -1;
    }

    return -1;
}

// Map a main-touch click (DS coords) to a touch-array button index for
// the current menu, mirroring the bottom screen's button layout.
static int HudTouchButtonIndex(BattleSubscreen *btlSubscreen, int x, int y)
{
    int menu = btlSubscreen->activeMenuConfigIndex;
    int col, row;

    if (SIM_Battle3D_IsEnabled()) {
        return BdspHudTouchButtonIndex(btlSubscreen, x, y);
    }

    if (BattleHud_IsWidePixelMode()) {
        return WideHudTouchButtonIndex(btlSubscreen, x, y);
    }

    // Strip at tiles (0,11,32,7) -> pixels y 88..144, full width.
    if (y < HUD_TILE_Y * 8 || y >= (HUD_TILE_Y + HUD_TILE_H) * 8) {
        return -1;
    }
    col = x < 128 ? 0 : 1;
    row = y < (HUD_TILE_Y + 3) * 8 ? 0 : 1;

    if (menu >= 13 && menu <= 17) {
        return row; // yes=0, no=1
    }
    if (menu == HUD_MENU_MOVE) {
        if (y >= (HUD_TILE_Y + 5) * 8) {
            // Mega strip (or Back on the right half, mirroring bottom bar)
            return x < 128 ? 5 : 0;
        }
        return 1 + row * 2 + col; // moves 1..4 at touch indices 1..4
    }
    if (menu == HUD_MENU_TARGET) {
        static const u8 layout[2][2] = { { 3, 1 }, { 0, 2 } };
        if (y >= (HUD_TILE_Y + 5) * 8) {
            return 4; // cancel strip area
        }
        return layout[row][col];
    }
    if (menu >= 1 && menu <= 10) {
        static const u8 layout[2][2] = { { 0, 3 }, { 1, 2 } };
        return layout[row][col]; // FIGHT, POKEMON / BAG, RUN
    }
    return -1;
}

int BattleHud_Update(BattleSubscreen *btlSubscreen)
{
    int menu, cx, cy, touchX, touchY;
    BOOL bdsp3d;
    BOOL widePixel;

    if (!BattleHud_IsEnabled() || btlSubscreen == NULL) {
        if (btlSubscreen != NULL) {
            HudHideInternal(btlSubscreen);
        }
        return -1;
    }

    menu = btlSubscreen->activeMenuConfigIndex;
    if (menu == HUD_MENU_IDLE || menu < 0) {
        HudHideInternal(btlSubscreen);
        return -1;
    }

    bdsp3d = SIM_Battle3D_IsEnabled();
    widePixel = BattleHud_IsWidePixelMode();

    // Wide layout: HUD is up on the top screen, bottom panel not needed.
    if (SIM_Wide_IsWideLayout()) {
        SIM_Wide_SetBattleTouchNeeded(0);
    }
    SIM_Wide_SetMainTouchEnabled(1);

    // Wild quick-ball shortcut: X opens Bag immediately in BDSP corner HUD.
    if (bdsp3d && !btlSubscreen->isPanelSliding
        && BdspHudHasWildQuickBall(btlSubscreen, menu)
        && (gSystem.pressedKeys & PAD_BUTTON_X)) {
        return 1;
    }

    // Main-screen click: confirm like a bottom-screen touch.
    if (SIM_Wide_PollMainTouch(&touchX, &touchY)) {
        int button = HudTouchButtonIndex(btlSubscreen, touchX, touchY);
        if (button >= 0) {
            return button;
        }
    }

    HudLiftHealthboxes(btlSubscreen, TRUE);
    cx = btlSubscreen->cursor.x;
    cy = btlSubscreen->cursor.y;

    if (sHud.windowAdded && sHud.wideModeWindow == widePixel && sHud.bdspModeWindow == bdsp3d
        && menu == sHud.lastMenu && cx == sHud.lastCursorX && cy == sHud.lastCursorY
        && menu != HUD_MENU_MOVE) {
        if (bdsp3d) {
            BdspHudKeepTilemapIntact(btlSubscreen, menu);
        } else if (widePixel) {
            WideHudKeepTilemapIntact(btlSubscreen);
        } else {
            HudLiftHealthboxes(btlSubscreen, TRUE);
        }
        return -1;
    }
    if (menu == HUD_MENU_MOVE && sHud.windowAdded && sHud.wideModeWindow == widePixel && sHud.bdspModeWindow == bdsp3d
        && menu == sHud.lastMenu && cx == sHud.lastCursorX && cy == sHud.lastCursorY) {
        MoveSelectData *md = &btlSubscreen->activeMenuData.moveData;
        BattleContext *ctx = BattleSystem_GetBattleContext(btlSubscreen->battleSys);
        int battler = BattleSystem_GetBattlerOfType(btlSubscreen->battleSys, btlSubscreen->battlerType);
        int on = md->megaEvolutionAvailable ? (ctx->megaEvolutionTriggered[battler] ? 1 : 0) : -1;
        BOOL same = (on == sHud.lastMega);
        int i;
        for (i = 0; i < 4; i++) {
            if (md->currPP[i] != sHud.lastMovePP[i]) {
                same = FALSE;
            }
        }
        if (same) {
            if (bdsp3d) {
                BdspHudKeepTilemapIntact(btlSubscreen, menu);
            } else if (widePixel) {
                WideHudKeepTilemapIntact(btlSubscreen);
            } else {
                HudLiftHealthboxes(btlSubscreen, TRUE);
            }
            return -1;
        }
    }

    if (bdsp3d) {
        BdspHudEnsureWindow(btlSubscreen, menu);

        if (menu == HUD_MENU_MOVE) {
            BdspHudDrawMoves(btlSubscreen);
        } else if (menu == HUD_MENU_TARGET) {
            BdspHudDrawTarget(btlSubscreen);
        } else if (menu >= 13 && menu <= 17) {
            WideHudDrawYesNo(btlSubscreen);
        } else {
            BdspHudDrawAction(btlSubscreen);
        }
    } else if (widePixel) {
        WideHudEnsureWindow(btlSubscreen, menu);

        if (menu == HUD_MENU_MOVE) {
            WideHudDrawMoves(btlSubscreen);
        } else if (menu == HUD_MENU_TARGET) {
            WideHudDrawTarget(btlSubscreen);
        } else if (menu >= 13 && menu <= 17) {
            WideHudDrawYesNo(btlSubscreen);
        } else {
            WideHudDrawAction(btlSubscreen);
        }
    } else {
        HudEnsureWindow(btlSubscreen);
        HudLiftHealthboxes(btlSubscreen, TRUE);

        Window_FillTilemap(&sHud.window, 0xFF);
        // Panel background: dark fill over the whole strip.
        HudFillRect(btlSubscreen, 1, 0, 0, HUD_TILE_W, HUD_TILE_H);

        if (menu == HUD_MENU_MOVE) {
            HudDrawMoves(btlSubscreen);
        } else if (menu == HUD_MENU_TARGET) {
            HudDrawTarget(btlSubscreen);
        } else if (menu >= 13 && menu <= 17) {
            HudDrawYesNo(btlSubscreen);
        } else {
            HudDrawAction(btlSubscreen);
        }
    }

    Window_ScheduleCopyToVRAM(&sHud.window);
    Bg_ScheduleTilemapTransfer(BattleSystem_GetBgConfig(btlSubscreen->battleSys), BG_LAYER_MAIN_1);
    sHud.lastMenu = menu;
    sHud.lastCursorX = cx;
    sHud.lastCursorY = cy;
    return -1;
}

BOOL BattleHud_IsWindowVisible(void)
{
    return sHud.windowAdded;
}

int BattleHud_TopTouchButton(BattleSubscreen *btlSubscreen, int x, int y)
{
    if (!BattleHud_IsEnabled() || btlSubscreen == NULL) {
        return -1;
    }
    return HudTouchButtonIndex(btlSubscreen, x, y);
}
