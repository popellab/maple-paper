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

Originals were extracted from Logfire traces using `pdac-build/scripts/extract_logfire_originals.py`, which queries the `agent run` span's `final_result` attribute for each file's `logfire_trace_id`.

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

| Extraction Model | Files | Logfire Trace | Notes |
|-----------------|-------|---------------|-------|
| gpt-5.1 | 22 | Populated trace IDs | Run through instrumented pipeline |
| claude-opus-4-6 | 27 | Blank trace IDs | Run outside Logfire-instrumented pipeline |
| manually-curated | 1 | None | `tumor_pO2_baseline` (hand-written) |

All gpt-5.1 extractions have populated Logfire trace IDs; all claude-opus-4-6 extractions have blank traces.

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
| Has LLM original (Logfire gpt-5.1) | 22 | 44% |
| Has LLM original (to-review Claude batch) | 18 | 36% |
| New target, no LLM starting point | 13 | 26% |
| Manually curated (no LLM) | 1 | 2% |

Note: 18 of the to-review originals overlap with the Logfire gpt-5.1 originals; some curated files have originals from both runs.

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

---

# Part 3: Combined Analysis

## Side-by-Side Comparison

| Metric | SubmodelTargets | CalibrationTargets |
|--------|----------------|-------------------|
| Total curated files | 37 | 50 |
| Files with Logfire originals | 37 (100%) | 22 (44%) |
| Average curation (% lines changed) | 47.7% | 55.6% |
| Range | 36.0% -- 64.4% | 47.6% -- 65.4% |
| Files requiring no curation | 0 (0%) | 0 (0%) |
| Extraction model | gpt-5.1 only | gpt-5.1 (22) + claude-opus-4-6 (27) + manual (1) |
| Expert review documented | Informal (git history) | Formal review.md with accept/reject decisions |
| Review rejection rate | Unknown | 58% (in documented batch) |

**Key finding**: Both schema types required substantial curation (47-56% average line change), with CalibrationTargets trending slightly higher. The earlier git-based analysis that suggested 30% of SubmodelTargets needed no curation was an artifact of pre-commit curation. With Logfire-sourced originals, the picture is consistent: every extraction required meaningful human intervention.

## What This Means for the Paper

The curation data supports the narrative that MAPLE is a **human-AI collaboration tool**, not a fully automatic pipeline. The consistent 47-56% curation rate across both schema types means:

1. **The LLM provides ~50% of the final content** -- a meaningful starting scaffold that includes correct overall structure, literature identification, and approximate parameter values
2. **Expert judgment contributes the other ~50%** -- refining biological language, adjusting priors, fixing observable code, changing source papers, and catching methodological mismatches
3. **The schema structures this collaboration** -- validators catch errors during editing, structured templates prevent code bugs, and field typing prevents parameter/input confusion
4. **No extraction was used as-is** -- this is important for credibility, as it shows the framework doesn't encourage blind acceptance of LLM output

The CalibrationTarget rejection rate (58% in the documented batch) further demonstrates that the schema enables systematic quality control that would be difficult with unstructured free-text outputs.

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
- [ ] Classify edits by type (rationale text vs. numeric values vs. observable code vs. distribution params) for a finer-grained breakdown
- [ ] Characterize the 27 claude-opus-4-6 CalibrationTarget extractions