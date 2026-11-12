# Crisp 2D upscale + hi-res text (prototype)

PC-only rendering work (lane `hiresui`). Two independent features, both off
the DS critical path and both separable from the G2 layer renderers: no
layer-rendering logic changed.

## 1. Upscaled 2D output (sharp bilinear at composite)

The 2D layer textures (256x384, native DS resolution) used to be drawn to
the window with NEAREST filtering, pixel-doubling the DS output. The
composite (`shaders/g2_fragment.glsl`) now samples BG/OBJ layer textures
through `sampleUpscaled()`:

- Mode 0 `Nearest (native)`: plain `texture()` with NEAREST filtering.
  Byte-identical to the old output.
- Mode 1 `Sharp bilinear` (opt-in; Nearest is the default): LINEAR filtering with the
  sample position snapped towards the texel centre by the magnification
  factor (`fwidth`-based sharp-bilinear). Pixel art and text stay crisp
  without nearest stair-stepping or bilinear blur.
- Mode 2 `Bilinear (smooth)`: plain `texture()` with LINEAR filtering.

3D is untouched: when BG0 is 3D, the composite samples the
internal-resolution 3D texture exactly as before, and
`InternalResolutionScale` behaviour is unchanged. The OBJ window mask
texture stays NEAREST (it is a mask, not an image).

Configuration (first match wins):

1. `SIM_2D_UPSCALE=0|1|2` (or `Nearest`/`Sharp`/`Bilinear`) environment.
2. The headless/lockstep default: Nearest, so regression screenshots stay
   byte-identical unless a run explicitly opts in.
3. `sim_config.ini` `[General] Upscale2DFilter=Sharp`, also in the backtick Config
   window ("2D Upscale"). Default config value is 1 (Sharp).

FPS cost is one `fwidth` + a few ALU ops per composite sample; see the
lane STATUS for measurements. An xBR/hqx-style scaler is a natural next
step behind the same `upscaleMode` uniform (needs neighbour taps in
`sampleUpscaled`, no other plumbing).

## 2. High-res dialogue text (prototype)

Flag: `sim_config_prj.ini` `[General] HiResText=true` (backtick
"pokeplatinum Config" window, or env `SIM_HIRESTEXT=1`). Default off.

The DS text pipeline is completely untouched: glyphs are still rendered
into BG window tiles by `src/render_text.c`, so positions, colours,
scrolling, text speed and control codes behave exactly as before. When
the flag is on, the text printer additionally reports each glyph it
prints for `FONT_MESSAGE` on a wide main-screen window (the field and
battle dialogue box) to the simulator (`include/port/hirestext.h`,
implemented in libntr `sim_hirestext.cpp`). The simulator expands the
glyph at 4x (same font design, same palette colours; background pixels
stay transparent so the DS dialogue box shows through) into a
1024x1536 combined-display buffer and draws it over the composited
frame just before the PostFX pass. Window clear, scroll-up and
end-of-message are mirrored so the overlay tracks the DS text.

Prototype limits, and what generalizing takes:

- Main screen, vertical unswapped layout only. Other layouts skip the
  overlay (DS text still shows). Supporting them is a UV-mapping
  exercise in `HiResText_DrawOverlay` against `screenquads` layouts.
- Dialogue windows only (width >= 16 tiles). Menus use other fonts and
  narrower windows; generalizing = drop/adjust the gate in
  `HiRes_IsDialogueWindow` and handle several concurrent windows
  (the simulator buffer is already full-screen, so overlaps work, but
  window open/close must clear rects like dialogue EOS does).
- BG scroll offsets are assumed 0 (true for dialogue BGs); affine or
  scrolled text BGs would need the offset added per glyph.
- The 200% glyph-table scale mode and the scroll arrow are not mirrored.
- Glyphs are nearest-expanded to 4x on the CPU and the overlay texture
  is LINEAR-sampled at window scale. A vector font or a pre-baked
  anti-aliased 4x atlas (generated from `res/fonts/*.png` at build
  time) would plug into the same reporting path unchanged.

AI-assisted (Metamate)
