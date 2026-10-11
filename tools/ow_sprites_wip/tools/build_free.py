import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/tmp/a1r3/tools')
from free_src import *

OM_URL = 'https://screensmith.itch.io/openmon-npc-sprites-set-1'
OM_LIC = ('"NOT AI GENERATED, MADE BY A FIVERR ARTIST ... These sprites are released under a CC0 License. They were created '
          'as a part of commissions that I ordered and have the full rights to. Use them however you want, no attribution needed."')
OM = dict(licence='CC0 1.0 (public domain)', lic_quote=OM_LIC, url=OM_URL, creator='Screen Smith (Openmon project), commissioned from a Fiverr artist',
          credit='none required (optional: "Overworld sprite: Openmon NPC Sprites Set 1 by Screen Smith, CC0")')
TUX_URL = 'https://github.com/Tuxemon/Tuxemon/tree/development/mods/tuxemon/sprites'
CAB_URL = 'https://opengameart.org/content/edited-and-extended-24x32-character-pack'
CAB = dict(licence='CC-BY 3.0 (also OGA-BY 3.0)  [FLAG: attribution required]', url=CAB_URL,
           creator='Svetlana Kushnariova (Cabbit); walk cycles fixed by diamonddmgirl',
           lic_quote='OGA page licence field "CC-BY 3.0, OGA-BY 3.0". Original pack: "Attribution requirement: credit me as Svetlana Kushnariova and give my email address, lana-chan@yandex.ru". Edited pack: "as long as you properly credit the creator of the original character pack you do not necessarily have to credit me."',
           credit='"Character sprite by Svetlana Kushnariova (lana-chan@yandex.ru), CC-BY 3.0, https://opengameart.org/content/24x32-characters-with-faces-big-pack (walk cycle edits by diamonddmgirl)"')
KIT_URL = 'https://eeveeexpo.com/resources/317/'
KIT = dict(licence='Free use: "use, edit and share", credit appreciated  [FLAG: bodies built on vanilla Pokemon sprites]', url=KIT_URL,
           creator='Poltergeist / Coffee Cup (character-creation kit; also PokeCommunity thread 421381)',
           lic_quote='"You can freely use, edit and share it if you want. Credit and a link to your project would be appreciated, though!" Also: "even though some of the clothes are inspired by the game I created all resources from scratch (well, and from the vanilla sprites)."',
           credit='"Overworld sprite built with Poltergeist\'s Character Customization Resources (eeveeexpo.com/resources/317)"')

# ---------------------------------------------------------------- Darren, boy
add('darren_boy', 'B1_openmon_teal_jacket', 'Openmon NPC: dark-skinned boy, teal jacket', openmon(OM2, 5),
    sets='walk only', source_short='Openmon NPC Sprites Set 1 (Screen Smith), CC0', **OM)
add('darren_boy', 'B2_openmon_blue_hair', 'Openmon NPC: navy hair, green jacket', openmon(OM1, 2),
    sets='walk only', source_short='Openmon NPC Sprites Set 1 (Screen Smith), CC0', **OM)
add('darren_boy', 'B3_tuxemon_adventurer', 'Tuxemon "Adventurer" (protagonist option)', tux('adventurer'),
    sets='walk only', source_short='Tuxemon, overland by Catch Challenger adapted by Sanglorian; CC BY / CC BY-SA',
    url=TUX_URL + '/adventurer.png', creator='Catch Challenger art team (Jordan Brule), adapted by Sanglorian; design by Leo',
    licence='CC BY-SA 4.0 per Tuxemon wiki ("Content is available under Creative Commons Attribution-ShareAlike unless otherwise noted"); Tuxemon labels Catch Challenger art "(CC BY)"  [FLAG: attribution + share-alike]',
    lic_quote='wiki.tuxemon.org/Adventurer: "Overland sprites by Catch Challenger, adapted by Sanglorian. Art by Leo." Wiki footer: "Content is available under Creative Commons Attribution-ShareAlike unless otherwise noted." Tuxemon ATTRIBUTIONS.md / wiki File:Swim.png: "A sprite from Catch Challenger (CC BY), art director Jordan Brule. Project developer Herman Brule."',
    credit='"Overworld sprite: Tuxemon Adventurer, Catch Challenger (Jordan Brule), adapted by Sanglorian, CC BY-SA 4.0"')
kb = [('bases mf', ['m base light']), ('bottoms', ['jeans', 'navy']), ('tops', ['hoodie', 'red']), ('carrying stuff', ['sporty backpack', 'black']), ('hair', ['boy 2', 'brown'])]
kw, ksz = kit_walk(kit_compose('walk', kb))
kr, _ = kit_walk(kit_compose('run', kb))
kbk, _ = kit_walk(kit_compose('bike', kb))
add('darren_boy', 'B4_kit_boy', 'Kit build: hoodie + jeans + backpack (boy)', kw,
    extras=[('bike', [kbk[f][k] for f in FACINGS for k in (0, 1, 3)])], run=kr,
    sets='walk, run, bike (kit); swimming add-on exists (TechSkylander1518, eeveeexpo 373); no surf-on-Pokemon or fishing',
    source_short='Poltergeist character kit (Eevee Expo 317) - FLAG: vanilla-based bodies', **KIT)

# ---------------------------------------------------------------- Darren, girl
add('darren_girl', 'G1_openmon_blue', 'Openmon NPC: light-blue ponytail girl', openmon(OM2, 1),
    sets='walk only', source_short='Openmon NPC Sprites Set 1 (Screen Smith), CC0', **OM)
add('darren_girl', 'G2_openmon_dark_hair', 'Openmon NPC: dark hair, pink outfit', openmon(OM1, 6),
    sets='walk only', source_short='Openmon NPC Sprites Set 1 (Screen Smith), CC0', **OM)
add('darren_girl', 'G3_tuxemon_heroine', 'Tuxemon "Heroine" (protagonist option)', tux('heroine'),
    sets='walk only', source_short='Tuxemon, overland by josepharaoh99 (minor changes Sanglorian); CC BY-SA 4.0',
    url=TUX_URL + '/heroine.png', creator='josepharaoh99 ("Maple"), minor changes by Sanglorian; design by Leo',
    licence='CC BY-SA 4.0  [FLAG: attribution + share-alike]',
    lic_quote='Tuxemon ATTRIBUTIONS.md: "\\"Girl 1 Sprite\\" by josepharaoh99 is licensed under CC-BY-SA 4.0" and "\\"Female Trainer\\" by Leo is licensed under CC-BY-SA 4.0"; wiki.tuxemon.org/Heroine shows File:Josepharaoh99_maple_overland.png as the overland sprite; wiki footer "Content is available under Creative Commons Attribution-ShareAlike unless otherwise noted."',
    credit='"Overworld sprite: Tuxemon Heroine by josepharaoh99 and Leo (edits Sanglorian), CC BY-SA 4.0, https://wiki.tuxemon.org/Heroine"')
gb = [('bases mf', ['f base light']), ('bottoms', ['capris', 'navy']), ('tops', ['open jacket', 'orange']), ('carrying stuff', ['bag', 'yellow']), ('hair', ['girl 1/', 'red'])]
gw, _ = kit_walk(kit_compose('walk', gb))
gr, _ = kit_walk(kit_compose('run', gb))
gbk, _ = kit_walk(kit_compose('bike', gb))
add('darren_girl', 'G4_kit_girl', 'Kit build: open jacket + capris + bag (girl)', gw,
    extras=[('bike', [gbk[f][k] for f in FACINGS for k in (0, 1, 3)])], run=gr,
    sets='walk, run, bike (kit); swimming add-on exists; no surf-on-Pokemon or fishing',
    source_short='Poltergeist character kit (Eevee Expo 317) - FLAG: vanilla-based bodies', **KIT)

# ---------------------------------------------------------------- Garius
gar = openmon(OM2, 6)
add('garius', 'R1_openmon_red_spiky', 'Openmon NPC: spiky maroon hair, red shirt', gar,
    sets='walk only', source_short='Openmon NPC Sprites Set 1 (Screen Smith), CC0', **OM)


def eclipse(h, s, v):
    red = h > 340 or h < 8
    if red and s > 0.7:                 # red shirt -> Eclipse violet
        return 276, 0.62, min(1, v * 1.05)
    if red and 0.3 < s <= 0.6:          # maroon hair -> near-black slate violet
        return 255, 0.28, v * 0.62
    if s < 0.06:                        # dark greys -> violet-black
        return 262, 0.32, v * 0.9
    return h, s, v


add('garius', 'R1e_openmon_red_eclipse', 'R1 recoloured: "Eclipse" Garius (Arc 3)', hsv_map(gar, eclipse),
    sets='walk (palette swap of R1, allowed by CC0)', source_short='palette swap of Openmon spiky maroon hair (this research), CC0', **OM)
add('garius', 'R2_tuxemon_cooldude', 'Tuxemon "Cool Dude" (spiky hair, shades)', tux('cooldude'),
    sets='walk only', source_short='Tuxemon, overland by Catch Challenger; CC BY / CC BY-SA',
    url=TUX_URL + '/cooldude.png', creator='Catch Challenger art team (Jordan Brule); front sprite by Sanglorian',
    licence='CC BY-SA 4.0 per Tuxemon wiki footer; Tuxemon labels Catch Challenger art "(CC BY)"  [FLAG: attribution + share-alike; weaker per-file chain]',
    lic_quote='wiki.tuxemon.org/Cool_Dude: "Front sprite by Sanglorian. Overland sprite by Catch Challenger." Wiki footer: "Content is available under Creative Commons Attribution-ShareAlike unless otherwise noted." Tuxemon: "A sprite from Catch Challenger (CC BY), art director Jordan Brule."',
    credit='"Overworld sprite: Tuxemon Cool Dude, Catch Challenger (Jordan Brule), CC BY-SA 4.0"')
add('garius', 'R3_openmon_green_spiky', 'Openmon NPC: spiky green hair', openmon(OM1, 5),
    sets='walk only', source_short='Openmon NPC Sprites Set 1 (Screen Smith), CC0', **OM)
w, _ = recolor_stock('OBJ_EVENT_GFX_ACE_TRAINER_M', {
    1: (96, 40, 24), 3: (184, 88, 40), 2: (240, 152, 72),
    13: (56, 104, 168), 14: (112, 160, 224), 11: (32, 48, 88), 12: (64, 64, 80)})
add('garius', 'R4_stock_acetrainer_recolour', 'FALLBACK: stock Ace Trainer M, recoloured', w,
    sets='walk (stock member, every movement)', source_short='Platinum OBJ_EVENT_GFX_ACE_TRAINER_M palette swap (game asset, not free art)',
    url='repo: res/prebuilt/data/mmodel/mmodel (stock member 0x0B)', creator='Game Freak (stock Platinum)',
    licence='n/a: the game\'s own asset (owner-approved fallback)', lic_quote='n/a', credit='n/a')

# ---------------------------------------------------------------- Ruth
add('ruth', 'T1_openmon_purple_glasses', 'Openmon NPC: purple hair, white coat', openmon(OM2, 4),
    sets='walk only', source_short='Openmon NPC Sprites Set 1 (Screen Smith), CC0', **OM)
add('ruth', 'T2_openmon_green_hood', 'Openmon NPC: green hood girl', openmon(OM2, 3),
    sets='walk only', source_short='Openmon NPC Sprites Set 1 (Screen Smith), CC0', **OM)
add('ruth', 'T3_tuxemon_professor', 'Tuxemon "Professor" (lab coat), red-hair variant', tux('professor_fiery'),
    sets='walk only', source_short='Tuxemon, Professor sprite by Kurt Stine; CC BY-SA 4.0',
    url=TUX_URL + '/professor_fiery.png', creator='Kurt Stine (Qiangong2); hair colour variants by the Tuxemon team',
    licence='CC BY-SA 4.0  [FLAG: attribution + share-alike]',
    lic_quote='Tuxemon ATTRIBUTIONS.md: "\\"Professor Sprite\\" by Kurt Stine is licensed under CC-BY-SA 4.0"',
    credit='"Overworld sprite: Tuxemon Professor by Kurt Stine, CC BY-SA 4.0, https://github.com/Tuxemon/Tuxemon"')
w, _ = recolor_stock('OBJ_EVENT_GFX_SCIENTIST_F', {
    1: (72, 32, 24), 2: (152, 64, 40), 3: (208, 112, 64),
    9: (240, 232, 200), 12: (208, 192, 144), 10: (144, 112, 80), 11: (176, 144, 104), 13: (96, 72, 64)})
add('ruth', 'T4_stock_scientist_recolour', 'FALLBACK: stock Scientist F, recoloured', w,
    sets='walk (stock member, every movement)', source_short='Platinum OBJ_EVENT_GFX_SCIENTIST_F palette swap (game asset, not free art)',
    url='repo: res/prebuilt/data/mmodel/mmodel (stock member)', creator='Game Freak (stock Platinum)',
    licence='n/a: the game\'s own asset (owner-approved fallback)', lic_quote='n/a', credit='n/a')

json.dump([{'char': c.char, 'key': c.key, 'name': c.name, 'colors_in': c.orig_colors, 'colors_out': len(c.pal),
            'shift': [c.dx, c.dy], **{k: v for k, v in c.meta.items() if k != 'char_title'}} for c in CANDS],
          open(OUT2 / 'candidates.json', 'w'), indent=1)
print('kit char size', ksz)
