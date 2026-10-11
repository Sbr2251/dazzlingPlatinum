# Solaceon Town: the memorial wall

Arc 2 round 3 (workstream world-art), plan S4 / scene 2.16a: Team Eclipse's memorial wall, "every photo labelled with a
name, a date and a place". s-celestic owns the scene and placed its five sign events on the white fence west of the
main road (`events_solaceon_town.json` on `a2/s-celestic`: x 556, z 652..656, read from x 557 facing west; Indra stands
at (557,654) in the cutaway). This tool builds the wall itself, as terrain, on exactly those tiles.

Only overworld chunk `map_data_072` (matrix cell 17,20: x 544..575, z 640..671) and texture set 010 change.
Permissions, BDHC, props and every other chunk are stock.

## Files

| file | what |
|---|---|
| `textures.py` | Appends `sol_wall` (128x16, five 16x16 cells of pixel art) and the `sol_stone` palette to set 010, append-only, rebuilt from `BASE_REV`. |
| `build_wall.py` | Builds `map_data_072` from the stock chunk at `BASE_REV`: drops the fence segment, adds the wall and its five boards. Prints budgets and checks; refuses `--write` if one fails. |

```
python3 tools/solaceon_town/textures.py --write
python3 tools/solaceon_town/build_wall.py --write
make release
```

## What it looks like

```
      x 550 ....... 555 556 557 558..562
 651  F F F F F F F F  #   .   road        F  stock picket fence of the flower pen (stays)
 652  .  flowers  .    P   r   road        P  board: photo cards              (sign 652: photos)
 653  .           .    D   r   road        D  board: a child's Ponyta drawing (sign 653)
 654  .           .    E   r   road        E  board: one card, ELIAS          (sign 654); Indra's spot is (557,654)
 655  .           .    B   r   road        B  the violet Eclipse banner       (sign 655)
 656  F F F F F F F F  T   r   road        T  board: Teo's new card, shiny pin (sign 656)
                                           r  reading tiles (walk), x 557
```

- The stock picket fence along x 556 (a flat strip at h 1.375 plus two corner posts) is dropped; the pen's east-west
  fences stay and end against the wall.
- A low stone wall (stock `blueglay` texels, new `sol_stone` palette, warm grey), x 556.06..556.94, z 651.55..656.8,
  0.55 tiles high.
- Five boards stand on it, one per sign tile, in stone frames, leaning back 40 degrees so the fixed camera and the
  road both see them. Like the stock north-south fences (drawn as flat strips), they are drawn for the camera rather
  than literally on the wall's east face.
- All lit like stock. Set 010 grows by 1072 B of VRAM (44880 -> 45952 B). Chunk 072: 426 -> 436 polygons,
  20568 -> 21360 B of model.

## Not done here

- Teo's card is terrain, so it is on the wall in every story state (the sign only reads from state 49). A card that
  appears when Indra pins it would need an object event (s-celestic's file), not map data.
