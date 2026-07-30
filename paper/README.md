# Paper: AI-Assisted Aircraft Conceptualization

LaTeX sources for the manuscript *"AI-Assisted Aircraft
Conceptualization: Preliminary Design of a Tail-Sitter UAV"*
(Tuncer, Güneş, Üçler).

## Build

```bash
latexmk -pdf main.tex          # or: make
```

CI (`.github/workflows/paper.yml`) rebuilds the PDF on every push/PR
touching `paper/` and uploads it as the `paper-pdf` workflow artifact;
tagged releases attach `vbat-paper-<version>.pdf` to the GitHub
Release (`release.yml`).

Requires a standard TeX Live or MiKTeX distribution (pdflatex, natbib,
tikz + the `fit` library, rotating, booktabs, tabularx — all in the
default install).

Build verified with MiKTeX 25.12: 30 pages, no errors, no undefined
references, no overfull boxes. Both TikZ figures in `sections/model.tex`
have been rendered and visually checked. Note that Fig. 2 (the coupling
map) is a `sidewaysfigure` — it is rotated onto its own page because at
upright `\textwidth` the box text is too small to read. If you edit its
node coordinates, re-render and look at the page: the arrow routing and
the legend placement were tuned by hand to avoid collisions.

## Layout

- `main.tex` — preamble, title, abstract, acknowledgements
- `sections/` — one file per section, in `\input` order:
  `introduction`, `related`, `method`, `model`, `results`, `conclusions`.
  `model.tex` (§4) is the integrative parameter model: the parameter
  taxonomy, the coupling map, the dimensioning relations, and the
  constraint check flow. Both of its figures are TikZ — no image files
- `references.bib` — bibliography (from the draft's reference list +
  the Claude Code tool citation)
- `figures/` — **copied from the pipeline outputs** (`assets/`,
  `out/`); regenerate there and re-copy after a design change, do not
  edit here

## Editorial state

Open items are marked in red in the PDF via `\todopaper{...}` (none
currently). Before submission: re-check the process metrics if more
commits land (commit counts, AI co-authorship share, dates were
extracted from the git history on 2026-07-24).

Numbers in the case-study tables come from the v0.5.2 design snapshot
(`CHANGELOG.md`, `out/` handoffs) and the git history; update them if
the design point moves.
