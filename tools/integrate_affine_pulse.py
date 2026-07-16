#!/usr/bin/env python3
"""Integrate the staged Affine Pulse Mega Evolution display sequence.

The patch is deliberately idempotent and appends both client and battle-script
commands so all existing numeric command IDs remain stable.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"anchor not found in {path}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1))


# Client command ID: append only.
path = ROOT / "include/constants/battle/battle_controller.h"
replace_once(
    path,
    "    BATTLE_COMMAND_CLEAR_MESSAGE_BOX,\n};",
    "    BATTLE_COMMAND_CLEAR_MESSAGE_BOX,\n    BATTLE_COMMAND_AFFINE_PULSE,\n};",
)

# Compact serialized payload.
path = ROOT / "include/battle/message_defs.h"
replace_once(
    path,
    "} MosaicSetMessage;\n\ntypedef struct MonChangeFormMessage",
    "} MosaicSetMessage;\n\ntypedef struct AffinePulseMessage {\n"
    "    u8 command;\n"
    "    u8 stage;\n"
    "    u16 species;\n"
    "    u8 form;\n"
    "    u8 padding_05[3];\n"
    "} AffinePulseMessage;\n\ntypedef struct MonChangeFormMessage",
)

# Public controller emitter.
path = ROOT / "include/battle/battle_controller.h"
replace_once(
    path,
    "void BattleController_EmitSetMosaic(BattleSystem *battleSys, int battlerId, int param2, int wait);\n",
    "void BattleController_EmitSetMosaic(BattleSystem *battleSys, int battlerId, int param2, int wait);\n"
    "void BattleController_EmitAffinePulse(BattleSystem *battleSys, int battlerId, int stage);\n",
)

# Public display entrypoint.
path = ROOT / "include/battle/battle_display.h"
replace_once(
    path,
    "void ov16_0225E0F4(BattleSystem *battleSys, BattlerData *param1, MosaicSetMessage *message);\n",
    "void ov16_0225E0F4(BattleSystem *battleSys, BattlerData *param1, MosaicSetMessage *message);\n"
    "void BattleDisplay_StartAffinePulse(BattleSystem *battleSys, BattlerData *battlerData, AffinePulseMessage *message);\n",
)

# Server serializer beside Mosaic.
path = ROOT / "src/battle/battle_controller.c"
replace_once(
    path,
    "void BattleController_EmitChangeWeatherForm(BattleSystem *battleSys, int battlerId)\n",
    "void BattleController_EmitAffinePulse(BattleSystem *battleSys, int battlerId, int stage)\n"
    "{\n"
    "    AffinePulseMessage message;\n\n"
    "    message.command = BATTLE_COMMAND_AFFINE_PULSE;\n"
    "    message.stage = stage;\n"
    "    message.species = battleSys->battleCtx->battleMons[battlerId].species;\n"
    "    message.form = battleSys->battleCtx->battleMons[battlerId].formNum;\n\n"
    "    SendMessage(battleSys, COMM_RECIPIENT_CLIENT, battlerId, &message, sizeof(AffinePulseMessage));\n"
    "}\n\n"
    "void BattleController_EmitChangeWeatherForm(BattleSystem *battleSys, int battlerId)\n",
)

# Client dispatch declaration, appended table entry, and wrapper.
path = ROOT / "src/battle/battle_io_command.c"
replace_once(
    path,
    "static void ov16_0225CB80(BattleSystem *battleSys, BattlerData *param1);\n",
    "static void ov16_0225CB80(BattleSystem *battleSys, BattlerData *param1);\n"
    "static void BtlIOCmd_AffinePulse(BattleSystem *battleSys, BattlerData *battlerData);\n",
)
replace_once(
    path,
    "    [BATTLE_COMMAND_CLEAR_MESSAGE_BOX] = ov16_0225CB80\n};",
    "    [BATTLE_COMMAND_CLEAR_MESSAGE_BOX] = ov16_0225CB80,\n"
    "    [BATTLE_COMMAND_AFFINE_PULSE] = BtlIOCmd_AffinePulse\n};",
)
replace_once(
    path,
    "static void ov16_0225C684(BattleSystem *battleSys, BattlerData *param1)\n",
    "static void BtlIOCmd_AffinePulse(BattleSystem *battleSys, BattlerData *battlerData)\n"
    "{\n"
    "    AffinePulseMessage *message = (AffinePulseMessage *)&battlerData->data[0];\n\n"
    "    BattleDisplay_StartAffinePulse(battleSys, battlerData, message);\n"
    "    ZeroDataBuffer(battlerData);\n"
    "}\n\n"
    "static void ov16_0225C684(BattleSystem *battleSys, BattlerData *param1)\n",
)

# Display task: stage 0 charges/compresses into a concealed white silhouette;
# stage 1 reveals the reloaded Mega sprite with a flash and elastic overshoot.
path = ROOT / "src/battle/battle_display.c"
replace_once(
    path,
    "static void ov16_022634DC(SysTask *param0, void *param1);\n",
    "static void ov16_022634DC(SysTask *param0, void *param1);\n"
    "static void AffinePulseTask(SysTask *task, void *data);\n",
)
replace_once(
    path,
    "typedef struct PartyGaugeTask {",
    "typedef struct AffinePulseTaskData {\n"
    "    BattleSystem *battleSys;\n"
    "    PokemonSprite *sprite;\n"
    "    u8 command;\n"
    "    u8 battler;\n"
    "    u16 species;\n"
    "    u8 form;\n"
    "    u8 stage;\n"
    "    u8 state;\n"
    "    u8 frame;\n"
    "    s16 baseYOffset;\n"
    "} AffinePulseTaskData;\n\n"
    "void BattleDisplay_StartAffinePulse(BattleSystem *battleSys, BattlerData *battlerData, AffinePulseMessage *message)\n"
    "{\n"
    "    AffinePulseTaskData *data = Heap_Alloc(HEAP_ID_BATTLE, sizeof(AffinePulseTaskData));\n\n"
    "    MI_CpuClear8(data, sizeof(AffinePulseTaskData));\n"
    "    data->battleSys = battleSys;\n"
    "    data->sprite = battlerData->unk_20;\n"
    "    data->command = message->command;\n"
    "    data->battler = battlerData->battler;\n"
    "    data->species = message->species;\n"
    "    data->form = message->form;\n"
    "    data->stage = message->stage;\n"
    "    data->baseYOffset = PokemonSprite_GetAttribute(data->sprite, MON_SPRITE_Y_OFFSET);\n\n"
    "    SysTask_Start(AffinePulseTask, data, 0);\n"
    "}\n\n"
    "typedef struct PartyGaugeTask {",
)
replace_once(
    path,
    "static void ShowPartyGaugeTask(SysTask *param0, void *param1)\n",
    "static void AffinePulseTask(SysTask *task, void *taskData)\n"
    "{\n"
    "    AffinePulseTaskData *data = taskData;\n"
    "    PokemonSprite *sprite = data->sprite;\n"
    "    const int screenPlanes = GX_BLEND_PLANEMASK_BG0 | GX_BLEND_PLANEMASK_BG1 |\n"
    "        GX_BLEND_PLANEMASK_BG2 | GX_BLEND_PLANEMASK_BG3 |\n"
    "        GX_BLEND_PLANEMASK_OBJ | GX_BLEND_PLANEMASK_BD;\n\n"
    "    if (data->stage == 0) {\n"
    "        switch (data->state) {\n"
    "        case 0:\n"
    "            PokemonSprite_SetAttribute(sprite, MON_SPRITE_HIDE, FALSE);\n"
    "            PokemonSprite_SetAttribute(sprite, MON_SPRITE_MOSAIC_INTENSITY, 0);\n"
    "            PokemonSprite_StartFade(sprite, 0, 16, 1, RGB(31, 31, 31));\n"
    "            BrightnessController_StartTransition(8, -6, 0, screenPlanes, BRIGHTNESS_MAIN_SCREEN);\n"
    "            data->state++;\n"
    "            break;\n"
    "        case 1:\n"
    "            if (data->frame < 12) {\n"
    "                PokemonSprite_AddAttribute(sprite, MON_SPRITE_SCALE_X, -8);\n"
    "                PokemonSprite_AddAttribute(sprite, MON_SPRITE_SCALE_Y, -14);\n"
    "                PokemonSprite_SetAttribute(sprite, MON_SPRITE_Y_OFFSET, data->baseYOffset + data->frame / 2);\n"
    "                if ((data->frame & 3) == 3) {\n"
    "                    PokemonSprite_AddAttribute(sprite, MON_SPRITE_MOSAIC_INTENSITY, 1);\n"
    "                }\n"
    "                data->frame++;\n"
    "            } else if (PokemonSprite_IsFadeActive(sprite) == FALSE &&\n"
    "                BrightnessController_IsTransitionComplete(BRIGHTNESS_MAIN_SCREEN) == TRUE) {\n"
    "                PokemonSprite_SetAttribute(sprite, MON_SPRITE_HIDE, TRUE);\n"
    "                data->frame = 0;\n"
    "                data->state++;\n"
    "            }\n"
    "            break;\n"
    "        case 2:\n"
    "            if (data->frame < 8) {\n"
    "                data->frame++;\n"
    "            } else {\n"
    "                data->state++;\n"
    "            }\n"
    "            break;\n"
    "        default:\n"
    "            BattleController_EmitClearCommand(data->battleSys, data->battler, data->command);\n"
    "            Heap_Free(data);\n"
    "            SysTask_Done(task);\n"
    "            break;\n"
    "        }\n"
    "        return;\n"
    "    }\n\n"
    "    switch (data->state) {\n"
    "    case 0:\n"
    "        PokemonSprite_SetAttribute(sprite, MON_SPRITE_SCALE_X, 0x220);\n"
    "        PokemonSprite_SetAttribute(sprite, MON_SPRITE_SCALE_Y, 0x220);\n"
    "        PokemonSprite_SetAttribute(sprite, MON_SPRITE_Y_OFFSET, data->baseYOffset - 16);\n"
    "        PokemonSprite_SetAttribute(sprite, MON_SPRITE_MOSAIC_INTENSITY, 3);\n"
    "        PokemonSprite_StartFade(sprite, 16, 0, 1, RGB(31, 31, 31));\n"
    "        PokemonSprite_SetAttribute(sprite, MON_SPRITE_HIDE, FALSE);\n"
    "        BrightnessController_StartTransition(3, 16, -6, screenPlanes, BRIGHTNESS_MAIN_SCREEN);\n"
    "        data->state++;\n"
    "        break;\n"
    "    case 1:\n"
    "        if (BrightnessController_IsTransitionComplete(BRIGHTNESS_MAIN_SCREEN) == TRUE) {\n"
    "            Sound_PlayPokemonCry(data->species, data->form);\n"
    "            BrightnessController_StartTransition(8, 0, 16, screenPlanes, BRIGHTNESS_MAIN_SCREEN);\n"
    "            data->frame = 0;\n"
    "            data->state++;\n"
    "        }\n"
    "        break;\n"
    "    case 2:\n"
    "        if (data->frame < 12) {\n"
    "            PokemonSprite_AddAttribute(sprite, MON_SPRITE_SCALE_X, -24);\n"
    "            PokemonSprite_AddAttribute(sprite, MON_SPRITE_SCALE_Y, -24);\n"
    "            PokemonSprite_SetAttribute(sprite, MON_SPRITE_Y_OFFSET, data->baseYOffset - 16 + (data->frame * 4 / 3));\n"
    "            if ((data->frame & 3) == 3) {\n"
    "                PokemonSprite_AddAttribute(sprite, MON_SPRITE_MOSAIC_INTENSITY, -1);\n"
    "            }\n"
    "            data->frame++;\n"
    "        } else if (PokemonSprite_IsFadeActive(sprite) == FALSE &&\n"
    "            BrightnessController_IsTransitionComplete(BRIGHTNESS_MAIN_SCREEN) == TRUE) {\n"
    "            PokemonSprite_SetAttribute(sprite, MON_SPRITE_SCALE_X, 0xE0);\n"
    "            PokemonSprite_SetAttribute(sprite, MON_SPRITE_SCALE_Y, 0xE0);\n"
    "            data->frame = 0;\n"
    "            data->state++;\n"
    "        }\n"
    "        break;\n"
    "    case 3:\n"
    "        if (data->frame < 4) {\n"
    "            PokemonSprite_AddAttribute(sprite, MON_SPRITE_SCALE_X, 12);\n"
    "            PokemonSprite_AddAttribute(sprite, MON_SPRITE_SCALE_Y, 12);\n"
    "            data->frame++;\n"
    "        } else {\n"
    "            data->frame = 0;\n"
    "            data->state++;\n"
    "        }\n"
    "        break;\n"
    "    case 4:\n"
    "        if (data->frame < 3) {\n"
    "            PokemonSprite_AddAttribute(sprite, MON_SPRITE_SCALE_X, -5);\n"
    "            PokemonSprite_AddAttribute(sprite, MON_SPRITE_SCALE_Y, -5);\n"
    "            data->frame++;\n"
    "        } else if (PokemonSprite_IsFadeActive(sprite) == FALSE &&\n"
    "            BrightnessController_IsTransitionComplete(BRIGHTNESS_MAIN_SCREEN) == TRUE) {\n"
    "            PokemonSprite_SetAttribute(sprite, MON_SPRITE_SCALE_X, 0x100);\n"
    "            PokemonSprite_SetAttribute(sprite, MON_SPRITE_SCALE_Y, 0x100);\n"
    "            PokemonSprite_SetAttribute(sprite, MON_SPRITE_Y_OFFSET, data->baseYOffset);\n"
    "            PokemonSprite_SetAttribute(sprite, MON_SPRITE_MOSAIC_INTENSITY, 0);\n"
    "            PokemonSprite_SetAttribute(sprite, MON_SPRITE_HIDE, FALSE);\n"
    "            PokemonSprite_ClearFade(sprite);\n"
    "            data->state++;\n"
    "        }\n"
    "        break;\n"
    "    default:\n"
    "        BattleController_EmitClearCommand(data->battleSys, data->battler, data->command);\n"
    "        Heap_Free(data);\n"
    "        SysTask_Done(task);\n"
    "        break;\n"
    "    }\n"
    "}\n\n"
    "static void ShowPartyGaugeTask(SysTask *param0, void *param1)\n",
)

# Battle-script opcode 223, appended after End (222).
path = ROOT / "src/battle/battle_script.c"
replace_once(
    path,
    "static BOOL BtlCmd_End(BattleSystem *battleSys, BattleContext *battleCtx);\n",
    "static BOOL BtlCmd_End(BattleSystem *battleSys, BattleContext *battleCtx);\n"
    "static BOOL BtlCmd_AffinePulse(BattleSystem *battleSys, BattleContext *battleCtx);\n",
)
replace_once(
    path,
    "    BtlCmd_RefreshMonData,\n    BtlCmd_End\n};",
    "    BtlCmd_RefreshMonData,\n    BtlCmd_End,\n    BtlCmd_AffinePulse\n};",
)
replace_once(
    path,
    "static BOOL BtlCmd_ChangeForm(BattleSystem *battleSys, BattleContext *battleCtx)\n",
    "static BOOL BtlCmd_AffinePulse(BattleSystem *battleSys, BattleContext *battleCtx)\n"
    "{\n"
    "    BattleScript_Iter(battleCtx, 1);\n"
    "    int inBattler = BattleScript_Read(battleCtx);\n"
    "    int stage = BattleScript_Read(battleCtx);\n"
    "    int battler = BattleScript_Battler(battleSys, battleCtx, inBattler);\n\n"
    "    BattleController_EmitAffinePulse(battleSys, battler, stage);\n"
    "    return FALSE;\n"
    "}\n\n"
    "static BOOL BtlCmd_ChangeForm(BattleSystem *battleSys, BattleContext *battleCtx)\n",
)

# Assembler macro.
path = ROOT / "asm/macros/btlcmd.inc"
replace_once(
    path,
    "    .macro End\n    .long 222\n    .endm\n",
    "    .macro End\n    .long 222\n    .endm\n\n"
    "    .macro AffinePulse battler, stage\n"
    "    .long 223\n"
    "    .long \\battler\n"
    "    .long \\stage\n"
    "    .endm\n",
)

# Production Mega sequence: conceal before form reload; reveal afterward.
path = ROOT / "res/battle/scripts/subscripts/subscript_mega_evolution.s"
replace_once(
    path,
    "    // Flash and mosaic pixelate\n"
    "    PlaySound BTLSCR_MSG_TEMP, 1980\n"
    "    SetMosaic BTLSCR_MSG_TEMP, 8, 1\n"
    "    Wait\n"
    "    // Swap to mega form sprite\n"
    "    ChangeForm BTLSCR_MSG_TEMP\n"
    "    Wait\n"
    "    // Clear mosaic first — no animations between ChangeForm and SetMosaic 0\n"
    "    PlaySound BTLSCR_MSG_TEMP, 1984\n"
    "    SetMosaic BTLSCR_MSG_TEMP, 0, 1\n"
    "    Wait\n"
    "    // Sparkle effect after sprite is fully loaded\n",
    "    // Affine Pulse charge: dim, whiten, compress, and conceal the base form\n"
    "    PlaySound BTLSCR_MSG_TEMP, 1980\n"
    "    AffinePulse BTLSCR_MSG_TEMP, 0\n"
    "    Wait\n"
    "    // Swap forms only while the sprite is fully concealed\n"
    "    ChangeForm BTLSCR_MSG_TEMP\n"
    "    Wait\n"
    "    // Affine Pulse reveal: flash, elastic overshoot, settle, and restore\n"
    "    PlaySound BTLSCR_MSG_TEMP, 1984\n"
    "    AffinePulse BTLSCR_MSG_TEMP, 1\n"
    "    Wait\n"
    "    // Sparkle effect after the Mega sprite has settled\n",
)

print("Affine Pulse integration applied successfully.")
