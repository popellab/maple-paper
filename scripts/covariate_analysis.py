"""
Exploratory covariate meta-regression for single-target posteriors.
Run interactively: python -i scripts/covariate_analysis.py

Four analyses:
1. Per-parameter DL meta-analysis (no covariates)
2. Univariate screening: each covariate alone in pooled model
3. Multivariate model comparisons (including interactions)
4. Per-target covariate table for manual inspection
"""

import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
import yaml

# ── Load data ──────────────────────────────────────────────────────────

single_results = json.loads(Path("single_inference_results.json").read_text())

target_meta = {}
for yf in Path("metadata_storage").glob("*.yaml"):
    try:
        data = yaml.safe_load(yf.read_text())
        if data and "target_id" in data:
            target_meta[data["target_id"]] = data
    except Exception:
        pass

print(f"Loaded {len(single_results)} single-target posteriors, {len(target_meta)} YAML files\n")


# ── Measurement modality annotations ──────────────────────────────────
#
# Categories:
#   rate_direct       - time-course data → rate (doubling time, decay, imaging)
#   snapshot_density  - static cell count/density at one time point (IHC, endpoint)
#   accumulated       - accumulated secreted product over time (ELISA conditioned media)
#   fraction_ratio    - population fraction or ratio (flow cytometry %, IHC ratio)
#   migration_assay   - transwell / Boyden chamber migration
#
# Kept as a script-level lookup for exploration speed. Can formalize in
# the YAML schema if this proves to be a useful predictor.

MODALITY = {
    # k_C1_growth: clinical imaging VDT
    "k_C1_growth_pdac_human_vdt_ahn2017": "rate_direct",
    "k_C1_growth_pdac_tumor_doubling_jang2015": "rate_direct",

    # k_CCL2_sec: ELISA of conditioned media / clinical plasma
    "k_CCL2_sec_Steube1999_proxy": "accumulated",
    "k_CCL2_sec_bcproxy_yoshimura2023": "accumulated",
    "k_CCL2_sec_Fujita2010_PrSC": "accumulated",
    "k_CCL2_sec_psc_michalski2008": "accumulated",          # PSC culture ELISA 48h
    "k_CCL2_sec_pdac_plasma_Nixon2013": "snapshot_density",  # clinical plasma CCL2 (steady-state systemic)

    # k_M1_pol: flow cytometry M1/M2 % or IHC ratio
    "k_M1_pol_repolarization_horhold2020": "fraction_ratio",
    "k_M1_pol_Watkins2007_IL12_TAM_reprogramming": "fraction_ratio",
    "k_M1_pol_rp182_m2_to_m1_repolarization": "fraction_ratio",
    "k_M1_pol_pdac_cd86_cd163_gu2023": "fraction_ratio",  # IHC CD86/CD163 ratio
    "k_M1_pol_steady_state_ratio_DLBCL2021": "fraction_ratio",  # DLBCL M1:M2 fraction
    "k_M1_pol_pdac_m1m2ratio_DeSimoni2023": "fraction_ratio",   # PDAC iNOS/CD163 IHC ratio
    "k_M1_pol_tam_ratio_herwig2013": "fraction_ratio",          # uveal melanoma M2/M1 ratio
    "k_Mac_rec_humanPDAC_CD40_2021": "fraction_ratio",  # IHC M1:M2 ratio

    # k_MDSC_rec
    "k_MDSC_rec_recruitment_pericyte_MDSC_Hong2015": "snapshot_density",  # in vivo tumor counts
    "k_MDSC_rec_PDAC_Porembka2012": "fraction_ratio",  # flow cytometry MDSC %
    "k_MDSC_rec_oscc_ccl2_oo2022": "migration_assay",  # Boyden chamber
    "k_MDSC_rec_panc02_spleenexpansion_ghansah2013": "snapshot_density",  # mouse spleen MDSC counts
    "k_MDSC_rec_pdac_trovato2019": "fraction_ratio",    # flow cytometry M-MDSC % in PDAC
    "k_MDSC_rec_panc02_tnfr1_chopra2013": "snapshot_density",  # IHC CD11b+GR-1+ in Panc02

    # k_Mac_rec / k_Mac_death: IHC density
    "k_Mac_rec_PDAC_TAM_recruitment_Chen2015": "snapshot_density",
    "k_Mac_rec_PDAC_M1_recruitment_Gu2023": "snapshot_density",

    # k_apsc_death: cell viability/count over time
    "k_apsc_death_RA_Xiao2015": "rate_direct",
    "k_apsc_death_melatoninPSC_Estaras2021": "rate_direct",
    "k_apsc_death_hsc_apoptosis_issa2001": "rate_direct",  # in vivo HSC apoptosis over 42d

    # q_CD8_T_in
    "q_CD8_T_in_extravasation_boissonnas2007": "rate_direct",  # intravital imaging
    "q_CD8_T_in_yorty2007_sv11_brain_tumor": "snapshot_density",  # endpoint tumor counts
    "q_CD8_T_in_PDAC_CD8density_ModPathol2019": "snapshot_density",  # IHC

    # q_Treg_T_in
    "q_Treg_T_in_PDAC_Tang2014": "fraction_ratio",  # blood Treg fraction
    "q_Treg_T_in_extravasation_PDAC": "migration_assay",  # transwell
    "q_Treg_T_in_Tremblay2017_MRIcelltracking": "rate_direct",  # MRI tracking
    "q_Treg_T_in_Jiang2014_Liyanage2002": "snapshot_density",  # IHC

    # Single-parameter targets (not in multi-target tables but included for completeness)
    "N_IL2_CD4_division_destiny_Gett1998": "rate_direct",
    "N_IL2_CD8_division_generations_castro2012": "rate_direct",
    "k_psc_activation_apte1998": "rate_direct",
    "n_CD8_clones_Meng2023_PDAC": "snapshot_density",
}

MODALITY_LIST = ["rate_direct", "snapshot_density", "accumulated", "fraction_ratio", "migration_assay"]


# ── Process completeness annotations ──────────────────────────────────
#
# How many of the model's interacting processes are present in the assay?
#   full_system       = 3 — all processes active (in vivo tumor, clinical tissue)
#   partial_system    = 2 — some processes present (ex vivo TAMs, co-culture)
#   isolated_process  = 1 — only the target process (Boyden chamber, purified cells + stimulus)
#
# Encodes the biological fidelity gap between the assay and the model.

PROCESS_COMPLETENESS = {
    # k_C1_growth: clinical imaging of intact tumor growth → full
    "k_C1_growth_pdac_human_vdt_ahn2017": 3,
    "k_C1_growth_pdac_tumor_doubling_jang2015": 3,

    # k_CCL2_sec: in vitro cells secreting spontaneously → isolated; plasma → full
    "k_CCL2_sec_Steube1999_proxy": 1,
    "k_CCL2_sec_bcproxy_yoshimura2023": 1,
    "k_CCL2_sec_Fujita2010_PrSC": 1,
    "k_CCL2_sec_psc_michalski2008": 1,          # in vitro PSC culture
    "k_CCL2_sec_pdac_plasma_Nixon2013": 3,       # clinical plasma (full system)

    # k_M1_pol
    "k_M1_pol_repolarization_horhold2020": 1,    # purified BMDM + stimulus
    "k_M1_pol_Watkins2007_IL12_TAM_reprogramming": 2,  # TAMs from tumor → ex vivo
    "k_M1_pol_rp182_m2_to_m1_repolarization": 1,  # purified BMDM + drug
    "k_M1_pol_pdac_cd86_cd163_gu2023": 3,           # clinical tissue IHC ratio
    "k_M1_pol_steady_state_ratio_DLBCL2021": 3,   # clinical tissue (DLBCL)
    "k_M1_pol_pdac_m1m2ratio_DeSimoni2023": 3,    # clinical PDAC tissue IHC
    "k_M1_pol_tam_ratio_herwig2013": 3,            # clinical uveal melanoma tissue IHC
    "k_Mac_rec_humanPDAC_CD40_2021": 3,           # clinical tissue ratio

    # k_MDSC_rec
    "k_MDSC_rec_recruitment_pericyte_MDSC_Hong2015": 3,  # in vivo tumor model
    "k_MDSC_rec_PDAC_Porembka2012": 3,           # clinical tissue
    "k_MDSC_rec_oscc_ccl2_oo2022": 1,            # Boyden chamber, isolated chemotaxis
    "k_MDSC_rec_panc02_spleenexpansion_ghansah2013": 3,  # in vivo syngeneic tumor
    "k_MDSC_rec_pdac_trovato2019": 3,           # clinical PDAC (flow cytometry)
    "k_MDSC_rec_panc02_tnfr1_chopra2013": 3,    # in vivo syngeneic tumor IHC

    # k_Mac_rec / k_Mac_death: clinical IHC → full
    "k_Mac_rec_PDAC_TAM_recruitment_Chen2015": 3,
    "k_Mac_rec_PDAC_M1_recruitment_Gu2023": 3,

    # k_apsc_death: purified PSCs + drug → isolated; in vivo HSC → full
    "k_apsc_death_RA_Xiao2015": 1,
    "k_apsc_death_melatoninPSC_Estaras2021": 1,
    "k_apsc_death_hsc_apoptosis_issa2001": 3,    # in vivo rat biliary fibrosis resolution

    # q_CD8_T_in
    "q_CD8_T_in_extravasation_boissonnas2007": 2,  # intravital imaging in tumor, but adoptive transfer
    "q_CD8_T_in_yorty2007_sv11_brain_tumor": 3,    # in vivo tumor endpoint
    "q_CD8_T_in_PDAC_CD8density_ModPathol2019": 3,  # clinical IHC

    # q_Treg_T_in
    "q_Treg_T_in_PDAC_Tang2014": 3,               # clinical blood + tissue
    "q_Treg_T_in_extravasation_PDAC": 1,           # transwell migration assay
    "q_Treg_T_in_Tremblay2017_MRIcelltracking": 2, # in vivo but adoptive transfer
    "q_Treg_T_in_Jiang2014_Liyanage2002": 3,       # clinical IHC

    # Single-parameter targets
    "N_IL2_CD4_division_destiny_Gett1998": 1,
    "N_IL2_CD8_division_generations_castro2012": 3,
    "k_psc_activation_apte1998": 1,
    "n_CD8_clones_Meng2023_PDAC": 3,
}


# ── Indication distance annotations ──────────────────────────────────
#
# More granular than proxy/exact. How biologically close is the source
# to the target disease context?
#   3 = exact (PDAC for PDAC model)
#   2 = related (other GI, other adenocarcinoma, same cell type different context)
#   1 = distant (different cancer type entirely, e.g. OSCC, brain tumor, leukemia)
#   0 = non_disease (healthy tissue, generic physiology)

# ── Tumor tissue measurement ───────────────────────────────────────
#
# Is the measurement from actual tumor tissue (IHC, flow on digested
# tumor, in vivo tumor imaging)?  Or from a surrogate compartment
# (blood, spleen, conditioned media, Boyden chamber, purified cells)?
#
# Different from process_completeness: a measurement can be full_system=3
# (clinical blood) but not tumor tissue (it's systemic, not local).
# Different from in_vitro: a measurement can be in_vivo but still not
# from tumor tissue (spleen, blood).

TUMOR_TISSUE = {
    "k_C1_growth_pdac_human_vdt_ahn2017": 1,        # clinical imaging of tumor
    "k_C1_growth_pdac_tumor_doubling_jang2015": 1,   # clinical tumor growth
    "k_CCL2_sec_Steube1999_proxy": 0,                # conditioned media (in vitro)
    "k_CCL2_sec_bcproxy_yoshimura2023": 0,            # conditioned media (in vitro)
    "k_CCL2_sec_Fujita2010_PrSC": 0,                 # conditioned media (in vitro)
    "k_CCL2_sec_psc_michalski2008": 0,                # conditioned media (in vitro)
    "k_CCL2_sec_pdac_plasma_Nixon2013": 0,            # blood plasma (systemic, not tumor)
    "k_M1_pol_repolarization_horhold2020": 0,         # purified BMDM in vitro
    "k_M1_pol_Watkins2007_IL12_TAM_reprogramming": 0, # ex vivo TAM culture
    "k_M1_pol_rp182_m2_to_m1_repolarization": 0,     # purified BMDM in vitro
    "k_M1_pol_pdac_cd86_cd163_gu2023": 1,             # PDAC tissue IHC
    "k_M1_pol_steady_state_ratio_DLBCL2021": 1,      # DLBCL tissue biopsy
    "k_M1_pol_pdac_m1m2ratio_DeSimoni2023": 1,        # PDAC tissue IHC
    "k_M1_pol_tam_ratio_herwig2013": 1,               # uveal melanoma tissue
    "k_Mac_rec_humanPDAC_CD40_2021": 1,               # PDAC tissue IHC
    "k_MDSC_rec_recruitment_pericyte_MDSC_Hong2015": 1, # in vivo tumor tissue
    "k_MDSC_rec_PDAC_Porembka2012": 1,               # clinical PDAC tissue flow
    "k_MDSC_rec_oscc_ccl2_oo2022": 0,                # Boyden chamber (in vitro)
    "k_MDSC_rec_panc02_spleenexpansion_ghansah2013": 0, # spleen (systemic, not tumor)
    "k_MDSC_rec_pdac_trovato2019": 1,                # clinical PDAC tissue flow
    "k_MDSC_rec_panc02_tnfr1_chopra2013": 1,         # orthotopic tumor IHC
    "k_Mac_rec_PDAC_TAM_recruitment_Chen2015": 1,     # clinical PDAC tissue
    "k_Mac_rec_PDAC_M1_recruitment_Gu2023": 1,        # clinical PDAC tissue
    "k_apsc_death_RA_Xiao2015": 0,                   # purified PSCs in vitro
    "k_apsc_death_melatoninPSC_Estaras2021": 0,      # purified PSCs in vitro
    "k_apsc_death_hsc_apoptosis_issa2001": 1,         # in vivo liver tissue
    "q_CD8_T_in_extravasation_boissonnas2007": 1,     # intravital imaging of tumor
    "q_CD8_T_in_yorty2007_sv11_brain_tumor": 1,       # in vivo tumor endpoint
    "q_CD8_T_in_PDAC_CD8density_ModPathol2019": 1,    # clinical PDAC tissue IHC
    "q_Treg_T_in_PDAC_Tang2014": 0,                  # peripheral blood (not tumor tissue)
    "q_Treg_T_in_extravasation_PDAC": 0,              # transwell migration (in vitro)
    "q_Treg_T_in_Tremblay2017_MRIcelltracking": 1,   # in vivo tumor MRI
    "q_Treg_T_in_Jiang2014_Liyanage2002": 1,         # clinical tumor tissue IHC
    "N_IL2_CD4_division_destiny_Gett1998": 0,
    "N_IL2_CD8_division_generations_castro2012": 0,
    "k_psc_activation_apte1998": 0,
    "n_CD8_clones_Meng2023_PDAC": 1,
}


# ── Kinetic vs equilibrium measurement ─────────────────────────────
#
# Does the assay measure a DYNAMIC RATE (time-course, kinetic, turnover)
# or a STATIC EQUILIBRIUM state (snapshot density, fraction, ratio)?
#
# This captures a fundamental distinction: kinetic assays measure the
# process the parameter represents, while equilibrium assays measure
# the outcome and back-calculate the rate via a forward model.
# For polarization/trafficking parameters, kinetic and equilibrium
# measurements can give very different answers because the forward
# model assumptions (e.g., linear kinetics, steady state) introduce
# additional systematic error.

KINETIC_MEASUREMENT = {
    "k_C1_growth_pdac_human_vdt_ahn2017": 1,        # volume doubling time
    "k_C1_growth_pdac_tumor_doubling_jang2015": 1,   # tumor doubling
    "k_CCL2_sec_Steube1999_proxy": 1,                # accumulation over time (batch)
    "k_CCL2_sec_bcproxy_yoshimura2023": 1,            # accumulation over time (batch)
    "k_CCL2_sec_Fujita2010_PrSC": 1,                 # accumulation over time (batch)
    "k_CCL2_sec_psc_michalski2008": 1,                # accumulation over time (batch)
    "k_CCL2_sec_pdac_plasma_Nixon2013": 0,            # steady-state plasma level
    "k_M1_pol_repolarization_horhold2020": 1,         # time-course of repolarization
    "k_M1_pol_Watkins2007_IL12_TAM_reprogramming": 1, # kinetic reprogramming assay
    "k_M1_pol_rp182_m2_to_m1_repolarization": 1,     # kinetic: 30min drug exposure
    "k_M1_pol_pdac_cd86_cd163_gu2023": 0,             # equilibrium tissue ratio
    "k_M1_pol_steady_state_ratio_DLBCL2021": 0,      # equilibrium tissue ratio
    "k_M1_pol_pdac_m1m2ratio_DeSimoni2023": 0,        # equilibrium tissue ratio
    "k_M1_pol_tam_ratio_herwig2013": 0,               # equilibrium tissue ratio
    "k_Mac_rec_humanPDAC_CD40_2021": 0,               # equilibrium tissue ratio
    "k_MDSC_rec_recruitment_pericyte_MDSC_Hong2015": 0, # endpoint density (no kinetics)
    "k_MDSC_rec_PDAC_Porembka2012": 0,               # equilibrium fraction
    "k_MDSC_rec_oscc_ccl2_oo2022": 1,                # migration assay (kinetic: 9h)
    "k_MDSC_rec_panc02_spleenexpansion_ghansah2013": 0, # endpoint spleen fraction
    "k_MDSC_rec_pdac_trovato2019": 0,                # equilibrium fraction
    "k_MDSC_rec_panc02_tnfr1_chopra2013": 0,         # endpoint density
    "k_Mac_rec_PDAC_TAM_recruitment_Chen2015": 0,     # equilibrium density
    "k_Mac_rec_PDAC_M1_recruitment_Gu2023": 0,        # equilibrium density
    "k_apsc_death_RA_Xiao2015": 1,                   # time-course viability
    "k_apsc_death_melatoninPSC_Estaras2021": 1,      # time-course viability
    "k_apsc_death_hsc_apoptosis_issa2001": 1,         # time-course in vivo
    "q_CD8_T_in_extravasation_boissonnas2007": 1,     # intravital imaging time-course
    "q_CD8_T_in_yorty2007_sv11_brain_tumor": 0,       # endpoint counts
    "q_CD8_T_in_PDAC_CD8density_ModPathol2019": 0,    # equilibrium density
    "q_Treg_T_in_PDAC_Tang2014": 0,                  # equilibrium blood fraction
    "q_Treg_T_in_extravasation_PDAC": 1,              # transwell migration (kinetic)
    "q_Treg_T_in_Tremblay2017_MRIcelltracking": 1,   # MRI tracking over time
    "q_Treg_T_in_Jiang2014_Liyanage2002": 0,         # equilibrium tissue IHC
    "N_IL2_CD4_division_destiny_Gett1998": 1,
    "N_IL2_CD8_division_generations_castro2012": 1,
    "k_psc_activation_apte1998": 1,
    "n_CD8_clones_Meng2023_PDAC": 0,
}


INDICATION_DISTANCE = {
    "k_C1_growth_pdac_human_vdt_ahn2017": 3,
    "k_C1_growth_pdac_tumor_doubling_jang2015": 3,
    "k_CCL2_sec_Steube1999_proxy": 1,       # monocytic leukemia cell line
    "k_CCL2_sec_bcproxy_yoshimura2023": 2,   # breast cancer (adenocarcinoma)
    "k_CCL2_sec_Fujita2010_PrSC": 2,        # pancreatic stellate cells, relevant stroma
    "k_CCL2_sec_psc_michalski2008": 2,       # chronic pancreatitis PSCs (related)
    "k_CCL2_sec_pdac_plasma_Nixon2013": 3,   # advanced PDAC clinical plasma
    "k_M1_pol_repolarization_horhold2020": 1,  # generic BMDM, no tumor context
    "k_M1_pol_Watkins2007_IL12_TAM_reprogramming": 2,  # mouse tumor TAMs, not PDAC
    "k_M1_pol_rp182_m2_to_m1_repolarization": 2,  # mouse tumor-derived M2
    "k_M1_pol_pdac_cd86_cd163_gu2023": 3,       # human PDAC clinical tissue
    "k_M1_pol_steady_state_ratio_DLBCL2021": 1,  # DLBCL, distant indication
    "k_M1_pol_pdac_m1m2ratio_DeSimoni2023": 3,   # human PDAC clinical tissue
    "k_M1_pol_tam_ratio_herwig2013": 1,           # uveal melanoma, distant
    "k_Mac_rec_humanPDAC_CD40_2021": 3,       # human PDAC
    "k_MDSC_rec_recruitment_pericyte_MDSC_Hong2015": 2,  # mouse pancreatic tumor model
    "k_MDSC_rec_PDAC_Porembka2012": 3,       # human PDAC
    "k_MDSC_rec_oscc_ccl2_oo2022": 1,        # OSCC, distant indication
    "k_MDSC_rec_panc02_spleenexpansion_ghansah2013": 2,  # mouse Panc02 syngeneic
    "k_MDSC_rec_pdac_trovato2019": 3,       # human PDAC clinical
    "k_MDSC_rec_panc02_tnfr1_chopra2013": 2,  # mouse Panc02 syngeneic
    "k_Mac_rec_PDAC_TAM_recruitment_Chen2015": 3,
    "k_Mac_rec_PDAC_M1_recruitment_Gu2023": 3,
    "k_apsc_death_RA_Xiao2015": 2,           # generic PSCs, related
    "k_apsc_death_melatoninPSC_Estaras2021": 2,  # generic PSCs, related
    "k_apsc_death_hsc_apoptosis_issa2001": 1,    # rat hepatic stellate cells, distant
    "q_CD8_T_in_extravasation_boissonnas2007": 2,  # mouse tumor, not PDAC
    "q_CD8_T_in_yorty2007_sv11_brain_tumor": 1,  # brain tumor, distant
    "q_CD8_T_in_PDAC_CD8density_ModPathol2019": 3,
    "q_Treg_T_in_PDAC_Tang2014": 3,
    "q_Treg_T_in_extravasation_PDAC": 3,     # human PDAC-derived
    "q_Treg_T_in_Tremblay2017_MRIcelltracking": 1,  # mouse brain tumor
    "q_Treg_T_in_Jiang2014_Liyanage2002": 3,
    "N_IL2_CD4_division_destiny_Gett1998": 1,
    "N_IL2_CD8_division_generations_castro2012": 1,
    "k_psc_activation_apte1998": 2,
    "n_CD8_clones_Meng2023_PDAC": 3,
}


# ── Helpers ────────────────────────────────────────────────────────────

def shorten(tid):
    for i, p in enumerate(tid.split("_")):
        if p[0].isupper() and not p.startswith("PDAC"):
            return "_".join(tid.split("_")[i:])
    return tid[-30:]


def get_covariates(tid):
    """Extract a rich set of covariates from YAML metadata."""
    m = target_meta.get(tid, {})
    ctx = m.get("experimental_context", {}) or {}
    rel = m.get("source_relevance", {}) or {}
    cal = m.get("calibration", {}) or {}
    fm = cal.get("forward_model", {}) or {}
    em = cal.get("error_model", []) or []
    params = cal.get("parameters", []) or []

    sp = str(ctx.get("species", "")).lower()
    sys = str(ctx.get("system", "")).lower()
    qual = str(rel.get("source_quality", "")).lower()
    fm_type = str(fm.get("type", "")).lower()
    perturb = str(rel.get("perturbation_type", "")).lower()

    uncert = float(rel.get("estimated_translation_uncertainty_fold", 1.0) or 1.0)

    sample_size = 1
    if em and isinstance(em, list) and len(em) > 0:
        ss = em[0].get("sample_size", 1)
        if ss and ss > 0:
            sample_size = int(ss)

    modality = MODALITY.get(tid, "unknown")
    completeness = PROCESS_COMPLETENESS.get(tid, 2)
    ind_dist = INDICATION_DISTANCE.get(tid, 2)
    tumor_tissue = TUMOR_TISSUE.get(tid, 0)
    kinetic = KINETIC_MEASUREMENT.get(tid, 0)

    # TME compatibility from YAML (high=3, moderate=2, low=1)
    tme_raw = str(rel.get("tme_compatibility", "")).lower()
    tme_compat = {"high": 3, "moderate": 2, "low": 1}.get(tme_raw, 2)

    # Whether any input is inferred (vs all direct_measurement)
    inputs = m.get("inputs", []) or []
    has_inferred = any(
        str(inp.get("input_type", "")).lower() == "inferred_estimate"
        for inp in inputs
    )

    # Perturbation type from YAML (already populated)
    is_pharmacological = 1 if "pharmacol" in perturb else 0
    is_pathological = 1 if "pathological" in perturb else 0

    covs = {
        # ── Study design (round 1) ──
        "non_human": 0 if "human" in sp else 1,
        "in_vitro": 1 if "vitro" in sys else 0,
        "clinical": 1 if "primary_human_clinical" in qual else 0,

        # ── Forward model structure ──
        "structured_fm": 1 if fm_type.startswith("steady_state") else 0,

        # ── Continuous (round 1) ──
        "log_uncert": math.log10(uncert),
        "log_n": math.log10(max(sample_size, 1)),
        "small_n": 1 if sample_size <= 3 else 0,

        # ── Measurement modality (round 2, one-hot, rate_direct as reference) ──
        "mod_snapshot": 1 if modality == "snapshot_density" else 0,
        "mod_accumulated": 1 if modality == "accumulated" else 0,
        "mod_fraction": 1 if modality == "fraction_ratio" else 0,
        "mod_migration": 1 if modality == "migration_assay" else 0,

        # ── Round 3: deeper covariates ──
        # Perturbation context (from YAML perturbation_type)
        "pharmacological": is_pharmacological,
        "pathological": is_pathological,

        # Process completeness (1=isolated, 2=partial, 3=full)
        "completeness": completeness,
        "isolated_process": 1 if completeness == 1 else 0,
        "full_system": 1 if completeness == 3 else 0,

        # Indication distance (1=distant, 2=related, 3=exact)
        "ind_distance": ind_dist,
        "ind_distant": 1 if ind_dist == 1 else 0,
        "ind_exact": 1 if ind_dist == 3 else 0,

        # ── Round 4: new covariates ──
        # Tumor tissue (binary): measurement from tumor tissue vs surrogate
        "tumor_tissue": tumor_tissue,
        # Kinetic rate (binary): dynamic assay vs equilibrium snapshot
        "kinetic_rate": kinetic,
        # TME compatibility (ordinal 1-3, from YAML)
        "tme_compat": tme_compat,
        "tme_high": 1 if tme_compat == 3 else 0,
        "tme_low": 1 if tme_compat == 1 else 0,
        # Has inferred inputs (binary)
        "has_inferred": 1 if has_inferred else 0,

        # ── Raw labels (for display) ──
        "_modality": modality,
        "_perturbation": perturb,
        "_completeness": completeness,
        "_ind_distance": ind_dist,
    }

    # ── Interactions ──
    covs["invitro_x_migration"] = covs["in_vitro"] * covs["mod_migration"]
    covs["invitro_x_snapshot"] = covs["in_vitro"] * covs["mod_snapshot"]
    covs["invitro_x_fraction"] = covs["in_vitro"] * covs["mod_fraction"]
    covs["nonhuman_x_smalln"] = covs["non_human"] * covs["small_n"]
    covs["pharm_x_isolated"] = covs["pharmacological"] * covs["isolated_process"]
    covs["kinetic_x_pharm"] = covs["kinetic_rate"] * covs["pharmacological"]
    covs["tumor_x_exact"] = covs["tumor_tissue"] * covs["ind_exact"]
    covs["equil_x_tissue"] = (1 - covs["kinetic_rate"]) * covs["tumor_tissue"]

    return covs


def dersimonian_laird(y, s):
    """Random-effects meta-analysis. Returns (mu, se, tau2, I2)."""
    y, s = np.asarray(y, dtype=float), np.asarray(s, dtype=float)
    v = s**2
    w = 1.0 / v
    mu_fe = np.sum(w * y) / np.sum(w)
    Q = np.sum(w * (y - mu_fe) ** 2)
    df = len(y) - 1
    C = np.sum(w) - np.sum(w**2) / np.sum(w)
    tau2 = max(0.0, (Q - df) / C) if C > 0 else 0.0
    I2 = max(0.0, (Q - df) / Q) if Q > 0 else 0.0
    w_re = 1.0 / (v + tau2)
    mu_re = np.sum(w_re * y) / np.sum(w_re)
    se_re = 1.0 / np.sqrt(np.sum(w_re))
    return mu_re, se_re, tau2, I2


def pooled_wls(obs, param_list, param_idx, tau2_map, cov_names):
    """Fit pooled WLS: y = param_intercepts + beta * covariates.

    Returns dict with beta, se_beta, resid, r2, df, or None if singular.
    """
    n_obs = len(obs)
    n_params = len(param_list)

    y = np.array([o["lm"] for o in obs])
    w = np.array([1.0 / (o["ls"]**2 + tau2_map[o["param"]]) for o in obs])

    X_param = np.zeros((n_obs, n_params))
    for i, o in enumerate(obs):
        X_param[i, param_idx[o["param"]]] = 1.0

    X_cov = np.array([[o[c] for c in cov_names] for o in obs], dtype=float)

    # Check covariate variance
    for j, c in enumerate(cov_names):
        if np.std(X_cov[:, j]) < 1e-10:
            return None  # zero variance

    X = np.column_stack([X_param, X_cov])

    W = np.diag(w)
    XtWX = X.T @ W @ X

    rank = np.linalg.matrix_rank(XtWX)
    if rank < XtWX.shape[0]:
        return None

    b = np.linalg.solve(XtWX, X.T @ W @ y)
    se = np.sqrt(np.diag(np.linalg.inv(XtWX)))
    resid = y - X @ b

    beta = b[n_params:]
    se_beta = se[n_params:]

    wss_full = float(np.sum(w * resid**2))

    # Null model (intercepts only)
    XtWX0 = X_param.T @ W @ X_param
    b0 = np.linalg.solve(XtWX0, X_param.T @ W @ y)
    resid0 = y - X_param @ b0
    wss_null = float(np.sum(w * resid0**2))

    r2 = 1.0 - wss_full / wss_null if wss_null > 0 else 0.0

    return {
        "beta": beta,
        "se_beta": se_beta,
        "resid": resid,
        "resid0": resid0,
        "wss": wss_full,
        "wss_null": wss_null,
        "r2": r2,
        "df": n_obs - n_params - len(cov_names),
        "mu_hat": b[:n_params],
    }


# ── Build per-parameter tables ─────────────────────────────────────────

param_targets = defaultdict(list)
for tid, params in single_results.items():
    for p in params:
        param_targets[p].append(tid)

tables = {}
for param, tids in param_targets.items():
    rows = []
    for tid in tids:
        sr = single_results[tid][param]
        med, lo, hi = sr["median"], sr["ci_05"], sr["ci_95"]
        if med > 0 and lo > 0 and hi > 0:
            lm = np.log10(med)
            ls = (np.log10(hi) - np.log10(lo)) / 3.29
            rows.append({"tid": tid, "label": shorten(tid), "param": param,
                         "lm": lm, "ls": ls, **get_covariates(tid)})
    if len(rows) >= 2:
        tables[param] = rows


# Flatten and build common structures
obs = []
for param in sorted(tables):
    for r in tables[param]:
        obs.append(r)

n_obs = len(obs)
param_list = sorted(tables.keys())
param_idx = {p: i for i, p in enumerate(param_list)}
n_params = len(param_list)

tau2_map = {}
for param in param_list:
    rows = tables[param]
    _, _, tau2, _ = dersimonian_laird(
        [r["lm"] for r in rows], [r["ls"] for r in rows]
    )
    tau2_map[param] = tau2


# ══════════════════════════════════════════════════════════════════════
# PART 1: Per-parameter DL meta-analysis
# ══════════════════════════════════════════════════════════════════════

print("=" * 70)
print("PART 1: Per-parameter DL meta-analysis")
print("=" * 70)

for param in sorted(tables):
    rows = tables[param]
    y = np.array([r["lm"] for r in rows])
    s = np.array([r["ls"] for r in rows])
    mu, se, tau2, I2 = dersimonian_laird(y, s)

    print(f"\n{'─'*70}")
    print(f"{param}  ({len(rows)} targets)  pooled={10**mu:.4g}  tau={tau2**.5:.2f}  I²={I2:.0%}")
    print(f"{'─'*70}")
    for r in rows:
        mod = r["_modality"]
        flags = []
        if r["pharmacological"]: flags.append("PHARM")
        if r["isolated_process"]: flags.append("isol")
        elif r["_completeness"] == 2: flags.append("part")
        else: flags.append("full")
        flags.append(f"ind={r['_ind_distance']}")
        if r["small_n"]: flags.append("n<=3")
        tag = f"{mod} ({', '.join(flags)})"
        print(f"  {r['label']:42s} {10**r['lm']:>10.4g}  (sd={r['ls']:.2f})  [{tag}]")


# ══════════════════════════════════════════════════════════════════════
# PART 2: Univariate covariate screening (pooled model)
# ══════════════════════════════════════════════════════════════════════

SCREEN_COVS = [
    # Study design (round 1)
    "non_human", "in_vitro", "clinical", "small_n", "log_n", "log_uncert",
    # Forward model
    "structured_fm",
    # Measurement modality (round 2, vs rate_direct reference)
    "mod_snapshot", "mod_accumulated", "mod_fraction", "mod_migration",
    # Deeper covariates (round 3)
    "pharmacological", "pathological",
    "isolated_process", "full_system", "completeness",
    "ind_distant", "ind_exact", "ind_distance",
    # Round 4: new covariates
    "tumor_tissue", "kinetic_rate", "tme_compat", "tme_high", "tme_low",
    "has_inferred",
    # Interactions
    "invitro_x_migration", "invitro_x_fraction",
    "nonhuman_x_smalln", "pharm_x_isolated",
    "kinetic_x_pharm", "tumor_x_exact", "equil_x_tissue",
]

print("\n\n" + "=" * 70)
print("PART 2: Univariate covariate screening")
print("=" * 70)

print(f"\n{n_obs} observations, {n_params} parameter intercepts")

# Modality distribution
print(f"\nMeasurement modality distribution:")
from collections import Counter
mod_counts = Counter(o["_modality"] for o in obs)
for mod in MODALITY_LIST:
    print(f"  {mod:<20s}  {mod_counts.get(mod, 0):>2d}/{n_obs}")

# Covariate distribution
print(f"\nCovariate distribution:")
for cov in SCREEN_COVS:
    vals = [o[cov] for o in obs]
    if all(v in (0, 1, 0.0, 1.0) for v in vals):
        n1 = sum(1 for v in vals if v == 1)
        print(f"  {cov:<25s}  {n1:>2d}/{n_obs} = {n1/n_obs:.0%}")
    else:
        print(f"  {cov:<25s}  mean={np.mean(vals):.2f}  range=[{min(vals):.2f}, {max(vals):.2f}]")

# Univariate screening
print(f"\nUnivariate pooled regressions (each covariate alone):")
print(f"  {'Covariate':<25s}  {'beta':>7s}  {'SE':>6s}  {'fold':>7s}  {'|z|':>5s}  {'R²':>6s}  {'note'}")
print(f"  {'─'*25}  {'─'*7}  {'─'*6}  {'─'*7}  {'─'*5}  {'─'*6}  {'─'*20}")

screen_results = {}
for cov in SCREEN_COVS:
    result = pooled_wls(obs, param_list, param_idx, tau2_map, [cov])
    if result is None:
        print(f"  {cov:<25s}  {'--- zero var / singular ---':>40s}")
        continue

    b = result["beta"][0]
    se = result["se_beta"][0]
    z = abs(b / se) if se > 0 else 0
    fold = 10 ** b
    note = ""
    if z > 2: note = " ** sig (|z|>2)"
    elif z > 1.5: note = " * marginal"
    print(f"  {cov:<25s}  {b:+.3f}  {se:.3f}  {fold:>6.2g}x  {z:>4.1f}  {result['r2']:>5.1%}  {note}")
    screen_results[cov] = {"beta": b, "se": se, "z": z, "r2": result["r2"]}

# Rank by R²
print(f"\nRanked by R²:")
for cov, res in sorted(screen_results.items(), key=lambda x: -x[1]["r2"]):
    bar = "#" * int(res["r2"] * 100)
    print(f"  {cov:<25s}  {res['r2']:>5.1%}  {bar}")


# ══════════════════════════════════════════════════════════════════════
# PART 3: Multivariate model comparison
# ══════════════════════════════════════════════════════════════════════

print("\n\n" + "=" * 70)
print("PART 3: Multivariate models")
print("=" * 70)

combos = [
    # ── Round 1 baselines ──
    ("non_human + in_vitro", ["non_human", "in_vitro"]),
    ("small_n alone", ["small_n"]),
    ("log_n alone", ["log_n"]),

    # ── Round 2: modality ──
    ("modality + small_n", ["mod_snapshot", "mod_fraction", "mod_migration", "small_n"]),
    ("modality + log_n", ["mod_snapshot", "mod_fraction", "mod_migration", "log_n"]),

    # ── Round 3: deeper covariates ──
    ("pharmacological alone", ["pharmacological"]),
    ("isolated_process alone", ["isolated_process"]),
    ("completeness alone", ["completeness"]),
    ("ind_distance alone", ["ind_distance"]),
    ("ind_distant alone", ["ind_distant"]),
    ("pharm_x_isolated alone", ["pharm_x_isolated"]),

    # ── Round 3 combos ──
    ("pharmacological + completeness", ["pharmacological", "completeness"]),
    ("pharmacological + isolated_process", ["pharmacological", "isolated_process"]),
    ("pharmacological + ind_distance", ["pharmacological", "ind_distance"]),
    ("completeness + ind_distance", ["completeness", "ind_distance"]),
    ("completeness + small_n", ["completeness", "small_n"]),
    ("pharmacological + small_n", ["pharmacological", "small_n"]),
    ("isolated_process + small_n", ["isolated_process", "small_n"]),

    # ── 3-covariate models ──
    ("pharm + completeness + small_n", ["pharmacological", "completeness", "small_n"]),
    ("pharm + completeness + ind_distance", ["pharmacological", "completeness", "ind_distance"]),
    ("pharm + isolated + ind_distant", ["pharmacological", "isolated_process", "ind_distant"]),
    ("pharm + isolated + small_n", ["pharmacological", "isolated_process", "small_n"]),
    ("pharm + isolated + log_n", ["pharmacological", "isolated_process", "log_n"]),
    ("completeness + ind_distance + small_n", ["completeness", "ind_distance", "small_n"]),
    ("completeness + ind_distance + log_n", ["completeness", "ind_distance", "log_n"]),

    # ── 4-covariate kitchen sink ──
    ("pharm + completeness + ind_dist + small_n", ["pharmacological", "completeness", "ind_distance", "small_n"]),
    ("pharm + completeness + ind_dist + log_n", ["pharmacological", "completeness", "ind_distance", "log_n"]),
    ("pharm + isolated + ind_distant + small_n", ["pharmacological", "isolated_process", "ind_distant", "small_n"]),

    # ── Cross-comparison: best round 2 vs best round 3 ──
    ("modality + pharmacological", ["mod_snapshot", "mod_fraction", "mod_migration", "pharmacological"]),
    ("modality + completeness", ["mod_snapshot", "mod_fraction", "mod_migration", "completeness"]),
    ("modality + pharm + completeness", ["mod_snapshot", "mod_fraction", "mod_migration", "pharmacological", "completeness"]),

    # ── Round 4: new covariates ──
    ("tumor_tissue alone", ["tumor_tissue"]),
    ("kinetic_rate alone", ["kinetic_rate"]),
    ("tme_compat alone", ["tme_compat"]),
    ("tumor_tissue + ind_distant", ["tumor_tissue", "ind_distant"]),
    ("kinetic_rate + ind_distant", ["kinetic_rate", "ind_distant"]),
    ("kinetic_rate + small_n", ["kinetic_rate", "small_n"]),
    ("tumor_tissue + kinetic_rate", ["tumor_tissue", "kinetic_rate"]),
    ("tumor_tissue + kinetic_rate + ind_distant", ["tumor_tissue", "kinetic_rate", "ind_distant"]),
    ("tumor_tissue + kinetic_rate + small_n", ["tumor_tissue", "kinetic_rate", "small_n"]),
    ("tumor_tissue + kinetic_rate + ind_distant + small_n", ["tumor_tissue", "kinetic_rate", "ind_distant", "small_n"]),
    ("kinetic_rate + pharm + ind_distant + small_n", ["kinetic_rate", "pharmacological", "ind_distant", "small_n"]),
    ("tumor_tissue + tme_compat + ind_distant", ["tumor_tissue", "tme_compat", "ind_distant"]),
    ("equil_x_tissue + ind_distant + small_n", ["equil_x_tissue", "ind_distant", "small_n"]),
    ("kinetic_x_pharm + ind_distant + small_n", ["kinetic_x_pharm", "ind_distant", "small_n"]),
]

print(f"\n  {'Model':<42s}  {'R²':>6s}  {'df':>3s}  {'coefficients'}")
print(f"  {'─'*42}  {'─'*6}  {'─'*3}  {'─'*50}")

best_r2 = 0
best_name = ""
for name, covs in combos:
    result = pooled_wls(obs, param_list, param_idx, tau2_map, covs)
    if result is None:
        print(f"  {name:<42s}  {'singular / zero var':>20s}")
        continue

    coef_parts = []
    for i, c in enumerate(covs):
        b = result["beta"][i]
        se = result["se_beta"][i]
        z = abs(b/se) if se > 0 else 0
        star = "*" if z > 2 else "~" if z > 1.5 else ""
        coef_parts.append(f"{c}={b:+.2f}({se:.2f}){star}")
    coef_str = "  ".join(coef_parts)
    marker = " <-- BEST" if result["r2"] > best_r2 else ""
    print(f"  {name:<42s}  {result['r2']:>5.1%}  {result['df']:>3d}  {coef_str}{marker}")
    if result["r2"] > best_r2:
        best_r2 = result["r2"]
        best_name = name


# ══════════════════════════════════════════════════════════════════════
# PART 4: Detailed best model
# ══════════════════════════════════════════════════════════════════════

print("\n\n" + "=" * 70)
print(f"PART 4: Best model details")
print("=" * 70)

# Re-fit the best few and show residuals
for name, covs in combos:
    result = pooled_wls(obs, param_list, param_idx, tau2_map, covs)
    if result is None or result["r2"] < best_r2 * 0.8:
        continue

    print(f"\n{'─'*70}")
    print(f"Model: {name}  (R²={result['r2']:.1%}, df={result['df']})")
    print(f"{'─'*70}")

    print(f"\n  Coefficients:")
    for i, c in enumerate(covs):
        b = result["beta"][i]
        se = result["se_beta"][i]
        z = abs(b/se) if se > 0 else 0
        fold = 10 ** b
        sig = "**" if z > 2 else "*" if z > 1.5 else ""
        print(f"    {c:<25s}  {b:+.3f} (SE {se:.3f})  {fold:.2g}x  |z|={z:.1f} {sig}")

    print(f"\n  Largest residuals:")
    order = np.argsort(-np.abs(result["resid"]))
    for idx in order[:8]:
        o = obs[idx]
        r = result["resid"][idx]
        r0 = result["resid0"][idx]
        print(f"    {o['label']:42s}  before={r0:+.2f}  after={r:+.2f}  [{o['param']}] {o['_modality']}")

    print(f"\n  Residual I² by parameter:")
    print(f"    {'Parameter':<25s}  {'I² before':>9s}  {'I² after':>9s}  {'change':>8s}")
    for param in param_list:
        rows = tables[param]
        y_p = np.array([r["lm"] for r in rows])
        s_p = np.array([r["ls"] for r in rows])
        _, _, _, I2_before = dersimonian_laird(y_p, s_p)

        mask = [i for i, o in enumerate(obs) if o["param"] == param]
        r_p = result["resid"][mask]
        w_p = 1.0 / (s_p ** 2)
        Q_after = float(np.sum(w_p * r_p**2))
        df = len(r_p) - 1
        I2_after = max(0, (Q_after - df) / Q_after) if Q_after > df and df > 0 else 0.0

        delta = I2_after - I2_before
        marker = " <<" if delta < -0.2 else ""
        print(f"    {param:<25s}  {I2_before:>8.0%}  {I2_after:>8.0%}  {delta:>+7.0%}{marker}")


# ══════════════════════════════════════════════════════════════════════
# PART 5: Per-target covariate table
# ══════════════════════════════════════════════════════════════════════

print("\n\n" + "=" * 70)
print("PART 5: Per-target covariate summary")
print("=" * 70)

print(f"\n  {'target':42s} {'param':18s} {'modality':15s} {'perturb':15s} {'cpl':>3s} {'ind':>3s} {'sn':>3s} {'ph':>3s} {'ln':>5s}")
print(f"  {'─'*42} {'─'*18} {'─'*15} {'─'*15} {'─'*3} {'─'*3} {'─'*3} {'─'*3} {'─'*5}")
for o in obs:
    print(f"  {o['label']:42s} {o['param']:18s} {o['_modality']:15s} {o['_perturbation']:15s}"
          f" {o['_completeness']:>3d} {o['_ind_distance']:>3d}"
          f" {o['small_n']:>3d} {o['pharmacological']:>3d}"
          f" {o['log_n']:>5.2f}")

print()


# ══════════════════════════════════════════════════════════════════════
# PART 6: Hierarchical model — parameter-specific covariate slopes
# ══════════════════════════════════════════════════════════════════════
#
# The shared-beta model forces every parameter to respond identically to
# a covariate.  This is wrong for structured_fm (opposite direction for
# k_M1_pol vs k_MDSC_rec) and may be wrong for pharmacological.
#
# Here we allow selected covariates to have parameter-specific slopes
# (= interaction terms) while keeping others shared.

print("\n\n" + "=" * 70)
print("PART 6: Hierarchical model (parameter-specific slopes)")
print("=" * 70)


def fit_hierarchical(obs, param_list, param_idx, tau2_map,
                     shared_covs, specific_covs):
    """WLS with parameter-specific slopes for selected covariates.

    shared_covs: covariates with a single pooled beta
    specific_covs: covariates with per-parameter beta_j (only for
        parameters that have >=2 targets AND covariate variance)

    Returns dict with r2, r2_adj, parameter-specific slopes, etc.
    """
    n_obs = len(obs)
    n_params = len(param_list)

    y = np.array([o["lm"] for o in obs])
    w = np.array([1.0 / (o["ls"]**2 + tau2_map[o["param"]]) for o in obs])

    # Parameter intercepts
    X_param = np.zeros((n_obs, n_params))
    for i, o in enumerate(obs):
        X_param[i, param_idx[o["param"]]] = 1.0

    # Shared covariate columns
    X_shared = (np.array([[o[c] for c in shared_covs] for o in obs], dtype=float)
                if shared_covs else np.zeros((n_obs, 0)))

    # Parameter-specific covariate columns (interaction terms)
    spec_labels = []
    spec_cols = []
    for c in specific_covs:
        for p in param_list:
            mask = [i for i, o in enumerate(obs) if o["param"] == p]
            vals = [obs[i][c] for i in mask]
            if len(mask) >= 2 and len(set(vals)) > 1:
                col = np.zeros(n_obs)
                for i in mask:
                    col[i] = obs[i][c]
                spec_cols.append(col)
                spec_labels.append(f"{c}|{p}")

    X_spec = (np.column_stack(spec_cols) if spec_cols
              else np.zeros((n_obs, 0)))

    X = np.column_stack([X_param, X_shared, X_spec])

    W = np.diag(w)
    XtWX = X.T @ W @ X
    if np.linalg.matrix_rank(XtWX) < X.shape[1]:
        return None

    b = np.linalg.solve(XtWX, X.T @ W @ y)
    se = np.sqrt(np.diag(np.linalg.inv(XtWX)))
    resid = y - X @ b

    wss_full = float(np.sum(w * resid**2))

    # Null model (intercepts only)
    XtWX0 = X_param.T @ W @ X_param
    b0 = np.linalg.solve(XtWX0, X_param.T @ W @ y)
    resid0 = y - X_param @ b0
    wss_null = float(np.sum(w * resid0**2))

    r2 = 1.0 - wss_full / wss_null if wss_null > 0 else 0.0
    n_shared = len(shared_covs) if shared_covs else 0
    n_cov = n_shared + len(spec_cols)
    df = n_obs - n_params - n_cov
    r2_adj = 1.0 - (1.0 - r2) * (n_obs - n_params) / df if df > 0 else 0.0

    return {
        "r2": r2, "r2_adj": r2_adj, "df": df, "n_cov": n_cov,
        "resid": resid, "resid0": resid0,
        "beta_shared": b[n_params:n_params + n_shared],
        "se_shared": se[n_params:n_params + n_shared],
        "beta_spec": b[n_params + n_shared:],
        "se_spec": se[n_params + n_shared:],
        "spec_labels": spec_labels,
        "shared_covs": shared_covs,
        "wss_full": wss_full, "wss_null": wss_null,
    }


# ── 6A: Within-parameter slope estimates ────────────────────────────

KEY_COVS = ["structured_fm", "pharmacological", "ind_distant", "small_n",
            "tumor_tissue", "kinetic_rate", "tme_compat"]

print(f"\n── 6A: Within-parameter slope estimates ──")

param_slopes = {}  # {cov: {param: (beta, se, n_targets)}}

for cov in KEY_COVS:
    param_slopes[cov] = {}
    for param in param_list:
        rows = tables[param]
        n_t = len(rows)
        x = np.array([r[cov] for r in rows])
        y_p = np.array([r["lm"] for r in rows])
        s_p = np.array([r["ls"] for r in rows])
        w_p = 1.0 / (s_p**2 + tau2_map[param])

        if n_t < 2 or np.std(x) < 1e-10:
            continue

        # Simple WLS: y = a + b*x
        X_p = np.column_stack([np.ones(n_t), x])
        W_p = np.diag(w_p)
        XtWX_p = X_p.T @ W_p @ X_p
        if np.linalg.matrix_rank(XtWX_p) < 2:
            continue
        b_p = np.linalg.solve(XtWX_p, X_p.T @ W_p @ y_p)
        se_p = np.sqrt(np.diag(np.linalg.inv(XtWX_p)))
        param_slopes[cov][param] = (b_p[1], se_p[1], n_t)

for cov in KEY_COVS:
    slopes = param_slopes[cov]
    if not slopes:
        continue
    print(f"\n  {cov}:")
    print(f"    {'Parameter':<20s}  {'beta':>7s}  {'SE':>6s}  {'fold':>7s}  {'|z|':>5s}  {'n':>3s}")
    for param in sorted(slopes):
        beta, se_b, n_t = slopes[param]
        z = abs(beta / se_b) if se_b > 0 else 0
        fold = 10 ** beta
        sig = "**" if z > 2 else "*" if z > 1.5 else ""
        print(f"    {param:<20s}  {beta:+.3f}  {se_b:.3f}  {fold:>6.2g}x  {z:>4.1f}  {n_t:>3d}  {sig}")

    # Meta-analyze parameter-specific slopes via DL
    if len(slopes) >= 2:
        betas_arr = np.array([v[0] for v in slopes.values()])
        ses_arr = np.array([v[1] for v in slopes.values()])
        mu_b, se_mu, tau2_b, I2_b = dersimonian_laird(betas_arr, ses_arr)
        print(f"    ── Population mean: beta_bar={mu_b:+.3f} (SE {se_mu:.3f}), "
              f"tau_slope={tau2_b**.5:.2f}, I²_slopes={I2_b:.0%}")
        param_slopes[cov]["_pop"] = (mu_b, se_mu, tau2_b, I2_b)


# ── 6B: Shared vs parameter-specific R² comparison ─────────────────

print(f"\n\n── 6B: Shared-beta vs parameter-specific R² ──\n")

print(f"  {'Covariate':<20s}  {'Shared R²':>10s}  {'Spec R²':>8s}  "
      f"{'adj R²':>7s}  {'Gain':>6s}  {'#slopes':>7s}  {'df':>4s}")
print(f"  {'─'*20}  {'─'*10}  {'─'*8}  {'─'*7}  {'─'*6}  {'─'*7}  {'─'*4}")

for cov in KEY_COVS:
    r_shared = pooled_wls(obs, param_list, param_idx, tau2_map, [cov])
    r_spec = fit_hierarchical(obs, param_list, param_idx, tau2_map, [], [cov])

    if r_shared and r_spec:
        gain = r_spec["r2"] - r_shared["r2"]
        print(f"  {cov:<20s}  {r_shared['r2']:>9.1%}  {r_spec['r2']:>7.1%}  "
              f"{r_spec['r2_adj']:>6.1%}  {gain:>+5.1%}  "
              f"{r_spec['n_cov']:>7d}  {r_spec['df']:>4d}")
    elif r_shared:
        print(f"  {cov:<20s}  {r_shared['r2']:>9.1%}  {'singular':>7s}")


# ── 6C: Hierarchical model combinations ────────────────────────────

print(f"\n\n── 6C: Hierarchical model combinations ──\n")

hier_combos = [
    ("sfm specific only",
     [], ["structured_fm"]),
    ("sfm specific + ind_distant shared",
     ["ind_distant"], ["structured_fm"]),
    ("sfm specific + small_n shared",
     ["small_n"], ["structured_fm"]),
    ("sfm specific + ind_distant + small_n shared",
     ["ind_distant", "small_n"], ["structured_fm"]),
    ("sfm + pharm specific, ind_distant shared",
     ["ind_distant"], ["structured_fm", "pharmacological"]),
    ("sfm + pharm specific, ind_distant + small_n shared",
     ["ind_distant", "small_n"], ["structured_fm", "pharmacological"]),
    # ── With new covariates ──
    ("kinetic specific, ind_distant shared",
     ["ind_distant"], ["kinetic_rate"]),
    ("kinetic specific + ind_distant + small_n shared",
     ["ind_distant", "small_n"], ["kinetic_rate"]),
    ("kinetic + sfm specific, ind_distant shared",
     ["ind_distant"], ["kinetic_rate", "structured_fm"]),
    ("kinetic + sfm specific, ind_distant + small_n shared",
     ["ind_distant", "small_n"], ["kinetic_rate", "structured_fm"]),
    ("sfm specific, tumor_tissue + ind_distant shared",
     ["tumor_tissue", "ind_distant"], ["structured_fm"]),
    ("sfm specific, tumor_tissue + ind_distant + small_n",
     ["tumor_tissue", "ind_distant", "small_n"], ["structured_fm"]),
    ("sfm + pharm specific, tumor + ind_dist + small_n",
     ["tumor_tissue", "ind_distant", "small_n"], ["structured_fm", "pharmacological"]),
    ("kinetic + pharm specific, tumor + ind_distant",
     ["tumor_tissue", "ind_distant"], ["kinetic_rate", "pharmacological"]),
]

# Shared-beta baseline for comparison
r_baseline = pooled_wls(
    obs, param_list, param_idx, tau2_map,
    ["pharmacological", "isolated_process", "ind_distant", "small_n"],
)

print(f"  {'Model':<52s}  {'R²':>6s}  {'adj R²':>7s}  {'df':>4s}  {'#cov':>4s}")
print(f"  {'─'*52}  {'─'*6}  {'─'*7}  {'─'*4}  {'─'*4}")

if r_baseline:
    df_b = r_baseline["df"]
    adj_b = 1.0 - (1.0 - r_baseline["r2"]) * (n_obs - n_params) / df_b
    print(f"  {'[baseline] pharm+isol+ind_dist+small_n (shared)':<52s}  "
          f"{r_baseline['r2']:>5.1%}  {adj_b:>6.1%}  {df_b:>4d}  {'4':>4s}")

best_hier = None
for name, shared, specific in hier_combos:
    result = fit_hierarchical(
        obs, param_list, param_idx, tau2_map, shared, specific,
    )
    if result is None:
        print(f"  {name:<52s}  {'singular':>6s}")
        continue

    marker = ""
    if best_hier is None or result["r2_adj"] > best_hier["r2_adj"]:
        best_hier = result
        best_hier["name"] = name
        marker = " <-- BEST adj"

    print(f"  {name:<52s}  {result['r2']:>5.1%}  {result['r2_adj']:>6.1%}  "
          f"{result['df']:>4d}  {result['n_cov']:>4d}{marker}")


# ── 6D: Best hierarchical model details ────────────────────────────

if best_hier:
    print(f"\n\n── 6D: Best hierarchical model details ──")
    print(f"\nModel: {best_hier['name']}")
    print(f"R² = {best_hier['r2']:.1%}, adj R² = {best_hier['r2_adj']:.1%}, "
          f"df = {best_hier['df']}, #covariate params = {best_hier['n_cov']}")

    if best_hier["shared_covs"]:
        print(f"\n  Shared slopes:")
        for i, c in enumerate(best_hier["shared_covs"]):
            b_val = best_hier["beta_shared"][i]
            se_b = best_hier["se_shared"][i]
            z = abs(b_val / se_b) if se_b > 0 else 0
            fold = 10 ** b_val
            sig = "**" if z > 2 else "*" if z > 1.5 else ""
            print(f"    {c:<25s}  {b_val:+.3f} (SE {se_b:.3f})  {fold:.2g}x  |z|={z:.1f} {sig}")

    print(f"\n  Parameter-specific slopes:")
    print(f"    {'Label':<35s}  {'beta':>7s}  {'SE':>6s}  {'fold':>7s}  {'|z|':>5s}")
    for i, label in enumerate(best_hier["spec_labels"]):
        b_val = best_hier["beta_spec"][i]
        se_b = best_hier["se_spec"][i]
        z = abs(b_val / se_b) if se_b > 0 else 0
        fold = 10 ** b_val
        sig = "**" if z > 2 else "*" if z > 1.5 else ""
        print(f"    {label:<35s}  {b_val:+.3f}  {se_b:.3f}  {fold:>6.2g}x  {z:>4.1f}  {sig}")

    # Residual I² by parameter
    print(f"\n  Residual I² by parameter:")
    print(f"    {'Parameter':<20s}  {'I² raw':>7s}  {'I² shared':>10s}  "
          f"{'I² hier':>8s}  {'hier-raw':>9s}")
    for param in param_list:
        rows = tables[param]
        y_p = np.array([r["lm"] for r in rows])
        s_p = np.array([r["ls"] for r in rows])
        _, _, _, I2_raw = dersimonian_laird(y_p, s_p)

        mask = [i for i, o in enumerate(obs) if o["param"] == param]
        w_p = 1.0 / (s_p**2)
        df_p = len(mask) - 1

        # Shared-beta baseline
        if r_baseline:
            Q_sh = float(np.sum(w_p * r_baseline["resid"][mask]**2))
            I2_sh = max(0, (Q_sh - df_p) / Q_sh) if Q_sh > df_p and df_p > 0 else 0.0
        else:
            I2_sh = I2_raw

        # Hierarchical
        Q_h = float(np.sum(w_p * best_hier["resid"][mask]**2))
        I2_h = max(0, (Q_h - df_p) / Q_h) if Q_h > df_p and df_p > 0 else 0.0

        delta = I2_h - I2_raw
        marker = " <<" if delta < -0.20 else ""
        print(f"    {param:<20s}  {I2_raw:>6.0%}  {I2_sh:>9.0%}  "
              f"{I2_h:>7.0%}  {delta:>+8.0%}{marker}")

    # Largest residuals
    print(f"\n  Largest residuals:")
    order = np.argsort(-np.abs(best_hier["resid"]))
    for idx in order[:8]:
        o = obs[idx]
        r_h = best_hier["resid"][idx]
        r0 = best_hier["resid0"][idx]
        print(f"    {o['label']:42s}  null={r0:+.2f}  hier={r_h:+.2f}  [{o['param']}]")


# ── 6E: Empirical Bayes shrinkage of structured_fm slopes ──────────
#
# The parameter-specific slopes from 6D are unregularized. With few
# targets per parameter, they may be noisy.  EB shrinkage pulls each
# parameter's slope toward the population mean, with shrinkage
# proportional to that parameter's estimation uncertainty.

if "structured_fm" in param_slopes and "_pop" in param_slopes["structured_fm"]:
    print(f"\n\n── 6E: Empirical Bayes shrinkage (structured_fm) ──\n")

    mu_pop, _, tau2_pop, I2_pop = param_slopes["structured_fm"]["_pop"]
    print(f"  Population: beta_bar={mu_pop:+.3f} ({10**mu_pop:.2g}x), "
          f"tau_slope={tau2_pop**.5:.3f}, I²_slopes={I2_pop:.0%}")

    print(f"\n  {'Parameter':<20s}  {'Raw':>8s}  {'Shrunk':>8s}  "
          f"{'Shrinkage':>9s}  {'Fold':>7s}")
    for param in sorted(param_slopes["structured_fm"]):
        if param.startswith("_"):
            continue
        beta, se_b, n_t = param_slopes["structured_fm"][param]
        if tau2_pop > 0:
            prec_data = 1.0 / se_b**2
            prec_prior = 1.0 / tau2_pop
            beta_shrunk = (beta * prec_data + mu_pop * prec_prior) / (prec_data + prec_prior)
            shrinkage = prec_prior / (prec_data + prec_prior)
        else:
            beta_shrunk = beta
            shrinkage = 0.0

        print(f"  {param:<20s}  {beta:>+7.3f}  {beta_shrunk:>+7.3f}  "
              f"{shrinkage:>8.0%}  {10**beta_shrunk:>6.2g}x")

    # Refit with EB-shrunk slopes applied as offsets
    print(f"\n  EB-adjusted R²: subtract shrunk sfm effect, fit shared covariates on residual")

    y_orig = np.array([o["lm"] for o in obs], dtype=float)
    y_adj = y_orig.copy()
    for i, o in enumerate(obs):
        p = o["param"]
        if p in param_slopes["structured_fm"]:
            beta_raw, se_b, _ = param_slopes["structured_fm"][p]
            if tau2_pop > 0:
                prec_d = 1.0 / se_b**2
                prec_p = 1.0 / tau2_pop
                b_s = (beta_raw * prec_d + mu_pop * prec_p) / (prec_d + prec_p)
            else:
                b_s = beta_raw
            y_adj[i] -= b_s * o["structured_fm"]

    obs_adj = [dict(o, lm=y_adj[i]) for i, o in enumerate(obs)]

    # Compute original null WSS for consistent R²
    w_all = np.array([1.0 / (o["ls"]**2 + tau2_map[o["param"]]) for o in obs])
    X_int = np.zeros((n_obs, n_params))
    for ii, o in enumerate(obs):
        X_int[ii, param_idx[o["param"]]] = 1.0
    W_d = np.diag(w_all)
    b0_orig = np.linalg.solve(X_int.T @ W_d @ X_int, X_int.T @ W_d @ y_orig)
    resid0_orig = y_orig - X_int @ b0_orig
    wss_null_orig = float(np.sum(w_all * resid0_orig**2))

    for label, covs in [
        ("ind_distant only", ["ind_distant"]),
        ("ind_distant + small_n", ["ind_distant", "small_n"]),
        ("pharm + isol + ind_dist + small_n",
         ["pharmacological", "isolated_process", "ind_distant", "small_n"]),
    ]:
        r_eb = pooled_wls(obs_adj, param_list, param_idx, tau2_map, covs)
        if r_eb:
            wss_eb = float(np.sum(w_all * r_eb["resid"]**2))
            r2_eb = 1.0 - wss_eb / wss_null_orig
            df_eb = r_eb["df"]
            n_sfm_slopes = len([p for p in param_slopes["structured_fm"] if not p.startswith("_")])
            n_total_cov = len(covs) + n_sfm_slopes
            r2_adj_eb = (1.0 - (1.0 - r2_eb) * (n_obs - n_params) / (n_obs - n_params - n_total_cov)
                         if (n_obs - n_params - n_total_cov) > 0 else 0.0)
            print(f"    + {label:<40s}  R²={r2_eb:.1%}  adj={r2_adj_eb:.1%}  "
                  f"df={n_obs - n_params - n_total_cov}  #cov={n_total_cov}")