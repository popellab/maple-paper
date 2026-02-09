# Review: immune_dynamics_timecourse_PDAC_deriv001.yaml

**Source:** Yang et al. 2022, eBioMedicine (DOI: 10.1016/j.ebiom.2022.103958)

**Reviewed:** 2026-02-03

---

## Summary

This calibration target attempts to jointly identify three parameters (q_Treg_T_in, k_MDSC_rec, k_M1_pol) from CyTOF immune profiling data across five PDAC developmental stages in KPC mice. The file has significant issues with both data extraction accuracy and forward model validity.

---

## Data Extraction Issues

### 1. Treg Fractions (Figure 2e) - Likely Underestimated

**Claimed values:** 2% → 7% (ADM peak) → 4% → 3% → 2%

**Problem:** Figure 2e shows two Treg subclusters (CD4_c10 and CD4_c12). The CD4_c12 subcluster alone at ADM appears to range from ~15-30% of CD3+ cells. The claimed values (~7% peak) appear to reflect only CD4_c10, not the sum of both Treg clusters.

**Qualitative pattern is correct:** The paper confirms "The proportion of Tregs increased transiently in the ADM stage and continuously decreased in subsequent stages" (p. 5).

### 2. MDSC Fractions (Figure 1g) - Trend Correct, Values Unverified

**Claimed values:** 5% → 8% → 12% → 25% → 38%

The monotonic increase matches the paper's description: "Nearly all of the MDSC subsets rapidly accumulated after tumor formation" (p. 7). Exact values need digitization from Figure 1g scatter plots.

### 3. Arg-1+ Macrophage Fractions (Figure 3i) - Values Unverified

**Claimed values:** 10% → 15% → 25% → 40% → 55%

The increase pattern matches the paper's description of Arg-1+ macrophage accumulation at tumor stages. Values would need to be summed across clusters Mφ_c3, c8, and c9.

### 4. Missing Value Snippets

All extracted values list `extraction_method: digitizer` but provide no `value_snippet` fields. The paper does not report exact percentages in text—all data is in scatter plots requiring digitization.

### 5. Assumed Parameters Have No Paper Support

The following are entirely assumed with no basis in Yang et al. 2022:
- Tumor burden mappings: B_normal=0.02, B_ADM=0.15, B_PanIN=0.35, B_ES=0.70, B_LS=0.95
- Hill function parameters: Kc_rec=0.3, K_CXCL12_excl=0.25, CCL2_50_norm=0.3
- Reference rates: k_M2_pol_ref=0.5, q_cd8_ref=1e-5

These should have `source_ref: assumed` rather than `Yang2022_eBioMedicine`.

---

## Forward Model Issues

### 1. CRITICAL: Treg Model Cannot Reproduce the Observed Peak

The forward model computes:
```
R_treg = q_treg * Hill_cancer(B)
R_cd8 = q_cd8_ref * Hill_cancer(B) * (1 - H_CXCL12(B))
R_other = q_other_T * Hill_cancer(B) * (1 - 0.5 * H_CXCL12(B))
Treg_frac = 100 * R_treg / (R_treg + R_cd8 + R_other)
```

Since `Hill_cancer(B)` cancels in the ratio, this simplifies to:
```
Treg_frac ∝ q_treg / [q_treg + q_cd8*(1-H_CXCL12) + q_other*(1-0.5*H_CXCL12)]
```

**Mathematical consequence:** As B increases, H_CXCL12 increases, the denominator decreases, and Treg_frac **increases monotonically**.

**The model cannot produce a peak at ADM followed by decline.** It always predicts Tregs increase with tumor burden.

To fix this, the model would need:
- Tregs also being excluded at late stages, OR
- Competition with MDSCs/macrophages for a shared "niche", OR
- Treg death/efflux increasing at late stages

### 2. MDSC Model Has Confounded Scale Factor

```python
mdsc_scale = 80.0  # Hard-coded
mdsc_frac = mdsc_scale * k_mdsc * B * Hill_CCL2(B)
```

The `mdsc_scale = 80.0` is calibrated to match the late-stage value. This makes `k_MDSC_rec` and `mdsc_scale` completely confounded—any late-stage MDSC fraction can be achieved by adjusting either parameter.

### 3. Arg-1+ Macrophage Model is Plausible

The mechanistic logic is sound:
- ↑ CXCL12 exclusion → ↓ CD8 infiltration → ↓ IFNγ → ↓ M2→M1 conversion → ↑ Arg-1+ fraction

This produces the correct monotonic increase. However, the floor `max(0.1, 1.0 - H_CXCL12)` is arbitrary.

---

## Observation Model Issues

### 1. Only 3 of 15 Data Points Used

The error model specifies only:
- `treg_ADM_obs` (1 stage)
- `mdsc_LS_obs` (1 stage)
- `arg1mac_LS_obs` (1 stage)

But inputs contain data for **all 5 stages × 3 observables = 15 data points**.

Using 3 observations to constrain 3 parameters gives an exactly-determined system with no statistical power to test model validity or estimate meaningful uncertainty.

### 2. ADM Treg Observation is Incompatible with Forward Model

The error model uses the ADM Treg peak to constrain `q_Treg_T_in`, but the forward model cannot produce a peak. Inference will fail or produce meaningless parameter estimates.

### 3. Assumed CVs Lack Justification

```yaml
cv_treg: 0.4
cv_mdsc: 0.35
cv_arg1mac: 0.4
```

These are stated as "assumed based on scatter" but no actual digitization of variance from the figures was performed.

---

## Identifiability Claims are Invalid

The `identifiability_notes` state:

> "q_Treg_T_in is identified by the Treg fraction peak at ADM (~7% vs ~2% baseline)"

**This is false because:**
1. The forward model cannot produce a peak (predicts monotonic increase)
2. Only one time point (ADM) is used, not the full trajectory that would constrain peak shape
3. The q_Treg_T_in / q_CD8_ref ratio is what matters, and q_CD8_ref is arbitrarily fixed

> "k_MDSC_rec is identified by the MDSC accumulation curve"

**Partially true, but:**
- Only the late-stage point is used, not the full curve
- Confounded with the hard-coded `mdsc_scale = 80.0`

> "k_M1_pol is identified by the macrophage polarization shift"

**Partially true, but:**
- Only the late-stage point is used
- Confounded with fixed `k_M2_pol_ref = 0.5`

---

## Recommendations

### Must Fix
1. **Redesign Treg model** to include a mechanism for decline at late stages (e.g., Treg exclusion, death, or competition)
2. **Use all 15 data points** in the error model, not just 3
3. **Remove hard-coded mdsc_scale** or explicitly acknowledge k_MDSC_rec is unidentifiable in absolute terms

### Should Fix
4. **Re-digitize Figure 2e** carefully, summing both CD4_c10 and CD4_c12 for total Treg fractions
5. **Add value_snippets** documenting which figure panels and clusters were used
6. **Change source_ref for assumed parameters** to `assumed` rather than attributing to Yang2022

### Consider
7. **Simplify to empirical model** rather than claiming mechanistic coupling that doesn't work mathematically
8. **Add more observation time points** to actually constrain the temporal dynamics
9. **Digitize actual variance** from scatter plots rather than assuming CVs

---

## Verdict

**Not ready for use.** The fundamental issue is that the forward model cannot reproduce the key qualitative feature (Treg peak at ADM) that is supposed to identify the primary parameter of interest. The file needs substantial revision before it can provide meaningful calibration constraints.