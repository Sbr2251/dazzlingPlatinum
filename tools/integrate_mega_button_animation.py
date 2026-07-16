#!/usr/bin/env python3
"""Integrate the armed-state MEGA Energy Border into battle_cursor.c.

The implementation uses the existing move-menu per-frame update path, the MEGA
button's BG tilemap, and two BG palette banks that are unused by the move-menu
NSCR layouts (14 = trail, 15 = head/surge). No OAM objects or heap tasks are
allocated.
"""

from __future__ import annotations

from pathlib import Path

SOURCE = Path("src/battle/battle_cursor.c")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    text = SOURCE.read_text()
    if "MEGA_BORDER_PATH_LENGTH" in text:
        print("Energy Border is already integrated; no changes made.")
        return

    struct_old = """    struct {
        UnkStruct_ov16_0226DEEC *unk_00;
        u8 unk_04;
        u8 unk_05;
        u8 unk_06;
    } unk_6C4;
} UnkStruct_ov16_02268A14_t;"""
    struct_new = """    struct {
        UnkStruct_ov16_0226DEEC *unk_00;
        u8 unk_04;
        u8 unk_05;
        u8 unk_06;
    } unk_6C4;
    u8 megaBorderFrame;
    u8 megaBorderWasActive;
} UnkStruct_ov16_02268A14_t;"""
    text = replace_once(text, struct_old, struct_new, "menu animation state")

    palette_anchor = """static const u16 sMegaButtonPalette_Active[16] = {
    RGB( 0,  0,  0),   //  0: transparent
    RGB(10,  4, 16),   //  1: dark outline
    RGB(14,  6, 20),   //  2: outline 2
    RGB(28, 14, 22),   //  3: fill (warmer pink)
    RGB(30, 16, 24),   //  4: fill
    RGB(31, 18, 26),   //  5: fill
    RGB(31, 22, 28),   //  6: fill
    RGB(31, 26, 30),   //  7: fill bright
    RGB(31, 28, 31),   //  8: fill brightest
    RGB(31, 31, 31),   //  9: highlight (white)
    RGB(20, 10, 18),   // 10: shadow
    RGB(24, 12, 20),   // 11: mid shadow
    RGB(31, 30, 31),   // 12: near-white
    RGB( 8,  3, 12),   // 13: darkest
    RGB(14,  5, 18),   // 14: dark accent
    RGB(31, 31, 31),   // 15: white
};"""
    palette_insert = palette_anchor + """

// Energy Border palette banks. The move-menu NSCR layouts do not use BG
// palette banks 14 or 15, so these banks can highlight individual border tiles
// without changing the MEGA fill, CANCEL, or move-button palettes.
static const u16 sMegaButtonPalette_EnergyTrail[16] = {
    RGB( 0,  0,  0),
    RGB(22, 10, 24), // outline energy
    RGB(28, 16, 29), // secondary outline energy
    RGB(28, 14, 22),
    RGB(30, 16, 24),
    RGB(31, 18, 26),
    RGB(31, 22, 28),
    RGB(31, 26, 30),
    RGB(31, 28, 31),
    RGB(31, 31, 31),
    RGB(28, 14, 24), // border shadow energy
    RGB(31, 18, 27), // border mid-shadow energy
    RGB(31, 30, 31),
    RGB(18,  7, 20), // darkest border energy
    RGB(26, 11, 25), // dark border accent energy
    RGB(31, 31, 31),
};

static const u16 sMegaButtonPalette_EnergyHead[16] = {
    RGB( 0,  0,  0),
    RGB(31, 18, 28), // bright outline energy
    RGB(31, 27, 31), // white-hot secondary outline
    RGB(28, 14, 22),
    RGB(30, 16, 24),
    RGB(31, 18, 26),
    RGB(31, 22, 28),
    RGB(31, 26, 30),
    RGB(31, 28, 31),
    RGB(31, 31, 31),
    RGB(31, 20, 28), // bright border shadow energy
    RGB(31, 25, 30), // bright border mid-shadow energy
    RGB(31, 30, 31),
    RGB(24, 10, 24), // bright darkest-border energy
    RGB(31, 17, 28), // bright dark-accent energy
    RGB(31, 31, 31),
};

#define MEGA_BORDER_BASE_PALETTE 2
#define MEGA_BORDER_TRAIL_PALETTE 14
#define MEGA_BORDER_HEAD_PALETTE 15
#define MEGA_BORDER_PATH_LENGTH 34
#define MEGA_BORDER_STEP_FRAMES 2
#define MEGA_BORDER_TRAVEL_FRAMES (MEGA_BORDER_PATH_LENGTH * MEGA_BORDER_STEP_FRAMES)
#define MEGA_BORDER_SURGE_FRAMES 6
#define MEGA_BORDER_QUIET_FRAMES 10
#define MEGA_BORDER_TOTAL_FRAMES (MEGA_BORDER_TRAVEL_FRAMES + MEGA_BORDER_SURGE_FRAMES + MEGA_BORDER_QUIET_FRAMES)

// Clockwise outer-ring path around the 14 x 5 MEGA button tile rectangle.
static const u8 sMegaBorderPath[MEGA_BORDER_PATH_LENGTH][2] = {
    { 1, 0x13 }, { 2, 0x13 }, { 3, 0x13 }, { 4, 0x13 }, { 5, 0x13 }, { 6, 0x13 }, { 7, 0x13 },
    { 8, 0x13 }, { 9, 0x13 }, { 10, 0x13 }, { 11, 0x13 }, { 12, 0x13 }, { 13, 0x13 }, { 14, 0x13 },
    { 14, 0x14 }, { 14, 0x15 }, { 14, 0x16 }, { 14, 0x17 },
    { 13, 0x17 }, { 12, 0x17 }, { 11, 0x17 }, { 10, 0x17 }, { 9, 0x17 }, { 8, 0x17 },
    { 7, 0x17 }, { 6, 0x17 }, { 5, 0x17 }, { 4, 0x17 }, { 3, 0x17 }, { 2, 0x17 }, { 1, 0x17 },
    { 1, 0x16 }, { 1, 0x15 }, { 1, 0x14 },
};"""
    text = replace_once(text, palette_anchor, palette_insert, "energy palettes and path")

    prototype_old = """static void LoadMegaButtonPalette(UnkStruct_ov16_02268A14 *param0, BOOL isActive);"""
    prototype_new = """static void LoadMegaButtonPalette(UnkStruct_ov16_02268A14 *param0, BOOL isActive);
static void ResetMegaButtonBorder(UnkStruct_ov16_02268A14 *param0);
static void UpdateMegaButtonBorder(UnkStruct_ov16_02268A14 *param0);"""
    text = replace_once(text, prototype_old, prototype_new, "energy function prototypes")

    functions_old = """// Load mega evolution button palette into VRAM BG palette slot 2
static void LoadMegaButtonPalette(UnkStruct_ov16_02268A14 *param0, BOOL isActive)
{
    PaletteData *paletteSys = BattleSystem_PaletteSys(param0->battleSys);
    const u16 *palette = isActive ? sMegaButtonPalette_Active : sMegaButtonPalette_Inactive;
    PaletteData_LoadBuffer(paletteSys, palette, PLTTBUF_SUB_BG, 2 * 16, 0x20);
}

// Sync mega button palette with current megaEvolutionTriggered state
static void UpdateMegaIconState(UnkStruct_ov16_02268A14 *param0)
{
    UnkStruct_ov16_02260C00 *v0 = &param0->unk_1A.val2;
    if (v0->megaEvolutionAvailable) {
        BattleContext *battleCtx = BattleSystem_Context(param0->battleSys);
        int battler = BattleSystem_BattlerOfType(param0->battleSys, param0->unk_66A);
        BOOL isActive = battleCtx->megaEvolutionTriggered[battler];
        LoadMegaButtonPalette(param0, isActive);
    }
}"""
    functions_new = """// Load the MEGA button base palette and the two Energy Border palette banks.
static void LoadMegaButtonPalette(UnkStruct_ov16_02268A14 *param0, BOOL isActive)
{
    PaletteData *paletteSys = BattleSystem_PaletteSys(param0->battleSys);
    const u16 *palette = isActive ? sMegaButtonPalette_Active : sMegaButtonPalette_Inactive;

    PaletteData_LoadBuffer(paletteSys, palette, PLTTBUF_SUB_BG, MEGA_BORDER_BASE_PALETTE * 16, 0x20);

    if (isActive) {
        PaletteData_LoadBuffer(paletteSys, sMegaButtonPalette_EnergyTrail, PLTTBUF_SUB_BG, MEGA_BORDER_TRAIL_PALETTE * 16, 0x20);
        PaletteData_LoadBuffer(paletteSys, sMegaButtonPalette_EnergyHead, PLTTBUF_SUB_BG, MEGA_BORDER_HEAD_PALETTE * 16, 0x20);
    }
}

static void SetMegaButtonBorderPalette(UnkStruct_ov16_02268A14 *param0, int pathIndex, int palette)
{
    BgConfig *bgConfig = BattleSystem_BGL(param0->battleSys);
    int x = sMegaBorderPath[pathIndex][0];
    int y = sMegaBorderPath[pathIndex][1];

    Bg_ChangeTilemapRectPalette(bgConfig, 4, x, y, 1, 1, palette);
}

static void ResetMegaButtonBorder(UnkStruct_ov16_02268A14 *param0)
{
    BgConfig *bgConfig = BattleSystem_BGL(param0->battleSys);
    int i;

    for (i = 0; i < MEGA_BORDER_PATH_LENGTH; i++) {
        SetMegaButtonBorderPalette(param0, i, MEGA_BORDER_BASE_PALETTE);
    }

    Bg_ScheduleTilemapTransfer(bgConfig, 4);
}

static void DrawMegaButtonBorderFrame(UnkStruct_ov16_02268A14 *param0, int frame)
{
    BgConfig *bgConfig = BattleSystem_BGL(param0->battleSys);
    int travelStep;
    int i;

    if (frame < MEGA_BORDER_TRAVEL_FRAMES) {
        if ((frame % MEGA_BORDER_STEP_FRAMES) != 0) {
            return;
        }

        travelStep = frame / MEGA_BORDER_STEP_FRAMES;
        for (i = 0; i < MEGA_BORDER_PATH_LENGTH; i++) {
            SetMegaButtonBorderPalette(param0, i, MEGA_BORDER_BASE_PALETTE);
        }

        SetMegaButtonBorderPalette(param0, (travelStep + MEGA_BORDER_PATH_LENGTH - 2) % MEGA_BORDER_PATH_LENGTH, MEGA_BORDER_TRAIL_PALETTE);
        SetMegaButtonBorderPalette(param0, (travelStep + MEGA_BORDER_PATH_LENGTH - 1) % MEGA_BORDER_PATH_LENGTH, MEGA_BORDER_TRAIL_PALETTE);
        SetMegaButtonBorderPalette(param0, travelStep, MEGA_BORDER_HEAD_PALETTE);
        Bg_ScheduleTilemapTransfer(bgConfig, 4);
        return;
    }

    if (frame == MEGA_BORDER_TRAVEL_FRAMES) {
        for (i = 0; i < MEGA_BORDER_PATH_LENGTH; i++) {
            SetMegaButtonBorderPalette(param0, i, MEGA_BORDER_TRAIL_PALETTE);
        }
        SetMegaButtonBorderPalette(param0, 0, MEGA_BORDER_HEAD_PALETTE);
        SetMegaButtonBorderPalette(param0, 13, MEGA_BORDER_HEAD_PALETTE);
        SetMegaButtonBorderPalette(param0, 17, MEGA_BORDER_HEAD_PALETTE);
        SetMegaButtonBorderPalette(param0, 30, MEGA_BORDER_HEAD_PALETTE);
        Bg_ScheduleTilemapTransfer(bgConfig, 4);
    } else if (frame == MEGA_BORDER_TRAVEL_FRAMES + MEGA_BORDER_SURGE_FRAMES) {
        ResetMegaButtonBorder(param0);
    }
}

static void UpdateMegaButtonBorder(UnkStruct_ov16_02268A14 *param0)
{
    DrawMegaButtonBorderFrame(param0, param0->megaBorderFrame);

    param0->megaBorderFrame++;
    if (param0->megaBorderFrame >= MEGA_BORDER_TOTAL_FRAMES) {
        param0->megaBorderFrame = 0;
    }
}

// Sync the MEGA selected state and advance the Energy Border while menu 11 is active.
static void UpdateMegaIconState(UnkStruct_ov16_02268A14 *param0)
{
    UnkStruct_ov16_02260C00 *v0 = &param0->unk_1A.val2;

    if (v0->megaEvolutionAvailable) {
        BattleContext *battleCtx = BattleSystem_Context(param0->battleSys);
        int battler = BattleSystem_BattlerOfType(param0->battleSys, param0->unk_66A);
        BOOL isActive = battleCtx->megaEvolutionTriggered[battler];

        if (isActive) {
            if (param0->megaBorderWasActive == FALSE) {
                LoadMegaButtonPalette(param0, TRUE);
                param0->megaBorderFrame = 0;
                param0->megaBorderWasActive = TRUE;
            }
            UpdateMegaButtonBorder(param0);
        } else if (param0->megaBorderWasActive) {
            ResetMegaButtonBorder(param0);
            LoadMegaButtonPalette(param0, FALSE);
            param0->megaBorderFrame = 0;
            param0->megaBorderWasActive = FALSE;
        }
    }
}"""
    text = replace_once(text, functions_old, functions_new, "energy border functions")

    toggle_old = """            LoadMegaButtonPalette(param0, battleCtx->megaEvolutionTriggered[battler]);

            Sound_PlayEffect(SEQ_SE_CONFIRM);"""
    toggle_new = """            UpdateMegaIconState(param0);

            Sound_PlayEffect(SEQ_SE_CONFIRM);"""
    toggle_count = text.count(toggle_old)
    if toggle_count != 2:
        raise RuntimeError(f"toggle hooks: expected two matches, found {toggle_count}")
    text = text.replace(toggle_old, toggle_new)

    SOURCE.write_text(text)
    print("Integrated MEGA Energy Border into src/battle/battle_cursor.c")


if __name__ == "__main__":
    main()
