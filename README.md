# MAPLE Paper

Manuscript and supporting materials for "Structured Schemas for Provenance-Rich, LLM-Assisted QSP Model Calibration", targeting CPT: Pharmacometrics & Systems Pharmacology.

MAPLE is a framework for LLM-assisted calibration of quantitative systems pharmacology (QSP) models. It combines model-aware literature search (using LLM web search guided by mechanistic context) with structured extraction, automated validation, and code generation for Bayesian inference.

## Repository Structure

```
maple-paper/
├── paper/                        # Manuscript
│   ├── main.tex                  # Main manuscript
│   ├── supplementary.tex         # Supplementary materials (S1-S15)
│   ├── references.bib            # Bibliography
│   └── generated/                # Auto-generated tables, figures, and LaTeX macros
│
├── batch_extraction/             # Extraction provenance
│   ├── run_extraction.sh         # Batch extraction invocation script
│   ├── extraction_targets.csv    # 19 PDAC parameters targeted for extraction
│   ├── model_context.txt         # Model description passed to LLM
│   ├── model_definitions.json    # ODE species/parameter definitions
│   ├── species_units.json        # Unit mappings for model species
│   ├── reference_values.yaml    # Curated reference constants
│   └── model_structure.json    # Model structure (requires MATLAB to regenerate)
│
├── metadata_storage/             # Extraction outputs (YAML files)
│   ├── submodel_targets/
│   │   ├── curated/              # 37 curated SubmodelTargets (paper stats + inference)
│   │   └── originals/            # 38 original LLM outputs (pre-curation)
│   └── calibration_targets/
│       ├── originals/            # 22 raw batch-extracted CalibrationTargets (frozen)
│       └── final/                # Live corpus: 54 active + 5 retired under */excluded/
│
├── scripts/                      # Statistics and inference generation
│   ├── generate_results.py       # Extraction pipeline metrics
│   ├── generate_latex.py         # LaTeX table generation
│   ├── generate_inference.py     # Julia/Turing.jl inference script generator
│   ├── generate_curation_stats.py
│   ├── generate_ct_stats.py
│   ├── validate_submodel_target.py
│   ├── validate_snippets_in_source.py  # External check: snippets vs. source papers (Europe PMC/Unpaywall)
│   ├── verify_validation.sh         # Re-run the MAPLE v0.1.0 validator suite over all final targets
│   ├── verify_validation.py         # Worker for verify_validation.sh
│   ├── joint_calibration.jl      # Generated Julia inference script
│   ├── export_docx.sh            # Export to Word docx via pandoc
│   ├── postprocess_docx.py       # Post-process docx (captions, bold headers)
│   ├── clean_bbl.py              # Strip BibTeX artifacts for pandoc
│   └── logfire/                  # Logfire observability queries
│       ├── pull_ct_extraction_metrics.py
│       ├── query_logfire.py
│       └── query_logfire_errors.py
│
└── supporting_files/             # Reference PDFs (gitignored)
```

## Setup

Create a Python virtual environment and install the [MAPLE](https://github.com/popellab/maple) framework as an editable dependency:

```bash
uv venv
uv pip install -e ../maple
```

A `.env` file is required at the repository root with the following keys:

```
OPENAI_API_KEY=...       # For LLM extraction via qsp-extract
LOGFIRE_READ_TOKEN=...   # For querying extraction metrics from Logfire
```

## Reproducing Extractions

The `batch_extraction/` directory contains all inputs needed to reproduce the LLM extraction step using the [MAPLE](https://github.com/popellab/maple) framework:

```bash
cd batch_extraction
./run_extraction.sh
```

See `batch_extraction/run_extraction.sh` for details on how multiple independent derivations per parameter were obtained.

## Reproducing Paper Statistics

All quantitative results are auto-generated from the YAML metadata files:

```bash
# Collect metrics from extraction YAMLs
python scripts/generate_results.py

# Generate LaTeX tables
python scripts/generate_latex.py

# Generate curation and CalibrationTarget stats
python scripts/generate_curation_stats.py
python scripts/generate_ct_stats.py

# Generate and run Bayesian inference
python scripts/generate_inference.py metadata_storage/submodel_targets/curated --skip-single
julia scripts/joint_calibration.jl
```

## Verifying Snippets Against Source Papers

`scripts/validate_snippets_in_source.py` is the on-demand external validator described in the manuscript (Methods, "External Validation"). For each `value_snippet` in a target, it fetches the cited paper's text from Europe PMC and Unpaywall by DOI and uses fuzzy matching (80% similarity) to confirm the snippet actually appears in the source, catching cases where a snippet contains the right number but was not taken from the paper. It builds on the MAPLE validators `get_paper_texts_from_doi` and `fuzzy_find_snippet_in_text` (in [maple](https://github.com/popellab/maple)).

Because external full-text availability is uneven across sources, this runs on demand rather than as part of the per-target validation gate; the internal value-in-snippet check (run automatically during extraction) is the systematically applied anti-hallucination defense.

```bash
# Verify one target
python scripts/validate_snippets_in_source.py metadata_storage/submodel_targets/curated/<target>.yaml

# Verify all targets in a directory
python scripts/validate_snippets_in_source.py metadata_storage/submodel_targets/curated/
```

Requires network access. Snippets from sources without accessible full text are reported as skipped rather than failed.

## Verifying All Targets Pass Validation

`scripts/verify_validation.sh` re-runs the MAPLE Pydantic validator pipeline (schema, unit, reference, structural, and observable/observation code validators) over every final target and reports pass/fail. This reproduces the manuscript's claim that no final target retains an unresolved validator failure.

```bash
./scripts/verify_validation.sh        # validate all final targets
./scripts/verify_validation.sh -v     # also list each file
```

The result is pinned to MAPLE v0.1.0 (commit `7f1faa4`); later versions have a different schema and would report spurious failures. The wrapper puts the pinned version on the path automatically: it uses `$MAPLE_SRC` if set, otherwise clones the public MAPLE repo at commit `7f1faa4` (cached under `.maple-v0.1.0/`; override the URL with `$MAPLE_REPO_URL`). No local MAPLE checkout is required. It validates the 37 SubmodelTargets and 45 CalibrationTargets against the model structure, species units, and reference database in `batch_extraction/`, and exits non-zero if any target fails. This is the deterministic pipeline only; the network-dependent DOI and external-snippet checks are run separately (see above).

## Building the Paper

The inference step above must complete before building, as it generates statistics included in the manuscript.

```bash
cd paper
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

### Exporting to Word

```bash
./scripts/export_docx.sh
```

This uses pandoc with Vancouver-superscript CSL for bibliography formatting, and post-processes the output to number captions and bold table headers. Requires `python-docx` in the virtual environment.

## Supplementary Materials

- **S1**: Complete SubmodelTarget example (PSC proliferation)
- **S2**: Supported model types table
- **S3**: Validation checks with code examples (DOI, value-in-snippet, unit validators)
- **S4**: Generated Julia/Turing.jl code structure
- **S5**: Pydantic model definitions
- **S6**: SubmodelTarget schema details
- **S7**: Complete CalibrationTarget example
- **S8**: SubmodelTarget source characteristics
- **S9**: CalibrationTarget detailed metrics
- **S10**: Inference results
- **S11**: Model-aware prompt construction details
- **S12**: Schema implementation details
- **S13**: Source relevance assessment details
- **S14**: Collaboration mode details
- **S15**: Detailed comparison to existing approaches

## Related Repository

MAPLE (SubmodelTarget and CalibrationTarget schemas, validators, Julia translator) is implemented in [maple](https://github.com/popellab/maple).

## License

MIT
