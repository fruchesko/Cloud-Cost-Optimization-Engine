# scenario_10.py
import math
from pulp import *

def run_scenario_10(results_list):
    print("--- Running Scenario 10: Risk-Adjusted Storage Optimization ---")
    
    # --- SCENARIO 10: LEVEL 2 - RISK-ADJUSTED STORAGE OPTIMIZATION ---
    # Goal: Minimize Monthly Storage OPEX while maintaining average performance and limiting "deep freeze" risk.
    model = LpProblem("L2_Scenario_10_Risk_Adjusted_Storage_Optimization", LpMinimize)

    # --- 1. INPUT DATA (Monthly Cost Context) ---
    REQUIRED_VOLUME_GB = 180000
    MAX_RISKY_VOLUME_PERCENT = 0.20  # Max 20% in Glacier/Archive
    MIN_PERFORMANCE_THRESHOLD = 0.05 # Average IOPS per GB required across the whole pool

    # Calculated Target
    REQUIRED_TOTAL_IOPS = REQUIRED_VOLUME_GB * MIN_PERFORMANCE_THRESHOLD

    # Data Structure
    instances = {
        # 1. Hot (Fast, Expensive, Safe)
        "Hot_Standard":    {"cost": 0.0230, "iops_per_gb": 0.3,  "is_risky": False, "type": "Hot"},
        # 2. Cool (Mid, Mid, Safe)
        "Cool_Infrequent": {"cost": 0.0125, "iops_per_gb": 0.1,  "is_risky": False, "type": "Cool"},
        # 3. Archive (Slow, Cheap, Risky for Access)
        "Archive_Glacier": {"cost": 0.0040, "iops_per_gb": 0.01, "is_risky": True,  "type": "Archive"},
    }

    # --- 2. HEURISTIC BASELINE (Single-Tier Safety Strategy) ---
    # Logic: "Don't risk data availability. Put everything on Hot_Standard."
    heuristic_tier = instances["Hot_Standard"]
    heuristic_monthly_cost = REQUIRED_VOLUME_GB * heuristic_tier["cost"]

    # --- 3. OPTIMIZATION MODEL ---
    # Variable: Volume (GB) allocated to each tier
    instance_vars = LpVariable.dicts("Volume_GB", instances.keys(), lowBound=0, cat=LpContinuous)

    # Objective: Minimize Monthly Cost
    model += lpSum([instances[i]['cost'] * instance_vars[i] for i in instances])

    # Constraints
    # 1. Total Volume
    model += lpSum([instance_vars[i] for i in instances]) >= REQUIRED_VOLUME_GB

    # 2. Performance (Total IOPS)
    model += lpSum([instances[i]['iops_per_gb'] * instance_vars[i] for i in instances]) >= REQUIRED_TOTAL_IOPS

    # 3. Risk (Max Risky Volume)
    max_risky_gb = REQUIRED_VOLUME_GB * MAX_RISKY_VOLUME_PERCENT
    model += lpSum([
        instance_vars[i] for i in instances if instances[i]['is_risky']
    ]) <= max_risky_gb

    # --- 4. SOLVE ---
    model.solve(PULP_CBC_CMD(msg=0))
    optimized_monthly_cost = value(model.objective)
    savings = heuristic_monthly_cost - optimized_monthly_cost
    savings_pct = (savings / heuristic_monthly_cost) * 100

    # --- 5. OUTPUT ---
    print(f"Goal: Minimize Monthly Cost (Min Avg IOPS: {MIN_PERFORMANCE_THRESHOLD})")
    print(f"1. Heuristic (All Hot Storage):     ${heuristic_monthly_cost:,.2f} / month")
    print(f"2. Optimization (Tiered Strategy):  ${optimized_monthly_cost:,.2f} / month")
    print(f"   >> SAVINGS GENERATED:            ${savings:,.2f} / month ({savings_pct:.1f}%)")

    final_total_risky_volume = 0
    
    for v in model.variables():
        if v.varValue > 0:
            name = v.name.replace('Volume_GB_', '')
            volume = v.varValue
            data = instances[name]

            if data['is_risky']:
                final_total_risky_volume += volume

            results_list.append({
                "Scenario": "Scenario 10: Risk-Adjusted Storage",
                "Status": LpStatus[model.status],
                "Overall_Cost": optimized_monthly_cost,
                "Baseline_Heuristic_Cost": heuristic_monthly_cost,
                "Savings_Amount": savings,
                "Savings_Percent": savings_pct,
                "Instance_Type": name,
                "Provider": "AWS", 
                "Number_of_Instances": 1, # Conceptually 1 chunk of storage
                "Total_Instance_TCO": data['cost'] * volume, # Monthly
                "Volume_GB_Per_Tier": volume,
                "Total_Instance_IOPS": data['iops_per_gb'] * volume,
                "Scenario_Required_Volume_GB": REQUIRED_VOLUME_GB,
                "Scenario_Min_IOPS_Limit": REQUIRED_TOTAL_IOPS,
                "Scenario_Max_Spot_VCPU_Allowed": max_risky_gb, # Reusing col for Risk limit
                "Scenario_Total_Spot_VCPU_Utilized": final_total_risky_volume
            })
    print("Scenario 10 results captured.\n")