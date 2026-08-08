#!/usr/bin/env python3
"""
Claim 06 — turn results/scores.csv into the article artifacts:

  results/dist_metrics.png    histograms + CDFs of each quality metric,
                              iconic frames marked (upper-tail visualization)
  results/montage_worst.png   the 48 worst frames of the systematic sample,
                              with frame IDs — NASA's outtakes
  results/montage_icons.png   the iconic comparison frames, with IDs
  results/summary.json        headline numbers for the repo index
"""

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
FRAMES = os.path.join(DATA, "frames")     # 1400px reductions of print scans (partial coverage)
BROWSE = os.path.join(DATA, "browse")     # 450px browse scans (full coverage; scoring source)
RESULTS = os.path.join(HERE, "results")
SCORES = os.path.join(RESULTS, "scores.csv")

ICON_COLOR = "#d62728"


def frame_path(fid):
    """Best available image for display: print reduction, else browse scan."""
    p = os.path.join(FRAMES, fid + ".jpg")
    return p if os.path.exists(p) else os.path.join(BROWSE, fid + ".jpg")


def pctile(series, value):
    return 100.0 * (series < value).mean()


def dist_plot(df):
    ins = df[df.in_sample == 1]
    icons = df[df.icon == 1]
    specs = [
        ("lap_var", "Sharpness: variance of Laplacian (whole frame)", True),
        ("content_lap", "Content sharpness (textured blocks only)", True),
        ("mean_lum", "Mean luminance (8-bit)", False),
        ("dark_frac", "Near-black fraction (<25; scan black point ~15-25)", False),
        ("featureless_frac", "Featureless fraction (blank sky/regolith)", False),
        ("tilt_deg", "Horizon tilt (deg, where horizon found)", False),
    ]
    fig, axes = plt.subplots(3, 4, figsize=(19, 11))
    fig.suptitle(
        f"The whole roll, not the highlight reel — {len(ins)} consecutive frames from 5 complete "
        "Apollo surface magazines (LPI Apollo Image Atlas)\n"
        "red = the famous 'too-well-composed' frames", fontsize=14)
    for i, (col, title, logx) in enumerate(specs):
        ax_h = axes[i // 2, (i % 2) * 2]
        ax_c = axes[i // 2, (i % 2) * 2 + 1]
        x = ins[col].dropna()
        if logx:
            bins = np.logspace(np.log10(max(x.min(), 1e-2)), np.log10(x.max()), 45)
            ax_h.set_xscale("log")
            ax_c.set_xscale("log")
        else:
            bins = 45
        ax_h.hist(x, bins=bins, color="#7f9fc4", edgecolor="white", linewidth=0.3)
        ax_h.set_title(title, fontsize=10)
        ax_h.set_ylabel("frames")
        xs = np.sort(x.values)
        ax_c.plot(xs, np.arange(1, len(xs) + 1) / len(xs) * 100, color="#40607f")
        ax_c.set_ylabel("CDF %")
        ax_c.set_title(title + " — CDF", fontsize=10)
        for _, r in icons.iterrows():
            v = r[col]
            if pd.isna(v):
                continue
            ax_h.axvline(v, color=ICON_COLOR, alpha=0.7, linewidth=1)
            ax_c.plot([v], [pctile(x, v)], "o", color=ICON_COLOR, ms=5, alpha=0.8)
        ax_h.plot([], [], color=ICON_COLOR, label="iconic frames")
        ax_h.legend(fontsize=7, loc="upper right")
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    out = os.path.join(RESULTS, "dist_metrics.png")
    plt.savefig(out, dpi=110)
    plt.close()
    print("wrote", out)


def load_font(size):
    for cand in ["/System/Library/Fonts/Helvetica.ttc",
                 "/System/Library/Fonts/Supplemental/Arial.ttf"]:
        if os.path.exists(cand):
            try:
                return ImageFont.truetype(cand, size)
            except Exception:
                pass
    return ImageFont.load_default()


def montage(rows, out_path, title, cell=320, cols=8, note_col=None):
    n = len(rows)
    rows_n = int(np.ceil(n / cols))
    pad, cap, head = 6, 40, 64
    W = cols * (cell + pad) + pad
    H = head + rows_n * (cell + cap + pad) + pad
    canvas = Image.new("RGB", (W, H), (12, 12, 14))
    draw = ImageDraw.Draw(canvas)
    f_head = load_font(30)
    f_cap = load_font(17)
    f_note = load_font(14)
    draw.text((pad + 4, 16), title, fill=(235, 235, 235), font=f_head)
    for i, (_, r) in enumerate(rows.iterrows()):
        cx = pad + (i % cols) * (cell + pad)
        cy = head + (i // cols) * (cell + cap + pad)
        try:
            im = Image.open(frame_path(r["id"])).convert("RGB")
        except Exception:
            continue
        im.thumbnail((cell, cell), Image.LANCZOS)
        ox = cx + (cell - im.size[0]) // 2
        oy = cy + (cell - im.size[1]) // 2
        canvas.paste(im, (ox, oy))
        draw.text((cx + 2, cy + cell + 4), r["id"], fill=(255, 210, 90), font=f_cap)
        if note_col:
            note = str(r[note_col])[:38]
            draw.text((cx + 2, cy + cell + 23), note, fill=(170, 170, 175), font=f_note)
    canvas.save(out_path)
    print("wrote", out_path, canvas.size)


def dud_reasons(r):
    reasons = []
    if r.black_frame:
        reasons.append("black frame")
    elif r.underexposed:
        reasons.append("underexposed")
    if r.overexposed:
        reasons.append("flare/overexposed")
    if r.blurry:
        reasons.append("blurry")
    if r.aimless:
        reasons.append("aimless/featureless")
    return ", ".join(reasons) if reasons else "low composite quality"


def main():
    df = pd.read_csv(SCORES)
    ins = df[df.in_sample == 1].copy()
    icons = df[df.icon == 1].copy()

    dist_plot(df)

    worst = ins.sort_values("quality").head(48).copy()
    worst["why"] = worst.apply(dud_reasons, axis=1)
    montage(worst, os.path.join(RESULTS, "montage_worst.png"),
            "Apollo's outtakes — the 48 worst of %d consecutive Hasselblad frames (chest-mounted, no viewfinder)" % len(ins),
            note_col="why")

    icons_sorted = icons.sort_values(["mission", "magazine", "frame"])
    montage(icons_sorted, os.path.join(RESULTS, "montage_icons.png"),
            "The comparison set — the frames the claim is built on",
            cell=340, cols=5, note_col="icon_label")

    # headline stats
    ins_icons = icons[icons.in_sample == 1]
    icon_rows = {}
    for _, r in ins_icons.iterrows():
        mag = ins[(ins.mission == r.mission) & (ins.magazine == r.magazine)]
        icon_rows[r["id"]] = {
            "quality_pctile_overall": round(pctile(ins.quality, r.quality), 1),
            "content_sharpness_pctile_in_magazine": round(pctile(mag.content_lap, r.content_lap), 1),
            "tilt_deg": None if pd.isna(r.tilt_deg) else round(float(r.tilt_deg), 1),
            "is_dud": int(r.dud),
        }
    med_icon_pct = float(np.median([v["quality_pctile_overall"] for v in icon_rows.values()]))
    horizon = ins[ins.has_horizon == 1]
    stats = {
        "n_scored": int(len(ins)),
        "n_icons_in_sample": int(len(ins_icons)),
        "n_icon_duds": int(ins_icons.dud.sum()),
        "pct_black_frame": round(100 * ins.black_frame.mean(), 1),
        "pct_underexposed": round(100 * ins.underexposed.mean(), 1),
        "pct_overexposed": round(100 * ins.overexposed.mean(), 1),
        "pct_blurry": round(100 * ins.blurry.mean(), 1),
        "pct_aimless": round(100 * ins.aimless.mean(), 1),
        "pct_dud": round(100 * ins.dud.mean(), 1),
        "pct_crooked_horizon_gt10deg": round(100 * ins.crooked.sum() / max(len(horizon), 1), 1),
        "median_abs_tilt_deg": round(float(horizon.tilt_deg.abs().median()), 1),
        "icons": icon_rows,
        "median_icon_quality_percentile": med_icon_pct,
        "dud_rate_by_magazine": {f"{m}-{g}": round(100 * grp.dud.mean(), 1)
                                 for (m, g), grp in ins.groupby(["mission", "magazine"])},
        "magazines": {f"{m}-{g}": int(len(grp))
                      for (m, g), grp in ins.groupby(["mission", "magazine"])},
    }
    print(json.dumps(stats, indent=2))

    summary = {
        "claim": 6,
        "title": "Photos too good for chest cameras",
        "verdict": "REFUTED - survivorship bias: the archive has a thick tail of genuinely bad frames; "
                   "the famous photos are the curated top of a wide, human distribution",
        "headline": (f"{stats['n_scored']} consecutive frames from 5 complete Apollo surface magazines scored: "
                     f"{stats['pct_dud']}% are outright duds (black, washed-out, blurred or aimless) and "
                     f"{stats['pct_crooked_horizon_gt10deg']}% of detectable horizons are tilted >10 deg, "
                     f"yet 0 of {stats['n_icons_in_sample']} iconic frames is a dud (median composite percentile "
                     f"{med_icon_pct:.0f}) - and even the Aldrin portrait's raw horizon is tilted ~15 deg, "
                     f"fixed only by publication cropping."),
        "impressive": "results/montage_worst.png - 48 genuine NASA outtakes (black frames, lens flare, "
                      "blurry regolith, aimless sky) with frame IDs",
        "stats": stats,
    }
    with open(os.path.join(RESULTS, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
    print("wrote", os.path.join(RESULTS, "summary.json"))


if __name__ == "__main__":
    main()
