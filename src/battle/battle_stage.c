#include "battle/battle_stage.h"

#include <nitro.h>
#include <nnsys.h>
#include <string.h>

#include "config/battle_stage.h"
#include "constants/battle.h"
#include "constants/graphics.h"
#include "constants/heap.h"
#include "constants/narc.h"

#include "battle/battle_stage_camera.h"
#include "battle/battle_stage_format.h"
#include "battle/battle_stage_sprites.h"
#include "battle/ov16_0223DF00.h"
#include "battle/ov16_02268520.h"

#include "bg_window.h"
#include "heap.h"
#include "narc.h"
#include "palette.h"
#include "vram_transfer.h"

#define STAGE_MAX_TEXTURES 8
#define STAGE_MAX_MESHES   64
#define STAGE_NUM_VIEWS    4

// Bank B; the bag and party menus unmap the texture banks above it
#define STAGE_TEX_VRAM_END 0x20000

// NDC depth range of the arena (fx32). The sprites land at 0..0.625, the shadows at 0.977
// and the particles near -1; the clear depth is 1.
#define STAGE_DEPTH_NEAR 4010
#define STAGE_DEPTH_FAR  4094

// ov16_0223EF8C keeps a copy of the platform palette in this BG row
#define STAGE_PLATFORM_BG_ROW 7

// F6 (compat.md): the arena fades out and in over this many drawn frames when a move hides it
#define STAGE_FADE_STEPS SCREEN_FRAMES(8)
#define STAGE_ALPHA_MAX  31
// Polygon IDs of the arena meshes while they are translucent: one per mesh, so an arena mesh
// still draws over another (a translucent polygon skips pixels of its own ID), and clear
// of the mons' low IDs and the shadows' 62
#define STAGE_FADE_POLYGON_ID_BASE  32
#define STAGE_FADE_POLYGON_ID_COUNT 30
// The layers under BG0 that the translucent arena blends with (2nd targets)
#define STAGE_FADE_BLEND_TARGETS (GX_BLEND_PLANEMASK_BG2 | GX_BLEND_PLANEMASK_BG3 | GX_BLEND_PLANEMASK_OBJ | GX_BLEND_PLANEMASK_BD)
// Draws after a fade ends before the added blend targets go: the last translucent frame
// stays on screen until the next geometry swap
#define STAGE_FADE_BLEND_HOLD 2
// Reasons that always hide at once: a screen that owns VRAM
#define STAGE_SUPPRESS_INSTANT BATTLE_STAGE_SUPPRESS_MENU
// BattleStage_SetCurtain: the bars lie in front of the arena and the shadows (0.977) and
// behind the sprites (0.625 at most); their own polygon ID, clear of the shadows' 62
#define STAGE_CURTAIN_DEPTH       FX16_CONST(0.95)
#define STAGE_CURTAIN_POLYGON_ID  63

enum StagePaletteSlot {
    SLOT_BG = 0,
    SLOT_PLATFORM_PLAYER,
    SLOT_PLATFORM_ENEMY,
    SLOT_EMBEDDED, // one per texture from here
    SLOT_MAX = SLOT_EMBEDDED + STAGE_MAX_TEXTURES,
};

typedef struct StagePalette {
    u32 offset;
    u16 numColors; // 0 when unused
    u16 dirty;
    u16 colors[256];
} StagePalette;

typedef struct StageMesh {
    u32 dlOffset;
    u32 dlSize;
    fx32 vertexScale;
    u16 flags;
    u8 scrollAmplitude[2];
    u16 scrollPeriod;
    u16 attrIndex; // word of the POLYGON_ATTR parameter in the mesh's DL, 0 when not found
    u16 alpha; // the mesh's own polygon alpha
    u32 attr; // its POLYGON_ATTR parameter as built
} StageMesh;

typedef struct StageArena {
    NNSGfdTexKey texKey;
    NNSGfdPlttKey plttKey;
    u32 plttAddr;
    u32 *dl;
    int numMeshes;
    StageMesh meshes[STAGE_MAX_MESHES];
    StagePalette palettes[SLOT_MAX];
    VecFx32 camPos;
    VecFx32 camTarget;
    fx32 fovySin;
    fx32 fovyCos;
    fx32 nearClip;
    fx32 farClip;
    VecFx32 platformStep[2];
    MtxFx44 projection; // home
    MtxFx43 view; // home
    BOOL hasTexMtxMesh; // FOLLOW_BG3_SCROLL or SCROLL
    BOOL hasLitMesh;
    BOOL hasAtmosphere;
    u32 frame; // drawn frames, for SCROLL
    int dlAlpha; // arena alpha the DL's POLYGON_ATTR words are patched for
    BattleStageFileAtmosphere atmosphere;
} StageArena;

typedef struct BattleStage {
    BattleSystem *battleSys;
    StageArena *arena;
    BOOL enabled;
    u32 suppressed;
    int debugView;
    BOOL wasVisible;
    BOOL platformsHidden;
    int brightness; // BattleStage_SetBrightness; the Mega critic reads it from RAM at +28
    BattleStageSpriteFields sprites; // +32..+48, read and written by the critic (sprites.md)
    BattleStageCameraFields camera; // +52..+95, read by the critic (camera.md)
    BattleStageCompatFields compat; // +96..+119, read by the critic (compat.md)
    BattleStageCutGuardFields cutGuard; // +120..+139, read by the critic (cut_guard.md)
    BOOL inMoveAnim; // BattleStage_SetInMoveAnim: suppressions fade instead of popping
    int fadePos; // 0 (hidden) .. STAGE_FADE_STEPS (opaque)
    BOOL fadingOut;
    BOOL instantHidden; // hidden without a fade, so it comes back without one
    u16 blendAdded; // BLDCNT 2nd-target bits the fade added
    u16 blendWritten; // BLDCNT as the fade last left it
    int blendHold;
    u16 backdropFadeColor; // BattleStage_SetBackdropFade
    int backdropFadeAlpha; // 0..16
    BOOL backdropGrayscale; // BattleStage_SetBackdropGrayscale
    BOOL curtainOn; // BattleStage_SetCurtain
    int curtainLeft;
    int curtainRight;
} BattleStage;

// What was last written to the fog registers
typedef struct StageFog {
    BOOL on;
    BOOL tableValid;
    u32 table[8]; // 32 densities, as G3X_SetFogTable takes them
} StageFog;

static StageArena *LoadArena(BattleSystem *battleSys);
static void FreeArena(StageArena *arena);
static void UpdatePlatforms(BOOL visible);
static void SyncPalettes(StageArena *arena);
static void DrawArena(StageArena *arena, const MtxFx43 *view, const MtxFx44 *projection);
static const BattleStageFileLighting *CurrentLighting(StageArena *arena);
static const BattleStageFileLighting *DayLighting(StageArena *arena);
static void UpdateFog(StageArena *arena);
static void FogOff(void);
static void UpdateFade(void);
static void PatchArenaAlpha(StageArena *arena, int alpha);
static void UpdateFadeBlend(BOOL translucent);
static void DrawCurtain(int alpha);

static BattleStage sBattleStage;
static StageFog sStageFog;

// Without an atmosphere LIT meshes render unlit white, as in format v1
static const BattleStageFileLighting sDefaultLighting = {
    .lightDir = { 0, -FX16_ONE + 1, 0 },
    .lightColor = GX_RGB(0, 0, 0),
    .diffuse = GX_RGB(0, 0, 0),
    .ambient = GX_RGB(0, 0, 0),
    .emission = GX_RGB(31, 31, 31),
};

void BattleStage_Init(BattleSystem *battleSys)
{
    sBattleStage.battleSys = battleSys;
    sBattleStage.arena = NULL;
    sBattleStage.enabled = BATTLE_STAGE_3D;
    sBattleStage.suppressed = 0;
    sBattleStage.debugView = 0;
    sBattleStage.wasVisible = FALSE;
    sBattleStage.platformsHidden = FALSE;
    sBattleStage.brightness = 0;
    sBattleStage.curtainOn = FALSE;
    memset(&sBattleStage.compat, 0, sizeof(sBattleStage.compat));
    sBattleStage.inMoveAnim = FALSE;
    sBattleStage.fadePos = STAGE_FADE_STEPS;
    sBattleStage.fadingOut = FALSE;
    sBattleStage.instantHidden = FALSE;
    sBattleStage.blendAdded = 0;
    sBattleStage.blendWritten = 0;
    sBattleStage.blendHold = 0;
    sBattleStage.backdropFadeColor = 0;
    sBattleStage.backdropFadeAlpha = 0;
    sBattleStage.backdropGrayscale = FALSE;
    sStageFog.on = TRUE; // unknown, so FogOff writes it
    sStageFog.tableValid = FALSE;
    FogOff();

    if (BATTLE_STAGE_3D) {
        sBattleStage.arena = LoadArena(battleSys);
    }

    // Resets the sprite fields and hooks the battle's sprites when there is an arena
    if (sBattleStage.arena != NULL) {
        BattleStageSpriteCamera camera;

        camera.camPos = sBattleStage.arena->camPos;
        camera.camTarget = sBattleStage.arena->camTarget;
        camera.fovySin = sBattleStage.arena->fovySin;
        camera.fovyCos = sBattleStage.arena->fovyCos;
        BattleStageSprites_Init(battleSys, &sBattleStage.sprites, &camera);
    } else {
        BattleStageSprites_Init(battleSys, &sBattleStage.sprites, NULL);
    }

    // Resets the camera fields and hooks the particles when there is an arena
    if (sBattleStage.arena != NULL) {
        BattleStageCameraHome home;

        home.camPos = sBattleStage.arena->camPos;
        home.camTarget = sBattleStage.arena->camTarget;
        home.fovySin = sBattleStage.arena->fovySin;
        home.fovyCos = sBattleStage.arena->fovyCos;
        home.nearClip = sBattleStage.arena->nearClip;
        home.farClip = sBattleStage.arena->farClip;
        home.view = &sBattleStage.arena->view;
        home.projection = &sBattleStage.arena->projection;
        BattleStageCamera_Init(battleSys, &sBattleStage.camera, &sBattleStage.cutGuard, &home, &sBattleStage.sprites.debugFlags);
    } else {
        BattleStageCamera_Init(battleSys, &sBattleStage.camera, &sBattleStage.cutGuard, NULL, &sBattleStage.sprites.debugFlags);
    }
}

void BattleStage_Free(void)
{
    BattleStageCamera_Free();
    BattleStageSprites_Free();

    if (sBattleStage.arena != NULL) {
        FreeArena(sBattleStage.arena);
        sBattleStage.arena = NULL;
    }

    // Takes back the blend targets of a fade in progress
    sBattleStage.blendHold = 0;
    UpdateFadeBlend(FALSE);
    sBattleStage.inMoveAnim = FALSE;
    sBattleStage.battleSys = NULL;
    sBattleStage.debugView = 0;
    sBattleStage.brightness = 0;
    sBattleStage.backdropFadeAlpha = 0;
    sBattleStage.backdropGrayscale = FALSE;
    sBattleStage.curtainOn = FALSE;
    FogOff();
}

void BattleStage_Draw(void)
{
    BOOL visible;
    const MtxFx43 *view;
    const MtxFx44 *projection;

    if (sBattleStage.battleSys == NULL || sBattleStage.arena == NULL) {
        BattleStageSprites_BeginFrame(FALSE, NULL, NULL, NULL);
        return;
    }

    UpdateFade();
    visible = BattleStage_IsVisible();

    // Home draws with the arena's own matrices, exactly as before the camera
    BattleStageCamera_Advance(visible, sBattleStage.debugView);

    if (BattleStageCamera_IsHome()) {
        view = &sBattleStage.arena->view;
        projection = &sBattleStage.arena->projection;
    } else {
        view = BattleStageCamera_View();
        projection = BattleStageCamera_Projection();
    }

    BattleStageSprites_BeginFrame(visible, CurrentLighting(sBattleStage.arena), DayLighting(sBattleStage.arena), view);
    UpdatePlatforms(visible);

    if (visible) {
        int alpha = STAGE_ALPHA_MAX * sBattleStage.fadePos / STAGE_FADE_STEPS;

        SyncPalettes(sBattleStage.arena);
        PatchArenaAlpha(sBattleStage.arena, alpha);
        DrawArena(sBattleStage.arena, view, projection);
        DrawCurtain(alpha);
        UpdateFog(sBattleStage.arena);
        sBattleStage.compat.arenaAlpha = alpha;
    } else {
        FogOff();
        sBattleStage.compat.arenaAlpha = 0;

        if (sBattleStage.enabled) {
            sBattleStage.compat.hiddenFrames++;
        }
    }

    UpdateFadeBlend(visible && sBattleStage.fadePos < STAGE_FADE_STEPS);
    sBattleStage.wasVisible = visible;
}

void BattleStage_SetEnabled(BOOL enabled)
{
    sBattleStage.enabled = BATTLE_STAGE_3D && enabled;
}

BOOL BattleStage_IsEnabled(void)
{
    return sBattleStage.enabled;
}

void BattleStage_Suppress(u32 reasons, BOOL suppress)
{
    if (suppress) {
        sBattleStage.suppressed |= reasons;

        // A screen that takes over the scene hides the platforms itself; don't show them
        // again under it when the arena goes away
        if (reasons & BATTLE_STAGE_SUPPRESS_MENU) {
            sBattleStage.platformsHidden = FALSE;
        }
    } else {
        sBattleStage.suppressed &= ~reasons;
    }
}

BOOL BattleStage_HasArena(void)
{
    return sBattleStage.battleSys != NULL && sBattleStage.arena != NULL;
}

// TRUE when the arena goes at once: the debug toggle, the menu, or a reason set outside a
// move animation
static BOOL IsHiddenInstantly(void)
{
    return !sBattleStage.enabled
        || (sBattleStage.suppressed & STAGE_SUPPRESS_INSTANT) != 0
        || (sBattleStage.suppressed != 0 && !sBattleStage.inMoveAnim && !sBattleStage.fadingOut);
}

BOOL BattleStage_IsVisible(void)
{
    if (sBattleStage.battleSys == NULL || sBattleStage.arena == NULL || IsHiddenInstantly()) {
        return FALSE;
    }

    // Still drawn while it fades out; back at once after an instant hide
    return sBattleStage.fadePos > 0 || (sBattleStage.suppressed == 0 && sBattleStage.instantHidden);
}

BOOL BattleStage_IsFading(void)
{
    return BattleStage_IsVisible() && sBattleStage.fadePos < STAGE_FADE_STEPS && !sBattleStage.instantHidden;
}

void BattleStage_SetInMoveAnim(BOOL inMoveAnim)
{
    sBattleStage.inMoveAnim = inMoveAnim;
}

// Once per drawn frame, before the arena draws: steps the fade toward the suppression state
static void UpdateFade(void)
{
    BattleStageCompatFields *compat = &sBattleStage.compat;

    if (IsHiddenInstantly()) {
        // A pop during a move animation; the toggle and the menu outside one aren't counted
        if (sBattleStage.fadePos > 0 && !sBattleStage.instantHidden && sBattleStage.inMoveAnim) {
            compat->hardPops++;
        }

        sBattleStage.fadePos = 0;
        sBattleStage.instantHidden = TRUE;
        sBattleStage.fadingOut = FALSE;
    } else if (sBattleStage.suppressed != 0) {
        if (sBattleStage.instantHidden) {
            sBattleStage.fadePos = 0;
        } else if (sBattleStage.fadePos > 0) {
            if (!sBattleStage.fadingOut) {
                compat->fades++;
            }

            sBattleStage.fadingOut = TRUE;
            sBattleStage.fadePos--;
        }
    } else {
        sBattleStage.fadingOut = FALSE;

        if (sBattleStage.instantHidden) {
            sBattleStage.fadePos = STAGE_FADE_STEPS;
            sBattleStage.instantHidden = FALSE;
        } else if (sBattleStage.fadePos < STAGE_FADE_STEPS) {
            sBattleStage.fadePos++;
        }
    }
}

// Rewrites the alpha (and, while translucent, the polygon ID and depth update) of every
// mesh's POLYGON_ATTR in the DL; at STAGE_ALPHA_MAX the DL is exactly as built
static void PatchArenaAlpha(StageArena *arena, int alpha)
{
    int i;

    if (arena->dlAlpha == alpha) {
        return;
    }

    for (i = 0; i < arena->numMeshes; i++) {
        StageMesh *mesh = &arena->meshes[i];
        u32 *word = arena->dl + mesh->dlOffset / 4 + mesh->attrIndex;
        u32 attr = mesh->attr;

        if (mesh->attrIndex == 0) {
            continue;
        }

        if (alpha < STAGE_ALPHA_MAX && mesh->alpha != 0) {
            int meshAlpha = mesh->alpha * alpha / STAGE_ALPHA_MAX;

            // 0 would draw wireframe
            if (meshAlpha < 1) {
                meshAlpha = 1;
            }

            attr &= ~(REG_G3_POLYGON_ATTR_ALPHA_MASK | REG_G3_POLYGON_ATTR_ID_MASK);
            attr |= (u32)meshAlpha << REG_G3_POLYGON_ATTR_ALPHA_SHIFT;
            attr |= (u32)(STAGE_FADE_POLYGON_ID_BASE + i % STAGE_FADE_POLYGON_ID_COUNT) << REG_G3_POLYGON_ATTR_ID_SHIFT;

            // An opaque mesh keeps writing depth, so the fog and the shadows see the same depth
            if (mesh->alpha == STAGE_ALPHA_MAX) {
                attr |= REG_G3_POLYGON_ATTR_XL_MASK;
            }
        }

        *word = attr;
        DC_FlushRange(word, sizeof(u32));
    }

    arena->dlAlpha = alpha;
}

// A translucent 3D pixel only blends with the layer under it when that layer is a 2nd target
// in BLDCNT. The fade adds the targets it needs and takes them back once it is done, unless
// something else wrote BLDCNT in between.
static void UpdateFadeBlend(BOOL translucent)
{
    u16 bldcnt;

    if (translucent) {
        u16 targets = STAGE_FADE_BLEND_TARGETS << REG_G2_BLDCNT_PLANE2_SHIFT;

        bldcnt = reg_G2_BLDCNT;

        if ((bldcnt & targets) != targets) {
            sBattleStage.blendAdded |= targets & ~bldcnt;
            bldcnt |= targets;
            reg_G2_BLDCNT = bldcnt;
        }

        sBattleStage.blendWritten = bldcnt;
        sBattleStage.blendHold = STAGE_FADE_BLEND_HOLD;
        return;
    }

    if (sBattleStage.blendAdded == 0) {
        return;
    }

    if (sBattleStage.blendHold > 0) {
        sBattleStage.blendHold--;
        return;
    }

    bldcnt = reg_G2_BLDCNT;

    if (bldcnt == sBattleStage.blendWritten) {
        reg_G2_BLDCNT = bldcnt & ~sBattleStage.blendAdded;
    }

    sBattleStage.blendAdded = 0;
}

BattleStageCompatFields *BattleStage_CompatFields(void)
{
    return &sBattleStage.compat;
}

void BattleStage_SetDebugView(int view)
{
    if (view < 0 || view >= STAGE_NUM_VIEWS) {
        view = 0;
    }

    sBattleStage.debugView = view;
}

int BattleStage_GetDebugView(void)
{
    return sBattleStage.debugView;
}

void BattleStage_SetBrightness(int brightness)
{
    if (brightness < -16) {
        brightness = -16;
    } else if (brightness > 16) {
        brightness = 16;
    }

    sBattleStage.brightness = brightness;
}

void BattleStage_SetBackdropFade(u16 color, int alpha)
{
    if (alpha < 0) {
        alpha = 0;
    } else if (alpha > 16) {
        alpha = 16;
    }

    sBattleStage.backdropFadeColor = color & 0x7FFF;
    sBattleStage.backdropFadeAlpha = alpha;
}

void BattleStage_SetBackdropGrayscale(BOOL grayscale)
{
    sBattleStage.backdropGrayscale = grayscale;
}

// The brightness wins over the backdrop fade, as it does in 2D where it applies last
static BOOL BackdropFadeActive(void)
{
    return sBattleStage.brightness == 0 && (sBattleStage.backdropFadeAlpha != 0 || sBattleStage.backdropGrayscale);
}

// A colour of the arena as the backdrop fade shows it: grayed as SetBgGrayscale grays the
// BG palette, then blended as PaletteData_StartFade blends it
static GXRgb BackdropFadeColor(GXRgb color)
{
    int r = ColorR(color);
    int g = ColorG(color);
    int b = ColorB(color);
    int target = sBattleStage.backdropFadeColor;

    if (sBattleStage.backdropGrayscale) {
        r = g = b = RGB_TO_GRAYSCALE(r, g, b);
    }

    r = BlendColor(r, ColorR(target), sBattleStage.backdropFadeAlpha);
    g = BlendColor(g, ColorG(target), sBattleStage.backdropFadeAlpha);
    b = BlendColor(b, ColorB(target), sBattleStage.backdropFadeAlpha);

    return GX_RGB(r, g, b);
}

// The emission of the LIT meshes under the backdrop fade. The faded texture is modulated
// by the light, so a dim (twilight, night) light would keep a fade towards white or a
// colour from reaching it: each channel's light rises towards full by as much as the fade
// target has of that channel, so a full fade shows the flat colour and a fade to black
// leaves the light alone
static GXRgb BackdropFadeEmission(GXRgb emission)
{
    int channel[3] = { ColorR(emission), ColorG(emission), ColorB(emission) };
    int target[3] = { ColorR(sBattleStage.backdropFadeColor), ColorG(sBattleStage.backdropFadeColor), ColorB(sBattleStage.backdropFadeColor) };
    int i;

    if (sBattleStage.backdropGrayscale) {
        channel[0] = channel[1] = channel[2] = RGB_TO_GRAYSCALE(channel[0], channel[1], channel[2]);
    }

    for (i = 0; i < 3; i++) {
        channel[i] += (31 - channel[i]) * target[i] * sBattleStage.backdropFadeAlpha / (31 * 16);
    }

    return GX_RGB(channel[0], channel[1], channel[2]);
}

// The light of the LIT meshes, grayed along with the backdrop
static GXRgb BackdropGrayColor(GXRgb color)
{
    int y;

    if (!sBattleStage.backdropGrayscale) {
        return color;
    }

    y = RGB_TO_GRAYSCALE(ColorR(color), ColorG(color), ColorB(color));
    return GX_RGB(y, y, y);
}

void BattleStage_SetCurtain(int left, int right)
{
    sBattleStage.curtainOn = TRUE;
    sBattleStage.curtainLeft = left < 0 ? 0 : (left > HW_LCD_WIDTH ? HW_LCD_WIDTH : left);
    sBattleStage.curtainRight = right < sBattleStage.curtainLeft ? sBattleStage.curtainLeft : (right > HW_LCD_WIDTH ? HW_LCD_WIDTH : right);
}

void BattleStage_ClearCurtain(void)
{
    sBattleStage.curtainOn = FALSE;
}

static const void *PieceData(const BattleStageFileHeader *piece, u32 offset)
{
    return (const u8 *)piece + offset;
}

static BOOL IsRangeValid(u32 offset, u32 size, u32 pieceSize)
{
    return (offset & 3) == 0 && offset <= pieceSize && size <= pieceSize - offset;
}

// GX_TEXSIZE_S*/T* for a power of two in 8..1024, or -1
static int TexSizeParam(u16 size)
{
    int i;

    for (i = GX_TEXSIZE_S8; i <= GX_TEXSIZE_S1024; i++) {
        if (size == (8 << i)) {
            return i;
        }
    }

    return -1;
}

static u32 TextureBytes(const BattleStageFileTexture *texture)
{
    u32 texels = texture->width * texture->height;

    return texture->format == GX_TEXFMT_PLTT16 ? texels / 2 : texels;
}

static BOOL IsAtmosphereValid(const BattleStageFileAtmosphere *atmosphere)
{
    int i;

    if (atmosphere->fogShift > GX_FOGSLOPE_0x0020 || atmosphere->fogOffset > 0x7FFF) {
        return FALSE;
    }

    for (i = 0; i < 32; i++) {
        if (atmosphere->fogTable[i] > 127) {
            return FALSE;
        }
    }

    for (i = 0; i < 3; i++) {
        if (atmosphere->lighting[i].fogAlpha > 31) {
            return FALSE;
        }
    }

    return TRUE;
}

// The atmosphere is only read from the backdrop piece; a platform piece's is ignored
static BOOL IsPieceValid(const BattleStageFileHeader *piece, u32 size, BOOL isBackdrop)
{
    const BattleStageFileTexture *textures;
    const BattleStageFileMesh *meshes;
    int i;

    if (piece->magic != BATTLE_STAGE_MAGIC || piece->version != BATTLE_STAGE_VERSION || piece->numMeshes == 0) {
        return FALSE;
    }

    if (!IsRangeValid(piece->texturesOffset, piece->numTextures * sizeof(BattleStageFileTexture), size)
        || !IsRangeValid(piece->meshesOffset, piece->numMeshes * sizeof(BattleStageFileMesh), size)) {
        return FALSE;
    }

    textures = PieceData(piece, piece->texturesOffset);

    for (i = 0; i < piece->numTextures; i++) {
        const BattleStageFileTexture *texture = &textures[i];

        if (TexSizeParam(texture->width) < 0 || TexSizeParam(texture->height) < 0) {
            return FALSE;
        }

        if (texture->format != GX_TEXFMT_PLTT16 && texture->format != GX_TEXFMT_PLTT256) {
            return FALSE;
        }

        if (texture->paletteSource > BATTLE_STAGE_PALETTE_EMBEDDED
            || (texture->paletteSource == BATTLE_STAGE_PALETTE_PLATFORM_OBJ && texture->format != GX_TEXFMT_PLTT16)) {
            return FALSE;
        }

        if (texture->dataSize < TextureBytes(texture)
            || !IsRangeValid(texture->dataOffset, texture->dataSize, size)
            || !IsRangeValid(texture->paletteOffset, texture->paletteSize, size)) {
            return FALSE;
        }
    }

    meshes = PieceData(piece, piece->meshesOffset);

    for (i = 0; i < piece->numMeshes; i++) {
        const BattleStageFileMesh *mesh = &meshes[i];

        if (mesh->textureIndex >= piece->numTextures || mesh->primitive > GX_BEGIN_QUAD_STRIP || mesh->numVertices == 0 || mesh->alpha > 31) {
            return FALSE;
        }

        if (!IsRangeValid(mesh->vertexOffset, mesh->numVertices * sizeof(BattleStageFileVertex), size)) {
            return FALSE;
        }

        if ((mesh->flags & BATTLE_STAGE_MESH_SCROLL) && mesh->scrollPeriod == 0) {
            return FALSE;
        }
    }

    if (isBackdrop && piece->atmosphereOffset != 0) {
        if (!IsRangeValid(piece->atmosphereOffset, sizeof(BattleStageFileAtmosphere), size)
            || !IsAtmosphereValid(PieceData(piece, piece->atmosphereOffset))) {
            return FALSE;
        }
    }

    return TRUE;
}

static BattleStageFileHeader *LoadPiece(NARC *narc, u32 memberIndex, BOOL isBackdrop, u32 *outSize)
{
    BattleStageFileHeader *piece;
    u32 size;

    if (memberIndex >= NARC_GetFileCount(narc)) {
        return NULL;
    }

    size = NARC_GetMemberSize(narc, memberIndex);

    if (size < sizeof(BattleStageFileHeader)) {
        return NULL;
    }

    piece = Heap_AllocAtEnd(HEAP_ID_BATTLE, size);

    if (piece == NULL) {
        return NULL;
    }

    NARC_ReadWholeMember(narc, memberIndex, piece);

    if (!IsPieceValid(piece, size, isBackdrop)) {
        Heap_Free(piece);
        return NULL;
    }

    *outSize = size;
    return piece;
}

static int PaletteSlot(const BattleStageFileTexture *texture, const BattleStageFileMesh *mesh, int textureSlot)
{
    switch (texture->paletteSource) {
    case BATTLE_STAGE_PALETTE_BG:
        return SLOT_BG;
    case BATTLE_STAGE_PALETTE_PLATFORM_OBJ:
        return (mesh->flags & BATTLE_STAGE_MESH_FOLLOW_PLATFORM_ENEMY) ? SLOT_PLATFORM_ENEMY : SLOT_PLATFORM_PLAYER;
    default:
        return textureSlot;
    }
}

// Upper bound of the display list size for a mesh, in bytes
static u32 MeshDLBound(const BattleStageFileMesh *mesh)
{
    u32 numCommands = 5 + 3 * mesh->numVertices;
    u32 numParams = 4 + 4 * mesh->numVertices;

    return 4 * (numParams + (numCommands + 3) / 4 + 2);
}

static u32 BuildMeshDL(u32 *dest, u32 capacity, const BattleStageFileHeader *piece, const BattleStageFileMesh *mesh, const BattleStageFileTexture *texture, u32 texAddr, u32 plttAddr, u32 *outAttr)
{
    GXDLInfo info;
    const BattleStageFileVertex *vertices = PieceData(piece, mesh->vertexOffset);
    GXTexGen texGen = (mesh->flags & (BATTLE_STAGE_MESH_FOLLOW_BG3_SCROLL | BATTLE_STAGE_MESH_SCROLL)) ? GX_TEXGEN_TEXCOORD : GX_TEXGEN_NONE;
    GXTexPlttColor0 color0 = (mesh->flags & BATTLE_STAGE_MESH_COLOR0_TRANSPARENT) ? GX_TEXPLTTCOLOR0_TRNS : GX_TEXPLTTCOLOR0_USE;
    BOOL lit = (mesh->flags & BATTLE_STAGE_MESH_LIT) != 0;
    int misc = GX_POLYGON_ATTR_MISC_FAR_CLIPPING;
    int i;

    if (mesh->flags & BATTLE_STAGE_MESH_FOG) {
        misc |= GX_POLYGON_ATTR_MISC_FOG;
    }

    G3_BeginMakeDL(&info, dest, capacity);
    G3C_TexImageParam(&info,
        (GXTexFmt)texture->format,
        texGen,
        (GXTexSizeS)TexSizeParam(texture->width),
        (GXTexSizeT)TexSizeParam(texture->height),
        (GXTexRepeat)((mesh->flags >> 4) & GX_TEXREPEAT_ST),
        (GXTexFlip)((mesh->flags >> 6) & GX_TEXFLIP_ST),
        color0,
        texAddr);
    G3C_TexPlttBase(&info, plttAddr, (GXTexFmt)texture->format);
    *outAttr = GX_PACK_POLYGONATTR_PARAM(lit ? GX_LIGHTMASK_0 : GX_LIGHTMASK_NONE, GX_POLYGONMODE_MODULATE, GX_CULL_NONE, 0, mesh->alpha, misc);
    G3C_PolygonAttr(&info, lit ? GX_LIGHTMASK_0 : GX_LIGHTMASK_NONE, GX_POLYGONMODE_MODULATE, GX_CULL_NONE, 0, mesh->alpha, misc);
    G3C_Begin(&info, (GXBegin)mesh->primitive);

    for (i = 0; i < mesh->numVertices; i++) {
        const BattleStageFileVertex *vertex = &vertices[i];

        // A normal command lights the vertex with the material and light 0; the packed
        // normal is sent as is (G3C_Normal would take it apart and pack it again)
        if (lit) {
            if (i == 0 || vertex->normal != vertices[i - 1].normal) {
                G3C_Direct1(&info, G3OP_NORMAL, vertex->normal);
            }
        } else if (i == 0 || vertex->color != vertices[i - 1].color) {
            G3C_Color(&info, vertex->color);
        }

        G3C_TexCoord(&info, vertex->texCoord[0] * 256, vertex->texCoord[1] * 256);
        G3C_Vtx(&info, vertex->pos[0], vertex->pos[1], vertex->pos[2]);
    }

    G3C_End(&info);
    return G3_EndMakeDL(&info);
}

// The packed DL starts with one opcode word (TEXIMAGE_PARAM, PLTT_BASE, POLYGON_ATTR,
// BEGIN_VTXS), then their parameters, so POLYGON_ATTR's is word 3. Checked, so a changed
// layout only turns the fade off for that mesh (it then hides while fading).
static u16 FindAttrWord(const u32 *dl, u32 words, u32 attr)
{
    if (words > 4 && dl[3] == attr && ((dl[0] >> 16) & 0xFF) == G3OP_POLYGON_ATTR) {
        return 3;
    }

    return 0;
}

void BattleStage_BuildProjection(fx32 fovySin, fx32 fovyCos, fx32 nearClip, fx32 farClip, MtxFx44 *m)
{
    fx32 a = (STAGE_DEPTH_FAR - STAGE_DEPTH_NEAR) / 2;
    fx32 b = (STAGE_DEPTH_FAR + STAGE_DEPTH_NEAR) / 2;
    int farUnits = farClip >> FX32_SHIFT;
    int scaleW = farUnits > 0 ? 1024 / farUnits : 16;

    // A larger W keeps more bits in the squeezed depth; it doesn't move anything on screen
    if (scaleW < 1) {
        scaleW = 1;
    } else if (scaleW > 16) {
        scaleW = 16;
    }

    MTX_PerspectiveW(fovySin, fovyCos, FX32_ONE * 4 / 3, nearClip, farClip, scaleW * FX32_ONE, m);

    // z' = a * z + b * w, so NDC z lands in [STAGE_DEPTH_NEAR, STAGE_DEPTH_FAR]
    m->_02 = FX_Mul(a, m->_02) + FX_Mul(b, m->_03);
    m->_12 = FX_Mul(a, m->_12) + FX_Mul(b, m->_13);
    m->_22 = FX_Mul(a, m->_22) + FX_Mul(b, m->_23);
    m->_32 = FX_Mul(a, m->_32) + FX_Mul(b, m->_33);
}

// The home view; the debug views are poses of the stage camera
static void BuildView(StageArena *arena)
{
    VecFx32 up = { 0, FX32_ONE, 0 };

    MTX_LookAt(&arena->camPos, &up, &arena->camTarget, &arena->view);
}

static void BuildCamera(StageArena *arena, const BattleStageFileHeader *backdrop, const BattleStageFileHeader *platforms)
{
    VecFx32 up = { 0, FX32_ONE, 0 };
    VecFx32 look, right;
    int side;

    arena->camPos.x = backdrop->camPos[0];
    arena->camPos.y = backdrop->camPos[1];
    arena->camPos.z = backdrop->camPos[2];
    arena->camTarget.x = backdrop->camTarget[0];
    arena->camTarget.y = backdrop->camTarget[1];
    arena->camTarget.z = backdrop->camTarget[2];
    arena->fovySin = backdrop->fovySin;
    arena->fovyCos = backdrop->fovyCos;
    arena->nearClip = backdrop->nearClip;
    arena->farClip = backdrop->farClip;

    BattleStage_BuildProjection(arena->fovySin, arena->fovyCos, arena->nearClip, arena->farClip, &arena->projection);
    BuildView(arena);

    // Camera-right of the home camera, as in MTX_LookAt
    VEC_Subtract(&arena->camPos, &arena->camTarget, &look);
    VEC_CrossProduct(&up, &look, &right);
    VEC_Normalize(&right, &right);

    for (side = 0; side < 2; side++) {
        fx32 pixelToWorld = platforms->platformPixelToWorld[side];

        if (pixelToWorld == 0) {
            pixelToWorld = backdrop->platformPixelToWorld[side];
        }

        arena->platformStep[side].x = FX_Mul(right.x, pixelToWorld);
        arena->platformStep[side].y = FX_Mul(right.y, pixelToWorld);
        arena->platformStep[side].z = FX_Mul(right.z, pixelToWorld);
    }
}

static StageArena *BuildArena(BattleStageFileHeader **pieces, const u32 *sizes)
{
    StageArena *arena;
    u32 texOffsets[STAGE_MAX_TEXTURES];
    int textureBase[2];
    u32 texBytes = 0, dlBytes = 0, plttBytes = 0, texAddr;
    int numTextures = 0, numMeshes = 0;
    int p, i;

    for (p = 0; p < 2; p++) {
        const BattleStageFileTexture *textures = PieceData(pieces[p], pieces[p]->texturesOffset);
        const BattleStageFileMesh *meshes = PieceData(pieces[p], pieces[p]->meshesOffset);

        textureBase[p] = numTextures;

        if (numTextures + pieces[p]->numTextures > STAGE_MAX_TEXTURES || numMeshes + pieces[p]->numMeshes > STAGE_MAX_MESHES) {
            return NULL;
        }

        for (i = 0; i < pieces[p]->numTextures; i++) {
            texOffsets[numTextures++] = texBytes;
            texBytes += (TextureBytes(&textures[i]) + 7) & ~7;
        }

        for (i = 0; i < pieces[p]->numMeshes; i++) {
            dlBytes += MeshDLBound(&meshes[i]);
        }

        numMeshes += pieces[p]->numMeshes;
    }

    arena = Heap_Alloc(HEAP_ID_BATTLE, sizeof(StageArena));

    if (arena == NULL) {
        return NULL;
    }

    memset(arena, 0, sizeof(StageArena));
    arena->dlAlpha = STAGE_ALPHA_MAX;
    arena->dl = Heap_Alloc(HEAP_ID_BATTLE, dlBytes);

    if (arena->dl == NULL) {
        Heap_Free(arena);
        return NULL;
    }

    arena->texKey = NNS_GfdAllocTexVram(texBytes, FALSE, 0);
    texAddr = NNS_GfdGetTexKeyAddr(arena->texKey);
    GF_ASSERT(arena->texKey != NNS_GFD_ALLOC_ERROR_TEXKEY && texAddr + texBytes <= STAGE_TEX_VRAM_END);

    if (arena->texKey == NNS_GFD_ALLOC_ERROR_TEXKEY || texAddr + texBytes > STAGE_TEX_VRAM_END) {
        if (arena->texKey != NNS_GFD_ALLOC_ERROR_TEXKEY) {
            NNS_GfdFreeTexVram(arena->texKey);
        }

        Heap_Free(arena->dl);
        Heap_Free(arena);
        return NULL;
    }

    // Palette slots, seeded with the embedded palettes; the live ones are synced in Draw
    for (p = 0; p < 2; p++) {
        const BattleStageFileTexture *textures = PieceData(pieces[p], pieces[p]->texturesOffset);
        const BattleStageFileMesh *meshes = PieceData(pieces[p], pieces[p]->meshesOffset);

        for (i = 0; i < pieces[p]->numMeshes; i++) {
            const BattleStageFileTexture *texture = &textures[meshes[i].textureIndex];
            StagePalette *slot = &arena->palettes[PaletteSlot(texture, &meshes[i], SLOT_EMBEDDED + textureBase[p] + meshes[i].textureIndex)];
            u32 size;

            if (slot->numColors != 0) {
                continue;
            }

            slot->numColors = (slot == &arena->palettes[SLOT_BG] || texture->format == GX_TEXFMT_PLTT256) ? 256 : 16;
            slot->offset = plttBytes;
            plttBytes += slot->numColors * sizeof(u16);

            size = texture->paletteSize;

            if (size > slot->numColors * sizeof(u16)) {
                size = slot->numColors * sizeof(u16);
            }

            memcpy(slot->colors, PieceData(pieces[p], texture->paletteOffset), size);
        }
    }

    arena->plttKey = NNS_GfdAllocPlttVram(plttBytes, FALSE, 0);

    if (arena->plttKey == NNS_GFD_ALLOC_ERROR_PLTTKEY) {
        NNS_GfdFreeTexVram(arena->texKey);
        Heap_Free(arena->dl);
        Heap_Free(arena);
        return NULL;
    }

    arena->plttAddr = NNS_GfdGetPlttKeyAddr(arena->plttKey);

    GX_BeginLoadTex();

    for (p = 0; p < 2; p++) {
        const BattleStageFileTexture *textures = PieceData(pieces[p], pieces[p]->texturesOffset);

        DC_FlushRange(pieces[p], sizes[p]);

        for (i = 0; i < pieces[p]->numTextures; i++) {
            GX_LoadTex(PieceData(pieces[p], textures[i].dataOffset), texAddr + texOffsets[textureBase[p] + i], TextureBytes(&textures[i]));
        }
    }

    GX_EndLoadTex();

    DC_FlushRange(arena->palettes, sizeof(arena->palettes));
    GX_BeginLoadTexPltt();

    for (i = 0; i < SLOT_MAX; i++) {
        if (arena->palettes[i].numColors != 0) {
            GX_LoadTexPltt(arena->palettes[i].colors, arena->plttAddr + arena->palettes[i].offset, arena->palettes[i].numColors * sizeof(u16));
        }
    }

    GX_EndLoadTexPltt();

    dlBytes = 0;

    for (p = 0; p < 2; p++) {
        const BattleStageFileTexture *textures = PieceData(pieces[p], pieces[p]->texturesOffset);
        const BattleStageFileMesh *meshes = PieceData(pieces[p], pieces[p]->meshesOffset);

        for (i = 0; i < pieces[p]->numMeshes; i++) {
            const BattleStageFileMesh *mesh = &meshes[i];
            const BattleStageFileTexture *texture = &textures[mesh->textureIndex];
            int textureIndex = textureBase[p] + mesh->textureIndex;
            StageMesh *stageMesh = &arena->meshes[arena->numMeshes++];
            StagePalette *slot = &arena->palettes[PaletteSlot(texture, mesh, SLOT_EMBEDDED + textureIndex)];

            stageMesh->dlOffset = dlBytes;
            stageMesh->dlSize = BuildMeshDL(arena->dl + dlBytes / 4, MeshDLBound(mesh), pieces[p], mesh, texture, texAddr + texOffsets[textureIndex], arena->plttAddr + slot->offset, &stageMesh->attr);
            stageMesh->alpha = mesh->alpha;
            stageMesh->attrIndex = FindAttrWord(arena->dl + dlBytes / 4, stageMesh->dlSize / 4, stageMesh->attr);
            stageMesh->vertexScale = pieces[p]->vertexScale;
            stageMesh->flags = mesh->flags;
            stageMesh->scrollAmplitude[0] = mesh->scrollAmplitude[0];
            stageMesh->scrollAmplitude[1] = mesh->scrollAmplitude[1];
            stageMesh->scrollPeriod = mesh->scrollPeriod;
            dlBytes += stageMesh->dlSize;

            if (mesh->flags & (BATTLE_STAGE_MESH_FOLLOW_BG3_SCROLL | BATTLE_STAGE_MESH_SCROLL)) {
                arena->hasTexMtxMesh = TRUE;
            }

            if (mesh->flags & BATTLE_STAGE_MESH_LIT) {
                arena->hasLitMesh = TRUE;
            }
        }
    }

    DC_FlushRange(arena->dl, dlBytes);
    BuildCamera(arena, pieces[0], pieces[1]);

    // Copied, as the pieces are freed after the arena is built
    if (pieces[0]->atmosphereOffset != 0) {
        arena->hasAtmosphere = TRUE;
        arena->atmosphere = *(const BattleStageFileAtmosphere *)PieceData(pieces[0], pieces[0]->atmosphereOffset);
    }

    return arena;
}

static StageArena *LoadArena(BattleSystem *battleSys)
{
    enum BattleBackground background = BattleSystem_Background(battleSys);
    enum BattleTerrain terrain = BattleSystem_Terrain(battleSys);
    BattleStageFileHeader *pieces[2];
    u32 sizes[2];
    StageArena *arena = NULL;
    NARC *narc;

    if ((u32)background >= BACKGROUND_MAX || (u32)terrain >= TERRAIN_MAX) {
        return NULL;
    }

    narc = NARC_ctor(NARC_INDEX_BATTLE__GRAPHIC__BATTLE_STAGE, HEAP_ID_BATTLE);
    pieces[0] = LoadPiece(narc, background, TRUE, &sizes[0]);
    pieces[1] = LoadPiece(narc, BACKGROUND_MAX + terrain, FALSE, &sizes[1]);
    NARC_dtor(narc);

    if (pieces[0] != NULL && pieces[1] != NULL) {
        arena = BuildArena(pieces, sizes);
    }

    if (pieces[1] != NULL) {
        Heap_Free(pieces[1]);
    }

    if (pieces[0] != NULL) {
        Heap_Free(pieces[0]);
    }

    return arena;
}

static void FreeArena(StageArena *arena)
{
    NNS_GfdFreePlttVram(arena->plttKey);
    NNS_GfdFreeTexVram(arena->texKey);
    Heap_Free(arena->dl);
    Heap_Free(arena);
}

static void UpdatePlatforms(BOOL visible)
{
    int side;

    // Hidden every frame while the arena draws them, as the OBJs are created after Init
    // and some battle scripts toggle them; shown once when the arena goes away
    if (visible || sBattleStage.platformsHidden) {
        for (side = 0; side < 2; side++) {
            ov16_022686BC(ov16_0223E020(sBattleStage.battleSys, side), !visible);
        }
    }

    sBattleStage.platformsHidden = visible;
}

static void SyncPalette(StageArena *arena, StagePalette *slot, const u16 *source)
{
    u32 size = slot->numColors * sizeof(u16);

    if (size == 0) {
        return;
    }

    if (source != NULL && memcmp(slot->colors, source, size) != 0) {
        memcpy(slot->colors, source, size);
        slot->dirty = TRUE;
    }

    if (slot->dirty) {
        slot->dirty = !VramTransfer_Request(NNS_GFD_DST_3D_TEX_PLTT, arena->plttAddr + slot->offset, slot->colors, size);
    }
}

static const u16 *PlatformPalette(PaletteData *paletteSys, int side)
{
    int row = BattlePlatform_GetPaletteRow(ov16_0223E020(sBattleStage.battleSys, side));
    u16 *colors;

    if (row >= 0 && row < 16) {
        colors = PaletteData_GetFadedBuffer(paletteSys, PLTTBUF_MAIN_OBJ);

        if (colors != NULL) {
            return colors + row * 16;
        }
    }

    colors = PaletteData_GetFadedBuffer(paletteSys, PLTTBUF_MAIN_BG);
    return colors != NULL ? colors + STAGE_PLATFORM_BG_ROW * 16 : NULL;
}

static void SyncPalettes(StageArena *arena)
{
    PaletteData *paletteSys = BattleSystem_PaletteSys(sBattleStage.battleSys);
    int i;

    // Another screen may have used the palette VRAM while the arena was hidden
    if (!sBattleStage.wasVisible) {
        for (i = 0; i < SLOT_MAX; i++) {
            arena->palettes[i].dirty = TRUE;
        }
    }

    SyncPalette(arena, &arena->palettes[SLOT_BG], PaletteData_GetFadedBuffer(paletteSys, PLTTBUF_MAIN_BG));
    SyncPalette(arena, &arena->palettes[SLOT_PLATFORM_PLAYER], PlatformPalette(paletteSys, 0));
    SyncPalette(arena, &arena->palettes[SLOT_PLATFORM_ENEMY], PlatformPalette(paletteSys, 1));

    for (i = SLOT_EMBEDDED; i < SLOT_MAX; i++) {
        SyncPalette(arena, &arena->palettes[i], NULL);
    }
}

// Signed BG scroll in -period/2..period/2-1
static int WrapScroll(int offset, int period)
{
    offset &= period - 1;
    return offset >= period / 2 ? offset - period : offset;
}

static void SendDL(const u32 *dl, u32 size)
{
    if (GX_DMAID != GX_DMA_NOT_USE) {
        MI_SendGXCommand(GX_DMAID, dl, size);
    } else {
        MI_CpuSend32(dl, &reg_G3X_GXFIFO, size);
    }
}

// Time-of-day column of the atmosphere: 0 day, 1 twilight, 2 night
static int LightingColumn(void)
{
    int column = ov16_0223EC04(sBattleStage.battleSys);

    if (column < 0) {
        column = 0;
    } else if (column > 2) {
        column = 2;
    }

    return column;
}

// Material and light 0 of the LIT meshes (and the stage sprites) for the time of day
static const BattleStageFileLighting *CurrentLighting(StageArena *arena)
{
    return arena->hasAtmosphere ? &arena->atmosphere.lighting[LightingColumn()] : &sDefaultLighting;
}

// The same at day, whatever the time
static const BattleStageFileLighting *DayLighting(StageArena *arena)
{
    return arena->hasAtmosphere ? &arena->atmosphere.lighting[0] : &sDefaultLighting;
}

static void SetLight(StageArena *arena)
{
    const BattleStageFileLighting *lighting = CurrentLighting(arena);

    // Transformed by the current vector matrix (the view), so lightDir is in world space
    G3_LightVector(GX_LIGHTID_0, lighting->lightDir[0], lighting->lightDir[1], lighting->lightDir[2]);

    if (BackdropFadeActive()) {
        G3_LightColor(GX_LIGHTID_0, BackdropGrayColor(lighting->lightColor));
        G3_MaterialColorDiffAmb(BackdropGrayColor(lighting->diffuse), BackdropGrayColor(lighting->ambient), FALSE);
        G3_MaterialColorSpecEmi(GX_RGB(0, 0, 0), BackdropFadeEmission(lighting->emission), FALSE);
        return;
    }

    G3_LightColor(GX_LIGHTID_0, lighting->lightColor);
    G3_MaterialColorDiffAmb(lighting->diffuse, lighting->ambient, FALSE);
    G3_MaterialColorSpecEmi(GX_RGB(0, 0, 0), lighting->emission, FALSE);
}

// Texture matrix of a FOLLOW_BG3_SCROLL and/or SCROLL mesh, in texels << 16
static void SetTexMtx(StageArena *arena, const StageMesh *mesh, int bg3X, int bg3Y)
{
    fx32 s = 0, t = 0;

    // Texel (s, t) shows at the screen pixel BG3 would show it at
    if (mesh->flags & BATTLE_STAGE_MESH_FOLLOW_BG3_SCROLL) {
        s = bg3X << 16;
        t = bg3Y << 16;
    }

    if (mesh->flags & BATTLE_STAGE_MESH_SCROLL) {
        u16 index = (u32)(arena->frame % mesh->scrollPeriod) * 0x10000 / mesh->scrollPeriod;

        s += mesh->scrollAmplitude[0] * FX_SinIdx(index) * 16;
        t += mesh->scrollAmplitude[1] * FX_SinIdx((u16)(index * 2)) * 16;
    }

    G3_MtxMode(GX_MTXMODE_TEXTURE);
    G3_Identity();
    G3_Translate(s, t, 0);
    G3_MtxMode(GX_MTXMODE_POSITION_VECTOR);
}

static void DrawArena(StageArena *arena, const MtxFx43 *view, const MtxFx44 *projection)
{
    int platformOffset[2];
    int bg3X = 0, bg3Y = 0;
    int side, i;

    for (side = 0; side < 2; side++) {
        platformOffset[side] = BattlePlatform_GetOffsetX(ov16_0223E020(sBattleStage.battleSys, side));
    }

    NNS_G3dGeFlushBuffer();

    G3_MtxMode(GX_MTXMODE_PROJECTION);
    G3_PushMtx();
    G3_LoadMtx44(projection);

    if (arena->hasTexMtxMesh) {
        BgConfig *bgConfig = BattleSystem_BGL(sBattleStage.battleSys);

        bg3X = WrapScroll(Bg_GetXOffset(bgConfig, BG_LAYER_MAIN_3), 512);
        bg3Y = WrapScroll(Bg_GetYOffset(bgConfig, BG_LAYER_MAIN_3), 256);

        G3_MtxMode(GX_MTXMODE_TEXTURE);
        G3_PushMtx();
    }

    G3_MtxMode(GX_MTXMODE_POSITION_VECTOR);
    G3_PushMtx();
    G3_LoadMtx43(view);

    if (arena->hasLitMesh) {
        SetLight(arena);
    }

    for (i = 0; i < arena->numMeshes; i++) {
        StageMesh *mesh = &arena->meshes[i];

        // A mesh whose alpha can't be patched sits the fade out
        if (arena->dlAlpha < STAGE_ALPHA_MAX && mesh->attrIndex == 0) {
            continue;
        }

        if (mesh->flags & (BATTLE_STAGE_MESH_FOLLOW_BG3_SCROLL | BATTLE_STAGE_MESH_SCROLL)) {
            SetTexMtx(arena, mesh, bg3X, bg3Y);
        }

        G3_PushMtx();

        if (mesh->flags & (BATTLE_STAGE_MESH_FOLLOW_PLATFORM_PLAYER | BATTLE_STAGE_MESH_FOLLOW_PLATFORM_ENEMY)) {
            side = (mesh->flags & BATTLE_STAGE_MESH_FOLLOW_PLATFORM_PLAYER) ? 0 : 1;
            G3_Translate(arena->platformStep[side].x * platformOffset[side], arena->platformStep[side].y * platformOffset[side], arena->platformStep[side].z * platformOffset[side]);
        }

        // The scale only goes to the position matrix, so the normals stay unit length
        G3_Scale(mesh->vertexScale, mesh->vertexScale, mesh->vertexScale);
        SendDL(arena->dl + mesh->dlOffset / 4, mesh->dlSize);
        G3_PopMtx(1);
    }

    // With the view still loaded
    BattleStageSprites_DrawBlobs(projection);
    G3_PopMtx(1);

    if (arena->hasTexMtxMesh) {
        G3_MtxMode(GX_MTXMODE_TEXTURE);
        G3_PopMtx(1);
    }

    G3_MtxMode(GX_MTXMODE_PROJECTION);
    G3_PopMtx(1);
    G3_MtxMode(GX_MTXMODE_POSITION);
    G3_Color(GX_RGB(31, 31, 31));

    arena->frame++;
}

// NDC x of the left edge of screen column x
static fx16 CurtainX(int x)
{
    return (fx16)(x * FX16_ONE * 2 / HW_LCD_WIDTH - FX16_ONE);
}

static void DrawCurtainBar(int left, int right)
{
    if (left >= right) {
        return;
    }

    G3_Vtx(CurtainX(left), FX16_ONE, STAGE_CURTAIN_DEPTH);
    G3_Vtx(CurtainX(left), -FX16_ONE, STAGE_CURTAIN_DEPTH);
    G3_Vtx(CurtainX(right), -FX16_ONE, STAGE_CURTAIN_DEPTH);
    G3_Vtx(CurtainX(right), FX16_ONE, STAGE_CURTAIN_DEPTH);
}

// After the arena, before the sprites: the curtain bars cover the arena outside
// curtainLeft..curtainRight with a flat colour, under the mons, as the classic Fake Out
// window cuts BG3 to the backdrop colour around them. The colour is read from BG palette
// VRAM each frame, so it follows a palette fade as the 2D backdrop does; no fog, so it is
// exact. It fades with the arena (alpha 0 would draw a wireframe).
static void DrawCurtain(int alpha)
{
    if (!sBattleStage.curtainOn || alpha == 0 || (sBattleStage.curtainLeft == 0 && sBattleStage.curtainRight == HW_LCD_WIDTH)) {
        return;
    }

    G3_MtxMode(GX_MTXMODE_PROJECTION);
    G3_PushMtx();
    G3_Identity();
    G3_MtxMode(GX_MTXMODE_POSITION_VECTOR);
    G3_PushMtx();
    G3_Identity();

    G3_TexImageParam(GX_TEXFMT_NONE, GX_TEXGEN_NONE, GX_TEXSIZE_S8, GX_TEXSIZE_T8, GX_TEXREPEAT_NONE, GX_TEXFLIP_NONE, GX_TEXPLTTCOLOR0_USE, 0);
    G3_PolygonAttr(GX_LIGHTMASK_NONE, GX_POLYGONMODE_MODULATE, GX_CULL_NONE, STAGE_CURTAIN_POLYGON_ID, alpha, 0);
    G3_Color(*(const u16 *)HW_BG_PLTT & GX_RGB(31, 31, 31));
    G3_Begin(GX_BEGIN_QUADS);
    DrawCurtainBar(0, sBattleStage.curtainLeft);
    DrawCurtainBar(sBattleStage.curtainRight, HW_LCD_WIDTH);
    G3_End();

    G3_PopMtx(1);
    G3_MtxMode(GX_MTXMODE_PROJECTION);
    G3_PopMtx(1);
    G3_MtxMode(GX_MTXMODE_POSITION);
    G3_Color(GX_RGB(31, 31, 31));
}

static void FogOff(void)
{
    if (sStageFog.on) {
        G3X_SetFog(FALSE, GX_FOGBLEND_COLOR_ALPHA, GX_FOGSLOPE_0x8000, 0);
        sStageFog.on = FALSE;
    }
}

// Written from the main loop like the rest of the 3D state (as the field fog does), right
// after the arena's geometry; the 2D brightness blend that the brightness follows is also
// written from the main loop, so both change on the same frame
static void UpdateFog(StageArena *arena)
{
    u32 table[8];
    GXRgb color;
    int alpha, shift, offset;

    if (sBattleStage.brightness != 0) {
        int magnitude = sBattleStage.brightness < 0 ? -sBattleStage.brightness : sBattleStage.brightness;
        u32 density = magnitude * 8 > 127 ? 127 : magnitude * 8;
        int i;

        // (fog * d + pixel * (128 - d)) / 128 is the 2D brightness formula at d = |b| * 8
        color = sBattleStage.brightness < 0 ? GX_RGB(0, 0, 0) : GX_RGB(31, 31, 31);
        alpha = 31;
        shift = GX_FOGSLOPE_0x8000;
        offset = 0;

        for (i = 0; i < 8; i++) {
            table[i] = density * 0x01010101;
        }
    } else if (arena->hasAtmosphere && arena->atmosphere.fogEnabled) {
        const BattleStageFileLighting *lighting = &arena->atmosphere.lighting[LightingColumn()];

        // The fog stands for the backdrop's distance, so it fades with the backdrop
        color = BackdropFadeActive() ? BackdropFadeColor(lighting->fogColor) : lighting->fogColor;
        alpha = lighting->fogAlpha;
        shift = arena->atmosphere.fogShift;
        offset = arena->atmosphere.fogOffset;
        memcpy(table, arena->atmosphere.fogTable, sizeof(table));
    } else {
        FogOff();
        return;
    }

    // Another screen may have used the fog table while the arena was hidden
    if (!sBattleStage.wasVisible) {
        sStageFog.tableValid = FALSE;
    }

    G3X_SetFog(TRUE, GX_FOGBLEND_COLOR_ALPHA, (GXFogSlope)shift, offset);
    G3X_SetFogColor(color, alpha);

    if (!sStageFog.tableValid || memcmp(sStageFog.table, table, sizeof(table)) != 0) {
        memcpy(sStageFog.table, table, sizeof(table));
        G3X_SetFogTable(sStageFog.table);
        sStageFog.tableValid = TRUE;
    }

    sStageFog.on = TRUE;
}
