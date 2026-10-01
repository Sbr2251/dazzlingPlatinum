#ifndef POKEPLATINUM_POKEMON_SPRITE_STREAM_H
#define POKEPLATINUM_POKEMON_SPRITE_STREAM_H

#include <nitro.h>

#include "constants/graphics.h"

#include "pokemon_sprite.h"

// Gen 5 animated sprites for PokemonSpriteManager (docs/living_battle_stage/sprite_stream.md).
// A screen opts sprites in; each drawn frame, the frame of the Gen 5 animation is cut to the
// classic 80x80 window and written over the sprite's frame in the manager's char data, and
// the rows that changed go to VRAM at the next PokemonSpriteManager_UpdateCharAndPltt. Any
// failure (no stream, no heap, flipped vertically, mosaic) draws the classic sprite.
//
// The battle stage streams battlers on its own mesh (battle_stage_stream.c); a manager it
// draws from must not opt in.

#define MON_STREAM_CANVAS_WIDTH  128 // the stream frame, in pixels
#define MON_STREAM_CANVAS_HEIGHT 96
#define MON_STREAM_CLASSIC_LEFT  24 // where the classic 80x80 frame sits in it
#define MON_STREAM_CLASSIC_TOP   8
#define MON_STREAM_ANCHOR_U      64 // the canvas column on the classic frame's centre line
#define MON_STREAM_GROUND_V      88 // the canvas row under the feet (the animation stands on row 87)
#define MON_STREAM_SCALE_ONE     8 // member scales are in eighths
#define MON_STREAM_MAX_SCALE     16

// Where a member's feet stand in the classic 80x80 frame: its bottom edge, also for a member
// drawn larger (a back sprite), which grows up and to the sides from there
#define MON_STREAM_FEET_Y        MON_SPRITE_FRAME_HEIGHT

#define MON_STREAM_INDEX_VERSION 2

// Member 0 of mon_stream.narc, version 2 (tools/gen5_sprites/gen5_stream.py)
typedef struct MonStreamIndexHeader {
    u16 version; // 0 reads as the step 1 index, u16 [species][back, front]
    u16 numPokegra;
    u16 numOtherpoke;
    u16 reserved;
    // u16 pokegra[numPokegra]: member for each PL_POKEGRA file (template character)
    // u16 otherpoke[numOtherpoke]: member for each PL_OTHERPOKE file
} MonStreamIndexHeader;

// A stream member
typedef struct MonStreamHeader {
    u8 numFrames;
    u8 scale; // drawn at scale/8 the size, about the feet (back sprites at 1.75x); 0 is 1:1
    u16 numSteps;
    u8 left; // the animation's box in the canvas: bytes (2 pixels)
    u8 width; // bytes
    u8 top;
    u8 height;
    u32 frameOffsets[]; // from the member's start, to LZ77 frames of height rows of width bytes
    // then {u8 frame, u8 duration} steps, duration in 1/60 s, looping
} MonStreamHeader;

// Read by probes (sMonSpriteStreamStats)
typedef struct MonSpriteStreamStats {
    u32 streamMask; // the opted-in sprites of the last manager that drew
    u32 loadedMask; // sprites with a stream loaded
    u32 drawnMask; // sprites whose frame came from their stream in the last drawn frame
    u32 loads;
    u32 loadFailures; // not enough heap, or a bad member
    u32 frames; // stream frames written
    u32 uploads; // partial VRAM uploads
    u32 bytesThisFrame; // queued for the next upload
    u32 maxBytesPerFrame;
    u32 decodeTicksMax; // OS ticks to decompress and copy one frame
    u32 loadTicksMax; // the longest stream load, card read included
    u32 heapFree; // the manager's heap after the last load
    u16 frame[MAX_MON_SPRITES]; // stream frame per sprite, 0xFFFF if none
    u32 pagedMask; // loaded sprites that read each frame from the card (the whole member didn't fit)
    u32 cardReads; // frames read from the card
    u32 readTicksMax; // the longest frame read
    u32 badFrames; // frames that failed to read or decode (the sprite went back to classic)
} MonSpriteStreamStats;

// The format, shared with battle_stage_stream.c, which keeps the index in RAM and reads its
// frames in the background.
//
// The u16 entries of member 0 that may hold a template's member, in order: the first that
// isn't 0 is it. Returns how many (0 to 2). A female PL_POKEGRA file with no stream takes the
// male file's (odd characters are male: species * 6 + face + male). Spinda's spots are drawn
// into the classic frame only, so it has none. version 0 reads as the step 1 index.
int MonStream_IndexEntries(const MonStreamIndexHeader *index, const PokemonSpriteTemplate *template, u32 entries[2]);
// The member's scale in eighths, MON_STREAM_SCALE_ONE to MON_STREAM_MAX_SCALE
static inline int MonStream_Scale(const MonStreamHeader *data)
{
    return data->scale != 0 ? data->scale : MON_STREAM_SCALE_ONE;
}

// The canvas texel drawn at pixel (x, y) of the classic 80x80 frame (scale in eighths). At 1:1
// the classic frame is the canvas at (24, 8)
#define MON_STREAM_TEXEL_U(x, scale) ((((x) - MON_SPRITE_FRAME_WIDTH / 2) * MON_STREAM_SCALE_ONE + MON_STREAM_ANCHOR_U * (scale)) / (scale))
#define MON_STREAM_TEXEL_V(y, scale) ((((y) - MON_STREAM_FEET_Y) * MON_STREAM_SCALE_ONE + MON_STREAM_GROUND_V * (scale)) / (scale))
// Where canvas column u and row v start in the classic frame, in eighths of a pixel: the first
// frame pixel showing texel u is the one at or right of it
#define MON_STREAM_FRAME_X8(u, scale) (MON_SPRITE_FRAME_WIDTH / 2 * MON_STREAM_SCALE_ONE + ((u) - MON_STREAM_ANCHOR_U) * (scale))
#define MON_STREAM_FRAME_Y8(v, scale) (MON_STREAM_FEET_Y * MON_STREAM_SCALE_ONE + ((v) - MON_STREAM_GROUND_V) * (scale))

// The header, frame offsets and steps
u32 MonStream_HeaderSize(const MonStreamHeader *data);
// A member the runtimes can play without reading past it: the box inside the canvas, frames in
// order on 4-byte boundaries and at least 4 bytes, steps on real frames (data: its HeaderSize)
BOOL MonStream_IsValid(const MonStreamHeader *data, u32 memberSize);
// Where a frame ends in its member (a valid one): the next frame's start, the last at the end
u32 MonStream_FrameEnd(const MonStreamHeader *data, u32 memberSize, u16 frame);
// The LZ77 header of a packed frame: MI_UncompressLZ8 writes exactly the box, no more
BOOL MonStream_IsFrameValid(const MonStreamHeader *data, const u8 *packed);
// Stream reads must not go by DMA. The card DMA is an auto DMA: an HBlank DMA started while
// it runs (the battle's wavy scrolls, Extrasensory's for one, restart theirs every VBlank), or
// a card DMA started while an HBlank DMA runs, stops the game (MIi_CheckAnotherAutoDMA).
// CARDi_TryReadCardDma uses DMA only for whole 512-byte pages into a destination on a 32-byte
// boundary; anything else the card thread copies with the CPU.
// FS_ReadFile that never takes the DMA path; TRUE when all size bytes came in
BOOL MonStream_ReadFile(FSFile *file, void *dst, u32 size);
// Background reads (FS_ReadFileAsync) go to this offset from a 32-byte boundary instead
#define MON_STREAM_READ_MISALIGN 4

// The stream member for a sprite template, 0 when it has none (MonStream_IndexEntries)
u16 MonStream_FindMember(const PokemonSpriteTemplate *template);

// Opts sprites in (bit n for sprites[n]); 0 turns streaming off, gives every sprite its
// classic frames back and frees all the streams hold. The first opt-in allocates on the
// manager's heap.
void PokemonSpriteManager_SetStreamMask(PokemonSpriteManager *monSpriteMan, u32 mask);
// Heap a stream load must leave free (default MON_STREAM_DEFAULT_HEAP_SPARE). A small stream
// (24 KB at most) is held whole when that leaves twice the spare; otherwise only its header is,
// and each frame is read from the card when it is drawn (2 KB at most, about 1 ms).
void PokemonSpriteManager_SetStreamHeapSpare(PokemonSpriteManager *monSpriteMan, u32 bytes);
// Frozen sprites hold the first step of their animation, the classic frame A
void PokemonSpriteManager_SetStreamFrozenMask(PokemonSpriteManager *monSpriteMan, u32 mask);

#define MON_STREAM_DEFAULT_HEAP_SPARE 0x8000
#define MON_STREAM_ALL_SPRITES        ((1 << MAX_MON_SPRITES) - 1)

// Called by pokemon_sprite.c
void PokemonSpriteStream_Free(PokemonSpriteManager *monSpriteMan);
void PokemonSpriteStream_BeginFrame(PokemonSpriteManager *monSpriteMan);
// Right before sprite index's quad: brings its stream up to date and writes a changed frame
// over the frame slot it draws (u0, v0: the slot's top-left texel)
void PokemonSpriteStream_UpdateSprite(PokemonSpriteManager *monSpriteMan, int index, int u0, int v0);
// The sprite's classic char data was just reloaded over the stream's frame
void PokemonSpriteStream_Invalidate(PokemonSpriteManager *monSpriteMan, int index);
// From PokemonSpriteManager_UpdateCharAndPltt (VBlank): sends the rows written since the last
// call, unless the whole char data is being sent anyway
void PokemonSpriteStream_Upload(PokemonSpriteManager *monSpriteMan, BOOL wholeSent);

#endif // POKEPLATINUM_POKEMON_SPRITE_STREAM_H
