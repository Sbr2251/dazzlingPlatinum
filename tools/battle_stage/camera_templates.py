#!/usr/bin/env python3
"""Per-move camera templates for the 3D battle stage (docs/living_battle_stage/moves.md, "Per-move
camera", "Templates").

Writes the template macros of asm/macros/btlanimcam.inc into the move animation scripts listed in
TEMPLATES below, and only those. Each listed res/battle/moves/<dir>/anim.s gets:

- `#include "macros/btlanimcam.inc"` after the btlanimcmd.inc include, and one comment line;
- the template's open macro at the top of the script (after `L_0:` and the LoadParticleResource
  lines that follow it);
- `CamTplImpact` (and for template "push" first `CamTplPushImpact`) right before every hit, which is
  every `Func_Shake` on the defender (or, for "wide", on every battler but the attacker);
- `CamTplClose` right before every `End`.

Every line it writes carries a CamTpl macro or the marker comment, so a rerun first strips its own
lines and gives the same file. The table is the result of the particle profile and the checks in
moves.md ("Templates": how each move was picked and verified); REJECTED says why the other candidates
kept the home camera.

Usage:
    python3 tools/battle_stage/camera_templates.py            # write the scripts
    python3 tools/battle_stage/camera_templates.py --check    # exit 1 if a script is out of date
    python3 tools/battle_stage/camera_templates.py --strip    # remove every template (back to vanilla)
    python3 tools/battle_stage/camera_templates.py --list     # the table, by template
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MOVES = ROOT / "res" / "battle" / "moves"

INCLUDE_CMD = '#include "macros/btlanimcmd.inc"'
INCLUDE_CAM = '#include "macros/btlanimcam.inc"'
MARKER = "// Per-move camera template"

OPEN = {
    "contact": "CamTplContactOpen",
    "push": "CamTplPushOpen",
    "self": "CamTplSelfOpen",
    "twoshot": "CamTplTwoShotOpen",
    "wide": "CamTplWideOpen",
    "shake": "CamTplShakeOpen",
}
DESCRIBE = {
    "contact": "the attacker for the wind-up, then a cut to the defender, a punch on the hit",
    "push": "both mons while it flies, then a push-in on the defender at the hit",
    "self": "a close shot of the attacker with a slow orbit",
    "twoshot": "both mons for the whole move, a punch on the hit",
    "wide": "a pull-back over the whole field",
    "shake": "the camera stays home and shakes on the hit",
}

DEFENDER_HIT = re.compile(r"^\s*Func_Shake\s+([^,]+),[^,]*,[^,]*,[^,]*,\s*BATTLE_ANIM_BATTLER_SPRITE_DEFENDER\s*$")
SPREAD_HIT = re.compile(r"^\s*Func_Shake\s+([^,]+),[^,]*,[^,]*,[^,]*,\s*"
                        r"(?:BATTLE_ANIM_BATTLER_SPRITE_DEFENDER|BATTLE_ANIM_BATTLER_SPRITES\s*\|\s*BATTLE_ANIM_NOT_ATTACKER)\s*$")
END = re.compile(r"^\s*End\s*$")
LOAD = re.compile(r"^\s*(LoadParticleResource|LoadParticleSystem)\b")

# move dir -> template. Filled from the particle profile (moves.md, "Templates").
TEMPLATES = {
    # contact
    "arm_thrust": "contact",
    "astonish": "contact",
    "attract": "contact",
    "bind": "contact",
    "body_slam": "contact",
    "brick_break": "contact",
    "bullet_punch": "contact",
    "clamp": "contact",
    "comet_punch": "contact",
    "cut": "contact",
    "dizzy_punch": "contact",
    "drill_peck": "contact",
    "ember": "contact",
    "feint": "contact",
    "force_palm": "contact",
    "fury_attack": "contact",
    "fury_swipes": "contact",
    "grass_knot": "contact",
    "hi_jump_kick": "contact",
    "horn_attack": "contact",
    "lick": "contact",
    "low_kick": "contact",
    "peck": "contact",
    "pin_missile": "contact",
    "play_rough": "contact",
    "pluck": "contact",
    "poison_fang": "contact",
    "poison_jab": "contact",
    "poison_tail": "contact",
    "return": "contact",
    "secret_power": "contact",
    "smog": "contact",
    "strength": "contact",
    "struggle": "contact",
    "submission": "contact",
    "sucker_punch": "contact",
    "thrash": "contact",
    "triple_kick": "contact",
    "vine_whip": "contact",
    "vital_throw": "contact",
    "wing_attack": "contact",
    "wrap": "contact",
    "wring_out": "contact",
    # push
    "ancient_power": "push",
    "attack_order": "push",
    "block": "push",
    "bounce": "push",
    "brine": "push",
    "charm": "push",
    "chatter": "push",
    "copycat": "push",
    "cotton_spore": "push",
    "crush_grip": "push",
    "dig": "push",
    "dive": "push",
    "facade": "push",
    "fake_tears": "push",
    "feather_dance": "push",
    "fire_spin": "push",
    "flail": "push",
    "flatter": "push",
    "fling": "push",
    "gastro_acid": "push",
    "giga_drain": "push",
    "guard_swap": "push",
    "gyro_ball": "push",
    "heart_swap": "push",
    "hypnosis": "push",
    "ice_ball": "push",
    "leech_life": "push",
    "mach_punch": "push",
    "magic_coat": "push",
    "magical_leaf": "push",
    "magnet_bomb": "push",
    "me_first": "push",
    "mirror_coat": "push",
    "natural_gift": "push",
    "payback": "push",
    "poison_gas": "push",
    "poison_powder": "push",
    "poison_sting": "push",
    "power_swap": "push",
    "psybeam": "push",
    "psycho_cut": "push",
    "psycho_shift": "push",
    "psywave": "push",
    "roar": "push",
    "rock_blast": "push",
    "rock_climb": "push",
    "rock_throw": "push",
    "rollout": "push",
    "sand_attack": "push",
    "sand_tomb": "push",
    "screech": "push",
    "skill_swap": "push",
    "sleep_powder": "push",
    "sleep_talk": "push",
    "sludge": "push",
    "sludge_bomb": "push",
    "snatch": "push",
    "spider_web": "push",
    "spit_up": "push",
    "spore": "push",
    "steel_wing": "push",
    "stun_spore": "push",
    "sweet_kiss": "push",
    "tickle": "push",
    "twineedle": "push",
    "uproar": "push",
    "vacuum_wave": "push",
    "will_o_wisp": "push",
    "worry_seed": "push",
    "yawn": "push",
    # twoshot
    "aqua_jet": "twoshot",
    "assurance": "twoshot",
    "beat_up": "twoshot",
    "bite": "twoshot",
    "blaze_kick": "twoshot",
    "bone_club": "twoshot",
    "bone_rush": "twoshot",
    "bubble_beam": "twoshot",
    "bug_bite": "twoshot",
    "bug_buzz": "twoshot",
    "bullet_seed": "twoshot",
    "counter": "twoshot",
    "covet": "twoshot",
    "cross_chop": "twoshot",
    "cross_poison": "twoshot",
    "crunch": "twoshot",
    "double_hit": "twoshot",
    "double_kick": "twoshot",
    "double_slap": "twoshot",
    "dragon_breath": "twoshot",
    "dragon_rage": "twoshot",
    "egg_bomb": "twoshot",
    "embargo": "twoshot",
    "endeavor": "twoshot",
    "flame_wheel": "twoshot",
    "frustration": "twoshot",
    "headbutt": "twoshot",
    "horn_drill": "twoshot",
    "hyper_fang": "twoshot",
    "iron_head": "twoshot",
    "jump_kick": "twoshot",
    "karate_chop": "twoshot",
    "knock_off": "twoshot",
    "last_resort": "twoshot",
    "leech_seed": "twoshot",
    "lovely_kiss": "twoshot",
    "mirror_shot": "twoshot",
    "mud_bomb": "twoshot",
    "mud_shot": "twoshot",
    "mud_slap": "twoshot",
    "needle_arm": "twoshot",
    "night_slash": "twoshot",
    "octazooka": "twoshot",
    "ominous_wind": "twoshot",
    "pain_split": "twoshot",
    "pay_day": "twoshot",
    "petal_dance": "twoshot",
    "punishment": "twoshot",
    "rage": "twoshot",
    "rapid_spin": "twoshot",
    "rock_smash": "twoshot",
    "scratch": "twoshot",
    "seed_bomb": "twoshot",
    "shadow_claw": "twoshot",
    "signal_beam": "twoshot",
    "slam": "twoshot",
    "slash": "twoshot",
    "smoke_screen": "twoshot",
    "sonic_boom": "twoshot",
    "spike_cannon": "twoshot",
    "stomp": "twoshot",
    "super_fang": "twoshot",
    "take_down": "twoshot",
    "thief": "twoshot",
    "trump_card": "twoshot",
    "u_turn": "twoshot",
    "vice_grip": "twoshot",
    "wake_up_slap": "twoshot",
    "water_gun": "twoshot",
    "whirlwind": "twoshot",
    # self
    "acupressure": "self",
    "aqua_ring": "self",
    "barrier": "self",
    "belly_drum": "self",
    "bide": "self",
    "bulk_up": "self",
    "conversion": "self",
    "defend_order": "self",
    "defense_curl": "self",
    "dragon_dance": "self",
    "endure": "self",
    "focus_energy": "self",
    "growth": "self",
    "heal_order": "self",
    "light_screen": "self",
    "lucky_chant": "self",
    "magnet_rise": "self",
    "milk_drink": "self",
    "nasty_plot": "self",
    "power_trick": "self",
    "protect": "self",
    "recover": "self",
    "recycle": "self",
    "reflect": "self",
    "rest": "self",
    "roost": "self",
    "safeguard": "self",
    "sharpen": "self",
    "slack_off": "self",
    "softboiled": "self",
    "splash": "self",
    "stockpile": "self",
    "synthesis": "self",
    "withdraw": "self",
    # wide
    "acid": "wide",
    "air_cutter": "wide",
    "bubble": "wide",
    "captivate": "wide",
    "conversion_2": "wide",
    "gravity": "wide",
    "growl": "wide",
    "haze": "wide",
    "heat_wave": "wide",
    "howl": "wide",
    "imprison": "wide",
    "lava_plume": "wide",
    "mud_sport": "wide",
    "razor_leaf": "wide",
    "razor_wind": "wide",
    "rock_slide": "wide",
    "sandstorm": "wide",
    "spikes": "wide",
    "stealth_rock": "wide",
    "swallow": "wide",
    "sweet_scent": "wide",
    "tail_whip": "wide",
    "tailwind": "wide",
    "teeter_dance": "wide",
    "toxic_spikes": "wide",
    "water_sport": "wide",
    "water_spout": "wide",
}

# move dir -> why it keeps the home camera (candidates only: risk low in move_audit.json, no
# background change, no 2D OBJ effect sprites, not a camera-core move).
REJECTED = {
    "false_swipe": "the critic's reference move for real turns at home (camera: the no-kick and crit-kick turns; move_tester)",
    "pound": "the critic's reference move at home (camera: tester Pound at home; stage_toggle; move_tester turn 2)",
    "barrage": "shakes a background layer (Func_ShakeBg)",
    "baton_pass": "draws 2D OBJ effect sprites, which cannot follow the camera",
    "bonemerang": "draws 2D OBJ effect sprites, which cannot follow the camera",
    "constrict": "draws 2D OBJ effect sprites only, which cannot follow the camera",
    "crush_claw": "draws 2D OBJ effect sprites, which cannot follow the camera",
    "dragon_claw": "draws 2D OBJ effect sprites, which cannot follow the camera",
    "dragon_rush": "shakes a background layer (Func_ShakeBg)",
    "follow_me": "draws 2D OBJ effect sprites only, which cannot follow the camera",
    "gust": "switches its particles to the perspective camera (SetCameraProjection)",
    "hammer_arm": "shakes a background layer (Func_ShakeBg)",
    "icicle_spear": "draws 2D OBJ effect sprites, which cannot follow the camera",
    "magnitude": "Magnitude BG3 shake (mirrored onto the camera, category A)",
    "metronome": "draws 2D OBJ effect sprites only, which cannot follow the camera",
    "mirror_move": "no animation of its own (calls another move)",
    "nature_power": "no animation of its own (calls another move)",
    "rock_tomb": "shakes a background layer (Func_ShakeBg); switches its particles to the perspective camera (SetCameraProjection)",
    "smelling_salt": "draws 2D OBJ effect sprites, which cannot follow the camera",
    "snore": "shakes a background layer (Func_ShakeBg)",
    "substitute": "draws its doll in screen space (BtlAnimCmd_068)",
    "swagger": "draws 2D OBJ effect sprites, which cannot follow the camera",
    "torment": "draws 2D OBJ effect sprites, which cannot follow the camera",
    "twister": "switches its particles to the perspective camera (SetCameraProjection)",
    "wood_hammer": "shakes a background layer (Func_ShakeBg)",
}


def hit_amplitude(extent):
    """The camera punch for a Func_Shake of this x extent: px, frames."""
    try:
        n = int(extent.strip())
    except ValueError:
        return 2, 6
    return (3, 8) if n >= 3 else (2, 6)


def strip(lines):
    out = []
    for ln in lines:
        s = ln.strip()
        if s == INCLUDE_CAM or s.startswith(MARKER) or re.match(r"^CamTpl\w+", s):
            continue
        out.append(ln)
    return out


def apply(text, template):
    lines = strip(text.split("\n"))
    if template is None:
        return "\n".join(lines)
    out = []
    hit = SPREAD_HIT if template == "wide" else DEFENDER_HIT
    opened = False
    i = 0
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if s == INCLUDE_CMD:
            out.append(ln)
            out.append(INCLUDE_CAM)
            i += 1
            continue
        if not opened and s == "L_0:":
            out.append(f"{MARKER} \"{template}\" (moves.md, \"Templates\"): {DESCRIBE[template]}.")
            out.append(ln)
            i += 1
            while i < len(lines) and LOAD.match(lines[i]):
                out.append(lines[i])
                i += 1
            out.append(f"    {OPEN[template]}")
            opened = True
            continue
        m = hit.match(ln)
        if m and template != "self":
            if template == "push":
                out.append("    CamTplPushImpact")
            amp, frames = hit_amplitude(m.group(1))
            out.append(f"    CamTplImpact {amp}, {frames}")
        if END.match(ln):
            out.append("    CamTplClose")
        out.append(ln)
        i += 1
    if not opened:
        raise ValueError("no L_0: label")
    return "\n".join(out)


def targets(everything=False):
    dirs = set(TEMPLATES)
    if everything:
        for p in MOVES.glob("*/anim.s"):
            if any(s.strip().startswith(("CamTpl", INCLUDE_CAM)) for s in p.read_text().split("\n")):
                dirs.add(p.parent.name)
    return sorted(dirs)


def main(argv):
    mode = argv[1] if len(argv) > 1 else "--write"
    if mode == "--list":
        by = defaultdict(list)
        for d, t in sorted(TEMPLATES.items()):
            by[t].append(d)
        for t in OPEN:
            print(f"{t} ({len(by[t])}): {' '.join(by[t])}")
        print(f"total {len(TEMPLATES)}; rejected {len(REJECTED)}")
        return 0
    stale = []
    for d in targets(everything=True):
        path = MOVES / d / "anim.s"
        old = path.read_text()
        new = apply(old, None if mode == "--strip" else TEMPLATES.get(d))
        new.encode("ascii")
        if new != old:
            stale.append(d)
            if mode != "--check":
                path.write_text(new)
    if mode == "--check":
        print("stale: " + " ".join(stale) if stale else "up to date")
        return 1 if stale else 0
    print(f"{len(stale)} scripts written; {len(TEMPLATES)} templated")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
