#include "battle/battle_debug.h"

#include <nitro.h>
#include <string.h>

#include "config/battle_stage.h"

#if DEBUG_BATTLE_TOOLS

#include "constants/battle.h"
#include "constants/charcode.h"
#include "constants/graphics.h"
#include "constants/heap.h"
#include "generated/moves.h"

#include "struct_defs/battle_system.h"

#include "battle/battle_context.h"
#include "battle/battle_controller.h"
#include "battle/battle_controller_player.h"
#include "battle/battle_display.h"
#include "battle/battle_stage.h"
#include "battle/ov16_0223B140.h"
#include "battle/ov16_0223DF00.h"
#include "battle/ov16_02264798.h"
#include "battle/struct_ov16_0225BFFC_t.h"
#include "battle/struct_ov16_02265BBC.h"
#include "battle_anim/battle_anim_system.h"

#include "bg_window.h"
#include "font.h"
#include "heap.h"
#include "message_util.h"
#include "move_table.h"
#include "pokemon_sprite.h"
#include "string_gf.h"
#include "system.h"
#include "text.h"

#define MOVE_TESTER_KEYS (PAD_BUTTON_L | PAD_BUTTON_R)
#define MOVE_TESTER_LINE_HEIGHT 16

// Move flags read by the move-animation battle command (see ov16_022645B8)
#define MOVE_FLAG_KEEP_HEALTHBARS 0x40
#define MOVE_FLAG_HIDE_SHADOWS 0x80

typedef struct MoveTester {
    BOOL overlayShown;
    void *savedTextPixels; // the message window as it was before the overlay covered it
    BOOL animPlaying;
    BOOL healthbarsHidden;
    BOOL shadowsHidden;
    BOOL swappedOverlay; // the battle_anim overlay was loaded in place of trainer_ai for the animation
    // Out-of-sequence animations can end with a battler hidden (e.g. the charge turn of Fly or Dig, Roar)
    BOOL spriteHidden[MAX_BATTLERS];
} MoveTester;

static MoveTester sMoveTester;
static u16 sTestMove; // kept across battles

static u16 WrapMove(int move)
{
    int numMoves = MAX_MOVES - 1;

    return ((move - 1) % numMoves + numMoves) % numMoves + 1;
}

static void AppendAscii(String *string, const char *ascii)
{
    for (; *ascii != '\0'; ascii++) {
        char c = *ascii;

        if (c >= 'A' && c <= 'Z') {
            String_AppendChar(string, CHAR_A + (c - 'A'));
        } else if (c >= 'a' && c <= 'z') {
            String_AppendChar(string, CHAR_a + (c - 'a'));
        } else if (c >= '0' && c <= '9') {
            String_AppendChar(string, CHAR_0 + (c - '0'));
        } else if (c == '/') {
            String_AppendChar(string, CHAR_SLASH);
        } else if (c == ':') {
            String_AppendChar(string, CHAR_COLON);
        } else {
            String_AppendChar(string, CHAR_SPACE);
        }
    }
}

static u32 TextWindowSize(Window *window)
{
    return window->width * window->height * (window->colorMode == BG_COLOR_MODE_4BPP ? TILE_SIZE_4BPP : TILE_SIZE_8BPP);
}

static void ShowOverlay(BattleSystem *battleSys)
{
    Window *window = BattleSystem_Window(battleSys, 0);
    u32 size = TextWindowSize(window);

    sMoveTester.savedTextPixels = Heap_Alloc(HEAP_ID_BATTLE, size);
    memcpy(sMoveTester.savedTextPixels, window->pixels, size);
    sMoveTester.overlayShown = TRUE;
}

static void HideOverlay(BattleSystem *battleSys)
{
    Window *window = BattleSystem_Window(battleSys, 0);

    memcpy(window->pixels, sMoveTester.savedTextPixels, TextWindowSize(window));
    Window_CopyToVRAM(window);

    Heap_Free(sMoveTester.savedTextPixels);
    sMoveTester.savedTextPixels = NULL;
    sMoveTester.overlayShown = FALSE;
}

// Line 1: "Move 123: Tackle", line 2: key help and the 3D stage state
static void DrawOverlay(BattleSystem *battleSys)
{
    Window *window = BattleSystem_Window(battleSys, 0);
    String *line = String_Init(64, HEAP_ID_BATTLE);
    String *number = String_Init(8, HEAP_ID_BATTLE);
    String *moveName = MessageUtil_MoveName(sTestMove, HEAP_ID_BATTLE);

    Window_FillTilemap(window, 0xFF);

    AppendAscii(line, "Move ");
    String_FormatInt(number, sTestMove, 3, PADDING_MODE_ZEROES, CHARSET_MODE_EN);
    String_Concat(line, number);
    AppendAscii(line, ": ");
    String_Concat(line, moveName);
    Text_AddPrinterWithParams(window, FONT_MESSAGE, line, 0, 0, TEXT_SPEED_NO_TRANSFER, NULL);

    String_Clear(line);
    AppendAscii(line, BattleStage_IsEnabled() ? "A/Y play  SELECT 3D stage ON" : "A/Y play  SELECT 3D stage OFF");
    Text_AddPrinterWithParams(window, FONT_MESSAGE, line, 0, MOVE_TESTER_LINE_HEIGHT, TEXT_SPEED_NO_TRANSFER, NULL);

    Window_CopyToVRAM(window);

    String_Free(moveName);
    String_Free(number);
    String_Free(line);
}

static PokemonSprite *BattlerSprite(BattleSystem *battleSys, int battler)
{
    return BattleSystem_BattlerData(battleSys, battler)->unk_20;
}

static BOOL BattlerIsAlive(BattleSystem *battleSys, int battler)
{
    return battler < BattleSystem_MaxBattlers(battleSys) && BattleSystem_Context(battleSys)->battleMons[battler].curHP > 0;
}

// Battler 0 and the first enemy; in a double battle, fall back to the partner if one has fainted
static int PickBattler(BattleSystem *battleSys, int battler, int partner)
{
    if (BattlerIsAlive(battleSys, battler) == FALSE && BattlerIsAlive(battleSys, partner)) {
        return partner;
    }

    return battler;
}

static BOOL CanStartTestAnimation(BattleSystem *battleSys)
{
    if (BattleSystem_BattleType(battleSys) & BATTLE_TYPE_LINK) {
        return FALSE;
    }

    return BattleControllerPlayer_AIDoneSelecting(battleSys, BattleSystem_Context(battleSys));
}

// Mirrors the move-animation battle command (ov16_0225D9A8), minus the Substitute swap
static void StartTestAnimation(BattleSystem *battleSys, BattlerData *commandBattler, int attacker, int defender)
{
    MoveAnimation animation;
    u32 moveFlags = MoveTable_LoadParam(sTestMove, MOVEATTRIBUTE_FLAGS);

    MI_CpuClear8(&animation, sizeof(MoveAnimation));
    BattleController_SetMoveAnimation(battleSys, BattleSystem_Context(battleSys), &animation, 0, 0, attacker, defender, sTestMove);
    animation.isSubstitute = FALSE;

    // The idle bob would fight the animation over the sprite's Y offset
    ov16_022647D8(commandBattler);

    sMoveTester.healthbarsHidden = (moveFlags & MOVE_FLAG_KEEP_HEALTHBARS) == 0;
    sMoveTester.shadowsHidden = (moveFlags & MOVE_FLAG_HIDE_SHADOWS) != 0;

    for (int battler = 0; battler < BattleSystem_MaxBattlers(battleSys); battler++) {
        PokemonSprite *sprite = BattlerSprite(battleSys, battler);

        sMoveTester.spriteHidden[battler] = sprite != NULL && PokemonSprite_GetAttribute(sprite, MON_SPRITE_HIDE);
    }

    BattleSystem_SetRedHPSoundFlag(battleSys, 2);

    if (sMoveTester.healthbarsHidden) {
        ov16_0223F3EC(battleSys);
    }

    if (sMoveTester.shadowsHidden) {
        PokemonSpriteManager_HideShadows(BattleSystem_GetPokemonSpriteManager(battleSys));
    }

    // During command selection the trainer AI overlay sits where the animation code lives; swap
    // it out the same way the ball throw does, and swap it back once the animation is over
    sMoveTester.swappedOverlay = battleSys->overlayFlags != 0;

    if (sMoveTester.swappedOverlay) {
        BattleSystem_LoadFightOverlay(battleSys, 0);
    }

    BattleDisplay_StartMoveAnimation(battleSys, attacker, &animation);
    sMoveTester.animPlaying = TRUE;
}

// Returns TRUE while the animation is still playing
static BOOL UpdateTestAnimation(BattleSystem *battleSys, BattlerData *commandBattler)
{
    BattleAnimSystem *animSys = ov16_0223E008(battleSys);

    BattleAnimSystem_ExecuteScript(animSys);

    if (BattleAnimSystem_IsMoveActive(animSys)) {
        return TRUE;
    }

    BattleAnimSystem_FreeScriptData(animSys);
    BattleSystem_SetRedHPSoundFlag(battleSys, 0);

    if (sMoveTester.healthbarsHidden) {
        ov16_0223F3BC(battleSys);
    }

    if (sMoveTester.shadowsHidden) {
        PokemonSpriteManager_ShowShadows(BattleSystem_GetPokemonSpriteManager(battleSys));
    }

    for (int battler = 0; battler < BattleSystem_MaxBattlers(battleSys); battler++) {
        PokemonSprite *sprite = BattlerSprite(battleSys, battler);

        if (sprite != NULL) {
            PokemonSprite_SetAttribute(sprite, MON_SPRITE_HIDE, sMoveTester.spriteHidden[battler]);
        }
    }

    // The script has ended, and with it every task running animation code
    if (sMoveTester.swappedOverlay) {
        BattleSystem_LoadFightOverlay(battleSys, 1);
        sMoveTester.swappedOverlay = FALSE;
    }

    ov16_02264798(commandBattler, battleSys);
    sMoveTester.animPlaying = FALSE;

    return FALSE;
}

void BattleDebug_Init(void)
{
    MI_CpuClear8(&sMoveTester, sizeof(MoveTester));
}

// The battle is ending, possibly with the overlay up or an animation playing; the anim system cleans up after itself
void BattleDebug_Free(void)
{
    if (sMoveTester.savedTextPixels != NULL) {
        Heap_Free(sMoveTester.savedTextPixels);
    }

    MI_CpuClear8(&sMoveTester, sizeof(MoveTester));
}

BOOL BattleDebug_UpdateCommandMenu(BattleSystem *battleSys, BattlerData *commandBattler)
{
    BOOL redraw = FALSE;

    if (sMoveTester.animPlaying) {
        if (UpdateTestAnimation(battleSys, commandBattler) == FALSE && (gSystem.heldKeys & MOVE_TESTER_KEYS) != MOVE_TESTER_KEYS) {
            HideOverlay(battleSys);
        }

        return TRUE;
    }

    if ((gSystem.heldKeys & MOVE_TESTER_KEYS) != MOVE_TESTER_KEYS) {
        if (sMoveTester.overlayShown) {
            HideOverlay(battleSys);
        }

        return FALSE;
    }

    if (sTestMove == MOVE_NONE) {
        sTestMove = MOVE_POUND;
    }

    if (sMoveTester.overlayShown == FALSE) {
        ShowOverlay(battleSys);
        redraw = TRUE;
    }

    if (gSystem.pressedKeysRepeatable & PAD_KEY_LEFT) {
        sTestMove = WrapMove(sTestMove - 1);
        redraw = TRUE;
    } else if (gSystem.pressedKeysRepeatable & PAD_KEY_RIGHT) {
        sTestMove = WrapMove(sTestMove + 1);
        redraw = TRUE;
    } else if (gSystem.pressedKeysRepeatable & PAD_KEY_UP) {
        sTestMove = WrapMove(sTestMove + 10);
        redraw = TRUE;
    } else if (gSystem.pressedKeysRepeatable & PAD_KEY_DOWN) {
        sTestMove = WrapMove(sTestMove - 10);
        redraw = TRUE;
    }

    if (gSystem.pressedKeys & PAD_BUTTON_SELECT) {
        BattleStage_SetEnabled(!BattleStage_IsEnabled());
        redraw = TRUE;
    }

    if (redraw) {
        DrawOverlay(battleSys);
    }

    int player = PickBattler(battleSys, BATTLER_PLAYER_1, BATTLER_PLAYER_2);
    int enemy = PickBattler(battleSys, BATTLER_ENEMY_1, BATTLER_ENEMY_2);

    // The AI may still be picking its move (it runs alongside the menu after the first turn, from the
    // overlay the animation needs); ignore the press until it is done
    if (CanStartTestAnimation(battleSys) == FALSE) {
        return TRUE;
    }

    if (gSystem.pressedKeys & PAD_BUTTON_A) {
        StartTestAnimation(battleSys, commandBattler, player, enemy);
    } else if (gSystem.pressedKeys & PAD_BUTTON_Y) {
        StartTestAnimation(battleSys, commandBattler, enemy, player);
    }

    return TRUE;
}

#endif // DEBUG_BATTLE_TOOLS
