#include "pokemon_sprite_stream.h"

#include <nitro.h>
#include <string.h>

#include "constants/graphics.h"
#include "constants/narc.h"

#include "heap.h"
#include "narc.h"
#include "pokemon_sprite.h"
#include "unk_020366A0.h"

#define CHAR_ROW_BYTES    0x80 // the manager's char data is a 256 wide 4bpp texture
#define SLOT_ROW_BYTES    (MON_SPRITE_FRAME_WIDTH / 2)
#define CANVAS_ROW_BYTES  (MON_STREAM_CANVAS_WIDTH / 2)
#define CLASSIC_LEFT_BYTE (MON_STREAM_CLASSIC_LEFT / 2)
#define FRAME_BUFFER_SIZE (CANVAS_ROW_BYTES * MON_STREAM_CANVAS_HEIGHT) // the largest box
#define MAX_SKIP          60 // vblanks one frame may advance, after a pause
#define NO_FRAME          0xFFFF
#define LZ77_TYPE         0x10
#define RESIDENT_MAX      0x6000 // larger members are paged: reading them whole stalls a frame or two

// Pokegra files: species * 6 + (back 0, front 2) + male, palettes species * 6 + 4 + shiny
#define POKEGRA_FILES_PER_SPECIES 6
#define POKEGRA_MAX_FACE_FILE     4

typedef struct SpriteStream {
    u16 narcID; // the template looked up last
    u16 character;
    u8 lookedUp;
    u8 owned; // the char data holds a stream frame, so the classic frames must be reloaded
    u16 written; // frame written over the slot; NO_FRAME when the whole slot must be written
    u32 slotOffset; // of the slot written last, in the char data
    MonStreamHeader *data; // NULL: the template has no stream. The whole member, or (paged) its header only
    const u8 *steps; // {frame, duration}
    u8 paged; // frames are read from the card when they are drawn
    u32 memberSize;
    u32 fileOffset; // paged: the member's start in the open NARC
    u16 step;
    s16 left; // vblanks the step has left
} SpriteStream;

struct PokemonSpriteStreamState {
    u32 mask;
    u32 frozenMask;
    u32 heapSpare;
    u32 lastVBlank;
    u32 elapsed; // vblanks since the last drawn frame
    u8 *frameBuffer; // one decompressed box, allocated with the first stream
    u8 *packed; // paged: one frame as read from the card
    u32 packedSize;
    NARC *narc; // paged: kept open while the manager lives
    u16 dirtyTop; // char data rows [top, bottom) and bytes [left, right) to send at the next VBlank
    u16 dirtyBottom;
    u16 dirtyLeft;
    u16 dirtyRight;
    SpriteStream sprites[MAX_MON_SPRITES];
};

MonSpriteStreamStats sMonSpriteStreamStats;
static MonStreamIndexHeader sIndexHeader;
static BOOL sIndexHeaderRead;

static void ReadIndexHeader(void)
{
    if (!sIndexHeaderRead) {
        NARC_ReadFromMemberByIndexPair(&sIndexHeader, NARC_INDEX_BATTLE__GRAPHIC__MON_STREAM, 0, 0, sizeof(sIndexHeader));
        sIndexHeaderRead = TRUE;
    }
}

static u16 ReadIndexEntry(u32 entry)
{
    u16 member = 0;

    NARC_ReadFromMemberByIndexPair(&member, NARC_INDEX_BATTLE__GRAPHIC__MON_STREAM, 0, entry * sizeof(u16), sizeof(u16));
    return member;
}

int MonStream_IndexEntries(const MonStreamIndexHeader *index, const PokemonSpriteTemplate *template, u32 entries[2])
{
    u32 base = sizeof(MonStreamIndexHeader) / sizeof(u16);
    int file;

    if (template->spindaSpots) {
        return 0;
    }

    if (index->version == 0) {
        // Step 1: u16 [species][back, front], PL_POKEGRA only
        file = template->character % POKEGRA_FILES_PER_SPECIES;

        if (template->narcID != NARC_INDEX_POKETOOL__POKEGRA__PL_POKEGRA || file >= POKEGRA_MAX_FACE_FILE) {
            return 0;
        }

        entries[0] = template->character / POKEGRA_FILES_PER_SPECIES * 2 + (file >> 1);
        return 1;
    }

    if (index->version != MON_STREAM_INDEX_VERSION) {
        return 0;
    }

    if (template->narcID == NARC_INDEX_POKETOOL__POKEGRA__PL_POKEGRA) {
        if (template->character >= index->numPokegra) {
            return 0;
        }

        entries[0] = base + template->character;
        file = template->character % POKEGRA_FILES_PER_SPECIES;

        // Female files are even; most species share the male art
        if (file < POKEGRA_MAX_FACE_FILE && (file & 1) == 0 && template->character + 1 < index->numPokegra) {
            entries[1] = base + template->character + 1;
            return 2;
        }

        return 1;
    }

    if (template->narcID == NARC_INDEX_POKETOOL__POKEGRA__PL_OTHERPOKE && template->character < index->numOtherpoke) {
        entries[0] = base + index->numPokegra + template->character;
        return 1;
    }

    return 0;
}

u16 MonStream_FindMember(const PokemonSpriteTemplate *template)
{
    u32 entries[2];
    u16 member = 0;
    int i, count;

    ReadIndexHeader();
    count = MonStream_IndexEntries(&sIndexHeader, template, entries);

    for (i = 0; i < count && member == 0; i++) {
        member = ReadIndexEntry(entries[i]);
    }

    return member;
}

BOOL MonStream_ReadFile(FSFile *file, void *dst, u32 size)
{
    // A first word read alone puts the rest off the 32-byte boundary
    if (((u32)dst & 31) == 0 && size > 4) {
        if (FS_ReadFile(file, dst, 4) != 4) {
            return FALSE;
        }

        dst = (u8 *)dst + 4;
        size -= 4;
    }

    return FS_ReadFile(file, dst, size) == (s32)size;
}

u32 MonStream_HeaderSize(const MonStreamHeader *data)
{
    return sizeof(MonStreamHeader) + data->numFrames * sizeof(u32) + data->numSteps * 2;
}

BOOL MonStream_IsValid(const MonStreamHeader *data, u32 memberSize)
{
    u32 i, end;

    if (memberSize < sizeof(MonStreamHeader)
        || data->numFrames == 0
        || data->numSteps == 0
        || data->scale > MON_STREAM_MAX_SCALE
        || data->width == 0
        || data->height == 0
        || data->left + data->width > CANVAS_ROW_BYTES
        || data->top + data->height > MON_STREAM_CANVAS_HEIGHT
        || MonStream_HeaderSize(data) > memberSize) {
        return FALSE;
    }

    for (i = 0; i < data->numFrames; i++) {
        end = i + 1 < data->numFrames ? data->frameOffsets[i + 1] : memberSize;

        if (data->frameOffsets[i] < MonStream_HeaderSize(data)
            || (data->frameOffsets[i] & 3)
            || end > memberSize
            || data->frameOffsets[i] + 4 > end) {
            return FALSE;
        }
    }

    for (i = 0; i < data->numSteps; i++) {
        const u8 *step = (const u8 *)&data->frameOffsets[data->numFrames] + i * 2;

        if (step[0] >= data->numFrames || step[1] == 0) {
            return FALSE;
        }
    }

    return TRUE;
}

u32 MonStream_FrameEnd(const MonStreamHeader *data, u32 memberSize, u16 frame)
{
    return frame + 1 < data->numFrames ? data->frameOffsets[frame + 1] : memberSize;
}

BOOL MonStream_IsFrameValid(const MonStreamHeader *data, const u8 *packed)
{
    u32 header = packed[0] | (packed[1] << 8) | (packed[2] << 16) | (packed[3] << 24);

    return (header & 0xFF) == LZ77_TYPE && (header >> 8) == (u32)data->width * data->height;
}

static struct PokemonSpriteStreamState *GetState(PokemonSpriteManager *monSpriteMan)
{
    struct PokemonSpriteStreamState *state = monSpriteMan->stream;
    int i;

    if (state != NULL) {
        return state;
    }

    if (HeapExp_FndGetTotalFreeSize(monSpriteMan->heapID) < sizeof(*state) + MON_STREAM_DEFAULT_HEAP_SPARE) {
        return NULL;
    }

    state = Heap_AllocAtEnd(monSpriteMan->heapID, sizeof(*state));

    if (state == NULL) {
        return NULL;
    }

    memset(state, 0, sizeof(*state));
    state->heapSpare = MON_STREAM_DEFAULT_HEAP_SPARE;
    state->lastVBlank = OS_GetVBlankCount();

    for (i = 0; i < MAX_MON_SPRITES; i++) {
        state->sprites[i].written = NO_FRAME;
    }

    monSpriteMan->stream = state;
    return state;
}

static void Unload(PokemonSpriteManager *monSpriteMan, int index)
{
    SpriteStream *stream = &monSpriteMan->stream->sprites[index];

    if (stream->owned) {
        monSpriteMan->sprites[index].needReloadChar = TRUE;
        stream->owned = FALSE;
    }

    if (stream->data != NULL) {
        Heap_Free(stream->data);
        stream->data = NULL;
    }

    stream->lookedUp = FALSE;
    stream->paged = FALSE;
    stream->written = NO_FRAME;
    sMonSpriteStreamStats.loadedMask &= ~(1 << index);
    sMonSpriteStreamStats.pagedMask &= ~(1 << index);
    sMonSpriteStreamStats.frame[index] = NO_FRAME;
}

void PokemonSpriteManager_SetStreamMask(PokemonSpriteManager *monSpriteMan, u32 mask)
{
    struct PokemonSpriteStreamState *state;
    int i;

    mask &= (1 << MAX_MON_SPRITES) - 1;

    // Off: the screen gets all the heap back, the open NARC included
    if (mask == 0) {
        PokemonSpriteStream_Free(monSpriteMan);
        return;
    }

    state = GetState(monSpriteMan);

    if (state == NULL) {
        return;
    }

    for (i = 0; i < MAX_MON_SPRITES; i++) {
        if ((mask & (1 << i)) == 0) {
            Unload(monSpriteMan, i);
        }
    }

    state->mask = mask;
}

void PokemonSpriteManager_SetStreamHeapSpare(PokemonSpriteManager *monSpriteMan, u32 bytes)
{
    struct PokemonSpriteStreamState *state = GetState(monSpriteMan);

    if (state != NULL) {
        state->heapSpare = bytes;
    }
}

void PokemonSpriteManager_SetStreamFrozenMask(PokemonSpriteManager *monSpriteMan, u32 mask)
{
    if (monSpriteMan->stream != NULL) {
        monSpriteMan->stream->frozenMask = mask;
    }
}

void PokemonSpriteStream_Free(PokemonSpriteManager *monSpriteMan)
{
    int i;

    if (monSpriteMan->stream == NULL) {
        return;
    }

    for (i = 0; i < MAX_MON_SPRITES; i++) {
        Unload(monSpriteMan, i);
    }

    if (monSpriteMan->stream->frameBuffer != NULL) {
        Heap_Free(monSpriteMan->stream->frameBuffer);
    }

    if (monSpriteMan->stream->packed != NULL) {
        Heap_Free(monSpriteMan->stream->packed);
    }

    if (monSpriteMan->stream->narc != NULL) {
        NARC_dtor(monSpriteMan->stream->narc);
    }

    Heap_Free(monSpriteMan->stream);
    monSpriteMan->stream = NULL;
    sMonSpriteStreamStats.streamMask = 0;
    sMonSpriteStreamStats.drawnMask = 0;
}

// The largest packed frame of a valid member
static u32 MaxPackedSize(const MonStreamHeader *data, u32 size)
{
    u32 i, max = 0;

    for (i = 0; i < data->numFrames; i++) {
        if (MonStream_FrameEnd(data, size, i) - data->frameOffsets[i] > max) {
            max = MonStream_FrameEnd(data, size, i) - data->frameOffsets[i];
        }
    }

    return max;
}

static BOOL AllocBuffers(PokemonSpriteManager *monSpriteMan, u32 packedSize)
{
    struct PokemonSpriteStreamState *state = monSpriteMan->stream;

    if (state->frameBuffer == NULL) {
        state->frameBuffer = Heap_AllocAtEnd(monSpriteMan->heapID, FRAME_BUFFER_SIZE);

        if (state->frameBuffer == NULL) {
            return FALSE;
        }
    }

    if (packedSize > state->packedSize) {
        if (state->packed != NULL) {
            Heap_Free(state->packed);
        }

        state->packed = Heap_AllocAtEnd(monSpriteMan->heapID, packedSize);
        state->packedSize = state->packed != NULL ? packedSize : 0;

        if (state->packed == NULL) {
            return FALSE;
        }
    }

    return TRUE;
}

// The first size bytes of the member into stream->data
static BOOL ReadMember(struct PokemonSpriteStreamState *state, SpriteStream *stream, u32 size)
{
    return FS_SeekFile(&state->narc->file, stream->fileOffset, FS_SEEK_SET) && MonStream_ReadFile(&state->narc->file, stream->data, size);
}

// Reads the stream of sprite index: the whole member when the heap has room for it, else its
// header only, and each frame is then read from the card when it is drawn (paged)
static void Load(PokemonSpriteManager *monSpriteMan, int index)
{
    struct PokemonSpriteStreamState *state = monSpriteMan->stream;
    SpriteStream *stream = &state->sprites[index];
    const PokemonSpriteTemplate *template = &monSpriteMan->sprites[index].template;
    MonStreamHeader header;
    u16 member;
    u32 size, headerSize, packedSize, frameNeed, fatStart;
    OSTick start;

    Unload(monSpriteMan, index);
    stream->narcID = template->narcID;
    stream->character = template->character;
    stream->lookedUp = TRUE;

    // An allocation failure during communication resets the game
    if (CommMan_IsInitialized()) {
        return;
    }

    member = MonStream_FindMember(template);

    if (member == 0) {
        return;
    }

    start = OS_GetTick();

    if (state->narc == NULL) {
        if (HeapExp_FndGetTotalFreeSize(monSpriteMan->heapID) < sizeof(NARC) + state->heapSpare) {
            sMonSpriteStreamStats.loadFailures++;
            return;
        }

        state->narc = NARC_ctor(NARC_INDEX_BATTLE__GRAPHIC__MON_STREAM, monSpriteMan->heapID);

        if (state->narc == NULL) {
            sMonSpriteStreamStats.loadFailures++;
            return;
        }
    }

    if (member >= NARC_GetFileCount(state->narc)) {
        return;
    }

    size = NARC_GetMemberSize(state->narc, member);

    if (size < sizeof(header)) {
        return;
    }

    FS_SeekFile(&state->narc->file, state->narc->fatbStart + 12 + member * 8, FS_SEEK_SET);
    FS_ReadFile(&state->narc->file, &fatStart, sizeof(fatStart));
    stream->fileOffset = state->narc->fimgStart + 8 + fatStart;
    FS_SeekFile(&state->narc->file, stream->fileOffset, FS_SEEK_SET);
    FS_ReadFile(&state->narc->file, &header, sizeof(header));
    headerSize = MonStream_HeaderSize(&header);
    frameNeed = state->frameBuffer == NULL ? FRAME_BUFFER_SIZE : 0;

    if (headerSize > size) {
        return;
    }

    // Whole members only when that leaves twice the spare: the screen may allocate later
    if (size <= RESIDENT_MAX && HeapExp_FndGetTotalFreeSize(monSpriteMan->heapID) >= size + frameNeed + state->heapSpare * 2) {
        stream->data = Heap_AllocAtEnd(monSpriteMan->heapID, size);

        if (stream->data != NULL && !ReadMember(state, stream, size)) {
            Heap_Free(stream->data);
            stream->data = NULL;
        }
    } else if (HeapExp_FndGetTotalFreeSize(monSpriteMan->heapID) >= headerSize + frameNeed + state->heapSpare) {
        stream->data = Heap_AllocAtEnd(monSpriteMan->heapID, headerSize);

        if (stream->data != NULL && !ReadMember(state, stream, headerSize)) {
            Heap_Free(stream->data);
            stream->data = NULL;
        } else if (stream->data != NULL) {
            stream->paged = TRUE;
        }
    }

    if (stream->data == NULL || !MonStream_IsValid(stream->data, size)) {
        sMonSpriteStreamStats.loadFailures++;
        Unload(monSpriteMan, index);
        stream->lookedUp = TRUE;
        return;
    }

    packedSize = 0;

    if (stream->paged) {
        packedSize = MaxPackedSize(stream->data, size);

        if (packedSize > state->packedSize
            && HeapExp_FndGetTotalFreeSize(monSpriteMan->heapID) < packedSize + frameNeed + state->heapSpare) {
            sMonSpriteStreamStats.loadFailures++;
            Unload(monSpriteMan, index);
            stream->lookedUp = TRUE;
            return;
        }

    }

    if (!AllocBuffers(monSpriteMan, packedSize)) {
        sMonSpriteStreamStats.loadFailures++;
        Unload(monSpriteMan, index);
        stream->lookedUp = TRUE;
        return;
    }

    stream->memberSize = size;
    stream->steps = (const u8 *)&stream->data->frameOffsets[stream->data->numFrames];
    stream->step = 0;
    stream->left = stream->steps[1];

    sMonSpriteStreamStats.loads++;
    sMonSpriteStreamStats.loadedMask |= 1 << index;
    sMonSpriteStreamStats.heapFree = HeapExp_FndGetTotalFreeSize(monSpriteMan->heapID);

    if (stream->paged) {
        sMonSpriteStreamStats.pagedMask |= 1 << index;
    }

    if (OS_GetTick() - start > sMonSpriteStreamStats.loadTicksMax) {
        sMonSpriteStreamStats.loadTicksMax = OS_GetTick() - start;
    }
}

void PokemonSpriteStream_BeginFrame(PokemonSpriteManager *monSpriteMan)
{
    struct PokemonSpriteStreamState *state = monSpriteMan->stream;
    u32 now;
    int i;

    if (state == NULL) {
        return;
    }

    now = OS_GetVBlankCount();
    state->elapsed = now - state->lastVBlank;
    state->lastVBlank = now;

    if (state->elapsed > MAX_SKIP) {
        state->elapsed = MAX_SKIP;
    }

    sMonSpriteStreamStats.streamMask = state->mask;
    sMonSpriteStreamStats.drawnMask = 0;
    sMonSpriteStreamStats.bytesThisFrame = 0;

    // Deleted sprites give their heap back
    for (i = 0; i < MAX_MON_SPRITES; i++) {
        if (!monSpriteMan->sprites[i].active && state->sprites[i].lookedUp) {
            state->sprites[i].owned = FALSE;
            Unload(monSpriteMan, i);
        }
    }
}

void PokemonSpriteStream_Invalidate(PokemonSpriteManager *monSpriteMan, int index)
{
    if (monSpriteMan->stream != NULL) {
        monSpriteMan->stream->sprites[index].owned = FALSE;
        monSpriteMan->stream->sprites[index].written = NO_FRAME;
    }
}

static void Advance(SpriteStream *stream, u32 elapsed, BOOL frozen)
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

static inline u8 SwapNybbles(u8 value)
{
    return (value >> 4) | (value << 4);
}

// The packed frame, read from the card when the stream is paged; NULL when it can't be decoded
static const u8 *GetPackedFrame(struct PokemonSpriteStreamState *state, SpriteStream *stream, u16 frame)
{
    const MonStreamHeader *data = stream->data;
    u32 offset = data->frameOffsets[frame];
    u32 size;
    const u8 *packed;
    OSTick start;

    if (stream->paged) {
        size = MonStream_FrameEnd(data, stream->memberSize, frame) - offset;

        if (size > state->packedSize) {
            return NULL;
        }

        start = OS_GetTick();

        if (!FS_SeekFile(&state->narc->file, stream->fileOffset + offset, FS_SEEK_SET)
            || !MonStream_ReadFile(&state->narc->file, state->packed, size)) {
            return NULL;
        }

        sMonSpriteStreamStats.cardReads++;

        if (OS_GetTick() - start > sMonSpriteStreamStats.readTicksMax) {
            sMonSpriteStreamStats.readTicksMax = OS_GetTick() - start;
        }

        packed = state->packed;
    } else {
        packed = (const u8 *)data + offset;
    }

    return MonStream_IsFrameValid(data, packed) ? packed : NULL;
}

// Decompresses a frame and writes its classic window over the slot: the rows the box covers,
// or the whole slot. Queues the written rows for the next VBlank.
static BOOL WriteFrame(PokemonSpriteManager *monSpriteMan, int index, u16 frame, u32 slotOffset, BOOL whole)
{
    struct PokemonSpriteStreamState *state = monSpriteMan->stream;
    const MonStreamHeader *data = state->sprites[index].data;
    const u8 *packed;
    BOOL flip = monSpriteMan->sprites[index].transforms.flipH;
    u8 *slot = monSpriteMan->charRawData + slotOffset;
    int scale = MonStream_Scale(data);
    int boxTop = (data->top - MON_STREAM_GROUND_V) * scale + MON_STREAM_FEET_Y; // in slot rows
    int boxBottom = boxTop + data->height * scale;
    int y0, y1, y, x, canvasByte, u;
    u32 row0, row1, left;
    OSIntrMode intrMode;
    OSTick start = OS_GetTick();

    packed = GetPackedFrame(state, &state->sprites[index], frame);

    if (packed == NULL) {
        sMonSpriteStreamStats.badFrames++;
        return FALSE;
    }

    MI_UncompressLZ8(packed, state->frameBuffer);

    if (whole) {
        y0 = 0;
        y1 = MON_SPRITE_FRAME_HEIGHT;
    } else {
        y0 = boxTop < 0 ? 0 : boxTop;
        y1 = boxBottom > MON_SPRITE_FRAME_HEIGHT ? MON_SPRITE_FRAME_HEIGHT : boxBottom;
    }

    for (y = y0; y < y1; y++) {
        u8 *dst = slot + y * CHAR_ROW_BYTES;
        const u8 *src = state->frameBuffer + (MON_STREAM_TEXEL_V(y, scale) - data->top) * data->width - data->left; // indexed by canvas byte

        if (y < boxTop || y >= boxBottom) {
            memset(dst, 0, SLOT_ROW_BYTES);
            continue;
        }

        if (scale == 1) {
            for (x = 0; x < SLOT_ROW_BYTES; x++) {
                canvasByte = CLASSIC_LEFT_BYTE + (flip ? SLOT_ROW_BYTES - 1 - x : x);

                if (canvasByte < data->left || canvasByte >= data->left + data->width) {
                    dst[x] = 0;
                } else {
                    dst[x] = flip ? SwapNybbles(src[canvasByte]) : src[canvasByte];
                }
            }

            continue;
        }

        // Scaled up: pixel by pixel, the left pixel in the low nibble
        memset(dst, 0, SLOT_ROW_BYTES);

        for (x = 0; x < MON_SPRITE_FRAME_WIDTH; x++) {
            u = MON_STREAM_TEXEL_U(flip ? MON_SPRITE_FRAME_WIDTH - 1 - x : x, scale);
            canvasByte = u / 2;

            if (canvasByte >= data->left && canvasByte < data->left + data->width) {
                dst[x / 2] |= ((src[canvasByte] >> ((u & 1) * 4)) & 0xF) << ((x & 1) * 4);
            }
        }
    }

    if (y1 <= y0) {
        return TRUE;
    }

    row0 = slotOffset / CHAR_ROW_BYTES + y0;
    row1 = slotOffset / CHAR_ROW_BYTES + y1;
    left = slotOffset % CHAR_ROW_BYTES;
    DC_FlushRange(monSpriteMan->charRawData + row0 * CHAR_ROW_BYTES, (row1 - row0) * CHAR_ROW_BYTES);

    intrMode = OS_DisableInterrupts();

    if (state->dirtyTop >= state->dirtyBottom) {
        state->dirtyTop = row0;
        state->dirtyBottom = row1;
        state->dirtyLeft = left;
        state->dirtyRight = left + SLOT_ROW_BYTES;
    } else {
        state->dirtyTop = row0 < state->dirtyTop ? row0 : state->dirtyTop;
        state->dirtyBottom = row1 > state->dirtyBottom ? row1 : state->dirtyBottom;
        state->dirtyLeft = left < state->dirtyLeft ? left : state->dirtyLeft;
        state->dirtyRight = left + SLOT_ROW_BYTES > state->dirtyRight ? left + SLOT_ROW_BYTES : state->dirtyRight;
    }

    OS_RestoreInterrupts(intrMode);

    sMonSpriteStreamStats.frames++;
    sMonSpriteStreamStats.bytesThisFrame += (y1 - y0) * SLOT_ROW_BYTES;

    if (sMonSpriteStreamStats.bytesThisFrame > sMonSpriteStreamStats.maxBytesPerFrame) {
        sMonSpriteStreamStats.maxBytesPerFrame = sMonSpriteStreamStats.bytesThisFrame;
    }

    if (OS_GetTick() - start > sMonSpriteStreamStats.decodeTicksMax) {
        sMonSpriteStreamStats.decodeTicksMax = OS_GetTick() - start;
    }

    return TRUE;
}

void PokemonSpriteStream_UpdateSprite(PokemonSpriteManager *monSpriteMan, int index, int u0, int v0)
{
    struct PokemonSpriteStreamState *state = monSpriteMan->stream;
    PokemonSprite *sprite = &monSpriteMan->sprites[index];
    SpriteStream *stream;
    u32 slotOffset;
    u16 frame;

    if (state == NULL || (state->mask & (1 << index)) == 0) {
        return;
    }

    stream = &state->sprites[index];

    if (!stream->lookedUp || sprite->template.narcID != stream->narcID || sprite->template.character != stream->character) {
        Load(monSpriteMan, index);
    }

    if (stream->data == NULL) {
        return;
    }

    // Classic only: the char loader flips vertically and applies the mosaic itself
    if (sprite->transforms.flipV || sprite->transforms.mosaicIntensity != 0) {
        if (stream->owned) {
            sprite->needReloadChar = TRUE;
            stream->owned = FALSE;
        }

        stream->written = NO_FRAME;
        return;
    }

    Advance(stream, state->elapsed, (state->frozenMask & (1 << index)) != 0);

    frame = stream->steps[stream->step * 2];
    slotOffset = v0 * CHAR_ROW_BYTES + u0 / 2;

    if (slotOffset + (MON_SPRITE_FRAME_HEIGHT - 1) * CHAR_ROW_BYTES + SLOT_ROW_BYTES > monSpriteMan->charSize) {
        return;
    }

    if (stream->written == NO_FRAME || stream->slotOffset != slotOffset || stream->written != frame) {
        // The slot may hold half a frame now: a bad stream gives the sprite its classic frames back
        stream->owned = TRUE;

        if (!WriteFrame(monSpriteMan, index, frame, slotOffset, stream->written == NO_FRAME || stream->slotOffset != slotOffset)) {
            Unload(monSpriteMan, index);
            stream->lookedUp = TRUE;
            return;
        }
    }

    stream->written = frame;
    stream->slotOffset = slotOffset;
    stream->owned = TRUE;
    sMonSpriteStreamStats.drawnMask |= 1 << index;
    sMonSpriteStreamStats.frame[index] = frame;
}

void PokemonSpriteStream_Upload(PokemonSpriteManager *monSpriteMan, BOOL wholeSent)
{
    struct PokemonSpriteStreamState *state = monSpriteMan->stream;
    u32 top, bottom, left, right, row;
    OSIntrMode intrMode;

    if (state == NULL) {
        return;
    }

    intrMode = OS_DisableInterrupts();
    top = state->dirtyTop;
    bottom = state->dirtyBottom;
    left = state->dirtyLeft;
    right = state->dirtyRight;
    state->dirtyTop = 0;
    state->dirtyBottom = 0;
    OS_RestoreInterrupts(intrMode);

    if (wholeSent || top >= bottom) {
        return;
    }

    GX_BeginLoadTex();

    for (row = top; row < bottom; row++) {
        GX_LoadTex(monSpriteMan->charRawData + row * CHAR_ROW_BYTES + left, monSpriteMan->charBaseAddr + row * CHAR_ROW_BYTES + left, right - left);
    }

    GX_EndLoadTex();
    sMonSpriteStreamStats.uploads++;
}
