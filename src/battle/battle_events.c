#include "battle/battle_events.h"

#include <nitro.h>

#include "constants/battle.h"
#include "constants/heap.h"

#include "battle/ability_popup.h"
#include "battle/ov16_0223DF00.h"

#include "brightness_controller.h"
#include "heap.h"
#include "pokedex.h"
#include "sound_playback.h"
#include "sys_task.h"
#include "sys_task_manager.h"

BattleEventsDebug gBattleEventsDebug = {
    .magic = BATTLE_EVENTS_DEBUG_MAGIC,
};

// ---------------------------------------------------------------------------------------------------------------
// Critical capture
// ---------------------------------------------------------------------------------------------------------------

// pokebw2 btl_server_flow_sub.c:1045-1072 CheckCriticalCapture, with BW2's thresholds unchanged. They were set for
// a 649-species National Dex; this hack's dex is smaller, so the top tier (more than 600) cannot be reached.
// Ratios are in 1/2 steps: 0.5x, 1x, 1.5x, 2x, 2.5x.
static int CriticalCapture_RatioHalves(u32 caught)
{
    if (caught > 600) {
        return 5;
    }

    if (caught > 450) {
        return 4;
    }

    if (caught > 300) {
        return 3;
    }

    if (caught > 150) {
        return 2;
    }

    if (caught > 30) {
        return 1;
    }

    return 0;
}

BOOL BattleEvents_RollCriticalCapture(BattleSystem *battleSys, u32 catchRate)
{
    Pokedex *pokedex = BattleSystem_GetPokedex(battleSys);
    u32 caught = pokedex != NULL ? Pokedex_CountCaught_National(pokedex) : 0;
    u32 threshold;
    BOOL critical;

    // BW2: value = min(rate, 255) * ratio / 6, and a critical capture when Random(256) < value
    if (catchRate > 255) {
        catchRate = 255;
    }

    threshold = catchRate * CriticalCapture_RatioHalves(caught) / 2 / 6;
    critical = (BattleSystem_RandNext(battleSys) % 256) < threshold;

    switch (gBattleEventsDebug.forceCriticalCapture) {
    case CRITICAL_CAPTURE_FORCE_ON:
        critical = TRUE;
        break;
    case CRITICAL_CAPTURE_FORCE_OFF:
        critical = FALSE;
        break;
    }

    gBattleEventsDebug.dexCaught = caught;
    gBattleEventsDebug.lastCriticalThreshold = threshold;
    gBattleEventsDebug.lastCaptureCritical = critical;

    if (critical) {
        gBattleEventsDebug.criticalCaptures++;
    }

    return critical;
}

// The critical capture's flash. BW2 plays it inside its capture effect script (0x23a, unextracted), so this is an
// approximation from what the battle has: the main screen's 2D brightness to white and back (as the battle's own
// white flash at battle_display.c ov16_022646C8; the 3D arena follows the 2D brightness), the text box excluded,
// with a sparkle SE.
#define CRITICAL_FLASH_PLANES ((GX_BLEND_PLANEMASK_BG0 | GX_BLEND_PLANEMASK_BG2 | GX_BLEND_PLANEMASK_BG3 | GX_BLEND_PLANEMASK_OBJ | GX_BLEND_PLANEMASK_BD))
#define CRITICAL_FLASH_IN_STEPS  3
#define CRITICAL_FLASH_OUT_STEPS 10
#define CRITICAL_FLASH_SE        SEQ_SE_DP_KIRAN // "kiran": a gleam; in BANK_SE_BATTLE, so it is loaded in battle

static SysTask *sCriticalFlashTask = NULL;
static u8 sCriticalFlashState;

static void CriticalCapture_FlashTask(SysTask *task, void *data)
{
    switch (sCriticalFlashState) {
    case 0:
        Sound_PlayEffect(CRITICAL_FLASH_SE);
        BrightnessController_StartTransition(CRITICAL_FLASH_IN_STEPS, 16, 0, CRITICAL_FLASH_PLANES, BRIGHTNESS_MAIN_SCREEN);
        sCriticalFlashState++;
        break;
    case 1:
        if (BrightnessController_IsTransitionComplete(BRIGHTNESS_MAIN_SCREEN) == TRUE) {
            BrightnessController_StartTransition(CRITICAL_FLASH_OUT_STEPS, 0, 16, CRITICAL_FLASH_PLANES, BRIGHTNESS_MAIN_SCREEN);
            sCriticalFlashState++;
        }
        break;
    default:
        if (BrightnessController_IsTransitionComplete(BRIGHTNESS_MAIN_SCREEN) == TRUE) {
            SysTask_Done(task);
            sCriticalFlashTask = NULL;
        }
        break;
    }
}

void BattleEvents_StartCriticalCaptureFlash(BattleSystem *battleSys)
{
    if (sCriticalFlashTask != NULL) {
        return;
    }

    sCriticalFlashState = 0;
    sCriticalFlashTask = SysTask_Start(CriticalCapture_FlashTask, NULL, 1000);
    gBattleEventsDebug.criticalFlashes++;
}

BOOL BattleEvents_IsCriticalCaptureFlashDone(void)
{
    return sCriticalFlashTask == NULL;
}

// ---------------------------------------------------------------------------------------------------------------

void BattleEvents_Shutdown(void)
{
    AbilityPopup_Shutdown();

    if (sCriticalFlashTask != NULL) {
        SysTask_Done(sCriticalFlashTask);
        sCriticalFlashTask = NULL;
    }
}
