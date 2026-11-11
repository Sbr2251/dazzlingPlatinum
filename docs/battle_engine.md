# Battle engine: specs, events, fast mode, replay

This file is the shared contract between engine-core (rules/presentation
split, event stream, fast mode, replay) and engine-sim (battle specs,
`start_battle`, `tools/battle/sim.py`, battle tests). engine-core owns the
event/fast/replay sections; engine-sim owns the spec section below. Until
engine-core's sections land, sim/test code works against normal mode and
the headless `state` reply (battler species/hp, `waiting`, turn).

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
- `seed`: declarative; the actual RNG seed is the process seed
  (`SIM_SEED` / sim.py `--seed`), which the spec value should match.
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

## Events / fast mode / replay (engine-core)

Pending engine-core. Expected interface (see NIGHT-BRIEF): one JSON event
per line in `SIM_BATTLE_EVENTS=<file>` (turn start, move used, hit/miss,
damage with crit/effectiveness, status, stat stage, faint, switch, item,
ability, weather, Mega, Totem aura, battle end), a `battle_events`
headless command, `SIM_BATTLE_FAST=1`, and
`SIM_BATTLE_RECORD`/`SIM_BATTLE_REPLAY`. sim.py uses these when present
(`--fast`, `battle_events`) and falls back to `state` polling otherwise.
