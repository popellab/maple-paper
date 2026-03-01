# Claude Code Guidelines for maple-paper

## Project Overview

This repository contains the manuscript for MAPLE (Model-Aware Parameter Literature Extraction), a framework for LLM-assisted QSP model calibration. The paper targets CPT: Pharmacometrics & Systems Pharmacology.

## Repository Layout

```
paper/                          # Manuscript
  main.tex                      # Main manuscript (Intro, Methods, Results, Discussion)
  supplementary.tex             # Supplementary materials (S1-S5)
  references.bib                # Bibliography
  generated/                    # Auto-generated tables, figures, and LaTeX macros

batch_extraction/               # Extraction provenance (inputs to maple)
  run_extraction.sh             # Batch extraction invocation script
  extraction_targets.csv        # 19 PDAC parameters targeted for extraction
  model_context.txt             # Model description passed to LLM
  model_definitions.json        # ODE species/parameter definitions
  species_units.json            # Unit mappings for model species
  reference_values.yaml         # Curated reference constants (also used by inference/validation)
  model_structure.json          # Model structure (also used by inference/validation, requires MATLAB to regenerate)

metadata_storage/               # Extraction outputs (YAML files)
  submodel_targets/curated/     # 37 curated SubmodelTarget YAMLs (paper stats + inference)
  submodel_targets/originals/   # 38 original LLM-generated YAMLs (pre-curation)
  calibration_targets/originals/  # 23 original CalibrationTarget YAMLs (pre-curation)
  calibration_targets/curated/    # 50 curated CalibrationTargets (paired with originals for curation stats)
  calibration_targets/pdac_build/ # 59 final CalibrationTargets for PDAC model (generate_ct_stats.py)

scripts/                        # Statistics and inference generation
  generate_results.py           # Extraction pipeline metrics + source characteristics
  generate_latex.py             # LaTeX table generation from metrics.json
  generate_inference.py         # Julia/Turing.jl joint calibration script generator
  generate_curation_stats.py    # Curation field-level change metrics
  generate_ct_stats.py          # CalibrationTarget summary stats
  validate_submodel_target.py   # Schema + value-in-snippet validation
  validate_snippets_in_source.py
  joint_calibration.jl          # Generated Julia inference script
  logfire/                      # Logfire observability queries
    pull_ct_extraction_metrics.py  # Pull CalibrationTarget extraction metrics
    query_logfire.py               # Query extraction run traces
    query_logfire_errors.py        # Query extraction errors

supporting_files/               # Reference PDFs (gitignored)
```

## Writing Style

- Scientific journal format (CPT:PSP)
- Do not use `\textbf{}` for emphasis in running text
- Avoid emojis
- Do not use em-dashes (---). Use commas, parentheses, or restructure the sentence instead.
- Use proper LaTeX formatting for code (`\texttt{}`)
- Reference supplementary materials as "Supplementary Material S1" etc.

## Related Repository

The MAPLE framework code is in `../maple/` (sibling directory). Schema definitions, validators, Julia translator, and extraction CLI (`qsp-extract`) are there.

## Git Commits

- Do not include "Co-Authored-By: Claude" or any AI attribution in commit messages
- Use concise, descriptive commit messages

## Generated Statistics

All quantitative results in the paper come from auto-generated LaTeX macros in `paper/generated/`:
- `extraction_stats.tex` - Extraction pipeline metrics (from `scripts/generate_results.py`)
- `codegen_stats.tex` - Code generation metrics (from `scripts/generate_results.py`)
- `yaml_stats.tex` - Source characteristics (from `scripts/generate_results.py`)
- `curation_stats.tex` - Curation field-level change metrics (from `scripts/generate_curation_stats.py`)
- `ct_stats.tex` - CalibrationTarget summary stats (from `scripts/generate_ct_stats.py`)
- `inference_stats.tex` - Bayesian inference results (from `scripts/generate_inference.py`)

## Regeneration Pipeline

Inference must run before building the paper (it generates stats included in the manuscript).

```bash
python scripts/generate_results.py           # Collects metrics from YAMLs
python scripts/generate_latex.py             # Generates tables from metrics.json
python scripts/generate_curation_stats.py    # Diffs originals vs curated
python scripts/generate_ct_stats.py          # CalibrationTarget stats
python scripts/generate_inference.py metadata_storage/submodel_targets/curated --skip-single
julia scripts/joint_calibration.jl           # Run Bayesian inference
# Then build paper: cd paper && pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```

## Current State

- Manuscript: Complete (all sections)
- Supplementary S1-S5: Complete
