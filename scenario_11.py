# scenario_11.py
import math
from pulp import *

def run_scenario_11(results_list):
    print("--- Running Scenario 11: Budget Multi-Cloud ---")
    
    model = LpProblem("Scenario_11_Budget_Multi_Cloud", LpMinimize)

    # --- 1. INPUTS ---
    HOURS_IN_3_YEARS = 26280
    MAX_CAPEX_BUDGET = 35000
    MAX_SPOT_VCPU_PERCENT = 0.10
    REQUIRED_VCPUS = 350
    REQUIRED_RAM_GB = 1400

    instances = {
        "AWS_M6_RI_3YR": {"cost": 0.070, "upfront": 1600, "vCPU": 4, "RAM_GB": 16, "is_spot": False, "provider": "AWS", "type": "RI"},
        "AWS_M6_OD":     {"cost": 0.150, "upfront": 0,    "vCPU": 4, "RAM_GB": 16, "is_spot": False, "provider": "AWS", "type": "OD"},
        "AWS_T4_Spot":   {"cost": 0.012, "upfront": 0,    "vCPU": 2, "RAM_GB": 8,  "is_spot": True,  "provider": "AWS", "type": "Spot"},
        "AZR_E4_RI_3YR": {"cost": 0.085, "upfront": 1900, "vCPU": 4, "RAM_GB": 16, "is_spot": False, "provider": "Azure", "type": "RI"},
        "AZR_E4_OD":     {"cost": 0.180, "upfront": 0,    "vCPU": 4, "RAM_GB": 16, "is_spot": False, "provider": "Azure", "type": "OD"},
        "AZR_D2_Spot":   {"cost": 0.016, "upfront": 0,    "vCPU": 2, "RAM_GB": 8,  "is_spot": True,  "provider": "Azure", "type": "Spot"},
    }

    # --- 2. HEURISTIC BASELINE ("Single Cloud Safe Strategy") ---
    # Strategy: Stick to AWS. Buy max AWS RIs with budget. Fill gap with AWS OD. No Spot.
    ri_instance = instances["AWS_M6_RI_3YR"]
    od_instance = instances["AWS_M6_OD"]

    # Step A: Buy Max RIs
    max_ris = int(MAX_CAPEX_BUDGET // ri_instance["upfront"])
    needed_total = math.ceil(REQUIRED_VCPUS / ri_instance["vCPU"])
    num_ris = min(max_ris, needed_total)

    # Step B: Fill with OD
    vcpu_covered = num_ris * ri_instance["vCPU"]
    remaining_vcpu = max(0, REQUIRED_VCPUS - vcpu_covered)
    num_ods = math.ceil(remaining_vcpu / od_instance["vCPU"])

    heuristic_tco = (
        (num_ris * (ri_instance["upfront"] + ri_instance["cost"] * HOURS_IN_3_YEARS)) +
        (num_ods * (od_instance["upfront"] + od_instance["cost"] * HOURS_IN_3_YEARS))
    )

    # --- 3. OPTIMIZATION ---
    instance_vars = LpVariable.dicts("Num_Instances", instances.keys(), lowBound=0, cat=LpInteger)

    model += lpSum([
        instances[i]['upfront'] * instance_vars[i] +
        instances[i]['cost'] * instance_vars[i] * HOURS_IN_3_YEARS
        for i in instances
    ])

    # Constraints
    model += lpSum([instances[i]['vCPU'] * instance_vars[i] for i in instances]) >= REQUIRED_VCPUS
    model += lpSum([instances[i]['RAM_GB'] * instance_vars[i] for i in instances]) >= REQUIRED_RAM_GB
    model += lpSum([instances[i]['upfront'] * instance_vars[i] for i in instances]) <= MAX_CAPEX_BUDGET

    # Risk Limit
    max_spot = REQUIRED_VCPUS * MAX_SPOT_VCPU_PERCENT
    model += lpSum([
        instances[i]['vCPU'] * instance_vars[i]
        for i in instances if instances[i]['is_spot']
    ]) <= max_spot

    model.solve(PULP_CBC_CMD(msg=0))
    optimized_tco = value(model.objective)
    savings = heuristic_tco - optimized_tco
    savings_pct = (savings / heuristic_tco) * 100

    # --- 4. OUTPUT ---
    print(f"1. Heuristic (AWS Only, No Spot): ${heuristic_tco:,.2f}")
    print(f"2. Optimization (Multi-Cloud):    ${optimized_tco:,.2f}")
    print(f"   >> SAVINGS:                    ${savings:,.2f} ({savings_pct:.1f}%)")

    final_capex = 0
    final_spot_vcpu = 0
    for v in model.variables():
        if v.varValue > 0:
            name = v.name.replace('Num_Instances_', '')
            count = int(v.varValue)
            data = instances[name]

            final_capex += data['upfront'] * count
            if data['is_spot']: final_spot_vcpu += data['vCPU'] * count

            results_list.append({
                "Scenario": "Scenario 11: Budget Multi-Cloud",
                "Status": LpStatus[model.status],
                "Overall_Cost": optimized_tco,
                "Baseline_Heuristic_Cost": heuristic_tco,
                "Savings_Amount": savings,
                "Savings_Percent": savings_pct,
                "Instance_Type": name,
                "Provider": data['provider'],
                "Number_of_Instances": count,
                "Hourly_Cost": data['cost'],
                "Upfront_Cost": data['upfront'],
                "Total_Instance_TCO": (data['upfront'] + data['cost'] * HOURS_IN_3_YEARS) * count,
                "vCPU_Per_Instance": data['vCPU'],
                "Total_Instance_vCPU": data['vCPU'] * count,
                "Scenario_CAPEX_Limit": MAX_CAPEX_BUDGET,
                "Scenario_CAPEX_Spent": final_capex,
                "Scenario_Max_Spot_VCPU_Allowed": max_spot,
                "Scenario_Total_Spot_VCPU_Utilized": final_spot_vcpu
            })
    print("Scenario 11 results captured.\n")