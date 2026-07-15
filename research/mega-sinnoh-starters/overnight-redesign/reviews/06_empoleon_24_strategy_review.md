# Mega Empoleon — 24-Strategy Conversion Review

**Global decision: all 24 automatic conversions are rejected as final sprites.** This batch has the strongest immediate Mega readability of the three species: the emperor torso, mantle, crown, and paired blade wings survive reduction. However, the current composition is still too narrow through the body, too dependent on one-pixel gold rails, and too dominated by long triangular wing planes. At true size the crown reads as fragile antennae rather than a heavy integrated crest.

| Strategy family | Front result | Rear result | Decision |
|---|---|---|---|
| Nearest 58–70 | `ne66` preserves the crown and wing edges but retains jagged one-pixel gold rails | `ne66` keeps the rear mantle and shoulder attachments readable | Primary shape reference |
| Box 58–70 | `bo66` gives the cleanest torso and mantle blocks; small gold structures soften | `bo66` has the most coherent rear color masses | Primary color reference |
| Bilinear 58–70 | Crown and toes blur into weak clusters; wing/body boundary loses authority | Rear mantle becomes soft and generic | Reject |
| Lanczos 58–70 | Edge ringing creates stray gold/dark pixels on blades and crown | Noisy rails undermine sprite authenticity | Reject |
| Staged 58–70 | `st66` gives the strongest game-like outline and best crown legibility | `st66` has the clearest rear silhouette but over-outlines the mantle | Primary tracing reference |
| Mask/color 58–70 | `mk66` balances color and hard-edged blades | `mk66` is usable as secondary rear reference | Secondary tracing reference |

**Required reconstruction changes:** widen the torso and shoulders; shorten both blade wings by roughly 15%; attach each wing with a visibly thick shoulder block; replace one-pixel gold perimeter rails with two-pixel clusters at critical bends; merge the crown into a broad forehead plate before branching into three thick prongs; enlarge the feet; simplify the mantle to three large panels; and keep rear crown/wing geometry consistent with the front. `st66`, `bo66`, and `ne66` are tracing references only, not production assets.
