#!/usr/bin/env python
"""Fetch every input file this claim needs, from its original public source.

`data/` is git-ignored, so a fresh clone starts empty.  Running this script (or
just running `run.py`, which calls `ensure_data()` automatically) recreates it.

Seven files are required:

  ae8min.asc, ae8max.asc, ap8min.asc, ap8max.asc
      NASA/NSSDC AE-8 / AP-8 trapped-radiation model coefficient maps.
      Fetched verbatim from NASA's own repository, pinned to release v0.1.8:
      https://github.com/nasa/radbelt/tree/v0.1.8/radbelt/extern/aep8
      (NASA originally distributed them at
       https://ccmc.gsfc.nasa.gov/pub/modelweb/radiation_belt/radbelt/fortran_code/ ;
       the GitHub copy is the same bytes and is the one under version control.)
      SHA-256 is checked against the values used for the published results, so a
      silent upstream change cannot slip into the numbers unnoticed.

  pstar_aluminum.csv, pstar_water.csv, estar_aluminum.csv
      NIST PSTAR (protons) and ESTAR (electrons) stopping-power / range tables.
      Queried live from the NIST STAR CGI at physics.nist.gov with an explicit
      energy list (below), then parsed into CSV.  Nothing is hand-typed: every
      number in the CSVs is a value NIST returned for this query.
      SHA-256 of the generated CSV is compared with the file used for the
      published results; a difference is reported loudly (it would mean NIST
      revised the tables) but does not abort the run.

Usage:
    python fetch_data.py            # fetch anything missing
    python fetch_data.py --force    # re-fetch everything, even if cached
    python fetch_data.py --dest DIR # write into DIR instead of ./data
"""
import argparse
import hashlib
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

# --------------------------------------------------------------------------
# 1. AE-8 / AP-8 model coefficient files (NASA)
# --------------------------------------------------------------------------
RADBELT_TAG = "v0.1.8"
RADBELT_BASE = (f"https://raw.githubusercontent.com/nasa/radbelt/{RADBELT_TAG}"
                "/radbelt/extern/aep8")
AEP8_FILES = {
    "ae8min.asc": "4cea68a560a98e3efab4ec3b02a78a026c077453f179606a9a598698cfa34734",
    "ae8max.asc": "73cf3ad873c8adea48c27eb7628621a03937d9f6c17b55805d32692e636815e8",
    "ap8min.asc": "e381b3aaa88a120e6ee9e8cc0645d0205ca947924d2bf32e86a105044749ebf8",
    "ap8max.asc": "e21fced8e9c2e97d6bf4824173bed1af803b9f52ca261c49106b0c58e609a7de",
}

# --------------------------------------------------------------------------
# 2. NIST PSTAR / ESTAR stopping-power tables
# --------------------------------------------------------------------------
NIST_PSTAR = "https://physics.nist.gov/cgi-bin/Star/ap_table.pl"
NIST_ESTAR = "https://physics.nist.gov/cgi-bin/Star/e_table.pl"

# Proton energies: the NIST PSTAR default grid restricted to 1-500 MeV, which
# brackets everything AP-8 and the King SPE fit supply (10-400 MeV trapped,
# 10-1000 MeV event) and everything that penetrates 0.3-30 g/cm^2 of aluminum.
PSTAR_ENERGIES_MEV = [
    1, 2, 3, 4, 5, 6, 8, 10, 12.5, 15, 17.5, 20, 25, 30, 35, 40, 45, 50, 55,
    60, 65, 70, 75, 80, 85, 90, 95, 100, 110, 120, 130, 140, 150, 175, 200,
    250, 300, 350, 400, 450, 500,
]
# Electron energies: 10 per decade from 0.01 to 10 MeV (AE-8 tops out at 7 MeV).
ESTAR_ENERGIES_MEV = [10.0 ** (-2 + k / 10.0) for k in range(31)]

PSTAR_HEADER = ["T_MeV", "stop_e", "stop_n", "stop_total_MeVcm2g",
                "csda_range_gcm2", "proj_range_gcm2", "detour"]
ESTAR_HEADER = ["T_MeV", "closs", "rloss", "tloss_MeVcm2g", "delta"]

NIST_FILES = {
    # filename: (url, matno, prog, energies, header, sha256-of-published-copy)
    "pstar_aluminum.csv": (NIST_PSTAR, "013", "PSTAR", PSTAR_ENERGIES_MEV, PSTAR_HEADER,
                           "9286d487cffc78430e8bfcc0a96b2e06cff877fdbe25f500e5a74fed7ba4acb9"),
    "pstar_water.csv": (NIST_PSTAR, "276", "PSTAR", PSTAR_ENERGIES_MEV, PSTAR_HEADER,
                        "28570a40bf0f04e6458962dcc6ea49d2803a4509458f7b6ea6f2a9cc784d2b5b"),
    "estar_aluminum.csv": (NIST_ESTAR, "013", "ESTAR", ESTAR_ENERGIES_MEV, ESTAR_HEADER,
                           "9bca0d4da3559008ab247688434cee5fef93f3886ee8b9027138b6e15b4baf4e"),
}

REQUIRED = list(AEP8_FILES) + list(NIST_FILES)
UA = {"User-Agent": "apollo-forensics/claim-11 (reproduction script; python-urllib)"}


def _sha256(b):
    return hashlib.sha256(b).hexdigest()


def _get(url, timeout=180):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _post_multipart(url, fields, timeout=180):
    """POST a multipart/form-data body (the NIST STAR CGI requires it)."""
    boundary = "----apollo-forensics-boundary-8d1f2a"
    parts = []
    for k, v in fields.items():
        parts.append(f"--{boundary}\r\n"
                     f'Content-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n')
    body = ("".join(parts) + f"--{boundary}--\r\n").encode()
    req = urllib.request.Request(url, data=body, headers=dict(
        UA, **{"Content-Type": f"multipart/form-data; boundary={boundary}"}))
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


_TD = re.compile(r"<td[^>]*>\s*([-+0-9.Ee]+)\s*</td>", re.I)
_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.I | re.S)
_NUMLINE = re.compile(r"^\s*\d\.\d{3}E[+-]\d\d(?:\s+[-+0-9.Ee]+)+\s*$")


def _parse_star_table(html, ncols):
    """Extract the numeric table from a NIST STAR result page.

    Handles both output styles NIST has served: an HTML <table> of <td> cells
    (current) and a preformatted <pre> block (older).
    """
    rows = []
    for m in _ROW.finditer(html):
        cells = _TD.findall(m.group(1))
        if len(cells) == ncols:
            rows.append(cells)
    if rows:
        return rows
    text = re.sub(r"<[^>]+>", "", html.replace("<br>", "\n").replace("<BR>", "\n"))
    for line in text.split("\n"):
        if _NUMLINE.match(line):
            cells = line.split()
            if len(cells) == ncols:
                rows.append(cells)
    return rows


def fetch_nist(url, matno, prog, energies, header):
    """Query the NIST STAR CGI and return the table as CSV text."""
    # NIST's CGI parses the energy list most reliably in E-notation; plain
    # decimals with many significant digits are silently dropped by ESTAR.
    elist = "\n".join("%.3E" % e for e in energies)
    html = _post_multipart(url, {
        "prog": prog,
        "matno": matno,
        "GraphType": "None",
        "Energies": elist,
        # ShowDefault deliberately omitted (= unchecked): return exactly the
        # energies requested, so the table is byte-reproducible.
    })
    rows = _parse_star_table(html, len(header))
    if len(rows) != len(energies):
        raise RuntimeError(
            f"NIST {prog} matno={matno}: expected {len(energies)} rows, parsed "
            f"{len(rows)}. The CGI output format may have changed; inspect the "
            f"response manually at {url}")
    lines = [",".join(header)] + [",".join(r) for r in rows]
    return "\n".join(lines) + "\n"


def ensure_data(dest=None, force=False, verbose=True):
    """Make sure every required input file exists in `dest` (default ./data).

    Returns the list of files that were downloaded this call.
    """
    dest = dest or DATA
    os.makedirs(dest, exist_ok=True)
    fetched = []

    def say(*a):
        if verbose:
            print(*a, flush=True)

    missing = [n for n in REQUIRED if force or not os.path.exists(os.path.join(dest, n))]
    if not missing:
        say(f"data: all {len(REQUIRED)} input files present in {dest}")
        return fetched
    say(f"data: fetching {len(missing)} missing input file(s) into {dest}")

    for name, want in AEP8_FILES.items():
        path = os.path.join(dest, name)
        if not force and os.path.exists(path):
            continue
        url = f"{RADBELT_BASE}/{name}"
        say(f"  {name}: downloading {url}")
        blob = _get(url)
        got = _sha256(blob)
        if got != want:
            raise RuntimeError(f"{name}: SHA-256 mismatch\n  expected {want}\n  got      {got}\n"
                               f"  (source {url}) - refusing to use it")
        with open(path, "wb") as f:
            f.write(blob)
        say(f"    ok, {len(blob):,} bytes, sha256 {got[:16]}... verified")
        fetched.append(name)

    for name, (url, matno, prog, energies, header, want) in NIST_FILES.items():
        path = os.path.join(dest, name)
        if not force and os.path.exists(path):
            continue
        say(f"  {name}: querying NIST {prog} (matno={matno}, {len(energies)} energies) at {url}")
        csv_text = fetch_nist(url, matno, prog, energies, header)
        got = _sha256(csv_text.encode())
        with open(path, "w") as f:
            f.write(csv_text)
        if got == want:
            say(f"    ok, {len(energies)} rows, sha256 {got[:16]}... "
                f"identical to the table used for the published results")
        else:
            say(f"    ok, {len(energies)} rows, but sha256 {got[:16]}... != published "
                f"{want[:16]}...\n"
                f"    NIST appears to have revised this table since the published run; "
                f"results computed now may differ.")
        fetched.append(name)

    return fetched


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--force", action="store_true", help="re-fetch even if cached")
    ap.add_argument("--dest", default=None, help="destination directory (default ./data)")
    args = ap.parse_args()
    got = ensure_data(dest=args.dest, force=args.force)
    print(f"done ({len(got)} file(s) downloaded)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
