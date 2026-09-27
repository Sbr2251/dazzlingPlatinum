#ifndef POKEPLATINUM_OV5_FIELD_CAMERA_ZONES_H
#define POKEPLATINUM_OV5_FIELD_CAMERA_ZONES_H

#include "field/field_system_decl.h"

// Data-driven camera tilt zones. The zone table lives in field_camera_zones.c.
//
// FieldCameraZones_Reset must be called whenever a fresh field camera is
// created (FieldCamera_Create does this), so the tracked offsets start at zero
// and match the stock camera exactly.
//
// FieldCameraZones_Update is called once per rendered field frame, before the
// view matrix is computed. It eases the camera pitch/distance offsets toward
// the target implied by the player's continuous position.
void FieldCameraZones_Reset(void);
void FieldCameraZones_Update(FieldSystem *fieldSystem);

#endif // POKEPLATINUM_OV5_FIELD_CAMERA_ZONES_H
