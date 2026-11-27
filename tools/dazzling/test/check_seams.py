#!/usr/bin/env python3
"""Overworld town/route seam-crossing health check for Dazzling Platinum.

Walks back and forth across key overworld chunk seams and asserts billboard
integrity (zero OOB texture indices, zero ALLOC_ERROR texKeys, player billboard
drawn) and VRAM headroom after every crossing.

Usage:
    python3 tools/dazzling/test/check_seams.py [--build build_macos_release] \
        [--out /tmp/seam_check] [--cine]
"""

import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DAZZLING_DIR = os.path.normpath(os.path.join(HERE, ".."))
if DAZZLING_DIR not in sys.path:
    sys.path.insert(0, DAZZLING_DIR)

from repro_lib import ReproError, ReproSession


# Verified chunk seams from res/field/maps/groups.json and map events/scripts:
#   - Route 209 (chunk 17,21 z=672..703) <-> Solaceon Town (chunk 17,20 z=640..671)
#   - Solaceon Town (chunk 17,20 z=640..671) <-> Route 210 South (chunk 17,19 z=608..639)
#   - Route 201 (chunk 4,26 x=128..159) <-> Sandgem Town (chunk 5,26 x=160..191), road z=844..846
#   - Route 202 (chunk 5,25 z=800..831) <-> Jubilife City (chunk 5,24 z=768..799), road x=173..175
SEAMS = [
    {
        "id": "solaceon_south_band_b",
        "label": "Route 209 <-> Solaceon (Band B + cine)",
        "vars": {"VAR_ARC2_PROGRESS": 60},
        "flags": {"FLAG_CINE_VISITED_SOLACEON": False},
        "start_map": "MAP_HEADER_ROUTE_209",
        "start_pos": (560, 674),
        "start_dir": "DIR_NORTH",
        "forward_dir": "UP",
        "forward_tiles": 3,
        "forward_map": "MAP_HEADER_SOLACEON_TOWN",
        "back_dir": "DOWN",
        "back_tiles": 3,
        "back_map": "MAP_HEADER_ROUTE_209",
        "cine_wait_frames": 360,
    },
    {
        "id": "solaceon_north_band_a",
        "label": "Solaceon <-> Route 210 South (Band A)",
        "vars": {"VAR_ARC2_PROGRESS": 45},
        "flags": {},
        "start_map": "MAP_HEADER_SOLACEON_TOWN",
        "start_pos": (560, 642),
        "start_dir": "DIR_NORTH",
        "forward_dir": "UP",
        "forward_tiles": 4,
        "forward_map": "MAP_HEADER_ROUTE_210_SOUTH",
        "back_dir": "DOWN",
        "back_tiles": 4,
        "back_map": "MAP_HEADER_SOLACEON_TOWN",
        "cine_wait_frames": 120,
    },
    {
        "id": "route201_sandgem",
        "label": "Route 201 <-> Sandgem Town",
        "vars": {},
        "flags": {},
        "start_map": "MAP_HEADER_ROUTE_201",
        "start_pos": (157, 845),
        "start_dir": "DIR_EAST",
        "forward_dir": "RIGHT",
        "forward_tiles": 5,
        "forward_map": "MAP_HEADER_SANDGEM_TOWN",
        "back_dir": "LEFT",
        "back_tiles": 5,
        "back_map": "MAP_HEADER_ROUTE_201",
        "cine_wait_frames": 180,
    },
    {
        "id": "route202_jubilife",
        "label": "Route 202 <-> Jubilife City",
        "vars": {},
        "flags": {},
        "start_map": "MAP_HEADER_ROUTE_202",
        "start_pos": (175, 802),
        "start_dir": "DIR_NORTH",
        "forward_dir": "UP",
        "forward_tiles": 4,
        "forward_map": "MAP_HEADER_JUBILIFE_CITY",
        "back_dir": "DOWN",
        "back_tiles": 4,
        "back_map": "MAP_HEADER_ROUTE_202",
        "cine_wait_frames": 180,
    },
]


def walk_across(sess, direction, tiles, expected_map, cine_wait_frames=0):
    """Walk `tiles` steps in `direction` (with a small retry margin) until on expected_map."""
    st = sess.state()
    for _ in range(tiles):
        st = sess.walk(direction, tiles=1, hold_frames=16, settle_frames=4)
        if st.get("map") == expected_map and st.get("script") is not None:
            # A city-entry cinematic or script started on crossing; let it finish below.
            break

    # If the first press only turned the player or a bump slowed a tile, nudge up to 3 extra tiles.
    for _ in range(3):
        if st.get("map") == expected_map:
            break
        if st.get("script") is not None:
            break
        st = sess.walk(direction, tiles=1, hold_frames=16, settle_frames=4)

    if cine_wait_frames > 0:
        # Step through any city-entry camera cinematic or OnFrame transition.
        st = sess.settle(frames=max(600, cine_wait_frames))
        if sess.cine:
            sess.step(cine_wait_frames)
            st = sess.settle(frames=600)
    else:
        st = sess.settle(frames=600)
    return st


def check_point(sess, step_label, expected_map, min_tex_free, shot_name=None):
    """Verify map, billboards, and VRAM at one seam checkpoint; return a result dict."""
    st = sess.state()
    actual_map = st.get("map")
    player = st.get("player") or {}
    pos = (player.get("x"), player.get("z"))

    bb_data = {}
    vram = {}
    errors = []

    if actual_map != expected_map:
        errors.append(f"expected map {expected_map}, got {actual_map} at {pos}")

    try:
        bb_data = sess.assert_billboards_healthy(require_player=True)
    except AssertionError as e:
        errors.append(str(e))
        try:
            bb_data = sess.inspect("billboards").get("data") or {}
        except Exception:
            pass

    try:
        vram = sess.assert_vram_healthy(min_tex_free=min_tex_free)
    except AssertionError as e:
        errors.append(str(e))
        try:
            vram = (sess.memory().get("memory") or {}).get("vram") or {}
        except Exception:
            pass

    if shot_name and sess.out_dir:
        try:
            sess.screenshot(shot_name, png=True)
        except Exception as e:
            errors.append(f"screenshot failed: {e}")

    return {
        "name": step_label,
        "ok": not errors,
        "map": actual_map or "?",
        "pos": pos,
        "tex_free": vram.get("tex_free"),
        "pltt_free": vram.get("pltt_free"),
        "bb_drawn": bb_data.get("drawn"),
        "bb_count": bb_data.get("count"),
        "bb_oob": bb_data.get("oob_count"),
        "bb_zero": bb_data.get("zero_tex_count"),
        "error": "; ".join(errors),
    }


def print_table(rows):
    headers = ("CHECKPOINT", "STATUS", "MAP", "TILE", "TEX_FREE", "BILLBOARDS", "OOB/0TEX")
    lines = [headers]
    for r in rows:
        tex_s = str(r["tex_free"]) if r["tex_free"] is not None else "?"
        bb_s = f"{r['bb_drawn']}/{r['bb_count']}" if r["bb_count"] is not None else "?"
        err_s = (
            f"{r['bb_oob']}/{r['bb_zero']}"
            if r["bb_oob"] is not None or r["bb_zero"] is not None
            else "?"
        )
        map_short = (r["map"] or "?").replace("MAP_HEADER_", "")
        pos_s = f"({r['pos'][0]},{r['pos'][1]})"
        lines.append((
            r["name"],
            "PASS" if r["ok"] else "FAIL",
            map_short,
            pos_s,
            tex_s,
            bb_s,
            err_s,
        ))

    widths = [max(len(row[i]) for row in lines) for i in range(len(headers))]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*lines[0]))
    print("  ".join("-" * w for w in widths))
    for row, data in zip(lines[1:], rows):
        print(fmt.format(*row))
        if not data["ok"] and data["error"]:
            print(f"    -> {data['error']}")


def run_seams(args):
    rows = []
    t0 = time.time()
    with ReproSession(
        build_dir=args.build,
        save=args.save,
        layout=args.layout,
        renderer=args.renderer,
        cine=args.cine,
        out_dir=args.out,
    ) as sess:
        st = sess.boot_to_field()
        p = st.get("player") or {}
        print(
            f"Booted to {st.get('map')} ({p.get('x')},{p.get('z')}) "
            f"[layout={args.layout} renderer={args.renderer} cine={args.cine}]"
        )

        for seam in SEAMS:
            for k, v in seam["vars"].items():
                sess.set_var(k, v)
            for k, v in seam["flags"].items():
                sess.set_flag(k, v)

            sx, sz = seam["start_pos"]
            sess.warp(seam["start_map"], sx, sz, dir=seam["start_dir"])

            # Forward crossing
            walk_across(
                sess,
                seam["forward_dir"],
                seam["forward_tiles"],
                seam["forward_map"],
                cine_wait_frames=seam["cine_wait_frames"],
            )
            rows.append(
                check_point(
                    sess,
                    f"{seam['id']}:fwd",
                    seam["forward_map"],
                    args.min_tex_free,
                    shot_name=f"{seam['id']}_fwd" if args.out else None,
                )
            )

            # Return crossing
            walk_across(
                sess,
                seam["back_dir"],
                seam["back_tiles"],
                seam["back_map"],
                cine_wait_frames=0,
            )
            rows.append(
                check_point(
                    sess,
                    f"{seam['id']}:back",
                    seam["back_map"],
                    args.min_tex_free,
                    shot_name=f"{seam['id']}_back" if args.out else None,
                )
            )

    print()
    print_table(rows)
    passed = sum(1 for r in rows if r["ok"])
    total = len(rows)
    elapsed = time.time() - t0
    print(f"\n{'PASS' if passed == total else 'FAIL'}: {passed}/{total} seam checks passed in {elapsed:.1f}s")
    return 0 if passed == total else 1


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--build",
        default=None,
        help="build dir containing main (default: auto-detect build_macos_release or build_macos)",
    )
    ap.add_argument(
        "--out",
        default=None,
        help="optional output directory for screenshots and game.stderr.log",
    )
    cine_grp = ap.add_mutually_exclusive_group()
    cine_grp.add_argument(
        "--cine",
        dest="cine",
        action="store_true",
        default=True,
        help="enable overworld city-entry cinematics (default: on)",
    )
    cine_grp.add_argument(
        "--no-cine",
        dest="cine",
        action="store_false",
        help="disable overworld city-entry cinematics",
    )
    ap.add_argument("--save", default=None, help="override .sav/.dsv fixture path")
    ap.add_argument("--layout", default="wide", help="ScreenLayout (default: wide)")
    ap.add_argument("--renderer", default="gpu", help="SIM_RENDERER backend (default: gpu)")
    ap.add_argument(
        "--min-tex-free",
        type=int,
        default=16384,
        help="minimum required free texture VRAM in bytes (default: 16384)",
    )
    args = ap.parse_args()
    try:
        return run_seams(args)
    except ReproError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
