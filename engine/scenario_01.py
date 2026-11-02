"""Scenario 1: Rate Optimization (ported from code/scenario_01.py).

Cover a steady vCPU/RAM demand with the cheapest mix of On-Demand and
Reserved Instances over a 3-year horizon.
"""

from __future__ import annotations

import math
from typing import Mapping

from ._common import HOURS_IN_3_YEARS, ScenarioResult, build_result, solve, tco

NAME = "Scenario 1: Rate Optimization"

DEFAULT_INSTANCES: dict[str, dict] = {
    "Instance_OD":     {"cost": 0.150, "upfront": 0,    "vCPU": 4, "RAM_GB": 16, "type": "OD"},
    "Instance_RI_1YR": {"cost": 0.090, "upfront": 800,  "vCPU": 4, "RAM_GB": 16, "type": "RI-1YR"},
    "Instance_RI_3YR": {"cost": 0.060, "upfront": 1500, "vCPU": 4, "RAM_GB": 16, "type": "RI-3YR"},
}


def run(
    required_vcpus: float = 100,
    required_ram_gb: float = 400,
    instances: Mapping[str, Mapping] | None = None,
    heuristic_instance: str = "Instance_RI_1YR",
    hours: int = HOURS_IN_3_YEARS,
    baseline_instances: Mapping[str, Mapping] | None = None,
) -> ScenarioResult:
    """Run Scenario 1. Defaults are the thesis inputs.

    Heuristic baseline: cover all vCPUs with ``heuristic_instance`` (1-year RIs),
    looked up in ``baseline_instances`` (default: ``instances``).
    Raises InfeasibleError if no mix of instances meets the demand.
    """
    if required_vcpus < 0 or required_ram_gb < 0:
        raise ValueError("required_vcpus and required_ram_gb must be non-negative")
    instances = DEFAULT_INSTANCES if instances is None else instances

    constraints = {
        "vCPU_demand": (">=", required_vcpus, {i: d["vCPU"] for i, d in instances.items()}),
        "RAM_demand": (">=", required_ram_gb, {i: d["RAM_GB"] for i, d in instances.items()}),
    }
    status, optimal, chosen, checks = solve(NAME, instances, constraints, hours)

    h = (instances if baseline_instances is None else baseline_instances)[heuristic_instance]
    heuristic = tco(h, math.ceil(required_vcpus / h["vCPU"]), hours)

    return build_result(NAME, status, heuristic, optimal, chosen, checks)
