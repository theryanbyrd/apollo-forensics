"""Trapped-particle environment along the trajectory: AE-8/AP-8.

Two engines, in order of preference:

1. 'radbelt'  - the genuine NASA package (github.com/nasa/radbelt, compiled
   Fortran): IGRF magnetic field + SHELLG McIlwain L-shell tracing + AE8/AP8.
   Runs in a separate Python (binary wheels exist for CPython <= 3.12; this
   machine has no Fortran compiler, so the analysis venv (3.13) cannot build
   it).  Point the RADBELT_PYTHON env var at a python that can
   `import radbelt` to enable.  This is the engine used for the published
   results in README.md.

2. 'port'     - pure-Python port of TRARA1/TRARA2 (aep8_port.py) reading the
   same NASA coefficient files, with tilted-dipole (L, B/B0) from DGRF-1970.
   Validated against engine 1 to <4e-6 relative error at fixed (E, L, B/B0)
   (results/port_validation.json); remaining difference between engines is
   the dipole-vs-IGRF magnetic coordinates (quantified in the README).
"""
import json
import os
import subprocess

import aep8_port

P_ENERGIES = [10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100, 120, 150, 200, 250, 300, 400]
E_ENERGIES = [0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.0]

_HELPER = r"""
import json, sys
import numpy as np
from radbelt import igrf, aep8
req = json.load(sys.stdin)
year = req["year"]
out = {"L": [], "bb0": [], "pflux": [], "eflux": []}
for lat, lon, h in req["points"]:
    L, bb0 = igrf(lon, lat, h, year)
    L, bb0 = float(L), float(bb0)
    out["L"].append(L)
    out["bb0"].append(bb0)
    out["pflux"].append([float(aep8(E, L, bb0, 'p', req["solar"])) for E in req["p_energies"]])
    out["eflux"].append([float(aep8(E, L, bb0, 'e', req["solar"])) for E in req["e_energies"]])
json.dump(out, sys.stdout)
"""


def radbelt_available():
    py = os.environ.get("RADBELT_PYTHON")
    if not py:
        return False
    try:
        r = subprocess.run([py, "-c", "import radbelt"], capture_output=True, timeout=120)
        return r.returncode == 0
    except Exception:
        return False


def sample_radbelt(points, year=1969.54, solar="max"):
    """points: list of state dicts from trajectory.sample_leg."""
    py = os.environ["RADBELT_PYTHON"]
    req = {
        "year": year, "solar": solar,
        "p_energies": P_ENERGIES, "e_energies": E_ENERGIES,
        "points": [[p["lat_geodetic_deg"], p["lon_deg"], p["height_km"]] for p in points],
    }
    r = subprocess.run([py, "-c", _HELPER], input=json.dumps(req),
                       capture_output=True, text=True, check=True, timeout=7200)
    return json.loads(r.stdout)


def sample_port(points, solar="max"):
    pmod = "ap8" + solar
    emod = "ae8" + solar
    out = {"L": [], "bb0": [], "pflux": [], "eflux": []}
    for p in points:
        L, bb0 = p["L_dipole"], p["BB0_dipole"]
        out["L"].append(L)
        out["bb0"].append(bb0)
        out["pflux"].append([aep8_port.aep8(E, L, bb0, pmod) for E in P_ENERGIES])
        out["eflux"].append([aep8_port.aep8(E, L, bb0, emod) for E in E_ENERGIES])
    return out


def sample(points, solar="max", engine=None):
    """Returns (env dict, engine_name)."""
    if engine is None:
        engine = "radbelt" if radbelt_available() else "port"
    if engine == "radbelt":
        return sample_radbelt(points, solar=solar), "radbelt (IGRF L,B/B0 + NASA Fortran AE8/AP8)"
    return sample_port(points, solar=solar), "pure-Python port (validated) + tilted-dipole L,B/B0"
