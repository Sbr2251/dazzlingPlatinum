#ifndef POKEPLATINUM_DW_PUZZLE_H
#define POKEPLATINUM_DW_PUZZLE_H

/*
 * Distortion World puzzle engine (engine-a).
 *
 * Data-driven core for the DW puzzle rifts (docs/distortion_world/PUZZLE_PLAN.md
 * section 3). Every module is a table: a rift workstream writes one table in
 * src/overlay009/dw_puzzle_<map>.c and nothing else; the engine in
 * src/overlay009/dw_puzzle.c owns all runtime behaviour. The glue in
 * src/overlay009/ov9_02249960.c is hook calls only: it passes the player's
 * tile/surface/facing in, applies the results out (ghost-prop show/hide, the
 * jump-point surface change, slide teleports, checkpoint respawns).
 *
 * Coordinates are DW world tile coords (x, y, z) exactly as the ov9 step hook
 * sees them: base-ground tiles have y = 1, wall tiles y >= 2 at a fixed x,
 * ceiling tiles y = 10. (x, y, z) alone does NOT identify a tile: a wall and
 * a ceiling can share one (the B4F wall->ceiling transfers sit on the same
 * tile). Every table entry therefore carries a surface, and every query
 * passes the surface the player is standing on. An entry matches when its
 * surface is DW_PUZZLE_SURFACE_ANY or equals the queried surface.
 *
 * Surfaces: the ov9 FloatingPlatformKind numbering for platforms
 * (FLOOR = 0, WEST_WALL = 1, EAST_WALL = 2, CEILING = 3), plus
 * GROUND = 4 (ov9 INVALID: base map terrain, no platform, platform index
 * -1, avatar distortion ACTIVE). FLOOR and GROUND are different surfaces:
 * a floating floor platform is walked on via its tw_arc_attr grid; base
 * ground is walked on via the map's terrain collision. A rune to GROUND
 * must translate to platform kind INVALID / index -1 in the jump template,
 * never to kind FLOOR -- a player left in distortion FLOOR on base ground
 * would consult a nonexistent platform grid and strand.
 *
 * Directions use FACE_* (FACE_UP = 0, FACE_DOWN = 1, FACE_LEFT = 2,
 * FACE_RIGHT = 3), as pressed on the surface the player is standing on.
 * The engine converts a FACE_* on a surface to a (dx, dy, dz) step with the
 * same tables the stock DW movement code uses (unk_0205F180.c).
 *
 * Landing rule (rift-ef): a landing fires NOTHING. A jump, warp or
 * respawn landing never calls the step hook, so no sigil, rune,
 * checkpoint, current or fall fires on the landing tile -- each fires
 * only when the player next WALKS onto it. A rune pair therefore cannot
 * ping-pong (the destination rune fires only on a later walk onto it),
 * and sigils / checkpoints must sit on walked tiles, never on landing
 * tiles. The glue re-runs the step hook on slide landings on purpose:
 * a slide is a movement, so its landing tile DOES fire step effects.
 *
 * Group + current on one tile (rift-214): a tile can be both a group
 * tile and a current. When the group's tile state is BLOCKED it wins
 * and no slide happens (a slide stranded there stops; the frame hook
 * also stops a slide whose current tile went BLOCKED under the player);
 * when the group is open, the current applies. A VOID current tile is
 * a fall, not a slide.
 *
 * Snapshots (rift-214): a checkpoint snapshot stores the LOGICAL group
 * states (the toggle/set base state), not the fading display state and
 * not the momentary holds. A group mid-fade at snapshot time restores to
 * its logical value, with walkability and display snapping to it
 * (timers cleared, no fade). gDwPuzzleDebug.groupBits is the logical
 * state (base OR momentary holds); groupDisplayBits is the visual state.
 *
 * Tile-state precedence in ResolveTile (see DwPuzzle_QueryTile): actor
 * tiles win over explicit table overrides, which win over groups
 * (later group wins). An actor tile is the most immediate physical
 * reality (a stone sitting on a tile), so a RESTING stone's BLOCKED
 * actor tile plugs a current tile even if that tile has an explicit
 * SOLID override -- the slide stops before the stone.
 */

#include <nitro.h>

#include "field/field_system_decl.h"
#include "location.h"

/* ------------------------------------------------------------------ */
/* Limits (one puzzle table per map; keep tables inside these)        */
/* ------------------------------------------------------------------ */

#define DW_PUZZLE_MAX_GROUPS        8
#define DW_PUZZLE_MAX_GROUP_TILES   32
#define DW_PUZZLE_MAX_TILES         32
#define DW_PUZZLE_MAX_SIGILS        16
#define DW_PUZZLE_MAX_RUNES         8
#define DW_PUZZLE_MAX_CURRENTS      16
#define DW_PUZZLE_MAX_CHECKPOINTS   8
#define DW_PUZZLE_MAX_ACTOR_BLOCKS  8
#define DW_PUZZLE_MAX_STONES        8
/* Safety cap on one slide (a closed current cycle must end). */
#define DW_PUZZLE_MAX_SLIDE_STEPS   64

/* Ghost-prop groups are numbered by tw_arc (0..23). */
#define DW_PUZZLE_GHOST_GROUP_NONE  0xFF
/* The honeycomb rule: a group that fades out stays solid for its whole
 * fade (31 opacity steps + lag), and a group that fades in is drawn a few
 * frames before it holds. Solid implies drawn; drawn does not imply solid
 * during the fade-in lead (stepping onto a drawn-but-not-yet-solid tile
 * bumps, it never drops the player). */
#define DW_PUZZLE_FADE_OUT_FRAMES   33
#define DW_PUZZLE_FADE_IN_LEAD      3
/* Currents slide one tile per this many field frames. */
#define DW_PUZZLE_SLIDE_FRAMES_PER_TILE 6

/* ------------------------------------------------------------------ */
/* Tile state                                                          */
/* ------------------------------------------------------------------ */

typedef enum DwPuzzleTileState {
    /* No engine override: use the stock collision grid. */
    DW_PUZZLE_TILE_DEFAULT = 0,
    /* Walkable even if the stock grid says blocked. */
    DW_PUZZLE_TILE_SOLID,
    /* Stepping (or standing) here is a fall. Walkable in the collision
     * check, so the player can step onto it; the step/frame hook then
     * starts the fall. */
    DW_PUZZLE_TILE_VOID,
    /* Impassable even if the stock grid says walkable. */
    DW_PUZZLE_TILE_BLOCKED,
} DwPuzzleTileState;

typedef enum DwPuzzleSurface {
    /* Floating floor platform (ov9 kind 0). */
    DW_PUZZLE_SURFACE_FLOOR = 0,
    DW_PUZZLE_SURFACE_WEST_WALL = 1,
    DW_PUZZLE_SURFACE_EAST_WALL = 2,
    DW_PUZZLE_SURFACE_CEILING = 3,
    /* Base map terrain (ov9 kind INVALID, platform index -1). */
    DW_PUZZLE_SURFACE_GROUND = 4,
    DW_PUZZLE_SURFACE_INVALID = 4,
    DW_PUZZLE_SURFACE_ANY = 0xFF,
} DwPuzzleSurface;

/* Occupants that can press sigils (momentary holders are per occupant). */
typedef enum DwPuzzleOccupant {
    DW_PUZZLE_OCCUPANT_PLAYER = 0,
    DW_PUZZLE_OCCUPANT_ECHO = 1, /* engine-b's echo self */
    DW_PUZZLE_OCCUPANT_COUNT = 2,
} DwPuzzleOccupant;

/* ------------------------------------------------------------------ */
/* Tables (all const, all in dw_puzzle_<map>.c)                        */
/* ------------------------------------------------------------------ */

/* One tile of a group, or one explicit override. */
typedef struct DwPuzzleTile {
    s16 x;
    s16 y;
    s16 z;
    /* For a group tile: unused (the group's on/off states decide).
     * For an explicit override (DwPuzzleTable.tiles): the state.
     * state is the resolved state while the tile's surface matches. */
    u8 state;
    /* DwPuzzleSurface of this tile, or ANY. */
    u8 surface;
    /* Step-fall script for this tile (1-based map script entry, as in the
     * .s files); 0 = the table's fallScriptId. Only used when the tile
     * resolves to VOID. */
    u8 fallScriptId;
    u8 padding;
} DwPuzzleTile;

/*
 * A group: a set of tiles plus one ghost-prop group, on or off.
 * Walkability follows the honeycomb rule, not the props: when a group
 * turns off, its props start fading at once but its tiles stay solid for
 * fadeOutFrames; when it turns on, its props show at once but its tiles
 * hold only after fadeInLeadFrames. Groups with ghostPropGroup =
 * DW_PUZZLE_GHOST_GROUP_NONE have no props and switch at once.
 * Tiles take onState while the group is (solid-)on, offState while off.
 * Explicit overrides in DwPuzzleTable.tiles win over groups, actor tiles
 * win over groups; among groups, the later group in the table wins.
 * fallScriptId is the step-fall script for the group's tiles when they
 * resolve to VOID (0 = the table's fallScriptId).
 */
typedef struct DwPuzzleGroup {
    const DwPuzzleTile *tiles;
    u8 tileCount;
    u8 ghostPropGroup; /* tw_arc ghost-prop group id, or NONE */
    u8 fadeOutFrames;  /* 0 = DW_PUZZLE_FADE_OUT_FRAMES when props exist */
    u8 fadeInLeadFrames; /* 0 = DW_PUZZLE_FADE_IN_LEAD when props exist */
    u8 onState;  /* DwPuzzleTileState while on (usually SOLID) */
    u8 offState; /* DwPuzzleTileState while off (usually BLOCKED or VOID) */
    u8 initialOn; /* 0 off, 1 on */
    u8 fallScriptId;
} DwPuzzleGroup;

typedef enum DwPuzzleSigilKind {
    /* Step on: flip the target group. Step on again: flip it back. */
    DW_PUZZLE_SIGIL_TOGGLE = 0,
    /* Step on: set the target group to setValue (0/1). */
    DW_PUZZLE_SIGIL_SET,
    /* Held while stood on: the group is on while any momentary sigil for
     * it is stood on by any occupant, off otherwise (unless a toggle/set
     * says otherwise). Holder counts are per occupant, so the player,
     * the echo and two momentary sigils for one group all behave. */
    DW_PUZZLE_SIGIL_MOMENTARY,
    /* Step on: restore the puzzle to the last checkpoint snapshot
     * (groups + sigil states). The player does not move. */
    DW_PUZZLE_SIGIL_RESET,
} DwPuzzleSigilKind;

/* A sigil tile. Sigils fire once per step onto the tile (stepping off
 * and back on fires again); momentary sigils also release on stepping
 * off (per occupant). A sigil on a tile that is VOID still fires before
 * the fall. */
typedef struct DwPuzzleSigil {
    s16 x;
    s16 y;
    s16 z;
    u8 kind;       /* DwPuzzleSigilKind */
    u8 targetGroup; /* index into DwPuzzleTable.groups (RESET ignores it) */
    u8 setValue;   /* SET only: 0 or 1 */
    u8 surface;    /* DwPuzzleSurface of this sigil, or ANY */
} DwPuzzleSigil;

/*
 * A gravity rune: stepping on it changes surface in place, reusing the
 * jump-point surface-change path (the ov9 glue builds a
 * DistWorldFloatingPlatformJumpPointTemplate from these fields).
 * targetX/Y/Z is the tile on the destination surface (usually the same
 * (x, z), the y of the destination surface). rot is the jump template's
 * rotation (usually -90 / 90 / 180 / 0, as in the tw_arc jump points);
 * steps is the jump animation length (0 = 16, the stock jumps).
 * If useCamera, the glue runs a camera transition to cameraX/Y/Z over
 * cameraSteps frames (0 = 16) as the rune fires; otherwise the stock
 * camera-angle templates at the destination do it. cameraX/Y/Z are camera
 * angles in tw_arc camera-template units (the same units as
 * DistWorldCameraAngleTemplate.angleX/Y/Z), not positions.
 * A rune to GROUND translates to platform kind INVALID / index -1.
 */
typedef struct DwPuzzleRune {
    s16 x;
    s16 y;
    s16 z;
    s16 targetX;
    s16 targetY;
    s16 targetZ;
    u8 surface;      /* DwPuzzleSurface of the rune tile, or ANY */
    u8 targetSurface; /* DwPuzzleSurface */
    s8 facing;        /* FACE_* after the change, or -1 to keep facing */
    s8 padding;
    s16 rot;
    u8 steps; /* 0 = 16 */
    u8 useCamera;
    s16 cameraX;
    s16 cameraY;
    s16 cameraZ;
    s16 cameraSteps; /* 0 = 16 */
} DwPuzzleRune;

typedef struct DwPuzzleCurrent {
    s16 x;
    s16 y;
    s16 z;
    u8 dir; /* FACE_* drift direction on this tile's surface */
    u8 surface; /* DwPuzzleSurface of this tile, or ANY */
    /* The ghost-prop group holding this current's arrow visuals, or NONE.
     * Arrow props are drawn by the rift's tw_arc record; the engine does
     * not animate them, it only reports the slide in gDwPuzzleDebug. */
    u8 arrowGhostGroup;
    u8 padding;
} DwPuzzleCurrent;

/* A checkpoint tile. Stepping on it snapshots the puzzle (group base /
 * target / solid / display states; momentary holders are NOT snapshotted
 * -- they are per-occupant and cleared on restore, so occupants must
 * re-press after a restore) and makes it the fall target. Checkpoint 0
 * should be the map entry: the fresh-entry reset snapshots it without
 * anyone stepping on it, so an early fall or reset always has a snapshot.
 * surface is the surface of the checkpoint tile: the respawn restores
 * the player to (x, y, z) on that surface (platform + distortion state
 * + height mode from the glue). */
typedef struct DwPuzzleCheckpoint {
    s16 x;
    s16 y;
    s16 z;
    s8 facing; /* FACE_* to face on respawn, or -1 to keep facing */
    u8 surface; /* DwPuzzleSurface of the checkpoint tile */
    u8 padding[2];
} DwPuzzleCheckpoint;

typedef struct DwPuzzleTable {
    u32 mapHeader; /* MAP_HEADER_DW_* */
    /* VAR_ARC2_PROGRESS gate: 0/0 = any progress. */
    u16 minProgress;
    u16 maxProgress;
    /* The map's frame-fall script entry (1-based, as in the .s files) and
     * the map-local var the frame hook raises to start it when the ground
     * goes from under a standing player (the Eterna honeycomb pattern:
     * the rift's init frame table must have
     *   InitScriptGoToIfEqual <fallVar>, 1, <fallScriptId>
     * and the fall script must clear <fallVar> first). 0 = no frame fall.
     * Step falls use the per-tile / per-group fallScriptId, falling back
     * to this one. Eterna Forest's split is the model: entry-chasm lips
     * are VOID tiles with fallScriptId 2 (their own script), the
     * honeycomb group's fallScriptId is 5, and the table's is 5. */
    u16 fallScriptId;
    u16 fallVar; /* a VAR_MAP_LOCAL_* id, e.g. VAR_MAP_LOCAL_3 */
    u8 groupCount;
    u8 sigilCount;
    u8 runeCount;
    u8 currentCount;
    u8 checkpointCount;
    u8 tileCount;
    /* Debug-only table (the test table): returned only while test mode
     * is on. Production tables must set 0. */
    u8 testOnly;
    u8 padding;
    const DwPuzzleGroup *groups;
    const DwPuzzleSigil *sigils;
    const DwPuzzleRune *runes;
    const DwPuzzleCurrent *currents;
    const DwPuzzleCheckpoint *checkpoints;
    const DwPuzzleTile *tiles; /* explicit overrides */
} DwPuzzleTable;

/* ------------------------------------------------------------------ */
/* Results (filled by the step/frame hooks; the ov9 glue acts on them) */
/* ------------------------------------------------------------------ */

typedef struct DwPuzzleRuneAction {
    s16 targetX;
    s16 targetY;
    s16 targetZ;
    u8 targetSurface;
    s8 facing;
    s16 rot;
    u8 steps; /* 0 = 16 */
    u8 useCamera;
    s16 cameraX;
    s16 cameraY;
    s16 cameraZ;
    s16 cameraSteps; /* 0 = 16 */
} DwPuzzleRuneAction;

typedef struct DwPuzzleStepResult {
    BOOL handled;       /* TRUE: the per-map hook should return TRUE */
    BOOL fallRequested; /* step onto VOID: start fallScriptId */
    u16 fallScriptId;   /* map script entry for this fall */
    BOOL runeRequested;
    DwPuzzleRuneAction rune;
    BOOL checkpointReached;
    BOOL slideStarted;  /* step onto a current: the slide is running */
} DwPuzzleStepResult;

typedef struct DwPuzzleFrameResult {
    /* Ghost-prop groups to show/hide this frame (tw_arc group ids as a
     * bitmask). The glue applies Hide/ShowGhostPropGroup for each bit. */
    u32 ghostShowMask;
    u32 ghostHideMask;
    /* Slide: one tile per DW_PUZZLE_SLIDE_FRAMES_PER_TILE frames. The glue
     * moves the player to (slideX, slideY, slideZ) and re-runs the step
     * hook there; it must pause player movement while slideActive. */
    BOOL slideActive;
    BOOL slideStep; /* this frame: move one tile */
    s16 slideX;
    s16 slideY;
    s16 slideZ;
    /* Fall respawn: the warp after a fall has landed, or a shadow catch.
     * The glue moves the player to the checkpoint (surface + facing as
     * in the table) once the player is idle. */
    BOOL respawnRequested;
    s16 respawnX;
    s16 respawnY;
    s16 respawnZ;
    s8 respawnFacing;
    u8 respawnSurface; /* DwPuzzleSurface of the checkpoint tile */
    /* Standing on ground that went away (frame-detected fall). The
     * engine has raised fallVar; the init frame table starts the fall. */
    BOOL frameFallRequested;
} DwPuzzleFrameResult;

/* ------------------------------------------------------------------ */
/* Debug export (gDwPuzzleDebug, in the xMAP; one RAM struct)         */
/* ------------------------------------------------------------------ */

typedef enum DwPuzzleEvent {
    DW_PUZZLE_EVENT_NONE = 0,
    DW_PUZZLE_EVENT_SIGIL,
    DW_PUZZLE_EVENT_RUNE,
    DW_PUZZLE_EVENT_CURRENT_START,
    DW_PUZZLE_EVENT_CURRENT_STOP,
    DW_PUZZLE_EVENT_CHECKPOINT,
    DW_PUZZLE_EVENT_FALL,
    DW_PUZZLE_EVENT_RESPAWN,
    DW_PUZZLE_EVENT_RESET,
    DW_PUZZLE_EVENT_CAUGHT, /* shadow catch -> checkpoint respawn */
} DwPuzzleEvent;

/* One stone / actor position (engine-b writes stone/shadow/echo here). */
typedef struct DwPuzzleActorPos {
    s16 x;
    s16 y;
    s16 z;
    u8 present;
    u8 surface; /* DwPuzzleSurface, so (0,0,0) on GROUND is unambiguous */
    u8 padding[2];
} DwPuzzleActorPos;

typedef struct DwPuzzleDebug {
    u32 mapHeader;
    u32 active; /* a puzzle table is loaded for this map */
    s16 playerX;
    s16 playerY;
    s16 playerZ;
    u8 surface; /* DwPuzzleSurface */
    u8 currentTileState; /* DwPuzzleTileState at the player's tile */
    u16 padding;
    u32 groupBits;        /* group i solid-on */
    u32 groupDisplayBits; /* group i props shown */
    u32 sigilBits;        /* sigil i currently pressed (any occupant) */
    u32 checkpointIndex;
    s16 checkpointX;
    s16 checkpointY;
    s16 checkpointZ;
    u32 fallCount;
    u32 frameCount;
    /* Slide. */
    u32 slideActive;
    s8 slideDir; /* FACE_* */
    u8 slidePadding[3];
    s16 slideTargetX;
    s16 slideTargetY;
    s16 slideTargetZ;
    u32 slideSteps; /* tiles slid in the current slide */
    /* Last event, for the harness. */
    u32 lastEvent; /* DwPuzzleEvent */
    u32 lastEventFrame;
    u32 lastEventGroup;
    /* Sigil flash: frames remaining of the sigil flash. */
    u32 flashFrames;
    /* Bump on every checkpoint restore / reset sigil / shadow catch.
     * Engine-b's actors poll this and restore their own snapshot when it
     * changes. */
    u32 resetGeneration;
    /* Actors (engine-b owns these fields; engine-a zeroes them). */
    DwPuzzleActorPos stones[DW_PUZZLE_MAX_STONES];
    u32 stoneCount;
    u32 shadowPhase;
    DwPuzzleActorPos shadow; /* present = the shadow is on the map */
    DwPuzzleActorPos echo;   /* present = the echo is on the map */
} DwPuzzleDebug;

extern DwPuzzleDebug gDwPuzzleDebug;
/* Test-mode gate (default off). The harness sets it by writing this RAM
 * word (xMAP symbol gDwPuzzleTestMode) before entering the test map. */
extern BOOL gDwPuzzleTestMode;

/* ------------------------------------------------------------------ */
/* Runtime API (dw_puzzle.c)                                         */
/* ------------------------------------------------------------------ */

/* The table for a map, or NULL (no puzzle on this map / test table with
 * test mode off). No progress gate here: DwPuzzle_IsActive / the hook
 * entry points apply the progress gate, because this function has no
 * FieldSystem to read VAR_ARC2_PROGRESS from. Rift tables are in
 * dw_puzzle_<map>.c. */
const DwPuzzleTable *DwPuzzle_GetTable(u32 mapHeader);
void DwPuzzle_SetTestMode(BOOL enabled);
BOOL DwPuzzle_IsTestMode(void);
/* TRUE when a table is loaded for this map at this FieldSystem's progress. */
BOOL DwPuzzle_IsActive(FieldSystem *fieldSystem, u32 mapHeader);

/* Resolved tile state at (x, y, z) on surface, after groups, overrides
 * and actor tiles. Called by the DW walk/collision check (wall/ceiling
 * platforms) and by the floor path
 * (DistWorld_DynamicMapFeaturesCheckCollision). BLOCKED = impassable,
 * SOLID = walkable, VOID = step = fall (the collision check must NOT
 * block VOID, so the player can step onto it). */
DwPuzzleTileState DwPuzzle_QueryTile(FieldSystem *fieldSystem, int x, int y, int z, int surface);

/* Per-map step hook. Call from the per-map HandleStep in ov9_02249960.c
 * (before the map's own step logic) with the player's tile, surface and
 * facing. If out->handled, the per-map hook returns TRUE. If
 * out->fallRequested, start out->fallScriptId. If out->runeRequested, the
 * glue builds a jump-point template from out->rune and starts
 * CreateJumpOnFloatingPlatformTask (steps/cameraSteps 0 = 16; a rune to
 * GROUND becomes platform kind INVALID / index -1). */
BOOL DwPuzzle_HandleStep(FieldSystem *fieldSystem, int x, int y, int z, int surface, int facing, DwPuzzleStepResult *out);

/* Per-frame hook. Call from Arc2Dw_HandleFrame (the DW SysTask) with the
 * player's tile, surface and facing. Applies fade timers, momentary
 * releases, slides, fall detection and respawns; fills out for the glue. */
void DwPuzzle_HandleFrame(FieldSystem *fieldSystem, int x, int y, int z, int surface, int facing, DwPuzzleFrameResult *out);

/* Map-load hook. Call from DistWorld_DynamicMapFeaturesInit. It does NOT
 * reset puzzle state: a fall warp reloads the same map, and the state
 * must survive it. A fresh entry is detected on the first hook call
 * (no fall pending) and resets then. */
void DwPuzzle_OnMapEnter(FieldSystem *fieldSystem, u32 mapHeader);

/*
 * Actor tiles (engine-b): a stone / actor on a tile overrides that
 * tile's state -- a stone landed as a stepping stone is SOLID, a stone
 * sitting on a path is BLOCKED. A stone on a current tile plugs the
 * current (a slide stops before it, because the tile resolves BLOCKED).
 * Up to DW_PUZZLE_MAX_ACTOR_BLOCKS, keyed by (index). Set present =
 * FALSE to clear. Engine-a's own modules never call this. Actor tiles
 * win over groups but lose to explicit table overrides.
 */
void DwPuzzle_SetActorTile(int index, int x, int y, int z, int surface, DwPuzzleTileState state, BOOL present);
void DwPuzzle_ClearActorTiles(void);

/* Sigil presses for occupants other than the player (engine-b's echo).
 * PressSigil fires the sigil at (x, y, z, surface) as occupant, and
 * releases that occupant's momentary sigils elsewhere -- the same
 * press/release the player step hook does for the player, without
 * runes, currents, checkpoints or falls. ReleaseSigils releases all of
 * an occupant's momentary holds (call when the echo leaves the map). */
BOOL DwPuzzle_PressSigil(FieldSystem *fieldSystem, int x, int y, int z, int surface, int occupant);
void DwPuzzle_ReleaseSigils(FieldSystem *fieldSystem, int occupant);

/* Shadow catch (engine-b): restore the puzzle to the last checkpoint
 * snapshot and respawn the player there, without a fall script. The next
 * frame hook reports the respawn in DwPuzzleFrameResult (the glue moves
 * the player). Restore semantics are the snapshot ones: the logical
 * base state is restored (target / solid / display snap to it),
 * momentary holders cleared, fade timers cleared (props snap, no fade),
 * actors notified via resetGeneration. */
void DwPuzzle_RequestCheckpointRespawn(FieldSystem *fieldSystem);

/* A fall the step hook never sees (a scripted fall: DW Eterna Forest's
 * honeycomb, the Lost Tower false-seam drop). Call it synchronously
 * from the fall site, BEFORE the fall script starts. The engine records
 * fall-pending in its own RAM at the moment of the call -- that record
 * survives the fall script clearing its fallVar (HoneyFall clears
 * VAR_MAP_LOCAL_2 first thing), which is why it lives in engine RAM and
 * not in any var. On the fall script's warp, the frame hook restores
 * the last checkpoint snapshot and respawns, exactly as for a
 * VOID-tile fall. No-op without an active table, and idempotent while
 * a fall is already in flight. Generic: any scripted fall can use it. */
void DwPuzzle_NotifyFall(FieldSystem *fieldSystem);

/* Convert a FACE_* on a surface to a (dx, dy, dz) step. Shared with the
 * solver / harness: the same tables the stock DW movement code uses. */
void DwPuzzle_DirDelta(int surface, int dir, int *dx, int *dy, int *dz);

/* Test table (debug-only, Ravaged Path). Registered in dw_puzzle_test.c;
 * returned by DwPuzzle_GetTable only while test mode is on. */
extern const DwPuzzleTable gDwPuzzleTestTable;
extern const DwPuzzleTable gDwPuzzleTestEternaTable;

#endif // POKEPLATINUM_DW_PUZZLE_H
