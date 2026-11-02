"""Run one scenario solve and print the result as JSON.

The API starts this as a separate process per request so a slow solve can be
killed (with the CBC solver it launches) when it exceeds the timeout.

stdin:  {"scenario": "scenario_15", "params": {...}}   (already validated)
stdout: {"ok": true, "result": {...}} or {"ok": false, "error": "...", "message": "..."}
"""

from __future__ import annotations

import json
import sys
import time

from engine import InfeasibleError
from engine._common import tco

from .scenarios import ALLOWED, SCENARIOS


_PRICING = {"OD": "On-Demand", "RI-1YR": "Reserved 1-yr", "RI-3YR": "Reserved 3-yr"}


def _pricing(spec: dict) -> str:
    if "type" in spec:
        return _PRICING.get(spec["type"], spec["type"])
    if spec.get("spot"):
        return "Spot"
    return "Reserved" if spec["upfront"] else "On-Demand"


def solve(scenario_id: str, params: dict) -> dict:
    s = SCENARIOS[scenario_id]
    params = dict(params)
    allowed = list(dict.fromkeys(params.pop(ALLOWED, None) or s.instances))
    hours = params.get("hours")
    start = time.perf_counter()
    # The optimum may only use the allowed types; the baseline keeps the full
    # catalogue (its rule names specific types), so it stays the thesis baseline.
    r = s.run(**params, instances={i: s.instances[i] for i in allowed},
              baseline_instances=s.instances)
    elapsed_ms = (time.perf_counter() - start) * 1000

    resources = []
    for name, count in sorted(r.instances.items(), key=lambda kv: -tco(s.instances[kv[0]], kv[1], hours)):
        spec = s.instances[name]
        resources.append({
            "name": name,
            "count": count,
            "provider": spec.get("prov"),
            "type": _pricing(spec),
            "vcpu_each": spec["vCPU"],
            "ram_gb_each": spec.get("RAM", spec.get("RAM_GB")),
            "hourly_each": spec["cost"],
            "upfront_each": spec["upfront"],
            "total_cost": tco(spec, count, hours),
        })

    return {
        "scenario": s.id,
        "name": r.scenario,
        "status": r.status,
        "heuristic_cost": r.heuristic_cost,
        "optimal_cost": r.optimal_cost,
        "savings": r.savings,
        "savings_pct": r.savings_pct,
        "resources": resources,
        "constraints": [
            {"name": n, "lhs": c.lhs, "sense": c.sense, "rhs": c.rhs,
             "slack": c.slack, "binding": c.binding}
            for n, c in r.constraints.items()
        ],
        "binding_constraints": r.binding_constraints,
        "allowed_instances": allowed,
        "solve_ms": round(elapsed_ms, 1),
    }


def main() -> None:
    req = json.load(sys.stdin)
    try:
        out = {"ok": True, "result": solve(req["scenario"], req["params"])}
    except InfeasibleError as e:
        out = {"ok": False, "error": "infeasible", "message": str(e), "solver_status": e.status}
    except ValueError as e:
        out = {"ok": False, "error": "invalid", "message": str(e)}
    json.dump(out, sys.stdout)


if __name__ == "__main__":
    main()
