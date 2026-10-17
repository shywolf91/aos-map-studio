# Project Context: AI-Designed Ace of Spades VXL Maps

## Main objective

Learn the classic Ace of Spades VXL map format and establish a reliable,
reusable process for turning any map prompt or requested design feature
into an original, beautiful, playable map.

The project must connect technical research with practical production.
The desired endpoint is not merely a collection of prompts or concept images:
it is a working map-generation and validation pipeline.

## Target ecosystem

Primary target:
- Classic Ace of Spades, especially the 0.75 ecosystem.
- Piqueserver and its associated map-loading and mode implementations.

Do not conflate this target with the separate Jagex/Steam game.

The exact server version, client, scripts, and configurations should be
recorded when available.

## Project materials

### Attached brief

ace_of_spades_075_map_design_prompts.md

Use this document for:
- Shared artistic and structural requirements.
- Mode-specific design briefs.
- Additional mode families and modifiers.
- Acceptance criteria.
- Warnings about script-dependent behavior.

Its concept seeds are optional proposals, not mandatory themes or existing maps.

### Research sources supplied by the user

- https://aos.party/
- https://penguins.win/aloha-map-grid/
- https://www.piqueserver.org/aosprotocol/
- https://www.silverspaceship.com/aosmap/

Investigate their actual contents and usefulness rather than assuming their role.

### Additional starting references

- https://www.piqueserver.org/aosprotocol/mapformat.html
- https://docs.piqueserver.org/en/latest/included-gamemodes.html
- https://docs.piqueserver.org/en/latest/configuration.html
- https://docs.piqueserver.org/en/latest/included-scripts.html
- https://github.com/piqueserver/piqueserver

Prefer sources matching the installed server version.

### Reference-inspection status

The supplied Markdown brief has been reviewed for this project setup.

No Shenlong or Jungle Push map files or screenshots were supplied with this
setup request.

The four user-supplied websites could not be retrieved during setup.
Their contents and map references have not been inspected.

Do not infer visual details from map names alone.

## User preferences

### Highest artistic priority

Maps should look beautiful and fit the classic AoS voxel art style.

The user especially likes Shenlong and possibly Jungle Push because of
their visual richness and detail.

Use these references for standards of craft when available.
Do not recycle their objects or reproduce their layouts.

### Originality

Every map should have:
- Its own setting and concept.
- A distinctive landmark or architectural identity.
- Original voxel objects.
- Coherent terrain and material choices.
- Detail that reinforces the setting.
- A layout designed for its mode, rather than a generic environment.

### Symmetry

For symmetric team modes:
- Prefer mirrored or approximately mirrored gameplay structure.
- Keep travel time, cover, elevation, and objective access fair.
- Allow cosmetic differences that make the map feel handcrafted.

Do not impose symmetry on attacker/defender or FFA designs.

### Preferred protection policy

The original request prefers:
- Protected authored map blocks.
- Player construction where appropriate.
- Enemy destruction of player-built structures.

This is a desired server policy, not an inherent feature of a VXL file.

Verify whether each mode supports it and identify any script changes required.

## Technical starting point

The classic VXL specification describes:
- 512 × 512 horizontal columns.
- Vertical positions z = 0 through z = 63.
- z = 0 at the top and increasing z downward.
- Column order progressing through x, then y.
- No conventional file header.
- Variable-length spans containing air, colored surface voxels,
  and implicit solid regions.
- Special handling for terminal spans and the bottom layers.

These facts are a research baseline, not a complete exporter specification.

Before writing an exporter, verify:
- Exact span headers and length interpretation.
- Inclusive/exclusive height conventions.
- Terminal-span handling.
- Color byte order and the fourth byte's meaning.
- Surface-color requirements.
- How hidden solid voxels are reconstructed.
- Bottom-layer rules.
- Reader behavior on malformed or unusual files.

Historical format documentation also describes implicit spawning.
Do not use those historical defaults as a substitute for target-server
metadata or mode-specific spawn logic.

## Structural requirements

Permanent scenery should be continuously face-connected to stable terrain.

Examples:
- Islands rooted into the seabed.
- Roofs connected through walls or pillars.
- Branches connected through trunks and roots.
- Elevated platforms supported by columns, rock, or buttresses.
- Arches and overhangs integrated into grounded structures.

Supports must not introduce unintended routes.

Grounding and protection are separate:
- Connectivity addresses structural support.
- Server rules address destruction permissions.

Avoid universal claims about collapse until tested against the target runtime.

## Primary mode briefs

### Push

Desired experience:
- Start near intel and carry it toward a distant tent/capture destination.
- Build sideways bridges across hazardous gaps.
- Protect, repair, and contest player-built routes.

Implementation note:
The included piqueserver mode describes teams spawning with enemy intel
and pushing it toward their own control point.
Use script-defined ownership, not assumptions based on visual placement.

Design requirements:
- Original islands, structures, or objects.
- Fair paired progressions.
- Equivalent bridge distances and combat opportunities.
- Useful landing areas and meaningful route choices.
- No permanent walkable bypass around the bridge-building challenge.
- Grounded supports that do not become shortcuts.
- Verified map protection, player-block rules, water damage,
  objective protection, resupply, and intel resets.

### Babel: standard implementation

Desired core:
- Upward player construction to reach elevated intel.
- Fair competing build areas.
- Readable vertical progress.
- Counterplay against builders without unavoidable suppression.

Permanent supports must not provide a ready-made ascent that removes
the building challenge.

Verify platform generation, objectives, restricted zones, and capture rules
in the actual script.

### Tower of Babel: custom user variant

The user also wants:
- A massive central tower.
- Opposing ground-level bases.
- Intel at the summit.
- Ledges, stairs, ramps, balconies, and bridgeable gaps.
- Multiple tiers with mid-tower fights.
- A fast risky route and a slower safer route.
- An interesting descent and return journey.

The tower should have a strong identity:
an ancient ziggurat, spiraling spire, overgrown ruin, gothic tower,
sandstone monument, or another original concept.

Use rich but readable detail:
arches, windows, ornaments, statues, banners, vegetation,
and renderer-appropriate lighting accents.

Treat this as a custom variant until a compatible script is identified.
Do not present it as interchangeable with standard construction-focused Babel.

### Arena

Desired experience:
- Compact team elimination rounds.
- No respawns during a round.
- Fair starting zones and quick contact.
- Cover, flanks, elevated positions, and a central landmark.
- No dominant all-seeing position or excessive hiding pockets.
- Enclosed, exploit-resistant playable space.

The user requests player building, but this must be checked against
the actual Arena variant.

For gate-based piqueserver Arena:
- Verify spawn and gate metadata.
- Verify uniform gate colors and selection behavior.
- Keep decorative geometry from accidentally joining gate selection.
- Test gate rebuilding and simultaneous release.

### Capture the Flag

Desired experience:
- Steal enemy intel and return it to the team's capture base.
- Distinct opposing bases with readable intel and tent placements.
- Fast exposed central routes and slower protected flanks.
- Interception, escort, pursuit, and risky escape.
- Several base entrances without an undefendable or impregnable objective.
- Fair route lengths and elevation advantages.

Verify actual capture conditions and object placement in the target implementation.

### Hallway

Desired layout:
- Long, narrow, linear battlefield.
- Opposing end zones.
- Distinct sections rather than one uninterrupted shooting lane.
- Alternating chokepoints and wider engagement spaces.
- Main path, local side routes, ledges, and lower routes where movement permits.
- Balanced spawn protection and distance to the center.
- A coherent theme such as a canyon, gallery, trench, or ruined temple corridor.

Do not assume “Hallway” establishes a particular objective or script.
Determine whether it is CTF, TDM, another mode, or a custom ruleset
using hallway geometry.

## Additional mode coverage

Use the attachment for briefs covering:
- Territory Control.
- Team Deathmatch.
- Free for All.
- Infiltration.
- One-Flag CTF.
- Tug of War.
- Zombies/Infection.
- Last Stand/Survival.
- Fort Wars/Build Then Shoot.
- Domination.
- King of the Hill.
- Intel RPG.
- Parkour/Race.
- Build/Creative.
- Sports variants.
- Running Man.
- Weapon-restricted modifiers.

Community names do not establish standardized rules.
Conditional families require an actual compatible script.

## Research deliverables

### 1. VXL technical reference

Explain the format clearly enough to implement or audit a writer.

Include diagrams or worked byte examples when useful.
Separate specification facts from implementation observations.

### 2. Toolchain assessment

Evaluate available:
- Map editors.
- Voxel authoring tools.
- Procedural generators.
- Python/Cython APIs.
- VXL readers and writers.
- Preview/render tools.
- Server and client validation methods.

Recommend a practical pipeline based on verified capabilities.

### 3. Mode compatibility matrix

For each target mode, record:
- Script/version.
- Objective and scoring.
- Spawn behavior.
- Building and destruction.
- Required metadata.
- Protection and restricted zones.
- Reset and round behavior.
- Remaining uncertainties.

### 4. Minimal technical prototype

Build a small diagnostic scene containing:
- Grounded terrain.
- A supported structure.
- Multiple heights.
- An overhang or enclosed space.
- Distinct colors.
- Test spawns/objectives where appropriate.

Its purpose is exporter and runtime validation, not final artistic quality.

### 5. Reusable map-generation architecture

Separate:
- Prompt/design specification.
- Voxel geometry and materials.
- Original procedural assets.
- Mode metadata.
- Server configuration.
- Export.
- Validation.
- Presentation.

Use deterministic seeds and configurable dimensions where practical.

### 6. First finished map

After validating the toolchain:
- Choose a mode and concept.
- Graybox the gameplay.
- Build original scenery.
- Export and integrate.
- Inspect in-game.
- Iterate on beauty and playability.

## Acceptance criteria

A successful finished map:
- Loads through the target server and client.
- Uses verified VXL encoding.
- Includes correct metadata and setup notes.
- Matches the actual mode or clearly named custom variant.
- Uses original, coherent, detailed voxel art.
- Has supported permanent geometry.
- Enforces the intended destruction policy through server behavior.
- Provides fair spawns and readable objectives.
- Preserves required construction challenges.
- Avoids unintended shortcuts and major boundary exploits.
- Has reproducible source/settings.
- Includes honest validation results and known limitations.

A concept, generated image, or untested VXL must not be described as
a fully validated playable map.
