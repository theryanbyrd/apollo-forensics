# Claim 10 — "The astronauts were hanging on wire rigs"

The loping gait and slow, gentle falls are said to be stage flying: astronauts
on cables, Peter-Pan style, with the "moon gravity" faked by counterweights or
tension rigs. **The dynamics don't lie.** A cable cannot pull on a body without
leaving fingerprints in the acceleration record: tension transients (jerk
spikes), asymmetric rise vs fall, an effective g that wanders between takes,
cable-pendulum lateral dynamics — and, at some thickness, a visible line.

Free ballistic flight has none of these. Between takeoff and landing the center
of mass obeys `y(t) = y₀ + v₀t − ½gt²` with *constant* g, perfectly symmetric
rise and fall, zero jerk, and zero lateral acceleration.

## Falsification criterion

The hoax is *supported* if the airborne phase of a real EVA jump shows any of:

1. **Tension events** — statistically significant, *rigid-body-coherent*
   velocity/acceleration discontinuities inside the flight window;
2. **Asymmetry** — rise time ≠ fall time beyond noise (the classic "prolonged
   hang" of stage flying);
3. **Wrong or inconsistent g** — fitted acceleration far from 1.62 m/s², or
   differing between two jumps minutes (or seconds) apart;
4. **Cable dynamics** — pendulum-band oscillation, or lateral acceleration
   toward a pivot during flight;
5. **A line** — anything wire-like in a noise-beating temporal stack of the
   region above the helmet.

## The footage

**John Young's Apollo 16 "jump salute"** (EVA-1 flag deployment, GET
120:25:02–120:26:57, Descartes) — he jumps twice, saluting, while Charlie Duke
takes the famous photo AS16-113-18339. Two independent digitizations of the
same event, both fetched by `run.py` from the Apollo Lunar Surface Journal:

| file | source URL | format | documented rate |
|---|---|---|---|
| `a16salute.mpg` | apollojournals.org/alsj/a16/a16salute.mpg | MPEG-1 352×240 | **29.97 fps** |
| `a16v.1202502.mov` | apollojournals.org/alsj/a16/a16v.1202502.mov | SVQ1 256×192 | 15.01 fps |

### Frame-rate provenance (this matters, so here it is in full)

* The event was recorded by the **RCA GCTA color TV camera on the lunar rover
  and transmitted live** — so the NTSC timeline is wall-clock time. This is
  *not* 16 mm DAC film; there is no 12-vs-24 fps ambiguity for this event.
* ALSJ's Ken Glover documents `a16salute.mpg` explicitly: made *"for students
  interested in analyzing John's 'Big Navy Salute'"*, at **29.97 fps**, from a
  high-resolution AVI he captured from the VHS release of the broadcast
  (quoted on the [A16 Video Library page](https://www.apollojournals.org/alsj/a16/video16.html),
  entry at 120:25:23; page cached in `data/video16.html`).
* We verified the 29.97 fps stream is temporally genuine: 2 near-duplicate
  frames out of 467 (i.e. not an upsampled 15 fps stream).
* **Discovered during analysis:** the parabola-fit residuals of *both* jumps
  contain an identical 5-frame-periodic sampling-time pattern
  (τ = [−19, −4, −5, +13, +14] ms, matching between jumps to ~1 ms). The
  implied true sample spacing is four ~42 ms steps plus one repeat — i.e. the
  VHS chain included a **24 fps film-transfer stage with 2:3 pulldown**
  (fig 4). Pulldown is wall-clock-preserving (5 video frames = 166.8 ms = 4
  film frames at 24 fps), so it biases g by < 1%; we correct for it by fitting
  per-phase time offsets. This cadence was recovered blind, from the jump
  dynamics alone.
* **Independent cross-check:** the separately-encoded QuickTime clip (different
  codec, different rate) gives an apex-to-apex separation between the two jumps
  of 3.110 s vs 3.104 s in the MPEG — a **timeline ratio of 1.002** across two
  digitization chains — and fits g = 1.613 m/s² on both jumps using its own
  independently measured scale.

## Method

1. **Track** — normalized cross-correlation template matching on 4×-upsampled
   patches (sub-pixel via parabolic peak interpolation). Fixed templates taken
   at each jump's apex frame; three features per jump (helmet, PLSS backpack,
   and combined upper body) so that rigid-body motion can be distinguished from
   limb articulation. Minimum NCC across all astronaut tracks: 0.79.
2. **Stabilize** — four static ground-rock patches tracked the same way;
   median per-frame offset subtracted (camera jitter: 0.19 px rms).
3. **Scale** — Young's standing image height, measured on four gridded frames
   (195/205/290/300): 128 ± 4 px, taken as 1.80 ± 0.10 m (Young 1.75 m,
   NASA bio, + EVA helmet/boots, − relaxed A7LB knee flex) → 71 px/m,
   ±6.4% systematic. The `.mov` cross-check uses its own scale (105 ± 4 px).
4. **Flight window** — maximal contiguous interval around the apex where the
   Savitzky-Golay-smoothed acceleration is negative, trimmed 2 frames per
   side. Window edges are set by the *contact* spikes (push-off/landing), not
   by fit quality, so an in-flight tension event cannot be defined away.
5. **Fit & test** — quadratic (constant-g) fit; telecine-cadence-corrected
   fit; moving-block bootstrap errors; Ljung-Box whiteness; single-changepoint
   F-test (velocity+acceleration hinge, Bonferroni-corrected) with an
   injection-calibrated detection floor; fit-free rise/fall timing at 25/50/75%
   height levels; cubic-term jerk bound; lateral-acceleration fit; residual
   FFT vs the stage-cable pendulum band; static-rock control through the same
   pipeline.
6. **Wire search** — median stack of all 73 flight frames in the *astronaut's*
   reference frame (a jump wire moves with the jumper, so it stacks
   constructively while sky noise averages down) over a 120×30 px strip above
   the helmet (~1.7 m wide × 0.42 m tall at his distance), plus a ground-frame
   stack of the permanently-empty sky strip (static rigging). Matched
   filtering with oriented line kernels (−30°…+30° from vertical); detection
   threshold z = 5 (robust MAD units), calibrated by injecting synthetic wires.

## Results (all numbers printed by `run.py`)

| quantity | jump 1 | jump 2 |
|---|---|---|
| flight duration T | 1.302 s | 1.137 s |
| **fitted g** | **1.690 ± 0.007 (stat) ± 0.108 (scale) m/s²** | **1.680 ± 0.010 ± 0.107 m/s²** |
| apex height above window edge | 0.35 m | 0.26 m |
| g from 8h/T² (endpoint check) | 1.686 m/s² | 1.689 m/s² |
| residual rms (plain → cadence-corrected) | 0.58 → **0.15 px ≈ 2.0 mm** | 0.54 → **0.17 px ≈ 2.3 mm** |
| rise/fall asymmetry (50% level) | −3.8% | −1.9% |
| apex time − window midpoint | −5 ms | +13 ms |
| lateral acceleration | 0.05 ± 0.01 m/s² | 0.09 ± 0.01 m/s² |
| jerk (cubic term) | −0.11 ± 0.06 m/s³ | +0.17 ± 0.10 m/s³ |
| tension-impulse detection floor (95%) | 5.6 cm/s | 8.4 cm/s |
| static-rock control (same pipeline) | 0.06 px rms, "g" = 0.004 m/s² | — |

**Point by point against the falsification criteria:**

1. **Tension events: none that survive the rigid-body test.** The changepoint
   F-test does flag structure at the 0.15 px (2 mm!) level (p = 0.002 / 0.02) —
   but a cable pulls the *whole* body, and the flagged "events" fail exactly
   that requirement: in jump 1 the best-fit event is **−9.2 cm/s in the helmet
   at t = −0.32 s but +8.9 cm/s in the backpack at t = −0.07 s** (jump 2:
   −4.9 vs +13.1 cm/s, also at different times; helmet–PLSS residual
   correlation only −0.21 / +0.21). Opposite signs, different times: that is
   Young *moving his arm to salute* — limb articulation redistributing momentum
   at millimetre scale — not a force on the body. Any real rig impulse above
   ~6–8 cm/s (5% of takeoff velocity) would have been detected coherently.
2. **Symmetry: rise = fall to a few per cent** (and with the *wrong sign* for
   stage flying — the fall is marginally the shorter side, driven by cm-level
   ground-height differences at takeoff vs landing, not a prolonged "hang").
   Apex sits within ±13 ms (less than half a frame) of the flight-window
   midpoint in both jumps.
3. **g: right value, twice.** 1.69 and 1.68 m/s² — 0.6% apart from each other,
   4% from lunar 1.62 (well inside the ±6.4% scale systematic), and the
   independent `.mov` chain lands on 1.613 m/s² for both jumps with its own
   scale. Curvature-based and endpoint-based (8h/T²) estimates agree to < 1%.
   For contrast: Earth free fall over the same 0.35 m apex gives T = 0.53 s,
   not the observed 1.30 s; and the observed T on Earth would require a 2.1 m
   jump. A rig faking this must hold ~83.5% of body weight steady: the jerk
   bound says its tension could have drifted by at most ~0.3 m/s² over the
   flight — **steadier than 3–4% — with zero attach/release transients, twice,
   identically.**
4. **Cable dynamics: none visible.** Lateral acceleration is 0.05–0.09 m/s²
   (≈ noise floor; a pendulum on a fixed pivot at the observed lateral drift
   would need L ≳ 10 m to hide here — see Limitations). The residual spectra
   show no oscillatory line; the stage-cable pendulum band itself
   (0.13–0.5 Hz for L = 1–15 m) is honestly *unreachable* with a 1.3 s flight
   — that specific test is inconclusive by construction and we say so.
5. **No wire.** Astronaut-frame stack of 73 flight frames: max line-filter
   response z = 3.6 (threshold 5); ground-frame sky stack: z = 4.1. The
   injection calibration shows a 1.0-DN line *would* have been detected
   (z = 10.9): that corresponds to a sunlit wire of **≥ 0.16 mm**, or a dull
   (20% suit radiance) wire of **≥ 0.8 mm**, at the astronaut's distance
   (14.1 mm/px, MTF 0.5 assumed). Any load-bearing cable for a 130 kg suited
   astronaut (real ones are several mm, typically painted *bright* for stage
   safety or blackened — see caveat below) is orders of magnitude above the
   sunlit bound.

**Bonus forensic:** the residuals didn't just fail to show wires — they
recovered the video's own transfer history (a 24 fps film stage with 2:3
pulldown, fig 4) blind, from dynamics alone, identically in both jumps. A
tracking pipeline sensitive enough to read *milliseconds of telecine cadence*
off a 1972 VHS-generation clip found no trace of a cable.

## Figures

| file | contents |
|---|---|
| `results/fig1_track_overlay.png` | annotated frames + whole-clip track (walk-in, crouch, both jumps) |
| `results/fig2_fit_jump1.png`, `fig3_fit_jump2.png` | y(t) + parabola fit, residuals before/after cadence correction, acceleration profile with contact spikes and flat lunar-g plateau |
| `results/fig4_cadence_forensics.png` | recovered telecine cadence, both jumps |
| `results/fig5_symmetry_spectrum.png` | trajectory vs its own time-mirror; residual PSD vs pendulum band |
| `results/fig6_wire_stack.png` | astronaut-frame sky stack, line-filter response, synthetic-wire injection, ground-frame stack |

## Limitations (honest scope)

* **Scale dominates the g error** (±6.4%): suited standing height is assumed
  1.80 ± 0.10 m and measured at 128 ± 4 px. The 4% offset of the fit from
  1.62 m/s² is well inside this. Timing, by contrast, is cross-validated to
  0.2% across two independent encodes.
* **Residuals are not fully white even after cadence correction**
  (Ljung-Box p < 0.01). The remaining ~2 mm structure is smooth, incoherent
  between helmet and backpack, and of changepoint-equivalent magnitude below
  ~10 cm/s — consistent with the arm salute and suit articulation visible in
  the footage, and *inconsistent* with rigid-body force events. We report
  this rather than hiding it; the detection floors quoted are calibrated
  against exactly this noise.
* **The pendulum-frequency test is inconclusive by construction**: any
  plausible stage cable (L ≥ 1 m) has a period ≥ 2 s, longer than the 1.3 s
  flight. The lateral-acceleration bound covers part of this space (short
  cables), but a very long (L ≳ 10 m), perfectly steady rig evades the
  frequency test specifically — it is caught instead by criteria 1–3 and 5.
* **A matte-black wire against the black sky is optically undetectable** at
  this resolution; the visibility bound applies to lit wires. This is exactly
  why the *dynamics* tests are primary and the wire stack is secondary.
* **A mathematically perfect constant-tension rig** tuned to exactly
  1.62 m/s²-equivalent, with noiseless servo response, no transients at
  takeoff/landing, identical calibration across takes, and an invisible cable
  is asymptotically indistinguishable from real lunar gravity by profile shape
  — the analysis quantifies how perfect it would have to be (tension steady to
  a few %, impulses < 6 cm/s, g repeatable to < 1%) using 1972 stage
  technology, on the first take, live.
* One event, two jumps, ~350 × 240 px, VHS-generation footage. The method
  scales to the DAC film library (Grand Prix runs, falls, the hammer throw);
  this is the scaled-down version per repo ground rules.
* Camera assumed level (a tilt θ scales fitted g by cos θ; < 1% for θ < 8°);
  jump assumed depth-constant (apparent size change over the 1.3 s flight is
  below measurement noise).

## Verdict

**NO WIRES.** Both jumps are free ballistic flight at lunar gravity: constant
acceleration 1.69/1.68 ± 0.11 m/s², millimetre-level residuals with no
coherent tension event above a 6 cm/s floor, rise/fall symmetric to a few per
cent, no cable-arc lateral dynamics, and nothing above the helmet down to
sub-millimetre (sunlit) wire visibility. To fake this in 1972 you would have
needed a tension rig steadier than a few per cent with no transients whatsoever,
calibrated to lunar gravity within 1%, repeatably, on live TV, with an
invisible cable — i.e., a machine indistinguishable from the Moon.

## Reproduce

```bash
cd claims/10-wire-rigs
../../.venv/bin/python run.py    # fetches ~4 MB from apollojournals.org on first run
```
