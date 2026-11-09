# Bikini Atoll (Detonation) — glow-cloud edit of IAmYourFriend's Push map (2026-10-28)

Request (Dylan): glow blocks only on the nuclear mushroom cloud; darken the surrounding atmosphere/blocks.
Follow-up: v1.1 was "a good start", but the cloud was just a giant fireball. He wants it to **look realistic**, so v1.2 (current) is mostly smoke, with fire only where a real cloud burns.

**Status (v1.2):** generated · exported · parser-validated (own reader round trip; geometry identical to the original, 0 voxels added or removed) · **not** server-loaded · **not** client-inspected · **not** playtested. Views come from a numpy raycaster.

## Original (measured)
* The map is mostly open ocean (water at z 63), with a north island (CPs at y 101) and the spawn ships at y 347.
* Cloud = one connected solid: cap z 0–25 (x 183–319, y 177–297) plus a 29×31 stem (x 234–262, y 219–249) down to the seabed. It is grounded and filled solid. The cap top is flat at z 0, the map ceiling.
* Only the cap's top face had stored colours (a fireball painted from above). The sides and underside had **no stored colour**, so clients render them as default or black. The stem sides were grey (45).
* The water around the stem base had a painted light halo.

## v1.2 cloud (realistic)
* **Smoke** on every surface voxel, from a lighting value:
  * Face term: top 0.80, side 0.55, underside 0.30.
  * Geometric AO: gaussian σ2.5 of solid occupancy, constant-0 boundary so z 0 isn't treated as occluded.
  * Cauliflower billows: domain-warped 3-D Worley noise at two scales, with bright bulge centres and dark creases.
  * Fine fbm on top.
  * Ramp: charcoal → brown-grey → dusty tan → cream.
* **Stem**: dust/condensation column, paler towards the lagoon, with vertical streaks.
* **Fire** (blended over the smoke):
  * strongest on the cap underside near the stem, fading by r ≈ 66;
  * deep folds and creases on the lower cap sides;
  * irregular glow up the stem neck, fading within ~20 voxels below the cap;
  * only faint glimpses in creases on the top centre.
  * Ramp: dark red → red → orange → amber.
* **Glow sources**: 196 on the cloud only (193 orange, 3 yellow), where fire > 0.62, on a jittered 8-voxel grid.
* **Glow light** is baked as hallweeb does: stored + source × 0.32 × (1 − d/6.5). Lit voxels that clamped onto palette colours were nudged by −1, so the only palette-colour voxels are the sources. There are 11 290 stored colours.
* Lessons from v1.1:
  * Red glow (255,95,95) reads as pink specks.
  * Dense sources wash the colours out to white.
  * Plain Worley creases look like cracked mud unless domain-warped.
  * A z-threshold on the stem gives a hard ring.

## Rest of map (unchanged from v1.1)
* Grade × (0.5 + 0.5·0.35·saturation), so team colours keep more brightness. Warm tint (1, 0.86, 0.82).
* Orange blast light falls off with distance from the cloud (55 voxels).
* The water halo within 95 voxels of the stem becomes a fiery reflection. Median non-cloud luminance: 53 → ~33.
* .txt: Push keys unchanged; version 1.2; fog (78,40,38); heavens_color (52,24,26,255); glow_enabled + stored colours.

## Open
* Fog is far darker than the ~150 Dylan found acceptable before; chosen because he explicitly asked for it. Check in client.
* Glow keys do nothing on stock piqueserver, but the light is baked into the VXL, so it still shows there.
* Author line credits IAmYourFriend plus the edit.
* Possible next step (needs geometry changes, not done): a condensation ring/skirt around the stem, and a lumpier top silhouette (the top is capped by the map ceiling).

## Regenerate
`python build.py r5 0.5` (seed 1946) with `vxl.py`. Needs orig.npz (read from BikiniAtoll.vxl) and cloud.npy (the connected component containing (250,236,0), solid z ≤ 60). Second argument = DARK grade. The v1.1 fireball build is kept as build_fireball.py.
