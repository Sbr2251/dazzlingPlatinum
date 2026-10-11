#include "macros/scrcmd.inc"
#include "res/text/bank/eterna_city.h"
#include "res/text/bank/special_met_location_names.h"
#include "res/field/events/events_eterna_city.h"


    ScriptEntry _01BF
    ScriptEntry _04FC
    ScriptEntry _050F
    ScriptEntry _0522
    ScriptEntry _00BF
    ScriptEntry _00E5
    ScriptEntry _00D2
    ScriptEntry _010E
    ScriptEntry _0535
    ScriptEntry _0548
    ScriptEntry _055B
    ScriptEntry _0137
    ScriptEntry _014E
    ScriptEntry _0163
    ScriptEntry _017A
    ScriptEntry _0191
    ScriptEntry _01A8
    ScriptEntry _056E
    ScriptEntry _057F
    ScriptEntry _05B0
    ScriptEntry _0072
    ScriptEntry _0770
    ScriptEntry _07BA
    ScriptEntry _08FC
    ScriptEntry _0954
    ScriptEntry _0D00
    ScriptEntry _0FDC
    ScriptEntry _0EB4
    ScriptEntry EternaCity_Arc2RuthTalk
    ScriptEntry EternaCity_Arc2CyrusTalk
    ScriptEntry EternaCity_Arc2GariusScene
    ScriptEntry EternaCity_Arc2HavenArrival
    ScriptEntry EternaCity_Arc2GardeniaHavenTalk
    ScriptEntryEnd

// Dazzling Platinum Arc 2, workstream s-eterna (screenplay 2.11-2.12). VAR_ARC2_PROGRESS block 30-39:
//   29 (read) Vespiquen calmed, arrived from Eterna Forest
//   31 Forest Badge (scripts_eterna_city_gym.s) -> Garius waits outside the Gym (frame trigger)
//   32 Garius battle done (whatever the result)
//   33 Gardenia asked for help; the party stands at the Haven trees
//   34 inside the Haven, Looker met (scripts_team_galactic_eterna_building_1f.s)
//   35 Haven shut (4F), then the 2.13 cutaway (s-cutaways) sets 39 and returns here
// Flags (s-eterna allocation 0x093E-0x0941, already named by R0):
//   FLAG_ARC2_ETERNA_A (0x093E)  Haven caretakers beaten (3F double battle)
//   FLAG_ARC2_ETERNA_B (0x093F)  Haven kennel scene seen (2F)
//   FLAG_ARC2_ETERNA_C (0x0940)  Haven manifests read (3F)
//   FLAG_ARC2_ETERNA_D (0x0941)  spare
// Map-local hide flags (cleared on every map change, recomputed in EternaCity_Arc2SetObjects):
//   0x30 Ruth, 0x31 the stock Galactic grunts (always hidden), 0x32 Cyrus, 0x33 Garius, 0x34 Gardenia at the Haven.
// Stock content removed here: the Barry/Cyrus statue scene (coord, VAR_UNK_0x407A 0) and Cynthia's HM01 give
// (coords, VAR_UNK_0x407A 1; plan D11). VAR_UNK_0x407A now stays 0, so Cynthia's stock Egg scene never runs.


_0072:
    Call EternaCity_Arc2SetObjects
    CallIfEq VAR_UNK_0x407A, 4, _00B5
    CheckItem ITEM_BICYCLE, 1, VAR_MAP_LOCAL_0
    GoToIfEq VAR_MAP_LOCAL_0, 1, _0096
    End

_0096:
    CheckItem ITEM_EXPLORER_KIT, 1, VAR_MAP_LOCAL_0
    GoToIfEq VAR_MAP_LOCAL_0, 1, _00AD
    End

_00AD:
    SetVar VAR_UNK_0x4114, 0
    End

_00B5:
    SetObjectEventPos 12, 0x133, 0x21D
    Return

_00BF:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 25
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_00D2:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 26
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_00E5:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfSet FLAG_UNK_0x0081, _0103
    Message 21
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0103:
    Message 22
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_010E:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfSet FLAG_UNK_0x0081, _012C
    Message 23
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_012C:
    Message 24
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0137:
    ShowMapSign 36
    End

_014E:
    ShowScrollingSign 37
    End

_0163:
    ShowLandmarkSign 38
    End

_017A:
    GoToIfLt VAR_ARC2_PROGRESS, 29, EternaCity_HavenSignPlain
    GoToIfGe VAR_ARC2_PROGRESS, 35, EternaCity_HavenSignPlain
    CheckItem ITEM_RESONATOR, 1, VAR_RESULT
    GoToIfEq VAR_RESULT, FALSE, EternaCity_HavenSignPlain
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message 39
    WaitABXPadPress
    Message EternaCity_Text_Arc2HavenBuzz
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

EternaCity_HavenSignPlain:
    ShowLandmarkSign 39
    End

_0191:
    ShowLandmarkSign 40
    End

_01A8:
    ShowLandmarkSign 41
    End

_01BF:
    // Stock: Cynthia gives HM01 at the Galactic building trees. Removed for Arc 2 (plan D11): field moves are
    // Resonator-only. The entry slot stays so the script numbering doesn't move.
    End

_04FC:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 18
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_050F:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 19
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0522:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 20
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0535:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 27
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_0548:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 28
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_055B:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 29
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_056E:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    Message 42
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_057F:
    GoToIfSet FLAG_EXPLORER_KIT_RECEIVED, _059D
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 31
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_059D:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message 32
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

_05B0:
    LockAll
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8004, 0x12F, _0657
    CallIfEq VAR_0x8004, 0x130, _0663
    CallIfEq VAR_0x8004, 0x131, _066F
    CallIfEq VAR_0x8004, 0x132, _067B
    CallIfEq VAR_0x8004, 0x133, _0687
    ApplyMovement LOCALID_PLAYER, _0760
    WaitMovement
    Message 30
    CloseMessage
    CallIfEq VAR_0x8004, 0x12F, _0693
    CallIfEq VAR_0x8004, 0x130, _0695
    CallIfEq VAR_0x8004, 0x131, _06A1
    CallIfEq VAR_0x8004, 0x132, _06AD
    CallIfEq VAR_0x8004, 0x133, _06B9
    ApplyMovement LOCALID_PLAYER, _0768
    WaitMovement
    ReleaseAll
    End

_0657:
    ApplyMovement 28, _06C8
    WaitMovement
    Return

_0663:
    ApplyMovement 28, _06D8
    WaitMovement
    Return

_066F:
    ApplyMovement 28, _06EC
    WaitMovement
    Return

_067B:
    ApplyMovement 28, _0700
    WaitMovement
    Return

_0687:
    ApplyMovement 28, _0714
    WaitMovement
    Return

_0693:
    Return

_0695:
    ApplyMovement 28, _0730
    WaitMovement
    Return

_06A1:
    ApplyMovement 28, _073C
    WaitMovement
    Return

_06AD:
    ApplyMovement 28, _0748
    WaitMovement
    Return

_06B9:
    ApplyMovement 28, _0754
    WaitMovement
    Return

    .balign 4, 0
_06C8:
    WalkOnSpotFastEast
    EmoteExclamationMark
    Delay4
    EndMovement

    .balign 4, 0
_06D8:
    WalkOnSpotFastEast
    EmoteExclamationMark
    Delay4
    WalkNormalEast
    EndMovement

    .balign 4, 0
_06EC:
    WalkOnSpotFastEast
    EmoteExclamationMark
    Delay4
    WalkNormalEast 2
    EndMovement

    .balign 4, 0
_0700:
    WalkOnSpotFastEast
    EmoteExclamationMark
    Delay4
    WalkNormalEast 3
    EndMovement

    .balign 4, 0
_0714:
    WalkOnSpotFastEast
    EmoteExclamationMark
    Delay4
    WalkNormalEast 4
    EndMovement

EternaCity_UnusedMovement:
    WalkOnSpotFastEast
    EndMovement

    .balign 4, 0
_0730:
    WalkNormalWest
    WalkOnSpotFastEast
    EndMovement

    .balign 4, 0
_073C:
    WalkNormalWest 2
    WalkOnSpotFastEast
    EndMovement

    .balign 4, 0
_0748:
    WalkNormalWest 3
    WalkOnSpotFastEast
    EndMovement

    .balign 4, 0
_0754:
    WalkNormalWest 4
    WalkOnSpotFastEast
    EndMovement

    .balign 4, 0
_0760:
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_0768:
    WalkNormalNorth
    EndMovement

_0770:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfUnset FLAG_UNK_0x0082, _07A5
    GoToIfGe VAR_UNK_0x408C, 1, _07A5
    Message 34
    WaitABXPadPress
    CloseMessage
    ApplyMovement 30, _0898
    WaitMovement
    ReleaseAll
    End

_07A5:
    Message 35
    WaitABXPadPress
    CloseMessage
    ApplyMovement 30, _0898
    WaitMovement
    ReleaseAll
    End

_07BA:
    LockAll
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    CallIfEq VAR_0x8005, 0x214, _0823
    CallIfEq VAR_0x8005, 0x215, _082F
    CallIfEq VAR_0x8005, 0x216, _083B
    ApplyMovement LOCALID_PLAYER, _0890
    WaitMovement
    Message 33
    CloseMessage
    CallIfEq VAR_0x8005, 0x214, _0847
    CallIfEq VAR_0x8005, 0x215, _085B
    CallIfEq VAR_0x8005, 0x216, _086F
    ReleaseAll
    End

_0823:
    ApplyMovement 30, _08A0
    WaitMovement
    Return

_082F:
    ApplyMovement 30, _08AC
    WaitMovement
    Return

_083B:
    ApplyMovement 30, _08BC
    WaitMovement
    Return

_0847:
    ApplyMovement 30, _08CC
    ApplyMovement LOCALID_PLAYER, _0884
    WaitMovement
    Return

_085B:
    ApplyMovement 30, _08DC
    ApplyMovement LOCALID_PLAYER, _0884
    WaitMovement
    Return

_086F:
    ApplyMovement 30, _08EC
    ApplyMovement LOCALID_PLAYER, _0884
    WaitMovement
    Return

    .balign 4, 0
_0884:
    WalkNormalEast
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_0890:
    FaceNorth
    EndMovement

    .balign 4, 0
_0898:
    FaceSouth
    EndMovement

    .balign 4, 0
_08A0:
    FaceSouth
    EmoteExclamationMark
    EndMovement

    .balign 4, 0
_08AC:
    FaceSouth
    EmoteExclamationMark
    WalkNormalSouth
    EndMovement

    .balign 4, 0
_08BC:
    FaceSouth
    EmoteExclamationMark
    WalkNormalSouth 2
    EndMovement

    .balign 4, 0
_08CC:
    WalkNormalSouth
    WalkNormalNorth
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_08DC:
    WalkNormalSouth
    WalkNormalNorth 2
    WalkOnSpotNormalSouth
    EndMovement

    .balign 4, 0
_08EC:
    WalkNormalSouth
    WalkNormalNorth 3
    WalkOnSpotNormalSouth
    EndMovement

_08FC:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    BufferRivalName 0
    Message 17
    CloseMessage
    ApplyMovement 31, _0944
    WaitMovement
    LoadDoorAnimation 9, 17, 24, 18, ANIMATION_TAG_DOOR_1
    PlayDoorOpenAnimation ANIMATION_TAG_DOOR_1
    WaitForAnimation ANIMATION_TAG_DOOR_1
    ApplyMovement 31, _094C
    WaitMovement
    RemoveObject 31
    PlayDoorCloseAnimation ANIMATION_TAG_DOOR_1
    WaitForAnimation ANIMATION_TAG_DOOR_1
    UnloadAnimation ANIMATION_TAG_DOOR_1
    ReleaseAll
    End

    .balign 4, 0
_0944:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
_094C:
    WalkNormalNorth
    EndMovement

_0954:
    // Stock: Barry runs in and Galactic boss Cyrus speaks at the statue. Removed for Arc 2 (Cyrus travels with
    // the player). Its coord event is gone; the entry slot stays.
    End

_0D00:
    LockAll
    SetObjectEventDir 12, DIR_EAST
    SetObjectEventMovementType 12, MOVEMENT_TYPE_LOOK_EAST
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 0x21C, _0D64
    GoToIfEq VAR_0x8005, 0x21D, _0D7A
    GoToIfEq VAR_0x8005, 0x21E, _0D90
    GoToIfEq VAR_0x8005, 0x21F, _0DA6
    GoToIfEq VAR_0x8005, 0x220, _0DBC
    GoToIfEq VAR_0x8005, 0x221, _0DD2
    End

_0D64:
    SetObjectEventPos 12, 0x130, 0x224
    Call _0DE8
    GoTo _0DF6
    End

_0D7A:
    SetObjectEventPos 12, 0x130, 0x225
    Call _0DE8
    GoTo _0DF6
    End

_0D90:
    SetObjectEventPos 12, 0x130, 0x226
    Call _0DE8
    GoTo _0DF6
    End

_0DA6:
    SetObjectEventPos 12, 0x130, 0x227
    Call _0DE8
    GoTo _0DF6
    End

_0DBC:
    SetObjectEventPos 12, 0x130, 0x228
    Call _0DE8
    GoTo _0DF6
    End

_0DD2:
    SetObjectEventPos 12, 0x130, 0x229
    Call _0DE8
    GoTo _0DF6
    End

_0DE8:
    ClearFlag FLAG_UNK_0x0180
    AddObject 12
    LockObject 12
    Return

_0DF6:
    ApplyMovement 12, _0E88
    WaitMovement
    ApplyMovement LOCALID_PLAYER, _0EAC
    WaitMovement
    Message 9
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_NO, _0E75
    GetPartyCount VAR_RESULT
    GoToIfGe VAR_RESULT, 6, _0E67
    Call _0E4B
    ApplyMovement 12, _0EA0
    WaitMovement
    RemoveObject 12
    GoTo _0E83
    End

_0E4B:
    PlaySound SEQ_FANFA4
    WaitSound
    Message 10
    Message 16
    CloseMessage
    GiveEgg SPECIES_TOGEPI, SPECIAL_METLOC_NAME_CYNTHIA
    SetVar VAR_UNK_0x407A, 5
    Return

_0E67:
    Call _0FBE
    GoTo _0E83
    End

_0E75:
    Call _0FCD
    GoTo _0E83
    End

_0E83:
    ReleaseAll
    End

    .balign 4, 0
_0E88:
    WalkNormalNorth 3
    EmoteExclamationMark
    WalkNormalNorth 5
    WalkNormalEast 2
    WalkNormalEast
    EndMovement

    .balign 4, 0
_0EA0:
    WalkNormalWest 3
    WalkNormalSouth 9
    EndMovement

    .balign 4, 0
_0EAC:
    WalkOnSpotNormalWest
    EndMovement

_0EB4:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfEq VAR_UNK_0x407A, 4, _0ECD
    ReleaseAll
    End

_0ECD:
    Message 14
    ShowYesNoMenu VAR_RESULT
    GoToIfEq VAR_RESULT, MENU_NO, _0FAC
    GetPartyCount VAR_RESULT
    GoToIfGe VAR_RESULT, 6, _0F9E
    Call _0E4B
    GetPlayerDir VAR_RESULT
    GoToIfEq VAR_RESULT, 0, _0F32
    GoToIfEq VAR_RESULT, 1, _0F4C
    GoToIfEq VAR_RESULT, 2, _0F66
    GoToIfEq VAR_RESULT, 3, _0F78
    End

_0F32:
    ApplyMovement 12, _10BC
    ApplyMovement LOCALID_PLAYER, _10E0
    WaitMovement
    GoTo _0F92
    End

_0F4C:
    ApplyMovement 12, _10BC
    ApplyMovement LOCALID_PLAYER, _10E0
    WaitMovement
    GoTo _0F92
    End

_0F66:
    ApplyMovement 12, _10BC
    WaitMovement
    GoTo _0F92
    End

_0F78:
    ApplyMovement 12, _10C8
    ApplyMovement LOCALID_PLAYER, _10EC
    WaitMovement
    GoTo _0F92
    End

_0F92:
    RemoveObject 12
    GoTo _0FBA
    End

_0F9E:
    Call _0FBE
    GoTo _0FBA
    End

_0FAC:
    Call _0FCD
    GoTo _0FBA
    End

_0FBA:
    ReleaseAll
    End

_0FBE:
    SetVar VAR_UNK_0x407A, 4
    Message 11
    WaitABXPadPress
    CloseMessage
    Return

_0FCD:
    Message 12
    WaitABXPadPress
    CloseMessage
    SetVar VAR_UNK_0x407A, 4
    Return

_0FDC:
    LockAll
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfEq VAR_0x8005, 0x21C, _1034
    GoToIfEq VAR_0x8005, 0x21D, _1046
    GoToIfEq VAR_0x8005, 0x21E, _1058
    GoToIfEq VAR_0x8005, 0x21F, _106A
    GoToIfEq VAR_0x8005, 0x220, _107C
    GoToIfEq VAR_0x8005, 0x221, _108E
    End

_1034:
    ApplyMovement 12, _10B4
    WaitMovement
    GoTo _10A0
    End

_1046:
    ApplyMovement 12, _10B4
    WaitMovement
    GoTo _10A0
    End

_1058:
    ApplyMovement 12, _10B4
    WaitMovement
    GoTo _10A0
    End

_106A:
    ApplyMovement 12, _10B4
    WaitMovement
    GoTo _10A0
    End

_107C:
    ApplyMovement 12, _10B4
    WaitMovement
    GoTo _10A0
    End

_108E:
    ApplyMovement 12, _10B4
    WaitMovement
    GoTo _10A0
    End

_10A0:
    Message 13
    CloseMessage
    ApplyMovement LOCALID_PLAYER, _10D8
    WaitMovement
    ReleaseAll
    End

    .balign 4, 0
_10B4:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
_10BC:
    WalkNormalWest 3
    WalkNormalSouth 9
    EndMovement

    .balign 4, 0
_10C8:
    WalkNormalSouth
    WalkNormalWest 3
    WalkNormalSouth 8
    EndMovement

    .balign 4, 0
_10D8:
    WalkNormalWest
    EndMovement

    .balign 4, 0
_10E0:
    Delay8
    WalkOnSpotNormalWest
    EndMovement

    .balign 4, 0
_10EC:
    Delay8 2
    Delay4
    WalkOnSpotNormalWest
    EndMovement

// ---------------------------------------------------------------------------------------------------------------
// Dazzling Platinum Arc 2 (s-eterna): object placement per VAR_ARC2_PROGRESS. Called at the top of OnTransition.
// ---------------------------------------------------------------------------------------------------------------
EternaCity_Arc2SetObjects:
    SetVar VAR_OBJ_GFX_ID_0, OBJ_EVENT_GFX_DP_PLAYER_F /* Ruth placeholder (Arc 1 D1) */
    SetFlag FLAG_UNK_0x0030
    SetFlag FLAG_UNK_0x0031
    SetFlag FLAG_UNK_0x0032
    SetFlag FLAG_UNK_0x0033
    SetFlag FLAG_UNK_0x0034
    GoToIfLt VAR_ARC2_PROGRESS, 29, EternaCity_Arc2Return
    // From 34 on, the middle Haven tree (305,521) stays cut, so leaving the Haven never shuts the player in.
    CallIfGe VAR_ARC2_PROGRESS, 34, EternaCity_Arc2KeepHavenTreeCut
    GoToIfGe VAR_ARC2_PROGRESS, 34, EternaCity_Arc2SetObjectsHaven
    GoToIfEq VAR_ARC2_PROGRESS, 33, EternaCity_Arc2SetObjectsTrees
    // 29-32: Ruth and Cyrus wait by the Gym; Garius is there at 31
    ClearFlag FLAG_UNK_0x0030
    ClearFlag FLAG_UNK_0x0032
    CallIfEq VAR_ARC2_PROGRESS, 31, EternaCity_Arc2ShowGarius
    Return

EternaCity_Arc2KeepHavenTreeCut:
    SetFlag FLAG_UNK_0x0021
    Return

EternaCity_Arc2ShowGarius:
    ClearFlag FLAG_UNK_0x0033
    Return

// 33: Gardenia and Ruth by the Haven trees, Cyrus a little apart. The arrival line runs from the frame table.
EternaCity_Arc2SetObjectsTrees:
    ClearFlag FLAG_UNK_0x0030
    ClearFlag FLAG_UNK_0x0032
    ClearFlag FLAG_UNK_0x0034
    SetObjectEventPos ETERNA_CITY_RUTH, 306, 523
    SetObjectEventDir ETERNA_CITY_RUTH, DIR_NORTH
    SetObjectEventMovementType ETERNA_CITY_RUTH, MOVEMENT_TYPE_LOOK_NORTH
    SetObjectEventPos ETERNA_CITY_CYRUS, 308, 522
    SetObjectEventDir ETERNA_CITY_CYRUS, DIR_WEST
    SetObjectEventMovementType ETERNA_CITY_CYRUS, MOVEMENT_TYPE_LOOK_WEST
    SetVar VAR_MAP_LOCAL_2, 1
    Return

// 34: Gardenia and Ruth are inside; Cyrus waits outside by the trees. 35+: the party has moved on.
EternaCity_Arc2SetObjectsHaven:
    GoToIfGe VAR_ARC2_PROGRESS, 35, EternaCity_Arc2Return
    ClearFlag FLAG_UNK_0x0032
    SetObjectEventPos ETERNA_CITY_CYRUS, 308, 522
    SetObjectEventDir ETERNA_CITY_CYRUS, DIR_WEST
    SetObjectEventMovementType ETERNA_CITY_CYRUS, MOVEMENT_TYPE_LOOK_WEST
EternaCity_Arc2Return:
    Return

EternaCity_Arc2RuthTalk:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfGe VAR_ARC2_PROGRESS, 33, EternaCity_Arc2RuthTalkHaven
    Message EternaCity_Text_Arc2RuthBeforeGym
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

EternaCity_Arc2RuthTalkHaven:
    Message EternaCity_Text_Arc2RuthAtHaven
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

EternaCity_Arc2CyrusTalk:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    GoToIfGe VAR_ARC2_PROGRESS, 33, EternaCity_Arc2CyrusTalkHaven
    Message EternaCity_Text_Arc2CyrusBeforeGym
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

EternaCity_Arc2CyrusTalkHaven:
    Message EternaCity_Text_Arc2CyrusWaitHere
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

EternaCity_Arc2GardeniaHavenTalk:
    PlayFanfare SEQ_SE_CONFIRM
    LockAll
    FacePlayer
    Message EternaCity_Text_Arc2GardeniaTrees
    WaitABXPadPress
    CloseMessage
    ReleaseAll
    End

// ---------------------------------------------------------------------------------------------------------------
// 2.11: Garius by the Gym door (frame trigger at progress 31; the player has just walked out of the Gym onto
// (312,563)). Garius battle 1, then Gardenia comes out (2.12 start), then the walk to the Haven.
// ---------------------------------------------------------------------------------------------------------------
EternaCity_Arc2GariusScene:
    LockAll
    ApplyMovement ETERNA_CITY_GARIUS, EternaCity_Arc2Movement_GariusWalkUp
    WaitMovement
    ApplyMovement LOCALID_PLAYER, EternaCity_Arc2Movement_FaceEast
    WaitMovement
    BufferRivalName 0
    Message EternaCity_Text_Arc2GariusTookYouLongEnough
    BufferRivalName 0
    Message EternaCity_Text_Arc2GariusStillFollowing
    BufferRivalName 0
    Message EternaCity_Text_Arc2GariusBattleMe
    CloseMessage
    GetPlayerStarterSpecies VAR_RESULT
    GoToIfEq VAR_RESULT, SPECIES_TURTWIG, EternaCity_Arc2GariusBattleTurtwig
    GoToIfEq VAR_RESULT, SPECIES_CHIMCHAR, EternaCity_Arc2GariusBattleChimchar
    StartTrainerBattle TRAINER_GARIUS_ARC2_ETERNA_PIPLUP
    GoTo EternaCity_Arc2GariusAfterBattle

EternaCity_Arc2GariusBattleTurtwig:
    StartTrainerBattle TRAINER_GARIUS_ARC2_ETERNA_TURTWIG
    GoTo EternaCity_Arc2GariusAfterBattle

EternaCity_Arc2GariusBattleChimchar:
    StartTrainerBattle TRAINER_GARIUS_ARC2_ETERNA_CHIMCHAR
    GoTo EternaCity_Arc2GariusAfterBattle

// The screenplay sets 32 whatever the result: a loss heals the party and the scene goes on (no blackout).
EternaCity_Arc2GariusAfterBattle:
    CheckWonBattle VAR_RESULT
    CallIfEq VAR_RESULT, FALSE, EternaCity_Arc2HealAfterLoss
    SetVar VAR_ARC2_PROGRESS, 32
    BufferRivalName 0
    Message EternaCity_Text_Arc2GariusYoureGood
    BufferRivalName 0
    Message EternaCity_Text_Arc2GariusRowanCalled
    CloseMessage
    ApplyMovement ETERNA_CITY_GARIUS, EternaCity_Arc2Movement_GariusLeave
    WaitMovement
    RemoveObject ETERNA_CITY_GARIUS
    GoTo EternaCity_Arc2GardeniaComesOut

// A lost scripted battle leaves the field unloaded (COMMON hazards): reload it, then heal.
EternaCity_Arc2HealAfterLoss:
    ReturnToField
    FadeScreenIn
    WaitFadeScreen
    HealParty
    Return

// 2.12 start: Gardenia steps out of the Gym door (312,562) behind the player.
EternaCity_Arc2GardeniaComesOut:
    WaitTime 15, VAR_RESULT
    LoadDoorAnimation 9, 17, 24, 18, ANIMATION_TAG_DOOR_1
    PlayDoorOpenAnimation ANIMATION_TAG_DOOR_1
    WaitForAnimation ANIMATION_TAG_DOOR_1
    ClearFlag FLAG_UNK_0x0218
    SetObjectEventPos ETERNA_CITY_GARDENIA, 312, 562
    SetObjectEventDir ETERNA_CITY_GARDENIA, DIR_SOUTH
    SetObjectEventMovementType ETERNA_CITY_GARDENIA, MOVEMENT_TYPE_LOOK_SOUTH
    AddObject ETERNA_CITY_GARDENIA
    PlayDoorCloseAnimation ANIMATION_TAG_DOOR_1
    WaitForAnimation ANIMATION_TAG_DOOR_1
    UnloadAnimation ANIMATION_TAG_DOOR_1
    ApplyMovement LOCALID_PLAYER, EternaCity_Arc2Movement_FaceNorth
    WaitMovement
    Message EternaCity_Text_Arc2GardeniaOffTheRecord
    WaitABXPadPress
    Message EternaCity_Text_Arc2GardeniaShelter
    WaitABXPadPress
    Message EternaCity_Text_Arc2GardeniaSomethingsWrong
    WaitABXPadPress
    CloseMessage
    SetVar VAR_ARC2_PROGRESS, 33
    FadeScreenOut
    WaitFadeScreen
    RemoveObject ETERNA_CITY_GARDENIA
    Warp MAP_HEADER_ETERNA_CITY, 0, 305, 522, DIR_NORTH
    FadeScreenIn
    WaitFadeScreen
    ReleaseAll
    End

// 33, after the warp to the Haven trees (frame trigger on VAR_MAP_LOCAL_2, which OnTransition sets at 33).
// Runs only when the map loaded with the player at the trees spot, i.e. right after the walk.
EternaCity_Arc2HavenArrival:
    SetVar VAR_MAP_LOCAL_2, 0
    GetPlayerMapPos VAR_0x8004, VAR_0x8005
    GoToIfNe VAR_0x8004, 305, EternaCity_Arc2HavenArrivalEnd
    GoToIfNe VAR_0x8005, 522, EternaCity_Arc2HavenArrivalEnd
    LockAll
    ApplyMovement ETERNA_CITY_CYRUS, EternaCity_Arc2Movement_FaceWest
    WaitMovement
    Message EternaCity_Text_Arc2CyrusWaitHere
    WaitABXPadPress
    CloseMessage
    ReleaseAll
EternaCity_Arc2HavenArrivalEnd:
    End

    .balign 4, 0
EternaCity_Arc2Movement_GariusWalkUp:
    WalkNormalWest 2
    EndMovement

    .balign 4, 0
EternaCity_Arc2Movement_GariusLeave:
    WalkNormalSouth
    WalkNormalWest 6
    WalkNormalNorth 8
    EndMovement

    .balign 4, 0
EternaCity_Arc2Movement_FaceEast:
    WalkOnSpotNormalEast
    EndMovement

    .balign 4, 0
EternaCity_Arc2Movement_FaceNorth:
    WalkOnSpotNormalNorth
    EndMovement

    .balign 4, 0
EternaCity_Arc2Movement_FaceWest:
    WalkOnSpotNormalWest
    EndMovement
