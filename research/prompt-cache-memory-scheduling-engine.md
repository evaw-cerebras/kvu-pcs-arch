# **Prompt Cache Memory Scheduling Engine**

| Field      | Value                                                                  |
|------------|------------------------------------------------------------------------|
| Author     | Eva Winterschön                                                        |
| Section    | research/prompt-cache-memory-scheduling-engine                         |
| Version    | 0.1                                                                    |
| Date       | 2025-07-29                                                             |
| Repo       | [https://github.com/evaw-cerebras/](https://github.com/evaw-cerebras/) |
| Summarized | Prompt Cache, Cluster Components, Performance Concerns                 |
| Aggregates | Docs + Reqs + Components (June+July 2025), RAG Analysis                |
| Inferenced | Qwen3-235B-Instruct                                                    |

---

## Subject Matter Overview
Reviewing implementation details for the **KVSS (Key-Value Storage Server) Memory Engine** system, focused on off-wafer prompt caching, with an analysis of topology, memory allocation, network affinity, scheduling strategies, and operational implications.

---

## ✅ **Concept Guidelines**
- **KVSS memory must be allocated proportionally** to avoid waste.
- **Fair-share allocation** is preferred for production scalability.
- **Rail-optimized paths are critical** — avoid spine for KVSS traffic.
- **Scheduler must evolve** to be **spine-aware** and **WIO-balanced**.
- **Job sharing creates session rigidity** — plan sessions carefully.
- **Short-term**: Conservative memory grants + warnings.
- **Long-term**: Smarter scheduling, topology flexibility, and reduced CPU overhead.

---

## 🎯 **Priority Order**
1. **Evict performance** (most critical)
2. **Scheduler updates** (WIO stream awareness)
3. **Buffering / zero-copy improvements**
4. **Spine-aware scheduling** (long-term)

---

## 🔧 **1. KVSS Topology & Sharding**
- **Constraints**:
  - Each KVSS shard communicates with **one domain** (FPGA on CS-X) for **port affinity**.
  - One shard per region (future support for G*).
- **Imbalance**:
  - Shards have **different WIO (Weight I/O) counts** → varying memory per token.
  - Some domains (e.g., domain 3) handle ACT-IO traffic → fewer WIOs available for KVSS.
- **Example**:
  - In a 3-box job, box 1 may have 4 shards (1 with 1 WIO, others with 2 WIOs), while box 3 has only 1 shard.

> ✅ **Properties**: Imbalanced memory usage and shard-to-domain mapping.

---

## 💾 **2. KVSS Memory Requirements**
KVSS memory is composed of:
```
kvss_mem = base_mem + (mem_per_token × num_cached_tokens)
```

| Component             | Description | Varies by Model? | Varies by Shard? |
|-----------------------|-----------|------------------|------------------|
| `base_mem`            | Fixed overhead (~10GB) | No | No |
| `mem_per_token`       | Per-token storage (compile-time) | Yes | Yes (due to WIO imbalance) |
| `num_cached_tokens`   | Max tokens cached (configurable) | Yes | No |

- **Key Insight**: Memory must scale **proportionally** across shards to avoid waste.
  - E.g., if one shard gets extra memory but others don’t, the gain is lost — caching capacity is bottlenecked by the smallest shard.

---

## 📏 **3. Memory Allocation Strategies**
Three main proposals for assigning `num_cached_tokens`:

### **Proposal 1: Naive Allocation (Rejected)**
- Assign equal memory to all shards.
- ❌ **High memory waste** due to shard imbalance.

### **Proposal 2: Pre-determined Exact Allocation**
- Operator defines exact `base_mem` and `mem_per_token × num_tokens` per shard.
- **Pros**: Predictable, avoids waste.
- **Cons**: Requires deep operator knowledge; hard to scale.

### **Proposal 3: Fair Distribution Based on Boxes**
- Allocate memory based on:
  $$
  M_{s,j} = \frac{B_j}{B_{\text{total}}} \cdot \frac{R_k}{N_{\text{KVU}}}
  $$
  Where:
  - $ B_j $: boxes used by job $ j $
  - $ R_k $: RAM on KVU node $ k $
  - $ N_{\text{KVU}} $: total KVU nodes

- ✅ **Pros**: No prior job knowledge needed; reduces imbalance.
- ❌ **Cons**: Less flexibility; TTL depends on cluster load.

### **Proposal 4: Ratio-Based Across Jobs (Future)**
- Define cache priority ratios across all jobs.
- Scheduler allocates memory proportionally.
- Allows prioritization but complicates TTL predictability.

### **Proposal 5: Single Container per KVU (Rejected)**
- Run one pod with multiple logical shards.
- ❌ Fails due to imbalance, defragmentation, and scalability issues.

---

## 🌐 **4. Port Affinity & Rail Optimization**
- **Rail-optimized path**: Direct AX → CS-X connection via leaf switch (no spine).
- **Goal**: Avoid spine usage to prevent:
  - Bursty KV traffic from interfering with other jobs.
  - Packet loss and performance debugging issues.
- **Current Issue**:
  - Scheduler may pick ports **without affinity**, forcing spine use.
  - Scheduler **cannot detect spine use during scheduling** → hard to avoid.

> ⚠️ **Why it matters for inference (not training)**:
> - Training (ACT-IO) has predictable traffic.
> - Inference (KVSS) has **bursty, unpredictable** eviction/refill → spine congestion.

---

## 🛠️ **Short-Term Solutions to Avoid Spine**
1. **Conservative Memory Granting**:
   - Set `num_tokens_upper` close to `num_tokens_lower`.
   - Apply 20% "discount" in fair-share model.
   - During binary search for memory, **round down**.
2. **Spine Usage Handling**:
   - If spine is used:
     - **Warn** (for testing).
     - **Fail/re-queue** (for production, via flag).
   - Cannot reschedule — framework doesn’t support rollback.

---

## 🔮 **Long-Term Solutions**
- **Spine-Aware Scheduler**:
  - Make spine avoidance a scheduling constraint.
- **Move ACT-IO from Domain 3**:
  - Free up WIOs on domain 3.
  - Requires re-cabling IX nodes — complex and disruptive.
- **Improve WIO Distribution**:
  - Allow more shards per domain to balance WIO load.
  - Trade-off: increases CPU contention.

---

## 🔄 **Cluster Scheduling Considerations**
- **Inputs to Scheduler**:
  - Port affinity per shard
  - CS-X box assignment
  - Memory requirements (`base_mem`, `mem_per_token`, `num_tokens`)
- **Job Sharing Impact**:
  - Multiple jobs share AX nodes → **session blackhole**:
    - Once a session is in use, **cannot remove AX/CS-X** without canceling jobs.
    - Causes **outage risk** during maintenance or upgrades.

> 🚨 **Operational Risk**: Session resizing requires job cancellation → potential downtime.

---

## 📊 **Memory Simulation Results (llama-3.3-70b)**
| Scenario | Max Tokens | vs Baseline |
|--------|------------|-------------|
| Ideal (no sharding) | 27.3M | 100% |
| Perfect sharding (with CHIEF/ACT) | ~22.8M | 83.4% |
| Non-perfect (equal memory) | ~16.3M | 59.5% |

> ✅ **Conclusion**: Imbalanced memory allocation **halves effective cache capacity**.

---

## ⚙️ **Implementation & Protocol Updates**
- **New `LinearMemoryRange` in ClusterDetails**:
  ```protobuf
  message LinearMemoryRange {
    int64 intercept = base_mem;
    int64 coefficient_value = mem_per_token;
    int64 min_x = num_tokens_lower;
    int64 max_x = num_tokens_upper;
    bool keep_ratio = true; // all shards scale together
  }
  ```

---

## 🧩 **Other Technical Notes**
- **HIO Busy Loop**:
  - Used in latency-sensitive mode for fast evict.
  - Turning it off slows evict by 2–3×.
  - **Future fix**: Pre-read tokens into buffer (avoid busy loop).
- **Ingress Spinning**:
  - Potential to reduce with SG changes (lower priority).
- **CPU Contention**:
  - Too many shards → too many busy loops.
  - Long-term: reduce shard count, improve runtime.

---
