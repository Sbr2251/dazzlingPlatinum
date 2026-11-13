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
#include <stdlib.h>
#include <string.h>

#include "battle/battle_context.h"
#include "battle/battle_system.h"
#include "battle/healthbox.h"
#include "port/sim_config_prj.h"
#include "port/sim_wide.h"

#include "bg_window.h"
#include "message.h"
#include "message_util.h"
#include "move_table.h"
#include "pokemon.h"
#include "render_window.h"
#include "string_gf.h"
#include "string_template.h"
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

typedef struct BattleHudState {
    Window window;
    BOOL windowAdded;
    BOOL tilesLoaded;
    BOOL healthboxesLifted;
    int lastMenu;
    int lastCursorX;
    int lastCursorY;
    int lastMega;
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
        // Clear the strip so no panel tiles linger over the scene: wipe
        // the window bitmap to transparent and upload both the char
        // tiles and the tilemap (a tilemap-buffer write alone never
        // reaches VRAM).
        BgConfig *bgConfig = BattleSystem_GetBgConfig(btlSubscreen->battleSys);
        Window_FillRectWithColor(&sHud.window, 0, 0, 0, HUD_TILE_W * 8, HUD_TILE_H * 8);
        Window_ScheduleCopyToVRAM(&sHud.window);
        Bg_FillTilemapRect(bgConfig, BG_LAYER_MAIN_1,
            0, HUD_TILE_X, HUD_TILE_Y, HUD_TILE_W, HUD_TILE_H, HUD_PALETTE);
        Bg_ScheduleTilemapTransfer(bgConfig, BG_LAYER_MAIN_1);
        Window_Remove(&sHud.window);
        sHud.windowAdded = FALSE;
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

// Map a main-touch click (DS coords) to a touch-array button index for
// the current menu, mirroring the bottom screen's button layout.
static int HudTouchButtonIndex(BattleSubscreen *btlSubscreen, int x, int y)
{
    int menu = btlSubscreen->activeMenuConfigIndex;
    int col, row;

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

    // Wide layout: HUD is up on the top screen, bottom panel not needed.
    if (SIM_Wide_IsWideLayout()) {
        SIM_Wide_SetBattleTouchNeeded(0);
    }
    SIM_Wide_SetMainTouchEnabled(1);

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

    if (sHud.windowAdded && menu == sHud.lastMenu && cx == sHud.lastCursorX && cy == sHud.lastCursorY
        && menu != HUD_MENU_MOVE) {
        HudLiftHealthboxes(btlSubscreen, TRUE);
        return -1;
    }
    if (menu == HUD_MENU_MOVE && sHud.windowAdded && menu == sHud.lastMenu && cx == sHud.lastCursorX && cy == sHud.lastCursorY) {
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
            HudLiftHealthboxes(btlSubscreen, TRUE);
            return -1;
        }
    }

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

    Window_ScheduleCopyToVRAM(&sHud.window);
    Bg_ScheduleTilemapTransfer(BattleSystem_GetBgConfig(btlSubscreen->battleSys), BG_LAYER_MAIN_1);
    sHud.lastMenu = menu;
    sHud.lastCursorX = cx;
    sHud.lastCursorY = cy;
    return -1;
}

int BattleHud_TopTouchButton(BattleSubscreen *btlSubscreen, int x, int y)
{
    if (!BattleHud_IsEnabled() || btlSubscreen == NULL) {
        return -1;
    }
    return HudTouchButtonIndex(btlSubscreen, x, y);
}
