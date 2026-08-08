"""Pure-Python port of the NASA AE-8/AP-8 trapped-radiation model evaluator.

This is a line-faithful port of TRARA1/TRARA2 from `trmfun.f` (TRMFUN.FOR, 1987,
NSSDC), as distributed by NASA in https://github.com/nasa/radbelt
(radbelt/extern/aep8/trmfun.f, SPDX: NASA-1.3).  The model *coefficient files*
(ae8min.asc, ae8max.asc, ap8min.asc, ap8max.asc) are the actual NASA/NSSDC
model maps, downloaded verbatim from the same repository and cached in ./data/.

The port is validated point-by-point against the genuine compiled Fortran
(radbelt 0.1.8 binary wheel) by validate_port.py; see results/port_validation.json.

References:
  Vette, J.I., "The AE-8 Trapped Electron Model Environment", NSSDC/WDC-A-R&S 91-24 (1991)
  Sawyer, D.M. & Vette, J.I., "AP-8 Trapped Proton Environment", NSSDC/WDC-A-R&S 76-06 (1976)

Interface (mirrors radbelt.core.aep8):
    flux = aep8(energy_MeV, L, B_over_B0, model)
      model in {'ae8min','ae8max','ap8min','ap8max'}
      returns omnidirectional integral flux (particles cm^-2 s^-1) above energy.
"""
import os

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
_CACHE = {}


def _read_map(model):
    """Read a NSSDC .asc model file: 8-int header + NMAP ints, FORMAT(1X,12I6)."""
    path = os.path.join(_DATA_DIR, model + ".asc")
    ints = []
    with open(path) as f:
        for line in f:
            line = line.rstrip("\n")
            # FORMAT(1X,12I6): skip 1 char, then 12 fixed-width-6 integer fields
            body = line[1:]
            for k in range(0, len(body), 6):
                fld = body[k:k + 6].strip()
                if fld:
                    ints.append(int(fld))
    ihead = ints[:8]
    nmap = ihead[7]
    fmap = ints[8:8 + nmap]
    return ihead, fmap


def _get_model(model):
    if model not in _CACHE:
        _CACHE[model] = _read_map(model)
    return _CACHE[model]


def _trara2(mp, off, il, ib, fistep):
    """Port of FUNCTION TRARA2(MAP,IL,IB).

    mp:  full map list (0-based python list; MAP(j) == mp[j-1])
    off: Fortran offset such that TRARA2's MAP(k) == parent MAP(off+k)
         (caller passes MAP(I1+3) -> off = I1+2)
    Returns scaled log flux.
    """
    def M(k):
        return mp[off + k - 1]

    fnl = float(il)
    fnb = float(ib)
    itime = 0
    i2 = 0
    i1 = 0
    l1 = 0
    l2 = M(i2 + 1)
    # label 1: find consecutive sub-sub-maps with scaled L values LS1 <= IL <= LS2
    while not (M(i2 + 2) > il):
        i1 = i2
        l1 = l2
        i2 = i2 + l2
        l2 = M(i2 + 1)
    # label 2
    if l1 < 4 and l2 < 4:
        return 0.0

    # local floats
    fkb = 0.0
    flog = 0.0
    fkbm = 0.0
    flogm = 0.0
    fincr1 = 0.0
    fincr2 = 0.0
    sl1 = 0.0
    sl2 = 0.0
    fkbj1 = 0.0
    j1 = 4
    j2 = 4

    label = 5 if not (M(i2 + 3) > M(i1 + 3)) else 10
    while True:
        if label == 5:
            i1, i2 = i2, i1
            l1, l2 = l2, l1
            label = 10

        if label == 10:
            fll1 = float(M(i1 + 2))
            fll2 = float(M(i2 + 2))
            dfl = (fnl - fll1) / (fll2 - fll1)
            flog1 = float(M(i1 + 3))
            flog2 = float(M(i2 + 3))
            fkb1 = 0.0
            fkb2 = 0.0
            if l1 < 4:
                label = 32
                continue
            # B/B0 loop: DO 17 J2=4,L2
            hit23 = False
            j2 = 4
            while j2 <= l2:
                fincr2 = float(M(i2 + j2))
                if fkb2 + fincr2 > fnb:
                    hit23 = True
                    break
                fkb2 = fkb2 + fincr2
                flog2 = flog2 - fistep
                j2 += 1
            if not hit23:
                itime += 1
                if itime == 1:
                    label = 5
                    continue
                return 0.0
            label = 23
            continue

        if label == 23:
            if itime == 1:
                label = 30
                continue
            if j2 == 4:
                label = 28
                continue
            sl2 = flog2 / fkb2
            hit31 = False
            j1 = 4
            while j1 <= l1:
                fincr1 = float(M(i1 + j1))
                fkb1 = fkb1 + fincr1
                flog1 = flog1 - fistep
                fkbj1 = ((flog1 / fistep) * fincr1 + fkb1) / ((fincr1 / fistep) * sl2 + 1.0)
                if fkbj1 <= fkb1:
                    hit31 = True
                    break
                j1 += 1
            if not hit31:
                if fkbj1 <= fkb2:
                    return 0.0
            # label 31
            if fkbj1 <= fkb2:
                label = 29
                continue
            fkb1 = 0.0
            label = 30
            continue

        if label == 30:
            fkb2 = 0.0
            label = 32
            continue

        if label == 32:
            j2 = 4
            fincr2 = float(M(i2 + j2))
            flog2 = float(M(i2 + 3))
            flog1 = float(M(i1 + 3))
            label = 28
            continue

        if label == 28:
            flogm = flog1 + (flog2 - flog1) * dfl
            fkbm = 0.0
            fkb2 = fkb2 + fincr2
            flog2 = flog2 - fistep
            sl2 = flog2 / fkb2
            if l1 < 4:
                label = 35
                continue
            j1 = 4
            fincr1 = float(M(i1 + j1))
            fkb1 = fkb1 + fincr1
            flog1 = flog1 - fistep
            sl1 = flog1 / fkb1
            label = 15
            continue

        if label == 29:
            fkbm = fkbj1 + (fkb2 - fkbj1) * dfl
            flogm = fkbm * sl2
            flog2 = flog2 - fistep
            fkb2 = fkb2 + fincr2
            sl1 = flog1 / fkb1
            sl2 = flog2 / fkb2
            label = 15
            continue

        if label == 15:
            if sl1 < sl2:
                label = 20
                continue
            fkbj2 = ((flog2 / fistep) * fincr2 + fkb2) / ((fincr2 / fistep) * sl1 + 1.0)
            fkb = fkb1 + (fkbj2 - fkb1) * dfl
            flog = fkb * sl1
            if fkb >= fnb:
                label = 60
                continue
            fkbm = fkb
            flogm = flog
            if j1 >= l1:
                return 0.0
            j1 += 1
            fincr1 = float(M(i1 + j1))
            flog1 = flog1 - fistep
            fkb1 = fkb1 + fincr1
            sl1 = flog1 / fkb1
            label = 15
            continue

        if label == 20:
            fkbj1 = ((flog1 / fistep) * fincr1 + fkb1) / ((fincr1 / fistep) * sl2 + 1.0)
            fkb = fkbj1 + (fkb2 - fkbj1) * dfl
            flog = fkb * sl2
            if fkb >= fnb:
                label = 60
                continue
            fkbm = fkb
            flogm = flog
            if j2 >= l2:
                return 0.0
            j2 += 1
            fincr2 = float(M(i2 + j2))
            flog2 = flog2 - fistep
            fkb2 = fkb2 + fincr2
            sl2 = flog2 / fkb2
            label = 15
            continue

        if label == 35:
            fincr1 = 0.0
            sl1 = -900000.0
            label = 20
            continue

        if label == 60:
            if fkb < fkbm + 1.0e-10:
                return 0.0
            t = flogm + (flog - flogm) * ((fnb - fkbm) / (fkb - fkbm))
            return max(t, 0.0)


def _trara1(descr, fmap, fl, bb0, energies):
    """Port of SUBROUTINE TRARA1(DESCR,MAP,FL,BB0,E,F,N).

    energies must be in ascending order.  Returns list of log10 fluxes.
    """
    fistep = float(descr[6] // descr[1])       # DESCR(7)/DESCR(2), integer division
    escale = float(descr[3])                   # DESCR(4)
    fscale = float(descr[6])                   # DESCR(7)
    xnl = min(15.6, abs(fl))
    nl = int(xnl * descr[4])                   # DESCR(5), Fortran INT truncation
    if bb0 < 1.0:
        bb0 = 1.0
    nb = int((bb0 - 1.0) * descr[5])           # DESCR(6)

    def MAP(j):
        return fmap[j - 1]

    i1 = 0
    i2 = MAP(1)
    i3 = i2 + MAP(i2 + 1)
    l3 = MAP(i3 + 1)
    e1 = MAP(i1 + 2) / escale
    e2 = MAP(i2 + 2) / escale
    s0 = True
    s1 = True
    s2 = True
    f0 = 1.001
    f1 = 1.001
    f2 = 1.002
    e0 = e1
    i0 = 0
    out = []
    for e in energies:
        # label 1: scan up in energy
        while not (e <= e2 or l3 == 0):
            i0 = i1
            i1 = i2
            i2 = i3
            i3 = i3 + l3
            l3 = MAP(i3 + 1)
            e0 = e1
            e1 = e2
            e2 = MAP(i2 + 2) / escale
            s0 = s1
            s1 = s2
            s2 = True
            f0 = f1
            f1 = f2
        # label 2
        if s1:
            f1 = _trara2(fmap, i1 + 2, nl, nb, fistep) / fscale
        if s2:
            f2 = _trara2(fmap, i2 + 2, nl, nb, fistep) / fscale
        s1 = False
        s2 = False
        f = f1 + (f2 - f1) * (e - e1) / (e2 - e1)
        # special interpolation when F2 == 0 and a zeroth map exists
        if not (f2 > 0.0) and i1 != 0:
            if s0:
                f0 = _trara2(fmap, i0 + 2, nl, nb, fistep) / fscale
            s0 = False
            f = min(f, f0 + (f1 - f0) * (e - e0) / (e1 - e0))
        out.append(max(f, 0.0))
    return out


def aep8(energy, lvalue, bb0, model):
    """Omnidirectional integral flux (cm^-2 s^-1) above `energy` MeV.

    model: 'ae8min' | 'ae8max' | 'ap8min' | 'ap8max'
    Mirrors SUBROUTINE AEP8 in radbelt's core.f (one energy per call).
    """
    ihead, fmap = _get_model(model)
    logf = _trara1(ihead, fmap, float(lvalue), float(bb0), [float(energy)])[0]
    return 10.0 ** logf if logf > 0.0 else 0.0
