#ifndef POKEPLATINUM_OV5_FIELD_CINEMATICS_H
#define POKEPLATINUM_OV5_FIELD_CINEMATICS_H

#include <nitro/fx/fx.h>

#include "camera.h"
#include "field/field_system_decl.h"

// Overworld cinematics: scripted, eased moves of the field camera over a
// fixed number of frames. A cinematic snapshots the follow camera on its
// first move and restores that snapshot exactly when the return move ends,
// so frames after a cinematic are identical to frames with no cinematic.
//
// A move is described relative to the camera target at the moment the move
// starts: a target offset in tiles (16 world units each, target height is
// kept), an absolute distance, pitch/yaw in degrees, a vertical field of
// view in degrees, a duration in frames, and an easing curve.

enum CineEasing {
    CINE_EASE_LINEAR = 0,
    CINE_EASE_IN_OUT, // smoothstep: slow at both ends
    CINE_EASE_OUT, // fast start, gentle arrival
    CINE_EASE_IN, // gentle start, fast arrival
    CINE_EASE_COUNT
};

// TRUE when overworld cinematics are enabled (sim_config_prj.ini
// [General] OverworldCinematics, on by default; off under SIM_HEADLESS
// unless SIM_FX_CINE=1, so headless goldens stay byte-identical).
BOOL FieldCinematics_IsEnabled(void);

// Clears any cinematic state. Called when the field camera is (re)created.
void FieldCinematics_Reset(void);

// Per-frame update, called before the camera view matrix is computed.
void FieldCinematics_Update(FieldSystem *fieldSystem);

// TRUE while a cinematic move (out or return) is in progress.
BOOL FieldCinematics_IsActive(void);

// Starts a move. On the first move of a cinematic, snapshots the current
// camera so FieldCinematics_ReturnMove can restore it. A move started
// while another is running retargets from the current camera state.
void FieldCinematics_StartMove(FieldSystem *fieldSystem, s16 targetOffsetXTiles, s16 targetOffsetZTiles, fx32 distance, s16 pitchDeg, s16 yawDeg, u16 fovDeg, u16 frames, u8 easing);

// Starts a move back to the snapshot taken by the first StartMove. When
// the move finishes the snapshot is restored exactly and target tracking
// resumes.
void FieldCinematics_ReturnMove(FieldSystem *fieldSystem, u16 frames, u8 easing);

#endif // POKEPLATINUM_OV5_FIELD_CINEMATICS_H
