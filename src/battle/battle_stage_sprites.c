#include "battle/battle_stage_sprites.h"

#include <nitro.h>
#include <nnsys.h>
#include <string.h>

#include "config/battle_stage.h"
#include "constants/graphics.h"
#include "generated/shadow_sizes.h"

#include "battle/battle_stage.h"
#include "battle/battle_stage_camera.h"
#include "battle/battle_stage_stream.h"
#include "battle/ov16_0223DF00.h"

#include "palette.h"
#include "pokemon_sprite.h"
#include "vram_transfer.h"

// The mesh: GRID x GRID quads, drawn as GRID quad strips
#define GRID          8
#define GRID_VERTICES (GRID + 1)

// Vertices are in 1/256 pixel (fx16 scaled by 16), so a half size up to this many pixels
// fits fx16 with the breathing and the wobble on top; larger sprites draw classic
#define MESH_MAX_HALF_SIZE 120

// Pillow normals: the tilt toward the grid edge at the rim. The sprite material is scaled
// so the vertex least lit at day still saturates (TINT_TARGET), and the smaller the tilt,
// the smaller that scale and the stronger the tint at twilight and night
#define PILLOW_TILT_DEG 12

// Lit colour (0..31, before the clamp at 31) of the least lit vertex at day, with a margin
// for the rounding of the hardware lighting
#define TINT_TARGET 33

// Breathing: period in drawn frames, +-2.5% in y (102 / 4096), half of it in x, a 1 px
// top sway; the battlers start BREATH_STAGGER frames apart
#define BREATH_PERIOD  90
#define BREATH_Y       102
#define BREATH_X       51
#define BREATH_SWAY    256
#define BREATH_STAGGER 22

// Hit wobble: frames, shear at the top row (1/256 px) and oscillation period in frames
#define WOBBLE_FRAMES    12
#define WOBBLE_AMPLITUDE (3 * 256)
#define WOBBLE_PERIOD    6

// Blob shadows
#define BLOB_TEX_WIDTH    32
#define BLOB_TEX_HEIGHT   16
#define BLOB_TEX_BYTES    (BLOB_TEX_WIDTH * BLOB_TEX_HEIGHT) // A5I3, a byte per texel
#define BLOB_PLTT_BYTES   16
#define BLOB_MAX_ALPHA    14
#define BLOB_POLYGON_ID   62
#define BLOB_TEX_VRAM_END 0x20000 // as the arena textures: bank B survives the menus
#define BLOB_GROUND_Y     (FX32_CONST(0.1) + FX32_CONST(0.03)) // just above the platform discs
// NDC depth (fx32) of every blob pixel: the arena squeezes its depth into 4010..4094, where
// the blob and the ground under it get the same depth and the blob loses the depth test, so
// the blob is flattened just in front of the arena, behind the sprites (0..0.625) as the
// classic shadows (0.977)
#define BLOB_DEPTH 4000
#define BLOB_PLAYER_WIDTH 96 // wider than the back sprite (about 60 px), whose body hides the middle
// Blob height on screen, as a fraction of its width (the classic shadows are about 1:4)
#define BLOB_HEIGHT_DIV 4
// Screen rows sampled either side of the blob row to measure the ground per row
#define BLOB_ROW_STEP 4

// Dig's hole in the ground (moves.md, D): a second 32x16 A5I3 texture right after the blob's
// in the same VRAM block (1 KB for both), drawn as the blobs are, at the mon's blob place
#define HOLE_TEX_BYTES      BLOB_TEX_BYTES
#define BLOB_TEX_ALLOC      (BLOB_TEX_BYTES + HOLE_TEX_BYTES)
#define HOLE_MAX_ALPHA      28
#define HOLE_POLYGON_ID     61 // not the blobs': translucent pixels never cover their own ID
#define HOLE_CORE_F         560 // 1 - d^2 (of 1024) inside which the hole is solid
#define HOLE_EARTH_F        360 // ... and inside which it is black rather than earth
#define HOLE_PLTT_EARTH     1 // blob palette colour of the hole's rim
#define HOLE_EARTH_COLOR    GX_RGB(9, 6, 3)
#define HOLE_RAMP_FRAMES    6 // drawn frames to open or shut
#define HOLE_PLAYER_WIDTH   64 // the back sprite no longer hides its middle
#define HOLE_ENEMY_EXTRA    8 // wider than the enemy's blob
#define HOLE_PLAYER_RISE    6 // screen rows up from the player's blob row, clear of the text box

// Screen rows of the blob centres at home, per side (player, enemy): the mons' feet, the
// player's raised above the text box (its feet are at 148, under it). The blobs sit on the
// ground seen at these rows and follow the mons in x.
static const int sBlobRow[2] = { 142, 90 };
// Blob width in pixels of an enemy per shadow size, as the classic shadow sizes
static const int sEnemyBlobWidth[MAX_SHADOW_SIZES] = {
    [SHADOW_SIZE_NONE] = 40,
    [SHADOW_SIZE_SMALL] = 32,
    [SHADOW_SIZE_MEDIUM] = 40,
    [SHADOW_SIZE_LARGE] = 48,
};

typedef struct StageSpriteState {
    u8 phase; // breathing phase, 0..BREATH_PERIOD-1
    u8 delay; // frames before the breathing starts (the per-battler offset)
    u8 wobble; // frames of wobble left
    u8 padding;
} StageSpriteState;

typedef struct StageSprites {
    BattleSystem *battleSys;
    BattleStageSpriteFields *fields;
    BOOL hooked;
    BOOL moveAnimActive;
    // This frame, from BeginFrame
    BOOL visible;
    BOOL wasVisible;
    BOOL advanced; // breathing advanced for a mon this frame
    BOOL streamLive; // the streams play: the arena is drawn, or hidden with its texture VRAM kept
    u32 streamedMask; // battlers drawn from their stream so far this frame
    u32 lastStreamedMask; // and in the frame before
    const BattleStageFileLighting *lighting;
    const MtxFx43 *view;
    StageSpriteState states[MAX_MON_SPRITES];
    // Pillow normals, fx16 in the sprite camera's space (x right, y down, z to the viewer)
    s16 normals[GRID_VERTICES][GRID_VERTICES][3];
    BOOL normalsBuilt;
    // Blob shadows
    BOOL hasBlobs;
    NNSGfdTexKey blobTexKey;
    NNSGfdPlttKey blobPlttKey;
    u32 blobTexAddr;
    u32 blobPlttAddr;
    VecFx32 groundCentre[2]; // ground point seen at screen column 128 on the blob row
    VecFx32 groundRight[2]; // ground vector across 128 pixels on the blob row
    fx32 groundHalfWidth[2]; // its length
    VecFx32 groundDown[2]; // ground vector down one screen row (toward the camera) there
    VecFx32 right; // unit camera-right of the home camera
    fx32 tint[3]; // material scale per channel (R, G, B), from UpdateTint
    BOOL bg2Lifted; // BattleStage_SetBg2Lifted
    // BattleStage_SetGroundHole: per battler, open or not and how far (0..HOLE_RAMP_FRAMES)
    u8 holeOpen[MAX_MON_SPRITES];
    u8 holeLevel[MAX_MON_SPRITES];
} StageSprites;

static u32 DrawHook(PokemonSpriteManager *monSpriteMan, int index, const PokemonSpriteDrawRect *rect);
static void BuildNormals(void);
static void UpdateTint(const BattleStageFileLighting *dayLighting);
static BOOL InitBlobs(const BattleStageSpriteCamera *camera);
static void FreeBlobs(void);

static StageSprites sStageSprites;
static u16 sBlobPalette[BLOB_PLTT_BYTES / 2]; // black
static u8 sBlobTexture[BLOB_TEX_ALLOC]; // the blob, then the hole

void BattleStageSprites_Init(BattleSystem *battleSys, BattleStageSpriteFields *fields, const BattleStageSpriteCamera *camera)
{
    int i;

    sStageSprites.battleSys = battleSys;
    sStageSprites.fields = fields;
    sStageSprites.hooked = FALSE;
    sStageSprites.moveAnimActive = FALSE;
    sStageSprites.visible = FALSE;
    sStageSprites.streamLive = FALSE;
    sStageSprites.streamedMask = 0;
    sStageSprites.lastStreamedMask = 0;
    sStageSprites.wasVisible = FALSE;
    sStageSprites.advanced = FALSE;
    sStageSprites.lighting = NULL;
    sStageSprites.view = NULL;
    sStageSprites.hasBlobs = FALSE;
    sStageSprites.bg2Lifted = FALSE;
    BattleStage_ClearGroundHoles();

    for (i = 0; i < MAX_MON_SPRITES; i++) {
        sStageSprites.states[i].phase = 0;
        sStageSprites.states[i].delay = i * BREATH_STAGGER;
        sStageSprites.states[i].wobble = 0;
    }

    // BattleStage_Init has just cleared sBattleStage, debugFlags included; the critic sets
    // debugFlags again inside each battle
    fields->spriteMeshes = 0;
    fields->idleFrames = 0;
    fields->wobbleMask = 0;
    fields->blobShadows = 0;

    if (!BATTLE_STAGE_3D || camera == NULL) {
        return;
    }

    if (!sStageSprites.normalsBuilt) {
        BuildNormals();
        sStageSprites.normalsBuilt = TRUE;
    }

    sStageSprites.hasBlobs = InitBlobs(camera);
    PokemonSpriteManager_SetDrawHook(BattleSystem_GetPokemonSpriteManager(battleSys), DrawHook);
    sStageSprites.hooked = TRUE;
    BattleStageStream_Init(BattleSystem_GetPokemonSpriteManager(battleSys));
}

void BattleStageSprites_Free(void)
{
    if (sStageSprites.hooked) {
        PokemonSpriteManager_SetDrawHook(BattleSystem_GetPokemonSpriteManager(sStageSprites.battleSys), NULL);
        sStageSprites.hooked = FALSE;
    }

    BattleStageStream_Free();
    FreeBlobs();
    sStageSprites.battleSys = NULL;
    sStageSprites.visible = FALSE;
    sStageSprites.streamLive = FALSE;
    sStageSprites.streamedMask = 0;
    sStageSprites.lastStreamedMask = 0;
    sStageSprites.lighting = NULL;
    sStageSprites.view = NULL;
}

void BattleStageSprites_BeginFrame(BOOL visible, const BattleStageFileLighting *lighting, const BattleStageFileLighting *dayLighting, const MtxFx43 *view)
{
    BattleStageSpriteFields *fields = sStageSprites.fields;
    int i;

    if (fields == NULL) {
        return;
    }

    sStageSprites.visible = visible && sStageSprites.hooked && lighting != NULL && dayLighting != NULL && view != NULL;
    sStageSprites.lighting = lighting;
    sStageSprites.view = view;
    sStageSprites.advanced = FALSE;
    sStageSprites.lastStreamedMask = sStageSprites.streamedMask;
    sStageSprites.streamedMask = 0;

    if (sStageSprites.visible) {
        UpdateTint(dayLighting);
    }

    fields->spriteMeshes = 0;
    fields->blobShadows = 0;
    fields->wobbleMask = 0;

    if (sStageSprites.bg2Lifted) {
        BattleStage_CompatFields()->liftedBg2Frames++;
    }

    for (i = 0; i < MAX_MON_SPRITES; i++) {
        StageSpriteState *state = &sStageSprites.states[i];

        if (fields->debugFlags & BATTLE_STAGE_DEBUG_FREEZE_IDLE) {
            state->wobble = 0;
        } else if (state->wobble > 0) {
            state->wobble--;
        }

        if (state->wobble > 0) {
            fields->wobbleMask |= 1 << i;
        }

        if (sStageSprites.holeOpen[i] && sStageSprites.holeLevel[i] < HOLE_RAMP_FRAMES) {
            sStageSprites.holeLevel[i]++;
        } else if (!sStageSprites.holeOpen[i] && sStageSprites.holeLevel[i] > 0) {
            sStageSprites.holeLevel[i]--;
        }
    }

    // Hidden but with the texture VRAM kept (the debug toggle, a move's backdrop), the streams
    // go on and the sprites draw them flat (DrawFlatStream), so hiding the arena doesn't snap
    // them back to the classic frame
    sStageSprites.streamLive = sStageSprites.visible || (sStageSprites.hooked && BattleStage_KeepsTextureVram());
    BattleStageStream_BeginFrame(sStageSprites.streamLive, (fields->debugFlags & BATTLE_STAGE_DEBUG_FREEZE_IDLE) != 0);

    // Another screen may have used the texture or palette VRAM while the arena was hidden
    if (sStageSprites.hasBlobs && sStageSprites.visible && !sStageSprites.wasVisible) {
        DC_FlushRange(sBlobTexture, sizeof(sBlobTexture));
        DC_FlushRange(sBlobPalette, sizeof(sBlobPalette));
        sStageSprites.wasVisible = VramTransfer_Request(NNS_GFD_DST_3D_TEX_VRAM, sStageSprites.blobTexAddr, sBlobTexture, sizeof(sBlobTexture))
            && VramTransfer_Request(NNS_GFD_DST_3D_TEX_PLTT, sStageSprites.blobPlttAddr, sBlobPalette, sizeof(sBlobPalette));
    } else {
        sStageSprites.wasVisible = sStageSprites.visible;
    }
}

void BattleStage_SetMoveAnimActive(BOOL active)
{
    sStageSprites.moveAnimActive = active;
    BattleStageCamera_SetScriptActive(active);
}

void BattleStage_NotifyHit(int battler)
{
    if (!BATTLE_STAGE_3D || sStageSprites.fields == NULL || battler < 0 || battler >= MAX_MON_SPRITES) {
        return;
    }

    if (sStageSprites.fields->debugFlags & BATTLE_STAGE_DEBUG_FREEZE_IDLE) {
        return;
    }

    // BeginFrame counts it down before the first wobbling frame
    sStageSprites.states[battler].wobble = WOBBLE_FRAMES + 1;
}

BOOL BattleStage_IsSpriteStreamed(int battler)
{
    if (!BATTLE_STAGE_3D || sStageSprites.fields == NULL || !sStageSprites.hooked || battler < 0 || battler >= MAX_MON_SPRITES) {
        return FALSE;
    }

    return ((sStageSprites.streamedMask | sStageSprites.lastStreamedMask) & (1 << battler)) != 0;
}

BOOL BattleStage_GetStreamFrameTiles(int battler, u8 *tiles)
{
    // The tile order of CharacterSprite_LoadPokemonSprite (SUB_REGION_ORDER): x, y, width,
    // height in tiles, each region row by row
    static const u8 regions[][4] = { { 0, 0, 8, 8 }, { 8, 0, 2, 4 }, { 8, 4, 2, 4 }, { 0, 8, 4, 2 }, { 4, 8, 4, 2 }, { 8, 8, 2, 2 } };
    const u8 *frame;
    int i, tx, ty, row, x, y, u, scale;

    if (tiles == NULL || !BattleStage_IsSpriteStreamed(battler)) {
        return FALSE;
    }

    frame = BattleStageStream_GetFrame(battler);

    if (frame == NULL) {
        return FALSE;
    }

    scale = BattleStageStream_GetScale(battler);

    // Both are 4bpp with the left pixel in the low nibble: at 1:1 a tile row is 4 bytes of a
    // texture row; scaled, each pixel comes from the texel under it (MON_STREAM_TEXEL_U/V)
    for (i = 0; i < NELEMS(regions); i++) {
        for (ty = regions[i][1]; ty < regions[i][1] + regions[i][3]; ty++) {
            for (tx = regions[i][0]; tx < regions[i][0] + regions[i][2]; tx++) {
                for (row = 0; row < 8; row++) {
                    y = ty * 8 + row;

                    if (scale == MON_STREAM_SCALE_ONE) {
                        memcpy(tiles, frame + (STREAM_CLASSIC_TOP + y) * (STREAM_CANVAS_WIDTH / 2) + (STREAM_CLASSIC_LEFT + tx * 8) / 2, 4);
                    } else {
                        const u8 *src = frame + MON_STREAM_TEXEL_V(y, scale) * (STREAM_CANVAS_WIDTH / 2);

                        memset(tiles, 0, 4);

                        for (x = 0; x < 8; x++) {
                            u = MON_STREAM_TEXEL_U(tx * 8 + x, scale);
                            tiles[x / 2] |= ((src[u / 2] >> ((u & 1) * 4)) & 0xF) << ((x & 1) * 4);
                        }
                    }

                    tiles += 4;
                }
            }
        }
    }

    return TRUE;
}

void BattleStage_SetGroundHole(int battler, BOOL open)
{
    if (battler < 0 || battler >= MAX_MON_SPRITES) {
        return;
    }

    sStageSprites.holeOpen[battler] = open != FALSE;
}

void BattleStage_ClearGroundHoles(void)
{
    int i;

    for (i = 0; i < MAX_MON_SPRITES; i++) {
        sStageSprites.holeOpen[i] = FALSE;
        sStageSprites.holeLevel[i] = 0;
    }
}

// Blob shadows are drawn (and the classic shadows are not) this frame
static BOOL BlobsOn(void)
{
    return sStageSprites.visible && sStageSprites.hasBlobs && (sStageSprites.fields->debugFlags & (BATTLE_STAGE_DEBUG_NO_BLOB_SHADOWS | BATTLE_STAGE_DEBUG_CLASSIC_SPRITES)) == 0;
}

static void BuildNormals(void)
{
    u16 maxTilt = FX_DEG_TO_IDX(FX32_CONST(PILLOW_TILT_DEG));
    int i, j;

    for (j = 0; j < GRID_VERTICES; j++) {
        for (i = 0; i < GRID_VERTICES; i++) {
            int dx = i - GRID / 2, dy = j - GRID / 2;
            int d2 = dx * dx + dy * dy;
            s16 *n = sStageSprites.normals[j][i];

            if (d2 == 0) {
                n[0] = 0;
                n[1] = 0;
                n[2] = GX_FX16_FX10_MAX;
            } else {
                // The tilt grows with the square of the distance from the centre (in half
                // grids) up to the rim
                int r2 = d2 > (GRID / 2) * (GRID / 2) ? (GRID / 2) * (GRID / 2) : d2;
                u16 tilt = (u16)(maxTilt * r2 / ((GRID / 2) * (GRID / 2)));
                fx32 sinT = FX_SinIdx(tilt);
                fx32 cosT = FX_CosIdx(tilt);
                fx32 len = FX_Sqrt(d2 << FX32_SHIFT);
                fx32 x = FX_Div(sinT * dx, len);
                fx32 y = FX_Div(sinT * dy, len);

                // 1.0 doesn't fit the packed fx10 normal
                n[0] = (s16)MATH_CLAMP(x, -GX_FX16_FX10_MAX, GX_FX16_FX10_MAX);
                n[1] = (s16)MATH_CLAMP(y, -GX_FX16_FX10_MAX, GX_FX16_FX10_MAX);
                n[2] = (s16)MATH_CLAMP(cosT, -GX_FX16_FX10_MAX, GX_FX16_FX10_MAX);
            }
        }
    }
}

static int Channel(GXRgb color, int shift)
{
    return (color >> shift) & 31;
}

// The material scale per channel that makes the least lit pillow vertex saturate at day
// with the neutral sprite material: day stays the unchanged texture everywhere, and
// twilight and night, lit by their own columns with the same scale, tint the mon as they
// differ from day. Without light (emission only) the scale is 1.
static void UpdateTint(const BattleStageFileLighting *dayLighting)
{
    const MtxFx43 *view = sStageSprites.view;
    const fx16 *dir = dayLighting->lightDir;
    fx32 lx, ly, lz, level, minLevel;
    int i, j, c;

    // Light 0 in the sprite camera's space (SetLight: the view with y negated)
    lx = (dir[0] * view->_00 + dir[1] * view->_10 + dir[2] * view->_20) >> FX32_SHIFT;
    ly = -((dir[0] * view->_01 + dir[1] * view->_11 + dir[2] * view->_21) >> FX32_SHIFT);
    lz = (dir[0] * view->_02 + dir[1] * view->_12 + dir[2] * view->_22) >> FX32_SHIFT;

    minLevel = FX32_ONE;

    for (j = 0; j < GRID_VERTICES; j++) {
        for (i = 0; i < GRID_VERTICES; i++) {
            const s16 *n = sStageSprites.normals[j][i];

            level = -((lx * n[0] + ly * n[1] + lz * n[2]) >> FX32_SHIFT);

            if (level < 0) {
                level = 0;
            }

            if (level < minLevel) {
                minLevel = level;
            }
        }
    }

    for (c = 0; c < 3; c++) {
        int lightColor = Channel(dayLighting->lightColor, c * 5);
        int need = TINT_TARGET - Channel(dayLighting->emission, c * 5);
        // 32 * 4096 times the lit colour of the least lit vertex, before the emission
        s64 lit = (s64)lightColor * (Channel(dayLighting->diffuse, c * 5) * minLevel + Channel(dayLighting->ambient, c * 5) * FX32_ONE);
        s64 tint;

        if (need <= 0 || lit <= 0) {
            sStageSprites.tint[c] = FX32_ONE;
            continue;
        }

        tint = (s64)need * 32 * FX32_ONE * FX32_ONE / lit;

        if (tint < FX32_ONE / 4) {
            tint = FX32_ONE / 4;
        } else if (tint > 2 * FX32_ONE) {
            tint = 2 * FX32_ONE;
        }

        sStageSprites.tint[c] = (fx32)tint;
    }
}

// The arena's lighting column combined with the sprite's diffuse and ambient, scaled by
// the day tint (UpdateTint) and rounded up. 16 is the sprite's neutral ambient; its
// diffuse (31 neutral) dims everything, as it dims the unlit classic quad
static void SetMaterial(const PokemonSpriteTransforms *transforms)
{
    const BattleStageFileLighting *lighting = sStageSprites.lighting;
    int spriteDif[3], spriteAmb[3];
    int dif[3], amb[3], emi[3];
    int c;

    spriteDif[0] = transforms->diffuseR;
    spriteDif[1] = transforms->diffuseG;
    spriteDif[2] = transforms->diffuseB;
    spriteAmb[0] = transforms->ambientR;
    spriteAmb[1] = transforms->ambientG;
    spriteAmb[2] = transforms->ambientB;

    for (c = 0; c < 3; c++) {
        fx32 tint = sStageSprites.tint[c];

        dif[c] = (Channel(lighting->diffuse, c * 5) * spriteDif[c] * tint + 31 * FX32_ONE - 1) / (31 * FX32_ONE);
        amb[c] = (Channel(lighting->ambient, c * 5) * spriteAmb[c] * spriteDif[c] * tint + 16 * 31 * FX32_ONE - 1) / (16 * 31 * FX32_ONE);
        emi[c] = Channel(lighting->emission, c * 5) * spriteDif[c] / 31;

        if (dif[c] > 31) {
            dif[c] = 31;
        }

        if (amb[c] > 31) {
            amb[c] = 31;
        }
    }

    G3_MaterialColorDiffAmb(GX_RGB(dif[0], dif[1], dif[2]), GX_RGB(amb[0], amb[1], amb[2]), FALSE);
    G3_MaterialColorSpecEmi(GX_RGB(0, 0, 0), GX_RGB(emi[0], emi[1], emi[2]), FALSE);
}

// Light 0 in the sprite camera's space: the arena's view with y pointing down
static void SetLight(void)
{
    const BattleStageFileLighting *lighting = sStageSprites.lighting;
    MtxFx43 view = *sStageSprites.view;

    view._01 = -view._01;
    view._11 = -view._11;
    view._21 = -view._21;
    view._31 = -view._31;

    G3_LoadMtx43(&view);
    G3_LightVector(GX_LIGHTID_0, lighting->lightDir[0], lighting->lightDir[1], lighting->lightDir[2]);
    G3_LightColor(GX_LIGHTID_0, lighting->lightColor);
}

// Whether the idle breathing of a sprite runs this frame; updates its state and returns
// the sine (fx32) of the phase to draw, 0 at rest
static fx32 Breathe(int index, const PokemonSpriteTransforms *transforms)
{
    StageSpriteState *state = &sStageSprites.states[index];
    fx32 s;

    if ((sStageSprites.fields->debugFlags & BATTLE_STAGE_DEBUG_FREEZE_IDLE)
        || sStageSprites.moveAnimActive
        || transforms->partialDraw
        || (transforms->scaleX != MON_AFFINE_SCALE(1) && transforms->scaleX != -MON_AFFINE_SCALE(1))
        || transforms->scaleY != MON_AFFINE_SCALE(1)
        || transforms->rotationX != 0
        || transforms->rotationY != 0
        || transforms->rotationZ != 0) {
        // Restart from the rest pose, so there is no snap
        state->phase = 0;
        state->delay = index * BREATH_STAGGER;
        return 0;
    }

    if (state->delay > 0) {
        state->delay--;
        return 0;
    }

    s = FX_SinIdx((u16)((u32)state->phase * 0x10000 / BREATH_PERIOD));
    state->phase = (state->phase + 1) % BREATH_PERIOD;

    if (!sStageSprites.advanced) {
        sStageSprites.advanced = TRUE;
        sStageSprites.fields->idleFrames++;
    }

    return s;
}

static void ResetBreath(int index)
{
    sStageSprites.states[index].phase = 0;
    sStageSprites.states[index].delay = index * BREATH_STAGGER;
}

// The camera's similarity of a sprite, p' = now + scale * (p - home), on the current matrix
static void LoadSimilarity(const BattleStageCameraSimilarity *similarity)
{
    G3_Translate(similarity->nowX, similarity->nowY, 0);
    G3_Scale(similarity->scale, similarity->scale, FX32_ONE);
    G3_Translate(-(similarity->homeX << FX32_SHIFT), -(similarity->homeY << FX32_SHIFT), 0);
}

// The classic quad's matrix (the manager's pivot rotation) with the similarity under it
static void LoadClassicMatrix(const PokemonSpriteTransforms *transforms, const BattleStageCameraSimilarity *similarity)
{
    NNS_G3dGeFlushBuffer();
    G3_Identity();
    LoadSimilarity(similarity);
    G3_Translate((transforms->xCenter + transforms->xPivot) << FX32_SHIFT, (transforms->yCenter + transforms->yPivot) << FX32_SHIFT, transforms->zCenter << FX32_SHIFT);
    G3_RotX(FX_SinIdx(transforms->rotationX), FX_CosIdx(transforms->rotationX));
    G3_RotY(FX_SinIdx(transforms->rotationY), FX_CosIdx(transforms->rotationY));
    G3_RotZ(FX_SinIdx(transforms->rotationZ), FX_CosIdx(transforms->rotationZ));
    G3_Translate(-((transforms->xCenter + transforms->xPivot) << FX32_SHIFT), -((transforms->yCenter + transforms->yPivot) << FX32_SHIFT), -(transforms->zCenter << FX32_SHIFT));
}

// The arena hidden: the battler's stream frame as the classic quad would draw it, flat and
// unlit with the state the manager set, the 128x96 canvas about the classic 80x80 frame's
// centre as on the mesh. A partial draw takes the same part of the 80x80 window. FALSE when
// the battler has no stream frame (then the classic quad draws)
static BOOL DrawFlatStream(PokemonSpriteManager *monSpriteMan, int index, const PokemonSpriteDrawRect *rect)
{
    const PokemonSpriteTransforms *transforms = &monSpriteMan->sprites[index].transforms;
    BattleStageStreamRect canvas;

    if (!sStageSprites.streamLive
        || monSpriteMan->excludeIdentity == TRUE
        || (sStageSprites.fields->debugFlags & BATTLE_STAGE_DEBUG_NO_SPRITE_STREAM)
        || !BattleStageStream_Bind(index)) {
        return FALSE;
    }

    BattleStageStream_CanvasRect(index, transforms, rect, &canvas);
    NNS_G2dDrawSpriteFast(canvas.x, canvas.y, rect->z, canvas.width, canvas.height, canvas.u0, canvas.v0, canvas.u1, canvas.v1);
    BattleStageStream_Unbind();
    sStageSprites.streamedMask |= 1 << index;
    return TRUE;
}

static u32 DrawHook(PokemonSpriteManager *monSpriteMan, int index, const PokemonSpriteDrawRect *rect)
{
    PokemonSprite *sprite;
    const PokemonSpriteTransforms *transforms;
    BattleStageCameraSimilarity similarity;
    BOOL follow;
    u32 result;
    int width, height;
    fx32 breath, wobble;
    int sy, sx, sway, bottom;
    int column[GRID_VERTICES]; // x of each column, 1/256 px
    int row[GRID_VERTICES]; // y of each row
    int rowShift[GRID_VERTICES]; // sway + wobble of each row
    fx32 texS[GRID_VERTICES], texT[GRID_VERTICES];
    int u0, v0, u1, v1;
    fx32 centreX, centreY; // of the quad, in px
    BOOL streamed;
    int flipX, flipY;
    int i, j;

    if (index < 0 || index >= MAX_MON_SPRITES) {
        return 0;
    }

    // Off home the sprite follows the camera, whichever way it is drawn; at home the camera
    // gives no similarity and nothing here touches the matrix
    follow = sStageSprites.visible
        && BattleStage_IsVisible()
        && monSpriteMan->excludeIdentity != TRUE
        && BattleStageCamera_GetSimilarity(index, &similarity);

    // Called again for the classic shadow (MON_SPRITE_DRAW_HOOK_SHADOW_MATRIX), after its G3_Identity
    if (rect == NULL) {
        if (follow) {
            NNS_G3dGeFlushBuffer();
            LoadSimilarity(&similarity);
        }

        return 0;
    }

    result = BlobsOn() ? MON_SPRITE_DRAW_HOOK_NO_SHADOW : 0;
    sprite = &monSpriteMan->sprites[index];
    transforms = &sprite->transforms;

    if (!sStageSprites.visible || !BattleStage_IsVisible() || (sStageSprites.fields->debugFlags & BATTLE_STAGE_DEBUG_CLASSIC_SPRITES)) {
        ResetBreath(index);

        if (follow) {
            LoadClassicMatrix(transforms, &similarity);
            result |= MON_SPRITE_DRAW_HOOK_SHADOW_MATRIX;
        }

        if ((sStageSprites.fields->debugFlags & BATTLE_STAGE_DEBUG_CLASSIC_SPRITES) == 0 && DrawFlatStream(monSpriteMan, index, rect)) {
            result |= MON_SPRITE_DRAW_HOOK_DREW;
        }

        return result;
    }

    width = rect->width;
    height = rect->height;
    u0 = rect->u0;
    v0 = rect->v0;
    u1 = rect->u1;
    v1 = rect->v1;
    centreX = rect->x * FX32_ONE + rect->width * (FX32_ONE / 2);
    centreY = rect->y * FX32_ONE + rect->height * (FX32_ONE / 2);
    streamed = FALSE;

    // A streamed frame is the 80x80 frame with 24 more pixels on the sides and 8 above and
    // below, about the same centre; a partial draw keeps its cuts in the 80x80 window
    // (BattleStageStream_CanvasRect)
    if (monSpriteMan->excludeIdentity != TRUE
        && (sStageSprites.fields->debugFlags & BATTLE_STAGE_DEBUG_NO_SPRITE_STREAM) == 0
        && BattleStageStream_Bind(index)) {
        BattleStageStreamRect canvas;

        streamed = TRUE;
        BattleStageStream_CanvasRect(index, transforms, rect, &canvas);
        width = canvas.width;
        height = canvas.height;
        centreX = canvas.centreX;
        centreY = canvas.centreY;
        u0 = canvas.u0;
        v0 = canvas.v0;
        u1 = canvas.u1;
        v1 = canvas.v1;
    }

    if (monSpriteMan->excludeIdentity == TRUE
        || width == 0
        || height == 0
        || width > 2 * MESH_MAX_HALF_SIZE
        || width < -2 * MESH_MAX_HALF_SIZE
        || height > 2 * MESH_MAX_HALF_SIZE
        || height < -2 * MESH_MAX_HALF_SIZE) {
        ResetBreath(index);

        if (streamed) {
            BattleStageStream_Unbind();
        }

        if (follow) {
            LoadClassicMatrix(transforms, &similarity);
            result |= MON_SPRITE_DRAW_HOOK_SHADOW_MATRIX;
        }

        return result;
    }

    breath = Breathe(index, transforms);
    wobble = 0;

    if (sStageSprites.states[index].wobble > 0) {
        int t = WOBBLE_FRAMES - sStageSprites.states[index].wobble;

        // Decaying: WOBBLE_AMPLITUDE * sin(2 pi t / period) * (1 - t / frames), in 1/256 px
        wobble = WOBBLE_AMPLITUDE * FX_SinIdx((u16)((u32)t * 0x10000 / WOBBLE_PERIOD)) / FX32_ONE * (WOBBLE_FRAMES - t) / WOBBLE_FRAMES;
    }

    // Squash and stretch anchored at the bottom row (the feet), in fx32 scale factors
    sy = FX32_ONE + breath * BREATH_Y / FX32_ONE;
    sx = FX32_ONE - breath * BREATH_X / FX32_ONE;
    sway = BREATH_SWAY * breath / FX32_ONE;
    bottom = height * 128;

    for (i = 0; i < GRID_VERTICES; i++) {
        int x = i * width * 32 - width * 128;
        int y = i * height * 32 - height * 128;
        int fromBottom = GRID - i;

        column[i] = breath != 0 ? x * sx / FX32_ONE : x;
        row[i] = breath != 0 ? bottom - (bottom - y) * sy / FX32_ONE : y;
        rowShift[i] = sway * fromBottom / GRID + wobble * fromBottom * fromBottom / (GRID * GRID);
        texS[i] = u0 * FX32_ONE + (u1 - u0) * i * (FX32_ONE / GRID);
        texT[i] = v0 * FX32_ONE + (v1 - v0) * i * (FX32_ONE / GRID);
    }

    // The pillow bulges toward the screen edge the vertex is on, also when flipped
    flipX = width < 0 ? -1 : 1;
    flipY = height < 0 ? -1 : 1;

    NNS_G3dGeFlushBuffer();

    G3_MtxMode(GX_MTXMODE_POSITION_VECTOR);
    G3_PushMtx();
    SetLight();

    // The camera's similarity first, so whatever the script did to the sprite rides along;
    // then the sprite's pivot rotation, now on the vector matrix too so the normals follow it
    G3_Identity();

    if (follow) {
        LoadSimilarity(&similarity);
        result |= MON_SPRITE_DRAW_HOOK_SHADOW_MATRIX;
    }

    G3_Translate((transforms->xCenter + transforms->xPivot) << FX32_SHIFT, (transforms->yCenter + transforms->yPivot) << FX32_SHIFT, transforms->zCenter << FX32_SHIFT);
    G3_RotX(FX_SinIdx(transforms->rotationX), FX_CosIdx(transforms->rotationX));
    G3_RotY(FX_SinIdx(transforms->rotationY), FX_CosIdx(transforms->rotationY));
    G3_RotZ(FX_SinIdx(transforms->rotationZ), FX_CosIdx(transforms->rotationZ));
    G3_Translate(-((transforms->xCenter + transforms->xPivot) << FX32_SHIFT), -((transforms->yCenter + transforms->yPivot) << FX32_SHIFT), -(transforms->zCenter << FX32_SHIFT));

    // Rect centre; 1 vertex unit (fx16) = 1/256 px. The scale only goes to the position
    // matrix, so the normals stay unit length
    G3_Translate(centreX, centreY, rect->z * FX32_ONE);
    G3_Scale(16 * FX32_ONE, 16 * FX32_ONE, FX32_ONE);

    SetMaterial(transforms);
    G3_PolygonAttr(GX_LIGHTMASK_0, GX_POLYGONMODE_MODULATE, GX_CULL_NONE, sprite->polygonID, transforms->alpha, 0);

    for (j = 0; j < GRID; j++) {
        G3_Begin(GX_BEGIN_QUAD_STRIP);

        for (i = 0; i < GRID_VERTICES; i++) {
            const s16 *n;

            n = sStageSprites.normals[j][i];
            G3_TexCoord(texS[i], texT[j]);
            G3_Direct1(G3OP_NORMAL, GX_PACK_NORMAL_PARAM(n[0] * flipX, n[1] * flipY, n[2]));
            G3_Vtx((fx16)(column[i] + rowShift[j]), (fx16)row[j], 0);

            n = sStageSprites.normals[j + 1][i];
            G3_TexCoord(texS[i], texT[j + 1]);
            G3_Direct1(G3OP_NORMAL, GX_PACK_NORMAL_PARAM(n[0] * flipX, n[1] * flipY, n[2]));
            G3_Vtx((fx16)(column[i] + rowShift[j + 1]), (fx16)row[j + 1], 0);
        }

        G3_End();
    }

    G3_PopMtx(1);
    G3_MtxMode(GX_MTXMODE_POSITION);

    // Back to the classic quad's state, for the shadow and the next sprite
    G3_MaterialColorDiffAmb(GX_RGB(transforms->diffuseR, transforms->diffuseG, transforms->diffuseB), GX_RGB(transforms->ambientR, transforms->ambientG, transforms->ambientB), TRUE);
    G3_MaterialColorSpecEmi(GX_RGB(16, 16, 16), GX_RGB(0, 0, 0), FALSE);
    G3_PolygonAttr(GX_LIGHTMASK_NONE, GX_POLYGONMODE_MODULATE, GX_CULL_NONE, sprite->polygonID, transforms->alpha, 0);

    if (streamed) {
        BattleStageStream_Unbind();
        sStageSprites.streamedMask |= 1 << index;
    }

    sStageSprites.fields->spriteMeshes++;
    return result | MON_SPRITE_DRAW_HOOK_DREW;
}

static void BuildBlobTexture(void)
{
    int u, v;

    // A soft disc in the normalised texture: alpha = max * (1 - d^2), palette index 0
    for (v = 0; v < BLOB_TEX_HEIGHT; v++) {
        for (u = 0; u < BLOB_TEX_WIDTH; u++) {
            int du = 2 * u - (BLOB_TEX_WIDTH - 1);
            int dv = 2 * (2 * v - (BLOB_TEX_HEIGHT - 1));
            int f = 1024 - (du * du + dv * dv);
            int alpha = f > 0 ? BLOB_MAX_ALPHA * f / 1024 : 0;

            sBlobTexture[v * BLOB_TEX_WIDTH + u] = (u8)(alpha << 3);
        }
    }

    // The hole: solid black inside, a ring of dark earth, then a soft edge
    for (v = 0; v < BLOB_TEX_HEIGHT; v++) {
        for (u = 0; u < BLOB_TEX_WIDTH; u++) {
            int du = 2 * u - (BLOB_TEX_WIDTH - 1);
            int dv = 2 * (2 * v - (BLOB_TEX_HEIGHT - 1));
            int f = 1024 - (du * du + dv * dv);
            int alpha = f >= HOLE_CORE_F ? HOLE_MAX_ALPHA : (f > 0 ? HOLE_MAX_ALPHA * f / HOLE_CORE_F : 0);
            int index = f >= HOLE_EARTH_F ? 0 : HOLE_PLTT_EARTH;

            sBlobTexture[BLOB_TEX_BYTES + v * BLOB_TEX_WIDTH + u] = (u8)((alpha << 3) | index);
        }
    }
}

// Where the home camera sees a screen row (column 128) on the ground; FALSE above the horizon
static BOOL GroundAtRow(const BattleStageSpriteCamera *camera, const VecFx32 *back, const VecFx32 *camUp, fx32 tanY, int row, VecFx32 *point, fx32 *dist)
{
    fx32 ndcY = (96 - row) * FX32_ONE / 96;
    fx32 lift = FX_Mul(ndcY, tanY);
    VecFx32 dir;

    dir.x = -back->x + FX_Mul(camUp->x, lift);
    dir.y = -back->y + FX_Mul(camUp->y, lift);
    dir.z = -back->z + FX_Mul(camUp->z, lift);

    if (dir.y >= 0) {
        return FALSE;
    }

    *dist = FX_Div(BLOB_GROUND_Y - camera->camPos.y, dir.y);
    point->x = camera->camPos.x + FX_Mul(dir.x, *dist);
    point->y = BLOB_GROUND_Y;
    point->z = camera->camPos.z + FX_Mul(dir.z, *dist);
    return TRUE;
}

// Where the home camera sees the blob row of each side on the ground
static void BuildGroundMapping(const BattleStageSpriteCamera *camera)
{
    VecFx32 up = { 0, FX32_ONE, 0 };
    VecFx32 back, camUp, above, below;
    fx32 tanY, tanX, t, tAbove, tBelow;
    int side;

    VEC_Subtract(&camera->camPos, &camera->camTarget, &back);
    VEC_Normalize(&back, &back);
    VEC_CrossProduct(&up, &back, &sStageSprites.right);
    VEC_Normalize(&sStageSprites.right, &sStageSprites.right);
    VEC_CrossProduct(&back, &sStageSprites.right, &camUp);

    tanY = FX_Div(camera->fovySin, camera->fovyCos);
    tanX = tanY * 4 / 3;

    for (side = 0; side < 2; side++) {
        // A row above the horizon never meets the ground; leave the blobs off
        if (!GroundAtRow(camera, &back, &camUp, tanY, sBlobRow[side], &sStageSprites.groundCentre[side], &t)
            || !GroundAtRow(camera, &back, &camUp, tanY, sBlobRow[side] - BLOB_ROW_STEP, &above, &tAbove)
            || !GroundAtRow(camera, &back, &camUp, tanY, sBlobRow[side] + BLOB_ROW_STEP, &below, &tBelow)) {
            sStageSprites.groundHalfWidth[0] = 0;
            return;
        }

        sStageSprites.groundHalfWidth[side] = FX_Mul(t, tanX);
        sStageSprites.groundRight[side].x = FX_Mul(sStageSprites.right.x, sStageSprites.groundHalfWidth[side]);
        sStageSprites.groundRight[side].y = FX_Mul(sStageSprites.right.y, sStageSprites.groundHalfWidth[side]);
        sStageSprites.groundRight[side].z = FX_Mul(sStageSprites.right.z, sStageSprites.groundHalfWidth[side]);
        sStageSprites.groundDown[side].x = (below.x - above.x) / (2 * BLOB_ROW_STEP);
        sStageSprites.groundDown[side].y = 0;
        sStageSprites.groundDown[side].z = (below.z - above.z) / (2 * BLOB_ROW_STEP);
    }
}

int BattleStageSprites_BlobRow(int side)
{
    return sBlobRow[side & 1];
}

BOOL BattleStageSprites_GroundPoint(int side, int px, VecFx32 *point)
{
    side &= 1;

    if (!sStageSprites.hooked || sStageSprites.groundHalfWidth[0] <= 0 || sStageSprites.groundHalfWidth[1] <= 0) {
        return FALSE;
    }

    px -= 128;
    point->x = sStageSprites.groundCentre[side].x + sStageSprites.groundRight[side].x * px / 128;
    point->y = sStageSprites.groundCentre[side].y + sStageSprites.groundRight[side].y * px / 128;
    point->z = sStageSprites.groundCentre[side].z + sStageSprites.groundRight[side].z * px / 128;
    return TRUE;
}

BOOL BattleStageSprites_CutHomeY(int battler, int *y)
{
    PokemonSpriteManager *monSpriteMan;
    PokemonSprite *sprite;
    const PokemonSpriteTransforms *transforms;
    int height;

    if (!sStageSprites.hooked || battler < 0 || battler >= MAX_MON_SPRITES) {
        return FALSE;
    }

    monSpriteMan = BattleSystem_GetPokemonSpriteManager(sStageSprites.battleSys);
    sprite = &monSpriteMan->sprites[battler];

    if (monSpriteMan->excludeIdentity == TRUE || !PokemonSprite_IsCut(sprite)) {
        return FALSE;
    }

    // The same rect DrawSprites hands the draw hook; the pivot rotation is left out
    transforms = &sprite->transforms;

    if (transforms->partialDraw) {
        if (transforms->drawYOffset + transforms->drawHeight < MON_SPRITE_FRAME_HEIGHT) {
            return FALSE;
        }

        *y = transforms->yCenter - MON_SPRITE_FRAME_HEIGHT / 2 + transforms->drawYOffset + transforms->yOffset - sprite->shadow.height + transforms->drawHeight;
        return TRUE;
    }

    height = (MON_SPRITE_FRAME_HEIGHT * transforms->scaleY) >> MON_AFFINE_SHIFT;

    if (height <= 0) {
        return FALSE;
    }

    *y = transforms->yCenter - height / 2 + transforms->yOffset - sprite->shadow.height + height;
    return TRUE;
}

static BOOL InitBlobs(const BattleStageSpriteCamera *camera)
{
    sStageSprites.groundHalfWidth[0] = 0;
    sStageSprites.groundHalfWidth[1] = 0;
    BuildGroundMapping(camera);

    if (sStageSprites.groundHalfWidth[0] <= 0 || sStageSprites.groundHalfWidth[1] <= 0) {
        return FALSE;
    }

    sStageSprites.blobTexKey = NNS_GfdAllocTexVram(BLOB_TEX_ALLOC, FALSE, 0);

    if (sStageSprites.blobTexKey == NNS_GFD_ALLOC_ERROR_TEXKEY) {
        return FALSE;
    }

    sStageSprites.blobTexAddr = NNS_GfdGetTexKeyAddr(sStageSprites.blobTexKey);

    if (sStageSprites.blobTexAddr + BLOB_TEX_ALLOC > BLOB_TEX_VRAM_END) {
        NNS_GfdFreeTexVram(sStageSprites.blobTexKey);
        return FALSE;
    }

    sStageSprites.blobPlttKey = NNS_GfdAllocPlttVram(BLOB_PLTT_BYTES, FALSE, 0);

    if (sStageSprites.blobPlttKey == NNS_GFD_ALLOC_ERROR_PLTTKEY) {
        NNS_GfdFreeTexVram(sStageSprites.blobTexKey);
        return FALSE;
    }

    sStageSprites.blobPlttAddr = NNS_GfdGetPlttKeyAddr(sStageSprites.blobPlttKey);

    BuildBlobTexture();
    memset(sBlobPalette, 0, sizeof(sBlobPalette));
    sBlobPalette[HOLE_PLTT_EARTH] = HOLE_EARTH_COLOR;
    DC_FlushRange(sBlobTexture, sizeof(sBlobTexture));
    DC_FlushRange(sBlobPalette, sizeof(sBlobPalette));

    GX_BeginLoadTex();
    GX_LoadTex(sBlobTexture, sStageSprites.blobTexAddr, BLOB_TEX_ALLOC);
    GX_EndLoadTex();

    GX_BeginLoadTexPltt();
    GX_LoadTexPltt(sBlobPalette, sStageSprites.blobPlttAddr, BLOB_PLTT_BYTES);
    GX_EndLoadTexPltt();

    return TRUE;
}

static void FreeBlobs(void)
{
    if (sStageSprites.hasBlobs) {
        NNS_GfdFreePlttVram(sStageSprites.blobPlttKey);
        NNS_GfdFreeTexVram(sStageSprites.blobTexKey);
        sStageSprites.hasBlobs = FALSE;
    }
}

// Dig's holes are drawn this frame, wherever they are open: they don't depend on the blob
// shadows being on, only on their texture being there
static BOOL HolesOn(void)
{
    return sStageSprites.visible && sStageSprites.hasBlobs && (sStageSprites.fields->debugFlags & BATTLE_STAGE_DEBUG_CLASSIC_SPRITES) == 0;
}

// The arena's projection with z' = BLOB_DEPTH * w (the projection stack has a single entry,
// which DrawArena uses)
static void LoadFlatProjection(const MtxFx44 *projection)
{
    MtxFx44 flat = *projection;

    flat._02 = FX_Mul(BLOB_DEPTH, flat._03);
    flat._12 = FX_Mul(BLOB_DEPTH, flat._13);
    flat._22 = FX_Mul(BLOB_DEPTH, flat._23);
    flat._32 = FX_Mul(BLOB_DEPTH, flat._33);
    G3_MtxMode(GX_MTXMODE_PROJECTION);
    G3_LoadMtx44(&flat);
    G3_MtxMode(GX_MTXMODE_POSITION_VECTOR);
}

// A textured quad on the ground around centre: a across (half), b down the screen (half)
static void DrawGroundQuad(const VecFx32 *centre, const VecFx32 *a, const VecFx32 *b)
{
    G3_PushMtx();
    G3_Translate(centre->x, centre->y, centre->z);
    G3_Begin(GX_BEGIN_QUADS);
    G3_TexCoord(0, 0);
    G3_Vtx((fx16)(-a->x - b->x), (fx16)(-a->y - b->y), (fx16)(-a->z - b->z));
    G3_TexCoord(BLOB_TEX_WIDTH * FX32_ONE, 0);
    G3_Vtx((fx16)(a->x - b->x), (fx16)(a->y - b->y), (fx16)(a->z - b->z));
    G3_TexCoord(BLOB_TEX_WIDTH * FX32_ONE, BLOB_TEX_HEIGHT * FX32_ONE);
    G3_Vtx((fx16)(a->x + b->x), (fx16)(a->y + b->y), (fx16)(a->z + b->z));
    G3_TexCoord(0, BLOB_TEX_HEIGHT * FX32_ONE);
    G3_Vtx((fx16)(-a->x + b->x), (fx16)(-a->y + b->y), (fx16)(-a->z + b->z));
    G3_End();
    G3_PopMtx(1);
}

// The ground quad of a mon's blob place, widthPx wide on screen at scale 1
static void GroundQuadAxes(int battler, int widthPx, int scale, VecFx32 *centre, VecFx32 *a, VecFx32 *b, fx32 *radius)
{
    const PokemonSprite *sprite = &BattleSystem_GetPokemonSpriteManager(sStageSprites.battleSys)->sprites[battler];
    const PokemonSpriteTransforms *transforms = &sprite->transforms;
    int side = BattleSystem_BattlerSlot(sStageSprites.battleSys, battler) & 1;
    int px, rows;

    // Half the width, as a fraction of the 128 pixels groundHalfWidth covers
    *radius = sStageSprites.groundHalfWidth[side] * widthPx / 2 / 128 * scale / MON_AFFINE_SCALE(1);

    px = transforms->xCenter + transforms->xOffset + sprite->shadow.xOffset - 128;
    centre->x = sStageSprites.groundCentre[side].x + sStageSprites.groundRight[side].x * px / 128;
    centre->y = sStageSprites.groundCentre[side].y + sStageSprites.groundRight[side].y * px / 128;
    centre->z = sStageSprites.groundCentre[side].z + sStageSprites.groundRight[side].z * px / 128;
    a->x = FX_Mul(sStageSprites.right.x, *radius);
    a->y = FX_Mul(sStageSprites.right.y, *radius);
    a->z = FX_Mul(sStageSprites.right.z, *radius);
    // Half the height on screen, in rows, times the ground per row
    rows = widthPx * scale / MON_AFFINE_SCALE(1) / (2 * BLOB_HEIGHT_DIV);
    b->x = sStageSprites.groundDown[side].x * rows;
    b->y = 0;
    b->z = sStageSprites.groundDown[side].z * rows;
}

void BattleStageSprites_DrawBlobs(const MtxFx44 *projection)
{
    PokemonSpriteManager *monSpriteMan;
    int numBattlers, i;
    BOOL started = FALSE;
    BOOL blobsOn = BlobsOn();
    BOOL holesOn = HolesOn();

    if (!blobsOn && !holesOn) {
        return;
    }

    monSpriteMan = BattleSystem_GetPokemonSpriteManager(sStageSprites.battleSys);
    numBattlers = BattleSystem_MaxBattlers(sStageSprites.battleSys);

    if (numBattlers > MAX_MON_SPRITES) {
        numBattlers = MAX_MON_SPRITES;
    }

    for (i = 0; i < numBattlers && blobsOn; i++) {
        const PokemonSprite *sprite = &monSpriteMan->sprites[i];
        const PokemonSpriteTransforms *transforms = &sprite->transforms;
        int side, widthPx, scale;
        fx32 radius;
        VecFx32 centre, a, b;

        // hideShadows is never initialised (PokemonSpriteManager_New leaves it as the heap
        // had it), so it only means something while a script runs: the battle sets it before
        // a move whose shadow hides and clears it after
        if (!sprite->active || transforms->hide || transforms->hide2 || transforms->partialDraw || (sStageSprites.moveAnimActive && (monSpriteMan->hideShadows & 1))) {
            continue;
        }

        side = BattleSystem_BattlerSlot(sStageSprites.battleSys, i) & 1;
        widthPx = side ? sEnemyBlobWidth[sprite->shadow.size] : BLOB_PLAYER_WIDTH;
        scale = transforms->scaleX < 0 ? -transforms->scaleX : transforms->scaleX;

        if (scale > MON_AFFINE_SCALE(1)) {
            scale = MON_AFFINE_SCALE(1);
        }

        GroundQuadAxes(i, widthPx, scale, &centre, &a, &b, &radius);

        if (radius <= 0) {
            continue;
        }

        if (!started) {
            LoadFlatProjection(projection);

            // Texcoords used as is (no texture matrix), no light, no fog; translucent
            // (A5I3), so it doesn't write depth and blends over the ground
            G3_TexImageParam(GX_TEXFMT_A5I3, GX_TEXGEN_NONE, GX_TEXSIZE_S32, GX_TEXSIZE_T16, GX_TEXREPEAT_NONE, GX_TEXFLIP_NONE, GX_TEXPLTTCOLOR0_USE, sStageSprites.blobTexAddr);
            G3_TexPlttBase(sStageSprites.blobPlttAddr, GX_TEXFMT_A5I3);
            G3_PolygonAttr(GX_LIGHTMASK_NONE, GX_POLYGONMODE_MODULATE, GX_CULL_NONE, BLOB_POLYGON_ID, 31, 0);
            G3_Color(GX_RGB(31, 31, 31));
            started = TRUE;
        }

        DrawGroundQuad(&centre, &a, &b);
        sStageSprites.fields->blobShadows++;
    }

    // Dig's holes (moves.md, D), after the blobs: at the blob place of the mon, which is
    // clipped or hidden meanwhile, at its full width; the polygon alpha opens and shuts them
    for (i = 0; i < numBattlers && holesOn; i++) {
        const PokemonSprite *sprite = &monSpriteMan->sprites[i];
        int level = sStageSprites.holeLevel[i];
        int side, widthPx;
        fx32 radius;
        VecFx32 centre, a, b;

        if (level == 0 || !sprite->active) {
            continue;
        }

        side = BattleSystem_BattlerSlot(sStageSprites.battleSys, i) & 1;
        widthPx = side ? sEnemyBlobWidth[sprite->shadow.size] + HOLE_ENEMY_EXTRA : HOLE_PLAYER_WIDTH;
        GroundQuadAxes(i, widthPx, MON_AFFINE_SCALE(1), &centre, &a, &b, &radius);

        if (radius <= 0) {
            continue;
        }

        if (side == 0) {
            centre.x -= sStageSprites.groundDown[0].x * HOLE_PLAYER_RISE;
            centre.z -= sStageSprites.groundDown[0].z * HOLE_PLAYER_RISE;
        }

        if (!started) {
            LoadFlatProjection(projection);
            started = TRUE;
        }

        G3_TexImageParam(GX_TEXFMT_A5I3, GX_TEXGEN_NONE, GX_TEXSIZE_S32, GX_TEXSIZE_T16, GX_TEXREPEAT_NONE, GX_TEXFLIP_NONE, GX_TEXPLTTCOLOR0_USE, sStageSprites.blobTexAddr + BLOB_TEX_BYTES);
        G3_TexPlttBase(sStageSprites.blobPlttAddr, GX_TEXFMT_A5I3);
        G3_PolygonAttr(GX_LIGHTMASK_NONE, GX_POLYGONMODE_MODULATE, GX_CULL_NONE, HOLE_POLYGON_ID, 31 * level / HOLE_RAMP_FRAMES, 0);
        G3_Color(GX_RGB(31, 31, 31));
        DrawGroundQuad(&centre, &a, &b);
    }

    if (started) {
        G3_MtxMode(GX_MTXMODE_PROJECTION);
        G3_LoadMtx44(projection);
        G3_MtxMode(GX_MTXMODE_POSITION_VECTOR);
    }
}

// The factor (1/256 per channel) that the lit mesh applies to a camera-facing texel with the
// neutral sprite material (diffuse 31, ambient 16): SetMaterial and the hardware lighting,
// clamped to 31, over 31. 256 at day, where the mesh saturates (compat.md, F2)
BOOL BattleStage_GetSpriteTint(u16 *tintR, u16 *tintG, u16 *tintB)
{
    const BattleStageFileLighting *lighting = sStageSprites.lighting;
    const MtxFx43 *view = sStageSprites.view;
    const fx16 *dir;
    u16 factor[3];
    fx32 level;
    int c;

    if (!BATTLE_STAGE_3D || sStageSprites.fields == NULL || !sStageSprites.visible || lighting == NULL || view == NULL) {
        return FALSE;
    }

    if (!BattleStage_IsVisible() || (sStageSprites.fields->debugFlags & BATTLE_STAGE_DEBUG_CLASSIC_SPRITES)) {
        return FALSE;
    }

    // The camera-facing normal is +z in the sprite camera's space (the y flip of SetLight
    // leaves z alone)
    dir = lighting->lightDir;
    level = -((dir[0] * view->_02 + dir[1] * view->_12 + dir[2] * view->_22) >> FX32_SHIFT);

    if (level < 0) {
        level = 0;
    } else if (level > FX32_ONE) {
        level = FX32_ONE;
    }

    for (c = 0; c < 3; c++) {
        fx32 tint = sStageSprites.tint[c];
        int lightColor = Channel(lighting->lightColor, c * 5);
        int dif = (Channel(lighting->diffuse, c * 5) * tint + FX32_ONE - 1) / FX32_ONE;
        int amb = (Channel(lighting->ambient, c * 5) * tint + FX32_ONE - 1) / FX32_ONE;
        int lit;

        if (dif > 31) {
            dif = 31;
        }

        if (amb > 31) {
            amb = 31;
        }

        lit = Channel(lighting->emission, c * 5) + (int)(((s64)lightColor * ((s64)dif * level + (s64)amb * FX32_ONE)) / (32 * FX32_ONE));

        if (lit >= 31) {
            factor[c] = 256;
        } else {
            factor[c] = (u16)((lit * 256 + 15) / 31);
        }
    }

    if (factor[0] == 256 && factor[1] == 256 && factor[2] == 256) {
        return FALSE;
    }

    *tintR = factor[0];
    *tintG = factor[1];
    *tintB = factor[2];

    return TRUE;
}

BOOL BattleStage_TintCopyPalette(PaletteData *paletteData, enum PaletteBufferID bufferID, u16 start, u16 count)
{
    u16 tint[3];
    int k;

    if (!BattleStage_GetSpriteTint(&tint[0], &tint[1], &tint[2])) {
        return FALSE;
    }

    for (k = 0; k < 2; k++) {
        u16 *colors = (k == 0) ? PaletteData_GetUnfadedBuffer(paletteData, bufferID) : PaletteData_GetFadedBuffer(paletteData, bufferID);
        u16 i;

        if (colors == NULL) {
            continue;
        }

        for (i = start; i < start + count; i++) {
            u16 color = colors[i];
            int r = ((color & 31) * tint[0] + 128) >> 8;
            int g = (((color >> 5) & 31) * tint[1] + 128) >> 8;
            int b = (((color >> 10) & 31) * tint[2] + 128) >> 8;

            colors[i] = (u16)((color & 0x8000) | GX_RGB(r > 31 ? 31 : r, g > 31 ? 31 : g, b > 31 ? 31 : b));
        }
    }

    BattleStage_CompatFields()->tintedCopies++;

    return TRUE;
}

void BattleStage_SetBg2Lifted(BOOL lifted)
{
    sStageSprites.bg2Lifted = lifted;
}
