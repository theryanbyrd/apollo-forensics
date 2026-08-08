# Claim 2: "Astronauts visible in shadow = fill lights"

**The claim.** In AS11-40-5866/5869 (Aldrin coming down the LM ladder), Aldrin
stands entirely inside the Lunar Module's shadow, yet his suit is clearly
visible. In vacuum there is no air to scatter light into shadows, so — the
argument goes — the only way to light him is a studio fill lamp.

**The physics the claim forgets.** Vacuum has no air scatter, but the Moon has
an enormous diffuse reflector three meters from Aldrin's boots: the sunlit
regolith itself. The question is not qualitative but quantitative: is
sun → sunlit regolith → shadowed suit **enough** to produce the measured
brightness, with no other emitter anywhere?

**Falsification criterion.** Measure the shadowed suit's radiance in the
photograph relative to the sunlit ground in the same frame. If it exceeds what
sun + regolith bounce + spacecraft interreflection can deliver (beyond the
stated error budget), something else was lighting him ⇒ the hoax claim stands.
If it matches the bounce prediction, the claim is busted. A secondary
signature: a lamp would also light the *ground* inside the shadow, and would
not reproduce the height-dependence of ground bounce.

## Method

1. **Hapke BRDF** (`hapke.py`): full IMSA bidirectional reflectance —
   double-lobed Henyey-Greenstein single-particle phase function,
   shadow-hiding opposition effect, Hapke-2002 H-functions, and the Hapke-1984
   macroscopic-roughness correction — exactly the model form of the LROC WAC
   photometric parameter product (see its `WAC_HAPKEPARAMMAP_README.TXT`).
2. **Parameters measured at the site, not assumed.** We read the actual
   Sato et al. (2014) LROC WAC Hapke parameter maps (PDS RDR, 1°×1° cells) and
   extract the cell containing Tranquility Base (23.47297°E, 0.67408°N):
   at 566 nm `w=0.188, b=0.254, c=0.158, Bs0=2.134, hs=0.0623`,
   at 643 nm `w=0.222, b=0.254, c=0.160, Bs0=1.993, hs=0.0597`,
   `theta_bar=23.657°` (fixed in the product), CBOE off.
3. **Validation.** Normal albedo comes out 0.11–0.13 (mare-like, sane);
   the disk-integrated phase curve gives full(g≈5°)/quarter(g=90°) = **12.1**,
   inside the observed 6–12× textbook range; the θ̄→0 analytic limits check out
   (`fig1_hapke_validation.png`).
4. **Scene** (`run.py`, Stage 3): flat regolith plane, LM as a 4.29 m × 4.29 m
   × 6.98 m box, its shadow cast by the real Sun position during the EVA
   (elevation 14.246°, azimuth 88.84° — JPL Horizons, observer at Tranquility
   Base, 03:15 UTC 21 Jul 1969; the ladder photos are timestamped 109:41:56 –
   109:42:53 GET = 03:13:56–03:14:53 UTC in the ALSJ). Aldrin is a set of
   vertical Lambertian Beta-cloth patches at 0.20/0.65/1.05/1.45 m height on
   the footpad, 2.1 m west of the descent stage, deep inside the ~27-m shadow.
   Fill irradiance on each patch is computed by integrating Hapke radiance
   from every sunlit 0.25 m ground cell out to 60 m, with the correct
   per-cell incidence/emission/phase/azimuth geometry and with the LM box
   occluding sight lines. No sky term (vacuum), no lamps.
5. **Prediction vs photograph.** For the same frame we predict the ratio
   (shadowed suit radiance)/(sunlit regolith radiance seen by the camera) and
   measure it in the LPI print-quality scan of AS11-40-5869: median pixel
   patches (suit, sunlit ground, deep-shadow ground, sky), sRGB/gamma
   linearization, black level subtracted using the sky patch. Ratios are
   in-frame, so film exposure cancels; the film *curve* does not, which is why
   we quote the decode spread and claim only factor-~2 honesty.

## Results (all numbers produced by `run.py`)

| Quantity | Predicted (sun + bounce only) | Measured in AS11-40-5869 |
|---|---|---|
| shadowed suit torso / sunlit ground | **0.40** [0.22–0.72] | **0.26** [0.23–0.29 across decodes] |
| suit brightness vs height (boot/thigh/PLSS rel. torso) | 0.21 / 0.66 / 1.29 | 0.075 / 0.63 / 1.07 |
| deep-shadow *ground* / sunlit ground | ≤ 0.02 (bound) | 0.0002 (≈ sky level) |
| counterfactual: black ground, no bounce | suit = 0 (silhouette) | not what the photo shows |
| AS11-40-5866 (Aldrin ~2.7 m up the ladder) suit/ground | 0.80 (assumed camera geometry) | 0.85 |

- Fill irradiance on the torso patch: **4.8 W/m²** (566 nm params) vs
  1279 W/m² direct sun on a sunlit vertical surface — the shadow side runs on
  ~0.4 % of direct sunlight, and that is *enough*, because the white Beta-cloth
  suit (ρ≈0.68) is ~7× more reflective than the regolith it is compared
  against.
- The Hapke backscatter matters: an equal-albedo Lambertian ground delivers
  only 2.5 W/m²; the no-roughness Hapke variant 8.8 W/m². Our central model
  sits between, and the envelope covers both.
- The **vertical gradient** is the fingerprint: ground bounce grows with
  height above the shadow floor (more sunlit ground visible over the shadow
  edge). Measured suit brightness tracks the prediction closely at
  thigh/torso/PLSS. And the *horizontal ground* inside the shadow stays at
  sky level — a coplanar surface receives no first-order ground bounce. A
  studio fill lamp does the opposite: it lights the shadow floor and doesn't
  know about height. (`fig4`, `fig5`)
- Boots measure darker than predicted (0.075 vs 0.21): the model omits the
  footpad/ladder blocking most of the remaining ground view at 0.2 m height,
  and boot dust/material differences. Noted as a limitation, direction
  understood.

**Verdict: BUSTED — no fill lamps needed.** Sun → regolith → suit bounce
predicts the shadowed suit at 40 % of sunlit-ground radiance [22–72 %]; the
photo measures 26 % [23–29 %]. The photograph contains, if anything, slightly
*less* shadow light than pure physics supplies — the opposite of what a fill
lamp would leave behind.

## Parameter provenance

| Input | Value | Source |
|---|---|---|
| Hapke w, b, c, Bs0, hs (566/643 nm) | see above; map cell (23.5°E, 0.5°N) | Sato et al. (2014), JGR Planets 119, 1775–1805, doi:10.1002/2013JE004580 — read directly from the PDS product `WAC_HAPKEPARAMMAP_{566,643}NM.IMG`, `pds.lroc.im-ldi.com/.../SDP/WAC_HAPKEPARAMMAP/` |
| θ̄ = 23.657°, CBOE off, φ→K=1 | fixed values in product | `WAC_HAPKEPARAMMAP_README.TXT` (same directory) |
| Model equations | IMSA + 2-lobe HG + SHOE + roughness | Hapke (2012), *Theory of Reflectance and Emittance Spectroscopy*, 2nd ed. (eq. 6.7a, 8.56, 9.22, ch. 12); Hapke (1984), Icarus 59, 41 |
| Sun elevation/azimuth/range at EVA | 14.246°, 88.84°, 1.01532 AU | JPL Horizons API, `CENTER='coord@301'`, `SITE_COORD='23.47297,0.67408,0'`, 1969-07-21 03:15 UTC |
| Photo times (109:41:56 / 109:42:53 GET) | 03:13:56 / 03:14:53 UTC | ALSJ Apollo 11 Image Library captions (nasa.gov static mirror of `images11.html`) |
| Tranquility Base coordinates | 0.67408°N, 23.47297°E | ALSJ / Davies & Colvin (2000) |
| Total solar irradiance | 1360.8 W/m² at 1 AU → 1320 W/m² at 1.0153 AU | Kopp & Lean (2011), GRL 38, L01706 |
| Suit outer-layer reflectance | ρ = 0.68 (α_s = 0.32), bracket 0.60–0.85 | Gilmore, *Spacecraft Thermal Control Handbook* 2nd ed., Table 4.1 ("Beta cloth 0.32 0.86"); A7L ITMG outer layer is Beta cloth |
| LM dimensions | 6.98 m tall, 4.29 m across flats, 9.45 m gear span | NASA Apollo 11 press kit / Grumman LM data (22'11", 14'1", 31') |
| Photographs | AS11-40-5866/5869/5862, 3900×3900 scans | LPI Apollo Image Atlas, `lpi.usra.edu/resources/apollo/images/print/AS11/40/` |

Transcribed inputs (not outputs of this code): the four provenance rows above
marked with literature values (S0, ρ_suit, LM dimensions, site coordinates).
Everything else — Hapke parameters, Sun geometry, radiances, ratios — is read
from public data files or computed by `run.py` in this directory.

## Limitations (honest error budget)

- **Patch-level analytic model**, not a renderer: astronaut = flat Lambertian
  patches; LM = a box; terrain = a plane (no craters/undulations, whose tilted
  faces add fill). Under-stage sunlight leakage (visible in the photo as the
  glowing foil at the footpad) and LM interreflection are *excluded* from the
  central model and only bounded (≤ +13 W/m² worst-case foil bounce; the
  +40 % envelope arm covers it). Both omissions make the model *under*-predict
  natural light — conservative for this test.
- **Film linearization is approximate.** Ektachrome's shoulder/toe are not a
  power law; we quote the ratio under sRGB and gamma 2.0/2.2/2.4 decodes
  (spread 0.23–0.29) and claim agreement only within factor ~2. In-frame
  ratios cancel exposure but not the curve.
- **Camera geometry assumed, then swept.** Armstrong's exact position isn't
  telemetered; camera azimuth 60–90°, ground-patch positions, and suit-normal
  azimuth are swept and the spread is in the envelope. The AS11-40-5866
  cross-check (0.80 predicted vs 0.85 measured) uses an assumed up-Sun
  geometry and is quoted as a consistency check, not a precision result.
- **Scan pipeline unknown** (scanner curve, color balance). The sky patch
  (DN ≈ 14/35/36 RGB — a teal-cast black) is subtracted as the black level;
  veiling glare in the up-Sun frame 5866 is why 5869 is the primary frame.
- Earthshine (~0.1 W/m², Earth near zenith) is 2 orders below regolith fill;
  ignored.

## Reproduce

```bash
cd claims/02-fill-light
../../.venv/bin/python run.py   # auto-fetches missing photos + parameter maps
```

`data/` is git-ignored; `run.py` re-fetches the photos (LPI) and parameter
maps (LROC PDS node) if absent — same URLs as the provenance table. Outputs:
`results/fig1..fig5*.png`, `results/summary.json`.
