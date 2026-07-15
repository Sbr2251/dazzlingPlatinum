# V8 Native Sprite Gate Review

V8 resolves the quantitative failures that blocked v7. All six sheets are **160×80 indexed PNGs**, use indices **0–15**, have complete normal and shiny 16-color JASC palettes, contain valid four-byte key files, maintain safe left/top/right margins, keep each frame as one connected component, and pass the animation-difference bounds. Torterra’s new fortress front lowers its ordinary-base silhouette overlap below the strict threshold, and Empoleon’s rebuilt rear lowers front/rear silhouette overlap from 0.9485 to 0.6021. The complete machine report is `target-native-v8-nearest-validation.json`.

## Static visual gate

At native-grid scale, all three designs now read as intentional Mega evolutions rather than recolored base starters. Torterra has a high asymmetrical fortress shell, split tree canopy, forward horn mass, blade parapets, and an upward armored tail. Infernape has compact Monkey King anatomy, gold armor, a continuous diagonal staff, a large flame mane, and substantially reconstructed rear anatomy. Empoleon has a narrow emperor body, crown, asymmetric blade-wing silhouette, layered mantle, and a true rear view with exposed nape and rear clasps. No frame contains a floating one-pixel component after the v8 native cleanup pass.

## Rejection retained after paired-frame inspection

V8 is **not promoted** despite passing static and numeric gates. The paired review shows that frame 1 of every sheet is produced by translating the complete sprite. This makes planted feet slide over the battle floor and makes large props—including Torterra’s fortress, Infernape’s staff, and Empoleon’s blade-wing—move as rigid pasted cutouts rather than animate. The issue is most visible in Torterra rear and both Empoleon views, where the feet shift by one pixel while the full body remains unchanged.

## V9 correction contract

V9 must preserve the accepted v8 first frames and replace only animation construction. Feet and lower legs must remain anchored. Torterra should show a subtle upper-shell/canopy heave while all four feet remain fixed. Infernape should keep the staff grip and feet fixed while the upper mane and flame tips flex by one pixel. Empoleon should keep both feet fixed while the upper torso, nape plume, and outer wing tips make a restrained one-pixel breathing/feather motion. The new frames must remain single-component, retain safe margins, avoid new palette colors, and pass the existing XOR and IoU animation gates.
