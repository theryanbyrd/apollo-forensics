"""
Agent-based extension of the Grimes (2016) conspiracy-failure model.

Shared model helpers (Grimes analytic model, Gompertz mortality, plot style)
live here so run.py can import them without circularity.

Model provenance
----------------
Grimes DR (2016) "On the Viability of Conspiratorial Beliefs",
PLOS ONE 11(1): e0147905, and its published correction,
PLOS ONE 11(3): e0151003 (non-homogeneous Poisson form for time-varying N).

  L(t)          = 1 - exp(-integral_0^t [1 - psi^N(t')] dt'),  psi = 1 - p
  constant N    : L(t) = 1 - exp(-t * (1 - psi^N))             (unchanged by correction)
  Gompertz N(t) : N(t) = N0 * exp((alpha/beta) * (1 - exp(beta*(t + t_e))))
                  with alpha = 1e-4, beta = 0.085 (Grimes' human-mortality
                  constants, his ref. 28: Levy & Levin 2014)

Calibrated per-person per-year leak probabilities (Grimes Table 1, from his
Eq 8, p >= 1 - (1 - ln2/t)^(1/N) applied to real exposed conspiracies):
  NSA PRISM      N=30,000, t=6 yr  -> p = 4.09e-6   (his deliberately
                                       conservative "best case for conspirators";
                                       assumes ALL NSA staff knew)
  Tuskegee       N=6,700,  t=25 yr -> p = 4.20e-6
  FBI forensics  N=500,    t=6 yr  -> p = 2.45e-4   (the least-diluted
                                       calibration: only forensics staff counted)

ABM extension (this file): heterogeneous witting core with
  - per-agent Gompertz mortality (1969 workforce, mean age ~35),
  - annual defection hazard p_base, doubled 1969-1991 (Cold-War defection
    payoff multiplier),
  - deathbed-confession channel (probability q_db per death),
  - FOIA-era document-leak channel from 1975 (per-member archival hazard),
  - independent Soviet-exposure Bernoulli channel 1969-1991 (the USSR tracked
    Apollo in real time and had every incentive to expose a fake).
All parameters are printed and written to results/summary.json; every number
reported comes from these simulations.
"""

import json
import numpy as np
from scipy.stats import truncnorm

# ----------------------------------------------------------------------------
# Grimes analytic model
# ----------------------------------------------------------------------------

GOMPERTZ_ALPHA = 1e-4   # Grimes eq 5 constants (Levy & Levin 2014)
GOMPERTZ_BETA = 0.085

# Calibration constants exactly as published (Grimes 2016, Table 1)
P_CONS = 4.09e-6    # NSA PRISM-derived, ultra-conservative (used in his Results)
P_TUSK = 4.20e-6    # Tuskegee-derived
P_FBI = 2.45e-4     # FBI-forensics-derived (highest of his three estimates)


def phi(p, N):
    """Mean failures per year, phi = 1 - (1-p)^N  (Grimes eq 2)."""
    N = np.asarray(N, dtype=float)
    return -np.expm1(N * np.log1p(-p))


def L_const(t, N, p):
    """Failure probability, constant N (Grimes eq 3 with eq 4)."""
    return -np.expm1(-np.asarray(t, dtype=float) * phi(p, N))


def survival_const(t, N, p):
    """P(secret intact at t) = 1 - L = exp(-t*phi)."""
    return np.exp(-np.asarray(t, dtype=float) * phi(p, N))


def n_gompertz(t, N0, t_e, alpha=GOMPERTZ_ALPHA, beta=GOMPERTZ_BETA):
    """Surviving conspirators, single-event conspiracy (Grimes eq 5)."""
    t = np.asarray(t, dtype=float)
    return N0 * np.exp((alpha / beta) * (1.0 - np.exp(beta * (t + t_e))))


def L_inhomogeneous(t_grid, N_of_t, p):
    """Corrected form (PLOS ONE 11(3):e0151003):
    L(t) = 1 - exp(-int_0^t phi(t') dt'), cumulative-trapezoid on t_grid."""
    ph = phi(p, N_of_t)
    integral = np.concatenate(
        [[0.0], np.cumsum(0.5 * (ph[1:] + ph[:-1]) * np.diff(t_grid))])
    return -np.expm1(-integral), integral


def L_homogeneous_original(t_grid, N_of_t, p):
    """Grimes' ORIGINAL (uncorrected) eq 3, L = 1 - exp(-t*phi(N(t))).
    Kept only to validate our implementation against the original Fig 1
    caption numbers; all results use the corrected form."""
    return -np.expm1(-t_grid * phi(p, N_of_t))


def p_lower_bound(N, t):
    """Grimes eq 8: p >= 1 - (1 - ln2/t)^(1/N)."""
    return -np.expm1(np.log1p(-np.log(2.0) / t) / N)


def t_fail(N, p, threshold=0.95):
    """Time until L exceeds threshold, constant N (Grimes Table 3)."""
    return -np.log1p(-threshold) / phi(p, N)


def n_max_for_mu(t, p, mu=0.05):
    """Max N with L(t) <= mu, constant N (Grimes Table 4)."""
    phi_req = -np.log1p(-mu) / t
    return np.log1p(-phi_req) / np.log1p(-p)


def n_max_survival(p, t=57.0, s_min=0.5):
    """Max N with P(secret survives to t) >= s_min (our frontier)."""
    phi_req = -np.log(s_min) / t
    return np.log1p(-phi_req) / np.log1p(-p)


# ----------------------------------------------------------------------------
# Plot style (dataviz reference palette, light mode)
# ----------------------------------------------------------------------------

STYLE = {
    "surface": "#fcfcfb",
    "page": "#f9f9f7",
    "ink": "#0b0b0b",
    "ink2": "#52514e",
    "muted": "#898781",
    "grid": "#e1e0d9",
    "axis": "#c3c2b7",
    "series": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"],
    "critical": "#d03b3b",
    "good": "#0ca30c",
    # sequential blue ramp, steps 100 -> 700 (light -> dark)
    "seq_blues": ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec",
                  "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab",
                  "#184f95", "#104281", "#0d366b"],
}


def apply_style(plt):
    plt.rcParams.update({
        "figure.facecolor": STYLE["page"],
        "axes.facecolor": STYLE["surface"],
        "axes.edgecolor": STYLE["axis"],
        "axes.labelcolor": STYLE["ink2"],
        "axes.titlecolor": STYLE["ink"],
        "xtick.color": STYLE["muted"],
        "ytick.color": STYLE["muted"],
        "grid.color": STYLE["grid"],
        "grid.linewidth": 0.6,
        "axes.grid": True,
        "axes.axisbelow": True,
        "font.family": "sans-serif",
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.frameon": False,
        "savefig.dpi": 200,
        "savefig.facecolor": STYLE["page"],
    })


# ----------------------------------------------------------------------------
# Agent-based Monte Carlo
# ----------------------------------------------------------------------------

HORIZON = 57            # 1969 -> 2026
COLDWAR_YEARS = 23      # 1969 -> 1991 inclusive (USSR dissolved Dec 1991)
FOIA_START = 6          # document channel active from 1975 (1974 FOIA amendments)

ABM_DEFAULTS = dict(
    age_mean=35.0,      # 1969 aerospace workforce, mean age ~35 (assumption)
    age_sd=8.0,
    age_lo=21,
    age_hi=65,
    q_deathbed=0.01,    # P(credible confession/papers released per death) - assumption
    p_doc=1e-5,         # per-member per-year archival-leak hazard from 1975 - assumption
    coldwar_mult=2.0,   # defection-payoff multiplier 1969-1991 - assumption
    q_soviet=0.10,      # P/yr USSR detects AND exposes a fake, 1969-1991 - assumption
    n_runs=10000,
    seed=17,
)


def _age_distribution(cfg):
    """PMF over integer starting ages, truncated normal."""
    ages = np.arange(cfg["age_lo"], cfg["age_hi"] + 1)
    a = (cfg["age_lo"] - 0.5 - cfg["age_mean"]) / cfg["age_sd"]
    b = (cfg["age_hi"] + 0.5 - cfg["age_mean"]) / cfg["age_sd"]
    dist = truncnorm(a, b, loc=cfg["age_mean"], scale=cfg["age_sd"])
    pmf = dist.cdf(ages + 0.5) - dist.cdf(ages - 0.5)
    return ages, pmf / pmf.sum()


def gompertz_annual_q(age):
    """Annual death probability at integer age (same constants as Grimes)."""
    h = GOMPERTZ_ALPHA * np.exp(GOMPERTZ_BETA * np.asarray(age, dtype=float))
    return -np.expm1(-h)


def simulate_scenario(n_core, p_base, cfg=None, soviet=True):
    """Vectorised annual-step Monte Carlo.

    Returns dict with per-run first-exposure year (HORIZON if censored),
    the first channel to fire, and summary statistics.
    Channels: 0=defection, 1=deathbed, 2=documents, 3=soviet.
    """
    cfg = {**ABM_DEFAULTS, **(cfg or {})}
    rng = np.random.default_rng(cfg["seed"] + n_core)
    runs, T = cfg["n_runs"], HORIZON

    ages0, pmf = _age_distribution(cfg)
    counts = rng.multinomial(n_core, pmf, size=runs)          # [runs, n_ages]

    alive = np.zeros((runs, T), dtype=np.int64)
    deaths = np.zeros((runs, T), dtype=np.int64)
    for t in range(T):
        alive[:, t] = counts.sum(axis=1)
        q = gompertz_annual_q(ages0 + t)                       # ages advance
        d = rng.binomial(counts, q[None, :])
        deaths[:, t] = d.sum(axis=1)
        counts = counts - d

    # per-year hazards per channel, [runs, T]
    cw = np.where(np.arange(T) < COLDWAR_YEARS, cfg["coldwar_mult"], 1.0)
    p_eff = np.clip(p_base * cw, 0, 1)[None, :]
    hz_def = -np.expm1(alive * np.log1p(-p_eff))               # defection
    hz_db = -np.expm1(deaths * np.log1p(-cfg["q_deathbed"]))   # deathbed
    doc = np.zeros(T)
    doc[FOIA_START:] = -np.expm1(n_core * np.log1p(-cfg["p_doc"]))
    hz_doc = np.broadcast_to(doc, (runs, T))                   # documents
    sov = np.zeros(T)
    if soviet:
        sov[:COLDWAR_YEARS] = cfg["q_soviet"]
    hz_sov = np.broadcast_to(sov, (runs, T))                   # soviet

    hazards = np.stack([hz_def, hz_db, hz_doc, hz_sov])        # [4, runs, T]
    fires = rng.random(hazards.shape) < hazards
    any_fire = fires.any(axis=0)                               # [runs, T]
    exposed = any_fire.any(axis=1)
    first_year = np.where(exposed, any_fire.argmax(axis=1), T)

    # attribute the first channel to fire in the exposure year
    channel = np.full(runs, -1, dtype=int)
    if exposed.any():
        rows = np.nonzero(exposed)[0]
        yy = first_year[rows]
        ch = fires[:, rows, yy]                                # [4, n_exposed]
        channel[rows] = ch.argmax(axis=0)

    tte = first_year.astype(float)
    res = dict(
        n_core=n_core, p_base=p_base, soviet=soviet,
        n_runs=runs,
        p_survive_57=float((~exposed).mean()),
        exposed_frac=float(exposed.mean()),
        first_year=first_year,
        channel=channel,
        median_tte=float(np.median(tte)),
        mean_tte_exposed=float(tte[exposed].mean()) if exposed.any() else None,
        q10_tte=float(np.quantile(tte, 0.10)),
        q90_tte=float(np.quantile(tte, 0.90)),
        channel_shares={
            name: float((channel == i).sum() / max(exposed.sum(), 1))
            for i, name in enumerate(["defection", "deathbed", "documents", "soviet"])
        },
        config={k: cfg[k] for k in ABM_DEFAULTS},
    )
    return res


def soviet_silence_factor(q_grid=(0.05, 0.10, 0.25, 0.50), years=COLDWAR_YEARS):
    """P(USSR stays silent through the Cold War | hoax) for a range of
    per-year detect-and-expose probabilities."""
    return {f"q={q:g}": float((1.0 - q) ** years) for q in q_grid}


def run_abm(core_sizes=(50, 200, 1000, 5000, 30000),
            p_values=(P_FBI, P_CONS), cfg=None, verbose=True):
    """Full scenario grid, internal channels only AND with the Soviet channel."""
    out = []
    for p in p_values:
        for n in core_sizes:
            for soviet in (False, True):
                r = simulate_scenario(n, p, cfg=cfg, soviet=soviet)
                out.append(r)
                if verbose:
                    tag = "joint(+USSR)" if soviet else "internal    "
                    print(f"  ABM core={n:>6} p={p:.3g} {tag}: "
                          f"P(survive 57y)={r['p_survive_57']:.4g}  "
                          f"median TTE={r['median_tte']:.1f} yr  "
                          f"shares={ {k: round(v, 3) for k, v in r['channel_shares'].items()} }")
    return out


def deathbed_sensitivity(n_core=1000, p_base=P_CONS,
                         q_grid=(0.001, 0.01, 0.05)):
    """Sensitivity of the weakest-channel scenario to the deathbed parameter,
    internal channels only (no Soviet)."""
    rows = {}
    for q in q_grid:
        r = simulate_scenario(n_core, p_base, cfg={"q_deathbed": q}, soviet=False)
        rows[f"q_db={q:g}"] = dict(p_survive_57=r["p_survive_57"],
                                   median_tte=r["median_tte"])
    return rows


if __name__ == "__main__":
    res = run_abm()
    print(json.dumps(soviet_silence_factor(), indent=2))
