# Route 215 — Flooded Lowland (routes wave 2, Arc 2)

Rain runoff from the Route 214 rift has flooded Route 215's lowland: standing puddles (with the stock splash /
reflection puddle behaviour), weathered timber boardwalks over the wettest stretches, Team Eclipse dual-tyre truck
ruts running east through MAP_070 / MAP_071 to the Veilstone gate, three tarp-and-crate staging clusters with amber /
violet work lamps, and an overcast slate-blue rain lighting set. Contract: `docs/routes_wave2/PLAN.md`.

Chunks MAP_069 / 070 / 071 (matrix row z 18, x 576..671, z 576..607) are edited in place with
`tools/world_art/chunkedit.py`: every stock shape, material, prop and BDHC byte is kept, new geometry is appended.
The west (Route 210, x 576) and east (Veilstone gate, x 671) seam columns are untouched.

| file | what |
|---|---|
| `common.py` | Chunk cells, stock readers (from git `BASE_REV`), tile maps. |
| `inspect_stock.py` | ASCII permissions / BDHC heights / texture usage / events of the stock route. |
| `show.py x0 z0 x1 z1` | Tile classes of a rect (flat ground, grass, blocked, slopes, events). |
| `paths.py` | Walk graph (4-neighbour + one-way ledges); reachability and the shortest Route 210 -> gate path. |
| `textures.py` | Set 078 = stock set 010 + `r215_board`, `r215_ruts` (c0), `r215_puddle` (c0), `r215_crate` (c0). |
| `build_art.py` | The layout (FLOOD, BOARDWALKS, RUTS, CLUSTERS, SIGNS), chunk edits, puddle behaviour + prop blocking, lighting_set_006; every check. `--write` refuses on a FAIL. |
| `render.py` | NumPy software previews (top view, field-camera views) decoded from the built NSBMD + set. |
| `verify_r215.py` | Headless in-game run (Linux/macOS SDL3 build): viewpoints day/night, both BG_EVENTs, the boardwalk walk, the Route 210 seam and the Veilstone gate warp. |

```
~/.venvs/desmume/bin/python tools/routes/r215/build_art.py           # dry run + checks
~/.venvs/desmume/bin/python tools/routes/r215/build_art.py --write   # chunks, set 078, lighting_set_006
~/.venvs/desmume/bin/python tools/routes/r215/render.py /tmp/r215 --top --views
python3 tools/routes/r215/verify_r215.py build_linux /tmp/r215/game --night
python3 tools/dazzling/test/static_checks.py
```

## Layout

- Flood zones (puddle blobs on flat behaviour-0 ground; puddle-covered tile centres get `TILE_BEHAVIOR_PUDDLE` 0x16):
  west entry x 577..589 z 595..601, lowland x 584..606 z 589..594 (MAP_069), x 608..621 z 588..597 and the north
  field x 630..645 z 583..587 (MAP_070), south field x 640..654 z 590..593, lane x 644..658 z 596..599 and the gate
  approach x 660..667 z 595..601 (MAP_071, low ground h 0).
- Boardwalks (decks at the BDHC floor + 0.03 tiles): x 577..587 z 598..599, x 595..606 z 591..592,
  x 616..621 z 592..593.
- Ruts: north field z 585..586 x 630..656 (MAP_070 -> 071); south field z 590..591 -> x 644..645 down to the lane ->
  z 597..598 to x 658 (the gate stairs); gate approach z 598..599 x 661..667.
- Staging clusters (tiles blocked): north field x 630..631 z 583..584 (amber lamp), south field x 655..656 z 592..593
  (violet lamp, BG_EVENT `Route215_EclipseCrates` at 655,592), gate x 665..667 z 600..601 (amber lamp, barrier).
- Drainage sign post at 594,590 (blocked; BG_EVENT `Route215_DrainageSign`, read from 595,590 facing west).
