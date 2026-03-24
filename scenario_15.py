# scenario_15.py
import math
from pulp import *

def run_scenario_15(results_list):
    print("--- Running Scenario 15: Master Optimization ---")
    
    model = LpProblem("Scenario_15_Master", LpMinimize)

    # --- 1. INPUTS ---
    HOURS_IN_3_YEARS = 26280
    MAX_CAPEX = 45000
    MAX_SPOT_PCT = 0.15
    MIN_AZURE_PCT = 0.35
    REQUIRED_VCPU = 500
    REQUIRED_RAM = 2000
    REQUIRED_IOPS = 15000

    instances = {
        "AWS_R6_RI":  {"cost": 0.080, "upfront": 1800, "vCPU": 4, "RAM": 32, "IOPS": 200, "spot": False, "prov": "AWS"},
        "AWS_M6_OD":  {"cost": 0.160, "upfront": 0,    "vCPU": 4, "RAM": 16, "IOPS": 100, "spot": False, "prov": "AWS"},
        "AWS_C7_Spot":{"cost": 0.015, "upfront": 0,    "vCPU": 8, "RAM": 16, "IOPS": 150, "spot": True,  "prov": "AWS"},
        "AZR_E4_RI":  {"cost": 0.095, "upfront": 2200, "vCPU": 4, "RAM": 64, "IOPS": 150, "spot": False, "prov": "Azure"},
        "AZR_E4_OD":  {"cost": 0.190, "upfront": 0,    "vCPU": 4, "RAM": 32, "IOPS": 120, "spot": False, "prov": "Azure"},
        "AZR_D2_Spot":{"cost": 0.020, "upfront": 0,    "vCPU": 2, "RAM": 8,  "IOPS": 50,  "spot": True,  "prov": "Azure"},
    }

    # --- 2. HEURISTIC BASELINE ("Siloed Compliance") ---
    # Strategy: Meet Azure (35%) via Azure OD. Meet rest via AWS RIs (up to budget). No Spot.
    min_azure = REQUIRED_VCPU * MIN_AZURE_PCT

    # Azure Part (OD)
    num_azure = math.ceil(min_azure / instances["AZR_E4_OD"]["vCPU"])
    cost_azure = num_azure * (instances["AZR_E4_OD"]["cost"] * HOURS_IN_3_YEARS)

    # AWS Part (RIs then OD)
    rem_vcpu = REQUIRED_VCPU - (num_azure * instances["AZR_E4_OD"]["vCPU"])
    aws_ri = instances["AWS_R6_RI"]
    max_ris = int(MAX_CAPEX // aws_ri["upfront"])
    needed_aws = math.ceil(rem_vcpu / aws_ri["vCPU"])
    num_ris = min(max_ris, needed_aws)

    cost_aws_ri = num_ris * (aws_ri["upfront"] + aws_ri["cost"] * HOURS_IN_3_YEARS)

    # AWS OD (if budget ran out)
    covered = num_ris * aws_ri["vCPU"]
    rem_final = max(0, rem_vcpu - covered)
    num_od = math.ceil(rem_final / instances["AWS_M6_OD"]["vCPU"])
    cost_aws_od = num_od * (instances["AWS_M6_OD"]["cost"] * HOURS_IN_3_YEARS)

    heuristic_tco = cost_azure + cost_aws_ri + cost_aws_od

    # --- 3. OPTIMIZATION ---
    instance_vars = LpVariable.dicts("Num_Instances", instances.keys(), lowBound=0, cat=LpInteger)

    model += lpSum([
        instances[i]['upfront'] * instance_vars[i] +
        instances[i]['cost'] * instance_vars[i] * HOURS_IN_3_YEARS
        for i in instances
    ])

    # Constraints
    model += lpSum([instances[i]['vCPU'] * instance_vars[i] for i in instances]) >= REQUIRED_VCPU
    model += lpSum([instances[i]['RAM'] * instance_vars[i] for i in instances]) >= REQUIRED_RAM
    model += lpSum([instances[i]['IOPS'] * instance_vars[i] for i in instances]) >= REQUIRED_IOPS
    model += lpSum([instances[i]['upfront'] * instance_vars[i] for i in instances]) <= MAX_CAPEX

    model += lpSum([
        instances[i]['vCPU'] * instance_vars[i]
        for i in instances if instances[i]['prov'] == "Azure"
    ]) >= min_azure

    max_spot = REQUIRED_VCPU * MAX_SPOT_PCT
    model += lpSum([
        instances[i]['vCPU'] * instance_vars[i]
        for i in instances if instances[i]['spot']
    ]) <= max_spot

    model.solve(PULP_CBC_CMD(msg=0))
    optimized_tco = value(model.objective)
    savings = heuristic_tco - optimized_tco
    savings_pct = (savings / heuristic_tco) * 100

    # --- 4. OUTPUT ---
    print(f"1. Heuristic (Siloed):           ${heuristic_tco:,.2f}")
    print(f"2. Optimization (Master):        ${optimized_tco:,.2f}")
    print(f"   >> SAVINGS:                   ${savings:,.2f} ({savings_pct:.1f}%)")

    final_capex = 0
    final_spot = 0
    final_azure = 0
    for v in model.variables():
        if v.varValue > 0:
            name = v.name.replace('Num_Instances_', '')
            count = int(v.varValue)
            data = instances[name]

            final_capex += data['upfront'] * count
            if data['spot']: final_spot += data['vCPU'] * count
            if data['prov'] == 'Azure': final_azure += data['vCPU'] * count

            results_list.append({
                "Scenario": "Scenario 15: Master Optimization",
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
                "Scenario_Max_Spot_VCPU_Allowed": max_spot,
                "Scenario_Total_Spot_VCPU_Utilized": final_spot,
                "Scenario_Min_Azure_VCPU_Rule": min_azure,
                "Scenario_Azure_VCPU_Provided": final_azure
            })
    print("Scenario 15 results captured.\n")