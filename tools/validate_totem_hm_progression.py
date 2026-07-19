#!/usr/bin/env python3
"""Validate the combined Gym Badge and Totem requirements for field HMs.

The checks are intentionally deterministic and source-based. They prove the exact
eight HM mappings, the Badge-first/Totem-second gate, every two-input truth-table
state, the persistence producers for the required Totem flags, and the dedicated
party-menu error message.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Requirement:
    move: str
    check_function: str
    badge: str
    totem_flag: str
    encounter_script: str


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


REQUIREMENTS = (
    Requirement(
        "Rock Smash",
        "FieldMoves_CheckRockSmash",
        "BADGE_ID_COAL",
        "FLAG_TOTEM_HITMONLEE_DEFEATED",
        "res/field/scripts/scripts_ravaged_path.s",
    ),
    Requirement(
        "Cut",
        "FieldMoves_CheckCut",
        "BADGE_ID_FOREST",
        "FLAG_TOTEM_VESPIQUEN_DEFEATED",
        "res/field/scripts/scripts_eterna_forest.s",
    ),
    Requirement(
        "Defog",
        "FieldMoves_CheckDefog",
        "BADGE_ID_RELIC",
        "FLAG_TOTEM_SPIRITOMB_DEFEATED",
        "res/field/scripts/scripts_route_209_lost_tower_2f.s",
    ),
    Requirement(
        "Fly",
        "FieldMoves_CheckFly",
        "BADGE_ID_COBBLE",
        "FLAG_TOTEM_SKARMORY_DEFEATED",
        "res/field/scripts/scripts_route_214.s",
    ),
    Requirement(
        "Surf",
        "FieldMoves_CheckSurf",
        "BADGE_ID_FEN",
        "FLAG_TOTEM_LAPRAS_DEFEATED",
        "res/field/scripts/scripts_route_213.s",
    ),
    Requirement(
        "Strength",
        "FieldMoves_CheckStrength",
        "BADGE_ID_MINE",
        "FLAG_TOTEM_AGGRON_DEFEATED",
        "res/field/scripts/scripts_iron_island_b3f.s",
    ),
    Requirement(
        "Rock Climb",
        "FieldMoves_CheckRockClimb",
        "BADGE_ID_ICICLE",
        "FLAG_TOTEM_MAMOSWINE_DEFEATED",
        "res/field/scripts/scripts_acuity_lakefront.s",
    ),
    Requirement(
        "Waterfall",
        "FieldMoves_CheckWaterfall",
        "BADGE_ID_BEACON",
        "FLAG_TOTEM_KINGDRA_DEFEATED",
        "res/field/scripts/scripts_route_223.s",
    ),
)


def read(root: Path, relative: str) -> str:
    path = root / relative
    if not path.is_file():
        raise FileNotFoundError(relative)
    return path.read_text(encoding="utf-8")


def balanced_block(text: str, opening_brace: int) -> str:
    if opening_brace < 0 or text[opening_brace] != "{":
        raise ValueError("opening brace not found")

    depth = 0
    for index in range(opening_brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[opening_brace : index + 1]

    raise ValueError("unterminated brace-delimited block")


def function_body(text: str, function_name: str) -> str:
    signature = re.compile(
        rf"^\s*(?:static\s+)?[A-Za-z_][A-Za-z0-9_\s*]*\b{re.escape(function_name)}\s*\(",
        re.M,
    )
    for match in signature.finditer(text):
        opening_paren = text.find("(", match.start())
        depth = 0
        closing_paren = -1
        for index in range(opening_paren, len(text)):
            if text[index] == "(":
                depth += 1
            elif text[index] == ")":
                depth -= 1
                if depth == 0:
                    closing_paren = index
                    break
        if closing_paren < 0:
            continue

        next_token = closing_paren + 1
        while next_token < len(text) and text[next_token].isspace():
            next_token += 1
        if next_token < len(text) and text[next_token] == "{":
            return balanced_block(text, next_token)

    raise ValueError(f"function definition not found: {function_name}")


def result(name: str, condition: bool, pass_detail: str, fail_detail: str) -> CheckResult:
    return CheckResult(name, condition, pass_detail if condition else fail_detail)


def check_shared_gate(root: Path) -> CheckResult:
    source = read(root, "src/field_move_tasks.c")
    body = function_body(source, "FieldMoves_CheckProgression")

    badge_check = "PlayerHasRequiredBadge(fieldMoveContext, badge) == FALSE"
    flag_check = (
        "VarsFlags_CheckFlag(SaveData_GetVarsFlags(fieldMoveContext->fieldSystem->saveData), "
        "totemDefeatedFlag) == FALSE"
    )
    required_tokens = (
        badge_check,
        "return FIELD_MOVE_ERROR_BADGE;",
        flag_check,
        "return FIELD_MOVE_ERROR_TOTEM;",
        "return FIELD_MOVE_ERROR_NONE;",
    )
    ordered = all(token in body for token in required_tokens)
    if ordered:
        positions = [body.index(token) for token in required_tokens]
        ordered = positions == sorted(positions)

    return result(
        "shared progression gate",
        ordered,
        "checks the Badge first, then the saved Totem flag, and succeeds only after both pass",
        "FieldMoves_CheckProgression must return BADGE, then TOTEM, then NONE in that order",
    )


def check_all_mappings(root: Path) -> CheckResult:
    source = read(root, "src/field_move_tasks.c")
    failures: list[str] = []

    for requirement in REQUIREMENTS:
        body = function_body(source, requirement.check_function)
        expected_call = (
            "FieldMoves_CheckProgression(fieldMoveContext, "
            f"{requirement.badge}, {requirement.totem_flag})"
        )
        if body.count(expected_call) != 1:
            failures.append(requirement.move)
        if "return progressionError;" not in body:
            failures.append(f"{requirement.move} return")
        if "PlayerHasRequiredBadge(" in body:
            failures.append(f"{requirement.move} bypass")

    used_flags = re.findall(
        r"FieldMoves_CheckProgression\(fieldMoveContext,\s*BADGE_ID_[A-Z]+,\s*(FLAG_TOTEM_[A-Z]+_DEFEATED)\)",
        source,
    )
    unique_complete = len(used_flags) == 8 and len(set(used_flags)) == 8
    flash_unchanged = "FieldMoves_CheckProgression" not in function_body(source, "FieldMoves_CheckFlash")
    valid = not failures and unique_complete and flash_unchanged

    mapping = ", ".join(
        f"{entry.move}/{entry.totem_flag.removeprefix('FLAG_TOTEM_').removesuffix('_DEFEATED')}"
        for entry in REQUIREMENTS
    )
    return result(
        "eight HM mappings",
        valid,
        f"all eight mappings are unique and exact ({mapping}); Flash remains ungated",
        "mapping failures: " + (", ".join(failures) if failures else "duplicate/missing flag or Flash changed"),
    )


def expected_gate_result(has_badge: bool, defeated_totem: bool) -> str:
    if not has_badge:
        return "FIELD_MOVE_ERROR_BADGE"
    if not defeated_totem:
        return "FIELD_MOVE_ERROR_TOTEM"
    return "FIELD_MOVE_ERROR_NONE"


def check_truth_tables(_: Path) -> CheckResult:
    states = {
        (False, False): "FIELD_MOVE_ERROR_BADGE",
        (False, True): "FIELD_MOVE_ERROR_BADGE",
        (True, False): "FIELD_MOVE_ERROR_TOTEM",
        (True, True): "FIELD_MOVE_ERROR_NONE",
    }
    failures: list[str] = []

    for requirement in REQUIREMENTS:
        for inputs, expected in states.items():
            actual = expected_gate_result(*inputs)
            if actual != expected:
                failures.append(f"{requirement.move}:{inputs}={actual}")

    return result(
        "32-state truth table",
        not failures,
        "all 8 HMs reject neither/Badge-only/Totem-only states and allow only Badge-plus-Totem",
        "truth-table failures: " + ", ".join(failures),
    )


def check_flag_producers(root: Path) -> CheckResult:
    failures: list[str] = []

    for requirement in REQUIREMENTS:
        script = read(root, requirement.encounter_script)
        set_flag = f"SetFlag {requirement.totem_flag}"
        if script.count(set_flag) != 1:
            failures.append(f"{requirement.move}: {set_flag}")
            continue

        battle_pos = script.find("StartTotemBattle")
        won_pos = script.find("CheckWonBattle", battle_pos)
        flag_pos = script.find(set_flag, won_pos)
        if battle_pos < 0 or won_pos < 0 or flag_pos < 0 or not (battle_pos < won_pos < flag_pos):
            failures.append(f"{requirement.move}: victory ordering")

    return result(
        "persistent Totem prerequisites",
        not failures,
        "each required flag is set once, after its Totem battle result is checked",
        "flag producer failures: " + ", ".join(failures),
    )


def check_error_contract(root: Path) -> CheckResult:
    header = read(root, "include/field_move_tasks.h")
    party_source = read(root, "src/applications/party_menu/unk_02083370.c")
    text_bank = json.loads(read(root, "res/text/party_menu.json"))

    enum_match = re.search(r"enum FieldMoveError\s*\{(?P<body>.*?)\};", header, re.S)
    enum_values = []
    if enum_match:
        enum_values = re.findall(r"\b(FIELD_MOVE_ERROR_[A-Z]+)\b", enum_match.group("body"))
    expected_values = [
        "FIELD_MOVE_ERROR_NONE",
        "FIELD_MOVE_ERROR_LOCATION",
        "FIELD_MOVE_ERROR_BADGE",
        "FIELD_MOVE_ERROR_PARTNER",
        "FIELD_MOVE_ERROR_STATE",
        "FIELD_MOVE_ERROR_TOTEM",
    ]

    switch_body = function_body(party_source, "sub_02084808")
    case_ok = re.search(
        r"case\s+FIELD_MOVE_ERROR_TOTEM\s*:\s*v2\s*=\s*205\s*;\s*break\s*;",
        switch_body,
        re.S,
    ) is not None

    matching_messages = [
        message
        for message in text_bank.get("messages", [])
        if message.get("id") == "pl_msg_00000453_00205"
    ]
    expected_text = "This can’t be used until the area’s\nTotem has been defeated."
    message_ok = False
    if len(matching_messages) == 1:
        value = matching_messages[0].get("en_US")
        message_text = "".join(value) if isinstance(value, list) else value
        message_ok = message_text == expected_text

    valid = enum_values == expected_values and case_ok and message_ok
    return result(
        "Totem failure message",
        valid,
        "new enum value routes to party-menu message 205 with explicit Totem guidance",
        "expected appended enum value, switch case 205, and exact Totem requirement text",
    )


def parse_args() -> argparse.Namespace:
    default_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=default_root, help="repository root")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    checks = (
        check_shared_gate(root),
        check_all_mappings(root),
        check_truth_tables(root),
        check_flag_producers(root),
        check_error_contract(root),
    )

    print(f"Totem HM progression validation: {root}")
    for check in checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"[{status}] {check.name}: {check.detail}")

    passed = sum(check.passed for check in checks)
    print(f"summary: {passed}/{len(checks)} checks passed")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
