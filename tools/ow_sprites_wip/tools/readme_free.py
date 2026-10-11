import json, sys
from pathlib import Path
OUT = Path('/tmp/a1r3/ow_sprites_free')
cands = json.load(open(OUT / 'candidates.json'))
rec = json.load(open(OUT / 'recommendations.json'))

NOTES = {
 'B1_openmon_teal_jacket': ('RECOMMENDED. Clean CC0, human-drawn, made for a Pokemon-style game, so the shading and outline match Gen 3/4 '
   'overworlds. Reads as a sporty trainer and looks nothing like Lucas. Fit: about 21 px tall against Lucas\'s 24 px, so he looks '
   'slightly small and young next to stock NPCs. Quantised to 15 colours; the loss is invisible at 1x. 3-frame walk.'),
 'B2_openmon_blue_hair': 'Same CC0 pack. Navy hair with a ponytail and a green jacket. A softer, older look than B1, and 12 colours.',
 'B3_tuxemon_adventurer': ('Tuxemon\'s own protagonist option, a cap-and-backpack trainer. Chibi proportions (big head, 16x20 px), '
   'about 3 px shorter than Lucas. Licence chain: Catch Challenger art, adapted for Tuxemon, published as CC BY / CC BY-SA. Share-alike '
   'means the edited sprite stays CC BY-SA.'),
 'B4_kit_boy': ('The only free candidate with RUN and BIKE sets (plus a swimming add-on by TechSkylander1518, Eevee Expo 373; it '
   'was not downloaded because the Mediafire link blocks scripted fetches). Built here from the kit layers: light base, navy jeans, '
   'red hoodie, black sports backpack, "boy 2" brown hair. Any combination works. Size matches Platinum exactly (18x25). FLAG: '
   'the author says the bodies were made "from scratch (well, and from the vanilla sprites)", so the base is derived from official '
   'sprites. The licence itself is explicit and allows edits. No surf-on-Pokemon or fishing frames.'),
 'G1_openmon_blue': ('RECOMMENDED. Clean CC0. A light-blue haired girl with a high ponytail, cheerful and readable, and not '
   'Dawn-like. Only 9 colours, so recolouring is easy. Same small-size note as B1.'),
 'G2_openmon_dark_hair': 'Same CC0 pack. Long dark hair, pink outfit. A quieter look, 14 colours.',
 'G3_tuxemon_heroine': ('Runner-up on looks: Tuxemon\'s protagonist option (blonde, hair clip), the most "main character" of the '
   'free set. Licence CC BY-SA 4.0 (attribution + share-alike), chibi proportions.'),
 'G4_kit_girl': ('Kit build with RUN and BIKE sets: light base, navy capris, orange open jacket, yellow bag, long red hair ("girl 1"). '
   'Same FLAG as B4: the bodies derive from vanilla sprites.'),
 'R1_openmon_red_spiky': ('RECOMMENDED. Clean CC0. Spiky maroon hair and a red shirt: hot-headed colours, and it reads apart from both '
   'Darren picks. The design is plain rather than cocky; a pixel edit to the brows or a jacket would push the "brash" read.'),
 'R1e_openmon_red_eclipse': ('RECOMMENDED for Arc 3: R1 hue-mapped by `eclipse()` in `tools/build_free.py`. The red shirt becomes Eclipse '
   'violet, the hair near-black slate, and the dark greys violet-black. CC0 allows this edit. Adding the Eclipse ring on the chest is a few pixels.'),
 'R2_tuxemon_cooldude': ('Runner-up: the most "brash" silhouette (spiky hair, shades, jacket). Licence chain: Catch Challenger art, '
   'published by Tuxemon as CC BY / CC BY-SA. Weaker than the CC0 picks, because the original Catch Challenger datapack repo states '
   'no licence of its own. Chibi proportions.'),
 'R3_openmon_green_spiky': 'Same CC0 pack. Wild green hair; reads energetic but young (kid proportions).',
 'R4_stock_acetrainer_recolour': ('FALLBACK (the owner-approved option): the stock Platinum Ace Trainer M with copper hair and a blue jacket. '
   'Native size and every stock movement, but it is the game\'s own asset and the silhouette is a common trainer class.'),
 'T1_openmon_purple_glasses': ('RECOMMENDED. Clean CC0. Glasses, a white coat with a red tie and wild purple hair: "lab assistant who '
   'builds her own gadgets" at a glance, and nothing like Dawn. The hair spills past the 18 px source pitch, so frames were cut at the '
   'midpoints between neighbouring frames; at most 1 px of strand tips is lost. 24 colours quantised to 15.'),
 'T2_openmon_green_hood': 'Runner-up. Same CC0 pack: a green hoodie, outdoorsy field-researcher look, 9 colours.',
 'T3_tuxemon_professor': ('Tuxemon "Professor" (lab coat), red-hair variant. CC BY-SA 4.0 with a clean per-file credit (Kurt Stine). '
   'Reads young and male-ish; chibi proportions.'),
 'T4_stock_scientist_recolour': ('FALLBACK: the stock Scientist F with copper hair and a canvas work coat. Native size, zero format risk, '
   'but it is the game\'s own asset and shares a silhouette with the lab scientists.'),
}
TITLES = {'darren_boy': 'Darren (boy)', 'darren_girl': 'Darren (girl)', 'garius': 'Garius (rival)', 'ruth': "Ruth (Rowan's assistant)"}
for char, title in TITLES.items():
    L = [f'# {title}: free-licence overworld candidates', '',
         f'Overview: `{char}_overview.png`. Per candidate: `<key>_sheet.png` (4 facings x stand/step A/stand/step B at 4x, '
         'plus extra sets), `<key>_walk.gif`, `<key>_platinum_walk.png` (128x128, 4-bit, 16 colours, index 0 transparent, '
         'BGR555-snapped), and for kit builds `<key>_run.gif` and `<key>_platinum_walk_run.png` (128x256, walk + run).', '']
    for c in [c for c in cands if c['char'] == char]:
        star = rec.get(char, {}).get(c['key'])
        L += [f"## {c['key']}: {c['name']}" + (f'  **[{star}]**' if star else ''), '',
              f"- Source: {c['url']}" + (f" (page: {c['page']})" if c.get('page') else ''),
              f"- Creator: {c['creator']}",
              f"- Licence: {c['licence']}",
              f"- Licence text (quoted from where it is published): {c['lic_quote']}",
              f"- Credit line: {c['credit']}",
              f"- Sets: {c['sets']}",
              f"- Colours: {c['colors_in']} in source -> {c['colors_out']} + transparent",
              f"- Notes: {NOTES.get(c['key'], '')}", '']
    (OUT / char / 'README.md').write_text('\n'.join(L))
print('ok')
