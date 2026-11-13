// Battle HUD (lane battlehud): top-screen mirror of the battle menus.
// See include/battle/battle_hud.h. Draws into a Window on BG_LAYER_MAIN_1
// (the battle message layer) anchored just above the message box
// (message box: tiles y=19..22; HUD: y=13..17), so the message stays
// readable underneath. Redraws only when the menu or cursor changes.

#include "battle/battle_hud.h"

#include <nitro.h>
#include <stdlib.h>
#include <string.h>

#include "battle/battle_context.h"
#include "battle/battle_system.h"
#include "port/sim_config_prj.h"
#include "port/sim_wide.h"

#include "bg_window.h"
#include "message.h"
#include "message_util.h"
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

typedef struct BattleHudState {
    Window window;
    BOOL windowAdded;
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

static void HudHide(void)
{
    if (sHud.windowAdded) {
        Window_Remove(&sHud.window);
        sHud.windowAdded = FALSE;
    }
    sHud.lastMenu = -2;
}

void BattleHud_Hide(BattleSubscreen *btlSubscreen)
{
    (void)btlSubscreen;
    HudHide();
    if (BattleHud_IsEnabled()) {
        SIM_Wide_SetBattleTouchNeeded(1);
    }
}

static void HudEnsureWindow(BattleSubscreen *btlSubscreen)
{
    if (sHud.windowAdded) {
        return;
    }
    // Anchored to the main-screen edges in tiles (32x24 screen), not to
    // 256px assumptions beyond the tile grid the message box itself uses.
    Window_Add(BattleSystem_GetBgConfig(btlSubscreen->battleSys), &sHud.window,
        BG_LAYER_MAIN_1, 1, 13, 30, 5, 11, 600);
    sHud.windowAdded = TRUE;
    sHud.lastMenu = -2;
}

static void HudPrint(BattleSubscreen *btlSubscreen, String *str, int x, int y, BOOL selected)
{
    if (selected) {
        String *cursor = String_Init(4, HEAP_ID_BATTLE);
        // ">" in the game font is charcode for '>' via String_SetCharcodeASCII? Use plain printer at x-8.
        String_Free(cursor);
        Text_AddPrinterWithParams(&sHud.window, FONT_SYSTEM, str, x, y, 0, NULL);
        // Selection marker: draw '>' glyph string built from the message bank is overkill;
        // the subscreen cursor sprite already shows selection on the bottom screen, and the
        // HUD bolds the selected entry by re-printing offset by (1,0) below.
        Text_AddPrinterWithParams(&sHud.window, FONT_SYSTEM, str, x + 1, y, 0, NULL);
    } else {
        Text_AddPrinterWithParams(&sHud.window, FONT_SYSTEM, str, x, y, 0, NULL);
    }
    (void)btlSubscreen;
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

    // 2x2 grid, later-game style: FIGHT top-left big, others around.
    HudPrint(btlSubscreen, fight, 16, 4, cx == 0 && cy == 0);
    HudPrint(btlSubscreen, party, 128, 4, cx == 1 && cy == 0);
    HudPrint(btlSubscreen, bag, 16, 22, cx == 0 && cy == 1);
    HudPrint(btlSubscreen, run, 128, 22, cx == 1 && cy == 1);

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
        int x = (i & 1) ? 128 : 16;
        int y = (i & 2) ? 20 : 4;
        BOOL selected = (cx == (i & 1) && cy == (i >> 1));
        if (moveData->moveIDs[i] == 0) {
            continue;
        }
        {
            String *name = MessageUtil_MoveName(moveData->moveIDs[i], HEAP_ID_BATTLE);
            HudPrint(btlSubscreen, name, x, y, selected);
            String_Free(name);
        }
        {
            String *fmt = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_CurPPOutOfMaxPP);
            String *pp = String_Init(16, HEAP_ID_BATTLE);
            StringTemplate_SetNumber(template, 0, moveData->currPP[i], 2, 1, 0);
            StringTemplate_SetNumber(template, 1, moveData->maxPP[i], 2, 1, 0);
            StringTemplate_Format(template, pp, fmt);
            Text_AddPrinterWithParams(&sHud.window, FONT_SYSTEM, pp, x + 64, y + 8, 0, NULL);
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
        Text_AddPrinterWithParams(&sHud.window, FONT_SYSTEM, mega, 16, 34, 0, NULL);
        String_Free(mega);
        {
            String *state = String_Init(8, HEAP_ID_BATTLE);
            // ON/OFF via message bank strings Yes/No is wrong; use PP-style numeric marker.
            StringTemplate_SetNumber(template, 0, on, 1, 1, 0);
            {
                String *fmt = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_CurPPOutOfMaxPP);
                (void)fmt;
                String_Free(fmt);
            }
            Text_AddPrinterWithParams(&sHud.window, FONT_SYSTEM, state, 64, 34, 0, NULL);
            String_Free(state);
        }
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
        int x = (i & 1) ? 128 : 16;
        int y = (i & 2) ? 20 : 4;
        BOOL selected = (btlSubscreen->cursor.x == (i & 1) && btlSubscreen->cursor.y == (i >> 1));
        if (!data->targetMonData[battlerIndex].isPresent) {
            continue;
        }
        {
            String *formatMsg = MessageLoader_GetNewString(msgLoader, BattleStrings_Text_HealthBoxPokemonName);
            Pokemon *partyMon = BattleSystem_GetPartyPokemon(btlSubscreen->battleSys, battlerIndex, data->targetMonData[battlerIndex].partySlot);
            StringTemplate_SetNickname(template, 0, Pokemon_GetBoxPokemon(partyMon));
            StringTemplate_Format(template, message, formatMsg);
            HudPrint(btlSubscreen, message, x, y, selected);
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

    HudPrint(btlSubscreen, yes, 96, 6, cy == 0);
    HudPrint(btlSubscreen, no, 96, 22, cy == 1);

    String_Free(yes);
    String_Free(no);
}

void BattleHud_Update(BattleSubscreen *btlSubscreen)
{
    int menu, cx, cy;

    if (!BattleHud_IsEnabled() || btlSubscreen == NULL) {
        HudHide();
        return;
    }

    menu = btlSubscreen->activeMenuConfigIndex;
    if (menu == HUD_MENU_IDLE || menu < 0) {
        HudHide();
        return;
    }

    // Wide layout: HUD is up on the top screen, bottom panel not needed.
    if (SIM_Wide_IsWideLayout()) {
        SIM_Wide_SetBattleTouchNeeded(0);
    }

    cx = btlSubscreen->cursor.x;
    cy = btlSubscreen->cursor.y;

    if (sHud.windowAdded && menu == sHud.lastMenu && cx == sHud.lastCursorX && cy == sHud.lastCursorY
        && menu != HUD_MENU_MOVE) {
        return;
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
            return;
        }
    }

    HudEnsureWindow(btlSubscreen);
    Window_FillTilemap(&sHud.window, 0xFF);
    Window_DrawMessageBoxWithScrollCursor(&sHud.window, FALSE, 1, 10);

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
    sHud.lastMenu = menu;
    sHud.lastCursorX = cx;
    sHud.lastCursorY = cy;
}

int BattleHud_TopTouchButton(BattleSubscreen *btlSubscreen, int x, int y)
{
    int menu, col, row;

    if (!BattleHud_IsEnabled() || btlSubscreen == NULL) {
        return -1;
    }
    menu = btlSubscreen->activeMenuConfigIndex;
    // HUD window at tiles (1,13) size 30x5 -> pixels x 8..248, y 104..144.
    if (x < 8 || x >= 248 || y < 104 || y >= 144) {
        return -1;
    }
    col = x < 128 ? 0 : 1;
    row = y < 124 ? 0 : 1;

    if (menu >= 13 && menu <= 17) {
        return row; // yes=0, no=1 in cursor terms
    }
    if (menu == HUD_MENU_MOVE || menu == HUD_MENU_TARGET || (menu >= 1 && menu <= 10)) {
        return row * 2 + col;
    }
    (void)menu;
    return -1;
}
