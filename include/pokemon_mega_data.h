#ifndef POKEPLATINUM_POKEMON_MEGA_DATA_H
#define POKEPLATINUM_POKEMON_MEGA_DATA_H

#include "struct_defs/pokemon_mega_data.h"

extern const MegaEvolutionData sMegaEvolutionTable[];
extern const int sMegaEvolutionTableSize;

/**
 * @brief Get the mega evolution data for a species in a given form
 *
 * Lives outside the battle overlay so the species data and sprite code can
 * treat Mega forms as real forms.
 *
 * @param species The base species ID
 * @param form    The form ID
 * @return Pointer to MegaEvolutionData if (species, form) is a Mega form, NULL otherwise
 */
const MegaEvolutionData *MegaEvolution_GetFormData(int species, int form);

#endif // POKEPLATINUM_POKEMON_MEGA_DATA_H
