#!/usr/bin/env python3
"""
Verify that every final target in this study passes MAPLE's validator suite.

Re-runs the MAPLE Pydantic validator pipeline against all final SubmodelTarget
and CalibrationTarget YAMLs and reports pass/fail, reproducing the manuscript's
claim that no final target retains an unresolved validator failure.

The manuscript pins this result to MAPLE v0.1.0 (commit 7f1faa4). Because the
schema has changed in later versions, run this through scripts/verify_validation.sh,
which puts MAPLE v0.1.0 on the path for you. Running against a different version
will report spurious failures; this script warns if the imported version is not
0.1.0.

What this checks: the deterministic Pydantic validator pipeline
(SubmodelTarget / CalibrationTarget model_validate with the model structure,
species units, and reference database as context), which runs the schema, unit,
reference, structural, and observable/observation code validators. It does not
run the network-dependent checks (CrossRef DOI resolution, external
snippet-in-paper fetch), which the manuscript reports separately.

Usage:
    ./scripts/verify_validation.sh         # recommended: pins MAPLE v0.1.0
    python scripts/verify_validation.py    # uses whatever 'maple' is importable
    python scripts/verify_validation.py -v # also list each file

Exits 0 if every final target passes, 1 otherwise.
"""

import json
import sys
import warnings
from pathlib import Path

import yaml

# Validators emit advisory UserWarnings (e.g. wide CV, magnitude hints). These
# are not failures; count them quietly instead of flooding the output.
_warning_count = 0


def _count_warning(*args, **kwargs):
    global _warning_count
    _warning_count += 1


warnings.showwarning = _count_warning

REPO = Path(__file__).resolve().parent.parent
MODEL_STRUCTURE_PATH = REPO / "batch_extraction" / "model_structure.json"
SPECIES_UNITS_PATH = REPO / "batch_extraction" / "species_units.json"
REFERENCE_VALUES_PATH = REPO / "batch_extraction" / "reference_values.yaml"
SMT_DIR = REPO / "metadata_storage" / "submodel_targets" / "curated"
CT_DIR = REPO / "metadata_storage" / "calibration_targets" / "final"
PINNED_VERSION = "0.1.0"

try:
    import maple
except ModuleNotFoundError:
    sys.exit(
        "Error: the 'maple' package is not importable.\n"
        "Run this via scripts/verify_validation.sh (which puts MAPLE v0.1.0 on the "
        "path), or set PYTHONPATH to a MAPLE v0.1.0 (commit 7f1faa4) src checkout."
    )

from maple.core.calibration.submodel_target import SubmodelTarget  # noqa: E402
from maple.core.calibration.calibration_target_models import CalibrationTarget  # noqa: E402
from maple.core.model_structure import ModelStructure  # noqa: E402


def load_context() -> dict:
    """Build the validation context expected by the v0.1.0 validators."""
    context = {
        "model_structure": ModelStructure.from_json(str(MODEL_STRUCTURE_PATH)),
        "species_units": json.loads(SPECIES_UNITS_PATH.read_text()),
    }
    ref = yaml.safe_load(REFERENCE_VALUES_PATH.read_text())
    context["reference_db"] = {v["name"]: float(v["value"]) for v in ref["values"]}
    return context


def validate_dir(label, directory, model_cls, context, skip_excluded, verbose):
    """Validate every YAML in a directory; return the list of (path, error) failures."""
    failures = []
    passed = 0
    for path in sorted(directory.rglob("*.yaml")):
        # Retired targets are retained for provenance under */excluded/ and are
        # not part of the reported corpus.
        if skip_excluded and "excluded" in path.parts:
            continue
        try:
            data = yaml.safe_load(path.read_text())
            model_cls.model_validate(data, context=context)
            passed += 1
            if verbose:
                print(f"  PASS  {path.relative_to(REPO)}")
        except Exception as exc:  # ValidationError or any validator-raised error
            failures.append((path, exc))
            first = str(exc).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__
            print(f"  FAIL  {path.relative_to(REPO)}")
            print(f"        {first}")
    print(f"{label}: {passed}/{passed + len(failures)} passed")
    return failures


def main():
    verbose = "-v" in sys.argv or "--verbose" in sys.argv

    version = getattr(maple, "__version__", "unknown")
    print(f"MAPLE version: {version}  (manuscript pins {PINNED_VERSION}, commit 7f1faa4)")
    if version != PINNED_VERSION:
        print(
            f"  WARNING: this is not v{PINNED_VERSION}; the schema may differ and "
            "failures below may be spurious.\n"
            "  Run scripts/verify_validation.sh to pin the correct version.\n"
        )
    print("Validators: Pydantic pipeline (model_validate with model_structure, "
          "species_units, reference_db)\n")

    context = load_context()
    failures = []
    failures += validate_dir("SubmodelTargets   ", SMT_DIR, SubmodelTarget,
                             context, skip_excluded=False, verbose=verbose)
    failures += validate_dir("CalibrationTargets", CT_DIR, CalibrationTarget,
                             context, skip_excluded=True, verbose=verbose)

    print()
    if _warning_count:
        print(f"({_warning_count} advisory validator warnings emitted; these are not failures)")
    if failures:
        print(f"RESULT: {len(failures)} target(s) FAILED the validator suite.")
        sys.exit(1)
    print("RESULT: every final target passes the validator suite.")
    sys.exit(0)


if __name__ == "__main__":
    main()
