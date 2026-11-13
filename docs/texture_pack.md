# Texture packs (GPU backend)

Hash-keyed texture replacement for the SDL GPU renderer. Under
`Renderer=gl` nothing changes.

## Switches

In `sim_config_prj.ini` `[General]` (the file next to the game data):

```
TexturePack=true        ; default true in the app
TexturePackDump=false   ; default false
```

Headless runs ignore both unless the scenario opts in with
`SIM_FX_TEXPACK=1` / `SIM_FX_TEXPACK_DUMP=1`, so existing goldens stay
byte-identical. `SIM_TEXPACK_DIR=<dir>` overrides the pack location.
The pack directory is looked up as: `$SIM_TEXPACK_DIR`, `./TexturePack`,
`<exe dir>/TexturePack`, then the bundled demo pack under
`tools/texpack/demo/TexturePack` (dev builds only).

## How it works

Each decoded G3 texture is named by a stable 64-bit FNV-1a hash of its
raw texel data, format and size. The palette is hashed separately and
is not part of the name, so a palette animation still uses the same
replacement. `TexturePack/<hash>.png` at any integer scale 1x-4x (same
aspect) replaces the texture; it is sampled with the original
normalised UVs, so a 2x image simply carries more detail. Replacements
are cached by hash; with no pack directory there is no per-texture
file IO at all.

## Dump, redraw, install

1. Set `TexturePackDump=true` (headless: `SIM_FX_TEXPACK_DUMP=1`) and
   run to the scene you want to redraw. Every distinct texture lands in
   the pack directory as `<hash>.png` at 1x, with a `manifest.csv`
   row (`hash,width,height,format,palette_hash,scene`; scene is
   `unknown` - the simulator does not know map names).
2. Redraw a PNG at 1x, 2x, 3x or 4x, keeping the aspect ratio and the
   transparent pixels transparent. Keep the file name.
3. Put the redrawn files in `TexturePack/` next to the game data (or
   point `SIM_TEXPACK_DIR` at the folder), set `TexturePack=true`,
   restart. Delete a file to fall back to the original texture.

## Demo pack

`tools/texpack/demo/TexturePack/` holds 2x replacements for the eight
largest Twinleaf field textures (trees, ground, roofs), made by
`tools/texpack/make_demo_pack.py` (nearest-2x plus a palette-shading /
grain / outline detail pass - pixel art, not a smoothing filter):

```
python3 tools/texpack/make_demo_pack.py <dump-dir> tools/texpack/demo/TexturePack
```

Golden: `visual_texpack_twinleaf` (GPU, demo pack) vs
`visual_overworld_twinleaf_after_distortion_world` (same frame, no pack).
