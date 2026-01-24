# MAPLE Paper

Manuscript and supporting materials for "MAPLE: Model-Aware Parameter Literature Extraction for QSP Model Calibration", targeting CPT: Pharmacometrics & Systems Pharmacology.

MAPLE is a framework for LLM-assisted calibration of quantitative systems pharmacology (QSP) models. It combines model-aware literature search (using LLM web search guided by mechanistic context) with validated extraction and automatic code generation for Bayesian inference.

## Repository Structure

```
qsp-llm-workflows-paper/
├── paper/                    # Manuscript
│   ├── main.tex             # Main manuscript
│   ├── supplementary.tex    # Supplementary materials (S1-S5)
│   ├── cpt_article_outline.md # Article outline
│   └── references.bib       # Bibliography
│
├── examples/                 # PDAC calibration targets (YAML)
│   ├── psc_*.yaml           # Pancreatic stellate cell targets
│   ├── ecm_*.yaml           # ECM secretion targets
│   ├── tcell_*.yaml         # T cell killing targets
│   ├── tgfb_*.yaml          # TGF-beta secretion targets
│   └── treg_*.yaml          # Treg suppression targets
│
├── prompts/                  # LLM prompts for extraction
│   └── extract_calibration_target.md
│
├── presentation/             # Conference presentations
│   └── calibration_workflow_presentation.tex
│
└── archive/                  # Old manuscript materials
```

## Supplementary Materials

- **S1**: Complete SubmodelTarget example (PSC proliferation)
- **S2**: Supported model types table
- **S3**: Validation checks with code examples (DOI, value-in-snippet, unit validators)
- **S4**: Generated Julia/Turing.jl code structure
- **S5**: Pydantic model definitions

## Related Repository

MAPLE (SubmodelTarget schema, validators, Julia translator) is implemented in [qsp-llm-workflows](https://github.com/popellab/qsp-llm-workflows).

## Building the Paper

```bash
cd paper
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

## License

MIT
