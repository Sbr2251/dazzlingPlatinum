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
#include "battle/battle_bdsp_dialogue.h"
#include "battle/battle_bdsp_overlay.h"

#include <nitro.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef SDK_PORT
#include <simulator/sim_headless.h>
#endif

#include "constants/battle/battle_script.h"
#include "constants/battle/condition.h"
#include "constants/battle/moves.h"
#include "constants/charcode.h"
#include "constants/graphics.h"
#include "constants/items.h"
#include "generated/pokemon_types.h"

#include "battle/battle_context.h"
#include "battle/battle_display.h"
#include "battle/battle_lib.h"
#include "battle/battle_system.h"
#include "battle/healthbox.h"
#include "port/sim_battle3d.h"
#include "port/sim_config_prj.h"
#include "port/sim_hud_hd.h"
#include "port/sim_wide.h"

#include "bag.h"
#include "bg_window.h"
#include "message.h"
#include "message_util.h"
#include "move_table.h"
#include "palette.h"
#include "party.h"
#include "pokemon.h"
#include "render_window.h"
#include "sound_playback.h"
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
    BattleSubscreen *activeSubscreen;
    u32 lastDumpHash;
    BOOL hasDumped;
    int infoCardMode; // 0 = closed, 1 = move detail, 2 = battle status
    int infoCardMenu; // activeMenuConfigIndex when infoCardMode opened
    BOOL lastConfirmWasKey;
    u16 cachedMoveInfoId;
    char cachedMoveName[SIM_HUDHD_NAME_LEN];
    char cachedMoveTypeName[24];
    char cachedMoveDesc[160];
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

BOOL BattleHud_IsHdMode(void)
{
#ifdef SDK_PORT
    const char *env;

    if (!SIM_Wide_IsWideLayout() || !BattleHud_IsEnabled()) {
        return FALSE;
    }
    env = getenv("SIM_FX_HUDHD");
    if (!GameHudHD_IsSupported()) {
        if (env != NULL && env[0] == '1') {
            return TRUE;
        }
        return FALSE;
    }
    if (env != NULL && env[0] != '\0') {
        return env[0] != '0' ? TRUE : FALSE;
    }
    if (SIM_Headless_Enabled()) {
        return FALSE;
    }
    return SIM_Config_prj_GetConfig()->battleHudStyleHd ? TRUE : FALSE;
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
    sHud.activeSubscreen = NULL;
    sHud.infoCardMode = 0;
    sHud.infoCardMenu = -1;
    sHud.lastConfirmWasKey = FALSE;
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
    sHud.activeSubscreen = NULL;
    sHud.infoCardMode = 0;
    sHud.infoCardMenu = -1;
    sHud.lastConfirmWasKey = FALSE;
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

// --- HD Battle HUD (BDSP parity, sim_hud_hd.h) ---

static void HudStringToUtf8(const String *str, char *out, int outSize)
{
    int pos = 0;
    u32 i;
    const charcode_t *data;

    if (out == NULL || outSize <= 0) {
        return;
    }
    out[0] = '\0';
    if (str == NULL) {
        return;
    }

    data = String_GetData(str);
    if (data == NULL) {
        return;
    }

    for (i = 0; i < 512 && pos < outSize - 1; i++) {
        charcode_t c = data[i];
        if (c == CHAR_EOS) {
            break;
        }
        if (c == CHAR_FORMAT_ARG) {
            // Skip format control sequence (tag, id, argc, args...)
            if (i + 2 < 512) {
                u16 argc = data[i + 2];
                i += 2 + argc;
            }
            continue;
        }
        if (c == CHAR_CR || c == CHAR_CONTROL_CLEAR || c == CHAR_CONTROL_SCROLL) {
            if (pos > 0 && out[pos - 1] != ' ') {
                out[pos++] = ' ';
            }
            continue;
        }
        if (c == CHAR_CONTROL_SET_COLOR || c == CHAR_CONTROL_SET_SIZE || c == CHAR_CONTROL_MOVE) {
            i++;
            continue;
        }
        if (c >= CHAR_0 && c <= CHAR_9) {
            out[pos++] = (char)('0' + (c - CHAR_0));
        } else if (c >= CHAR_A && c <= CHAR_Z) {
            out[pos++] = (char)('A' + (c - CHAR_A));
        } else if (c >= CHAR_a && c <= CHAR_z) {
            out[pos++] = (char)('a' + (c - CHAR_a));
        } else if (c == CHAR_SPACE || c == CHAR_WIDE_SPACE || c == CHAR_NUM_SPACE
            || (c >= CHAR_SPACE_1px && c <= CHAR_SPACE_16px)) {
            if (pos == 0 || out[pos - 1] != ' ') {
                out[pos++] = ' ';
            }
        } else if (c == CHAR_EXCLAMATION) {
            out[pos++] = '!';
        } else if (c == CHAR_QUESTION) {
            out[pos++] = '?';
        } else if (c == CHAR_PERIOD) {
            out[pos++] = '.';
        } else if (c == CHAR_COMMA) {
            out[pos++] = ',';
        } else if (c == CHAR_SINGLE_QUOTE_OPEN || c == CHAR_SINGLE_QUOTE_CLOSE) {
            out[pos++] = '\'';
        } else if (c == CHAR_DOUBLE_QUOTE_OPEN || c == CHAR_DOUBLE_QUOTE_CLOSE || c == CHAR_DOUBLE_QUOTE_CLOSE_INVERTED) {
            out[pos++] = '"';
        } else if (c == CHAR_MINUS) {
            out[pos++] = '-';
        } else if (c == CHAR_COLON) {
            out[pos++] = ':';
        } else if (c == CHAR_SEMICOLON) {
            out[pos++] = ';';
        } else if (c == CHAR_SLASH) {
            out[pos++] = '/';
        } else if (c == CHAR_PAREN_OPEN) {
            out[pos++] = '(';
        } else if (c == CHAR_PAREN_CLOSE) {
            out[pos++] = ')';
        } else if (c == CHAR_PLUS) {
            out[pos++] = '+';
        } else if (c == CHAR_STAR || c == CHAR_ASTERISK) {
            out[pos++] = '*';
        } else if (c == CHAR_PERCENT) {
            out[pos++] = '%';
        } else if (c == CHAR_AMPERSAND) {
            out[pos++] = '&';
        } else if (c == CHAR_TILDE) {
            out[pos++] = '~';
        } else if (c == CHAR_HASH) {
            out[pos++] = '#';
        } else if (c == CHAR_EQUALS) {
            out[pos++] = '=';
        } else if (c == CHAR_AT_SIGN) {
            out[pos++] = '@';
        } else if (c == CHAR_UNDERSCORE || c == CHAR_WIDE_UNDERSCORE) {
            out[pos++] = '_';
        } else if (c == CHAR_ELLIPSIS) {
            if (pos + 3 < outSize) {
                out[pos++] = '.';
                out[pos++] = '.';
                out[pos++] = '.';
            }
        } else if (c == CHAR_MALE) {
            if (pos + 3 < outSize) {
                out[pos++] = (char)0xE2;
                out[pos++] = (char)0x99;
                out[pos++] = (char)0x82;
            }
        } else if (c == CHAR_FEMALE) {
            if (pos + 3 < outSize) {
                out[pos++] = (char)0xE2;
                out[pos++] = (char)0x99;
                out[pos++] = (char)0x80;
            }
        } else if (c == CHAR_e_ACUTE || c == CHAR_e_SUPERSCRIPT) {
            if (pos + 2 < outSize) {
                out[pos++] = (char)0xC3;
                out[pos++] = (char)0xA9;
            }
        } else {
            out[pos++] = '?';
        }
    }
    while (pos > 0 && out[pos - 1] == ' ') {
        pos--;
    }
    out[pos] = '\0';
}

static int HdHudEffectiveness(BattleSystem *battleSys, BattleSubscreen *btlSubscreen, u16 moveID)
{
    u32 battleType;
    BattleContext *ctx;
    int attacker, defender;
    u32 moveClass;
    u32 moveStatusMask = 0;

    if (battleSys == NULL || btlSubscreen == NULL || moveID == 0) {
        return SIM_HUDHD_EFF_UNKNOWN;
    }
    battleType = BattleSystem_GetBattleType(battleSys);
    if (battleType & BATTLE_TYPE_DOUBLES) {
        return SIM_HUDHD_EFF_UNKNOWN;
    }
    moveClass = MoveTable_LoadParam(moveID, MOVEATTRIBUTE_CLASS);
    if (moveClass == CLASS_STATUS) {
        return SIM_HUDHD_EFF_UNKNOWN;
    }

    ctx = BattleSystem_GetBattleContext(battleSys);
    if (ctx == NULL) {
        return SIM_HUDHD_EFF_UNKNOWN;
    }
    attacker = BattleSystem_GetBattlerOfType(battleSys, btlSubscreen->battlerType);
    defender = BattleSystem_GetBattlerOfType(battleSys, BATTLER_TYPE_SOLO_ENEMY);
    if (attacker < 0 || attacker >= MAX_BATTLERS || defender < 0 || defender >= MAX_BATTLERS) {
        return SIM_HUDHD_EFF_UNKNOWN;
    }

    BattleSystem_ApplyTypeChart(battleSys, ctx, moveID, 0, attacker, defender, 100, &moveStatusMask);

    if (moveStatusMask & (MOVE_STATUS_INEFFECTIVE | MOVE_STATUS_LEVITATED | MOVE_STATUS_MAGNET_RISE | MOVE_STATUS_WONDER_GUARD)) {
        return SIM_HUDHD_EFF_NONE;
    }
    if (moveStatusMask & MOVE_STATUS_SUPER_EFFECTIVE) {
        return SIM_HUDHD_EFF_SUPER;
    }
    if (moveStatusMask & MOVE_STATUS_NOT_VERY_EFFECTIVE) {
        return SIM_HUDHD_EFF_NOT_VERY;
    }
    return SIM_HUDHD_EFF_NORMAL;
}

static int HdHudBallPriority(u16 item)
{
    switch (item) {
    case ITEM_ULTRA_BALL:
        return 50;
    case ITEM_QUICK_BALL:
    case ITEM_DUSK_BALL:
    case ITEM_TIMER_BALL:
    case ITEM_REPEAT_BALL:
    case ITEM_NET_BALL:
    case ITEM_DIVE_BALL:
    case ITEM_NEST_BALL:
    case ITEM_HEAL_BALL:
    case ITEM_LUXURY_BALL:
    case ITEM_PREMIER_BALL:
    case ITEM_CHERISH_BALL:
        return 40;
    case ITEM_GREAT_BALL:
        return 30;
    case ITEM_POKE_BALL:
        return 20;
    case ITEM_MASTER_BALL:
        return 10; // only pick Master Ball automatically if no other balls exist
    default:
        return 15;
    }
}

static void HdHudQuickBallInfo(BattleSystem *battleSys, u16 *outItem, int *outCount)
{
    Bag *bag;
    BagCursor *bagCursor;
    u16 bestItem = ITEM_NONE;
    int bestQty = 0;
    int bestPrio = -1;
    u16 slot;

    if (outItem != NULL) {
        *outItem = ITEM_NONE;
    }
    if (outCount != NULL) {
        *outCount = 0;
    }
    if (battleSys == NULL) {
        return;
    }

    bag = BattleSystem_GetBag(battleSys);
    if (bag == NULL) {
        return;
    }

    // Prefer the last-used Poké Ball from this battle if any remain in Bag.
    bagCursor = BattleSystem_GetBagCursor(battleSys);
    if (bagCursor != NULL) {
        u16 lastItem = BagCursor_GetLastUsedBattleItem(bagCursor);
        u16 lastCat = BagCursor_GetLastUsedBattleItemCategory(bagCursor);
        if (lastItem != ITEM_NONE && lastCat == ITEM_BATTLE_CATEGORY_POKE_BALLS) {
            for (slot = 0; slot < POKEBALL_POCKET_SIZE; slot++) {
                BagItem *bi = Bag_GetItemSlot(bag, POCKET_BALLS, slot);
                if (bi != NULL && bi->item == lastItem && bi->quantity > 0) {
                    if (outItem != NULL) {
                        *outItem = bi->item;
                    }
                    if (outCount != NULL) {
                        *outCount = (int)bi->quantity;
                    }
                    return;
                }
            }
        }
    }

    // Otherwise pick the best available Poké Ball in the Balls pocket.
    for (slot = 0; slot < POKEBALL_POCKET_SIZE; slot++) {
        BagItem *bi = Bag_GetItemSlot(bag, POCKET_BALLS, slot);
        if (bi == NULL || bi->item == ITEM_NONE || bi->quantity == 0) {
            continue;
        }
        {
            int prio = HdHudBallPriority(bi->item);
            if (prio > bestPrio) {
                bestPrio = prio;
                bestItem = bi->item;
                bestQty = (int)bi->quantity;
            }
        }
    }

    if (outItem != NULL) {
        *outItem = bestItem;
    }
    if (outCount != NULL) {
        *outCount = bestQty;
    }
}

static void HdHudPrepareQuickBallBag(BattleSubscreen *btlSubscreen)
{
    BagCursor *bagCursor;

    sHud.infoCardMode = 0;
    sHud.infoCardMenu = -1;
    if (btlSubscreen == NULL || btlSubscreen->battleSys == NULL) {
        return;
    }
    bagCursor = BattleSystem_GetBagCursor(btlSubscreen->battleSys);
    if (bagCursor != NULL) {
        // Pre-focus the Poké Balls pocket in Battle Bag without altering Bag
        // inventory or overwriting lastUsedItem.
        BagCursor_SetBattleCurrentCategory(bagCursor, ITEM_BATTLE_CATEGORY_POKE_BALLS);
    }
}

static void HdHudTitleCaseAscii(char *s)
{
    BOOL startWord = TRUE;
    int i;

    if (s == NULL) {
        return;
    }
    for (i = 0; s[i] != '\0'; i++) {
        char c = s[i];
        if (c >= 'A' && c <= 'Z') {
            if (!startWord) {
                s[i] = (char)(c - 'A' + 'a');
            }
            startWord = FALSE;
        } else if (c >= 'a' && c <= 'z') {
            if (startWord) {
                s[i] = (char)(c - 'a' + 'A');
            }
            startWord = FALSE;
        } else {
            startWord = (c == ' ' || c == '-');
        }
    }
}

static void HdHudLoadMoveInfoCached(u16 moveID)
{
    if (moveID == 0 || moveID == sHud.cachedMoveInfoId) {
        return;
    }
    {
        int moveType = (int)MoveTable_LoadParam(moveID, MOVEATTRIBUTE_TYPE);
        String *nameStr = MessageUtil_MoveName(moveID, HEAP_ID_BATTLE);
        MessageLoader *typeLoader = MessageLoader_Init(MSG_LOADER_LOAD_ON_DEMAND,
            NARC_INDEX_MSGDATA__PL_MSG, TEXT_BANK_POKEMON_TYPE_NAMES, HEAP_ID_BATTLE);
        String *typeStr = MessageLoader_GetNewString(typeLoader, (u32)moveType);
        MessageLoader *descLoader = MessageLoader_Init(MSG_LOADER_LOAD_ON_DEMAND,
            NARC_INDEX_MSGDATA__PL_MSG, TEXT_BANK_MOVE_DESCRIPTIONS, HEAP_ID_BATTLE);
        String *descStr = MessageLoader_GetNewString(descLoader, (u32)moveID);

        HudStringToUtf8(nameStr, sHud.cachedMoveName, sizeof(sHud.cachedMoveName));
        HudStringToUtf8(typeStr, sHud.cachedMoveTypeName, sizeof(sHud.cachedMoveTypeName));
        HdHudTitleCaseAscii(sHud.cachedMoveTypeName);
        HudStringToUtf8(descStr, sHud.cachedMoveDesc, sizeof(sHud.cachedMoveDesc));

        String_Free(nameStr);
        String_Free(typeStr);
        String_Free(descStr);
        MessageLoader_Free(typeLoader);
        MessageLoader_Free(descLoader);
        sHud.cachedMoveInfoId = moveID;
    }
}

static void HdHudFillMoveInfoCard(BattleSubscreen *btlSubscreen, SIM_HudHD_InfoCard *card)
{
    MoveSelectData *moveData;
    int cx, cy, slot, i;
    u16 moveID;
    u32 moveClass;
    int power, accuracy;
    const char *catLabel;
    char powBuf[8];
    char accBuf[8];

    if (btlSubscreen == NULL || card == NULL) {
        return;
    }
    moveData = &btlSubscreen->activeMenuData.moveData;
    cx = btlSubscreen->cursor.x;
    cy = btlSubscreen->cursor.y;

    if (cy >= 0 && cy < 2 && cx >= 0 && cx < 2) {
        int focusIdx = cy * 2 + cx;
        if (moveData->moveIDs[focusIdx] != 0) {
            sHud.lastMoveSlot = focusIdx;
        }
    }
    slot = sHud.lastMoveSlot;
    if (slot < 0 || slot >= 4 || moveData->moveIDs[slot] == 0) {
        slot = -1;
        for (i = 0; i < 4; i++) {
            if (moveData->moveIDs[i] != 0) {
                slot = i;
                break;
            }
        }
    }
    if (slot < 0) {
        return;
    }
    sHud.lastMoveSlot = slot;
    moveID = moveData->moveIDs[slot];

    HdHudLoadMoveInfoCached(moveID);

    moveClass = MoveTable_LoadParam(moveID, MOVEATTRIBUTE_CLASS);
    power = (int)MoveTable_LoadParam(moveID, MOVEATTRIBUTE_POWER);
    accuracy = (int)MoveTable_LoadParam(moveID, MOVEATTRIBUTE_ACCURACY);

    card->visible = 1;
    card->kind = 1;
    card->rect = (SIM_HudHD_Rect){ 8.0f, 28.0f, 162.0f, 84.0f };
    card->type = (int)MoveTable_LoadParam(moveID, MOVEATTRIBUTE_TYPE);
    if (moveClass == CLASS_PHYSICAL) {
        card->category = SIM_HUDHD_CAT_PHYSICAL;
        catLabel = "Physical";
    } else if (moveClass == CLASS_SPECIAL) {
        card->category = SIM_HUDHD_CAT_SPECIAL;
        catLabel = "Special";
    } else {
        card->category = SIM_HUDHD_CAT_STATUS;
        catLabel = "Status";
    }

    if (power > 0) {
        snprintf(powBuf, sizeof(powBuf), "%d", power);
    } else {
        snprintf(powBuf, sizeof(powBuf), "--");
    }
    if (accuracy > 0) {
        snprintf(accBuf, sizeof(accBuf), "%d", accuracy);
    } else {
        snprintf(accBuf, sizeof(accBuf), "--");
    }

    snprintf(card->title, sizeof(card->title), "%s", sHud.cachedMoveName);
    snprintf(card->line1, sizeof(card->line1), "Power: %s   Accuracy: %s", powBuf, accBuf);
    snprintf(card->line2, sizeof(card->line2), "%s  |  %s", catLabel, sHud.cachedMoveTypeName);
    snprintf(card->desc, sizeof(card->desc), "%s", sHud.cachedMoveDesc);
}

static void HdHudAppendText(char *dst, int dstSize, const char *sep, const char *text)
{
    int len;

    if (dst == NULL || dstSize <= 1 || text == NULL || text[0] == '\0') {
        return;
    }
    len = (int)strlen(dst);
    if (len >= dstSize - 1) {
        return;
    }
    if (len > 0 && sep != NULL && sep[0] != '\0') {
        snprintf(dst + len, (size_t)(dstSize - len), "%s%s", sep, text);
    } else {
        snprintf(dst + len, (size_t)(dstSize - len), "%s", text);
    }
}

static void HdHudAppendBattlerStats(BattleSystem *battleSys, BattleContext *ctx, int battler,
    char *dst, int dstSize)
{
    static const char *const sStatNames[NUM_BOOSTABLE_STATS] = {
        "HP", "Atk", "Def", "Spe", "SpA", "SpD", "Acc", "Eva"
    };
    const BattleMon *bmon;
    Pokemon *partyMon;
    char nameBuf[SIM_HUDHD_NAME_LEN];
    char entryBuf[96];
    BOOL anyBoost = FALSE;
    int s;

    if (ctx == NULL || battler < 0 || battler >= MAX_BATTLERS) {
        return;
    }
    bmon = &ctx->battleMons[battler];
    if (bmon->species == 0 || bmon->curHP <= 0) {
        return;
    }

    nameBuf[0] = '\0';
    partyMon = BattleSystem_GetPartyPokemon(battleSys, battler, ctx->selectedPartySlot[battler]);
    if (partyMon != NULL) {
        String *nick = String_Init(MON_NAME_LEN + 4, HEAP_ID_BATTLE);
        Pokemon_GetValue(partyMon, MON_DATA_NICKNAME_STRING, nick);
        HudStringToUtf8(nick, nameBuf, sizeof(nameBuf));
        String_Free(nick);
    }
    if (nameBuf[0] == '\0') {
        snprintf(nameBuf, sizeof(nameBuf), (battler % 2 == 0) ? "Ally" : "Foe");
    }

    snprintf(entryBuf, sizeof(entryBuf), "%s: ", nameBuf);
    for (s = BATTLE_STAT_ATTACK; s < NUM_BOOSTABLE_STATS; s++) {
        int delta = (int)bmon->statBoosts[s] - DEFAULT_STAT_STAGE;
        if (delta != 0) {
            char part[16];
            snprintf(part, sizeof(part), "%s %+d", sStatNames[s], delta);
            HdHudAppendText(entryBuf, (int)sizeof(entryBuf), anyBoost ? ", " : "", part);
            anyBoost = TRUE;
        }
    }
    if (!anyBoost) {
        HdHudAppendText(entryBuf, (int)sizeof(entryBuf), "", "No stat changes");
    }

    HdHudAppendText(dst, dstSize, "  |  ", entryBuf);
}

static void HdHudAppendSideEffects(const BattleContext *ctx, int side, const char *sideLabel,
    char *dst, int dstSize)
{
    u32 mask;
    const SideConditions *sc;
    char sideBuf[96];
    BOOL any = FALSE;

    if (ctx == NULL || side < 0 || side >= NUM_BATTLE_SIDES) {
        return;
    }
    mask = ctx->sideConditionsMask[side];
    sc = &ctx->sideConditions[side];
    sideBuf[0] = '\0';

    if (mask & SIDE_CONDITION_REFLECT) {
        char tmp[24];
        snprintf(tmp, sizeof(tmp), "Reflect (%u)", (unsigned)sc->reflectTurns);
        HdHudAppendText(sideBuf, (int)sizeof(sideBuf), any ? ", " : "", tmp);
        any = TRUE;
    }
    if (mask & SIDE_CONDITION_LIGHT_SCREEN) {
        char tmp[28];
        snprintf(tmp, sizeof(tmp), "Light Screen (%u)", (unsigned)sc->lightScreenTurns);
        HdHudAppendText(sideBuf, (int)sizeof(sideBuf), any ? ", " : "", tmp);
        any = TRUE;
    }
    if (mask & SIDE_CONDITION_TAILWIND) {
        HdHudAppendText(sideBuf, (int)sizeof(sideBuf), any ? ", " : "", "Tailwind");
        any = TRUE;
    }
    if (mask & SIDE_CONDITION_SAFEGUARD) {
        HdHudAppendText(sideBuf, (int)sizeof(sideBuf), any ? ", " : "", "Safeguard");
        any = TRUE;
    }
    if (mask & SIDE_CONDITION_MIST) {
        HdHudAppendText(sideBuf, (int)sizeof(sideBuf), any ? ", " : "", "Mist");
        any = TRUE;
    }
    if (mask & SIDE_CONDITION_STEALTH_ROCK) {
        HdHudAppendText(sideBuf, (int)sizeof(sideBuf), any ? ", " : "", "Stealth Rock");
        any = TRUE;
    }
    if (mask & SIDE_CONDITION_SPIKES) {
        char tmp[20];
        snprintf(tmp, sizeof(tmp), "Spikes x%u", (unsigned)sc->spikesLayers);
        HdHudAppendText(sideBuf, (int)sizeof(sideBuf), any ? ", " : "", tmp);
        any = TRUE;
    }
    if (mask & SIDE_CONDITION_TOXIC_SPIKES) {
        char tmp[24];
        snprintf(tmp, sizeof(tmp), "Toxic Spikes x%u", (unsigned)sc->toxicSpikesLayers);
        HdHudAppendText(sideBuf, (int)sizeof(sideBuf), any ? ", " : "", tmp);
        any = TRUE;
    }

    if (any) {
        char labeled[112];
        snprintf(labeled, sizeof(labeled), "%s: %s", sideLabel, sideBuf);
        HdHudAppendText(dst, dstSize, "  |  ", labeled);
    }
}

static void HdHudFillBattleStatusCard(BattleSystem *battleSys, SIM_HudHD_InfoCard *card)
{
    BattleContext *ctx;
    u32 fieldMask;
    int maxBattlers, i;

    if (battleSys == NULL || card == NULL) {
        return;
    }
    ctx = BattleSystem_GetBattleContext(battleSys);
    if (ctx == NULL) {
        return;
    }

    card->visible = 1;
    card->kind = 2;
    card->rect = (SIM_HudHD_Rect){ 8.0f, 28.0f, 220.0f, 84.0f };
    card->type = 0;
    card->category = 0;
    snprintf(card->title, sizeof(card->title), "Battle Status");

    // Line 1: Weather & active field conditions.
    fieldMask = ctx->fieldConditionsMask;
    card->line1[0] = '\0';
    if (fieldMask & FIELD_CONDITION_RAINING) {
        if ((fieldMask & FIELD_CONDITION_RAINING_TEMP) && ctx->fieldConditions.weatherTurns > 0) {
            snprintf(card->line1, sizeof(card->line1), "Weather: Rain (%u)", (unsigned)ctx->fieldConditions.weatherTurns);
        } else {
            snprintf(card->line1, sizeof(card->line1), "Weather: Rain");
        }
    } else if (fieldMask & FIELD_CONDITION_SUNNY) {
        if ((fieldMask & FIELD_CONDITION_SUNNY_TEMP) && ctx->fieldConditions.weatherTurns > 0) {
            snprintf(card->line1, sizeof(card->line1), "Weather: Harsh Sun (%u)", (unsigned)ctx->fieldConditions.weatherTurns);
        } else {
            snprintf(card->line1, sizeof(card->line1), "Weather: Harsh Sun");
        }
    } else if (fieldMask & FIELD_CONDITION_SANDSTORM) {
        if ((fieldMask & FIELD_CONDITION_SANDSTORM_TEMP) && ctx->fieldConditions.weatherTurns > 0) {
            snprintf(card->line1, sizeof(card->line1), "Weather: Sandstorm (%u)", (unsigned)ctx->fieldConditions.weatherTurns);
        } else {
            snprintf(card->line1, sizeof(card->line1), "Weather: Sandstorm");
        }
    } else if (fieldMask & FIELD_CONDITION_HAILING) {
        if ((fieldMask & FIELD_CONDITION_HAILING_TEMP) && ctx->fieldConditions.weatherTurns > 0) {
            snprintf(card->line1, sizeof(card->line1), "Weather: Hail (%u)", (unsigned)ctx->fieldConditions.weatherTurns);
        } else {
            snprintf(card->line1, sizeof(card->line1), "Weather: Hail");
        }
    } else if (fieldMask & FIELD_CONDITION_DEEP_FOG) {
        snprintf(card->line1, sizeof(card->line1), "Weather: Fog");
    } else {
        snprintf(card->line1, sizeof(card->line1), "Weather: Clear");
    }

    if (fieldMask & FIELD_CONDITION_TRICK_ROOM) {
        unsigned trTurns = (unsigned)((fieldMask & FIELD_CONDITION_TRICK_ROOM) >> FIELD_CONDITION_TRICK_ROOM_SHIFT);
        char trBuf[24];
        snprintf(trBuf, sizeof(trBuf), "Trick Room (%u)", trTurns);
        HdHudAppendText(card->line1, (int)sizeof(card->line1), "  |  ", trBuf);
    }
    if (fieldMask & FIELD_CONDITION_GRAVITY) {
        unsigned grTurns = (unsigned)((fieldMask & FIELD_CONDITION_GRAVITY) >> FIELD_CONDITION_GRAVITY_SHIFT);
        char grBuf[24];
        snprintf(grBuf, sizeof(grBuf), "Gravity (%u)", grTurns);
        HdHudAppendText(card->line1, (int)sizeof(card->line1), "  |  ", grBuf);
    }

    // Line 2: Player active battler(s) stat stage modifiers.
    // Desc: Enemy active battler(s) stat stage modifiers + side conditions.
    card->line2[0] = '\0';
    card->desc[0] = '\0';
    maxBattlers = BattleSystem_GetMaxBattlers(battleSys);
    if (maxBattlers > MAX_BATTLERS) {
        maxBattlers = MAX_BATTLERS;
    }
    for (i = 0; i < maxBattlers; i++) {
        if (i % 2 == 0) {
            HdHudAppendBattlerStats(battleSys, ctx, i, card->line2, (int)sizeof(card->line2));
        } else {
            HdHudAppendBattlerStats(battleSys, ctx, i, card->desc, (int)sizeof(card->desc));
        }
    }
    HdHudAppendSideEffects(ctx, BATTLE_SIDE_PLAYER, "Your side", card->desc, (int)sizeof(card->desc));
    HdHudAppendSideEffects(ctx, BATTLE_SIDE_ENEMY, "Foe side", card->desc, (int)sizeof(card->desc));
    if (card->line2[0] == '\0') {
        snprintf(card->line2, sizeof(card->line2), "No active stat changes");
    }
    if (card->desc[0] == '\0') {
        snprintf(card->desc, sizeof(card->desc), "Field normal");
    }
}

BOOL BattleHud_HandleOverlayKeys(BattleSubscreen *btlSubscreen)
{
    int menu;

    if (!BattleHud_IsHdMode() || btlSubscreen == NULL || btlSubscreen->isPanelSliding) {
        return FALSE;
    }
    menu = btlSubscreen->activeMenuConfigIndex;
    if (menu == HUD_MENU_IDLE || menu < 0) {
        sHud.infoCardMode = 0;
        sHud.infoCardMenu = -1;
        return FALSE;
    }
    if (sHud.infoCardMode != 0 && menu != sHud.infoCardMenu) {
        sHud.infoCardMode = 0;
        sHud.infoCardMenu = -1;
    }

    if (menu == HUD_MENU_MOVE) {
        if (gSystem.pressedKeys & PAD_BUTTON_Y) {
            sHud.infoCardMode = (sHud.infoCardMode == 1) ? 0 : 1;
            sHud.infoCardMenu = menu;
            Sound_PlayEffect(SE_CONFIRM_sseq_3);
            return TRUE;
        }
        if (sHud.infoCardMode != 0 && (gSystem.pressedKeys & PAD_BUTTON_B)) {
            sHud.infoCardMode = 0;
            sHud.infoCardMenu = -1;
            Sound_PlayEffect(SE_CONFIRM_sseq_3);
            return TRUE;
        }
    } else if (menu >= 1 && menu <= 10) {
        if (gSystem.pressedKeys & PAD_BUTTON_Y) {
            sHud.infoCardMode = (sHud.infoCardMode == 2) ? 0 : 2;
            sHud.infoCardMenu = menu;
            Sound_PlayEffect(SE_CONFIRM_sseq_3);
            return TRUE;
        }
        if (sHud.infoCardMode != 0 && (gSystem.pressedKeys & PAD_BUTTON_B)) {
            sHud.infoCardMode = 0;
            sHud.infoCardMenu = -1;
            Sound_PlayEffect(SE_CONFIRM_sseq_3);
            return TRUE;
        }
    } else if (sHud.infoCardMode != 0 && (gSystem.pressedKeys & (PAD_BUTTON_Y | PAD_BUTTON_B))) {
        sHud.infoCardMode = 0;
        sHud.infoCardMenu = -1;
        Sound_PlayEffect(SE_CONFIRM_sseq_3);
        return TRUE;
    }

    return FALSE;
}

BOOL BattleHud_LastConfirmWasKey(void)
{
    return sHud.lastConfirmWasKey;
}

static void HdHudPopulateButtonsAndMoves(BattleSubscreen *btlSubscreen, SIM_HudHD_Frame *frame,
    int *btnTouchIdx, int *moveTouchIdx)
{
    BattleSystem *battleSys = btlSubscreen->battleSys;
    MessageLoader *msgLoader = BattleSystem_GetMessageLoader(battleSys);
    u32 battleType = BattleSystem_GetBattleType(battleSys);
    int menu = btlSubscreen->activeMenuConfigIndex;
    int cx = btlSubscreen->cursor.x;
    int cy = btlSubscreen->cursor.y;
    int i;

    frame->numButtons = 0;
    frame->numMoves = 0;
    for (i = 0; i < SIM_HUDHD_MAX_BUTTONS; i++) {
        btnTouchIdx[i] = -1;
    }
    for (i = 0; i < SIM_HUDHD_MAX_MOVES; i++) {
        moveTouchIdx[i] = -1;
    }

    if (menu == HUD_MENU_IDLE || menu < 0) {
        return;
    }

    frame->showKeyHints = SIM_Battle3D_ModelsEnabled() ? 1 : 0;

    if (menu >= 13 && menu <= 17) {
        String *yesStr = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_Yes);
        String *noStr = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_No);

        SIM_HudHD_Button *b0 = &frame->buttons[0];
        b0->visible = 1;
        b0->style = SIM_HUDHD_BUTTON_YES;
        b0->rect = (SIM_HudHD_Rect){ 256.0f, 96.0f, 78.0f, 20.0f };
        HudStringToUtf8(yesStr, b0->label, sizeof(b0->label));
        b0->selected = (cy == 0) ? 1 : 0;
        b0->enabled = 1;
        btnTouchIdx[0] = 0;

        SIM_HudHD_Button *b1 = &frame->buttons[1];
        b1->visible = 1;
        b1->style = SIM_HUDHD_BUTTON_NO;
        b1->rect = (SIM_HudHD_Rect){ 256.0f, 120.0f, 78.0f, 20.0f };
        HudStringToUtf8(noStr, b1->label, sizeof(b1->label));
        b1->selected = (cy == 1) ? 1 : 0;
        b1->enabled = 1;
        btnTouchIdx[1] = 1;

        frame->numButtons = 2;
        String_Free(yesStr);
        String_Free(noStr);
        return;
    }

    if (menu == HUD_MENU_MOVE) {
        MoveSelectData *moveData = &btlSubscreen->activeMenuData.moveData;
        for (i = 0; i < 4; i++) {
            int col = i & 1;
            int row = i >> 1;
            SIM_HudHD_MoveCard *mc = &frame->moves[i];

            if (moveData->moveIDs[i] == 0) {
                mc->visible = 0;
                continue;
            }
            {
                String *nameStr = MessageUtil_MoveName(moveData->moveIDs[i], HEAP_ID_BATTLE);
                u32 moveClass = MoveTable_LoadParam(moveData->moveIDs[i], MOVEATTRIBUTE_CLASS);
                mc->visible = 1;
                mc->rect = (SIM_HudHD_Rect){ 178.0f, 74.0f + (float)(i * 23), 156.0f, 21.0f };
                HudStringToUtf8(nameStr, mc->name, sizeof(mc->name));
                mc->type = (int)MoveTable_LoadParam(moveData->moveIDs[i], MOVEATTRIBUTE_TYPE);
                if (moveClass == CLASS_PHYSICAL) {
                    mc->category = SIM_HUDHD_CAT_PHYSICAL;
                } else if (moveClass == CLASS_SPECIAL) {
                    mc->category = SIM_HUDHD_CAT_SPECIAL;
                } else {
                    mc->category = SIM_HUDHD_CAT_STATUS;
                }
                mc->pp = moveData->currPP[i];
                mc->maxPp = moveData->maxPP[i];
                mc->effectiveness = HdHudEffectiveness(battleSys, btlSubscreen, moveData->moveIDs[i]);
                mc->selected = (cx == col && cy == row) ? 1 : 0;
                mc->enabled = (moveData->currPP[i] > 0) ? 1 : 0;
                moveTouchIdx[i] = 1 + i;
                String_Free(nameStr);
            }
        }
        frame->numMoves = 4;

        if (moveData->megaEvolutionAvailable) {
            BattleContext *ctx = BattleSystem_GetBattleContext(battleSys);
            int battler = BattleSystem_GetBattlerOfType(battleSys, btlSubscreen->battlerType);
            int on = (ctx != NULL && ctx->megaEvolutionTriggered[battler]) ? 1 : 0;
            String *megaStr = MessageLoader_GetNewString(msgLoader, 1272); // "MEGA"
            SIM_HudHD_Button *mb = &frame->buttons[frame->numButtons];
            mb->visible = 1;
            mb->style = SIM_HUDHD_BUTTON_MEGA;
            mb->rect = (SIM_HudHD_Rect){ 178.0f, 168.0f, 92.0f, 18.0f };
            HudStringToUtf8(megaStr, mb->label, sizeof(mb->label));
            mb->selected = (cy == 2 && cx == 0) ? 1 : 0;
            mb->enabled = 1;
            mb->toggled = on;
            btnTouchIdx[frame->numButtons] = 5;
            frame->numButtons++;
            String_Free(megaStr);
        }

        {
            String *cancelStr = NULL;
            SIM_HudHD_Button *cb = &frame->buttons[frame->numButtons];
            cb->visible = 1;
            cb->style = SIM_HUDHD_BUTTON_CANCEL;
            cb->rect = moveData->megaEvolutionAvailable
                ? (SIM_HudHD_Rect){ 274.0f, 168.0f, 60.0f, 18.0f }
                : (SIM_HudHD_Rect){ 254.0f, 168.0f, 80.0f, 18.0f };
            snprintf(cb->label, sizeof(cb->label), "Back");
            cb->selected = (cy == 2 && (cx == 1 || !moveData->megaEvolutionAvailable)) ? 1 : 0;
            cb->enabled = 1;
            btnTouchIdx[frame->numButtons] = 0;
            frame->numButtons++;
            (void)cancelStr;
        }
        if (sHud.infoCardMode == 1 && sHud.infoCardMenu == menu) {
            HdHudFillMoveInfoCard(btlSubscreen, &frame->infoCard);
        }
        return;
    }

    if (menu == HUD_MENU_TARGET) {
        TargetSelectData *data = &btlSubscreen->activeMenuData.targetSelectData;
        StringTemplate *template = BattleSystem_GetStringTemplate(battleSys);
        int layout = btlSubscreen->targetingLayout;
        BOOL isMultiTarget = (layout == 1 || layout == 2 || layout == 3 || layout == 5 || layout == 7);
        BOOL cancelSel = isMultiTarget ? (cy > 0) : (cy == 2);
        u8 battlersByType[6];
        static const u8 sGridTypeIdx[2][2] = { { 5, 3 }, { 2, 4 } };
        static const u8 sGridTouchIdx[2][2] = { { 3, 1 }, { 0, 2 } };
        int row, col;

        BattleSystem_SetBattlersByType(battleSys, battlersByType);

        for (row = 0; row < 2; row++) {
            for (col = 0; col < 2; col++) {
                int battlerIndex = battlersByType[sGridTypeIdx[row][col]];
                SIM_HudHD_Button *tb = &frame->buttons[frame->numButtons];
                BOOL selected = isMultiTarget
                    ? ((!cancelSel) && WideHudTargetMultiSelected(layout, row, col))
                    : ((!cancelSel) && (cy == row && cx == col));

                tb->rect = (SIM_HudHD_Rect){
                    col ? 242.0f : 146.0f,
                    row ? 142.0f : 120.0f,
                    92.0f, 18.0f
                };
                tb->style = SIM_HUDHD_BUTTON_GENERIC;
                tb->selected = selected ? 1 : 0;
                if (data->targetMonData[battlerIndex].isPresent) {
                    String *fmt = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_HealthBoxPokemonName);
                    String *msg = String_Init(32, HEAP_ID_BATTLE);
                    Pokemon *mon = BattleSystem_GetPartyPokemon(battleSys, battlerIndex, data->targetMonData[battlerIndex].partySlot);
                    StringTemplate_SetNickname(template, 0, Pokemon_GetBoxPokemon(mon));
                    StringTemplate_Format(template, msg, fmt);
                    tb->visible = 1;
                    tb->enabled = 1;
                    HudStringToUtf8(msg, tb->label, sizeof(tb->label));
                    String_Free(msg);
                    String_Free(fmt);
                    btnTouchIdx[frame->numButtons] = sGridTouchIdx[row][col];
                    frame->numButtons++;
                }
            }
        }

        {
            SIM_HudHD_Button *cb = &frame->buttons[frame->numButtons];
            cb->visible = 1;
            cb->style = SIM_HUDHD_BUTTON_CANCEL;
            cb->rect = (SIM_HudHD_Rect){ 146.0f, 166.0f, 188.0f, 18.0f };
            snprintf(cb->label, sizeof(cb->label), "Back");
            cb->selected = cancelSel ? 1 : 0;
            cb->enabled = 1;
            btnTouchIdx[frame->numButtons] = 4;
            frame->numButtons++;
        }
        return;
    }

    if (menu >= 1 && menu <= 10) {
        if (menu == 5 || menu == 6) {
            SIM_HudHD_Button *b = &frame->buttons[0];
            b->visible = 1;
            b->style = SIM_HUDHD_BUTTON_FIGHT;
            b->rect = (SIM_HudHD_Rect){ 248.0f, 162.0f, 86.0f, 24.0f };
            snprintf(b->label, sizeof(b->label), "Battle");
            b->selected = 1;
            b->enabled = 1;
            btnTouchIdx[0] = 0;
            frame->numButtons = 1;
            if (sHud.infoCardMode == 2 && sHud.infoCardMenu == menu) {
                HdHudFillBattleStatusCard(battleSys, &frame->infoCard);
            }
            return;
        }

        if (menu == 9 || menu == 10) {
            SIM_HudHD_Button *b0 = &frame->buttons[0];
            SIM_HudHD_Button *b1 = &frame->buttons[1];

            b0->visible = 1;
            b0->style = SIM_HUDHD_BUTTON_FIGHT;
            b0->rect = (SIM_HudHD_Rect){ 248.0f, 138.0f, 86.0f, 22.0f };
            snprintf(b0->label, sizeof(b0->label), "Ball");
            b0->selected = (cy == 0) ? 1 : 0;
            b0->enabled = 1;
            btnTouchIdx[0] = 0;

            b1->visible = 1;
            b1->style = SIM_HUDHD_BUTTON_RUN;
            b1->rect = (SIM_HudHD_Rect){ 248.0f, 164.0f, 86.0f, 22.0f };
            snprintf(b1->label, sizeof(b1->label), "Run");
            b1->selected = (cy == 1) ? 1 : 0;
            b1->enabled = 1;
            btnTouchIdx[1] = 1;

            frame->numButtons = 2;
            if (sHud.infoCardMode == 2 && sHud.infoCardMenu == menu) {
                HdHudFillBattleStatusCard(battleSys, &frame->infoCard);
            }
            return;
        }

        if (BdspHudHasWildQuickBall(btlSubscreen, menu)) {
            u16 qbItem = ITEM_NONE;
            int qbCount = 0;
            SIM_HudHD_Button *qb = &frame->buttons[frame->numButtons];
            HdHudQuickBallInfo(battleSys, &qbItem, &qbCount);
            (void)qbItem;
            frame->quickBallCount = qbCount;
            qb->visible = 1;
            qb->style = SIM_HUDHD_BUTTON_QUICK_BALL;
            qb->rect = (SIM_HudHD_Rect){ 248.0f, 74.0f, 86.0f, 18.0f };
            snprintf(qb->label, sizeof(qb->label), "Ball");
            qb->selected = 0;
            qb->enabled = (qbCount > 0 || !SIM_Battle3D_ModelsEnabled()) ? 1 : 0;
            btnTouchIdx[frame->numButtons] = 1;
            frame->numButtons++;
        }

        {
            const char *fightLbl = (battleType & BATTLE_TYPE_SAFARI) ? "Ball" : "Battle";
            const char *partyLbl = (battleType & BATTLE_TYPE_SAFARI) ? "Mud" : "Pok\xC3\xA9mon";
            const char *bagLbl = (battleType & BATTLE_TYPE_SAFARI) ? "Bait" : "Bag";
            const char *runLbl = btlSubscreen->activeMenuData.actionData.isWaitingForPartner ? "Back" : "Run";
            SIM_HudHD_Button *b;

            b = &frame->buttons[frame->numButtons];
            b->visible = 1;
            b->style = SIM_HUDHD_BUTTON_FIGHT;
            b->rect = (SIM_HudHD_Rect){ 248.0f, 96.0f, 86.0f, 21.0f };
            snprintf(b->label, sizeof(b->label), "%s", fightLbl);
            b->selected = (cy == 0) ? 1 : 0;
            b->enabled = 1;
            btnTouchIdx[frame->numButtons++] = 0;

            b = &frame->buttons[frame->numButtons];
            b->visible = 1;
            b->style = SIM_HUDHD_BUTTON_POKEMON;
            b->rect = (SIM_HudHD_Rect){ 248.0f, 119.0f, 86.0f, 21.0f };
            snprintf(b->label, sizeof(b->label), "%s", partyLbl);
            b->selected = (cy == 1 && cx == 2) ? 1 : 0;
            b->enabled = 1;
            btnTouchIdx[frame->numButtons++] = 2;

            b = &frame->buttons[frame->numButtons];
            b->visible = 1;
            b->style = SIM_HUDHD_BUTTON_BAG;
            b->rect = (SIM_HudHD_Rect){ 248.0f, 142.0f, 86.0f, 21.0f };
            snprintf(b->label, sizeof(b->label), "%s", bagLbl);
            b->selected = (cy == 1 && cx == 0) ? 1 : 0;
            b->enabled = 1;
            btnTouchIdx[frame->numButtons++] = 1;

            b = &frame->buttons[frame->numButtons];
            b->visible = 1;
            b->style = SIM_HUDHD_BUTTON_RUN;
            b->rect = (SIM_HudHD_Rect){ 248.0f, 165.0f, 86.0f, 21.0f };
            snprintf(b->label, sizeof(b->label), "%s", runLbl);
            b->selected = (cy == 1 && cx == 1) ? 1 : 0;
            b->enabled = 1;
            btnTouchIdx[frame->numButtons++] = 3;
        }
        if (sHud.infoCardMode == 2 && sHud.infoCardMenu == menu) {
            HdHudFillBattleStatusCard(battleSys, &frame->infoCard);
        }
    }
}

static BOOL HdHudRectContains(SIM_HudHD_Rect r, int x, int y)
{
    return ((float)x >= r.x && (float)x < r.x + r.w && (float)y >= r.y && (float)y < r.y + r.h) ? TRUE : FALSE;
}

static int HdHudTouchButtonIndexEx(BattleSubscreen *btlSubscreen, int x, int y,
    BOOL *outIsQuickBall, BOOL *outIsInfoToggle)
{
    SIM_HudHD_Frame frame;
    int btnTouchIdx[SIM_HUDHD_MAX_BUTTONS];
    int moveTouchIdx[SIM_HUDHD_MAX_MOVES];
    int menu, i;

    if (outIsQuickBall != NULL) {
        *outIsQuickBall = FALSE;
    }
    if (outIsInfoToggle != NULL) {
        *outIsInfoToggle = FALSE;
    }
    if (btlSubscreen == NULL || x < 0 || x >= WIDE_HUD_WIDTH_PX || y < 0 || y >= HW_LCD_HEIGHT) {
        return -1;
    }

    memset(&frame, 0, sizeof(frame));
    HdHudPopulateButtonsAndMoves(btlSubscreen, &frame, btnTouchIdx, moveTouchIdx);
    menu = btlSubscreen->activeMenuConfigIndex;

    // Clicking an open info card dismisses it without activating buttons underneath.
    if (frame.infoCard.visible && HdHudRectContains(frame.infoCard.rect, x, y)) {
        if (outIsInfoToggle != NULL) {
            *outIsInfoToggle = TRUE;
        }
        return -1;
    }

    for (i = 0; i < frame.numMoves; i++) {
        if (!frame.moves[i].visible) {
            continue;
        }
        if (HdHudRectContains(frame.moves[i].rect, x, y)) {
            return moveTouchIdx[i];
        }
    }
    for (i = 0; i < frame.numButtons; i++) {
        if (!frame.buttons[i].visible) {
            continue;
        }
        if (HdHudRectContains(frame.buttons[i].rect, x, y)) {
            if (frame.buttons[i].style == SIM_HUDHD_BUTTON_QUICK_BALL && outIsQuickBall != NULL) {
                *outIsQuickBall = TRUE;
            }
            return btnTouchIdx[i];
        }
    }

    // Touch-friendly Info Toggle hitboxes matching BDSP HD HUD layout:
    // - Move Select: key-guide / info pill zone to the left of Back (or bottom key bar).
    // - Action Menu: tapping Player/Enemy HP plates or bottom key-guide bar toggles Battle Status.
    if (outIsInfoToggle != NULL) {
        if (menu == HUD_MENU_MOVE) {
            if (!btlSubscreen->activeMenuData.moveData.megaEvolutionAvailable
                && HdHudRectContains((SIM_HudHD_Rect){ 178.0f, 168.0f, 74.0f, 18.0f }, x, y)) {
                *outIsInfoToggle = TRUE;
                return -1;
            }
            if (frame.showKeyHints && HdHudRectContains((SIM_HudHD_Rect){ 122.0f, 172.0f, 124.0f, 18.0f }, x, y)) {
                *outIsInfoToggle = TRUE;
                return -1;
            }
        } else if (menu >= 1 && menu <= 10) {
            u32 battleType = BattleSystem_GetBattleType(btlSubscreen->battleSys);
            SIM_HudHD_Rect playerPlate = (battleType & BATTLE_TYPE_DOUBLES)
                ? (SIM_HudHD_Rect){ 8.0f, 118.0f, 102.0f, 60.0f }
                : (SIM_HudHD_Rect){ 8.0f, 144.0f, 110.0f, 33.0f };
            SIM_HudHD_Rect enemyPlate = (battleType & BATTLE_TYPE_DOUBLES)
                ? (SIM_HudHD_Rect){ 236.0f, 6.0f, 98.0f, 44.0f }
                : (SIM_HudHD_Rect){ 234.0f, 8.0f, 100.0f, 22.0f };
            if (HdHudRectContains(playerPlate, x, y) || HdHudRectContains(enemyPlate, x, y)) {
                *outIsInfoToggle = TRUE;
                return -1;
            }
            if (frame.showKeyHints && HdHudRectContains((SIM_HudHD_Rect){ 122.0f, 172.0f, 122.0f, 18.0f }, x, y)) {
                *outIsInfoToggle = TRUE;
                return -1;
            }
        }
    }
    return -1;
}

static int HdHudTouchButtonIndex(BattleSubscreen *btlSubscreen, int x, int y)
{
    return HdHudTouchButtonIndexEx(btlSubscreen, x, y, NULL, NULL);
}

static int HdHudMapStatus(const HealthBox *hb, Pokemon *mon)
{
    if (hb->curHP <= 0 && hb->type != HEALTHBOX_TYPE_SAFARI_ZONE && hb->type != HEALTHBOX_TYPE_PAL_PARK) {
        return SIM_HUDHD_STATUS_FNT;
    }
    switch (hb->status) {
    case BATTLE_ANIMATION_ASLEEP:
        return SIM_HUDHD_STATUS_SLP;
    case BATTLE_ANIMATION_POISONED:
        if (mon != NULL && (Pokemon_GetValue(mon, MON_DATA_STATUS, NULL) & MON_CONDITION_TOXIC)) {
            return SIM_HUDHD_STATUS_TOX;
        }
        return SIM_HUDHD_STATUS_PSN;
    case BATTLE_ANIMATION_BURNED:
        return SIM_HUDHD_STATUS_BRN;
    case BATTLE_ANIMATION_FROZEN:
        return SIM_HUDHD_STATUS_FRZ;
    case BATTLE_ANIMATION_PARALYZED:
        return SIM_HUDHD_STATUS_PAR;
    default:
        return SIM_HUDHD_STATUS_NONE;
    }
}

static SIM_HudHD_Rect HdHudCardRect(u8 healthboxType)
{
    switch (healthboxType) {
    case HEALTHBOX_TYPE_PLAYER_SOLO:
    case HEALTHBOX_TYPE_SAFARI_ZONE:
    case HEALTHBOX_TYPE_PAL_PARK:
        return (SIM_HudHD_Rect){ 8.0f, 144.0f, 110.0f, 33.0f };
    case HEALTHBOX_TYPE_ENEMY_SOLO:
        return (SIM_HudHD_Rect){ 234.0f, 8.0f, 100.0f, 22.0f };
    case HEALTHBOX_TYPE_PLAYER_SLOT_1:
        return (SIM_HudHD_Rect){ 8.0f, 118.0f, 102.0f, 29.0f };
    case HEALTHBOX_TYPE_PLAYER_SLOT_2:
        return (SIM_HudHD_Rect){ 8.0f, 149.0f, 102.0f, 29.0f };
    case HEALTHBOX_TYPE_ENEMY_SLOT_1:
        return (SIM_HudHD_Rect){ 236.0f, 6.0f, 98.0f, 21.0f };
    case HEALTHBOX_TYPE_ENEMY_SLOT_2:
        return (SIM_HudHD_Rect){ 236.0f, 29.0f, 98.0f, 21.0f };
    default:
        return (SIM_HudHD_Rect){ 8.0f, 144.0f, 110.0f, 33.0f };
    }
}

static void HdHudFillCard(BattleSystem *battleSys, const HealthBox *hb, SIM_HudHD_Card *card)
{
    u32 battleType = BattleSystem_GetBattleType(battleSys);
    BOOL isPlayer;
    Pokemon *mon;
    float animHp;
    int dispHp;

    if (hb == NULL || hb->mainSprite == NULL || !hb->hdVisible) {
        card->visible = 0;
        return;
    }
    if (hb->maxHP <= 0 && hb->type != HEALTHBOX_TYPE_SAFARI_ZONE && hb->type != HEALTHBOX_TYPE_PAL_PARK) {
        card->visible = 0;
        return;
    }

    isPlayer = (hb->type == HEALTHBOX_TYPE_PLAYER_SOLO
        || hb->type == HEALTHBOX_TYPE_PLAYER_SLOT_1
        || hb->type == HEALTHBOX_TYPE_PLAYER_SLOT_2
        || hb->type == HEALTHBOX_TYPE_SAFARI_ZONE
        || hb->type == HEALTHBOX_TYPE_PAL_PARK);

    card->visible = 1;
    card->isPlayer = isPlayer ? 1 : 0;
    card->rect = HdHudCardRect(hb->type);
    card->level = hb->level;
    card->alpha = 1.0f;

    if (hb->scrollDirection == HEALTHBOX_SCROLL_OUT && hb->doneScrolling) {
        card->alpha = 0.0f;
    }

    if (hb->type == HEALTHBOX_TYPE_SAFARI_ZONE || hb->type == HEALTHBOX_TYPE_PAL_PARK) {
        snprintf(card->name, sizeof(card->name), "%s",
            (hb->type == HEALTHBOX_TYPE_SAFARI_ZONE) ? "Safari Balls" : "Park Balls");
        card->gender = SIM_HUDHD_GENDER_NONE;
        card->hpFrac = 1.0f;
        card->hp = hb->numSafariBalls;
        card->maxHp = 30;
        card->showHpNumbers = 1;
        card->showExp = 0;
        card->expFrac = 0.0f;
        card->status = SIM_HUDHD_STATUS_NONE;
        card->caught = 0;
        return;
    }

    mon = BattleSystem_GetPartyPokemon(battleSys, hb->battler, hb->selectedPartySlot);
    if (mon != NULL) {
        String *nick = String_Init(MON_NAME_LEN + 4, HEAP_ID_BATTLE);
        Pokemon_GetValue(mon, MON_DATA_NICKNAME_STRING, nick);
        HudStringToUtf8(nick, card->name, sizeof(card->name));
        String_Free(nick);
    }

    if (hb->gender == GENDER_MALE) {
        card->gender = SIM_HUDHD_GENDER_MALE;
    } else if (hb->gender == GENDER_FEMALE) {
        card->gender = SIM_HUDHD_GENDER_FEMALE;
    } else {
        card->gender = SIM_HUDHD_GENDER_NONE;
    }

    if (hb->hpTemp != (-0x7fffffff - 1) && hb->hpTemp > 0) {
        if (hb->maxHP < 48) {
            animHp = (float)hb->hpTemp / 256.0f;
            dispHp = (hb->hpTemp >> 8) + ((hb->hpTemp & 0xFF) > 0 ? 1 : 0);
        } else {
            animHp = (float)hb->hpTemp;
            dispHp = hb->hpTemp;
        }
    } else {
        animHp = (float)hb->curHP;
        dispHp = hb->curHP;
    }

    card->maxHp = hb->maxHP;
    card->hp = dispHp;
    card->hpFrac = (hb->maxHP > 0) ? (animHp / (float)hb->maxHP) : 0.0f;
    if (card->hpFrac < 0.0f) {
        card->hpFrac = 0.0f;
    } else if (card->hpFrac > 1.0f) {
        card->hpFrac = 1.0f;
    }
    card->showHpNumbers = isPlayer ? 1 : 0;

    if (hb->type == HEALTHBOX_TYPE_PLAYER_SOLO && hb->level < MAX_POKEMON_LEVEL && hb->maxExp > 0) {
        float animExp;
        if (hb->expTemp != (-0x7fffffff - 1) && hb->expTemp > 0) {
            animExp = (hb->maxExp < 64) ? ((float)hb->expTemp / 256.0f) : (float)hb->expTemp;
        } else {
            animExp = (float)hb->curExp;
        }
        card->showExp = 1;
        card->expFrac = animExp / (float)hb->maxExp;
        if (card->expFrac < 0.0f) {
            card->expFrac = 0.0f;
        } else if (card->expFrac > 1.0f) {
            card->expFrac = 1.0f;
        }
    } else {
        card->showExp = 0;
        card->expFrac = 0.0f;
    }

    card->status = HdHudMapStatus(hb, mon);
    card->caught = (!isPlayer && !(battleType & BATTLE_TYPE_TRAINER) && hb->caughtSpecies) ? 1 : 0;
}

static int HdHudBallState(Pokemon *mon)
{
    u32 hp, status;
    if (mon == NULL || Pokemon_GetValue(mon, MON_DATA_IS_EGG, NULL)) {
        return SIM_HUDHD_BALL_EMPTY;
    }
    hp = Pokemon_GetValue(mon, MON_DATA_HP, NULL);
    if (hp == 0) {
        return SIM_HUDHD_BALL_FAINTED;
    }
    status = Pokemon_GetValue(mon, MON_DATA_STATUS, NULL);
    if (status & MON_CONDITION_ANY) {
        return SIM_HUDHD_BALL_STATUS;
    }
    return SIM_HUDHD_BALL_OK;
}

static void HdHudFillPartyStrip(BattleSystem *battleSys, int battler, SIM_HudHD_Rect rect,
    BOOL visible, SIM_HudHD_PartyStrip *strip)
{
    Party *party;
    int count, i;

    strip->visible = visible ? 1 : 0;
    strip->rect = rect;
    strip->count = 0;
    for (i = 0; i < 6; i++) {
        strip->balls[i] = SIM_HUDHD_BALL_EMPTY;
    }
    if (!visible) {
        return;
    }

    party = BattleSystem_GetParty(battleSys, battler);
    if (party == NULL) {
        return;
    }
    count = Party_GetCurrentCount(party);
    if (count > 6) {
        count = 6;
    }
    // Always draw 6 slots (unused slots remain SIM_HUDHD_BALL_EMPTY).
    strip->count = 6;
    for (i = 0; i < count; i++) {
        strip->balls[i] = HdHudBallState(Party_GetPokemonBySlotIndex(party, i));
    }
}

static u32 HdHudHashBytes(const void *data, size_t len)
{
    const u8 *p = (const u8 *)data;
    u32 h = 2166136261u;
    size_t i;
    for (i = 0; i < len; i++) {
        h ^= p[i];
        h *= 16777619u;
    }
    return h;
}

static void HdHudWriteJsonStr(FILE *f, const char *s)
{
    fputc('"', f);
    if (s != NULL) {
        const unsigned char *p = (const unsigned char *)s;
        while (*p != '\0') {
            if (*p == '"' || *p == '\\') {
                fputc('\\', f);
                fputc((int)*p, f);
            } else if (*p == '\n') {
                fputs("\\n", f);
            } else if (*p == '\r') {
                fputs("\\r", f);
            } else if (*p == '\t') {
                fputs("\\t", f);
            } else if (*p < 0x20) {
                fputc(' ', f);
            } else {
                fputc((int)*p, f);
            }
            p++;
        }
    }
    fputc('"', f);
}

static void HdHudDumpFrame(const SIM_HudHD_Frame *frame)
{
    const char *path = getenv("SIM_HUDHD_DUMP");
    u32 h;
    FILE *f;
    int i, j;

    if (path == NULL || path[0] == '\0') {
        return;
    }
    h = HdHudHashBytes(frame, sizeof(*frame));
    if (sHud.hasDumped && h == sHud.lastDumpHash) {
        return;
    }
    sHud.lastDumpHash = h;
    sHud.hasDumped = TRUE;

    f = fopen(path, "a");
    if (f == NULL) {
        return;
    }

    fprintf(f, "{\"active\":%d,\"canvas\":[%.0f,%.0f],\"cards\":[",
        frame->active, frame->canvasW, frame->canvasH);
    for (i = 0; i < SIM_HUDHD_MAX_CARDS; i++) {
        const SIM_HudHD_Card *c = &frame->cards[i];
        if (i > 0) {
            fprintf(f, ",");
        }
        fprintf(f, "{\"visible\":%d,\"isPlayer\":%d,\"rect\":[%.0f,%.0f,%.0f,%.0f],"
            "\"name\":\"%s\",\"gender\":%d,\"level\":%d,\"hpFrac\":%.3f,"
            "\"hp\":%d,\"maxHp\":%d,\"showHpNumbers\":%d,\"expFrac\":%.3f,"
            "\"showExp\":%d,\"status\":%d,\"caught\":%d,\"alpha\":%.2f}",
            c->visible, c->isPlayer, c->rect.x, c->rect.y, c->rect.w, c->rect.h,
            c->name, c->gender, c->level, c->hpFrac, c->hp, c->maxHp,
            c->showHpNumbers, c->expFrac, c->showExp, c->status, c->caught, c->alpha);
    }
    fprintf(f, "],\"partyStrips\":[");
    for (i = 0; i < 2; i++) {
        const SIM_HudHD_PartyStrip *ps = &frame->partyStrips[i];
        if (i > 0) {
            fprintf(f, ",");
        }
        fprintf(f, "{\"visible\":%d,\"count\":%d,\"balls\":[", ps->visible, ps->count);
        for (j = 0; j < 6; j++) {
            fprintf(f, "%s%d", j > 0 ? "," : "", ps->balls[j]);
        }
        fprintf(f, "]}");
    }
    fprintf(f, "],\"numButtons\":%d,\"buttons\":[", frame->numButtons);
    for (i = 0; i < frame->numButtons; i++) {
        const SIM_HudHD_Button *b = &frame->buttons[i];
        if (i > 0) {
            fprintf(f, ",");
        }
        fprintf(f, "{\"style\":%d,\"rect\":[%.0f,%.0f,%.0f,%.0f],\"label\":\"%s\",\"selected\":%d,\"enabled\":%d,\"toggled\":%d}",
            b->style, b->rect.x, b->rect.y, b->rect.w, b->rect.h, b->label, b->selected, b->enabled, b->toggled);
    }
    fprintf(f, "],\"numMoves\":%d,\"moves\":[", frame->numMoves);
    for (i = 0; i < frame->numMoves; i++) {
        const SIM_HudHD_MoveCard *m = &frame->moves[i];
        if (i > 0) {
            fprintf(f, ",");
        }
        fprintf(f, "{\"visible\":%d,\"rect\":[%.0f,%.0f,%.0f,%.0f],\"name\":\"%s\",\"type\":%d,\"category\":%d,\"pp\":%d,\"maxPp\":%d,\"eff\":%d,\"selected\":%d,\"enabled\":%d}",
            m->visible, m->rect.x, m->rect.y, m->rect.w, m->rect.h, m->name, m->type, m->category, m->pp, m->maxPp, m->effectiveness, m->selected, m->enabled);
    }
    fprintf(f, "],\"quickBallCount\":%d,\"showKeyHints\":%d,\"infoCard\":{\"visible\":%d,\"kind\":%d,\"rect\":[%.0f,%.0f,%.0f,%.0f],\"title\":",
        frame->quickBallCount, frame->showKeyHints,
        frame->infoCard.visible, frame->infoCard.kind,
        frame->infoCard.rect.x, frame->infoCard.rect.y, frame->infoCard.rect.w, frame->infoCard.rect.h);
    HdHudWriteJsonStr(f, frame->infoCard.title);
    fprintf(f, ",\"line1\":");
    HdHudWriteJsonStr(f, frame->infoCard.line1);
    fprintf(f, ",\"line2\":");
    HdHudWriteJsonStr(f, frame->infoCard.line2);
    fprintf(f, ",\"desc\":");
    HdHudWriteJsonStr(f, frame->infoCard.desc);
    fprintf(f, ",\"type\":%d,\"category\":%d}}\n", frame->infoCard.type, frame->infoCard.category);
    fclose(f);
}

void BattleHud_SyncFrame(BattleSystem *battleSys)
{
    SIM_HudHD_Frame frame;
    int maxBattlers, i;
    BOOL anyPlayerCard = FALSE;
    BOOL anyEnemyCard = FALSE;
    u32 battleType;
    int btnTouchIdx[SIM_HUDHD_MAX_BUTTONS];
    int moveTouchIdx[SIM_HUDHD_MAX_MOVES];

    if (battleSys == NULL || !BattleHud_IsHdMode()) {
        return;
    }

    memset(&frame, 0, sizeof(frame));
    frame.active = 1;
    frame.canvasW = (float)WIDE_HUD_WIDTH_PX;
    frame.canvasH = (float)HW_LCD_HEIGHT;

    maxBattlers = BattleSystem_GetMaxBattlers(battleSys);
    if (maxBattlers > SIM_HUDHD_MAX_CARDS) {
        maxBattlers = SIM_HUDHD_MAX_CARDS;
    }
    for (i = 0; i < maxBattlers; i++) {
        BattlerData *bd = BattleSystem_GetBattlerData(battleSys, i);
        HealthBox *hb = (bd != NULL) ? BattlerData_GetHealthBox(bd) : NULL;
        HdHudFillCard(battleSys, hb, &frame.cards[i]);
        if (frame.cards[i].visible) {
            if (frame.cards[i].isPlayer) {
                anyPlayerCard = TRUE;
            } else {
                anyEnemyCard = TRUE;
            }
        }
    }

    battleType = BattleSystem_GetBattleType(battleSys);
    if (battleType & (BATTLE_TYPE_SAFARI | BATTLE_TYPE_PAL_PARK)) {
        anyPlayerCard = FALSE;
    }
    HdHudFillPartyStrip(battleSys, BATTLER_PLAYER_1,
        (battleType & BATTLE_TYPE_DOUBLES)
            ? (SIM_HudHD_Rect){ 8.0f, 180.0f, 102.0f, 10.0f }
            : (SIM_HudHD_Rect){ 8.0f, 179.0f, 110.0f, 10.0f },
        anyPlayerCard, &frame.partyStrips[0]);
    HdHudFillPartyStrip(battleSys, BATTLER_ENEMY_1,
        (battleType & BATTLE_TYPE_DOUBLES)
            ? (SIM_HudHD_Rect){ 236.0f, 52.0f, 98.0f, 10.0f }
            : (SIM_HudHD_Rect){ 234.0f, 32.0f, 100.0f, 11.0f },
        anyEnemyCard && (battleType & BATTLE_TYPE_TRAINER), &frame.partyStrips[1]);

    if (sHud.activeSubscreen != NULL) {
        HdHudPopulateButtonsAndMoves(sHud.activeSubscreen, &frame, btnTouchIdx, moveTouchIdx);
    }

    HdHudDumpFrame(&frame);
    BattleBdspDialogue_FillFrame(battleSys, &frame);
    BattleBdspOverlay_TickAndFillFrame(battleSys, &frame);
    GameHudHD_Submit(&frame);
}

void BattleHud_Reset(void)
{
    SIM_HudHD_Frame frame;
    sHud.activeSubscreen = NULL;
    sHud.infoCardMode = 0;
    sHud.infoCardMenu = -1;
    sHud.lastConfirmWasKey = FALSE;
    sHud.cachedMoveInfoId = 0;
    if (!BattleHud_IsHdMode()) {
        return;
    }
    memset(&frame, 0, sizeof(frame));
    frame.active = 0;
    frame.canvasW = (float)WIDE_HUD_WIDTH_PX;
    frame.canvasH = (float)HW_LCD_HEIGHT;
    HdHudDumpFrame(&frame);
    BattleBdspDialogue_Reset();
    BattleBdspOverlay_Reset();
    GameHudHD_Submit(&frame);
}

// Map a main-touch click (DS coords) to a touch-array button index for
// the current menu, mirroring the bottom screen's button layout.
static int HudTouchButtonIndex(BattleSubscreen *btlSubscreen, int x, int y)
{
    int menu = btlSubscreen->activeMenuConfigIndex;
    int col, row;

    if (BattleHud_IsHdMode()) {
        return HdHudTouchButtonIndex(btlSubscreen, x, y);
    }

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
    BOOL hdMode;
    BOOL bdsp3d;
    BOOL widePixel;

    if (!BattleHud_IsEnabled() || btlSubscreen == NULL) {
        sHud.lastConfirmWasKey = FALSE;
        if (btlSubscreen != NULL) {
            sHud.activeSubscreen = NULL;
            sHud.infoCardMode = 0;
            sHud.infoCardMenu = -1;
            HudHideInternal(btlSubscreen);
        }
        return -1;
    }

    sHud.lastConfirmWasKey = FALSE;
    menu = btlSubscreen->activeMenuConfigIndex;
    if (menu == HUD_MENU_IDLE || menu < 0) {
        sHud.activeSubscreen = NULL;
        sHud.infoCardMode = 0;
        sHud.infoCardMenu = -1;
        HudHideInternal(btlSubscreen);
        return -1;
    }
    if (sHud.infoCardMode != 0 && menu != sHud.infoCardMenu) {
        sHud.infoCardMode = 0;
        sHud.infoCardMenu = -1;
    }

    hdMode = BattleHud_IsHdMode();
    bdsp3d = SIM_Battle3D_IsEnabled();
    widePixel = BattleHud_IsWidePixelMode();

    // Wide layout: HUD is up on the top screen, bottom panel not needed.
    if (SIM_Wide_IsWideLayout()) {
        SIM_Wide_SetBattleTouchNeeded(0);
    }
    SIM_Wide_SetMainTouchEnabled(1);

    // Wild quick-ball shortcut: X opens Bag focused on Poké Balls pocket cleanly.
    if ((bdsp3d || hdMode) && !btlSubscreen->isPanelSliding
        && BdspHudHasWildQuickBall(btlSubscreen, menu)
        && (gSystem.pressedKeys & PAD_BUTTON_X)) {
        HdHudPrepareQuickBallBag(btlSubscreen);
        sHud.lastConfirmWasKey = TRUE;
        return 1;
    }

    // Main-screen click: confirm like a bottom-screen touch (or toggle info card).
    if (!btlSubscreen->isPanelSliding && SIM_Wide_PollMainTouch(&touchX, &touchY)) {
        if (hdMode) {
            BOOL isQuickBall = FALSE;
            BOOL isInfoToggle = FALSE;
            int button = HdHudTouchButtonIndexEx(btlSubscreen, touchX, touchY, &isQuickBall, &isInfoToggle);
            if (isInfoToggle) {
                if (sHud.infoCardMode != 0) {
                    sHud.infoCardMode = 0;
                    sHud.infoCardMenu = -1;
                } else if (menu == HUD_MENU_MOVE) {
                    sHud.infoCardMode = 1;
                    sHud.infoCardMenu = menu;
                } else if (menu >= 1 && menu <= 10) {
                    sHud.infoCardMode = 2;
                    sHud.infoCardMenu = menu;
                }
                Sound_PlayEffect(SE_CONFIRM_sseq_3);
                return -1;
            }
            if (isQuickBall) {
                HdHudPrepareQuickBallBag(btlSubscreen);
                return button;
            }
            if (button >= 0) {
                sHud.infoCardMode = 0;
                sHud.infoCardMenu = -1;
                return button;
            }
        } else {
            int button = HudTouchButtonIndex(btlSubscreen, touchX, touchY);
            if (button >= 0) {
                if (bdsp3d && BdspHudHasWildQuickBall(btlSubscreen, menu)) {
                    int wy = BDSP_HUD_ACTION_Y * 8;
                    int wx = BDSP_HUD_ACTION_X * 8;
                    if (touchX >= wx + 3 && touchX < wx + 91 && touchY >= wy + 1 && touchY < wy + 19) {
                        HdHudPrepareQuickBallBag(btlSubscreen);
                    }
                }
                return button;
            }
        }
    }

    if (hdMode) {
        sHud.activeSubscreen = btlSubscreen;
        if (sHud.windowAdded) {
            HudHideInternal(btlSubscreen);
        }
        if (menu >= 1 && menu <= 12) {
            BdspHudClearBg1Lower(btlSubscreen->battleSys);
            Bg_ScheduleTilemapTransfer(BattleSystem_GetBgConfig(btlSubscreen->battleSys), BG_LAYER_MAIN_1);
        }
        return -1;
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
    if (BattleHud_IsHdMode() && sHud.activeSubscreen != NULL) {
        int menu = sHud.activeSubscreen->activeMenuConfigIndex;
        if (menu >= 1 && menu <= 12) {
            return TRUE;
        }
    }
    return sHud.windowAdded;
}

BOOL BattleHud_IsBdspCornerHud(void)
{
#ifdef SDK_PORT
    return BattleHud_IsEnabled() && (SIM_Battle3D_IsEnabled() || BattleHud_IsHdMode());
#else
    return FALSE;
#endif
}

int BattleHud_TopTouchButton(BattleSubscreen *btlSubscreen, int x, int y)
{
    if (!BattleHud_IsEnabled() || btlSubscreen == NULL) {
        return -1;
    }
    return HudTouchButtonIndex(btlSubscreen, x, y);
}
