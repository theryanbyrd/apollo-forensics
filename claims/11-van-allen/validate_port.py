"""Validate the pure-Python TRARA1/TRARA2 port against the genuine NASA Fortran.

The reference is radbelt 0.1.8 (NASA's official Python wrapper, compiled Fortran
binary wheel), installed in a separate Python 3.10 venv because no wheel exists
for the analysis venv's Python 3.13 and no Fortran compiler is present.

Usage:
    python validate_port.py [path-to-radbelt-python]

Writes results/port_validation.json with max/median relative errors per model.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import aep8_port  # noqa: E402
import fetch_data  # noqa: E402

RADBELT_PY = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("RADBELT_PYTHON", "")

MODELS = {
    "ap8min": ("p", "min", [10, 20, 30, 50, 80, 100, 150, 200, 300, 400]),
    "ap8max": ("p", "max", [10, 20, 30, 50, 80, 100, 150, 200, 300, 400]),
    "ae8min": ("e", "min", [0.5, 1.0, 2.0, 3.0, 5.0, 7.0]),
    "ae8max": ("e", "max", [0.5, 1.0, 2.0, 3.0, 5.0, 7.0]),
}
LGRID = [1.1, 1.2, 1.3, 1.4, 1.5, 1.7, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 7.0, 8.0]
BGRID = [1.0, 1.1, 1.3, 1.7, 2.5, 4.0, 8.0, 20.0, 50.0]


def main():
    fetch_data.ensure_data()   # data/ is git-ignored; download the AE-8/AP-8 maps if absent
    cases = []
    for model, (particle, solar, energies) in MODELS.items():
        for L in LGRID:
            for b in BGRID:
                for E in energies:
                    cases.append((model, particle, solar, E, L, b))

    # --- reference values from the genuine Fortran, via subprocess ---
    prog = r"""
import sys, json
from radbelt import aep8
cases = json.load(sys.stdin)
out = []
for model, particle, solar, E, L, b in cases:
    out.append(float(aep8(E, L, b, particle, solar)))
json.dump(out, sys.stdout)
"""
    res = subprocess.run([RADBELT_PY, "-c", prog], input=json.dumps(cases),
                         capture_output=True, text=True, check=True)
    ref = json.loads(res.stdout)

    # --- port values ---
    port = [aep8_port.aep8(E, L, b, model) for (model, particle, solar, E, L, b) in cases]

    stats = {}
    worst = None
    nonzero = 0
    exact_zero_match = 0
    mismatched_zero = 0
    rel_errs = []
    for (case, r, p) in zip(cases, ref, port):
        if r == 0.0 and p == 0.0:
            exact_zero_match += 1
            continue
        if r == 0.0 or p == 0.0:
            mismatched_zero += 1
            if worst is None:
                worst = {"case": case, "fortran": r, "port": p}
            continue
        nonzero += 1
        e = abs(p - r) / r
        rel_errs.append(e)
        if worst is None or e > worst.get("rel_err", -1):
            worst = {"case": case, "fortran": r, "port": p, "rel_err": e}
    rel_errs.sort()
    stats = {
        "n_cases": len(cases),
        "n_both_zero": exact_zero_match,
        "n_zero_mismatch": mismatched_zero,
        "n_nonzero_compared": nonzero,
        "max_rel_err": rel_errs[-1] if rel_errs else None,
        "median_rel_err": rel_errs[len(rel_errs) // 2] if rel_errs else None,
        "worst_case": worst,
        "reference": "radbelt 0.1.8 compiled Fortran wheel (github.com/nasa/radbelt)",
    }
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    with open(os.path.join(HERE, "results", "port_validation.json"), "w") as f:
        json.dump(stats, f, indent=2)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
