# scenario_03.py
import math
from pulp import *

def run_scenario_03(results_list):
    print("--- Running Scenario 3: Spot Risk Management ---")
    
    model = LpProblem("Scenario_03_Spot_Risk", LpMinimize)

    # --- 1. INPUTS ---
    REQUIRED_VCPUS = 200
    MAX_SPOT_PERCENT = 0.20 # 20% Risk Tolerance

    instances = {
        "Instance_OD":   {"cost": 0.120, "vCPU": 4, "is_spot": False, "type": "OD"},
        "Instance_Spot": {"cost": 0.020, "vCPU": 4, "is_spot": True,  "type": "Spot"},
    }

    # --- 2. HEURISTIC BASELINE ---
    # Strategy: Risk averse -> Buy only On-Demand (0% Spot).
    heuristic_instance = instances["Instance_OD"]
    num_instances_needed = math.ceil(REQUIRED_VCPUS / heuristic_instance["vCPU"])
    heuristic_hourly_cost = num_instances_needed * heuristic_instance["cost"]

    # --- 3. OPTIMIZATION ---
    instance_vars = LpVariable.dicts("Num_Instances", instances.keys(), lowBound=0, cat=LpInteger)

    model += lpSum([instances[i]['cost'] * instance_vars[i] for i in instances])

    model += lpSum([instances[i]['vCPU'] * instance_vars[i] for i in instances]) >= REQUIRED_VCPUS
    
    max_spot_vcpus = REQUIRED_VCPUS * MAX_SPOT_PERCENT
    model += lpSum([
        instances[i]['vCPU'] * instance_vars[i]
        for i in instances if instances[i]['is_spot']
    ]) <= max_spot_vcpus

    model.solve(PULP_CBC_CMD(msg=0))
    optimized_hourly_cost = value(model.objective)
    savings = heuristic_hourly_cost - optimized_hourly_cost
    savings_pct = (savings / heuristic_hourly_cost) * 100

    # --- 4. OUTPUT & EXPORT ---
    print(f"1. Heuristic (0% Spot):          ${heuristic_hourly_cost:,.2f}/hr")
    print(f"2. Optimization (20% Spot):      ${optimized_hourly_cost:,.2f}/hr")
    print(f"   >> SAVINGS:                   ${savings:,.2f} ({savings_pct:.1f}%)")

    final_spot_vcpu = 0
    for v in model.variables():
        if v.varValue > 0:
            name = v.name.replace('Num_Instances_', '')
            count = int(v.varValue)
            data = instances[name]

            if data['is_spot']: final_spot_vcpu += data['vCPU'] * count

            results_list.append({
                "Scenario": "Scenario 3: Spot Risk Management",
                "Status": LpStatus[model.status],
                "Overall_Cost": optimized_hourly_cost,
                "Baseline_Heuristic_Cost": heuristic_hourly_cost,
                "Savings_Amount": savings,
                "Savings_Percent": savings_pct,
                "Instance_Type": name,
                "Provider": "AWS",
                "Number_of_Instances": count,
                "Total_Instance_TCO": data['cost'] * count,
                "Is_Spot": data['is_spot'],
                "Scenario_Max_Spot_VCPU_Allowed": max_spot_vcpus,
                "Scenario_Total_Spot_VCPU_Utilized": final_spot_vcpu
            })
    print("Scenario 3 results captured.\n")