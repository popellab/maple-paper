# Curation Analysis: LLM Output vs. Final Curated Targets

## File Organization

All extraction data is stored in `metadata_storage/` with a clean paired structure for diffing:

```
metadata_storage/
  submodel_targets/
    curated/              # 37 final curated SubmodelTarget files
    originals/            # 37 Logfire-sourced LLM originals (matching filenames)
  calibration_targets/
    curated/
      baseline_no_treatment/   # 31 curated CalibrationTargets
      clinical_progression/    # 1 curated CalibrationTarget
      gvax_nivo_neoadjuvant/   # 18 curated CalibrationTargets
    originals/                 # 22 Logfire-sourced LLM originals (gpt-5.1 subset)
  paper_extractions/      # 18 files from a separate LLM run (provenance archive)
  to-review/              # 2 files under review
```

Originals for the gpt-5.1 pipeline extractions were retrieved from Logfire traces using `pdac-build/scripts/extract_logfire_originals.py`, which queries the `agent run` span's `final_result` attribute for each file's `logfire_trace_id`. The 27 claude-opus-4-6 files do not have retrievable originals because they were extracted interactively (not through the instrumented pipeline); their first git commit is effectively their "original."

---

# Part 1: SubmodelTargets

## Data Sources

All 37 SubmodelTarget files were extracted by gpt-5.1 through the Logfire-instrumented pipeline and have populated `logfire_trace_id` fields. Using `extract_logfire_originals.py`, we retrieved the raw LLM output for all 37 files from their Logfire traces.

We also have three git/backup snapshots at different points:

| Source | Date | Files | Description |
|--------|------|-------|-------------|
| First git commit (`8a561e0`) | Jan 27 | 22 | Earliest committed versions (already partially curated) |
| Restic backup (`d90b88f8`) | Jan 31 | 22 | Same 22 files with minor edits (4 days of curation) |
| `paper_extractions/` (`7eec97d`) | Feb 3 (archived Feb 9) | 18 | A separate, fresh LLM extraction run (different from the curated run) |
| Current HEAD | Feb 19 | 37 | Final curated versions |

**Key finding**: The git-based analysis (first commit vs HEAD) understated curation because the first commits already had curation baked in. The Logfire originals reveal the true extent of human intervention.

## Original Extraction Attrition

The first LLM extraction pass produced 18 SubmodelTargets (`paper_extractions/`). Of those:

- **6 were dropped entirely**: `initial_tumour_diameter`, `k_ECM_apsc_sec`, `k_ECM_deg`, `k_ECM_qpsc_sec`, `k_psc_const`, `k_qpsc_death`, `n_Treg_clones`
- **12 were kept** as `deriv001` files, but most were substantially reworked (different source papers, different model types)
- The original and curated `deriv001` files share the same parameter name but often have **different `target_id` values**, indicating the source paper changed during curation

Additionally, **25 new derivations** (`deriv002` through `deriv007`) were added after the initial extraction, with no LLM original in `paper_extractions/`. These represent alternative data sources for the same parameter, discovered during expert review.

## Per-File Curation Metrics (Logfire original vs curated)

| File | Orig Lines | Cur Lines | % Changed |
|------|-----------|-----------|-----------|
| N_IL2_CD4_PDAC_deriv001 | 166 | 204 | 55.1% |
| N_IL2_CD8_PDAC_deriv001 | 169 | 281 | 53.3% |
| k_C1_growth_PDAC_deriv001 | 171 | 221 | 53.6% |
| k_C1_growth_PDAC_deriv002 | 210 | 229 | 45.8% |
| k_CCL2_sec_PDAC_deriv001 | 174 | 240 | 44.9% |
| k_CCL2_sec_PDAC_deriv002 | 134 | 202 | 42.6% |
| k_CCL2_sec_PDAC_deriv003 | 178 | 225 | 41.9% |
| k_CCL2_sec_PDAC_deriv004 | 198 | 237 | 37.0% |
| k_CCL2_sec_PDAC_deriv005 | 203 | 221 | 42.9% |
| k_M1_pol_PDAC_deriv001 | 132 | 199 | 64.4% |
| k_M1_pol_PDAC_deriv002 | 176 | 207 | 58.5% |
| k_M1_pol_PDAC_deriv003 | 299 | 293 | 45.3% |
| k_M1_pol_PDAC_deriv004 | 284 | 305 | 36.0% |
| k_M1_pol_PDAC_deriv005 | 212 | 223 | 39.3% |
| k_M1_pol_PDAC_deriv006 | 235 | 238 | 41.0% |
| k_M1_pol_PDAC_deriv007 | 207 | 208 | 43.1% |
| k_MDSC_rec_PDAC_deriv001 | 215 | 259 | 49.8% |
| k_MDSC_rec_PDAC_deriv002 | 241 | 309 | 46.4% |
| k_MDSC_rec_PDAC_deriv003 | 272 | 270 | 42.3% |
| k_MDSC_rec_PDAC_deriv004 | 197 | 216 | 46.0% |
| k_MDSC_rec_PDAC_deriv005 | 186 | 186 | 46.2% |
| k_MDSC_rec_PDAC_deriv006 | 190 | 204 | 42.6% |
| k_Mac_rec_PDAC_deriv001 | 205 | 260 | 48.0% |
| k_Mac_rec_PDAC_deriv002 | 313 | 320 | 44.1% |
| k_Mac_rec_PDAC_deriv003 | 199 | 222 | 46.3% |
| k_apsc_death_PDAC_deriv001 | 210 | 252 | 49.8% |
| k_apsc_death_PDAC_deriv002 | 173 | 200 | 55.0% |
| k_apsc_death_PDAC_deriv003 | 206 | 207 | 45.5% |
| k_psc_activation_PDAC_deriv001 | 165 | 215 | 52.4% |
| n_CD8_clones_PDAC_deriv001 | 177 | 217 | 56.3% |
| q_CD8_T_in_PDAC_deriv001 | 258 | 304 | 51.1% |
| q_CD8_T_in_PDAC_deriv002 | 216 | 225 | 58.5% |
| q_CD8_T_in_PDAC_deriv003 | 273 | 298 | 44.0% |
| q_Treg_T_in_PDAC_deriv001 | 160 | 218 | 58.7% |
| q_Treg_T_in_PDAC_deriv002 | 249 | 296 | 51.6% |
| q_Treg_T_in_PDAC_deriv003 | 281 | 325 | 48.5% |
| q_Treg_T_in_PDAC_deriv004 | 442 | 403 | 38.7% |

**Average change: 47.7%** (range: 36.0% -- 64.4%). Every file was substantially curated.

## Corrected Summary Statistics

| Category | Count | % of 37 |
|----------|-------|---------|
| No curation (0% changed) | 0 | 0% |
| Light curation (<40% changed) | 6 | 16% |
| Moderate curation (40-50% changed) | 19 | 51% |
| Heavy curation (>50% changed) | 12 | 32% |

### Correction from git-based analysis

The earlier git-based analysis (first commit vs HEAD) showed 30% of files needed no curation. This was misleading: the first git commits already contained partially curated files, not raw LLM output. The Logfire traces reveal that **all 37 files required substantial curation**, with changes ranging from 36% to 64% of lines.

| Metric | Git-based (first commit vs HEAD) | Logfire-sourced (LLM output vs curated) |
|--------|----------------------------------|----------------------------------------|
| Average % changed | ~12% | 47.7% |
| Files with 0% change | 11 (30%) | 0 (0%) |
| Files with >20% change | 7 (19%) | 37 (100%) |

The git-based metrics accurately measured the *post-commit* refinement phase but missed the larger initial curation that happened before the first commit.

## Patterns

### Uniform curation regardless of derivation number

Unlike what the git-based analysis suggested, later derivations (deriv003+) were NOT used as-is. The Logfire data shows they required 36-46% curation, similar to early derivations (44-65%). The earlier git analysis showing 0% change for late derivations simply reflected that all curation happened before the first commit.

### Schema evolution drove some curation

The curated versions frequently use structured forward model types (algebraic, batch_accumulation, steady_state_density) where the LLM originals used `direct_conversion` (custom code). This reflects schema evolution during the project, not purely LLM error. However, even files that kept the same model type showed 36-58% change.

### Common edit categories

Across all 37 files, recurring curation patterns include:
- Rewritten rationale and assumptions (more precise biological language)
- Adjusted prior widths and distributions
- Changed forward model type (schema migration)
- Revised identifiability notes
- Fixed observation/distribution code
- Changed source papers (different target_id)

### Source paper changes

Comparing `paper_extractions/` originals to curated `deriv001` files: most have different `target_id` values, indicating the expert selected a different source paper during curation. The LLM found a relevant paper, but the expert often preferred a different one (e.g., more directly applicable species, better experimental design, or more recent data).

---

# Part 2: CalibrationTargets

## Data Sources

CalibrationTarget files live in `pdac-build/calibration_targets/`, organized into scenario subdirectories. Curated copies are archived in `metadata_storage/calibration_targets/curated/`.

| Subdirectory | Files | Description |
|-------------|-------|-------------|
| `baseline_no_treatment/` | 31 | Diagnosis-state TME observables (IHC densities, ratios, fractions) |
| `gvax_nivo_neoadjuvant/` | 18 | Treatment-arm day-21 immune readouts from Li 2022 |
| `clinical_progression/` | 1 | Tumor doubling time |
| **Total** | **50** | |

## Extraction Model Breakdown

| Extraction Model | Files | Logfire Trace | Collaboration Mode |
|-----------------|-------|---------------|-------------------|
| gpt-5.1 | 22 | Populated trace IDs | Batch pipeline extraction, then interactive curation with Claude Code |
| claude-opus-4-6 | 27 | Blank trace IDs | Interactive extraction+curation with Claude Code using source PDFs |
| manually-curated | 1 | None | `tumor_pO2_baseline` (hand-written) |

The gpt-5.1 files were extracted through the Logfire-instrumented automated pipeline, then curated interactively with Claude Code. The claude-opus-4-6 files were extracted directly in Claude Code sessions with the source PDFs loaded from `pdac-build/calibration_targets/sources/`, where the expert and LLM collaborated on extraction and curation simultaneously.

**Important**: All curation across the entire project (both SubmodelTargets and CalibrationTargets) was performed interactively with Claude Code. The distinction is not "automated vs. manual" but rather the sequencing: batch extraction followed by interactive curation (gpt-5.1) vs. unified interactive extraction+curation (claude-opus-4-6).

## Original vs. Curated Comparison (Logfire-sourced, gpt-5.1 files)

Using `extract_logfire_originals.py`, we retrieved the raw LLM output for all 22 gpt-5.1 CalibrationTargets. Originals are in `metadata_storage/calibration_targets/originals/`.

| File | Orig Lines | Cur Lines | % Changed |
|------|-----------|-----------|-----------|
| apcaf_fraction_of_caf | 164 | 213 | 57.3% |
| cd8_density_baseline | 243 | 327 | 50.5% |
| cd8_exhausted_fraction | 204 | 244 | 59.8% |
| cd8_fold_increase_gvax_nivo_d21 | 232 | 274 | 54.5% |
| cdc1_density_baseline | 217 | 264 | 55.7% |
| cdc1_fraction_of_dc | 200 | 250 | 49.3% |
| collagen1_protein_level | 253 | 290 | 51.2% |
| hif1a_positivity_rate | 180 | 218 | 60.8% |
| m1_m2_ratio | 198 | 266 | 47.6% |
| major_pathologic_response_rate_gvax_nivo | 200 | 235 | 60.2% |
| nk_fraction_of_tils | 148 | 197 | 59.1% |
| psc_activation_ratio | 254 | 248 | 53.6% |
| stromal_fraction | 156 | 367 | 62.1% |
| tam_to_cdc1_ratio | 226 | 246 | 57.2% |
| th_exhausted_fraction | 201 | 222 | 53.0% |
| treg_fraction_baseline | 173 | 215 | 62.6% |
| treg_fraction_gvax_nivo_d21 | 144 | 230 | 54.3% |
| tumor_doubling_time | 182 | 221 | 50.6% |
| tumor_glucose_ratio | 206 | 262 | 56.8% |
| tumor_lactate_fold_change | 194 | 244 | 50.9% |
| tumor_volume_resection | 196 | 321 | 65.4% |
| vegf_tissue_concentration | 198 | 238 | 51.1% |

**Average change: 55.6%** (range: 47.6% -- 65.4%). Every file was substantially reworked. The curated versions are on average 26% larger (total 5569 vs 4369 lines).

## Attrition and New Targets

| Category | Count | % of 50 |
|----------|-------|---------|
| Batch pipeline extraction (gpt-5.1) | 22 | 44% |
| Interactive extraction (claude-opus-4-6) | 27 | 54% |
| Manually written (no LLM) | 1 | 2% |

All 49 LLM-extracted files were curated interactively with Claude Code.

**4 dropped targets** (extracted but not carried forward):
1. `arginase_concentration` -- not in current model structure
2. `asma_positive_area` -- alpha-SMA area, superseded by PSC activation ratio
3. `collagen_content_total` -- superseded by `collagen1_protein_level` (more specific)
4. `maximum_tumor_burden` -- not used as calibration target

## Expert Review Process

A detailed review document (`pdac-build/calibration_targets/sources/review.md`) captures the curation of a Feb 17 extraction batch (12 files from 3 gpt-5.1 batch runs):

| Outcome | Count | % |
|---------|-------|---|
| **Rejected** | 7 | 58% |
| **Accepted** | 5 | 42% |

**Rejection reasons** (rich expert judgment):
- 2 placeholder/no-data outputs (LLM couldn't access paper, returned dummy values)
- 1 parse error (corrupted output)
- 1 mislabeled (computed fraction but named as density)
- 1 superseded (scRNA-seq estimate inferior to IHC with patient-level variability)
- 1 contradictory (order-of-magnitude disagreement with accepted source)
- 1 too many conversion assumptions (volumetric vs areal density mismatch)

**Accepted files** required fixes before promotion:
- Fill empty `source_relevance` sections
- Correct `experimental_denominator` text (FOXP3+ mislabeled as conventional Th)
- Noted caveats for weak accepts (e.g., CD1a not specific to cDC1)

This 58% rejection rate on a single batch demonstrates that expert review is essential.

## Interactive Claude Code Extractions (27 files)

The remaining 27 CalibrationTargets were extracted interactively with Claude Code (claude-opus-4-6) rather than through the automated pipeline. In these sessions, the expert loaded source PDFs directly into Claude Code from `pdac-build/calibration_targets/sources/` and collaboratively built each YAML file, with the expert providing domain guidance (species mapping, denominator definitions, distribution choices) and Claude handling literature comprehension, data extraction, and code generation in real time.

### Breakdown by scenario

| Subdirectory | Claude-extracted | gpt-5.1 | Manual |
|-------------|:---:|:---:|:---:|
| `baseline_no_treatment/` | 12 | 18 | 1 |
| `gvax_nivo_neoadjuvant/` | 15 | 3 | 0 |
| `clinical_progression/` | 0 | 1 | 0 |
| **Total** | **27** | **22** | **1** |

Most of the gvax_nivo_neoadjuvant treatment targets (15/18) were Claude-extracted. These derive from Li et al. (Cancer Cell 2022) scatter plots that required manual digitization, documented in `sources/li2022_digitization_results.md` and `sources/cd8t_nonLA_tumor.csv`.

### Post-commit curation

| Metric | Value |
|--------|-------|
| Total files | 27 |
| Total lines (all files) | 7,395 |
| Mean file size | 274 lines (range 182--426) |
| Files with zero post-commit changes | 20 (74%) |
| Files with any post-commit changes | 7 (26%) |
| Total lines changed post-commit | 28 (0.19% of all lines) |

The 7 changed files all received the same single edit: updating `pdac_cellularity_fraction` from 0.25 to 0.15 in the `model_context_parameters` section (commit `4271302`). This was a shared reference value correction, not a per-file extraction error.

### Interpretation

The near-zero post-commit curation does **not** mean these files required less human input than the gpt-5.1 pipeline extractions. It means the human input was folded into the extraction process itself. In the interactive mode:

1. The expert read the source paper alongside Claude, guiding which data to extract
2. Observable code was written collaboratively, with the expert specifying species mappings and denominator definitions
3. Distribution code was iterated until the expert was satisfied with the uncertainty quantification
4. Source relevance assessments were discussed and finalized before the file was committed

The supporting documentation in `sources/` illustrates this interactive workflow:
- `li2022_digitization_results.md` -- tabulated digitization of scatter plot data points, with pooled arm-level statistics and bootstrap CIs
- `ogawa2021_ccr_digitization_results.md` -- pixel-level desmoplastic element proportions from multiplex IHC
- `parameter_audit.md` -- a systematic audit of 175 model prior parameters, organized by concern level (red flags, yellow flags, minor concerns)
- `initialization_to_calibration_review.md` -- discussion of calibration strategy (evolution-to-diagnosis vs. direct IC setting)

These documents are Claude Code session transcripts, showing the expert-AI collaboration that produced the YAML files.

### Two collaboration modes

| | Batch pipeline (gpt-5.1) | Interactive (claude-opus-4-6) |
|--|--|--|
| **Extraction** | Automated, no expert input | Expert-guided, real-time |
| **Curation** | Post-hoc, interactive with Claude Code | Embedded in extraction |
| **Post-commit change** | 55.6% average | 0.19% average |
| **Total human effort** | Comparable | Comparable |
| **Files per session** | Many (batch) | Few (deep) |
| **Failure mode** | 58% rejection rate on review | Prevented during extraction |

The batch pipeline is more efficient for initial coverage (many files per run) but requires substantial post-extraction curation. The interactive mode produces near-final quality on first commit but requires deeper per-file engagement. Both modes are LLM-augmented; the difference is when the human judgment enters the workflow.

---

# Part 3: Combined Analysis

## Side-by-Side Comparison

| Metric | SubmodelTargets | CalibrationTargets (gpt-5.1) | CalibrationTargets (Claude) |
|--------|:-:|:-:|:-:|
| Total curated files | 37 | 22 | 27 (+1 manual) |
| Collaboration mode | Batch extract, then interactive curate | Batch extract, then interactive curate | Interactive extract+curate |
| Average post-extraction curation | 47.7% | 55.6% | 0.19% |
| Range | 36.0% -- 64.4% | 47.6% -- 65.4% | 0% -- 0.4% |
| Files requiring no curation | 0 (0%) | 0 (0%) | 20 (74%) |
| Review rejection rate | Unknown | 58% (documented batch) | N/A (prevented during extraction) |

**Key finding**: The batch pipeline extractions (gpt-5.1) required 48-56% post-extraction curation regardless of schema type. The interactive Claude extractions show near-zero post-commit change because curation was embedded in the extraction process. All three workflows are LLM-augmented: all curation was performed interactively with Claude Code. The meaningful distinction is not "automated vs. manual" but when expert judgment enters the loop.

## Edit Classification by Category

Using `difflib.SequenceMatcher` on each original/curated pair, we classified every changed line by the YAML section it belongs to, then grouped into semantic categories. This reveals *what kind of expert judgment* drove the curation.

### SubmodelTarget edit breakdown (n=37, 15,017 changed lines)

| Category | Lines | % of total |
|----------|------:|-----------:|
| Input data (values, snippets, sources) | 4,356 | 29.0% |
| Text & rationale (interpretation, assumptions, limitations, identifiability) | 3,581 | 23.8% |
| Model structure (forward model type, state variables, error model) | 1,971 | 13.1% |
| Data sources / references | 1,376 | 9.2% |
| Prior & likelihood (distribution params, bounds) | 1,362 | 9.1% |
| Source relevance (applicability assessment) | 738 | 4.9% |
| Experimental context (species, system, culture) | 730 | 4.9% |
| Metadata & formatting (tags, trace IDs, YAML style) | 394 | 2.6% |
| Code (compute / observation functions) | 392 | 2.6% |
| Other | 117 | 0.8% |

Notable: 65% of files (24/37) had their forward model type changed (e.g., `direct_conversion` to `algebraic`, `batch_accumulation`, or `steady_state_*`). 95% (35/37) had observation code changes. 100% had prior distribution adjustments.

### CalibrationTarget edit breakdown (n=22, 9,391 changed lines)

| Category | Lines | % of total |
|----------|------:|-----------:|
| Empirical data & distribution (inputs, distribution code, CI values) | 4,377 | 46.6% |
| Observable code & structure (species mapping, denominator, constants) | 1,793 | 19.1% |
| Text & rationale (interpretation, assumptions, limitations) | 1,313 | 14.0% |
| Experimental context (species, system, culture) | 718 | 7.6% |
| Scenario configuration | 378 | 4.0% |
| Data sources / references | 334 | 3.6% |
| Metadata & formatting | 203 | 2.2% |
| Source relevance | 180 | 1.9% |
| Other | 95 | 1.0% |

### High-level grouping

Collapsing into three interpretive categories:

| Group | SubmodelTargets | CalibrationTargets | What it represents |
|-------|:-:|:-:|---|
| **Scientific content** | 52% | 52% | Data values, priors, source papers, relevance assessments |
| **Narrative & documentation** | 29% | 22% | Rationale text, assumptions, limitations, experimental context |
| **Structural & technical** | 16% | 23% | Schema migration, code, observable structure, scenario config |
| **Metadata & formatting** | 3% | 2% | Tags, trace IDs, YAML formatting |

The most striking finding is that **scientific content changes account for exactly 52% of all edits in both schema types**, despite the different overall curation rates (48% for SMT, 56% for CT). This means:

- The LLM produces a structurally correct scaffold with reasonable literature identification
- The expert contributes domain-specific judgment: adjusting data values, widening/narrowing priors, selecting different source papers, and assessing relevance
- Roughly a quarter of changes are narrative refinement (more precise biological language, better-justified assumptions)
- Technical/structural changes (16-23%) reflect schema evolution during the project rather than LLM error

The low code change percentage for SubmodelTargets (2.6%) reflects the success of structured forward model types: rather than editing handwritten code, experts select a model type and the framework generates the code. CalibrationTargets show higher structural change (19%) because observable code (mapping model species to experimental measurements) requires deep domain knowledge that the LLM frequently gets wrong (incorrect denominators, missing area corrections, wrong species sums).

## What This Means for the Paper

The curation data supports the narrative that MAPLE is a **human-AI collaboration tool**, not a fully automatic pipeline.

### Batch pipeline mode (59 files: 37 SMT + 22 CT)

The consistent 48-56% post-extraction curation rate across both schema types means:

1. **The LLM provides ~50% of the final content** -- a meaningful starting scaffold that includes correct overall structure, literature identification, and approximate parameter values
2. **Expert judgment contributes the other ~50%** -- half of which is scientific content (data, priors, sources) and half narrative refinement (rationale, assumptions)
3. **No extraction was used as-is** -- this is important for credibility, as it shows the framework doesn't encourage blind acceptance of LLM output
4. **Code is NOT the main bottleneck** -- only 2.6% of SubmodelTarget changes and 19% of CalibrationTarget changes involve code, because structured forward model types handle the common patterns

The CalibrationTarget rejection rate (58% in the documented batch) further demonstrates that the schema enables systematic quality control that would be difficult with unstructured free-text outputs.

### Interactive mode (27 files)

The near-zero post-commit curation rate for the interactive Claude extractions tells a complementary story:

1. **Expert-in-the-loop extraction produces near-final quality** -- when the domain expert guides the extraction in real time, the output converges to publication quality before the first commit
2. **The schema still structures the collaboration** -- even in interactive mode, the YAML schema provides the scaffold that the expert and LLM fill in together, ensuring completeness and consistency
3. **Figure digitization and complex observables benefit from interactivity** -- 15 of the 27 files involved digitizing scatter plots from Li et al. 2022, where the expert directed Claude through the figure interpretation, pooling strategy, and bootstrap uncertainty quantification
4. **The supporting documentation is itself a product of the collaboration** -- parameter audits, digitization tables, and calibration strategy discussions were generated in the same Claude Code sessions

### Across both modes

All curation was performed interactively with Claude Code. The framework supports both batch-then-curate and interactive-extraction workflows, with the schema providing structure in either case. The batch mode is more scalable (many files per run), while the interactive mode produces higher first-pass quality for complex targets requiring figure digitization, multi-source synthesis, or deep domain reasoning.

## Restic Backup Timeline

### SubmodelTargets

| Snapshot | Date | YAML files in metadata_storage/ |
|----------|------|---------------------------------|
| `d90b88f8` | Jan 31 | 22 |
| `94e06809` | Feb 4 | 22 |
| `7576503a` | Feb 5 | 22 |
| `8889764f` | Feb 11 | 37 |
| `bb327700` | Feb 19 | 37 |

The 22 to 37 jump (15 new files) happened between Feb 5-11, corresponding to the addition of structured forward model types and the covariate expansion extraction run.

### CalibrationTargets

| Snapshot | Date | CalibrationTargets in pdac-build |
|----------|------|----------------------------------|
| `d90b88f8` | Jan 31 | 0 (pdac-build doesn't exist yet) |
| `94e06809` | Feb 4 | 0 |
| `8cd7268d` | Feb 16 | 0 (pdac-build exists, no calibration_targets/) |
| `e4a94f62` | Feb 17 | 52 entries (32 baseline + 18 gvax + sources) |
| `bb327700` | Feb 19 | 69 entries (+clinical_progression subdirectory) |

## TODO

- [x] Query Logfire traces for the 22 gpt-5.1 CalibrationTargets to retrieve original LLM outputs
- [x] Query Logfire traces for all 37 SubmodelTargets to get true original-vs-curated diffs
- [x] Correct SubmodelTarget metrics (git-based analysis understated curation)
- [x] Organize originals + curated in paired directory structure for easy diffing
- [x] Classify edits by type (rationale text vs. numeric values vs. observable code vs. distribution params)
- [x] Characterize the 27 claude-opus-4-6 CalibrationTarget extractions