# 2b. GPU backend: the 2D compositor

Model: Muse (tbh-1005 or tbh-1015). Tree name: `gpu2d`. Starts after wave 1 is merged. Read `PLAN.md` and `briefs/COMMON.md` first, then
the interface header from workstream 1b (`include/simulator/sim_render_backend.hpp`) and the foundation guide from
workstream 1c (`libraries/sim/src/gpu/README.md`). Those two documents are your contract; if either is missing
something you need, tell the integrator instead of working around it in your own files.

## Plan v2 changes (read first)

- Port the **current** `g2gpu_*.glsl` and `g2_fragment.glsl`: per-sprite scissored OBJ draws with a depth buffer
  (lowest OAM index wins), WIN0 > WIN1 > OBJ window > outside, BG + OBJ mosaic, OBJ extended palettes, bitmap OBJ
  with per-sprite alpha, XLU sprite blending, comparison-based sign extension (no signed-shift tricks: Apple's
  compiler differs). These replace the v1 description below where they conflict.
- `Upscale2DFilter` (Nearest default, Sharp bilinear, Bilinear) is sampled in the composite shader; Nearest must be
  the exact pre-upscale sampling.
- Display mode "VRAM" (captured image shown from emulated VRAM) goes through your path; capture itself is 2c's.
- Targets: 0 differing pixels against `gl` for both 2D paths (`run.py --compare-backends`, with `SIM_G2_GPU=0` and
  `1`), and `--compare-renderers` still passing under `gpu`.

## Task

Implement the 2D compositing part of the `gpu` render backend on the SDL3 GPU API: both paths the OpenGL backend
has, with identical output. Unlike 3D, the 2D paths are integer and nearest-sampled arithmetic, so the target is
**zero differing pixels** against the OpenGL backend.

You own: the 2D files under `libraries/sim/src/render_gpu/` (suggested `sim_render_gpu_g2.cpp` and
`sim_render_gpu_g2gpu.cpp`) and the ported shaders (`shaders/g2_*.glsl`, `shaders/g2gpu_*.glsl` to GLSL 450). Do
not edit the interface header, the foundation library, or the files of workstreams 2a and 2c.

The two paths:
1. **CPU layers** (`SIM_G2_GPU=0`): `sim_g2.cpp` rasterises each BG and OBJ layer of an engine into RGBA images.
   The backend uploads up to four BG images, five OBJ priority images and the OBJ-window image, and draws one quad
   per DS screen with the `g2` shader, which applies layer priorities and order, the blend registers (`BLDCNT`,
   `BLDALPHA`, `BLDY`), windows (`WINOUT`, OBJ window), the backdrop colour and master brightness. BG0 may be the 3D
   colour target from workstream 2a instead of a CPU image (`bg0as3d`), including the DS special case where
   translucent 3D pixels blend with the layer below whatever the blend mode is.
2. **GPU layers** (`SIM_G2_GPU=1`, the default): `sim_g2_gpu.cpp` uploads raw DS memory as integer textures
   (BG VRAM and OBJ VRAM as R8_UINT, extended palettes, OAM as R16_UINT, palettes as R16_UINT) and the
   `g2gpu` fragment shader decodes tiles, affine backgrounds and sprites with `texelFetch`, driven by many integer
   uniforms and uniform arrays (scroll offsets, affine parameters, control registers). It falls back to the CPU
   path per engine for features it does not support; keep that fallback.

Points that need care:
- Uniforms: OpenGL sets dozens of individual uniforms that persist between draws. SDL GPU takes a block of bytes
  per draw. Define one std140 block per shader (the interface from 1b should already express the parameters as
  plain structs), and check array layout end to end: std140 pads every array element of `int` or `float` to 16
  bytes, which silently scrambles arrays if the C++ struct does not match.
- Integer textures cannot be filtered and need `usampler2D` with `texelFetch`; bind them with a nearest sampler.
- Upload cost: the GPU path re-uploads VRAM-sized textures; upload only what changed if the OpenGL path does, and
  route every upload through the frame's upload queue (no uploads inside a render pass).
- Orientation: each DS screen is drawn into its half of the composited frame; OpenGL's bottom-left origin is baked
  into the current vertex data and texture coordinates (`sim_screenquads.cpp`). Use the foundation's coordinate
  helpers and verify with a screen that is asymmetric in both axes.
- The window shows the screens in three layouts (vertical, horizontal, large) with optional screen swap; all must
  match.
- Sub-engine ("DB") registers mirror the main engine's; both engines go through the same code with a flag.

## Verification (required)

1. `tools/dazzling/render_compare/render_compare.py --a SIM_RENDERER=gl --b SIM_RENDERER=gpu` over every tour, once
   with `SIM_G2_GPU=0` and once with `SIM_G2_GPU=1` in both configurations. For checkpoints without 3D content the
   result must be zero differing pixels; where 3D is visible, mask or account for the 3D layer's differences
   (workstream 2a reports those) and the 2D layers must still be exact.
2. The 2D-heavy tours specifically: boot logos and fades (master brightness, alpha blends), the intro's blended
   scenes, menus on both screens (bag, party, Pokedex, options, town map), the naming screen, text boxes over the
   field, battle interface, mosaic and window effects.
3. All three screen layouts and swapped screens (settings in `sim_config.ini`) for at least one tour.
4. Both scenarios pass with `SIM_RENDERER=gpu` (needs 2a and 2c merged; until then say what you could run).
5. Frame rate against the OpenGL backend for the same lockstep run, for both 2D paths; report all four numbers.
