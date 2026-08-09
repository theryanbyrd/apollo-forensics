"""Slab/spherical-shell dose model: NIST PSTAR/ESTAR data, aluminum shield, tissue dose.

Data files (queried live from NIST by fetch_data.py, cached in ./data/):
  data/pstar_aluminum.csv : proton stopping power + CSDA range in Al  (NIST PSTAR, matno 013)
  data/pstar_water.csv    : proton stopping power + CSDA range in liquid water (matno 276)
  data/estar_aluminum.csv : electron collision/radiative stopping powers in Al (NIST ESTAR)

Geometry: crew point at the center of a uniform spherical aluminum shell of areal
density x (g/cm^2).  For an isotropic omnidirectional flux J (cm^-2 s^-1), every
arrival direction traverses the same thickness, so

    D_tissue = sum over E of  j(E) * S_water(E_res(E, x)) * 1.602e-10 Gy

with E_res from CSDA range algebra R_Al(E_res) = R_Al(E) - x.  This is the
standard first-order (straight-ahead, no nuclear interactions, no secondaries)
estimate; expected accuracy a factor of ~2 for the geometries used here.

Electrons: trapped electrons (< 7 MeV) cannot penetrate >= 3 g/cm^2 of aluminum
(ESTAR CSDA range of a 7 MeV electron in Al is ~4.0 g/cm^2, and AE-8 flux above
5 MeV is negligible), so the primary-electron dose behind the CM hull is ~0.
The bremsstrahlung photon dose is estimated from the NIST ESTAR radiation yield:

    D_brems = 0.5 * integral( j_e(E) * E * Y(E) dE ) * (mu_en/rho)_tissue * 1.602e-10

with (mu_en/rho)_tissue = 0.03 cm^2/g (NIST XCOM, 0.2-1.5 MeV photons; flat to
~10%), the 0.5 accounting for outward-directed photons, and *no* credit taken
for photon attenuation in the shield (conservative: overestimates dose).
"""
import csv
import math
import os

import numpy as np

_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
MEV_PER_G_TO_GY = 1.602176634e-10   # 1 MeV/g in J/kg


def _load_csv(name):
    with open(os.path.join(_DATA, name)) as f:
        rows = list(csv.DictReader(f))
    return rows


class _LogLog:
    def __init__(self, x, y):
        self.lx = np.log(np.asarray(x, float))
        self.ly = np.log(np.asarray(y, float))

    def __call__(self, x):
        return np.exp(np.interp(np.log(np.asarray(x, float)), self.lx, self.ly))


class ProtonPhysics:
    def __init__(self):
        al = _load_csv("pstar_aluminum.csv")
        wa = _load_csv("pstar_water.csv")
        E = [float(r["T_MeV"]) for r in al]
        self.E_grid = np.array(E)
        self.range_al = _LogLog(E, [float(r["csda_range_gcm2"]) for r in al])
        self.energy_from_range_al = _LogLog([float(r["csda_range_gcm2"]) for r in al], E)
        self.stop_w = _LogLog([float(r["T_MeV"]) for r in wa],
                              [float(r["stop_total_MeVcm2g"]) for r in wa])
        self.stop_w_cap = float(self.stop_w(1.0))  # cap near end of range

    def cutoff_energy(self, x_gcm2):
        """Proton energy that just penetrates x g/cm^2 of aluminum."""
        return float(self.energy_from_range_al(x_gcm2))

    def dose_rate(self, e_grid, J_integral, x_gcm2, nfine=400):
        """Tissue dose rate (Gy/s) behind x g/cm^2 Al for integral-flux spectrum.

        e_grid: energies (MeV, ascending); J_integral: omnidirectional integral
        fluxes (cm^-2 s^-1) above those energies.  Returns 0 if spectrum empty.
        """
        e_grid = np.asarray(e_grid, float)
        J = np.asarray(J_integral, float)
        if not np.any(J > 0):
            return 0.0
        ecut = max(self.cutoff_energy(x_gcm2), e_grid[0])
        emax = e_grid[-1]
        if ecut >= emax:
            return 0.0
        Ef = np.geomspace(ecut * 1.0001, emax, nfine)
        # interpolate integral flux (log flux vs log E, zeros handled)
        pos = J > 0
        if pos.sum() < 2:
            return 0.0
        lJ = np.interp(np.log(Ef), np.log(e_grid[pos]), np.log(J[pos]),
                       left=np.log(J[pos][0]), right=-np.inf)
        Jf = np.exp(lJ)
        # differential flux j = -dJ/dE
        j = -np.gradient(Jf, Ef)
        j = np.clip(j, 0, None)
        # residual energy after shield
        R = self.range_al(Ef) - x_gcm2
        R = np.clip(R, 1e-6, None)
        Eres = self.energy_from_range_al(R)
        S = np.minimum(self.stop_w(np.clip(Eres, 0.3, None)), self.stop_w_cap)
        return float(np.trapezoid(j * S, Ef) * MEV_PER_G_TO_GY)

    def fluence_dose(self, e_grid, F_integral, x_gcm2):
        """Tissue dose (Gy) for an event-integrated fluence spectrum (cm^-2)."""
        return self.dose_rate(e_grid, F_integral, x_gcm2)  # same integral, fluence in


class ElectronPhysics:
    def __init__(self):
        es = _load_csv("estar_aluminum.csv")
        self.E = np.array([float(r["T_MeV"]) for r in es])
        self.s_col = np.array([float(r["closs"]) for r in es])
        self.s_rad = np.array([float(r["rloss"]) for r in es])
        self.s_tot = np.array([float(r["tloss_MeVcm2g"]) for r in es])
        # CSDA range in Al by integration of 1/S_tot
        r = np.concatenate([[0.0], np.cumsum(np.diff(self.E) /
                            (0.5 * (self.s_tot[1:] + self.s_tot[:-1])))])
        r += self.E[0] / self.s_tot[0]  # small start segment
        self.csda_al = r
        # radiation yield Y(E) = (1/E) * int_0^E (s_rad/s_tot) dE'
        frac = self.s_rad / self.s_tot
        y = np.concatenate([[0.0], np.cumsum(np.diff(self.E) * 0.5 * (frac[1:] + frac[:-1]))])
        self.yield_ = y / self.E
        self.mu_en_tissue = 0.03  # cm^2/g, NIST XCOM 0.2-1.5 MeV

    def range_al(self, E):
        return float(np.interp(E, self.E, self.csda_al))

    def brems_dose_rate(self, e_grid, J_integral, x_gcm2):
        """Bremsstrahlung tissue dose rate (Gy/s) behind x g/cm^2 Al.

        Primary electrons assumed fully stopped (valid for x >= 3 g/cm^2 with
        AE-8 spectra).  Conservative: no photon attenuation in the shield.
        """
        e_grid = np.asarray(e_grid, float)
        J = np.asarray(J_integral, float)
        pos = J > 0
        if pos.sum() < 2:
            return 0.0
        Ef = np.geomspace(max(e_grid[0], 0.04), e_grid[-1], 200)
        lJ = np.interp(np.log(Ef), np.log(e_grid[pos]), np.log(J[pos]),
                       left=np.log(J[pos][0]), right=-np.inf)
        Jf = np.exp(lJ)
        j = np.clip(-np.gradient(Jf, Ef), 0, None)
        Y = np.interp(Ef, self.E, self.yield_)
        radiated = np.trapezoid(j * Ef * Y, Ef)          # MeV cm^-2 s^-1 radiated
        return float(0.5 * radiated * self.mu_en_tissue * MEV_PER_G_TO_GY)


# --- August 1972 solar particle event (counterfactual) -----------------------
def spe_spectrum(F30=7.9e9, E0=26.5):
    """King (1974) anomalously-large-event fit for the 4-9 Aug 1972 SPE.

    Event-integrated omnidirectional fluence above E (MeV):
        F(>E) = F30 * exp((30 - E)/E0)   [protons cm^-2]
    King's AL-event parameters (as tabulated in the SPENVIS solar-proton model
    documentation and standard references): F30 = 7.9e9 cm^-2, E0 = 26.5 MeV.
    Cross-anchor: Smart et al. (2005) / McCracken et al. (2001) give the
    measured >30 MeV omnidirectional fluence as ~5.0e9 cm^-2 (Carrington 1859
    = 1.88e10 is 'about 4 times the August 1972 episode', Hu 2017); pass
    F30=5.0e9 for the measured-anchor variant.
    """
    e = np.geomspace(10, 1000, 120)
    return e, F30 * np.exp((30 - e) / E0)
