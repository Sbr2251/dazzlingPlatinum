#!/usr/bin/env python3
"""Headless verification suite for the Following Pokemon engine (GAME-29).

Tests:
  1. Follower spawn & healthy billboard/VRAM state (SIM_FX_FOLLOWER=1).
  2. Smooth trailing on walking/turning and player pass-through swap.
  3. Overworld seam crossings: Solaceon Town <-> Route 210 South and
     Route 209 <-> Solaceon Town with 0 corrupt billboards & 0 VRAM OOM.
  4. Talk interaction via both `follower_talk` JSON command and Press-A
     facing the follower.
  5. Live party lead swap to a Gen 5 species (SPECIES_DEINO) and a large
     64x64 species (SPECIES_STEELIX), plus large-species indoor retraction.
  6. Live FOLLOWER=OFF/ON toggle and clean boot with SIM_FX_FOLLOWER=0.

Usage:
    python3 tools/dazzling/test/test_follower.py [--build build_macos_release] \
        [--out /tmp/follower_test] [--require-archive]
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


def manhattan(x1, z1, x2, z2):
    return abs(x1 - x2) + abs(z1 - z2)


def follower_state(sess):
    r = sess.cmd({"cmd": "follower_state"})
    if not r.get("ok"):
        raise ReproError(f"follower_state failed: {r}")
    return r


def assert_healthy(sess, label, min_tex_free=16384):
    bb = sess.assert_billboards_healthy(require_player=True)
    vram = sess.assert_vram_healthy(min_tex_free=min_tex_free)
    return bb, vram


def walk_to_map(sess, direction, tiles, expected_map):
    st = sess.state()
    for _ in range(tiles + 4):
        if st.get("map") == expected_map:
            break
        st = sess.walk(direction, tiles=1, hold_frames=16, settle_frames=6)
    st = sess.settle(frames=600)
    if st.get("map") != expected_map:
        raise AssertionError(
            f"expected map {expected_map} after walking {direction}, got {st.get('map')} at {st.get('player')}"
        )
    return st


def run_enabled_suite(build_dir, save, out_dir, require_archive):
    results = []

    def record(name, ok, detail=""):
        results.append((name, ok, detail))
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}" + (f" -- {detail}" if detail else ""))

    with ReproSession(
        build_dir=build_dir,
        save=save,
        layout="wide",
        cine=False,
        out_dir=out_dir,
        extra_env={"SIM_FX_FOLLOWER": "1"},
    ) as sess:
        sess.boot_to_field()
        fs = follower_state(sess)

        if not fs.get("available"):
            if require_archive:
                raise AssertionError(f"follow_mon.narc not available: {fs}")
            assert_healthy(sess, "no_archive_boot")
            record("graceful_missing_archive", not fs.get("active"), f"available=False, active={fs.get('active')}")
            return results

        # 1. Spawn on Solaceon Town
        sess.warp("MAP_HEADER_SOLACEON_TOWN", 560, 648, "DIR_NORTH")
        sess.step(12)
        st = sess.state()
        fs = follower_state(sess)
        p = st["player"]
        dist = manhattan(p["x"], p["z"], fs["x"], fs["z"])
        assert fs["active"] and not fs["hidden"], f"follower not active/visible after warp: {fs}"
        assert fs["species"] > 0, f"invalid follower species: {fs}"
        assert dist == 1, f"expected follower adjacent to player, player={p} follower={fs}"
        bb, vram = assert_healthy(sess, "spawn")
        if out_dir:
            sess.screenshot("01_spawn")
        record(
            "spawn_and_health",
            True,
            f"species={fs.get('species_name')} pos=({fs['x']},{fs['z']}) bb={bb.get('drawn')}/{bb.get('count')} tex_free={vram.get('tex_free')}",
        )

        # 2. Walking, turning, and pass-through swap
        start_fx, start_fz = fs["x"], fs["z"]
        sess.walk("UP", tiles=3, hold_frames=16, settle_frames=6)
        sess.step(10)
        st_walk = sess.state()
        fs_walk = follower_state(sess)
        p_walk = st_walk["player"]
        dist_walk = manhattan(p_walk["x"], p_walk["z"], fs_walk["x"], fs_walk["z"])
        assert (fs_walk["x"], fs_walk["z"]) != (start_fx, start_fz), f"follower did not move: {fs_walk}"
        assert dist_walk == 1, f"follower not trailing adjacent after walk: player={p_walk} follower={fs_walk}"
        assert_healthy(sess, "walk_north")

        # Walk directly back onto follower's tile (pass-through swap)
        target_swap_x, target_swap_z = fs_walk["x"], fs_walk["z"]
        sess.walk("DOWN", tiles=2, hold_frames=16, settle_frames=6)
        sess.step(10)
        st_swap = sess.state()
        fs_swap = follower_state(sess)
        p_swap = st_swap["player"]
        assert p_swap["z"] >= target_swap_z, f"player blocked by follower on pass-through: player={p_swap} target_z={target_swap_z}"
        assert manhattan(p_swap["x"], p_swap["z"], fs_swap["x"], fs_swap["z"]) == 1, (
            f"follower did not swap cleanly behind player: player={p_swap} follower={fs_swap}"
        )
        assert_healthy(sess, "pass_through_swap")
        record(
            "walk_and_pass_through",
            True,
            f"player=({p_swap['x']},{p_swap['z']}) follower=({fs_swap['x']},{fs_swap['z']})",
        )

        # 3. Seam crossings: Solaceon Town <-> Route 210 South <-> Route 209
        sess.warp("MAP_HEADER_SOLACEON_TOWN", 560, 642, "DIR_NORTH")
        sess.step(10)
        walk_to_map(sess, "UP", 4, "MAP_HEADER_ROUTE_210_SOUTH")
        fs_210 = follower_state(sess)
        assert fs_210["active"] and not fs_210["hidden"], f"follower lost crossing to Route 210 South: {fs_210}"
        assert_healthy(sess, "seam_solaceon_to_r210s")

        walk_to_map(sess, "DOWN", 4, "MAP_HEADER_SOLACEON_TOWN")
        fs_sol = follower_state(sess)
        assert fs_sol["active"] and not fs_sol["hidden"], f"follower lost returning to Solaceon: {fs_sol}"
        assert_healthy(sess, "seam_r210s_to_solaceon")

        sess.warp("MAP_HEADER_ROUTE_209", 560, 674, "DIR_NORTH")
        sess.step(10)
        walk_to_map(sess, "UP", 4, "MAP_HEADER_SOLACEON_TOWN")
        fs_209_sol = follower_state(sess)
        assert fs_209_sol["active"] and not fs_209_sol["hidden"], f"follower lost crossing Route 209 -> Solaceon: {fs_209_sol}"
        assert_healthy(sess, "seam_r209_to_solaceon")

        walk_to_map(sess, "DOWN", 4, "MAP_HEADER_ROUTE_209")
        fs_209_back = follower_state(sess)
        assert fs_209_back["active"] and not fs_209_back["hidden"], f"follower lost crossing Solaceon -> Route 209: {fs_209_back}"
        assert_healthy(sess, "seam_solaceon_to_r209")
        record("seam_crossings", True, "Solaceon <-> Route 210 South & Route 209 <-> Solaceon")

        # 4. Talk via follower_talk command AND Press-A facing follower
        talk_res = sess.cmd({"cmd": "follower_talk"})
        assert talk_res.get("ok"), f"follower_talk failed: {talk_res}"
        assert talk_res.get("emote", 0) > 0, f"expected non-zero emote: {talk_res}"
        assert bool(talk_res.get("message")), f"expected non-empty message: {talk_res}"
        sess.step(20)
        assert_healthy(sess, "after_headless_talk")

        # Turn to face follower and press A
        st_now = sess.state()
        fs_now = follower_state(sess)
        dx = fs_now["x"] - st_now["player"]["x"]
        dz = fs_now["z"] - st_now["player"]["z"]
        face_key = "UP" if dz < 0 else ("DOWN" if dz > 0 else ("LEFT" if dx < 0 else "RIGHT"))
        sess.press([face_key], frames=3)
        sess.step(6)
        sess.press(["A"], frames=4)
        sess.step(40)
        # Dismiss dialogue box
        for _ in range(4):
            sess.press(["A"], frames=4)
            sess.step(20)
        sess.settle(frames=240)
        assert_healthy(sess, "after_press_a_talk")
        record(
            "follower_talk_and_press_a",
            True,
            f"emote={talk_res.get('emote_name')} mood={talk_res.get('mood')} msg={talk_res.get('message')!r}",
        )

        # 5. Lead swap: Gen 5 species (SPECIES_DEINO) & Large species (SPECIES_STEELIX)
        sess.warp("MAP_HEADER_SOLACEON_TOWN", 560, 648, "DIR_NORTH")
        sess.step(10)
        r_gen5 = sess.cmd({"cmd": "set_party", "slot": 0, "species": "SPECIES_DEINO", "level": 50})
        assert r_gen5.get("ok"), f"set_party DEINO failed: {r_gen5}"
        sess.step(12)
        fs_gen5 = follower_state(sess)
        assert fs_gen5["active"] and not fs_gen5["hidden"], f"Gen 5 follower not active: {fs_gen5}"
        assert fs_gen5["species"] == r_gen5["species_id"], f"species mismatch: {fs_gen5} vs {r_gen5}"
        assert not fs_gen5["large"], f"DEINO should not be large: {fs_gen5}"
        assert_healthy(sess, "gen5_deino")
        if out_dir:
            sess.screenshot("02_gen5_deino")
        record("lead_swap_gen5", True, f"species={fs_gen5.get('species_name')} large={fs_gen5['large']}")

        r_large = sess.cmd({"cmd": "set_party", "slot": 0, "species": "SPECIES_STEELIX", "level": 50})
        assert r_large.get("ok"), f"set_party STEELIX failed: {r_large}"
        sess.step(12)
        fs_large = follower_state(sess)
        assert fs_large["active"] and not fs_large["hidden"], f"large follower not active outdoors: {fs_large}"
        assert fs_large["species"] == r_large["species_id"], f"species mismatch: {fs_large} vs {r_large}"
        assert fs_large["large"], f"STEELIX should be large: {fs_large}"
        assert_healthy(sess, "large_steelix_outdoors")
        if out_dir:
            sess.screenshot("03_large_steelix")

        # Indoors check: large species retracts cleanly inside a Pokecenter
        sess.warp("MAP_HEADER_SOLACEON_TOWN_POKECENTER_1F", 7, 10, "DIR_NORTH")
        sess.step(12)
        fs_indoor = follower_state(sess)
        assert fs_indoor["large"] and fs_indoor["hidden"], f"large species should retract indoors: {fs_indoor}"
        assert_healthy(sess, "large_steelix_indoors")
        record("lead_swap_large_and_indoor_retract", True, f"outdoors=visible indoors_hidden={fs_indoor['hidden']}")

        # 6. Live FOLLOWER=OFF / ON toggle
        sess.warp("MAP_HEADER_SOLACEON_TOWN", 560, 648, "DIR_NORTH")
        sess.step(10)
        r_off = sess.cmd({"cmd": "set_follower", "enabled": False})
        assert r_off.get("ok") and not r_off.get("enabled"), f"set_follower False failed: {r_off}"
        sess.step(10)
        fs_off = follower_state(sess)
        assert not fs_off["active"], f"follower still active after toggle OFF: {fs_off}"
        assert_healthy(sess, "toggle_off")

        r_on = sess.cmd({"cmd": "set_follower", "enabled": True})
        assert r_on.get("ok") and r_on.get("enabled"), f"set_follower True failed: {r_on}"
        sess.step(10)
        fs_on = follower_state(sess)
        assert fs_on["active"], f"follower did not respawn after toggle ON: {fs_on}"
        assert_healthy(sess, "toggle_on")
        record("live_toggle_off_on", True, "OFF -> despawned, ON -> respawned cleanly")

    return results


def run_disabled_boot_check(build_dir, save):
    with ReproSession(
        build_dir=build_dir,
        save=save,
        layout="wide",
        cine=False,
        extra_env={"SIM_FX_FOLLOWER": "0"},
    ) as sess:
        sess.boot_to_field()
        fs = follower_state(sess)
        assert not fs.get("active"), f"follower should be inactive when SIM_FX_FOLLOWER=0: {fs}"
        assert_healthy(sess, "disabled_boot")
        print("  [PASS] disabled_boot_sim_fx_follower_0 -- active=False, billboards & VRAM healthy")


def main():
    parser = argparse.ArgumentParser(description="Following Pokemon headless test suite")
    parser.add_argument("--build", default=None, help="Build directory containing ./main")
    parser.add_argument("--save", default=None, help="Path to .sav fixture")
    parser.add_argument("--out", default=None, help="Optional directory for screenshots/logs")
    parser.add_argument(
        "--require-archive",
        action="store_true",
        help="Fail if follow_mon.narc is not present in the build dir",
    )
    args = parser.parse_args()

    t0 = time.time()
    print("Running Following Pokemon headless test suite...")
    run_enabled_suite(args.build, args.save, args.out, args.require_archive)
    run_disabled_boot_check(args.build, args.save)
    print(f"All Following Pokemon checks PASSED in {time.time() - t0:.1f}s.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
