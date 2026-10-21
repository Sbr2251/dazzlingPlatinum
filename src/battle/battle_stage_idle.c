#include "battle/battle_stage_idle.h"

#include <nitro.h>
#include <string.h>

#include "config/battle_stage.h"
#include "constants/battle.h"

#include "battle/battle_stage_sprites.h"
#include "battle/battle_stage_stream.h"
#include "battle/ov16_0223DF00.h"

#include "pokemon_anim.h"
#include "pokemon_sprite.h"

// bw2vis:idle. Gen 5 motion (docs/living_battle_stage/sprites.md, "Gen 5 motion"). The B/W
// behaviour is read from the pokebw2 decomp (src/ov168/btlv_mcss.c, btlv_effect.c).

BattleStageGen5MotionStats sGen5MotionStats;

void BattleStage_Gen5MotionInit(void)
{
    memset(&sGen5MotionStats, 0, sizeof(sGen5MotionStats));
}

BOOL BattleStage_UsesGen5Motion(int battler)
{
    if (!BATTLE_STAGE_3D || battler < 0 || battler >= MAX_MON_SPRITES) {
        return FALSE;
    }

    if (BattleStageSprites_DebugFlags() & (BATTLE_STAGE_DEBUG_CLASSIC_SPRITES | BATTLE_STAGE_DEBUG_NO_SPRITE_STREAM)) {
        return FALSE;
    }

    return BattleStageSprites_StreamsLive() && BattleStageStream_HasStream(battler);
}

// The battler of a battle sprite: the battle creates each battler's at its own index
// (ov16_02263B30, PokemonSpriteManager_CreateSpriteAtIndex)
static int SpriteBattler(PokemonSprite *sprite)
{
    BattleSystem *battleSys = BattleStageSprites_BattleSystem();
    PokemonSpriteManager *monSpriteMan;

    if (battleSys == NULL || sprite == NULL) {
        return -1;
    }

    monSpriteMan = BattleSystem_GetPokemonSpriteManager(battleSys);

    if (sprite < &monSpriteMan->sprites[0] || sprite >= &monSpriteMan->sprites[MAX_MON_SPRITES]) {
        return -1;
    }

    return sprite - &monSpriteMan->sprites[0];
}

void BattleStage_InitEntryAnim(PokemonSprite *sprite, int dummy)
{
    if (BattleStage_UsesGen5Motion(SpriteBattler(sprite))) {
        // No frame swaps, so no x offset either: the stream is the animation
        PokemonSprite_SetAttribute(sprite, MON_SPRITE_X_OFFSET, 0);
        return;
    }

    PokemonSprite_InitAnim(sprite, dummy);
}

void BattleStage_LoadEntryAnim(NARC *narc, PokemonAnimManager *monAnimMan, PokemonSprite *sprite, u16 species, int face, int flipSprite, int frame)
{
    PokemonSprite_LoadAnim(narc, monAnimMan, sprite, species, face, flipSprite, frame);

    if (BattleStage_UsesGen5Motion(SpriteBattler(sprite))) {
        // The script's task hasn't run a command yet: deleting it leaves the sprite as it is
        // and marks the slot complete
        PokemonAnimManager_DeleteAnim(monAnimMan, frame);
        sGen5MotionStats.entryAnimsSkipped++;
    } else {
        sGen5MotionStats.entryAnimsPlayed++;
    }
}
