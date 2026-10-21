#ifndef POKEPLATINUM_BATTLE_BATTLE_STAGE_IDLE_H
#define POKEPLATINUM_BATTLE_BATTLE_STAGE_IDLE_H

#include <nitro.h>

#include "struct_decls/battle_system.h"

#include "narc.h"
#include "pokemon_anim.h"
#include "pokemon_sprite.h"

// Gen 5 motion for the battle sprites (bw2vis:idle; docs/living_battle_stage/sprites.md,
// "Gen 5 motion"): what replaces Platinum's own motion on a battler the stage draws from its
// Gen 5 stream, and B/W's special idle. Every entry point degrades to Platinum's behaviour on
// the classic path (stage off, CLASSIC_SPRITES, NO_SPRITE_STREAM, a species without a stream).

// The battler's sprite plays its Gen 5 stream: the stage is on and streaming, the debug flags
// allow it, and the sprite's template has a stream
BOOL BattleStage_UsesGen5Motion(int battler);

// Platinum's per-species entry animation, at send-out and wild appear: the frame swaps
// (PokemonSprite_InitAnim) and the PokemonAnim script (PokemonSprite_LoadAnim: hops, squash,
// palette fades). Same arguments as the calls they replace. For a battler that uses Gen 5
// motion neither plays: B/W show only the stream's own loop. The anim slot is still set up and
// at once marked complete, so the tasks that wait for it go on.
void BattleStage_InitEntryAnim(PokemonSprite *sprite, int dummy);
void BattleStage_LoadEntryAnim(NARC *narc, PokemonAnimManager *monAnimMan, PokemonSprite *sprite, u16 species, int face, int flipSprite, int frame);

// The classic command-menu bob (ov16_02264798.c) leaves a battler alone while the stage draws
// it as a mesh or from its stream: B/W bob only the HP gauge
BOOL BattleStage_SuppressMenuBob(int battler);

// Read by the harness (sGen5MotionStats), zeroed at each battle's BattleStage_Init
typedef struct BattleStageGen5MotionStats {
    u32 entryAnimsSkipped; // per-species entry animations not played (Gen 5 motion)
    u32 entryAnimsPlayed; // ... played (classic)
    u32 bobSuppressedFrames; // frames the menu bob left a battler alone
    u32 hitFlashes; // hit flashes started
    u32 hitFlashColor; // the colour of the last one
    u32 idleRolls; // loop ends that rolled for a special idle
    u32 idleStarts[4]; // special idles started, per battler
    u32 idleAborts; // ... cut short by a move anim
    u32 idleActiveMask; // battlers in a special idle now
    u32 idleApproxStarts; // idles that used the approximation (no idle clip)
    u32 lastIdleWait; // vblanks
    u8 idleCount[4]; // B/W's: the chance of the next roll is 1 in this
    u32 faints; // BW2-like faints started
} BattleStageGen5MotionStats;

extern BattleStageGen5MotionStats sGen5MotionStats;

void BattleStage_Gen5MotionInit(void);

#endif // POKEPLATINUM_BATTLE_BATTLE_STAGE_IDLE_H
