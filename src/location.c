#include "location.h"

#include "generated/map_headers.h"

#include "field_overworld_state.h"
#include "savedata.h"

static const Location sPlayerStartLocation = {
    .mapId = MAP_HEADER_TWINLEAF_TOWN_PLAYER_HOUSE_2F,
    .warpId = WARP_ID_NONE,
    .x = 4,
    .z = 6,
    .faceDirection = FACE_UP,
};

// Arc 1: a new game opens on the Distortion World flashback in the Giratina room
// (scripts_distortion_world_giratina_room.s, VAR_ARC1_PROGRESS == 0), which then warps to
// Lake Verity. sPlayerStartLocation above stays the bedroom: the Hall of Fame respawn uses it.
static const Location sNewGameStartLocation = {
    .mapId = MAP_HEADER_DISTORTION_WORLD_GIRATINA_ROOM,
    .warpId = WARP_ID_NONE,
    .x = 15,
    .z = 15,
    .faceDirection = FACE_UP,
};

static const Location sPlayerFirstRespawnLocation = {
    .mapId = MAP_HEADER_TWINLEAF_TOWN,
    .warpId = WARP_ID_NONE,
    .x = 116,
    .z = 886,
    .faceDirection = FACE_DOWN,
};

void SetPlayerStartLocation(Location *outLocation)
{
    *outLocation = sPlayerStartLocation;
}

void SetPlayerFirstRespawnLocation(Location *outLocation)
{
    *outLocation = sPlayerFirstRespawnLocation;
}

void InitPlayerStartLocation(SaveData *saveData)
{
    *FieldOverworldState_GetPlayerLocation(SaveData_GetFieldOverworldState(saveData)) = sNewGameStartLocation;
}
