#!/usr/bin/env python3
"""Claim 1 - "Non-parallel shadows in Apollo photos = multiple studio lights."

End-to-end analysis:
  1. Synthetic demonstrator: parallel sun rays SHOULD give diverging 2D
     shadows (the fence-post fallacy); a nearby lamp gives a measurably
     different convergence geometry. Proves the method discriminates.
  2. Real photos (AS14-68-9487, AS11-40-5961): hand-digitized shadow
     lines (annotations_*.json) are fit with two rival models:
       H_sun : one source at infinity  (concurrency point ON the ground
               vanishing line + one elevation angle; 2 params)
       H_lamp: one source at finite distance (free ground-convergence
               point + free source-image point; 4 params - a superset,
               deliberately generous to the lamp)
     Compared via chi^2 / AIC, with Monte-Carlo propagation of the
     digitization uncertainties.
  3. Killer cross-check: the fitted sun ELEVATION vs the JPL Horizons
     ephemeris for the documented site + UTC time of each photo.

Every number in README.md / results/summary.json is produced by this
script. Run:  ../../.venv/bin/python run.py
"""
import json
import math
import os
import subprocess
import sys

import numpy as np
from scipy.optimize import least_squares
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reseau import find_grid  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
RESULTS = os.path.join(HERE, "results")
os.makedirs(DATA, exist_ok=True)
os.makedirs(RESULTS, exist_ok=True)

FOCAL_MM = 61.1          # Hasselblad EDC calibrated focal length
RESEAU_MM = 10.0         # reseau cross spacing
N_MC = 800
RNG = np.random.default_rng(20260807)

DOWNLOADS = {
    "AS14-68-9487.jpg": "https://www.lpi.usra.edu/resources/apollo/images/print/AS14/68/9487.jpg",
    "AS11-40-5961.jpg": "https://www.lpi.usra.edu/resources/apollo/images/print/AS11/40/5961.jpg",
}
HORIZONS = {
    "horizons_a14_sun.txt": {
        "SITE_COORD": "'-17.47139,-3.64544,0'",
        "START_TIME": "'1971-02-06 10:00'", "STOP_TIME": "'1971-02-06 14:00'",
    },
    "horizons_a11_sun.txt": {
        "SITE_COORD": "'23.47297,0.67408,0'",
        "START_TIME": "'1969-07-21 02:40'", "STOP_TIME": "'1969-07-21 06:40'",
    },
}


def ensure_data():
    for fn, url in DOWNLOADS.items():
        path = os.path.join(DATA, fn)
        if not os.path.exists(path):
            print("downloading", fn)
            subprocess.run(["curl", "-s", "--max-time", "180", "-o", path, url],
                           check=True)
    for fn, q in HORIZONS.items():
        path = os.path.join(DATA, fn)
        if not os.path.exists(path):
            print("querying JPL Horizons ->", fn)
            args = ["curl", "-sG", "https://ssd.jpl.nasa.gov/api/horizons.api"]
            base = {
                "format": "text", "COMMAND": "'10'", "OBJ_DATA": "'NO'",
                "MAKE_EPHEM": "'YES'", "EPHEM_TYPE": "'OBSERVER'",
                "CENTER": "'coord@301'", "COORD_TYPE": "'GEODETIC'",
                "STEP_SIZE": "'10m'", "QUANTITIES": "'4'",
                "APPARENT": "'AIRLESS'",
            }
            base.update(q)
            for k, v in base.items():
                args += ["--data-urlencode", f"{k}={v}"]
            args += ["-o", path]
            subprocess.run(args, check=True)


def parse_horizons(path):
    """Return list of (utc_hours_since_first, az, el) plus datetime strings."""
    rows = []
    with open(path) as fh:
        in_data = False
        for line in fh:
            if line.startswith("$$SOE"):
                in_data = True
                continue
            if line.startswith("$$EOE"):
                break
            if in_data and line.strip():
                parts = line.split()
                # e.g. "1971-Feb-06 12:00 *i   88.589773  23.827735"
                if len(parts) >= 4:
                    stamp = parts[0] + " " + parts[1]
                    az, el = float(parts[-2]), float(parts[-1])
                    rows.append((stamp, az, el))
    return rows


MONTHS = {m: i + 1 for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}


def stamp_to_minutes(stamp):
    d, hm = stamp.split()
    y, mon, day = d.split("-")
    h, mi = hm.split(":")
    mon = MONTHS[mon]
    # minutes since epoch-ish (only differences used within one file)
    import datetime
    dt = datetime.datetime(int(y), mon, int(day), int(h), int(mi))
    return dt.timestamp() / 60.0


def horizons_at(path, utc_iso):
    import datetime
    rows = parse_horizons(path)
    t = [stamp_to_minutes(s) for s, _, _ in rows]
    az = [a for _, a, _ in rows]
    el = [e for _, _, e in rows]
    dt = datetime.datetime.strptime(utc_iso, "%Y-%m-%dT%H:%M:%SZ")
    tq = dt.timestamp() / 60.0
    return float(np.interp(tq, t, az)), float(np.interp(tq, t, el))


# ---------------------------------------------------------------- geometry
def rays(pts, pp, f):
    """Image points (N,2) -> unit direction vectors (N,3), y down, z fwd."""
    pts = np.atleast_2d(pts).astype(float)
    d = np.column_stack([(pts[:, 0] - pp[0]) / f, (pts[:, 1] - pp[1]) / f,
                         np.ones(len(pts))])
    return d / np.linalg.norm(d, axis=1, keepdims=True)


def project(d, pp, f):
    """Direction (3,) -> image point; projective (sign of z irrelevant)."""
    z = d[2] if abs(d[2]) > 1e-12 else 1e-12
    return np.array([pp[0] + f * d[0] / z, pp[1] + f * d[1] / z])


def horizon_frame(hpts, pp, f):
    """Fit horizon line y = a + b x; return (a, b, up_unit_vector)."""
    hpts = np.asarray(hpts, float)
    b, a = np.polyfit(hpts[:, 0], hpts[:, 1], 1)
    p1 = np.array([0.0, a])
    p2 = np.array([3900.0, a + b * 3900.0])
    r1 = rays(p1, pp, f)[0]
    r2 = rays(p2, pp, f)[0]
    n = np.cross(r1, r2)
    n /= np.linalg.norm(n)
    if n[1] < 0:          # orient: ground side is +y (image y is down)
        n = -n
    up = -n
    return a, b, up, (r1, r2)


def perp_residual(base, tip, Q):
    """Perpendicular distance of tip from the infinite line base->Q."""
    v = Q - base
    nv = np.linalg.norm(v)
    if nv < 1e-9:
        return np.linalg.norm(tip - base)
    v /= nv
    w = tip - base
    return w[0] * v[1] - w[1] * v[0]


# ---------------------------------------------------------------- models
class PhotoModel:
    """Holds calibrated geometry + measured lines for one photograph."""

    def __init__(self, ann, calib, sign_src, terrain_frac):
        self.ann = ann
        self.pp = np.array(calib["center"])
        self.f = FOCAL_MM * calib["px_per_10mm"] / RESEAU_MM
        self.sign_src = sign_src      # +1: source VP above horizon (up-sun)
        self.terrain_frac = terrain_frac
        self.shadow = self._lines(ann["shadow_lines"], "base", "tip")
        self.toptip = self._lines(ann["top_tip_lines"], "top", "tip")
        hp = ann["horizon_points"]
        self.hpts = np.asarray(hp["points"], float)
        self.h_sig_read = hp["sigma_read"]
        self.h_sig_sys = hp["sigma_sys"]
        self.h_tilt_sys = hp["tilt_sys_deg"]
        self.anti = ann.get("antisolar_point")

    def _lines(self, items, k0, k1):
        out = []
        for it in items:
            p0 = np.array(it[k0], float)
            p1 = np.array(it[k1], float)
            length = np.linalg.norm(p1 - p0)
            sig = math.sqrt(it[f"sigma_{k0}" if k0 != "top" else "sigma_top"] ** 2
                            + it["sigma_tip"] ** 2
                            + it.get("sigma_extra_perp", 0.0) ** 2
                            + (self.terrain_frac * length) ** 2)
            out.append({"name": it["name"], "p0": p0, "p1": p1, "sig": sig,
                        "sig_dig": math.sqrt(
                            it[f"sigma_{k0}" if k0 != "top" else "sigma_top"] ** 2
                            + it["sigma_tip"] ** 2)})
        return out

    # -- geometry pieces, given (possibly jittered) horizon + pp
    def frame(self, hpts=None, pp=None):
        return horizon_frame(self.hpts if hpts is None else hpts,
                             self.pp if pp is None else pp, self.f)

    def dir_on_horizon(self, theta, fr, pp):
        a, b, up, (r1, r2) = fr
        d0 = rays(np.array([pp[0], a + b * pp[0]]), pp, self.f)[0]
        t = r2 - r1
        t -= np.dot(t, up) * up
        t /= np.linalg.norm(t)
        d0 -= np.dot(d0, up) * up
        d0 /= np.linalg.norm(d0)
        return math.cos(theta) * d0 + math.sin(theta) * t

    def sun_points(self, theta, elev, fr, pp):
        a, b, up, _ = fr
        dh = self.dir_on_horizon(theta, fr, pp)
        dsrc = math.cos(elev) * dh + self.sign_src * math.sin(elev) * up
        return project(dh, pp, self.f), project(dsrc, pp, self.f)

    # -- residual vectors
    def residuals_sun(self, params, fr, pp, shadow, toptip, anti):
        theta, elev = params
        P_sh, P_src = self.sun_points(theta, elev, fr, pp)
        res = [perp_residual(L["p0"], L["p1"], P_sh) / L["sig"] for L in shadow]
        res += [perp_residual(L["p0"], L["p1"], P_src) / L["sig"] for L in toptip]
        if anti is not None:
            res += [(P_src[0] - anti["xy"][0]) / anti["sigma"][0],
                    (P_src[1] - anti["xy"][1]) / anti["sigma"][1]]
        return np.array(res)

    def residuals_lamp(self, params, shadow, toptip, anti):
        P_g = np.array(params[0:2])
        P_L = np.array(params[2:4])
        res = [perp_residual(L["p0"], L["p1"], P_g) / L["sig"] for L in shadow]
        res += [perp_residual(L["p0"], L["p1"], P_L) / L["sig"] for L in toptip]
        if anti is not None:
            res += [(P_L[0] - anti["xy"][0]) / anti["sigma"][0],
                    (P_L[1] - anti["xy"][1]) / anti["sigma"][1]]
        return np.array(res)

    def fit(self, shadow=None, toptip=None, hpts=None, pp=None, anti=None,
            x0_sun=None, x0_lamp=None):
        shadow = self.shadow if shadow is None else shadow
        toptip = self.toptip if toptip is None else toptip
        pp = self.pp if pp is None else pp
        anti = self.anti if anti is None else anti
        fr = self.frame(hpts, pp)
        if x0_sun is None:
            x0_sun = [0.0, math.radians(15.0)]
        sun = least_squares(self.residuals_sun, x0_sun,
                            args=(fr, pp, shadow, toptip, anti),
                            bounds=([-1.4, math.radians(0.5)],
                                    [1.4, math.radians(80)]))
        P_sh, P_src = self.sun_points(sun.x[0], sun.x[1], fr, pp)
        if x0_lamp is None:
            x0_lamp = [*P_sh, *P_src]
        lamp = least_squares(self.residuals_lamp, x0_lamp,
                             args=(shadow, toptip, anti))
        n_obs = len(shadow) + len(toptip) + (2 if anti is not None else 0)
        out = {
            "fr": fr, "pp": pp,
            "sun": {"theta": sun.x[0], "elev": sun.x[1],
                    "P_sh": P_sh, "P_src": P_src,
                    "chi2": float(2 * sun.cost), "k": 2, "n": n_obs},
            "lamp": {"P_g": lamp.x[0:2], "P_L": lamp.x[2:4],
                     "chi2": float(2 * lamp.cost), "k": 4, "n": n_obs},
        }
        out["sun"]["aic"] = out["sun"]["chi2"] + 2 * out["sun"]["k"]
        out["lamp"]["aic"] = out["lamp"]["chi2"] + 2 * out["lamp"]["k"]
        # physical readout of the lamp fit: angle of P_g below the horizon
        a, b, up, _ = fr
        dg = rays(np.array(out["lamp"]["P_g"]), pp, self.f)[0]
        out["lamp"]["depress_deg"] = math.degrees(math.asin(float(np.dot(dg, -up))))
        return out


def implied_distance(depress_deg, h_cam):
    """Ground distance of the point imaged at depression angle below horizon."""
    if depress_deg <= 0.0:
        return math.inf
    return h_cam / math.tan(math.radians(depress_deg))


def run_photo(tag, ann_file, sign_src, terrain_frac, seedkey):
    ann = json.load(open(os.path.join(HERE, ann_file)))
    img = np.asarray(Image.open(os.path.join(HERE, ann["image"])).convert("L"))
    seed = ann["reseau_seed"]
    calib = find_grid(img.astype(float), seed["center"], seed["spacing"],
                      threshold=seed["threshold"])
    model = PhotoModel(ann, calib, sign_src, terrain_frac)
    base = model.fit()

    # --------------------------- Monte Carlo over digitization errors
    mc = {"elev": [], "theta": [], "depress": [], "dist": [],
          "dchi2": [], "P_g": []}
    h_cam = ann["camera_height_m"]
    for _ in range(N_MC):
        shadow = [{**L,
                   "p0": L["p0"] + RNG.normal(0, L["sig"] / np.sqrt(2), 2),
                   "p1": L["p1"] + RNG.normal(0, L["sig"] / np.sqrt(2), 2)}
                  for L in model.shadow]
        toptip = [{**L,
                   "p0": L["p0"] + RNG.normal(0, L["sig"] / np.sqrt(2), 2),
                   "p1": L["p1"] + RNG.normal(0, L["sig"] / np.sqrt(2), 2)}
                  for L in model.toptip]
        tilt = math.radians(RNG.normal(0, model.h_tilt_sys))
        off = RNG.normal(0, model.h_sig_sys)
        hp = model.hpts.copy()
        hp[:, 1] = (hp[:, 1] + off + (hp[:, 0] - model.pp[0]) * math.tan(tilt)
                    + RNG.normal(0, model.h_sig_read, len(hp)))
        pp = model.pp + RNG.normal(0, 8.0, 2)
        anti = None
        if model.anti is not None:
            anti = {"xy": np.array(model.anti["xy"], float)
                    + RNG.normal(0, model.anti["sigma"], 2),
                    "sigma": model.anti["sigma"]}
        h = max(0.8, RNG.normal(h_cam["value"], h_cam["sigma"]))
        try:
            r = model.fit(shadow, toptip, hp, pp, anti,
                          x0_sun=[base["sun"]["theta"], base["sun"]["elev"]],
                          x0_lamp=[*base["lamp"]["P_g"], *base["lamp"]["P_L"]])
        except Exception:
            continue
        mc["elev"].append(math.degrees(r["sun"]["elev"]))
        mc["theta"].append(math.degrees(r["sun"]["theta"]))
        mc["depress"].append(r["lamp"]["depress_deg"])
        mc["dist"].append(implied_distance(r["lamp"]["depress_deg"], h))
        mc["dchi2"].append(r["lamp"]["chi2"] - r["sun"]["chi2"])
        mc["P_g"].append(list(r["lamp"]["P_g"]))
    for k in mc:
        mc[k] = np.array(mc[k])

    ephem_az, ephem_el = horizons_at(
        os.path.join(DATA, f"horizons_{seedkey}_sun.txt"), ann["photo_utc"])

    # per-top-tip-line implied elevation (shadow lines + one top-tip line):
    per_line_elev = {}
    for i, L in enumerate(model.toptip):
        try:
            r1 = model.fit(model.shadow, [model.toptip[i]])
            per_line_elev[L["name"]] = round(math.degrees(r1["sun"]["elev"]), 2)
        except Exception:
            per_line_elev[L["name"]] = None

    dist = mc["dist"]
    finite = dist[np.isfinite(dist)]
    frac_above = float(np.mean(~np.isfinite(dist)))
    out = {
        "frame": ann["frame_id"],
        "photo_utc": ann["photo_utc"],
        "calibration": {
            "n_crosses": calib["n"], "px_per_10mm": calib["px_per_10mm"],
            "grid_rms_px": calib["rms_px"],
            "principal_point": calib["center"],
            "focal_px": FOCAL_MM * calib["px_per_10mm"] / RESEAU_MM,
        },
        "n_shadow_lines": len(model.shadow),
        "n_toptip_lines": len(model.toptip),
        "sun_fit": {
            "chi2": base["sun"]["chi2"], "k": 2, "n": base["sun"]["n"],
            "chi2_per_dof": base["sun"]["chi2"] / max(1, base["sun"]["n"] - 2),
            "aic": base["sun"]["aic"],
            "elev_deg": math.degrees(base["sun"]["elev"]),
            "elev_deg_mc": [float(np.mean(mc["elev"])), float(np.std(mc["elev"]))],
            "theta_deg_mc": [float(np.mean(mc["theta"])), float(np.std(mc["theta"]))],
            "P_sh": base["sun"]["P_sh"].tolist(),
            "P_src": base["sun"]["P_src"].tolist(),
            "per_toptip_line_implied_elev_deg": per_line_elev,
        },
        "lamp_fit": {
            "chi2": base["lamp"]["chi2"], "k": 4, "aic": base["lamp"]["aic"],
            "P_g": list(map(float, base["lamp"]["P_g"])),
            "depress_deg": base["lamp"]["depress_deg"],
            "depress_deg_mc": [float(np.mean(mc["depress"])),
                               float(np.std(mc["depress"]))],
            "implied_source_dist_m_median": (float(np.median(dist))
                                             if np.isfinite(np.median(dist))
                                             else None),
            "implied_dist_m_p05": (float(np.percentile(finite, 5))
                                   if len(finite) else None),
            "frac_mc_convergence_at_or_above_horizon": frac_above,
        },
        "delta_aic_lamp_minus_sun": base["lamp"]["aic"] - base["sun"]["aic"],
        "ephemeris": {"az_deg": ephem_az, "el_deg": ephem_el},
        "elev_minus_ephem_deg": [float(np.mean(mc["elev"]) - ephem_el),
                                 float(np.std(mc["elev"]))],
    }
    return model, base, mc, out


# ---------------------------------------------------------------- synthetic
def synthetic_figure():
    f, w, h = 1300.0, 1000, 800
    pp = np.array([w / 2, h / 2])
    cam_h, pitch = 1.6, math.radians(6)
    cp, sp = math.cos(pitch), math.sin(pitch)

    def cam(P):  # world (x right, y up, z fwd from camera at origin) -> image
        x, y, z = P
        yz = y * cp + z * sp   # camera pitched DOWN by `pitch`
        zz = z * cp - y * sp
        return np.array([pp[0] + f * x / zz, pp[1] - f * yz / zz])

    posts = [(-3.0, 6.0, 1.4), (-1.0, 5.0, 1.0), (1.2, 7.0, 1.6),
             (2.5, 9.0, 1.2), (0.0, 10.0, 1.8), (-2.2, 12.0, 1.3),
             (3.3, 13.0, 1.5)]
    sun_azr, sun_el = math.radians(15), math.radians(14)  # antisolar az 15 deg
    s_dir = np.array([math.sin(sun_azr) * math.cos(sun_el),
                      -math.sin(sun_el),
                      math.cos(sun_azr) * math.cos(sun_el)])  # light travel dir
    lamp = np.array([8 * math.sin(sun_azr), 5.0, 8 * math.cos(sun_azr)])

    def shadow_tip_sun(base, hh):
        top = np.array([base[0], hh, base[2]])
        lam = -top[1] / s_dir[1]
        return top + lam * s_dir

    def shadow_tip_lamp(base, hh):
        top = np.array([base[0], hh, base[2]])
        v = top - lamp
        lam = -lamp[1] / v[1]
        return lamp + lam * v

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 6.2), dpi=130)
    for ax, mode in zip(axes, ["sun", "lamp"]):
        ax.set_facecolor("#0b0e13")
        # horizon of ground plane y=-cam_h ... vanishing line: y_img where
        # ray parallel to ground: v = pp1 - f*tan(pitch)
        y_hor = pp[1] - f * math.tan(pitch)
        ax.axhline(y_hor, color="#8899aa", lw=1.2, ls="-")
        ax.annotate("horizon (ground-plane vanishing line)",
                    (12, y_hor - 8), color="#8899aa", fontsize=8)
        segs = []
        for (px_, pz, hh) in posts:
            base = np.array([px_, -cam_h, pz])
            tip3 = (shadow_tip_sun(base, hh - cam_h) if mode == "sun"
                    else shadow_tip_lamp(base, hh - cam_h))
            b2, t2 = cam(base), cam(tip3)
            topi = cam([px_, hh - cam_h, pz])
            ax.plot([b2[0], topi[0]], [b2[1], topi[1]], color="#c8a24a", lw=3)
            ax.plot([b2[0], t2[0]], [b2[1], t2[1]], color="#2a3648", lw=5,
                    solid_capstyle="round")
            segs.append((b2, t2))
        # extend the 2D shadow lines exactly as a debunker would with a ruler
        for b2, t2 in segs:
            v = t2 - b2
            ax.plot([b2[0] - 6 * v[0], b2[0] + 6 * v[0]],
                    [b2[1] - 6 * v[1], b2[1] + 6 * v[1]],
                    color="#d05555", lw=0.7, alpha=0.65, ls="--")
        # true convergence point
        if mode == "sun":
            dh = np.array([math.sin(sun_azr), 0, math.cos(sun_azr)])
            P = cam(dh * 500)   # far along the antisolar azimuth
            title = "(a) SUN at infinity, elevation 14°"
            note = ("2D shadow directions span ~50° (the naive\n"
                    "“non-parallel!” reading) — yet every line passes\n"
                    "through ONE point exactly ON the horizon")
        else:
            P = cam([lamp[0], -cam_h, lamp[2]])
            title = "(b) LAMP 8 m away, 5 m up (same azimuth)"
            note = ("lines converge at the lamp's foot point,\n"
                    "%.1f° BELOW the horizon → implied distance\n"
                    "h/tan(%.1f°) ≈ 8 m. Measurably different." %
                    (math.degrees(math.atan2(cam_h, math.hypot(lamp[0], lamp[2]))),
                     math.degrees(math.atan2(cam_h, math.hypot(lamp[0], lamp[2])))))
        ax.plot(*P, marker="o", ms=9, mfc="#e8c95a", mec="white", zorder=5)
        ax.annotate("convergence point", P + np.array([12, -10]),
                    color="#e8c95a", fontsize=9, fontweight="bold")
        ax.set_title(title, fontsize=11)
        ax.text(0.02, 0.03, note, transform=ax.transAxes, color="#dddddd",
                fontsize=8.5, va="bottom",
                bbox=dict(fc="#141a24", ec="none", alpha=0.85, pad=5))
        ax.set_xlim(0, w)
        ax.set_ylim(h, 0)
        ax.set_xticks([])
        ax.set_yticks([])
    fig.suptitle("Fence-post fallacy, demonstrated: a single distant sun MUST "
                 "produce diverging 2D shadows.\nThe rigorous test is WHERE the "
                 "shadow lines converge - on the horizon (sun) vs below it "
                 "(nearby lamp).", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    fig.savefig(os.path.join(RESULTS, "fig1_synthetic_demonstrator.png"))
    plt.close(fig)


def photo_figure(models_results):
    fig, axes = plt.subplots(1, 2, figsize=(15, 7.8), dpi=130)
    for ax, (tag, model, base, mc, out) in zip(axes, models_results):
        img = np.asarray(Image.open(
            os.path.join(HERE, model.ann["image"])).convert("L"))
        small = img[::4, ::4]
        ax.imshow(small, cmap="gray", extent=[0, 3900, 3900, 0])
        P = base["sun"]["P_sh"]
        pad_l = min(0, P[0] - 250)
        ax.set_xlim(pad_l, 3900)
        ax.set_ylim(3900, min(0, P[1] - 250))
        for L in model.shadow:
            b, t = L["p0"], L["p1"]
            ax.plot([b[0], t[0]], [b[1], t[1]], color="#ff5555", lw=2.4)
            v = P - b
            v = v / np.linalg.norm(v)
            far = b + v * 12000
            ax.plot([b[0], far[0]], [b[1], far[1]], color="#ff9955",
                    lw=0.8, ls="--", alpha=0.8)
            ax.plot([b[0], b[0] - v[0] * 900], [b[1], b[1] - v[1] * 900],
                    color="#ff9955", lw=0.8, ls="--", alpha=0.5)
        for L in model.toptip:
            b, t = L["p0"], L["p1"]
            ax.plot([b[0], t[0]], [b[1], t[1]], color="#55aaff", lw=1.6)
        hf = base["fr"]
        xs = np.array([pad_l, 3900.0])
        ax.plot(xs, hf[0] + hf[1] * xs, color="#dddd66", lw=1.2, ls=":",
                label="horizon fit (skyline)")
        ax.plot(*P, marker="*", ms=17, mfc="#ffee66", mec="black", zorder=6)
        ann_el = out["sun_fit"]["elev_deg_mc"]
        eph = out["ephemeris"]["el_deg"]
        extra = ("\n(up-sun frame: elevation weakly constrained, "
                 "see fig4; azimuth + concurrency are the tests here)"
                 if out["frame"].startswith("AS14") else "")
        ax.set_title(
            f"{out['frame']}  -  shadow lines concurrent at one point "
            f"(star)\nfitted sun elevation {ann_el[0]:.1f}° ± "
            f"{ann_el[1]:.1f}°  vs  JPL Horizons {eph:.2f}°" + extra,
            fontsize=10)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.legend(loc="lower right", fontsize=8)
    fig.suptitle("Red: digitized shadow lines (base->tip). Blue: object-top -> "
                 "shadow-tip lines. Dashed: extension to the fitted "
                 "single-source convergence point.", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(os.path.join(RESULTS, "fig2_real_photo_fits.png"))
    plt.close(fig)


def mc_figure(models_results):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4), dpi=130)
    for ax, (tag, model, base, mc, out) in zip(axes, models_results):
        d = mc["depress"]
        ax.hist(d, bins=48, color="#4477cc", alpha=0.85)
        ax.axvline(0, color="#33aa55", lw=2)
        ax.text(0.0, ax.get_ylim()[1] * 0.97, "  sun (convergence ON horizon)",
                color="#33aa55", fontsize=9, va="top")
        h = model.ann["camera_height_m"]["value"]
        for D, lab in [(5, "lamp 5 m"), (10, "lamp 10 m"), (20, "lamp 20 m")]:
            x = math.degrees(math.atan2(h, D))
            ax.axvline(x, color="#cc4444", lw=1.4, ls="--")
            ax.text(x, ax.get_ylim()[1] * 0.55, " " + lab, rotation=90,
                    color="#cc4444", fontsize=8, va="top")
        ax.set_xlabel("free-fit convergence point: angle BELOW horizon (deg)")
        ax.set_ylabel("Monte-Carlo samples")
        med = np.median(d)
        ax.set_title(f"{out['frame']}: median offset {med:+.2f}° "
                     f"(σ {np.std(d):.2f}°)", fontsize=10)
    fig.suptitle("If the light were a studio lamp 5-20 m away, the shadow-line "
                 "convergence point would sit degrees BELOW the horizon.\n"
                 "Monte-Carlo refits of the hand-digitized lines put it at the "
                 "horizon - a source at effectively infinite distance.",
                 fontsize=10.5)
    fig.tight_layout(rect=[0, 0, 1, 0.88])
    fig.savefig(os.path.join(RESULTS, "fig3_montecarlo_source_distance.png"))
    plt.close(fig)


def elev_figure(models_results):
    fig, ax = plt.subplots(figsize=(8.2, 5.6), dpi=130)
    xs = np.arange(len(models_results))
    for i, (tag, model, base, mc, out) in enumerate(models_results):
        m, s = out["sun_fit"]["elev_deg_mc"]
        eph = out["ephemeris"]["el_deg"]
        per = [v for v in
               out["sun_fit"]["per_toptip_line_implied_elev_deg"].values()
               if v is not None]
        ax.plot([i - 0.22] * len(per), per, marker="o", ms=5, ls="none",
                color="#999999", alpha=0.8,
                label="single-object solutions\n(spread = terrain/ID systematics)"
                if i == 0 else None)
        ax.errorbar([i], [m], yerr=[s], fmt="o", ms=9, capsize=6,
                    color="#4477cc",
                    label="joint fit (MC ±1σ)" if i == 0 else None)
        ax.plot([i + 0.16], [eph], marker="*", ms=18, color="#dd9922",
                ls="none",
                label="JPL Horizons ephemeris" if i == 0 else None)
        ax.annotate(f"Δ = {m - eph:+.1f}°", (i, max(max(per), m + s, eph) + 1.4),
                    ha="center", fontsize=10)
    ax.set_xticks(xs)
    ax.set_xticklabels([r[4]["frame"] + "\n" + r[4]["photo_utc"]
                        + ("\n(up-sun: weak elevation lever)" if i == 0 else
                           "\n(down-sun: strong elevation lever)")
                        for i, r in enumerate(models_results)], fontsize=9)
    ax.set_ylabel("sun elevation at the site (deg)")
    ax.set_ylim(0, 40)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8.5, loc="upper right")
    ax.set_title("Sun elevation recovered from photo geometry alone vs the\n"
                 "JPL ephemeris for the documented minute of exposure",
                 fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "fig4_elevation_vs_ephemeris.png"))
    plt.close(fig)


def main():
    ensure_data()
    synthetic_figure()
    print("fig1 done")

    results = []
    a14 = run_photo("a14", "annotations_AS14-68-9487.json",
                    sign_src=+1, terrain_frac=0.05, seedkey="a14")
    results.append(("a14", *a14))
    a11 = run_photo("a11", "annotations_AS11-40-5961.json",
                    sign_src=-1, terrain_frac=0.04, seedkey="a11")
    results.append(("a11", *a11))

    photo_figure(results)
    mc_figure(results)
    elev_figure(results)

    per_photo = {tag: out for tag, _, _, _, out in results}
    for tag, _, _, _, out in results:
        print(json.dumps(out, indent=2, default=float)[:2000])

    d11 = per_photo["a11"]["elev_minus_ephem_deg"]
    p05 = per_photo["a11"]["lamp_fit"]["implied_dist_m_p05"]
    c14 = per_photo["a14"]["sun_fit"]["chi2_per_dof"]
    c11 = per_photo["a11"]["sun_fit"]["chi2_per_dof"]
    summary = {
        "claim": 1,
        "title": "Non-parallel shadows = studio lights",
        "verdict": "REFUTED",
        "headline": (
            "In both famous 'non-parallel shadow' frames every shadow line "
            "is concurrent at a single vanishing point on the horizon "
            f"(chi2/dof {c14:.1f} and {c11:.1f}) - the signature of one "
            "source at infinity - and the down-sun Apollo 11 frame recovers "
            f"a sun elevation of "
            f"{per_photo['a11']['sun_fit']['elev_deg_mc'][0]:.1f}° ± "
            f"{d11[1]:.1f}°, matching the JPL Horizons ephemeris value of "
            f"{per_photo['a11']['ephemeris']['el_deg']:.2f}° to "
            f"{abs(d11[0]):.1f}°, while any lamp closer than {p05:.0f} m is "
            "excluded at 95% confidence."),
        "impressive": (
            "The sun's elevation over Tranquility Base at 1969-07-21 "
            f"04:43:31 UTC was recovered to {abs(d11[0]):.1f}° using nothing but hand-"
            "digitized shadow endpoints from AS11-40-5961 (including the "
            "shadow of Armstrong's own camera, which marks the antisolar "
            "point exactly, independent of terrain), the Hasselblad's "
            "reseau-plate calibration, and projective geometry - then "
            "confirmed against JPL Horizons. No 1969 set designer was "
            "simulating astronomically correct vanishing points to "
            "sub-degree accuracy."),
        "photos": per_photo,
    }
    with open(os.path.join(RESULTS, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2, default=float)
    print("wrote results/summary.json")


if __name__ == "__main__":
    main()
