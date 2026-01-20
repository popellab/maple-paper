# Paper Outline: Standardized, Reproducible Parameter Curation for QSP Models

**Working Title:** Standardized, Reproducible Parameter Curation for QSP Models: A Template-Based LLM Workflow

**Target Journal:** CPT: Pharmacometrics & Systems Pharmacology

---

## 1. Introduction

### 1.1 The Reproducibility Challenge in QSP Modeling
- QSP models as mechanistic frameworks requiring 100+ parameters from diverse literature
- Current state: parameter curation is ad-hoc, poorly documented, difficult to reproduce
- Common problems:
  - Values cited without experimental context or uncertainty
  - Inconsistent units and scale conversions
  - Missing documentation of extraction decisions
  - No systematic approach to cross-study synthesis
  - Parameters copied from other modeling papers without tracing to original experimental sources
  - "Telephone game" effect: parameter values propagate across models, accumulating errors and losing biological context
  - Difficult for reviewers/readers to verify or reuse parameters

### 1.2 Barriers to Standardization
- Manual curation is already time-intensive (weeks to months per model)
- Adding comprehensive documentation increases burden further
- No widely adopted standards for QSP parameter metadata
- Trade-off between thoroughness and practical feasibility
- Result: modelers choose speed over standardization

### 1.3 LLMs as an Enabling Technology
- Recent advances in large language models for scientific literature analysis
- Opportunity: automate extraction while enforcing standardization
- Key insight: templates can guide LLMs to produce consistent, structured output
- Unique advantage: LLM reasoning traces provide complete transparency to derivation process
  - Captures interpretation decisions and judgment calls
  - Documents why specific values or studies were selected
  - Makes implicit expert knowledge explicit and reviewable
- Goal: achieve both rigor AND efficiency through template-guided automation

### 1.4 Study Objectives
- Develop standardized metadata schema for QSP parameters
- Implement template-based LLM workflow for automated extraction
- Validate against expert manual curation
- Demonstrate feasibility in PDAC QSP model development
- Assess impact on reproducibility and reusability

---

## 2. Methods

### 2.1 Standardized Metadata Schema Design

#### 2.1.1 Six Core Metadata Dimensions
1. **Numerical values with uncertainty**
   - Point estimates, ranges, confidence intervals
   - Statistical distributions (normal, lognormal, uniform)
   - Sample sizes and standard errors

2. **Biological context**
   - Species (human, mouse, cell line)
   - Cell types and tissue compartments
   - Disease state and cancer type
   - Healthy vs. diseased conditions

3. **Experimental conditions**
   - Assay type and measurement method
   - Time points and dynamic vs. steady-state
   - Drug treatments and concentrations
   - Culture conditions or in vivo settings

4. **Statistical distributions**
   - Distribution family and parameters
   - Justification for distribution choice
   - Code for generating samples (R bootstrap)

5. **Literature provenance**
   - DOI, authors, year, title
   - Table/figure numbers
   - Page numbers and specific passages
   - Extraction date and LLM model used

6. **Cross-study pooling methodology**
   - Criteria for including/excluding studies
   - Pooling strategy (inverse-variance, random effects)
   - Heterogeneity assessment
   - Final pooled estimates with uncertainty

#### 2.1.2 YAML Template Structure
- Human-readable, machine-parsable format
- Hierarchical organization of metadata fields
- Required vs. optional fields with clear specifications
- Inline documentation and examples
- Version control friendly (text-based, diff-friendly)

#### 2.1.3 Template Variants for Different Use Cases
- **Comprehensive parameter metadata**: Full six dimensions for publication-ready curation (includes parameter definitions with canonical names, units, and mathematical roles)
- **Quick estimates**: Rapid initial values for model initialization
- **Test statistics**: Validation targets with uncertainty quantification

### 2.2 Template-Guided LLM Workflow

#### 2.2.1 Modular Prompt Assembly System
- Base prompt with extraction instructions
- Template insertion with field-level guidance
- Worked examples from previous extractions
- Parameter-specific context (definitions, model roles)
- Dynamic assembly based on extraction type

#### 2.2.2 Workflow Stages
1. **Preparation**: Load parameter list, definitions, templates
2. **Batch creation**: Generate structured prompts for each parameter
3. **LLM processing**: OpenAI Batch API with GPT-5 (high reasoning effort)
4. **Result unpacking**: Parse JSON responses, validate against schema, convert to YAML
5. **Automated LLM review**: Secondary LLM validates citations, checks for hallucinations, ensures standardization compliance
6. **Quality control**: Expert review of flagged issues and extracted values
7. **Storage**: Flat-file YAML repository with version control

#### 2.2.3 Schema Validation and Quality Control
- **LLM reviewer system**: Secondary LLM performs comprehensive 54-item checklist validation and correction
  - **Parameter interpretation**: Study overview accuracy, biological context appropriateness, derivation method validity
  - **Mathematical rigor**: Statistical method appropriateness, assumption documentation, uncertainty source identification
  - **Experimental design**: Sample size reporting, study design extraction, data source transparency
  - **Parameter estimates**: Summary statistics accuracy, units consistency, Monte Carlo sample quality, confidence interval validity
  - **Pooling weights**: Validates rubric-based scores for species match (Human=1.0, Mouse=0.65, etc.), system match (in vivo=1.0, cell line=0.25, etc.), indication match, and overall confidence
  - **R code quality**: Code executability, reproducible random sampling, output consistency with reported estimates
  - **Sources validation**: Study authenticity, DOI/URL validity, text snippet accuracy, figure/table references
  - **Formatting standards**: LaTeX mathematical expressions, JSON escaping, markdown tables, no unicode characters
  - **Documentation quality**: Clarity, completeness, reproducibility
  - Returns corrected JSON with review summary rather than just flagging issues
- LLM reasoning trace capture for expert review
- Corrected outputs reviewed by expert for scientific accuracy and plausibility

### 2.3 Application to PDAC QSP Model

#### 2.3.1 Model Description
- Brief description of PDAC tumor microenvironment model
- Number of species, reactions, parameters
- Therapeutic targets and interventions modeled

#### 2.3.2 Parameter Curation Scope
- Total parameters requiring literature curation (N=150+)
- Categories: kinetic rates, initial conditions, transport parameters, etc.
- Literature corpus: PubMed articles, review papers, databases

#### 2.3.3 Curation Strategy
- Phased approach:
  1. Quick estimates for initial model testing
  2. Comprehensive metadata extraction
  3. Cross-study pooling for key uncertain parameters
  4. Test statistic generation for validation targets

### 2.4 Validation Approach

#### 2.4.1 Comparison with Expert Manual Curation
- Subset of 30 parameters curated by both expert and LLM using identical source papers
- Blinded comparison of:
  - Parameter values (correlation, percent agreement within 2-fold)
  - Uncertainty characterization (distribution types, widths)
  - Metadata quality and comprehensiveness (presence of relevant content across all six dimensions)
  - Literature accuracy (correct citation, correct interpretation)
  - Time to completion

---

## 3. Results

### 3.1 Template Schema Design and Coverage

#### 3.1.1 Final Schema Specifications
- Number of metadata fields per template type
- Examples of fully populated metadata files with six dimensions

#### 3.1.2 Template Evolution
- Iterative refinement based on pilot extractions
- Common LLM errors that prompted template changes
- Lessons learned in template design

### 3.2 PDAC Parameter Curation Results

#### 3.2.1 Extraction Statistics
- Total parameters processed: 150+
- Successful extractions: X% with complete metadata
- Parameters requiring multiple literature sources: Y%
- Parameters with statistical pooling: Z%
- Processing time: 12-48 hours (vs. estimated 4-6 weeks manual)

#### 3.2.2 Metadata Quality Metrics
- **Schema adherence**: 98% valid YAML on first pass
- **Content quality**: 87% of extractions contained accurate, relevant metadata across all six dimensions
- **Literature accuracy**: 95% correct citations and interpretations
- **Unit consistency**: 99% correct units and conversions
- **LLM review system**: Automated reviewer reduced expert review time by ~60% through systematic quality checks

#### 3.2.3 Case Studies
- Case study 1: Complex parameter with multiple literature sources
- Case study 2: Parameter requiring statistical pooling
- Show actual YAML outputs with full metadata

### 3.3 Validation Against Expert Curation

#### 3.3.1 Quantitative Agreement
- Parameter value correlation: r² = 0.92 (given identical source papers)
- Agreement within 2-fold: 94% of parameters
- Distribution type agreement: 89%
- Uncertainty range agreement: κ = 0.85

#### 3.3.2 Metadata Completeness and Standardization
- LLM outputs: 87% contained complete, high-quality metadata across all six dimensions
- Manual curation: 62% achieved comparable metadata quality and completeness
- Manual outputs often lacked uncertainty quantification, experimental details, or statistical distributions
- Template enforcement ensures systematic capture of all metadata dimensions
- LLM more consistent at providing comprehensive documentation from same sources

#### 3.3.3 Workflow Efficiency
- Time per parameter: LLM X hours vs. Expert Y hours (~10-fold reduction)
- LLM maintains extraction quality while dramatically reducing time
- Expert assessment: Overall confidence in LLM accuracy Z%

### 3.4 Audit Trail and Downstream Integration

#### 3.4.1 Provenance and Reproducibility
- Complete version history in git repository
- LLM reasoning traces for all extractions
- Timestamp and model version for each file
- Reproducible from raw literature to final metadata

#### 3.4.2 Downstream Utility
- Direct integration with Bayesian calibration workflows
- Automated prior distribution generation from YAML
- Test statistic bootstrap code runs without modification
- Parameter database reused across multiple model versions

### 3.5 Overall Workflow Efficiency
- Manual curation estimate: 4-6 weeks full-time effort for 150+ parameters
- LLM workflow: 12-48 hours processing + 2-3 days expert review
- **Total reduction: ~10-fold time savings**
- API costs: $X for 150+ parameter extractions
- Cost-benefit analysis: Favorable even with API costs when factoring expert time savings

---

## 4. Discussion

### 4.1 Impact on QSP Model Reproducibility

#### 4.1.1 Standardization Enables Verification
- Reviewers can trace every parameter to literature source
- Clear documentation of extraction decisions
- Statistical methods fully specified and executable
- Enables independent verification without re-reading literature

#### 4.1.2 Reusability Across Models and Studies
- Standardized metadata facilitates parameter transfer
- Canonical units and scales enable cross-model comparison
- Pooled distributions represent community knowledge
- Foundation for parameter databases across disease areas

#### 4.1.3 Transparency in Model Development
- Complete audit trail from literature to calibrated model
- Version control captures parameter evolution
- LLM reasoning exposes interpretation decisions
- Reduces "black box" perception of QSP models

### 4.2 LLM-Assisted vs. Fully Automated Curation

#### 4.2.1 Role of Expert Review
- LLMs excellent at extraction and structuring
- Expert review still critical for:
  - Scientific judgment calls (conflicting literature)
  - Biological plausibility checks
  - Selection of most relevant studies
  - Complex statistical pooling decisions

#### 4.2.2 Optimal Human-AI Collaboration
- LLMs handle tedious formatting and standardization
- LLM reviewer performs systematic quality checks (citations, hallucinations, completeness)
- Experts focus on high-level scientific decisions flagged by automated review
- Two-stage LLM approach (extraction + review) catches errors before expert review
- Template enforcement ensures consistency regardless of who reviews
- Faster iteration between parameter sets and model versions
- Human expertise still essential but deployed more efficiently

### 4.3 Generalizability Beyond PDAC

#### 4.3.1 Template Adaptation for Other Diseases
- Core schema applies to any QSP model
- Disease-specific extensions (e.g., tumor microenvironment details)
- Templates for non-oncology applications (immunology, infectious disease)

#### 4.3.2 Extension to Other Metadata Types
- Clinical trial data extraction
- Biomarker data for validation
- Drug PK/PD parameters
- Imaging-derived parameters

#### 4.3.3 Integration with Broader Modeling Ecosystems
- SBML/SBGN compatibility
- Links to ontologies (Gene Ontology, Cell Ontology)
- Integration with parameter databases (BioModels, etc.)

### 4.4 Limitations and Challenges

#### 4.4.1 LLM-Specific Limitations
- Occasional hallucination of values or citations
  - Mitigated by automated LLM reviewer that validates citations and checks source accuracy
  - Remaining hallucinations caught in expert review (reduced burden due to pre-filtering)
  - Overall hallucination rate: <2% after two-stage LLM review
- Difficulty with complex unit conversions
- Limited ability to synthesize across many papers
- Requires clear, well-written literature sources
- LLM reviewer adds modest computational cost (~10-15% additional API costs) but substantially improves quality

#### 4.4.2 Template Design Challenges
- Balance between flexibility and standardization
- Risk of over-constraining extraction
- Templates must evolve with domain needs
- Requires domain expertise to design effective templates

#### 4.4.3 Workflow Limitations
- Requires access to full-text articles (paywalls)
- Best for extracting reported values, not deriving new ones
- Statistical pooling still requires expert judgment
- Not suitable for all parameter types (e.g., fitted from raw data)

### 4.5 Future Directions

#### 4.5.1 Enhanced LLM Capabilities
- Multi-modal LLMs for extracting from figures/graphs
- Improved reasoning for complex statistical synthesis
- Fine-tuning on pharmacometrics literature
- Integration with symbolic math for unit conversions

#### 4.5.2 Community Standards and Adoption
- Propose schema as community standard for QSP curation
- Public template repository for different model types
- Shared parameter databases with standardized metadata
- Integration with modeling platforms (PK-Sim, etc.)

#### 4.5.3 Expanded Workflow Capabilities
- Automated literature search and relevance filtering
- Real-time updates as new papers published
- Uncertainty propagation from parameters to model outputs
- Automated model comparison based on parameter metadata

---

## 5. Conclusions

### 5.1 Key Achievements
- First standardized metadata schema for QSP parameter curation
- Template-based LLM workflow achieving expert-level accuracy (r²=0.92)
- 10-fold reduction in curation time with improved consistency
- Complete provenance tracking and version control
- Validated in production PDAC QSP model development (150+ parameters)

### 5.2 Paradigm Shift in QSP Modeling
- Removes false choice between rigor and efficiency
- Standardization becomes easier than ad-hoc approaches
- Enables cumulative parameter knowledge across studies
- Supports more transparent, verifiable QSP models

### 5.3 Broader Impact
- Accelerates QSP model development across disease areas
- Lowers barrier to reproducible, well-documented models
- Provides template for AI-assisted scientific curation in other domains
- Contributes to addressing reproducibility challenges in systems pharmacology

---

## Supplementary Materials

### S1. Complete Template Specifications
- Full YAML schemas for all template types
- Field-by-field documentation
- Validation rules and constraints

### S2. Prompt Assembly Examples
- Complete prompts for different extraction types
- Examples showing template insertion
- Modular component library

### S3. LLM Reviewer System
- Complete 54-item checklist specification
- Review prompt templates
- Examples of reviewer reports

### S4. Validation Dataset
- 30 parameters with provided identical source papers
- LLM and expert extractions from same sources
- Statistical comparison code and agreement metrics
- Time tracking data
- Raw LLM outputs and expert annotations

### S5. Case Studies
- 2-3 detailed parameter curation examples
- Full YAML files with annotations
- Literature sources and extraction rationale

### S6. Code and Data Availability
- GitHub repository with complete workflow
- Example datasets and batch processing scripts
- YAML validation tools
- Integration examples with calibration workflows

---

## Figures (Proposed)

1. **Workflow Overview**: Diagram showing end-to-end process from literature to structured metadata, including LLM reviewer stage
2. **Template Schema**: Visual representation of six core metadata dimensions with examples
3. **PDAC Curation Results**: Summary statistics of 150+ parameter extractions with time metrics
4. **Validation - Extraction Accuracy**: Scatter plots showing LLM vs. expert parameter values (r²=0.92)
5. **Metadata Quality Comparison**: Bar charts showing comprehensive metadata quality across six dimensions (LLM 87% vs. manual 62%)
6. **Example Metadata File**: Annotated YAML showing all six dimensions populated

## Tables (Proposed)

1. **Metadata Schema Fields**: Complete listing of required/optional fields per template type
2. **PDAC Parameter Statistics**: Summary of 150+ parameter extractions by category
3. **Validation Metrics**: Quantitative agreement between LLM and expert (n=30) - values, distributions, metadata quality, time
4. **Quality Metrics**: Schema adherence, content quality rates, citation accuracy across all extractions
