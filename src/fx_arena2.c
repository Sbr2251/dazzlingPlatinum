#include "fx_arena2.h"

#include <nitro.h>
#include <stdlib.h>
#include <string.h>

#include "battle/battle_system.h"
#include "constants/heap.h"
#include "constants/map_object.h"
#include "constants/player_avatar.h"
#include "field/field_system.h"
#include "field_overworld_state.h"
#include "map_header.h"
#include "map_object.h"
#include "math_util.h"
#include "palette.h"
#include "player_avatar.h"
#include "port/sim_config_prj.h"
#include "port/sim_wide.h"
#include "savedata.h"
#include "struct_defs/player_data.h"

#include "bg_window.h"
#include "billboard.h"
#include "camera.h"
#include "heap.h"

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

    // Wide layout: the simulator's display capture re-render only covers
    // the left ~55% of the 256x192 capture target in wide mode, so a
    // wide capture would show a black right half as the backdrop. Fall
    // back to the classic backdrop there (the lane spec's "else" case);
    // the wide stage stretches the prebuilt art correctly.
    if (SIM_Wide_IsWideLayout()) {
        return FALSE;
    }

    return FxArena2_BackgroundEligible(FxArena2_FieldBackground(fieldSystem));
}

// ---------------------------------------------------------------------------
// Map objects: hidden for the capture, then restored exactly
// ---------------------------------------------------------------------------

// LocalMapObjByIndex matches by local ID and skips objects with
// STATUS_25, so it can miss a story NPC (Barry on Route 213 kept
// showing up in the lakeside capture). Scan the manager's array
// directly instead: every active slot, whatever its local ID.
#define FX_ARENA2_MAX_HIDDEN 256

static u16 sHiddenIndices[FX_ARENA2_MAX_HIDDEN];
static int sHiddenCount = 0;
static BOOL sObjectsHidden = FALSE;
static BOOL sPlayerHidden = FALSE;
static u32 sBillboardDrawMask = 0;

void FxArena2_HideMapObjects(const FieldSystem *fieldSystem)
{
    int i, max;

    if (fieldSystem == NULL || fieldSystem->mapObjMan == NULL || sObjectsHidden) {
        return;
    }

    // Suspend every billboard list for the capture frame. MapObjects'
    // sprites are billboards, and so are script-driven actors (the
    // Arc2 NPCs on Route 213 are not MapObjects, so the loop above
    // cannot hide them); suspending all lists covers both. The lists
    // keep updating while suspended, so resuming shows them exactly
    // where they would have been.
    sBillboardDrawMask = BillboardLists_SuspendDraw();

    (void)max;
    sHiddenCount = 0;
    sObjectsHidden = TRUE;

    for (i = 0; i < MapObjectMan_GetMaxObjects(fieldSystem->mapObjMan) && sHiddenCount < FX_ARENA2_MAX_HIDDEN; i++) {
        MapObject *obj = MapObjectMan_GetMapObjectBySlot(fieldSystem->mapObjMan, i);

        if (obj == NULL || !MapObject_CheckStatus(obj, MAP_OBJ_STATUS_0) || MapObject_IsHidden(obj)) {
            continue;
        }

        MapObject_SetHidden(obj, TRUE);
        sHiddenIndices[sHiddenCount++] = (u16)i;
    }

    // The player is not in the local list: hide it through the avatar.
    // (A following Pokemon / partner is a local object, covered above.)
    if (fieldSystem->playerAvatar != NULL) {
        MapObject *playerObj = PlayerAvatar_GetMapObject(fieldSystem->playerAvatar);

        if (playerObj != NULL && !MapObject_IsHidden(playerObj)) {
            MapObject_SetHidden(playerObj, TRUE);
            sPlayerHidden = TRUE;
        }
    }
}

void FxArena2_RestoreMapObjects(const FieldSystem *fieldSystem)
{
    int i;

    if (!sObjectsHidden) {
        return;
    }

    if (fieldSystem != NULL && fieldSystem->mapObjMan != NULL) {
        for (i = 0; i < sHiddenCount; i++) {
            MapObject *obj = MapObjectMan_GetMapObjectBySlot(fieldSystem->mapObjMan, sHiddenIndices[i]);

            // Slots are stable across the capture frames (the
            // encounter task holds the field, so no object is added
            // or deleted), so restoring by slot is exact.
            if (obj != NULL) {
                MapObject_SetHidden(obj, FALSE);
            }
        }
    }

    if (sPlayerHidden && fieldSystem != NULL && fieldSystem->playerAvatar != NULL) {
        MapObject *playerObj = PlayerAvatar_GetMapObject(fieldSystem->playerAvatar);

        if (playerObj != NULL) {
            MapObject_SetHidden(playerObj, FALSE);
        }
    }

    BillboardLists_ResumeDraw(sBillboardDrawMask);

    sHiddenCount = 0;
    sObjectsHidden = FALSE;
    sPlayerHidden = FALSE;
}

// ---------------------------------------------------------------------------
// Capture camera: low, behind the player, looking where they face
// ---------------------------------------------------------------------------
// The field camera tracks the player and the zones update holds still
// while a FieldTask runs, so the settings below survive the capture
// frames and the snapshot restores the field camera exactly.

#define FX_ARENA2_CAM_PITCH_DEG 8
#define FX_ARENA2_CAM_DISTANCE (FX32_ONE * 56)
#define FX_ARENA2_CAM_FOV_DEG   38
#define FX_ARENA2_CAM_NEAR      (FX32_ONE * 8)

static Camera sSavedCamera;
static BOOL sCameraSaved = FALSE;

void FxArena2_SaveCamera(const FieldSystem *fieldSystem)
{
    if (fieldSystem == NULL || fieldSystem->camera == NULL) {
        sCameraSaved = FALSE;
        return;
    }

    Camera_Copy(fieldSystem->camera, &sSavedCamera);
    sCameraSaved = TRUE;
}

void FxArena2_SetCaptureCamera(const FieldSystem *fieldSystem)
{
    Camera *camera;
    CameraAngle angle;
    int facing;

    if (fieldSystem == NULL || fieldSystem->camera == NULL || fieldSystem->playerAvatar == NULL) {
        return;
    }

    camera = fieldSystem->camera;
    facing = PlayerAvatar_GetFacingDir(fieldSystem->playerAvatar);

    // Yaw: the camera sits behind the player, opposite the facing
    // direction. The default (facing north) is yaw 0 (camera south of
    // the target); the other facings rotate around the target.
    memset(&angle, 0, sizeof(angle));
    angle.x = (u16)(-F32_DEG_TO_IDX(FX_ARENA2_CAM_PITCH_DEG));

    switch (facing) {
    case DIR_NORTH:
        angle.y = 0;
        break;
    case DIR_SOUTH:
        angle.y = (u16)F32_DEG_TO_IDX(180);
        break;
    case DIR_WEST:
        angle.y = (u16)F32_DEG_TO_IDX(90);
        break;
    case DIR_EAST:
        angle.y = (u16)F32_DEG_TO_IDX(270);
        break;
    default:
        angle.y = 0;
        break;
    }

    Camera_SetAngleAroundTarget(&angle, camera);
    Camera_SetDistance(FX_ARENA2_CAM_DISTANCE, camera);
    Camera_SetFOV((u16)F32_DEG_TO_IDX(FX_ARENA2_CAM_FOV_DEG), camera);

    // A close near clip keeps the foreground ground in range; the field
    // default (150) would void everything within 9 tiles of the lens.
    Camera_SetClipping(FX_ARENA2_CAM_NEAR, sCameraSaved ? sSavedCamera.perspective.farClip : CAMERA_DEFAULT_FAR_CLIP, camera);

    Camera_ComputeProjectionMatrix(CAMERA_PROJECTION_PERSPECTIVE, camera);
}

void FxArena2_RestoreCamera(const FieldSystem *fieldSystem)
{
    if (!sCameraSaved || fieldSystem == NULL || fieldSystem->camera == NULL) {
        return;
    }

    Camera_Copy(&sSavedCamera, fieldSystem->camera);
    Camera_ComputeProjectionMatrix(fieldSystem->camera->projection, fieldSystem->camera);
    sCameraSaved = FALSE;
}

// ---------------------------------------------------------------------------
// Capture
// ---------------------------------------------------------------------------

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
    int r5, g5, b5, grey;

    // Expand 3/3/2 bits back to 5 bits, rounding to the centre of the bin.
    r5 = (r * 31 + 3) / 7;
    g5 = (g * 31 + 3) / 7;
    b5 = (b * 31 + 1) / 3;

    // Soften the backdrop so the battlers stay readable: desaturate a
    // quarter of the way to grey, then darken to 7/8.
    grey = (r5 * 3 + g5 * 6 + b5) / 10;
    r5 = (r5 * 3 + grey) / 4 * 7 / 8;
    g5 = (g5 * 3 + grey) / 4 * 7 / 8;
    b5 = (b5 * 3 + grey) / 4 * 7 / 8;

    return GX_RGB(Clamp31(r5), Clamp31(g5), Clamp31(b5));
}

// Quantize a 5-5-5 RGB pixel to a 3-3-2 palette index, dithered by the
// Bayer offset of its pixel position. The battle's BG palette slots
// 160..191 hold the text box frame and the font; BG3 tiles must never
// produce those indices (see ApplyToBattleBg). Indices 160..191 are
// exactly rIdx == 5, so nudge those reds to a neighbour bin.
static u8 FxArena2_Quantize(int r, int g, int b, int dither)
{
    int rIdx, gIdx, bIdx;

    // Dither by about half a quantization step per channel before
    // truncating, so smooth sky and ground gradients band less.
    // Red/green step 4 (5 -> 3 bits), blue step 8 (5 -> 2 bits).
    r = Clamp31(r + (dither >> 2));
    g = Clamp31(g + (dither >> 2));
    b = Clamp31(b + dither);
    rIdx = r >> 2;
    gIdx = g >> 2;
    bIdx = b >> 3;

    if (rIdx == 5) {
        rIdx = (r < 22) ? 4 : 6;
    }

    return (u8)((rIdx << 5) | (gIdx << 2) | bIdx);
}

// The field's clear colour (pure black) marks void: the sky above the
// loaded terrain and holes where an unloaded block shows through.
// Fill those with a sky gradient / distance fog colour, so the backdrop
// reads as a horizon instead of a black hole.
#define FX_ARENA2_SKY_ZENITH_R 55
#define FX_ARENA2_SKY_ZENITH_G 100
#define FX_ARENA2_SKY_ZENITH_B 175
#define FX_ARENA2_SKY_HORIZON_R 175
#define FX_ARENA2_SKY_HORIZON_G 205
#define FX_ARENA2_SKY_HORIZON_B 225
#define FX_ARENA2_FOG_R 145
#define FX_ARENA2_FOG_G 170
#define FX_ARENA2_FOG_B 190

static void FxArena2_FillVoid(const u16 *vram)
{
    int x, y;

    for (x = 0; x < FX_ARENA2_WIDTH; x++) {
        int horizon = FX_ARENA2_HEIGHT;

        // First non-void (non-pure-black) row in this column: the
        // terrain edge. Everything above it is sky.
        for (y = 0; y < FX_ARENA2_HEIGHT; y++) {
            if ((vram[y * FX_ARENA2_WIDTH + x] & 0x7FFF) != 0) {
                horizon = y;
                break;
            }
        }

        for (y = 0; y < horizon; y++) {
            // Zenith -> horizon gradient across the sky column, so
            // the fill follows the terrain's silhouette instead of
            // banding on a fixed row.
            int t = (horizon > 0) ? (y * 256) / horizon : 256;
            int r = (FX_ARENA2_SKY_ZENITH_R * (256 - t) + FX_ARENA2_SKY_HORIZON_R * t) / 256;
            int g = (FX_ARENA2_SKY_ZENITH_G * (256 - t) + FX_ARENA2_SKY_HORIZON_G * t) / 256;
            int b = (FX_ARENA2_SKY_ZENITH_B * (256 - t) + FX_ARENA2_SKY_HORIZON_B * t) / 256;
            int dither = (int)sBayer[y & 3][x & 3] - 8;

            sCaptureIndices[y * FX_ARENA2_WIDTH + x] = FxArena2_Quantize(r * 31 / 255, g * 31 / 255, b * 31 / 255, dither);
        }

        // Any remaining pure-black pixel below the sky is a hole in
        // the loaded terrain (an unloaded block showing through, or
        // the far plane's edge): fill with the distance fog colour
        // rather than leaving a black pit.
        for (y = horizon; y < FX_ARENA2_HEIGHT; y++) {
            if ((vram[y * FX_ARENA2_WIDTH + x] & 0x7FFF) == 0) {
                int dither = (int)sBayer[y & 3][x & 3] - 8;

                sCaptureIndices[y * FX_ARENA2_WIDTH + x] = FxArena2_Quantize(
                    FX_ARENA2_FOG_R * 31 / 255, FX_ARENA2_FOG_G * 31 / 255, FX_ARENA2_FOG_B * 31 / 255, dither);
            }
        }
    }
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
            u8 index = FxArena2_Quantize(r, g, b, dither);

            sCaptureIndices[y * FX_ARENA2_WIDTH + x] = index;

            if (y == 0 && x == 0) {
                first = index;
            } else if (index != first) {
                varied = TRUE;
            }
        }
    }

    // All one colour means the capture never ran (VRAM C still holds
    // whatever was there, or the frame was blank): fall back instead
    // of showing a flat-colour backdrop.
    sCaptureValid = varied;

    if (sCaptureValid) {
        FxArena2_FillVoid(vram);
    }
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

// ---------------------------------------------------------------------------
// BG3: rewrite the battle's BG3 backdrop with the capture
// ---------------------------------------------------------------------------
// The classic tilemap is identity+1 except screen tile 638, which reuses
// char 543 flipped (the classic art is symmetric there). The capture is
// not, so that entry is repointed at unused char 639 and the tiles are
// written through the (fixed) tilemap, flips applied, so the hardware
// flip lands the right pixel. The palette's winframe/font slots
// (160..191) keep the live buffer's values.

void FxArena2_ApplyToBattleBg(BattleSystem *battleSys)
{
    BgConfig *bgConfig;
    PaletteData *paletteData;
    u16 palette[256];
    u8 *tiles;
    u16 *tilemap;
    const u16 *livePalette;
    int i;

    if (battleSys == NULL || !FxArena2_RealPlaceEnabled() || !sCaptureValid) {
        return;
    }

    if (FxArena2_CaptureBackground() != BattleSystem_GetBackground(battleSys)) {
        return;
    }

    bgConfig = BattleSystem_GetBgConfig(battleSys);
    paletteData = BattleSystem_GetPaletteData(battleSys);

    if (bgConfig == NULL || paletteData == NULL) {
        return;
    }

    for (i = 0; i < 256; i++) {
        palette[i] = FxArena2_PaletteEntry(i);
    }

    livePalette = PaletteData_GetFadedBuffer(paletteData, PLTTBUF_MAIN_BG);

    if (livePalette != NULL) {
        for (i = 160; i < 192; i++) {
            palette[i] = livePalette[i];
        }
    }

    PaletteData_LoadBuffer(paletteData, palette, PLTTBUF_MAIN_BG, 0, sizeof(palette));

    tiles = Heap_Alloc(HEAP_ID_BATTLE, FX_ARENA2_BG3_TILES_BYTES);

    if (tiles == NULL) {
        return;
    }

    memset(tiles, 0, FX_ARENA2_BG3_TILES_BYTES);

    tilemap = (u16 *)Bg_GetTilemapBuffer(bgConfig, BG_LAYER_MAIN_3);

    if (tilemap != NULL) {
        tilemap[638] = 639;
        Bg_CopyTilemapBufferToVRAM(bgConfig, BG_LAYER_MAIN_3);
    }

    for (i = 0; i < FX_ARENA2_BG3_TILES_W * FX_ARENA2_BG3_TILES_H; i++) {
        u16 entry = (tilemap != NULL) ? tilemap[i] : (u16)(i + 1);
        int charIdx = entry & 0x3FF;
        int flipH = (entry >> 10) & 1;
        int flipV = (entry >> 11) & 1;
        int tx = i % FX_ARENA2_BG3_TILES_W;
        int ty = i / FX_ARENA2_BG3_TILES_W;
        int x, y;

        if (charIdx >= FX_ARENA2_BG3_TILES_BYTES / FX_ARENA2_BG3_TILE_BYTES) {
            continue;
        }

        for (y = 0; y < 8; y++) {
            for (x = 0; x < 8; x++) {
                int sx = flipH ? 7 - x : x;
                int sy = flipV ? 7 - y : y;

                tiles[charIdx * FX_ARENA2_BG3_TILE_BYTES + y * 8 + x] = FxArena2_CaptureIndex(tx * 8 + sx, ty * 8 + sy);
            }
        }
    }

    Bg_LoadTilesToVRAM(bgConfig, BG_LAYER_MAIN_3, tiles, FX_ARENA2_BG3_TILES_BYTES, 0);
    Heap_Free(tiles);
}
