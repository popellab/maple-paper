#!/usr/bin/env python3
"""
Compare joint vs single-target posterior samples.

Reads JSON output from both inference scripts and produces:
1. Forest plot (log-scale): medians + 90% CIs for joint, single-targets, and priors
2. Summary table with conflict detection and prior sensitivity metrics

Prior sensitivity metrics:
- Contraction: 1 - posterior_width / prior_width (on log10 scale)
  ~1 = data very informative, ~0 = prior-dominated
- Shift: |log10(med_post) - log10(med_prior)| / prior_sd_log10
  ~0 = data confirms prior, >1 = data overrides prior

Usage:
    python scripts/compare_posteriors.py [OPTIONS]

Options:
    --joint-results      Path to joint inference_results.json
                         (default: inference_results.json)
    --single-results     Path to single_inference_results.json
                         (default: single_inference_results.json)
    --julia-script       Path to joint calibration Julia script for prior extraction
                         (default: scripts/joint_calibration.jl)
    --output-dir         Directory for output plots (default: scripts/)
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def build_param_to_targets(single_results: dict) -> dict[str, list[str]]:
    """Map parameter name -> list of target_ids that constrain it."""
    param_targets = defaultdict(list)
    for target_id, params in single_results.items():
        for param_name in params:
            param_targets[param_name].append(target_id)
    return dict(param_targets)


def shorten_target_id(target_id: str) -> str:
    """Shorten target_id for plot labels."""
    parts = target_id.split("_")
    for i, p in enumerate(parts):
        if p[0].isupper() and not p.startswith("PDAC"):
            return "_".join(parts[i:])
    return target_id[-30:]


def parse_priors_from_julia(julia_path: Path) -> dict[str, dict]:
    """Parse prior distributions from Julia calibration script.

    Returns dict mapping parameter name to prior info with keys:
    type, arg1, arg2, median, ci_05, ci_95.
    """
    text = julia_path.read_text()

    # Only match lines in the PRIORS section (param ~ Distribution pattern)
    pattern = r"(\w+)\s*~\s*(Normal|LogNormal|Uniform)\(([\d.\-e+]+),\s*([\d.\-e+]+)\)"
    priors = {}

    for match in re.finditer(pattern, text):
        name = match.group(1)
        dist_type = match.group(2)
        arg1 = float(match.group(3))
        arg2 = float(match.group(4))

        if dist_type == "LogNormal":
            median = np.exp(arg1)
            ci_05 = np.exp(arg1 - 1.645 * arg2)
            ci_95 = np.exp(arg1 + 1.645 * arg2)
        elif dist_type == "Normal":
            median = arg1
            ci_05 = arg1 - 1.645 * arg2
            ci_95 = arg1 + 1.645 * arg2
        elif dist_type == "Uniform":
            median = (arg1 + arg2) / 2
            ci_05 = arg1 + 0.05 * (arg2 - arg1)
            ci_95 = arg1 + 0.95 * (arg2 - arg1)
        else:
            continue

        priors[name] = {
            "type": dist_type,
            "arg1": arg1,
            "arg2": arg2,
            "median": median,
            "ci_05": ci_05,
            "ci_95": ci_95,
        }

    return priors


def compute_prior_sensitivity(
    joint_results: dict,
    priors: dict[str, dict],
) -> dict[str, dict]:
    """Compute prior-to-posterior contraction and shift for each parameter.

    contraction = 1 - posterior_CI_width / prior_CI_width  (log10 scale)
    shift = |log10(med_post) - log10(med_prior)| / prior_sd_log10
    """
    sensitivity = {}

    for param_name, prior in priors.items():
        if param_name not in joint_results.get("parameters", {}):
            continue

        jr = joint_results["parameters"][param_name]
        post_med = jr["median"]
        post_lo = jr["ci_05"]
        post_hi = jr["ci_95"]

        prior_med = prior["median"]
        prior_lo = prior["ci_05"]
        prior_hi = prior["ci_95"]

        # Use log scale if all values are positive
        if all(v > 0 for v in [post_med, post_lo, post_hi, prior_med, prior_lo, prior_hi]):
            post_width = np.log10(post_hi) - np.log10(post_lo)
            prior_width = np.log10(prior_hi) - np.log10(prior_lo)
            prior_sd_log10 = prior_width / 3.29

            contraction = 1.0 - post_width / prior_width if prior_width > 0 else 0.0
            shift = (
                abs(np.log10(post_med) - np.log10(prior_med)) / prior_sd_log10
                if prior_sd_log10 > 0
                else 0.0
            )
        else:
            # Fallback to linear scale (Normal priors that might go negative)
            post_width = post_hi - post_lo
            prior_width = prior_hi - prior_lo
            prior_sd = prior_width / 3.29

            contraction = 1.0 - post_width / prior_width if prior_width > 0 else 0.0
            shift = abs(post_med - prior_med) / prior_sd if prior_sd > 0 else 0.0

        sensitivity[param_name] = {
            "contraction": contraction,
            "shift": shift,
        }

    return sensitivity


def compute_pairwise_log_discrepancies(
    single_results: dict,
    param_name: str,
    target_ids: list[str],
) -> list[tuple[str, str, float]]:
    """Compute standardized log-scale discrepancy between all pairs.

    d = |log10(med_a) - log10(med_b)| / sqrt(sd_a^2 + sd_b^2)
    where SD is estimated from the 90% CI on log scale:
    sd_log10 = (log10(ci_95) - log10(ci_05)) / 3.29
    """
    entries = []
    for tid in target_ids:
        if tid not in single_results or param_name not in single_results[tid]:
            continue
        sr = single_results[tid][param_name]
        med, lo, hi = sr["median"], sr["ci_05"], sr["ci_95"]
        if med > 0 and lo > 0 and hi > 0:
            log_med = np.log10(med)
            log_sd = (np.log10(hi) - np.log10(lo)) / 3.29  # 2 * 1.645
            entries.append((tid, log_med, max(log_sd, 1e-10)))

    pairs = []
    for a in range(len(entries)):
        for b in range(a + 1, len(entries)):
            tid_a, lm_a, ls_a = entries[a]
            tid_b, lm_b, ls_b = entries[b]
            d = abs(lm_a - lm_b) / np.sqrt(ls_a**2 + ls_b**2)
            pairs.append((tid_a, tid_b, d))
    return pairs


def plot_forest(
    joint_results: dict,
    single_results: dict,
    param_targets: dict[str, list[str]],
    output_dir: Path,
    priors: dict[str, dict] | None = None,
    sensitivity: dict[str, dict] | None = None,
):
    """Forest plot (log-scale): medians + 90% CIs for each parameter."""
    params = sorted(param_targets.keys())
    colors = plt.cm.tab10.colors

    # Account for prior row in height calculation
    extra_per_param = 1 if priors else 0
    fig, axes = plt.subplots(
        len(params), 1,
        figsize=(10, 1.2 * sum(1 + extra_per_param + len(param_targets[p]) for p in params)),
        squeeze=False,
    )

    for p_idx, param_name in enumerate(params):
        ax = axes[p_idx, 0]
        y_labels = []
        y_positions = []
        y = 0

        # Prior (shown first / top)
        if priors and param_name in priors:
            p = priors[param_name]
            med = p["median"]
            lo = p["ci_05"]
            hi = p["ci_95"]
            ax.errorbar(
                med, y, xerr=[[med - lo], [hi - med]],
                fmt="s", color="lightgray", capsize=4, markersize=8,
                markeredgecolor="gray", ecolor="gray",
            )
            y_labels.append("Prior")
            y_positions.append(y)
            y += 1

        # Joint
        if param_name in joint_results.get("parameters", {}):
            jr = joint_results["parameters"][param_name]
            med = jr["median"]
            lo = jr["ci_05"]
            hi = jr["ci_95"]
            ax.errorbar(med, y, xerr=[[med - lo], [hi - med]], fmt="ko", capsize=4, markersize=8)
            y_labels.append("Joint")
            y_positions.append(y)
            y += 1

        # Single targets
        target_ids = param_targets[param_name]
        for i, tid in enumerate(target_ids):
            if tid not in single_results or param_name not in single_results[tid]:
                continue
            sr = single_results[tid][param_name]
            med = sr["median"]
            lo = sr["ci_05"]
            hi = sr["ci_95"]
            color = colors[i % len(colors)]
            ax.errorbar(
                med, y, xerr=[[med - lo], [hi - med]],
                fmt="o", color=color, capsize=4, markersize=6,
            )
            y_labels.append(shorten_target_id(tid))
            y_positions.append(y)
            y += 1

        ax.set_xscale("log")
        ax.set_yticks(y_positions)
        ax.set_yticklabels(y_labels, fontsize=8)
        ax.set_xlabel(param_name)
        ax.invert_yaxis()
        ax.grid(axis="x", alpha=0.3)

        # Build title with conflict and sensitivity info
        pairs = compute_pairwise_log_discrepancies(single_results, param_name, target_ids)
        max_d = max((d for _, _, d in pairs), default=0.0)

        title_parts = [param_name]
        if max_d > 2.0:
            title_parts.append(f"[CONFLICT d={max_d:.1f}]")
        elif max_d > 1.0:
            title_parts.append(f"[TENSION d={max_d:.1f}]")

        if sensitivity and param_name in sensitivity:
            s = sensitivity[param_name]
            title_parts.append(f"c={s['contraction']:.2f} s={s['shift']:.1f}")

        title = "  ".join(title_parts)
        if max_d > 2.0:
            ax.set_title(title, fontsize=10, color="red")
        elif max_d > 1.0:
            ax.set_title(title, fontsize=10, color="orange")
        else:
            ax.set_title(title, fontsize=10)

    fig.suptitle("Forest Plot: Joint vs Single-Target 90% CIs (log scale)", fontsize=14, y=1.01)
    fig.tight_layout()
    out = output_dir / "posterior_comparison_forest.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Saved: {out}")
    plt.close(fig)


def print_summary_table(
    joint_results: dict,
    single_results: dict,
    param_targets: dict[str, list[str]],
    priors: dict[str, dict] | None = None,
    sensitivity: dict[str, dict] | None = None,
):
    """Print text summary table with conflict detection and sensitivity."""
    params = sorted(param_targets.keys())

    print("\n" + "=" * 90)
    print("COMPARISON SUMMARY: Joint vs Single-Target Posteriors")
    print("=" * 90)

    for param_name in params:
        print(f"\n  {param_name}:")

        # Prior
        if priors and param_name in priors:
            p = priors[param_name]
            print(f"    Prior:  {p['median']:.4g}  [{p['ci_05']:.4g} - {p['ci_95']:.4g}]  ({p['type']})")

        # Joint + sensitivity
        if param_name in joint_results.get("parameters", {}):
            jr = joint_results["parameters"][param_name]
            line = f"    Joint:  {jr['median']:.4g}  [{jr['ci_05']:.4g} - {jr['ci_95']:.4g}]"
            if sensitivity and param_name in sensitivity:
                s = sensitivity[param_name]
                line += f"  contraction={s['contraction']:.2f}, shift={s['shift']:.1f}"
            print(line)

        # Singles
        for tid in param_targets[param_name]:
            if tid in single_results and param_name in single_results[tid]:
                sr = single_results[tid][param_name]
                label = shorten_target_id(tid)
                print(f"    {label}:  {sr['median']:.4g}  [{sr['ci_05']:.4g} - {sr['ci_95']:.4g}]")

        # Conflict check via standardized log-scale discrepancy
        pairs = compute_pairwise_log_discrepancies(
            single_results, param_name, param_targets[param_name]
        )
        for tid_a, tid_b, d in pairs:
            la = shorten_target_id(tid_a)
            lb = shorten_target_id(tid_b)
            if d > 2.0:
                print(f"    >> CONFLICT (d={d:.1f}): {la} vs {lb}")
            elif d > 1.0:
                print(f"    >> TENSION (d={d:.1f}): {la} vs {lb}")

    print("\n" + "=" * 90)


def main():
    parser = argparse.ArgumentParser(description="Compare joint vs single-target posteriors.")
    parser.add_argument(
        "--joint-results",
        default="inference_results.json",
        help="Path to joint inference_results.json",
    )
    parser.add_argument(
        "--single-results",
        default="single_inference_results.json",
        help="Path to single_inference_results.json",
    )
    parser.add_argument(
        "--julia-script",
        default="scripts/joint_calibration.jl",
        help="Path to joint calibration Julia script (for prior extraction)",
    )
    parser.add_argument(
        "--output-dir",
        default="scripts",
        help="Directory for output plots",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    joint_results_path = Path(args.joint_results)
    single_results_path = Path(args.single_results)
    julia_script_path = Path(args.julia_script)

    missing = []
    for p in [joint_results_path, single_results_path]:
        if not p.exists():
            missing.append(str(p))
    if missing:
        print("Missing files:", file=sys.stderr)
        for m in missing:
            print(f"  {m}", file=sys.stderr)
        print("\nRun both inference scripts first:", file=sys.stderr)
        print("  julia scripts/joint_calibration.jl", file=sys.stderr)
        print("  julia scripts/single_targets_combined.jl", file=sys.stderr)
        sys.exit(1)

    joint_results = load_json(joint_results_path)
    single_results = load_json(single_results_path)

    # Parse priors from Julia script (optional)
    priors = None
    sensitivity = None
    if julia_script_path.exists():
        priors = parse_priors_from_julia(julia_script_path)
        if priors:
            sensitivity = compute_prior_sensitivity(joint_results, priors)
            print(f"Parsed {len(priors)} priors from {julia_script_path}")
    else:
        print(f"Julia script not found at {julia_script_path}, skipping prior analysis",
              file=sys.stderr)

    # Build parameter -> target mapping from single-target results
    param_targets = build_param_to_targets(single_results)

    # Generate forest plot
    plot_forest(joint_results, single_results, param_targets, output_dir, priors, sensitivity)

    # Print summary
    print_summary_table(joint_results, single_results, param_targets, priors, sensitivity)


if __name__ == "__main__":
    main()