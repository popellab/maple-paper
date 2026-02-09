#!/usr/bin/env python3
"""Check forward model predictions against target values."""

import yaml
import numpy as np
from pathlib import Path
from pint import UnitRegistry

# Setup pint with custom units
ureg = UnitRegistry()
ureg.define('cell = []')
ureg.define('HPF = []')


def run_forward_model(yaml_path):
    """Run forward model and compare to target."""
    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    # Skip non-algebraic models
    fm = data.get('calibration', {}).get('forward_model', {})
    if fm.get('type') != 'algebraic':
        return None

    code = fm.get('code')
    if not code:
        return None

    # Build inputs dict (just use floats)
    inputs = {}
    target_input = None
    for inp in data.get('inputs', []):
        name = inp['name']
        val = inp['value']
        inputs[name] = float(val)
        if inp.get('role') == 'target':
            target_input = (name, val, inp.get('units'))

    # Get parameter info and sample from prior
    param_info = data['calibration']['parameters'][0]
    param_name = param_info['name']
    prior = param_info.get('prior', {})

    # Sample median from prior
    if prior.get('distribution') == 'lognormal':
        mu = prior.get('mu', 0)
        param_val = np.exp(mu)  # median of lognormal
    else:
        param_val = 1.0

    params = {param_name: param_val}

    # Execute forward model
    exec_globals = {'np': np}
    exec(code, exec_globals)
    compute = exec_globals['compute']

    try:
        result = compute(params, inputs, ureg)
        result_mag = getattr(result, 'magnitude', result)
    except Exception as e:
        return {
            'file': yaml_path.name,
            'param': param_name,
            'error': str(e)[:60]
        }

    # Get target value for comparison
    target_name, target_val, target_units = target_input if target_input else (None, None, None)

    if target_val and target_val != 0:
        ratio = result_mag / target_val
    else:
        ratio = None

    return {
        'file': yaml_path.name,
        'param': param_name,
        'prior_median': param_val,
        'prediction': result_mag,
        'target': target_val,
        'target_units': target_units or "",
        'ratio': ratio
    }


def main():
    yaml_dir = Path(__file__).parent.parent / "metadata_storage"
    results = []

    for yaml_path in sorted(yaml_dir.glob("*.yaml")):
        result = run_forward_model(yaml_path)
        if result:
            results.append(result)

    # Check for errors
    errors = [r for r in results if 'error' in r]
    valid = [r for r in results if 'error' not in r]

    if valid:
        print(f"{'File':<42} {'Param':<16} {'Prior Med':<12} {'Predict':<12} {'Target':<12} {'Ratio'}")
        print("-" * 110)
        for r in valid:
            pm = f"{r['prior_median']:.2e}"
            pred = f"{r['prediction']:.2e}"
            tgt = f"{r['target']:.2e}" if r['target'] else "N/A"
            ratio = f"{r['ratio']:.2f}x" if r['ratio'] else "N/A"
            print(f"{r['file']:<42} {r['param']:<16} {pm:<12} {pred:<12} {tgt:<12} {ratio}")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for r in errors:
            print(f"  {r['file']}: {r['error']}")


if __name__ == "__main__":
    main()
