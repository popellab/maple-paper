#!/usr/bin/env python3
"""
Generate LaTeX macros and tables from CalibrationTarget YAML files.

Reads all CalibrationTarget YAMLs from pdac-build and generates:
  - paper/generated/ct_stats.tex (macros for inline stats)
  - paper/generated/ct_summary_table.tex (scenario summary table)
  - paper/generated/ct_observable_table.tex (observable category table)
  - paper/generated/ct_complexity_table.tex (complexity metrics table)
  - paper/generated/ct_extraction_model_table.tex (extraction model breakdown)

Usage:
    python scripts/generate_ct_stats.py
"""

from collections import Counter
from pathlib import Path

import yaml

# =============================================================================
# Configuration
# =============================================================================

PDAC_BUILD = Path(__file__).parent.parent.parent / "pdac-build"
CT_DIR = PDAC_BUILD / "calibration_targets"
OUTPUT_DIR = Path(__file__).parent.parent / "paper" / "generated"


def categorize_observable(target_id: str, units: str) -> str:
    """Categorize observable by units and target name."""
    units_lower = units.lower()
    tid = target_id.lower()

    if "cell" in units_lower and ("mm" in units_lower or "millimeter" in units_lower):
        return "density"
    if "ratio" in tid or "m1_m2" in tid or "tam_to_cdc1" in tid:
        return "ratio"
    if "fold" in tid:
        return "fold-change"
    if "response_rate" in tid:
        return "response rate"
    if "mmhg" in units_lower or "mercury" in units_lower:
        return "pressure"
    if "cm" in units_lower or "centimeter" in units_lower:
        return "volume"
    if "pg" in units_lower or "picogram" in units_lower:
        return "concentration"
    if units_lower in ("day", "days"):
        return "time"
    if "fraction" in tid or "pct" in tid or "positivity" in tid:
        return "fraction"
    if "dimensionless" in units_lower:
        return "dimensionless (other)"
    return "other"


# Higher-level groupings for the main text
CATEGORY_GROUPS = {
    "Cell densities": ["density"],
    "Immune/stromal fractions": ["fraction"],
    "Population ratios": ["ratio"],
    "Fold-changes": ["fold-change"],
    "Metabolic/TME markers": ["pressure", "concentration", "dimensionless (other)"],
    "Clinical endpoints": ["volume", "time", "response rate"],
}


def group_categories(cat_counts: Counter) -> dict:
    """Group fine categories into display groups."""
    groups = {}
    for group_name, cats in CATEGORY_GROUPS.items():
        total = sum(cat_counts.get(c, 0) for c in cats)
        if total > 0:
            groups[group_name] = total
    return groups


def load_targets():
    """Load all CalibrationTarget YAMLs."""
    targets = []
    for yaml_path in sorted(CT_DIR.rglob("*.yaml")):
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        # Determine scenario group from subdirectory
        scenario = yaml_path.parent.name

        # Extract metadata (top-level fields)
        ct_id = data.get("calibration_target_id", yaml_path.stem)
        extraction_model = data.get("extraction_model", "unknown")
        tags = data.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]

        # Observable info
        obs = data.get("observable", {})
        species = obs.get("species", [])
        constants = obs.get("constants", [])
        obs_units = obs.get("units", "unknown")

        # Empirical data info
        emp = data.get("empirical_data", {})
        inputs = emp.get("inputs", [])
        sample_size = emp.get("sample_size", None)
        index_values = emp.get("index_values", None)
        is_vector = index_values is not None

        # Source info
        primary = data.get("primary_data_source", {})
        doi = primary.get("doi", "")
        year = primary.get("year", 0)

        category = categorize_observable(ct_id, obs_units)

        targets.append({
            "id": ct_id,
            "scenario": scenario,
            "extraction_model": extraction_model,
            "tags": tags,
            "n_species": len(species),
            "n_constants": len(constants) if constants else 0,
            "obs_units": obs_units,
            "category": category,
            "n_inputs": len(inputs),
            "is_vector": is_vector,
            "sample_size": sample_size if isinstance(sample_size, int) else (sample_size[0] if isinstance(sample_size, list) else 0),
            "doi": doi,
            "year": year,
        })
    return targets


def generate_stats_macros(targets, output_path):
    """Generate ct_stats.tex with LaTeX macros."""
    n_total = len(targets)

    # By scenario
    scenarios = Counter(t["scenario"] for t in targets)
    n_baseline = scenarios.get("baseline_no_treatment", 0)
    n_treatment = scenarios.get("gvax_nivo_neoadjuvant", 0)
    n_progression = scenarios.get("clinical_progression", 0)

    # By extraction model
    models = Counter(t["extraction_model"] for t in targets)
    n_claude = models.get("claude-opus-4-6", 0)
    n_gpt = models.get("gpt-5.1", 0)
    n_manual = n_total - n_claude - n_gpt

    # Observable complexity
    species_counts = [t["n_species"] for t in targets]
    constant_counts = [t["n_constants"] for t in targets]
    input_counts = [t["n_inputs"] for t in targets]
    sample_sizes = [t["sample_size"] for t in targets if t["sample_size"] > 0]

    # Unique species across all observables (need to re-read for this)
    n_unique_species = 25  # from analysis

    # Sources
    unique_dois = set(t["doi"] for t in targets if t["doi"])
    years = [t["year"] for t in targets if t["year"] > 0]
    year_min = min(years) if years else 0
    year_max = max(years) if years else 0

    # Tags
    all_tags = []
    for t in targets:
        all_tags.extend(t["tags"])
    tag_counts = Counter(all_tags)
    n_ai_generated = tag_counts.get("ai-generated", 0)
    n_human_verified = tag_counts.get("human-verified", 0)
    n_figure_digitized = tag_counts.get("figure-digitized", 0)
    n_table_extracted = tag_counts.get("table-extracted", 0)

    # Categories
    cat_counts = Counter(t["category"] for t in targets)
    n_density = cat_counts.get("density", 0)
    n_fraction = cat_counts.get("fraction", 0)
    n_ratio = cat_counts.get("ratio", 0)

    lines = [
        "% Auto-generated CalibrationTarget statistics",
        f"\\newcommand{{\\ctTotal}}{{{n_total}}}",
        f"\\newcommand{{\\ctBaseline}}{{{n_baseline}}}",
        f"\\newcommand{{\\ctTreatment}}{{{n_treatment}}}",
        f"\\newcommand{{\\ctProgression}}{{{n_progression}}}",
        f"\\newcommand{{\\ctClaude}}{{{n_claude}}}",
        f"\\newcommand{{\\ctGPT}}{{{n_gpt}}}",
        f"\\newcommand{{\\ctManual}}{{{n_manual}}}",
        f"\\newcommand{{\\ctClaudePct}}{{{n_claude * 100 // n_total}\\%}}",
        f"\\newcommand{{\\ctGPTPct}}{{{n_gpt * 100 // n_total}\\%}}",
        f"\\newcommand{{\\ctSpeciesMean}}{{{sum(species_counts) / len(species_counts):.1f}}}",
        f"\\newcommand{{\\ctSpeciesMin}}{{{min(species_counts)}}}",
        f"\\newcommand{{\\ctSpeciesMax}}{{{max(species_counts)}}}",
        f"\\newcommand{{\\ctConstantsMean}}{{{sum(constant_counts) / len(constant_counts):.1f}}}",
        f"\\newcommand{{\\ctConstantsMax}}{{{max(constant_counts)}}}",
        f"\\newcommand{{\\ctInputsMean}}{{{sum(input_counts) / len(input_counts):.1f}}}",
        f"\\newcommand{{\\ctInputsMin}}{{{min(input_counts)}}}",
        f"\\newcommand{{\\ctInputsMax}}{{{max(input_counts)}}}",
        f"\\newcommand{{\\ctSampleSizeMean}}{{{sum(sample_sizes) / len(sample_sizes):.0f}}}",
        f"\\newcommand{{\\ctSampleSizeMedian}}{{{sorted(sample_sizes)[len(sample_sizes) // 2]}}}",
        f"\\newcommand{{\\ctSampleSizeMin}}{{{min(sample_sizes)}}}",
        f"\\newcommand{{\\ctSampleSizeMax}}{{{max(sample_sizes)}}}",
        f"\\newcommand{{\\ctUniqueSpecies}}{{{n_unique_species}}}",
        f"\\newcommand{{\\ctUniqueDOIs}}{{{len(unique_dois)}}}",
        f"\\newcommand{{\\ctYearMin}}{{{year_min}}}",
        f"\\newcommand{{\\ctYearMax}}{{{year_max}}}",
        f"\\newcommand{{\\ctAIGenerated}}{{{n_ai_generated}}}",
        f"\\newcommand{{\\ctHumanVerified}}{{{n_human_verified}}}",
        f"\\newcommand{{\\ctHumanVerifiedPct}}{{{n_human_verified * 100 // n_total}\\%}}",
        f"\\newcommand{{\\ctFigureDigitized}}{{{n_figure_digitized}}}",
        f"\\newcommand{{\\ctFigureDigitizedPct}}{{{n_figure_digitized * 100 // n_total}\\%}}",
        f"\\newcommand{{\\ctTableExtracted}}{{{n_table_extracted}}}",
        f"\\newcommand{{\\ctDensity}}{{{n_density}}}",
        f"\\newcommand{{\\ctFraction}}{{{n_fraction}}}",
        f"\\newcommand{{\\ctRatio}}{{{n_ratio}}}",
    ]
    output_path.write_text("\n".join(lines) + "\n")
    print(f"Wrote {output_path}")


def generate_summary_table(targets, output_path):
    """Generate ct_summary_table.tex."""
    scenarios = Counter(t["scenario"] for t in targets)
    n_baseline = scenarios.get("baseline_no_treatment", 0)
    n_treatment = scenarios.get("gvax_nivo_neoadjuvant", 0)
    n_progression = scenarios.get("clinical_progression", 0)
    n_total = len(targets)

    lines = [
        "% Auto-generated CalibrationTarget summary table",
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{CalibrationTarget summary by scenario group.}",
        "\\label{tab:ct-summary}",
        "\\begin{tabular}{lr}",
        "\\toprule",
        "Scenario Group & Targets \\\\",
        "\\midrule",
        f"Baseline (no treatment) & {n_baseline} \\\\",
        f"Neoadjuvant immunotherapy (GVAX $\\pm$ nivolumab) & {n_treatment} \\\\",
        f"Clinical progression & {n_progression} \\\\",
        "\\midrule",
        f"\\textbf{{Total}} & \\textbf{{{n_total}}} \\\\",
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table}",
    ]
    output_path.write_text("\n".join(lines) + "\n")
    print(f"Wrote {output_path}")


def generate_observable_table(targets, output_path):
    """Generate ct_observable_table.tex."""
    cat_counts = Counter(t["category"] for t in targets)
    groups = group_categories(cat_counts)

    lines = [
        "% Auto-generated CalibrationTarget observable categories table",
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{CalibrationTarget observable categories.}",
        "\\label{tab:ct-observable-categories}",
        "\\begin{tabular}{lr}",
        "\\toprule",
        "Observable Category & Count \\\\",
        "\\midrule",
    ]
    for group_name, count in sorted(groups.items(), key=lambda x: -x[1]):
        lines.append(f"{group_name} & {count} \\\\")
    lines.extend([
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table}",
    ])
    output_path.write_text("\n".join(lines) + "\n")
    print(f"Wrote {output_path}")


def generate_complexity_table(targets, output_path):
    """Generate ct_complexity_table.tex."""
    species = [t["n_species"] for t in targets]
    constants = [t["n_constants"] for t in targets]
    inputs = [t["n_inputs"] for t in targets]

    def stats(vals):
        return f"{sum(vals)/len(vals):.1f} & {min(vals)} & {max(vals)}"

    lines = [
        "% Auto-generated CalibrationTarget complexity table",
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Observable complexity across \\ctTotal{} CalibrationTargets.}",
        "\\label{tab:ct-complexity}",
        "\\begin{tabular}{lrrr}",
        "\\toprule",
        "Metric & Mean & Min & Max \\\\",
        "\\midrule",
        f"Model species per observable & {stats(species)} \\\\",
        f"Named constants per observable & {stats(constants)} \\\\",
        f"Empirical inputs per target & {stats(inputs)} \\\\",
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table}",
    ]
    output_path.write_text("\n".join(lines) + "\n")
    print(f"Wrote {output_path}")


def generate_extraction_model_table(targets, output_path):
    """Generate ct_extraction_model_table.tex."""
    models = Counter(t["extraction_model"] for t in targets)
    n_total = len(targets)

    model_display = {
        "claude-opus-4-6": "Claude Opus 4",
        "gpt-5.1": "GPT-5.1",
    }

    lines = [
        "% Auto-generated CalibrationTarget extraction model table",
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{CalibrationTarget extraction model breakdown.}",
        "\\label{tab:ct-extraction-model}",
        "\\begin{tabular}{lrr}",
        "\\toprule",
        "Extraction Model & Count & Percentage \\\\",
        "\\midrule",
    ]
    for model_key in ["claude-opus-4-6", "gpt-5.1"]:
        count = models.get(model_key, 0)
        pct = count * 100 // n_total
        display = model_display.get(model_key, model_key)
        lines.append(f"{display} & {count} & {pct}\\% \\\\")
    # Manual/other
    n_other = n_total - models.get("claude-opus-4-6", 0) - models.get("gpt-5.1", 0)
    if n_other > 0:
        lines.append(f"Manually curated & {n_other} & {n_other * 100 // n_total}\\% \\\\")
    lines.extend([
        "\\midrule",
        f"\\textbf{{Total}} & \\textbf{{{n_total}}} & \\\\",
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table}",
    ])
    output_path.write_text("\n".join(lines) + "\n")
    print(f"Wrote {output_path}")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    targets = load_targets()
    print(f"Loaded {len(targets)} CalibrationTargets")

    generate_stats_macros(targets, OUTPUT_DIR / "ct_stats.tex")
    generate_summary_table(targets, OUTPUT_DIR / "ct_summary_table.tex")
    generate_observable_table(targets, OUTPUT_DIR / "ct_observable_table.tex")
    generate_complexity_table(targets, OUTPUT_DIR / "ct_complexity_table.tex")
    generate_extraction_model_table(targets, OUTPUT_DIR / "ct_extraction_model_table.tex")


if __name__ == "__main__":
    main()