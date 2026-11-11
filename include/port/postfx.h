#ifndef POKEPLATINUM_PORT_POSTFX_H
#define POKEPLATINUM_PORT_POSTFX_H

// PostFX: PC-only full-screen effects, applied in the simulator's final
// compositing post pass (subprojects/libntr, shaders/post_fragment.glsl), so
// they work with both the CPU and GPU 2D paths. See docs/postfx.md.
//
// Call from game code on the frame the effect should start; the simulator
// decays it over the given number of rendered frames. All calls are cheap
// (they only write a state struct) and are no-ops visually once expired.
// Coordinates: x in [0,255], y in [0,383] over the combined display as the
// player sees it (main/top screen y 0-191, sub/bottom screen y 192-383),
// origin at the top-left. Strength/amount values are 0.0-1.0 unless noted.

#ifdef __cplusplus
extern "C" {
#endif

// Expanding radial shockwave ring centred at (x, y): distorts the picture
// as the ring passes. strength ~0.5 is a strong shove; frames ~25.
void PostFX_Shockwave(int x, int y, float strength, int frames);
// Full-screen vignette tinted (r, g, b) (each 0.0-1.0): darkens/tints
// towards the edges by amount, fading out over frames.
void PostFX_Vignette(float r, float g, float b, float amount, int frames);
// Radial (zoom) blur streaking away from (x, y). amount ~0.3 is strong.
void PostFX_ZoomBlur(int x, int y, float amount, int frames);
// Chromatic aberration: red/blue fringing growing towards the edges.
void PostFX_ChromaticAberration(float amount, int frames);
// Bloom-ish glow: bright areas bleed light. amount ~0.6 is strong.
void PostFX_Glow(float amount, int frames);
// Screen shake: random per-frame offset of up to amount * 8 display pixels.
void PostFX_Shake(float amount, int frames);
// Cinematic letterbox: black bars at the top and bottom of the main (top)
// screen, each amount * main-screen-height tall (amount 0.14 is a strong
// cinema bar). Drive it per frame with frames=2 to animate the slide.
void PostFX_Letterbox(float amount, int frames);
// Which screens effects apply to: 0 = both, 1 = main/top only (the
// default: the bottom touch screen stays clean during cinematics),
// 2 = sub/bottom only. The letterbox is always on the main screen.
void PostFX_SetRegion(int screen);
// Key Stone cut-in, driven per frame with frames=2 like the letterbox:
// a diagonal rainbow strip sweeps across the main screen carrying a
// glowing Key Stone, with a rainbow beam from the stone to (x, y).
// progress 0-1 is the sweep position; alpha 0-1 fades it in/out.
void PostFX_CutIn(float progress, float alpha, int x, int y);
// Localised radial glow centred at (x, y): a soft rainbow halo that
// decays over frames. Good for picking out one sprite or icon.
void PostFX_GlowAt(int x, int y, float amount, int frames);
// Title card, driven per frame: a dark violet gradient band with
// rainbow edges slides across the middle of the main screen. Pair it
// with a printed "MEGA <NAME>!" line (the shader draws no text).
void PostFX_TitleCard(float progress, float alpha);
// Cancel every active effect on the next rendered frame.
void PostFX_Clear(void);

#ifdef __cplusplus
}
#endif

#endif // POKEPLATINUM_PORT_POSTFX_H
