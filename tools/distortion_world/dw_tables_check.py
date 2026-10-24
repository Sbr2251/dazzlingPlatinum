#!/usr/bin/env python3
"""Host check over the DW puzzle tables (engine-a) and actor tables
(engine-b): every dw_puzzle_<map>.c table in src/overlay009/ plus the
actor table(s).

The checker is a small C program, generated here and compiled against
the real headers (same pattern as tools/distortion_world/
dw_actors_test.c), so it reads the tables exactly as the game does --
no re-parsed struct layouts to drift. It compiles the table .c files
themselves (plus dw_puzzle_actors.c in DW_ACTORS_HOST_TEST mode for
the actor test table).

Rules (docs/distortion_world/actors_design.md + the engine headers).
An oversize count is reported once by its cap CHECK and its entries
are then skipped (puzzle tables) or the loop clamps to the cap
(actor tables, whose arrays are inline). A puzzle count over its cap
means the count lies about the pointed-to array, so reading its
entries would read past the array; the helpers likewise treat an
oversize array as absent.
  puzzle tables:
    - count caps: groupCount <= 8, sigilCount <= 16, runeCount <= 8,
      currentCount <= 16, checkpointCount <= 8 (DW_PUZZLE_MAX_*)
    - group tileCount <= DW_PUZZLE_MAX_GROUP_TILES (32)
    - explicit tileCount <= DW_PUZZLE_MAX_TILES (32)
    - sigil kind valid; non-RESET targetGroup < groupCount; SET setValue 0/1
    - checkpointCount >= 1 (checkpoint 0 is the entry snapshot)
    - current dirs, rune surfaces/facing in range
    - no duplicate explicit-override tiles
  actor tables:
    - stoneCount <= 4, padCount <= 4, shadow tileCount <= 16,
      edgeCount <= 4/stone, protectedCount <= 8, echo sigils <= 8
    - shadow lane tiles all on one surface, consecutive tiles adjacent
      (seam-corner proxy: a jump teleports the shadow across a seam);
      stone start tiles unique; pad tiles unique; pad totems in range
    - echo mirrorAxis (geometric: MIRROR_X/Y/Z -> AXIS_X/Y/Z) != echoAxis
    - every actor tile surface in range 0..4 (actor surfaces are
      explicit: exact-equality match, so ANY (0xFF) never matches);
      group tiles too (puzzle ANY allowed there)
  pairs (engine registry in dw_puzzle.c first, then same-file, then the
  known test pair):
    - landing tiles never current tiles; landing-tile overrides VOID-only
    - landing tiles in no group, and never sigil / pad / checkpoint /
      rune tiles (landing tiles are reserved)
    - each landing tile belongs to at most one stone
    - stone starts never on a pad / protected / echo-sigil / landing tile
      (no exemptions: a start may not sit on another stone's landing)
    - edges never on a protected / pad / echo-sigil / landing tile
      (edges are pushed into, then fall; a protected edge blocks the fall)
    - shadow lane tiles never checkpoint tiles (entry = checkpoint 0);
      totem/talk spots are map scripts, not tables -- they need
      map-script review, the validator cannot see them
    - pad tiles never checkpoint / rune / current tiles
  production-only (paired puzzle testOnly == 0; test tables are
  fixtures for the host test and the engine's test mode):
    - every GROUND actor tile EXCEPT landings (stone start/edge,
      shadow lane, echo sigil, pad, protected) has an explicit
      engine-a state: a group tile or an explicit override with
      state != DEFAULT (GROUND has no stock grid, so DEFAULT always
      reads BLOCKED, fail closed). Landings are exempt: section 3
      permits a landing to use its base kind (VOID for a gap,
      WALKABLE for a platform); the VOID-only override rule still
      applies if a landing override is present. Non-GROUND actor
      tiles resolve via the stock grid on the player's surface --
      no walkability query in the engine is cross-surface (TryPush,
      the step hook, Currents, and the slide all query the player's
      surface; shadow/echo/pad checks are TileEq), so the
      cross-surface BLOCKED is a latent contract, not an
      enforceable table rule.
    - shadow beatFrames >= 30 (Arc 2 rule; the test table uses a 6-frame
      beat on purpose)
    - every pad tile has a sigil in the engine-a table (pads are sigil
      tiles; the glue suppresses the auto-fire)
  Not checked: a true seam-corner rule needs the seam geometry from
  tw_arc (not in the tables): a cross-surface FLOOR/GROUND tile pair
  is legal (a floating platform over base terrain shares coords), so
  no same-coords cross-surface check is done.

Usage:
  python3 tools/distortion_world/dw_tables_check.py [--keep] [--out DIR]
Exit 1 on any failure. --keep leaves the generated checker.c +
binary in --out (default: a temp dir, cleaned up).
"""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
OV9 = REPO / "src" / "overlay009"
ACTORS_C = OV9 / "dw_puzzle_actors.c"

# (puzzle table, actor table) pairs that live in different files: the
# actor test table is written against the Ravaged Path test puzzle
# table (see the table's own comment). Same-file pairs are paired by
# file automatically.
EXTRA_PAIRS = [("gDwPuzzleTestTable", "gDwActorsTestTable")]

CHECKER_C = r"""
#define DW_ACTORS_HOST_TEST 1
#include <stdio.h>
#include <string.h>

#include "overlay009/dw_puzzle.h"
#include "overlay009/dw_puzzle_actors.h"

static int g_checks, g_failures;
static const char *g_table;

#define CHECK(cond, ...) do { \
    g_checks++; \
    if (!(cond)) { \
        g_failures++; \
        printf("FAIL %s: ", g_table); \
        printf(__VA_ARGS__); \
        printf("\n"); \
    } \
} while (0)

/* Coords + surface, with ANY (0xFF) matching anything. */
static int same_tile(int x1, int y1, int z1, int s1,
                     int x2, int y2, int z2, int s2)
{
    return x1 == x2 && y1 == y2 && z1 == z2
        && (s1 == 0xFF || s2 == 0xFF || s1 == s2);
}

static int valid_surface(int s)
{
    return s <= DW_PUZZLE_SURFACE_GROUND || s == DW_PUZZLE_SURFACE_ANY;
}

/* Actor tiles carry EXPLICIT surfaces (actors_design.md section 2):
 * the actor core compares surfaces with exact equality (TileEq),
 * so DW_ACTOR_SURFACE_ANY (0xFF) would never match a real tile.
 * An actor surface must be a real surface, 0..4. */
static int valid_actor_surface(int s)
{
    return s <= DW_ACTOR_SURFACE_GROUND;
}

/* Clamp a declared count to its array size: an oversize count is
 * reported once by its cap CHECK, and every loop below uses the
 * clamped value so the checker never reads past a fixed array.
 * (Actor tables hold their arrays inline, so clamping to the cap is
 * always in-bounds there. Puzzle tables hold pointers: a count over
 * the cap means the count lies about the array, so the puzzle
 * helpers below treat an oversize array as absent -- its entries
 * are untrustworthy -- and check_puzzle skips its entry checks.) */
#define CLAMP(n, cap) ((n) < (cap) ? (n) : (cap))

static const DwPuzzleTile *find_explicit(const DwPuzzleTable *t,
                                         int x, int y, int z, int s)
{
    int i, n = t->tileCount;
    if (n > DW_PUZZLE_MAX_TILES)
        return NULL;
    for (i = 0; i < n; i++)
        if (same_tile(t->tiles[i].x, t->tiles[i].y, t->tiles[i].z,
                      t->tiles[i].surface, x, y, z, s))
            return &t->tiles[i];
    return NULL;
}

static int is_group_tile(const DwPuzzleTable *t, int x, int y, int z, int s)
{
    int g, i;
    if (t->groupCount > DW_PUZZLE_MAX_GROUPS)
        return 0;
    for (g = 0; g < t->groupCount; g++) {
        int nt = t->groups[g].tileCount;
        if (nt > DW_PUZZLE_MAX_GROUP_TILES)
            continue; /* untrustworthy group, already failed on its cap */
        for (i = 0; i < nt; i++)
            if (same_tile(t->groups[g].tiles[i].x, t->groups[g].tiles[i].y,
                          t->groups[g].tiles[i].z, t->groups[g].tiles[i].surface,
                          x, y, z, s))
                return 1;
    }
    return 0;
}

static int is_current(const DwPuzzleTable *t, int x, int y, int z, int s)
{
    int i;
    if (t->currentCount > DW_PUZZLE_MAX_CURRENTS)
        return 0;
    for (i = 0; i < t->currentCount; i++)
        if (same_tile(t->currents[i].x, t->currents[i].y, t->currents[i].z,
                      t->currents[i].surface, x, y, z, s))
            return 1;
    return 0;
}

static int is_sigil(const DwPuzzleTable *t, int x, int y, int z, int s)
{
    int i;
    if (t->sigilCount > DW_PUZZLE_MAX_SIGILS)
        return 0;
    for (i = 0; i < t->sigilCount; i++)
        if (same_tile(t->sigils[i].x, t->sigils[i].y, t->sigils[i].z,
                      t->sigils[i].surface, x, y, z, s))
            return 1;
    return 0;
}

static int is_checkpoint(const DwPuzzleTable *t, int x, int y, int z, int s)
{
    int i;
    if (t->checkpointCount > DW_PUZZLE_MAX_CHECKPOINTS)
        return 0;
    for (i = 0; i < t->checkpointCount; i++)
        if (same_tile(t->checkpoints[i].x, t->checkpoints[i].y,
                      t->checkpoints[i].z, t->checkpoints[i].surface,
                      x, y, z, s))
            return 1;
    return 0;
}

static int is_rune(const DwPuzzleTable *t, int x, int y, int z, int s)
{
    int i;
    if (t->runeCount > DW_PUZZLE_MAX_RUNES)
        return 0;
    for (i = 0; i < t->runeCount; i++)
        if (same_tile(t->runes[i].x, t->runes[i].y, t->runes[i].z,
                      t->runes[i].surface, x, y, z, s))
            return 1;
    return 0;
}

static void check_puzzle(const char *name, const DwPuzzleTable *t)
{
    int i, j;
    /* Count caps (DW_PUZZLE_MAX_*). An oversize count is reported once
     * above; its entries are skipped -- the count lies about the
     * pointed-to array, so reading them would read past it. */
    int ngroups = t->groupCount <= DW_PUZZLE_MAX_GROUPS ? t->groupCount : 0;
    int ntiles = t->tileCount <= DW_PUZZLE_MAX_TILES ? t->tileCount : 0;
    int ncheckpoints = t->checkpointCount <= DW_PUZZLE_MAX_CHECKPOINTS
        ? t->checkpointCount : 0;
    int nsigils = t->sigilCount <= DW_PUZZLE_MAX_SIGILS ? t->sigilCount : 0;
    int nrunes = t->runeCount <= DW_PUZZLE_MAX_RUNES ? t->runeCount : 0;
    int ncurrents = t->currentCount <= DW_PUZZLE_MAX_CURRENTS
        ? t->currentCount : 0;
    g_table = name;
    CHECK(t->groupCount <= DW_PUZZLE_MAX_GROUPS,
          "%d groups, cap %d", t->groupCount, DW_PUZZLE_MAX_GROUPS);
    CHECK(t->sigilCount <= DW_PUZZLE_MAX_SIGILS,
          "%d sigils, cap %d", t->sigilCount, DW_PUZZLE_MAX_SIGILS);
    CHECK(t->runeCount <= DW_PUZZLE_MAX_RUNES,
          "%d runes, cap %d", t->runeCount, DW_PUZZLE_MAX_RUNES);
    CHECK(t->currentCount <= DW_PUZZLE_MAX_CURRENTS,
          "%d currents, cap %d", t->currentCount, DW_PUZZLE_MAX_CURRENTS);
    CHECK(t->checkpointCount <= DW_PUZZLE_MAX_CHECKPOINTS,
          "%d checkpoints, cap %d", t->checkpointCount, DW_PUZZLE_MAX_CHECKPOINTS);
    for (i = 0; i < ngroups; i++) {
        int gt, ngt = t->groups[i].tileCount <= DW_PUZZLE_MAX_GROUP_TILES
            ? t->groups[i].tileCount : 0; /* oversize: entries skipped */
        CHECK(t->groups[i].tileCount <= DW_PUZZLE_MAX_GROUP_TILES,
              "group %d has %d tiles, cap %d", i, t->groups[i].tileCount,
              DW_PUZZLE_MAX_GROUP_TILES);
        for (gt = 0; gt < ngt; gt++)
            CHECK(valid_surface(t->groups[i].tiles[gt].surface),
                  "group %d tile %d surface %d out of range",
                  i, gt, t->groups[i].tiles[gt].surface);
        CHECK(t->groups[i].onState <= DW_PUZZLE_TILE_BLOCKED,
              "group %d onState %d out of range", i, t->groups[i].onState);
        CHECK(t->groups[i].offState <= DW_PUZZLE_TILE_BLOCKED,
              "group %d offState %d out of range", i, t->groups[i].offState);
        CHECK(t->groups[i].initialOn <= 1,
              "group %d initialOn %d (want 0/1)", i, t->groups[i].initialOn);
    }
    CHECK(t->tileCount <= DW_PUZZLE_MAX_TILES,
          "%d explicit tiles, cap %d", t->tileCount, DW_PUZZLE_MAX_TILES);
    for (i = 0; i < ntiles; i++) {
        CHECK(valid_surface(t->tiles[i].surface),
              "explicit tile %d surface %d out of range", i, t->tiles[i].surface);
        CHECK(t->tiles[i].state <= DW_PUZZLE_TILE_BLOCKED,
              "explicit tile %d state %d out of range", i, t->tiles[i].state);
        for (j = i + 1; j < ntiles; j++)
            CHECK(!(t->tiles[i].x == t->tiles[j].x
                    && t->tiles[i].y == t->tiles[j].y
                    && t->tiles[i].z == t->tiles[j].z
                    && t->tiles[i].surface == t->tiles[j].surface),
                  "duplicate explicit tile (%d,%d,%d) surf %d",
                  t->tiles[i].x, t->tiles[i].y, t->tiles[i].z, t->tiles[i].surface);
    }
    CHECK(t->checkpointCount >= 1, "no checkpoints (checkpoint 0 is the entry)");
    for (i = 0; i < ncheckpoints; i++) {
        CHECK(valid_surface(t->checkpoints[i].surface),
              "checkpoint %d surface %d out of range", i, t->checkpoints[i].surface);
        CHECK(t->checkpoints[i].facing == -1
              || (t->checkpoints[i].facing >= 0 && t->checkpoints[i].facing <= 3),
              "checkpoint %d facing %d (want -1..3)", i, t->checkpoints[i].facing);
    }
    for (i = 0; i < nsigils; i++) {
        CHECK(t->sigils[i].kind <= DW_PUZZLE_SIGIL_RESET,
              "sigil %d kind %d out of range", i, t->sigils[i].kind);
        CHECK(valid_surface(t->sigils[i].surface),
              "sigil %d surface %d out of range", i, t->sigils[i].surface);
        if (t->sigils[i].kind != DW_PUZZLE_SIGIL_RESET)
            CHECK(t->sigils[i].targetGroup < t->groupCount,
                  "sigil %d targets group %d, only %d groups",
                  i, t->sigils[i].targetGroup, t->groupCount);
        if (t->sigils[i].kind == DW_PUZZLE_SIGIL_SET)
            CHECK(t->sigils[i].setValue <= 1,
                  "SET sigil %d setValue %d (want 0/1)", i, t->sigils[i].setValue);
    }
    for (i = 0; i < nrunes; i++) {
        CHECK(valid_surface(t->runes[i].surface),
              "rune %d surface %d out of range", i, t->runes[i].surface);
        CHECK(t->runes[i].targetSurface <= DW_PUZZLE_SURFACE_GROUND,
              "rune %d targetSurface %d out of range", i, t->runes[i].targetSurface);
        CHECK(t->runes[i].facing == -1
              || (t->runes[i].facing >= 0 && t->runes[i].facing <= 3),
              "rune %d facing %d (want -1..3)", i, t->runes[i].facing);
    }
    for (i = 0; i < ncurrents; i++) {
        CHECK(valid_surface(t->currents[i].surface),
              "current %d surface %d out of range", i, t->currents[i].surface);
        CHECK(t->currents[i].dir <= 3,
              "current %d dir %d (want FACE_* 0..3)", i, t->currents[i].dir);
    }
    CHECK(t->testOnly <= 1, "testOnly %d (want 0/1)", t->testOnly);
}

static const char *actor_tile_name(const DwActorTile *t, char *buf)
{
    sprintf(buf, "(%d,%d,%d) surf %d", t->x, t->y, t->z, t->surface);
    return buf;
}

/* DW_ACTOR_MIRROR_* -> DW_ACTOR_AXIS_* geometric mapping (NONE has no
 * axis). A mirror along an axis and an echo that moves along the same
 * axis would map the echo onto the player's axis -- the two must
 * differ (actors_design.md section 10). */
static int mirror_to_axis(int mirror)
{
    switch (mirror) {
    case DW_ACTOR_MIRROR_X: return DW_ACTOR_AXIS_X;
    case DW_ACTOR_MIRROR_Y: return DW_ACTOR_AXIS_Y;
    case DW_ACTOR_MIRROR_Z: return DW_ACTOR_AXIS_Z;
    default: return -1;
    }
}

static void check_actor(const char *name, const DwActorTable *a)
{
    int i, j;
    char buf[64], buf2[64];
    int nstones = CLAMP(a->stoneCount, DW_ACTORS_MAX_STONES);
    int npads = CLAMP(a->padCount, DW_ACTORS_MAX_PADS);
    int nshadow = CLAMP(a->shadow.tileCount, DW_ACTORS_MAX_SHADOW_TILES);
    g_table = name;
    CHECK(a->stoneCount <= DW_ACTORS_MAX_STONES,
          "%d stones, cap %d", a->stoneCount, DW_ACTORS_MAX_STONES);
    CHECK(a->padCount <= DW_ACTORS_MAX_PADS,
          "%d pads, cap %d", a->padCount, DW_ACTORS_MAX_PADS);
    CHECK(a->shadow.tileCount <= DW_ACTORS_MAX_SHADOW_TILES,
          "shadow lane %d tiles, cap %d",
          a->shadow.tileCount, DW_ACTORS_MAX_SHADOW_TILES);
    CHECK(a->protectedCount <= DW_ACTORS_MAX_PROTECTED_TILES,
          "%d protected tiles, cap %d",
          a->protectedCount, DW_ACTORS_MAX_PROTECTED_TILES);
    CHECK(a->echo.sigilCount <= DW_ACTORS_MAX_ECHO_SIGILS,
          "echo %d sigils, cap %d",
          a->echo.sigilCount, DW_ACTORS_MAX_ECHO_SIGILS);
    for (i = 0; i < nstones; i++) {
        int e, nedges = CLAMP(a->stones[i].edgeCount, DW_ACTORS_MAX_STONE_EDGES);
        CHECK(a->stones[i].edgeCount <= DW_ACTORS_MAX_STONE_EDGES,
              "stone %d edgeCount %d, cap %d",
              i, a->stones[i].edgeCount, DW_ACTORS_MAX_STONE_EDGES);
        CHECK(valid_actor_surface(a->stones[i].start.surface),
              "stone %d start %s surface %d out of range (actor surfaces are explicit, 0..4)",
              i, actor_tile_name(&a->stones[i].start, buf),
              a->stones[i].start.surface);
        for (e = 0; e < nedges; e++) {
            CHECK(valid_actor_surface(a->stones[i].edges[e].edge.surface),
                  "stone %d edge %d %s surface %d out of range",
                  i, e, actor_tile_name(&a->stones[i].edges[e].edge, buf),
                  a->stones[i].edges[e].edge.surface);
            CHECK(valid_actor_surface(a->stones[i].edges[e].landing.surface),
                  "stone %d edge %d landing %s surface %d out of range",
                  i, e, actor_tile_name(&a->stones[i].edges[e].landing, buf),
                  a->stones[i].edges[e].landing.surface);
        }
        for (j = i + 1; j < nstones; j++)
            CHECK(!same_tile(a->stones[i].start.x, a->stones[i].start.y,
                             a->stones[i].start.z, a->stones[i].start.surface,
                             a->stones[j].start.x, a->stones[j].start.y,
                             a->stones[j].start.z, a->stones[j].start.surface),
                  "stones %d and %d share start tile %s",
                  i, j, actor_tile_name(&a->stones[i].start, buf));
    }
    if (nshadow > 0) {
        int s = a->shadow.tiles[0].surface;
        CHECK(valid_actor_surface(s),
              "shadow lane tile 0 surface %d out of range", s);
        for (i = 1; i < nshadow; i++) {
            const DwActorTile *prev = &a->shadow.tiles[i - 1];
            const DwActorTile *tile = &a->shadow.tiles[i];
            int step = abs(tile->x - prev->x) + abs(tile->y - prev->y)
                + abs(tile->z - prev->z);
            CHECK(valid_actor_surface(tile->surface),
                  "shadow lane tile %d surface %d out of range",
                  i, tile->surface);
            CHECK(tile->surface == s,
                  "shadow lane tile %d surface %d, lane surface %d (one surface)",
                  i, tile->surface, s);
            /* Seam-corner proxy: the shadow walks its lane, so
             * consecutive tiles must be adjacent (a pause -- the
             * same tile twice -- is allowed). A jump of 2+ tiles
             * teleports the shadow across a seam corner. */
            CHECK(step <= 1,
                  "shadow lane jumps %d tile(s) from %s to %s "
                  "(seam-corner teleport; want adjacent)",
                  step, actor_tile_name(prev, buf),
                  actor_tile_name(tile, buf2));
        }
    }
    for (i = 0; i < npads; i++) {
        CHECK(valid_actor_surface(a->pads[i].tile.surface),
              "pad %d tile %s surface %d out of range",
              i, actor_tile_name(&a->pads[i].tile, buf),
              a->pads[i].tile.surface);
        CHECK(a->pads[i].totem < DW_ACTOR_TOTEM_COUNT,
              "pad %d totem %d out of range", i, a->pads[i].totem);
        for (j = i + 1; j < npads; j++)
            CHECK(!same_tile(a->pads[i].tile.x, a->pads[i].tile.y, a->pads[i].tile.z,
                             a->pads[i].tile.surface, a->pads[j].tile.x,
                             a->pads[j].tile.y, a->pads[j].tile.z,
                             a->pads[j].tile.surface),
                  "pads %d and %d share tile %s",
                  i, j, actor_tile_name(&a->pads[i].tile, buf));
    }
    for (i = 0; i < CLAMP(a->protectedCount, DW_ACTORS_MAX_PROTECTED_TILES); i++)
        CHECK(valid_actor_surface(a->protectedTiles[i].surface),
              "protected tile %d %s surface %d out of range",
              i, actor_tile_name(&a->protectedTiles[i], buf),
              a->protectedTiles[i].surface);
    for (i = 0; i < CLAMP(a->echo.sigilCount, DW_ACTORS_MAX_ECHO_SIGILS); i++)
        CHECK(valid_actor_surface(a->echo.sigilTiles[i].surface),
              "echo sigil %d %s surface %d out of range",
              i, actor_tile_name(&a->echo.sigilTiles[i], buf),
              a->echo.sigilTiles[i].surface);
    CHECK(a->echo.active <= 1, "echo active %d (want 0/1)", a->echo.active);
    if (a->echo.active) {
        CHECK(a->echo.playerSurface <= DW_ACTOR_SURFACE_GROUND,
              "echo playerSurface %d out of range", a->echo.playerSurface);
        CHECK(a->echo.echoSurface <= DW_ACTOR_SURFACE_GROUND,
              "echo echoSurface %d out of range", a->echo.echoSurface);
        CHECK(a->echo.echoAxis <= DW_ACTOR_AXIS_Z,
              "echo echoAxis %d out of range", a->echo.echoAxis);
        CHECK(a->echo.mirrorAxis <= DW_ACTOR_MIRROR_Z,
              "echo mirrorAxis %d out of range", a->echo.mirrorAxis);
        if (a->echo.mirrorAxis != DW_ACTOR_MIRROR_NONE)
            CHECK(mirror_to_axis(a->echo.mirrorAxis) != a->echo.echoAxis,
                  "echo mirrorAxis %d maps to the same axis as echoAxis %d "
                  "(mirrorAxis != echoAxis)",
                  a->echo.mirrorAxis, a->echo.echoAxis);
    }
}

/* An actor tile a stone may never occupy: pads, echo sigils, landings
 * (auto-protected) and the author-listed protected tiles. No
 * exemptions: a stone's own start may not sit on another stone's
 * landing, and an edge may not sit on its own stone's landing
 * (a protected edge blocks the fall). */
static int is_protected(const DwActorTable *a, const DwActorTile *t)
{
    int i, s, e;
    int npads = CLAMP(a->padCount, DW_ACTORS_MAX_PADS);
    int nstones = CLAMP(a->stoneCount, DW_ACTORS_MAX_STONES);
    int necho = CLAMP(a->echo.sigilCount, DW_ACTORS_MAX_ECHO_SIGILS);
    int nprotected = CLAMP(a->protectedCount, DW_ACTORS_MAX_PROTECTED_TILES);
    for (i = 0; i < npads; i++)
        if (same_tile(t->x, t->y, t->z, t->surface, a->pads[i].tile.x,
                      a->pads[i].tile.y, a->pads[i].tile.z, a->pads[i].tile.surface))
            return 1;
    for (i = 0; i < necho; i++)
        if (same_tile(t->x, t->y, t->z, t->surface, a->echo.sigilTiles[i].x,
                      a->echo.sigilTiles[i].y, a->echo.sigilTiles[i].z,
                      a->echo.sigilTiles[i].surface))
            return 1;
    for (s = 0; s < nstones; s++) {
        int nedges = CLAMP(a->stones[s].edgeCount, DW_ACTORS_MAX_STONE_EDGES);
        for (e = 0; e < nedges; e++)
            if (same_tile(t->x, t->y, t->z, t->surface,
                          a->stones[s].edges[e].landing.x,
                          a->stones[s].edges[e].landing.y,
                          a->stones[s].edges[e].landing.z,
                          a->stones[s].edges[e].landing.surface))
                return 1;
    }
    for (i = 0; i < nprotected; i++)
        if (same_tile(t->x, t->y, t->z, t->surface, a->protectedTiles[i].x,
                      a->protectedTiles[i].y, a->protectedTiles[i].z,
                      a->protectedTiles[i].surface))
            return 1;
    return 0;
}

static int is_pad_tile(const DwActorTable *a, int x, int y, int z, int s)
{
    int i, n = CLAMP(a->padCount, DW_ACTORS_MAX_PADS);
    for (i = 0; i < n; i++)
        if (same_tile(x, y, z, s, a->pads[i].tile.x, a->pads[i].tile.y,
                      a->pads[i].tile.z, a->pads[i].tile.surface))
            return 1;
    return 0;
}

/* Explicit-state rule (actors_design.md section 2): DEFAULT
 * resolves via the stock grid on the player's current surface, and
 * reads BLOCKED for any surface other than the player's (the glue
 * compares against gDwPuzzleDebug.surface); for GROUND there is no
 * stock grid, so DEFAULT always reads BLOCKED (fail closed). The
 * enforceable rule is GROUND-only: an audit of the engine's
 * queries shows no walkability query is cross-surface --
 * TryPush, the step hook, Currents, and the slide all query the
 * player's surface; the shadow/echo/pad checks are TileEq, not
 * tile queries; the one cross-surface tile is the landing, and
 * section 3 explicitly permits it to use its base kind (VOID for
 * a gap, WALKABLE for a platform -- the LANDED actor tile wins
 * once the stone is there). So production tables need explicit
 * states for GROUND actor tiles EXCEPT landings (the VOID-only
 * override rule still applies if a landing override is present).
 * Non-GROUND actor tiles resolve via the stock grid on the
 * player's surface; the cross-surface BLOCKED is a latent
 * contract, not an enforceable table rule. */
static void check_ground_actor_tile(const DwPuzzleTable *t, const DwActorTile *tile,
                                    const char *what, int production)
{
    char buf[64];
    if (!production || tile->surface != DW_PUZZLE_SURFACE_GROUND)
        return;
    CHECK(is_group_tile(t, tile->x, tile->y, tile->z, tile->surface)
          || (find_explicit(t, tile->x, tile->y, tile->z, tile->surface) != NULL
              && find_explicit(t, tile->x, tile->y, tile->z, tile->surface)->state
                 != DW_PUZZLE_TILE_DEFAULT),
          "ground actor tile %s %s has no explicit engine-a state "
          "(group tile or explicit override, state != DEFAULT)",
          what, actor_tile_name(tile, buf));
}

static void check_pair(const char *puzzle_name, const DwPuzzleTable *t,
                       const char *actor_name, const DwActorTable *a)
{
    int s, e, i, j;
    char buf[64];
    int production = !t->testOnly;
    int nstones = CLAMP(a->stoneCount, DW_ACTORS_MAX_STONES);
    int nshadow = CLAMP(a->shadow.tileCount, DW_ACTORS_MAX_SHADOW_TILES);
    int necho = CLAMP(a->echo.sigilCount, DW_ACTORS_MAX_ECHO_SIGILS);
    int npads = CLAMP(a->padCount, DW_ACTORS_MAX_PADS);
    int nprotected = CLAMP(a->protectedCount, DW_ACTORS_MAX_PROTECTED_TILES);
    int ncheckpoints = CLAMP(t->checkpointCount, DW_PUZZLE_MAX_CHECKPOINTS);
    int nrunes = CLAMP(t->runeCount, DW_PUZZLE_MAX_RUNES);
    g_table = puzzle_name;
    printf("pair %s + %s (production=%d)\n", puzzle_name, actor_name, production);
    /* Landings. */
    for (s = 0; s < nstones; s++) {
        int nedges = CLAMP(a->stones[s].edgeCount, DW_ACTORS_MAX_STONE_EDGES);
        for (e = 0; e < nedges; e++) {
            const DwActorTile *land = &a->stones[s].edges[e].landing;
            const DwActorTile *edge = &a->stones[s].edges[e].edge;
            const DwPuzzleTile *ov;
            CHECK(!is_current(t, land->x, land->y, land->z, land->surface),
                  "stone %d edge %d landing %s is a current tile",
                  s, e, actor_tile_name(land, buf));
            /* Landing tiles are reserved: in no group, and not a
             * sigil / pad / checkpoint / rune tile. */
            CHECK(!is_group_tile(t, land->x, land->y, land->z, land->surface),
                  "stone %d edge %d landing %s is a group tile",
                  s, e, actor_tile_name(land, buf));
            CHECK(!is_sigil(t, land->x, land->y, land->z, land->surface),
                  "stone %d edge %d landing %s is a sigil tile",
                  s, e, actor_tile_name(land, buf));
            CHECK(!is_pad_tile(a, land->x, land->y, land->z, land->surface),
                  "stone %d edge %d landing %s is a pad tile",
                  s, e, actor_tile_name(land, buf));
            CHECK(!is_checkpoint(t, land->x, land->y, land->z, land->surface),
                  "stone %d edge %d landing %s is a checkpoint tile",
                  s, e, actor_tile_name(land, buf));
            CHECK(!is_rune(t, land->x, land->y, land->z, land->surface),
                  "stone %d edge %d landing %s is a rune tile",
                  s, e, actor_tile_name(land, buf));
            ov = find_explicit(t, land->x, land->y, land->z, land->surface);
            CHECK(ov == NULL || ov->state == DW_PUZZLE_TILE_VOID,
                  "stone %d edge %d landing %s has explicit override state %d, "
                  "want VOID-only", s, e, actor_tile_name(land, buf),
                  ov ? ov->state : -1);
            for (i = s; i < nstones; i++) {
                int e0 = (i == s) ? e + 1 : 0;
                int nedges2 = CLAMP(a->stones[i].edgeCount, DW_ACTORS_MAX_STONE_EDGES);
                for (j = e0; j < nedges2; j++)
                    CHECK(!same_tile(land->x, land->y, land->z, land->surface,
                                     a->stones[i].edges[j].landing.x,
                                     a->stones[i].edges[j].landing.y,
                                     a->stones[i].edges[j].landing.z,
                                     a->stones[i].edges[j].landing.surface),
                          "stones %d and %d share landing tile %s",
                          s, i, actor_tile_name(land, buf));
            }
            CHECK(!same_tile(edge->x, edge->y, edge->z, edge->surface,
                             land->x, land->y, land->z, land->surface),
                  "stone %d edge %d: edge == landing %s",
                  s, e, actor_tile_name(edge, buf));
            CHECK(!is_protected(a, edge),
                  "stone %d edge %d %s is protected (pad/echo/landing/listed)",
                  s, e, actor_tile_name(edge, buf));
            check_ground_actor_tile(t, edge, "edge", production);
        }
        CHECK(!is_protected(a, &a->stones[s].start),
              "stone %d start %s is protected (pad/echo/landing/listed)",
              s, actor_tile_name(&a->stones[s].start, buf));
        check_ground_actor_tile(t, &a->stones[s].start, "stone start", production);
    }
    /* Shadow. */
    for (i = 0; i < nshadow; i++) {
        const DwActorTile *tile = &a->shadow.tiles[i];
        for (j = 0; j < ncheckpoints; j++)
            CHECK(!same_tile(tile->x, tile->y, tile->z, tile->surface,
                             t->checkpoints[j].x, t->checkpoints[j].y,
                             t->checkpoints[j].z, t->checkpoints[j].surface),
                  "shadow tile %s is checkpoint %d (entry/checkpoint are script tiles)",
                  actor_tile_name(tile, buf), j);
        check_ground_actor_tile(t, tile, "shadow", production);
    }
    if (production && nshadow > 0)
        CHECK(a->shadow.beatFrames >= 30,
              "shadow beat %d frames, Arc 2 needs >= 30 (readable patrol)",
              a->shadow.beatFrames);
    /* Echo sigils. */
    for (i = 0; i < necho; i++)
        check_ground_actor_tile(t, &a->echo.sigilTiles[i], "echo sigil", production);
    /* Pads. */
    for (i = 0; i < npads; i++) {
        const DwActorTile *tile = &a->pads[i].tile;
        for (j = 0; j < ncheckpoints; j++)
            CHECK(!same_tile(tile->x, tile->y, tile->z, tile->surface,
                             t->checkpoints[j].x, t->checkpoints[j].y,
                             t->checkpoints[j].z, t->checkpoints[j].surface),
                  "pad %d tile %s is checkpoint %d",
                  i, actor_tile_name(tile, buf), j);
        for (j = 0; j < nrunes; j++)
            CHECK(!same_tile(tile->x, tile->y, tile->z, tile->surface,
                             t->runes[j].x, t->runes[j].y, t->runes[j].z,
                             t->runes[j].surface),
                  "pad %d tile %s is rune %d",
                  i, actor_tile_name(tile, buf), j);
        CHECK(!is_current(t, tile->x, tile->y, tile->z, tile->surface),
              "pad %d tile %s is a current tile",
              i, actor_tile_name(tile, buf));
        /* A pad is an engine-a sigil tile: the glue suppresses the
         * auto-fire and ResolvePad fires via PressSigil. Production
         * only: the test fixtures' pads have no puzzle sigils. */
        if (production)
            CHECK(is_sigil(t, tile->x, tile->y, tile->z, tile->surface),
                  "pad %d tile %s has no sigil in the engine-a table",
                  i, actor_tile_name(tile, buf));
        check_ground_actor_tile(t, tile, "pad", production);
    }
    /* Protected. */
    for (i = 0; i < nprotected; i++)
        check_ground_actor_tile(t, &a->protectedTiles[i], "protected", production);
}
"""


def _registry_pairs():
    """(puzzle, actor) pairs from the engine registry in dw_puzzle.c:
    sPuzzleTables[i] pairs with sActorTables[i]; a NULL actor entry
    means the rift has no actor table yet. This is the primary source
    -- the registry is what the game loads, so it is the pairing that
    matters at runtime."""
    text = (OV9 / "dw_puzzle.c").read_text()
    pairs = []
    puzzles = _array_entries(text, "sPuzzleTables")
    actors = _array_entries(text, "sActorTables")
    for p_sym, a_sym in zip(puzzles, actors):
        if p_sym != "NULL" and a_sym != "NULL":
            pairs.append((p_sym, a_sym))
    return pairs


def _array_entries(text, name):
    """Entry symbols of `static const ... <name>[] = { &X, NULL, ... };`."""
    m = re.search(r"\b" + name + r"\s*\[\]\s*=\s*\{(.*?)\};", text, re.S)
    if not m:
        return []
    entries = []
    for tok in m.group(1).split(","):
        tok = tok.strip()
        tok = re.sub(r"//.*", "", tok).strip()
        if not tok:
            continue
        entries.append(tok.lstrip("&"))
    return entries


def _find_tables():
    """(puzzle tables, actor tables, pairs) from the sources.
    Pairing order: the engine registry (dw_puzzle.c sPuzzleTables /
    sActorTables, by index) first; then same-file pairing (each actor
    table pairs with one puzzle table in its file, for rifts that
    ship both tables but are not registered yet -- one pair per
    actor, so a shared actor table must be registered); then
    EXTRA_PAIRS (cross-file pairs, e.g. the test tables)."""
    puzzles = []  # (symbol, file)
    actors = []
    for path in sorted(OV9.glob("dw_puzzle_*.c")):
        if path.name == "dw_puzzle.c":
            continue  # the engine, not a table
        text = path.read_text()
        for sym in re.findall(r"const\s+DwPuzzleTable\s+(\w+)\s*=", text):
            puzzles.append((sym, path))
        for sym in re.findall(r"const\s+DwActorTable\s+(\w+)\s*=", text):
            actors.append((sym, path))
    pairs = []
    paired_puzzles = set()
    paired_actors = set()
    for p_sym, a_sym in _registry_pairs():
        if (p_sym, a_sym) not in pairs:
            pairs.append((p_sym, a_sym))
            paired_puzzles.add(p_sym)
            paired_actors.add(a_sym)
    by_file = {}
    for sym, path in puzzles:
        by_file.setdefault(str(path), []).append(("puzzle", sym))
    for sym, path in actors:
        by_file.setdefault(str(path), []).append(("actor", sym))
    for path, entries in by_file.items():
        p_syms = [s for kind, s in entries if kind == "puzzle"]
        a_syms = [s for kind, s in entries if kind == "actor"]
        for a_sym in a_syms:
            for p_sym in p_syms:
                if p_sym not in paired_puzzles and a_sym not in paired_actors:
                    pairs.append((p_sym, a_sym))
                    paired_puzzles.add(p_sym)
                    paired_actors.add(a_sym)
    for p_sym, a_sym in EXTRA_PAIRS:
        if (p_sym, a_sym) not in pairs:
            pairs.append((p_sym, a_sym))
    return puzzles, actors, pairs


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    puzzles, actors, pairs = _find_tables()
    if not puzzles and not actors:
        print("no DwPuzzleTable / DwActorTable found under src/overlay009/")
        return 1
    gen_dir = REPO / "build" / "generated"
    if not (gen_dir / "map_headers.h").exists():
        print("build/generated missing: run `make release` first")
        return 1

    externs = "\n".join(f"extern const DwPuzzleTable {sym};" for sym, _ in puzzles)
    externs += "\n" + "\n".join(f"extern const DwActorTable {sym};" for sym, _ in actors)
    calls = []
    for sym, _ in puzzles:
        calls.append(f'check_puzzle("{sym}", &{sym});')
    for sym, _ in actors:
        calls.append(f'check_actor("{sym}", &{sym});')
    for p_sym, a_sym in pairs:
        calls.append(f'check_pair("{p_sym}", &{p_sym}, "{a_sym}", &{a_sym});')
    for sym, _ in actors:
        if not any(a == sym for _, a in pairs):
            calls.append(f'printf("note: actor table {sym} has no paired puzzle table; '
                         f'cross-table rules skipped\\n");')
    for sym, _ in puzzles:
        if not any(p == sym for p, _ in pairs):
            calls.append(f'printf("note: puzzle table {sym} has no paired actor table; '
                         f'cross-table rules skipped\\n");')
    main_c = CHECKER_C + f"""
{externs}

int main(void)
{{
    printf("dw_tables_check: %d puzzle table(s), %d actor table(s), %d pair(s)\\n",
           {len(puzzles)}, {len(actors)}, {len(pairs)});
{chr(10).join("    " + c for c in calls)}
    printf("%d checks, %d failures\\n", g_checks, g_failures);
    puts(g_failures ? "FAIL" : "PASS");
    return g_failures != 0;
}}
"""
    workdir = pathlib.Path(a.out) if a.out else pathlib.Path(
        tempfile.mkdtemp(prefix="dw_tables_check_"))
    workdir.mkdir(parents=True, exist_ok=True)
    # Host-test shim for <nitro.h>: dw_puzzle.h needs only nitro's
    # base types (it calls no nitro functions), and the full SDK
    # header drags in the whole SDK include tree (ARM7 pieces
    # included). The shim dir goes first on the -I order. -std=c11:
    # dw_puzzle.h (via the shim) and dw_puzzle_actors.h (host-test
    # typedefs) both define the base types; C11 allows identical
    # typedef redefinition, C99 does not.
    shim_dir = workdir / "nitro_shim"
    shim_dir.mkdir(exist_ok=True)
    (shim_dir / "nitro.h").write_text(
        "/* Host-test shim: dw_puzzle.h needs only nitro's base types. */\n"
        "#ifndef DW_TABLES_CHECK_NITRO_H\n"
        "#define DW_TABLES_CHECK_NITRO_H\n"
        "#include <stddef.h>\n"
        "#include <stdint.h>\n"
        "typedef uint8_t u8;\ntypedef uint16_t u16;\ntypedef uint32_t u32;\n"
        "typedef int8_t s8;\ntypedef int16_t s16;\ntypedef int32_t s32;\n"
        "typedef int BOOL;\n#define TRUE 1\n#define FALSE 0\n"
        "#endif\n")
    checker_c = workdir / "dw_tables_check.c"
    checker_c.write_text(main_c)
    binary = workdir / "dw_tables_check"
    tu_files = sorted({str(p) for _, p in puzzles + actors})
    if ACTORS_C not in [pathlib.Path(p) for p in tu_files]:
        tu_files.append(str(ACTORS_C))
    # -I build (not build/generated): the sources #include
    # "generated/..." with the prefix. The shim dir goes first so
    # <nitro.h> resolves to the base-types shim (see above), not the
    # full SDK. -include nitro.h: some table TUs include location.h
    # (which needs the types via savedata.h) before dw_puzzle.h,
    # so the shim must come first in every TU, not just the checker.
    cmd = ["cc", "-std=c11", "-Wall", "-Wextra", "-DDW_ACTORS_HOST_TEST",
           "-DPOKEPLATINUM_GENERATED_ENUM", "-include", "nitro.h",
           "-I", str(shim_dir), "-I", str(REPO / "include"),
           "-I", str(REPO / "build"),
           str(checker_c)] + tu_files + ["-o", str(binary)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode:
        print("compile failed:")
        print(proc.stdout)
        print(proc.stderr)
        return 1
    proc = subprocess.run([str(binary)], capture_output=True, text=True)
    print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="")
    if not a.keep:
        import shutil
        shutil.rmtree(workdir, ignore_errors=True)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
