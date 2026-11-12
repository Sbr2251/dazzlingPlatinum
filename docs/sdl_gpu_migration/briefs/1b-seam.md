# 1b. Render-backend seam: every OpenGL call behind an interface

Model: Muse (tbh-1005 or tbh-1015). Tree name: `seam`. Read `PLAN.md` and `briefs/COMMON.md` first.

## Plan v2 changes (read first)

- **Redo**, do not rebase: the saved patch conflicts with today's `sim_main.cpp`, `sim_g2.cpp`, `sim_g2_gpu.cpp`
  and never compiled. Start from current `main` **with workstream 1a merged** (write against SDL3). Read the saved
  interface header (`include/simulator/sim_render_backend.hpp` inside `wip/seam-libntr.patch`) and the saved
  `render_gl/` files as reference only.
- Tree: `tools/sdl_gpu_migration/make_worktree.sh seam` (no patch). Ignore `wt_run.sh` below.
- The interface must additionally express everything added since v1 (PLAN.md, "What changed since plan v1"):
  9. **Display capture**: "re-render the main engine (2D + 3D) into a capture target of size W x H, blend with
     source B per DISPCAPCNT (mode, EVA/EVB), and deliver RGB555 pixels to a CPU buffer the caller writes into
     emulated VRAM". The OpenGL backend does it synchronously today; the interface must allow a backend to deliver
     the result one frame later at a fixed point (PLAN.md, "Capture on SDL GPU"). Also the VRAM display mode.
  10. **Hi-res text overlay**: a pass after the 2D composite and before the post pass that draws a list of glyph
      quads from a glyph texture (`sim_hirestext.cpp`).
  11. **2D sampling mode** per composite (`Upscale2DFilter`: Nearest / Sharp bilinear / Bilinear) and the scale
      uniform the sharp mode needs.
  12. **GPU 2D layer passes**: each BG layer pass and the per-sprite OBJ draws (scissored, depth-tested, lowest OAM
      index wins) into layer targets, plus the OBJ-window mask target; both engines; the CPU path's layer-image
      upload alternative.
  13. **PostFX** over an offscreen frame with the screen-region mask, letterbox, cut-in and title-card parameters
      (`include/port/postfx.h`).
- The FBO-rebinding bug class (a pass restoring framebuffer 0 instead of the previous target) must be impossible by
  construction: every pass names its target.
- Verification: the full gate set in `briefs/COMMON.md` with `SIM_RENDERER=gl` (pixel-identical to the pre-seam
  build: every scenario passes against the existing references, `--compare-renderers` passes), `--compare-backends`
  with `gl` on both sides, the Mac suite, and the grep proof.

## Resume state

Create the tree with the saved work applied:
`tools/sdl_gpu_migration/make_tree.sh seam --libntr docs/sdl_gpu_migration/wip/seam-libntr.patch`

The patch is a mid-edit snapshot and **does not compile**. It contains `include/simulator/sim_render_backend.hpp`
(the interface), `libraries/sim/src/sim_render_backend.cpp`, `libraries/sim/src/render_gl/` (OpenGL backend: core,
3D, GPU 2D), a `render_gpu/` stub, the removal of `sim_g3_GlRenderer.*`, and 15 partly converted files. Known
problems: `libraries/sim/src/meson.build` still lists the deleted file and not the new ones; the previous agent
stopped while fixing the `GX_CULL_FRONT` case of the cull-mode switch in the OpenGL 3D backend.

Start by reading the interface header critically against the requirements below. You may redesign it: nothing
depends on it yet, and three wave-2 workstreams will. Then make the tree compile, commit, and continue.

If workstream 1a (SDL3 port) has already been merged into the baseline you start from, ignore the SDL2 remarks
below and write against SDL3.

## Task

Today the simulator calls OpenGL directly, in immediate-mode style with global state, from `sim_main.cpp`
(`SIM_RenderInit`, `DrawEngine`, `PostFX_TickAndDraw`, `SIM_Render`, `SIM_SetInternalResolution`,
`SIM_PostRenderVBlank`, `SIM_DebugFrame`), the 3D files (`sim_g3_*`), the 2D files (`sim_g2.cpp`, `sim_g2_gpu.cpp`),
the headless files (readback) and `sim_gui.cpp` (ImGui). PLAN.md, "How the renderer works today", has the map.

Create the seam a second backend (SDL3 GPU API) will plug into, and move the existing OpenGL code behind it as the
first backend, so both backends can live in one binary and be chosen at startup. This is a behaviour-preserving
refactor.

Interface requirements:
1. Implementable on the SDL3 GPU API (read `SDL_gpu.h` first): no global state; draws inside render passes on
   explicit targets; pipeline state chosen per draw; uniforms pushed as byte blocks per draw; texture uploads in
   copy passes that cannot nest in a render pass; readback is a download and a wait; the swapchain texture is
   acquired per frame and may be BGRA. The game issues 3D draws all through the frame while OpenGL keeps the 3D
   framebuffer bound; the interface must not expose that. Express 3D work as calls a backend may execute
   immediately (OpenGL) or record and replay at frame end (GPU): begin 3D frame, submit a draw with fully specified
   state (texture handle, wrap modes, polygon mode, fog parameters, cull mode, depth function, depth write,
   blending, target screen viewport), clear, end. The cull/depth `gl*` calls in `sim_g3_CommandHandler.cpp` should
   become unnecessary once each draw carries its state; prove that by A/B before deleting them.
2. Backend-neutral handles for 3D textures (create, update pixels, destroy).
3. 2D compositing as data: "composite engine E into the frame at this viewport, given these layer images, these
   register values, and the 3D colour target as BG0", for the CPU-layer path and the GPU 2D path. Uniform sets
   become plain structs filled by backend-neutral code. DS-emulation logic stays outside the backend.
4. Post pass and present: PostFX parameters as one struct; present as one call. Readback as a call returning RGBA8
   pixels top-down, used by `SIM_DebugFrame`, `sim_headless.cpp` and `sim_headless_control.cpp`.
5. ImGui backend init, new-frame and render hidden behind the interface.
6. Internal-resolution changes, window resize, vsync interval, and the "3D on the top or bottom screen" viewport
   choice (`POWCNT` bit 15) go through the interface.
7. `SIM_RENDERER=gl|gpu`, read once at startup, default `gl`. A stub `gpu` backend prints that it is not implemented
   and falls back to `gl`. The interface lives in one header with the contract written at the top: which thread
   calls what, the frame lifecycle in order, who owns pixel buffers. Wave-2 agents work from that header alone.
8. Afterwards no file outside `render_gl/`, glad and the vendored ImGui OpenGL backend includes GL headers or calls
   `gl*`. Prove it with grep.

Rules:
- Behaviour-preserving. Do not fix rendering bugs you notice; list them.
- Workstream 1a converts every SDL call in the same files. Do not edit, move or reformat lines containing `SDL_`
  calls unless unavoidable; leave window creation, the event loop, input, frame pacing and audio where they are.
  When a block you move contains an `SDL_GL_*` call, move it as-is and list it in your report.
- Stay inside `libraries/sim` and `include/simulator`. Do not change headers the whole game includes. The
  `PostFX_*` C functions keep their signatures.
- New sources go into `libraries/sim/src/meson.build`.
- The OpenGL path must not get measurably slower: no per-draw heap allocation; one virtual call per draw is fine.

## Verification (required)

1. The tree builds.
2. Lockstep A/B against the reference binary, decoded pixels, for `SIM_G2_GPU=0` and `1`: 30+ checkpoints through
   boot, the intro's 3D scenes and the title, plus the new-game path. Zero differing pixels.
3. Both scenarios pass. The lockstep `screenshot` command and `SIM_HEADLESS_SHOT_AT` still produce correct images.
4. `SIM_RENDERER=gpu` prints the fallback notice and runs on OpenGL.
5. The grep proof for requirement 8.
6. Frame rate against the reference for the same run (`SIM_DEBUG_EXIT_FRAME` prints fps; the machine is noisy,
   report both numbers).

Report additionally: the interface header path, a ten-line summary of the frame lifecycle, the moved `SDL_*` lines,
and every OpenGL-specific assumption the GPU backend authors must know (bottom-left origin, clamp-to-border,
texture-unit conventions, state leaking between passes, clears at odd times).
