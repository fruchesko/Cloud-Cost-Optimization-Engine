# main.py
# --- DIPLOMA THESIS: CLOUD OPTIMIZATION ORCHESTRATOR ---
# Author: [Your Name]
# Description: Central execution script that runs all optimization scenarios 
# and aggregates results into a single analytical dataset.

import pandas as pd
import time
from 00_environment_setup import get_fresh_results_list

# --- IMPORT SCENARIOS ---
# This demonstrates modular architecture (Separation of Concerns)
from scenario_01 import run_scenario_01
from scenario_02 import run_scenario_02
from scenario_03 import run_scenario_03
from scenario_04 import run_scenario_04
from scenario_05 import run_scenario_05
from scenario_06 import run_scenario_06
from scenario_07 import run_scenario_07
from scenario_08 import run_scenario_08
from scenario_09 import run_scenario_09
from scenario_10 import run_scenario_10
from scenario_11 import run_scenario_11
from scenario_12 import run_scenario_12
from scenario_13 import run_scenario_13
from scenario_14 import run_scenario_14
from scenario_15 import run_scenario_15

def main():
    print("==========================================")
    print("STARTING CLOUD OPTIMIZATION ENGINE")
    print("==========================================\n")

    # 1. Initialize Global Data Container
    # We use the factory function from setup to ensure a clean state
    all_results = get_fresh_results_list()
    start_time = time.time()

    # 2. Execute Scenarios Sequentially
    # Level 1: Foundation
    run_scenario_01(all_results)
    run_scenario_02(all_results)
    run_scenario_03(all_results)
    run_scenario_04(all_results)
    run_scenario_05(all_results)

    # Level 2: Advanced Trade-offs
    run_scenario_06(all_results)
    run_scenario_07(all_results)
    run_scenario_08(all_results)
    run_scenario_09(all_results)
    run_scenario_10(all_results)

    # Level 3: Strategic & Hybrid
    run_scenario_11(all_results)
    run_scenario_12(all_results)
    run_scenario_13(all_results)
    run_scenario_14(all_results)
    run_scenario_15(all_results)

    # 3. Export Evidence
    print("==========================================")
    print(f"Processing {len(all_results)} data points...")
    
    output_filename = "Diploma_Optimization_Results_FINAL.csv"
    
    try:
        df = pd.DataFrame(all_results)
        
        # Optional: Reorder columns for readability if desired, 
        # otherwise Pandas defaults are fine.
        cols = [
            'Scenario', 'Status', 'Overall_Cost', 'Baseline_Heuristic_Cost', 
            'Savings_Amount', 'Savings_Percent', 'Instance_Type', 'Provider', 
            'Number_of_Instances', 'Total_Instance_TCO'
        ]
        # Only select columns that actually exist in the dataframe to avoid errors
        existing_cols = [c for c in cols if c in df.columns]
        remaining_cols = [c for c in df.columns if c not in cols]
        df = df[existing_cols + remaining_cols]

        df.to_csv(output_filename, index=False)
        
        elapsed = time.time() - start_time
        print(f"SUCCESS: Data exported to '{output_filename}'")
        print(f"Total Execution Time: {elapsed:.2f} seconds")
        print("==========================================")
        
    except PermissionError:
        print(f"ERROR: Could not write to '{output_filename}'. Is the file open in Excel?")
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}")

if __name__ == "__main__":
    main()