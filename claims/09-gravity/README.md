# Claim 9 — "The footage is Earth gravity slowed down ~2.46×"

**The claim.** Apollo surface footage was really shot on Earth and slowed
down. Slowing playback by a factor *s* scales apparent accelerations by
1/*s*², so to disguise Earth's 9.81 m/s² as the Moon's 1.62 m/s² you need
*s* = √(9.81/1.62) ≈ **2.46**.

**Falsification criterion.** The claim survives only if a *single global*
s ≈ 2.46 simultaneously explains (a) ballistic trajectories, (b) human
motion/speech tempo (which scales as 1/*s*, i.e. the "actors" really moved
and talked 2.46× faster than we see), and (c) drag-sensitive behaviour
(a feather falling in air acquires a terminal-velocity signature that no
playback speed can rescale into vacuum free-fall). Conversely, the claim is
refuted if the trajectories fit lunar gravity *and* the tempo and drag
observations are inconsistent with a 2.46× slow-down.

**Verdict: REFUTED.** The ballistics alone cannot separate "Moon" from
"slowed Earth" — that degeneracy is the whole point of the claim — but the
tempo and drag tests, run on the *same synchronized clip*, both fail the
slow-down hypothesis decisively.

---

## Data (all public; cached in `data/`, which is gitignored)

| file | what | source |
|---|---|---|
| `a15v_1672206.mpg` | Apollo 15 hammer‑feather drop, LRV TV camera, 320×240, 30 fps MPEG‑1, 49.05 s, GET ≈ 167:22:01–167:22:50 | ALSJ "MPEG Clip (49 sec; 6.2 Mb)" linked at 167:22:02 of the EVA‑3 closeout journal, fetched via Wayback: `web.archive.org/web/20200303130411if_/https://history.nasa.gov/alsj/a15/a15v_1672206.mpg` |
| `a16salute.mpg` | Apollo 16 John Young "jump salute", LRV TV camera, 352×240, 29.97 fps MPEG‑1, 15.8 s, GET ≈ 120:25:42 | ALSJ video library (video16.html), via Wayback: `web.archive.org/web/20191119005030if_/https://history.nasa.gov/alsj/a16/a16salute.mpg` |
| `hammer_feather_archiveorg.mp4` | independent‑lineage copy of the same A15 TV footage, 640×480, 15 fps | `archive.org/details/FeatherHammerDropOnMoon` |

The nasa.gov ALSJ pages moved in ~2023; the Wayback snapshots serve the
original NASA-hosted files byte-for-byte (`if_` = original file mode).

### Frame-rate provenance (this matters, so here it is honestly)

* Both ALSJ clips are MPEG‑1 **system streams**: audio and video are muxed
  with shared PTS clocks, so A/V sync is enforced by the container. The video
  streams decode at 30/29.97 fps with **no duplicated frames** (checked:
  consecutive-frame differences never approach zero).
* **Real-time check against the mission transcript:** Scott's Galileo
  monologue occupies 167:22:06 → 167:22:43 in the ALSJ transcript (~37 s of
  GET). In the clip's audio we measure the same monologue at 1.94 s → 37.61 s
  = **35.7 s**. The clip therefore plays at true broadcast rate (1:1 with
  elapsed mission time) to within ~4 %. Any global 2.46× slow-down of the
  *video* would have to be matched by a 2.46× slow-down of the *audio* —
  which is what the tempo test below measures.
* The Apollo 15/16 colour TV camera (RCA GCTA) was **field-sequential**: the
  ground-station NTSC conversion updates the position of a small *moving*
  object in ~3-frame (≈10 Hz) steps. We aggregate the tracks into those steps
  and carry ±0.6-frame timing errors. NTSC 29.97 vs the container's 30 fps is
  a 0.1 % effect, ignored.

---

## Method

Everything is reproduced by `run.py` (uses the shared repo venv; OpenCV +
scipy + matplotlib only):

1. **Scene forensics (A15).** Median of pre-release frames 1145–1175 gives a
   clean background. Differencing every frame against it localizes all
   motion. A pre/post comparison (frames 1160–1170 vs 1245–1255) shows
   exactly two new objects on the ground afterwards: the hammer patch at
   x 110–135 and the feather streak at x 157–195, both at image y ≈ 195–203
   — these anchor the track identities.
2. **Tracking.** Intensity-weighted centroids of background-subtracted blobs
   inside per-object lanes, aggregated into field-sequential steps
   (`src/a15_tracks.py`, output in `results/a15_tracks.csv`). The feather
   (bright, positive-signed diffs — it is the object, not a shadow) yields 5
   clean steps spanning y = 129.6 → 195.0 px over frames 1184.5 → 1199.5,
   landing at frame 1201.5 ± 1.5. The hammer is only partially resolvable
   against the mixed MESA background: 3 steps, landing at 1195.5 ± 1.5 on a
   small mound ~20 px above the feather's ground line, then sliding slowly to
   its final rest position by frame ~1233 (visible in `results/a15_streak.png`
   and corroborated by the independent archive.org copy).
3. **Metric scale.** A15: suited David Scott (1.83 m; A7LB EVA stack
   1.92 ± 0.06 m) measures 128 ± 5 px helmet-crown-to-boot-sole →
   **66.7 ± 4.5 px/m**. Cross-check: the measured hand-to-ground drop of
   87 px → 1.30 m, matching a chest-height release.
   A16: **imported from `claims/10-wire-rigs/a16_scale.py`**, the single
   definition of this clip's calibration, shared with claim 10 so that the
   two claims cannot disagree about the same measurement —
   **129.0 ± 5.0 px = 1.80 ± 0.10 m → 71.67 px/m, ±6.8 % systematic**
   (derivation and the code that measures the 129 px from the frames are in
   that file). Earlier versions of this page used 122 px / 1.88 m
   (64.9 px/m) while claim 10 used 128 px / 1.80 m (71.1 px/m) — a 10 %
   contradiction about one physical measurement. Re-measuring the extent
   over 62 frames gives 129.0 ± 3.5 px (claim 10's decode) and 128.8 ± 3.6 px
   (this claim's PNG frames, printed by `run.py`); 122 px was the
   crown-to-*ankle* extent and 1.88 m additionally ignored the knees-flexed
   stance the footage actually shows, so the two errors compounded.
4. **Fits.** `y(t) = y₀ + v₀t + ½at²` by least squares; bootstrap over pixel
   noise (1 px) and step-timing noise (0.6 frames for A15, 0.5 for A16)
   (`src/a15_fit.py`, `src/a16_jump.py`). For A16 the **scale is held fixed
   in the bootstrap and carried separately**: it is one constant shared by
   both jumps (and by claim 10), so resampling it per jump and then combining
   the jumps as if independent would shrink a systematic that cannot shrink.
   Statistical parts combine by inverse variance; the scale systematic is
   applied once to the combined value.
5. **Hypothesis tests.** Feather drag ODE (`src/feather_drag.py`), speech
   tempo (`src/a15_tempo.py`), and the A16 push-off biomechanics.

---

## Results

Every number below is produced by `run.py` and lands in `results/*.json`,
with two stated exceptions: the A16 metric scale is imported from
`claims/10-wire-rigs/a16_scale.py` (shared, by design — see Method 3), and
the archive.org frame-number cross-check in the timeline section was done by
eye and is labelled as such.

### Ballistics

| quantity | value |
|---|---|
| A15 feather apparent acceleration | **g = 1.22 ± 1.40 m/s²** (81 ± 93 px/s²) |
| → consistent with lunar 1.62 m/s²; real-time Earth 9.81 m/s² excluded at | **6.1 σ** |
| A16 jump 1 / jump 2 apparent g (helmet-top parabolas) | **1.76 ± 0.05 (stat)** / **1.84 ± 0.08 (stat) m/s²**, both ± 6.8 % scale |
| A16 combined | **1.78 ± 0.04 (stat) ± 0.12 (scale) m/s² = ± 0.13 total** |
| A16 hang times | 1.40 s / 1.43 s |
| playback factor *s* required if the A15 fall were really Earth footage | 2.84 (68 % CI 1.9–4.1) — **includes 2.46** |

The two A16 error components are reported separately because they behave
differently: the ±0.04 statistical part is what shrinks when you add jumps,
the ±0.12 scale part is one shared constant that never shrinks. Quoting a
single inverse-variance-combined "± 0.10 (stat)" — as an earlier version of
this page did — silently averaged a correlated systematic down.

So the trajectories fit lunar gravity, and — exactly as the claim intends —
a *s* ≈ 2.46 slow-down of Earth footage is *ballistically* allowed. A lone
parabola fits any g with a suitable playback speed. That is why the next two
tests exist, and they use the *same* footage, so no "different clip, different
trick" escape is available.

### Tempo (kills the slow-down)

The audio is PTS-locked to the video. If the video is slowed 2.46×, so is the
audio. Scott's 144-syllable monologue (text fixed by the ALSJ transcript)
takes 35.7 s in the clip → **4.04 syllables/s including pauses** — dead
normal (conversational English ≈ 3.5–5.5 syl/s). Under the hoax the real
Scott spoke at **9.9 syllables/s sustained for 15 s** (articulation bursts
≈ 16.7 syl/s) — roughly twice the rate of championship debate speed-reading,
maintained casually, twice (the A16 audio contains equally normal chatter).
And John Young's jump push-off (deepest crouch → liftoff) measures
**0.30 s / 0.23 s** in the two jumps; under the hoax the real push-off was
**0.12 s / 0.09 s** — a suited human (~90 kg of suit + PLSS) cannot complete
a full crouch-extension in a tenth of a second.

### Drag (kills it again, independently)

The tracked feather **accelerates throughout its visible fall** and crosses
its last step interval at an apparent **2.35 ± 0.48 m/s**. Integrating the
drag ODE dv/dt = g − (g/vt²)v² for a falcon feather in Earth air
(terminal velocity 0.8–1.5 m/s) over the measured 1.30 m drop:

| scenario | real fall time | seen at 1/2.46× | apparent impact speed on screen |
|---|---|---|---|
| Moon vacuum (real time) | 1.27 s | — | 2.05 m/s |
| Earth vacuum, slowed | 0.51 s | 1.27 s | 2.05 m/s ← degenerate, as advertised |
| Earth air, vt = 1.5 m/s, slowed | 0.97 s | 2.39 s | **0.61 m/s** |
| Earth air, vt = 1.1 m/s, slowed | 1.26 s | 3.10 s | **0.45 m/s** |
| Earth air, vt = 0.8 m/s, slowed | 1.68 s | 4.14 s | **0.33 m/s** |

The observed 2.35 ± 0.48 m/s is **~4× above the fastest possible Earth-air
feather** (3.6 σ), and the observed feather still gains speed between every
step — a terminal-velocity feather doesn't. In slowed Earth-air footage the
feather would also have hit ~2.5 s of *screen time* after the hammer; the
measured landing gap is **0.20 ± 0.07 s**, of which ~0.13 s is explained by
the hammer landing on a mound ~0.3 m higher along the slope (residual
0.07 ± 0.07 s ≈ simultaneous). See `results/feather_drag_sim.png` — the
observed track rides the vacuum curve, far from every air curve.

The only Earth-based way to produce the feather's motion is a **vacuum
chamber** — at which point the footage no longer needs slowing for the
feather, but still needs 2.46× slowing for the astronaut's g... and then the
audio/tempo test above kills it anyway. There is no self-consistent *s*.

### The forensic timeline (frames of `a15v_1672206.mpg` @ 30 fps)

* 1.94–37.6 s — Scott's Galileo monologue, ending "...they'll hit the ground
  at the same time." (frame ≈ 1155)
* ≈ 1179–1183 — hand motion; release completes. The exact instant is hidden
  against the bright suit, and **the ballistic extrapolation cannot recover
  it**: propagating the fit through the same bootstrap, the zero-velocity
  time `t_rel = t₀ − v₀/a` has a point estimate of frame **1143.6** with a
  68 % interval of **1082–1171** (≈ 3 s wide), and 20 % of bootstrap draws
  give a ≤ 0, i.e. no from-rest solution at all. That is what a fit whose
  acceleration is only ~1 σ from zero can support. The release *is*
  consistent with the end of the sentence (frame 1155 sits inside the
  interval, 0.38 s after the point estimate), but this test does not
  establish it and nothing downstream depends on it — the drag and tempo
  arguments use the landing times and the measured speeds, not the release
  instant. An earlier version of this page quoted "frame ≈ 1152 ± 8", a
  number that appeared nowhere in the code and was ~10× too confident.
* 1195.5 ± 1.5 — hammer lands on the raised mound (then slides ~0.3 m
  downslope until ≈ frame 1233)
* 1201.5 ± 1.5 — feather lands
* ≈ 41.0 s (frame ≈ 1230) — "How about that!"
* ≈ 47.5 s — Scott bends down to retrieve; Allen: "Superb."

The independent 15-fps archive.org copy shows the same event sequence at the
same wall-clock spacings (hammer's initial rest appears at its frame 579 ≈
our frame 1199), ruling out an encode-specific timing artifact. *This one
cross-check was made by stepping through the archive.org file by eye;
`run.py` downloads that file but does not track it, so unlike everything
else on this page the 579 is not regenerated by the code.*

---

## Figures (`results/`)

* `a15_track_overlay.png` — annotated frame with both tracks + scale bar
* `a15_streak.png` — time-vs-height motion streak: the fall, the landings,
  the hammer's slow slide; step markers overlaid
* `a15_fit.png` — feather y(t) steps + free-fall fit + residuals (< 1 px)
* `feather_drag_sim.png` — landing-anchored feather approach vs all
  hypotheses (the money plot for the drag argument)
* `joint_hypothesis.png` — ballistics / tempo / drag, side by side
* `a16_jump.png` — Young's two jump arcs with parabola fits and push-off
  windows

## Limitations

* This is **two events from two missions**, not the full-archive Bayesian
  fit the complete methodology calls for. The refutation logic doesn't need
  more: one synchronized clip already over-constrains the single global *s*.
* The A15 g error bar is wide (±1.4 m/s²) because one 10 Hz field-sequential
  event gives only 5 usable position steps and the release instant is
  occluded; the acceleration is measured from track curvature only. It still
  excludes real-time Earth at 6 σ. The same width is why the release-time
  extrapolation above is uninformative.
* The A15 and A16 scales use slightly different anthropometric conventions:
  A15 takes Scott's suited stack fully upright (1.92 m), A16 takes Young's
  crown-to-sole extent in the knees-flexed stance the clip actually shows
  (1.80 m). A15 is not re-derived here because its g error is 115 %
  fit-dominated — the scale contributes nothing to it — whereas the A16
  scale had to be fixed because claim 10 depends on it too.
* **The A16 g runs ~0.16 high of 1.62** (1.78 vs 1.62, i.e. 10 %), which is
  1.3× the ±0.12 scale systematic. Claim 10 measures *the same two jumps*
  with a more careful method — whole-body template rather than the helmet
  crown, flight windows set by the acceleration sign at the contact events,
  and a telecine-cadence correction — and gets **1.677 and 1.667 m/s²**, ~6 %
  below these numbers, using the identical metric scale. The difference is
  a method systematic, not a scale disagreement: re-fitting these jumps over
  a ±2-frame family of windows moves g by ±0.05–0.06 m/s², and the helmet
  crown moves relative to the centre of mass as Young pitches his torso and
  swings his arm up to salute in flight. **For the precision A16 number,
  prefer claim 10's.** What this claim needs from A16 is only that g is near
  1.6 and nowhere near 9.8, and both analyses agree on that.
* The camera was verified static (±1 px) during both jumps. Real-time Earth
  (9.81) is 63 σ away from the A16 combined value on the total ±0.13 error,
  and still > 25 σ away even if the scale systematic were tripled.
* The hammer track is partial (dark object against mixed background); we use
  it only for its landing time and identity, not for a second acceleration
  fit.
* Syllable counts use the official transcript text; the syllable counter is
  a standard vowel-group heuristic (±few %, immaterial against a 2.46×
  discrepancy).

## Reproduce

```bash
cd claims/09-gravity
../../.venv/bin/python run.py     # downloads → tracks → fits → figures → summary.json
```
