# calibration_targets/

Two directories representing the CalibrationTarget lifecycle for the PDAC build:

## `originals/`

Raw LLM output from the batch extraction pipeline (GPT-5.1), captured before
any modeler curation. 22 YAML files, one per target. Frozen: do not edit.

Sole role: the "before" side of the curation diff in
`scripts/generate_curation_stats.py`.

## `final/`

The live corpus that feeds all paper statistics, inference scripts, and tables.

```
final/
  baseline_no_treatment/        # active baseline (no-treatment) targets
    excluded/                   # retired during curation, retained for provenance
  gvax_nivo_neoadjuvant/        # active neoadjuvant immunotherapy targets
    excluded/
  clinical_progression/         # active clinical-progression target(s)
    excluded/
```

54 active YAMLs + 5 retired under `excluded/`. The retired files are real
extraction artifacts the modeler decided not to use; they are kept on disk for
provenance but are skipped by every paper-stats script.

## Curation diff

`scripts/generate_curation_stats.py` pairs each `originals/<F>` to the matching
`final/<scenario>/<F>` (exact filename match):

- If a match exists under an active subdirectory → counted as a surviving
  batch-extracted target (`\ctBatchFiles`); field-level change rates are
  computed from the original→final diff.
- If a match exists only under `final/<scenario>/excluded/` → counted as
  curated-then-retired (`\ctBatchRejected`); the original is in the paired
  denominator (`\ctBatchPairedTotal`) but not in the field-change rates.

A new `final/` file with a higher `_derivNNN` suffix represents a distinct
source/study, not a revision of the same original. Such files do not pair
back to an earlier deriv.
