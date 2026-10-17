# Ace of Spades 0.75 — Original Map Creation Briefs for Game Modes

## Purpose and scope

Adapt the supplied Push brief into reusable instructions for creating beautiful, original maps for classic Ace of Spades 0.75. This document contains brief mode descriptions, a shared creation prompt, and mode-specific prompts.

**There is no finite official list of every community mode.** The 0.75 protocol has two native modes: Capture the Flag and Territory Control. Servers emulate additional modes through scripts. This document covers both native modes, all eight modes listed in piqueserver's included-mode documentation, and additional community mode families and modifiers. The extra families are conditional briefs, not a claim that every server offers them or uses identical rules. This concerns classic AoS, not the separate Jagex/Steam game.

The actual server scripts and their versions are authoritative. Before creating a map pack, inventory the target server's installed modes, read their rules and metadata requirements, and add a brief for any unlisted custom mode. Do not silently substitute generic FPS rules for an unfamiliar AoS script.

**Reference status:** Shenlong and Jungle Push are the user's visual preferences. No map files or screenshots were supplied with this request, so they have not been inspected. The prompts below instruct the future map creator to inspect references when available.

## Brief descriptions

| Mode / family | Status | Brief description |
|---|---|---|
| Capture the Flag (CTF) | Native | Steal enemy intel and bring it to your team's capture base. |
| Territory Control (TC) | Native | Capture territory points and take control of the battlefield. |
| Push | Included piqueserver mode | Carry intel from the spawn area to a distant capture point by building bridges across hazardous gaps. |
| Babel | Included piqueserver mode | Build upward to reach elevated intel, then capture it according to the script. |
| Arena | Included piqueserver mode | Round-based team elimination; the surviving team wins. |
| Team Deathmatch (TDM) | Included piqueserver mode | Teams compete for kills. |
| Free for All (FFA) | Included piqueserver mode | Individual players compete against everyone else. |
| Infiltration | Included piqueserver mode | Attackers steal defended intel; defenders score by keeping it secure. |
| One-Flag CTF / OneCTF | Included piqueserver mode | Teams contest a single central intel; capture behavior follows the script. |
| Tug of War (TOW) | Included piqueserver mode | Advance the front by capturing successive control points. |
| Zombies / Infection | Community family | Humans resist zombie players; infection, respawn and victory rules vary. |
| Last Stand / Survival | Community family | Defenders survive attacks for a round, timer or wave objective. |
| Fort Wars / Build Then Shoot | Community family | Players prepare fortifications before a combat phase. |
| Domination | Conditional custom family | Hold several objectives to accumulate score, where a script implements this. |
| King of the Hill (KOTH) | Conditional custom family | Contest one scoring area, with fixed or rotating locations depending on the script. |
| Intel RPG | Community variant | Intel-related play combined with script-specific progression or abilities. |
| Parkour / Race | Community family | Complete a movement course; checkpoints and timing depend on the script. |
| Build / Creative | Community server family | Collaborative voxel construction rather than conventional combat victory. |
| Sports / Football / Basketball | Community script family | Move a scripted ball or equivalent scoring object into opposing goals. |
| Running Man | Gameplay modifier | Linked teammates must stay close together; excessive separation kills them. |
| Weapon-restricted play | Gameplay modifier | A base mode played with a limited weapon set, such as rifles or spades. |

Native and included-mode descriptions are grounded in sources [1–3]. Community references [4–7] establish the broader script ecosystem and examples; conditional descriptions above are design assumptions that must be matched to an actual script.

## Shared creation prompt — use with every mode-specific prompt

You are creating original playable voxel maps for classic Ace of Spades 0.75. Inspect the supplied maps, screenshots, target server configuration and relevant scripts before designing anything. If reference files are missing, state that limitation and develop an original concept without claiming to have inspected them.

My priority is beautiful maps that fit the AoS art style. I especially appreciate the detail and visual richness of Shenlong and Jungle Push. Use those maps as inspiration for craft, composition and density of detail, **not as a source of reusable objects**. Do not copy their landmarks, terrain arrangements, structures or voxel models. Invent your own setting, architectural language, terrain and objects.

Create scenery with clear silhouettes, restrained material palettes, stepped voxel contours and deliberate color shading. Use detail where it reinforces the setting: machinery, rock strata, roots, rooflines, docks, stonework, vegetation and signs. Avoid random color noise, generic scattered cubes, empty flat terrain and oversized primitive shapes standing in for finished landmarks. Detail must preserve player visibility and navigation.

Every permanent island, object, roof, overhang and elevated platform must have a continuous solid voxel connection to stable grounded terrain. Use face-connected supports rather than diagonal contact. Root islands into the seabed and connect branches to trunks, trunks to roots, roofs to walls and platforms to pillars or rock. Hidden submerged foundations are acceptable if they remain inaccessible to players and do not create shortcuts. Never rely on floating decorative clusters.

**Ground connection and indestructibility are different requirements.** Structural connectivity prevents unsupported voxel components; server rules determine whether blocks can be destroyed. The original brief's warning is best understood as a support/connectivity issue, not a universal rule that one damaged block destroys any object. Check behavior in the actual server and client.

Do not transfer Push's block-protection policy to every mode. Preserve building, digging, demolition and restoration rules required by the selected mode. Where terrain is destructible, use broad foundations, multiple supports and deliberate breachable areas. Where map blocks must be protected, specify the necessary server configuration or script. A VXL file alone does not enforce block ownership or indestructibility.

Use mirrored or rotationally balanced layouts for symmetric team modes. Cosmetic asymmetry is welcome when travel times, cover, objective access and elevation remain fair. Use intentional functional asymmetry for attacker/defender modes and distributed balance for FFA. Do not force symmetry onto a mode that benefits from different roles.

Plan spawn safety, useful landmarks, readable objectives, flanks, cover and movement before adding decoration. Avoid unavoidable spawn sightlines, single dominant sniper nests, accidental dead ends and objectives that players can seal permanently. Leave room for player construction when building is part of the mode.

Stay within the target classic map format and validate the actual exporter and coordinate conventions. Do not invent metadata fields. Inspect the installed mode's code or working map examples to obtain correct spawn, intel, control-point, gate, build-zone and checkpoint definitions.

For each mode:
1. Propose three distinct original concepts, each with a setting, landmark, palette and gameplay layout.
2. Select the strongest concept using visual quality, mode suitability and originality.
3. Build the selected map when map-authoring/export tools are available. If they are unavailable, deliver a concrete build specification and state that it is not a playable map yet.
4. Supply the VXL, required metadata, dependency/configuration notes, overhead view and several in-game-scale views when producing an actual map.
5. Validate grounded connectivity, movement, spawns, objectives, destruction rules and representative player counts on the target server.
6. Record what was actually tested and any remaining limitations.

The concept seeds below are optional starting points created for this brief, not existing maps to copy. Give the map pack variety; do not repeatedly reskin one layout.

## 1. Capture the Flag (CTF)

**Brief description:** Steal the opposing team's intel and return it to your capture base.

**Map-creation prompt:**

This is Capture the Flag. Design the map around infiltration, theft, escort and interception. Each team needs a recognizable base, accessible intel placement and several viable routes between bases. Include a central combat route, a covered flank and a route with a different elevation or exposure tradeoff.

Create a mirrored or approximately mirrored landscape with original voxel landmarks. Balance approach times and defensive cover, while allowing each side its own cosmetic identity. Place intel where defenders can contest it without turning its room into an unbreakable bottleneck. Avoid a direct spawn-to-spawn firing lane and a return route that is always safe.

Keep construction and digging meaningful under the target server's rules. Ground all permanent scenery, but do not protect the entire map unless that is the intended server variant. Test tunnel shortcuts, base fortification, dropped-intel recovery and capture behavior.

**Original concept seed:** *Copperleaf Reservoir* — opposing waterworks among autumn terraces, with a central spillway, low maintenance galleries and grounded pump towers.

## 2. Territory Control (TC)

**Brief description:** Capture territory points to gain control of the map.

**Map-creation prompt:**

This is Territory Control. Create a beautiful battlefield whose important places become distinct capture areas. Build a connected network of routes between objectives instead of arranging every point in one narrow corridor. Each point should have multiple approaches, usable cover and recognizable visual identity.

Use balanced terrain and access for both teams. Let different objectives encourage different engagements: a sheltered courtyard, a ridge, a quarry floor or a compact industrial yard. Avoid a high position that dominates every objective simultaneously.

Read the actual TC implementation to determine how points and spawns are selected. Confirm that generated or configured points land in playable spaces. Do not assume a custom scoring system or hand-authored point metadata exists.

Preserve the selected building and destruction rules. Test how captured territory changes spawning and whether a losing team can still counterattack.

**Original concept seed:** *Basalt Orchard* — orchard terraces around a quarry, with a kiln yard, stone terraces and an irrigation pavilion as distinct combat areas.

## 3. Push

**Brief description:** Carry intel from the spawn toward a distant tent/control point by constructing bridges over hazardous gaps.

**Map-creation prompt:**

This is Push. Players start near the suitcase/intel and must bring it to the destination tent. In the common piqueserver implementation, the carried item is technically enemy intel placed near the team's spawn; verify team ownership and capture placement in the installed script.

Create original islands, objects or grounded structures separated by gaps that require sideways bridge construction. Make bridging, protection, repair and sabotage the central experience. Give players meaningful landing points, choices of bridge alignment and opportunities for cross-team fighting. Do not include an existing walkable route that bypasses construction.

Use a mirrored or approximately mirrored design with equivalent gaps, cover, elevations and progress requirements. Create completely new voxel objects and scenery rather than recycling objects from Shenlong or Jungle Push.

All permanent map components must connect to stable terrain, including islands rooted into the seabed. Configure original map blocks to be indestructible and enforce the desired ownership rules for player-built bridges. Validate those rules in the server; protection is not encoded by scenery alone. Confirm water damage, capture protection, build areas, block resupply and dropped-intel resets.

**Original concept seed:** *Tideglass Foundry* — seabed-rooted furnace platforms, cooling basins and broken loading arms form two balanced chains across a turquoise channel.

## 4. Babel

**Brief description:** Build upward to reach elevated intel and complete the script's capture objective.

**Map-creation prompt:**

This is Babel. The central construction challenge is vertical ascent. Create balanced team building areas beneath or beside an elevated objective, with enough open space for towers, ramps and improvised approaches.

The elevated structure must look convincingly supported by grounded pillars, buttresses or a large rock formation. Those permanent supports must not provide a climbable route that bypasses the required player construction. Do not replace Babel's upward challenge with ordinary stairs or a Push-style horizontal course.

Design original scenery that frames the tower race and makes progress visible. Control long-range sightlines so a single perch cannot permanently suppress every builder. Read the script to establish build boundaries, restricted zones, objective layout and return/capture behavior.

Test all permanent surfaces for unintended access and ensure players can recover or reset dropped intel. Confirm platform protection without assuming map connectivity alone protects it.

**Original concept seed:** *Solar Crown* — a grounded observatory canopy above sandstone courtyards, supported by inaccessible smooth pylons outside the ascent zones.

## 5. Arena

**Brief description:** Eliminate the opposing team in rounds; dead players wait for the next round.

**Map-creation prompt:**

This is Arena. Build a compact, polished team-survival battlefield with balanced starting areas, varied cover and several interconnecting routes. Make first contact fair, and prevent either team from holding every exit from an overwhelming position.

Create original landmarks that support short tactical engagements. Include spaces suited to different weapons, but do not add excessive hiding pockets that prolong rounds. The usual no-building/no-breaking variant should be playable entirely through the authored geometry; confirm the installed rules.

For piqueserver's gate-based Arena, provide the required spawn and gate metadata. Gate blocks must follow its exact color/connectivity behavior. Do not let nearby decorative blocks accidentally join the gate selection. Ensure server-controlled gate removal and rebuilding still work when terrain protection is enabled.

Ground permanent scenery and test round starts, release timing, spectator/death handling and every reachable hiding place.

**Original concept seed:** *Ceramic Works* — a symmetrical kiln complex with glazed arches, loading courts and a low central drying hall.

## 6. Team Deathmatch (TDM)

**Brief description:** Teams compete to achieve the kill objective.

**Map-creation prompt:**

This is Team Deathmatch. Design a combat loop that supports repeated engagements, safe re-entry and shifting territorial pressure. Use several connected routes with close, medium and selectively long sightlines.

Choose balanced team sectors or spawn behavior appropriate to the script. Prevent spawn camping through terrain screening, alternative exits and cover. Avoid a central tower that sees all spawns or a decorative maze that makes encounters rare.

Create a distinctive original setting whose landmarks help players predict enemy movement. Make construction and demolition useful if enabled, while keeping the map enjoyable before anyone places a block. Test how destroyed cover changes combat and whether the map needs round restoration.

Ground scenery and verify scoring, respawns, effective playable area and weapon balance.

**Original concept seed:** *Switchyard Gardens* — a compact freight yard reclaimed by vegetation, with grounded signal towers, workshop courts and freight-car cover.

## 7. Free for All (FFA)

**Brief description:** Every player fights independently against everyone else.

**Map-creation prompt:**

This is Free for All. Balance distributed spawn locations and circulation rather than two mirrored team bases. Create a network of loops that lets players move, disengage and encounter opponents without repeatedly crossing one lethal choke.

Use original voxel scenery with readable districts and varied cover. Avoid a central perch that controls all spawn positions. Give elevated locations exposed approaches and counters. Ensure nearby spawns do not create immediate unavoidable fights.

Read the actual script's team emulation, spawn selection and scoring behavior. Do not assume native individual teams exist in the protocol. Test repeated respawns at several population levels and remove dead zones, spawn traps and excessively safe camping pockets.

Keep building and destruction consistent with the server and ground all permanent objects.

**Original concept seed:** *Saltwind Market* — irregular courtyards around a low market hall, with awnings, pottery stalls, accessible roofs and several looping alleys.

## 8. Infiltration

**Brief description:** Attackers capture defended intel; defenders gain score for keeping it secure.

**Map-creation prompt:**

This is Infiltration. Create an intentionally asymmetric map with an attacker staging area, a fortified defender location and an intel objective that can be reached through several attack plans.

Give defenders stronger initial positions without making the intel inaccessible. Provide attackers a fast exposed route, a slower covered route and an alternative breach or elevation route. Design the escape after theft as carefully as the approach.

Do not mirror the roles. Balance the layout against the script's team ratio, defensive scoring interval and attacker capture reward. Check whether digging, demolition or player fortification is allowed before relying on breachable walls.

Build an original setting with believable layers of security and grounded architecture. Test defending, attacking, escape and dropped-intel recovery with representative teams.

**Original concept seed:** *Monsoon Archive* — an elevated records compound approached through flooded terraces, a service yard and a grounded aqueduct gallery.

## 9. One-Flag CTF / OneCTF

**Brief description:** Teams compete over a single central intel.

**Map-creation prompt:**

This is One-Flag CTF. Create a clear central contest area with fair arrival times, multiple approaches and room for a carrier to escape. Read the installed script before deciding where carriers score; do not assume every one-flag variant uses the same destination.

Use mirrored or approximately mirrored team sectors, balanced interception routes and equal exposure around the intel. Keep its location readable without making it a completely uncovered firing bowl.

Invent a central landmark with original geometry and palette. Ground it and any elevated decoration. Let flanks support escort and interception, while preventing one permanent sniper position from deciding every pickup.

Test pickup, capture, death drops, resets and construction around the objective.

**Original concept seed:** *Amber Signal* — a grounded beacon pavilion in the middle of two balanced headlands, with low retaining walls and winding coast paths.

## 10. Tug of War (TOW)

**Brief description:** Capture successive control points to push the front toward the enemy's end.

**Map-creation prompt:**

This is Tug of War. Design a readable sequence of contested areas along the progression supported by the script. Treat each stage as a complete fight with multiple local approaches and a clear fallback position.

Use a balanced arrangement of stages. Avoid one objective that becomes much harder to attack than all others, and do not let a bypass reach objectives out of order. Give successive locations visual variety while retaining a coherent setting.

Read the script's point positioning and spawn advancement behavior. Do not assume arbitrary branching objective networks are supported. Include routes for counterattacks and check that forward spawns cannot be fired on directly from newly contested points.

Ground permanent landmarks and preserve required construction/destruction behavior.

**Original concept seed:** *Glacier Railway* — successive freight yards, snow galleries and maintenance courts along a stepped valley, using paired flank paths at each stage.

## 11. Zombies / Infection

**Brief description:** Humans resist zombie players under server-specific infection and victory rules.

**Map-creation prompt:**

This is a Zombies or Infection variant. Read the actual rules first: identify zombie movement, health, weapons, infection behavior, respawns and human victory conditions. Design the map for that implementation.

Create original atmospheric voxel scenery with several defensible locations, escape routes and paths that let zombies approach without crossing one uninterrupted gun corridor. Avoid human perches zombies cannot reach under their permitted movement rules.

If building is allowed, make barricades valuable but challengeable. If destruction is restricted, provide permanent alternative access. Avoid tiny sealed rooms that guarantee survival and hidden crevices that stall the match.

Do not assume AI waves exist; many variants use player-controlled zombies. Ground the setting and test both roles.

**Original concept seed:** *Reedlight Sanatorium* — connected treatment wings and overgrown courts with low roofs, service alleys and several retreat paths.

## 12. Last Stand / Survival

**Brief description:** Defenders attempt to survive a script-defined attack, timer or wave sequence.

**Map-creation prompt:**

This is Last Stand or Survival. Confirm whether attackers are players or bots, how rounds end and whether defenders build before or during combat.

Create layered defensive terrain with fallback positions and several attack approaches. Give defenders recognizable rally areas without concentrating all action into one doorway. Design the outer perimeter, middle defenses and final holdout as connected spaces.

Avoid unreachable fortresses, unlimited retreat loops and camping pockets that attackers cannot discover. Balance ammunition, resupply and fortification space against the script, rather than inventing those systems in map geometry.

Use original grounded landmarks and test attack pressure, retreat, breachability and the final victory condition.

**Original concept seed:** *Emberwatch Depot* — a hillside emergency station with retaining walls, a repair court and an exposed grounded communications mast.

## 13. Fort Wars / Build Then Shoot

**Brief description:** Teams prepare fortifications during a building phase and fight afterward.

**Map-creation prompt:**

This is Fort Wars. Verify the selected script's phase transitions, build boundaries, objective and restoration behavior. Create balanced construction plots with clear terrain features and enough freedom for players to design their own defenses.

Provide beautiful original scenery around and between the plots, but leave the important fortification work to players. Do not prebuild a perfect fortress or obstruct useful construction space with decorative clutter.

Use a neutral combat area with several approaches. Test firing angles across the phase boundary and ensure players cannot place unreachable objectives, completely seal required routes or attack during preparation through a map exploit.

Ground permanent scenery and separate its protection from the intended destructibility of player-built forts.

**Original concept seed:** *Ochre Frontier* — matched excavation terraces facing a dry riverbed, framed by grounded drilling sheds and stepped rock walls.

## 14. Domination — conditional custom mode

**Brief description:** Teams hold multiple objectives to earn score, if the selected script implements this rule.

**Map-creation prompt:**

This is the server's Domination variant. Verify scoring, number of objectives, capture rules and respawns before making the map. If no Domination script exists, do not label a TC map as Domination without explaining the difference.

Design an interconnected objective network with balanced travel times and meaningful decisions about attacking, defending and rotating. Give each objective distinct scenery, several approaches and cover that does not favor one team consistently.

Prevent one elevated position from defending every point. Ensure a disadvantaged team has routes to retake territory without crossing all held objectives.

Create original grounded landmarks and test objective rotations with the script's actual scoring.

**Original concept seed:** *Verdigris District* — a compact industrial town organized around a fountain court, a tram workshop and a terraced greenhouse yard.

## 15. King of the Hill — conditional custom mode

**Brief description:** Teams fight to control one scoring zone, fixed or rotating according to the script.

**Map-creation prompt:**

This is King of the Hill. Read the capture radius, scoring conditions, contested-state behavior and any zone rotation rules. Shape the main objective as a contested space with several entrances, mixed cover and fair arrival times.

Do not put the entire objective in a tiny sealed room or on an inaccessible peak. Make holding it expose players to several attack directions while still rewarding coordinated defense.

For rotating objectives, ensure every supported location has balanced access and room for simultaneous combat. Do not assume the script supports rotation merely because the map has several landmarks.

Create an original setting with grounded structures and test capture-zone boundaries in game.

**Original concept seed:** *Windmill Court* — a low grounded mill surrounded by terraces, stone walls and balanced approach lanes.

## 16. Intel RPG

**Brief description:** Intel-focused play with progression or abilities defined by a community script.

**Map-creation prompt:**

This is Intel RPG. Inspect the actual implementation before designing objectives: determine how intel, classes, levels, abilities, rewards and victory interact. The name alone is not a complete ruleset.

Build a readable objective battlefield with varied engagement ranges and counterplay for the implemented abilities. Use terrain to offer choices without creating positions that become invulnerable for particular classes.

Do not invent shops, quests, teleporters or progression systems unless the server provides them. Account for any changes to movement, range, health or explosives. Preserve the verified underlying intel capture loop.

Create original grounded scenery and test both baseline and advanced player capabilities.

**Original concept seed:** *Prism Excavation* — a layered mineral dig with a grounded survey station, service tunnels and stepped working terraces.

## 17. Parkour / Race

**Brief description:** Complete a movement course using the script's timing and checkpoint rules.

**Map-creation prompt:**

This is Parkour or Race. Verify the movement model, allowed tools, checkpoints, reset behavior and whether construction is permitted. Build a clear sequence of movement challenges with gradual difficulty and fair recovery.

Integrate the course into beautiful original voxel scenery. Support every permanent platform with grounded columns, buttresses or connected terrain; position those supports so players cannot use them to skip the intended course.

Use readable landing surfaces and consistent visual cues for routes. Avoid blind jumps, decorative collision traps and mandatory movements that fail in the target 0.75 client.

Only specify checkpoint metadata that the script actually supports. Test every jump, reset and shortcut in game.

**Original concept seed:** *Cloudstone Aqueduct* — a grounded cliffside waterworks course with supported platforms, stepped arches and sheltered recovery ledges.

## 18. Build / Creative

**Brief description:** Players collaboratively construct voxel structures under server-specific permissions.

**Map-creation prompt:**

This is a Build or Creative server. Design a beautiful original environment that gives players usable building space and an inspiring shared setting.

Provide distinct plots or natural districts, readable paths and a modest collection of original grounded example structures. Leave generous open areas and avoid filling the map with finished scenery that prevents player authorship.

Verify plot ownership, save behavior, rollback, grief protection and available building tools. A map cannot implement those permissions by itself. Keep any protected showcase area separate from construction plots through the server's supported controls.

Test accessibility, plot usability and persistence.

**Original concept seed:** *Maker's Estuary* — terraced waterfront plots around a small civic plaza, with grounded docks, stone embankments and generous workshop space.

## 19. Sports / Football / Basketball

**Brief description:** Teams score with a ball or equivalent object handled by a community sports script.

**Map-creation prompt:**

This is the installed sports variant. Inspect the script to determine ball interaction, goal detection, scoring, boundaries, resets and permitted combat before designing the field or court.

Create balanced team halves with unobstructed play space, readable goals and safe restart positions. Place rich original voxel scenery beyond the active playing area so it frames play without interfering with the ball or goal detection.

Do not assume the map can create ball physics, bouncing or kicking on its own. Ground stands, roof canopies, scoreboards and decorative objects. Match enclosure and out-of-bounds geometry to the actual script.

Test goals, resets, stuck-ball cases and symmetry.

**Original concept seed:** *Harbor Bowl* — a compact waterfront sports ground with grounded stepped stands, storage sheds and painted voxel boundary markings.

## 20. Running Man — modifier

**Brief description:** Teammates are linked and must stay close; straying too far causes them to explode.

**Map-creation prompt:**

This is a Running Man variant applied to the verified base mode. Preserve that base mode's objective and adapt routes for paired movement.

Provide parallel cover, reasonably wide approaches and coordinated movement options. Avoid repeated narrow passages, mandatory single-player jumps or alternate paths that separate linked players beyond the permitted distance.

Read the link-distance rule and pairing behavior. Do not treat Running Man as a generic running race. Test partners moving through each major route and around obstacles while fighting.

Use original grounded scenery and keep cosmetic detail from obstructing synchronized movement.

**Original concept seed:** *Twintrail Canyon* — paired tracks around rock spurs and grounded rail sheds, with cover that accommodates two moving players.

## 21. Weapon-restricted play — modifier

**Brief description:** A base mode played with restrictions such as rifle-only, shotgun-only or spade-only.

**Map-creation prompt:**

This is a weapon-restricted variant. Identify its underlying objective, allowed weapons, damage rules and building permissions. Adapt the map to that combination.

For rifle-only play, offer varied angles and meaningful cover rather than one huge exposed firing strip. For shotgun-only play, emphasize close and medium routes without making every corridor a blind ambush. For spade-only play, prioritize accessible circulation, melee space and the actual digging rules.

These variants do not require separate invented objective mechanics. Preserve the base mode's balance, spawns and win conditions. Build original grounded scenery and test engagements with the permitted equipment.

**Original concept seed:** *Slate Courtyard* — a layered masonry workshop district whose route lengths and openings can be tuned for the chosen weapon set.

## Final acceptance checklist

- Reference inspection is accurately reported; missing maps are not described as inspected.
- Every mode available on the target server has an applicable brief and verified rules.
- Every map has a distinct concept, palette, original objects and clear landmarks.
- Permanent geometry has a continuous face-connected path to stable grounded terrain.
- Foundations do not create walkable shortcuts through hazards or movement challenges.
- Server protection matches the mode; original geometry and player-built blocks are handled correctly.
- Spawns, intel, capture points, gates and other scripted areas use verified metadata.
- Objectives cannot be made inaccessible by foreseeable construction or terrain exploits.
- Symmetry or intentional asymmetry fits the mode's roles.
- Player visibility, travel times, weapon ranges and navigation remain readable.
- Actual maps are exported, loaded and tested; untested specifications are labelled honestly.
- Screenshots and validation notes accompany any playable-map delivery.

## Sources and implementation references

Checked October 12, 2026. These establish mechanics and implementation categories; the original art directions and concept seeds are proposals written for this brief.

1. [Piqueserver architecture — native protocol modes and scripted modes](https://docs.piqueserver.org/en/latest/architecture.html)
2. [Piqueserver included game modes — Arena, Babel, FFA, Infiltration, OneCTF, Push, TDM and TOW](https://docs.piqueserver.org/en/latest/included-gamemodes.html)
3. [Piqueserver configuration — game_mode and original-block controls](https://docs.piqueserver.org/en/latest/config-options.html)
4. [Piqueserver included scripts — Running Man and other modifiers](https://docs.piqueserver.org/en/latest/included-scripts.html)
5. [Build and Shoot community mode discussion — historical names including Zombies and Intel RPG](https://webmail.buildandshoot.com/forums/viewtopic.php?f=5&t=252)
6. [Build and Shoot discussion — Build Then Shoot / Fort Wars](https://webmail.buildandshoot.com/forums/viewtopic.php?f=5&t=10727)
7. [Community script archive — examples including building and basketball scripts](https://github.com/MarshmelloOS/ace-of-spades-scripts)
8. [Piqueserver Extras — additional community scripts and maps](https://github.com/piqueserver/piqueserver-extras)

The historical forum references were discoverable through indexed search excerpts; their full pages were unavailable during verification. They establish community names, not standardized mechanics. Domination, KOTH and other conditional families require an actual compatible script. To extend this document to a particular server's complete catalog, inspect that server's installed script inventory.
