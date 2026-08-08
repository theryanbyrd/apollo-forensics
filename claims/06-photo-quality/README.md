# Claim 06 — "The photos are too well-composed for chest-mounted cameras with no viewfinder"

## The claim

Apollo surface photography was shot on Hasselblad 500EL/EDC cameras bolted to
the astronauts' chest packs. No viewfinder, no metering readout, stiff
pressurized gloves, a helmet you can't put to an eyepiece. Hoax proponents
argue the resulting pictures — Aldrin's portrait, the flag salutes, the
bootprint — are impossibly well-framed, well-exposed and level for blind
point-and-hope shooting, therefore a studio (with viewfinders, lighting and
retakes) must have produced them.

## Why this is a survivorship-bias argument

The claim is only ever illustrated with the same few dozen frames. But the
crews exposed **thousands**; the famous ones are the handful that museums,
textbooks and NASA public affairs picked out of the pile precisely *because*
they were the best. So test the pile, not the picks.

**Falsification criterion:** if a systematic (non-hand-picked) sample of the
archive were uniformly excellent — no meaningful bad-frame tail, icons
indistinguishable from the median frame because every frame is excellent —
the survivorship-bias explanation fails and the claim survives this test.

## Data

Source: **LPI Apollo Image Atlas** (Lunar and Planetary Institute), which
hosts a scan of *every* frame of every Apollo 70 mm magazine — including the
black, blank and blurred frames — under a systematic URL:

```
https://www.lpi.usra.edu/resources/apollo/images/{size}/{MISSION}/{MAG}/{FRAME}.jpg
e.g.  https://www.lpi.usra.edu/resources/apollo/images/browse/AS11/40/5903.jpg
```

Sampling design: **five complete EVA-era Hasselblad magazines across four
missions** — every consecutive frame the atlas holds, discovered empirically
by walking frame numbers outward from a seed until three consecutive HTTP
404s on each side (`download.py`). Nothing is hand-picked; the duds are in by
construction. (A few frames inside these magazines were exposed in flight
rather than on the surface — e.g. the AS16-113 rendezvous sequence around
18284–18293 — and are kept: systematic means systematic.)

| Magazine | Context | Frames fetched (empirical range) |
|---|---|---|
| AS11-40 (S)  | Apollo 11, the only surface EVA magazine | 127 (5844–5970) |
| AS12-48 (Z)  | Apollo 12 EVA 2, Surveyor 3 visit (B&W) | 150 (7022–7171) |
| AS12-49 (EE) | Apollo 12 EVA 2 (B&W) | 153 (7172–7324) |
| AS16-113     | Apollo 16 EVAs + rendezvous | 102 (18279–18382) |
| AS17-134 (B) | Apollo 17 EVAs (flag-with-Earth magazine) | 155 (20376–20532) |

**N = 687 in-sample frames.** One extra frame outside the systematic sample
is fetched for the comparison set only and **excluded from all statistics**:
AS17-148-22727 ("Blue Marble", taken in flight, not chest-mounted).

Two sizes were cached (`data/`, gitignored; re-fetch with `python
download.py` then `python download.py --size browse`):

- `browse` (450 px) — covers **every** frame; **all statistics come from
  these** so the scoring pipeline is identical for every frame.
- `print` (~3900 px, stored downscaled to 1400 px) — used only to render
  sharper montage cells where available. Print coverage is itself partial
  and *biased* (full for Apollo 11/12/14, absent for the Apollo 15/16/17
  surface magazines, yet present for famous frames like the Blue Marble) —
  a neat demonstration that even scan resolution follows curation, and the
  reason statistics are computed from browse scans only.

Downloads: identifying User-Agent, single connection, 0.3 s delay between
requests, resumable log.

## Method

`score.py` scores every frame on a standardized basis: grayscale, long side
resized to exactly 448 px (resolution-dependent metrics need a common scale).

| Metric | Meaning |
|---|---|
| `lap_var` | variance of Laplacian, whole frame — global sharpness |
| `content_lap` | variance of Laplacian over *textured* 32×32 blocks only (block std ≥ 6). Global lap_var punishes any composition with a big black sky; this measures whether what IS in frame is sharp |
| `mean_lum`, `p50/p95/p99` | luminance level and percentiles |
| `clip5_frac`, `clip250_frac` | literal clipped-pixel fractions — always ≈0 for these scans: the LPI tone curve lifts the black point to ~15–25 and compresses highlights (verified empirically; max fraction >240 in the whole sample is 0.06), so absolute clipping is meaningless here |
| `dark_frac` | fraction of pixels < 25 ("near-black", scan-adapted) |
| `bright_frac` | fraction of pixels > 240 |
| `featureless_frac` | fraction of 32×32 blocks with std < 6 — blank sky / featureless regolith / washed-out nothing |
| `tilt_deg`, `has_horizon` | length-weighted median angle of near-horizontal Hough lines (Canny + probabilistic Hough, angles within ±35° of horizontal, total length > 0.6×width). Horizon tilt where a horizon exists (572/687 frames) |

**Dud flags** — thresholds calibrated by visual inspection of contact sheets
of each metric band (a correctly exposed lunar shot legitimately contains a
large black sky, so exposure tests are conservative):

| Flag | Threshold | In-sample rate |
|---|---|---|
| `black_frame` | p99 < 50 or dark_frac > 0.97 | 6 (0.9 %) |
| `underexposed` | dark_frac > 0.75, or mean_lum < 30 with p99 < 150 | 17 (2.5 %) |
| `overexposed` | mean_lum > 160 (every such frame is a washed-out sun/flare shot on inspection) or bright_frac > 0.20 | 14 (2.0 %) |
| `blurry` | lap_var < 70 (visibly soft at 448 px, verified on contact sheet) | 25 (3.6 %) |
| `aimless` | featureless_frac > 0.85 | 6 (0.9 %) |
| **`dud`** | **any of the above** | **49 (7.1 %)** |
| `crooked` | detected horizon tilted > 10° — reported separately, *not* counted as a dud | 114 of 572 detected horizons (19.9 %; 16.6 % of all frames) |

Composite `quality` = z-score of log content sharpness minus penalties that
activate only past the dud thresholds. The comparison set is nine endlessly
reproduced icons that fall inside the sampled magazines, plus the
out-of-sample Blue Marble.

Run order: `download.py` → `download.py --size browse` → `score.py` → `plots.py`.

## RESULTS

**687 consecutive frames, 5 complete magazines, 4 missions. 7.1 % are
outright technical failures, and 1 in 5 detectable horizons is tilted more
than 10°.** The archive is exactly what blind chest-mounted shooting with
heavy bracketing looks like: a wide, messy, very human distribution
(`results/dist_metrics.png`), with a genuine outtake reel at the bottom —
frames of pure black, frames obliterated by sun flare, light-struck
magazine-end frames, blurry LM interiors with a barely visible face, an
accidental half-flag in the dark (`results/montage_worst.png`).

The waste rate also *grows* with mission experience — later crews shot more
casually because film was cheap and EVA time was not:

| Magazine | AS11-40 | AS12-48 | AS12-49 | AS16-113 | AS17-134 |
|---|---|---|---|---|---|
| dud rate | 2.4 % | 3.3 % | 5.9 % | 11.8 % | 12.9 % |

**The icons are keepers, not miracles.** 0 of 9 in-sample icons trips any
dud flag, yet on objective pixel metrics they are ordinary-to-good members of
the distribution, not outliers:

| Frame | What it is | Quality pctile | In-mag sharpness pctile | Raw horizon tilt |
|---|---|---|---|---|
| AS11-40-5850 | Armstrong's first surface photo | 37 | 45 | −13.8° |
| AS11-40-5875 | Aldrin salutes the flag | 43 | 54 | +9.7° |
| AS11-40-5877 | Bootprint (pair, 1st) | 75 | 88 | ~0° |
| AS11-40-5878 | Bootprint (pair, 2nd) | 69 | 84 | +5.0° |
| AS11-40-5903 | **Aldrin portrait** | 31 | 32 | **−15.4°** |
| AS12-48-7133 | Conrad at Surveyor 3 | 51 | 29 | ~0° |
| AS12-49-7278 | Bean, Conrad in visor | 14 | 14 | ~0° |
| AS16-113-18339 | Young's jumping salute | 83 | 82 | −7.2° |
| AS17-134-20384 | Cernan, flag and Earth | 68 | 77 | (no horizon found) |

The single best detail in the data: **the most famous photograph of the
20th century, the Aldrin portrait, has a horizon tilted ~15° in the raw
frame** (every published version you have seen is cropped and straightened —
compare `results/montage_icons.png`, which shows the uncropped scan). Its
sharpness sits at the 32nd percentile of its own magazine. The "impossibly
perfect" photo is a technically ordinary frame made iconic by subject,
cropping and selection — the survivorship pipeline in miniature.

Median composite percentile of the nine icons: **50.5** — the icons are drawn
from the comfortable middle-to-upper bulk of a wide distribution, while the
bottom 7 % of that distribution is unpublishable garbage no studio would
ever have manufactured.

Headline numbers live in `results/summary.json`; per-frame scores in
`results/scores.csv`.

## Limitations

- Metrics are computed on modern 450 px JPEG scans of film; scanner
  processing and JPEG compression add noise, and the scan tone curve hides
  literal clipping (documented above). All comparisons are *relative within
  one consistent source*, which is what the survivorship argument needs.
- Laplacian sharpness is scene-dependent: macro regolith shots score higher
  than mid-distance scenes at equal focus quality. `content_lap` corrects
  for empty-sky area but not for subject distance — icon sharpness
  percentiles are indicative, not precise.
- The dud thresholds are calibrated for lunar *surface* photography; applied
  to deep-space shots they misfire (the out-of-sample Blue Marble trips the
  underexposure flag because 80 % of its frame is dark space — a false
  positive, and it is excluded from all statistics anyway).
- Blur vs. subject-in-darkness can overlap in the flags; the montage exists
  so you can eyeball what each flag actually caught. Flags are non-exclusive;
  `dud` is their union.
- Five magazines ≠ the whole archive, but they are *complete consecutive
  rolls* from four missions — exactly the sampling the claim's proponents
  never do.

## Verdict

**REFUTED — survivorship bias, quantified.** The falsification criterion
fails to trigger: the archive is nowhere near uniformly excellent. 7.1 % of
687 systematically sampled frames are outright duds, a fifth of detectable
horizons are visibly crooked, and the per-magazine dud rate runs up to 12.9 %. The
famous frames the claim is built on are not statistical impossibilities —
they are unremarkable members of the distribution's better half, selected
after the fact, then cropped and straightened for publication (the Aldrin
portrait's raw horizon is tilted 15°). NASA's own archive contains the
outtake reel — black frames, sun-blasted washouts, blurred boots and empty
regolith — that no hoax studio would have needed, produced, or released.
