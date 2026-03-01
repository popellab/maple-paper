#!/usr/bin/env bash
# Run SubmodelTarget batch extraction using the MAPLE framework.
#
# Prerequisites:
#   pip install maple   # or install from ../maple
#   export OPENAI_API_KEY=...
#
# To regenerate model_structure.json and species_units.json (requires MATLAB):
#   qsp-export-model \
#     --matlab-model /path/to/pdac-build/scripts/immune_oncology_model_PDAC.m \
#     --output batch_extraction/model_structure.json \
#     --structure
#
# This script was used to generate the SubmodelTarget YAML files in
# metadata_storage/submodel_targets/originals/. Each row in extraction_targets.csv
# produces one extraction attempt per invocation. Multiple derivations per parameter
# were obtained by running the script multiple times with --previous-extractions
# pointing to prior results (which excludes already-used sources).

set -euo pipefail
cd "$(dirname "$0")"

REPO_ROOT=".."
OUTPUT_DIR="${REPO_ROOT}/metadata_storage/submodel_targets/to-review"

# First extraction round (no previous extractions to exclude)
qsp-extract extraction_targets.csv \
  --type submodel_target \
  --model-structure model_structure.json \
  --model-context model_context.txt \
  --reference-values reference_values.yaml \
  --output-dir "${OUTPUT_DIR}" \
  --model gpt-5.1 \
  --reasoning-effort high \
  --max-retries 10

# Subsequent rounds: pass previous extractions to exclude already-used sources.
# This yields independent derivations (deriv002, deriv003, ...) per parameter.
#
# qsp-extract extraction_targets.csv \
#   --type submodel_target \
#   --model-structure model_structure.json \
#   --model-context model_context.txt \
#   --reference-values reference_values.yaml \
#   --previous-extractions "${REPO_ROOT}/metadata_storage/submodel_targets/originals" \
#   --output-dir "${OUTPUT_DIR}" \
#   --model gpt-5.1 \
#   --reasoning-effort high \
#   --max-retries 10