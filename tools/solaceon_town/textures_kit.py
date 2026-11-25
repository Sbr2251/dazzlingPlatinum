#!/usr/bin/env python3
"""Appends the Solaceon redesign texture kit to overworld texture set 010. Dry run unless --write.

Usage:
  python3 tools/solaceon_town/textures_kit.py                  dry run: every check, the per-texture table, VRAM
  python3 tools/solaceon_town/textures_kit.py --write          write SET_REL (only if every check passes)
  python3 tools/solaceon_town/textures_kit.py --out FILE       write the result to FILE instead (also check-gated)
  python3 tools/solaceon_town/textures_kit.py --preview DIR    decode the kit back out of the built set to PNGs

Set 010 belongs to area 0xA: Solaceon Town, Celestic Town, Routes 209, 210, 211 East and 215. APPEND-ONLY: the set is
rebuilt from git at BASE_REV every run (idempotent, never feeds back on itself), the stock textures and palettes keep
their names, texels and palette bytes (asserted), and the kit's entries go after them.

Inputs: tools/solaceon_town/assets/textures/<name>.png + <name>.json (tools/lake_verity/assets/README.md format),
painted by tools/solaceon_town/art/paint_kit.py. JSON keys used here:
  format, c0                   encoding (pltt16 / pltt4); c0 = 1 makes palette colour 0 transparent
  texels_of + palette          palette-only entry: the PNG must carry exactly the texel indices of stock texture
                               <texels_of>; only palette <palette> is appended (the memorial wall's sol_stone trick)
  frames, frame_ticks          animated (sol_candle): the base texture goes into the set; the frame PNGs
                               (<name>.1..N) belong in a fldtanime entry, which town-art adds (see art.md)
  repeat, flip                 material settings, reported for town-art (not stored in the texture set)
New texture palettes are named <texture>_pl.

Checks (all must pass for --write / --out): kit names unique, not clashing with stock, <= 15 characters; palette-only
texels identical to stock; stock textures and palettes unchanged in the output; kit VRAM <= KIT_BUDGET and the set
<= VRAM_PROVEN (largest stock set, 048); every animated texture's frames share size, format and palette.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "lake_verity"))
import nsbtx  # noqa: E402
import png  # noqa: E402

# Output path of set 010: the macOS app branch (solaceon-mac) keeps it in res/field/mapmodels/texture_sets/ (the devserver
# ROM tree used res/field/maps/texture_sets/; the stock bytes are the same).
SET_REL = "res/field/mapmodels/texture_sets/map_texture_set_010.nsbtx"
BASE_REV = "50482f890"          # arc2 merge: stock set 010 (with the memorial wall's sol_wall / sol_stone)
BASE_SET_REL = "res/field/maps/texture_sets/map_texture_set_010.nsbtx"   # where set 010 lives at BASE_REV
ASSET_DIR = os.path.join(ROOT, "tools", "solaceon_town", "assets", "textures")
KIT_BUDGET = 24576              # docs/solaceon_redesign/PLAN.md section 3: +24 KB in set 010
VRAM_PROVEN = 76416             # largest stock map texture set (048)
NAME_MAX = 15

# append order (groups as in docs/solaceon_redesign/art.md); stretch items last, so they are the first to cut
ORDER = ["sol_hwall", "sol_hroof", "sol_htrim", "sol_hatlas", "sol_gate", "sol_steps", "sol_fcpave", "sol_emblem",
         "sol_plaza", "sol_border", "sol_furn", "sol_offer", "sol_banner", "sol_candle", "sol_canvas", "sol_awning",
         "sol_tent", "sol_scaff", "sol_wfence", "sol_tarp", "sol_exatlas", "sol_spoil", "sol_kwall", "sol_kroof",
         "sol_yard", "sol_ruts"]
STRETCH = ["sol_ruts", "sol_candle", "sol_tarp", "sol_border"]   # sol_truck was cut by town-art (no terrain truck)   # cut in this order if VRAM is needed


def git_bytes(rev, rel):
    import subprocess
    return subprocess.run(["git", "-C", ROOT, "show", f"{rev}:{rel}"], check=True, capture_output=True).stdout


def load_kit():
    names = sorted(f[:-5] for f in os.listdir(ASSET_DIR) if f.endswith(".json") and "." not in f[:-5])
    extra = [n for n in names if n not in ORDER]
    missing = [n for n in ORDER if n not in names]
    out = []
    for n in [n for n in ORDER if n in names] + extra:
        meta = json.load(open(os.path.join(ASSET_DIR, n + ".json")))
        out.append((n, meta, png.read(os.path.join(ASSET_DIR, n + ".png"))))
    return out, missing


def build(base_bytes, kit):
    """-> (output bytes, rows for the table, list of failed checks, material bindings)."""
    fails = []
    base = nsbtx.parse(base_bytes)
    T = {t["name"]: t for t in base["textures"]}
    P = {p["name"]: p for p in base["palettes"]}
    new_t, new_p, rows, binds = [], [], [], []
    seen = set()
    for name, meta, img in kit:
        fmt = meta.get("format", "pltt16")
        if "texels_of" in meta:
            src = meta["texels_of"]
            pal_name = meta["palette"]
            if src not in T:
                fails.append(f"{name}: stock texture {src} not in set 010")
                continue
            t, p = nsbtx.encode_texture(src, img, fmt, T[src]["c0"])
            if t["data"] != T[src]["data"]:
                fails.append(f"{name}: texels differ from stock {src}")
            p["name"] = pal_name
            new_p.append(p)
            tex_b, pal_b = 0, len(p["colors"]) * 2
            binds.append((name, src, pal_name))
            added = [pal_name]
        else:
            t, p = nsbtx.encode_texture(name, img, fmt, meta.get("c0"))
            new_t.append(t)
            new_p.append(p)
            tex_b, pal_b = len(t["data"]), len(p["colors"]) * 2
            binds.append((name, name, p["name"]))
            added = [name, p["name"]]
            for k, fn in enumerate(meta.get("frames", [])):
                fi = png.read(os.path.join(ASSET_DIR, fn + ".png"))
                ft, fp = nsbtx.encode_texture(fn, fi, fmt, meta.get("c0"))
                if (fi.width, fi.height) != (img.width, img.height) or fp["colors"][:len(p["colors"])] != \
                        p["colors"][:len(fp["colors"])]:
                    fails.append(f"{name}: frame {fn} does not share size/palette")
        for a in added:
            if a in T or a in P:
                fails.append(f"{name}: '{a}' clashes with a stock entry")
            if a in seen:
                fails.append(f"{name}: '{a}' is not unique in the kit")
            if len(a) > NAME_MAX:
                fails.append(f"{name}: '{a}' is longer than {NAME_MAX} characters")
            seen.add(a)
        rep = "".join(c for c, on in zip("st", meta.get("repeat", [True, True])) if on) or "-"
        if any(meta.get("flip", [])):
            rep += "+flip"
        rows.append((name, fmt, f"{img.width}x{img.height}", len(meta.get("frames", [])) or 1, tex_b, pal_b, rep,
                     meta.get("c0", 0), meta.get("texels_of", "")))
    for t in base["textures"]:
        t.pop("off", None)
    for p in base["palettes"]:
        p.pop("off", None)
    out = nsbtx.build(base["textures"] + new_t, base["palettes"] + new_p, pal_flag=base["header"]["pal_flag"])
    # stock unchanged
    sb, so = nsbtx.parse(base_bytes), nsbtx.parse(out)
    OT = {t["name"]: t for t in so["textures"]}
    OP = {p["name"]: p for p in so["palettes"]}
    for t in sb["textures"]:
        t2 = OT.get(t["name"])
        if not t2 or t2["data"] != t["data"] or (t2["fmt"], t2["w"], t2["h"], t2["c0"]) != \
                (t["fmt"], t["w"], t["h"], t["c0"]):
            fails.append(f"stock texture {t['name']} changed")
    for p in sb["palettes"]:
        if p["name"] not in OP or not OP[p["name"]]["data"].startswith(p["data"]):
            fails.append(f"stock palette {p['name']} changed")
    if len(so["textures"]) != len(sb["textures"]) + len(new_t) or len(so["palettes"]) != len(sb["palettes"]) + len(new_p):
        fails.append("entry count mismatch")
    vb, vo = nsbtx.vram_usage(sb), nsbtx.vram_usage(so)
    if sum(vo) - sum(vb) > KIT_BUDGET:
        fails.append(f"kit VRAM {sum(vo) - sum(vb)} B > budget {KIT_BUDGET}")
    if sum(vo) > VRAM_PROVEN:
        fails.append(f"set VRAM {sum(vo)} B > {VRAM_PROVEN} (largest stock set)")
    return out, rows, fails, binds, (vb, vo)


def main():
    kit, missing = load_kit()
    base_bytes = git_bytes(BASE_REV, BASE_SET_REL)
    out, rows, fails, binds, (vb, vo) = build(base_bytes, kit)
    if missing:
        fails.append(f"kit textures missing from {ASSET_DIR}: {missing} (run tools/solaceon_town/art/paint_kit.py)")
    print(f"set 010 from {BASE_REV}:{BASE_SET_REL} -> {SET_REL}")
    print(f"{'texture':12s} {'format':7s} {'size':6s} {'fr':>2s} {'texel B':>8s} {'pal B':>6s}  repeat   c0  note")
    for (n, fmt, size, fr, tb, pb, rep, c0, src) in rows:
        note = f"palette only, texels = stock {src}" if src else ("stretch" if n in STRETCH else "")
        print(f"{n:12s} {fmt:7s} {size:6s} {fr:2d} {tb:8d} {pb:6d}  {rep:8s} {c0:2d}  {note}")
    tt = sum(r[4] for r in rows)
    tp = sum(r[5] for r in rows)
    print(f"kit: {len(rows)} entries, {tt} texel + {tp} palette = {tt + tp} B (budget {KIT_BUDGET})")
    print(f"set 010 VRAM: {sum(vb)} -> {sum(vo)} B (texels {vb[0]} -> {vo[0]}, palettes {vb[1]} -> {vo[1]}); "
          f"+{sum(vo) - sum(vb)} B, ceiling {VRAM_PROVEN}")
    print(f"textures {len(nsbtx.parse(base_bytes)['textures'])} -> {len(nsbtx.parse(out)['textures'])}, "
          f"palettes {len(nsbtx.parse(base_bytes)['palettes'])} -> {len(nsbtx.parse(out)['palettes'])}")
    print("material bindings (texture + palette):")
    print("  " + ", ".join(f"{n}: {t}+{p}" for n, t, p in binds))
    anim = [(n, m) for n, m, _ in kit if m.get("frames")]
    for n, m in anim:
        print(f"fldtanime (town-art): {n}, {len(m['frames'])} frames ({', '.join(m['frames'])}), "
              f"{m['frame_ticks']} VBlanks per frame")
    if fails:
        print("CHECKS FAILED:")
        for f in fails:
            print("  -", f)
    else:
        print("all checks pass: names unique and <= 15 chars, palette-only texels = stock, stock textures and "
              "palettes unchanged, VRAM within budget")
    if "--preview" in sys.argv:
        d = sys.argv[sys.argv.index("--preview") + 1]
        os.makedirs(d, exist_ok=True)
        s = nsbtx.parse(out)
        TT = {t["name"]: t for t in s["textures"]}
        PP = {p["name"]: p for p in s["palettes"]}
        for n, t, p in binds:
            rgba, _ = nsbtx.decode(TT[t], PP[p]["colors"])
            png.write_rgba(os.path.join(d, n + ".png"), TT[t]["w"], TT[t]["h"], rgba)
        print("wrote previews to", d)
    target = None
    if "--write" in sys.argv:
        target = os.path.join(ROOT, SET_REL)
    if "--out" in sys.argv:
        target = sys.argv[sys.argv.index("--out") + 1]
    if target:
        if fails:
            print("refusing to write: checks failed")
            sys.exit(1)
        open(target, "wb").write(out)
        print("wrote", target, len(out), "B")
    elif not fails:
        print("dry run: nothing written (use --write)")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
