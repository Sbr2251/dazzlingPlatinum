// start_battle for the headless protocol: builds a battle directly from a
// JSON battle spec (docs/battle_engine.md), from any field state.
// The player's save party/bag are set from the spec (this is a test tool:
// use a throwaway save via SIM_SAVE_PATH), then a custom FieldBattleDTO is
// handed to Encounter_NewHeadlessBattle, i.e. the normal encounter/battle
// code path used by wild/trainer battles.
#include <nitro.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "generated/pokemon_data_params.h"
#include "headless_names.h"

#include "port/debug_field.h"
#include "port/headless_battle.h"

#include "config/battle_stage.h"
#include "constants/battle.h"
#include "constants/heap.h"
#include "generated/items.h"

#include "field/field_system.h"

#include "bag.h"
#include "encounter.h"
#include "field_battle_data_transfer.h"
#include "heap.h"
#include "party.h"
#include "pokemon.h"
#include "savedata.h"
#include "trainer_data.h"
#include "trainer_info.h"
#include "save_player.h"
#include "unk_020528D0.h"

// ------------------------------------------------------------ tiny JSON
static const char *FindKey(const char *s, const char *e, const char *key) {
    char pat[64]; snprintf(pat, sizeof(pat), "\"%s\"", key);
    size_t kl = strlen(pat);
    for (const char *p = s; p + kl <= e; p++) {
        if (strncmp(p, pat, kl) == 0) {
            const char *c = strchr(p + kl, ':');
            if (c && c < e) return c + 1;
        }
    }
    return NULL;
}
static int JsonStr(const char *s, const char *e, const char *key, char *out, size_t cap) {
    const char *p = FindKey(s, e, key); if (!p) return 0;
    while (p < e && (*p == ' ' || *p == '\t')) p++;
    if (p >= e || *p != '"') return 0;
    const char *q = p + 1; while (q < e && *q != '"') q++;
    size_t n = (size_t)(q - (p + 1)); if (n >= cap) n = cap - 1;
    memcpy(out, p + 1, n); out[n] = 0; return 1;
}
static int JsonLong(const char *s, const char *e, const char *key, long *out) {
    const char *p = FindKey(s, e, key); if (!p) return 0;
    *out = strtol(p, NULL, 10); return 1;
}
static int JsonBool(const char *s, const char *e, const char *key, int *out) {
    const char *p = FindKey(s, e, key); if (!p) return 0;
    while (p < e && (*p == ' ')) p++;
    *out = (p + 4 <= e && strncmp(p, "true", 4) == 0); return 1;
}
// nth string in the array at key; returns 1 if present.
static int JsonArrStr(const char *s, const char *e, const char *key, int idx, char *out, size_t cap) {
    const char *p = FindKey(s, e, key); if (!p) return 0;
    p = strchr(p, '['); if (!p || p >= e) return 0;
    for (int i = 0;; i++) {
        const char *q = p; while (q < e && *q != '"' && *q != ']') q++;
        if (q >= e || *q == ']') return 0;
        const char *r = q + 1; while (r < e && *r != '"') r++;
        if (i == idx) { size_t n = (size_t)(r - (q + 1)); if (n >= cap) n = cap - 1; memcpy(out, q + 1, n); out[n] = 0; return 1; }
        p = r + 1;
    }
}
static int JsonArrLong(const char *s, const char *e, const char *key, int idx, long *out) {
    const char *p = FindKey(s, e, key); if (!p) return 0;
    p = strchr(p, '['); if (!p || p >= e) return 0;
    for (int i = 0; i <= idx; i++) {
        while (p < e && (*p == ' ' || *p == ',' || *p == '[')) p++;
        if (p >= e || *p == ']') return 0;
        char *end = NULL; long v = strtol(p, &end, 10); if (end == p) return 0;
        if (i == idx) { *out = v; return 1; }
        p = end;
    }
    return 0;
}
static const HeadlessName *Lookup(const HeadlessName *t, int c, const char *name, const char *prefix) {
    const HeadlessName *r = Headless_Lookup(t, c, name);
    if (r) return r;
    if (strncmp(name, prefix, strlen(prefix)) != 0) {
        char buf[160]; snprintf(buf, sizeof(buf), "%s%s", prefix, name);
        return Headless_Lookup(t, c, buf);
    }
    return NULL;
}

// ------------------------------------------------------------ mon build
typedef struct { char text[65536]; } SpecBuf;

static Pokemon *BuildMon(const char *s, const char *e, FieldSystem *fsys) {
    char name[96];
    if (!JsonStr(s, e, "species", name, sizeof(name))) return NULL;
    const HeadlessName *sp = Lookup(kHeadlessSpecies, kHeadlessSpeciesCount, name, "SPECIES_");
    if (!sp) { fprintf(stderr, "start_battle: unknown species %s\n", name); return NULL; }
    long level = 50; JsonLong(s, e, "level", &level);
    Pokemon *mon = Pokemon_New(HEAP_ID_FIELD3);
    Pokemon_Init(mon);
    Pokemon_InitWith(mon, sp->id, (int)level, INIT_IVS_RANDOM, FALSE, 0, OTID_NOT_SET, 0);
    Pokemon_SetCatchData(mon, SaveData_GetTrainerInfo(fsys->saveData), ITEM_POKE_BALL, 0, TERRAIN_MAX, HEAP_ID_FIELD3);
    long v;
    // IVs / EVs as [hp,atk,def,speed,spatk,spdef]
    static const int ivIds[6] = { MON_DATA_HP_IV, MON_DATA_ATK_IV, MON_DATA_DEF_IV, MON_DATA_SPEED_IV, MON_DATA_SPATK_IV, MON_DATA_SPDEF_IV };
    static const int evIds[6] = { MON_DATA_HP_EV, MON_DATA_ATK_EV, MON_DATA_DEF_EV, MON_DATA_SPEED_EV, MON_DATA_SPATK_EV, MON_DATA_SPDEF_EV };
    for (int i = 0; i < 6; i++) {
        if (JsonArrLong(s, e, "ivs", i, &v)) { u32 x = (u32)v; Pokemon_SetValue(mon, ivIds[i], &x); }
        if (JsonArrLong(s, e, "evs", i, &v)) { u32 x = (u32)v; Pokemon_SetValue(mon, evIds[i], &x); }
    }
    if (JsonStr(s, e, "nature", name, sizeof(name))) {
        const HeadlessName *nat = Lookup(kHeadlessNatures, kHeadlessNaturesCount, name, "NATURE_");
        if (nat) { u32 pers = Pokemon_GetValue(mon, MON_DATA_PERSONALITY, NULL); pers = pers - (pers % 25) + (u32)nat->id; Pokemon_SetValue(mon, MON_DATA_PERSONALITY, &pers); }
    }
    if (JsonStr(s, e, "ability", name, sizeof(name))) {
        const HeadlessName *ab = Lookup(kHeadlessAbilities, kHeadlessAbilitiesCount, name, "ABILITY_");
        if (ab) { u32 x = (u32)ab->id; Pokemon_SetValue(mon, MON_DATA_ABILITY, &x); }
    }
    if (JsonStr(s, e, "held_item", name, sizeof(name))) {
        const HeadlessName *it = Lookup(kHeadlessItems, kHeadlessItemsCount, name, "ITEM_");
        if (it) { u32 x = (u32)it->id; Pokemon_SetValue(mon, MON_DATA_HELD_ITEM, &x); }
    }
    if (JsonLong(s, e, "form", &v)) { u32 x = (u32)v; Pokemon_SetValue(mon, MON_DATA_FORM, &x); }
    for (int i = 0; i < 4; i++) {
        if (JsonArrStr(s, e, "moves", i, name, sizeof(name))) {
            const HeadlessName *mv = Lookup(kHeadlessMoves, kHeadlessMovesCount, name, "MOVE_");
            if (mv) Pokemon_ResetMoveSlot(mon, (u16)mv->id, (u8)i);
        }
    }
    Pokemon_CalcLevelAndStats(mon);
    { u32 hp = Pokemon_GetValue(mon, MON_DATA_MAX_HP, NULL); Pokemon_SetValue(mon, MON_DATA_HP, &hp); }
    return mon;
}

// Iterate objects in the array at key, calling fn for each object slice.
static int ForEachMon(const char *s, const char *e, const char *key, FieldSystem *fsys, Party *party) {
    const char *p = FindKey(s, e, key); if (!p) return 0;
    p = strchr(p, '['); if (!p) return 0;
    int count = 0;
    while (p < e) {
        while (p < e && *p != '{' && *p != ']') p++;
        if (p >= e || *p == ']') break;
        const char *q = p; int depth = 0;
        do { if (*q == '{') depth++; else if (*q == '}') depth--; q++; } while (q < e && depth > 0);
        Pokemon *mon = BuildMon(p, q, fsys);
        if (mon) { Party_AddPokemon(party, mon); Heap_Free(mon); count++; }
        p = q;
    }
    return count;
}

// ------------------------------------------------------------ task
typedef struct {
    int state;
    int result;
    FieldBattleDTO *dto;
    char *spec;
} HeadlessBattleTask;

static BOOL FieldTask_HeadlessBattle(FieldTask *task) {
    FieldSystem *fsys = FieldTask_GetFieldSystem(task);
    HeadlessBattleTask *env = FieldTask_GetEnv(task);
    switch (env->state) {
    case 0: {
        const char *s = env->spec; const char *e = s + strlen(s);
        char typeStr[32] = "wild"; JsonStr(s, e, "battle_type", typeStr, sizeof(typeStr));
        int isTrainer = strcmp(typeStr, "trainer") == 0;
        int isTotem = strcmp(typeStr, "totem") == 0; int b = 0;
        if (JsonBool(s, e, "totem", &b) && b) isTotem = 1;
        int isDouble = (strcmp(typeStr, "double") == 0) || isTotem;
        if (JsonBool(s, e, "double", &b) && b) isDouble = 1;
        // Player party + bag from spec.
        Party *party = SaveData_GetParty(fsys->saveData);
        Party_Init(party);
        if (ForEachMon(s, e, "player", fsys, party) == 0) ForEachMon(s, e, "player_party", fsys, party);
        Bag *bag = SaveData_GetBag(fsys->saveData);
        char itemName[96];
        // bag: [{"item":"ITEM_X","qty":N}, ...]
        {
            const char *p = FindKey(s, e, "bag");
            if (p) { const char *arr = strchr(p, '['); if (arr && arr < e) {
                const char *q = arr;
                while (q < e) { while (q < e && *q != '{' && *q != ']') q++; if (q >= e || *q == ']') break;
                    const char *r = q; int d = 0; do { if (*r == '{') d++; else if (*r == '}') d--; r++; } while (r < e && d > 0);
                    if (JsonStr(q, r, "item", itemName, sizeof(itemName))) {
                        const HeadlessName *it = Lookup(kHeadlessItems, kHeadlessItemsCount, itemName, "ITEM_");
                        long qty = 1; JsonLong(q, r, "qty", &qty);
                        if (it) Bag_TryAddItem(bag, (u16)it->id, (u16)qty, HEAP_ID_FIELD3);
                    }
                    q = r; }
            } }
        }
        if (JsonBool(s, e, "key_stone", &b) && b) Bag_TryAddItem(bag, ITEM_KEY_STONE, 1, HEAP_ID_FIELD3);
        // DTO
        u32 battleType = isTrainer ? BATTLE_TYPE_TRAINER : BATTLE_TYPE_WILD_MON;
        if (isDouble) battleType |= BATTLE_TYPE_DOUBLES;
        FieldBattleDTO *dto = FieldBattleDTO_New(HEAP_ID_FIELD2, battleType);
        FieldBattleDTO_Init(dto, fsys);
        long trainerId = 0; JsonLong(s, e, "trainer_id", &trainerId);
        if (isTrainer) {
            dto->trainerIDs[BATTLER_ENEMY_1] = (int)(trainerId ? trainerId : 1);
            Trainer_Encounter(dto, fsys->saveData, HEAP_ID_FIELD2);
        }
        Party_Init(dto->parties[BATTLER_ENEMY_1]);
        int opp = ForEachMon(s, e, "opponent", fsys, dto->parties[BATTLER_ENEMY_1]);
        if (opp == 0) opp = ForEachMon(s, e, "opponent_party", fsys, dto->parties[BATTLER_ENEMY_1]);
        if (opp == 0) { fprintf(stderr, "start_battle: no opponent mons\n"); FieldBattleDTO_Free(dto); free(env->spec); Heap_Free(env); return TRUE; }
        if (isTotem) {
            dto->battleStatusMask |= BATTLE_STATUS_LEGENDARY | BATTLE_STATUS_TOTEM | BATTLE_STATUS_NO_RUNNING;
            if (JsonBool(s, e, "totem_boosted", &b) && b) dto->battleStatusMask |= BATTLE_STATUS_TOTEM_BOOSTED;
        }
        env->dto = dto;
        Encounter_NewHeadlessBattle(task, dto, &env->result);
        env->state = 1;
        return FALSE;
    }
    case 1:
        env->state = 2;
        if (CheckPlayerWonBattle((u32)env->result) == FALSE) FieldTask_StartBlackOutFromBattle(task);
        return FALSE;
    default:
        free(env->spec); Heap_Free(env); return TRUE;
    }
}

int HeadlessBattle_Start(const char *line, char *reply, size_t cap) {
    FieldSystem *fsys = DEBUG_GetFieldSystem();
    if (!fsys) { snprintf(reply, cap, "{\"ok\":false,\"error\":\"not in the field\"}"); return 1; }
    char path[512];
    char *spec = NULL;
    const char *lend = line + strlen(line);
    if (JsonStr(line, lend, "spec_path", path, sizeof(path))) {
        FILE *f = fopen(path, "rb");
        if (!f) { snprintf(reply, cap, "{\"ok\":false,\"error\":\"cannot open spec_path\"}"); return 1; }
        fseek(f, 0, SEEK_END); long n = ftell(f); fseek(f, 0, SEEK_SET);
        if (n <= 0 || n > 60000) { fclose(f); snprintf(reply, cap, "{\"ok\":false,\"error\":\"bad spec size\"}"); return 1; }
        spec = malloc((size_t)n + 1);
        if (fread(spec, 1, (size_t)n, f) != (size_t)n) { /* best effort */ }
        spec[n] = 0; fclose(f);
    } else {
        // Inline: the whole command line carries the spec fields.
        spec = malloc(strlen(line) + 1); strcpy(spec, line);
    }
    HeadlessBattleTask *env = Heap_AllocAtEnd(HEAP_ID_FIELD3, sizeof(HeadlessBattleTask));
    memset(env, 0, sizeof(*env)); env->spec = spec; env->result = 0;
    FieldSystem_CreateTask(fsys, FieldTask_HeadlessBattle, env);
    snprintf(reply, cap, "{\"ok\":true}");
    return 1;
}
