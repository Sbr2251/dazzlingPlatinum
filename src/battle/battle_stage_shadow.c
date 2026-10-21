#include "battle/battle_stage_shadow.h"

#include <nitro.h>
#include <nnsys.h>
#include <string.h>

#include "constants/battle.h"
#include "constants/narc.h"
#include "constants/species.h"

#include "battle/battle_stage_layout.h" // bw2vis:layout
#include "battle/battle_stage_sprites.h"
#include "battle/battle_stage_stream.h"
#include "battle/ov16_0223DF00.h"

#include "constants/graphics.h"
#include "pokemon.h"
#include "pokemon_sprite.h"
#include "vram_transfer.h"

// BW2's battle shadow (pokebw2 src/system/mcss.c MCSSSys_Draw and MCSS_DrawQuad, src/ov168/btlv_mcss.c
// BtlvMcss_AddPokemon): every cell quad of a sprite is drawn a second time with a palette whose 15
// colours are black, at half the sprite's alpha, through a matrix that lays the sprite down
// behind its foot point. Our battlers are one textured frame each, so the shadow is one quad: the
// battler's current stream frame (the texture the sprite draws this frame), with the same mapping
// laid onto the arena's ground. It follows the animation because it samples the same texture.
//
// The matrix, in BW2's world (y up, the enemy at -z, the camera at +x and +z):
//   translate(foot + offset) * RotX(SHADOW_ROT_X) * RotZ(rotZ) * the sprite's quads (y up)
// RotX(0xc400) tips the sprite back by 84.4 degrees: up becomes "away from the camera", 5.6
// degrees off the ground. RotZ turns it first in its own plane (default 0xf800, -11.25 degrees,
// which leans the top to the left). The offset and rotZ come from the per-species adjust table,
// else (-0.25, 0, -0.375) and 0xf800.
//
// Our arena's home camera looks straight down -z; BW2's is yawed 21.2 degrees (it sits at x 6.7,
// z 17.3 from its target). The shadow is laid along BW2's world axes as the BW2 camera sees them,
// so it falls the way it does on BW2's screen: BW2 +x is SHADOW_YAW to the right of our camera's
// right, BW2 -z the same angle to the right of straight ahead.

#define SHADOW_ROT_X        0xc400
#define SHADOW_DEFAULT_ROTZ 0xf800
#define SHADOW_DEFAULT_X    (-0x400) // fx32 world units, BW2's
#define SHADOW_DEFAULT_Z    (-0x600)
#define SHADOW_POLYGON_ID   62 // the blobs' ID: a translucent pixel never covers its own ID, so shadows don't stack
#define SHADOW_PLTT_BYTES   32 // one 16-colour palette: 0 transparent, 1..15 black (BW2's btlv file 355)
#define SHADOW_PLTT_GAP     2 // vblanks without a drawn shadow after which the palette is sent again
// BW2's camera position relative to its target, for its yaw (btlv_camera.c data_ov168_021f2f80/74)
#define BW2_CAMERA_X FX32_CONST(6.7)
#define BW2_CAMERA_Z FX32_CONST(17.3)
// BW2's perspective scale of a singles battler (data_ov168_021f31f4): the shadow's scale. A sprite
// quad is 1/16 world unit per art pixel at scale 1, so a world unit of offset is 16 / scale art
// pixels: 15.8 for the back, 14.4 for the front
#define BW2_SCALE_BACK  0x1030
#define BW2_SCALE_FRONT 0x11bf
// NDC depth of the shadow, as the blobs': in front of the arena (4010..4094), behind the sprites
#define SHADOW_DEPTH 4000
// Vertices are fx16 world units over this, so a 2x back sprite's shadow fits
#define SHADOW_VTX_SCALE 8
// Same as pokemon_sprite_stream.c: the pl_pokegra layout (species * 6 + face + male)
#define POKEGRA_FILES_PER_SPECIES 6

// The stream's battler textures: battle_stage_stream.c packs them from vramAddr, a battler each
#define STREAM_TEX_BYTES (STREAM_CANVAS_HEIGHT * STREAM_CANVAS_WIDTH / 2)
extern BattleStageStreamStats sSpriteStreamStats;

// BW2's adjust table (btlv_mcss.c data_ov168_021f3414), by face: front is BW2's enemy side.
// shadow FALSE turns the shadow off. x and z are fx32 world offsets, rotZ the in-plane turn.
// BW2 species numbers are the national dex; ours keep the same constant names, so each entry is
// written with our SPECIES_ constant (tools/battle_shadow/bw2_shadow_table.py checks it). BW2's
// entries for species this game lacks (Samurott, Zoroark, Galvantula, Haxorus, Mienfoo,
// Bouffalant, Reshiram, Zekrom) are left out.
typedef struct ShadowAdjust {
    u16 species;
    u8 front;
    u8 shadow;
    s16 x;
    s16 z;
    u16 rotZ;
} ShadowAdjust;

static const ShadowAdjust sShadowAdjust[] = {
    { SPECIES_RATTATA, 1, 1, 0x0, -0x1200, 0xee00 },
    { SPECIES_PARASECT, 0, 1, -0x400, -0x400, 0xfc00 },
    { SPECIES_DIGLETT, 1, 0, -0x400, -0x400, 0xfc00 },
    { SPECIES_DUGTRIO, 1, 0, -0x400, -0x400, 0xfc00 },
    { SPECIES_GROWLITHE, 1, 1, 0x0, -0x1200, 0xee00 },
    { SPECIES_RHYHORN, 0, 1, -0x400, -0x600, 0xf400 },
    { SPECIES_TAUROS, 1, 1, 0x0, -0x1200, 0xee00 },
    { SPECIES_SPINARAK, 1, 1, 0x0, -0x1200, 0xee00 },
    { SPECIES_SKARMORY, 1, 1, -0x400, -0x600, 0xfe00 },
    { SPECIES_ENTEI, 0, 1, -0x400, -0x900, 0xf400 },
    { SPECIES_GROVYLE, 1, 1, -0x400, -0xc00, 0x100 },
    { SPECIES_SCEPTILE, 1, 1, -0x400, -0xc00, 0x100 },
    { SPECIES_SCEPTILE, 0, 1, -0x400, -0xa00, 0xf000 },
    { SPECIES_BLAZIKEN, 1, 1, -0x800, -0x1400, 0x100 },
    { SPECIES_MIGHTYENA, 1, 1, 0x0, -0x1200, 0xee00 },
    { SPECIES_MIGHTYENA, 0, 1, -0x400, -0x900, 0xf400 },
    { SPECIES_LINOONE, 1, 1, 0x0, -0x1200, 0xee00 },
    { SPECIES_SURSKIT, 1, 1, -0x400, -0x1800, 0xf800 },
    { SPECIES_ARON, 1, 1, 0x0, -0x1200, 0xf000 },
    { SPECIES_LAIRON, 1, 1, 0x0, -0x1200, 0xee00 },
    { SPECIES_SWALOT, 1, 1, 0x0, -0x1200, 0xee00 },
    { SPECIES_ABSOL, 1, 1, 0x0, -0x1a00, 0xee00 },
    { SPECIES_SALAMENCE, 0, 1, -0x400, -0xa00, 0xf000 },
    { SPECIES_METAGROSS, 1, 1, -0x800, -0x1400, 0x100 },
    { SPECIES_GROTLE, 1, 1, 0x0, -0x1600, 0xee00 },
    { SPECIES_GROTLE, 0, 1, -0x400, -0x900, 0xf400 },
    { SPECIES_TORTERRA, 1, 1, 0x0, -0x1600, 0xee00 },
    { SPECIES_TORTERRA, 0, 1, -0x400, -0x900, 0xf400 },
    { SPECIES_INFERNAPE, 1, 1, -0x800, -0x1400, 0x100 },
    { SPECIES_HIPPOWDON, 1, 0, -0x400, -0x400, 0xfc00 },
    { SPECIES_HIPPOWDON, 0, 0, -0x400, -0x400, 0xfc00 },
    { SPECIES_ELECTIVIRE, 1, 1, -0x400, -0xc00, 0x100 },
    { SPECIES_MAGMORTAR, 1, 1, -0x400, -0xc00, 0x100 },
    { SPECIES_DIALGA, 1, 1, -0x400, -0x1000, 0xfc00 },
    { SPECIES_HEATRAN, 1, 1, 0x0, -0x2000, 0xf800 },
    { SPECIES_HEATRAN, 0, 1, -0x400, -0x900, 0xf400 },
    { SPECIES_LIEPARD, 1, 1, -0x400, -0x1000, 0xf800 },
    { SPECIES_UNFEZANT, 1, 1, -0x400, -0xc00, 0x100 },
};

typedef struct StageShadow {
    BattleSystem *battleSys;
    BOOL hasPltt;
    NNSGfdPlttKey plttKey;
    u32 plttAddr;
    u32 lastVBlank; // of the last frame that drew a silhouette
    BOOL axesBuilt;
    // Unit vectors in our world: BW2's +x and -z as BW2's camera sees them (see the top)
    VecFx32 bw2X;
    VecFx32 bw2Back;
} StageShadow;

static StageShadow sStageShadow;
BattleStageShadowStats sStageShadowStats;
static u16 sShadowPalette[SHADOW_PLTT_BYTES / 2] ATTRIBUTE_ALIGN(32);

void BattleStageShadow_Init(BattleSystem *battleSys)
{
    memset(&sStageShadow, 0, sizeof(sStageShadow));
    memset(&sStageShadowStats, 0, sizeof(sStageShadowStats));
    sStageShadow.battleSys = battleSys;

    // All black; colour 0 is transparent through the texture's colour-0 mode
    memset(sShadowPalette, 0, sizeof(sShadowPalette));
    sStageShadow.plttKey = NNS_GfdAllocPlttVram(SHADOW_PLTT_BYTES, FALSE, 0);

    if (sStageShadow.plttKey == NNS_GFD_ALLOC_ERROR_PLTTKEY) {
        return;
    }

    sStageShadow.plttAddr = NNS_GfdGetPlttKeyAddr(sStageShadow.plttKey);
    sStageShadow.hasPltt = TRUE;
    sStageShadowStats.plttAddr = sStageShadow.plttAddr;

    DC_FlushRange(sShadowPalette, sizeof(sShadowPalette));
    GX_BeginLoadTexPltt();
    GX_LoadTexPltt(sShadowPalette, sStageShadow.plttAddr, SHADOW_PLTT_BYTES);
    GX_EndLoadTexPltt();
    sStageShadow.lastVBlank = OS_GetVBlankCount();
}

void BattleStageShadow_Free(void)
{
    if (sStageShadow.hasPltt) {
        NNS_GfdFreePlttVram(sStageShadow.plttKey);
        sStageShadow.hasPltt = FALSE;
    }

    sStageShadow.battleSys = NULL;
    sStageShadowStats.plttAddr = 0;
}

// BW2's world axes in ours, from our ground's camera-right
static BOOL BuildAxes(void)
{
    VecFx32 centre, right, down, f, up = { 0, FX32_ONE, 0 };
    VecFx32 bw2Cam = { BW2_CAMERA_X, 0, BW2_CAMERA_Z };
    fx32 sinYaw, cosYaw;

    if (!BattleStageSprites_GroundFrame(1, &centre, &right, &down)) {
        return FALSE;
    }

    right.y = 0;
    VEC_Normalize(&right, &right);
    // Ahead on the ground, away from the camera
    VEC_CrossProduct(&up, &right, &f);
    VEC_Normalize(&f, &f);
    VEC_Normalize(&bw2Cam, &bw2Cam);
    sinYaw = bw2Cam.x;
    cosYaw = bw2Cam.z;

    sStageShadow.bw2X.x = FX_Mul(cosYaw, right.x) - FX_Mul(sinYaw, f.x);
    sStageShadow.bw2X.y = 0;
    sStageShadow.bw2X.z = FX_Mul(cosYaw, right.z) - FX_Mul(sinYaw, f.z);
    sStageShadow.bw2Back.x = FX_Mul(sinYaw, right.x) + FX_Mul(cosYaw, f.x);
    sStageShadow.bw2Back.y = 0;
    sStageShadow.bw2Back.z = FX_Mul(sinYaw, right.z) + FX_Mul(cosYaw, f.z);
    return TRUE;
}

// The adjust entry of a sprite (by the species and face its template shows), NULL for the default
static const ShadowAdjust *FindAdjust(const PokemonSprite *sprite, int side)
{
    u32 species = 0;
    int front = side;
    int i;

    // Other archives (Megas, forms, the doll) have no species in their template and no BW2 entry
    if (sprite->template.narcID == NARC_INDEX_POKETOOL__POKEGRA__PL_POKEGRA) {
        species = sprite->template.character / POKEGRA_FILES_PER_SPECIES;
        front = (sprite->template.character % POKEGRA_FILES_PER_SPECIES) / 2 == FACE_FRONT / 2;
    }

    for (i = 0; i < NELEMS(sShadowAdjust); i++) {
        if (sShadowAdjust[i].species == species && sShadowAdjust[i].front == front) {
            return &sShadowAdjust[i];
        }
    }

    return NULL;
}

// The projection with z' = SHADOW_DEPTH * w, as the blobs' (the projection stack has one entry)
static void LoadFlatProjection(const MtxFx44 *projection)
{
    MtxFx44 flat = *projection;

    flat._02 = FX_Mul(SHADOW_DEPTH, flat._03);
    flat._12 = FX_Mul(SHADOW_DEPTH, flat._13);
    flat._22 = FX_Mul(SHADOW_DEPTH, flat._23);
    flat._32 = FX_Mul(SHADOW_DEPTH, flat._33);
    G3_MtxMode(GX_MTXMODE_PROJECTION);
    G3_LoadMtx44(&flat);
    G3_MtxMode(GX_MTXMODE_POSITION_VECTOR);
}

typedef struct ShadowPlace {
    fx32 groundPer128; // world length of 128 screen pixels on the ground at the foot row
    fx32 cosZ; // the in-plane turn, as G3_RotZ(-sin, cos) takes it
    fx32 negSinZ;
    fx32 offX; // the adjust offset in screen pixels, along BW2's x and back
    fx32 offBack;
} ShadowPlace;

// A point of the sprite (screen pixels from the foot point: x right, y up) laid on the ground,
// as a vertex relative to the foot point
static void SendVertex(const ShadowPlace *place, fx32 x, fx32 y)
{
    fx32 xr = FX_Mul(x, place->cosZ) - FX_Mul(y, place->negSinZ);
    fx32 yr = FX_Mul(x, place->negSinZ) + FX_Mul(y, place->cosZ);
    fx32 across = xr + place->offX;
    fx32 up = FX_Mul(yr, FX_CosIdx(SHADOW_ROT_X));
    fx32 back = -FX_Mul(yr, FX_SinIdx(SHADOW_ROT_X)) + place->offBack;
    // Pixels times units, times the world per 128 pixels: world * 128, then / 128 / SHADOW_VTX_SCALE
    s64 div = 128 * SHADOW_VTX_SCALE;
    fx32 vx = (fx32)((s64)FX_Mul(FX_Mul(across, sStageShadow.bw2X.x) + FX_Mul(back, sStageShadow.bw2Back.x), place->groundPer128) / div);
    fx32 vy = (fx32)((s64)FX_Mul(up, place->groundPer128) / div);
    fx32 vz = (fx32)((s64)FX_Mul(FX_Mul(across, sStageShadow.bw2X.z) + FX_Mul(back, sStageShadow.bw2Back.z), place->groundPer128) / div);

    G3_Vtx((fx16)vx, (fx16)vy, (fx16)vz);
}

// The silhouette of one battler whose stream is bound this frame
static BOOL DrawSilhouette(int index, PokemonSprite *sprite, int side, const ShadowAdjust *adjust)
{
    const PokemonSpriteTransforms *transforms = &sprite->transforms;
    PokemonSpriteDrawRect frame;
    BattleStageStreamRect canvas;
    ShadowPlace place;
    VecFx32 centre, right128, down, foot;
    int streamScale = BattleStageStream_GetScale(index);
    fx32 kx, ky, hover, rotZ, offX, offZ, unitPx;
    int px, row, alpha, u, v;
    fx32 x[2], y[2];

    alpha = transforms->alpha / 2;

    if (alpha == 0 || !BattleStageSprites_GroundFrame(side, &centre, &right128, &down)) {
        return FALSE;
    }

    if (!BattleStageStream_Bind(index)) {
        return FALSE;
    }

    // The canvas box (a scaled back's box, else the whole canvas), as a whole-frame draw sees it
    frame.x = 0;
    frame.y = 0;
    frame.z = 0;
    frame.width = MON_SPRITE_FRAME_WIDTH;
    frame.height = MON_SPRITE_FRAME_HEIGHT;
    frame.u0 = 0;
    frame.v0 = 0;
    frame.u1 = MON_SPRITE_FRAME_WIDTH;
    frame.v1 = MON_SPRITE_FRAME_HEIGHT;
    BattleStageStream_CanvasRect(index, transforms, &frame, &canvas);

    // The foot point: the sprite's x (without the classic shadow's per-species x offset: the
    // silhouette lines up with the art itself) on the ground row under its feet. A front stands
    // its ground row (MON_STREAM_GROUND_V) on the bottom of its home frame; a back's feet are under
    // the text box, so its shadow starts on the side's blob row, above it, as the blob does
    px = transforms->xCenter + transforms->xOffset - 128;
    row = side ? transforms->yCenter + MON_SPRITE_FRAME_HEIGHT / 2 - BattleStageSprites_BlobRow(side) : 0;

    // bw2vis:shadow+layout: the battler's rest offset (screen px), as the sprite and the blob take it
    {
        int dx, dy;

        if (BattleStageLayout_Offset(index, &dx, &dy)) {
            px += dx;
            row += dy;
        }
    }

    foot.x = centre.x + (s32)((s64)right128.x * px / 128) + down.x * row;
    foot.y = centre.y + (s32)((s64)right128.y * px / 128) + down.y * row;
    foot.z = centre.z + (s32)((s64)right128.z * px / 128) + down.z * row;
    place.groundPer128 = VEC_Mag(&right128);

    // Screen pixels per texel: the stream's scale and the sprite's own (a negative x flips)
    kx = (fx32)((s64)streamScale * transforms->scaleX * FX32_ONE / (MON_STREAM_SCALE_ONE * MON_AFFINE_SCALE(1)));
    ky = (fx32)((s64)streamScale * transforms->scaleY * FX32_ONE / (MON_STREAM_SCALE_ONE * MON_AFFINE_SCALE(1)));
    // A floater's lift (the classic altitude, enemy fronts only) is baked into BW2's art above its
    // foot point, so BW2 lays it down behind the foot point: the shadow starts that far back
    hover = sprite->shadow.height * FX32_ONE;

    rotZ = adjust != NULL ? adjust->rotZ : SHADOW_DEFAULT_ROTZ;
    offX = adjust != NULL ? adjust->x : SHADOW_DEFAULT_X;
    offZ = adjust != NULL ? adjust->z : SHADOW_DEFAULT_Z;
    place.cosZ = FX_CosIdx((u16)rotZ);
    place.negSinZ = -FX_SinIdx((u16)rotZ);
    // World units to screen pixels: BW2's art pixels per unit, times our art's scale on screen
    unitPx = (fx32)((s64)16 * FX32_ONE * streamScale / MON_STREAM_SCALE_ONE * FX32_ONE / (side ? BW2_SCALE_FRONT : BW2_SCALE_BACK));
    place.offX = FX_Mul(offX, unitPx);
    place.offBack = -FX_Mul(offZ, unitPx);

    for (u = 0; u < 2; u++) {
        x[u] = FX_Mul(((u ? canvas.u1 : canvas.u0) - MON_STREAM_ANCHOR_U) * FX32_ONE, kx);
    }

    for (v = 0; v < 2; v++) {
        y[v] = FX_Mul((MON_STREAM_GROUND_V - (v ? canvas.v1 : canvas.v0)) * FX32_ONE, ky) + hover;
    }

    // The stream texture with texcoords as is: the arena may have left a texture matrix loaded
    G3_TexImageParam(GX_TEXFMT_PLTT16, GX_TEXGEN_NONE, GX_TEXSIZE_S128, GX_TEXSIZE_T128, GX_TEXREPEAT_NONE, GX_TEXFLIP_NONE, GX_TEXPLTTCOLOR0_TRNS, sSpriteStreamStats.vramAddr + index * STREAM_TEX_BYTES);
    G3_TexPlttBase(sStageShadow.plttAddr, GX_TEXFMT_PLTT16);
    G3_PolygonAttr(GX_LIGHTMASK_NONE, GX_POLYGONMODE_MODULATE, GX_CULL_NONE, SHADOW_POLYGON_ID, alpha, 0);
    G3_Color(GX_RGB(31, 31, 31));

    G3_PushMtx();
    G3_Translate(foot.x, foot.y, foot.z);
    G3_Scale(SHADOW_VTX_SCALE * FX32_ONE, SHADOW_VTX_SCALE * FX32_ONE, SHADOW_VTX_SCALE * FX32_ONE);
    G3_Begin(GX_BEGIN_QUADS);
    G3_TexCoord(canvas.u0 * FX32_ONE, canvas.v0 * FX32_ONE);
    SendVertex(&place, x[0], y[0]);
    G3_TexCoord(canvas.u1 * FX32_ONE, canvas.v0 * FX32_ONE);
    SendVertex(&place, x[1], y[0]);
    G3_TexCoord(canvas.u1 * FX32_ONE, canvas.v1 * FX32_ONE);
    SendVertex(&place, x[1], y[1]);
    G3_TexCoord(canvas.u0 * FX32_ONE, canvas.v1 * FX32_ONE);
    SendVertex(&place, x[0], y[1]);
    G3_End();
    G3_PopMtx(1);
    return TRUE;
}

u32 BattleStageShadow_Draw(const MtxFx44 *projection, u32 shownMask, u32 debugFlags, u32 *counter)
{
    PokemonSpriteManager *monSpriteMan;
    u32 noBlob = 0;
    BOOL started = FALSE;
    int numBattlers, i;

    sStageShadowStats.silhouetteMask = 0;
    sStageShadowStats.offMask = 0;
    sStageShadowStats.silhouettes = 0;

    if (sStageShadow.battleSys == NULL) {
        return 0;
    }

    if (!sStageShadow.axesBuilt) {
        sStageShadow.axesBuilt = BuildAxes();
    }

    monSpriteMan = BattleSystem_GetPokemonSpriteManager(sStageShadow.battleSys);
    numBattlers = BattleSystem_MaxBattlers(sStageShadow.battleSys);

    if (numBattlers > MAX_MON_SPRITES) {
        numBattlers = MAX_MON_SPRITES;
    }

    // Another screen may have used the palette VRAM while the stage shadows were not drawn
    if (sStageShadow.hasPltt && OS_GetVBlankCount() - sStageShadow.lastVBlank > SHADOW_PLTT_GAP) {
        DC_FlushRange(sShadowPalette, sizeof(sShadowPalette));
        VramTransfer_Request(NNS_GFD_DST_3D_TEX_PLTT, sStageShadow.plttAddr, sShadowPalette, sizeof(sShadowPalette));
    }

    sStageShadow.lastVBlank = OS_GetVBlankCount();

    for (i = 0; i < numBattlers; i++) {
        PokemonSprite *sprite = &monSpriteMan->sprites[i];
        int side = BattleSystem_BattlerSlot(sStageShadow.battleSys, i) & 1;
        const ShadowAdjust *adjust;

        // The blobs' rule (shownMask): nothing while hidden (Fly, Dig, a faint), cut (the faint
        // slide, the send-out reveal) or while a move hides the shadows
        if ((shownMask & (1 << i)) == 0) {
            continue;
        }

        adjust = FindAdjust(sprite, side);

        if (adjust != NULL && !adjust->shadow) {
            noBlob |= 1 << i;
            sStageShadowStats.offMask |= 1 << i;
            continue;
        }

        // Only a battler the sprite hook drew from its stream last frame, and will again: the
        // same texture, so the shadow is the frame on screen. Others keep their blob.
        if (!sStageShadow.hasPltt
            || !sStageShadow.axesBuilt
            || monSpriteMan->excludeIdentity == TRUE
            || (debugFlags & BATTLE_STAGE_DEBUG_NO_SPRITE_STREAM)
            || !BattleStage_IsSpriteStreamed(i)) {
            continue;
        }

        if (!started) {
            LoadFlatProjection(projection);
            started = TRUE;
        }

        if (DrawSilhouette(i, sprite, side, adjust)) {
            noBlob |= 1 << i;
            sStageShadowStats.silhouetteMask |= 1 << i;
            sStageShadowStats.silhouettes++;
            (*counter)++;
        }
    }

    if (started) {
        G3_MtxMode(GX_MTXMODE_PROJECTION);
        G3_LoadMtx44(projection);
        G3_MtxMode(GX_MTXMODE_POSITION_VECTOR);
    }

    if (sStageShadowStats.silhouettes > 0) {
        sStageShadowStats.drawnFrames++;
    }

    return noBlob;
}
