#!/usr/bin/env python3
"""
Generate Dazzling Platinum Phenomena encounter/item tables from Platinum Reforged data.

Outputs (all under the repository root):
  - res/field/phenomena_tables.json
  - include/overlay006/phenomena_tables.h
  - src/overlay006/phenomena_tables.c

By default, if /tmp/platinum-reforged-anvil exists, this script extracts the
official Platinum Reforged encounter tables from its origin/gh-pages HTML and
updates res/field/phenomena_tables.json before generating the C header/source.
Pass --from-json (or run without the reference repo present) to regenerate the
C files directly from res/field/phenomena_tables.json.
"""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
import unicodedata


DEFAULT_REF_REPO = Path("/tmp/platinum-reforged-anvil")
REPO_ROOT = Path(__file__).resolve().parents[2]

HONEY_SENTINEL = "PHENOMENON_SPECIES_HONEY_TREE"

# Exact location heading (ASCII-normalized) -> list of MAP_HEADER_* constants.
LOCATION_TO_MAPS: dict[str, list[str]] = {
    # Routes
    "Route 201": ["MAP_HEADER_ROUTE_201"],
    "Route 202": ["MAP_HEADER_ROUTE_202"],
    "Route 203": ["MAP_HEADER_ROUTE_203"],
    "Route 204 (south)": ["MAP_HEADER_ROUTE_204_SOUTH"],
    "Route 204 (north)": ["MAP_HEADER_ROUTE_204_NORTH"],
    "Route 205 (south)": ["MAP_HEADER_ROUTE_205_SOUTH"],
    "Route 205 (north)": ["MAP_HEADER_ROUTE_205_NORTH"],
    "Route 206": ["MAP_HEADER_ROUTE_206"],
    "Route 207": ["MAP_HEADER_ROUTE_207"],
    "Route 208": ["MAP_HEADER_ROUTE_208"],
    "Route 209": ["MAP_HEADER_ROUTE_209"],
    "Route 210 (south)": ["MAP_HEADER_ROUTE_210_SOUTH"],
    "Route 210 (north)": ["MAP_HEADER_ROUTE_210_NORTH"],
    "Route 211 (west)": ["MAP_HEADER_ROUTE_211_WEST"],
    "Route 211 (east)": ["MAP_HEADER_ROUTE_211_EAST"],
    "Route 212 (north)": ["MAP_HEADER_ROUTE_212_NORTH"],
    "Route 212 (south)": ["MAP_HEADER_ROUTE_212_SOUTH"],
    "Route 213": ["MAP_HEADER_ROUTE_213"],
    "Route 214": ["MAP_HEADER_ROUTE_214"],
    "Route 215": ["MAP_HEADER_ROUTE_215"],
    "Route 216": ["MAP_HEADER_ROUTE_216"],
    "Route 217": ["MAP_HEADER_ROUTE_217"],
    "Route 218": ["MAP_HEADER_ROUTE_218"],
    "Route 219": ["MAP_HEADER_ROUTE_219"],
    "Route 220": ["MAP_HEADER_ROUTE_220"],
    "Route 221": ["MAP_HEADER_ROUTE_221"],
    "Route 222": ["MAP_HEADER_ROUTE_222"],
    "Route 223": ["MAP_HEADER_ROUTE_223"],
    "Route 224": ["MAP_HEADER_ROUTE_224"],
    "Route 225": ["MAP_HEADER_ROUTE_225"],
    "Route 226": ["MAP_HEADER_ROUTE_226"],
    "Route 227": ["MAP_HEADER_ROUTE_227"],
    "Route 228": ["MAP_HEADER_ROUTE_228"],
    "Route 229": ["MAP_HEADER_ROUTE_229"],
    "Route 230": ["MAP_HEADER_ROUTE_230"],
    # Caves
    "Oreburgh Gate (1F)": ["MAP_HEADER_OREBURGH_GATE_1F"],
    "Oreburgh Gate (B1F)": ["MAP_HEADER_OREBURGH_GATE_B1F"],
    "Oreburgh Mine (B1F)": ["MAP_HEADER_OREBURGH_MINE_B1F"],
    "Oreburgh Mine (B2F)": [
        "MAP_HEADER_OREBURGH_MINE_B2F",
        "MAP_HEADER_OREBURGH_MINE_SIDE_TUNNEL",
    ],
    "Ravaged Path": ["MAP_HEADER_RAVAGED_PATH"],
    "Mt. Coronet (1F, Route 211 side)": ["MAP_HEADER_MT_CORONET_1F_NORTH_ROOM_1"],
    "Mt. Coronet (1F, south)": ["MAP_HEADER_MT_CORONET_1F_SOUTH"],
    "Mt. Coronet (2F / 3F / 4F, room 3 / 1F, tunnel room)": [
        "MAP_HEADER_MT_CORONET_2F",
        "MAP_HEADER_MT_CORONET_3F",
        "MAP_HEADER_MT_CORONET_4F_ROOM_3",
        "MAP_HEADER_MT_CORONET_1F_TUNNEL_ROOM",
    ],
    "Mt. Coronet (4F, rooms 1 and 2)": ["MAP_HEADER_MT_CORONET_4F_ROOMS_1_AND_2"],
    "Mt. Coronet (5F)": ["MAP_HEADER_MT_CORONET_5F"],
    "Mt. Coronet (6F)": ["MAP_HEADER_MT_CORONET_6F"],
    "Mt. Coronet (1F, north)": ["MAP_HEADER_MT_CORONET_1F_NORTH_ROOM_2"],
    "Mt. Coronet (B1F)": ["MAP_HEADER_MT_CORONET_B1F"],
    "Mt. Coronet (snowy path, south)": ["MAP_HEADER_MT_CORONET_OUTSIDE_SOUTH"],
    "Mt. Coronet (snowy path, north)": ["MAP_HEADER_MT_CORONET_OUTSIDE_NORTH"],
    "Wayward Cave": [
        "MAP_HEADER_WAYWARD_CAVE_1F",
        "MAP_HEADER_WAYWARD_CAVE_B1F",
    ],
    "Solaceon Ruins": [
        "MAP_HEADER_SOLACEON_RUINS_MANIAC_TUNNEL_ROOM",
        "MAP_HEADER_SOLACEON_RUINS_ROOM_1_NORTHWEST_DEAD_END",
        "MAP_HEADER_SOLACEON_RUINS_ROOM_1_SOUTHEAST_DEAD_END",
        "MAP_HEADER_SOLACEON_RUINS_ROOM_2",
        "MAP_HEADER_SOLACEON_RUINS_ROOM_2_NORTHEAST_DEAD_END",
        "MAP_HEADER_SOLACEON_RUINS_ROOM_2_SOUTHEAST_DEAD_END",
        "MAP_HEADER_SOLACEON_RUINS_ROOM_3",
        "MAP_HEADER_SOLACEON_RUINS_ROOM_3_NORTHWEST_DEAD_END",
        "MAP_HEADER_SOLACEON_RUINS_ROOM_3_SOUTHWEST_DEAD_END",
        "MAP_HEADER_SOLACEON_RUINS_ROOM_4",
        "MAP_HEADER_SOLACEON_RUINS_ROOM_4_SOUTHEAST_DEAD_END",
        "MAP_HEADER_SOLACEON_RUINS_ROOM_5",
        "MAP_HEADER_SOLACEON_RUINS_ROOM_5_SOUTHEAST_DEADEND",
        "MAP_HEADER_SOLACEON_RUINS_ROOM_5_SOUTHWEST_DEAD_END",
        "MAP_HEADER_SOLACEON_RUINS_ROOM_6",
        "MAP_HEADER_SOLACEON_RUINS_ROOM_6_NORTHWEST_DEAD_END",
        "MAP_HEADER_SOLACEON_RUINS_ROOM_6_SOUTHEAST_DEAD_END",
        "MAP_HEADER_SOLACEON_RUINS_ROOM_7",
    ],
    "Maniac Tunnel": ["MAP_HEADER_MANIAC_TUNNEL"],
    "Ruin Maniac Cave (short)": ["MAP_HEADER_RUIN_MANIAC_CAVE_SHORT"],
    "Ruin Maniac Cave (long)": ["MAP_HEADER_RUIN_MANIAC_CAVE_LONG"],
    "Iron Island (outside)": ["MAP_HEADER_IRON_ISLAND"],
    "Iron Island (1F / B1F, left)": [
        "MAP_HEADER_IRON_ISLAND_1F",
        "MAP_HEADER_IRON_ISLAND_B1F_LEFT_ROOM",
    ],
    "Iron Island (B1F, right)": ["MAP_HEADER_IRON_ISLAND_B1F_RIGHT_ROOM"],
    "Iron Island (B2F, right / B2F, left)": [
        "MAP_HEADER_IRON_ISLAND_B2F_RIGHT_ROOM",
        "MAP_HEADER_IRON_ISLAND_B2F_LEFT_ROOM",
    ],
    "Iron Island (B3F)": ["MAP_HEADER_IRON_ISLAND_B3F"],
    "Victory Road (1F)": ["MAP_HEADER_VICTORY_ROAD_1F"],
    "Victory Road (2F)": ["MAP_HEADER_VICTORY_ROAD_2F"],
    "Victory Road (B1F)": ["MAP_HEADER_VICTORY_ROAD_B1F"],
    "Victory Road (1F, room 1 / 1F, room 3)": [
        "MAP_HEADER_VICTORY_ROAD_1F_ROOM_1",
        "MAP_HEADER_VICTORY_ROAD_1F_ROOM_3",
    ],
    "Victory Road (1F, room 2)": ["MAP_HEADER_VICTORY_ROAD_1F_ROOM_2"],
    "Turnback Cave (pillar 1, rooms 1-6)": [
        "MAP_HEADER_TURNBACK_CAVE_ENTRANCE",
        "MAP_HEADER_TURNBACK_CAVE_PILLAR_1_ROOM_1",
        "MAP_HEADER_TURNBACK_CAVE_PILLAR_1_ROOM_2",
        "MAP_HEADER_TURNBACK_CAVE_PILLAR_1_ROOM_3",
        "MAP_HEADER_TURNBACK_CAVE_PILLAR_1_ROOM_4",
        "MAP_HEADER_TURNBACK_CAVE_PILLAR_1_ROOM_5",
        "MAP_HEADER_TURNBACK_CAVE_PILLAR_1_ROOM_6",
    ],
    "Turnback Cave (pillar 2, rooms 1-6)": [
        "MAP_HEADER_TURNBACK_CAVE_PILLAR_2_ROOM_1",
        "MAP_HEADER_TURNBACK_CAVE_PILLAR_2_ROOM_2",
        "MAP_HEADER_TURNBACK_CAVE_PILLAR_2_ROOM_3",
        "MAP_HEADER_TURNBACK_CAVE_PILLAR_2_ROOM_4",
        "MAP_HEADER_TURNBACK_CAVE_PILLAR_2_ROOM_5",
        "MAP_HEADER_TURNBACK_CAVE_PILLAR_2_ROOM_6",
    ],
    "Turnback Cave (pillar 3, rooms 1-5)": [
        "MAP_HEADER_TURNBACK_CAVE_PILLAR_3_ROOM_1",
        "MAP_HEADER_TURNBACK_CAVE_PILLAR_3_ROOM_2",
        "MAP_HEADER_TURNBACK_CAVE_PILLAR_3_ROOM_3",
        "MAP_HEADER_TURNBACK_CAVE_PILLAR_3_ROOM_4",
        "MAP_HEADER_TURNBACK_CAVE_PILLAR_3_ROOM_5",
        "MAP_HEADER_TURNBACK_CAVE_PILLAR_3_ROOM_6",
        "MAP_HEADER_TURNBACK_CAVE_PILLAR_ROOM",
    ],
    "Snowpoint Temple (1F / B1F / B2F / B3F)": [
        "MAP_HEADER_SNOWPOINT_TEMPLE_1F",
        "MAP_HEADER_SNOWPOINT_TEMPLE_B1F",
        "MAP_HEADER_SNOWPOINT_TEMPLE_B2F",
        "MAP_HEADER_SNOWPOINT_TEMPLE_B3F",
    ],
    "Snowpoint Temple (B4F / B5F)": [
        "MAP_HEADER_SNOWPOINT_TEMPLE_B4F",
        "MAP_HEADER_SNOWPOINT_TEMPLE_B5F",
    ],
    "Stark Mountain (outside)": ["MAP_HEADER_STARK_MOUNTAIN_OUTSIDE"],
    "Stark Mountain (inside, entrance)": ["MAP_HEADER_STARK_MOUNTAIN_ROOM_1"],
    "Stark Mountain (inside)": ["MAP_HEADER_STARK_MOUNTAIN_ROOM_2"],
    # Places
    "Twinleaf Town": ["MAP_HEADER_TWINLEAF_TOWN"],
    "Lake Verity": ["MAP_HEADER_LAKE_VERITY"],
    "Lake Verity (low water)": ["MAP_HEADER_LAKE_VERITY_LOW_WATER"],
    "Valley Windworks": ["MAP_HEADER_VALLEY_WINDWORKS_OUTSIDE"],
    "Eterna Forest": ["MAP_HEADER_ETERNA_FOREST"],
    "Eterna City": ["MAP_HEADER_ETERNA_CITY"],
    "Pastoria City": ["MAP_HEADER_PASTORIA_CITY"],
    "Valor Lakefront": ["MAP_HEADER_VALOR_LAKEFRONT"],
    "Canalave City": ["MAP_HEADER_CANALAVE_CITY"],
    "Fuego Ironworks": ["MAP_HEADER_FUEGO_IRONWORKS_OUTSIDE"],
    "Acuity Lakefront": ["MAP_HEADER_ACUITY_LAKEFRONT"],
    "Lake Acuity": ["MAP_HEADER_LAKE_ACUITY"],
    "Lake Valor": ["MAP_HEADER_LAKE_VALOR"],
    "Celestic Town": ["MAP_HEADER_CELESTIC_TOWN"],
    "Sunyshore City": ["MAP_HEADER_SUNYSHORE_CITY"],
    "Pokemon League": ["MAP_HEADER_POKEMON_LEAGUE"],
    "Sendoff Spring": ["MAP_HEADER_SENDOFF_SPRING"],
    "Resort Area": ["MAP_HEADER_RESORT_AREA"],
}

LABEL_TO_KEY: dict[str, str] = {
    "Rustling grass": "grass",
    "Dust clouds": "dust",
    "Surfing": "surf",
    "Fishing": "fish",
    "Shadows (day)": "shadow_day",
    "Shadows (night)": "shadow_night",
}

# Evolution level floors from Platinum Reforged's phenomena rules:
# stone/held-item evos = 35, trade evos + Honchkrow/Mismagius = 38, level-up evos = evo level.
SPECIES_EVOLUTION_FLOOR: dict[str, int] = {
    "SPECIES_KRICKETUNE": 10,
    "SPECIES_BEAUTIFLY": 10,
    "SPECIES_STARAVIA": 14,
    "SPECIES_LUXIO": 15,
    "SPECIES_AZUMARILL": 18,
    "SPECIES_KIRLIA": 20,
    "SPECIES_GYARADOS": 20,
    "SPECIES_HOUNDOOM": 24,
    "SPECIES_GABITE": 24,
    "SPECIES_FLOATZEL": 26,
    "SPECIES_GARDEVOIR": 30,
    "SPECIES_LUXRAY": 30,
    "SPECIES_WHISCASH": 30,
    "SPECIES_BASTIODON": 30,
    "SPECIES_RAMPARDOS": 30,
    "SPECIES_GOLDUCK": 33,
    "SPECIES_SEAKING": 33,
    "SPECIES_MAMOSWINE": 33,
    "SPECIES_SKUNTANK": 34,
    "SPECIES_ALTARIA": 35,
    "SPECIES_CHANSEY": 35,
    "SPECIES_BLISSEY": 35,
    "SPECIES_FROSLASS": 35,
    "SPECIES_VAPOREON": 35,
    "SPECIES_TOGEKISS": 35,
    "SPECIES_ROSERADE": 35,
    "SPECIES_GALLADE": 35,
    "SPECIES_STEELIX": 38,
    "SPECIES_GENGAR": 38,
    "SPECIES_DUSKNOIR": 38,
    "SPECIES_MISMAGIUS": 38,
    "SPECIES_HONCHKROW": 38,
    "SPECIES_ELECTIVIRE": 38,
    "SPECIES_MAGMORTAR": 38,
    "SPECIES_MACHAMP": 38,
    "SPECIES_SCIZOR": 38,
    "SPECIES_PURUGLY": 38,
    "SPECIES_GARCHOMP": 48,
}

# Early-game rustling grass level floors explicitly raised in Platinum Reforged (8-10).
EARLY_GRASS_LEVEL_FLOOR_MAPS = {
    "MAP_HEADER_ROUTE_201": (8, 10),
    "MAP_HEADER_LAKE_VERITY": (8, 10),
    "MAP_HEADER_LAKE_VERITY_LOW_WATER": (8, 10),
}

# Honey tree sub-table rolled when the 4% honey slot hits in rustling grass.
HONEY_TREE_SLOTS: list[dict[str, object]] = [
    {"species": "SPECIES_COMBEE", "weight": 32, "minLevel": 0},
    {"species": "SPECIES_BURMY", "weight": 26, "minLevel": 0},
    {"species": "SPECIES_WURMPLE", "weight": 13, "minLevel": 0},
    {"species": "SPECIES_CHERUBI", "weight": 13, "minLevel": 0},
    {"species": "SPECIES_AIPOM", "weight": 12, "minLevel": 0},
    {"species": "SPECIES_HERACROSS", "weight": 3, "minLevel": 0},
    {"species": "SPECIES_MUNCHLAX", "weight": 1, "minLevel": 0},
]

# Dust cloud items (exact Platinum Reforged weights, sum = 100).
DUST_CLOUD_ITEMS: list[dict[str, object]] = [
    {"item": "ITEM_HEART_SCALE", "weight": 16},
    {"item": "ITEM_STARDUST", "weight": 12},
    {"item": "ITEM_RED_SHARD", "weight": 11},
    {"item": "ITEM_BLUE_SHARD", "weight": 11},
    {"item": "ITEM_YELLOW_SHARD", "weight": 11},
    {"item": "ITEM_GREEN_SHARD", "weight": 11},
    {"item": "ITEM_HARD_STONE", "weight": 6},
    {"item": "ITEM_STAR_PIECE", "weight": 5},
    {"item": "ITEM_EVERSTONE", "weight": 5},
    {"item": "ITEM_RARE_BONE", "weight": 2},
    {"item": "ITEM_SUN_STONE", "weight": 1},
    {"item": "ITEM_MOON_STONE", "weight": 1},
    {"item": "ITEM_FIRE_STONE", "weight": 1},
    {"item": "ITEM_THUNDERSTONE", "weight": 1},
    {"item": "ITEM_WATER_STONE", "weight": 1},
    {"item": "ITEM_LEAF_STONE", "weight": 1},
    {"item": "ITEM_SHINY_STONE", "weight": 1},
    {"item": "ITEM_DUSK_STONE", "weight": 1},
    {"item": "ITEM_DAWN_STONE", "weight": 1},
    {"item": "ITEM_OVAL_STONE", "weight": 1},
]

# Cycling Road Shadow items (Gen 4 EV vitamin equivalents to BW2 Feathers + Pearl, sum = 100).
SHADOW_ITEMS: list[dict[str, object]] = [
    {"item": "ITEM_HP_UP", "weight": 15},
    {"item": "ITEM_PROTEIN", "weight": 15},
    {"item": "ITEM_IRON", "weight": 15},
    {"item": "ITEM_CALCIUM", "weight": 15},
    {"item": "ITEM_ZINC", "weight": 15},
    {"item": "ITEM_CARBOS", "weight": 15},
    {"item": "ITEM_PEARL", "weight": 10},
]


def normalize_ascii(text: str) -> str:
    text = text.replace("\u2013", "-").replace("\u2014", "-").replace("\u00b7", "/")
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return " ".join(text.split())


def species_name_to_const(raw_name: str) -> str:
    name = normalize_ascii(raw_name)
    if name == "Honey tree Pokemon":
        return HONEY_SENTINEL
    const = name.upper().replace(". ", "_").replace(".", "").replace("-", "_").replace(" ", "_").replace("'", "")
    return f"SPECIES_{const}"


def parse_level_range(raw_lv: str) -> tuple[int, int]:
    lv = normalize_ascii(raw_lv)
    if "-" in lv:
        lo_s, hi_s = lv.split("-", 1)
        return int(lo_s), int(hi_s)
    v = int(lv)
    return v, v


class EncounterPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.h2: str | None = None
        self.h3: str | None = None
        self.cur_tag: str | None = None
        self.buf: list[str] = []
        self.tab_labels: dict[str, str] = {}
        self.cur_tab_id: str | None = None
        self.cur_panel_label: str | None = None
        self.last_p: str | None = None
        self.in_table = False
        self.cur_table: list[list[str]] = []
        self.cur_row: list[str] = []
        self.in_cell = False
        self.cell_buf: list[str] = []
        self.records: list[dict[str, object]] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        d = dict(attrs)
        if tag in ("script", "style", "svg") or "sr-only" in (d.get("class") or ""):
            self.skip += 1
            return
        if self.skip:
            return
        if tag in ("h2", "h3", "h4"):
            self.cur_tag = tag
            self.buf = []
        elif tag == "a" and d.get("role") == "tab":
            self.cur_tag = "tab"
            self.cur_tab_id = d.get("id")
            self.buf = []
        elif tag == "div" and d.get("role") == "tabpanel":
            lid = d.get("aria-labelledby") or ""
            self.cur_panel_label = self.tab_labels.get(lid, lid)
        elif tag == "p" and not self.in_table:
            self.cur_tag = "p"
            self.buf = []
        elif tag == "table":
            self.in_table = True
            self.cur_table = []
        elif tag == "tr" and self.in_table:
            self.cur_row = []
        elif tag in ("td", "th") and self.in_table:
            self.in_cell = True
            self.cell_buf = []

    def handle_endtag(self, tag: str) -> None:
        if self.skip:
            if tag in ("script", "style", "svg", "span"):
                self.skip = max(0, self.skip - 1)
            return
        if tag in ("h2", "h3", "h4") and self.cur_tag == tag:
            txt = normalize_ascii("".join(self.buf))
            if tag == "h2":
                self.h2 = txt
                self.h3 = None
            elif tag == "h3":
                self.h3 = txt
            self.cur_tag = None
            self.cur_panel_label = None
            self.last_p = None
        elif tag == "a" and self.cur_tag == "tab":
            if self.cur_tab_id is not None:
                self.tab_labels[self.cur_tab_id] = normalize_ascii("".join(self.buf))
            self.cur_tag = None
        elif tag == "p" and self.cur_tag == "p":
            self.last_p = normalize_ascii("".join(self.buf))
            self.cur_tag = None
        elif tag in ("td", "th") and self.in_cell:
            self.cur_row.append(normalize_ascii("".join(self.cell_buf)))
            self.in_cell = False
        elif tag == "tr" and self.in_table:
            if self.cur_row:
                self.cur_table.append(self.cur_row)
        elif tag == "table" and self.in_table:
            label = self.cur_panel_label or self.last_p or "unknown"
            self.records.append(
                {
                    "location": self.h3 or self.h2 or "unknown",
                    "label": label,
                    "rows": self.cur_table,
                }
            )
            self.in_table = False

    def handle_data(self, data: str) -> None:
        if self.skip:
            return
        if self.cur_tag:
            self.buf.append(data)
        if self.in_cell:
            self.cell_buf.append(data)


def extract_from_ref_repo(ref_repo: Path) -> dict[str, object]:
    pages = (
        "encounters/routes/index.html",
        "encounters/caves/index.html",
        "encounters/places/index.html",
    )
    records: list[dict[str, object]] = []
    for page in pages:
        html = subprocess.check_output(
            ["git", "-C", str(ref_repo), "show", f"origin/gh-pages:{page}"],
            text=True,
        )
        m = re.search(r"<main[^>]*>(.*?)</main>", html, re.S)
        if not m:
            raise RuntimeError(f"Could not find <main> in {page}")
        parser = EncounterPageParser()
        parser.feed(m.group(1))
        records.extend(parser.records)

    maps_data: dict[str, dict[str, object]] = {}
    seen_locations: set[str] = set()

    for rec in records:
        loc = str(rec["location"])
        label = str(rec["label"])
        rows = rec["rows"]
        assert isinstance(rows, list)
        if loc not in LOCATION_TO_MAPS:
            raise RuntimeError(f"Unmapped Platinum Reforged location: {loc!r}")
        if label not in LABEL_TO_KEY:
            raise RuntimeError(f"Unexpected phenomenon label: {label!r} in {loc!r}")
        seen_locations.add(loc)

        phen_key = LABEL_TO_KEY[label]
        data_rows = rows[1:]
        parsed_lvs = [parse_level_range(r[2]) for r in data_rows]
        table_min = min(lo for lo, _ in parsed_lvs)

        slots: list[dict[str, object]] = []
        total_w = 0
        for row, (lo, _hi) in zip(data_rows, parsed_lvs):
            sp = species_name_to_const(row[0])
            weight = int(row[3].rstrip("%"))
            total_w += weight
            evo_floor = SPECIES_EVOLUTION_FLOOR.get(sp, 0)
            explicit_floor = lo if lo > table_min else 0
            min_lv = max(evo_floor, explicit_floor)
            slots.append({"species": sp, "weight": weight, "minLevel": min_lv})

        if total_w != 100:
            raise RuntimeError(f"Weights in {loc} [{label}] sum to {total_w}, expected 100")

        for map_header in LOCATION_TO_MAPS[loc]:
            entry = maps_data.setdefault(map_header, {})
            if phen_key in entry:
                raise RuntimeError(f"Duplicate table for {map_header} [{phen_key}]")
            floor_min, floor_max = (0, 0)
            if phen_key == "grass" and map_header in EARLY_GRASS_LEVEL_FLOOR_MAPS:
                floor_min, floor_max = EARLY_GRASS_LEVEL_FLOOR_MAPS[map_header]
            entry[phen_key] = {
                "floorMinLv": floor_min,
                "floorMaxLv": floor_max,
                "slots": slots,
            }

    unused_locs = sorted(set(LOCATION_TO_MAPS) - seen_locations)
    if unused_locs:
        raise RuntimeError(f"Unused LOCATION_TO_MAPS keys: {unused_locs}")

    return {
        "source": "Platinum Reforged (origin/gh-pages encounters/{routes,caves,places})",
        "eternaChateauClearing": {"minX": 60, "maxZ": 32},
        "honeyTreeSlots": HONEY_TREE_SLOTS,
        "dustCloudItems": DUST_CLOUD_ITEMS,
        "shadowItems": SHADOW_ITEMS,
        "maps": dict(sorted(maps_data.items())),
    }


def load_constants(path: Path) -> set[str]:
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def validate_data(data: dict[str, object], repo_root: Path) -> dict[str, int]:
    valid_maps = load_constants(repo_root / "generated/map_headers.txt")
    valid_species = load_constants(repo_root / "generated/species.txt")
    valid_items = load_constants(repo_root / "generated/items.txt")

    errors: list[str] = []
    maps_data = data["maps"]
    assert isinstance(maps_data, dict)

    table_counts = {"grass": 0, "dust": 0, "surf": 0, "fish": 0, "shadow_day": 0, "shadow_night": 0}
    species_used: set[str] = set()
    items_used: set[str] = set()

    for map_header, entry in maps_data.items():
        if map_header not in valid_maps:
            errors.append(f"Invalid map header: {map_header}")
        assert isinstance(entry, dict)
        for key, tbl in entry.items():
            if key not in table_counts:
                errors.append(f"Unknown table key {key} on {map_header}")
                continue
            table_counts[key] += 1
            assert isinstance(tbl, dict)
            slots = tbl["slots"]
            assert isinstance(slots, list)
            wsum = 0
            for slot in slots:
                sp = str(slot["species"])
                w = int(slot["weight"])
                wsum += w
                if sp != HONEY_SENTINEL:
                    species_used.add(sp)
                    if sp not in valid_species:
                        errors.append(f"Invalid species {sp} in {map_header}.{key}")
            if wsum != 100:
                errors.append(f"Weight sum {wsum} != 100 in {map_header}.{key}")

    honey_slots = data["honeyTreeSlots"]
    assert isinstance(honey_slots, list)
    honey_w = 0
    for slot in honey_slots:
        sp = str(slot["species"])
        honey_w += int(slot["weight"])
        species_used.add(sp)
        if sp not in valid_species:
            errors.append(f"Invalid honey tree species: {sp}")
    if honey_w != 100:
        errors.append(f"Honey tree weight sum {honey_w} != 100")

    for list_name in ("dustCloudItems", "shadowItems"):
        item_list = data[list_name]
        assert isinstance(item_list, list)
        iw = 0
        for row in item_list:
            it = str(row["item"])
            iw += int(row["weight"])
            items_used.add(it)
            if it not in valid_items:
                errors.append(f"Invalid item {it} in {list_name}")
        if iw != 100:
            errors.append(f"Item weight sum {iw} != 100 in {list_name}")

    if errors:
        raise RuntimeError("Validation failed:\n  " + "\n  ".join(errors))

    return {
        "maps": len(maps_data),
        "tables": sum(table_counts.values()),
        "grass": table_counts["grass"],
        "dust": table_counts["dust"],
        "surf": table_counts["surf"],
        "fish": table_counts["fish"],
        "shadow_day": table_counts["shadow_day"],
        "shadow_night": table_counts["shadow_night"],
        "unique_species": len(species_used),
        "unique_items": len(items_used),
    }


def generate_header() -> str:
    return (
        "#ifndef POKEPLATINUM_OVERLAY006_PHENOMENA_TABLES_H\n"
        "#define POKEPLATINUM_OVERLAY006_PHENOMENA_TABLES_H\n"
        "\n"
        "#include <nitro/types.h>\n"
        "\n"
        '#include "generated/items.h"\n'
        '#include "generated/map_headers.h"\n'
        '#include "generated/species.h"\n'
        "\n"
        "enum PhenomenonType {\n"
        "    PHENOMENON_NONE = 0,\n"
        "    PHENOMENON_GRASS = 1,\n"
        "    PHENOMENON_DUST = 2,\n"
        "    PHENOMENON_WATER = 3,\n"
        "    PHENOMENON_SHADOW = 4,\n"
        "};\n"
        "\n"
        "typedef struct PhenomenonSlot {\n"
        "    u16 species;\n"
        "    u8 weight;\n"
        "    u8 minLevel;\n"
        "} PhenomenonSlot;\n"
        "\n"
        "typedef struct PhenomenonItemSlot {\n"
        "    u16 item;\n"
        "    u8 weight;\n"
        "} PhenomenonItemSlot;\n"
        "\n"
        "BOOL PhenomenaTables_MapHasPhenomenon(int mapHeaderID, enum PhenomenonType type);\n"
        "BOOL PhenomenaTables_RollEncounter(int mapHeaderID, enum PhenomenonType type, BOOL isFishing, BOOL isNight, int playerX, int playerZ, int baseMinLv, int baseMaxLv, u16 *outSpecies, u8 *outLevel);\n"
        "u16 PhenomenaTables_RollItem(enum PhenomenonType type, int mapHeaderID);\n"
        "\n"
        "#endif\n"
    )


def generate_source(data: dict[str, object]) -> str:
    maps_data = data["maps"]
    assert isinstance(maps_data, dict)
    chateau = data["eternaChateauClearing"]
    assert isinstance(chateau, dict)

    # Deduplicate slot arrays and PhenomenonSlotTable descriptors so there are zero unused statics.
    slots_key_to_name: dict[tuple[tuple[str, int, int], ...], str] = {}
    slots_defs: list[tuple[str, list[dict[str, object]]]] = []

    table_key_to_name: dict[tuple[str, int, int], str] = {}
    table_defs: list[tuple[str, str, int, int, int]] = []

    def intern_table(tbl: dict[str, object]) -> str:
        slots = tbl["slots"]
        assert isinstance(slots, list)
        s_key = tuple((str(s["species"]), int(s["weight"]), int(s["minLevel"])) for s in slots)
        if s_key not in slots_key_to_name:
            s_name = f"sPhenomenonSlots_{len(slots_defs)}"
            slots_key_to_name[s_key] = s_name
            slots_defs.append((s_name, slots))
        else:
            s_name = slots_key_to_name[s_key]

        fmin = int(tbl.get("floorMinLv", 0))
        fmax = int(tbl.get("floorMaxLv", 0))
        t_key = (s_name, fmin, fmax)
        if t_key not in table_key_to_name:
            t_name = f"sPhenomenonTable_{len(table_defs)}"
            table_key_to_name[t_key] = t_name
            table_defs.append((t_name, s_name, len(slots), fmin, fmax))
        return table_key_to_name[t_key]

    map_rows: list[tuple[str, str, str, str, str, str, str]] = []
    for map_header, entry in maps_data.items():
        assert isinstance(entry, dict)
        refs = []
        for k in ("grass", "dust", "surf", "fish", "shadow_day", "shadow_night"):
            if k in entry:
                t_name = intern_table(entry[k])  # type: ignore[arg-type]
                refs.append(f"&{t_name}")
            else:
                refs.append("NULL")
        map_rows.append((map_header, refs[0], refs[1], refs[2], refs[3], refs[4], refs[5]))

    lines: list[str] = [
        "/* AUTO-GENERATED by tools/phenomena/generate_tables.py - DO NOT EDIT BY HAND. */",
        "",
        '#include "overlay006/phenomena_tables.h"',
        "",
        "#include <nitro.h>",
        "#include <stddef.h>",
        "",
        '#include "math_util.h"',
        "",
        f"#define {HONEY_SENTINEL} 0xFFFF",
        f"#define ETERNA_CHATEAU_MIN_X {int(chateau['minX'])}",
        f"#define ETERNA_CHATEAU_MAX_Z {int(chateau['maxZ'])}",
        "",
        "typedef struct PhenomenonSlotTable {",
        "    const PhenomenonSlot *slots;",
        "    u8 count;",
        "    u8 floorMinLv;",
        "    u8 floorMaxLv;",
        "} PhenomenonSlotTable;",
        "",
        "typedef struct PhenomenonMapEntry {",
        "    u16 mapHeaderID;",
        "    const PhenomenonSlotTable *grass;",
        "    const PhenomenonSlotTable *dust;",
        "    const PhenomenonSlotTable *surf;",
        "    const PhenomenonSlotTable *fish;",
        "    const PhenomenonSlotTable *shadowDay;",
        "    const PhenomenonSlotTable *shadowNight;",
        "} PhenomenonMapEntry;",
        "",
        "static const PhenomenonSlot sHoneyTreeSlots[] = {",
    ]

    for s in data["honeyTreeSlots"]:  # type: ignore[union-attr]
        lines.append(f"    {{ {s['species']}, {int(s['weight'])}, {int(s['minLevel'])} }},")
    lines.append("};")
    lines.append("")

    lines.append("static const PhenomenonItemSlot sDustCloudItems[] = {")
    for row in data["dustCloudItems"]:  # type: ignore[union-attr]
        lines.append(f"    {{ {row['item']}, {int(row['weight'])} }},")
    lines.append("};")
    lines.append("")

    lines.append("static const PhenomenonItemSlot sShadowItems[] = {")
    for row in data["shadowItems"]:  # type: ignore[union-attr]
        lines.append(f"    {{ {row['item']}, {int(row['weight'])} }},")
    lines.append("};")
    lines.append("")

    for s_name, slots in slots_defs:
        lines.append(f"static const PhenomenonSlot {s_name}[] = {{")
        for s in slots:
            lines.append(f"    {{ {s['species']}, {int(s['weight'])}, {int(s['minLevel'])} }},")
        lines.append("};")
        lines.append("")

    for t_name, s_name, count, fmin, fmax in table_defs:
        lines.append(f"static const PhenomenonSlotTable {t_name} = {{ {s_name}, {count}, {fmin}, {fmax} }};")
    lines.append("")

    lines.append("static const PhenomenonMapEntry sMapPhenomenaEntries[] = {")
    for map_header, grass, dust, surf, fish, sday, snight in map_rows:
        lines.append(f"    {{ {map_header}, {grass}, {dust}, {surf}, {fish}, {sday}, {snight} }},")
    lines.append("};")
    lines.append("")

    lines.extend(
        [
            "static const PhenomenonMapEntry *FindMapEntry(int mapHeaderID)",
            "{",
            "    size_t count = sizeof(sMapPhenomenaEntries) / sizeof(sMapPhenomenaEntries[0]);",
            "    for (size_t i = 0; i < count; i++) {",
            "        if ((int)sMapPhenomenaEntries[i].mapHeaderID == mapHeaderID) {",
            "            return &sMapPhenomenaEntries[i];",
            "        }",
            "    }",
            "    return NULL;",
            "}",
            "",
            "static const PhenomenonSlot *RollWeightedSlot(const PhenomenonSlot *slots, u8 count, u16 excludeSpecies)",
            "{",
            "    u32 totalWeight = 0;",
            "    for (u8 i = 0; i < count; i++) {",
            "        if (excludeSpecies != SPECIES_NONE && slots[i].species == excludeSpecies) {",
            "            continue;",
            "        }",
            "        totalWeight += slots[i].weight;",
            "    }",
            "    if (totalWeight == 0) {",
            "        return NULL;",
            "    }",
            "",
            "    u32 roll = (u32)(LCRNG_Next() % totalWeight);",
            "    u32 acc = 0;",
            "    for (u8 i = 0; i < count; i++) {",
            "        if (excludeSpecies != SPECIES_NONE && slots[i].species == excludeSpecies) {",
            "            continue;",
            "        }",
            "        acc += slots[i].weight;",
            "        if (roll < acc) {",
            "            return &slots[i];",
            "        }",
            "    }",
            "    return &slots[count - 1];",
            "}",
            "",
            "BOOL PhenomenaTables_MapHasPhenomenon(int mapHeaderID, enum PhenomenonType type)",
            "{",
            "    const PhenomenonMapEntry *entry = FindMapEntry(mapHeaderID);",
            "    if (entry == NULL) {",
            "        return FALSE;",
            "    }",
            "",
            "    switch (type) {",
            "    case PHENOMENON_GRASS:",
            "        return entry->grass != NULL;",
            "    case PHENOMENON_DUST:",
            "        return entry->dust != NULL;",
            "    case PHENOMENON_WATER:",
            "        return (entry->surf != NULL) || (entry->fish != NULL);",
            "    case PHENOMENON_SHADOW:",
            "        return (entry->shadowDay != NULL) || (entry->shadowNight != NULL);",
            "    default:",
            "        return FALSE;",
            "    }",
            "}",
            "",
            "BOOL PhenomenaTables_RollEncounter(int mapHeaderID, enum PhenomenonType type, BOOL isFishing, BOOL isNight, int playerX, int playerZ, int baseMinLv, int baseMaxLv, u16 *outSpecies, u8 *outLevel)",
            "{",
            "    if (outSpecies == NULL || outLevel == NULL) {",
            "        return FALSE;",
            "    }",
            "",
            "    const PhenomenonMapEntry *entry = FindMapEntry(mapHeaderID);",
            "    if (entry == NULL) {",
            "        return FALSE;",
            "    }",
            "",
            "    const PhenomenonSlotTable *table = NULL;",
            "    switch (type) {",
            "    case PHENOMENON_GRASS:",
            "        table = entry->grass;",
            "        break;",
            "    case PHENOMENON_DUST:",
            "        table = entry->dust;",
            "        break;",
            "    case PHENOMENON_WATER:",
            "        table = isFishing ? entry->fish : entry->surf;",
            "        break;",
            "    case PHENOMENON_SHADOW:",
            "        table = isNight ? entry->shadowNight : entry->shadowDay;",
            "        break;",
            "    default:",
            "        return FALSE;",
            "    }",
            "",
            "    if (table == NULL || table->slots == NULL || table->count == 0) {",
            "        return FALSE;",
            "    }",
            "",
            "    u16 excludeSpecies = SPECIES_NONE;",
            "    if (mapHeaderID == MAP_HEADER_ETERNA_FOREST && type == PHENOMENON_GRASS) {",
            "        BOOL inChateauClearing = (playerX >= ETERNA_CHATEAU_MIN_X && playerZ <= ETERNA_CHATEAU_MAX_Z);",
            "        if (!inChateauClearing) {",
            "            excludeSpecies = SPECIES_ROTOM;",
            "        }",
            "    }",
            "",
            "    const PhenomenonSlot *slot = RollWeightedSlot(table->slots, table->count, excludeSpecies);",
            "    if (slot == NULL) {",
            "        return FALSE;",
            "    }",
            "",
            "    u16 species = slot->species;",
            "    u8 slotMinLv = slot->minLevel;",
            f"    if (species == {HONEY_SENTINEL}) {{",
            "        const PhenomenonSlot *honeySlot = RollWeightedSlot(sHoneyTreeSlots, (u8)(sizeof(sHoneyTreeSlots) / sizeof(sHoneyTreeSlots[0])), SPECIES_NONE);",
            "        if (honeySlot == NULL) {",
            "            return FALSE;",
            "        }",
            "        species = honeySlot->species;",
            "        if (honeySlot->minLevel > slotMinLv) {",
            "            slotMinLv = honeySlot->minLevel;",
            "        }",
            "    }",
            "",
            "    int lo = baseMinLv + 2;",
            "    int hi = baseMaxLv + 2;",
            "    if (table->floorMinLv > 0 && lo < (int)table->floorMinLv) {",
            "        lo = (int)table->floorMinLv;",
            "    }",
            "    if (table->floorMaxLv > 0 && hi < (int)table->floorMaxLv) {",
            "        hi = (int)table->floorMaxLv;",
            "    }",
            "    if (slotMinLv > 0 && lo < (int)slotMinLv) {",
            "        lo = (int)slotMinLv;",
            "    }",
            "    if (lo < 1) {",
            "        lo = 1;",
            "    }",
            "    if (lo > 100) {",
            "        lo = 100;",
            "    }",
            "    if (hi > 100) {",
            "        hi = 100;",
            "    }",
            "    if (hi < lo) {",
            "        hi = lo;",
            "    }",
            "",
            "    u8 level = (u8)(lo + (int)(LCRNG_Next() % (u32)(hi - lo + 1)));",
            "    *outSpecies = species;",
            "    *outLevel = level;",
            "    return TRUE;",
            "}",
            "",
            "u16 PhenomenaTables_RollItem(enum PhenomenonType type, int mapHeaderID)",
            "{",
            "    (void)mapHeaderID;",
            "    const PhenomenonItemSlot *slots = NULL;",
            "    size_t count = 0;",
            "",
            "    if (type == PHENOMENON_DUST) {",
            "        slots = sDustCloudItems;",
            "        count = sizeof(sDustCloudItems) / sizeof(sDustCloudItems[0]);",
            "    } else if (type == PHENOMENON_SHADOW) {",
            "        slots = sShadowItems;",
            "        count = sizeof(sShadowItems) / sizeof(sShadowItems[0]);",
            "    } else {",
            "        return ITEM_NONE;",
            "    }",
            "",
            "    u32 totalWeight = 0;",
            "    for (size_t i = 0; i < count; i++) {",
            "        totalWeight += slots[i].weight;",
            "    }",
            "    if (totalWeight == 0) {",
            "        return ITEM_NONE;",
            "    }",
            "",
            "    u32 roll = (u32)(LCRNG_Next() % totalWeight);",
            "    u32 acc = 0;",
            "    for (size_t i = 0; i < count; i++) {",
            "        acc += slots[i].weight;",
            "        if (roll < acc) {",
            "            return slots[i].item;",
            "        }",
            "    }",
            "    return slots[count - 1].item;",
            "}",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Phenomena encounter and item tables.")
    parser.add_argument(
        "--ref-repo",
        type=Path,
        default=DEFAULT_REF_REPO,
        help="Path to platinum-reforged-anvil repo (default: /tmp/platinum-reforged-anvil)",
    )
    parser.add_argument(
        "--from-json",
        action="store_true",
        help="Read res/field/phenomena_tables.json instead of extracting from platinum-reforged-anvil",
    )
    args = parser.parse_args()

    json_path = REPO_ROOT / "res/field/phenomena_tables.json"
    header_path = REPO_ROOT / "include/overlay006/phenomena_tables.h"
    source_path = REPO_ROOT / "src/overlay006/phenomena_tables.c"

    if not args.from_json and args.ref_repo.exists():
        data = extract_from_ref_repo(args.ref_repo)
        stats = validate_data(data, REPO_ROOT)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    else:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        stats = validate_data(data, REPO_ROOT)

    header_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.parent.mkdir(parents=True, exist_ok=True)
    header_path.write_text(generate_header(), encoding="utf-8")
    source_path.write_text(generate_source(data), encoding="utf-8")

    print(
        f"Generated Phenomena tables: {stats['maps']} maps, {stats['tables']} tables "
        f"(grass={stats['grass']}, dust={stats['dust']}, surf={stats['surf']}, "
        f"fish={stats['fish']}, shadow_day={stats['shadow_day']}, shadow_night={stats['shadow_night']}), "
        f"{stats['unique_species']} unique species, {stats['unique_items']} unique items."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
