"""Catalogue of the scenarios the app exposes: parameters, ranges and defaults.

Defaults are the thesis inputs (taken from the engine). Ranges are kept to sizes
that solve instantly and give meaningful results; the solver timeout is a
second line of defence, not the first.
"""

from __future__ import annotations

import inspect
from dataclasses import asdict, dataclass
from typing import Any, Callable, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, create_model

from engine import run_scenario_01, run_scenario_15
from engine import scenario_01, scenario_15
from engine._common import HOURS_IN_3_YEARS

# Not an engine argument: limits which instance types the optimizer may use.
ALLOWED = "allowed_instances"


@dataclass(frozen=True)
class Param:
    name: str
    label: str
    kind: Literal["int", "float", "choice", "multi"]
    default: Any
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    unit: str = ""
    help: str = ""
    choices: tuple = ()


@dataclass(frozen=True)
class Scenario:
    id: str
    name: str
    description: str
    run: Callable
    instances: dict
    params: tuple
    notes: tuple = ()


def _hours() -> Param:
    return Param("hours", "Planning horizon", "int", HOURS_IN_3_YEARS, 730, 43800, 730, "hours",
                 "Hours of running cost counted in the total. 26,280 h = 3 years; 8,760 h = 1 year.")


def _allowed(instances: dict) -> Param:
    names = tuple(instances)
    return Param(ALLOWED, "Allowed instance types", "multi", names,
                 help="Instance types the optimizer may use. The baseline always uses its "
                      "standard types, so it stays the thesis comparison.",
                 choices=names)


SCENARIOS: dict[str, Scenario] = {
    "scenario_01": Scenario(
        id="scenario_01",
        name=scenario_01.NAME,
        description="Cover a steady vCPU and RAM demand with the cheapest mix of "
                    "On-Demand, 1-year and 3-year Reserved Instances.",
        run=run_scenario_01,
        instances=scenario_01.DEFAULT_INSTANCES,
        params=(
            Param("required_vcpus", "Required vCPUs", "int", 100, 4, 10000, 4, "vCPU"),
            Param("required_ram_gb", "Required RAM", "int", 400, 0, 40000, 16, "GB"),
            Param("heuristic_instance", "Baseline buys", "choice", "Instance_RI_1YR",
                  help="The instance type the rule-of-thumb baseline uses for everything.",
                  choices=tuple(scenario_01.DEFAULT_INSTANCES)),
            _hours(),
            _allowed(scenario_01.DEFAULT_INSTANCES),
        ),
        notes=("The baseline sizes for vCPUs only, as in the thesis. If RAM needs more "
               "instances than vCPUs do, the baseline can look cheaper than the optimum.",),
    ),
    "scenario_15": Scenario(
        id="scenario_15",
        name=scenario_15.NAME,
        description="Multi-cloud allocation across AWS and Azure under vCPU, RAM and IOPS "
                    "demand, an upfront (CAPEX) budget, a Spot risk ceiling and a "
                    "minimum Azure share.",
        run=run_scenario_15,
        instances=scenario_15.DEFAULT_INSTANCES,
        params=(
            Param("required_vcpu", "Required vCPUs", "int", 500, 4, 5000, 4, "vCPU"),
            Param("required_ram", "Required RAM", "int", 2000, 0, 50000, 16, "GB"),
            Param("required_iops", "Required IOPS", "int", 15000, 0, 200000, 500, "IOPS"),
            Param("max_capex", "Upfront budget (CAPEX)", "int", 45000, 0, 500000, 1000, "$",
                  "Most that may be paid upfront for Reserved Instances."),
            Param("max_spot_pct", "Max Spot share", "float", 0.15, 0, 1, 0.01, "of vCPUs",
                  "Ceiling on vCPUs from interruptible Spot instances."),
            Param("min_azure_pct", "Min Azure share", "float", 0.35, 0, 1, 0.01, "of vCPUs",
                  "Policy: at least this share of vCPUs must run on Azure."),
            _hours(),
            _allowed(scenario_15.DEFAULT_INSTANCES),
        ),
        notes=("The baseline is the thesis's siloed rule: Azure On-Demand for the Azure "
               "share, then AWS Reserved up to the budget, then AWS On-Demand. It only "
               "sizes for vCPUs and never uses Spot.",),
    ),
}

# Every engine argument's default must be the engine's own default (the thesis input).
for _s in SCENARIOS.values():
    _sig = inspect.signature(_s.run).parameters
    for _p in _s.params:
        if _p.name != ALLOWED:
            assert _sig[_p.name].default == _p.default, (_s.id, _p.name)


def _field(p: Param):
    if p.kind == "choice":
        return (Literal[p.choices], Field(p.default, description=p.label))  # type: ignore[valid-type]
    if p.kind == "multi":
        return (List[Literal[p.choices]],  # type: ignore[valid-type]
                Field(default_factory=lambda: list(p.default), min_length=1,
                      max_length=len(p.choices), description=p.help))
    typ = int if p.kind == "int" else float
    return (typ, Field(p.default, ge=p.min, le=p.max, description=f"{p.label} ({p.unit})"))


def params_model(s: Scenario) -> type[BaseModel]:
    return create_model(
        f"{s.id.title().replace('_', '')}Params",
        __config__=ConfigDict(extra="forbid"),
        **{p.name: _field(p) for p in s.params},
    )


PARAM_MODELS = {sid: params_model(s) for sid, s in SCENARIOS.items()}


def describe(s: Scenario) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "description": s.description,
        "notes": list(s.notes),
        "parameters": [
            {k: v for k, v in asdict(p).items() if v not in (None, "", ())}
            for p in s.params
        ],
    }
