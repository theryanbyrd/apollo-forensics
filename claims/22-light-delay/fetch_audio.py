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
is gitignored); re-running skips completed downloads.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)

ITEM = "https://archive.org/download/Apollo11Audio"
FILES = ["173-AAA.mp3", "174-AAA.mp3", "175-AAA.mp3"]


def main():
    for name in FILES:
        dest = os.path.join(DATA, name)
        url = f"{ITEM}/{name}"
        print(f"{name}: ", end="", flush=True)
        if os.path.exists(dest) and os.path.getsize(dest) > 50e6:
            print("cached")
            continue
        print(f"downloading {url}")
        subprocess.check_call(["curl", "-sL", "-C", "-", "-o", dest, url])
    print("done")


if __name__ == "__main__":
    sys.exit(main())
