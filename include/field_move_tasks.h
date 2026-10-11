#ifndef POKEPLATINUM_FIELD_MOVE_TASKS_H
#define POKEPLATINUM_FIELD_MOVE_TASKS_H

#include "struct_decls/struct_02061AB4_decl.h"

#include "field/field_system_decl.h"

#include "field_task.h"
#include "pokemon.h"

typedef struct FieldMoveContext {
    u32 mapId;
    FieldSystem *fieldSystem;
    MapObject *mapObj;
    u16 usableMoves;
} FieldMoveContext;

typedef struct FieldMovePokemon {
    FieldTask *fieldTask;
    u16 fieldMonId;
    u16 fieldMove;
} FieldMovePokemon;

enum FieldMoveList {
    FIELD_MOVE_CUT,
    FIELD_MOVE_FLY, // unused
    FIELD_MOVE_SURF,
    FIELD_MOVE_STRENGTH,
    FIELD_MOVE_DEFOG,
    FIELD_MOVE_ROCK_SMASH,
    FIELD_MOVE_WATERFALL,
    FIELD_MOVE_ROCK_CLIMB,
    FIELD_MOVE_FLASH,
};

enum FieldMoveError {
    FIELD_MOVE_ERROR_NONE,
    FIELD_MOVE_ERROR_LOCATION,
    FIELD_MOVE_ERROR_BADGE,
    FIELD_MOVE_ERROR_PARTNER,
    FIELD_MOVE_ERROR_STATE,
    FIELD_MOVE_ERROR_TOTEM,
};

enum TaskOrError {
    FIELD_MOVE_TASK,
    FIELD_MOVE_ERROR,
};

typedef void (*FieldMoveTaskContext)(FieldMovePokemon *, const FieldMoveContext *);
typedef enum FieldMoveError (*FieldMoveErrContext)(const FieldMoveContext *);

// Arc 2 Resonator (S8, D10/D11). Field obstacles are cleared by the Resonator, never by a party Pokemon: each power
// needs ITEM_RESONATOR in the bag, its Gym badge and its FLAG_TOTEM_*_DEFEATED. The field-move scripts pass
// RESONATOR_SLOT(fieldMove) in place of a party slot to the cut-in and the Use* commands; the performer is then the
// power's totem, drawn as a ghost. Keep in sync with RESONATOR_SLOT_* in res/field/scripts/scripts_field_moves.s.
#define RESONATOR_SLOT_BASE       0xF0
#define RESONATOR_SLOT(fieldMove) (RESONATOR_SLOT_BASE + (fieldMove))

void *FieldMove_GetTaskOrError(u16 taskOrError, u16 fieldMove);
void FieldMoves_SetUsableMoves(FieldSystem *fieldSystem, FieldMoveContext *fieldMoveContext);
BOOL FieldMoves_IsHMUnlocked(FieldSystem *fieldSystem, u16 move);
Pokemon *FieldMoves_GetHMPerformer(FieldSystem *fieldSystem, int partySlot);
Pokemon *FieldMoves_GetFlyPerformer(FieldSystem *fieldSystem, int partySlot);
BOOL FieldMoves_IsResonatorObstacleMove(u16 move);
BOOL FieldMoves_IsResonatorGhost(const Pokemon *mon);
void FieldMoves_ApplyResonatorGhostPalette(const Pokemon *mon, u16 *palette, int numColors);
u16 FieldMoves_GetFogInteractScript(FieldSystem *fieldSystem);

// Arc 2 Resonator echoes (S8): ghost actors (local IDs 0xC0-0xC7, opacity in VAR_MAP_LOCAL_5). Called by
// MapObjectTask_Draw after each map object draws.
void FieldMoves_EchoGhostDraw(MapObject *mapObj);

#endif // POKEPLATINUM_FIELD_MOVE_TASKS_H
