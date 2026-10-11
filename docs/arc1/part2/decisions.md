# Owner decisions (2026-10-08), overriding /tmp/act1p2/spec.md where they differ

- D1 Ruth's interim sprite: CONFIRMED `OBJ_EVENT_GFX_DP_PLAYER_F` (after the lead's smoke test; fallback `OBJ_EVENT_GFX_SCIENTIST_F`).
- D2 Saros on the big screen: CHANGED. A dedicated art stream ("Art", which also absorbs the spec's optional Stream E)
  designs a real Saros overworld sprite. Stream C stages Saros "on the big screen" with that sprite (for example
  standing on/in front of the Jubilife TV facade, framed by the screen flash and TV sound effects), speaker label
  "Saros:" or "Saros (on screen):", as C sees fit. No battle, so no trainer class or battle sprite in Arc 1.
- D3 Eclipse grunts: CHANGED. The Art stream designs Team Eclipse grunt overworld sprites (male and female):
  "the Eclipse look (dark, with a violet eclipse ring)" (docs/story/artwork.md:121). Stream C uses them for the
  rally grunts. No grunt battles in Arc 1, so no trainer class/battle sprites yet (note as follow-up).
- D4-D7, D9-D12, D14: spec defaults.
- D8 stock items: CONFIRMED spec default (Ruth gives the Town Map with the 5 Poke Balls; Mom keeps the Journal;
  Parcel, TM27 and VS Recorder dropped in Arc 1; Poketch campaign stays optional).
- D13 post-Arc-1 gate: CONFIRMED "To be continued..." at Jubilife's north exit at state 16.
- L9's "mirror into the Google Doc" is NOT authorised: do not edit the owner's Google Doc. Repo docs only.

## Sprite constants (registered by the lead pre-work with placeholder art so every stream builds from day 1)

The pre-work registers these object gfx IDs up front (following the Totem sprites' pattern, commit bfe72932eb,
generated/object_events_gfx.txt + res/field/objects/...), each initially a copy of a stock sprite:

| constant | placeholder copy of | final art by |
|---|---|---|
| `OBJ_EVENT_GFX_SAROS` | a stock adult male NPC of the same sheet layout (e.g. the gentleman) | Art |
| `OBJ_EVENT_GFX_ECLIPSE_GRUNT_M` | `OBJ_EVENT_GFX_GRUNT_M` | Art |
| `OBJ_EVENT_GFX_ECLIPSE_GRUNT_F` | `OBJ_EVENT_GFX_GRUNT_F` | Art |
| `OBJ_EVENT_GFX_ARC1_RIFT` | a stock small static object | Art |
| `OBJ_EVENT_GFX_TOTEM_HITMONLEE_VIOLET` | `OBJ_EVENT_GFX_TOTEM_HITMONLEE` | Art |

Art owns only those PNGs (and its own generator script under tools/arc1_sprites/ plus a design sheet under
docs/story/art/). Streams A-D reference the constants and never touch the PNGs or the gfx registration files.
If a placeholder can't be registered cleanly for some constant, the pre-work documents the fallback in
/tmp/act1p2/handoff/sprites.txt and the streams use the stock constant named there.
