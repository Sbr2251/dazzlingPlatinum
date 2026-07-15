# V9 Native Acceptance Review

V9 preserves the accepted v8 first frames and replaces every rigid translated second frame with an **anchored one-pixel upper-body heave**. The lower-leg and foot rows remain fixed. This removes the visible floor sliding that caused v8’s rejection without changing any Mega design, front/rear anatomy, palette, or frame footprint.

## Technical results

The complete machine-readable report is `target-native-v9-nearest-validation.json`. Every sheet passes the following checks: 160×80 indexed PNG structure; palette indices constrained to 0–15 with transparent index 0; complete normal and shiny 16-color JASC palettes; valid four-byte key files; nonempty frames; safe left, top, and right margins; one connected foreground component per frame; animation XOR above 30 pixels; animation silhouette IoU between 0.80 and 0.99; front/rear silhouette IoU below 0.80; and Mega/base front silhouette IoU below 0.72.

| Species | Front animation XOR / IoU | Rear animation XOR / IoU | Front–rear IoU | Mega–base front IoU |
|---|---:|---:|---:|---:|
| Torterra | 74 / 0.9867 | 177 / 0.9566 | 0.7235 | 0.6431 |
| Infernape | 300 / 0.8944 | 296 / 0.8674 | 0.4164 | 0.4916 |
| Empoleon | 187 / 0.9324 | 203 / 0.9245 | 0.6021 | 0.5711 |

## Reject-first visual verdict

The paired evidence `target-native-v9-visual-evidence/v9_animation_review.png` passes the visual motion gate. Torterra’s canopy and fortress rise subtly while all four feet remain planted. Infernape’s upper mane, staff-hand region, and torso heave without moving either foot or breaking the continuous diagonal staff. Empoleon’s crown, nape, torso, and blade-wing move as a restrained breath while both taloned feet remain fixed. No one-row alpha gap or disconnected fragment is visible at any motion anchor.

The static designs continue to pass at native and gridded scales. Torterra reads as a fortress-tree Mega rather than ordinary Torterra. Infernape reads as the approved armored Monkey King with flame mane and staff. Empoleon reads as a crowned blade-emperor with an asymmetric front silhouette and reconstructed rear mantle. V9 is therefore the first candidate accepted for **production promotion and ROM/emulator validation**. It is not yet considered complete until repository asset validation, ROM builds, and unobscured in-game evidence also pass.
