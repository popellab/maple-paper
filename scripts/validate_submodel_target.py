#!/usr/bin/env python3
"""
Validate a YAML file against the SubmodelTarget schema.

Usage:
    python scripts/validate_submodel_target.py path/to/target.yaml
"""

import sys
from pathlib import Path

import yaml
from pydantic import ValidationError

from qsp_llm_workflows.core.calibration.submodel_target import SubmodelTarget
from qsp_llm_workflows.core.model_structure import ModelStructure

# Model structure path relative to this script
MODEL_STRUCTURE_PATH = Path(__file__).parent.parent / "batch_extraction" / "model_structure.json"
REFERENCE_VALUES_PATH = Path(__file__).parent.parent / "batch_extraction" / "reference_values.yaml"


def load_model_structure() -> ModelStructure:
    """Load the model structure for unit validation."""
    if MODEL_STRUCTURE_PATH.exists():
        return ModelStructure.from_json(str(MODEL_STRUCTURE_PATH))
    return None


def load_reference_db() -> dict:
    """Load reference values database for ReferenceRef resolution."""
    if REFERENCE_VALUES_PATH.exists():
        data = yaml.safe_load(REFERENCE_VALUES_PATH.read_text())
        return {v["name"]: float(v["value"]) for v in data["values"]}
    return None


def validate_yaml(yaml_path: str, model_structure: ModelStructure = None,
                   reference_db: dict = None) -> bool:
    """
    Validate a YAML file against SubmodelTarget schema.

    Args:
        yaml_path: Path to the YAML file
        model_structure: ModelStructure for unit validation
        reference_db: Reference values database for ReferenceRef resolution

    Returns:
        True if valid, False otherwise
    """
    path = Path(yaml_path)

    if not path.exists():
        print(f"Error: File not found: {yaml_path}")
        return False

    # Load YAML
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML syntax:\n{e}")
        return False

    # Validate against model
    try:
        context = {}
        if model_structure:
            context["model_structure"] = model_structure
        if reference_db:
            context["reference_db"] = reference_db
        target = SubmodelTarget.model_validate(data, context=context)
        print(f"✓ Valid: {path.name}")
        print(f"  target_id: {target.target_id}")
        print(f"  inputs: {len(target.inputs)}")
        print(f"  parameters: {[p.name for p in target.calibration.parameters]}")
        print(f"  model type: {target.calibration.model.type}")
        return True
    except ValidationError as e:
        print(f"✗ Validation failed: {path.name}\n")
        for error in e.errors():
            loc = " → ".join(str(x) for x in error["loc"])
            print(f"  [{loc}]")
            print(f"    {error['msg']}")
            if error.get("input"):
                input_str = str(error["input"])[:80]
                print(f"    Input: {input_str}{'...' if len(str(error['input'])) > 80 else ''}")
            print()
        return False


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    # Load model structure for unit validation
    model_structure = load_model_structure()
    if model_structure:
        print(f"Using model structure: {MODEL_STRUCTURE_PATH.name}")

    # Load reference values database for ReferenceRef resolution
    reference_db = load_reference_db()
    if reference_db:
        print(f"Using reference values: {REFERENCE_VALUES_PATH.name} ({len(reference_db)} values)")
    print()

    yaml_paths = sys.argv[1:]
    results = []

    for yaml_path in yaml_paths:
        valid = validate_yaml(yaml_path, model_structure, reference_db)
        results.append((yaml_path, valid))
        if len(yaml_paths) > 1:
            print()

    # Summary for multiple files
    if len(results) > 1:
        print("-" * 40)
        valid_count = sum(1 for _, v in results if v)
        print(f"Summary: {valid_count}/{len(results)} files valid")

    # Exit with error if any failed
    sys.exit(0 if all(v for _, v in results) else 1)


if __name__ == "__main__":
    main()
