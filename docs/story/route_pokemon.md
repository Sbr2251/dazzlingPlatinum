# Pokemon route changes: more Gen 3, and Gen 5 (draft)

Mirrored in the "Pokemon Route Changes" tab of the story doc.

## The rules

- Gen 3 Pokemon are already in the game's data (all 493 species are). Adding more of them only means editing encounter tables.
- Gen 5 Pokemon are not in the game yet: species stop at Arceus (#493).
- Gen 5 sprites are covered: tools/gen5_sprites/gen5_stream.py already builds the game's battle sprites from the PokeAPI sprites repository's Black/White animated GIFs, which include every Gen 5 species (#494-649), with front, back, shiny and female versions. The same tool can import them, and it also writes the classic 80x80 sprites used outside battle.
- What Gen 5 still costs: (1) Engine room. The save file's Pokedex block has seen/caught bitfields sized for 493 species, and Platinum stores alternate forms (Deoxys, Wormadam, Giratina-Origin, Shaymin-Sky, Rotom) in the species IDs right after #493. Adding #494+ means moving those forms and resizing the Pokedex save data, which breaks old saves. (2) Data: base stats, learnsets, evolutions and Pokedex entries (available from PokeAPI or Showdown data). (3) Icons, cries and footprints. (4) Some Gen 5 abilities and moves need adding or substituting. Because of (1), it's worth doing all of Gen 5's IDs in one pass, even if only phase 1 gets placed in the wild at first.
- Add, don't replace: Sinnoh's own Pokemon stay. New species mostly take swarm, day/night, Poke Radar and GBA dual-slot slots, which players can't otherwise use in this hack.
- Placement follows the story and the new maps where it can: grief Pokemon in the memorial town, clockwork Pokemon at the Dialga palace, meteor Pokemon at the Meteor Shrine.
- Levels follow the new gym order.

## Gen 5, phase 1: tied to the story and the new maps (27 lines)

| Gen 5 line | Where |
|---|---|
| Roggenrola | Oreburgh Mine, Iron Island |
| Drilbur | Oreburgh Mine, Iron Island |
| Timburr | Oreburgh Mine, Routes 206-207 |
| Woobat | Ravaged Path, Mt. Coronet |
| Sewaddle | Route 203, Eterna Forest |
| Venipede | Eterna Forest |
| Cottonee | Route 204, Route 218 |
| Throh and Sawk | Route 211 |
| Mienfoo | Route 210 |
| Sigilyph | Celestic Town ruins |
| Yamask | Solaceon Town |
| Litwick | Old Chateau, Lost Tower |
| Tympole | Route 215, Great Marsh |
| Elgyem | Meteor Shrine, Veilstone |
| Sandile | Valor Basin, Route 214 |
| Scraggy | Route 214 |
| Pawniard | Route 214 |
| Stunfisk | Great Marsh |
| Frillish | Routes 213, 222, 223 |
| Klink | The clockwork palace, Fuego Ironworks |
| Cubchoo | Routes 216-217 |
| Vanillite | Routes 216-217 |
| Tynamo | Route 222 |
| Golett | Umbral Palace |
| Axew | Victory Road |
| Deino | Victory Road (rare) |
| Larvesta | Mt. Coronet molten depths (rare) |

## Gen 5, phase 2: nice to have (23 lines)

Patrat, Lillipup, Pidove, Purrloin, Blitzle, Emolga, Ducklett, Foongus, Minccino, Gothita, Trubbish, Karrablast, Shelmet, Alomomola, Joltik, Heatmor, Durant, Druddigon, Cryogonal, Darumaka, Petilil, Rufflet, Vullaby.

## Arc 1: start to Gym 1

| Area | Theme | Add: Gen 3 | Add: Gen 5, phase 1 | Add: Gen 5, phase 2 | Notes |
|---|---|---|---|---|---|
| Route 201 | Start of the game | Zigzagoon, Wurmple | - | Patrat, Lillipup | - |
| Route 202 | First catches | Poochyena (night), Taillow | - | Pidove, Purrloin (night) | - |
| Route 203 | On the way to Oreburgh | Ralts (rare), Whismur | Sewaddle | - | - |
| Oreburgh Gate and Oreburgh Mine | Mines; Act 1 ends here | Aron, Nosepass, Makuhita | Roggenrola, Drilbur, Timburr | - | - |
| Lake Verity | The castle lake | Surskit, Lotad (Surf, later) | - | Ducklett (Surf, later) | - |

## Arc 2: Gyms 2 to 5

| Area | Theme | Add: Gen 3 | Add: Gen 5, phase 1 | Add: Gen 5, phase 2 | Notes |
|---|---|---|---|---|---|
| Route 204 and Ravaged Path | First totem (Hitmonlee) | Shroomish, Whismur (Ravaged Path) | Woobat (Ravaged Path), Cottonee | - | - |
| Route 205, Floaroma, Valley Windworks | Flowers and wind | Electrike, Plusle and Minun (Windworks), Lotad (water) | - | Blitzle, Emolga, Ducklett | - |
| Eterna Forest | Second totem (Vespiquen) | Seedot, Shroomish, Nincada | Sewaddle, Venipede | Foongus, Karrablast (night) | - |
| Old Chateau | Haunted mansion | Shuppet | Litwick (rare) | - | Gengarite is hidden here. |
| Route 211 and the Mt. Coronet crossing | Mountain road to Celestic | Meditite, Makuhita, Numel | Throh and Sawk, Woobat, Roggenrola | - | - |
| Celestic Town | Ruins and the elder's shrine | Baltoy | Sigilyph (an ancient guardian, at the ruins) | - | - |
| Route 210 | Fog and cliffs | Swablu, Absol (rare: it senses disaster, and the rifts) | Mienfoo | - | Remove the stock fog on the north half, or make it rift mist (gym order check). |
| Solaceon Town and Route 209 | The town of Eclipse's believers, with the memorial wall | Duskull | Yamask (it carries the face of who it used to be) | Minccino, Gothita | Yamask in a town full of grief is deliberate. |
| Lost Tower | Graves; the Spiritomb totem | Duskull, Shuppet | Litwick | - | - |
| Route 215 | Flooded lowland, Eclipse truck route | Lotad, Surskit, Castform (rain) | Tympole | Shelmet | - |
| Veilstone City and the Meteor Shrine | The fallen star | Lunatone (night), Solrock (day), Beldum (very rare, postgame) | Elgyem | - | Meteor Pokemon at the meteor shrine. |
| Route 214 | Skarmory totem; violet sky over the rift | Zangoose (day), Seviper (night), Absol (rare, near the rift) | Sandile, Scraggy, Pawniard | - | - |
| Valor Lakefront and the Valor Basin | The dry lakebed | Trapinch, Cacnea, Barboach (fishing in the puddles) | Sandile | Darumaka | - |
| Route 213 and Pastoria | Beach; the Lapras totem | Wingull, Corphish, Carvanha (fishing), Clamperl (Surf), Wailmer (Surf) | Frillish (Surf) | Alomomola (Surf) | - |
| Great Marsh | Swamp | Tropius, Kecleon, Lotad | Stunfisk, Tympole | Karrablast, Shelmet | - |
| Route 212 and the new Lake Valor | Rain road, and the clockwork palace | Kecleon (Route 212 south), Baltoy (palace grounds) | Klink (palace grounds) | Petilil, Cottonee | - |
| Route 208 and Hearthome | - | Swablu | - | Minccino | - |

## Arc 3: Gym 6 to the League

| Area | Theme | Add: Gen 3 | Add: Gen 5, phase 1 | Add: Gen 5, phase 2 | Notes |
|---|---|---|---|---|---|
| Canalave City and Route 218 | The fairy route | Mawile, Ralts, Azurill and Marill, Snubbull, Clefairy, Togepi (rare) | Cottonee | - | Fairy typing: check which species the engine already treats as Fairy. |
| Iron Island | Aggron totem; deep tunnels | Aron, Lairon | Drilbur, Roggenrola | Durant | Lucarionite comes from Riley here. |
| Fuego Ironworks | Eclipse's shard-machine foundry | Magnemite | Klink | Joltik, Trubbish | Scizorite is hidden here. |
| Routes 206 and 207 | Eclipse's supply road into Mt. Coronet | Gulpin, Numel | Timburr | Trubbish | - |
| Routes 216 and 217, Acuity Lakefront, Snowpoint | The mountain pass, Teo's memorial; the Mamoswine totem | Snorunt, Spheal | Cubchoo, Vanillite | Cryogonal (night, rare) | - |
| Mt. Coronet molten depths | The race for Giratina | Numel, Torkoal, Slugma | Larvesta (rare) | Heatmor, Durant (a predator and its prey, together) | - |
| Umbral Palace | Half in the Distortion World | Sableye | Golett | - | - |
| Route 222 | Coast lit violet by the Route 223 rift | Electrike and Manectric, Wingull | Tynamo, Frillish | Ducklett | - |
| Route 223 | Kingdra totem; the final battle | Wailmer and Wailord, Relicanth (rare, Super Rod) | Frillish | Alomomola | - |
| Victory Road | The last cave | Bagon (rare) | Axew, Deino (rare) | Druddigon | - |

## Postgame

| Area | Theme | Add: Gen 3 | Add: Gen 5, phase 1 | Add: Gen 5, phase 2 | Notes |
|---|---|---|---|---|---|
| Postgame routes (224-230), Stark Mountain, Battle Zone | After the credits | Absol, Relicanth, Zangoose and Seviper, Tropius, Bagon and Beldum (rare) | - | Rufflet and Vullaby (Route 228 desert), Druddigon, Heatmor | - |
| Postgame gift | - | Rowan gives one of the Gen 3 starters (Treecko, Torchic or Mudkip), already in the game's data | - | - | Gen 5 starters could follow if Gen 5 is added. |

