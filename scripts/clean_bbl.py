"""Strip BibTeX formatting artifacts from .bbl files for pandoc compatibility.

Removes {{double braces}} (title-case protection) and {\relax } wrappers
that pandoc's LaTeX reader doesn't handle correctly.
"""

import re
import sys


def clean_bbl(text: str) -> str:
    # Remove {\relax XX} -> XX (used for initials in vancouver.bst)
    text = re.sub(r"\{\\relax\s+([^}]+)\}", r"\1", text)

    # Expand \doi{X} -> doi:X (pandoc doesn't understand \doi command)
    text = re.sub(r"\\doi\{([^}]+)\}", r"doi:\1", text)

    # Remove {{double braces}} -> content (title-case protection)
    # Repeat until no more double braces (handles nesting)
    while "{{" in text:
        text = text.replace("{{", "").replace("}}", "")

    return text


if __name__ == "__main__":
    in_path, out_path = sys.argv[1], sys.argv[2]
    with open(in_path) as f:
        text = f.read()
    with open(out_path, "w") as f:
        f.write(clean_bbl(text))
