#!/usr/bin/env python3
"""Shared helpers for the battle-events headless checks (docs/battle_events.md).

- edit_save(): offline .sav edits of the lead (species, ability, level, stats, HP, moves): the only party writes,
  done before boot, so the game never owns the record while it changes (space note arc2/qa_harness_lessons.md).
- AudioProbe: which sequences the NitroSystem sequence players hold (sSeqPlayer in the xMAP), works on any build.
- EventsDebug: gBattleEventsDebug (battle_events.h), the battle overlay's debug block; absent on the base ROM.
"""

from __future__ import annotations

import pathlib
import struct
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/battle_stage/emu"))

from platinum_save_utils import (  # noqa: E402
    GENERAL_SIZE, MAIN_FOOTER_SIZE, PARTITION_SIZE, PARTY_COUNT_OFFSET, PARTY_OFFSET, PK4_PARTY_SIZE,
    crc16_ccitt, decrypt_pk4, encrypt_pk4, general_block_valid, u16,
)

SEQ = {
    1116: "SEQ_BATTLE_WILD_POKEMON", 1117: "SEQ_BATTLE_GYM_LEADER", 1119: "SEQ_BATTLE_TRAINER",
    1129: "SEQ_VICTORY_GYM_LEADER", 1202: "SEQ_BATTLE_FRONTIER_BRAIN", 1796: "SEQ_SE_DP_HINSI",
    1806: "SEQ_SE_DP_SLIDEIN", 1501: "SEQ_SE_DP_DECIDE", 2129: "SEQ_SE_DP_KIRAN", 1534: "SEQ_SE_DP_BOWA", 1800: "SEQ_SE_DP_BOWA4", 1801: "SEQ_SE_DP_GETTING", 1802: "SEQ_SE_DP_NAGERU", 1127: "SEQ_VICTORY_WILD_POKEMON", 1510: "SEQ_SE_DP_KON",
}
SEQ_ID = {v: k for k, v in SEQ.items()}


def _newest(raw):
    def key(base):
        foot = base + GENERAL_SIZE - MAIN_FOOTER_SIZE
        return struct.unpack_from("<II", raw, foot)
    valid = [b for b in (0, PARTITION_SIZE) if general_block_valid(raw, b)]
    return max(valid, key=key)


def edit_save(src, out, species=None, ability=None, level=None, stats=None, hp_frac=None, moves=None,
              slot=0) -> dict:
    """Edits party `slot` of the newest partition. stats = (hp, atk, def, spe, spa, spd)."""
    raw = bytearray(pathlib.Path(src).read_bytes())
    base = _newest(raw)
    o = base + PARTY_OFFSET + slot * PK4_PARTY_SIZE
    r = decrypt_pk4(bytes(raw[o:o + PK4_PARTY_SIZE]))
    if species is not None:
        struct.pack_into("<H", r, 0x08, species)
    if ability is not None:
        r[0x15] = ability
    if moves is not None:
        for i, mv in enumerate(moves):
            struct.pack_into("<H", r, 0x28 + 2 * i, mv)
            r[0x30 + i] = 30
    if level is not None:
        r[0x8C] = level
    if stats is not None:
        struct.pack_into("<6H", r, 0x90, *stats)
    maxhp = u16(r, 0x90)
    struct.pack_into("<I", r, 0x88, 0)                       # no status
    hp = maxhp if hp_frac is None else max(1, int(maxhp * hp_frac))
    struct.pack_into("<H", r, 0x8E, hp)
    struct.pack_into("<H", r, 6, sum(struct.unpack_from("<64H", r, 8)) & 0xFFFF)
    raw[o:o + PK4_PARTY_SIZE] = encrypt_pk4(r)
    foot = base + GENERAL_SIZE - MAIN_FOOTER_SIZE
    struct.pack_into("<H", raw, foot + 18, crc16_ccitt(raw[base:foot]))
    assert general_block_valid(raw, base)
    pathlib.Path(out).write_bytes(raw)
    return dict(species=u16(r, 8), ability=r[0x15], level=r[0x8C], hp=hp, maxhp=maxhp,
                moves=[u16(r, 0x28 + 2 * i) for i in range(4)])


def read_xmap_syms(path, names):
    out = {}
    with open(path, errors="replace") as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 4 and parts[3] in names and len(parts[0]) == 8:
                try:
                    out[parts[3]] = (int(parts[0], 16), int(parts[1], 16))
                except ValueError:
                    pass
    return out


class AudioProbe:
    """NNSSndSeqPlayer sSeqPlayer[16] (NitroSystem snd/src/player.c), 0x44 bytes each:
    status +44, seqNo +56, playerNo +60, volume +62, fader {origin, target, counter, frame} +28."""

    SIZE = 0x44

    def __init__(self, e, xmap):
        syms = read_xmap_syms(xmap, {"sSeqPlayer"})
        self.e = e
        self.addr = syms.get("sSeqPlayer", (None, 0))[0]

    def players(self):
        if self.addr is None:
            return []
        raw = self.e.read(self.addr, self.SIZE * 16)
        out = []
        for i in range(16):
            b = raw[i * self.SIZE:(i + 1) * self.SIZE]
            status = b[44]
            if status == 0:
                continue
            origin, target, counter, frame = struct.unpack_from("<iiii", b, 28)
            out.append(dict(seq=struct.unpack_from("<H", b, 56)[0], player=b[60], status=status,
                            volume=struct.unpack_from("<h", b, 62)[0], fade_target=target, fade_counter=counter))
        return out

    def seqs(self):
        return sorted({p["seq"] for p in self.players()})

    def bgm(self):
        """The battle music playing: a SEQ_BATTLE_* / SEQ_VICTORY_* sequence (IDs 1116-1356). The field BGM the
        battle paused stays on its own player (1063 in the Eterna Forest save) and is ignored."""
        for p in self.players():
            if 1116 <= p["seq"] <= 1356:
                return p["seq"]
        return None

    def playing(self, seq):
        return seq in self.seqs()


class EventsDebug:
    FMT = "<IBBBBHH2H2H2B2B2hHHHBBBBxxI"
    FIELDS = ("magic forceCriticalCapture lastCaptureCritical lastCaptureShakes criticalCaptures "
              "lastCriticalThreshold dexCaught popupShows0 popupShows1 popupAbility0 popupAbility1 "
              "popupBattler0 popupBattler1 popupState0 popupState1 popupX0 popupX1 popupSkipped leaderBgm "
              "leaderBgmTrainerMsg beepSuppressed lowHPLayerActive hinsiPlaying criticalFlashes "
              "beepSuppressedFrames").split()

    def __init__(self, e, xmap):
        syms = read_xmap_syms(xmap, {"gBattleEventsDebug"})
        self.e = e
        self.addr, self.size = syms.get("gBattleEventsDebug", (None, 0))

    def read(self):
        if self.addr is None:
            return None
        n = struct.calcsize(self.FMT)
        d = dict(zip(self.FIELDS, struct.unpack(self.FMT, self.e.read(self.addr, n))))
        return d if d["magic"] == 0x54564542 else None

    def force_critical(self, mode: int) -> bool:
        if self.read() is None:
            return False
        self.e.write(self.addr + 4, bytes([mode]))
        return True
