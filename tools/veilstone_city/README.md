# Veilstone City: the Meteor Shrine

Arc 2 round 3 (workstream world-art). The bible lists Veilstone's meteorite garden as the **Meteor Shrine (NEEDS
DESIGN)**: Maylene's family keeps the meteorites, and s-veilstone stages her Key Stone trial (2.17b) there. This tool
turns the stock garden into a small shrine without moving a single tile of gameplay.

Only overworld chunk `map_data_080` (matrix cell 22,19: x 704..735, z 608..639) and texture set 011 change.
Permissions, BDHC, props and every stock face of the chunk are unchanged (new geometry is appended only).

## Files

| file | what |
|---|---|
| `textures.py` | Appends `vs_shide` (8x16 paper streamer) and five palettes to set 011, append-only, rebuilt from `BASE_REV`. |
| `build_shrine.py` | Builds `map_data_080` from the stock chunk at `BASE_REV` plus the shrine. Prints budgets and checks; refuses `--write` if one fails. |

```
python3 tools/veilstone_city/textures.py --write
python3 tools/veilstone_city/build_shrine.py --write
make release
```

## The shrine

The stock garden is three sunken pits: A (x 727..731, z 614..618), B (x 730..733, z 621..624) and the big pit C
(x 728..735, z 626..633) with its steps at x 731..732, z 632..633. The stock meteorite bg events are (729,616),
(731,622), (730,629), (732,628); s-veilstone's trial puts Maylene at (728,625), the stone box at (729,625) and Cyrus at
(731,619).

| piece | where | made of |
|---|---|---|
| torii over the top of pit C's steps | posts on the rim tiles (730,633) and (733,633); beams 2.85..3.94 tiles up, so the player walks under | `c07_criff` texels: `vs_red` (vermilion) posts and beams, `vs_black` cap |
| shimenawa with three shide | under the torii's tie beam | `nbridge` texels with `vs_straw`; `vs_shide` (new) |
| two stone lanterns | rim tiles (729,633) and (734,633) | stock `c07_criff` stone; fire boxes `c07_base_x` with `vs_glow`, unlit so they glow at night |
| roped frames | north rims of pits A, B and C, on short wooden posts | `vs_wood` posts, `vs_straw` rope, `vs_shide` |

Everything stands on tiles that are already blocked in stock (checked), and no object or bg event is on them. The
trial tiles, Cyrus's spot and the walk down pit C's steps stay walkable.

Set 011 is used only by Veilstone City among the overworld headers. It grows by 192 B of VRAM (49440 -> 49632 B).
Chunk 080: 1098 -> 1221 polygons (stock Lake Verity chunks reach 1176), 51480 -> 58152 B of model (buffer 61440:
3.3 KB of headroom left; trim the rope frames first if this chunk ever needs more). Worst on-screen map polygons
over every walkable tile (chunks 077/078/079/080, CAMERA_TYPE_DEFAULT): 544 at (727,631), stock 471; DS limit 2048.

## Not done here

- A "METEOR SHRINE" sign or an offering box would be events (s-veilstone's file).
