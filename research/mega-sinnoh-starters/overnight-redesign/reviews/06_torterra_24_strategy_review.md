# Mega Torterra — 24-Strategy Conversion Review

**Global decision: all 24 raw conversions are rejected as final sprites.** This batch successfully proves that the source is visually Mega rather than base-form, but it also exposes a fundamental composition failure that resampling alone cannot solve: the tree occupies roughly half the total height while the face and front legs become tiny. Increasing target height improves detail but worsens the top-heavy silhouette; reducing height makes the head unreadable. Therefore the final sprite needs target-native redrawing, not further whole-image reduction.

| Strategy family | Front result | Rear result | Decision |
|---|---|---|---|
| Nearest 58–70 | Retains hard clusters but creates noisy canopy and trunk holes; `ne66` is the least damaged front | `ne66` preserves spikes and rear shell best but is still top-heavy | Retain only as shape tracing reference |
| Box 58–70 | Smoother color blocks; `bo66` has the best facial/gem readability | `bo66` has the clearest rear mountain mass | Retain as color-block reference |
| Bilinear 58–70 | Over-softens boundaries before palette mapping; loses eye and leg separation | Rear shell becomes muddy | Reject |
| Lanczos 58–70 | Adds false high-frequency pixels around canopy and shell | Produces noisy trunk/spike interfaces | Reject |
| Staged 58–70 | Strong outline helps separation; `st66` is most game-like | `st66` provides the clearest silhouette but outline consumes small details | Retain as outline reference only |
| Mask/color 58–70 | Better interior color continuity but weaker boundary discipline than staged | Rear remains readable at `mk66` | Secondary reference only |

**Required reconstruction changes:** reduce canopy width and height by approximately one quarter; shorten the trunk; enlarge the head and forward plate; thicken all four visible legs; reduce shell spikes to three major clusters per view; keep the shell low and broad; and draw at 80×80 from the outset. `st66`, `bo66`, and `ne66` are the only candidates worth tracing. None should be promoted directly.
