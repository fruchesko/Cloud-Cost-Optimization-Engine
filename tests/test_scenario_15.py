import pytest

from engine import InfeasibleError, run_scenario_15
from engine.scenario_15 import DEFAULT_INSTANCES


def test_defaults_match_thesis():
    r = run_scenario_15()
    assert r.status == "Optimal"
    assert r.savings == pytest.approx(72_138.60, abs=0.005)
    assert round(r.savings_pct, 1) == 13.1
    assert r.heuristic_cost == pytest.approx(552_729.60, abs=0.005)
    assert r.optimal_cost == pytest.approx(480_591.00, abs=0.005)


def test_defaults_meet_all_constraints():
    r = run_scenario_15()
    assert all(c.slack >= -1e-9 for c in r.constraints.values())
    assert r.constraints["Azure_min_vCPU"].rhs == 175
    assert r.constraints["Spot_max_vCPU"].rhs == 75
    assert r.constraints["CAPEX_budget"].lhs <= 45_000
    assert {"vCPU_demand", "CAPEX_budget"} <= set(r.binding_constraints)


def test_bigger_budget_is_never_worse():
    base = run_scenario_15()
    looser = run_scenario_15(max_capex=90_000)
    assert looser.optimal_cost <= base.optimal_cost


def test_zero_capex_uses_no_reserved_instances():
    r = run_scenario_15(max_capex=0)
    assert not any(DEFAULT_INSTANCES[i]["upfront"] for i in r.instances)
    assert r.optimal_cost > run_scenario_15().optimal_cost


def test_azure_policy_without_azure_instances_is_infeasible():
    aws_only = {k: v for k, v in DEFAULT_INSTANCES.items() if v["prov"] == "AWS"}
    with pytest.raises(InfeasibleError):
        run_scenario_15(instances=aws_only)


def test_reserved_only_catalog_with_no_budget_is_infeasible():
    reserved_only = {k: v for k, v in DEFAULT_INSTANCES.items() if v["upfront"] > 0}
    with pytest.raises(InfeasibleError):
        run_scenario_15(instances=reserved_only, max_capex=0)


@pytest.mark.parametrize(
    "kwargs",
    [{"max_spot_pct": 1.5}, {"min_azure_pct": -0.1}, {"required_vcpu": -1}, {"max_capex": -1}],
)
def test_invalid_parameters_rejected(kwargs):
    with pytest.raises(ValueError):
        run_scenario_15(**kwargs)
