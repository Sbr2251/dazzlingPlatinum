#ifndef POKEPLATINUM_SOUND_AREA_FX_H
#define POKEPLATINUM_SOUND_AREA_FX_H

#include <nitro/types.h>

/*
 * Area audio effects ("area FX").
 *
 * A capture-unit effect (NNS_SndCaptureStartEffect) that post-processes the
 * whole mixer output (BGM, SFX and cries) while the player is in certain
 * places:
 *   - caves (map header battle background CAVE_1/2/3)  -> SOUND_AREA_FX_ECHO
 *   - Distortion World (battle background)             -> SOUND_AREA_FX_WARP
 *   - surfing                                          -> SOUND_AREA_FX_MUFFLE
 *
 * The capture unit is exclusive (reverb OR effect OR sampling). Area FX only
 * takes it while it is free, and gives it up when the Pokedex cry filter, the
 * title/ending reverb or any non-field sound scene (battle, contest, ...)
 * needs it. See src/sound_area_fx.c for the details.
 */

enum SoundAreaFxMode {
    SOUND_AREA_FX_NONE = 0,
    SOUND_AREA_FX_ECHO, // Feedback delay, for caves
    SOUND_AREA_FX_MUFFLE, // Two-pole low-pass, for water
    SOUND_AREA_FX_WARP, // LFO-modulated delay + light ring mod, for the Distortion World

    SOUND_AREA_FX_MODE_COUNT
};

// Reasons why area FX must not use the capture unit. Each reason is an
// independent bit, so suspend/resume calls from different systems can not
// cancel each other out.
enum SoundAreaFxSuspendReason {
    SOUND_AREA_FX_SUSPEND_EXTERNAL = 1 << 0, // Free for other callers (e.g. scripts)
    SOUND_AREA_FX_SUSPEND_FILTER = 1 << 1, // Sound_StartFilter() owns the capture unit
    SOUND_AREA_FX_SUSPEND_REVERB = 1 << 2, // Sound_StartReverb() owns the capture unit
    SOUND_AREA_FX_SUSPEND_SCENE = 1 << 3, // The main sound scene is not the field
};

// Called once per frame (from SoundSystem_Tick). Starts/stops the capture
// effect and tracks the sound scene.
void SoundAreaFx_Update(void);

// Zone hooks.
void SoundAreaFx_OnMapChange(u32 mapHeaderID);
void SoundAreaFx_SetSurfing(BOOL surfing);
enum SoundAreaFxMode SoundAreaFx_GetModeForMapHeader(u32 mapHeaderID);

// Overrides the zone mode until the next map change.
void SoundAreaFx_SetMode(enum SoundAreaFxMode mode);
enum SoundAreaFxMode SoundAreaFx_GetMode(void);
enum SoundAreaFxMode SoundAreaFx_GetEffectiveMode(void);

// Capture arbitration. SuspendFor() stops the effect immediately (before
// returning) if area FX currently owns the capture unit. ResumeFor() only
// clears the reason; the effect restarts on a later SoundAreaFx_Update()
// once the capture unit is free.
void SoundAreaFx_SuspendFor(u32 reasons);
void SoundAreaFx_ResumeFor(u32 reasons);
BOOL SoundAreaFx_OwnsCapture(void);

#endif // POKEPLATINUM_SOUND_AREA_FX_H
