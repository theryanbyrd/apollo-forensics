#!/usr/bin/env python
"""Fetch Earth-Moon light-time across the Apollo 11 mission window from JPL Horizons.

Queries the public JPL Horizons API (no auth) for the Moon (COMMAND='301') as seen
from Earth, hourly, 1969-07-16 00:00 to 1969-07-24 18:00 UTC (launch to splashdown).
QUANTITIES='20,21' gives observer range/range-rate and one-way down-leg light time.

Outputs:
  data/horizons_moon_1969.txt      raw API response (cached; delete to re-fetch)
  data/horizons_rtt.csv            parsed table: utc, range_km, one_way_lt_s, rtt_s
  results/rtt_curve.png            round-trip light time vs date

Two observer geometries are fetched:
  geocentric (CENTER='500@399')            -- Earth center to Moon center
  topocentric MSC Houston (coord@399)      -- ground-station-height sanity band
"""
import io
import os
import sys

import numpy as np
import pandas as pd
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
RESULTS = os.path.join(HERE, "results")
os.makedirs(DATA, exist_ok=True)
os.makedirs(RESULTS, exist_ok=True)

API = "https://ssd.jpl.nasa.gov/api/horizons.api"

C_KM_S = 299_792.458
MOON_RADIUS_KM = 1737.4  # nearside surface is ~1 lunar radius closer than Moon center

# Mission events (UTC) for annotation.  Times from the NASA Apollo 11 mission
# report / press kit (well-established public record).
EVENTS = {
    "Launch": "1969-07-16 13:32:00",
    "Lunar orbit insertion": "1969-07-19 17:21:50",
    "Landing (Eagle)": "1969-07-20 20:17:40",
    "EVA start": "1969-07-21 02:39:33",
    "LM liftoff": "1969-07-21 17:54:00",
    "Trans-Earth injection": "1969-07-22 04:55:42",
    "Splashdown": "1969-07-24 16:50:35",
}


def query_horizons(center, cache_name, site_coord=None):
    cache = os.path.join(DATA, cache_name)
    if os.path.exists(cache):
        with open(cache) as f:
            return f.read()
    params = {
        "format": "text",
        "COMMAND": "'301'",
        "OBJ_DATA": "'NO'",
        "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'OBSERVER'",
        "CENTER": f"'{center}'",
        "START_TIME": "'1969-07-16 00:00'",
        "STOP_TIME": "'1969-07-24 18:00'",
        "STEP_SIZE": "'1 h'",
        "QUANTITIES": "'20,21'",
        "CSV_FORMAT": "'YES'",
    }
    if site_coord:
        params["COORD_TYPE"] = "'GEODETIC'"
        params["SITE_COORD"] = f"'{site_coord}'"
    r = requests.get(API, params=params, timeout=60)
    r.raise_for_status()
    with open(cache, "w") as f:
        f.write(r.text)
    return r.text


def parse(text):
    """Parse the CSV block between $$SOE and $$EOE."""
    lines = text.splitlines()
    i0 = lines.index("$$SOE") + 1
    i1 = lines.index("$$EOE")
    body = "\n".join(lines[i0:i1])
    # columns: date, [flags], delta (au), deldot (km/s), 1-way LT (minutes),
    cols = ["utc", "f1", "f2", "delta_au", "deldot_kms", "lt_min", "trail"]
    df = pd.read_csv(io.StringIO(body), header=None, names=cols, usecols=range(7))
    df["utc"] = pd.to_datetime(df["utc"].str.strip(), format="%Y-%b-%d %H:%M")
    df["range_km"] = df["delta_au"].astype(float) * 149_597_870.7
    df["one_way_lt_s"] = df["lt_min"].astype(float) * 60.0
    df["rtt_s"] = 2.0 * df["one_way_lt_s"]
    return df[["utc", "range_km", "one_way_lt_s", "rtt_s"]]


def main():
    print("Querying JPL Horizons (geocentric)...")
    geo_text = query_horizons("500@399", "horizons_moon_1969_geocentric.txt")
    geo = parse(geo_text)

    print("Querying JPL Horizons (topocentric, MSC Houston 95.09W 29.55N)...")
    # SITE_COORD = E-long(deg), lat(deg), alt(km); Houston is 95.09 W
    hou_text = query_horizons(
        "coord@399", "horizons_moon_1969_houston.txt", site_coord="264.91,29.55,0.02"
    )
    hou = parse(hou_text)

    geo.to_csv(os.path.join(DATA, "horizons_rtt.csv"), index=False)

    # Surface-to-surface correction: Houston topocenter to lunar *surface*
    # (nearside), i.e. subtract one lunar radius from the topocentric range.
    hou_surf_rtt = 2.0 * (hou["range_km"] - MOON_RADIUS_KM) / C_KM_S

    print(f"Geocentric RTT range over window: "
          f"{geo['rtt_s'].min():.4f} .. {geo['rtt_s'].max():.4f} s")
    print(f"Houston->lunar-surface RTT range: "
          f"{hou_surf_rtt.min():.4f} .. {hou_surf_rtt.max():.4f} s")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.plot(geo["utc"], geo["rtt_s"], color="#1f77b4", lw=2,
            label="Geocentric RTT (2 x one-way light time, JPL Horizons)")
    ax.plot(hou["utc"], hou_surf_rtt, color="#d62728", lw=1, alpha=0.8,
            label="Houston ground station -> lunar surface RTT")
    for name, t in EVENTS.items():
        t = pd.Timestamp(t)
        ax.axvline(t, color="gray", lw=0.7, ls=":")
        ax.annotate(name, (t, ax.get_ylim()[0]), xytext=(3, 5),
                    textcoords="offset points", rotation=90, fontsize=7,
                    va="bottom", color="dimgray")
    ax.set_ylabel("Round-trip radio delay (s)")
    ax.set_xlabel("1969 UTC")
    ax.set_title("Earth-Moon round-trip light time, Apollo 11 mission window\n"
                 "(the delay any hoax audio would have to reproduce, continuously, "
                 "for 195 hours)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.grid(alpha=0.3)
    ax.legend(loc="lower right", fontsize=9)
    fig.tight_layout()
    out = os.path.join(RESULTS, "rtt_curve.png")
    fig.savefig(out, dpi=150)
    print(f"Wrote {out}")

    # values at key events, for later overlay with measured delays
    def epoch_s(ts):
        return (ts - pd.Timestamp("1969-01-01")) / pd.Timedelta("1s")

    ev = []
    for name, t in EVENTS.items():
        t = pd.Timestamp(t)
        r_geo = np.interp(epoch_s(t), epoch_s(geo["utc"]), geo["rtt_s"])
        r_hou = np.interp(epoch_s(t), epoch_s(hou["utc"]), hou_surf_rtt)
        ev.append((name, str(t), r_geo, r_hou))
        print(f"  {name:26s} {t}  RTT_geo={r_geo:.3f} s  RTT_hou_surface={r_hou:.3f} s")
    pd.DataFrame(ev, columns=["event", "utc", "rtt_geo_s", "rtt_houston_surface_s"]) \
        .to_csv(os.path.join(DATA, "rtt_at_events.csv"), index=False)


if __name__ == "__main__":
    sys.exit(main())
