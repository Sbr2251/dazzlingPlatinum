# Totem Reachability Validation — Final Correction

## Verdict

The original Skarmory, Lapras, and Mamoswine placements were **not reachable through normal gameplay**. Their Totem anchors and prepared player tiles all carried Platinum’s `0x8000` collision bit. The earlier adjacent-save emulator captures therefore proved encounter dispatch only; they did not prove that a player could legally walk to the interaction tile.

All three placements have now been relocated and independently revalidated from ordinary map entrances. The final proof uses continuous player movement, a native in-game save at the reached tile, one deliberate A-button press, and the full clean release ROM.

| Totem | Final object anchor | Live-reached approach | Ordinary entry | Accepted movement inputs | One-A battle |
|---|---:|---:|---:|---:|---|
| Skarmory | Route 214 `(726,664)` | `(725,664)`, facing right | North Veilstone gate `(718,646)` | 25 | **PASS** |
| Lapras | Route 213 beach `(715,830)` | `(714,830)`, facing right | Pastoria gate `(647,812)` | 99 | **PASS** |
| Mamoswine | Acuity Lakefront `(312,243)` | `(311,243)`, facing right | South entry `(310,243)` | 1 | **PASS** |

## Confirmed original defect

The collision audit decoded each original anchor and prepared approach from the map’s land-data terrain attributes. Every one was an impassable cell.

| Totem | Original anchor | Original prepared approach | Anchor attribute | Approach attribute | Verdict |
|---|---:|---:|---:|---:|---|
| Skarmory | `(714,660)` | `(715,660)` | `0x8000` | `0x8000` | Forced placement only |
| Lapras | `(695,850)` | `(695,851)` | `0x8000` | `0x8000` | Forced placement only |
| Mamoswine | `(315,240)` | `(315,241)` | `0x8000` | `0x8000` | Forced placement only |

> The user’s reachability concern was correct. Prepared saves had bypassed collision by beginning directly beside each object.

## Corrections

**Skarmory** now occupies the open Route 214 public path. A fresh map-entry save was required because Platinum restores persisted current-map object coordinates on Continue. From the ordinary north gate, the player walks to `(725,664)` and is stopped by Skarmory occupying `(726,664)`, providing direct runtime evidence that the object is instantiated on the connected path. Facing right and pressing A starts Skarmory Lv. 35.

**Lapras** first moved to reachable shoreline water at `(716,830)`, but pressing A from sand invoked Platinum’s Surf prompt before the object script. That candidate was rejected. Lapras now occupies the adjacent collision-free beach tile `(715,830)`. The player reaches `(714,830)` entirely on foot from the Pastoria-side gate; one A starts Lapras Lv. 36 rather than Surf.

**Mamoswine** now occupies an open snow tile immediately east of Acuity Lakefront’s ordinary southern entry. One accepted eastward step reaches `(311,243)`, visibly adjacent to Mamoswine at `(312,243)`. One A starts Mamoswine Lv. 44. The placement does not overlap the nearby sign, Barry event, coordinate trigger, rocks, or trees.

## Clean-ROM validation

A full clean `release` build was produced after the final coordinates were regenerated. The three native arrival saves reached through ordinary movement were then used against that exact clean ROM.

| Validation | Result |
|---|---|
| Clean release build | **PASS** |
| ROM size | `134,217,728` bytes |
| ROM SHA-256 | `ae5e0cf00ac2ddf1676b410831c118d60b0dc036a022df22dd33811576510787` |
| Skarmory, Lapras, and Mamoswine opponent identity | **PASS, 3/3** |
| Victory sets defeated and hide flags | **PASS, 3/3** |
| Victory removes the billboard immediately | **PASS, 3/3** |
| Billboard remains absent after native save and restart | **PASS, 3/3** |
| Blackout completes normally | **PASS, 3/3** |
| Blackout leaves defeated and hide flags clear | **PASS, 3/3** |
| Native post-battle save validation | **PASS, 6/6** |

## Retained evidence

| Evidence | Repository path |
|---|---|
| Full audit chronology and rejected candidates | `deliverables/totem-encounters/reachability-audit/REACHABILITY_AUDIT_NOTES.md` |
| Skarmory final walked arrival | `deliverables/totem-encounters/reachability-audit/post-relocation-live-walks/skarmory/01_arrival_before_save.png` |
| Lapras final walked arrival | `deliverables/totem-encounters/reachability-audit/final-validation/final-lapras-live-walk/01_arrival_before_save.png` |
| Mamoswine final walked arrival | `deliverables/totem-encounters/reachability-audit/post-relocation-live-walks/mamoswine/01_arrival_before_save.png` |
| Clean-ROM interaction review | `deliverables/totem-encounters/reachability-audit/final-validation/clean-rom-encounters/REVIEW.md` |
| Clean-ROM battle screenshots | `deliverables/totem-encounters/reachability-audit/final-validation/clean-rom-encounters/` |
| Clean-ROM persistence visual review | `deliverables/totem-encounters/reachability-audit/final-validation/clean-rom-contact-sheets/VISUAL_REVIEW.md` |
| Five labeled persistence contact sheets | `deliverables/totem-encounters/reachability-audit/final-validation/clean-rom-contact-sheets/` |
| Clean build metadata | `deliverables/totem-encounters/reachability-audit/final-validation/clean-release-build-summary.txt` |

## Scope correction

This report **supersedes the reachability implication** in the original adjacent-save battle-start report. The scripts and one-time persistence behavior were valid, but the first placement test did not establish a legal route from ordinary gameplay. The corrected standard is now: normal map entry, continuous accepted movement, native arrival save, visible adjacent object, one-A opponent dispatch, and clean-ROM persistence validation.
