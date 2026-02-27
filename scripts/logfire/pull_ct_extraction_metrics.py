#!/usr/bin/env python3
"""
One-time script to pull CalibrationTarget extraction metrics from Logfire.

Reads trace IDs from extraction_results.json and queries Logfire for each,
saving the results to paper/generated/ct_extraction_metrics.json.

Usage:
    python scripts/pull_ct_extraction_metrics.py
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from query_logfire import LogfireClient

EXTRACTION_RESULTS = (
    Path(__file__).parent.parent
    / "metadata_storage"
    / "calibration_targets"
    / "originals"
    / "extraction_results.json"
)
OUTPUT_PATH = Path(__file__).parent.parent / "paper" / "generated" / "ct_extraction_metrics.json"


def main():
    with open(EXTRACTION_RESULTS) as f:
        entries = json.load(f)

    print(f"Found {len(entries)} trace IDs to query")

    # Load any partial results from a previous run
    existing = {}
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH) as f:
            for r in json.load(f):
                if "error" not in r:
                    existing[r["trace_id"]] = r

    client = LogfireClient()
    results = []

    for i, entry in enumerate(entries):
        trace_id = entry["trace_id"]
        name = entry["name"]
        # Reuse cached result if available
        if trace_id in existing:
            results.append(existing[trace_id])
            print(f"  {name}: cached")
            continue

        # Rate limit: pause between queries
        if i > 0:
            time.sleep(8)

        print(f"  Querying {name} ({trace_id[:12]}...)...", end=" ")

        try:
            m = client.get_trace_metrics(trace_id)
            error_cats = dict(m.categorize_errors())
            results.append({
                "name": name,
                "file": entry["file"],
                "trace_id": trace_id,
                "chat_count": m.chat_count,
                "retries": m.retries,
                "duration_sec": m.duration,
                "total_tokens": m.total_tokens,
                "input_tokens": m.input_tokens,
                "output_tokens": m.output_tokens,
                "cost": m.cost,
                "first_attempt_success": m.first_attempt_success,
                "exception_types": m.exception_types,
                "error_categories": error_cats,
                "tool_calls": m.tool_calls,
            })
            print(f"OK ({m.retries} retries, ${m.cost:.2f})")
        except Exception as e:
            print(f"FAILED: {e}")
            results.append({
                "name": name,
                "file": entry["file"],
                "trace_id": trace_id,
                "error": str(e),
            })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, indent=2)

    n_ok = sum(1 for r in results if "error" not in r)
    print(f"\nSaved {n_ok}/{len(results)} metrics to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
