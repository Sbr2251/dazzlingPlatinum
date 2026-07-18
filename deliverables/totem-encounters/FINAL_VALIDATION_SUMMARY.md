# Totem Encounter Final Validation Summary

## Result

The eight planned Totem field encounters are complete and pass deterministic native-emulator validation. Each stationary field billboard is visible at a valid location, one deliberate A-button press from the documented adjacent tile starts the intended wild battle, victory removes the encounter permanently, and a loss preserves the encounter for a future attempt.

| Totem | Map | Level | Battle start | Victory persistence | Loss persistence |
|---|---|---:|---|---|---|
| Hitmonlee | Ravaged Path | 20 | **PASS** | **PASS** | **PASS** |
| Vespiquen | Eterna Forest | 25 | **PASS** | **PASS** | **PASS** |
| Skarmory | Route 214 | 35 | **PASS** | **PASS** | **PASS** |
| Lapras | Route 213 | 36 | **PASS** | **PASS** | **PASS** |
| Spiritomb | Lost Tower 2F | 30 | **PASS** | **PASS** | **PASS** |
| Aggron | Iron Island B3F | 42 | **PASS** | **PASS** | **PASS** |
| Mamoswine | Acuity Lakefront | 44 | **PASS** | **PASS** | **PASS** |
| Kingdra | Route 223 | 50 | **PASS** | **PASS** | **PASS** |

## Corrections completed

**Hitmonlee** now uses the canonical Ravaged Path geometry with the Totem at `(19,45)` and the test/player approach at `(18,45)`, facing east. The earlier south-side approach crossed a stair and elevation boundary, so Platinum’s live field-object selector rejected the interaction despite the sprite rendering correctly. The west-side approach places the player and object on the same runtime layer and reliably starts the battle with one A press.

| Correction | Final behavior |
|---|---|
| Deterministic startup sequence | Two Start presses reach Continue; one menu A loads the field; no input spam can trigger an adjacent Totem prematurely. |
| Hitmonlee approach geometry | West-side, same-elevation interaction passes on the clean release ROM. |
| Spiritomb field placement | Moved from the occluded grave-model tile `(6,5)` to collision-free open floor `(6,8)`; native player approach is `(5,8)`, facing east. |
| Victory-test loadout | Replaced the incorrect move-ID assumption that resolved to non-damaging Sweet Kiss with always-hit Aerial Ace, eliminating the stalled Spiritomb/Lapras automation path. |

**Spiritomb** was interactable at its original grave tile, but the grave model almost completely occluded its billboard. A hide-flag A/B comparison and decoded Lost Tower terrain attributes isolated the issue. Its production object now occupies open aisle tile `(6,8)`, where the billboard is recognizable and remains fully interactable. The corrected native save proves the new geometry rather than relying on a raw coordinate patch that Platinum would reject when restoring persisted player map-object state.

## One-time encounter contract

Every script checks the battle result before changing persistence state. A victory sets the species-specific defeated and hide flags, removes the live object immediately, and leaves it absent after a native save and full emulator restart. A blackout executes the loss branch first, returns the player through the standard Pokémon Center sequence, and leaves both flags clear.

| Persistence assertion | Result |
|---|---|
| Reserved flag IDs are exactly `0x0900–0x090F` | **PASS** |
| Victory sets defeated and hide flags | **PASS, 8/8** |
| Victory removes the object immediately | **PASS, 8/8** |
| Object remains absent after save and restart | **PASS, 8/8** |
| Loss reaches the standard blackout/healing flow | **PASS, 8/8** |
| Loss leaves defeated and hide flags clear | **PASS, 8/8** |
| Native post-battle saves pass Platinum checksum validation | **PASS, 16/16** |

## Source and build validation

The independent source validator checks all eight event objects, script entry IDs, species, levels, story gates, exact reserved flag IDs, victory-only flagging, blackout branches, script archive registration, and map-header archive assignments. The authoritative encounter integrator is byte-for-byte idempotent across its exact 20 runtime outputs.

| Validation | Result |
|---|---|
| Eight-species source validator | **PASS** |
| Exact-scope integrator idempotency | **PASS** |
| Python and shell syntax checks | **PASS** |
| Clean `release` build | **PASS** |
| Immediate no-change rebuild | **PASS; hash stable** |
| Final clean-ROM Hitmonlee one-A smoke test | **PASS** |
| ROM size | `134,217,728` bytes |
| ROM SHA-256 | `38685cb82565db9e826faeb595a106748620181a96c224aa863c7e7f9d049d5b` |

The default decomp target’s vanilla-ROM checksum comparison is not applicable to a modified ROM. The modder-appropriate clean `release` target completed successfully and produced the stable hash above.

## Retained evidence

The compact evidence package keeps reports and labeled contact sheets while excluding copied ROMs, raw save files, temporary worker archives, emulator logs, and unrelated project work.

| Evidence | Repository path |
|---|---|
| Eight-species battle-start report | `deliverables/totem-encounters/BATTLE_START_VALIDATION_FINAL.md` |
| Pre-interaction field contact sheet | `deliverables/totem-encounters/final-validation/contact-sheets/battle-start-field.png` |
| Confirmed opponent contact sheet | `deliverables/totem-encounters/final-validation/contact-sheets/battle-start-opponents.png` |
| Eight-species persistence audit | `deliverables/totem-encounters/persistence-validation/PERSISTENCE_AUDIT.md` |
| Persistence visual review | `deliverables/totem-encounters/persistence-validation/contact-sheets/VISUAL_REVIEW.md` |
| Five persistence contact sheets | `deliverables/totem-encounters/persistence-validation/contact-sheets/` |
| Clean release build summary | `deliverables/totem-encounters/final-validation/clean-release-build-summary.txt` |
| Exact integrator idempotency summary | `deliverables/totem-encounters/final-validation/exact-integrator-idempotency-summary.txt` |

> This validation covers field placement, visibility, A-button dispatch, intended opponent identity, victory-only one-time removal, loss retry behavior, native-save persistence, and clean-ROM compilation. Additional custom Totem battle mechanics beyond the standard `StartLegendaryBattle` encounter remain outside this implementation phase.
