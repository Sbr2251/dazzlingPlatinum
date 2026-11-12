# 2c. GPU backend: post pass, present, readback and ImGui

Model: Sonnet. Tree name: `gpupost`. Starts after wave 1 is merged. Read `PLAN.md` and `briefs/COMMON.md` first,
then the interface header from workstream 1b (`include/simulator/sim_render_backend.hpp`) and the foundation guide
from workstream 1c (`libraries/sim/src/gpu/README.md`). Those two documents are your contract; if either is missing
something you need, tell the integrator instead of working around it in your own files.

## Task

Implement the frame skeleton of the `gpu` render backend on the SDL3 GPU API: device and window setup, the frame
lifecycle, the post pass, present, readback and the ImGui overlay. This is the part that gets a frame to the screen,
so the 3D (2a) and 2D (2b) workstreams depend on it to verify end to end. Land a first version that presents a
cleared frame and supports `screenshot` early, commit it, and tell the integrator, so 2a and 2b can rebase on it.

You own: the core files under `libraries/sim/src/render_gpu/` (the backend class, frame lifecycle, post pass,
present, readback, ImGui glue), the post shader ported from `shaders/post_*.glsl` to GLSL 450, and the ImGui SDL GPU
backend. Do not edit the interface header, the foundation library, or the files of 2a and 2b.

Parts:
1. **Backend start-up and frame lifecycle.** With `SIM_RENDERER=gpu`, create the device through the foundation
   (windowed, or windowless in headless mode with no DISPLAY), claim the window, and run the phases in the order the
   interface defines: uploads, 3D (2a), 2D composite of both screens into the offscreen frame (2b), post pass,
   ImGui, submit and present. Vsync and the frame-cap toggle (Tab, fast-forward on Space) switch the present mode
   at runtime. Window resize and high-DPI drawable size are handled.
2. **Post pass.** Port `post_fragment.glsl` exactly: shockwave, zoom blur, chromatic aberration, glow, vignette,
   localised glow, Key Stone cut-in and title card, letterbox, screen region mask, shake. All parameters arrive as
   one struct (one uniform block). The effects are triggered from game code (`include/port/postfx.h`,
   docs/postfx.md); the decay logic stays outside the backend. The post pass samples the composited frame with
   linear filtering and clamp-to-edge, as today.
3. **Present.** The post pass draws into the swapchain texture, which may be BGRA; letterboxing for aspect ratio
   happens as today (black around the viewport).
4. **Readback.** The interface's readback call returns the presented frame as RGBA8 top-down, synchronously, for
   `SIM_DebugFrame`, the lockstep `screenshot` command and `sim_headless_control.cpp`'s centre probe. In headless
   mode there is no swapchain: render into an offscreen present target and read that. Output must have the same
   size and orientation as the OpenGL backend's.
5. **ImGui.** The vendored ImGui needs the SDL GPU renderer backend (`imgui_impl_sdlgpu3`) from the upstream ImGui
   commit matching the vendored version, or a newer one if that version has none; if the vendored ImGui is too old
   for it, say so and propose the smallest ImGui update. The debug menu (` key), the Battle Lab panel and the file
   dialogs must work. ImGui draws after the post pass, on top of the presented frame, and is excluded from
   screenshots exactly as it is today (check whether it is).

## Verification (required)

1. With `SIM_RENDERER=gpu` and 2a/2b not yet present: the game boots headless, presents frames, and `screenshot`
   returns an image of the right size and orientation (the cleared colour, or whatever the stubs draw).
2. Post pass: run the Mega Evolution and Totem battle tours (or, if unreachable, force effects with a small test
   driver that calls the `PostFX_*` functions at known frames) through both backends and compare. Same rasteriser
   caveat as 2a only where geometry is involved; the post pass itself is a full-screen quad and should be exact or
   within one unit per channel (linear filtering).
3. Interactive under `xvfb-run -a`: window, present, resize, the frame-cap toggle, and the ImGui debug menu opening
   and drawing (screenshot it with ImGui visible by reading back the swapchain in a debug build, or say how you
   checked it).
4. Headless with no DISPLAY: the windowless path works and the scenario runner can drive it.
5. Both scenarios pass with `SIM_RENDERER=gpu` once 2a and 2b are in; until then say what you could run.
