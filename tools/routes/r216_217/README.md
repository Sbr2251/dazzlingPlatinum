# Routes 216-217: Teo's Memorial Ridge & Indra's Snowy Camp

Reproducible pipeline (inputs read from git: stock chunks/lighting at `406c75f6a8`, stock set 014 at HEAD):

    ~/.venvs/desmume/bin/python tools/routes/r216_217/dump_stock.py 110     # stock permissions / heights / props
    ~/.venvs/desmume/bin/python tools/routes/r216_217/textures.py --preview DIR
    ~/.venvs/desmume/bin/python tools/routes/r216_217/build_art.py --preview DIR   # all checks + field-camera renders
    ~/.venvs/desmume/bin/python tools/routes/r216_217/build_art.py --write   # map_data_109/110, set 080, lighting_set_008
    python3 tools/routes/r216_217/story.py                                    # BG events, scripts, text (idempotent)
    python3 tools/dazzling/test/static_checks.py

Showcase (absolute tiles):

| Landmark | Chunk | Blocked | Stand (x, z, facing) | BG event |
|---|---|---|---|---|
| Teo's Memorial Marker (Route 216 cliff ledge, faces south to Mt. Coronet) | map_data_110 | (316..318, 401) | (317, 402, north) | `Route216_TeoMemorial` at (317, 401) |
| Indra's camp scanner crate / journal (Route 217 NE snowfield) | map_data_109 | (313..316, 360..362), (311..312, 360) | (312, 361, north) | `Route217_IndraCamp` at (312, 360) and (311, 360) |

Chunks 106, 107, 108, 111, 112 are untouched (checked byte-identical); BDHC and props of 109/110 are stock.
