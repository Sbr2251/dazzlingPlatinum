#!/usr/bin/env python3
"""Clean-room BDSP 3D asset extractor for Dazzling Platinum.

Extracts legally user-dumped Pokemon Brilliant Diamond / Shining Pearl XCI
RomFS assets (3D skinned Pokemon models, textures, battle animations, and 3D
battle arenas) into self-contained glTF 2.0 (.glb) files + manifest.json.

ZERO copyrighted assets or keys are stored in this repository.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

# Ensure sibling modules resolve regardless of CWD
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from PIL import Image, ImageDraw

from unity_arena import ARENA_BIOME_MAP, extract_arena_glb
from concurrent.futures import ProcessPoolExecutor, as_completed
from unity_pokemon import discover_species_forms, extract_pokemon_glb
from verify_render import eval_glb_pose, load_glb, make_texture_contact_sheet, render_preview


def _find_hactool(explicit: str | None) -> str:
    candidates = []
    if explicit:
        candidates.append(explicit)
    env_ht = os.environ.get("HACTOOL")
    if env_ht:
        candidates.append(env_ht)
    candidates.extend(
        [
            str(Path.home() / "dz-team/bdsp3d-tools/hactool/hactool"),
            shutil.which("hactool") or "",
        ]
    )
    for c in candidates:
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    raise FileNotFoundError(
        "hactool binary not found. Pass --hactool <path> or build hactool (see tools/bdsp_extract/README.md)."
    )


def ensure_romfs_unpacked(
    xci_path: str | None,
    keys_path: str | None,
    romfs_cache: str,
    hactool_bin: str | None,
) -> str:
    """Ensure AssetAssistant RomFS exists under romfs_cache; unpack XCI if absent."""
    aa_dir = os.path.join(romfs_cache, "Data", "StreamingAssets", "AssetAssistant")
    if os.path.isdir(aa_dir):
        print(f"[romfs] Using cached RomFS: {aa_dir}")
        return aa_dir

    if not xci_path or not keys_path:
        raise ValueError(
            f"RomFS cache not populated at {romfs_cache}; provide --xci and --keys to unpack."
        )
    if not os.path.isfile(xci_path):
        raise FileNotFoundError(f"XCI not found: {xci_path}")
    if not os.path.isfile(keys_path):
        raise FileNotFoundError(f"prod.keys not found: {keys_path}")

    ht = _find_hactool(hactool_bin)
    secure_dir = os.path.join(romfs_cache, "_tmp_secure")
    os.makedirs(secure_dir, exist_ok=True)
    os.makedirs(romfs_cache, exist_ok=True)

    try:
        print(f"[romfs] Unpacking XCI secure partition with {ht} ...")
        subprocess.run(
            [ht, "-k", keys_path, "-t", "xci", f"--securedir={secure_dir}", xci_path],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        ncas = sorted(
            [os.path.join(secure_dir, f) for f in os.listdir(secure_dir) if f.endswith(".nca")],
            key=lambda p: os.path.getsize(p),
            reverse=True,
        )
        if not ncas:
            raise RuntimeError("No .nca files found in XCI secure partition.")
        main_nca = ncas[0]
        print(f"[romfs] Extracting RomFS from Program NCA ({os.path.basename(main_nca)}) ...")
        subprocess.run(
            [ht, "-k", keys_path, "-t", "nca", f"--romfsdir={romfs_cache}", main_nca],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    finally:
        shutil.rmtree(secure_dir, ignore_errors=True)

    if not os.path.isdir(aa_dir):
        raise RuntimeError(f"Expected AssetAssistant directory missing after unpack: {aa_dir}")
    return aa_dir


def _discover_all_species(aa_root: str) -> list[int]:
    battle_dir = os.path.join(aa_root, "Pokemon Database/pokemons/battle")
    found: set[int] = set()
    for name in os.listdir(battle_dir):
        if name.startswith("pm") and name.endswith("_00"):
            try:
                found.add(int(name[2:6]))
            except ValueError:
                pass
    return sorted(found)


def _render_verification_sheet(
    out_dir: str,
    verify_dir: str,
    mon_entries: list[dict[str, Any]],
    arena_entries: list[dict[str, Any]],
    all_textures: list[tuple[str, Image.Image]],
) -> None:
    os.makedirs(verify_dir, exist_ok=True)

    # 1. Decoded diffuse texture contact sheet
    tex_path = os.path.join(verify_dir, "textures_check.png")
    make_texture_contact_sheet(all_textures, tex_path)
    print(f"[verify] Wrote {tex_path} ({len(all_textures)} textures)")

    # 2. Pokemon 3D previews (front 3/4, rear 3/4, idle mid-frame, attack_phys mid-frame)
    for m in mon_entries:
        glb_path = os.path.join(out_dir, m["file"])
        gltf, bin_data = load_glb(glb_path)
        h = max(m["height_m"], 0.6)
        cy = h * 0.5
        d = h * 2.4
        panels = []
        views = [
            ("bind_front", None, 0.0, (d * 0.45, cy * 1.1, d), (0.0, cy, 0.0)),
            ("idle_t0", "idle", 0.0, (d * 0.55, cy * 1.05, d * 0.9), (0.0, cy, 0.0)),
            ("idle_back", "idle", 0.4, (-d * 0.5, cy * 1.15, -d * 0.95), (0.0, cy, 0.0)),
            ("attack_phys", "attack_phys", 0.5, (d * 0.65, cy * 1.05, d * 0.85), (0.0, cy, 0.0)),
        ]
        for label, clip, t_s, eye, tgt in views:
            prims = eval_glb_pose(gltf, bin_data, clip_name=clip, t_sec=t_s)
            im = render_preview(prims, eye=eye, target=tgt, fov_deg=35.0, width=320, height=320, bg_rgb=(28, 36, 58))
            dr = ImageDraw.Draw(im)
            dr.text((8, 8), f"{m['id']} {label}", fill=(255, 255, 255))
            panels.append(im)
        strip = Image.new("RGB", (320 * len(panels), 320))
        for i, im in enumerate(panels):
            strip.paste(im, (i * 320, 0))
        p_out = os.path.join(verify_dir, f"{m['id']}_preview.png")
        strip.save(p_out)
        print(f"[verify] Wrote {p_out}")

    # 3. Arena camera view + top-down preview (matching battle_stage.c home camera)
    for a in arena_entries:
        glb_path = os.path.join(out_dir, a["file"])
        gltf, bin_data = load_glb(glb_path)
        prims = eval_glb_pose(gltf, bin_data)
        cam_im = render_preview(
            prims,
            eye=(-3.6, 2.55, 8.8),
            target=(0.6, 1.45, -2.0),
            fov_deg=38.0,
            width=640,
            height=360,
            bg_rgb=(16, 24, 58),
            backface_cull=True,
        )
        dr = ImageDraw.Draw(cam_im)
        dr.text((10, 10), f"{a['biome']} ({a['source_ground']} yaw={a['yaw_deg']}deg) battle cam", fill=(255, 255, 255))

        top_im = render_preview(
            prims,
            eye=(0.0, 58.0, 0.01),
            target=(0.0, 0.0, 0.0),
            fov_deg=55.0,
            width=360,
            height=360,
            bg_rgb=(16, 24, 38),
            backface_cull=False,
        )
        dr2 = ImageDraw.Draw(top_im)
        dr2.text((10, 10), f"{a['biome']} top-down", fill=(255, 255, 255))

        comb = Image.new("RGB", (640 + 360, 360))
        comb.paste(cam_im, (0, 0))
        comb.paste(top_im, (640, 0))
        a_out = os.path.join(verify_dir, f"{a['biome']}_preview.png")
        comb.save(a_out)
        print(f"[verify] Wrote {a_out}")


def _extract_mon_worker(
    aa_root: str, species: int, form: int, shiny: bool, out_glb: str, fps: float
) -> dict[str, Any]:
    info = extract_pokemon_glb(aa_root, species=species, form=form, shiny=shiny, out_glb_path=out_glb, sample_fps=fps)
    info.pop("decoded_textures", None)
    return info


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract BDSP 3D Pokemon & battle arenas to glTF 2.0 (.glb)")
    ap.add_argument("--xci", help="Path to user's Brilliant Diamond / Shining Pearl .xci (read-only)")
    ap.add_argument("--keys", help="Path to user's Switch prod.keys (read-only)")
    ap.add_argument("--romfs-cache", required=True, help="Directory holding unpacked RomFS (reused across runs)")
    ap.add_argument("--hactool", default=None, help="Optional path to hactool binary")
    ap.add_argument("--out", required=True, help="Output assets directory (writes mons/, arenas/, manifest.json)")
    ap.add_argument("--species", default="392,400", help="Comma-separated National Dex IDs, 'all', or 'none' (default: 392,400)")
    ap.add_argument("--range", dest="species_range", default=None, help="Inclusive Dex range START-END (e.g. 1-151), overrides --species")
    ap.add_argument("--forms", action="store_true", help="Extract all alternate battle forms for multi-form species")
    ap.add_argument("--shiny", action="store_true", help="Also extract shiny variants (*_shiny.glb)")
    ap.add_argument("--workers", type=int, default=1, help="Parallel worker processes for Pokemon extraction (default: 1)")
    ap.add_argument("--skip-existing", action="store_true", help="Skip already extracted .glb files")
    ap.add_argument("--no-manifest", action="store_true", help="Do not overwrite <out>/manifest.json (useful for parallel shards)")
    ap.add_argument("--arenas", default="forest", help="Comma-separated biome stems, 'all', or 'none' (default: forest)")
    ap.add_argument("--arena-yaw", type=float, default=0.0, help="Yaw rotation (degrees) applied to arena geometry")
    ap.add_argument("--fps", type=float, default=30.0, help="Animation resample rate in FPS (default: 30)")
    ap.add_argument("--verify-dir", default=None, help="Optional directory to render texture/mesh sanity previews")
    ap.add_argument("--ui", action="store_true", help="Also extract BDSP battle UI sprites & atlas into <out>/ui/")
    ap.add_argument("--cameras", action="store_true", help="Also extract BDSP battle camera curves into <out>/cameras/")
    ap.add_argument("--trainers", action="store_true", help="Also extract 3D player trainers (Lucas/Dawn) & Poke Ball into <out>/trainers/")
    args = ap.parse_args()

    aa_root = ensure_romfs_unpacked(args.xci, args.keys, args.romfs_cache, args.hactool)

    os.makedirs(os.path.join(args.out, "mons"), exist_ok=True)
    os.makedirs(os.path.join(args.out, "arenas"), exist_ok=True)

    if args.species_range:
        lo_s, hi_s = args.species_range.split("-", 1)
        lo, hi = int(lo_s), int(hi_s)
        species_list = [sp for sp in _discover_all_species(aa_root) if lo <= sp <= hi]
    elif args.species.strip().lower() == "all":
        species_list = _discover_all_species(aa_root)
    elif args.species.strip().lower() == "none":
        species_list = []
    else:
        species_list = [int(s.strip()) for s in args.species.split(",") if s.strip()]

    if args.arenas.strip().lower() == "all":
        arena_list = list(ARENA_BIOME_MAP.keys())
    elif args.arenas.strip().lower() == "none":
        arena_list = []
    else:
        arena_list = [a.strip() for a in args.arenas.split(",") if a.strip()]

    all_textures: list[tuple[str, Image.Image]] = []
    mon_entries: list[dict[str, Any]] = []
    arena_entries: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    jobs: list[tuple[int, int, bool, str]] = []
    for sp in species_list:
        forms = discover_species_forms(aa_root, sp) if args.forms else [0]
        if not forms:
            forms = [0]
        for fm in forms:
            for sh in ([False, True] if args.shiny else [False]):
                suffix = "_shiny" if sh else ""
                out_glb = os.path.join(args.out, "mons", f"pm{sp:04d}_{fm:02d}{suffix}.glb")
                if args.skip_existing and os.path.isfile(out_glb) and os.path.getsize(out_glb) > 1024:
                    continue
                jobs.append((sp, fm, sh, out_glb))

    if args.workers > 1 and len(jobs) > 1:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futs = {
                pool.submit(_extract_mon_worker, aa_root, sp, fm, sh, out_glb, args.fps): (sp, fm, sh, out_glb)
                for (sp, fm, sh, out_glb) in jobs
            }
            for fut in as_completed(futs):
                sp, fm, sh, out_glb = futs[fut]
                try:
                    info = fut.result()
                    mon_entries.append(info)
                    print(
                        f"[mon] OK pm{sp:04d}_{fm:02d}{'_shiny' if sh else ''}: "
                        f"{info['size_bytes']//1024} KB, tris={info['triangles']}, bones={info['bones']}, clips={len(info['clips'])}"
                    )
                except Exception as exc:
                    failures.append({"species": sp, "form": fm, "shiny": sh, "error": str(exc)})
                    print(f"[mon] FAIL pm{sp:04d}_{fm:02d}{'_shiny' if sh else ''}: {exc}", file=sys.stderr)
    else:
        for sp, fm, sh, out_glb in jobs:
            print(f"[mon] Extracting pm{sp:04d}_{fm:02d}{'_shiny' if sh else ''} -> {out_glb} ...")
            try:
                info = extract_pokemon_glb(aa_root, species=sp, form=fm, shiny=sh, out_glb_path=out_glb, sample_fps=args.fps)
                all_textures.extend(info.pop("decoded_textures", []))
                mon_entries.append(info)
                print(
                    f"      OK: {info['size_bytes']//1024} KB, verts={info['vertices']}, tris={info['triangles']}, "
                    f"bones={info['bones']}, height={info['height_m']}m, clips={list(info['clips'].keys())}"
                )
            except Exception as exc:
                failures.append({"species": sp, "form": fm, "shiny": sh, "error": str(exc)})
                print(f"      FAIL: {exc}", file=sys.stderr)

    for biome in arena_list:
        out_glb = os.path.join(args.out, "arenas", f"{biome}.glb")
        print(f"[arena] Extracting biome '{biome}' (yaw={args.arena_yaw} deg) -> {out_glb} ...")
        info = extract_arena_glb(aa_root, biome=biome, out_glb_path=out_glb, yaw_deg=args.arena_yaw)
        all_textures.extend(info.pop("decoded_textures", []))
        arena_entries.append(info)
        print(
            f"        OK: {info['size_bytes']//1024} KB, verts={info['vertices']}, tris={info['triangles']}, "
            f"prims={info['primitives']}, bbox={info['bbox_min']}..{info['bbox_max']}"
        )

    manifest = {
        "schema_version": 1,
        "source_title_id": "0100000011D90000",
        "coordinate_system": "right_handed_y_up_meters",
        "mons": mon_entries,
        "arenas": arena_entries,
    }
    if not args.no_manifest:
        manifest_path = os.path.join(args.out, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        print(f"[manifest] Wrote {manifest_path}")
    if failures:
        print(f"[summary] {len(mon_entries)} succeeded, {len(failures)} failed", file=sys.stderr)
        return 1

    if args.verify_dir:
        _render_verification_sheet(args.out, args.verify_dir, mon_entries, arena_entries, all_textures)

    here = os.path.dirname(os.path.abspath(__file__))
    if args.ui:
        subprocess.run([sys.executable, os.path.join(here, "unity_ui.py"), "--romfs-cache", args.romfs_cache, "--out", os.path.join(args.out, "ui")], check=True)
    if args.cameras:
        subprocess.run([sys.executable, os.path.join(here, "unity_camera.py"), "--romfs-cache", args.romfs_cache, "--out", os.path.join(args.out, "cameras", "battle_cameras.json")], check=True)
    if args.trainers:
        subprocess.run([sys.executable, os.path.join(here, "unity_trainer.py"), "--romfs-cache", args.romfs_cache, "--out", os.path.join(args.out, "trainers")], check=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
