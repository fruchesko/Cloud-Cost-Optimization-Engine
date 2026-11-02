import pytest

from engine import InfeasibleError, run_scenario_13
from engine.scenario_13 import DEFAULT_TIERS


def test_defaults_match_thesis():
    r = run_scenario_13()
    assert r.status == "Optimal"
    assert r.heuristic_cost == pytest.approx(8_875.00, abs=0.005)
    assert r.optimal_cost == pytest.approx(3_310.34, abs=0.005)
    assert r.savings == pytest.approx(5_564.66, abs=0.005)
    assert round(r.savings_pct, 1) == 62.7


def test_defaults_allocation_and_binding_constraints():
    r = run_scenario_13()
    assert set(r.instances) == {"Hot_Standard", "Archive_Glacier"}
    assert r.instances["Archive_Glacier"] == pytest.approx(431_034.48, abs=0.01)
    assert r.instances["Hot_Standard"] == pytest.approx(68_965.52, abs=0.01)
    assert {"Volume_demand", "IOPS_demand"} <= set(r.binding_constraints)
    assert "CAPEX_budget" not in r.binding_constraints
    assert r.extras["baseline_capex"] == pytest.approx(112_500)
    assert r.extras["optimal_capex"] == pytest.approx(28_448.28, abs=0.01)


def test_matches_original_script():
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "code"))
    import scenario_13 as original
    rows = []
    original.run_scenario_13(rows)
    assert run_scenario_13().optimal_cost == pytest.approx(rows[0]["Overall_Cost"])


def test_tight_budget_raises_cost():
    # Reaching 25,000 IOPS costs at least $25,000 of migration; $26,000 forces a pricier mix.
    assert run_scenario_13(max_capex=26_000).optimal_cost > run_scenario_13().optimal_cost


def test_archive_only_overprovisions_to_meet_iops():
    # Volume is a minimum, so archive-only meets IOPS by storing 2.5M GB.
    r = run_scenario_13(tiers={"Archive_Glacier": DEFAULT_TIERS["Archive_Glacier"]},
                        baseline_tiers=DEFAULT_TIERS)
    assert r.instances["Archive_Glacier"] == pytest.approx(2_500_000)


def test_archive_only_with_small_budget_is_infeasible():
    with pytest.raises(InfeasibleError):
        run_scenario_13(tiers={"Archive_Glacier": DEFAULT_TIERS["Archive_Glacier"]}, max_capex=20_000)


def test_budget_too_small_for_iops_is_infeasible():
    # 25,000 IOPS needs at least ~29k of hot-tier migration capex.
    with pytest.raises(InfeasibleError):
        run_scenario_13(max_capex=5_000)


def test_negative_inputs_rejected():
    with pytest.raises(ValueError):
        run_scenario_13(required_iops=-1)
