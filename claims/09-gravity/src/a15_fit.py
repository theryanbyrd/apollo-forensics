"""Fit y(t) = y0 + v0*(t-t0) + 0.5*a*(t-t0)^2 to the Apollo 15 feather track,
convert to metric acceleration, and derive the claim-test quantities.

Scale calibration: David Scott suited (A7LB EVA) height. Scott is 6'0"
(1.83 m); helmet + EVA boots put the suited stack at 1.92 +/- 0.06 m. His
image extent (helmet crown y=48+/-3 to boot sole y=176+/-4, measured on the
16-frame average of 1145-1160) is 128 +/- 5 px.
"""
import json
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import common as C
import a15_tracks

FPS = 30.0
RNG = np.random.default_rng(42)

# scale calibration
SCOTT_PX = (128.0, 5.0)     # px, +/-
SCOTT_M = (1.92, 0.06)      # m, +/-

# landing frames (onset of static ground signatures, +/- 1.5 frames)
HAMMER_LAND = (1195.5, 1.5)
FEATHER_LAND = (1201.5, 1.5)
GROUND_DY_PX = 20.0         # feather ground line ~20 px below hammer mound
SPEECH_END_FRAME = 1155     # end of "...at the same time." in clip audio


def fit_quadratic(t, y):
    """LSQ quadratic; returns (y0, v0[px/fr], a[px/fr^2]) about t[0]."""
    tt = np.asarray(t) - t[0]
    A = np.vstack([np.ones_like(tt), tt, 0.5 * tt ** 2]).T
    coef, *_ = np.linalg.lstsq(A, np.asarray(y), rcond=None)
    return coef


def main():
    fsteps, hsteps = a15_tracks.main()
    t = np.array([f for f, _, _ in fsteps])
    y = np.array([v for _, v, _ in fsteps])

    coef = fit_quadratic(t, y)
    # bootstrap: pixel noise 1.0 px on step y, timing noise 0.6 frames
    # (field-sequential 10 Hz position updates), scale errors propagated
    boots = []
    for _ in range(20000):
        tb = t + RNG.normal(0, 0.6, size=t.shape)
        yb = y + RNG.normal(0, 1.0, size=y.shape)
        c = fit_quadratic(tb, yb)
        px = RNG.normal(*SCOTT_PX)
        m = RNG.normal(*SCOTT_M)
        scale = px / m                       # px per metre
        a_px_s2 = c[2] * FPS ** 2
        boots.append([c[1], c[2], a_px_s2 / scale])
    boots = np.array(boots)
    a_pxf2 = coef[2]
    a_px_s2 = a_pxf2 * FPS ** 2
    scale = SCOTT_PX[0] / SCOTT_M[0]
    g_fit = a_px_s2 / scale
    g_err = boots[:, 2].std()

    # velocity at the last step and at landing, in m/s
    v_last_pxf = coef[1] + coef[2] * (t[-1] - t[0])
    v_last = v_last_pxf * FPS / scale
    v_land_pxf = coef[1] + coef[2] * (FEATHER_LAND[0] - t[0])
    v_land = v_land_pxf * FPS / scale
    v_land_err = np.std((boots[:, 0] + boots[:, 1] *
                         (FEATHER_LAND[0] - t[0])) * FPS) / scale

    # how strongly is real-time Earth gravity excluded?
    sigma_earth = (9.81 - g_fit) / g_err

    # fall height check (image drop hand->ground ~ 87 px)
    drop_h = 87.0 / scale

    # playback factor that would be required if this were Earth footage
    # (percentile CI over positive-acceleration bootstrap samples)
    pos = boots[boots[:, 2] > 0.1, 2]
    s_req = float(np.sqrt(9.81 / g_fit))
    s_lo, s_hi = np.percentile(np.sqrt(9.81 / pos), [16, 84])

    # hammer/feather landing separation, elevation-corrected
    dt_land = (FEATHER_LAND[0] - HAMMER_LAND[0]) / FPS
    dt_land_err = np.hypot(HAMMER_LAND[1], FEATHER_LAND[1]) / FPS
    # time for the feather to cover the extra 20 px of ground drop
    dt_elev = GROUND_DY_PX / (v_land_pxf * FPS)
    dt_resid = dt_land - dt_elev

    out = {
        "scale_px_per_m": round(scale, 1),
        "feather_fit": {
            "a_px_per_s2": round(float(a_px_s2), 1),
            "g_apparent_m_s2": round(float(g_fit), 2),
            "g_err_m_s2": round(float(g_err), 2),
            "v0_px_per_frame_at_1184.5": round(float(coef[1]), 2),
            "v_at_landing_m_s": round(float(v_land), 2),
            "v_at_landing_err_m_s": round(float(v_land_err), 2),
            "v_at_last_step_m_s": round(float(v_last), 2),
            "earth_realtime_excluded_sigma": round(float(sigma_earth), 1),
            "speech_end_frame": SPEECH_END_FRAME,
            "drop_height_m_from_87px": round(float(drop_h), 2),
        },
        "s_required_if_earth": {"value": round(s_req, 2),
                                "ci68": [round(float(s_lo), 2),
                                         round(float(s_hi), 2)]},
        "landing_separation": {
            "observed_s": round(float(dt_land), 2),
            "err_s": round(float(dt_land_err), 2),
            "elevation_explained_s": round(float(dt_elev), 2),
            "residual_s": round(float(dt_resid), 2),
        },
        "hammer_steps": [[round(f, 1), round(v, 1)] for f, v, _ in hsteps],
        "hammer_landing_frame": HAMMER_LAND[0],
    }
    with open(os.path.join(C.RESULTS, "a15_fit.json"), "w") as fh:
        json.dump(out, fh, indent=2)
    print(json.dumps(out, indent=2))

    # ------------------------- figure -------------------------
    fig, ax = plt.subplots(2, 1, figsize=(9, 8), sharex=True,
                           gridspec_kw={"height_ratios": [3, 1]})
    tt = np.linspace(t[0] - 6, FEATHER_LAND[0] + 2, 300)
    yy = coef[0] + coef[1] * (tt - t[0]) + 0.5 * coef[2] * (tt - t[0]) ** 2
    ts = (tt - SPEECH_END_FRAME) / FPS
    ax[0].plot(ts, yy, "-", color="tab:blue", lw=1.5,
               label=f"free-fall fit: a = {g_fit:.2f} $\\pm$ {g_err:.2f} m/s$^2$")
    ax[0].errorbar((t - SPEECH_END_FRAME) / FPS, y, yerr=1.0, xerr=0.6 / FPS,
                   fmt="o", color="tab:orange", capsize=3, ms=6,
                   label="feather (field-sequential position steps)")
    hs_t = np.array([f for f, _, _ in hsteps])
    hs_y = np.array([v for _, v, _ in hsteps])
    ax[0].plot((hs_t - SPEECH_END_FRAME) / FPS, hs_y, "s", ms=6, mfc="none",
               color="tab:red", label="hammer (partial track)")
    ax[0].axhline(195, color="gray", ls=":", lw=1)
    ax[0].text(0.02, 196.5, "feather ground line", fontsize=8, color="gray")
    ax[0].axhline(175, color="brown", ls=":", lw=1)
    ax[0].text(0.02, 176.5, "hammer landing mound", fontsize=8, color="brown")
    ax[0].axvline(0, color="green", ls="--", lw=1)
    ax[0].text(0.01, 120, "audio: end of \"...hit the ground\n"
                          "at the same time.\"", fontsize=8, color="green")
    ax[0].invert_yaxis()
    ax[0].set_ylabel("image y (px, down = falling)")
    ax[0].legend(loc="upper right", fontsize=9)
    ax[0].set_title("Apollo 15 hammer-feather drop: fall tracks "
                    "(ALSJ a15v_1672206.mpg, 29.97 fps)")
    resid = y - (coef[0] + coef[1] * (t - t[0]) + 0.5 * coef[2] * (t - t[0]) ** 2)
    ax[1].axhline(0, color="k", lw=0.8)
    ax[1].stem((t - SPEECH_END_FRAME) / FPS, resid)
    ax[1].set_ylim(-3, 3)
    ax[1].set_ylabel("fit residual (px)")
    ax[1].set_xlabel("time since end of Scott's sentence (s)")
    plt.tight_layout()
    plt.savefig(os.path.join(C.RESULTS, "a15_fit.png"), dpi=110)
    return out


if __name__ == "__main__":
    main()
