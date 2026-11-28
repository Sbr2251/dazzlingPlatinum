#include "battle/battle_bdsp_overlay.h"

#include <stdio.h>
#include <string.h>

#include "constants/battle.h"
#include "constants/battle/condition.h"
#include "constants/charcode.h"
#include "constants/heap.h"
#include "constants/items.h"
#include "constants/moves.h"
#include "constants/sound.h"
#include "constants/species.h"
#include "generated/battle_context_params.h"
#include "generated/genders.h"
#include "generated/move_attributes.h"
#include "generated/pokemon_data_params.h"
#include "generated/text_banks.h"

#include "battle/battle_context.h"
#include "battle/battle_events.h"
#include "battle/battle_hud.h"
#include "battle/battle_lib.h"
#include "battle/battle_system.h"
#include "battle_sub_menus/battle_bag_utils.h"

#include "bag.h"
#include "item.h"
#include "message.h"
#include "move_table.h"
#include "party.h"
#include "pc_boxes.h"
#include "pokemon.h"
#include "port/sim_battle3d.h"
#include "port/sim_wide.h"
#include "sound_playback.h"
#include "string_gf.h"
#include "system.h"
#include "totem_battle.h"

#define OVERLAY_MODE_NONE        0
#define OVERLAY_MODE_BAG         1
#define OVERLAY_MODE_PARTY       2
#define OVERLAY_MODE_SUMMARY     3
#define OVERLAY_MODE_PP_SELECT   4

#define OVERLAY_BAG_VISIBLE_ROWS 7
#define OVERLAY_BAG_TAB_COUNT    4
#define OVERLAY_ERROR_FRAMES     120

static const u8 sTabToPocket[OVERLAY_BAG_TAB_COUNT] = {
    BATTLE_POCKET_INDEX_RECOVER_HP_PP,
    BATTLE_POCKET_INDEX_POKE_BALLS,
    BATTLE_POCKET_INDEX_RECOVER_STATUS,
    BATTLE_POCKET_INDEX_BATTLE_ITEMS,
};

static const char *const sTabNames[OVERLAY_BAG_TAB_COUNT] = {
    "HP / PP",
    "Pok\xC3\xA9 Balls",
    "Status",
    "Battle",
};

typedef struct OverlayBagEntry {
    u16 itemId;
    u16 count;
    char name[32];
} OverlayBagEntry;

typedef struct OverlayPartyCache {
    SIM_HudHD_OverlayMon ui;
    u16 species;
    u16 moveIds[LEARNED_MOVES_MAX];
    BOOL isEgg;
} OverlayPartyCache;

typedef struct BattleBdspOverlayState {
    int mode;
    int ignoreInputFrames;
    BOOL decisionRejected;
    int errorTimer;
    char errorMsg[128];

    // Bag state
    BattleBagContext *bagCtx;
    int activeTab;
    int bagCursor[OVERLAY_BAG_TAB_COUNT];
    int bagScroll[OVERLAY_BAG_TAB_COUNT];
    int pocketCounts[OVERLAY_BAG_TAB_COUNT];
    OverlayBagEntry pocketItems[OVERLAY_BAG_TAB_COUNT][BATTLE_POCKET_SIZE];
    char cachedDesc[180];
    u16 cachedDescItemId;

    // Party / Summary state
    BattlePartyContext *partyCtx;
    int partyCount;
    int partyCursor;
    int confirmMode;
    int confirmCursor;
    int ppMoveCursor;
    char itemUseName[32];
    OverlayPartyCache mons[MAX_PARTY_SIZE];
} BattleBdspOverlayState;

static BattleBdspOverlayState sOv;

static void OverlayStringToUtf8(const String *str, char *out, int outSize)
{
    int pos = 0;
    u32 i;
    u32 len;
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

    // Opus B11: Bound scan by min(String_Length(str), 512) and validate skip lengths.
    len = String_Length(str);
    if (len > 512u) {
        len = 512u;
    }

    for (i = 0; i < len && pos < outSize - 1; i++) {
        charcode_t c = data[i];
        if (c == CHAR_EOS) {
            break;
        }
        if (c == CHAR_FORMAT_ARG) {
            if (i + 2u < len) {
                u16 argc = data[i + 2u];
                if (i + 2u + (u32)argc < len) {
                    i += 2u + (u32)argc;
                } else {
                    break;
                }
            } else {
                break;
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
            if (i + 1u < len) {
                i++;
            } else {
                break;
            }
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

static void OverlaySetError(const char *msg)
{
    if (msg == NULL) {
        sOv.errorMsg[0] = '\0';
        sOv.errorTimer = 0;
        return;
    }
    snprintf(sOv.errorMsg, sizeof(sOv.errorMsg), "%s", msg);
    sOv.errorTimer = OVERLAY_ERROR_FRAMES;
    Sound_PlayEffect(SEQ_SE_DP_BEEP_sseq);
}

static void OverlayClearError(void)
{
    sOv.errorMsg[0] = '\0';
    sOv.errorTimer = 0;
}

static int OverlayMapStatus(u32 statusCond, int curHp)
{
    if (curHp <= 0) {
        return SIM_HUDHD_STATUS_FNT;
    }
    if (statusCond & MON_CONDITION_TOXIC) {
        return SIM_HUDHD_STATUS_TOX;
    }
    if (statusCond & MON_CONDITION_POISON) {
        return SIM_HUDHD_STATUS_PSN;
    }
    if (statusCond & MON_CONDITION_BURN) {
        return SIM_HUDHD_STATUS_BRN;
    }
    if (statusCond & MON_CONDITION_PARALYSIS) {
        return SIM_HUDHD_STATUS_PAR;
    }
    if (statusCond & MON_CONDITION_SLEEP) {
        return SIM_HUDHD_STATUS_SLP;
    }
    if (statusCond & MON_CONDITION_FREEZE) {
        return SIM_HUDHD_STATUS_FRZ;
    }
    return SIM_HUDHD_STATUS_NONE;
}

static void OverlayLoadItemName(u16 itemId, enum HeapID heapID, char *out, int outSize)
{
    String *str = String_Init(64, heapID);
    Item_LoadName(str, itemId, heapID);
    OverlayStringToUtf8(str, out, outSize);
    String_Free(str);
}

static void OverlayRefreshBagDesc(void)
{
    int tab = sOv.activeTab;
    int count = sOv.pocketCounts[tab];
    int cur = sOv.bagCursor[tab];
    u16 itemId;

    if (sOv.bagCtx == NULL || count <= 0 || cur < 0 || cur >= count) {
        sOv.cachedDesc[0] = '\0';
        sOv.cachedDescItemId = ITEM_NONE;
        return;
    }

    itemId = sOv.pocketItems[tab][cur].itemId;
    if (itemId == sOv.cachedDescItemId && sOv.cachedDesc[0] != '\0') {
        return;
    }

    {
        String *str = String_Init(256, sOv.bagCtx->heapID);
        Item_LoadDescription(str, itemId, sOv.bagCtx->heapID);
        OverlayStringToUtf8(str, sOv.cachedDesc, sizeof(sOv.cachedDesc));
        String_Free(str);
        sOv.cachedDescItemId = itemId;
    }
}

static void OverlayClampBagCursor(int tab)
{
    int count = sOv.pocketCounts[tab];
    if (count <= 0) {
        sOv.bagCursor[tab] = 0;
        sOv.bagScroll[tab] = 0;
        return;
    }
    if (sOv.bagCursor[tab] < 0) {
        sOv.bagCursor[tab] = 0;
    } else if (sOv.bagCursor[tab] >= count) {
        sOv.bagCursor[tab] = count - 1;
    }
    if (sOv.bagCursor[tab] < sOv.bagScroll[tab]) {
        sOv.bagScroll[tab] = sOv.bagCursor[tab];
    } else if (sOv.bagCursor[tab] >= sOv.bagScroll[tab] + OVERLAY_BAG_VISIBLE_ROWS) {
        sOv.bagScroll[tab] = sOv.bagCursor[tab] - OVERLAY_BAG_VISIBLE_ROWS + 1;
    }
    if (sOv.bagScroll[tab] < 0) {
        sOv.bagScroll[tab] = 0;
    }
}

static void OverlayPopulateBagPockets(BattleBagContext *ctx)
{
    String *nameStr = String_Init(64, ctx->heapID);

    memset(sOv.pocketCounts, 0, sizeof(sOv.pocketCounts));
    memset(sOv.pocketItems, 0, sizeof(sOv.pocketItems));

    for (u32 pocket = 0; pocket < POCKET_MAX; pocket++) {
        u16 slot = 0;
        while (TRUE) {
            BagItem *bagItem = Bag_GetItemSlot(ctx->bag, (u16)pocket, slot);
            if (bagItem == NULL) {
                break;
            }
            if (bagItem->item != ITEM_NONE && bagItem->quantity != 0) {
                s32 mask = Item_LoadParam(bagItem->item, ITEM_PARAM_BATTLE_POCKET, ctx->heapID);
                BOOL matches[OVERLAY_BAG_TAB_COUNT];
                matches[0] = (mask & (BATTLE_POCKET_MASK_RECOVER_HP | BATTLE_POCKET_MASK_RECOVER_PP)) != 0;
                matches[1] = (mask & BATTLE_POCKET_MASK_POKE_BALLS) != 0;
                matches[2] = (mask & BATTLE_POCKET_MASK_RECOVER_STATUS) != 0;
                matches[3] = (mask & BATTLE_POCKET_MASK_BATTLE_ITEMS) != 0;

                for (int t = 0; t < OVERLAY_BAG_TAB_COUNT; t++) {
                    if (matches[t] && sOv.pocketCounts[t] < BATTLE_POCKET_SIZE) {
                        int idx = sOv.pocketCounts[t]++;
                        sOv.pocketItems[t][idx].itemId = bagItem->item;
                        sOv.pocketItems[t][idx].count = bagItem->quantity;
                        Item_LoadName(nameStr, bagItem->item, ctx->heapID);
                        OverlayStringToUtf8(nameStr, sOv.pocketItems[t][idx].name, sizeof(sOv.pocketItems[t][idx].name));
                    }
                }
            }
            slot++;
        }
    }

    String_Free(nameStr);
}

static void OverlaySaveBagCursor(BattleBagContext *ctx)
{
    BagCursor *cursor = BattleSystem_GetBagCursor(ctx->battleSys);
    if (cursor == NULL) {
        return;
    }
    BagCursor_SetBattleCurrentCategory(cursor, sTabToPocket[sOv.activeTab]);
}

static void OverlayUseBagItemConsume(BattleSystem *battleSys, u16 item, u16 category, enum HeapID heapID)
{
    if (item != ITEM_BLUE_FLUTE && item != ITEM_RED_FLUTE && item != ITEM_YELLOW_FLUTE) {
        Bag_TryRemoveItem(BattleSystem_GetBag(battleSys), item, 1, heapID);
    }
    Bag_SetLastBattleItemUsed(BattleSystem_GetBagCursor(battleSys), item, category);
}

static void OverlayCloseToBattle(void);

static BOOL OverlayTrySelectBagItem(u16 itemId, u8 pocketIndex)
{
    BattleBagContext *ctx = sOv.bagCtx;
    BattleSystem *battleSys = ctx->battleSys;

    if (pocketIndex == BATTLE_POCKET_INDEX_POKE_BALLS) {
        if (BattleSystem_GetBattleType(battleSys) & BATTLE_TYPE_TRAINER) {
            OverlaySetError("You can't catch a Trainer's Pokemon!");
            return FALSE;
        }
        if (TotemBattle_IsActive(battleSys)) {
            OverlaySetError("You can't catch a Totem Pokemon!");
            return FALSE;
        }
        if (ctx->hasTwoOpponents == TRUE) {
            OverlaySetError("It's impossible to aim when there are two Pokemon!");
            return FALSE;
        }
        if (ctx->opponentHidden == TRUE) {
            OverlaySetError("It's impossible to aim at a hidden Pokemon!");
            return FALSE;
        }
        if (ctx->opponentSubstituted == TRUE) {
            OverlaySetError("You can't throw a Ball at a substitute!");
            return FALSE;
        }
        {
            Party *party = BattleSystem_GetParty(battleSys, ctx->battler);
            PCBoxes *pcBoxes = BattleSystem_GetPCBoxes(battleSys);
            if (Party_GetCurrentCount(party) == MAX_PARTY_SIZE && PCBoxes_FirstEmptyBox(pcBoxes) == MAX_PC_BOXES) {
                OverlaySetError("There is no room left in the PC Boxes!");
                return FALSE;
            }
        }
        // Poke Balls are consumed by the battle script when thrown (matches battle_bag.c).
        ctx->selectedBattleBagItem = itemId;
        ctx->selectedBattleBagPocket = BATTLE_POCKET_INDEX_POKE_BALLS;
        OverlaySaveBagCursor(ctx);
        Sound_PlayEffect(SEQ_SE_DP_DECIDE_sseq);
        ctx->battleBagExited = TRUE;
        OverlayCloseToBattle();
        return TRUE;
    }

    if (pocketIndex == BATTLE_POCKET_INDEX_BATTLE_ITEMS) {
        int partySlot = BattleContext_Get(battleSys, BattleSystem_GetBattleContext(battleSys), BATTLECTX_SELECTED_PARTY_SLOT, ctx->battler);
        u32 itemBattleUse = (u32)Item_LoadParam(itemId, ITEM_PARAM_BATTLE_USE_CATEGORY, ctx->heapID);

        if (ctx->embargoRemainingTurns != 0 && itemId != ITEM_GUARD_SPEC && itemBattleUse != 3) {
            OverlaySetError("Embargo prevents using that item!");
            return FALSE;
        }
        if (BattleSystem_UseBagItem(battleSys, ctx->battler, partySlot, 0, itemId) == TRUE) {
            Bag_TryRemoveItem(BattleSystem_GetBag(battleSys), itemId, 1, ctx->heapID);
            Bag_SetLastBattleItemUsed(BattleSystem_GetBagCursor(battleSys), itemId, BATTLE_POCKET_INDEX_BATTLE_ITEMS);
            ctx->selectedBattleBagItem = itemId;
            ctx->selectedBattleBagPocket = BATTLE_POCKET_INDEX_BATTLE_ITEMS;
            OverlaySaveBagCursor(ctx);
            Sound_PlayEffect(SEQ_SE_DP_DECIDE_sseq);
            ctx->battleBagExited = TRUE;
            OverlayCloseToBattle();
            return TRUE;
        }
        if (itemBattleUse == 3) {
            if (!(BattleSystem_GetBattleType(battleSys) & BATTLE_TYPE_TRAINER) && !TotemBattle_IsActive(battleSys)) {
                Bag_TryRemoveItem(BattleSystem_GetBag(battleSys), itemId, 1, ctx->heapID);
                Bag_SetLastBattleItemUsed(BattleSystem_GetBagCursor(battleSys), itemId, BATTLE_POCKET_INDEX_BATTLE_ITEMS);
                ctx->selectedBattleBagItem = itemId;
                ctx->selectedBattleBagPocket = BATTLE_POCKET_INDEX_BATTLE_ITEMS;
                OverlaySaveBagCursor(ctx);
                Sound_PlayEffect(SEQ_SE_DP_DECIDE_sseq);
                ctx->battleBagExited = TRUE;
                OverlayCloseToBattle();
                return TRUE;
            }
            OverlaySetError("You can't use that here!");
            return FALSE;
        }
        OverlaySetError("It won't have any effect.");
        return FALSE;
    }

    // HP/PP Restore or Status Restore: hand off to inline Party target picker via Task_PlayerShowBagMenu case 4.
    ctx->selectedBattleBagItem = itemId;
    ctx->selectedBattleBagPocket = pocketIndex;
    OverlaySaveBagCursor(ctx);
    Sound_PlayEffect(SEQ_SE_DP_DECIDE_sseq);
    ctx->battleBagExited = TRUE;
    OverlayCloseToBattle();
    return TRUE;
}

static BOOL OverlayIs2v2Battle(BattleSystem *battleSys)
{
    u32 battleType = BattleSystem_GetBattleType(battleSys);
    if (battleType != BATTLE_TYPE_AI_PARTNER
        && battleType != (BATTLE_TYPE_TRAINER_DOUBLES | BATTLE_TYPE_2vs2 | BATTLE_TYPE_AI)
        && (battleType & BATTLE_TYPE_2vs2)) {
        return TRUE;
    }
    return FALSE;
}

static BOOL OverlayIsPartnersPokemon(BattlePartyContext *ctx, int slot)
{
    if (!OverlayIs2v2Battle(ctx->battleSys)) {
        return FALSE;
    }
    if (BattleSystem_GetBattlerType(ctx->battleSys, ctx->battler) == BATTLER_TYPE_PLAYER_SIDE_SLOT_1) {
        return (slot & 1) != 0;
    }
    return (slot & 1) == 0;
}

static BOOL OverlayCheckCanSwitch(BattlePartyContext *ctx, int slot, char *errBuf, int errSize)
{
    OverlayPartyCache *mon = &sOv.mons[slot];

    if (!mon->ui.valid) {
        snprintf(errBuf, (size_t)errSize, "There is no Pokemon in that slot!");
        return FALSE;
    }
    if (OverlayIsPartnersPokemon(ctx, slot)) {
        snprintf(errBuf, (size_t)errSize, "You can't switch out your partner's Pokemon!");
        return FALSE;
    }
    if (mon->ui.hp <= 0) {
        snprintf(errBuf, (size_t)errSize, "%s has no energy left to battle!", mon->ui.name);
        return FALSE;
    }
    if (ctx->pokemonPartySlots[slot] == ctx->playerPokemonPartySlot
        || ctx->pokemonPartySlots[slot] == ctx->partnerPokemonPartySlot) {
        snprintf(errBuf, (size_t)errSize, "%s is already in battle!", mon->ui.name);
        return FALSE;
    }
    if (mon->isEgg) {
        snprintf(errBuf, (size_t)errSize, "An Egg can't battle!");
        return FALSE;
    }
    if (ctx->doubleBattleFirstSelectedPartySlot != 6
        && ctx->pokemonPartySlots[slot] == ctx->doubleBattleFirstSelectedPartySlot) {
        snprintf(errBuf, (size_t)errSize, "%s has already been selected!", mon->ui.name);
        return FALSE;
    }
    if (ctx->moveToLearn != MOVE_NONE) {
        snprintf(errBuf, (size_t)errSize, "Your active Pokemon can't be switched out!");
        return FALSE;
    }
    return TRUE;
}

static void OverlayPopulateParty(BattlePartyContext *ctx)
{
    MessageLoader *abilityLoader = MessageLoader_Init(MSG_LOADER_LOAD_ON_DEMAND, NARC_INDEX_MSGDATA__PL_MSG, TEXT_BANK_ABILITY_NAMES, ctx->heapID);
    MessageLoader *moveLoader = MessageLoader_Init(MSG_LOADER_LOAD_ON_DEMAND, NARC_INDEX_MSGDATA__PL_MSG, TEXT_BANK_MOVE_NAMES, ctx->heapID);
    String *str = String_Init(64, ctx->heapID);
    int count = Party_GetCurrentCount(ctx->party);

    if (count > MAX_PARTY_SIZE) {
        count = MAX_PARTY_SIZE;
    }

    memset(sOv.mons, 0, sizeof(sOv.mons));
    sOv.partyCount = count;

    for (int i = 0; i < count; i++) {
        Pokemon *mon = Party_GetPokemonBySlotIndex(ctx->party, i);
        OverlayPartyCache *dst = &sOv.mons[i];
        u16 species;
        BOOL isEgg;
        u32 gender;
        u32 status;
        u16 heldItem;
        u16 ability;

        if (mon == NULL) {
            continue;
        }
        species = (u16)Pokemon_GetValue(mon, MON_DATA_SPECIES, NULL);
        if (species == SPECIES_NONE) {
            continue;
        }
        isEgg = Pokemon_GetValue(mon, MON_DATA_IS_EGG, NULL) != 0;

        dst->species = species;
        dst->isEgg = isEgg;
        dst->ui.valid = 1;

        if (isEgg) {
            snprintf(dst->ui.name, sizeof(dst->ui.name), "Egg");
        } else {
            Pokemon_GetValue(mon, MON_DATA_NICKNAME_STRING, str);
            OverlayStringToUtf8(str, dst->ui.name, sizeof(dst->ui.name));
        }

        gender = Pokemon_GetValue(mon, MON_DATA_GENDER, NULL);
        if (isEgg || gender == GENDER_NONE) {
            dst->ui.gender = SIM_HUDHD_GENDER_NONE;
        } else if (gender == GENDER_MALE) {
            dst->ui.gender = SIM_HUDHD_GENDER_MALE;
        } else if (gender == GENDER_FEMALE) {
            dst->ui.gender = SIM_HUDHD_GENDER_FEMALE;
        } else {
            dst->ui.gender = SIM_HUDHD_GENDER_NONE;
        }

        dst->ui.level = (int)Pokemon_GetValue(mon, MON_DATA_LEVEL, NULL);
        dst->ui.hp = (int)Pokemon_GetValue(mon, MON_DATA_HP, NULL);
        dst->ui.maxHp = (int)Pokemon_GetValue(mon, MON_DATA_MAX_HP, NULL);
        status = Pokemon_GetValue(mon, MON_DATA_STATUS, NULL);
        dst->ui.status = isEgg ? SIM_HUDHD_STATUS_NONE : OverlayMapStatus(status, dst->ui.hp);
        dst->ui.isFainted = (!isEgg && dst->ui.hp <= 0) ? 1 : 0;
        dst->ui.isActive = (ctx->pokemonPartySlots[i] == ctx->playerPokemonPartySlot
            || ctx->pokemonPartySlots[i] == ctx->partnerPokemonPartySlot) ? 1 : 0;
        dst->ui.selectable = (!isEgg && !OverlayIsPartnersPokemon(ctx, i)) ? 1 : 0;

        heldItem = (u16)Pokemon_GetValue(mon, MON_DATA_HELD_ITEM, NULL);
        if (heldItem != ITEM_NONE && !isEgg) {
            Item_LoadName(str, heldItem, ctx->heapID);
            OverlayStringToUtf8(str, dst->ui.heldItem, sizeof(dst->ui.heldItem));
        } else {
            snprintf(dst->ui.heldItem, sizeof(dst->ui.heldItem), "None");
        }

        ability = (u16)Pokemon_GetValue(mon, MON_DATA_ABILITY, NULL);
        if (!isEgg && ability != 0) {
            MessageLoader_GetString(abilityLoader, ability, str);
            OverlayStringToUtf8(str, dst->ui.ability, sizeof(dst->ui.ability));
        } else {
            snprintf(dst->ui.ability, sizeof(dst->ui.ability), "---");
        }

        dst->ui.stats[0] = dst->ui.maxHp;
        dst->ui.stats[1] = (int)Pokemon_GetValue(mon, MON_DATA_ATK, NULL);
        dst->ui.stats[2] = (int)Pokemon_GetValue(mon, MON_DATA_DEF, NULL);
        dst->ui.stats[3] = (int)Pokemon_GetValue(mon, MON_DATA_SP_ATK, NULL);
        dst->ui.stats[4] = (int)Pokemon_GetValue(mon, MON_DATA_SP_DEF, NULL);
        dst->ui.stats[5] = (int)Pokemon_GetValue(mon, MON_DATA_SPEED, NULL);

        for (int m = 0; m < LEARNED_MOVES_MAX; m++) {
            u16 move = (u16)Pokemon_GetValue(mon, MON_DATA_MOVE1 + m, NULL);
            dst->moveIds[m] = move;
            if (move != MOVE_NONE && !isEgg) {
                MessageLoader_GetString(moveLoader, move, str);
                OverlayStringToUtf8(str, dst->ui.moveNames[m], sizeof(dst->ui.moveNames[m]));
                dst->ui.moveTypes[m] = (int)MoveTable_LoadParam(move, MOVEATTRIBUTE_TYPE);
                dst->ui.movePp[m] = (int)Pokemon_GetValue(mon, MON_DATA_MOVE1_PP + m, NULL);
                dst->ui.moveMaxPp[m] = (int)Pokemon_GetValue(mon, MON_DATA_MOVE1_MAX_PP + m, NULL);
            } else {
                dst->ui.moveNames[m][0] = '\0';
                dst->ui.moveTypes[m] = 0;
                dst->ui.movePp[m] = 0;
                dst->ui.moveMaxPp[m] = 0;
            }
        }
    }

    String_Free(str);
    MessageLoader_Free(moveLoader);
    MessageLoader_Free(abilityLoader);
}

static BOOL OverlayApplyItemOnPartyMon(BattlePartyContext *ctx, int slot, int moveSlot)
{
    u16 item = ctx->selectedBattleBagItem;
    int oldHp = sOv.mons[slot].ui.hp;
    BOOL isActive = sOv.mons[slot].ui.isActive != 0;

    if ((slot == 0 && ctx->embargoRemainingTurns[0] != 0)
        || (slot == 1 && ctx->embargoRemainingTurns[1] != 0)) {
        OverlaySetError("Embargo prevents using items on this Pokemon!");
        return FALSE;
    }
    if (sOv.mons[slot].isEgg) {
        OverlaySetError("It won't have any effect.");
        return FALSE;
    }

    if (BattleSystem_UseBagItem(ctx->battleSys, ctx->battler, ctx->pokemonPartySlots[slot], moveSlot, item) == TRUE) {
        if (isActive && Item_LoadParam(item, ITEM_PARAM_REVIVE, ctx->heapID) == FALSE) {
            Pokemon *realMon = BattleSystem_GetPartyPokemon(ctx->battleSys, ctx->battler, ctx->pokemonPartySlots[slot]);
            int newHp = (realMon != NULL) ? (int)Pokemon_GetValue(realMon, MON_DATA_HP, NULL) : oldHp;
            ctx->currentDamage = (newHp > oldHp) ? (u16)(newHp - oldHp) : 0;
        } else {
            ctx->currentDamage = 0;
        }

        OverlayUseBagItemConsume(ctx->battleSys, item, ctx->selectedBattleBagPocket, ctx->heapID);
        Sound_PlayEffect(SEQ_SE_DP_KAIFUKU_sseq);
        ctx->selectedPartyIndex = (u8)slot;
        ctx->selectedMoveSlot = (u8)moveSlot;
        ctx->battlePartyExited = TRUE;
        OverlayCloseToBattle();
        return TRUE;
    }

    OverlaySetError("It won't have any effect.");
    return FALSE;
}

static int OverlayStepValidPartySlot(int cur, int delta)
{
    for (int step = 1; step <= MAX_PARTY_SIZE; step++) {
        int cand = (cur + delta * step + MAX_PARTY_SIZE * 4) % MAX_PARTY_SIZE;
        if (sOv.mons[cand].ui.valid) {
            return cand;
        }
    }
    return cur;
}

static int OverlayMovePartyGrid(int cur, u32 keys)
{
    int next = cur;

    if (keys & PAD_KEY_LEFT) {
        int partner = cur ^ 1;
        if (partner >= 0 && partner < MAX_PARTY_SIZE && sOv.mons[partner].ui.valid) {
            next = partner;
        } else {
            next = OverlayStepValidPartySlot(cur, -1);
        }
    } else if (keys & PAD_KEY_RIGHT) {
        int partner = cur ^ 1;
        if (partner >= 0 && partner < MAX_PARTY_SIZE && sOv.mons[partner].ui.valid) {
            next = partner;
        } else {
            next = OverlayStepValidPartySlot(cur, 1);
        }
    } else if (keys & PAD_KEY_UP) {
        int cand = cur - 2;
        if (cand < 0) {
            cand += 6;
        }
        if (cand >= 0 && cand < MAX_PARTY_SIZE && sOv.mons[cand].ui.valid) {
            next = cand;
        } else {
            next = OverlayStepValidPartySlot(cur, -1);
        }
    } else if (keys & PAD_KEY_DOWN) {
        int cand = cur + 2;
        if (cand >= 6) {
            cand -= 6;
        }
        if (cand >= 0 && cand < MAX_PARTY_SIZE && sOv.mons[cand].ui.valid) {
            next = cand;
        } else {
            next = OverlayStepValidPartySlot(cur, 1);
        }
    }

    return next;
}

static BOOL OverlayRectHit(float x, float y, float w, float h, int tx, int ty)
{
    return tx >= (int)x && tx < (int)(x + w) && ty >= (int)y && ty < (int)(y + h);
}

static void OverlayCloseToBattle(void)
{
    sOv.mode = OVERLAY_MODE_NONE;
    sOv.bagCtx = NULL;
    sOv.partyCtx = NULL;
    SIM_Wide_SetMainTouchEnabled(0);
}

static void OverlayCancelBag(BattleBagContext *ctx)
{
    ctx->selectedBattleBagItem = ITEM_NONE;
    ctx->selectedBattleBagPocket = BATTLE_POCKET_INDEX_NONE;
    OverlaySaveBagCursor(ctx);
    Sound_PlayEffect(SEQ_SE_DP_DECIDE_sseq);
    ctx->battleBagExited = TRUE;
    OverlayCloseToBattle();
}

static void OverlayConfirmPartySlot(BattlePartyContext *ctx)
{
    if (!sOv.mons[sOv.partyCursor].ui.valid) {
        return;
    }
    if (ctx->battlePartyMode == BATTLE_PARTY_MODE_USE_ITEM) {
        u16 item = ctx->selectedBattleBagItem;
        if (Item_LoadParam(item, ITEM_PARAM_PP_RESTORE, ctx->heapID) != FALSE
            && Item_LoadParam(item, ITEM_PARAM_PP_RESTORE_ALL, ctx->heapID) == FALSE
            && !sOv.mons[sOv.partyCursor].isEgg) {
            if ((sOv.partyCursor == 0 && ctx->embargoRemainingTurns[0] != 0)
                || (sOv.partyCursor == 1 && ctx->embargoRemainingTurns[1] != 0)) {
                OverlaySetError("Embargo prevents using items on this Pok\xC3\xA9mon!");
                return;
            }
            sOv.ppMoveCursor = 0;
            for (int m = 0; m < LEARNED_MOVES_MAX; m++) {
                if (sOv.mons[sOv.partyCursor].moveIds[m] != MOVE_NONE) {
                    sOv.ppMoveCursor = m;
                    break;
                }
            }
            Sound_PlayEffect(SEQ_SE_DP_DECIDE_sseq);
            sOv.mode = OVERLAY_MODE_PP_SELECT;
            return;
        }
        OverlayApplyItemOnPartyMon(ctx, sOv.partyCursor, 0);
        return;
    }

    Sound_PlayEffect(SEQ_SE_DP_DECIDE_sseq);
    sOv.confirmMode = 1;
    sOv.confirmCursor = 0;
}

static void OverlayExecutePartyConfirm(BattlePartyContext *ctx)
{
    if (sOv.confirmCursor == 0) {
        char err[128];
        if (OverlayCheckCanSwitch(ctx, sOv.partyCursor, err, sizeof(err))) {
            Sound_PlayEffect(SEQ_SE_DP_DECIDE_sseq);
            ctx->selectedPartyIndex = (u8)sOv.partyCursor;
            ctx->battlePartyExited = TRUE;
            OverlayCloseToBattle();
        } else {
            sOv.confirmMode = 0;
            OverlaySetError(err);
        }
    } else if (sOv.confirmCursor == 1) {
        if (sOv.mons[sOv.partyCursor].isEgg) {
            sOv.confirmMode = 0;
            OverlaySetError("Cannot view summary for an Egg.");
        } else {
            Sound_PlayEffect(SEQ_SE_DP_DECIDE_sseq);
            sOv.confirmMode = 0;
            sOv.mode = OVERLAY_MODE_SUMMARY;
        }
    } else {
        Sound_PlayEffect(SEQ_SE_DP_DECIDE_sseq);
        sOv.confirmMode = 0;
    }
}

static void OverlayCancelParty(BattlePartyContext *ctx)
{
    if (ctx->battlePartyMode == BATTLE_PARTY_MODE_SELECT_POKEMON_NO_CANCEL) {
        OverlaySetError("Choose a Pok\xC3\xA9mon to send out!");
        return;
    }
    Sound_PlayEffect(SEQ_SE_DP_DECIDE_sseq);
    ctx->selectedPartyIndex = 6;
    ctx->battlePartyExited = TRUE;
    OverlayCloseToBattle();
}

static void OverlayTickBag(void)
{
    BattleBagContext *ctx = sOv.bagCtx;
    u32 pressed;
    u32 repeat;
    int tx = 0, ty = 0;

    if (ctx == NULL) {
        OverlayCloseToBattle();
        return;
    }

    // Automated battle decision queue support (mirrors battle_bag.c).
    if (!sOv.decisionRejected) {
        BattleDecision dec;
        if (BattleDecisions_Peek(ctx->battler, &dec) && dec.action == BATTLE_DECISION_ITEM) {
            BOOL found = FALSE;
            for (int t = 0; t < OVERLAY_BAG_TAB_COUNT && !found; t++) {
                for (int i = 0; i < sOv.pocketCounts[t]; i++) {
                    if (sOv.pocketItems[t][i].itemId == (u16)dec.itemId) {
                        found = TRUE;
                        sOv.activeTab = t;
                        sOv.bagCursor[t] = i;
                        OverlayClampBagCursor(t);
                        OverlayRefreshBagDesc();
                        if (!OverlayTrySelectBagItem((u16)dec.itemId, sTabToPocket[t])) {
                            sOv.decisionRejected = TRUE;
                            BattleDecisions_MarkDone(ctx->battler, BATTLE_DECISION_ITEM);
                        }
                        return;
                    }
                }
            }
            if (!found) {
                sOv.decisionRejected = TRUE;
                BattleDecisions_MarkDone(ctx->battler, BATTLE_DECISION_ITEM);
            }
        }
    }

    // Direct touch / mouse tap support on the 342x192 HD canvas.
    if (SIM_Wide_PollMainTouch(&tx, &ty)) {
        OverlayClearError();
        if (OverlayRectHit(286.0f, 175.0f, 52.0f, 17.0f, tx, ty)) {
            OverlayCancelBag(ctx);
            return;
        }
        if (OverlayRectHit(6.0f, 24.0f, 20.0f, 18.0f, tx, ty)) {
            sOv.activeTab = (sOv.activeTab + OVERLAY_BAG_TAB_COUNT - 1) % OVERLAY_BAG_TAB_COUNT;
            OverlayClampBagCursor(sOv.activeTab);
            OverlayRefreshBagDesc();
            Sound_PlayEffect(SE_CONFIRM_sseq_3);
            return;
        }
        if (OverlayRectHit(316.0f, 24.0f, 20.0f, 18.0f, tx, ty)) {
            sOv.activeTab = (sOv.activeTab + 1) % OVERLAY_BAG_TAB_COUNT;
            OverlayClampBagCursor(sOv.activeTab);
            OverlayRefreshBagDesc();
            Sound_PlayEffect(SE_CONFIRM_sseq_3);
            return;
        }
        {
            const float tabsX = 26.5f;
            const float gap = 4.0f;
            const float tabW = (342.0f - 53.0f - gap * (OVERLAY_BAG_TAB_COUNT - 1)) / (float)OVERLAY_BAG_TAB_COUNT;
            for (int t = 0; t < OVERLAY_BAG_TAB_COUNT; t++) {
                float tabX = tabsX + t * (tabW + gap);
                if (OverlayRectHit(tabX, 24.0f, tabW, 17.0f, tx, ty)) {
                    if (sOv.activeTab != t) {
                        sOv.activeTab = t;
                        OverlayClampBagCursor(t);
                        OverlayRefreshBagDesc();
                        Sound_PlayEffect(SE_CONFIRM_sseq_3);
                    }
                    return;
                }
            }
        }
        {
            int tab = sOv.activeTab;
            int total = sOv.pocketCounts[tab];
            int scroll = sOv.bagScroll[tab];
            // Left card "Use" button.
            if (total > 0 && OverlayRectHit(17.0f, 148.0f, 100.0f, 18.0f, tx, ty)) {
                OverlayTrySelectBagItem(sOv.pocketItems[tab][sOv.bagCursor[tab]].itemId, sTabToPocket[tab]);
                return;
            }
            // Right item list rows.
            for (int row = 0; row < OVERLAY_BAG_VISIBLE_ROWS && (scroll + row) < total; row++) {
                float ry = 50.0f + row * 16.6f;
                if (OverlayRectHit(135.0f, ry, 192.0f, 15.5f, tx, ty)) {
                    int idx = scroll + row;
                    if (idx == sOv.bagCursor[tab]) {
                        OverlayTrySelectBagItem(sOv.pocketItems[tab][idx].itemId, sTabToPocket[tab]);
                    } else {
                        sOv.bagCursor[tab] = idx;
                        OverlayClampBagCursor(tab);
                        OverlayRefreshBagDesc();
                        Sound_PlayEffect(SE_CONFIRM_sseq_3);
                    }
                    return;
                }
            }
        }
        return;
    }

    pressed = gSystem.pressedKeys;
    repeat = gSystem.pressedKeysRepeatable;

    if (pressed != 0) {
        OverlayClearError();
    }

    // Switch battle pockets via L/R or LEFT/RIGHT.
    if (pressed & (PAD_BUTTON_L | PAD_KEY_LEFT)) {
        sOv.activeTab = (sOv.activeTab + OVERLAY_BAG_TAB_COUNT - 1) % OVERLAY_BAG_TAB_COUNT;
        OverlayClampBagCursor(sOv.activeTab);
        OverlayRefreshBagDesc();
        Sound_PlayEffect(SE_CONFIRM_sseq_3);
        return;
    }
    if (pressed & (PAD_BUTTON_R | PAD_KEY_RIGHT)) {
        sOv.activeTab = (sOv.activeTab + 1) % OVERLAY_BAG_TAB_COUNT;
        OverlayClampBagCursor(sOv.activeTab);
        OverlayRefreshBagDesc();
        Sound_PlayEffect(SE_CONFIRM_sseq_3);
        return;
    }

    // Scroll items via UP/DOWN.
    {
        int tab = sOv.activeTab;
        int count = sOv.pocketCounts[tab];
        if (count > 0 && (repeat & PAD_KEY_UP)) {
            sOv.bagCursor[tab] = (sOv.bagCursor[tab] + count - 1) % count;
            OverlayClampBagCursor(tab);
            OverlayRefreshBagDesc();
            Sound_PlayEffect(SE_CONFIRM_sseq_3);
            return;
        }
        if (count > 0 && (repeat & PAD_KEY_DOWN)) {
            sOv.bagCursor[tab] = (sOv.bagCursor[tab] + 1) % count;
            OverlayClampBagCursor(tab);
            OverlayRefreshBagDesc();
            Sound_PlayEffect(SE_CONFIRM_sseq_3);
            return;
        }
    }

    // Cancel back to Battle Action menu.
    if (pressed & PAD_BUTTON_B) {
        OverlayCancelBag(ctx);
        return;
    }

    // Select item with A.
    if (pressed & PAD_BUTTON_A) {
        int tab = sOv.activeTab;
        int count = sOv.pocketCounts[tab];
        if (count <= 0) {
            OverlaySetError("There are no items in this pocket.");
            return;
        }
        OverlayTrySelectBagItem(sOv.pocketItems[tab][sOv.bagCursor[tab]].itemId, sTabToPocket[tab]);
    }
}

static void OverlayTickParty(void)
{
    BattlePartyContext *ctx = sOv.partyCtx;
    u32 pressed;
    u32 repeat;
    int tx = 0, ty = 0;

    if (ctx == NULL) {
        OverlayCloseToBattle();
        return;
    }

    // Automated battle decision queue support (mirrors battle_party.c).
    if (!sOv.decisionRejected) {
        BattleDecision dec;
        if (ctx->battlePartyMode == BATTLE_PARTY_MODE_USE_ITEM
            && BattleDecisions_PeekAction(ctx->battler, BATTLE_DECISION_ITEM, &dec)) {
            BOOL found = FALSE;
            for (int pi = 0; pi < MAX_PARTY_SIZE; pi++) {
                if (sOv.mons[pi].ui.valid && ctx->pokemonPartySlots[pi] == dec.partySlot) {
                    u16 item = ctx->selectedBattleBagItem;
                    BOOL isSinglePp = (Item_LoadParam(item, ITEM_PARAM_PP_RESTORE, ctx->heapID) != FALSE
                        && Item_LoadParam(item, ITEM_PARAM_PP_RESTORE_ALL, ctx->heapID) == FALSE
                        && !sOv.mons[pi].isEgg);
                    found = TRUE;
                    sOv.partyCursor = pi;
                    if (isSinglePp) {
                        int moveSlot = -1;
                        if (dec.moveSlot >= 0 && dec.moveSlot < LEARNED_MOVES_MAX
                            && sOv.mons[pi].moveIds[dec.moveSlot] != MOVE_NONE) {
                            moveSlot = dec.moveSlot;
                        } else if (dec.moveId != MOVE_NONE) {
                            for (int m = 0; m < LEARNED_MOVES_MAX; m++) {
                                if (sOv.mons[pi].moveIds[m] == (u16)dec.moveId) {
                                    moveSlot = m;
                                    break;
                                }
                            }
                        }
                        if (moveSlot < 0) {
                            // No explicit valid move slot: consume queued decision and open interactive PP picker.
                            sOv.decisionRejected = TRUE;
                            BattleDecisions_MarkDone(ctx->battler, BATTLE_DECISION_ITEM);
                            OverlayConfirmPartySlot(ctx);
                            return;
                        }
                        if (!OverlayApplyItemOnPartyMon(ctx, pi, moveSlot)) {
                            sOv.decisionRejected = TRUE;
                            BattleDecisions_MarkDone(ctx->battler, BATTLE_DECISION_ITEM);
                        }
                        return;
                    }
                    if (!OverlayApplyItemOnPartyMon(ctx, pi, 0)) {
                        sOv.decisionRejected = TRUE;
                        BattleDecisions_MarkDone(ctx->battler, BATTLE_DECISION_ITEM);
                    }
                    return;
                }
            }
            if (!found) {
                sOv.decisionRejected = TRUE;
                BattleDecisions_MarkDone(ctx->battler, BATTLE_DECISION_ITEM);
            }
        }
        if (ctx->battlePartyMode != BATTLE_PARTY_MODE_USE_ITEM
            && BattleDecisions_PeekAction(ctx->battler, BATTLE_DECISION_SWITCH, &dec)) {
            BOOL found = FALSE;
            for (int pi = 0; pi < MAX_PARTY_SIZE; pi++) {
                if (sOv.mons[pi].ui.valid && ctx->pokemonPartySlots[pi] == dec.partySlot) {
                    char err[128];
                    found = TRUE;
                    if (OverlayCheckCanSwitch(ctx, pi, err, sizeof(err))) {
                        ctx->selectedPartyIndex = (u8)pi;
                        ctx->battlePartyExited = TRUE;
                        OverlayCloseToBattle();
                        return;
                    }
                    sOv.decisionRejected = TRUE;
                    BattleDecisions_MarkDone(ctx->battler, BATTLE_DECISION_SWITCH);
                    OverlaySetError(err);
                    break;
                }
            }
            if (!found) {
                sOv.decisionRejected = TRUE;
                BattleDecisions_MarkDone(ctx->battler, BATTLE_DECISION_SWITCH);
            }
        }
    }

    // Direct touch / mouse tap support on the 342x192 HD canvas.
    if (SIM_Wide_PollMainTouch(&tx, &ty)) {
        OverlayClearError();
        if (sOv.mode == OVERLAY_MODE_SUMMARY) {
            if (OverlayRectHit(8.0f, 175.0f, 48.0f, 17.0f, tx, ty)) {
                int next = OverlayStepValidPartySlot(sOv.partyCursor, -1);
                while (sOv.mons[next].isEgg && next != sOv.partyCursor) {
                    next = OverlayStepValidPartySlot(next, -1);
                }
                if (next != sOv.partyCursor) {
                    sOv.partyCursor = next;
                    Sound_PlayEffect(SE_CONFIRM_sseq_3);
                }
                return;
            }
            if (OverlayRectHit(58.0f, 175.0f, 48.0f, 17.0f, tx, ty)) {
                int next = OverlayStepValidPartySlot(sOv.partyCursor, 1);
                while (sOv.mons[next].isEgg && next != sOv.partyCursor) {
                    next = OverlayStepValidPartySlot(next, 1);
                }
                if (next != sOv.partyCursor) {
                    sOv.partyCursor = next;
                    Sound_PlayEffect(SE_CONFIRM_sseq_3);
                }
                return;
            }
            // Back pill or tapping summary returns cleanly to Party grid.
            Sound_PlayEffect(SEQ_SE_DP_DECIDE_sseq);
            sOv.mode = OVERLAY_MODE_PARTY;
            sOv.confirmMode = 0;
            return;
        }

        if (sOv.mode == OVERLAY_MODE_PP_SELECT) {
            OverlayPartyCache *mon = &sOv.mons[sOv.partyCursor];
            if (OverlayRectHit(286.0f, 175.0f, 52.0f, 17.0f, tx, ty)) {
                Sound_PlayEffect(SEQ_SE_DP_DECIDE_sseq);
                sOv.mode = OVERLAY_MODE_PARTY;
                return;
            }
            for (int m = 0; m < LEARNED_MOVES_MAX; m++) {
                float my = 45.0f + m * 31.0f;
                if (mon->moveIds[m] != MOVE_NONE && OverlayRectHit(179.0f, my, 146.0f, 26.5f, tx, ty)) {
                    sOv.ppMoveCursor = m;
                    OverlayApplyItemOnPartyMon(ctx, sOv.partyCursor, m);
                    return;
                }
            }
            return;
        }

        if (sOv.confirmMode == 1) {
            const float px = 342.0f - 104.0f - 12.0f;
            const float ph = 14.0f + 3 * 17.5f + 2 * 3.5f;
            const float py = 170.0f - ph;
            for (int k = 0; k < 3; k++) {
                float oy = py + 7.0f + k * (17.5f + 3.5f);
                if (OverlayRectHit(px + 7.0f, oy, 104.0f - 14.0f, 17.5f, tx, ty)) {
                    sOv.confirmCursor = k;
                    OverlayExecutePartyConfirm(ctx);
                    return;
                }
            }
            // Tapping outside modal or Back dismisses prompt.
            Sound_PlayEffect(SEQ_SE_DP_DECIDE_sseq);
            sOv.confirmMode = 0;
            return;
        }

        if (OverlayRectHit(286.0f, 175.0f, 52.0f, 17.0f, tx, ty)) {
            OverlayCancelParty(ctx);
            return;
        }

        for (int i = 0; i < MAX_PARTY_SIZE; i++) {
            int col = i & 1;
            int row = i >> 1;
            float cx = 12.0f + col * (155.0f + 8.0f);
            float cy = 27.0f + row * (43.0f + 5.5f);
            if (sOv.mons[i].ui.valid && OverlayRectHit(cx, cy, 155.0f, 43.0f, tx, ty)) {
                sOv.partyCursor = i;
                OverlayConfirmPartySlot(ctx);
                return;
            }
        }
        return;
    }

    pressed = gSystem.pressedKeys;
    repeat = gSystem.pressedKeysRepeatable;

    if (pressed != 0) {
        OverlayClearError();
    }

    if (sOv.mode == OVERLAY_MODE_SUMMARY) {
        if (pressed & (PAD_BUTTON_B | PAD_BUTTON_A)) {
            Sound_PlayEffect(SEQ_SE_DP_DECIDE_sseq);
            sOv.mode = OVERLAY_MODE_PARTY;
            sOv.confirmMode = 0;
            return;
        }
        if (pressed & (PAD_KEY_LEFT | PAD_BUTTON_L)) {
            int next = OverlayStepValidPartySlot(sOv.partyCursor, -1);
            while (sOv.mons[next].isEgg && next != sOv.partyCursor) {
                next = OverlayStepValidPartySlot(next, -1);
            }
            if (next != sOv.partyCursor) {
                sOv.partyCursor = next;
                Sound_PlayEffect(SE_CONFIRM_sseq_3);
            }
            return;
        }
        if (pressed & (PAD_KEY_RIGHT | PAD_BUTTON_R)) {
            int next = OverlayStepValidPartySlot(sOv.partyCursor, 1);
            while (sOv.mons[next].isEgg && next != sOv.partyCursor) {
                next = OverlayStepValidPartySlot(next, 1);
            }
            if (next != sOv.partyCursor) {
                sOv.partyCursor = next;
                Sound_PlayEffect(SE_CONFIRM_sseq_3);
            }
            return;
        }
        return;
    }

    if (sOv.mode == OVERLAY_MODE_PP_SELECT) {
        OverlayPartyCache *mon = &sOv.mons[sOv.partyCursor];
        if (pressed & PAD_BUTTON_B) {
            Sound_PlayEffect(SEQ_SE_DP_DECIDE_sseq);
            sOv.mode = OVERLAY_MODE_PARTY;
            return;
        }
        if (repeat & (PAD_KEY_UP | PAD_KEY_LEFT)) {
            for (int step = 1; step <= LEARNED_MOVES_MAX; step++) {
                int cand = (sOv.ppMoveCursor - step + LEARNED_MOVES_MAX) % LEARNED_MOVES_MAX;
                if (mon->moveIds[cand] != MOVE_NONE) {
                    sOv.ppMoveCursor = cand;
                    Sound_PlayEffect(SE_CONFIRM_sseq_3);
                    break;
                }
            }
            return;
        }
        if (repeat & (PAD_KEY_DOWN | PAD_KEY_RIGHT)) {
            for (int step = 1; step <= LEARNED_MOVES_MAX; step++) {
                int cand = (sOv.ppMoveCursor + step) % LEARNED_MOVES_MAX;
                if (mon->moveIds[cand] != MOVE_NONE) {
                    sOv.ppMoveCursor = cand;
                    Sound_PlayEffect(SE_CONFIRM_sseq_3);
                    break;
                }
            }
            return;
        }
        if (pressed & PAD_BUTTON_A) {
            if (mon->moveIds[sOv.ppMoveCursor] != MOVE_NONE) {
                OverlayApplyItemOnPartyMon(ctx, sOv.partyCursor, sOv.ppMoveCursor);
            }
            return;
        }
        return;
    }

    // Inline Shift / Summary / Cancel action prompt.
    if (sOv.confirmMode == 1) {
        if (pressed & PAD_BUTTON_B) {
            Sound_PlayEffect(SEQ_SE_DP_DECIDE_sseq);
            sOv.confirmMode = 0;
            return;
        }
        if (repeat & PAD_KEY_UP) {
            sOv.confirmCursor = (sOv.confirmCursor + 2) % 3;
            Sound_PlayEffect(SE_CONFIRM_sseq_3);
            return;
        }
        if (repeat & PAD_KEY_DOWN) {
            sOv.confirmCursor = (sOv.confirmCursor + 1) % 3;
            Sound_PlayEffect(SE_CONFIRM_sseq_3);
            return;
        }
        if (pressed & PAD_BUTTON_A) {
            OverlayExecutePartyConfirm(ctx);
            return;
        }
        return;
    }

    // Main 2x3 party grid navigation.
    if (repeat & (PAD_KEY_UP | PAD_KEY_DOWN | PAD_KEY_LEFT | PAD_KEY_RIGHT)) {
        int next = OverlayMovePartyGrid(sOv.partyCursor, repeat);
        if (next != sOv.partyCursor) {
            sOv.partyCursor = next;
            Sound_PlayEffect(SE_CONFIRM_sseq_3);
        }
        return;
    }

    if (pressed & PAD_BUTTON_B) {
        OverlayCancelParty(ctx);
        return;
    }

    if (pressed & PAD_BUTTON_A) {
        OverlayConfirmPartySlot(ctx);
    }
}

void BattleBdspOverlay_Reset(void)
{
    if (sOv.mode != OVERLAY_MODE_NONE) {
        SIM_Wide_SetMainTouchEnabled(0);
    }
    memset(&sOv, 0, sizeof(sOv));
}

BOOL BattleBdspOverlay_ShouldUse(BattleSystem *battleSys)
{
    if (battleSys == NULL) {
        return FALSE;
    }
    if (!SIM_Battle3D_ModelsEnabled() || !BattleHud_IsHdMode()) {
        return FALSE;
    }
    if (BattleSystem_GetBattleType(battleSys) & BATTLE_TYPE_CATCH_TUTORIAL) {
        return FALSE;
    }
    return TRUE;
}

void BattleBdspOverlay_StartBag(BattleBagContext *ctx)
{
    BagCursor *cursor;
    u16 curCat;
    int startTab = 0;

    if (ctx == NULL) {
        return;
    }

    memset(&sOv, 0, sizeof(sOv));
    sOv.mode = OVERLAY_MODE_BAG;
    sOv.bagCtx = ctx;
    sOv.ignoreInputFrames = 2;

    OverlayPopulateBagPockets(ctx);

    cursor = BattleSystem_GetBagCursor(ctx->battleSys);
    curCat = (cursor != NULL) ? BagCursor_GetBattleCurrentCategory(cursor) : BATTLE_POCKET_INDEX_RECOVER_HP_PP;
    for (int t = 0; t < OVERLAY_BAG_TAB_COUNT; t++) {
        if (sTabToPocket[t] == curCat) {
            startTab = t;
            break;
        }
    }
    sOv.activeTab = startTab;
    OverlayClampBagCursor(sOv.activeTab);
    OverlayRefreshBagDesc();
    SIM_Wide_SetBattleTouchNeeded(0);
    SIM_Wide_SetMainTouchEnabled(1);
}

void BattleBdspOverlay_StartParty(BattlePartyContext *ctx)
{
    int startCursor = 0;

    if (ctx == NULL) {
        return;
    }

    memset(&sOv, 0, sizeof(sOv));
    sOv.mode = OVERLAY_MODE_PARTY;
    sOv.partyCtx = ctx;
    sOv.ignoreInputFrames = 2;
    ctx->currentDamage = 0;

    OverlayPopulateParty(ctx);

    if (ctx->battlePartyMode == BATTLE_PARTY_MODE_USE_ITEM && ctx->selectedBattleBagItem != ITEM_NONE) {
        OverlayLoadItemName(ctx->selectedBattleBagItem, ctx->heapID, sOv.itemUseName, sizeof(sOv.itemUseName));
    }

    if (ctx->selectedPartyIndex < MAX_PARTY_SIZE && sOv.mons[ctx->selectedPartyIndex].ui.valid) {
        startCursor = ctx->selectedPartyIndex;
    } else {
        for (int i = 0; i < MAX_PARTY_SIZE; i++) {
            if (sOv.mons[i].ui.valid) {
                startCursor = i;
                break;
            }
        }
    }
    sOv.partyCursor = startCursor;
    SIM_Wide_SetBattleTouchNeeded(0);
    SIM_Wide_SetMainTouchEnabled(1);
}

BOOL BattleBdspOverlay_IsActive(void)
{
    return sOv.mode != OVERLAY_MODE_NONE;
}

void BattleBdspOverlay_Tick(BattleSystem *battleSys)
{
    (void)battleSys;
    if (sOv.mode == OVERLAY_MODE_NONE) {
        return;
    }

    SIM_Wide_SetBattleTouchNeeded(0);
    SIM_Wide_SetMainTouchEnabled(1);

    if (sOv.errorTimer > 0) {
        sOv.errorTimer--;
        if (sOv.errorTimer == 0) {
            sOv.errorMsg[0] = '\0';
        }
    }

    if (sOv.ignoreInputFrames > 0) {
        int dropX = 0, dropY = 0;
        SIM_Wide_PollMainTouch(&dropX, &dropY);
        sOv.ignoreInputFrames--;
    } else if (sOv.mode == OVERLAY_MODE_BAG) {
        OverlayTickBag();
    } else {
        OverlayTickParty();
    }
}

void BattleBdspOverlay_FillFrame(BattleSystem *battleSys, SIM_HudHD_Frame *frame)
{
    SIM_HudHD_Overlay *ov;

    (void)battleSys;
    if (frame == NULL) {
        return;
    }

    if (sOv.mode == OVERLAY_MODE_NONE) {
        frame->overlay.kind = SIM_HUDHD_OVERLAY_NONE;
        return;
    }

    // Suppress underlying battle HUD cards/menus/dialogue so the HD overlay is clean & unobstructed.
    for (int i = 0; i < SIM_HUDHD_MAX_CARDS; i++) {
        frame->cards[i].visible = 0;
    }
    frame->partyStrips[0].visible = 0;
    frame->partyStrips[1].visible = 0;
    frame->numButtons = 0;
    frame->numMoves = 0;
    frame->infoCard.visible = 0;
    frame->dialogue.visible = 0;
    frame->showKeyHints = 0;

    ov = &frame->overlay;
    memset(ov, 0, sizeof(*ov));

    if (sOv.mode == OVERLAY_MODE_BAG) {
        int tab = sOv.activeTab;
        int total = sOv.pocketCounts[tab];
        int scroll = sOv.bagScroll[tab];
        int visible = 0;

        ov->kind = SIM_HUDHD_OVERLAY_BAG;
        snprintf(ov->title, sizeof(ov->title), "BATTLE BAG");
        snprintf(ov->subtitle, sizeof(ov->subtitle), "%s", sTabNames[tab]);
        snprintf(ov->desc, sizeof(ov->desc), "%s", sOv.cachedDesc);
        snprintf(ov->footerHint, sizeof(ov->footerHint), "A Use   B Back   L/R Pocket");

        ov->numTabs = OVERLAY_BAG_TAB_COUNT;
        ov->activeTab = tab;
        for (int t = 0; t < OVERLAY_BAG_TAB_COUNT; t++) {
            snprintf(ov->tabNames[t], sizeof(ov->tabNames[t]), "%s", sTabNames[t]);
        }

        ov->scrollOffset = scroll;
        ov->totalItems = total;
        for (int row = 0; row < OVERLAY_BAG_VISIBLE_ROWS && (scroll + row) < total; row++) {
            int idx = scroll + row;
            SIM_HudHD_OverlayItem *it = &ov->items[visible++];
            it->valid = 1;
            it->itemId = sOv.pocketItems[tab][idx].itemId;
            snprintf(it->name, sizeof(it->name), "%s", sOv.pocketItems[tab][idx].name);
            it->count = sOv.pocketItems[tab][idx].count;
            it->selected = (idx == sOv.bagCursor[tab]) ? 1 : 0;
            it->usable = 1;
        }
        ov->numItems = visible;
    } else if (sOv.mode == OVERLAY_MODE_PARTY) {
        BattlePartyContext *ctx = sOv.partyCtx;
        ov->kind = SIM_HUDHD_OVERLAY_PARTY;
        if (ctx != NULL && ctx->battlePartyMode == BATTLE_PARTY_MODE_USE_ITEM) {
            snprintf(ov->title, sizeof(ov->title), "USE ITEM");
            snprintf(ov->subtitle, sizeof(ov->subtitle), "Use %s on which Pok\xC3\xA9mon?", sOv.itemUseName);
            snprintf(ov->footerHint, sizeof(ov->footerHint), "A Use   B Back to Bag");
        } else if (ctx != NULL && ctx->battlePartyMode == BATTLE_PARTY_MODE_SELECT_POKEMON_NO_CANCEL) {
            snprintf(ov->title, sizeof(ov->title), "POK\xC3\x89MON");
            snprintf(ov->subtitle, sizeof(ov->subtitle), "Choose next Pok\xC3\xA9mon");
            snprintf(ov->footerHint, sizeof(ov->footerHint), "A Select   D-Pad / Tap");
        } else {
            snprintf(ov->title, sizeof(ov->title), "POK\xC3\x89MON");
            snprintf(ov->subtitle, sizeof(ov->subtitle), "Choose a Pok\xC3\xA9mon");
            snprintf(ov->footerHint, sizeof(ov->footerHint), "A Options   B Back   D-Pad / Tap");
        }

        ov->numParty = sOv.partyCount;
        ov->partyCursor = sOv.partyCursor;
        for (int i = 0; i < MAX_PARTY_SIZE; i++) {
            ov->party[i] = sOv.mons[i].ui;
            ov->party[i].selected = (i == sOv.partyCursor && sOv.mons[i].ui.valid) ? 1 : 0;
        }

        if (sOv.confirmMode == 1) {
            ov->confirmMode = 1;
            ov->confirmCursor = sOv.confirmCursor;
            ov->confirmCount = 3;
            snprintf(ov->confirmLabels[0], sizeof(ov->confirmLabels[0]),
                (ctx != NULL && ctx->battlePartyMode == BATTLE_PARTY_MODE_SELECT_POKEMON_NO_CANCEL)
                    ? "Send Out"
                    : "Shift");
            snprintf(ov->confirmLabels[1], sizeof(ov->confirmLabels[1]), "Summary");
            snprintf(ov->confirmLabels[2], sizeof(ov->confirmLabels[2]), "Cancel");
            snprintf(ov->footerHint, sizeof(ov->footerHint), "A Confirm   B Back");
        }
    } else if (sOv.mode == OVERLAY_MODE_SUMMARY || sOv.mode == OVERLAY_MODE_PP_SELECT) {
        ov->kind = SIM_HUDHD_OVERLAY_SUMMARY;
        ov->numParty = sOv.partyCount;
        ov->partyCursor = sOv.partyCursor;
        for (int i = 0; i < MAX_PARTY_SIZE; i++) {
            ov->party[i] = sOv.mons[i].ui;
            ov->party[i].selected = (i == sOv.partyCursor) ? 1 : 0;
        }

        if (sOv.mode == OVERLAY_MODE_PP_SELECT) {
            snprintf(ov->title, sizeof(ov->title), "RESTORE PP");
            snprintf(ov->subtitle, sizeof(ov->subtitle), "Select a move for %s", sOv.itemUseName);
            snprintf(ov->footerHint, sizeof(ov->footerHint), "A Restore Move   B Back");
            ov->confirmMode = 1;
            ov->confirmCursor = sOv.ppMoveCursor;
        } else {
            snprintf(ov->title, sizeof(ov->title), "SUMMARY");
            snprintf(ov->subtitle, sizeof(ov->subtitle), "%s  Lv.%d",
                sOv.mons[sOv.partyCursor].ui.name,
                sOv.mons[sOv.partyCursor].ui.level);
            snprintf(ov->footerHint, sizeof(ov->footerHint), "L/R Switch Mon   B Back to Party");
            ov->confirmMode = 0;
        }
    }

    if (sOv.errorMsg[0] != '\0') {
        snprintf(ov->errorMsg, sizeof(ov->errorMsg), "%s", sOv.errorMsg);
    }
}
