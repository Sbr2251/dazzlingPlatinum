// Headless proof for the DW puzzle actors (engine-b). Compiles the SAME
// src/overlay009/dw_puzzle_actors.c core with DW_ACTORS_HOST_TEST and drives it with a fake
// platform (a small grid + group bits + a fake player + a fake reset generation) and the
// debug-only test table gDwActorsTestTable. No emulator, no game state.
//
// Build: cc -std=c99 -Wall -Wextra -DDW_ACTORS_HOST_TEST -I include
//   tools/distortion_world/dw_actors_test.c src/overlay009/dw_puzzle_actors.c
//   -o /tmp/dwp/engine-b/dw_actors_test
// Run: /tmp/dwp/engine-b/dw_actors_test > /tmp/dwp/engine-b/actors_test.log
// Frame strips: python3 tools/distortion_world/dw_actors_strip.py < log > strips (see README).

#define DW_ACTORS_HOST_TEST 1
#include <stdio.h>
#include <string.h>

#include "overlay009/dw_puzzle_actors.h"

static int gChecks;
static int gFailures;

#define CHECK(cond) do { \
    gChecks++; \
    if (!(cond)) { gFailures++; printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); } \
} while (0)

// Tile literals: T(x, y, z, surface).
#define T(x, y, z, s) ((DwActorTile){ (x), (y), (z), (s), 0 })
#define WALL(x, y, z) T((x), (y), (z), DW_ACTOR_SURFACE_WEST_WALL)
#define EWALL(x, y, z) T((x), (y), (z), DW_ACTOR_SURFACE_EAST_WALL)
#define GROUND(x, y, z) T((x), (y), (z), DW_ACTOR_SURFACE_GROUND)

// ---------------------------------------------------------------- fake platform

typedef struct {
    int present, x, y, z, surface;
    DwActorTileKind state;
} FakeActorTile;

typedef struct {
    FakeActorTile actorTiles[DW_ACTORS_MAX_STONES];
    int groupBits[8];
    int playerX, playerY, playerZ;
    int inputLocked;
    u32 resetGen;
    int totemDefeated[DW_ACTOR_TOTEM_COUNT];
    int scriptRunning;
    int catchEffects;
    int pressCalls;
    int lastOccupant;
    int echoHolds; // the echo's momentary sigil holds (fake model of engine-a's per-occupant tracking)
    int releaseCalls;
    int respawnCalls;
    int respawnWorks; // 0 = engine-a never restores (watchdog path)
} Fake;

static Fake sFake;

static DwActorTileKind FakeTileAt(void *ctx, int x, int y, int z, int surface)
{
    Fake *f = (Fake *)ctx;
    int i;

    // Actor tiles first (they win over the base grid, like engine-a).
    for (i = 0; i < DW_ACTORS_MAX_STONES; i++) {
        if (f->actorTiles[i].present && f->actorTiles[i].x == x && f->actorTiles[i].y == y
            && f->actorTiles[i].z == z && f->actorTiles[i].surface == surface) {
            return f->actorTiles[i].state;
        }
    }
    if (x == 11 && y >= 2 && y <= 4 && z >= 12 && z <= 20) {
        // West wall. (11,3,18) is the fall edge: VOID.
        if (surface != DW_ACTOR_SURFACE_WEST_WALL) {
            return DW_ACTOR_TILE_BLOCKED; // wrong surface for these coords
        }
        return (y == 3 && z == 18) ? DW_ACTOR_TILE_VOID : DW_ACTOR_TILE_WALKABLE;
    }
    if (x == 49 && y >= 2 && y <= 4 && z >= 12 && z <= 20) {
        // East wall. (49,3,15) is blocked (echo-hide test).
        if (surface != DW_ACTOR_SURFACE_EAST_WALL) {
            return DW_ACTOR_TILE_BLOCKED;
        }
        return (y == 3 && z == 15) ? DW_ACTOR_TILE_BLOCKED : DW_ACTOR_TILE_WALKABLE;
    }
    if (y == 1 && x >= 12 && x <= 22 && z >= 12 && z <= 20) {
        // Ground. (12,1,18) is the gap a stone plugs: VOID until a stone lands.
        if (surface != DW_ACTOR_SURFACE_GROUND) {
            return DW_ACTOR_TILE_BLOCKED;
        }
        return (x == 12 && z == 18) ? DW_ACTOR_TILE_VOID : DW_ACTOR_TILE_WALKABLE;
    }
    return DW_ACTOR_TILE_BLOCKED;
}

static void FakeSetActorTile(void *ctx, int index, int x, int y, int z, int surface, DwActorTileKind state, int present)
{
    Fake *f = (Fake *)ctx;

    f->actorTiles[index].present = present;
    f->actorTiles[index].x = x;
    f->actorTiles[index].y = y;
    f->actorTiles[index].z = z;
    f->actorTiles[index].surface = surface;
    f->actorTiles[index].state = state;
}

static void FakeClearActorTiles(void *ctx)
{
    Fake *f = (Fake *)ctx;
    int i;

    for (i = 0; i < DW_ACTORS_MAX_STONES; i++) {
        f->actorTiles[i].present = 0;
    }
}

// The fake engine-a sigil map: pad tiles + the echo sigil tile, with their group effects.
static int FakePressSigil(void *ctx, int x, int y, int z, int surface, int occupant)
{
    Fake *f = (Fake *)ctx;

    (void)y;
    f->pressCalls++;
    f->lastOccupant = occupant;
    if (surface == DW_ACTOR_SURFACE_GROUND && x == 12 && z == 13) {
        f->groupBits[0] = 0; // Hitmonlee pad: crystal group off
        return TRUE;
    }
    if (surface == DW_ACTOR_SURFACE_GROUND && x == 12 && z == 14) {
        f->groupBits[1] = 1; // Vespiquen pad: hidden tiles on
        return TRUE;
    }
    if (surface == DW_ACTOR_SURFACE_GROUND && x == 12 && z == 15) {
        f->groupBits[2] = 1; // Lapras pad: sunk stones on
        return TRUE;
    }
    if (surface == DW_ACTOR_SURFACE_GROUND && x == 12 && z == 16) {
        return TRUE; // Skarmory pad: no-op group (the script carries)
    }
    if (surface == DW_ACTOR_SURFACE_EAST_WALL && x == 49 && z == 18) {
        f->groupBits[2] = 1; // echo sigil (momentary in this fake model: held until released)
        if (occupant == DW_ACTOR_OCCUPANT_ECHO) {
            f->echoHolds = 1;
        }
        return TRUE;
    }
    return FALSE; // no sigil at this tile (table error)
}

static void FakeReleaseSigils(void *ctx, int occupant)
{
    Fake *f = (Fake *)ctx;

    if (occupant == DW_ACTOR_OCCUPANT_ECHO) {
        f->echoHolds = 0;
    }
    f->releaseCalls++;
}

static void FakeRequestCheckpointRespawn(void *ctx)
{
    Fake *f = (Fake *)ctx;

    f->respawnCalls++;
    if (f->respawnWorks) {
        f->resetGen++; // engine-a restores + bumps the reset generation
    }
}

static void FakeSetPlayerTile(void *ctx, int x, int y, int z)
{
    Fake *f = (Fake *)ctx;

    f->playerX = x;
    f->playerY = y;
    f->playerZ = z;
}

static void FakeSetInputLocked(void *ctx, int locked)
{
    ((Fake *)ctx)->inputLocked = locked;
}

static int FakeIsScriptRunning(void *ctx)
{
    return ((Fake *)ctx)->scriptRunning;
}

static int FakeTotemDefeated(void *ctx, int totem)
{
    return ((Fake *)ctx)->totemDefeated[totem];
}

static u32 FakeGetResetGeneration(void *ctx)
{
    return ((Fake *)ctx)->resetGen;
}

static void FakePlayCatchEffect(void *ctx)
{
    ((Fake *)ctx)->catchEffects++;
}

static DwActorPlatform FakePlatform(Fake *f)
{
    DwActorPlatform p;

    memset(&p, 0, sizeof(p));
    p.tileAt = FakeTileAt;
    p.setActorTile = FakeSetActorTile;
    p.clearActorTiles = FakeClearActorTiles;
    p.pressSigil = FakePressSigil;
    p.releaseSigils = FakeReleaseSigils;
    p.requestCheckpointRespawn = FakeRequestCheckpointRespawn;
    p.setPlayerTile = FakeSetPlayerTile;
    p.setInputLocked = FakeSetInputLocked;
    p.isScriptRunning = FakeIsScriptRunning;
    p.totemDefeated = FakeTotemDefeated;
    p.getResetGeneration = FakeGetResetGeneration;
    p.playCatchEffect = FakePlayCatchEffect;
    p.ctx = f;
    return p;
}

static void Fresh(void)
{
    DwActorPlatform p;

    DwActors_OnExit();
    memset(&sFake, 0, sizeof(sFake));
    sFake.playerX = 12;
    sFake.playerY = 1;
    sFake.playerZ = 12;
    sFake.totemDefeated[DW_ACTOR_TOTEM_HITMONLEE] = 1;
    sFake.totemDefeated[DW_ACTOR_TOTEM_VESPIQUEN] = 1;
    sFake.totemDefeated[DW_ACTOR_TOTEM_LAPRAS] = 1;
    sFake.totemDefeated[DW_ACTOR_TOTEM_SKARMORY] = 0;
    sFake.respawnWorks = 1;
    p = FakePlatform(&sFake);
    DwActors_Init(&gDwActorsTestTable, &p);
}

static void LogFallFrame(int frame)
{
    DwActorDebug dbg;

    DwActors_FillDebug(&dbg);
    printf("FRAME fall %d stone0=%d,%d,%d state=%d blocks=%d,%d override=%d\n", frame,
        dbg.stoneTiles[0][0], dbg.stoneTiles[0][1], dbg.stoneTiles[0][2], dbg.stoneStates[0],
        sFake.actorTiles[0].present, sFake.actorTiles[1].present,
        (int)FakeTileAt(&sFake, 12, 1, 18, DW_ACTOR_SURFACE_GROUND));
}

static void LogShadowFrame(int frame)
{
    DwActorDebug dbg;

    DwActors_FillDebug(&dbg);
    printf("FRAME shadow %d phase=%d tile=%d,%d,%d state=%d grace_player=12,1,20\n", frame,
        dbg.shadowPhase, dbg.shadowTile[0], dbg.shadowTile[1], dbg.shadowTile[2], dbg.shadowState);
}

// ---------------------------------------------------------------- scenarios

static void TestPush(void)
{
    DwActorDebug dbg;

    Fresh();
    // Stone 0: (11,3,14). Player 13 -> 14 pushes it to 15.
    CHECK(DwActors_TryPush(WALL(11, 3, 13), WALL(11, 3, 14)) == TRUE);
    DwActors_HandlePlayerStep(WALL(11, 3, 13), WALL(11, 3, 14));
    DwActors_FillDebug(&dbg);
    CHECK(dbg.stoneTiles[0][2] == 15);
    CHECK(sFake.actorTiles[0].present == 1 && sFake.actorTiles[0].z == 15);
    CHECK(sFake.actorTiles[0].state == DW_ACTOR_TILE_BLOCKED);
    // Echo: player (11,3,14) -> echo (49,3,18), which is the echo sigil: PressSigil as ECHO.
    CHECK(dbg.echoTile[0] == 49 && dbg.echoTile[2] == 18);
    CHECK(sFake.groupBits[2] == 1);
    CHECK(dbg.echoSigilPresses == 1);
    CHECK(sFake.lastOccupant == DW_ACTOR_OCCUPANT_ECHO);
    // Push into stone 1 at (11,3,16): player 14 -> 15, stone 0 would go to 16. Blocked.
    CHECK(DwActors_TryPush(WALL(11, 3, 14), WALL(11, 3, 15)) == FALSE);
    DwActors_FillDebug(&dbg);
    CHECK(dbg.stoneTiles[0][2] == 15);
    // Back to start, then push into the protected tile (11,3,13): player 15 -> 14. Blocked.
    DwActors_ResetStones();
    CHECK(DwActors_TryPush(WALL(11, 3, 15), WALL(11, 3, 14)) == FALSE);
    DwActors_FillDebug(&dbg);
    CHECK(dbg.stoneTiles[0][2] == 14);
    // A non-unit delta (a jump: prev 12, cur 14) does not push.
    CHECK(DwActors_TryPush(WALL(11, 3, 12), WALL(11, 3, 14)) == FALSE);
    DwActors_FillDebug(&dbg);
    CHECK(dbg.stoneTiles[0][2] == 14);
    // A surface-changing step never pushes.
    CHECK(DwActors_TryPush(GROUND(12, 1, 12), WALL(11, 3, 14)) == TRUE);
    DwActors_FillDebug(&dbg);
    CHECK(dbg.stoneTiles[0][2] == 14);
    // Landing tiles are reserved: a stone on the ground cannot be pushed onto (12,1,18).
    {
        DwActorTable t = gDwActorsTestTable;
        DwActorPlatform p;

        DwActors_OnExit();
        memset(&sFake, 0, sizeof(sFake));
        sFake.respawnWorks = 1;
        t.stones[1].start = GROUND(12, 1, 17);
        t.stones[1].edgeCount = 0;
        p = FakePlatform(&sFake);
        DwActors_Init(&t, &p);
        CHECK(DwActors_TryPush(GROUND(12, 1, 16), GROUND(12, 1, 17)) == FALSE);
    }
}

static void TestFallAndReset(void)
{
    DwActorTable t = gDwActorsTestTable;
    DwActorPlatform p;
    DwActorDebug dbg;
    int frame;

    DwActors_OnExit();
    memset(&sFake, 0, sizeof(sFake));
    sFake.totemDefeated[DW_ACTOR_TOTEM_HITMONLEE] = 1;
    sFake.respawnWorks = 1;
    // Move stone 1 out of stone 0's path so stone 0 can reach the edge at (11,3,18).
    t.stones[1].start = WALL(11, 3, 19);
    p = FakePlatform(&sFake);
    DwActors_Init(&t, &p);
    // Push stone 0 along the wall: 14->15->16->17, then 17->edge(18) starts the fall.
    CHECK(DwActors_TryPush(WALL(11, 3, 13), WALL(11, 3, 14)) == TRUE);
    CHECK(DwActors_TryPush(WALL(11, 3, 14), WALL(11, 3, 15)) == TRUE);
    CHECK(DwActors_TryPush(WALL(11, 3, 15), WALL(11, 3, 16)) == TRUE);
    DwActors_FillDebug(&dbg);
    CHECK(dbg.stoneTiles[0][2] == 17);
    CHECK(DwActors_TryPush(WALL(11, 3, 16), WALL(11, 3, 17)) == TRUE); // into the edge: starts falling
    DwActors_FillDebug(&dbg);
    CHECK(dbg.stoneStates[0] == DW_ACTOR_STONE_FALLING);
    CHECK(dbg.stoneTiles[0][2] == 18);
    LogFallFrame(0);
    // Mid-fall: the falling stone occupies no tile and registers no actor tile.
    for (frame = 1; frame <= 3; frame++) {
        DwActors_HandleFrame(WALL(11, 3, 17));
        LogFallFrame(frame);
    }
    CHECK(DwActors_IsStoneAt(WALL(11, 3, 18)) == FALSE);
    CHECK(sFake.actorTiles[0].present == 0);
    // Checkpoint reached mid-fall: snapshot the falling stone (timer included).
    DwActors_OnCheckpoint();
    for (frame = 4; frame <= 12; frame++) {
        DwActors_HandleFrame(WALL(11, 3, 17));
        LogFallFrame(frame);
    }
    DwActors_FillDebug(&dbg);
    CHECK(dbg.stoneStates[0] == DW_ACTOR_STONE_LANDED);
    CHECK(dbg.stoneTiles[0][0] == 12 && dbg.stoneTiles[0][1] == 1 && dbg.stoneTiles[0][2] == 18);
    CHECK(dbg.stoneSurfaces[0] == DW_ACTOR_SURFACE_GROUND);
    CHECK(FakeTileAt(&sFake, 12, 1, 18, DW_ACTOR_SURFACE_GROUND) == DW_ACTOR_TILE_SOLID);
    // A LANDED stone is terrain: walkable, not pushable, and its actor tile is SOLID.
    CHECK(DwActors_IsStoneAt(GROUND(12, 1, 18)) == FALSE);
    CHECK(sFake.actorTiles[0].present == 1 && sFake.actorTiles[0].state == DW_ACTOR_TILE_SOLID);
    CHECK(DwActors_TryPush(GROUND(12, 1, 17), GROUND(12, 1, 18)) == TRUE);
    // Reset generation (fall / catch / RESET sigil): restore the mid-fall snapshot.
    sFake.resetGen++;
    DwActors_HandleFrame(WALL(11, 3, 17));
    DwActors_FillDebug(&dbg);
    CHECK(dbg.stoneStates[0] == DW_ACTOR_STONE_FALLING);
    CHECK(dbg.stoneTiles[0][2] == 18);
    for (frame = 1; frame <= 9; frame++) {
        DwActors_HandleFrame(WALL(11, 3, 17));
    }
    DwActors_FillDebug(&dbg);
    CHECK(dbg.stoneStates[0] == DW_ACTOR_STONE_LANDED);
    CHECK(FakeTileAt(&sFake, 12, 1, 18, DW_ACTOR_SURFACE_GROUND) == DW_ACTOR_TILE_SOLID);
    // Explicit to-start reset: stones home, actor tiles re-registered at the start.
    DwActors_ResetStones();
    DwActors_FillDebug(&dbg);
    CHECK(dbg.stoneTiles[0][2] == 14);
    CHECK(dbg.stoneStates[0] == DW_ACTOR_STONE_RESTING);
    CHECK(FakeTileAt(&sFake, 12, 1, 18, DW_ACTOR_SURFACE_GROUND) == DW_ACTOR_TILE_VOID);
}

static void TestResetGenerationAfterInit(void)
{
    DwActorDebug dbg;

    // Reset generation captured at Init: a reset sigil after Init restores, never missed.
    // (The snapshot here is Init's: the initial state, not a mid-fall snapshot.)
    Fresh();
    CHECK(DwActors_TryPush(WALL(11, 3, 13), WALL(11, 3, 14)) == TRUE);
    DwActors_FillDebug(&dbg);
    CHECK(dbg.stoneTiles[0][2] == 15);
    sFake.resetGen++;
    DwActors_HandleFrame(WALL(11, 3, 14));
    DwActors_FillDebug(&dbg);
    CHECK(dbg.stoneTiles[0][2] == 14); // back to the Init snapshot
}

static void TestShadow(void)
{
    DwActorDebug dbg;
    int frame;

    Fresh();
    // Patrol: beat 6, pingpong over (12,1,12..16). Log frames for the strip.
    for (frame = 1; frame <= 36; frame++) {
        DwActors_HandleFrame(GROUND(12, 1, 20));
        if (frame % 6 == 0) {
            LogShadowFrame(frame);
        }
    }
    DwActors_FillDebug(&dbg);
    CHECK(dbg.shadowPhase == 2); // 6 advances: 0,1,2,3,4,3,2
    CHECK(dbg.shadowTile[2] == 14);
    // Snapshot at phase 2 with pingpong direction -1 (the patrol just turned), advance to
    // phase 0, restore via the reset generation: phase AND direction come back.
    DwActors_OnCheckpoint();
    for (frame = 0; frame < 12; frame++) {
        DwActors_HandleFrame(GROUND(12, 1, 20));
    }
    DwActors_FillDebug(&dbg);
    CHECK(dbg.shadowPhase == 0);
    sFake.resetGen++;
    DwActors_HandleFrame(GROUND(12, 1, 20));
    DwActors_FillDebug(&dbg);
    CHECK(dbg.shadowPhase == 2);
    CHECK(dbg.shadowTile[2] == 14);

    // Grace: standing on the shadow's tile during grace does not catch.
    Fresh();
    for (frame = 0; frame < 29; frame++) {
        DwActorDebug d2;

        // Player stands far away while grace runs down; no catch even on overlap frames
        // (the shadow never overlaps the far tile here, but grace must not catch anyway).
        DwActors_HandleFrame(GROUND(12, 1, 20));
        DwActors_FillDebug(&d2);
        CHECK(d2.shadowState == DW_ACTOR_SHADOW_PATROL);
    }
    // Grace expires on the next frame. The shadow advances first (phase 4 -> 3, tile
    // (12,1,15)), so a player standing on the tile it advances ONTO is caught.
    {
        DwActorDebug d2;

        DwActors_FillDebug(&d2);
        CHECK(d2.shadowTile[2] == 16); // phase 4, one frame before the beat
        DwActors_HandleFrame(GROUND(12, 1, 15));
        DwActors_FillDebug(&d2);
        CHECK(d2.shadowState == DW_ACTOR_SHADOW_CAUGHT);
        CHECK(d2.caughtCount == 1);
    }
    CHECK(sFake.inputLocked == 1);
    CHECK(sFake.catchEffects == 1);
    // 30-frame freeze, then exactly one checkpoint-respawn request (latched).
    for (frame = 0; frame < 30; frame++) {
        DwActors_HandleFrame(GROUND(12, 1, 20));
    }
    DwActors_FillDebug(&dbg);
    CHECK(dbg.respawnRequests == 1);
    CHECK(sFake.respawnCalls == 1);
    // Engine-a restores + bumps the generation: snapshot restore, input unlocked.
    DwActors_HandleFrame(GROUND(12, 1, 20));
    DwActors_FillDebug(&dbg);
    CHECK(dbg.shadowState == DW_ACTOR_SHADOW_PATROL);
    CHECK(dbg.shadowPhase == 0);
    CHECK(sFake.inputLocked == 0);
    CHECK(dbg.caughtCount == 1);

    // Watchdog: when engine-a never restores, the catch self-heals after 60 frames.
    Fresh();
    sFake.respawnWorks = 0;
    for (frame = 0; frame < 29; frame++) {
        DwActors_HandleFrame(GROUND(12, 1, 20));
    }
    DwActors_HandleFrame(GROUND(12, 1, 15)); // caught (as above)
    for (frame = 0; frame < 30; frame++) {
        DwActors_HandleFrame(GROUND(12, 1, 20));
    }
    DwActors_FillDebug(&dbg);
    CHECK(dbg.respawnRequests == 1);
    CHECK(sFake.respawnCalls == 1);
    for (frame = 0; frame < 60; frame++) {
        DwActors_HandleFrame(GROUND(12, 1, 20));
    }
    DwActors_FillDebug(&dbg);
    CHECK(dbg.shadowState == DW_ACTOR_SHADOW_PATROL);
    CHECK(dbg.respawnRequests == 1); // issued once, never re-issued
    CHECK(sFake.inputLocked == 0);
}

static void TestEcho(void)
{
    DwActorDebug dbg;
    int releases;

    Fresh();
    // Player (11,3,14) -> echo (49,3,18) on its sigil: PressSigil as ECHO, fires once.
    DwActors_HandlePlayerStep(WALL(11, 3, 13), WALL(11, 3, 14));
    DwActors_FillDebug(&dbg);
    CHECK(dbg.echoTile[0] == 49 && dbg.echoTile[2] == 18);
    CHECK(dbg.echoSigilPresses == 1);
    CHECK(sFake.groupBits[2] == 1);
    CHECK(sFake.lastOccupant == DW_ACTOR_OCCUPANT_ECHO);
    // Player steps back onto the same echo configuration: no refire (desired unchanged).
    DwActors_HandlePlayerStep(WALL(11, 3, 15), WALL(11, 3, 14));
    DwActors_FillDebug(&dbg);
    CHECK(dbg.echoSigilPresses == 1);
    CHECK(sFake.echoHolds == 1); // the momentary echo sigil is held
    // Echo moves to a NON-sigil tile: its momentary hold releases on the move.
    DwActors_ResetStones(); // stone 0 back to 14, so the step below is not a push
    DwActors_HandlePlayerStep(WALL(11, 3, 14), WALL(11, 3, 15));
    DwActors_FillDebug(&dbg);
    CHECK(dbg.echoTile[0] == 49 && dbg.echoTile[2] == 17);
    CHECK(sFake.echoHolds == 0);
    CHECK(dbg.echoSigilPresses == 1); // no press on a non-sigil tile
    // Player (11,3,17) -> echo desired (49,3,15) is BLOCKED: echo hides (not last-valid),
    // and hiding releases the echo's momentary holds.
    releases = sFake.releaseCalls;
    DwActors_HandlePlayerStep(WALL(11, 3, 16), WALL(11, 3, 17));
    DwActors_FillDebug(&dbg);
    CHECK(dbg.echoTile[0] == -1);
    CHECK(dbg.echoBlocked == 1);
    CHECK(sFake.releaseCalls == releases + 1);
    // ...and the blocked echo never blocks the player: TryPush is unaffected.
    CHECK(DwActors_TryPush(WALL(11, 3, 16), WALL(11, 3, 17)) == TRUE);
    // Player back to (11,3,14): the step pushes stone 0 aside (14->15) and the echo
    // reappears on the sigil (re-entry fires again).
    DwActors_HandlePlayerStep(WALL(11, 3, 13), WALL(11, 3, 14));
    DwActors_FillDebug(&dbg);
    CHECK(dbg.echoTile[0] == 49 && dbg.echoTile[2] == 18);
    CHECK(dbg.echoSigilPresses == 2);
    // Player off the paired surface (ground): echo hides.
    DwActors_HandlePlayerStep(WALL(11, 3, 14), GROUND(12, 1, 12));
    DwActors_FillDebug(&dbg);
    CHECK(dbg.echoTile[0] == -1);
    CHECK(dbg.echoBlocked == 0);
    // First activation on an unenterable desired tile: starts hidden (no previous tile).
    DwActors_HandlePlayerStep(GROUND(12, 1, 12), WALL(11, 3, 17));
    DwActors_FillDebug(&dbg);
    CHECK(dbg.echoTile[0] == -1);
    CHECK(dbg.echoBlocked == 1);
}

static void TestPads(void)
{
    DwActorDebug dbg;
    DwActorEvent ev;
    int phase, presses;

    Fresh();
    sFake.groupBits[0] = 1;
    sFake.groupBits[1] = 0;
    sFake.groupBits[2] = 0;
    // Hitmonlee pad: No -> nothing (PressSigil not called). Yes -> CUTIN, group 0 off.
    ev = DwActors_HandlePlayerStep(GROUND(12, 1, 12), GROUND(12, 1, 13));
    CHECK(ev == DW_ACTOR_EVENT_PAD_READY);
    presses = sFake.pressCalls;
    CHECK(DwActors_ResolvePad(0, FALSE) == DW_ACTOR_EVENT_NONE);
    CHECK(sFake.pressCalls == presses);
    DwActors_FillDebug(&dbg);
    CHECK(dbg.padUsed == 0);
    ev = DwActors_HandlePlayerStep(GROUND(12, 1, 12), GROUND(12, 1, 13));
    CHECK(ev == DW_ACTOR_EVENT_PAD_READY);
    // The patrol freezes while the pad prompt is pending.
    DwActors_FillDebug(&dbg);
    phase = dbg.shadowPhase;
    for (int f = 0; f < 20; f++) {
        DwActors_HandleFrame(GROUND(12, 1, 20));
    }
    DwActors_FillDebug(&dbg);
    CHECK(dbg.shadowPhase == phase);
    ev = DwActors_ResolvePad(0, TRUE);
    CHECK(ev == DW_ACTOR_EVENT_CUTIN);
    CHECK(DwActors_TakePendingCutin() == DW_ACTOR_TOTEM_HITMONLEE);
    CHECK(DwActors_TakePendingCutin() == -1);
    CHECK(sFake.lastOccupant == DW_ACTOR_OCCUPANT_PLAYER);
    DwActors_FillDebug(&dbg);
    CHECK(dbg.padUsed == 1);
    CHECK(sFake.groupBits[0] == 0);
    // Vespiquen pad: group 1 on.
    ev = DwActors_HandlePlayerStep(GROUND(12, 1, 13), GROUND(12, 1, 14));
    CHECK(ev == DW_ACTOR_EVENT_PAD_READY);
    CHECK(DwActors_ResolvePad(1, TRUE) == DW_ACTOR_EVENT_CUTIN);
    CHECK(sFake.groupBits[1] == 1);
    // Lapras pad: group 2 on.
    ev = DwActors_HandlePlayerStep(GROUND(12, 1, 14), GROUND(12, 1, 15));
    CHECK(ev == DW_ACTOR_EVENT_PAD_READY);
    CHECK(DwActors_ResolvePad(2, TRUE) == DW_ACTOR_EVENT_CUTIN);
    CHECK(sFake.groupBits[2] == 1);
    // Skarmory pad, totem NOT calmed: denied, explicitly NOT used.
    ev = DwActors_HandlePlayerStep(GROUND(12, 1, 15), GROUND(12, 1, 16));
    CHECK(ev == DW_ACTOR_EVENT_PAD_READY);
    CHECK(DwActors_ResolvePad(3, TRUE) == DW_ACTOR_EVENT_NONE);
    DwActors_FillDebug(&dbg);
    CHECK(dbg.padDenied == 1);
    CHECK((dbg.padUsed & 8) == 0);
    // Skarmory pad, totem calmed: CARRY_REQUESTED, carry pending, shadow frozen.
    sFake.totemDefeated[DW_ACTOR_TOTEM_SKARMORY] = 1;
    ev = DwActors_HandlePlayerStep(GROUND(12, 1, 15), GROUND(12, 1, 16));
    CHECK(ev == DW_ACTOR_EVENT_PAD_READY);
    CHECK(DwActors_ResolvePad(3, TRUE) == DW_ACTOR_EVENT_CARRY_REQUESTED);
    CHECK(DwActors_TakePendingCutin() == DW_ACTOR_TOTEM_SKARMORY);
    DwActors_FillDebug(&dbg);
    CHECK(dbg.carryPending == 3);
    CHECK((dbg.padUsed & 8) != 0);
    DwActors_FillDebug(&dbg);
    phase = dbg.shadowPhase;
    for (int f = 0; f < 20; f++) {
        DwActors_HandleFrame(GROUND(12, 1, 20));
    }
    DwActors_FillDebug(&dbg);
    CHECK(dbg.shadowPhase == phase);
    DwActors_ConfirmCarryDone();
    DwActors_FillDebug(&dbg);
    CHECK(dbg.carryPending == -1);
    // Stale answer: pad 0 is used, so stepping on it no longer arms it; ResolvePad ignores it.
    ev = DwActors_HandlePlayerStep(GROUND(12, 1, 14), GROUND(12, 1, 13));
    CHECK(ev == DW_ACTOR_EVENT_NONE);
    CHECK(DwActors_ResolvePad(0, TRUE) == DW_ACTOR_EVENT_NONE);
    // Missing sigil (table error): the pad stays unused, nothing fires.
    {
        DwActorTable t = gDwActorsTestTable;
        DwActorPlatform p;

        DwActors_OnExit();
        memset(&sFake, 0, sizeof(sFake));
        sFake.respawnWorks = 1;
        sFake.totemDefeated[DW_ACTOR_TOTEM_HITMONLEE] = 1;
        t.pads[0].tile = GROUND(12, 1, 19); // no sigil in the fake map at this tile
        p = FakePlatform(&sFake);
        DwActors_Init(&t, &p);
        ev = DwActors_HandlePlayerStep(GROUND(12, 1, 12), GROUND(12, 1, 19));
        CHECK(ev == DW_ACTOR_EVENT_PAD_READY);
        CHECK(DwActors_ResolvePad(0, TRUE) == DW_ACTOR_EVENT_NONE);
        DwActors_FillDebug(&dbg);
        CHECK((dbg.padUsed & 1) == 0);
    }
    // Reset generation restores the checkpoint snapshot: pad bits back to 0 (checkpoint was
    // taken at Init, before any pad use). Groups are engine-a's to restore, not actors'.
    Fresh();
    ev = DwActors_HandlePlayerStep(GROUND(12, 1, 12), GROUND(12, 1, 13));
    CHECK(ev == DW_ACTOR_EVENT_PAD_READY);
    CHECK(DwActors_ResolvePad(0, TRUE) == DW_ACTOR_EVENT_CUTIN);
    sFake.resetGen++;
    DwActors_HandleFrame(GROUND(12, 1, 12));
    DwActors_FillDebug(&dbg);
    CHECK(dbg.padUsed == 0);
    CHECK(dbg.carryPending == -1);
}

static void TestExit(void)
{
    DwActorDebug dbg;
    int releases;

    Fresh();
    CHECK(DwActors_TryPush(WALL(11, 3, 13), WALL(11, 3, 14)) == TRUE);
    releases = sFake.releaseCalls;
    DwActors_OnExit();
    DwActors_FillDebug(&dbg);
    CHECK(dbg.stoneCount == 0);
    CHECK(dbg.shadowTile[0] == -1);
    CHECK(dbg.echoTile[0] == -1);
    CHECK(dbg.pendingPad == -1);
    CHECK(dbg.carryPending == -1);
    CHECK(sFake.actorTiles[0].present == 0);
    CHECK(sFake.releaseCalls == releases + 1); // echo holds released on departure
    CHECK(sFake.inputLocked == 0);
    // Idempotent: exiting twice is safe, and stepping after exit is inert.
    DwActors_OnExit();
    CHECK(DwActors_TryPush(WALL(11, 3, 13), WALL(11, 3, 14)) == TRUE);
    CHECK(DwActors_HandlePlayerStep(WALL(11, 3, 13), WALL(11, 3, 14)) == DW_ACTOR_EVENT_NONE);
}

static void TestInitClamp(void)
{
    DwActorTable t = gDwActorsTestTable;
    DwActorPlatform p;
    DwActorDebug dbg;

    DwActors_OnExit();
    memset(&sFake, 0, sizeof(sFake));
    sFake.respawnWorks = 1;
    t.stoneCount = 99; // malformed: clamped to DW_ACTORS_MAX_STONES, no overrun
    t.shadow.beatFrames = 0; // malformed: clamped to 1 (advances every frame)
    t.padCount = 99; // malformed: clamped to DW_ACTORS_MAX_PADS
    p = FakePlatform(&sFake);
    DwActors_Init(&t, &p);
    DwActors_FillDebug(&dbg);
    CHECK(dbg.stoneCount == DW_ACTORS_MAX_STONES);
    DwActors_HandleFrame(GROUND(12, 1, 20));
    DwActors_FillDebug(&dbg);
    CHECK(dbg.shadowPhase == 1);
    // The clamped pad loop is intact: stepping on pad 3 still arms it.
    CHECK(DwActors_HandlePlayerStep(GROUND(12, 1, 12), GROUND(12, 1, 16)) == DW_ACTOR_EVENT_PAD_READY);
}

static void TestMakeShadowLane(void)
{
    DwActorShadowDef def;

    CHECK(DwActors_MakeShadowLane(&def, GROUND(12, 1, 12), GROUND(12, 1, 16), 50) == TRUE);
    CHECK(def.tileCount == 5 && def.beatFrames == 50 && def.pingpong == 1);
    CHECK(def.tiles[0].z == 12 && def.tiles[4].z == 16);
    CHECK(def.tiles[0].surface == DW_ACTOR_SURFACE_GROUND);
    CHECK(DwActors_MakeShadowLane(&def, WALL(11, 2, 14), WALL(11, 4, 14), 45) == TRUE);
    CHECK(def.tileCount == 3 && def.tiles[2].y == 4);
    CHECK(DwActors_MakeShadowLane(&def, GROUND(12, 1, 12), GROUND(13, 1, 13), 50) == FALSE);
    CHECK(DwActors_MakeShadowLane(&def, GROUND(12, 1, 12), GROUND(12, 1, 16), 0) == FALSE);
    // Different surfaces: not a lane on one surface.
    CHECK(DwActors_MakeShadowLane(&def, GROUND(12, 1, 12), WALL(11, 3, 14), 50) == FALSE);
    // Wall lane crossing the y==1 seam corner: rejected.
    CHECK(DwActors_MakeShadowLane(&def, WALL(11, 1, 14), WALL(11, 3, 14), 50) == FALSE);
    // Wall lane moving in x (off the wall plane): rejected.
    CHECK(DwActors_MakeShadowLane(&def, WALL(11, 3, 14), WALL(12, 3, 14), 50) == FALSE);
}

int main(void)
{
    TestMakeShadowLane();
    TestInitClamp();
    TestPush();
    TestFallAndReset();
    TestResetGenerationAfterInit();
    TestShadow();
    TestEcho();
    TestPads();
    TestExit();
    printf("actors_test: %d checks, %d failures\n", gChecks, gFailures);
    return gFailures != 0;
}
