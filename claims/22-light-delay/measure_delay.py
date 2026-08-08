#!/usr/bin/env python
"""Echo cross-correlation: find the Earth-Moon round-trip delay inside the tape.

Physics: these reels record the air-to-ground loop AT HOUSTON.  When CapCom
speaks, his voice is recorded immediately (local mic).  The same voice travels
up to the Moon, plays in the crew's earphones, leaks into their live (VOX)
mics, and returns on the downlink -- arriving one full round-trip light time
(~2.5-2.7 s) later.  So CapCom utterances should be followed by a faint,
delayed copy of themselves.  A sound stage has no such channel: the "echo"
would be absent (or at a constant, arbitrary lag).

Method:
  1. Detect Quindar tones (2525 Hz intro / 2475 Hz outro beeps that keyed the
     uplink transmitter) -> CapCom utterance spans.
  2. Compute a band-limited log Hilbert envelope of the whole tape (~100 Hz).
  3. For each CapCom utterance, normalized-cross-correlate its envelope
     against the envelope over lags 0.8-4.4 s.
  4. z-score each curve against off-echo lags, average across utterances.
     Control: same procedure on non-CapCom (crew/PAO) speech segments, where
     no echo should exist.

Usage: measure_delay.py TAPE.mp3 --met-start HH:MM [--out results/prefix]
Outputs per-tape JSON + plots in results/.
"""
import argparse
import json
import os

import numpy as np
from scipy import signal

import audio_utils as au

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
os.makedirs(RESULTS, exist_ok=True)

LAG_MIN, LAG_MAX = 0.8, 4.4          # searched lag range (s)
ECHO_LO, ECHO_HI = 2.2, 3.0          # where a lunar echo may live (s)
CHUNK_DEC = 110                       # envelope decimation (11025/110 ~ 100.2 Hz)
CHUNK_SAMP = 60500 * CHUNK_DEC        # ~603 s chunks, multiple of decimation
PAD = 200 * CHUNK_DEC                 # chunk overlap (samples, ~2 s), multiple of
                                      # the decimation so envelope grids align


def tape_envelope_and_quindar(x, fs):
    """Chunked processing of a long tape -> (envelope, fs_env, quindar events)."""
    pad = PAD
    envs = []
    events = []
    n = len(x)
    fs_env = None
    for start in range(0, n, CHUNK_SAMP):
        a = max(0, start - pad)
        b = min(n, start + CHUNK_SAMP + pad)
        chunk = x[a:b]
        env, fs_env = au.envelope(chunk, fs, fs_env=fs / CHUNK_DEC)
        # cut the pads (in decimated samples)
        cut0 = (start - a) // CHUNK_DEC
        cut1 = cut0 + min(CHUNK_SAMP, n - start) // CHUNK_DEC
        envs.append(env[cut0:cut1])
        for ev in au.quindar_detect(chunk, fs):
            ev = dict(ev)
            t_off = a / fs
            ev["t0"] += t_off
            ev["t1"] += t_off
            if start / fs <= ev["t0"] < (start + CHUNK_SAMP) / fs:
                events.append(ev)
    env = np.concatenate(envs)
    # de-duplicate quindar events (overlap regions)
    events.sort(key=lambda e: e["t0"])
    dedup = []
    for ev in events:
        if dedup and abs(ev["t0"] - dedup[-1]["t0"]) < 0.1:
            continue
        dedup.append(ev)
    return env, fs / CHUNK_DEC, dedup


def capcom_spans(events, min_dur=0.8, max_dur=15.0):
    """Pair intro->outro Quindar tones into keyed uplink spans."""
    spans = []
    intro = None
    for ev in events:
        if ev["kind"] == "intro":
            intro = ev
        elif ev["kind"] == "outro" and intro is not None:
            dur = ev["t0"] - intro["t1"]
            if min_dur <= dur <= max_dur:
                spans.append((intro["t1"], ev["t0"]))
            intro = None
    return spans


def xcorr_curve(env, fs_env, t0, t1, lag_min=LAG_MIN, lag_max=LAG_MAX):
    """Normalized cross-correlation of env[t0:t1] vs env at positive lags."""
    i0, i1 = int(t0 * fs_env), int(t1 * fs_env)
    tpl = env[i0:i1].astype(np.float64)
    tpl = tpl - tpl.mean()
    ntpl = np.linalg.norm(tpl)
    if ntpl < 1e-6 or len(tpl) < int(0.5 * fs_env):
        return None, None
    lmax = int(lag_max * fs_env)
    seg = env[i0:i1 + lmax].astype(np.float64)
    if len(seg) < len(tpl) + lmax:
        return None, None
    # sliding normalized correlation
    num = signal.correlate(seg, tpl, mode="valid")  # lag 0..lmax
    # running norms of seg windows
    c1 = np.concatenate([[0], np.cumsum(seg)])
    c2 = np.concatenate([[0], np.cumsum(seg ** 2)])
    L = len(tpl)
    wsum = c1[L:] - c1[:-L]
    wsq = c2[L:] - c2[:-L]
    wnorm = np.sqrt(np.maximum(wsq - wsum ** 2 / L, 1e-12))
    cc = (num - wsum * tpl.mean()) / (wnorm * ntpl + 1e-12)
    lags = np.arange(len(cc)) / fs_env
    keep = (lags >= lag_min) & (lags <= lag_max)
    return lags[keep], cc[keep]


def zscore_curve(lags, cc, exclude=(ECHO_LO, ECHO_HI)):
    off = (lags < exclude[0]) | (lags > exclude[1])
    mu, sd = cc[off].mean(), cc[off].std() + 1e-12
    return (cc - mu) / sd


def analyze(tape_path, met_start, label, no_capcom_reuse_window=3.2):
    print(f"=== {label}: decoding")
    x, fs = au.decode(tape_path)
    dur = len(x) / fs
    print(f"    {dur/3600:.2f} h @ {fs} Hz")
    print("    envelope + quindar detection (chunked)")
    env, fs_env, events = tape_envelope_and_quindar(x, fs)
    del x
    n_intro = sum(1 for e in events if e["kind"] == "intro")
    n_outro = sum(1 for e in events if e["kind"] == "outro")
    print(f"    quindar tones: {n_intro} intro / {n_outro} outro")
    spans = capcom_spans(events)
    print(f"    capcom utterances (0.8-15 s): {len(spans)}")

    quindar_marks = [(e["t0"], e["t1"]) for e in events]

    def clean(spanlist):
        """Drop spans whose echo-search window collides with new uplink keying."""
        out = []
        for (a, b) in spanlist:
            collide = any(q0 > b and q0 < b + no_capcom_reuse_window
                          for q0, _ in quindar_marks)
            if not collide:
                out.append((a, b))
        return out

    spans_clean = clean(spans)
    print(f"    after excluding overlapped-keying spans: {len(spans_clean)}")

    curves, per_utt = [], []
    lag_axis = None
    for (a, b) in spans_clean:
        b_eff = min(b, a + 10.0)
        lags, cc = xcorr_curve(env, fs_env, a, b_eff)
        if lags is None:
            continue
        z = zscore_curve(lags, cc)
        if lag_axis is None:
            lag_axis = lags
        if len(z) == len(lag_axis):
            curves.append(z)
            band = (lags >= ECHO_LO) & (lags <= ECHO_HI)
            ipk = np.argmax(np.where(band, z, -np.inf))
            per_utt.append(dict(t=a, dur=b - a, peak_lag=float(lags[ipk]),
                                peak_z=float(z[ipk])))
    curves = np.array(curves)
    print(f"    correlated {len(curves)} utterances")

    # control: non-capcom speech (crew + PAO announcer), same pipeline
    voice = au.vad(env, fs_env)
    in_capcom = np.zeros(len(env), bool)
    for (a, b) in spans:
        in_capcom[int(a * fs_env):int(b * fs_env)] = True
    ctrl_spans = []
    for (a, b) in voice:
        ia, ib = int(a * fs_env), int(b * fs_env)
        if not in_capcom[ia:ib].any() and 0.8 <= b - a <= 15:
            ctrl_spans.append((a, b))
    ctrl_spans = clean(ctrl_spans)
    ctrl_curves = []
    for (a, b) in ctrl_spans:
        b_eff = min(b, a + 10.0)
        lags, cc = xcorr_curve(env, fs_env, a, b_eff)
        if lags is None or len(cc) != len(lag_axis):
            continue
        ctrl_curves.append(zscore_curve(lags, cc))
    ctrl_curves = np.array(ctrl_curves)
    print(f"    control (non-capcom) utterances: {len(ctrl_curves)}")

    out = dict(label=label, tape=os.path.basename(tape_path), duration_s=dur,
               met_start=met_start, fs_env=fs_env,
               n_quindar_intro=n_intro, n_quindar_outro=n_outro,
               n_capcom=len(spans), n_capcom_used=int(len(curves)),
               n_control_used=int(len(ctrl_curves)),
               lag_axis=lag_axis.tolist(),
               mean_curve=curves.mean(axis=0).tolist() if len(curves) else None,
               ctrl_curve=ctrl_curves.mean(axis=0).tolist() if len(ctrl_curves) else None,
               per_utt=per_utt)
    return out


def met_to_seconds(met):
    h, m = met.split(":")[:2]
    return int(h) * 3600 + int(m) * 60


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tape")
    ap.add_argument("--met-start", required=True,
                    help="GET at tape start, HH:MM (from NASA tape catalog)")
    ap.add_argument("--label", default=None)
    args = ap.parse_args()
    label = args.label or os.path.splitext(os.path.basename(args.tape))[0]
    res = analyze(args.tape, args.met_start, label)
    out_json = os.path.join(RESULTS, f"echo_{label}.json")
    with open(out_json, "w") as f:
        json.dump(res, f)
    print(f"wrote {out_json}")

    if res["mean_curve"]:
        lag = np.array(res["lag_axis"])
        mc = np.array(res["mean_curve"])
        band = (lag >= ECHO_LO) & (lag <= ECHO_HI)
        ipk = np.argmax(np.where(band, mc, -np.inf))
        print(f"    MEAN-CURVE peak in echo band: lag={lag[ipk]:.3f} s  "
              f"z={mc[ipk]:.2f} (n={res['n_capcom_used']})")


if __name__ == "__main__":
    main()
