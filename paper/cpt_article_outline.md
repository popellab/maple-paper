# CPT: Pharmacometrics & Systems Pharmacology - Article Outline

**Working Title:** LLM-Assisted Extraction of QSP Calibration Targets: A Validated Schema for Structured Data and Joint Bayesian Inference

**Target Journal:** CPT: Pharmacometrics & Systems Pharmacology

---

## 2. Methods

### 2.1 Problem Framing: The Full Model Calibration Challenge

**The goal**: Calibrate parameters in a full QSP model (e.g., 100+ ODEs, 100+ parameters) using Bayesian inference.

**The challenge**: Where does the data come from?
- Clinical endpoints (tumor response, survival) constrain only a few aggregate parameters
- Many mechanistic parameters are not identifiable from clinical data alone
- Running MCMC on the full model is computationally expensive

**The opportunity**: Isolated system experiments
- In vitro, ex vivo, and preclinical studies are abundant in the literature
- These experiments isolate specific biological processes (proliferation, death, secretion, etc.)
- They provide direct measurements of quantities that relate to model parameters

**The gap**: Gathering this data is difficult at scale
- Each experiment measures something slightly different, with different units, conditions, and uncertainties
- No standardized procedure for extracting data with full provenance
- No systematic way to connect extracted data to model parameters
- Manual curation is error-prone, poorly documented, and not reproducible

**The question this paper addresses**: How do we create a well-documented, reproducible procedure for extracting data from isolated experiments and using it to constrain parameters in the full model?

**Why now? The LLM opportunity**
- Large language models can read papers and extract structured data at speed and scale
- But LLMs have well-known failure modes: hallucination, inconsistent outputs, fabricated citations
- Naive LLM extraction is not trustworthy for scientific applications
- We need a framework that harnesses LLM capabilities while guarding against their pitfalls

**Our approach**:
1. Extract experimental data with full provenance (the `inputs` layer)
2. Define a submodel that connects the data to full model parameters (the `calibration` layer)
3. Validate the extraction automatically before inference
4. Generate inference code that combines multiple targets via **joint Bayesian inference**

**Why joint Bayesian inference?**
- **Global optimization**: Find parameters that satisfy ALL targets simultaneously, not one at a time
- **Shared parameters**: When multiple experiments inform the same parameter, all data contributes to its posterior
- **Uncertainty propagation**: Full posterior distributions, not point estimates—uncertainty flows through to predictions
- **Correlation structure**: Captures how parameters covary, which matters for model predictions
- **Principled combination**: No ad-hoc averaging or weighting—Bayes' theorem handles it

### 2.2 Schema Design: SimplifiedIsolatedTarget

**Design philosophy for LLM-assisted extraction**:
- Structured schema constrains LLM output to a predictable format (plays to LLM strength: following templates)
- Required fields force completeness—LLM cannot skip provenance information
- Enumerated options (input_type, role, model type) reduce free-form errors
- Separation of `inputs` from `calibration` matches how humans reason about the task
- Every field is machine-verifiable, enabling automated validation of LLM output

#### 2.2.1 The Submodel Philosophy: From Isolated Experiments to Full Model Parameters

**The core problem**: We want to calibrate parameters in a full QSP model (100+ ODEs, 100+ parameters), but:
- Full model inference is computationally expensive
- Many parameters are not identifiable from clinical endpoints alone
- Clinical data is scarce; preclinical/in vitro data is abundant

**The solution**: Use *submodels* that capture the relevant dynamics from isolated experiments.

**What is a submodel?**
- A simplified ODE system (often 1-3 equations) that describes the isolated experiment
- Example: PSC proliferation assay → single exponential growth ODE: dy/dt = k · y
- The submodel is *derived from* the full model by:
  - Isolating the relevant species/reactions
  - Assuming other species are constant or absent
  - Documenting these simplifying assumptions

**The critical link: shared parameter names**
- Submodel parameters use the *same names* as in the full QSP model
- Example: `k_apsc_prolif` in the submodel IS the same `k_apsc_prolif` in the full model
- This enables the posterior from submodel inference to directly inform the full model
- No post-hoc mapping or unit conversion required

**Why this works**
- Isolated experiments control confounding factors (no immune cells, no drug, etc.)
- The submodel captures exactly what the experiment measures
- Inference on the submodel yields posteriors for parameters that are identifiable from that data
- Multiple submodels → multiple constraints on overlapping parameters → joint inference

**The end goal**: Combine posteriors from many isolated system targets with clinical calibration targets for full model inference. The submodel approach makes each piece of data maximally informative for the parameters it can actually constrain.

#### 2.2.2 Core Design Principle: Data First, Then Model Mapping

The schema reflects a data-driven workflow:

1. **Start with the data**: What did the experimentalists actually measure?
2. **Then ask**: How can this data constrain parameters in our model?

This inverts the typical approach ("we need parameter X, go find a value") to instead ask: "here is experimental data with uncertainty—how does it inform our model parameters?" The result is *model-relative parameter identification*: the same experimental data could inform different parameters depending on the model structure.

**`inputs` layer (extraction)**
- Captures data exactly as reported in papers
- No modeling decisions yet—just faithful extraction
- Full provenance: DOI, source_location, value_snippet
- Input classification:
  - `input_type`: direct_measurement | proxy_measurement | inferred_estimate | assumed_value
  - `role`: target | auxiliary | initial_condition | fixed_parameter
- Reusable: same inputs could inform different models or parameters

**`calibration` layer (inference)**
- Maps extracted data to model parameters
- Specifies the submodel connecting observations to parameters
- Defines how to compare model predictions to observed data
- References inputs by name (values not duplicated)
- Model-relative: same data + different model → different calibration specification

#### 2.2.3 Prior Specification

- Supported distributions: LogNormal, Normal, Uniform, HalfNormal
- Each prior has:
  - Distribution parameters (mu, sigma, lower, upper)
  - `rationale`: Documents reasoning for prior choice
- Connection between literature values and prior parameterization

#### 2.2.4 Model Types

**Built-in ODE models** (template-based generation):
- `exponential_growth`: dy/dt = k·y
- `first_order_decay`: dy/dt = -k·y
- `two_state`: A → B transition
- `logistic`: dy/dt = k·y·(1 - y/K)
- `saturation`: dy/dt = k·(1 - y)
- `michaelis_menten`: dy/dt = -Vmax·y/(Km + y)

**Non-ODE models**:
- `direct_conversion`: Analytical formula (e.g., k = ln(2)/t_half)
- `direct_fit`: Hill function, linear regression
- `custom`: User-provided ODE code

#### 2.2.5 Measurement Model

- Observable specification (identity or transformation of state)
- Likelihood distribution (LogNormal, Normal)
- Evaluation points (time or dose)
- Sample size for uncertainty scaling

### 2.3 Validation Framework: Guarding Against LLM Failure Modes

The validation framework is specifically designed to catch common LLM errors before they propagate to inference. Each validator targets a known failure mode:

#### 2.3.1 Reference Validation (catches: inconsistent outputs)
LLMs sometimes generate references to inputs or sources that don't exist elsewhere in the document.
- `validate_input_refs`: All `uses_inputs` references exist in inputs list
- `validate_source_refs`: All `source_ref` fields match defined sources
- `validate_parameter_roles`: Model parameters exist in parameter list
- `validate_observable_state_vars`: Observable references valid state variables

#### 2.3.2 Content Validation (catches: hallucination, fabrication)
LLMs may fabricate values, invent citations, or misremember numbers from source text.
- `validate_doi_resolution`: DOIs resolve via CrossRef API → catches fabricated citations
- `validate_input_values_in_snippets`: Numeric values must appear in source text → catches hallucinated values
- `validate_units_are_valid_pint`: All units parseable by Pint → catches malformed units
- `validate_custom_code_syntax`: AST validation for custom code → catches syntactically invalid code

#### 2.3.3 Structural Validation (catches: logical errors)
LLMs may produce structurally inconsistent outputs.
- `validate_span_ordering`: t_start < t_end
- `validate_ode_model_requirements`: Required fields present for each model type

**Key insight**: The `value_in_snippet` validator is the primary anti-hallucination defense. By requiring that every extracted numeric value appears verbatim in the quoted source text, we can automatically detect when an LLM has invented a number.

### 2.4 Automatic Julia/Turing.jl Code Generation

#### 2.4.1 Single-Target Translation
- YAML → complete Julia inference script
- ODE function generation from model type
- Prior specification from `calibration.parameters`
- Likelihood construction from `calibration.measurements`
- NUTS sampler configuration

#### 2.4.2 Joint Inference with Parameter Sharing

**The key insight**: Parameters with the same name across targets ARE the same parameter.

**How it works**:
1. Load multiple YAML targets
2. Scan all `calibration.parameters` across targets
3. Identify shared parameters by name matching
4. Generate single Turing model with:
   - One prior per unique parameter (shared parameters declared once)
   - One likelihood term per target (each target contributes its constraint)
   - Single NUTS sampler exploring the joint posterior

**What this enables**:
- **Global optimization**: Parameters must satisfy ALL targets simultaneously
- **Information pooling**: Multiple experiments → tighter posteriors on shared parameters
- **Correlation capture**: Joint posterior reveals how parameters covary
- **Automatic identifiability improvement**: Shared parameters get more data

**Example**: If targets A and B both involve parameter `k_psc_const`:
```
k_psc_const ~ LogNormal(prior)  # declared once
target_A_pred = simulate(k_psc_const, ...)
target_B_pred = simulate(k_psc_const, ...)
obs_A ~ Normal(target_A_pred, σ_A)  # likelihood from target A
obs_B ~ Normal(target_B_pred, σ_B)  # likelihood from target B
```

### 2.5 Posterior Diagnostics

- **Convergence**: R-hat (target < 1.01), ESS (target > 400/chain)
- **Posterior predictive checks**:
  - Z-scores: (observed - predicted) / posterior_sd
  - Coverage: Fraction of observations within posterior CI
- **Model assessment**: Visual trace plots, pair plots

### 2.6 Application: PDAC Stromal Biology

- **Model context**: Pancreatic stellate cell dynamics in tumor microenvironment
- **Target scope**: 10 calibration targets from published literature
- **Parameter scope**: 10 parameters (1 shared across targets)
- **Literature sources**: [List key papers]

---

## 3. Results

### 3.1 Schema Validation Results

- N YAML files created for PDAC targets
- Validation pass rates by validator type
- Example validation catches (anti-hallucination, DOI resolution)

### 3.2 Calibration Targets Extracted

**Table: Summary of 10 Calibration Targets**

| Target | Parameter(s) | Model Type | Data Source |
|--------|--------------|------------|-------------|
| ECM secretion | k_ECM_apsc_sec | exponential_growth | [Ref] |
| PSC activation | k_psc_activation | two_state | [Ref] |
| aPSC death | k_apsc_death | first_order_decay | [Ref] |
| qPSC death | k_qpsc_death | first_order_decay | [Ref] |
| aPSC proliferation | k_apsc_prolif | exponential_growth | [Ref] |
| PSC recruitment (const) | k_psc_const | direct_conversion | [Ref] |
| PSC recruitment (encounter) | k_psc_encounter | direct_conversion | [Ref] |
| T cell killing | p_T_kill_per_contact | direct_fit | [Ref] |
| TGF-β secretion | k_TGFb_sec_apsc | exponential_growth | [Ref] |
| Treg suppression | R50_Treg | direct_fit | [Ref] |

### 3.3 Joint Inference Results

#### 3.3.1 Convergence Diagnostics

**Table: Posterior Summary with Convergence Metrics**

| Parameter | Posterior Median | Units | 95% CI | R-hat | ESS |
|-----------|------------------|-------|--------|-------|-----|
| k_ECM_apsc_sec | 8.74×10⁻¹⁰ | mg/(cell·day) | [...] | 1.001 | 3839 |
| k_psc_activation | 2.58 | 1/day | [...] | 1.000 | 4074 |
| k_apsc_death | 0.091 | 1/day | [...] | 1.002 | 4020 |
| k_qpsc_death | 0.178 | 1/day | [...] | 1.002 | 3802 |
| k_apsc_prolif | 1.44 | 1/day | [...] | 1.001 | 4590 |
| k_psc_const | 3.49×10⁷ | cell/mL | [...] | 1.002 | 2670 |
| k_psc_encounter | 2.54×10⁵ | cell/(mL·day) | [...] | 1.001 | 2388 |
| p_T_kill_per_contact | 0.150 | - | [...] | 1.000 | 4023 |
| k_TGFb_sec_apsc | 3.75×10⁻¹⁰ | nM·L/(cell·day) | [...] | 1.002 | 3282 |
| R50_Treg | 0.411 | - | [...] | 1.000 | 4571 |

- All R-hat ≈ 1.0 (excellent convergence)
- All ESS > 2000 (well above 400/chain threshold)

#### 3.3.2 Posterior Predictive Performance

**Table: Observed vs Predicted with Diagnostics**

| Target | Observed | Predicted | Z-score | 90% CI | 95% CI |
|--------|----------|-----------|---------|--------|--------|
| ecm_secretion | 6.48×10⁻¹⁰ | 8.74×10⁻¹⁰ | -0.69 | ✓ | ✓ |
| psc_activation | 0.950 | 0.994 | -1.19 | ✓ | ✓ |
| ... | ... | ... | ... | ... | ... |

**Summary statistics:**
- Mean |Z| = 0.44 (target: < 1.0) ✓
- Max |Z| = 1.19 (target: < 2.0) ✓
- 90% coverage: 100% (target: ~90%)
- 95% coverage: 100% (target: ~95%)

→ Well-calibrated posteriors with appropriate uncertainty

### 3.4 Parameter Sharing Example

- k_psc_const appears in two targets (recruitment_const, recruitment_encounter)
- Joint inference constrains it from both data sources
- Improved identifiability vs. separate inference
- [Figure: Posterior correlation plot showing parameter relationships]

---

## 4. Discussion

### 4.1 Playing to LLM Strengths While Guarding Against Weaknesses

#### 4.1.1 What LLMs Do Well (and how we leverage it)
- **Reading and comprehension**: LLMs can process papers and identify relevant passages at scale
- **Template following**: Given a structured schema, LLMs produce consistent output formats
- **Unit conversion and calculation**: LLMs can perform the arithmetic needed for derivations
- **Rationale generation**: LLMs can articulate the reasoning behind modeling choices

#### 4.1.2 What LLMs Do Poorly (and how we guard against it)
- **Hallucination**: LLMs may invent values → `value_in_snippet` validator requires source text evidence
- **Fabricated citations**: LLMs may generate fake DOIs → DOI resolution validator checks CrossRef
- **Inconsistent references**: LLMs may reference non-existent inputs → reference validators check consistency
- **Overconfidence**: LLMs don't express uncertainty well → human review required for scientific judgment

#### 4.1.3 The Human-LLM Division of Labor
- **LLM role**: First-pass extraction, template population, boilerplate code generation
- **Human role**: Scientific judgment, assumption validation, edge case handling
- **Validation layer**: Automated gatekeeper between LLM output and downstream inference
- **Result**: Speed of LLM extraction + rigor of human oversight

### 4.2 Benefits of Structured Schema Approach

#### 4.2.1 Reproducibility
- Every value traces to source text via snippets
- Executable path: YAML → Julia → Posterior
- Version-controlled, diff-friendly format
- No hidden assumptions in spreadsheets

#### 4.2.2 Validation as Safety Net
- Anti-hallucination check catches fabricated values
- DOI resolution verifies citations exist
- Unit validation prevents conversion errors
- Catches errors before costly inference runs

#### 4.2.3 Separation of Concerns
- Extraction layer: What does the paper say?
- Inference layer: How do we use it?
- Enables different people/roles to contribute
- Facilitates review and auditing

### 4.3 Joint Bayesian Inference: Why It Matters

#### 4.3.1 Global vs. Local Optimization
- **Local approach** (traditional): Calibrate each parameter independently, then combine via ad-hoc averaging
- **Global approach** (joint inference): Find parameter values that simultaneously satisfy ALL targets
- Joint inference naturally handles trade-offs—if one target pulls a parameter up and another pulls it down, the posterior reflects this tension

#### 4.3.2 Parameter Sharing Across Targets
- When multiple experiments inform the same parameter, joint inference pools the information
- Example: `k_psc_const` appears in both recruitment_const and recruitment_encounter targets
- Each target contributes a likelihood term; the shared prior is updated by both
- Result: tighter posterior than either target alone could provide

#### 4.3.3 Uncertainty Propagation
- Posteriors are full distributions, not point estimates
- Uncertainty from extraction (CI from papers) propagates through to parameter uncertainty
- Parameter uncertainty can then propagate to model predictions
- Enables credible intervals on model outputs, not just point predictions

#### 4.3.4 Correlation Structure
- Joint posterior captures how parameters covary
- Important for model predictions: if k₁ and k₂ are correlated, sampling them independently would underestimate prediction uncertainty
- Pair plots reveal which parameters are identifiable vs. confounded

#### 4.3.5 Principled Data Combination
- No need for ad-hoc weighting schemes ("trust this paper more than that one")
- Sample size and reported uncertainty naturally weight each target's contribution
- Bayes' theorem handles the combination—the posterior is the mathematically correct answer given the data and priors

### 4.4 Comparison to Existing Approaches

| Approach | Provenance | Validation | LLM-Compatible | Auto Code Gen | Joint Inference |
|----------|------------|------------|----------------|---------------|-----------------|
| Manual spreadsheet | Poor | None | No | No | No |
| Parameter databases | Limited | Varies | No | No | No |
| Naive LLM extraction | None | None | Yes | No | No |
| **This work** | Complete | Automated | Yes | Yes | Yes |

### 4.5 Limitations

#### 4.5.1 LLM Limitations (not fully addressed)
- Semantic errors: LLM may misinterpret study design even with correct extraction
- Context limits: Very long papers may exceed context window
- Model dependence: Results may vary across LLM versions
- Cost: API calls add up for large-scale extraction

#### 4.5.2 Schema Scope
- Currently limited to isolated system targets
- Full model targets require different approach
- Custom models need manual code

#### 4.5.3 Validation Limitations
- Snippet matching is string-based, not semantic
- Cannot catch scientifically incorrect interpretations
- DOI resolution doesn't verify paper content matches claimed findings

#### 4.5.4 Translation Limitations
- Fixed set of built-in ODE models
- Julia/Turing.jl specific (not portable to other platforms)
- No automatic species translation (rat → human)

### 4.6 Future Directions

#### 4.6.1 Improved LLM Integration
- Multi-pass extraction: LLM proposes → validator checks → LLM revises
- Fine-tuned models for QSP-specific terminology
- Retrieval-augmented generation for long papers
- Confidence scoring for LLM outputs

#### 4.6.2 Integration with Full QSP Model
- Joint inference: isolated targets + clinical targets
- Virtual population generation from posteriors
- Sensitivity analysis using posterior samples

#### 4.6.3 Expanded Scope
- Additional cancer types (NSCLC, TNBC, melanoma)
- Additional cell types (CD8, MDSC, macrophages)
- Drug-specific parameters (checkpoint inhibitors)

---

## 1. Introduction

### 1.1 The Calibration Challenge in QSP

- QSP models require extensive parameterization from heterogeneous sources
- Typical PDAC model: 100+ parameters, 50+ from literature
- Current practice:
  - Manual extraction into spreadsheets
  - Poorly documented assumptions
  - Lost provenance ("where did this number come from?")
  - Copy-paste propagation across models
- Consequences:
  - Irreproducibility
  - Difficult peer review
  - Wasted effort re-extracting same data

### 1.2 Isolated System Targets

- Definition: In vitro/ex vivo experiments measuring parameters in isolation
- Advantages over clinical targets:
  - Abundant data availability
  - Simpler inference (fewer confounding parameters)
  - Directly interpretable mechanisms
- Challenge: Systematic extraction with uncertainty quantification

### 1.3 Existing Approaches and Gaps

**Parameter databases:**
- Limited coverage, no uncertainty
- Often missing experimental context
- Hard to trace to original source
- Not designed for LLM integration

**Naive LLM extraction:**
- Hallucination risk: LLMs may fabricate values or citations
- Unstructured outputs not machine-readable
- No validation layer to catch errors
- No path from extraction to inference code

**Manual expert curation:**
- High quality but not scalable
- Inconsistent documentation across experts
- Knowledge leaves with experts
- Cannot keep pace with literature growth

**The opportunity**: LLMs excel at reading papers and following templates. The challenge is building guardrails that catch their failure modes while preserving their speed advantage.

### 1.4 Our Contribution

A framework that harnesses LLM capabilities while systematically guarding against their weaknesses:

1. **SimplifiedIsolatedTarget schema**: Structured template that constrains LLM output to a predictable, machine-verifiable format
2. **10-validator framework**: Automated checks targeting specific LLM failure modes (hallucination, fabricated citations, inconsistent references)
3. **Automatic Julia/Turing.jl translator**: YAML → inference code, removing manual transcription errors
4. **Demonstration**: 10 PDAC stromal biology targets with full convergence diagnostics

**Key insight**: The schema + validation approach creates a "trust but verify" workflow—LLMs provide speed, validators provide safety, humans provide judgment.

### 1.5 Article Overview

- Methods: Schema design, validation framework, code generation, application setup
- Results: Extracted targets, joint inference results, diagnostics
- Discussion: Benefits, limitations, future directions

---

## 5. Conclusions

- Presented a framework for LLM-assisted calibration target extraction that plays to LLM strengths (speed, template following) while guarding against weaknesses (hallucination, fabrication)
- SimplifiedIsolatedTarget schema constrains LLM output to structured, machine-verifiable format
- 10 validators specifically target LLM failure modes: hallucinated values caught by snippet matching, fabricated DOIs caught by CrossRef resolution
- Automatic Julia code generation removes manual transcription as error source
- Demonstrated on 10 PDAC targets: all parameters converged, excellent posterior predictive performance
- The "trust but verify" approach enables scalable extraction without sacrificing scientific rigor
- Open source: github.com/popellab/qsp-llm-workflows

---

## Figures

1. **Workflow Overview**: Paper → LLM → YAML → Validators → Julia → Posterior (showing where LLM contributes and where guardrails apply)
2. **Schema Architecture**: inputs layer vs calibration layer, showing how structure constrains LLM output
3. **Validation Framework**: 10 validators organized by LLM failure mode they catch (hallucination, fabrication, inconsistency)
4. **Submodel Philosophy**: How isolated experiment connects to full model via shared parameter names
5. **Joint Inference Diagram**: Parameter sharing across targets
6. **Posterior Results**: Trace plots or pair plots for key parameters
7. **Posterior Predictive**: Observed vs predicted with uncertainty bands

## Tables

1. **Calibration Targets Summary**: 10 targets with parameters, model types, sources
2. **Posterior Summary**: Median, CI, R-hat, ESS for all parameters
3. **Posterior Predictive Diagnostics**: Z-scores, coverage for all targets
4. **Validation Suite**: 10 validators with descriptions and what they catch

## Supplementary Material

- S1: Full SimplifiedIsolatedTarget Pydantic schema
- S2: Complete YAML files for all 10 targets
- S3: Generated Julia code for joint inference
- S4: Posterior trace plots and pair plots
- S5: Validation reports

---

## Notes / Open Questions

- [ ] Include timing comparison (schema approach vs manual)?
- [ ] Add worked example walkthrough in Methods?
- [ ] How much Julia code to show in main text vs supplement?
- [ ] Include comparison to literature values from other QSP models?
- [ ] Should we include any LLM-assisted extraction results or save for future paper?
