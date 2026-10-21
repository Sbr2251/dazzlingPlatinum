#ifndef POKEPLATINUM_BATTLE_BATTLE_STAGE_LAYOUT_H
#define POKEPLATINUM_BATTLE_BATTLE_STAGE_LAYOUT_H

#include <nitro.h>

// The move-animation command (battle_display.c): before its first script, with hideTextbox,
// the text box fades out (battle_textbox.c); Begin/End bracket the whole command
void BattleStage_BeginAnimSequence(BOOL hideTextbox);
void BattleStage_EndAnimSequence(void);
// Once per frame before the command's first script: TRUE once the box is out, or after
// LAYOUT_ANIM_WAIT_MAX frames of waiting (then the animation plays with the box up)
BOOL BattleStage_IsReadyForAnim(void);

// Read by the critic (sBattleStageLayout in the xMAP)
typedef struct BattleStageLayoutStats {
    s8 offset[4][2]; // reserved for the battler placement
    u8 ease;
    u8 on;
    u8 sequences; // move-animation commands in progress
    u8 scriptActive;
    u32 animWaitFrames; // logic frames animations waited for the box, in total
    u32 animWaitMax; // the longest single wait
} BattleStageLayoutStats;

#endif // POKEPLATINUM_BATTLE_BATTLE_STAGE_LAYOUT_H
