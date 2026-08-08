# Claim 01 — "Non-parallel shadows prove studio lighting"

**Verdict: REFUTED.** The claim rests on a geometry error (the fence-post
fallacy). Measured rigorously, the shadows in the two most-cited "problem"
photos behave exactly as a single sun at infinity requires — down to the
sun's ephemeris elevation at the documented minute of exposure.

---

## 1. The claim, steelmanned

Hoax proponents observe that in many Apollo surface photographs the 2D
directions of different shadows differ by tens of degrees, and argue:

> Sunlight arrives in parallel rays, so all shadows on the Moon must be
> parallel. Shadows pointing in visibly different directions mean multiple
> nearby light sources — i.e., studio lamps on a soundstage.

This argument appears in Bill Kaysing's *We Never Went to the Moon* (1976),
is developed at length by David Percy and Mary Bennett (*Dark Moon*, 1999,
and the video *What Happened on the Moon?*, 2000), and reached its widest
audience in the Fox TV special *Conspiracy Theory: Did We Land on the
Moon?* (2001). Frames like the two analyzed here — a distant LM with
foreground boulders whose long shadows visibly "diverge" (Apollo 14), and
the down-sun view with the photographer's giant shadow (Apollo 11) — are
standard exhibits.

Steelmanned, the claim makes a **testable geometric prediction**, which is
what makes this analysis possible: if the light were a lamp at studio
distance (meters to tens of meters), shadow geometry on the ground encodes
the lamp's *position*, not just its direction.

## 2. Why the naive version is a fallacy — and what the rigorous test is

Shadows of vertical objects lie along **parallel horizontal lines** on the
ground (for one distant source). A camera projects parallel 3D lines into
2D lines that **converge at a vanishing point** — they are parallel in the
world and *non-parallel on film*. Anyone who has photographed a fence at
sunset has seen this. Measuring 2D angle differences between shadows and
declaring them "non-parallel" is exactly as meaningful as declaring that
railroad tracks meet.

The rigorous, falsifiable test is **where the shadow lines converge**:

| Hypothesis | Prediction |
|---|---|
| **Sun at infinity** | All shadow ground-lines pass through **one** vanishing point that lies **on the horizon** (the ground plane's vanishing line); all object-top→shadow-tip lines pass through the image of the sun (or antisolar) direction, offset from the horizon point by exactly the sun's **elevation** — which is independently known from the ephemeris. |
| **Studio lamp (5–20 m)** | Shadow ground-lines converge at the image of the **lamp's foot point** — a point measurably **below** the horizon (by `atan(camera height / lamp distance)` ≈ 4–16°); shadow directions of near vs far objects imply wildly different "elevations". Bonus: a *second* light source would give every object two shadows; no Apollo photo shows that. |

Both hypotheses are fit to the same measurements and compared by χ²/AIC.
`results/fig1_synthetic_demonstrator.png` proves the method discriminates:
a synthetic sun scene shows ~50° of 2D "non-parallelism" with perfect
concurrency on the horizon, while a synthetic lamp at 8 m puts the
convergence point 11.6° below the horizon.

## 3. Data

Two famous frames, chosen because hoax sites use exactly this genre of
image, and because they have opposite geometry (one up-sun, one down-sun —
methodological independence):

| Frame | Scene | Documented time | Source |
|---|---|---|---|
| **AS14-68-9487** | Station H pan toward the LM *Antares*; foreground boulders with long "diverging" shadows, Shepard and the LM ~100 m away | GET 135:01:56 → **1971-02-06 12:04:58 UTC** (launch 1971-01-31 21:03:02 UTC) | LPI Apollo Image Atlas print scan, 3900×3900 (`data/`, re-fetched by `run.py`) |
| **AS11-40-5961** | Armstrong's down-sun shot from the rim of Little West Crater: his own shadow, the LM, flag, TV camera, SWC staff | GET 111:11:31 → **1969-07-21 04:43:31 UTC** (launch 1969-07-16 13:32:00 UTC) | LPI Apollo Image Atlas print scan, 3900×3900 |

Frame times and scene identifications are from the Apollo Lunar Surface
Journal image libraries (captions quoted in the `annotations_*.json`
files). Landing-site coordinates: Fra Mauro 3.64544°S 17.47139°W;
Tranquility Base 0.67408°N 23.47297°E.

**Digitization.** Every measured coordinate was read by eye from
labeled-grid crops of the full-resolution scans rendered with
`digitize_helper.py`, and recorded with per-point 1σ uncertainties in
`annotations_AS14-68-9487.json` (8 shadow lines + 6 top→tip lines +
15 horizon points) and `annotations_AS11-40-5961.json` (5 shadow lines +
3 top→tip lines + 13 horizon points + the antisolar anchor). Ambiguous
features were either skipped (the Gold camera's rod shadow, the flag
shadow entangled with LM strut shadows) or flagged with inflated σ
(Shepard's shadow tip; Armstrong's crater-bent shadow axis) — the JSON
notes say why, line by line.

**Camera calibration — no assumptions needed.** Apollo surface Hasselblads
exposed every frame through a reseau plate: crosses etched at exactly
10 mm spacing. `reseau.py` template-matches the crosses (22 found in the
A14 scan, 8 in the A11 scan; grid-fit residuals 0.7 px and 0.4 px), giving
the scan scale (74.22 px/mm — both scans) and the principal point (central
cross). With the EDC's calibrated 61.1 mm focal length this turns pixels
into angles: f = 4535 px, and the whole analysis becomes metric.

**A geometric gift in AS11-40-5961:** the frame contains the shadow of the
*camera that took it* (on Armstrong's chest). The image of the taking
camera's own shadow is *exactly* the antisolar vanishing point — every
point of the antisolar ray through the lens projects to that one pixel —
**independent of the terrain the shadow falls on**. That single feature
anchors the sun's elevation with no assumptions about ground slope.

## 4. Analysis

`run.py` (everything is reproduced by `../../.venv/bin/python run.py`):

1. Downloads the scans and the JPL Horizons ephemerides if absent
   (cached responses in `data/horizons_*.txt`).
2. Detects the reseau grid → pixel scale + principal point.
3. Fits both models to the digitized lines:
   - **H_sun** (2 parameters): a vanishing point constrained to the fitted
     horizon line + an elevation angle placing the source point on the
     same vertical circle. Residual = perpendicular miss distance of each
     shadow tip, weighted by its σ (digitization ⊕ terrain term of
     4–5 % of line length ⊕ flagged extras).
   - **H_lamp** (4 parameters): fully free ground-convergence point + free
     source-image point. Deliberately generous: it contains H_sun as a
     special case and is not even required to keep the lamp vertically
     above its foot.
4. Monte-Carlo (800 refits): every endpoint, horizon point (with
   correlated offset + tilt systematics), principal point, and camera
   height re-drawn from its uncertainty.
5. Compares the fitted sun elevation with JPL Horizons for the documented
   site and second.

## 5. Results

Numbers below are from `results/summary.json` (regenerated on every run).

### Concurrency — the "multiple lights" claim dies here

| Frame | lines | χ²/dof (H_sun) | ΔAIC (lamp − sun) |
|---|---|---|---|
| AS14-68-9487 | 8 shadow + 6 top→tip | **1.38** | **+0.14** (lamp worse) |
| AS11-40-5961 | 5 shadow + 3 top→tip + anchor | **1.36** | **−0.04** (tie) |

Every shadow line in both frames passes through a *single* convergence
point to within its measurement uncertainty. The 4-parameter lamp model
buys essentially zero χ² over the 2-parameter sun model — by parsimony
(AIC) the extra "nearby source position" freedom is useless. There is
nothing here for a second light source to explain. (And no object in
either frame casts two shadows.)

### Where the convergence point sits — sun vs lamp

The free-fit convergence point lands **on the horizon** in both frames
(A14: 2.3° ± 6.8° above; A11: 2.0° ± 1.5° above — a physical lamp foot
must sit *below* the horizon by atan(h/D)):

- **AS11-40-5961**: 91 % of Monte-Carlo solutions put the convergence at
  or above the horizon (i.e., source at infinity); the 95 % lower bound on
  the implied source distance is **≈ 54 m**. A lamp 5–20 m away (4–16°
  below the horizon) is excluded outright — see
  `results/fig3_montecarlo_source_distance.png`.
- **AS14-68-9487**: same story but weaker leverage (the vanishing point is
  far outside the frame and the Fra Mauro skyline is rolling ridge
  terrain, not a sharp horizon): implied source distance ≥ ~9 m at 95 %.
  The A14 frame's sharp tests are concurrency (above) and azimuth (below).

### The ephemeris cross-check

JPL Horizons, sun seen from the landing sites at the documented seconds:

| Frame | Horizons az / el | Fitted elevation | Δ |
|---|---|---|---|
| AS11-40-5961 (down-sun) | 88.84° / **15.00°** | **15.7° ± 1.1°** | **+0.7° (0.6 σ)** |
| AS14-68-9487 (up-sun) | 88.59° / **23.87°** | 11.7° ± 2.7° (formal); per-object solutions span 5°–36° | consistent, but weak (see below) |

- **Apollo 11:** the elevation recovered from shadow geometry alone —
  including Armstrong's own camera shadow as the antisolar anchor —
  matches the astronomical almanac value for 04:43:31 UTC on 21 July 1969
  to better than a degree. The three independent per-object solutions
  (SWC staff 16.6°, TV camera 16.5°, foreground rock 15.9°) agree with
  each other, which is itself the parallel-ray test: a lamp at studio
  distance would make near and far objects imply very different angles.
- **Apollo 14:** an honest negative lesson about up-sun geometry: the
  top→tip lines run nearly parallel to the shadow lines, so the elevation
  lever arm is tiny and rough-terrain truncation of shadow tips dominates
  (single-object solutions scatter from 5° to 36°, bracketing the
  ephemeris value; the formal MC error underestimates this systematic —
  both are shown in `results/fig4_elevation_vs_ephemeris.png`). The frame
  still delivers its azimuth check: the fitted vanishing point sits
  45.7° ± 4.1° left of the frame axis, which with the ephemeris azimuth
  (88.6°) implies a camera azimuth of ~134° (SE) — exactly right for a
  frame one pan-step right of 9486's documented "looking ESE".
- Sun elevation changes only ~0.5°/hour on the Moon, so the ±10 min
  timing uncertainty contributes < 0.1°.

### Figures

- `fig1_synthetic_demonstrator.png` — fence-post fallacy + method validation
- `fig2_real_photo_fits.png` — both frames with digitized lines extended to
  their fitted convergence points
- `fig3_montecarlo_source_distance.png` — the lamp-distance exclusion
- `fig4_elevation_vs_ephemeris.png` — fitted vs ephemeris elevation,
  including the per-object systematic spread

## 6. Limitations (read before quoting)

- **Terrain is not a billiard table.** Local slopes bend the 2D appearance
  of shadows (Armstrong's shadow visibly kinks into Little West Crater —
  it is flagged and de-weighted in the JSON). This is handled as noise
  (χ²/dof ≈ 1.4 confirms the error model is about right), but it is the
  dominant uncertainty, especially for A14's boulder field.
- **The visible skyline is not the true horizon** (ridges at finite
  distance, ±60 px systematic assigned). This mostly affects the A14
  lamp-distance bound, which is why it is quoted as a weak ≥9 m.
- **Up-sun frames constrain elevation poorly** (A14). This is geometry,
  not a free pass: the frame still passes concurrency, azimuth, and
  lamp-exclusion tests.
- Print-scan JPEGs (LPI atlas) — fine for ±5–45 px measurements; lens
  distortion of the Biogon is < a few px and ignored.
- Hand digitization: coordinates were read from labeled-grid crops
  (process documented in the JSON); σ values are judgment calls, tested by
  the χ²/dof of the fits.

**What would change the verdict:** shadow lines in an original-scan frame
that demonstrably share *no* single convergence point (with double
shadows to match), a convergence point degrees below the true horizon, or
a well-conditioned down-sun frame whose fitted elevation contradicts the
ephemeris by many σ. None of the frames examined shows anything of the
kind.

## 7. Verdict

**REFUTED.** "Non-parallel" 2D shadows are the *required* appearance of
parallel 3D shadows under perspective — reproduced quantitatively in
`fig1`. In the two canonical "problem" photos every shadow is consistent
with one light source at infinity (χ²/dof ≈ 1.4, lamp model gains nothing
by AIC), a studio lamp within ~54 m is excluded at 95 % for the Apollo 11
frame, and the sun's elevation recovered from AS11-40-5961's geometry
matches the JPL ephemeris for 1969-07-21 04:43:31 UTC at Tranquility Base
to 0.7° ± 1.1°. Whoever lit that scene put the light exactly where the
Sun was — because it was the Sun.

## Files

```
annotations_AS14-68-9487.json   hand-digitized measurements + provenance
annotations_AS11-40-5961.json   hand-digitized measurements + provenance
digitize_helper.py              labeled-grid crop renderer used to digitize
reseau.py                       reseau-cross detector (camera calibration)
run.py                          full pipeline: data -> fits -> MC -> figures
data/                           scans + Horizons responses (gitignored;
                                re-fetched automatically by run.py)
results/fig1..fig4.png          figures
results/summary.json            machine-readable results + verdict
```
