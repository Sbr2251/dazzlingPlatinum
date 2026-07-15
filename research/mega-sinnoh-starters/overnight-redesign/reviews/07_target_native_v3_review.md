# Target-Native v3 Static Review

## Decision

**Advance v3 to animation and rear-view refinement, but do not promote it yet.** This is the first batch whose three silhouettes read as deliberate Mega transformations rather than ornamented base starters. The result remains subject to non-duplicated animation, front/back feature consistency, native indexed-palette validation, and unobscured emulator review.

## Provenance discipline

The selective v3 batch retains only changes that survived visual comparison:

| Species | v3 source | Rejected alternatives |
|---|---|---|
| Torterra | v2 target-native reconstruction | v1 facial ambiguity and any automatic 24-strategy reduction |
| Infernape | precritical concept reconstruction with the original single staff | v1 doubled-staff overlay and v2 flattened torso repaint |
| Empoleon | v1 target-native reconstruction | v2 pasted-on crown and shoulder patches |

## Static visual judgment

**Mega Torterra:** The front view now has a fortress shell, monumental trunk and canopy, luminous armored cheek/head plate, deep shell rim, and materially different mass distribution. Its front base-IoU remains high at 0.7066 because both designs are quadrupeds with a tree in the same battle-facing orientation, not because this candidate reuses the base pixels. The candidate is visibly broader, taller, more architectural, and more heavily armored than canonical Torterra. The body and all additions form one connected component with no orphan pixels or edge contacts. The rear score is 0.5787. Further silhouette changes made only to lower IoU would risk weakening the coherent anatomy and are not justified unless animation or emulator evidence exposes a real readability defect.

**Mega Infernape:** The Monkey King identity is unmistakable. There is exactly one diagonal staff; it passes behind the torso where physically appropriate and reappears continuously at both ends. The gold wrists/hands meet the shaft, the mane creates a transformed crown-like silhouette, and the body remains readable rather than disappearing inside the flame mass. Base-IoU is 0.4916 front and 0.3960 rear. Both views are one connected component with no tiny islands or edge contacts. The next gate must prove that frame two animates the body and staff coherently rather than duplicating frame one.

**Mega Empoleon:** The broad emperor torso, crown lattice, mantle, attached blade-wings, and gold armor distribution make the transformation obvious. Both wing planes meet the shoulders in front and rear views. Base-IoU is 0.5935 front and 0.5143 rear. Both views are one connected component with no tiny islands or edge contacts. The rear needs motion that preserves wing attachment and crown geometry.

## Analyzer summary

| Sheet | Visible colors | Base IoU mean | Components per frame | Orphans | Edge contacts |
|---|---:|---:|---:|---:|---:|
| Torterra front | 15 | 0.7066 | 1 | 0 | 0 |
| Torterra back | 11 | 0.5787 | 1 | 0 | 0 |
| Infernape front | 15 | 0.4916 | 1 | 0 | 0 |
| Infernape back | 15 | 0.3960 | 1 | 0 | 0 |
| Empoleon front | 15 | 0.5935 | 1 | 0 | 0 |
| Empoleon back | 14 | 0.5143 | 1 | 0 | 0 |

The current animation IoU of 1.0 is an intentional hard failure caused by duplicated frames used only to run the static diagnostics. v3 cannot be considered complete until distinct frame-two poses are constructed and reviewed.
