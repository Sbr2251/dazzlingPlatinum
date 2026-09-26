#include "debug_quick_battle.h"

#include <nitro.h>
#include <string.h>

#include "config/battle_stage.h"

#if DEBUG_BATTLE_TOOLS

#include "constants/charcode.h"
#include "constants/moves.h"
#include "constants/player_avatar.h"
#include "generated/items.h"
#include "generated/moves.h"
#include "generated/species.h"

#include "field/field_system.h"

#include "bag.h"
#include "bg_window.h"
#include "encounter.h"
#include "field_battle_data_transfer.h"
#include "field_message.h"
#include "field_task.h"
#include "font.h"
#include "heap.h"
#include "map_header.h"
#include "map_object.h"
#include "message_util.h"
#include "party.h"
#include "player_avatar.h"
#include "pokemon.h"
#include "render_window.h"
#include "rtc.h"
#include "save_player.h"
#include "sound_playback.h"
#include "string_gf.h"
#include "system.h"
#include "text.h"
#include "totem_battle.h"
#include "unk_0202F180.h"
#include "unk_020528D0.h"
#include "unk_02054884.h"

#define QUICK_BATTLE_KEYS   (PAD_BUTTON_L | PAD_BUTTON_R)
#define LINE_HEIGHT         16
#define DEBUG_MON_LEVEL     50
#define DEFAULT_WILD_LEVEL  50
#define DEBUG_MON_FULL_SLOT (MAX_PARTY_SIZE - 1)
#define STRING_SIZE         64
#define PANEL_WIDTH         (27 * 8)

enum QuickBattleState {
    QUICK_BATTLE_STATE_MENU = 0,
    QUICK_BATTLE_STATE_AFTER_BATTLE,
    QUICK_BATTLE_STATE_DONE,
};

typedef struct DebugQuickBattle {
    Window window;
    enum QuickBattleState state;
    int battleResult;
    const char *status;
} DebugQuickBattle;

typedef struct BackgroundTerrainPair {
    u8 background;
    u8 terrain;
} BackgroundTerrainPair;

typedef struct MegaMon {
    u16 species;
    u16 megaStone;
    u16 moves[LEARNED_MOVES_MAX];
} MegaMon;

// Entry 0 of the cycle (not in this table) keeps the map's own background and terrain.
static const BackgroundTerrainPair sBackgroundTerrainPairs[] = {
    { BACKGROUND_PLAIN, TERRAIN_PLAIN },
    { BACKGROUND_WATER, TERRAIN_WATER },
    { BACKGROUND_CITY, TERRAIN_BUILDING },
    { BACKGROUND_FOREST, TERRAIN_GRASS },
    { BACKGROUND_MOUNTAIN, TERRAIN_MOUNTAIN },
    { BACKGROUND_SNOW, TERRAIN_SNOW },
    { BACKGROUND_INDOORS_1, TERRAIN_BUILDING },
    { BACKGROUND_INDOORS_2, TERRAIN_BUILDING },
    { BACKGROUND_INDOORS_3, TERRAIN_BUILDING },
    { BACKGROUND_CAVE_1, TERRAIN_CAVE },
    { BACKGROUND_CAVE_2, TERRAIN_CAVE },
    { BACKGROUND_CAVE_3, TERRAIN_CAVE },
    { BACKGROUND_AARON, TERRAIN_AARON },
    { BACKGROUND_BERTHA, TERRAIN_BERTHA },
    { BACKGROUND_FLINT, TERRAIN_FLINT },
    { BACKGROUND_LUCIAN, TERRAIN_LUCIAN },
    { BACKGROUND_CYNTHIA, TERRAIN_CYNTHIA },
    { BACKGROUND_DISTORTION_WORLD, TERRAIN_DISTORTION_WORLD },
    { BACKGROUND_BATTLE_TOWER, TERRAIN_BATTLE_TOWER },
    { BACKGROUND_BATTLE_FACTORY, TERRAIN_BATTLE_FACTORY },
    { BACKGROUND_BATTLE_ARCADE, TERRAIN_BATTLE_ARCADE },
    { BACKGROUND_BATTLE_CASTLE, TERRAIN_BATTLE_CASTLE },
    { BACKGROUND_BATTLE_HALL, TERRAIN_BATTLE_HALL },
    // Terrains that no background maps to on its own.
    { BACKGROUND_PLAIN, TERRAIN_SAND },
    { BACKGROUND_PLAIN, TERRAIN_PUDDLE },
    { BACKGROUND_PLAIN, TERRAIN_BRIDGE },
    { BACKGROUND_SNOW, TERRAIN_ICE },
    { BACKGROUND_FOREST, TERRAIN_GREAT_MARSH },
    { BACKGROUND_DISTORTION_WORLD, TERRAIN_GIRATINA },
    // A route battle in tall grass; last so the entries above keep their numbers
    { BACKGROUND_PLAIN, TERRAIN_GRASS },
};

#define NUM_BACKGROUND_CHOICES (NELEMS(sBackgroundTerrainPairs) + 1)

static const char *const sBackgroundNames[BACKGROUND_MAX] = {
    [BACKGROUND_PLAIN] = "Plain",
    [BACKGROUND_WATER] = "Water",
    [BACKGROUND_CITY] = "City",
    [BACKGROUND_FOREST] = "Forest",
    [BACKGROUND_MOUNTAIN] = "Mountain",
    [BACKGROUND_SNOW] = "Snow",
    [BACKGROUND_INDOORS_1] = "Indoors 1",
    [BACKGROUND_INDOORS_2] = "Indoors 2",
    [BACKGROUND_INDOORS_3] = "Indoors 3",
    [BACKGROUND_CAVE_1] = "Cave 1",
    [BACKGROUND_CAVE_2] = "Cave 2",
    [BACKGROUND_CAVE_3] = "Cave 3",
    [BACKGROUND_AARON] = "Aaron",
    [BACKGROUND_BERTHA] = "Bertha",
    [BACKGROUND_FLINT] = "Flint",
    [BACKGROUND_LUCIAN] = "Lucian",
    [BACKGROUND_CYNTHIA] = "Cynthia",
    [BACKGROUND_DISTORTION_WORLD] = "Distortion",
    [BACKGROUND_BATTLE_TOWER] = "Tower",
    [BACKGROUND_BATTLE_FACTORY] = "Factory",
    [BACKGROUND_BATTLE_ARCADE] = "Arcade",
    [BACKGROUND_BATTLE_CASTLE] = "Castle",
    [BACKGROUND_BATTLE_HALL] = "Hall",
};

static const char *const sTerrainNames[TERRAIN_MAX] = {
    [TERRAIN_PLAIN] = "Plain",
    [TERRAIN_SAND] = "Sand",
    [TERRAIN_GRASS] = "Grass",
    [TERRAIN_PUDDLE] = "Puddle",
    [TERRAIN_MOUNTAIN] = "Mountain",
    [TERRAIN_CAVE] = "Cave",
    [TERRAIN_SNOW] = "Snow",
    [TERRAIN_WATER] = "Water",
    [TERRAIN_ICE] = "Ice",
    [TERRAIN_BUILDING] = "Building",
    [TERRAIN_GREAT_MARSH] = "Marsh",
    [TERRAIN_BRIDGE] = "Bridge",
    [TERRAIN_AARON] = "Aaron",
    [TERRAIN_BERTHA] = "Bertha",
    [TERRAIN_FLINT] = "Flint",
    [TERRAIN_LUCIAN] = "Lucian",
    [TERRAIN_CYNTHIA] = "Cynthia",
    [TERRAIN_DISTORTION_WORLD] = "Distortion",
    [TERRAIN_BATTLE_TOWER] = "Tower",
    [TERRAIN_BATTLE_FACTORY] = "Factory",
    [TERRAIN_BATTLE_ARCADE] = "Arcade",
    [TERRAIN_BATTLE_CASTLE] = "Castle",
    [TERRAIN_BATTLE_HALL] = "Hall",
    [TERRAIN_GIRATINA] = "Giratina",
};

static const MegaMon sMegaMons[] = {
    { SPECIES_GARCHOMP, ITEM_GARCHOMPITE, { MOVE_EARTHQUAKE, MOVE_DRAGON_CLAW, MOVE_STONE_EDGE, MOVE_SWORDS_DANCE } },
    { SPECIES_ALAKAZAM, ITEM_ALAKAZITE, { MOVE_PSYCHIC, MOVE_SHADOW_BALL, MOVE_FOCUS_BLAST, MOVE_CALM_MIND } },
    { SPECIES_EMPOLEON, ITEM_EMPOLEONITE, { MOVE_SURF, MOVE_ICE_BEAM, MOVE_FLASH_CANNON, MOVE_GRASS_KNOT } },
    { SPECIES_GARDEVOIR, ITEM_GARDEVOIRITE, { MOVE_PSYCHIC, MOVE_THUNDERBOLT, MOVE_SHADOW_BALL, MOVE_CALM_MIND } },
    { SPECIES_GENGAR, ITEM_GENGARITE, { MOVE_SHADOW_BALL, MOVE_SLUDGE_BOMB, MOVE_FOCUS_BLAST, MOVE_THUNDERBOLT } },
    { SPECIES_GYARADOS, ITEM_GYARADOSITE, { MOVE_WATERFALL, MOVE_EARTHQUAKE, MOVE_ICE_FANG, MOVE_DRAGON_DANCE } },
    { SPECIES_INFERNAPE, ITEM_INFERNAPITE, { MOVE_FLARE_BLITZ, MOVE_CLOSE_COMBAT, MOVE_MACH_PUNCH, MOVE_U_TURN } },
    { SPECIES_LUCARIO, ITEM_LUCARIONITE, { MOVE_AURA_SPHERE, MOVE_FLASH_CANNON, MOVE_DARK_PULSE, MOVE_EXTREME_SPEED } },
    { SPECIES_SCIZOR, ITEM_SCIZORITE, { MOVE_BULLET_PUNCH, MOVE_X_SCISSOR, MOVE_U_TURN, MOVE_SWORDS_DANCE } },
    { SPECIES_STARAPTOR, ITEM_STARAPTITE, { MOVE_BRAVE_BIRD, MOVE_CLOSE_COMBAT, MOVE_U_TURN, MOVE_QUICK_ATTACK } },
    { SPECIES_TORTERRA, ITEM_TORTERRITE, { MOVE_WOOD_HAMMER, MOVE_EARTHQUAKE, MOVE_STONE_EDGE, MOVE_CRUNCH } },
};

static const u16 sOpponentSpecies[] = {
    SPECIES_BIDOOF,
    SPECIES_STARLY,
    SPECIES_SHINX,
    SPECIES_BUDEW,
    SPECIES_GEODUDE,
    SPECIES_ZUBAT,
    SPECIES_MACHOP,
    SPECIES_MAGIKARP,
    SPECIES_ALAKAZAM,
    SPECIES_EMPOLEON,
    SPECIES_GARCHOMP,
    SPECIES_GARDEVOIR,
    SPECIES_GENGAR,
    SPECIES_GYARADOS,
    SPECIES_INFERNAPE,
    SPECIES_LUCARIO,
    SPECIES_SCIZOR,
    SPECIES_STARAPTOR,
    SPECIES_TORTERRA,
};

// Entry 0 (not in this table) keeps the clock's time of day. The others force one, which picks
// the backdrop palette of the outdoor backgrounds and the arena's lighting.
static const struct {
    u8 timeOfDay;
    const char *name;
} sTimeOfDayChoices[] = {
    { TIMEOFDAY_DAY, "Day" },
    { TIMEOFDAY_TWILIGHT, "Twilight" },
    { TIMEOFDAY_NIGHT, "Night" },
};

#define NUM_TIME_OF_DAY_CHOICES (NELEMS(sTimeOfDayChoices) + 1)

// Kept in main so the selection survives the overlay reloads around each battle.
static u8 sBackgroundChoice = 0;
static u8 sTimeOfDayChoice = 0;
static u8 sOpponentChoice = 0;
static u8 sTotemChoice = TOTEM_ENCOUNTER_HITMONLEE;

static charcode_t AsciiToCharCode(char c)
{
    if (c >= '0' && c <= '9') {
        return CHAR_0 + (c - '0');
    }

    if (c >= 'A' && c <= 'Z') {
        return CHAR_A + (c - 'A');
    }

    if (c >= 'a' && c <= 'z') {
        return CHAR_a + (c - 'a');
    }

    switch (c) {
    case '/':
        return CHAR_SLASH;
    case ':':
        return CHAR_COLON;
    case '+':
        return CHAR_PLUS;
    case '-':
        return CHAR_MINUS;
    case '.':
        return CHAR_PERIOD;
    case '(':
        return CHAR_PAREN_OPEN;
    case ')':
        return CHAR_PAREN_CLOSE;
    default:
        return CHAR_SPACE;
    }
}

static void String_AppendAscii(String *dst, const char *src)
{
    while (*src != '\0') {
        String_AppendChar(dst, AsciiToCharCode(*src));
        src++;
    }
}

static void String_AppendNumber(String *dst, int num, u32 digits, enum PaddingMode paddingMode)
{
    String *tmp = String_Init(8, HEAP_ID_FIELD3);

    String_FormatInt(tmp, num, digits, paddingMode, CHARSET_MODE_EN);
    String_Concat(dst, tmp);
    String_Free(tmp);
}

static void String_AppendSpeciesName(String *dst, u16 species)
{
    String *name = MessageUtil_SpeciesName(species, HEAP_ID_FIELD3);

    String_Concat(dst, name);
    String_Free(name);
}

static u8 GetOpponentLevel(Party *party)
{
    int count = Party_GetCurrentCount(party);

    for (int i = 0; i < count; i++) {
        Pokemon *mon = Party_GetPokemonBySlotIndex(party, i);

        if (Pokemon_CanBattle(mon)) {
            return Pokemon_GetValue(mon, MON_DATA_LEVEL, NULL);
        }
    }

    return DEFAULT_WILD_LEVEL;
}

static const MegaMon *FindMegaMon(u16 species)
{
    for (int i = 0; i < NELEMS(sMegaMons); i++) {
        if (sMegaMons[i].species == species) {
            return &sMegaMons[i];
        }
    }

    return NULL;
}

static void DrawPanel(FieldSystem *fieldSystem, DebugQuickBattle *quickBattle)
{
    String *line = String_Init(STRING_SIZE, HEAP_ID_FIELD3);
    enum BattleBackground background;
    enum BattleTerrain terrain;

    Window_FillTilemap(&quickBattle->window, 15);

    String_AppendNumber(line, sBackgroundChoice, 2, PADDING_MODE_ZEROES);
    String_AppendAscii(line, "/");
    String_AppendNumber(line, NUM_BACKGROUND_CHOICES - 1, 2, PADDING_MODE_ZEROES);
    String_AppendAscii(line, " ");

    if (sBackgroundChoice == 0) {
        background = MapHeader_GetBattleBG(fieldSystem->location->mapId);
        String_AppendAscii(line, "Map: ");
        String_AppendAscii(line, background < BACKGROUND_MAX ? sBackgroundNames[background] : "?");
    } else {
        background = sBackgroundTerrainPairs[sBackgroundChoice - 1].background;
        terrain = sBackgroundTerrainPairs[sBackgroundChoice - 1].terrain;
        String_AppendAscii(line, sBackgroundNames[background]);
        String_AppendAscii(line, " + ");
        String_AppendAscii(line, sTerrainNames[terrain]);
    }

    Text_AddPrinterWithParams(&quickBattle->window, FONT_MESSAGE, line, 0, 0, TEXT_SPEED_INSTANT, NULL);
    String_Clear(line);

    // Time of day, right-aligned on the first line.
    String_AppendAscii(line, sTimeOfDayChoice == 0 ? "Clock" : sTimeOfDayChoices[sTimeOfDayChoice - 1].name);
    Text_AddPrinterWithParams(&quickBattle->window, FONT_MESSAGE, line, PANEL_WIDTH - Font_CalcStringWidth(FONT_MESSAGE, line, 0), 0, TEXT_SPEED_INSTANT, NULL);
    String_Clear(line);

    if (quickBattle->status != NULL) {
        String_AppendAscii(line, quickBattle->status);
    } else {
        String_AppendSpeciesName(line, sOpponentSpecies[sOpponentChoice]);
        String_AppendAscii(line, " Lv");
        String_AppendNumber(line, GetOpponentLevel(SaveData_GetParty(fieldSystem->saveData)), 3, PADDING_MODE_NONE);
        String_AppendAscii(line, "  X: ");
        String_AppendSpeciesName(line, TotemBattle_GetEncounterConfig(sTotemChoice)->party[0].species);
    }

    Text_AddPrinterWithParams(&quickBattle->window, FONT_MESSAGE, line, 0, LINE_HEIGHT, TEXT_SPEED_INSTANT, NULL);
    String_Free(line);
}

static void ClosePanel(FieldSystem *fieldSystem, DebugQuickBattle *quickBattle)
{
    Window_EraseMessageBox(&quickBattle->window, FALSE);
    Window_Remove(&quickBattle->window);
}

// Gives the selected opponent species if it can Mega Evolve, otherwise Garchomp.
static const char *GiveMegaMon(FieldSystem *fieldSystem)
{
    SaveData *saveData = fieldSystem->saveData;
    Party *party = SaveData_GetParty(saveData);
    Bag *bag = SaveData_GetBag(saveData);
    const MegaMon *megaMon = FindMegaMon(sOpponentSpecies[sOpponentChoice]);
    u32 heldItem;

    if (megaMon == NULL) {
        megaMon = &sMegaMons[0];
    }

    if (Bag_GetItemQuantity(bag, ITEM_KEY_STONE, HEAP_ID_FIELD3) == 0) {
        Bag_TryAddItem(bag, ITEM_KEY_STONE, 1, HEAP_ID_FIELD3);
    }

    Pokemon *mon = Pokemon_New(HEAP_ID_FIELD3);

    Pokemon_Init(mon);
    Pokemon_InitWith(mon, megaMon->species, DEBUG_MON_LEVEL, INIT_IVS_RANDOM, FALSE, 0, OTID_NOT_SET, 0);
    Pokemon_SetCatchData(mon, SaveData_GetTrainerInfo(saveData), ITEM_POKE_BALL, MapHeader_GetMapLabelTextID(fieldSystem->location->mapId), TERRAIN_MAX, HEAP_ID_FIELD3);

    heldItem = megaMon->megaStone;
    Pokemon_SetValue(mon, MON_DATA_HELD_ITEM, &heldItem);

    for (int i = 0; i < LEARNED_MOVES_MAX; i++) {
        Pokemon_ResetMoveSlot(mon, megaMon->moves[i], i);
    }

    const char *status = "Got Mega mon + Key Stone";

    if (Party_GetCurrentCount(party) < MAX_PARTY_SIZE) {
        Party_AddPokemon(party, mon);
    } else {
        Party_AddPokemonBySlotIndex(party, DEBUG_MON_FULL_SLOT, mon);
        status = "Party full: slot 6 replaced";
    }

    SaveData_UpdateCatchRecords(saveData, mon);
    Heap_Free(mon);

    return status;
}

static void StartBattle(FieldTask *task, FieldSystem *fieldSystem, DebugQuickBattle *quickBattle, BOOL totem)
{
    ClosePanel(fieldSystem, quickBattle);

    if (sBackgroundChoice != 0) {
        const BackgroundTerrainPair *pair = &sBackgroundTerrainPairs[sBackgroundChoice - 1];
        FieldBattleDTO_SetDebugBackgroundOverride(pair->background, pair->terrain);
    }

    if (sTimeOfDayChoice != 0) {
        FieldBattleDTO_SetDebugTimeOfDayOverride(sTimeOfDayChoices[sTimeOfDayChoice - 1].timeOfDay);
    }

    if (totem) {
        Encounter_NewTotemBattle(task, sTotemChoice, &quickBattle->battleResult);
    } else {
        u8 level = GetOpponentLevel(SaveData_GetParty(fieldSystem->saveData));
        Encounter_NewVsSpeciesAtLevel(task, sOpponentSpecies[sOpponentChoice], level, &quickBattle->battleResult, FALSE);
    }

    quickBattle->state = QUICK_BATTLE_STATE_AFTER_BATTLE;
}

static BOOL FieldTask_DebugQuickBattle(FieldTask *task)
{
    FieldSystem *fieldSystem = FieldTask_GetFieldSystem(task);
    DebugQuickBattle *quickBattle = FieldTask_GetEnv(task);
    u32 pressed = gSystem.pressedKeys;
    BOOL redraw = FALSE;

    switch (quickBattle->state) {
    case QUICK_BATTLE_STATE_MENU:
        if ((gSystem.heldKeys & QUICK_BATTLE_KEYS) != QUICK_BATTLE_KEYS) {
            ClosePanel(fieldSystem, quickBattle);
            quickBattle->state = QUICK_BATTLE_STATE_DONE;
            break;
        }

        if (pressed & PAD_BUTTON_A) {
            Sound_PlayEffect(SEQ_SE_CONFIRM);
            StartBattle(task, fieldSystem, quickBattle, FALSE);
            return FALSE;
        }

        if (pressed & PAD_BUTTON_X) {
            Sound_PlayEffect(SEQ_SE_CONFIRM);
            StartBattle(task, fieldSystem, quickBattle, TRUE);
            return FALSE;
        }

        if (pressed & (PAD_KEY | PAD_BUTTON_B | PAD_BUTTON_START | PAD_BUTTON_SELECT)) {
            quickBattle->status = NULL;
            redraw = TRUE;
        }

        if (pressed & PAD_KEY_UP) {
            sBackgroundChoice = (sBackgroundChoice + NUM_BACKGROUND_CHOICES - 1) % NUM_BACKGROUND_CHOICES;
        } else if (pressed & PAD_KEY_DOWN) {
            sBackgroundChoice = (sBackgroundChoice + 1) % NUM_BACKGROUND_CHOICES;
        } else if (pressed & PAD_KEY_LEFT) {
            sOpponentChoice = (sOpponentChoice + NELEMS(sOpponentSpecies) - 1) % NELEMS(sOpponentSpecies);
        } else if (pressed & PAD_KEY_RIGHT) {
            sOpponentChoice = (sOpponentChoice + 1) % NELEMS(sOpponentSpecies);
        } else if (pressed & PAD_BUTTON_B) {
            sTotemChoice = (sTotemChoice + 1) % TOTEM_ENCOUNTER_COUNT;
        } else if (pressed & PAD_BUTTON_START) {
            quickBattle->status = GiveMegaMon(fieldSystem);
            Sound_PlayEffect(SEQ_SE_CONFIRM);
        } else if (pressed & PAD_BUTTON_SELECT) {
            sTimeOfDayChoice = (sTimeOfDayChoice + 1) % NUM_TIME_OF_DAY_CHOICES;
        }

        if (redraw) {
            DrawPanel(fieldSystem, quickBattle);
        }
        break;
    case QUICK_BATTLE_STATE_AFTER_BATTLE:
        quickBattle->state = QUICK_BATTLE_STATE_DONE;

        if (CheckPlayerWonBattle(quickBattle->battleResult) == FALSE) {
            FieldTask_StartBlackOutFromBattle(task);
            return FALSE;
        }
        break;
    case QUICK_BATTLE_STATE_DONE:
        break;
    }

    if (quickBattle->state == QUICK_BATTLE_STATE_DONE) {
        MapObjectMan_UnpauseAllMovement(fieldSystem->mapObjMan);
        Heap_Free(quickBattle);
        return TRUE;
    }

    return FALSE;
}

BOOL DebugQuickBattle_TryStart(FieldSystem *fieldSystem, u32 heldKeys)
{
    if ((heldKeys & QUICK_BATTLE_KEYS) != QUICK_BATTLE_KEYS) {
        return FALSE;
    }

    int moveState = Player_MoveState(fieldSystem->playerAvatar);

    if (moveState != PLAYER_MOVE_STATE_END && moveState != PLAYER_MOVE_STATE_NONE) {
        return FALSE;
    }

    DebugQuickBattle *quickBattle = Heap_AllocAtEnd(HEAP_ID_FIELD3, sizeof(DebugQuickBattle));

    memset(quickBattle, 0, sizeof(DebugQuickBattle));
    quickBattle->state = QUICK_BATTLE_STATE_MENU;

    MapObjectMan_PauseAllMovement(fieldSystem->mapObjMan);
    FieldMessage_AddWindow(fieldSystem->bgConfig, &quickBattle->window, BG_LAYER_MAIN_3);
    FieldMessage_DrawWindow(&quickBattle->window, SaveData_GetOptions(fieldSystem->saveData));
    DrawPanel(fieldSystem, quickBattle);

    FieldSystem_CreateTask(fieldSystem, FieldTask_DebugQuickBattle, quickBattle);
    return TRUE;
}

#endif // DEBUG_BATTLE_TOOLS
