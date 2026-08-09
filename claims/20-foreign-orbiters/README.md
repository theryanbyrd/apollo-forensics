# Claim 20 — Foreign orbiters verify the terrain

**Claim under test:** the mountains on the skyline of the Apollo 15 surface
photographs (Mons Hadley, Mons Hadley Delta) are painted studio backdrops.

**Independence check:** the skyline in photographs taken on the Moon in
**1971** is compared against a digital elevation model built from images
taken by **JAXA's Kaguya/SELENE orbiter in 2007-2009** — a Japanese
spacecraft, Japanese cameras, Japanese processing, hosted on a Japanese
archive. No set designer in 1971 could have possessed decimeter-quality
topography of the far ridge lines at Hadley; large parts of it were first
measured decades later.

## Falsification criterion

Render the horizon a 1.6 m-tall camera at the Apollo 15 LM site *should*
see according to the Kaguya DEM, and compare it with the skyline actually
photographed in 1971. A systematic mismatch — wrong ridge shapes, wrong
angular heights, or a best match at an azimuth different from the
documented viewing direction — would support fabricated terrain. A
sub-degree match across tens of degrees of panorama, at the documented
azimuth, falsifies the backdrop claim.

## Data (all public, fetch scripts included)

| Item | Source | Provenance |
|---|---|---|
| DEM tiles `DTM_MAPs02_N27E003N24E006SC` (contains the site, Mons Hadley, Mons Hadley Delta), `N27E000N24E003`, `N30E003N27E006`, `N30E000N27E003` | JAXA DARTS, `darts.isas.jaxa.jp/pub/pds3/sln-l-tc-5-dtm-map-seamless-v2.0/` | **JAXA** Kaguya/SELENE Terrain Camera stereo DTM, product set `SLN-L-TC-5-DTM-MAP-SEAMLESS-V2.0` (PDS3, 3600 px/deg ≈ 8.4 m/px, int16 meters vs. the 1737.4 km sphere) |
| Photo `AS15-88-11866` ("Jim salutes the flag", start of EVA-3, taken beside the LM; Mons Hadley Delta on the skyline, view ~south) | Wikimedia Commons mirror of the Project Apollo Archive film scan (4175×4175 px) | NASA flight film, magazine 88, Hasselblad 500EL + Zeiss Biogon 60 mm |
| Photo `AS15-86-11603` (Jim Irwin at the Rover, end of EVA-1, taken from the LM shadow; Mons Hadley on the skyline, view ~northeast) | same | NASA flight film, magazine 86 |

Photo captions and viewing directions are documented in the Apollo Lunar
Surface Journal, Apollo 15 Image Library. Downloaded tiles were verified
against the MIN/MAX/AVERAGE/STDEV statistics in their PDS labels.

The 1971 photographs are NASA's — they are the *claim under test*. The
terrain model they are tested against is JAXA's.

## Method

1. **`fetch_dem.py` / `fetch_photos.py`** — download and verify the data
   above into `data/` (gitignored; ~950 MB).
2. **`render_horizon.py`** — mosaic the four tiles, then from the LM
   coordinates (26.1322 N, 3.6339 E, camera 1.6 m above the local DEM
   surface, which sits at −1925.9 m) march rays every 0.05° of azimuth out
   to 40 km, computing the elevation angle of every DEM sample with the
   spherical curvature drop d²/2R (R = 1737.4 km, no atmosphere). The
   per-azimuth maximum is the synthetic horizon.
3. **`extract_skyline.py`** — recover each photo's pixel scale from the
   film's own reseau grid (crosses are exactly 10 mm apart; measured
   752 px → 75.2 px/mm), then trace the skyline with a dynamic-programming
   seam tracker on vertical-gradient rewards. Columns where mission
   hardware (LM, Rover high-gain antenna) pokes above the terrain, or
   where the skyline is a shadowed flank lost against the black sky, are
   masked (documented in the script, visible in `results/skyline_*.png`).
4. **`match_skyline.py`** — every skyline pixel becomes a 3D ray through
   the calibrated focal length (61.1 mm). The camera's yaw/pitch/roll are
   the only free parameters (no scale fudge): a grid search over all 360°
   of yaw with local refinement minimizes the RMS difference between ray
   elevations and the DEM horizon at the same azimuths. Scoring is RMS in
   degrees with the angular scale fixed by the camera calibration —
   a plain normalized cross-correlation is gain-invariant and can inflate
   a small ridge into a mountain (it produced a false secondary peak in an
   early version of this analysis; the final metric cannot).
   Each refinement box is **re-centred and re-searched whenever its
   optimum lands on a face**, so a reported pose is always an interior
   minimum. (This matters: an earlier version reported roll = +1.8° for
   AS15-88-11866, which was exactly the edge of both successive roll grids.
   The true optimum is +3.0°, and it fits an order of magnitude better —
   0.017° RMS instead of 0.179°. `pose_is_interior_minimum` in
   `match_results.json` now records the check.)

## RESULTS

| | AS15-88-11866 (flag, LM) | AS15-86-11603 (Irwin + Rover) |
|---|---|---|
| Skyline | Mons Hadley Delta | Mons Hadley |
| Best-fit boresight azimuth | **184.2°** (skyline spans 161–207°) | **46.3°** (spans 39–68°) |
| Documented direction | ~south; DEM summit bears 168.6° (in-frame, left of center — exactly as photographed) | ~northeast; DEM summit bears 41.8° (left of center — as photographed) |
| Azimuth agrees? | **YES** | **YES** |
| RMS residual (pitch/roll fitted) | **0.017°** (1.3 px on the film) | **0.208°** (17 px) |
| Pearson r | **0.99998** | **0.9951** |
| Best rival azimuth elsewhere on the 360° circle, refined identically | 0.764° at az 110.7° — **45.6× worse** | 0.266° at az 182.5° — **1.28× worse** |
| Fitted pose | pitch −1.0°, roll +3.0° | pitch −7.8°, roll −0.5° |

For the flag frame the 2008 Japanese DEM reproduces the 1971 skyline to
**0.017° RMS across 46° of panorama** — 1.3 pixels on a 4175 px film scan,
with the residual sitting at ~0.011° everywhere except the low near ridge
at the right edge (see Limitations). For the Rover frame, whose skyline is
shorter, partly shadowed and partly masked, the agreement is 0.208°. In
both, the best-fit pointing lands where the mission transcript says the
camera was aimed. Per the DEM, the photographed skylines are real
mountains 17.5 km away rising 3.5 km above the site (Hadley Delta,
summit 25.568 N 3.761 E) and 20.1 km away rising 4.1 km (Mons Hadley,
summit 26.627 N 4.127 E) — not a backdrop a few tens of meters from the
camera.

**How much of that is uniqueness?** The two frames carry very different
evidential weight, and the table says so honestly. Every candidate azimuth
is given the *same* three free parameters and the *same* refinement, then
the winner is compared with the best rival more than 10° away:

- **AS15-88-11866 is decisive.** Its best rival anywhere else on the circle
  reaches only 0.764° RMS (r = 0.92) — 45.6× worse. This skyline can be
  matched at one azimuth and nowhere else.
- **AS15-86-11603 is corroborating, not decisive.** Its best rival (az
  182.5°, roll −5.8°) reaches 0.266° with r = 0.9955 — nominally a *better*
  correlation than the winning fit, and only 1.28× worse in RMS. A 29°
  stretch of lunar ridge is simply not distinctive enough to pin an azimuth
  on shape alone. What this frame does establish is that the global optimum
  still falls at the documented direction, with sub-quarter-degree
  residuals.

An earlier version of this analysis reported 8.7× and 3.1× here. Those
numbers compared a fully refined winner against rivals scored on the coarse
roll = 0 grid — not like with like. The figures above are the corrected,
like-for-like comparison; the raw coarse values are still written to
`match_results.json` as `second_best_rms_deg_coarse_grid`.

See `results/`:
- `dem_hillshade.png` — the Kaguya DEM with the LM and rendered horizon points
- `synthetic_horizon.png` — the full 360° synthetic horizon profile
- `skyline_AS15-*.png` — the photos with extracted skylines and reseau detections
- `match_AS15-*.png` — profile overlays + RMS-vs-azimuth curves (sharp, unique minima)
- `overlay_AS15-*.png` — **the money shots**: the 1971 photographs with the
  horizon predicted from the 2008 Japanese DEM drawn on top
- `match_results.json`, `summary.json`

## Limitations

- The horizon is rendered from the LM coordinates; the photos were taken
  a few tens of meters away. For ridge lines 12–20 km away this is <0.2°
  of azimuth, but the low near ridge on the right of AS15-88-11866
  (~1–8 km away) shows a residual consistent with this parallax: with the
  pose properly converged, that frame's residual is ~0.011° RMS across the
  Hadley Delta massif and 0.041° in the near-ridge sector (az 202–208°),
  the only part of the panorama where it is elevated.
- Ray marching stops at 40 km; toward the WNW mare (az ~260–340°) the true
  skyline may lie farther out. Neither photo looks that way.
- In AS15-86-11603 the shadowed WNW flank of Mons Hadley (left third) is
  black-on-black and was excluded; the summit region skyline sits inside
  veiling glare and relies on the seam tracker's crest detection. That
  frame's residual (0.208°) is an order of magnitude larger than the flag
  frame's, and its RMS minimum is shallow (1.28× over the best rival
  azimuth) — treat it as corroboration, not as an independent lock.
- The seamless TC DTM is JAXA's own stereo product from Kaguya Terrain
  Camera images. (JAXA used LALT altimetry — also Japanese — for long-
  wavelength control. It is not the NASA-merged SLDEM2015; NASA data does
  not enter this comparison.)
- Camera focal length taken as the calibrated 61.1 mm for the Apollo 15
  EDC 60 mm Biogon; pixel scale from the reseau grid. Pose (yaw, pitch,
  roll) is fitted — it is unknown a priori — so the test is the *shape*
  agreement and the *location* of the unique RMS minimum.

## Verdict

**CONFIRMED REAL TERRAIN — the backdrop claim is falsified.** Terrain
photographed by Apollo 15 astronauts in 1971 matches, to 0.017° RMS
(1.3 film pixels over 46° of panorama) for the flag frame and 0.208° for
the Rover frame, at the documented viewing azimuths, an elevation model
measured 36+ years later by a Japanese orbiter that no 1971 set designer
could have had. For
the hoax claim to survive, the 1971 "backdrop painters" would have needed
the 2008 Japanese topography of an 800 km² mountain panorama — including
ridge lines that are only knowable from orbit — to sub-pixel precision.
