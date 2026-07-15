# Native-Derived Mega Sprite Redesign Specification

The generated replacement sheets failed because they changed each species’ fundamental anatomy and introduced more silhouette detail than an 80×80 Nintendo DS battle frame can support. The corrected approach uses each canonical Platinum sprite as the anatomical source of truth and applies only a small number of connected Mega-defining additions.

| Species | Anatomy that must remain unchanged | Mega additions permitted | Features explicitly rejected |
|---|---|---|---|
| Mega Torterra | Head position, four-leg stance, shell ellipse, tail, baseline, and the canonical rear tree/shell relationship | A broader tiered canopy, darker armored shell rim, three connected stone spires, and restrained root-like facial armor | A tree larger than the body, floating foliage, fortress clutter, changed body proportions, or unrelated front/back shell geometry |
| Mega Infernape | Face mask, long limbs, compact torso, tail, crown flame, hand and foot placement, and canonical rear shoulder anatomy | A slim staff connected to the raised hand, a slightly longer controlled crown flame, dark bracers/greaves, a simple waist sash, and one repeated gold accent | A full dark costume, detached fireballs, mask replacement, bulky armor, disconnected staff flames, or a generic humanoid-warrior silhouette |
| Mega Empoleon | Current revised penguin torso, trident crown, wing placement, and rear-facing armor relationship | No automatic change; retain only if it remains clearer than the native-derived Torterra and Infernape in the final comparison | Additional filigree, narrow disconnected limbs, or front/back poses that appear to be the same camera angle |

> **Acceptance rule:** At native 1× scale, an observer must identify the base species before noticing the Mega ornamentation. Every added feature must connect to the body or to an object held directly by the body, and the front/back sheets must depict the same design rather than merely sharing colors.

The animation pair for each view will retain the canonical frame positions and movement. The normal palette will remain at 15 visible colors plus transparency, and no smoothing or subpixel scaling will be introduced.

## Torterra Coordinate Review

The canonical front frames already provide the correct connected silhouette: the canopy spans approximately `x=24–61, y=4–31` in frame one and `x=95–154, y=3–32` in frame two, while the white shell rim and three canonical shell spikes occupy the mid-body band. The Mega edit must therefore modify internal color masses and extend only a few pixels beyond these bounds; replacing the tree or moving the head is unnecessary.

The canonical rear frames correctly hide the face and foreground the shell, tree trunk, and three white spires. The rear canopy occupies approximately `x=0–54, y=8–44` and `x=80–151, y=7–45`. The same darker canopy band and armored shell-rim treatment used in front can be repeated here without changing the perspective. The existing three rear spires already communicate the intended mountain motif, so the Mega version should sharpen or recolor them rather than add unrelated structures.

## Infernape Coordinate Review

The canonical front frames already contain an unmistakable face mask, compact torso, long limbs, tail, crown flame, gold joints, and dark-blue extremities. In frame one the raised left arm ends near `x=14, y=6`; in frame two the raised right fist occupies approximately `x=136–147, y=18–31`. A staff can therefore be connected directly through the raised hand in each frame and extended toward a nearby free edge, but it must remain two to three pixels thick and must not cross the face or detach from the grip. The crown flame should retain the canonical red/yellow mass and can be lengthened by only a few connected pixels.

The canonical rear frames strongly establish the player-side view through the visible back, shoulder armor, rear flame crown, and partially cropped lower body. A corresponding staff should pass through the hand/forearm on the visible side and remain behind the torso where necessary. The Mega treatment will recolor existing forearm and shin accents toward a restrained dark indigo while keeping the original skin, white fur, gold joints, and red/yellow flame architecture. No full-body costume or replacement mask will be introduced.

## Native-Derived Candidate Review

The first native-derived **Torterra** candidate now reads immediately as Torterra from both perspectives. The front and rear views share the same canopy, shell, head, and stone/amber armor language; no anatomy is replaced, no disconnected structures are introduced, and the existing rear spires remain a genuine back-view feature. The Mega accents are intentionally restrained and remain connected to the canonical body.

The native-derived **Infernape** body, face, limbs, tail, crown flame, and palette now read clearly as Infernape. However, the staff still fails the connectivity requirement in frame-specific ways. The first front pose nearly connects at the raised hand, but the second front pose leaves the staff visually isolated to the right. In the rear preview the upper staff segment is visible at the right edge while the body hides its center, making it look detached. The next revision must draw the long shaft behind the body but redraw a short shaft segment and gold grip ring in the foreground directly across the visible hand in every frame. No candidate may be promoted while any staff segment reads as a floating object.

The corrected Infernape staff now crosses a visible hand in both the front and rear candidate previews, while the canonical body and flame remain intact. Torterra remains anatomically coherent and consistent across perspectives.

The currently committed emulator capture confirms that **Empoleon still needs the same native-derived treatment**. Although its colors load correctly, its generated front sprite is too small and visually compressed beside the Rowan reference, with a narrow, jagged silhouette that does not clearly preserve Empoleon's broad penguin torso or canonical flipper geometry. It should not be retained merely because it is less fragmented than the rejected first-pass Infernape.

### Empoleon native-derived constraints

The canonical front sheet already supplies the correct broad triangular penguin silhouette: tall trident crown, white chest wedge, large contiguous flippers, compact orange feet, and a stable centered baseline. The Mega version must retain these exact anatomical masses and should not be narrowed or surrounded by detached ornament. Its minimal Mega changes will be a restrained crown extension, connected gold shoulder/flipper edging, and a small continuous chest-armor accent using the existing navy, cyan, white, gold, and outline colors.

The canonical rear sheet is tightly cropped and dominated by the back of the head and upper torso. The Mega rear must preserve that genuine player-side crop and orientation. Matching crown extensions and connected shoulder edging may be added, but no face, white chest wedge, forward-pointing beak, detached wings, or full-body replacement is permitted. Front and back additions must use the same motif and palette.

#### Empoleon coordinate findings

In each front frame, the crown occupies roughly x=29–55 / x=109–137 and y=3–27, while the canonical shoulder blades and upper flipper edges already create a strong connected armored line. Mega accents must remain inside or directly adjacent to those masses. Safe changes are a one- to three-pixel extension of the existing crown tips, a narrow gold line embedded along the upper shoulder blades, and a compact gold/cyan chest clasp around the upper white wedge. The broad flipper outlines, white breast, feet, and body width must remain unchanged.

In each rear frame, the crown and shoulder blades occupy approximately x=19–60 / x=91–140 and y=2–46. The native rear is deliberately close-cropped and hides the face and white chest. Matching Mega changes must therefore be limited to the rear crown tips, a connected gold edge inside the blue shoulder blades, and at most a small centered navy/cyan back plate. No front anatomy or detached ornament should be introduced.

#### Empoleon indexed-candidate review

The rebuilt 160×80 indexed sheets preserve canonical Empoleon anatomy in both animation frames. The front remains immediately recognizable through its trident mask, white breast, flipper silhouette, and feet; the restrained crown reinforcement, connected shoulder trim, and compact chest clasp read as one coherent imperial armor motif rather than detached decoration. The rear sheets remain unambiguously back-facing, retain the canonical close crop and cape-like body mass, and echo the front through gold crown/shoulder trim and a small centered back clasp. The candidate is suitable for production replacement and emulator-scale validation.

#### Torterra indexed-candidate review

Both indexed animation sheets retain Torterra's canonical quadrupedal anatomy, head, shell rim, tree, and baseline. The front uses a restrained stone-spire and darker shell treatment without obscuring the face or changing body proportions. The rear is unmistakably back-facing and repeats the same tree, dark shell, and three connected stone spires. Palette conversion leaves the silhouette and internal separation readable at native DS scale, so this candidate is suitable for production replacement and emulator validation.

#### Infernape indexed-candidate review

The front indexed sheet preserves Infernape's canonical face mask, flame crown, compact torso, long limbs, tail, and fighting pose in both frames. The staff remains thin and crosses the raised hand rather than floating independently. The rear sheet retains the canonical player-side close crop, back and shoulder anatomy, and flame mass; in both frames the short visible staff section terminates at the hand/forearm and reads as held. The restrained indigo/gold accents survive palette conversion without becoming a replacement costume. This candidate is suitable for production replacement and emulator validation.
