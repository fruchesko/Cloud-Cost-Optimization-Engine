# scenario_08.py
import math
from pulp import *

def run_scenario_08(results_list):
    print("--- Running Scenario 8: Multi-Cloud Governance ---")
    
    model = LpProblem("L2_Scenario_8_Multi_Cloud_Governance", LpMinimize)

    # --- 1. INPUTS ---
    REQUIRED_VCPU = 300
    REQUIRED_RAM_GB = 1024
    REQUIRED_IOPS = 10000
    MIN_AZURE_VCPU_PERCENT = 0.20

    instances = {
        "AWS_M5_RI":    {"cost": 0.090, "vCPU": 4, "RAM_GB": 16, "iops": 200, "provider": "AWS"},
        "AWS_C5_OD":    {"cost": 0.170, "vCPU": 8, "RAM_GB": 16, "iops": 300, "provider": "AWS"},
        "AZR_D4_RI":    {"cost": 0.110, "vCPU": 4, "RAM_GB": 16, "iops": 250, "provider": "Azure"},
        "AZR_E8_OD":    {"cost": 0.220, "vCPU": 8, "RAM_GB": 64, "iops": 400, "provider": "Azure"},
    }

    # --- 2. HEURISTIC BASELINE ---
    # Baseline: Compliance-via-Least-Effort using OD instances.
    # 1. Azure Part
    azure_vcpu_needed = REQUIRED_VCPU * MIN_AZURE_VCPU_PERCENT
    num_azure_od = math.ceil(azure_vcpu_needed / instances["AZR_E8_OD"]["vCPU"])
    azure_cost = num_azure_od * instances["AZR_E8_OD"]["cost"]

    # 2. AWS Part
    aws_vcpu_needed = max(0, REQUIRED_VCPU - (num_azure_od * instances["AZR_E8_OD"]["vCPU"]))
    num_aws_od = math.ceil(aws_vcpu_needed / instances["AWS_C5_OD"]["vCPU"])
    aws_cost = num_aws_od * instances["AWS_C5_OD"]["cost"]

    heuristic_hourly_cost = azure_cost + aws_cost

    # --- 3. OPTIMIZATION ---
    instance_vars = LpVariable.dicts("Num_Instances", instances.keys(), lowBound=0, cat=LpInteger)

    model += lpSum([instances[i]['cost'] * instance_vars[i] for i in instances])

    model += lpSum([instances[i]['vCPU'] * instance_vars[i] for i in instances]) >= REQUIRED_VCPU
    model += lpSum([instances[i]['RAM_GB'] * instance_vars[i] for i in instances]) >= REQUIRED_RAM_GB
    model += lpSum([instances[i]['iops'] * instance_vars[i] for i in instances]) >= REQUIRED_IOPS

    min_azure_units = REQUIRED_VCPU * MIN_AZURE_VCPU_PERCENT
    model += lpSum([
        instances[i]['vCPU'] * instance_vars[i]
        for i in instances if instances[i]['provider'] == "Azure"
    ]) >= min_azure_units

    model.solve(PULP_CBC_CMD(msg=0))
    optimized_hourly_cost = value(model.objective)
    savings = heuristic_hourly_cost - optimized_hourly_cost
    savings_pct = (savings / heuristic_hourly_cost) * 100

    # --- 4. OUTPUT ---
    print(f"1. Heuristic (Compliance via OD):   ${heuristic_hourly_cost:,.2f}")
    print(f"2. Optimization (Smart RI Mix):     ${optimized_hourly_cost:,.2f}")
    print(f"   >> SAVINGS:                      ${savings:,.2f} ({savings_pct:.1f}%)")

    final_azure_vcpu = 0
    for v in model.variables():
        if v.varValue > 0:
            name = v.name.replace('Num_Instances_', '')
            count = int(v.varValue)
            data = instances[name]

            if data['provider'] == 'Azure': final_azure_vcpu += data['vCPU'] * count

            results_list.append({
                "Scenario": "Scenario 8: Multi-Cloud Governance",
                "Status": LpStatus[model.status],
                "Overall_Cost": optimized_hourly_cost,
                "Baseline_Heuristic_Cost": heuristic_hourly_cost,
                "Savings_Amount": savings,
                "Savings_Percent": savings_pct,
                "Instance_Type": name,
                "Provider": data['provider'],
                "Number_of_Instances": count,
                "Total_Instance_TCO": data['cost'] * count,
                "Scenario_Min_Azure_VCPU_Rule": min_azure_units,
                "Scenario_Azure_VCPU_Provided": final_azure_vcpu
            })
    print("Scenario 8 results captured.\n")