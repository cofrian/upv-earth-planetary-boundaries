# Multi-Agent Pipeline Report

## Contents
- `multi_agent_pipeline_report.tex` — full report in LaTeX (article class, ≈ 3 700 words).
- `multi_agent_pipeline_report.md` — Markdown twin, identical content.
- `figures/` — 8 PNG figures referenced by both files.
- `generate_diagrams.py` — script that regenerates `figures/` from the run outputs.

## Compiling the LaTeX

LaTeX is **not installed on the GPU machine**, so compile the document on your local machine or in Overleaf.

### Option A — Overleaf (no install)
1. Create a new blank project on overleaf.com.
2. Upload `multi_agent_pipeline_report.tex` and the `figures/` folder (drag-and-drop).
3. Compile with `pdflatex` (the default). Run twice so the table of contents resolves.

### Option B — Local TeX Live
```bash
# Install once (Ubuntu/Debian)
sudo apt install texlive-latex-recommended texlive-fonts-extra texlive-latex-extra latexmk

# Compile (twice, or use latexmk)
cd docs/report
latexmk -pdf multi_agent_pipeline_report.tex
# or
pdflatex multi_agent_pipeline_report.tex
pdflatex multi_agent_pipeline_report.tex
```

The output is `multi_agent_pipeline_report.pdf` in the same folder.

### Required LaTeX packages
All standard, all in `texlive-latex-recommended` + `texlive-latex-extra`:
`graphicx`, `hyperref`, `booktabs`, `listings`, `xcolor`, `geometry`, `caption`, `subcaption`, `babel`, `inputenc`, `fontenc`, `microtype`, `csquotes`, `lmodern`, `amsmath`, `tabularx`, `array`, `float`, `multirow`.

## Regenerating the figures

```bash
python3 docs/report/generate_diagrams.py
```

This reads the latest CSVs from `nlp/llm/outputs/` and writes 8 PNGs into `figures/`.
Run after every pipeline re-execution to keep the figures in sync with the reported numbers.
