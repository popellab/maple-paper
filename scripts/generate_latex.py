#!/usr/bin/env python3
"""
Generate LaTeX tables and figures from metrics.json.

This script reads the pre-computed metrics from generate_results.py
and generates all LaTeX output files. Run this when you need to
update formatting without re-running inference.

Usage:
    python scripts/generate_latex.py

Requires:
    paper/generated/metrics.json (from generate_results.py)
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR.parent / "paper" / "generated"
FIGURES_DIR = OUTPUT_DIR / "figures"
METRICS_PATH = OUTPUT_DIR / "metrics.json"

# =============================================================================
# Data Classes (reconstructed from JSON)
# =============================================================================


@dataclass
class ExtractionMetrics:
    """Aggregate metrics from LLM extraction process."""

    n_attempted: int = 0
    n_targets: int = 0
    n_failed: int = 0
    n_first_attempt_success: int = 0
    n_required_retries: int = 0
    total_retries: int = 0
    max_retries: int = 0
    total_duration_sec: float = 0.0
    total_tokens: int = 0
    total_cost: float = 0.0
    retry_distribution: dict = field(default_factory=dict)
    error_categories: dict = field(default_factory=dict)
    tool_usage: dict = field(default_factory=dict)
    per_target: list = field(default_factory=list)

    @property
    def first_attempt_rate(self) -> float:
        return self.n_first_attempt_success / self.n_targets if self.n_targets > 0 else 0

    @property
    def avg_duration_sec(self) -> float:
        return self.total_duration_sec / self.n_targets if self.n_targets > 0 else 0

    @property
    def avg_duration_min(self) -> float:
        return self.avg_duration_sec / 60

    @property
    def avg_tokens(self) -> int:
        return int(self.total_tokens / self.n_targets) if self.n_targets > 0 else 0

    @property
    def avg_cost(self) -> float:
        return self.total_cost / self.n_targets if self.n_targets > 0 else 0

    @classmethod
    def from_dict(cls, d: dict) -> "ExtractionMetrics":
        return cls(
            n_attempted=d.get("n_attempted", d.get("n_targets", 0)),
            n_targets=d.get("n_targets", 0),
            n_failed=d.get("n_failed", 0),
            n_first_attempt_success=d.get("n_first_attempt_success", 0),
            total_retries=d.get("total_retries", 0),
            max_retries=d.get("max_retries", 0),
            total_duration_sec=d.get("avg_duration_min", 0) * 60 * d.get("n_targets", 0),
            total_tokens=d.get("avg_tokens", 0) * d.get("n_targets", 0),
            total_cost=d.get("total_cost", 0),
            retry_distribution={int(k): v for k, v in d.get("retry_distribution", {}).items()},
            error_categories=d.get("error_categories", {}),
            tool_usage=d.get("tool_usage", {}),
            per_target=d.get("per_target", []),
        )


@dataclass
class CodeGenMetrics:
    """Metrics from Julia code generation."""

    n_targets: int = 0
    n_unique_parameters: int = 0
    n_shared_parameters: int = 0
    total_lines: int = 0
    parameters: list = field(default_factory=list)
    shared_params_detail: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "CodeGenMetrics":
        return cls(
            n_targets=d.get("n_targets", 0),
            n_unique_parameters=d.get("n_unique_parameters", 0),
            n_shared_parameters=d.get("n_shared_parameters", 0),
            total_lines=d.get("total_lines", 0),
            parameters=d.get("parameters", []),
            shared_params_detail=d.get("shared_params_detail", {}),
        )


@dataclass
class InferenceMetrics:
    """Metrics from Bayesian inference."""

    available: bool = False
    n_chains: int = 0
    n_samples: int = 0
    warmup: int = 0
    runtime_min: float = 0.0
    parameters: list = field(default_factory=list)
    ppc_results: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict, available: bool = False) -> "InferenceMetrics":
        return cls(available=available)


@dataclass
class YAMLMetrics:
    """Metrics extracted directly from YAML target files."""

    source_quality: dict = field(default_factory=dict)
    species_translation: dict = field(default_factory=dict)
    indication_match: dict = field(default_factory=dict)
    model_types: dict = field(default_factory=dict)
    complexity: list = field(default_factory=list)
    per_target: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "YAMLMetrics":
        return cls(
            source_quality=d.get("source_quality", {}),
            species_translation=d.get("species_translation", {}),
            indication_match=d.get("indication_match", {}),
            model_types=d.get("model_types", {}),
            complexity=d.get("complexity", []),
            per_target=d.get("per_target", []),
        )


# =============================================================================
# LaTeX Generation Functions
# =============================================================================


def generate_extraction_stats_tex(metrics: ExtractionMetrics) -> str:
    """Generate LaTeX macros for extraction statistics."""
    n_required_retries = metrics.n_targets - metrics.n_first_attempt_success
    total_tokens_m = metrics.total_tokens / 1_000_000

    # Error category percentages
    total_errors = sum(metrics.error_categories.values()) if metrics.error_categories else 1
    err_hallucination = metrics.error_categories.get("hallucination", 0)
    err_fabrication = metrics.error_categories.get("fabrication", 0)
    err_code = metrics.error_categories.get("code", 0)
    err_prior = metrics.error_categories.get("prior", 0)

    # Tool usage totals
    tool_web = sum(t.get("tool_calls", {}).get("web_search", 0) for t in metrics.per_target)
    tool_code = sum(t.get("tool_calls", {}).get("code_execution", 0) for t in metrics.per_target)

    return f"""% Auto-generated extraction statistics
\\newcommand{{\\nAttempted}}{{{metrics.n_attempted}}}
\\newcommand{{\\nTargets}}{{{metrics.n_targets}}}
\\newcommand{{\\nFailed}}{{{metrics.n_failed}}}
\\newcommand{{\\firstAttemptRate}}{{{100 * metrics.first_attempt_rate:.0f}\\%}}
\\newcommand{{\\nFirstAttemptSuccess}}{{{metrics.n_first_attempt_success}}}
\\newcommand{{\\nRequiredRetries}}{{{n_required_retries}}}
\\newcommand{{\\totalRetries}}{{{metrics.total_retries}}}
\\newcommand{{\\maxRetries}}{{{metrics.max_retries}}}
\\newcommand{{\\avgDurationMin}}{{{metrics.avg_duration_min:.1f}}}
\\newcommand{{\\avgTokens}}{{{metrics.avg_tokens:,}}}
\\newcommand{{\\avgCost}}{{{metrics.avg_cost:.2f}}}
\\newcommand{{\\totalCost}}{{{metrics.total_cost:.2f}}}
\\newcommand{{\\totalTokensM}}{{{total_tokens_m:.1f}}}
\\newcommand{{\\totalErrorsCaught}}{{{total_errors}}}
\\newcommand{{\\errHallucinationPct}}{{{100 * err_hallucination / total_errors:.0f}\\%}}
\\newcommand{{\\errFabricationPct}}{{{100 * err_fabrication / total_errors:.0f}\\%}}
\\newcommand{{\\errCodePct}}{{{100 * err_code / total_errors:.0f}\\%}}
\\newcommand{{\\errPriorPct}}{{{100 * err_prior / total_errors:.0f}\\%}}
\\newcommand{{\\toolWebSearch}}{{{tool_web}}}
\\newcommand{{\\toolCodeExecution}}{{{tool_code}}}
"""


def generate_codegen_stats_tex(codegen: CodeGenMetrics) -> str:
    """Generate LaTeX macros for code generation statistics."""
    # Format shared params list for paper
    shared_list = ", ".join(
        f"\\texttt{{{p.replace('_', chr(92) + '_')}}}"
        for p in sorted(codegen.shared_params_detail.keys())
    ) if codegen.shared_params_detail else "none"

    return f"""% Auto-generated code generation statistics
\\newcommand{{\\nCodeTargets}}{{{codegen.n_targets}}}
\\newcommand{{\\nUniqueParams}}{{{codegen.n_unique_parameters}}}
\\newcommand{{\\nSharedParams}}{{{codegen.n_shared_parameters}}}
\\newcommand{{\\totalJuliaLines}}{{{codegen.total_lines}}}
\\newcommand{{\\nCodeLines}}{{{codegen.total_lines}}}
\\newcommand{{\\sharedParamsList}}{{{shared_list}}}
"""


def _clean_param_name(filename: str) -> str:
    """Convert filename to clean parameter name for display."""
    import re
    # Remove .yaml extension
    name = filename.replace(".yaml", "")
    # Remove _PDAC_derivNNN suffix
    name = re.sub(r"_PDAC_deriv\d+$", "", name)
    # Format as texttt with escaped underscores
    name_escaped = name.replace("_", r"\_")
    return f"\\texttt{{{name_escaped}}}"


def generate_extraction_table_tex(metrics: ExtractionMetrics) -> str:
    """Generate LaTeX table of extraction metrics per target."""
    rows = []
    for t in sorted(metrics.per_target, key=lambda x: x["file"]):
        name = _clean_param_name(t["file"])
        retries = t.get("retries", 0)
        duration = t.get("duration", 0) / 60  # Convert to minutes
        tokens = t.get("tokens", 0)
        rows.append(f"{name} & {retries} & {duration:.1f} & {tokens:,}")

    rows_tex = " \\\\\n".join(rows)

    return rf"""% Auto-generated extraction metrics table
\begin{{table}}[htbp]
\centering
\caption{{\revisedtext{{Extraction metrics for the \nTargets{{}} Logfire-instrumented SubmodelTargets. Retries: automated re-extractions triggered by validator failures before any human review. Duration: wall-clock extraction time. Tokens: total LLM tokens consumed. The final row reports the mean across targets.}}}}
\label{{tab:extraction}}
\begin{{tabular}}{{lccc}}
\toprule
Target & Retries & Duration (min) & Tokens \\
\midrule
{rows_tex} \\
\midrule
\textbf{{Average}} & \textbf{{{metrics.total_retries / max(metrics.n_targets, 1):.1f}}} & \textbf{{{metrics.avg_duration_min:.1f}}} & \textbf{{{metrics.avg_tokens:,}}} \\
\bottomrule
\end{{tabular}}
\end{{table}}"""


def generate_retry_table_tex(metrics: ExtractionMetrics) -> str:
    """Generate LaTeX table of retry distribution."""
    rows = []
    for retries in sorted(metrics.retry_distribution.keys()):
        count = metrics.retry_distribution[retries]
        pct = 100 * count / metrics.n_targets if metrics.n_targets > 0 else 0
        rows.append(f"{retries} & {count} & {pct:.0f}\\%")

    rows_tex = " \\\\\n".join(rows)

    return rf"""% Auto-generated retry distribution table
\begin{{table}}[htbp]
\centering
\caption{{Distribution of retry attempts across SubmodelTargets.}}
\label{{tab:retries}}
\begin{{tabular}}{{ccc}}
\toprule
Retries & Count & \% \\
\midrule
{rows_tex} \\
\bottomrule
\end{{tabular}}
\end{{table}}"""


def generate_error_categories_table_tex(metrics: ExtractionMetrics) -> str:
    """Generate LaTeX table of error categories."""
    if not metrics.error_categories:
        return "% No error categories recorded"

    rows = []
    total = sum(metrics.error_categories.values())
    for cat, count in sorted(metrics.error_categories.items(), key=lambda x: -x[1]):
        cat_tex = cat.replace("_", r"\_")
        pct = 100 * count / total if total > 0 else 0
        rows.append(f"{cat_tex} & {count} & {pct:.0f}\\%")

    rows_tex = " \\\\\n".join(rows)

    return rf"""% Auto-generated error categories table
\begin{{table}}[htbp]
\centering
\caption{{Categories of validation exceptions captured during batch-extraction tracing. The total is a lower bound on validator interventions: tracing recorded a representative subset of exceptions per target, whereas the validators triggered \totalRetries{{}} retries across the \nTargets{{}} instrumented extractions overall. Units: incorrect or inconsistent unit conversions. Prior: proposed uncertainty range incompatible with stated translation context. Fabrication: LLM-generated DOIs or citations that do not resolve to real publications. Code: observation function fails unit checks or execution. Hallucination: extracted values not found in the cited source text.}}
\label{{tab:error-categories}}
\begin{{tabular}}{{lcc}}
\toprule
Error Category & Count & \% \\
\midrule
{rows_tex} \\
\midrule
\textbf{{Total}} & \textbf{{{total}}} & \\
\bottomrule
\end{{tabular}}
\end{{table}}"""


def generate_convergence_table_tex(
    inference: InferenceMetrics, codegen: CodeGenMetrics, inference_results: Optional[dict]
) -> str:
    """Generate LaTeX table of convergence diagnostics."""
    if not inference_results or "parameters" not in inference_results:
        return """% Placeholder convergence table - run inference to populate
\\begin{table}[htbp]
\\centering
\\caption{Convergence diagnostics for MCMC sampling. Run inference to populate.}
\\label{tab:convergence}
\\begin{tabular}{lccc}
\\toprule
Parameter & $\\hat{R}$ & ESS (bulk) & ESS (tail) \\\\
\\midrule
\\textit{Run inference to populate} & --- & --- & --- \\\\
\\bottomrule
\\end{tabular}
\\end{table}"""

    rows = []
    for param, vals in sorted(inference_results["parameters"].items()):
        param_tex = f"\\texttt{{{param.replace('_', chr(92) + '_')}}}"
        rhat = vals.get("rhat", 0)
        ess_bulk = vals.get("ess_bulk", 0)
        ess_tail = vals.get("ess_tail", 0)
        rows.append(f"{param_tex} & {rhat:.3f} & {ess_bulk:.0f} & {ess_tail:.0f}")

    rows_tex = " \\\\\n".join(rows)

    return rf"""% Auto-generated convergence table
\begin{{table}}[htbp]
\centering
\caption{{Convergence diagnostics for MCMC sampling. All $\hat{{R}} < 1.01$ indicates convergence.}}
\label{{tab:convergence}}
\begin{{tabular}}{{lccc}}
\toprule
Parameter & $\hat{{R}}$ & ESS (bulk) & ESS (tail) \\
\midrule
{rows_tex} \\
\bottomrule
\end{{tabular}}
\end{{table}}"""


def generate_ppc_table_tex(inference: InferenceMetrics, codegen: CodeGenMetrics) -> str:
    """Generate LaTeX table of posterior predictive checks."""
    return """% Placeholder PPC table
\\begin{table}[htbp]
\\centering
\\caption{Posterior predictive checks comparing model predictions to observed data.}
\\label{tab:ppc}
\\begin{tabular}{lccc}
\\toprule
Target & Observed & Predicted (median) & 90\\% PI Coverage \\\\
\\midrule
\\textit{See posterior table for results} & --- & --- & --- \\\\
\\bottomrule
\\end{tabular}
\\end{table}"""


def _load_param_units() -> dict:
    """Load parameter units from model_structure.json."""
    model_path = SCRIPT_DIR.parent / "batch_extraction" / "model_structure.json"
    if not model_path.exists():
        return {}
    with open(model_path) as f:
        data = json.load(f)
    units = {p["name"]: p["units"] for p in data.get("parameters", [])}
    # Parameters not present in model_structure.json (auxiliary or submodel-only),
    # with units sourced from model_definitions.json and the curated SubmodelTarget YAMLs
    units["L_leukocyte_T"] = "cell/milliliter"
    units["k_apsc_death"] = "1/day"
    units["k_psc_activation"] = "1/day"
    units["cd8_exclusion_fraction"] = "dimensionless"
    return units


def _format_units_latex(units: str) -> str:
    """Convert units string to LaTeX format."""
    import re

    if not units:
        return "---"
    if units == "dimensionless":
        return "dimensionless"

    # Handle specific complex units first
    if units == "1/(centimeter^3*minute)":
        return r"min$^{-1}\cdot$cm$^{-3}$"
    if units == "nanomole/cell/day":
        return r"nmol$\cdot$cell$^{-1}\cdot$day$^{-1}$"
    if units == "cell/(milliliter*day)":
        return r"cell$\cdot$mL$^{-1}\cdot$day$^{-1}$"

    u = units
    # Handle common unit abbreviations
    u = u.replace("milliliter", "mL")
    u = u.replace("milligram", "mg")
    u = u.replace("centimeter", "cm")
    u = u.replace("nanomole", "nmol")
    u = u.replace("minute", "min")

    # Handle simple reciprocal pattern "1/<unit>" (e.g. 1/day, 1/hour)
    m = re.fullmatch(r"1/(\w+)", u)
    if m:
        return rf"{m.group(1)}$^{{-1}}$"

    # Handle exponents - wrap in math mode
    u = re.sub(r"\^(\d+)", r"$^{\1}$", u)
    u = re.sub(r"\^(-\d+)", r"$^{\1}$", u)

    # Handle multiplication
    u = u.replace("*", r"$\cdot$")

    return u


# Auxiliary parameters introduced during extraction (not in the QSP model itself).
# These are bridging quantities estimated within a target rather than model rate
# constants; submodel-only model parameters absent from model_structure.json
# (e.g. k_apsc_death, k_psc_activation) are NOT auxiliary and are excluded here.
AUXILIARY_PARAMS = {"L_leukocyte_T", "cd8_exclusion_fraction"}


def generate_posterior_table_tex(codegen: CodeGenMetrics, inference_results: Optional[dict]) -> str:
    """Generate LaTeX table of posterior parameter estimates."""
    if not inference_results or "parameters" not in inference_results:
        return """% Placeholder posterior table - run inference to populate
\\begin{table}[htbp]
\\centering
\\caption{Posterior parameter estimates from joint Bayesian inference.}
\\label{tab:posteriors}
\\begin{tabular}{lccc}
\\toprule
Parameter & Median & 90\\% CI & Units \\\\
\\midrule
\\textit{Run inference to populate} & --- & --- & --- \\\\
\\bottomrule
\\end{tabular}
\\end{table}"""

    param_units = _load_param_units()

    rows = []
    for param, vals in sorted(inference_results["parameters"].items()):
        param_tex = f"\\texttt{{{param.replace('_', chr(92) + '_')}}}"
        if param in AUXILIARY_PARAMS:
            param_tex += "$^\\dagger$"
        units = _format_units_latex(param_units.get(param, ""))
        if vals:
            med = vals.get("median", 0)
            ci_lo = vals.get("ci_05", 0)
            ci_hi = vals.get("ci_95", 0)

            def fmt(x):
                if x == 0:
                    return "0"
                if abs(x) < 0.01 or abs(x) > 1000:
                    return f"{x:.2e}"
                return f"{x:.3g}"

            rows.append(f"{param_tex} & {fmt(med)} & [{fmt(ci_lo)}, {fmt(ci_hi)}] & {units}")
        else:
            rows.append(f"{param_tex} & --- & --- & ---")

    rows_tex = " \\\\\n".join(rows)

    return rf"""% Auto-generated posterior table
\begin{{table}}[htbp]
\centering
\caption{{Posterior parameter estimates from joint Bayesian inference. Credible intervals are 90\% highest density intervals. $^\dagger$Auxiliary parameter introduced during extraction.}}
\label{{tab:posteriors}}
\begin{{tabular}}{{lccc}}
\toprule
Parameter & Median & 90\% CI & Units \\
\midrule
{rows_tex} \\
\bottomrule
\end{{tabular}}
\end{{table}}"""


def generate_inference_stats_tex(inference_results: Optional[dict]) -> str:
    """Generate LaTeX macros for inference statistics."""
    lines = ["% Auto-generated inference statistics"]

    if not inference_results or "parameters" not in inference_results:
        lines.append("% No inference results available")
        lines.append("\\newcommand{\\inferenceAvailable}{false}")
        return "\n".join(lines)

    lines.append("\\newcommand{\\inferenceAvailable}{true}")
    lines.append(f"\\newcommand{{\\nChains}}{{{inference_results.get('n_chains', 4)}}}")
    lines.append(f"\\newcommand{{\\nSamples}}{{{inference_results.get('n_samples', 1000)}}}")

    # Add per-parameter macros
    for param, vals in inference_results.get("parameters", {}).items():
        digit_words = {
            "0": "Zero",
            "1": "One",
            "2": "Two",
            "3": "Three",
            "4": "Four",
            "5": "Five",
            "6": "Six",
            "7": "Seven",
            "8": "Eight",
            "9": "Nine",
        }
        macro_name = ""
        for word in param.split("_"):
            word_clean = ""
            for char in word:
                if char.isdigit():
                    word_clean += digit_words[char]
                else:
                    word_clean += char
            macro_name += word_clean.capitalize()

        med = vals.get("median", 0)
        ci_lo = vals.get("ci_05", 0)
        ci_hi = vals.get("ci_95", 0)
        rhat = vals.get("rhat", 0)

        def fmt(x):
            if abs(x) < 0.01 or abs(x) > 1000:
                return f"{x:.2e}"
            return f"{x:.3g}"

        lines.append(f"\\newcommand{{\\{macro_name}Med}}{{{fmt(med)}}}")
        lines.append(f"\\newcommand{{\\{macro_name}CILo}}{{{fmt(ci_lo)}}}")
        lines.append(f"\\newcommand{{\\{macro_name}CIHi}}{{{fmt(ci_hi)}}}")
        lines.append(f"\\newcommand{{\\{macro_name}Rhat}}{{{rhat:.3f}}}")

    return "\n".join(lines)


def generate_source_quality_table_tex(yaml_metrics: YAMLMetrics) -> str:
    """Generate LaTeX table of source quality distribution."""
    if not yaml_metrics.source_quality:
        return "% No source quality data available"

    desc = {
        "primary_human_clinical": "Clinical trial or observational study",
        "primary_human_in_vitro": "Human cell/tissue in vitro",
        "primary_animal_in_vivo": "Animal model in vivo",
        "primary_animal_in_vitro": "Animal cell/tissue in vitro",
        "review_article": "Review/meta-analysis",
        "database": "Curated database",
    }

    rows = []
    total = sum(yaml_metrics.source_quality.values())
    for quality, count in sorted(yaml_metrics.source_quality.items(), key=lambda x: -x[1]):
        quality_tex = quality.replace("_", r"\_")
        pct = 100 * count / total if total > 0 else 0
        description = desc.get(quality, quality)
        rows.append(f"{quality_tex} & {count} & {pct:.0f}\\%")

    rows_tex = " \\\\\n".join(rows)

    return rf"""% Auto-generated source quality table
\begin{{table}}[htbp]
\centering
\caption{{Distribution of primary data source quality across SubmodelTargets.}}
\label{{tab:source-quality}}
\begin{{tabular}}{{lcc}}
\toprule
Source Quality & Count & \% \\
\midrule
{rows_tex} \\
\midrule
\textbf{{Total}} & \textbf{{{total}}} & \\
\bottomrule
\end{{tabular}}
\end{{table}}"""


def generate_species_table_tex(yaml_metrics: YAMLMetrics) -> str:
    """Generate LaTeX table of species translation."""
    if not yaml_metrics.species_translation:
        return "% No species translation data available"

    rows = []
    total = sum(yaml_metrics.species_translation.values())
    for trans, count in sorted(yaml_metrics.species_translation.items(), key=lambda x: -x[1]):
        pct = 100 * count / total if total > 0 else 0
        # Escape underscores and arrow for LaTeX
        trans_tex = trans.replace("_", r"\_").replace("→", r"$\rightarrow$")
        rows.append(f"{trans_tex} & {count} & {pct:.0f}\\%")

    rows_tex = " \\\\\n".join(rows)

    return rf"""% Auto-generated species translation table
\begin{{table}}[htbp]
\centering
\caption{{Species translation from data source to model target. Human$\rightarrow$human indicates no cross-species translation required.}}
\label{{tab:species}}
\begin{{tabular}}{{lcc}}
\toprule
Translation & Count & \% \\
\midrule
{rows_tex} \\
\midrule
\textbf{{Total}} & \textbf{{{total}}} & \\
\bottomrule
\end{{tabular}}
\end{{table}}"""


def generate_indication_table_tex(yaml_metrics: YAMLMetrics) -> str:
    """Generate LaTeX table of indication match."""
    if not yaml_metrics.indication_match:
        return "% No indication match data available"

    desc = {
        "exact": "Data from PDAC patients/models",
        "proxy": "Proxy indication (e.g., other cancers, fibrosis)",
        "related": "Related indication (same organ/disease class)",
        "general": "General physiological data",
        "unknown": "Not specified",
    }

    rows = []
    total = sum(yaml_metrics.indication_match.values())
    for match, count in sorted(yaml_metrics.indication_match.items(), key=lambda x: -x[1]):
        pct = 100 * count / total if total > 0 else 0
        description = desc.get(match, match)
        rows.append(f"{description} & {count} & {pct:.0f}\\%")

    rows_tex = " \\\\\n".join(rows)

    return rf"""% Auto-generated indication match table
\begin{{table}}[htbp]
\centering
\caption{{How closely the data source indication matches the model target (PDAC).}}
\label{{tab:indication}}
\begin{{tabular}}{{lcc}}
\toprule
Indication Match & Count & \% \\
\midrule
{rows_tex} \\
\midrule
\textbf{{Total}} & \textbf{{{total}}} & \\
\bottomrule
\end{{tabular}}
\end{{table}}"""


def generate_model_type_table_tex(yaml_metrics: YAMLMetrics) -> str:
    """Generate LaTeX table of model types."""
    if not yaml_metrics.model_types:
        return "% No model type data available"

    desc = {
        "algebraic": "Algebraic (closed-form)",
        "first_order_decay": "First-order decay ODE",
        "two_state": "Two-state ODE",
        "ode": "General ODE",
        "batch_accumulation": "Batch accumulation",
        "steady_state_density": "Steady-state density",
        "steady_state_fraction": "Steady-state fraction",
        "steady_state_concentration": "Steady-state concentration",
        "steady_state_ratio": "Steady-state ratio",
        "steady_state_proliferation_index": "Steady-state proliferation index",
    }

    rows = []
    total = sum(yaml_metrics.model_types.values())
    for mtype, count in sorted(yaml_metrics.model_types.items(), key=lambda x: -x[1]):
        pct = 100 * count / total if total > 0 else 0
        description = desc.get(mtype, mtype)
        rows.append(f"{description} & {count} & {pct:.0f}\\%")

    rows_tex = " \\\\\n".join(rows)

    return rf"""% Auto-generated model type table
\begin{{table}}[htbp]
\centering
\caption{{Distribution of forward model types used in calibration submodels.}}
\label{{tab:model-type-dist}}
\begin{{tabular}}{{lcc}}
\toprule
Model Type & Count & \% \\
\midrule
{rows_tex} \\
\midrule
\textbf{{Total}} & \textbf{{{total}}} & \\
\bottomrule
\end{{tabular}}
\end{{table}}"""


def generate_tool_usage_table_tex(metrics: ExtractionMetrics) -> str:
    """Generate LaTeX table of tool usage during extraction."""
    if not metrics.per_target:
        return "% No tool usage data available"

    rows = []
    total_web = 0
    total_code = 0
    for t in sorted(metrics.per_target, key=lambda x: x["file"]):
        name = _clean_param_name(t["file"])
        tool_calls = t.get("tool_calls", {})
        web_search = tool_calls.get("web_search", 0)
        code_exec = tool_calls.get("code_execution", 0)
        retries = t.get("retries", 0)
        total_web += web_search
        total_code += code_exec
        rows.append(f"{name} & {web_search} & {code_exec} & {retries}")

    rows_tex = " \\\\\n".join(rows)

    return rf"""% Auto-generated tool usage table
\begin{{table}}[htbp]
\centering
\caption{{Tool usage during LLM extraction. Web search retrieves literature; code execution validates observation derivation functions.}}
\label{{tab:tool-usage}}
\begin{{tabular}}{{lccc}}
\toprule
Target & Web Search & Code Exec & Retries \\
\midrule
{rows_tex} \\
\midrule
\textbf{{Total}} & \textbf{{{total_web}}} & \textbf{{{total_code}}} & \\
\bottomrule
\end{{tabular}}
\end{{table}}"""


def generate_complexity_table_tex(yaml_metrics: YAMLMetrics) -> str:
    """Generate LaTeX table of target complexity."""
    if not yaml_metrics.complexity:
        return "% No complexity data available"

    rows = []
    total_inputs = 0
    total_params = 0
    total_states = 0
    total_lines = 0
    for c in sorted(yaml_metrics.complexity, key=lambda x: x.get("file", x.get("target", ""))):
        # Use file field if available, otherwise target
        raw_name = c.get("file", c.get("target", ""))
        name = _clean_param_name(raw_name) if raw_name.endswith(".yaml") else _clean_param_name(raw_name + ".yaml")
        inputs = c.get("n_inputs", 0)
        params = c.get("n_params", 0)
        states = c.get("n_states", 0)
        lines = c.get("code_lines", 0)
        total_inputs += inputs
        total_params += params
        total_states += states
        total_lines += lines
        rows.append(f"{name} & {inputs} & {params} & {states} & {lines}")

    rows_tex = " \\\\\n".join(rows)
    n = len(yaml_metrics.complexity)
    avg_inputs = total_inputs / n if n > 0 else 0
    avg_params = total_params / n if n > 0 else 0
    avg_states = total_states / n if n > 0 else 0
    avg_lines = total_lines / n if n > 0 else 0

    return rf"""% Auto-generated complexity table
\begin{{table}}[htbp]
\centering
\caption{{Complexity metrics for SubmodelTargets. Inputs are experimental values; parameters are model rate constants; states are ODE variables.}}
\label{{tab:complexity}}
\begin{{tabular}}{{lcccc}}
\toprule
Target & Inputs & Params & States & Code Lines \\
\midrule
{rows_tex} \\
\midrule
\textbf{{Average}} & \textbf{{{avg_inputs:.1f}}} & \textbf{{{avg_params:.1f}}} & \textbf{{{avg_states:.1f}}} & \textbf{{{avg_lines:.1f}}} \\
\bottomrule
\end{{tabular}}
\end{{table}}"""


def generate_yaml_stats_tex(yaml_metrics: YAMLMetrics) -> str:
    """Generate LaTeX macros for YAML-derived statistics."""
    lines = ["% Auto-generated YAML-derived statistics"]

    # Total targets
    total = len(yaml_metrics.complexity) if yaml_metrics.complexity else sum(yaml_metrics.source_quality.values())
    lines.append(f"\\newcommand{{\\nYAMLTargets}}{{{total}}}")

    # Average complexity
    if yaml_metrics.complexity:
        avg_inputs = sum(c.get("n_inputs", 0) for c in yaml_metrics.complexity) / len(yaml_metrics.complexity)
        avg_lines = sum(c.get("code_lines", 0) for c in yaml_metrics.complexity) / len(yaml_metrics.complexity)
        lines.append(f"\\newcommand{{\\avgInputs}}{{{avg_inputs:.1f}}}")
        lines.append(f"\\newcommand{{\\avgCodeLines}}{{{int(avg_lines)}}}")

    # Source quality macros
    total_sq = sum(yaml_metrics.source_quality.values())
    for sq, count in yaml_metrics.source_quality.items():
        sq_name = sq.replace("_", " ").title().replace(" ", "")
        pct = round(100 * count / total_sq) if total_sq > 0 else 0
        lines.append(f"\\newcommand{{\\sq{sq_name}}}{{{count}}}")
        lines.append(f"\\newcommand{{\\sq{sq_name}Pct}}{{{pct}\\%}}")

    # Species translation macros
    total_sp = sum(yaml_metrics.species_translation.values())
    for sp, count in yaml_metrics.species_translation.items():
        sp_name = sp.replace("→", "To").replace("_", "").title()
        pct = round(100 * count / total_sp) if total_sp > 0 else 0
        lines.append(f"\\newcommand{{\\sp{sp_name}}}{{{count}}}")
        lines.append(f"\\newcommand{{\\sp{sp_name}Pct}}{{{pct}\\%}}")

    # Indication match macros
    total_ind = sum(yaml_metrics.indication_match.values())
    for ind, count in yaml_metrics.indication_match.items():
        ind_name = ind.title()
        pct = round(100 * count / total_ind) if total_ind > 0 else 0
        lines.append(f"\\newcommand{{\\ind{ind_name}}}{{{count}}}")
        lines.append(f"\\newcommand{{\\ind{ind_name}Pct}}{{{pct}\\%}}")

    # Model type macros
    total_mt = sum(yaml_metrics.model_types.values())
    for mt, count in yaml_metrics.model_types.items():
        mt_name = mt.replace("_", " ").title().replace(" ", "")
        pct = round(100 * count / total_mt) if total_mt > 0 else 0
        lines.append(f"\\newcommand{{\\mt{mt_name}}}{{{count}}}")
        lines.append(f"\\newcommand{{\\mt{mt_name}Pct}}{{{pct}\\%}}")

    return "\n".join(lines)


# =============================================================================
# Figure Generation Functions
# =============================================================================


def generate_retry_distribution_figure(metrics: ExtractionMetrics, output_path: Path):
    """Generate retry distribution bar chart."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Warning: matplotlib not available. Skipping figure generation.")
        return

    retries = sorted(metrics.retry_distribution.keys())
    counts = [metrics.retry_distribution[r] for r in retries]

    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(retries, counts, color="steelblue", edgecolor="black", alpha=0.8)

    for bar, count in zip(bars, counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.3,
            str(count),
            ha="center",
            va="bottom",
            fontsize=10,
        )

    ax.set_xlabel("Number of Retries")
    ax.set_ylabel("Number of Targets")
    ax.set_title("Retry Distribution Across Calibration Targets")
    ax.set_xticks(retries)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {output_path}")


def generate_error_category_figure(metrics: ExtractionMetrics, output_path: Path):
    """Generate error category horizontal bar chart."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return

    if not metrics.error_categories:
        return

    cats = sorted(metrics.error_categories.keys(), key=lambda x: metrics.error_categories[x])
    counts = [metrics.error_categories[c] for c in cats]

    fig, ax = plt.subplots(figsize=(8, max(4, len(cats) * 0.4)))
    bars = ax.barh(cats, counts, color="coral", edgecolor="black", alpha=0.8)

    for bar, count in zip(bars, counts):
        ax.text(
            bar.get_width() + 0.2,
            bar.get_y() + bar.get_height() / 2,
            str(count),
            ha="left",
            va="center",
            fontsize=9,
        )

    ax.set_xlabel("Count")
    ax.set_title("Error Categories During Extraction")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {output_path}")


def generate_tool_usage_figure(metrics: ExtractionMetrics, output_path: Path):
    """Generate tool usage pie chart."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return

    if not metrics.tool_usage:
        return

    tools = list(metrics.tool_usage.keys())
    counts = list(metrics.tool_usage.values())

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(
        counts, labels=tools, autopct="%1.0f%%", startangle=90, colors=plt.cm.Pastel1.colors
    )
    ax.set_title("Tool Usage Distribution")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {output_path}")


def generate_token_cost_figure(metrics: ExtractionMetrics, output_path: Path):
    """Generate token/cost distribution figure."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return

    if not metrics.per_target:
        return

    tokens = [t.get("tokens", 0) for t in metrics.per_target]
    costs = [t.get("cost", 0) for t in metrics.per_target]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    ax1.hist(tokens, bins=10, color="steelblue", edgecolor="black", alpha=0.8)
    ax1.set_xlabel("Tokens")
    ax1.set_ylabel("Count")
    ax1.set_title("Token Distribution")

    ax2.hist(costs, bins=10, color="seagreen", edgecolor="black", alpha=0.8)
    ax2.set_xlabel("Cost (USD)")
    ax2.set_ylabel("Count")
    ax2.set_title("Cost Distribution")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {output_path}")


def _parse_priors_from_julia(julia_path: Path) -> dict:
    """Parse prior distributions from Julia calibration script."""
    import re

    priors = {}
    if not julia_path.exists():
        return priors

    content = julia_path.read_text()

    # Match patterns like :param_name => LogNormal(mu, sigma) or Normal(mu, sigma)
    pattern = r":(\w+)\s*=>\s*(LogNormal|Normal)\(([^,]+),\s*([^)]+)\)"
    for match in re.finditer(pattern, content):
        param = match.group(1)
        dist_type = match.group(2)
        param1 = float(match.group(3))
        param2 = float(match.group(4))
        priors[param] = {"type": dist_type, "param1": param1, "param2": param2}

    return priors


def _format_units_matplotlib(units: str) -> str:
    """Convert units string to matplotlib-friendly format."""
    if units == "dimensionless" or not units:
        return ""

    u = units
    # Abbreviations
    u = u.replace("milliliter", "mL")
    u = u.replace("milligram", "mg")
    u = u.replace("centimeter", "cm")
    u = u.replace("nanomole", "nmol")
    u = u.replace("minute", "min")

    # Handle specific complex units
    if "1/(centimeter^3*minute)" in units or "1/(cm^3*min)" in u:
        return "min⁻¹·cm⁻³"
    if "nanomole/cell/day" in units or "nmol/cell/day" in u:
        return "nmol·cell⁻¹·day⁻¹"
    if "cell/(milliliter*day)" in units or "cell/(mL*day)" in u:
        return "cell·mL⁻¹·day⁻¹"
    if u == "1/day":
        return "day⁻¹"

    # General replacements
    u = u.replace("^-1", "⁻¹")
    u = u.replace("^-3", "⁻³")
    u = u.replace("^3", "³")
    u = u.replace("*", "·")

    return u


def generate_posterior_figure(inference_results: dict, output_path: Path):
    """Generate histogram/density plots of posterior parameter estimates from raw samples."""
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        from scipy import stats
    except ImportError:
        print("Warning: matplotlib/scipy not available. Skipping posterior figure.")
        return

    if not inference_results or "parameters" not in inference_results:
        print("Warning: No inference results. Skipping posterior figure.")
        return

    # Load raw posterior samples from fixed path
    samples_path = OUTPUT_DIR / "posterior_samples.json"
    if not samples_path.exists():
        print("Warning: posterior_samples.json not found. Skipping posterior figure.")
        return

    with open(samples_path) as f:
        posterior_samples = json.load(f)

    # Parse priors from Julia script
    julia_path = SCRIPT_DIR / "joint_calibration.jl"
    priors = _parse_priors_from_julia(julia_path)

    params = inference_results["parameters"]
    n_params = len(params)

    # Load units for parameter labels
    param_units = _load_param_units()

    # Sort parameters alphabetically
    sorted_params = sorted(params.keys())

    # Calculate grid dimensions
    n_cols = 4
    n_rows = (n_params + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(14, 3 * n_rows))
    axes = axes.flatten()

    for i, param in enumerate(sorted_params):
        if i >= len(axes):
            break

        ax = axes[i]
        vals = params[param]

        # Get raw samples
        samples = np.array(posterior_samples.get(param, []))
        units_str = _format_units_matplotlib(param_units.get(param, ""))
        title = param.replace("_", " ")
        if units_str:
            title += f" ({units_str})"

        if len(samples) == 0:
            ax.text(0.5, 0.5, "No samples", transform=ax.transAxes, ha="center")
            ax.set_title(title, fontsize=9)
            continue

        med = vals.get("median", np.median(samples))
        ci_lo = vals.get("ci_05", np.percentile(samples, 5))
        ci_hi = vals.get("ci_95", np.percentile(samples, 95))

        # Plot histogram with density
        ax.hist(samples, bins=50, density=True, color="steelblue", alpha=0.6, edgecolor="none")

        # X range for plotting densities
        x_min = min(samples.min(), np.percentile(samples, 0.1))
        x_max = max(samples.max(), np.percentile(samples, 99.9))
        x_range = np.linspace(x_min, x_max, 200)

        # Overlay prior distribution (gray, underneath)
        if param in priors:
            prior_info = priors[param]
            try:
                if prior_info["type"] == "LogNormal":
                    prior_dist = stats.lognorm(s=prior_info["param2"], scale=np.exp(prior_info["param1"]))
                elif prior_info["type"] == "Normal":
                    prior_dist = stats.norm(loc=prior_info["param1"], scale=prior_info["param2"])
                else:
                    prior_dist = None

                if prior_dist:
                    prior_pdf = prior_dist.pdf(x_range)
                    # Scale prior to be visible but not overwhelming
                    ax.fill_between(x_range, prior_pdf, alpha=0.2, color="gray", label="Prior")
                    ax.plot(x_range, prior_pdf, color="gray", linewidth=1, alpha=0.7)
            except Exception:
                pass  # Skip prior if it fails

        # Overlay posterior KDE
        try:
            kde = stats.gaussian_kde(samples)
            ax.plot(x_range, kde(x_range), color="darkblue", linewidth=1.5, label="Posterior")
        except Exception:
            pass  # Skip KDE if it fails

        # Add median line
        ax.axvline(med, color="red", linewidth=2, linestyle="-")

        # Add CI lines
        ax.axvline(ci_lo, color="red", linewidth=1, linestyle="--", alpha=0.7)
        ax.axvline(ci_hi, color="red", linewidth=1, linestyle="--", alpha=0.7)

        # Format title and axes
        ax.set_title(title, fontsize=11)
        ax.set_ylabel("")
        ax.set_yticks([])
        ax.ticklabel_format(style="scientific", axis="x", scilimits=(-2, 3))
        ax.tick_params(axis="x", labelsize=10, rotation=45)

    # Hide unused subplots
    for i in range(n_params, len(axes)):
        axes[i].set_visible(False)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {output_path}")


# =============================================================================
# Main
# =============================================================================


def main():
    print("=" * 60)
    print("Generating LaTeX from metrics.json")
    print("=" * 60)

    # Check for metrics.json
    if not METRICS_PATH.exists():
        print(f"Error: {METRICS_PATH} not found.")
        print("Run 'python scripts/generate_results.py' first to generate metrics.")
        return 1

    # Load metrics
    print(f"\nLoading metrics from {METRICS_PATH}...")
    with open(METRICS_PATH) as f:
        data = json.load(f)

    # Reconstruct dataclasses
    extraction = ExtractionMetrics.from_dict(data.get("extraction", {}))
    codegen = CodeGenMetrics.from_dict(data.get("codegen", {}))
    yaml_metrics = YAMLMetrics.from_dict(data.get("yaml_metrics", {}))
    inference = InferenceMetrics.from_dict({}, data.get("inference_available", False))

    # Load inference results from fixed path
    inference_results = None
    inference_path = OUTPUT_DIR / "inference_results.json"
    if inference_path.exists():
        print(f"  Using inference results from {inference_path}")
        with open(inference_path) as f:
            inference_results = json.load(f)
    else:
        inference_results = data.get("inference_results")

    print(f"  Extraction: {extraction.n_targets} targets")
    print(f"  Codegen: {codegen.n_unique_parameters} parameters")
    print(f"  Inference: {'available' if inference_results else 'not available'}")

    # Create output directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # Generate LaTeX files
    print("\n" + "-" * 60)
    print("Generating LaTeX files...")

    files = [
        ("extraction_stats.tex", generate_extraction_stats_tex(extraction)),
        ("codegen_stats.tex", generate_codegen_stats_tex(codegen)),
        ("extraction_table.tex", generate_extraction_table_tex(extraction)),
        ("retry_table.tex", generate_retry_table_tex(extraction)),
        ("error_categories_table.tex", generate_error_categories_table_tex(extraction)),
        ("convergence_table.tex", generate_convergence_table_tex(inference, codegen, inference_results)),
        ("ppc_table.tex", generate_ppc_table_tex(inference, codegen)),
        ("posterior_table.tex", generate_posterior_table_tex(codegen, inference_results)),
        ("inference_stats.tex", generate_inference_stats_tex(inference_results)),
        ("source_quality_table.tex", generate_source_quality_table_tex(yaml_metrics)),
        ("species_table.tex", generate_species_table_tex(yaml_metrics)),
        ("indication_table.tex", generate_indication_table_tex(yaml_metrics)),
        ("model_type_table.tex", generate_model_type_table_tex(yaml_metrics)),
        ("tool_usage_table.tex", generate_tool_usage_table_tex(extraction)),
        ("complexity_table.tex", generate_complexity_table_tex(yaml_metrics)),
        ("yaml_stats.tex", generate_yaml_stats_tex(yaml_metrics)),
    ]

    for filename, content in files:
        path = OUTPUT_DIR / filename
        path.write_text(content)
        print(f"  Saved: {path}")

    # Generate figures
    print("\n" + "-" * 60)
    print("Generating figures...")
    generate_retry_distribution_figure(extraction, FIGURES_DIR / "retry_distribution.pdf")
    generate_error_category_figure(extraction, FIGURES_DIR / "error_categories.pdf")
    generate_tool_usage_figure(extraction, FIGURES_DIR / "tool_usage.pdf")
    generate_token_cost_figure(extraction, FIGURES_DIR / "token_cost_distribution.pdf")
    generate_posterior_figure(inference_results, FIGURES_DIR / "posterior_marginals.pdf")

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())