#ifndef POKEPLATINUM_BATTLE_MEGA_EVOLUTION_H
#define POKEPLATINUM_BATTLE_MEGA_EVOLUTION_H

#include "pokemon.h"
#include "struct_defs/pokemon_mega_data.h"

/**
 * @brief Get mega evolution data for a species + item combination
 *
 * Searches the mega evolution table for a matching entry.
 *
 * @param species The base species ID
 * @param heldItem The held item ID
 * @return Pointer to MegaEvolutionData if found, NULL otherwise
 */
const MegaEvolutionData* GetMegaEvolutionData(int species, int heldItem);

/**
 * @brief Perform mega evolution transformation
 *
 * Transforms the Pokémon into its mega form by:
 * - Changing form to mega form
 * - Recalculating the stored ability from the mega form's species data
 * - Recalculating level and stats from the mega form's species data
 *
 * The current HP is adjusted by the change in max HP, as for any other
 * form change.
 *
 * @param mon Pointer to the Pokémon to mega evolve
 * @param megaData The mega evolution entry to use, as returned by GetMegaEvolutionData
 * @return TRUE if the Pokémon changed into its mega form, FALSE if the entry
 *         is not for its species or it is already in that form
 */
BOOL Pokemon_MegaEvolve(Pokemon *mon, const MegaEvolutionData *megaData);

/**
 * @brief Revert mega evolution (end of battle)
 *
 * Reverts the Pokémon back to its base form and recalculates its ability
 * and stats. Does nothing if the Pokémon is not mega evolved.
 * Should be called at the end of battle for all party Pokémon.
 *
 * @param mon Pointer to the Pokémon to revert
 */
void Pokemon_RevertMegaEvolution(Pokemon *mon);

/**
 * @brief Check if a Pokémon is currently mega evolved
 *
 * Checks if the Pokémon's species and current form match an entry in the
 * mega evolution data table.
 *
 * @param mon Pointer to the Pokémon to check
 * @return TRUE if mega evolved, FALSE otherwise
 */
BOOL Pokemon_IsMegaEvolved(const Pokemon *mon);

#endif // POKEPLATINUM_BATTLE_MEGA_EVOLUTION_H
