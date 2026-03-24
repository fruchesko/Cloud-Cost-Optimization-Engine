# 00_environment_setup.py

# --- 0. LIBRARY SETUP & GLOBAL UTILITIES ---
# This file is imported by main.py and the scenario files.
# It ensures all necessary libraries are available and provides the results container.

import pandas as pd
import math
from pulp import *

def get_fresh_results_list():
    """
    Factory function to initialize a new results container.
    This is called by main.py to ensure the report starts empty.
    """
    print("--- 0. ENVIRONMENT SETUP ---")
    print("System: Global results list initialized.")
    return []