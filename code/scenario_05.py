# scenario_05.py
import math
from pulp import *

def run_scenario_05(results_list):
    print("--- Running Scenario 5: Storage Tiering ---")
    
    model = LpProblem("Scenario_05_Storage_Tiering", LpMinimize)

    # --- 1. INPUTS ---
    REQUIRED_STORAGE_GB = 100000
    MAX_ARCHIVE_GB = 50000 # Max 50% in Archive
    MIN_HOT_GB = 10000     # Min 10% in Hot

    instances = {
        "Tier_Hot":     {"cost": 0.023, "type": "Hot"},
        "Tier_Cool":    {"cost": 0.0125, "type": "Cool"},
        "Tier_Archive": {"cost": 0.004, "type": "Archive"},
    }

    # --- 2. HEURISTIC BASELINE ---
    # Baseline: No tiering, all data stored in Hot Tier for maximum accessibility.
    heuristic_monthly_cost = REQUIRED_STORAGE_GB * instances["Tier_Hot"]["cost"]

    # --- 3. OPTIMIZATION ---
    # Variables are Continuous (Volume)
    volume_vars = LpVariable.dicts("Volume_GB", instances.keys(), lowBound=0, cat=LpContinuous)

    model += lpSum([instances[i]['cost'] * volume_vars[i] for i in instances])
    model += lpSum([volume_vars[i] for i in instances]) >= REQUIRED_STORAGE_GB
    model += volume_vars["Tier_Archive"] <= MAX_ARCHIVE_GB
    model += volume_vars["Tier_Hot"] >= MIN_HOT_GB

    model.solve(PULP_CBC_CMD(msg=0))
    optimized_monthly_cost = value(model.objective)
    savings = heuristic_monthly_cost - optimized_monthly_cost
    savings_pct = (savings / heuristic_monthly_cost) * 100

    # --- 4. OUTPUT & EXPORT ---
    print(f"1. Heuristic (All Hot):          ${heuristic_monthly_cost:,.2f}/mo")
    print(f"2. Optimization (Tiered):        ${optimized_monthly_cost:,.2f}/mo")
    print(f"   >> SAVINGS:                   ${savings:,.2f} ({savings_pct:.1f}%)")

    for v in model.variables():
        if v.varValue > 0:
            name = v.name.replace('Volume_GB_', '')
            volume = v.varValue
            data = instances[name]

            results_list.append({
                "Scenario": "Scenario 5: Storage Tiering",
                "Status": LpStatus[model.status],
                "Overall_Cost": optimized_monthly_cost,
                "Baseline_Heuristic_Cost": heuristic_monthly_cost,
                "Savings_Amount": savings,
                "Savings_Percent": savings_pct,
                "Instance_Type": name,
                "Provider": "AWS",
                "Volume_GB_Per_Tier": volume,
                "Total_Instance_TCO": data['cost'] * volume
            })
    print("Scenario 5 results captured.\n")