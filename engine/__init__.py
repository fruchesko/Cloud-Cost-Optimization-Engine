"""Parameterised versions of the thesis optimisation scenarios.

Each ``run_scenario_XX`` takes its inputs as keyword arguments (thesis values
are the defaults) and returns a ScenarioResult. The original scripts in
``code/`` are kept unchanged as the thesis record.
"""

from ._common import ConstraintCheck, InfeasibleError, ScenarioResult
from .scenario_01 import run as run_scenario_01
from .scenario_15 import run as run_scenario_15

__all__ = [
    "ConstraintCheck",
    "InfeasibleError",
    "ScenarioResult",
    "run_scenario_01",
    "run_scenario_15",
]
