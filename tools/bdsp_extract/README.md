# BDSP 3D Asset Extractor (`tools/bdsp_extract/`)

Clean-room Python pipeline that extracts 3D Pokemon models, animations, and
3D battle arenas from the user's own legally dumped *Pokemon Brilliant Diamond*
/ *Shining Pearl* Nintendo Switch `.xci` into self-contained glTF 2.0 (`.glb`)
files for Dazzling Platinum's Metal 3D battle renderer.

**Zero copyrighted assets, keys, or RomFS data are stored in this repository.**

## Prerequisites (installed outside git)

1. **XCI / NCA unpacker (`hactool`):**
   ```bash
   mkdir -p ~/dz-team/bdsp3d-tools
   git clone --depth 1 https://github.com/SciresM/hactool.git ~/dz-team/bdsp3d-tools/hactool
   cd ~/dz-team/bdsp3d-tools/hactool && cp config.mk.template config.mk && make -j8
   ```
2. **Python 3.11+ venv with UnityPy, Pillow, NumPy:**
   ```bash
   uv venv --python 3.11 ~/dz-team/bdsp3d-tools/venv
   uv pip install --python ~/dz-team/bdsp3d-tools/venv/bin/python UnityPy Pillow numpy
   ```
   (`UnityPy >= 1.25` pulls in `astc-encoder-py`, `texture2ddecoder`, and `lz4`
   automatically, handling Switch Tegra ASTC texture deswizzling.)

## Usage

First run (unpacks the XCI Program NCA RomFS once into `--romfs-cache`, keeping
the `.xci` and `prod.keys` strictly read-only):

```bash
~/dz-team/bdsp3d-tools/venv/bin/python tools/bdsp_extract/extract_bdsp.py \
  --xci "/path/to/Pokemon Brilliant Diamond [0100000011D90000][v0].xci" \
  --keys "/path/to/prod.keys" \
  --romfs-cache ~/dz-team/bdsp3d-scratch/romfs \
  --out ~/dz-team/bdsp3d-assets \
  --species 392,400 \
  --arenas forest \
  --verify-dir ~/dz-team/bdsp3d-OUT/extract
```

Subsequent runs reuse `--romfs-cache` and skip XCI unpacking:

```bash
~/dz-team/bdsp3d-tools/venv/bin/python tools/bdsp_extract/extract_bdsp.py \
  --romfs-cache ~/dz-team/bdsp3d-scratch/romfs \
  --out ~/dz-team/bdsp3d-assets \
  --species 392,400 \
  --arenas forest
```

Pass `--species all` or `--arenas all` to extract every available species or
mapped battle biome (`plain_route`, `forest`, `water_lake`, `mountain_cave`,
`snow`, `city`, `indoors_gym`, `distortion_world`).

## Output Layout

```text
<out>/
  manifest.json        # metadata: source title id, bboxes, counts, clip info
  mons/
    pm0392_00.glb      # Infernape (skinned mesh, embedded PNGs, 6 clips)
    pm0400_00.glb      # Bibarel (skinned mesh, embedded PNGs, 6 clips)
  arenas/
    forest.glb         # Forest battle stage (BDSP g005, static batched GLB)
```

Runtime lookup in Dazzling Platinum checks `SIM_BDSP_ASSETS_DIR`, then
`~/Library/Application Support/Dazzling Platinum/bdsp_assets` (macOS) or
`<App>/Documents/bdsp_assets` (iOS).

## Exported Asset Conventions

- **Coordinate system:** Right-handed Y-up in meters (Unity left-handed assets
  converted via X reflection `x -> -x`, quaternion `(qx, -qy, -qz, qw)`,
  similarity `F * M * F` on `inverseBindMatrices`, and flipped triangle winding).
- **Pokemon `.glb`:**
  - Grounded via `idle` frame-0 skinned bounds so feet rest at `Y = 0`, facing `+Z`.
  - Single unified skin (`<= 128` joints) and single multi-primitive mesh.
  - Switch ASTC textures decoded to RGBA PNGs; `wrapU=Mirror` + `scale.x=2`
    textures are mirror-expanded for universal `REPEAT` sampling; BDSP eye
    sheets with `_ColorBaseU = -0.5` mirror the neutral expression column, and
    `_L1Col0Tex` iris layers are composited behind eye cutouts; `FireCore`
    meshes get a baked flame gradient while stencil-only `FireMask*` shells are
    stripped.
  - Battle animation clips: `idle` (`ba10_waitA01`), `attack_phys`
    (`ba20_buturi01`), `attack_spec` (`ba21_tokusyu01`), `hit`
    (`ba30_damageS01`), `faint` (`ba41_down01`), `cry` (`ba02_roar01`),
    decoded from Unity `StreamedClip` + `DenseClip` + `ConstantClip`.
- **Arena `.glb` (`forest.glb` from `g005`):**
  - Static geometry baked into world space and batched by material (8 primitives),
    clearing floor at `Y = 0`, unobstructed camera view from `(-3.6, 2.55, 8.8)`
    toward `(0.6, 1.45, -2.0)`.
  - Two-layer ground mask (`_MainTex` soil + `_LayerTex` grass via `_BlendTex`
    on UV1) baked into a 1024x1024 diffuse PNG; foliage/treeboards preserve
    `alphaMode = "MASK"`, `alphaCutoff`, and `doubleSided`.
  - Skybox omitted so Dazzling Platinum's time-of-day sky dome shows through
    the alpha-masked treeline.

## Module Overview

- `extract_bdsp.py` — CLI driver, RomFS cache unpacking, manifest & preview output
- `gltf_writer.py` — self-contained glTF 2.0 `.glb` binary serializer
- `unity_anim.py` — Unity `AnimationClip` curve decoder + LH-to-RH math helpers
- `unity_pokemon.py` — Pokemon mesh/skin/texture/animation extractor
- `unity_arena.py` — static battle arena extractor & ground-mask baker
- `verify_render.py` — GLB validator, texture contact sheet, and software preview renderer
