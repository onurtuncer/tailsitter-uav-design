# ADR-0019: Fixed body drag area in NB2 and the candidate-wing comparison

Date: 2026-09-28
Status: Accepted

## Context

A co-author wing study (2026-09-17, "NACA karşılaştırma" parts 2 and 3)
compared three wings at the current design point:

| | A — pre-ADR-0015 2412 | B — ADR-0015 4412 (design) | C — proposed 4412 |
|---|---|---|---|
| S [m²] | 0.1834 | 0.1883 | 0.2100 |
| AR | 6.0 | 6.0 | 6.5 |
| b [m] | 1.049 | 1.063 | 1.168 |

Part 3 fixed two problems with part 2 and is the version adopted here:

1. **Body drag.** NB2 added a constant `CD0_fuselage = 0.010` to the wing
   profile drag, referenced to whatever wing area was being evaluated,
   so a bigger wing also got a bigger fuselage drag. Part 3 holds the
   fuselage as a fixed equivalent flat-plate area:
   `f0 = Cd0_w·S + f_body`, `CD0_eff = Cd0_w + f_body/S`.
2. **Wing-mass penalty.** Each wing is evaluated at its own weight: its
   Raymer wing-mass difference is added on top of the design MTOW.

## Decision

- `config/airfoil_selection.yaml` replaces `CD0_fuselage` with
  `f_body_m2: 0.001834`. That is the old 0.010 referenced to wing A
  (0.1834 m²), the study's reference wing, so wing A's drag does not
  change. `analyse_airfoil`/`compare_airfoils` take `S_wing_m2` and
  `f_body_m2`.
- New module `wing_comparison.py` implements the study's bookkeeping:
  characteristic speeds (V_S, 1.2·V_S, V_MP, V_MD, V_MD+ΔV), required
  α, (L/D)_max, minimum aerodynamic power, and the drag breakdown at a
  common speed. NB2 gets a new §10 that always adds the converged
  design wing as B, with the alternatives from
  `config/airfoil_selection.yaml` → `wing_comparison`.
- The comparison is **reporting only**. It does not resize the wing and
  does not feed the mass closure. The design wing stays sized by
  `V_stall`/`AR` in `config/aerodynamics.yaml`.

### Two deliberate differences from the study

- **Oswald e per AR.** The study used e = 0.8691 (the AR-6 value) for all
  three wings. NB2 keeps Raymer's `e(AR)`, which gives 0.8540 at AR 6.5.
  For C this changes (L/D)_max from 14.42 to 14.30 and P_min from 26.84 to
  27.17 W. The ranking does not change.
- **Required α uses each wing's own lift slope.** The study computed C's
  α at V_MD+1 with the AR-6 CL_α, which gave 3.78° (3.96° in part 2).
  With C's own AR-6.5 slope it is **3.63°** (3.61° with e(AR)).
  `tests/test_wing_comparison.py` reproduces the study's other numbers
  with its constant e, and pins this correction.

## Consequences

- The design-point L/D_cruise in `out/airfoil.yaml` goes from 13.35 to
  **13.44** (CD0 from 0.0226 to 0.02234 at S = 0.1883 m²). The cruise
  jet-vane roll backup (NB4/NB13) goes from 50.0 to 49.7 deg/s², against
  the 30 deg/s² requirement. MTOW, hover power and the wing geometry do
  not change: the closure's cruise power still uses the conservative
  config `LD: 8.0`.
- The study's "corrected MTOW" (wing delta added on top) is a
  conservative reporting convention. In the closure the wing sits inside
  the structural fraction, so a heavier wing instead shrinks the fuselage
  structure pool. Adopting C (or `V_stall` 11.5 m/s) through `config/`
  would cost roughly 15–17 g of pool, against the ~9 g as-selected
  structure margin, and would re-open that finding. That is a separate
  decision, not taken here.
