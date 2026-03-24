# Diploma Project: Cloud Cost Optimization

## About This Project
This folder contains the Python code for my diploma thesis on Cloud Cost Optimization.

I built a system using Python and Linear Programming (PuLP) that calculates the best way to buy cloud resources (like AWS/Azure servers and storage). It looks at different "What If" scenarios—like having a tight budget, needing high performance, or mixing multiple clouds—and mathematically finds the cheapest option.

## How the Files Are Organized
To keep things clean, I didn't put everything in one giant script. Here is how it breaks down:

### 1. The Setup
* **00_environment_setup.py**: This sets up the libraries and creates the empty list where we save our results.

### 2. The Scenarios (The Logic)
Each file represents a specific business problem I solved in the thesis:
* **scenario_01.py**: Comparing standard rates vs. discounts (RIs).
* **scenario_02.py**: What to buy if you have a strict budget cap.
* **scenario_03.py**: Using "Spot" instances (cheap but risky).
* **scenario_04.py**: Picking the perfect size for a server (Right-Sizing).
* **scenario_05.py & 10.py**: Optimizing Storage (Hot vs. Cool vs. Archive).
* **scenario_06.py**: Balancing upfront costs (CAPEX) vs. monthly costs (OPEX).
* **scenario_08.py - 15.py**: Advanced scenarios involving Multi-Cloud (AWS + Azure), Governance rules, and complex migrations.

### 3. The Runner
* **main.py**: This is the most important file. It connects everything. It runs the setup, executes all 15 scenarios one by one, and saves the results to a CSV file.

---

## How to Run It (Google Colab)
Since this project uses multiple files, here is the easiest way to run it in Colab:

1.  **Zip the files:** Select all the .py files in this folder and compress them into a file named project.zip (or similar).
2.  **Open Colab:** Go to Google Colab and create a new notebook.
3.  **Upload:** Click the folder icon on the left and drag your zip file there.
4.  **Install the Solver:** In the first code cell, run this to install the math library:
    !pip install pulp

5.  **Unzip and Run:** In the next cell, run this:
    !unzip -o project.zip
    !python main.py

## The Output
When the script finishes running, it will generate a file called:
**Diploma_Cloud_Optimization_Evidence.csv**

You can download this file. It contains the data rows for every scenario, showing exactly how much money was saved and which servers were selected.

---
**Created by:** Kyrylo Brykov