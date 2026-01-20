# QSP LLM Workflows Paper

Manuscript and validation data for the qsp-llm-workflows framework, targeting CPT: Pharmacometrics & Systems Pharmacology.

## Repository Structure

```
qsp-llm-workflows-paper/
├── paper/                    # Manuscript
│   ├── main.tex             # Main manuscript
│   ├── supplementary.tex    # Supplementary materials
│   └── references.bib       # Bibliography
│
├── examples/                 # PDAC calibration targets
│   ├── psc_*.yaml           # Pancreatic stellate cell targets
│   ├── ecm_*.yaml           # ECM secretion targets
│   ├── tcell_*.yaml         # T cell killing targets
│   ├── tgfb_*.yaml          # TGF-beta secretion targets
│   ├── treg_*.yaml          # Treg suppression targets
│   └── joint_calibration.jl # Generated Julia inference script
│
├── prompts/                  # LLM prompts for extraction
│   └── extract_calibration_target.md
│
└── archive/                  # Old manuscript materials
    └── docs-manuscript/
```

## Related Repository

The framework code is in [qsp-llm-workflows](https://github.com/popellab/qsp-llm-workflows).

## Building the Paper

```bash
cd paper
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

## Running Inference

The Julia scripts in `examples/` can be run with:

```bash
cd examples
julia joint_calibration.jl
```

Requires Julia with DifferentialEquations.jl, Turing.jl, and Distributions.jl.

## License

MIT
