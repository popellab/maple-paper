# Posterior Predictive Diagnostics
# Computes z-scores and posterior coverage for calibration results

using Turing
using DifferentialEquations
using Distributions
using Statistics
using Random
using Printf

Random.seed!(42)

# ======================================================================
# OBSERVED DATA
# ======================================================================

const DATA = Dict(
    "ecm_secretion_apsc" => (
        obs_median = 6.477e-10,
        obs_sigma = 3.288e-10,
        param = :k_ECM_apsc_sec,
    ),
    "psc_activation_rate" => (
        obs_median = 0.950,
        obs_sigma = 0.037,
        param = :k_psc_activation,
        requires_ode = true,
    ),
    "psc_death_activated" => (
        obs_median = 0.086,
        obs_sigma = 0.022,
        param = :k_apsc_death,
        requires_ode = true,
    ),
    "psc_death_quiescent" => (
        obs_median = 0.198,
        obs_sigma = 0.049,
        param = :k_qpsc_death,
    ),
    "psc_proliferation" => (
        obs_median = 4.336,
        obs_sigma = 0.492,
        param = :k_apsc_prolif,
        requires_ode = true,
    ),
    "psc_recruitment_const" => (
        obs_median = 3.723e7,
        obs_sigma = 1.575e7,
        param = :k_psc_const,
    ),
    "tcell_kill_probability" => (
        obs_median = 0.150,
        obs_sigma = 0.028,
        param = :p_T_kill_per_contact,
    ),
    "tgfb_secretion_apsc" => (
        obs_median = 4.254e-10,
        obs_sigma = 1.827e-10,
        param = :k_TGFb_sec_apsc,
    ),
    "treg_suppression_r50" => (
        obs_median = 0.507,
        obs_sigma = 0.145,
        param = :R50_Treg,
    ),
)

# Posterior medians from joint inference (from previous run)
const POSTERIOR_MEDIANS = Dict(
    :k_ECM_apsc_sec => 8.744e-10,
    :k_psc_activation => 2.576,
    :k_apsc_death => 0.09125,
    :k_qpsc_death => 0.1776,
    :k_apsc_prolif => 1.442,
    :k_psc_const => 3.489e7,
    :k_psc_encounter => 2.542e5,
    :p_T_kill_per_contact => 0.1503,
    :k_TGFb_sec_apsc => 3.754e-10,
    :R50_Treg => 0.4112,
)

# Posterior standard deviations (estimated from inference)
const POSTERIOR_SDS = Dict(
    :k_ECM_apsc_sec => 3.0e-10,
    :k_psc_activation => 0.25,
    :k_apsc_death => 0.025,
    :k_qpsc_death => 0.045,
    :k_apsc_prolif => 0.20,
    :k_psc_const => 1.5e7,
    :k_psc_encounter => 1.0e5,
    :p_T_kill_per_contact => 0.025,
    :k_TGFb_sec_apsc => 1.7e-10,
    :R50_Treg => 0.12,
)

# ODE functions for computing predicted observables
function psc_activation_ode!(du, u, p, t)
    k = p[1]
    du[1] = -k * u[1]
    du[2] = k * u[1]
end

function first_order_decay_ode!(du, u, p, t)
    k = p[1]
    du[1] = -k * u[1]
end

function exponential_growth_ode!(du, u, p, t)
    k = p[1]
    du[1] = k * u[1]
end

# Compute predicted observable for each target
function compute_predicted(target_name, param_value)
    if target_name == "psc_activation_rate"
        prob = ODEProblem(psc_activation_ode!, [1.0, 0.0], (0.0, 2.0), [param_value])
        sol = solve(prob, Tsit5(); abstol=1e-8, reltol=1e-6)
        return sol[2, end] / (sol[1, end] + sol[2, end])
    elseif target_name == "psc_death_activated"
        prob = ODEProblem(first_order_decay_ode!, [1.0], (0.0, 28.0), [param_value])
        sol = solve(prob, Tsit5(); abstol=1e-8, reltol=1e-6)
        return sol[1, end]
    elseif target_name == "psc_proliferation"
        prob = ODEProblem(exponential_growth_ode!, [1.0], (0.0, 1.0), [param_value])
        sol = solve(prob, Tsit5(); abstol=1e-8, reltol=1e-6)
        return sol[1, end]
    else
        # Direct parameter mapping
        return param_value
    end
end

# ======================================================================
# COMPUTE DIAGNOSTICS
# ======================================================================

println("=" ^ 70)
println("POSTERIOR PREDICTIVE DIAGNOSTICS")
println("=" ^ 70)
println()

# Store results for summary
z_scores = Float64[]
coverage_90 = Bool[]
coverage_95 = Bool[]

println(@sprintf("%-25s %12s %12s %10s %8s %8s", "Target", "Observed", "Predicted", "Z-score", "In 90%", "In 95%"))
println("-" ^ 75)

for (target_name, d) in sort(collect(DATA), by=x->x[1])
    param = d.param
    param_value = POSTERIOR_MEDIANS[param]

    # Compute predicted observable
    predicted = compute_predicted(target_name, param_value)

    # Z-score: (observed - predicted) / obs_sigma
    z = (d.obs_median - predicted) / d.obs_sigma
    push!(z_scores, z)

    # Posterior predictive intervals
    # 90% CI: predicted ± 1.645 * combined_sigma
    # 95% CI: predicted ± 1.96 * combined_sigma
    # Combined uncertainty: sqrt(obs_sigma^2 + posterior_sd^2)
    posterior_sd = POSTERIOR_SDS[param]
    combined_sigma = sqrt(d.obs_sigma^2 + posterior_sd^2)

    in_90 = abs(d.obs_median - predicted) < 1.645 * combined_sigma
    in_95 = abs(d.obs_median - predicted) < 1.96 * combined_sigma
    push!(coverage_90, in_90)
    push!(coverage_95, in_95)

    # Format output
    status_90 = in_90 ? "✓" : "✗"
    status_95 = in_95 ? "✓" : "✗"

    println(@sprintf("%-25s %12.4g %12.4g %10.2f %8s %8s",
            target_name, d.obs_median, predicted, z, status_90, status_95))
end

println("-" ^ 75)
println()

# Summary statistics
println("=" ^ 70)
println("SUMMARY STATISTICS")
println("=" ^ 70)
println()

mean_abs_z = mean(abs.(z_scores))
max_abs_z = maximum(abs.(z_scores))
rmse_z = sqrt(mean(z_scores.^2))
coverage_90_pct = 100.0 * mean(coverage_90)
coverage_95_pct = 100.0 * mean(coverage_95)

println(@sprintf("Mean |Z-score|:           %.3f  (ideal: < 1.0)", mean_abs_z))
println(@sprintf("Max |Z-score|:            %.3f  (ideal: < 2.0)", max_abs_z))
println(@sprintf("RMSE of Z-scores:         %.3f  (ideal: ~ 1.0)", rmse_z))
println()
println(@sprintf("90%% Coverage:             %.1f%%  (expected: 90%%)", coverage_90_pct))
println(@sprintf("95%% Coverage:             %.1f%%  (expected: 95%%)", coverage_95_pct))
println()

# Interpretation
println("=" ^ 70)
println("INTERPRETATION")
println("=" ^ 70)
println()

if mean_abs_z < 1.0 && max_abs_z < 2.0
    println("✓ Z-scores indicate good model-data agreement")
else
    println("⚠ Some Z-scores indicate potential model misfit")
end

if coverage_90_pct >= 80.0 && coverage_95_pct >= 90.0
    println("✓ Posterior coverage is well-calibrated")
elseif coverage_90_pct >= 70.0
    println("⚠ Posterior coverage is slightly under-calibrated (uncertainties may be too narrow)")
else
    println("⚠ Posterior coverage suggests model misspecification or underestimated uncertainties")
end

println()
println("Note: These metrics evaluate how well posterior predictions match observed data.")
println("Good calibration implies the model captures both point estimates and uncertainty.")
