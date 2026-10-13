# Phase 2 — Exporter Validation Report

Date 2026-10-12 · Python 3.11.17 · piqueserver 1.4.2 · package `aosmap` 0.1.0 · scene seed 7501.
Source-verified rules are in `vxl_and_runtime_reference.md`. Nothing here is playtested.

## Status of the diagnostic scene

| Stage | Result |
|---|---|
| generated | ✔ deterministic: rebuilding from scratch gives identical bytes (sha256 c5a22fe8…a5b6, 2,123,896 B) |
| exported | ✔ `aosmap_diagnostic.vxl` + `.txt` |
| parser-validated | ✔ own strict reader: 0 issues · pyspades 1.4.2 loads and regenerates **byte-identical** · D-VXLMapPreview (independent D reader) decodes and renders it |
| server-loaded | ✔ piqueserver 1.4.2 headless, `ctf` with `user_blocks_only = true`, and `arena` (gates constructed without error) |
| network transfer | ✔ map downloaded over ENet by a minimal 0.75 client is byte-identical to the file |
| client-inspected | partial — user reports the map **loads in their spectator web client** (2026-10-12); not yet inspected in OpenSpades / BetterSpades / 0.75 |
| playtested | ✘ |

## Exporter vs real maps (36 files = 34 distinct maps)

remus was uploaded twice, and ga_gardens_japan / GoonassaultJapan are byte-identical files.
All 36 pass: strict decode, **our re-encode == pyspades `generate()` byte-for-byte** (colours and shade byte included), identical occupancy and surface colours after a pyspades round-trip. 22 files are already in canonical pyspades form; the other 14 come from other editors (some store colours on hidden voxels — harmless).
Quirk found: 10yearsaloha has 512 all-air "void" columns (incl. z=63); the writer reproduces them with `force_bottom=False`, and forces z=63 solid by default.

## Runtime checks — real piqueserver 1.4.2 code run on the exported file

| Check | Result | Meaning |
|---|---|---|
| `check_node` floating slab / diagonal-contact block / pillar | 9 / 1 / 0 | 6-face grounding confirmed; edge contact is floating |
| Player block under authored floating slab, then destroyed | 10 voxels removed, slab gone | **Collapse bypasses protection** → ground all authored geometry |
| One pillar voxel vs full pillar layer removed | 1 vs 287 (roof gone) | redundancy matters only where authored blocks are destructible |
| Arena `Gate` A (1 thick) | 40 selected, opening clear | correct |
| Arena `Gate` B (same-colour pot touching) | 41 selected | decoration absorbed into gate |
| Arena `Gate` C (3 thick) | 40 of 120 selected, **80 remain** | thick gates never open — validator now flags this |
| Push colour test: (0,0,120) swatch | counted as blue team block | palette lint warns |
| `.txt` import + piqueserver `Map()` loader | ✔ hooks and extensions read | |

Static validator: 0 errors; 18/18 spawns have floor + 3-voxel headroom.

## Things this phase corrected

* Phase 1 "4th colour byte: unknown" → cosmetic; both open clients discard it.
* Phase 1 "user_blocks_only: verify name" → exists, works, but has no team ownership and grenades fail near any authored voxel.
* Phase 1 "default spawn regions asymmetric (0–256 / 384–512)" → 1.4.2 uses 0–127 / 384–511 symmetric.
* My own prediction for gate C (80 selected) was wrong; real result 40.

## Not verified / next

1. Client inspection in OpenSpades and BetterSpades (and vanilla 0.75 if available): edge islet faces, floating slab, colours, ledge/tunnel/drop figures.
2. Movement figures (jump 1.6, fall 10/20) are derived; confirm on the course in the scene.
3. Team-ownership protection (user's preferred policy) needs a small script on top of `user_blocks_only`; grenade behaviour near authored blocks must be decided.
4. Material colouring: per-voxel jitter reads as stipple; replace with structured variation before art work.

## Addendum (2026-10-12, later)

* Floating pieces are now **opt-in** (user preference): unlisted floating components are errors; requested ones are reported with a collapse-risk warning.
* New checks: `check_push()` (required keys, spawn squares, intel/CP settling under roofs, team-colour clashes) and `check_babel()` (platform volume, spawn zones, spawn symmetry; platform constants are parameters for modded servers). Both were exercised: deliberately bad Push coordinates on the diagnostic map were all caught; good ones passed.
* Entity settling verified with pyspades on the diagnostic map: an entity dropped above the roof slab rests on the roof (z=46), not the floor (z=58).
* Cloud Smash analysed and server-loaded (see reference doc §7). `Scene.paint_bottom()` added and tested (8/8 tests pass).
