#ifndef DEBUG_FIELD_H
#define DEBUG_FIELD_H
#include <nitro.h>
#include "field/field_system_decl.h"

#ifdef __cplusplus
extern "C" {
#endif

FieldSystem * DEBUG_GetFieldSystem();
void DEBUG_SetFieldSystem(FieldSystem * fieldSystem);

#ifdef __cplusplus
}
#endif

#endif
