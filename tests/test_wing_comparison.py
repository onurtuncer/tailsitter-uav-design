"""Tests for wing_comparison.py -- the ADR-0019 candidate-wing study."""

import math

import numpy as np
import pytest

import conceptual_design.wing_comparison as wc
from conceptual_design.wing_comparison import WingCandidate, compare_wings
from conceptual_design.wing_sizing import WingStructureParams

# Study inputs (2026-09-17 co-author wing study, "NACA karsilastirma 3")
RHO, G = 1.225, 9.80665
F_BODY = 0.010 * 0.1834          # old CD0_fuselage referenced to wing A
WS_PARAMS = WingStructureParams(sweep_rad=0.0, taper=1.0, tc_ratio=0.12,
                                n_ult=3.75, k_material=0.70, method="raymer")
A = WingCandidate("A", "NACA 2412", 0.1834, 6.0)
B = WingCandidate("B", "NACA 4412", 0.1883, 6.0)
C = WingCandidate("C", "NACA 4412", 0.2100, 6.5)


def _run(cands, m_wing_design=0.1213):
    return compare_wings(cands, MTOW_design_kg=2.518, m_wing_design_kg=m_wing_design,
                         f_body_m2=F_BODY, V_cruise=20.0, V_ref=18.0, dV_MD=1.0,
                         rho=RHO, g=G, ws=WS_PARAMS)


@pytest.fixture
def constant_e(monkeypatch):
    """The study held e at the AR-6 value 0.8691 for every wing."""
    monkeypatch.setattr(wc, "oswald_efficiency", lambda AR, sweep=0.0: 0.8691)


class TestBodyDragArea:
    def test_body_drag_does_not_scale_with_wing_area(self):
        a, c = _run([A, C])
        # parasite drag area f0 = Cd0_w*S + f_body: only the wing part grows
        q = 0.5 * RHO * 18.0**2
        f0_a, f0_c = a.D_parasite_ref_N / q, c.D_parasite_ref_N / q
        Cd0_w = a.CD0_eff - F_BODY / a.S_m2
        assert f0_c - f0_a == pytest.approx(Cd0_w * (C.S_m2 - A.S_m2), rel=1e-9)

    def test_reference_wing_matches_old_coefficient_bookkeeping(self):
        (a,) = _run([A])
        assert a.CD0_eff == pytest.approx(0.0126 + 0.010, rel=1e-9)


class TestPolarRelations:
    def test_min_power_speed_and_power(self):
        (b,) = _run([B])
        assert b.V_MP == pytest.approx(b.V_MD / 3.0 ** 0.25, rel=1e-12)
        W = b.MTOW_kg * G
        V = np.linspace(8.0, 30.0, 4001)
        P = (0.5 * RHO * V**2 * b.CD0_eff * b.S_m2
             + b.k_induced * W**2 / (0.5 * RHO * V**2 * b.S_m2)) * V
        assert b.P_min_W == pytest.approx(P.min(), rel=1e-4)
        assert b.D_min_N * b.LD_max == pytest.approx(W, rel=1e-12)

    def test_required_alpha_nan_below_stall(self):
        (a,) = _run([A])
        assert math.isnan(a.required_alpha_deg(0.99 * a.V_S, RHO, G))
        assert a.required_alpha_deg(a.V_MD_plus, RHO, G) == pytest.approx(
            a.alpha_MD_plus_deg, rel=1e-12)

    def test_design_wing_carries_no_mass_penalty(self):
        (b,) = _run([B])
        assert b.dm_wing_kg == pytest.approx(0.0, abs=1e-3)


class TestReproducesStudy:
    """Report-3 numbers, with the study's constant e."""

    def test_characteristic_values(self, constant_e):
        a, b, c = _run([A, B, C])
        assert [p.V_S for p in (a, b, c)] == pytest.approx([13.43, 12.00, 11.40], abs=0.02)
        assert [p.V_MD for p in (a, b, c)] == pytest.approx([19.01, 18.82, 17.73], abs=0.03)
        assert [p.LD_max for p in (a, b, c)] == pytest.approx([13.46, 13.54, 14.42], abs=0.01)
        assert [p.P_min_W for p in (a, b, c)] == pytest.approx([30.59, 30.15, 26.84], abs=0.06)
        assert [p.D_total_ref_N for p in (a, b, c)] == pytest.approx(
            [1.845, 1.833, 1.726], abs=0.003)
        assert c.D_induced_ref_N / a.D_induced_ref_N == pytest.approx(0.818, abs=0.003)

    def test_alpha_uses_the_candidates_own_lift_slope(self, constant_e):
        # The study reported 3.78 deg for C at V_MD+1 using the AR-6 lift
        # slope; with C's own AR-6.5 CL_alpha it is 3.63 deg (ADR-0019).
        a, b, c = _run([A, B, C])
        assert a.alpha_MD_plus_deg == pytest.approx(5.13, abs=0.01)
        assert b.alpha_MD_plus_deg == pytest.approx(3.71, abs=0.01)
        assert c.alpha_MD_plus_deg == pytest.approx(3.63, abs=0.01)
