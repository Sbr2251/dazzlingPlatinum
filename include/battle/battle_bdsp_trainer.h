#ifndef POKEPLATINUM_BATTLE_BDSP_TRAINER_H
#define POKEPLATINUM_BATTLE_BDSP_TRAINER_H

#include "battle/battle_system.h"
#include "port/sim_battle3d.h"

// BDSP 3D trainer & Poke Ball intro animation controller.
// Inspects player trainer state, hides 2D trainer back OBJ when 3D Lucas/Dawn
// .glb is loaded, drives the throw animation + Poke Ball arc in frame->actors[],
// and notifies BattleBdspCam_NotifyTrainerThrow() on send-out. Owned by trainer lane.
void BattleBdspTrainer_Reset(void);
void BattleBdspTrainer_Update(BattleSystem *battleSys, SIM_Battle3DFrame *frame);
BOOL BattleBdspTrainer_IsIntroActive(void);

#endif // POKEPLATINUM_BATTLE_BDSP_TRAINER_H
