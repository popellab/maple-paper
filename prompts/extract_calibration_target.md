# Extract Calibration Target Prompt

Use this prompt by saying: **"Extract target: `[TARGET_ID]` using prompts/extract_calibration_target.md"**

---

## Instructions

Extract the calibration target `[TARGET_ID]` following this workflow:

### 1. Gather Context
- Look up the target in `notes/isolated_system_targets_pdac.csv` for parameter name and notes
- Check `jobs/input_data/model_definitions.json` for parameter units and model reaction context

### 2. Find Literature Data
- Search for quantitative experimental data (ELISA, flow cytometry, cell counts, etc.)
- Must have exact numeric values with units (e.g., "26.30 ± 3.69 ng/mL")
- Record verbatim quotes containing the values

### 3. Create YAML
- Create `examples/[target_id]_PDAC_deriv001.yaml` using SubmodelTarget schema
- Follow existing examples in `examples/` for format
- All `value_snippet` fields must be **verbatim quotes** from the paper
- All `source_ref` must match a `source_tag` defined in data sources section
- Use `input_type: inferred_estimate` only when value is interpreted from qualitative text

### 4. Validate
```bash
python scripts/validate_submodel_target.py examples/[filename].yaml
```

### 5. Run Joint Inference
```bash
python -m qsp_llm_workflows.core.calibration.julia_translator --joint \
  examples/*.yaml \
  --output examples/joint_psc_calibration.jl

julia --project=../qspio-pdac examples/joint_psc_calibration.jl
```

---

## Key Schema Requirements

**Input types:**
- `direct_measurement`: Value explicitly stated in paper (requires verbatim snippet)
- `experimental_condition`: Protocol parameter from methods (requires verbatim snippet)
- `assumed_value`: Standard value not in paper (no snippet needed)
- `inferred_estimate`: Interpreted from qualitative text (skips snippet validation)

**Input roles:**
- `target`: Used as calibration target (included in likelihood)
- `auxiliary`: Supporting data (SD values, conditions)
- `initial_condition`: ODE initial value (excluded from likelihood)

**Model types:**
- `direct_conversion`: No ODE, analytical formula (k = ln(2)/t_half)
- `exponential_growth`: dy/dt = k*y
- `first_order_decay`: dy/dt = -k*y
- `two_state`: A → B transition
- `saturation`: dy/dt = k*(1-y)
- `custom`: User-provided ODE code
