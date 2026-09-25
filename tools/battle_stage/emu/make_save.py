#!/usr/bin/env python3
"""Edit a raw 512 KB Platinum save for the emulator critic.

    make_save.py SRC OUT [--party-from SAV] [--at X,Z[,DIR]] [--heal] [--set-move SLOT:MOVE:PP]
    make_save.py SAV --info

--party-from  copy the whole party (count + 6 slots) from another save of the
              same trainer.
--at          move the player within the CURRENT map (both the saved location
              and the player's saved map object, which is what Continue actually
              restores). DIR: 0 up, 1 down, 2 left, 3 right.
--heal        full HP and no status for every party member.
--set-move    put MOVE (numeric ID, generated/moves.txt line - 1) with PP into
              the lead's move SLOT (0-3). Repeatable.

Only the newest partition (the one Continue loads) is edited; its CRC is
rewritten. The older partition is left untouched.

The committed saves/eterna_forest_grass.sav was produced with
    make_save.py vesp.sav saves/eterna_forest_grass.sav \
        --party-from coronet_1f_south.sav --at 74,47,1 --heal --set-move 3:206:40
(vesp.sav: player in Eterna Forest next to the Vespiquen totem;
 coronet_1f_south.sav: same trainer, 5 mons around Lv 29). Slot 3 of the
lead (Finneon) is False Swipe, a damaging move that never KOs, so the critic
can show a hit and still bag/run from the same battle.
"""

from __future__ import annotations

import argparse
import pathlib
import struct
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from platinum_save_utils import (  # noqa: E402
    GENERAL_SIZE, MAIN_FOOTER_SIZE, PARTITION_SIZE, PARTY_COUNT_OFFSET, PARTY_OFFSET,
    PK4_PARTY_SIZE, crc16_ccitt, decrypt_pk4, encrypt_pk4, general_block_valid, u16,
)

LOCATION_OFFSET = 0x1280          # Location {mapId, warpId, x, z, faceDirection}, s32 each
MAPOBJ_SIZE = 0x50                # MapObjectSave, include/map_object.h
PLAYER_LOCAL_ID = 0xFF
PARTY_BLOCK = (PARTY_COUNT_OFFSET - 4, PARTY_OFFSET + 6 * PK4_PARTY_SIZE)   # capacity, count, mons
MAP_NAMES = {203: "Eterna Forest", 207: "Mt. Coronet 1F South"}


def fix_crc(raw: bytearray, base: int) -> None:
    foot = base + GENERAL_SIZE - MAIN_FOOTER_SIZE
    struct.pack_into("<H", raw, foot + 18, crc16_ccitt(raw[base:foot]))


def newest_partition(raw) -> int:
    """Base of the valid general block with the highest save counter (what the game loads)."""
    def key(base):
        foot = base + GENERAL_SIZE - MAIN_FOOTER_SIZE
        return struct.unpack_from("<II", raw, foot)
    valid = [b for b in (0, PARTITION_SIZE) if general_block_valid(raw, b)]
    if not valid:
        raise SystemExit("no valid save partition")
    return max(valid, key=key)


def location(raw, base):
    return struct.unpack_from("<iiiii", raw, base + LOCATION_OFFSET)


def find_player_object(raw, base) -> int:
    """Offset of the player's MapObjectSave: localID 0xFF at +8, x/z at +0x26/+0x2A match the location."""
    _, _, x, z, _ = location(raw, base)
    for off in range(base, base + GENERAL_SIZE - MAPOBJ_SIZE, 2):
        if raw[off + 8] == PLAYER_LOCAL_ID and struct.unpack_from("<h", raw, off + 0x26)[0] == x \
                and struct.unpack_from("<h", raw, off + 0x2A)[0] == z \
                and struct.unpack_from("<h", raw, off + 0x20)[0] == x:
            return off
    raise SystemExit(f"player map object not found in partition {base:#x}")


def party(raw, base):
    n = raw[base + PARTY_COUNT_OFFSET]
    out = []
    for i in range(n):
        o = base + PARTY_OFFSET + i * PK4_PARTY_SIZE
        r = decrypt_pk4(bytes(raw[o:o + PK4_PARTY_SIZE]))
        out.append(dict(species=u16(r, 8), level=r[0x8C], hp=u16(r, 0x8E), maxhp=u16(r, 0x90),
                        moves=[u16(r, 0x28 + 2 * j) for j in range(4)], item=u16(r, 0x0A)))
    return out


def info(raw) -> None:
    print(f"newest partition: {newest_partition(raw):#x}")
    for base in (0, PARTITION_SIZE):
        if not general_block_valid(raw, base):
            print(f"partition {base:#x}: invalid")
            continue
        m, w, x, z, d = location(raw, base)
        print(f"partition {base:#x}: map {m} ({MAP_NAMES.get(m, '?')}) warp {w} x {x} z {z} dir {d}")
        for p in party(raw, base):
            print("   ", p)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--info", action="store_true")
    ap.add_argument("--party-from")
    ap.add_argument("--at")
    ap.add_argument("--heal", action="store_true")
    ap.add_argument("--set-move", action="append", default=[])
    a = ap.parse_args()
    raw = bytearray(pathlib.Path(a.src).read_bytes())
    if a.info or not a.out:
        info(raw)
        return
    donor = bytearray(pathlib.Path(a.party_from).read_bytes()) if a.party_from else None
    base = newest_partition(raw)
    if True:
        if donor is not None:
            lo, hi = PARTY_BLOCK
            dbase = newest_partition(donor)
            raw[base + lo:base + hi] = donor[dbase + lo:dbase + hi]
        if a.at:
            vals = [int(v) for v in a.at.split(",")]
            nx, nz = vals[0], vals[1]
            m, w, _, _, d = location(raw, base)
            d = vals[2] if len(vals) > 2 else d
            obj = find_player_object(raw, base)
            struct.pack_into("<iiiii", raw, base + LOCATION_OFFSET, m, -1, nx, nz, d)
            struct.pack_into("<bbb", raw, obj + 0x0C, d, d, d)          # initial / facing / moving dir
            struct.pack_into("<h", raw, obj + 0x20, nx)
            struct.pack_into("<h", raw, obj + 0x24, nz)
            struct.pack_into("<h", raw, obj + 0x26, nx)
            struct.pack_into("<h", raw, obj + 0x2A, nz)
        if a.heal:
            for i in range(raw[base + PARTY_COUNT_OFFSET]):
                o = base + PARTY_OFFSET + i * PK4_PARTY_SIZE
                r = decrypt_pk4(bytes(raw[o:o + PK4_PARTY_SIZE]))
                struct.pack_into("<I", r, 0x88, 0)                          # status
                struct.pack_into("<H", r, 0x8E, u16(r, 0x90))               # hp = max hp
                raw[o:o + PK4_PARTY_SIZE] = encrypt_pk4(r)
        for spec in a.set_move:
            slot, move, pp = (int(v) for v in spec.split(":"))
            o = base + PARTY_OFFSET
            r = decrypt_pk4(bytes(raw[o:o + PK4_PARTY_SIZE]))
            struct.pack_into("<H", r, 0x28 + 2 * slot, move)
            r[0x30 + slot] = pp
            struct.pack_into("<H", r, 6, sum(struct.unpack_from("<64H", r, 8)) & 0xFFFF)   # checksum
            raw[o:o + PK4_PARTY_SIZE] = encrypt_pk4(r)
        fix_crc(raw, base)
        assert general_block_valid(raw, base)
    pathlib.Path(a.out).write_bytes(raw)
    info(raw)


if __name__ == "__main__":
    main()
