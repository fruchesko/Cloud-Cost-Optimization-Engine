# scenario_09.py
import math
from pulp import *

def run_scenario_09(results_list):
    print("--- Running Scenario 9: Financial Risk Trade-Off ---")
    
    model = LpProblem("L2_Scenario_9_Financial_Risk_Trade_Off", LpMinimize)

    # --- 1. INPUTS ---
    HOURS_IN_3_YEARS = 26280
    REQUIRED_VCPU = 240
    REQUIRED_RAM_GB = 960
    MAX_CAPEX_BUDGET = 20000
    MAX_SPOT_VCPU_PERCENT = 0.15

    instances = {
        "RI_3YR":       {"cost": 0.060, "upfront": 1800, "vCPU": 4, "RAM_GB": 16, "is_spot": False},
        "RI_1YR":       {"cost": 0.090, "upfront": 700,  "vCPU": 4, "RAM_GB": 16, "is_spot": False},
        "OD_Standard":  {"cost": 0.150, "upfront": 0,    "vCPU": 4, "RAM_GB": 16, "is_spot": False},
        "Spot_LowCost": {"cost": 0.015, "upfront": 0,    "vCPU": 2, "RAM_GB": 4,  "is_spot": True},
    }

    # --- 2. HEURISTIC BASELINE ---
    # Baseline: Greedy CAPEX -> Spend max budget on best RIs, then OD. No Spot.
    ri_3yr = instances["RI_3YR"]
    max_affordable = int(MAX_CAPEX_BUDGET // ri_3yr["upfront"])
    needed_total = math.ceil(REQUIRED_VCPU / ri_3yr["vCPU"])
    num_ris = min(max_affordable, needed_total)

    heuristic_capex = num_ris * ri_3yr["upfront"]
    heuristic_opex = num_ris * ri_3yr["cost"] * HOURS_IN_3_YEARS

    vcpu_covered = num_ris * ri_3yr["vCPU"]
    rem_vcpu = max(0, REQUIRED_VCPU - vcpu_covered)
    od_inst = instances["OD_Standard"]
    num_ods = math.ceil(rem_vcpu / od_inst["vCPU"])
    heuristic_opex += num_ods * od_inst["cost"] * HOURS_IN_3_YEARS
    heuristic_tco = heuristic_capex + heuristic_opex

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

    max_spot = REQUIRED_VCPU * MAX_SPOT_VCPU_PERCENT
    model += lpSum([
        instances[i]['vCPU'] * instance_vars[i]
        for i in instances if instances[i]['is_spot']
    ]) <= max_spot

    model.solve(PULP_CBC_CMD(msg=0))
    optimized_tco = value(model.objective)
    savings = heuristic_tco - optimized_tco
    savings_pct = (savings / heuristic_tco) * 100

    # --- 4. OUTPUT ---
    print(f"1. Heuristic (Greedy CAPEX):      ${heuristic_tco:,.2f}")
    print(f"2. Optimization (Balanced):       ${optimized_tco:,.2f}")
    print(f"   >> SAVINGS:                    ${savings:,.2f} ({savings_pct:.1f}%)")

    final_spot_vcpu = 0
    for v in model.variables():
        if v.varValue > 0:
            name = v.name.replace('Num_Instances_', '')
            count = int(v.varValue)
            data = instances[name]

            if data['is_spot']: final_spot_vcpu += data['vCPU'] * count

            results_list.append({
                "Scenario": "Scenario 9: Financial Risk Trade-Off",
                "Status": LpStatus[model.status],
                "Overall_Cost": optimized_tco,
                "Baseline_Heuristic_Cost": heuristic_tco,
                "Savings_Amount": savings,
                "Savings_Percent": savings_pct,
                "Instance_Type": name,
                "Provider": "AWS",
                "Number_of_Instances": count,
                "Total_Instance_TCO": (data['upfront'] + data['cost'] * HOURS_IN_3_YEARS) * count,
                "Scenario_Max_Spot_VCPU_Allowed": max_spot,
                "Scenario_Total_Spot_VCPU_Utilized": final_spot_vcpu
            })
    print("Scenario 9 results captured.\n")