#ifndef POKEPLATINUM_CONSTANTS_TOTEM_BATTLE_H
#define POKEPLATINUM_CONSTANTS_TOTEM_BATTLE_H

#define TOTEM_ENCOUNTER_HITMONLEE   0
#define TOTEM_ENCOUNTER_VESPIQUEN   1
#define TOTEM_ENCOUNTER_SPIRITOMB   2
#define TOTEM_ENCOUNTER_SKARMORY    3
#define TOTEM_ENCOUNTER_LAPRAS      4
#define TOTEM_ENCOUNTER_AGGRON      5
#define TOTEM_ENCOUNTER_MAMOSWINE   6
#define TOTEM_ENCOUNTER_KINGDRA     7
// Arc 2 2.18: the Skarmory totem with the grunts' boost shard left in its frame (config .boosted: +1 Atk, +1 Def
// on top of the aura). DW Route 214 picks this one unless Cyrus pulled the shard (VAR_ARC2_CHOICES bit 2).
#define TOTEM_ENCOUNTER_SKARMORY_BOOSTED 8
#define TOTEM_ENCOUNTER_COUNT       9

#define TOTEM_PARTY_SIZE       3
#define TOTEM_MAX_ALLY_SUMMONS 2

#endif // POKEPLATINUM_CONSTANTS_TOTEM_BATTLE_H
