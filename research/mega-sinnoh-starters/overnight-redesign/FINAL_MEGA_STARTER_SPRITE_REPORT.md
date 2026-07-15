# Pokémon Dazzling Platinum: Final Mega Sinnoh Starter Sprite Report

**Author:** Manus AI  
**Final candidate:** target-native v9  
**Status:** Accepted, promoted, compiled, and rendered through DeSmuME  

## Final result

The three Mega Sinnoh starters have been rebuilt as **new Mega designs**, not recolored or lightly edited base starters. Mega Torterra now uses a low, armored fortress body under an enlarged tree canopy; Mega Infernape uses the approved armored Monkey King direction with a continuous two-handed staff and flame mane; Mega Empoleon uses a crowned blade-emperor silhouette with broad shoulder roots, mantle planes, and independently reconstructed rear anatomy. The accepted v9 artwork preserves v8’s approved static designs and replaces its rejected sliding animation with planted-foot upper-body motion.[1]

![Final six-view native DeSmuME evidence](v9-emulator-evidence/v9_final_native_emulator_contact_sheet_robust.png)

The image above is not a composited mock-up. Each view was loaded from its compiled Pokémon graphics archive member and rendered through the Nintendo DS graphics path in DeSmuME. A reversible Rowan-intro test harness exposed one production frame at a time; the source, palettes, sheets, and clean ROM were restored after every instrumented build. The final integrity audit shows no residual diff in `rowan_intro_app.c`.[2]

| Species | Final Mega direction | Front-view proof | Rear-view proof | Final visual verdict |
|---|---|---|---|---|
| **Torterra** | Fortress-tree body, broad shell armor, crown-like canopy, enlarged forward plate | The canopy, forward armor, and massive low body separate it materially from base Torterra | The rear exposes shell mass, rear armor, and a distinct tree/plate arrangement rather than mirroring the front | Accepted |
| **Infernape** | Armored Monkey King, flame mane, continuous diagonal staff, enlarged hands and feet | The staff, mane, armor, and martial stance remain readable at native scale | Rear mane, shoulders, hips, feet, and both staff grips are reconstructed from behind | Accepted |
| **Empoleon** | Crowned emperor, angular blade wings, mantle, thick shoulder roots | The three-prong crown, asymmetric blade planes, and emperor torso are clear | Rear mantle and wing overlap form a separate silhouette without copying the front | Accepted |

## Native-format and animation gates

Every production sheet is a **160×80 two-frame indexed PNG** using palette indices 0–15, transparent index 0, complete normal and shiny sixteen-entry JASC palettes, and matching four-byte key files. Every frame has safe margins, a single connected foreground component, nonempty content, sufficient frame-to-frame change, and bounded animation silhouette overlap.[1] [3]

| Species | Front animation XOR / IoU | Rear animation XOR / IoU | Front–rear silhouette IoU | Mega–base front IoU | Result |
|---|---:|---:|---:|---:|---|
| Torterra | 74 / 0.9867 | 177 / 0.9566 | 0.7235 | 0.6431 | Pass |
| Infernape | 300 / 0.8944 | 296 / 0.8674 | 0.4164 | 0.4916 | Pass |
| Empoleon | 187 / 0.9324 | 203 / 0.9245 | 0.6021 | 0.5711 | Pass |

The animation review was deliberately reject-first. V8 was rejected even after its static sprites passed because every second frame translated the whole body and visibly slid the feet. V9 instead applies a one-pixel heave only above a species-specific lower-body anchor. Torterra’s feet remain planted under the moving canopy and fortress; Infernape’s feet and staff continuity remain fixed while the upper body breathes; Empoleon’s talons remain fixed while the crown, nape, torso, and wings heave.[1] [4]

## Production assets and ROM verification

The accepted assets were promoted to the following production directories. Only the six sheets, their key files, and normal/shiny palettes were replaced. Temporary emulator instrumentation was fully removed before the final clean build.[2]

| Species | Production directory | Front SHA-256 | Back SHA-256 |
|---|---|---|---|
| Torterra | `res/pokemon/torterra/forms/mega/` | `48714ff71ec975436d266953cae11d1eb86a2725c7ec55e3e987c30a62d00f4d` | `5c1a537c4e454b2d0a82c53c8882be8dca2b2deaa69426254abcf447b41103b4` |
| Infernape | `res/pokemon/infernape/forms/mega/` | `35b7adc209ce65c65bae695e3df871ffa56e22738abb277261c0c4542a1ffad3` | `d17dfbac9cd88eab8b86c08735fb434470648a31f8cb29b032235499e0f21436` |
| Empoleon | `res/pokemon/empoleon/forms/mega/` | `6fe4f6921934db611fd36675ea579ffeec6d3cd7e872e56b14f1453fb01466c3` | `d050f76c311d3856e60a7d69d75e118a66ae8df3b573cfb0af9720f7cad09d0c` |

The production sprite validator passes all six sheets. The integration validator also passes the Mega species data, stones, abilities, typing, +100 BST increases, and graphics archive member assignments. The final clean ROM is `build/pokeplatinum.us.nds`, with SHA-256 `ff5bbee49a82f819ac6993ed4f592548d5472e1437e4503c2b9852292a21848a`.[2] [3]

## Twenty-four concrete automatic-conversion configurations

The first large experiment batch ran **twenty-four distinct conversion configurations on each species**, for seventy-two concrete outputs. Each of six pipelines was tested at target heights 58, 62, 66, and 70 pixels. All seventy-two were rejected as production assets; the best examples were retained only as shape, color, outline, or pose references. This batch established that resampling could preserve the Mega concept but could not allocate enough native pixels to the required face, limbs, grip, crown, shoulder roots, and rear anatomy.[5] [6] [7]

| ID | Concrete strategy | What it tested | Outcome |
|---|---|---|---|
| 1 | Nearest-neighbor at 58 px | Small hard-cluster reduction | Rejected: anatomy too compressed |
| 2 | Nearest-neighbor at 62 px | Medium-small hard-cluster reduction | Rejected: jagged diagonals and lost attachments |
| 3 | Nearest-neighbor at 66 px | Mid-size hard-cluster reduction | Best nearest reference, not production |
| 4 | Nearest-neighbor at 70 px | Large hard-cluster reduction | Rejected: top-heavy or border-pressured |
| 5 | Box reduction at 58 px | Small averaged color masses | Rejected: muddy material joins |
| 6 | Box reduction at 62 px | Medium-small averaged masses | Rejected: small anatomy softened away |
| 7 | Box reduction at 66 px | Mid-size averaged masses | Best color-block reference, not production |
| 8 | Box reduction at 70 px | Large averaged masses | Rejected: silhouette imbalance remained |
| 9 | Bilinear reduction at 58 px | Small smooth resampling | Rejected: severe blur and merged anatomy |
| 10 | Bilinear reduction at 62 px | Medium-small smooth resampling | Rejected: weak outlines and lost details |
| 11 | Bilinear reduction at 66 px | Mid-size smooth resampling | Rejected: soft, non-DS surface |
| 12 | Bilinear reduction at 70 px | Large smooth resampling | Rejected: composition still wrong despite detail |
| 13 | Lanczos reduction at 58 px | Small high-frequency resampling | Rejected: ringing and false pixels |
| 14 | Lanczos reduction at 62 px | Medium-small high-frequency resampling | Rejected: noisy edges and unstable rails |
| 15 | Lanczos reduction at 66 px | Mid-size high-frequency resampling | Rejected: false mane, canopy, crown, and blade detail |
| 16 | Lanczos reduction at 70 px | Large high-frequency resampling | Rejected: noise increased with no anatomy repair |
| 17 | Staged reduction at 58 px | Intermediate reduction plus hard outline | Rejected: outline consumed the smallest parts |
| 18 | Staged reduction at 62 px | Medium staged cleanup | Rejected: attachment points remained weak |
| 19 | Staged reduction at 66 px | Mid-size staged cleanup | Best tracing/outline reference, not production |
| 20 | Staged reduction at 70 px | Large staged cleanup | Rejected: oversized upper structures persisted |
| 21 | Mask/color reduction at 58 px | Small alpha-mask and color treatment | Rejected: weak boundary discipline |
| 22 | Mask/color reduction at 62 px | Medium-small mask/color treatment | Rejected: ambiguous small anatomy |
| 23 | Mask/color reduction at 66 px | Mid-size mask/color treatment | Secondary silhouette reference, not production |
| 24 | Mask/color reduction at 70 px | Large mask/color treatment | Rejected: did not solve composition or rear truth |

## Additional construction and review strategies

The project did not stop after the seventy-two automatic conversions failed. It moved through maquette, direct-native, target-raster, palette, silhouette, animation, and emulator strategies. These are separate from the twenty-four conversion configurations above.

| ID | Strategy actually exercised | Result and lesson |
|---|---|---|
| 25 | High-resolution Mega maquettes | Preserved design identity but did not survive naïve reduction cleanly |
| 26 | Direct DS-style generation | Produced usable ideation but inconsistent native anatomy and paired views |
| 27 | Target-native v1 reconstruction | Established 80×80 composition; rejected for geometric anatomy and incomplete Mega landmarks |
| 28 | Target-native v2 selective refinement | Improved Infernape and Empoleon joins; still failed holistic silhouette review |
| 29 | Target-native v3 assembly | Improved component placement; rejected after pixel diagnostics |
| 30 | Target-native v4 animation pass | Technically stronger, but later emulator review showed the art was still insufficient |
| 31 | Clean emulator v4 rejection | Prevented a technically valid but visually weak batch from being accepted |
| 32 | Target-native v5 reconstruction | Reworked anatomy and color ramps; still failed front/rear and silhouette standards |
| 33 | Target-native v6 gate-driven reconstruction | Added strict gates; rejected for Torterra fragments, Infernape grip/border defects, and weak Empoleon rear palette |
| 34 | Rocketmanga/VilliamBoom landmark contract | Converted concept references into explicit crown, staff, fortress, wing, and rear-view requirements |
| 35 | Generated species-specific front maquettes | Supplied stronger organic underdrawings than geometric polygons |
| 36 | True rear maquettes generated separately | Prevented mirrored or front-facing “back” sprites |
| 37 | Nearest native conversion branch | Retained hard pixel clusters and advanced after comparison |
| 38 | Box native conversion branch | Rejected because antialias-aware averaging softened important native clusters |
| 39 | V7 Mega/base silhouette gate | Correctly rejected Torterra as still too close to base despite otherwise stronger anatomy |
| 40 | V7 front/rear silhouette gate | Correctly rejected Empoleon’s rear outline as too similar to its front |
| 41 | V8 targeted Torterra silhouette regeneration | Created the accepted extreme fortress-tree static silhouette |
| 42 | V8 targeted Empoleon rear regeneration | Created a distinct rear wing and mantle outline |
| 43 | One-pixel-fragment cleanup | Removed isolated downsampling artifacts before indexing |
| 44 | V8 whole-sprite translated animation | Rejected because the feet visibly slid across the ground |
| 45 | V9 anchored upper-body breathing | Accepted because it preserved planted feet, components, palette, and silhouette |
| 46 | Connected-component gate | Rejected any disconnected weapon, limb, canopy, or accent fragment |
| 47 | Pixel-grid coordinate review | Exposed orphan pixels, false facial landmarks, border pressure, and muddy joins hidden by enlarged previews |
| 48 | Paired animation review sheets | Exposed sliding, stretching, grip breaks, and prop discontinuity that static checks missed |
| 49 | Base-form silhouette comparison | Prevented a “base starter plus accessories” result from passing |
| 50 | Front/rear silhouette comparison | Enforced true viewpoint reconstruction rather than mirroring |
| 51 | Semantic fifteen-color palette optimization | Preserved material separation within Gen IV palette limits |
| 52 | Production-root validation before promotion | Tested candidate structure without overwriting accepted repository assets prematurely |

## Emulator-proof strategies and failures

The emulator phase was also reject-first. Earlier contact sheets were not accepted because they were synthetic, obscured, mistimed, black, magenta-tinted, or tile-layout corrupted. The final contact sheet was produced only after every failure had a specific diagnosis and repair.[8]

| ID | Emulator strategy | Outcome |
|---|---|---|
| 53 | Reuse prior Rowan contact sheet | Rejected because it was not adequate unobscured proof |
| 54 | Fixed-count A-button capture | Rejected because boot and reveal timing were nondeterministic |
| 55 | Press-by-press checkpoint capture | Located the transition but still caught dark reveal frames |
| 56 | Raw 160×80 sheet through Rowan’s 10×10 loader | Rejected after tile-layout corruption |
| 57 | Reversible first-frame 80×80 crop | Corrected the loader’s expected frame geometry |
| 58 | One-time brightness neutralization | Failed because Rowan’s fade state reapplied black output |
| 59 | Per-frame BG2 and brightness forcing | Reached the harness but initially used the wrong brightness semantic |
| 60 | Correct neutral-brightness API | Removed the persistent black frame |
| 61 | Original palette restoration after Rowan load | Removed the intro’s intentional all-magenta Buneary reveal tint |
| 62 | Fixed-time six-ROM batch capture | Rejected when several ROMs remained at title or black frames |
| 63 | Start-aware multi-checkpoint capture | Reliably advanced into the instrumented Rowan state |
| 64 | Density-scored late-frame selection with retries | Accepted; selected a stable low-density sprite-on-black frame for each of six ROMs |
| 65 | Post-harness restoration audit | Accepted; no Rowan source diff remained and production validators passed |

## Final reject-first scorecard

| Gate | Torterra | Infernape | Empoleon | Evidence |
|---|---|---|---|---|
| Mega rather than base | Pass | Pass | Pass | Mega/base IoU and native visual review |
| Species recognition | Pass | Pass | Pass | Native and emulator contact sheets |
| Anatomy and attachments | Pass | Pass | Pass | One-component gate and pixel-grid inspection |
| True front/rear views | Pass | Pass | Pass | Front/rear IoU plus six-view emulator proof |
| Palette economy | Pass | Pass | Pass | Indexed-sheet and palette validation |
| Safe 80×80 composition | Pass | Pass | Pass | Frame bounds and edge checks |
| Animation quality | Pass | Pass | Pass | V9 paired animation review |
| Production integration | Pass | Pass | Pass | Sprite and mechanics validators |
| Compiled ROM | Pass | Pass | Pass | Clean ROM build and SHA-256 |
| Native emulator rendering | Pass | Pass | Pass | Robust DeSmuME contact sheet |

## Deliverables

The primary review artifact is `v9-emulator-evidence/v9_final_native_emulator_contact_sheet_robust.png`. The enlarged native candidate sheet is `target-native-v9-nearest-preview.png`, and paired animation evidence is `target-native-v9-visual-evidence/v9_animation_review.png`. Machine-readable gate results are in `target-native-v9-nearest-validation.json`. Final production checks are in `v9-emulator-evidence/final-production-sprite-validation.txt`, `final-production-integration-validation.txt`, and `final-integrity-audit.txt`. The clean rebuilt ROM is preserved as `v9-emulator-evidence/pokemon_dazzling_platinum_v9_clean.nds` and also exists at `build/pokeplatinum.us.nds`.

> **Final verdict:** v9 is the first batch in the overnight redesign that passes the concept, native-pixel, front/rear, palette, animation, production, ROM-build, and native-emulator gates together. No GitHub push was performed.

## References

[1]: reviews/17_v9_native_acceptance.md "V9 Native Acceptance Review"
[2]: v9-emulator-evidence/final-integrity-audit.txt "Final Production Integrity Audit"
[3]: v9-emulator-evidence/final-production-sprite-validation.txt "Final Production Sprite Validation"
[4]: target-native-v9-visual-evidence/v9_animation_review.png "V9 Paired Animation Evidence"
[5]: reviews/06_torterra_24_strategy_review.md "Mega Torterra 24-Strategy Review"
[6]: reviews/06_infernape_24_strategy_review.md "Mega Infernape 24-Strategy Review"
[7]: reviews/06_empoleon_24_strategy_review.md "Mega Empoleon 24-Strategy Review"
[8]: reviews/18_v9_emulator_capture_calibration.md "V9 Emulator Capture Calibration"
