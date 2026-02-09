#include "constants/species.h"
#include "constants/items.h"
#include "constants/forms.h"
#include "generated/abilities.h"
#include "generated/pokemon_types.h"
#include "generated/items.h"
#include "struct_defs/pokemon_mega_data.h"

// Mega Evolution data table
// Each entry defines the properties of a mega-evolved Pokémon
const MegaEvolutionData sMegaEvolutionTable[] = {
    // Mega Garchomp
    // Base stats: 108 HP, 170 Atk, 115 Def, 120 SpAtk, 95 SpDef, 92 Speed
    // Ability: Sand Force (ID 159)
    // Type: Dragon/Ground (unchanged)
    // NOTE: Using placeholder item ID until ITEM_GARCHOMPITE is generated
    {
        .baseSpecies = SPECIES_GARCHOMP,
        .megaForm = MEGA_FORM_GARCHOMP,
        .requiredItem = ITEM_NONE,  // Placeholder: will be ITEM_GARCHOMPITE
        .baseStats = {108, 170, 115, 120, 95, 92},
        .ability = ABILITY_SAND_FORCE,
        .type1 = TYPE_DRAGON,
        .type2 = TYPE_GROUND,
    },
    // Add more mega evolutions here as needed
};

// Size of the mega evolution table
const int sMegaEvolutionTableSize = 1;  // Using literal instead of ARRAY_COUNT for now
