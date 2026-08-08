# Claim #11 — "The Van Allen belts would have killed the astronauts"

**Verdict: REFUTED.** A radiation-transport calculation along the *actual* Apollo 11
trajectory, using NASA's *actual* AE-8/AP-8 trapped-radiation models and NIST
stopping-power data, gives a total mission dose of **~2.4 mGy** (sensitivity band
1.7–4.6 mGy). The crew's film badges read **1.8 mGy**. A 50% lethal dose is
**~4,500 mGy**. The claim is off by three orders of magnitude — and the belt
transits themselves contributed only ~0.5 mGy of the total.

## The claim

Hoax proponents assert the Van Allen radiation belts are so intense that any
crew crossing them would have died, so the missions must have been faked.

**Falsification criterion.** The claim would be supported if an honest
transport simulation showed an unavoidable Sv-scale (thousands of mGy) dose for
any feasible translunar trajectory and realistic spacecraft shielding. It is
refuted if the computed dose along the real trajectory is far below medical
significance and consistent with the flown dosimetry.

## Method (all reproducible from `run.py`)

1. **Trajectory** (`trajectory.py`). The outbound leg is the real post-TLI
   osculating conic from the AS-506 Postflight Trajectory state vector
   (a = 286,545 km, e = 0.976966, i = 31.383°, TLI 1969-07-16 16:22:23 UTC at
   9.92° N, 164.84° W). The ascending node is reconstructed by anchoring the
   conic to the documented sub-TLI point with Earth rotation (GMST); the code
   verifies it reproduces the documented latitude/longitude/radius/velocity to
   4+ decimals (`check_anchor()`). The return transit is modeled as the inbound
   branch of the same conic anchored to the actual entry-interface time
   (1969-07-24 16:35 UTC). Magnetic coordinates via IGRF/SHELLG McIlwain L
   (primary) or a DGRF-1970 tilted centered dipole (fallback; pole 78.6° N,
   289.8° E, tilt 11.4°).

2. **Environment** (`environment.py`, `aep8_port.py`). Omnidirectional integral
   fluxes from NASA's AE-8/AP-8 models — not a paraphrase of them: the actual
   NSSDC model coefficient files (`ap8max.asc` etc., cached in `data/`) are
   evaluated with a line-faithful pure-Python port of the reference
   TRARA1/TRARA2 Fortran. The port is validated against the genuine compiled
   NASA Fortran (`radbelt` 0.1.8 binary wheel) at 4,896 (E, L, B/B0) points:
   max relative error 3.6e-6, zero zero/nonzero mismatches
   (`results/port_validation.json`, regenerate with `validate_port.py`).
   The published results additionally use the genuine `radbelt` engine end to
   end (IGRF L-shell tracing + compiled AP8/AE8) via `RADBELT_PYTHON`; the
   dipole+port fallback changes the belt dose by only ~9%.
   AP8/AE8 **MAX** models are used (1969 = solar maximum of cycle 20); the MIN
   variants change the belt-transit dose by ~3%.

3. **Shielding & dose** (`dosemodel.py`). Crew point at the center of a uniform
   aluminum shell: 7.5 g/cm² nominal, 3 and 15 g/cm² sensitivity. (Turner 2009,
   NASA THREE: the CM hull was "on the order of ten g/cm²"; the Boeing/Atwell
   512-ray CSM shielding distribution spans a few to tens of g/cm².)
   Protons: NIST PSTAR CSDA ranges in aluminum give the cutoff energy
   (~50 / 85 / 126 MeV for 3 / 7.5 / 15 g/cm²); penetrating protons deposit
   dose at the PSTAR liquid-water stopping power of their residual energy.
   PSTAR/ESTAR tables are downloaded live from `physics.nist.gov` (cached as
   CSV in `data/`) — nothing hand-typed. Electrons (≤7 MeV) cannot penetrate
   ≥3 g/cm² Al (ESTAR range of a 7 MeV electron: ~4 g/cm²); their
   bremsstrahlung photon dose is estimated from the ESTAR radiation yield with
   *no* credit for photon attenuation in the hull (conservative).
   Galactic cosmic rays: 0.24 mGy/day (SP-368/TN D-7080: "1.0 millirads per
   hour in cislunar space", an Apollo-measured value; band 0.16–0.48 mGy/day
   for solar-cycle modulation, consistent with Artemis I HERA's 0.37–0.48
   mGy/day in 2022) over the 8.14-day mission.

4. **Comparison & counterfactual** (`run.py`). Computed dose vs. flown
   dosimetry vs. medical thresholds; plus the August 4–9, 1972 solar particle
   event (between Apollo 16 and 17) pushed through the same transport model.

## RESULTS

| Quantity | Value |
|---|---|
| Inner-belt (proton) exposure duration, outbound | **~15 minutes**, at 25–40° magnetic latitude (misses the belt core) |
| Belt transits, both ways, behind 7.5 g/cm² | **0.47 mGy** (protons 0.14 + bremsstrahlung 0.33) |
| ... behind 3 / 15 g/cm² | 0.67 / 0.39 mGy |
| GCR background, 8.14 days | 1.95 mGy (band 1.3–3.9) |
| **Computed Apollo 11 mission total (7.5 g/cm²)** | **2.4 mGy** (band 1.7–4.6) |
| **Measured: Apollo 11 crew film badges** | **1.8 mGy** |
| Measured: all Apollo crews (SP-368 Table 2) | 1.6 – 11.4 mGy |
| Measured: Artemis I "Helga" phantom skin, 25.5 d (2022) | 11.5 mGy (belt transits: 2.1) |
| Threshold: lowest clinically observable effect | ~100 mGy |
| Threshold: acute radiation syndrome onset | ~1,000–2,000 mGy |
| Threshold: LD50 (untreated) | ~4,000–5,000 mGy |
| Worst case: dead-center equatorial belt crossings (both ways) | 25 mGy — still ~180× below LD50 |
| Worst case: loiter in the inner-belt core (L=1.5) behind the CM hull | 87 mGy/h → **52 hours** to LD50 (the crossing took minutes) |
| Counterfactual: Aug-1972 SPE inside the CM | **~2,900 mGy** (this model, King fit; 1,800 with measured-fluence anchor) |
| ... NASA's own 1975 estimate for that event (SP-368) | 3,600 mGy skin / 350 mGy blood-forming organs |
| ... Aug-1972 SPE in a spacesuit only (0.3 g/cm²) | ~67,000 mGy skin — this is what an *unlucky, unshielded* crew risked |

The computed mission dose agrees with the flown dosimetry to ~35% — far better
than the order-of-magnitude fidelity claimed — and both sit **three orders of
magnitude below lethal**. The trajectory figure shows why: Apollo's departure
was inclined ~31° to the equator (~30–40° in *magnetic* latitude thanks to the
11.4° dipole tilt and the Pacific injection point), threading over the inner
belt's core outbound and under it on return, crossing the proton belt in about
a quarter of an hour at fluxes ~100× below the equatorial peak.

The August 1972 counterfactual is the honest flip side: a Carrington-quarter
storm during a mission would have delivered a genuinely dangerous (though, per
NASA's and our numbers, survivable-in-the-CM) dose — and tens of Gy to the skin
of a crew caught outside. Radiation was a *real, managed* risk: that is why the
missions carried dosimeters, a solar-particle alert network, and flare rules
(TN D-7080 Table II) — and why "the belts are instantly lethal" was never the
question. The lethal-belts claim requires the dose to be ~1000× larger than
either the calculation or eleven missions' worth of dosimeters show.

Figures (in `results/`):
- `trajectory_through_belts.png` — the real trajectory over the real AP-8/AE-8
  flux maps in magnetic-meridian projection, with time ticks.
- `dose_rate_vs_time.png` — dose rate vs time for both transits, three shields.
- `comparison_chart.png` — the four-number verdict chart (log axis).
- `spe_counterfactual.png` — Aug-1972 dose vs shielding depth, with NASA's own
  published estimate overplotted.

## Parameter sources (transcribed inputs)

Everything numerical that is *not* computed here is a transcribed published
value, marked in the code where used:

- **TLI state vector / orbital elements**: Apollo/Saturn V Postflight
  Trajectory AS-506 (NASA MSC, 1969), as tabulated and independently re-derived
  at oikofuge.com/converting-apollo-state-vectors-to-orbits (a = 286,545 km,
  e = 0.976966, i = 31.383°, ω = 4.410°, ν = 14.909°, lat 9.9204° N,
  lon −164.8373°, r = 6,711.964 km, v = 10.8343 km/s). Self-consistency
  verified in code.
- **AE-8/AP-8 models**: NASA/NSSDC coefficient files from
  github.com/nasa/radbelt (Vette 1991; Sawyer & Vette 1976). Not transcribed —
  used verbatim.
- **Geomagnetic field**: DGRF-1970 degree-1 coefficients g10 = −30220 nT,
  g11 = −2068 nT, h11 = 5737 nT (IGRF-13) for the dipole fallback; full IGRF
  via `radbelt` for the primary engine.
- **Stopping powers/ranges**: NIST PSTAR (aluminum, liquid water) and ESTAR
  (aluminum), fetched live from physics.nist.gov and cached in `data/*.csv`.
- **CM shielding**: Turner, "Radiation Shielding" (NASA THREE, 2009): Apollo CM
  hull "nominal thickness on the order of ten g/cm²"; Apollo CSM shielding
  distribution figure (Atwell/Boeing). Nominal 7.5 g/cm², 3–15 sensitivity.
- **Apollo crew doses**: NASA TN D-7080 (English et al., 1973) Table I and
  SP-368 (Bailey, 1975) Ch. 3 Table 2: 0.16–1.14 rad; Apollo 11 = 0.18 rad.
- **GCR dose rate**: SP-368 Ch. 3 / TN D-7080: 1.0 mrad/h cislunar (solar max),
  doubling at solar min. Artemis I (2024 Nature) HERA: 0.37–0.48 mGy/day.
- **Artemis I doses**: "Space radiation measurements during the Artemis I lunar
  mission", Nature 634 (2024): Helga phantom skin, inner belt 1.96 ± 0.22 mGy,
  outer belt 0.11 ± 0.01, GCR 9.38 ± 1.03 (~11.5 total, 25.5 days).
- **Aug-1972 SPE spectrum**: King (1974) anomalously-large-event exponential
  fit, F(>30 MeV) = 7.9e9 cm⁻², E0 = 26.5 MeV (as tabulated in SPENVIS
  documentation and standard references); measured-fluence anchor
  F(>30 MeV) ≈ 5.0e9 cm⁻² per Smart et al. (2005)/McCracken et al. (2001) as
  cited by Hu, "Solar Particle Events and Radiation Exposure in Space" (NASA
  THREE, 2017). NASA's own in-CM estimate: SP-368 Ch. 3: "360 rads … to their
  skin and 35 rads to their blood-forming organs."
- **Medical thresholds**: standard radiobiology (NCRP/USNRC teaching values):
  ~100 mGy lowest clinically observable, ~1–2 Gy ARS onset, ~4–5 Gy LD50.

## Limitations (read before quoting)

- This is a **slab/spherical-shell, straight-ahead, CSDA transport estimate**,
  not a Geant4/HZETRN Monte Carlo: no nuclear interactions, no secondaries, no
  realistic mass distribution, isotropic-flux center-of-shell geometry.
  Expected accuracy is a **factor of a few**; the claim being tested is off by
  a factor of ~1,000, so this fidelity is decisive anyway.
- AE-8/AP-8 are themselves ~factor-of-2 models (their stated accuracy), static,
  omnidirectional averages; 1969 solar-cycle specifics are folded in only
  through the MIN/MAX pair (a ~3% effect here).
- The return leg reuses the outbound conic (inbound branch, correct entry
  epoch); the real transearth trajectory differed modestly. The worst-case
  scenario (dead-center equatorial crossing, 25 mGy) bounds any plausible
  geometry error from above.
- Bremsstrahlung is deliberately conservative (no shield attenuation) and still
  contributes only ~0.3 mGy; Artemis I measured 0.11 mGy for its outer-belt
  passes, so reality is smaller than our number, as designed.
- Film badges measure skin dose at the body surface inside a non-uniform CM;
  blood-forming-organ doses were ~40% *lower* (TN D-7080).

## Reproduce

```bash
# fallback engine (pure-Python port of AE8/AP8 + tilted dipole) - no extra deps
python run.py

# primary engine (genuine NASA radbelt: IGRF L-shell + compiled Fortran AE8/AP8)
python3.10 -m venv rbenv && rbenv/bin/pip install radbelt
RADBELT_PYTHON=$PWD/rbenv/bin/python python run.py

# port-vs-Fortran validation report
RADBELT_PYTHON=... python validate_port.py $RADBELT_PYTHON
```

`data/` (model files, NIST tables, cached environment samples, source PDFs) is
git-ignored; the scripts re-download what is missing.
