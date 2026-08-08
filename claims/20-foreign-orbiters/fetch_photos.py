#!/usr/bin/env python
"""Fetch the Apollo 15 surface photographs used for the skyline test.

Both frames are 4175 x 4175 px Project Apollo Archive scans of the original
NASA flight film (Kipp Teague / NASA JSC scans), mirrored on Wikimedia
Commons. Both were taken with the Hasselblad 500EL data camera and the
Zeiss Biogon 60 mm f/5.6 lens, and both were taken at the LM / flag area
(not at a distant geology station), which is what the horizon rendering
assumes.

  AS15-88-11866  "Jim salutes the flag" (163:59:05 GET, start of EVA-3,
                 taken a few tens of meters west of the LM).
                 Skyline: Mons Hadley Delta, to the south.
  AS15-86-11603  Jim Irwin at the Rover, end of EVA-1, taken from the LM
                 shadow just southwest of the Rover.
                 Skyline: Mons Hadley, to the northeast.

ALSJ captions (Apollo Lunar Surface Journal, Apollo 15 Image Library)
document the viewing directions quoted in README.md.

Note: upload.wikimedia.org rejects python-requests (TLS/UA fingerprinting,
HTTP 429), so this script shells out to curl.
"""
import subprocess
from pathlib import Path

PHOTOS = {
    "AS15-88-11866.jpg": ("https://upload.wikimedia.org/wikipedia/commons/"
                          "4/4e/AS15-88-11866_%2821648389932%29.jpg"),
    "AS15-86-11603.jpg": ("https://upload.wikimedia.org/wikipedia/commons/"
                          "0/0e/AS15-86-11603_%2821495828160%29.jpg"),
}

DATA_DIR = Path(__file__).resolve().parent / "data"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0 Safari/537.36 apollo-forensics/1.0")


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    for name, url in PHOTOS.items():
        dest = DATA_DIR / name
        if dest.exists() and dest.stat().st_size > 1_000_000:
            print(f"already have {name}")
            continue
        subprocess.run(
            ["curl", "-sSL", "--fail", "--max-time", "300",
             "-A", UA, url, "-o", str(dest)],
            check=True)
        print(f"fetched {name} ({dest.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
