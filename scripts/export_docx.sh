#!/bin/bash
# Export main.tex and supplementary.tex to Word docx via pandoc
# Usage: ./scripts/export_docx.sh

set -e

cd "$(dirname "$0")/../paper"

# Preprocess main.tex: replace supplementary cross-refs with section numbers
# since pandoc can't resolve \externaldocument refs
sed \
  -e 's/\\ref{sec:complete-example}/S1/g' \
  -e 's/\\ref{tab:model-types}/S2/g' \
  -e 's/\\ref{sec:model-types}/S2/g' \
  -e 's/\\ref{sec:validators}/S3/g' \
  -e 's/\\ref{sec:julia-code}/S4/g' \
  -e 's/\\ref{sec:pydantic-models}/S5/g' \
  -e 's/\\ref{sec:submodel-field-reference}/S6/g' \
  -e 's/\\ref{sec:calibration-target-example}/S7/g' \
  -e 's/\\ref{sec:source-characteristics}/S8/g' \
  -e 's/\\ref{sec:ct-detailed-metrics}/S9/g' \
  -e 's/\\ref{sec:inference-results}/S10/g' \
  -e 's/\\ref{sec:prompt-construction}/S11/g' \
  -e 's/\\ref{sec:schema-implementation-detail}/S12/g' \
  -e 's/\\ref{sec:source-relevance-detail}/S13/g' \
  -e 's/\\ref{sec:collaboration-modes}/S14/g' \
  -e 's/\\ref{sec:detailed-comparison}/S15/g' \
  -e '/\\externaldocument/d' \
  main.tex > main_preprocessed.tex

pandoc main_preprocessed.tex \
  --from latex \
  --to docx \
  --bibliography references.bib \
  --citeproc \
  --number-sections \
  --output main.docx

rm main_preprocessed.tex
echo "Created paper/main.docx"

# Also export supplementary
pandoc supplementary.tex \
  --from latex \
  --to docx \
  --bibliography references.bib \
  --citeproc \
  --number-sections \
  --output supplementary.docx

echo "Created paper/supplementary.docx"