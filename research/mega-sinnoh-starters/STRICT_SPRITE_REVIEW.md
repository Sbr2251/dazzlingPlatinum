# Strict Mega Sinnoh Starter Sprite Review

## Acceptance Standard

The revised assets must match the visual economy of native Generation IV battle sprites: one continuous and immediately identifiable body silhouette, intentional clusters of pixels rather than anti-aliased noise, a restrained 16-color palette with clear light/mid/shadow roles, readable anatomy at 1× scale, a genuinely rear-facing player view, and no dependence on tiny facial or decorative details for identity.

## Initial Runtime Diagnosis

| Species | Front-view defects | Back-view defects | Verdict |
|---|---|---|---|
| Mega Torterra | The body, shell, tree, head, foreground foliage, and stone structures compete as separate masses. The head and front legs are difficult to distinguish, and the low/wide composition reads more like a miniature landscape than a single Pokémon. | The view is primarily a side profile rather than a convincing rear view. The head remains prominently visible, the tree obscures the body connection, and the shell/hindquarter anatomy is ambiguous. | Redesign both views. Preserve the fortress-tree concept but simplify it to one connected quadrupedal silhouette. |
| Mega Infernape | Severe fragmentation: bright flame clusters, staff, limbs, face, and torso separate into disconnected marks. The light body values disappear against the scene, and the character cannot be parsed reliably at native scale. | The same fragmentation is worse from behind; the rear anatomy is not readable, and the staff/flame elements overpower the body. | Full redesign of both views. Establish a dark, solid body first; treat the flame crown and staff as secondary accents. |
| Mega Empoleon | More coherent than Infernape, but the broad black-and-gold wing panels dominate while the torso, feet, head, and crown merge into a narrow central column. Fine pale-blue plume pixels add noise instead of hierarchy. | The mantle reads as a large dark mass with weak separation between torso, wings, and legs. The orientation differs from the front, but the anatomy remains muddy. | Redesign both views. Use fewer, larger armor planes and a broader, readable penguin torso. |

## Native Comparison Finding

The canonical Mega Lucario sheet uses compact, connected silhouettes, large color blocks, sparse highlights, and deliberate one-pixel outlines. Even with two animation frames and complex appendages, the torso and limbs remain continuously readable. The current starter assets fail mainly because their generated source art contains too many thin, disconnected, anti-aliased details before 16-color reduction. The correction must begin with simpler source compositions rather than further quantizing the existing images.

## Approved Design Anchors for Redesign

The retained three-species concept board establishes Torterra as a low, heavy quadruped whose central tree grows directly from a broad green-and-stone shell, with four clearly planted legs and a small armored head; Infernape as an upright martial simian with a white flame crown, dark solid torso and limbs, gold guards, and one diagonal flame-tipped staff; and Empoleon as a broad royal penguin with a blue central torso, a tall gold trident crown, and two large but anatomically attached black-and-gold wing armor planes. The separate approved Infernape reference confirms that the staff and flame arc are signature accents, but the revised DS sprite must reduce them to compact connected shapes around a readable body rather than reproduce the reference’s long ribbons and airborne pose.
