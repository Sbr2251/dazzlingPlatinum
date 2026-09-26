#include "battle/battle_stage.h"

#include <nitro.h>
#include <nnsys.h>
#include <string.h>

#include "config/battle_stage.h"
#include "constants/battle.h"
#include "constants/heap.h"
#include "constants/narc.h"

#include "battle/battle_stage_format.h"
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
    VecFx32 platformStep[2];
    MtxFx44 projection;
    MtxFx43 view;
    int viewBuiltFor;
    BOOL hasTexMtxMesh; // FOLLOW_BG3_SCROLL or SCROLL
    BOOL hasLitMesh;
    BOOL hasAtmosphere;
    u32 frame; // drawn frames, for SCROLL
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
static void DrawArena(StageArena *arena);
static void UpdateFog(StageArena *arena);
static void FogOff(void);

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
    sStageFog.on = TRUE; // unknown, so FogOff writes it
    sStageFog.tableValid = FALSE;
    FogOff();

    if (BATTLE_STAGE_3D) {
        sBattleStage.arena = LoadArena(battleSys);
    }
}

void BattleStage_Free(void)
{
    if (sBattleStage.arena != NULL) {
        FreeArena(sBattleStage.arena);
        sBattleStage.arena = NULL;
    }

    sBattleStage.battleSys = NULL;
    sBattleStage.debugView = 0;
    sBattleStage.brightness = 0;
    FogOff();
}

void BattleStage_Draw(void)
{
    BOOL visible;

    if (sBattleStage.battleSys == NULL || sBattleStage.arena == NULL) {
        return;
    }

    visible = BattleStage_IsVisible();
    UpdatePlatforms(visible);

    if (visible) {
        SyncPalettes(sBattleStage.arena);
        DrawArena(sBattleStage.arena);
        UpdateFog(sBattleStage.arena);
    } else {
        FogOff();
    }

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

BOOL BattleStage_IsVisible(void)
{
    return sBattleStage.battleSys != NULL && sBattleStage.arena != NULL && sBattleStage.enabled && sBattleStage.suppressed == 0;
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

static u32 BuildMeshDL(u32 *dest, u32 capacity, const BattleStageFileHeader *piece, const BattleStageFileMesh *mesh, const BattleStageFileTexture *texture, u32 texAddr, u32 plttAddr)
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

static void BuildProjection(StageArena *arena, const BattleStageFileHeader *header)
{
    MtxFx44 *m = &arena->projection;
    fx32 a = (STAGE_DEPTH_FAR - STAGE_DEPTH_NEAR) / 2;
    fx32 b = (STAGE_DEPTH_FAR + STAGE_DEPTH_NEAR) / 2;
    int farUnits = header->farClip >> FX32_SHIFT;
    int scaleW = farUnits > 0 ? 1024 / farUnits : 16;

    // A larger W keeps more bits in the squeezed depth; it doesn't move anything on screen
    if (scaleW < 1) {
        scaleW = 1;
    } else if (scaleW > 16) {
        scaleW = 16;
    }

    MTX_PerspectiveW(header->fovySin, header->fovyCos, FX32_ONE * 4 / 3, header->nearClip, header->farClip, scaleW * FX32_ONE, m);

    // z' = a * z + b * w, so NDC z lands in [STAGE_DEPTH_NEAR, STAGE_DEPTH_FAR]
    m->_02 = FX_Mul(a, m->_02) + FX_Mul(b, m->_03);
    m->_12 = FX_Mul(a, m->_12) + FX_Mul(b, m->_13);
    m->_22 = FX_Mul(a, m->_22) + FX_Mul(b, m->_23);
    m->_32 = FX_Mul(a, m->_32) + FX_Mul(b, m->_33);
}

static void BuildView(StageArena *arena, int view)
{
    VecFx32 up = { 0, FX32_ONE, 0 };
    VecFx32 offset, camPos;
    fx32 sinA, cosA, x;

    VEC_Subtract(&arena->camPos, &arena->camTarget, &offset);

    if (view == 1 || view == 2) {
        sinA = FX_SinIdx(FX_DEG_TO_IDX(FX32_CONST(20)));
        cosA = FX_CosIdx(FX_DEG_TO_IDX(FX32_CONST(20)));

        // View 1 moves the camera to the left of the target
        if (view == 1) {
            sinA = -sinA;
        }

        x = offset.x;
        offset.x = FX_Mul(x, cosA) + FX_Mul(offset.z, sinA);
        offset.z = FX_Mul(offset.z, cosA) - FX_Mul(x, sinA);
    } else if (view == 3) {
        VecFx32 right, lift;

        sinA = FX_SinIdx(FX_DEG_TO_IDX(FX32_CONST(15)));
        cosA = FX_CosIdx(FX_DEG_TO_IDX(FX32_CONST(15)));

        VEC_CrossProduct(&up, &offset, &right);
        VEC_Normalize(&right, &right);
        VEC_CrossProduct(&offset, &right, &lift);

        offset.x = FX_Mul(FX_Mul(offset.x, cosA) + FX_Mul(lift.x, sinA), FX32_CONST(0.8));
        offset.y = FX_Mul(FX_Mul(offset.y, cosA) + FX_Mul(lift.y, sinA), FX32_CONST(0.8));
        offset.z = FX_Mul(FX_Mul(offset.z, cosA) + FX_Mul(lift.z, sinA), FX32_CONST(0.8));
    }

    VEC_Add(&arena->camTarget, &offset, &camPos);
    MTX_LookAt(&camPos, &up, &arena->camTarget, &arena->view);
    arena->viewBuiltFor = view;
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

    BuildProjection(arena, backdrop);
    BuildView(arena, 0);

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
            stageMesh->dlSize = BuildMeshDL(arena->dl + dlBytes / 4, MeshDLBound(mesh), pieces[p], mesh, texture, texAddr + texOffsets[textureIndex], arena->plttAddr + slot->offset);
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

static void SetLight(StageArena *arena)
{
    const BattleStageFileLighting *lighting = arena->hasAtmosphere ? &arena->atmosphere.lighting[LightingColumn()] : &sDefaultLighting;

    // Transformed by the current vector matrix (the view), so lightDir is in world space
    G3_LightVector(GX_LIGHTID_0, lighting->lightDir[0], lighting->lightDir[1], lighting->lightDir[2]);
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
        t += mesh->scrollAmplitude[1] * FX_CosIdx(index) * 16;
    }

    G3_MtxMode(GX_MTXMODE_TEXTURE);
    G3_Identity();
    G3_Translate(s, t, 0);
    G3_MtxMode(GX_MTXMODE_POSITION_VECTOR);
}

static void DrawArena(StageArena *arena)
{
    int platformOffset[2];
    int bg3X = 0, bg3Y = 0;
    int side, i;

    if (arena->viewBuiltFor != sBattleStage.debugView) {
        BuildView(arena, sBattleStage.debugView);
    }

    for (side = 0; side < 2; side++) {
        platformOffset[side] = BattlePlatform_GetOffsetX(ov16_0223E020(sBattleStage.battleSys, side));
    }

    NNS_G3dGeFlushBuffer();

    G3_MtxMode(GX_MTXMODE_PROJECTION);
    G3_PushMtx();
    G3_LoadMtx44(&arena->projection);

    if (arena->hasTexMtxMesh) {
        BgConfig *bgConfig = BattleSystem_BGL(sBattleStage.battleSys);

        bg3X = WrapScroll(Bg_GetXOffset(bgConfig, BG_LAYER_MAIN_3), 512);
        bg3Y = WrapScroll(Bg_GetYOffset(bgConfig, BG_LAYER_MAIN_3), 256);

        G3_MtxMode(GX_MTXMODE_TEXTURE);
        G3_PushMtx();
    }

    G3_MtxMode(GX_MTXMODE_POSITION_VECTOR);
    G3_PushMtx();
    G3_LoadMtx43(&arena->view);

    if (arena->hasLitMesh) {
        SetLight(arena);
    }

    for (i = 0; i < arena->numMeshes; i++) {
        StageMesh *mesh = &arena->meshes[i];

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

        color = lighting->fogColor;
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
