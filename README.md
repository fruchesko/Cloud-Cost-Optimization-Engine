# Cloud Cost Optimization Engine: Deterministic Multi-Cloud Allocation

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Power Bi](https://img.shields.io/badge/power_bi-F2C811?style=for-the-badge&logo=microsoftpowerbi&logoColor=black)
![AWS](https://img.shields.io/badge/AWS-%23FF9900.svg?style=for-the-badge&logo=amazon-aws&logoColor=white)
![Azure](https://img.shields.io/badge/microsoft%20azure-0089D6?style=for-the-badge&logo=microsoft-azure&logoColor=white)
![MIT License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)

## 🎯 Project Overview
This engine, developed for my **Engineer's Thesis**, addresses the "Efficiency Gap" in modern Cloud FinOps. While native tools often fall into the "Heuristic Myopia" trap—prioritizing local, immediate savings—this system utilizes **Linear Programming (LP)** to identify the **Global Optimum** for multi-cloud resource allocation.

## 🛑 The Problem: Cloud Complexity & Heuristic Failure
Modern cloud infrastructure has scaled beyond the cognitive capacity of manual management.
* [cite_start]**Cost Inflation**: Organizations face significant financial waste due to stranded capacity and inefficient resource allocation[cite: 84, 86].
* [cite_start]**The Heuristic Trap**: Current optimization tools typically use "greedy" algorithms that settle for local peaks—saving money on one instance while inadvertently spiking costs in another dimension, such as storage or data transfer[cite: 104, 106, 256, 258].
* [cite_start]**Constraint Conflict**: Engineering teams prioritize reliability (often leading to over-provisioning), while Finance teams enforce rigid budget caps, creating a friction-filled "Efficiency Gap"[cite: 112, 114, 139, 140].

### ⚠️ Research Scope & Data Integrity
This project is a **mathematical proof-of-concept** conducted in a controlled analytical environment.
* [cite_start]**Data Nature**: The research utilizes **synthetic telemetry** mapped against real-world AWS and Azure pricing APIs to ensure 100% experimental control[cite: 306, 307, 313, 1585].
* [cite_start]**Validation Status**: While mathematically rigorous, this model **has not been verified in real-world production environments** and does not currently account for the "noise," tagging errors, or unstructured anomalies inherent in raw corporate billing logs[cite: 1589, 1590, 1611, 1612].
