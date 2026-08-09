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
3. **Scale** — defined once in **`a16_scale.py`** and imported by *both* this
   claim and claim 09, so the two pages cannot quote different answers to the
   same physical question. `run.py` re-measures Young's helmet-crown-to-boot-
   sole extent from the frames on every run: over the 62 frames in which he
   is walking on the ground away from a jump crouch it is **129.0 ± 3.5 px**
   (frame-to-frame sd; the scatter is real gait posture change). Sweeping the
   sole threshold over its plausible range moves the mean across 131.6–123.5
   px, a ±4 px systematic → adopted **129.0 ± 5.0 px**. Taken as
   **1.80 ± 0.10 m** (Young 1.75 m NASA bio, + 0.11 m EVA helmet/boots,
   − 3 % for the relaxed-knee A7LB stance the footage actually shows) →
   **71.67 px/m, ±6.8 % systematic**. The `.mov` cross-check uses its own
   independently measured scale (105 ± 4 px at its 256×192 raster, consistent
   with 129 × 192/240 = 103 px).

   *Correction:* earlier versions of this page used 128 px measured by eye on
   four stills, and claim 09 used 122 px / 1.88 m (64.9 px/m) for the same
   measurement — a 10 % contradiction between two pages of this repo, which
   propagated into a 17 % disagreement in the published A16 g. Re-measuring
   in code settles it: 122 px is the crown-to-*ankle* extent (it is what a
   0.60 threshold returns, because the boot is darker than the leg), and the
   boot/ground contact sits at y ≈ 187–189 with the crown at y ≈ 58–59.
4. **Flight window** — maximal contiguous interval around the apex where the
   Savitzky-Golay-smoothed acceleration is negative, trimmed 2 frames per
   side. Window edges are set by the *contact* spikes (push-off/landing), not
   by fit quality, so an in-flight tension event cannot be defined away.
5. **Fit & test** — quadratic (constant-g) fit; telecine-cadence-corrected
   fit; moving-block bootstrap errors; Ljung-Box whiteness; single-changepoint
   F-test (velocity+acceleration hinge, Bonferroni-corrected) with an
   injection-calibrated **power curve**; fit-free rise/fall timing at 25/50/75%
   height levels; cubic-term jerk bound; lateral-acceleration fit; residual
   FFT vs the stage-cable pendulum band; static-rock control through the same
   pipeline.

   The changepoint power curve is calibrated by injecting a velocity hinge of
   known Δv into synthetic trajectories whose noise is a **moving-block
   bootstrap of the real post-cadence residuals**, not i.i.d. Gaussian noise.
   That matters: those residuals fail Ljung-Box whiteness (p < 0.01), and
   autocorrelated noise partly mimics the hinge basis, so a white-noise
   calibration flatters the test. Against the real noise the test's
   *false-alarm* rate at Δv = 0 is **24 % (jump 1) / 13 % (jump 2)**, not the
   nominal 5 % — which is also the right yardstick for the p = 0.002 / 0.02
   "detections" reported below.
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
| **fitted g** | **1.677 ± 0.007 (stat) ± 0.114 (scale) m/s²** | **1.667 ± 0.010 ± 0.113 m/s²** |
| apex height above window edge | 0.35 m | 0.26 m |
| g from 8h/T² (endpoint check) | 1.673 m/s² | 1.676 m/s² |
| residual rms (plain → cadence-corrected) | 0.58 → **0.15 px ≈ 2.0 mm** | 0.54 → **0.17 px ≈ 2.3 mm** |
| rise/fall asymmetry (50% level) | −3.8% | −1.9% |
| apex time − window midpoint | −5 ms | +13 ms |
| lateral acceleration | 0.05 ± 0.01 m/s² | 0.09 ± 0.01 m/s² |
| jerk (cubic term) | −0.11 ± 0.06 m/s³ | +0.17 ± 0.10 m/s³ |
| tension-impulse Δv detected **50%** of the time | 3.5 cm/s | 5.6 cm/s |
| tension-impulse Δv detected **95%** of the time | **8.4 cm/s** | **11.2 cm/s** |
| changepoint false-alarm rate vs the real noise | 24% | 13% |
| static-rock control (same pipeline) | 0.06 px rms, "g" = 0.004 m/s² | — |

The two detection floors are different quantities and an earlier version of
this page conflated them: it labelled the 50%-power numbers "detection floor
(95%)". A real impulse at the 50% figure would be missed half the time. The
bound that supports a *non-detection* statement is the 95% row.

**Point by point against the falsification criteria:**

1. **Tension events: none that survive the rigid-body test.** The changepoint
   F-test does flag structure at the 0.15 px (2 mm!) level (p = 0.002 / 0.02).
   Two things say that is not a cable. First, against the actual
   (autocorrelated) residual noise this test fires on pure noise 24% / 13% of
   the time, so p = 0.002 / 0.02 is much weaker evidence than it looks.
   Second and decisively, a cable pulls the *whole* body, and the flagged
   "events" fail exactly that requirement: in jump 1 the best-fit event is
   **−9.1 cm/s in the helmet at t = −0.32 s but +8.8 cm/s in the backpack at
   t = −0.07 s** (jump 2: −4.9 vs +13.0 cm/s, also at different times;
   helmet–PLSS residual correlation only −0.21 / +0.21). Opposite signs,
   different times: that is Young *moving his arm to salute* — limb
   articulation redistributing momentum at millimetre scale — not a force on
   the body. A rigid-body impulse of **8–11 cm/s** (≈ 8% of takeoff velocity)
   would have been flagged 95% of the time — that is 8–12% of the takeoff
   velocity (1.09 / 0.95 m/s); one of ~4–6 cm/s, half the time.
2. **Symmetry: rise = fall to a few per cent** (and with the *wrong sign* for
   stage flying — the fall is marginally the shorter side, driven by cm-level
   ground-height differences at takeoff vs landing, not a prolonged "hang").
   Apex sits within ±13 ms (less than half a frame) of the flight-window
   midpoint in both jumps.
3. **g: right value, twice.** 1.677 and 1.667 m/s² — 0.6% apart from each
   other, 3.5% from lunar 1.62 (well inside the ±6.8% scale systematic), and
   the independent `.mov` chain lands on 1.613 m/s² for both jumps with its
   own scale. Curvature-based and endpoint-based (8h/T²) estimates agree to
   < 1%. Claim 09 fits the *same two jumps* by a coarser route (helmet-crown
   trace, no cadence correction) and gets 1.76 / 1.84 m/s² on the identical
   metric scale — 6% above these, i.e. a method difference smaller than the
   scale systematic the two claims now share. For contrast: Earth free fall
   over the same 0.35 m apex gives T = 0.53 s, not the observed 1.30 s; and
   the observed T on Earth would require a 2.1 m jump. A rig faking this must
   hold ~83% of body weight steady: the jerk bound says its tension could
   have drifted by at most ~0.3 m/s² over the flight — **steadier than
   3–4% — with zero attach/release transients, twice, identically.**
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
   (14.0 mm/px, MTF 0.5 assumed). Any load-bearing cable for a 130 kg suited
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

* **Scale dominates the g error** (±6.8%): suited standing height is measured
  at 129.0 ± 5.0 px and *assumed* to be 1.80 ± 0.10 m. The 3.5% offset of the
  fit from 1.62 m/s² is well inside this. The metre figure is the weakest
  link and it is an assumption, not a measurement: no independent length
  standard at Young's depth exists in this clip (the flag is a known 3 ft × 5
  ft but sits at a different, unmeasured distance). Timing, by contrast, is
  cross-validated to 0.2% across two independent encodes. This same constant
  is used by claim 09, so the two claims' A16 g values move together and
  their *difference* is scale-free.
* **Residuals are not fully white even after cadence correction**
  (Ljung-Box p = 0.000 / 0.003). The remaining ~2 mm structure is smooth,
  incoherent between helmet and backpack, and of changepoint-equivalent
  magnitude below ~13 cm/s — consistent with the arm salute and suit
  articulation visible in the footage, and *inconsistent* with rigid-body
  force events. We report this rather than hiding it, **and we calibrate
  against it**: the power curve and the false-alarm rates above are computed
  by block-bootstrapping these actual residuals, not by drawing white noise
  (an earlier version of this page claimed the floors were calibrated against
  this noise while the code was in fact injecting i.i.d. Gaussians — which is
  why the false-alarm rate turned out to be 24%/13% rather than 5%).
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
  a few %, impulses below the 8–11 cm/s 95%-power bound, g repeatable to
  < 1%) using 1972 stage technology, on the first take, live.
* One event, two jumps, ~350 × 240 px, VHS-generation footage. The method
  scales to the DAC film library (Grand Prix runs, falls, the hammer throw);
  this is the scaled-down version per repo ground rules.
* Camera assumed level (a tilt θ scales fitted g by cos θ; < 1% for θ < 8°);
  jump assumed depth-constant (apparent size change over the 1.3 s flight is
  below measurement noise).

## Verdict

**NO WIRES.** Both jumps are free ballistic flight at lunar gravity: constant
acceleration 1.677/1.667 ± 0.11 m/s², millimetre-level residuals with no
coherent tension event, against a test that would catch an 8–11 cm/s
rigid-body impulse 95% of the time, rise/fall symmetric to a few per
cent, no cable-arc lateral dynamics, and nothing above the helmet down to
sub-millimetre (sunlit) wire visibility. To fake this in 1972 you would have
needed a tension rig steadier than a few per cent with no transients whatsoever,
calibrated to lunar gravity within 1%, repeatably, on live TV, with an
invisible cable — i.e., a machine indistinguishable from the Moon.

## Reproduce

Downloads go to a `.part` file with a 120 s timeout and are renamed into
place only after the byte count matches `Content-Length`, so an interrupted
fetch cannot leave a truncated clip that later runs would trust. The decoded-
frame cache is keyed on the source file's size and the template-tracking
cache on a hash of every parameter that changes the answer (template boxes,
search radii, upsampling factor, frame shapes) — edit a box and the tracks
are recomputed instead of being silently reused.

```bash
cd claims/10-wire-rigs
../../.venv/bin/python run.py    # fetches ~4 MB from apollojournals.org on first run
```
