"""Scenario 13: Storage Migration (ported from code/scenario_13.py).

Place a data volume across storage tiers (hot, cool, archive) to minimise the
monthly storage bill, while meeting an IOPS requirement and keeping the one-time
migration cost (CAPEX, per GB moved) within budget. Volumes are continuous (GB),
unlike the instance counts in the compute scenarios.
"""

from __future__ import annotations

from typing import Mapping

import pulp

from ._common import BINDING_TOLERANCE, ConstraintCheck, InfeasibleError, ScenarioResult, build_result

NAME = "Scenario 13: Storage Migration"

# Per GB: monthly cost (opex), IOPS provided, one-time migration cost (capex).
DEFAULT_TIERS: dict[str, dict] = {
    "Hot_Standard":    {"opex": 0.023,  "iops": 0.3,  "capex": 0.35, "type": "Hot"},
    "Cool_Infrequent": {"opex": 0.0125, "iops": 0.1,  "capex": 0.10, "type": "Cool"},
    "Archive_Glacier": {"opex": 0.004,  "iops": 0.01, "capex": 0.01, "type": "Archive"},
}


def heuristic(required_volume_gb: float, tiers: Mapping[str, Mapping],
              hot: str = "Hot_Standard", cool: str = "Cool_Infrequent") -> tuple[float, float]:
    """"Active tiers only" baseline from the thesis: split the volume 50/50 between
    hot and cool storage. Returns (monthly cost, migration capex)."""
    half = required_volume_gb / 2
    monthly = half * tiers[hot]["opex"] + half * tiers[cool]["opex"]
    capex = half * tiers[hot]["capex"] + half * tiers[cool]["capex"]
    return monthly, capex


def run(
    required_volume_gb: float = 500_000,
    required_iops: float = 25_000,
    max_capex: float = 80_000,
    tiers: Mapping[str, Mapping] | None = None,
    baseline_tiers: Mapping[str, Mapping] | None = None,
) -> ScenarioResult:
    """Run Scenario 13. Defaults are the thesis inputs.

    Costs in the result are per month. ``instances`` holds GB per tier.
    ``extras`` has the migration capex of the baseline and of the optimum.
    The baseline's tiers are looked up in ``baseline_tiers`` (default: ``tiers``).
    """
    if min(required_volume_gb, required_iops, max_capex) < 0:
        raise ValueError("volume, IOPS and max_capex must be non-negative")
    tiers = DEFAULT_TIERS if tiers is None else tiers
    if not tiers:
        raise InfeasibleError(NAME, "No tiers")

    model = pulp.LpProblem("Scenario_13_Storage_Migration", pulp.LpMinimize)
    gb = pulp.LpVariable.dicts("Volume_GB", list(tiers), lowBound=0, cat=pulp.LpContinuous)
    model += pulp.lpSum(tiers[t]["opex"] * gb[t] for t in tiers)

    constraints = {
        "Volume_demand": (">=", required_volume_gb, {t: 1.0 for t in tiers}),
        "IOPS_demand": (">=", required_iops, {t: d["iops"] for t, d in tiers.items()}),
        "CAPEX_budget": ("<=", max_capex, {t: d["capex"] for t, d in tiers.items()}),
    }
    for name, (sense, rhs, coeffs) in constraints.items():
        expr = pulp.lpSum(coeffs[t] * gb[t] for t in tiers)
        model += (expr >= rhs if sense == ">=" else expr <= rhs), name

    model.solve(pulp.PULP_CBC_CMD(msg=0))
    status = pulp.LpStatus[model.status]
    if status != "Optimal":
        raise InfeasibleError(NAME, status)

    volumes = {t: gb[t].varValue or 0.0 for t in tiers}
    checks = {}
    for name, (sense, rhs, coeffs) in constraints.items():
        lhs = sum(coeffs[t] * volumes[t] for t in tiers)
        slack = lhs - rhs if sense == ">=" else rhs - lhs
        # Continuous LP: allow a relative tolerance for "binding".
        tol = max(BINDING_TOLERANCE, 1e-6 * max(1.0, abs(rhs)))
        checks[name] = ConstraintCheck(lhs, sense, rhs, slack, abs(slack) <= tol)

    optimal = pulp.value(model.objective)
    base_monthly, base_capex = heuristic(required_volume_gb,
                                         tiers if baseline_tiers is None else baseline_tiers)
    chosen = {t: v for t, v in volumes.items() if v > 1e-6}
    result = build_result(NAME, status, base_monthly, optimal, chosen, checks)
    result.extras.update({"baseline_capex": base_capex,
                          "optimal_capex": checks["CAPEX_budget"].lhs})
    return result
