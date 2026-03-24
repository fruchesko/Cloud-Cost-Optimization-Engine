# scenario_02.py
import math
from pulp import *

def run_scenario_02(results_list):
    print("--- Running Scenario 2: Budget Constrained ---")
    
    model = LpProblem("Scenario_02_Budget_Constrained", LpMinimize)

    # --- 1. INPUTS ---
    HOURS_IN_3_YEARS = 26280
    MAX_CAPEX_BUDGET = 10000
    REQUIRED_VCPUS = 100

    instances = {
        "Instance_OD":      {"cost": 0.150, "upfront": 0,    "vCPU": 4, "type": "OD"},
        "Instance_RI_3YR":  {"cost": 0.060, "upfront": 1500, "vCPU": 4, "type": "RI-3YR"},
    }

    # --- 2. HEURISTIC BASELINE ---
    # Strategy: Zero upfront budget available -> Buy all On-Demand.
    heuristic_instance = instances["Instance_OD"]
    num_instances_needed = math.ceil(REQUIRED_VCPUS / heuristic_instance["vCPU"])
    heuristic_tco = num_instances_needed * (heuristic_instance["upfront"] + heuristic_instance["cost"] * HOURS_IN_3_YEARS)

    # --- 3. OPTIMIZATION ---
    instance_vars = LpVariable.dicts("Num_Instances", instances.keys(), lowBound=0, cat=LpInteger)

    model += lpSum([
        instances[i]['upfront'] * instance_vars[i] +
        instances[i]['cost'] * instance_vars[i] * HOURS_IN_3_YEARS
        for i in instances
    ])

    model += lpSum([instances[i]['vCPU'] * instance_vars[i] for i in instances]) >= REQUIRED_VCPUS
    model += lpSum([instances[i]['upfront'] * instance_vars[i] for i in instances]) <= MAX_CAPEX_BUDGET

    model.solve(PULP_CBC_CMD(msg=0))
    optimized_tco = value(model.objective)
    savings = heuristic_tco - optimized_tco
    savings_pct = (savings / heuristic_tco) * 100

    # --- 4. OUTPUT & EXPORT ---
    print(f"1. Heuristic (All OD):           ${heuristic_tco:,.2f}")
    print(f"2. Optimization (Budget Fit):    ${optimized_tco:,.2f}")
    print(f"   >> SAVINGS:                   ${savings:,.2f} ({savings_pct:.1f}%)")

    final_capex = 0
    for v in model.variables():
        if v.varValue > 0:
            name = v.name.replace('Num_Instances_', '')
            count = int(v.varValue)
            data = instances[name]
            final_capex += data['upfront'] * count

            results_list.append({
                "Scenario": "Scenario 2: Budget Constrained",
                "Status": LpStatus[model.status],
                "Overall_Cost": optimized_tco,
                "Baseline_Heuristic_Cost": heuristic_tco,
                "Savings_Amount": savings,
                "Savings_Percent": savings_pct,
                "Instance_Type": name,
                "Provider": "AWS",
                "Number_of_Instances": count,
                "Total_Instance_TCO": (data['upfront'] + data['cost'] * HOURS_IN_3_YEARS) * count,
                "Scenario_CAPEX_Limit": MAX_CAPEX_BUDGET,
                "Scenario_CAPEX_Spent": final_capex
            })
    print(" Scenario 2 results captured.\n")