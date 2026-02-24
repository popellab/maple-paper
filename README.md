# MAPLE Paper

Manuscript and supporting materials for "Structured Schemas for LLM-Modeler Collaboration in QSP Model Calibration", targeting CPT: Pharmacometrics & Systems Pharmacology.

MAPLE is a framework for LLM-assisted calibration of quantitative systems pharmacology (QSP) models. It combines model-aware literature search (using LLM web search guided by mechanistic context) with validated extraction and automatic code generation for Bayesian inference.

## Repository Structure

```
qsp-llm-workflows-paper/
├── paper/                    # Manuscript
│   ├── main.tex             # Main manuscript
│   ├── supplementary.tex    # Supplementary materials (S1-S5)
│   ├── generated/           # Auto-generated tables, figures, and LaTeX macros
│   └── references.bib       # Bibliography
│
├── scripts/                  # Statistics generation scripts
│   ├── generate_results.py  # Extraction pipeline metrics
│   ├── generate_curation_stats.py  # Curation field-level change metrics
│   └── generate_ct_stats.py # CalibrationTarget summary stats
│
├── metadata_storage/         # Original and curated YAML files for diffing
│
├── examples/                 # PDAC calibration target examples (YAML)
│
├── prompts/                  # LLM prompts for extraction
│   └── extract_calibration_target.md
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

MAPLE (SubmodelTarget and CalibrationTarget schemas, validators, Julia translator) is implemented in [qsp-llm-workflows](https://github.com/popellab/qsp-llm-workflows).

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
