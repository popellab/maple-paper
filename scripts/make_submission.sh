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

# Compile with cross-references resolved (no bibtex; the .bbl is inlined).
# main and the supplement \externaldocument each other, so xr-hyper chokes on the
# OTHER document's not-yet-settled .aux during early passes. Those failures
# self-heal once both .aux files exist, so we tolerate transient nonzero exits
# here (|| true) and assert the settled outputs afterwards rather than halting.
# Seed main.aux first, then alternate until both documents settle.
cd "$OUT"
# Route pdflatex's terminal output to a build log, NOT /dev/null: on some TeX
# builds writing the terminal stream to /dev/null intermittently aborts the run.
for pass in 1 2 3; do
  pdflatex -interaction=nonstopmode main.tex          >build.log 2>&1 || true
  pdflatex -interaction=nonstopmode supplementary.tex >build.log 2>&1 || true
done
[ -f supplementary.pdf ] && [ -f main.aux ] && [ -f supplementary.aux ] \
  || { echo "Error: build did not settle (missing supplementary.pdf or .aux)"; exit 1; }

# Freeze main's \ref's into the supplement to literal numbers and drop
# \externaldocument, so main.tex compiles standalone (the supplement ships as a
# PDF, so its .aux won't be present at the journal's compile of main.tex).
"$PY" "$SCRIPT_DIR/freeze_external_refs.py" main.tex main.aux supplementary.aux

# Recompile the now-standalone main.tex from a clean slate (two passes for its
# own refs). Drop ALL pre-freeze main artifacts first: they were written with
# \externaldocument active and carry xr/hyperref state that crashes a standalone
# read. supplementary.aux is also removed so nothing external lingers.
rm -f main.aux main.out main.toc main.lof main.lot supplementary.aux
pdflatex -interaction=nonstopmode main.tex >build.log 2>&1 || true
pdflatex -interaction=nonstopmode main.tex >build.log 2>&1 || true
[ -f main.pdf ] || { echo "Error: main.pdf not produced"; exit 1; }
# main.tex is now standalone: fail loudly if any cross-ref stayed unresolved.
if grep -q "Reference.*undefined" main.log; then
  echo "Error: undefined references remain in standalone main.tex"; exit 1
fi

# The flattened supplementary.tex is only a build artifact now; the deliverable
# is the PDF. Remove it (and the scratch build log) to avoid confusion.
rm -f supplementary.tex build.log

echo
echo "Submission files in $OUT:"
echo "  main.tex          -> upload as the TEX manuscript"
echo "  figures/workflow.pdf -> upload as the manuscript figure"
echo "  supplementary.pdf -> upload as the PDF supplement"
