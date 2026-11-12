# 1c. SDL GPU foundation library, shader toolchain and self-test

Model: Opus. Tree name: `gpufound`. Read `PLAN.md` and `briefs/COMMON.md` first.

## Resume state

This workstream needs no game build. Work in a plain clone of the simulator:
`git clone subprojects/libntr /home/user/wt/gpufound/libntr`, check out a branch `team/gpufound`, then
`git apply /home/user/dazzlingPlatinum/docs/sdl_gpu_migration/wip/gpufound-libntr.patch`.

The patch adds, as new files only: `include/simulator/gpu/{gpu,device,pipeline,texture,frame,std140,coords,
shader_blob}.hpp`, `libraries/sim/src/gpu/{gpu_device,gpu_pipeline,gpu_texture,gpu_frame}.cpp` and
`libraries/sim/tools/gpu_shaderc.py`. **None of it has been compiled or run.** The previous agent stopped while
writing the frame manager (`gpu_frame.cpp`); treat it as unfinished. There is no self-test, no meson wiring and no
guide yet. Read the existing code critically, keep what is sound, then build the self-test first so everything else
is verified as you go. Commit after each piece that passes.

## Task

Wave 2 writes three SDL GPU backends in parallel (3D, 2D compositing, post/present/readback/ImGui). They need a
shared, tested base so they do not each reinvent device setup, shader loading, pipeline caching and frame
management, and so their parts compose into one frame. Read `/home/user/deps/prefix/include/SDL3/SDL_gpu.h` fully
first.

Deliverables:

1. **Shader toolchain.** Shaders authored once in Vulkan-flavoured GLSL (`#version 450`, explicit
   `layout(set, binding)` following SDL GPU's resource-set rules for SPIR-V, which are strict), compiled to SPIR-V
   with `glslangValidator`, cross-compiled to MSL with `spirv-cross`, embedded as C arrays. A Python 3 (stdlib only)
   script emits the SPIR-V bytes, the MSL text and the resource counts SDL GPU needs at shader creation; a meson
   target makes adding a shader one line; a clear error when the tools are missing. The MSL binding/slot mapping
   must match what SDL's Metal backend expects: derive the rule from `/home/user/deps/SDL/src/gpu/metal/
   SDL_gpu_metal.m`, write it down in a comment, and state the MSL version chosen and why. This is the part most
   likely to be silently wrong, and it cannot be run here.
2. **`SIM::Gpu` core** (C++20, SDL3 and the standard library only):
   - Device: SPIR-V and MSL formats requested; optional debug mode by environment variable; window claim; vsync
     switchable at runtime; a **windowless mode** for headless runs that works with no DISPLAY.
   - Shader and graphics-pipeline creation from the embedded blobs, and a pipeline cache keyed by a small POD state
     struct (shaders, vertex layout, blend, cull, depth test/compare/write, target formats).
   - Textures: RGBA8, R8_UINT, R16_UINT, depth, render targets; full and sub-region upload; a sampler cache
     (nearest/linear, repeat/mirror/clamp-to-edge; OpenGL's clamp-to-border has no SDL GPU equivalent: say what a
     renderer should do instead); render-target recreation for internal-resolution changes.
   - Frame manager: one command buffer per frame; an upload queue executed in a copy pass before the render passes;
     ordered phases (3D scene into an offscreen colour+depth target, 2D composite into an offscreen frame target,
     post pass into the swapchain or an offscreen present target, ImGui, submit); a per-frame streaming vertex
     buffer for thousands of small draws; uniform push helpers.
   - Readback: a texture or the presented frame to CPU RGBA8 top-down, synchronously, handling BGRA swapchains.
   - Coordinate conventions: document exactly how SDL GPU differs from the current OpenGL code (NDC Y, depth range,
     texture origin, framebuffer origin for viewport/scissor/readback, front-face winding) and provide helpers so a
     renderer ported from OpenGL produces the same image.
   - Every SDL GPU failure logs `SDL_GetError()` with context and fails loudly.
3. **Standalone self-test** that links only SDL3, runs with no DISPLAY on lavapipe, exits non-zero on any mismatch
   and prints one PASS/FAIL line per case: windowless device; textured, vertex-coloured, depth-tested draw with
   readback against expected pixels including an orientation check (an asymmetric pattern must come back upright and
   unmirrored); alpha blending; cull and depth-compare permutations through the pipeline cache; integer textures
   read with `texelFetch` through `usampler2D`; a uniform block with an int array and a float array (std140 end to
   end; the 3D shader has two 32-float fog tables); sub-region texture updates; upload-queue ordering; many small
   draws in one frame; render-target resize; and under `xvfb-run`, the windowed path with present and readback.
4. **Porting guide** `libraries/sim/src/gpu/README.md`: how to add a shader, get a pipeline, upload a texture,
   record draws in a phase, push uniforms, read back; the coordinate rules; what OpenGL 4.1 offered that SDL GPU
   does not (clamp-to-border, `glReadPixels` of the default framebuffer, sampler state on textures, uniforms that
   persist between draws); Metal cautions derived from the SDL source.

Constraints:
- Do not design the game-facing backend interface (workstream 1b). This library sits underneath the GPU backend;
  keep it free of DS concepts. The frame API must allow a backend either to record draws and replay them at frame
  end or to issue them immediately once the frame has begun.
- Include only `<SDL3/SDL.h>`. Register the sources in meson so the integrator enables them with a one-line change,
  and name that line.
- Nothing that Metal on iOS or Vulkan 1.1-class Android devices lack; note any exception.

## Verification (required)

Build the self-test from a clean directory and run it with no DISPLAY and under `xvfb-run -a`; paste the PASS/FAIL
lines. Run the shader script on every shader and confirm SPIR-V and MSL are produced.

Report additionally: the coordinate-convention table, the MSL version and binding rule, a one-line-per-function
summary of the public API, and open risks.
