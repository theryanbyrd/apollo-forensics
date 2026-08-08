"""Apollo 11 translunar trajectory through the Van Allen belts.

Outbound leg: the actual post-TLI osculating conic from the AS-506 Postflight
Trajectory (NASA MSC, 1969; state vector at translunar injection, GET 02:50:23):

    r        = 6711.964 km          (geocentric radius)
    v        = 10.8343  km/s        (space-fixed)
    lat      = +9.9204 deg          (geocentric)
    lon      = -164.8373 deg        (east longitude; over the central Pacific)
    a        = 286545  km           (semi-major axis)
    e        = 0.976966
    i        = 31.383 deg           (to Earth's equator)
    arg. perigee = 4.410 deg,  true anomaly = 14.909 deg

(Values as tabulated from the AS-506 Postflight Trajectory report; the same
elements are re-derived independently at https://oikofuge.com/converting-apollo-state-vectors-to-orbits/ .)

The ascending node in a Greenwich-referenced inertial frame is reconstructed
here by requiring the conic to pass over the documented sub-TLI point
(lat 9.9204 N, lon -164.8373 E) at the TLI epoch 1969-07-16 16:22:23 UTC
(launch 13:32:00 UTC + GET 02:50:23).  Self-consistency check:
sin(lat) = sin(i) sin(omega+nu) reproduces the documented latitude to 4 d.p.

Return leg: modeled as the inbound branch of the same conic, anchored to the
actual entry-interface time 1969-07-24 16:35 UTC (GET 195:03).  The actual
transearth conic differed modestly (TEI targeting); this approximation is noted
in the README and its effect probed via the worst-case scenario.

Magnetic coordinates: tilted centered dipole from the DGRF-1970 degree-1
coefficients (IGRF-13): g10 = -30220 nT, g11 = -2068 nT, h11 = 5737 nT
=> dipole axis at 78.65 N, 289.85 E geographic, tilt 11.35 deg.
L = (r/Re)/cos^2(maglat), B/B0 = sqrt(1+3 sin^2 maglat)/cos^6 maglat  (dipole).
When the genuine radbelt package is available, IGRF + SHELLG McIlwain L is used
instead (see environment.py); the dipole is the documented fallback.
"""
import math
from datetime import datetime, timedelta, timezone

MU_EARTH = 398600.4418        # km^3/s^2
RE_KM = 6371.2                # mean Earth radius used by the AE8/AP8 models (km)

# --- AS-506 post-TLI osculating elements (transcribed inputs, see docstring) ---
A_KM = 286545.0
ECC = 0.976966
INC = math.radians(31.383)
NU0 = math.radians(14.909)
ARGP = math.radians(4.410)
LAT0 = math.radians(9.9204)     # geocentric
LON0 = math.radians(-164.8373)
T0 = datetime(1969, 7, 16, 16, 22, 23, tzinfo=timezone.utc)      # TLI
T_ENTRY = datetime(1969, 7, 24, 16, 35, 0, tzinfo=timezone.utc)  # entry interface

# --- DGRF-1970 degree-1 coefficients, IGRF-13 (transcribed inputs) ---
G10, G11, H11 = -30220.0, -2068.0, 5737.0


def gmst_rad(t):
    """Greenwich mean sidereal time (IAU 1982-style, adequate to ~arcsec here)."""
    jd = 2440587.5 + t.timestamp() / 86400.0     # Unix epoch JD
    d = jd - 2451545.0
    gmst_deg = 280.46061837 + 360.98564736629 * d
    return math.radians(gmst_deg % 360.0)


def _kepler_E_from_nu(nu):
    E = 2.0 * math.atan2(math.sqrt(1 - ECC) * math.sin(nu / 2), math.sqrt(1 + ECC) * math.cos(nu / 2))
    return E


def _time_from_nu(nu):
    """Seconds from perigee passage to true anomaly nu (elliptic)."""
    E = _kepler_E_from_nu(nu)
    M = E - ECC * math.sin(E)
    n = math.sqrt(MU_EARTH / A_KM ** 3)
    return M / n


# node reconstruction ---------------------------------------------------------
U0 = ARGP + NU0                       # argument of latitude at TLI
# angle from ascending node to sub-point, measured along the equator
_ALPHA_OFF = math.atan2(math.cos(INC) * math.sin(U0), math.cos(U0))
RAAN = (gmst_rad(T0) + LON0 - _ALPHA_OFF) % (2 * math.pi)

# perigee-passage epochs for the two legs
_TP_OUT = T0 - timedelta(seconds=_time_from_nu(NU0))       # outbound perigee epoch
_TP_IN = T_ENTRY + timedelta(seconds=120.0)                # inbound: vacuum perigee ~2 min after EI


def check_anchor():
    """Verify the reconstructed geometry reproduces the documented TLI point."""
    lat = math.degrees(math.asin(math.sin(INC) * math.sin(U0)))
    st = state(T0, leg="out")
    return {"lat_from_elements_deg": lat, "documented_lat_deg": math.degrees(LAT0),
            "recomputed_lon_deg": st["lon_deg"], "documented_lon_deg": math.degrees(LON0),
            "recomputed_r_km": st["r_km"], "documented_r_km": 6711.964,
            "recomputed_v_kms": st["v_kms"], "documented_v_kms": 10.8343}


def _nu_from_time(dt_peri):
    """True anomaly from time since perigee (Newton on Kepler's equation)."""
    n = math.sqrt(MU_EARTH / A_KM ** 3)
    M = n * dt_peri
    # Newton with bisection safety
    E = math.pi if M > 0 else -math.pi
    lo, hi = (0.0, 2 * math.pi) if M > 0 else (-2 * math.pi, 0.0)
    E = M if abs(M) < 1 else E
    for _ in range(80):
        f = E - ECC * math.sin(E) - M
        fp = 1 - ECC * math.cos(E)
        if f > 0:
            hi = E
        else:
            lo = E
        E_new = E - f / fp
        if not (lo < E_new < hi):
            E_new = 0.5 * (lo + hi)
        if abs(E_new - E) < 1e-13:
            E = E_new
            break
        E = E_new
    nu = 2.0 * math.atan2(math.sqrt(1 + ECC) * math.sin(E / 2), math.sqrt(1 - ECC) * math.cos(E / 2))
    return nu


def state(t, leg="out"):
    """Geocentric state + magnetic coordinates at datetime t.

    leg='out': time measured from outbound perigee epoch (nu > 0 branch)
    leg='in' : inbound branch (nu < 0), anchored to entry interface
    """
    tp = _TP_OUT if leg == "out" else _TP_IN
    dt = (t - tp).total_seconds()
    nu = _nu_from_time(dt)
    p = A_KM * (1 - ECC ** 2)
    r = p / (1 + ECC * math.cos(nu))
    v = math.sqrt(MU_EARTH * (2 / r - 1 / A_KM))
    u = ARGP + nu
    # ECI (Greenwich-referenced equatorial inertial)
    xo = math.cos(RAAN) * math.cos(u) - math.sin(RAAN) * math.sin(u) * math.cos(INC)
    yo = math.sin(RAAN) * math.cos(u) + math.cos(RAAN) * math.sin(u) * math.cos(INC)
    zo = math.sin(u) * math.sin(INC)
    x, y, z = r * xo, r * yo, r * zo
    # ECEF
    th = gmst_rad(t)
    xe = math.cos(th) * x + math.sin(th) * y
    ye = -math.sin(th) * x + math.cos(th) * y
    ze = z
    lon = math.degrees(math.atan2(ye, xe))
    lat_gc = math.degrees(math.asin(ze / r))
    # geodetic (spherical-to-geodetic; flattening correction, small at altitude)
    lat_gd, h_km = _geodetic(xe, ye, ze)
    # tilted-dipole magnetic coordinates
    mlat, L, bb0 = dipole_coords(xe, ye, ze)
    return {"t": t, "nu_deg": math.degrees(nu), "r_km": r, "v_kms": v,
            "lat_deg": lat_gc, "lon_deg": lon, "lat_geodetic_deg": lat_gd,
            "height_km": h_km, "maglat_deg": mlat, "L_dipole": L, "BB0_dipole": bb0}


_WGS_A, _WGS_F = 6378.137, 1 / 298.257223563


def _geodetic(x, y, z):
    """ECEF (km) -> geodetic latitude (deg), height (km). Bowring iteration."""
    b = _WGS_A * (1 - _WGS_F)
    e2 = 1 - (b / _WGS_A) ** 2
    p = math.hypot(x, y)
    lat = math.atan2(z, p * (1 - e2))
    for _ in range(6):
        N = _WGS_A / math.sqrt(1 - e2 * math.sin(lat) ** 2)
        h = p / math.cos(lat) - N
        lat = math.atan2(z, p * (1 - e2 * N / (N + h)))
    N = _WGS_A / math.sqrt(1 - e2 * math.sin(lat) ** 2)
    h = p / math.cos(lat) - N
    return math.degrees(lat), h


# dipole axis unit vector (ECEF), from DGRF-1970 degree-1 coefficients
_B0SQ = G10 ** 2 + G11 ** 2 + H11 ** 2
_COLAT_D = math.acos(-G10 / math.sqrt(_B0SQ))          # dipole colatitude of N pole...
# Note: the geomagnetic north pole (in the northern hemisphere) is at
# colatitude theta_d, east longitude phi_d:
_THETA_D = math.acos(G10 / math.sqrt(_B0SQ))           # ~168.65 deg => south axis
# Use the conventional formulas:
_PHI_D = math.atan2(H11, G11) + math.pi                # ~289.85 deg east
_TILT = math.pi - _THETA_D                             # 11.35 deg
_ZM = (math.sin(_TILT) * math.cos(_PHI_D),
       math.sin(_TILT) * math.sin(_PHI_D),
       math.cos(_TILT))                                # unit vector toward geomagnetic N pole


def dipole_pole():
    return {"lat_deg": 90 - math.degrees(_TILT), "lon_deg": math.degrees(_PHI_D) % 360,
            "tilt_deg": math.degrees(_TILT)}


def dipole_coords(xe, ye, ze):
    """Magnetic latitude (deg), dipole L, and B/B0 for ECEF position (km)."""
    r = math.sqrt(xe * xe + ye * ye + ze * ze)
    cosang = (xe * _ZM[0] + ye * _ZM[1] + ze * _ZM[2]) / r
    mlat = math.pi / 2 - math.acos(max(-1.0, min(1.0, cosang)))
    c = math.cos(mlat)
    L = (r / RE_KM) / (c * c)
    bb0 = math.sqrt(1 + 3 * math.sin(mlat) ** 2) / c ** 6
    return math.degrees(mlat), L, bb0


def sample_leg(leg="out", r_max_km=12 * RE_KM, n=1500):
    """Sample one belt transit from perigee out to r_max (or reverse for inbound).

    Returns list of state dicts ordered by time, plus per-sample dt weights (s)
    for trapezoidal time integration.
    """
    # find nu at r_max
    p = A_KM * (1 - ECC ** 2)
    cnu = (p / r_max_km - 1) / ECC
    nu_max = math.acos(max(-1.0, min(1.0, cnu)))
    tp = _TP_OUT if leg == "out" else _TP_IN
    if leg == "out":
        nus = [NU0 + (nu_max - NU0) * k / (n - 1) for k in range(n)]
    else:
        nus = [-nu_max + (nu_max - 0.0017) * k / (n - 1) for k in range(n)]  # to ~perigee
    out = []
    for nu in nus:
        t = tp + timedelta(seconds=_time_from_nu(nu))
        out.append(state(t, leg=leg))
    return out
