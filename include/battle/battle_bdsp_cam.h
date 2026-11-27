#ifndef POKEPLATINUM_BATTLE_BDSP_CAM_H
#define POKEPLATINUM_BATTLE_BDSP_CAM_H

#include "battle/battle_system.h"
#include "port/sim_battle3d.h"

// BDSP camera choreography controller (intro pan, send-out cut, idle drift/orbit,
// attack/hit cuts), backed by extracted BDSP camera curves in <bdsp_assets>/cameras/
// with smooth procedural fallback. Owned by the camera lane.
void BattleBdspCam_Reset(void);
void BattleBdspCam_NotifyIntroStart(BOOL isTrainerBattle);
void BattleBdspCam_NotifyTrainerThrow(void);
void BattleBdspCam_NotifyAttack(int attacker, u16 move);
void BattleBdspCam_NotifyHit(int defender);
void BattleBdspCam_NotifyFaint(int battler);

// Adjusts frame->camEye, frame->camTarget, and frame->camFovDeg in place
// (deterministic 1/60s stepping; respects BattleStage suppression and headless gate).
void BattleBdspCam_Update(BattleSystem *battleSys, SIM_Battle3DFrame *frame);

#endif // POKEPLATINUM_BATTLE_BDSP_CAM_H
