#!/usr/bin/env python3
"""
Generate Julia/Turing.jl inference scripts from SubmodelTarget YAML files.

Usage:
    python scripts/generate_inference.py [YAML_DIR]
    python scripts/generate_inference.py metadata_storage/to-review/batch3
    python scripts/generate_inference.py --fixed-sigma metadata_storage

Arguments:
    YAML_DIR  Directory containing .yaml extraction files (default: metadata_storage)

Options:
    --fixed-sigma       Treat all measurement sigmas as fixed (faster sampling)
    --joint-output      Output path for joint script (default: scripts/joint_calibration.jl)
    --single-output     Output path for single-target script (default: scripts/single_targets_combined.jl)
    --skip-joint        Skip joint inference generation
    --skip-single       Skip single-target generation
    --model-structure   Path to model_structure.json (default: batch_extraction/model_structure.json)
"""

import argparse
import subprocess
import sys
from pathlib import Path


def find_yaml_files(directory: Path) -> list[Path]:
    """Find all .yaml files in a directory (non-recursive)."""
    files = sorted(directory.glob("*.yaml"))
    return [f for f in files if f.is_file()]


def run_translator(args: list[str], description: str) -> None:
    """Run the julia_translator module with the given arguments."""
    cmd = [sys.executable, "-m", "maple.core.calibration.julia_translator"] + args
    print(f"  {' '.join(cmd)}\n")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error generating {description}:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    if result.stdout:
        print(result.stdout)


def main():
    parser = argparse.ArgumentParser(
        description="Generate Julia inference scripts from SubmodelTarget YAML files."
    )
    parser.add_argument(
        "yaml_dir",
        nargs="?",
        default="metadata_storage",
        help="Directory containing .yaml extraction files (default: metadata_storage)",
    )
    parser.add_argument(
        "--sample-sigma",
        action="store_true",
        help="Estimate sigma as latent variable when sd_uncertain is true (default: fixed)",
    )
    parser.add_argument(
        "--joint-output",
        default="scripts/joint_calibration.jl",
        help="Output path for joint script",
    )
    parser.add_argument(
        "--single-output",
        default="scripts/single_targets_combined.jl",
        help="Output path for single-target script",
    )
    parser.add_argument("--skip-joint", action="store_true", help="Skip joint inference generation")
    parser.add_argument("--skip-single", action="store_true", help="Skip single-target generation")
    parser.add_argument(
        "--model-structure",
        default="batch_extraction/model_structure.json",
        help="Path to model_structure.json",
    )
    parser.add_argument(
        "--reference-values",
        default="batch_extraction/reference_values.yaml",
        help="Path to reference_values.yaml",
    )
    args = parser.parse_args()

    yaml_dir = Path(args.yaml_dir)
    model_structure = Path(args.model_structure)
    reference_values = Path(args.reference_values)

    if not yaml_dir.is_dir():
        print(f"Error: directory '{yaml_dir}' does not exist", file=sys.stderr)
        sys.exit(1)

    if not model_structure.is_file():
        print(f"Error: model structure file '{model_structure}' not found", file=sys.stderr)
        sys.exit(1)

    if not reference_values.is_file():
        print(f"Error: reference values file '{reference_values}' not found", file=sys.stderr)
        sys.exit(1)

    yaml_files = find_yaml_files(yaml_dir)
    if not yaml_files:
        print(f"Error: no .yaml files found in '{yaml_dir}'", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(yaml_files)} YAML files in {yaml_dir}")
    for f in yaml_files:
        print(f"  {f.name}")
    print()

    yaml_paths = [str(f) for f in yaml_files]

    # Joint inference
    if not args.skip_joint:
        print(f"Generating joint inference script -> {args.joint_output}")
        joint_args = [
            "--joint",
            "--model-structure", str(model_structure),
            "--reference-values", str(reference_values),
            "--output", args.joint_output,
        ]
        if not args.sample_sigma:
            joint_args.append("--fixed-sigma")
        joint_args.extend(yaml_paths)
        run_translator(joint_args, "joint inference script")

    # Single-target combined
    if not args.skip_single:
        print(f"Generating single-target script -> {args.single_output}")
        single_args = [
            "--single-all",
            "--model-structure", str(model_structure),
            "--reference-values", str(reference_values),
            "--output", args.single_output,
        ]
        single_args.extend(yaml_paths)
        run_translator(single_args, "single-target script")

    print("Done. To run inference:")
    if not args.skip_joint:
        print(f"  julia {args.joint_output}")
    if not args.skip_single:
        print(f"  julia {args.single_output}")


if __name__ == "__main__":
    main()
