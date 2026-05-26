Dear Dr. Eliason,

Manuscript ID PSP-2026-0079 entitled "Structured Schemas for LLM-Modeler Collaboration in Quantitative Systems Pharmacology Model Calibration" which you submitted to CPT: Pharmacometrics & Systems Pharmacology, has been evaluated. The revision comments are included at the bottom of this letter. I invite you to respond to these suggestions and revise your manuscript accordingly.

Because we are trying to facilitate timely publication, your revised manuscript should be submitted to our system within four weeks of receiving this letter.

Authors are required to supply sufficient technical details (including example model code and datasets) as supplementary information or in a publicly accessible repository to allow readers to replicate the key modeling and simulation steps described in the main article.

INSTRUCTIONS:
You will be unable to make your revisions directly on the originally submitted manuscript files. Instead, revise your manuscript text using a word processing program, save it on your computer, and then use the "Remove & Replace Files" tab to upload your revised text file. Please highlight the changes you've made to your manuscript by using the track changes mode in MS Word or by using bold or colored text. Be sure to include the following within the revised main document: author name(s) and affiliation(s), conflict of interest statement(s), and figure legends. Please delete any redundant files before completing the submission.

Please check your revision carefully to ensure it is final as written. To preserve the integrity of peer-review, changes cannot be made after acceptance.

Please include a "Response" document that includes your responses to each of the revision comments, as well as a marked or highlighted manuscript file clearly showing changes made during revision.

SUBMIT YOUR REVISION:
To revise your manuscript, click on the link below:

https://psp.msubmit.net/cgi-bin/main.plex?el=A3JQ7BVB6A3Ewi3I5A9ftdE3LvjuUvpfekcPSZxjL0EgZ

(NOTE: The above link automatically submits your login name and password. If you wish to share this link with colleagues, please be aware that they will have access to your entire account for this journal.)

Submitting a revised manuscript does not guarantee acceptance of the paper for publication. The final decision will be based upon the comments of the reviewers, Associate Editor, and Editor-in-Chief.

Once again, thank you for submitting your manuscript to CPT: Pharmacometrics & Systems Pharmacology and I look forward to receiving your revision.

Sincerely,
Dr. France Mentré
Editor-in-Chief
CPT: Pharmacometrics & Systems Pharmacology







Reviewer #1 (Remarks to the Author):

This paper makes a genuine contribution to the QSP community, and I want to highlight what I think works well before turning to suggestions for improvement.

The central design decision, separating what a paper reports (the inputs layer) from how to use it for calibration (model type, priors, likelihood), is more than good engineering. It formalizes a distinction that experienced modelers make intuitively but rarely document. When a modeler leaves a project, the reasoning behind parameter choices is typically lost; with MAPLE, it is preserved in the schema. This alone is a useful community contribution, independent of any LLM involvement.
The validation framework is technically sound and reflects real understanding of LLM failure modes. The value-in-snippet check is clever, it exploits the fact that LLMs hallucinating a number rarely bother fabricating a consistent supporting quote. The DOI resolution and external snippet verification add meaningful additional layers. Together, these form a practical defense that other scientific domains could adapt.
I also want to commend the transparent reporting. Zero first-pass validation success, 65% model-type revision rate, 58% batch rejection, these numbers take intellectual honesty to publish.
The source_relevance block, requiring structured documentation of species translation, indication match, and uncertainty propagation to priors, is a principled contribution that makes implicit modeler reasoning auditable.

To strengthen the manuscript, I would suggesst to address the following:

Major Comments:

1. Framing of LLM vs. modeler contribution:
The title says "LLM-Modeler Collaboration," but the data tells us the modeler changed the forward model type in 65% of files, adjusted priors in 46%, and revised source relevance in 100%. After curation, the LLM's surviving contribution is essentially literature identification, snippet extraction, and YAML scaffolding. That is genuinely useful, but it is closer to an intelligent assistant than a scientific collaborator. I am not suggesting this is a weakness; it may be exactly the right division of labor. But the framing should match the evidence. Explicitly characterizing the LLM as handling mechanical tasks while the modeler provides scientific content would actually make the contribution claim more defensible.

2. Batch vs. interactive comparison:
The batch pipeline used GPT-5.1; interactive extraction used Claude Opus 4. Since these differ in capability, context handling, and error profiles, the observed differences between modes could reflect the LLM rather than the workflow. Combined with learning effects (the modeler curated batch outputs before doing interactive work), the comparison is observational at best. I would not ask for a controlled experiment, but the text should explicitly acknowledge these confounds rather than implying interactive mode is inherently superior.

3. Inference validation:
The inference section appropriately serves as a pipeline demonstration rather than a full calibration study. However, the claim that all ESS > 3000 is contradicted by Table 9 (N_IL2_CD8 tail-ESS = 1334, N_IL2_CD4 tail-ESS = 2549) and should be corrected. The biological plausibility claims (e.g., ~130-day doubling time) should cite specific clinical references, a paper setting this standard for provenance in extraction should apply it to its own results.

4. Generalizability claims:
The evaluation covers one model, one disease area, one group. This is perfectly acceptable for a methods paper introducing a new framework, but the abstract and Discussion should say so. Notably, 49% of SubmodelTargets used the generic "algebraic" type, meaning the 15 built-in templates covered only about half the use cases even for this model. A brief "Generalization Requirements" paragraph discussing what adaptation would be needed for a non-oncology application would be helpful.

5. CalibrationTarget metrics gap:
Per-target extraction metrics are reported only for the 18 SubmodelTargets. For the 59 CalibrationTargets, the majority of the dataset, there are no retries, tokens, or error breakdowns. I understand this is because the Logfire tracing was only instrumented for SubmodelTargets, but even aggregate statistics would help the reader assess performance on the more complex schema.


Minor Comments:

1. Table 10 units: All parameter units listed as "-" in a paper about rigorous unit tracking. Please correct.
2. External validator: The snippet-in-paper validator (Section 2.3.3) is described but its pass/fail rate is not reported. If it was systematically applied, report results; if not, clarify its status.
3. Threshold justification: The fuzzy-match thresholds (75% title, 80% snippet) and uncertainty multipliers (2-fold cross-species, 3-fold cross-indication) directly affect what passes validation. Brief justification would help.
4. Prompt availability: Extraction prompts are described conceptually but not provided. Since results are prompt-dependent, representative prompts should be in the repository.
5. LLM versioning: Exact model identifiers and API dates should be recorded for reproducibility.
6. 58% rejection rate: This derives from N=12 CalibrationTarget files. Note the limited sample size or report confidence intervals.
7. Terminology: "Calibration target" as general concept vs. CalibrationTarget as schema name is occasionally confusing. A brief clarification early on would help.
8. Figure 1: The retry distribution bar chart for 18 targets could be reported inline. Consider whether it warrants a figure.
9. QSP-Copilot comparison: Section 4.4 characterizes QSP-Copilot as focusing solely on model structure discovery, but it does include literature extraction components. The contrast is slightly overstated.
10. PDAC model availability: The model is "adapted from" an unpublished bioRxiv preprint. Is the PDAC model itself available for independent evaluation?
11. Cost context: ~218K tokens per target is reported, but without even rough modeler time estimates, readers cannot assess net efficiency. A qualitative discussion would help.


Reviewer #2 (Remarks to the Author):

This is a timely and promising manuscript with a strong central contribution: MAPLE reframes LLM use in QSP calibration as a structured collaboration between modeler and machine rather than as full automation. The dual-schema design-SubmodelTarget for isolated experiments and CalibrationTarget for full-model clinical/in vivo endpoints-is well aligned with QSP practice, and the emphasis on provenance, uncertainty, source relevance, executable code, and validation directly addresses the major risks of LLM-based literature extraction. The most compelling aspect is the treatment of modeler input: forward model types, priors, source relevance, observable code, and empirical data often required expert revision, showing that MAPLE's value is in making scientific judgment explicit, auditable, and reproducible.
I would like to request that the authors tigthen the quantitative accounting and tempering the scope of the evaluation. Several target counts appear inconsistent. For example, the manuscript reports 87 targets versus 18 SubmodelTargets plus 59 CalibrationTargets, it later mention of 37 curated SubmodelTargets, and a scenario table that appears not to sum to 59 (Table 3).
It would also help clarifying validator performance, reporting whether errors remained after validation, as well as adding a workflow figure and one compact schema example, expanding the human-curation analysis.
Overall, this is a paper suitable for publication following minor revisions, with a valuable contribution to reproducible, provenance-rich QSP calibration.






Editorial Office Comments:

Please ensure the following items are addressed in your revision:

All manuscript pages should include page and line numbers. Please add them if they are not already included.

We encourage authors to link their ORCID accounts. If your manuscript is selected for publication, authors' ORCID IDs will be linked online and will aid readers to easily find authors' publications. Please include a list of each author's ORCID ID on the title page of the paper.

Please add two sections on your title page: Conflict of Interest and Funding. These sections should match the information included in your responses in the system. Please note in your Conflict of Interest statement the conflicts for all authors. If some of the authors do not have conflicts of interest, please use this statement: All other authors declared no competing interests for this work. If no authors have a conflict of interest, please use this statement: The authors declared no competing interests for this work. The conflict of interest statement should be included on the title page.

Please do not embed the figures within the manuscript file. Figures should be submitted as separate files with one figure per file; figures with multiple panels (A, B, C, etc.) should be combined into a single file.
For production purposes, please remove the figure labels/captions from the figure files and move them to the end of the manuscript file.

Use of Artificial Intelligence: In accordance with journal guidelines, please note that AI tools may be used in drafting assistance or to help in developing figures and tables. These tools should only be used to improve readability and language. All AI use must be credited, either in the acknowledgements or methods section. Authors remain responsible for all work submitted under their name.

All references should be accounted for and cited in the main text, and full publication details included in the reference list, including page numbers or DOIs as appropriate. References for figures and tables should appear at the end of the Reference list.
