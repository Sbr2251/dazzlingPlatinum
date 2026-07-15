# Mega Sinnoh Starter Validation Report

**Branch:** `ManusAgentMegaSinnohStarters`

**Scope:** Mega Torterra, Mega Infernape, and Mega Empoleon
**Validation status:** **Passed for source integration, native sprite format, archive packaging, clean ROM compilation, and six-view emulator rendering**

![Indexed in-game asset preview](https://private-us-east-1.manuscdn.com/sessionFile/XfTWq4JocjJtvgXUyppjvp/sandbox/Vkvmb0ZmAcg3E1dCUz86yo-images_1784085600796_na1fn_L2hvbWUvdWJ1bnR1L2RhenpsaW5nUGxhdGludW0vcmVzZWFyY2gvbWVnYS1zaW5ub2gtc3RhcnRlcnMvbWVnYV9zaW5ub2hfaW5nYW1lX2Fzc2V0X3ByZXZpZXc.png?Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9wcml2YXRlLXVzLWVhc3QtMS5tYW51c2Nkbi5jb20vc2Vzc2lvbkZpbGUvWGZUV3E0Sm9jakp0dmdYVXlwcGp2cC9zYW5kYm94L1Zrdm1iMFptQWNnM0UxZENVejg2eW8taW1hZ2VzXzE3ODQwODU2MDA3OTZfbmExZm5fTDJodmJXVXZkV0oxYm5SMUwyUmhlbnBzYVc1blVHeGhkR2x1ZFcwdmNtVnpaV0Z5WTJndmJXVm5ZUzF6YVc1dWIyZ3RjM1JoY25SbGNuTXZiV1ZuWVY5emFXNXViMmhmYVc1bllXMWxYMkZ6YzJWMFgzQnlaWFpwWlhjLnBuZyIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc4NTU0MjQwMH19fV19&Key-Pair-Id=K2QY5QTL8JSY6C&Signature=MEYCIQC0E8cT5N14ublMreOhC0J4GDHToksI6-eoOnISVs8dNwIhAIQiM8gBkLdvco9WIWdmZoll6S~7EQ3b5teFdQJ-p-Ey)

![Emulator-rendered front and back views](https://private-us-east-1.manuscdn.com/sessionFile/XfTWq4JocjJtvgXUyppjvp/sandbox/Vkvmb0ZmAcg3E1dCUz86yo-images_1784085600796_na1fn_L2hvbWUvdWJ1bnR1L2RhenpsaW5nUGxhdGludW0vcmVzZWFyY2gvbWVnYS1zaW5ub2gtc3RhcnRlcnMvZW11bGF0b3IvbWVnYV9zaW5ub2hfZW11bGF0b3JfY29udGFjdF9zaGVldA.png?Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9wcml2YXRlLXVzLWVhc3QtMS5tYW51c2Nkbi5jb20vc2Vzc2lvbkZpbGUvWGZUV3E0Sm9jakp0dmdYVXlwcGp2cC9zYW5kYm94L1Zrdm1iMFptQWNnM0UxZENVejg2eW8taW1hZ2VzXzE3ODQwODU2MDA3OTZfbmExZm5fTDJodmJXVXZkV0oxYm5SMUwyUmhlbnBzYVc1blVHeGhkR2x1ZFcwdmNtVnpaV0Z5WTJndmJXVm5ZUzF6YVc1dWIyZ3RjM1JoY25SbGNuTXZaVzExYkdGMGIzSXZiV1ZuWVY5emFXNXViMmhmWlcxMWJHRjBiM0pmWTI5dWRHRmpkRjl6YUdWbGRBLnBuZyIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc4NTU0MjQwMH19fV19&Key-Pair-Id=K2QY5QTL8JSY6C&Signature=MEUCIDciThlRFPau4y5-B2LohZl-gsMKFCZa74J03wNsUyeAAiEArACPIeJXRcee2dXjDbrEyyhrBblmbQSs-rqNDA2nyMM_)

## Summary

The three Sinnoh starter Mega Evolutions are integrated as native Platinum battle resources with two front frames, two back frames, normal and shiny palettes, Mega Evolution data, reusable Mega Stone item slots, and Route 206 test pickups. The approved mechanics use abilities already present in the project—**Thick Fat**, **Adaptability**, and **Filter**—so this branch does not add or modify the global ability enum or battle ability handlers.

| Mega Evolution | Type | Ability | Base BST | Mega BST | Increase | Stone ID |
|---|---|---:|---:|---:|---:|---:|
| Mega Torterra | Grass / Ground | Thick Fat | 525 | 625 | +100 | Torterrite, item 120 |
| Mega Infernape | Fire / Fighting | Adaptability | 534 | 634 | +100 | Infernapite, item 121 |
| Mega Empoleon | Water / Steel | Filter | 530 | 630 | +100 | Empoleonite, item 122 |

## Visual Design Review

The indexed preview was reviewed at enlarged nearest-neighbor scale after conversion to the actual 16-color game assets. Each front/back pair retains the same core design language, and the back frames are genuine player-side views rather than mirrored or duplicated front views.

| Species | Front-view assessment | Back-view assessment | Result |
|---|---|---|---|
| Mega Torterra | The ancient world-tree canopy, reinforced stone shell, forward head, and heavy quadrupedal silhouette remain legible at DS scale. The two front frames preserve design identity while producing a subtle battle-idle change. | The player-side view exposes the rear shell, tail, hind legs, trunk structure, and canopy from behind. It is compositionally distinct from the front pose and reads as the same creature. | Pass |
| Mega Infernape | The Omni-Master concept reads through the dark body, high flame crown, bright shoulder flames, and diagonal flame staff. The staff and crown provide a strong, recognizable silhouette. | The rear view correctly reverses the body read, shows the back of the head and shoulders, and keeps the flame staff crossing the pose consistently. Both frames remain recognizable without relying on facial details. | Pass |
| Mega Empoleon | The armored-emperor design reads through the gold crown structure, navy-and-gold wing shields, pale blue body, and tall icy plume. The stance is centered and authoritative. | The rear view exposes the dark mantle, shield-like wing backs, rear crown/plume structure, and feet. It clearly differs from the front while preserving the same armor geometry. | Pass |

## Native Sprite Validation

The command `python3 tools/validate_mega_sinnoh_sprites.py` validates the committed assets directly. All six sprite sheets passed the following requirements:

| Requirement | Expected | Observed |
|---|---:|---:|
| Sheet dimensions | 160 × 80 pixels | 160 × 80 for all six sheets |
| Animation layout | Two 80 × 80 frames | Two frames for every front/back sheet |
| Image mode | Indexed palette (`P`) | Indexed palette for all sheets |
| Palette range | Indices 0–15 | Exactly 16 used indices, maximum 15 |
| Key sidecars | Four bytes each | Four bytes for every `.png.key` |
| Lateral/top clipping | None | No frame touches left, top, or right edge |
| Transparent background | Palette index 0 | Present in every sheet |

| Species | View | Frame 1 occupied bounds | Frame 2 occupied bounds |
|---|---|---|---|
| Torterra | Front | `(3, 4, 76, 78)` | `(3, 4, 75, 78)` |
| Torterra | Back | `(7, 8, 73, 79)` | `(7, 8, 73, 79)` |
| Infernape | Front | `(4, 4, 75, 78)` | `(2, 4, 77, 78)` |
| Infernape | Back | `(2, 6, 78, 79)` | `(2, 7, 78, 79)` |
| Empoleon | Front | `(8, 3, 72, 78)` | `(8, 3, 72, 78)` |
| Empoleon | Back | `(8, 4, 72, 79)` | `(8, 4, 71, 79)` |

## Mechanics and Resource Validation

The command `python3 tools/validate_mega_sinnoh_integration.py` validates the Mega table entries against the base-species JSON, verifies the +100 BST rule, confirms that all abilities and types already exist, checks item IDs, confirms form constants, verifies sprite/palette routing, and checks Route 206 event/script wiring.

| Species | Sprite indices, back/front | Palette indices, normal/shiny | Route 206 script | Pickup flag |
|---|---:|---:|---:|---|
| Torterra | 276 / 277 | 282 / 283 | 7335 | `FLAG_UNK_0x0543` |
| Infernape | 278 / 279 | 284 / 285 | 7336 | `FLAG_UNK_0x0544` |
| Empoleon | 280 / 281 | 286 / 287 | 7337 | `FLAG_UNK_0x0545` |

The `pl_otherpoke` builder was generalized to select the NCGR or NCLR conversion path from each input file’s extension. This permits new sprite entries to be appended after the canonical palette block without renumbering any existing resources. Extracting the rebuilt archive produced **293 files**: the original 276 core entries, 12 appended Mega starter entries, and five shared substitute/shadow entries. Entries 276–281 have NCGR signatures, while entries 282–287 have NCLR signatures.

## Build Validation

A clean build was executed with `make clean` followed by `make -j2`. Compilation and linking reached **1491/1491**, and the build generated `build/pokeplatinum.us.nds` with the expected 134,217,728-byte ROM size. The resulting ROM SHA-256 is:

```text
4d23cd9388fe38b6fdc425dcfd9fd85f547ff90a9490f81fa77cc1fdefb8aa69
```

The post-build vanilla checksum suite reports four checksum mismatches. This is expected for this ROM hack because source, resource archives, filesystem data, and the final ROM intentionally differ from the unmodified Pokémon Platinum reference checksums. There were no compiler, linker, resource-generation, JSON-validation, sprite-format, or integration-validation failures.

## Emulator Rendering Validation

The same deterministic Rowan-intro rendering workflow previously used for Mega Hydreigon was applied to all three Sinnoh starter Megas. A temporary local-only harness supplied each species, Mega form ID, and `FACE_FRONT` or `FACE_BACK` to the production `BuildPokemonSpriteTemplate` resource path. Six ROM variants were booted in DeSmuME, advanced through the same fixed input and frame schedule, and captured at the fully revealed sprite frame. The harness was then restored completely before the production ROM rebuild.

| Species | Front / opponent-view result | Back / player-view result | Result |
|---|---|---|---|
| Mega Torterra | The tree canopy, pale armor, rocky shell, and foreground foliage render with the intended palette and remain within the DS sprite area. | The rear view is compositionally distinct, emphasizes the canopy and rear shell mass, and loads without clipping or palette corruption. | Pass |
| Mega Infernape | The dark body and orange/yellow flame staff retain strong contrast and a readable Omni-Master silhouette. | The rear pose and diagonal staff remain distinct and fully contained, with consistent flame and body colors. | Pass |
| Mega Empoleon | The crown, pale plume, navy mantle, gold trim, and wing shields remain readable at native runtime scale. | The rear mantle and wing-shield geometry clearly distinguish the player-side view and render without archive artifacts. | Pass |

All six captures are stored under `research/mega-sinnoh-starters/emulator/`. The Rowan intro positions its human and Pokémon sprites closer together than a battle scene, so wide sprites overlap Professor Rowan in these evidence frames; this is expected from the validation layout and is not sprite clipping. No visual defect requiring an asset correction was found.

## Remaining Gameplay Checks

The emulator pass verifies production resource lookup, decompression, palette loading, front/back selection, transparency, runtime scale, and placement through the game engine. A normal gameplay test is still recommended before pushing to verify Mega Evolution activation, held-stone behavior, assigned abilities, Route 206 pickups, and final battle-scene coordinates. The branch remains local and unpushed for that user-facing test.
