#ifndef POKEPLATINUM_BATTLE_BATTLE_STAGE_STREAM_H
#define POKEPLATINUM_BATTLE_BATTLE_STAGE_STREAM_H

#include <nitro.h>

#include "pokemon_sprite.h"

// Gen 5 animated battle sprites, streamed one 128x96 frame at a time into a texture per
// battler (docs/living_battle_stage/sprite_stream.md). Internal to the battle stage:
// battle_stage_sprites.c drives it and draws its frames on the sprite mesh.

#define STREAM_CANVAS_WIDTH  128 // the stream frame, in pixels: a whole texture row
#define STREAM_CANVAS_HEIGHT 96
#define STREAM_CLASSIC_LEFT  24 // where the classic 80x80 frame sits in it
#define STREAM_CLASSIC_TOP   8

// Read by the critic (sSpriteStreamStats)
typedef struct BattleStageStreamStats {
    u32 vramAddr; // the four battler textures; 0 when streaming is off
    u32 loadedMask; // bit n while battler n has a stream loaded
    u32 drawnMask; // battlers drawn from their stream in the last frame
    u32 loads;
    u32 loadFailures; // no room on the heap
    u32 uploads; // frames sent to VRAM
    u32 bytesThisFrame; // queued for the next VBlank
    u32 maxBytesPerFrame;
    u32 decodeTicksThisFrame; // OS ticks (64 cycles of the 33.5 MHz bus) to decompress and copy
    u32 maxDecodeTicks;
    u32 loadTicksMax; // the longest stream load, card read included
    u32 streamBytes; // heap the loaded streams hold
    u32 heapFree; // HEAP_ID_BATTLE free after the last load
    u16 frame[MAX_MON_SPRITES]; // frame on screen per battler
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

#endif // POKEPLATINUM_BATTLE_BATTLE_STAGE_STREAM_H
