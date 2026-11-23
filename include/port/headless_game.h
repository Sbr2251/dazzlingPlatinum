#ifndef PORT_HEADLESS_GAME_H
#define PORT_HEADLESS_GAME_H

#include <stddef.h>

// Registry hooks for the headless protocol (src/port/headless_game.c).
// Called from battle_main.c / main.c under SDK_PORT so `state` can report
// the current battle and application. See docs/headless_protocol.md.

#ifdef __cplusplus
extern "C" {
#endif

struct BattleSystem;
void Headless_SetBattleSystem(struct BattleSystem *battleSys);
struct BattleSystem *Headless_GetBattleSystem(void);
void Headless_SetOverlay(int overlayId);
int Headless_GetOverlay(void);

// dbg-inspect hook: rich, read-only game-side diagnostics.
int HeadlessInspect_Handle(const char *line, char *reply, size_t cap);

#ifdef __cplusplus
}
#endif

#endif
