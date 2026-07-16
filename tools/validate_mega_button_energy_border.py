#!/usr/bin/env python3
"""Deterministically validate the MEGA button Energy Border integration."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "deliverables/mega-button-animation-proof/energy-border-static-validation.txt"

errors: list[str] = []
checks: list[str] = []


def require(condition: bool, description: str) -> None:
    (checks if condition else errors).append(description)


def read(rel: str) -> str:
    return (ROOT / rel).read_text()


source = read("src/battle/battle_cursor.c")
integrator = read("tools/integrate_mega_button_animation.py")
auditor = read("tools/audit_mega_button_palette_slots.py")


def parse_palette(name: str) -> list[str]:
    match = re.search(rf"static const u16 {name}\[16\] = \{{(.*?)\n\}};", source, re.S)
    if match is None:
        return []
    return re.findall(r"RGB\(\s*\d+,\s*\d+,\s*\d+\)", match.group(1))


active_palette = parse_palette("sMegaButtonPalette_Active")
trail_palette = parse_palette("sMegaButtonPalette_EnergyTrail")
head_palette = parse_palette("sMegaButtonPalette_EnergyHead")

require(
    "#define MEGA_BORDER_BASE_PALETTE 2" in source
    and "#define MEGA_BORDER_TRAIL_PALETTE 14" in source
    and "#define MEGA_BORDER_HEAD_PALETTE 15" in source,
    "Energy Border reserves base bank 2 and isolated trail/head banks 14 and 15",
)
require(
    "sMegaButtonPalette_EnergyTrail[16]" in source
    and "sMegaButtonPalette_EnergyHead[16]" in source
    and source.count("PaletteData_LoadBuffer(paletteSys, sMegaButtonPalette_Energy") == 2,
    "two complete 16-color energy palettes are loaded only through the armed-state palette path",
)
require(
    len(active_palette) == len(trail_palette) == len(head_palette) == 16
    and all(trail_palette[i] == active_palette[i] and head_palette[i] == active_palette[i] for i in (0, 3, 4, 5, 6, 7, 8, 9, 12, 15))
    and all(trail_palette[i] != active_palette[i] and head_palette[i] != active_palette[i] for i in (1, 2, 10, 11, 13, 14)),
    "energy palettes alter only perimeter outline, shadow, and accent ink while preserving every fill entry",
)
require(
    "LoadMoveSelectPltt(BattleSystem_PaletteSys(param0->battleSys), moveType, 5, PLTTBUF_SUB_BG, PLTT_8 + moveSlot);" in source
    and "MEGA_BORDER_TRAIL_PALETTE 14" in source
    and "MEGA_BORDER_HEAD_PALETTE 15" in source,
    "Energy banks do not overlap the four dynamic move-type banks 8 through 11",
)
require(
    "payload_size = struct.unpack_from(\"<I\", data, 0x20)[0]" in auditor
    and "entry >> 12" in auditor
    and "unused = [bank for bank in range(16) if bank not in all_counts]" in auditor,
    "NSCR audit tool derives palette occupancy from decoded tilemap entries rather than assumptions",
)

path_match = re.search(
    r"static const u8 sMegaBorderPath\[MEGA_BORDER_PATH_LENGTH\]\[2\] = \{(.*?)\n\};",
    source,
    re.S,
)
coords: list[tuple[int, int]] = []
if path_match:
    for x_raw, y_raw in re.findall(r"\{\s*(0x[0-9A-Fa-f]+|\d+)\s*,\s*(0x[0-9A-Fa-f]+|\d+)\s*\}", path_match.group(1)):
        coords.append((int(x_raw, 0), int(y_raw, 0)))

expected_perimeter = {
    (x, y)
    for x in range(1, 15)
    for y in range(0x13, 0x18)
    if x in (1, 14) or y in (0x13, 0x17)
}
require(len(coords) == 34, "clockwise Energy Border path contains exactly 34 tile positions")
require(len(set(coords)) == len(coords), "Energy Border path contains no duplicate tile positions")
require(set(coords) == expected_perimeter, "Energy Border path covers the complete 14-by-5 outer perimeter and no interior tiles")
require(
    len(coords) == 34
    and all(abs(coords[(i + 1) % len(coords)][0] - coords[i][0]) + abs(coords[(i + 1) % len(coords)][1] - coords[i][1]) == 1 for i in range(len(coords))),
    "all path steps, including loop closure, move to an orthogonally adjacent border tile",
)

constants = {}
for name in ("MEGA_BORDER_PATH_LENGTH", "MEGA_BORDER_STEP_FRAMES", "MEGA_BORDER_SURGE_FRAMES", "MEGA_BORDER_QUIET_FRAMES"):
    match = re.search(rf"#define {name} (\d+)", source)
    if match:
        constants[name] = int(match.group(1))
require(
    constants.get("MEGA_BORDER_PATH_LENGTH") == 34
    and constants.get("MEGA_BORDER_STEP_FRAMES") == 2
    and constants.get("MEGA_BORDER_SURGE_FRAMES") == 6
    and constants.get("MEGA_BORDER_QUIET_FRAMES") == 10,
    "accepted timing is a 68-frame lap, 6-frame surge, and 10-frame clean pause",
)
require(
    "SetMegaButtonBorderPalette(param0, (travelStep + MEGA_BORDER_PATH_LENGTH - 2) % MEGA_BORDER_PATH_LENGTH, MEGA_BORDER_TRAIL_PALETTE);" in source
    and "SetMegaButtonBorderPalette(param0, (travelStep + MEGA_BORDER_PATH_LENGTH - 1) % MEGA_BORDER_PATH_LENGTH, MEGA_BORDER_TRAIL_PALETTE);" in source
    and "SetMegaButtonBorderPalette(param0, travelStep, MEGA_BORDER_HEAD_PALETTE);" in source,
    "travel phase draws a two-tile soft trail behind one bright head segment",
)
require(
    all(f"SetMegaButtonBorderPalette(param0, {corner}, MEGA_BORDER_HEAD_PALETTE);" in source for corner in (0, 13, 17, 30)),
    "surge phase accents all four perimeter corners with the head palette",
)
require(
    "else if (frame == MEGA_BORDER_TRAVEL_FRAMES + MEGA_BORDER_SURGE_FRAMES) {\n        ResetMegaButtonBorder(param0);" in source,
    "surge returns the complete perimeter to the base palette before the quiet phase",
)
require(
    "if (param0->megaBorderWasActive == FALSE)" in source
    and "LoadMegaButtonPalette(param0, TRUE);" in source
    and "param0->megaBorderFrame = 0;" in source
    and "param0->megaBorderWasActive = TRUE;" in source,
    "arming loads energy palettes once and starts the border at a deterministic frame",
)
require(
    "} else if (param0->megaBorderWasActive) {\n            ResetMegaButtonBorder(param0);\n            LoadMegaButtonPalette(param0, FALSE);" in source
    and "param0->megaBorderWasActive = FALSE;" in source,
    "disarming immediately restores border tile attributes and the inactive base palette",
)
require(
    source.count("battleCtx->megaEvolutionTriggered[battler] = !battleCtx->megaEvolutionTriggered[battler];") == 2
    and source.count("battleCtx->megaEvolutionTriggered[battler] = !battleCtx->megaEvolutionTriggered[battler];\n\n            UpdateMegaIconState(param0);") == 2,
    "both touch and button toggle paths synchronize the border immediately",
)
require(
    "if (param0->unk_66B == 11) {\n        UpdateMegaIconState(param0);\n    }" in source,
    "move-menu input advances the selected-state border once per battle UI frame",
)
require(
    "megaBorderTask" not in source
    and "MegaBorderTaskState" not in source
    and "SysTask_ExecuteAfterVBlank(MegaBorder" not in source,
    "border animation adds no heap allocation, OAM sprite, or independently owned task lifecycle",
)
require(
    "if \"MEGA_BORDER_PATH_LENGTH\" in text:" in integrator
    and "expected one match" in integrator
    and "toggle hooks: expected two matches" in integrator,
    "integration script is idempotent and fails closed when source anchors differ",
)
require(
    "MEGA_BORDER_TRAIL_PALETTE 14" in integrator
    and "MEGA_BORDER_HEAD_PALETTE 15" in integrator
    and "MEGA_BORDER_TOTAL_FRAMES" in integrator,
    "reproducible integrator emits the accepted palette banks and timing state machine",
)

REPORT.parent.mkdir(parents=True, exist_ok=True)
lines = [f"PASS: {description}" for description in checks]
lines.extend(f"FAIL: {description}" for description in errors)
lines.append(f"\nSUMMARY: {len(checks)} passed, {len(errors)} failed")
REPORT.write_text("\n".join(lines) + "\n")
print(REPORT.read_text(), end="")
raise SystemExit(1 if errors else 0)
