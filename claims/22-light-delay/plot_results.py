#!/usr/bin/env python
"""Assemble result plots from echo_*.json + turn_taking.json + Horizons CSV.

Produces:
  results/echo_correlation.png      mean z-scored envelope correlation vs lag,
                                    CapCom vs control, per tape
  results/echo_events.png           per-utterance detections: lag vs GET over
                                    the Horizons RTT prediction  (money plot)
  results/turn_taking_hist.png      gap histograms G1 vs G2
"""
import glob
import json
import os

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
DATA = os.path.join(HERE, "data")

# GET anchor (hours) at tape start, from the NASA JSC tape catalog
# (MET-ST..MET-END: 173: 102:12-106:17, 174: 106:17-109:21, 175: 109:21-111:37).
# Tapes 174/175 have durations ~= their GET spans (continuous recording, GET
# good to a couple of minutes); tape 173 contains ~55 min of release pauses, so
# GET = anchor + offset is a lower bound there.  Either way the error moves the
# predicted RTT by < 0.005 s (the curve changes ~0.004 s/h), i.e. negligible.
TAPE_GET_START = {"173-AAA": 102 + 12 / 60,
                  "174-AAA": 106 + 17 / 60,
                  "175-AAA": 109 + 21 / 60}
LAUNCH_UTC = pd.Timestamp("1969-07-16 13:32:00")

ECHO_LO, ECHO_HI = 2.2, 3.0
Z_DETECT = 3.0  # per-utterance candidate threshold (secondary evidence; the
                # primary measurement is each tape's aggregate mean curve)


def horizons():
    geo = pd.read_csv(os.path.join(DATA, "horizons_rtt.csv"), parse_dates=["utc"])
    geo["get_h"] = (geo["utc"] - LAUNCH_UTC) / pd.Timedelta("1h")
    return geo


def load_echo():
    out = {}
    for p in sorted(glob.glob(os.path.join(RESULTS, "echo_*.json"))):
        with open(p) as f:
            d = json.load(f)
        out[d["label"]] = d
    return out


def plot_correlation(echo):
    n = len(echo)
    fig, axes = plt.subplots(n, 1, figsize=(10, 3.2 * n), sharex=True)
    if n == 1:
        axes = [axes]
    for ax, (label, d) in zip(axes, echo.items()):
        lag = np.array(d["lag_axis"])
        if d["mean_curve"]:
            ax.plot(lag, d["mean_curve"], color="#d62728", lw=1.6,
                    label=f"CapCom utterances (n={d['n_capcom_used']})")
        if d["ctrl_curve"]:
            ax.plot(lag, d["ctrl_curve"], color="#7f7f7f", lw=1.2, alpha=0.8,
                    label=f"control: crew/PAO speech (n={d['n_control_used']})")
        ax.axvspan(ECHO_LO, ECHO_HI, color="#1f77b4", alpha=0.08,
                   label="physically allowed lunar-echo lags")
        ax.set_ylabel("mean z of envelope corr.")
        ax.set_title(f"Tape {label}", fontsize=10, loc="left")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8, loc="upper left")
    axes[-1].set_xlabel("lag after CapCom speech (s)")
    fig.suptitle("Searching Houston tapes for CapCom's voice returning from the Moon",
                 y=0.995)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "echo_correlation.png"), dpi=150)
    print("wrote echo_correlation.png")


def aggregate_peak(d):
    """Peak of a tape's mean z-curve in the echo band + rough uncertainty."""
    if not d["mean_curve"]:
        return None
    lag = np.array(d["lag_axis"])
    mc = np.array(d["mean_curve"])
    band = (lag >= ECHO_LO) & (lag <= ECHO_HI)
    ipk = int(np.argmax(np.where(band, mc, -np.inf)))
    # uncertainty: half-width of the region around the peak above half its height
    half = mc[ipk] / 2
    i0 = ipk
    while i0 > 0 and mc[i0 - 1] > half:
        i0 -= 1
    i1 = ipk
    while i1 < len(mc) - 1 and mc[i1 + 1] > half:
        i1 += 1
    err = max(0.03, (lag[i1] - lag[i0]) / 2)
    sigma = mc[ipk] * np.sqrt(d["n_capcom_used"])  # null: mean of n unit-z curves
    return dict(lag=float(lag[ipk]), err=float(err), meanz=float(mc[ipk]),
                sigma=float(sigma), n=d["n_capcom_used"])


def plot_events(echo):
    geo = horizons()
    fig, ax = plt.subplots(figsize=(10, 5.5))
    colors = {"173-AAA": "#2ca02c", "174-AAA": "#d62728", "175-AAA": "#9467bd"}
    detections = []
    for label, d in echo.items():
        g0 = TAPE_GET_START.get(label)
        if g0 is None:
            continue
        for u in d["per_utt"]:
            if u["peak_z"] >= Z_DETECT:
                get_h = g0 + u["t"] / 3600.0
                detections.append((label, get_h, u["peak_lag"], u["peak_z"], u["t"]))
    for label, get_h, lagv, z, t in detections:
        ax.scatter(get_h, lagv, s=20 + 8 * (z - Z_DETECT), marker="o",
                   color=colors.get(label, "k"), alpha=0.6,
                   edgecolor="k", linewidth=0.4, zorder=3)
    # per-tape aggregate measurement (primary): peak of the mean z-curve,
    # plotted at the tape's central GET with its span as x-error
    aggs = {}
    for label, d in echo.items():
        g0 = TAPE_GET_START.get(label)
        agg = aggregate_peak(d)
        if g0 is None or agg is None or agg["sigma"] < 3:
            continue
        aggs[label] = agg
        gmid = g0 + d["duration_s"] / 2 / 3600
        ax.errorbar(gmid, agg["lag"], xerr=d["duration_s"] / 2 / 3600,
                    yerr=agg["err"], fmt="D", ms=9, color=colors.get(label, "k"),
                    ecolor=colors.get(label, "k"), elinewidth=1.6, capsize=4,
                    zorder=4, markeredgecolor="k")
        ax.annotate(f"{agg['lag']:.2f} s ({agg['sigma']:.1f}σ, n={agg['n']})",
                    (gmid, agg["lag"]), xytext=(8, 10),
                    textcoords="offset points", fontsize=9)
    sel = (geo["get_h"] > 95) & (geo["get_h"] < 135)
    ax.plot(geo["get_h"][sel], geo["rtt_s"][sel], color="#1f77b4", lw=2,
            label="JPL Horizons round-trip light time (geocentric)")
    ax.axhline(0.0, color="k", lw=0.8)
    handles, labels_ = ax.get_legend_handles_labels()
    for lab, c in colors.items():
        if lab in aggs:
            handles.append(plt.Line2D([], [], marker="D", ls="", color=c,
                                      markeredgecolor="k"))
            labels_.append(f"tape {lab}: aggregate echo delay over all "
                           f"CapCom utterances")
        if any(d[0] == lab for d in detections):
            handles.append(plt.Line2D([], [], marker="o", ls="", color=c, alpha=0.6))
            labels_.append(f"tape {lab}: individual echo candidates (z>={Z_DETECT:g})")
    ax.set_xlabel("Ground elapsed time (h since launch)")
    ax.set_ylabel("measured delay of CapCom's returning voice (s)")
    ax.set_title("CapCom echo delay measured in NASA Houston tapes vs "
                 "JPL ephemeris prediction\n(a sound stage would put this at "
                 "zero -- or nowhere at all)")
    ax.set_ylim(2.0, 3.2)
    ax.grid(alpha=0.3)
    ax.legend(handles, labels_, fontsize=8, loc="lower left")
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "echo_events.png"), dpi=150)
    print(f"wrote echo_events.png  ({len(detections)} candidates, "
          f"{len(aggs)} aggregate measurements)")
    return detections, aggs


def plot_turn_taking():
    p = os.path.join(RESULTS, "turn_taking.json")
    if not os.path.exists(p):
        print("no turn_taking.json; skipping")
        return
    with open(p) as f:
        d = json.load(f)
    g1, g2 = np.array(d["g1_all"]), np.array(d["g2_all"])
    bins = np.arange(0, 8.05, 0.4)

    # KDE modes
    from scipy.stats import gaussian_kde
    xs = np.linspace(0, 8, 800)
    k1 = gaussian_kde(g1, bw_method=0.18)(xs)
    k2 = gaussian_kde(g2, bw_method=0.18)(xs)
    mode2 = xs[np.argmax(k2)]
    mode1 = xs[(xs > 1.8)][np.argmax(k1[xs > 1.8])]  # main (reply) mode

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.hist(g2, bins=bins, alpha=0.45, color="#7f7f7f", density=True,
            label=f"crew stops -> CapCom starts (n={len(g2)}), "
                  f"median {np.median(g2):.2f} s: human reaction only")
    ax.hist(g1, bins=bins, alpha=0.45, color="#d62728", density=True,
            label=f"CapCom stops -> crew starts (n={len(g1)}), "
                  f"median {np.median(g1):.2f} s: reaction + round trip")
    ax.plot(xs, k2, color="#4d4d4d", lw=1.5)
    ax.plot(xs, k1, color="#a02020", lw=1.5)
    ax.axvspan(2.56, 2.60, color="#1f77b4", alpha=0.55, zorder=0,
               label="Earth-Moon round-trip light time at these GETs (Horizons)")
    ax.annotate(f"mode {mode2:.1f} s", (mode2, k2.max()), xytext=(6, 6),
                textcoords="offset points", color="#4d4d4d", fontsize=9)
    ax.annotate(f"reply mode {mode1:.1f} s", (mode1, k1[xs > 1.8].max()),
                xytext=(6, 6), textcoords="offset points",
                color="#a02020", fontsize=9)
    ax.set_xlabel("gap between transmissions, as recorded at Houston (s)")
    ax.set_ylabel("probability density")
    diff = np.median(g1) - np.median(g2)
    ax.set_title("Turn-taking asymmetry in Apollo 11 air-to-ground audio "
                 "(tapes 173/174/175)\n"
                 f"median difference = {diff:.2f} s; on a sound stage both "
                 "histograms would be the same")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "turn_taking_hist.png"), dpi=150)
    print(f"wrote turn_taking_hist.png  (modes: G1 {mode1:.2f}, G2 {mode2:.2f})")


if __name__ == "__main__":
    echo = load_echo()
    if echo:
        plot_correlation(echo)
        det, aggs = plot_events(echo)
        for d in det:
            print(f"  {d[0]}  GET {d[1]:.2f} h  tape-t {d[4]:.0f} s  "
                  f"lag {d[2]:.2f} s  z {d[3]:.1f}")
        for lab, a in aggs.items():
            print(f"  AGG {lab}: {a['lag']:.3f} +- {a['err']:.3f} s  "
                  f"({a['sigma']:.1f} sigma, n={a['n']})")
    plot_turn_taking()
