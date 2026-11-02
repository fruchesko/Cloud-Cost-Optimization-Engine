# Cloud Cost Optimization Engine: Deterministic Multi-Cloud Allocation

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Power Bi](https://img.shields.io/badge/power_bi-F2C811?style=for-the-badge&logo=microsoftpowerbi&logoColor=black)
![AWS](https://img.shields.io/badge/AWS-%23FF9900.svg?style=for-the-badge&logo=amazon-aws&logoColor=white)
![Azure](https://img.shields.io/badge/microsoft%20azure-0089D6?style=for-the-badge&logo=microsoft-azure&logoColor=white)


## 🎯 Project Overview
This engine addresses the "Efficiency Gap" in modern Cloud FinOps. While native tools often fall into the "Heuristic Myopia" trap—prioritizing local, immediate savings—this system utilizes **Linear Programming (LP)** to identify the **Global Optimum** for multi-cloud resource allocation.

## 🛑 The Problem: Cloud Complexity & Heuristic Failure
Modern cloud infrastructure has scaled beyond the cognitive capacity of manual management.
* **Cost Inflation**: Organizations face significant financial waste due to stranded capacity and inefficient resource allocation.
* **The Heuristic Trap**: Current optimization tools typically use "greedy" algorithms that settle for local peaks—saving money on one instance while inadvertently spiking costs in another dimension, such as storage or data transfer.
* **Constraint Conflict**: Engineering teams prioritize reliability (often leading to over-provisioning), while Finance teams enforce rigid budget caps, creating a friction-filled "Efficiency Gap."

### ⚠️ Research Scope & Data Integrity
This project is a **mathematical proof-of-concept** conducted in a controlled analytical environment.
* **Data Nature**: The research utilizes **synthetic telemetry** mapped against real-world AWS and Azure pricing APIs to ensure 100% experimental control.
* **Validation Status**: While mathematically rigorous, this model **has not been verified in real-world production environments** and does not currently account for the "noise," tagging errors, or unstructured anomalies inherent in raw corporate billing logs.

## 🚀 Key Performance Indicators (KPIs)
The engine’s efficacy was measured by comparing its deterministic output against standard heuristic baselines across 15 scenarios.

* **Global Efficiency**: Achieved a **13.1% ($72.1K)** reduction in Total Cost of Ownership (TCO) for complex enterprise-scale configurations.
* **Solver Performance**: High-dimensional multi-objective problems were resolved in just **0.0318 seconds**, demonstrating real-time decision-support viability.
* **Storage ROI**: Identified lifecycle arbitrage and migration opportunities yielding up to a **62.7% TCO reduction**.
* **Constraint Precision**: Successfully saturated financial and technical boundaries (e.g., utilizing 97.8% of available CAPEX) to minimize operational waste.

## 📈 Visualized Results & Evidence

The model was stress-tested across three levels of complexity to verify its ability to maintain a global optimum under increasingly conflicting constraints.

### 1. Level 1: Isolated Rate Optimization (Scenario 1)
This baseline test evaluates the engine's ability to balance On-Demand flexibility against Reserved Instance discounts. 
* **Outcome**: The solver identified the exact saturation point (25 units) required to cover a steady 100 vCPU workload, eliminating the manual "best guess" rounding errors common in heuristic tools.

![Scenario 1 - Rate Optimization](visuals/S1.png)

### 2. Level 2: Advanced Risk & Governance (Scenario 7)
Moving beyond cost, this scenario introduces a "Risk Budget" limit on Spot instance usage to ensure system stability.
* **Outcome**: The engine utilized 94% of the allowable risk threshold to drive down unit costs, proving that precise mathematical assignment eliminates the need for expensive, fear-based over-provisioning.

![Scenario 7 - Risk vs Technical Fit](visuals/S7.png)

### 3. Level 3: Storage Lifecycle & ROI (Scenario 13)
This global optimization scenario calculates the financial break-even point for migrating 180TB of unstructured data across storage tiers.
* **Outcome**: Identified a massive **62.7% efficiency gain**. The model demonstrated that the one-time migration fee (CAPEX) was offset by monthly savings in under 24 days.

![Scenario 13 - Storage ROI](visuals/S13.png)

### 4. Level 3: The Integrated Master Problem (Scenario 15)
The final test simulates a large-scale enterprise environment subject to simultaneous, conflicting constraints: a $45K CAPEX limit, Spot Risk ceilings, and mandatory Multi-Cloud provider policies.
* **Outcome**: Achieved the **Global Optimum with 13.1% ($72.1K) total savings**. While standard scripts failed to find a feasible solution within the budget, the LP solver performed global resource arbitration to satisfy all requirements.

![Scenario 15 - Master Optimization](visuals/S15.png)

* ## 🧠 Core Technical Architecture
The engine treats cloud infrastructure as a multi-dimensional solution space governed by linear inequalities. By navigating the polytope of feasible solutions, it identifies the absolute mathematical floor of expenditure without compromising system resilience.

* **Optimization Engine**: Built in **Python** using the **PuLP** library to model objective functions and constraints.
* **Algorithmic Core**: Utilizes the **Simplex Algorithm** to search for a global optimum, delegating heavy computation to high-performance C-solvers (CBC/GLPK).
* **Intelligence Layer**: **Microsoft Power BI** (integrated via DAX) serves as the visualization frontend, transforming raw optimization vectors into actionable business intelligence.

---

## 📂 Repository Structure
* **/code**: Modular Python scripts implementing the optimization logic for all 15 experimental scenarios.
* **/docs**: Contains the full digital version of the Engineer's Thesis (PDF) and the interactive Power BI (.pbix) dashboard files.
* **/visuals**: High-resolution screenshots of the analytical dashboards and performance benchmarks.
* **/engine**: Scenarios 1, 13 and 15 as importable functions with parameters (thesis values as defaults).
* **/app**: Web app and HTTP API on top of `/engine`.
* **/tests**: pytest suite for the engine and the app.

---

## 🛠️ Replication Protocol

### Local (Python 3)
```bash
git clone https://github.com/fruchesko/Cloud-Cost-Optimization-Engine.git
cd Cloud-Cost-Optimization-Engine
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd code
python Main.py
```
The engine processes all 15 scenarios in sequence and writes the results to `Diploma_Optimization_Results_FINAL.csv` in the `code` directory.

### Google Colab
1. **Install Dependencies**: Upload `requirements.txt` and run `!pip install -r requirements.txt` (installs `pandas` and `pulp<3`).
2. **Environment Setup**: Upload all `.py` files from the `/code` directory (or a compressed `project.zip` of them, then `!unzip -o project.zip`) to your Colab session.
3. **Execution**: Run `!python Main.py` (the file name is case-sensitive). The results are written to `Diploma_Optimization_Results_FINAL.csv`.

---

## 🖥️ Web App

A small web page and API for Scenarios 1, 13 and 15: adjust the inputs, solve, and
compare the heuristic baseline with the optimum.

```bash
docker compose up -d --build      # then open http://<server>:8090
```

Or without Docker:
```bash
pip install -r requirements-app.txt
uvicorn app.main:app --host 0.0.0.0 --port 8090
```

| Endpoint | |
|---|---|
| `GET /` | the web page |
| `GET /scenarios` | scenarios with each parameter's range and default |
| `POST /solve` | `{"scenario": "scenario_15", "params": {"max_capex": 60000}}`; omitted parameters use the thesis values |
| `POST /assistant` | `{"messages": [{"role": "user", "content": "..."}], "scenario": "...", "params": {...}}` → reply and validated suggestion |
| `GET /docs` | interactive API documentation |

`POST /solve` returns 422 with `"error": "infeasible"` when no allocation meets the
constraints, 422 with field details for out-of-range inputs, and 504 if the solver
runs longer than `SOLVER_TIMEOUT_SECONDS` (default 10). `allowed_instances` limits
the types the optimizer may use; the baseline keeps its standard types.

### Needs assistant

A chat window ("This helps you better understand your needs") turns a client's
description into suggested settings that can be applied with one click. It calls
`gpt-6-luna` through a LiteLLM gateway: put the gateway key in `.env` as
`LITELLM_API_KEY` (see `.env.example`); without it the assistant is hidden.
Suggestions are validated against the same ranges as `/solve`. Limits: 20
messages per visitor per hour, 300 per day, 600 tokens per reply, and the key's
own budget in LiteLLM.

The app has no login. Set `COST_ENGINE_PORT` to use a port other than 8090, and
`FORWARDED_ALLOW_IPS` to your reverse proxy's address so per-visitor limits see
real client addresses. Every response carries security headers (CSP, HSTS,
X-Frame-Options) and request bodies over 64 KB (`MAX_BODY_BYTES`) get a 413.

Tests: `pip install -r requirements-dev.txt && pytest`.

---

## 👤 Author Information
* **Author**: Kyrylo Brykov
* **Degree**: Bachelor of Science in Information and Communication Technology (ICT)
* **Institution**: Bydgoszcz University of Science and Technology (Politechnika Bydgoska), 2026
* **Specialization**: Deterministic Optimization, Cloud FinOps, and Business Intelligence Analytics

---
