#ifndef PORT_HEADLESS_GAME_H
#define PORT_HEADLESS_GAME_H

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

#ifdef __cplusplus
}
#endif

#endif
