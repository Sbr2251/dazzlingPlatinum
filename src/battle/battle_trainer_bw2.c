#include "battle/battle_trainer_bw2.h"

#include <nitro.h>

#include "constants/narc.h"
#include "generated/trainer_classes.h"

#include "narc.h"
#include "palette.h"
#include "sprite.h"
#include "sprite_system.h"

// BW2 animated trainer fronts (bw2vis:trainers-anim, docs/living_battle_stage/trainers.md).
//
// The art is built by tools/bw2_trainers/build_bw2_trainers.py from pokebw2's trainer MCSS into Platinum's
// own trainer front format (one 80x80 4bpp cell per frame, VRAM transfer of 3200 bytes, so the same OBJ
// VRAM as any trainer). It lives in a separate archive so only the battle shows it: the union room, the
// Wi-Fi club and the other screens that draw trainer fronts keep reading Platinum's trfgra.narc.
#include "battle_trainer_bw2_table.h"

#define BW2_FILES_PER_ENTRY 4
#define BW2_IDLE_ATTR       0x102

// Resource IDs, the template and the priorities are sub_02076994's (pokemon.c), so the battle's
// unload code (SpriteManager_Unload*ById(20015/20010/20007 + battlerType)) frees these too
static const SpriteTemplate sTrainerTemplate = {
    .x = 0,
    .y = 0,
    .z = 0,
    .animIdx = 0,
    .priority = 0,
    .plttIdx = 0,
    .vramType = NNS_G2D_VRAM_TYPE_2DMAIN,
    .resources = { 0x4E2F, 0x4E2A, 0x4E27, 0x4E27, 0xffffffff, 0xffffffff },
    .bgPriority = 2,
    .vramTransfer = TRUE,
};

static const int sTrainerPriority[] = { 0, 0, 1, 0, 0, 1 };

ManagedSprite *BattleTrainerBW2_NewFront(SpriteSystem *spriteSys, SpriteManager *spriteMan, PaletteData *palette, int x, int y, int trainerClass, int face, int battlerType, enum HeapID heapID)
{
    SpriteTemplate template;
    ManagedSprite *sprite;
    NARC *narc;
    int entry;

    if (BW2_TRAINER_FRONTS == 0 || face != 2 || trainerClass < 0 || trainerClass >= (int)NELEMS(sTrainerClassBW2Front)) {
        return NULL;
    }

    entry = sTrainerClassBW2Front[trainerClass];

    if (entry == 0) {
        return NULL;
    }

    entry = (entry - 1) * BW2_FILES_PER_ENTRY;
    narc = NARC_ctor(NARC_INDEX_POKETOOL__TRGRA__TRFGRA_BW2, heapID);

    SpriteSystem_LoadCharResObjFromOpenNarc(spriteSys, spriteMan, narc, entry + 0, FALSE, NNS_G2D_VRAM_TYPE_2DMAIN, 20015 + battlerType);
    SpriteSystem_LoadPaletteBufferFromOpenNarc(palette, PLTTBUF_MAIN_OBJ, spriteSys, spriteMan, narc, entry + 1, FALSE, 1, NNS_G2D_VRAM_TYPE_2DMAIN, 20010 + battlerType);
    SpriteSystem_LoadCellResObjFromOpenNarc(spriteSys, spriteMan, narc, entry + 2, FALSE, 20007 + battlerType);
    SpriteSystem_LoadAnimResObjFromOpenNarc(spriteSys, spriteMan, narc, entry + 3, FALSE, 20007 + battlerType);
    NARC_dtor(narc);

    template = sTrainerTemplate;
    template.resources[0] = 20015 + battlerType;
    template.resources[1] = 20010 + battlerType;
    template.resources[2] = 20007 + battlerType;
    template.resources[3] = 20007 + battlerType;
    template.priority = sTrainerPriority[battlerType];

    sprite = SpriteSystem_NewSprite(spriteSys, spriteMan, &template);

    Sprite_SetExplicitPaletteOffsetAutoAdjust(sprite->sprite, 0);
    ManagedSprite_SetPositionXY(sprite, x, y);
    ManagedSprite_TickFrame(sprite);
    ManagedSprite_SetAnimateFlag(sprite, 1);

    return sprite;
}

void BattleTrainerBW2_StartIdle(ManagedSprite *sprite)
{
    if (sprite == NULL || ManagedSprite_GetNumFrames(sprite) < 2) {
        return;
    }

    if (Sprite_GetUserAttrForAnimFrame(sprite->sprite, 1, 0) == BW2_IDLE_ATTR) {
        ManagedSprite_SetAnimationFrame(sprite, 0);
        ManagedSprite_SetAnim(sprite, 1);
        ManagedSprite_SetAnimateFlag(sprite, 1);
    }
}
