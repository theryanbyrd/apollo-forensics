"""Shared audio utilities: decoding, Quindar-tone detection, envelopes.

All functions operate on mono float32 audio at a known sample rate.
MP3s are decoded once with ffmpeg (from imageio-ffmpeg) to 11025 Hz mono WAV,
cached next to the source in data/.
"""
import os
import subprocess

import numpy as np
import soundfile as sf
from scipy import signal

FS = 11025  # decode rate; keeps Quindar band (2.4-2.6 kHz) comfortably below Nyquist


def ffmpeg_bin():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def decode(mp3_path, fs=FS):
    """Decode an mp3 to cached mono WAV at fs; return (audio float32, fs)."""
    wav_path = os.path.splitext(mp3_path)[0] + f"_{fs}.wav"
    if not os.path.exists(wav_path):
        subprocess.check_call(
            [ffmpeg_bin(), "-y", "-loglevel", "error", "-i", mp3_path,
             "-ac", "1", "-ar", str(fs), wav_path])
    x, got_fs = sf.read(wav_path, dtype="float32")
    assert got_fs == fs
    return x, fs


def stft_bandpower(x, fs, nperseg=1024, hop=256):
    """Return (times, freqs, power spectrogram)."""
    f, t, Z = signal.stft(x, fs=fs, nperseg=nperseg, noverlap=nperseg - hop,
                          padded=False, boundary=None)
    return t, f, (np.abs(Z) ** 2)


def quindar_detect(x, fs, min_dur=0.12, max_dur=0.60):
    """Detect Quindar tones (2525 Hz intro / 2475 Hz outro keying beeps).

    Returns list of dicts {t0, t1, freq, kind} where kind is 'intro'/'outro'.
    Detection: STFT frames where a narrow 2.4-2.6 kHz band carries a large
    fraction of total frame power and the band peak is stable.
    """
    nperseg, hop = 2048, 256  # ~5.4 Hz bins, 23 ms hop
    t, f, P = stft_bandpower(x, fs, nperseg=nperseg, hop=hop)
    band = (f >= 2400) & (f <= 2650)
    wide = (f >= 200) & (f <= 4500)
    bandP = P[band].sum(axis=0)
    wideP = P[wide].sum(axis=0) + 1e-12
    ratio = bandP / wideP
    fband = f[band]
    peak_f = fband[np.argmax(P[band], axis=0)]

    tone = ratio > 0.6
    events = []
    i = 0
    n = len(tone)
    while i < n:
        if not tone[i]:
            i += 1
            continue
        j = i
        while j < n and tone[j]:
            j += 1
        t0, t1 = t[i], t[min(j, n - 1)]
        dur = t1 - t0
        if min_dur <= dur <= max_dur:
            fmed = float(np.median(peak_f[i:j]))
            # Quindar tones are 2525 (key) and 2475 (unkey); allow +-20 Hz
            kind = None
            if abs(fmed - 2525) < 20:
                kind = "intro"
            elif abs(fmed - 2475) < 20:
                kind = "outro"
            if kind:
                events.append(dict(t0=float(t0), t1=float(t1), freq=fmed, kind=kind))
        i = j
    return events


def envelope(x, fs, fs_env=100, lo=300.0, hi=3000.0):
    """Band-limited Hilbert envelope, resampled to fs_env, log-compressed and
    high-passed (slow gain changes removed).  Good for echo cross-correlation.
    """
    sos = signal.butter(4, [lo, hi], btype="bandpass", fs=fs, output="sos")
    xb = signal.sosfiltfilt(sos, x)
    env = np.abs(signal.hilbert(xb))
    # anti-alias then decimate to fs_env
    dec = int(round(fs / fs_env))
    sos2 = signal.butter(4, 0.4 * fs / dec, btype="low", fs=fs, output="sos")
    env = np.maximum(signal.sosfiltfilt(sos2, env)[::dec], 0.0)
    env = np.log1p(env / (np.median(env) + 1e-9))
    # remove slow trend (1.0 s moving average)
    k = int(fs_env * 1.0)
    trend = signal.convolve(env, np.ones(k) / k, mode="same")
    return (env - trend).astype(np.float32), fs / dec


def vad(env_hp, fs_env, thresh_sigma=1.0, min_dur=0.25, merge_gap=0.35):
    """Energy VAD on a high-passed log envelope.  Returns [(t0, t1), ...]."""
    # smooth the rectified envelope a little
    k = max(1, int(0.05 * fs_env))
    sm = signal.convolve(np.maximum(env_hp, 0), np.ones(k) / k, mode="same")
    sigma = np.median(np.abs(sm)) + 1e-9
    on = sm > thresh_sigma * sigma
    segs = []
    i, n = 0, len(on)
    while i < n:
        if not on[i]:
            i += 1
            continue
        j = i
        while j < n and on[j]:
            j += 1
        segs.append([i / fs_env, j / fs_env])
        i = j
    # merge close segments
    merged = []
    for s in segs:
        if merged and s[0] - merged[-1][1] < merge_gap:
            merged[-1][1] = s[1]
        else:
            merged.append(s)
    return [(a, b) for a, b in merged if b - a >= min_dur]
