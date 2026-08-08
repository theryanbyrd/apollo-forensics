"""Reseau-cross detection for Apollo Hasselblad scans.

The lunar-surface Hasselblad EDC exposed every frame through a reseau
plate: a 5x5 grid of crosses etched at exactly 10 mm spacing (the center
cross is double-length). Locating the crosses in a scan gives the
px-per-mm scale and the principal point (center cross), which turns
pixel coordinates into calibrated camera rays via the known EDC focal
length (61.1 mm).

Method: normalized cross-correlation of a synthetic dark-plus template
around seed positions on an estimated grid; peaks above threshold are
kept; an affine grid (center + two step vectors) is least-squares fit to
the detections.
"""
import numpy as np
from scipy.signal import fftconvolve


def make_template(arm=28, thick=2):
    """Dark plus-sign on neutral background, zero-mean."""
    size = 2 * arm + 1
    t = np.zeros((size, size))
    c = arm
    t[c - thick:c + thick + 1, :] = -1.0
    t[:, c - thick:c + thick + 1] = -1.0
    t -= t.mean()
    return t


def ncc_peak(img, cx, cy, template, search=110):
    """Return (x, y, score) of best normalized correlation near (cx, cy)."""
    h, w = img.shape
    r = search + template.shape[0] // 2
    x0, x1 = int(max(0, cx - r)), int(min(w, cx + r))
    y0, y1 = int(max(0, cy - r)), int(min(h, cy + r))
    if x1 - x0 < template.shape[1] + 4 or y1 - y0 < template.shape[0] + 4:
        return None
    patch = img[y0:y1, x0:x1].astype(np.float64)
    patch = patch - patch.mean()
    corr = fftconvolve(patch, template[::-1, ::-1], mode="same")
    # normalize by local energy
    local = fftconvolve(patch ** 2, np.ones_like(template), mode="same")
    denom = np.sqrt(np.maximum(local, 1e-9)) * np.sqrt((template ** 2).sum())
    ncc = corr / denom
    iy, ix = np.unravel_index(np.argmax(ncc), ncc.shape)
    # subpixel: centroid of 5x5 neighborhood of the peak
    yy0, yy1 = max(0, iy - 2), min(ncc.shape[0], iy + 3)
    xx0, xx1 = max(0, ix - 2), min(ncc.shape[1], ix + 3)
    win = ncc[yy0:yy1, xx0:xx1]
    win = np.maximum(win - win.min(), 0)
    ys, xs = np.mgrid[yy0:yy1, xx0:xx1]
    if win.sum() > 0:
        py = (ys * win).sum() / win.sum()
        px = (xs * win).sum() / win.sum()
    else:
        py, px = iy, ix
    return (x0 + px, y0 + py, float(ncc[iy, ix]))


def find_grid(img, center_guess, spacing_guess, threshold=0.55, drift_frac=0.18):
    """Detect reseau crosses near a 5x5 grid; fit affine grid model.

    Returns dict with detections [(i,j,x,y,score)], fitted center (x0,y0),
    step vectors, and px-per-10mm scale.
    """
    template = make_template()
    det = []
    for j in range(-2, 3):
        for i in range(-2, 3):
            cx = center_guess[0] + i * spacing_guess
            cy = center_guess[1] + j * spacing_guess
            res = ncc_peak(img, cx, cy, template)
            if res and res[2] >= threshold:
                # reject if drifted onto another node
                if abs(res[0] - cx) < spacing_guess * drift_frac and \
                   abs(res[1] - cy) < spacing_guess * drift_frac:
                    det.append((i, j, res[0], res[1], res[2]))
    if len(det) < 6:
        raise RuntimeError(f"only {len(det)} reseau crosses found")
    # LS fit: p = c + i*u + j*v
    A, bx, by = [], [], []
    for i, j, x, y, s in det:
        A.append([1, 0, i, 0, j, 0])
        A.append([0, 1, 0, i, 0, j])
        bx.append(x)
        by.append(y)
    A = np.array(A)
    b = np.empty(2 * len(det))
    b[0::2] = bx
    b[1::2] = by
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = sol[0:2]
    u = sol[2:4]
    v = sol[4:6]
    pred = np.array([[c[0] + i * u[0] + j * v[0], c[1] + i * u[1] + j * v[1]]
                     for i, j, x, y, s in det])
    meas = np.array([[x, y] for i, j, x, y, s in det])
    rms = float(np.sqrt(((pred - meas) ** 2).sum(axis=1).mean()))
    return {
        "detections": det,
        "center": c.tolist(),          # principal point estimate (px)
        "step_x": u.tolist(),          # image vector for +10 mm in x
        "step_y": v.tolist(),
        "px_per_10mm": float(0.5 * (np.hypot(*u) + np.hypot(*v))),
        "rms_px": rms,
        "n": len(det),
    }
