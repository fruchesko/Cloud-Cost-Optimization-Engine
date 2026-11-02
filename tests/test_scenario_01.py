import pytest

from engine import InfeasibleError, run_scenario_01
from engine.scenario_01 import DEFAULT_INSTANCES


def test_defaults_match_thesis():
    # Thesis Table 4.2
    r = run_scenario_01()
    assert r.status == "Optimal"
    assert r.heuristic_cost == pytest.approx(79_130.00, abs=0.005)
    assert r.optimal_cost == pytest.approx(76_920.00, abs=0.005)
    assert r.savings == pytest.approx(2_210.00, abs=0.005)
    assert round(r.savings_pct, 2) == 2.79
    assert r.instances == {"Instance_RI_3YR": 25}
    assert set(r.binding_constraints) == {"vCPU_demand", "RAM_demand"}


def test_constraints_satisfied():
    r = run_scenario_01()
    assert all(c.slack >= 0 for c in r.constraints.values())


def test_parameters_change_result():
    r = run_scenario_01(required_vcpus=200, required_ram_gb=800)
    assert r.instances == {"Instance_RI_3YR": 50}
    assert r.optimal_cost == pytest.approx(2 * 76_920.00)


def test_empty_catalog_is_infeasible():
    with pytest.raises(InfeasibleError):
        run_scenario_01(instances={})


def test_no_ram_capacity_is_infeasible():
    no_ram = {k: {**v, "RAM_GB": 0} for k, v in DEFAULT_INSTANCES.items()}
    with pytest.raises(InfeasibleError):
        run_scenario_01(instances=no_ram)


def test_negative_demand_rejected():
    with pytest.raises(ValueError):
        run_scenario_01(required_vcpus=-1)
