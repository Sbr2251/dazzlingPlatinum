# Totem Reachability Audit Notes

## Scope correction

The prior one-A emulator captures began from prepared saves already at each encounter. They prove field interaction and opponent dispatch, but they do **not** by themselves prove that normal gameplay can reach the interaction tile from a map entrance. Reachability is therefore being audited independently.

| Totem | Preliminary full-resolution observation | Status before traversal audit |
|---|---|---|
| Lapras | The encounter is on a small raised rocky island surrounded by water. The frame proves the prepared save can occupy the encounter area, but not that a player can enter it through normal map movement. Surf/shore connectivity and the island collision graph must be checked. | **Unproven** |
| Skarmory | The billboard’s visible pixels appear over dense trees while the player stands on the eastern Route 214 path. This may be a genuinely unreachable object tile or a billboard-origin offset whose logical anchor is on the path; object coordinates, opaque-pixel offset, collision, and live traversal must be correlated. | **Unproven** |
| Mamoswine | The prepared player appears on the narrow upper Acuity Lakefront route beside snow-covered tree/boulder models, while the Totem billboard is not readily distinguishable. The logical anchor may be inside or visually occluded by that model cluster; collision and entrance connectivity must be checked. | **Unproven** |

No placement will be accepted solely because a prepared adjacent save can press A. The final criterion is a continuous legal route from an ordinary entrance to an adjacent interaction tile, followed by the same one-A battle proof.

## Static collision verdict

The concern is confirmed for all three original placements. Each Totem anchor and each prepared approach save were placed on cells whose terrain attribute has the `0x8000` collision bit set.

| Totem | Original anchor | Prepared approach | Anchor value | Approach value | Static verdict |
|---|---:|---:|---:|---:|---|
| Skarmory | `(714,660)` | `(715,660)` | `0x8000` | `0x8000` | Unreachable without forced placement |
| Lapras | `(695,850)` | `(695,851)` | `0x8000` | `0x8000` | Unreachable without forced placement |
| Mamoswine | `(315,240)` | `(315,241)` | `0x8000` | `0x8000` | Unreachable without forced placement |

The route-entry collision graphs found the following replacement candidates. These are **candidates only** until the player traverses to them in the emulator.

| Totem | Proposed anchor | Proposed approach | Facing | Terrain rationale |
|---|---:|---:|---|---|
| Skarmory | `(726,664)` | `(727,664)` | Left | Both cells are collision-free Route 214 path (`0x0000`) in the entry-connected component, with an open billboard footprint. |
| Lapras | `(716,830)` | `(715,830)` | Right | Lapras occupies collision-free sea (`0x0015`) directly beside entry-connected Route 213 sand (`0x0021`), allowing shore interaction without Surf. |
| Mamoswine | `(335,244)` | `(334,244)` | Right | Both cells are collision-free Acuity Lakefront snow/grass (`0x0002`) in a broad entry-connected snowfield. |

Static evidence is retained in `*-static-reachability.txt` and `*-candidate-region.txt` within this directory.

## Live traversal — candidate validation

### Skarmory

The native entry save loaded at Route 214’s ordinary Veilstone gate exit `(718,646)`. A continuous 27-tile input path (`Down:18,Right:9`) reached `(727,664)` without warping, save editing, clipping, or collision bypass. The native post-walk save reports Route 214 at exactly `(727,664)`. The arrival frame shows a broad public-path clearing with open space for the billboard at proposed anchor `(726,664)`. **Candidate traversal pass.**

### Lapras

The native entry save loaded at Route 213’s ordinary Pastoria gate exit `(647,812)`. A continuous 100-tile on-foot path reached sand tile `(715,830)` without Surf, warping, save editing, clipping, or collision bypass. The native post-walk save reports Route 213 at exactly `(715,830)`. The arrival frame shows the player at the unobstructed eastern edge of a broad beach with collision-free sea immediately at proposed Lapras anchor `(716,830)`. **Candidate traversal pass.**

### Mamoswine — first live-path attempt

The initial attribute-only route (`Up:1,Right:8,Up:1,...`) did **not** reach the proposed snowfield. The player reached approximately `(319,245)` and the attempted northward shortcut beside the rock merely changed facing without advancing; subsequent right inputs remained blocked. The two adjacent visual checkpoints are effectively position-identical. This demonstrates that the 32×32 terrain attribute grid alone does not encode every obstruction or directional edge in Acuity Lakefront’s BDHC collision/model geometry. The failed route is rejected; Mamoswine requires a route proven by live movement around the visible path rather than by attribute flood-fill alone.

The ordinary Acuity Lakefront entry frame shows a traversable snow corridor and several open patches immediately around the player, whereas the rejected destination lies past visually dense rock/tree geometry. The failed end frame confirms that repeated inputs can leave the player in a narrow obstructed corridor despite apparently passable attribute cells. The correction will therefore favor a **near-entry open snow patch** and require an exact native-save arrival proof before placing Mamoswine.

### Mamoswine — corrected candidate

A second live probe used only one ordinary eastward movement from the native Acuity Lakefront entry save. It reached `(311,243)` exactly, and a normal in-game save recorded that position in the active partition. The frame shows an open snow patch immediately east of the entrance with no event object at proposed anchor `(312,243)`; existing nearby records are the arrow sign at `(309,242)`, Barry at `(310,237)`, a coordinate event on `(310..311,244)`, and the old unreachable Totem at `(315,240)`. Proposed corrected geometry is therefore **Mamoswine `(312,243)`, player approach `(311,243)`, facing right**. **Candidate traversal pass.**

### Rebuilt-ROM encounter retest — Skarmory first attempt

The native arrival save is at `(727,664)`, but its active saved facing is `3` (right), inherited from the final eastward movement. Because Skarmory’s anchor is west at `(726,664)`, the first `Stay` capture faced away from the object; `04_battle_started.png` is therefore still the field and **is not a valid interaction result**. This is a harness-input error, not an encounter-script verdict. The rerun must explicitly use `FaceLeft`. The frame also shows that the visible billboard art is displaced toward the upper-left relative to the object anchor, so visual-to-interaction alignment must be reviewed independently rather than accepting coordinate connectivity alone.

The corrected `FaceLeft` rerun still remained in the overworld at the final checkpoint. Thus `(726,664)` is reachable as terrain, but the object is **not interactable from `(727,664)` with its current event `y=0`**. The likely remaining variable is Route 214’s event elevation/layer at this public-path candidate; static X/Z connectivity alone is insufficient. This candidate is rejected unless its proper event elevation can be proved and the one-A battle passes.

### Stale same-map save diagnosis

The visible Skarmory in the failed rebuilt-ROM frame is approximately 13 tiles west and 4 tiles north of the player—exactly the **old** anchor `(714,660)` relative to the native arrival save at `(727,664)`. Platinum persists current-map object state in the save, so a Continue from the pre-relocation Route 214 save restores Skarmory’s old object coordinates instead of instantiating the rebuilt event record at `(726,664)`. This explains both observations: the new event JSON is compiled correctly, yet pressing A at the new tile finds no object. The retest must regenerate route-entry saves under the rebuilt ROM (or enter from a different map) and repeat the live walk; pre-relocation same-map saves are invalid for post-relocation placement testing.

### Fresh post-relocation map-state test — Skarmory

After regenerating the Route 214 entry save under the corrected ROM, the same ordinary-entry movement sequence no longer reached the old expected far-side tile `(727,664)`. It stopped at `(725,664)` facing right because the newly instantiated Skarmory object at `(726,664)` occupied the next tile. This is positive runtime evidence that the corrected object is present on the connected public path. The valid interaction geometry is therefore player `(725,664)` facing right toward object `(726,664)`, not the previously planned east-side approach. The deterministic location-save definition and final walk assertion must use the west-side coordinate.

### Fresh-map live-walk visual review

- **Skarmory:** The post-relocation Route 214 arrival frame visibly shows Skarmory centered on the open public path with the player immediately west of it after 25 ordinary movement inputs from the north gate exit. The billboard is neither inside the tree line nor separated by a ledge.
- **Lapras:** The post-relocation Route 213 arrival frame visibly shows Lapras in the water immediately east of the player’s reachable sand shoreline tile after 100 ordinary movement inputs from the Pastoria-side gate exit. The player does not need to occupy a collision tile or approach through scenery.
- **Mamoswine:** The post-relocation Acuity Lakefront arrival frame visibly shows the billboard on open snow immediately east of the player after one ordinary movement input from the southern entry. Nearby rocks and trees frame the area but do not occupy the player or interaction tiles; the native arrival save verifies `(311,243)` adjacent to object `(312,243)`.

All three fresh-map live walks now pass with native-save coordinate proof: Skarmory reaches `(725,664)` in 25 inputs from Route 214’s north gate, Lapras reaches `(715,830)` in 100 inputs from Route 213’s Pastoria-side gate, and Mamoswine reaches `(311,243)` in one input from Acuity Lakefront’s south entry.

### One-A interaction from fresh walked saves

**Skarmory passes.** From the native save reached by 25 normal movement inputs, one deliberate A press starts the intended level-35 Skarmory encounter.

**Lapras does not yet pass.** Although the player can walk normally to `(715,830)` and the Lapras billboard is visibly adjacent in the water at `(716,830)`, pressing A opens Platinum’s Surf prompt (`The water is a deep blue color... Would you like to surf on it?`) rather than dispatching the Totem script. Therefore this shoreline-water anchor is visually reachable but not directly interactable as implemented. Lapras must move to a nearby collision-free beach tile, or be proven interactable from an adjacent Surf tile; the simpler and more robust correction is a beach placement that uses ordinary object interaction.

**Mamoswine passes.** From the native save reached through ordinary Acuity Lakefront movement, one deliberate A press starts the intended level-44 Mamoswine encounter. The near-entry open-snow placement is both reachable and interactable.

At this checkpoint, Skarmory and Mamoswine are fully corrected. Lapras remains the only unresolved placement because the water tile routes A to Surf before the object script.

## Final Lapras beach correction

The first reachable shoreline candidate at object `(716,830)` remained unsuitable: pressing A from sand at `(715,830)` invoked the field Surf prompt before the Totem script. Lapras was therefore moved one tile west onto collision-free beach at `(715,830)`, with the interaction tile at `(714,830)` facing right.

A fresh Route 213 entry save was generated after rebuilding the event data, then the player walked from the ordinary Pastoria-side entrance `(647,812)` to `(714,830)` through **99 accepted movement inputs**. The natively saved arrival frame visibly places the player immediately west of Lapras on the beach. From that exact walked save, one deliberate A press starts the intended level-36 Lapras battle rather than Surf. Evidence: `final-validation/final-lapras-live-walk/01_arrival_before_save.png` and `final-validation/reachable-encounters/lapras-final-beach/04_battle_started.png`.

**Lapras final reachability and interaction verdict: PASS.**
