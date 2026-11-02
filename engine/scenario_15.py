"""Scenario 15: Integrated Master Problem (ported from code/scenario_15.py).

Multi-cloud allocation under vCPU/RAM/IOPS demand, a CAPEX budget, a Spot
risk ceiling and a minimum Azure share.
"""

from __future__ import annotations

import math
from typing import Mapping

from ._common import HOURS_IN_3_YEARS, ScenarioResult, build_result, solve, tco

NAME = "Scenario 15: Master Optimization"

DEFAULT_INSTANCES: dict[str, dict] = {
    "AWS_R6_RI":   {"cost": 0.080, "upfront": 1800, "vCPU": 4, "RAM": 32, "IOPS": 200, "spot": False, "prov": "AWS"},
    "AWS_M6_OD":   {"cost": 0.160, "upfront": 0,    "vCPU": 4, "RAM": 16, "IOPS": 100, "spot": False, "prov": "AWS"},
    "AWS_C7_Spot": {"cost": 0.015, "upfront": 0,    "vCPU": 8, "RAM": 16, "IOPS": 150, "spot": True,  "prov": "AWS"},
    "AZR_E4_RI":   {"cost": 0.095, "upfront": 2200, "vCPU": 4, "RAM": 64, "IOPS": 150, "spot": False, "prov": "Azure"},
    "AZR_E4_OD":   {"cost": 0.190, "upfront": 0,    "vCPU": 4, "RAM": 32, "IOPS": 120, "spot": False, "prov": "Azure"},
    "AZR_D2_Spot": {"cost": 0.020, "upfront": 0,    "vCPU": 2, "RAM": 8,  "IOPS": 50,  "spot": True,  "prov": "Azure"},
}


def heuristic_cost(
    required_vcpu: float,
    max_capex: float,
    min_azure_pct: float,
    instances: Mapping[str, Mapping],
    azure_od: str = "AZR_E4_OD",
    aws_ri: str = "AWS_R6_RI",
    aws_od: str = "AWS_M6_OD",
    hours: int = HOURS_IN_3_YEARS,
) -> float:
    """"Siloed compliance" baseline, same steps as code/scenario_15.py.

    Meet the Azure share with Azure On-Demand, then the rest with AWS RIs up to
    the CAPEX budget, then AWS On-Demand. No Spot.
    """
    az, ri, od = instances[azure_od], instances[aws_ri], instances[aws_od]

    num_azure = math.ceil(required_vcpu * min_azure_pct / az["vCPU"])
    rem_vcpu = required_vcpu - num_azure * az["vCPU"]

    max_ris = int(max_capex // ri["upfront"]) if ri["upfront"] else math.inf
    num_ris = min(max_ris, math.ceil(rem_vcpu / ri["vCPU"]))

    rem_final = max(0, rem_vcpu - num_ris * ri["vCPU"])
    num_od = math.ceil(rem_final / od["vCPU"])

    return (
        num_azure * az["cost"] * hours
        + tco(ri, num_ris, hours)
        + num_od * od["cost"] * hours
    )


def run(
    required_vcpu: float = 500,
    required_ram: float = 2000,
    required_iops: float = 15000,
    max_capex: float = 45000,
    max_spot_pct: float = 0.15,
    min_azure_pct: float = 0.35,
    instances: Mapping[str, Mapping] | None = None,
    hours: int = HOURS_IN_3_YEARS,
) -> ScenarioResult:
    """Run Scenario 15. Defaults are the thesis inputs.

    Spot and Azure limits are fractions of ``required_vcpu``.
    Raises InfeasibleError if the constraints cannot all be met.
    """
    if min(required_vcpu, required_ram, required_iops, max_capex) < 0:
        raise ValueError("demands and max_capex must be non-negative")
    for name, pct in (("max_spot_pct", max_spot_pct), ("min_azure_pct", min_azure_pct)):
        if not 0 <= pct <= 1:
            raise ValueError(f"{name} must be between 0 and 1")
    instances = DEFAULT_INSTANCES if instances is None else instances

    def coeffs(field, keep=lambda d: True):
        return {i: d[field] for i, d in instances.items() if keep(d)}

    constraints = {
        "vCPU_demand": (">=", required_vcpu, coeffs("vCPU")),
        "RAM_demand": (">=", required_ram, coeffs("RAM")),
        "IOPS_demand": (">=", required_iops, coeffs("IOPS")),
        "CAPEX_budget": ("<=", max_capex, coeffs("upfront")),
        "Azure_min_vCPU": (">=", required_vcpu * min_azure_pct,
                           coeffs("vCPU", lambda d: d["prov"] == "Azure")),
        "Spot_max_vCPU": ("<=", required_vcpu * max_spot_pct,
                          coeffs("vCPU", lambda d: d["spot"])),
    }
    status, optimal, chosen, checks = solve(NAME, instances, constraints, hours)

    heuristic = heuristic_cost(required_vcpu, max_capex, min_azure_pct, instances, hours=hours)

    return build_result(NAME, status, heuristic, optimal, chosen, checks)
