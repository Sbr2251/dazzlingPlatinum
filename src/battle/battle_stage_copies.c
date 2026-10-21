#include "battle/battle_stage_copies.h"

#include <nitro.h>
#include <nnsys.h>
#include <string.h>

#include "config/battle_stage.h"
#include "constants/battle.h"
#include "constants/graphics.h"

#include "battle/battle_stage.h"
#include "battle/battle_stage_camera.h"
#include "battle/battle_stage_layout.h"
#include "battle/battle_stage_sprites.h"
#include "battle/battle_stage_stream.h"
#include "battle/ov16_0223DF00.h"

#include "bg_window.h"
#include "heap.h"
#include "pokemon_sprite.h"
#include "sprite.h"
#include "sprite_system.h"
#include "vram_transfer.h"

// bw2vis:idle. Move copies of a streamed battler, drawn by the stage (docs/living_battle_stage/
// sprite_stream.md, "Move copies"). A move's OAM copy (AddPokemonSprite: Double Team, Agility,
// Minimize, ...) was the classic 80x80 window of the stream frame: a back at 1.75x showed only
// its bottom-centre 46x46 texels, with no sink, and the mesh popped back larger and lower at the
// end. Now the copy's own tiles go blank and the stage draws, where the copy is, the battler's
// live stream frame as the mesh would draw it: its canvas at its scale, with its sink, the
// copy's affine scale and rotation, its visibility and its blend (a translucent copy at the
// blend's EVA), following the camera as the battler does.

#define COPY_TILE_BYTES  (10 * 10 * TILE_SIZE_4BPP) // the copy's 80x80 frame
#define COPY_POLYGON_ID  40 // + the copy's slot: translucent copies over each other still blend
#define COPY_Z_BIAS      1 // in front of the battler (the sprite camera's z grows toward the viewer)

typedef struct StageCopy {
    ManagedSprite *sprite; // NULL: the slot is free
    u8 battler;
    u32 vramAddr; // the copy's OBJ tiles
    const u8 *tiles; // the 2D copy's own tiles (the battler's classic window), for Release
} StageCopy;

// The BG2 copy (LoadPokemonSpriteIntoBg) at the mesh's scale: BG2's tiles (char base 0xC000)
// end where BG3's begin (0x10000), 512 4bpp tiles; tile 0 stays blank for the empty tilemap
#define BG2_COPY_MAX_TILES 511
#define BG2_MAP_TILES      64 // the 512x512 tilemap, in tiles a side
#define BG2_BLOCK_TILES    32 // a screen block's side
#define BG2_COPY_HEAP_SPARE 0x4000 // heap left free while the copy's tiles are built (16 KB at most)

static StageCopy sCopies[BATTLE_STAGE_MAX_MON_COPIES];
static u16 sBg2CopyTiles; // tiles the last BG2 copy loaded after tile 0, for RemoveBg2Copy
static u8 sBlankTiles[COPY_TILE_BYTES] ATTRIBUTE_ALIGN(32);
BattleStageCopyStats sMonCopyStats;

void BattleStageCopies_Init(void)
{
    memset(sCopies, 0, sizeof(sCopies));
    sBg2CopyTiles = 0;
    memset(&sMonCopyStats, 0, sizeof(sMonCopyStats));
}

BOOL BattleStage_AdoptMonCopy(int slot, ManagedSprite *sprite, int battler, const u8 *tiles, u32 vramAddr)
{
    if (slot < 0 || slot >= BATTLE_STAGE_MAX_MON_COPIES || sprite == NULL || battler < 0 || battler >= MAX_MON_SPRITES) {
        return FALSE;
    }

    sCopies[slot].sprite = NULL;

    // Only where the stage draws the battler from its stream, and so can draw the copy
    if (!BattleStageSprites_StreamsLive()
        || (BattleStageSprites_DebugFlags() & (BATTLE_STAGE_DEBUG_CLASSIC_SPRITES | BATTLE_STAGE_DEBUG_NO_SPRITE_STREAM))
        || !BattleStage_IsSpriteStreamed(battler)) {
        return FALSE;
    }

    sCopies[slot].sprite = sprite;
    sCopies[slot].battler = battler;
    sCopies[slot].vramAddr = vramAddr;
    sCopies[slot].tiles = tiles;
    sMonCopyStats.adopted++;
    return TRUE;
}

const u8 *BattleStage_BlankCopyTiles(void)
{
    DC_FlushRange(sBlankTiles, sizeof(sBlankTiles));
    return sBlankTiles;
}

void BattleStage_DropMonCopy(int slot)
{
    if (slot >= 0 && slot < BATTLE_STAGE_MAX_MON_COPIES) {
        sCopies[slot].sprite = NULL;
    }
}

void BattleStage_DropAllMonCopies(void)
{
    int i;

    for (i = 0; i < BATTLE_STAGE_MAX_MON_COPIES; i++) {
        sCopies[i].sprite = NULL;
    }
}

void BattleStage_ReleaseMonCopiesOf(ManagedSprite *sprite)
{
    int i, battler = -1;

    for (i = 0; i < BATTLE_STAGE_MAX_MON_COPIES; i++) {
        if (sprite != NULL && sCopies[i].sprite == sprite) {
            battler = sCopies[i].battler;
        }
    }

    if (battler < 0) {
        return;
    }

    for (i = 0; i < BATTLE_STAGE_MAX_MON_COPIES; i++) {
        if (sCopies[i].sprite != NULL && sCopies[i].battler == battler) {
            // Its own tiles back: the 2D effect (an OBJ window) needs the 2D copy
            if (sCopies[i].tiles != NULL) {
                DC_FlushRange(sCopies[i].tiles, COPY_TILE_BYTES);
                VramTransfer_Request(NNS_GFD_DST_2D_OBJ_CHAR_MAIN, sCopies[i].vramAddr, (void *)sCopies[i].tiles, COPY_TILE_BYTES);
            }

            sCopies[i].sprite = NULL;
            sMonCopyStats.released++;
        }
    }
}

// The polygon alpha of a copy: a translucent OBJ shows at the blend's EVA (of 16)
static int CopyAlpha(const Sprite *sprite)
{
    int eva;

    if ((sprite->overwriteFlags & NNS_G2D_RND_OVERWRITE_OBJMODE) == 0 || sprite->explicitOamMode != GX_OAM_MODE_XLU) {
        return 31;
    }

    eva = reg_G2_BLDALPHA & 0x1F;

    if (eva > 16) {
        eva = 16;
    }

    return eva * 31 / 16;
}

void BattleStage_DrawMonCopies(PokemonSpriteManager *monSpriteMan)
{
    BOOL begun = FALSE;
    u16 tint[3] = { 256, 256, 256 };
    int i;

    if (!BATTLE_STAGE_3D || monSpriteMan == NULL || !BattleStageSprites_StreamsLive()) {
        return;
    }

    for (i = 0; i < BATTLE_STAGE_MAX_MON_COPIES; i++) {
        StageCopy *copy = &sCopies[i];
        const Sprite *sprite;
        PokemonSpriteTransforms transforms;
        PokemonSpriteDrawRect rect;
        BattleStageStreamRect canvas;
        BattleStageCameraSimilarity similarity;
        fx32 scaleX = FX32_ONE, scaleY = FX32_ONE;
        u16 rotation = 0;
        int alpha;

        if (copy->sprite == NULL || copy->sprite->sprite == NULL) {
            continue;
        }

        sprite = copy->sprite->sprite;

        if (!sprite->draw || (sprite->overwriteFlags & NNS_G2D_RND_OVERWRITE_OBJMODE && sprite->explicitOamMode == GX_OAM_MODE_OBJWND)) {
            continue;
        }

        alpha = CopyAlpha(sprite);

        if (alpha == 0) {
            continue; // polygon alpha 0 draws wireframe
        }

        if (!begun) {
            NNS_G3dGeFlushBuffer();
            G3_PushMtx();
            BattleStage_GetSpriteTint(&tint[0], &tint[1], &tint[2]);
            begun = TRUE;
        }

        if (!BattleStageStream_Bind(copy->battler)) {
            continue;
        }

        if (sprite->affineOverwriteMode != NNS_G2D_RND_AFFINE_OVERWRITE_NONE) {
            scaleX = sprite->affineScale.x;
            scaleY = sprite->affineScale.y;
            rotation = sprite->affineZRotation;
        }

        // The copy's 80x80 frame about its position, as the classic frame about the battler's
        // centre: the stream's canvas lands about it as the mesh's about the battler
        memset(&transforms, 0, sizeof(transforms));
        rect.x = -MON_SPRITE_FRAME_WIDTH / 2;
        rect.y = -MON_SPRITE_FRAME_HEIGHT / 2;
        rect.width = MON_SPRITE_FRAME_WIDTH;
        rect.height = MON_SPRITE_FRAME_HEIGHT;
        rect.z = monSpriteMan->sprites[copy->battler].transforms.zCenter + COPY_Z_BIAS;
        BattleStageStream_CanvasRect(copy->battler, &transforms, &rect, &canvas);

        G3_Identity();

        // Off home the copy follows the camera as its battler does (the copy's place is a home
        // screen place, like the battler's)
        if (BattleStage_IsVisible() && BattleStageLayout_Similarity(copy->battler, &similarity)) { // bw2vis:layout - and its BW2 place
            G3_Translate(similarity.nowX, similarity.nowY, 0);
            G3_Scale(similarity.scale, similarity.scale, FX32_ONE);
            G3_Translate(-(similarity.homeX << FX32_SHIFT), -(similarity.homeY << FX32_SHIFT), 0);
        }

        G3_Translate(sprite->position.x + sprite->affineTranslation.x, sprite->position.y + sprite->affineTranslation.y, 0);

        if (sprite->affineOverwriteMode != NNS_G2D_RND_AFFINE_OVERWRITE_NONE) {
            G3_Scale(scaleX, scaleY, FX32_ONE);
            G3_RotZ(FX_SinIdx(rotation), FX_CosIdx(rotation));
        }

        G3_Translate(-sprite->affineTranslation.x, -sprite->affineTranslation.y, 0);

        G3_TexPlttBase(monSpriteMan->plttBaseAddr + copy->battler * PALETTE_SIZE_BYTES, monSpriteMan->imageProxy.attr.fmt);
        G3_MaterialColorDiffAmb(GX_RGB(31 * tint[0] / 256, 31 * tint[1] / 256, 31 * tint[2] / 256), GX_RGB(16, 16, 16), TRUE);
        G3_MaterialColorSpecEmi(GX_RGB(16, 16, 16), GX_RGB(0, 0, 0), FALSE);
        G3_PolygonAttr(GX_LIGHTMASK_NONE, GX_POLYGONMODE_MODULATE, GX_CULL_NONE, COPY_POLYGON_ID + i, alpha, 0);
        NNS_G2dDrawSpriteFast(canvas.x, canvas.y, rect.z, canvas.width, canvas.height, canvas.u0, canvas.v0, canvas.u1, canvas.v1);
        BattleStageStream_Unbind();
        sMonCopyStats.drawnFrames++;
    }

    if (begun) {
        G3_PopMtx(1);
    }
}

// The tilemap entry of BG2 tile (tx, ty), wrapped into the 512x512 map's four screen blocks
static u16 *Bg2MapEntry(u16 *map, int tx, int ty)
{
    tx &= BG2_MAP_TILES - 1;
    ty &= BG2_MAP_TILES - 1;
    return &map[((ty / BG2_BLOCK_TILES) * 2 + tx / BG2_BLOCK_TILES) * BG2_BLOCK_TILES * BG2_BLOCK_TILES + (ty % BG2_BLOCK_TILES) * BG2_BLOCK_TILES + tx % BG2_BLOCK_TILES];
}

static int FloorDiv8(int v)
{
    return v >= 0 ? v / 8 : -((-v + 7) / 8);
}

BOOL BattleStage_BuildBg2Copy(int battler, BgConfig *bgConfig, u8 bgLayer, enum HeapID heapID)
{
    const u8 *frame;
    u16 *map;
    u8 *tiles;
    PokemonSpriteTransforms transforms;
    PokemonSpriteDrawRect rect;
    BattleStageStreamRect canvas;
    int tx0, ty0, tx1, ty1, tx, ty, x, y, n, palette;

    if (!BATTLE_STAGE_3D
        || !BattleStageSprites_StreamsLive()
        || (BattleStageSprites_DebugFlags() & (BATTLE_STAGE_DEBUG_CLASSIC_SPRITES | BATTLE_STAGE_DEBUG_NO_SPRITE_STREAM))
        || !BattleStage_IsSpriteStreamed(battler)) {
        return FALSE;
    }

    frame = BattleStageStream_GetFrame(battler);
    map = Bg_GetTilemapBuffer(bgConfig, bgLayer);

    if (frame == NULL || map == NULL) {
        return FALSE;
    }

    // In BG pixels the classic copy's 80x80 frame is at (0, 0) (the BG offset puts it about the
    // battler): the canvas lands about it as the mesh's about the battler, sink included
    memset(&transforms, 0, sizeof(transforms));
    rect.x = 0;
    rect.y = 0;
    rect.width = MON_SPRITE_FRAME_WIDTH;
    rect.height = MON_SPRITE_FRAME_HEIGHT;
    rect.z = 0;
    BattleStageStream_CanvasRect(battler, &transforms, &rect, &canvas);

    if (canvas.width <= 0 || canvas.height <= 0 || canvas.width > 255 || canvas.height > 255) {
        return FALSE;
    }

    tx0 = FloorDiv8(canvas.x);
    ty0 = FloorDiv8(canvas.y);
    tx1 = FloorDiv8(canvas.x + canvas.width - 1) + 1;
    ty1 = FloorDiv8(canvas.y + canvas.height - 1) + 1;
    n = (tx1 - tx0) * (ty1 - ty0);

    if (n > BG2_COPY_MAX_TILES) {
        return FALSE;
    }

    // A failed allocation resets a link battle (AllocFail): keep the classic copy rather than try
    if (HeapExp_FndGetTotalFreeSize(heapID) < (n + 1) * TILE_SIZE_4BPP + BG2_COPY_HEAP_SPARE) {
        return FALSE;
    }

    tiles = Heap_AllocAtEnd(heapID, (n + 1) * TILE_SIZE_4BPP);

    if (tiles == NULL) {
        return FALSE;
    }

    memset(tiles, 0, (n + 1) * TILE_SIZE_4BPP);

    // The palette row the copy's own tilemap (pl_batt_bg 264) gave its frame
    palette = *Bg2MapEntry(map, 0, 0) >> 12;
    memset(map, 0, BG2_MAP_TILES * BG2_MAP_TILES * sizeof(u16));
    n = 0;

    for (ty = ty0; ty < ty1; ty++) {
        for (tx = tx0; tx < tx1; tx++) {
            u8 *tile = tiles + (n + 1) * TILE_SIZE_4BPP;

            for (y = 0; y < 8; y++) {
                int py = ty * 8 + y;
                int v;

                if (py < canvas.y || py >= canvas.y + canvas.height) {
                    continue;
                }

                v = canvas.v0 + (py - canvas.y) * (canvas.v1 - canvas.v0) / canvas.height;

                for (x = 0; x < 8; x++) {
                    int px = tx * 8 + x;
                    int u, texel;

                    if (px < canvas.x || px >= canvas.x + canvas.width) {
                        continue;
                    }

                    u = canvas.u0 + (px - canvas.x) * (canvas.u1 - canvas.u0) / canvas.width;
                    texel = (frame[v * (STREAM_CANVAS_WIDTH / 2) + u / 2] >> ((u & 1) * 4)) & 0xF;
                    tile[y * 4 + x / 2] |= texel << ((x & 1) * 4);
                }
            }

            *Bg2MapEntry(map, tx, ty) = (u16)((n + 1) | (palette << 12));
            n++;
        }
    }

    Bg_LoadTiles(bgConfig, bgLayer, tiles, (n + 1) * TILE_SIZE_4BPP, 0);
    Heap_Free(tiles);
    Bg_CopyTilemapBufferToVRAM(bgConfig, bgLayer);
    sBg2CopyTiles = n;
    sMonCopyStats.bg2Copies++;
    return TRUE;
}

BOOL BattleStage_TakeBg2Copy(u32 *clearBytes)
{
    u32 bytes = (sBg2CopyTiles + 1) * TILE_SIZE_4BPP;
    BOOL built = sBg2CopyTiles != 0;

    // At least what the classic copy cleared
    *clearBytes = bytes > 10 * 10 * 2 * TILE_SIZE_4BPP ? bytes : 10 * 10 * 2 * TILE_SIZE_4BPP;
    sBg2CopyTiles = 0;
    return built;
}
