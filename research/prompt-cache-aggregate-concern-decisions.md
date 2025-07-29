# **Aggregate Concerns and Decision Processes in Off-Wafer Prompt Caching**

| Field      | Value                                                                  |
|------------|------------------------------------------------------------------------|
| Author     | Eva Winterschön                                                        |
| Section    | research/prompt-cache-aggregate-concerns-decision-processes            |
| Version    | 0.2.1                                                                  |
| Date       | 2025-07-29                                                             |
| Repo       | [https://github.com/evaw-cerebras/](https://github.com/evaw-cerebras/) |
| Summarized | Prompt Cache, Cluster Components, Performance Concerns                 |
| Aggregates | Docs + Reqs + Components (June+July 2025), RAG Analysis                |
| Inferenced | Qwen3-235B-Instruct                                                    |


## **Structured Summary**

This report synthesizes the design, technical concerns, and decision-making processes for the **off-wafer prompt caching system**, an innovation aimed at accelerating our inference platform by reusing previously computed Key-Value (KV) state data. The system centers on KVSS _(Key Value Storage Servers)_ and the infamous `SwDriver`. Both components require alterations resulting in deep integration into cluster topology, scheduling, memory management, and security policies.

Long(ish) term analysis of documentation, meeting notes, repository commits, and development roadmaps reveal a **multi-dimensional challenge space** involving performance, scalability, security, and operational resilience. Decisions are driven by trade-offs between multiple spaces:

- predictability and flexibility
- performance and robustness
- short-term feasibility vs long-term vision

In performing this multi-week analysis, I've focused on several high-level categories for the cognitive-flow: 
- **aggregate concerns**
- **decision rationale**
- **implementation roadmap**

And mostly for my own reference, included **Glossary of Terms**.

## **Summary of Summary**
The proposed off-wafer prompt caching system represents a complex integration of hardware, software, and scheduling to deliver high-performance inference. The design decisions reflect a pragmatic balance between innovation and operational reality, with reservations on cost-center compliance and total-cluster performance being maintained over esoteric design patterns.

### Short Term focus
Rail optimization, fair memory allocation, and evict performance. 

### Long Term Focus
The system will evolve toward smarter scheduling, multi-level caching, and enhanced security and scalability.

---

## **1. Aggregate Concerns**

### **1.1 Performance & Latency**
- **Bursty traffic** from KV evictions/refills can congest the **spine switch**, leading to unpredictable latency and performance degradation.
- **Rail-optimized paths** are essential to avoid spine usage and ensure low-latency, high-throughput communication between AX nodes and CS-X.
- **Evict performance** is the most critical path — delays directly impact throughput.

### **1.2 Memory Imbalance and Waste**
- KVSS shards have **unequal memory-per-token** requirements due to variable WIO allocations per domain.
- **Naive or equal memory allocation** leads to severe waste — underutilized shards bottleneck overall cache capacity.
- Simulation shows **non-proportional allocation reduces effective cache by 40%**.

### **1.3 Scheduler Limitations**
- Current scheduler **cannot detect spine usage during placement**, risking suboptimal network paths.
- No mechanism to **rollback or reschedule** after placement decisions.
- **Job sharing** introduces **session rigidity** ("session blackhole") — once jobs are running, resizing or reconfiguring sessions requires job cancellation and potential downtime.

### **1.4 Scalability and Multi-Tenancy**
- Need to support **multiple models**, **draft/target decoders**, and **independent caches** (e.g., SWA).
- Must scale across **replicas** while maintaining **cache coherence** and **isolation**.
- Load balancer affinity helps, but global cache sharing introduces complexity.

### **1.5 Security and Privacy**
- Risk of **cross-organization cache leakage** if not properly isolated.
- Need **configurable TTL policies** (last-use, first-use) to meet compliance and privacy requirements.
- Sensitive prompts (e.g., user input) may need restricted caching.

### **1.6 Operational Resilience**
- **Session blackhole**: Inability to remove AX/CS-X from active sessions without disrupting jobs.
- **Single node failure** can impact multiple jobs in shared sessions.
- **Cluster software upgrades** are complicated by shared, long-running sessions.

### **1.7 CPU and Resource Contention**
- **Too many KVSS shards** → CPU contention due to busy loops (especially in HIO latency mode).
- **Ingress spinning** and **zero-copy overheads** add to CPU load.
- Trade-off between **WIO balancing** and **CPU efficiency**.

---

## **2. Decision Processes and Rationale**

### **2.1 Core Architecture: SwDriver-Centric, KVSS as Storage**
- **Decision**: SwDriver manages cache state; KVSS is passive storage.
- **Rationale**:
  - Avoids back-and-forth queries and locking.
  - Enables fine-grained control for features like Spec Decode and SWA.
  - Centralizes cache logic for consistency.

### **2.2 Memory Allocation Strategy: Fair Share Based on Boxes**
- **Decision**: Adopt **fair distribution based on number of CS-X boxes** used by a job.
- **Rationale**:
  - Operator doesn’t need prior knowledge of all jobs.
  - Reduces memory imbalance across KVU nodes.
  - Simple to implement and aligns with cluster-wide resource fairness.
- **Trade-off**: Less flexibility for prioritizing high-value models.

### **2.3 Network Topology: Rail Optimization as Priority**
- **Decision**: Enforce **rail-optimized paths** for KVSS ↔ CS-X communication.
- **Rationale**:
  - Prevents spine congestion from bursty KV traffic.
  - Ensures predictable performance.
  - Matches hardware design intent.
- **Short-term mitigation**: Conservative memory grants to increase chance of rail-optimized placement.

### **2.4 Cross-Replica Caching: Load Balancer Affinity (Preferred)**
- **Decision**: Use **load balancer affinity** (by `isolation_id`, then prompt hash) over shared cache.
- **Rationale**:
  - Avoids shared state and coherence complexity.
  - Enables fault isolation and easy restarts.
  - Fully compatible with current SwDriver cache visibility.
- **Future**: Consider **two-level cache** (L1: local KVSS, L2: SharedKVSS) for long-term reuse.

### **2.5 Cache Eviction and Refill: Column-Based, Synchronized**
- **Decision**: Operate in **fixed-size cache columns** (e.g., 64 tokens).
- **Rationale**:
  - Simplifies refill and eviction logic.
  - Enables efficient batch operations.
  - Facilitates concurrency via `evictCount` synchronization.

### **2.6 Concurrency Model: Dual-Queue with Versioning**
- **Decision**: Separate **evict** and **refill/delete** queues in KVSS, synchronized via `evictCount`.
- **Rationale**:
  - Prevents race conditions.
  - SwDriver maintains linear view of operations.
  - Enables safe overwrites (e.g., for Spec Decode).

### **2.7 Speculative Decoding and SWA Support**
- **Decision**: Support both, but **only cache verified tokens**.
- **Rationale**:
  - Prevents caching speculative (potentially incorrect) KV states.
  - SWA handled via logical reconstruction of cache windows.

### **2.8 Fault Tolerance and Resilience**
- **Decision**: Accept **data loss on failure**; prioritize **system availability**.
- **Rationale**:
  - KV cache is performance enhancement, not persistent state.
  - Redundancy can be achieved via prompt replay or replication.
  - Focus on preventing cascading failures.

---

## **3. Implementation Roadmap and Priorities**

| Priority | Item | Status | Owner/Team |
|--------|------|--------|-----------|
| 1 | **Evict performance optimization** | Critical | Runtime, HIO |
| 2 | **Scheduler updates for WIO stream awareness** | In progress | Cluster Scheduling |
| 3 | **Buffering to reduce HIO busy loop** | Future | Runtime |
| 4 | **Spine-aware scheduler** | Long-term | Cluster Scheduling |
| 5 | **Two-level cache (L1 + L2)** | Future | KVSS, Storage |
| 6 | **Per-org TTL and policy API** | Future | Framework |
| 7 | **Multimodal prompt caching** | Future | SwDriver |

---

## **4. Operational Implications**

### **4.1 Session Management**
- **Minimum session size** should be enforced during creation.
- **Session resizing** is high-risk — avoid unless necessary.
- **Proposal**: Define cluster-level rules for session increments and minimum size.

### **4.2 Cluster Upgrades**
- **Cluster software updates** (6-month cycle) must coexist with inference workloads.
- **Inference-platform updates** (weekly) can run across versions.
- **Mitigation**: Support multi-version compatibility within sessions.

### **4.3 Monitoring and Diagnostics**
- **Spine usage warnings** should be logged.
- **Flag to reject spine-optimized placements** in production.
- **Performance telemetry** for refill/evict latency and cache hit rates.

---

## **5. Key Trade-offs Summary**

| Trade-off | Decision | Rationale |
|---------|--------|---------|
| **Memory allocation** | Fair-share over exact | Simpler, less operator burden |
| **Network path** | Rail-optimized over spine | Prevents interference, ensures performance |
| **Cache sharing** | Load-balancer affinity over global cache | Simpler, more robust |
| **Cache state** | SwDriver-managed over KVSS-autonomous | Avoids coordination overhead |
| **Failure mode** | Accept data loss over strong persistence | Prioritizes availability and simplicity |

---

## **Appendix A: Glossary of Terms**

| Term | Definition |
|------|-----------|
| **KVSS (Key-Value Storage Server)** | Off-wafer server that stores evicted KV cache values; one or more shards per CS-X box. |
| **SwDriver** | Software driver on AX node that controls inference execution and manages prompt caching. |
| **CS-X / CS-3** | Cerebras wafer-scale AI system (e.g., CS-3); contains compute cores and IO domains. |
| **AX Node** | Activation node (x86 server) with high-bandwidth connection to CS-X; hosts KVSS, SwDriver, etc. |
| **Domain** | FPGA on CS-X that handles IO; each CS-X has 4 domains. |
| **WIO (Weight I/O)** | Logical channel for transferring weights or KV data between AX and wafer. |
| **Rail / Rail-Optimized Path** | Direct network path from AX to CS-X port via leaf switch, avoiding spine; lower latency. |
| **Spine Switch** | High-capacity central switch; shared across jobs; congestion-prone under bursty traffic. |
| **KV Cache** | Key-Value states stored during transformer attention; reused to avoid recomputation. |
| **Prompt Caching** | Reusing KV states from previous prompts to accelerate inference on shared prefixes. |
| **Cache Column** | Unit of caching (e.g., 64 tokens); refills and evictions occur in column-sized units. |
| **PrefixMap** | SwDriver’s in-memory map of cached prefixes, indexed by hash and `isolation_id`. |
| **isolation_id** | Identifier (e.g., Org ID) used to isolate cache entries between tenants. |
| **Speculative Decoding (Spec Decode)** | Technique using a draft model to predict tokens; requires careful KV cache management. |
| **Sliding Window Attention (SWA)** | Attention mechanism that limits context window; complicates cache alignment. |
| **Job Sharing** | Multiple inference jobs sharing the same AX nodes within a session. |
| **Session Blackhole** | Inability to resize or reconfigure a session once jobs are running. |
| **HIO (Host I/O)** | Low-level interface for AX-to-wafer communication; used in latency-sensitive mode. |
| **evictCount** | Monotonic counter used to synchronize KVSS operations and ensure version consistency. |
| **SharedKVSS** | Hypothetical long-term, disk-backed shared cache for cross-replica reuse. |
| **TTL (Time-To-Live)** | Duration for which a cached entry remains valid; enforced via first/last-use timestamps. |

---
