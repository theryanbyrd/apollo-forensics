#!/usr/bin/env python
"""Plot the single best-detected CapCom echo: envelope + correlation + spectrogram.

Picks the highest-z detection from the echo_*.json files, renders a figure
showing (a) the band-limited envelope with the utterance and its delayed copy,
(b) the normalized cross-correlation with the peak at the round-trip time.
Writes results/echo_example.png and results/echo_example.wav (12 s excerpt so
anyone can listen for themselves).
"""
import glob
import json
import os

import numpy as np
import soundfile as sf
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import audio_utils as au
import measure_delay as md
from plot_results import TAPE_GET_START, aggregate_peak

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
DATA = os.path.join(HERE, "data")


def best_detection():
    """Highest-z utterance from tapes with a >=3-sigma aggregate echo, whose
    lag agrees with that tape's aggregate lag (avoids showcasing an isolated
    noise peak from a tape with no echo)."""
    best = None
    for p in sorted(glob.glob(os.path.join(RESULTS, "echo_*.json"))):
        with open(p) as f:
            d = json.load(f)
        agg = aggregate_peak(d)
        if agg is None or agg["sigma"] < 3:
            continue
        for u in d["per_utt"]:
            if abs(u["peak_lag"] - agg["lag"]) > 0.15:
                continue
            if best is None or u["peak_z"] > best[1]["peak_z"]:
                best = (d, u)
    return best


def main():
    d, u = best_detection()
    label, t0, lagv = d["label"], u["t"], u["peak_lag"]
    dur = min(u["dur"], 10.0)
    get_h = TAPE_GET_START[label] + t0 / 3600.0
    print(f"best echo: tape {label}  t={t0:.1f} s  GET~{get_h:.2f} h  "
          f"lag={lagv:.2f} s  z={u['peak_z']:.1f}")

    wav = os.path.join(DATA, f"{label}_{au.FS}.wav")
    a = max(0.0, t0 - 1.0)
    span = 1.0 + dur + md.LAG_MAX + 1.0
    with sf.SoundFile(wav) as f:
        f.seek(int(a * au.FS))
        x = f.read(int(span * au.FS), dtype="float32")
    sf.write(os.path.join(RESULTS, "echo_example.wav"), x, au.FS)

    env, fs_env = au.envelope(x, au.FS, fs_env=au.FS / 110)
    tt = a + np.arange(len(env)) / fs_env
    lags, cc = md.xcorr_curve(env, fs_env, t0 - a, t0 - a + dur)

    fig, axes = plt.subplots(2, 1, figsize=(11, 7))
    ax = axes[0]
    ax.plot(tt - t0, env, lw=0.7, color="#333333")
    ax.axvspan(0, dur, color="#d62728", alpha=0.15,
               label="CapCom transmission (recorded at Houston)")
    ax.axvspan(lagv, lagv + dur, color="#1f77b4", alpha=0.15,
               label=f"same words returning from the Moon (+{lagv:.2f} s)")
    ax.set_xlabel(f"time (s) relative to utterance start "
                  f"(tape {label} @ {t0:.0f} s, GET ~{get_h:.2f} h)")
    ax.set_ylabel("speech envelope (log, high-passed)")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    ax.set_title("The clearest single echo found by the pipeline")

    ax = axes[1]
    ax.plot(lags, cc, color="#333333", lw=1.2)
    ax.axvspan(2.2, 3.0, color="#1f77b4", alpha=0.08,
               label="physically allowed lunar-echo lags")
    ipk = np.argmax(np.where((lags >= 2.2) & (lags <= 3.0), cc, -np.inf))
    ax.annotate(f"{lags[ipk]:.2f} s", (lags[ipk], cc[ipk]),
                xytext=(10, 10), textcoords="offset points", fontsize=11,
                arrowprops=dict(arrowstyle="->"))
    ax.set_xlabel("lag (s)")
    ax.set_ylabel("normalized envelope correlation")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "echo_example.png"), dpi=150)
    print("wrote results/echo_example.png and results/echo_example.wav")


if __name__ == "__main__":
    main()
