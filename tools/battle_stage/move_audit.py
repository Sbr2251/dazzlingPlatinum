#!/usr/bin/env python3
"""Static move animation audit for the 3D battle stage (chunk 5).

WIP skeleton: C helpers only.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ANIM_SRC = ROOT / "src" / "battle_anim"

FUNC_DEF_RE = re.compile(
    r"^(?:static\s+)?(?:inline\s+)?(?:const\s+)?[A-Za-z_][\w \t\*]*?\b([A-Za-z_]\w*)\s*\(([^;{}]*)\)\s*\{",
    re.M,
)


def strip_c_comments(text):
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def parse_c_functions(path):
    """Return {name: (body_text, line)} for every function defined in path."""
    text = strip_c_comments(path.read_text(encoding="utf-8", errors="replace"))
    funcs = {}
    for m in FUNC_DEF_RE.finditer(text):
        name = m.group(1)
        if name in ("if", "for", "while", "switch", "return", "sizeof"):
            continue
        start = m.end() - 1
        depth = 0
        i = start
        while i < len(text):
            c = text[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        body = text[start:i + 1]
        line = text.count("\n", 0, m.start()) + 1
        funcs[name] = (body, path.name, line)
    return funcs


def load_anim_c():
    funcs = {}
    for path in sorted(ANIM_SRC.glob("*.c")):
        funcs.update(parse_c_functions(path))
    return funcs


# --- C scan: raw evidence per function ------------------------------------

_SET = r"PokemonSprite_(?:Set|Add)Attribute\([^;]*"
C_EVIDENCE = [
    ("sprite_xy", re.compile(_SET + r"MON_SPRITE_(?:X|Y)_(?:CENTER|OFFSET)|BattleAnimUtil_SetPokemonSpriteAnchoredPosition")),
    ("sprite_scale_rot", re.compile(_SET + r"MON_SPRITE_(?:SCALE|ROTATION)_")),
    ("partial_draw", re.compile(_SET + r"MON_SPRITE_(?:PARTIAL_DRAW|DRAW_)|PokemonSprite_SetPartialDraw")),
    ("sprite_fade_tint", re.compile(_SET + r"MON_SPRITE_(?:FADE_|DIFFUSE|AMBIENT|ALPHA|MOSAIC)|PokemonSprite_StartFade")),
    ("hblank_wave", re.compile(r"\b(?:Custom)?BgScrollContext_New|BufferManager_New|HBlank")),
    ("window", re.compile(r"\bG2_SetWnd\w*|GX_SetVisibleWnd|BattleAnimUtil_SetBackgroundWindowMask")),
    ("sprite_bg_blend", re.compile(r"\bG2_SetBlendAlpha|G2_ChangeBlendAlpha|BattleAnimUtil_Set\w*Blending|AlphaFadeContext_Init|BattleAnimSystem_SetDefaultAlphaBlending")),
    ("brightness", re.compile(r"\bG2_SetBlendBrightness|G2_ChangeBlendBrightness|BrightnessController_StartTransition")),
    ("palette", re.compile(r"\bPaletteData_(?:StartFade|Blend\w*|LoadBuffer\w*|FillBufferRange)|PaletteFadeContext_New|MakeBgPalsGrayscale")),
    ("bg_op", re.compile(r"\bBg_(?:SetOffset|ScheduleScroll|SetPriority|ToggleLayer|ClearTilemap|ClearTilesRange|LoadTiles|LoadTilemapBuffer|FillTilemapRect|CopyTilemapBufferToVRAM|ScheduleTilemapTransfer|GetCharPtr)|Graphics_Load\w*ToBgLayer")),
    ("oam_copy_use", re.compile(r"pokemonSprites\[|BattleAnimUtil_GetPokemonSprites")),
]
LAYER_WORDS = [
    ("BG2", re.compile(r"BATTLE_ANIM_BG_BASE|BATTLE_BG_BASE|BG_LAYER_MAIN_2|PLANEMASK_BG2")),
    ("BG3", re.compile(r"BATTLE_ANIM_BG_EFFECT|BATTLE_BG_EFFECT|BG_LAYER_MAIN_3|PLANEMASK_BG3")),
    ("BG0", re.compile(r"BATTLE_BG_3D|BG_LAYER_MAIN_0|PLANEMASK_BG0")),
    ("BG1", re.compile(r"BATTLE_ANIM_BG_WINDOW|BATTLE_BG_WINDOW|BG_LAYER_MAIN_1|PLANEMASK_BG1")),
]


def c_evidence(body):
    """Evidence tags in one function body; layered tags get a /BGn suffix per statement."""
    found = set()
    for stmt in re.split(r"[;{}]", body):
        for tag, rx in C_EVIDENCE:
            if not rx.search(stmt):
                continue
            if tag in ("hblank_wave", "bg_op", "palette", "window", "sprite_bg_blend"):
                layers = [ln for ln, lrx in LAYER_WORDS if lrx.search(stmt)]
                if layers:
                    for ln in layers:
                        found.add(f"{tag}/{ln}")
                    continue
            found.add(tag)
    return found


CALL_STOP = {
    # hubs that would drag unrelated effects into every func
    "BattleAnimSystem_EndAnimTask", "BattleAnimSystem_StartAnimTask", "BattleAnimSystem_StartAnimTaskEx",
}


def scan_func_evidence(funcs, root):
    names = set(funcs)
    ident = re.compile(r"\b([A-Za-z_]\w*)\b")
    seen, stack, ev = set(), [root], set()
    while stack:
        name = stack.pop()
        if name in seen or name not in funcs:
            continue
        seen.add(name)
        body = funcs[name][0]
        ev |= c_evidence(body)
        for ref in set(ident.findall(body)):
            if ref in names and ref not in seen and ref not in CALL_STOP:
                stack.append(ref)
    return ev, seen


def script_func_table():
    text = strip_c_comments((ANIM_SRC / "script_func_tables.c").read_text())
    m = re.search(r"sBattleAnimScriptFuncs\[\]\s*=\s*\{(.*?)\};", text, re.S)
    funcs = [x.strip() for x in m.group(1).split(",") if x.strip()]
    m = re.search(r"sBattleAnimScriptSpriteFuncs\[\]\s*=\s*\{(.*?)\};", text, re.S)
    sprite_funcs = [x.strip() for x in m.group(1).split(",") if x.strip()]
    return funcs, sprite_funcs


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--scan-c":
        funcs = load_anim_c()
        table, sprite_table = script_func_table()
        for kind, tab in (("func", table), ("sprite", sprite_table)):
            for i, name in enumerate(tab):
                ev, seen = scan_func_evidence(funcs, name)
                print(f"{kind} {i:2d} {name}: {' '.join(sorted(ev))}")
        sys.exit(0)
    if len(sys.argv) > 2 and sys.argv[1] == "--show-func":
        funcs = load_anim_c()
        for name in sys.argv[2:]:
            body, fname, line = funcs[name]
            print(f"== {name} ({fname}:{line})")
            print(body)
