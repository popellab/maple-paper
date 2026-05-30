#!/usr/bin/env bash
#
# Build self-contained .tex files for CPT:PSP submission.
#
# CPT:PSP accepts the manuscript as TEX but wants the supplement as a PDF, so
# the deliverables differ:
#   - main.tex          : single self-contained TEX (all \input{snippets,generated}
#                         and the .bbl inlined; external \ref's into the supplement
#                         frozen to literal numbers so it compiles standalone).
#   - supplementary.pdf : compiled PDF (its figures are embedded).
#   - figures/workflow.pdf : the only figure main.tex references, uploaded with it.
# Track changes are left ON (blue); set \trackchanges to 0 in main.tex for a
# clean copy.
#
# Usage: ./scripts/make_submission.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
PAPER="$REPO_ROOT/paper"
OUT="$PAPER/submission"
PY="$REPO_ROOT/.venv/bin/python"

rm -rf "$OUT"
mkdir -p "$OUT/figures" "$OUT/generated/figures"

# Flatten main and supplement (named to keep \externaldocument resolvable).
"$PY" "$SCRIPT_DIR/flatten_tex.py" "$PAPER/main.tex"          "$OUT/main.tex"
"$PY" "$SCRIPT_DIR/flatten_tex.py" "$PAPER/supplementary.tex" "$OUT/supplementary.tex"

# Copy the figures referenced via \includegraphics (not inlined).
cp "$PAPER/figures/workflow.pdf"                       "$OUT/figures/"
cp "$PAPER/generated/figures/posterior_marginals.pdf"  "$OUT/generated/figures/"

# Compile both with cross-references resolved (supplement <-> main cycled; no
# bibtex because the .bbl is inlined). This produces the final supplementary.pdf
# and the .aux files needed to freeze main's external refs.
cd "$OUT"
for pass in 1 2; do
  pdflatex -interaction=nonstopmode -halt-on-error supplementary.tex >/dev/null
  pdflatex -interaction=nonstopmode -halt-on-error main.tex          >/dev/null
done

# Freeze main's \ref's into the supplement to literal numbers and drop
# \externaldocument, so main.tex compiles standalone (the supplement ships as a
# PDF, so its .aux won't be present at the journal's compile of main.tex).
"$PY" "$SCRIPT_DIR/freeze_external_refs.py" main.tex main.aux supplementary.aux

# Recompile the now-standalone main.tex (two passes for its own refs).
pdflatex -interaction=nonstopmode -halt-on-error main.tex >/dev/null
pdflatex -interaction=nonstopmode -halt-on-error main.tex >/dev/null

# The flattened supplementary.tex is only a build artifact now; the deliverable
# is the PDF. Remove it to avoid confusion about what to upload.
rm -f supplementary.tex

echo
echo "Submission files in $OUT:"
echo "  main.tex          -> upload as the TEX manuscript"
echo "  figures/workflow.pdf -> upload as the manuscript figure"
echo "  supplementary.pdf -> upload as the PDF supplement"
