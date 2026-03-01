#!/usr/bin/env python3
"""
Generate curation statistics from original/curated YAML file pairs.

Computes meaningful field-level changes between LLM originals and
expert-curated versions by comparing parsed YAML content.

Reads from:
  metadata_storage/submodel_targets/{originals,curated}/
  metadata_storage/calibration_targets/{originals,curated/*/}

Outputs:
  paper/generated/curation_stats.tex

Usage:
    python scripts/generate_curation_stats.py
"""

from pathlib import Path

import yaml

# =============================================================================
# Configuration
# =============================================================================

ROOT = Path(__file__).parent.parent
METADATA = ROOT / "metadata_storage"
SMT_ORIGINALS = METADATA / "submodel_targets" / "originals"
SMT_CURATED = METADATA / "submodel_targets" / "curated"
CT_ORIGINALS = METADATA / "calibration_targets" / "originals"
CT_CURATED = METADATA / "calibration_targets" / "curated"
OUTPUT = ROOT / "paper" / "generated" / "curation_stats.tex"

CT_SCENARIOS = ["baseline_no_treatment", "gvax_nivo_neoadjuvant", "clinical_progression"]


# =============================================================================
# SubmodelTarget field-level comparison
# =============================================================================


def get_smt_forward_model_type(data: dict) -> str | None:
    """Get forward model type from either schema version."""
    cal = data.get("calibration", {})
    # Curated format
    fm = cal.get("forward_model")
    if isinstance(fm, dict) and "type" in fm:
        return fm["type"]
    # Original format
    model = cal.get("model")
    if isinstance(model, dict) and "type" in model:
        return model["type"]
    return None


def get_smt_prior_numerics(data: dict) -> dict:
    """Get prior numeric params {param_name: {distribution, mu, sigma, lower, upper}}."""
    cal = data.get("calibration", {})
    params = cal.get("parameters", []) or []
    result = {}
    for p in params:
        if not isinstance(p, dict) or "name" not in p:
            continue
        prior = p.get("prior") or {}
        result[p["name"]] = {
            k: prior.get(k)
            for k in ("distribution", "mu", "sigma", "lower", "upper")
        }
    return result


def get_smt_input_values(data: dict) -> dict:
    """Get input name -> value mapping."""
    inputs = data.get("inputs", []) or []
    result = {}
    for inp in inputs:
        if isinstance(inp, dict) and "name" in inp:
            result[inp["name"]] = inp.get("value")
    return result


def compare_smt_pair(orig_path: Path, curated_path: Path) -> dict:
    """Compare an original/curated SubmodelTarget pair on meaningful fields."""
    orig = yaml.safe_load(orig_path.read_text())
    cur = yaml.safe_load(curated_path.read_text())

    # Source relevance
    o_sr = orig.get("source_relevance", {}) or {}
    c_sr = cur.get("source_relevance", {}) or {}

    # Number of inputs
    o_n_inputs = len(orig.get("inputs", []) or [])
    c_n_inputs = len(cur.get("inputs", []) or [])

    return {
        "fm_type_changed": get_smt_forward_model_type(orig) != get_smt_forward_model_type(cur),
        "prior_numeric_changed": get_smt_prior_numerics(orig) != get_smt_prior_numerics(cur),
        "input_values_changed": get_smt_input_values(orig) != get_smt_input_values(cur),
        "input_count_changed": o_n_inputs != c_n_inputs,
        "source_relevance_changed": o_sr != c_sr,
    }


# =============================================================================
# CalibrationTarget field-level comparison
# =============================================================================


def compare_ct_pair(orig_path: Path, curated_path: Path) -> dict:
    """Compare an original/curated CalibrationTarget pair on meaningful fields."""
    orig = yaml.safe_load(orig_path.read_text())
    cur = yaml.safe_load(curated_path.read_text())

    # Source relevance
    o_sr = orig.get("source_relevance", {}) or {}
    c_sr = cur.get("source_relevance", {}) or {}

    # Observable code
    o_obs_code = str(orig.get("observable", {}).get("code", "") or "").strip()
    c_obs_code = str(cur.get("observable", {}).get("code", "") or "").strip()

    # Empirical data input values
    o_emp = orig.get("empirical_data", {}).get("inputs", []) or []
    c_emp = cur.get("empirical_data", {}).get("inputs", []) or []
    o_vals = {i.get("name"): i.get("value") for i in o_emp if isinstance(i, dict)}
    c_vals = {i.get("name"): i.get("value") for i in c_emp if isinstance(i, dict)}

    # Source DOI
    o_doi = orig.get("primary_data_source", {}).get("doi")
    c_doi = cur.get("primary_data_source", {}).get("doi")

    # Observable species list
    o_species = sorted(orig.get("observable", {}).get("species", []))
    c_species = sorted(cur.get("observable", {}).get("species", []))

    return {
        "source_relevance_changed": o_sr != c_sr,
        "observable_code_changed": o_obs_code != c_obs_code,
        "empirical_values_changed": o_vals != c_vals,
        "source_doi_changed": o_doi != c_doi,
        "observable_species_changed": o_species != c_species,
    }


# =============================================================================
# Interactive CalibrationTarget stats
# =============================================================================


def compute_interactive_ct_stats() -> dict:
    """Compute stats for interactive (claude-opus-4-6) CalibrationTargets."""
    total_lines = 0
    n_files = 0

    for scenario in CT_SCENARIOS:
        scenario_dir = CT_CURATED / scenario
        if not scenario_dir.exists():
            continue
        for yaml_path in sorted(scenario_dir.glob("*.yaml")):
            with open(yaml_path) as f:
                data = yaml.safe_load(f)
            if data.get("extraction_model") == "claude-opus-4-6":
                lines = yaml_path.read_text().splitlines()
                total_lines += len(lines)
                n_files += 1

    return {"n_files": n_files, "total_lines": total_lines}


# =============================================================================
# Helpers
# =============================================================================


def find_curated_ct(orig_filename: str) -> Path | None:
    """Find the curated counterpart of a CT original in scenario subdirs."""
    for scenario in CT_SCENARIOS:
        candidate = CT_CURATED / scenario / orig_filename
        if candidate.exists():
            return candidate
    return None


def pct(n: int, total: int) -> int:
    """Compute percentage as integer."""
    return round(n * 100 / total) if total > 0 else 0


# =============================================================================
# Main
# =============================================================================


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # SubmodelTarget comparisons
    # =========================================================================
    smt_results = []
    for orig in sorted(SMT_ORIGINALS.glob("*.yaml")):
        curated = SMT_CURATED / orig.name
        if not curated.exists():
            print(f"  Warning: no curated match for {orig.name}")
            continue
        smt_results.append(compare_smt_pair(orig, curated))

    smt_n = len(smt_results)
    smt_fm = sum(1 for r in smt_results if r["fm_type_changed"])
    smt_prior = sum(1 for r in smt_results if r["prior_numeric_changed"])
    smt_inputs = sum(1 for r in smt_results if r["input_values_changed"])
    smt_input_count = sum(1 for r in smt_results if r["input_count_changed"])
    smt_relevance = sum(1 for r in smt_results if r["source_relevance_changed"])

    print(f"SubmodelTargets: {smt_n} paired files")
    print(f"  Forward model type changed:    {smt_fm}/{smt_n} ({pct(smt_fm, smt_n)}%)")
    print(f"  Prior numerics changed:        {smt_prior}/{smt_n} ({pct(smt_prior, smt_n)}%)")
    print(f"  Input values changed:          {smt_inputs}/{smt_n} ({pct(smt_inputs, smt_n)}%)")
    print(f"  Number of inputs changed:      {smt_input_count}/{smt_n} ({pct(smt_input_count, smt_n)}%)")
    print(f"  Source relevance changed:      {smt_relevance}/{smt_n} ({pct(smt_relevance, smt_n)}%)")

    # =========================================================================
    # CalibrationTarget comparisons (batch pipeline)
    # =========================================================================
    ct_results = []
    for orig in sorted(CT_ORIGINALS.glob("*.yaml")):
        curated = find_curated_ct(orig.name)
        if curated is None:
            print(f"  Warning: no curated match for {orig.name}")
            continue
        ct_results.append(compare_ct_pair(orig, curated))

    ct_n = len(ct_results)
    ct_relevance = sum(1 for r in ct_results if r["source_relevance_changed"])
    ct_obs_code = sum(1 for r in ct_results if r["observable_code_changed"])
    ct_empirical = sum(1 for r in ct_results if r["empirical_values_changed"])
    ct_doi = sum(1 for r in ct_results if r["source_doi_changed"])
    ct_species = sum(1 for r in ct_results if r["observable_species_changed"])

    print(f"\nCalibrationTargets (batch): {ct_n} paired files")
    print(f"  Source relevance changed:      {ct_relevance}/{ct_n} ({pct(ct_relevance, ct_n)}%)")
    print(f"  Observable code changed:       {ct_obs_code}/{ct_n} ({pct(ct_obs_code, ct_n)}%)")
    print(f"  Empirical values changed:      {ct_empirical}/{ct_n} ({pct(ct_empirical, ct_n)}%)")
    print(f"  Source DOI changed:            {ct_doi}/{ct_n} ({pct(ct_doi, ct_n)}%)")
    print(f"  Observable species changed:    {ct_species}/{ct_n} ({pct(ct_species, ct_n)}%)")

    # =========================================================================
    # Interactive CalibrationTargets
    # =========================================================================
    interactive = compute_interactive_ct_stats()
    print(f"\nInteractive CTs: {interactive['n_files']} files, {interactive['total_lines']} total lines")

    # =========================================================================
    # Total target files (SMT derivations + all CTs across scenarios)
    # =========================================================================
    all_ct_files = 0
    for scenario in CT_SCENARIOS:
        scenario_dir = CT_CURATED / scenario
        if scenario_dir.exists():
            all_ct_files += len(list(scenario_dir.glob("*.yaml")))
    total_ct_files = smt_n + all_ct_files
    print(f"\nTotal target files: {smt_n} SMT + {all_ct_files} CT = {total_ct_files}")

    # =========================================================================
    # Write LaTeX macros
    # =========================================================================
    lines = [
        "% Auto-generated curation statistics",
        "% Generated by scripts/generate_curation_stats.py",
        "%",
        "% SubmodelTarget curation (batch pipeline, gpt-5.1)",
        f"\\newcommand{{\\smtCuratedFiles}}{{{smt_n}}}",
        f"\\newcommand{{\\smtFmTypeChanged}}{{{smt_fm}}}",
        f"\\newcommand{{\\smtFmTypeChangedPct}}{{{pct(smt_fm, smt_n)}\\%}}",
        f"\\newcommand{{\\smtPriorChanged}}{{{smt_prior}}}",
        f"\\newcommand{{\\smtPriorChangedPct}}{{{pct(smt_prior, smt_n)}\\%}}",
        f"\\newcommand{{\\smtInputsChanged}}{{{smt_inputs}}}",
        f"\\newcommand{{\\smtInputsChangedPct}}{{{pct(smt_inputs, smt_n)}\\%}}",
        f"\\newcommand{{\\smtInputCountChanged}}{{{smt_input_count}}}",
        f"\\newcommand{{\\smtInputCountChangedPct}}{{{pct(smt_input_count, smt_n)}\\%}}",
        f"\\newcommand{{\\smtRelevanceChanged}}{{{smt_relevance}}}",
        f"\\newcommand{{\\smtRelevanceChangedPct}}{{{pct(smt_relevance, smt_n)}\\%}}",
        "%",
        "% CalibrationTarget curation (batch pipeline, gpt-5.1)",
        f"\\newcommand{{\\ctBatchFiles}}{{{ct_n}}}",
        f"\\newcommand{{\\ctRelevanceChanged}}{{{ct_relevance}}}",
        f"\\newcommand{{\\ctRelevanceChangedPct}}{{{pct(ct_relevance, ct_n)}\\%}}",
        f"\\newcommand{{\\ctObsCodeChanged}}{{{ct_obs_code}}}",
        f"\\newcommand{{\\ctObsCodeChangedPct}}{{{pct(ct_obs_code, ct_n)}\\%}}",
        f"\\newcommand{{\\ctEmpiricalChanged}}{{{ct_empirical}}}",
        f"\\newcommand{{\\ctEmpiricalChangedPct}}{{{pct(ct_empirical, ct_n)}\\%}}",
        f"\\newcommand{{\\ctDoiChanged}}{{{ct_doi}}}",
        f"\\newcommand{{\\ctSpeciesChanged}}{{{ct_species}}}",
        f"\\newcommand{{\\ctSpeciesChangedPct}}{{{pct(ct_species, ct_n)}\\%}}",
        "%",
        "% Interactive extraction (claude-opus-4-6)",
        f"\\newcommand{{\\ctInteractiveFiles}}{{{interactive['n_files']}}}",
        f"\\newcommand{{\\ctInteractiveTotalLines}}{{{interactive['total_lines']:,}}}",
        "%",
        "% Total target files (SMT derivations + all CTs)",
        f"\\newcommand{{\\totalTargetFiles}}{{{total_ct_files}}}",
    ]
    OUTPUT.write_text("\n".join(lines) + "\n")
    print(f"\nWrote {OUTPUT}")


if __name__ == "__main__":
    main()
