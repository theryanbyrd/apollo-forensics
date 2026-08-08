"""Hapke (1981/1984/2012) IMSA bidirectional-reflectance model, as used by
Sato et al. (2014) for the LROC WAC Hapke parameter maps.

Model form (Hapke 2012, "Theory of Reflectance and Emittance Spectroscopy",
2nd ed., ch. 8.7-8.9 and ch. 12; Sato et al. 2014, JGR Planets 119, 1775-1805,
doi:10.1002/2013JE004580):

    r(i,e,g) = (w / 4pi) * mu0e/(mu0e + mue)
               * [ p(g) * (1 + B_SH(g)) + H(mu0e)H(mue) - 1 ] * S(i,e,psi)

where r is the bidirectional reflectance (sr^-1): radiance L = J * r, with J
the collimated incident irradiance measured normal to the beam (W m^-2).

 - p(g): double-lobed Henyey-Greenstein (Hapke 2012 eq. 6.7a),
       p(g) = (1+c)/2 * (1-b^2)/(1 - 2b cos g + b^2)^{3/2}
            + (1-c)/2 * (1-b^2)/(1 + 2b cos g + b^2)^{3/2}
   (first term is the backscatter lobe; c > 0 increases backscatter).
 - B_SH(g) = Bs0 / (1 + tan(g/2)/hs): shadow-hiding opposition effect.
   CBOE disabled (Bc0 = 0 in the Sato et al. 2014 product).
 - H(x): Hapke (2002) approximation of the Ambartsumian-Chandrasekhar H fn.
 - mu0e, mue, S: macroscopic-roughness effective cosines and shadowing
   function (Hapke 1984, Icarus 59, 41-59; Hapke 2012 ch. 12.3.1) with
   roughness slope angle theta_bar. The Sato et al. product fixes
   theta_bar = 23.657 deg.

All angles in radians unless noted.
"""

import numpy as np


def p_dhg(g, b, c):
    """Double-lobed Henyey-Greenstein phase function (Hapke 2012 eq. 6.7a)."""
    cg = np.cos(g)
    back = (1 + c) / 2 * (1 - b**2) / (1 - 2 * b * cg + b**2) ** 1.5
    fwd = (1 - c) / 2 * (1 - b**2) / (1 + 2 * b * cg + b**2) ** 1.5
    return back + fwd


def B_shoe(g, Bs0, hs):
    """Shadow-hiding opposition effect (Hapke 2012 eq. 9.22)."""
    return Bs0 / (1.0 + np.tan(np.asarray(g) / 2.0) / hs)


def H_2002(x, w):
    """Hapke (2002) approximation to the H function (Hapke 2012 eq. 8.56)."""
    x = np.asarray(x, dtype=float)
    gamma = np.sqrt(1.0 - w)
    r0 = (1.0 - gamma) / (1.0 + gamma)
    xs = np.where(x <= 0, 1e-12, x)
    ln_term = np.log((1.0 + xs) / xs)
    Hinv = 1.0 - w * xs * (r0 + (1.0 - 2.0 * r0 * xs) / 2.0 * ln_term)
    H = 1.0 / Hinv
    return np.where(x <= 0, 1.0, H)


def _E1(x, tan_tb):
    """Hapke 1984 auxiliary E1; x is i or e."""
    tx = np.tan(x)
    with np.errstate(divide="ignore", over="ignore"):
        out = np.exp(-2.0 / (np.pi * tan_tb * np.where(tx == 0, np.inf, tx)))
    return np.where(tx <= 0, 0.0, out)


def _E2(x, tan_tb):
    tx = np.tan(x)
    with np.errstate(divide="ignore", over="ignore"):
        out = np.exp(-1.0 / (np.pi * tan_tb**2 * np.where(tx == 0, np.inf, tx) ** 2))
    return np.where(tx <= 0, 0.0, out)


def roughness(i, e, psi, theta_bar):
    """Hapke 1984 macroscopic roughness: effective cosines mu0e, mue and
    shadowing function S. i, e, psi broadcastable arrays (radians)."""
    i = np.asarray(i, float)
    e = np.asarray(e, float)
    psi = np.abs(np.asarray(psi, float))
    mu0, mu = np.cos(i), np.cos(e)
    if theta_bar <= 0:
        return mu0, mu, np.ones(np.broadcast(i, e, psi).shape)

    tan_tb = np.tan(theta_bar)
    chi = 1.0 / np.sqrt(1.0 + np.pi * tan_tb**2)
    f_psi = np.exp(-2.0 * np.tan(psi / 2.0))

    E1i, E2i = _E1(i, tan_tb), _E2(i, tan_tb)
    E1e, E2e = _E1(e, tan_tb), _E2(e, tan_tb)
    sin_half_psi2 = np.sin(psi / 2.0) ** 2
    cos_psi = np.cos(psi)

    eta_i = chi * (mu0 + np.sin(i) * tan_tb * E2i / (2.0 - E1i))
    eta_e = chi * (mu + np.sin(e) * tan_tb * E2e / (2.0 - E1e))

    # case i <= e
    den_le = 2.0 - E1e - (psi / np.pi) * E1i
    mu0e_le = chi * (mu0 + np.sin(i) * tan_tb * (cos_psi * E2e + sin_half_psi2 * E2i) / den_le)
    mue_le = chi * (mu + np.sin(e) * tan_tb * (E2e - sin_half_psi2 * E2i) / den_le)
    S_le = (mue_le / eta_e) * (mu0 / eta_i) * chi / (1.0 - f_psi + f_psi * chi * mu0 / eta_i)

    # case i > e
    den_gt = 2.0 - E1i - (psi / np.pi) * E1e
    mu0e_gt = chi * (mu0 + np.sin(i) * tan_tb * (E2i - sin_half_psi2 * E2e) / den_gt)
    mue_gt = chi * (mu + np.sin(e) * tan_tb * (cos_psi * E2i + sin_half_psi2 * E2e) / den_gt)
    S_gt = (mue_gt / eta_e) * (mu0 / eta_i) * chi / (1.0 - f_psi + f_psi * chi * mu / eta_e)

    le = i <= e
    mu0e = np.where(le, mu0e_le, mu0e_gt)
    mue = np.where(le, mue_le, mue_gt)
    S = np.where(le, S_le, S_gt)
    return mu0e, mue, np.clip(S, 0.0, None)


def r_bidir(i, e, g, psi, par, use_roughness=True):
    """Bidirectional reflectance r (sr^-1). L = J * r.

    par: dict with w, b, c, Bs0, hs, theta_bar (theta_bar in radians).
    """
    i = np.asarray(i, float)
    e = np.asarray(e, float)
    g = np.asarray(g, float)
    psi = np.asarray(psi, float)
    w = par["w"]
    tb = par["theta_bar"] if use_roughness else 0.0
    mu0e, mue, S = roughness(i, e, psi, tb)
    mu0e = np.clip(mu0e, 1e-9, None)
    mue = np.clip(mue, 1e-9, None)
    bracket = (
        p_dhg(g, par["b"], par["c"]) * (1.0 + B_shoe(g, par["Bs0"], par["hs"]))
        + H_2002(mu0e, w) * H_2002(mue, w)
        - 1.0
    )
    r = (w / (4.0 * np.pi)) * mu0e / (mu0e + mue) * bracket * S
    # no light for below-horizon sun/viewer
    r = np.where((np.cos(i) <= 0) | (np.cos(e) <= 0), 0.0, r)
    return r


def psi_from_angles(i, e, g):
    """Relative azimuth psi between incidence and emission planes,
    from cos g = cos i cos e + sin i sin e cos psi."""
    i = np.asarray(i, float)
    e = np.asarray(e, float)
    g = np.asarray(g, float)
    si, se = np.sin(i), np.sin(e)
    denom = np.where(si * se < 1e-9, 1e-9, si * se)
    cpsi = (np.cos(g) - np.cos(i) * np.cos(e)) / denom
    return np.arccos(np.clip(cpsi, -1.0, 1.0))


def geometry_from_vectors(n, to_sun, to_view):
    """Angles (i, e, g, psi) for surface normal n, unit vector to sun and to
    viewer. All arrays broadcastable with last axis = 3."""
    n = np.asarray(n, float)
    s = np.asarray(to_sun, float)
    v = np.asarray(to_view, float)
    mu0 = np.clip((n * s).sum(-1), -1, 1)
    mu = np.clip((n * v).sum(-1), -1, 1)
    i = np.arccos(np.clip(mu0, -1, 1))
    e = np.arccos(np.clip(mu, -1, 1))
    cg = np.clip((s * v).sum(-1), -1, 1)
    g = np.arccos(cg)
    psi = psi_from_angles(i, e, g)
    return i, e, g, psi
