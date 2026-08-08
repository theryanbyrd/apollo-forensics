# Claim 7 — The "C" rock (AS16-107-17446)

**Claim.** Apollo 16 frame AS16-107-17446 (Station 4, EVA-2, the down-sun locator shot of
sample 64435 with Charlie Duke and the rover in the background) shows a foreground rock
carrying a neat letter **"C"**, with a second, fainter "C" on the ground nearby — allegedly a
props-department inventory mark photographed on a studio set.

**Falsification criterion (fixed before analysis).**

* If the mark is present in the earliest-generation scans of the **original flight film**,
  with in-scene characteristics (modulated by the rock's texture and lighting), the prop
  claim is **supported**.
* If the mark is **absent from every film scan** and present **only in one print
  generation**, with the characteristics of a fiber lying on duplicating/printing equipment
  (smooth, continuous, uniform stroke sitting *on top of* the film grain), the claim is
  **refuted**, with provenance.

## Method

1. **Acquisition** — ten independently archived versions of the same frame (table below),
   spanning the duplication chain: two scans of the original flight film (March to the Moon
   full-resolution 14,160 px scan and the Project Apollo Archive 4,175 px scan), four
   print/dupe scans from NASA and LPI archives (GRIN, spaceflight.nasa.gov 2002, JSC Digital
   Image Collection early-90s digitization, LPI Apollo Image Atlas), and three copies of the
   **C-bearing print generation** — including the hoax sites' own crop and the
   high-resolution re-scan of that print made by LPI.
2. **Registration** — every version is registered to a common reference frame (the PAA film
   scan's rock region) with SIFT features + FLANN matching + RANSAC homographies
   (two-stage: coarse full-frame, then native-resolution refinement on the rock
   neighbourhood; 295–4,405 inliers). The blurry LPI fiber re-scan, which has too few SIFT
   features, is registered by multi-scale normalized cross-correlation onto the classic crop
   (r = 0.923) and composed through the classic crop's homography.
3. **Comparison** — identical physical crops across all generations (the money shot);
   histogram-matched absolute-difference and SSIM maps; intensity cross-sections through the
   C stroke along the *same physical line* in every version; stroke-mask contrast,
   visibility z-score and arc-coherence statistics; a 400-sample null distribution of
   C-shaped masks placed randomly on the rock's film-scan surface; LAB chroma analysis of
   the fiber; and the same comparison at the "second C" ground location.

Reproduce with `../../.venv/bin/python run.py` (downloads everything except the optional
260 MB full-res film scan; add `--download-full` for that). All numbers below are printed by
`run.py` and stored in `results/summary.json`.

## Image provenance

| key | source / URL | what it is | generation |
|---|---|---|---|
| `mttm_full` | [tothemoon.im-ldi.com … processed/AS16-107-17446.png](https://tothemoon.im-ldi.com/data_a70/AS16/processed/AS16-107-17446.png) | March to the Moon (NASA JSC film-preservation scans, hosted by ASU), 14160×16020 px | **original flight film** |
| `mttm_med` | [tothemoon.im-ldi.com … AS16-107-17446.med.png](https://tothemoon.im-ldi.com/data_a70/AS16/extra/AS16-107-17446.med.png) | same scan, 3540×4005 px reduction | original flight film |
| `paa` | [Wikimedia Commons mirror](https://commons.wikimedia.org/wiki/File:AS16-107-17446_(21651763756).jpg) of the Project Apollo Archive Flickr original, 4175×4175 px | JSC 2004 scans of the original film | original flight film |
| `grin` | [NASA GRIN GPN-2000-001123 via Commons](https://commons.wikimedia.org/wiki/File:Duke_on_the_Descartes_-_GPN-2000-001123.jpg), 3000×3104 px | scan of a paper print (~2000) | film → dupe → print |
| `sf2002` | [Wayback 2002 capture of spaceflight.nasa.gov hires](http://web.archive.org/web/20021116111956/http://spaceflight.nasa.gov/gallery/images/apollo/apollo16/hires/as16-107-17446.jpg), 2830×3000 px | NASA JSC web gallery print/dupe scan | film → dupe → print |
| `jsc90s` | [Wayback 2005 capture of images.jsc.nasa.gov lores](http://web.archive.org/web/20051217225605/http://images.jsc.nasa.gov/lores/AS16-107-17446.jpg), 640×480 px | JSC Digital Image Collection, digitized early 1990s ("Image Alchemy v1.6.2" JPEG comment) | film → dupe → print |
| `lpi450` | [LPI Apollo Image Atlas browse image](https://www.lpi.usra.edu/resources/apollo/images/browse/AS16/107/17446.jpg), 450×450 px (byte-identical since ≥2013) | LPI print scan | film → dupe → print |
| `classic` | [Commons "Apollo16CRock.jpg"](https://commons.wikimedia.org/wiki/File:Apollo16CRock.jpg), 329×301 px — "Close up from some prints of Apollo 16 photo AS16-107-17446" | **the C-bearing print generation**, the crop that hoax sites circulate | film → internegative **with fiber** → print |
| `aulis` | Aulis.com annotated crop (250×164 px), preserved in [moonhoaxdebunked fig 5.15-1](https://moonhoaxdebunked.blogspot.com/2017/07/514-how-come-theres-letter-c-on-rock.html) | hoax-proponent version of the same print generation | same C-bearing print |
| `lpihair` | LPI high-resolution re-scan of the C-bearing print (340×314 px crop), supplied by LPI, preserved in [moonhoaxdebunked fig 5.15-3](https://moonhoaxdebunked.blogspot.com/2017/07/514-how-come-theres-letter-c-on-rock.html) | the "C" resolved: a curled **fiber** with a protruding tail, plus a second hair in the crop's top-left corner | same C-bearing print, rescanned at high res |

All raw files are cached in `data/` (gitignored); `run.py` re-fetches them from the URLs above.

## Results

**Where the C is.** Registered to the film scan, the mark sits on the rock's upper-left face
at PAA pixel (1054, 2868), bounding box 78×65 reference px ≈ **1.03 × 0.86 mm at
original-film scale** — exactly hair-scale for a 70 mm duplicate or an enlarger stage.

**Per-generation statistics at the identical registered C mask** (contrast = how much darker
the mask pixels are than the surrounding rock face; coherence = fraction of mask pixels ≥8%
darker than local background — a continuous stroke scores ≈1, random grain ≈0.1–0.3):

| generation | kind | contrast | coherence | verdict |
|---|---|---:|---:|---|
| March to the Moon full (14160 px) | film | 2.2 % | 0.17 | **no C** |
| March to the Moon med | film | 2.2 % | 0.16 | **no C** |
| Project Apollo Archive | film | 1.3 % | 0.08 | **no C** |
| NASA GRIN print scan | print | 4.0 % | 0.33 | **no C** |
| spaceflight.nasa.gov 2002 hires | print | 2.6 % | 0.22 | **no C** |
| JSC Digital Image Collection (early 90s) | print | 13.6 % | 0.65 | unresolved dark smudge at the C location |
| LPI Atlas browse (450 px) | print | 0.3 % | 0.00 | below resolution |
| **C-bearing print crop (classic)** | c-print | **15.5 %** | **0.99** | **C PRESENT** |
| **Aulis.com crop** | c-print | **38.7 %** | **0.99** | **C PRESENT** |
| **LPI high-res re-scan of that print** | c-print | **13.5 %** | **0.76** | **C PRESENT** |

**Cross-sections** (same physical line through the stroke in every version, intensity as %
of local median): the C-bearing versions dip **21.8 %** (classic), **50.3 %** (aulis) and
**29.9 %** (LPI re-scan) below background with stroke FWHM 0.05–0.10 mm at film scale; at
the same coordinates the film scans dip only **1.8 %** (PAA) and **4.0 %** (MttM full) —
indistinguishable from grain. (`results/stroke_cross_sections.png`)

**Difference / SSIM maps** (`results/difference_maps.png`): after histogram matching, the
C-bearing print differs from the film scan by a mean of **14.7 gray levels inside the C
mask vs 2.6 elsewhere** — the C is the only structured difference; the control pair (GRIN
print scan vs film scan) shows 2.7 at the mask vs 3.0 elsewhere, i.e. nothing.

**Fiber characteristics** (`results/fiber_texture_analysis.png`):

* In LPI's high-resolution re-scan the "letter" resolves into a smooth, continuous curled
  filament with a **tail extending past the top of the arc** — and a **second hair** lies in
  the top-left corner of the same crop. Letters don't have tails and don't shed.
* Chroma: the stroke is **yellow-brown** (mean LAB b = 134.7) against a near-neutral gray
  rock (b = 129.2) — the color of an organic hair, not of a shadowed marking on gray
  breccia.
* Correlation between stroke darkness and the underlying surface brightness is **−0.01**:
  the mark is completely unmodulated by the rock it supposedly sits on — it lies on top of
  the image, not in the scene.
* Null test: the same C-shaped mask placed at 400 random offsets on the rock's film-scan
  face never exceeds **4.1 %** contrast; the real C measures **15.5 %** in the C-bearing
  print, while the *same pixels* in the film scan measure **1.3 %** (an unremarkable 48th
  percentile of the null distribution).

**The second "C" on the ground** (`results/ground_c_comparison.png`): at the location the
hoax annotation points to, every generation — film scans and print scans alike — shows the
identical cluster of native terrain shadows. Nothing appears in the print generation that
is not already on the original film: the "ground C" is pareidolia on real dirt relief.

**A bonus corroboration:** the early-1990s JSC Digital Image Collection scan (640×480, a
different digitization lineage from all the others) shows a dark smudge at exactly the
registered C location (13.6 % contrast, coherence 0.65) — too small to resolve into a
letter, but consistent with it deriving from the same physically marked print, which the
historical record says hung around NASA/LPI collections from the late 1980s on.

## Verdict: REFUTED

The "C" does not exist on the Moon, and it does not exist on the original film. It exists in
exactly one branch of the duplication tree — a print generation of which we obtained three
independent copies — and at high resolution it is unambiguously a ~1 mm curled fiber (with a
tail, accompanied by a second hair) that landed on duplicating/printing equipment. Every
scan of the original flight film, including a 14,160-pixel preservation scan, shows bare
rock at the same registered coordinates at grain-level noise (≤2.2 % contrast). A prop
inventory mark photographed in the scene would appear in *every* generation; a fiber on one
internegative or enlarger appears only downstream of that one duplicate. The evidence
matches the fiber, exclusively.

## Limitations

* The C-bearing versions survive only as web-resolution crops (250–340 px) plus the 640 px
  early-90s JSC scan; the original marked print/internegative itself is not online. The
  three copies are consistent with a single print generation, and the LPI re-scan's
  provenance (LPI supplied it to debunk researchers, published 2017) is documented but
  secondary — it is preserved on a blog, not on lpi.usra.edu.
* The Aulis crop carries hoax-site annotations (white arrows/letters) that slightly
  contaminate its background statistics; its C-mask numbers are still reported unmodified.
* The two lowest-resolution versions (LPI 450 px browse, JSC 640 px) map the ~8-reference-px
  stroke to under 1.2 native pixels, so present/absent cannot be adjudicated there; they are
  labeled accordingly rather than counted for either side.
* Registration of the low-resolution versions uses the coarse full-frame homography (the
  native-resolution refinement lacks features), leaving a few reference pixels of possible
  misalignment — irrelevant at the C's 78×65 px scale.
