# Arc 2 cutaways: caller contract (s-cutaways)

Three self-contained scenes the player watches but is not in: 2.4, 2.13 (the "violet room") and 2.19 (Kahn's cliff).
The caller is identified by `VAR_ARC2_PROGRESS` alone. There are no temp vars and no flags to pass.

| Scene | Caller (sets, then warps) | Entry warp | Cutaway sets | Return (the cutaway warps back and fades in) |
|---|---|---|---|---|
| 2.4 Kahn, Indra | s-jubilife, after Cyrus battle 1: **5** | `Warp MAP_HEADER_GALACTIC_HQ_CONTROL_ROOM, 0, 8, 9, DIR_NORTH` | **9** | `MAP_HEADER_JUBILIFE_CITY` 168,777 `DIR_SOUTH` (outside the Trainers' School door) |
| 2.13 Saros, Kahn | s-eterna, after the Haven: **35** | `Warp MAP_HEADER_GALACTIC_HQ_CONTROL_ROOM, 0, 8, 9, DIR_NORTH` | **39** | `MAP_HEADER_ETERNA_CITY` 305,520 `DIR_SOUTH` (below the Haven door, 305,519) |
| 2.19 Kahn's cliff | s-route214, at Route 214 after rift-b's Skarmory calm: **63** | `Warp MAP_HEADER_ROUTE_222, 0, 742, 796, DIR_NORTH` | **69** | `MAP_HEADER_ROUTE_214` 726,665 `DIR_SOUTH` (the `DW_ROUTE_214` exit tile) |

## What the caller does

```asm
    // ... last line of the caller's scene ...
    SetVar VAR_ARC2_PROGRESS, 5          // 35 for 2.13; 63 is already set by rift-b for 2.19
    FadeScreenOut
    WaitFadeScreen
    Warp MAP_HEADER_GALACTIC_HQ_CONTROL_ROOM, 0, 8, 9, DIR_NORTH
    ReleaseAll                           // no FadeScreenIn: the cutaway lifts the black screen itself
    End
```

- **Don't fade in after the Warp.** The cutaway hides the player in OnResume, before the first frame is drawn, and
  then fades in. If a caller does fade in, the scene still plays correctly; that was tested from a lit screen.
- **Don't use `PlaySound` in a scene that warps.** It pauses the music, and the next `Warp` then never finishes: the
  map id changes, but the screen stays black. Use `PlayFanfare SEQ_SE_...` for sound effects. Found while building these
  scenes; it applies to every story workstream.
- 2.19 has no caller code on the DW side. rift-b's `DW_ROUTE_214` exit lands on Route 214 at 63, and s-route214 sends
  the player to Route 222 from there (on load, or a frame script keyed on 63). Once the cutaway has set 69, Route 214
  won't send the player again.
- After the return, the caller's map runs its normal OnTransition at the new value (9, 39 or 69): Jubilife at 9 has
  no Rowan or Ruth (s-jubilife), Eterna at 39 is after the Haven (s-eterna), Route 214 at 69 is after the totem
  (s-route214).

## What the cutaway maps do (owned by s-cutaways)

- **Galactic HQ control room** (`scripts_galactic_hq_control_room.s`):
  - OnTransition at 5 or 35 shows Kahn plus Indra (5) or Saros (35), using map-local hide flags `0x30-0x32`.
  - It hides stock Saturn, Charon and the lake trio by setting `FLAG_UNK_0x0236`/`0x0237`/`0x029E`. Their old values are saved in `VAR_MAP_LOCAL_5-7` and put back before the return warp, so the stock Galactic HQ is untouched (tested).
  - At any other value the room is stock.
  - The scenes run from an on-frame table: 5 → entry 16, 35 → entry 17.
- **Route 222** (`scripts_route_222.s`):
  - At 63 only, Kahn stands at the cliff edge (742,794, facing the sea; map-local flag `0x30`). The player is the hidden camera anchor at 742,796.
  - Scene: on-frame entry 9. Player hiding: OnResume, entry 10.
  - Night is not forced: the clock decides, so the scene plays at any time of day.
  - Route 222's trainers are all far from 742,796.
- Each scene sets the next value just before its return warp, so it runs once. Re-entering either map later shows the
  stock map with no Arc 2 cast.

## Flags and vars

None of s-cutaways' allocated flags (`FLAG_UNK_0x0934-0x0935`) are used. Hide flags are map-local (`0x30-0x32`, cleared
on every map load and set again by OnTransition). `VAR_MAP_LOCAL_5-7` in the control room hold the stock flag values
during a cutaway.

## Not built (P2 or art)

- No Eclipse Shard object on the console: no shard sprite exists. The pulse is a white flash plus `SEQ_SE_PL_SYUWA`.
- No violet palette tint on the room.
- Kahn holds no visible Poke Ball, and no sprite variant exists. Kahn and Indra use art-ph's placeholder sprites until the
  real art lands.
