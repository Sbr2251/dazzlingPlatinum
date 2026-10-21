#ifndef POKEPLATINUM_BATTLE_BATTLE_STAGE_COPIES_H
#define POKEPLATINUM_BATTLE_BATTLE_STAGE_COPIES_H

#include <nitro.h>

#include "constants/heap.h"

#include "bg_window.h"
#include "pokemon_sprite.h"
#include "sprite_system.h"

// bw2vis:idle. A move's OAM copies of a streamed battler, drawn by the stage from the live
// stream at the mesh's scale (battle_stage_copies.c; sprite_stream.md, "Move copies")

#define BATTLE_STAGE_MAX_MON_COPIES 5 // BATTLE_ANIM_SCRIPT_MAX_POKEMON_SPRITES

// Read by the harness (sMonCopyStats), zeroed at each battle's BattleStage_Init
typedef struct BattleStageCopyStats {
    u32 adopted; // copies the stage took over
    u32 released; // ... handed back to 2D (an OBJ window effect)
    u32 drawnFrames; // copy draws
    u32 bg2Copies; // BG2 copies made at the mesh's scale (LoadPokemonSpriteIntoBg)
} BattleStageCopyStats;

extern BattleStageCopyStats sMonCopyStats;

// At BattleStage_Init
void BattleStageCopies_Init(void);
// AddPokemonSprite made sprite, the copy in slot of battler, its OBJ tiles at vramAddr and tiles
// its own 80x80 frame. TRUE when the stage draws it: the caller uploads BlankCopyTiles instead
BOOL BattleStage_AdoptMonCopy(int slot, ManagedSprite *sprite, int battler, const u8 *tiles, u32 vramAddr);
const u8 *BattleStage_BlankCopyTiles(void);
// The copy in slot is gone (RemovePokemonSprite); all copies are gone (the manager freed, the
// script ended)
void BattleStage_DropMonCopy(int slot);
void BattleStage_DropAllMonCopies(void);
// An effect uses the battler's copies as an OBJ window (Harden, Superpower, Camouflage, the 2D
// stat change): they go back to 2D, with their own tiles, so the window matches the copy shown
// (sprite is any of the battler's copies; nothing happens for a copy the stage doesn't draw)
void BattleStage_ReleaseMonCopiesOf(ManagedSprite *sprite);
// LoadPokemonSpriteIntoBg, after it loaded the classic copy and its tilemap: replaces them with
// the battler's live stream frame at the mesh's scale (its canvas, sink included), tile-aligned
// about the classic frame's place so the move's BG offsets still apply. FALSE (and the classic
// copy kept) when the battler isn't streamed or the copy wouldn't fit BG2's 511 tiles
BOOL BattleStage_BuildBg2Copy(int battler, BgConfig *bgConfig, u8 bgLayer, enum HeapID heapID);
// RemovePokemonSpriteFromBg: the bytes of tiles to clear (at least the classic copy's, as before),
// and TRUE when the copy was the stage's: then its larger tilemap goes too
BOOL BattleStage_TakeBg2Copy(u32 *clearBytes);
// After the battle's PokemonSpriteManager_DrawSprites, with its sprite camera
void BattleStage_DrawMonCopies(PokemonSpriteManager *monSpriteMan);

#endif // POKEPLATINUM_BATTLE_BATTLE_STAGE_COPIES_H
