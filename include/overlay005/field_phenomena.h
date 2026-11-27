#ifndef POKEPLATINUM_FIELD_PHENOMENA_H
#define POKEPLATINUM_FIELD_PHENOMENA_H

#include <nitro/types.h>

#include "constants/wild_encounters.h"

#include "field/field_system_decl.h"
#include "overlay006/phenomena_tables.h"

#include "field_battle_data_transfer.h"

void FieldPhenomena_OnFieldInit(FieldSystem *fieldSystem);
void FieldPhenomena_OnFieldExit(FieldSystem *fieldSystem);
void FieldPhenomena_OnZoneChange(FieldSystem *fieldSystem);
void FieldPhenomena_OnBattleStart(FieldSystem *fieldSystem);
void FieldPhenomena_Clear(void);

void FieldPhenomena_OnPlayerStep(FieldSystem *fieldSystem);
void FieldPhenomena_Update(FieldSystem *fieldSystem);
void FieldPhenomena_Draw(FieldSystem *fieldSystem);

// Returns:
//   1 if a phenomenon wild battle was started
//  -1 if a phenomenon item pickup occurred (skip normal wild encounter)
//   0 if no phenomenon triggered on the player's current tile
int FieldPhenomena_CheckStepTrigger(FieldSystem *fieldSystem);

BOOL FieldPhenomena_TrySuperRodEncounter(FieldSystem *fieldSystem, enum EncounterFishingRodType rodType, FieldBattleDTO **battleParams);

BOOL FieldPhenomena_DebugForceSpawn(FieldSystem *fieldSystem, enum PhenomenonType type, BOOL hasCoords, int tileX, int tileZ);
void FieldPhenomena_GetState(BOOL *outActive, enum PhenomenonType *outType, int *outMapHeaderID, int *outTileX, int *outTileZ, int *outStepCounter);

#endif // POKEPLATINUM_FIELD_PHENOMENA_H
