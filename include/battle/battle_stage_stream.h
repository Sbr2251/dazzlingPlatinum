#ifndef POKEPLATINUM_BATTLE_BATTLE_STAGE_STREAM_H
#define POKEPLATINUM_BATTLE_BATTLE_STAGE_STREAM_H

#include <nitro.h>

#include "pokemon_sprite.h"
#include "pokemon_sprite_stream.h"

// Gen 5 animated battle sprites, streamed one 128x96 frame at a time into a texture per
// battler (docs/living_battle_stage/sprite_stream.md). Internal to the battle stage:
// battle_stage_sprites.c drives it and draws its frames on the sprite mesh. The member format
// and its checks are pokemon_sprite_stream.h's.

#define STREAM_CANVAS_WIDTH  MON_STREAM_CANVAS_WIDTH // a whole texture row
#define STREAM_CANVAS_HEIGHT MON_STREAM_CANVAS_HEIGHT
#define STREAM_CLASSIC_LEFT  MON_STREAM_CLASSIC_LEFT
#define STREAM_CLASSIC_TOP   MON_STREAM_CLASSIC_TOP

// Read by the critic (sSpriteStreamStats)
typedef struct BattleStageStreamStats {
    u32 vramAddr; // the four battler textures; 0 when streaming is off
    u32 loadedMask; // bit n while battler n has a stream loaded
    u32 drawnMask; // battlers drawn from their stream in the last frame
    u32 loads;
    u32 loadFailures; // no room on the heap, or a bad member
    u32 uploads; // frames sent to VRAM
    u32 bytesThisFrame; // queued for the next VBlank
    u32 maxBytesPerFrame;
    u32 decodeTicksThisFrame; // OS ticks (64 cycles of the 33.5 MHz bus) to decompress and copy
    u32 maxDecodeTicks;
    u32 loadTicksMax; // the longest stream load: its tables only, the frames come in the background
    u32 streamBytes; // heap the streams hold, the index included; 0 again after the battle
    u32 heapFree; // HEAP_ID_BATTLE free after the last load
    u16 frame[MAX_MON_SPRITES]; // frame on screen per battler
    // Added in step 2, after frame[] so the fields above keep their offsets
    u32 drawnEver; // battlers drawn from their stream at least once this battle
    u32 cardReads; // background frame reads
    u32 cardBytes;
    u32 readFailures; // reads the card failed; the battler draws classic
    u32 stallFrames; // frames a step was held because its frame wasn't in from the card yet
    u32 readVBlanksMax; // the slowest frame read, in vblanks from asking to polling it done
    u32 heapFreeMin; // the least HEAP_ID_BATTLE left free after a load
    u32 indexVersion; // of mon_stream.narc's member 0: 1 or 2; 0 when there is no index
    u32 deferredUploads; // frames sent a frame late, the upload budget being spent
    u16 member[MAX_MON_SPRITES]; // the NARC member each battler streams, 0 for none
    u32 readTicksMax; // the longest frame read: the card thread copies it with the CPU
} BattleStageStreamStats;

void BattleStageStream_Init(PokemonSpriteManager *monSpriteMan);
void BattleStageStream_Free(void);
// Every drawn frame, before the sprites: loads streams for new species, advances the
// animations and queues changed frames. Frozen holds every stream on its first step (the
// classic frame A); not visible sends nothing and sends whole frames when visible again.
void BattleStageStream_BeginFrame(BOOL visible, BOOL frozen);
// From the draw hook: when battler index's current frame is in VRAM, binds its texture
// (the canvas from texel 0, 0) and returns TRUE. Unbind gives the manager's
// texture back.
BOOL BattleStageStream_Bind(int index);
void BattleStageStream_Unbind(void);
// Where a battler's canvas goes for a draw the manager meant for the classic 80x80 frame
// (rect), on the mapping of MON_STREAM_TEXEL_U/V: at 1:1 the whole 128x96 canvas about the
// frame's centre; a scaled member (a back sprite) only its box, at its scale, standing on the
// frame's bottom edge, or below it by up to 40 frame pixels when tall (the sink, so the head
// clears the opponent's healthbar). A partial draw (the faint slide, the send-out reveal) keeps its cuts
// inside the 80x80 window, and on the sides where the window reaches the frame's edge goes out
// to the canvas's (scaled: the box's) edge, so art wider or taller than the classic frame stays.
// For a battler Bind took. centreX and centreY in fx32, the rest in pixels and texels.
typedef struct BattleStageStreamRect {
    fx32 centreX;
    fx32 centreY;
    int x;
    int y;
    int width;
    int height;
    int u0;
    int v0;
    int u1;
    int v1;
} BattleStageStreamRect;

void BattleStageStream_CanvasRect(int index, const PokemonSpriteTransforms *transforms, const PokemonSpriteDrawRect *rect, BattleStageStreamRect *out);
// The battler's texture copy (128x96, 4bpp, 64 bytes a row, the battler's palette) of the frame
// last decoded, which is on screen or goes there at the next VBlank; NULL when the battler has
// no stream or no frame in yet
const u8 *BattleStageStream_GetFrame(int index);
// The scale the battler's stream is drawn at (MonStream_Scale, in eighths), 1:1 when it has none
int BattleStageStream_GetScale(int index);

#endif // POKEPLATINUM_BATTLE_BATTLE_STAGE_STREAM_H
