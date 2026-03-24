# scenario_01.py
import math
from pulp import *

def run_scenario_01(results_list):
    print("--- Running Scenario 1: Rate Optimization ---")
    
    model = LpProblem("Scenario_01_Rate_Optimization", LpMinimize)

    # --- 1. INPUTS ---
    HOURS_IN_3_YEARS = 26280
    REQUIRED_VCPUS = 100
    REQUIRED_RAM_GB = 400

    instances = {
        "Instance_OD":      {"cost": 0.150, "upfront": 0,    "vCPU": 4, "RAM_GB": 16, "type": "OD"},
        "Instance_RI_1YR":  {"cost": 0.090, "upfront": 800,  "vCPU": 4, "RAM_GB": 16, "type": "RI-1YR"},
        "Instance_RI_3YR":  {"cost": 0.060, "upfront": 1500, "vCPU": 4, "RAM_GB": 16, "type": "RI-3YR"},
    }

    # --- 2. HEURISTIC BASELINE ---
    # Strategy: 100% coverage using 1-Year RIs (cautious approach).
    heuristic_instance = instances["Instance_RI_1YR"]
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
    model += lpSum([instances[i]['RAM_GB'] * instance_vars[i] for i in instances]) >= REQUIRED_RAM_GB

    model.solve(PULP_CBC_CMD(msg=0)) # msg=0 keeps the console clean
    optimized_tco = value(model.objective)
    savings = heuristic_tco - optimized_tco
    savings_pct = (savings / heuristic_tco) * 100

    # --- 4. OUTPUT & EXPORT ---
    print(f"1. Heuristic (All 1-Year RIs):   ${heuristic_tco:,.2f}")
    print(f"2. Optimization (Best Mix):      ${optimized_tco:,.2f}")
    print(f"   >> SAVINGS:                   ${savings:,.2f} ({savings_pct:.1f}%)")

    # Use the injected results_list instead of checking locals()
    for v in model.variables():
        if v.varValue > 0:
            name = v.name.replace('Num_Instances_', '')
            count = int(v.varValue)
            data = instances[name]

            results_list.append({
                "Scenario": "Scenario 1: Rate Optimization",
                "Status": LpStatus[model.status],
                "Overall_Cost": optimized_tco,
                "Baseline_Heuristic_Cost": heuristic_tco,
                "Savings_Amount": savings,
                "Savings_Percent": savings_pct,
                "Instance_Type": name,
                "Provider": "AWS",
                "Number_of_Instances": count,
                "Total_Instance_TCO": (data['upfront'] + data['cost'] * HOURS_IN_3_YEARS) * count,
                "Scenario_Required_VCPU": REQUIRED_VCPUS
            })
            
    print("Scenario 1 results captured.\n")