# Collaborator Onboarding Guide

Welcome to the QSP-LLM-Workflows project! This guide will help you get started with the codebase and understand how to contribute to the paper.

## Project Overview

This project provides LLM-powered workflows for extracting and standardizing QSP parameter metadata from scientific literature. The key innovation is using **template-guided LLM extraction** to achieve both rigorous standardization AND efficient automation.

**The Problem We're Solving:**
- QSP models require 100+ parameters from diverse literature
- Manual curation is ad-hoc, poorly documented, time-intensive
- Parameters propagate across models without provenance ("telephone game" effect)
- Reviewers can't easily verify parameter sources

**Our Solution:**
- Structured YAML templates enforce standardization
- LLMs automate extraction while maintaining quality
- Complete audit trail from literature to final values
- Expected speedup and quality improvements (to be measured in validation study)

---

## Repository Organization

**This repository (`qsp-llm-workflows`):**
- General-purpose LLM workflow tools for parameter extraction
- Reusable across any QSP model or disease area
- Focus: Core extraction, validation, and storage workflows

**Paper repository (`qsp-llm-workflows-paper`, to be created):**
- Paper-specific code, validation analyses, and figures
- Validation study comparing LLM vs. expert curation
- Manuscript-ready figures and statistical analyses
- Focus: Reproducible research for publication

**Benefits of this separation:**
- Keeps this repo clean and focused on reusable tools
- Paper-specific work doesn't clutter the general-purpose codebase
- Easier for others to adopt these workflows for their own models

**Note:** The manuscript documentation (this onboarding guide, presentation, paper outline) is shared via email and not checked into either repository.

---

## Quick Start

### 1. Environment Setup

```bash
# Clone the repository (if you haven't already)
cd /path/to/qsp-llm-workflows

# Activate Python virtual environment
source venv/bin/activate

# Install dependencies (if needed)
pip install -r requirements.txt
```

### 2. API Key Configuration

Create a `.env` file in the project root with your OpenAI API key:

```bash
# .env file
OPENAI_API_KEY=sk-your-api-key-here
```

### 3. Sister Repository Setup

This project writes outputs to the `qsp-metadata-storage` repository:

```bash
# Clone as sibling directory
cd ..
git clone [qsp-metadata-storage-url]
cd qsp-llm-workflows
```

Expected directory structure:
```
parent-directory/
├── qsp-llm-workflows/       # This repo (code + workflows)
└── qsp-metadata-storage/    # Storage repo (YAML outputs)
    ├── parameter_estimates/
    ├── quick_estimates/
    └── test_statistics/
```

---

## Repository Architecture

### Directory Structure

```
qsp-llm-workflows/
├── scripts/
│   ├── prepare/          # Create batch requests
│   ├── run/              # Execute batches via OpenAI API
│   ├── process/          # Extract and unpack results
│   ├── lib/              # Core libraries
│   ├── debug/            # Debug and inspection tools
│   └── matlab/           # MATLAB integration scripts
├── prompts/              # Base prompt templates
├── templates/            # YAML schemas and examples
│   ├── configs/          # Prompt assembly configuration
│   └── examples/         # Worked examples for LLM
├── data/                 # Input parameter lists and context
├── batch_jobs/           # Batch API requests/results (gitignored)
└── docs-manuscript/      # Paper collaboration materials (gitignored, shared via email)
```

### Key Components

**Modular Prompt Assembly System** (`scripts/lib/prompt_assembly.py`):
- Combines base prompts + templates + examples + parameter context
- Configurable via `templates/configs/prompt_assembly.yaml`
- Ensures consistent, structured LLM outputs

**Batch Creator Classes** (`scripts/lib/batch_creator.py`):
- Base class `BatchCreator` with common functionality
- Specialized subclasses: `ParameterBatchCreator`, `QuickEstimateBatchCreator`, etc.
- CLI scripts in `scripts/prepare/` provide simple interfaces

**Parameter Utilities** (`scripts/lib/parameter_utils.py`):
- CSV loading and parameter list processing
- Model context generation from `data/model_context.csv`

---

## Core Workflows

We have three main workflows, each producing different types of metadata:

### Workflow 1: Parameter Extraction (Comprehensive)

**Purpose**: Extract detailed parameter metadata with full provenance, uncertainty, and biological context.

**Input**: CSV with `cancer_type` and `parameter_name` columns

**Outputs**: YAML files in `../qsp-metadata-storage/parameter_estimates/` with:
- Numerical values and uncertainty (distributions, CI, sample sizes)
- Biological context (species, cell types, disease state)
- Experimental conditions (assay type, time points, treatments)
- Statistical distributions with R bootstrap code
- Literature provenance (DOI, figures, page numbers)
- Cross-study pooling metadata

**Example workflow**:
```bash
# 1. Create batch requests
python scripts/prepare/create_parameter_batch.py data/my_parameters.csv

# 2. Upload to OpenAI Batch API
python scripts/run/upload_batch.py batch_jobs/parameter_requests.jsonl

# 3. Monitor batch progress
python scripts/run/batch_monitor.py batch_<id>

# 4. Download and unpack results
python scripts/process/unpack_results.py \
  batch_jobs/batch_<id>_results.jsonl \
  ../qsp-metadata-storage/parameter_estimates \
  data/my_parameters.csv \
  "" \
  templates/parameter_metadata_template.yaml
```

**Output naming**: `{param_name}_{author_year}_{cancer_type}_{hash}.yaml`

---

### Workflow 2: Quick Estimates

**Purpose**: Rapid parameter initialization for early-stage model testing.

**Input**: CSV with `cancer_type` and `parameter_name` columns

**Outputs**: YAML files with ballpark estimates, ranges, and brief rationale

**Example workflow**:
```bash
# 1. Create batch requests
python scripts/prepare/create_quick_estimate_batch.py data/my_parameters.csv

# 2. Upload and monitor (same as above)
python scripts/run/upload_batch.py batch_jobs/quick_estimate_requests.jsonl
python scripts/run/batch_monitor.py batch_<id>

# 3. Unpack results
python scripts/process/unpack_results.py \
  batch_jobs/batch_<id>_results.jsonl \
  ../qsp-metadata-storage/quick_estimates \
  data/my_parameters.csv

# 4. Aggregate across multiple sources
python ../qspio-pdac/metadata/aggregate_quick_estimates.py \
  data/my_parameters.csv \
  ../qsp-metadata-storage/quick_estimates \
  output/
```

**Output naming**: `{param_name}_{cancer_type}_{hash}_deriv{N}.yaml`

---

### Workflow 3: Test Statistics

**Purpose**: Create validation targets with uncertainty quantification from experimental data.

**Input**: CSV with `test_statistic_id`, `scenario_context`, `required_species`, `derived_species_description`

**Outputs**: YAML files with test statistics, distributions, and R bootstrap code

**Example workflow**:
```bash
# 1. Create batch requests
python scripts/prepare/create_test_statistic_batch.py data/test_stats.csv

# 2. Upload and monitor
python scripts/run/upload_batch.py batch_jobs/test_statistic_requests.jsonl
python scripts/run/batch_monitor.py batch_<id>

# 3. Unpack results
python scripts/process/unpack_results.py \
  batch_jobs/batch_<id>_results.jsonl \
  ../qsp-metadata-storage/test_statistics \
  data/test_stats.csv \
  "" \
  templates/test_statistic_template.yaml

# 4. Aggregate distributions
python ../qspio-pdac/metadata/aggregate_test_statistics.py \
  data/test_stats.csv \
  ../qsp-metadata-storage/test_statistics \
  ../qsp-metadata-storage/scratch/
```

**Output naming**: `{test_stat_id}_{cancer_type}_{hash}.yaml`

---

## Key Concepts

### 1. Template-Guided Extraction

Templates define the structure LLMs must produce. Example template snippet:

```yaml
parameter_name: ""  # Required: canonical name
parameter_estimate:
  value: 0.0        # Required: central estimate
  unit: ""          # Required: with proper notation
  type: ""          # normal | lognormal | uniform
```

Templates ensure:
- Consistent field names across all extractions
- Required metadata is always captured
- Outputs are machine-parsable (YAML format)

### 2. Modular Prompt Assembly

Prompts are built dynamically from components:
- **Base prompt**: Task instructions, formatting rules
- **Template**: YAML structure to fill
- **Examples**: Previously completed extractions
- **Parameter context**: Definitions, model roles, units

Configuration in `templates/configs/prompt_assembly.yaml` controls which components are included.

### 3. Batch Processing Model

We use OpenAI's Batch API for cost-effective, high-volume processing:
- Submit JSONL file with multiple requests
- Batch processes asynchronously (12-24 hours typical)
- 50% cost reduction vs. real-time API
- Custom IDs enable result tracking: `{cancer_type}_{param_name}_{index}`

For quick testing, use `upload_immediate.py` for synchronous responses.

### 4. Quality Control: LLM Review + Expert Validation

**Two-stage validation**:
1. **Automated LLM reviewer**: Secondary LLM performs 54-item checklist validation
   - Citation accuracy, hallucination detection
   - Statistical method appropriateness
   - Formatting compliance (LaTeX, units, JSON escaping)
   - Returns corrected JSON with review summary
2. **Expert review**: Human validates scientific accuracy and plausibility
   - Focus on high-level decisions flagged by automated review

### 5. Flat-File YAML Storage

All outputs stored as individual YAML files in `qsp-metadata-storage`:
- Version controlled with git
- Human-readable diffs
- Easy to browse and inspect
- No database dependencies

### 6. Validation Strategy: Legacy Database Comparison

**Key Resource:**
An extensive database of manually-curated parameters from prior QSP models exists in legacy YAML format. This database serves as our primary validation ground truth.

**Primary validation approach:**
- Compare LLM-extracted PDAC parameters against legacy manual curations (50-100+ overlapping parameters)
- Metrics: Value agreement, uncertainty consistency, metadata completeness, extraction accuracy
- No new expert curation required for large-scale validation

**Secondary benefits:**
- Contextualize PDAC parameters within broader QSP landscape
- Identify parameter patterns and coverage gaps across models
- Cross-model parameter variability characterization

**Complementary validation (optional):**
- Expert comparison for gap parameters not in legacy database
- Downstream model performance testing if PDAC model ready

This validation approach enables large-scale accuracy testing without the time/cost burden of new expert curation, while also providing cross-model insights as a secondary benefit.

---

## Common Tasks

### Task 1: Run Parameter Extraction for New Parameters

1. Create input CSV with columns: `cancer_type`, `parameter_name`
2. Run workflow (see Workflow 1 above)
3. Check outputs in `../qsp-metadata-storage/parameter_estimates/`
4. Review extractions for accuracy

### Task 2: Inspect Batch Request/Response Files

```bash
# View request prompts
python scripts/debug/inspect_jsonl.py batch_jobs/parameter_requests.jsonl

# View batch results
python scripts/debug/inspect_jsonl.py batch_jobs/batch_<id>_results.jsonl

# Extract a specific prompt
python scripts/debug/extract_prompt.py batch_jobs/parameter_requests.jsonl custom_id_here
```

### Task 3: Monitor Batch Progress

```bash
# Check status and download when complete
python scripts/run/batch_monitor.py batch_<id>

# Batch states: validating → in_progress → completed → downloaded
```

### Task 4: Test Prompt Changes

For rapid iteration on prompt design:

```bash
# Use immediate API instead of batch
python scripts/run/upload_immediate.py batch_jobs/test_requests.jsonl

# Results returned in seconds (but costs 2x more)
```

---

## Development Workflow

### Git Practices

**Branches**:
- `main`: Stable production code
- Feature branches: `feature/description` or `fix/description`

**Commits**:
- Use descriptive commit messages
- Claude Code will offer to commit changes for you
- Review diffs before committing

**Common operations**:
```bash
# Check status
git status

# Create feature branch
git checkout -b feature/new-workflow

# Commit changes
git add file1.py file2.py
git commit -m "Add new workflow for X"

# Push to remote
git push -u origin feature/new-workflow
```

### Testing Changes

**Before committing**:
1. Test script with small input (1-2 parameters)
2. Verify output YAML structure
3. Check for errors in logs
4. Validate against template schema

**Debugging tools**:
- `scripts/debug/inspect_jsonl.py`: View batch files
- `scripts/debug/pretty_print_csv.py`: Format CSV output
- Python debugger: `import pdb; pdb.set_trace()`

### Code Standards

From `CLAUDE.md`:
- **No backward compatibility**: Clean, modern interfaces
- **Class-focused architecture**: Prefer classes over functions
- **No main blocks in libraries**: Only in CLI scripts
- **Explicit interfaces**: Require all necessary arguments

---

## Paper Collaboration Plan

### Current Status

✅ **Completed**:
- Core workflows implemented and prototyped (~20 parameters trialed)
- YAML templates finalized (v2 schema)
- Modular prompt assembly system
- LLM review system (54-item checklist)
- Flat-file storage system in `qsp-metadata-storage`
- Legacy parameter database from prior QSP models (validation ground truth)

🚧 **In Progress**:
- Validation study design and execution
- Case studies and example extractions

📋 **Remaining Work**:
- Database comparison validation (50-100+ parameters)
- Complementary validation (expert comparison, model performance)
- Generate figures and tables for paper
- Write manuscript sections
- Prepare supplementary materials
- Code/data release preparation

### Division of Labor (To Discuss)

**Primary Validation (Database Comparison)**:
- [ ] Align LLM-extracted PDAC parameters with legacy YAML database
- [ ] Compute validation metrics (value agreement, uncertainty consistency, metadata completeness)
- [ ] Statistical analysis scripting
- [ ] Secondary analysis: Contextualize PDAC within broader QSP landscape

**Complementary Validation (Optional)**:
- [ ] Expert manual curation for gap parameters (not in legacy database)
- [ ] Time tracking and efficiency metrics
- [ ] Model performance testing (if PDAC model ready)

**Analysis & Figures**:
- [ ] Validation scatter plots (LLM vs. database)
- [ ] Metadata quality comparison across six dimensions
- [ ] Cross-model parameter landscape visualization
- [ ] Workflow diagram and schema visualization

**Writing**:
- [ ] Methods: Template schema design
- [ ] Methods: LLM workflow description
- [ ] Results: Database validation metrics
- [ ] Results: PDAC parameter landscape contextualization
- [ ] Discussion: Accuracy, reproducibility, generalizability

**Supplementary Materials**:
- [ ] Complete template specifications
- [ ] LLM reviewer checklist documentation
- [ ] Code repository preparation
- [ ] Example extractions with annotations

### Timeline (To Discuss)

**Week 1-3**: Database comparison validation (align extractions, compute metrics, contextualize)
**Week 4-5**: Complementary validation (if needed)
**Week 6-7**: Analysis and figure generation
**Week 8-9**: Manuscript drafting
**Week 10**: Revisions and submission prep

---

## Getting Help

### Documentation

- `CLAUDE.md`: Instructions for Claude Code when working with this repo
- `README.md`: High-level project overview
- `docs-manuscript/`: Paper collaboration materials (gitignored, shared via email)

### Debugging

If something goes wrong:
1. Check script output for error messages
2. Use `scripts/debug/inspect_jsonl.py` to examine batch files
3. Verify `.env` file has valid API key
4. Ensure `qsp-metadata-storage` is in expected location
5. Check Python environment is activated

### Common Issues

**"No module named X"**: Activate virtual environment (`source venv/bin/activate`)

**"API key not found"**: Check `.env` file exists and has `OPENAI_API_KEY=...`

**"Batch ID not found"**: Make sure `.batch_id` file exists or provide full batch ID

**"Cannot write to ../qsp-metadata-storage"**: Verify sister repo is cloned

---

## Next Steps

### For New Collaborators

1. ✅ Read this document
2. ✅ Set up environment and test a small extraction
3. ✅ Attend presentation/discussion tomorrow
4. ⬜ Decide on your role in the collaboration
5. ⬜ Identify specific tasks to tackle first

### Immediate Actions

**Today/Tomorrow**:
- Review paper outline (shared via email: `paper_outline_standardization.md`)
- Explore existing extractions in `../qsp-metadata-storage/`
- Try running a quick estimate workflow on a test parameter
- Prepare questions for group discussion

**This Week**:
- Finalize validation study design
- Assign paper sections and figure responsibilities
- Set up regular collaboration meetings
- Create shared task tracking (GitHub issues, project board)

---

## Resources

### Key Files to Read

1. `CLAUDE.md`: Comprehensive codebase documentation
2. `paper_outline_standardization.md`: Complete paper outline (shared via email)
3. `templates/parameter_metadata_template.yaml`: Example of our schema
4. `prompts/parameter_prompt.md`: See how we prompt the LLM

### Example Extractions

Look at actual outputs in `../qsp-metadata-storage/parameter_estimates/` to see:
- Complete metadata structure
- Literature provenance tracking
- Statistical distribution specifications
- R bootstrap code generation

### Further Reading

- OpenAI Batch API: https://platform.openai.com/docs/guides/batch
- YAML specification: https://yaml.org/spec/
- Our target journal: CPT Pharmacometrics & Systems Pharmacology

---

**Welcome aboard! We're excited to collaborate with you on this project.**

Questions? Let's discuss tomorrow!
