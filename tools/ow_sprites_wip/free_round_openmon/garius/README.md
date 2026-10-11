# Garius (rival): free-licence overworld candidates

Overview: `garius_overview.png`. Per candidate: `<key>_sheet.png` (4 facings x stand/step A/stand/step B at 4x, plus extra sets), `<key>_walk.gif`, `<key>_platinum_walk.png` (128x128, 4-bit, 16 colours, index 0 transparent, BGR555-snapped), and for kit builds `<key>_run.gif` and `<key>_platinum_walk_run.png` (128x256, walk + run).

## R1_openmon_red_spiky: Openmon NPC: spiky maroon hair, red shirt  **[PICK]**

- Source: https://screensmith.itch.io/openmon-npc-sprites-set-1
- Creator: Screen Smith (Openmon project), commissioned from a Fiverr artist
- Licence: CC0 1.0 (public domain)
- Licence text (quoted from where it is published): "NOT AI GENERATED, MADE BY A FIVERR ARTIST ... These sprites are released under a CC0 License. They were created as a part of commissions that I ordered and have the full rights to. Use them however you want, no attribution needed."
- Credit line: none required (optional: "Overworld sprite: Openmon NPC Sprites Set 1 by Screen Smith, CC0")
- Sets: walk only
- Colours: 15 in source -> 15 + transparent
- Notes: RECOMMENDED. Clean CC0. Spiky maroon hair and a red shirt: hot-headed colours, and it reads apart from both Darren picks. The design is plain rather than cocky; a pixel edit to the brows or a jacket would push the "brash" read.

## R1e_openmon_red_eclipse: R1 recoloured: "Eclipse" Garius (Arc 3)  **[PICK]**

- Source: https://screensmith.itch.io/openmon-npc-sprites-set-1
- Creator: Screen Smith (Openmon project), commissioned from a Fiverr artist
- Licence: CC0 1.0 (public domain)
- Licence text (quoted from where it is published): "NOT AI GENERATED, MADE BY A FIVERR ARTIST ... These sprites are released under a CC0 License. They were created as a part of commissions that I ordered and have the full rights to. Use them however you want, no attribution needed."
- Credit line: none required (optional: "Overworld sprite: Openmon NPC Sprites Set 1 by Screen Smith, CC0")
- Sets: walk (palette swap of R1, allowed by CC0)
- Colours: 15 in source -> 15 + transparent
- Notes: RECOMMENDED for Arc 3: R1 hue-mapped by `eclipse()` in `tools/build_free.py`. The red shirt becomes Eclipse violet, the hair near-black slate, and the dark greys violet-black. CC0 allows this edit. Adding the Eclipse ring on the chest is a few pixels.

## R2_tuxemon_cooldude: Tuxemon "Cool Dude" (spiky hair, shades)

- Source: https://github.com/Tuxemon/Tuxemon/tree/development/mods/tuxemon/sprites/cooldude.png
- Creator: Catch Challenger art team (Jordan Brule); front sprite by Sanglorian
- Licence: CC BY-SA 4.0 per Tuxemon wiki footer; Tuxemon labels Catch Challenger art "(CC BY)"  [FLAG: attribution + share-alike; weaker per-file chain]
- Licence text (quoted from where it is published): wiki.tuxemon.org/Cool_Dude: "Front sprite by Sanglorian. Overland sprite by Catch Challenger." Wiki footer: "Content is available under Creative Commons Attribution-ShareAlike unless otherwise noted." Tuxemon: "A sprite from Catch Challenger (CC BY), art director Jordan Brule."
- Credit line: "Overworld sprite: Tuxemon Cool Dude, Catch Challenger (Jordan Brule), CC BY-SA 4.0"
- Sets: walk only
- Colours: 18 in source -> 15 + transparent
- Notes: Runner-up: the most "brash" silhouette (spiky hair, shades, jacket). Licence chain: Catch Challenger art, published by Tuxemon as CC BY / CC BY-SA. Weaker than the CC0 picks, because the original Catch Challenger datapack repo states no licence of its own. Chibi proportions.

## R3_openmon_green_spiky: Openmon NPC: spiky green hair  **[runner-up]**

- Source: https://screensmith.itch.io/openmon-npc-sprites-set-1
- Creator: Screen Smith (Openmon project), commissioned from a Fiverr artist
- Licence: CC0 1.0 (public domain)
- Licence text (quoted from where it is published): "NOT AI GENERATED, MADE BY A FIVERR ARTIST ... These sprites are released under a CC0 License. They were created as a part of commissions that I ordered and have the full rights to. Use them however you want, no attribution needed."
- Credit line: none required (optional: "Overworld sprite: Openmon NPC Sprites Set 1 by Screen Smith, CC0")
- Sets: walk only
- Colours: 9 in source -> 9 + transparent
- Notes: Same CC0 pack. Wild green hair; reads energetic but young (kid proportions).

## R4_stock_acetrainer_recolour: FALLBACK: stock Ace Trainer M, recoloured

- Source: repo: res/prebuilt/data/mmodel/mmodel (stock member 0x0B)
- Creator: Game Freak (stock Platinum)
- Licence: n/a: the game's own asset (owner-approved fallback)
- Licence text (quoted from where it is published): n/a
- Credit line: n/a
- Sets: walk (stock member, every movement)
- Colours: 14 in source -> 14 + transparent
- Notes: FALLBACK (the owner-approved option): the stock Platinum Ace Trainer M with copper hair and a blue jacket. Native size and every stock movement, but it is the game's own asset and the silhouette is a common trainer class.
