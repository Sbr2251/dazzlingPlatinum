#include "battle/mega_evolution.h"
#include "pokemon.h"
#include "constants/species.h"
#include "constants/forms.h"
#include "struct_defs/pokemon_mega_data.h"

// External references to mega evolution data table
extern const MegaEvolutionData sMegaEvolutionTable[];
extern const int sMegaEvolutionTableSize;

BOOL Pokemon_CanMegaEvolve(const Pokemon *mon)
{
    if (mon == NULL) {
        return FALSE;
    }

    int species = Pokemon_GetValue((Pokemon *)mon, MON_DATA_SPECIES, NULL);
    int heldItem = Pokemon_GetValue((Pokemon *)mon, MON_DATA_HELD_ITEM, NULL);
    int currentForm = Pokemon_GetValue((Pokemon *)mon, MON_DATA_FORM, NULL);

    // Cannot mega evolve if already mega evolved
    if (currentForm & FORM_FLAG_MEGA) {
        return FALSE;
    }

    // Check if this species + item combination exists in the table
    for (int i = 0; i < sMegaEvolutionTableSize; i++) {
        if (sMegaEvolutionTable[i].baseSpecies == species && 
            sMegaEvolutionTable[i].requiredItem == heldItem) {
            return TRUE;
        }
    }

    return FALSE;
}

const MegaEvolutionData* GetMegaEvolutionData(int species, int heldItem)
{
    for (int i = 0; i < sMegaEvolutionTableSize; i++) {
        if (sMegaEvolutionTable[i].baseSpecies == species && 
            sMegaEvolutionTable[i].requiredItem == heldItem) {
            return &sMegaEvolutionTable[i];
        }
    }

    return NULL;
}

void Pokemon_MegaEvolve(Pokemon *mon)
{
    if (mon == NULL) {
        return;
    }

    int species = Pokemon_GetValue(mon, MON_DATA_SPECIES, NULL);
    int heldItem = Pokemon_GetValue(mon, MON_DATA_HELD_ITEM, NULL);

    // Get mega evolution data
    const MegaEvolutionData *megaData = GetMegaEvolutionData(species, heldItem);
    if (megaData == NULL) {
        return; // Cannot mega evolve
    }

    // Set the mega form
    Pokemon_SetValue(mon, MON_DATA_FORM, &megaData->megaForm);

    // Note: Stats, ability, and type changes are handled by the Pokémon data system
    // when the form is changed. The mega evolution data table is consulted
    // by Pokemon_CalcLevelAndStats() to apply the correct stats.

    // Recalculate stats with the new form
    Pokemon_CalcLevelAndStats(mon);
}

void Pokemon_RevertMegaEvolution(Pokemon *mon)
{
    if (mon == NULL) {
        return;
    }

    int currentForm = Pokemon_GetValue(mon, MON_DATA_FORM, NULL);

    // Only revert if currently mega evolved
    if (!(currentForm & FORM_FLAG_MEGA)) {
        return;
    }

    // Revert to base form (form 0)
    int baseForm = 0;
    Pokemon_SetValue(mon, MON_DATA_FORM, &baseForm);

    // Recalculate stats with base form
    Pokemon_CalcLevelAndStats(mon);
}

BOOL Pokemon_IsMegaEvolved(const Pokemon *mon)
{
    if (mon == NULL) {
        return FALSE;
    }

    int currentForm = Pokemon_GetValue((Pokemon *)mon, MON_DATA_FORM, NULL);
    return (currentForm & FORM_FLAG_MEGA) != 0;
}
