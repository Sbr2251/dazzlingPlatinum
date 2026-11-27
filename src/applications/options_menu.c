#include "applications/options_menu.h"

#include <nitro.h>
#include <string.h>

#include "constants/charcode.h"
#include "constants/heap.h"
#include "constants/narc.h"

#ifdef SDK_PORT
#include <stdlib.h>
#include <SDL3/SDL.h>

#include "port/sim_config_prj.h"
#include "port/sim_wide.h"
#include <simulator/sim.h>
#include <simulator/sim_headless.h>
#include <simulator/sim_layout.h>
#include <simulator/sim_platform.h>
#endif

#include "bg_window.h"
#include "font.h"
#include "game_options.h"
#include "graphics.h"
#include "gx_layers.h"
#include "heap.h"
#include "menu.h"
#include "message.h"
#include "narc.h"
#include "network_icon.h"
#include "overlay_manager.h"
#include "palette.h"
#include "render_text.h"
#include "render_window.h"
#include "screen_fade.h"
#include "sound.h"
#include "sound_playback.h"
#include "sprite_system.h"
#include "string_gf.h"
#include "system.h"
#include "text.h"
#include "vram_transfer.h"

#include "res/graphics/options_menu/config_gra.naix"
#include "res/text/bank/options_menu.h"

#define MENU_TITLE_BASE_TILE      10
#define MENU_TITLE_WIDTH          12
#define MENU_TITLE_HEIGHT         2
#define ENTRIES_BASE_TILE         (MENU_TITLE_BASE_TILE + MENU_TITLE_WIDTH * MENU_TITLE_HEIGHT)
#define ENTRIES_WIDTH             30
#define ENTRIES_HEIGHT            14
#define DESCRIPTION_BASE_TILE     (ENTRIES_BASE_TILE + ENTRIES_WIDTH * ENTRIES_HEIGHT)
#define DESCRIPTION_WIDTH         27
#define DESCRIPTION_HEIGHT        4
#define STANDARD_WINDOW_BASE_TILE (DESCRIPTION_BASE_TILE + DESCRIPTION_WIDTH * DESCRIPTION_HEIGHT)
#define MESSAGE_BOX_BASE_TILE     (STANDARD_WINDOW_BASE_TILE + 9)
#define CONFIRMATION_BASE_TILE    (MESSAGE_BOX_BASE_TILE + 30)

#define CHOICES_X     (12 * 8 + 4)
#define CHOICES_WIDTH (48 * 8)

#define SINGLE_ENTRY_HEIGHT 16
#define FIRST_ENTRY_OFFSET  24

#define NUM_WINDOWS      3
#define NUM_BG_TEMPLATES 5

#define HEAP_ALLOCATION_SIZE      0x10000
#define WIDE_HEAP_ALLOCATION_SIZE 0x20000

#ifdef SDK_PORT
#define WIDE_2D_WIDTH                  342
#define WIDE_MENU_TITLE_BASE_TILE      10
#define WIDE_MENU_TITLE_WIDTH          41
#define WIDE_MENU_TITLE_HEIGHT         2
#define WIDE_ENTRIES_BASE_TILE         (WIDE_MENU_TITLE_BASE_TILE + WIDE_MENU_TITLE_WIDTH * WIDE_MENU_TITLE_HEIGHT)
#define WIDE_ENTRIES_WIDTH             41
#define WIDE_ENTRIES_HEIGHT            14
#define WIDE_DESCRIPTION_BASE_TILE     (WIDE_ENTRIES_BASE_TILE + WIDE_ENTRIES_WIDTH * WIDE_ENTRIES_HEIGHT)
#define WIDE_DESCRIPTION_WIDTH         38
#define WIDE_DESCRIPTION_HEIGHT        4
#define WIDE_STANDARD_WINDOW_BASE_TILE (WIDE_DESCRIPTION_BASE_TILE + WIDE_DESCRIPTION_WIDTH * WIDE_DESCRIPTION_HEIGHT)
#define WIDE_MESSAGE_BOX_BASE_TILE     (WIDE_STANDARD_WINDOW_BASE_TILE + 9)
#define WIDE_CONFIRMATION_BASE_TILE    (WIDE_MESSAGE_BOX_BASE_TILE + 30)

#define WIDE_LABEL_X       8
#define WIDE_CHOICES_X     116
#define WIDE_CHOICES_WIDTH (WIDE_ENTRIES_WIDTH * 8 - WIDE_CHOICES_X)
#define WIDE_FRAME_SPLIT_X 164

#define WIDE_MAX_TAB_ROWS     7
#define WIDE_MAX_ROW_CHOICES  5

enum OptionsWideTab {
    WIDE_TAB_GAME = 0,
    WIDE_TAB_PLAY,
    WIDE_TAB_DISPLAY,
    WIDE_TAB_FX,
    WIDE_TAB_COUNT,
};

enum OptionsWideRowID {
    WIDE_ROW_TEXT_SPEED = 0,
    WIDE_ROW_BATTLE_SCENE,
    WIDE_ROW_BATTLE_STYLE,
    WIDE_ROW_SOUND_MODE,
    WIDE_ROW_BUTTON_MODE,
    WIDE_ROW_FRAME,

    WIDE_ROW_60FPS,
    WIDE_ROW_BATTLE_SPEED,
    WIDE_ROW_MEGA_CUTSCENE,
    WIDE_ROW_BATTLE_HUD,
    WIDE_ROW_FOLLOWER,
    WIDE_ROW_PHENOMENA,

    WIDE_ROW_VOLUME,
    WIDE_ROW_3D_RES,
    WIDE_ROW_2D_FILTER,
    WIDE_ROW_LAYOUT,
    WIDE_ROW_FULLSCREEN,
    WIDE_ROW_TOUCH_PAD,

    WIDE_ROW_WEATHER_FX,
    WIDE_ROW_LIGHTING,
    WIDE_ROW_ARENA_TINT,
    WIDE_ROW_PARTICLES,
    WIDE_ROW_WATER_REFL,
    WIDE_ROW_CINEMATICS,

    WIDE_ROW_CLOSE,
};

enum OptionsWideOptIdx {
    WIDE_OPT_60FPS = 0,
    WIDE_OPT_BATTLE_SPEED,
    WIDE_OPT_MEGA_CUTSCENE,
    WIDE_OPT_BATTLE_HUD,
    WIDE_OPT_FOLLOWER,
    WIDE_OPT_PHENOMENA,
    WIDE_OPT_VOLUME,
    WIDE_OPT_3D_RES,
    WIDE_OPT_2D_FILTER,
    WIDE_OPT_LAYOUT,
    WIDE_OPT_FULLSCREEN,
    WIDE_OPT_TOUCH_PAD,
    WIDE_OPT_WEATHER_FX,
    WIDE_OPT_LIGHTING,
    WIDE_OPT_ARENA_TINT,
    WIDE_OPT_PARTICLES,
    WIDE_OPT_WATER_REFL,
    WIDE_OPT_CINEMATICS,
    WIDE_OPT_COUNT,
};
#endif

enum OptionsMenuEntryID {
    ENTRY_TEXT_SPEED = 0,
    ENTRY_SOUND_MODE,
    ENTRY_BATTLE_SCENE,
    ENTRY_BATTLE_STYLE,
    ENTRY_BUTTON_MODE,
    ENTRY_MESSAGE_BOX_FRAME,
    ENTRY_CLOSE,

    MAX_ENTRIES,
};

typedef struct OptionsMenuEntry {
    u16 numChoices;
    u16 selected;
    String *choices[20];
} OptionsMenuEntry;

typedef struct OptionsMenuData {
    enum HeapID heapID;
    int state;
    int subState;
    int dummy0C;
    u32 saveSelections : 2;
    u32 cursor : 3;
    u32 dummy10_5 : 16;
    u32 redrawMessageBox : 1;
    u32 dummy10_22 : 10;
    BgConfig *bgConfig;
    OptionsMenu options;
    Options *saveOptions;
    MessageLoader *msgLoader;
    void *nscrBuffer;
    NNSG2dScreenData *tilemapData;

    union {
        Window asArray[NUM_WINDOWS];
        struct {
            Window title;
            Window entries;
            Window description;
        };
    } windows;

    union {
        OptionsMenuEntry asArray[MAX_ENTRIES];
        struct {
            OptionsMenuEntry textSpeed;
            OptionsMenuEntry soundMode;
            OptionsMenuEntry battleScene;
            OptionsMenuEntry battleStyle;
            OptionsMenuEntry buttonMode;
            OptionsMenuEntry messageBoxStyle;
            OptionsMenuEntry close;
        };
    } entries;

    Menu *yesNoChoice;
    u32 textPrinter;
    void *dummy2B0;
    void *dummy2B4;
    void *dummy2B8;

    BOOL wideMode;
#ifdef SDK_PORT
    u8 activeTab;
    u8 wideSelected[WIDE_OPT_COUNT];
    u8 wideInitial[WIDE_OPT_COUNT];
    u16 wideChoiceX[WIDE_MAX_TAB_ROWS][WIDE_MAX_ROW_CHOICES];
    u16 wideChoiceW[WIDE_MAX_TAB_ROWS][WIDE_MAX_ROW_CHOICES];
    SIM_Config_prj_type snapPrj;
    SIM_config_type snapSim;
#endif
} OptionsMenuData;

static void OptionsMenuVBlank(void *data);

static int SetupMenuVisuals(OptionsMenuData *menuData);
static void SetVRAMBanks(void);
static void SetupBgs(OptionsMenuData *menuData);
static void LoadBgTiles(OptionsMenuData *menuData);
static void SetupWindows(OptionsMenuData *menuData);

static void PrintTitleAndEntries(OptionsMenuData *param0);
static void PrintEntryChoices(OptionsMenuData *menuData, u16 entry);
static void PrintEntryDescription(OptionsMenuData *menuData, u16 entry, BOOL scheduleVRAMCopy);
static void PrintBankEntryAsDescription(OptionsMenuData *menuData, u16 entry, BOOL scheduleVRAMCopy);
static BOOL IsTextPrinterDone(const OptionsMenuData *menuData);
static void LoadAllEntryChoices(OptionsMenuData *menuData);

static BOOL ChangesWereMade(OptionsMenuData *menuData);
static void DrawConfirmationPrompt(OptionsMenuData *menuData);

static void ProcessMainInput(OptionsMenuData *menuData);
#ifdef SDK_BUILD_ARM
static u32 ProcessConfirmationInput(OptionsMenuData *menuData);
#else
static u64 ProcessConfirmationInput(OptionsMenuData *menuData);
#endif

static int TeardownMenuData(OptionsMenuData *menuData);
static void TeardownBgs(OptionsMenuData *menuData);
static void TeardownTilemaps(OptionsMenuData *menuData);
static void TeardownWindows(OptionsMenuData *menuData);

#ifdef SDK_PORT
static void WideSnapshotConfig(OptionsMenuData *menuData);
static void WideApplyAndSaveOrRevert(OptionsMenuData *menuData, BOOL *outLayoutChanged, SIM_config_screen_layout_type *outNewLayout);
static void WideDrawTitleAndTabs(OptionsMenuData *menuData);
static void WideDrawCurrentTabEntries(OptionsMenuData *menuData);
static void WidePrintRowChoices(OptionsMenuData *menuData, u16 rowIdx, BOOL applyLive);
static void WidePrintCurrentRowDescription(OptionsMenuData *menuData, BOOL scheduleVRAMCopy);
static BOOL WideProcessMainInput(OptionsMenuData *menuData);
static BOOL WideChangesWereMade(const OptionsMenuData *menuData);
static void WideDrainPendingTouch(void);
#endif

BOOL OptionsMenu_IsWidePixelMode(void)
{
#ifdef SDK_PORT
    if (!SIM_Wide_IsWideLayout()) {
        return FALSE;
    }
    if (!SIM_Headless_Enabled()) {
        return TRUE;
    }
    {
        const char *wideOpts = getenv("SIM_FX_WIDE_OPTIONS");
        const char *interactive = getenv("SIM_HEADLESS_INTERACTIVE_FX");
        if ((wideOpts != NULL && wideOpts[0] == '1') || (interactive != NULL && interactive[0] == '1')) {
            return TRUE;
        }
    }
    return FALSE;
#else
    return FALSE;
#endif
}

BOOL OptionsMenu_Init(ApplicationManager *appMan, int *state)
{
    OptionsMenuData *menuData = NULL;
    Options *options = ApplicationManager_Args(appMan);
    BOOL wideMode = OptionsMenu_IsWidePixelMode();

#ifdef SDK_PORT
    if (wideMode) {
        SIM_Wide_PushScene(SIM_WIDE_SCENE_MENU_SINGLE);
        SIM_Wide_SetWide2DWidth(WIDE_2D_WIDTH);
        SIM_Wide_SetMainTouchEnabled(1);
    }
#endif

    Heap_Create(HEAP_ID_APPLICATION, HEAP_ID_OPTIONS_MENU, wideMode ? WIDE_HEAP_ALLOCATION_SIZE : HEAP_ALLOCATION_SIZE);

    menuData = ApplicationManager_NewData(appMan, sizeof(OptionsMenuData), HEAP_ID_OPTIONS_MENU);
    memset(menuData, 0, sizeof(OptionsMenuData));

    menuData->wideMode = wideMode;
    menuData->options.textSpeed = Options_TextSpeed(options);
    menuData->options.battleScene = Options_BattleScene(options);
    menuData->options.battleStyle = Options_BattleStyle(options);
    menuData->options.soundMode = Options_SoundMode(options);
    menuData->options.buttonMode = Options_ButtonMode(options);
    menuData->options.messageBoxStyle = Options_Frame(options);
    menuData->heapID = HEAP_ID_OPTIONS_MENU;
    menuData->saveOptions = options;

#ifdef SDK_PORT
    if (menuData->wideMode) {
        WideSnapshotConfig(menuData);
    }
#endif

    RenderControlFlags_SetCanABSpeedUpPrint(FALSE);

    return TRUE;
}

BOOL OptionsMenu_Exit(ApplicationManager *appMan, int *state)
{
    OptionsMenuData *menuData = ApplicationManager_Data(appMan);
    enum HeapID heapID = menuData->heapID;
    BOOL wideMode = menuData->wideMode;
#ifdef SDK_PORT
    BOOL layoutChanged = FALSE;
    SIM_config_screen_layout_type newLayout = SIM_CONFIG_SCREEN_LAYOUT_WIDE;
#endif

    if (menuData->saveSelections == 1) {
        menuData->options.textSpeed = menuData->entries.textSpeed.selected;
        menuData->options.battleScene = menuData->entries.battleScene.selected;
        menuData->options.battleStyle = menuData->entries.battleStyle.selected;
        menuData->options.soundMode = menuData->entries.soundMode.selected;
        menuData->options.buttonMode = menuData->entries.buttonMode.selected;
        menuData->options.messageBoxStyle = menuData->entries.messageBoxStyle.selected;
    }

    Options_SetTextSpeed(menuData->saveOptions, menuData->options.textSpeed);
    Options_SetBattleScene(menuData->saveOptions, menuData->options.battleScene);
    Options_SetBattleStyle(menuData->saveOptions, menuData->options.battleStyle);
    Options_SetSoundMode(menuData->saveOptions, menuData->options.soundMode);
    Options_SetButtonMode(menuData->saveOptions, menuData->options.buttonMode);
    Options_SetFrame(menuData->saveOptions, menuData->options.messageBoxStyle);
    Sound_SetPlaybackMode(menuData->options.soundMode);
    Options_SetSystemButtonMode(NULL, menuData->options.buttonMode);

#ifdef SDK_PORT
    if (wideMode) {
        WideApplyAndSaveOrRevert(menuData, &layoutChanged, &newLayout);
    }
#endif

    RenderControlFlags_SetCanABSpeedUpPrint(TRUE);

    ApplicationManager_FreeData(appMan);
    Heap_Destroy(heapID);

#ifdef SDK_PORT
    if (wideMode) {
        SIM_Wide_SetMainTouchEnabled(0);
        SIM_Wide_SetWide2DWidth(0);
        SIM_Wide_PopScene();
    }
    if (layoutChanged) {
        SIM_Layout_SetWideEnabled(newLayout == SIM_CONFIG_SCREEN_LAYOUT_WIDE ? 1 : 0);
    }
#endif

    return TRUE;
}

enum OptonsMenuState {
    STATE_SETUP_MENU_VISUALS = 0,
    STATE_WAIT_FOR_FADE_IN,
    STATE_HANDLE_INPUT,
    STATE_CONFIRM_NEW_SETTINGS,
    STATE_WAIT_CONFIRM_NEW_SETTINGS,
    STATE_HANDLE_YES_NO_INPUT,
    STATE_START_VISUAL_TEARDOWN,
    STATE_WAIT_FOR_FADE_OUT,
    STATE_TEARDOWN,
};

BOOL OptionsMenu_Main(ApplicationManager *appMan, int *state)
{
    OptionsMenuData *menuData = ApplicationManager_Data(appMan);
    #ifdef SDK_BUILD_ARM
    u32 choiceYesNo;
    #else
    u64 choiceYesNo;
    #endif

    switch (menuData->state) {
    case STATE_SETUP_MENU_VISUALS:
        if (!SetupMenuVisuals(menuData)) {
            return FALSE;
        }

        StartScreenFade(FADE_MAIN_ONLY, FADE_TYPE_BRIGHTNESS_IN, FADE_TYPE_BRIGHTNESS_IN, COLOR_BLACK, 6, 1, menuData->heapID);
        break;

    case STATE_WAIT_FOR_FADE_IN:
#ifdef SDK_PORT
        if (menuData->wideMode) {
            WideDrainPendingTouch();
        }
#endif
        if (!IsScreenFadeDone()) {
            return FALSE;
        }
        break;

    case STATE_HANDLE_INPUT:
#ifdef SDK_PORT
        if (menuData->wideMode) {
            if (WideProcessMainInput(menuData)) {
                if (ChangesWereMade(menuData) == TRUE) {
                    menuData->state = STATE_CONFIRM_NEW_SETTINGS;
                } else {
                    Sound_PlayEffect(SE_CONFIRM_sseq_3);
                    menuData->saveSelections = 2;
                    menuData->state = STATE_START_VISUAL_TEARDOWN;
                }
            }
            return FALSE;
        }
#endif
        if ((JOY_NEW(PAD_BUTTON_A) && menuData->cursor == ENTRY_CLOSE) || JOY_NEW(PAD_BUTTON_B)) {
            if (ChangesWereMade(menuData) == TRUE) {
                menuData->state = STATE_CONFIRM_NEW_SETTINGS;
            } else {
                Sound_PlayEffect(SE_CONFIRM_sseq_3);
                menuData->saveSelections = 2;
                menuData->state = STATE_START_VISUAL_TEARDOWN;
            }

            return FALSE;
        }

        ProcessMainInput(menuData);
        return FALSE;

    case STATE_CONFIRM_NEW_SETTINGS:
        RenderControlFlags_SetCanABSpeedUpPrint(TRUE);
        PrintBankEntryAsDescription(menuData, OptionsMenu_Text_ConfirmDialog, FALSE);
        break;

    case STATE_WAIT_CONFIRM_NEW_SETTINGS:
        if (IsTextPrinterDone(menuData)) {
            RenderControlFlags_SetCanABSpeedUpPrint(FALSE);
            DrawConfirmationPrompt(menuData);
            menuData->state = STATE_HANDLE_YES_NO_INPUT;
        }

        return FALSE;

    case STATE_HANDLE_YES_NO_INPUT:
        choiceYesNo = ProcessConfirmationInput(menuData);

        if (choiceYesNo != MENU_NOTHING_CHOSEN) {
            if (choiceYesNo == 0) {
                Sound_StopEffect(SE_CONFIRM_sseq_3, 0);
                Sound_PlayEffect(SEQ_SE_DP_SAVE_sseq);
                menuData->saveSelections = 1;
            } else {
                menuData->saveSelections = 2;
            }

            menuData->state = STATE_START_VISUAL_TEARDOWN;
        }

        return FALSE;

    case STATE_START_VISUAL_TEARDOWN:
        if (Text_IsPrinterActive(menuData->textPrinter)) {
            Text_RemovePrinter(menuData->textPrinter);
        }

        StartScreenFade(FADE_MAIN_ONLY, FADE_TYPE_BRIGHTNESS_OUT, FADE_TYPE_BRIGHTNESS_OUT, COLOR_BLACK, 6, 1, menuData->heapID);
        break;

    case STATE_WAIT_FOR_FADE_OUT:
        if (!IsScreenFadeDone()) {
            return FALSE;
        }
        break;

    case STATE_TEARDOWN:
        if (!TeardownMenuData(menuData)) {
            return FALSE;
        }

        return TRUE;
    }

    menuData->state++;
    return FALSE;
}

static void SetVRAMBanks()
{
    GXBanks banks = {
        GX_VRAM_BG_128_A,
        GX_VRAM_BGEXTPLTT_NONE,
        GX_VRAM_SUB_BG_128_C,
        GX_VRAM_SUB_BGEXTPLTT_NONE,
        GX_VRAM_OBJ_16_G,
        GX_VRAM_OBJEXTPLTT_NONE,
        GX_VRAM_SUB_OBJ_16_I,
        GX_VRAM_SUB_OBJEXTPLTT_NONE,
        GX_VRAM_TEX_NONE,
        GX_VRAM_TEXPLTT_NONE,
    };

    GXLayers_SetBanks(&banks);
}

static void OptionsMenuVBlank(void *data)
{
    OptionsMenuData *menuData = data;

    if (menuData->redrawMessageBox) {
        u16 msgBoxBaseTile = MESSAGE_BOX_BASE_TILE;
#ifdef SDK_PORT
        if (menuData->wideMode) {
            msgBoxBaseTile = WIDE_MESSAGE_BOX_BASE_TILE;
        }
#endif
        LoadMessageBoxGraphics(menuData->bgConfig,
            BG_LAYER_MAIN_1,
            msgBoxBaseTile,
            15,
            menuData->entries.messageBoxStyle.selected,
            menuData->heapID);
        menuData->redrawMessageBox = FALSE;
    }

    SpriteSystem_TransferOam();
    NNS_GfdDoVramTransfer();
    Bg_RunScheduledUpdates(menuData->bgConfig);
    OS_SetIrqCheckFlag(OS_IE_V_BLANK);
}

static int SetupMenuVisuals(OptionsMenuData *menuData)
{
    switch (menuData->subState) {
    case 0:
        SetVBlankCallback(NULL, NULL);
        DisableHBlank();
        GXLayers_DisableEngineALayers();
        GXLayers_DisableEngineBLayers();

        GX_SetVisiblePlane(0);
        GXS_SetVisiblePlane(0);

        SetVRAMBanks();
        ResetVisibleHardwareWindows(DS_SCREEN_MAIN);
        ResetVisibleHardwareWindows(DS_SCREEN_SUB);
        SetupBgs(menuData);
        break;

    case 1:
        LoadBgTiles(menuData);
        menuData->msgLoader = MessageLoader_Init(MSG_LOADER_LOAD_ON_DEMAND,
            NARC_INDEX_MSGDATA__PL_MSG,
            TEXT_BANK_OPTIONS_MENU,
            menuData->heapID);
        LoadAllEntryChoices(menuData);
        break;

    case 2:
        SetupWindows(menuData);
        PrintTitleAndEntries(menuData);
        VramTransfer_New(32, menuData->heapID);
        GXLayers_EngineAToggleLayers(GX_PLANEMASK_OBJ, TRUE);
        NetworkIcon_InitIfConnected();
        SetVBlankCallback(OptionsMenuVBlank, menuData);
        menuData->subState = 0;
        return TRUE;
    }

    menuData->subState++;
    return FALSE;
}

static int TeardownMenuData(OptionsMenuData *menuData)
{
    int v0 = 0, v1 = 0;

    switch (menuData->subState) {
    case 0:
        VramTransfer_Free();
        TeardownWindows(menuData);

        for (v0 = 0; v0 < MAX_ENTRIES; v0++) {
            for (v1 = 0; v1 < menuData->entries.asArray[v0].numChoices; v1++) {
                String_Free(menuData->entries.asArray[v0].choices[v1]);
            }
        }

        MessageLoader_Free(menuData->msgLoader);
        TeardownTilemaps(menuData);
        TeardownBgs(menuData);
        break;

    case 1:
        SetVBlankCallback(NULL, NULL);
        DisableHBlank();
        GXLayers_DisableEngineALayers();
        GXLayers_DisableEngineBLayers();

        GX_SetVisiblePlane(0);
        GXS_SetVisiblePlane(0);
        menuData->subState = 0;
        return TRUE;
    }

    menuData->subState++;
    return FALSE;
}

static void SetupBgs(OptionsMenuData *menuData)
{
    menuData->bgConfig = BgConfig_New(menuData->heapID);

    GraphicsModes graphicsModes = {
        GX_DISPMODE_GRAPHICS,
        GX_BGMODE_0,
        GX_BGMODE_0,
        GX_BG0_AS_2D
    };

    SetAllGraphicsModes(&graphicsModes);

    BgTemplate bgTemplates[NUM_BG_TEMPLATES] = {
        {
            .x = 0,
            .y = 0,
            .bufferSize = 0x800,
            .baseTile = 0,
            .screenSize = BG_SCREEN_SIZE_256x256,
            .colorMode = GX_BG_COLORMODE_16,
            .screenBase = GX_BG_SCRBASE_0xf800,
            .charBase = GX_BG_CHARBASE_0x00000,
            .bgExtPltt = GX_BG_EXTPLTT_01,
            .priority = 1,
            .areaOver = 0,
            .mosaic = FALSE,
        },
        {
            .x = 0,
            .y = 0,
            .bufferSize = 0x800,
            .baseTile = 0,
            .screenSize = BG_SCREEN_SIZE_256x256,
            .colorMode = GX_BG_COLORMODE_16,
            .screenBase = GX_BG_SCRBASE_0xf000,
            .charBase = GX_BG_CHARBASE_0x00000,
            .bgExtPltt = GX_BG_EXTPLTT_01,
            .priority = 2,
            .areaOver = 0,
            .mosaic = FALSE,
        },
        {
            .x = 0,
            .y = 0,
            .bufferSize = 0x800,
            .baseTile = 0,
            .screenSize = BG_SCREEN_SIZE_256x256,
            .colorMode = GX_BG_COLORMODE_16,
            .screenBase = GX_BG_SCRBASE_0xe800,
            .charBase = GX_BG_CHARBASE_0x00000,
            .bgExtPltt = GX_BG_EXTPLTT_01,
            .priority = 3,
            .areaOver = 0,
            .mosaic = FALSE,
        },
        {
            .x = 0,
            .y = 0,
            .bufferSize = 0x800,
            .baseTile = 0,
            .screenSize = BG_SCREEN_SIZE_256x256,
            .colorMode = GX_BG_COLORMODE_16,
            .screenBase = GX_BG_SCRBASE_0xe000,
            .charBase = GX_BG_CHARBASE_0x00000,
            .bgExtPltt = GX_BG_EXTPLTT_01,
            .priority = 0,
            .areaOver = 0,
            .mosaic = FALSE,
        },
        {
            .x = 0,
            .y = 0,
            .bufferSize = 0x800,
            .baseTile = 0,
            .screenSize = BG_SCREEN_SIZE_256x256,
            .colorMode = GX_BG_COLORMODE_16,
            .screenBase = GX_BG_SCRBASE_0xf800,
            .charBase = GX_BG_CHARBASE_0x00000,
            .bgExtPltt = GX_BG_EXTPLTT_01,
            .priority = 0,
            .areaOver = 0,
            .mosaic = FALSE,
        },
    };

#ifdef SDK_PORT
    if (menuData->wideMode) {
        static const int sWideScreenBases[4] = {
            GX_BG_SCRBASE_0xf000,
            GX_BG_SCRBASE_0xe000,
            GX_BG_SCRBASE_0xd000,
            GX_BG_SCRBASE_0xc000,
        };
        for (int i = 0; i < 4; i++) {
            bgTemplates[i].bufferSize = 0x1000;
            bgTemplates[i].screenSize = BG_SCREEN_SIZE_512x256;
            bgTemplates[i].screenBase = sWideScreenBases[i];
        }
    }
#endif

    for (int i = 0; i < NUM_BG_TEMPLATES; i++) {
        static const int sBgLayers[NUM_BG_TEMPLATES] = {
            // Must declared inline to match.
            BG_LAYER_MAIN_0,
            BG_LAYER_MAIN_1,
            BG_LAYER_MAIN_2,
            BG_LAYER_MAIN_3,
            BG_LAYER_SUB_0,
        };

        Bg_InitFromTemplate(menuData->bgConfig, sBgLayers[i], &(bgTemplates[i]), BG_TYPE_STATIC);
        Bg_ClearTilemap(menuData->bgConfig, sBgLayers[i]);
    }

    Bg_ClearTilesRange(BG_LAYER_MAIN_0, 32, 0, menuData->heapID);
    Bg_ClearTilesRange(BG_LAYER_SUB_0, 32, 0, menuData->heapID);
}

static void TeardownBgs(OptionsMenuData *menuData)
{
    Bg_FreeTilemapBuffer(menuData->bgConfig, BG_LAYER_SUB_0);
    Bg_FreeTilemapBuffer(menuData->bgConfig, BG_LAYER_MAIN_3);
    Bg_FreeTilemapBuffer(menuData->bgConfig, BG_LAYER_MAIN_2);
    Bg_FreeTilemapBuffer(menuData->bgConfig, BG_LAYER_MAIN_1);
    Bg_FreeTilemapBuffer(menuData->bgConfig, BG_LAYER_MAIN_0);
    Heap_Free(menuData->bgConfig);
}

static void LoadBgTiles(OptionsMenuData *menuData)
{
    NNSG2dCharacterData *cursorTiles;
    NNSG2dPaletteData *cursorPalette;

    NARC *narc = NARC_ctor(NARC_INDEX_GRAPHIC__CONFIG_GRA, menuData->heapID);

    u32 memberSize = NARC_GetMemberSize(narc, tiles_NCGR);
    void *memberBuffer = Heap_AllocAtEnd(menuData->heapID, memberSize);
    NARC_ReadWholeMember(narc, tiles_NCGR, memberBuffer);
    NNS_G2dGetUnpackedCharacterData(memberBuffer, &cursorTiles);
    Bg_LoadTiles(menuData->bgConfig, BG_LAYER_MAIN_0, cursorTiles->pRawData, cursorTiles->szByte, 0);
    Bg_LoadTiles(menuData->bgConfig, BG_LAYER_SUB_0, cursorTiles->pRawData, cursorTiles->szByte, 0);
    Heap_Free(memberBuffer);

    memberSize = NARC_GetMemberSize(narc, tiles_NCLR);
    memberBuffer = Heap_AllocAtEnd(menuData->heapID, memberSize);
    NARC_ReadWholeMember(narc, tiles_NCLR, memberBuffer);
    NNS_G2dGetUnpackedPaletteData(memberBuffer, &cursorPalette);
    Bg_LoadPalette(BG_LAYER_MAIN_0, cursorPalette->pRawData, PALETTE_SIZE_BYTES, 0);
    Bg_LoadPalette(BG_LAYER_SUB_0, cursorPalette->pRawData, PALETTE_SIZE_BYTES, 0);
    Heap_Free(memberBuffer);

    memberSize = NARC_GetMemberSize(narc, tilemap_bin);
    menuData->nscrBuffer = Heap_Alloc(menuData->heapID, memberSize);
    NARC_ReadWholeMember(narc, tilemap_bin, menuData->nscrBuffer);
    NNS_G2dGetUnpackedScreenData(menuData->nscrBuffer, &(menuData->tilemapData));

    NARC_dtor(narc);

    Bg_FillTilemapRect(menuData->bgConfig,
        BG_LAYER_SUB_0,
        1,
        0,
        0,
        32,
        32,
        TILEMAP_FILL_VAL_INCLUDES_PALETTE);

#ifdef SDK_PORT
    if (menuData->wideMode) {
        Bg_FillTilemapRect(menuData->bgConfig,
            BG_LAYER_MAIN_2,
            1,
            0,
            0,
            64,
            32,
            TILEMAP_FILL_VAL_INCLUDES_PALETTE);

        // Extend the authentic config_gra row cursor highlight bar across cols 1..41
        Bg_FillTilemapRect(menuData->bgConfig, BG_LAYER_MAIN_0, 0x0003, 1, 0, 1, 1, TILEMAP_FILL_VAL_INCLUDES_PALETTE);
        Bg_FillTilemapRect(menuData->bgConfig, BG_LAYER_MAIN_0, 0x0004, 2, 0, WIDE_ENTRIES_WIDTH - 2, 1, TILEMAP_FILL_VAL_INCLUDES_PALETTE);
        Bg_FillTilemapRect(menuData->bgConfig, BG_LAYER_MAIN_0, 0x0403, WIDE_ENTRIES_WIDTH, 0, 1, 1, TILEMAP_FILL_VAL_INCLUDES_PALETTE);
        Bg_FillTilemapRect(menuData->bgConfig, BG_LAYER_MAIN_0, 0x0803, 1, 1, 1, 1, TILEMAP_FILL_VAL_INCLUDES_PALETTE);
        Bg_FillTilemapRect(menuData->bgConfig, BG_LAYER_MAIN_0, 0x0804, 2, 1, WIDE_ENTRIES_WIDTH - 2, 1, TILEMAP_FILL_VAL_INCLUDES_PALETTE);
        Bg_FillTilemapRect(menuData->bgConfig, BG_LAYER_MAIN_0, 0x0C03, WIDE_ENTRIES_WIDTH, 1, 1, 1, TILEMAP_FILL_VAL_INCLUDES_PALETTE);
    } else
#endif
    {
        Bg_FillTilemapRect(menuData->bgConfig,
            BG_LAYER_MAIN_2,
            1,
            0,
            0,
            32,
            32,
            TILEMAP_FILL_VAL_INCLUDES_PALETTE);

        Bg_CopyRectToTilemapRect(menuData->bgConfig,
            BG_LAYER_MAIN_0,
            0,
            0,
            32,
            2,
            menuData->tilemapData->rawData,
            0,
            0,
            menuData->tilemapData->screenWidth / 8,
            menuData->tilemapData->screenHeight / 8);
    }

    Bg_SetOffset(menuData->bgConfig, BG_LAYER_MAIN_0, BG_OFFSET_UPDATE_SET_Y, -FIRST_ENTRY_OFFSET);
    Bg_ScheduleTilemapTransfer(menuData->bgConfig, BG_LAYER_MAIN_2);
    Bg_ScheduleTilemapTransfer(menuData->bgConfig, BG_LAYER_MAIN_0);
    Bg_ScheduleTilemapTransfer(menuData->bgConfig, BG_LAYER_SUB_0);
}

static void TeardownTilemaps(OptionsMenuData *menuData)
{
    Heap_Free(menuData->nscrBuffer);
}

static void SetupWindows(OptionsMenuData *menuData)
{
    u8 titleW = MENU_TITLE_WIDTH;
    u16 titleBase = MENU_TITLE_BASE_TILE;
    u8 entriesW = ENTRIES_WIDTH;
    u16 entriesBase = ENTRIES_BASE_TILE;
    u8 descW = DESCRIPTION_WIDTH;
    u16 descBase = DESCRIPTION_BASE_TILE;
    u16 stdBase = STANDARD_WINDOW_BASE_TILE;
    u16 msgBase = MESSAGE_BOX_BASE_TILE;

#ifdef SDK_PORT
    if (menuData->wideMode) {
        titleW = WIDE_MENU_TITLE_WIDTH;
        titleBase = WIDE_MENU_TITLE_BASE_TILE;
        entriesW = WIDE_ENTRIES_WIDTH;
        entriesBase = WIDE_ENTRIES_BASE_TILE;
        descW = WIDE_DESCRIPTION_WIDTH;
        descBase = WIDE_DESCRIPTION_BASE_TILE;
        stdBase = WIDE_STANDARD_WINDOW_BASE_TILE;
        msgBase = WIDE_MESSAGE_BOX_BASE_TILE;
    }
#endif

    Window_Add(menuData->bgConfig,
        &menuData->windows.title,
        BG_LAYER_MAIN_1,
        1,
        0,
        titleW,
        MENU_TITLE_HEIGHT,
        13,
        titleBase);
    Window_Add(menuData->bgConfig,
        &menuData->windows.entries,
        BG_LAYER_MAIN_1,
        1,
        3,
        entriesW,
        ENTRIES_HEIGHT,
        13,
        entriesBase);
    Window_Add(menuData->bgConfig,
        &menuData->windows.description,
        BG_LAYER_MAIN_1,
        2,
        19,
        descW,
        DESCRIPTION_HEIGHT,
        12,
        descBase);
    LoadStandardWindowGraphics(menuData->bgConfig,
        BG_LAYER_MAIN_1,
        stdBase,
        14,
        STANDARD_WINDOW_SYSTEM,
        menuData->heapID);
    LoadMessageBoxGraphics(menuData->bgConfig,
        BG_LAYER_MAIN_1,
        msgBase,
        15,
        menuData->options.messageBoxStyle,
        menuData->heapID);

    Font_LoadTextPalette(PAL_LOAD_MAIN_BG, PLTT_OFFSET(13), menuData->heapID);
    Font_LoadTextPalette(PAL_LOAD_SUB_BG, PLTT_OFFSET(13), menuData->heapID);
    Font_LoadScreenIndicatorsPalette(PAL_LOAD_MAIN_BG, PLTT_OFFSET(12), menuData->heapID);
    Font_LoadScreenIndicatorsPalette(PAL_LOAD_SUB_BG, PLTT_OFFSET(12), menuData->heapID);

    Window_FillTilemap(&menuData->windows.title, PIXEL_FILL(0));
    Window_FillTilemap(&menuData->windows.entries, PIXEL_FILL(15));
    Window_FillTilemap(&menuData->windows.description, PIXEL_FILL(15));
    Window_ClearTilemap(&menuData->windows.description);
    Window_ClearTilemap(&menuData->windows.entries);
    Window_ClearTilemap(&menuData->windows.title);

    Window_DrawStandardFrame(&menuData->windows.entries, TRUE, stdBase, 14);
    Window_DrawMessageBoxWithScrollCursor(&menuData->windows.description, TRUE, msgBase, 15);
}

static void TeardownWindows(OptionsMenuData *menuData)
{
    Window_EraseStandardFrame(&menuData->windows.entries, FALSE);
    Window_EraseMessageBox(&menuData->windows.description, FALSE);

    for (u16 i = 0; i < 3; i++) {
        Window_ClearAndCopyToVRAM(&menuData->windows.asArray[i]);
        Window_FillTilemap(&menuData->windows.asArray[i], 0);
        Window_ClearTilemap(&menuData->windows.asArray[i]);
        Window_Remove(&menuData->windows.asArray[i]);
    }
}

static const u8 sEntryLabels[MAX_ENTRIES] = {
    OptionsMenu_Text_TextSpeedLabel,
    OptionsMenu_Text_SoundModeLabel,
    OptionsMenu_Text_BattleSceneLabel,
    OptionsMenu_Text_BattleStyleLabel,
    OptionsMenu_Text_ButtonModeLabel,
    OptionsMenu_Text_MessageBoxStyleLabel,
    OptionsMenu_Text_CloseLabel,
};

static void PrintTitleAndEntries(OptionsMenuData *menuData)
{
#ifdef SDK_PORT
    if (menuData->wideMode) {
        WideDrawTitleAndTabs(menuData);
        WideDrawCurrentTabEntries(menuData);
        WidePrintCurrentRowDescription(menuData, TRUE);
        return;
    }
#endif

    u16 i; // Must forward-declare to match
    TextColor transparentBg = TEXT_COLOR(1, 2, 0);
    TextColor whiteBg = TEXT_COLOR(1, 2, 15);

    String *string = String_Init(256, menuData->heapID);
    MessageLoader_GetString(menuData->msgLoader, OptionsMenu_Text_Title, string);
    Text_AddPrinterWithParamsAndColor(&menuData->windows.title,
        FONT_SYSTEM,
        string,
        2,
        2,
        TEXT_SPEED_INSTANT,
        transparentBg,
        NULL);

    for (i = 0; i < MAX_ENTRIES; i++) {
        String_Clear(string);
        MessageLoader_GetString(menuData->msgLoader, sEntryLabels[i], string);
        Text_AddPrinterWithParamsAndColor(&menuData->windows.entries,
            FONT_SYSTEM,
            string,
            4,
            16 * i,
            TEXT_SPEED_NO_TRANSFER,
            whiteBg,
            NULL);
    }

    for (i = 0; i < MAX_ENTRIES; i++) {
        PrintEntryChoices(menuData, i);
    }

    PrintEntryDescription(menuData, ENTRY_TEXT_SPEED, TRUE);
    Window_CopyToVRAM(&menuData->windows.title);
    Window_CopyToVRAM(&menuData->windows.entries);
    String_Free(string);
}

static const int sNumChoicesPerEntry[MAX_ENTRIES] = {
    3,
    2,
    2,
    2,
    3,
    20,
    0,
};

static const u8 sFirstChoicePerEntry[MAX_ENTRIES] = {
    OptionsMenu_Text_TextSpeedSlow,
    OptionsMenu_Text_SoundModeStereo,
    OptionsMenu_Text_BattleSceneOn,
    OptionsMenu_Text_BattleStyleShift,
    OptionsMenu_Text_ButtonModeNormal,
    OptionsMenu_Text_MessageBoxStyle_01,
    0,
};

static void LoadAllEntryChoices(OptionsMenuData *menuData)
{
    u16 i, j;
    for (i = 0; i < MAX_ENTRIES; i++) {
        menuData->entries.asArray[i].numChoices = sNumChoicesPerEntry[i];
        for (j = 0; j < sNumChoicesPerEntry[i]; j++) {
            menuData->entries.asArray[i].choices[j] = MessageLoader_GetNewString(menuData->msgLoader, sFirstChoicePerEntry[i] + j);
        }
    }

    menuData->entries.textSpeed.selected = menuData->options.textSpeed;
    menuData->entries.battleScene.selected = menuData->options.battleScene;
    menuData->entries.battleStyle.selected = menuData->options.battleStyle;
    menuData->entries.soundMode.selected = menuData->options.soundMode;
    menuData->entries.buttonMode.selected = menuData->options.buttonMode;
    menuData->entries.messageBoxStyle.selected = menuData->options.messageBoxStyle;
}

static const s8 sEntryXOffsets[] = { 0, 0, 0, 0, 0, 0, 0 };

static void PrintEntryChoices(OptionsMenuData *menuData, u16 entry)
{
    TextColor darkGray, red, color;
    u16 i;
    u8 textSpeed;
    s8 xOffset = 0;

    darkGray = TEXT_COLOR(1, 2, 15);
    red = TEXT_COLOR(3, 4, 15);

    Window_FillRectWithColor(&menuData->windows.entries, PIXEL_FILL(15), CHOICES_X + sEntryXOffsets[entry], entry * SINGLE_ENTRY_HEIGHT, CHOICES_WIDTH, SINGLE_ENTRY_HEIGHT);
    if (entry == ENTRY_MESSAGE_BOX_FRAME) {
        Text_AddPrinterWithParamsAndColor(&menuData->windows.entries,
            FONT_SYSTEM,
            menuData->entries.asArray[entry].choices[menuData->entries.asArray[entry].selected],
            48 + CHOICES_X,
            entry * SINGLE_ENTRY_HEIGHT,
            TEXT_SPEED_NO_TRANSFER,
            red,
            NULL);
        Window_CopyToVRAM(&menuData->windows.entries);
        menuData->redrawMessageBox = TRUE;
        return;
    }

    if (entry == ENTRY_SOUND_MODE) {
        Sound_SetPlaybackMode(menuData->entries.asArray[entry].selected);
    } else if (entry == ENTRY_BUTTON_MODE) {
        Options_SetSystemButtonMode(NULL, menuData->entries.asArray[entry].selected);
    } else if (entry == ENTRY_TEXT_SPEED) {
        Options_SetTextSpeed(menuData->saveOptions, menuData->entries.asArray[entry].selected);
        PrintEntryDescription(menuData, entry, FALSE);
    }

    xOffset = 0;
    for (i = 0; i < menuData->entries.asArray[entry].numChoices; i++) {
        if (i == menuData->entries.asArray[entry].selected) {
            color = red;
        } else {
            color = darkGray;
        }

        if (i == menuData->entries.asArray[entry].numChoices - 1) {
            textSpeed = TEXT_SPEED_NO_TRANSFER;
        } else {
            textSpeed = TEXT_SPEED_NO_TRANSFER;
        }

        if (entry == ENTRY_BUTTON_MODE) {
            Text_AddPrinterWithParamsAndColor(&menuData->windows.entries,
                FONT_SYSTEM,
                menuData->entries.asArray[entry].choices[i],
                xOffset + CHOICES_X,
                entry * SINGLE_ENTRY_HEIGHT,
                textSpeed,
                color,
                NULL);
            xOffset += Font_CalcStringWidth(FONT_SYSTEM, menuData->entries.asArray[entry].choices[i], 0) + 12;
        } else {
            Text_AddPrinterWithParamsAndColor(&menuData->windows.entries,
                FONT_SYSTEM,
                menuData->entries.asArray[entry].choices[i],
                i * 48 + CHOICES_X + sEntryXOffsets[entry],
                entry * SINGLE_ENTRY_HEIGHT,
                textSpeed,
                color,
                NULL);
        }
    }

    Window_CopyToVRAM(&menuData->windows.asArray[1]);
}

static void PrintBankEntryAsDescription(OptionsMenuData *menuData, u16 entry, BOOL scheduleVRAMCopy)
{
    // Kill any active printer
    if (IsTextPrinterDone(menuData) == FALSE) {
        Text_RemovePrinter(menuData->textPrinter);
    }

    u8 renderDelay = Options_TextFrameDelay(menuData->saveOptions);

    Window_FillTilemap(&menuData->windows.description, 15);

    TextColor color = TEXT_COLOR(1, 2, 15);
    String *string = String_Init(256, menuData->heapID);
    MessageLoader_GetString(menuData->msgLoader, entry, string);

    if (scheduleVRAMCopy == FALSE) {
        menuData->textPrinter = Text_AddPrinterWithParamsAndColor(&menuData->windows.description,
            FONT_MESSAGE,
            string,
            4,
            0,
            renderDelay,
            color,
            NULL);
    } else {
        Text_AddPrinterWithParamsAndColor(&menuData->windows.description,
            FONT_MESSAGE,
            string,
            4,
            0,
            TEXT_SPEED_NO_TRANSFER,
            color,
            NULL);
        Window_ScheduleCopyToVRAM(&menuData->windows.description);
    }

    String_Free(string);
}

static BOOL IsTextPrinterDone(const OptionsMenuData *menuData)
{
    return Text_IsPrinterActive(menuData->textPrinter) == FALSE;
}

static void ProcessMainInput(OptionsMenuData *menuData)
{
    OptionsMenuEntry *entry = &menuData->entries.asArray[menuData->cursor];

    if (menuData->cursor != ENTRY_CLOSE) {
        if (JOY_NEW(PAD_KEY_RIGHT)) {
            entry->selected = (entry->selected + 1) % entry->numChoices;
            PrintEntryChoices(menuData, menuData->cursor);
            Sound_PlayEffect(SE_CONFIRM_sseq_3);
        } else if (JOY_NEW(PAD_KEY_LEFT)) {
            entry->selected = (entry->selected + entry->numChoices - 1) % entry->numChoices;
            PrintEntryChoices(menuData, menuData->cursor);
            Sound_PlayEffect(SE_CONFIRM_sseq_3);
        }
    }

    if (JOY_NEW(PAD_KEY_UP)) {
        menuData->cursor = (menuData->cursor + 7 - 1) % 7;
        Bg_ScheduleScroll(menuData->bgConfig,
            BG_LAYER_MAIN_0,
            BG_OFFSET_UPDATE_SET_Y,
            -(menuData->cursor * SINGLE_ENTRY_HEIGHT + FIRST_ENTRY_OFFSET));

        PrintEntryDescription(menuData, menuData->cursor, TRUE);
        Sound_PlayEffect(SE_CONFIRM_sseq_3);
    } else if (JOY_NEW(PAD_KEY_DOWN)) {
        menuData->cursor = (menuData->cursor + 1) % 7;
        Bg_ScheduleScroll(menuData->bgConfig,
            BG_LAYER_MAIN_0,
            BG_OFFSET_UPDATE_SET_Y,
            -(menuData->cursor * SINGLE_ENTRY_HEIGHT + FIRST_ENTRY_OFFSET));

        PrintEntryDescription(menuData, menuData->cursor, TRUE);
        Sound_PlayEffect(SE_CONFIRM_sseq_3);
    }
}

static BOOL ChangesWereMade(OptionsMenuData *menuData)
{
    BOOL classicChanged = menuData->options.textSpeed != menuData->entries.textSpeed.selected
        || menuData->options.battleScene != menuData->entries.battleScene.selected
        || menuData->options.battleStyle != menuData->entries.battleStyle.selected
        || menuData->options.soundMode != menuData->entries.soundMode.selected
        || menuData->options.buttonMode != menuData->entries.buttonMode.selected
        || menuData->options.messageBoxStyle != menuData->entries.messageBoxStyle.selected;

#ifdef SDK_PORT
    if (menuData->wideMode && WideChangesWereMade(menuData)) {
        return TRUE;
    }
#endif

    return classicChanged;
}

static const WindowTemplate sConfirmationWindowTemplate = {
    .bgLayer = BG_LAYER_MAIN_3,
    .tilemapLeft = 25,
    .tilemapTop = 13,
    .width = 6,
    .height = 4,
    .palette = 13,
    .baseTile = CONFIRMATION_BASE_TILE,
};

#ifdef SDK_PORT
static const WindowTemplate sWideConfirmationWindowTemplate = {
    .bgLayer = BG_LAYER_MAIN_3,
    .tilemapLeft = 34,
    .tilemapTop = 13,
    .width = 6,
    .height = 4,
    .palette = 13,
    .baseTile = WIDE_CONFIRMATION_BASE_TILE,
};
#endif

static void DrawConfirmationPrompt(OptionsMenuData *menuData)
{
#ifdef SDK_PORT
    if (menuData->wideMode) {
        WideDrainPendingTouch();
        menuData->yesNoChoice = Menu_MakeYesNoChoice(menuData->bgConfig,
            &sWideConfirmationWindowTemplate,
            WIDE_STANDARD_WINDOW_BASE_TILE,
            14,
            menuData->heapID);
        return;
    }
#endif
    menuData->yesNoChoice = Menu_MakeYesNoChoice(menuData->bgConfig,
        &sConfirmationWindowTemplate,
        STANDARD_WINDOW_BASE_TILE,
        14,
        menuData->heapID);
}

#ifdef SDK_BUILD_ARM
static u32 ProcessConfirmationInput(OptionsMenuData *menuData)
#else
static u64 ProcessConfirmationInput(OptionsMenuData *menuData)
#endif
{
#ifdef SDK_PORT
    if (menuData->wideMode) {
        int tx = 0;
        int ty = 0;
        if (SIM_Wide_PollMainTouch(&tx, &ty)) {
            int left = (sWideConfirmationWindowTemplate.tilemapLeft - 1) * 8;
            int right = (sWideConfirmationWindowTemplate.tilemapLeft + sWideConfirmationWindowTemplate.width + 1) * 8;
            int top = (sWideConfirmationWindowTemplate.tilemapTop - 1) * 8;
            int bottom = (sWideConfirmationWindowTemplate.tilemapTop + sWideConfirmationWindowTemplate.height + 1) * 8;
            int splitY = (sWideConfirmationWindowTemplate.tilemapTop + 2) * 8;

            if (tx >= left && tx < right && ty >= top && ty < bottom) {
                if (ty < splitY) {
                    Menu_DestroyForExit(menuData->yesNoChoice, menuData->heapID);
                    return 0;
                } else {
                    Sound_PlayEffect(SE_CONFIRM_sseq_3);
                    Menu_DestroyForExit(menuData->yesNoChoice, menuData->heapID);
                    return MENU_CANCEL;
                }
            }
        }
    }
#endif
    return Menu_ProcessInputAndHandleExit(menuData->yesNoChoice, menuData->heapID);
}

static const u8 sEntryDescriptions[MAX_ENTRIES] = {
    OptionsMenu_Text_TextSpeedDescription,
    OptionsMenu_Text_SoundModeDescription,
    OptionsMenu_Text_BattleSceneDescription,
    OptionsMenu_Text_BattleStyleDescription,
    OptionsMenu_Text_ButtonModeDescription,
    OptionsMenu_Text_MessageBoxStyleDescription,
    OptionsMenu_Text_CloseDescription,
};

static void PrintEntryDescription(OptionsMenuData *menuData, u16 entry, BOOL scheduleVRAMCopy)
{
    PrintBankEntryAsDescription(menuData, sEntryDescriptions[entry], scheduleVRAMCopy);
}

#ifdef SDK_PORT

typedef struct WideTabDef {
    const char *label;
    u16 x;
    u16 width;
} WideTabDef;

static const WideTabDef sWideTabs[WIDE_TAB_COUNT] = {
    { "GAME",    60,  48 },
    { "PLAY",    112, 48 },
    { "DISPLAY", 164, 64 },
    { "FX",      232, 36 },
};

static const u8 sWideTab0Rows[] = {
    WIDE_ROW_TEXT_SPEED,
    WIDE_ROW_BATTLE_SCENE,
    WIDE_ROW_BATTLE_STYLE,
    WIDE_ROW_SOUND_MODE,
    WIDE_ROW_BUTTON_MODE,
    WIDE_ROW_FRAME,
    WIDE_ROW_CLOSE,
};

static const u8 sWideTab1Rows[] = {
    WIDE_ROW_60FPS,
    WIDE_ROW_BATTLE_SPEED,
    WIDE_ROW_MEGA_CUTSCENE,
    WIDE_ROW_BATTLE_HUD,
    WIDE_ROW_FOLLOWER,
    WIDE_ROW_PHENOMENA,
    WIDE_ROW_CLOSE,
};

static const u8 sWideTab2RowsMac[] = {
    WIDE_ROW_VOLUME,
    WIDE_ROW_3D_RES,
    WIDE_ROW_2D_FILTER,
    WIDE_ROW_LAYOUT,
    WIDE_ROW_FULLSCREEN,
    WIDE_ROW_TOUCH_PAD,
    WIDE_ROW_CLOSE,
};

static const u8 sWideTab2RowsIOS[] = {
    WIDE_ROW_VOLUME,
    WIDE_ROW_3D_RES,
    WIDE_ROW_2D_FILTER,
    WIDE_ROW_TOUCH_PAD,
    WIDE_ROW_CLOSE,
};

static const u8 sWideTab3Rows[] = {
    WIDE_ROW_WEATHER_FX,
    WIDE_ROW_LIGHTING,
    WIDE_ROW_ARENA_TINT,
    WIDE_ROW_PARTICLES,
    WIDE_ROW_WATER_REFL,
    WIDE_ROW_CINEMATICS,
    WIDE_ROW_CLOSE,
};

static const u8 sWideVolumeSteps[5] = { 0, 32, 64, 96, 127 };

typedef struct WideOptMeta {
    const char *label;
    const char *description;
    u8 numChoices;
    const char *choices[WIDE_MAX_ROW_CHOICES];
} WideOptMeta;

static const WideOptMeta sWideOptMeta[WIDE_OPT_COUNT] = {
    [WIDE_OPT_60FPS] = {
        "60 FPS",
        "Run the game at a smooth 60 frames\nper second, or classic 30 FPS.",
        2,
        { "ON", "OFF", NULL, NULL, NULL },
    },
    [WIDE_OPT_BATTLE_SPEED] = {
        "BATTLE SPEED",
        "Choose normal, fast-paced, or instant\nbattle animations and HP gauges.",
        3,
        { "NORMAL", "FAST", "INSTANT", NULL, NULL },
    },
    [WIDE_OPT_MEGA_CUTSCENE] = {
        "MEGA CUTSCENE",
        "Play the full Mega Evolution cutscene\nor a shorter quick version.",
        2,
        { "FULL", "SHORT", NULL, NULL, NULL },
    },
    [WIDE_OPT_BATTLE_HUD] = {
        "BATTLE HUD",
        "Choose BDSP-style HD HUD, classic\npixel-art HUD, or touch-screen only.",
        3,
        { "HD", "PIXEL", "OFF", NULL, NULL },
    },
    [WIDE_OPT_FOLLOWER] = {
        "FOLLOWER",
        "Have your lead Pokemon walk behind\nyou in the overworld, or stay in ball.",
        2,
        { "ON", "OFF", NULL, NULL, NULL },
    },
    [WIDE_OPT_PHENOMENA] = {
        "PHENOMENA",
        "Enable BW2 rustling grass, dust\nclouds, rippling water, and shadows.",
        2,
        { "ON", "OFF", NULL, NULL, NULL },
    },
    [WIDE_OPT_VOLUME] = {
        "VOLUME",
        "Adjust the master sound volume for\nmusic and sound effects.",
        5,
        { "0%", "25%", "50%", "75%", "100%" },
    },
    [WIDE_OPT_3D_RES] = {
        "3D RES",
        "Set the internal 3D rendering\nresolution multiplier.",
        4,
        { "1x", "2x", "3x", "4x", NULL },
    },
    [WIDE_OPT_2D_FILTER] = {
        "2D FILTER",
        "Choose crisp nearest pixels, sharp\nbilinear, or smooth 2D filtering.",
        3,
        { "NEAREST", "SHARP", "SMOOTH", NULL, NULL },
    },
    [WIDE_OPT_LAYOUT] = {
        "LAYOUT",
        "Choose wide 16:9, vertical, horizontal,\nor large screen layout.",
        4,
        { "WIDE", "VERT", "HORIZ", "LARGE", NULL },
    },
    [WIDE_OPT_FULLSCREEN] = {
        "FULLSCREEN",
        "Toggle between full-screen display\nand a desktop window.",
        2,
        { "ON", "OFF", NULL, NULL, NULL },
    },
    [WIDE_OPT_TOUCH_PAD] = {
        "TOUCH PAD",
        "Show on-screen touch controls auto,\nalways on, or hidden.",
        3,
        { "AUTO", "ON", "OFF", NULL, NULL },
    },
    [WIDE_OPT_WEATHER_FX] = {
        "WEATHER FX",
        "Enable Metal GPU fog, rain, heat, and\nlight shaft weather effects.",
        2,
        { "ON", "OFF", NULL, NULL, NULL },
    },
    [WIDE_OPT_LIGHTING] = {
        "LIGHTING",
        "Enable per-pixel 3D scene lighting\nand battle sprite rim highlights.",
        2,
        { "ON", "OFF", NULL, NULL, NULL },
    },
    [WIDE_OPT_ARENA_TINT] = {
        "ARENA TINT",
        "Tint battle arenas to match overworld\ntime of day and weather.",
        2,
        { "ON", "OFF", NULL, NULL, NULL },
    },
    [WIDE_OPT_PARTICLES] = {
        "PARTICLES",
        "Boost battle particle effects with\nextra GPU sparkle trails.",
        2,
        { "ON", "OFF", NULL, NULL, NULL },
    },
    [WIDE_OPT_WATER_REFL] = {
        "WATER REFL",
        "Enable pixelated water reflections\nand shoreline foam effects.",
        2,
        { "ON", "OFF", NULL, NULL, NULL },
    },
    [WIDE_OPT_CINEMATICS] = {
        "CINEMATICS",
        "Enable or disable scripted camera\nmoves during overworld events.",
        2,
        { "ON", "OFF", NULL, NULL, NULL },
    },
};

static void WideDrainPendingTouch(void)
{
    int tx = 0;
    int ty = 0;
    while (SIM_Wide_PollMainTouch(&tx, &ty)) {
        // discard stray clicks during transitions
    }
}

static charcode_t WideAsciiToCharCode(char c)
{
    if (c >= 'A' && c <= 'Z') {
        return (charcode_t)(CHAR_A + (c - 'A'));
    }
    if (c >= 'a' && c <= 'z') {
        return (charcode_t)(CHAR_a + (c - 'a'));
    }
    if (c >= '0' && c <= '9') {
        return (charcode_t)(CHAR_0 + (c - '0'));
    }

    switch (c) {
    case '\n':
        return CHAR_CR;
    case ' ':
        return CHAR_SPACE;
    case '.':
        return CHAR_PERIOD;
    case ',':
        return CHAR_COMMA;
    case '-':
        return CHAR_MINUS;
    case '/':
        return CHAR_SLASH;
    case ':':
        return CHAR_COLON;
    case '%':
        return CHAR_PERCENT;
    case '=':
        return CHAR_EQUALS;
    case '+':
        return CHAR_PLUS;
    case '&':
        return CHAR_AMPERSAND;
    case '(':
        return CHAR_PAREN_OPEN;
    case ')':
        return CHAR_PAREN_CLOSE;
    case '!':
        return CHAR_EXCLAMATION;
    case '?':
        return CHAR_QUESTION;
    case '\'':
        return CHAR_SINGLE_QUOTE_CLOSE;
    default:
        return CHAR_SPACE;
    }
}

static String *WideNewAsciiString(const char *ascii, enum HeapID heapID)
{
    u32 len = (u32)strlen(ascii);
    String *str = String_Init(len + 1, heapID);

    for (u32 i = 0; i < len; i++) {
        String_AppendChar(str, WideAsciiToCharCode(ascii[i]));
    }

    return str;
}

static const u8 *WideGetTabRows(u8 tab, u16 *outCount)
{
    switch (tab) {
    case WIDE_TAB_GAME:
        *outCount = (u16)NELEMS(sWideTab0Rows);
        return sWideTab0Rows;
    case WIDE_TAB_PLAY:
        *outCount = (u16)NELEMS(sWideTab1Rows);
        return sWideTab1Rows;
    case WIDE_TAB_DISPLAY:
        if (SIM_Platform_IsIOS()) {
            *outCount = (u16)NELEMS(sWideTab2RowsIOS);
            return sWideTab2RowsIOS;
        }
        *outCount = (u16)NELEMS(sWideTab2RowsMac);
        return sWideTab2RowsMac;
    case WIDE_TAB_FX:
    default:
        *outCount = (u16)NELEMS(sWideTab3Rows);
        return sWideTab3Rows;
    }
}

static BOOL WideRowIsClassic(u8 rowId)
{
    return rowId <= WIDE_ROW_FRAME;
}

static enum OptionsMenuEntryID WideRowToClassicEntry(u8 rowId)
{
    switch (rowId) {
    case WIDE_ROW_TEXT_SPEED:
        return ENTRY_TEXT_SPEED;
    case WIDE_ROW_BATTLE_SCENE:
        return ENTRY_BATTLE_SCENE;
    case WIDE_ROW_BATTLE_STYLE:
        return ENTRY_BATTLE_STYLE;
    case WIDE_ROW_SOUND_MODE:
        return ENTRY_SOUND_MODE;
    case WIDE_ROW_BUTTON_MODE:
        return ENTRY_BUTTON_MODE;
    case WIDE_ROW_FRAME:
        return ENTRY_MESSAGE_BOX_FRAME;
    case WIDE_ROW_CLOSE:
    default:
        return ENTRY_CLOSE;
    }
}

static u8 WideVolumeToChoice(u8 volume)
{
    if (volume <= 15) {
        return 0;
    }
    if (volume <= 47) {
        return 1;
    }
    if (volume <= 79) {
        return 2;
    }
    if (volume <= 111) {
        return 3;
    }
    return 4;
}

static u8 WideLayoutToChoice(SIM_config_screen_layout_type layout)
{
    switch (layout) {
    case SIM_CONFIG_SCREEN_LAYOUT_WIDE:
        return 0;
    case SIM_CONFIG_SCREEN_LAYOUT_VERTICAL:
        return 1;
    case SIM_CONFIG_SCREEN_LAYOUT_HORIZONTAL:
        return 2;
    case SIM_CONFIG_SCREEN_LAYOUT_LARGE:
        return 3;
    default:
        return 0;
    }
}

static SIM_config_screen_layout_type WideChoiceToLayout(u8 choice)
{
    switch (choice) {
    case 0:
        return SIM_CONFIG_SCREEN_LAYOUT_WIDE;
    case 1:
        return SIM_CONFIG_SCREEN_LAYOUT_VERTICAL;
    case 2:
        return SIM_CONFIG_SCREEN_LAYOUT_HORIZONTAL;
    case 3:
        return SIM_CONFIG_SCREEN_LAYOUT_LARGE;
    default:
        return SIM_CONFIG_SCREEN_LAYOUT_WIDE;
    }
}

static void WideSnapshotConfig(OptionsMenuData *menuData)
{
    const SIM_Config_prj_type *prj = SIM_Config_prj_GetConfig();
    const SIM_config_type *simCfg = SIM_GetConfigPtr();
    u32 maxScale = SIM_Platform_IsIOS() ? 2 : 4;
    u32 scale;

    menuData->snapPrj = *prj;
    menuData->snapSim = *simCfg;

    menuData->wideInitial[WIDE_OPT_60FPS] = prj->enable60fps ? 0 : 1;
    if (prj->battleInstantAnimations) {
        menuData->wideInitial[WIDE_OPT_BATTLE_SPEED] = 2;
    } else if (prj->battleFastPacing) {
        menuData->wideInitial[WIDE_OPT_BATTLE_SPEED] = 1;
    } else {
        menuData->wideInitial[WIDE_OPT_BATTLE_SPEED] = 0;
    }
    menuData->wideInitial[WIDE_OPT_MEGA_CUTSCENE] = prj->megaCinematicShort ? 1 : 0;
    if (!prj->battleHud) {
        menuData->wideInitial[WIDE_OPT_BATTLE_HUD] = 2;
    } else if (prj->battleHudStyleHd) {
        menuData->wideInitial[WIDE_OPT_BATTLE_HUD] = 0;
    } else {
        menuData->wideInitial[WIDE_OPT_BATTLE_HUD] = 1;
    }
    menuData->wideInitial[WIDE_OPT_FOLLOWER] = prj->followerEnabled ? 0 : 1;
    menuData->wideInitial[WIDE_OPT_PHENOMENA] = prj->phenomenaEnabled ? 0 : 1;
    menuData->wideInitial[WIDE_OPT_CINEMATICS] = prj->overworldCinematics ? 0 : 1;

    menuData->wideInitial[WIDE_OPT_VOLUME] = WideVolumeToChoice(simCfg->masterVolume);

    scale = simCfg->internalResolutionScale;
    if (scale < 1) {
        scale = 1;
    } else if (scale > maxScale) {
        scale = maxScale;
    }
    menuData->wideInitial[WIDE_OPT_3D_RES] = (u8)(scale - 1);

    menuData->wideInitial[WIDE_OPT_2D_FILTER] = (simCfg->upscale2D <= 2) ? simCfg->upscale2D : 0;
    menuData->wideInitial[WIDE_OPT_LAYOUT] = WideLayoutToChoice(simCfg->screenLayout);
    menuData->wideInitial[WIDE_OPT_FULLSCREEN] = simCfg->fullScreen ? 0 : 1;
    menuData->wideInitial[WIDE_OPT_TOUCH_PAD] = (simCfg->touchControls <= 2) ? simCfg->touchControls : 0;

    menuData->wideInitial[WIDE_OPT_WEATHER_FX] = prj->weatherFx ? 0 : 1;
    menuData->wideInitial[WIDE_OPT_LIGHTING] = (prj->sceneLights || prj->spriteRimLight) ? 0 : 1;
    menuData->wideInitial[WIDE_OPT_ARENA_TINT] = prj->arenaContext ? 0 : 1;
    menuData->wideInitial[WIDE_OPT_PARTICLES] = prj->particleBoost ? 0 : 1;
    menuData->wideInitial[WIDE_OPT_WATER_REFL] = prj->waterReflections ? 0 : 1;

    memcpy(menuData->wideSelected, menuData->wideInitial, sizeof(menuData->wideSelected));
}

static BOOL WideChangesWereMade(const OptionsMenuData *menuData)
{
    for (int i = 0; i < WIDE_OPT_COUNT; i++) {
        if (menuData->wideSelected[i] != menuData->wideInitial[i]) {
            return TRUE;
        }
    }
    return FALSE;
}

static u16 WideGetRowNumChoices(u8 rowId)
{
    if (rowId == WIDE_ROW_CLOSE) {
        return 0;
    }
    if (WideRowIsClassic(rowId)) {
        return (u16)sNumChoicesPerEntry[WideRowToClassicEntry(rowId)];
    }
    if (rowId == WIDE_ROW_3D_RES && SIM_Platform_IsIOS()) {
        return 2;
    }
    return sWideOptMeta[rowId - WIDE_ROW_60FPS].numChoices;
}

static u16 WideGetRowSelected(const OptionsMenuData *menuData, u8 rowId)
{
    if (WideRowIsClassic(rowId)) {
        return menuData->entries.asArray[WideRowToClassicEntry(rowId)].selected;
    }
    return menuData->wideSelected[rowId - WIDE_ROW_60FPS];
}

static void WideSetRowSelected(OptionsMenuData *menuData, u8 rowId, u16 val)
{
    if (WideRowIsClassic(rowId)) {
        menuData->entries.asArray[WideRowToClassicEntry(rowId)].selected = val;
    } else {
        menuData->wideSelected[rowId - WIDE_ROW_60FPS] = (u8)val;
    }
}

static void WideApplyLivePreview(OptionsMenuData *menuData, u8 rowId)
{
    SIM_config_type *simCfg = SIM_GetConfigPtr();
    u16 sel = WideGetRowSelected(menuData, rowId);

    switch (rowId) {
    case WIDE_ROW_TEXT_SPEED:
        Options_SetTextSpeed(menuData->saveOptions, sel);
        PrintEntryDescription(menuData, ENTRY_TEXT_SPEED, FALSE);
        break;
    case WIDE_ROW_SOUND_MODE:
        Sound_SetPlaybackMode(sel);
        break;
    case WIDE_ROW_BUTTON_MODE:
        Options_SetSystemButtonMode(NULL, sel);
        break;
    case WIDE_ROW_FRAME:
        menuData->redrawMessageBox = TRUE;
        break;
    case WIDE_ROW_VOLUME:
        simCfg->masterVolume = sWideVolumeSteps[sel < 5 ? sel : 4];
        break;
    case WIDE_ROW_3D_RES:
        simCfg->internalResolutionScale = (u32)(sel + 1);
        SIM_SetInternalResolutionAfterRender((int)(sel + 1));
        break;
    case WIDE_ROW_2D_FILTER:
        simCfg->upscale2D = (u8)sel;
        break;
    case WIDE_ROW_FULLSCREEN:
        simCfg->fullScreen = (sel == 0) ? 1 : 0;
        if (!SIM_Headless_Enabled() && SIM_GetSDLWindow() != NULL) {
            SDL_SetWindowFullscreen(SIM_GetSDLWindow(), simCfg->fullScreen ? true : false);
        }
        break;
    default:
        break;
    }
}

static void WideApplyAndSaveOrRevert(OptionsMenuData *menuData, BOOL *outLayoutChanged, SIM_config_screen_layout_type *outNewLayout)
{
    SIM_Config_prj_type *prj = SIM_Config_prj_GetConfig();
    SIM_config_type *simCfg = SIM_GetConfigPtr();

    *outLayoutChanged = FALSE;
    *outNewLayout = simCfg->screenLayout;

    if (menuData->saveSelections == 1) {
        BOOL prjDirty = FALSE;
        BOOL simDirty = FALSE;

        if (menuData->wideSelected[WIDE_OPT_60FPS] != menuData->wideInitial[WIDE_OPT_60FPS]) {
            prj->enable60fps = (menuData->wideSelected[WIDE_OPT_60FPS] == 0) ? TRUE : FALSE;
            prjDirty = TRUE;
        }
        if (menuData->wideSelected[WIDE_OPT_BATTLE_SPEED] != menuData->wideInitial[WIDE_OPT_BATTLE_SPEED]) {
            u8 spd = menuData->wideSelected[WIDE_OPT_BATTLE_SPEED];
            prj->battleFastPacing = (spd >= 1) ? TRUE : FALSE;
            prj->battleInstantAnimations = (spd >= 2) ? TRUE : FALSE;
            prjDirty = TRUE;
        }
        if (menuData->wideSelected[WIDE_OPT_MEGA_CUTSCENE] != menuData->wideInitial[WIDE_OPT_MEGA_CUTSCENE]) {
            prj->megaCinematicShort = (menuData->wideSelected[WIDE_OPT_MEGA_CUTSCENE] == 1) ? TRUE : FALSE;
            prjDirty = TRUE;
        }
        if (menuData->wideSelected[WIDE_OPT_BATTLE_HUD] != menuData->wideInitial[WIDE_OPT_BATTLE_HUD]) {
            u8 hud = menuData->wideSelected[WIDE_OPT_BATTLE_HUD];
            prj->battleHud = (hud < 2) ? TRUE : FALSE;
            if (hud < 2) {
                prj->battleHudStyleHd = (hud == 0) ? TRUE : FALSE;
            }
            prjDirty = TRUE;
        }
        if (menuData->wideSelected[WIDE_OPT_FOLLOWER] != menuData->wideInitial[WIDE_OPT_FOLLOWER]) {
            prj->followerEnabled = (menuData->wideSelected[WIDE_OPT_FOLLOWER] == 0) ? TRUE : FALSE;
            prjDirty = TRUE;
        }
        if (menuData->wideSelected[WIDE_OPT_PHENOMENA] != menuData->wideInitial[WIDE_OPT_PHENOMENA]) {
            prj->phenomenaEnabled = (menuData->wideSelected[WIDE_OPT_PHENOMENA] == 0) ? TRUE : FALSE;
            prjDirty = TRUE;
        }
        if (menuData->wideSelected[WIDE_OPT_CINEMATICS] != menuData->wideInitial[WIDE_OPT_CINEMATICS]) {
            prj->overworldCinematics = (menuData->wideSelected[WIDE_OPT_CINEMATICS] == 0) ? TRUE : FALSE;
            prjDirty = TRUE;
        }
        if (menuData->wideSelected[WIDE_OPT_WEATHER_FX] != menuData->wideInitial[WIDE_OPT_WEATHER_FX]) {
            prj->weatherFx = (menuData->wideSelected[WIDE_OPT_WEATHER_FX] == 0) ? TRUE : FALSE;
            prjDirty = TRUE;
        }
        if (menuData->wideSelected[WIDE_OPT_LIGHTING] != menuData->wideInitial[WIDE_OPT_LIGHTING]) {
            BOOL on = (menuData->wideSelected[WIDE_OPT_LIGHTING] == 0) ? TRUE : FALSE;
            prj->sceneLights = on;
            prj->spriteRimLight = on;
            prjDirty = TRUE;
        }
        if (menuData->wideSelected[WIDE_OPT_ARENA_TINT] != menuData->wideInitial[WIDE_OPT_ARENA_TINT]) {
            prj->arenaContext = (menuData->wideSelected[WIDE_OPT_ARENA_TINT] == 0) ? TRUE : FALSE;
            prjDirty = TRUE;
        }
        if (menuData->wideSelected[WIDE_OPT_PARTICLES] != menuData->wideInitial[WIDE_OPT_PARTICLES]) {
            prj->particleBoost = (menuData->wideSelected[WIDE_OPT_PARTICLES] == 0) ? TRUE : FALSE;
            prjDirty = TRUE;
        }
        if (menuData->wideSelected[WIDE_OPT_WATER_REFL] != menuData->wideInitial[WIDE_OPT_WATER_REFL]) {
            prj->waterReflections = (menuData->wideSelected[WIDE_OPT_WATER_REFL] == 0) ? TRUE : FALSE;
            prjDirty = TRUE;
        }

        if (menuData->wideSelected[WIDE_OPT_VOLUME] != menuData->wideInitial[WIDE_OPT_VOLUME]) {
            u8 idx = menuData->wideSelected[WIDE_OPT_VOLUME];
            simCfg->masterVolume = sWideVolumeSteps[idx < 5 ? idx : 4];
            simDirty = TRUE;
        }
        if (menuData->wideSelected[WIDE_OPT_3D_RES] != menuData->wideInitial[WIDE_OPT_3D_RES]) {
            u32 scale = (u32)(menuData->wideSelected[WIDE_OPT_3D_RES] + 1);
            simCfg->internalResolutionScale = scale;
            SIM_SetInternalResolutionAfterRender((int)scale);
            simDirty = TRUE;
        }
        if (menuData->wideSelected[WIDE_OPT_2D_FILTER] != menuData->wideInitial[WIDE_OPT_2D_FILTER]) {
            simCfg->upscale2D = menuData->wideSelected[WIDE_OPT_2D_FILTER];
            simDirty = TRUE;
        }
        if (!SIM_Platform_IsIOS() && menuData->wideSelected[WIDE_OPT_LAYOUT] != menuData->wideInitial[WIDE_OPT_LAYOUT]) {
            simCfg->screenLayout = WideChoiceToLayout(menuData->wideSelected[WIDE_OPT_LAYOUT]);
            *outLayoutChanged = TRUE;
            *outNewLayout = simCfg->screenLayout;
            simDirty = TRUE;
        }
        if (!SIM_Platform_IsIOS() && menuData->wideSelected[WIDE_OPT_FULLSCREEN] != menuData->wideInitial[WIDE_OPT_FULLSCREEN]) {
            simCfg->fullScreen = (menuData->wideSelected[WIDE_OPT_FULLSCREEN] == 0) ? 1 : 0;
            if (!SIM_Headless_Enabled() && SIM_GetSDLWindow() != NULL) {
                SDL_SetWindowFullscreen(SIM_GetSDLWindow(), simCfg->fullScreen ? true : false);
            }
            simDirty = TRUE;
        }
        if (menuData->wideSelected[WIDE_OPT_TOUCH_PAD] != menuData->wideInitial[WIDE_OPT_TOUCH_PAD]) {
            simCfg->touchControls = menuData->wideSelected[WIDE_OPT_TOUCH_PAD];
            simDirty = TRUE;
        }

        if (prjDirty) {
            SIM_Config_prj_SaveConfigFile(prj);
        }
        if (simDirty) {
            SIM_Config_SaveConfigFile(simCfg);
        }
    } else {
        // Cancel: revert any live-previewed changes back to the initial snapshot
        *prj = menuData->snapPrj;

        if (simCfg->masterVolume != menuData->snapSim.masterVolume) {
            simCfg->masterVolume = menuData->snapSim.masterVolume;
        }
        if (simCfg->internalResolutionScale != menuData->snapSim.internalResolutionScale) {
            simCfg->internalResolutionScale = menuData->snapSim.internalResolutionScale;
            SIM_SetInternalResolutionAfterRender((int)simCfg->internalResolutionScale);
        }
        if (simCfg->upscale2D != menuData->snapSim.upscale2D) {
            simCfg->upscale2D = menuData->snapSim.upscale2D;
        }
        if (simCfg->fullScreen != menuData->snapSim.fullScreen) {
            simCfg->fullScreen = menuData->snapSim.fullScreen;
            if (!SIM_Headless_Enabled() && SIM_GetSDLWindow() != NULL) {
                SDL_SetWindowFullscreen(SIM_GetSDLWindow(), simCfg->fullScreen ? true : false);
            }
        }
        simCfg->screenLayout = menuData->snapSim.screenLayout;
        simCfg->touchControls = menuData->snapSim.touchControls;
    }
}

static void WideDrawTitleAndTabs(OptionsMenuData *menuData)
{
    TextColor inactiveCol = TEXT_COLOR(1, 2, 0);
    TextColor activeCol = TEXT_COLOR(3, 4, 15);
    String *titleStr = String_Init(64, menuData->heapID);
    String *hintStr;

    Window_FillTilemap(&menuData->windows.title, PIXEL_FILL(0));

    MessageLoader_GetString(menuData->msgLoader, OptionsMenu_Text_Title, titleStr);
    Text_AddPrinterWithParamsAndColor(&menuData->windows.title,
        FONT_SYSTEM,
        titleStr,
        2,
        2,
        TEXT_SPEED_NO_TRANSFER,
        inactiveCol,
        NULL);
    String_Free(titleStr);

    for (u8 t = 0; t < WIDE_TAB_COUNT; t++) {
        u16 tx = sWideTabs[t].x;
        u16 tw = sWideTabs[t].width;
        String *tabStr = WideNewAsciiString(sWideTabs[t].label, menuData->heapID);
        u32 strW = Font_CalcStringWidth(FONT_SYSTEM, tabStr, 0);
        u32 textX = tx + (tw > strW ? (tw - strW) / 2 : 0);

        if (t == menuData->activeTab) {
            Window_FillRectWithColor(&menuData->windows.title, PIXEL_FILL(15), tx + 1, 1, tw - 2, 13);
            Text_AddPrinterWithParamsAndColor(&menuData->windows.title,
                FONT_SYSTEM,
                tabStr,
                textX,
                1,
                TEXT_SPEED_NO_TRANSFER,
                activeCol,
                NULL);
            Window_FillRectWithColor(&menuData->windows.title, PIXEL_FILL(1), tx + 1, 0, tw - 2, 1);
            Window_FillRectWithColor(&menuData->windows.title, PIXEL_FILL(1), tx, 1, 1, 15);
            Window_FillRectWithColor(&menuData->windows.title, PIXEL_FILL(1), tx + tw - 1, 1, 1, 15);
            Window_FillRectWithColor(&menuData->windows.title, PIXEL_FILL(3), tx + 1, 14, tw - 2, 2);
        } else {
            Text_AddPrinterWithParamsAndColor(&menuData->windows.title,
                FONT_SYSTEM,
                tabStr,
                textX,
                1,
                TEXT_SPEED_NO_TRANSFER,
                inactiveCol,
                NULL);
            Window_FillRectWithColor(&menuData->windows.title, PIXEL_FILL(2), tx + 2, 15, tw - 4, 1);
        }

        String_Free(tabStr);
    }

    hintStr = WideNewAsciiString("L/R", menuData->heapID);
    Text_AddPrinterWithParamsAndColor(&menuData->windows.title,
        FONT_SYSTEM,
        hintStr,
        294,
        2,
        TEXT_SPEED_NO_TRANSFER,
        inactiveCol,
        NULL);
    String_Free(hintStr);

    Window_CopyToVRAM(&menuData->windows.title);
}

static void WidePrintRowChoices(OptionsMenuData *menuData, u16 rowIdx, BOOL applyLive)
{
    u16 rowCount = 0;
    const u8 *rows = WideGetTabRows(menuData->activeTab, &rowCount);
    u8 rowId;
    TextColor darkGray = TEXT_COLOR(1, 2, 15);
    TextColor red = TEXT_COLOR(3, 4, 15);

    if (rowIdx >= rowCount) {
        return;
    }

    rowId = rows[rowIdx];

    Window_FillRectWithColor(&menuData->windows.entries,
        PIXEL_FILL(15),
        WIDE_CHOICES_X,
        rowIdx * SINGLE_ENTRY_HEIGHT,
        WIDE_CHOICES_WIDTH,
        SINGLE_ENTRY_HEIGHT);

    if (rowId == WIDE_ROW_CLOSE) {
        return;
    }

    if (applyLive) {
        WideApplyLivePreview(menuData, rowId);
    }

    if (rowId == WIDE_ROW_FRAME) {
        String *valStr = menuData->entries.messageBoxStyle.choices[menuData->entries.messageBoxStyle.selected];
        u32 strW = Font_CalcStringWidth(FONT_SYSTEM, valStr, 0);
        u32 valX = 132 + (64 > strW ? (64 - strW) / 2 : 0);
        String *leftArrow = String_Init(2, menuData->heapID);
        String *rightArrow = String_Init(2, menuData->heapID);

        String_AppendChar(leftArrow, CHAR_ARROW_LEFT);
        String_AppendChar(rightArrow, CHAR_ARROW_RIGHT);

        Text_AddPrinterWithParamsAndColor(&menuData->windows.entries,
            FONT_SYSTEM,
            leftArrow,
            WIDE_CHOICES_X,
            rowIdx * SINGLE_ENTRY_HEIGHT,
            TEXT_SPEED_NO_TRANSFER,
            darkGray,
            NULL);
        Text_AddPrinterWithParamsAndColor(&menuData->windows.entries,
            FONT_SYSTEM,
            valStr,
            valX,
            rowIdx * SINGLE_ENTRY_HEIGHT,
            TEXT_SPEED_NO_TRANSFER,
            red,
            NULL);
        Text_AddPrinterWithParamsAndColor(&menuData->windows.entries,
            FONT_SYSTEM,
            rightArrow,
            200,
            rowIdx * SINGLE_ENTRY_HEIGHT,
            TEXT_SPEED_NO_TRANSFER,
            darkGray,
            NULL);

        String_Free(leftArrow);
        String_Free(rightArrow);
        Window_CopyToVRAM(&menuData->windows.entries);
        return;
    }

    {
        u16 numChoices = WideGetRowNumChoices(rowId);
        u16 selected = WideGetRowSelected(menuData, rowId);
        u16 minStep = (numChoices >= 4) ? 38 : 54;
        u16 xPos = WIDE_CHOICES_X;
        BOOL isClassic = WideRowIsClassic(rowId);
        enum OptionsMenuEntryID classicEntry = isClassic ? WideRowToClassicEntry(rowId) : ENTRY_CLOSE;

        for (u16 c = 0; c < numChoices && c < WIDE_MAX_ROW_CHOICES; c++) {
            String *choiceStr;
            u16 w;
            u16 step;
            TextColor color = (c == selected) ? red : darkGray;

            if (isClassic) {
                choiceStr = menuData->entries.asArray[classicEntry].choices[c];
            } else {
                choiceStr = WideNewAsciiString(sWideOptMeta[rowId - WIDE_ROW_60FPS].choices[c], menuData->heapID);
            }

            w = (u16)Font_CalcStringWidth(FONT_SYSTEM, choiceStr, 0);
            menuData->wideChoiceX[rowIdx][c] = xPos;
            menuData->wideChoiceW[rowIdx][c] = w;

            Text_AddPrinterWithParamsAndColor(&menuData->windows.entries,
                FONT_SYSTEM,
                choiceStr,
                xPos,
                rowIdx * SINGLE_ENTRY_HEIGHT,
                TEXT_SPEED_NO_TRANSFER,
                color,
                NULL);

            if (!isClassic) {
                String_Free(choiceStr);
            }

            step = (u16)(w + 14);
            if (step < minStep) {
                step = minStep;
            }
            xPos = (u16)(xPos + step);
        }
    }

    Window_CopyToVRAM(&menuData->windows.entries);
}

static void WideDrawCurrentTabEntries(OptionsMenuData *menuData)
{
    u16 rowCount = 0;
    const u8 *rows = WideGetTabRows(menuData->activeTab, &rowCount);
    TextColor whiteBg = TEXT_COLOR(1, 2, 15);
    String *labelStr = String_Init(64, menuData->heapID);

    Window_FillTilemap(&menuData->windows.entries, PIXEL_FILL(15));

    for (u16 r = 0; r < rowCount; r++) {
        u8 rowId = rows[r];

        if (WideRowIsClassic(rowId) || rowId == WIDE_ROW_CLOSE) {
            enum OptionsMenuEntryID classicEntry = WideRowToClassicEntry(rowId);
            String_Clear(labelStr);
            MessageLoader_GetString(menuData->msgLoader, sEntryLabels[classicEntry], labelStr);
            Text_AddPrinterWithParamsAndColor(&menuData->windows.entries,
                FONT_SYSTEM,
                labelStr,
                WIDE_LABEL_X,
                SINGLE_ENTRY_HEIGHT * r,
                TEXT_SPEED_NO_TRANSFER,
                whiteBg,
                NULL);
        } else {
            String *asciiLabel = WideNewAsciiString(sWideOptMeta[rowId - WIDE_ROW_60FPS].label, menuData->heapID);
            Text_AddPrinterWithParamsAndColor(&menuData->windows.entries,
                FONT_SYSTEM,
                asciiLabel,
                WIDE_LABEL_X,
                SINGLE_ENTRY_HEIGHT * r,
                TEXT_SPEED_NO_TRANSFER,
                whiteBg,
                NULL);
            String_Free(asciiLabel);
        }

        WidePrintRowChoices(menuData, r, FALSE);
    }

    Window_CopyToVRAM(&menuData->windows.entries);
    String_Free(labelStr);
}

static void WidePrintAsciiDescription(OptionsMenuData *menuData, const char *asciiDesc, BOOL scheduleVRAMCopy)
{
    if (IsTextPrinterDone(menuData) == FALSE) {
        Text_RemovePrinter(menuData->textPrinter);
    }

    u8 renderDelay = Options_TextFrameDelay(menuData->saveOptions);
    TextColor color = TEXT_COLOR(1, 2, 15);
    String *string = WideNewAsciiString(asciiDesc, menuData->heapID);

    Window_FillTilemap(&menuData->windows.description, 15);

    if (scheduleVRAMCopy == FALSE) {
        menuData->textPrinter = Text_AddPrinterWithParamsAndColor(&menuData->windows.description,
            FONT_MESSAGE,
            string,
            4,
            0,
            renderDelay,
            color,
            NULL);
    } else {
        Text_AddPrinterWithParamsAndColor(&menuData->windows.description,
            FONT_MESSAGE,
            string,
            4,
            0,
            TEXT_SPEED_NO_TRANSFER,
            color,
            NULL);
        Window_ScheduleCopyToVRAM(&menuData->windows.description);
    }

    String_Free(string);
}

static void WidePrintCurrentRowDescription(OptionsMenuData *menuData, BOOL scheduleVRAMCopy)
{
    u16 rowCount = 0;
    const u8 *rows = WideGetTabRows(menuData->activeTab, &rowCount);
    u8 rowId;

    if (menuData->cursor >= rowCount) {
        return;
    }

    rowId = rows[menuData->cursor];
    if (WideRowIsClassic(rowId) || rowId == WIDE_ROW_CLOSE) {
        PrintEntryDescription(menuData, (u16)WideRowToClassicEntry(rowId), scheduleVRAMCopy);
    } else {
        WidePrintAsciiDescription(menuData, sWideOptMeta[rowId - WIDE_ROW_60FPS].description, scheduleVRAMCopy);
    }
}

static void WideSwitchTab(OptionsMenuData *menuData, u8 newTab)
{
    if (newTab >= WIDE_TAB_COUNT || newTab == menuData->activeTab) {
        return;
    }

    menuData->activeTab = newTab;
    menuData->cursor = 0;
    Bg_ScheduleScroll(menuData->bgConfig,
        BG_LAYER_MAIN_0,
        BG_OFFSET_UPDATE_SET_Y,
        -FIRST_ENTRY_OFFSET);

    WideDrawTitleAndTabs(menuData);
    WideDrawCurrentTabEntries(menuData);
    WidePrintCurrentRowDescription(menuData, TRUE);
    Sound_PlayEffect(SE_CONFIRM_sseq_3);
}

static BOOL WideProcessMainInput(OptionsMenuData *menuData)
{
    u16 rowCount = 0;
    const u8 *rows = WideGetTabRows(menuData->activeTab, &rowCount);
    u8 curRowId = rows[menuData->cursor];
    int tx = 0;
    int ty = 0;

    // Mac mouse & iOS touch support
    if (SIM_Wide_PollMainTouch(&tx, &ty)) {
        // Top tab bar (y < 20)
        if (ty >= 0 && ty < 20) {
            for (u8 t = 0; t < WIDE_TAB_COUNT; t++) {
                int left = 8 + (int)sWideTabs[t].x - 2;
                int right = 8 + (int)sWideTabs[t].x + (int)sWideTabs[t].width + 2;
                if (tx >= left && tx < right) {
                    WideSwitchTab(menuData, t);
                    return FALSE;
                }
            }
            if (tx >= 288 && tx < WIDE_2D_WIDTH) {
                WideSwitchTab(menuData, (u8)((menuData->activeTab + 1) % WIDE_TAB_COUNT));
                return FALSE;
            }
            return FALSE;
        }

        // Entries panel rows (y = 24 .. 24 + rowCount * 16)
        if (tx >= 8 && tx < 8 + WIDE_ENTRIES_WIDTH * 8
            && ty >= FIRST_ENTRY_OFFSET && ty < FIRST_ENTRY_OFFSET + (int)(rowCount * SINGLE_ENTRY_HEIGHT)) {
            u16 hitRow = (u16)((ty - FIRST_ENTRY_OFFSET) / SINGLE_ENTRY_HEIGHT);
            u8 hitRowId = rows[hitRow];
            BOOL moved = (hitRow != menuData->cursor);

            if (moved) {
                menuData->cursor = hitRow;
                Bg_ScheduleScroll(menuData->bgConfig,
                    BG_LAYER_MAIN_0,
                    BG_OFFSET_UPDATE_SET_Y,
                    -(menuData->cursor * SINGLE_ENTRY_HEIGHT + FIRST_ENTRY_OFFSET));
                WidePrintCurrentRowDescription(menuData, TRUE);
            }

            if (hitRowId == WIDE_ROW_CLOSE) {
                return TRUE;
            }

            if (tx >= 8 + WIDE_CHOICES_X - 4) {
                if (hitRowId == WIDE_ROW_FRAME) {
                    u16 cur = menuData->entries.messageBoxStyle.selected;
                    u16 next = (tx < 8 + WIDE_FRAME_SPLIT_X) ? (u16)((cur + 19) % 20) : (u16)((cur + 1) % 20);
                    menuData->entries.messageBoxStyle.selected = next;
                    WidePrintRowChoices(menuData, hitRow, TRUE);
                    Sound_PlayEffect(SE_CONFIRM_sseq_3);
                    return FALSE;
                }

                {
                    int localX = tx - 8;
                    u16 numChoices = WideGetRowNumChoices(hitRowId);
                    u16 curSel = WideGetRowSelected(menuData, hitRowId);
                    for (u16 c = 0; c < numChoices && c < WIDE_MAX_ROW_CHOICES; c++) {
                        int x0 = (int)menuData->wideChoiceX[hitRow][c] - 4;
                        int x1 = (c + 1 < numChoices)
                            ? (int)menuData->wideChoiceX[hitRow][c + 1] - 4
                            : (int)(menuData->wideChoiceX[hitRow][c] + menuData->wideChoiceW[hitRow][c] + 12);
                        if (localX >= x0 && localX < x1) {
                            if (c != curSel) {
                                WideSetRowSelected(menuData, hitRowId, c);
                                WidePrintRowChoices(menuData, hitRow, TRUE);
                                Sound_PlayEffect(SE_CONFIRM_sseq_3);
                            } else if (moved) {
                                Sound_PlayEffect(SE_CONFIRM_sseq_3);
                            }
                            return FALSE;
                        }
                    }
                }
            }

            if (moved) {
                Sound_PlayEffect(SE_CONFIRM_sseq_3);
            }
            return FALSE;
        }
    }

    if ((JOY_NEW(PAD_BUTTON_A) && curRowId == WIDE_ROW_CLOSE) || JOY_NEW(PAD_BUTTON_B)) {
        return TRUE;
    }

    if (JOY_NEW(PAD_BUTTON_L)) {
        WideSwitchTab(menuData, (u8)((menuData->activeTab + WIDE_TAB_COUNT - 1) % WIDE_TAB_COUNT));
        return FALSE;
    }
    if (JOY_NEW(PAD_BUTTON_R)) {
        WideSwitchTab(menuData, (u8)((menuData->activeTab + 1) % WIDE_TAB_COUNT));
        return FALSE;
    }

    if (curRowId != WIDE_ROW_CLOSE) {
        u16 numChoices = WideGetRowNumChoices(curRowId);
        if (numChoices > 0) {
            if (JOY_NEW(PAD_KEY_RIGHT)) {
                u16 next = (u16)((WideGetRowSelected(menuData, curRowId) + 1) % numChoices);
                WideSetRowSelected(menuData, curRowId, next);
                WidePrintRowChoices(menuData, menuData->cursor, TRUE);
                Sound_PlayEffect(SE_CONFIRM_sseq_3);
            } else if (JOY_NEW(PAD_KEY_LEFT)) {
                u16 next = (u16)((WideGetRowSelected(menuData, curRowId) + numChoices - 1) % numChoices);
                WideSetRowSelected(menuData, curRowId, next);
                WidePrintRowChoices(menuData, menuData->cursor, TRUE);
                Sound_PlayEffect(SE_CONFIRM_sseq_3);
            }
        }
    }

    if (JOY_NEW(PAD_KEY_UP)) {
        menuData->cursor = (u32)((menuData->cursor + rowCount - 1) % rowCount);
        Bg_ScheduleScroll(menuData->bgConfig,
            BG_LAYER_MAIN_0,
            BG_OFFSET_UPDATE_SET_Y,
            -(menuData->cursor * SINGLE_ENTRY_HEIGHT + FIRST_ENTRY_OFFSET));
        WidePrintCurrentRowDescription(menuData, TRUE);
        Sound_PlayEffect(SE_CONFIRM_sseq_3);
    } else if (JOY_NEW(PAD_KEY_DOWN)) {
        menuData->cursor = (u32)((menuData->cursor + 1) % rowCount);
        Bg_ScheduleScroll(menuData->bgConfig,
            BG_LAYER_MAIN_0,
            BG_OFFSET_UPDATE_SET_Y,
            -(menuData->cursor * SINGLE_ENTRY_HEIGHT + FIRST_ENTRY_OFFSET));
        WidePrintCurrentRowDescription(menuData, TRUE);
        Sound_PlayEffect(SE_CONFIRM_sseq_3);
    }

    return FALSE;
}

#endif // SDK_PORT
