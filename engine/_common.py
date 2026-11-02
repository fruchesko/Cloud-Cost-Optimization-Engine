"""Shared result types and LP helpers for the engine scenarios."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

import pulp

HOURS_IN_3_YEARS = 26280

# Constraint slack at or below this is treated as binding (tight).
BINDING_TOLERANCE = 1e-6


class InfeasibleError(ValueError):
    """Raised when the LP solver finds no allocation that meets every constraint."""

    def __init__(self, scenario: str, status: str):
        super().__init__(f"{scenario}: no feasible allocation (solver status: {status})")
        self.scenario = scenario
        self.status = status


@dataclass(frozen=True)
class ConstraintCheck:
    """How one constraint ended up at the optimum.

    ``slack`` is the unused room: lhs - rhs for ``>=`` and rhs - lhs for ``<=``.
    """

    lhs: float
    sense: str
    rhs: float
    slack: float
    binding: bool


@dataclass(frozen=True)
class ScenarioResult:
    scenario: str
    status: str
    heuristic_cost: float
    optimal_cost: float
    savings: float
    savings_pct: float
    instances: dict[str, int]
    constraints: dict[str, ConstraintCheck] = field(default_factory=dict)

    @property
    def binding_constraints(self) -> list[str]:
        return [name for name, c in self.constraints.items() if c.binding]


def tco(instance: Mapping, count: int | float = 1, hours: int = HOURS_IN_3_YEARS) -> float:
    """Upfront plus hourly cost over the horizon for ``count`` instances."""
    return count * (instance["upfront"] + instance["cost"] * hours)


def solve(
    scenario: str,
    instances: Mapping[str, Mapping],
    constraints: Mapping[str, tuple[str, float, Mapping[str, float]]],
    hours: int = HOURS_IN_3_YEARS,
) -> tuple[str, float, dict[str, int], dict[str, ConstraintCheck]]:
    """Minimise 3-year TCO over integer instance counts.

    ``constraints`` maps a name to ``(sense, rhs, coefficients)`` where sense is
    ">=" or "<=" and coefficients maps instance name to its per-unit contribution.
    Raises InfeasibleError unless the solver reports an optimal solution.
    """
    if not instances:
        raise InfeasibleError(scenario, "No instances")

    model = pulp.LpProblem(scenario.replace(" ", "_"), pulp.LpMinimize)
    x = pulp.LpVariable.dicts("Num_Instances", list(instances), lowBound=0, cat=pulp.LpInteger)
    model += pulp.lpSum(tco(instances[i], x[i], hours) for i in instances)

    exprs = {}
    for name, (sense, rhs, coeffs) in constraints.items():
        expr = pulp.lpSum(coeffs.get(i, 0) * x[i] for i in instances)
        exprs[name] = expr
        if sense == ">=":
            model += expr >= rhs, name
        elif sense == "<=":
            model += expr <= rhs, name
        else:
            raise ValueError(f"unknown constraint sense {sense!r}")

    model.solve(pulp.PULP_CBC_CMD(msg=0))
    status = pulp.LpStatus[model.status]
    if status != "Optimal":
        raise InfeasibleError(scenario, status)

    counts = {i: int(round(x[i].varValue or 0)) for i in instances}
    checks = {}
    for name, (sense, rhs, coeffs) in constraints.items():
        lhs = sum(coeffs.get(i, 0) * counts[i] for i in instances)
        slack = lhs - rhs if sense == ">=" else rhs - lhs
        checks[name] = ConstraintCheck(lhs, sense, rhs, slack, abs(slack) <= BINDING_TOLERANCE)

    optimal = pulp.value(model.objective)
    return status, optimal, {i: n for i, n in counts.items() if n > 0}, checks


def build_result(scenario, status, heuristic, optimal, chosen, checks) -> ScenarioResult:
    savings = heuristic - optimal
    return ScenarioResult(
        scenario=scenario,
        status=status,
        heuristic_cost=heuristic,
        optimal_cost=optimal,
        savings=savings,
        savings_pct=savings / heuristic * 100 if heuristic else 0.0,
        instances=chosen,
        constraints=checks,
    )
