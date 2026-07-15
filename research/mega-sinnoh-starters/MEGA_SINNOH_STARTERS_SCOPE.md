# Mega Sinnoh Starters Implementation Scope

This document outlines a proposed implementation scope for introducing Mega Torterra, Mega Infernape, and Mega Empoleon into the Pokémon Dazzling Platinum decompilation environment. It covers design direction, typing, abilities, and stat allocations based on the standard +100 Mega Evolution budget, along with verifiable fan-concept visual references.

## Visual Reference Directions

Because no official Mega forms exist for the Sinnoh starters, their designs must be sourced from fan concepts or created originally. The following verifiable fan concepts serve as strong visual and thematic starting points. The images are archived in `research/mega-sinnoh-starters/references/`.

*   **Tomycase Concept** ([Source](https://www.reddit.com/r/pokemon/comments/39b1u6/mega_sinnoh_starters_by_tomycase/))
    *   **Torterra**: A heavier, fortress-like shell with a dense, mountainous terrain and thicker, darker bark. Emphasizes slow, impregnable bulk.
    *   **Infernape**: A wilder flame mane, extended arm-bands, and sharper gold accents.
    *   **Empoleon**: A streamlined, fully armored "emperor" silhouette with exaggerated, blade-like wings.
*   **Rocketmanga Concept** ([Source](https://www.deviantart.com/rocketmanga/art/ALL-SINNOH-STARTERS-MEGA-EVOLUTION-FANART-875079181))
    *   Provides alternative silhouettes, particularly for Infernape (more white fur and distinct flame shaping) and Empoleon (heavier gold armor plating).
*   **VilliamBoom Concept** ([Source](https://x.com/VilliamBoom1/status/1379069620087312386))
    *   **Torterra**: Features geological armor and a massive, ancient tree.
    *   **Infernape**: Incorporates Sun Wukong elements like cloud motifs and rings.
    *   **Empoleon**: Adds a regal cape silhouette and a distinct trident crown.

## Mega Torterra

Mega Torterra leans into its "Continent Pokémon" identity, transforming its shell into an impenetrable mountain fortress.

| Attribute | Base Form | Mega Form | Change |
| :--- | :--- | :--- | :--- |
| **Type** | Grass / Ground | Grass / Ground | No change |
| **Ability** | Overgrow / Shell Armor | **Thick Fat** | Mitigates severe Fire/Ice weaknesses |
| **HP** | 95 | 95 | +0 |
| **Attack** | 109 | 149 | +40 |
| **Defense** | 105 | 145 | +40 |
| **Sp. Atk** | 75 | 85 | +10 |
| **Sp. Def** | 85 | 115 | +30 |
| **Speed** | 56 | 36 | -20 |
| **Total** | **525** | **625** | **+100** |

**Design & Mechanics:** By sacrificing Speed (making it a premier Trick Room candidate), Mega Torterra heavily bolsters its Attack and both defensive stats. Thick Fat is a highly synergistic ability, neutralizing its 4x Ice weakness to 2x and its 2x Fire weakness to neutral, allowing it to survive hits and retaliate with devastating Wood Hammers and Earthquakes.

## Mega Infernape

Mega Infernape embraces the "Monkey King" (Sun Wukong) martial arts aesthetic, turning its flames into focused, blindingly fast strikes.

| Attribute | Base Form | Mega Form | Change |
| :--- | :--- | :--- | :--- |
| **Type** | Fire / Fighting | Fire / Fighting | No change |
| **Ability** | Blaze / Iron Fist | **Adaptability** | Drastically boosts dual-STAB offensive power |
| **HP** | 76 | 76 | +0 |
| **Attack** | 104 | 134 | +30 |
| **Defense** | 71 | 81 | +10 |
| **Sp. Atk** | 104 | 134 | +30 |
| **Sp. Def** | 71 | 81 | +10 |
| **Speed** | 108 | 128 | +20 |
| **Total** | **534** | **634** | **+100** |

**Design & Mechanics:** Infernape retains its mixed-attacker identity but becomes significantly faster and more lethal. Adaptability increases its STAB modifier from 1.5x to 2.0x, making Flare Blitz and Close Combat exceptionally dangerous without requiring the setup turns that a pure stat-boosting ability might demand. The +100 budget is split evenly across offenses, with a necessary bump to Speed to outpace other Megas.

## Mega Empoleon

Mega Empoleon adopts a heavily armored, regal "Emperor" design, with its steel wings becoming true, cleaving blades.

| Attribute | Base Form | Mega Form | Change |
| :--- | :--- | :--- | :--- |
| **Type** | Water / Steel | Water / Steel | No change |
| **Ability** | Torrent / Defiant | **Filter** | Reduces super-effective damage (Fighting/Ground/Electric) |
| **HP** | 84 | 84 | +0 |
| **Attack** | 86 | 106 | +20 |
| **Defense** | 88 | 118 | +30 |
| **Sp. Atk** | 111 | 141 | +30 |
| **Sp. Def** | 101 | 121 | +20 |
| **Speed** | 60 | 60 | +0 |
| **Total** | **530** | **630** | **+100** |

**Design & Mechanics:** Empoleon already possesses an incredible defensive typing (Water/Steel). Mega Empoleon doubles down on this by gaining Filter, which reduces the damage of super-effective hits by 25%, allowing it to comfortably tank Earthquakes and Close Combats. Its stat boosts focus on Special Attack and Defense, cementing its role as a bulky special attacker that is extremely difficult to remove from the field.

## Required Implementation Areas

If this scope is approved for implementation, the following areas in the `dazzlingPlatinum` decompilation must be modified:

1.  **Species Definitions (`include/constants/species.h`)**: Define `SPECIES_MEGA_TORTERRA`, `SPECIES_MEGA_INFERNAPE`, and `SPECIES_MEGA_EMPOLEON`.
2.  **Base Stats (`src/data/pokemon/base_stats.h`)**: Implement the new 625/634/630 stat spreads, abilities (Thick Fat, Adaptability, Filter), and type assignments.
3.  **Item Definitions (`include/constants/items.h`)**: Add `ITEM_TORTERRITE`, `ITEM_INFERNAPITE`, and `ITEM_EMPOLEONITE`.
4.  **Mega Evolution Tables (`src/pokemon_mega_evolution.c` or equivalent)**: Map the base species to the Mega species using the correct Mega Stones.
5.  **Sprite and Palette Assets (`res/pokemon/`)**: Inject the new front/back sprites and normal/shiny palettes.
6.  **Cry Routing (`src/sound_playback.c` & `res/sound/`)**: Assign or duplicate appropriate wave archives for the new forms.


## Additional Sprite-Production References

The implementation asset search identified public sprite and concept references for silhouette and animation-layout study. These remain **references only**; the production sprites will be newly prepared for this project and fitted to Platinum’s native format.

- **Anarlaurendil, “Mega Torterra — full sprite set”** — DeviantArt source surfaced by image search; useful for front/back and overworld-view conventions.
- **StefanTeleporter, “Mega Infernape Sprite”** — DeviantArt source surfaced by image search; useful for DS-era pixel-scale anatomy.
- **Pokémon-Subrosia, “Mega Evolution Back Sprites in 160x160”** — DeviantArt source surfaced by image search; useful for general back-view framing rather than the approved species designs.
- **VilliamBoom Sinnoh Mega concept set** — https://x.com/VilliamBoom1/status/1379069620087312386; secondary anatomy reference while Rocketmanga remains the approved Torterra/Empoleon direction.
- **Approved Omni-Master Mega Infernape concept** — supplied directly by the user and preserved at `research/mega-sinnoh-starters/references/approved_mega_infernape_flame_staff.jpeg`.
