# Target-Native v6 Ruthless Gates Review

**Decision: REJECTED.** Target-native v6 is technically valid DS sprite data, but none of the three species reaches the required authentic Platinum battle-sprite standard. The silhouettes communicate the intended broad themes more clearly than v1–v5, yet the artwork remains visibly maquette-like: large geometric fills, long straight edges, weak anatomical articulation, sparse material texture, and almost no species-specific pixel clustering. It would fail at 1× even though the enlarged review sheet is readable.

## Evidence reviewed

The following evidence was inspected at both native and enlarged scales:

| Evidence | Path |
|---|---|
| Paired animation review | `target-native-v6-visual-evidence/v6_animation_review.png` |
| Six-sheet coordinate grids | `target-native-v6-visual-evidence/pixel-grids/all_pixel_grids.png` |
| Automated metric summary | `target-native-v6-diagnostics/v6_summary.md` |
| Per-sheet analyzer evidence | `target-native-v6-diagnostics/<species>_<view>/` |

## Automated gate summary

| Sheet | Colors | Mean base IoU | Animation IoU | Components | Orphans | Edge contacts | Result |
|---|---:|---:|---:|---:|---:|---:|---|
| Torterra front | 13 | 0.7232 | 0.9800 | 2 / 2 | 2 | 0 | **Reject**: too base-like; two single-pixel islands |
| Torterra back | 11 | 0.6257 | 0.9904 | 1 / 1 | 0 | 0 | **Reject**: geometric slab silhouette |
| Infernape front | 12 | 0.5050 | 0.9959 | 1 / 1 | 0 | 13 | **Reject**: clipped staff/flame; flat mannequin anatomy |
| Infernape back | 12 | 0.5429 | 0.9959 | 1 / 1 | 0 | 26 | **Reject**: severe border contact; mirrored-posterior appearance |
| Empoleon front | 13 | 0.6675 | 0.9928 | 1 / 1 | 0 | 0 | **Reject**: over-symmetric shield geometry; base-like central mass |
| Empoleon back | 7 | 0.5190 | 0.9937 | 1 / 1 | 0 | 6 | **Reject**: under-rendered rear palette and anatomy |

## Twelve-gate review

| Gate | Torterra | Infernape | Empoleon | Ruling |
|---|---|---|---|---|
| 1. Format and palette budget | Pass | Pass | Pass | All sheets are 160×80 indexed PNGs and remain within the visible-color limit. |
| 2. Unlabelled 1× Mega silhouette | Fail | Borderline fail | Fail | Themes are visible when enlarged, but the 1× read is “block fortress,” “staff monkey,” and “winged shield,” not polished Mega Pokémon. |
| 3. Base-sprite comparison | Fail | Pass numerically | Fail | Torterra front IoU 0.7232 is an automatic concern; Empoleon front 0.6675 remains high. Infernape’s lower IoU does not rescue weak anatomy. |
| 4. Species landmark hierarchy | Fail | Fail | Fail | Major landmarks are oversized symbols rather than integrated anatomy. |
| 5. Platinum pixel clustering | Fail | Fail | Fail | Long straight stair-steps, rectangular fills, and coarse highlights read as a construction draft rather than Gen IV sprite craft. |
| 6. Anatomy and attachment | Fail | Fail | Fail | Torterra’s fortress sits as a slab; Infernape’s limbs and staff grips are diagrammatic; Empoleon’s wings connect as broad shields without believable shoulder structure. |
| 7. True rear orientation | Fail | Fail | Fail | Rear views remove facial marks, but do not convincingly expose rear anatomy, scapular/wing roots, shell depth, or posterior limb overlap. |
| 8. Perspective and volume | Fail | Fail | Fail | All three rely on flat frontal symmetry or box-like side planes. |
| 9. Palette and material rendering | Fail | Borderline fail | Fail | Empoleon back uses only seven colors; Torterra’s stone and foliage have minimal ramps; Infernape is clearer but still lacks fur/fire material nuance. |
| 10. Outline integrity and isolation | Fail | Fail | Pass technically | Torterra has two orphan pixels. Infernape has 13/26 border contacts and visible clipping. Empoleon is connected but its huge perimeter dominates the canvas. |
| 11. Animation | Fail | Fail | Fail | IoU 0.98–0.996 indicates near-static swaps. Motion is not a convincing battle idle and does not articulate Mega landmarks. |
| 12. Emulator risk | Fail | Fail | Fail | The flat geometry and edge contacts are likely to look harsher on the real battle background; promotion is not justified. |

## Species-specific rejection findings

### Mega Torterra

The fortress direction is present, but the shell is rendered as a rectangular masonry box with a dark horizontal band. It does not wrap around the torso or show a believable load-bearing shell. The tree canopy is a broad rounded rectangle, and the trunk reads as a circular emblem planted on the front face rather than a rooted tree rising from the shell. The head remains close to the canonical Torterra footprint, producing the 0.7232 mean silhouette IoU. The front sheet also contains two one-pixel islands, most plausibly the tiny white eye marks, so the expression is technically disconnected.

**v7 requirements:** lower base IoU below 0.60; replace the rectangle with a stepped, asymmetrical bastion silhouette; create visible shell curvature beneath the battlements; root the tree off-center and behind the head plane; enlarge and reshape the cranial horns; integrate the face and eye into the main connected cluster; use broken stone clusters rather than long flat bands; establish foreleg overlap and rear-leg foreshortening.

### Mega Infernape

The Monkey King brief is recognizable, and v6 preserves a continuous staff-to-hand relationship better than earlier attempts. However, the body is a stick-figure mannequin built from long diagonal limb bars. The cream mane is an almost perfect ring, the face is a mask disk, and the torso is a flat rectangular tunic. The front staff touches or crosses the canvas on the left; the rear has 26 border contacts across the staff/flame extremities. Both flames are partially clipped. The rear view mostly mirrors the front silhouette while replacing facial detail, rather than showing shoulder blades, back mane layering, hand rotation, or correct staff depth. The two animation frames are almost identical (IoU 0.9959).

**v7 requirements:** keep every pixel at least two pixels from the canvas border; shorten or steepen the staff without shrinking its landmark importance; build a compact bent-knee martial pose; give forearms, shoulders, thighs, and feet distinct taper and overlap; make two unmistakable closed grips that visibly wrap around one continuous staff; break the circular mane into asymmetric flame/fur clumps; add a true rear shoulder and spine read; animate staff angle, flame flicker, mane tips, and weight shift.

### Mega Empoleon

The emperor-wing concept is legible, but the front is dominated by bilateral symmetry and large gold kite shapes. The body reads as a heraldic shield rather than a living penguin. The head and crown occupy the centerline with little depth; both wings attach as enormous curved panels. The front IoU remains high at 0.6675 because the central body mass is still close to canonical Empoleon. The rear uses only seven colors, flattening the mantle, wing backs, and torso into broad blue-gray areas. It also lacks credible rear wing-root and tail anatomy.

**v7 requirements:** reduce front base IoU below 0.60; angle the body three-quarters rather than dead-on; make one wing nearer and foreshortened, the other extended to create an emperor-cape silhouette; integrate gold blade feathers within the wing anatomy instead of placing large flat kite emblems; add crown depth and a face/beak plane; use at least ten purposeful rear-view colors with distinct outline, deep shadow, midtone, and highlight ramps; show scapular roots, mantle overlap, tail, and rear foot placement; animate the mantle/wing tips and crown plume.

## Category scoring

The scoring below uses the skill’s eight categories, each out of five. A pass requires at least 4/5 in every category and at least 36/40 overall.

| Category | Torterra | Infernape | Empoleon |
|---|---:|---:|---:|
| Mega concept and silhouette | 2 | 3 | 2 |
| Species identity and landmarks | 2 | 2 | 2 |
| Anatomy and attachment | 1 | 1 | 1 |
| Rear-view legitimacy | 1 | 1 | 1 |
| Pixel clustering and outline craft | 1 | 1 | 1 |
| Palette and material rendering | 2 | 2 | 1 |
| Animation quality | 1 | 1 | 1 |
| DS technical/emulator readiness | 3 | 2 | 3 |
| **Total** | **13/40** | **13/40** | **12/40** |

## Final v6 ruling

**Do not promote v6 to production.** A v7 pass must be a genuine native-pixel redraw rather than a local cleanup. Technical format compliance is retained, but all three species need more organic DS anatomy, stronger three-quarter staging, true rear construction, deliberate material clusters, and meaningful two-frame motion. V6 remains preserved as evidence of the “geometric native reconstruction” strategy and why technical validity alone does not satisfy the brief.
