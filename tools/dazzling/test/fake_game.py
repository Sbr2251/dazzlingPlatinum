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
import json, os, struct, sys

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
                    elif k == "A": self.message_waiting = True
                    elif k == "B": self.message_waiting = False
                    elif k == "START":
                        self.app = "battle"
                        self.battle = {"enemy_species": "SPECIES_STARLY", "enemy_hp": 20,
                                       "player_hp": 30, "action_menu_waiting": True, "turn": "player"}
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
        if cmd == "talk":
            self.message_waiting, self.script = True, {"archive": 1, "offset": 64}
            return {"ok": True}, False
        return {"ok": False, "error": f"unknown cmd {cmd}"}, False

def main():
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
