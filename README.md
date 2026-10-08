# Electric Tail-Sitter UAV (EDF) – Conceptual Design Study

[![CI](https://github.com/onurtuncer/tailsitter-uav-design/actions/workflows/ci.yml/badge.svg)](https://github.com/onurtuncer/tailsitter-uav-design/actions/workflows/ci.yml)
[![Design Pipeline](https://github.com/onurtuncer/tailsitter-uav-design/actions/workflows/design-pipeline.yml/badge.svg)](https://github.com/onurtuncer/tailsitter-uav-design/actions/workflows/design-pipeline.yml)
[![Release](https://img.shields.io/github/v/tag/onurtuncer/tailsitter-uav-design?label=release)](https://github.com/onurtuncer/tailsitter-uav-design/releases)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23238441.svg)](https://doi.org/10.5281/zenodo.23238441)

**📖 Documentation:** rendered design notebooks, an interactive 3D viewer and
the bill of materials are published at
**<https://onurtuncer.github.io/tailsitter-uav-design/>**

<p align="center">
  <a href="https://onurtuncer.github.io/tailsitter-uav-design/viewer.html">
    <img src="assets/vbat_render.png" width="560" alt="Rendered CAD model of the tail-sitter standing on its landing legs, nose up"/>
  </a>
  <br/>
  <em>The current design point, rendered from the CadQuery solid model the
  pipeline exports on every run — click the image for the
  <a href="https://onurtuncer.github.io/tailsitter-uav-design/viewer.html">interactive 3D viewer</a>
  (orbit, exploded view).
  Regenerate with <code>python scripts/render_readme_cad.py</code> after a design change.</em>
</p>

This repository contains a **first-principles conceptual design study** for a
**small electric tail-sitter VTOL UAV** of the single-ducted-fan,
jet-vane-controlled class.

The focus is **not** on a production UAV, but on:
- architectural feasibility,
- mass / power / energy closure,
- and understanding design trade-offs at the **technology-demonstrator level**.

The study starts from mission requirements and ends with a frozen COTS
hardware set, a solid model, and CFD case setups. The whole chain is
reproducible from YAML inputs and is re-run in CI on every change.

---

## 1. Problem Definition

### Objective
Design a **small electric ducted-fan tail-sitter UAV** capable of:

- **True VTOL** (vertical takeoff and landing, tail-down)
- **A short, cruise-dominated mission** after transition
- Carrying **0.5 kg of payload**
- Using **electric propulsion only** and **COTS hardware only** (no custom rotor development)

This mirrors the *earliest feasibility phase* of tail-sitter concepts before
scaling to fuel engines, endurance optimization, or operational payloads.

### Design Philosophy
- **First-order physics** (momentum theory, L/D cruise, lumped thermal models),
  with every assumption explicit and every parameter in `config/*.yaml`
  with a commented rationale. There are no magic numbers in the code.
- **Derived, not configured:** disk loading, heat loads, ESC current and
  servo torque requirements follow from the sizing result.
- **Honest margins:** where the design falls short, the shortfall is kept
  as a pinned *standing finding* rather than tuned away (see §5).
- **Higher-fidelity tools as consumers:** CAD, CFD (OpenFOAM) and the PX4
  configuration sit *downstream* of the conceptual design. They never feed
  back into it automatically.

> *“Is this architecture feasible at this scale, and where are the dominant penalties?”*

---

## 2. Vehicle Concept

| | |
|---|---|
| **Configuration** | Tail-sitter VTOL, vertical takeoff and landing on the tail |
| **Propulsor** | COTS 203 mm 3-blade prop in the airframe duct (ADR-0003) |
| **Control** | Jet vanes in the duct exit (primary, all three axes in hover/transition); ailerons as cruise roll backup (ADR-0004) |
| **Wing** | NACA 4412, sized to its real CL_max (ADR-0015) |
| **Construction** | Segmented-FDM airframe on an 8 mm CFRP spar (ADR-0008); semi-monocoque clamshell fuselage (ADR-0010) |
| **Avionics** | PX4 on a Pixhawk-class flight controller (ADR-0011) |

Jet-vane authority scales with fan thrust, so it collapses in cruise, where
thrust is only about 1/(L/D) of hover thrust. Ailerons use wing dynamic
pressure instead and stay effective exactly where the vanes are weakest.

---

## 3. Mission Profile

| Segment | Value |
|---|---|
| Hover | 120 s total (60 s takeoff + 60 s landing) |
| Transitions | 40 s total (2 × 20 s, billed at hover power) |
| Cruise | 900 s at 20 m/s (18 km) |
| Total | ≈ 17.7 min (target band 15–20 min) |
| Energy reserve | 20 % |
| Payload | 0.5 kg |

Hover is expensive at this disk loading, so the mission is deliberately
short-hover. All mission parameters are editable in
[`config/mission.yaml`](config/mission.yaml).

---

## 4. Current Design Point

From the latest pipeline run (release `v0.5.4`):

| Quantity | Value |
|---|---|
| MTOW (mass closure) | ≈ 2.52 kg |
| Hover electrical power | ≈ 743 W (≈ 8.1C peak discharge) |
| Wing | NACA 4412, S = 0.1883 m², b = 1.063 m, W/S = 131 N/m² |
| Wing CL_max (3D) | 1.489 |
| Cruise L/D (design point) | 13.4 |
| Fuselage (conceptual) | ⌀ 98 × 491 mm |
| Fuselage (as selected, COTS) | ⌀ 107 × 533 mm |
| As-selected all-up mass | ≈ 2.34 kg (182 g under closure) |

**Frozen COTS hardware** ([`out/components.yaml`](out/components.yaml)):
Holybro Pixhawk 6C flight controller · APD 80F3[X] telemetry ESC ·
SunnySky X4120 KV465 motor · Master Airscrew 3-blade 8×6 prop ·
KST X08 V6 servos · Molicel P50B 6S1P 5000 mAh Li-ion pack.

The regression pins in
[`tests/test_design_outputs.py`](tests/test_design_outputs.py) hold these
values. An intentional design change updates them in the same commit.

---

## 5. Modeling Approach

**Hover:** momentum (actuator-disk) theory with a figure of merit and
drive-train efficiencies,

$$
P_{ideal} = \frac{T^{3/2}}{\sqrt{2 \rho A}}
$$

Disk loading is derived from MTOW and the COTS rotor diameter. A thrust
ceiling (`T_max_N` in [`config/rotor.yaml`](config/rotor.yaml)) makes the
sizing fail loudly rather than size past the rotor.

**Cruise:** power from a lift-to-drag model,

$$
P = \frac{W \, V}{L/D}
$$

The mass closure uses a conservative L/D of 8. The wing notebook reports the
design-point L/D from the selected airfoil polar, wing geometry and a fixed
body drag area (ADR-0019).

**Battery:** mass from mission energy, pack specific energy, usable fraction,
reserve, and a mission-averaged I²R discharge efficiency for the nominal
pack resistance (ADR-0014).

**Mass closure:** iterative, on weight fractions. The structural fraction
uses an explicit member model of the clamshell (skin, longerons, crossbeams
and rings) scaled by a construction factor. This construction factor is the
most sensitive mass parameter in the project.

**Downstream analyses:** jet-vane and aileron authority against a common
angular-acceleration requirement; vibration isolation against the rotor
1/rev; fuselage layout, CG and drag; ESC cold-plate and battery-bay thermal
paths, plus a battery-pack mission transient; inertia tensor and BOM;
electrical design; and COTS selection, followed by an as-selected
re-solve with the frozen hardware (ADR-0012).

### Standing findings

The pipeline reports these openly, and the summary notebook collects them
from the handoffs:

- The **ESC cold-plate is marginal**: it needs a plate heavier than the ESC
  mass allocation, with only a few °C of margin.
- **Battery pack transient:** at 40 °C ambient, the nominal 90 mΩ pack
  ends the mission about 5 °C over its 60 °C limit. Measuring the built
  pack's DCIR at procurement is the next step.
- The **avionics bay and drive motor** exceed their weight-fraction
  allocations (≈ 25 g and ≈ 79 g).
- **Wing watch items:** un-modelled nose-down Cm0 (cruise trim) and the
  empirical Cl_max at Re ≈ 1.4·10⁵.

---

## 6. Design Pipeline

Everything flows one way, from configuration to CFD (ADR-0001):

```
config/*.yaml  ->  src/conceptual_design/  ->  notebooks/  ->  out/  ->  cfd/, px4/
(inputs)           (ALL physics)               (orchestrate)   (handoffs)  (consumers)
```

Notebooks are thin orchestration (ADR-0013). Each one writes YAML handoffs
to `out/` that later ones read, so they run **in this order**:

| # | Notebook | Purpose | Output |
|---|---|---|---|
| 1 | `tailsitter_conceptual_design` | Mission sizing, mass closure | — |
| 2 | `wing_design` | Airfoil selection, candidate-wing comparison | `airfoil.yaml` |
| 3 | `control_vane_design` | Jet-vane sizing | `control_vanes.yaml` |
| 4 | `aileron_design` | Cruise roll backup | `aileron.yaml` |
| 5 | `vibration_isolation` | FC/IMU and payload soft mounts | `vibration.yaml` |
| 6 | `fuselage_design` | Layout, CG, drag, structure | `fuselage.yaml` |
| 7 | `thermal_design` | ESC cold-plate, battery bay, pack transient | `thermal.yaml` |
| 8 | `vehicle_solid_model` | CadQuery CAD (STEP/STL) | `cad/` |
| 9 | `aeolion_handoff` | VLM/BEMT geometry contract | `cad/aeolion_geometry.json` |
| 10 | `mass_properties` | Inertia tensor, BOM | `mass_properties.yaml`, `bom.csv` |
| 11 | `wiring_diagram` | Electrical block diagram | `wiring_diagram.svg`, `electrical.yaml` |
| 12 | `cots_selection` | COTS hardware freeze | `components.yaml` |
| 13 | `aileron_design_cots` | NB4 with the frozen servo | `aileron_cots.yaml` |
| 14 | `vibration_isolation_cots` | NB5 with the frozen FC | `vibration_cots.yaml` |
| 15 | `fuselage_design_cots` | NB6 with as-selected masses and envelopes | `fuselage_cots.yaml` |
| 16 | `design_summary` | Final rollup and standing findings (read-only) | — |

Architectural decisions are recorded in [`adr/`](adr/), and the design
history is in [`CHANGELOG.md`](CHANGELOG.md).

---

## 7. Repository Structure

```
config/                     Design inputs (mission, aero, battery, rotor, ...) as commented YAML
config/components/          COTS candidate databases (FC, ESC, motor, prop, servo, battery)
src/conceptual_design/      All physics models, reports and plots
src/conceptual_design/cad/  CadQuery solid-model generators
notebooks/                  The sixteen design notebooks (import from src/, write to out/)
out/                        Generated design outputs (YAML handoffs, STEP/STL, plots, BOM)
cfd/                        OpenFOAM cases (vehicle, prop, vanes) + DAVE-ML post-processing
px4/                        PX4 airframe configuration and SITL setup
schemas/                    JSON schema for the Aeolion geometry handoff
printprep/                  3D-print preparation scripts
scripts/                    Utilities (README render, repo dump)
adr/                        Architecture decision records
tests/                      Unit, design-regression and geometry tests (pytest)
```

---

## 8. Requirements

- Python **3.10+**
- Install the package in editable mode with the extras you need:

```bash
pip install -e ".[cad,notebooks,dev]"
```

CadQuery (the `cad` extra) is only needed for the solid-model notebook
(NB8). At the time of writing it does not install on Python 3.14; use
Python 3.12 for NB8. Everything else runs on the plain scientific stack.

**OpenFOAM (optional):** the `Allrun.*` scripts under [`cfd/`](cfd/) need a
sourced **OpenFOAM.com v2306+** environment on Linux. See
[`cfd/README.md`](cfd/README.md). CI only validates the case *setup*
with a coarse smoke run. Production CFD is run on dedicated hardware.

---

## 9. How to Run

Launch Jupyter from the repository root and run the notebooks in the order
of §6:

```bash
jupyter lab
```

or execute them headless:

```bash
for nb in tailsitter_conceptual_design wing_design control_vane_design \
          aileron_design vibration_isolation fuselage_design thermal_design \
          vehicle_solid_model aeolion_handoff mass_properties wiring_diagram \
          cots_selection aileron_design_cots vibration_isolation_cots \
          fuselage_design_cots design_summary; do
  jupyter nbconvert --to notebook --execute --output-dir executed "notebooks/${nb}.ipynb"
done
```

Adjust parameters in `config/*.yaml` and re-run to explore trade-offs.

### Tests

```bash
pytest
ruff check src tests scripts printprep cfd
```

A failing design-regression pin that you didn't expect means the design
drifted. A geometry-test span failure usually means `out/cad/` is stale.

### Continuous integration

- **`ci.yml`:** ruff, pytest on Python 3.10/3.12/3.14, ShellCheck on the CFD scripts.
- **`design-pipeline.yml`:** executes all sixteen notebooks and runs the
  regression and geometry tests on every PR. On `main` it also runs the
  coarse OpenFOAM smoke run and deploys the GitHub Pages site.
- **`release.yml`:** pushing a `v*` tag re-runs the full pipeline and
  attaches the design snapshot to a GitHub Release.

### Versioning & releases

The package version derives from **git tags** via `setuptools-scm`. Never
edit a version number by hand. Tagging a release freezes the design:

```bash
git tag v0.6.0 && git push origin v0.6.0
```

CI then attaches the snapshot (all `out/` handoffs, the executed notebooks,
and STEP/STL geometry) to the
[GitHub Release](https://github.com/onurtuncer/tailsitter-uav-design/releases).
Convention: bump **minor** for a new design point or analysis capability,
and **patch** for corrections that do not move the design. Each tag gets a
[changelog](CHANGELOG.md) entry.

---

## 10. Scope & Limitations

This study:

- ❌ is not a flight-ready design
- ❌ does no structural stress analysis
- ❌ does not implement control laws (PX4 is configured, not modified)
- ❌ does not address certification or safety

It is appropriate for concept feasibility, academic exploration and
architecture comparison.

Natural extensions include parametric sweeps and Pareto fronts, disk-loading
vs. noise trade-offs, transition dynamics, folding converged CFD polars back
into the aerodynamic model, and hybrid-electric or fuel-based scaling.

---

## 11. Citation

If you use this work, please cite it. The metadata are in
[`CITATION.cff`](CITATION.cff), and GitHub's **“Cite this repository”**
button (repository sidebar) exports them as BibTeX or APA.

## 12. License

[MIT](LICENSE). No warranty and no fitness for flight.

---

## 👤 Author

**Prof.Dr. Onur Tuncer**  
Aerospace Engineer, Researcher & C++ Systems Developer  
Istanbul Technical University · ORCID [0000-0002-2803-1146](https://orcid.org/0000-0002-2803-1146)  
Email: **onur.tuncer@itu.edu.tr**

<p align="left">
  <img src="assets/itu_logo.png" width="180" alt="Istanbul Technical University"/>
</p>
