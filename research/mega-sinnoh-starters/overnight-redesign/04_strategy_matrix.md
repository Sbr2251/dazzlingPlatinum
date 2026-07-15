# Mega Sinnoh Starter Sprite Experiment Matrix

**Author:** Manus AI

This matrix separates genuinely different construction and conversion methods. Every strategy must produce preserved artifacts and a written outcome. No method is counted as “tried” merely because it was considered.

| ID | Strategy | Concrete procedure | Primary hypothesis | Automatic failure signal |
|---|---|---|---|---|
| S01 | Canonical base paint-over | Recolor and redraw internal regions while preserving the canonical silhouette | Pixel-authentic clusters may survive extensive internal redesign | Mega silhouette remains over 80% aligned with base |
| S02 | Canonical base with large appendages | Add crown, weapon, mantle, shell massif, or wing structures to the base pose | Strong appendages may transform identity cheaply | Reads as base plus detached accessories |
| S03 | Base skeleton, full contour redraw | Retain only joint anchors and footprint; redraw all outer contours | Canonical proportions can guide a genuinely new body | Fewer than three large regions materially change |
| S04 | Direct nearest-neighbor concept reduction | Crop concept transparently and reduce straight to target with nearest-neighbor | Hard edges may preserve concept identity | Stair-stepping and lost thin anatomy dominate |
| S05 | Lanczos reduction then hard indexing | Smoothly reduce, strip alpha fringe, then index without dithering | Better gross shape may survive before repixeling | Antialias haze or fragmented clusters remain |
| S06 | Area/box reduction then hard indexing | Average source blocks, threshold alpha, then index | Area sampling may preserve value masses | Muddy outline and merged materials |
| S07 | Two-stage 4× reduction | Reduce concept to 320×320, clean, then nearest-neighbor to 80×80 | Intermediate cleanup may retain landmark placement | Cleanup still collapses into noisy micro-detail |
| S08 | Silhouette-first target raster | Trace only the transformed silhouette directly at 80×80, then fill anatomy | Large-shape identity should survive every later step | Species or Mega form unclear in one-color test |
| S09 | Cluster-first target painting | Build 2–4 pixel color clusters from large to small with no initial outline | Organic forms may read better than traced downscales | Weak diagonal connections or orphan noise |
| S10 | Four-value-first construction | Design in four grayscale values, then map semantic color ramps | Value separation can prevent palette-dependent anatomy | Major parts merge in grayscale |
| S11 | Palette-first construction | Reserve fifteen semantic colors before drawing and never exceed them | Prevents destructive late quantization | Palette roles are exhausted before Mega anchors read |
| S12 | Outline-first construction | Draw a clean one-pixel outline and internal dividers before color | Gen IV contour discipline may stabilize anatomy | Outline becomes a hollow sticker or over-dominates form |
| S13 | Modular anatomy assembly | Draw head, torso, limbs, weapon/landscape, and effects on logical layers; join at target size | Explicit attachment control prevents floating parts | Essential components remain separate or mis-scaled |
| S14 | Vector-mask concept tracing | Trace large concept regions as flat masks, rasterize at 80×80, then pixel-clean | Vector simplification can preserve large motifs | Curves rasterize mechanically or lack DS character |
| S15 | Canonical cluster transplant | Reuse proven canonical head/limb clusters inside a new silhouette | Native clusters can lend authenticity without copying the form | Base silhouette still dominates or seams are visible |
| S16 | Concept silhouette plus canonical shading grammar | Use concept outline, then shade with canonical ramp placement and cluster sizes | Can combine new identity with Gen IV rendering | Lighting or texture contradicts new anatomy |
| S17 | Generated high-resolution character concept | Generate a clean transformation concept without requesting pixel art; manually simplify | Strong design ideation may be easier outside pixel constraints | Concept cannot be reduced without losing anchors |
| S18 | Generated large pixel-art sprite | Generate a 5×–10× nearest-neighbor-style sprite, reduce only by integer scale | Model may supply usable pixel clusters | Fake pixel art contains subpixel gradients and inconsistent blocks |
| S19 | Generated native-resolution sprite sheet | Request front/back DS battle sprites at target composition | Direct target prompting may preserve pose and scale | Model produces illegible anatomy or non-matching views |
| S20 | Generated silhouette sheet | Generate only solid silhouettes for front/back/pose selection | Separates design identity from rendering noise | Silhouettes are generic, asymmetrical, or inconsistent |
| S21 | Generated flat-color maquette | Generate no-shading, five-region character maquettes for target rasterization | Flat masses may survive DS reduction better than rendered concepts | Missing depth cues make anatomy ambiguous |
| S22 | Back-view-first construction | Establish true rear landmarks first, then derive the front | Prevents fake/mirrored back sprites | Front loses agreed concept identity or landmarks disagree |
| S23 | Front/back landmark map | Define coordinates for crown, shoulders, hips, weapon grip, shell landmarks, and feet before drawing | Shared anchors can enforce orientation consistency | Landmark errors exceed three pixels after normalization |
| S24 | Frame-one master plus controlled motion | Finish one frame, duplicate it, and move only selected connected clusters 1–3 pixels | Prevents animation-frame morphing | Weapon length, anatomy, or palette changes between frames |
| S25 | Independent frame drafts plus reconciliation | Draft both poses separately, then reconcile silhouettes and landmarks | Independent posing may avoid stiffness | Reconciliation cannot eliminate identity drift |
| S26 | Custom semantic palette optimization | Cluster source colors by material role, manually merge near-duplicates, and lock fifteen visible entries | Better color economy should improve readability | Wasted near-duplicates or value collisions remain |
| S27 | Canonical palette remapping | Force the design into the base species’ canonical palette roles | Existing palettes may guarantee Gen IV harmony | Signature Mega materials cannot be separated |
| S28 | Battle-background contrast optimization | Test candidates over representative light/dark battle backgrounds and adjust outline/value ramps | Context testing should prevent disappearing structures | Any essential structure disappears or merges in game |

## Required output per strategy

Each completed strategy receives a directory containing the source/crop, at least one 80×80 frame, a one-color silhouette, a four-value rendering, a palette or source-color report, and a brief rejection or retention note. Conversion-only strategies are run on all three species’ best available front concepts; construction strategies may first be prototyped on the species whose design stresses that method most, then propagated only if they pass.

## Ruthless decision order

The decision order is **Mega silhouette**, **species recognition**, **anatomy and attachment**, **front/back truth**, **cluster quality**, **palette/value quality**, **animation consistency**, and only then surface polish. Technical file validity never raises a visual score.
