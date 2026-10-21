#ifndef POKEPLATINUM_BATTLE_TRAINER_BW2_H
#define POKEPLATINUM_BATTLE_TRAINER_BW2_H

#include "constants/heap.h"

#include "palette.h"
#include "sprite_system.h"

// The revert switch for the BW2 animated trainer fronts (bw2vis:trainers-anim). 1: the classes in
// tools/bw2_trainers/mapping.py battle with BW2's animated art from poketool/trgra/trfgra_bw2.narc.
// 0: every class shows its Platinum art again (the archive stays in the ROM, unused).
#define BW2_TRAINER_FRONTS 1

// The battle's trainer front (opponent side) for classes with a BW2 front; NULL for every other class
// and for back sprites, so the caller falls back to sub_02076994. Same resources, IDs and placement.
ManagedSprite *BattleTrainerBW2_NewFront(SpriteSystem *spriteSys, SpriteManager *spriteMan, PaletteData *palette, int x, int y, int trainerClass, int face, int battlerType, enum HeapID heapID);

// Start the idle loop of a BW2 front (sequence 1 marked as a loop); does nothing for Platinum art, whose
// sequence 1 is a one-shot gesture.
void BattleTrainerBW2_StartIdle(ManagedSprite *sprite);

#endif // POKEPLATINUM_BATTLE_TRAINER_BW2_H
