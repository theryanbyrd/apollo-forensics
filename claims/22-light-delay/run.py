#!/usr/bin/env python
"""Run the full claim-22 pipeline: ephemeris -> audio -> measurements -> plots.

Steps (each cached; delete data/ or results/*.json to redo):
  1. fetch_ephemeris.py    JPL Horizons light-time curve for the mission window
  2. fetch_audio.py        NASA JSC mission tapes from archive.org (~490 MB)
  3. measure_delay.py      echo cross-correlation per tape
  4. turn_taking.py        conversational-gap asymmetry across all tapes
  5. plot_results.py       assembles results/*.png
  6. summary               writes results/summary.json
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable

TAPES = {  # tape -> GET (MET) at tape start per NASA JSC catalog
    "173-AAA.mp3": "102:12",
    "174-AAA.mp3": "106:17",
    "175-AAA.mp3": "109:21",
}


def run(*args):
    print("+", " ".join(args))
    subprocess.check_call([PY] + list(args), cwd=HERE)


def main():
    run("fetch_ephemeris.py")
    run("fetch_audio.py")
    for tape, met in TAPES.items():
        label = os.path.splitext(tape)[0]
        out = os.path.join(HERE, "results", f"echo_{label}.json")
        if not os.path.exists(out):
            run("measure_delay.py", os.path.join("data", tape), "--met-start", met)
    if not os.path.exists(os.path.join(HERE, "results", "turn_taking.json")):
        run("turn_taking.py", *[os.path.join("data", t) for t in TAPES])
    run("plot_results.py")
    run("plot_example.py")
    run("make_summary.py")


if __name__ == "__main__":
    main()
