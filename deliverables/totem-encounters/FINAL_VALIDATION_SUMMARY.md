# Totem Encounter Final Validation Summary

## Result

The eight planned Totem field encounters are implemented and pass deterministic native-emulator validation. Each stationary billboard is visible at its final location, one deliberate A-button press from the documented adjacent tile starts the intended battle, victory removes the encounter permanently, and a loss preserves it for another attempt.

A follow-up audit found that the original Skarmory, Lapras, and Mamoswine test saves had been forced onto impassable tiles. Those three placements have now been corrected and proven by continuous normal movement from ordinary map entrances before interaction. The reachability correction is documented in `REACHABILITY_VALIDATION_FINAL.md`.

| Totem | Map | Level | Battle start | Normal reachability | Victory persistence | Loss persistence |
|---|---|---:|---|---|---|---|
| Hitmonlee | Ravaged Path | 20 | **PASS** | **PASS** | **PASS** | **PASS** |
| Vespiquen | Eterna Forest | 25 | **PASS** | **PASS** | **PASS** | **PASS** |
| Skarmory | Route 214 | 35 | **PASS** | **PASS — live walked** | **PASS** | **PASS** |
| Lapras | Route 213 | 36 | **PASS** | **PASS — live walked** | **PASS** | **PASS** |
| Spiritomb | Lost Tower 2F | 30 | **PASS** | **PASS** | **PASS** | **PASS** |
| Aggron | Iron Island B3F | 42 | **PASS** | **PASS** | **PASS** | **PASS** |
| Mamoswine | Acuity Lakefront | 44 | **PASS** | **PASS — live walked** | **PASS** | **PASS** |
| Kingdra | Route 223 | 50 | **PASS** | **PASS** | **PASS** | **PASS** |

## Final placement corrections

| Totem | Final geometry | Correction and proof |
|---|---|---|
| Hitmonlee | Object `(19,45)`; player `(18,45)`, facing right | The prior south-side approach crossed a stair/elevation boundary. The west-side same-layer approach passes on the clean ROM. |
| Spiritomb | Object `(6,8)`; player `(5,8)`, facing right | Moved from a grave-model tile that visually occluded the billboard to decoded collision-free open floor. |
| Skarmory | Object `(726,664)`; player `(725,664)`, facing right | Moved from impassable trees to Route 214’s public path. The player reaches it from the ordinary north gate in 25 accepted movement inputs. |
| Lapras | Object `(715,830)`; player `(714,830)`, facing right | Moved from an unreachable island, then rejected a reachable water candidate because A invoked Surf. The final beach placement is reached from the Pastoria gate in 99 inputs and dispatches Lapras rather than Surf. |
| Mamoswine | Object `(312,243)`; player `(311,243)`, facing right | Moved from impassable scenery to open snow one accepted step east of Acuity Lakefront’s ordinary southern entry. |

The earlier adjacent-save captures proved script dispatch but did not establish entrance-to-object connectivity. For Skarmory, Lapras, and Mamoswine, the final standard now includes a fresh map entry, continuous legal player movement, a native in-game arrival save, visible adjacency, and one-A dispatch on the clean release ROM.

## One-time encounter contract

Every script checks the battle result before changing persistence state. A victory sets the species-specific defeated and hide flags, removes the live object immediately, and leaves it absent after a native save and full emulator restart. A blackout follows the standard healing sequence and leaves both flags clear.

| Persistence assertion | Result |
|---|---|
| Reserved flag IDs are exactly `0x0900–0x090F` | **PASS** |
| Victory sets defeated and hide flags | **PASS, 8/8** |
| Victory removes the object immediately | **PASS, 8/8** |
| Object remains absent after save and restart | **PASS, 8/8** |
| Loss reaches the standard blackout/healing flow | **PASS, 8/8** |
| Loss leaves defeated and hide flags clear | **PASS, 8/8** |
| Reachability-corrected species rerun on final clean ROM | **PASS, 3/3 victory and 3/3 loss** |
| Native post-battle saves pass Platinum checksum validation | **PASS, 16/16 original suite plus 6/6 corrected-species reruns** |

## Source and build validation

The independent source validator checks all eight event objects, script entry IDs, species, levels, story gates, exact reserved flag IDs, victory-only flagging, blackout branches, script archive registration, and map-header archive assignments. The authoritative encounter integrator remains byte-for-byte idempotent after the coordinate corrections.

| Validation | Result |
|---|---|
| Eight-species source validator | **PASS** |
| Exact-scope encounter integrator idempotency | **PASS** |
| Python and shell syntax checks | **PASS** |
| Collision and route-entry reachability audit | **PASS** |
| Native live-walk arrival assertions | **PASS, 3/3** |
| Clean `release` build | **PASS** |
| Final clean-ROM one-A tests for corrected species | **PASS, 3/3** |
| ROM size | `134,217,728` bytes |
| Final ROM SHA-256 | `ae5e0cf00ac2ddf1676b410831c118d60b0dc036a022df22dd33811576510787` |

The default decomp target’s vanilla-ROM checksum comparison is not applicable to a modified ROM. The modder-appropriate clean `release` target completed successfully.

## Retained evidence

The compact evidence package keeps reports and labeled screenshots while excluding copied ROMs, raw save files, temporary emulator state, and unrelated project work.

| Evidence | Repository path |
|---|---|
| Reachability correction and final verdict | `deliverables/totem-encounters/REACHABILITY_VALIDATION_FINAL.md` |
| Full reachability audit chronology | `deliverables/totem-encounters/reachability-audit/REACHABILITY_AUDIT_NOTES.md` |
| Final clean-ROM interaction review | `deliverables/totem-encounters/reachability-audit/final-validation/clean-rom-encounters/REVIEW.md` |
| Corrected live-walk arrival screenshots | `deliverables/totem-encounters/reachability-audit/post-relocation-live-walks/` and `final-validation/final-lapras-live-walk/` |
| Corrected clean-ROM persistence visual review | `deliverables/totem-encounters/reachability-audit/final-validation/clean-rom-contact-sheets/VISUAL_REVIEW.md` |
| Independent manual sheet review | `deliverables/totem-encounters/reachability-audit/final-validation/clean-rom-contact-sheets/MANUAL_REVIEW.md` |
| Clean-ROM persistence contact sheets | `deliverables/totem-encounters/reachability-audit/final-validation/clean-rom-contact-sheets/` |
| Eight-species battle-start report | `deliverables/totem-encounters/BATTLE_START_VALIDATION_FINAL.md` |
| Eight-species persistence audit | `deliverables/totem-encounters/persistence-validation/PERSISTENCE_AUDIT.md` |
| Clean release build metadata | `deliverables/totem-encounters/reachability-audit/final-validation/clean-release-build-summary.txt` |

> This validation covers field visibility, ordinary-player reachability, A-button dispatch, opponent identity, victory-only removal, loss retry behavior, native-save persistence, and clean-ROM compilation. Additional custom Totem battle mechanics beyond the standard `StartLegendaryBattle` encounter remain outside this implementation phase.
