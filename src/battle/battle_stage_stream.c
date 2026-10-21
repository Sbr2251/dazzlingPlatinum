#include "battle/battle_stage_stream.h"

#include <nitro.h>
#include <nnsys.h>
#include <string.h>

#include "constants/graphics.h"
#include "constants/heap.h"
#include "constants/narc.h"

#include "battle/battle_stage_idle.h"
#include "battle/battle_stage_layout.h"

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

// A scaled member (a back) taller than BACK_ROOM frame pixels sinks by the rest, at most
// BattleStageLayout_BackMaxSink(), so its top clears the opponent's healthbar (OBJs, drawn
// over the 3D layer). BW2 stands the player's feet 64 rows below ours, 20 below the screen,
// and its text box is translucent, so small backs show through it (sprite_stream.md "Sink").
// Ours is opaque, so short backs keep the classic row and only tall ones go down, at most to
// BW2's foot row. Fronts stand on the ground. bw2vis:layout
#define BACK_ROOM 100
// bw2vis:layout - a back whose art ends in a flat cut along the ground row (a run of at least
// GROUND_CUT_RUN opaque texels: the Mega stills, Platinum-style art) sinks at least
// BattleStageLayout_CutBackSink(), so the cut is at the screen's bottom edge when the text box
// fades, as BW2's backs are cut by the screen. Feet are narrower than the run.
#define GROUND_CUT_UNKNOWN 0
#define GROUND_CUT_NO      1
#define GROUND_CUT_YES     2
#define GROUND_CUT_RUN     16

typedef struct BattlerStream {
    u16 narcID; // the sprite template looked up last
    u16 character;
    MonStreamHeader *data; // header, frame offsets and steps; NULL: the template has no stream
    u32 size; // heap this battler holds
    u32 romStart; // the member's first byte, from the start of the card
    u32 memberSize;
    const u8 *steps; // {frame, duration}: the table playing, the loop's or the special idle's
    u16 numSteps; // in steps
    u16 step;
    s16 left; // vblanks the step has left
    u16 rateLeft; // the part of a vblank (of STREAM_RATE_ONE) not counted yet at a slow rate
    u16 texFrame; // frame in the texture copy, STREAM_NO_FRAME before the first
    u8 groundCut; // bw2vis:layout - GROUND_CUT_*: the first frame's art is cut flat along the ground row
    u16 shown; // frame in VRAM, STREAM_NO_FRAME when it has to be sent whole
    u16 queued; // frame queued for the next VBlank, STREAM_NO_FRAME if none
    u16 bufFrame; // compressed frame waiting in the read buffer
    u16 reading; // frame the card is reading into it
    u32 readVBlank; // when the read was asked for
    u8 *texture; // STREAM_TEX_BYTES, what the VRAM block holds; zero outside the box
    void *bufAlloc;
    u8 *buf; // bufAlloc, MON_STREAM_READ_MISALIGN past a 32-byte boundary
    FSFile file; // the NARC, for this battler's background reads
    // bw2vis:idle: B/W's special idle (battle_stage_idle.c), played as a second step table
    const u8 *loopSteps; // the loop (B/W's sequence 0)
    u16 loopNumSteps;
    u16 idleLeft; // vblanks the special idle has left; 0 while the loop plays
    u8 approxIdle[2]; // the approximation's clip: the loop's first frame held, one step
} BattlerStream;

typedef struct StageStream {
    PokemonSpriteManager *monSpriteMan;
    NNSGfdTexKey texKey;
    u32 texAddr;
    BOOL hasVram;
    BOOL hasFiles;
    u32 lastVBlank;
    u8 firstBattler; // updated first this frame
    u16 rate[MAX_MON_SPRITES]; // BattleStageStream_SetRate
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
        sSpriteStreamStats.indexVersion = sStageStream.index->version;
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
        sStageStream.rate[i] = STREAM_RATE_ONE;
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
    stream->groundCut = GROUND_CUT_UNKNOWN;
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
    stream->steps = MonStream_Steps(stream->data);
    stream->numSteps = head.numSteps;
    stream->loopSteps = stream->steps;
    stream->loopNumSteps = head.numSteps;
    stream->idleLeft = 0;
    BattleStage_StreamSpecialIdleReset(index);
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
    stream->rateLeft = 0;

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

    for (i = 0; i < stream->numSteps; i++) {
        step = step + 1 < stream->numSteps ? step + 1 : 0;

        if (StepFrame(stream, step) != stream->texFrame) {
            return StepFrame(stream, step);
        }
    }

    return stream->texFrame;
}

// bw2vis:idle: back to the loop, from its first step (B/W restart sequence 0 from tick 0)
static void EndSpecialIdle(int index, BattlerStream *stream, BOOL aborted)
{
    stream->steps = stream->loopSteps;
    stream->numSteps = stream->loopNumSteps;
    stream->step = 0;
    stream->left = stream->steps[1];
    stream->idleLeft = 0;
    BattleStage_StreamSpecialIdleEnd(index, aborted);
}

// bw2vis:idle: at the end of a loop, B/W may play a special idle (btlv_mcss.c OnAnimationEnd):
// the member's idle clip (pokemon_sprite_stream.h, index version 3), or without one the
// approximation, the loop's first frame held. TRUE when it started; the step it shows may still
// be on its way from the card, as after a stall
static BOOL StartSpecialIdle(int index, BattlerStream *stream)
{
    const u8 *idleSteps = NULL;
    u16 numIdleSteps = 1;
    u32 wait;

    if (stream->loopNumSteps <= 1) {
        return FALSE; // a still (the Megas' backs)
    }

#ifdef MON_STREAM_IDLE_NONE
    // B/W play no special idle for the faces without idle nodes (most flyers)
    if (stream->data->idleKind == MON_STREAM_IDLE_NONE || stream->data->numIdleSteps == 0) {
        return FALSE;
    }

    idleSteps = MonStream_IdleSteps(stream->data);
    numIdleSteps = stream->data->numIdleSteps;
#endif

    if (!BattleStage_StreamSpecialIdleStart(index, idleSteps, &wait) || wait == 0) {
        return FALSE;
    }

    if (idleSteps == NULL) {
        stream->approxIdle[0] = stream->loopSteps[0];
        stream->approxIdle[1] = 0xFF;
        idleSteps = stream->approxIdle;
    }

    stream->steps = idleSteps;
    stream->numSteps = numIdleSteps;
    stream->step = 0;
    stream->left = idleSteps[1];
    stream->idleLeft = wait;
    return TRUE;
}

// Moves on by the vblanks gone, keeping the steps' time exact. The battle draws every second vblank and
// B2W2's steps can be one vblank long, so a step may come due before its frame is in: the frame on
// screen then stays a draw longer (counted in stallFrames) while the time goes on, and the read ahead
// (StepAfter) asks for the frame of the step the next draw lands on
static void Advance(int index, BattlerStream *stream, u32 elapsed, BOOL frozen, u32 rate)
{
    int next;

    if (frozen) {
        if (stream->idleLeft != 0) {
            EndSpecialIdle(index, stream, TRUE);
        }

        stream->step = 0;
        stream->left = stream->steps[1];
        return;
    }

    // bw2vis:idle: the special idle's wait counts every vblank, whatever the speed (B/W's
    // IdleTask counts frames), and a move animation ends it at once
    if (stream->idleLeft != 0) {
        if (BattleStage_StreamSpecialIdleAbort(index)) {
            EndSpecialIdle(index, stream, TRUE);
        } else if (stream->idleLeft <= elapsed) {
            EndSpecialIdle(index, stream, FALSE);
        } else {
            stream->idleLeft -= elapsed;
        }
    }

    // Below STREAM_RATE_ONE a vblank counts for less; at 0 the step holds
    if (rate == 0) {
        return;
    }

    elapsed = elapsed * rate + stream->rateLeft;
    stream->rateLeft = elapsed % STREAM_RATE_ONE;
    stream->left -= elapsed / STREAM_RATE_ONE;

    while (stream->left <= 0) {
        next = stream->step + 1 < stream->numSteps ? stream->step + 1 : 0;

        if (next == 0 && stream->idleLeft != 0) {
            // The idle clip covers the longest wait and doesn't loop: its last step holds
            stream->left = 0;
            break;
        }

        if (next == 0 && StartSpecialIdle(index, stream)) {
            continue;
        }

        stream->step = next;
        stream->left += stream->steps[next * 2 + 1];
    }

    if (!HasFrame(stream, StepFrame(stream, stream->step))) {
        sSpriteStreamStats.stallFrames++;
    }
}

// The step the battler is on after vblanks more vblanks at its rate
static int StepAfter(const BattlerStream *stream, u32 vblanks, u32 rate)
{
    int i, step = stream->step;
    s32 left = stream->left - (s32)((vblanks * rate + stream->rateLeft) / STREAM_RATE_ONE);

    for (i = 0; left <= 0 && i < stream->numSteps; i++) {
        if (step + 1 >= stream->numSteps && stream->idleLeft != 0) {
            break; // the idle clip's last step holds
        }

        step = step + 1 < stream->numSteps ? step + 1 : 0;
        left += stream->steps[step * 2 + 1];
    }

    return step;
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

    // bw2vis:layout - judged once per stream, on its first frame, so the sink holds still
    if (stream->groundCut == GROUND_CUT_UNKNOWN) {
        const u8 *ground = stream->texture + (MON_STREAM_GROUND_V - 1) * STREAM_ROW_BYTES;
        int u, run = 0, longest = 0;

        for (u = 0; u < STREAM_CANVAS_WIDTH; u++) {
            run = ((ground[u / 2] >> ((u & 1) * 4)) & 0xF) != 0 ? run + 1 : 0;
            longest = run > longest ? run : longest;
        }

        stream->groundCut = longest >= GROUND_CUT_RUN ? GROUND_CUT_YES : GROUND_CUT_NO;
    }

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
        Advance(index, stream, elapsed, frozen, sStageStream.rate[index]);
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

    // One draw ahead: the frame of the step the next draw lands on (as many vblanks on as this one
    // took), else the next one the steps change to. Before the first frame, frozen, and when the
    // step's own frame is in but waits for the decode budget: the step's own
    if (stream->texFrame == STREAM_NO_FRAME || frozen || (want != stream->texFrame && want == stream->bufFrame)) {
        next = want;
    } else {
        next = StepFrame(stream, StepAfter(stream, elapsed != 0 ? elapsed : 1, sStageStream.rate[index]));
        next = next != stream->texFrame ? next : NextFrame(stream);
    }

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

void BattleStageStream_SetRate(int index, u32 rate)
{
    if (index >= 0 && index < MAX_MON_SPRITES) {
        sStageStream.rate[index] = rate > STREAM_RATE_ONE ? STREAM_RATE_ONE : rate;
    }
}

// bw2vis:idle: battler index's sprite plays a stream, or will once its tables are read (its
// template changed this frame)
BOOL BattleStageStream_HasStream(int index)
{
    const PokemonSprite *sprite;
    const BattlerStream *stream;

    if (sStageStream.monSpriteMan == NULL || !sStageStream.hasVram || sStageStream.index == NULL || index < 0 || index >= MAX_MON_SPRITES) {
        return FALSE;
    }

    sprite = &sStageStream.monSpriteMan->sprites[index];
    stream = &sStageStream.battlers[index];

    if (!sprite->active) {
        return FALSE;
    }

    if (sprite->template.narcID == stream->narcID && sprite->template.character == stream->character) {
        return stream->data != NULL;
    }

    return FindMember(&sprite->template) != 0;
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

    return BattleStageLayout_StreamScale(MonStream_Scale(sStageStream.battlers[index].data)); // bw2vis:layout - backs at 2x
}

// How far a scaled member (a back) sinks below the frame's bottom edge, in frame pixels
static int BackSink(int index, int scale)
{
    const BattlerStream *stream = &sStageStream.battlers[index];
    int sink = (MON_STREAM_GROUND_V - stream->data->top) * scale / MON_STREAM_SCALE_ONE - BACK_ROOM;
    int dx, dy;

    sink = sink < 0 ? 0 : (sink > BattleStageLayout_BackMaxSink() ? BattleStageLayout_BackMaxSink() : sink);

    // bw2vis:layout
    if (stream->groundCut == GROUND_CUT_YES && sink < BattleStageLayout_CutBackSink()) {
        sink = BattleStageLayout_CutBackSink();
    }

    // bw2vis:layout - a battler already moved down by the layout (a doubles back at its BW2 row)
    // sinks only by what that leaves: the sink is a depth below the classic foot row
    if (BattleStageLayout_Offset(index, &dx, &dy) && dy > 0) {
        sink = sink > dy ? sink - dy : 0;
    }

    return sink;
}

int BattleStageStream_SinkPixels(int index, int frameHeight)
{
    const BattlerStream *stream;
    int scale;

    if (index < 0 || index >= MAX_MON_SPRITES || sStageStream.battlers[index].data == NULL) {
        return 0;
    }

    stream = &sStageStream.battlers[index];
    scale = BattleStageLayout_StreamScale(MonStream_Scale(stream->data));
    return scale == MON_STREAM_SCALE_ONE ? 0 : BackSink(index, scale) * frameHeight / MON_SPRITE_FRAME_HEIGHT;
}

void BattleStageStream_CanvasRect(int index, const PokemonSpriteTransforms *transforms, const PokemonSpriteDrawRect *rect, BattleStageStreamRect *out)
{
    const MonStreamHeader *data = sStageStream.battlers[index].data;
    int scale = BattleStageLayout_StreamScale(MonStream_Scale(data)); // bw2vis:layout - backs at 2x
    int boxU0, boxV0, boxU1, boxV1; // what a side reaching the frame's edge extends to
    int frameX, frameY, frameW, frameH; // the classic frame on screen; flipped when negative
    int x0, x1, y0, y1; // the quad in the frame, in eighths of a pixel
    int sink = 0; // frame pixels

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
        sink = BackSink(index, scale);
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

    if (sink != 0) {
        sink = sink * frameH / MON_SPRITE_FRAME_HEIGHT;
        out->y += sink;
        out->centreY += sink * FX32_ONE;
    }
}

const MonStreamHeader *BattleStageStream_GetHeader(int index)
{
    return sStageStream.battlers[index].data;
}
