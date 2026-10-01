#ifndef POKEPLATINUM_SOUND_LAYERS_H
#define POKEPLATINUM_SOUND_LAYERS_H

#include <nitro/types.h>

// Adaptive battle music: extra "intensity" tracks in a battle theme that fade in while a layer is on.
// Songs without an entry in the layer table in sound_layers.c are left untouched.
enum BGMLayer {
    BGM_LAYER_LOW_HP = 0, // A player-side battler is at or below 25% HP
    BGM_LAYER_MEGA, // The player Mega Evolved (stays on for the rest of the battle)
    BGM_LAYER_TOTEM_ALLY, // The Totem called its ally (stays on for the rest of the battle)
    BGM_LAYER_COUNT,
};

// Turns every layer off and silences the layer tracks of the song on the BGM player at once.
// Call right after the battle BGM starts, and on battle start and end.
void SoundLayers_Reset(void);

// Turns a layer on or off. The layer's tracks fade in or out over the following SoundLayers_Update calls.
void SoundLayers_Set(enum BGMLayer layer, BOOL on);

// Steps the layer fades. Call once per frame while a battle runs.
void SoundLayers_Update(void);

#endif // POKEPLATINUM_SOUND_LAYERS_H
