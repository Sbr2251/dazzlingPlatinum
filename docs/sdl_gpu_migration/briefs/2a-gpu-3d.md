# 2a. GPU backend: the 3D renderer

Model: Muse (tbh-1005 or tbh-1015). Tree name: `gpu3d`. Starts after wave 1 is merged. Read `PLAN.md` and `briefs/COMMON.md` first, then
the interface header from workstream 1b (`include/simulator/sim_render_backend.hpp`) and the foundation guide from
workstream 1c (`libraries/sim/src/gpu/README.md`). Those two documents are your contract; if either is missing
something you need, tell the integrator instead of working around it in your own files.

## Plan v2 changes (read first)

- Fog comes from `SIM_FogTable[32]` (sanitizers lane), not a register byte-walk.
- The **stat-change effect** (`src/battle/battle_stage_sprites.c`, `DrawStatFxMesh` / `DrawFlatStream`) redraws the
  battler's mesh vertex for vertex with depth compare `EQUAL`. Use `invariant gl_Position` and identical vertex math
  so it passes on lavapipe and Metal; golden scenarios `visual_intimidate_stat_drop`, `visual_swords_dance_stat_raise`
  and `visual_growl_enemy_stat_drop` must show the pattern on the Pokemon only.
- Display capture re-renders the 3D scene into the capture target (workstream 2c owns capture); make the 3D replay
  callable for a second target in the same frame.
- Verify with `run.py --compare-backends` over the whole suite instead of the old `render_compare.py`.

## Task

Implement the 3D part of the `gpu` render backend on the SDL3 GPU API, matching the OpenGL backend
(`libraries/sim/src/render_gl/`, 3D files) pixel for pixel where the rasterisers allow.

You own: the 3D files under `libraries/sim/src/render_gpu/` (suggested `sim_render_gpu_g3.cpp`), and the 3D
shaders ported from `shaders/g3_vertex.glsl` / `g3_fragment.glsl` to GLSL 450 for the shader toolchain. Do not edit
the interface header, the foundation library, or the files of workstreams 2b and 2c; ask the integrator for changes.

What the OpenGL 3D path does, all of which must be reproduced:
- Thousands of small draw calls per frame (vertex position, texture coordinate, colour), issued by the game during
  the frame. The GPU backend records them and replays them in the 3D render pass at frame end; vertex data goes into
  the frame's streaming vertex buffer.
- Per-draw state baked into pipelines: cull mode (none, front, back, and "cull all" = draw nothing), depth function
  `LESS` or `EQUAL` (the DS "decal" test; `LEQUAL` is wrong, see the comment in the OpenGL renderer), depth write
  off for translucent polygons unless their attribute asks for it, alpha blending.
- Opaque draws in submission order, then the deferred translucent draws, with the ordering the OpenGL path uses.
- Texturing: nearest filtering; per-draw wrap modes repeat, mirrored repeat, and clamp. OpenGL uses clamp-to-border
  here, which SDL GPU does not have: reproduce the border behaviour (what colour does the border give today, and
  does any content rely on it?) in the shader or by another exact method, and say which.
- Polygon modes (modulate, decal, toon/highlight, shadow as far as the OpenGL path implements them) and fog with
  the two 32-entry tables, passed as a uniform block per draw (or per change).
- Target: an offscreen colour+depth target at 256x192 times the internal-resolution scale, with the viewport on the
  top or bottom half depending on which screen shows 3D (`POWCNT` bit 15), cleared when the OpenGL path clears it.
  The 2D compositor (2b) samples this colour target as BG0.
- 3D texture handles: create, update, destroy through the interface, with uploads queued for the copy pass.
- Coordinate conventions: OpenGL NDC and framebuffer origin differ from SDL GPU's. Use the foundation's helpers;
  check orientation and winding early with a known asymmetric scene, because a flipped Y also flips the winding and
  therefore the cull mode.

## Verification (required)

1. The self-contained check first: render the title screen's 3D scene and the intro's 3D scenes through both
   backends and compare (`tools/dazzling/render_compare/render_compare.py --a SIM_RENDERER=gl --b SIM_RENDERER=gpu`
   with the boot/title tour). If 2c's present path is not ready yet, read the 3D colour target back through the
   foundation's readback helper and compare against the OpenGL 3D target dumped the same way.
2. All tours that show 3D: field maps (terrain, buildings, water, fog), battles (sprites are 3D quads; particle
   effects; the stat-change effect that relies on the `EQUAL` depth test), the Distortion World.
3. Differences: polygon-edge pixels may differ between llvmpipe and lavapipe. Report the per-tour numbers, look at
   the diff images for every checkpoint above 0.5% differing pixels, and classify each as rasteriser noise or a
   bug. Anything structural (missing geometry, wrong order, wrong blend, flipped, wrong depth) is a bug to fix.
4. Changing the internal resolution at runtime (debug menu setting) works and does not leak textures.
5. Frame rate against the OpenGL backend for the same lockstep run; report both.
6. Both scenarios pass with `SIM_RENDERER=gpu` once 2b and 2c are in; until then say what you could run.
