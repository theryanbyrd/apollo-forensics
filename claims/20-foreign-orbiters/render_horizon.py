#!/usr/bin/env python
"""Render the 360-degree horizon visible from the Apollo 15 LM site using
only JAXA Kaguya/SELENE Terrain Camera DTM tiles (SLN-L-TC-5-DTM-MAP-
SEAMLESS-V2.0, ~8.4 m/px, elevations in meters w.r.t. the 1737.4 km
sphere).

Method: from the camera position (LM coordinates, 1.6 m above the local
DEM surface) sweep azimuth 0..360 deg. Along each azimuth, march outward
and compute the elevation angle of every DEM sample, subtracting the
curvature drop d^2/2R for the spherical Moon (no atmospheric refraction —
there is no atmosphere). The horizon at that azimuth is the maximum
elevation angle encountered.

Outputs (in results/):
  horizon.npz          az (deg), elev (deg), dist (m), hpt_lat, hpt_lon
  dem_hillshade.png    shaded relief of the DEM with the LM marked
  synthetic_horizon.png  the 360-deg panorama profile
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
RESULTS = HERE / "results"

# --- Apollo 15 LM (Falcon) planetocentric coordinates -----------------------
LM_LAT = 26.1322
LM_LON = 3.6339
CAMERA_HEIGHT = 1.6          # m above local terrain (chest-mounted Hasselblad)
R_MOON = 1_737_400.0         # m, sphere used by the Kaguya DTM

# --- DEM grid: global simple-cylindrical mosaic of the four tiles -----------
# Grid: 3600 px/deg. Tile row 0 center is exactly at its UPPER_LEFT_LATITUDE,
# col 0 center exactly at UPPER_LEFT_LONGITUDE (verified against the .lbl:
# N27E003 tile spans lat 27.000000 .. 24.000278, lon 3.000000 .. 5.999722,
# 10800 x 10800 -> 1/3600 deg per px, pixel centers on the 1/3600 grid).
PPD = 3600
TILES = [
    # (filename, upper-left lat, upper-left lon)
    ("DTM_MAPs02_N30E000N27E003SC.img", 30.0, 0.0),
    ("DTM_MAPs02_N30E003N27E006SC.img", 30.0, 3.0),
    ("DTM_MAPs02_N27E000N24E003SC.img", 27.0, 0.0),
    ("DTM_MAPs02_N27E003N24E006SC.img", 27.0, 3.0),
]
N = 10800
DUMMY = -9999

# Mosaic crop (covers 40 km around the LM with margin)
LAT_MAX, LAT_MIN = 27.65, 24.60
LON_MIN, LON_MAX = 1.90, 5.45

MAX_RANGE = 40_000.0   # m
MIN_RANGE = 8.0        # m
RANGE_STEP = 8.0       # m (matches DEM resolution)
AZ_STEP = 0.05         # deg


def load_mosaic():
    """Assemble the cropped int16 mosaic. Returns (dem, lat0, lon0) where
    dem[0,0] is the pixel whose center is at (lat0, lon0)."""
    # global pixel indices: row = (30 - lat) * PPD, col = (lon - 0) * PPD
    r0 = int(round((30.0 - LAT_MAX) * PPD))
    r1 = int(round((30.0 - LAT_MIN) * PPD))
    c0 = int(round(LON_MIN * PPD))
    c1 = int(round(LON_MAX * PPD))
    dem = np.full((r1 - r0, c1 - c0), DUMMY, dtype=np.int16)
    for fname, ul_lat, ul_lon in TILES:
        path = DATA / fname
        if not path.exists():
            print(f"WARNING: missing tile {fname}; leaving gap")
            continue
        tile = np.memmap(path, dtype=">i2", mode="r", shape=(N, N))
        tr0 = int(round((30.0 - ul_lat) * PPD))   # tile's global first row
        tc0 = int(round(ul_lon * PPD))
        # overlap between [tr0, tr0+N) and [r0, r1)
        rr0, rr1 = max(tr0, r0), min(tr0 + N, r1)
        cc0, cc1 = max(tc0, c0), min(tc0 + N, c1)
        if rr0 >= rr1 or cc0 >= cc1:
            continue
        dem[rr0 - r0:rr1 - r0, cc0 - c0:cc1 - c0] = \
            tile[rr0 - tr0:rr1 - tr0, cc0 - tc0:cc1 - tc0]
        del tile
    lat0 = 30.0 - r0 / PPD
    lon0 = c0 / PPD
    return dem, lat0, lon0


def bilinear(dem, lat0, lon0, lat, lon):
    """Bilinear sample of the mosaic at (lat, lon) arrays. Returns float32
    elevations; NaN where any contributing pixel is DUMMY/outside."""
    rf = (lat0 - lat) * PPD
    cf = (lon - lon0) * PPD
    r = np.floor(rf).astype(np.int64)
    c = np.floor(cf).astype(np.int64)
    fr = (rf - r).astype(np.float32)
    fc = (cf - c).astype(np.float32)
    H, W = dem.shape
    valid = (r >= 0) & (r < H - 1) & (c >= 0) & (c < W - 1)
    r = np.clip(r, 0, H - 2)
    c = np.clip(c, 0, W - 2)
    p00 = dem[r, c].astype(np.float32)
    p01 = dem[r, c + 1].astype(np.float32)
    p10 = dem[r + 1, c].astype(np.float32)
    p11 = dem[r + 1, c + 1].astype(np.float32)
    bad = (p00 == DUMMY) | (p01 == DUMMY) | (p10 == DUMMY) | (p11 == DUMMY)
    z = (p00 * (1 - fr) * (1 - fc) + p01 * (1 - fr) * fc +
         p10 * fr * (1 - fc) + p11 * fr * fc)
    z[~valid | bad] = np.nan
    return z


def render(dem, lat0, lon0):
    """Sweep the full azimuth circle; return horizon arrays."""
    m_per_deg = R_MOON * np.pi / 180.0            # 30323 m/deg of latitude
    coslat = np.cos(np.radians(LM_LAT))

    z_lm = bilinear(dem, lat0, lon0,
                    np.array([LM_LAT]), np.array([LM_LON]))[0]
    z_cam = z_lm + CAMERA_HEIGHT
    print(f"DEM elevation at LM site: {z_lm:.1f} m "
          f"(w.r.t. 1737.4 km sphere); camera at {z_cam:.1f} m")

    az = np.arange(0.0, 360.0, AZ_STEP)
    d = np.arange(MIN_RANGE, MAX_RANGE + RANGE_STEP, RANGE_STEP,
                  dtype=np.float64)
    horizon = np.empty(az.size, dtype=np.float64)
    hdist = np.empty(az.size, dtype=np.float64)
    hlat = np.empty(az.size, dtype=np.float64)
    hlon = np.empty(az.size, dtype=np.float64)

    drop = d * d / (2.0 * R_MOON)                 # spherical curvature drop
    chunk = 32
    for i0 in range(0, az.size, chunk):
        a = np.radians(az[i0:i0 + chunk])[:, None]
        north = d[None, :] * np.cos(a)            # m
        east = d[None, :] * np.sin(a)
        lat = LM_LAT + north / m_per_deg
        lon = LM_LON + east / (m_per_deg * coslat)
        z = bilinear(dem, lat0, lon0, lat, lon)
        elev = np.degrees(np.arctan2(z - z_cam - drop[None, :], d[None, :]))
        elev = np.where(np.isnan(elev), -90.0, elev)
        k = np.nanargmax(elev, axis=1)
        rows = np.arange(elev.shape[0])
        horizon[i0:i0 + chunk] = elev[rows, k]
        hdist[i0:i0 + chunk] = d[k]
        hlat[i0:i0 + chunk] = lat[rows, k]
        hlon[i0:i0 + chunk] = lon[rows, k]
    return az, horizon, hdist, hlat, hlon, z_lm


def plot_hillshade(dem, lat0, lon0, hlat, hlon):
    """Shaded relief with the LM and the horizon trace marked."""
    # Downsample x4 for the plot
    d = dem[::4, ::4].astype(np.float32)
    d[d == DUMMY] = np.nan
    gy, gx = np.gradient(d, 8.43 * 4)             # m/m
    # Sun from the east (az 90 deg, alt 25 deg) like the Apollo 15 morning
    saz, salt = np.radians(90.0), np.radians(25.0)
    sx = np.cos(salt) * np.sin(saz)
    sy = np.cos(salt) * np.cos(saz)
    sz = np.sin(salt)
    norm = np.sqrt(gx * gx + gy * gy + 1)
    shade = (-gx * sx + gy * sy + sz) / norm
    shade = np.clip(shade, 0, 1)

    H, W = d.shape
    ext = [lon0, lon0 + W * 4 / PPD, lat0 - H * 4 / PPD, lat0]
    fig, ax = plt.subplots(figsize=(11, 9))
    ax.imshow(shade, cmap="gray", extent=ext, aspect=1.0 / np.cos(
        np.radians(LM_LAT)))
    ax.plot(hlon[::20], hlat[::20], ".", color="cyan", ms=1.5,
            label="rendered horizon points")
    ax.plot(LM_LON, LM_LAT, "*", color="red", ms=16, mec="white",
            label="Apollo 15 LM (26.1322 N, 3.6339 E)")
    ax.annotate("Mons Hadley", xy=(4.12, 26.69), color="yellow",
                fontsize=11, ha="center")
    ax.annotate("Mons Hadley Delta", xy=(3.71, 25.72), color="yellow",
                fontsize=11, ha="center")
    ax.set_xlabel("Longitude (deg E)")
    ax.set_ylabel("Latitude (deg N)")
    ax.set_title("JAXA Kaguya TC DTM (SLN-L-TC-5-DTM-MAP-SEAMLESS-V2.0) - "
                 "Hadley-Apennine\nhillshade with rendered horizon points")
    ax.legend(loc="lower left")
    fig.tight_layout()
    fig.savefig(RESULTS / "dem_hillshade.png", dpi=150)
    plt.close(fig)


def plot_panorama(az, horizon, hdist):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 7), sharex=True,
                                   height_ratios=[2, 1])
    ax1.fill_between(az, horizon, -1.0, color="0.35")
    ax1.plot(az, horizon, color="k", lw=0.8)
    ax1.set_ylabel("horizon elevation (deg)")
    ax1.set_ylim(-1, max(6.5, horizon.max() + 0.5))
    ax1.set_title("Synthetic 360-deg horizon from the Apollo 15 LM site\n"
                  "(JAXA Kaguya/SELENE Terrain Camera DTM, camera 1.6 m "
                  "above surface, spherical Moon R=1737.4 km)")
    for a, name in [(41.8, "Mons Hadley"), (168.6, "Mons Hadley Delta"),
                    (263.0, "Hadley Rille / west rim"),
                    (110.0, "Silver Spur / Apennine front")]:
        ax1.axvline(a, color="orange", lw=0.6, ls="--")
        ax1.text(a, ax1.get_ylim()[1] * 0.95, name, rotation=90,
                 va="top", ha="right", fontsize=8, color="orange")
    ax2.plot(az, hdist / 1000.0, color="steelblue", lw=0.8)
    ax2.set_ylabel("horizon distance (km)")
    ax2.set_xlabel("azimuth (deg, 0 = North, 90 = East)")
    ax2.set_xlim(0, 360)
    fig.tight_layout()
    fig.savefig(RESULTS / "synthetic_horizon.png", dpi=150)
    plt.close(fig)


def main():
    RESULTS.mkdir(exist_ok=True)
    dem, lat0, lon0 = load_mosaic()
    print(f"mosaic {dem.shape}, upper-left pixel center at "
          f"({lat0:.6f} N, {lon0:.6f} E)")
    az, horizon, hdist, hlat, hlon, z_lm = render(dem, lat0, lon0)
    np.savez_compressed(RESULTS / "horizon.npz", az=az, elev=horizon,
                        dist=hdist, hlat=hlat, hlon=hlon, z_lm=z_lm,
                        lm_lat=LM_LAT, lm_lon=LM_LON,
                        camera_height=CAMERA_HEIGHT, max_range=MAX_RANGE)
    print(f"horizon: min {horizon.min():.2f} deg, max {horizon.max():.2f} "
          f"deg at az {az[np.argmax(horizon)]:.1f}")
    plot_hillshade(dem, lat0, lon0, hlat, hlon)
    plot_panorama(az, horizon, hdist)
    print("wrote results/horizon.npz, dem_hillshade.png, "
          "synthetic_horizon.png")


if __name__ == "__main__":
    main()
