#!/usr/bin/env python
"""Turn-taking asymmetry: the light delay hides in conversational gaps.

These tapes record the loop AT HOUSTON.  Therefore:
  - CapCom's voice is recorded with zero delay.
  - The crew hears CapCom one uplink light-time later, and their reply takes
    one downlink light-time to come back.
  So the Houston-observed gap (CapCom stops -> crew starts) contains one full
  round-trip light time PLUS human reaction time, while the reverse gap
  (crew stops -> CapCom starts) contains human reaction time only.
  Prediction: gap distributions differ by ~2.5-2.7 s.  A sound-stage
  conversation has no such asymmetry.

CapCom transmissions are identified by Quindar keying tones (2525 Hz key /
2475 Hz unkey).  Non-CapCom speech is classified crew vs PAO-announcer by
high-frequency content (the S-band downlink is band-limited and noisy; the
announcer's studio mic is not).

Usage: turn_taking.py TAPE.mp3 [TAPE2.mp3 ...] --out results/turn_taking
"""
import argparse
import json
import os

import numpy as np
import soundfile as sf
from scipy import signal

import audio_utils as au

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
os.makedirs(RESULTS, exist_ok=True)

import measure_delay as md


def hf_ratio(wav_path, fs, t0, t1):
    """Power(3300-5200 Hz) / Power(300-2800 Hz) for audio in [t0, t1]."""
    with sf.SoundFile(wav_path) as f:
        f.seek(int(t0 * fs))
        x = f.read(int((t1 - t0) * fs), dtype="float32")
    if len(x) < fs // 4:
        return None
    fxx, pxx = signal.welch(x, fs=fs, nperseg=2048)
    lo = pxx[(fxx >= 300) & (fxx <= 2800)].sum()
    hi = pxx[(fxx >= 3300) & (fxx <= 5200)].sum()
    return float(hi / (lo + 1e-12))


def analyze_tape(tape_path):
    label = os.path.splitext(os.path.basename(tape_path))[0]
    print(f"=== {label}")
    x, fs = au.decode(tape_path)
    wav_path = os.path.splitext(tape_path)[0] + f"_{fs}.wav"
    env, fs_env, events = md.tape_envelope_and_quindar(x, fs)
    del x
    spans = md.capcom_spans(events, min_dur=0.3, max_dur=30.0)
    print(f"    capcom keyed spans: {len(spans)}")
    voice = au.vad(env, fs_env)
    print(f"    vad segments: {len(voice)}")

    # non-capcom voice segments, with margin around keyed spans
    margin = 0.3
    others = []
    for (a, b) in voice:
        if any(a < s1 + margin and b > s0 - margin for (s0, s1) in spans):
            continue
        if 0.4 <= b - a <= 60:
            others.append((a, b))

    # classify crew (band-limited, noisy downlink) vs announcer (studio mic)
    classified = []
    for (a, b) in others:
        r = hf_ratio(wav_path, fs, a, min(b, a + 8))
        if r is None:
            continue
        classified.append((a, b, r))
    ratios = np.array([c[2] for c in classified])
    print(f"    hf-ratio percentiles 10/50/90: "
          f"{np.percentile(ratios,10):.4f} {np.percentile(ratios,50):.4f} "
          f"{np.percentile(ratios,90):.4f}")
    return dict(label=label, spans=spans, classified=classified,
                events=events, voice=voice, duration=len(env) / fs_env)


def refine_spans(spans, voice):
    """Replace keyed spans by actual CapCom speech boundaries: first/last VAD
    voice inside each keyed span.  (CapCom keys ~0.5 s before speaking and
    unkeys after; using tone times would bias both gap types.)"""
    out = []
    for (s0, s1) in spans:
        inside = [(max(a, s0), min(b, s1)) for (a, b) in voice
                  if a < s1 and b > s0]
        if inside:
            out.append((inside[0][0], inside[-1][1]))
    return out


def gaps_from(spans, crew_segs, max_gap=8.0):
    """G1: capcom speech end -> next crew onset.
       G2: crew speech end -> next capcom speech onset."""
    g1, g2 = [], []
    crew_on = sorted(s[0] for s in crew_segs)
    crew_off = sorted(s[1] for s in crew_segs)
    cap_on = sorted(s[0] for s in spans)
    for (_, s1) in spans:
        nxt = [t for t in crew_on if t > s1]
        if nxt and nxt[0] - s1 <= max_gap:
            # require no other capcom speech in between
            if not any(s1 < k < nxt[0] for k in cap_on):
                g1.append((s1, nxt[0] - s1))
    for off in crew_off:
        nxt = [k for k in cap_on if k > off]
        if nxt and nxt[0] - off <= max_gap:
            if not any(off < t < nxt[0] for t in crew_on):
                g2.append((off, nxt[0] - off))
    return g1, g2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tapes", nargs="+")
    ap.add_argument("--crew-hf-max", type=float, default=None,
                    help="hf-ratio threshold below which a segment is crew "
                         "(default: data-driven split at the distribution valley)")
    args = ap.parse_args()

    all_g1, all_g2 = [], []
    per_tape = {}
    for tp in args.tapes:
        res = analyze_tape(tp)
        ratios = np.array([c[2] for c in res["classified"]])
        thr = args.crew_hf_max
        if thr is None:
            # data-driven: log-ratio histogram valley between two modes
            lr = np.log10(ratios + 1e-6)
            hist, edges = np.histogram(lr, bins=40)
            # find minimum between the two largest peaks
            imax1 = np.argmax(hist)
            rest = hist.copy()
            w = 5
            rest[max(0, imax1 - w):imax1 + w] = 0
            imax2 = np.argmax(rest)
            i0, i1 = sorted([imax1, imax2])
            ivalley = i0 + np.argmin(hist[i0:i1 + 1]) if i1 > i0 else imax1
            thr = 10 ** edges[ivalley]
        # ambiguity band: drop segments within ~x1.6 of the threshold
        crew = [(a, b) for (a, b, r) in res["classified"] if r < thr / 1.6]
        pao = [(a, b) for (a, b, r) in res["classified"] if r > thr * 1.6]
        n_amb = len(res["classified"]) - len(crew) - len(pao)
        print(f"    threshold hf-ratio {thr:.4f}: crew {len(crew)}, "
              f"announcer {len(pao)}, ambiguous dropped {n_amb}")
        cap_speech = refine_spans(res["spans"], res["voice"])
        g1, g2 = gaps_from(cap_speech, crew)
        print(f"    gaps: capcom->crew {len(g1)}, crew->capcom {len(g2)}")
        per_tape[res["label"]] = dict(threshold=thr,
                                      g1=[[t, g] for t, g in g1],
                                      g2=[[t, g] for t, g in g2])
        all_g1 += [g for _, g in g1]
        all_g2 += [g for _, g in g2]

    a1, a2 = np.array(all_g1), np.array(all_g2)
    out = dict(per_tape=per_tape,
               g1_all=a1.tolist(), g2_all=a2.tolist(),
               g1_median=float(np.median(a1)) if len(a1) else None,
               g2_median=float(np.median(a2)) if len(a2) else None)
    if len(a1) and len(a2):
        out["median_diff"] = out["g1_median"] - out["g2_median"]
        print(f"\nMEDIANS: capcom->crew {out['g1_median']:.2f} s   "
              f"crew->capcom {out['g2_median']:.2f} s   "
              f"difference {out['median_diff']:.2f} s")
    with open(os.path.join(RESULTS, "turn_taking.json"), "w") as f:
        json.dump(out, f)
    print("wrote", os.path.join(RESULTS, "turn_taking.json"))


if __name__ == "__main__":
    main()
