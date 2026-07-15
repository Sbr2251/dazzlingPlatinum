#!/usr/bin/env python3
"""Validate the added Contrary ability and its centralized stage-change semantics."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIN_STAGE = 0
MAX_STAGE = 12
DEFAULT_STAGE = 6


def messages(rel: str) -> list[dict]:
    data = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    for value in data.values():
        if isinstance(value, list) and (not value or isinstance(value[0], dict)):
            return value
    raise RuntimeError(f"No message array in {rel}")


def entry(rel: str, message_id: str) -> dict | None:
    return next((row for row in messages(rel) if row.get("id") == message_id), None)


def apply_stage(current: int, requested_change: int, contrary: bool) -> tuple[int, int, bool]:
    """Model the centralized handler after ability inversion and boundary checks."""
    effective = -requested_change if contrary else requested_change
    candidate = current + effective
    if candidate < MIN_STAGE or candidate > MAX_STAGE:
        return current, effective, False
    return candidate, effective, True


def main() -> None:
    failures: list[str] = []
    abilities = (ROOT / "generated/abilities.txt").read_text(encoding="utf-8").splitlines()
    if len(abilities) <= 125 or abilities[125] != "ABILITY_CONTRARY":
        failures.append("ABILITY_CONTRARY is not append-only ID 125")

    expected_text = (
        ("res/text/ability_names.json", "pl_msg_00000610_00125", "Contrary"),
        ("res/text/ability_names_uppercase.json", "pl_msg_00000611_00125", "CONTRARY"),
    )
    for rel, message_id, expected in expected_text:
        row = entry(rel, message_id)
        if row is None or row.get("en_US") != expected:
            failures.append(f"{rel}: {message_id} does not equal {expected!r}")

    description = entry("res/text/ability_descriptions.json", "pl_msg_00000612_00125")
    description_text = "".join(description.get("en_US", [])) if description else ""
    if "Reverses all changes" not in description_text or "to its stats." not in description_text:
        failures.append("Contrary description is missing or indexed incorrectly")

    source = (ROOT / "src/battle/battle_script.c").read_text(encoding="utf-8")
    start = source.index("static BOOL BtlCmd_ChangeStatStage(BattleSystem *battleSys, BattleContext *battleCtx)\n{")
    end = source.index("static BOOL BtlCmd_UpdateMonData(BattleSystem *battleSys, BattleContext *battleCtx)\n{", start)
    handler = source[start:end]
    hook = handler.find("if (mon->ability == ABILITY_CONTRARY)")
    invert = handler.find("stageChange = -stageChange;", hook)
    directional = handler.find("if (stageChange > 0)", invert)
    if min(hook, invert, directional) < 0 or not (hook < invert < directional):
        failures.append("Contrary inversion is not before direction-dependent checks")
    if "BATTLE_ANIMATION_STAT_BOOST" not in handler[hook:directional] or "BATTLE_ANIMATION_STAT_DROP" not in handler[hook:directional]:
        failures.append("Contrary does not update boost/drop animation after inversion")

    # Copy/swap/reset operations must remain outside the ordinary stage-change handler.
    forbidden = ("BtlCmd_CopyStatStages", "BtlCmd_SwapStatStages", "BtlCmd_ResetStatStages")
    if any(name in handler for name in forbidden):
        failures.append("Direct copy/swap/reset logic leaked into Contrary's ordinary change hook")

    cases = (
        ("Close Combat Defense drop becomes +2", DEFAULT_STAGE, -2, True, 8, 2, True),
        ("Close Combat Sp. Def drop becomes +2", DEFAULT_STAGE, -2, True, 8, 2, True),
        ("Intimidate drop becomes +1", DEFAULT_STAGE, -1, True, 7, 1, True),
        ("Swords Dance raise becomes -2", DEFAULT_STAGE, 2, True, 4, -2, True),
        ("ordinary raise becomes drop", DEFAULT_STAGE, 1, True, 5, -1, True),
        ("non-Contrary raise is unchanged", DEFAULT_STAGE, 1, False, 7, 1, True),
        ("non-Contrary drop is unchanged", DEFAULT_STAGE, -1, False, 5, -1, True),
        ("drop at minimum reverses to valid raise", MIN_STAGE, -1, True, 1, 1, True),
        ("raise at maximum reverses to valid drop", MAX_STAGE, 1, True, 11, -1, True),
        ("reversed drop fails at maximum", MAX_STAGE, -1, True, MAX_STAGE, 1, False),
        ("reversed raise fails at minimum", MIN_STAGE, 1, True, MIN_STAGE, -1, False),
    )

    rows: list[str] = []
    for name, current, requested, contrary, exp_stage, exp_effective, exp_applied in cases:
        actual = apply_stage(current, requested, contrary)
        expected = (exp_stage, exp_effective, exp_applied)
        status = "PASS" if actual == expected else "FAIL"
        rows.append(
            f"{status:4} {name}: stage {current}, request {requested:+d}, "
            f"effective {actual[1]:+d}, result {actual[0]}, applied={actual[2]}"
        )
        if actual != expected:
            failures.append(f"{name}: got {actual}, expected {expected}")

    print("\n".join(rows))
    if failures:
        print("\nFAILURES:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)
    print("\nContrary ID, text, source ordering, exclusions, and semantic test matrix passed.")


if __name__ == "__main__":
    main()
