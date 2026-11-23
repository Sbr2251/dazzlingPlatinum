#!/usr/bin/env python3
"""Fake/mock game process implementing docs/headless_protocol.md (BRIEF.md).

Used for the runner's own unit tests until debug-headless lands the real
SIM_HEADLESS/SIM_CONTROL implementation. Deterministic: same commands give
the same state and screenshots (a BMP whose pixels encode the frame).

State model (deliberately tiny):
  frame, app ("field"/"battle"/"title"), player {map,x,z,dir},
  vars/flags dicts, party/bag stubs, message_waiting, in_battle.
  press UP/DOWN/LEFT/RIGHT moves on the field; A on the field sets
  message_waiting; START opens battle stub; B flees battle.
"""
import json, os, struct, sys, time

def write_bmp(path, w, h, seed):
    rows = []
    for y in range(h):
        row = bytearray()
        for x in range(w):
            row += bytes(((seed + x) & 0xFF, (seed + y) & 0xFF, seed & 0xFF))
        rows.append(bytes(row) + b"\x00" * ((4 - (w * 3) % 4) % 4))
    body = b"".join(reversed(rows))
    with open(path, "wb") as f:
        f.write(b"BM" + struct.pack("<IHHI", 54 + len(body), 0, 0, 54))
        f.write(struct.pack("<IiiHHIIiiII", 40, w, h, 1, 24, 0, len(body), 2835, 2835, 0, 0))
        f.write(body)

class Fake:
    def __init__(self):
        self.frame = 0
        self.app = "title"
        self.player = {"map": "MAP_HEADER_TWINLEAF_TOWN", "map_id": 0, "x": 10, "z": 10, "dir": "DIR_SOUTH"}
        self.script = None
        self.message_waiting = False
        self.dialogue_queue = []
        self.objects = [{"localid": 1, "name": "LOCALID_ARC1_GARIUS", "x": 12, "z": 10, "visible": True}]
        self.vars, self.flags = {}, {}
        self.battle = None
        cov = os.environ.get("SIM_SCRIPT_COVERAGE")
        if cov:
            with open(cov, "a") as f:
                f.write("0 0\n")

    def state(self, req):
        st = {"frame": self.frame, "app": self.app, "player": dict(self.player),
              "script": self.script, "message_waiting": self.message_waiting,
              "vars": {k: self.vars.get(k, 0) for k in req.get("vars", [])},
              "flags": {k: self.flags.get(k, False) for k in req.get("flags", [])},
              "party": [{"species": "SPECIES_CHIMCHAR", "level": 10, "hp": 30, "held_item": "ITEM_NONE"}],
              "in_battle": self.battle is not None}
        if self.battle:
            st["battle"] = self.battle
        return {"ok": True, "state": st}

    def step(self, frames, keys=()):
        for _ in range(frames):
            self.frame += 1
            if self.app == "title" and self.frame >= 30:
                self.app = "field"
            for k in keys:
                if self.app == "field":
                    if k == "UP": self.player["z"] -= 1; self.player["dir"] = "DIR_NORTH"
                    elif k == "DOWN": self.player["z"] += 1; self.player["dir"] = "DIR_SOUTH"
                    elif k == "LEFT": self.player["x"] -= 1; self.player["dir"] = "DIR_WEST"
                    elif k == "RIGHT": self.player["x"] += 1; self.player["dir"] = "DIR_EAST"
                    elif k == "A":
                        if self.script is not None and self.dialogue_queue:
                            self.dialogue_queue.pop(0)
                            if not self.dialogue_queue:
                                self.message_waiting = False
                                self.script = None
                                self.vars["VAR_ARC1_PROGRESS"] = 13
                                self.objects = [{"localid": 2, "name": "LOCALID_CLOWN_1", "x": 14, "z": 10, "visible": True}]
                        else:
                            self.message_waiting = True
                    elif k == "B": self.message_waiting = False
                    elif k == "START":
                        self.app = "battle"
                        self.battle = {"enemy_species": "SPECIES_STARLY", "enemy_hp": 20,
                                       "player_hp": 30, "action_menu_waiting": True, "turn": "player"}
                    if self.app == "field" and self.script is None and self.vars.get("VAR_ARC1_PROGRESS", 0) < 13 and self.player["x"] == 12 and self.player["z"] == 10:
                        self.script = {"id": 99, "offset": 0}
                        self.dialogue_queue = ["Everyone has lost someone.", "Just a flyer."]
                        self.message_waiting = True
            if keys and "B" in keys and self.app == "battle":
                self.app, self.battle = "field", None

    def handle(self, req):
        cmd = req.get("cmd")
        if cmd == "quit":
            return {"ok": True}, True
        if cmd == "step":
            self.step(req.get("frames", 1)); return {"ok": True}, False
        if cmd == "press":
            self.step(req.get("frames", 1), req.get("keys", [])); return {"ok": True}, False
        if cmd == "touch":
            self.step(req.get("frames", 1)); return {"ok": True}, False
        if cmd == "finger":
            self.step(req.get("frames", 1)); return {"ok": True}, False
        if cmd == "screenshot":
            write_bmp(req["path"], 16, 16, self.frame % 251)
            return {"ok": True}, False
        if cmd == "state":
            return self.state(req), False
        if cmd == "import_save":
            if not os.path.exists(req["path"]):
                return {"ok": False, "error": f"save not found: {req['path']}"}, False
            base = os.path.basename(req["path"])
            self.app, self.frame = "field", self.frame + 1
            if "mega" in base:
                self.player["map"] = "MAP_HEADER_ROUTE_203"
            return {"ok": True}, False
        if cmd == "warp":
            self.player.update({"map": req["map"], "x": req.get("x", 0), "z": req.get("z", 0),
                                "dir": req.get("dir", "DIR_SOUTH")})
            self.app = "field"
            return {"ok": True}, False
        if cmd == "set_var":
            self.vars[req["name"]] = req["value"]; return {"ok": True}, False
        if cmd == "set_flag":
            self.flags[req["name"]] = bool(req["value"]); return {"ok": True}, False
        if cmd == "give_item":
            return {"ok": True}, False
        if cmd == "start_battle":
            self.app = "battle"
            self.battle = {"waiting": True, "turn": 1, "battlers": [
                {"battler": 0, "species": "SPECIES_INFERNAPE", "level": 50, "hp": 100, "max_hp": 100, "mega": False, "form": 0},
                {"battler": 1, "species": "SPECIES_GARCHOMP", "level": 50, "hp": 100, "max_hp": 100, "mega": False, "form": 0}]}
            return {"ok": True}, False
        if cmd == "battle_decide":
            if self.battle and req.get("mega"):
                self.battle["battlers"][0]["mega"] = True
                self.battle["battlers"][0]["form"] = 1
            return {"ok": True}, False
        if cmd == "battle_events":
            return {"ok": True, "events": [{"type": "battle_start"}, {"type": "move_used", "move": "MOVE_TACKLE"}, {"type": "stat_stage", "battler": 0, "delta": -1}]}, False
        if cmd == "talk":
            self.message_waiting, self.script = True, {"archive": 1, "offset": 64}
            self.dialogue_queue = ["Everyone has lost someone.", "Just a flyer."]
            return {"ok": True}, False
        if cmd == "inspect":
            what = req.get("what")
            if what == "text":
                txt = self.dialogue_queue[0] if self.dialogue_queue else ""
                return {"ok": True, "frame": self.frame, "what": "text", "data": {
                    "message_waiting": self.message_waiting, "signpost_active": False, "text": txt}}, False
            if what == "objects":
                return {"ok": True, "frame": self.frame, "what": "objects", "data": {
                    "objects": list(self.objects), "count": len(self.objects)}}, False
            if what == "camera":
                return {"ok": True, "frame": self.frame, "what": "camera", "data": {
                    "active": True, "position_fx": [0, 0, 0], "target_fx": [0, 0, 0],
                    "distance": 1000, "angle": [0, 0, 0], "fov_y": 1400, "projection": 0,
                    "tracking_target": True}}, False
            return {"ok": False, "error": f"unknown inspect target {what}"}, False
        return {"ok": False, "error": f"unknown cmd {cmd}"}, False

def main():
    # Test-only simulation of Darwin's dead-strip soft-reset loop: stderr
    # banners repeat while the control protocol never answers.
    if os.environ.get("FAKE_BOOT_LOOP"):
        for _ in range(3):
            print("SIM headless=1 fake soft reset", file=sys.stderr, flush=True)
            time.sleep(0.1)
        time.sleep(30)
        return 1
    fake = Fake()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            reply, done = fake.handle(json.loads(line))
        except Exception as e:  # keep protocol: one JSON line per command
            reply, done = {"ok": False, "error": str(e)}, False
        print(json.dumps(reply), flush=True)
        if done:
            return 0
    return 0

if __name__ == "__main__":
    sys.exit(main())
