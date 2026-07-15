# Direct DS-Style Generation Review

## Strategy S05 — Mega Torterra direct DS generation

**Decision: reject direct shrinking; retain silhouette regions for reconstruction.** The generated design now unmistakably differs from base Torterra and retains coherent front/rear anatomy. The fortress shell, tree roots, frontal gem plate, and heavy body are strong. However, this remains high-resolution pseudo-pixel art: the canopy has dozens of micro-notches, the trunk contains thin interior lines, and the silhouette height is dominated by a tree that would leave the head only a few pixels tall after fitting to 80×80. The rear design is coherent but needs explicit head/neck visibility and fewer spikes. Use the large-shape mask, not the raw pixels.

## Strategy S05 — Mega Infernape direct DS generation

**Decision: reject direct shrinking; retain the pose and grip topology.** The front and rear are both unambiguously Mega/Monkey King and the staff is a single continuous object held at two points. The front, however, shows a doubled parallel-looking staff segment near the torso due to overlapping outline/highlight geometry, which can read as two weapons when reduced. The huge mane consumes too much of the frame, and thin limb/armor lines will disappear. The rear staff and lower hand are coherent, but the large central divider and generated border are unusable. Preserve the two-hand diagonal composition, compact the mane, thicken limbs, and reconstruct manually in target-sized clusters.

## Strategy S05 — Mega Empoleon direct DS generation

**Decision: reject direct shrinking; retain the strongest target-sized design skeleton.** This is the most immediately reducible of the three direct-DS experiments. The torso remains broad, the wing planes are clearly attached, the crown is integrated, and the rear is a genuine counterpart rather than a front repaint. It still fails production criteria: the wings are so wide that fitting them in 80 pixels would make the body undersized; the thin gold rims and crown tines would fracture; the pale mantle appears as long hanging cloth instead of the reference’s shoulder/back plume mass; and the generated image has a hard center divider. Reconstruct with slightly folded wings, a three-prong crown at least two pixels thick, and two compact mantle masses anchored at the shoulders.
