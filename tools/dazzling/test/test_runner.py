#!/usr/bin/env python3
"""Unit tests for run.py against fake_game.py. No game build needed.
Run: python3 -m unittest tools.dazzling.test.test_runner  (or this file directly)
"""
import json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run as runner  # noqa: E402

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
            ep, ap, dp = runner.write_diff_images(a, b, d, "shot", crop=[0, 0, 8, 8])
            for pth in (ep, ap, dp):
                self.assertTrue(os.path.exists(pth), pth)
            self.assertEqual(runner.load_image(ep)[:2], (8, 8))

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

    def test_start_battle_and_decide_steps(self):
        with tempfile.TemporaryDirectory() as d:
            ok, msg = self.run_one(d, {
                "name": "case",
                "steps": [{"start_battle": {"spec": "nope.json"}},
                          {"battle_decide": {"battler": 0, "action": "move", "move_index": 0, "mega": True}},
                          {"battle_event": {"type": "battle_start"}},
                          {"assert": {"app": "battle", "battle.battlers.0.mega": True}}]})
            self.assertTrue(ok, msg)

if __name__ == "__main__":
    unittest.main(verbosity=2)
