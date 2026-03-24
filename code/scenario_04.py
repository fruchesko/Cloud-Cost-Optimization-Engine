# scenario_04.py
import math
from pulp import *

def run_scenario_04(results_list):
    print("--- Running Scenario 4: Right Sizing ---")
    
    model = LpProblem("Scenario_04_Right_Sizing", LpMinimize)

    # --- 1. INPUTS ---
    REQUIRED_VCPUS = 160
    REQUIRED_RAM_GB = 320 # Ratio 1:2 (Compute Heavy)

    instances = {
        "M5_General":  {"cost": 0.192, "vCPU": 4, "RAM_GB": 16, "type": "General"},
        "C5_Compute":  {"cost": 0.170, "vCPU": 4, "RAM_GB": 8,  "type": "Compute"},
    }

    # --- 2. HEURISTIC BASELINE ---
    # Baseline: Standardized selection on General Purpose (M5) instances.
    heuristic_instance = instances["M5_General"]
    num_needed_vcpu = math.ceil(REQUIRED_VCPUS / heuristic_instance["vCPU"])
    num_needed_ram = math.ceil(REQUIRED_RAM_GB / heuristic_instance["RAM_GB"])
    num_instances_needed = max(num_needed_vcpu, num_needed_ram)
    heuristic_hourly_cost = num_instances_needed * heuristic_instance["cost"]

    # --- 3. OPTIMIZATION ---
    instance_vars = LpVariable.dicts("Num_Instances", instances.keys(), lowBound=0, cat=LpInteger)

    model += lpSum([instances[i]['cost'] * instance_vars[i] for i in instances])
    model += lpSum([instances[i]['vCPU'] * instance_vars[i] for i in instances]) >= REQUIRED_VCPUS
    model += lpSum([instances[i]['RAM_GB'] * instance_vars[i] for i in instances]) >= REQUIRED_RAM_GB

    model.solve(PULP_CBC_CMD(msg=0))
    optimized_hourly_cost = value(model.objective)
    savings = heuristic_hourly_cost - optimized_hourly_cost
    savings_pct = (savings / heuristic_hourly_cost) * 100

    # --- 4. OUTPUT & EXPORT ---
    print(f"1. Heuristic (General Purpose):  ${heuristic_hourly_cost:,.2f}/hr")
    print(f"2. Optimization (Right Fit):     ${optimized_hourly_cost:,.2f}/hr")
    print(f"   >> SAVINGS:                   ${savings:,.2f} ({savings_pct:.1f}%)")

    for v in model.variables():
        if v.varValue > 0:
            name = v.name.replace('Num_Instances_', '')
            count = int(v.varValue)
            data = instances[name]

            results_list.append({
                "Scenario": "Scenario 4: Right Sizing",
                "Status": LpStatus[model.status],
                "Overall_Cost": optimized_hourly_cost,
                "Baseline_Heuristic_Cost": heuristic_hourly_cost,
                "Savings_Amount": savings,
                "Savings_Percent": savings_pct,
                "Instance_Type": name,
                "Provider": "AWS",
                "Number_of_Instances": count,
                "Total_Instance_TCO": data['cost'] * count,
                "vCPU_Per_Instance": data['vCPU'],
                "Total_Instance_vCPU": data['vCPU'] * count
            })
    print("Scenario 4 results captured.\n")