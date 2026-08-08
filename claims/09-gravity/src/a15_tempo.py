"""Tempo test: if the footage is Earth footage slowed by s=2.46, then every
human process in it - including David Scott's SPEECH - ran 2.46x faster in
reality. The clip's audio is in sync with the video (MPEG-1 system-stream
PTS), and the same 2.46x factor would have to apply to it.

We measure Scott's speaking rate over his Galileo monologue and ask what the
"real" rate would have been under the hoax hypothesis.

The monologue text is fixed by the Apollo 15 ALSJ transcript (167:22:06 to
167:22:43); we count its syllables and divide by the measured duration of the
corresponding speech in the clip audio (and by active-speech time with pauses
removed).
"""
import json
import os
import re

import numpy as np
import soundfile as sf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import common as C

# ALSJ transcript, 167:22:06 -> 167:22:43 (a15.clsout3.html)
MONOLOGUE = """
Well, in my left hand, I have a feather; in my right hand, a hammer. And I
guess one of the reasons we got here today was because of a gentleman named
Galileo, a long time ago, who made a rather significant discovery about
falling objects in gravity fields. And we thought where would be a better
place to confirm his findings than on the Moon. And so we thought we'd try
it here for you. The feather happens to be, appropriately, a falcon feather
for our Falcon. And I'll drop the two of them here and, hopefully, they'll
hit the ground at the same time.
"""

S = 2.46
NORMAL_SYL_RATE = (3.5, 5.5)   # syl/s, conversational English (articulation
                               # rates run ~4-6; overall incl. pauses 3.5-5)


def count_syllables(text):
    words = re.findall(r"[a-z']+", text.lower())
    total = 0
    for w in words:
        w = w.strip("'")
        groups = re.findall(r"[aeiouy]+", w)
        n = len(groups)
        if w.endswith("e") and not w.endswith(("le", "ee", "ye")) and n > 1:
            n -= 1
        total += max(1, n)
    return total, len(words)


def speech_segments(env, t, thr_hi):
    act = env > thr_hi
    segs = []
    on = None
    for i in range(1, len(act)):
        if act[i] and not act[i - 1]:
            on = t[i]
        if not act[i] and act[i - 1] and on is not None:
            if t[i] - on > 0.10:
                segs.append((on, t[i]))
            on = None
    return segs


def main():
    wav = C.extract_audio("a15v_1672206.mpg", "a15_audio.wav")
    y, sr = sf.read(wav)
    win = int(0.05 * sr)
    env = np.sqrt(np.convolve(y ** 2, np.ones(win) / win, mode="same"))
    t = np.arange(len(y)) / sr

    # The monologue: continuous talking from first onset (~1.9 s) to the last
    # active segment before the >1.5 s silence around 38.5 s (the release).
    thr_seg = 1.6 * np.percentile(env, 55)
    segs = [s for s in speech_segments(env, t, thr_seg) if s[0] < 39.5]
    mono_start = segs[0][0]
    mono_end = max(e for _, e in segs if e < 39.5)
    gross = mono_end - mono_start
    # voiced-time estimate: low threshold just above the radio noise floor
    w = (t > mono_start) & (t < mono_end)
    e = env[w]
    floor, p95 = np.percentile(e, 10), np.percentile(e, 95)
    active = float((e > floor + 0.10 * (p95 - floor)).mean() * gross)

    syl, words = count_syllables(MONOLOGUE)
    rate_gross = syl / gross
    rate_active = syl / active
    out = {
        "monologue": {
            "syllables": syl, "words": words,
            "clip_window_s": [round(mono_start, 2), round(mono_end, 2)],
            "gross_duration_s": round(gross, 2),
            "voiced_time_est_s": round(active, 2),
            "syl_rate_gross_incl_pauses": round(rate_gross, 2),
            "syl_rate_articulation_upper_bound": round(rate_active, 2),
        },
        "hoax_implication": {
            "slowdown_factor": S,
            "implied_real_rate_gross": round(rate_gross * S, 2),
            "implied_real_rate_active": round(rate_active * S, 2),
            "normal_conversational_range": NORMAL_SYL_RATE,
            "note": "GET timestamps (167:22:06-167:22:43, ~37 s) match the "
                    "measured clip duration 1:1, so the audio (and the "
                    "PTS-locked video) is running at true broadcast rate.",
        },
    }
    with open(os.path.join(C.RESULTS, "a15_tempo.json"), "w") as fh:
        json.dump(out, fh, indent=2)
    print(json.dumps(out, indent=2))

    # ---------------- joint-hypothesis figure ----------------
    with open(os.path.join(C.RESULTS, "a15_fit.json")) as fh:
        fit = json.load(fh)
    with open(os.path.join(C.RESULTS, "feather_drag.json")) as fh:
        drag = json.load(fh)

    fig, axes = plt.subplots(1, 3, figsize=(13, 4.6))

    ax = axes[0]
    g, ge = fit["feather_fit"]["g_apparent_m_s2"], fit["feather_fit"]["g_err_m_s2"]
    ax.errorbar([0], [g], yerr=[ge], fmt="o", ms=10, capsize=6, color="k",
                label="fitted apparent g")
    ax.axhline(1.62, color="tab:blue", ls="-",
               label="Moon g / slowed-Earth (degenerate)")
    ax.axhline(9.81, color="tab:red", ls="--", label="real-time Earth g")
    ax.set_xlim(-1, 1)
    ax.set_xticks([])
    ax.set_ylabel("apparent acceleration (m/s$^2$)")
    ax.set_title("Ballistics\n(cannot separate Moon from\nslowed Earth "
                 "- by construction)")
    ax.legend(fontsize=8)

    ax = axes[1]
    labels = ["observed\n(incl. pauses)", "implied real\nx2.46"]
    vals = [rate_gross, rate_gross * S]
    cols = ["tab:blue", "tab:red"]
    ax.bar(labels, vals, color=cols, width=0.55)
    ax.axhspan(*NORMAL_SYL_RATE, color="green", alpha=0.2, lw=0)
    ax.text(-0.42, 4.6, "normal English\nspeech range", fontsize=8,
            color="green")
    ax.set_ylabel("syllables / s")
    ax.tick_params(axis="x", labelsize=7)
    ax.set_title("Tempo (same clip's synced audio):\nunder the hoax Scott "
                 "spoke at chipmunk rate")

    ax = axes[2]
    v_obs = fit["feather_fit"]["v_at_landing_m_s"]
    v_err = fit["feather_fit"]["v_at_landing_err_m_s"]
    ax.errorbar([0], [v_obs], yerr=[v_err], fmt="o", ms=10, capsize=6,
                color="k", label="observed apparent impact speed")
    ax.axhline(drag["scenarios"]["moon_vacuum"]["real_impact_speed_m_s"],
               color="tab:blue", label="Moon vacuum prediction")
    for vt, ls in [("0.8", "--"), ("1.1", "-"), ("1.5", ":")]:
        v = drag["scenarios"][f"earth_air_vt{vt}"][
            "apparent_impact_speed_in_slowed_footage_m_s"]
        ax.axhline(v, color="tab:orange", ls=ls,
                   label=f"Earth-air feather vt={vt} (slowed)")
    ax.set_xlim(-1, 1)
    ax.set_xticks([])
    ax.set_ylabel("feather impact speed, screen time (m/s)")
    ax.set_title("Drag\n(feather at terminal velocity can't\nbe rescaled "
                 "into the observed track)")
    ax.legend(fontsize=7, loc="center right")

    plt.suptitle("Claim 9 joint test: one global slow-down factor must "
                 "explain all three - it can't", y=1.0)
    plt.tight_layout()
    plt.savefig(os.path.join(C.RESULTS, "joint_hypothesis.png"), dpi=110)
    return out


if __name__ == "__main__":
    main()
