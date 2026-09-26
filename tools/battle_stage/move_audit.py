#!/usr/bin/env python3
"""Static move animation audit for the 3D battle stage (chunk 5).

Scans every res/battle/moves/*/anim.s (following Call/Jump/branches, and labels in
res/battle/scripts/* when a label is not local), maps opcodes and script funcs to the
mechanism tags of docs/living_battle_stage/compat.md section 1, and writes
docs/living_battle_stage/move_audit.json and move_audit.md.

The func -> tag tables below were built by hand from the C sources (src/battle_anim/*.c);
`--scan-c` prints the raw C evidence they were reviewed against. Judgement (risk, fix,
notes) lives in OVERRIDES / CHUNK6, so a rerun gives the same files.

No emulator, no build. Usage:
    python3 tools/battle_stage/move_audit.py            # write json + md
    python3 tools/battle_stage/move_audit.py --check    # exit 1 if the files are stale
    python3 tools/battle_stage/move_audit.py --scan-c   # raw C evidence per func
"""

import json
import re
import sys
from collections import Counter, defaultdict
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


# --- hand-curated tables (reviewed against --scan-c and the C sources) --------

MECHANISMS = [
    "sprite_xy", "sprite_scale_rot", "partial_draw", "bg2_copy", "oam_copy", "hblank_wave",
    "window", "sprite_bg_blend", "brightness", "switch_bg", "bg2_effect", "particles",
    "sprite_fade_tint",
]
RISKS = ["high", "medium", "low"]


def F(tags, suppress=(), wave=None, note=""):
    """wave: BG layer of a per-line (HBlank) scroll, which decides F5."""
    return {"tags": list(tags), "suppress": list(suppress), "wave": wave, "note": note}


XY, SR, PD, TINT = "sprite_xy", "sprite_scale_rot", "partial_draw", "sprite_fade_tint"
OAM, BLEND, WIN = "oam_copy", "sprite_bg_blend", "window"

# CallFunc id -> tags. Blends here are OBJ-first alpha (BattleAnimUtil_SetSpriteBgBlending:
# 1st NONE, 2nd BG3|BG0) unless noted; no anim code makes BG0 a 1st target.
FUNC_TAGS = {
    0: F([]), 1: F([]), 2: F([]), 3: F([]),
    4: F([SR]),                                   # RotateMon
    5: F([XY, SR, TINT]),                         # Strength
    6: F([XY, SR]),                               # BulkUp
    7: F([OAM, BLEND, TINT]),                     # DoubleTeam
    8: F([OAM, BLEND, XY]),                       # QuickAttack
    9: F([XY, SR]), 10: F([XY, SR]),              # DrillPeck, Submission
    11: F([OAM, BLEND, XY]),                      # Confusion
    12: F(["bg2_copy", "hblank_wave", BLEND], wave="BG2",
          note="AcidArmor puts BG2 above BG0 itself"),
    13: F([SR, TINT]),                            # Growth
    14: F([XY, SR]), 15: F([XY, SR]),             # Meditate, Teleport
    16: F([TINT, "switch_bg"], note="Flash fades the backdrop palette (the arena follows it)"),
    17: F([OAM, BLEND]),                          # NightShadeAttacker
    18: F([OAM, TINT, XY]),                       # NightShadeDefender
    19: F([XY, SR]),                              # Splash
    20: F(["bg2_copy", "hblank_wave", BLEND, TINT], wave="BG2",
          note="Spite puts BG2 above BG0 itself"),
    21: F([WIN, OAM, TINT], note="Harden: OBJ window drops BG0 inside the copy's silhouette"),
    22: F([OAM, PD, BLEND]),                      # Minimize
    23: F([OAM, BLEND]),                          # FaintAttack
    24: F([XY], note="Earthquake shakes BG3 (offset) and fades the backdrop palette"),
    25: F([XY, SR]),                              # PlayfulHops
    26: F([OAM, BLEND]),                          # Nightmare
    27: F([XY, SR]),                              # Flail
    28: F([XY], note="Magnitude shakes BG3 (offset)"),
    29: F([XY]), 30: F([XY]),                     # Return, VitalThrow
    31: F([XY, SR]),                              # Swagger
    32: F([OAM, BLEND, TINT]),                    # Memento
    33: F(["switch_bg"], note="FadeBg: backdrop palette fade, the arena follows it"),
    34: F([TINT]),                                # FadeBattlerSprite
    35: F([OAM, BLEND, SR]),                      # ScalePokemonSprite
    36: F([XY]),                                  # Shake (BG3 too when targets has BATTLE_ANIM_BACKGROUND)
    37: F(["bg2_copy", "hblank_wave"], wave="BG2",
          note="Extrasensory puts BG2 above BG0 itself"),
    38: F([OAM, BLEND]),                          # AlphaFadePokemonSprite
    39: F([OAM]),                                 # OdorSleuth
    40: F([]), 50: F([]),                         # HideBattler, BlinkAttacker (visibility only)
    41: F([WIN, "switch_bg"],
          note="FakeOutCurtain: WIN0 hides BG3 outside a shrinking rect"),
    42: F([XY, SR]), 43: F([XY, SR]),             # ScaleBattlerSprite, FakeOut
    44: F(["bg2_effect", BLEND], suppress=["bg2_effect"],
          note="ScrollCustomBg: picture on BG2 blended over BG0|BG3"),
    45: F(["bg2_effect", BLEND], suppress=["bg2_effect"],
          note="MuddyWater: picture on BG2 blended over BG0|BG3"),
    46: F([XY]), 47: F([XY]), 48: F([XY]),         # Megahorn*
    49: F([BLEND]),                               # Surf
    51: F([XY]), 52: F([XY]),                     # MoveBattlerX*
    53: F([XY, SR]), 54: F([XY, SR]),             # ShakeAndScaleAttacker*
    55: F([WIN, "bg2_effect", "hblank_wave", OAM, BLEND], wave="BG2",
          note="Camouflage: base picture on BG2 inside an OBJ window, lifted above BG0 (chunk 6)"),
    56: F([WIN, "bg2_effect", OAM], suppress=["bg2_effect"],
          note="Superpower: base picture on BG2 under BG0 inside an OBJ window"),
    57: F([XY]),                                  # MoveBattler
    58: F([OAM]),                                 # Mimic
    59: F([OAM, BLEND, TINT, XY]),                # ShadowPunch
    60: F([XY]), 61: F([XY]), 62: F([XY]),         # Revolve/OffScreen/DefaultPos
    63: F([TINT]),                                # FadePokemonSprite
    64: F([PD, XY, SR]),                          # BattlerPartialDrawTest
    65: F(["particles"]), 66: F(["particles"]),   # MoveEmitter*
    67: F([PD, XY, SR]),                          # BattlerPartialDraw
    68: F([]),                                    # ShakeBg: layer from its target arg
    69: F([OAM, TINT], note="Pixelate: OBJ mosaic on an OAM copy"),
    70: F([OAM, BLEND, TINT]),                    # RolePlay
    71: F([XY]),                                  # Snatch
    72: F(["particles"]), 73: F(["particles"]),   # RevolveEmitter, MoveEmitterViewportTop
    74: F(["switch_bg"], note="SetBgGrayscale: backdrop palette, the arena follows it"),
    75: F([WIN], note="WIN0 hides OBJ in a rect; every BG stays on"),
    76: F(["hblank_wave", "switch_bg"], wave="BG3", note="ScrollSwitchedBg: per-line BG3 wave"),
    77: F([XY]),                                  # MoveBattlerOnOrOffScreen
    78: F([OAM]),                                 # RenderPokemonSprites
    79: F([WIN, PD, TINT], note="Sketch: BG2 copy above BG0, revealed by WIN0"),
    80: F([WIN, "bg2_effect", OAM, BLEND], note="stat change: BG2 picture only inside the OBJ window"),
    81: F([WIN, "bg2_effect", OAM, BLEND], note="stat change: BG2 picture only inside the OBJ window"),
    82: F([WIN, "bg2_effect", OAM, BLEND], note="stat change: BG2 picture only inside the OBJ window"),
    83: F([WIN, "bg2_effect", OAM, BLEND], note="stat change: BG2 picture only inside the OBJ window"),
    84: F([BLEND]),                               # KeepTranslucent
    85: F([]), 86: F([]),                         # SkipSoundEffectWait, MegaEvolutionCue
}
WINDOW_FUNCS = sorted(k for k, v in FUNC_TAGS.items() if WIN in v["tags"])

# AddSpriteWithFunc funcID -> tags (sBattleAnimScriptSpriteFuncs). These move 2D effect
# sprites; tags only where they also touch a mon (PokemonSprite_*) or blend/brighten.
SPRITE_FUNC_TAGS = {
    1: [BLEND], 2: [BLEND], 3: [BLEND, XY, SR], 5: [XY], 6: [XY], 7: [BLEND, SR],
    8: [BLEND, TINT], 9: [BLEND, TINT], 11: ["brightness", BLEND], 12: [XY, SR], 13: [XY, SR],
    14: [XY], 15: [BLEND], 18: [BLEND], 19: [BLEND], 20: [BLEND], 21: [BLEND], 23: [BLEND],
    28: [BLEND], 31: [BLEND], 32: [BLEND],
}

# Script opcodes (asm/macros/btlanimcmd.inc) -> (tags, suppress).
OPCODE_TAGS = {
    "SwitchBg": (["switch_bg"], ["bg_switch"]),
    "SwitchBgEx": (["switch_bg"], ["bg_switch"]),
    "RestoreBg": (["switch_bg"], ["bg_switch"]),
    "SetBg": (["switch_bg"], ["bg_switch"]),
    "LoadPokemonSpriteIntoBg": (["bg2_copy"], ["bg2_effect"]),
    "AddPokemonSprite": ([OAM], []),
    "BtlAnimCmd_082": ([OAM], []),
    "BtlAnimCmd_083": ([OAM], []),
    "BtlAnimCmd_068": ([XY], []),
    "BtlAnimCmd_069": ([XY], []),
    "CreateEmitter": (["particles"], []),
    "CreateEmitterEx": (["particles"], []),
    "CreateEmitterForMove": (["particles"], []),
    "CreateEmitterForFriendlyFire": (["particles"], []),
}

# Label arguments per control-flow op. JumpIfContest targets are contest-only paths
# (never on the stage), so they are not followed.
BRANCH_ARGS = {
    "Call": [0], "Jump": [0], "BtlAnimCmd_013": [0, 1], "BtlAnimCmd_014": [0, 1],
    "BtlAnimCmd_033": [0], "JumpIfEqual": [2], "JumpIfBattlerSide": [1, 2],
    "JumpIfWeather": [0, 1, 2, 3, 4], "JumpIfFriendlyFire": [0],
}
FLOW_STOP = {"End", "Jump", "Return"}

# --- judgement --------------------------------------------------------------

# name -> {"risk", "fix", "notes"}; any key present replaces the rule-based value.
OVERRIDES = {
    "FAKE_OUT": {"risk": "high", "fix": ["F3"],
                 "notes": "chunk 6: the stage draws the curtain in 3D, over the arena and under the mons (F3 option c)"},
    "SUPERPOWER": {"fix": ["F3", "F6"],
                   "notes": "chunk 6: no silhouette window with the arena up (F3 option a); SwitchBg still fades (F6)"},
    "CAMOUFLAGE": {"fix": ["F1", "F3"],
                   "notes": "chunk 6: BG2 picture + BG2 wave lifted above BG0 in the OBJ window (F1, F3 option c)"},
    "NONE": {"risk": "medium",
             "notes": "MOVE_NONE placeholder (a Sketch copy), never played in battle; see SKETCH"},
    "HARDEN": {"notes": "StatChangeUp: BG2 picture only inside the OBJ window; F3 option a"},
    "SKETCH": {"notes": "BG2 copy lifted above BG0 by the func, WIN0 reveal keeps BG0 on; F3 option a"},
    "EARTHQUAKE": {"notes": "BG3 shake + backdrop fade; chunk 6: the stage camera mirrors the BG3 shake"},
    "MAGNITUDE": {"notes": "BG3 shake; chunk 6: the stage camera mirrors the BG3 shake"},
}

CHUNK6 = {
    "EARTHQUAKE": "shake the stage camera instead of BG3",
    "MAGNITUDE": "shake the stage camera instead of BG3",
    "DIG": "open the ground instead of clipping the sprite",
    "FAKE_OUT": "curtain drawn over BG3 only; done: a 3D curtain on the stage (redo/silhouette.json)",
    "SUPERPOWER": "BG2 picture in the mon silhouette; done: window skipped with the arena up (redo/silhouette.json)",
    "CAMOUFLAGE": "BG2 picture and wave in the silhouette; done: BG2 lifted above BG0 (redo/silhouette.json)",
    "MUDDY_WATER": "full-screen BG2 picture; a 3D water plane would fit",
    "SURF": "big wave; a 3D water plane would fit",
}

# F3 decisions per window func, written to the md: (func id, label, mask, option, why).
F3_DECISIONS = [
    (21, "Harden", "OBJ window: inside = WINDOW|OBJ, outside = all", "a",
     "only the silhouette loses BG0 and the OAM copy covers it; keep the arena, tint the copy (F2)"),
    (41, "FakeOutCurtain", "WIN0: BG3 only inside a shrinking rect", "c",
     "chunk 6: with the arena up the window stays off and BattleStage_SetCurtain draws the bars in 3D, "
     "in the backdrop colour, over the arena and the shadows and under the mons; the BG palette fade "
     "whitens the arena textures as it whitens BG3. Classic WIN0 when the arena is hidden"),
    (55, "Camouflage", "OBJ window: inside adds BG2, BG2 at BG3 priority", "c",
     "chunk 6: BattleAnimSystem_LiftBaseBgOverStage puts BG2 above BG0 (the F1 lift) and the OBJ "
     "window inside also shows BG3, which the opaque picture covers, so F3 doesn't fire; "
     "dropped before UnloadBaseBg. Option b when the arena is hidden"),
    (56, "Superpower", "OBJ window: inside adds BG2, BG2 at BG3 priority", "a",
     "chunk 6: the silhouette only cuts BG3 for one frame, unseen under the arena, so the window "
     "stays off with the arena up; the SwitchBg picture that follows still fades (F6)"),
    (75, "SetPokemonSpritePriority / DarkVoid", "WIN0: inside BG0-3 without OBJ", "a",
     "only OBJ is hidden and BG0 is already in both regions; nothing to change"),
    (79, "Sketch", "WIN0 reveal of a BG2 copy placed above BG0", "a",
     "BG0 is in both regions; BG2 is above BG0 once the func runs"),
    (80, "StatChangeUp/Down/Heal/Metal", "OBJ window: inside = BG1|OBJ|BG2, outside has BG0", "a",
     "BG2 picture only in the silhouette, which the OAM copy fills; tint the copy (F2)"),
]


def judge(mechs, sup, waves, has_picture_bg2):
    fix = set()
    if "bg_switch" in sup:
        fix.add("F6")
    if "bg2_copy" in mechs:
        fix |= {"F1", "F2"}
    if "bg2_effect" in sup and has_picture_bg2:
        fix.add("F6")
    if OAM in mechs:
        fix.add("F2")
    if WIN in mechs:
        fix.add("F3")
    if BLEND in mechs:
        fix.add("F4")
    if "BG3" in waves or "BG0" in waves:
        fix.add("F5")
    if sup:
        risk = "high"
    elif mechs & {WIN, "hblank_wave", BLEND, "brightness", OAM, "bg2_effect", "bg2_copy", "switch_bg"}:
        risk = "medium"
    else:
        risk = "low"
    return risk, sorted(fix)


# --- parsing ------------------------------------------------------------------

def load_moves():
    lines = (ROOT / "generated" / "moves.txt").read_text().split("\n")
    moves = []
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith("MOVE_"):
            d = "0000" if line == "MOVE_NONE" else line[len("MOVE_"):].lower()
            moves.append((i, line[len("MOVE_"):], d))
    return moves


def load_func_macros():
    """Func_* macro name -> CallFunc id (asm/macros/btlanimfunc.inc)."""
    text = (ROOT / "asm" / "macros" / "btlanimfunc.inc").read_text()
    out = {}
    for m in re.finditer(r"\.macro\s+(Func_\w+)[^\n]*\n\s*CallFunc\s+(\d+)", text):
        out[m.group(1)] = int(m.group(2))
    return out


def split_args(rest):
    return [a.strip() for a in rest.split(",")] if rest.strip() else []


def parse_script(path):
    instrs, labels = [], {}
    for n, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").split("\n"), 1):
        line = re.sub(r"//.*|@.*|;.*", "", raw).strip()
        if not line or line.startswith(("#", ".")):
            continue
        m = re.match(r"^(\w+):\s*(.*)$", line)
        if m:
            labels[m.group(1)] = len(instrs)
            line = m.group(2).strip()
            if not line:
                continue
        op, _, rest = line.partition(" ")
        instrs.append((op, split_args(rest), n))
    return instrs, labels


_GLOBAL_LABELS = None


def global_labels():
    """label -> (path, index) for non-L_n labels defined once in the anim scripts dirs."""
    global _GLOBAL_LABELS
    if _GLOBAL_LABELS is None:
        seen = defaultdict(list)
        base = ROOT / "res" / "battle" / "scripts"
        for sub in ("common_anims", "subscripts"):
            for path in sorted((base / sub).glob("*.s")):
                for lab, idx in parse_script(path)[1].items():
                    seen[lab].append((path, idx))
        _GLOBAL_LABELS = {k: v[0] for k, v in seen.items()
                          if len(v) == 1 and not re.match(r"L_\d+$", k)}
    return _GLOBAL_LABELS


def walk_script(path):
    """Every instruction reachable from the top of path: [(op, args, file, line)], unresolved."""
    files = {path: parse_script(path)}
    stack, seen, out, unresolved = [(path, 0)], set(), [], set()
    while stack:
        f, i = stack.pop()
        instrs, labels = files[f]
        while i < len(instrs) and (f, i) not in seen:
            seen.add((f, i))
            op, args, n = instrs[i]
            out.append((op, args, f, n))
            for k in BRANCH_ARGS.get(op, []):
                if k >= len(args):
                    continue
                lab = args[k]
                if lab in labels:
                    stack.append((f, labels[lab]))
                elif lab in global_labels():
                    gf, gi = global_labels()[lab]
                    if gf not in files:
                        files[gf] = parse_script(gf)
                    stack.append((gf, gi))
                else:
                    unresolved.add(lab)
            if op in FLOW_STOP:
                break
            i += 1
    out.sort(key=lambda x: (str(x[2]), x[3]))
    return out, sorted(unresolved)


def tag_instr(op, args, func_ids):
    """-> (tags, suppress, wave, note, func id or None)"""
    if op in OPCODE_TAGS:
        tags, sup = OPCODE_TAGS[op]
        return tags, sup, None, "", None
    fid = None
    if op == "CallFunc" and args and args[0].isdigit():
        fid, fargs = int(args[0]), args[1:]
    elif op in func_ids:
        fid, fargs = func_ids[op], args
    if fid is not None:
        e = FUNC_TAGS.get(fid, F([], note=f"unknown func {fid}"))
        tags, sup, note = list(e["tags"]), list(e["suppress"]), e["note"]
        # chunk 6 shake: the stage camera mirrors a BG3 shake, so it no longer suppresses
        if fid == 36 and fargs and "BATTLE_ANIM_BACKGROUND" in fargs[-1]:
            note = "Shake also shakes BG3"
        if fid == 68:
            target = fargs[5] if len(fargs) > 5 else "0"
            if target in ("0", "SHAKE_BG_TARGET_EFFECT"):
                note = "ShakeBg on BG3"
            else:
                note = "ShakeBg on BG2"
        return tags, sup, e["wave"], note, fid
    if op == "AddSpriteWithFunc" and len(args) > 1 and args[1].isdigit():
        return SPRITE_FUNC_TAGS.get(int(args[1]), []), [], None, "", None
    return [], [], None, "", None


def audit_move(mid, name, d, func_ids):
    path = ROOT / "res" / "battle" / "moves" / d / "anim.s"
    rec = {"id": mid, "name": name, "dir": d, "mechanisms": [], "suppress": [],
           "fix": [], "risk": "low", "notes": ""}
    info = {"waves": [], "funcs": []}
    if not path.exists():
        rec["notes"] = "no anim.s"
        return rec, info
    instrs, unresolved = walk_script(path)
    mechs, sup, waves, funcs, notes = set(), set(), set(), set(), []
    picture = False
    for op, args, f, n in instrs:
        tags, s, wave, note, fid = tag_instr(op, args, func_ids)
        mechs |= set(tags)
        sup |= set(s)
        if fid is not None:
            funcs.add(fid)
        if wave:
            waves.add(wave)
        if "bg2_effect" in tags:
            picture = True
        if note and note not in notes:
            notes.append(note)
    if waves:
        notes.insert(0, "per-line wave on " + "/".join(sorted(waves)))
    if unresolved:
        notes.append("unresolved labels: " + " ".join(unresolved))
    rec["mechanisms"] = [m for m in MECHANISMS if m in mechs]
    rec["suppress"] = sorted(sup)
    rec["risk"], rec["fix"] = judge(mechs, sup, waves, picture)
    rec["notes"] = "; ".join(notes)
    for k, v in OVERRIDES.get(name, {}).items():
        rec[k] = v
    info = {"waves": sorted(waves), "funcs": sorted(funcs)}
    return rec, info


def run_audit():
    func_ids = load_func_macros()
    recs, infos = [], {}
    for mid, name, d in load_moves():
        rec, info = audit_move(mid, name, d, func_ids)
        recs.append(rec)
        infos[mid] = info
    return recs, infos


# --- output -------------------------------------------------------------------

OUT_DIR = ROOT / "docs" / "living_battle_stage"
KEYS = ["id", "name", "dir", "mechanisms", "suppress", "fix", "risk", "notes"]


def render_json(recs):
    rows = [json.dumps({k: r[k] for k in KEYS}, ensure_ascii=True) for r in recs]
    return "[\n" + ",\n".join(rows) + "\n]\n"


def cell(xs):
    return ", ".join(xs) if xs else "-"


def md_escape(s):
    return s.replace("|", "\\|") if s else ""


def render_md(recs, infos):
    by_name = {r["name"]: r for r in recs}
    risk_n = Counter(r["risk"] for r in recs)
    L = []
    L.append("# Move audit (chunk 5)")
    L.append("")
    L.append("Generated by `tools/battle_stage/move_audit.py` from the move animation scripts and")
    L.append("the C sources; do not edit by hand. Tags, `suppress`, `fix` and `risk` follow")
    L.append("compat.md section 1. Rerun the script after changing a script or the overrides in it.")
    L.append("")
    L.append("## Summary")
    L.append("")
    L.append(f"{len(recs)} moves (ids 0-{recs[-1]['id']}, `generated/moves.txt`). "
             f"Risk: high {risk_n['high']}, medium {risk_n['medium']}, low {risk_n['low']}.")
    sup_n = Counter(s for r in recs for s in r["suppress"])
    fix_n = Counter(f for r in recs for f in r["fix"])
    L.append("")
    L.append("Predicted suppression today: " +
             ", ".join(f"`{k}` {sup_n[k]}" for k in ("bg_switch", "bg2_effect")) + ".")
    L.append("Fixes: " + ", ".join(f"{k} {fix_n[k]}" for k in sorted(fix_n)) + ".")
    L.append("")
    L.append("### By mechanism")
    L.append("")
    L.append("| mechanism | moves | high | medium | low |")
    L.append("|---|---|---|---|---|")
    for m in MECHANISMS:
        rs = [r for r in recs if m in r["mechanisms"]]
        c = Counter(r["risk"] for r in rs)
        L.append(f"| `{m}` | {len(rs)} | {c['high']} | {c['medium']} | {c['low']} |")
    L.append("")
    quiet = [r for r in recs if "switch_bg" in r["mechanisms"] and "bg_switch" not in r["suppress"]]
    L.append(f"`switch_bg` without `bg_switch` ({len(quiet)} moves): backdrop palette fades (FadeBg,")
    L.append("SetBgGrayscale, Flash, Earthquake) or the Fake Out curtain. Nothing is suppressed. The arena's")
    L.append("textures take the faded BG palette and the stage fades its fog and light along (chunk 6")
    L.append("backdrop_fade), so the fades show on the arena; the stage draws Fake Out's curtain in 3D.")
    L.append("`sprite_bg_blend` is always OBJ-first alpha with BG0|BG3 as the 2nd target; no anim code")
    L.append("makes BG0 a 1st target (F4 then means: check the arena stays opaque).")
    L.append("")
    L.append("### By risk")
    L.append("")
    L.append("| risk | moves | meaning |")
    L.append("|---|---|---|")
    L.append(f"| high | {risk_n['high']} | a pop today (a suppression reason fires), or visibly wrong with the arena up |")
    L.append(f"| medium | {risk_n['medium']} | windows, blends, OAM/BG2 copies, BG palette fades: probably fine, unverified |")
    L.append(f"| low | {risk_n['low']} | particles and sprite moves only |")
    L.append("")
    L.append("## High-risk moves")
    L.append("")
    L.append("| id | name | mechanisms | suppress | fix | notes |")
    L.append("|---|---|---|---|---|---|")
    for r in recs:
        if r["risk"] == "high":
            L.append(f"| {r['id']} | {r['name']} | {cell(r['mechanisms'])} | {cell(r['suppress'])} | "
                     f"{cell(r['fix'])} | {md_escape(r['notes'])} |")
    L.append("")
    L.append("## Chunk 6 candidates")
    L.append("")
    L.append("Moves to redo by hand in chunk 6 (stage-side versions); the generic fixes only make")
    L.append("them fade cleanly.")
    L.append("")
    for name in sorted(CHUNK6, key=lambda n: by_name[n]["id"] if n in by_name else 9999):
        r = by_name.get(name)
        mid = r["id"] if r else "?"
        L.append(f"- {mid} {name}: {CHUNK6[name]}")
    L.append("")
    L.append("## F3: window decisions")
    L.append("")
    L.append("Options a and b are compat.md F3's. Option c (chunk 6, moves.md category C): the func")
    L.append("redraws its effect over the arena while the arena shows, and keeps the classic window when")
    L.append("it is hidden. The `BATTLE_STAGE_SUPPRESS_WINDOW` path stays for any other window user.")
    L.append("")
    L.append("| func | mask | option | why | moves |")
    L.append("|---|---|---|---|---|")
    for fid, label, mask, opt, why in F3_DECISIONS:
        ids = (80, 81, 82, 83) if fid == 80 else (fid,)
        users = [r["name"] for r in recs if set(infos[r["id"]]["funcs"]) & set(ids)]
        fids = "80-83" if fid == 80 else str(fid)
        L.append(f"| {label} ({fids}) | {md_escape(mask)} | {opt} | {md_escape(why)} | "
                 f"{cell(users) if users else 'unused'} |")
    L.append("")
    L.append("## F5: per-line waves")
    L.append("")
    for layer in ("BG0", "BG2", "BG3"):
        users = [f"{r['id']} {r['name']}" for r in recs if layer in infos[r["id"]]["waves"]]
        what = {"BG0": "waves the arena and the mons; chunk 6 material",
                "BG2": "above BG0 in these funcs, or suppressed with the BG2 picture",
                "BG3": "invisible under the arena; treat as BG_SWITCH (F5 + F6)"}[layer]
        L.append(f"- {layer} ({what}): {cell(users) if users else 'none'}")
    L.append("")
    L.append("SwitchBg's per-line flag (FLAG_UNK_20, a BG3 wave) is not used by any script.")
    L.append("")
    L.append("## All moves")
    L.append("")
    L.append("| id | name | mechanisms | suppress | fix | risk | notes |")
    L.append("|---|---|---|---|---|---|---|")
    for r in recs:
        L.append(f"| {r['id']} | {r['name']} | {cell(r['mechanisms'])} | {cell(r['suppress'])} | "
                 f"{cell(r['fix'])} | {r['risk']} | {md_escape(r['notes'])} |")
    L.append("")
    return "\n".join(L)


def main(argv):
    if len(argv) > 1 and argv[1] == "--scan-c":
        funcs = load_anim_c()
        table, sprite_table = script_func_table()
        for kind, tab in (("func", table), ("sprite", sprite_table)):
            for i, name in enumerate(tab):
                ev, _ = scan_func_evidence(funcs, name)
                print(f"{kind} {i:2d} {name}: {' '.join(sorted(ev))}")
        return 0
    if len(argv) > 2 and argv[1] == "--show-func":
        funcs = load_anim_c()
        for name in argv[2:]:
            body, fname, line = funcs[name]
            print(f"== {name} ({fname}:{line})")
            print(body)
        return 0
    recs, infos = run_audit()
    outs = {OUT_DIR / "move_audit.json": render_json(recs),
            OUT_DIR / "move_audit.md": render_md(recs, infos)}
    for text in outs.values():
        text.encode("ascii")
    if len(argv) > 1 and argv[1] == "--check":
        stale = [p.name for p, t in outs.items() if not p.exists() or p.read_text() != t]
        print("stale: " + " ".join(stale) if stale else "up to date")
        return 1 if stale else 0
    for p, t in outs.items():
        p.write_text(t)
    c = Counter(r["risk"] for r in recs)
    print(f"{len(recs)} moves: high {c['high']} medium {c['medium']} low {c['low']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))


