#include <nitro.h>


#include "gui_createmon_utils.h"

#include "party.h"
#include "pokemon.h"
#include "savedata.h"
#include "species.h"
#include "message_util.h"

#include "charcode_convert.h"

#include <stdlib.h>


const char * GUI_CreateMon_GetSpeciesName(int speciesNo) {
    String * string = MessageUtil_SpeciesName(speciesNo, HEAP_ID_SYSTEM);
    char * nameBuf = malloc(sizeof(char) * string->size + 1);
    CharCode_ToAsciiString(string->data, nameBuf, string->size);
    nameBuf[string->size] = 0;
    String_Free(string);

    return nameBuf;
}

int GUI_CreateMon_GenPokemon(int speciesNo, int level) {
        Pokemon myPoke;

        Pokemon_InitWith(&myPoke, 
                         speciesNo, 
                         level, 
                         INIT_IVS_RANDOM, 
                         FALSE, 
                         0, 
                         OTID_NOT_SHINY, 
                         0);

        SaveData * mySaveData = SaveData_Ptr();
        Party * myParty = SaveData_GetParty(mySaveData);
        if(myParty->currentCount >= 6) {
            return FALSE;
        } else {
            Party_AddPokemon(myParty, &myPoke);
        }

        return TRUE;
        
}