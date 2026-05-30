#!/usr/bin/env python3
r"""
Flatten a LaTeX file into a single self-contained .tex for journal submission.

Adapted from shade_paper_code/manuscript/flatten_tex.py. Beyond inlining
\input{snippets/...}, this version also inlines \input{generated/...} (the
auto-generated stat macros and tables) and replaces \bibliography{...} with the
contents of the compiled .bbl, so the output compiles with pdflatex alone (no
bibtex, no .bib, no generated/ directory). \externaldocument is left intact so
cross-references resolve when main and supplement are compiled as a pair.

Usage:
    python scripts/flatten_tex.py paper/main.tex paper/main_submission.tex
"""

import re
import sys
from pathlib import Path

INPUT_PATTERN = r'\\input\{(snippets|generated)/([^}]+)\}'


def inline_inputs(content: str, base_dir: Path) -> str:
    r"""Replace \input{snippets/...} and \input{generated/...} with file contents."""

    def repl(match):
        subdir, name = match.group(1), match.group(2)
        if not name.endswith('.tex'):
            name += '.tex'
        path = base_dir / subdir / name
        if not path.exists():
            print(f"  Warning: input not found: {path}")
            return match.group(0)
        text = path.read_text(encoding='utf-8')
        if not text.endswith('\n'):
            text += '\n'
        return f"% BEGIN {subdir}/{name}\n{text}% END {subdir}/{name}\n"

    # One pass is enough (snippets/generated do not nest \input of these kinds),
    # but loop until stable in case they ever do.
    for _ in range(5):
        new = re.sub(INPUT_PATTERN, repl, content)
        if new == content:
            break
        content = new
    return content


def inline_bbl(content: str, base_dir: Path, stem: str) -> str:
    r"""Replace \bibliography{...} with the contents of <stem>.bbl."""
    bbl = base_dir / f"{stem}.bbl"
    if not bbl.exists():
        print(f"  Warning: {bbl} not found; leaving \\bibliography intact")
        return content
    bbl_text = bbl.read_text(encoding='utf-8')
    replacement = f"% BEGIN {stem}.bbl\n{bbl_text}\n% END {stem}.bbl"
    # Use a function replacement so backslashes in the .bbl are inserted
    # literally (a string replacement would treat \d, \s, etc. as escapes).
    return re.sub(r'\\bibliography\{[^}]*\}', lambda _: replacement, content)


def flatten(input_file: str, output_file: str) -> None:
    in_path = Path(input_file)
    out_path = Path(output_file)
    if not in_path.exists():
        sys.exit(f"Error: {input_file} not found")

    content = in_path.read_text(encoding='utf-8')
    n_inputs = len(re.findall(INPUT_PATTERN, content))
    content = inline_inputs(content, in_path.parent)
    content = inline_bbl(content, in_path.parent, in_path.stem)

    out_path.write_text(content, encoding='utf-8')
    print(f"✓ Flattened {input_file} → {output_file} "
          f"({n_inputs} \\input inlined, .bbl inlined)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: python scripts/flatten_tex.py <input.tex> <output.tex>")
    flatten(sys.argv[1], sys.argv[2])
