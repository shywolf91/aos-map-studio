# AGENTS reference — map catalogue, lessons, Claude Code details

Moved out of `AGENTS.md` on 2026-11-18 so the always-loaded context stays small. Section numbers match the
pointers in `AGENTS.md`. Read this when you need the catalogue, a past lesson, or tooling/git specifics.

## 8. Lessons not to repeat

* Mirror first, then place cosmetic or asymmetric pieces (stem, witches, sky decor).
* Mirroring leaves column 256 empty unless you copy 255 into it.
* Props must test the surface they land on. Keep spawn squares, anchors, walkways and objective columns in a no-prop mask.
* Enforce face contact for trunks, branches, roofs and vigas. Diagonal-only contact floats, and floating pieces collapse.
* Sky decor only reads within ~65 voxels. Fog (~128) and the 64-voxel ceiling stop backdrops from carrying across the map.
  Birds narrower than ~13 voxels vanish.
* Dense foliage creates walk-out pockets (Backyard Babel). Check for trap cells, and keep foliage off spawn fronts.
* A painted z = 63 sea or sky (Cloud Smash technique) gives a large visual payoff at zero gameplay cost.
* Big maps are fine for the server, but watch the file size: Backyard Babel is 7.6 MB, about 3× normandie. Client FPS is untested.

## 9. Map catalogue

| map | mode | latest | status | where the source lives |
|---|---|---|---|---|
| Kestrel Spires | sky Babel | art v2 / v3 | client-inspected (BetterSpades) | `scenes/kestrel_spires*` |
| Hollowfen | Babel + CTF | art v1 | client-inspected (BetterSpades) | `scenes/hollowfen*` |
| Hollowfen Vale | Babel | v1 | server-loaded | `scenes/hollowfen*`, `docs/hollowfen_vale_spec.md` |
| Drowned Cathedral | Halloween Babel | v2 (rotated redesign) | server-loaded; v1 playtested by a tester | `scenes/drowned_cathedral*` |
| spinline | joke Babel (pinline-style) | v1.4 | client-loaded by owner | **zip from its chat**; spec `docs/spinline_spec.md` |
| Brimstone Atoll | Halloween island Babel | v1.3 | server-loaded | **zip from its chat**; spec `docs/brimstone_atoll_spec.md` |
| Witchwood Isles | Halloween island Babel | v1.0 | server-loaded | `scenes/witchwood_isles/`, `maps/witchwood_isles_v1_0/`; spec `docs/witchwood_isles_spec.md` |
| Backyard Babel | Grounded-style backyard Babel | v5.0 | server-loaded | **zip from its chat**; spec `docs/backyard_babel_spec.md` (v2 spec kept) |
| The Wicker King's Harvest | Halloween island Babel | v1.0 / v1.1 (sky) | server-loaded | `scenes/wicker_kings_harvest/` |
| Graveyard of the Forgotten — The Bone Cathedral | Halloween ground Babel | v1.0 | client-inspected (BetterSpades screenshots) | `scenes/graveyard_forgotten/`, `docs/graveyard_of_the_forgotten_spec.md` |
| The Hollow Crown | Halloween ground Babel | v1.1 (v1.0 kept) | server-loaded + bots | `scenes/hollow_crown/`, `docs/hollow_crown_spec.md` |
| Death Swamp | Push (first) | v1.0 | server-loaded + bots | **zip from its chat**; spec `docs/death_swamp_spec.md` |
| Haunted Fairground | Halloween island Babel (Ruins layout) | v1.3 | server-loaded | `scenes/haunted_fairground/` (needs `refs/Ruins.vxl` or `RUINS_VXL`), `maps/haunted_fairground_v1_3/`; spec `docs/haunted_fairground_isles_v1.md` |
| Ferrari's Revenge (Skull River) | Babel | v3 | parser-validated | **zip from its chat**; spec `docs/skull_river_spec.md` |
| Royal Parade Halloween | community-map edit (Bradley & Mile) | v1.1 | parser-validated; viewed on alohacraft | **zip from its chat**; spec `docs/royal_parade_halloween_spec.md` |
| 1river2night v2.2 | night recolour + glow | v2.2 | parser-validated | **zip from its chat**; spec `docs/1river2night_v2_spec.md` |
| Bikini Atoll (Detonation) | Push glow edit (IAmYourFriend) | v1.2 | parser-validated | **zip from its chat**; spec `docs/bikini_atoll_detonation_spec.md` |
| Silverpine Hunt | Halloween snow Babel | v1.x → v2.2 (+sky) | server-loaded | v2.2: `scenes/silverpine_hunt_v2/`, `maps/silverpine_hunt_v2_2*/`, `server_test/sph_babel/` (v1 still zip-only); specs `docs/silverpine_hunt_spec.md`, `docs/silverpine_hunt_v2_spec.md` |
| Mossglade Pond | ground Babel | v1.0 | server-loaded | **zip from its chat**; spec `docs/mossglade_pond_spec.md` (owner decisions open) |
| Lantern Bazaar Canals | ground Babel | v1.0 | server-loaded | **zip from its chat**; spec `docs/lantern_bazaar_canals_spec.md` |
| Highland Loch Castle | island Babel | v1.0 | server-loaded | **zip from its chat**; spec `docs/highland_loch_castle_spec.md` |
| Sunken Reef Atoll | island Babel | v1.0 | server-loaded | **zip from its chat**; spec `docs/sunken_reef_atoll_spec.md` |
| Clockwork Skyyard | steampunk sky Babel | v1.0 | server-loaded | **zip from its chat**; spec `docs/clockwork_skyyard_spec.md` |
| Cherry Terrace Gardens / Cherry Gardens | spring ground Babel | v1.0 (rebuilt as Cherry Gardens) | parser-validated / server-loaded | **zip from its chat**; specs `docs/cherry_terrace_gardens_spec.md`, `docs/cherry_gardens_spec.md` |
| Remoria ([recreate] of remus) | ground Babel | v1.0 | server-loaded | **zip from its chat**; report `docs/remus_recreate_report.md` |
| Bloomhop Kingdom | platformer-world ground Babel | v1.0 | server-loaded | `scenes/bloomhop_kingdom/` (compile `vxlenc.c` first), `maps/bloomhop_kingdom_v1/`, `server_test/bk_babel/`; spec `docs/bloomhop_kingdom_spec.md` |
| Under the Tree | Christmas Babel, assist structures | v1.0 | server-loaded | **zip from its chat**; spec `docs/under_the_tree_spec.md` |
| Tradeoff Christmas (ei8htx / aloha.pk Tradeoff retheme) | community-map Christmas edit, Babel (original hooks kept) | v1.0 (floor props, superseded) / v2.0 | parser-validated | `scenes/tradeoff_christmas/` (`tc_build.py` v1, `tc2_build.py` v2), `maps/tradeoff_christmas_v1/`, `_v2/`, specs `docs/tradeoff_christmas_spec.md`, `docs/tradeoff_christmas_v2_spec.md` |
| Frostbell Hollow | Christmas alpine-village ground Babel | v1.2 (v1.0, v1.1 kept) | server-loaded | `scenes/frostbell_hollow/` (built with `aosmap.kit`), `docs/frostbell_hollow_spec.md` |
| Elderveil | dark-fantasy ruins ground Babel, assist structures | v1.1 (v1.0 kept) | server-loaded (spawn exposure waived by owner) | `scenes/elderveil/` (built with `aosmap.kit`), `docs/elderveil_spec.md` |
| Yulehaven Isles | Christmas island Babel (Nordic archipelago) | v1.0 | server-loaded (spawn exposure waived by owner) | `scenes/yulehaven_isles/` (built with `aosmap.kit`), `docs/yulehaven_isles_spec.md` |
| Cursed Skull Reef | pirate island Babel, assist structures (current island style) | v1.0 | server-loaded (spawn exposure fails, owner decision open) | `scenes/cursed_skull_reef/` (built with `aosmap.kit`), `docs/cursed_skull_reef_spec.md` |
| Sprinkler Field | Grounded-scale lawn Babel, assist structures | v1.0 | server-loaded (spawn exposure fails; owner decision pending) | `scenes/sprinkler_field/` (built with `aosmap.kit`), `docs/sprinkler_field_spec.md` |
| Janjira Sound ([recreate] of newfort by JoJoe Stinky) | classic island Babel (Konkan sea forts), 180° rotation | v1.0 | server-loaded (spawn exposure hidden share 0 %, owner decision open) | `scenes/janjira_sound/` (built with `aosmap.kit`), `docs/janjira_sound_recreate_report.md` |

Maps marked "zip from its chat" were built in Claude's sandbox. Their generator code is in the zip delivered in that
chat (links: `docs/knowledge/map_sources.md`). Unpack it under `scenes/<map>/` and `maps/<map>_vN/` to bring them into the repo (see §11 below).

## 11. Working in Claude Code (since 2026-11-09)

* Work happens in `D:\Ace of Spades\Aos_Map` on the owner's Windows PC (DRAGONSPIRE). Use Python 3.11 in a venv with
  `requirements.txt` + `piqueserver==1.4.2`. Shell commands in docs are written bash-style; on Windows use
  `python` from the venv and adjust `cp`/paths.
* Put reference maps in `refs/` (git-ignored). Read them with `aosmap.vxl.read_vxl`.
* **Importing a map from a chat zip:** unzip into `_updates/<map>/` (git-ignored), then move the generator into
  `scenes/<map>/` and the outputs into `maps/<map>_vN/`, run its check script, and update §9's "where the source
  lives" column. Large build artefacts (`mat.npy`, `*.npy`) stay git-ignored.
* **Recording new decisions** `[USER]` (2026-11-10): when the owner states a new preference or rule, append it to
  `docs/knowledge/project_memory.md` (`- [stated] … (date)`) **in the same turn**, on a `docs/<topic>` branch, then
  commit and push. If it's a standing rule, add it to §4 here too. That file replaces the claude.ai Project memory.
* Finish every map with `docs/<map>_spec.md` (status ladder, layout table, validation table, limits, regenerate).
* **Cloud sessions** (claude.ai/code) start without the toolchain: run `uv venv --python 3.11 .venv && . .venv/bin/activate &&
  uv pip install -r requirements.txt` (verified 2026-11-15: piqueserver 1.4.2 builds, tests pass). `refs/` is empty there;
  the owner attaches the maps a job needs.
* **`[recreate]` analysis:** `python tools/recreate_analysis.py refs/<map>.vxl` writes the original-map analysis
  (`out/recreate/<stem>/`); `--compare <new.vxl>` adds the fidelity section. `/recreate` describes the flow and the
  planning/implementation model split (owner, 2026-11-15).
* **Slash commands** (`.claude/commands/`): `/new-map <brief>`, `/recreate <file.vxl>`, `/check-map <maps dir>`,
  `/remember <rule>`, `/sync`. Subagents (`.claude/agents/`): `map-builder` (Opus, generator code) and `map-runner` (Sonnet, checks/export/probe/specs); `/new-map` step 0 picks tier S/M/L and routes stages to them. `/check-map` and `/remember` run on Sonnet, `/sync` on Haiku. `.claude/settings.json` allowlists routine work; force-push and pushes to main are denied.
* **Shared kit** (`aosmap/kit/`, `docs/kit.md`): new maps import codec, canvas, structures, symmetry, colour, veg,
  tag, sky, checks, probe, export and previews from here instead of copying `*_core.py` / `*_check.py`. Old
  generators stay as they are. `tools/kit_acceptance.py` proves the suite reproduces the legacy reports.
* Commit per map version; don't push `refs/` or the rotation-guide PDF.

### Git workflow — keep GitHub up to date, one branch per map `[USER]` (2026-11-10)
The owner wants every Claude session (claude.ai and Claude Code) to keep `https://github.com/shywolf91/Aos_Map`
current at all times. This is standing permission to pull, branch, commit and push for map work.
1. **Before any map work:** `git checkout main && git pull`. Never start from a stale tree.
2. **One branch per map:** `git checkout -b map/<map-slug>` (e.g. `map/under-the-tree`). A new version of an
   existing map gets its own branch too (`map/<map-slug>-v2`). Non-map work (toolchain, docs, setup) uses
   `tooling/<topic>` or `docs/<topic>`.
3. **Commit as you go** — at least after the graybox, after the art pass, and at release — and **push the branch
   after each commit** (`git push -u origin map/<map-slug>`), so the work is never only on one machine.
4. **When the map is released**, open a PR into `main`, then update the §9 catalogue, `docs/<map>_spec.md`,
   `docs/knowledge/project_memory.md` and `docs/knowledge/map_sources.md` on the same branch.
   Merge only when the owner says so.
5. Large build artefacts (`*.npy`) and `refs/` stay git-ignored. If a file is over ~50 MB, ask before committing it.
6. If a push fails (auth, rejected), say so plainly and leave the work committed locally; never force-push `main`.
