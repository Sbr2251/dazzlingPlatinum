"""Which of our battle trainer classes show BW2's animated trainer art instead of Platinum's.

THE REVERT SWITCH. This table is the only place that decides it:
- delete a row to put that class back on its Platinum art;
- empty the table (or set BW2_TRAINER_FRONTS to 0 in include/battle/battle_trainer_bw2.h) to put every
  class back. After editing the table, rerun `tools/bw2_trainers/build_bw2_trainers.py`.

Key: our class directory (res/trainers/classes/<key>, = TRAINER_CLASS_<KEY>).
Value: the BW2 front sprite directory in pokebw2's res/trainers/sprites/front/.

Only generic classes that are clearly the same character type are mapped. Story characters stay on our art
(gym leaders, Elite Four, Champion, Cyrus/galactic boss, Garius/rival, partners, Team Eclipse and Galactic,
the player), and so does every Sinnoh class Unova has no counterpart for.
"""

MAPPING = {
    "ace_trainer_female": "ace_trainer_f",
    "ace_trainer_male": "ace_trainer_m",
    "artist": "artist",
    "battle_girl": "battle_girl",
    "beauty": "beauty",
    "black_belt": "black_belt",
    "breeder_female": "pkmn_breeder_f",
    "breeder_male": "pkmn_breeder_m",
    "clown": "harlequin",
    "cyclist_female": "cyclist_f",
    "cyclist_male": "cyclist_m",
    "fisherman": "fisherman",
    "gentleman": "gentleman",
    "guitarist": "musician",
    "hiker": "hiker",
    "lady": "lady",
    "lass": "lass",
    "maid": "maid",
    "parasol_lady": "parasol_lady",
    "pokefan_female": "pokefan_f",
    "pokefan_male": "pokefan_m",
    "policeman": "policeman",
    "psychic_female": "psychic_f",
    "psychic_male": "psychic_m",
    "ranger_female": "pkmn_ranger_f",
    "ranger_male": "pkmn_ranger_m",
    "rich_boy": "rich_boy",
    "roughneck": "roughneck",
    "school_kid_female": "school_kid_f",
    "school_kid_male": "school_kid_m",
    "scientist": "scientist_m_52",
    "socialite": "socialite",
    "swimmer_female": "swimmer_f",
    "swimmer_male": "swimmer_m",
    "twins": "twins",
    "veteran": "veteran_m",
    "waiter": "waiter",
    "waitress": "waitress",
    "worker": "worker_26",
    "youngster": "youngster",
}
