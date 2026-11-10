# Garius (rival): character design

Approved 2026-11-09. The bible gives him no physical description; these traits come from his story beats.

| Trait | Design | Story basis |
|---|---|---|
| Build | Same age as Darren, a little taller and leaner | His mom: "his father's habit of running off before anyone can stop him" |
| Hair | Ink-navy, short at the sides, a windswept tuft blown back off the forehead | Always moving |
| Eyes | Amber, slightly narrowed | Warm at first glance, guarded on a second look |
| Jacket | His father Elias's burnt-orange field jacket, cream trim, a size too big, collar popped, sleeves pushed up | Never mentioned in dialogue (track G); the opposite of Eclipse's dark and violet |
| Under layer | Dark teal shirt, charcoal trousers, cream-and-rust shoes | The jacket stays the only loud colour |
| Keepsake | His father's brass pocket watch at the hip | Ties to Dialga and his wish to turn time back |

Arc 3 look (after the reveal): no jacket, Eclipse dark with the violet ring; hair, eyes and watch unchanged.
Epilogue: the jacket is back on.

Source: `tools/garius_sprite/garius.py` (palette and pixel grid). Preview: `garius_design.png`.
Style: stock Platinum. The key frame is drawn on stock Barry's skeleton (same height, face box, eye columns and stance);
the preview is a line-up with stock Barry, Rowan and Cyrus.
Status: front-facing overworld key frame only; not in the build yet.

Battle front sprite (shown as a battle starts): the pose comes from a generated concept image
(`src/garius_battle_concept.webp`). `tools/garius_sprite/convert_concept.py` shrinks it to 80x80 and 15 colours
(`concept_grid.txt`); `tools/garius_sprite/garius_battle.py` closes the outline and redraws the face, hair lights and
watch by hand. Two frames for the intro animation: eyes shut, then eyes open with the smirk.
Preview: `garius_battle_design.png` (stock Barry, frame 1, frame 2, stock Cyrus).
Frames: `res/trainers/classes/garius/front_design.png` (160x80).
Status: design frames; not a trainer class in the build yet.
