#include <nitro.h>
#include <string.h>

#include "constants/graphics.h"
#include "constants/narc.h"
#include "generated/genders.h"
#include "generated/string_padding_mode.h"
#include "generated/text_banks.h"

#include "struct_decls/pokedexdata_decl.h"

#include "game_opening/const_ov77_021D742C.h"
#include "main_menu/main_menu_util.h"

#include "bg_window.h"
#include "field_overworld_state.h"
#include "font.h"
#include "game_start.h"
#include "graphics.h"
#include "gx_layers.h"
#include "heap.h"
#include "location.h"
#include "main.h"
#include "map_header_util.h"
#include "message.h"
#include "message_util.h"
#include "overlay_manager.h"
#include "palette.h"
#include "party.h"
#include "play_time.h"
#include "pokedex.h"
#include "pokemon.h"
#include "pokemon_icon.h"
#include "savedata.h"
#include "screen_fade.h"
#include "sound.h"
#include "sound_playback.h"
#include "string_gf.h"
#include "string_template.h"
#include "system.h"
#include "text.h"
#include "trainer_info.h"
#include "vram_transfer.h"

#include "res/graphics/main_menu/main_menu_graphics.naix.h"
#include "res/text/bank/main_menu_options.h"

FS_EXTERN_OVERLAY(game_start);
FS_EXTERN_OVERLAY(game_opening);

/*
 * Dazzling Platinum main menu: a horizontal Continue / New Game card picker.
 *
 * Both screens use the same layout. BG2 holds the Continue card and BG3 the
 * New Game card, both 8bpp and pre-rendered by
 * tools/giratina_title/make_main_menu.py. Switching cards crossfades BG2 over
 * BG3 with alpha blending. BG0 is a 4bpp text layer for the save-dependent
 * parts of the Continue card and is only shown while that card is fully
 * visible.
 */

#define LAYER_TOP_TEXT        BG_LAYER_MAIN_0
#define LAYER_TOP_CONTINUE    BG_LAYER_MAIN_2
#define LAYER_TOP_NEW_GAME    BG_LAYER_MAIN_3
#define LAYER_BOTTOM_TEXT     BG_LAYER_SUB_0
#define LAYER_BOTTOM_CONTINUE BG_LAYER_SUB_2
#define LAYER_BOTTOM_NEW_GAME BG_LAYER_SUB_3

#define TEXT_PLTT_WHITE    1
#define TEXT_PLTT_SHADOW   2
#define TEXT_PLTT_LAVENDER 3
#define TEXT_COLOR_MAIN    TEXT_COLOR(TEXT_PLTT_WHITE, TEXT_PLTT_SHADOW, 0)
#define TEXT_COLOR_LEVEL   TEXT_COLOR(TEXT_PLTT_LAVENDER, TEXT_PLTT_SHADOW, 0)

// Palette indices reserved by the generator for the top screen badge row.
#define BADGE_FILL_PLTT_IDX 32
#define BADGE_RIM_PLTT_IDX  40
#define NUM_BADGES          8

#define ICON_PLTT_SLOT       1
#define NUM_ICON_PLTTS       3
#define ICON_TILES_PER_FRAME (4 * 4)
#define ICON_TILES           (2 * ICON_TILES_PER_FRAME)
#define ICON_BASE_TILE       1
#define ICON_ANIM_FRAMES     12

#define STATS_WINDOW_BASE_TILE    1
#define LEVEL_WINDOWS_BASE_TILE   (ICON_BASE_TILE + MAX_PARTY_SIZE * ICON_TILES)
#define LEVEL_WINDOW_TILES        (4 * 2)
#define LOCATION_WINDOW_BASE_TILE (LEVEL_WINDOWS_BASE_TILE + MAX_PARTY_SIZE * LEVEL_WINDOW_TILES)

#define STATS_VALUE_RIGHT    74
#define LEVEL_VALUE_RIGHT    28
#define LOCATION_VALUE_RIGHT 118

#define CROSSFADE_STEP 2
#define BLEND_MAX      16

enum MainMenuNextApp {
    NEXT_APP_TITLE_SCREEN = 0,
    NEXT_APP_LOAD_SAVE,
    NEXT_APP_GAME_INTRO,
};

enum MainMenuCard {
    MAIN_MENU_CARD_CONTINUE = 0,
    MAIN_MENU_CARD_NEW_GAME,
};

enum MainMenuAppState {
    MAIN_MENU_STATE_INIT = 0,
    MAIN_MENU_STATE_LOAD_GRAPHICS,
    MAIN_MENU_STATE_SELECT_CARD,
    MAIN_MENU_STATE_EXIT,
    MAIN_MENU_STATE_WAIT_SCREEN_TRANSITION,
};

typedef struct MainMenuAppData {
    BgConfig *bgConfig;
    SaveData *saveData;
    Pokedex *pokedex;
    TrainerInfo *trainerInfo;
    PlayTime *playTime;
    BOOL pokedexObtained;
    BOOL isNewGame;
    enum MainMenuCard card;
    enum MainMenuNextApp nextApplication;
    int blendEva; // BLEND_MAX shows Continue, 0 shows New Game
    int framesCounter;
    int partyCount;
    BOOL iconIsEgg[MAX_PARTY_SIZE];
    u8 iconPalette[MAX_PARTY_SIZE];
    u8 iconFrame;
    Window statsWindow;
    Window levelWindows[MAX_PARTY_SIZE];
    Window locationWindow;
} MainMenuAppData;

static const u8 sPartySlotX[MAX_PARTY_SIZE] = { 24, 96, 168, 24, 96, 168 };
static const u8 sPartySlotY[MAX_PARTY_SIZE] = { 48, 48, 48, 88, 88, 88 };

static const GXRgb sBadgeFillColors[NUM_BADGES] = {
    GX_RGB(20, 18, 17), // Coal
    GX_RGB(10, 21, 10), // Forest
    GX_RGB(25, 15, 7), // Cobble
    GX_RGB(7, 17, 27), // Fen
    GX_RGB(17, 13, 11), // Relic
    GX_RGB(21, 23, 27), // Mine
    GX_RGB(28, 23, 5), // Icicle
    GX_RGB(28, 10, 7), // Beacon
};

#define BADGE_RIM_EARNED_COLOR GX_RGB(31, 30, 31)

#define MAIN_BG_PLTT ((GXRgb *)HW_BG_PLTT)
#define SUB_BG_PLTT  ((GXRgb *)HW_DB_BG_PLTT)

static void InitLayer(BgConfig *bgConfig, enum BgLayer layer, u8 colorMode, u8 screenBase, u8 charBase, u8 priority)
{
    BgTemplate template = {
        .x = 0,
        .y = 0,
        .bufferSize = 0x800,
        .baseTile = 0,
        .screenSize = BG_SCREEN_SIZE_256x256,
        .colorMode = colorMode,
        .screenBase = screenBase,
        .charBase = charBase,
        .bgExtPltt = GX_BG_EXTPLTT_01,
        .priority = priority,
        .areaOver = 0,
        .mosaic = FALSE
    };

    Bg_InitFromTemplate(bgConfig, layer, &template, BG_TYPE_STATIC);
    Bg_ClearTilemap(bgConfig, layer);
}

static void InitEngineLayers(BgConfig *bgConfig, enum BgLayer textLayer, enum BgLayer continueLayer, enum BgLayer newGameLayer)
{
    InitLayer(bgConfig, textLayer, GX_BG_COLORMODE_16, GX_BG_SCRBASE_0xf000, GX_BG_CHARBASE_0x1c000, 0);
    InitLayer(bgConfig, continueLayer, GX_BG_COLORMODE_256, GX_BG_SCRBASE_0xf800, GX_BG_CHARBASE_0x00000, 1);
    InitLayer(bgConfig, newGameLayer, GX_BG_COLORMODE_256, GX_BG_SCRBASE_0xe800, GX_BG_CHARBASE_0x10000, 2);
    Bg_ClearTilesRange(textLayer, TILE_SIZE_4BPP, 0, HEAP_ID_MAIN_MENU);
}

static void InitMainMenuGraphics(MainMenuAppData *appData)
{
    GXBanks vramBanks = {
        GX_VRAM_BG_128_A,
        GX_VRAM_BGEXTPLTT_NONE,
        GX_VRAM_SUB_BG_128_C,
        GX_VRAM_SUB_BGEXTPLTT_NONE,
        GX_VRAM_OBJ_64_E,
        GX_VRAM_OBJEXTPLTT_NONE,
        GX_VRAM_SUB_OBJ_16_I,
        GX_VRAM_SUB_OBJEXTPLTT_NONE,
        GX_VRAM_TEX_0_B,
        GX_VRAM_TEXPLTT_01_FG
    };
    GraphicsModes graphicsModes = {
        GX_DISPMODE_GRAPHICS,
        GX_BGMODE_0,
        GX_BGMODE_0,
        GX_BG0_AS_2D
    };

    GXLayers_SetBanks(&vramBanks);
    SetAllGraphicsModes(&graphicsModes);
    GXLayers_DisableEngineALayers();
    GXLayers_DisableEngineBLayers();

    InitEngineLayers(appData->bgConfig, LAYER_TOP_TEXT, LAYER_TOP_CONTINUE, LAYER_TOP_NEW_GAME);
    InitEngineLayers(appData->bgConfig, LAYER_BOTTOM_TEXT, LAYER_BOTTOM_CONTINUE, LAYER_BOTTOM_NEW_GAME);

    Text_ResetAllPrinters();
}

static void LoadTextColors(GXRgb *pltt)
{
    pltt[TEXT_PLTT_WHITE] = GX_RGB(31, 31, 31);
    pltt[TEXT_PLTT_SHADOW] = GX_RGB(5, 2, 8);
    pltt[TEXT_PLTT_LAVENDER] = GX_RGB(25, 22, 30);
}

static void LoadCardGraphics(MainMenuAppData *appData)
{
    BgConfig *bgConfig = appData->bgConfig;
    u32 continueTopTilemap = menu_top_continue_NSCR;

    if (TrainerInfo_Gender(appData->trainerInfo) == GENDER_FEMALE) {
        continueTopTilemap = menu_top_continue_female_NSCR;
    }

    Graphics_LoadTilesToBgLayer(NARC_INDEX_GRAPHIC__MYSTERY, menu_top_continue_NCGR, bgConfig, LAYER_TOP_CONTINUE, 0, 0, FALSE, HEAP_ID_MAIN_MENU);
    Graphics_LoadTilemapToBgLayer(NARC_INDEX_GRAPHIC__MYSTERY, continueTopTilemap, bgConfig, LAYER_TOP_CONTINUE, 0, 0, FALSE, HEAP_ID_MAIN_MENU);
    Graphics_LoadTilesToBgLayer(NARC_INDEX_GRAPHIC__MYSTERY, menu_top_new_game_NCGR, bgConfig, LAYER_TOP_NEW_GAME, 0, 0, FALSE, HEAP_ID_MAIN_MENU);
    Graphics_LoadTilemapToBgLayer(NARC_INDEX_GRAPHIC__MYSTERY, menu_top_new_game_NSCR, bgConfig, LAYER_TOP_NEW_GAME, 0, 0, FALSE, HEAP_ID_MAIN_MENU);

    Graphics_LoadTilesToBgLayer(NARC_INDEX_GRAPHIC__MYSTERY, menu_bottom_continue_NCGR, bgConfig, LAYER_BOTTOM_CONTINUE, 0, 0, FALSE, HEAP_ID_MAIN_MENU);
    Graphics_LoadTilemapToBgLayer(NARC_INDEX_GRAPHIC__MYSTERY, menu_bottom_continue_NSCR, bgConfig, LAYER_BOTTOM_CONTINUE, 0, 0, FALSE, HEAP_ID_MAIN_MENU);
    Graphics_LoadTilesToBgLayer(NARC_INDEX_GRAPHIC__MYSTERY, menu_bottom_new_game_NCGR, bgConfig, LAYER_BOTTOM_NEW_GAME, 0, 0, FALSE, HEAP_ID_MAIN_MENU);
    Graphics_LoadTilemapToBgLayer(NARC_INDEX_GRAPHIC__MYSTERY, menu_bottom_new_game_NSCR, bgConfig, LAYER_BOTTOM_NEW_GAME, 0, 0, FALSE, HEAP_ID_MAIN_MENU);

    // Both cards of a screen share one palette, the NCLRs of the two variants are identical.
    Graphics_LoadPalette(NARC_INDEX_GRAPHIC__MYSTERY, menu_top_continue_NCLR, PAL_LOAD_MAIN_BG, 0, PALETTE_SIZE_BYTES * 16, HEAP_ID_MAIN_MENU);
    Graphics_LoadPalette(NARC_INDEX_GRAPHIC__MYSTERY, menu_bottom_continue_NCLR, PAL_LOAD_SUB_BG, 0, PALETTE_SIZE_BYTES * 16, HEAP_ID_MAIN_MENU);

    LoadTextColors(MAIN_BG_PLTT);
    LoadTextColors(SUB_BG_PLTT);

    for (int i = 0; i < NUM_BADGES; i++) {
        if (TrainerInfo_HasBadge(appData->trainerInfo, i)) {
            MAIN_BG_PLTT[BADGE_FILL_PLTT_IDX + i] = sBadgeFillColors[i];
            MAIN_BG_PLTT[BADGE_RIM_PLTT_IDX + i] = BADGE_RIM_EARNED_COLOR;
        }
    }
}

static void PrintRightAligned(Window *window, MessageLoader *msgLoader, StringTemplate *strTemplate, u32 entryID, int right, int y, TextColor color)
{
    String *string = MessageUtil_ExpandedString(strTemplate, msgLoader, entryID, HEAP_ID_MAIN_MENU);
    int x = right - (int)Font_CalcStringWidth(FONT_SYSTEM, string, Font_GetAttribute(FONT_SYSTEM, FONTATTR_LETTER_SPACING));

    Text_AddPrinterWithParamsAndColor(window, FONT_SYSTEM, string, x < 0 ? 0 : x, y, TEXT_SPEED_NO_TRANSFER, color, NULL);
    String_Free(string);
}

static void RenderTrainerStats(MainMenuAppData *appData, MessageLoader *msgLoader, StringTemplate *strTemplate)
{
    Window *window = &appData->statsWindow;

    Window_Add(appData->bgConfig, window, LAYER_TOP_TEXT, 17, 8, 10, 7, PLTT_0, STATS_WINDOW_BASE_TILE);
    Window_FillTilemap(window, 0);

    StringTemplate_SetPlayerName(strTemplate, 0, appData->trainerInfo);
    PrintRightAligned(window, msgLoader, strTemplate, MainMenuOptions_Text_PlayerName, STATS_VALUE_RIGHT, 4, TEXT_COLOR_MAIN);

    StringTemplate_SetNumber(strTemplate, 0, PlayTime_GetHours(appData->playTime), 3, PADDING_MODE_NONE, CHARSET_MODE_EN);
    StringTemplate_SetNumber(strTemplate, 1, PlayTime_GetMinutes(appData->playTime), 2, PADDING_MODE_ZEROES, CHARSET_MODE_EN);
    PrintRightAligned(window, msgLoader, strTemplate, MainMenuOptions_Text_PlayTime, STATS_VALUE_RIGHT, 21, TEXT_COLOR_MAIN);

    if (appData->pokedexObtained) {
        StringTemplate_SetNumber(strTemplate, 0, Pokedex_CountSeen(appData->pokedex), 3, PADDING_MODE_NONE, CHARSET_MODE_EN);
        PrintRightAligned(window, msgLoader, strTemplate, MainMenuOptions_Text_SeenSpeciesCount, STATS_VALUE_RIGHT, 38, TEXT_COLOR_MAIN);
    } else {
        PrintRightAligned(window, msgLoader, strTemplate, MainMenuOptions_Text_NoPokedex, STATS_VALUE_RIGHT, 38, TEXT_COLOR_MAIN);
    }

    Window_CopyToVRAM(window);
}

static void DrawPartyIcons(MainMenuAppData *appData)
{
    for (int i = 0; i < appData->partyCount; i++) {
        u16 baseTile = ICON_BASE_TILE + i * ICON_TILES + appData->iconFrame * ICON_TILES_PER_FRAME;
        int tileX = sPartySlotX[i] / TILE_WIDTH_PIXELS;
        int tileY = sPartySlotY[i] / TILE_HEIGHT_PIXELS;

        for (int row = 0; row < 4; row++) {
            for (int col = 0; col < 4; col++) {
                Bg_FillTilemapRect(appData->bgConfig, LAYER_BOTTOM_TEXT, baseTile + row * 4 + col, tileX + col, tileY + row, 1, 1, appData->iconPalette[i]);
            }
        }
    }

    Bg_ScheduleTilemapTransfer(appData->bgConfig, LAYER_BOTTOM_TEXT);
}

static void RenderParty(MainMenuAppData *appData, MessageLoader *msgLoader, StringTemplate *strTemplate)
{
    Party *party = SaveData_GetParty(appData->saveData);

    appData->partyCount = Party_GetCurrentCount(party);

    if (appData->partyCount > MAX_PARTY_SIZE) {
        appData->partyCount = MAX_PARTY_SIZE;
    }

    Graphics_LoadPalette(NARC_INDEX_POKETOOL__ICONGRA__PL_POKE_ICON, PokeIconPalettesFileIndex(), PAL_LOAD_SUB_BG, PLTT_OFFSET(ICON_PLTT_SLOT), PALETTE_SIZE_BYTES * NUM_ICON_PLTTS, HEAP_ID_MAIN_MENU);

    for (int i = 0; i < appData->partyCount; i++) {
        Pokemon *mon = Party_GetPokemonBySlotIndex(party, i);
        NNSG2dCharacterData *charData;
        void *ncgrBuffer = Graphics_GetCharData(NARC_INDEX_POKETOOL__ICONGRA__PL_POKE_ICON, Pokemon_IconSpriteIndex(mon), FALSE, &charData, HEAP_ID_MAIN_MENU);

        // Icon graphics use 1D sprite mapping, so each 32x32 frame is 16 row-major tiles.
        DC_FlushRange(charData->pRawData, ICON_TILES * TILE_SIZE_4BPP);
        Bg_LoadTiles(appData->bgConfig, LAYER_BOTTOM_TEXT, charData->pRawData, ICON_TILES * TILE_SIZE_4BPP, ICON_BASE_TILE + i * ICON_TILES);
        Heap_Free(ncgrBuffer);

        appData->iconPalette[i] = ICON_PLTT_SLOT + Pokemon_IconPaletteIndex(mon);
        appData->iconIsEgg[i] = Pokemon_GetValue(mon, MON_DATA_IS_EGG, NULL);

        Window *window = &appData->levelWindows[i];

        Window_Add(appData->bgConfig, window, LAYER_BOTTOM_TEXT, sPartySlotX[i] / TILE_WIDTH_PIXELS + 4, sPartySlotY[i] / TILE_HEIGHT_PIXELS + 1, 4, 2, PLTT_0, LEVEL_WINDOWS_BASE_TILE + i * LEVEL_WINDOW_TILES);
        Window_FillTilemap(window, 0);

        if (!appData->iconIsEgg[i]) {
            StringTemplate_SetNumber(strTemplate, 0, Pokemon_GetValue(mon, MON_DATA_LEVEL, NULL), 3, PADDING_MODE_NONE, CHARSET_MODE_EN);
            PrintRightAligned(window, msgLoader, strTemplate, MainMenuOptions_Text_Level, LEVEL_VALUE_RIGHT, 1, TEXT_COLOR_LEVEL);
        }

        Window_CopyToVRAM(window);
    }

    DrawPartyIcons(appData);
}

static void RenderLocation(MainMenuAppData *appData)
{
    Window *window = &appData->locationWindow;
    Location *location = FieldOverworldState_GetPlayerLocation(SaveData_GetFieldOverworldState(appData->saveData));
    String *string = String_Init(64, HEAP_ID_MAIN_MENU);

    MapHeader_LoadName(location->mapId, HEAP_ID_MAIN_MENU, string);

    Window_Add(appData->bgConfig, window, LAYER_BOTTOM_TEXT, 14, 15, 16, 2, PLTT_0, LOCATION_WINDOW_BASE_TILE);
    Window_FillTilemap(window, 0);

    int x = LOCATION_VALUE_RIGHT - (int)Font_CalcStringWidth(FONT_SYSTEM, string, Font_GetAttribute(FONT_SYSTEM, FONTATTR_LETTER_SPACING));
    Text_AddPrinterWithParamsAndColor(window, FONT_SYSTEM, string, x < 0 ? 0 : x, 2, TEXT_SPEED_NO_TRANSFER, TEXT_COLOR_MAIN, NULL);

    Window_CopyToVRAM(window);
    String_Free(string);
}

static void RenderSaveInfo(MainMenuAppData *appData)
{
    MessageLoader *msgLoader = MessageLoader_Init(MSG_LOADER_LOAD_ON_DEMAND, NARC_INDEX_MSGDATA__PL_MSG, TEXT_BANK_MAIN_MENU_OPTIONS, HEAP_ID_MAIN_MENU);
    StringTemplate *strTemplate = StringTemplate_Default(HEAP_ID_MAIN_MENU);

    RenderTrainerStats(appData, msgLoader, strTemplate);
    RenderParty(appData, msgLoader, strTemplate);
    RenderLocation(appData);

    StringTemplate_Free(strTemplate);
    MessageLoader_Free(msgLoader);
}

static void UpdateIconAnimation(MainMenuAppData *appData)
{
    if (appData->partyCount == 0 || appData->framesCounter % ICON_ANIM_FRAMES != 0) {
        return;
    }

    appData->iconFrame ^= 1;
    DrawPartyIcons(appData);
}

static void UpdateCrossfade(MainMenuAppData *appData)
{
    int target = appData->card == MAIN_MENU_CARD_CONTINUE ? BLEND_MAX : 0;

    if (appData->blendEva < target) {
        appData->blendEva += CROSSFADE_STEP;
    } else if (appData->blendEva > target) {
        appData->blendEva -= CROSSFADE_STEP;
    }
}

static void ApplyBlend(int eva)
{
    BOOL showText = eva == BLEND_MAX;

    G2_SetBlendAlpha(GX_BLEND_PLANEMASK_BG2, GX_BLEND_PLANEMASK_BG3, eva, BLEND_MAX - eva);
    G2S_SetBlendAlpha(GX_BLEND_PLANEMASK_BG2, GX_BLEND_PLANEMASK_BG3, eva, BLEND_MAX - eva);
    GXLayers_EngineAToggleLayers(GX_PLANEMASK_BG0, showText);
    GXLayers_EngineBToggleLayers(GX_PLANEMASK_BG0, showText);
}

static void FreeApplicationResources(ApplicationManager *appMan)
{
    MainMenuAppData *appData = ApplicationManager_Data(appMan);

    SetVBlankCallback(NULL, NULL);

    if (appData->statsWindow.bgConfig) {
        Window_Remove(&appData->statsWindow);
    }

    for (int i = 0; i < MAX_PARTY_SIZE; i++) {
        if (appData->levelWindows[i].bgConfig) {
            Window_Remove(&appData->levelWindows[i]);
        }
    }

    if (appData->locationWindow.bgConfig) {
        Window_Remove(&appData->locationWindow);
    }

    G2_BlendNone();
    G2S_BlendNone();

    Bg_FreeTilemapBuffer(appData->bgConfig, LAYER_TOP_TEXT);
    Bg_FreeTilemapBuffer(appData->bgConfig, LAYER_TOP_CONTINUE);
    Bg_FreeTilemapBuffer(appData->bgConfig, LAYER_TOP_NEW_GAME);
    Bg_FreeTilemapBuffer(appData->bgConfig, LAYER_BOTTOM_TEXT);
    Bg_FreeTilemapBuffer(appData->bgConfig, LAYER_BOTTOM_CONTINUE);
    Bg_FreeTilemapBuffer(appData->bgConfig, LAYER_BOTTOM_NEW_GAME);
    Heap_Free(appData->bgConfig);
}

static void MainMenuVBlankCallback(void *data)
{
    MainMenuAppData *appData = data;

    ApplyBlend(appData->blendEva);
    VramTransfer_Process();
    Bg_RunScheduledUpdates(appData->bgConfig);

    OS_SetIrqCheckFlag(OS_IE_V_BLANK);
}

static BOOL MainMenu_Init(ApplicationManager *appMan, int *unused)
{
    Heap_Create(HEAP_ID_APPLICATION, HEAP_ID_MAIN_MENU, HEAP_SIZE_MAIN_MENU);

    MainMenuAppData *appData = ApplicationManager_NewData(appMan, sizeof(MainMenuAppData), HEAP_ID_MAIN_MENU);
    memset(appData, 0, sizeof(MainMenuAppData));
    appData->bgConfig = BgConfig_New(HEAP_ID_MAIN_MENU);

    SetScreenColorBrightness(DS_SCREEN_MAIN, COLOR_BLACK);
    SetScreenColorBrightness(DS_SCREEN_SUB, COLOR_BLACK);

    appData->saveData = ((ApplicationArgs *)ApplicationManager_Args(appMan))->saveData;
    appData->trainerInfo = SaveData_GetTrainerInfo(appData->saveData);
    appData->pokedex = SaveData_GetPokedex(appData->saveData);
    appData->playTime = SaveData_GetPlayTime(appData->saveData);
    appData->pokedexObtained = Pokedex_IsObtained(appData->pokedex);
    appData->card = MAIN_MENU_CARD_CONTINUE;
    appData->blendEva = BLEND_MAX;

    MainMenuUtil_Init(HEAP_ID_MAIN_MENU);

    if (!SaveData_DataExists(appData->saveData)) {
        appData->isNewGame = TRUE;
    }

    Sound_ConfigureBGMChannelsAndReverb(SOUND_CHANNEL_CONFIG_DEFAULT);
    Sound_SetScene(SOUND_SCENE_NONE);

    return TRUE;
}

static BOOL MainMenu_Main(ApplicationManager *appMan, int *state)
{
    MainMenuAppData *appData = ApplicationManager_Data(appMan);

    appData->framesCounter++;

    switch (*state) {
    case MAIN_MENU_STATE_INIT:
        if (appData->isNewGame == TRUE) {
            appData->nextApplication = NEXT_APP_GAME_INTRO;
            MainMenuUtil_StartScreenFadeToState(FADE_TYPE_BRIGHTNESS_OUT, MAIN_MENU_STATE_EXIT, state, MAIN_MENU_STATE_WAIT_SCREEN_TRANSITION);
        } else {
            InitMainMenuGraphics(appData);
            *state = MAIN_MENU_STATE_LOAD_GRAPHICS;
        }
        break;
    case MAIN_MENU_STATE_LOAD_GRAPHICS:
        LoadCardGraphics(appData);
        RenderSaveInfo(appData);
        ApplyBlend(appData->blendEva);

        SetVBlankCallback(MainMenuVBlankCallback, appData);
        MainMenuUtil_StartScreenFadeToState(FADE_TYPE_BRIGHTNESS_IN, MAIN_MENU_STATE_SELECT_CARD, state, MAIN_MENU_STATE_WAIT_SCREEN_TRANSITION);
        break;
    case MAIN_MENU_STATE_SELECT_CARD:
        if (JOY_NEW(PAD_BUTTON_A)) {
            Sound_PlayEffect(SEQ_SE_CONFIRM);
            appData->nextApplication = appData->card == MAIN_MENU_CARD_CONTINUE ? NEXT_APP_LOAD_SAVE : NEXT_APP_GAME_INTRO;
            MainMenuUtil_StartScreenFadeToState(FADE_TYPE_BRIGHTNESS_OUT, MAIN_MENU_STATE_EXIT, state, MAIN_MENU_STATE_WAIT_SCREEN_TRANSITION);
            break;
        }

        if (JOY_NEW(PAD_BUTTON_B)) {
            Sound_PlayEffect(SEQ_SE_CONFIRM);
            appData->nextApplication = NEXT_APP_TITLE_SCREEN;
            MainMenuUtil_SetFadeToWhite(TRUE);
            MainMenuUtil_StartScreenFadeToState(FADE_TYPE_BRIGHTNESS_OUT, MAIN_MENU_STATE_EXIT, state, MAIN_MENU_STATE_WAIT_SCREEN_TRANSITION);
            break;
        }

        if (JOY_NEW(PAD_KEY_LEFT | PAD_KEY_RIGHT)) {
            Sound_PlayEffect(SEQ_SE_CONFIRM);
            appData->card = appData->card == MAIN_MENU_CARD_CONTINUE ? MAIN_MENU_CARD_NEW_GAME : MAIN_MENU_CARD_CONTINUE;
        }
        break;
    case MAIN_MENU_STATE_EXIT:
        if (appData->isNewGame) {
            Heap_Free(appData->bgConfig);
        } else {
            FreeApplicationResources(appMan);
        }
        return TRUE;
    case MAIN_MENU_STATE_WAIT_SCREEN_TRANSITION:
        MainMenuUtil_CheckScreenFadeDone(state);
        break;
    }

    if (appData->isNewGame == FALSE) {
        UpdateCrossfade(appData);
        UpdateIconAnimation(appData);
    }

    return FALSE;
}

static void EnqueueNextApplication(MainMenuAppData *appData)
{
    switch (appData->nextApplication) {
    case NEXT_APP_LOAD_SAVE:
        EnqueueApplication(FS_OVERLAY_ID(game_start), &gGameStartLoadSaveAppTemplate);
        break;
    case NEXT_APP_GAME_INTRO:
        EnqueueApplication(FS_OVERLAY_ID(game_start), &gGameStartRowanIntroAppTemplate);
        break;
    case NEXT_APP_TITLE_SCREEN:
        EnqueueApplication(FS_OVERLAY_ID(game_opening), &gTitleScreenAppTemplate);
        break;
    }
}

static BOOL MainMenu_Exit(ApplicationManager *appMan, int *unused)
{
    MainMenuAppData *appData = ApplicationManager_Data(appMan);

    EnqueueNextApplication(appData);

    ApplicationManager_FreeData(appMan);
    Heap_Destroy(HEAP_ID_MAIN_MENU);

    MainMenuUtil_ToggleTerminateOnGBACartRemoved(FALSE);

    return TRUE;
}

const ApplicationManagerTemplate gMainMenuAppTemplate = {
    MainMenu_Init,
    MainMenu_Main,
    MainMenu_Exit,
    FS_OVERLAY_ID_NONE
};
