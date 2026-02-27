#!/usr/bin/env python3
"""
Generate metrics.json for the MAPLE paper.

Collects YAML-based metrics, validation results, and code generation stats
from local files only (no external services). Preserves cached extraction
and inference sections from previous runs.

Usage:
    python scripts/generate_results.py

Outputs:
    paper/generated/metrics.json
"""

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from subprocess import run

import yaml

# =============================================================================
# Configuration
# =============================================================================

CURATED_DIR = Path(__file__).parent.parent / "metadata_storage" / "submodel_targets" / "curated"
OUTPUT_DIR = Path(__file__).parent.parent / "paper" / "generated"
SCRIPTS_DIR = Path(__file__).parent


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class CodeGenMetrics:
    """Metrics from Julia code generation."""

    n_targets: int = 0
    n_unique_parameters: int = 0
    n_shared_parameters: int = 0
    total_lines: int = 0
    parameters: list = field(default_factory=list)
    shared_params_detail: dict = field(default_factory=dict)


@dataclass
class YAMLMetrics:
    """Metrics extracted directly from YAML target files."""

    source_quality: dict = field(default_factory=dict)
    species_translation: dict = field(default_factory=dict)
    indication_match: dict = field(default_factory=dict)
    model_types: dict = field(default_factory=dict)
    complexity: list = field(default_factory=list)
    per_target: list = field(default_factory=list)


# =============================================================================
# Data Collection Functions
# =============================================================================


def collect_codegen_metrics() -> CodeGenMetrics:
    """Collect metrics from the generated Julia code."""
    metrics = CodeGenMetrics()

    julia_file = SCRIPTS_DIR / "joint_calibration.jl"
    if not julia_file.exists():
        print("Warning: joint_calibration.jl not found. Code generation metrics will be empty.")
        return metrics

    content = julia_file.read_text()
    metrics.total_lines = len(content.splitlines())

    # Extract parameters from prior declarations
    # Pattern: k_param ~ LogNormal(...) # Used by: target1, target2
    param_pattern = re.compile(
        r"^\s+(\w+)\s+~\s+\w+\([^)]+\)\s*#\s*Used by:\s*(.+)$", re.MULTILINE
    )

    param_targets = {}
    for match in param_pattern.finditer(content):
        param_name = match.group(1)
        targets = [t.strip() for t in match.group(2).split(",")]
        param_targets[param_name] = targets

    metrics.parameters = list(param_targets.keys())
    metrics.n_unique_parameters = len(param_targets)

    for param, targets in param_targets.items():
        if len(targets) > 1:
            metrics.shared_params_detail[param] = targets
    metrics.n_shared_parameters = len(metrics.shared_params_detail)

    # Count targets from DATA dict
    data_pattern = re.compile(r'"([^"]+)"\s*=>\s*\(')
    target_matches = data_pattern.findall(content)
    metrics.n_targets = len(target_matches)

    return metrics


def collect_validation_metrics() -> dict:
    """Collect validation pass/fail statistics from curated YAML files."""
    yaml_files = list(CURATED_DIR.glob("*.yaml"))

    result = run(
        ["python", "scripts/validate_submodel_target.py"] + [str(f) for f in yaml_files],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )

    output = result.stdout + result.stderr
    valid_count = output.count("✓ Valid:")
    invalid_count = output.count("✗ Invalid:") + output.count("ValidationError")

    return {
        "n_files": len(yaml_files),
        "n_valid": valid_count,
        "n_invalid": invalid_count,
        "pass_rate": valid_count / len(yaml_files) if yaml_files else 0,
    }


def collect_yaml_metrics() -> YAMLMetrics:
    """Collect metrics directly from curated YAML target files."""
    metrics = YAMLMetrics()

    yaml_files = sorted(CURATED_DIR.glob("*.yaml"))

    source_quality = Counter()
    species_trans = Counter()
    indication = Counter()
    model_types = Counter()

    for yf in yaml_files:
        try:
            with open(yf) as f:
                data = yaml.safe_load(f)

            if not data or "calibration" not in data:
                continue

            target_info = {"file": yf.name}

            # Source relevance
            sr = data.get("source_relevance", {})
            if sr:
                sq = sr.get("source_quality", "unknown")
                source_quality[sq] += 1
                target_info["source_quality"] = sq

                species_src = sr.get("species_source", "unknown")
                species_tgt = sr.get("species_target", "unknown")
                trans_key = f"{species_src}\u2192{species_tgt}"
                species_trans[trans_key] += 1
                target_info["species_translation"] = trans_key

                ind_match = sr.get("indication_match", "unknown")
                indication[ind_match] += 1
                target_info["indication_match"] = ind_match

            # Model type
            cal = data.get("calibration", {})
            model = cal.get("forward_model", {})
            model_type = model.get("type", "unknown")
            model_types[model_type] += 1
            target_info["model_type"] = model_type

            # Complexity
            n_inputs = len(data.get("inputs", []))
            n_params = len(cal.get("parameters", []))
            n_states = len(cal.get("state_variables", []))

            code_lines = 0
            for em in cal.get("error_model", []):
                obs_code = em.get("observation_code", "")
                if obs_code:
                    code_lines += len(obs_code.strip().split("\n"))

            fm_code = model.get("code", "") or model.get("code_julia", "")
            if fm_code:
                code_lines += len(fm_code.strip().split("\n"))

            complexity = {
                "file": yf.name,
                "n_inputs": n_inputs,
                "n_params": n_params,
                "n_states": n_states,
                "code_lines": code_lines,
            }
            metrics.complexity.append(complexity)
            target_info["complexity"] = complexity

            metrics.per_target.append(target_info)

        except Exception as e:
            print(f"Warning: Could not parse {yf.name}: {e}")

    metrics.source_quality = dict(source_quality)
    metrics.species_translation = dict(species_trans)
    metrics.indication_match = dict(indication)
    metrics.model_types = dict(model_types)

    return metrics


# =============================================================================
# Main
# =============================================================================


def main():
    print("=" * 60)
    print("Generating MAPLE paper metrics (local data only)")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load existing metrics.json to preserve cached extraction/inference data
    cached = {}
    metrics_path = OUTPUT_DIR / "metrics.json"
    if metrics_path.exists():
        with open(metrics_path) as f:
            cached = json.load(f)
        print(f"Loaded cached metrics.json ({len(cached)} sections)")

    # Collect local-only metrics
    print("\n[1/3] Collecting YAML-based metrics...")
    yaml_metrics = collect_yaml_metrics()
    print(f"  Source qualities: {len(yaml_metrics.source_quality)} types")
    print(f"  Model types: {len(yaml_metrics.model_types)} types")
    print(f"  Targets with complexity data: {len(yaml_metrics.complexity)}")

    print("\n[2/3] Collecting validation metrics...")
    validation = collect_validation_metrics()
    print(f"  Validation: {validation['n_valid']}/{validation['n_files']} passed")

    print("\n[3/3] Collecting code generation metrics...")
    codegen = collect_codegen_metrics()
    print(f"  Parameters: {codegen.n_unique_parameters} ({codegen.n_shared_parameters} shared)")
    print(f"  Lines of Julia: {codegen.total_lines}")

    # Merge: update local sections, preserve cached extraction/inference
    metrics_json = {
        "extraction": cached.get("extraction", {}),
        "codegen": {
            "n_unique_parameters": codegen.n_unique_parameters,
            "n_shared_parameters": codegen.n_shared_parameters,
            "n_targets": codegen.n_targets,
            "total_lines": codegen.total_lines,
            "parameters": codegen.parameters,
            "shared_params_detail": codegen.shared_params_detail,
        },
        "julia_generation": cached.get("julia_generation", {}),
        "inference_run": cached.get("inference_run"),
        "inference_results": cached.get("inference_results"),
        "validation": validation,
        "inference_available": cached.get("inference_available", False),
        "yaml_metrics": {
            "source_quality": yaml_metrics.source_quality,
            "species_translation": yaml_metrics.species_translation,
            "indication_match": yaml_metrics.indication_match,
            "model_types": yaml_metrics.model_types,
            "complexity": yaml_metrics.complexity,
        },
    }

    metrics_path.write_text(json.dumps(metrics_json, indent=2))
    print(f"\nSaved: {metrics_path}")

    print("\n" + "=" * 60)
    print("Done! Now run:")
    print("  python scripts/generate_latex.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
