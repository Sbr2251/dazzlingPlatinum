#!/usr/bin/env python3
"""Unit tests for run.py against fake_game.py. No game build needed.
Run: python3 -m unittest tools.dazzling.test.test_runner  (or this file directly)
"""
import json, os, struct, sys, tempfile, time, unittest
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run as runner  # noqa: E402
import gate  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FAKE = os.path.join(HERE, "fake_game.py")

def write_scenario(tmp, name, data):
    p = os.path.join(tmp, name + ".json")
    with open(p, "w") as f:
        json.dump(data, f)
    return p

class TestAssertions(unittest.TestCase):
    def test_state_get_and_ops(self):
        st = {"player": {"map": "M", "x": 3}, "party": [{"level": 5}]}
        self.assertIsNone(runner.check_assertion(st, {"player.map": "M"}))
        self.assertIsNone(runner.check_assertion(st, {"path": "party.0.level", "op": "ge", "value": 5}))
        self.assertIn("expected", runner.check_assertion(st, {"player.x": 4}))
        self.assertIn("no 'player.y'", runner.check_assertion(st, {"player.y": 1}))

    def test_bmp_compare(self):
        sys.path.insert(0, HERE)
        from fake_game import write_bmp
        with tempfile.TemporaryDirectory() as d:
            a, b, c = (os.path.join(d, n) for n in ("a.bmp", "b.bmp", "c.bmp"))
            write_bmp(a, 16, 16, 7); write_bmp(b, 16, 16, 7); write_bmp(c, 16, 16, 100)
            self.assertTrue(runner.compare_images(a, b)[0])
            self.assertFalse(runner.compare_images(a, c, tolerance=0.0)[0])

    def test_compare_exact_fast_path_avoids_pixel_loop(self):
        image = (2, 2, bytes(range(12)))
        with mock.patch.object(runner, "load_image", side_effect=[image, image]), \
             mock.patch("builtins.abs", side_effect=AssertionError("pixel loop entered")):
            ok, fraction, _ = runner.compare_images("a", "b")
        self.assertTrue(ok)
        self.assertEqual(fraction, 0.0)

    def test_save_png_signature_and_dimensions(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "tiny.png")
            runner.save_png(path, 2, 1, bytes((255, 0, 0, 0, 255, 0)))
            with open(path, "rb") as f:
                data = f.read()
            self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(struct.unpack(">II", data[16:24]), (2, 1))

class TestRunnerEndToEnd(unittest.TestCase):
    def run_one(self, tmp, data, record=False):
        p = write_scenario(tmp, "case", data)
        name, ok, msg, client = runner.run_scenario(p, FAKE, record=record, timeout=30, work_root=tmp)
        client.close()
        return ok, msg

    def test_warp_move_assert_wait(self):
        with tempfile.TemporaryDirectory() as d:
            ok, msg = self.run_one(d, {
                "name": "case",
                "start": {"warp": {"map": "MAP_HEADER_ROUTE_201", "x": 5, "z": 5, "dir": "DIR_NORTH"}},
                "steps": [
                    {"press": "UP", "frames": 2},
                    {"wait_until": {"app": "field"}, "timeout_frames": 50},
                    {"assert": {"player.map": "MAP_HEADER_ROUTE_201", "player.z": 3}},
                ]})
            self.assertTrue(ok, msg)

    def test_failure_reports_step_and_state(self):
        with tempfile.TemporaryDirectory() as d:
            ok, msg = self.run_one(d, {
                "name": "case", "steps": [{"assert": {"app": "battle"}}]})
            self.assertFalse(ok)
            self.assertIn("FAIL step 0", msg)
            self.assertIn("state:", msg)

    def test_wait_until_timeout(self):
        with tempfile.TemporaryDirectory() as d:
            ok, msg = self.run_one(d, {
                "name": "case", "steps": [{"wait_until": {"app": "battle"}, "timeout_frames": 20}]})
            self.assertFalse(ok)
            self.assertIn("wait_until", msg)

    def test_record_then_compare_screenshot(self):
        with tempfile.TemporaryDirectory() as d:
            sc = {"name": "case", "start": {"warp": {"map": "MAP_HEADER_X", "x": 0, "z": 0}},
                  "steps": [{"step": 40}, {"screenshot": "shot", "reference": "ref.bmp"}]}
            ok, msg = self.run_one(d, sc, record=True)
            self.assertTrue(ok, msg)
            self.assertTrue(os.path.exists(os.path.join(d, "ref.bmp")))
            ok, msg = self.run_one(d, sc, record=False)
            self.assertTrue(ok, msg)

    def test_no_child_alive_after_scenario(self):
        # Leak guard: run a scenario the way run.py's worker does and check
        # no game process survives it, pass or fail.
        with tempfile.TemporaryDirectory() as d:
            for data in ({"name": "case", "steps": [{"step": 40}]},
                         {"name": "case", "steps": [{"assert": {"app": "battle"}}]}):
                path = write_scenario(d, "case", data)
                client = None
                try:
                    _name, _ok, _msg, client = runner.run_scenario(path, FAKE, timeout=30, work_root=d)
                finally:
                    if client is not None:
                        client.close()
                self.assertIsNotNone(client.proc.poll())
            self.assertEqual(runner.GameClient.live_count(), 0)

    def test_talk_and_battle_stub(self):
        with tempfile.TemporaryDirectory() as d:
            ok, msg = self.run_one(d, {
                "name": "case",
                "steps": [{"step": 40}, {"talk": "LOCALID_X"},
                          {"assert": {"message_waiting": True}},
                          {"press": "START", "frames": 1},
                          {"assert": {"in_battle": True}},
                          {"press": "B", "frames": 1},
                          {"assert": {"in_battle": False}}]})
            self.assertTrue(ok, msg)

    def test_crop_and_diff_artifacts(self):
        sys.path.insert(0, HERE)
        from fake_game import write_bmp
        with tempfile.TemporaryDirectory() as d:
            a, b = os.path.join(d, "a.bmp"), os.path.join(d, "b.bmp")
            write_bmp(a, 16, 16, 7); write_bmp(b, 16, 16, 100)
            self.assertTrue(runner.compare_images(a, a)[0])
            ep, ap, dp, cp, bbox, max_delta = runner.write_diff_images(a, b, d, "shot", crop=[0, 0, 8, 8])
            for pth in (ep, ap, dp, cp):
                self.assertTrue(os.path.exists(pth), pth)
            self.assertEqual(runner.load_image(ep)[:2], (8, 8))
            self.assertEqual(bbox, (0, 0, 7, 7))
            self.assertGreater(max_delta, 0)
            with open(cp, "rb") as f:
                data = f.read()
            self.assertEqual(struct.unpack(">II", data[16:24]), (28, 8))

    def test_diff_bbox_and_max_delta_are_exact(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = os.path.join(d, "a.bmp"), os.path.join(d, "b.bmp")
            base = bytearray(b"\x00" * (4 * 3 * 3))
            changed = bytearray(base)
            changed[(1 * 4 + 2) * 3 + 1] = 17
            runner.save_bmp(a, 4, 3, bytes(changed)); runner.save_bmp(b, 4, 3, bytes(base))
            result = runner.write_diff_images(a, b, d, "one")
            self.assertEqual(result[4], (2, 1, 2, 1))
            self.assertEqual(result[5], 17)

    def test_record_stores_cropped_reference(self):
        with tempfile.TemporaryDirectory() as d:
            sc = {"name": "case", "steps": [{"step": 40},
                  {"screenshot": "shot", "reference": "ref.bmp", "crop": [0, 0, 8, 8]}]}
            ok, msg = self.run_one(d, sc, record=True)
            self.assertTrue(ok, msg)
            self.assertEqual(runner.load_image(os.path.join(d, "ref.bmp"))[:2], (8, 8))
            ok, msg = self.run_one(d, sc, record=False)
            self.assertTrue(ok, msg)

    def test_compare_cropped_actual_vs_stored_cropped_ref(self):
        sys.path.insert(0, HERE)
        from fake_game import write_bmp
        with tempfile.TemporaryDirectory() as d:
            a, b = os.path.join(d, "a.bmp"), os.path.join(d, "b.bmp")
            write_bmp(a, 16, 16, 7)
            img = runner.crop_image(runner.load_image(a), [0, 0, 8, 8])
            runner.save_bmp(b, img[0], img[1], img[2])
            self.assertTrue(runner.compare_images(a, b, crop=[0, 0, 8, 8])[0])

    def test_wait_battle_event_step(self):
        with tempfile.TemporaryDirectory() as d:
            ok, msg = self.run_one(d, {
                "name": "case",
                "steps": [{"start_battle": {"spec": "nope.json"}},
                          {"wait_battle_event": {"type": "stat_stage", "battler": 0}, "timeout_frames": 100},
                          {"battle_event": {"type": "battle_start"}}]})
            self.assertTrue(ok, msg)

    def test_start_battle_and_decide_steps(self):
        with tempfile.TemporaryDirectory() as d:
            ok, msg = self.run_one(d, {
                "name": "case",
                "steps": [{"start_battle": {"spec": "nope.json"}},
                          {"battle_decide": {"battler": 0, "action": "move", "move_index": 0, "mega": True}},
                          {"battle_event": {"type": "battle_start"}},
                          {"assert": {"app": "battle", "battle.battlers.0.mega": True}}]})
            self.assertTrue(ok, msg)


    def test_tolerance_gpu_overrides_tolerance(self):
        # Record a screenshot at frame 40, then re-run with an extra step so
        # the frame (and pixels) differ: tolerance 0.0 fails, but
        # tolerance_gpu 1.0 passes when use_gpu_tolerance is set.
        with tempfile.TemporaryDirectory() as d:
            sc = {"name": "case", "steps": [{"step": 40},
                  {"screenshot": "shot", "reference": "ref.bmp", "tolerance": 0.0, "tolerance_gpu": 1.0}]}
            ok, msg = self.run_one(d, sc, record=True)
            self.assertTrue(ok, msg)
            p2 = write_scenario(d, "case2", {"name": "case",
                "steps": [{"step": 100},
                          {"screenshot": "shot", "reference": "ref.bmp", "tolerance": 0.0, "tolerance_gpu": 1.0}]})
            name, ok, msg, client = runner.run_scenario(p2, FAKE, timeout=30, work_root=d)
            client.close()
            self.assertFalse(ok, "tolerance 0.0 should fail on a different frame")
            name, ok, msg, client = runner.run_scenario(p2, FAKE, timeout=30, work_root=d, use_gpu_tolerance=True)
            client.close()
            self.assertTrue(ok, msg)

    def test_scenario_env_and_config(self):
        with tempfile.TemporaryDirectory() as d:
            pth = write_scenario(d, "case", {"name": "case",
                "env": {"SIM_HIRESTEXT": "1"}, "config": {"ScreenLayout": "Horizontal"},
                "steps": [{"step": 10}]})
            name, ok, msg, client = runner.run_scenario(pth, FAKE, timeout=30, work_root=d)
            self.assertTrue(ok, msg)
            # Fake game returns early from make_run_dir, so no config file is
            # written for it; the scenario still runs (env/config accepted).
            client.close()

    def test_reload_config_step(self):
        with tempfile.TemporaryDirectory() as d:
            save = os.path.join(d, "s.sav")
            with open(save, "w") as f:
                f.write("x")
            pth = write_scenario(d, "case", {"name": "case",
                "start": {"save": save},
                "steps": [{"step": 10}, {"reload_config": {"InternalResolutionScale": "4"}}, {"step": 10}]})
            name, ok, msg, client = runner.run_scenario(pth, FAKE, timeout=30, work_root=d)
            self.assertTrue(ok, msg)
            with open(os.path.join(client.dir, "sim_config.ini")) as f:
                self.assertIn("InternalResolutionScale=4", f.read())
            client.close()

    def test_compare_backends_mock(self):
        with tempfile.TemporaryDirectory() as d:
            pth = write_scenario(d, "case", {"name": "case", "steps": [{"step": 10}]})
            rc = runner.main(["--mock", "--compare-backends", "--jobs", "1",
                              "--work-root", os.path.join(d, "work"), pth])
            self.assertEqual(rc, 0)

    def test_boot_loop_fast_fail_and_stderr_tail(self):
        with tempfile.TemporaryDirectory() as d:
            began = time.monotonic()
            client = runner.GameClient(FAKE, d, "loop", env_extra={"FAKE_BOOT_LOOP": "1"})
            try:
                with self.assertRaisesRegex(runner.GameError, "boot soft-reset loop detected"):
                    client.cmd({"cmd": "state"}, timeout=10)
                self.assertLess(time.monotonic() - began, 2.0)
                self.assertGreaterEqual(client.stderr_tail().count("SIM headless=1"), 3)
            finally:
                client.close()

    def test_tier_tag_and_json_report(self):
        with tempfile.TemporaryDirectory() as d:
            scenarios = os.path.join(d, "scenarios"); os.mkdir(scenarios)
            write_scenario(scenarios, "core_title_screen_animation",
                           {"name": "title", "steps": [{"step": 1}]})
            write_scenario(scenarios, "other",
                           {"name": "other", "tags": ["menu"], "steps": [{"step": 1}]})
            report = os.path.join(d, "report.json")
            rc = runner.main(["--mock", "--tier", "smoke", "--scenarios-dir", scenarios,
                              "--json-report", report, "-j", "1"])
            self.assertEqual(rc, 0)
            with open(report) as f:
                data = json.load(f)
            self.assertEqual([x["name"] for x in data["scenarios"]], ["title"])
            self.assertEqual(data["passed"], 1)
            self.assertTrue(data["scenarios"][0]["workdir"])
            rc = runner.main(["--mock", "--tag", "menu", "--scenarios-dir", scenarios,
                              "-j", "1"])
            self.assertEqual(rc, 0)

    def test_failure_report_has_stderr_tail_field(self):
        with tempfile.TemporaryDirectory() as d:
            report = os.path.join(d, "report.json")
            pth = write_scenario(d, "bad", {"name": "bad", "steps": [{"assert": {"app": "nope"}}]})
            self.assertEqual(runner.main(["--mock", "--json-report", report, pth]), 1)
            with open(report) as f:
                item = json.load(f)["scenarios"][0]
            self.assertIn("stderr_tail", item)
            self.assertEqual(item["failure_step"], 0)

    def test_health_checks_pass_when_counters_zero(self):
        with tempfile.TemporaryDirectory() as d:
            ok, msg = self.run_one(d, {
                "name": "healthy_field",
                "steps": [{"step": 35}],
                "assertions": [{"app": "field"}],
            })
            self.assertTrue(ok, msg)

    def test_health_checks_fail_on_vram_oom(self):
        with tempfile.TemporaryDirectory() as d:
            for env_key, label in (
                ("FAKE_TEX_OOM", "tex_oom=1"),
                ("FAKE_PLTT_OOM", "pltt_oom=1"),
                ("FAKE_POOL_OOM", "pool_oom=1"),
            ):
                ok, msg = self.run_one(d, {
                    "name": "oom_" + env_key.lower(),
                    "env": {env_key: "1"},
                    "steps": [{"step": 35}],
                })
                self.assertFalse(ok, f"expected failure for {env_key}")
                self.assertIn("VRAM/pool OOM detected", msg)
                self.assertIn(label, msg)

    def test_health_checks_fail_on_corrupt_billboards_in_field(self):
        with tempfile.TemporaryDirectory() as d:
            for env_key, label in (
                ("FAKE_BB_OOB", "oob_count=1"),
                ("FAKE_BB_ZERO_TEX", "zero_tex_count=1"),
            ):
                ok, msg = self.run_one(d, {
                    "name": "bb_" + env_key.lower(),
                    "env": {env_key: "1"},
                    "steps": [{"step": 35}],
                })
                self.assertFalse(ok, f"expected failure for {env_key}")
                self.assertIn("Corrupt billboard(s) detected", msg)
                self.assertIn(label, msg)

    def test_health_checks_skip_billboards_outside_field(self):
        with tempfile.TemporaryDirectory() as d:
            ok, msg = self.run_one(d, {
                "name": "battle_bb_ignored",
                "env": {"FAKE_BB_OOB": "2"},
                "steps": [{"start_battle": {"spec": "nope.json"}}],
                "assertions": [{"app": "battle"}],
            })
            self.assertTrue(ok, msg)

    def test_health_checks_can_be_skipped_per_scenario_or_cli(self):
        with tempfile.TemporaryDirectory() as d:
            ok, msg = self.run_one(d, {
                "name": "skip_json",
                "skip_health_checks": True,
                "env": {"FAKE_TEX_OOM": "1", "FAKE_BB_OOB": "1"},
                "steps": [{"step": 35}],
            })
            self.assertTrue(ok, msg)
            pth = write_scenario(d, "skip_cli", {
                "name": "skip_cli",
                "env": {"FAKE_TEX_OOM": "1", "FAKE_BB_OOB": "1"},
                "steps": [{"step": 35}],
            })
            self.assertEqual(runner.main(["--mock", "-j", "1", pth]), 1)
            self.assertEqual(runner.main(["--mock", "--no-health-checks", "-j", "1", pth]), 0)

    def test_health_checks_graceful_on_older_binaries(self):
        with tempfile.TemporaryDirectory() as d:
            ok, msg = self.run_one(d, {
                "name": "legacy_binary",
                "env": {"FAKE_NO_MEMORY": "1", "FAKE_NO_BILLBOARDS": "1"},
                "steps": [{"step": 35}],
            })
            self.assertTrue(ok, msg)


class TestGateMapping(unittest.TestCase):
    def test_changed_path_mapping(self):
        mapped = gate.map_changed_paths(["src/battle/foo.c", "src/applications/bag.c",
                                         "src/render_gpu/pipeline.c"])
        self.assertEqual(mapped["tags"], ["battle", "menu", "visual"])
        self.assertTrue(mapped["battle"])
        self.assertTrue(mapped["compare_backends_note"])
        self.assertTrue(mapped["seams"])
        self.assertEqual(gate.map_changed_paths(["README.md"])["tags"], ["smoke"])
        self.assertFalse(gate.map_changed_paths(["README.md"])["seams"])
        self.assertFalse(gate.map_changed_paths(["src/battle/foo.c"])["seams"])
        release = gate.map_changed_paths(["src/meson.build"])
        self.assertEqual(release["tags"], ["smoke"])
        self.assertTrue(release["release"])
        self.assertTrue(release["seams"])
        for pth in (
            "src/overlay005/field_camera.c",
            "src/billboard_vram_transfer.c",
            "res/field/maps/solaceon_town/scripts.s",
            "tools/dazzling/test/check_seams.py",
        ):
            self.assertTrue(gate.map_changed_paths([pth])["seams"], pth)

    def test_gate_runs_and_skips_seams_step(self):
        calls = []

        def fake_run_step(name, command, results):
            calls.append((name, command))
            results.append({"name": name, "ok": True, "returncode": 0, "elapsed_sec": 0.0, "command": command})
            return True

        with mock.patch.object(gate, "run_step", side_effect=fake_run_step), \
             mock.patch.object(gate, "resolve_seams_build_dir", return_value="build_macos"):
            rc = gate.main(["--tier", "smoke", "--skip-static", "--skip-patches"])
            self.assertEqual(rc, 0)
            names = [n for n, _ in calls]
            self.assertIn("seams", names)
            seams_cmd = dict(calls)["seams"]
            self.assertIn("--build", seams_cmd)
            self.assertIn("build_macos", seams_cmd)
            self.assertIn("--cine", seams_cmd)

            calls.clear()
            rc = gate.main(["--tier", "smoke", "--skip-static", "--skip-patches", "--skip-seams"])
            self.assertEqual(rc, 0)
            self.assertNotIn("seams", [n for n, _ in calls])

            calls.clear()
            with mock.patch.object(gate, "capture_changed_paths", return_value=["src/battle/foo.c"]):
                rc = gate.main(["--changed", "--skip-static", "--skip-patches", "--skip-battle"])
                self.assertEqual(rc, 0)
                self.assertNotIn("seams", [n for n, _ in calls])

            calls.clear()
            with mock.patch.object(gate, "capture_changed_paths", return_value=["src/billboard.c"]):
                rc = gate.main(["--changed", "--skip-static", "--skip-patches"])
                self.assertEqual(rc, 0)
                self.assertIn("seams", [n for n, _ in calls])

    def test_walk_to_advance_dialogue_and_inspect(self):
        sc = {
            "name": "story_mock_cutscene",
            "steps": [
                {"step": 35},
                {"inspect": "objects", "expect_present": ["LOCALID_ARC1_GARIUS"], "expect_absent": ["LOCALID_CLOWN_1"]},
                {"inspect": "camera", "assert": {"active": True, "tracking_target": True}},
                {"walk_to": {"x": 12, "z": 10, "step_frames": 1, "stop_on_script": True}},
                {"advance_dialogue": {
                    "until": {"script": None},
                    "press_frames": 1, "settle_frames": 1, "poll_frames": 1, "capture_delay_frames": 0,
                    "expect_min_lines": 2,
                    "expect_text_contains": ["lost someone", "flyer"],
                    "capture_on_text": [{"contains": "lost someone", "name": "mock_beat"}],
                }},
                {"inspect": "objects", "expect_absent": ["LOCALID_ARC1_GARIUS"], "expect_present": ["LOCALID_CLOWN_1"]},
            ],
            "assertions": [{"vars.VAR_ARC1_PROGRESS": 13}],
        }
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "story_mock_cutscene.json")
            with open(p, "w") as f:
                json.dump(sc, f)
            # Check final assertion via state_request step as well
            sc["steps"].append({"assert": {"vars.VAR_ARC1_PROGRESS": 13}, "state_request": {"vars": ["VAR_ARC1_PROGRESS"]}})
            sc["assertions"] = [{"script": None}]
            with open(p, "w") as f:
                json.dump(sc, f)
            name, ok, msg, client = runner.run_scenario(p, FAKE, work_root=td)
            try:
                self.assertTrue(ok, msg)
                self.assertTrue(os.path.exists(os.path.join(client.dir, "mock_beat.png")))
                tags = runner.classify_tags(p, sc)
                self.assertIn("story", tags)
            finally:
                if client:
                    client.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
