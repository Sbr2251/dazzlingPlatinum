# Target-Native Reconstruction v1 — Ruthless Review

**Batch decision: major improvement, but not ready for production.** Unlike the currently promoted base-derived assets, all three candidates are immediately recognizable as transformed Mega designs. The sprites use compact, hard-edged clusters and fit the DS frame without clipping. Nevertheless, several critical defects remain.

| Species | What now works | Remaining rejection defects |
|---|---|---|
| Torterra | Fortress shell, giant integrated tree, mineral plate, broad quadruped body, and true rear orientation are all unmistakable | The front face is partially buried beneath the shell rim; the canopy remains visually dominant; front and rear shell spike placement is not yet tightly matched; the front legs need cleaner separation |
| Infernape | Monkey King mane, armor, wide stance, flame-tipped staff, distinct front/rear poses, and transformed silhouette survive at 80×80 | At native scale the staff is readable but the two grips are still too symbol-like; the diagonal shaft consumes too much foreground; the lower end flame is oversized; face/mane balance still favors the mane; the rear right forearm merges with the torso |
| Empoleon | Broad emperor body, large integrated crown, shoulder mantle, blade wings, and true rear silhouette are strongly Mega | The rear crown prongs appear detached from the head plate; the outer wings are still too long and dominate the body; the front left wing includes fragile one-pixel gold structures; feet and lower body are small relative to the upper silhouette |

**Next action:** perform a second target-native pass with explicit anatomical redrawing rather than another warp: expose Torterra’s face and simplify the tree; thicken and reposition Infernape’s hands around the staff; shorten both Empoleon wings and reconnect the rear crown through a solid forehead/back-of-head plate.

## Native 1× follow-up

At actual 80×80 scale, **Torterra’s face does remain identifiable**, so the next pass should not radically rescale it again. The priority is stronger eye/jaw separation from the shell rim and cleaner front-leg spacing. The tree is large but no longer erases the quadruped body.

At actual 80×80 scale, **Empoleon’s rear crown connection is the primary automatic-rejection risk**: the gold prongs read as hovering above the dark head plate. The blade wings remain attached by dark shoulder pixels and do not clip, but their outer gold edges occupy disproportionate attention. The next pass must join the crown through a solid dark/gold base and strengthen the shoulder anchors before any further palette work.

The quantitative analyzer confirms strong transformation rather than base-sprite reuse: mean base-silhouette IoU ranges from 0.3957 to 0.7065, all sheets remain one connected component, no orphan/tiny components occur, no frame touches an image edge, and each sheet uses 11–15 visible colors. These technical successes do **not** override the anatomical rejections above.
