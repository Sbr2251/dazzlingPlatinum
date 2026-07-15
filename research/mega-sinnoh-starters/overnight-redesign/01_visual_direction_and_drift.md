# Recovered Visual Direction and Drift Diagnosis

## Authoritative references

The primary concept board is Rocketmanga’s Sinnoh Mega set. Mega Torterra is not merely base Torterra with a different shell: it has a dramatically taller, ancient tree whose trunk visibly grows through the armor; a broad mountain-like white shell rim; a large faceted green frontal shell plate; horn/spike armor; thicker bark-brown legs; and a low fortress silhouette. Mega Empoleon is not merely base Empoleon with crown extensions: it has a greatly widened black-and-gold armored-wing silhouette, a tall mask-like trident crown, a royal dark central chest, large pale-blue mantle/plume masses, and gold feet. These large-shape changes are required to read at Nintendo DS scale.

The separate approved Mega Infernape reference defines the stronger visual direction for Infernape: an athletic Monkey King silhouette; large white flame-like crown fur; a dark connected torso and limbs; gold guards; blue hand/foot accents; a single long red staff held across the body; and compact orange-red flames attached to the staff ends. The Rocketmanga version adds a large white mane, red mask, tail/flame curl, and oversized martial guards. The DS sprite should combine these anchors without preserving the source art’s airborne pose or long detached flame ribbons.

## Why the previous native-derived sprites failed

The native-derived pipeline began from Platinum’s canonical starter sprites and drew only modest surface decorations over them. This guaranteed correct format, animation layout, and anatomy, but it also guaranteed that the silhouettes remained overwhelmingly identical to the base forms. Palette validity and connectedness were mistaken for successful Mega design. Infernape’s added staff and Torterra’s added shell ridges functioned as accessories rather than transformational anatomy; Empoleon’s crown and mantle accents likewise did not create the broad armored emperor silhouette required by the reference.

## Non-negotiable redesign anchors

| Species | Required silhouette changes | Required palette hierarchy | Automatic rejection conditions |
|---|---|---|---|
| Mega Torterra | Much taller ancient tree; massive connected mountain shell; frontal faceted green armor plate; horn/spike armor; heavier legs and low fortress body | Dark outline; bark shadow/mid/light; forest-green shadow/mid/light; pale stone armor shadow/light; small red eye accent | Base Torterra silhouette still dominant; tree reads as a small accessory; landscape fragments detach; head or legs cannot be parsed at 1× |
| Mega Infernape | Enlarged white flame crown/mane; dark solid martial body; visible gold guards; one staff crossing and visibly touching both hands/forearms; compact staff-end flames | Near-black outline/body shadow; warm brown/red body; white/cream mane; gold guards; blue extremities; orange/red flame accents | Canonical Infernape pose with accessory pasted on; floating staff; detached flame noise; pale body disappears; rear view is a side/front repaint |
| Mega Empoleon | Broad armored penguin torso; huge but attached black-and-gold blade wings; tall mask-like trident crown; royal mantle mass; wider stance | Dark navy/near-black planes; medium blue torso; gold armor; pale-blue mantle highlights; white belly accents | Base Empoleon silhouette still dominant; crown is the only change; wings read as separate shields; torso collapses into a thin column |

## Acceptance principle

A candidate must be recognizable as the intended species and unmistakably transformed into its Mega form when shown as an unlabelled 80×80 frame at 1×. Technical validity cannot compensate for weak Mega identity. Every front and rear sprite must survive silhouette-only, four-value grayscale, indexed-palette, frame-to-frame consistency, and in-game rendering checks.

## Strict comparison of the two failed production paths

The current emulator assets are clean but fundamentally fail Mega identity. Torterra’s body and tree placement are almost entirely canonical; the small mountain ridge and shell decorations do not alter the base silhouette. Infernape is closer to a new form because of the enlarged flame crown and staff, but the front reads as a canonical-sized Infernape with accessories, while the rear is oversized, crouched, partially hidden, and inconsistent with the front. Empoleon remains essentially canonical, with modest gold and mantle extensions rather than Rocketmanga’s wide armored emperor shape.

The earlier concept-derived preview demonstrates the opposite failure mode. It contains the correct large-scale transformations—Torterra’s colossal tree and mountain armor, Infernape’s crown/staff/flames, and Empoleon’s massive gold-black wings and pale-blue mantle—but the conversion is noisy and fragmented. Torterra’s rear frames lose the head and body connection; Infernape’s dark anatomy disappears into holes and scattered outlines; Empoleon is the most salvageable because its broad armor planes and torso remain largely connected. The correct path is therefore neither “decorate the canonical sprite” nor “directly shrink a detailed illustration.” It must reconstruct the concept at DS scale with deliberately simplified pixel clusters and species-specific front/rear anatomy.
