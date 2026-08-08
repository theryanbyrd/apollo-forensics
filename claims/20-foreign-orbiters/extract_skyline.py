#!/usr/bin/env python
"""Extract the terrain skyline from Apollo 15 surface photographs and
convert it to angular coordinates (azimuth offset, elevation) using the
Hasselblad camera geometry.

Geometry:
  - Camera: Hasselblad 500EL Data Camera, Zeiss Biogon 5.6/60,
    calibrated focal length ~61.1 mm (nominal "60 mm"). The film carries
    a reseau plate: a grid of '+' crosses spaced exactly 10 mm apart.
  - The scans are 4175 x 4175 px Project Apollo Archive film scans that
    include the film borders, so the pixel scale is recovered from the
    reseau crosses themselves (median cross spacing / 10 mm), not from
    the scan size. Measured: 75.2 px/mm on both frames.
  - A pixel at (dx, dy) from the principal point maps to a ray with
      azimuth offset  = atan(dx_mm / f)
      elevation       = atan(-dy_mm / sqrt(f^2 + dx_mm^2))
    (valid for a level camera; unknown camera pitch/roll/yaw are fitted
    later in match_skyline.py).

Skyline detection: a dynamic-programming seam tracker. For every pixel a
cost rewards a sky->terrain brightness transition (short- and medium-
window vertical gradients); the skyline is the connected left-to-right
path of maximum total reward with a slope limit. This survives the
veiling glare in AS15-86-11603, where the sky next to the sunlit summit
of Mons Hadley is nearly as bright as the mountain flank and only the
thin sunlit crest marks the ridge. Columns where mission hardware (LM,
Rover high-gain antenna) pokes above the terrain skyline, or where the
skyline is a shadowed flank lost against the sky, are masked by hand-set
column ranges (documented below, verified in results/skyline_*.png).

Outputs: results/skyline_<frame>.npz  (az_off_deg, elev_deg, col, row,
         px_per_mm, confidence) and results/skyline_<frame>.png.
"""
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
RESULTS = HERE / "results"

FOCAL_MM = 61.1          # calibrated focal length of the A15 EDC 60mm Biogon
RESEAU_SPACING_MM = 10.0

PHOTOS = {
    "AS15-88-11866": {
        # Jim salutes the flag; Mons Hadley Delta skyline to the south.
        # The flag and astronaut stay below the skyline. Masked: the LM
        # (cols 1700-2830) and the Rover high-gain antenna (3380-3810)
        # cross the skyline.
        "mask_cols": [(1700, 2830), (3380, 3810)],
        "cols": (150, 4045),        # usable column span
        "band": (200, 1900),        # rows that can contain the skyline
    },
    "AS15-86-11603": {
        # Jim at the Rover, end of EVA-1; Mons Hadley skyline to the NE.
        # Cols < 1500 masked: there the skyline is Mons Hadley's shadowed
        # WNW flank, black against black sky (and the Rover's high-gain
        # dish rim sits in front of it) - not recoverable.
        # Row band capped at 1300: the true skyline stays above that row
        # everywhere in-frame, and the cap keeps the tracker off the
        # Rover's bright top edges below.
        "mask_cols": [(0, 1500)],
        "cols": (150, 3990),
        "band": (200, 1300),
    },
}


def detect_reseau(a: np.ndarray) -> tuple[float, list]:
    """Find reseau '+' crosses; return px spacing and cross positions."""
    small = cv2.resize(a, None, fx=0.5, fy=0.5,
                       interpolation=cv2.INTER_AREA)
    bg = cv2.medianBlur(small, 31)
    resid = cv2.subtract(bg, small)     # crosses are dark -> positive resid
    t = np.zeros((37, 37), np.float32)  # plus-shaped template
    t[17:20, :] = 1.0
    t[:, 17:20] = 1.0
    resp = cv2.matchTemplate(resid.astype(np.float32), t,
                             cv2.TM_CCOEFF_NORMED)
    pad = 18
    crosses = []
    r = resp.copy()
    for _ in range(40):
        _, mx, _, loc = cv2.minMaxLoc(r)
        if mx < 0.30:
            break
        x, y = loc
        crosses.append((2 * (x + pad), 2 * (y + pad), mx))
        cv2.circle(r, loc, 60, 0.0, -1)
    diffs = []
    for (x1, y1, _) in crosses:
        for (x2, y2, _) in crosses:
            if abs(y1 - y2) < 80 and 500 < x2 - x1 < 950:
                diffs.append(x2 - x1)
            if abs(x1 - x2) < 80 and 500 < y2 - y1 < 950:
                diffs.append(y2 - y1)
    if len(diffs) < 4:
        raise RuntimeError("reseau grid not found")
    return float(np.median(diffs)), crosses


def skyline_cost(a: np.ndarray, r0: int, r1: int, c0: int,
                 c1: int) -> np.ndarray:
    """Reward image: positive where brightness steps up from sky (above)
    to terrain (below). Combines a 7 px and a 25 px window."""
    band = a[r0 - 30:r1 + 30, c0:c1].astype(np.float32)
    band = cv2.blur(band, (5, 1))          # light horizontal smoothing
    k7 = np.zeros((15, 1), np.float32)
    k7[:7, 0] = -1 / 7.0
    k7[8:, 0] = 1 / 7.0
    g7 = cv2.filter2D(band, -1, k7)
    k25 = np.zeros((51, 1), np.float32)
    k25[:25, 0] = -1 / 25.0
    k25[26:, 0] = 1 / 25.0
    g25 = cv2.filter2D(band, -1, k25)
    return (g7 + 0.5 * g25)[30:-30, :]


def track(reward: np.ndarray, masked: np.ndarray,
          max_step: int = 5, step_pen: float = 1.2) -> np.ndarray:
    """DP seam: for each column pick a row, maximizing sum of rewards with
    |row change| <= max_step per column (penalized). Masked columns give
    zero reward (free passage). Returns row index per column."""
    H, W = reward.shape
    r = reward.copy()
    r[:, masked] = 0.0
    score = r[:, 0].copy()
    back = np.zeros((H, W), dtype=np.int16)
    for c in range(1, W):
        best = score.copy()
        arg = np.zeros(H, dtype=np.int16)
        for s in range(1, max_step + 1):
            pen = step_pen * s
            up = np.empty(H)                    # from row-s (above)
            up[:s] = -np.inf
            up[s:] = score[:-s] - pen
            better = up > best
            best[better] = up[better]
            arg[better] = -s
            dn = np.empty(H)                    # from row+s (below)
            dn[-s:] = -np.inf
            dn[:-s] = score[s:] - pen
            better = dn > best
            best[better] = dn[better]
            arg[better] = s
        score = best + r[:, c]
        back[:, c] = arg
    rows = np.empty(W, dtype=np.int64)
    rows[-1] = int(np.argmax(score))
    for c in range(W - 1, 0, -1):
        rows[c - 1] = rows[c] + back[rows[c], c]
    return rows


def extract(frame: str, cfg: dict) -> None:
    a = np.asarray(Image.open(DATA / f"{frame}.jpg").convert("L"),
                   dtype=np.uint8)
    spacing, crosses = detect_reseau(a)
    px_per_mm = spacing / RESEAU_SPACING_MM
    print(f"{frame}: reseau spacing {spacing:.1f} px "
          f"({len(crosses)} crosses) -> {px_per_mm:.2f} px/mm; "
          f"scan width {a.shape[1] / px_per_mm:.1f} mm")

    c0, c1 = cfg["cols"]
    r0, r1 = cfg["band"]
    cols = np.arange(c0, c1)
    masked = np.zeros(cols.size, dtype=bool)
    for (m0, m1) in cfg["mask_cols"]:
        masked |= (cols >= m0) & (cols <= m1)

    reward = skyline_cost(a, r0, r1, c0, c1)
    rows = track(reward, masked) + r0
    conf = reward[rows - r0, np.arange(cols.size)]

    # keep unmasked columns with a clear transition
    good = ~masked & (conf > 6.0)

    cx, cy = a.shape[1] / 2.0, a.shape[0] / 2.0
    dx_mm = (cols - cx) / px_per_mm
    dy_mm = (rows - cy) / px_per_mm
    az_off = np.degrees(np.arctan2(dx_mm, FOCAL_MM))
    elev = np.degrees(np.arctan2(-dy_mm, np.hypot(FOCAL_MM, dx_mm)))

    np.savez_compressed(
        RESULTS / f"skyline_{frame}.npz",
        col=cols[good], row=rows[good],
        az_off=az_off[good], elev=elev[good], conf=conf[good],
        px_per_mm=px_per_mm, focal_mm=FOCAL_MM, cx=cx, cy=cy,
        crosses=np.array([(x, y) for x, y, _ in crosses]))

    fig, ax = plt.subplots(figsize=(11, 11))
    ax.imshow(a, cmap="gray")
    ax.plot(cols[good], rows[good], ".", color="red", ms=0.8)
    ax.plot(cols[~good], rows[~good], ".", color="orange", ms=0.5,
            alpha=0.4)
    for (x, y, _) in crosses:
        ax.plot(x, y, "+", color="cyan", ms=10, mew=0.8)
    ax.set_title(f"{frame}: extracted skyline (red = used, orange = "
                 "masked/low-confidence), cyan = reseau crosses")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(RESULTS / f"skyline_{frame}.png", dpi=140)
    plt.close(fig)
    print(f"  kept {good.sum()} skyline columns "
          f"({100 * good.sum() / cols.size:.0f}% of span)")


def main():
    RESULTS.mkdir(exist_ok=True)
    for frame, cfg in PHOTOS.items():
        extract(frame, cfg)


if __name__ == "__main__":
    main()
