# V7 maquette-conversion visual review

## Decision

Both conversion branches are a material improvement over v6 and finally read as complete Mega designs rather than geometric placeholders. The **nearest-neighbor branch advances as the primary v7 candidate** because it preserves firmer dark outlines and more deliberate pixel clusters at native scale. The box-resampled branch remains a useful fallback for isolated internal smoothing but introduces softer edge colors that are less characteristic of Platinum sprites.

## Reject-first findings

| Sprite | Status | Evidence and remaining risk |
|---|---|---|
| Torterra front | Advance with scrutiny | Long, low quadruped anatomy, huge shell blades, rooted tree, canopy, planted feet, and armored head all read immediately. It is substantially different from base Torterra. The white spike mass is dense but remains layered rather than becoming a rectangular fortress. Check at native scale that the front horn and face do not merge. |
| Torterra back | Advance with scrutiny | This is a true rear construction: trunk planes, canopy overlap, shell rear, hips, and rear spike order differ from the front. No frontal eye is apparent. The leftmost upward spike and pale trunk opening need automated component and rear-view checks to ensure they do not read as an orphan or face. |
| Infernape front | Advance with targeted gate | Compact Monkey King anatomy, swept mane/flame, gold scroll armor, blue hands/feet, and one continuous diagonal staff are all present. Both hand regions intersect the shaft, but grip continuity must be tested at native coordinates. The lower staff flame is safely inside the canvas. |
| Infernape back | Advance with targeted gate | The rear shows mane, shoulder/hip overlap, bent legs, rear armor, and staff continuity rather than a mirrored face. The long flame arc is intentionally directional. Verify that its staff and flame remain one connected subject after palette indexing and that no border contact occurs. |
| Empoleon front | Advance | The giant gold-edged foreground blade-wing, secondary mantle wing, integrated crown, pale center plume, narrow dark body, and gold talons form a clear emperor Mega silhouette. It is asymmetrical and radically different from base Empoleon. |
| Empoleon back | Advance with scrutiny | Rear crown planes, pale nape, shoulder roots, warm back accents, mantle, connected wings, hips, and talons are readable. It no longer collapses into a dark blob. Verify front/back silhouette distance and ensure the rear does not accidentally retain a frontal eye pixel after quantization. |

## Animation assessment

The paired frames are not frozen: each view uses a one-pixel breathing/bob displacement with species/view-dependent horizontal timing. This is modest but valid Platinum-scale motion and avoids the v6 issue where high-risk structures appeared static or disconnected. Before promotion, automated gates must prove nonzero frame difference, transparent margins, one principal connected component, indexed 4-bit PNG output, 80×80 frame geometry, and a maximum of 15 visible colors.
