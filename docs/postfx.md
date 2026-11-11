# PostFX API

PC-only full-screen screen effects for cinematics (Mega Evolution, Totem
flare-up, big hits). The games composited frame (both DS screens, CPU or GPU
2D path) is rendered into an offscreen texture in the simulator
(`subprojects/libntr`, `SIM_Render` in `libraries/sim/src/sim_main.cpp`) and
drawn to the window through `shaders/post_fragment.glsl`. Effects therefore
sit on top of everything the game draws, cost one fullscreen pass, and show
up in headless screenshots exactly as in the window.

## Calling it

```c
#include "port/postfx.h"

PostFX_Vignette(0.10f, 0.02f, 0.22f, 0.65f, 24);   // dark violet edges, 24 frames
PostFX_Shockwave(128, 90, 0.8f, 26);               // ring bursting from the battler
PostFX_Shake(0.7f, 14);
PostFX_ChromaticAberration(0.6f, 20);
PostFX_Glow(0.5f, 30);
PostFX_ZoomBlur(128, 90, 0.35f, 22);
PostFX_Clear();                                    // cancel everything now
```

- Header: `include/port/postfx.h`. Implementation: `PostFX_*` (extern "C")
  in libntr `sim_main.cpp`; game code only writes a small state struct.
- Coordinates are combined-display pixels as the player sees them:
  x 0-255, y 0-383 (main/top screen y 0-191, sub/bottom screen y 192-383),
  origin top-left. A battler on the top screen is usually near (64, 90)
  (enemy) or (175, 120) (player); measure from a screenshot when in doubt.
- `frames` counts rendered frames (60 per second at normal speed; fewer
  wall-clock frames under fast-forward, which is what "scales with
  fast-forward" means here). Strengths fade linearly to zero over `frames`,
  except the shockwave, whose ring keeps expanding while it fades.
- Trigger once at the beat; do not re-trigger every frame. For a held look
  (e.g. a vignette for a whole cinematic), pass a long `frames` and call
  `PostFX_Clear()` when the beat ends.
- Shake is a deterministic per-frame hash, so headless runs with the same
  seed reproduce the same frames.
- All effects compose in one pass; calling several at once is the intended
  use (e.g. shockwave + shake + chromatic aberration on a burst).

## Effects

| Call | Look |
|---|---|
| `PostFX_Shockwave(x, y, strength, frames)` | Expanding ring that shoves the picture as it passes |
| `PostFX_Vignette(r, g, b, amount, frames)` | Edges mix towards the colour by amount |
| `PostFX_ZoomBlur(x, y, amount, frames)` | Radial streak blur away from the centre |
| `PostFX_ChromaticAberration(amount, frames)` | Red/blue fringing towards the corners |
| `PostFX_Glow(amount, frames)` | Bloom-ish bleed of bright areas |
| `PostFX_Shake(amount, frames)` | Random offset up to amount * 8 display pixels |

AI-assisted (Metamate)
