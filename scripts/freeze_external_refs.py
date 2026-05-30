#!/usr/bin/env python3
r"""
Freeze cross-document \ref's into literal text for standalone submission.

The flattened main.tex keeps \ref's into the supplement (e.g.
\ref{tab:model-types}), which normally resolve via \externaldocument reading
supplementary.aux. When the supplement is submitted as a compiled PDF rather
than a .tex, the journal compiles main.tex on its own and those refs become
"??". This script replaces each *external* \ref{X} (a label defined in the
supplement but not in main) with the literal value the ref currently renders,
taken from supplementary.aux, and comments out \externaldocument so main.tex
compiles standalone. Local \ref's (labels defined in main itself) are left as
live references.

Usage:
    python scripts/freeze_external_refs.py <main.tex> <main.aux> <supplementary.aux>
"""

import re
import sys
from pathlib import Path

NEWLABEL = re.compile(r'\\newlabel\{([^}]+)\}\{\{([^}]*)\}')


def labels(aux_path: Path) -> dict:
    r"""Map label name -> printed \ref value from a .aux file."""
    out = {}
    if not aux_path.exists():
        sys.exit(f"Error: {aux_path} not found")
    for name, value in NEWLABEL.findall(aux_path.read_text(encoding='utf-8')):
        # Skip hyperref's sub-anchors (e.g. "sub@foo"); keep the primary label.
        if name.startswith('sub@'):
            continue
        out.setdefault(name, value)
    return out


def freeze(main_tex: str, main_aux: str, supp_aux: str) -> None:
    tex_path = Path(main_tex)
    content = tex_path.read_text(encoding='utf-8')

    local = labels(Path(main_aux))
    supp = labels(Path(supp_aux))

    frozen = []

    def repl(match):
        name = match.group(1)
        if name in supp and name not in local:
            frozen.append((name, supp[name]))
            return supp[name]
        return match.group(0)

    content = re.sub(r'\\ref\{([^}]+)\}', repl, content)

    # Neutralize the external-document hookup; nothing external remains.
    content = re.sub(
        r'^\\externaldocument\{[^}]*\}.*$',
        r'% \g<0>  % frozen for standalone submission',
        content, flags=re.MULTILINE)

    tex_path.write_text(content, encoding='utf-8')
    print(f"✓ Froze {len(frozen)} external \\ref(s) in {main_tex}:")
    for name, value in frozen:
        print(f"    {name} -> {value}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit("Usage: python scripts/freeze_external_refs.py "
                 "<main.tex> <main.aux> <supplementary.aux>")
    freeze(sys.argv[1], sys.argv[2], sys.argv[3])
