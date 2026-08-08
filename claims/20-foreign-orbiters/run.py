#!/usr/bin/env python
"""Reproduce claim 20 end-to-end.

  1. fetch_dem.py      - download 4 JAXA Kaguya TC DTM tiles (~933 MB)
  2. fetch_photos.py   - download 2 Apollo 15 film scans (~14 MB)
  3. render_horizon.py - 360-deg synthetic horizon from the LM site
  4. extract_skyline.py- skyline curves from the photographs
  5. match_skyline.py  - camera-pose fit photo vs DEM + figures + JSON

Run with the repo venv:  ../../.venv/bin/python run.py
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

for step in ["fetch_dem.py", "fetch_photos.py", "render_horizon.py",
             "extract_skyline.py", "match_skyline.py"]:
    print(f"\n=== {step} ===")
    subprocess.run([sys.executable, str(HERE / step)], check=True)
