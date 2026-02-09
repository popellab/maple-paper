# Claude Code Guidelines for qsp-llm-workflows-paper

## Project Overview

This repository contains the manuscript for MAPLE (Model-Aware Parameter Literature Extraction), a framework for LLM-assisted QSP model calibration. The paper targets CPT: Pharmacometrics & Systems Pharmacology.

## Key Files

- `paper/main.tex` - Main manuscript (Introduction, Methods, Results, Discussion)
- `paper/supplementary.tex` - Supplementary materials (S1-S5: examples, model types, validators, Julia code, Pydantic models)
- `paper/cpt_article_outline.md` - Detailed outline for the paper
- `examples/*.yaml` - PDAC calibration target examples
- `prompts/extract_calibration_target.md` - LLM prompt for extraction

## Writing Style

- Scientific journal format (CPT:PSP)
- Do not use `\textbf{}` for emphasis in running text
- Avoid emojis
- Do not use em-dashes (---). Use commas, parentheses, or restructure the sentence instead.
- Use proper LaTeX formatting for code (`\texttt{}`)
- Reference supplementary materials as "Supplementary Material S1" etc.

## Related Repository

The framework code is in `../qsp-llm-workflows/` (sibling directory). Schema and validator implementations are there.

## Git Commits

- Do not include "Co-Authored-By: Claude" or any AI attribution in commit messages
- Use concise, descriptive commit messages

## Current State

- Introduction: Complete
- Methods: Complete
- Results: Partially complete (placeholder values in tables)
- Discussion: To be written
- Conclusions: To be written
- Supplementary S1-S5: Complete
