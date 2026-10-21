#ifndef POKEPLATINUM_BATTLE_BATTLE_EVENTS_H
#define POKEPLATINUM_BATTLE_BATTLE_EVENTS_H

#include <nitro/types.h>

#include "battle/ov16_0223DF00.h"

// BW2 battle events with no BW2 effect script behind them (docs/battle_events.md):
// - critical capture: the Gen 5 roll from the number of species caught, one shake, its own sound and flash;
// - the Gym Leader "last Pokemon" music;
// - the debug block below, which the headless harness reads (and writes forceCriticalCapture in).

#define BATTLE_EVENTS_DEBUG_MAGIC 0x54564542 // "BEVT"

enum CriticalCaptureForce {
    CRITICAL_CAPTURE_ROLL = 0, // the normal Gen 5 roll
    CRITICAL_CAPTURE_FORCE_ON, // every throw is a critical capture (still one shake check)
    CRITICAL_CAPTURE_FORCE_OFF, // never
};

// Lives in the battle overlay's .data, so it is reset (magic included) every time a battle loads.
typedef struct BattleEventsDebug {
    u32 magic;
    u8 forceCriticalCapture; // enum CriticalCaptureForce, written by the harness only
    u8 lastCaptureCritical; // the last throw's roll
    u8 lastCaptureShakes; // what the throw returned: 0-3 broke free after that many shakes, 4 caught
    u8 criticalCaptures; // critical captures rolled this battle
    u16 lastCriticalThreshold; // the last throw's Random(256) threshold (0 = no chance)
    u16 dexCaught; // the caught count the last roll used
    u16 popupShows[2]; // banners started, by side (0 player, 1 enemy)
    u16 popupAbility[2]; // the ability on each side's banner
    u8 popupBattler[2];
    u8 popupState[2]; // enum AbilityPopupState in ability_popup.c, 0 = none
    s16 popupX[2]; // the banner's screen x
    u16 popupSkipped; // banners that could not get OBJ VRAM or a palette
    u16 leaderBgm; // the BGM the leader switch started, 0 if none yet
    u16 leaderBgmTrainerMsg; // the trainer message that started it
    u8 beepSuppressed; // 1 while the low-HP layer keeps the HINSI beep off
    u8 lowHPLayerActive; // SoundLayers_IsActive(BGM_LAYER_LOW_HP) as the beep task last saw it
    u8 hinsiPlaying; // Sound_IsEffectPlaying(SEQ_SE_DP_HINSI) as the beep task last saw it
    u8 criticalFlashes; // critical-capture flashes played
    u32 beepSuppressedFrames; // frames the beep task spent with the beep held off by the layer
} BattleEventsDebug;

extern BattleEventsDebug gBattleEventsDebug;

// Critical capture (pokebw2 btl_server_flow_sub.c:1045 CheckCriticalCapture). catchRate is the modified catch rate
// (Platinum's "a", 0-255+, before the shake-probability square roots). Returns TRUE for a critical capture, which
// then gets a single shake check.
BOOL BattleEvents_RollCriticalCapture(BattleSystem *battleSys, u32 catchRate);

// The critical capture's own sound and flash, played when the ball has dropped, before its one shake. No BW2 effect
// script is used: a white flash of the main screen (the 3D arena follows the 2D brightness) plus a sparkle SE.
void BattleEvents_StartCriticalCaptureFlash(BattleSystem *battleSys);
BOOL BattleEvents_IsCriticalCaptureFlashDone(void);

// Gym Leader "last Pokemon" music (pokebw2 btl_client.c:2251-2266). Called when the battle script prints a buffered
// trainer message; switches the BGM when a Gym Leader shows their last-Pokemon line.
void BattleEvents_OnTrainerMessage(BattleSystem *battleSys, int battler, int trainerMsg);

// Ends the pop-up banners, the capture flash and a pending music switch. Call before the battle frees its systems.
void BattleEvents_Shutdown(void);

#endif // POKEPLATINUM_BATTLE_BATTLE_EVENTS_H
