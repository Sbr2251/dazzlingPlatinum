#include "battle/mega_evolution.h"
#include "pokemon.h"
#include "pokemon_mega_data.h"
#include "constants/species.h"
#include "constants/forms.h"
#include "struct_defs/pokemon_mega_data.h"

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

BOOL Pokemon_MegaEvolve(Pokemon *mon, const MegaEvolutionData *megaData)
{
    if (mon == NULL || megaData == NULL) {
        return FALSE;
    }

    int species = Pokemon_GetValue(mon, MON_DATA_SPECIES, NULL);
    int currentForm = Pokemon_GetValue(mon, MON_DATA_FORM, NULL);

    // The entry must belong to this species (e.g. not a transformed Ditto)
    if (species != megaData->baseSpecies || currentForm == megaData->megaForm) {
        return FALSE;
    }

    // Mega forms are real forms: the species data for the new form supplies
    // the mega base stats, types and ability, so the usual form change path
    // (set form, recalc ability, recalc stats) is all that is needed
    int megaForm = megaData->megaForm;
    Pokemon_SetValue(mon, MON_DATA_FORM, &megaForm);
    Pokemon_CalcAbility(mon);
    Pokemon_CalcLevelAndStats(mon);

    return TRUE;
}

void Pokemon_RevertMegaEvolution(Pokemon *mon)
{
    if (Pokemon_IsMegaEvolved(mon) == FALSE) {
        return;
    }

    // Revert to base form (form 0); the ability is derived again from the
    // base species data and personality, as it was when the mon was created
    int baseForm = 0;
    Pokemon_SetValue(mon, MON_DATA_FORM, &baseForm);
    Pokemon_CalcAbility(mon);
    Pokemon_CalcLevelAndStats(mon);
}

BOOL Pokemon_IsMegaEvolved(const Pokemon *mon)
{
    if (mon == NULL) {
        return FALSE;
    }

    int species = Pokemon_GetValue((Pokemon *)mon, MON_DATA_SPECIES, NULL);
    int currentForm = Pokemon_GetValue((Pokemon *)mon, MON_DATA_FORM, NULL);

    return MegaEvolution_GetFormData(species, currentForm) != NULL;
}

BOOL Item_IsMegaStone(int item)
{
    for (int i = 0; i < sMegaEvolutionTableSize; i++) {
        if (sMegaEvolutionTable[i].requiredItem == item) {
            return TRUE;
        }
    }

    return FALSE;
}
