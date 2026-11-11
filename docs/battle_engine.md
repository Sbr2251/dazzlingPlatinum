# Battle engine: rules/presentation boundary, event stream, fast mode, replay

Status: engine-core foundation (branch `engine/core`). This is the contract
engine-sim builds against. Keep it current in the same commits as the code.

## 1. The boundary that already exists

Gen 4 battle code is already split server/client; this work makes it explicit:

- **Server (rules)** - `src/battle/battle_controller.c` (turn machine),
  `battle_lib.c` (damage/effectiveness/ability/item triggers),
  `battle_script.c` (interprets `res/battle/scripts` bytecode),
  `src/battle/trainer_ai/`. Owns `BattleContext` (`include/battle/battle_context.h`):
  battlers, HP, status, stat stages, field/side conditions, move selection,
  RNG-driven outcomes. Must never wait on presentation timing for RNG.
- **Boundary** - `BattleController_Emit*()` in `battle_controller.c` builds a
  typed message (`include/constants/battle/battle_controller.h`:
  `BATTLE_COMMAND_*`, structs in `struct_defs/battler_data.h`) and calls
  `SendMessage(..., COMM_RECIPIENT_CLIENT, ...)`. Locally that is
  `BattleController_SendLocalMessage` into the client ring buffer
  (`BattleSystem_GetClientMessage`); in link battles it goes over comms.
  Client-to-server replies travel the symmetric server buffer /
  `BattleIO_EnqueueVal/DequeueVal` queues (`battle_lib.h`).
- **Client (presentation)** - per-battler `BattlerData` dispatched in
  `battle_display.c` (`BattleDisplay_InitTask*`), `battle_controller_player.c`
  (menus/input), animations, text, sound. It acknowledges by clearing
  `battlers[battler]->data[0]`; the server waits on that for animated steps.

Commands crossing server->client (grouped): setup/encounter
(`SETUP_UI, SET_ENCOUNTER, SHOW_ENCOUNTER, SHOW_POKEMON, RETURN_POKEMON,
DELETE_POKEMON, trainer slide/throw`), menus (`SET_COMMAND_SELECTION,
SHOW_MOVE/TARGET/BAG/PARTY/YES_NO_MENU`), messages (`PRINT_ATTACK_MESSAGE,
PRINT_MESSAGE, trainer/recall/send-out/battle-start/lead/result/escape/forfeit`),
animation/sound (`SET_MOVE_ANIMATION, FLICKER_BATTLER, PLAY_SOUND, PLAY_MUSIC,
FLY_MOVE_HIT_SOUND_EFFECT, status-effect via SET_MOVE_ANIMATION secondary`),
gauges/state mirrors (`UPDATE_HP_GAUGE, UPDATE_EXP_GAUGE, REFRESH_HP_GAUGE,
SET_STATUS_ICON, PLAY_FAINTING_SEQUENCE, UPDATE_PARTY_MON, REFRESH_PARTY_STATUS`),
and misc (`FADE_OUT, TOGGLE_VANISH, SET_MOSAIC, AFFINE_PULSE (Mega cue),
CHANGE_WEATHER_FORM, UPDATE_BG, party-gauge show/hide, SUBMIT_RESULT`).
Client->server: selected command/move/target/bag item/party switch/yes-no
(`BattleController_EmitSelected*` on the player controller), plus IO-queue
acks. Presentation must not mutate rules state except through those replies.

## 2. Event stream (engine-side, presentation-independent)

Module: `include/battle/battle_events.h`, `src/battle/battle_events.c`.
Events are emitted from the server side (Emit* chokepoints + BattleContext
snapshot diff in `BattleEvents_Poll`, called from the battle task), never
from display code, so normal and fast mode produce identical streams.

Enable: `SIM_BATTLE_EVENTS=<file>` appends one JSON object per line (JSONL).
Headless: `{"cmd":"battle_events"}` returns `{"ok":true,"events":[...]}`
with events since the last call (and clears the pending queue). Events are
always collected in a bounded ring (4096) once a battle starts, file or not.

Schema (v1). Every line: `{"v":1,"seq":N,"turn":T,"type":"...", ...}`.
`seq` is monotonic per battle, starting 0. Battlers are indices
0..maxBattlers-1. Names are symbolic (`SPECIES_*`, `MOVE_*`, `ITEM_*`,
ability id numeric until a name table is wired).

| type | extra fields |
|---|---|
| `battle_start` | `battle_type`, `max_battlers`, `battlers:[{battler,species,species_id,level,hp,max_hp,held_item}]` |
| `turn_start` | (turn in header) |
| `move_chosen` | `battler, move, move_id, target, mega(bool)` |
| `move_used` | `battler, move, move_id, target` |
| `hit` / `miss` | `battler(attacker), target, move_id` |
| `damage` | `battler(target), attacker, amount, hp_after, max_hp, critical(bool), effectiveness` (`"super"``"not_very"``"immune"``"normal"`) |
| `heal` | `battler, amount, hp_after, max_hp` |
| `status` | `battler, status` (BattleMon.status bitmask after change) |
| `stat_stage` | `battler, stat, stage, delta` (stat = index into statBoosts) |
| `faint` | `battler` |
| `switch` | `battler, species, species_id, party_slot, out_species_id` |
| `send_out` | `battler, species, species_id` |
| `item` | `battler, item, item_id` |
| `ability` | `battler, ability` (on announced-flag rising edge) |
| `weather` | `weather` (fieldConditionsMask weather bits), `mask` |
| `mega_evolution` | `battler, species_id(after), form` |
| `totem_aura` | `battler, species_id` (Totem battler detected at start / aura boost) |
| `battle_end` | `result` (`win`/`lose`/`flee`/`caught`/`draw` best-effort from battleEndFlag/outcome), `turns` |

Unknown/partial info is emitted as null/0 rather than omitted where the
table above lists it, so consumers can rely on keys. `effectiveness` is
derived from the damage event context (critical from `criticalMul>1` at
HP-gauge time; effectiveness string may be `normal` when the server did
not retain the mask - consumers should treat damage amount as ground truth).

## 3. Fast mode (null presentation)

`SIM_BATTLE_FAST=1`: in `SendMessage` (server->client, local battles only),
after enqueueing, the client slot is immediately acknowledged
(`battlers[battler]->data[0]=0` semantics via `BattleEvents_FastAck`) and
no animation/text/sound task is required to progress the server. Rules
code, script bytecode and RNG calls are unchanged and in the same order.

**Determinism invariant:** same `SIM_SEED` + same save/spec + same decisions
=> byte-identical event streams in normal and fast mode. Presentation code
must not consume the battle RNG; any violation found is a bug in the
presentation hook, not in the test. Proven by
`tools/battle/test_determinism.py` (runs one scripted battle both ways via
the headless protocol and diffs the JSONL).

Seed override: `BattleEvents_SetSeedOverride(u32)` (header `battle/battle_events.h`), or env `SIM_BATTLE_SEED=<n>`, replaces the field-supplied `dto->seed` for the battle LCRNG (`seedRandNext`/`seedDTO` in BattleMain init). engine-sim's `start_battle` should call it with the spec seed at battle setup, making battle outcomes independent of field frames. 0 = no override.

Fast-mode whitelist (acked at client-message receipt, end state is presentation-only and rules state is already final): all PRINT_* messages, PLAY_SOUND/PLAY_MUSIC, CLEAR_MESSAGE_BOX, UPDATE/REFRESH_HP_GAUGE, UPDATE_EXP_GAUGE, SET_STATUS_ICON. Sprite-creating, menu/input, move-animation and faint commands still run their tasks (acking those segfaults or corrupts teardown - verified). UPDATE (round 2): SET_MOVE_ANIMATION is also acked - a move animation's end
state is the battlers back at rest (the rules have already applied damage),
so skipping it is end-state-safe and is the single biggest wait. Measured on
the seed-777 Tristan battle (same drive script): total frames 5771 normal /
4451 fast-v1 (text+gauges) / 3371 fast+anim-ack; battle portion ~2.2x fewer
frames, DETERMINISM_OK still holds. PLAY_FAINTING_SEQUENCE must NOT be acked:
its task frees the sprite slot and the next ShowPokemon asserts
(monSpriteMan sprites[index].active) - verified. SHOW_POKEMON/SET_ENCOUNTER
(sprite creation) likewise stay.

Caveat: player-menu input still comes through the normal player controller
(headless clients drive it with press/touch or, for engine-sim, scripted
decisions). Fast mode only removes presentation waits.

## 4. Replay

- `SIM_BATTLE_RECORD=<file>`: at battle start writes a header line
  `{"v":1,"kind":"record_header","seed":...,"battle_type":...,"battlers":[...]}`
  (seed from `SIM_SEED` env / battle seed DTO when available), then every
  `move_chosen`/decision event as `{"kind":"decision",...}`, then the full
  event stream lines.
- `SIM_BATTLE_REPLAY=<file>`: loads the header, re-emits recorded decisions
  through the same recording queue the headless/sim driver consumes, runs
  (fast if `SIM_BATTLE_FAST=1`), and at `battle_end` compares the produced
  event types/fields (excluding `seq` timing fields) with the recording;
  prints `BATTLE_REPLAY_OK` or `BATTLE_REPLAY_MISMATCH ...` to stderr and,
  in headless, exposes the verdict via `{"cmd":"battle_events"}` last event
  `{"type":"replay_verdict","ok":bool}`.

Replay is a checker, not a save-state rewind: it requires the same build
and the same starting save/spec as the recording (engine-sim supplies it).

## 4b. Decision queue (scripted battles and replay)

Queue: `BattleDecisions_Push/P peek/Complete` in `battle_events.h`.
`BattleDecision{battler, action(move|switch|item|run), moveId, moveSlot(-1=by id), target(-1=auto), partySlot, itemId, mega}`.
Consumption is client-side: the player command/move/target menu tasks in
`battle_display.c` read the queue when they would poll input, set their
input (and `megaEvolutionTriggered` for mega), then emit and clean up
normally - so no menu task is orphaned. Bag/party sub-menus are hooked inside their own tasks (round 4):
BattlePartyTask_PartyPokemonScreen selects the queued party slot and exits
through its own cleanup (also serves the forced-switch party menu and the
party USE_ITEM target for bag items), and BattleBagTask MenuScreen /
UseItemScreen locate and confirm the queued item (pressing the pocket button
so the screen transition completes). Decisions complete per action via
BattleDecisions_MarkDone (forced switches never reach the command WAIT
state). Move decisions are recorded with their final target. Verified with
start_battle specs: switch, Potion, faint->forced switch and doubles all
record and replay with BATTLE_REPLAY_OK.
Lockstep: `{"cmd":"battle_decide","battler":0,"action":"move","move":"MOVE_X"|"move_index":0,"target":1,"mega":true}`
(also `switch`+`party_slot`, `item`+`item`, `run`). Move/item names resolve
via generated tables (`kHeadlessMoves`/`kHeadlessItems`; gen_headless_names.py
now also emits Moves/Abilities). Recording writes every selected move (both
sides, AI included) as `{"kind":"decision",...,"move_slot":N}` lines;
`SIM_BATTLE_REPLAY` pushes them back at battle start, so a replay file
alone reproduces the battle with no input script (text still advances via
press/step in lockstep) and verifies events as before.

## Battle spec (engine-sim, implemented)

A battle spec is one JSON object:

```json
{
  "battle_type": "wild",
  "seed": 42,
  "player": [
    {"species": "SPECIES_INFERNAPE", "level": 50,
     "moves": ["MOVE_FLARE_BLITZ", "MOVE_CLOSE_COMBAT"],
     "held_item": "ITEM_INFERNAPITE", "ability": "ABILITY_BLAZE",
     "nature": "NATURE_JOLLY", "ivs": [31,31,31,31,31,31],
     "evs": [0,252,0,252,0,4], "form": 0, "shiny": false}
  ],
  "opponent": [
    {"species": "SPECIES_BIDOOF", "level": 5, "moves": ["MOVE_TACKLE"]}
  ],
  "bag": [{"item": "ITEM_POTION", "qty": 5}],
  "key_stone": true,
  "double": false,
  "totem": false,
  "totem_boosted": false,
  "trainer_id": 1
}
```

- `battle_type`: `wild` (default), `trainer`, `double`, or `totem`
  (`totem` implies double + the Totem aura boost at battle start).
  `double`/`totem` booleans may also be set alongside any type.
- Parties: `player`/`opponent` (aliases `player_party`/`opponent_party`),
  1-6 mons. Per mon: `species` (required; `SPECIES_*` name/id spelling
  without the prefix also accepted), `level` (default 50), `moves`
  (up to 4 `MOVE_*` names, in slot order), `held_item` (`ITEM_*`),
  `ability` (`ABILITY_*`), `nature` (`NATURE_*`), `ivs`/`evs` as
  `[hp, atk, def, speed, spatk, spdef]`, `form`, `shiny` (accepted;
  personality-based shininess is not forced in v1).
- `bag`: items added to the player's bag before the battle
  (`Key Stone: use {"item":"ITEM_KEY_STONE"} or "key_stone": true`).
- `trainer_id`: existing trainer whose data (class/intro) is used for a
  `trainer` battle; the opponent party still comes from the spec.
- `seed`: seeds the battle RNG (`BattleEvents_SetSeedOverride`), so the
  same spec + seed + decisions replays identically.
- `restore_party` (default `true`): the player's real party and bag are
  backed up before the spec party is installed and restored when the battle
  ends (no blackout on a loss), so Battle Lab is safe on a real save. Set
  `false` to keep the spec party afterwards (e.g. to check that a Mega
  form reverted).
- `field`/`weather`: reserved; battles use the current map background,
  terrain and field weather in v1.

Names are resolved from the build's generated tables
(`headless_names`, extended with moves/abilities/natures) - nothing is
hand-maintained.

### `start_battle` headless command

From any field state (after a save is loaded):

```json
{"cmd":"start_battle","spec_path":"/abs/path/spec.json"}
{"cmd":"start_battle","battle_type":"wild","player":[...],"opponent":[...]}
```

The player's save party and bag are replaced from the spec first (use a
throwaway save: `SIM_SAVE_PATH` in a private run dir), then a custom
`FieldBattleDTO` runs through the normal encounter path
(`Encounter_NewHeadlessBattle`). Reply is `{"ok":true}` once the battle
task is queued; step frames and read `state` to observe the battle.
Errors: not in the field, unreadable `spec_path`, or no opponent mons
(the last is reported on stderr when the queued task runs).

## 5b. Battle spec coordination (engine-core notes)

Documented for coordination; engine-core only guarantees the events above
for any battle however started (wild, trainer, debug quick battle, or
engine-sim `start_battle`). Spec JSON, `start_battle` headless command and
`tools/battle/sim.py` are engine-sim's section of the night brief.

## 6. How engine-sim should consume this

1. Read events via file (`SIM_BATTLE_EVENTS=`) for offline tests, or poll
   `battle_events` in lockstep for interactive policies.
2. Drive decisions through the existing player controller (press/touch in
   lockstep today; scripted decision queue is engine-sim's `start_battle`
   follow-on). Do not patch battle_controller internals.
3. Cherry-pick engine-core commits from `/data/repos/dp-wt/engine-core`
   branch `engine/core` when the lead says they are ready.
