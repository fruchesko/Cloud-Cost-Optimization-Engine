"""Check the engine ports reproduce the original code/ scripts exactly."""

import importlib.util
from pathlib import Path

import pytest

import engine

CODE_DIR = Path(__file__).resolve().parent.parent / "code"


def _load(module_name):
    spec = importlib.util.spec_from_file_location(module_name, CODE_DIR / f"{module_name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "script, port",
    [("scenario_01", engine.run_scenario_01), ("scenario_15", engine.run_scenario_15)],
)
def test_port_matches_original(script, port):
    rows = []
    getattr(_load(script), f"run_{script}")(rows)
    r = port()

    assert rows[0]["Baseline_Heuristic_Cost"] == pytest.approx(r.heuristic_cost)
    assert rows[0]["Overall_Cost"] == pytest.approx(r.optimal_cost)
    assert rows[0]["Savings_Amount"] == pytest.approx(r.savings)
    assert {row["Instance_Type"]: row["Number_of_Instances"] for row in rows} == r.instances
