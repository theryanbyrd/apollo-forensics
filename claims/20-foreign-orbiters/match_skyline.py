#!/usr/bin/env python
"""Match the skylines extracted from the 1971 Apollo 15 surface
photographs against the synthetic 360-degree horizon rendered from the
2008 JAXA Kaguya/SELENE Terrain Camera DTM.

Camera model (exact, no small-angle approximations): each skyline pixel
defines a 3D ray in the camera frame through the calibrated focal length
(f = 61.1 mm, Zeiss Biogon 5.6/60 of the Apollo 15 Hasselblad EDC) and
the pixel scale measured from the film's own reseau grid (75.2 px per
10 mm). The only unknowns are the camera's orientation: yaw (azimuth of
the optical axis), pitch and roll. For a candidate orientation, every
ray maps to a world (azimuth, elevation); the cost is the RMS difference
between the ray elevations and the DEM horizon elevation at the same
azimuths.

Scoring is RMS in degrees with the angular scale FIXED by the camera
calibration - unlike a plain normalized cross-correlation this cannot
inflate a smooth low ridge into a mountain (Pearson r is gain-invariant
and produced a false secondary peak in an earlier version of this
analysis; the Pearson r at the best fit is still reported).

Search: coarse grid over yaw (0..360 deg, 0.5 deg) x pitch, roll = 0;
then three rounds of local grid refinement over (yaw, pitch, roll). Each
refinement box is RE-CENTRED and re-searched whenever its optimum lands on
a face of the box, so the reported pose is an interior minimum rather than
a value clipped by the search window (an earlier version reported
roll = +1.8 deg for AS15-88-11866, which was exactly the boundary of both
successive roll grids - the true optimum lies further out and fits
better).

Uniqueness is scored by refining the best rival azimuth (>10 deg away on
the 360 deg circle) through exactly the same three-round procedure and
taking the ratio of its RMS to the winner's - a like-for-like comparison,
not a refined winner against a coarse rival.

If the mountains were painted backdrops there is no reason the RMS
minimum should be deep (sub-degree over a ~45 deg panorama), unique, or
located at the azimuth the mission documentation says the camera faced.

Outputs: results/match_<frame>.png (profile overlay + RMS/r vs yaw),
results/overlay_<frame>.png (photo with the DEM horizon drawn in),
results/match_results.json.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
RESULTS = HERE / "results"

# Documented viewing directions (ALSJ captions; azimuths of the peaks
# computed from selenographic coordinates in render_horizon.py):
#   AS15-88-11866: "Jim, the flag ... with Mt. Hadley Delta in the
#     background" -> looking ~south (Hadley Delta summit bears ~171 deg
#     from the LM).
#   AS15-86-11603: Jim at the Rover with "Mt. Hadley, in all its glory,
#     in the background" -> looking ~northeast (Mons Hadley summit bears
#     ~38-45 deg from the LM).
# Hard physical limit on the hand-held / chest-mounted Hasselblad's roll.
# Deliberately far wider than any plausible pose so that it never becomes
# the thing that stops the search; if the optimum ever reaches it, the fit
# is flagged as non-converged rather than silently clipped.
ROLL_LIMIT_DEG = 20.0

DOCUMENTED = {
    "AS15-88-11866": {"expect_az": (150.0, 195.0),
                      "label": "south - Mons Hadley Delta "
                               "(DEM summit bearing 168.6 deg)"},
    "AS15-86-11603": {"expect_az": (25.0, 70.0),
                      "label": "northeast - Mons Hadley "
                               "(DEM summit bearing 41.8 deg)"},
}


def horizon_interp(h_az, h_el):
    az_ext = np.concatenate([h_az - 360.0, h_az, h_az + 360.0])
    el_ext = np.concatenate([h_el, h_el, h_el])

    def f(a):
        return np.interp(np.mod(a, 360.0), az_ext, el_ext)
    return f


def pearson(x, y):
    x = x - x.mean()
    y = y - y.mean()
    d = np.sqrt((x * x).sum() * (y * y).sum())
    return float((x * y).sum() / d) if d > 0 else 0.0


def rays_from_pixels(cols, rows, cx, cy, px_per_mm, f_mm):
    """Unit rays in the camera frame: x right, y up, z forward (boresight)."""
    x = (cols - cx) / px_per_mm
    y = -(rows - cy) / px_per_mm          # image row grows downward
    z = np.full_like(x, f_mm)
    v = np.stack([x, y, z], axis=1)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def cam_to_world(yaw, pitch, roll):
    """Rotation matrix mapping camera frame -> world (E, N, Up).
    yaw: azimuth of boresight (deg clockwise from North);
    pitch: boresight tilt up (+) in deg; roll: clockwise (+) in deg."""
    sy, cy_ = np.sin(np.radians(yaw)), np.cos(np.radians(yaw))
    sp, cp = np.sin(np.radians(pitch)), np.cos(np.radians(pitch))
    sr, cr = np.sin(np.radians(roll)), np.cos(np.radians(roll))
    fwd = np.array([sy * cp, cy_ * cp, sp])          # boresight
    right0 = np.array([cy_, -sy, 0.0])               # level right vector
    up0 = np.cross(right0, fwd)                      # camera-up, no roll
    right = cr * right0 + sr * up0
    up = -sr * right0 + cr * up0
    return np.stack([right, up, fwd], axis=1)        # world = M @ cam


def rms_cost(u, hfun, yaw, pitch, roll):
    M = cam_to_world(yaw, pitch, roll)
    w = u @ M.T
    az = np.degrees(np.arctan2(w[:, 0], w[:, 1]))
    el = np.degrees(np.arcsin(np.clip(w[:, 2], -1, 1)))
    resid = el - hfun(az)
    return float(np.sqrt(np.mean(resid * resid))), az, el


def refine_box(u, hfun, yw, p, r, span, step, span_r, step_r, max_iter=40):
    """Grid-search (yaw, pitch, roll) inside a box centred on the current
    pose.  If the optimum lands on a face of the box the box is re-centred
    on it and searched again, so the value returned is a genuine interior
    minimum of the sampled grid and never an artefact of where the window
    happened to stop.  Returns (yaw, pitch, roll, rms, interior, n_iter).
    """
    bc = np.inf
    for it in range(1, max_iter + 1):
        yws = np.arange(yw - span, yw + span + 1e-9, step)
        pps = np.arange(p - span, p + span + 1e-9, step)
        rrs = np.arange(r - span_r, r + span_r + 1e-9, step_r)
        rrs = rrs[(rrs >= -ROLL_LIMIT_DEG - 1e-9) &
                  (rrs <= ROLL_LIMIT_DEG + 1e-9)]
        if rrs.size == 0:
            rrs = np.array([float(np.clip(r, -ROLL_LIMIT_DEG,
                                          ROLL_LIMIT_DEG))])
        bc, by, bp, br = np.inf, yw, p, r
        for yw_ in yws:
            for p_ in pps:
                for r_ in rrs:
                    c, _, _ = rms_cost(u, hfun, yw_, p_, r_)
                    if c < bc:
                        bc, by, bp, br = c, yw_, p_, r_
        on_face = (by in (yws[0], yws[-1])) or (bp in (pps[0], pps[-1])) or \
                  (rrs.size > 1 and br in (rrs[0], rrs[-1]))
        yw, p, r = float(by), float(bp), float(br)
        if not on_face:
            return yw, p, r, float(bc), True, it
        if abs(abs(r) - ROLL_LIMIT_DEG) < 1e-9:
            # pinned by the physical roll limit: cannot expand further
            return yw, p, r, float(bc), False, it
    return yw, p, r, float(bc), False, max_iter


def fit(frame: str, hfun):
    d = np.load(RESULTS / f"skyline_{frame}.npz")
    u = rays_from_pixels(d["col"].astype(float), d["row"].astype(float),
                        float(d["cx"]), float(d["cy"]),
                        float(d["px_per_mm"]), float(d["focal_mm"]))
    n = u.shape[0]

    # ---- coarse: yaw x pitch, roll = 0, subsampled points -------------
    us = u[::4]
    yaw_grid = np.arange(0.0, 360.0, 0.5)
    pitch_grid = np.arange(-12.0, 12.01, 1.0)
    rms_of_yaw = np.full(yaw_grid.size, np.inf)
    for i, yw in enumerate(yaw_grid):
        for p in pitch_grid:
            c, _, _ = rms_cost(us, hfun, yw, p, 0.0)
            if c < rms_of_yaw[i]:
                rms_of_yaw[i] = c
    k = int(np.argmin(rms_of_yaw))
    best = (yaw_grid[k], 0.0, 0.0)

    # ---- refine: three rounds of shrinking grid search, all points ----
    # Each round re-centres its box until the optimum is interior, so a
    # boundary hit can never be mistaken for a converged parameter.
    def refine_from(yaw0):
        yw_, r_ = yaw0, 0.0
        p_ = min(pitch_grid,
                 key=lambda pp: rms_cost(us, hfun, yw_, pp, 0.0)[0])
        ok_all, nits = True, []
        # (span_yaw_pitch, step_yaw_pitch, span_roll, step_roll)
        for (span, step, span_r, step_r) in [(1.5, 0.1, 4.0, 0.2),
                                             (0.3, 0.02, 0.5, 0.05),
                                             (0.06, 0.005, 0.1, 0.01)]:
            yw_, p_, r_, bc_, ok, nit = refine_box(u, hfun, yw_, p_, r_,
                                                   span, step, span_r, step_r)
            ok_all = ok_all and ok
            nits.append(nit - 1)
        return yw_, p_, r_, bc_, ok_all, nits

    yw, p, r, bc, interior, recentres = refine_from(best[0])
    rms, az, el = rms_cost(u, hfun, yw, p, r)
    az = (az - (yw - 180.0)) % 360.0 + yw - 180.0   # unwrap around boresight
    pred = hfun(az)
    rcoef = pearson(el, pred)

    # uniqueness: best rival elsewhere on the circle (> 10 deg away in yaw).
    # The rival is put through the IDENTICAL three-round refinement, so the
    # contrast ratio compares like with like; scoring a fully refined winner
    # against a coarse roll = 0 rival would flatter the winner.
    away = np.abs((yaw_grid - yw + 180) % 360 - 180) > 10.0
    second_coarse = float(rms_of_yaw[away].min())
    yaw2 = float(yaw_grid[away][int(np.argmin(rms_of_yaw[away]))])
    yw2, p2, r2, second, _, _ = refine_from(yaw2)
    _, az2, el2 = rms_cost(u, hfun, yw2, p2, r2)
    az2 = (az2 - (yw2 - 180.0)) % 360.0 + yw2 - 180.0
    rcoef2 = pearson(el2, hfun(az2))
    e0, e1 = DOCUMENTED[frame]["expect_az"]
    out = {
        "yaw_deg": float(yw), "pitch_deg": float(p), "roll_deg": float(r),
        "rms_deg": rms, "pearson_r": rcoef,
        "second_best_rms_deg": second,
        "second_best_yaw_deg": float(yw2),
        "second_best_pearson_r": rcoef2,
        "second_best_rms_deg_coarse_grid": second_coarse,
        "rms_contrast": second / rms,
        "n_columns": int(n),
        "pose_is_interior_minimum": bool(interior),
        "refinement_recentres_per_round": recentres,
        "az_span_deg": [float(az.min()), float(az.max())],
        "documented": DOCUMENTED[frame]["label"],
        "expected_az_range": [e0, e1],
        "azimuth_agrees": bool(e0 <= yw <= e1),
    }
    return out, (d, u, az, el, pred, yaw_grid, rms_of_yaw)


def plots(frame, res, aux, hfun, h_az, h_el):
    d, u, az, el, pred, yaw_grid, rms_of_yaw = aux
    yw, p, r = res["yaw_deg"], res["pitch_deg"], res["roll_deg"]

    # --- profile overlay + RMS vs yaw ---------------------------------
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 8),
                                   height_ratios=[2, 1])
    order = np.argsort(az)
    a_lo, a_hi = az.min() - 15, az.max() + 15
    h_dense = np.arange(a_lo, a_hi, 0.05)
    ax1.plot(h_dense, hfun(h_dense), color="0.55", lw=1.2,
             label="synthetic horizon, JAXA Kaguya TC DTM (2008)")
    ax1.plot(az[order], el[order], ".", color="crimson", ms=2,
             label=f"{frame} skyline (1971), camera pose fitted")
    ax1.set_xlim(a_lo, a_hi)
    win = hfun(h_dense)
    ax1.set_ylim(min(win.min(), el.min()) - 1, max(win.max(), el.max()) + 1)
    ax1.set_xlabel("azimuth (deg, 0 = North, 90 = East)")
    ax1.set_ylabel("elevation angle (deg)")
    ax1.legend(loc="upper right")
    ax1.set_title(
        f"{frame} vs Kaguya DEM horizon - yaw {yw:.2f} deg, "
        f"pitch {p:+.2f}, roll {r:+.2f}; RMS {res['rms_deg']:.3f} deg, "
        f"r = {res['pearson_r']:.4f}")
    ax2.plot(yaw_grid, rms_of_yaw, color="steelblue", lw=0.9)
    ax2.axvline(yw, color="crimson", lw=1, ls="--",
                label=f"best fit {yw:.1f} deg")
    e0, e1 = res["expected_az_range"]
    ax2.axvspan(e0, e1, color="green", alpha=0.15,
                label="documented viewing direction")
    ax2.set_yscale("log")
    ax2.set_xlim(0, 360)
    ax2.set_xlabel("candidate boresight azimuth (deg)")
    ax2.set_ylabel("best RMS (deg, log)")
    ax2.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(RESULTS / f"match_{frame}.png", dpi=150)
    plt.close(fig)

    # --- photo overlay -------------------------------------------------
    px_per_mm = float(d["px_per_mm"])
    f_mm = float(d["focal_mm"])
    cx, cy = float(d["cx"]), float(d["cy"])
    img = np.asarray(Image.open(DATA / f"{frame}.jpg").convert("L"))
    M = cam_to_world(yw, p, r)
    a_dense = np.arange(yw - 40, yw + 40, 0.02)
    e_dense = hfun(a_dense)
    wdir = np.stack([np.sin(np.radians(a_dense)) * np.cos(np.radians(e_dense)),
                     np.cos(np.radians(a_dense)) * np.cos(np.radians(e_dense)),
                     np.sin(np.radians(e_dense))], axis=1)
    cam = wdir @ M                       # world -> camera (M orthonormal)
    infront = cam[:, 2] > 0.2
    cam = cam[infront]
    xs = cx + (cam[:, 0] / cam[:, 2]) * f_mm * px_per_mm
    ys = cy - (cam[:, 1] / cam[:, 2]) * f_mm * px_per_mm
    keep = (xs > -200) & (xs < img.shape[1] + 200) & \
           (ys > -200) & (ys < img.shape[0] + 200)
    fig, ax = plt.subplots(figsize=(11, 11))
    ax.imshow(img, cmap="gray")
    ax.plot(xs[keep], ys[keep], "--", color="lime", lw=1.6,
            label="horizon predicted from JAXA Kaguya DEM (2008)")
    ax.legend(loc="lower right", fontsize=11)
    ax.set_title(f"{frame} (1971) with the skyline predicted from the "
                 f"Kaguya Terrain Camera DEM (2008)\nboresight azimuth "
                 f"{yw:.1f} deg, RMS {res['rms_deg']:.3f} deg, "
                 f"r = {res['pearson_r']:.3f}")
    ax.set_xlim(0, img.shape[1])
    ax.set_ylim(img.shape[0], 0)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(RESULTS / f"overlay_{frame}.png", dpi=140)
    plt.close(fig)


def main():
    h = np.load(RESULTS / "horizon.npz")
    hfun = horizon_interp(h["az"], h["elev"])
    results = {}
    for frame in DOCUMENTED:
        res, aux = fit(frame, hfun)
        plots(frame, res, aux, hfun, h["az"], h["elev"])
        results[frame] = res
        print(f"{frame}: yaw {res['yaw_deg']:.2f} deg, pitch "
              f"{res['pitch_deg']:+.2f}, roll {res['roll_deg']:+.2f} | "
              f"RMS {res['rms_deg']:.3f} deg, r = {res['pearson_r']:.4f} | "
              f"2nd-best RMS {res['second_best_rms_deg']:.3f} "
              f"(contrast x{res['rms_contrast']:.1f}) | documented "
              f"{res['documented']} -> "
              f"{'AGREES' if res['azimuth_agrees'] else 'DISAGREES'} | "
              f"interior minimum: {res['pose_is_interior_minimum']} "
              f"(re-centres {res['refinement_recentres_per_round']})")
    with open(RESULTS / "match_results.json", "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
