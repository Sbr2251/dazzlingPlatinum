#include "battle/battle_events.h"

#include <nitro.h>

#include "constants/battle.h"
#include "constants/heap.h"
#include "generated/trainer_classes.h"
#include "struct_defs/trainer.h"

#include "battle/ability_popup.h"
#include "battle/ov16_0223DF00.h"

#include "brightness_controller.h"
#include "heap.h"
#include "pokedex.h"
#include "sound.h"
#include "sound_layers.h"
#include "sound_playback.h"
#include "sound_system.h"
#include "sys_task.h"
#include "sys_task_manager.h"
#include "trainer_data.h"

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
// Gym Leader "last Pokemon" music
// ---------------------------------------------------------------------------------------------------------------

// BW2 switches to its leader "last Pokemon" theme (BGM 0x47B) when a Gym Leader shows trainer message 19 or 20 (last
// Pokemon, last Pokemon at half HP), fading the battle theme out over 8 frames first (btl_client.c:2251-2266).
// BW2's audio is not used: the switch goes to Platinum's Frontier Brain battle theme, already in the SDAT. It is
// the step up from the Gym Leader theme in the same boss register, and it has no story meaning before the
// post-game Battle Frontier, unlike the Elite Four, Champion, Galactic and Cyrus themes. See docs/battle_events.md.
#define LEADER_LAST_MON_BGM      SEQ_BATTLE_FRONTIER_BRAIN
#define LEADER_LAST_MON_FADE_OUT 8

static SysTask *sLeaderBgmTask = NULL;

static BOOL BattleEvents_IsGymLeaderClass(int trainerClass)
{
    switch (trainerClass) {
    case TRAINER_CLASS_LEADER_ROARK:
    case TRAINER_CLASS_LEADER_GARDENIA:
    case TRAINER_CLASS_LEADER_WAKE:
    case TRAINER_CLASS_LEADER_MAYLENE:
    case TRAINER_CLASS_LEADER_FANTINA:
    case TRAINER_CLASS_LEADER_CANDICE:
    case TRAINER_CLASS_LEADER_BYRON:
    case TRAINER_CLASS_LEADER_VOLKNER:
        return TRUE;
    }

    return FALSE;
}

static int BattleEvents_CurrentBattleBGM(void)
{
    return Sound_GetSequenceIDFromSoundHandle(SoundSystem_GetSoundHandle(SOUND_HANDLE_TYPE_BGM));
}

static void LeaderBgm_Task(SysTask *task, void *data)
{
    if (Sound_IsFadeActive() == FALSE) {
        Sound_StopBGM(SEQ_BATTLE_GYM_LEADER, 0);
        Sound_PlayBGM(LEADER_LAST_MON_BGM);
        SysTask_Done(task);
        sLeaderBgmTask = NULL;
    }
}

void BattleEvents_OnTrainerMessage(BattleSystem *battleSys, int battler, int trainerMsg)
{
    Trainer *trainer;

    if (trainerMsg != TRMSG_LAST_BATTLER && trainerMsg != TRMSG_LAST_BATTLER_HALF_HP) {
        return;
    }

    if ((BattleSystem_BattleType(battleSys) & BATTLE_TYPE_TRAINER) == FALSE || sLeaderBgmTask != NULL) {
        return;
    }

    trainer = BattleSystem_GetTrainer(battleSys, battler);

    if (BattleEvents_IsGymLeaderClass(trainer->header.trainerType) == FALSE) {
        return;
    }

    // Only out of the standard Gym Leader theme: a scripted battle with its own music keeps it, and the switch
    // happens once (the half-HP line after the last-Pokemon line finds the new theme playing)
    if (BattleEvents_CurrentBattleBGM() != SEQ_BATTLE_GYM_LEADER) {
        return;
    }

    Sound_FadeOutBGM(0, LEADER_LAST_MON_FADE_OUT);
    sLeaderBgmTask = SysTask_Start(LeaderBgm_Task, NULL, 1000);
    gBattleEventsDebug.leaderBgm = LEADER_LAST_MON_BGM;
    gBattleEventsDebug.leaderBgmTrainerMsg = trainerMsg;
}

// ---------------------------------------------------------------------------------------------------------------
// Low-HP beep vs the low-HP music layer
// ---------------------------------------------------------------------------------------------------------------

// BW2 has no low-HP beep (btlv_gauge.c:1459-1501 swaps in a pinch BGM instead). The hack's low-HP music layer
// plays that part, so Platinum's HINSI beep stays off while the layer plays. A battle theme without the layer
// (every theme but the wild one today) keeps the beep.
BOOL BattleEvents_SuppressLowHPBeep(void)
{
    BOOL layer = SoundLayers_IsActive(BGM_LAYER_LOW_HP);

    gBattleEventsDebug.lowHPLayerActive = layer;
    gBattleEventsDebug.hinsiPlaying = Sound_IsEffectPlaying(SEQ_SE_DP_HINSI);
    gBattleEventsDebug.beepSuppressed = layer;

    if (layer) {
        gBattleEventsDebug.beepSuppressedFrames++;
    }

    return layer;
}

// ---------------------------------------------------------------------------------------------------------------

void BattleEvents_Shutdown(void)
{
    AbilityPopup_Shutdown();

    if (sCriticalFlashTask != NULL) {
        SysTask_Done(sCriticalFlashTask);
        sCriticalFlashTask = NULL;
    }

    if (sLeaderBgmTask != NULL) {
        SysTask_Done(sLeaderBgmTask);
        sLeaderBgmTask = NULL;
    }
}
