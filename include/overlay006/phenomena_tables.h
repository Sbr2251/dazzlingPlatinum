#ifndef POKEPLATINUM_OVERLAY006_PHENOMENA_TABLES_H
#define POKEPLATINUM_OVERLAY006_PHENOMENA_TABLES_H

#include <nitro/types.h>

#include "constants/fieldmap.h"
#include "generated/items.h"
#include "generated/species.h"

enum PhenomenonType {
    PHENOMENON_NONE = 0,
    PHENOMENON_GRASS = 1,
    PHENOMENON_DUST = 2,
    PHENOMENON_WATER = 3,
    PHENOMENON_SHADOW = 4,
};

typedef struct PhenomenonSlot {
    u16 species;
    u8 weight;
    u8 minLevel;
} PhenomenonSlot;

typedef struct PhenomenonItemSlot {
    u16 item;
    u8 weight;
} PhenomenonItemSlot;

BOOL PhenomenaTables_MapHasPhenomenon(int mapHeaderID, enum PhenomenonType type);
BOOL PhenomenaTables_RollEncounter(int mapHeaderID, enum PhenomenonType type, BOOL isFishing, BOOL isNight, int playerX, int playerZ, int baseMinLv, int baseMaxLv, u16 *outSpecies, u8 *outLevel);
u16 PhenomenaTables_RollItem(enum PhenomenonType type, int mapHeaderID);

#endif
