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
    // Ability: Sand Force
    // Type: Dragon/Ground (unchanged)
    {
        .baseSpecies = SPECIES_GARCHOMP,
        .megaForm = MEGA_FORM_GARCHOMP,
        .requiredItem = ITEM_GARCHOMPITE,
        .baseStats = {108, 170, 115, 120, 95, 92},
        .ability = ABILITY_SAND_FORCE,
        .type1 = TYPE_DRAGON,
        .type2 = TYPE_GROUND,
    },
    // Mega Lucario
    // Base stats: 70 HP, 145 Atk, 88 Def, 140 SpAtk, 70 SpDef, 112 Speed
    // Ability: Adaptability
    // Type: Fighting/Steel (unchanged)
    {
        .baseSpecies = SPECIES_LUCARIO,
        .megaForm = MEGA_FORM_LUCARIO,
        .requiredItem = ITEM_LUCARIONITE,
        .baseStats = {70, 145, 88, 140, 70, 112},
        .ability = ABILITY_ADAPTABILITY,
        .type1 = TYPE_FIGHTING,
        .type2 = TYPE_STEEL,
    },
    // Mega Gengar
    // Base stats: 60 HP, 65 Atk, 80 Def, 170 SpAtk, 95 SpDef, 130 Speed
    // Ability: Shadow Tag
    // Type: Ghost/Poison (unchanged)
    {
        .baseSpecies = SPECIES_GENGAR,
        .megaForm = MEGA_FORM_GENGAR,
        .requiredItem = ITEM_GENGARITE,
        .baseStats = {60, 65, 80, 170, 95, 130},
        .ability = ABILITY_SHADOW_TAG,
        .type1 = TYPE_GHOST,
        .type2 = TYPE_POISON,
    },
    // Mega Gardevoir
    // Base stats: 68 HP, 85 Atk, 65 Def, 165 SpAtk, 135 SpDef, 100 Speed
    // Ability: Trace (Pixilate not available in Gen 4)
    // Type: Psychic/Fairy
    {
        .baseSpecies = SPECIES_GARDEVOIR,
        .megaForm = MEGA_FORM_GARDEVOIR,
        .requiredItem = ITEM_GARDEVOIRITE,
        .baseStats = {68, 85, 65, 165, 135, 100},
        .ability = ABILITY_TRACE,
        .type1 = TYPE_PSYCHIC,
        .type2 = TYPE_FAIRY,
    },
    // Mega Alakazam
    // Base stats: 55 HP, 50 Atk, 65 Def, 175 SpAtk, 105 SpDef, 150 Speed
    // Ability: Trace
    // Type: Psychic (unchanged)
    {
        .baseSpecies = SPECIES_ALAKAZAM,
        .megaForm = MEGA_FORM_ALAKAZAM,
        .requiredItem = ITEM_ALAKAZITE,
        .baseStats = {55, 50, 65, 175, 105, 150},
        .ability = ABILITY_TRACE,
        .type1 = TYPE_PSYCHIC,
        .type2 = TYPE_PSYCHIC,
    },
    // Mega Gyarados
    // Base stats: 95 HP, 155 Atk, 109 Def, 70 SpAtk, 130 SpDef, 81 Speed
    // Ability: Mold Breaker
    // Type: Water/Dark
    {
        .baseSpecies = SPECIES_GYARADOS,
        .megaForm = MEGA_FORM_GYARADOS,
        .requiredItem = ITEM_GYARADOSITE,
        .baseStats = {95, 155, 109, 70, 130, 81},
        .ability = ABILITY_MOLD_BREAKER,
        .type1 = TYPE_WATER,
        .type2 = TYPE_DARK,
    },
    // Mega Scizor
    // Base stats: 70 HP, 150 Atk, 140 Def, 65 SpAtk, 100 SpDef, 75 Speed
    // Ability: Technician (unchanged)
    // Type: Bug/Steel (unchanged)
    {
        .baseSpecies = SPECIES_SCIZOR,
        .megaForm = MEGA_FORM_SCIZOR,
        .requiredItem = ITEM_SCIZORITE,
        .baseStats = {70, 150, 140, 65, 100, 75},
        .ability = ABILITY_TECHNICIAN,
        .type1 = TYPE_BUG,
        .type2 = TYPE_STEEL,
    },
};

// Size of the mega evolution table
const int sMegaEvolutionTableSize = 7;
