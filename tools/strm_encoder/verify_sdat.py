#!/usr/bin/env python3
"""Checks that a rebuilt SDAT only gained stream data compared to a baseline SDAT.

  python3 tools/strm_encoder/verify_sdat.py BASE.sdat NEW.sdat --src res/sound/pl_sound_data

BASE.sdat is built from the res/sound tree before the stream change, NEW.sdat from the tree
after it (both with SDATTool, exactly like res/sound/meson.build does; see README.md).
The SDAT is parsed directly (no SDATTool code), and the script checks:

  * SEQ/SEQARC/BANK/WAVARC/PLAYER/GROUP: same record count, same SYMB names and byte-identical
    INFO records. (Records hold file IDs, so this also proves no existing file ID moved.)
  * FAT/FILE: with the STRM files removed, NEW holds exactly BASE's files, same order and bytes,
    and the STRM files come after all of them.
  * player2Info / strmInfo: each record decodes (NNSSndArcStrmPlayerInfo / NNSSndArcStrmInfo
    from NitroSystem sndarc.h) to the values in --src InfoBlock.json; unused channel slots are
    0xFF; every stream's player exists and has enough channels; flags only uses FORCE_STEREO.
  * Every STRM file in NEW is byte-identical to --src Files/STRM/<name> and passes
    strmlib.validate (the header checks that would make NNS misbehave).

Exit code 0 = all checks passed.
"""
import argparse
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import strmlib as S  # noqa: E402

GROUPS = ("SEQ", "SEQARC", "BANK", "WAVARC", "PLAYER", "GROUP", "PLAYER2", "STRM")
SEQ, SEQARC, BANK, WAVARC, PLAYER, GROUP, PLAYER2, STRM = range(8)
RECORD_SIZE = {SEQ: 12, SEQARC: 4, BANK: 12, WAVARC: 4, PLAYER: 8, PLAYER2: 24, STRM: 12}
NNS_SND_ARC_STRM_FORCE_STEREO = 1 << 0
NNS_SND_STRM_PLAYER_NUM = 4  # sndarc_stream.h; NNS_SndArcStrmSetupPlayer only looks at 0..3


class Sdat:
    def __init__(self, path):
        self.path = path
        d = self.data = open(path, "rb").read()
        if d[:4] != b"SDAT":
            raise ValueError("%s: not an SDAT" % path)
        size, hsize, nblocks = struct.unpack_from("<IHH", d, 8)
        if size != len(d):
            raise ValueError("%s: header size %d != file size %d" % (path, size, len(d)))
        offs = struct.unpack_from("<8I", d, 0x10)
        if nblocks == 4:
            self.symb, self.info, self.fat, self.file = offs[0], offs[2], offs[4], offs[6]
        else:  # no SYMB block
            self.symb, self.info, self.fat, self.file = None, offs[0], offs[2], offs[4]
        for off, magic in ((self.info, b"INFO"), (self.fat, b"FAT "), (self.file, b"FILE")):
            if d[off:off + 4] != magic:
                raise ValueError("%s: missing %r block" % (path, magic))
        if self.symb is not None and d[self.symb:self.symb + 4] != b"SYMB":
            raise ValueError("%s: missing SYMB block" % path)
        self.records = [self._records(g) for g in range(8)]
        self.names = [self._names(g) for g in range(8)]
        self.files = self._files()

    def _u32(self, off):
        return struct.unpack_from("<I", self.data, off)[0]

    def _records(self, g):
        base = self.info
        table = base + self._u32(base + 8 + 4 * g)
        out = []
        for i in range(self._u32(table)):
            off = self._u32(table + 4 + 4 * i)
            if off == 0:
                out.append(None)  # empty slot ({"name": ""} in InfoBlock.json)
                continue
            start = base + off
            size = RECORD_SIZE.get(g)
            if size is None:  # GROUP: u32 count + count * 8 bytes
                size = 4 + 8 * self._u32(start)
            out.append(self.data[start:start + size])
        return out

    def _cstr(self, off):
        end = self.data.index(b"\0", off)
        return self.data[off:end].decode("ascii")

    def _names(self, g):
        if self.symb is None:
            return None
        base = self.symb
        table = base + self._u32(base + 8 + 4 * g)
        stride = 8 if g == SEQARC else 4
        out = []
        for i in range(self._u32(table)):
            off = self._u32(table + 4 + stride * i)
            out.append(self._cstr(base + off) if off else "")
        return out

    def _files(self):
        n = self._u32(self.fat + 8)
        out = []
        for i in range(n):
            off, size = struct.unpack_from("<II", self.data, self.fat + 12 + 16 * i)
            out.append(self.data[off:off + size])
        return out


def decode_player2(rec):
    num = rec[0]
    return {"count": num, "v": list(rec[1:17]), "reserved": list(rec[17:24])}


def decode_strm(rec):
    file_id, vol, pri, ply, flags = struct.unpack_from("<IBBBB", rec, 0)
    return {"fileId": file_id, "vol": vol, "pri": pri, "ply": ply, "flags": flags,
            "reserved": list(rec[8:12])}


class Checker:
    def __init__(self):
        self.failures = 0

    def check(self, ok, msg):
        print("%s %s" % ("ok  " if ok else "FAIL", msg))
        if not ok:
            self.failures += 1
        return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base", help="SDAT built from the tree before the stream change")
    ap.add_argument("new", help="SDAT built from the tree after the stream change")
    ap.add_argument("--src", required=True, help="pl_sound_data folder NEW was built from")
    a = ap.parse_args()

    base, new = Sdat(a.base), Sdat(a.new)
    info_json = json.load(open(os.path.join(a.src, "InfoBlock.json")))
    file_json = json.load(open(os.path.join(a.src, "FileBlock.json")))["file"]
    file_names = [f["name"] for f in file_json]
    c = Checker()

    print("-- unchanged groups")
    for g in range(PLAYER2):
        c.check(base.records[g] == new.records[g],
                "%-6s %d INFO records byte-identical" % (GROUPS[g], len(new.records[g])))
        if base.names is not None and new.names is not None:
            c.check(base.names[g] == new.names[g], "%-6s SYMB names identical" % GROUPS[g])

    print("-- files")
    c.check(len(new.files) == len(file_json),
            "FAT has %d files, FileBlock.json lists %d" % (len(new.files), len(file_json)))
    strm_ids = [i for i, f in enumerate(file_json) if f["type"] == "STRM"]
    kept = [blob for i, blob in enumerate(new.files) if i not in strm_ids]
    c.check(kept == base.files,
            "non-STRM files: %d in NEW == %d in BASE, same order, byte-identical"
            % (len(kept), len(base.files)))
    c.check(all(i >= len(base.files) for i in strm_ids),
            "STRM files appended after all existing files (ids %s)" % strm_ids)

    print("-- player2Info (stream players)")
    p2_json = info_json["player2Info"]
    c.check(len(new.records[PLAYER2]) == len(p2_json),
            "%d player2 records (JSON %d)" % (len(new.records[PLAYER2]), len(p2_json)))
    c.check(len(p2_json) <= NNS_SND_STRM_PLAYER_NUM, "at most %d stream players" % NNS_SND_STRM_PLAYER_NUM)
    players = []
    for i, (rec, js) in enumerate(zip(new.records[PLAYER2], p2_json)):
        p = decode_player2(rec) if rec else None
        players.append(p)
        name = new.names[PLAYER2][i] if new.names else "#%d" % i
        if js["name"] == "":
            c.check(p is None, "player2 %d empty" % i)
            continue
        print("     %s = %s" % (name, p))
        c.check(name == js["name"], "player2 %d SYMB name %s" % (i, name))
        c.check(p == {k: js[k] for k in ("count", "v", "reserved")}, "player2 %s matches InfoBlock.json" % name)
        n = p["count"]
        c.check(1 <= n <= 16 and len(set(p["v"][:n])) == n and all(ch < 16 for ch in p["v"][:n]),
                "player2 %s: %d distinct hardware channels %s" % (name, n, p["v"][:n]))
        c.check(all(ch == 0xFF for ch in p["v"][n:]), "player2 %s: unused slots are 0xFF" % name)

    print("-- strmInfo (streams)")
    st_json = info_json["strmInfo"]
    c.check(len(new.records[STRM]) == len(st_json),
            "%d strm records (JSON %d)" % (len(new.records[STRM]), len(st_json)))
    for i, (rec, js) in enumerate(zip(new.records[STRM], st_json)):
        name = new.names[STRM][i] if new.names else "#%d" % i
        if js["name"] == "":
            c.check(rec is None, "strm %d empty" % i)
            continue
        s = decode_strm(rec)
        print("     %s = %s" % (name, s))
        c.check(name == js["name"], "strm %d SYMB name %s" % (i, name))
        want_id = file_names.index(js["fileName"])
        c.check(s["fileId"] == want_id + (js["unkA"] << 16),
                "strm %s fileId %d -> %s" % (name, s["fileId"], js["fileName"]))
        c.check(file_json[want_id]["type"] == "STRM", "strm %s file has type STRM" % name)
        c.check((s["vol"], s["pri"], s["ply"]) == (js["vol"], js["pri"], js["ply"]),
                "strm %s vol/pri/ply = %d/%d/%d" % (name, s["vol"], s["pri"], s["ply"]))
        c.check([s["flags"]] + s["reserved"] == js["reserved"], "strm %s flags/reserved match JSON" % name)
        c.check(s["flags"] & ~NNS_SND_ARC_STRM_FORCE_STEREO == 0, "strm %s flags 0x%02X" % (name, s["flags"]))
        blob = new.files[s["fileId"]] if s["fileId"] < len(new.files) else b""
        src_path = os.path.join(a.src, "Files", "STRM", js["fileName"])
        c.check(os.path.exists(src_path) and blob == open(src_path, "rb").read(),
                "strm %s file (%d bytes) byte-identical to %s" % (name, len(blob), src_path))
        try:
            hdr = S.parse_strm(blob)
            problems = S.validate(blob, hdr)
        except ValueError as e:
            hdr, problems = None, [str(e)]
        c.check(not problems, "strm %s header valid%s" % (name, (": " + "; ".join(problems)) if problems else ""))
        if hdr is None:
            continue
        print("     %s: %s, %d ch, %d Hz (timer %d), loop %s %d..%d samples, %.1f s"
              % (js["fileName"], S.FORMAT_NAMES.get(hdr.format, "?"), hdr.channels,
                 round(S.rate_for_timer(hdr.timer)), hdr.timer, "on" if hdr.loop_flag else "off",
                 hdr.loop_start, hdr.loop_end, hdr.loop_end / S.rate_for_timer(hdr.timer)))
        p = players[s["ply"]] if s["ply"] < len(players) else None
        c.check(p is not None, "strm %s player %d exists" % (name, s["ply"]))
        if p is not None:
            need = 2 if s["flags"] & NNS_SND_ARC_STRM_FORCE_STEREO else hdr.channels
            c.check(need <= p["count"], "strm %s needs %d channels, player has %d" % (name, need, p["count"]))

    print()
    print("all checks passed" if c.failures == 0 else "%d check(s) FAILED" % c.failures)
    return 1 if c.failures else 0


if __name__ == "__main__":
    sys.exit(main())
