# scenario_14.py
import math
from pulp import *

def run_scenario_14(results_list):
    print("--- Running Scenario 14: Governance Financial ---")
    
    model = LpProblem("Scenario_14_Governance", LpMinimize)

    # --- 1. INPUTS ---
    HOURS_IN_3_YEARS = 26280
    MAX_CAPEX = 40000
    MIN_AZURE_PERCENT = 0.30
    REQUIRED_VCPU = 400
    REQUIRED_RAM = 3200

    instances = {
        "AWS_R6_RI_3YR": {"cost": 0.08, "upfront": 1800, "vCPU": 4, "RAM_GB": 32, "prov": "AWS", "type": "RI"},
        "AWS_R6_OD":     {"cost": 0.16, "upfront": 0,    "vCPU": 4, "RAM_GB": 32, "prov": "AWS", "type": "OD"},
        "AZR_M4_RI_3YR": {"cost": 0.10, "upfront": 2200, "vCPU": 4, "RAM_GB": 32, "prov": "Azure", "type": "RI"},
        "AZR_M4_OD":     {"cost": 0.20, "upfront": 0,    "vCPU": 4, "RAM_GB": 32, "prov": "Azure", "type": "OD"},
    }

    # --- 2. HEURISTIC BASELINE ("Compliance via OD") ---
    # Strategy: Meet 30% Azure rule using OD. Meet rest with AWS OD. No RIs.
    min_azure_vcpu = REQUIRED_VCPU * MIN_AZURE_PERCENT
    # Azure OD
    num_azure = math.ceil(min_azure_vcpu / instances["AZR_M4_OD"]["vCPU"])
    cost_azure = num_azure * (instances["AZR_M4_OD"]["cost"] * HOURS_IN_3_YEARS)

    # AWS OD
    remaining = REQUIRED_VCPU - (num_azure * instances["AZR_M4_OD"]["vCPU"])
    num_aws = math.ceil(remaining / instances["AWS_R6_OD"]["vCPU"])
    cost_aws = num_aws * (instances["AWS_R6_OD"]["cost"] * HOURS_IN_3_YEARS)

    heuristic_tco = cost_azure + cost_aws

    # --- 3. OPTIMIZATION ---
    instance_vars = LpVariable.dicts("Num_Instances", instances.keys(), lowBound=0, cat=LpInteger)

    model += lpSum([
        instances[i]['upfront'] * instance_vars[i] +
        instances[i]['cost'] * instance_vars[i] * HOURS_IN_3_YEARS
        for i in instances
    ])

    # Constraints
    model += lpSum([instances[i]['vCPU'] * instance_vars[i] for i in instances]) >= REQUIRED_VCPU
    model += lpSum([instances[i]['RAM_GB'] * instance_vars[i] for i in instances]) >= REQUIRED_RAM
    model += lpSum([instances[i]['upfront'] * instance_vars[i] for i in instances]) <= MAX_CAPEX

    model += lpSum([
        instances[i]['vCPU'] * instance_vars[i]
        for i in instances if instances[i]['prov'] == "Azure"
    ]) >= min_azure_vcpu

    model.solve(PULP_CBC_CMD(msg=0))
    optimized_tco = value(model.objective)
    savings = heuristic_tco - optimized_tco
    savings_pct = (savings / heuristic_tco) * 100

    # --- 4. OUTPUT ---
    print(f"1. Heuristic (Compliance via OD): ${heuristic_tco:,.2f}")
    print(f"2. Optimization (RI + Compliance):${optimized_tco:,.2f}")
    print(f"   >> SAVINGS:                    ${savings:,.2f} ({savings_pct:.1f}%)")

    final_capex = 0
    final_azure_vcpu = 0
    for v in model.variables():
        if v.varValue > 0:
            name = v.name.replace('Num_Instances_', '')
            count = int(v.varValue)
            data = instances[name]

            final_capex += data['upfront'] * count
            if data['prov'] == 'Azure': final_azure_vcpu += data['vCPU'] * count

            results_list.append({
                "Scenario": "Scenario 14: Governance",
                "Status": LpStatus[model.status],
                "Overall_Cost": optimized_tco,
                "Baseline_Heuristic_Cost": heuristic_tco,
                "Savings_Amount": savings,
                "Savings_Percent": savings_pct,
                "Instance_Type": name,
                "Provider": data['prov'],
                "Number_of_Instances": count,
                "Hourly_Cost": data['cost'],
                "Upfront_Cost": data['upfront'],
                "Total_Instance_TCO": (data['upfront'] + data['cost'] * HOURS_IN_3_YEARS) * count,
                "vCPU_Per_Instance": data['vCPU'],
                "Total_Instance_vCPU": data['vCPU'] * count,
                "Scenario_CAPEX_Limit": MAX_CAPEX,
                "Scenario_CAPEX_Spent": final_capex,
                "Scenario_Min_Azure_VCPU_Rule": min_azure_vcpu,
                "Scenario_Azure_VCPU_Provided": final_azure_vcpu
            })
    print("Scenario 14 results captured.\n")