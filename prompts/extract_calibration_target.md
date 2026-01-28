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

**CRITICAL: distribution_code requirement**

For `direct_conversion` models with a formula, you MUST provide `distribution_code` in the measurement that implements the unit conversion. Without it, the raw input value will be used as the observation, causing unit mismatches.

Example - if formula is `k = ln(2) / t_half`:
```python
distribution_code: |
  def derive_distribution(inputs, ureg):
      import numpy as np
      t_half = inputs['doubling_time_h'].magnitude  # hours
      k = np.log(2) / t_half * 24  # convert to 1/day
      # Propagate uncertainty assuming ~10% CV
      cv = 0.1
      sigma_log = np.sqrt(np.log(1 + cv**2))
      return {
          'median': [k] * ureg('1/day'),
          'ci95': [[k * np.exp(-1.96*sigma_log), k * np.exp(1.96*sigma_log)]],
          'units': '1/day',
      }
```

**Observable types for ODE models:**

For ODE models, choose the appropriate observable type:
- `final_value`: Value of state variable at final time (default)
- `fraction_remaining`: y(t_end) / y(0) - for decay experiments
- `fold_change`: y(t_end) / y(0) - for growth experiments
- `auc`: Area under curve (trapezoidal integration)
- `max_value`: Maximum value reached
- `custom`: User-provided code (only if built-in types don't work)

**AVOID `custom` observable when possible** - use built-in types. If you must use `custom`, the signature is:
```python
code: |
  def compute(t, y, y0):
      # t: time array, y: state array [n_states, n_times], y0: initial conditions
      return y[0, -1] / y0[0]  # example: fraction remaining
```
