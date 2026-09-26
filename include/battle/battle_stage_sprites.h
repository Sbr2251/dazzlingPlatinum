#ifndef POKEPLATINUM_BATTLE_BATTLE_STAGE_SPRITES_H
#define POKEPLATINUM_BATTLE_BATTLE_STAGE_SPRITES_H

#include <nitro.h>

#include "struct_decls/battle_system.h"

#include "battle/battle_stage_format.h"

// Lit, deformable battle sprites and blob shadows (docs/living_battle_stage/sprites.md).
// Internal to the battle stage: battle_stage.c drives these; the public entry points
// (BattleStage_SetMoveAnimActive, BattleStage_NotifyHit) are in battle/battle_stage.h.

// BattleStage debugFlags, written by the critic
enum BattleStageDebugFlag {
    BATTLE_STAGE_DEBUG_FREEZE_IDLE = 1 << 0, // no breathing and no wobble
    BATTLE_STAGE_DEBUG_NO_BLOB_SHADOWS = 1 << 1, // blobs off, the classic shadow is back
    BATTLE_STAGE_DEBUG_CLASSIC_SPRITES = 1 << 2, // sprites (and shadows) take the old path
    BATTLE_STAGE_DEBUG_NO_CINEMATICS = 1 << 3, // no crit or faint kicks (camera.md)
    BATTLE_STAGE_DEBUG_CRIT_KICK_ON_HIT = 1 << 4, // every hit blink plays the crit kick
};

// The fields of BattleStage at +32, in order
typedef struct BattleStageSpriteFields {
    u32 debugFlags;
    u32 spriteMeshes; // mons drawn as a mesh in the last drawn frame
    u32 idleFrames; // drawn frames in which breathing advanced for at least one mon
    u32 wobbleMask; // bit n while battler n wobbles
    u32 blobShadows; // blob shadows drawn in the last frame
} BattleStageSpriteFields;

// The home camera of the arena, for placing the blobs on the ground
typedef struct BattleStageSpriteCamera {
    VecFx32 camPos;
    VecFx32 camTarget;
    fx32 fovySin;
    fx32 fovyCos;
} BattleStageSpriteCamera;

// At BattleStage_Init, after the arena loaded (camera NULL when there is no arena)
void BattleStageSprites_Init(BattleSystem *battleSys, BattleStageSpriteFields *fields, const BattleStageSpriteCamera *camera);
void BattleStageSprites_Free(void);
// First thing in BattleStage_Draw, every drawn frame. When visible, lighting is the arena's
// material and light 0 for the time of day, dayLighting the same at day (the sprites are
// lit relative to it) and view the arena's current view matrix.
void BattleStageSprites_BeginFrame(BOOL visible, const BattleStageFileLighting *lighting, const BattleStageFileLighting *dayLighting, const MtxFx43 *view);
// From DrawArena, with the arena's projection and view loaded (POSITION_VECTOR mode). The
// projection is loaded again before it returns.
void BattleStageSprites_DrawBlobs(const MtxFx44 *projection);
// Screen row of a side's feet at home (the blob row)
int BattleStageSprites_BlobRow(int side);
// Where the home camera sees screen column px of a side's blob row on the ground; FALSE
// when there is no ground mapping (no arena, or the row is above the horizon)
BOOL BattleStageSprites_GroundPoint(int side, int px, VecFx32 *point);

#endif // POKEPLATINUM_BATTLE_BATTLE_STAGE_SPRITES_H
