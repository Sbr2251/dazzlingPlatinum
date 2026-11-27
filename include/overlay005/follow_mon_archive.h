#ifndef POKEPLATINUM_FOLLOW_MON_ARCHIVE_H
#define POKEPLATINUM_FOLLOW_MON_ARCHIVE_H

#include <nitro/types.h>

#include "constants/forms.h"
#include "constants/species.h"
#include "generated/genders.h"

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Member indices for follow_mon.narc (built at build/package time by
 * tools/follow_mon/build_follow_mon.py from a user-supplied HGSS ROM plus
 * Dazzling Platinum's 43 Gen 5 species sprites).
 *
 * BTX0 palette layout (applies to BOTH HGSS sprites 0..565 and Gen 5 sprites 741..783):
 *   - Every follower BTX0 holds 8 4bpp (GX_TEXFMT_PLTT16, color 0 transparent) frames:
 *       frames 0,1 = North (up)
 *       frames 2,3 = South (down)
 *       frames 4,5 = West  (left)
 *       frames 6,7 = East  (right)
 *   - Every follower BTX0 holds TWO 16-color RGB555 palettes INSIDE the SAME BTX0:
 *       palette index 0 ("tsure_poke0", byte offset 0x00): normal colors
 *       palette index 1 ("tsure_poke1", byte offset 0x20): shiny colors
 *   - Shiny Pokemon therefore use the SAME NARC member index as non-shiny Pokemon;
 *     switch the billboard's palette index to FOLLOW_MON_ARC_PALETTE_SHINY (1) when
 *     isShiny is TRUE (see FollowMonArchive_PaletteIndex).
 */

#define FOLLOW_MON_ARC_SPRITES                   0
#define FOLLOW_MON_ARC_HGSS_SPRITE_COUNT         566
#define FOLLOW_MON_ARC_TP_PARAM                  566
#define FOLLOW_MON_ARC_SEQUENCE                  567
#define FOLLOW_MON_ARC_BALL_MODEL                568
#define FOLLOW_MON_ARC_BURST_MODEL               569
#define FOLLOW_MON_ARC_BURST_ANIM                570
#define FOLLOW_MON_ARC_EMOTE_MODEL               571
#define FOLLOW_MON_ARC_EMOTE_SEQUENCE            572
#define FOLLOW_MON_ARC_EMOTE_TEXTURE             573
#define FOLLOW_MON_ARC_EMOTE_TEXTURES            574
#define FOLLOW_MON_ARC_EMOTE_KINDS               14
#define FOLLOW_MON_ARC_EMOTE_SEQUENCES           588
#define FOLLOW_MON_ARC_RULES_GLOBAL              602
#define FOLLOW_MON_ARC_RULES_LOCATION            603
#define FOLLOW_MON_ARC_LOCATION_COUNT            126
#define FOLLOW_MON_ARC_SCRIPTS                   729
#define FOLLOW_MON_ARC_MOVEMENTS                 730
#define FOLLOW_MON_ARC_SPECIES_ATTR              731
#define FOLLOW_MON_ARC_TEXT                      732
#define FOLLOW_MON_ARC_GIFT_TEXT                 733
#define FOLLOW_MON_ARC_FLY_JUMP_MODEL            734
#define FOLLOW_MON_ARC_FLY_JUMP_MATERIAL_ANIM    735
#define FOLLOW_MON_ARC_FLY_JUMP_JOINT_ANIM       736
#define FOLLOW_MON_ARC_SWEET_SCENT_MODEL         737
#define FOLLOW_MON_ARC_SWEET_SCENT_MATERIAL_ANIM 738
#define FOLLOW_MON_ARC_SWEET_SCENT_TEXTURE_ANIM  739
#define FOLLOW_MON_ARC_SWEET_SCENT_JOINT_ANIM    740
#define FOLLOW_MON_ARC_HGSS_MEMBER_COUNT         741
#define FOLLOW_MON_ARC_GEN5_SPRITES              741
#define FOLLOW_MON_ARC_GEN5_SPRITE_COUNT         43
#define FOLLOW_MON_ARC_TOTAL_SPRITE_COUNT        609
#define FOLLOW_MON_ARC_MEMBER_COUNT              784

/* Palette index inside each follower BTX0 (normal = 0, shiny = 1). */
#define FOLLOW_MON_ARC_PALETTE_NORMAL            0
#define FOLLOW_MON_ARC_PALETTE_SHINY             1

/*
 * Return the BTX0 palette index (0 = normal "tsure_poke0", 1 = shiny "tsure_poke1")
 * to bind for a follower sprite.
 */
static inline u8 FollowMonArchive_PaletteIndex(BOOL isShiny)
{
    return isShiny ? FOLLOW_MON_ARC_PALETTE_SHINY : FOLLOW_MON_ARC_PALETTE_NORMAL;
}

/*
 * Map (species, form, gender, isShiny) to its BTX0 member index inside follow_mon.narc:
 *   - Gen 1..4 (SPECIES_BULBASAUR..SPECIES_ARCEUS): returns 0..565
 *   - Gen 5 custom species (43 species past SPECIES_ARCEUS): returns 741..783
 *   - Invalid / Egg species: returns -1
 *
 * Note: Shiny uses palette index 1 ("tsure_poke1") INSIDE the same BTX0, so isShiny
 * does not alter the returned archive member index.
 */
static inline int FollowMonArchive_SpriteMemberIndex(u16 species, u8 form, u8 gender, BOOL isShiny)
{
    (void)isShiny;

    if (species == SPECIES_NONE || species == SPECIES_EGG || species == SPECIES_BAD_EGG) {
        return -1;
    }

    if (species <= SPECIES_ARCEUS) {
        int idx = (int)species - 1;

        /* Cumulative extra slots for preceding HGSS multi-slot species (73 total). */
        if (species > SPECIES_VENUSAUR) {
            idx += 1;
        }
        if (species > SPECIES_PIKACHU) {
            idx += 1;
        }
        if (species > SPECIES_MEGANIUM) {
            idx += 1;
        }
        if (species > SPECIES_PICHU) {
            idx += 1;
        }
        if (species > SPECIES_UNOWN) {
            idx += UNOWN_FORM_COUNT - 1;
        }
        if (species > SPECIES_WOBBUFFET) {
            idx += 1;
        }
        if (species > SPECIES_STEELIX) {
            idx += 1;
        }
        if (species > SPECIES_HERACROSS) {
            idx += 1;
        }
        if (species > SPECIES_DEOXYS) {
            idx += DEOXYS_FORM_COUNT - 1;
        }
        if (species > SPECIES_BURMY) {
            idx += BURMY_FORM_COUNT - 1;
        }
        if (species > SPECIES_WORMADAM) {
            idx += WORMADAM_FORM_COUNT - 1;
        }
        if (species > SPECIES_COMBEE) {
            idx += 1;
        }
        if (species > SPECIES_SHELLOS) {
            idx += SHELLOS_FORM_COUNT - 1;
        }
        if (species > SPECIES_GASTRODON) {
            idx += GASTRODON_FORM_COUNT - 1;
        }
        if (species > SPECIES_GIBLE) {
            idx += 1;
        }
        if (species > SPECIES_GABITE) {
            idx += 1;
        }
        if (species > SPECIES_GARCHOMP) {
            idx += 1;
        }
        if (species > SPECIES_HIPPOPOTAS) {
            idx += 1;
        }
        if (species > SPECIES_HIPPOWDON) {
            idx += 1;
        }
        if (species > SPECIES_ROTOM) {
            idx += ROTOM_FORM_COUNT - 1;
        }
        if (species > SPECIES_GIRATINA) {
            idx += GIRATINA_FORM_COUNT - 1;
        }
        if (species > SPECIES_SHAYMIN) {
            idx += SHAYMIN_FORM_COUNT - 1;
        }

        /* Within-species gender (+1 for female) or form offset. */
        switch (species) {
        case SPECIES_VENUSAUR:
        case SPECIES_PIKACHU:
        case SPECIES_MEGANIUM:
        case SPECIES_WOBBUFFET:
        case SPECIES_STEELIX:
        case SPECIES_HERACROSS:
        case SPECIES_COMBEE:
        case SPECIES_GIBLE:
        case SPECIES_GABITE:
        case SPECIES_GARCHOMP:
        case SPECIES_HIPPOPOTAS:
        case SPECIES_HIPPOWDON:
            if (gender == GENDER_FEMALE) {
                idx += 1;
            }
            break;
        case SPECIES_PICHU:
            if (form == 1) {
                idx += 1;
            }
            break;
        case SPECIES_UNOWN:
            if (form < UNOWN_FORM_COUNT) {
                idx += form;
            }
            break;
        case SPECIES_DEOXYS:
            if (form < DEOXYS_FORM_COUNT) {
                idx += form;
            }
            break;
        case SPECIES_BURMY:
            if (form < BURMY_FORM_COUNT) {
                idx += form;
            }
            break;
        case SPECIES_WORMADAM:
            if (form < WORMADAM_FORM_COUNT) {
                idx += form;
            }
            break;
        case SPECIES_SHELLOS:
            if (form < SHELLOS_FORM_COUNT) {
                idx += form;
            }
            break;
        case SPECIES_GASTRODON:
            if (form < GASTRODON_FORM_COUNT) {
                idx += form;
            }
            break;
        case SPECIES_ROTOM:
            if (form < ROTOM_FORM_COUNT) {
                idx += form;
            }
            break;
        case SPECIES_GIRATINA:
            if (form < GIRATINA_FORM_COUNT) {
                idx += form;
            }
            break;
        case SPECIES_SHAYMIN:
            if (form < SHAYMIN_FORM_COUNT) {
                idx += form;
            }
            break;
        case SPECIES_ARCEUS:
            if (form < ARCEUS_FORM_COUNT) {
                idx += form;
            }
            break;
        default:
            break;
        }

        return FOLLOW_MON_ARC_SPRITES + idx;
    }

    /* Dazzling Platinum's 43 custom Gen 5 species (SPECIES_DEINO..SPECIES_CHANDELURE). */
    {
        int gen5Idx = (int)(species - SPECIES_ARCEUS - 1);
        if (gen5Idx >= 0 && gen5Idx < FOLLOW_MON_ARC_GEN5_SPRITE_COUNT) {
            return FOLLOW_MON_ARC_GEN5_SPRITES + gen5Idx;
        }
    }

    return -1;
}

/*
 * Map a sprite NARC member index (0..565 or 741..783) to its 4-byte record index
 * inside FOLLOW_MON_ARC_TP_PARAM (0..565 for HGSS, 566..608 for Gen 5; -1 if invalid).
 */
static inline int FollowMonArchive_TpParamIndex(int spriteMemberIdx)
{
    if (spriteMemberIdx >= FOLLOW_MON_ARC_SPRITES
        && spriteMemberIdx < FOLLOW_MON_ARC_SPRITES + FOLLOW_MON_ARC_HGSS_SPRITE_COUNT) {
        return spriteMemberIdx - FOLLOW_MON_ARC_SPRITES;
    }
    if (spriteMemberIdx >= FOLLOW_MON_ARC_GEN5_SPRITES
        && spriteMemberIdx < FOLLOW_MON_ARC_GEN5_SPRITES + FOLLOW_MON_ARC_GEN5_SPRITE_COUNT) {
        return FOLLOW_MON_ARC_HGSS_SPRITE_COUNT + (spriteMemberIdx - FOLLOW_MON_ARC_GEN5_SPRITES);
    }
    return -1;
}

/*
 * Return TRUE for large (64x64 BTX0) follower species in HGSS (31 sprites total):
 * Steelix (2), Lugia (1), Ho-Oh (1), Wailord (1), Kyogre (1), Groudon (1),
 * Rayquaza (1), Dialga (1), Palkia (1), Regigigas (1), Giratina (2), Arceus (18).
 */
static inline BOOL FollowMonArchive_IsLargeSpecies(u16 species, u8 form)
{
    (void)form;

    switch (species) {
    case SPECIES_STEELIX:
    case SPECIES_LUGIA:
    case SPECIES_HO_OH:
    case SPECIES_WAILORD:
    case SPECIES_KYOGRE:
    case SPECIES_GROUDON:
    case SPECIES_RAYQUAZA:
    case SPECIES_DIALGA:
    case SPECIES_PALKIA:
    case SPECIES_REGIGIGAS:
    case SPECIES_GIRATINA:
    case SPECIES_ARCEUS:
        return TRUE;
    default:
        return FALSE;
    }
}

#ifdef __cplusplus
}
#endif

#endif // POKEPLATINUM_FOLLOW_MON_ARCHIVE_H
