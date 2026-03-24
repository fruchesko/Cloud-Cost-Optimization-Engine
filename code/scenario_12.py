# scenario_12.py
import math
from pulp import *

def run_scenario_12(results_list):
    print("--- Running Scenario 12: Risk Averse Architect ---")
    
    model = LpProblem("Scenario_12_Risk_Averse", LpMinimize)

    # --- 1. INPUTS ---
    HOURS_PER_WEEK = 168
    MAX_SPOT_PERCENT = 0.05
    REQUIRED_VCPU = 300
    REQUIRED_RAM = 1024
    REQUIRED_IOPS = 12000

    instances = {
        "P_Heavy_RI":     {"cost": 0.18,  "vCPU": 8, "RAM_GB": 64, "IOPS": 500, "is_spot": False, "type": "HighPerf"},
        "G_Mid_OD":       {"cost": 0.12,  "vCPU": 4, "RAM_GB": 16, "IOPS": 100, "is_spot": False, "type": "GenPurp"},
        "C_Lite_OD":      {"cost": 0.08,  "vCPU": 2, "RAM_GB": 4,  "IOPS": 50,  "is_spot": False, "type": "Compute"},
        "S_LowRisk_Spot": {"cost": 0.015, "vCPU": 2, "RAM_GB": 8,  "IOPS": 120, "is_spot": True,  "type": "Spot"},
    }

    # --- 2. HEURISTIC BASELINE ("Performance Safety") ---
    # Strategy: Buy expensive P_Heavy_RI to guarantee IOPS.
    heuristic_instance = instances["P_Heavy_RI"]
    num_needed = math.ceil(REQUIRED_VCPU / heuristic_instance["vCPU"])
    heuristic_cost = num_needed * heuristic_instance["cost"]

    # --- 3. OPTIMIZATION ---
    instance_vars = LpVariable.dicts("Num_Instances", instances.keys(), lowBound=0, cat=LpInteger)

    model += lpSum([instances[i]['cost'] * instance_vars[i] for i in instances])

    # Constraints
    model += lpSum([instances[i]['vCPU'] * instance_vars[i] for i in instances]) >= REQUIRED_VCPU
    model += lpSum([instances[i]['RAM_GB'] * instance_vars[i] for i in instances]) >= REQUIRED_RAM
    model += lpSum([instances[i]['IOPS'] * instance_vars[i] for i in instances]) >= REQUIRED_IOPS

    max_spot = REQUIRED_VCPU * MAX_SPOT_PERCENT
    model += lpSum([
        instances[i]['vCPU'] * instance_vars[i]
        for i in instances if instances[i]['is_spot']
    ]) <= max_spot

    model.solve(PULP_CBC_CMD(msg=0))
    optimized_cost = value(model.objective)
    savings = heuristic_cost - optimized_cost
    savings_pct = (savings / heuristic_cost) * 100

    # --- 4. OUTPUT ---
    print(f"1. Heuristic (High Perf Only):   ${heuristic_cost:,.2f}/hr")
    print(f"2. Optimization (Balanced):      ${optimized_cost:,.2f}/hr")
    print(f"   >> SAVINGS:                   ${savings:,.2f} ({savings_pct:.1f}%)")

    final_iops = 0
    final_spot = 0
    for v in model.variables():
        if v.varValue > 0:
            name = v.name.replace('Num_Instances_', '')
            count = int(v.varValue)
            data = instances[name]

            final_iops += data['IOPS'] * count
            if data['is_spot']: final_spot += data['vCPU'] * count

            results_list.append({
                "Scenario": "Scenario 12: Risk Averse Architect",
                "Status": LpStatus[model.status],
                "Overall_Cost": optimized_cost,
                "Baseline_Heuristic_Cost": heuristic_cost,
                "Savings_Amount": savings,
                "Savings_Percent": savings_pct,
                "Instance_Type": name,
                "Provider": "N/A",
                "Number_of_Instances": count,
                "Hourly_Cost": data['cost'],
                "Total_Instance_TCO": data['cost'] * count,
                "vCPU_Per_Instance": data['vCPU'],
                "Total_Instance_vCPU": data['vCPU'] * count,
                "IOPS_Per_Instance": data['IOPS'],
                "Total_Instance_IOPS": data['IOPS'] * count,
                "Scenario_Min_IOPS_Limit": REQUIRED_IOPS,
                "Scenario_Max_Spot_VCPU_Allowed": max_spot,
                "Scenario_Total_Spot_VCPU_Utilized": final_spot
            })
    print("Scenario 12 results captured.\n")