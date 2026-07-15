# Target-Native v4 Animation and Palette Review

## First animation attempt: rejected

The first v4 motion pass moved rectangular anatomical regions by erasing and repasting them. Although it created obvious frame variation, the analyzer found split components in both Empoleon views, one-pixel islands in both Infernape views, and a visibly detached Infernape mane tip. This pass was rejected and never promoted.

## Corrected animation method

The corrected pass restricts added anticipation pixels to four-neighbor-connected locations and leaves major anatomical anchors intact. Torterra retains a controlled canopy/head motion; Infernape retains its body, mane, central staff shaft, and both grip contacts while only the mane edge and staff flames change; Empoleon retains both shoulder anchors while the wing and crown outlines gain subtle motion.

## Quantitative gate

| Sheet | Visible colors | Components F0/F1 | Orphans | Edge contacts | Animation IoU |
|---|---:|---:|---:|---:|---:|
| Torterra front | 15 | 1 / 1 | 0 | 0 | 0.9717 |
| Torterra back | 11 | 1 / 1 | 0 | 0 | 0.9828 |
| Infernape front | 15 | 1 / 1 | 0 | 0 | 0.9613 |
| Infernape back | 15 | 1 / 1 | 0 | 0 | 0.9512 |
| Empoleon front | 15 | 1 / 1 | 0 | 0 | 0.9779 |
| Empoleon back | 14 | 1 / 1 | 0 | 0 | 0.9843 |

All six sheets pass the native 160×80 indexed format gate, remain within the fifteen-visible-color budget, avoid frame edges, and preserve one connected component in both frames.

## Visual judgment

The corrected enlarged frame-pair sheet shows no doubled staff, detached canopy, separated wing, pasted-on crown, or front/back identity drift. The Infernape indexed front sheet was also inspected at its actual 160×80 format after shared-palette conversion. Both frames preserve a single red staff running through the same two grip locations, the flame tips remain attached, and the changed pixels read as controlled flame/mane motion rather than anatomy deformation. The palette retains distinct outline, body, gold armor, staff, flame, and mane clusters without automatic dithering.

**Decision:** advance the corrected v4 batch to comparative final selection. Promotion remains contingent on final production sidecars, shiny palette generation, repository validators, clean ROM build, and unobscured emulator captures.
