#include "battle/battle_stage_stream.h"

#include <nitro.h>
#include <nnsys.h>
#include <string.h>

#include "constants/graphics.h"
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
// Per frame, for all battlers together. Past the budget the remaining battlers wait a frame
// (the first one in the frame's order always goes, and the order turns every frame): four
// battlers changing frame at once, or four whole textures after a menu, would otherwise take
// 8 ms of decoding or 24 KB of the VBlank's texture window
#define STREAM_DECODE_BUDGET 1600 // OS ticks, 3 ms
#define STREAM_UPLOAD_BUDGET (2 * STREAM_TEX_BYTES)

// Frames are read with FS_ReadFileAsync into a buffer MON_STREAM_READ_MISALIGN past a 32-byte
// boundary, so the card thread copies them with the CPU and never by DMA (pokemon_sprite_stream.h).
// The card thread outranks the game's, so a frame (2 KB at most, five pages) is in before
// FS_ReadFileAsync returns: 1.2 ms at worst in the emulator (readTicksMax)
#define READ_BUF_ALIGN 32

typedef struct BattlerStream {
    u16 narcID; // the sprite template looked up last
    u16 character;
    MonStreamHeader *data; // header, frame offsets and steps; NULL: the template has no stream
    u32 size; // heap this battler holds
    u32 romStart; // the member's first byte, from the start of the card
    u32 memberSize;
    const u8 *steps; // {frame, duration}
    u16 step;
    s16 left; // vblanks the step has left
    u16 texFrame; // frame in the texture copy, STREAM_NO_FRAME before the first
    u16 shown; // frame in VRAM, STREAM_NO_FRAME when it has to be sent whole
    u16 queued; // frame queued for the next VBlank, STREAM_NO_FRAME if none
    u16 bufFrame; // compressed frame waiting in the read buffer
    u16 reading; // frame the card is reading into it
    u32 readVBlank; // when the read was asked for
    u8 *texture; // STREAM_TEX_BYTES, what the VRAM block holds; zero outside the box
    void *bufAlloc;
    u8 *buf; // bufAlloc, MON_STREAM_READ_MISALIGN past a 32-byte boundary
    FSFile file; // the NARC, for this battler's background reads
} BattlerStream;

typedef struct StageStream {
    PokemonSpriteManager *monSpriteMan;
    NNSGfdTexKey texKey;
    u32 texAddr;
    BOOL hasVram;
    BOOL hasFiles;
    u32 lastVBlank;
    u8 firstBattler; // updated first this frame
    NARC *narc; // the header reads at a load, and the member table
    MonStreamIndexHeader *index; // all of member 0
    u32 indexEntries; // u16 entries in member 0
    BattlerStream battlers[MAX_MON_SPRITES];
} StageStream;

static StageStream sStageStream;
BattleStageStreamStats sSpriteStreamStats;
static u8 sFrameBuffer[STREAM_CANVAS_WIDTH * STREAM_CANVAS_HEIGHT / 2]; // one decompressed box

static void OpenFiles(void)
{
    u32 top, bottom;
    int i;

    sStageStream.narc = NARC_ctor(NARC_INDEX_BATTLE__GRAPHIC__MON_STREAM, HEAP_ID_BATTLE);

    if (sStageStream.narc == NULL) {
        return;
    }

    top = FS_GetFileImageTop(&sStageStream.narc->file);
    bottom = FS_GetFileImageBottom(&sStageStream.narc->file);

    for (i = 0; i < MAX_MON_SPRITES; i++) {
        FS_InitFile(&sStageStream.battlers[i].file);

        if (!FS_CreateFileFromRom(&sStageStream.battlers[i].file, top, bottom - top)) {
            while (--i >= 0) {
                FS_CloseFile(&sStageStream.battlers[i].file);
            }

            NARC_dtor(sStageStream.narc);
            sStageStream.narc = NULL;
            return;
        }
    }

    sStageStream.hasFiles = TRUE;
    sStageStream.index = NARC_AllocAndReadWholeMember(sStageStream.narc, 0, HEAP_ID_BATTLE);

    if (sStageStream.index != NULL) {
        sStageStream.indexEntries = NARC_GetMemberSize(sStageStream.narc, 0) / sizeof(u16);
        sSpriteStreamStats.streamBytes += sStageStream.indexEntries * sizeof(u16) + sizeof(NARC);
        sSpriteStreamStats.indexVersion = sStageStream.index->version == 0 ? 1 : sStageStream.index->version;
    }
}

static void CloseFiles(void)
{
    int i;

    if (sStageStream.index != NULL) {
        Heap_Free(sStageStream.index);
        sStageStream.index = NULL;
        sSpriteStreamStats.streamBytes -= sStageStream.indexEntries * sizeof(u16) + sizeof(NARC);
    }

    if (sStageStream.hasFiles) {
        for (i = 0; i < MAX_MON_SPRITES; i++) {
            FS_WaitAsync(&sStageStream.battlers[i].file);
            FS_CloseFile(&sStageStream.battlers[i].file);
        }

        sStageStream.hasFiles = FALSE;
    }

    if (sStageStream.narc != NULL) {
        NARC_dtor(sStageStream.narc);
        sStageStream.narc = NULL;
    }
}

void BattleStageStream_Init(PokemonSpriteManager *monSpriteMan)
{
    int i;
    u32 addr;

    memset(&sStageStream, 0, sizeof(sStageStream));
    memset(&sSpriteStreamStats, 0, sizeof(sSpriteStreamStats));
    sStageStream.monSpriteMan = monSpriteMan;
    sStageStream.lastVBlank = OS_GetVBlankCount();

    for (i = 0; i < MAX_MON_SPRITES; i++) {
        sStageStream.battlers[i].texFrame = STREAM_NO_FRAME;
        sStageStream.battlers[i].shown = STREAM_NO_FRAME;
        sStageStream.battlers[i].queued = STREAM_NO_FRAME;
        sStageStream.battlers[i].bufFrame = STREAM_NO_FRAME;
        sStageStream.battlers[i].reading = STREAM_NO_FRAME;
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

    OpenFiles();

    if (sStageStream.index == NULL) {
        CloseFiles();
        NNS_GfdFreeTexVram(sStageStream.texKey);
        return;
    }

    sStageStream.texAddr = addr;
    sStageStream.hasVram = TRUE;
    sSpriteStreamStats.vramAddr = addr;
    sSpriteStreamStats.heapFreeMin = HeapExp_FndGetTotalFreeSize(HEAP_ID_BATTLE);
}

static void Unload(int index)
{
    BattlerStream *stream = &sStageStream.battlers[index];

    // The card may still be writing the buffer
    if (stream->reading != STREAM_NO_FRAME) {
        FS_CancelFile(&stream->file);
        FS_WaitAsync(&stream->file);
        stream->reading = STREAM_NO_FRAME;
    }

    if (stream->data != NULL) {
        Heap_Free(stream->data);
        stream->data = NULL;
    }

    if (stream->texture != NULL) {
        Heap_Free(stream->texture);
        stream->texture = NULL;
    }

    if (stream->bufAlloc != NULL) {
        Heap_Free(stream->bufAlloc);
        stream->bufAlloc = NULL;
        stream->buf = NULL;
    }

    sSpriteStreamStats.streamBytes -= stream->size;
    stream->size = 0;
    stream->texFrame = STREAM_NO_FRAME;
    stream->shown = STREAM_NO_FRAME;
    stream->queued = STREAM_NO_FRAME;
    stream->bufFrame = STREAM_NO_FRAME;
    sSpriteStreamStats.loadedMask &= ~(1 << index);
    sSpriteStreamStats.frame[index] = STREAM_NO_FRAME;
    sSpriteStreamStats.member[index] = 0;
}

void BattleStageStream_Free(void)
{
    int i;

    for (i = 0; i < MAX_MON_SPRITES; i++) {
        Unload(i);
    }

    CloseFiles();

    if (sStageStream.hasVram) {
        NNS_GfdFreeTexVram(sStageStream.texKey);
        sStageStream.hasVram = FALSE;
    }

    sStageStream.monSpriteMan = NULL;
    sSpriteStreamStats.vramAddr = 0;
}

static u16 IndexEntry(u32 entry)
{
    return entry < sStageStream.indexEntries ? ((const u16 *)sStageStream.index)[entry] : 0;
}

static u16 FindMember(const PokemonSpriteTemplate *template)
{
    u32 entries[2];
    u16 member = 0;
    int i, count = MonStream_IndexEntries(sStageStream.index, template, entries);

    for (i = 0; i < count && member == 0; i++) {
        member = IndexEntry(entries[i]);
    }

    return member;
}

// Reads the stream's tables (a few hundred bytes, from the card right away) and sets up the
// background reads of its frames. The classic frame shows until the first one is in.
static void Load(int index, const PokemonSpriteTemplate *template)
{
    BattlerStream *stream = &sStageStream.battlers[index];
    NARC *narc = sStageStream.narc;
    MonStreamHeader head;
    u32 fat[2], headerSize, maxFrame, size;
    u16 member;
    OSTick start;
    int i;

    Unload(index);
    stream->narcID = template->narcID;
    stream->character = template->character;

    member = FindMember(template);

    if (member == 0 || member >= narc->numFiles) {
        return;
    }

    start = OS_GetTick();

    FS_SeekFile(&narc->file, narc->fatbStart + 12 + member * 8, FS_SEEK_SET);
    FS_ReadFile(&narc->file, fat, sizeof(fat));
    FS_SeekFile(&narc->file, narc->fimgStart + 8 + fat[0], FS_SEEK_SET);
    FS_ReadFile(&narc->file, &head, sizeof(head));

    stream->memberSize = fat[1] - fat[0];
    headerSize = MonStream_HeaderSize(&head);

    if (stream->memberSize < sizeof(head) || headerSize > stream->memberSize) {
        sSpriteStreamStats.loadFailures++;
        return;
    }

    // The heap check needs the largest frame, so the tables come first; then the frames go
    // into a buffer for one frame
    if (HeapExp_FndGetTotalFreeSize(HEAP_ID_BATTLE) < headerSize + STREAM_TEX_BYTES + STREAM_HEAP_SPARE) {
        sSpriteStreamStats.loadFailures++;
        return;
    }

    stream->data = Heap_Alloc(HEAP_ID_BATTLE, headerSize);

    if (stream->data == NULL) {
        sSpriteStreamStats.loadFailures++;
        return;
    }

    *stream->data = head;

    if (!MonStream_ReadFile(&narc->file, stream->data->frameOffsets, headerSize - sizeof(head))
        || !MonStream_IsValid(stream->data, stream->memberSize)) {
        sSpriteStreamStats.loadFailures++;
        Unload(index);
        return;
    }

    stream->romStart = FS_GetFileImageTop(&narc->file) + narc->fimgStart + 8 + fat[0];
    stream->steps = (const u8 *)&stream->data->frameOffsets[head.numFrames];
    maxFrame = 0;

    for (i = 0; i < head.numFrames; i++) {
        if (MonStream_FrameEnd(stream->data, stream->memberSize, i) - stream->data->frameOffsets[i] > maxFrame) {
            maxFrame = MonStream_FrameEnd(stream->data, stream->memberSize, i) - stream->data->frameOffsets[i];
        }
    }

    size = maxFrame + READ_BUF_ALIGN + MON_STREAM_READ_MISALIGN;

    if (HeapExp_FndGetTotalFreeSize(HEAP_ID_BATTLE) < size + STREAM_TEX_BYTES + STREAM_HEAP_SPARE) {
        sSpriteStreamStats.loadFailures++;
        Unload(index);
        return;
    }

    stream->texture = Heap_Alloc(HEAP_ID_BATTLE, STREAM_TEX_BYTES);
    stream->bufAlloc = Heap_Alloc(HEAP_ID_BATTLE, size);

    if (stream->texture == NULL || stream->bufAlloc == NULL) {
        sSpriteStreamStats.loadFailures++;
        Unload(index);
        return;
    }

    stream->buf = (u8 *)((((u32)stream->bufAlloc + READ_BUF_ALIGN - 1) & ~(READ_BUF_ALIGN - 1)) + MON_STREAM_READ_MISALIGN);
    memset(stream->texture, 0, STREAM_TEX_BYTES);
    stream->size = headerSize + STREAM_TEX_BYTES + size;
    stream->step = 0;
    stream->left = stream->steps[1];

    sSpriteStreamStats.loads++;
    sSpriteStreamStats.member[index] = member;
    sSpriteStreamStats.streamBytes += stream->size;
    sSpriteStreamStats.loadedMask |= 1 << index;
    sSpriteStreamStats.heapFree = HeapExp_FndGetTotalFreeSize(HEAP_ID_BATTLE);

    if (sSpriteStreamStats.heapFree < sSpriteStreamStats.heapFreeMin) {
        sSpriteStreamStats.heapFreeMin = sSpriteStreamStats.heapFree;
    }

    if (OS_GetTick() - start > sSpriteStreamStats.loadTicksMax) {
        sSpriteStreamStats.loadTicksMax = OS_GetTick() - start;
    }
}

// Starts the read of a frame
static void RequestFrame(int index, u16 frame)
{
    BattlerStream *stream = &sStageStream.battlers[index];
    u32 offset = stream->data->frameOffsets[frame];
    u32 size = MonStream_FrameEnd(stream->data, stream->memberSize, frame) - offset;
    OSTick start = OS_GetTick();

    if (!FS_SeekFile(&stream->file, stream->romStart + offset - FS_GetFileImageTop(&stream->file), FS_SEEK_SET)
        || FS_ReadFileAsync(&stream->file, stream->buf, size) < 0) {
        return;
    }

    if (OS_GetTick() - start > sSpriteStreamStats.readTicksMax) {
        sSpriteStreamStats.readTicksMax = OS_GetTick() - start;
    }

    stream->reading = frame;
    stream->readVBlank = OS_GetVBlankCount();
    sSpriteStreamStats.cardReads++;
    sSpriteStreamStats.cardBytes += size;
}

// A finished read leaves its frame in the buffer; a failed one drops the stream for good
static BOOL PollRead(int index)
{
    BattlerStream *stream = &sStageStream.battlers[index];
    u32 vblanks;

    if (stream->reading == STREAM_NO_FRAME || FS_IsBusy(&stream->file)) {
        return TRUE;
    }

    if (!FS_IsSucceeded(&stream->file)) {
        stream->reading = STREAM_NO_FRAME;
        sSpriteStreamStats.readFailures++;
        Unload(index);
        return FALSE;
    }

    vblanks = OS_GetVBlankCount() - stream->readVBlank;

    if (vblanks > sSpriteStreamStats.readVBlanksMax) {
        sSpriteStreamStats.readVBlanksMax = vblanks;
    }

    stream->bufFrame = stream->reading;
    stream->reading = STREAM_NO_FRAME;
    return TRUE;
}

static BOOL HasFrame(const BattlerStream *stream, u16 frame)
{
    return frame == stream->texFrame || frame == stream->bufFrame;
}

static u16 StepFrame(const BattlerStream *stream, int step)
{
    return stream->steps[step * 2];
}

// The first frame after the texture's that the steps from the current one show
static u16 NextFrame(const BattlerStream *stream)
{
    int i, step = stream->step;

    for (i = 0; i < stream->data->numSteps; i++) {
        step = step + 1 < stream->data->numSteps ? step + 1 : 0;

        if (StepFrame(stream, step) != stream->texFrame) {
            return StepFrame(stream, step);
        }
    }

    return stream->texFrame;
}

// Moves on by the vblanks gone, but never onto a step whose frame isn't in yet: the step
// before it waits for the card
static void Advance(BattlerStream *stream, u32 elapsed, BOOL frozen)
{
    int next;

    if (frozen) {
        stream->step = 0;
        stream->left = stream->steps[1];
        return;
    }

    stream->left -= elapsed;

    while (stream->left <= 0) {
        next = stream->step + 1 < stream->data->numSteps ? stream->step + 1 : 0;

        if (!HasFrame(stream, StepFrame(stream, next))) {
            stream->left = 0;
            sSpriteStreamStats.stallFrames++;
            break;
        }

        stream->step = next;
        stream->left += stream->steps[next * 2 + 1];
    }
}

// Decompresses the buffered frame into the battler's texture copy; a bad frame drops the stream
static BOOL DecodeFrame(int index)
{
    BattlerStream *stream = &sStageStream.battlers[index];
    const MonStreamHeader *data = stream->data;
    OSTick start = OS_GetTick();
    int row;

    if (!MonStream_IsFrameValid(data, stream->buf)) {
        sSpriteStreamStats.readFailures++;
        Unload(index);
        return FALSE;
    }

    MI_UncompressLZ8(stream->buf, sFrameBuffer);

    for (row = 0; row < data->height; row++) {
        memcpy(stream->texture + (data->top + row) * STREAM_ROW_BYTES + data->left, sFrameBuffer + row * data->width, data->width);
    }

    stream->texFrame = stream->bufFrame;
    stream->bufFrame = STREAM_NO_FRAME;
    sSpriteStreamStats.decodeTicksThisFrame += OS_GetTick() - start;
    return TRUE;
}

// TRUE when a battler already used the frame's budget and adding size would pass it
static BOOL OverBudget(u32 used, u32 size, u32 budget)
{
    return used != 0 && used + size > budget;
}

// Queues the texture copy: the box rows, or the whole texture when VRAM may hold something else
static void SendFrame(int index)
{
    BattlerStream *stream = &sStageStream.battlers[index];
    const MonStreamHeader *data = stream->data;
    u32 addr = sStageStream.texAddr + index * STREAM_TEX_BYTES;
    u32 offset, size;

    if (stream->shown == STREAM_NO_FRAME) {
        offset = 0;
        size = STREAM_TEX_BYTES;
    } else {
        offset = data->top * STREAM_ROW_BYTES;
        size = data->height * STREAM_ROW_BYTES;
    }

    if (OverBudget(sSpriteStreamStats.bytesThisFrame, size, STREAM_UPLOAD_BUDGET)) {
        sSpriteStreamStats.deferredUploads++;
        return;
    }

    DC_FlushRange(stream->texture + offset, size);

    if (VramTransfer_Request(NNS_GFD_DST_3D_TEX_VRAM, addr + offset, stream->texture + offset, size)) {
        stream->queued = stream->texFrame;
        sSpriteStreamStats.uploads++;
        sSpriteStreamStats.bytesThisFrame += size;
    }
}

static void UpdateBattler(int index, u32 elapsed, BOOL visible, BOOL frozen)
{
    BattlerStream *stream = &sStageStream.battlers[index];
    u16 want, next;

    if (!PollRead(index)) {
        return;
    }

    // Another screen may have used the texture VRAM while the arena was hidden; the texture
    // copy is still good
    if (!visible) {
        stream->shown = STREAM_NO_FRAME;
        return;
    }

    if (stream->texFrame != STREAM_NO_FRAME) {
        Advance(stream, elapsed, frozen);
    }

    want = StepFrame(stream, stream->step);

    if (want != stream->texFrame && want == stream->bufFrame && !OverBudget(sSpriteStreamStats.decodeTicksThisFrame, 0, STREAM_DECODE_BUDGET)) {
        if (stream->texFrame == STREAM_NO_FRAME) {
            stream->left = stream->steps[stream->step * 2 + 1];
        }

        if (!DecodeFrame(index)) {
            return;
        }
    }

    if (stream->texFrame != STREAM_NO_FRAME && stream->texFrame != stream->shown) {
        SendFrame(index);
    }

    // One frame ahead: the step's own if it is still missing, else the next one the steps
    // change to
    next = want != stream->texFrame ? want : NextFrame(stream);

    if (stream->bufFrame != STREAM_NO_FRAME && stream->bufFrame != next) {
        stream->bufFrame = STREAM_NO_FRAME; // after a freeze or a stall: not the one needed
    }

    if (stream->reading == STREAM_NO_FRAME && stream->bufFrame == STREAM_NO_FRAME && next != stream->texFrame) {
        RequestFrame(index, next);
    }
}

void BattleStageStream_BeginFrame(BOOL visible, BOOL frozen)
{
    u32 now, elapsed;
    int k;

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

    sStageStream.firstBattler = (sStageStream.firstBattler + 1) % MAX_MON_SPRITES;

    for (k = 0; k < MAX_MON_SPRITES; k++) {
        int i = (sStageStream.firstBattler + k) % MAX_MON_SPRITES;
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

        if (stream->data != NULL) {
            UpdateBattler(i, elapsed, visible, frozen);
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
    sSpriteStreamStats.drawnEver |= 1 << index;
    return TRUE;
}

void BattleStageStream_Unbind(void)
{
    PokemonSpriteManager *monSpriteMan = sStageStream.monSpriteMan;

    G3_TexImageParam(monSpriteMan->imageProxy.attr.fmt, GX_TEXGEN_TEXCOORD, monSpriteMan->imageProxy.attr.sizeS, monSpriteMan->imageProxy.attr.sizeT, GX_TEXREPEAT_NONE, GX_TEXFLIP_NONE, monSpriteMan->imageProxy.attr.plttUse, monSpriteMan->charBaseAddr);
}

const u8 *BattleStageStream_GetFrame(int index)
{
    if (sStageStream.monSpriteMan == NULL
        || index < 0
        || index >= MAX_MON_SPRITES
        || sStageStream.battlers[index].data == NULL
        || sStageStream.battlers[index].texFrame == STREAM_NO_FRAME) {
        return NULL;
    }

    return sStageStream.battlers[index].texture;
}

int BattleStageStream_GetScale(int index)
{
    if (index < 0 || index >= MAX_MON_SPRITES || sStageStream.battlers[index].data == NULL) {
        return MON_STREAM_SCALE_ONE;
    }

    return MonStream_Scale(sStageStream.battlers[index].data);
}

void BattleStageStream_CanvasRect(int index, const PokemonSpriteTransforms *transforms, const PokemonSpriteDrawRect *rect, BattleStageStreamRect *out)
{
    const MonStreamHeader *data = sStageStream.battlers[index].data;
    int scale = MonStream_Scale(data);
    int boxU0, boxV0, boxU1, boxV1; // what a side reaching the frame's edge extends to
    int frameX, frameY, frameW, frameH; // the classic frame on screen; flipped when negative
    int x0, x1, y0, y1; // the quad in the frame, in eighths of a pixel

    // At 1:1 the whole canvas; scaled, the stream's box, as the canvas could pass the widest mesh
    if (scale == MON_STREAM_SCALE_ONE) {
        boxU0 = 0;
        boxV0 = 0;
        boxU1 = STREAM_CANVAS_WIDTH;
        boxV1 = STREAM_CANVAS_HEIGHT;
    } else {
        boxU0 = data->left * 2;
        boxV0 = data->top;
        boxU1 = (data->left + data->width) * 2;
        boxV1 = data->top + data->height;
    }

    if (!transforms->partialDraw) {
        frameX = rect->x;
        frameY = rect->y;
        frameW = rect->width;
        frameH = rect->height;
        out->u0 = boxU0;
        out->v0 = boxV0;
        out->u1 = boxU1;
        out->v1 = boxV1;
    } else {
        // The window [drawXOffset, + drawWidth) x [drawYOffset, + drawHeight) of the frame,
        // drawn 1:1
        frameX = rect->x - transforms->drawXOffset;
        frameY = rect->y - transforms->drawYOffset;
        frameW = MON_SPRITE_FRAME_WIDTH;
        frameH = MON_SPRITE_FRAME_HEIGHT;
        x1 = transforms->drawXOffset + transforms->drawWidth;
        y1 = transforms->drawYOffset + transforms->drawHeight;
        out->u0 = transforms->drawXOffset == 0 ? boxU0 : MON_STREAM_TEXEL_U(transforms->drawXOffset, scale);
        out->v0 = transforms->drawYOffset == 0 ? boxV0 : MON_STREAM_TEXEL_V(transforms->drawYOffset, scale);
        out->u1 = x1 >= MON_SPRITE_FRAME_WIDTH ? boxU1 : MON_STREAM_TEXEL_U(x1 - 1, scale) + 1;
        out->v1 = y1 >= MON_SPRITE_FRAME_HEIGHT ? boxV1 : MON_STREAM_TEXEL_V(y1 - 1, scale) + 1;
    }

    x0 = MON_STREAM_FRAME_X8(out->u0, scale);
    x1 = MON_STREAM_FRAME_X8(out->u1, scale);
    y0 = MON_STREAM_FRAME_Y8(out->v0, scale);
    y1 = MON_STREAM_FRAME_Y8(out->v1, scale);
    out->x = frameX + x0 * frameW / (MON_SPRITE_FRAME_WIDTH * MON_STREAM_SCALE_ONE);
    out->y = frameY + y0 * frameH / (MON_SPRITE_FRAME_HEIGHT * MON_STREAM_SCALE_ONE);
    out->width = x1 * frameW / (MON_SPRITE_FRAME_WIDTH * MON_STREAM_SCALE_ONE) - x0 * frameW / (MON_SPRITE_FRAME_WIDTH * MON_STREAM_SCALE_ONE);
    out->height = y1 * frameH / (MON_SPRITE_FRAME_HEIGHT * MON_STREAM_SCALE_ONE) - y0 * frameH / (MON_SPRITE_FRAME_HEIGHT * MON_STREAM_SCALE_ONE);
    out->centreX = frameX * FX32_ONE + (x0 + x1) * frameW * (FX32_ONE / 2 / MON_STREAM_SCALE_ONE) / MON_SPRITE_FRAME_WIDTH;
    out->centreY = frameY * FX32_ONE + (y0 + y1) * frameH * (FX32_ONE / 2 / MON_STREAM_SCALE_ONE) / MON_SPRITE_FRAME_HEIGHT;
}
