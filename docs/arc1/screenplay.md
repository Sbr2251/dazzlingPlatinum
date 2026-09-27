# Arc 1 part 1 screenplay (approved)

Scope: a new game up to Cyrus and Barry leaving Lake Verity. Mom's line rewrites, the Route 201 rival battle
and Sandgem come later.

## Intro (Rowan intro app)

- Rowan's intro also says that this game takes place in a parallel dimension (a line or two added to his stock
  speech).
- The player picks a character (Lucas/Dawn) and a name as in stock.
- Rival naming is skipped completely. The rival's name is always "Barry".

## Scene 1: Distortion World flashback

- The last Distortion World exchange between Cyrus and Cynthia (the stock ending after Giratina, in the
  Giratina room), with **the player's own avatar** standing there as the hero. Rowan's assistant is the other
  gender, as in stock.
- Skip the stock opening line that branches on Giratina (defeated / caught / quelled). Use the common ending
  exchange from `res/text/distortion_world_giratina_room.json`.
- Cyrus walks away. Fade out.

## Scene 2: Verity castle roof landing (Lake Verity map, castle terrace, portal at 32,27)

- White flash from the portal, screen shake, then Cyrus is on the terrace beside the portal, facing down. He
  pauses, looks left and right, then speaks. There's no new "lying down" sprite; the flash and pause carry it.
- Cyrus:
  - "...Where am I? This is not the Distortion World. Time flows here. Space holds its shape."
  - "The fall... Did the shadow cast me out? Or did I finally fall far enough to escape it?"
  - "...Was I wrong? No. The logic was sound. And yet... the world remains. I remain."
- Fade out, then the bedroom.

## Scene 3: bedroom TV

- The player watches TV (the stock opening TV program, reworded):
  - Interviewer: "Team Eclipse has been gaining followers at an unprecedented rate. How do you feel about this
    emerging organization?"
  - Rowan: "Any person or group that promises to bring people back from the dead is either a con artist or
    lying to themselves. Either way, they don't have my support."
  - Then the stock outro "That concludes our special program, "Let's Ask Prof. Rowan!"...", changed so it's
    broadcast from Lake Verity.
- The player can move. Then Barry bursts in: "Man, that Team Eclipse really is something. Anyways, Professor
  Rowan's probably the guy that can help us get our starters, and the TV broadcast said he was at Lake
  Verity!" Then his stock bedroom dialogue continues (trimmed to fit where needed).

## Scene 4: Mom (1F)

- Her stock dialogue, but she gives the Running Shoes straight away (on this first talk / on the way out), not
  after the Route 201 scene.

## Scene 5: leaving Twinleaf (Diamond/Pearl style)

- Barry talks about heading to the lake to see if Rowan is still there, and he blocks the tall grass and every
  other area except the way to Lake Verity. Only the path to Lake Verity is open.
- The player and Barry arrive at Lake Verity together.

## Scene 6: Lake Verity

Remove all legacy Lake Verity story content: the Mesprit sighting, the Mesprit cry, and the first lakeside
Cyrus interaction.

1. When the player arrives, the camera pans to the castle top. Rowan and Dawn (the assistant, opposite gender
   to the player) are checking on Cyrus: they ask if he came out of the portal.
2. Before he can answer, a Mawile jumps out of the portal, then a second Mawile.
3. The portal closes. It must visually disappear (`SetLakeVerityPortalHidden 1`).
4. The Mawile chase the three around the terrace. Rowan (cowardly) drops his briefcase of starters.
5. Toward the end, Barry and the player are seen coming up the open staircase (x23-24, z29-37).
6. Rowan and Dawn run past them: "Out of the way, you two! There's a Pokemon going berserk. We all need to get
   out of here!" and leave.
7. Barry sees Cyrus still being chased in circles. The two walk to the briefcase. Barry: "We need to help that
   man. Let's use one of the Pokemon in this briefcase!"
8. Starter select: Turtwig, Chimchar, Piplup. Barry also picks one (the stock rule: the one strong against the
   player's).
9. A Mawile gets an exclamation mark and jumps at the player, and the battle starts: wild Mawile Lv3, Hyper
   Cutter, Astonish + Fake Tears. Losing continues the story, with no whiteout.
10. Barry fights the second Mawile off screen. After it, he says his Mawile ran off.

After the battle, Cyrus (slowly turning toward them, thankful):
- "...You two. You remind me of someone I once knew. A child who stood against me with nothing but a Pokemon
  and... conviction."
- "I once called that a flaw. Spirit. Something to be purged."
- "And yet that same flaw is the reason I'm still standing."
- "...Thank you. Both of you."
- "The professor ran and left this behind. A curious choice for a man of science."
- "I'll return it to him myself. He and I have much to discuss."
- He picks up the briefcase and leaves.

Barry: "Whew! Perfect timing on our part. However, I'm not sure what to make of that guy just yet. And man, he
was wearing some weird clothes. Whatever, though, I'm going to go ahead and head back home and heal my
Pokemon." Barry leaves.

## Scene 7: to be continued

- The stock Route 201 Rowan / starter / first rival battle scene is disabled.
- A temporary "To be continued..." block on Route 201 (a trigger/sign/NPC that shows the message and stops the
  player going further). In the next arc, the first rival battle happens back on Route 201.

(In message text, write "Pokemon" with the game's e-acute character the way neighbouring stock messages do.)
