"""Apollo 16 'jump salute' (John Young, 120:25:42 GET, ALSJ a16salute.mpg,
352x240, 29.97 fps, 15.8 s).

One event gives BOTH claim tests at once:
  - ballistics: during flight the helmet-top traces a parabola -> apparent g;
  - biomechanics: the muscle-driven push-off (deepest crouch -> liftoff)
    duration does not rescale with gravity; under the s=2.46 hypothesis the
    real push-off would be observed/2.46.

Tracking: Young's white suit is the brightest thing against the black sky;
the top edge of the thresholded suit mask is his helmet crown.

Scale: imported from claims/10-wire-rigs/a16_scale.py, which is the single
definition of the metric calibration of this clip and is shared with claim 10
(129.0 +/- 5.0 px = 1.80 +/- 0.10 m -> 71.67 px/m, +/-6.8 % systematic).
An earlier version of this file used 122 px / 1.88 m = 64.9 px/m while claim
10 used 128 px / 1.80 m = 71.1 px/m for the *same* measurement of the *same*
standing man in the *same* clip - a 10 % contradiction between two pages of
this repo.  a16_scale.py re-measures the extent from the frames (129.0 +/-
3.5 px over 62 frames) and settles it: 122 px was the crown-to-*ankle*
extent, and 1.88 m additionally ignored the knees-flexed stance the footage
actually shows, so the two errors compounded into ~10 %.

Errors: the scale is 100 % correlated between the two jumps, so it is
carried as a separate systematic and never averaged down (see main()).
"""
import json
import os
import sys

import cv2
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import common as C

sys.path.insert(0, os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "10-wire-rigs")))
import a16_scale  # noqa: E402  (shared with claim 10 - do not redefine)

FPS = 29.97
N_FRAMES = 466
SCALE_PX_PER_M = a16_scale.PX_PER_M
SCALE_RELERR = a16_scale.SCALE_RELERR
RNG = np.random.default_rng(7)

# jump windows (frames), from the helmet-top trace
JUMPS = {
    "jump1": dict(flight=(240, 279), crouch_lo=(220, 240), takeoff_level=60),
    "jump2": dict(flight=(336, 366), crouch_lo=(315, 336), takeoff_level=62),
}


def helmet_top_trace():
    tops = np.full(N_FRAMES + 1, np.nan)
    for i in range(1, N_FRAMES + 1):
        im = cv2.imread(os.path.join(C.DATA, "frames_a16", f"f{i:05d}.png"),
                        cv2.IMREAD_GRAYSCALE)
        roi = im[:, 30:280]
        m = (roi > 175).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        ys, _ = np.where(m > 0)
        if len(ys) > 50:
            tops[i] = ys.min()
    return tops


def fit_parabola(f, y):
    ff = f - f[0]
    A = np.vstack([np.ones_like(ff), ff, 0.5 * ff ** 2]).T
    coef, res, *_ = np.linalg.lstsq(A, y, rcond=None)
    return coef


def measure_scale_crosscheck():
    """Re-run claim 10's standing-height measurement on *our* frame files.

    Claim 09 extracts frames with `ffmpeg -vsync 0` (466 PNGs, 1-based) while
    claim 10 decodes with imageio (468 frames, 0-based); the same wall-clock
    frame is claim-09 index n <-> claim-10 index n+1.  If the two pipelines
    ever stop measuring the same man at the same size, this prints it.
    """
    def get(t):
        im = cv2.imread(os.path.join(C.DATA, "frames_a16", f"f{t:05d}.png"),
                        cv2.IMREAD_GRAYSCALE)
        return im.astype(np.float32)
    m = a16_scale.measure_standing_px(get, a16_scale.STAND_FRAMES_09)
    print(f"[scale] a16salute standing extent re-measured on claim-09 PNG "
          f"frames: {m['mean']:.1f} +- {m['sd']:.1f} px over {m['n']} frames "
          f"(claim 10 measures {a16_scale.STAND_PX} px on its own decode)")
    return m


def main():
    C.extract_frames("a16salute.mpg", "frames_a16")
    tops = helmet_top_trace()
    meas = measure_scale_crosscheck()
    out = {
        "scale": {
            "source": "claims/10-wire-rigs/a16_scale.py (shared with claim 10)",
            "px_per_m": round(SCALE_PX_PER_M, 2),
            "rel_err_systematic": round(float(SCALE_RELERR), 4),
            "standing_px_adopted": a16_scale.STAND_PX,
            "standing_m_adopted": a16_scale.STAND_M,
            "standing_px_remeasured_here": round(meas["mean"], 2),
            "standing_px_remeasured_sd": round(meas["sd"], 2),
            "standing_px_remeasured_n_frames": meas["n"],
        },
        "scale_px_per_m": round(SCALE_PX_PER_M, 2),
    }
    fits = {}
    for name, cfg in JUMPS.items():
        a, b = cfg["flight"]
        f = np.arange(a, b + 1, dtype=float)
        y = tops[a:b + 1]
        ok = ~np.isnan(y)
        f, y = f[ok], y[ok]
        coef = fit_parabola(f, y)
        # Bootstrap the *statistical* error only: pixel noise (1 px) and
        # step-timing noise (0.5 frame).  The scale is held FIXED here - it is
        # one number shared by both jumps and by claim 10, so resampling it
        # per jump and then combining the jumps as if independent would shrink
        # a systematic that cannot shrink.  It is applied once, below.
        boots = []
        for _ in range(5000):
            fb = f + RNG.normal(0, 0.5, f.shape)
            yb = y + RNG.normal(0, 1.0, y.shape)
            c = fit_parabola(fb, yb)
            boots.append(c[2] * FPS ** 2 / SCALE_PX_PER_M)
        boots = np.array(boots)
        g_fit = coef[2] * FPS ** 2 / SCALE_PX_PER_M
        g_err = boots.std()                       # statistical only
        g_sys = abs(g_fit) * SCALE_RELERR         # correlated scale systematic

        # hang time: rise above takeoff level
        lvl = cfg["takeoff_level"]
        below = np.where(tops[a - 10:b + 8] < lvl)[0]
        hang = (below[-1] - below[0] + 1) / FPS if len(below) else np.nan

        # push-off: deepest crouch -> last frame at/below takeoff level y
        c0, c1 = cfg["crouch_lo"]
        crouch_frame = c0 + int(np.nanargmax(tops[c0:c1]))
        lift_frame = a - 10 + below[0]
        push = (lift_frame - crouch_frame) / FPS

        fits[name] = dict(coef=coef, f=f, y=y)
        out[name] = {
            "flight_window": [a, b],
            "g_apparent_m_s2": round(float(g_fit), 2),
            "g_stat_err_m_s2": round(float(g_err), 3),
            "g_scale_sys_err_m_s2": round(float(g_sys), 3),
            "g_total_err_m_s2": round(float(np.hypot(g_err, g_sys)), 3),
            "hang_time_s": round(float(hang), 2),
            "push_off_s": round(float(push), 2),
            "push_off_under_hoax_s": round(float(push / 2.46), 3),
            "crouch_frame": int(crouch_frame),
            "liftoff_frame": int(lift_frame),
        }

    # Combine the two jumps.  ONLY the statistical parts combine in
    # inverse-variance quadrature; the scale systematic is 100 % correlated
    # between them (it is literally the same constant), so it is applied once
    # to the combined value instead of being averaged down.
    gs = np.array([[out[j]["g_apparent_m_s2"], out[j]["g_stat_err_m_s2"]]
                   for j in JUMPS])
    w = 1.0 / gs[:, 1] ** 2
    wmean = float(np.sum(gs[:, 0] * w) / np.sum(w))
    werr_stat = float(np.sqrt(1.0 / np.sum(w)))
    werr_sys = abs(wmean) * SCALE_RELERR
    out["combined_g_m_s2"] = round(wmean, 2)
    out["combined_g_stat_err_m_s2"] = round(werr_stat, 3)
    out["combined_g_scale_sys_err_m_s2"] = round(werr_sys, 3)
    out["combined_g_total_err_m_s2"] = round(float(np.hypot(werr_stat,
                                                            werr_sys)), 3)
    out["note"] = ("Helmet-top parabola includes body-pose change near "
                   "takeoff/landing; flight windows are trimmed to the "
                   "airborne phase. Under the hoax the real push-off would "
                   "be ~0.1 s - beyond human capability in a 90 kg suit. "
                   "The scale systematic is the same constant for both jumps "
                   "(and for claim 10), so it is applied once to the combined "
                   "value rather than combined in quadrature.")

    with open(os.path.join(C.RESULTS, "a16_jump.json"), "w") as fh:
        json.dump(out, fh, indent=2)
    print(json.dumps(out, indent=2))

    # ---------------- figure ----------------
    fig, ax = plt.subplots(figsize=(12, 5))
    tt = np.arange(N_FRAMES + 1) / FPS
    ax.plot(tt, tops, ".", ms=3, color="gray", label="helmet-top trace")
    for name, cfg in JUMPS.items():
        coef = fits[name]["coef"]
        f = fits[name]["f"]
        ff = np.linspace(f[0], f[-1], 100)
        yy = coef[0] + coef[1] * (ff - f[0]) + 0.5 * coef[2] * (ff - f[0]) ** 2
        ax.plot(ff / FPS, yy, "-", lw=2,
                label=f"{name}: g = {out[name]['g_apparent_m_s2']} "
                      f"$\\pm$ {out[name]['g_stat_err_m_s2']:.2f} (stat) "
                      f"$\\pm$ {out[name]['g_scale_sys_err_m_s2']:.2f} "
                      f"(scale) m/s$^2$, "
                      f"push-off {out[name]['push_off_s']} s")
        ax.axvspan(out[name]["crouch_frame"] / FPS,
                   out[name]["liftoff_frame"] / FPS, color="orange", alpha=0.25)
    ax.invert_yaxis()
    ax.set_xlabel("clip time (s)")
    ax.set_ylabel("helmet top, image y (px)")
    ax.set_title("Apollo 16 jump salute (a16salute.mpg): ballistic arcs + "
                 "muscle-driven push-off (shaded)")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(C.RESULTS, "a16_jump.png"), dpi=110)
    return out


if __name__ == "__main__":
    main()
