# Route 212 North: the brass gate

Arc 2 round 3 (workstream world-art), plan S11: "a brass gate in the rock, ticking... Arc 3's Lake Valor entrance". The
forest in the top-left corner of Route 212 North, just south of the Hearthome gate, becomes a rock outcrop with an
ancient brass gate set into it: an arched opening with a riveted brass ring, gold bars, a clock face over the arch and
gears on the rock. It reads as the door of Dialga's clockwork palace. It is a plant only: the gate is solid in Arc 2.

Only overworld chunk `map_data_085` (matrix cell 14,23: x 448..479, z 736..767) and texture set 012 change. The BDHC,
the props, the map matrix and every other chunk are stock.

## Files

| file | what |
|---|---|
| `textures.py` | Appends the gate's textures and palettes to set 012, append-only, rebuilt from `BASE_REV`. `--preview DIR` writes PNGs. |
| `build_gate.py` | Builds `map_data_085` from the stock chunk at `BASE_REV`: drops the trees in the corner, cuts the ground, adds the gate, sets the clearing's permissions. Prints budgets and checks, refuses `--write` if one fails. |
| `../world_art/chunkedit.py` | Shared with the Solaceon and Veilstone edits: edits a chunk model in place (untouched stock shapes keep their display lists and materials byte for byte), appends to texture sets, counts camera polygons. |

Regenerate (repo root, system `python3`, standard library only):

```
python3 tools/route_212_north/textures.py --write
python3 tools/route_212_north/build_gate.py --write
make release
```

Both read their stock inputs from git (`BASE_REV` = 065698b277, arc2 before world-art), so re-running is deterministic
and never feeds back on itself. Writers: `tools/lake_verity/` (see `docs/lake_verity_redesign/pipeline.md`).

## Layout

```
      x 448 ............ 455 456..
 736  T T T T T T T T T T  |  road     T  stock trees (row 736..737 stays)
 737  T T T T T T T T T T  |  road
 738  R R R R R R R R R R  |           R  the outcrop (blocked, as the stock trees were)
 739  R R R R R R R R R R  |              its south face leans back 20 deg, 6 tiles up the slope:
 740  R R R R R R R R R R  |              arch x 450.2..453.8, clock above, gears either side
 741  R R R R R R R R R R  |
 742  T T = = = = . . . .  |           =  stone apron (walk), the gate's threshold
 743  T T w w w w . . s .  |           w  tall grass (behaviour 0x02): the Route 212 North table, Klink included
 744  T T T T T T . . . .  |           s  stock arrow signpost (455,744)
```

## Art

Everything is stock texels; two small decals are new.

| surface | texels | palette | notes |
|---|---|---|---|
| rock face, east side | `criffp` / `criffp2` (grass fringe at the top) | stock `criff` / `criff2` | 1 repeat per 2 tiles |
| arch ring, jambs | `hanger` (round bosses) | `r212_brass` (new) | one column of bosses along the band: rivets |
| bars | `area07_hei_h` / `area07_hei_h3` | stock | the gold finials of the Pokemon Mansion fence; tops follow the arch |
| rails | `blueglay` | `r212_plate` (new) | |
| the hall behind | `shadowchip`; returns `criffp` | `r212_dark` / `r212_aged` (new) | floor: stock `blueglay` |
| clock | `r212_clock` 32x32, new | `r212_clock_pl` | hands at ten to two; Dialga-blue gem at the centre |
| gears (5) | `r212_gear` 32x32, new | `r212_gear_pl` | colour 0 transparent, see-through between spokes |
| apron, tall grass | `blueglay`, `nectgr` | stock | |

All materials are lit like stock (they follow the time of day). Round decals are stretched up the slope by
1 / cos(59.05 - 20 deg) so the fixed field camera (pitch 59.05) sees them round.

The facade top is a ridge: behind it a steep back slope (63 deg, always back-face culled) drops to the stock tree row at
z 736..737. Nothing rises into Hearthome City's view from its south exit (checked pixel-identical in game).

Set 012 is shared by Pastoria City, Route 212 North, Route 212 South and Trophy Garden. The additions cost 1184 B of
VRAM (48272 -> 49456 B; the largest stock set is 76416). Stock entries are asserted byte-identical.

Budgets: chunk 085 goes from 784 to 808 polygons (6 trees dropped) and from 37144 to 40016 B of model (buffer 61440).
Worst on-screen count over every walkable tile of the chunk is unchanged (222, at the south end).

## Not done here

- No event: if Arc 3 wants a "look at the gate" sign, the apron tiles (450..453, 742) face it; a bg event there needs
  the Route 212 North events owner.
- No animation: a ticking gear would need a `fldtanime.narc` entry (shared archive, not map data).
