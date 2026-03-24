# scenario_13.py
import math
from pulp import *

def run_scenario_13(results_list):
    print("--- Running Scenario 13: Storage Migration ---")
    
    model = LpProblem("Scenario_13_Storage_Migration", LpMinimize)

    # --- 1. INPUTS ---
    MAX_CAPEX = 80000
    REQUIRED_VOL = 500000
    REQUIRED_IOPS = 25000
    MONTHS_IN_3_YEARS = 36

    instances = {
        "Hot_Standard":    {"opex": 0.023,  "iops": 0.3,  "capex": 0.35, "type": "Hot"},
        "Cool_Infrequent": {"opex": 0.0125, "iops": 0.1,  "capex": 0.10, "type": "Cool"},
        "Archive_Glacier": {"opex": 0.004,  "iops": 0.01, "capex": 0.01, "type": "Archive"},
    }

    # --- 2. HEURISTIC BASELINE ("Active Tiers Only") ---
    # Strategy: Use only Hot and Cool to ensure performance/availability.
    # Split 50/50 for simplicity.
    half_vol = REQUIRED_VOL / 2
    heuristic_capex = (half_vol * instances["Hot_Standard"]["capex"]) + (half_vol * instances["Cool_Infrequent"]["capex"])
    heuristic_opex = (half_vol * instances["Hot_Standard"]["opex"]) + (half_vol * instances["Cool_Infrequent"]["opex"])
    heuristic_monthly = heuristic_opex # We optimize monthly OPEX in this scenario

    # --- 3. OPTIMIZATION ---
    volume_vars = LpVariable.dicts("Volume_GB", instances.keys(), lowBound=0, cat=LpContinuous)

    model += lpSum([instances[t]['opex'] * volume_vars[t] for t in instances])

    # Constraints
    model += lpSum([volume_vars[t] for t in instances]) >= REQUIRED_VOL
    model += lpSum([instances[t]['iops'] * volume_vars[t] for t in instances]) >= REQUIRED_IOPS
    model += lpSum([instances[t]['capex'] * volume_vars[t] for t in instances]) <= MAX_CAPEX

    model.solve(PULP_CBC_CMD(msg=0))
    optimized_monthly = value(model.objective)
    savings = heuristic_monthly - optimized_monthly
    savings_pct = (savings / heuristic_monthly) * 100

    # --- 4. OUTPUT ---
    print(f"1. Heuristic (50/50 Hot/Cool):   ${heuristic_monthly:,.2f}/mo")
    print(f"2. Optimization (Tiered):        ${optimized_monthly:,.2f}/mo")
    print(f"   >> SAVINGS:                   ${savings:,.2f} ({savings_pct:.1f}%)")

    final_capex = 0
    final_iops = 0
    for v in model.variables():
        if v.varValue > 0:
            name = v.name.replace('Volume_GB_', '')
            vol = v.varValue
            data = instances[name]

            final_capex += data['capex'] * vol
            final_iops += data['iops'] * vol

            results_list.append({
                "Scenario": "Scenario 13: Storage Migration",
                "Status": LpStatus[model.status],
                "Overall_Cost": optimized_monthly,
                "Baseline_Heuristic_Cost": heuristic_monthly,
                "Savings_Amount": savings,
                "Savings_Percent": savings_pct,
                "Instance_Type": name,
                "Provider": "N/A",
                "Number_of_Instances": 1,
                "Volume_GB_Per_Tier": vol,
                "Total_Instance_TCO": data['opex'] * vol, # Monthly
                "Upfront_Cost": data['capex'],
                "Total_Instance_Upfront_Cost": data['capex'] * vol,
                "Scenario_CAPEX_Limit": MAX_CAPEX,
                "Scenario_CAPEX_Spent": final_capex,
                "Scenario_Min_IOPS_Limit": REQUIRED_IOPS,
                "Scenario_Provided_IOPS": final_iops
            })
    print("Scenario 13 results captured.\n")