#!/usr/bin/env python3
"""
Generate all results artifacts (tables, figures, statistics) for the MAPLE paper.

Usage:
    python scripts/generate_results.py

Outputs:
    paper/generated/
        extraction_metrics.tex      - Table of extraction/validation metrics
        extraction_stats.tex        - LaTeX macros for inline statistics
        retry_distribution.tex      - Table of retry distribution
        parameter_summary.tex       - Table of parameters and targets
        convergence_table.tex       - Convergence diagnostics (placeholder until inference)
        ppc_table.tex              - Posterior predictive checks (placeholder until inference)
        figures/
            retry_distribution.pdf
            posterior_marginals.pdf (if inference results available)
"""

import json
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

# Add scripts to path for query_logfire
sys.path.insert(0, str(Path(__file__).parent))

# =============================================================================
# Configuration
# =============================================================================

METADATA_DIR = Path(__file__).parent.parent / "metadata_storage" / "to-review" / "20260203_125326_submodel_target"
CURATED_DIR = Path(__file__).parent.parent / "metadata_storage" / "submodel_targets" / "curated"
OUTPUT_DIR = Path(__file__).parent.parent / "paper" / "generated"
FIGURES_DIR = OUTPUT_DIR / "figures"
SCRIPTS_DIR = Path(__file__).parent
MODEL_STRUCTURE = Path(__file__).parent.parent / "supporting_files" / "model_structure.json"

# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ExtractionMetrics:
    """Aggregate metrics from LLM extraction process."""

    n_attempted: int = 0  # Total YAML files found
    n_targets: int = 0  # Successfully extracted (with Logfire trace)
    n_failed: int = 0  # Failed extractions (no trace or max retries exceeded)
    n_first_attempt_success: int = 0
    n_required_retries: int = 0
    total_retries: int = 0
    max_retries: int = 0
    total_duration_sec: float = 0.0
    total_tokens: int = 0
    total_cost: float = 0.0
    n_single_retry: int = 0
    retry_distribution: dict = field(default_factory=dict)
    error_categories: dict = field(default_factory=dict)
    tool_usage: dict = field(default_factory=dict)  # Aggregated tool usage
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


@dataclass
class CodeGenMetrics:
    """Metrics from Julia code generation."""

    n_targets: int = 0
    n_unique_parameters: int = 0
    n_shared_parameters: int = 0
    total_lines: int = 0
    parameters: list = field(default_factory=list)
    shared_params_detail: dict = field(default_factory=dict)  # param -> list of targets


@dataclass
class InferenceMetrics:
    """Metrics from Bayesian inference (placeholder until run)."""

    available: bool = False
    n_chains: int = 0
    n_samples: int = 0
    warmup: int = 0
    runtime_min: float = 0.0
    parameters: list = field(default_factory=list)  # list of dicts with rhat, ess, etc.
    ppc_results: list = field(default_factory=list)  # list of dicts with z-score, coverage


@dataclass
class YAMLMetrics:
    """Metrics extracted directly from YAML target files."""

    # Source quality distribution
    source_quality: dict = field(default_factory=dict)  # quality type -> count
    species_translation: dict = field(default_factory=dict)  # "human->human" -> count
    indication_match: dict = field(default_factory=dict)  # exact/proxy/none -> count

    # Model type distribution
    model_types: dict = field(default_factory=dict)  # algebraic/first_order_decay/etc -> count

    # Complexity metrics per target
    complexity: list = field(default_factory=list)  # list of dicts with inputs, states, params, code_lines

    # Per-target details
    per_target: list = field(default_factory=list)


# =============================================================================
# Data Collection Functions
# =============================================================================


def collect_extraction_metrics() -> ExtractionMetrics:
    """Collect extraction metrics from Logfire traces."""
    metrics = ExtractionMetrics()

    try:
        from query_logfire import LogfireClient

        client = LogfireClient()
    except Exception as e:
        print(f"Warning: Could not initialize Logfire client: {e}")
        print("Extraction metrics will be empty.")
        return metrics

    yaml_files = sorted(METADATA_DIR.glob("*.yaml"))
    metrics.n_attempted = len(yaml_files)
    retry_counts = []
    error_cats = Counter()
    tool_usage = Counter()

    for yf in yaml_files:
        try:
            m = client.get_trace_metrics_from_yaml(yf)
            target_error_cats = dict(m.categorize_errors())
            metrics.per_target.append(
                {
                    "file": yf.name,
                    "trace_id": m.trace_id,
                    "chat_count": m.chat_count,
                    "retries": m.retries,
                    "duration": m.duration,
                    "tokens": m.total_tokens,
                    "cost": m.cost,
                    "first_attempt_success": m.first_attempt_success,
                    "exception_types": m.exception_types,
                    "error_categories": target_error_cats,
                    "tool_calls": m.tool_calls,
                }
            )
            retry_counts.append(m.retries)
            metrics.total_duration_sec += m.duration
            metrics.total_tokens += m.total_tokens
            metrics.total_cost += m.cost
            error_cats.update(target_error_cats)
            tool_usage.update(m.tool_calls)

            if m.first_attempt_success:
                metrics.n_first_attempt_success += 1

        except Exception as e:
            print(f"Warning: Could not get metrics for {yf.name}: {e}")

    metrics.n_targets = len(metrics.per_target)
    metrics.n_failed = metrics.n_attempted - metrics.n_targets
    metrics.n_required_retries = metrics.n_targets - metrics.n_first_attempt_success
    metrics.total_retries = sum(retry_counts)
    metrics.max_retries = max(retry_counts) if retry_counts else 0
    metrics.retry_distribution = dict(Counter(retry_counts))
    metrics.n_single_retry = sum(1 for r in retry_counts if r == 1)
    metrics.error_categories = dict(error_cats)
    metrics.tool_usage = dict(tool_usage)

    return metrics


def collect_codegen_metrics() -> CodeGenMetrics:
    """Collect metrics from the generated Julia code."""
    metrics = CodeGenMetrics()

    # Look in scripts directory first, then metadata_storage for backwards compatibility
    julia_file = SCRIPTS_DIR / "joint_calibration.jl"
    if not julia_file.exists():
        julia_file = METADATA_DIR / "joint_calibration.jl"
    if not julia_file.exists():
        print(f"Warning: joint_calibration.jl not found. Code generation metrics will be empty.")
        return metrics

    content = julia_file.read_text()
    metrics.total_lines = len(content.splitlines())

    # Extract parameters from prior declarations
    # Pattern: k_param ~ LogNormal(...) # Used by: target1, target2
    import re

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

    # Identify shared parameters (appear in multiple targets)
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
    from subprocess import run, PIPE

    yaml_files = list(CURATED_DIR.glob("*.yaml"))

    # Run the validation script and capture output
    result = run(
        ["python", "scripts/validate_submodel_target.py"] + [str(f) for f in yaml_files],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )

    # Parse output to count valid/invalid
    output = result.stdout + result.stderr
    valid_count = output.count("✓ Valid:")
    # Look for any validation errors
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
                trans_key = f"{species_src}→{species_tgt}"
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

            # Count lines in observation_code
            code_lines = 0
            for em in cal.get("error_model", []):
                obs_code = em.get("observation_code", "")
                if obs_code:
                    code_lines += len(obs_code.strip().split("\n"))

            # Count lines in forward model code
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


def collect_inference_metrics() -> InferenceMetrics:
    """Collect inference metrics from chain files (if available)."""
    metrics = InferenceMetrics()

    # Look for saved chain files (JLD2 format from Julia)
    chain_files = list(METADATA_DIR.glob("*.jld2")) + list(
        METADATA_DIR.glob("**/chains*.jld2")
    )

    if not chain_files:
        # Check for CSV exports
        chain_files = list(METADATA_DIR.glob("**/chain*.csv"))

    if not chain_files:
        print("Note: No inference results found. Convergence tables will be placeholders.")
        return metrics

    # TODO: Parse chain files when available
    # For now, return empty metrics
    metrics.available = True
    return metrics


# =============================================================================
# LaTeX Generation Functions
# =============================================================================


def generate_extraction_stats_tex(metrics: ExtractionMetrics) -> str:
    """Generate LaTeX macros for inline statistics."""
    lines = [
        "% Auto-generated extraction statistics",
        "% Usage: \\nTargets, \\firstAttemptRate, etc.",
        "",
        f"\\newcommand{{\\nAttempted}}{{{metrics.n_attempted}}}",
        f"\\newcommand{{\\nTargets}}{{{metrics.n_targets}}}",
        f"\\newcommand{{\\nFailed}}{{{metrics.n_failed}}}",
        f"\\newcommand{{\\nFirstAttemptSuccess}}{{{metrics.n_first_attempt_success}}}",
        f"\\newcommand{{\\nRequiredRetries}}{{{metrics.n_required_retries}}}",
        f"\\newcommand{{\\firstAttemptRate}}{{{metrics.first_attempt_rate*100:.1f}\\%}}",
        f"\\newcommand{{\\totalRetries}}{{{metrics.total_retries}}}",
        f"\\newcommand{{\\maxRetries}}{{{metrics.max_retries}}}",
        f"\\newcommand{{\\nSingleRetry}}{{{metrics.n_single_retry}}}",
        f"\\newcommand{{\\avgDurationMin}}{{{metrics.avg_duration_min:.1f}}}",
        f"\\newcommand{{\\avgTokensK}}{{{metrics.avg_tokens/1000:.0f}k}}",
        f"\\newcommand{{\\avgCost}}{{\\${metrics.avg_cost:.2f}}}",
        f"\\newcommand{{\\totalCost}}{{\\${metrics.total_cost:.2f}}}",
        f"\\newcommand{{\\totalTokensM}}{{{metrics.total_tokens/1e6:.1f}M}}",
    ]

    # Error category stats
    total_errors = sum(metrics.error_categories.values())
    lines.append(f"\\newcommand{{\\totalErrorsCaught}}{{{total_errors}}}")

    for cat, count in metrics.error_categories.items():
        pct = 100 * count / total_errors if total_errors > 0 else 0
        # Create macro names like \errFabrication, \errFabricationPct
        cat_name = cat.replace("_", "").title()
        lines.append(f"\\newcommand{{\\err{cat_name}}}{{{count}}}")
        lines.append(f"\\newcommand{{\\err{cat_name}Pct}}{{{pct:.0f}\\%}}")

    # Tool usage stats
    for tool, count in metrics.tool_usage.items():
        tool_name = tool.replace("_", " ").title().replace(" ", "")
        lines.append(f"\\newcommand{{\\tool{tool_name}}}{{{count}}}")

    return "\n".join(lines)


def generate_extraction_table_tex(metrics: ExtractionMetrics) -> str:
    """Generate LaTeX table of extraction metrics."""
    return rf"""% Auto-generated extraction metrics table
\begin{{table}}[htbp]
\centering
\caption{{LLM extraction metrics for {metrics.n_targets} calibration targets. First-attempt success indicates extractions that passed validation without requiring retry.}}
\label{{tab:extraction}}
\begin{{tabular}}{{lr}}
\toprule
Metric & Value \\
\midrule
Total targets extracted & {metrics.n_targets} \\
First-attempt success & {metrics.n_first_attempt_success}/{metrics.n_targets} ({metrics.first_attempt_rate*100:.0f}\%) \\
Required $\geq$1 retry & {metrics.n_required_retries}/{metrics.n_targets} ({(1-metrics.first_attempt_rate)*100:.0f}\%) \\
Total LLM retries & {metrics.total_retries} \\
Max retries (single target) & {metrics.max_retries} \\
\midrule
Avg. time per target & {metrics.avg_duration_min:.1f} min \\
Avg. tokens per target & {metrics.avg_tokens:,} \\
Avg. cost per target & \${metrics.avg_cost:.2f} \\
Total extraction cost & \${metrics.total_cost:.2f} \\
\bottomrule
\end{{tabular}}
\end{{table}}"""


def generate_retry_table_tex(metrics: ExtractionMetrics) -> str:
    """Generate LaTeX table of retry distribution."""
    rows = []
    for retries in sorted(metrics.retry_distribution.keys()):
        count = metrics.retry_distribution[retries]
        pct = 100 * count / metrics.n_targets
        rows.append(f"{retries} & {count} & {pct:.0f}\\%")

    rows_tex = " \\\\\n".join(rows)

    return rf"""% Auto-generated retry distribution table
\begin{{table}}[htbp]
\centering
\caption{{Distribution of retry counts across {metrics.n_targets} extraction attempts. Retries occur when validation fails and the LLM is prompted to correct errors.}}
\label{{tab:retries}}
\begin{{tabular}}{{ccc}}
\toprule
Retries & Count & Percentage \\
\midrule
{rows_tex} \\
\bottomrule
\end{{tabular}}
\end{{table}}"""


def generate_error_categories_table_tex(metrics: ExtractionMetrics) -> str:
    """Generate LaTeX table of validation error categories."""
    # Category descriptions for the table
    category_descriptions = {
        "hallucination": "Value not in source snippet",
        "fabrication": "DOI failed to resolve or metadata mismatch",
        "reference": "Internal reference inconsistency",
        "code": "Custom code syntax or execution error",
        "units": "Invalid or inconsistent units",
        "structural": "Schema or structural issues",
        "prior": "Prior specification issues",
        "source_quality": "Source reliability concerns",
        "translation": "Translation uncertainty issues",
        "encoding": "Character encoding issues",
        "other": "Other validation errors",
    }

    if not metrics.error_categories:
        return """% Auto-generated error categories table
% No validation errors were captured in the traces.
% This may indicate errors are not being logged to Logfire with exception.type,
% or all extractions succeeded on first attempt."""

    rows = []
    total_errors = sum(metrics.error_categories.values())

    for category, count in sorted(
        metrics.error_categories.items(), key=lambda x: -x[1]
    ):
        desc = category_descriptions.get(category, category)
        pct = 100 * count / total_errors if total_errors > 0 else 0
        rows.append(f"{category.replace('_', ' ').title()} & {desc} & {count} & {pct:.0f}\\%")

    rows_tex = " \\\\\n".join(rows)

    return rf"""% Auto-generated error categories table
\begin{{table}}[htbp]
\centering
\caption{{Validation errors caught during extraction, categorized by type. These errors triggered LLM retries before successful extraction.}}
\label{{tab:error-categories}}
\begin{{tabular}}{{llcc}}
\toprule
Category & Description & Count & \% \\
\midrule
{rows_tex} \\
\midrule
\textbf{{Total}} & & \textbf{{{total_errors}}} & \\
\bottomrule
\end{{tabular}}
\end{{table}}"""


def generate_parameter_table_tex(codegen: CodeGenMetrics) -> str:
    """Generate LaTeX table of parameters and sharing."""
    rows = []
    for param in sorted(codegen.parameters):
        targets = codegen.shared_params_detail.get(param, ["(single target)"])
        n_targets = len(targets) if param in codegen.shared_params_detail else 1
        shared = "Yes" if n_targets > 1 else "No"
        rows.append(f"\\texttt{{{param.replace('_', '\\_')}}} & {n_targets} & {shared}")

    rows_tex = " \\\\\n".join(rows)

    return rf"""% Auto-generated parameter summary table
\begin{{table}}[htbp]
\centering
\caption{{Parameters calibrated via joint inference. Shared parameters appear in multiple calibration targets and receive constraints from all relevant experiments.}}
\label{{tab:parameters}}
\begin{{tabular}}{{lcc}}
\toprule
Parameter & \# Targets & Shared \\
\midrule
{rows_tex} \\
\midrule
\multicolumn{{3}}{{l}}{{\textit{{Total: {codegen.n_unique_parameters} parameters, {codegen.n_shared_parameters} shared}}}} \\
\bottomrule
\end{{tabular}}
\end{{table}}"""


def generate_codegen_stats_tex(codegen: CodeGenMetrics) -> str:
    """Generate LaTeX macros for code generation statistics."""
    shared_list = ", ".join(
        [f"\\texttt{{{p.replace('_', '\\_')}}}" for p in codegen.shared_params_detail.keys()]
    )

    return f"""% Auto-generated code generation statistics
\\newcommand{{\\nUniqueParams}}{{{codegen.n_unique_parameters}}}
\\newcommand{{\\nSharedParams}}{{{codegen.n_shared_parameters}}}
\\newcommand{{\\nCodeTargets}}{{{codegen.n_targets}}}
\\newcommand{{\\nCodeLines}}{{{codegen.total_lines}}}
\\newcommand{{\\sharedParamsList}}{{{shared_list}}}"""


def generate_convergence_table_tex(
    inference: InferenceMetrics,
    codegen: CodeGenMetrics,
    inference_results: Optional[dict] = None,
) -> str:
    """Generate convergence diagnostics table."""
    if not inference_results or "parameters" not in inference_results:
        # Generate placeholder table with actual parameter names
        rows = []
        for param in sorted(codegen.parameters):
            param_tex = f"\\texttt{{{param.replace('_', '\\_')}}}"
            rows.append(f"{param_tex} & --- & --- & ---")
        rows_tex = " \\\\\n".join(rows)

        return rf"""% Auto-generated convergence table (PLACEHOLDER - run inference to populate)
\begin{{table}}[htbp]
\centering
\caption{{Convergence diagnostics for joint inference. Values will be populated after running MCMC sampling.}}
\label{{tab:convergence}}
\begin{{tabular}}{{lccc}}
\toprule
Parameter & $\hat{{R}}$ & Bulk ESS & Converged \\
\midrule
{rows_tex} \\
\bottomrule
\end{{tabular}}
\end{{table}}"""

    # Generate table with real values
    rows = []
    all_converged = True
    for param in sorted(codegen.parameters):
        param_tex = f"\\texttt{{{param.replace('_', '\\_')}}}"
        if param in inference_results["parameters"]:
            p = inference_results["parameters"][param]
            rhat = p.get("rhat", 0)
            ess = p.get("ess_bulk", 0)
            converged = rhat < 1.01 and ess > 400
            status = "\\checkmark" if converged else "\\texttimes"
            if not converged:
                all_converged = False
            rows.append(f"{param_tex} & {rhat:.3f} & {int(ess)} & {status}")
        else:
            rows.append(f"{param_tex} & --- & --- & ---")

    rows_tex = " \\\\\n".join(rows)
    n_chains = inference_results.get("n_chains", 4)
    n_samples = inference_results.get("n_samples", 1000)

    return rf"""% Auto-generated convergence table
\begin{{table}}[htbp]
\centering
\caption{{Convergence diagnostics for joint inference ({n_chains} chains, {n_samples} samples each). $\hat{{R}} < 1.01$ and ESS $> 400$ indicate convergence.}}
\label{{tab:convergence}}
\begin{{tabular}}{{lccc}}
\toprule
Parameter & $\hat{{R}}$ & Bulk ESS & Converged \\
\midrule
{rows_tex} \\
\bottomrule
\end{{tabular}}
\end{{table}}"""


def generate_ppc_table_tex(inference: InferenceMetrics, codegen: CodeGenMetrics) -> str:
    """Generate posterior predictive check table (placeholder if no inference)."""
    if not inference.available:
        return rf"""% Auto-generated PPC table (PLACEHOLDER - run inference to populate)
\begin{{table}}[htbp]
\centering
\caption{{Posterior predictive check summary. Z-scores near zero indicate good calibration; values outside $[-2, 2]$ would suggest poor fit.}}
\label{{tab:ppc}}
\begin{{tabular}}{{lcc}}
\toprule
Target & Z-score & 95\% coverage \\
\midrule
\multicolumn{{3}}{{c}}{{\textit{{Run inference to populate}}}} \\
\bottomrule
\end{{tabular}}
\end{{table}}"""

    # TODO: Generate actual table from inference results
    return "% PPC table with real values - TODO"


def generate_posterior_table_tex(
    codegen: CodeGenMetrics,
    inference_results: Optional[dict] = None,
) -> str:
    """Generate posterior summary table with medians and credible intervals."""
    if not inference_results or "parameters" not in inference_results:
        # Generate placeholder
        rows = []
        for param in sorted(codegen.parameters):
            param_tex = f"\\texttt{{{param.replace('_', '\\_')}}}"
            rows.append(f"{param_tex} & --- & --- & ---")
        rows_tex = " \\\\\n".join(rows)

        return rf"""% Auto-generated posterior table (PLACEHOLDER - run inference to populate)
\begin{{table}}[htbp]
\centering
\caption{{Posterior parameter estimates from joint Bayesian inference. Run inference to populate.}}
\label{{tab:posteriors}}
\begin{{tabular}}{{lccc}}
\toprule
Parameter & Median & 90\% CI & Units \\
\midrule
{rows_tex} \\
\bottomrule
\end{{tabular}}
\end{{table}}"""

    # Generate table with real values
    # Get units from codegen shared_params_detail or default
    rows = []
    for param in sorted(codegen.parameters):
        param_tex = f"\\texttt{{{param.replace('_', '\\_')}}}"
        if param in inference_results["parameters"]:
            p = inference_results["parameters"][param]
            med = p.get("median", 0)
            ci_lo = p.get("ci_05", 0)
            ci_hi = p.get("ci_95", 0)

            # Format numbers in scientific notation if needed
            def fmt(x):
                if abs(x) < 0.01 or abs(x) > 1000:
                    return f"{x:.2e}"
                return f"{x:.3g}"

            rows.append(f"{param_tex} & {fmt(med)} & [{fmt(ci_lo)}, {fmt(ci_hi)}] & ---")
        else:
            rows.append(f"{param_tex} & --- & --- & ---")

    rows_tex = " \\\\\n".join(rows)

    return rf"""% Auto-generated posterior table
\begin{{table}}[htbp]
\centering
\caption{{Posterior parameter estimates from joint Bayesian inference. Credible intervals are 90\% highest density intervals.}}
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
        # Create macro-safe name: replace underscores and digits with words
        # LaTeX macros can't have digits parsed correctly without braces
        digit_words = {'0': 'Zero', '1': 'One', '2': 'Two', '3': 'Three', '4': 'Four',
                       '5': 'Five', '6': 'Six', '7': 'Seven', '8': 'Eight', '9': 'Nine'}
        macro_name = ""
        for word in param.split("_"):
            # Replace digits with words
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

        # Format for LaTeX
        def fmt(x):
            if abs(x) < 0.01 or abs(x) > 1000:
                return f"{x:.2e}"
            return f"{x:.3g}"

        lines.append(f"\\newcommand{{\\{macro_name}Med}}{{{fmt(med)}}}")
        lines.append(f"\\newcommand{{\\{macro_name}CILo}}{{{fmt(ci_lo)}}}")
        lines.append(f"\\newcommand{{\\{macro_name}CIHi}}{{{fmt(ci_hi)}}}")
        lines.append(f"\\newcommand{{\\{macro_name}Rhat}}{{{rhat:.3f}}}")

    return "\n".join(lines)


# =============================================================================
# Figure Generation Functions
# =============================================================================


def generate_retry_distribution_figure(metrics: ExtractionMetrics, output_path: Path):
    """Generate retry distribution bar chart."""
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("Warning: matplotlib not available. Skipping figure generation.")
        return

    retries = sorted(metrics.retry_distribution.keys())
    counts = [metrics.retry_distribution[r] for r in retries]

    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(retries, counts, color="steelblue", edgecolor="black", alpha=0.8)

    # Add count labels on bars
    for bar, count in zip(bars, counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.3,
            str(count),
            ha="center",
            va="bottom",
            fontsize=11,
        )

    ax.set_xlabel("Number of Retries", fontsize=12)
    ax.set_ylabel("Number of Targets", fontsize=12)
    ax.set_xticks(retries)
    ax.set_ylim(0, max(counts) + 2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Add annotation for first-attempt success
    first_success_pct = metrics.first_attempt_rate * 100
    ax.annotate(
        f"{first_success_pct:.0f}% first-attempt success",
        xy=(0, metrics.retry_distribution.get(0, 0)),
        xytext=(1.5, max(counts) - 1),
        fontsize=10,
        arrowprops=dict(arrowstyle="->", color="gray"),
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {output_path}")


def generate_error_category_figure(metrics: ExtractionMetrics, output_path: Path):
    """Generate error category bar chart."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Warning: matplotlib not available. Skipping figure generation.")
        return

    if not metrics.error_categories:
        print("  Skipping error category figure (no errors recorded)")
        return

    # Sort by count descending
    categories = sorted(metrics.error_categories.items(), key=lambda x: -x[1])
    names = [c[0].replace("_", " ").title() for c in categories]
    counts = [c[1] for c in categories]

    # Color mapping for different error types
    colors = {
        "fabrication": "#e74c3c",  # red
        "hallucination": "#e67e22",  # orange
        "units": "#3498db",  # blue
        "code": "#9b59b6",  # purple
        "prior": "#1abc9c",  # teal
        "reference": "#f39c12",  # yellow
        "structural": "#95a5a6",  # gray
        "other": "#7f8c8d",  # dark gray
    }
    bar_colors = [colors.get(c[0], "#95a5a6") for c in categories]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.barh(names[::-1], counts[::-1], color=bar_colors[::-1], edgecolor="black", alpha=0.8)

    # Add count labels
    for bar, count in zip(bars, counts[::-1]):
        ax.text(
            bar.get_width() + 0.2,
            bar.get_y() + bar.get_height() / 2,
            str(count),
            ha="left",
            va="center",
            fontsize=10,
        )

    ax.set_xlabel("Number of Errors Caught", fontsize=12)
    ax.set_title("Validation Errors by Category", fontsize=14)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_xlim(0, max(counts) + 1.5)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {output_path}")


def generate_tool_usage_figure(metrics: ExtractionMetrics, output_path: Path):
    """Generate tool usage bar chart."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Warning: matplotlib not available. Skipping figure generation.")
        return

    if not metrics.tool_usage:
        print("  Skipping tool usage figure (no tool usage recorded)")
        return

    tools = sorted(metrics.tool_usage.items(), key=lambda x: -x[1])
    names = [t[0].replace("_", " ").title() for t in tools]
    counts = [t[1] for t in tools]

    colors = ["#3498db", "#2ecc71", "#e74c3c", "#9b59b6", "#f39c12"]

    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(names, counts, color=colors[: len(names)], edgecolor="black", alpha=0.8)

    # Add count labels
    for bar, count in zip(bars, counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 2,
            str(count),
            ha="center",
            va="bottom",
            fontsize=11,
        )

    ax.set_ylabel("Number of Calls", fontsize=12)
    ax.set_title("Tool Usage During Extraction", fontsize=14)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_ylim(0, max(counts) * 1.15)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {output_path}")


def generate_token_cost_figure(metrics: ExtractionMetrics, output_path: Path):
    """Generate token and cost distribution histograms."""
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("Warning: matplotlib not available. Skipping figure generation.")
        return

    if not metrics.per_target:
        print("  Skipping token/cost figure (no per-target data)")
        return

    tokens = [t["tokens"] / 1000 for t in metrics.per_target]  # Convert to thousands
    costs = [t["cost"] for t in metrics.per_target]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    # Token distribution
    ax1.hist(tokens, bins=10, color="steelblue", edgecolor="black", alpha=0.8)
    ax1.axvline(np.median(tokens), color="red", linestyle="--", linewidth=2, label=f"Median: {np.median(tokens):.0f}k")
    ax1.set_xlabel("Tokens (thousands)", fontsize=12)
    ax1.set_ylabel("Number of Targets", fontsize=12)
    ax1.set_title("Token Usage Distribution", fontsize=14)
    ax1.legend()
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    # Cost distribution
    ax2.hist(costs, bins=10, color="forestgreen", edgecolor="black", alpha=0.8)
    ax2.axvline(np.median(costs), color="red", linestyle="--", linewidth=2, label=f"Median: ${np.median(costs):.2f}")
    ax2.set_xlabel("Cost (USD)", fontsize=12)
    ax2.set_ylabel("Number of Targets", fontsize=12)
    ax2.set_title("Cost Distribution", fontsize=14)
    ax2.legend()
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {output_path}")


# =============================================================================
# Additional Table Generation Functions
# =============================================================================


def generate_source_quality_table_tex(yaml_metrics: YAMLMetrics) -> str:
    """Generate LaTeX table of source quality distribution."""
    if not yaml_metrics.source_quality:
        return "% No source quality data available"

    # Format quality labels nicely
    quality_labels = {
        "primary_human_in_vitro": "Primary human in vitro",
        "primary_human_in_vivo": "Primary human in vivo",
        "primary_animal_in_vivo": "Primary animal in vivo",
        "primary_animal_in_vitro": "Primary animal in vitro",
        "review_article": "Review article",
        "meta_analysis": "Meta-analysis",
        "clinical_trial": "Clinical trial",
        "unknown": "Unknown",
    }

    rows = []
    total = sum(yaml_metrics.source_quality.values())
    for quality, count in sorted(yaml_metrics.source_quality.items(), key=lambda x: -x[1]):
        label = quality_labels.get(quality, quality.replace("_", " ").title())
        pct = 100 * count / total if total > 0 else 0
        rows.append(f"{label} & {count} & {pct:.0f}\\%")

    rows_tex = " \\\\\n".join(rows)

    return rf"""% Auto-generated source quality table
\begin{{table}}[htbp]
\centering
\caption{{Distribution of primary data source quality across calibration targets.}}
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
        "proxy": "Related indication (e.g., other cancers, fibrosis)",
        "general": "General physiological data",
        "unknown": "Not specified",
    }

    rows = []
    total = sum(yaml_metrics.indication_match.values())
    for match, count in sorted(yaml_metrics.indication_match.items(), key=lambda x: -x[1]):
        pct = 100 * count / total if total > 0 else 0
        description = desc.get(match, match)
        rows.append(f"{match.title()} & {description} & {count} & {pct:.0f}\\%")

    rows_tex = " \\\\\n".join(rows)

    return rf"""% Auto-generated indication match table
\begin{{table}}[htbp]
\centering
\caption{{Indication match between data source and PDAC model target.}}
\label{{tab:indication}}
\begin{{tabular}}{{llcc}}
\toprule
Match & Description & Count & \% \\
\midrule
{rows_tex} \\
\midrule
\textbf{{Total}} & & \textbf{{{total}}} & \\
\bottomrule
\end{{tabular}}
\end{{table}}"""


def generate_model_type_table_tex(yaml_metrics: YAMLMetrics) -> str:
    """Generate LaTeX table of forward model types."""
    if not yaml_metrics.model_types:
        return "% No model type data available"

    type_labels = {
        "algebraic": "Algebraic (closed-form)",
        "first_order_decay": "First-order decay ODE",
        "exponential_growth": "Exponential growth ODE",
        "two_state": "Two-state ODE",
        "saturation": "Saturation ODE",
        "logistic": "Logistic growth ODE",
        "custom_ode": "Custom ODE",
        "batch_accumulation": "Batch accumulation",
        "steady_state_density": "Steady-state density",
        "steady_state_fraction": "Steady-state fraction",
        "steady_state_concentration": "Steady-state concentration",
        "steady_state_ratio": "Steady-state ratio",
        "steady_state_proliferation_index": "Steady-state proliferation index",
        "unknown": "Unknown",
    }

    rows = []
    total = sum(yaml_metrics.model_types.values())
    for mtype, count in sorted(yaml_metrics.model_types.items(), key=lambda x: -x[1]):
        label = type_labels.get(mtype, mtype.replace("_", " ").title())
        pct = 100 * count / total if total > 0 else 0
        rows.append(f"{label} & {count} & {pct:.0f}\\%")

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
    """Generate LaTeX table of tool usage per target."""
    if not metrics.per_target:
        return "% No tool usage data available"

    rows = []
    for t in sorted(metrics.per_target, key=lambda x: x["file"]):
        fname = t["file"].replace("_", "\\_").replace(".yaml", "")
        # Truncate long names
        if len(fname) > 30:
            fname = fname[:27] + "..."
        web = t.get("tool_calls", {}).get("web_search", 0)
        code = t.get("tool_calls", {}).get("code_execution", 0)
        retries = t.get("retries", 0)
        rows.append(f"{fname} & {web} & {code} & {retries}")

    rows_tex = " \\\\\n".join(rows)

    total_web = sum(t.get("tool_calls", {}).get("web_search", 0) for t in metrics.per_target)
    total_code = sum(t.get("tool_calls", {}).get("code_execution", 0) for t in metrics.per_target)

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
    """Generate LaTeX table of extraction complexity."""
    if not yaml_metrics.complexity:
        return "% No complexity data available"

    rows = []
    for c in sorted(yaml_metrics.complexity, key=lambda x: x["file"]):
        fname = c["file"].replace("_", "\\_").replace(".yaml", "")
        if len(fname) > 30:
            fname = fname[:27] + "..."
        rows.append(f"{fname} & {c['n_inputs']} & {c['n_params']} & {c['n_states']} & {c['code_lines']}")

    rows_tex = " \\\\\n".join(rows)

    # Summary stats
    import statistics
    avg_inputs = statistics.mean(c["n_inputs"] for c in yaml_metrics.complexity)
    avg_params = statistics.mean(c["n_params"] for c in yaml_metrics.complexity)
    avg_states = statistics.mean(c["n_states"] for c in yaml_metrics.complexity)
    avg_code = statistics.mean(c["code_lines"] for c in yaml_metrics.complexity)

    return rf"""% Auto-generated complexity table
\begin{{table}}[htbp]
\centering
\caption{{Complexity metrics for calibration targets. Inputs are experimental values; parameters are model rate constants; states are ODE variables.}}
\label{{tab:complexity}}
\begin{{tabular}}{{lcccc}}
\toprule
Target & Inputs & Params & States & Code Lines \\
\midrule
{rows_tex} \\
\midrule
\textbf{{Average}} & \textbf{{{avg_inputs:.1f}}} & \textbf{{{avg_params:.1f}}} & \textbf{{{avg_states:.1f}}} & \textbf{{{avg_code:.1f}}} \\
\bottomrule
\end{{tabular}}
\end{{table}}"""


def generate_yaml_stats_tex(yaml_metrics: YAMLMetrics) -> str:
    """Generate LaTeX macros for YAML-derived statistics."""
    import statistics

    lines = ["% Auto-generated YAML-derived statistics"]

    # Calculate summary stats
    n_targets = len(yaml_metrics.complexity)
    avg_inputs = statistics.mean(c["n_inputs"] for c in yaml_metrics.complexity) if yaml_metrics.complexity else 0
    avg_code_lines = statistics.mean(c["code_lines"] for c in yaml_metrics.complexity) if yaml_metrics.complexity else 0

    lines.append(f"\\newcommand{{\\nYAMLTargets}}{{{n_targets}}}")
    lines.append(f"\\newcommand{{\\avgInputs}}{{{avg_inputs:.1f}}}")
    lines.append(f"\\newcommand{{\\avgCodeLines}}{{{avg_code_lines:.0f}}}")

    # Source quality percentages
    total_sq = sum(yaml_metrics.source_quality.values())
    for sq, count in yaml_metrics.source_quality.items():
        pct = 100 * count / total_sq if total_sq > 0 else 0
        # Create macro name like \sqPrimaryHumanClinical, \sqPrimaryHumanClinicalPct
        sq_name = sq.replace("_", " ").title().replace(" ", "")
        lines.append(f"\\newcommand{{\\sq{sq_name}}}{{{count}}}")
        lines.append(f"\\newcommand{{\\sq{sq_name}Pct}}{{{pct:.0f}\\%}}")

    # Species translation percentages
    total_sp = sum(yaml_metrics.species_translation.values())
    for sp, count in yaml_metrics.species_translation.items():
        pct = 100 * count / total_sp if total_sp > 0 else 0
        # Create macro name, handling the arrow
        sp_name = sp.replace("→", "To").replace("_", "").title()
        lines.append(f"\\newcommand{{\\sp{sp_name}}}{{{count}}}")
        lines.append(f"\\newcommand{{\\sp{sp_name}Pct}}{{{pct:.0f}\\%}}")

    # Indication match percentages
    total_ind = sum(yaml_metrics.indication_match.values())
    for ind, count in yaml_metrics.indication_match.items():
        pct = 100 * count / total_ind if total_ind > 0 else 0
        ind_name = ind.replace("_", "").title()
        lines.append(f"\\newcommand{{\\ind{ind_name}}}{{{count}}}")
        lines.append(f"\\newcommand{{\\ind{ind_name}Pct}}{{{pct:.0f}\\%}}")

    # Model type percentages
    total_mt = sum(yaml_metrics.model_types.values())
    for mt, count in yaml_metrics.model_types.items():
        pct = 100 * count / total_mt if total_mt > 0 else 0
        mt_name = mt.replace("_", " ").title().replace(" ", "")
        lines.append(f"\\newcommand{{\\mt{mt_name}}}{{{count}}}")
        lines.append(f"\\newcommand{{\\mt{mt_name}Pct}}{{{pct:.0f}\\%}}")

    return "\n".join(lines)


# =============================================================================
# Julia Code Generation Functions
# =============================================================================


def generate_julia_inference_scripts() -> dict:
    """
    Generate Julia inference scripts from YAML targets.

    Returns dict with generation status and any errors.
    """
    result = {
        "joint_generated": False,
        "single_generated": False,
        "joint_path": None,
        "single_path": None,
        "errors": [],
    }

    yaml_files = sorted(CURATED_DIR.glob("*.yaml"))
    if not yaml_files:
        result["errors"].append("No YAML files found in curated targets directory")
        return result

    if not MODEL_STRUCTURE.exists():
        result["errors"].append(f"Model structure not found: {MODEL_STRUCTURE}")
        return result

    # Generate joint inference script
    joint_output = SCRIPTS_DIR / "joint_calibration.jl"
    try:
        cmd = [
            "python", "-m", "qsp_llm_workflows.core.calibration.julia_translator",
            "--joint",
            "--model-structure", str(MODEL_STRUCTURE),
            "--fixed-sigma",
            "--output", str(joint_output),
        ] + [str(f) for f in yaml_files]

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        if proc.returncode == 0:
            result["joint_generated"] = True
            result["joint_path"] = str(joint_output)
        else:
            result["errors"].append(f"Joint generation failed: {proc.stderr}")

    except Exception as e:
        result["errors"].append(f"Joint generation error: {e}")

    # Generate combined single-target inference script
    single_output = SCRIPTS_DIR / "single_targets_combined.jl"
    try:
        cmd = [
            "python", "-m", "qsp_llm_workflows.core.calibration.julia_translator",
            "--single-all",
            "--model-structure", str(MODEL_STRUCTURE),
            "--output", str(single_output),
        ] + [str(f) for f in yaml_files]

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        if proc.returncode == 0:
            result["single_generated"] = True
            result["single_path"] = str(single_output)
        else:
            result["errors"].append(f"Single-target generation failed: {proc.stderr}")

    except Exception as e:
        result["errors"].append(f"Single-target generation error: {e}")

    return result


def run_julia_inference(script_path: Path, timeout_minutes: int = 30) -> dict:
    """
    Run a Julia inference script and return results.

    Args:
        script_path: Path to Julia script
        timeout_minutes: Maximum time to wait for inference

    Returns:
        Dict with inference results or error info
    """
    result = {
        "success": False,
        "results_path": None,
        "figure_path": None,
        "runtime_sec": None,
        "error": None,
    }

    if not script_path.exists():
        result["error"] = f"Script not found: {script_path}"
        return result

    import time
    start_time = time.time()

    # Run Julia in the scripts directory so output files are created there
    try:
        proc = subprocess.run(
            ["julia", "--threads=auto", str(script_path.name)],
            capture_output=True,
            text=True,
            cwd=script_path.parent,
            timeout=timeout_minutes * 60,
        )

        result["runtime_sec"] = time.time() - start_time

        if proc.returncode == 0:
            result["success"] = True

            # Check for output files
            results_json = script_path.parent / "inference_results.json"
            if results_json.exists():
                result["results_path"] = str(results_json)

            figure_png = script_path.parent / "posterior_marginals.png"
            if figure_png.exists():
                result["figure_path"] = str(figure_png)
        else:
            result["error"] = f"Julia error (exit {proc.returncode}): {proc.stderr[-1000:]}"

    except subprocess.TimeoutExpired:
        result["error"] = f"Inference timed out after {timeout_minutes} minutes"
    except FileNotFoundError:
        result["error"] = "Julia not found. Install Julia and add to PATH."
    except Exception as e:
        result["error"] = str(e)

    return result


def load_inference_results(results_path: Optional[str]) -> Optional[dict]:
    """Load inference results from JSON file."""
    if not results_path:
        return None

    path = Path(results_path)
    if not path.exists():
        return None

    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load inference results: {e}")
        return None


# =============================================================================
# Main
# =============================================================================


def main():
    print("=" * 60)
    print("Generating MAPLE paper results artifacts")
    print("=" * 60)

    # Configuration
    inference_timeout = 60  # minutes

    # Create output directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # Collect all metrics
    print("\n[1/7] Collecting extraction metrics from Logfire...")
    extraction = collect_extraction_metrics()
    if extraction.n_targets == 0:
        # Logfire expired or unavailable; load cached extraction metrics
        cached_json = OUTPUT_DIR / "metrics.json"
        if cached_json.exists():
            cached = json.load(open(cached_json))
            cached_ext = cached.get("extraction", {})
            if cached_ext.get("n_targets", 0) > 0:
                print("  Logfire unavailable; loading cached extraction metrics from metrics.json")
                extraction = ExtractionMetrics(
                    n_attempted=cached_ext.get("n_attempted", cached_ext.get("n_targets", 0)),
                    n_targets=cached_ext["n_targets"],
                    n_failed=cached_ext.get("n_failed", 0),
                    n_first_attempt_success=cached_ext.get("n_first_attempt_success", 0),
                    n_required_retries=cached_ext["n_targets"] - cached_ext.get("n_first_attempt_success", 0),
                    total_retries=cached_ext.get("total_retries", 0),
                    max_retries=cached_ext.get("max_retries", 0),
                    total_duration_sec=cached_ext.get("avg_duration_min", 0) * 60 * cached_ext["n_targets"],
                    total_tokens=cached_ext.get("avg_tokens", 0) * cached_ext["n_targets"],
                    total_cost=cached_ext.get("total_cost", 0),
                    retry_distribution={int(k): v for k, v in cached_ext.get("retry_distribution", {}).items()},
                    error_categories=cached_ext.get("error_categories", {}),
                    tool_usage=cached_ext.get("tool_usage", {}),
                    per_target=cached_ext.get("per_target", []),
                )
    print(f"  Found {extraction.n_targets} targets")
    print(f"  First-attempt success: {extraction.n_first_attempt_success}/{extraction.n_targets}")

    print("\n[2/7] Collecting YAML-based metrics...")
    yaml_metrics = collect_yaml_metrics()
    print(f"  Source qualities: {len(yaml_metrics.source_quality)} types")
    print(f"  Model types: {len(yaml_metrics.model_types)} types")
    print(f"  Targets with complexity data: {len(yaml_metrics.complexity)}")

    print("\n[3/7] Collecting validation metrics...")
    validation = collect_validation_metrics()
    print(f"  Validation: {validation['n_valid']}/{validation['n_files']} passed")

    print("\n[4/7] Generating Julia inference scripts...")
    julia_result = generate_julia_inference_scripts()
    if julia_result["joint_generated"]:
        print(f"  Joint inference script: {julia_result['joint_path']}")
    if julia_result["single_generated"]:
        print(f"  Single-target script: {julia_result['single_path']}")
    if julia_result["errors"]:
        for err in julia_result["errors"]:
            print(f"  Warning: {err}")

    # Run inference
    inference_results = None
    inference_run_result = None
    if julia_result["joint_generated"]:
        print(f"\n[5/7] Running Julia inference (timeout: {inference_timeout} min)...")
        print("  This may take 10-30 minutes...")
        inference_run_result = run_julia_inference(
            Path(julia_result["joint_path"]),
            timeout_minutes=inference_timeout,
        )
        if inference_run_result["success"]:
            print(f"  Inference completed in {inference_run_result['runtime_sec']:.1f} seconds")
            if inference_run_result["results_path"]:
                print(f"  Results: {inference_run_result['results_path']}")
                inference_results = load_inference_results(inference_run_result["results_path"])
            if inference_run_result["figure_path"]:
                print(f"  Figure: {inference_run_result['figure_path']}")
                # Copy figure to paper/generated/figures/
                import shutil
                dest = FIGURES_DIR / "posterior_marginals.png"
                shutil.copy(inference_run_result["figure_path"], dest)
                print(f"  Copied to: {dest}")
        else:
            print(f"  Inference failed: {inference_run_result['error']}")
    else:
        print("\n[5/7] Skipping inference (Julia script generation failed)")

    print("\n[6/7] Collecting code generation metrics...")
    codegen = collect_codegen_metrics()
    print(f"  Parameters: {codegen.n_unique_parameters} ({codegen.n_shared_parameters} shared)")
    print(f"  Lines of Julia: {codegen.total_lines}")

    print("\n[7/7] Checking inference results...")
    inference = collect_inference_metrics()
    if inference_results:
        inference.available = True
        n_params = len(inference_results.get("parameters", {}))
        print(f"  Inference results loaded: {n_params} parameters")
    else:
        print("  No inference results (tables will be placeholders)")

    # Save metrics as JSON
    print("\n" + "-" * 60)
    print("Saving metrics.json...")

    metrics_json = {
        "extraction": {
            "n_attempted": extraction.n_attempted,
            "n_targets": extraction.n_targets,
            "n_failed": extraction.n_failed,
            "n_first_attempt_success": extraction.n_first_attempt_success,
            "first_attempt_rate": extraction.first_attempt_rate,
            "total_retries": extraction.total_retries,
            "max_retries": extraction.max_retries,
            "avg_duration_min": extraction.avg_duration_min,
            "avg_tokens": extraction.avg_tokens,
            "avg_cost": extraction.avg_cost,
            "total_cost": extraction.total_cost,
            "retry_distribution": extraction.retry_distribution,
            "error_categories": extraction.error_categories,
            "tool_usage": extraction.tool_usage,
            "per_target": extraction.per_target,
        },
        "codegen": {
            "n_unique_parameters": codegen.n_unique_parameters,
            "n_shared_parameters": codegen.n_shared_parameters,
            "n_targets": codegen.n_targets,
            "total_lines": codegen.total_lines,
            "parameters": codegen.parameters,
            "shared_params_detail": codegen.shared_params_detail,
        },
        "julia_generation": julia_result,
        "inference_run": inference_run_result,
        "inference_results": inference_results,
        "validation": validation,
        "inference_available": inference.available,
        "yaml_metrics": {
            "source_quality": yaml_metrics.source_quality,
            "species_translation": yaml_metrics.species_translation,
            "indication_match": yaml_metrics.indication_match,
            "model_types": yaml_metrics.model_types,
            "complexity": yaml_metrics.complexity,
        },
    }

    json_path = OUTPUT_DIR / "metrics.json"
    json_path.write_text(json.dumps(metrics_json, indent=2))
    print(f"  Saved: {json_path}")

    print("\n" + "=" * 60)
    print("Done! Now run:")
    print("  python scripts/generate_latex.py")
    print("to generate LaTeX tables and figures.")
    print("=" * 60)


if __name__ == "__main__":
    main()
