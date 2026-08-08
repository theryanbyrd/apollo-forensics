#!/usr/bin/env python3
"""Helper used during manual digitization of shadow endpoints.

Renders a crop of a full-resolution scan with a labeled coordinate grid
(in FULL-IMAGE pixel coordinates) so that point coordinates can be read
off visually and recorded in annotations_*.json. This is the documented
process by which every hand-digitized coordinate in this claim was
obtained: view crop -> read coordinate off grid -> record + uncertainty.

Usage:
  python digitize_helper.py IMAGE X0 Y0 X1 Y1 OUT [--step N] [--scale S]
"""
import sys
import argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("x0", type=int)
    ap.add_argument("y0", type=int)
    ap.add_argument("x1", type=int)
    ap.add_argument("y1", type=int)
    ap.add_argument("out")
    ap.add_argument("--step", type=int, default=50, help="grid step, px")
    ap.add_argument("--width", type=float, default=11, help="figure width in")
    ap.add_argument("--gamma", type=float, default=1.0, help="brighten shadows")
    args = ap.parse_args()

    im = np.asarray(Image.open(args.image).convert("L"), dtype=np.float64) / 255.0
    crop = im[args.y0:args.y1, args.x0:args.x1]
    if args.gamma != 1.0:
        crop = crop ** (1.0 / args.gamma)

    h, w = crop.shape
    fig_w = args.width
    fig_h = fig_w * h / w + 0.6
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=110)
    ax.imshow(crop, cmap="gray", vmin=0, vmax=1,
              extent=[args.x0, args.x1, args.y1, args.y0], interpolation="nearest")
    xt = np.arange(args.x0 - args.x0 % args.step + args.step, args.x1, args.step)
    yt = np.arange(args.y0 - args.y0 % args.step + args.step, args.y1, args.step)
    ax.set_xticks(xt)
    ax.set_yticks(yt)
    ax.grid(color="red", alpha=0.45, linewidth=0.5)
    ax.tick_params(labelsize=7)
    plt.setp(ax.get_xticklabels(), rotation=90)
    ax.set_title(f"{args.image.split('/')[-1]}  crop x[{args.x0}:{args.x1}] y[{args.y0}:{args.y1}]",
                 fontsize=8)
    fig.tight_layout()
    fig.savefig(args.out)
    print("wrote", args.out)


if __name__ == "__main__":
    main()
