# Claim 4 — "Identical backgrounds = a painted backdrop"

> *"Two Apollo 15 photos supposedly taken at different locations show IDENTICAL
> mountain backgrounds — one even has the Lunar Module missing! Clearly the same
> painted backdrop a few meters behind the actors, reused between takes."*

This is one of the oldest exhibits in the hoax literature (aired in Fox TV's
*Did We Land on the Moon?*, 2001, and pushed by Aulis/David Percy). The pair is
**AS15-82-11057** (LM in the foreground) and **AS15-82-11082** (no LM, boulder
field in the foreground), both showing the same mountain skyline at
Hadley–Apennine.

The claim is quantitatively testable, because a backdrop a few meters behind
the actors and a mountain range kilometers away behave completely differently
when the camera moves.

## Falsification criterion

We would **support** the backdrop claim if we measured:

* effectively **zero parallax** on the supposedly-distant background across a
  large camera baseline (no apparent-size change *and* no internal geometry
  change), or
* internal-geometry behavior inconsistent with rigid distant terrain — e.g. the
  entire "mountain" moving as one flat sheet (a plane maps between any two
  camera positions as an **exact homography** with zero internal depth
  parallax).

We **refute** it if the background shows exactly the small, layered,
distance-consistent parallax that real terrain kilometers away must show, while
the foregrounds share nothing.

## Data provenance

| frame | station (ALSJ caption) | time (GET) |
|---|---|---|
| AS15-82-11057 | "up-Sun picture of the LM … from a pan Jim took at the **ALSEP site** at the start of EVA-3" (Station 8, ~125 m NW of the LM) | 164:26:56 |
| AS15-82-11082 | frame from "**Dave's Station 9 pan**" (Station 9, ~1400 m W of the LM, by Hadley Rille) | 165:05:09 |
| AS15-82-11081 | frame immediately before 11082 in the **same Station 9 pan** (control) | 165:05:09 |

Scans: ALSJ high-resolution JPEGs (2340×2355 px, full 55 mm frame), fetched
from Wayback Machine snapshots of `hq.nasa.gov/alsj/a15/` (URLs pinned in
`run.py`; SHA-256 logged at fetch). Captions: ALSJ *Apollo 15 Map and Image
Library* (archived copy cached in `data/`). Station separation ≈ **1315 m**.
Hoax-debunk literature (moonhoaxdebunked.com §5.12) annotates the visible
ranges at ~5/14/21 km.

Camera model: Hasselblad 500EL, Zeiss Biogon 60 mm, 55 mm square frame →
49.2° FOV, 44.6 px/deg at frame center.

The line of sight is anchored by documented physics: ALSJ calls 11057
"up-Sun", and advancing the documented landing sun elevation (12° at GET
104:42) at the lunar synodic rate puts the sun at el 38.5°, **az 112°** at the
pan time. The Station 8→9 baseline (az 266°) then decomposes into **~1180 m
radial** (Station 9 farther from the mountains) and **~570 m transverse**
(both ±~10 % over the ±8° pointing uncertainty we carry).

## Method (`run.py`)

1. **Reseau masking.** The Hasselblad reseau plate prints the same 5×5 cross
   grid on every frame at fixed *film* positions. Left in place, crosses (and
   the frame border) generate false "zero-motion" matches between any two
   Apollo frames — biasing the test *toward* the hoax conclusion. We detect
   them by template matching, snap to the lattice, and inpaint; near-zero-
   displacement matches are also rejected.
2. **SIFT + ratio test + RANSAC** (`cv2.SIFT_create`, Lowe 0.8, similarity
   model) on the mountain band and, separately, the foreground band.
3. **Dense verification**: iterative alignment (warp → normalized
   cross-correlation of 96 px patches on a 32–40 px grid → robust similarity
   refit, 3 rounds), then a final displacement field with subpixel peaks.
   Patches must pass a structure-tensor check (corner-like texture) so
   correlation cannot slide along the skyline edge, plus a neighborhood
   coherence filter.
4. **Models**: global similarity (scale = apparent-size ratio), full
   homography (= any flat backdrop under any camera rotation), k-means layer
   decomposition of the residuals.
5. **Control**: the identical pipeline on 11081 vs 11082 — two frames of the
   *same* pan from the *same* station seconds apart, i.e. zero baseline. Any
   "parallax" the pipeline finds there is pipeline artifact, not depth.

## RESULTS

**The two backgrounds are the same real massif** — 396 ratio-test SIFT
matches, of which 17 strict inliers lock the mountain bands together
(RMS 2.9 px), verified densely by 114 coherent NCC points (correlations up to
0.97). **The foregrounds share nothing**: 68 scattered candidate "matches",
best mutually-consistent subset = 3 (chance level; see `fig1`, red lines).

**Observable 1 — apparent size.** The mountains are **3.5–9.5 % smaller** in
11082 than in 11057 (similarity scale 0.9587; homography center-magnification
0.911; range brackets both estimators ± RANSAC spread). Real terrain at
distance D seen after retreating b_r ≈ 1.18 km shrinks by b_r/(D+b_r):

* measured 3.5–9.5 % → **D ≈ 10–34 km** — bracketing the documented 14–21 km
  ranges of the Apennine front;
* a **backdrop at 30 m** would predict **97.5 %** (the mountain would be ~40×
  larger from Station 8). Measured parallax excludes it by **≥ 345× in
  distance**.

**Observable 2 — internal depth structure.** After the best rigid alignment,
the background does *not* move as one sheet: it decomposes into coherent
layers (fig3) spanning **1.05°** of differential parallax
(−0.19° / +0.86° / +1.49°), with the *near* lower slopes displaced opposite to
the camera motion and the ridge seen through the saddle displaced with it —
the correct sign ordering for real depth. Solving each layer with the
transverse baseline gives ~15 km (near slopes), ~27 km (main range), ≳50 km
(far ridge in the saddle). Even allowing the camera ANY rotation and the scene
to be ANY flat sheet (full homography fit), **13.9 px RMS (0.31°) of layered
residual survives** (35.7 px layer spread).

**Control (same station, zero baseline):** homography residual **3.0 px**
(≈ the measurement noise floor), layer spread 7.4 px, similarity scale 1.017.
The depth structure appears **only** when the camera actually moves
(fig5) — it is not film, scanner, lens, or pipeline artifact.

**Conservative bound needing no documents:** the LM standing ~10 m from the
11057 camera is absent from 11082 and zero foreground is shared, so the camera
moved ≥ ~30 m no matter whose story you believe. Even then
D ≥ b·s/(1−s) ≈ **285 m** — an order of magnitude beyond "a few meters behind
the actors". With the documented 1.3 km traverse the background sits at
10–34 km.

| metric | cross-station pair (b = 1315 m) | same-station control (b = 0) |
|---|---|---|
| similarity scale | 0.9587 (mountains shrink) | 1.0167 |
| homography residual RMS | **13.9 px (0.31°)** | 3.0 px (0.07°) |
| residual layer spread | **35.7 px** | 7.4 px |
| foreground shared | nothing (3/68 = chance) | (same scene) |

### Figures

* `results/fig1_pair_matches.png` — the pair with SIFT matches: green =
  background inliers; red = foreground "matches" (random criss-cross).
* `results/fig2_aligned_difference.png`, `results/blink_aligned.gif` — the
  "identical" backgrounds aligned and blinked: same mountains, LM present in
  one, gone in the other, foregrounds unrelated.
* `results/fig3_parallax_field.png` — residual displacement field: the three
  depth layers of the massif.
* `results/fig4_exclusion.png` — the exclusion plot: measured size change vs
  background distance; backdrop at 10–50 m sits at 96–99 %, measurement sits
  at 10–34 km.
* `results/fig5_control_same_station.png` — the depth test with its control:
  homography residuals for the 1.3 km pair (structured) vs the 0 m pair
  (nothing).

## Limitations

* The station coordinates (125 m NW; 1400 m W of the LM) come from
  ALSJ-derived literature; we did not re-derive them from LROC imagery. The
  ±8° line-of-sight uncertainty and both scale estimators are propagated into
  every quoted range, and the *conservative* 285 m bound uses no station data
  at all.
* The similarity "scale" partially mixes with projective distortion from the
  different camera pointing; that is why we bracket it with the homography
  center-magnification (0.911–0.959) rather than quoting one number.
* A perfect *scaled 3-D miniature* of the massif is projectively
  indistinguishable from the real thing in a single pair — but it would have
  to be a miniature mountain range with kilometer-equivalent layered depth,
  matched to LRO topography, not the claimed flat backdrop; and the
  centimeter-detailed foreground (bootprints, rover tracks, 15 m crater
  ejecta) breaks the scaling.
* NCC layer decomposition is k-means with k=3; the true scene is a depth
  continuum. The layer distances (15/27/≳50 km) are indicative; the exclusion
  argument uses only the robust size-change and the existence of nonzero
  layered parallax.

## Verdict: **REFUTED**

The "identical background" is identical in exactly the way an 11–30 km distant
mountain range must be, and different in exactly the way a painted backdrop
cannot be: it shrinks 3.5–9.5 % across the documented 1.3 km station
separation, carries ~1° of internally layered depth parallax with the correct
sign structure, and shares zero foreground. The measured parallax bound puts
the background at ≥ 10 km — at least **345×** farther than any studio wall —
while the same pipeline on a same-station pair finds nothing. "Same background
+ different foreground" is the signature of *real distant terrain*, and it is
the strongest possible photographic evidence *against* a backdrop.

## Reproduce

```bash
../../.venv/bin/python run.py          # cached stages
../../.venv/bin/python run.py --force  # recompute everything
```
