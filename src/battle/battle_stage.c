#include "battle/battle_stage.h"
#include "battle/battle_bdsp_cam.h"
#include "battle/battle_bdsp_trainer.h"

#include <math.h>
#include <nitro.h>
#include <nnsys.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "config/battle_stage.h"
#include "constants/battle.h"
#include "constants/graphics.h"
#include "constants/heap.h"
#include "constants/moves.h"
#include "constants/narc.h"
#include "constants/overworld_weather.h"

#include "battle/battle_context.h"
#include "battle/battle_stage_camera.h"
#include "battle/battle_stage_format.h"
#include "battle/battle_stage_sprites.h"
#include "battle/battle_system.h"
#include "battle/terrain.h"
#include "battle_anim/ov12_022380BC.h"

#include "bg_window.h"
#include "fx_arena.h"
#include "heap.h"
#include "move_table.h"
#include "narc.h"
#include "palette.h"
#include "pokemon_sprite.h"
#include "port/postfx.h"
#include "port/sim_battle3d.h"
#ifdef SDK_PORT
#include "port/sim_wide.h"
#endif
#include "vram_transfer.h"

extern void BattleStageCamera_GetBdspDeltas(float *yawDeg, float *pitchDeg, float *distScale, float *fovScale, float *shakeX, float *shakeY, int *isIdle);

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
    // Lane arena: per-channel arena tint (1/256) and the atmosphere lighting
    // with it applied. Feature off: 256, 256, 256 and the lighting copy is
    // the atmosphere lighting unchanged. After every other field, so the
    // critic's offsets above do not move.
    int arenaTint[3];
    BattleStageFileLighting tintedLighting;
    // Lane arena: this frame's lightning flash brightness, 0..16, separate
    // from brightness (the Mega pulse channel the critic reads). UpdateFog
    // uses the larger of the two, so a flash whitens the arena without
    // clobbering a Mega pulse's value.
    int lightningBrightness;
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
static void UpdateArenaTint(void);
static void UpdateBattleLightning(void);
static const BattleStageFileLighting *DayLighting(StageArena *arena);
static void UpdateFog(StageArena *arena);
static void FogOff(void);
static void UpdateFade(void);
static void PatchArenaAlpha(StageArena *arena, int alpha);
static void UpdateFadeBlend(BOOL translucent);
static void DrawCurtain(int alpha);
static void SubmitBdspFrame(void);
static void ResetBdspAnimState(void);
static void BdspDumpInit(void);
static void BdspDumpClose(void);

#define BDSP_ANIM_DT         (1.0f / 60.0f)
#define BDSP_ANIM_BLEND_DUR  0.15f
#define BDSP_ANIM_CRY_DUR    3.20f
#define BDSP_ANIM_ATTACK_DUR 2.35f
#define BDSP_ANIM_HIT_DUR    1.20f
#define BDSP_ANIM_FAINT_HOLD 1.65f

typedef struct BdspBattlerAnim {
    int species;
    int form;
    int isShiny;
    BOOL wasVisible;
    BOOL hitFlickering;
    BOOL justTriggered;
    int animState;
    float animTime;
    float animDuration; // 0.0f = looping (IDLE) or hold end frame (FAINT)
    int animNonce;
} BdspBattlerAnim;

static BattleStage sBattleStage;
static StageFog sStageFog;
static BdspBattlerAnim sBdspAnim[SIM_BATTLE3D_MAX_BATTLERS];

#ifdef SDK_PORT
typedef struct BdspDumpSlot {
    int visible;
    int species;
    int form;
    int isShiny;
    int use3dModel;
    int animState;
    int animNonce;
    int postChangeFrames;
} BdspDumpSlot;

static FILE *sBdspDumpFile;
static BOOL sBdspDumpOpenedOnce;
static BdspDumpSlot sBdspDumpPrev[SIM_BATTLE3D_MAX_BATTLERS];
#endif

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
    sBattleStage.lightningBrightness = 0;
    sBattleStage.backdropFadeColor = 0;
    sBattleStage.backdropFadeAlpha = 0;
    sBattleStage.backdropGrayscale = FALSE;
    sStageFog.on = TRUE; // unknown, so FogOff writes it
    sStageFog.tableValid = FALSE;
    FogOff();
    ResetBdspAnimState();
    BdspDumpInit();

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

    UpdateArenaTint();

    // Lightning restarts with each battle, seeded from the battle's own
    // context (clock, weather, place), so the flashes are deterministic for
    // the same battle.
    if (FxArena_WeatherLightningEnabled() && sBattleStage.battleSys != NULL) {
        u32 seed = (u32)(BattleSystem_GetFieldHour(battleSys) * 3600 + BattleSystem_GetFieldMinute(battleSys) * 60)
            + (u32)BattleSystem_GetFieldWeather(battleSys) * 1000003u
            + (u32)BattleSystem_GetBackground(battleSys) * 9176u
            + (u32)BattleSystem_GetTerrain(battleSys) * 131u;
        FxArena_LightningReset(seed);
    }

}

void BattleStage_Free(void)
{
    SIM_Battle3D_Reset();
    ResetBdspAnimState();
    BdspDumpClose();
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
    sBattleStage.lightningBrightness = 0;
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

    if (sBattleStage.battleSys != NULL) {
        UpdateArenaTint();
        UpdateBattleLightning();
    }

    if (sBattleStage.battleSys == NULL || sBattleStage.arena == NULL) {
        SIM_Battle3D_Reset();
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

    BattleStageSprites_BeginFrame(visible, &sBattleStage.tintedLighting, DayLighting(sBattleStage.arena), view);
    UpdatePlatforms(visible);

    if (SIM_Battle3D_IsEnabled()) {
        if (visible && sBattleStage.fadePos > 0) {
            int alpha = STAGE_ALPHA_MAX * sBattleStage.fadePos / STAGE_FADE_STEPS;

            SubmitBdspFrame();
            DrawCurtain(alpha);
            FogOff();
            sBattleStage.compat.arenaAlpha = alpha;
        } else {
            SIM_Battle3D_Reset();
            FogOff();
            sBattleStage.compat.arenaAlpha = 0;

            if (sBattleStage.enabled) {
                sBattleStage.compat.hiddenFrames++;
            }
        }
    } else if (visible) {
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
            SIM_Battle3D_Reset();
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

BOOL BattleStage_KeepsTextureVram(void)
{
    return sBattleStage.battleSys != NULL
        && sBattleStage.arena != NULL
        && (sBattleStage.suppressed & BATTLE_STAGE_SUPPRESS_MENU) == 0;
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

    // Wide layout (wide-OUT/API.md): the battle arena renders at the wide
    // aspect; battler sprite anchors are projected through this same
    // matrix (battle_stage_camera.c), so sprites stay on their platforms.
    // Not wide: exactly the classic 4/3, byte-identical at the home pose.
    fx32 aspect = FX32_ONE * 4 / 3;
#ifdef SDK_PORT
    aspect = SIM_Wide_AspectRatio();
#endif
    MTX_PerspectiveW(fovySin, fovyCos, aspect, nearClip, farClip, scaleW * FX32_ONE, m);

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
    enum BattleBackground background = BattleSystem_GetBackground(battleSys);
    enum BattleTerrain terrain = BattleSystem_GetTerrain(battleSys);
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
            Terrain_SetVisibility(BattleSystem_GetTerrainForSide(sBattleStage.battleSys, side), !visible);
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
    int row = BattlePlatform_GetPaletteRow(BattleSystem_GetTerrainForSide(sBattleStage.battleSys, side));
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
    PaletteData *paletteSys = BattleSystem_GetPaletteData(sBattleStage.battleSys);
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

// A GX_RGB colour with each channel scaled by tint[c] / 256, clamped to 31
static u16 TintColor(u16 color, const int tint[3])
{
    int r = ((color >> 0) & 31) * tint[0] / 256;
    int g = ((color >> 5) & 31) * tint[1] / 256;
    int b = ((color >> 10) & 31) * tint[2] / 256;

    if (r > 31) {
        r = 31;
    }
    if (g > 31) {
        g = 31;
    }
    if (b > 31) {
        b = 31;
    }

    return (u16)GX_RGB(r, g, b);
}

// Lane arena: the arena lighting with the exact-time / weather / terrain
// tint applied (battle_stage.h, BattleStage_GetSpriteTint follows it, so 2D
// copies get the same tint). With the feature off the tint is neutral and
// the copy is the atmosphere lighting unchanged.
static void UpdateArenaTint(void)
{
    const BattleStageFileLighting *base;
    BattleSystem *battleSys = sBattleStage.battleSys;

    if (sBattleStage.arena != NULL) {
        base = CurrentLighting(sBattleStage.arena);
    } else {
        base = &sDefaultLighting;
    }

    sBattleStage.tintedLighting = *base;

    if (battleSys != NULL && FxArena_ArenaContextEnabled()) {
        FxArena_ArenaTint(BattleSystem_GetFieldHour(battleSys), BattleSystem_GetFieldMinute(battleSys),
            BattleSystem_GetFieldWeather(battleSys), BattleSystem_GetTerrain(battleSys),
            BattleSystem_GetBackground(battleSys), &sBattleStage.arenaTint[0], &sBattleStage.arenaTint[1], &sBattleStage.arenaTint[2]);
    } else {
        sBattleStage.arenaTint[0] = 256;
        sBattleStage.arenaTint[1] = 256;
        sBattleStage.arenaTint[2] = 256;
    }

    sBattleStage.tintedLighting.lightColor = TintColor(base->lightColor, sBattleStage.arenaTint);
    sBattleStage.tintedLighting.diffuse = TintColor(base->diffuse, sBattleStage.arenaTint);
    sBattleStage.tintedLighting.ambient = TintColor(base->ambient, sBattleStage.arenaTint);
    sBattleStage.tintedLighting.emission = TintColor(base->emission, sBattleStage.arenaTint);
    sBattleStage.tintedLighting.fogColor = TintColor(base->fogColor, sBattleStage.arenaTint);
}

// Lane arena: one lightning-scheduler step per drawn frame. The flash is a
// PostFX glow, so it needs no simulator change and never touches the Mega
// pulse's BattleStage_SetBrightness.
static void UpdateBattleLightning(void)
{
    int strength;

    if (!FxArena_WeatherLightningEnabled() || sBattleStage.battleSys == NULL) {
        return;
    }

    strength = FxArena_LightningUpdate(BattleSystem_GetFieldWeather(sBattleStage.battleSys));

    // The arena fog flash (UpdateFog reads this) is the part the player
    // sees: PostFX glow alone only lifts pixels above 0.55, nearly
    // invisible in a dark storm scene.
    // Max 10/16: a full-white arena for a frame reads as a camera flash,
    // not lightning, and strobes. 10/16 is a strong but readable flash.
    sBattleStage.lightningBrightness = strength * 10 / 256;

    if (strength > 0) {
        PostFX_Glow((float)strength / 256.0f * 0.9f, 2);
        PostFX_Vignette(1.0f, 1.0f, 1.0f, (float)strength / 256.0f * 0.35f, 2);
    }
}

// Time-of-day column of the atmosphere: 0 day, 1 twilight, 2 night
static int LightingColumn(void)
{
    int column = BattleSystem_GetBackgroundTimeOffset(sBattleStage.battleSys);

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
    const BattleStageFileLighting *lighting = &sBattleStage.tintedLighting;

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
        s = (fx32)((u32)bg3X << 16);
        t = (fx32)((u32)bg3Y << 16);
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
        platformOffset[side] = BattlePlatform_GetOffsetX(BattleSystem_GetTerrainForSide(sBattleStage.battleSys, side));
    }

    NNS_G3dGeFlushBuffer();

    G3_MtxMode(GX_MTXMODE_PROJECTION);
    G3_PushMtx();
    G3_LoadMtx44(projection);

    if (arena->hasTexMtxMesh) {
        BgConfig *bgConfig = BattleSystem_GetBgConfig(sBattleStage.battleSys);

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

    // A lightning flash whitens the arena through the fog, like the
    // Mega pulse does, without touching the pulse's own brightness value:
    // the larger of the two wins for this frame.
    if (sBattleStage.brightness != 0 || sBattleStage.lightningBrightness != 0) {
        int brightness = sBattleStage.brightness;
        int magnitude;
        u32 density;
        int i;

        // Only while a flash is active: lightning 0 must never cancel a
        // Mega dim (a negative brightness).
        if (sBattleStage.lightningBrightness > 0 && sBattleStage.lightningBrightness > brightness) {
            brightness = sBattleStage.lightningBrightness;
        }

        magnitude = brightness < 0 ? -brightness : brightness;
        density = magnitude * 8 > 127 ? 127 : magnitude * 8;

        // (fog * d + pixel * (128 - d)) / 128 is the 2D brightness formula at d = |b| * 8
        color = brightness < 0 ? GX_RGB(0, 0, 0) : GX_RGB(31, 31, 31);
        alpha = 31;
        shift = GX_FOGSLOPE_0x8000;
        offset = 0;

        for (i = 0; i < 8; i++) {
            table[i] = density * 0x01010101;
        }
    } else if (arena->hasAtmosphere && arena->atmosphere.fogEnabled) {
        const BattleStageFileLighting *lighting = &sBattleStage.tintedLighting;

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

static int BdspTimeOfDay(BattleSystem *battleSys)
{
    int offset = BattleSystem_GetBackgroundTimeOffset(battleSys);

    if (offset <= 0) {
        int hour = BattleSystem_GetFieldHour(battleSys);
        if (hour >= 4 && hour < 10) {
            return SIM_BATTLE3D_TOD_MORNING;
        }
        return SIM_BATTLE3D_TOD_DAY;
    }
    if (offset == 1) {
        return SIM_BATTLE3D_TOD_EVENING;
    }
    return SIM_BATTLE3D_TOD_NIGHT;
}

static int BdspWeather(BattleSystem *battleSys)
{
    BattleContext *battleCtx = BattleSystem_GetBattleContext(battleSys);
    int fieldWeather;

    if (battleCtx != NULL) {
        u32 cond = battleCtx->fieldConditionsMask;
        if (cond & FIELD_CONDITION_RAINING) {
            return SIM_BATTLE3D_WEATHER_RAIN;
        }
        if (cond & FIELD_CONDITION_SUNNY) {
            return SIM_BATTLE3D_WEATHER_SUN;
        }
        if (cond & FIELD_CONDITION_HAILING) {
            return SIM_BATTLE3D_WEATHER_HAIL;
        }
        if (cond & FIELD_CONDITION_SANDSTORM) {
            return SIM_BATTLE3D_WEATHER_SAND;
        }
        if (cond & FIELD_CONDITION_DEEP_FOG) {
            return SIM_BATTLE3D_WEATHER_FOG;
        }
    }

    fieldWeather = BattleSystem_GetFieldWeather(battleSys);
    switch (fieldWeather) {
    case OVERWORLD_WEATHER_RAINING:
    case OVERWORLD_WEATHER_HEAVY_RAIN:
    case OVERWORLD_WEATHER_THUNDERSTORM:
        return SIM_BATTLE3D_WEATHER_RAIN;
    case OVERWORLD_WEATHER_HARSH_SUN:
        return SIM_BATTLE3D_WEATHER_SUN;
    case OVERWORLD_WEATHER_SNOWING:
    case OVERWORLD_WEATHER_HEAVY_SNOW:
    case OVERWORLD_WEATHER_BLIZZARD:
    case OVERWORLD_WEATHER_HAILING:
        return SIM_BATTLE3D_WEATHER_HAIL;
    case OVERWORLD_WEATHER_SANDSTORM:
        return SIM_BATTLE3D_WEATHER_SAND;
    case OVERWORLD_WEATHER_FOG:
    case OVERWORLD_WEATHER_DEEP_FOG:
    case OVERWORLD_WEATHER_RIFT_MIST:
        return SIM_BATTLE3D_WEATHER_FOG;
    default:
        return SIM_BATTLE3D_WEATHER_CLEAR;
    }
}

static void ResetBdspAnimState(void)
{
    memset(sBdspAnim, 0, sizeof(sBdspAnim));
    BattleBdspCam_Reset();
    BattleBdspTrainer_Reset();
}

static void SetBdspAnim(int battler, int animState, float duration)
{
    BdspBattlerAnim *st;

    if (battler < 0 || battler >= SIM_BATTLE3D_MAX_BATTLERS) {
        return;
    }

    st = &sBdspAnim[battler];
    st->animState = animState;
    st->animTime = 0.0f;
    st->animDuration = duration;
    st->animNonce++;
    st->justTriggered = TRUE;
}

void BattleStage_NotifyBdspCry(int battler)
{
    BdspBattlerAnim *st;

    if (battler < 0 || battler >= SIM_BATTLE3D_MAX_BATTLERS) {
        return;
    }

    st = &sBdspAnim[battler];
    if (st->animState == SIM_BATTLE3D_ANIM_FAINT) {
        return;
    }
    if (st->animState == SIM_BATTLE3D_ANIM_CRY && st->animTime < 0.35f) {
        return;
    }

    SetBdspAnim(battler, SIM_BATTLE3D_ANIM_CRY, BDSP_ANIM_CRY_DUR);
}

void BattleStage_NotifyBdspAttack(int battler, u16 move)
{
    u32 moveClass;
    int state;

    if (battler < 0 || battler >= SIM_BATTLE3D_MAX_BATTLERS || move == MOVE_NONE) {
        return;
    }
    if (sBdspAnim[battler].animState == SIM_BATTLE3D_ANIM_FAINT) {
        return;
    }

    moveClass = MoveTable_LoadParam(move, MOVEATTRIBUTE_CLASS);
    state = (moveClass == CLASS_PHYSICAL) ? SIM_BATTLE3D_ANIM_ATTACK_PHYS : SIM_BATTLE3D_ANIM_ATTACK_SPEC;
    SetBdspAnim(battler, state, BDSP_ANIM_ATTACK_DUR);
    BattleBdspCam_NotifyAttack(battler, move);
}

void BattleStage_NotifyBdspHit(int battler)
{
    if (battler < 0 || battler >= SIM_BATTLE3D_MAX_BATTLERS) {
        return;
    }
    if (sBdspAnim[battler].animState == SIM_BATTLE3D_ANIM_FAINT) {
        return;
    }

    sBdspAnim[battler].hitFlickering = TRUE;
    SetBdspAnim(battler, SIM_BATTLE3D_ANIM_HIT, BDSP_ANIM_HIT_DUR);
    BattleBdspCam_NotifyHit(battler);
}

void BattleStage_NotifyBdspHitEnd(int battler)
{
    if (battler < 0 || battler >= SIM_BATTLE3D_MAX_BATTLERS) {
        return;
    }

    sBdspAnim[battler].hitFlickering = FALSE;
}

void BattleStage_NotifyBdspFaint(int battler)
{
    if (battler < 0 || battler >= SIM_BATTLE3D_MAX_BATTLERS) {
        return;
    }

    sBdspAnim[battler].hitFlickering = FALSE;
    SetBdspAnim(battler, SIM_BATTLE3D_ANIM_FAINT, 0.0f);
    BattleBdspCam_NotifyFaint(battler);
}

BOOL BattleStage_IsBattler3DModel(BattleSystem *battleSys, int battler)
{
    BattleContext *ctx;

    if (battleSys == NULL || battler < 0 || battler >= SIM_BATTLE3D_MAX_BATTLERS) {
        return FALSE;
    }
    if (!SIM_Battle3D_ModelsEnabled()) {
        return FALSE;
    }
    ctx = BattleSystem_GetBattleContext(battleSys);
    if (ctx == NULL) {
        return FALSE;
    }
    return SIM_Battle3D_HasModelLoaded(
        ctx->battleMons[battler].species,
        ctx->battleMons[battler].formNum,
        ctx->battleMons[battler].isShiny
    );
}

static const char *BdspAnimStateName(int state)
{
    switch (state) {
    case SIM_BATTLE3D_ANIM_IDLE:
        return "IDLE";
    case SIM_BATTLE3D_ANIM_ATTACK_PHYS:
        return "ATTACK_PHYS";
    case SIM_BATTLE3D_ANIM_ATTACK_SPEC:
        return "ATTACK_SPEC";
    case SIM_BATTLE3D_ANIM_HIT:
        return "HIT";
    case SIM_BATTLE3D_ANIM_FAINT:
        return "FAINT";
    case SIM_BATTLE3D_ANIM_CRY:
        return "CRY";
    default:
        return "UNKNOWN";
    }
}

static void BdspDumpInit(void)
{
#ifdef SDK_PORT
    const char *path = getenv("SIM_BATTLE3D_DUMP");
    int i;

    if (sBdspDumpFile != NULL) {
        fclose(sBdspDumpFile);
        sBdspDumpFile = NULL;
    }

    for (i = 0; i < SIM_BATTLE3D_MAX_BATTLERS; i++) {
        sBdspDumpPrev[i].visible = -1;
        sBdspDumpPrev[i].species = -1;
        sBdspDumpPrev[i].form = -1;
        sBdspDumpPrev[i].isShiny = -1;
        sBdspDumpPrev[i].use3dModel = -1;
        sBdspDumpPrev[i].animState = -1;
        sBdspDumpPrev[i].animNonce = -1;
        sBdspDumpPrev[i].postChangeFrames = 0;
    }

    if (path != NULL && path[0] != '\0') {
        sBdspDumpFile = fopen(path, sBdspDumpOpenedOnce ? "a" : "w");
        if (sBdspDumpFile != NULL) {
            sBdspDumpOpenedOnce = TRUE;
            fprintf(sBdspDumpFile, "# battle_init\n");
            fflush(sBdspDumpFile);
        }
    }
#endif
}

static void BdspDumpClose(void)
{
#ifdef SDK_PORT
    if (sBdspDumpFile != NULL) {
        fprintf(sBdspDumpFile, "# battle_free\n");
        fclose(sBdspDumpFile);
        sBdspDumpFile = NULL;
    }
#endif
}

static void BdspDumpFrame(u32 frameNum, const SIM_Battle3DFrame *frame, BattleSystem *battleSys, int maxBattlers)
{
#ifdef SDK_PORT
    int i;

    if (sBdspDumpFile == NULL || frame == NULL) {
        return;
    }

    for (i = 0; i < maxBattlers && i < SIM_BATTLE3D_MAX_BATTLERS; i++) {
        const SIM_Battle3DBattler *b = &frame->battlers[i];
        BdspDumpSlot *prev = &sBdspDumpPrev[i];
        BOOL changed = (prev->visible != b->visible
            || prev->species != b->species
            || prev->form != b->form
            || prev->isShiny != b->isShiny
            || prev->use3dModel != b->use3dModel
            || prev->animState != b->animState
            || prev->animNonce != b->animNonce);

        if (changed || prev->postChangeFrames > 0) {
            int btype = BattleSystem_GetBattlerType(battleSys, i);
            fprintf(sBdspDumpFile,
                "frame=%u time=%.4f biome=%d slot=%d btype=%d vis=%d species=%d form=%d shiny=%d use3d=%d pos=(%.2f,%.2f,%.2f) yaw=%.1f scale=%.2f anim=%s(%d) animTime=%.4f nonce=%d\n",
                (unsigned)frameNum,
                frame->timeSec,
                frame->biome,
                i,
                btype,
                b->visible,
                b->species,
                b->form,
                b->isShiny,
                b->use3dModel,
                b->worldX,
                b->worldY,
                b->worldZ,
                b->yawDeg,
                b->modelScale,
                BdspAnimStateName(b->animState),
                b->animState,
                b->animTime,
                b->animNonce);
            fflush(sBdspDumpFile);

            if (changed) {
                prev->visible = b->visible;
                prev->species = b->species;
                prev->form = b->form;
                prev->isShiny = b->isShiny;
                prev->use3dModel = b->use3dModel;
                prev->animState = b->animState;
                prev->animNonce = b->animNonce;
                prev->postChangeFrames = b->visible ? 1 : 0;
            } else {
                prev->postChangeFrames--;
            }
        }
    }
#else
    (void)frameNum;
    (void)frame;
    (void)battleSys;
    (void)maxBattlers;
#endif
}

static BOOL BdspIsSubstituteDoll(const PokemonSprite *spr)
{
    return spr != NULL && spr->active
        && spr->template.narcID == NARC_INDEX_POKETOOL__POKEGRA__PL_OTHERPOKE
        && (spr->template.character == SUBSTITUTE_BACK_NCGR || spr->template.character == SUBSTITUTE_FRONT_NCGR);
}

static void SubmitBdspFrame(void)
{
    BattleSystem *battleSys = sBattleStage.battleSys;
    BattleContext *battleCtx;
    StageArena *arena = sBattleStage.arena;
    SIM_Battle3DFrame frame;
    float alpha;
    float timeSec;
    u32 frameNum;
    float yawDeg = 0.0f;
    float pitchDeg = 0.0f;
    float distScale = 1.0f;
    float fovScale = 1.0f;
    float shakeX = 0.0f;
    float shakeY = 0.0f;
    int isIdle = 1;
    int br;
    float baseEye[3] = { -3.6f, 2.35f, 8.4f };
    float baseTarget[3] = { 0.5f, 1.35f, -1.8f };
    float baseFov = 36.0f;
    BOOL heightSizing = BattleStageSprites_IsHeightSizingEnabled();
    BOOL slotHas3d[SIM_BATTLE3D_MAX_BATTLERS];
    int slotSpecies[SIM_BATTLE3D_MAX_BATTLERS];
    int slotForm[SIM_BATTLE3D_MAX_BATTLERS];
    int slotShiny[SIM_BATTLE3D_MAX_BATTLERS];
    BOOL any3dModel = FALSE;
    float off[3];
    float target[3];
    float eye[3];
    float yawRad, pitchRad, cosY, sinY, cosP, sinP;
    PokemonSpriteManager *monSpriteMan;
    int maxBattlers;
    int i;

    if (battleSys == NULL || arena == NULL) {
        SIM_Battle3D_Reset();
        return;
    }

    alpha = (float)sBattleStage.fadePos / (float)STAGE_FADE_STEPS;
    if (alpha <= 0.0f) {
        SIM_Battle3D_Reset();
        return;
    }
    if (alpha > 1.0f) {
        alpha = 1.0f;
    }

    battleCtx = BattleSystem_GetBattleContext(battleSys);
    monSpriteMan = BattleSystem_GetPokemonSpriteManager(battleSys);
    maxBattlers = BattleSystem_GetMaxBattlers(battleSys);
    if (maxBattlers > SIM_BATTLE3D_MAX_BATTLERS) {
        maxBattlers = SIM_BATTLE3D_MAX_BATTLERS;
    }

    for (i = 0; i < SIM_BATTLE3D_MAX_BATTLERS; i++) {
        slotHas3d[i] = FALSE;
        slotSpecies[i] = 0;
        slotForm[i] = 0;
        slotShiny[i] = 0;
    }

    for (i = 0; i < maxBattlers; i++) {
        const PokemonSprite *spr = (monSpriteMan != NULL && i < MAX_MON_SPRITES) ? &monSpriteMan->sprites[i] : NULL;
        if (battleCtx != NULL) {
            slotSpecies[i] = battleCtx->battleMons[i].species;
            slotForm[i] = battleCtx->battleMons[i].formNum;
            slotShiny[i] = battleCtx->battleMons[i].isShiny;
        }
        if (slotSpecies[i] > 0 && !BdspIsSubstituteDoll(spr)
            && SIM_Battle3D_HasModelLoaded(slotSpecies[i], slotForm[i], slotShiny[i])) {
            slotHas3d[i] = TRUE;
            any3dModel = TRUE;
        }
    }

    memset(&frame, 0, sizeof(frame));
    frameNum = arena->frame;
    timeSec = (float)frameNum / 60.0f;
    arena->frame++;

    br = sBattleStage.brightness;
    if (sBattleStage.lightningBrightness > 0 && sBattleStage.lightningBrightness > br) {
        br = sBattleStage.lightningBrightness;
    }

    frame.active = 1;
    frame.biome = SIM_Battle3D_BiomeFromBackground((int)BattleSystem_GetBackground(battleSys));
    frame.timeOfDay = BdspTimeOfDay(battleSys);
    frame.weather = BdspWeather(battleSys);
    frame.alpha = alpha;
    frame.timeSec = timeSec;
    frame.brightness = (float)br / 16.0f;

    if (heightSizing || any3dModel) {
        baseEye[0] = -3.6f;
        baseEye[1] = 2.55f;
        baseEye[2] = 8.8f;
        baseTarget[0] = 0.6f;
        baseTarget[1] = 1.45f;
        baseTarget[2] = -2.0f;
        baseFov = 38.0f;
    }

    BattleStageCamera_GetBdspDeltas(&yawDeg, &pitchDeg, &distScale, &fovScale, &shakeX, &shakeY, &isIdle);

    // Subtle, alive BDSP over-the-shoulder camera sway combined with
    // BattleStageCamera intro/idle/cinematic/shake deltas.
    target[0] = baseTarget[0];
    target[1] = baseTarget[1];
    target[2] = baseTarget[2];

    if (isIdle) {
        yawDeg = yawDeg * 0.55f + 1.5f * sinf(timeSec * 0.42f);
        pitchDeg = pitchDeg * 0.55f + 0.4f * sinf(timeSec * 0.65f);
        target[0] += 0.12f * sinf(timeSec * 0.35f);
        target[1] += 0.04f * cosf(timeSec * 0.52f);
    } else {
        yawDeg *= 0.65f;
        pitchDeg *= 0.65f;
    }

    if (distScale < 0.65f) {
        distScale = 0.65f;
    } else if (distScale > 1.25f) {
        distScale = 1.25f;
    }

    off[0] = baseEye[0] - baseTarget[0];
    off[1] = baseEye[1] - baseTarget[1];
    off[2] = baseEye[2] - baseTarget[2];

    // Pitch around camera-right (same convention as BattleStageCamera PoseCamera)
    pitchRad = pitchDeg * 0.0174532925f;
    if (pitchRad != 0.0f) {
        float rx = off[2];
        float rz = -off[0];
        float rlen = sqrtf(rx * rx + rz * rz);
        if (rlen > 0.0001f) {
            float lx, ly, lz;
            rx /= rlen;
            rz /= rlen;
            // lift = cross(off, right) where right = (rx, 0, rz)
            lx = off[1] * rz;
            ly = off[2] * rx - off[0] * rz;
            lz = -off[1] * rx;
            cosP = cosf(pitchRad);
            sinP = sinf(pitchRad);
            off[0] = off[0] * cosP + lx * sinP;
            off[1] = off[1] * cosP + ly * sinP;
            off[2] = off[2] * cosP + lz * sinP;
        }
    }

    // Yaw around world +Y
    yawRad = yawDeg * 0.0174532925f;
    if (yawRad != 0.0f) {
        float ox = off[0];
        cosY = cosf(yawRad);
        sinY = sinf(yawRad);
        off[0] = ox * cosY + off[2] * sinY;
        off[2] = off[2] * cosY - ox * sinY;
    }

    off[0] *= distScale;
    off[1] *= distScale;
    off[2] *= distScale;

    eye[0] = target[0] + off[0];
    eye[1] = target[1] + off[1];
    eye[2] = target[2] + off[2];

    if (shakeX != 0.0f || shakeY != 0.0f) {
        float rx = off[2];
        float rz = -off[0];
        float rlen = sqrtf(rx * rx + rz * rz);
        float sx = shakeX * 0.045f;
        float sy = shakeY * 0.045f;
        if (rlen > 0.0001f) {
            rx /= rlen;
            rz /= rlen;
            eye[0] += rx * sx;
            eye[2] += rz * sx;
            target[0] += rx * sx;
            target[2] += rz * sx;
        }
        eye[1] += sy;
        target[1] += sy;
    }

    if (eye[1] < 0.85f) {
        eye[1] = 0.85f;
    }

    frame.camEye[0] = eye[0];
    frame.camEye[1] = eye[1];
    frame.camEye[2] = eye[2];
    frame.camTarget[0] = target[0];
    frame.camTarget[1] = target[1];
    frame.camTarget[2] = target[2];

    frame.camFovDeg = baseFov * fovScale;
    if (frame.camFovDeg < 18.0f) {
        frame.camFovDeg = 18.0f;
    } else if (frame.camFovDeg > 56.0f) {
        frame.camFovDeg = 56.0f;
    }
    frame.camAspect = 16.0f / 9.0f;

    for (i = 0; i < maxBattlers; i++) {
        int btype = BattleSystem_GetBattlerType(battleSys, i);
        SIM_Battle3DBattler *dst = &frame.battlers[i];
        BdspBattlerAnim *anim = &sBdspAnim[i];
        BOOL has3d = slotHas3d[i];
        int species = slotSpecies[i];
        int form = slotForm[i];
        int isShiny = slotShiny[i];
        float wx = 0.0f;
        float wz = 0.0f;
        float oppX = 0.0f;
        float oppZ = 0.0f;
        float radius = 0.9f;
        float modelScale = 1.0f;
        float battlerYawDeg;
        int isPlayer = 0;
        int homeX = 128;

        // Reset per-battler anim state on switch-in / species or form change
        if (species != anim->species || form != anim->form || isShiny != anim->isShiny) {
            int prevNonce = anim->animNonce;
            memset(anim, 0, sizeof(*anim));
            anim->species = species;
            anim->form = form;
            anim->isShiny = isShiny;
            anim->animState = SIM_BATTLE3D_ANIM_IDLE;
            anim->animNonce = prevNonce;
        }

        switch (btype) {
        case BATTLER_TYPE_SOLO_PLAYER:
            if (has3d) {
                wx = -2.15f;
                wz = 2.25f;
                oppX = 2.35f;
                oppZ = -2.15f;
                modelScale = 1.40f;
            } else {
                wx = -2.95f;
                wz = 1.35f;
                oppX = 6.95f;
                oppZ = -7.80f;
            }
            radius = 1.25f;
            isPlayer = 1;
            homeX = 64;
            break;
        case BATTLER_TYPE_SOLO_ENEMY:
            if (has3d) {
                wx = 2.35f;
                wz = -2.15f;
                oppX = -2.15f;
                oppZ = 2.25f;
                modelScale = 1.40f;
            } else {
                wx = 6.95f;
                wz = -7.80f;
                oppX = -2.95f;
                oppZ = 1.35f;
            }
            radius = 1.45f;
            isPlayer = 0;
            homeX = 192;
            break;
        case BATTLER_TYPE_PLAYER_SIDE_SLOT_1:
            if (has3d) {
                wx = -2.75f;
                wz = 1.75f;
                oppX = 2.275f;
                oppZ = -2.85f;
                modelScale = 1.25f;
            } else {
                wx = -3.35f;
                wz = 0.70f;
                oppX = 8.825f;
                oppZ = -9.55f;
            }
            radius = 1.15f;
            isPlayer = 1;
            homeX = 40;
            break;
        case BATTLER_TYPE_PLAYER_SIDE_SLOT_2:
            if (has3d) {
                wx = -1.55f;
                wz = 2.65f;
                oppX = 2.275f;
                oppZ = -2.85f;
                modelScale = 1.25f;
            } else {
                wx = -2.25f;
                wz = 1.90f;
                oppX = 8.825f;
                oppZ = -9.55f;
            }
            radius = 1.15f;
            isPlayer = 1;
            homeX = 80;
            break;
        case BATTLER_TYPE_ENEMY_SIDE_SLOT_1:
            if (has3d) {
                wx = 3.10f;
                wz = -2.35f;
                oppX = -2.15f;
                oppZ = 2.20f;
                modelScale = 1.25f;
            } else {
                wx = 9.90f;
                wz = -7.75f;
                oppX = -2.80f;
                oppZ = 1.30f;
            }
            radius = 1.35f;
            isPlayer = 0;
            homeX = 216;
            break;
        case BATTLER_TYPE_ENEMY_SIDE_SLOT_2:
            if (has3d) {
                wx = 1.45f;
                wz = -3.35f;
                oppX = -2.15f;
                oppZ = 2.20f;
                modelScale = 1.25f;
            } else {
                wx = 7.75f;
                wz = -11.35f;
                oppX = -2.80f;
                oppZ = 1.30f;
            }
            radius = 1.35f;
            isPlayer = 0;
            homeX = 176;
            break;
        default:
            continue;
        }

        // Right-handed Y-up (+Z forward): yaw = atan2(dx, dz) turns +Z toward opponent
        battlerYawDeg = atan2f(oppX - wx, oppZ - wz) * (180.0f / 3.14159265f);

        dst->isPlayer = isPlayer;
        dst->worldX = wx;
        dst->worldY = 0.0f;
        dst->worldZ = wz;
        dst->shadowRadius = radius;
        dst->alpha = 0.0f;
        dst->visible = 0;
        dst->species = species;
        dst->form = form;
        dst->isShiny = isShiny;
        dst->yawDeg = battlerYawDeg;
        dst->modelScale = modelScale;
        dst->use3dModel = has3d ? 1 : 0;

        if (monSpriteMan != NULL && i < MAX_MON_SPRITES) {
            const PokemonSprite *spr = &monSpriteMan->sprites[i];
            const PokemonSpriteTransforms *tr = &spr->transforms;
            if (!spr->active) {
                if (has3d && anim->animState == SIM_BATTLE3D_ANIM_FAINT && species > 0) {
                    float clipDur = SIM_Battle3D_GetModelClipDuration(species, form, isShiny, SIM_BATTLE3D_ANIM_FAINT);
                    float faintTotal = (clipDur > 0.05f ? clipDur : (BDSP_ANIM_FAINT_HOLD - 0.35f)) + 0.35f;
                    if (anim->animTime < faintTotal) {
                        float fadeStart = faintTotal - 0.35f;
                        float fadeAlpha = (anim->animTime > fadeStart)
                            ? (1.0f - (anim->animTime - fadeStart) / 0.35f)
                            : 1.0f;
                        if (fadeAlpha < 0.0f) {
                            fadeAlpha = 0.0f;
                        }
                        dst->visible = 1;
                        dst->worldX = wx;
                        dst->worldY = 0.0f;
                        dst->worldZ = wz;
                        dst->alpha = fadeAlpha;
                    } else {
                        anim->wasVisible = FALSE;
                        anim->hitFlickering = FALSE;
                        anim->animState = SIM_BATTLE3D_ANIM_IDLE;
                        anim->animTime = 0.0f;
                        anim->animDuration = 0.0f;
                    }
                } else {
                    anim->wasVisible = FALSE;
                    anim->hitFlickering = FALSE;
                    if (anim->animState == SIM_BATTLE3D_ANIM_FAINT) {
                        anim->animState = SIM_BATTLE3D_ANIM_IDLE;
                        anim->animTime = 0.0f;
                        anim->animDuration = 0.0f;
                    }
                }
            } else {
                BOOL hidden = (tr->hide && !(has3d && anim->hitFlickering)) || tr->hide2 || tr->alpha <= 0;
                if (hidden && has3d && anim->animState == SIM_BATTLE3D_ANIM_FAINT && species > 0) {
                    float clipDur = SIM_Battle3D_GetModelClipDuration(species, form, isShiny, SIM_BATTLE3D_ANIM_FAINT);
                    float faintTotal = (clipDur > 0.05f ? clipDur : (BDSP_ANIM_FAINT_HOLD - 0.35f)) + 0.35f;
                    if (anim->animTime < faintTotal) {
                        float fadeStart = faintTotal - 0.35f;
                        float fadeAlpha = (anim->animTime > fadeStart)
                            ? (1.0f - (anim->animTime - fadeStart) / 0.35f)
                            : 1.0f;
                        if (fadeAlpha < 0.0f) {
                            fadeAlpha = 0.0f;
                        }
                        dst->visible = 1;
                        dst->worldX = wx;
                        dst->worldY = 0.0f;
                        dst->worldZ = wz;
                        dst->alpha = fadeAlpha;
                    }
                }
                if (!hidden) {
                    int dxPx = (tr->xCenter + tr->xOffset) - homeX;
                    int sc = tr->scaleX < 0 ? -tr->scaleX : tr->scaleX;
                    float elev = spr->shadow.height > 0 ? (float)spr->shadow.height * 0.04f : 0.0f;

                    if (dxPx < -96) {
                        dxPx = -96;
                    } else if (dxPx > 96) {
                        dxPx = 96;
                    }

                    dst->visible = 1;
                    dst->worldX = wx + (float)dxPx * 0.032f;
                    dst->worldY = elev;
                    dst->worldZ = wz;
                    dst->alpha = (float)tr->alpha / 31.0f;

                    if (!anim->wasVisible && species > 0) {
                        anim->wasVisible = TRUE;
                        if (anim->animState != SIM_BATTLE3D_ANIM_FAINT) {
                            SetBdspAnim(i, SIM_BATTLE3D_ANIM_CRY, BDSP_ANIM_CRY_DUR);
                        }
                    }

                    if (heightSizing && !has3d) {
                        float spScale = BattleStageSprites_GetSpeciesScale(i);
                        float refBase = isPlayer ? 1.0f : 0.45f;
                        float ratio = spScale / refBase;
                        if (ratio < 0.65f) {
                            ratio = 0.65f;
                        } else if (ratio > 2.2f) {
                            ratio = 2.2f;
                        }
                        dst->shadowRadius *= ratio;
                    }

                    if (sc < MON_AFFINE_SCALE(1)) {
                        float sf = (float)sc / (float)MON_AFFINE_SCALE(1);
                        if (sf < 0.0f) {
                            sf = 0.0f;
                        }
                        if (has3d) {
                            dst->modelScale = modelScale * sf;
                        }
                        dst->shadowRadius = radius * sf;
                    }
                }
            }
        }

        // Deterministic frame-stepped (1/60s per frame) animation timer
        if (anim->wasVisible) {
            if (anim->justTriggered) {
                anim->justTriggered = FALSE;
            } else {
                anim->animTime += BDSP_ANIM_DT;
                if (anim->animState != SIM_BATTLE3D_ANIM_IDLE && anim->animState != SIM_BATTLE3D_ANIM_FAINT) {
                    float clipDur = has3d
                        ? SIM_Battle3D_GetModelClipDuration(species, form, isShiny, anim->animState)
                        : 0.0f;
                    float effDur = (clipDur > 0.05f)
                        ? (clipDur + BDSP_ANIM_BLEND_DUR + 0.05f)
                        : anim->animDuration;
                    if (effDur > 0.0f && anim->animTime >= effDur) {
                        // Match the renderer's post-blend idle phase so IDLE resumes with zero snap.
                        float resumeIdleT = (clipDur > 0.05f && anim->animTime > clipDur)
                            ? (anim->animTime - clipDur)
                            : 0.0f;
                        anim->animState = SIM_BATTLE3D_ANIM_IDLE;
                        anim->animTime = resumeIdleT;
                        anim->animDuration = 0.0f;
                        anim->animNonce++;
                    }
                } else if (anim->animState == SIM_BATTLE3D_ANIM_IDLE && anim->animTime >= 3600.0f) {
                    anim->animTime -= 3600.0f;
                }
            }
        }

        dst->animState = anim->animState;
        dst->animTime = anim->animTime;
        dst->animNonce = anim->animNonce;
    }

    BattleBdspTrainer_Update(battleSys, &frame);
    BattleBdspCam_Update(battleSys, &frame);
    BdspDumpFrame(frameNum, &frame, battleSys, maxBattlers);
    SIM_Battle3D_SubmitFrame(&frame);
}
