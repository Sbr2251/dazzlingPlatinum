#ifndef PORT_HEADLESS_BATTLE_H
#define PORT_HEADLESS_BATTLE_H
#include <stddef.h>
// Start a battle from a JSON battle spec (docs/battle_engine.md).
// `line` is the full start_battle command line; it may carry "spec_path"
// (absolute path to a spec JSON file) or an inline "spec"/party fields.
// Writes a JSON reply ({"ok":true} or {"ok":false,"error":...}) into reply.
// Returns 1 if the command was handled.
int HeadlessBattle_Start(const char *line, char *reply, size_t cap);
#endif
