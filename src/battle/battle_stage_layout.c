#include "battle/battle_stage_layout.h"

#include <nitro.h>
#include <string.h>

#include "constants/battle.h"

#include "battle/battle_stage.h"
#include "battle/battle_stage_camera.h"
#include "battle/battle_stage_sprites.h"
#include "battle/battle_textbox.h"
#include "battle/ov16_0223DF00.h"

#include "pokemon_sprite_stream.h"
#include "totem_battle.h"

// The ease between the classic and the BW2 places, in drawn frames (30 Hz): 5 steps, 10
// screen frames, about the text box's 6-frame fade plus a little
#define LAYOUT_EASE_STEPS 5
// Drawn frames with no script before the battlers go back to their BW2 places (the
// move-animation command runs several scripts back to back for a Substitute)
#define LAYOUT_REST_DELAY 2
// The longest a move-animation command waits for the box and the places (logic frames)
#define LAYOUT_ANIM_WAIT_MAX 90

// Backs: stored at the 1.75x baseline (14 eighths), drawn at BW2's 2x (btlv_mcss.c:2203,
// BtlvMcss_GetDefaultScaleImpl: 32 for the back, 16 for the front, flat)
#define STREAM_BACK_BASELINE 14
#define STREAM_BACK_DRAWN    16
// The most a tall back sinks below the classic foot row, in frame pixels: down to BW2's foot
// row (212, 64 below the classic 148); 40 at the 1.75x baseline
#define BACK_MAX_SINK_BW2      64
#define BACK_MAX_SINK_BASELINE 40
// The least a back with a flat-cut bottom sinks (frame pixels): its cut goes from the classic
// foot row (152) to the screen's bottom edge, with a little to spare for the breathing
#define CUT_BACK_SINK 44

// Per battler slot (BATTLER_TYPE_*): the move from the classic foot point toward BW2's, in screen
// pixels. BW2's foot points are its battler positions (btlv_mcss.c:184-195, singles
// data_ov168_021f327c, doubles data_ov168_021f32ac) through its default camera
// (btlv_camera.c:41-52): singles player (62, 212), enemy (184, 98); doubles player (16, 192) and
// (113, 234), enemy (216, 100) and (156, 91). The classic feet are the bottom of the 80x80
// frame at BATTLER_POS_*: x, y + 40. BW2's x is taken where Platinum's HUD allows it:
// - The player side keeps its classic row: BW2's is 20 to 42 px below the screen, which only
//   works under BW2's translucent text box; under Platinum's opaque one a small back would
//   vanish at the command menu. Tall backs still sink toward it (BattleStageLayout_BackMaxSink).
// - The enemy side keeps its classic row too: BW2's, 8 to 10 px lower, puts the feet and the
//   blob behind Platinum's player healthbar (from y 95 for x >= 150 in singles, 88 in doubles;
//   BW2's gauge is smaller and lower, btlv_gauge.c:662).
// - Doubles player slot 2 stops at x 100 (BW2 113), where its head would go under the player
//   gauges, and slot 1 at 28 (BW2 16) keeps the pair as far apart (72 px; BW2 97, classic 40).
static const s8 sRestOffset[BATTLER_TYPE_MAX][2] = {
    [BATTLER_TYPE_SOLO_PLAYER] = { 62 - 64, 0 },
    [BATTLER_TYPE_SOLO_ENEMY] = { 184 - 192, 0 },
    [BATTLER_TYPE_PLAYER_SIDE_SLOT_1] = { 28 - 40, 0 },
    [BATTLER_TYPE_ENEMY_SIDE_SLOT_1] = { 216 - 216, 0 },
    [BATTLER_TYPE_PLAYER_SIDE_SLOT_2] = { 100 - 80, 0 },
    [BATTLER_TYPE_ENEMY_SIDE_SLOT_2] = { 156 - 176, 0 },
};

typedef struct StageLayout {
    BattleSystem *battleSys;
    const u32 *debugFlags;
    BOOL hasArena;
    int ease; // 0 .. LAYOUT_EASE_STEPS
    int restDelay;
    BOOL action; // an animation ran and the text box hasn't shown since
    int waitFrames; // of the move-animation command waiting now
    int offset[MAX_BATTLERS][2];
} StageLayout;

static StageLayout sStageLayout;
BattleStageLayoutStats sBattleStageLayout;

static BOOL LayoutOff(void)
{
    return sStageLayout.battleSys == NULL
        || !sStageLayout.hasArena
        || (sStageLayout.debugFlags != NULL && (*sStageLayout.debugFlags & (BATTLE_STAGE_DEBUG_CLASSIC_SPRITES | BATTLE_STAGE_DEBUG_PLATINUM_LAYOUT)))
        || TotemBattle_IsActive(sStageLayout.battleSys);
}

// Smoothstep of step / steps, in 1/256
static int Smooth(int step, int steps)
{
    int t = step * 256 / steps;

    return t * t * (3 * 256 - 2 * t) / (256 * 256);
}

void BattleStageLayout_Init(BattleSystem *battleSys, BOOL hasArena, const u32 *debugFlags)
{
    memset(&sStageLayout, 0, sizeof(sStageLayout));
    memset(&sBattleStageLayout, 0, sizeof(sBattleStageLayout));
    sStageLayout.battleSys = battleSys;
    sStageLayout.hasArena = hasArena;
    sStageLayout.debugFlags = debugFlags;
    // The battle opens with the battlers at rest
    sStageLayout.ease = LAYOUT_EASE_STEPS;
}

void BattleStageLayout_Free(void)
{
    memset(&sStageLayout, 0, sizeof(sStageLayout));
}

void BattleStageLayout_Advance(BOOL visible)
{
    int max, i, s;

    if (sStageLayout.battleSys == NULL) {
        return;
    }

    sBattleStageLayout.on = visible && !LayoutOff();

    if (!sBattleStageLayout.on) {
        // Classic at once, and back at rest when it comes on again
        sStageLayout.ease = LAYOUT_EASE_STEPS;
        sStageLayout.restDelay = 0;
        sStageLayout.action = FALSE;
        memset(sStageLayout.offset, 0, sizeof(sStageLayout.offset));
        memset(sBattleStageLayout.offset, 0, sizeof(sBattleStageLayout.offset));
        sBattleStageLayout.ease = 0;
        return;
    }

    // From an animation until the text box shows again: between the hits of a multi-hit move,
    // the HP drain and the faint, the battlers stay where the animations aim
    if (sBattleStageLayout.sequences > 0 || sBattleStageLayout.scriptActive) {
        sStageLayout.action = TRUE;
    } else if (!BattleTextbox_IsClear()) {
        sStageLayout.action = FALSE;
    }

    if (sStageLayout.action) {
        sStageLayout.restDelay = LAYOUT_REST_DELAY;

        if (sStageLayout.ease > 0) {
            sStageLayout.ease--;
        }
    } else if (sStageLayout.restDelay > 0) {
        sStageLayout.restDelay--;
    } else if (sStageLayout.ease < LAYOUT_EASE_STEPS) {
        sStageLayout.ease++;
    }

    sBattleStageLayout.ease = sStageLayout.ease;
    s = Smooth(sStageLayout.ease, LAYOUT_EASE_STEPS);
    max = BattleSystem_MaxBattlers(sStageLayout.battleSys);

    for (i = 0; i < MAX_BATTLERS; i++) {
        int type = i < max ? BattleSystem_BattlerSlot(sStageLayout.battleSys, i) : BATTLER_TYPE_MAX;

        if (type >= BATTLER_TYPE_MAX) {
            sStageLayout.offset[i][0] = 0;
            sStageLayout.offset[i][1] = 0;
        } else {
            sStageLayout.offset[i][0] = (sRestOffset[type][0] * s + (sRestOffset[type][0] < 0 ? -128 : 128)) / 256;
            sStageLayout.offset[i][1] = (sRestOffset[type][1] * s + (sRestOffset[type][1] < 0 ? -128 : 128)) / 256;
        }

        sBattleStageLayout.offset[i][0] = (s8)sStageLayout.offset[i][0];
        sBattleStageLayout.offset[i][1] = (s8)sStageLayout.offset[i][1];
    }
}

BOOL BattleStageLayout_Offset(int battler, int *dx, int *dy)
{
    *dx = 0;
    *dy = 0;

    if (sStageLayout.battleSys == NULL || !sBattleStageLayout.on || battler < 0 || battler >= MAX_BATTLERS) {
        return FALSE;
    }

    *dx = sStageLayout.offset[battler][0];
    *dy = sStageLayout.offset[battler][1];
    return *dx != 0 || *dy != 0;
}

BOOL BattleStageLayout_SideOffset(int side, int *dx, int *dy)
{
    int sumX = 0, sumY = 0, count = 0;
    int max, i;

    *dx = 0;
    *dy = 0;

    if (sStageLayout.battleSys == NULL || !sBattleStageLayout.on) {
        return FALSE;
    }

    max = BattleSystem_MaxBattlers(sStageLayout.battleSys);

    for (i = 0; i < max && i < MAX_BATTLERS; i++) {
        if ((BattleSystem_BattlerSlot(sStageLayout.battleSys, i) & 1) == side) {
            sumX += sStageLayout.offset[i][0];
            sumY += sStageLayout.offset[i][1];
            count++;
        }
    }

    if (count == 0) {
        return FALSE;
    }

    *dx = sumX / count;
    *dy = sumY / count;
    return *dx != 0 || *dy != 0;
}

BOOL BattleStageLayout_PlatformShift(int side, VecFx32 *shift)
{
    int dx, dy;

    shift->x = 0;
    shift->y = 0;
    shift->z = 0;

    if (!BattleStageLayout_SideOffset(side, &dx, &dy)) {
        return FALSE;
    }

    return BattleStageSprites_GroundShift(side, dx, dy, shift);
}

BOOL BattleStageLayout_Similarity(int battler, BattleStageCameraSimilarity *similarity)
{
    int dx, dy;
    BOOL moved = BattleStageLayout_Offset(battler, &dx, &dy);

    // Off home the camera's anchors stand at the layout place, so a sprite point p, which is at
    // p + d there, maps to now + scale * (p + d - home)
    if (BattleStageCamera_GetSimilarity(battler, similarity)) {
        similarity->homeX -= dx;
        similarity->homeY -= dy;
        return TRUE;
    }

    if (!moved) {
        return FALSE;
    }

    similarity->homeX = 0;
    similarity->homeY = 0;
    similarity->nowX = dx * FX32_ONE;
    similarity->nowY = dy * FX32_ONE;
    similarity->scale = FX32_ONE;
    return TRUE;
}

int BattleStageLayout_StreamScale(int storedScale)
{
    if (storedScale <= MON_STREAM_SCALE_ONE
        || (sStageLayout.debugFlags != NULL && (*sStageLayout.debugFlags & BATTLE_STAGE_DEBUG_PLATINUM_LAYOUT))) {
        return storedScale;
    }

    // Megas are stored at 14 to 16 to match their base form's back at the baseline
    return (storedScale * STREAM_BACK_DRAWN + STREAM_BACK_BASELINE / 2) / STREAM_BACK_BASELINE;
}

int BattleStageLayout_BackMaxSink(void)
{
    if (sStageLayout.debugFlags != NULL && (*sStageLayout.debugFlags & BATTLE_STAGE_DEBUG_PLATINUM_LAYOUT)) {
        return BACK_MAX_SINK_BASELINE;
    }

    return BACK_MAX_SINK_BW2;
}

int BattleStageLayout_CutBackSink(void)
{
    if (sStageLayout.debugFlags != NULL && (*sStageLayout.debugFlags & BATTLE_STAGE_DEBUG_PLATINUM_LAYOUT)) {
        return 0;
    }

    return CUT_BACK_SINK;
}

void BattleStageLayout_SetScriptActive(BOOL active)
{
    sBattleStageLayout.scriptActive = active ? TRUE : FALSE;
}

void BattleStage_BeginAnimSequence(BOOL hideTextbox)
{
    if (sBattleStageLayout.sequences < 0xFF) {
        sBattleStageLayout.sequences++;
    }

    sStageLayout.waitFrames = 0;

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
    BOOL placed = !sBattleStageLayout.on || sStageLayout.ease == 0;
    BOOL ready = BattleTextbox_IsReadyForAnim(sStageLayout.waitFrames) && placed;

    if (!ready && sStageLayout.waitFrames < LAYOUT_ANIM_WAIT_MAX) {
        sStageLayout.waitFrames++;
        sBattleStageLayout.animWaitFrames++;
        return FALSE;
    }

    if ((u32)sStageLayout.waitFrames > sBattleStageLayout.animWaitMax) {
        sBattleStageLayout.animWaitMax = sStageLayout.waitFrames;
    }

    sStageLayout.waitFrames = 0;
    return TRUE;
}
