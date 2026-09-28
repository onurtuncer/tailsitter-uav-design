"""
wing_comparison.py  --  Candidate-wing aerodynamic comparison (NB2)
==================================================================

PURPOSE
-------
Compares candidate wings (airfoil + planform) at their own weight, with
the fuselage drag held as a fixed equivalent flat-plate area so that a
larger wing does not artificially inflate the body drag.  Implements the
method of the 2026-09-17 co-author wing study ("NACA karsilastirma 3",
ADR-0019).

THEORY
------
DRAG BOOKKEEPING  (body drag area fixed)
    f0      = Cd0_w * S + f_body                         [m^2]
    CD0_eff = f0 / S = Cd0_w + f_body / S                [-]
    D_p     = q * f0,   D_i = 2 k W^2 / (rho V^2 S),   k = 1/(pi e AR)

    The older NB2 bookkeeping added a constant CD0_fuselage coefficient
    referenced to *whatever* wing area was being evaluated, which scales
    the body drag with S -- wrong for a wing-area trade.

CHARACTERISTIC SPEEDS  (parabolic polar)
    V_S    = sqrt(2 W / (rho S CL_max))
    V_MD   = sqrt(2 W / (rho S)) * (k / CD0_eff)^(1/4)     min drag
    V_MP   = V_MD / 3^(1/4)                                min power
    (L/D)_max = 1 / (2 sqrt(k CD0_eff)),  D_min = W / (L/D)_max
    P_min  = D(V_MP) * V_MP        (aerodynamic power only -- no
                                    propulsor/ESC efficiency)

REQUIRED ANGLE OF ATTACK  (linear CL-alpha, wing root chord line)
    alpha = alpha_L0 + CL / CL_alpha_3D,    CL = 2 W / (rho V^2 S)

WING-MASS PENALTY
    Each candidate's wing mass comes from the same Raymer GA formula the
    sizing loop uses.  Following the study, the wing-mass difference is
    added ON TOP of the design-point MTOW (conservative: the closure itself
    carries the wing inside the structural fraction, so there it shows up
    as a smaller fuselage structure pool instead of a heavier aircraft):

        MTOW_i = MTOW_design - m_w,design + m_w(S_i, AR_i, MTOW_i)

    solved by fixed-point iteration (Raymer's MTOW^0.49 dependence).

References
----------
  Raymer (2018), Aircraft Design: A Conceptual Approach, 6th ed., eq. 3-5, 15-46
  Anderson (2017), Fundamentals of Aerodynamics, 6th ed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List

from .airfoil_selection import (
    oswald_efficiency,
    parse_naca4,
    section_alpha_L0,
    section_Cd0,
    section_Cl_alpha,
    section_Cl_max,
    wing_CL_alpha,
    wing_CL_max,
)
from .wing_sizing import WingStructureParams, wing_mass_raymer_kg

MTOW_ITER_TOL_KG = 1e-7   # fixed-point tolerance on the corrected MTOW
MTOW_ITER_MAX    = 50


def body_drag_CD0(Cd0_section: float, f_body_m2: float, S_m2: float) -> float:
    """Effective zero-lift drag coefficient referenced to wing area S."""
    return Cd0_section + f_body_m2 / S_m2


@dataclass(frozen=True)
class WingCandidate:
    """One wing in the comparison (config/airfoil_selection.yaml)."""
    label:       str     # short name, e.g. "B -- ADR-0015 4412"
    designation: str     # NACA 4-digit designation
    S_m2:        float   # planform area   [m^2]
    AR:          float   # aspect ratio    [-]

    @classmethod
    def from_dict(cls, d: dict) -> "WingCandidate":
        return cls(label=str(d["label"]), designation=str(d["designation"]),
                   S_m2=float(d["S_m2"]), AR=float(d["AR"]))


@dataclass
class WingPerformance:
    """Evaluated candidate wing."""
    label:        str
    designation:  str
    S_m2:         float
    AR:           float
    b_m:          float
    chord_m:      float
    m_wing_kg:    float    # Raymer wing mass at MTOW_kg
    dm_wing_kg:   float    # vs the design-point wing
    MTOW_kg:      float    # corrected MTOW
    WS_N_m2:      float
    CL_max_3D:    float
    e_oswald:     float
    k_induced:    float
    CD0_eff:      float
    CL_alpha_rad: float
    alpha_L0_deg: float
    V_S:          float
    V_1p2S:       float
    V_MP:         float
    V_MD:         float
    V_MD_plus:    float    # V_MD + dV (study's operating speed)
    alpha_MD_plus_deg: float
    LD_max:       float
    D_min_N:      float
    P_min_W:      float    # aerodynamic power at V_MP
    V_ref:        float    # common comparison speed
    D_parasite_ref_N: float
    D_induced_ref_N:  float
    D_total_ref_N:    float
    P_ref_W:          float
    alpha_ref_deg:    float

    def required_alpha_deg(self, V: float, rho: float, g: float) -> float:
        """Required alpha [deg] for level flight at V; NaN below stall."""
        CL = 2.0 * self.MTOW_kg * g / (rho * V**2 * self.S_m2)
        if CL > self.CL_max_3D:
            return float("nan")
        return self.alpha_L0_deg + math.degrees(CL / self.CL_alpha_rad)


def corrected_mtow_kg(S_m2: float, AR: float, MTOW_design_kg: float,
                      m_wing_design_kg: float, V_cruise: float, rho: float,
                      ws: WingStructureParams) -> tuple[float, float]:
    """(MTOW_i, m_wing_i) with the wing-mass delta added on top."""
    mtow = MTOW_design_kg
    for _ in range(MTOW_ITER_MAX):
        m_w = wing_mass_raymer_kg(S_m2, AR, mtow, V_cruise, rho, ws)
        new = MTOW_design_kg - m_wing_design_kg + m_w
        if abs(new - mtow) < MTOW_ITER_TOL_KG:
            return new, m_w
        mtow = new
    raise RuntimeError("corrected MTOW did not converge")


def evaluate_wing(cand: WingCandidate, MTOW_design_kg: float,
                  m_wing_design_kg: float, f_body_m2: float, V_cruise: float,
                  V_ref: float, dV_MD: float, rho: float, g: float,
                  ws: WingStructureParams) -> WingPerformance:
    """Full aerodynamic evaluation of one candidate wing at its own weight."""
    M, P, t = parse_naca4(cand.designation)
    S, AR = cand.S_m2, cand.AR

    mtow, m_w = corrected_mtow_kg(S, AR, MTOW_design_kg, m_wing_design_kg,
                                  V_cruise, rho, ws)
    W = mtow * g

    e      = oswald_efficiency(AR)
    k      = 1.0 / (math.pi * AR * e)
    Cd0_w  = section_Cd0(t)
    CD0    = body_drag_CD0(Cd0_w, f_body_m2, S)
    CLa    = wing_CL_alpha(section_Cl_alpha(t), AR, e)
    CLmax  = wing_CL_max(section_Cl_max(M, P, t))
    aL0    = math.degrees(section_alpha_L0(M, P))

    V_S    = math.sqrt(2.0 * W / (rho * S * CLmax))
    V_MD   = math.sqrt(2.0 * W / (rho * S)) * (k / CD0) ** 0.25
    V_MP   = V_MD / 3.0 ** 0.25
    LD_max = 1.0 / (2.0 * math.sqrt(k * CD0))

    def drag(V: float) -> tuple[float, float]:
        q = 0.5 * rho * V**2
        return q * CD0 * S, k * W**2 / (q * S)

    def alpha(V: float) -> float:
        CL = 2.0 * W / (rho * V**2 * S)
        return aL0 + math.degrees(CL / CLa)

    Dp_mp, Di_mp = drag(V_MP)
    Dp_ref, Di_ref = drag(V_ref)

    return WingPerformance(
        label=cand.label, designation=cand.designation.upper(),
        S_m2=S, AR=AR, b_m=math.sqrt(AR * S), chord_m=math.sqrt(S / AR),
        m_wing_kg=m_w, dm_wing_kg=m_w - m_wing_design_kg, MTOW_kg=mtow,
        WS_N_m2=W / S, CL_max_3D=CLmax, e_oswald=e, k_induced=k,
        CD0_eff=CD0, CL_alpha_rad=CLa, alpha_L0_deg=aL0,
        V_S=V_S, V_1p2S=1.2 * V_S, V_MP=V_MP, V_MD=V_MD,
        V_MD_plus=V_MD + dV_MD, alpha_MD_plus_deg=alpha(V_MD + dV_MD),
        LD_max=LD_max, D_min_N=W / LD_max, P_min_W=(Dp_mp + Di_mp) * V_MP,
        V_ref=V_ref, D_parasite_ref_N=Dp_ref, D_induced_ref_N=Di_ref,
        D_total_ref_N=Dp_ref + Di_ref, P_ref_W=(Dp_ref + Di_ref) * V_ref,
        alpha_ref_deg=alpha(V_ref),
    )


def compare_wings(candidates: List[WingCandidate], **kwargs) -> List[WingPerformance]:
    """Evaluate every candidate with the same bookkeeping (see evaluate_wing)."""
    return [evaluate_wing(c, **kwargs) for c in candidates]
