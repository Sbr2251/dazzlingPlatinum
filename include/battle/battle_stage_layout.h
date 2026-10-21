#ifndef POKEPLATINUM_BATTLE_BATTLE_STAGE_LAYOUT_H
#define POKEPLATINUM_BATTLE_BATTLE_STAGE_LAYOUT_H

#include <nitro.h>

#include "struct_decls/battle_system.h"

#include "battle/battle_stage_camera.h"

// Black 2/White 2's battler placement on the 3D stage (docs/living_battle_stage/layout.md).
//
// At rest (the command menu, messages) each battler stands at its BW2 place: toward BW2's foot
// point on screen (pokebw2 btlv_mcss.c:184-195 projected through btlv_camera.c's camera) by a
// per-slot offset from its classic place, as far as Platinum's opaque text box and its
// healthbars allow (battle_stage_layout.c, sRestOffset). From an animation script until the text box shows again,
// everything goes back to the classic places, where Platinum's move animations aim their
// OBJs, BGs and particles. The change eases over a few frames, in step with the text box fade
// (battle_textbox.c). The platforms, the blobs, the camera anchors and the trainers follow.
//
// Off (every offset 0) with no arena, while the stage isn't visible, in Totem battles (their
// own layout) and with the CLASSIC_SPRITES or PLATINUM_LAYOUT debug flags.

void BattleStageLayout_Init(BattleSystem *battleSys, BOOL hasArena, const u32 *debugFlags);
void BattleStageLayout_Free(void);
// Once per BattleStage_Draw, before the camera
void BattleStageLayout_Advance(BOOL visible);
// The battler's current offset from its classic place, in screen pixels; FALSE when 0, 0
BOOL BattleStageLayout_Offset(int battler, int *dx, int *dy);
// A side's platform offset (the mean of its battlers'), in screen pixels; FALSE when 0, 0
BOOL BattleStageLayout_SideOffset(int side, int *dx, int *dy);
// The world shift of a side's platform meshes (FALSE when none)
BOOL BattleStageLayout_PlatformShift(int side, VecFx32 *shift);
// The sprite's screen-space similarity: the camera's (BattleStageCamera_GetSimilarity), with
// the battler's layout place under it. FALSE at home with no offset (the sprite is left alone)
BOOL BattleStageLayout_Similarity(int battler, BattleStageCameraSimilarity *similarity);
// The scale (in eighths) a stream stored at storedScale is drawn at in battle: backs (stored
// above 1:1, at the 1.75x baseline) at BW2's 2x (btlv_mcss.c:2203), the rest as stored
int BattleStageLayout_StreamScale(int storedScale);
// The most a tall back sinks below its classic foot row (frame pixels, battle_stage_stream.c)
int BattleStageLayout_BackMaxSink(void);
// The least a back whose art is cut flat along the ground row sinks (frame pixels), so the cut
// is off the screen's bottom when the text box fades (battle_stage_stream.c)
int BattleStageLayout_CutBackSink(void);
// From BattleStage_SetMoveAnimActive
void BattleStageLayout_SetScriptActive(BOOL active);

// The move-animation command (battle_display.c): before its first script the battlers ease
// to their classic places and, with hideTextbox, the text box fades out; Begin/End bracket the
// whole command
void BattleStage_BeginAnimSequence(BOOL hideTextbox);
void BattleStage_EndAnimSequence(void);
// Once per frame before the command's first script: TRUE once both are done, or after
// LAYOUT_ANIM_WAIT_MAX frames of waiting (then the animation plays with the box up, or from
// wherever the battlers are)
BOOL BattleStage_IsReadyForAnim(void);

// Read by the critic (sBattleStageLayout in the xMAP)
typedef struct BattleStageLayoutStats {
    s8 offset[4][2]; // per battler, this frame (px)
    u8 ease; // 0 (classic places) .. LAYOUT_EASE_STEPS (BW2 places)
    u8 on; // the layout applies this frame
    u8 sequences; // move-animation commands in progress
    u8 scriptActive;
    u32 animWaitFrames; // logic frames animations waited for the box and the places, in total
    u32 animWaitMax; // the longest single wait
} BattleStageLayoutStats;

#endif // POKEPLATINUM_BATTLE_BATTLE_STAGE_LAYOUT_H
