#!/usr/bin/env python3
"""
Claim 06 — bulk-acquire a systematic sample of Apollo Hasselblad frames.

Source: LPI Apollo Image Atlas (Lunar and Planetary Institute), which hosts a
scan of EVERY frame of every Apollo 70mm magazine — including the blank,
blurred and accidental frames — under a systematic URL:

    https://www.lpi.usra.edu/resources/apollo/images/print/{AS11}/{40}/{5903}.jpg

Sampling design (survivorship-bias test): COMPLETE surface (EVA) Hasselblad
magazines, discovered empirically by walking frame numbers outward from a
known-good seed until 3 consecutive 404s on each side.  Nothing is
hand-picked; every frame the atlas has for these magazines is taken.

Magazines (5 surface magazines, 4 missions' EVAs):
    Apollo 11  mag 40 (S)   — the only Apollo 11 surface EVA magazine
    Apollo 12  mag 48 (Z)   — EVA 2, Surveyor III visit
    Apollo 12  mag 49 (EE)  — EVA 2
    Apollo 16  mag 113 (?)  — EVA (Young flag-jump-salute magazine)
    Apollo 17  mag 134 (B)  — EVA (flag-with-Earth magazine)

Plus ONE out-of-sample comparison icon (flight, not surface): AS17-148-22727
("Blue Marble"), marked in_sample=0 and excluded from distribution statistics.

Each print scan (~3900 px, ~4 MB) is downscaled on arrival to max side 1400 px
(LANCZOS, JPEG q=88) to keep the cache small; original dimensions are logged.
Politeness: single connection, ~0.3 s sleep after every request, identifying
User-Agent, resumable (skips frames already fetched).
"""

import argparse
import io
import json
import os
import sys
import time

import requests
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

# Two sizes exist on LPI.  "print" (~3900 px) covers Apollo 11/12/14 fully but
# has NO coverage for the Apollo 15/16/17 surface magazines (and, tellingly,
# DOES cover famous frames like AS17-148-22727 — even scan resolution is
# curated).  "browse" (450 px) covers every frame of every magazine, so all
# statistics are computed from browse; cached print files are used only to
# render prettier montage cells where available.
SIZE = "print"          # overridden by --size
FRAMES = os.path.join(DATA, "frames")
LOG = os.path.join(DATA, "download_log.jsonl")
MANIFEST = os.path.join(DATA, "manifest.csv")

BASE = "https://www.lpi.usra.edu/resources/apollo/images/{s}/{m}/{g}/{f}.jpg"
UA = "ApolloForensics/1.0 (open-source moon-hoax-claim testing; contact: ryanbyrd@gmail.com)"
DELAY = 0.3          # seconds between HTTP requests
MISS_STOP = 3        # consecutive 404s = end of magazine
MAX_SPAN = 260       # hard safety bound on frames walked per direction
SAVE_MAX_SIDE = 1400

# (mission, magazine, seed frame known to exist, in_sample)
MAGAZINES = [
    ("AS11", "40", 5903, True),
    ("AS12", "48", 7071, True),
    ("AS12", "49", 7278, True),
    ("AS16", "113", 18339, True),
    ("AS17", "134", 20384, True),
]
# out-of-sample comparison icons (scored, marked, excluded from stats)
EXTRA_FRAMES = [
    ("AS17", "148", 22727, False),   # Blue Marble (taken in flight)
]


def load_done():
    done = {}
    if os.path.exists(LOG):
        with open(LOG) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                done[rec["id"]] = rec
    return done


def log_rec(rec):
    with open(LOG, "a") as fh:
        fh.write(json.dumps(rec) + "\n")


def fetch_frame(session, mission, mag, frame, in_sample, done):
    fid = f"{mission}-{mag}-{frame}"
    path = os.path.join(FRAMES, fid + ".jpg")
    prev = done.get(fid)
    if prev is not None:
        if prev["status"] == "ok" and os.path.exists(path):
            return "ok"
        if prev["status"] == "missing":
            return "missing"
    url = BASE.format(s=SIZE, m=mission, g=mag, f=frame)
    try:
        r = session.get(url, timeout=60)
    except requests.RequestException as e:
        time.sleep(2.0)
        try:
            r = session.get(url, timeout=60)
        except requests.RequestException as e2:
            print(f"  {fid}: network error twice ({e2}); recording as error", flush=True)
            rec = {"id": fid, "mission": mission, "magazine": mag, "frame": frame,
                   "url": url, "status": "error", "in_sample": int(in_sample)}
            log_rec(rec)
            done[fid] = rec
            time.sleep(DELAY)
            return "error"
    time.sleep(DELAY)
    if r.status_code == 404:
        rec = {"id": fid, "mission": mission, "magazine": mag, "frame": frame,
               "url": url, "status": "missing", "in_sample": int(in_sample)}
        log_rec(rec)
        done[fid] = rec
        return "missing"
    if r.status_code != 200:
        print(f"  {fid}: HTTP {r.status_code}", flush=True)
        rec = {"id": fid, "mission": mission, "magazine": mag, "frame": frame,
               "url": url, "status": "error", "in_sample": int(in_sample)}
        log_rec(rec)
        done[fid] = rec
        return "error"
    raw = r.content
    try:
        im = Image.open(io.BytesIO(raw))
        im.load()
    except Exception as e:
        print(f"  {fid}: not decodable ({e})", flush=True)
        rec = {"id": fid, "mission": mission, "magazine": mag, "frame": frame,
               "url": url, "status": "error", "in_sample": int(in_sample)}
        log_rec(rec)
        done[fid] = rec
        return "error"
    ow, oh = im.size
    if SIZE == "print" and max(im.size) > SAVE_MAX_SIDE:
        scale = SAVE_MAX_SIDE / max(im.size)
        im = im.resize((round(ow * scale), round(oh * scale)), Image.LANCZOS)
    if im.mode != "RGB":
        im = im.convert("RGB")
    im.save(path, "JPEG", quality=88)
    rec = {"id": fid, "mission": mission, "magazine": mag, "frame": frame,
           "url": url, "status": "ok", "in_sample": int(in_sample),
           "orig_w": ow, "orig_h": oh, "saved_w": im.size[0], "saved_h": im.size[1],
           "bytes_downloaded": len(raw)}
    log_rec(rec)
    done[fid] = rec
    return "ok"


def walk_magazine(session, mission, mag, seed, in_sample, done):
    print(f"== {mission} magazine {mag} (seed {seed}) ==", flush=True)
    st = fetch_frame(session, mission, mag, seed, in_sample, done)
    if st != "ok":
        print(f"  SEED {mission}-{mag}-{seed} not fetchable ({st})!", flush=True)
    n_ok = 1 if st == "ok" else 0
    for step in (-1, +1):
        misses = 0
        f = seed
        for _ in range(MAX_SPAN):
            f += step
            st = fetch_frame(session, mission, mag, f, in_sample, done)
            if st == "ok":
                misses = 0
                n_ok += 1
            elif st == "missing":
                misses += 1
                if misses >= MISS_STOP:
                    break
            # network 'error' neither resets nor increments the 404 counter
        print(f"  direction {step:+d} stopped at frame {f}", flush=True)
    print(f"  {mission}-{mag}: {n_ok} frames fetched so far", flush=True)


def write_manifest(done):
    import csv
    rows = sorted(done.values(), key=lambda r: (r["mission"], int(r["magazine"]), r["frame"]))
    cols = ["id", "mission", "magazine", "frame", "url", "status", "in_sample",
            "orig_w", "orig_h", "saved_w", "saved_h", "bytes_downloaded"]
    with open(MANIFEST, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    n_ok = sum(1 for r in rows if r["status"] == "ok")
    n_miss = sum(1 for r in rows if r["status"] == "missing")
    n_err = sum(1 for r in rows if r["status"] == "error")
    print(f"manifest: {n_ok} ok, {n_miss} missing, {n_err} error -> {MANIFEST}", flush=True)


def main():
    global SIZE, FRAMES, LOG, MANIFEST
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", choices=["print", "browse"], default="print")
    args = ap.parse_args()
    SIZE = args.size
    if SIZE == "browse":
        FRAMES = os.path.join(DATA, "browse")
        LOG = os.path.join(DATA, "download_log_browse.jsonl")
        MANIFEST = os.path.join(DATA, "manifest_browse.csv")
    os.makedirs(FRAMES, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = UA
    done = load_done()
    t0 = time.time()
    for mission, mag, seed, in_sample in MAGAZINES:
        walk_magazine(session, mission, mag, seed, in_sample, done)
    for mission, mag, frame, in_sample in EXTRA_FRAMES:
        fetch_frame(session, mission, mag, frame, in_sample, done)
    write_manifest(done)
    print(f"total wall time {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    sys.exit(main())
