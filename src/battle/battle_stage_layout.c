#include "battle/battle_stage_layout.h"

#include <nitro.h>

#include "battle/battle_textbox.h"

// The longest a move-animation command waits for the text box (logic frames)
#define LAYOUT_ANIM_WAIT_MAX 90

static int sWaitFrames; // of the move-animation command waiting now
BattleStageLayoutStats sBattleStageLayout;

void BattleStage_BeginAnimSequence(BOOL hideTextbox)
{
    if (sBattleStageLayout.sequences < 0xFF) {
        sBattleStageLayout.sequences++;
    }

    sWaitFrames = 0;

    if (hideTextbox) {
        BattleTextbox_RequestHide();
    }
}

void BattleStage_EndAnimSequence(void)
{
    if (sBattleStageLayout.sequences > 0) {
        sBattleStageLayout.sequences--;
    }
}

BOOL BattleStage_IsReadyForAnim(void)
{
    BOOL ready = BattleTextbox_IsReadyForAnim(sWaitFrames);

    if (!ready && sWaitFrames < LAYOUT_ANIM_WAIT_MAX) {
        sWaitFrames++;
        sBattleStageLayout.animWaitFrames++;
        return FALSE;
    }

    if ((u32)sWaitFrames > sBattleStageLayout.animWaitMax) {
        sBattleStageLayout.animWaitMax = sWaitFrames;
    }

    sWaitFrames = 0;
    return TRUE;
}
