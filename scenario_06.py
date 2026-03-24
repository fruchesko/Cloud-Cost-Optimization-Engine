# scenario_06.py
import math
from pulp import *

def run_scenario_06(results_list):
    print("--- Running Scenario 6: Financial Right-Sizing ---")
    
    model = LpProblem("L2_Scenario_6_Financial_Right_Sizing", LpMinimize)

    # --- 1. INPUTS ---
    HOURS_IN_3_YEARS = 26280
    MAX_CAPEX_BUDGET = 25000
    REQUIRED_VCPU = 200
    REQUIRED_RAM_GB = 800

    instances = {
        "C_Opt_RI_3YR":   {"cost": 0.055, "upfront": 1800, "vCPU": 8, "RAM_GB": 16, "type": "RI"},
        "R_Opt_RI_1YR":   {"cost": 0.120, "upfront": 750,  "vCPU": 4, "RAM_GB": 32, "type": "RI"},
        "G_Purp_OD":      {"cost": 0.200, "upfront": 0,    "vCPU": 4, "RAM_GB": 16, "type": "OD"},
    }

    # --- 2. HEURISTIC BASELINE ---
    # Baseline: Avoid CAPEX complexity -> Buy flexible On-Demand instances.
    heuristic_instance = instances["G_Purp_OD"]
    needed_for_vcpu = REQUIRED_VCPU / heuristic_instance["vCPU"]
    needed_for_ram = REQUIRED_RAM_GB / heuristic_instance["RAM_GB"]
    heuristic_count = max(needed_for_vcpu, needed_for_ram)
    heuristic_tco = heuristic_count * (heuristic_instance["upfront"] + heuristic_instance["cost"] * HOURS_IN_3_YEARS)

    # --- 3. OPTIMIZATION ---
    instance_vars = LpVariable.dicts("Num_Instances", instances.keys(), lowBound=0, cat=LpInteger)

    model += lpSum([
        instances[i]['upfront'] * instance_vars[i] +
        instances[i]['cost'] * instance_vars[i] * HOURS_IN_3_YEARS
        for i in instances
    ])

    model += lpSum([instances[i]['vCPU'] * instance_vars[i] for i in instances]) >= REQUIRED_VCPU
    model += lpSum([instances[i]['RAM_GB'] * instance_vars[i] for i in instances]) >= REQUIRED_RAM_GB
    model += lpSum([instances[i]['upfront'] * instance_vars[i] for i in instances]) <= MAX_CAPEX_BUDGET

    model.solve(PULP_CBC_CMD(msg=0))
    optimized_tco = value(model.objective)
    savings = heuristic_tco - optimized_tco
    savings_pct = (savings / heuristic_tco) * 100

    # --- 4. OUTPUT ---
    print(f"1. Heuristic Approach: ${heuristic_tco:,.2f}")
    print(f"2. Optimization Model: ${optimized_tco:,.2f}")
    print(f"   >> SAVINGS:         ${savings:,.2f} ({savings_pct:.1f}%)")

    final_total_capex = 0
    for v in model.variables():
        if v.varValue > 0:
            name = v.name.replace('Num_Instances_', '')
            count = int(v.varValue)
            data = instances[name]
            final_total_capex += data['upfront'] * count

            results_list.append({
                "Scenario": "Scenario 6: Financial Right-Sizing",
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
                "Scenario_CAPEX_Spent": final_total_capex
            })
    print("Scenario 6 results captured.\n")