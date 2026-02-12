#ifndef POKEPLATINUM_BATTLE_MEGA_EVOLUTION_H
#define POKEPLATINUM_BATTLE_MEGA_EVOLUTION_H

#include "pokemon.h"
#include "struct_defs/pokemon_mega_data.h"

/**
 * @brief Check if a Pokémon can mega evolve
 * 
 * Checks if the Pokémon's species and held item match an entry
 * in the mega evolution data table.
 * 
 * @param mon Pointer to the Pokémon to check
 * @return TRUE if the Pokémon can mega evolve, FALSE otherwise
 */
BOOL Pokemon_CanMegaEvolve(const Pokemon *mon);

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
 * - Updating stats, ability, and types from mega data
 * - Recalculating level and stats
 * 
 * @param mon Pointer to the Pokémon to mega evolve
 */
void Pokemon_MegaEvolve(Pokemon *mon);

/**
 * @brief Revert mega evolution (end of battle)
 * 
 * Reverts the Pokémon back to its base form and recalculates stats.
 * Should be called at the end of battle for all mega evolved Pokémon.
 * 
 * @param mon Pointer to the Pokémon to revert
 */
void Pokemon_RevertMegaEvolution(Pokemon *mon);

/**
 * @brief Check if a Pokémon is currently mega evolved
 * 
 * Checks if the Pokémon's current form has the FORM_FLAG_MEGA flag.
 * 
 * @param mon Pointer to the Pokémon to check
 * @return TRUE if mega evolved, FALSE otherwise
 */
BOOL Pokemon_IsMegaEvolved(const Pokemon *mon);

#endif // POKEPLATINUM_BATTLE_MEGA_EVOLUTION_H
