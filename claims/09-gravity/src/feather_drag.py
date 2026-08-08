"""Falcon-feather drag simulation: what SHOULD the feather have done if the
footage were Earth footage played at 1/2.46 speed?

Model: quadratic aerodynamic drag, dv/dt = g - (g/vt^2) * v^2, which gives a
terminal velocity vt. Literature terminal velocities for large bird feathers
falling broadside are ~0.8-1.5 m/s (a falcon primary feather is ~1-2 g with
~50-100 cm^2 of area).

Scenarios simulated for a 1.30 m drop (the measured release height):
  1. Moon vacuum, g=1.62               (the genuine-footage hypothesis)
  2. Earth vacuum, g=9.81              (what a vacuum-chamber fake would need)
  3. Earth air, feather vt=0.8/1.1/1.5 (what an open-air Earth fake gives)

For each we report the real fall time, the fall time AS SEEN in footage
slowed by s=2.46, and the impact speed as seen in the slowed footage.
"""
import json
import os

import numpy as np
from scipy.integrate import solve_ivp
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import common as C

H = 1.30          # m, measured drop height (87 px / 66.7 px per m)
S = 2.46          # hoax slow-down factor sqrt(9.81/1.62)
OBS_FALL = (0.68, 1.55)   # s, observed release->feather-landing bracket
OBS_VLAND = (2.35, 0.48)  # m/s, observed apparent feather landing speed


def fall(g, vt=None):
    """Integrate a drop from rest through height H. Returns (t, y, v) arrays
    and the fall time."""
    def rhs(t, s):
        y, v = s
        a = g if vt is None else g * (1 - (v / vt) ** 2)
        return [v, a]
    def hit(t, s):
        return H - s[0]
    hit.terminal = True
    hit.direction = -1
    sol = solve_ivp(rhs, [0, 30], [0, 0], events=hit, max_step=0.001)
    t_fall = sol.t_events[0][0]
    return sol.t, sol.y[0], sol.y[1], t_fall


def main():
    os.makedirs(C.RESULTS, exist_ok=True)
    scen = {}
    curves = {}
    for name, g, vt in [
        ("moon_vacuum", 1.62, None),
        ("earth_vacuum", 9.81, None),
        ("earth_air_vt0.8", 9.81, 0.8),
        ("earth_air_vt1.1", 9.81, 1.1),
        ("earth_air_vt1.5", 9.81, 1.5),
    ]:
        t, y, v, tf = fall(g, vt)
        v_land = v[-1]
        scen[name] = {
            "real_fall_time_s": round(float(tf), 2),
            "as_seen_at_2.46x_slowdown_s": round(float(tf * S), 2),
            "real_impact_speed_m_s": round(float(v_land), 2),
            "apparent_impact_speed_in_slowed_footage_m_s":
                round(float(v_land / S), 2),
        }
        curves[name] = (t, y)

    out = {
        "drop_height_m": H,
        "slowdown_factor": S,
        "observed_fall_time_bracket_s": OBS_FALL,
        "observed_apparent_impact_speed_m_s": OBS_VLAND,
        "scenarios": scen,
        "verdict_notes": [
            "A feather in Earth air is terminal-velocity limited: its "
            "apparent impact speed in 2.46x-slowed footage could not exceed "
            f"{round(1.5/S,2)} m/s (vt=1.5), yet the tracked feather hits at "
            f"{OBS_VLAND[0]} +/- {OBS_VLAND[1]} m/s while still accelerating.",
            "In 2.46x-slowed Earth-air footage the feather would take "
            f"{scen['earth_air_vt1.1']['as_seen_at_2.46x_slowdown_s']} s of "
            "screen time to fall and would lag the hammer by ~2.5 s of screen "
            "time; observed hammer-feather landing gap is 0.20 +/- 0.07 s "
            "(0.07 s after terrain-elevation correction).",
        ],
    }
    with open(os.path.join(C.RESULTS, "feather_drag.json"), "w") as fh:
        json.dump(out, fh, indent=2)
    print(json.dumps(out, indent=2))

    # figure: screen-time y(t) under each hypothesis vs observation
    fig, ax = plt.subplots(figsize=(9, 6))
    styles = {
        "moon_vacuum": ("tab:blue", "-",
                        "Moon vacuum g=1.62 (real time) [wide band]"),
        "earth_vacuum": ("tab:red", "--",
                         "Earth vacuum g=9.81, played at 1/2.46x "
                         "(identical curve - the degeneracy)"),
        "earth_air_vt0.8": ("tab:orange", "--",
                            "Earth air feather vt=0.8, played at 1/2.46x"),
        "earth_air_vt1.1": ("tab:orange", "-",
                            "Earth air feather vt=1.1, played at 1/2.46x"),
        "earth_air_vt1.5": ("tab:orange", ":",
                            "Earth air feather vt=1.5, played at 1/2.46x"),
    }
    # Landing-anchored comparison (independent of the exact release instant):
    # height above the landing point vs screen time remaining before landing.
    for name, (t, y) in curves.items():
        col, ls, lab = styles[name]
        tt = t if name == "moon_vacuum" else t * S
        t_land = tt[-1]
        lw, alpha = (5, 0.35) if name == "moon_vacuum" else (1.6, 1.0)
        ax.plot(t_land - tt, H - y, color=col, ls=ls, lw=lw, alpha=alpha,
                label=lab)
    # observed feather steps, anchored on the measured landing frame 1201.5
    import a15_tracks
    fsteps, _ = a15_tracks.main()
    ty = np.array([[(1201.5 - f) / 30.0, (199.0 - y) / 66.7]
                   for f, y, _ in fsteps])
    ax.errorbar(ty[:, 0], ty[:, 1], yerr=0.03, xerr=0.05 / 3, fmt="o",
                color="k", ms=6, zorder=5,
                label="observed feather track (screen time)")
    ax.set_xlim(1.6, 0)
    ax.set_ylim(0, 1.35)
    ax.set_xlabel("screen time remaining before landing (s)")
    ax.set_ylabel("height above landing point (m)")
    ax.set_title("Feather approach to the ground vs hypotheses\n"
                 "(landing-anchored; slope near 0 = apparent speed)")
    ax.legend(fontsize=9, loc="upper left")
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(C.RESULTS, "feather_drag_sim.png"), dpi=110)
    return out


if __name__ == "__main__":
    main()
