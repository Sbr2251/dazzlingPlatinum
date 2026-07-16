#!/usr/bin/env python3
"""Deterministically validate the Affine Pulse Mega Evolution integration."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []
checks: list[str] = []


def text(rel: str) -> str:
    return (ROOT / rel).read_text()


def require(condition: bool, description: str) -> None:
    if condition:
        checks.append(description)
    else:
        errors.append(description)


enum_h = text("include/constants/battle/battle_controller.h")
msg_h = text("include/battle/message_defs.h")
controller = text("src/battle/battle_controller.c")
io = text("src/battle/battle_io_command.c")
display = text("src/battle/battle_display.c")
script_c = text("src/battle/battle_script.c")
macros = text("asm/macros/btlcmd.inc")
mega = text("res/battle/scripts/subscripts/subscript_mega_evolution.s")
integrator = text("tools/integrate_affine_pulse.py")

require(
    "BATTLE_COMMAND_CLEAR_MESSAGE_BOX,\n    BATTLE_COMMAND_AFFINE_PULSE," in enum_h,
    "Affine Pulse client command is appended after every existing command",
)
require(
    "typedef struct AffinePulseMessage" in msg_h
    and "u8 stage;" in msg_h
    and "u16 species;" in msg_h
    and "u8 form;" in msg_h,
    "Affine Pulse has an aligned stage payload carrying transformed species and form",
)
require(
    "message.command = BATTLE_COMMAND_AFFINE_PULSE;" in controller
    and "message.species = battleSys->battleCtx->battleMons[battlerId].species;" in controller
    and "message.form = battleSys->battleCtx->battleMons[battlerId].formNum;" in controller
    and "SendMessage(battleSys, COMM_RECIPIENT_CLIENT" in controller,
    "server emitter sends authoritative transformed species and form through the established client queue",
)
require(
    "[BATTLE_COMMAND_AFFINE_PULSE] = BtlIOCmd_AffinePulse" in io,
    "client dispatch maps the appended command to its handler",
)
require(
    "BattleDisplay_StartAffinePulse" in io and "ZeroDataBuffer(battlerData);" in io,
    "client wrapper starts the asynchronous task and releases its inbound buffer",
)
require(
    "BtlCmd_End,\n    BtlCmd_AffinePulse" in script_c,
    "battle-script opcode is appended after End without renumbering earlier opcodes",
)
require(
    ".macro AffinePulse battler, stage\n    .long 223" in macros,
    "AffinePulse assembler macro is fixed at appended opcode 223",
)

sequence = [
    "AffinePulse BTLSCR_MSG_TEMP, 0",
    "ChangeForm BTLSCR_MSG_TEMP",
    "AffinePulse BTLSCR_MSG_TEMP, 1",
    "PlayBattleAnimation BTLSCR_MSG_TEMP, BATTLE_ANIMATION_SHINY",
    "PrintMessage pl_msg_00000368_01269",
]
pos = [mega.find(token) for token in sequence]
require(all(p >= 0 for p in pos) and pos == sorted(pos), "charge, concealed form swap, reveal, sparkle, and announcement are strictly ordered")
require("SetMosaic BTLSCR_MSG_TEMP" not in mega, "legacy Mosaic transition is absent from the Mega subscript")

require(
    "PokemonSprite_SetAttribute(sprite, MON_SPRITE_HIDE, TRUE);" in display,
    "charge stage fully conceals the base sprite before form reload",
)
require(
    "PokemonSprite_SetAttribute(sprite, MON_SPRITE_HIDE, FALSE);" in display,
    "reveal stage explicitly restores sprite visibility",
)
require(
    "PokemonSprite_SetAttribute(sprite, MON_SPRITE_SCALE_X, 0x100);" in display
    and "PokemonSprite_SetAttribute(sprite, MON_SPRITE_SCALE_Y, 0x100);" in display,
    "completion restores both affine scales to identity",
)
require(
    "PokemonSprite_SetAttribute(sprite, MON_SPRITE_Y_OFFSET, data->baseYOffset);" in display,
    "completion restores the saved sprite Y offset",
)
require(
    "PokemonSprite_SetAttribute(sprite, MON_SPRITE_MOSAIC_INTENSITY, 0);" in display,
    "completion clears all residual mosaic state",
)
require(
    "PokemonSprite_ClearFade(sprite);" in display,
    "completion clears the sprite palette-fade state",
)
require(
    "BrightnessController_StartTransition(8, 0, 16" in display,
    "reveal returns main-screen brightness to neutral",
)
require(
    "data->species = message->species;" in display
    and "data->form = message->form;" in display
    and display.count("Sound_PlayPokemonCry(data->species, data->form);") == 1,
    "reveal task receives the transformed identity and plays exactly one Mega cry",
)
cry_pos = display.find("Sound_PlayPokemonCry(data->species, data->form);")
flash_pos = display.find("BrightnessController_StartTransition(8, 0, 16")
require(
    cry_pos >= 0 and flash_pos >= 0 and cry_pos < flash_pos,
    "transformed cry begins at the reveal flash peak before brightness restoration",
)
require(
    "case 2:\n            if (data->frame < 8)" in display,
    "concealed base-form hold lasts eight frames before the hidden form swap completes",
)
require(
    "MON_SPRITE_SCALE_X, 0x220" in display
    and "MON_SPRITE_SCALE_Y, 0x220" in display,
    "accepted reveal begins with the amplified 2.125x Mega overshoot",
)
require(
    "if (data->frame < 12)" in display
    and "MON_SPRITE_SCALE_X, -24" in display
    and "MON_SPRITE_SCALE_Y, -24" in display,
    "accepted twelve-frame reveal contracts uniformly from the amplified overshoot",
)
require(
    display.count("PokemonSprite_IsFadeActive(sprite) == FALSE") >= 2
    and display.count("BrightnessController_IsTransitionComplete(BRIGHTNESS_MAIN_SCREEN) == TRUE") >= 3,
    "both transformation stages block on fade and brightness completion before cleanup",
)
require(
    "MON_SPRITE_SCALE_X, 0x220" in integrator
    and "if (data->frame < 12)" in integrator
    and "PokemonSprite_IsFadeActive(sprite) == FALSE" in integrator
    and "message.species = battleSys->battleCtx->battleMons[battlerId].species" in integrator
    and "message.form = battleSys->battleCtx->battleMons[battlerId].formNum" in integrator
    and "Sound_PlayPokemonCry(data->species, data->form);" in integrator,
    "reproducible integration script emits the accepted iteration with synchronized reveal cry",
)
require(
    display.count("BattleController_EmitClearCommand(data->battleSys, data->battler, data->command);") == 2,
    "both Affine Pulse stages acknowledge completion exactly once",
)
require(
    "Heap_Free(data);\n            SysTask_Done(task);" in display,
    "task completion frees heap state and terminates the system task",
)

# Ensure client table designators cover all enum commands exactly once.
enum_body = re.search(r"enum BattleCommand \{(.*?)\};", enum_h, re.S)
if enum_body:
    commands = re.findall(r"\b(BATTLE_COMMAND_[A-Z0-9_]+)\b", enum_body.group(1))
    table = re.search(r"Unk_ov16_0226F068\[\] = \{(.*?)\n\};", io, re.S)
    entries = re.findall(r"\[(BATTLE_COMMAND_[A-Z0-9_]+)\]", table.group(1)) if table else []
    require(commands == entries, "battle client dispatch entries exactly match enum order and coverage")
else:
    errors.append("battle command enum was parseable")

report = ROOT / "deliverables/mega-staraptor-proof/affine-pulse-static-validation.txt"
report.parent.mkdir(parents=True, exist_ok=True)
lines = [f"PASS: {c}" for c in checks]
lines += [f"FAIL: {e}" for e in errors]
lines += [f"\nSUMMARY: {len(checks)} passed, {len(errors)} failed"]
report.write_text("\n".join(lines) + "\n")
print(report.read_text(), end="")
raise SystemExit(1 if errors else 0)
