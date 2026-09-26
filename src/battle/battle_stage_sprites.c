#include "battle/battle_stage_sprites.h"

#include <nitro.h>
#include <nnsys.h>
#include <string.h>

#include "config/battle_stage.h"
#include "generated/shadow_sizes.h"

#include "battle/battle_stage.h"
#include "battle/battle_stage_camera.h"
#include "battle/ov16_0223DF00.h"

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
} StageSprites;

static u32 DrawHook(PokemonSpriteManager *monSpriteMan, int index, const PokemonSpriteDrawRect *rect);
static void BuildNormals(void);
static void UpdateTint(const BattleStageFileLighting *dayLighting);
static BOOL InitBlobs(const BattleStageSpriteCamera *camera);
static void FreeBlobs(void);

static StageSprites sStageSprites;
static u16 sBlobPalette[BLOB_PLTT_BYTES / 2]; // black
static u8 sBlobTexture[BLOB_TEX_BYTES];

void BattleStageSprites_Init(BattleSystem *battleSys, BattleStageSpriteFields *fields, const BattleStageSpriteCamera *camera)
{
    int i;

    sStageSprites.battleSys = battleSys;
    sStageSprites.fields = fields;
    sStageSprites.hooked = FALSE;
    sStageSprites.moveAnimActive = FALSE;
    sStageSprites.visible = FALSE;
    sStageSprites.wasVisible = FALSE;
    sStageSprites.advanced = FALSE;
    sStageSprites.lighting = NULL;
    sStageSprites.view = NULL;
    sStageSprites.hasBlobs = FALSE;

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
}

void BattleStageSprites_Free(void)
{
    if (sStageSprites.hooked) {
        PokemonSpriteManager_SetDrawHook(BattleSystem_GetPokemonSpriteManager(sStageSprites.battleSys), NULL);
        sStageSprites.hooked = FALSE;
    }

    FreeBlobs();
    sStageSprites.battleSys = NULL;
    sStageSprites.visible = FALSE;
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

    if (sStageSprites.visible) {
        UpdateTint(dayLighting);
    }

    fields->spriteMeshes = 0;
    fields->blobShadows = 0;
    fields->wobbleMask = 0;

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
    }

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

        return result;
    }

    width = rect->width;
    height = rect->height;

    if (monSpriteMan->excludeIdentity == TRUE
        || width == 0
        || height == 0
        || width > 2 * MESH_MAX_HALF_SIZE
        || width < -2 * MESH_MAX_HALF_SIZE
        || height > 2 * MESH_MAX_HALF_SIZE
        || height < -2 * MESH_MAX_HALF_SIZE) {
        ResetBreath(index);

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
        texS[i] = rect->u0 * FX32_ONE + (rect->u1 - rect->u0) * i * (FX32_ONE / GRID);
        texT[i] = rect->v0 * FX32_ONE + (rect->v1 - rect->v0) * i * (FX32_ONE / GRID);
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
    G3_Translate(rect->x * FX32_ONE + width * (FX32_ONE / 2), rect->y * FX32_ONE + height * (FX32_ONE / 2), rect->z * FX32_ONE);
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

static BOOL InitBlobs(const BattleStageSpriteCamera *camera)
{
    sStageSprites.groundHalfWidth[0] = 0;
    sStageSprites.groundHalfWidth[1] = 0;
    BuildGroundMapping(camera);

    if (sStageSprites.groundHalfWidth[0] <= 0 || sStageSprites.groundHalfWidth[1] <= 0) {
        return FALSE;
    }

    sStageSprites.blobTexKey = NNS_GfdAllocTexVram(BLOB_TEX_BYTES, FALSE, 0);

    if (sStageSprites.blobTexKey == NNS_GFD_ALLOC_ERROR_TEXKEY) {
        return FALSE;
    }

    sStageSprites.blobTexAddr = NNS_GfdGetTexKeyAddr(sStageSprites.blobTexKey);

    if (sStageSprites.blobTexAddr + BLOB_TEX_BYTES > BLOB_TEX_VRAM_END) {
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
    DC_FlushRange(sBlobTexture, sizeof(sBlobTexture));
    DC_FlushRange(sBlobPalette, sizeof(sBlobPalette));

    GX_BeginLoadTex();
    GX_LoadTex(sBlobTexture, sStageSprites.blobTexAddr, BLOB_TEX_BYTES);
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

void BattleStageSprites_DrawBlobs(const MtxFx44 *projection)
{
    PokemonSpriteManager *monSpriteMan;
    MtxFx44 flat;
    int numBattlers, i;
    BOOL started = FALSE;

    if (!BlobsOn()) {
        return;
    }

    monSpriteMan = BattleSystem_GetPokemonSpriteManager(sStageSprites.battleSys);
    numBattlers = BattleSystem_MaxBattlers(sStageSprites.battleSys);

    if (numBattlers > MAX_MON_SPRITES) {
        numBattlers = MAX_MON_SPRITES;
    }

    for (i = 0; i < numBattlers; i++) {
        const PokemonSprite *sprite = &monSpriteMan->sprites[i];
        const PokemonSpriteTransforms *transforms = &sprite->transforms;
        int side, widthPx, scale, px, rows;
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

        // Half the width, as a fraction of the 128 pixels groundHalfWidth covers
        radius = sStageSprites.groundHalfWidth[side] * widthPx / 2 / 128 * scale / MON_AFFINE_SCALE(1);

        if (radius <= 0) {
            continue;
        }

        px = transforms->xCenter + transforms->xOffset + sprite->shadow.xOffset - 128;
        centre.x = sStageSprites.groundCentre[side].x + sStageSprites.groundRight[side].x * px / 128;
        centre.y = sStageSprites.groundCentre[side].y + sStageSprites.groundRight[side].y * px / 128;
        centre.z = sStageSprites.groundCentre[side].z + sStageSprites.groundRight[side].z * px / 128;
        a.x = FX_Mul(sStageSprites.right.x, radius);
        a.y = FX_Mul(sStageSprites.right.y, radius);
        a.z = FX_Mul(sStageSprites.right.z, radius);
        // Half the height on screen, in rows, times the ground per row
        rows = widthPx * scale / MON_AFFINE_SCALE(1) / (2 * BLOB_HEIGHT_DIV);
        b.x = sStageSprites.groundDown[side].x * rows;
        b.y = 0;
        b.z = sStageSprites.groundDown[side].z * rows;

        if (!started) {
            // The arena's projection with z' = BLOB_DEPTH * w (the projection stack has a
            // single entry, which DrawArena uses)
            flat = *projection;
            flat._02 = FX_Mul(BLOB_DEPTH, flat._03);
            flat._12 = FX_Mul(BLOB_DEPTH, flat._13);
            flat._22 = FX_Mul(BLOB_DEPTH, flat._23);
            flat._32 = FX_Mul(BLOB_DEPTH, flat._33);
            G3_MtxMode(GX_MTXMODE_PROJECTION);
            G3_LoadMtx44(&flat);
            G3_MtxMode(GX_MTXMODE_POSITION_VECTOR);

            // Texcoords used as is (no texture matrix), no light, no fog; translucent
            // (A5I3), so it doesn't write depth and blends over the ground
            G3_TexImageParam(GX_TEXFMT_A5I3, GX_TEXGEN_NONE, GX_TEXSIZE_S32, GX_TEXSIZE_T16, GX_TEXREPEAT_NONE, GX_TEXFLIP_NONE, GX_TEXPLTTCOLOR0_USE, sStageSprites.blobTexAddr);
            G3_TexPlttBase(sStageSprites.blobPlttAddr, GX_TEXFMT_A5I3);
            G3_PolygonAttr(GX_LIGHTMASK_NONE, GX_POLYGONMODE_MODULATE, GX_CULL_NONE, BLOB_POLYGON_ID, 31, 0);
            G3_Color(GX_RGB(31, 31, 31));
            started = TRUE;
        }

        G3_PushMtx();
        G3_Translate(centre.x, centre.y, centre.z);
        G3_Begin(GX_BEGIN_QUADS);
        G3_TexCoord(0, 0);
        G3_Vtx((fx16)(-a.x - b.x), (fx16)(-a.y - b.y), (fx16)(-a.z - b.z));
        G3_TexCoord(BLOB_TEX_WIDTH * FX32_ONE, 0);
        G3_Vtx((fx16)(a.x - b.x), (fx16)(a.y - b.y), (fx16)(a.z - b.z));
        G3_TexCoord(BLOB_TEX_WIDTH * FX32_ONE, BLOB_TEX_HEIGHT * FX32_ONE);
        G3_Vtx((fx16)(a.x + b.x), (fx16)(a.y + b.y), (fx16)(a.z + b.z));
        G3_TexCoord(0, BLOB_TEX_HEIGHT * FX32_ONE);
        G3_Vtx((fx16)(-a.x + b.x), (fx16)(-a.y + b.y), (fx16)(-a.z + b.z));
        G3_End();
        G3_PopMtx(1);

        sStageSprites.fields->blobShadows++;
    }

    if (started) {
        G3_MtxMode(GX_MTXMODE_PROJECTION);
        G3_LoadMtx44(projection);
        G3_MtxMode(GX_MTXMODE_POSITION_VECTOR);
    }
}
