#!/usr/bin/env python
"""Fetch JAXA Kaguya/SELENE Terrain Camera seamless DTM tiles covering the
Apollo 15 landing site (Hadley-Apennine, 26.1322 N, 3.6339 E).

Product: SLN-L-TC-5-DTM-MAP-SEAMLESS-V2.0 (JAXA DARTS archive, PDS3).
Each tile is 3 deg x 3 deg, 10800 x 10800 int16 (MSB), 3600 px/deg
(~8.4 m/px), simple cylindrical projection, elevation in meters relative to
the 1737.4 km sphere. DUMMY = -9999.

We need terrain out to 40 km from the LM in every azimuth:
  lat 26.1322 +/- 1.32 deg  -> 24.81 .. 27.45 N
  lon 3.6339 +/- 1.47 deg   -> 2.16 .. 5.10 E
which spans four tiles (the DARTS server does not honor HTTP Range
requests, so full tiles are downloaded):

  DTM_MAPs02_N27E003N24E006SC  (main: contains LM, Mons Hadley,
                                Mons Hadley Delta)
  DTM_MAPs02_N27E000N24E003SC  (west)
  DTM_MAPs02_N30E003N27E006SC  (north)
  DTM_MAPs02_N30E000N27E003SC  (northwest)

Usage: python fetch_dem.py [tile-substring ...]
With no args, fetches all four tiles (+ labels). ~933 MB total.
"""
import sys
from pathlib import Path

import requests
from tqdm import tqdm

BASE = ("https://data.darts.isas.jaxa.jp/pub/pds3/"
        "sln-l-tc-5-dtm-map-seamless-v2.0")

TILES = [
    ("lon003", "DTM_MAPs02_N27E003N24E006SC"),
    ("lon000", "DTM_MAPs02_N27E000N24E003SC"),
    ("lon003", "DTM_MAPs02_N30E003N27E006SC"),
    ("lon000", "DTM_MAPs02_N30E000N27E003SC"),
]

DATA_DIR = Path(__file__).resolve().parent / "data"

EXPECTED_IMG_BYTES = 10800 * 10800 * 2  # 233,280,000


def fetch(url: str, dest: Path, expected: int | None = None) -> None:
    if dest.exists() and (expected is None or dest.stat().st_size == expected):
        print(f"already have {dest.name}")
        return
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0)) or None
        with open(tmp, "wb") as f, tqdm(total=total, unit="B",
                                        unit_scale=True,
                                        desc=dest.name) as bar:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
                bar.update(len(chunk))
    if expected is not None and tmp.stat().st_size != expected:
        raise RuntimeError(
            f"{dest.name}: got {tmp.stat().st_size} bytes, "
            f"expected {expected}")
    tmp.rename(dest)
    print(f"fetched {dest.name}")


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    wanted = sys.argv[1:]
    for londir, tile in TILES:
        # match on the tile's NW-corner name only: tile IDs contain BOTH
        # corner coordinates (e.g. ...N30E000N27E003SC), so a plain
        # substring test would match two different tiles.
        nw = tile.removeprefix("DTM_MAPs02_")
        if wanted and not any(nw.startswith(w) for w in wanted):
            continue
        for ext, expected in ((".lbl", None), (".img", EXPECTED_IMG_BYTES)):
            url = f"{BASE}/{londir}/data/{tile}{ext}"
            fetch(url, DATA_DIR / f"{tile}{ext}", expected)


if __name__ == "__main__":
    main()
