#!/usr/bin/env python3
"""
Validate that value_snippets in YAML files exist in their source papers.

This script fetches paper text (abstract and full text) from Europe PMC/Unpaywall
and uses fuzzy matching to verify that snippets actually appear in the cited sources.

Catches hallucinations where the LLM fabricates plausible-looking snippets
that don't actually appear in the cited paper.

Usage:
    python scripts/validate_snippets_in_source.py path/to/target.yaml
    python scripts/validate_snippets_in_source.py metadata_storage/  # validate all
"""

import sys
from pathlib import Path
from typing import Optional

import yaml

from maple.core.calibration.submodel_target import SubmodelTarget
from maple.core.calibration.validators import (
    fuzzy_find_snippet_in_text,
    get_paper_texts_from_doi,
)


def validate_snippets_in_file(yaml_path: Path) -> tuple[bool, list[str], list[str], list[str]]:
    """
    Validate snippets in a single YAML file.

    Returns:
        (success, errors, skipped, passed) tuple
    """
    errors = []
    skipped = []
    passed = []

    try:
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        # Parse as SubmodelTarget to get structured data
        target = SubmodelTarget.model_validate(data)

    except Exception as e:
        return (False, [f"Failed to parse: {e}"], [], [])

    # Build source_ref -> DOI mapping
    source_dois: dict[str, str] = {}
    source_dois[target.primary_data_source.source_tag] = target.primary_data_source.doi
    if target.secondary_data_sources:
        for src in target.secondary_data_sources:
            if src.doi:
                source_dois[src.source_tag] = src.doi

    # Collect inputs that need verification (all inputs with snippets)
    inputs_to_verify = []
    for inp in target.inputs:
        if not inp.value_snippet:
            skipped.append(f"{inp.name} (no snippet)")
            continue
        if inp.source_ref in source_dois:
            inputs_to_verify.append(inp)
        else:
            skipped.append(f"{inp.name} (source_ref not in DOI mapping)")

    if not inputs_to_verify:
        return (True, [], skipped, [])

    # Fetch paper texts for unique DOIs (both abstract and full_text)
    unique_dois = set(source_dois[inp.source_ref] for inp in inputs_to_verify)
    paper_texts: dict[str, dict[str, Optional[str]]] = {}

    for doi in unique_dois:
        paper_texts[doi] = get_paper_texts_from_doi(doi)

    # Verify each snippet against BOTH abstract and full_text
    for inp in inputs_to_verify:
        doi = source_dois[inp.source_ref]
        texts = paper_texts.get(doi, {})

        # Try matching against both abstract and full_text
        best_score = 0.0
        found = False
        best_source = None

        for source_type in ["abstract", "full_text"]:
            text = texts.get(source_type)
            if not text:
                continue

            match_found, score, matched = fuzzy_find_snippet_in_text(
                inp.value_snippet, text, threshold=0.8
            )

            if match_found:
                found = True
                best_source = source_type
                best_score = score
                break
            elif score > best_score:
                best_score = score

        if found:
            passed.append(f"{inp.name} (matched in {best_source}, score={best_score:.2f})")
        elif texts.get("abstract") or texts.get("full_text"):
            # At least one text source was available but snippet not found
            snippet_display = (
                inp.value_snippet[:60] + "..."
                if len(inp.value_snippet) > 60
                else inp.value_snippet
            )
            errors.append(
                f"{inp.name} (score: {best_score:.2f})\n"
                f"      Snippet: '{snippet_display}'"
            )
        else:
            skipped.append(f"{inp.name} (no paper text available)")

    success = len(errors) == 0
    return (success, errors, skipped, passed)


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_snippets_in_source.py <yaml_file_or_dir>")
        sys.exit(1)

    path = Path(sys.argv[1])

    if path.is_file():
        yaml_files = [path]
    elif path.is_dir():
        yaml_files = sorted(path.glob("**/*.yaml"))
    else:
        print(f"Error: {path} is not a valid file or directory")
        sys.exit(1)

    total_files = len(yaml_files)
    passed_files = 0
    failed_files = 0
    all_errors = []
    all_skipped = []

    print(f"\nValidating snippets in {total_files} file(s)...\n")

    for yaml_file in yaml_files:
        success, errors, skipped, passed = validate_snippets_in_file(yaml_file)

        if success:
            passed_files += 1
            status = "✓"
            print(f"{status} {yaml_file.name}: {len(passed)} snippets validated")
        else:
            failed_files += 1
            status = "✗"
            print(f"{status} {yaml_file.name}: {len(errors)} error(s)")
            for err in errors:
                print(f"    FAIL: {err}")
                all_errors.append(f"{yaml_file.name} / {err}")

        for skip in skipped:
            all_skipped.append(f"{yaml_file.name} / {skip}")

    print(f"\n{'='*60}")
    print(f"Summary: {passed_files}/{total_files} files passed")

    if all_skipped:
        print(f"\nSkipped ({len(all_skipped)} inputs):")
        for skip in all_skipped:
            print(f"  - {skip}")

    if all_errors:
        print(f"\nFailures ({len(all_errors)}):")
        for err in all_errors:
            print(f"  FAIL: {err}")
        sys.exit(1)
    else:
        print("\nAll snippets validated successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()