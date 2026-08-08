#!/usr/bin/env python3
"""
Claim 06 — score every downloaded frame on objective quality metrics.

All metrics are computed from the LPI *browse* scans (450 px), the only size
that covers EVERY frame of every magazine, on a standardized basis:
grayscale, long side resized to exactly 448 px (metrics like
variance-of-Laplacian are resolution-dependent, so every frame is scored at
the same scale from the same source pipeline).  The partial-coverage "print"
scans are deliberately NOT used for statistics — their coverage is itself
biased toward famous missions/frames.

Metrics
-------
lap_var          variance of the Laplacian over the whole frame
content_lap      variance of the Laplacian over *textured* 32x32 blocks only
                 (std-dev >= 6).  Global lap_var punishes any composition with
                 a large black sky; content_lap measures whether what IS in
                 the frame is sharp.  0 if fewer than 5% of blocks have texture.
mean_lum         mean 8-bit luminance
clip5_frac       fraction of pixels < 5   (literal clipped shadows — always ~0
                 for LPI scans, whose black point is lifted to ~15-25)
clip250_frac     fraction of pixels > 250 (literal clipped highlights — also
                 ~0: the scan tone curve compresses highlights, verified
                 empirically, max bright_frac in sample = 0.06)
dark_frac        fraction of pixels < 25  (scan-adapted "near-black")
bright_frac      fraction of pixels > 240
p50/p95/p99      luminance percentiles (robust exposure descriptors)
featureless_frac fraction of 32x32 blocks whose std-dev < 6 ("nothing there":
                 black sky, blank regolith, washed-out flare)
tilt_deg         length-weighted median angle of near-horizontal Hough lines
                 (|angle| <= 35 deg), i.e. horizon/eyeline tilt where one exists
has_horizon      1 if enough near-horizontal line length was found to trust tilt

Dud flags — thresholds calibrated by visual inspection of contact sheets of
the metric bands (see README).  A correctly exposed lunar surface shot
legitimately contains a large black sky, so the exposure tests are
deliberately conservative:
  black_frame   p99 < 50 or dark_frac > 0.97      essentially nothing recorded
  underexposed  (dark_frac > 0.75 or (mean_lum < 30 and p99 < 150)) and not
                black_frame                        subject lost in darkness
  overexposed   mean_lum > 160 or bright_frac > 0.20   sun-washed / heavy
                flare (every sampled frame with mean_lum > 160 is a washed-out
                sun/flare shot on visual inspection)
  blurry        lap_var < 70 and not black_frame   visibly soft at 448 px
  aimless       featureless_frac > 0.85 and not black_frame   mostly empty
  dud           any of the above
  crooked       |tilt_deg| > 10 with a detected horizon — reported separately,
                NOT counted as a dud (a tilted horizon is a framing blemish,
                not a failed photograph)

Composite quality score (for ranking best/worst; z-scores within the
in-sample distribution):
  quality = z(log10 lap_var) - 2*max(0, bright_frac-0.05)*10
            - 2*max(0, featureless_frac-0.5) - max(0, (25-mean_lum)/25)*2

Outputs results/scores.csv
"""

import csv
import os

import cv2
import numpy as np
import pandas as pd
from tqdm import tqdm

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
FRAMES = os.path.join(DATA, "browse")
MANIFEST = os.path.join(DATA, "manifest_browse.csv")
RESULTS = os.path.join(HERE, "results")
SCORES = os.path.join(RESULTS, "scores.csv")

SCORE_SIDE = 448
BLOCK = 32
FLAT_STD = 6.0

# The comparison set: famous, endlessly reproduced frames that happen to fall
# in (or, marked out-of-sample, beside) the systematically sampled magazines.
ICONS = {
    "AS11-40-5850": "Armstrong: first photo taken on the lunar surface",
    "AS11-40-5875": "Aldrin salutes the U.S. flag",
    "AS11-40-5877": "Aldrin's bootprint (soil-mechanics pair, 1st)",
    "AS11-40-5878": "Aldrin's bootprint (soil-mechanics pair, 2nd)",
    "AS11-40-5903": "Aldrin portrait ('the visor shot')",
    "AS12-48-7133": "Conrad at Surveyor 3, LM on the horizon",
    "AS12-49-7278": "Bean with sample container, Conrad in visor",
    "AS16-113-18339": "Young's jumping flag salute",
    "AS17-134-20384": "Cernan with the flag, Earth above",
    "AS17-148-22727": "Blue Marble (in flight, out-of-sample)",
}


def score_image(path):
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None
    h, w = img.shape
    scale = SCORE_SIDE / max(h, w)
    img = cv2.resize(img, (round(w * scale), round(h * scale)),
                     interpolation=cv2.INTER_AREA)
    h, w = img.shape

    lap_var = float(cv2.Laplacian(img, cv2.CV_64F).var())
    mean_lum = float(img.mean())
    clip5_frac = float((img < 5).mean())
    clip250_frac = float((img > 250).mean())
    dark_frac = float((img < 25).mean())
    bright_frac = float((img > 240).mean())
    p50, p95, p99 = (float(v) for v in np.percentile(img, [50, 95, 99]))

    # featureless fraction: 32x32 block std-dev
    hb, wb = h // BLOCK, w // BLOCK
    crop = img[:hb * BLOCK, :wb * BLOCK].astype(np.float64)
    blocks = crop.reshape(hb, BLOCK, wb, BLOCK).transpose(0, 2, 1, 3)
    stds = blocks.reshape(hb, wb, -1).std(axis=2)
    featureless_frac = float((stds < FLAT_STD).mean())

    # content sharpness: Laplacian variance restricted to textured blocks
    lap = cv2.Laplacian(img, cv2.CV_64F)[:hb * BLOCK, :wb * BLOCK]
    lap_blocks = lap.reshape(hb, BLOCK, wb, BLOCK).transpose(0, 2, 1, 3).reshape(hb, wb, -1)
    textured = stds >= FLAT_STD
    if textured.mean() >= 0.05:
        content_lap = float(lap_blocks[textured].var())
    else:
        content_lap = 0.0

    # tilt of dominant near-horizontal structure
    edges = cv2.Canny(img, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 360, threshold=40,
                            minLineLength=w // 5, maxLineGap=6)
    tilt_deg, has_horizon = np.nan, 0
    if lines is not None and len(lines):
        angs, lens = [], []
        for x1, y1, x2, y2 in np.asarray(lines).reshape(-1, 4):
            ang = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            if ang > 90:
                ang -= 180
            if ang < -90:
                ang += 180
            if abs(ang) <= 35:
                angs.append(ang)
                lens.append(np.hypot(x2 - x1, y2 - y1))
        if angs and sum(lens) > 0.6 * w:
            order = np.argsort(angs)
            angs = np.array(angs)[order]
            lens = np.array(lens)[order]
            cum = np.cumsum(lens)
            tilt_deg = float(angs[np.searchsorted(cum, cum[-1] / 2)])
            has_horizon = 1

    return dict(lap_var=lap_var, content_lap=content_lap, mean_lum=mean_lum,
                clip5_frac=clip5_frac, clip250_frac=clip250_frac,
                dark_frac=dark_frac, bright_frac=bright_frac,
                p50=p50, p95=p95, p99=p99,
                featureless_frac=featureless_frac,
                tilt_deg=tilt_deg, has_horizon=has_horizon)


def main():
    os.makedirs(RESULTS, exist_ok=True)
    man = pd.read_csv(MANIFEST)
    man = man[man.status == "ok"].copy()
    rows = []
    for _, r in tqdm(man.iterrows(), total=len(man), desc="scoring"):
        path = os.path.join(FRAMES, r["id"] + ".jpg")
        m = score_image(path)
        if m is None:
            print("unreadable:", r["id"])
            continue
        m.update(id=r["id"], mission=r["mission"], magazine=int(r["magazine"]),
                 frame=int(r["frame"]), in_sample=int(r["in_sample"]),
                 icon=int(r["id"] in ICONS),
                 icon_label=ICONS.get(r["id"], ""))
        rows.append(m)
    df = pd.DataFrame(rows)

    # dud flags (see module docstring / README for threshold rationale)
    df["black_frame"] = ((df.p99 < 50) | (df.dark_frac > 0.97)).astype(int)
    df["underexposed"] = (((df.dark_frac > 0.75) |
                           ((df.mean_lum < 30) & (df.p99 < 150)))
                          & (df.black_frame == 0)).astype(int)
    df["overexposed"] = ((df.mean_lum > 160) | (df.bright_frac > 0.20)).astype(int)
    df["blurry"] = ((df.lap_var < 70) & (df.black_frame == 0)).astype(int)
    df["aimless"] = ((df.featureless_frac > 0.85) & (df.black_frame == 0)).astype(int)
    df["dud"] = ((df.black_frame | df.underexposed | df.overexposed |
                  df.blurry | df.aimless) > 0).astype(int)
    df["crooked"] = ((df.has_horizon == 1) & (df.tilt_deg.abs() > 10)).astype(int)

    # composite quality: content sharpness z-score, minus penalties that
    # activate only past the dud thresholds (black sky per se is not a flaw)
    ins = df[df.in_sample == 1]
    logc = np.log10(df.content_lap.clip(lower=1.0))
    mu, sd = np.log10(ins.content_lap.clip(lower=1.0)).mean(), np.log10(ins.content_lap.clip(lower=1.0)).std()
    df["quality"] = ((logc - mu) / sd
                     - 3 * df.black_frame - 2 * df.underexposed
                     - 2 * df.overexposed - 1.5 * df.aimless)

    df = df.sort_values(["mission", "magazine", "frame"])
    cols = ["id", "mission", "magazine", "frame", "in_sample", "icon", "icon_label",
            "lap_var", "content_lap", "mean_lum", "clip5_frac", "clip250_frac",
            "dark_frac", "bright_frac", "p50", "p95", "p99", "featureless_frac",
            "tilt_deg", "has_horizon", "black_frame", "underexposed", "overexposed",
            "blurry", "aimless", "dud", "crooked", "quality"]
    df[cols].to_csv(SCORES, index=False, quoting=csv.QUOTE_MINIMAL)
    ins = df[df.in_sample == 1]
    print(f"\nscored {len(df)} frames ({len(ins)} in-sample) -> {SCORES}")
    for flag in ["black_frame", "underexposed", "overexposed", "blurry", "aimless", "dud", "crooked"]:
        print(f"  {flag:14s} {ins[flag].sum():4d}  ({100*ins[flag].mean():.1f}%)")
    print("\nicons:")
    for _, r in df[df.icon == 1].iterrows():
        pct = 100.0 * (ins.quality < r.quality).mean()
        print(f"  {r['id']:16s} quality={r.quality:+.2f} ({pct:.0f}th pctile) lap_var={r.lap_var:.0f} {r.icon_label}")


if __name__ == "__main__":
    main()
