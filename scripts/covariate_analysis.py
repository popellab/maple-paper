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

    # k_CCL2_sec: ELISA of conditioned media
    "k_CCL2_sec_Steube1999_proxy": "accumulated",
    "k_CCL2_sec_bcproxy_yoshimura2023": "accumulated",
    "k_CCL2_sec_Fujita2010_PrSC": "accumulated",

    # k_M1_pol: flow cytometry M1/M2 % or IHC ratio
    "k_M1_pol_repolarization_horhold2020": "fraction_ratio",
    "k_M1_pol_Watkins2007_IL12_TAM_reprogramming": "fraction_ratio",
    "k_M1_pol_rp182_m2_to_m1_repolarization": "fraction_ratio",
    "k_Mac_rec_humanPDAC_CD40_2021": "fraction_ratio",  # IHC M1:M2 ratio

    # k_MDSC_rec
    "k_MDSC_rec_recruitment_pericyte_MDSC_Hong2015": "snapshot_density",  # in vivo tumor counts
    "k_MDSC_rec_PDAC_Porembka2012": "fraction_ratio",  # flow cytometry MDSC %
    "k_MDSC_rec_oscc_ccl2_oo2022": "migration_assay",  # Boyden chamber

    # k_Mac_rec / k_Mac_death: IHC density
    "k_Mac_rec_PDAC_TAM_recruitment_Chen2015": "snapshot_density",
    "k_Mac_rec_PDAC_M1_recruitment_Gu2023": "snapshot_density",

    # k_apsc_death: cell viability/count over time
    "k_apsc_death_RA_Xiao2015": "rate_direct",
    "k_apsc_death_melatoninPSC_Estaras2021": "rate_direct",

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

    # k_CCL2_sec: in vitro cells secreting spontaneously → isolated
    "k_CCL2_sec_Steube1999_proxy": 1,
    "k_CCL2_sec_bcproxy_yoshimura2023": 1,
    "k_CCL2_sec_Fujita2010_PrSC": 1,

    # k_M1_pol
    "k_M1_pol_repolarization_horhold2020": 1,    # purified BMDM + stimulus
    "k_M1_pol_Watkins2007_IL12_TAM_reprogramming": 2,  # TAMs from tumor → ex vivo
    "k_M1_pol_rp182_m2_to_m1_repolarization": 1,  # purified BMDM + drug
    "k_Mac_rec_humanPDAC_CD40_2021": 3,           # clinical tissue ratio

    # k_MDSC_rec
    "k_MDSC_rec_recruitment_pericyte_MDSC_Hong2015": 3,  # in vivo tumor model
    "k_MDSC_rec_PDAC_Porembka2012": 3,           # clinical tissue
    "k_MDSC_rec_oscc_ccl2_oo2022": 1,            # Boyden chamber, isolated chemotaxis

    # k_Mac_rec / k_Mac_death: clinical IHC → full
    "k_Mac_rec_PDAC_TAM_recruitment_Chen2015": 3,
    "k_Mac_rec_PDAC_M1_recruitment_Gu2023": 3,

    # k_apsc_death: purified PSCs + drug → isolated
    "k_apsc_death_RA_Xiao2015": 1,
    "k_apsc_death_melatoninPSC_Estaras2021": 1,

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

INDICATION_DISTANCE = {
    "k_C1_growth_pdac_human_vdt_ahn2017": 3,
    "k_C1_growth_pdac_tumor_doubling_jang2015": 3,
    "k_CCL2_sec_Steube1999_proxy": 1,       # monocytic leukemia cell line
    "k_CCL2_sec_bcproxy_yoshimura2023": 2,   # breast cancer (adenocarcinoma)
    "k_CCL2_sec_Fujita2010_PrSC": 2,        # pancreatic stellate cells, relevant stroma
    "k_M1_pol_repolarization_horhold2020": 1,  # generic BMDM, no tumor context
    "k_M1_pol_Watkins2007_IL12_TAM_reprogramming": 2,  # mouse tumor TAMs, not PDAC
    "k_M1_pol_rp182_m2_to_m1_repolarization": 2,  # mouse tumor-derived M2
    "k_Mac_rec_humanPDAC_CD40_2021": 3,       # human PDAC
    "k_MDSC_rec_recruitment_pericyte_MDSC_Hong2015": 2,  # mouse pancreatic tumor model
    "k_MDSC_rec_PDAC_Porembka2012": 3,       # human PDAC
    "k_MDSC_rec_oscc_ccl2_oo2022": 1,        # OSCC, distant indication
    "k_Mac_rec_PDAC_TAM_recruitment_Chen2015": 3,
    "k_Mac_rec_PDAC_M1_recruitment_Gu2023": 3,
    "k_apsc_death_RA_Xiao2015": 2,           # generic PSCs, related
    "k_apsc_death_melatoninPSC_Estaras2021": 2,  # generic PSCs, related
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
    # Interactions
    "invitro_x_migration", "invitro_x_fraction",
    "nonhuman_x_smalln", "pharm_x_isolated",
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