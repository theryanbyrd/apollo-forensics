"""Shared helpers for claim 09 (gravity / slowed-footage) analysis."""
import os
import subprocess
import glob

import cv2
import numpy as np
import imageio_ffmpeg

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                    # claims/09-gravity
DATA = os.path.join(ROOT, "data")
RESULTS = os.path.join(ROOT, "results")

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

# ----------------------------------------------------------------------------
# Data sources (provenance).  The ALSJ pages moved off history.nasa.gov in
# ~2023; we fetch the clips through the Internet Archive Wayback Machine
# snapshots of the original NASA-hosted files.
# ----------------------------------------------------------------------------
SOURCES = {
    # Apollo 15 hammer-feather drop, ALSJ "MPEG Clip (49 sec; 6.2Mb)" linked at
    # 167:22:02 in the EVA-3 closeout journal (a15.clsout3.html).
    "a15v_1672206.mpg": (
        "http://web.archive.org/web/20200303130411if_/"
        "https://history.nasa.gov/alsj/a15/a15v_1672206.mpg"
    ),
    # Apollo 16 John Young "jump salute", ALSJ video library (video16.html).
    "a16salute.mpg": (
        "http://web.archive.org/web/20191119005030if_/"
        "https://history.nasa.gov/alsj/a16/a16salute.mpg"
    ),
    # Independent-lineage copy of the hammer-feather TV footage (cross-check).
    "hammer_feather_archiveorg.mp4": (
        "https://archive.org/download/FeatherHammerDropOnMoon/"
        "Feather%20%26%20Hammer%20Drop%20on%20Moon.mp4"
    ),
}


def fetch(name):
    """Download a source video into data/ if not already cached."""
    os.makedirs(DATA, exist_ok=True)
    path = os.path.join(DATA, name)
    if os.path.exists(path) and os.path.getsize(path) > 100_000:
        return path
    import requests
    url = SOURCES[name]
    print(f"downloading {name} from {url}")
    r = requests.get(url, timeout=300)
    r.raise_for_status()
    with open(path, "wb") as f:
        f.write(r.content)
    return path


def extract_frames(video_name, frames_dir):
    """Extract every frame (no duplication/drops: -vsync 0) as PNGs."""
    outdir = os.path.join(DATA, frames_dir)
    if glob.glob(os.path.join(outdir, "f*.png")):
        return outdir
    os.makedirs(outdir, exist_ok=True)
    video = fetch(video_name)
    subprocess.run(
        [FFMPEG, "-y", "-i", video, "-vsync", "0",
         os.path.join(outdir, "f%05d.png")],
        check=True, capture_output=True)
    return outdir


def extract_audio(video_name, wav_name, sr=16000):
    video = fetch(video_name)
    wav = os.path.join(DATA, wav_name)
    if not os.path.exists(wav):
        subprocess.run(
            [FFMPEG, "-y", "-i", video, "-vn", "-ac", "1", "-ar", str(sr), wav],
            check=True, capture_output=True)
    return wav


def load_gray(frames_dir, i):
    p = os.path.join(DATA, frames_dir, f"f{i:05d}.png")
    im = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
    if im is None:
        raise FileNotFoundError(p)
    return im.astype(np.float32)


def median_background(frames_dir, frame_range):
    stack = np.stack([load_gray(frames_dir, i) for i in frame_range])
    return np.median(stack, axis=0)


def lane_blobs(img, bg, xa, xb, ya, yb, thr, min_area=3):
    """Connected bright/dark blobs of |img-bg| inside a lane; returns
    intensity-weighted centroids (x, y, area, peak)."""
    d = np.abs(img - bg)[ya:yb, xa:xb]
    m = (d > thr).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m)
    out = []
    for k in range(1, n):
        a = stats[k, cv2.CC_STAT_AREA]
        if a >= min_area:
            ys, xs = np.where(lab == k)
            w = d[ys, xs]
            cy = (ys * w).sum() / w.sum() + ya
            cx = (xs * w).sum() / w.sum() + xa
            out.append((cx, cy, int(a), float(w.max())))
    return out
