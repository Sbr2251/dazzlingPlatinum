#include "battle/battle_stage_stream.h"

#include <nitro.h>
#include <nnsys.h>
#include <string.h>

#include "constants/heap.h"
#include "constants/narc.h"

#include "heap.h"
#include "narc.h"
#include "pokemon_sprite.h"
#include "vram_transfer.h"

#define STREAM_ROW_BYTES  64 // the texture is 128 wide, 4bpp
#define STREAM_TEX_BYTES  (STREAM_CANVAS_HEIGHT * STREAM_ROW_BYTES)
#define STREAM_TEX_ALLOC  (MAX_MON_SPRITES * STREAM_TEX_BYTES)
#define STREAM_VRAM_END   0x20000 // as the arena textures: bank B survives the menus
#define STREAM_HEAP_SPARE 0x20000 // battle heap left free after a load
#define STREAM_MAX_SKIP   60 // vblanks one frame may advance, after a pause
#define STREAM_NO_FRAME   0xFFFF

// Pokegra files: species * 6 + (back 0, front 2) + male, palettes species * 6 + 4 + shiny
#define POKEGRA_FILES_PER_SPECIES 6

// A stream member of mon_stream.narc (tools/gen5_sprites/gen5_stream.py)
typedef struct StreamHeader {
    u16 numFrames;
    u16 numSteps;
    u8 left; // bytes
    u8 width; // bytes
    u8 top;
    u8 height;
    u32 frameOffsets[];
} StreamHeader;

typedef struct BattlerStream {
    u16 narcID; // the sprite template looked up last
    u16 character;
    StreamHeader *data; // NULL: the template has no stream
    u32 size; // of data
    const u8 *steps; // {frame, duration}
    u16 step;
    u16 shown; // frame in the texture, STREAM_NO_FRAME when it has to be sent whole
    s16 left; // vblanks the step has left
    u16 queued; // frame queued for the next VBlank, STREAM_NO_FRAME if none
    u8 *texture; // STREAM_TEX_BYTES, what the VRAM block holds; zero outside the box
} BattlerStream;

typedef struct StageStream {
    PokemonSpriteManager *monSpriteMan;
    NNSGfdTexKey texKey;
    u32 texAddr;
    BOOL hasVram;
    u32 lastVBlank;
    BattlerStream battlers[MAX_MON_SPRITES];
} StageStream;

static StageStream sStageStream;
BattleStageStreamStats sSpriteStreamStats;
static u8 sFrameBuffer[STREAM_CANVAS_WIDTH * STREAM_CANVAS_HEIGHT / 2]; // one decompressed box

void BattleStageStream_Init(PokemonSpriteManager *monSpriteMan)
{
    int i;
    u32 addr;

    memset(&sStageStream, 0, sizeof(sStageStream));
    memset(&sSpriteStreamStats, 0, sizeof(sSpriteStreamStats));
    sStageStream.monSpriteMan = monSpriteMan;
    sStageStream.lastVBlank = OS_GetVBlankCount();

    for (i = 0; i < MAX_MON_SPRITES; i++) {
        sStageStream.battlers[i].shown = STREAM_NO_FRAME;
        sStageStream.battlers[i].queued = STREAM_NO_FRAME;
        sSpriteStreamStats.frame[i] = STREAM_NO_FRAME;
    }

    sStageStream.texKey = NNS_GfdAllocTexVram(STREAM_TEX_ALLOC, FALSE, 0);

    if (sStageStream.texKey == NNS_GFD_ALLOC_ERROR_TEXKEY) {
        return;
    }

    addr = NNS_GfdGetTexKeyAddr(sStageStream.texKey);

    if (addr + STREAM_TEX_ALLOC > STREAM_VRAM_END) {
        NNS_GfdFreeTexVram(sStageStream.texKey);
        return;
    }

    sStageStream.texAddr = addr;
    sStageStream.hasVram = TRUE;
    sSpriteStreamStats.vramAddr = addr;
}

static void Unload(int index)
{
    BattlerStream *stream = &sStageStream.battlers[index];

    if (stream->data != NULL) {
        Heap_Free(stream->data);
        sSpriteStreamStats.streamBytes -= stream->size;
        stream->data = NULL;
        stream->size = 0;
    }

    if (stream->texture != NULL) {
        Heap_Free(stream->texture);
        stream->texture = NULL;
    }

    stream->shown = STREAM_NO_FRAME;
    stream->queued = STREAM_NO_FRAME;
    sSpriteStreamStats.loadedMask &= ~(1 << index);
    sSpriteStreamStats.frame[index] = STREAM_NO_FRAME;
}

void BattleStageStream_Free(void)
{
    int i;

    for (i = 0; i < MAX_MON_SPRITES; i++) {
        Unload(i);
    }

    if (sStageStream.hasVram) {
        NNS_GfdFreeTexVram(sStageStream.texKey);
        sStageStream.hasVram = FALSE;
    }

    sStageStream.monSpriteMan = NULL;
    sSpriteStreamStats.vramAddr = 0;
}

// The stream member of a template, 0 if none
static u16 FindMember(const PokemonSpriteTemplate *template)
{
    u16 member = 0;
    int species, face;

    if (template->narcID != NARC_INDEX_POKETOOL__POKEGRA__PL_POKEGRA || template->spindaSpots) {
        return 0;
    }

    species = template->character / POKEGRA_FILES_PER_SPECIES;
    face = (template->character % POKEGRA_FILES_PER_SPECIES) >> 1;

    if (face > 1) {
        return 0;
    }

    NARC_ReadFromMemberByIndexPair(&member, NARC_INDEX_BATTLE__GRAPHIC__MON_STREAM, 0, (species * 2 + face) * sizeof(u16), sizeof(u16));
    return member;
}

static void Load(int index, const PokemonSpriteTemplate *template)
{
    BattlerStream *stream = &sStageStream.battlers[index];
    u16 member;
    u32 size;
    OSTick start;

    Unload(index);
    stream->narcID = template->narcID;
    stream->character = template->character;

    member = FindMember(template);

    if (member == 0) {
        return;
    }

    start = OS_GetTick();
    size = NARC_GetMemberSizeByIndexPair(NARC_INDEX_BATTLE__GRAPHIC__MON_STREAM, member);

    if (HeapExp_FndGetTotalFreeSize(HEAP_ID_BATTLE) < size + STREAM_TEX_BYTES + STREAM_HEAP_SPARE) {
        sSpriteStreamStats.loadFailures++;
        return;
    }

    stream->texture = Heap_Alloc(HEAP_ID_BATTLE, STREAM_TEX_BYTES);
    stream->data = NARC_AllocAndReadWholeMemberByIndexPair(NARC_INDEX_BATTLE__GRAPHIC__MON_STREAM, member, HEAP_ID_BATTLE);

    if (stream->texture == NULL || stream->data == NULL) {
        sSpriteStreamStats.loadFailures++;
        Unload(index);
        return;
    }

    memset(stream->texture, 0, STREAM_TEX_BYTES);
    stream->size = size;
    stream->steps = (const u8 *)&stream->data->frameOffsets[stream->data->numFrames];
    stream->step = 0;
    stream->left = stream->steps[1];

    sSpriteStreamStats.loads++;
    sSpriteStreamStats.streamBytes += size;
    sSpriteStreamStats.loadedMask |= 1 << index;
    sSpriteStreamStats.heapFree = HeapExp_FndGetTotalFreeSize(HEAP_ID_BATTLE);

    if (OS_GetTick() - start > sSpriteStreamStats.loadTicksMax) {
        sSpriteStreamStats.loadTicksMax = OS_GetTick() - start;
    }
}

static void Advance(BattlerStream *stream, u32 elapsed, BOOL frozen)
{
    if (frozen) {
        stream->step = 0;
        stream->left = stream->steps[1];
        return;
    }

    stream->left -= elapsed;

    while (stream->left <= 0) {
        stream->step++;

        if (stream->step >= stream->data->numSteps) {
            stream->step = 0;
        }

        stream->left += stream->steps[stream->step * 2 + 1];
    }
}

// Decompresses a frame into the battler's texture copy and queues it: the box rows, or the
// whole texture when VRAM may hold something else
static void SendFrame(int index, u16 frame)
{
    BattlerStream *stream = &sStageStream.battlers[index];
    const StreamHeader *data = stream->data;
    u32 addr = sStageStream.texAddr + index * STREAM_TEX_BYTES;
    u32 offset, size;
    OSTick start = OS_GetTick();
    int row;

    MI_UncompressLZ8((const u8 *)data + data->frameOffsets[frame], sFrameBuffer);

    for (row = 0; row < data->height; row++) {
        memcpy(stream->texture + (data->top + row) * STREAM_ROW_BYTES + data->left, sFrameBuffer + row * data->width, data->width);
    }

    if (stream->shown == STREAM_NO_FRAME) {
        offset = 0;
        size = STREAM_TEX_BYTES;
    } else {
        offset = data->top * STREAM_ROW_BYTES;
        size = data->height * STREAM_ROW_BYTES;
    }

    DC_FlushRange(stream->texture + offset, size);
    sSpriteStreamStats.decodeTicksThisFrame += OS_GetTick() - start;

    if (VramTransfer_Request(NNS_GFD_DST_3D_TEX_VRAM, addr + offset, stream->texture + offset, size)) {
        stream->queued = frame;
        sSpriteStreamStats.uploads++;
        sSpriteStreamStats.bytesThisFrame += size;
    }
}

void BattleStageStream_BeginFrame(BOOL visible, BOOL frozen)
{
    u32 now, elapsed;
    int i;

    if (sStageStream.monSpriteMan == NULL) {
        return;
    }

    now = OS_GetVBlankCount();
    elapsed = now - sStageStream.lastVBlank;
    sStageStream.lastVBlank = now;

    if (elapsed > STREAM_MAX_SKIP) {
        elapsed = STREAM_MAX_SKIP;
    }

    sSpriteStreamStats.bytesThisFrame = 0;
    sSpriteStreamStats.decodeTicksThisFrame = 0;
    sSpriteStreamStats.drawnMask = 0;

    for (i = 0; i < MAX_MON_SPRITES; i++) {
        BattlerStream *stream = &sStageStream.battlers[i];
        const PokemonSprite *sprite = &sStageStream.monSpriteMan->sprites[i];

        // What was queued last frame went out at the VBlank
        if (stream->queued != STREAM_NO_FRAME) {
            stream->shown = stream->queued;
            stream->queued = STREAM_NO_FRAME;
            sSpriteStreamStats.frame[i] = stream->shown;
        }

        if (!sStageStream.hasVram || !sprite->active) {
            if (stream->data != NULL) {
                Unload(i);
            }

            stream->narcID = 0;
            stream->character = 0;
            continue;
        }

        if (sprite->template.narcID != stream->narcID || sprite->template.character != stream->character) {
            Load(i, &sprite->template);
        }

        if (stream->data == NULL) {
            continue;
        }

        // Another screen may have used the texture VRAM while the arena was hidden
        if (!visible) {
            stream->shown = STREAM_NO_FRAME;
            continue;
        }

        Advance(stream, elapsed, frozen);

        if (stream->steps[stream->step * 2] != stream->shown) {
            SendFrame(i, stream->steps[stream->step * 2]);
        }
    }

    if (sSpriteStreamStats.bytesThisFrame > sSpriteStreamStats.maxBytesPerFrame) {
        sSpriteStreamStats.maxBytesPerFrame = sSpriteStreamStats.bytesThisFrame;
    }

    if (sSpriteStreamStats.decodeTicksThisFrame > sSpriteStreamStats.maxDecodeTicks) {
        sSpriteStreamStats.maxDecodeTicks = sSpriteStreamStats.decodeTicksThisFrame;
    }
}

// What is queued now goes to VRAM at the VBlank, before the hardware renders what is drawn now
BOOL BattleStageStream_Bind(int index)
{
    PokemonSpriteManager *monSpriteMan = sStageStream.monSpriteMan;

    if (monSpriteMan == NULL
        || index < 0
        || index >= MAX_MON_SPRITES
        || sStageStream.battlers[index].data == NULL
        || (sStageStream.battlers[index].shown == STREAM_NO_FRAME && sStageStream.battlers[index].queued == STREAM_NO_FRAME)
        || monSpriteMan->sprites[index].transforms.mosaicIntensity != 0) {
        return FALSE;
    }

    G3_TexImageParam(GX_TEXFMT_PLTT16, GX_TEXGEN_TEXCOORD, GX_TEXSIZE_S128, GX_TEXSIZE_T128, GX_TEXREPEAT_NONE, GX_TEXFLIP_NONE, monSpriteMan->imageProxy.attr.plttUse, sStageStream.texAddr + index * STREAM_TEX_BYTES);
    sSpriteStreamStats.drawnMask |= 1 << index;
    return TRUE;
}

void BattleStageStream_Unbind(void)
{
    PokemonSpriteManager *monSpriteMan = sStageStream.monSpriteMan;

    G3_TexImageParam(monSpriteMan->imageProxy.attr.fmt, GX_TEXGEN_TEXCOORD, monSpriteMan->imageProxy.attr.sizeS, monSpriteMan->imageProxy.attr.sizeT, GX_TEXREPEAT_NONE, GX_TEXFLIP_NONE, monSpriteMan->imageProxy.attr.plttUse, monSpriteMan->charBaseAddr);
}
