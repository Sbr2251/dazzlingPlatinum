# Totem-Gated HM Progression Validation Report

## Result

Field use of each progression HM now requires **both** its existing Gym Badge and the corresponding Totem-defeated flag. The Badge check remains first, preserving the original missing-Badge response; a player who owns the Badge but has not defeated the relevant Totem receives the new message:

> This can't be used until the area's Totem has been defeated.

Flash, Teleport, Dig, Sweet Scent, Chatter, and all pre-existing location, partner, Safari Zone, Pal Park, and movement-state restrictions remain unchanged.

## Progression Pairings

| Field HM | Required Gym Badge | Required Totem flag |
|---|---|---|
| Rock Smash | Coal Badge | Hitmonlee defeated |
| Cut | Forest Badge | Vespiquen defeated |
| Defog | Relic Badge | Spiritomb defeated |
| Fly | Cobble Badge | Skarmory defeated |
| Surf | Fen Badge | Lapras defeated |
| Strength | Mine Badge | Aggron defeated |
| Rock Climb | Icicle Badge | Mamoswine defeated |
| Waterfall | Beacon Badge | Kingdra defeated |

The shared progression helper returns the original Badge error when the Badge is absent, the new Totem error when the Badge is owned but the Totem flag is absent, and success only when both conditions are true.

## Deterministic Validation

The host-side progression validator checks the helper's control-flow order, all eight exact and unique mappings, all four logical states for every HM, every flag producer, and the player-facing error route. This covers **32 state combinations**: neither prerequisite, Badge only, Totem only, and both prerequisites for each of the eight HMs.

| Validation suite | Result |
|---|---:|
| Totem HM progression contracts | 5/5 passed |
| Totem Battle Mode contracts, including fixture regression checks | 11/11 passed |
| Python compilation | Passed |
| JSON text-bank parsing and generated message constant | Passed |
| Repository whitespace check | Passed |

## Clean ROM Build

A ROM-only release build was performed after deleting the entire `build` directory. Compilation, linking, generated headers, and the party-menu text archive completed without errors.

| Artifact | Value |
|---|---|
| ROM | `build/pokeplatinum.us.nds` |
| Size | `134217728` bytes |
| SHA-256 | `5b5771862c69cf20bef009107eea1dd91a81c65189cba8c55c78b3556d02fa0f` |

## Live Emulator Validation

Fly was selected as the representative live test because it reaches a visually unambiguous Town Map on success. Two checksum-valid native Platinum saves were generated from the same Skarmory-adjacent source save. Both saves gave the lead Pokémon Fly and the Cobble Badge; only the second save set `FLAG_TOTEM_SKARMORY_DEFEATED`.

| Fixture state | Observed result |
|---|---|
| Cobble Badge present; Skarmory undefeated | Fly was rejected with the dedicated Totem requirement message. |
| Cobble Badge present; Skarmory defeated | Fly opened the destination-selection Town Map. |

The final screenshot sheet was captured from the exact clean-built ROM listed above. Its SHA-256 is `2c3fcacec94f173b2243519588cbcd83d367f9cfcd296d3f94b894834b9d91e6`.

## Test-Fixture Regression Correction

Live validation exposed two stale assumptions in the deterministic Totem save builder. First, the defeated and hide flags are ordered in the generated flag table as Hitmonlee, Vespiquen, Skarmory, Lapras, Spiritomb, Aggron, Mamoswine, and Kingdra rather than encounter-table order. Second, the serialized flag bit array begins at general-block offset `0x0FEC`, derived from the proven `VarsFlags` entry at `0x0DAC` plus `0x120` two-byte variables.

The builder now uses explicit generated defeated/hide flag pairs and the correct `0x0FEC` default. The Totem validator independently derives both contracts and will fail if either mapping or offset regresses.

## Reproduction Commands

```bash
python3 tools/validate_totem_battle_mode.py .
python3 tools/validate_totem_hm_progression.py --root .
rm -rf build
make -j"$(nproc)" rom
```
