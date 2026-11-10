#ifndef POKEPLATINUM_POKEDEX_H
#define POKEPLATINUM_POKEDEX_H

#include "constants/species.h"

#include "heap.h"
#include "pokemon.h"
#include "savedata.h"

#include "res/pokemon/regional_pokedex_size.h"

// The save layout is vanilla's: 16 words of seen/caught/gender bits (species 1-512 by bit
// index species - 1), with Deoxys's forms in the top byte of the last caught and seen words.
// So the main bitfields hold species 1-504. Species after that keep their four bits (caught,
// seen, two genders) in the top two bits of the per-species language bytes, which only ever
// use bits 0-5 (NUM_LANGUAGES): see DexBit_Locate in pokedex.c. Existing saves keep loading unchanged.
#define DEX_SIZE_U32          16
#define DEX_MAIN_LAST_SPECIES (15 * 32 + 24) // bit index 504 is Deoxys's first form nibble
#define DEX_EXT_FIRST_BYTE    1              // recordedLanguages[0] (no species) is left alone
#define DEX_EXT_BITS_PER_BYTE 2              // bits 6 and 7
#define DEX_EXT_BITS_SHIFT    6
#define DEX_EXT_KINDS         4
#define DEX_EXT_CAPACITY      ((SPECIES_ARCEUS + 1 - DEX_EXT_FIRST_BYTE) * DEX_EXT_BITS_PER_BYTE / DEX_EXT_KINDS)
#define LANGUAGE_BITS_MASK    ((1 << NUM_LANGUAGES) - 1)

#define MAGIC_NUMBER          0xBEEFCAFE
#define NUM_EXCLUDED_NATIONAL ((int)(sizeof(sExcludedMonsNational) / sizeof(u16)))
#define NUM_EXCLUDED_LOCAL    0 //((int)(sizeof(sExcludedMonsLocal) / sizeof(u16)))
#define NATIONAL_DEX_GOAL     (NATIONAL_DEX_COUNT - NUM_EXCLUDED_NATIONAL)
#define LOCAL_DEX_GOAL        (REGIONAL_DEX_COUNT - NUM_EXCLUDED_LOCAL)

typedef struct Pokedex {
    u32 magic;
    u32 caughtPokemon[DEX_SIZE_U32];
    u32 seenPokemon[DEX_SIZE_U32];
    u32 recordedGenders[2][DEX_SIZE_U32];
    u32 spindaForm;
    u8 shellosFormsSeen;
    u8 gastrodonFormsSeen;
    u8 burmyFormsSeen;
    u8 wormadamFormsSeen;
    u8 unownFormsSeen[UNOWN_FORM_COUNT];
    // Keep the vanilla save footprint. Species added after Arceus do not persist
    // per-language flags; bits 6-7 of these bytes hold species 505+ (DexBit_Locate).
    u8 recordedLanguages[SPECIES_ARCEUS + 1];
    u8 canDetectForms;
    u8 canDetectLanguages;
    u8 pokedexObtained;
    u8 nationalDexObtained;
    u32 rotomFormsSeen;
    u8 shayminFormsSeen;
    u8 giratinaFormsSeen;
    // u8 padding[2]; // implicit padding in vanilla
} Pokedex;

int Pokedex_SaveSize(void);
Pokedex *Pokedex_New(enum HeapID heapID);
void Pokedex_Copy(const Pokedex *src, Pokedex *dest);
void Pokedex_Init(Pokedex *pokedex);
u16 Pokedex_CountCaught_National(const Pokedex *pokedex);
u16 Pokedex_CountSeen_National(const Pokedex *pokedex);
u16 Pokedex_CountSeen(const Pokedex *pokedex);
u16 Pokedex_CountCaught_Local(const Pokedex *pokedex);
u16 Pokedex_CountSeen_Local(const Pokedex *pokedex);
BOOL Pokedex_NationalDexCompleted(const Pokedex *pokedex);
BOOL Pokedex_LocalDexCompleted(const Pokedex *pokedex);
u16 Pokedex_NumCaught_National(const Pokedex *pokedex);
u16 Pokedex_NumSeen_Local(const Pokedex *pokedex);
BOOL Pokedex_HasCaughtSpecies(const Pokedex *pokedex, u16 species);
BOOL Pokedex_HasSeenSpecies(const Pokedex *pokedex, u16 species);
u32 Pokedex_GetForm_Spinda(const Pokedex *pokedex, u8 formIndex);
u32 Pokedex_DisplayedGender(const Pokedex *pokedex, u16 species, int displaySecondary);
u32 Pokedex_GetForm_Unown(const Pokedex *pokedex, int formIndex);
u32 Pokedex_NumFormsSeen_Unown(const Pokedex *pokedex);
u32 Pokedex_GetForm_Shellos(const Pokedex *pokedex, int formIndex);
u32 Pokedex_NumFormsSeen_Shellos(const Pokedex *pokedex);
u32 Pokedex_GetForm_Gastrodon(const Pokedex *pokedex, int formIndex);
u32 Pokedex_NumFormsSeen_Gastrodon(const Pokedex *pokedex);
u32 Pokedex_GetForm_Burmy(const Pokedex *pokedex, int formIndex);
u32 Pokedex_NumFormsSeen_Burmy(const Pokedex *pokedex);
u32 Pokedex_GetForm_Wormadam(const Pokedex *pokedex, int formIndex);
u32 Pokedex_NumFormsSeen_Wormadam(const Pokedex *pokedex);
u32 Pokedex_GetForm_Deoxys(const Pokedex *pokedex, int formIndex);
u32 Pokedex_NumFormsSeen_Deoxys(const Pokedex *pokedex);
void Pokedex_Encounter(Pokedex *pokedex, Pokemon *mon);
void Pokedex_Capture(Pokedex *pokedex, Pokemon *mon);
void Pokedex_ObtainNationalDex(Pokedex *pokedex);
BOOL Pokedex_IsNationalDexObtained(const Pokedex *pokedex);
BOOL Pokedex_CanDetectForms(const Pokedex *pokedex);
void Pokedex_TurnOnFormDetection(Pokedex *pokedex);
BOOL Pokedex_IsLanguageObtained(const Pokedex *pokedex, u16 species, u32 languageIndex);
void Pokedex_TurnOnLanguageDetection(Pokedex *pokedex);
BOOL Pokedex_CanDetectLanguages(const Pokedex *pokedex);
BOOL Pokedex_IsObtained(const Pokedex *pokedex);
void Pokedex_ObtainPokedex(Pokedex *pokedex);
Pokedex *SaveData_GetPokedex(SaveData *saveData);
u32 Pokedex_GetDisplayForm(const Pokedex *pokedex, int species, int formIndex);
u32 Pokedex_NumFormsSeen(const Pokedex *pokedex, int species);

#endif // POKEPLATINUM_POKEDEX_H
