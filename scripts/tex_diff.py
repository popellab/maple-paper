#!/usr/bin/env python3
"""
tex_diff.py — Git-aware LaTeX diff using latexdiff.

Usage:
    python scripts/tex_diff.py [COMMIT] [--outdir DIR] [--files FILE...]

    COMMIT   Git ref to compare against (default: HEAD~1)
    --outdir  Output directory (default: paper/diff_output)
    --files   Specific .tex files to diff (default: paper/main.tex paper/supplementary.tex)
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def git_show(commit: str, filepath: str) -> str | None:
    """Get file contents at a given git commit."""
    try:
        result = subprocess.run(
            ["git", "show", f"{commit}:{filepath}"],
            capture_output=True, text=True, check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return None


def run_latexdiff(old_path: Path, new_path: Path) -> str:
    """Run latexdiff and return the diff text."""
    result = subprocess.run(
        ["latexdiff", str(old_path), str(new_path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  latexdiff warnings/errors:\n{result.stderr}", file=sys.stderr)
    return result.stdout


def normalize_minted(text: str) -> str:
    """Convert minted environments to verbatim so old/new match when diffing."""
    text = re.sub(r"\\begin\{minted\}(?:\[[^\]]*\])?\{[^}]*\}", r"\\begin{verbatim}", text)
    text = text.replace(r"\end{minted}", r"\end{verbatim}")
    text = re.sub(r"\\begin\{listing\}(\[[^\]]*\])?", r"\\begin{figure}[H]", text)
    text = text.replace(r"\end{listing}", r"\end{figure}")
    text = re.sub(r"\\usepackage(?:\[[^\]]*\])?\{minted\}\n?", "", text)
    text = re.sub(r"\\setminted(?:\[[^\]]*\])?\{[^}]*\}\n?", "", text)
    text = re.sub(r"\\renewcommand\{\\listoflistingscaption\}.*\n?", "", text)
    return text


def inject_graphicspath(text: str, source_dir: Path, output_dir: Path) -> str:
    """Inject \\graphicspath so figures resolve to the original source directory."""
    rel = os.path.relpath(source_dir, output_dir)
    directive = rf"\graphicspath{{{{{rel}/}}}}"
    return text.replace(r"\begin{document}", directive + "\n" + r"\begin{document}", 1)


def main():
    parser = argparse.ArgumentParser(
        description="Git-aware LaTeX diff using latexdiff"
    )
    parser.add_argument(
        "commit", nargs="?", default="HEAD~1",
        help="Git commit to compare against (default: HEAD~1)",
    )
    parser.add_argument(
        "--outdir", default="paper/diff_output",
        help="Output directory (default: paper/diff_output)",
    )
    parser.add_argument(
        "--files", nargs="+",
        default=["paper/main.tex"],
        help="Files to diff",
    )
    parser.add_argument(
        "--copy", nargs="*", default=["paper/supplementary.tex"],
        help="Extra .tex files to copy (not diff) into outdir for cross-refs",
    )
    parser.add_argument(
        "--flatten", action="store_true",
        help=r"Use latexdiff --flatten to expand \input commands",
    )
    parser.add_argument(
        "--compile", action="store_true",
        help="Compile the diff PDFs after generating",
    )
    parser.add_argument(
        "--timeout", type=int, default=120,
        help="Timeout in seconds per pdflatex pass (default: 120)",
    )
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        for filepath in args.files:
            print(f"Processing {filepath}...")

            new_text = Path(filepath).read_text()
            old_text = git_show(args.commit, filepath)

            if old_text is None:
                print(f"  {filepath} is new (not in {args.commit}), copying as-is")
                dest = outdir / filepath
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(new_text)
                continue

            # Normalize old text so minted->verbatim changes don't produce diffs
            old_text = normalize_minted(old_text)

            # Write old/new to temp files for latexdiff
            old_tmp = tmpdir / f"old_{Path(filepath).name}"
            old_tmp.write_text(old_text)

            new_tmp = tmpdir / f"new_{Path(filepath).name}"
            new_tmp.write_text(new_text)

            diff_text = run_latexdiff(old_tmp, new_tmp)

            if not diff_text:
                print(f"  latexdiff produced no output for {filepath}, skipping")
                continue

            # Fix figure paths to point back to original source directory
            source_dir = Path(filepath).parent.resolve()
            dest = outdir / filepath
            dest.parent.mkdir(parents=True, exist_ok=True)
            diff_text = inject_graphicspath(diff_text, source_dir, dest.parent.resolve())

            dest.write_text(diff_text)
            print(f"  -> {dest}")

        # If not flattening, also need to copy/diff \input'd files
        if not args.flatten:
            input_files = set()
            for filepath in args.files:
                try:
                    text = Path(filepath).read_text()
                    for m in re.finditer(r"\\input\{(.+?)\}", text):
                        input_path = m.group(1)
                        if not input_path.endswith(".tex"):
                            input_path += ".tex"
                        base = Path(filepath).parent
                        resolved = base / input_path
                        if resolved.exists():
                            input_files.add(str(resolved))
                except FileNotFoundError:
                    pass

            for filepath in sorted(input_files):
                old_text = git_show(args.commit, filepath)
                new_text = Path(filepath).read_text()

                dest = outdir / filepath
                dest.parent.mkdir(parents=True, exist_ok=True)

                if old_text is None or old_text == new_text:
                    dest.write_text(new_text)
                    if old_text is None:
                        print(f"  Copied (new): {filepath}")
                else:
                    old_tmp = tmpdir / f"old_{Path(filepath).name}"
                    old_tmp.write_text(normalize_minted(old_text))
                    new_tmp = tmpdir / f"new_{Path(filepath).name}"
                    new_tmp.write_text(new_text)

                    diff_text = run_latexdiff(old_tmp, new_tmp)
                    if diff_text:
                        dest.write_text(diff_text)
                        print(f"  Diffed: {filepath}")
                    else:
                        dest.write_text(new_text)
                        print(f"  latexdiff failed, copied as-is: {filepath}")

    # Copy extra .tex files (for cross-references) and their \input'd files
    for filepath in (args.copy or []):
        src = Path(filepath)
        if not src.exists():
            print(f"  Warning: --copy file {filepath} not found, skipping")
            continue
        dest = outdir / filepath
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        print(f"  Copied (for cross-refs): {filepath}")
        # Also copy any \input'd files from copied documents
        text = src.read_text()
        for m in re.finditer(r"\\input\{(.+?)\}", text):
            input_path = m.group(1)
            if not input_path.endswith(".tex"):
                input_path += ".tex"
            resolved = src.parent / input_path
            if resolved.exists():
                input_dest = outdir / str(resolved)
                input_dest.parent.mkdir(parents=True, exist_ok=True)
                if not input_dest.exists():
                    shutil.copy2(resolved, input_dest)
                    print(f"  Copied (input of {src.name}): {resolved}")

    # Copy .bib and .bst files needed for compilation
    all_tex_dirs = {Path(f).parent for f in args.files}
    all_tex_dirs.update(Path(f).parent for f in (args.copy or []))
    for src_dir in all_tex_dirs:
        dest_dir = outdir / src_dir
        dest_dir.mkdir(parents=True, exist_ok=True)
        for ext in ("*.bib", "*.bst"):
            for f in src_dir.glob(ext):
                shutil.copy2(f, dest_dir / f.name)
                print(f"  Copied: {f}")

    # Compile if requested
    if args.compile:
        # First compile copied files so their .aux is available for cross-refs
        for filepath in (args.copy or []):
            dest = outdir / filepath
            if dest.exists():
                print(f"\nCompiling {dest} (for cross-refs)...")
                tex_dir = dest.parent
                tex_name = dest.name
                try:
                    subprocess.run(
                        ["pdflatex", "-interaction=nonstopmode", tex_name],
                        cwd=tex_dir, capture_output=True,
                        timeout=args.timeout,
                    )
                except subprocess.TimeoutExpired:
                    print(f"  pdflatex timed out after {args.timeout}s")

        # Then compile the diffed files
        for filepath in args.files:
            dest = outdir / filepath
            if dest.exists():
                print(f"\nCompiling {dest}...")
                tex_dir = dest.parent
                tex_name = dest.name
                stem = tex_name.removesuffix(".tex")

                def run_pdflatex():
                    try:
                        subprocess.run(
                            ["pdflatex", "-interaction=nonstopmode", tex_name],
                            cwd=tex_dir, capture_output=True,
                            timeout=args.timeout,
                        )
                    except subprocess.TimeoutExpired:
                        print(f"  pdflatex timed out after {args.timeout}s")
                        return False
                    return True

                # pdflatex -> bibtex -> pdflatex * 3 (extra pass for xr cross-refs)
                if not run_pdflatex():
                    continue
                subprocess.run(
                    ["bibtex", stem],
                    cwd=tex_dir, capture_output=True, timeout=30,
                )
                for _ in range(3):
                    if not run_pdflatex():
                        break

                pdf_path = tex_dir / f"{stem}.pdf"
                if pdf_path.exists():
                    print(f"  -> {pdf_path} ({pdf_path.stat().st_size // 1024}KB)")
                else:
                    print(f"  FAILED: {pdf_path} not created")

    print("\nDone.")


if __name__ == "__main__":
    main()
