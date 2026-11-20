# [recreate] report — Arctic Icebreaker → Floebreaker

## Original
| | |
|---|---|
| File | `arctic_icebreaker.vxl` (uploaded; a copy is kept untracked in `work/arctic_icebreaker/original/` and not pushed) |
| SHA-256 | `def76bbc76429b1cb3488e00af449ace0cd6899e6de6f96c0b3ca2f3c258ccf4`, 2,300,900 bytes |
| Author / `.txt` | unknown; no `.txt` supplied, so its mode, fog and extensions are `[OPEN]` |
| Parse | 512×512×64, no read issues, one connected piece, no floating parts, solid to the bottom |

## Map DNA `[RUN]`
* A polar island (46 % land, plain at z 57–61) with a grounded icebreaker E–W across the centre (x 168–286, y 234–273, up to z 3, ~47 high), two team bases N and S (y ≈ 150 / 360, blue and green markers) and ~10 faceted icebergs in the sea.
* Symmetry: ~95 % voxel match under both mirrors (the sea), but only ~51 % on height. The island itself is not mirrored.
* Mode (measured, not assumed): not Babel as built. The ship tops out at z 3 inside the platform zone, land sits under the platform footprint, the spawn squares are uneven (blue z 58–63, red z 39–63) and the bases are N/S. It reads as CTF or TC.
* Art: 45 % of surface columns have a max channel ≥ 235 (too white); land mean ≈ (229, 237, 246); 812 distinct surface colours; contour-line noise on the ice; few props.

## Element ledger
| element | verdict | note |
|---|---|---|
| Icebreaker | **Keep, rebuild** | now N–S and ≥ 60 from the platform; hollow with real decks, stairs, doors, windows, glow |
| Two bases N/S | **Reimagine** | Babel bases at x 118 / 394 with open fronts and base camps behind |
| Iceberg ring | **Keep** | faceted hex cones, ~38, kept clear of the corner tag |
| Island shape | **Reimagine** | similar footprint, mirrored, solid down, walkable shore ramps |
| White snow | **Replace** | lilac / pearl / mint snow capped at 212, glacier-blue ice, rock, lichen |
| Props and centre | **Add** | camps, towers, whale skeleton, ice caves, crevasses, ponds, penguins, crystals |
| Sea | **Keep** | gradient from cyan shallows to deep blue, painted on the seabed |

## Owner's choices
Depth **Reimagine**; mode **Babel**; two versions, **Day and Night**; name left to Claude (Floebreaker); sky decor in both; ship hollow with glow inside both; boundary damage instead of water damage (his example `.txt` confirmed it is a stock key); fog, unique objects and artistic direction left to Claude; corner tag bottom-right.

## Fidelity (Reimagine: traceable, not close)
| measure | original | Floebreaker |
|---|---|---|
| land share | 46 % | 54.7 % |
| land-mask overlap (IoU) | | 0.55 |
| height correlation | | ≈ 0.05 (new layout by design) |
| x-mirror height equality | 51 % | 84 % (ship and props are deliberate asymmetries) |
| ship | E–W, centre, ~47 high | N–S, north half, 10 hull + 28 superstructure |
| columns with max channel ≥ 235 | 45 % | 1.1 % (glow-lit voxels; snow capped at 212, ice at 224) |

## Problem ledger
| problem | status |
|---|---|
| too white | **fixed**: capped at 212, varied hues |
| ship inside the platform zone | **fixed**: moved ≥ 60 away |
| uneven spawn squares, land under the platform | **fixed**: ±1 mounds, anchors solid |
| solid or unexplored ship | **fixed**: all floors reachable (graph model) |
| sparse props, flat ice | **improved**: ~7 object families, caves, ponds, crevasses |
| unknown mode and metadata | **resolved by choice**: Babel, new `.txt` |
| spawn exposure | **fixed with a trade-off**: 3.8 viewers, 35–37 % hidden, via two declared tall fins; see spec, known limits |
| bare spawn-to-tower front (2026-11-13 rules) | **fixed**: dressed front, backdrop, low objects under the platform; all four zone rules pass |

## Credit
Based on `arctic_icebreaker.vxl` by its original, unidentified author. The `.txt` description says so; the `author` field stays `'shywolf91 + AI'`.
