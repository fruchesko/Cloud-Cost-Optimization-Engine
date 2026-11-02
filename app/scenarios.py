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

from engine import run_scenario_01, run_scenario_13, run_scenario_15
from engine import scenario_01, scenario_13, scenario_15
from engine._common import HOURS_IN_3_YEARS, tco

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
    instances: dict           # the catalogue the optimizer picks from
    params: tuple
    notes: tuple = ()
    catalog_arg: str = "instances"   # engine argument names for the catalogue
    baseline_arg: str = "baseline_instances"
    cost_period: str = "over the planning horizon"
    columns: tuple = ()        # (key, label, format) for the resources table
    rows: Optional[Callable] = None    # (scenario, result, params) -> list of row dicts
    comparisons: Optional[Callable] = None  # (result) -> [{label, baseline, optimal}]


_PRICING = {"OD": "On-Demand", "RI-1YR": "Reserved 1-yr", "RI-3YR": "Reserved 3-yr"}


def _pricing(spec: dict) -> str:
    if "type" in spec:
        return _PRICING.get(spec["type"], spec["type"])
    if spec.get("spot"):
        return "Spot"
    return "Reserved" if spec["upfront"] else "On-Demand"


COMPUTE_COLUMNS = (("name", "Instance", "text"), ("provider", "Cloud", "text"),
                   ("type", "Pricing", "text"), ("count", "Count", "num"),
                   ("vcpu", "vCPU", "num"), ("ram_gb", "RAM GB", "num"),
                   ("total_cost", "Total cost", "money"))


def compute_rows(s: "Scenario", r, params: dict) -> list[dict]:
    hours = params.get("hours", HOURS_IN_3_YEARS)
    rows = []
    for name, count in r.instances.items():
        spec = s.instances[name]
        rows.append({
            "name": name, "provider": spec.get("prov"), "type": _pricing(spec),
            "count": count, "vcpu": count * spec["vCPU"],
            "ram_gb": count * spec.get("RAM", spec.get("RAM_GB", 0)),
            "total_cost": tco(spec, count, hours),
        })
    return sorted(rows, key=lambda x: -x["total_cost"])


STORAGE_COLUMNS = (("name", "Tier", "text"), ("type", "Class", "text"),
                   ("gb", "Volume GB", "num"), ("iops", "IOPS", "num"),
                   ("monthly_cost", "Per month", "money"), ("migration_cost", "Migration (one-time)", "money"))


def storage_rows(s: "Scenario", r, params: dict) -> list[dict]:
    rows = []
    for name, gb in r.instances.items():
        t = s.instances[name]
        rows.append({"name": name, "type": t["type"], "gb": gb, "iops": gb * t["iops"],
                     "monthly_cost": gb * t["opex"], "migration_cost": gb * t["capex"]})
    return sorted(rows, key=lambda x: -x["monthly_cost"])


def storage_comparisons(r) -> list[dict]:
    return [{"label": "One-time migration cost", "baseline": r.extras["baseline_capex"],
             "optimal": r.extras["optimal_capex"]}]


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
        columns=COMPUTE_COLUMNS, rows=compute_rows,
    ),
    "scenario_13": Scenario(
        id="scenario_13",
        name=scenario_13.NAME,
        description="Spread a data volume across hot, cool and archive storage to cut the "
                    "monthly bill, while meeting an IOPS requirement and a budget for the "
                    "one-time migration cost.",
        run=run_scenario_13,
        instances=scenario_13.DEFAULT_TIERS,
        params=(
            Param("required_volume_gb", "Data volume", "int", 500_000, 1_000, 2_000_000, 1_000, "GB",
                  "Minimum amount of data to store (500,000 GB = 500 TB)."),
            Param("required_iops", "Required IOPS", "int", 25_000, 0, 200_000, 500, "IOPS",
                  "Total read/write operations per second the storage must sustain."),
            Param("max_capex", "Migration budget (CAPEX)", "int", 80_000, 0, 500_000, 1_000, "$",
                  "Most that may be spent once on moving data into the tiers (per GB fee)."),
            Param(ALLOWED, "Allowed storage tiers", "multi", tuple(scenario_13.DEFAULT_TIERS),
                  help="Tiers the optimizer may use. The baseline always splits 50/50 "
                       "between Hot and Cool, as in the thesis.",
                  choices=tuple(scenario_13.DEFAULT_TIERS)),
        ),
        notes=("Costs are per month. The baseline is the thesis's \"active tiers only\" "
               "rule: half the data in Hot, half in Cool, with no IOPS or budget check.",
               "The data volume is a minimum: if it's cheaper, the optimizer may store "
               "more in a slow tier to reach the IOPS target.",),
        catalog_arg="tiers", baseline_arg="baseline_tiers", cost_period="per month",
        columns=STORAGE_COLUMNS, rows=storage_rows, comparisons=storage_comparisons,
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
        columns=COMPUTE_COLUMNS, rows=compute_rows,
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
        "cost_period": s.cost_period,
        "parameters": [
            {k: v for k, v in asdict(p).items() if v not in (None, "", ())}
            for p in s.params
        ],
    }
