# Mega Infernape — 24-Strategy Conversion Review

**Global decision: all 24 automatic conversions are rejected as final sprites.** The transformed Monkey King identity survives, but automatic resampling consistently allocates too many pixels to the mane and too few to the limbs, hands, staff grip, and face. The staff remains one physical object, yet its one-pixel diagonal shaft and outline/highlight pattern are fragile at native resolution. The design must be redrawn around a deliberately thick staff and larger grip clusters.

| Strategy family | Front result | Rear result | Decision |
|---|---|---|---|
| Nearest 58–70 | Hard clusters preserve flames; `ne66` best preserves face and armor, but diagonal staff is jagged | `ne66` keeps stance and both grip regions readable | Trace pose only |
| Box 58–70 | `bo66` gives the cleanest color masses but softens the lower grip | `bo66` is coherent but staff/hand contrast is weak | Color reference only |
| Bilinear 58–70 | Mane and torso merge; small gold armor clusters disappear | Rear becomes a cream head over a dark stick figure | Reject |
| Lanczos 58–70 | Adds noisy edge pixels and false mane details | Staff flame and hand boundaries become unstable | Reject |
| Staged 58–70 | `st66` creates the strongest game-like outline and clearest feet | `st66` has the best rear silhouette, but outline swallows forearm detail | Primary tracing reference |
| Mask/color 58–70 | `mk66` balances color and hard silhouette | `mk66` is usable as a secondary silhouette source | Secondary tracing reference |

**Required reconstruction changes:** shrink the mane by roughly 20%; enlarge face, hands, forearms, and feet; use a two-pixel-thick red shaft over most of its length; make each grip a 3×3-or-larger blue cluster visibly wrapping the shaft; eliminate the apparent doubled-staff highlight; compress each end flame into a connected 5–8-pixel cluster; broaden the torso; and preserve a clear negative-space gap between tail and staff. `st66`, `mk66`, and `ne66` are references only, never production assets.
