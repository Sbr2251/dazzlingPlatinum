#!/usr/bin/env python3
"""Validate the source contracts that define Totem Battle Mode.

This script is intentionally host-side and deterministic. It complements, but
does not replace, emulator validation of animation, input, and battle flow.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


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


def check_constants_and_status(root: Path) -> CheckResult:
    constants = read(root, "include/constants/totem_battle.h")
    battle = read(root, "include/constants/battle.h")

    ids = {
        name: int(value)
        for name, value in re.findall(
            r"^#define\s+(TOTEM_ENCOUNTER_(?!COUNT)[A-Z0-9_]+)\s+(\d+)\s*$",
            constants,
            re.M,
        )
    }
    count_match = re.search(r"^#define\s+TOTEM_ENCOUNTER_COUNT\s+(\d+)\s*$", constants, re.M)
    size_match = re.search(r"^#define\s+TOTEM_PARTY_SIZE\s+(\d+)\s*$", constants, re.M)
    cap_match = re.search(r"^#define\s+TOTEM_MAX_ALLY_SUMMONS\s+(\d+)\s*$", constants, re.M)
    status_match = re.search(r"^#define\s+BATTLE_STATUS_TOTEM\s+\(1\s*<<\s*(\d+)\)\s*$", battle, re.M)

    valid = (
        count_match is not None
        and int(count_match.group(1)) == 8
        and len(ids) == 8
        and sorted(ids.values()) == list(range(8))
        and size_match is not None
        and int(size_match.group(1)) == 3
        and cap_match is not None
        and int(cap_match.group(1)) == 2
        and status_match is not None
        and battle.count("BATTLE_STATUS_TOTEM") == 1
    )
    names = ", ".join(name.removeprefix("TOTEM_ENCOUNTER_") for name, _ in sorted(ids.items(), key=lambda item: item[1]))
    return result(
        "constants and reserved status",
        valid,
        f"8 contiguous IDs ({names}); party size 3; summon cap 2; unique status bit",
        "expected 8 IDs numbered 0-7, party size 3, summon cap 2, and one Totem status-bit definition",
    )


def parse_encounter_ids(constants: str) -> dict[str, int]:
    return {
        name: int(value)
        for name, value in re.findall(
            r"^#define\s+(TOTEM_ENCOUNTER_(?!COUNT)[A-Z0-9_]+)\s+(\d+)\s*$",
            constants,
            re.M,
        )
    }


def check_encounter_table(root: Path) -> CheckResult:
    constants = read(root, "include/constants/totem_battle.h")
    source = read(root, "src/totem_battle.c")
    expected = parse_encounter_ids(constants)

    marker = re.search(r"sTotemEncounterTable\s*\[\s*TOTEM_ENCOUNTER_COUNT\s*\]\s*=\s*\{", source)
    if not marker:
        return CheckResult("encounter table", False, "sTotemEncounterTable initializer not found")
    table = balanced_block(source, source.find("{", marker.start()))

    found: dict[str, list[tuple[str, int]]] = {}
    entry_pattern = re.compile(r"\[(TOTEM_ENCOUNTER_[A-Z0-9_]+)\]\s*=\s*\{")
    for match in entry_pattern.finditer(table):
        block = balanced_block(table, table.find("{", match.start()))
        party = [
            (species, int(level))
            for species, level in re.findall(
                r"\{\s*(SPECIES_[A-Z0-9_]+)\s*,\s*(\d+)\s*,\s*0\s*\}",
                block,
            )
        ]
        found[match.group(1)] = party

    complete = set(found) == set(expected)
    three_each = all(len(party) == 3 for party in found.values())
    positive_levels = all(level > 0 for party in found.values() for _, level in party)
    matching_totems = all(
        party and party[0][0] == encounter.replace("TOTEM_ENCOUNTER_", "SPECIES_")
        for encounter, party in found.items()
    )
    lookup_safe = "encounterID >= TOTEM_ENCOUNTER_COUNT" in source and "&sTotemEncounterTable[encounterID]" in source
    valid = complete and three_each and positive_levels and matching_totems and lookup_safe
    return result(
        "encounter table",
        valid,
        "all 8 indexed encounters contain one matching Totem plus exactly two leveled allies; lookup is bounds-checked",
        f"table mismatch: entries={sorted(found)}, expected={sorted(expected)}, party_sizes={[len(value) for value in found.values()]}",
    )


def check_field_calls(root: Path) -> CheckResult:
    constants = read(root, "include/constants/totem_battle.h")
    expected = set(parse_encounter_ids(constants))
    found: list[tuple[Path, str]] = []
    for path in (root / "res/field/scripts").rglob("*.s"):
        text = path.read_text(encoding="utf-8")
        for encounter in re.findall(r"^\s*StartTotemBattle\s+(TOTEM_ENCOUNTER_[A-Z0-9_]+)\s*$", text, re.M):
            found.append((path.relative_to(root), encounter))

    actual = [encounter for _, encounter in found]
    valid = len(found) == 8 and set(actual) == expected and all(actual.count(item) == 1 for item in expected)
    return result(
        "field integration",
        valid,
        "exactly 8 field scripts call StartTotemBattle, once for every configured encounter",
        f"found {len(found)} calls: {actual}; expected exactly once each: {sorted(expected)}",
    )


def check_constructor_and_registration(root: Path) -> CheckResult:
    encounter = read(root, "src/encounter.c")
    body = function_body(encounter, "Encounter_NewTotemBattle")
    scrcmd = read(root, "src/scrcmd.c")
    macro = read(root, "asm/macros/scrcmd.inc")
    source_manifest = read(root, "src/meson.build")
    linker = read(root, "platinum.us/main.lsf")
    sub_manifest = read(root, "res/battle/scripts/subscripts/meson.build")
    sub_order = read(root, "res/battle/scripts/subscripts/sub_seq.order")

    body_tokens = (
        "TotemBattle_GetEncounterConfig",
        "TOTEM_PARTY_SIZE",
        "CreateWildMon_Scripted",
        "BATTLE_TYPE_DOUBLES",
        "BATTLE_STATUS_TOTEM",
    )
    table_match = re.search(r"const\s+ScrCmdFunc\s+Unk_020EAC58\[\]\s*=\s*\{", scrcmd)
    handlers: list[str] = []
    if table_match:
        table = balanced_block(scrcmd, scrcmd.find("{", table_match.start()))
        handlers = re.findall(r"^\s*(ScrCmd_[A-Za-z0-9_]+)\s*,\s*$", table, re.M)
    opcode_ok = len(handlers) > 840 and handlers[840] == "ScrCmd_StartTotemBattle"

    valid = (
        all(token in body for token in body_tokens)
        and opcode_ok
        and re.search(r"\.macro\s+StartTotemBattle", macro) is not None
        and re.search(r"\.(?:short|hword)\s+840", macro) is not None
        and "totem_battle.c" in source_manifest
        and "totem_battle.c.o" in linker
        and "subscript_totem_summon_ally.s" in sub_manifest
        and sub_order.count("subscript_totem_summon_ally") == 1
    )
    return result(
        "constructor and registrations",
        valid,
        "constructor creates a three-member wild doubles party with Totem status; opcode, macro, source, linker, and subscript registrations exist",
        "one or more constructor/opcode/build/linker/subscript registration contracts are missing",
    )


def check_fixed_topology(root: Path) -> CheckResult:
    controller = read(root, "src/battle/battle_controller_player.c")
    helper = read(root, "src/totem_battle.c")
    init_body = function_body(controller, "BattleControllerPlayer_InitBattleMons")
    replace_body = function_body(controller, "BattleControllerPlayer_ReplaceFainted")

    valid = (
        "selectedPartySlot[BATTLER_PLAYER_2] = MAX_PARTY_SIZE" in init_body
        and "selectedPartySlot[BATTLER_ENEMY_2] = MAX_PARTY_SIZE" in init_body
        and "TotemBattle_IsInactiveBattler" in init_body
        and "battler == BATTLER_PLAYER_2" in helper
        and "battler == BATTLER_ENEMY_2" in helper
        and "selectedPartySlot[battler] == MAX_PARTY_SIZE" in helper
        and "TotemBattle_IsPermanentlyInactiveBattler" in replace_body
        and "i == BATTLER_ENEMY_2" in replace_body
        and "selectedPartySlot[i] = MAX_PARTY_SIZE" in replace_body
    )
    return result(
        "fixed four-battler topology",
        valid,
        "player slot 2 is permanently absent; enemy slot 2 is reserved, skipped during init, and returned to the absent sentinel after fainting",
        "inactive-slot initialization, helper predicates, or ally deactivation contract is incomplete",
    )


def check_opening_boost(root: Path) -> CheckResult:
    controller = read(root, "src/battle/battle_controller_player.c")
    start_body = function_body(controller, "BattleControllerPlayer_StartEncounter")
    intro = read(root, "res/battle/scripts/subscripts/subscript_start_encounter.s")
    boost = read(root, "res/battle/scripts/subscripts/subscript_boost_all_stats.s")

    stats = (
        "MOVE_SUBSCRIPT_PTR_ATTACK_UP_1_STAGE",
        "MOVE_SUBSCRIPT_PTR_DEFENSE_UP_1_STAGE",
        "MOVE_SUBSCRIPT_PTR_SPEED_UP_1_STAGE",
        "MOVE_SUBSCRIPT_PTR_SP_ATTACK_UP_1_STAGE",
        "MOVE_SUBSCRIPT_PTR_SP_DEFENSE_UP_1_STAGE",
    )
    totem_label = intro.find("TotemEncounter:")
    next_branch = intro.find("\n_118:", totem_label)
    branch = intro[totem_label:next_branch] if totem_label >= 0 and next_branch >= 0 else ""
    valid = (
        "TotemBattle_IsActive" in start_body
        and "sideEffectMon = BATTLER_ENEMY_1" in start_body
        and "sideEffectType = SIDE_EFFECT_TYPE_INDIRECT" in start_body
        and "Call BATTLE_SUBSCRIPT_BOOST_ALL_STATS" in branch
        and branch.count("Call BATTLE_SUBSCRIPT_BOOST_ALL_STATS") == 1
        and "SetPokemonEncounter BTLSCR_ENEMY_SLOT_1" in branch
        and "PokemonSlideIn BTLSCR_PLAYER_SLOT_1" in branch
        and all(boost.count(stat) == 1 for stat in stats)
        and boost.count("Call BATTLE_SUBSCRIPT_UPDATE_STAT_STAGE") == 5
    )
    return result(
        "opening Totem omni-boost",
        valid,
        "Totem enemy slot 1 is the side-effect target; the dedicated intro calls the canonical +1 Attack/Defense/Speed/Sp. Atk/Sp. Def script once",
        "Totem intro target, explicit-slot presentation, or one of the five +1 stat-stage operations is missing",
    )


def check_turn_end_summoning(root: Path) -> CheckResult:
    controller = read(root, "src/battle/battle_controller_player.c")
    turn_end = function_body(controller, "BattleControllerPlayer_TurnEnd")
    summon = function_body(controller, "BattleControllerPlayer_TrySummonTotemAlly")
    context = read(root, "include/battle/battle_context.h")

    try_pos = turn_end.find("BattleControllerPlayer_TrySummonTotemAlly")
    reset_pos = turn_end.find("totemSummonAttempted = FALSE")
    init_pos = turn_end.find("BattleContext_Init")
    order_ok = 0 <= try_pos < reset_pos < init_pos

    summon_tokens = (
        "TotemBattle_IsActive(battleSys) == FALSE",
        "battleMons[BATTLER_ENEMY_1].curHP == 0",
        "totemSummonAttempted",
        "totemSummonsUsed >= TOTEM_MAX_ALLY_SUMMONS",
        "selectedPartySlot[BATTLER_ENEMY_2] != MAX_PARTY_SIZE",
        "switchedMon = BATTLER_ENEMY_2",
        "switchedPartySlot[BATTLER_ENEMY_2] = battleCtx->totemSummonsUsed + 1",
        "BATTLER_STATUS_SWITCHING",
        "totemSummonsUsed++",
        "totemSummonAttempted = TRUE",
        "LOAD_SUBSEQ(subscript_totem_summon_ally)",
    )
    valid = (
        order_ok
        and all(token in summon for token in summon_tokens)
        and context.count("totemSummonsUsed") == 1
        and context.count("totemSummonAttempted") == 1
    )
    return result(
        "turn-end ally summoning",
        valid,
        "summon gate runs after faint replacement; requires living Totem, vacant ally slot, unused turn attempt, and fewer than 2 summons; slots 1 then 2 are activated and the guard resets before next-turn init",
        "summon predicate, slot sequence, cap, subscript dispatch, per-turn state, or turn-end ordering is incomplete",
    )


def check_summon_script(root: Path) -> CheckResult:
    script = read(root, "res/battle/scripts/subscripts/subscript_totem_summon_ally.s")
    tokens = (
        "SwitchAndUpdateMon BTLSCR_SWITCHED_MON",
        "PrintGlobalMessage",
        "PokemonSendOut BTLSCR_SWITCHED_MON",
        "HealthbarSlideIn BTLSCR_SWITCHED_MON",
        "Call BATTLE_SUBSCRIPT_HAZARDS_CHECK",
        "BTLVAR_FAINTED_MON",
        "Call BATTLE_SUBSCRIPT_FAINT_MON",
    )
    valid = all(token in script for token in tokens)
    return result(
        "ally send-out subscript",
        valid,
        "standard switch/update, wild-appearance message, send-out, health bar, hazards, and faint-on-entry handling are present",
        "summon subscript is missing one or more standard send-out or hazard/faint steps",
    )


def check_battle_results(root: Path) -> CheckResult:
    controller = read(root, "src/battle/battle_controller_player.c")
    body = function_body(controller, "BattleControllerPlayer_CheckBattleOver")
    totem_start = body.find("if (TotemBattle_IsActive")
    normal_start = body.find("\n    for (i = 0; i < maxBattlers", totem_start)
    branch = body[totem_start:normal_start] if totem_start >= 0 and normal_start >= 0 else ""
    valid = (
        "battleMons[BATTLER_ENEMY_1].curHP == 0" in branch
        and "BATTLE_RESULT_WIN" in branch
        and "Party_GetCurrentCount" in branch
        and "totalPartyHP == 0" in branch
        and "BATTLE_RESULT_LOSE" in branch
        and "BattleSystem_SetResultFlag" in branch
        and "return FALSE" in branch
        and len(branch) > 0
    )
    return result(
        "Totem battle result semantics",
        valid,
        "Totem KO ends the battle in victory regardless of ally state; zero usable player-party HP produces loss; ordinary logic remains in a separate fallback path",
        "Totem-specific win/loss override or normal-battle fallback boundary is incomplete",
    )


def check_test_save_flag_mapping(root: Path) -> CheckResult:
    flag_names = [line.strip() for line in read(root, "generated/vars_flags.txt").splitlines()]
    builder = read(root, "tools/build_totem_mode_test_save.py")
    inspector = read(root, "tools/inspect_totem_save_flags.py")
    vars_offset_match = re.search(r"^VARS_FLAGS_OFFSET\s*=\s*(0x[0-9A-Fa-f]+)\s*$", inspector, re.M)
    num_vars_match = re.search(r"^NUM_VARS\s*=\s*(0x[0-9A-Fa-f]+)\s*$", inspector, re.M)
    default_offset_match = re.search(
        r'"--vars-flags-rel".*?default\s*=\s*(0x[0-9A-Fa-f]+)',
        builder,
        re.S,
    )
    expected_flags_offset = (
        int(vars_offset_match.group(1), 16) + int(num_vars_match.group(1), 16) * 2
        if vars_offset_match and num_vars_match
        else None
    )
    builder_flags_offset = (
        int(default_offset_match.group(1), 16) if default_offset_match else None
    )
    found = {
        species: (int(defeated, 16), int(hidden, 16))
        for species, defeated, hidden in re.findall(
            r'^\s*"([a-z]+)":\s*\(0x([0-9A-Fa-f]+),\s*0x([0-9A-Fa-f]+)\),\s*$',
            builder,
            re.M,
        )
    }
    species_names = (
        "hitmonlee",
        "vespiquen",
        "skarmory",
        "lapras",
        "spiritomb",
        "aggron",
        "mamoswine",
        "kingdra",
    )
    expected = {
        species: (
            flag_names.index(f"FLAG_TOTEM_{species.upper()}_DEFEATED"),
            flag_names.index(f"FLAG_HIDE_TOTEM_{species.upper()}"),
        )
        for species in species_names
    }
    valid = (
        found == expected
        and expected_flags_offset == 0x0FEC
        and builder_flags_offset == expected_flags_offset
        and "TOTEM_OUTCOME_FLAGS_BY_SPECIES[species]" in builder
        and "0x0900 + encounter_index" not in builder
        and "0x0908 + encounter_index" not in builder
    )
    return result(
        "test-save outcome-flag mapping",
        valid,
        "all 8 deterministic save fixtures use the exact generated defeated/hide pairs and the proven 0x0FEC serialized flag-array offset",
        f"save-builder mismatch: found={found}, expected={expected}, builder_offset={builder_flags_offset}, expected_offset={expected_flags_offset}",
    )


def check_tracked_artifacts(root: Path) -> CheckResult:
    forbidden_suffixes = (
        ".nds",
        ".sav",
        ".dsv",
        ".log",
        ".zip",
        ".tar",
        ".tgz",
        ".7z",
        ".rar",
    )
    merge_base = subprocess.run(
        ["git", "merge-base", "HEAD", "master"],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()
    changed = subprocess.run(
        ["git", "diff", "--name-only", "-z", merge_base, "--"],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
    ).stdout
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
    ).stdout
    paths = {
        Path(value.decode("utf-8"))
        for value in (changed + untracked).split(b"\0")
        if value
    }
    forbidden = sorted(
        str(path) for path in paths if path.name.lower().endswith(forbidden_suffixes)
    )
    return result(
        "branch artifact hygiene",
        not forbidden,
        "no ROMs, saves, emulator logs, or archives occur in the feature-branch delta or untracked source workspace",
        f"forbidden branch-delta or untracked artifacts: {forbidden}",
    )


def run_check(name: str, check: Callable[[Path], CheckResult], root: Path) -> CheckResult:
    try:
        return check(root)
    except Exception as exc:  # A validator failure should be reported, not hidden.
        return CheckResult(name, False, f"validator exception: {type(exc).__name__}: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path("."))
    args = parser.parse_args()
    root = args.root.resolve()

    checks: tuple[tuple[str, Callable[[Path], CheckResult]], ...] = (
        ("constants and reserved status", check_constants_and_status),
        ("encounter table", check_encounter_table),
        ("field integration", check_field_calls),
        ("constructor and registrations", check_constructor_and_registration),
        ("fixed four-battler topology", check_fixed_topology),
        ("opening Totem omni-boost", check_opening_boost),
        ("turn-end ally summoning", check_turn_end_summoning),
        ("ally send-out subscript", check_summon_script),
        ("Totem battle result semantics", check_battle_results),
        ("test-save outcome-flag mapping", check_test_save_flag_mapping),
        ("branch artifact hygiene", check_tracked_artifacts),
    )
    results = [run_check(name, check, root) for name, check in checks]

    print(f"Totem Battle Mode source-contract validation: {root}")
    for item in results:
        status = "PASS" if item.passed else "FAIL"
        print(f"[{status}] {item.name}: {item.detail}")

    passed = sum(item.passed for item in results)
    print(f"summary: {passed}/{len(results)} checks passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
