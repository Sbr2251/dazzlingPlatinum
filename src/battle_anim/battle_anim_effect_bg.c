#include "battle_anim/battle_anim_effect_bg.h"

#include <nitro.h>
#include <string.h>

#include "constants/battle/battle_anim.h"
#include "constants/battle/battle_effect_bg.h"
#include "constants/graphics.h"

#include "battle_anim/battle_anim_system.h"

#include "bg_window.h"
#include "graphics.h"
#include "heap.h"
#include "narc.h"
#include "palette.h"
#include "sys_task.h"

#include "res/graphics/battle/effect_bg/bw2_effect_bg.naix.h"

// BW2's BgPalAnim (btlv_effvm.c:1916) writes the anim rows over BG palette row 8, the background's
// first row, which we keep at BATTLE_BG_PALETTE_EFFECT
#define PAL_ANIM_ROW         BATTLE_BG_PALETTE_EFFECT
#define PAL_ANIM_MAX_FRAMES  128
#define PAL_ANIM_LIST_END    0xFF
#define PAL_ANIM_FRAMES_AT   0x80
#define PAL_ANIM_FRAMES_END  0xFF98
#define PAL_ANIM_FIRST_ROW   8 // the anim file's rows are named 8..15
#define PAL_ANIM_MAX_ROWS    8
#define PAL_ANIM_TASK_PRIO   1101 // after the BG switch task (1100)

typedef struct PalAnim {
    PaletteData *paletteData;
    u8 rows[PAL_ANIM_MAX_FRAMES];
    u16 frames[PAL_ANIM_MAX_FRAMES];
    u16 colors[PAL_ANIM_MAX_ROWS][16];
    int numFrames;
    int numRows;
    int index;
    int timer;
    int loops; // 0: until the background goes
} PalAnim;

#include "battle_anim/bw2_effect_bg_table.h"

// A BG3 change made in one VBlank, so a cut shows no torn or black frame (BattleEffectBg_UploadOnVBlank)
typedef struct BgUpload {
    BgConfig *bgConfig;
    u8 layer;
    u8 colorMode;
    const void *chars;
    u32 charSize;
    void *charFile; // freed after the upload, or NULL
    const void *screen;
    u32 screenSize;
    void *screenFile;
    BOOL resetOffset; // the scroll goes back to 0,0 with the screen
} BgUpload;

static BattleEffectBgStats sBattleEffectBgStats;
static BgUpload sUpload;
static SysTask *sUploadTask;
static SysTask *sPalAnimTask;
static PalAnim *sPalAnim;
static int sLoadedBgID = -1;
static BOOL sCut;
static BOOL sCutBack;
static BOOL sCutBackDone; // a cut back started in this script

static const BattleEffectBgEntry *GetEntry(int bgID)
{
    if (!BattleEffectBg_IsBw2(bgID)) {
        return NULL;
    }

    return &sBattleEffectBgs[bgID - BATTLE_BG_BW2_FIRST];
}

BOOL BattleEffectBg_IsBw2(int bgID)
{
    return bgID >= BATTLE_BG_BW2_FIRST && bgID < BATTLE_BG_BW2_FIRST + BATTLE_BG_BW2_COUNT;
}

int BattleEffectBg_ContestBg(int bgID)
{
    const BattleEffectBgEntry *entry = GetEntry(bgID);
    return entry != NULL ? entry->contestBg : bgID;
}

u16 BattleEffectBg_PaletteMask(int bgID)
{
    const BattleEffectBgEntry *entry = GetEntry(bgID);
    return entry != NULL ? entry->rowMask : BATTLE_BG_PALETTE_FLAG_EFFECT;
}

u16 BattleEffectBg_CurrentPaletteMask(void)
{
    return BattleEffectBg_PaletteMask(sLoadedBgID);
}

static void UploadTask(SysTask *task, void *data)
{
    BgUpload *upload = data;

    Bg_SetControlParam(upload->bgConfig, upload->layer, BG_CONTROL_PARAM_COLOR_MODE, upload->colorMode);
    Bg_LoadTilesToVRAM(upload->bgConfig, upload->layer, (void *)upload->chars, upload->charSize, 0);
    Bg_LoadTilemapBuffer(upload->bgConfig, upload->layer, (void *)upload->screen, upload->screenSize);
    Bg_CopyTilemapBufferToVRAM(upload->bgConfig, upload->layer);

    if (upload->resetOffset) {
        Bg_SetOffset(upload->bgConfig, upload->layer, BG_OFFSET_UPDATE_SET_X, 0);
        Bg_SetOffset(upload->bgConfig, upload->layer, BG_OFFSET_UPDATE_SET_Y, 0);
    }

    Bg_ToggleLayer(upload->layer, TRUE);

    // Runs in the VBlank handler: the files are freed later, on the main loop (BattleEffectBg_IsUploading)
    SysTask_Done(task);
    sUploadTask = NULL;
}

void BattleEffectBg_CancelUpload(void)
{
    if (sUploadTask != NULL) {
        SysTask_Done(sUploadTask);
        sUploadTask = NULL;
    }

    if (sUpload.charFile != NULL) {
        Heap_Free(sUpload.charFile);
    }

    if (sUpload.screenFile != NULL) {
        Heap_Free(sUpload.screenFile);
    }

    memset(&sUpload, 0, sizeof(sUpload));
}

// TRUE while the upload waits for its VBlank; FALSE once it is done, its files freed
BOOL BattleEffectBg_IsUploading(void)
{
    if (sUploadTask != NULL) {
        return TRUE;
    }

    BattleEffectBg_CancelUpload();
    return FALSE;
}

// Sets the layer's colour mode, tiles (at its char base) and whole screen (and with resetOffset its scroll to
// 0,0) in the next VBlank, then frees the files it was given. The palette goes through PaletteData as usual, which the battle commits in the same
// VBlank.
void BattleEffectBg_UploadOnVBlank(BgConfig *bgConfig, enum BgLayer layer, u8 colorMode, const void *chars, u32 charSize, void *charFile, const void *screen, u32 screenSize, void *screenFile, BOOL resetOffset)
{
    BattleEffectBg_CancelUpload();

    sUpload.bgConfig = bgConfig;
    sUpload.layer = layer;
    sUpload.colorMode = colorMode;
    sUpload.chars = chars;
    sUpload.charSize = charSize;
    sUpload.charFile = charFile;
    sUpload.screen = screen;
    sUpload.screenSize = screenSize;
    sUpload.screenFile = screenFile;
    sUpload.resetOffset = resetOffset;
    sUploadTask = SysTask_ExecuteOnVBlank(UploadTask, &sUpload, 0);
}

static void LoadPalettes(BattleAnimSystem *system, const BattleEffectBgEntry *entry, BOOL blackBackdrop)
{
    PaletteData *paletteData = BattleAnimSystem_GetPaletteData(system);
    NNSG2dPaletteData *palette;
    void *file = Graphics_GetPlttData(NARC_INDEX_BATTLE__GRAPHIC__BW2_EFFECT_BG, entry->nclr, &palette, BattleAnimSystem_GetHeapID(system));
    const u16 *colors = palette->pRawData;
    u32 count = palette->szByte / sizeof(u16);

    for (int row = 8; row < 16; row++) {
        if ((entry->rowMask & (1 << row)) && (u32)(row - 8 + 1) * 16 <= count) {
            PaletteData_LoadBuffer(paletteData, colors + (row - 8) * 16, PLTTBUF_MAIN_BG, PLTT_DEST(row), PALETTE_SIZE_BYTES);
        }
    }

    Heap_Free(file);

    if (blackBackdrop) {
        u16 black = 0;
        PaletteData_LoadBuffer(paletteData, &black, PLTTBUF_MAIN_BG, 0, sizeof(black));
    }
}

static void Loaded(BattleAnimSystem *system, int bgID, const BattleEffectBgEntry *entry)
{
    sLoadedBgID = bgID;
    sBattleEffectBgStats.loads++;
    sBattleEffectBgStats.lastBgID = bgID;
    sBattleEffectBgStats.lastTiles = entry->numTiles;

    if (entry->palAnim != BATTLE_EFFECT_BG_NO_MEMBER) {
        for (int i = 0; i < NELEMS(sBattleEffectBgPalAnimMembers); i++) {
            if (sBattleEffectBgPalAnimMembers[i][1] == entry->palAnim) {
                BattleEffectBg_StartPalAnim(system, sBattleEffectBgPalAnimMembers[i][0], 0);
            }
        }
    }
}

// The cut's load: the palette now, the tiles, screen and 4bpp mode in the next VBlank, all at once
void BattleEffectBg_LoadOnVBlank(BattleAnimSystem *system, enum BgLayer layer, int bgID, BOOL reversed)
{
    const BattleEffectBgEntry *entry = GetEntry(bgID);
    enum HeapID heapID = BattleAnimSystem_GetHeapID(system);
    NNSG2dCharacterData *chars;
    NNSG2dScreenData *screen;

    GF_ASSERT(entry != NULL);
    BattleEffectBg_StopPalAnim();

    void *charFile = Graphics_GetCharData(NARC_INDEX_BATTLE__GRAPHIC__BW2_EFFECT_BG, entry->ncgr, TRUE, &chars, heapID);
    void *screenFile = Graphics_GetScrnData(NARC_INDEX_BATTLE__GRAPHIC__BW2_EFFECT_BG, reversed ? entry->nscrReversed : entry->nscr, TRUE, &screen, heapID);

    LoadPalettes(system, entry, TRUE);
    BattleEffectBg_UploadOnVBlank(BattleAnimSystem_GetBgConfig(system), layer, GX_BG_COLORMODE_16, chars->pRawData, chars->szByte, charFile, screen->rawData, screen->szByte, screenFile, FALSE);
    Loaded(system, bgID, entry);
}

// Tiles at the layer's char base (BG3: 0x10000 in FADE and CUT mode, up to 32 KB; 0x0c000 in BLEND mode,
// up to 16 KB, under the backdrop BG2 shows), the screen, and the palette rows the entry uses. The colour
// BW2 leaves transparent around its picture shows the backdrop colour, made black as BW2's is; every
// restore reloads the whole BG palette.
void BattleEffectBg_Load(BattleAnimSystem *system, enum BgLayer layer, int bgID, BOOL reversed, BOOL blackBackdrop)
{
    const BattleEffectBgEntry *entry = GetEntry(bgID);
    BgConfig *bgConfig = BattleAnimSystem_GetBgConfig(system);
    enum HeapID heapID = BattleAnimSystem_GetHeapID(system);

    GF_ASSERT(entry != NULL);
    BattleEffectBg_StopPalAnim();

    Graphics_LoadTilesToBgLayer(NARC_INDEX_BATTLE__GRAPHIC__BW2_EFFECT_BG, entry->ncgr, bgConfig, layer, 0, 0, TRUE, heapID);
    Bg_ClearTilemap(bgConfig, layer);
    Graphics_LoadTilemapToBgLayer(NARC_INDEX_BATTLE__GRAPHIC__BW2_EFFECT_BG, reversed ? entry->nscrReversed : entry->nscr, bgConfig, layer, 0, 0, TRUE, heapID);
    LoadPalettes(system, entry, blackBackdrop);
    Loaded(system, bgID, entry);
}

static void PalAnim_Apply(PalAnim *anim)
{
    int row = anim->rows[anim->index] - PAL_ANIM_FIRST_ROW;
    const u16 *src = anim->colors[row >= 0 && row < anim->numRows ? row : 0];

    // A running palette fade blends from the unfaded buffer every step; outside one the faded buffer is
    // what is shown, so it takes the row too
    MI_CpuCopy16(src, PaletteData_GetUnfadedBuffer(anim->paletteData, PLTTBUF_MAIN_BG) + PLTT_DEST(PAL_ANIM_ROW), PALETTE_SIZE_BYTES);

    if ((PaletteData_GetSelectedBuffersMask(anim->paletteData) & (1 << PLTTBUF_MAIN_BG)) == 0) {
        MI_CpuCopy16(src, PaletteData_GetFadedBuffer(anim->paletteData, PLTTBUF_MAIN_BG) + PLTT_DEST(PAL_ANIM_ROW), PALETTE_SIZE_BYTES);
    }

    sBattleEffectBgStats.palAnimSteps++;
}

// BtlvEffvm_PalAnimTask (btlv_effvm.c:4410): the first row at once, then each row after its frame count
// (as BW2 counts it: a row shows until the timer reaches count - 2). One step per battle frame.
static void PalAnimTask(SysTask *task, void *data)
{
    PalAnim *anim = data;

    if (anim->timer < anim->frames[anim->index] - 2) {
        anim->timer++;
        return;
    }

    PalAnim_Apply(anim);
    anim->timer = 0;

    if (anim->index >= anim->numFrames - 1) {
        anim->index = 0;

        if (anim->loops > 0 && --anim->loops == 0) {
            BattleEffectBg_StopPalAnim();
        }
    } else {
        anim->index++;
    }
}

void BattleEffectBg_StartPalAnim(BattleAnimSystem *system, int animID, int loops)
{
    enum HeapID heapID = BattleAnimSystem_GetHeapID(system);
    u32 member = BATTLE_EFFECT_BG_NO_MEMBER;
    NNSG2dPaletteData *palette;

    BattleEffectBg_StopPalAnim();

    for (int i = 0; i < NELEMS(sBattleEffectBgPalAnimMembers); i++) {
        if (sBattleEffectBgPalAnimMembers[i][0] == animID) {
            member = sBattleEffectBgPalAnimMembers[i][1];
        }
    }

    if (member == BATTLE_EFFECT_BG_NO_MEMBER) {
        return;
    }

    PalAnim *anim = Heap_Alloc(heapID, sizeof(PalAnim));

    if (anim == NULL) {
        return;
    }

    memset(anim, 0, sizeof(PalAnim));
    anim->paletteData = BattleAnimSystem_GetPaletteData(system);
    anim->loops = loops;

    u8 *bin = NARC_AllocAndReadWholeMemberByIndexPair(NARC_INDEX_BATTLE__GRAPHIC__BW2_EFFECT_BG, member, heapID);

    while (anim->numFrames < PAL_ANIM_MAX_FRAMES && bin[anim->numFrames] != PAL_ANIM_LIST_END) {
        anim->rows[anim->numFrames] = bin[anim->numFrames];
        anim->numFrames++;
    }

    const u16 *frames = (const u16 *)(bin + PAL_ANIM_FRAMES_AT);

    for (int i = 0; i < anim->numFrames && frames[i] != PAL_ANIM_FRAMES_END; i++) {
        anim->frames[i] = frames[i];
    }

    Heap_Free(bin);

    void *file = Graphics_GetPlttData(NARC_INDEX_BATTLE__GRAPHIC__BW2_EFFECT_BG, member + 1, &palette, heapID);
    anim->numRows = palette->szByte / PALETTE_SIZE_BYTES;

    if (anim->numRows > PAL_ANIM_MAX_ROWS) {
        anim->numRows = PAL_ANIM_MAX_ROWS;
    }

    MI_CpuCopy16(palette->pRawData, anim->colors, anim->numRows * PALETTE_SIZE_BYTES);
    Heap_Free(file);

    if (anim->numFrames == 0) {
        Heap_Free(anim);
        return;
    }

    sPalAnim = anim;
    sPalAnimTask = SysTask_Start(PalAnimTask, anim, PAL_ANIM_TASK_PRIO);
    sBattleEffectBgStats.palAnimActive = TRUE;
    PalAnimTask(sPalAnimTask, anim);
}

void BattleEffectBg_StopPalAnim(void)
{
    if (sPalAnimTask != NULL) {
        SysTask_Done(sPalAnimTask);
        sPalAnimTask = NULL;
    }

    if (sPalAnim != NULL) {
        Heap_Free(sPalAnim);
        sPalAnim = NULL;
    }

    sBattleEffectBgStats.palAnimActive = FALSE;
}

void BattleEffectBg_SetCut(BOOL cut)
{
    sCut = cut;
    sBattleEffectBgStats.cutActive = cut;
}

BOOL BattleEffectBg_IsCut(void)
{
    return sCut;
}

// A cut back is running: the arena comes back while BG3 still holds the effect picture
void BattleEffectBg_SetCutBack(BOOL cutBack)
{
    sCutBack = cutBack;

    if (cutBack) {
        sCutBackDone = TRUE;
    }
}

BOOL BattleEffectBg_IsCutBackDone(void)
{
    return sCutBackDone;
}

BOOL BattleEffectBg_IsCutBack(void)
{
    return sCutBack;
}

void BattleEffectBg_CountCut(void)
{
    sBattleEffectBgStats.cuts++;
}

// The script ended or the system was deleted: nothing may outlive it
void BattleEffectBg_Reset(void)
{
    BattleEffectBg_CancelUpload();
    BattleEffectBg_StopPalAnim();
    BattleEffectBg_SetCut(FALSE);
    sCutBack = FALSE;
    sCutBackDone = FALSE;
    sLoadedBgID = -1;
}
