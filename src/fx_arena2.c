#include "fx_arena2.h"

#include <nitro.h>
#include <stdlib.h>
#include <string.h>

#include "constants/player_avatar.h"
#include "field/field_system.h"
#include "field_overworld_state.h"
#include "map_header.h"
#include "port/sim_config_prj.h"
#include "savedata.h"
#include "struct_defs/player_data.h"

// ---------------------------------------------------------------------------
// Feature gate (same SIM_HEADLESS rule as fx_arena.c)
// ---------------------------------------------------------------------------

static int EnvFlag(const char *name)
{
    const char *env = getenv(name);

    if (env == NULL || env[0] == 0) {
        return -1;
    }

    return env[0] != '0' ? 1 : 0;
}

BOOL FxArena2_RealPlaceEnabled(void)
{
    static int sHeadless = -1;
    int env;

    if (sHeadless < 0) {
        const char *headless = getenv("SIM_HEADLESS");
        sHeadless = (headless != NULL && headless[0] != 0 && headless[0] != '0') ? 1 : 0;
    }

    env = EnvFlag("SIM_FX_REALPLACE");

    if (sHeadless) {
        return env == 1 ? TRUE : FALSE;
    }

    if (env >= 0) {
        return env == 1 ? TRUE : FALSE;
    }

    return SIM_Config_prj_GetConfig()->realPlaceArena ? TRUE : FALSE;
}

// ---------------------------------------------------------------------------
// Capture buffer
// ---------------------------------------------------------------------------
// One byte per pixel plus no palette storage: the palette is a fixed
// function of the index (see FxArena2_PaletteEntry), so the whole
// capture is 48 KB of static RAM that survives the field teardown.

static u8 sCaptureIndices[FX_ARENA2_WIDTH * FX_ARENA2_HEIGHT];
static BOOL sCaptureValid = FALSE;
static enum BattleBackground sCaptureBackground = BACKGROUND_PLAIN;

// Ordered 4x4 Bayer thresholds, 0..15.
static const u8 sBayer[4][4] = {
    { 0, 8, 2, 10 },
    { 12, 4, 14, 6 },
    { 3, 11, 1, 9 },
    { 15, 7, 13, 5 },
};

enum BattleBackground FxArena2_FieldBackground(const FieldSystem *fieldSystem)
{
    PlayerData *player;
    enum BattleBackground background;

    if (fieldSystem == NULL || fieldSystem->location == NULL) {
        return BACKGROUND_PLAIN;
    }

    background = MapHeader_GetBattleBG(fieldSystem->location->mapHeaderID);

    if (fieldSystem->saveData != NULL) {
        player = FieldOverworldState_GetPlayerData(SaveData_GetFieldOverworldState(fieldSystem->saveData));

        if (player != NULL && player->playerState == PLAYER_AVATAR_SURFING) {
            background = BACKGROUND_WATER;
        }
    }

    return background;
}

BOOL FxArena2_BackgroundEligible(enum BattleBackground background)
{
    switch (background) {
    case BACKGROUND_PLAIN:
    case BACKGROUND_WATER:
    case BACKGROUND_CITY:
    case BACKGROUND_FOREST:
    case BACKGROUND_MOUNTAIN:
    case BACKGROUND_SNOW:
        return TRUE;
    default:
        return FALSE;
    }
}

BOOL FxArena2_ShouldCapture(const FieldSystem *fieldSystem)
{
    if (!FxArena2_RealPlaceEnabled() || fieldSystem == NULL) {
        return FALSE;
    }

    return FxArena2_BackgroundEligible(FxArena2_FieldBackground(fieldSystem));
}

void FxArena2_StartCapture(const FieldSystem *fieldSystem)
{
    sCaptureValid = FALSE;
    sCaptureBackground = FxArena2_FieldBackground(fieldSystem);
    GX_SetCapture(GX_CAPTURE_SIZE_256x192, GX_CAPTURE_MODE_A, GX_CAPTURE_SRCA_2D3D,
        GX_CAPTURE_SRCB_VRAM_0x00000, GX_CAPTURE_DEST_VRAM_C_0x00000, 16, 0);
}

static int Clamp31(int value)
{
    if (value < 0) {
        return 0;
    }

    if (value > 31) {
        return 31;
    }

    return value;
}

u16 FxArena2_PaletteEntry(int index)
{
    int r = (index >> 5) & 7;
    int g = (index >> 2) & 7;
    int b = index & 3;

    // Expand 3/3/2 bits back to 5 bits, rounding to the centre of the bin.
    return GX_RGB((r * 31 + 3) / 7, (g * 31 + 3) / 7, (b * 31 + 1) / 3);
}

void FxArena2_FinishCapture(void)
{
    const u16 *vram = (const u16 *)HW_LCDC_VRAM_C;
    int x, y;
    u8 first;
    BOOL varied = FALSE;

    first = 0;

    for (y = 0; y < FX_ARENA2_HEIGHT; y++) {
        for (x = 0; x < FX_ARENA2_WIDTH; x++) {
            u16 pixel = vram[y * FX_ARENA2_WIDTH + x];
            int r = (pixel >> 0) & 31;
            int g = (pixel >> 5) & 31;
            int b = (pixel >> 10) & 31;
            int dither = (int)sBayer[y & 3][x & 3] - 8;
            int index;

            // Dither by about half a quantization step per channel before
            // truncating, so smooth sky and ground gradients band less.
            // Red/green step 4 (5 -> 3 bits), blue step 8 (5 -> 2 bits).
            r = Clamp31(r + (dither >> 2));
            g = Clamp31(g + (dither >> 2));
            b = Clamp31(b + dither);
            index = ((r >> 2) << 5) | ((g >> 2) << 2) | (b >> 3);
            sCaptureIndices[y * FX_ARENA2_WIDTH + x] = (u8)index;

            if (y == 0 && x == 0) {
                first = (u8)index;
            } else if ((u8)index != first) {
                varied = TRUE;
            }
        }
    }

    // All one colour means the capture never ran (VRAM C still holds
    // whatever was there, or the frame was blank): fall back instead
    // of showing a flat-colour backdrop.
    sCaptureValid = varied;
}

BOOL FxArena2_HasCapture(void)
{
    return sCaptureValid;
}

enum BattleBackground FxArena2_CaptureBackground(void)
{
    return sCaptureBackground;
}

u8 FxArena2_CaptureIndex(int x, int y)
{
    if (x < 0 || x >= FX_ARENA2_WIDTH || y < 0 || y >= FX_ARENA2_HEIGHT) {
        return 0;
    }

    return sCaptureIndices[y * FX_ARENA2_WIDTH + x];
}

void FxArena2_ClearCapture(void)
{
    sCaptureValid = FALSE;
}
