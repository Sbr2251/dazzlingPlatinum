#include "battle/wide_battle_hud.h"

#include <nitro.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "constants/battle.h"
#include "constants/battle/condition.h"
#include "constants/battle/moves.h"
#include "constants/charcode.h"
#include "constants/pokemon.h"

#include "battle/battle_context.h"
#include "battle/battle_hud.h"
#include "battle/battle_lib.h"
#include "battle/battle_system.h"
#include "battle/battle_textbox.h"
#include "battle/healthbox.h"
#include "bg_window.h"
#include "message_util.h"
#include "move_table.h"
#include "pokedex.h"
#include "pokemon.h"
#include "port/sim_wide.h"
#include "string_gf.h"

static char WideBattleChar(charcode_t ch)
{
    if (ch >= CHAR_0 && ch <= CHAR_9) return (char)('0' + ch - CHAR_0);
    if (ch >= CHAR_A && ch <= CHAR_Z) return (char)('A' + ch - CHAR_A);
    if (ch >= CHAR_a && ch <= CHAR_z) return (char)('a' + ch - CHAR_a);
    if (ch == CHAR_E_ACUTE) return 'E';
    if (ch == CHAR_e_ACUTE) return 'e';
    switch (ch) {
    case CHAR_SPACE: return ' ';
    case CHAR_EXCLAMATION: return '!';
    case CHAR_QUESTION: return '?';
    case CHAR_COMMA: return ',';
    case CHAR_PERIOD: return '.';
    case CHAR_DOT: return '.';
    case CHAR_SLASH: return '/';
    case CHAR_SINGLE_QUOTE_OPEN:
    case CHAR_SINGLE_QUOTE_CLOSE: return '\'';
    case CHAR_DOUBLE_QUOTE_OPEN:
    case CHAR_DOUBLE_QUOTE_CLOSE: return '"';
    case CHAR_PAREN_OPEN: return '(';
    case CHAR_PAREN_CLOSE: return ')';
    case CHAR_MALE: return 'M';
    case CHAR_FEMALE: return 'F';
    case CHAR_PLUS: return '+';
    case CHAR_MINUS: return '-';
    case CHAR_HASH: return '#';
    case CHAR_AMPERSAND: return '&';
    case CHAR_COLON: return ':';
    case CHAR_SEMICOLON: return ';';
    case CHAR_PERCENT: return '%';
    case CHAR_UNDERSCORE: return '_';
    default: return '?';
    }
}

static void WideBattleDecode(const charcode_t *src, char *dst, size_t size)
{
    size_t n = 0;
    if (size == 0) return;
    while (*src != CHAR_EOS && n + 1 < size) {
        dst[n++] = WideBattleChar(*src++);
    }
    dst[n] = '\0';
}

static void WideBattleDecodeString(const String *src, char *dst, size_t size)
{
    WideBattleDecode(src->data, dst, size);
}

static int WideBattleEffectiveness(int type, const BattleMon *defender)
{
    int multiplier = BattleSystem_TypeMatchupMultiplier((u8)type, defender->type1, defender->type2);
    return multiplier / 10; /* engine 0/10/20/40/80/160 -> contract 0/1/2/4/8/16 */
}

static void WideBattleStatus(u32 status, char out[8])
{
    const char *label = "";
    if (status & MON_CONDITION_BURN) label = "BRN";
    else if (status & MON_CONDITION_PARALYSIS) label = "PAR";
    else if (status & MON_CONDITION_TOXIC) label = "TOX";
    else if (status & MON_CONDITION_POISON) label = "PSN";
    else if (status & MON_CONDITION_SLEEP) label = "SLP";
    else if (status & MON_CONDITION_FREEZE) label = "FRZ";
    strcpy(out, label);
}

BOOL WideBattleHud_IsActive(void)
{
    const char *headless = getenv("SIM_HEADLESS");
    const char *forced = getenv("SIM_FX_WIDEBATTLE");

    if (headless != NULL && headless[0] != '\0' && headless[0] != '0') {
        if (forced == NULL || forced[0] == '\0' || forced[0] == '0') return FALSE;
    }
    if (SIM_WideBattle_IsEnabled == NULL || !SIM_WideBattle_IsEnabled()) return FALSE;
    /* The dedicated headless switch must not depend on SIM_FX_BATTLEHUD. */
    if (forced != NULL && forced[0] != '\0' && forced[0] != '0') return TRUE;
    return BattleHud_IsEnabled() || SIM_Wide_IsWideLayout();
}

static int WideBattleActiveBattler(BattleSystem *battleSys, BattleSubscreen *subscreen)
{
    if (subscreen == NULL || subscreen->activeMenuConfigIndex <= 0) return -1;
    return BattleSystem_GetBattlerOfType(battleSys, subscreen->battlerType);
}

static void WideBattleFillBattlers(SIM_WideBattleState *state, BattleSystem *battleSys,
    BattleContext *ctx, BattleSubscreen *subscreen)
{
    int active = WideBattleActiveBattler(battleSys, subscreen);
    int max = BattleSystem_GetMaxBattlers(battleSys);
    int i, s;

    for (i = 0; i < max && i < MAX_BATTLERS; i++) {
        BattleMon *mon = &ctx->battleMons[i];
        SIM_WideBattleBattler *out = &state->battlers[i];
        out->present = mon->species != 0;
        out->battlerIndex = i;
        out->isEnemy = i & 1;
        out->isActive = i == active;
        out->isAllySlot2 = i >= 2;
        WideBattleDecode(mon->nickname, out->name, sizeof(out->name));
        out->level = mon->level;
        out->gender = mon->gender;
        out->curHP = mon->curHP;
        out->maxHP = mon->maxHP;
        out->expFrac = -1.0f;
        if (!(i & 1) && mon->species != 0 && mon->level < MAX_POKEMON_LEVEL) {
            Pokemon *partyMon = BattleSystem_GetPartyPokemon(battleSys, i, ctx->selectedPartySlot[i]);
            u32 exp = Pokemon_GetValue(partyMon, MON_DATA_EXPERIENCE, NULL);
            u32 base = Pokemon_GetSpeciesBaseExpAt(mon->species, mon->level);
            u32 next = Pokemon_GetSpeciesBaseExpAt(mon->species, mon->level + 1);
            if (next > base && exp >= base) out->expFrac = (float)(exp - base) / (float)(next - base);
        }
        WideBattleStatus(mon->status, out->status);
        out->caught = (mon->species != 0 && (i & 1)
            && !(BattleSystem_GetBattleType(battleSys) & BATTLE_TYPE_TRAINER))
            ? Pokedex_HasCaughtSpecies(BattleSystem_GetPokedex(battleSys), mon->species) : 0;
        out->megaEvolved = ctx->megaEvolutionUsed[i] != 0;
        out->type1 = mon->type1;
        out->type2 = mon->type2;
        for (s = 0; s < 7; s++) out->stages[s] = mon->statBoosts[BATTLE_STAT_ATTACK + s] - 6;
    }
}

static int WideBattleRangeMask(int range, int active, int maxBattlers)
{
    int i, mask = 0;
    if (range == RANGE_ALL || (range & RANGE_ALL_ADJACENT)) {
        for (i = 0; i < maxBattlers; i++) if (i != active) mask |= 1 << i;
    } else if (range & (RANGE_ADJACENT_OPPONENTS | RANGE_OPPONENT_SIDE)) {
        for (i = 0; i < maxBattlers; i++) if ((i & 1) != (active & 1)) mask |= 1 << i;
    }
    return mask;
}

static void WideBattleFillMoves(SIM_WideBattleState *state, BattleSystem *battleSys,
    BattleContext *ctx, BattleSubscreen *subscreen)
{
    MoveSelectData *data = &subscreen->activeMenuData.moveData;
    int active = state->activeBattler;
    int foe = active >= 0 ? (active ^ 1) : BATTLER_ENEMY_1;
    int max = BattleSystem_GetMaxBattlers(battleSys);
    int i;

    state->megaAvailable = data->megaEvolutionAvailable != 0;
    state->megaArmed = active >= 0 && ctx->megaEvolutionTriggered[active] != 0;
    for (i = 0; i < 4; i++) {
        SIM_WideBattleMove *out = &state->moves[i];
        String *name;
        int range;
        out->moveId = data->moveIDs[i];
        out->effectiveness = -1;
        if (out->moveId == 0) continue;
        name = MessageUtil_MoveName(out->moveId, HEAP_ID_BATTLE);
        WideBattleDecodeString(name, out->name, sizeof(out->name));
        String_Free(name);
        out->type = MoveTable_LoadParam(out->moveId, MOVEATTRIBUTE_TYPE);
        out->category = MoveTable_LoadParam(out->moveId, MOVEATTRIBUTE_CLASS);
        out->power = MoveTable_LoadParam(out->moveId, MOVEATTRIBUTE_POWER);
        out->accuracy = MoveTable_LoadParam(out->moveId, MOVEATTRIBUTE_ACCURACY);
        out->curPP = data->currPP[i];
        out->maxPP = data->maxPP[i];
        if (!state->isDoubles && out->category != SIM_WIDEBATTLE_CAT_STATUS && ctx->battleMons[foe].species)
            out->effectiveness = WideBattleEffectiveness(out->type, &ctx->battleMons[foe]);
        range = MoveTable_LoadParam(out->moveId, MOVEATTRIBUTE_RANGE);
        out->rangeMask = WideBattleRangeMask(range, active, max);
        out->hitsAlly = active >= 0 && (out->rangeMask & (1 << (active ^ 2))) != 0;
    }
}

static void WideBattleFillTargets(SIM_WideBattleState *state, BattleSystem *battleSys,
    BattleContext *ctx, BattleSubscreen *subscreen)
{
    static const u8 spatialOrder[4] = { 1, 3, 0, 2 }; /* enemies above allies */
    TargetSelectData *data = &subscreen->activeMenuData.targetSelectData;
    u8 byType[6] = { 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF };
    int selectedGrid = subscreen->cursor.y * 2 + subscreen->cursor.x;
    int active = state->activeBattler;
    int move = active >= 0 ? ctx->moveSelected[active] : 0;
    int moveType = move ? MoveTable_LoadParam(move, MOVEATTRIBUTE_TYPE) : -1;
    int range = move ? MoveTable_LoadParam(move, MOVEATTRIBUTE_RANGE) : 0;
    int spreadMask = WideBattleRangeMask(range, active, BattleSystem_GetMaxBattlers(battleSys));
    int selectedBattler;
    int i;

    BattleSystem_SetBattlersByType(battleSys, byType);
    selectedBattler = byType[2 + selectedGrid];
    for (i = 0; i < 4; i++) {
        int battler = byType[2 + spatialOrder[i]];
        SIM_WideBattleTargetSlot *out = &state->targets[i];
        out->effectiveness = -1;
        if (battler == 0xFF || battler >= MAX_BATTLERS || !data->targetMonData[battler].isPresent) continue;
        out->valid = 1;
        out->battlerIndex = battler;
        out->isEnemy = battler & 1;
        out->isHitBySpread = (spreadMask & (1 << battler)) != 0;
        WideBattleDecode(ctx->battleMons[battler].nickname, out->name, sizeof(out->name));
        out->curHP = data->targetMonData[battler].curHP;
        out->maxHP = data->targetMonData[battler].maxHP;
        if (moveType >= 0 && MoveTable_LoadParam(move, MOVEATTRIBUTE_CLASS) != SIM_WIDEBATTLE_CAT_STATUS)
            out->effectiveness = WideBattleEffectiveness(moveType, &ctx->battleMons[battler]);
        if (battler == selectedBattler) state->selectedTargetMask |= 1 << battler;
    }
    if (spreadMask) state->selectedTargetMask = spreadMask;
}

static BOOL sMessageWindowHidden;

static void WideBattleSetMessageWindowHidden(BattleSystem *battleSys, BOOL hidden)
{
    Window *window;

    /* Battle message code can redraw BG1 after command selection starts, so
     * reassert the transparent region on every native-menu frame. */
    if (!hidden && !sMessageWindowHidden) return;
    window = BattleSystem_GetWindow(battleSys, 0);
    if (window == NULL) return;
    if (hidden) {
        u8 transparentTile[TILE_SIZE_4BPP] = { 0 };
        u8 layer = Window_GetBgLayer(window);

        /* The native prompt replaces the DS command prompt completely. BG1's
         * tile zero belongs to the arena and is opaque, so clearing the
         * window tilemap alone leaves a white rectangle. Reuse the textbox's
         * private cursor tile as transparent while the window is hidden. */
        BattleTextbox_Suspend();
        Bg_LoadTiles(window->bgConfig, layer, transparentTile, sizeof(transparentTile), 139);
        Bg_FillTilemapRect(window->bgConfig, layer, 139,
            0, Window_GetYPos(window) - 1,
            32, Window_GetHeight(window) + 3, 0);
        Bg_ScheduleTilemapTransfer(window->bgConfig, layer);
    } else {
        /* Restore a blank message surface for the next turn's battle text;
         * this also reloads the normal dark cursor tile. */
        Window_FillTilemap(window, 0xFF);
        BattleTextbox_DrawMessageWindow(window);
        BattleTextbox_Resume();
    }
    sMessageWindowHidden = hidden;
}

void WideBattleHud_SyncFrame(BattleSystem *battleSys, BattleSubscreen *subscreen)
{
    SIM_WideBattleState state;
    BattleContext *ctx;
    int menu;

    if (!WideBattleHud_IsActive() || battleSys == NULL || SIM_WideBattle_SetState == NULL) return;
    ctx = BattleSystem_GetBattleContext(battleSys);
    if (ctx == NULL) return;
    memset(&state, 0, sizeof(state));
    state.active = 1;
    state.isDoubles = (BattleSystem_GetBattleType(battleSys) & BATTLE_TYPE_DOUBLES) != 0;
    state.cursorX = subscreen != NULL ? subscreen->cursor.x : 0;
    state.cursorY = subscreen != NULL ? subscreen->cursor.y : 0;
    state.activeBattler = WideBattleActiveBattler(battleSys, subscreen);
    state.isSafari = (BattleSystem_GetBattleType(battleSys) & BATTLE_TYPE_SAFARI) != 0;
    state.isPalPark = (BattleSystem_GetBattleType(battleSys) & BATTLE_TYPE_PAL_PARK) != 0;
    WideBattleFillBattlers(&state, battleSys, ctx, subscreen);
    /* Catch boxes which were made visible before the native bridge activated. */
    for (menu = 0; menu < BattleSystem_GetMaxBattlers(battleSys); menu++) {
        HealthBox *healthbox = BattleSystem_GetHealthBox(battleSys, menu);
        if (healthbox != NULL) HealthBox_Enable(healthbox, FALSE);
    }

    menu = subscreen != NULL ? subscreen->activeMenuConfigIndex : 0;
    if (menu >= 1 && menu <= 10) {
        state.menu = SIM_WIDEBATTLE_MENU_ACTION;
        state.isPartnerTurn = subscreen->activeMenuData.actionData.isWaitingForPartner;
        strcpy(state.actionLabels[0], state.isSafari || state.isPalPark ? "BALL" : "FIGHT");
        strcpy(state.actionLabels[1], state.isSafari || state.isPalPark ? "MUD" : "POKEMON");
        strcpy(state.actionLabels[2], state.isSafari || state.isPalPark ? "BAIT" : "BAG");
        strcpy(state.actionLabels[3], state.isPartnerTurn ? "CANCEL" : "RUN");
        if (state.activeBattler >= 0)
            snprintf(state.prompt, sizeof(state.prompt), "What will %s do?", state.battlers[state.activeBattler].name);
    } else if (menu == 11) {
        state.menu = SIM_WIDEBATTLE_MENU_MOVE;
        WideBattleFillMoves(&state, battleSys, ctx, subscreen);
        if (state.activeBattler >= 0)
            snprintf(state.prompt, sizeof(state.prompt), "Choose a move for %s.", state.battlers[state.activeBattler].name);
    } else if (menu == 12) {
        state.menu = SIM_WIDEBATTLE_MENU_TARGET;
        WideBattleFillTargets(&state, battleSys, ctx, subscreen);
        strcpy(state.prompt, "Choose a target.");
    } else if (menu >= 13 && menu <= 17) {
        state.menu = SIM_WIDEBATTLE_MENU_YESNO;
        strcpy(state.actionLabels[0], "YES");
        strcpy(state.actionLabels[1], "NO");
    } else {
        state.menu = SIM_WIDEBATTLE_MENU_IDLE;
        state.activeBattler = -1;
    }
    WideBattleSetMessageWindowHidden(battleSys, state.menu != SIM_WIDEBATTLE_MENU_IDLE);
    SIM_WideBattle_SetState(&state);
}

int WideBattleHud_PollTouch(void)
{
    SIM_WideBattleEvent event = { -1 };
    if (!WideBattleHud_IsActive() || SIM_WideBattle_PollEvent == NULL) return -1;
    if (SIM_WideBattle_PollEvent(&event)) return event.buttonIndex;
    return -1;
}

void WideBattleHud_Clear(void)
{
    sMessageWindowHidden = FALSE;
    BattleTextbox_Resume();
    if (SIM_WideBattle_Clear != NULL) SIM_WideBattle_Clear();
}
