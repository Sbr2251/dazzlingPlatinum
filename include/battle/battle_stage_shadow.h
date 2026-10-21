#ifndef POKEPLATINUM_BATTLE_BATTLE_STAGE_SHADOW_H
#define POKEPLATINUM_BATTLE_BATTLE_STAGE_SHADOW_H

#include <nitro.h>

#include "struct_decls/battle_system.h"

// BW2-style battler shadows (docs/living_battle_stage/shadows.md): each streamed battler's
// current frame drawn again, black at half its alpha, laid back onto the ground behind it as
// BW2's MCSS shadow pass does. Internal to the battle stage: battle_stage_sprites.c calls these
// around its blob shadows, which stay the fallback for battlers with no stream.

// Read by the critic and the harness (sStageShadowStats)
typedef struct BattleStageShadowStats {
    u32 silhouetteMask; // battlers drawn with a silhouette shadow in the last drawn frame
    u32 offMask; // battlers whose shadow is off (the adjust table) in the last drawn frame
    u32 silhouettes; // silhouette shadows drawn in the last drawn frame
    u32 drawnFrames; // frames that drew at least one silhouette, this battle
    u32 plttAddr; // the shadow palette in texture palette VRAM; 0 without one
} BattleStageShadowStats;

// From BattleStageSprites_Init (with an arena) and BattleStageSprites_Free
void BattleStageShadow_Init(BattleSystem *battleSys);
void BattleStageShadow_Free(void);
// From BattleStageSprites_DrawBlobs while the stage shadows are on, with the arena's view and
// projection loaded (POSITION_VECTOR mode): draws the silhouette shadows of the battlers in
// shownMask (those a blob would show for) and returns the battlers that get no blob (a silhouette
// drawn, or the shadow off). The projection is loaded again before it returns. debugFlags are the
// stage's; counter (the blobShadows field) is raised once per silhouette.
u32 BattleStageShadow_Draw(const MtxFx44 *projection, u32 shownMask, u32 debugFlags, u32 *counter);

#endif // POKEPLATINUM_BATTLE_BATTLE_STAGE_SHADOW_H
