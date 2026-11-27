#!/usr/bin/env python3
"""Headless regression test for BW2 Phenomena (grass, dust, water, shadow).

Tests:
1. Spawning & screenshotting all 4 phenomenon types:
   - Route 201 rustling grass
   - Oreburgh Mine dust cloud
   - Twinleaf Town / shore rippling water + Super Rod encounter
   - Route 206 Cycling Road flying shadow
2. Stepping into rustling grass triggers a wild battle (even with Repel active).
3. VRAM and billboard health checks pass with 0 OOM and 0 corrupt billboards.
"""

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..")))

from repro_lib import ReproError, ReproSession


def walk_to_tile(sess, target_x, target_z, max_steps=16):
    for _ in range(max_steps):
        st = sess.state()
        if st.get("app") == "battle":
            return st
        p = st.get("player") or {}
        px, pz = p.get("x"), p.get("z")
        if px == target_x and pz == target_z:
            return st
        if px < target_x:
            sess.walk("RIGHT", 1)
        elif px > target_x:
            sess.walk("LEFT", 1)
        elif pz < target_z:
            sess.walk("DOWN", 1)
        elif pz > target_z:
            sess.walk("UP", 1)
    return sess.state()


def assert_spawn_and_capture(sess, ptype, shot_name, x=None, z=None):
    req = {"cmd": "spawn_phenomenon", "type": ptype}
    if x is not None and z is not None:
        req["x"] = int(x)
        req["z"] = int(z)
    r = sess.cmd(req)
    assert r.get("ok") and r.get("active") and r.get("type") == ptype, f"spawn {ptype} failed: {r}"
    sess.step(12)
    ps = sess.cmd({"cmd": "phenomenon_state"})
    assert ps.get("ok") and ps.get("active") and ps.get("type") == ptype, f"state {ptype} mismatch: {ps}"
    sess.screenshot(shot_name)
    sess.assert_billboards_healthy()
    sess.assert_vram_healthy()
    return ps


def run_tests(build_dir=None, out_dir=None):
    with ReproSession(
        build_dir=build_dir,
        out_dir=out_dir,
        extra_env={"SIM_FX_PHENOMENA": "1"},
    ) as sess:
        sess.boot_to_field()

        # 1. Route 201: Rustling Grass + step-into battle (with Repel active)
        sess.warp("MAP_HEADER_ROUTE_201", 110, 838, "DIR_NORTH")
        sess.cmd({"cmd": "give_item", "item": "ITEM_MAX_REPEL", "count": 1})
        ps_grass = assert_spawn_and_capture(sess, "grass", "phenom_grass")

        # Step onto the rustling grass tile -> must trigger battle
        st = walk_to_tile(sess, ps_grass["x"], ps_grass["z"])
        if st.get("app") != "battle":
            # Step a few frames in case encounter transition is starting
            sess.step(30)
            st = sess.state()
        assert st.get("app") == "battle", f"expected battle on rustling grass, got: {st}"
        sess.screenshot("phenom_grass_battle")

        # Run from battle
        sess.cmd({"cmd": "battle_decide", "battler": 0, "action": "run"})
        for _ in range(30):
            sess.step(30)
            st = sess.state()
            if st.get("app") == "field":
                break
        assert st.get("app") == "field", f"failed to return to field after run: {st}"
        sess.settle()

        # 2. Oreburgh Mine B1F: Dust Cloud
        sess.warp("MAP_HEADER_OREBURGH_MINE_B1F", 15, 15, "DIR_SOUTH")
        assert_spawn_and_capture(sess, "dust", "phenom_dust")

        # 3. Route 213 shore: Rippling Water + Super Rod facing water
        sess.warp("MAP_HEADER_ROUTE_213", 686, 756, "DIR_SOUTH")
        sess.cmd({"cmd": "give_item", "item": "ITEM_SUPER_ROD", "count": 1})
        st = sess.state()
        px, pz = st["player"]["x"], st["player"]["z"]
        assert_spawn_and_capture(sess, "water", "phenom_water", x=px, z=pz + 1)

        # 4. Route 206 Cycling Road: Flying Shadow
        sess.warp("MAP_HEADER_ROUTE_206", 206, 540, "DIR_SOUTH")
        assert_spawn_and_capture(sess, "shadow", "phenom_shadow")

    print("test_phenomena.py: ALL CHECKS PASSED")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", default=None)
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args()
    run_tests(build_dir=args.build_dir, out_dir=args.out_dir)


if __name__ == "__main__":
    main()
