#!/usr/bin/env python3
"""Fail-closed validator for the Parallel Sinnoh dialogue and event flow."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAX_VISIBLE_CHARS = 36

TEXT_BANKS = {
    "act1": ROOT / "res/text/mt_coronet_1f_south.json",
    "act2": ROOT / "res/text/route_218.json",
    "acts3_4": ROOT / "res/text/spear_pillar.json",
}

REQUIRED_MESSAGE_IDS = {
    "act1": set(range(0, 7)),
    "act2": set(range(0, 13)),
    "acts3_4": {13, 18, 20, 24, 26, 27, 28, 29, 30, 31, 32},
}

REQUIRED_PHRASES = {
    "act1": [
        "two realities",
        "Totem Pokémon",
        "power demands a sacrifice",
        "glowing rocks",
    ],
    "act2": [
        "That’s right, CLEFAIRY!",
        "Rt. 218",
        "stone conduits",
        "Don’t trust him",
        "Totems hold the",
        "old machinery gives off",
    ],
    "acts3_4": [
        "Totems have fallen",
        "I am not of this world",
        "Distortion World",
        "true heir",
        "I was wrong",
        "hold the gate open",
        "eight seals",
    ],
}

TOTEM_FLAGS = [
    "FLAG_TOTEM_HITMONLEE_DEFEATED",
    "FLAG_TOTEM_VESPIQUEN_DEFEATED",
    "FLAG_TOTEM_SKARMORY_DEFEATED",
    "FLAG_TOTEM_LAPRAS_DEFEATED",
    "FLAG_TOTEM_SPIRITOMB_DEFEATED",
    "FLAG_TOTEM_AGGRON_DEFEATED",
    "FLAG_TOTEM_MAMOSWINE_DEFEATED",
    "FLAG_TOTEM_KINGDRA_DEFEATED",
]


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def load_bank(path: Path) -> tuple[dict[int, object], str]:
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    messages: dict[int, object] = {}
    for entry in data["messages"]:
        match = re.search(r"_(\d{5})$", entry["id"])
        if match:
            messages[int(match.group(1))] = entry.get("en_US")
    return messages, raw


def chunks(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return list(value)
    return []


def visible_lines(value: object) -> list[str]:
    output: list[str] = []
    for chunk in chunks(value):
        for line in re.split(r"[\n\r\f]", chunk):
            line = re.sub(r"\{[^}]+\}", "NAME", line)
            if line:
                output.append(line)
    return output


def require_tokens(errors: list[str], text: str, tokens: list[str], label: str) -> None:
    for token in tokens:
        if token not in text:
            fail(errors, f"{label}: missing token {token!r}")


def main() -> int:
    errors: list[str] = []
    summary: dict[str, object] = {"banks": {}, "checks": []}

    for act, path in TEXT_BANKS.items():
        messages, raw = load_bank(path)
        missing = sorted(REQUIRED_MESSAGE_IDS[act] - {mid for mid, value in messages.items() if chunks(value)})
        if missing:
            fail(errors, f"{act}: missing English messages {missing}")
        require_tokens(errors, raw, REQUIRED_PHRASES[act], act)

        too_long: list[tuple[int, int, str]] = []
        checked_lines = 0
        for mid in REQUIRED_MESSAGE_IDS[act]:
            for line in visible_lines(messages.get(mid)):
                checked_lines += 1
                if len(line) > MAX_VISIBLE_CHARS:
                    too_long.append((mid, len(line), line))
        for mid, length, line in too_long:
            fail(errors, f"{act}: message {mid} line length {length}>{MAX_VISIBLE_CHARS}: {line!r}")
        summary["banks"][act] = {
            "required_messages": len(REQUIRED_MESSAGE_IDS[act]),
            "visible_lines_checked": checked_lines,
            "max_visible_chars": MAX_VISIBLE_CHARS,
        }

    act1_script = (ROOT / "res/field/scripts/scripts_mt_coronet_1f_south.s").read_text(encoding="utf-8")
    act1_events = json.loads((ROOT / "res/field/events/events_mt_coronet_1f_south.json").read_text(encoding="utf-8"))
    require_tokens(
        errors,
        act1_script,
        [
            "ScriptEntry _RivalEncounter",
            "TRAINER_RIVAL_ROUTE_209_DRATINI",
            "TRAINER_RIVAL_ROUTE_209_GIBLE",
            "TRAINER_RIVAL_ROUTE_209_BAGON",
            "FLAG_HIDE_CINDER_RIFT_UPPER_RIVAL",
            "SetVar VAR_CINDER_RIFT_CYRUS_SCENE_STATE, 1",
            "SetVar VAR_CINDER_RIFT_UPPER_RIVAL_SCENE_STATE, 1",
            "SetVar VAR_CINDER_RIFT_UPPER_RIVAL_SCENE_STATE, 2",
            "SetVar VAR_UNK_0x4096, 2",
        ],
        "act1 script",
    )
    rival_objects = [obj for obj in act1_events["object_events"] if obj["id"] == "MT_CORONET_1F_SOUTH_RIVAL_7"]
    if len(rival_objects) != 1:
        fail(errors, "act1 events: expected exactly one MT_CORONET_1F_SOUTH_RIVAL_7 object")
    elif rival_objects[0]["script"] != 1 or rival_objects[0]["hidden_flag"] != "FLAG_HIDE_CINDER_RIFT_UPPER_RIVAL":
        fail(errors, "act1 events: Rival object script or hidden flag is incorrect")
    cyrus_triggers = [
        event
        for event in act1_events["coord_events"]
        if event["script"] == 1
        and event["var"] == "VAR_CINDER_RIFT_CYRUS_SCENE_STATE"
        and event["value"] == 0
    ]
    if len(cyrus_triggers) != 1:
        fail(errors, "act1 events: expected one Cyrus coordinate trigger gated by dedicated state 0")
    rival_triggers = [
        event
        for event in act1_events["coord_events"]
        if event["script"] == 2
        and event["var"] == "VAR_CINDER_RIFT_UPPER_RIVAL_SCENE_STATE"
        and event["value"] == 1
    ]
    if len(rival_triggers) != 1:
        fail(errors, "act1 events: expected one Rival coordinate trigger gated by dedicated state 1")

    act2_script = (ROOT / "res/field/scripts/scripts_route_218.s").read_text(encoding="utf-8")
    act2_events = json.loads((ROOT / "res/field/events/events_route_218.json").read_text(encoding="utf-8"))
    require_tokens(
        errors,
        act2_script,
        [
            "_CanalaveArrowSign:",
            "_JubilifeArrowSign:",
            "_GuitaristDialogue:",
            "_FishermanDialogue:",
            "_ClefairyFirstCry:",
            "_ClefairySecondCry:",
            "_PikachuCry:",
            "_EverspringRivalScene:",
            "_EverspringRivalTalk:",
            "_RiftRelic:",
            "Message 7",
            "Message 11",
            "Message 12",
            "RemoveObject 21",
            "SetFlag FLAG_HIDE_EVERSPRING_RIVAL",
            "SetVar VAR_EVERSPRING_RIVAL_SCENE_STATE, 1",
        ],
        "act2 script",
    )
    act2_triggers = [
        event
        for event in act2_events["coord_events"]
        if event["var"] == "VAR_EVERSPRING_RIVAL_SCENE_STATE" and event["value"] == 0
    ]
    if len(act2_triggers) != 1:
        fail(errors, "act2 events: expected one Everspring Rival trigger gated by scene state 0")
    elif act2_triggers[0] != {
        "script": 8,
        "x": 87,
        "z": 755,
        "y": 0,
        "width": 3,
        "length": 1,
        "var": "VAR_EVERSPRING_RIVAL_SCENE_STATE",
        "value": 0,
    }:
        fail(errors, "act2 events: relocated Rival trigger geometry or script wiring is incorrect")

    original_route218_objects = {
        "ROUTE_218_GUITARIST_TONY",
        "ROUTE_218_SAILOR_SKYLER",
        "ROUTE_218_FISHERMAN_MIGUEL",
        "ROUTE_218_FISHERMAN_LUC",
        "ROUTE_218_ARROW_SIGNPOST_4",
        "ROUTE_218_ARROW_SIGNPOST_5",
        "ROUTE_218_POKEBALL_6",
        "ROUTE_218_POKEBALL_7",
        "ROUTE_218_UNK_100_8",
        "ROUTE_218_UNK_100_9",
        "ROUTE_218_UNK_100_10",
        "ROUTE_218_UNK_100_11",
        "ROUTE_218_VENT_12",
        "ROUTE_218_VENT_13",
        "ROUTE_218_GUITARIST_14",
        "ROUTE_218_CLEFAIRY_15",
        "ROUTE_218_CLEFAIRY_16",
        "ROUTE_218_PIKACHU_17",
        "ROUTE_218_PIKACHU_18",
        "ROUTE_218_FISHERMAN_19",
        "ROUTE_218_POKEBALL_20",
    }
    act2_objects = {obj["id"]: obj for obj in act2_events["object_events"]}
    missing_original_objects = sorted(original_route218_objects - set(act2_objects))
    if missing_original_objects:
        fail(errors, f"act2 events: missing original Route 218 objects {missing_original_objects}")
    if len(act2_events["warp_events"]) != 4:
        fail(errors, "act2 events: original four Route 218 warps were not preserved")
    rival = act2_objects.get("ROUTE_218_EVERSPRING_RIVAL")
    if not rival or any(
        rival.get(key) != value
        for key, value in {
            "script": 9,
            "hidden_flag": "FLAG_HIDE_EVERSPRING_RIVAL",
            "x": 88,
            "z": 753,
            "y": 0,
        }.items()
    ):
        fail(errors, "act2 events: relocated Rival object wiring or coordinates are incorrect")
    relic = act2_objects.get("ROUTE_218_RIFT_RELIC")
    if not relic or any(
        relic.get(key) != value
        for key, value in {"script": 10, "x": 91, "z": 752, "y": 0}.items()
    ):
        fail(errors, "act2 events: relocated rift-relic object wiring or coordinates are incorrect")

    spear_script = (ROOT / "res/field/scripts/scripts_spear_pillar.s").read_text(encoding="utf-8")
    for flag in TOTEM_FLAGS:
        token = f"GoToIfUnset {flag}, _TotemsRemain"
        if token not in spear_script:
            fail(errors, f"acts3_4 script: missing Totem gate {flag}")
    require_tokens(
        errors,
        spear_script,
        [
            "SetFlag FLAG_UNK_0x01C8",
            "SetFlag FLAG_UNK_0x01C9",
            "Call SpearPillar_SetRivalPartnerTeam",
            "StartTrainerBattle VAR_0x8004",
            "Message 13",
            "Message 18",
            "Message 20",
            "Message 24",
            "Message 26",
            "Message 27",
            "Message 28",
            "Message 29",
            "Message 30",
            "SetVar VAR_SPEAR_PILLAR_PARALLEL_SCENE_STATE, 1",
            "SetVar VAR_SPEAR_PILLAR_PARALLEL_SCENE_STATE, 2",
            "SetVar VAR_SPEAR_PILLAR_PARALLEL_SCENE_STATE, 3",
            "SetVar VAR_UNK_0x4098, 3",
            "GoTo _0508",
        ],
        "acts3_4 script",
    )
    forbidden = [
        "StartTagBattle",
        "TRAINER_GALACTIC_GRUNT_SPEAR_PILLAR_1",
        "TRAINER_GALACTIC_GRUNT_SPEAR_PILLAR_2",
    ]
    for token in forbidden:
        if token in spear_script:
            fail(errors, f"acts3_4 script: legacy Galactic battle token remains: {token}")

    vars_flags = (ROOT / "generated/vars_flags.txt").read_text(encoding="utf-8")
    require_tokens(
        errors,
        vars_flags,
        [
            "FLAG_HIDE_CINDER_RIFT_UPPER_RIVAL",
            "FLAG_HIDE_EVERSPRING_RIVAL",
            "VAR_EVERSPRING_RIVAL_SCENE_STATE",
            "VAR_CINDER_RIFT_UPPER_RIVAL_SCENE_STATE",
            "VAR_SPEAR_PILLAR_PARALLEL_SCENE_STATE",
            "VAR_CINDER_RIFT_CYRUS_SCENE_STATE",
            *TOTEM_FLAGS,
        ],
        "progression constants",
    )

    summary["checks"] = [
        "Act 1 Cyrus scene and mandatory Rival battle",
        "Act 2 map-free Everspring anomaly scene with vanilla Route 218 preserved",
        "Eight-Totem fail-closed Spear Pillar gate",
        "Act 3 Cyrus confession and Rival betrayal battle",
        "Act 4 rejection, remorse, and rift transition",
        "Legacy Galactic Spear Pillar battles absent",
    ]
    summary["status"] = "PASS" if not errors else "FAIL"
    summary["errors"] = errors
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
