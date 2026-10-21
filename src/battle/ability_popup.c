#include "battle/ability_popup.h"

#include <nitro.h>
#include <string.h>

#include "constants/battle.h"
#include "constants/battle/message_tags.h"
#include "constants/charcode.h"
#include "constants/heap.h"
#include "constants/narc.h"
#include "generated/abilities.h"
#include "generated/text_banks.h"
#include "struct_defs/struct_020127E8.h"

#include "battle/battle_events.h"
#include "battle/battle_message.h"
#include "battle/ov16_0223DF00.h"

#include "bg_window.h"
#include "char_transfer.h"
#include "font.h"
#include "heap.h"
#include "message.h"
#include "palette.h"
#include "pltt_transfer.h"
#include "pokemon.h"
#include "sound_playback.h"
#include "sprite.h"
#include "sprite_system.h"
#include "string_gf.h"
#include "string_template.h"
#include "sys_task.h"
#include "sys_task_manager.h"
#include "text.h"
#include "unk_02012744.h"

#include "res/text/bank/battle_strings.h"

#include "ability_popup_banner.h"

// BW2 reference: BtlvScuAbilityWin (pokebw2 src/ov167/btlv_scu.c:2472-2650).
//   - each side has an 18x4-character banner, the player's on BG2 at screen (0,112), the foe's on BG3 at (120,48)
//     (screens 0x1E5/0x1E6), drawn from file 0x1E3 with BG palette 1;
//   - show: the banner scrolls in from its own screen edge, 144 px in 8 frames (18 px a frame) with SE_SHOOTER,
//     then the text appears one character column a frame; an ability activation (ScAbilityPopupIn) adds a white
//     palette flash with SE_DECIDE6;
//   - it stays until the server's "pop-up out" command, which BW2 sends after the activation's messages;
//   - a new pop-up for another Pokemon on the same side replaces the shown one at once.
// Here BG2 and BG3 are taken (move effects and the classic backdrop), so the banner is a FontOAM: OBJs built from a
// Window, with OBJ VRAM and an OBJ palette borrowed only while the banner is up. There is no "pop-up out" command
// in Platinum's scripts, so the banner holds while its message prints plus ABILITY_POPUP_HOLD_FRAMES, then slides
// back out the way it came.

#define POPUP_WIDTH   (ABILITY_BANNER_TILES_X * 8)
#define POPUP_HEIGHT  (ABILITY_BANNER_TILES_Y * 8)
#define POPUP_BYTES   (ABILITY_BANNER_TILES_X * ABILITY_BANNER_TILES_Y * TILE_SIZE_4BPP)
#define POPUP_COLUMNS ABILITY_BANNER_TILES_X

#define POPUP_SLIDE_FRAMES 8
#define POPUP_SLIDE_STEP   18 // 144 px in 8 frames, as BW2
#define POPUP_FLASH_FRAMES 8
// After the message has printed. BW2's banner stays through the activation's messages and their waits; Platinum's
// ability messages are followed by a 30-60 frame wait (WaitButtonABTime), so 45 frames keeps it up about as long.
#define ABILITY_POPUP_HOLD_FRAMES 45

#define POPUP_PLAYER_X 0
#define POPUP_PLAYER_Y 112
#define POPUP_ENEMY_X  120
#define POPUP_ENEMY_Y  48

// Banner palette colors: 1 text, 2 text shadow (BW2 draws with LUT 1, 2, 0). 3 is unused by the art, so the text
// is printed on 3 and composited onto the banner.
#define POPUP_TEXT_FG     1
#define POPUP_TEXT_SHADOW 2
#define POPUP_TEXT_KEY    3

// Text placement, after BtlvScuAbilityWin_DrawText (btlv_scu.c:2641-2683): the name line starts at the left, the
// ability line ends 12 px before the right edge, and the two overlap by at least 12 px. BW2's small font draws at
// y 7 and 18; Platinum's system font cell is 16 rows with the letters in its upper 12, so the ability line sits at
// 13 to center it in the banner's dark bar (rows 13-26) and the name above it.
#define POPUP_LINE1_Y        0
#define POPUP_LINE2_Y        13
#define POPUP_LINE2_END      132
#define POPUP_LINE1_PAD      8
#define POPUP_LINES_OVERLAP  12

// Resource IDs for the palettes in the PlttTransfer manager. Battle sprite resources use 20000-20100.
#define POPUP_PLTT_RESOURCE_ID 0xAB10

// The OBJ priority among the battle's sprites, and the BG priority: over the healthbars and battlers.
#define POPUP_SPRITE_PRIORITY 0
#define POPUP_BG_PRIORITY     0

enum AbilityPopupState {
    POPUP_NONE = 0,
    POPUP_SLIDE_IN,
    POPUP_REVEAL,
    POPUP_FLASH,
    POPUP_HOLD,
    POPUP_SLIDE_OUT,
};

typedef struct AbilityPopup {
    BattleSystem *battleSys;
    SysTask *task;
    UnkStruct_02012744 *fontMan;
    UnkStruct_02012B20 *layout;
    FontOAM *fontOAM;
    CharTransferAllocation charAlloc;
    Window window; // what the OBJs show: the banner, plus the text columns revealed so far
    u8 *composed; // the banner with all of its text
    u16 ability;
    u8 side;
    u8 battler;
    u8 partySlot;
    u8 state;
    u8 printerID;
    u8 column;
    u8 paletteSlot;
    u8 hasPalette : 1;
    u8 hasChars : 1;
    s16 x;
    s16 timer;
} AbilityPopup;

static AbilityPopup sPopups[2];

static const NNSG2dPaletteData sPaletteData[2] = {
    { GX_TEXFMT_PLTT16, FALSE, sizeof(sAbilityBannerPalette), (void *)sAbilityBannerPalette },
    { GX_TEXFMT_PLTT16, FALSE, sizeof(sAbilityBannerPalette), (void *)sAbilityBannerPalette },
};

static void AbilityPopup_Task(SysTask *task, void *data);

static s16 AbilityPopup_HomeX(int side)
{
    return side == BATTLE_SIDE_PLAYER ? POPUP_PLAYER_X : POPUP_ENEMY_X;
}

static s16 AbilityPopup_HomeY(int side)
{
    return side == BATTLE_SIDE_PLAYER ? POPUP_PLAYER_Y : POPUP_ENEMY_Y;
}

// Where the banner starts and ends its slide: just off its own edge of the screen
static s16 AbilityPopup_OffscreenX(int side)
{
    return side == BATTLE_SIDE_PLAYER
        ? POPUP_PLAYER_X - POPUP_SLIDE_FRAMES * POPUP_SLIDE_STEP
        : POPUP_ENEMY_X + POPUP_SLIDE_FRAMES * POPUP_SLIDE_STEP;
}

static void AbilityPopup_UpdateDebug(const AbilityPopup *popup)
{
    gBattleEventsDebug.popupState[popup->side] = popup->state;
    gBattleEventsDebug.popupX[popup->side] = popup->x;
}

static void AbilityPopup_Free(AbilityPopup *popup)
{
    if (popup->task != NULL) {
        SysTask_Done(popup->task);
        popup->task = NULL;
    }

    if (popup->fontOAM != NULL) {
        sub_02012870(popup->fontOAM);
        popup->fontOAM = NULL;
    }

    if (popup->layout != NULL) {
        sub_02012B48(popup->layout);
        popup->layout = NULL;
    }

    if (popup->fontMan != NULL) {
        sub_020127BC(popup->fontMan);
        popup->fontMan = NULL;
    }

    if (popup->hasChars) {
        CharTransfer_ClearRange(&popup->charAlloc);
        popup->hasChars = FALSE;
    }

    if (popup->window.pixels != NULL) {
        Window_Remove(&popup->window);
        popup->window.pixels = NULL;
    }

    if (popup->composed != NULL) {
        Heap_Free(popup->composed);
        popup->composed = NULL;
    }

    if (popup->hasPalette) {
        PlttTransfer_ResetTask(POPUP_PLTT_RESOURCE_ID + popup->side);
        popup->hasPalette = FALSE;
    }

    popup->state = POPUP_NONE;
    AbilityPopup_UpdateDebug(popup);
}

static void AbilityPopup_LoadPalette(AbilityPopup *popup, int whiteLevel)
{
    u16 colors[16];
    int i;

    for (i = 0; i < 16; i++) {
        u16 c = sAbilityBannerPalette[i];
        int r = c & 0x1F;
        int g = (c >> 5) & 0x1F;
        int b = (c >> 10) & 0x1F;

        if (i != 0 && whiteLevel > 0) {
            r += (31 - r) * whiteLevel / 16;
            g += (31 - g) * whiteLevel / 16;
            b += (31 - b) * whiteLevel / 16;
        }

        colors[i] = r | (g << 5) | (b << 10);
    }

    // The battle commits its whole palette buffer every frame (auto transparent), so the buffer is the source
    PaletteData_LoadBuffer(BattleSystem_PaletteSys(popup->battleSys), colors, PLTTBUF_MAIN_OBJ, popup->paletteSlot * 16, sizeof(colors));
}

// Prints str into a scratch window filled with the key color and copies the drawn pixels onto dst
static void AbilityPopup_PrintOnto(BgConfig *bgConfig, u8 *dst, const String *str, int x, int y)
{
    Window text;
    const u8 *src;
    int i;

    Window_Init(&text);
    Window_AddToTopLeftCorner(bgConfig, &text, ABILITY_BANNER_TILES_X, ABILITY_BANNER_TILES_Y, 0, POPUP_TEXT_KEY);

    if (text.pixels == NULL) {
        return;
    }

    Text_AddPrinterWithParamsAndColor(&text, FONT_SYSTEM, str, x, y, TEXT_SPEED_NO_TRANSFER, TEXT_COLOR(POPUP_TEXT_FG, POPUP_TEXT_SHADOW, POPUP_TEXT_KEY), NULL);
    src = text.pixels;

    for (i = 0; i < POPUP_BYTES; i++) {
        u8 lo = src[i] & 0xF;
        u8 hi = src[i] >> 4;

        if (lo != POPUP_TEXT_KEY) {
            dst[i] = (dst[i] & 0xF0) | lo;
        }

        if (hi != POPUP_TEXT_KEY) {
            dst[i] = (dst[i] & 0x0F) | (hi << 4);
        }
    }

    Window_Remove(&text);
}

static void AbilityPopup_DrawText(AbilityPopup *popup)
{
    BattleSystem *battleSys = popup->battleSys;
    BgConfig *bgConfig = BattleSystem_BGL(battleSys);
    String *name = String_Init(MON_NAME_LEN + 12, HEAP_ID_BATTLE);
    String *nameTemplate = MessageLoader_GetNewString(BattleSystem_GetMessageLoader(battleSys), pl_msg_00000368_00964);
    StringTemplate *strTemplate = StringTemplate_Default(HEAP_ID_BATTLE);
    MessageLoader *abilityLoader = MessageLoader_Init(MSG_LOADER_LOAD_ON_DEMAND, NARC_INDEX_MSGDATA__PL_MSG, TEXT_BANK_ABILITY_NAMES, HEAP_ID_BATTLE);
    String *abilityName = MessageLoader_GetNewString(abilityLoader, popup->ability);
    Pokemon *mon = BattleSystem_PartyPokemon(battleSys, popup->battler, popup->partySlot);
    int width1, width2, end, x1, x2, overlap, shift, half;

    // "<Pokemon>'s": line 1 of BW2's message 0x67, with the nickname the battle shows (the healthbar's template)
    StringTemplate_SetNickname(strTemplate, 0, Pokemon_GetBoxPokemon(mon));
    StringTemplate_Format(strTemplate, name, nameTemplate);
    String_AppendChar(name, CHAR_SINGLE_QUOTE_CLOSE);
    String_AppendChar(name, CHAR_s);

    width1 = Font_CalcStringWidth(FONT_SYSTEM, name, 0);
    width2 = Font_CalcStringWidth(FONT_SYSTEM, abilityName, 0);

    end = width1 + POPUP_LINE1_PAD;
    x2 = POPUP_LINE2_END - width2;
    overlap = end - x2;

    if (overlap < POPUP_LINES_OVERLAP) {
        shift = POPUP_LINES_OVERLAP - overlap;
        half = shift / 2;
        end += half;
        x2 -= shift - half;
    }

    x1 = end - width1;

    if (x1 < 0) {
        x1 = 0;
    }

    if (x2 < 0) {
        x2 = 0;
    }

    // Keep both lines inside the banner (long nickname + long ability)
    if (x1 + width1 > POPUP_WIDTH) {
        x1 = POPUP_WIDTH - width1 > 0 ? POPUP_WIDTH - width1 : 0;
    }

    AbilityPopup_PrintOnto(bgConfig, popup->composed, name, x1, POPUP_LINE1_Y);
    AbilityPopup_PrintOnto(bgConfig, popup->composed, abilityName, x2, POPUP_LINE2_Y);

    String_Free(abilityName);
    MessageLoader_Free(abilityLoader);
    StringTemplate_Free(strTemplate);
    String_Free(nameTemplate);
    String_Free(name);
}

static void AbilityPopup_Upload(AbilityPopup *popup)
{
    sub_02012BE0(popup->fontOAM, popup->layout, &popup->window, HEAP_ID_BATTLE);
}

// Copies text column `column` (4 characters) from the composed banner into the shown window
static void AbilityPopup_RevealColumn(AbilityPopup *popup, int column)
{
    u8 *dst = popup->window.pixels;
    int row;

    for (row = 0; row < ABILITY_BANNER_TILES_Y; row++) {
        int offset = (row * ABILITY_BANNER_TILES_X + column) * TILE_SIZE_4BPP;
        memcpy(dst + offset, popup->composed + offset, TILE_SIZE_4BPP);
    }
}

static void AbilityPopup_SetX(AbilityPopup *popup, s16 x)
{
    popup->x = x;
    FontOAM_SetXY(popup->fontOAM, x, AbilityPopup_HomeY(popup->side));
}

static BOOL AbilityPopup_Start(AbilityPopup *popup, BattleSystem *battleSys, int battler, int partySlot, u16 ability, u8 printerID)
{
    SpriteManager *spriteMan = BattleSystem_GetSpriteManager(battleSys);
    PlttTransferTaskTemplate plttTemplate;
    UnkStruct_020127E8 fontTemplate;
    int size;

    popup->battleSys = battleSys;
    popup->battler = battler;
    popup->partySlot = partySlot;
    popup->ability = ability;
    popup->printerID = printerID;

    // An OBJ palette, only while the banner is up
    plttTemplate.data = (NNSG2dPaletteData *)&sPaletteData[popup->side];
    plttTemplate.vramType = NNS_G2D_VRAM_TYPE_2DMAIN;
    plttTemplate.plttIndex = 1;
    plttTemplate.resourceID = POPUP_PLTT_RESOURCE_ID + popup->side;

    if (PlttTransfer_RequestFreeSpace(&plttTemplate) == FALSE) {
        return FALSE;
    }

    popup->hasPalette = TRUE;
    popup->paletteSlot = PlttTransfer_GetPlttOffset(PlttTransfer_GetPaletteProxy(plttTemplate.resourceID), NNS_G2D_VRAM_TYPE_2DMAIN);
    AbilityPopup_LoadPalette(popup, 0);

    // The banner art, then its text
    Window_Init(&popup->window);
    Window_AddToTopLeftCorner(BattleSystem_BGL(battleSys), &popup->window, ABILITY_BANNER_TILES_X, ABILITY_BANNER_TILES_Y, 0, 0);
    popup->composed = Heap_Alloc(HEAP_ID_BATTLE, POPUP_BYTES);

    if (popup->window.pixels == NULL || popup->composed == NULL) {
        return FALSE;
    }

    memcpy(popup->window.pixels, popup->side == BATTLE_SIDE_PLAYER ? sAbilityBannerTiles_Player : sAbilityBannerTiles_Enemy, POPUP_BYTES);
    memcpy(popup->composed, popup->window.pixels, POPUP_BYTES);
    AbilityPopup_DrawText(popup);

    // OBJ characters: 2.25 KB (144x32 at 4bpp), only while the banner is up
    popup->layout = sub_02012B20(&popup->window, HEAP_ID_BATTLE);
    size = sub_02012B58(popup->layout, NNS_G2D_VRAM_TYPE_2DMAIN);

    if (CharTransfer_AllocRange(size, TRUE, NNS_G2D_VRAM_TYPE_2DMAIN, &popup->charAlloc) == FALSE) {
        return FALSE;
    }

    popup->hasChars = TRUE;
    popup->fontMan = sub_02012744(1, HEAP_ID_BATTLE);

    fontTemplate.unk_00 = popup->fontMan;
    fontTemplate.unk_04 = &popup->window;
    fontTemplate.unk_08 = SpriteManager_GetSpriteList(spriteMan);
    fontTemplate.unk_0C = PlttTransfer_GetPaletteProxy(plttTemplate.resourceID);
    fontTemplate.unk_10 = NULL;
    fontTemplate.unk_14 = popup->charAlloc.offset;
    fontTemplate.unk_18 = AbilityPopup_OffscreenX(popup->side);
    fontTemplate.unk_1C = AbilityPopup_HomeY(popup->side);
    fontTemplate.unk_20 = POPUP_BG_PRIORITY;
    fontTemplate.unk_24 = POPUP_SPRITE_PRIORITY;
    fontTemplate.unk_28 = NNS_G2D_VRAM_TYPE_2DMAIN;
    fontTemplate.heapID = HEAP_ID_BATTLE;

    popup->fontOAM = sub_02012B60(&fontTemplate, popup->layout);

    if (popup->fontOAM == NULL) {
        return FALSE;
    }

    AbilityPopup_SetX(popup, AbilityPopup_OffscreenX(popup->side));
    popup->state = POPUP_SLIDE_IN;
    popup->timer = POPUP_SLIDE_FRAMES;
    popup->column = 0;
    popup->task = SysTask_Start(AbilityPopup_Task, popup, 1000);
    Sound_PlayEffect(SEQ_SE_DP_SLIDEIN);

    gBattleEventsDebug.popupShows[popup->side]++;
    gBattleEventsDebug.popupAbility[popup->side] = ability;
    gBattleEventsDebug.popupBattler[popup->side] = battler;
    AbilityPopup_UpdateDebug(popup);

    return TRUE;
}

static void AbilityPopup_Task(SysTask *task, void *data)
{
    AbilityPopup *popup = data;

    switch (popup->state) {
    case POPUP_SLIDE_IN:
        if (popup->side == BATTLE_SIDE_PLAYER) {
            AbilityPopup_SetX(popup, popup->x + POPUP_SLIDE_STEP);
        } else {
            AbilityPopup_SetX(popup, popup->x - POPUP_SLIDE_STEP);
        }

        if (--popup->timer <= 0) {
            AbilityPopup_SetX(popup, AbilityPopup_HomeX(popup->side));
            popup->state = POPUP_REVEAL;
            popup->column = 0;
        }
        break;

    case POPUP_REVEAL:
        // The text appears one column a frame, as BW2
        AbilityPopup_RevealColumn(popup, popup->column);
        AbilityPopup_Upload(popup);

        if (++popup->column >= POPUP_COLUMNS) {
            popup->state = POPUP_FLASH;
            popup->timer = 0;
            Sound_PlayEffect(SEQ_SE_DP_DECIDE);
        }
        break;

    case POPUP_FLASH:
        // BW2 fades the banner's palette from white back to normal
        popup->timer++;
        AbilityPopup_LoadPalette(popup, 16 - popup->timer * 16 / POPUP_FLASH_FRAMES);

        if (popup->timer >= POPUP_FLASH_FRAMES) {
            AbilityPopup_LoadPalette(popup, 0);
            popup->state = POPUP_HOLD;
            popup->timer = ABILITY_POPUP_HOLD_FRAMES;
        }
        break;

    case POPUP_HOLD:
        if (Text_IsPrinterActive(popup->printerID)) {
            popup->timer = ABILITY_POPUP_HOLD_FRAMES;
        } else if (--popup->timer <= 0) {
            popup->state = POPUP_SLIDE_OUT;
            popup->timer = POPUP_SLIDE_FRAMES;
        }
        break;

    case POPUP_SLIDE_OUT:
        if (popup->side == BATTLE_SIDE_PLAYER) {
            AbilityPopup_SetX(popup, popup->x - POPUP_SLIDE_STEP);
        } else {
            AbilityPopup_SetX(popup, popup->x + POPUP_SLIDE_STEP);
        }

        if (--popup->timer <= 0) {
            AbilityPopup_Free(popup);
            return;
        }
        break;

    default:
        AbilityPopup_Free(popup);
        return;
    }

    AbilityPopup_UpdateDebug(popup);
}

static void AbilityPopup_Show(BattleSystem *battleSys, int battler, int partySlot, u16 ability, u8 printerID)
{
    AbilityPopup *popup;
    int side;

    if (ability == ABILITY_NONE || battler < 0 || battler >= BattleSystem_MaxBattlers(battleSys)) {
        return;
    }

    side = Battler_Side(battleSys, battler) == BATTLE_SIDE_PLAYER ? BATTLE_SIDE_PLAYER : BATTLE_SIDE_ENEMY;
    popup = &sPopups[side];

    if (popup->state != POPUP_NONE) {
        if (popup->battler == battler && popup->ability == ability) {
            // Another message about the same activation (Intimidate hitting two foes): keep the banner up for it,
            // and bring it back if it was already leaving. BW2 also skips a show for the Pokemon already shown.
            popup->printerID = printerID;

            if (popup->state == POPUP_HOLD) {
                popup->timer = ABILITY_POPUP_HOLD_FRAMES;
            } else if (popup->state == POPUP_SLIDE_OUT) {
                AbilityPopup_SetX(popup, AbilityPopup_HomeX(side));
                popup->state = POPUP_HOLD;
                popup->timer = ABILITY_POPUP_HOLD_FRAMES;
            }

            return;
        }

        // Another Pokemon or ability on the same side replaces the shown banner at once, as BW2's Hide-then-show
        AbilityPopup_Free(popup);
    }

    popup->side = side;

    if (AbilityPopup_Start(popup, battleSys, battler, partySlot, ability, printerID) == FALSE) {
        AbilityPopup_Free(popup);
        gBattleEventsDebug.popupSkipped++;
    }
}

// Trace's and Frisk's messages and their side variants (BattleMessage_Print has already moved msg->id to the
// variant for the Pokemon's side: +1 wild, +2 foe, and for Trace's two Pokemon up to +6)
#define TRACE_MSG_FIRST pl_msg_00000368_00679
#define TRACE_MSG_LAST  pl_msg_00000368_00685
#define FRISK_MSG_FIRST pl_msg_00000368_01118
#define FRISK_MSG_LAST  pl_msg_00000368_01120

// The Pokemon and ability a message is about. Messages name a battler with a name tag (battler | party slot << 8)
// and an ability with its ID. Returns how many (Pokemon, ability) pairs it holds, at most 2.
static int AbilityPopup_GetHolders(const BattleMessage *msg, int *battlers, int *slots, u16 *abilities)
{
    // PrintGlobalMessage (the Totem's Pressure line) and side-local messages carry flags above the tag
    switch (msg->tags & BATTLE_MESSAGE_TAGS) {
    case TAG_NICKNAME_ABILITY:
    case TAG_NICKNAME_ABILITY_NICKNAME:
    case TAG_NICKNAME_ABILITY_MOVE:
    case TAG_NICKNAME_ABILITY_ITEM:
    case TAG_NICKNAME_ABILITY_STAT:
    case TAG_NICKNAME_ABILITY_TYPE:
    case TAG_NICKNAME_ABILITY_STATUS:
    case TAG_NICKNAME_ABILITY_NUMBER:
    case TAG_NICKNAME_ABILITY_NICKNAME_MOVE:
    case TAG_NICKNAME_ABILITY_NICKNAME_STAT:
        battlers[0] = msg->params[0] & 0xFF;
        slots[0] = (msg->params[0] >> 8) & 0xFF;
        abilities[0] = msg->params[1];
        return 1;

    case TAG_NICKNAME_ABILITY_NICKNAME_ABILITY:
        // "X's A was suppressed by Y's B" and the like: both abilities act
        battlers[0] = msg->params[0] & 0xFF;
        slots[0] = (msg->params[0] >> 8) & 0xFF;
        abilities[0] = msg->params[1];
        battlers[1] = msg->params[2] & 0xFF;
        slots[1] = (msg->params[2] >> 8) & 0xFF;
        abilities[1] = msg->params[3];
        return 2;

    case TAG_ABILITY_NICKNAME:
        // Anticipation: "X's Anticipation made it shudder!"
        battlers[0] = msg->params[1] & 0xFF;
        slots[0] = (msg->params[1] >> 8) & 0xFF;
        abilities[0] = msg->params[0];
        return 1;

    case TAG_NICKNAME_NICKNAME_ABILITY:
        // Trace names the traced ability; the one activating is Trace. (Role Play and Skill Swap are moves.)
        if (msg->id >= TRACE_MSG_FIRST && msg->id <= TRACE_MSG_LAST) {
            battlers[0] = msg->params[0] & 0xFF;
            slots[0] = (msg->params[0] >> 8) & 0xFF;
            abilities[0] = ABILITY_TRACE;
            return 1;
        }
        break;

    case TAG_NICKNAME_ITEM:
        // Frisk's message names the item, not the ability
        if (msg->id >= FRISK_MSG_FIRST && msg->id <= FRISK_MSG_LAST) {
            battlers[0] = msg->params[0] & 0xFF;
            slots[0] = (msg->params[0] >> 8) & 0xFF;
            abilities[0] = ABILITY_FRISK;
            return 1;
        }
        break;
    }

    return 0;
}

void AbilityPopup_OnBattleMessage(BattleSystem *battleSys, const BattleMessage *msg, u8 printerID)
{
    int battlers[2], slots[2];
    u16 abilities[2];
    int count = AbilityPopup_GetHolders(msg, battlers, slots, abilities);
    int i;

    for (i = 0; i < count; i++) {
        AbilityPopup_Show(battleSys, battlers[i], slots[i], abilities[i], printerID);
    }
}

void AbilityPopup_Shutdown(void)
{
    AbilityPopup_Free(&sPopups[0]);
    AbilityPopup_Free(&sPopups[1]);
}

BOOL AbilityPopup_IsActive(void)
{
    return sPopups[0].state != POPUP_NONE || sPopups[1].state != POPUP_NONE;
}
