# Run Submodel Target Extraction

```bash
qsp-extract supporting_files/parameters/xlsx_targets_matched_working.csv \
  --type submodel_target \
  --output-dir metadata_storage \
  --model-structure supporting_files/model_structure.json \
  --model-context supporting_files/model_context.txt \
  --previous-extractions metadata_storage
```

## Optional flags

- `--preview-prompts` — preview prompts without calling API
- `--model gpt-5.1` — model to use (default: gpt-5.1)
- `--reasoning-effort low|medium|high` — reasoning effort level (default: medium)