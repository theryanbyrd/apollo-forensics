#!/usr/bin/env python
"""Download Apollo 11 mission audio tapes used by this analysis.

Source: archive.org item "Apollo11Audio" -- "Digitized, cataloged and archived
by the Houston Audio Control Room, at the NASA Johnson Space Center."
https://archive.org/details/Apollo11Audio

Tapes used (NASA JSC PAO "Mission Commentary" reels; the public-affairs release
loop carried the live air-to-ground feed as received in Houston, plus the PAO
announcer).  Per the item's catalog file
NASA-Audio-Archive_Digital-Audio-File_Metadata (OCR text in the same item):

  173-AAA  1969-07-20  Mission Commentary 304-322, MET(GET) start 102:12
           -> contains the lunar landing (Eagle has landed, GET 102:45:58)
  174-AAA  1969-07-20  Mission Commentary 323-339, MET start 106:17
           -> contains beginning of EVA (hatch open GET 109:07)
  175-AAA  1969-07-21  Mission Commentary 339-352 (EVA; catalog cites content
           "@109:39") -> bulk of the EVA incl. the Nixon call

Each file is ~2-3 h of audio, 100-180 MB as MP3.  Files land in data/ (which
is gitignored).

Integrity: every measurement in this claim is timed against these bytes, and a
partial download is worse than no download -- a fragment still decodes, just to
the wrong length, which silently shifts tape timing, the interpolated Horizons
round-trip prediction and the utterance census.  So a tape is only accepted
when its size AND md5 match the archive.org catalog and it decodes to the
expected duration; downloads are staged in a .part file, resumed if partial,
and renamed into place only after they verify.

Usage: python fetch_audio.py [--verify-only]
"""
import argparse
import glob
import hashlib
import json
import os
import subprocess
import sys
import urllib.request

import soundfile as sf

import audio_utils as au

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)

ITEM = "https://archive.org/download/Apollo11Audio"
METADATA = "https://archive.org/metadata/Apollo11Audio"

# size and md5 come from the archive.org metadata API for item Apollo11Audio
# (the derivatives are dated 2011-02-05 and have not changed since); duration_s
# is the length of the 11025 Hz mono decode of the verified file, i.e. exactly
# the duration_s the measurement scripts work from.
FILES = {
    "173-AAA.mp3": (183309042, "607838a60b6b99236d6afcd7cd44c94a", 11456.606),
    "174-AAA.mp3": (178819324, "281eef3708120c8fbc3893de9bebf07c", 10983.002),
    "175-AAA.mp3": (129243931, "ef315a4d9e727687ea1b1b8961d62fcc",  8077.540),
}
DURATION_TOL_S = 1.0      # md5 already pins the bytes; this catches a bad decoder
CONNECT_TIMEOUT = 30
MAX_TIME = 3600           # per attempt; a .part file is kept and resumed next run
MIN_SPEED = 10240         # abort a transfer stalled below 10 kB/s ...
MIN_SPEED_TIME = 60       # ... for this many seconds


def md5sum(path, blocksize=1 << 22):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(blocksize), b""):
            h.update(block)
    return h.hexdigest()


def verify_bytes(path, size, md5):
    """(ok, reason) -- does `path` hold exactly the catalogued tape?"""
    n = os.path.getsize(path)
    if n != size:
        return False, (f"{n:,} bytes, expected {size:,} "
                       f"({'incomplete' if n < size else 'oversized'}, "
                       f"{abs(n - size):,} bytes {'short' if n < size else 'extra'})")
    got = md5sum(path)
    if got != md5:
        return False, f"md5 {got} != catalogued {md5}"
    return True, f"{n:,} bytes, md5 ok"


def verify_duration(path, expected):
    """(ok, reason) -- does the tape decode to the expected length?"""
    info = sf.info(au.ensure_wav(path))
    dur = info.frames / info.samplerate
    if abs(dur - expected) > DURATION_TOL_S:
        return False, f"decodes to {dur:.3f} s, expected {expected:.3f} s"
    return True, f"decodes to {dur:.3f} s"


def drop_stale_decodes(mp3_path):
    """Remove cached WAV decodes of a tape we are about to replace."""
    for w in glob.glob(os.path.splitext(mp3_path)[0] + "_*.wav"):
        os.remove(w)
        print(f"    dropped stale decode {os.path.basename(w)}")


def cross_check_catalog():
    """Warn if archive.org's item metadata no longer matches the table above."""
    try:
        with urllib.request.urlopen(METADATA, timeout=CONNECT_TIMEOUT) as r:
            remote = {f["name"]: f for f in json.load(r).get("files", [])}
    except Exception as e:                       # offline is not fatal
        print(f"  (could not read {METADATA}: {e}; using recorded sizes/md5s)")
        return
    for name, (size, md5, _) in FILES.items():
        f = remote.get(name)
        if f is None or int(f.get("size", -1)) != size or f.get("md5") != md5:
            print(f"  WARNING: archive.org's copy of {name} no longer matches the "
                  f"recorded catalog entry ({f.get('size') if f else 'absent'}/"
                  f"{f.get('md5') if f else '-'} vs {size}/{md5}).  The published "
                  f"results were computed from the recorded bytes.")


def download(url, part, resume):
    cmd = ["curl", "-L", "--fail", "--silent", "--show-error",
           "--connect-timeout", str(CONNECT_TIMEOUT),
           "--max-time", str(MAX_TIME),
           "--speed-limit", str(MIN_SPEED), "--speed-time", str(MIN_SPEED_TIME),
           "--retry", "3", "--retry-delay", "5",
           "-o", part, url]
    if resume:
        cmd[1:1] = ["-C", "-"]          # continue a .part file where it stopped
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        got = os.path.getsize(part) if os.path.exists(part) else 0
        raise SystemExit(
            f"curl failed (exit {e.returncode}) after {got:,} bytes of {url}. "
            f"The partial file is kept; re-run to resume.") from None


_catalog_checked = False


def acquire(name, size, md5, duration, verify_only=False):
    global _catalog_checked
    dest = os.path.join(DATA, name)
    part = dest + ".part"
    resume = False

    if os.path.exists(dest):
        ok, why = verify_bytes(dest, size, md5)
        if ok:
            ok, why = verify_duration(dest, duration)
            if ok:
                print(f"cached ({why})")
                return
        print(f"cached copy REJECTED: {why}")
    if verify_only:                     # report only; touch nothing
        print("    (--verify-only: not downloading)")
        return

    if (os.path.exists(dest) and os.path.getsize(dest) < size
            and not os.path.exists(part)):
        # older versions of this script wrote straight to dest, so a short file
        # here is a partial download: resume it instead of starting over
        os.replace(dest, part)
        resume = True
        print("    treating as a partial download and resuming")
    if os.path.exists(part):
        if os.path.getsize(part) < size:
            resume = True
        else:
            os.remove(part)             # oversized/corrupt: start clean
            resume = False
    if not _catalog_checked:
        _catalog_checked = True
        cross_check_catalog()

    url = f"{ITEM}/{name}"
    for attempt in (1, 2):
        at = f" (resuming at {os.path.getsize(part):,} bytes)" if resume else ""
        print(f"    downloading {url}{at}")
        download(url, part, resume)
        ok, why = verify_bytes(part, size, md5)
        if ok:
            break
        print(f"    download REJECTED: {why}")
        os.remove(part)                 # do not keep bytes we cannot trust
        if attempt == 2:
            raise SystemExit(f"{name}: download failed verification twice")
        resume = False                  # second try: fetch the whole file again
    drop_stale_decodes(dest)
    os.replace(part, dest)              # only verified bytes ever reach dest
    ok, why = verify_duration(dest, duration)
    if not ok:
        raise SystemExit(f"{name}: bytes verify but {why}")
    print(f"    ok: {why}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify-only", action="store_true",
                    help="check the cached tapes and report, but download nothing")
    args = ap.parse_args()
    for name, (size, md5, duration) in FILES.items():
        print(f"{name}: ", end="", flush=True)
        acquire(name, size, md5, duration, verify_only=args.verify_only)
    print("done")


if __name__ == "__main__":
    sys.exit(main())
