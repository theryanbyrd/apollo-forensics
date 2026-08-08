"""Apollo 16 'jump salute' (John Young, 120:25:42 GET, ALSJ a16salute.mpg,
352x240, 29.97 fps, 15.8 s).

One event gives BOTH claim tests at once:
  - ballistics: during flight the helmet-top traces a parabola -> apparent g;
  - biomechanics: the muscle-driven push-off (deepest crouch -> liftoff)
    duration does not rescale with gravity; under the s=2.46 hypothesis the
    real push-off would be observed/2.46.

Tracking: Young's white suit is the brightest thing against the black sky;
the top edge of the thresholded suit mask is his helmet crown.

Scale: suited John Young (1.78 m + EVA helmet/boots) = 1.88 +/- 0.07 m,
standing extent measured 122 +/- 6 px (frame 310, between the two jumps).
"""
import json
import os

import cv2
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import common as C

FPS = 29.97
N_FRAMES = 466
SCALE = (122.0 / 1.88, 122.0 / 1.88 * np.hypot(6 / 122, 0.07 / 1.88))
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


def main():
    C.extract_frames("a16salute.mpg", "frames_a16")
    tops = helmet_top_trace()
    out = {"scale_px_per_m": round(SCALE[0], 1)}
    fits = {}
    for name, cfg in JUMPS.items():
        a, b = cfg["flight"]
        f = np.arange(a, b + 1, dtype=float)
        y = tops[a:b + 1]
        ok = ~np.isnan(y)
        f, y = f[ok], y[ok]
        coef = fit_parabola(f, y)
        boots = []
        for _ in range(5000):
            fb = f + RNG.normal(0, 0.5, f.shape)
            yb = y + RNG.normal(0, 1.0, y.shape)
            c = fit_parabola(fb, yb)
            sc = RNG.normal(*SCALE)
            boots.append(c[2] * FPS ** 2 / sc)
        boots = np.array(boots)
        g_fit = coef[2] * FPS ** 2 / SCALE[0]
        g_err = boots.std()

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
            "g_err_m_s2": round(float(g_err), 2),
            "hang_time_s": round(float(hang), 2),
            "push_off_s": round(float(push), 2),
            "push_off_under_hoax_s": round(float(push / 2.46), 3),
            "crouch_frame": int(crouch_frame),
            "liftoff_frame": int(lift_frame),
        }

    # weighted mean g of the two jumps
    gs = np.array([[out[j]["g_apparent_m_s2"], out[j]["g_err_m_s2"]]
                   for j in JUMPS])
    wmean = np.sum(gs[:, 0] / gs[:, 1] ** 2) / np.sum(1 / gs[:, 1] ** 2)
    werr = np.sqrt(1 / np.sum(1 / gs[:, 1] ** 2))
    out["combined_g_m_s2"] = [round(float(wmean), 2), round(float(werr), 2)]
    out["note"] = ("Helmet-top parabola includes body-pose change near "
                   "takeoff/landing; flight windows are trimmed to the "
                   "airborne phase. Under the hoax the real push-off would "
                   "be ~0.1 s - beyond human capability in a 90 kg suit.")

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
                      f"$\\pm$ {out[name]['g_err_m_s2']} m/s$^2$, "
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
