#ifndef POKEPLATINUM_BATTLE_BATTLE_STAGE_CAMERA_H
#define POKEPLATINUM_BATTLE_BATTLE_STAGE_CAMERA_H

#include <nitro.h>

#include "constants/battle.h"

#include "struct_decls/battle_system.h"

// The stage camera and its cinematics (docs/living_battle_stage/camera.md). Internal to the
// battle stage: battle_stage.c drives it; the public entry points (commands, guard and
// cinematics) are in battle/battle_stage.h.

// camFlags
enum BattleStageCameraFlag {
    BATTLE_STAGE_CAMERA_AT_HOME = 1 << 0,
    BATTLE_STAGE_CAMERA_EASING = 1 << 1,
    BATTLE_STAGE_CAMERA_SHAKING = 1 << 2,
    BATTLE_STAGE_CAMERA_SCRIPT = 1 << 3, // the running script used a camera command
};

// The fields of BattleStage at +52, in order
typedef struct BattleStageCameraFields {
    u32 camFlags;
    u32 cinematicsSeen; // enum BattleStageCinematic bits
    u32 guardSnaps; // times the guard snapped home at a script start
    u32 offHomeMoveFrames; // drawn frames off home in a script that used no camera command
    u32 offHomeFrames; // drawn frames off home
    s16 anchor[MAX_BATTLERS][2]; // current screen foot anchor (x, y) of each battler
    u16 anchorScale[MAX_BATTLERS]; // its scale, in 1/256
} BattleStageCameraFields;

// The arena's home camera. view and projection are the arena's own, used as they are at home.
typedef struct BattleStageCameraHome {
    VecFx32 camPos;
    VecFx32 camTarget;
    fx32 fovySin;
    fx32 fovyCos;
    fx32 nearClip;
    fx32 farClip;
    const MtxFx43 *view;
    const MtxFx44 *projection;
} BattleStageCameraHome;

// The screen-space similarity of a battler: p' = now + scale * (p - home), in pixels
typedef struct BattleStageCameraSimilarity {
    int homeX;
    int homeY;
    fx32 nowX;
    fx32 nowY;
    fx32 scale;
} BattleStageCameraSimilarity;

// The arena's projection for a fovy (battle_stage.c), with the depth squeezed into the arena's range
void BattleStage_BuildProjection(fx32 fovySin, fx32 fovyCos, fx32 nearClip, fx32 farClip, MtxFx44 *projection);

// At BattleStage_Init, after the sprites (home NULL when there is no arena). debugFlags is
// the stage's debugFlags field.
void BattleStageCamera_Init(BattleSystem *battleSys, BattleStageCameraFields *fields, const BattleStageCameraHome *home, const u32 *debugFlags);
// Snaps home and unhooks the particles
void BattleStageCamera_Free(void);
// Once per BattleStage_Draw while the arena exists, before anything is drawn
void BattleStageCamera_Advance(BOOL visible, int debugView);
// AT_HOME after the last Advance: draw with the arena's own view and projection
BOOL BattleStageCamera_IsHome(void);
// The view and projection to draw with while not home
const MtxFx43 *BattleStageCamera_View(void);
const MtxFx44 *BattleStageCamera_Projection(void);
// FALSE at home (the sprite is left alone) or when the battler has no anchor
BOOL BattleStageCamera_GetSimilarity(int battler, BattleStageCameraSimilarity *similarity);
// From BattleStage_SetMoveAnimActive: TRUE to FALSE ends the script
void BattleStageCamera_SetScriptActive(BOOL active);

#endif // POKEPLATINUM_BATTLE_BATTLE_STAGE_CAMERA_H
