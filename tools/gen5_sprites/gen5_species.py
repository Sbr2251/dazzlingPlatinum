#!/usr/bin/env python3
"""Writes the data of the Gen 5 species added after Arceus (docs/story/route_pokemon.md, "Gen 5").

For each species in SPECIES it writes res/pokemon/<species>/:

    data.json           stats, types, abilities, learnsets, evolutions, Pokedex data and text
    sprite_data.json    the animation/shadow template of an analogous Sinnoh species (ANALOG);
                        gen5_stream.py then sets its y_offset to 0
    meson.build         the usual per-species build file
    *.png.key           the sprite encryption keys (copied from the analogue)
    icon.png            the party/box icon (32x64, two frames) in one of the three shared icon palettes
    footprint.png       the 16x16 footprint in the vanilla 32x16 layout

The battle sprites, normal.pal and shiny.pal come from gen5_stream.py (run it after this, with no
arguments for the whole NARC). Cries come from gen5_cries.py. See README.md in this directory.

Sources (cached in ~/.cache/gen5_sprites/pokeapi and ~/.cache/gen5_sprites/expansion):
  - PokeAPI (pokeapi.co): Gen 5 base stats and abilities (past_stats/past_abilities), types, catch rate,
    growth, egg groups, held items, height/weight, Black/White learnsets, Pokedex text in six languages.
  - pokeemerald-expansion (rh-hideout): the B/W icons and footprints, as indexed PNGs.

Gen 4 has two ability slots and no Gen 5 moves, so a Gen 5 ability or move the engine lacks goes
through ABILITY_SUBS / MOVE_SUBS (closest Gen 4 equivalent, or None to drop it). Every substitution
the tool makes is printed and written to tools/gen5_sprites/gen5_species_report.json.

Usage:  gen5_species.py [--species patrat,watchog ...]    (needs PIL and numpy: ~/.venvs/desmume/bin/python)
"""

import argparse
import json
import os
import statistics
import sys
import urllib.request

import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MON = os.path.join(ROOT, "res", "pokemon")
CACHE = os.path.expanduser("~/.cache/gen5_sprites")
API = "https://pokeapi.co/api/v2"
EXPANSION = "https://raw.githubusercontent.com/rh-hideout/pokeemerald-expansion/master"
REPORT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gen5_species_report.json")
UA = {"User-Agent": "Mozilla/5.0 (dazzling-platinum gen5_species.py)"}

# (directory, national dex number, analogous Sinnoh species: sprite_data.json template, keys,
#  footprint size/type, catching show, safari flee rate)
SPECIES = [
    ("patrat", 504, "bidoof"),
    ("watchog", 505, "bibarel"),
    ("lillipup", 506, "growlithe"),
    ("herdier", 507, "staravia"),
    ("stoutland", 508, "arcanine"),
    ("purrloin", 509, "glameow"),
    ("liepard", 510, "purugly"),
    ("pidove", 519, "starly"),
    ("tranquill", 520, "staravia"),
    ("unfezant", 521, "staraptor"),
    ("roggenrola", 524, "geodude"),
    ("boldore", 525, "graveler"),
    ("gigalith", 526, "golem"),
    ("drilbur", 529, "sandshrew"),
    ("excadrill", 530, "sandslash"),
    ("timburr", 532, "machop"),
    ("gurdurr", 533, "machoke"),
    ("conkeldurr", 534, "machamp"),
    ("sewaddle", 540, "wurmple"),
    ("swadloon", 541, "silcoon"),
    ("leavanny", 542, "beautifly"),
]

# Gen 5 moves the engine lacks. Value: the Gen 4 move that replaces it, or None (dropped).
MOVE_SUBS = {
    "MOVE_WORK_UP": ("MOVE_HOWL", "self boost of Attack (Work Up: Atk and Sp. Atk +1)"),
    "MOVE_HONE_CLAWS": ("MOVE_SHARPEN", "self boost of Attack (Hone Claws: Atk and accuracy +1)"),
    "MOVE_RETALIATE": ("MOVE_FACADE", "Normal 70 power that doubles on a condition"),
    "MOVE_AFTER_YOU": ("MOVE_HELPING_HAND", "Double Battle ally support"),
    "MOVE_CHIP_AWAY": ("MOVE_HEADBUTT", "Normal physical, 70 power"),
    "MOVE_SMACK_DOWN": ("MOVE_ROCK_THROW", "Rock physical, 50 power"),
    "MOVE_STRUGGLE_BUG": ("MOVE_SILVER_WIND", "special Bug move with a stat effect"),
    "MOVE_ENTRAINMENT": ("MOVE_WORRY_SEED", "replaces the target's ability (and is Grass)"),
    "MOVE_DRILL_RUN": ("MOVE_DRILL_PECK", "80 power physical drill attack (Flying instead of Ground)"),
    "MOVE_AUTOTOMIZE": ("MOVE_ROCK_POLISH", "Speed +2 (Autotomize also lowers weight)"),
    "MOVE_HEAVY_SLAM": ("MOVE_GYRO_BALL", "Steel physical with variable power"),
    "MOVE_BESTOW": (None, "no item-giving move in Gen 4"),
    "MOVE_FOUL_PLAY": (None, "no equivalent; Faint Attack is already an egg move"),
    "MOVE_WIDE_GUARD": (None, "Detect is already an egg move"),
}
# PokeAPI move names whose Gen 4 constant is spelled differently (not substitutions)
MOVE_RENAMES = {
    "feint-attack": "MOVE_FAINT_ATTACK",
    "smelling-salts": "MOVE_SMELLING_SALT",
    "self-destruct": "MOVE_SELFDESTRUCT",
    "soft-boiled": "MOVE_SOFTBOILED",
    "high-jump-kick": "MOVE_HI_JUMP_KICK",
    "vise-grip": "MOVE_VICE_GRIP",
}

# Gen 5 abilities the engine lacks -> closest Gen 4 ability.
ABILITY_SUBS = {
    "ABILITY_BIG_PECKS": ("ABILITY_KEEN_EYE", "blocks one stat drop (Defense -> accuracy)"),
    "ABILITY_SAND_RUSH": ("ABILITY_SAND_VEIL", "sandstorm ability with sandstorm immunity (Speed -> evasion)"),
    "ABILITY_SHEER_FORCE": ("ABILITY_IRON_FIST", "boosts a class of moves (the species' own hidden ability)"),
}

# Trade evolutions get a level, like Graveler and Machoke (decision 4A, 2026-10-10).
TRADE_EVO_LEVEL = {"boldore": 37, "gurdurr": 37}

# TMs/HMs from Gen 4 that no later game teaches as a TM, or that Gen 4 gave nearly everyone:
# granted here so the Gen 5 species match their Sinnoh neighbours.
UNIVERSAL_TMS = ["TM43", "TM58", "TM78", "TM82", "TM83"]  # Secret Power, Endure, Captivate, Sleep Talk, Natural Gift
EXTRA_TMS = {
    "pidove": ["TM47", "TM88", "HM05"], "tranquill": ["TM47", "TM88", "HM05"], "unfezant": ["TM47", "TM88", "HM05"],
    "purrloin": ["TM49"], "liepard": ["TM49"],
    "herdier": ["HM08"], "stoutland": ["HM08"],
    "roggenrola": ["HM08"], "boldore": ["HM08"], "gigalith": ["HM08"],
    "drilbur": ["HM08"], "excadrill": ["HM08"],
    "timburr": ["HM08"], "gurdurr": ["HM08"], "conkeldurr": ["HM08"],
}

COLORS = {"black": "MON_COLOR_BLACK", "blue": "MON_COLOR_BLUE", "brown": "MON_COLOR_BROWN", "gray": "MON_COLOR_GRAY",
          "green": "MON_COLOR_GREEN", "pink": "MON_COLOR_PINK", "purple": "MON_COLOR_PURPLE", "red": "MON_COLOR_RED",
          "white": "MON_COLOR_WHITE", "yellow": "MON_COLOR_YELLOW"}
SHAPES = {"ball": "SHAPE_HEAD", "squiggle": "SHAPE_SERPENTINE", "fish": "SHAPE_FINS", "arms": "SHAPE_HEAD_ARMS",
          "blob": "SHAPE_HEAD_BASE", "upright": "SHAPE_BIPEDAL_TAILED", "legs": "SHAPE_HEAD_LEGS",
          "quadruped": "SHAPE_QUADRUPED", "wings": "SHAPE_WINGED", "tentacles": "SHAPE_TENTACLES",
          "heads": "SHAPE_MULTI_BODY", "humanoid": "SHAPE_BIPEDAL_TAILLESS", "bug-wings": "SHAPE_MULTI_WINGED",
          "armor": "SHAPE_INSECTOID"}
EGG_GROUPS = {"monster": "EGG_GROUP_MONSTER", "water1": "EGG_GROUP_WATER_1", "bug": "EGG_GROUP_BUG",
              "flying": "EGG_GROUP_FLYING", "ground": "EGG_GROUP_FIELD", "fairy": "EGG_GROUP_FAIRY",
              "plant": "EGG_GROUP_GRASS", "humanshape": "EGG_GROUP_HUMAN_LIKE", "water3": "EGG_GROUP_WATER_3",
              "mineral": "EGG_GROUP_MINERAL", "indeterminate": "EGG_GROUP_AMORPHOUS", "water2": "EGG_GROUP_WATER_2",
              "ditto": "EGG_GROUP_DITTO", "dragon": "EGG_GROUP_DRAGON", "no-eggs": "EGG_GROUP_UNDISCOVERED"}
GROWTH = {"medium": "EXP_RATE_MEDIUM_FAST", "medium-slow": "EXP_RATE_MEDIUM_SLOW", "slow": "EXP_RATE_SLOW",
          "fast": "EXP_RATE_FAST", "slow-then-very-fast": "EXP_RATE_ERRATIC",
          "fast-then-very-slow": "EXP_RATE_FLUCTUATING"}
GENDER = {-1: "GENDER_RATIO_NO_GENDER", 0: "GENDER_RATIO_MALE_ONLY", 1: "GENDER_RATIO_FEMALE_12_5",
          2: "GENDER_RATIO_FEMALE_25", 4: "GENDER_RATIO_FEMALE_50", 6: "GENDER_RATIO_FEMALE_75",
          7: "GENDER_RATIO_FEMALE_87_5", 8: "GENDER_RATIO_FEMALE_ONLY"}
STATS = {"hp": "hp", "attack": "attack", "defense": "defense", "speed": "speed",
         "special-attack": "special_attack", "special-defense": "special_defense"}
LANGS = {"en": "en", "fr": "fr", "de": "de", "it": "it", "es": "es", "jp": "ja-hrkt"}
DEX_VERSIONS = ["black", "white", "black-2", "white-2", "x", "y", "omega-ruby", "alpha-sapphire"]
JP_LINE_PX = 168  # vanilla Japanese entries run up to about 14 full-width characters
DEX_LINE_PX = 192  # pixel width of the widest vanilla Pokedex entry line (message font)
# Entries no source version fits into 3 lines of the Pokedex box (lightly shortened B/W text).
DEX_TEXT_OVERRIDES = {
    ("patrat", "en"): "Using food stored in cheek pouches, they can keep watch for days. They signal others with "
                      "their tails.",
    ("purrloin", "en"): "They steal from people for fun, but their victims can't help but forgive them. Their cute "
                        "act is perfect.",
    ("excadrill", "en"): "It helps in tunnel construction. Its drill has evolved into steel that can bore through "
                         "iron plates.",
    ("conkeldurr", "en"): "It is thought that CONKELDURR taught humans to make concrete more than 2,000 years ago.",
    ("sewaddle", "en"): "LEAVANNY dress it in clothes they made when it hatched. It hides its head in its hood to "
                        "sleep.",
    ("leavanny", "en"): "When it finds a small Pokémon, it weaves clothes for it from leaves with sticky silk "
                        "and its cutters.",
}
GEN = {"generation-%s" % r: i for i, r in enumerate(["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix"], 1)}

REPORT_DATA = {"moves": {}, "abilities": {}, "dropped_hidden_abilities": {}, "evolutions": {}, "cries": {}}


def fetch(url, path, binary=False):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            data = r.read()
        with open(path + ".tmp", "wb") as f:
            f.write(data)
        os.replace(path + ".tmp", path)
    if binary:
        return path
    with open(path) as f:
        return json.load(f)


def api(kind, n):
    return fetch(f"{API}/{kind}/{n}", os.path.join(CACHE, "pokeapi", f"{kind}_{n}.json"))


def expansion(name, rel):
    return fetch(f"{EXPANSION}/{rel}", os.path.join(CACHE, "expansion", name, os.path.basename(rel)), binary=True)


def consts(name):
    with open(os.path.join(ROOT, "generated", name)) as f:
        return [ln.split("=")[0].strip() for ln in f if ln.strip()]


MOVES = set(consts("moves.txt"))
SPECIES_NAMES = {c[len("SPECIES_"):] for c in consts("species.txt")} | {n.upper() for n, _, _ in SPECIES}
ABILITIES = set(consts("abilities.txt"))
ITEMS = set(consts("items.txt"))


def move_const(name):
    return MOVE_RENAMES.get(name, "MOVE_" + name.upper().replace("-", "_"))


def map_move(species, const, where):
    """Gen 4 constant for a move, or None. Records substitutions."""
    if const in MOVES:
        return const
    if const not in MOVE_SUBS:
        return None  # machine/tutor lists: only Gen 4 moves are considered at all
    sub, why = MOVE_SUBS[const]
    REPORT_DATA["moves"].setdefault(const, {"to": sub, "why": why, "where": []})["where"].append(f"{species} {where}")
    return sub


def gen5_stats(poke):
    stats = {STATS[s["stat"]["name"]]: s["base_stat"] for s in poke["stats"]}
    for past in sorted(poke.get("past_stats", []), key=lambda p: -GEN[p["generation"]["name"]]):
        if GEN[past["generation"]["name"]] >= 5:
            for s in past["stats"]:
                stats[STATS[s["stat"]["name"]]] = s["base_stat"]
    return stats


def gen5_abilities(poke):
    slots = {a["slot"]: a["ability"]["name"] for a in poke["abilities"]}
    for past in sorted(poke.get("past_abilities", []), key=lambda p: -GEN[p["generation"]["name"]]):
        if GEN[past["generation"]["name"]] >= 5:
            for a in past["abilities"]:
                if a["ability"] is None:
                    slots.pop(a["slot"], None)
                else:
                    slots[a["slot"]] = a["ability"]["name"]
    return slots


def ability_const(name):
    return "ABILITY_" + name.upper().replace("-", "_")


def map_ability(species, name):
    const = ability_const(name)
    if const in ABILITIES:
        return const
    sub, why = ABILITY_SUBS[const]
    REPORT_DATA["abilities"].setdefault(const, {"to": sub, "why": why, "species": []})["species"].append(species)
    return sub


def _charmap():
    cm = {}
    with open(os.path.join(ROOT, "tools", "msgenc", "charmap.txt"), encoding="utf-8") as f:
        for ln in f:
            ln = ln.rstrip("\n")
            if "=" in ln:
                code, ch = ln.split("=", 1)
                if len(ch) == 1 and ch not in cm:
                    try:
                        cm[ch] = int(code, 16)
                    except ValueError:
                        pass
    return cm


CHARMAP = _charmap()
with open(os.path.join(ROOT, "res", "fonts", "font_message.json")) as _f:
    GLYPH_W = json.load(_f)["glyphWidths"]


def text_width(s):
    """Pixel width in the message font (glyph index = character code - 1)."""
    return sum(GLYPH_W[CHARMAP[c] - 1] for c in s)


def check_chars(s, where):
    bad = sorted({c for c in s if c not in CHARMAP and c != "\n"})
    if bad:
        raise SystemExit(f"{where}: characters not in the game charmap: {bad}")


def kana(text):
    """The game writes the katakana long vowel as a full-width hyphen."""
    return text.replace("\u30fc", "\uff0d")


def wrap(text, width=DEX_LINE_PX, sep=" "):
    lines, cur = [], ""
    for word in text.split():
        cand = f"{cur}{sep}{word}" if cur else word
        if cur and text_width(cand) > width:
            lines.append(cur)
            cur = word
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines


def clean(text):
    return (text.replace("\u2019", "'").replace("\u2018", "'").replace("\u00ad", "").replace("\f", " ")
            .replace("\n", " ").replace("\u00a0", " ").replace("POKéMON", "Pokémon").replace("  ", " ").strip())


def upper_names(text):
    """Platinum writes species names in capitals inside Pokedex entries."""
    out = []
    for word in text.split(" "):
        core = word.strip(".,;:!?'s")
        if core and core.upper() in SPECIES_NAMES and core[0].isupper():
            word = word.replace(core, core.upper(), 1)
        out.append(word)
    return " ".join(out)


def as_lines(lines):
    return [ln + "\n" for ln in lines[:-1]] + [lines[-1]]


def dex_text(species_json, lang, name_upper):
    """Black/White entry (later games as a fallback) wrapped into at most 3 lines that fit the
    Pokedex text box. Japanese keeps the source's own line breaks. Only the English entry is ever
    shown for species after Arceus (their language flags are not saved), so the other languages are
    best effort: the version that wraps into the fewest lines."""
    key = (species_json["name"], lang)
    if key in DEX_TEXT_OVERRIDES:
        lines = wrap(DEX_TEXT_OVERRIDES[key])
        if len(lines) > 3:
            raise SystemExit(f"{key}: override still needs {len(lines)} lines")
        return as_lines(lines)
    best = None
    for version in DEX_VERSIONS:
        for e in species_json["flavor_text_entries"]:
            if e["language"]["name"] != lang or e["version"]["name"] != version:
                continue
            if lang == "ja-hrkt":
                words = [w for w in kana(e["flavor_text"]).replace("\f", "\n").replace("\u3000", "\n").split("\n") if w]
                return as_lines(wrap("\u3000".join(words).replace("\u3000", " "), JP_LINE_PX, sep="\u3000"))
            text = clean(e["flavor_text"])
            if lang == "en":
                text = upper_names(text)
            lines = wrap(text)
            if len(lines) <= 3:
                return as_lines(lines)
            if best is None or len(lines) < len(best):
                best = lines
    if lang == "en" or best is None:
        raise SystemExit(f"{species_json['name']} ({lang}): no Pokedex entry fits 3 lines; add a DEX_TEXT_OVERRIDES entry")
    return as_lines(best)


def localized(species_json, field, lang, key):
    for e in species_json[field]:
        if e["language"]["name"] == lang:
            return clean(e[key]) if lang != "ja-hrkt" else kana(e[key])
    return None


def held_items(poke):
    common = rare = "ITEM_NONE"
    for h in poke["held_items"]:
        for v in h["version_details"]:
            if v["version"]["name"] in ("black-2", "white-2", "black", "white"):
                const = "ITEM_" + h["item"]["name"].upper().replace("-", "_")
                if const not in ITEMS:
                    continue
                if v["rarity"] >= 50:
                    common = const
                else:
                    rare = const
    return {"common": common, "rare": rare}


def learnsets(name, poke):
    by_level, egg = [], []
    teachable = set()  # Gen 4 moves the species can learn from a TM/tutor in any game
    level_moves = set()
    for m in poke["moves"]:
        const = move_const(m["move"]["name"])
        for v in m["version_group_details"]:
            method, vg = v["move_learn_method"]["name"], v["version_group"]["name"]
            if method in ("machine", "tutor"):
                teachable.add(const)
            if vg != "black-2-white-2":
                continue
            if method == "level-up":
                sub = map_move(name, const, f"Lv{v['level_learned_at']}")
                if sub:
                    by_level.append([v["level_learned_at"], sub])
                    level_moves.add(sub)
            elif method == "egg":
                sub = map_move(name, const, "egg")
                if sub and sub not in egg:
                    egg.append(sub)
    by_level.sort(key=lambda x: x[0])
    # drop exact duplicates (same level, same move) that a substitution can create
    seen, lv = set(), []
    for e in by_level:
        if tuple(e) not in seen:
            seen.add(tuple(e))
            lv.append(e)
    tm_moves = tm_table()
    tms = [tm for tm, mv in tm_moves if mv in teachable or mv in level_moves]
    tms = sorted(set(tms) | set(UNIVERSAL_TMS) | set(EXTRA_TMS.get(name, [])), key=lambda t: (t[:2] == "HM", int(t[2:])))
    with open(os.path.join(MON, "move_tutors.json")) as f:
        tutor_moves = list(json.load(f)["moves"])
    tutors = [mv for mv in tutor_moves if mv in teachable or mv in level_moves or mv in egg]
    if "MOVE_SNORE" not in tutors:
        tutors.append("MOVE_SNORE")
    return lv, tms, tutors, egg


_TM = None


def tm_table():
    global _TM
    if _TM is None:
        import re
        src = open(os.path.join(ROOT, "src", "item.c")).read()
        _TM = re.findall(r"\[TMHM_ID\(((?:TM|HM)\d+)\)\] = (MOVE_\w+)", src)
    return _TM


def dex_scale_table():
    """Median vanilla Pokedex size-comparison values per height (dm)."""
    fields = ["trainer_scale_f", "pokemon_scale_f", "trainer_scale_m", "pokemon_scale_m",
              "trainer_pos_f", "pokemon_pos_f", "trainer_pos_m", "pokemon_pos_m"]
    by_h = {}
    for s in os.listdir(MON):
        p = os.path.join(MON, s, "data.json")
        if s in {x[0] for x in SPECIES} or s in ("deino", "zweilous", "hydreigon") or not os.path.exists(p):
            continue
        with open(p) as f:
            px = json.load(f).get("pokedex_data")
        if not px or px.get("trainer_scale_m") != 256:
            continue
        by_h.setdefault(px["height"], []).append([px[k] - (65536 if px[k] > 32767 else 0) for k in fields])
    return fields, by_h


def dex_scales(height, table):
    fields, by_h = table
    near = sorted(by_h, key=lambda h: (abs(h - height), h))
    rows = []
    for h in near:
        rows += by_h[h]
        if len(rows) >= 5:
            break
    out = {}
    for i, k in enumerate(fields):
        v = int(statistics.median(r[i] for r in rows))
        out[k] = v & 0xFFFF if v < 0 else v
    return out


def icon(name, outdir):
    """B/W icon remapped to the shared Platinum icon palette that fits best. Returns its index."""
    src = Image.open(expansion(name, f"graphics/pokemon/{name}/icon.png"))
    with open(os.path.join(MON, ".shared", "pl_poke_icon.pal")) as f:
        rows = f.read().split("\n")[3:3 + 48]
    shared = [tuple(map(int, r.split())) for r in rows]
    pals = [shared[i * 16:(i + 1) * 16] for i in range(3)]
    sp = src.getpalette()[:48]
    spal = [tuple(sp[i:i + 3]) for i in range(0, 48, 3)]
    a = np.array(src)
    used, counts = np.unique(a, return_counts=True)
    best = None
    for pi, pal in enumerate(pals):
        mapping, err = {0: 0}, 0
        for idx, cnt in zip(used, counts):
            if idx == 0:
                continue
            c = spal[idx]
            d = [sum((c[k] - p[k]) ** 2 for k in range(3)) for p in pal[1:]]
            j = int(np.argmin(d)) + 1
            mapping[int(idx)] = j
            err += d[j - 1] * cnt
        if best is None or err < best[0]:
            best = (err, pi, mapping)
    _, pi, mapping = best
    out = np.vectorize(lambda v: mapping.get(int(v), 0))(a).astype(np.uint8)
    img = Image.fromarray(out, "P")
    flat = [c for col in pals[pi] for c in col]
    img.putpalette(flat + [0] * (768 - len(flat)))
    img.save(os.path.join(outdir, "icon.png"), bits=4)
    return pi


def footprint(name, outdir, template):
    """16x16 footprint into the vanilla 32x16 layout (print in the left half, colour 4)."""
    a = np.array(Image.open(expansion(name, f"graphics/pokemon/{name}/footprint.png")))
    tpl = Image.open(template)
    out = np.zeros((16, 32), np.uint8)
    out[:, 16:] = 12
    out[:, :16][a != 0] = 4
    img = Image.fromarray(out, "P")
    img.putpalette(tpl.getpalette())
    img.save(os.path.join(outdir, "footprint.png"), bits=4)
    return bool((a != 0).any())


def build(name, natdex, analog, table, species_names):
    poke, spec = api("pokemon", natdex), api("pokemon-species", natdex)
    with open(os.path.join(MON, analog, "data.json")) as f:
        ana = json.load(f)
    outdir = os.path.join(MON, name)
    os.makedirs(outdir, exist_ok=True)

    slots = gen5_abilities(poke)
    regular = [slots[s] for s in (1, 2) if s in slots]
    hidden = slots.get(3)
    abilities = [map_ability(name, a) for a in regular]
    if len(abilities) == 1:
        if hidden and ability_const(hidden) in ABILITIES:
            abilities.append(ability_const(hidden))
            hidden = None
        else:
            abilities.append("ABILITY_NONE")
    if hidden:
        REPORT_DATA["dropped_hidden_abilities"][name] = ability_const(hidden)

    by_level, tms, tutors, egg = learnsets(name, poke)

    evolutions = []
    chain = fetch(spec["evolution_chain"]["url"], os.path.join(CACHE, "pokeapi", f"chain_{spec['evolution_chain']['url'].rstrip('/').split('/')[-1]}.json"))

    def walk(node):
        if node["species"]["name"] == name:
            return node
        for n in node["evolves_to"]:
            r = walk(n)
            if r:
                return r
        return None

    node = walk(chain["chain"])
    for nxt in node["evolves_to"]:
        target = "SPECIES_" + nxt["species"]["name"].upper()
        d = nxt["evolution_details"][0]
        trig = d["trigger"]["name"]
        if trig == "level-up" and d["min_happiness"]:
            evolutions.append(["EVO_LEVEL_HAPPINESS", target])
        elif trig == "level-up":
            evolutions.append(["EVO_LEVEL", d["min_level"], target])
        elif trig == "trade":
            evolutions.append(["EVO_LEVEL", TRADE_EVO_LEVEL[name], target])
            REPORT_DATA["evolutions"][name] = f"trade -> level {TRADE_EVO_LEVEL[name]} ({nxt['species']['name']})"
        else:
            raise SystemExit(f"{name}: unhandled evolution trigger {trig}")
    base = chain["chain"]["species"]["name"]

    egg_groups = [EGG_GROUPS[e["name"]] for e in spec["egg_groups"]]
    if len(egg_groups) == 1:
        egg_groups.append(egg_groups[0])
    types = ["TYPE_" + t["type"]["name"].upper() for t in sorted(poke["types"], key=lambda t: t["slot"])]
    if len(types) == 1:
        types.append(types[0])

    has_print = footprint(name, outdir, os.path.join(MON, analog, "footprint.png"))
    icon_pal = icon(name, outdir)

    pokedex = {"height": poke["height"], "weight": poke["weight"], "body_shape": SHAPES[spec["shape"]["name"]]}
    pokedex.update(dex_scales(poke["height"], table))
    for key, lang in LANGS.items():
        nm = localized(spec, "names", lang, "name")
        genus = localized(spec, "genera", lang, "genus")
        if key == "en":
            nm = nm.upper()
            genus = genus.replace("Pokemon", "Pokémon")
        elif key != "jp":
            nm = nm.upper()
        pokedex[key] = {"name": nm, "category": genus, "entry_text": dex_text(spec, lang, nm)}
        check_chars(nm + genus + "".join(pokedex[key]["entry_text"]), f"{name} {key}")

    data = {
        "base_stats": gen5_stats(poke),
        "types": types,
        "catch_rate": spec["capture_rate"],
        "base_exp_reward": poke["base_experience"],
        "ev_yields": {STATS[s["stat"]["name"]]: s["effort"] for s in poke["stats"]},
        "held_items": held_items(poke),
        "gender_ratio": GENDER[spec["gender_rate"]],
        "hatch_cycles": spec["hatch_counter"],
        "base_friendship": spec["base_happiness"],
        "exp_rate": GROWTH[spec["growth_rate"]["name"]],
        "egg_groups": egg_groups,
        "abilities": abilities,
        "safari_flee_rate": ana["safari_flee_rate"],
        "body_color": COLORS[spec["color"]["name"]],
        "flip_sprite": False,
        "icon_palette": icon_pal,
        "learnset": {"by_level": by_level, "by_tm": tms, "by_tutor": tutors, "egg_moves": egg},
        "evolutions": evolutions,
        "offspring": "SPECIES_" + base.upper(),
        "footprint": {"has": has_print, "size": ana["footprint"]["size"], "type": ana["footprint"]["type"]},
        "pokedex_data": pokedex,
        "catching_show": dict(ana["catching_show"]),
    }
    order = ["hp", "attack", "defense", "speed", "special_attack", "special_defense"]
    data["base_stats"] = {k: data["base_stats"][k] for k in order}
    data["ev_yields"] = {k: data["ev_yields"][k] for k in order}
    with open(os.path.join(outdir, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        f.write("\n")

    # sprite_data.json and keys from the analogue (gen5_stream.py rewrites the PNGs and y_offset)
    sd = os.path.join(outdir, "sprite_data.json")
    if not os.path.exists(sd):
        with open(os.path.join(MON, analog, "sprite_data.json")) as f:
            tpl = json.load(f)
        with open(sd, "w") as f:
            json.dump(tpl, f, indent=4)
            f.write("\n")
    # placeholders until gen5_stream.py writes the B/W art (it only fills files that exist)
    for fname in ("female_front.png", "female_back.png", "male_front.png", "male_back.png", "normal.pal", "shiny.pal"):
        dst = os.path.join(outdir, fname)
        if not os.path.exists(dst):
            with open(os.path.join(MON, analog, fname), "rb") as f:
                blob = f.read()
            with open(dst, "wb") as f:
                f.write(blob)
    for g in ("female", "male"):
        for face in ("front", "back"):
            k = os.path.join(outdir, f"{g}_{face}.png.key")
            if not os.path.exists(k):
                with open(os.path.join(MON, analog, f"{g}_{face}.png.key"), "rb") as f:
                    key = f.read()
                with open(k, "wb") as f:
                    f.write(key)
    with open(os.path.join(outdir, "meson.build"), "w") as f:
        f.write("species_data_files += files('data.json')\n\n"
                "poke_icon_files += files('icon.png')\n\n"
                "pokegra_files += files('female_back.png')\n"
                "pokegra_files += files('male_back.png')\n"
                "pokegra_files += files('female_front.png')\n"
                "pokegra_files += files('male_front.png')\n\n"
                "pokefoot_files += files('footprint.png')\n")
    print(f"{name}: {data['types']} {abilities} evo={evolutions} icon_pal={icon_pal} footprint={has_print}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--species", default="", help="comma-separated subset")
    args = ap.parse_args()
    want = set(filter(None, args.species.split(",")))
    table = dex_scale_table()
    for name, natdex, analog in SPECIES:
        if not want or name in want:
            build(name, natdex, analog, table, [s[0] for s in SPECIES])
    with open(REPORT, "w") as f:
        json.dump(REPORT_DATA, f, indent=1)
        f.write("\n")
    for const, r in sorted(REPORT_DATA["moves"].items()):
        print(f"move {const} -> {r['to']}: {', '.join(r['where'])}")
    for const, r in sorted(REPORT_DATA["abilities"].items()):
        print(f"ability {const} -> {r['to']}: {', '.join(r['species'])}")


if __name__ == "__main__":
    sys.exit(main())
