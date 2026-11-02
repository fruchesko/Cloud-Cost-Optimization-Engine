import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.scenarios import SCENARIOS

client = TestClient(main.app)


def solve(scenario, **params):
    return client.post("/solve", json={"scenario": scenario, "params": params})


def test_page_and_health():
    assert client.get("/health").json() == {"status": "ok"}
    page = client.get("/")
    assert page.status_code == 200 and "<title>Cost Optimization Engine</title>" in page.text


def test_scenarios_lists_parameters_with_ranges_and_defaults():
    body = client.get("/scenarios").json()
    assert body["solver_timeout_seconds"] > 0
    by_id = {s["id"]: s for s in body["scenarios"]}
    assert set(by_id) == set(SCENARIOS)
    params = {p["name"]: p for p in by_id["scenario_15"]["parameters"]}
    assert params["max_capex"]["default"] == 45000
    assert params["max_spot_pct"]["min"] == 0 and params["max_spot_pct"]["max"] == 1
    assert params["allowed_instances"]["kind"] == "multi"


def test_scenario_15_defaults_match_thesis():
    r = client.post("/solve", json={"scenario": "scenario_15"})
    assert r.status_code == 200
    body = r.json()
    assert body["savings"] == pytest.approx(72_138.60, abs=0.005)
    assert round(body["savings_pct"], 1) == 13.1
    assert body["heuristic_cost"] == pytest.approx(552_729.60, abs=0.005)
    assert body["optimal_cost"] == pytest.approx(480_591.00, abs=0.005)
    assert {"vCPU_demand", "CAPEX_budget"} <= set(body["binding_constraints"])
    counts = {x["name"]: x["count"] for x in body["resources"]}
    assert sum(x["total_cost"] for x in body["resources"]) == pytest.approx(body["optimal_cost"])
    assert counts and all(n > 0 for n in counts.values())


def test_scenario_01_defaults_match_engine():
    from engine import run_scenario_01
    body = solve("scenario_01").json()
    assert body["savings"] == pytest.approx(run_scenario_01().savings)


def test_parameters_change_the_result():
    looser = solve("scenario_15", max_capex=90_000).json()
    assert looser["optimal_cost"] <= 480_591.00


@pytest.mark.parametrize("params", [
    {"max_spot_pct": 1.5},
    {"min_azure_pct": -0.1},
    {"required_vcpu": 0},
    {"required_vcpu": 10**9},
    {"max_capex": -1},
    {"hours": 10},
    {"required_vcpu": "lots"},
    {"not_a_parameter": 1},
    {"allowed_instances": []},
    {"allowed_instances": ["NOT_AN_INSTANCE"]},
])
def test_out_of_range_or_unknown_parameters_are_rejected(params):
    r = solve("scenario_15", **params)
    assert r.status_code == 422
    assert isinstance(r.json()["detail"], list)


def test_unknown_scenario_is_rejected():
    assert client.post("/solve", json={"scenario": "scenario_99"}).status_code == 422


def test_scenario_1_rejects_unknown_baseline_instance():
    assert solve("scenario_01", heuristic_instance="Nope").status_code == 422


@pytest.mark.parametrize("params", [
    # Azure share required, but only AWS types allowed.
    {"allowed_instances": ["AWS_R6_RI", "AWS_M6_OD", "AWS_C7_Spot"]},
    # Only Reserved types allowed, with no upfront budget.
    {"allowed_instances": ["AWS_R6_RI", "AZR_E4_RI"], "max_capex": 0},
    # Only Spot types allowed, with Spot capped at 15%.
    {"allowed_instances": ["AWS_C7_Spot", "AZR_D2_Spot"]},
])
def test_infeasible_inputs_get_a_clear_message(params):
    r = solve("scenario_15", **params)
    assert r.status_code == 422
    body = r.json()
    assert body["error"] == "infeasible"
    assert "No allocation meets every constraint" in body["message"]


def test_restricting_instance_types_keeps_the_thesis_baseline():
    body = solve("scenario_15", allowed_instances=["AWS_M6_OD", "AZR_E4_OD"]).json()
    assert body["heuristic_cost"] == pytest.approx(552_729.60, abs=0.005)
    assert {x["name"] for x in body["resources"]} <= {"AWS_M6_OD", "AZR_E4_OD"}
    assert body["optimal_cost"] > 480_591.00


def test_solver_timeout_returns_504(monkeypatch):
    monkeypatch.setattr(main, "SOLVER_TIMEOUT", 0.001)
    r = solve("scenario_15")
    assert r.status_code == 504
    assert r.json()["error"] == "timeout"
