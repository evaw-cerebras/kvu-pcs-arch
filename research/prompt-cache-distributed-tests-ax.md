# Cluster 3.0 Distributed SWdriver Across AX Tests

| Field      | Value                                                                  |
|------------|------------------------------------------------------------------------|
| Author     | Eva Winterschön                                                        |
| Section    | research/prompt-cache-distributed-ax-swdriver                          |
| Version    | 0.1                                                                    |
| Date       | 2025-07-31                                                             |
| Repo       | [https://github.com/evaw-cerebras/](https://github.com/evaw-cerebras/) |
| Summarized | Prompt Cache, SWdriver, AX Node Perf References                        |
| Inferenced | Qwen3-235B-(Thinking/Instruct), Llama3.3-70b                           |
| Wiki Doc   | [Cluster 3.0 Distributed SWdriver Across AX Tests](https://cerebras.atlassian.net/wiki/spaces/AIC/pages/4646732140/Cluster+3.0+distributed+swdriver+across+AX+tests)

---                           

This document offers summarized views of the original content, using three different LLMs running on an internal CS-3 cluster. Usually the more advanced results would be selected, parsed, reviewed, annotated as needed, and validated before use as a reference. 

In this case I've decided to include all three outputs to show how these three models offer substantially more detailed analysis and usefulness, using the same prompt query and same temperature variable. 

## Review by Llama3.3-70b

### **Technical Review**
Constrained Layout of Swdrivers on AX Nodes

### **Problem Statement**
The existing Job Operator (JO) in Cluster v3.0 prioritizes pod affinity to CSx over AX node allocation, leading to potential resource contention when multiple swdriver pods land on the same AX node.

### **Experiments and Results:**

#### 1. **Non-limited AX Job Sharing**
	* Ran a LLama 3.1 8B Spec Decode Fuzzer test with 3 parallel LLama 3.1 8B Spec Decode Structured Output tests.
	* All jobs landed on the same AX node (net001-ax-sr02).
	* **Results** showed a >25% drop in generation performance for at least 10% of the prompts.
   
#### 2. **Mutual SwDriver Exclusion in AX Job Sharing**
	* Ran the same experiment as Version 1, but with swdriver pods restricted to land on different AX nodes.
	* **Results** showed no degradation in performance.
   
#### 3. **Experiment: Prompt Caching**
	* Ran 4 parallel LLama 3.1 8B Spec Decode with Prompt Caching jobs.
	* **Results** showed no degradation in performance.
   
#### 4. **Experiment: Qwen 3 32B Spec Decode with Prompt Caching and 2 LLama 3.1 8B jobs**
	* Ran 1 Qwen 3 32B Spec Decode with Prompt Caching job and 2 LLama 3.1 8B jobs.
	* **Results** showed no performance degradation, but it was harder to overlap the 3 jobs. 
   
#### 5. **Experiment: Qwen 3 32B Fuzzer job with Prompt Caching and 3 LLama 3.1 8B SO jobs**
	* Ran 1 Qwen 3 32B Fuzzer job with Prompt Caching and 3 LLama 3.1 8B SO jobs.
	* **Results** showed a possible dip in the graph during SO runs for the fuzzer job, but it did not manifest in actual numbers.

### **Conclusion:**

- The experiments demonstrate that restricting swdriver pods to land on different AX nodes (Version 2) eliminates the resource contention issue and shows no degradation in performance. 
- The results also suggest that the mutual exclusion of swdriver pods on AX nodes does not negatively impact prompt caching performance. 
- However, further testing is needed to fully understand the effects of overlapping jobs on performance.

---

## Review by Qwen3-235B (Thinking)

### **Core Problem**  
In Cluster v3.0's Job Operator (JO), **swdriver pods (ACT-0) prioritized affinity to CSx nodes** without constraints, causing multiple swdrivers to land on the *same AX node*. This led to **resource contention** (CPU/memory overload), degrading inference performance (e.g., >25% drop in token generation speed during high-load jobs).

---

### **Solution: Mutual SwDriver Exclusion (JO: `tianyid-7d655ae129`)**  
- Modified pod scheduling to **enforce exclusive AX node placement for swdriver pods** (each swdriver lands on a *different* AX node).  
- Other pods (KVSS, CHF, WSE) retain standard affinity rules.  
- *Goal:* Eliminate resource contention by distributing swdriver load.

---

### **Validation Results**  
#### **Version 1: Baseline (Broken)**  
- **Test:** Llama 3.1 8B fuzzer + 3 high-load Structured Output (SO) jobs forced onto *one AX node* (`net001-ax-sr02`).  
- **Result:**  
  - **>25% drop in token generation speed** during SO runs (e.g., avg tokens/s dropped from **2039 → 1866**).  
  - CPU/memory spikes correlated with performance degradation (graphs confirmed contention).  

#### **Version 2: Mutual Exclusion (Fixed)**  
1. **Llama 3.1 8B Fuzzer + SO Jobs**  
   - Swdrivers distributed across **4 distinct AX nodes** (sr02, sr03, sr04, sr05).  
   - **Result:** Fuzzer maintained **baseline performance** (avg **2077 tokens/s** vs. 2039 in baseline). No degradation during SO runs.  

2. **4 Parallel Prompt Caching Jobs (Llama 3.1 8B)**  
   - Swdrivers placed on **4 separate AX nodes**.  
   - **Result:** All jobs sustained **near-identical performance** to single-job baseline (e.g., gen tokens/s: **1359–1957** vs. **1365–1934** in experiment).  

3. **Mixed Workloads (Qwen 32B + Llama 8B Jobs)**  
   - Qwen 32B fuzzer + 3 Llama SO jobs; swdrivers spanned **3 AX nodes** (sr02, sr03, sr04).  
   - **Result:** **No performance degradation** (e.g., Qwen gen tokens/s: **626–941** vs. expected). Minor visual dips in graphs did *not* reflect in metrics.  

---

### **Key Conclusions**  
- **Mutual swdriver exclusion successfully eliminated resource contention** by ensuring swdrivers never share an AX node.  
- **No performance impact** observed across:  
  - High-load Structured Output tests,  
  - Prompt caching workloads,  
  - Mixed-model (Qwen + Llama) scenarios.  
- **Critical fix** for Cluster v3.0, enabling reliable multi-job scheduling without inference degradation.  

> 💡 **Takeaway**: Enforcing swdriver pod distribution across AX nodes resolves contention issues while maintaining full cluster utilization. Validation proves robustness across diverse inference workloads.

---

## Review by Qwen3-235B (Instruct)
### **Technical Review: Constrained Layout of SwDrivers in Cluster v3.0 Job Operator**

---

#### **Problem Summary**
In Cluster v3.0’s Job Operator (JO), **pod affinity to CSx nodes** took precedence over **swdriver (ACT-0) placement**, potentially causing multiple swdriver pods to land on the same AX node. This led to **resource contention**, particularly CPU and memory, degrading generation performance (gen perf) under concurrent workloads.

> **Thread Reference**: [Slack Discussion](https://cerebras.slack.com/archives/C086NTF570F/p1751914584811629)  
> **Related Change**: Mutual SwDriver Exclusion ([Slack Link](https://cerebras.slack.com/archives/C086NTF570F/p1753391870023009))

---

### **Version 1: Non-Limited AX Job Sharing (Baseline Issue)**

- **JO Version**: `tianyid-4185925b8f` (Cluster v3.0 default)
- **Test Setup**:
  - Cluster: **DH1-p2** (8 WSE boxes, 8 AX nodes)
  - Workloads:
    - **Fuzzer Test**: Llama 3.1 8B Spec Decode, 3000s, fixed output length
    - **Concurrent Load**: 3 Structured Output (SO) tests launched at +10, +15, +30 min
  - All swdrivers forced to land on **net001-ax-sr02**

- **Observations**:
  - High CPU and memory utilization on shared AX node during SO runs.
  - **Gen token speed dropped >25% for ≥10% of prompts** during peak load.

| Metric               | Baseline    | Experiment  | During SO Load |
|----------------------|-------------|-------------|----------------|
| avg (tok/s)          | 2039.57     | 2023.51     | 1866.62        |
| p1 (tok/s)           | 1913.96     | 1391.50     | **83.30**      |
| p5 (tok/s)           | 1948.70     | 1947.45     | 610.92         |
| std (tok/s)          | 305.23      | 334.04      | **508.50**     |

- **Conclusion**:  
  Significant performance degradation due to **swdriver co-location** on a single AX node. Resource contention impacts tail latency and overall throughput.

---

### **Version 2: Mutual SwDriver Exclusion in AX Job Sharing**

- **JO Version**: `tianyid-7d655ae129`  
  → Enforces **swdriver pod anti-affinity**: ensures **one swdriver per AX node**

#### **Experiment 1: Fuzzer + SO Load (Llama 3.1 8B)**

- **Setup**: Identical to Version 1
- **SwDriver Placement**:
  - Fuzzer: `net001-ax-sr04`
  - SO Jobs: `sr02`, `sr05`, `sr02` (no overlap on same AX for swdrivers)

- **Gen Performance (Fuzzer)**: 
- 
  | Metric (tok/s) | Value     |
  |----------------|-----------|
  | avg            | 2077.88   |
  | std            | 307.70    |
  | p1             | 1975.84   |
  | p50            | 2002.97   |
  | p99            | 3466.78   |

- **Conclusion**:  
  **No observable performance degradation**. Gen speed remains stable and consistent with baseline, even during high load.

#### **Experiment 2: 4x Prompt Caching Jobs (Llama 3.1 8B)**

- **Workloads**: 4 parallel Llama 3.1 8B Spec Decode + Prompt Caching
- **SwDriver Placement**: Spread across `sr02`, `sr03`, `sr04`, `sr05`

- **Performance Comparison (Per-Box Throughput)**:
  - **Single Job (Base)**: 6016–21110 tok/s
  - **4x Concurrent Jobs**: 5765–21784 tok/s (within noise margin)

- **KVSS Pod Distribution**: Evenly spread; no AX node overload observed.

- **Conclusion**:  
  **No performance degradation** under concurrency. Mutual exclusion enables safe sharing of AX nodes while preserving performance.

#### **Experiment 3: Mixed Workload (Qwen 3 32B + 2x Llama 3.1 8B)**

- **Workloads**:
  - Qwen 3 32B Spec Decode + Prompt Caching
  - 2x Llama 3.1 8B Prompt Caching

- **SwDriver Placement**:
  - Qwen: `sr04`
  - Llama 1: `sr02`
  - Llama 2: `sr04` (same AX, but **different swdriver pod**; allowed)

- **Performance**:
  - Qwen: ~8.7K–33.2K total tok/s
  - Llama: ~5.8K–11.8K total tok/s
  - Comparable to expected baselines.

- **Note**: Jobs not perfectly synchronized due to compile-time variance.

- **Conclusion**:  
  **No measurable performance impact**. System handles mixed-model, high-load prompt caching scenarios effectively.

#### **Experiment 4: Qwen 3 32B Fuzzer + 3x Llama SO Jobs**

- **Setup**:
  - Fuzzer: Qwen 3 32B, 3000s
  - 3 SO jobs launched at +15, +20, +35 min

- **SwDriver Placement**:
  - Fuzzer: `sr02`
  - SO Jobs: `sr04`, `sr03`, `sr04` (no duplicate swdrivers on same AX)

- **Gen Performance (Fuzzer)**:
  
- | Metric (tok/s) | Overall     | During SO Job 1 |
  |----------------|-------------|-----------------|
  | avg            | 523.77      | 554.68          |
  | std            | 89.69       | 92.50           |
  | min            | 29.61       | 119.43          |
  | p50            | 515.46      | 579.82          |
  | p99            | 695.22      | 706.67          |

- **Conclusion**:  
  Minor visual dip in time-series graphs, but **no statistical performance degradation**. Anti-affinity policy prevents resource saturation.

---

### **Overall Conclusion**

- **Problem Confirmed**:  
  Co-locating multiple swdriver pods on the same AX node in Cluster v3.0 causes **resource contention and gen perf degradation**.

- **Solution Validated**:  
  **Mutual SwDriver Exclusion** (via anti-affinity rules) effectively mitigates this issue:
  - Swdrivers are distributed across AX nodes.
  - No measurable performance loss under high concurrency.
  - Safe for mixed-model, production-like workloads (prompt caching, fuzzer, SO).

- **Recommendation**:  
  **Adopt and deploy** the updated Job Operator (`tianyid-7d655ae129`) as default for Cluster v3.0+ to ensure robust, predictable performance in multi-job environments.

---
