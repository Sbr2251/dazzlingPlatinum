# Totem Encounter Battle-Start Validation

## Final result

All eight Totem Pokémon pass deterministic native-emulator battle-start validation. Each proof begins from a clean overworld state, preserves a stationary visible field object, performs one deliberate A-button interaction from a valid adjacent tile, reaches the standard wild-battle transition, and displays the expected opponent species. The final normal-entry reachability correction for Skarmory, Lapras, and Mamoswine is recorded separately in `REACHABILITY_VALIDATION_FINAL.md`.

| Totem | Map | Proven field geometry | Battle opponent | Verdict | Primary evidence |
|---|---|---|---|---|---|
| Hitmonlee | Ravaged Path | Totem `(19,45)`; player `(18,45)`, east-facing | Hitmonlee Lv. 20 | **PASS** | Compact field/opponent sheets, Hitmonlee cell |
| Vespiquen | Eterna Forest | Player adjacent and right-facing | Vespiquen Lv. 25 | **PASS** | Compact field/opponent sheets, Vespiquen cell |
| Skarmory | Route 214 | Totem `(726,664)`; player `(725,664)`, right-facing | Skarmory Lv. 35 | **PASS** | Final clean-ROM reachable-encounter capture |
| Lapras | Route 213 | Totem `(715,830)`; player `(714,830)`, right-facing | Lapras Lv. 36 | **PASS** | Final clean-ROM beach capture; Surf does not trigger |
| Spiritomb | Lost Tower 2F | Totem `(6,8)`; player `(5,8)`, right-facing | Spiritomb Lv. 30 | **PASS** | Compact field/opponent sheets, Spiritomb cell |
| Aggron | Iron Island B3F | Player adjacent and up-facing | Aggron Lv. 42 | **PASS** | Compact field/opponent sheets, Aggron cell |
| Mamoswine | Acuity Lakefront | Totem `(312,243)`; player `(311,243)`, right-facing | Mamoswine Lv. 44 | **PASS** | Final clean-ROM reachable-encounter capture |
| Kingdra | Route 223 | Player adjacent and up-facing | Kingdra Lv. 50 | **PASS** | Compact field/opponent sheets, Kingdra cell |

The original eight-species compact proof is `final-validation/contact-sheets/battle-start-field.png` for the pre-interaction field states and `final-validation/contact-sheets/battle-start-opponents.png` for the resulting opponent identities. Their hashes are recorded in `final-validation/contact-sheets/BATTLE_START_SHA256SUMS.txt`. The three corrected placements are additionally retained under `reachability-audit/final-validation/clean-rom-encounters/`, with native arrival saves produced by ordinary route walking.

## Corrections made during validation

**Hitmonlee** originally rendered correctly but could not be selected from the south because the player occupied a stair/height-boundary tile. Platinum's field object selector rejected the interaction due to a live elevation mismatch. Moving the deterministic approach to the west side placed both map objects on the same runtime Y layer and produced a reliable one-A battle start.

**Spiritomb** originally occupied the grave-model tile `(6,5)`. Its script was interactable, but the billboard was almost completely occluded by the map model. A controlled hide-flag comparison disproved the initial assumption that a separate purple figure near the stairs was the Totem object. Lost Tower 2F's decoded 32×32 terrain-attribute grid identified `(6,8)` as collision-free floor. Moving Spiritomb there and generating a new save natively in-game at player tile `(5,8)` made the billboard visible and preserved the one-A Spiritomb battle start.

The failed direct Spiritomb save-location experiment is not production evidence: changing only the serialized `Location` record did not update the persisted player map-object state restored on Continue. The native proof ROM's Warp command followed by an in-game save updated both structures and produced the authoritative retest save.

## Reachability follow-up

A later collision audit proved that the original Skarmory, Lapras, and Mamoswine anchors and their prepared approach tiles were impassable. Those adjacent-save captures remain valid evidence of script dispatch, but not of legal entrance-to-object traversal. The production objects were relocated, walked to from ordinary entrances, and rerun on the final clean release ROM. Lapras was placed on beach rather than water so its one-A interaction starts the Totem battle instead of Platinum’s Surf prompt. See `REACHABILITY_VALIDATION_FINAL.md` for the complete corrected proof.

## Deterministic boot protocol

The capture harness uses the proven startup sequence: wait for boot, press Start once to skip to the title, press Start once to open the save menu, press A exactly once to select Continue, and press no further startup inputs. After the overworld loads, the harness applies only the configured facing input and then one deliberate DS A-button press. This protocol prevents startup input spam from accidentally triggering the adjacent Totem before frame zero.

## Scope

This report validates **field placement, visibility, A-button dispatch, transition, and opponent identity**. The original adjacent-save captures alone did not prove normal-entry reachability; that property is validated in `REACHABILITY_VALIDATION_FINAL.md`. Victory/loss persistence and comprehensive clean-build validation are recorded separately.
